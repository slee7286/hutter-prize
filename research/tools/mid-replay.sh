#!/usr/bin/env bash
# Original self-extractors. No corpus is mounted into the decode sandbox.
set -euo pipefail
umask 077
ulimit -c 0
root=$(cd "$(dirname "$0")/../.." && pwd)
mid=$root/build/mid
mkdir -p "$mid"; cd "$mid"
mode=${1:-probe}; case $mode in probe|full|recompress) ;; *) exit 2;; esac
exec 9>mid.lock; flock -n 9 || { echo 'Another mid replay is active' >&2; exit 1; }
fetch() { local name=$1 hash=$2 url=$3; if [[ ! -f $name ]]; then curl -fLsS --retry 3 "$url" -o "$name.part"; printf '%s  %s\n' "$hash" "$name.part" | sha256sum -c -; mv "$name.part" "$name"; fi; printf '%s  %s\n' "$hash" "$name" | sha256sum -c -; }
drive='https://drive.usercontent.google.com/download?export=download&confirm=t&id='
fetch fast.archive 158402125b94a923939463089ac108736c38f80df6f9af70c6b3813141d56234 https://mattmahoney.net/dc/fastcmix.archive9
fetch fx.archive 5fb56eb2488dbb834a8b5903d9f853768303271b0f3602e17e22d27da59ad6c6 "${drive}14gjz045biXxjq4TuurRpvb5-wAFILbec"
fetch fx2.archive 9e733afa3870eb3278a1349626f665ddb5c5105f3158c3cc61adb5adec442569 "${drive}14QillUEElT5vR0ttmayRAXlciXuPwDWm"
chmod u+x {fast,fx,fx2}.archive
run=$(mktemp -d "$mid/$mode.XXXXXXXX"); echo "Evidence: $run"
corpus=159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc
if [[ $mode == recompress ]]; then printf '%s  %s\n' "$corpus" "$root/data/enwik9" | sha256sum -c -; fi
entries=(fast fx fx2); case ${2:-all} in all) ;; fast|fx|fx2) entries=("$2");; *) exit 2;; esac
for n in "${entries[@]}"; do
  work=$run/$n; mkdir "$work"
  file=$mid/$n.archive
  box=(bwrap --unshare-all --die-with-parent --new-session --cap-drop ALL --clearenv --setenv PATH /usr/bin:/bin --proc /proc --dev /dev --tmpfs /tmp --ro-bind /usr /usr --symlink usr/bin /bin --symlink usr/lib /lib --symlink usr/lib64 /lib64 --bind "$work" /work --ro-bind "$file" /work/archive9 --chdir /work)
  engine=(); if ! timeout 20 "${box[@]}" ./archive9 -h 11 22 33; then
    if [[ ! -d $run/sde ]]; then
      fetch sde.tar.xz 94e97d623fec54385686e1e7ba65ebc9941748c05ee451423948334892bf2b50 https://downloadmirror.intel.com/924984/sde-external-10.13.1-2026-07-28-lin.tar.xz
      mkdir "$run/sde"; tar -xf sde.tar.xz --strip-components=1 -C "$run/sde"
    fi
    engine=(/sde/sde64 -skx --); box+=(--ro-bind "$run/sde" /sde)
  fi
  rm -f "$work/header.dat"
  # Inner shell mimics system("./archive9 -d ...") in self_extract.h.
  timeout 30 "${box[@]}" "${engine[@]}" /bin/sh -c './archive9 -h 11 22 33'
  python3 -c 'import struct,sys; assert open(sys.argv[1],"rb").read()==struct.pack("<III",11,22,33)' "$work/header.dat"
  echo "$n: header OK (${engine[*]:-native})"
  printf 'mid replay smoke: <page>abc</page>\n' > "$work/sample"
  timeout 45 "${box[@]}" "${engine[@]}" ./archive9 -s sample stored > "$work/store.log" 2>&1
  timeout 45 "${box[@]}" "${engine[@]}" ./archive9 -d stored restored > "$work/restore.log" 2>&1
  cmp "$work/sample" "$work/restored"; echo "$n: stored-block round trip OK"
  if [[ $mode == probe ]]; then continue; fi
  if [[ $mode == recompress ]]; then
    # Recover the original ELF and packed dictionary from the published SFX;
    # only the packed order is absent. Fail before encoding if its size differs.
    case $n in fast) rev=e196e65fa09b2e655e8fb74e6c9944c2fc27eced; repo=saurabhk;; fx) rev=2af9836d17c24134a6c8c8ea9b99d6c13c34b720; repo=kaitz;; fx2) rev=04c5806f99b9b0fa8572be8c8063b4324ec405de; repo=kaitz;; esac
    [[ -d $n-cmix/.git ]] || git clone -q "https://github.com/$repo/$n-cmix" "$n-cmix"
    git -C "$n-cmix" show "$rev:src/readalike_prepr/data/new_article_order" > "$work/order"
    python3 - "$file" "$work" <<'PY'
