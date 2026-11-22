#!/usr/bin/env bash
# Optional native research binary, NOT substituted into original-archive replay.
set -euo pipefail
mid=$(cd "$(dirname "$0")/../.." && pwd)/build/mid
mkdir -p "$mid/tc/debs"; cd "$mid/tc/debs"
v=1:17.0.6-23ubuntu7
apt-get download "clang-17=$v" "libclang-common-17-dev=$v" "libclang-cpp17t64=$v" "libllvm17t64=$v"
sha256sum -c <<'SUMS'
a701a8ed281d9fb12b7b0888cac59ff4ed61b6dc302e58721300fa7a0ec2ccb2  clang-17_1%3a17.0.6-23ubuntu7_amd64.deb
fe2bfd4fd6d8e81544c60cc08c51661d5d843c730125bf067b714f03702a6f05  libclang-common-17-dev_1%3a17.0.6-23ubuntu7_amd64.deb
babea875ee886818e18c23fdedeeb58856a3e6f915fb4042bacaf5626381e661  libclang-cpp17t64_1%3a17.0.6-23ubuntu7_amd64.deb
a787c6822c3b42c7eb5267f7cc61cd5517e1f78f0e7189e7739591dec11fb3a0  libllvm17t64_1%3a17.0.6-23ubuntu7_amd64.deb
SUMS
for pkg in clang-17 libclang-common-17-dev libclang-cpp17t64 libllvm17t64; do dpkg-deb -x "${pkg}_1%3a17.0.6-23ubuntu7_amd64.deb" ../root; done
export LD_LIBRARY_PATH=$mid/tc/root/usr/lib/x86_64-linux-gnu
cd "$mid"; [[ -d fx2-cmix/.git ]] || git clone -q https://github.com/kaitz/fx2-cmix fx2-cmix
out=$(mktemp -d "$mid/native.XXXXXXXX"); git -C fx2-cmix archive 04c5806f99b9b0fa8572be8c8063b4324ec405de | tar -xf - -C "$out"
make -C "$out" -j1 cmix CC="$mid/tc/root/usr/bin/clang++-17" ZEN2=1 CFLAGS_DEFINES='-include cstdint -DSEED=923 -DUPDATE_LIMIT=3000' > "$out/build.log" 2>&1
sha256sum "$out/cmix"
