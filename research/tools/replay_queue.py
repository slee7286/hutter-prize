"""Run remaining high-memory cases serially after the named quiet job exits (Linux)."""

import argparse
import fcntl
import json
import os
import select
import shutil
import subprocess
import time
from pathlib import Path

MID = ["bash", "research/tools/mid-replay.sh"]
LATE = ["python3", "research/tools/late-replay.py"]
CASES = [
    ("fast", MID + ["recompress", "fast"]),
    ("obias", LATE + ["full", "obias"]),
    ("lex", LATE + ["full", "lex"]),
    ("transformer", LATE + ["decode-public", "transformer"]),
    ("fx2", MID + ["recompress", "fx2"]),
    ("fx", MID + ["recompress", "fx"]),
]


def dependency(receipt):
    s = json.loads(receipt.read_text())
    if s["state"] != "running":
        if s.get("exit_code") is None:
            raise RuntimeError("Dependency is not in a recognized terminal state")
        return
    pid = int(s["supervisor_pid"])
    try:
        fd = os.pidfd_open(pid)
    except ProcessLookupError:
        return
    try:
        # Check PID reuse, then block on the stable descriptor, not a polling loop.
        birth = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
        if birth == str(s["supervisor_birth"]):
            wait = select.poll()
            wait.register(fd, select.POLLIN)
            wait.poll()
    except FileNotFoundError:
        pass
    finally:
        os.close(fd)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("predecessor", type=Path)
    args = ap.parse_args()
    out = Path("build/replay-queue")
    out.mkdir(exist_ok=True)
    with (out / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print("Waiting for predecessor to release the large-memory slot", flush=True)
        dependency(args.predecessor)
        bad = 0
        for name, cmd in CASES:
            receipt = out / (name + ".json")
            if receipt.exists():
                bad += json.loads(receipt.read_text())["returncode"] != 0
                continue
            if shutil.disk_usage(out).free < 80_000_000_000:
                raise RuntimeError(
                    "Under 80 GB free: stop before starting another codec"
                )
            print("Starting", name, flush=True)
            start = time.time()
            env = os.environ.copy()
            if name == "transformer":
                env["REPLAY_USE_SDE"] = "1"
            prefix = [
                "systemd-run",
                "--user",
                "--scope",
                "-q",
                "-p",
                "MemoryMax=14G",
                "-p",
                "MemorySwapMax=0",
                "nice",
                "-n",
                "15",
                "taskset",
                "-c",
                "0",
                "timeout",
                "-k",
                "1m",
                "144h",
            ]
            with (out / (name + ".log")).open("wb") as log:
                rc = subprocess.run(
                    prefix + cmd, stdout=log, stderr=subprocess.STDOUT, env=env
                ).returncode
            r = {
                "case": name,
                "argv": cmd,
                "returncode": rc,
                "elapsed_s": time.time() - start,
            }
            tmp = receipt.with_suffix(".tmp")
            tmp.write_text(json.dumps(r, indent=2) + "\n")
            tmp.replace(receipt)
            print(r, flush=True)
            bad += rc != 0
        return bool(bad)


if __name__ == "__main__":
    raise SystemExit(main())
