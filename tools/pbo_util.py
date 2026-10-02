"""Minimal PBO reader for research: list entries and extract files (uncompressed or LZSS packed).

  pbo_util.py list <file.pbo> [filter]
  pbo_util.py extract <file.pbo> <out dir> [filter]
"""
import os
import struct
import sys


def read_cstr(data, pos):
    end = data.index(b'\0', pos)
    return data[pos:end].decode('latin-1'), end + 1


def parse(path):
    with open(path, 'rb') as fh:
        data = fh.read()
    pos = 0
    entries = []
    props = {}
    while True:
        name, pos = read_cstr(data, pos)
        method, orig, _res, _ts, size = struct.unpack_from('<5I', data, pos)
        pos += 20
        if name == '' and method == 0x56657273:
            while True:
                key, pos = read_cstr(data, pos)
                if key == '':
                    break
                val, pos = read_cstr(data, pos)
                props[key] = val
            continue
        if name == '':
            break
        entries.append([name, method, orig, size])
    offset = pos
    for e in entries:
        e.append(offset)
        offset += e[3]
    return data, entries, props


def lzss(src, out_len):
    out = bytearray()
    i = 0
    while len(out) < out_len and i < len(src):
        flags = src[i]
        i += 1
        for bit in range(8):
            if len(out) >= out_len or i >= len(src):
                break
            if flags & (1 << bit):
                out.append(src[i])
                i += 1
            else:
                b1, b2 = src[i], src[i + 1]
                i += 2
                rpos = len(out) - ((b1 | ((b2 & 0xF0) << 4)))
                rlen = (b2 & 0x0F) + 3
                for k in range(rlen):
                    p = rpos + k
                    out.append(out[p] if p >= 0 else 0x20)
    return bytes(out[:out_len])


def get(data, e):
    name, method, orig, size, off = e
    raw = data[off:off + size]
    if method == 0x43707273 or (orig and orig != size):
        return lzss(raw, orig)
    return raw


def main(argv):
    cmd, pbo = argv[1], argv[2]
    data, entries, props = parse(pbo)
    if cmd == 'list':
        filt = argv[3].lower() if len(argv) > 3 else ''
        print('props:', props)
        for e in entries:
            if filt in e[0].lower():
                print('%10d %10d %s' % (e[3], e[2], e[0]))
        return 0
    if cmd == 'extract':
        out = argv[3]
        filt = argv[4].lower() if len(argv) > 4 else ''
        n = 0
        for e in entries:
            if filt and filt not in e[0].lower():
                continue
            dest = os.path.join(out, e[0].replace('\\', os.sep))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'wb') as fh:
                fh.write(get(data, e))
            n += 1
        print('extracted %d files, prefix=%s' % (n, props.get('prefix')))
        return 0
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
