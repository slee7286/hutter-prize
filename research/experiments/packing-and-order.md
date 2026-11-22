# Follow-on experiments: reduce the shipped package, not the slice score

## 1. Change only the release executable packing method (preregistered)

Start from the [kept static-table rebuild](transformer-weight-integration-result.md), 100,350,152 B, including a 185,900 B UPX `-9` core in each file. The [donor-prefix comparison](transformer-donor-prefix.md) is an existing control, not a new experiment. Test one alternative: UPX 5.1.1 `-9 --lzma` on the identical *unpacked* candidate ELF. The stub is self-contained and charged in each copy; models, order, dictionary, payload, and framing must not change. Expected saving: about 10,000 B per packed core, **20,000 net bytes** per pair. This takes seconds, needs no new prediction model and can be tested exhaustively on the changed object.

Reject if the incumbent `-9` control cannot be reproduced, unpacked ELF bytes differ, launch fails, or the measured combined on-disk saving is nonpositive. If smaller, assemble and re-read the two packages, do a bounded predictive round trip on the established synthetic fixture and compare against the existing reference payload digest. Do not decode the billion-byte corpus.
