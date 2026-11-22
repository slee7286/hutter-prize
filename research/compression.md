# Compression research for the Hutter Prize

**Decision:** Use gzip to test byte fidelity, a small adaptive model to test ideas cheaply, and an accepted `cmix`-family entry to test competitiveness. The quantity to minimize is **bytes the entrant must supply**, not archive size or language-model perplexity. As of 22 November 2026 the official record is Vladimir Ivanov’s **100,424,672 bytes** (`fx2-cmix-T`, 24 July 2026); the next qualifying improvement is roughly one million **net** bytes.[1][2]

## What counts: a worked prize ledger

The input is the first **1,000,000,000 bytes** of the uncompressed 3 March 2006 English Wikipedia dump, not the distribution ZIP, not a GiB, and not enwik8 (the first 100,000,000 bytes). The corpus maintainer publishes lengths and hashes; enwik9’s MD5 is `e206c3450ac99950df65bf70ef61a12d`.[4]
The ordinary score is `S = C + A`: compressor size plus the *entire self-extracting archive*. The latter already contains its decoder. The archive must regenerate the exact input without other files, dictionaries, installations or network access; standard libraries such as file I/O are allowed.[2]

| Submission form | Charged bytes (before any required option text) |
|---|---:|
| Compressor producing a self-extractor | `C + A` |
| Separate compressor, decoder, raw payload | `C + 2D + P` |
| Identical program used for both, raw payload | `2C + P` (the decoder term drops from `2D` to `D = C`, not to zero) |

These are the organizer’s alternatives, not three ways to score the same `.gz` in isolation. Eligible zipped source plus makefile can stand in for the corresponding executable; required command-line options for compilation or execution add length. A smaller executable or source ZIP can therefore matter even when it emits the same bitstream.[2]

* **Target.** The formula is `award = €500,000 × (1 − S/L)`, minimum €5,000. With `L = 100,424,672`, the formula gives `floor(99L/100) = 99,420,425` bytes and a saving of **1,004,247 bytes**. The leaderboard’s prospective row prints a strict `<99,420,425`; aim below it rather than rely on its rounded boundary. Recheck `L` before a claim.[1][2]
* **Payload allowance.** Suppose a self-extracting entry charges 3,500,000 bytes for the compressor and 500,000 for decoder, metadata and framing inside the archive. The formula leaves **95,420,425 bytes** for coded data, before any option text. With distinct programs of those same sizes and a separate payload, the decoder counts twice: the allowance falls to **94,920,425**. These are hypothetical sizes, not measurements.
* **A better predictor can lose.** Across enwik9, a gain of 0.020 bits per original byte (bpb) saves `0.020 × 10^9 / 8 = 2,500,000` payload bytes. If the charged model grows by 3,000,000 bytes in total, the entry is **500,000 bytes worse**. From the record, with that overhead, the new predictor must save at least 4,004,247 bytes, about **0.03204 bpb**, merely to reach the formula threshold. Do not count a weight file once if it actually appears in both charged artifacts.
* **Time and space.** The detailed runtime limit is **per program**, less than `70,000/T` hours for Geekbench 5 score `T`; use the official single-core reference, no GPU, at most 10 GB RAM and 100 GB temporary disk. At `T = 1427` this is 49.05 h; a nominal 50 h pass must average 5,556 original bytes/s including preprocessing and I/O. For memory planning, `2^28` context slots at 24 bytes occupy **6.44 GB** before collision metadata, allocator overhead, model weights, buffers or sorting workspace. Measure peaks for encoding and decoding separately; neither a fast encoder nor free disk compensates for an over-budget decoder.[1][2]

## What the theory buys

Shannon’s entropy is an expected limit for a specified source distribution, not a known lower bound on the shortest program printing this particular file.[5]
For actual bytes `x₁…xₙ`, factor a model’s probability into next-symbol probabilities. Its ideal payload length is `−log₂ Q(x₁…xₙ) = Σᵢ −log₂ Q(xᵢ | x₁…xᵢ₋₁)`. Predicting the observed symbol at probability 1/2 costs one ideal bit; predicting it at 1/16 costs four. Under a true distribution `P`, expected log loss is entropy plus the nonnegative mismatch penalty `D_KL(P || Q)`. Experimentally one needs neither `P` nor an entropy estimate: accumulate log loss on the actual symbols and divide by **original input bytes**. This stays comparable across byte, bit and token predictors provided one charges the reversible mapping and its side information.[3][5][12]

