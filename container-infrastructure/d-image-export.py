#!/usr/bin/python3
'''
Create exports of container images.

TODO: real doc
'''

import argparse, datetime, glob, os, re, sys
import kcore.common as C
import ktools.ktools_settings as KS
from dataclasses import dataclass


# ---------- global controls & state

ARGS = {}   # set by main
DOCKER_EXEC = KS.get('docker_exec')


# ---------- internal types

@dataclass
class ImageMetadata:
    name: str
    label: str
    image_hash: str

    def filename(self): return os.path.join(ARGS.dir, f'img-{self.image_hash}.tgz')
    def linkname(self): return os.path.join(ARGS.dir, f'lnk-{self.name.replace("/","-")}:{self.label}')
    def dated_linkname(self):
        now = datetime.datetime.now()
        return os.path.join(ARGS.dir, self.linkname() + now.strftime('-%Y%m%d.tgz'))
    def spec(self): return f'{self.name}:{self.label}:[{self.image_hash}]'


# ---------- helpers

def Debug(msg):
    if ARGS.debug: print(msg, file=sys.stderr)


def Error(msg, prefix='ERROR: '):
    print(prefix + msg, file=sys.stderr)


def file_ok(filename, min_size=100):
    if not os.path.exists(filename): return False
    if os.stat(filename).st_size < min_size: return False
    return True


# ---------- main

def main():
    ap = argparse.ArgumentParser(description='container image exporter')
    ap.add_argument('--debug',  '-D',  action='store_true', help='print details')
    ap.add_argument('--dir',    '-d',  default='.',         help='output directory')
    ap.add_argument('--filter', '-f',  default='',          help='only snapshot images with regexp')
    ap.add_argument('--label',  '-l',  default='live',      help='only snapshot images with this label')
    ap.add_argument('--dryrun', '-n',  action='store_true', help='output what would be done')
    global ARGS
    ARGS = ap.parse_args()

    need = []
    filter = re.compile(ARGS.filter) if ARGS.filter else None
    for line in C.popener([DOCKER_EXEC, 'images']).split('\n'):
        if line.startswith('REPO'): continue  # header
        name, label, image_hash, _ = re.split(' +', line, maxsplit=3)
        imd = ImageMetadata(name, label, image_hash)
        if name.startswith('<none'):
            Debug(f'filtered by unnamed status: {imd.spec()}')
            continue
        if filter and not filter.search(imd.spec()):
            Debug(f'filtered by --filter mismatch: {imd.spec()}')
            continue
        if ARGS.label and not label == ARGS.label:
            Debug(f'filtered by label: {name}.{label}')
            continue
        Debug(f'Added: {imd.spec()}')
        need.append(imd)

    have = set()
    for filename in glob.glob(ARGS.dir + '/img-*.tgz'):
        if not file_ok(filename):
            print(f'WARNING: {filename} ignored; too small to be a valid export')
            continue
        image_hash = os.path.basename(filename).replace('img-', '').replace('.tgz', '')
        have.add(image_hash)

    todo = []
    for i in need:
        if i.image_hash in have:
            Debug(f'Image already exported: {i} ({i.name}:{i.label})')
            continue
        todo.append(i)

    if not todo:
        Error('Nothing to do', prefix='')
        sys.exit(0)

    cmds = ''
    for i in todo: cmds += f'{DOCKER_EXEC} save ^^"{i.name}:{i.label}" | gzip > {i.filename()}\n'

    if ARGS.dryrun:
        print('\nrun_para --sep="\\n" <<EOF\n' + cmds + '\nEOF\n')
        sys.exit(0)

    Debug(f'Running in parallel:\n{cmds}\n')
    out = C.popen(['run_para', '--sep', '\n'], stdin_str=cmds, passthrough=True)
    if not out.ok: Error(f'run_para returned error: {out.out}')

    os.chdir(ARGS.dir)  # for relative link creation
    status = 0
    for i in todo:
        image_name = os.path.basename(i.filename())
        link_name = i.dated_linkname()
        if not file_ok(image_name):
            status = 2
            Error(f'{image_name} failed to export')
            continue
        if os.path.exists(link_name):
            Debug(f'replacing old link: {link_name}')
            os.unlink(link_name)
        os.symlink(image_name, link_name)
        print(f'ok: {link_name} -> {image_name}')
    sys.exit(status)


if __name__ == "__main__":
  main()
