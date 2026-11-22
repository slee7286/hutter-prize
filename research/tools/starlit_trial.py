"""Run from repo root; see research/experiments/starlit-order.md. Linux only."""

import hashlib
import json
import mmap
import os
import re
import shutil
import struct
import subprocess as sp
import time
from pathlib import Path

ROOT = Path.cwd()
UP = ROOT / "build/starlit"
BASE = ROOT / "build/starlit-trial"
RAW = ROOT / "data/enwik9"
BIN = UP / "prebuild_binary/cmix_amdzen1_ub18"
DIC = UP / "dictionary/english.dic"
ORDER = UP / "src/readalike_prepr/data/new_article_order"
OFFSETS = (0, 250000000, 500000000, 750000000, 998951424)
CPU = min(os.sched_getaffinity(0))


def digest(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def check(ok, what):
    if not ok:
        raise RuntimeError(what)


def save(p, obj):
    temp = p.with_suffix(".tmp")
    temp.write_text(json.dumps(obj, indent=2) + "\n")
    temp.replace(p)


def sandbox(work, args, mounts=()):
    cmd = [
        "bwrap",
        "--die-with-parent",
        "--unshare-all",
        "--new-session",
        "--clearenv",
        "--setenv",
        "PATH",
        "/usr/bin:/bin",
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib64",
        "/lib64",
        "--symlink",
        "usr/bin",
        "/bin",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--bind",
        str(work),
        "/work",
        "--chdir",
        "/work",
    ]
    for src, dest in mounts:
        cmd += ["--ro-bind", str(src), dest]
    return cmd + args


def phase(label, work, args, mounts=()):
    print(label, flush=True)
    save(BASE / "active.json", {"phase": label, "start": time.time()})
    stats = BASE / (label + ".time")
    start = time.monotonic()
    peak = 0
    cmd = sandbox(
        work,
        [
            "/usr/bin/time",
            "-f",
            "%M",
            "-o",
            "/work/phase-rss",
            "taskset",
            "-c",
            str(CPU),
            "nice",
            "-n",
            "10",
            *args,
        ],
        mounts,
    )
    with (BASE / (label + ".log")).open("wb") as log:
        proc = sp.Popen(cmd, stdin=sp.DEVNULL, stdout=log, stderr=sp.STDOUT)
        try:
            while True:
                disk = 0
                for p in work.iterdir():
                    try:
                        disk += p.stat().st_size
                    except FileNotFoundError:
                        pass
                peak = max(disk, peak)
                check(
                    disk < 100_000_000_000
                    and shutil.disk_usage(BASE).free > 20_000_000_000,
                    "disk guard",
                )
                try:
                    rc = proc.wait(timeout=15)
                    break
                except sp.TimeoutExpired:
                    pass
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
    check(rc == 0, f"{label}: exit {rc}")
    (work / "phase-rss").replace(stats)
    rec = {
        "phase": label,
        "elapsed_s": time.monotonic() - start,
        "max_rss_kib": int(stats.read_text().strip()),
        "sampled_work_bytes": peak,
        "cpu": CPU,
    }
    with (BASE / "metrics.jsonl").open("a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def samples() -> list[dict[str, int]]:
    rank = {i: j for j, i in enumerate(map(int, ORDER.read_text().split()))}
    spans: list[list[tuple[int, bytes]]] = [[] for _ in OFFSETS]
    ends: list[dict[str, int]] = []
    with RAW.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as buf:
        for i, m in enumerate(re.finditer(b"(?m)^  <page>\n", buf)):
            a = m.start()
            k = next((k for k, o in enumerate(OFFSETS) if o <= a < o + 1048576), None)
            if k is None:
                continue
            token = b"  </page>\n"
            j = buf.find(token, a, min(len(buf), OFFSETS[k] + 1048576))
            if j >= 0:
                spans[k].append((i, bytes(buf[a : j + len(token)])))
    for k, rows in enumerate(spans):
        check(rows, f"empty window {k}")
        for arm in ("off", "on"):
            seq = (
                rows
                if arm == "off"
                else sorted(rows, key=lambda r: rank.get(r[0], len(rank) + r[0]))
            )
            p = BASE / f"window{k}-{arm}"
            p.write_bytes(b"".join(page for _, page in seq))
        ends.append(
            {
                "offset": OFFSETS[k],
                "pages": len(rows),
                "bytes": (BASE / f"window{k}-on").stat().st_size,
            }
        )
    return ends


def main():
    check(
        digest(RAW)
        == "159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc",
        "wrong corpus",
    )
    check(
        digest(BIN)
        == "8221d024cf8b54c6be45935e301a342a3a3cd63c0a1d2e6365653e02adaa9d85",
        "wrong binary",
    )
    check(
        sp.check_output(["git", "-C", UP, "rev-parse", "HEAD"], text=True).strip()
        == "14d68047e7b89f81c4504dc05f8e57a96247d880",
        "wrong revision",
    )
    sp.run(
        [
            "git",
            "-C",
            UP,
            "diff",
            "--quiet",
            "HEAD",
            "--",
            str(DIC.relative_to(UP)),
            str(ORDER.relative_to(UP)),
        ],
        check=True,
    )
    BASE.mkdir(exist_ok=False)
    prep = BASE / "prep"
    prep.mkdir()
    shutil.copy(BIN, prep / "tool")
    (prep / "tool").chmod(0o755)
    (prep / "identity").write_bytes(b"0\n")
    windows = samples()
    packs = {}
    for name, src in [("dict", DIC), ("on", ORDER), ("off", prep / "identity")]:
        phase(
            "pack-" + name,
            prep,
            ["./tool", "-c", "/input", "c-" + name],
            [(src, "/input")],
        )
        check((prep / ("c-" + name)).stat().st_size > 0, "missing compressed component")
    for arm in ("on", "off"):
        d = (prep / "c-dict").read_bytes()
        o = (prep / ("c-" + arm)).read_bytes()
        p = BASE / ("cmix-" + arm)
        p.write_bytes(BIN.read_bytes() + d + o + struct.pack("<iii", len(d), len(o), 0))
        p.chmod(0o755)
        packs[arm] = p.stat().st_size
    for k, row in enumerate(windows):
        for arm in ("on", "off") if k % 2 == 0 else ("off", "on"):
            tag = f"slice-{k}-{arm}"
            w = BASE / tag
            w.mkdir()
            inp = BASE / f"window{k}-{arm}"
            common = [(prep / "tool", "/tool"), (DIC, "/dict")]
            phase(
                tag + "-enc",
                w,
                ["/tool", "-c", "/dict", "/input", "payload"],
                common + [(inp, "/input")],
            )
            v = BASE / (tag + "-decode")
            v.mkdir()
            phase(
                tag + "-dec",
                v,
                ["/tool", "-d", "/dict", "/payload", "out"],
                common + [(w / "payload", "/payload")],
            )
            sp.run(["cmp", inp, v / "out"], check=True)
            row[arm] = (w / "payload").stat().st_size
    predicted = (
        1e9
        * sum(r["off"] - r["on"] for r in windows)
        / sum(r["bytes"] for r in windows)
        + packs["off"]
        - packs["on"]
    )
    result = {
        "windows": windows,
        "compressor_bytes": packs,
        "predicted_saving": predicted,
        "full": {},
    }
    save(BASE / "prediction.json", result)
    for arm in ("on", "off"):
        w = BASE / (arm + "-encode")
        w.mkdir()
        shutil.copy(BASE / ("cmix-" + arm), w / "cmix")
        enc = phase(
            arm + "-full-encode",
            w,
            ["./cmix", "-e", "/enwik9", "payload"],
            [(RAW, "/enwik9")],
        )
        arc = w / "archive9"
        check(arc.stat().st_size > 1_000_000, "missing archive")
        v = BASE / (arm + "-decode")
        v.mkdir()
        shutil.copy(arc, v / "archive9")
        (v / "archive9").chmod(0o755)
        dec = phase(arm + "-full-decode", v, ["./archive9"])
        out = v / "enwik9_uncompressed"
        sp.run(["cmp", RAW, out], check=True)
        result["full"][arm] = {
            "archive_bytes": arc.stat().st_size,
            "total": packs[arm] + arc.stat().st_size,
            "archive_sha256": digest(arc),
            "output_sha256": digest(out),
            "byte_equal": True,
            "encode": enc,
            "decode": dec,
        }
        save(BASE / "verified.json", result)
    actual = result["full"]["off"]["total"] - result["full"]["on"]["total"]
    result.update(
        actual_saving=actual,
        prediction_minus_actual=predicted - actual,
        sign_agrees=(predicted > 0) == (actual > 0),
        matches_published_amd_sizes=packs["on"] == 390308
        and result["full"]["on"]["archive_bytes"] == 114904928,
    )
    save(BASE / "final.json", result)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
