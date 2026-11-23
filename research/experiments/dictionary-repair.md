# Dictionary repair and native prefix gate

The unchanged `t-fixed/cmix -c` produced a 100,096 B stream, equal in length to the embedded stream but first differing at compressed offset 181. In separate empty sandboxes the published program and the label candidate recovered all 411,996 reference bytes from the fresh stream. [Receipt](dictionary-fresh-result.json). Replace only the dictionary in the 100,299,932 B pair, charging both copies. This is a compatibility repair, not an optimization.

Native startup of the repaired pair recovered the correct dictionary in both programs and the pinned complete order in the compressor. The argument-less archive reached the raw 65,536-byte stop but failed the old prefix comparison; the extracted complete corpus payload and weights are unchanged. No size experiments before all gates pass.

## Prefix discrepancy: paired diagnostic, before measurement

The earlier prefix harness gives `-d` an explicit dictionary file named `dictionary`. In native archive startup the same bytes exist under `.dict`. The model independently opens `.dict` in `fxcmv1.cpp:420`. Compare (a) the repaired argument-less archive, (b) explicit `-d` with recovered assets and no `.dict`, (c) the identical explicit call with a read-only alias `.dict` to the very same recovered bytes. Keep package, complete payload and weights fixed. Save and compare all exact-length prefixes, including the old pinned reference, with first differing offsets. Separately exercise the short predictive fixture even if the native prefix fails. If (b) matches the old reference and (c) matches native but not (b), the reference was obtained in a different model configuration; do not change it or claim a passing baseline. If the alias does not separate the arms, do not assign this cause. Stop on an unresolved native compatibility gate; no corpus run.

## Result: keep the dictionary repair; working baseline blocked

Both unmodified startup checks accepted the new embedded dictionary. The compressor restored the complete 1,094,862 B article order. On the 10,240 B fixture the encoder reproduced the reference 203 B predictive stream and the isolated decoder restored the input exactly. Weighed on disk: compressor **3,359,519 B**, self-extracting archive **96,940,413 B**, total **100,299,932 B**. Repair cost was **0 B** after counting both dictionary copies; this is not a compression saving. The 93,768,588 B corpus payload, including its header, remained byte-identical.

| Decoder invocation (same repaired archive and recovered assets) | Raw bytes captured | Compared with the pinned prefix |
|---|---:|---|
| Normal archive startup; only the archive mounted | 65,536 | First mismatch at offset 6: native `0x33`, reference `0x34` |
| Explicit `-d`, dictionary passed as `dictionary`, no `.dict` | 65,536 | Exact match |
| Same explicit command plus `.dict` alias | 65,536 | Exact match to **native**; differs from pinned at offset 6 |

All three stopped at the byte limit, not a timeout. The alias alone switched the result; an identical dictionary argument does not guarantee an identical prediction model. The [earlier receipt](transformer-donor-prefix-result.json) remains valid for its explicit invocation, not as ground truth for normal archive startup. No reference bytes were replaced. Neither the differing native prefix nor the matching explicit prefix establishes what the donor encoder consumed. [Measured sizes, checks and paired diagnostic](dictionary-repaired-pair-result.json).

**Stop decision:** no pair passed every requested check. Zero new size experiments ran; savings against a working baseline are undefined. Before optimizing, an independent reference is needed for the encoder-side predictive input or for a known-good native donor decode. No full enwik9 encode or decode was launched.

**Reproduce:** start from the hash-pinned label pair and retained published 65,536-byte prefix from the preceding experiments. Under `systemd-run --quiet --user --scope -p MemoryMax=8500M -p MemorySwapMax=0 taskset -c 2`, run `python3 -m research.tools.dictionary_repair "$LABEL_PAIR"`, then `python3 -m research.tools.repaired_pair "$LABEL_PAIR" "$FRESH/encode/stream" "$PUBLISHED_PREFIX"`, where `$FRESH` is the first script's printed output directory. Use a free CPU. The harness runs serialized offline sandboxes with per-process wall limits and retains `blocked.json` rather than emitting `baseline.json` when the native prefix differs.
