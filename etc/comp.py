#!/usr/bin/python3

import argparse, os, sys


def parse_args():
    ap = argparse.ArgumentParser(description='file comparison tool')
    ap.add_argument('--base', '-b',      default='')
    ap.add_argument('--left_mod', '-L',  default='')
    ap.add_argument('--right_mod', '-R', default='')
    ap.add_argument('--verbose', '-v',   action='store_true')
    ap.add_argument('files', nargs='*',  default=[])
    return ap.parse_args()


def comp(left, right, verbose=False):
    try:
        if verbose: print(f'  comp: {left} =? {right}')
        left_stat = os.stat(left)
        right_stat = os.stat(right)
        if left_stat.st_size != right_stat.st_size: return False
        with open(left) as f: left_contents = f.read()
        with open(right) as f: right_contents = f.read()
        return left_contents == right_contents
    except:
        return None
    

def main():
    args = parse_args()
    if not args.files:
        if args.verbose: print('no files given to compare')
        return 0
    
    left_mods = args.left_mod.split('/', 1)
    right_mods = args.right_mod.split('/', 1)

    matches = []
    mismatches = []
    missing = []
    
    for f in args.files:
        left = os.path.join(args.base, f if not args.left_mod else f.replace(left_mods[0], left_mods[1]))
        right = f if not args.right_mod else f.replace(right_mods[0], right_mods[1])
        same = comp(left, right, args.verbose)
        if same is None: missing.append(left)
        elif same: matches.append(left)
        else: mismatches.append(left)

    if args.verbose:
        for i in matches: print(f'  matched: {i}')
        
    if len(missing) == 0 and len(mismatches) == 0:
        print(f'{args.base}: all {len(matches)} matched')
        return 0
        
    print(f'{args.base}: {len(matches)} matched;  {len(missing)} missing;  {len(missing)} mismatched:')
    for i in missing:    print(f'  MISSING: {i}')
    for i in mismatches: print(f'  MISMATCH: {i}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
