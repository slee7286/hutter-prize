# Late enwik9 replay: downloaded packages, not reproduced scores

**Handoff:** On this AMD Ryzen 7 5700X3D, the public lex and obias packages and the *fixed* transformer package can exchange a 4 KiB stored stream in offline Bubblewrap. The **award-size transformer compressor fails at startup** on this machine. No billion-byte encode or decode was launched. The smoke test deliberately avoids allocating the ~10 GB predictor; it is not evidence that any full payload has been reproduced.

| Entry and artifact tested | Measured S1 (B) | Downloaded SFX archive9 (B) | Package total (B) | [Official total](https://www.hutter1.net/prize/#prev) (B) |
|---|---:|---:|---:|---:|
| cmix-lex, public Intel package | 459,938 | 109,190,109 | 109,650,047 | 109,671,639 |
| cmix-obias, public `final/` AMD package | 459,989 + 23,002 weights | 108,009,834 | 108,492,825 | 108,521,870 |
| fx2-cmix-T, July award-size pair | 3,428,474 | 96,996,198 | 100,424,672 | 100,424,672 |
| fx2-cmix-T, August fix on GitHub | 3,426,642 | 96,994,188 | 100,420,830 | not a separate award |

[Artifact manifest](../tools/late-artifacts.tsv): each row is `cache-relative path`, **measured bytes**, **SHA-256**, **exact retrieval URL**. Inputs live under `build/late/`. The [lex README](https://github.com/blahem/cmix-lex/blob/370e698f7ea62168cc64326ff97950c3dc212691/README.md) publishes matching hashes; [Mahoney](https://mattmahoney.net/dc/text.html#1091) identifies the scored AMD rebuild (470,599 + 109,201,040). The [obias final manifest](https://huggingface.co/dfreelan/cmix-obias/blob/51488a0c1228dbeab7c1be837fc90ceaed351728/final/README.md) identifies the extra head weights charged to the encoder; the archive already contains its own copy. Its public components do not establish a split of the ranked total. [Mahoney’s transformer version table and Drive links](https://mattmahoney.net/dc/text.html#0969) distinguish the July pair from the [later release](https://github.com/astOwOlfo/fx2-cmix-transformer-v1/releases/tag/binaries). The table above uses on-disk sizes, not inner payloads.

## Local smoke evidence

`python3 research/tools/late-replay.py smoke` takes the first 4,096 bytes of `data/enwik9`, runs `./cmix -s sample stored`, then runs `./archive9 -d stored restored` in a **different** offline namespace and checks size and SHA-256. No full data or source directory is mounted for either smoke stage. `-s` exercises the preprocessor/storage path, not predictive coding, article reordering, model weights or bare SFX decode. The `-d` executable is the fetched archive, not a second invocation of the fetched compressor.

| Artifact | Store → restored | Store/decode wall seconds | Store/decode peak RSS (KiB) | Raw logs under `build/late/` |
|---|---|---:|---:|---|
| lex | 4,107 → 4,096 B, matched | 0.01 / 0.01 | 5,884 / 6,024 | `smoke-lex-n9igf4tw/` |
| obias | 4,107 → 4,096 B, matched | 0.01 / 0.01 | 5,816 / 5,820 | `smoke-obias-svwt0rs5/` |
| transformer original | no stream; SIGILL (process status 132) | 0.09 / — | 3,988 / — | `smoke-transformer-6go5y204/` |
| transformer fixed | 4,107 → 4,096 B, matched | 0.00 / 0.00 | 5,024 / 5,020 | `smoke-t-fixed-v13fm9xh/` |

The three successful restored outputs have SHA-256 `652ed0541c8b9e2d8194c2a1cd20a3ea516efaa542082535c0ef57267e1ca49e`; the stored stream is `96af14732e59efa673d838fb9b931a22ada8f1eb7b19d8f6cdb8cd5883a065c6`. Times are GNU time readings rounded to hundredths. On the original transformer failure the signal and outer process status, not GNU time's `%x`, are authoritative. No instruction-level cause was established.

## Parent entry points (from repository root)

Follow-up: the July award-size transformer pair also passed the same 4 KiB stored-stream round trip using the mid-series Intel SDE installation (`REPLAY_USE_SDE=1 python3 research/tools/late-replay.py smoke transformer`; `build/late/smoke-transformer-of6kwir3/result.json`). This is not native execution or proof of predictive-stream compatibility. Prefer testing this award-size pair over silently substituting the August fix.

```sh
python3 research/tools/late-replay.py fetch       # fetch missing inputs; size/hash gate all
python3 research/tools/late-replay.py smoke       # safe store-mode test, serial
# ONLY when parent has granted the RAM/disk slot:
python3 research/tools/late-replay.py full lex obias t-fixed
```

`full` verifies canonical enwik9 SHA-256 `159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc`, runs `./cmix -e enwik9 out.cmix`, then executes **that generated** `./archive9` bare in fresh scratch without the source file, weights or encoder. It requires a 1,000,000,000-byte output with the canonical SHA-256 before advancing. The obias encoder receives `KH_BITLSTM32=/w/head.blob`. On AMD, lex repacks the original executable prefix with locally encoded dictionary/order streams and checks each stream decodes before using it; this addresses the [reported Intel-package self-extraction problem](https://huggingface.co/dfreelan/cmix-obias/blob/51488a0c1228dbeab7c1be837fc90ceaed351728/SUBMISSION.md). It is a **local variant**, not the official AMD rebuild. This preparation also needs the RAM slot and has not been run here. The transformer default is explicitly the fixed build, not the award-size one.

For just a downloaded-archive decode, use `python3 research/tools/late-replay.py decode-public obias` (or `lex`, `t-fixed`, `transformer` on a suitable CPU). To attempt the award-size transformer end-to-end on another host, use `python3 research/tools/late-replay.py full transformer`. These are full jobs. Reserve ~10 GB RSS plus filesystem cache, tens of GB of scratch, and days, not minutes. The lock serializes this runner only; it does not reserve resources against other suites. Each stage mounts `/usr` and its inputs read-only, private `/tmp`, and one writable working directory, with namespaces including network unshared. The runner retains generated archives, per-stage time/RSS logs and `result.json` in printed run directories; failed stages retain scratch and stop the sequence. Full timings, local package sizes and bit-exactness remain unmeasured until the parent runs it.
