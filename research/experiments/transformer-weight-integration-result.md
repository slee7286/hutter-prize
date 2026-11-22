# Keep: 52,022 bytes smaller in the matched release build

The [integration test](transformer-weight-integration.md) passed. These are **rebuilds**, not the exact award executables. Both carried the same 93,768,588-byte compressed corpus stream from the portable fixed release. It was copied, hashed and compared, never recompressed or decoded. On-disk measurements:

| Artifact | Baseline bytes | Candidate bytes | Net bytes saved |
|---|---:|---:|---:|
| Packed compressor (`cmix`) | 3,417,314 | 3,391,303 | 26,011 |
| Self-extracting archive (`archive9`) | 96,984,860 | 96,958,849 | 26,011 |
| **Combined** | **100,402,174** | **100,350,152** | **52,022** |

The packed executable core grew from 185,508 to 185,900 bytes. It ships twice: 784 B in all. The two weight copies saved 52,806 B including the new tables; all other components and trailer lengths stayed the same. See [package sizes and digests](transformer-integration-packages.json).

**Predictive test.** Both packed compressors encoded the fixed 10,240-byte input with `-n --transformer` using their own model extracted from their respective `cmix` files. Both produced a **203-byte payload**, byte-for-byte identical excluding any executable. Each stream's five-byte predictive length was 10,245 (a storage stream would say zero). The two recorded transformer traces also matched across all 10,245 probability rows. The packed candidate `archive9`, invoked with `-d --transformer` in a fresh offline sandbox, had its own model and the short compressed stream but not the original input or baseline files. The resulting 10,240 bytes compared equal to the input outside that sandbox. See [predictive receipt](transformer-integration-predictive.json).

**Scope.** Keep the [loader change](../tools/weight_tables/release-loader.patch) as a tested component. The synthetic case uses the real predictive mixer, not the specialized `-e` article pipeline. It does not establish that this particular rebuilt core decodes the fixed donor's enwik9 stream or that the combination is prize-eligible. No full corpus run was launched; no existing job was restarted.

## Repeating the comparison

Use a fresh private clone of `astOwOlfo/fx2-cmix-transformer-v1` at `83f2603f3f7751da5f429fd32669807eb8510494` in `build/wt-integration/src`. Fetch the `t-fixed` pair from [the pinned manifest](../tools/late-artifacts.tsv) into `build/late/t-fixed`, and use the two verified files from [the weight experiment](transformer-weight-tables-result.md). The [build driver](../tools/weight-integration-build.sh) expects the local UPX 5.1.1 executable and a private `build/wt-integration/sysroot` containing Ubuntu's extracted Clang/LLVM 17 packages. No system installation is required. Here the packages were `clang-17 libclang-cpp17t64 libclang-common-17-dev llvm-17-linker-tools libclang-rt-17-dev llvm-17 libllvm17t64` from Ubuntu 26.04, Clang 17.0.6 (23ubuntu7). The host headers required a common `-include stdint.h` for `uintptr_t`; neither arm had a source workaround. The release makefile, defines, PGO profile, LTO, CPU target, stripping and UPX `-9` packing were otherwise the same.

From the repository root on a compatible host, with a free RAM slot and the above inputs:

```
bash research/tools/weight-integration-build.sh profile
bash research/tools/weight-integration-build.sh baseline
git -C build/wt-integration/src apply "$PWD/research/tools/weight_tables/release-loader.patch"
bash research/tools/weight-integration-build.sh candidate
python3 research/tools/weight_integration.py packages
python3 research/tools/weight_integration.py predictive
```

The last command enforces the positive-size gate. The measured profile and predictive processes ran in a cgroup capped at 8,500 MiB with swap disabled. The build-generated profile came from the upstream's small PGO fixture; the synthetic comparison is separate.
