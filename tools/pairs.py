"""Side by side comparison sheet: pairs of images (before, after) with labels, one pair per row.

  pairs.py <out.png> <label> <before.png> <after.png> [<label> <before> <after> ...]
"""
import sys
from PIL import Image, ImageDraw, ImageFont

W, H = 800, 450


def main(argv):
    out = argv[1]
    items = argv[2:]
    rows = [items[i:i + 3] for i in range(0, len(items), 3)]
    font = ImageFont.truetype(r'C:\Windows\Fonts\segoeuib.ttf', 22)
    sheet = Image.new('RGB', (2 * W, len(rows) * H), (10, 10, 10))
    d = ImageDraw.Draw(sheet)
    for i, (label, a, b) in enumerate(rows):
        for k, path in enumerate((a, b)):
            im = Image.open(path).convert('RGB').resize((W, H), Image.LANCZOS)
            sheet.paste(im, (k * W, i * H))
            text = '%s %s' % (label, 'before' if k == 0 else 'after')
            d.rectangle([k * W, i * H, k * W + d.textlength(text, font=font) + 16, i * H + 34], fill=(0, 0, 0))
            d.text((k * W + 8, i * H + 4), text, font=font, fill=(255, 230, 120))
    sheet.save(out)
    print(out)


if __name__ == '__main__':
    main(sys.argv)
