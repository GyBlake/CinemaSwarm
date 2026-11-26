"""Offline-first production execution: validated media, explicit approval, resumable rendering."""
import hashlib, json, subprocess, os, tempfile
from pathlib import Path

def sha(path):
    with open(path,'rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))

def verify_media(path, kind, seconds=None, tolerance=.15):
    p=probe(path)
    if not any(s['codec_type']==kind for s in p['streams']):
        raise ValueError(f'Missing {kind}: {path}')
    duration=float(p['format']['duration'])
    if seconds is not None and abs(duration-seconds)>tolerance:
        raise ValueError(f'Duration mismatch: {path}: {duration} vs {seconds}')
    return {'path':str(Path(path).resolve()),'sha256':sha(path),'duration':duration,'kind':kind}

def atomic_json(path, data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,delete=False,encoding='utf8') as f:
        json.dump(data,f,indent=2); temp=f.name
    os.replace(temp,path)

def validate(shots):
    cursor=0; ids=set()
    for s in shots:
        if not isinstance(s['id'],str) or not s['id'] or s['id'] in ids or type(s['start_ms']) is not int or s['start_ms']!=cursor or type(s['duration_ms']) is not int or s['duration_ms']<=0 or not s['prompt'].strip():
            raise ValueError('Invalid shot sequence')
        ids.add(s['id']); cursor+=s['duration_ms']
    if not cursor: raise ValueError('Empty timeline')
    return cursor/1000

def preflight(shots, score, takes, assets):
    duration=validate(shots)
    refs=[]
    for a in assets:
        if sha(a['path'])!=a['sha256']: raise ValueError('Asset integrity failure')
        refs.append(a)
    music=verify_media(score,'audio',duration)
    ready={}; missing=[]
    for s in shots:
        t=takes.get(s['id'])
        if not t or not t.get('approved'):
            missing.append(s['id']); continue
        if sha(t['path'])!=t['sha256']: raise ValueError('Take integrity failure')
        ready[s['id']]=verify_media(t['path'],'video',s['duration_ms']/1000)
        if s.get('dialogue_required'): verify_media(t['path'],'audio')
    return {'duration':duration,'assets':refs,'score':music,'ready':ready,'missing':missing}

def assemble(shots, score, takes, assets, output):
    state=preflight(shots,score,takes,assets)
    if state['missing']: raise ValueError('Missing approved takes: '+','.join(state['missing']))
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists(): raise FileExistsError(output)
    with tempfile.TemporaryDirectory(dir=output.parent) as work:
        work=Path(work); parts=[]
        for i,s in enumerate(shots):
            src=state['ready'][s['id']]['path']; out=work/f'{i}.mp4'; seconds=s['duration_ms']/1000
            has_audio=any(x['codec_type']=='audio' for x in probe(src)['streams'])
            cmd=['ffmpeg','-v','error','-y','-i',src]
            if not has_audio: cmd+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
            cmd+=['-map','0:v:0','-map','0:a:0' if has_audio else '1:a:0','-vf','scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24','-af','apad','-t',str(seconds),'-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-ac','2',str(out)]
            subprocess.run(cmd,check=True); parts.append(out)
        listing=work/'concat.txt'; listing.write_text(''.join(f"file {p.name}\n" for p in parts))
        joined=work/'joined.mp4'; subprocess.run(['ffmpeg','-v','error','-f','concat','-safe','1','-i',str(listing),'-c','copy',str(joined)],check=True)
        final=work/'final.mp4'; subprocess.run(['ffmpeg','-v','error','-i',str(joined),'-i',str(score),'-filter_complex','[1:a]volume=0.25[m];[0:a][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]','-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-t',str(state['duration']),str(final)],check=True)
        verify_media(final,'video',state['duration']); verify_media(final,'audio',state['duration']); os.replace(final,output)
    return verify_media(output,'video',state['duration'])
