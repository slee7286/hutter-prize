"""Experiment 2: full order asset, no article/corpus compression."""

import json
import sys
import tempfile
from pathlib import Path

from .weight_integration import ROOT, W, box, meta, need


def encode(source):
    out = bytearray()
    prev = 0
    for line in source.splitlines():
        value = int(line)
        d = value - prev
        prev = value
        n = 2 * d if d >= 0 else -2 * d - 1
        while n >= 128:
            out.append((n % 128) + 128)
            n //= 128
        out.append(n)
    return bytes(out)


def decode(buf):
    prev = n = bits = 0
    out = bytearray()
    for b in buf:
        n |= (b % 128) << bits
        if b >= 128:
            bits += 7
            need(bits <= 28, "oversize varint")
            continue
        prev += n // 2 if n % 2 == 0 else -(n // 2) - 1
        out.extend(f"{prev}\n".encode())
        bits = n = 0
    need(bits == 0, "unterminated varint")
    return bytes(out)


def label_encode(source):
    ids = list(map(int, source.splitlines()))
    need(
        ids and min(ids) >= 0 and len(set(ids)) == len(ids),
        "expected unique nonnegative IDs",
    )
    labels = [0] * (max(ids) + 1)
    prev = -1
    run_id = 0
    for v in ids:
        if v > prev:
            run_id += 1
        labels[v] = run_id
        prev = v
    need(run_id <= 65535, "run label out of range")
    return bytes(v % 256 for v in labels) + bytes(v // 256 for v in labels)


def label_decode(buf):
    need(len(buf) % 2 == 0, "bad plane lengths")
    n = len(buf) // 2
    groups = {}
    for i in reversed(range(n)):
        v = buf[i] + 256 * buf[n + i]
        if v:
            groups.setdefault(v, []).append(i)
    return b"".join(f"{i}\n".encode() for v in sorted(groups) for i in groups[v])


def run(packed, mode="deltas"):
    need(mode in ("labels", "deltas"), "unknown order representation")
    transform, inverse, predicted = (
        (label_encode, label_decode, 14000)
        if mode == "labels"
        else (encode, decode, 28000)
    )
    rdir = ROOT / "research/experiments"
    ref = json.loads((rdir / "core-packing-result.json").read_text())
    core = packed / "cmix"
    need(meta(core.read_bytes()) == ref["cmix"], "incorrect baseline")
    p = Path(tempfile.mkdtemp(prefix="order-", dir=W))
    print(p, flush=True)
    source = (
        ROOT / "build/weight-research-src/src/readalike_prepr/data/new_article_order"
    ).read_bytes()
    raw = transform(source)
    need(inverse(raw) == source, "order is not canonical")
    (p / "deltas").write_bytes(raw)
    enc = box(
        p, "enc", {"cmix": core, "src": p / "deltas"}, ["./cmix", "-n", "src", "stream"]
    )
    stream = enc / "stream"
    dec = box(
        p,
        "dec",
        {"cmix": core, "stream": stream},
        ["./cmix", "-d", "stream", "decoded"],
    )
    restored = (dec / "decoded").read_bytes()
    need(restored == raw and inverse(restored) == source, "mismatch")
    old = json.loads((rdir / "transformer-integration-packages.json").read_text())[
        "order"
    ]["bytes"]
    new = stream.stat().st_size
    result = {
        "source": meta(source),
        "transformed": meta(raw),
        "old_order_bytes": old,
        "stream": meta(stream.read_bytes()),
        "saving_before_code": old - new,
        "exact": True,
        "method": mode,
        "prediction_net": predicted,
        "verdict": "integrate" if old > new else "reject",
    }
    text = json.dumps(result, indent=2) + "\n"
    (p / "result.json").write_text(text)
    print(text)


if __name__ == "__main__":
    run(Path(sys.argv[1]).resolve(), *sys.argv[2:])
