"""Serial sandbox replay; requires the staged files in build/legacy-replay."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

BASE = Path(__file__).resolve().parents[2] / 'build/legacy-replay'
REF = BASE / 'reference'
SHA = '2b49720ec4d78c3c9fabaee6e4179a5e997302b3a70029f30f2d582218c024a8'
CASES = {'hp5': ('8', 'paq8hp5.exe'), 'hp12': ('10', 'PAQ8HP12.EXE'),
         'hp12any': ('4', 'paq8hp12_l64'), 'decomp8': ('5', 'decmprs8.exe'),
         'phda': ('6', 'phda'), 'public': ('9', 'phda9'), 'hp5port': ('port', 'paq8hp5')}


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def run(case, full):
    group, exe = CASES[case]
    pkg = BASE / 'members' / group
    folder = Path(tempfile.mkdtemp(prefix=('full-' if full else 'probe-') + case + '-', dir=BASE))
    work = folder / 'work'
    work.mkdir()
    print(folder, flush=True)
    def invoke(name, args, seconds):
        argv = ['systemd-run', '--user', '--scope', '-q', '-p', 'MemoryMax=1800M', '-p', 'MemorySwapMax=0', '-p', 'AllowedCPUs=7', 'nice', '-n', '19', 'ionice', '-c3', 'taskset', '-c', '7', '/usr/bin/time', '-f', 'elapsed=%e maxrss_KiB=%M exit=%x', '-o', str(folder / (name+'.time')), 'bwrap', '--unshare-all', '--die-with-parent', '--new-session', '--cap-drop','ALL','--clearenv','--setenv','PATH','/usr/bin','--setenv','HOME','/work','--ro-bind','/usr','/usr','--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64','--symlink','usr/bin','/bin','--dev','/dev','--proc','/proc','--tmpfs','/tmp','--ro-bind',str(pkg),'/pkg','--ro-bind',str(BASE/'tools/wibo-i686'),'/wibo','--bind',str(work),'/work','--chdir','/work','--','timeout','-k','2',str(seconds),'/usr/bin/time','-f','payload elapsed=%e maxrss_KiB=%M exit=%x']
        if exe.lower().endswith('.exe'):
            at = argv.index('--ro-bind')
            argv[at:at] = ['--ro-bind',str(BASE/'tools/wine-11.22-amd64-wow64'),'/wine','--setenv','WINEPREFIX','/work/prefix','--setenv','WINEDEBUG','-all','--setenv','WINEDLLOVERRIDES','mscoree,mshtml=','--setenv','USER','replay']
            argv += ['/wine/bin/wine', 'Z:\\pkg\\'+exe, *[('Z:'+a.replace('/','\\')) if a.startswith('/') else a for a in args]]
        else:
            argv += ['/pkg/'+exe, *args]
        (folder/(name+'.argv.json')).write_text(json.dumps(argv))
        with (folder/(name+'.log')).open('wb') as log:
            return subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT).returncode
    result = {'case': case, 'full': full}
    limit = 24*3600 if full else 120
    try:
        if case in ('decomp8','phda'):
            arc = 'archive8.dat' if case == 'decomp8' else 'compressed_enwik8'
            result['decode_rc'] = invoke('decode', ['/pkg/'+arc,'enwik8'], limit if full else (35 if case=='decomp8' else 6))
            if not full:
                result['output_bytes'] = (work/'enwik8').stat().st_size if (work/'enwik8').exists() else None
                return result
            expected = SHA
        else:
            if full:
                shutil.copyfile(REF,work/'enwik8')
            else:
                with REF.open('rb') as f: (work/'enwik8').write_bytes(f.read(8192))
            expected = digest(work/'enwik8')
            if case == 'hp12any':
                for p in pkg.glob('*.dic'): shutil.copyfile(p,work/p.name)
            enc = ['C','enwik8','archive'] if case=='public' else ['-7','archive','enwik8']
            result['encode_rc'] = invoke('encode',enc,limit)
            if result['encode_rc'] != 0: return result
            result['archive_bytes'] = (work/'archive').stat().st_size
            if full:
                target = {'hp5':16898402,'hp5port':16898402,'hp12':16381959,'hp12any':16381959}.get(case)
                if target is not None:
                    result['award_archive_bytes'] = target
                    result['award_size_match'] = result['archive_bytes']==target
            result['archive_sha256'] = digest(work/'archive')
            (work/'enwik8').unlink()
            result['decode_rc'] = invoke('decode',['D','archive','enwik8'] if case=='public' else ['archive'],limit)
        if (work/'enwik8').is_file():
            result['decoded_sha256'] = digest(work/'enwik8')
            result['decoded_bytes'] = (work/'enwik8').stat().st_size
            result['verified'] = result['decode_rc']==0 and expected==result['decoded_sha256']
        return result
    finally:
        (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__ == '__main__':
    mode,*cases = sys.argv[1:]
    if mode not in ('probe','full') or os.getuid()==0 or not cases: sys.exit('use probe|full CASE... as a non-root user')
    if digest(REF)!=SHA: sys.exit('incorrect reference')
    failures = 0
    for case in cases:
        try:
            result = run(case, mode=='full')
            print(json.dumps(result), flush=True)
            failures += mode=='full' and not result.get('verified',False)
        except Exception as e:
            print(repr(e),flush=True); failures += 1
    sys.exit(int(bool(failures)))
