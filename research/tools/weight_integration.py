"""Measure packed releases, then exercise only a synthetic predictive stream."""

import hashlib
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "build/wt-integration"
T = struct.Struct("<4I")
ARMS = ["baseline", "candidate"]


def need(ok, why):
    if not ok:
        raise ValueError(why)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def meta(b):
    return {"bytes": len(b), "sha256": sha(b)}


def parts(b, archive):
    d, o, c, w = T.unpack(b[-16:])
    need(d > 0 and o > 0 and w > 0 and (c > 0) == archive, "invalid header")
    stored_order = 0 if archive else o
    k = len(b) - T.size - d - stored_order - w - c
    need(k > 0 and b.startswith(b"\x7fELF"), "invalid core")
    i = k + d
    j = i + stored_order
    return (b[:k], b[k:i], b[i:j], b[j : j + w], b[j + w : -16], o)


def assemble(core, dictionary, order, weights, payload, order_size):
    return b"".join(
        (
            core,
            dictionary,
            order,
            weights,
            payload,
            T.pack(len(dictionary), order_size, len(payload), len(weights)),
        )
    )


def pack():
    manifest = {
        f.split("\t")[0]: f.split("\t")[2]
        for f in (ROOT / "research/tools/late-artifacts.tsv").read_text().splitlines()
    }
    donor = {}
    for name in ["cmix", "archive9"]:
        b = (ROOT / "build/late/t-fixed" / name).read_bytes()
        need(sha(b) == manifest["t-fixed/" + name], "wrong donor")
        donor[name] = parts(b, name == "archive9")
        need(assemble(*donor[name]) == b, "donor layout mismatch")
    x, y = donor["cmix"], donor["archive9"]
    need(x[:2] == y[:2] and x[3] == y[3] and x[5] == y[5], "inconsistent donor")
    result = {
        "donor": "t-fixed",
        "corpus_payload": meta(y[4]),
        "dictionary": meta(y[1]),
        "order": meta(x[2]),
    }
    reference = json.loads(
        (
            ROOT / "research/experiments/transformer-weight-tables-result.json"
        ).read_text()
    )
    for arm, weightfile, key in zip(
        ARMS, ["v2.bin", "static.bin"], ["original", "candidate"], strict=True
    ):
        p = W / arm
        core = (p / "core").read_bytes()
        weights = (ROOT / "build/weight-tables" / weightfile).read_bytes()
        need(sha(weights) == reference[key + "_sha256"], "weight failed reference hash")
        if arm == "baseline":
            need(weights == x[3], "donor model differs")
        row = {"core": meta(core), "weights": meta(weights)}
        for name, obj in donor.items():
            out = p / name
            components = (core, obj[1], obj[2], weights, obj[4], obj[5])
            out.write_bytes(assemble(*components))
            out.chmod(0o755)
            disk = out.read_bytes()
            need(
                parts(disk, name == "archive9") == components, "pack readback mismatch"
            )
            row[name] = meta(disk)
        row["combined"] = row["cmix"]["bytes"] + row["archive9"]["bytes"]
        result[arm] = row
    net = result["baseline"]["combined"] - result["candidate"]["combined"]
    result.update(net_bytes_saved=net, added_nonweight_bytes=52806 - net)
    return result


def sandbox(out, mounts):
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
        str(out),
        "/w",
        "--chdir",
        "/w",
    ]
    for n, f in mounts.items():
        cmd.extend(["--ro-bind", str(f), "/w/" + n])
    return cmd


def box(parent, label, mounts, argv):
    out = parent / label
    out.mkdir()
    cmd = sandbox(out, mounts)
    with (parent / (label + ".log")).open("wb") as log:
        subprocess.run(
            [*cmd, *argv], check=True, stdout=log, stderr=subprocess.STDOUT, timeout=240
        )
    return out


def test_predictive():
    sizes = json.loads((W / "packages.json").read_text())
    need(sizes["net_bytes_saved"] > 0, "size gate failed; do not run codec")
    trial = Path(tempfile.mkdtemp(prefix="predict-", dir=W))
    print("Scratch:", trial, file=sys.stderr, flush=True)
    sample = (bytes(range(205)) * 50)[:10240]
    fixture = trial / "fixture"
    fixture.write_bytes(sample)
    need(
        sha(sample)
        == "443f66215cc8c604ef1f20e651da6af53f93e122528b153cbca4f8564cc2e8d5",
        "fixture mismatch",
    )
    report: dict[str, object] = {"input": meta(sample)}
    streams = []
    traces = []

    def program(arm, name):
        f = W / arm / name
        b = f.read_bytes()
        need(meta(b) == sizes[arm][name], "package changed since weigh-in")
        model = trial / (arm + "-" + name + ".weights")
        model.write_bytes(parts(b, name == "archive9")[3])
        return {name: f, "weights": model}

    for arm in ARMS:
        stage = box(
            trial,
            arm,
            dict(program(arm, "cmix"), sample=fixture),
            [
                "./cmix",
                "-n",
                "sample",
                "stream",
                "--transformer",
                "weights",
                "--save-transformer-probs",
                "trace",
            ],
        )
        s = (stage / "stream").read_bytes()
        t = (stage / "trace").read_bytes()
        n = int.from_bytes(s[:5], "big")
        need(
            n == len(sample) + 5
            and len(s) > 37
            and sum(b.bit_count() for b in s[5:37]) == 205,
            "not expected predictive stream",
        )
        need(
            len(t) > 0 and len(t) % (205 * 2) == 0 and any(t),
            "missing transformer trace",
        )
        streams.append(s)
        traces.append(t)
        report[arm] = {
            "header_length": n,
            "payload": meta(s),
            "probability_trace": meta(t),
            "rows": len(t) // 410,
        }
    dec = box(
        trial,
        "decode",
        dict(program("candidate", "archive9"), stream=trial / "candidate/stream"),
        ["./archive9", "-d", "stream", "out", "--transformer", "weights"],
    )
    restored = (dec / "out").read_bytes()
    report.update(
        payloads_equal=streams[0] == streams[1],
        traces_equal=traces[0] == traces[1],
        decoded_equal=sample == restored,
        restored=meta(restored),
    )
    report["verdict"] = (
        "keep"
        if all(report[k] for k in ("payloads_equal", "traces_equal", "decoded_equal"))
        else "reject"
    )
    return report


if __name__ == "__main__":
    actions = {"packages": pack, "predictive": test_predictive}
    mode = sys.argv[1]
    result = actions[mode]()
    data = json.dumps(result, indent=2) + "\n"
    (W / (mode + ".json")).write_text(data)
    print(data, end="")
