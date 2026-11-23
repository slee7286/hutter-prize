"""Isolate the fixed donor's auxiliary dictionary; do not open enwik9."""

import json
import sys
import tempfile
from pathlib import Path

from .order_controls import compare
from .weight_integration import ROOT, W, box, meta, need, parts


def receipt(name):
    return json.loads((ROOT / "research/experiments" / (name + ".json")).read_text())


def record(p, name, data):
    text = json.dumps(data, indent=2) + "\n"
    (p / name).write_text(text)
    print(text, flush=True)


def fresh(pair):
    refs = receipt("order-controls-result")
    pub = ROOT / "build/late/t-fixed/cmix"
    raw = pub.read_bytes()
    need(
        meta(raw) == refs["arms"]["published"]["executable"], "published binary changed"
    )
    old = parts(raw, False)[1]
    dic = ROOT / "build/weight-research-src/dictionary/english.dic"
    target = dic.read_bytes()
    need(meta(target) == refs["reference"]["dictionary"], "wrong plaintext")
    p = Path(tempfile.mkdtemp(prefix="dictionary-repair-", dir=W))
    print(p, flush=True)
    enc = (
        box(
            p,
            "encode",
            {"cmix": pub, "input": dic},
            ["./cmix", "-c", "input", "stream"],
        )
        / "stream"
    )
    data = enc.read_bytes()
    r = {
        "published": meta(raw),
        "plaintext": meta(target),
        "shipped": meta(old),
        "fresh_vs_shipped": compare(data, old),
    }
    for label, exe in [("published", pub), ("candidate", pair / "archive9")]:
        if label == "candidate":
            need(
                meta(exe.read_bytes())
                == receipt("label-integration-result")["archive9"],
                "wrong candidate",
            )
        name = exe.name
        dec = box(
            p,
            label + "-decode",
            {name: exe, "stream": enc},
            ["./" + name, "-d", "stream", "decoded"],
        )
        match = compare((dec / "decoded").read_bytes(), target)
        r[label + "_decode"] = match
        if not match["matches_reference"]:
            break
    record(p, "fresh.json", r)


if __name__ == "__main__":
    fresh(Path(sys.argv[1]).resolve())
