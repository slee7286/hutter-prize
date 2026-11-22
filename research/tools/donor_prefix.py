"""Bounded raw decoder comparison. Run: python3 -m research.tools.donor_prefix"""

import itertools
import json
import os
import select
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from .weight_integration import ROOT, W, meta, need, parts

LIMIT = 65536
WALL = 240
ARMS = ("t-fixed", "baseline", "candidate")


def compare(a, b):
    if len(a) != LIMIT or len(b) != LIMIT:
        return {"status": "incomplete"}
    for offset, (left, right) in enumerate(zip(a, b, strict=True)):
        if left != right:
            return {
                "status": "differ",
                "offset": offset,
                "left_byte": left,
                "right_byte": right,
            }
    return {"status": "match"}


def capture(fifo, argv, log, timeout):
    """Do not block waiting for open, pad short reads, or consume >LIMIT."""
    deadline = time.monotonic() + timeout
    buf = bytearray()
    with (
        log.open("wb") as out,
        os.fdopen(
            os.open(fifo, os.O_RDONLY | os.O_NONBLOCK), "rb", buffering=0
        ) as stream,
    ):
        fd = stream.fileno()
        with subprocess.Popen(
            argv, stdout=out, stderr=subprocess.STDOUT, start_new_session=True
        ) as p:
            try:
                while len(buf) < LIMIT:
                    left = deadline - time.monotonic()
                    if left <= 0:
                        stop = "wall_timeout"
                        break
                    ready = select.select([fd], [], [], min(left, 0.2))[0]
                    if ready:
                        data = os.read(fd, LIMIT - len(buf))
                        if not data:
                            stop = "writer_closed"
                            break
                        buf.extend(data)
                    elif p.poll() is not None:
                        stop = "process_exit"
                        break
                else:
                    stop = "prefix_limit"
            finally:
                # Only our own new process group. bwrap's PID namespace and
                # --die-with-parent also terminate the namespaced codec.
                if p.poll() is None:
                    try:
                        os.killpg(p.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                rc = p.wait(timeout=8)
    return bytes(buf), stop, rc


def box(work, fifo, files):
    cmd = [
        "bwrap",
        "--unshare-all",
        "--die-with-parent",
        "--new-session",
        "--clearenv",
        "--setenv",
        "PATH",
        "/usr/bin",
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/bin",
        "/bin",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib64",
        "/lib64",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--tmpfs",
        "/tmp",
        "--bind",
        str(work),
        "/w",
        "--chdir",
        "/w",
    ]
    for name, path in files.items():
        cmd.extend(["--ro-bind", str(path), "/w/" + name])
    # A bind mount prevents the writer replacing the FIFO by a regular file.
    cmd.extend(
        [
            "--bind",
            str(fifo),
            "/w/restored.cmix.temp",
            "/w/archive9",
            "-d",
            "dictionary",
            "corpus.stream",
            "restored",
            "--transformer",
            "weights",
        ]
    )
    return cmd


def main():
    ref = json.loads(
        (
            ROOT / "research/experiments/transformer-integration-packages.json"
        ).read_text()
    )
    manifest = {
        r[0]: {"bytes": int(r[1]), "sha256": r[2]}
        for line in (ROOT / "research/tools/late-artifacts.tsv")
        .read_text()
        .splitlines()
        for r in [line.split("\t")]
    }
    dictionary = ROOT / "build/weight-research-src/dictionary/english.dic"
    need(
        meta(dictionary.read_bytes()) == manifest["lex/english.dic"],
        "wrong plaintext dictionary",
    )
    root = Path(tempfile.mkdtemp(prefix="donor-prefix-", dir=W))
    payload = root / "corpus.stream"
    evidence = {}
    mounts = {}
    length = 0
    for arm in ARMS:
        dir_ = root / arm
        dir_.mkdir()
        published = arm == "t-fixed"
        archive = ((ROOT / "build/late/t-fixed") if published else W / arm) / "archive9"
        raw = archive.read_bytes()
        fingerprint = meta(raw)
        need(
            fingerprint
            == (manifest["t-fixed/archive9"] if published else ref[arm]["archive9"]),
            f"wrong {arm} executable",
        )
        _, packed_dictionary, _, weights, stream, _ = parts(raw, True)
        need(
            meta(packed_dictionary) == ref["dictionary"]
            and meta(stream) == ref["corpus_payload"],
            "wrong packed assets",
        )
        model = ref["baseline" if published else arm]["weights"]
        need(meta(weights) == model, "wrong packaged weights")
        if published:
            payload.write_bytes(stream)
        need(payload.read_bytes() == stream, "payload not byte-identical")
        header = int.from_bytes(stream[:5], "big")
        length = header & ((1 << 39) - 1)
        need(
            header >> 39 == 1
            and length > LIMIT
            and sum(b.bit_count() for b in stream[5:37]) == 205,
            "not a dictionary predictive stream with 205-symbol vocab",
        )
        weight_file = dir_ / "weights"
        weight_file.write_bytes(weights)
        need(weight_file.read_bytes() == weights, "weight copy mismatch")
        mounts[arm] = {
            "archive9": archive,
            "dictionary": dictionary,
            "weights": weight_file,
            "corpus.stream": payload,
        }
        evidence[arm] = {"archive": fingerprint, "embedded_weights": model}
        del raw, stream, weights
    report = {
        "prefix_limit": LIMIT,
        "wall_limit_s_per_arm": WALL,
        "corpus_payload": ref["corpus_payload"],
        "predictive_length": length,
        "dictionary": manifest["lex/english.dic"],
        "capture": "restored.cmix.temp FIFO from -d dictionary corpus.stream restored --transformer weights",
        "arms": evidence,
    }
    print("Run directory:", root, flush=True)
    data = {}
    for arm in ARMS:
        where = root / arm
        fifo = where / "tap"
        os.mkfifo(fifo, 0o600)
        work = where / "work"
        work.mkdir()
        start = time.monotonic()
        data[arm], stop, rc = capture(
            fifo, box(work, fifo, mounts[arm]), where / "decode.log", WALL
        )
        elapsed = round(time.monotonic() - start, 3)
        out = where / "prefix.bin"
        out.write_bytes(data[arm])
        evidence[arm].update(
            prefix=meta(out.read_bytes()),
            stop=stop,
            supervisor_exit=rc,
            elapsed_s=elapsed,
        )
        need(not (work / "restored").exists(), "unexpected final postprocessed output")
        shutil.rmtree(work)
        fifo.unlink()
        (root / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(arm, len(data[arm]), stop, elapsed, flush=True)
    pairs = {
        f"{a}:{b}": compare(data[a], data[b])
        for a, b in itertools.combinations(ARMS, 2)
    }
    report["comparisons"] = pairs
    report["verdict"] = (
        "incomplete"
        if any(v["status"] == "incomplete" for v in pairs.values())
        else "investigate baseline"
        if pairs["t-fixed:baseline"]["status"] != "match"
        else "investigate candidate"
        if pairs["baseline:candidate"]["status"] != "match"
        else "all matched"
    )
    (root / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(pairs), report["verdict"], flush=True)


if __name__ == "__main__":
    main()
