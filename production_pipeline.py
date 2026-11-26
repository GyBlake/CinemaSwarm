"""Provider-neutral production manifest, stage gates and durable receipts."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

STAGES = ("manifest", "assets", "soundtrack", "picture", "performance",
          "assembly", "continuity", "quality", "delivery")

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate_manifest(data):
    if not isinstance(data, dict) or not data.get("episode_id"):
        raise ValueError("episode_id required")
    shots = data.get("shots")
    if not isinstance(shots, list) or not shots:
        raise ValueError("shots required")
    seen = set()
    cursor = 0
    for shot in shots:
        sid = shot.get("id")
        if not isinstance(sid, str) or not sid or sid in seen:
            raise ValueError("unique shot id required")
        seen.add(sid)
        if type(shot.get("start_ms")) is not int or shot["start_ms"] != cursor:
            raise ValueError("shots must form a contiguous timeline")
        duration = shot.get("duration_ms")
        if type(duration) is not int or duration <= 0:
            raise ValueError("positive integer duration required")
        if not isinstance(shot.get("prompt"), str) or not shot["prompt"].strip():
            raise ValueError("shot prompt required")
        cursor += duration
    if data.get("duration_ms") != cursor:
        raise ValueError("episode duration mismatch")
    return cursor

@dataclass(frozen=True)
class Receipt:
    stage: str
    path: str
    sha256: str

class Pipeline:
    def __init__(self, checkpoint):
        self.path = Path(checkpoint)
        self.receipts = []
        if self.path.exists():
            for item in json.loads(self.path.read_text(encoding="utf-8")):
                receipt = Receipt(**item)
                self._verify(receipt)
                self.receipts.append(receipt)

    def _verify(self, receipt):
        if len(self.receipts) >= len(STAGES) or receipt.stage != STAGES[len(self.receipts)]:
            raise ValueError("out-of-order receipt")
        if digest(receipt.path) != receipt.sha256:
            raise ValueError("artifact hash mismatch")

    def record(self, stage, artifact):
        artifact = Path(artifact).resolve()
        if not artifact.is_file() or not artifact.stat().st_size:
            raise ValueError("nonempty artifact required")
        if stage == "manifest":
            validate_manifest(json.loads(artifact.read_text(encoding="utf-8")))
        receipt = Receipt(stage, str(artifact), digest(artifact))
        self._verify(receipt)
        pending = self.receipts + [receipt]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps([r.__dict__ for r in pending], indent=2), encoding="utf-8")
        temp.replace(self.path)
        self.receipts = pending
        return receipt

    @property
    def next_stage(self):
        return STAGES[len(self.receipts)] if len(self.receipts) < len(STAGES) else None
