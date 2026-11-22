# Mid-series replay: awards 6–8

**Result:** Three published x86-64 Linux self-extracting archives obtained and SHA-256 pinned. All three executed a small stored-block round trip in a network-isolated sandbox on the Ryzen 7 5700X3D. Only fast-cmix ran natively; fx-cmix and fx2-cmix needed instruction emulation. **Neither full decompression nor full recompression was started.** The probe tests startup, child invocation, file I/O and stored-data restoration, not the adaptive predictor or the Wikipedia inverse transform.

## Parent entry points

From `/home/siheon/projects/hutter-prize`:

```sh
research/tools/mid-replay.sh probe       # cheap; default if no args
research/tools/mid-replay.sh full        # published archive -> 1 GB -> size + SHA-256, sequential 6,7,8
research/tools/mid-replay.sh recompress  # stronger alternative: reconstruct compressor, encode, cmp SFX, then full restore
```

Run **one** of the last two only in the parent's serial RAM slot. Append `fast`, `fx` or `fx2` to select one entry. The lock prevents overlap between these scripts only. Allow tens of GB of scratch per entry and many hours/days; emulated timing is not prize timing. `build/mid/{probe,full,recompress}.XXXXXXXX/` contains fresh per-entry working directories; failed jobs retain scratch for diagnosis. Successful full runs keep `/usr/bin/time -v` reports, logs and the restored corpus. Required: Linux x86-64, unprivileged bwrap namespaces, GNU time/coreutils, curl, flock, Python 3, tar/xz; optional recompression also needs git and `data/enwik9`. There is no sudo, binfmt registration, or container service.

Full decode never sees `data/enwik9`: the original executable is mounted read-only under the literal working-directory name `archive9` used by the self-extractor. Only a fresh work directory is writable on the host; `/usr` is read-only, `/tmp` private, network/PID namespaces isolated and capabilities dropped. A zero exit alone does not pass: output must be 1,000,000,000 bytes, SHA-256 `159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc` (also measured on local `data/enwik9`).

## What was actually downloaded

| Entry | Immutable local bytes / source | Bytes | Measured SHA-256 |
|---|---|---:|---|
| 6 fast-cmix | `fast.archive`, [Mahoney archive mirror](https://mattmahoney.net/dc/fastcmix.archive9) | 113,746,218 | `158402125b94a923939463089ac108736c38f80df6f9af70c6b3813141d56234` |
| 7 fx-cmix | `fx.archive`, [submitter's archive9](https://drive.google.com/file/d/14gjz045biXxjq4TuurRpvb5-wAFILbec/view) | 112,142,259 | `5fb56eb2488dbb834a8b5903d9f853768303271b0f3602e17e22d27da59ad6c6` |
| 7 separate compressor | `fx.comp`, [fx-cmix-v1 release](https://github.com/kaitz/fx-cmix/releases/download/fx-cmix-v1/cmix) | 436,707 | `d542c8d6a36e4025595a220912d0fc0642742bdc75dfb49fa6b3b50489263373` |
| 8 fx2-cmix | `fx2.archive`, [authors' archive9](https://drive.google.com/file/d/14QillUEElT5vR0ttmayRAXlciXuPwDWm/view); direct download independently matched the existing cache | 110,351,665 | `9e733afa3870eb3278a1349626f665ddb5c5105f3158c3cc61adb5adec442569` |

These are local content pins, not organizer-signed digests. For #6 the Drive file in [the author's benchmark](https://github.com/saurabhk/fast-cmix/blob/e196e65fa09b2e655e8fb74e6c9944c2fc27eced/Benchmark.md) returned HTTP 404 and the `execs` folder presented an empty listing. The [benchmark mirror listing](https://mattmahoney.net/dc/text.html#1137) and author's size agree. For #7, the [submission PDF](https://drive.google.com/file/d/1JKUNzNXSGdKe0X2ZXdrcgBkYnD0dlpTn/view) and [README](https://github.com/kaitz/fx-cmix/tree/2af9836d17c24134a6c8c8ea9b99d6c13c34b720) report a **different** archive, 112,148,343 bytes. The release compressor plus the *downloaded* archive sum to 112,578,966, not the [official](https://www.hutter1.net/prize/#prev) 112,578,322. Do not claim a prize-matched pair. For #8 the measured archive matches the [published S2](https://github.com/kaitz/fx2-cmix/tree/04c5806f99b9b0fa8572be8c8063b4324ec405de); no independently downloaded compressor is claimed.

## Compatibility evidence

* With runtime libraries absent all four downloaded ELF probes exited 127. Binding `/usr` and the standard library symlinks fixed that for fast.archive and fx.comp (`-h 11 22 33`, status 0); both fx archives instead exited 132 (SIGILL). The separate #7 release and public archive are not interchangeable evidence.
* Unprivileged Ubuntu QEMU user 10.2.1, `-cpu max`, still exited 132 on both fx archives. [Intel SDE 10.13.1](https://downloadmirror.intel.com/924984/sde-external-10.13.1-2026-07-28-lin.tar.xz), tarball SHA-256 `94e97d623fec54385686e1e7ba65ebc9941748c05ee451423948334892bf2b50`, with `-skx --`, passed on both. No executable bytes were patched. The script verifies the tarball before extracting it.
* `build/mid/probe.log`, `probe.OhGFV0qr/{fast,fx,fx2}/`: child launched via `/bin/sh -c` wrote the correct 12 little-endian header bytes; all three `-s sample stored` / `-d stored restored` pairs passed `cmp`. Child coverage matters: dictionary decode uses `system("./archive9 -d ...")`. The smoke input bypasses the large model; no historical score, peak memory or run time was verified.

## Recompression and the native build

The [upstream layout](https://github.com/kaitz/fx2-cmix/blob/04c5806f99b9b0fa8572be8c8063b4324ec405de/src/readalike_prepr/self_extract.h) lets us reuse the exact packed ELF and packed dictionary from each archive. The order is *not* in the archive. `recompress` compresses the source-pinned order with that ELF, checks its length against the trailer, appends the compressor trailer, and accepts the subsequent enwik9 encoding **only** if its complete archive is byte-identical. It then runs the clean decode check. This is a queued test, not an assertion that order reconstruction or floating-point predictions will match. The header-implied reconstructed compressor sizes are 409,937, 438,704 and 441,463 respectively. Only #6 and #8 agree with published compressor sizes. For #7 this path targets the downloadable archive, not the separate GitHub compressor. The source commits in the script pin the order bytes; no compiler or pretraining is required on this path.

`research/tools/mid-build-fx2.sh` separately reproduced an **unprivileged native research build**, not a replacement for the public archive. It extracted four SHA-pinned Ubuntu resolute amd64 Clang/LLVM packages (`1:17.0.6-23ubuntu7`) under `build/mid/tc`, using host system headers/linker; no system packages changed. The ordinary build failed on undeclared `uintptr_t`; `-include cstdint` fixed that without editing upstream. Clang 17 + `ZEN2=1`, upstream seed 923/update limit 3000, no PGO/LTO/UPX: raw ELF 279,728 bytes, SHA-256 `039854dc4875a095925bdf50f454c17091448794ac71cbfd04eb67fece261541`, identical from two builds. Its sandboxed header probe returned `(66,77,88)`. It is neither the 441,463-byte packaged compressor nor proof of entropy-stream compatibility. Debian package digests and exact build command are in the executable helper.
