"""CLI builds a real review packet without authorizing media production."""
import json
from pathlib import Path
import pytest
from scripts.compile_studio_crew import compile_default, main

def test_compile_default_offline():
    doc=compile_default()
    assert doc["status"]=="planning_packets_not_performed"
    assert len(doc["departments"])==18
    assert all(x["status"]!="authorized" for x in doc["departments"])

def test_compile_writes_no_clobber(tmp_path):
    target=tmp_path/"crew"/"handoffs.json"
    assert main(["--output",str(target)])==0
    data=json.loads(target.read_text())
    assert data==compile_default()
    with pytest.raises(FileExistsError):
        main(["--output",str(target)])
    assert main(["--output",str(target),"--overwrite"])==0
