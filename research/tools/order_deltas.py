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


def run(packed):
    rdir = ROOT / "research/experiments"
    ref = json.loads((rdir / "core-packing-result.json").read_text())
    core = packed / "cmix"
    need(meta(core.read_bytes()) == ref["cmix"], "incorrect baseline")
    p = Path(tempfile.mkdtemp(prefix="order-", dir=W))
    print(p, flush=True)
    source = (
        ROOT / "build/weight-research-src/src/readalike_prepr/data/new_article_order"
    ).read_bytes()
    raw = encode(source)
    need(decode(raw) == source, "order is not canonical")
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
    need(restored == raw and decode(restored) == source, "mismatch")
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
        "prediction_net": 28000,
        "verdict": "integrate" if old > new else "reject",
    }
    text = json.dumps(result, indent=2) + "\n"
    (p / "result.json").write_text(text)
    print(text)


if __name__ == "__main__":
    run(Path(sys.argv[1]).resolve())
