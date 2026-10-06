"""Stages source/SeasonZ for packing as several PBOs, each under the 2 GB that DSSignFile and the game can address:

  build/split/SeasonZ                  everything but data/baked                      -> SeasonZ.pbo, prefix SeasonZ
  build/split/SeasonZ_Baked_<letter>   the baked models whose name starts with it    -> SeasonZ_Baked_<letter>.pbo,
                                       plus a small config.cpp                          prefix SeasonZ_Baked_<letter>

The script side reads them through SZ_Const.BAKED (SeasonZ_Baked_<first letter>\\<name>_v<n>.p3d). The folder name is
the prefix, as AddonBuilder needs (binarize writes to temp\\<prefix>, packing takes temp\\<folder>). Files are hard
links to the sources (nothing is copied, AddonBuilder only reads them). Stale SeasonZ PBOs in the output folder are
removed. Prints one line per addon: <folder> <prefix> <MB of sources>. The sources (MLOD) are about four times the
binarised PBO; build-mvp.ps1 checks that every PBO stays under 2 GB (split a letter further if one ever does not).

  split_stage.py [--out build/mvp/@SeasonZ/addons]
"""
import argparse
import os
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SRC = PROJECT / 'source' / 'SeasonZ'
SPLIT = PROJECT / 'build' / 'split'

CONFIG = '''// SeasonZ: the snow baked per model, models starting with '{l}' (see SZ_Const.BAKED)
class CfgPatches
{{
\tclass {name}
\t{{
\t\tunits[] = {{}};
\t\tweapons[] = {{}};
\t\trequiredVersion = 0.1;
\t\trequiredAddons[] = {{}};
\t}};
}};
'''


def link(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(PROJECT / 'build' / 'mvp' / '@SeasonZ' / 'addons'))
    args = ap.parse_args()
    if SPLIT.exists():
        shutil.rmtree(SPLIT)
    sizes = {}
    baked = SRC / 'data' / 'baked'
    for root, _dirs, files in os.walk(SRC):
        r = Path(root)
        if r == baked or baked in r.parents:
            continue
        for n in files:
            link(r / n, SPLIT / 'SeasonZ' / r.relative_to(SRC) / n)
            sizes['SeasonZ'] = sizes.get('SeasonZ', 0) + (r / n).stat().st_size
    for f in sorted(baked.iterdir()):
        if f.suffix.lower() != '.p3d':
            continue
        letter = f.name[0].lower()
        if not letter.isalnum():
            raise SystemExit('baked model name must start with a letter or digit: ' + f.name)
        name = 'SeasonZ_Baked_' + letter
        link(f, SPLIT / name / f.name)
        sizes[name] = sizes.get(name, 0) + f.stat().st_size
    for name in sizes:
        if name != 'SeasonZ':
            l = name[len('SeasonZ_Baked_'):]
            (SPLIT / name / 'config.cpp').write_text(CONFIG.format(l=l, name=name), newline='\r\n')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    keep = {n.lower() + '.pbo' for n in sizes}
    for f in out.iterdir():
        base = f.name.lower().split('.pbo')[0] + '.pbo'
        if base.startswith('seasonz') and base not in keep:
            f.unlink()
    for name in sorted(sizes):
        print('%s %s %d' % (name, name, sizes[name] // 2 ** 20))


if __name__ == '__main__':
    main()
