"""Build/verify the run-label inverse without starting enwik9 compression."""

import json
import os
import shutil
import subprocess as sp
import sys
import tempfile
from pathlib import Path

from .core_packing import REPORTS, UPX
from .order_controls import compare
from .weight_integration import ROOT, W, assemble, box, meta, need, parts


def report(name):
    return json.loads((REPORTS / name).read_text())


def main(packed, asset):
    base = report("core-packing-result.json")
    labels = report("order-labels-result.json")
    stream = (asset / "enc/stream").read_bytes()
    need(meta(stream) == labels["stream"], "bad order stream")
    out = Path(tempfile.mkdtemp(prefix="label-integration-", dir=W))
    print(out, flush=True)
    src = out / "src"
    sp.run(
        [
            "git",
            "clone",
            "-q",
            "--no-hardlinks",
            ROOT / "build/weight-research-src",
            src,
        ],
        check=True,
    )
    need(
        sp.check_output(["git", "rev-parse", "HEAD"], cwd=src, text=True).strip()
        == "83f2603f3f7751da5f429fd32669807eb8510494",
        "wrong source",
    )
    tools = ROOT / "research/tools/weight_tables"
    sp.run(["git", "apply", tools / "release-loader.patch"], cwd=src, check=True)
    profile = src / "pgo_data"
    profile.mkdir()
    shutil.copyfile(W / "src/pgo_data/default.profdata", profile / "default.profdata")
    usr = W / "sysroot/usr"
    env = dict(
        os.environ,
        PATH=f"{usr}/bin:{os.environ['PATH']}",
        LD_LIBRARY_PATH=f"{usr}/lib/x86_64-linux-gnu:{usr}/lib/llvm-17/lib",
    )
    header = src / "src/readalike_prepr/self_extract.h"
    for arm in ("control", "labels"):
        if arm == "labels":
            txt = header.read_text()
            marker = "int selfextract_comp() {"
            old = (
                'RunSubprocess("./cmix -d .new_article_order.comp .new_article_order");'
            )
            need(
                txt.count(marker) == 1 and txt.count(old) == 1,
                "unknown extraction code",
            )
            header.write_text(
                txt.replace(
                    marker, (tools / "order_restore.inc").read_text() + "\n" + marker
                ).replace(
                    old,
                    'RunSubprocess("./cmix -d .new_article_order.comp .order_labels");\n  RestoreArticleOrder();',
                )
            )
        with (out / (arm + ".log")).open("wb") as log:
            sp.run(
                [
                    "make",
                    "-j2",
                    "CFLAGS_DEFINES=-DSEED=923 -DUPDATE_LIMIT=3000 -include stdint.h",
                    "prof_use",
                ],
                cwd=src,
                env=env,
                stdout=log,
                stderr=sp.STDOUT,
                check=True,
                timeout=210,
            )
        core = out / (arm + ".core")
        sp.run(
            [UPX, "-q", "-9", "--lzma", "-o", core, src / "cmix"],
            check=True,
            stdout=sp.DEVNULL,
        )
        sp.run([UPX, "-q", "-t", core], check=True, stdout=sp.DEVNULL)
        if arm == "control":
            need(meta(core.read_bytes()) == base["new_core"], "control core drift")
    code = core.read_bytes()
    r = {
        "core": meta(code),
        "control_exact": True,
        "order": meta(stream),
        "baseline": base["total"],
        "prediction_net": 14000,
    }
    for name in ("cmix", "archive9"):
        original = (packed / name).read_bytes()
        need(meta(original) == base[name], "wrong input package")
        _, d, order, weights, payload, _ = parts(original, name == "archive9")
        changed = (code, d, stream if order else b"", weights, payload, len(stream))
        f = out / name
        f.write_bytes(assemble(*changed))
        f.chmod(0o755)
        disk = f.read_bytes()
        need(parts(disk, name == "archive9") == changed, "failed package readback")
        r[name] = meta(disk)
        if name == "archive9":
            r["unchanged_corpus_payload"] = meta(payload)
        (out / (name + ".weights")).write_bytes(weights)
    r["total"] = r["cmix"]["bytes"] + r["archive9"]["bytes"]
    r["net"] = r["baseline"] - r["total"]
    r["packed_code_growth_both"] = 2 * (len(code) - base["new_core"]["bytes"])
    if r["net"] > 0:
        # Allow the actual -e self-extractor to finish and close the order file,
        # then deliberately fail the NEXT dictionary stage. No enwik9 is mounted.
        dummy = out / "empty"
        dummy.touch()
        barrier = out / "directory-not-file"
        barrier.mkdir()
        for stage, exe in [
            ("control-startup", packed / "cmix"),
            ("startup", out / "cmix"),
        ]:
            try:
                box(
                    out,
                    stage,
                    {"cmix": exe, "empty": dummy, ".dict.cmix.temp": barrier},
                    ["./cmix", "-e", "empty", "unused"],
                )
            except sp.CalledProcessError:
                log = (out / (stage + ".log")).read_bytes()
                need(
                    b"cmix error: './cmix -d .dict.comp .dict' failed" in log,
                    "startup did not reach the intentional dictionary stop",
                )
            else:
                raise ValueError("dictionary stop not observed")
        reference = (src / "src/readalike_prepr/data/new_article_order").read_bytes()
        restored = (out / "startup/.new_article_order").read_bytes()
        old_order = (out / "control-startup/.new_article_order").read_bytes()
        need(meta(reference) == labels["source"], "pinned source changed")
        r["control_order_vs_source"] = compare(old_order, reference)
        r["candidate_order_vs_source"] = compare(restored, reference)
        r["control_and_candidate_order_identical"] = restored == old_order
        r["order_from_packaged_startup"] = meta(restored)
        r["dictionary_stop_expected"] = True
        gold = report("transformer-integration-predictive.json")
        sample = (bytes(range(205)) * 50)[:10240]
        (out / "input").write_bytes(sample)
        enc = box(
            out,
            "encode",
            {
                "cmix": out / "cmix",
                "weights": out / "cmix.weights",
                "input": out / "input",
            },
            ["./cmix", "-n", "input", "stream", "--transformer", "weights"],
        )
        pred = enc / "stream"
        need(
            meta(pred.read_bytes()) == gold["candidate"]["payload"],
            "prediction changed",
        )
        dec = box(
            out,
            "decode",
            {
                "archive9": out / "archive9",
                "weights": out / "archive9.weights",
                "stream": pred,
            },
            ["./archive9", "-d", "stream", "out", "--transformer", "weights"],
        )
        need((dec / "out").read_bytes() == sample, "short decode differs")
        r.update(
            predictive_payload=meta(pred.read_bytes()),
            exact_short_decode=True,
        )
        # Do not grant a package keep based on a fixture using supplied weights
        # if the real dictionary prerequisite for the donor corpus is broken.
        dictionary = src / "dictionary/english.dic"
        actual = box(
            out,
            "dictionary",
            {"archive9": out / "archive9", "stream": out / "startup/.dict.comp"},
            ["./archive9", "-d", "stream", "raw"],
        )
        r["dictionary_vs_source"] = compare(
            (actual / "raw").read_bytes(), dictionary.read_bytes()
        )
        if not r["candidate_order_vs_source"]["matches_reference"]:
            r["verdict"] = "reject"
        elif (
            not r["dictionary_vs_source"]["matches_reference"]
            or not r["control_and_candidate_order_identical"]
        ):
            r["verdict"] = "blocked"
        else:
            r["verdict"] = "keep"
    else:
        r["verdict"] = "reject"
    t = json.dumps(r, indent=2) + "\n"
    (out / "result.json").write_text(t)
    print(t)


if __name__ == "__main__":
    main(*(Path(s).resolve() for s in sys.argv[1:]))
