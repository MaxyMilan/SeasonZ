"""Visual QA sweep for SeasonZ: plans camera views of every structure model on the map and makes contact sheets.

  qa_sweep.py plan <buildscan.csv> <out dir> [kinds] [top]   one representative per model (the most common models
                                                            first when top is given, one view each)
  qa_sweep.py towns <buildscan.csv> <out dir> [cell] [min]   one aerial view over every cell of the map with at least
                                                            min large buildings (villages and towns)
  qa_sweep.py sheets <out dir> [per sheet]                   contact sheets of the captured views
"""
import csv
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FOV = 0.9            # vertical field of view of the sandbox camera (radians)
ELEVATION = math.radians(34)


def kind_of(row):
    s = row['shape']
    if row['rock'] in ('1', 'true', 'True') or '\\rocks' in s:
        return 'rock'
    if '\\walls\\' in s:
        return 'wall'
    if '\\wrecks\\' in s:
        return 'wreck'
    return 'building'


def load(path):
    rows = []
    with open(path, newline='', encoding='utf-8', errors='replace') as fh:
        for r in csv.DictReader(fh):
            try:
                for k in ('cx', 'cy', 'cz', 'dirx', 'dirz', 'sx', 'sy', 'sz', 'ground'):
                    r[k] = float(r[k])
            except (ValueError, KeyError):
                continue
            r['kind'] = kind_of(r)
            rows.append(r)
    return rows


SKIP = ('power_pole', 'power_hv', 'powerline', 'wire', 'rail_track', 'rail_polet', 'rail_poles', 'lamp_', 'decal',
        'football_line', 'garbage_ground', 'sign_', 'misc_flag', 'antenna', 'cable', 'tracke_', 'trackv_')


def wanted(r):
    k = r['kind']
    name = r['shape'].split('\\')[-1]
    if any(s in name for s in SKIP):
        return False
    span = max(r['sx'], r['sz'])
    if k == 'building':
        return span >= 2.5 and r['sy'] >= 1.6
    if k == 'wreck':
        return span >= 2.5
    if k == 'wall':
        return span >= 3.0 and r['sy'] >= 0.8
    if k == 'rock':
        return span >= 5.0
    return False


