# Follow-on experiments: reduce the shipped package, not the slice score

## 1. Change only the release executable packing method (preregistered)

Start from the [kept static-table rebuild](transformer-weight-integration-result.md), 100,350,152 B, including a 185,900 B UPX `-9` core in each file. The [donor-prefix comparison](transformer-donor-prefix.md) is an existing control, not a new experiment. Test one alternative: UPX 5.1.1 `-9 --lzma` on the identical *unpacked* candidate ELF. The stub is self-contained and charged in each copy; models, order, dictionary, payload, and framing must not change. Expected saving: about 10,000 B per packed core, **20,000 net bytes** per pair. This takes seconds, needs no new prediction model and can be tested exhaustively on the changed object.

Reject if the incumbent `-9` control cannot be reproduced, unpacked ELF bytes differ, launch fails, or the measured combined on-disk saving is nonpositive. If smaller, assemble and re-read the two packages, do a bounded predictive round trip on the established synthetic fixture and compare against the existing reference payload digest. Do not decode the billion-byte corpus.

**Result: keep.** Both packed cores unpacked to the identical 454,936-byte ELF. `-9` reproduced the incumbent core exactly; `-9 --lzma` reduced it from 185,900 to 167,224 B including its runtime stub. Measured compressor 3,372,627 B + archive 96,940,173 B = **100,312,800 B**, **37,352 B saved**. The 203-byte predictive fixture payload matched the previous reference and the separate decoder restored the original input. This is a matched package weigh-in with a reused corpus stream, not a full replay. [Receipt](core-packing-result.json); run `python3 -m research.tools.core_packing` under the same one-core/8,500 MiB limits as the preceding integration test.
 
## 2. Store differences between article indices (preregistered after result 1)

The 100,312,800 B winning arm of experiment 1 still stores a 201,042 B compressed article-order list once, in the compressor. Its plain text starts with many neighboring indices decreasing; the reorderer consumes decimal values, not their spelling. Rather than alter the order (which would change predictions), difference adjacent values from a starting previous value of zero, zigzag the signed delta and write unsigned LEB128. Compress this binary stream with the already shipped `cmix -n` (no transformer, no store mode); add a tiny inverse at order extraction. All lines must be reconstructed byte for byte. Prediction: about 171,000 B for the new stream plus roughly 2,000 B for extra code across both packed cores, or **about 28,000 net bytes saved**. This is a forecast, not an entropy estimate from the data.

Cheapest falsifier: run on the complete list, decode the stream in isolation and compare reconstructed order text with the pinned source. Reject if equal or larger than 201,042 B even before charging the inverse, or if restoration fails. If smaller, integrate and weigh both cores before claiming package savings; reject if the combined saving disappears. The corpus stream, model and order of article processing are fixed.

**Result: reject.** The binary deltas reconstructed all 1,094,862 source bytes, yet cmix compressed them to **209,371 B**, 8,329 B *larger* than the incumbent, even with a free inverse. The small intermediate size (282,095 B) did not predict a smaller compressed file. No release rebuild or adoption. [Receipt](order-deltas-result.json).

## 3. Encode membership in descending runs instead of individual jumps (preregistered)

Experiment 2 failed despite 168,477 descending steps. The list contains 172,277 unique IDs, only 38 holes up to its maximum, and 3,800 maximal decreasing runs (median length 47). That suggests a different representation: for each numeric ID in ascending order, store which run contains it (1-based, zero for absent). Recover the original ordering by visiting runs in order and each run's IDs in descending order. Unlike deltas this cannot spend bits naming an already-used ID. This bets that neighboring source IDs have correlated run labels; if not, a 3,800-label alphabet is expensive.

Keep experiment 1's 100,312,800 B pair and 201,042 B order stream as control. One arm only: low bytes of all uint16 labels, then high bytes; split at half the decoded length, so no side table. Compress with the same existing `cmix -n`. Predict 185,000 B for the stream plus 2,000 B combined packed inverse overhead, approximately **14,000 net bytes saved**. Reject on any nonexact order restoration or stream size >=201,042 B; otherwise build and weigh both actual packed programs and require positive net savings after charging both cores. No full corpus runs.

**Asset result: integrate for measurement.** The complete label stream measured 187,694 B, 13,348 B below the incumbent. After native stream decode, inversion restored all 1,094,862 original text bytes. This leaves a strict 13,348 B break-even for all additional shipped code and framing; the asset saving is not the final package saving. [Receipt](order-labels-result.json).

**Package result: 12,868 B smaller; adoption blocked on this host.** The control rebuild reproduced the 167,224 B packed core. The label inverse increased it to 167,464 B: 240 B per shipped copy, 480 B in all. The new compressor is 3,359,519 B; the archive is 96,940,413 B; the pair is **100,299,932 B**. The same 93,768,588 B donor corpus payload was copied unchanged. The packaged compressor restored the entire pinned order text at startup. The short predictive stream matched the 203 B reference and decoded exactly. [Integrated sizes and checks](label-integration-result.json).

**Why the smaller pair is not a runnable result.** Control and candidate startups were first stopped deliberately *after* order restoration, at the dictionary stage. The label candidate matched the source order, but the control did not (first difference at zero-based byte 227). The published portable `t-fixed` executable and the earlier rebuild without the static-table loader produced the same incorrect order when decoding the donor order stream on this host. For the unchanged donor dictionary, those two executables and the label candidate produced the same 411,996 B, differing from the reference starting at byte 263. A separate run of the label candidate through normal `-e` startup, with an empty input and **no artificial stop**, exited 1 at its built-in dictionary hash check. The failure predates these changes; its underlying cause is not established. The previous [donor-prefix test](transformer-donor-prefix.md) supplied the verified plaintext dictionary, so its match did not test this prerequisite. [Control outputs and native error](order-controls-result.json).

**Series decision.** Keep the packing change as a component result; reject adjacent-index coding; retain run labels as a tested component but do not adopt the pair as a working release. The 50,220 B reduction from the starting 100,350,152 B is an on-disk difference, **not** a verified eligible saving. Stop at three experiments. No full enwik9 encode or decode; do not spend a full run before dictionary recovery passes without an external plaintext file or a disabled check.

### Repeat the bounded measurements

Use the existing verified weights, donor and private compiler/profile from the [integration setup](transformer-weight-integration-result.md#repeating-the-comparison). Run the modules from the repository root, serially, in a resource-limited scope (e.g. prefix each with `systemd-run --quiet --user --scope -p MemoryMax=8500M -p MemorySwapMax=0 taskset -c 2`, substituting a free CPU). Each prints a fresh output directory. `$PACK`, `$LABELS` and `$PAIR` below refer to directories printed by steps 1, 3 and 4 respectively.

```sh
python3 -m research.tools.core_packing
python3 -m research.tools.order_deltas "$PACK" deltas
python3 -m research.tools.order_deltas "$PACK" labels
python3 -m research.tools.label_integration "$PACK" "$LABELS"
python3 -m research.tools.order_controls "$PAIR"
```
