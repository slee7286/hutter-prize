#!/usr/bin/env python3
"""Late Hutter Prize entries: fetch, offline smoke, or explicitly run serial replay."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess as sp
import tempfile

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]
BASE = ROOT / 'build/late'
DATA = ROOT / 'data/enwik9'
GOLD = '159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc'
ROWS = [line.split('\t') for line in (TOOLS/'late-artifacts.tsv').read_text().splitlines()]


def sha(path):
    with path.open('rb') as f:
        h = hashlib.sha256()
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
        return h.hexdigest()


def verify(path, size, digest):
    if path.stat().st_size != int(size) or sha(path) != digest:
        raise ValueError(f'wrong bytes: {path}')


def box(stage, mounts, args, *, head=False, short=False):
    stage.mkdir()
    cmd = ['bwrap','--unshare-all','--new-session','--die-with-parent','--clearenv',
           '--setenv','PATH','/usr/bin','--ro-bind','/usr','/usr','--symlink','usr/bin','/bin',
           '--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64','--dev','/dev',
           '--proc','/proc','--tmpfs','/tmp','--bind',str(stage),'/w','--chdir','/w']
    for name, path in mounts.items():
        cmd += ['--ro-bind',str(path),'/w/'+name]
    if head:
        cmd += ['--setenv','KH_BITLSTM32','/w/head.blob']
    if os.environ.get('REPLAY_USE_SDE') == '1':
        sde = ROOT/'build/mid/sde'
        if not (sde/'sde64').is_file():
            raise RuntimeError('pinned Intel SDE installation is required')
        cmd += ['--ro-bind',str(sde),'/sde']
        args = ['/sde/sde64','-skx','--',*args]
    cmd += ['/usr/bin/time','-f','wall=%e user=%U sys=%S maxrss_KiB=%M exit=%x',*args]
    log = stage.with_suffix('.log')
    with log.open('wb') as f:
        sp.run(cmd,check=True,stdout=f,stderr=sp.STDOUT,timeout=30 if short else None)


def lex_native(run, binary):
    # Keep the exact executable prefix; recode its two predictive streams on this CPU.
    # Intel-produced model streams aren't necessarily decodable on AMD.
    bits = binary.read_bytes()
    ds, osize, payload = struct.unpack('<III',bits[-12:])
    if payload or len(bits) <= ds+osize+12:
        raise ValueError('unexpected lex trailer')
    parts = []
    for i, name in enumerate(('english.dic','new_article_order')):
        d = run/f'asset{i}'
        box(d, {'cmix':binary,'asset':BASE/'lex'/name}, ['./cmix','-c','asset','stream'])
        dec = run/f'check{i}'
        box(dec, {'cmix':binary,'stream':d/'stream'}, ['./cmix','-d','stream','asset'])
        if sha(dec/'asset') != sha(BASE/'lex'/name):
            raise ValueError('local asset failed to round trip')
        parts.append((d/'stream').read_bytes())
        shutil.rmtree(d); shutil.rmtree(dec)
    dest = run/'cmix'
    dest.write_bytes(bits[:-(12+ds+osize)] + b''.join(parts) + struct.pack('<III',len(parts[0]),len(parts[1]),0))
    dest.chmod(0o755)
    return dest


def replay(k, mode):
    src = BASE/k
    run = Path(tempfile.mkdtemp(dir=BASE,prefix=f'{mode}-{k}-'))
    print(run,flush=True)
    encoder, archive = src/'cmix', src/'archive9'
    head = {'head.blob':src/'head.blob'} if k == 'obias' else {}
    if mode == 'smoke':
        sample = run/'sample'
        with DATA.open('rb') as f:
            sample.write_bytes(f.read(4096))
        box(run/'encode',{'cmix':encoder,'sample':sample,**head},['./cmix','-s','sample','stored'],head=bool(head),short=True)
        archive_stream = run/'encode/stored'
        box(run/'decode',{'archive9':archive,'stored':archive_stream},['./archive9','-d','stored','restored'],short=True)
        verify(run/'decode/restored',4096,sha(sample))
        result = {'input_sha256':sha(sample),'stored_bytes':archive_stream.stat().st_size,'stored_sha256':sha(archive_stream),'matched':True}
    else:
        if mode == 'full':
            if k == 'lex' and 'AuthenticAMD' in Path('/proc/cpuinfo').read_text():
                encoder = lex_native(run, encoder)
            box(run/'encode',{'cmix':encoder,'enwik9':DATA,**head},['./cmix','-e','enwik9','out.cmix'],head=bool(head))
            archive = run/'archive9'
            (run/'encode/archive9').rename(archive)
            archive.chmod(0o755)
            shutil.rmtree(run/'encode')
        result = {'encoder_sha256':sha(encoder),'archive9_sha256':sha(archive),'archive9_bytes':archive.stat().st_size,'S1':encoder.stat().st_size+sum(p.stat().st_size for p in head.values()),'matches_public_archive':sha(archive)==sha(src/'archive9')}
        result['S'] = result['S1'] + result['archive9_bytes']
        box(run/'decode',{'archive9':archive},['./archive9'])
        verify(run/'decode/enwik9_uncompressed',1000000000,GOLD)
        result['decoded_sha256'] = GOLD
        shutil.rmtree(run/'decode')
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode',choices=['fetch','smoke','full','decode-public'])
    ap.add_argument('entries',nargs='*',help='lex obias t-fixed transformer (original)')
    args = ap.parse_args()
    entries = args.entries or ['lex','obias','t-fixed']
    if set(entries)-{'lex','obias','t-fixed','transformer'}:
        ap.error('unknown entry')
    BASE.mkdir(parents=True,exist_ok=True)
    with (BASE/'replay.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for name,size,digest,url in ROWS:
            if args.mode != 'fetch' and name.split('/')[0] not in entries:
                continue
            dest = BASE/name
            if args.mode == 'fetch' and not dest.exists():
                dest.parent.mkdir(parents=True,exist_ok=True)
                tmp = dest.with_suffix('.part')
                sp.run(['curl','-fLsS','--retry','2','-o',str(tmp),url],check=True)
                verify(tmp,size,digest); tmp.replace(dest)
            verify(dest,size,digest)
            if dest.name in {'cmix','archive9'}:
                dest.chmod(0o755)
        if args.mode == 'fetch':
            return
        if args.mode == 'full':
            verify(DATA,1000000000,GOLD)
        for k in entries:
            replay(k,args.mode)


if __name__ == '__main__':
    main()