def clearance(rows):
    """distance from each structure to its nearest neighbour (centre to centre minus both radii)"""
    cell = 25.0
    grid = {}
    for i, r in enumerate(rows):
        grid.setdefault((int(r['cx'] // cell), int(r['cz'] // cell)), []).append(i)
    out = []
    for i, r in enumerate(rows):
        ri = 0.5 * math.hypot(r['sx'], r['sz'])
        best = 60.0
        gx, gz = int(r['cx'] // cell), int(r['cz'] // cell)
        for dx in (-2, -1, 0, 1, 2):
            for dz in (-2, -1, 0, 1, 2):
                for j in grid.get((gx + dx, gz + dz), ()):
                    if j == i:
                        continue
                    o = rows[j]
                    if o['kind'] in ('wall', 'rock'):
                        continue
                    rj = 0.5 * math.hypot(o['sx'], o['sz'])
                    d = math.hypot(o['cx'] - r['cx'], o['cz'] - r['cz']) - ri - rj
                    best = min(best, d)
        out.append(best)
    return out


def views(r):
    yaw = math.atan2(r['dirx'], r['dirz'])
    radius = 0.5 * math.sqrt(r['sx'] ** 2 + r['sy'] ** 2 + r['sz'] ** 2)
    dist = max(radius / math.sin(FOV * 0.5) * 1.08, 7.0)
    out = []
    offsets = (math.radians(35), math.radians(215))
    if r['kind'] == 'wall':
        offsets = (math.radians(90),) if r['sx'] >= r['sz'] else (0.0,)
    elif r['kind'] == 'rock':
        offsets = (math.radians(35),)
    for k, off in enumerate(offsets):
        a = yaw + off
        el = ELEVATION if r['kind'] != 'wall' else math.radians(24)
        cam = (r['cx'] + math.sin(a) * math.cos(el) * dist, r['cy'] + math.sin(el) * dist, r['cz'] + math.cos(a) * math.cos(el) * dist)
        out.append((k, cam, (r['cx'], r['cy'] - 0.15 * r['sy'], r['cz'])))
    return out


def ground_views(r):
    """eye level: 1.7 m above the ground, in front of the object and to the side, looking at its foot"""
    yaw = math.atan2(r['dirx'], r['dirz'])
    dist = 0.5 * max(r['sx'], r['sz']) + 7.0
    out = []
    for k, off in enumerate((math.radians(25), math.radians(205))):
        a = yaw + off
        cam = (r['cx'] + math.sin(a) * dist, 1.7, r['cz'] + math.cos(a) * dist)
        out.append((k, cam, (r['cx'], 0.6, r['cz'])))
    return out


def plan(scan, outdir, kinds, top=0, one_view=False, ground=False):
    rows = [r for r in load(scan) if wanted(r)]
    clear = clearance(rows)
    groups = {}
    for i, r in enumerate(rows):
        if r['kind'] in kinds:
            groups.setdefault(r['shape'], []).append(i)
    names = sorted(groups, key=lambda s: -len(groups[s]))
    if top:
        names = names[:top]
    shots = []
    for shape in names:
        idx = groups[shape]
        best = max(idx, key=lambda i: clear[i])
        r = rows[best]
        for k, cam, tgt in (ground_views(r) if ground else views(r)):
            if one_view and k > 0:
                continue
            shots.append({'shape': shape, 'type': r['type'], 'kind': r['kind'], 'count': len(idx), 'view': k,
                          'cam': cam, 'tgt': tgt, 'centre': (r['cx'], r['cy'], r['cz']), 'rel': ground})
    # visiting order: nearest neighbour, so the snow around the camera is mostly built already
    order = []
    left = list(range(len(shots)))
    cur = (7500.0, 0.0, 7500.0)
    while left:
        j = min(left, key=lambda i: (shots[i]['cam'][0] - cur[0]) ** 2 + (shots[i]['cam'][2] - cur[2]) ** 2)
        left.remove(j)
        order.append(shots[j])
        cur = shots[j]['cam']
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, 'plan.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['idx', 'tag', 'camx', 'camy', 'camz', 'tx', 'ty', 'tz', 'mode'])
        for n, s in enumerate(order):
            s['idx'] = n
            s['tag'] = 'q%04d' % n
            w.writerow([n, s['tag']] + ['%.2f' % v for v in s['cam']] + ['%.2f' % v for v in s['tgt']] + ['rel' if s.get('rel') else 'abs'])
    json.dump(order, open(os.path.join(outdir, 'plan.json'), 'w'), indent=1)
    kinds_count = {}
    for s in order:
        kinds_count[s['kind']] = kinds_count.get(s['kind'], 0) + 1
    print('structures %d, models %d, shots %d %s' % (len(rows), len(groups), len(order), kinds_count))


def sheets(outdir, per=9):
    shots = json.load(open(os.path.join(outdir, 'plan.json')))
    have = [s for s in shots if os.path.exists(os.path.join(outdir, 'shots', s['tag'] + '.png'))]
    font = ImageFont.truetype(r'C:\Windows\Fonts\segoeuib.ttf', 17)
    cols = 3
    tw, th = 672, 378
    os.makedirs(os.path.join(outdir, 'sheets'), exist_ok=True)
    made = 0
    for start in range(0, len(have), per):
        part = have[start:start + per]
        rows = (len(part) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * tw, rows * th), (12, 12, 12))
        d = ImageDraw.Draw(sheet)
        for i, s in enumerate(part):
            im = Image.open(os.path.join(outdir, 'shots', s['tag'] + '.png')).convert('RGB').resize((tw, th), Image.LANCZOS)
            x, y = (i % cols) * tw, (i // cols) * th
            sheet.paste(im, (x, y))
            name = s['shape'].split('\\')[-1].replace('.p3d', '')
            label = '%s %s v%d x%d' % (s['tag'], name, s['view'], s['count'])
            d.rectangle([x, y, x + d.textlength(label, font=font) + 12, y + 28], fill=(0, 0, 0))
            d.text((x + 6, y + 2), label, font=font, fill=(255, 230, 120))
        sheet.save(os.path.join(outdir, 'sheets', 'sheet_%03d.png' % (start // per)))
        made += 1
    print('sheets %d from %d shots' % (made, len(have)))


def towns(scan, outdir, cell=300.0, least=20):
    count = {}
    sumx = {}
    sumz = {}
    sumy = {}
    for r in load(scan):
        s = r['shape']
        if not any(k in s for k in ('\\residential\\', '\\industrial\\', '\\military\\', '\\specific\\')):
            continue
        if max(r['sx'], r['sz']) < 5 or r['sy'] < 3:
            continue
        key = (int(r['cx'] // cell), int(r['cz'] // cell))
        count[key] = count.get(key, 0) + 1
        sumx[key] = sumx.get(key, 0.0) + r['cx']
        sumz[key] = sumz.get(key, 0.0) + r['cz']
        sumy[key] = sumy.get(key, 0.0) + r['ground']
    shots = []
    for key, n in count.items():
        if n < least:
            continue
        tx, tz, ty = sumx[key] / n, sumz[key] / n, sumy[key] / n
        # from the south-west, 85 m up and 115 m away: the cell's buildings fill the view
        cam = (tx - 81.0, ty + 85.0, tz - 81.0)
        shots.append({'shape': 'town %d,%d' % key, 'type': '', 'kind': 'town', 'count': n, 'view': 0,
                      'cam': cam, 'tgt': (tx, ty, tz), 'centre': (tx, ty, tz)})
    order = []
    left = list(range(len(shots)))
    cur = (7500.0, 0.0, 7500.0)
    while left:
        j = min(left, key=lambda i: (shots[i]['cam'][0] - cur[0]) ** 2 + (shots[i]['cam'][2] - cur[2]) ** 2)
        left.remove(j)
        order.append(shots[j])
        cur = shots[j]['cam']
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, 'plan.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['idx', 'tag', 'camx', 'camy', 'camz', 'tx', 'ty', 'tz', 'mode'])
        for n, s in enumerate(order):
            s['idx'] = n
            s['tag'] = 't%04d' % n
            w.writerow([n, s['tag']] + ['%.2f' % v for v in s['cam']] + ['%.2f' % v for v in s['tgt']] + ['abs'])
    json.dump(order, open(os.path.join(outdir, 'plan.json'), 'w'), indent=1)
    print('town shots %d' % len(order))


if __name__ == '__main__':
    if sys.argv[1] == 'plan':
        kinds = sys.argv[4].split(',') if len(sys.argv) > 4 else ['building', 'wreck']
        top = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        plan(sys.argv[2], sys.argv[3], kinds, top, one_view=top > 0, ground=len(sys.argv) > 6 and sys.argv[6] == 'ground')
    elif sys.argv[1] == 'sheets':
        sheets(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 9)
    elif sys.argv[1] == 'towns':
        towns(sys.argv[2], sys.argv[3], float(sys.argv[4]) if len(sys.argv) > 4 else 300.0,
              int(sys.argv[5]) if len(sys.argv) > 5 else 20)
