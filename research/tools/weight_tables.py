"""Recode the complete, pinned July fx2-cmix-T model, never the corpus.

Run from anywhere with `python research/tools/weight_tables.py`. See the
preregistration for artifact retrieval. All generated files are in build/.
"""

import hashlib
import json
import struct
import subprocess as sp
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build/weight-tables"
UP = ROOT / "build/weight-research-src"
FIX = UP / "cpp_infer/src"
TOOLS = Path(__file__).with_suffix("")
SRC_PIN = "83f2603f3f7751da5f429fd32669807eb8510494"
WEIGHTS = "7f4db6c8c843a7e6264b6a48ed4805e9e431f543df7a9a0ecb37a35a5e4b8860"
PINS = {
    "cmix": "f8ddc2dfa3188398c4c60932abc5c5f2e1339c9be3769fad7943005ab6d40d30",
    "archive9": "2d368eb6df0da26432e7c19718df96caabcd597afb52d9065d351054305e5c6e",
}
FLAGS = [
    "-std=c++17",
    "-Os",
    "-s",
    "-ffunction-sections",
    "-fdata-sections",
    "-Wl,--gc-sections",
]


def projected_saving(before, after, code_delta):
    return 2 * (before - after - code_delta)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def h(data):
    return hashlib.sha256(data).hexdigest()


def extract():
    blobs = []
    for name, digest in PINS.items():
        package = (ROOT / "build/late/transformer" / name).read_bytes()
        require(h(package) == digest, f"wrong {name} artifact")
        size = struct.unpack_from("<I", package, len(package) - 4)[0]
        start = package.index(b"FX2TFWC2")
        blob = package[start : start + size]
        require(h(blob) == WEIGHTS, "wrong decoded layout")
        blobs.append(blob)
    require(blobs[0] == blobs[1], "package copies differ")
    return blobs[0]


def sub(src, old, new):
    require(src.count(old) == 1, f"unexpected upstream source near {old!r}")
    return src.replace(old, new)


ORIG = """for (size_t k = 0; k < numel; k++)
          out[k] = int8_t(int(dec.decode_tree(m.int4.data(), 4)) - 7);"""
CANDIDATE = """uint16_t p[15]{};
        for (unsigned j=1; j<15; ++j) {
          uint8_t lo = side.u8();
          p[j] = uint16_t(lo | (unsigned(side.u8()) << 8));
          if (!p[j] || p[j] >= 2048) die("invalid static table");
        }
        for (size_t k=0; k<numel; ++k) {
          unsigned node=1;
          while (node<16) {
            int bit=0;
            if (node!=15) {
              uint16_t tmp=p[node];
              bit=dec.decode_bit(&tmp);  // discard adaptive update
            }
            node=2*node+unsigned(bit);
          }
          out[k]=int8_t(int(node)-16-7);
        }"""


def variant(src, mode):
    if mode == "original":
        return src
    if mode == "recode":
        src = '#include "transcode.hpp"\n' + src
        src = sub(
            src,
            "int bit;\n    if (code < bound)",
            "unsigned before = *prob;\n    int bit;\n    if (code < bound)",
        )
        src = sub(src, "return bit;", "trial::observed(before, bit);\n    return bit;")
        return sub(
            src,
            ORIG,
            "trial::in_weights=true;\n        "
            + ORIG
            + "\n        trial::in_weights=false;\n        trial::emit_tensor(out, numel);",
        )
    require(mode == "tables", "unknown mode")
    src = sub(src, '"FX2TFWC2"', '"FX2TFT01"')
    src = sub(
        src,
        "BinDecoder dec(r.p, r.left);",
        """uint32_t n_side=r.u32();
  r.need(n_side);
  Reader side{r.p, n_side, path};
  r.p+=n_side; r.left-=n_side;
  r.need(5);
  BinDecoder dec(r.p, r.left);""",
    )
    src = sub(
        src,
        "return wf;\n}\n\n}  // namespace\n",
        'if (side.left) die("unused table bytes");\n  return wf;\n}\n\n}  // namespace\n',
    )
    return sub(src, ORIG, CANDIDATE)