A prefix code such as Huffman assigns integer bit lengths to individual symbols. Arithmetic coding instead narrows an interval in proportion to each predicted probability, so many fractional-bit events can share the cost of one final binary representation. A range coder implements that idea with bounded integers and renormalization.[6]
Log loss predicts stream length, not file length. Measure the gap: quantized cumulative frequencies, block restarts, headers, the final interval and padding all matter. Keep every possible symbol encodable, for example by assigning a positive count or reserving an escape. Both sides must use *exactly* the same cumulative counts **before** coding each symbol, then update in the same order. A predictor seeing even one future byte can look excellent in a notebook while producing a stream no decoder can read.

The organizer’s FAQ frames the trade as two-part description length: pay for the model **and** for the data given the model.[3]
Online adaptation builds state from already decoded bytes: no need to transmit a table the decoder can rebuild, but both sides pay for the updates and early predictions start cold. Offline fitting can shift training off the timed path, but the weights and inference machinery must travel with the submission. Token perplexity alone hides both that cost and the number of tokens per original byte. Even an oracle payload estimate is not the Hutter score.

## Algorithm choices, in the order worth testing

| Family and primary reading | Mechanism | What to try on enwik9; what can go wrong |
|---|---|---|
| Ziv & Lempel, *A Universal Algorithm for Sequential Data Compression* (1977)[9] | Replace text already in a sliding history with distance/length references. A parser chooses between literals and copies. | XML scaffolding and repeated links give exact copies. Longer history can recover distant matches but increases search and memory costs; compare actual coded costs, not just matched bytes. |
| Burrows & Wheeler, *A Block-sorting Lossless Data Compression Algorithm* (1994)[21] | Sort rotations and emit their last column plus a primary index. This permutation does not shorten the block: it groups symbols with similar right contexts so move-to-front and entropy coding can exploit locality. | A block sorter is a useful alternative when words recur in similar contexts but exact phrases do not. Charge the index and block headers; increasing block size increases sort workspace and cannot exploit repetitions across block boundaries. |
| Cleary & Witten, *Data Compression Using Adaptive Coding and Partial String Matching* (1984)[20] | PPM estimates the next symbol from suffix counts, escaping to shorter contexts when the longest one lacks the symbol. | Start with bounded byte contexts and a uniform fallback. Log escape bits separately: higher order predicts repeated markup precisely but wastes bits and nodes on unique prose. |
| Willems, Shtarkov & Tjalkens, *The Context-Tree Weighting Method* (1995)[8] | Recursively mix the likelihood of a short-context model with the product of its children’s likelihoods rather than committing to one suffix depth. | A bounded-depth binary tree is a principled variable-order control for PPM. Its guarantee concerns a specified model class, not automatic wins on Wikipedia; cap depth and track node growth. |
| Knoll, `cmix`; Ivanov, `fx2-cmix-T`[11][22] | Combine next-bit estimates from different predictors rather than choosing one text model for everything. A match expert, suffix expert and word-context expert may succeed at different positions. | Measure the **incremental** loss change with each expert disabled. A strong standalone predictor can be redundant with the mixer; a cheap weak one can win specifically after a link delimiter. |
| Delétang et al., *Language Modeling Is Compression*; Ivanov’s submission write-up[12][22] | A causal language model supplies probabilities to an entropy coder. Ivanov replaced an online LSTM with a 6M-parameter pretrained byte transformer, retaining the statistical ensemble. The author reports about 2.9 MB of quantized weights per binary. | Evidence for a small paid-for prior, not for importing a general-purpose LLM. Compare quantized inference **inside the ensemble**, count every shipped copy, and test CPU reproducibility. The organizer’s accepted total, not the author’s comparison against an earlier incumbent, determines the next target.[1] |

**Entropy coder choice is a separate experiment.** Duda’s asymmetric numeral systems (ANS) encode probabilities via an integer state rather than an interval.[23]
A range coder fits a forward online predictor naturally. With a stack-like rANS coder, decoding in forward order generally requires encoding symbols in reverse; a forward adaptive predictor then needs cached distributions, a second pass, or independently buffered blocks. Hold the probability model fixed when comparing coders. Faster state updates have value if they buy time for a better model; they need not save payload bits by themselves.

## Formats: what the decoder actually has to preserve

