import sys
import types
from pathlib import Path

# Lightweight SDK stand-ins let pure workflow functions be tested without network calls.
class StubAgent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    def as_tool(self, **kwargs):
        return kwargs

sys.modules.setdefault("agents", types.SimpleNamespace(Agent=StubAgent, Runner=types.SimpleNamespace()))
sys.modules.setdefault("dotenv", types.SimpleNamespace(load_dotenv=lambda: None))

from cinema_swarm import DEFAULT_BRIEF, build_request, parse_args, write_packet


def test_default_brief_is_generic():
    assert "Lantern City" in DEFAULT_BRIEF
    assert "Dreamguard" not in DEFAULT_BRIEF


def test_request_contains_brief():
    assert "cartographer" in build_request(DEFAULT_BRIEF)


def test_empty_brief_rejected():
    import pytest
    with pytest.raises(ValueError):
        build_request("   ")


def test_output_refuses_overwrite(tmp_path):
    import pytest
    path = tmp_path / "packet.md"
    write_packet(path, "first")
    with pytest.raises(FileExistsError):
        write_packet(path, "second")
    assert path.read_text() == "first"
    write_packet(path, "second", overwrite=True)
    assert path.read_text() == "second"


def test_cli_dry_run_flag():
    assert parse_args(["--dry-run"]).dry_run is True

def test_dry_run_without_sdk(tmp_path):
    import subprocess
    from pathlib import Path
    script = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    result = subprocess.run(
        [sys.executable, str(script), "--dry-run"],
        cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert "Lantern City" in result.stdout
    assert "SERIES BRIEF:" in result.stdout
    assert not (tmp_path / "pilot_sequence.md").exists()
