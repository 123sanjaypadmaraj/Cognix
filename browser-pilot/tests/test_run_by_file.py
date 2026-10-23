"""The per-file runner: summary parsing, an end-to-end run, resume, and the low-memory stop."""
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("run_by_file", Path(__file__).with_name("run_by_file.py"))
rbf = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rbf)


@pytest.mark.parametrize("line,expected", [
    ("3 passed, 1 skipped, 2 deselected in 4.2s", dict(passed=3, skipped=1, deselected=2)),
    ("1 failed, 2 passed in 0.5s", dict(failed=1, passed=2)),
    ("no tests ran in 0.01s", dict()),
    ("5 deselected in 0.02s", dict(deselected=5)),
    ("1 passed, 1 error in 1.0s", dict(passed=1, errors=1)),
    ("=== 2 failed, 1 errors in 3.0s ===", dict(failed=2, errors=1)),
])
def test_parse_summary(line, expected):
    got = rbf.parse_summary("noise\n" + line + "\n")
    assert got == {**dict.fromkeys(rbf.COUNTS, 0), **expected}


@pytest.fixture
def suite(tmp_path):
    d = tmp_path / "suite"
    d.mkdir()
    (d / "test_a.py").write_text("def test_ok():\n    assert True\n")
    (d / "test_b.py").write_text("import pytest\n\ndef test_bad():\n    assert False\n\n"
                                 "@pytest.mark.skip\ndef test_skipped():\n    pass\n")
    return d


def test_end_to_end_then_resume(suite, tmp_path, monkeypatch, capsys):
    out = tmp_path / "out"
    assert rbf.main(["--out", str(out), "--tests-dir", str(suite), "--marker", "not browser"]) == 1
    results = json.loads((out / "results.json").read_text())
    assert results["test_a.py"]["passed"] == 1 and results["test_a.py"]["failed"] == 0
    assert results["test_b.py"]["failed"] == 1 and results["test_b.py"]["skipped"] == 1
    assert any("test_bad" in l for l in results["test_b.py"]["failures"])
    assert (out / "test_a.log").exists()

    def no_spawn(*a, **k):
        raise AssertionError("resume must not start a subprocess")
    monkeypatch.setattr(subprocess, "Popen", no_spawn)
    assert rbf.main(["--out", str(out), "--tests-dir", str(suite), "--resume"]) == 1


def test_stops_when_memory_is_short(suite, tmp_path):
    pytest.importorskip("psutil")
    out = tmp_path / "out"
    code = rbf.main(["--out", str(out), "--tests-dir", str(suite), "--min-free-mb", "1e12", "--wait", "0"])
    assert code == 3
    assert json.loads((out / "results.json").read_text()) == {}
