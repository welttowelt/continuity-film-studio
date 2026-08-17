from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY / "scripts" / "check_upstream_pin.py"
MANIFEST = REPOSITORY / "docs" / "upstream-pin.json"


def run_check(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
    )


def test_recorded_pin_matches_checkout() -> None:
    result = run_check()
    assert result.returncode == 0, result.stderr
    assert "upstream pin verified" in result.stdout


def test_manifest_lists_all_seven_skills() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert len(manifest["skill_files"]) == 7
    assert manifest["submodule_commit"]


def test_drift_is_detected(tmp_path: Path) -> None:
    tampered = json.loads(MANIFEST.read_text())
    tampered["skill_files"]["shot-prompt"] = "0" * 64
    tampered["submodule_commit"] = "f" * 40
    tampered_path = tmp_path / "upstream-pin.json"
    tampered_path.write_text(json.dumps(tampered))

    result = run_check("--manifest", str(tampered_path))
    assert result.returncode == 1
    assert "submodule commit moved" in result.stderr
    assert "shot-prompt" in result.stderr


def test_missing_manifest_fails(tmp_path: Path) -> None:
    result = run_check("--manifest", str(tmp_path / "absent.json"))
    assert result.returncode == 1
    assert "missing manifest" in result.stderr
