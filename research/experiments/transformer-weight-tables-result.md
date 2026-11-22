# Result: save 26,403 bytes per transformer weight copy

**Keep the change for integration. Do not schedule an enwik9 run just for it.** The [preregistered](transformer-weight-tables.md) static probability tables compressed the complete July award model better than its adaptive bit tree. This is not an extrapolation from a corpus slice. Equally, it is not a new eligible whole-package score.

| Measured quantity | Bytes |
|---|---:|
| Original weight object, reproduced byte for byte | 2,930,652 |
| Candidate weight object, tables and framing included | 2,904,249 |
| Range-coded stream reduction, before paying for tables | 29,515 |
| 111 probability tables × 28 B plus 4 B framing | 3,112 |
| Net object saving per copy | 26,403 |
| Model saving across compressor and self-extractor | 52,806 |

The candidate re-encodes 5,868,864 quantized weights without retraining. Both loaders produced the same 39,617,261-byte canonical dump: ordered names, dtypes, dimensions and raw data for **all 434 tensors**, not just the 111 changed ones. Each loader received only its executable, its own weight file and system libraries in an offline sandbox. The baseline encoder also regenerated the original award weight bytes exactly. The isolated experiment including three compilations took 5.83 seconds, on one pinned CPU, with reported peak RSS 119,320 KiB. This is not a timing measurement of the prize compressor. See the [measurement receipt](transformer-weight-tables-result.json).

**What the code costs.** The stripped standalone reader binaries were both 35,032 B. GNU `size` nevertheless reports `text` 20,090 → 20,560 B (+470); file alignment can hide code growth. Both loaders are needed in production because the same learned weights are loaded on encode and decode. The offline recoder is a preparation tool, not needed to use the weights. The new table decoder and all data do have to ship. With no other changes, the exact condition for a positive total saving is **combined incremental packaged code/framing < 52,806 B**, or <26,403 B per copy if identical. The measured proxy implies 52,806 B saved against a preregistered forecast of 29,000 B. The actual integrated code delta is unknown; do not treat the proxy as a package measurement.

**Decision.** At the unchanged-code proxy the 100,424,672 B baseline would drop to 100,371,866 B, only 0.0526%. Another 951,441 B would be required for the formal 1% minimum. The next discriminating test is matched builds with the actual release packing flags, changing only the weight loader and object; weigh both charged artifacts and check that a predictive (not stored-mode) encode/decode produces the same payload and bytes on a compatible CPU. Abandon if the real code consumes the saving or any tensor/prediction differs. A full replay would still be necessary before claiming eligibility, but is not the best next use of the machine. No existing long run was restarted.

## Reproduction

Obtain the **July** `cmix` and `archive9` files as in [the replay report](late-replay.md) and place them in `build/late/transformer/`. Clone `https://github.com/astOwOlfo/fx2-cmix-transformer-v1` to `build/weight-research-src/` and check out `83f2603f3f7751da5f429fd32669807eb8510494`. On little-endian x86-64 Linux with GCC, bubblewrap and the stated inputs, use:

```
taskset -c 2 prlimit --as=700000000 -- python3 research/tools/weight_tables.py
size build/weight-tables/{original,tables}
```

Use an available CPU instead of 2 if necessary. The script checks both award hashes, the model digest, the pinned source revision and the clean upstream loader source before building. The pinned checkout is a source for the v2 loader, not a claim that it recreates the original July executable. The result was repeated with isolated file mounts; the JSON receipts matched. The project's daily economy-worker cap was already reached when a bounded source query was routed. No fallback model was invoked; the scope of the result comes from the byte comparisons, not testimony.
