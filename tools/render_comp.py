"""Joins the tiles of render_check.py into one sheet per model (OFF_<name>.jpg) and removes the tiles."""
import os, sys, re, glob
from PIL import Image, ImageDraw
out = sys.argv[1]
groups = {}
for p in glob.glob(os.path.join(out, '_tile_*.png')):
    m = re.match(r'_tile_(.+)_(\d)_v(\d)\.png', os.path.basename(p))
    groups.setdefault(m.group(1), []).append((int(m.group(2)), int(m.group(3)), p))
for name, tiles in groups.items():
    sheet = Image.new('RGB', (1600, 900))
    for k, var, p in sorted(tiles):
        im = Image.open(p).convert('RGB').resize((800, 450))
        ImageDraw.Draw(im).text((6, 4), '%s v%d' % (name, var), fill=(255, 255, 0))
        sheet.paste(im, ((k % 2) * 800, (k // 2) * 450))
        os.remove(p)
    sheet.save(os.path.join(out, 'OFF_%s.jpg' % name), quality=86)
    print(name)
