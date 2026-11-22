# All-winner package replays

The unit is one award, not one author, version family or published binary. The [award census](../winners.md) ties each of these 11 targets to the organizer's ranking. The two pre-prize baselines are excluded. A machine-specific build can be useful evidence without being the ranked artifact.

| Award | Target | Reference total (bytes) | Corpus |
|---:|---|---:|---|
|1|paq8hp5 -7|17,073,018|enwik8|
|2|paq8hp12 -7|16,481,655|enwik8|
|3|decomp8 (May 2009)|15,949,688|enwik8|
|4|phda9 (2017)|15,284,944|enwik8|
|5|STARLIT|115,352,938|enwik9|
|6|fast cmix|114,156,155|enwik9|
|7|fx-cmix|112,578,322|enwik9|
|8|fx2-cmix|110,793,128|enwik9|
|9|cmix-lex|109,671,639|enwik9|
|10|cmix-obias|108,521,870|enwik9|
|11|fx2-cmix-T|100,424,672|enwik9|

## How to read the results

- An artifact match needs identified provenance, lengths and hashes; matching a total alone is not enough. Reserve **bit-identical** for a direct file comparison or matching digest against the same published artifact.
- A **verified decode** requires a complete run without the original input available to the decoder, and output compared against the correct original corpus. No `--help`, prefix test, archive header inspection, build success or time estimate counts.
- An **end-to-end replay** additionally runs the encoder and verifies its output by a clean decode. Separate the achieved package total from the ranked figure. Old rules sometimes required only a decoder: if the matching encoder was not released, a successful official archive decode is still meaningful but not an encoder reproduction.
- Classify exact published artifact, historical public variant, compatible rebuild and substitute separately. Report missing releases, unsupported CPU instructions or unachieved resource limits rather than shifting the reference score. Runtime on this host is not a committee ruling.

## Corpus and scheduling

The local billion-byte `enwik9` was checked previously. Its first 100,000,000 bytes were independently hashed for this campaign and match the [published enwik8 MD5](https://mattmahoney.net/dc/textdata.html) `a1fa5ffddb56f4953e226637dabbb36a`; measured SHA-256 `2b49720ec4d78c3c9fabaee6e4179a5e997302b3a70029f30f2d582218c024a8`. These are grader references, not files available to contestants' decoders. The ongoing [STARLIT trial](starlit-order.md) covers award 5's public AMD variant; do not launch a duplicate or label that variant the official Intel package. Run large-memory full trials serially; fetches and lightweight inspection can proceed independently. Keep corpus, executable downloads, decoded outputs and large scratch files out of Git.
