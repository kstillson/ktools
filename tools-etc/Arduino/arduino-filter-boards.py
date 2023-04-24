#!/usr/bin/python3

'''Remove all but whitelisted boards from the Arduino IDE boards list.'''

import argparse, os, shutil, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--backup-suffix',  '-b', default='mbk', help='set to blank to disable creating a backup (not recommended)')
    ap.add_argument('--file',           '-f', default='/home/ken/snap/arduino/current/.arduino15/packages/esp32/hardware/esp32/2.0.5/boards.txt')
    ap.add_argument('--strip-comments', '-s', action='store_true')
    ap.add_argument('--whitelist',      '-w', default='adafruit_qtpy_esp32s2,adafruit_qtpy_esp32s3_nopsram')
    args = ap.parse_args()

    if not os.path.isfile(args.file): sys.exit(f'unable to find file to process: {args.file}')
    if args.backup_suffix:
        backup_filename = f'{args.file}.{args.backup_suffix}'
        if not os.path.isfile(backup_filename):
            shutil.copyfile(args.file, backup_filename)
            print(f'created backup: {backup_filename}')

    tmp = args.file + '.tmp'
    if os.path.isfile(tmp): os.unlink(tmp)

    os.rename(args.file, tmp)

    wl = args.whitelist.split(',')
    in_set = set()
    out_set = set()
    prev_out = None  # remove duplicates (generally repeated white-space only lines).

    fout = open(args.file, 'w')
    for line in open(tmp).readlines():
        if args.strip_comments and line.startswith('#'): continue
        if '.' not in line or line.startswith('#') or line.startswith('menu'):
            if line == prev_out: continue
            fout.write(line)
            prev_out = line
            continue
        board, _ = line.split('.', 1)
        in_set.add(board)
        for i in wl:
            if line.startswith(i):
                out_set.add(board)
                fout.write(line)
                break
    fout.close()
    print(f'input boards: {len(in_set)}, output boards: {len(out_set)}')
    os.unlink(tmp)


if __name__ == '__main__': main()
