# Hutter Prize sandbox

Research: [Hutter Prize dossier](research/README.md) — contest protocol, compression methods, winners, discussions, and an agent-assisted experiment workflow.

Run `make baseline`. On first use it downloads enwik9, checks its size and published checksum, and extracts its first MiB as `data/sample`. Later runs need no network. `data/enwik9` is the full corpus: treat it as read-only.

The baseline uses gzip, decompresses the result, and compares every byte with the sample. Start your own encoder/decoder on the same sample; compare compressed sizes only after the round trip passes. No custom codec is provided.

This is a development measurement, not a prize score: the actual rules use the entire corpus and count the compressor and self-extracting archive. Rules: http://prize.hutter1.net/hrules.htm . Corpus: https://mattmahoney.net/dc/textdata.html .