| Specification | Engineering consequence |
|---|---|
| DEFLATE, RFC 1951 §§3.2–3.2.7[13] | Literals and length/distance copies use stored, fixed-Huffman or dynamic-Huffman blocks; maximum distance 32,768 bytes, maximum match 258. A distant repeated template is invisible to its match finder. Dynamic trees themselves cost bits. |
| gzip, RFC 1952 §2.3; zlib, RFC 1950 §2.2[14][15] | These wrap DEFLATE differently. A minimal gzip member has a 10-byte header and 8-byte CRC32/ISIZE trailer; zlib has its own header, optional dictionary identifier and Adler-32. Raw DEFLATE is neither wrapper. Compare like with like and preserve an external byte comparison even when a checksum passes. |
| Zstandard, RFC 8878 §§3–5[16] | Frames contain blocks; compressed blocks separate literals from copy sequences, using Huffman for compressed literals and finite-state entropy coding for sequence symbols when appropriate. A formatted dictionary can seed history and coding tables. A dictionary ID does not transmit the dictionary: account for its actual bytes wherever supplied. |
| Brotli, RFC 7932 §§7–8[17] | Context-dependent literal coding and references to transformed static-dictionary words illustrate two ways to spend decoder complexity on text. A dictionary mandated by a format is not thereby free under prize rules. |
| XML 1.0 §§2.11, 3.3.3, 4.4[18] | XML processors can normalize line endings and attribute values and expand references. For this byte-prefix corpus, do not parse and reserialize as the inverse. `&amp;` and `&#38;` can denote the same character but occupy different bytes. A wiki-aware transform needs escapes for every literal/control collision and for a truncated final construct. |

None of these is a mandatory submission format.[2]
Use them as baselines or as designs with specified decoding semantics. A custom reversible tokenizer could separate XML field names, wiki markup and article prose, then model each stream differently. It must encode the interleaving, lengths and literal exceptions, or let the decoder derive them from the prefix. Sorting articles by topic may improve locality, but the original order must also be recoverable; the published winning pipeline actually reorders articles and substitutes dictionary indices before prediction.[22]

## Measurement ladder for this repository

1. **Fidelity control (observed).** The [Makefile](../Makefile) uses `gzip -n -6` on the first MiB, then `gzip -dc … | cmp … -`. The existing `data/sample` and `build/sample.gz` here measure **1,048,576 → 371,546 bytes**, or **2.83467 archive bpb**; decoding and comparing those files passed. This includes the gzip wrapper, excludes program sizes, and is not an enwik9 result.
2. **Cheap model test (proposed).** Keep the coder and framing fixed. Compare byte frequencies alone, suffix backoff, then suffix backoff plus a match expert. Report log-loss bits, actual stream bytes, and tool sizes separately. Run on several disjoint slices as well as the first MiB: a cold-start prefix can bias comparisons against online learning. Include empty blocks, all 256 byte values, literal escape markers, long runs and an input ending midway through markup in round-trip tests.
3. **Prize-relevant test (proposed).** Start from an accepted implementation and ablate one change on identical data and hardware. Mahoney’s Large Text Compression Benchmark lists **96,996,198** for `fx2-cmix-transformer`, versus the prize’s **100,424,672**. The two tables answer different questions: benchmarking decompression artifacts is not charging the compressor under the prize rules. Never select a target by copying a leaderboard payload column.[1][2][19]
4. **Full gate (proposed).** Verify corpus identity; generate the actual charged artifacts. Decode in a fresh directory without a network or uncharged inputs, compare all `10^9` bytes, and record exact sizes including options, per-direction elapsed time, CPU/core configuration, Geekbench 5 score, peak memory and temporary disk. Report `8P/N` for payload and `8S/N` for the prize package; the formula target above is **0.7953634 total bpb**. Check the organizer’s licensing, documented source, build, and public verification requirements before treating any local result as a claim.[2]

## Sources

[1] http://prize.hutter1.net
[2] http://prize.hutter1.net/hrules.htm
[3] http://prize.hutter1.net/hfaq.htm
[4] https://mattmahoney.net/dc/textdata.html
[5] https://doi.org/10.1002/j.1538-7305.1948.tb01338.x
[6] https://doi.org/10.1145/214762.214771
[8] https://doi.org/10.1109/18.382012
[9] https://doi.org/10.1109/TIT.1977.1055714
[11] https://www.byronknoll.com/cmix.html
[12] https://arxiv.org/abs/2309.10668
[13] https://www.rfc-editor.org/rfc/rfc1951
[14] https://www.rfc-editor.org/rfc/rfc1952
[15] https://www.rfc-editor.org/rfc/rfc1950
[16] https://www.rfc-editor.org/rfc/rfc8878
[17] https://www.rfc-editor.org/rfc/rfc7932
[18] https://www.w3.org/TR/xml
[19] https://mattmahoney.net/dc/text.html
[20] https://doi.org/10.1109/TCOM.1984.1096090
[21] https://www.cs.jhu.edu/~langmea/resources/burrows_wheeler.pdf
[22] https://github.com/astOwOlfo/fx2-cmix-transformer-v1/blob/main/writeup.md
[23] https://arxiv.org/abs/1311.2540