def build(mode, src):
    unit = BUILD / (mode + ".cpp")
    unit.write_text(variant(src, mode))
    defines = ["-DRECODE"] if mode == "recode" else []
    sp.run(
        [
            "g++",
            *FLAGS,
            *defines,
            "-I",
            FIX,
            "-I",
            TOOLS,
            unit,
            FIX / "weights_io.cpp",
            TOOLS / "main.cpp",
            "-o",
            BUILD / mode,
        ],
        check=True,
    )


def run(exe, args, dest):
    # Known hashes only, no network or other home-directory files. One core.
    with dest.open("wb") as out:
        proc = sp.run(
            [
                "bwrap",
                "--unshare-all",
                "--die-with-parent",
                "--clearenv",
                "--ro-bind",
                "/usr",
                "/usr",
                "--symlink",
                "usr/lib",
                "/lib",
                "--symlink",
                "usr/lib64",
                "/lib64",
                "--dir",
                "/trial",
                "--ro-bind",
                BUILD / exe,
                "/trial/" + exe,
                "--ro-bind",
                BUILD / args[0],
                "/trial/" + args[0],
                "--chdir",
                "/trial",
                "/trial/" + exe,
                *args,
            ],
            check=False,
            stdout=out,
            stderr=sp.PIPE,
            timeout=90,
        )
    require(proc.returncode == 0, f"{exe} failed: {proc.stderr[:1000]!r}")
    return proc.stderr.decode().strip()


def main():
    rev = sp.check_output(["git", "-C", UP, "rev-parse", "HEAD"], text=True).strip()
    require(rev == SRC_PIN, "wrong source; checkout the pinned revision")
    sp.run(
        ["git", "-C", UP, "diff", "--exit-code", "HEAD", "--", "cpp_infer/src"],
        check=True,
    )
    BUILD.mkdir(parents=True, exist_ok=True)
    original = extract()
    (BUILD / "v2.bin").write_bytes(original)
    src = (FIX / "weights_io_compressed.cpp").read_text()
    for mode in ("original", "recode", "tables"):
        build(mode, src)
    run("recode", ["v2.bin", "original"], BUILD / "roundtrip.bin")
    require(
        (BUILD / "roundtrip.bin").read_bytes() == original,
        "v2 encoder did not reproduce the award model",
    )
    log = run("recode", ["v2.bin", "tables"], BUILD / "static.bin")
    tensors, side, symbols = map(int, log.split())
    run("original", ["v2.bin"], BUILD / "original.dump")
    run("tables", ["static.bin"], BUILD / "tables.dump")
    dump = (BUILD / "original.dump").read_bytes()
    require(dump == (BUILD / "tables.dump").read_bytes(), "decoded tensor mismatch")
    candidate = (BUILD / "static.bin").read_bytes()
    require(
        struct.unpack_from("<I", candidate, 12)[0] == side and side % 28 == 0,
        "side-accounting mismatch",
    )
    old, new = [(BUILD / arm).stat().st_size for arm in ("original", "tables")]
    result = {
        "source": rev,
        "compiler": sp.check_output(["g++", "-dumpfullversion"], text=True).strip(),
        "flags": FLAGS,
        "original_bytes": len(original),
        "candidate_bytes": len(candidate),
        "original_sha256": h(original),
        "candidate_sha256": h(candidate),
        "baseline_reencoded_exactly": True,
        "all_tensors_identical": True,
        "tensors": tensors,
        "int4_tensors": side // 28,
        "int4_weights": symbols,
        "table_bytes": side,
        "extra_framing_bytes": 4,
        "canonical_dump_bytes": len(dump),
        "canonical_dump_sha256": h(dump),
        "old_standalone_decoder": old,
        "new_standalone_decoder": new,
        "both_copy_model_saving": 2 * (len(original) - len(candidate)),
        "projected_net_with_standalone_delta": projected_saving(
            len(original), len(candidate), new - old
        ),
        "corpus_run": False,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
