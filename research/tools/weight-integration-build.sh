#!/bin/bash
# Run from repo root, with private clang-17 packages extracted under $W/sysroot.
# Requires a private clone of the pinned upstream in $W/src. Never writes to
# the upstream reference checkout or executes the billion-byte donor stream.
set -euo pipefail
root=$(pwd -P); W=$root/build/wt-integration; T=$W/sysroot/usr
export PATH="$T/bin:$PATH" LD_LIBRARY_PATH="$T/lib/x86_64-linux-gnu:$T/lib/llvm-17/lib"
pack=$root/build/upx-5.1.1-amd64_linux/upx
cd "$W/src"
test "$(git rev-parse HEAD)" = 83f2603f3f7751da5f429fd32669807eb8510494
# Host's newer libstdc++ no longer transitively declares uintptr_t in fxcmv1.
# Same explicit standard header for profile generation and both release arms.
flags='CFLAGS_DEFINES=-DSEED=923 -DUPDATE_LIMIT=3000 -include stdint.h'
case "$1" in
 profile)
    git diff --exit-code HEAD -- . >/dev/null
    mkdir -p pgo_data
    make -j2 "$flags" prof_gen
    # Only the small upstream PGO fixture, not the research sample or enwik9.
    profile=$(realpath pgo_data); stage=$(mktemp -d "$W/profile.XXXXXX")
    bwrap --unshare-all --die-with-parent --clearenv --setenv PATH /usr/bin --ro-bind /usr /usr --symlink usr/bin /bin --symlink usr/lib /lib --symlink usr/lib64 /lib64 --dev /dev --proc /proc --tmpfs /tmp --bind "$stage" /w --bind "$profile" "$profile" --ro-bind "$PWD/cmix" /w/cmix --ro-bind "$PWD/prof_input/input" /w/input --chdir /w /w/cmix -c input stream
    llvm-profdata-17 merge -output=pgo_data/default.profdata pgo_data/*.profraw
    ;;
 baseline|candidate)
    test -s pgo_data/default.profdata
    make -j2 "$flags" prof_use
    # Same portability checks as upstream build_and_construct_comp.sh.
    objdump -d --insn-width=16 cmix > "$W/$1.dis"
    python3 -c 'import re,sys; from pathlib import Path; d=Path(sys.argv[1]).read_text(); sys.exit(bool(re.search(r"%zmm|%k[0-7]|\{vex\}|\t62 [0-9a-f][0-9a-f] |\b(v?rcpps|v?rcpss|v?rsqrtps|v?rsqrtss)\b",d)))' "$W/$1.dis"
    mkdir -p "$W/$1"; cp cmix "$W/$1/core"; "$pack" -9 "$W/$1/core"; "$pack" -t "$W/$1/core"
    ;;
 *) exit 2;;
esac
