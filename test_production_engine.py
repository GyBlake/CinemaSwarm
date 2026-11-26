import tempfile, unittest, subprocess
from pathlib import Path
from production_engine import validate, sha, preflight, assemble, verify_media

class EngineTests(unittest.TestCase):
    def test_invalid_timeline(self):
        for start, duration in [(1,1000),(0,0),(0,True)]:
            with self.assertRaises(ValueError): validate([dict(id='a',start_ms=start,duration_ms=duration,prompt='test')])
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); v=p/'take.mp4'; m=p/'score.wav'; out=p/'master.mp4'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=180x320:rate=24','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','1','-c:v','libx264','-c:a','aac',str(v)],check=True)
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=220:sample_rate=48000','-t','2',str(m)],check=True)
            shots=[dict(id=str(i),start_ms=i*1000,duration_ms=1000,prompt='synthetic fixture',dialogue_required=True) for i in range(2)]
            assets=[dict(path=str(v),sha256=sha(v))]
            self.assertEqual(preflight(shots,m,{},assets)['missing'],['0','1'])
            with self.assertRaises(ValueError): assemble(shots,m,{},assets,out)
            self.assertFalse(out.exists())
            takes={s['id']:dict(path=str(v),sha256=sha(v),approved=True) for s in shots}
            for name in ('master.mp4','second.mp4'):
                assembled=assemble(shots,m,takes,assets,p/name)
                self.assertAlmostEqual(assembled['duration'],2,places=1)
                verify_media(p/name,'audio',2)
            with self.assertRaises(FileExistsError): assemble(shots,m,takes,assets,out)
            takes['0']['sha256']='bad'
            with self.assertRaises(ValueError): preflight(shots,m,takes,assets)
if __name__=='__main__': unittest.main()
