"""Reads map models straight from the game's PBOs (binarized ODOL) with the ODOL reader of DayZ Object Builder
(tools/ext/dzob, GPL, a local tool only) and writes their visual LOD for the snow generator.
    python odol_extract.py probe <shape>
    python odol_extract.py dump <list file> <out dir>     (one .npz per model)"""
import os, sys, struct, types, io, re, glob
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
EXT = os.path.join(HERE, 'ext', 'dzob', 'DZObjectBuilder', 'io')
pkg = types.ModuleType('dzio')
pkg.__path__ = [EXT]
sys.modules['dzio'] = pkg
from dzio import data_p3d_odol as O
ADDONS = r'C:\Program Files (x86)\Steam\steamapps\common\DayZ\Addons'

def pbo_entries(path):
    out = {}
    with open(path, 'rb') as f:
        def z():
            b = bytearray()
            while True:
                c = f.read(1)
                if not c or c == b'\x00':
                    return b.decode('latin-1')
                b += c
        prefix = ''
        ents = []
        while True:
            n = z()
            mime, orig, res, ts, size = struct.unpack('<5I', f.read(20))
            if n == '' and mime == 0x56657273:
                while True:
                    k = z()
                    if k == '':
                        break
                    v = z()
                    if k.lower() == 'prefix':
                        prefix = v
                continue
            if n == '':
                break
            ents.append((n, size, mime, orig))
        off = f.tell()
        for n, size, mime, orig in ents:
            full = (prefix + '\\' + n if prefix else n).lower()
            out[full] = (path, off, size, mime)
            off += size
    return out

_INDEX = None
def index():
    global _INDEX
    if _INDEX is None:
        _INDEX = {}
        for p in sorted(glob.glob(os.path.join(ADDONS, '*.pbo'))):
            try:
                for k, v in pbo_entries(p).items():
                    if k.endswith('.p3d'):
                        _INDEX[k] = v
            except Exception as ex:
                print('pbo fail', p, ex)
    return _INDEX

def read_model(shape):
    e = index().get(shape.lower())
    if not e:
        return None
    path, off, size, mime = e
    if mime != 0:
        raise RuntimeError('packed entry')
    with open(path, 'rb') as f:
        f.seek(off)
        data = f.read(size)
    return O.ODOL_File.read(io.BytesIO(data))

def visual_lod(m):
    best = None
    for lod in m.lods:
        if lod.resolution < 900 and lod.vertices and lod.faces:
            if best is None or lod.resolution < best.resolution:
                best = lod
    return best

if __name__ == '__main__':
    if sys.argv[1] == 'probe':
        m = read_model(sys.argv[2])
        print('version', m.version, 'lods', [round(r, 3) for r in m.resolutions], 'failed', m.failed_lods[:3])
        for lod in m.lods:
            print(' lod', lod.index, lod.resolution, 'v', len(lod.vertices), 'f', len(lod.faces), 'bb', lod.bbox_min, lod.bbox_max)
        v = visual_lod(m)
        print('face sample', v.faces[:2])
        print('tex', v.textures[:8])