import pathlib,struct,sys
b=pathlib.Path(sys.argv[1]).read_bytes(); p=pathlib.Path(sys.argv[2]); d,o,c=struct.unpack('<III',b[-12:]); k=len(b)-d-c-12
assert 0<k<len(b) and b.startswith(b'\x7fELF'); (p/'core').write_bytes(b[:k]); (p/'core').chmod(0o700); (p/'prefix').write_bytes(b[:k+d]); (p/'footer').write_bytes(struct.pack('<III',d,o,0))
PY
    "${box[@]}" "${engine[@]}" ./core -c order packed.order > "$work/order.log" 2>&1
    python3 - "$work" <<'PY'
import pathlib,struct,sys
p=pathlib.Path(sys.argv[1]); o=(p/'packed.order').read_bytes(); h=(p/'footer').read_bytes(); assert len(o)==struct.unpack('<III',h)[1]; (p/'cmix').write_bytes((p/'prefix').read_bytes()+o+h); (p/'cmix').chmod(0o700)
PY
    sha256sum "$work/cmix"
    # archive9 must be writable for encoding: separate clean output directory.
    mkdir "$work/encode"; cp "$work/cmix" "$work/encode/"
    rc=0; /usr/bin/time -v -o "$work/encode.time" "${box[@]}" --ro-bind "$root/data/enwik9" /input --chdir /work/encode "${engine[@]}" ./cmix -e /input enwik9.comp > "$work/encode.log" 2>&1 || rc=$?
    echo "encoder exit=$rc"; [[ $rc == 0 || $rc == 134 ]]; cmp "$file" "$work/encode/archive9"; echo "$n: generated SFX byte-identical"
  fi
  # Exclude encoder and probe scratch from all decoder-visible files.
  dest=$run/$n-restore; mkdir "$dest"
  for i in "${!box[@]}"; do [[ ${box[$i]} != "$work" ]] || box[$i]=$dest; done
  "${box[@]}" /usr/bin/time -v "${engine[@]}" ./archive9 > "$work/decode.log" 2>&1
  out=$dest/enwik9_uncompressed; [[ -f $out ]] || out=$dest/enwik9_restored
  [[ ! -L $out && $(stat -c %s "$out") == 1000000000 ]]; printf '%s  %s\n' "$corpus" "$out" | sha256sum -c -
  echo "$n: full restore verified"; # keep logs and output, discard successful scratch
  mv "$out" "$work/verified-enwik9"; out=$work/verified-enwik9; rm -rf "$dest"
  python3 - "$work" "$out" <<'PY'
import pathlib,sys,shutil
p,out=map(pathlib.Path,sys.argv[1:]);
for f in p.iterdir():
 if f!=out and f.suffix not in ('.log','.time'):
  if f.is_dir() and not f.is_symlink(): shutil.rmtree(f)
  else: f.unlink()
PY
done
if [[ -d $run/sde ]]; then rm -rf "$run/sde"; fi
