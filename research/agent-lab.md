# Running an agent-assisted compression lab

This is a proposed engineering protocol, not a committee rule or a claim that an agent has beaten the record. It combines the [prize scoring contract](https://www.hutter1.net/prize/hrules.htm), [deterministic graders and isolated agent trials](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), and [reproducible build timestamp practice](https://reproducible-builds.org/docs/source-date-epoch/).

## A local example of why the grader matters

On 22 Nov 2026 this workspace's `data/enwik9` matched the publisher's size and MD5. Its locally measured SHA-256 is `159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc`. On an AMD Ryzen 7 5700X3D, GNU gzip 1.14 `gzip -n -6 -c data/enwik9` emitted **323,742,875 bytes**; decoding and piping the result to `cmp - data/enwik9` passed. One run: encode 31.85 s and decode 2.92 s wall time; not controlled speed measurements. These are **archive-only** results. `make baseline` on the first 1 MiB gave 371,546 bytes and an exact round trip.

Independent 1,048,576-byte slices, one cold model per slice, Python stdlib `gzip.compress(x,6,mtime=0)`, `bz2.compress(x)` and `lzma.compress(x)` (XZ default); each output independently decoded and compared equal:

|Byte offset|gzip|bzip2|XZ|
|---:|---:|---:|---:|
|0|372,045|294,143|302,764|
|250,000,000|348,221|278,582|281,652|
|500,000,000|146,645|97,188|105,192|
|750,000,000|365,757|293,416|295,668|
|998,951,424|370,633|297,405|302,468|

The midpoint is exceptionally easy for all three compared with the other slices. Multiplying its result by the corpus/slice length would give a misleading forecast. Even the Python and command-line gzip baselines do not give identical byte counts on the first slice: pin the implementation, not just the format and level. Cold independent slices are useful for diagnosis; they discard past context, change dictionary economics, and cannot replace one continuous full-corpus run.

## Build an independent grader before adding agents

Use three boundaries. (1) A researcher can read code and data and propose a patch or hypothesis. (2) A runner builds a pinned checkout with the declared toolchain and no secrets, and executes it under resource limits. (3) A separate grader, not editable by the candidate, owns the original corpus, reference hashes, scorer and pass/fail decisions. Treat downloaded archives, build recipes and old binaries as untrusted: inspect before executing, use an unprivileged offline sandbox with limited resources and no host home or credentials. No network for the measured encoder/decoder. Only a human publishes or contacts judges. The development agent may use an LLM; the submitted programs do not thereby gain permission to call one.

|Gate|What to do|What passes|
|---|---|---|
|0. Freeze|Record previous eligible package, toolchain, settings, hash of immutable test data, score equation and resource budget.|A rerun recovers the baseline. If the historical environment won't build, document that before changing code.|
|1. Correctness|Test the invertible transform separately, then the full codec. Include supported empty/tiny/long runs, all byte values, UTF-8 boundaries, escaped entities, case, markup, numeric strings, EOF and partial final records. For a corpus-only codec, test its declared domain and its internal components rather than imposing general-purpose eligibility.|Exact bytes; no silent fallback that reads the reference; no decoder dependence on encoder-side persistent state.|
|2. Proxy|Try a single hypothesis on contiguous slices with fixed offsets, both cold and with explicitly defined warm-up. Measure stage-by-stage sizes, code cost, encode/decode time and peak space.|Net expected byte savings and time headroom; not just lower loss on one slice. Record failures too.|
|3. Ablate|Use identical builds with component off/on. Shuffle run order, repeat noisy timing, isolate other load; compare joint variants when two changes touch the same contexts.|A plausible mechanism for the gain, attribution with interaction effects, and no hidden work moved into an uncounted step.|
|4. Full run|Encode full enwik9, restore elsewhere with no encoder artifacts except the allowed inputs, enforce CPU/RAM/disk ceilings, compare exact bytes and measure final packages.|Positive net savings after all charges; publish separate archive, program, options and total columns. No official-record label.|
|5. Independent replay|A second operator/agent starts from the public package and instructions alone on a clean supported system; check license, attribution, flags and online accessibility. Diff hash mismatches; don't explain them away.|Reproducible decode plus a qualified resource result. Only committee verification establishes a prize.|

One experiment record should contain hypothesis, expected byte gain and reason, baseline/candidate commits, toolchain, CPU/OS/core binding, source/input checksums, options, training state origin, slice offsets/warm-up, C/D/A and flags bytes, phase times, peak RSS and scratch high-water mark, round-trip status and first differing offset on failure. Log model/tool/compute spend of the development agent separately from the codec's runtime and package score. Keep raw logs and skipped/failed trials; otherwise an agent can report only lucky runs. Repeated correctness trials are not a substitute for a deterministic decoder.

## What to try, and when to stop

1. **Read one recent winner from encoder through inverse transform.** Draw the exact information available before each prediction at decode time. If a proposed feature sees even one future original bit, either redesign it causally or identify and charge the side information. A transform may inspect the whole input during encode if its inverse has sufficient counted information.
2. **Profile before adding capacity.** Separate transform time, predictor time, mixer updates, coder time and I/O. Track cumulative bits by byte class/region to distinguish an XML improvement from general better prediction. An agent proposing only “add a transformer” must provide an attainable byte budget, inference/update complexity and a deterministic synchronization plan.
3. **Compare three concrete hypotheses:** a reversible representation for a repetitive markup family (measure exceptions/metadata); a context predicting text conditioned on markup type (measure incremental value after existing mixing); reducing the cost of a slow expert (measure whether reinvesting the time in a richer model helps). Put each in its own branch; do not run competing full-corpus timing trials on the same cores. Early-abort losers only against preregistered criteria and label truncated runs.
4. **Keep search honest.** Contest-tuning to this known corpus is allowed. A claim of generalization is a different experiment: lock another corpus or an unseen region before tuning and publish its result even on failure. Independent agents must not train on the grading labels or rewrite evaluation code. Avoid one-agent-per-parameter brute force; cheap deterministic sweeps do not need model supervision.
5. **Stop or promote:** discard corruption, forbidden dependencies and budget violations first. Among survivors compare total score with the same packaging convention as the baseline. Promote sparse exploratory wins only after full replay; retain informative null results so the next agent doesn't repeat them. If resource compliance depends on an interpretation rather than a measurement, label it and ask the committee; never relabel the hypothesis as an award.
