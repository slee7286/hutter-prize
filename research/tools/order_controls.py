"""Attribute an order-extraction disagreement without opening the corpus."""

import json
import subprocess
import tempfile
from pathlib import Path

from .weight_integration import ROOT, W, box, meta, need, parts


def compare(raw, target):
    first = next((i for i, (a, b) in enumerate(zip(raw, target)) if a != b), None)
    if first is None and len(raw) != len(target):
        first = min(len(raw), len(target))
    return dict(**meta(raw), matches_reference=raw == target, first_difference=first)


def verify_guard(p, package, expected_exe):
    """Exercise real compressor startup on an empty input, never enwik9."""
    exe = package / "cmix"
    need(meta(exe.read_bytes()) == expected_exe, "wrong startup binary")
    dummy = p / "empty"
    dummy.touch()
    try:
        box(
            p,
            "native-guard",
            {"cmix": exe, "empty": dummy},
            ["./cmix", "-e", "empty", "unused"],
        )
    except subprocess.CalledProcessError as exc:
        lines = (p / "native-guard.log").read_bytes().splitlines()
        message = next(
            (
                line
                for line in lines
                if line.startswith(b"cmix error: the dictionary decompressed to ")
            ),
            None,
        )
        if message is None:
            raise ValueError(
                "startup did not report a dictionary hash mismatch"
            ) from exc
        return {"exit_code": exc.returncode, "message": message.decode("ascii")}
    raise ValueError("expected hash rejection not observed")


def run(package):
    root = ROOT / "build/weight-research-src"
    rs = ROOT / "research/experiments"
    receipt = json.loads((rs / "transformer-integration-packages.json").read_text())
    manifest = {
        s[0]: s[2]
        for s in (
            l.split("\t")
            for l in (ROOT / "research/tools/late-artifacts.tsv")
            .read_text()
            .splitlines()
        )
    }
    pub = ROOT / "build/late/t-fixed/cmix"
    donor = pub.read_bytes()
    need(meta(donor)["sha256"] == manifest["t-fixed/cmix"], "published binary drift")
    _, dictionary, order, _, _, _ = parts(donor, False)
    p = Path(tempfile.mkdtemp(prefix="order-controls-", dir=W))
    print(p, flush=True)
    targets = {
        "order": (root / "src/readalike_prepr/data/new_article_order").read_bytes(),
        "dictionary": (root / "dictionary/english.dic").read_bytes(),
    }
    for name, data in [("order", order), ("dictionary", dictionary)]:
        need(meta(data) == receipt[name], "embedded asset differs")
        (p / name).write_bytes(data)
    base = W / "baseline/cmix"
    need(
        meta(base.read_bytes()) == receipt["baseline"]["cmix"], "pre-static core drift"
    )
    result = {"reference": {k: meta(v) for k, v in targets.items()}, "arms": {}}
    for label, exe, assets in [
        ("published", pub, ("order", "dictionary")),
        ("pre_static_rebuild", base, ("order", "dictionary")),
        ("label_rebuild", package / "cmix", ("dictionary",)),
    ]:
        raw = exe.read_bytes()
        embedded = parts(raw, False)
        need(embedded[1] == dictionary, "dictionary changed")
        row = {"executable": meta(raw)}
        for asset in assets:
            if asset == "order":
                need(embedded[2] == order, "wrong order")
            out = box(
                p,
                label + "-" + asset,
                {"cmix": exe, "stream": p / asset},
                ["./cmix", "-d", "stream", "raw"],
            )
            row[asset] = compare((out / "raw").read_bytes(), targets[asset])
        result["arms"][label] = row
    if not result["arms"]["label_rebuild"]["dictionary"]["matches_reference"]:
        result["native_guard"] = verify_guard(
            p, package, result["arms"]["label_rebuild"]["executable"]
        )
    text = json.dumps(result, indent=2) + "\n"
    (p / "result.json").write_text(text)
    print(text)
    return result


if __name__ == "__main__":
    import sys

    run(Path(sys.argv[1]).resolve())
