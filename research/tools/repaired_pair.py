"""Construct a dictionary-only repair and validate actual package startup."""

import os
import sys
import tempfile
from pathlib import Path

from .dictionary_repair import receipt, record
from .donor_prefix import LIMIT, WALL, capture
from .order_controls import compare
from .weight_integration import ROOT, W, assemble, box, meta, need, parts, sandbox


def replace_pair(old, out, *, dictionary=None, core=None, order=None):
    for name in ("cmix", "archive9"):
        c, d, o, w, s, n = parts((old / name).read_bytes(), name == "archive9")
        fields = (
            core if core is not None else c,
            dictionary if dictionary is not None else d,
            order if order is not None and o else o,
            w,
            s,
            len(order) if order is not None else n,
        )
        dest = out / name
        dest.write_bytes(assemble(*fields))
        dest.chmod(0o755)
        need(parts(dest.read_bytes(), name == "archive9") == fields, "package readback")


def run_tap(out, label, mounts, tapped, argv):
    work = out / label
    work.mkdir()
    fifo = work / tapped
    os.mkfifo(fifo, 0o600)
    cmd = sandbox(work, mounts) + ["--bind", str(fifo), "/w/" + tapped, *argv]
    raw, stop, _ = capture(fifo, cmd, out / (label + ".log"), WALL)
    need(
        stop == "prefix_limit" and len(raw) == LIMIT,
        f"{label}: {stop}, {len(raw)} bytes",
    )
    return raw, work


def validate(pair, prefix):
    out = Path(tempfile.mkdtemp(prefix="check-", dir=pair))
    target = ROOT / "build/weight-research-src"
    gold = receipt("transformer-donor-prefix-result")
    controls = receipt("order-controls-result")["reference"]
    ref = prefix.read_bytes()
    need(meta(ref) == gold["arms"]["t-fixed"]["prefix"], "unverified prefix")
    dic = (target / "dictionary/english.dic").read_bytes()
    order = (target / "src/readalike_prepr/data/new_article_order").read_bytes()
    need(
        meta(dic) == controls["dictionary"] and meta(order) == controls["order"],
        "wrong reference assets",
    )
    cmix = pair / "cmix"
    archive = pair / "archive9"
    a = parts(archive.read_bytes(), True)
    c = parts(cmix.read_bytes(), False)
    need(
        a[1] == c[1]
        and a[3] == c[3]
        and a[5] == c[5]
        and meta(a[4]) == gold["corpus_payload"],
        "asset pair inconsistency",
    )
    # Only the compressor and a dummy one-line input. The split writes its
    # .intro AFTER dictionary verification; cap that write before reordering.
    dummy = out / "dummy"
    dummy.write_bytes(b"Q" * (2 * LIMIT))
    raw, comp = run_tap(
        out,
        "compress-start",
        {"cmix": cmix, "dummy": dummy},
        ".intro",
        ["./cmix", "-e", "dummy", "unused"],
    )
    need(
        raw == b"Q" * LIMIT
        and (comp / ".dict").read_bytes() == dic
        and (comp / ".new_article_order").read_bytes() == order,
        "compressor startup",
    )
    # No arguments and no external assets. temp_path is built while output_path
    # is empty; .dict.cmix.temp belongs to a different subprocess.
    raw, dec = run_tap(
        out, "archive-start", {"archive9": archive}, ".cmix.temp", ["./archive9"]
    )
    need(
        (dec / ".dict").read_bytes() == dic
        and (dec / ".tfweights").read_bytes() == a[3]
        and (dec / ".ready4cmix_decomp").read_bytes() == a[4],
        "native extraction differs from reference assets",
    )
    (out / "prefix.bin").write_bytes(raw)
    controls_by_name = {}
    if raw != ref:
        files = {
            "archive9": archive,
            "dictionary": dec / ".dict",
            "weights": dec / ".tfweights",
            "corpus.stream": dec / ".ready4cmix_decomp",
        }
        argv = [
            "./archive9",
            "-d",
            "dictionary",
            "corpus.stream",
            "restored",
            "--transformer",
            "weights",
        ]
        for arm in ("explicit", "explicit-alias"):
            if arm == "explicit-alias":
                files[".dict"] = dec / ".dict"
            captured, _ = run_tap(out, arm, files, "restored.cmix.temp", argv)
            (out / (arm + ".bin")).write_bytes(captured)
            controls_by_name[arm] = {
                "vs_pinned": compare(captured, ref),
                "vs_native": compare(captured, raw),
            }
    fixture = out / "fixture"
    sample = (bytes(range(205)) * 50)[:10240]
    fixture.write_bytes(sample)
    enc = box(
        out,
        "short-enc",
        {"cmix": cmix, "input": fixture, "weights": comp / ".tfweights"},
        ["./cmix", "-n", "input", "stream", "--transformer", "weights"],
    )
    stream = enc / "stream"
    need(
        meta(stream.read_bytes())
        == receipt("transformer-integration-predictive")["candidate"]["payload"],
        "short payload changed",
    )
    short = box(
        out,
        "short-dec",
        {"archive9": archive, "weights": dec / ".tfweights", "stream": stream},
        ["./archive9", "-d", "stream", "out", "--transformer", "weights"],
    )
    need((short / "out").read_bytes() == sample, "short restore failed")
    r = {
        "cmix": meta(cmix.read_bytes()),
        "archive9": meta(archive.read_bytes()),
        "total": cmix.stat().st_size + archive.stat().st_size,
        "embedded_dictionary": meta(a[1]),
        "both_recovered_dictionaries": meta(dic),
        "restored_order": meta(order),
        "short_payload": meta(stream.read_bytes()),
        "exact_short_bytes": len(sample),
        "archive_native_prefix": meta(raw),
        "native_vs_pinned": compare(raw, ref),
        "explicit_controls": controls_by_name,
        "verdict": "baseline" if raw == ref else "blocked",
        "archive_prefix_stop": "prefix_limit",
        "unchanged_corpus_payload": meta(a[4]),
    }
    record(pair, "checks.json", r)
    return r


def main(old, fresh, prefix):
    before = receipt("label-integration-result")
    newdict = fresh.read_bytes()
    verified = receipt("dictionary-fresh-result")["fresh_vs_shipped"]
    need(
        all(meta(newdict)[k] == verified[k] for k in ("bytes", "sha256")),
        "wrong fresh stream",
    )
    need(
        all(meta((old / n).read_bytes()) == before[n] for n in ("cmix", "archive9")),
        "incorrect blocked pair",
    )
    out = Path(tempfile.mkdtemp(prefix="repaired-pair-", dir=W))
    print(out, flush=True)
    replace_pair(old, out, dictionary=newdict)
    r = validate(out, prefix)
    record(
        out,
        "baseline.json" if r["verdict"] == "baseline" else "blocked.json",
        dict(
            r,
            blocked_size_reference=before["total"],
            repair_cost=r["total"] - before["total"],
        ),
    )


if __name__ == "__main__":
    main(*(Path(s).resolve() for s in sys.argv[1:]))
