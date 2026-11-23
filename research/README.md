# Hutter Prize research dossier

**22 November 2026.** The objective is the smallest eligible *whole package* that recreates a fixed billion bytes, not the smallest payload, lowest perplexity, or fastest compressor. The [organizer's current table](https://www.hutter1.net/prize/#prev) lists Vladimir Ivanov's `fx2-cmix-T` at **100,424,672 bytes**. A conservative target satisfying both the table and the [formal minimum](https://www.hutter1.net/prize/hrules.htm#award) is **99,420,424 bytes or fewer**. Verify the live record again before submitting.

## Read in this order

1. [The contest protocol](protocol.md): corpus identity, what is counted, exact threshold, machine budget, conflicting historical language, licensing and the submission checklist.
2. [How lossless compression works](compression.md): the technical background, algorithms, standards and their relevance to enwik9.
3. [Winning submissions](winners.md): the two competition eras, baselines versus actual awards, byte accounting and documented techniques.
4. [Public discussions](discussions.md): discussion evidence, disputes and access limits. Commentary is not a ruling.
5. [Agent-assisted lab](agent-lab.md): a measured full-corpus baseline, slice-selection experiment, deterministic grading, ablations and independent verification.
6. [Organizer site guide and inventory](site-guide.md): text of the substantive pages, link and resource manifests, reading routes, and scope limits.
7. [Transformer weight recoding](experiments/transformer-weight-tables-result.md) and [release integration](experiments/transformer-weight-integration-result.md): 52,022 B saved across matched rebuilt packages after counting code. The short predictive payload and isolated decode matched; the full corpus was not run.
8. [Release packing and article-order coding](experiments/packing-and-order.md): the smallest rebuilt pair is another 50,220 B smaller on disk. It restores the order exactly but cannot pass its native dictionary check on this host. The published portable control also returns incorrect dictionary bytes here. Do not treat either weigh-in as an eligible score.
9. [Embedded dictionary repair](experiments/dictionary-repair.md): replacing both dictionary streams cost zero bytes and fixed startup dictionary recovery. The repaired archive's native prefix differs from the old explicit-mode reference at byte 6. No working baseline or subsequent optimization is claimed.

**First useful engineering step:** reproduce the current winner's package calculation and a clean decode before modifying its prediction model. Until then, a smaller experimental stream does not establish progress toward the prize. The full GNU gzip run in this dossier is a reproducible sanity reference; it is not a reproduction of a winning submission.
