"""Real video measurement tests: detect synthetic motion and static failure."""
import json
import subprocess
from pathlib import Path
import pytest
from cinemaswarm_world.media_qc import inspect_clip, inspect_suite
from cinemaswarm_world.studio_runtime import file_sha

def generate(path,moving):
    source="testsrc2=size=320x320:rate=12:duration=3" if moving else "color=c=blue:s=320x320:r=12:d=3"
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi",
         "-i",source,"-f","lavfi","-i","sine=frequency=440:duration=3",
         "-shortest","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac",
         str(path)]
    result=subprocess.run(cmd,capture_output=True,text=True,check=False)
    assert result.returncode==0,result.stderr

def test_real_moving_clip_passes_technical_gate(tmp_path):
    generate(tmp_path/"moving.mp4",True)
    report=inspect_clip(tmp_path,"moving.mp4",
                        expected_sha256=file_sha(tmp_path/"moving.mp4"),
                        min_duration=2,max_duration=4,
                        min_width=320,min_height=320,require_audio=True,
                        minimum_motion=0.25)
    assert report["status"]=="checks_passed",report
    assert report["measurements"]["mean_interframe_difference"]>0.25

def test_static_movie_is_not_animated_acting(tmp_path):
    generate(tmp_path/"still.mp4",False)
    report=inspect_clip(tmp_path,"still.mp4",
                        expected_sha256=file_sha(tmp_path/"still.mp4"),
                        minimum_motion=0.25)
    assert report["status"]=="blocked"
    assert "insufficient_temporal_pixel_change" in report["failures"]

def test_tampered_media_hash_is_rejected(tmp_path):
    generate(tmp_path/"moving.mp4",True)
    report=inspect_clip(tmp_path,"moving.mp4",
                        expected_sha256="a"*64)
    assert "video_hash_mismatch" in report["failures"]

def test_manifest_checks_clips(tmp_path):
    generate(tmp_path/"moving.mp4",True)
    manifest={"version":1,"episode_id":"proof","clips":[{
        "id":"take1","path":"moving.mp4",
        "sha256":file_sha(tmp_path/"moving.mp4"),
        "min_duration":2,"max_duration":4,"min_width":320,"min_height":320,
        "require_audio":True,"minimum_motion":0.25}]}
    assert inspect_suite(manifest,tmp_path)["status"]=="checks_passed"
    manifest["clips"][0]["sha256"]="b"*64
    assert inspect_suite(manifest,tmp_path)["status"]=="blocked"
