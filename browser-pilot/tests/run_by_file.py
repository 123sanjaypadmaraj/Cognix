"""Run the test suite one file at a time, so a machine short of memory never holds the whole suite in one process.

    python tests/run_by_file.py --out DIR [--marker "not browser"] [--only GLOB] [--resume]
                                [--min-free-mb 1500] [--wait 300] [--tests-dir tests]

Each file's output goes to DIR/<stem>.log and its counts to DIR/results.json (rewritten after every file, so a stopped
run loses nothing). Exit codes: 0 all green, 1 failures or errors, 3 stopped for lack of free memory (use --resume).
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COUNTS = ("passed", "failed", "errors", "skipped", "deselected")
_WORD = {"passed": "passed", "failed": "failed", "error": "errors", "errors": "errors",
         "skipped": "skipped", "deselected": "deselected"}


def parse_summary(text: str) -> dict:
    """Counts from pytest's last summary line, e.g. `1 failed, 2 passed, 1 skipped in 4.2s`."""
    counts = dict.fromkeys(COUNTS, 0)
    for line in reversed(text.splitlines()):
        line = line.strip("= ").strip()
        if re.search(r"\bin [\d.]+s\b", line) and re.search(r"\b(passed|failed|errors?|skipped|deselected|no tests ran)\b", line):
            for n, word in re.findall(r"(\d+) (passed|failed|errors?|skipped|deselected)\b", line):
                counts[_WORD[word]] += int(n)
            break
    return counts


def _psutil():
    try:
        import psutil
        return psutil
    except ImportError:
        return None


def _free_mb() -> float | None:
    ps = _psutil()
    return ps.virtual_memory().available / 1048576 if ps else None


def _wait_for_memory(min_free: float, wait: float) -> float | None:
    """The free MB once it reaches `min_free`, or the last reading (below it) after `wait` seconds."""
    deadline = time.monotonic() + wait
    while True:
        free = _free_mb()
        if free is None or free >= min_free or time.monotonic() >= deadline:
            return free
        time.sleep(min(10, max(0.0, deadline - time.monotonic())))


def _peak_rss(proc, ps) -> float:
    try:
        p = ps.Process(proc.pid)
        return (p.memory_info().rss + sum(c.memory_info().rss for c in p.children(recursive=True))) / 1048576
    except Exception:
        return 0.0


def run_file(path: Path, out: Path, marker: str, tests_dir: Path) -> dict:
    cmd = [sys.executable, "-m", "pytest", str(path), "-q", "-m", marker, "-rf", "--durations=15", "-p", "no:cacheprovider"]
    ps = _psutil()
    peak = 0.0
    start = time.monotonic()
    log = out / f"{path.stem}.log"
    with open(log, "w", encoding="utf-8", errors="replace") as fh:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
        while proc.poll() is None:
            if ps:
                peak = max(peak, _peak_rss(proc, ps))
            time.sleep(0.5) if ps else proc.wait()
    seconds = round(time.monotonic() - start, 1)
    text = log.read_text(encoding="utf-8", errors="replace")
    row = {"file": path.name, "exit_code": proc.returncode, **parse_summary(text), "seconds": seconds,
           "peak_rss_mb": round(peak, 1) if ps else None,
           "failures": [l for l in text.splitlines() if l.startswith(("FAILED", "ERROR"))],
           "durations": [l.strip() for l in text.splitlines() if re.match(r"\s*[\d.]+s (call|setup|teardown) ", l)]}
    return row


def _save(results: dict, out: Path):
    tmp = out / "results.json.tmp"
    tmp.write_text(json.dumps(results, indent=2), encoding="utf-8")
    os.replace(tmp, out / "results.json")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--marker", default="not browser")
    ap.add_argument("--only", default="*")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--min-free-mb", type=float, default=1500)
    ap.add_argument("--wait", type=float, default=300)
    ap.add_argument("--tests-dir", default="tests")
    a = ap.parse_args(argv)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tests_dir = Path(a.tests_dir)
    if not tests_dir.is_absolute():
        tests_dir = ROOT / tests_dir
    results: dict = {}
    if a.resume and (out / "results.json").exists():
        results = json.loads((out / "results.json").read_text(encoding="utf-8"))
    else:
        _save(results, out)
    files = [f for f in sorted(tests_dir.glob("test_*.py")) if fnmatch.fnmatch(f.name, a.only) or fnmatch.fnmatch(f.stem, a.only)]
    if _psutil() is None:
        print("note: psutil is not installed; memory columns are null and the free-memory check is skipped")

    for f in files:
        if f.name in results:
            continue
        free = _wait_for_memory(a.min_free_mb, a.wait)
        if free is not None and free < a.min_free_mb:
            print(f"stopped: only {free:.0f} MB free before {f.name}; re-run with --resume")
            return 3
        results[f.name] = run_file(f, out, a.marker, tests_dir)
        _save(results, out)
        r = results[f.name]
        print(f"{f.name}: {r['passed']} passed, {r['failed']} failed, {r['errors']} errors in {r['seconds']}s", flush=True)

    rows = sorted(results.values(), key=lambda r: -r["seconds"])
    print("\nslowest first:")
    for r in rows:
        print(f"  {r['seconds']:8.1f}s  peak {r['peak_rss_mb']} MB  {r['file']}  "
              f"({r['passed']} passed, {r['failed']} failed, {r['errors']} errors, {r['skipped']} skipped)")
    totals = {k: sum(r[k] for r in rows) for k in COUNTS}
    print(f"total: {totals} in {sum(r['seconds'] for r in rows):.1f}s")
    for r in rows:
        for line in r["failures"]:
            print(line)
    bad = any(r["failed"] or r["errors"] or r["exit_code"] not in (0, 5) for r in rows)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
