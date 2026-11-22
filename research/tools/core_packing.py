"""Change only UPX's method on the already tested transformer ELF."""

import json
import subprocess
import tempfile
from pathlib import Path

from .weight_integration import ROOT, W, assemble, box, meta, need, parts

REPORTS = ROOT / "research/experiments"
UPX = ROOT / "build/upx-5.1.1-amd64_linux/upx"


def run():
    p = Path(tempfile.mkdtemp(prefix="packing-", dir=W))
    print(p, flush=True)
    sizes = json.loads((REPORTS / "transformer-integration-packages.json").read_text())[
        "candidate"
    ]
    prior = json.loads(
        (REPORTS / "transformer-integration-predictive.json").read_text()
    )
    raw = W / "src/cmix"

    def upx(*args):
        subprocess.run([UPX, "-q", *args], check=True, capture_output=True, timeout=180)

    cores = {}
    for mode, flags in [("old", []), ("new", ["--lzma"])]:
        f = p / mode
        upx("-9", *flags, "-o", f, raw)
        upx("-t", f)
        restored = p / (mode + ".elf")
        upx("-d", "-o", restored, f)
        need(restored.read_bytes() == raw.read_bytes(), "ELF reconstruction differs")
        cores[mode] = f.read_bytes()
        if mode == "old":
            need(meta(cores[mode]) == sizes["core"], "old packer control mismatch")
    r = {
        "tool": meta(UPX.read_bytes()),
        "elf": meta(raw.read_bytes()),
        "control_core": meta(cores["old"]),
        "new_core": meta(cores["new"]),
        "both_unpacked_exact": True,
        "baseline": sizes["combined"],
        "prediction": 20000,
    }
    if len(cores["new"]) >= len(cores["old"]):
        r.update(verdict="reject", net=2 * (len(cores["old"]) - len(cores["new"])))
    else:
        for name in ("cmix", "archive9"):
            b = (W / "candidate" / name).read_bytes()
            need(meta(b) == sizes[name], "package baseline mismatch")
            core, *assets = parts(b, name == "archive9")
            need(core == cores["old"], "bad core")
            out = p / name
            out.write_bytes(assemble(cores["new"], *assets))
            out.chmod(0o755)
            disk = out.read_bytes()
            need(
                parts(disk, name == "archive9") == (cores["new"], *assets),
                "bad package readback",
            )
            r[name] = meta(disk)
            (p / (name + ".weights")).write_bytes(assets[2])
        fixture = (bytes(range(205)) * 50)[:10240]
        (p / "input").write_bytes(fixture)
        enc = box(
            p,
            "encode",
            {"cmix": p / "cmix", "weights": p / "cmix.weights", "input": p / "input"},
            ["./cmix", "-n", "input", "stream", "--transformer", "weights"],
        )
        stream = enc / "stream"
        need(
            meta(stream.read_bytes()) == prior["candidate"]["payload"],
            "predictive payload differs",
        )
        dec = box(
            p,
            "decode",
            {
                "archive9": p / "archive9",
                "weights": p / "archive9.weights",
                "stream": stream,
            },
            ["./archive9", "-d", "stream", "out", "--transformer", "weights"],
        )
        need((dec / "out").read_bytes() == fixture, "predictive restore failed")
        total = r["cmix"]["bytes"] + r["archive9"]["bytes"]
        r.update(
            verdict="keep",
            total=total,
            net=r["baseline"] - total,
            short_payload=meta(stream.read_bytes()),
            exact_decode=True,
        )
    t = json.dumps(r, indent=2) + "\n"
    (p / "result.json").write_text(t)
    print(t)


if __name__ == "__main__":
    run()
