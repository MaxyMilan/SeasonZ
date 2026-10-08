#!/usr/bin/env python3
"""Asset generator for the SeasonZ DayZ mod.

Creates (all original, procedural):
  data/snow/sz_snow_s{1..4}_ca.png   albedo + coverage alpha per snow stage (converted to .paa)
  data/snow/sz_snow_nohq.png         normal map
  data/snow/sz_snow_smdi.png         specular/gloss map
  data/snow/sz_snow_s{1..4}.rvmat    Super shader materials (alpha tested)
  data/snow/sz_tri_{a,b,c,d}_s{1..4}.p3d   unit-cell terrain triangles (MLOD, binarized by AddonBuilder)
  data/lighting/sz_{base}_{01..10}.txt     lighting blends between the server lighting and snowy (Sakhal) lighting
"""
import os, re, struct, sys, subprocess
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'source', 'SeasonZ')
SNOW = os.path.join(SRC, 'data', 'snow')
LIGHT = os.path.join(SRC, 'data', 'lighting')
PREFIX = 'SeasonZ'
IMG2PAA = r'C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\ImageToPAA\ImageToPAA.exe'
LIGHT_SRC = os.path.join(os.environ['TEMP'], 'dzseason', 'cfg')
STAGE_COVERAGE = [0.30, 0.58, 0.82, 1.0]

rng = np.random.default_rng(20260930)

def tileable_noise(n, beta, seed):
    r = np.random.default_rng(seed)
    fx = np.fft.fftfreq(n)[:, None]
    fy = np.fft.fftfreq(n)[None, :]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1.0
    amp = f ** (-beta / 2.0)
    amp[0, 0] = 0.0
    phase = r.uniform(0, 2 * np.pi, (n, n))
    spec = amp * np.exp(1j * phase)
    img = np.real(np.fft.ifft2(spec))
    img -= img.min(); img /= img.max()
    return img

def equalize(a):
    flat = a.ravel()
    order = np.argsort(flat)
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.linspace(0.0, 1.0, flat.size)
    return ranks.reshape(a.shape)

def save_png(path, arr, mode):
    Image.fromarray(np.clip(arr * 255.0 + 0.5, 0, 255).astype(np.uint8), mode).save(path)

def make_textures():
    os.makedirs(SNOW, exist_ok=True)
    n = 1024
    low = tileable_noise(n, 3.2, 11)
    mid = tileable_noise(n, 2.2, 12)
    fine = tileable_noise(n, 1.2, 13)
    height = 0.55 * low + 0.3 * mid + 0.15 * fine
    shade = (height - height.mean())
    base = np.array([0.93, 0.945, 0.965])
    cool = np.array([-0.035, -0.02, 0.005])
    # fresh snow is nearly uniform: broad variation of a few percent, the rest comes from light and relief
    albedo = base[None, None, :] + shade[:, :, None] * 0.05 + (fine[:, :, None] - 0.5) * 0.03 + np.clip(-shade, 0, 1)[:, :, None] * cool * 2.0
    albedo = np.clip(albedo, 0, 1)
    coverage_field = equalize(0.6 * tileable_noise(n, 2.8, 21) + 0.4 * tileable_noise(n, 1.8, 22))
    for i, c in enumerate(STAGE_COVERAGE):
        if c >= 1.0:
            alpha = np.ones((n, n))
        else:
            alpha = np.clip((c - coverage_field) * 8.0 + 0.125, 0.0, 1.0)
        rgba = np.dstack([albedo, alpha])
        save_png(os.path.join(SNOW, 'sz_snow_s%d_ca.png' % (i + 1)), rgba, 'RGBA')
    # normal map from a height field in metres. The map repeats every 7.5 m (1024 px, 7.3 mm per pixel): soft wind
    # undulations of about a centimetre, small ripples of a millimetre and a faint crystal grain, together about
    # 4 degrees of tilt. Real snow tilts only a few degrees at these scales; stronger maps read as crumpled paper.
    px = 7.5 / n
    def unit(a):
        return (a - a.mean()) / a.std()
    hmap = 0.008 * unit(tileable_noise(n, 3.4, 41)) + 0.0012 * unit(tileable_noise(n, 2.4, 42)) + 0.00015 * unit(tileable_noise(n, 1.6, 43))
    gx = (np.roll(hmap, -1, 1) - np.roll(hmap, 1, 1)) / (2.0 * px)
    gy = (np.roll(hmap, -1, 0) - np.roll(hmap, 1, 0)) / (2.0 * px)
    tilt = np.degrees(np.arctan(np.sqrt(gx * gx + gy * gy)))
    print('normal map tilt: rms %.1f deg, 99%% %.1f deg' % (np.sqrt((tilt ** 2).mean()), np.percentile(tilt, 99)))
    nz = np.ones_like(gx)
    ln = np.sqrt(gx * gx + gy * gy + nz * nz)
    nrm = np.dstack([-gx / ln, -gy / ln, nz / ln]) * 0.5 + 0.5
    save_png(os.path.join(SNOW, 'sz_snow_nohq.png'), nrm, 'RGB')
    # specular: soft base with sparse small sparkles (ice crystals catching the sun)
    m = 512
    spark = rng.random((m, m)) > 0.9990
    spec = np.full((m, m), 0.12) + spark * 0.3
    gloss = np.full((m, m), 0.55)
    smdi = np.dstack([np.ones((m, m)), spec, gloss])
    save_png(os.path.join(SNOW, 'sz_snow_smdi.png'), smdi, 'RGB')
    # detail map: fine grain for close-up views. The engine reads detail textures (*_dt) from the ALPHA channel
    # only (TexConvert swizzles R, G and B from A) and fades the lower mipmaps to 0.5. The grain therefore goes into
    # the alpha channel with an average of exactly 0.5, so every mipmap has the same brightness: without alpha the
    # detail read as plain white, doubled the brightness near the camera and drew dark lines wherever the view
    # switched to a faded mipmap (slopes seen at a grazing angle, far away).
    d = 512
    grain = tileable_noise(d, 1.0, 31)
    grain = (grain - grain.mean()) / grain.std()
    detail = np.clip(0.5 + grain * 0.022, 0.0, 1.0)
    detail += 0.5 - detail.mean()
    print('detail map: mean %.4f, std %.4f' % (detail.mean(), detail.std()))
    save_png(os.path.join(SNOW, 'sz_snow_detail_dt.png'), np.dstack([detail, detail, detail, detail]), 'RGBA')

COVER_MAP = os.path.join(SRC, 'scripts', '4_World', 'SeasonZ', 'SZ_CoverMap.c')

# baked snow on roofs, rocks and structures in its open stages (1-3): a finer pattern than on the ground, so a light
# cover reads as a dusting with small patches of roof showing through instead of metre wide blotches
ROOF_COVERAGE = [0.38, 0.64, 0.86]

def make_roof_textures():
    n = 1024
    low = tileable_noise(n, 3.2, 11)
    mid = tileable_noise(n, 2.2, 12)
    fine = tileable_noise(n, 1.2, 13)
    height = 0.55 * low + 0.3 * mid + 0.15 * fine
    shade = (height - height.mean())
    base = np.array([0.93, 0.945, 0.965])
    cool = np.array([-0.035, -0.02, 0.005])
    albedo = base[None, None, :] + shade[:, :, None] * 0.05 + (fine[:, :, None] - 0.5) * 0.03 + np.clip(-shade, 0, 1)[:, :, None] * cool * 2.0
    albedo = np.clip(albedo, 0, 1)
    field = equalize(0.4 * tileable_noise(n, 2.4, 51) + 0.6 * tileable_noise(n, 1.1, 52))
    pngs = []
    for i, c in enumerate(ROOF_COVERAGE):
        alpha = np.clip((c - field) * 10.0 + 0.125, 0.0, 1.0)
        png = os.path.join(SNOW, 'sz_roofsnow_s%d_ca.png' % (i + 1))
        save_png(png, np.dstack([albedo, alpha]), 'RGBA')
        pngs.append(png)
        body = RVMAT % {'flags': 'renderFlags[]={"AlphaTest32"};\n', 'tex': '%s\\data\\snow\\sz_roofsnow_s%d_ca.paa' % (PREFIX, i + 1), 'prefix': PREFIX}
        with open(os.path.join(SNOW, 'sz_roofsnow_s%d.rvmat' % (i + 1)), 'w', newline='\r\n') as fh:
            fh.write(body)
    for png in pngs:
        subprocess.run([IMG2PAA, png, png[:-4] + '.paa'], check=True, capture_output=True)
        if not os.path.exists(png[:-4] + '.paa'):
            raise SystemExit('ImageToPAA failed for ' + png)
        os.remove(png)
COVER_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+/'

def make_cover_map(n=1024, size=128):
    """the coverage field of the snow textures for the scripts: footsteps and prints skip the bare spots"""
    field = equalize(0.6 * tileable_noise(n, 2.8, 21) + 0.4 * tileable_noise(n, 1.8, 22))
    k = n // size
    coarse = field.reshape(size, k, size, k).mean(axis=(1, 3))
    q = np.clip(np.round(coarse * 63), 0, 63).astype(int)
    rows = [''.join(COVER_ALPHABET[v] for v in row) for row in q]
    body = ',\n'.join('\t\t"%s"' % r for r in rows)
    cover = ', '.join('%.2f' % c for c in STAGE_COVERAGE)
    src = (
        '//! Generated by tools/make_assets.py (make_cover_map): the coverage field of the snow cover textures, %d x %d\n'
        '//! texels over one 30 m texture period, 64 levels per texel. A stage of the snow cover shows snow where the field\n'
        '//! is at most the coverage of the stage; footsteps and prints use it to skip the bare spots of thin snow.\n'
        'class SZ_CoverMap\n{\n'
        '\tstatic const int SIZE = %d;\n'
        '\tstatic const string ALPHABET = "%s";\n'
        '\tstatic const ref array<float> STAGE_COVERAGE = {%s};\n'
        '\tstatic const ref array<string> ROWS = {\n%s\n\t};\n'
        '\tprotected static ref array<int> s_Values;\n\n'
        '\tprotected static void Decode()\n\t{\n'
        '\t\ts_Values = new array<int>;\n'
        '\t\tfor (int r = 0; r < SIZE; r++)\n\t\t{\n'
        '\t\t\tstring row = ROWS[r];\n'
        '\t\t\tfor (int c = 0; c < SIZE; c++)\n\t\t\t{\n'
        '\t\t\t\tstring ch = row.Get(c);\n'
        '\t\t\t\ts_Values.Insert(ALPHABET.IndexOf(ch));\n'
        '\t\t\t}\n\t\t}\n\t}\n\n'
        '\t//! field value (0-1) at texture coordinates u, v (0-1, v from the top of the texture)\n'
        '\tstatic float Field(float u, float v)\n\t{\n'
        '\t\tif (!s_Values)\n\t\t\tDecode();\n'
        '\t\tint c = Math.Clamp(Math.Floor(u * SIZE), 0, SIZE - 1);\n'
        '\t\tint r = Math.Clamp(Math.Floor(v * SIZE), 0, SIZE - 1);\n'
        '\t\tfloat value = s_Values[r * SIZE + c];\n'
        '\t\treturn value / 63.0;\n\t}\n\n'
        '\t//! true where a snow cover triangle of this stage (1-4) and variant shows the ground at world x, z\n'
        '\tstatic bool IsBare(float x, float z, int stage, string variant)\n\t{\n'
        '\t\tif (stage >= 4 || stage < 1)\n\t\t\treturn stage < 1;\n'
        '\t\t// whole, half and quarter cells all take their place in the 30 m period\n'
        '\t\tfloat period = 30.0;\n'
        '\t\tfloat span = 1.0;\n'
        '\t\tfloat fx = x / period;\n'
        '\t\tfloat fz = z / period;\n'
        '\t\tfx = fx - Math.Floor(fx);\n'
        '\t\tfz = fz - Math.Floor(fz);\n'
        '\t\tfloat u = fx * span;\n'
        '\t\tfloat v = 1.0 - fz * span;\n'
        '\t\tfloat field = Field(u, v);\n'
        '\t\tfloat cover = STAGE_COVERAGE[stage - 1];\n'
        '\t\treturn field > cover;\n\t}\n}\n'
    ) % (size, size, size, COVER_ALPHABET, cover, body)
    with open(COVER_MAP, 'w', newline='\n') as fh:
        fh.write(src)
    print('cover map', size, 'x', size, 'bare share per stage', [round(float((coarse > c).mean()), 3) for c in STAGE_COVERAGE])

def convert_paa():
    for fn in sorted(os.listdir(SNOW)):
        if fn.endswith('.png'):
            src = os.path.join(SNOW, fn)
            dst = src[:-4] + '.paa'
            subprocess.run([IMG2PAA, src, dst], check=True, capture_output=True)
            if not os.path.exists(dst):
                raise SystemExit('ImageToPAA failed for ' + fn)
            os.remove(src)

# lighting response as the vanilla Sakhal snow: soft specular, the land environment map and fresnel of the snow
# layer on rocks (rm_boulder1_snow.rvmat). Snow scatters light, so part of the sunlight reaches the surface
# regardless of its angle to the sun (forced diffuse; the Sakhal road snow decals use 0.7, which washes a whole
# field out to white, 0.25 keeps the relief of the slopes readable).
RVMAT = '''ambient[]={1,1,1,1};
diffuse[]={1,1,1,1};
forcedDiffuse[]={0.25,0.25,0.25,0.25};
emmisive[]={0,0,0,1};
specular[]={0.25,0.25,0.25,0};
specularPower=10;
%(flags)sPixelShaderID="Super";
VertexShaderID="Super";
class TexGen0
{
	uvSource="tex";
	class uvTransform
	{
		aside[]={1,0,0};
		up[]={0,1,0};
		dir[]={0,0,1};
		pos[]={0,0,0};
	};
};
class TexGen1
{
	uvSource="tex";
	class uvTransform
	{
		aside[]={4,0,0};
		up[]={0,4,0};
		dir[]={0,0,1};
		pos[]={0,0,0};
	};
};
class TexGen2
{
	uvSource="tex";
	class uvTransform
	{
		aside[]={16,0,0};
		up[]={0,16,0};
		dir[]={0,0,1};
		pos[]={0,0,0};
	};
};
class Stage0
{
	texture="%(tex)s";
	texGen="0";
};
class Stage1
{
	texture="%(prefix)s\\data\\snow\\sz_snow_nohq.paa";
	texGen="1";
};
class Stage2
{
	texture="%(prefix)s\\data\\snow\\sz_snow_detail_dt.paa";
	texGen="2";
};
class Stage3
{
	texture="#(argb,8,8,3)color(0,0,0,0,MC)";
	texGen="0";
};
class Stage4
{
	texture="#(argb,8,8,3)color(1,1,1,1,AS)";
	texGen="0";
};
class Stage5
{
	texture="%(prefix)s\\data\\snow\\sz_snow_smdi.paa";
	texGen="1";
};
class Stage6
{
	texture="#(ai,32,128,1)fresnel(0.14,0.17)";
	texGen="0";
};
class Stage7
{
	texture="dz\\data\\data\\env_land_co.paa";
	texGen="0";
};
'''

def tex_path(stage):
    return '%s\\data\\snow\\sz_snow_s%d_ca.paa' % (PREFIX, stage)

def make_rvmats():
    for s in range(1, 5):
        flags = '' if STAGE_COVERAGE[s - 1] >= 1.0 else 'renderFlags[]={"AlphaTest32"};\n'
        body = RVMAT % {'flags': flags, 'tex': tex_path(s), 'prefix': PREFIX}
        with open(os.path.join(SNOW, 'sz_snow_s%d.rvmat' % s), 'w', newline='\r\n') as fh:
            fh.write(body)

# test only: a flat white material without any texture detail, for telling geometry from texture effects
DEBUG_RVMAT = '''ambient[]={1,1,1,1};
diffuse[]={1,1,1,1};
forcedDiffuse[]={0,0,0,0};
emmisive[]={0,0,0,1};
specular[]={0,0,0,0};
specularPower=1;
PixelShaderID="Super";
VertexShaderID="Super";
class Stage1
{
	texture="#(argb,8,8,3)color(0.5,0.5,1,1,NOHQ)";
	uvSource="tex";
};
class Stage2
{
	texture="#(argb,8,8,3)color(0.5,0.5,0.5,1,DT)";
	uvSource="tex";
};
class Stage3
{
	texture="#(argb,8,8,3)color(0,0,0,0,MC)";
	uvSource="tex";
};
class Stage4
{
	texture="#(argb,8,8,3)color(1,1,1,1,AS)";
	uvSource="tex";
};
class Stage5
{
	texture="#(argb,8,8,3)color(0,0,0,1,SMDI)";
	uvSource="tex";
};
class Stage6
{
	texture="#(ai,32,128,1)fresnel(0.01,0.01)";
	uvSource="tex";
};
class Stage7
{
	texture="#(argb,8,8,3)color(0,0,0,1,CO)";
	uvSource="tex";
};
'''

def make_debug():
    # test materials on the real full cell models: s6 = real material with a uniform detail texture file,
    # s7 = real material with the neutral procedural detail and stronger ambient/diffuse,
    # s8 = real material with a uniform brighter detail texture file
    flat_dt = '#(argb,8,8,3)color(0.5,0.5,0.5,1,DT)'
    real = RVMAT % {'flags': '', 'tex': tex_path(4), 'prefix': PREFIX}
    dt = '%s\\data\\snow\\sz_snow_detail_dt.paa' % PREFIX
    for name, value in (('sz_test_flat_dt', 0.5), ('sz_test_bright_dt', 0.6)):
        png = os.path.join(SNOW, name + '.png')
        save_png(png, np.full((64, 64, 3), value), 'RGB')
        subprocess.run([IMG2PAA, png, png[:-4] + '.paa'], check=True, capture_output=True)
        os.remove(png)
    boosted = real.replace(dt, flat_dt).replace('ambient[]={1,1,1,1};', 'ambient[]={1.4,1.4,1.4,1};').replace('diffuse[]={1,1,1,1};', 'diffuse[]={1.4,1.4,1.4,1};')
    variants = {
        6: (tex_path(4), real.replace(dt, '%s\\data\\snow\\sz_test_flat_dt.paa' % PREFIX)),
        7: (tex_path(4), boosted),
        8: (tex_path(4), real.replace(dt, '%s\\data\\snow\\sz_test_bright_dt.paa' % PREFIX)),
    }
    for s, (tex, body) in variants.items():
        with open(os.path.join(SNOW, 'sz_snow_dbg%d.rvmat' % s), 'w', newline='\r\n') as fh:
            fh.write(body)
    for key, corners in SHAPES.items():
        top = [(CORNERS[c][0], 0.0, CORNERS[c][1]) for c in corners]
        for name, cells, scale, a, b, depth in ground_variants():
            if len(name) != 2 or not name.isdigit():
                continue
            for s, (tex, body) in variants.items():
                mat = '%s\\data\\snow\\sz_snow_dbg%d.rvmat' % (PREFIX, s)
                lod = ground_lod(top, cells, scale, a, b, depth, tex, mat)
                write_mlod(os.path.join(SNOW, 'szk_%s%s_s%d.p3d' % (key, name, s)), [lod])

def ground_lod(top, cells, scale, a, b, depth, tex, mat):
    size = GROUND_CELL * cells
    uvs = [((a + 0.5 + p[0]) * scale, 4.0 - (b + 0.5 + p[2]) * scale) for p in top]
    real = [(p[0] * size, 0.0, p[2] * size) for p in top]
    # points 0-2: the triangle, 3-5: the same corners at the bottom of the skirt
    pts = real + [(p[0], -depth, p[2]) for p in real]
    period = GROUND_CELL * 4.0
    faces = [{'verts': [(i, 0, uvs[i][0], uvs[i][1]) for i in range(3)], 'texture': tex, 'material': mat}]
    for i, j in ((0, 1), (1, 2), (2, 0)):
        a_top = (i, 0, uvs[i][0] + 8.0, uvs[i][1])
        b_top = (j, 0, uvs[j][0] + 8.0, uvs[j][1])
        a_bot = (i + 3, 0, uvs[i][0] + 8.0, uvs[i][1] + depth / period)
        b_bot = (j + 3, 0, uvs[j][0] + 8.0, uvs[j][1] + depth / period)
        faces.append({'verts': [a_top, b_top, b_bot], 'texture': tex, 'material': mat})
        faces.append({'verts': [a_top, b_bot, a_bot], 'texture': tex, 'material': mat})
        faces.append({'verts': [b_top, a_top, a_bot], 'texture': tex, 'material': mat})
        faces.append({'verts': [b_top, a_bot, b_bot], 'texture': tex, 'material': mat})
    return mlod_lod(pts, faces, 1.0, props=(('lodnoshadow', '1'),))

# ---------------- MLOD writer ----------------
def asciiz(s):
    return s.encode('ascii') + b'\x00'

def mlod_lod(points, faces, resolution, props=(), selections=None, mass=None):
    # MLOD stores normals pointing into the surface (snow_craft writes -n for the same reason): index 0 is the
    # normal of a face that looks up, index 1 of a face that looks down. Written the other way round the game lit
    # the ground cover, the roof pieces, prints, tracks and ice as if they faced the ground (ambient light and the
    # forced diffuse share only), so the ground snow read grey blue next to the baked roofs.
    normals = [(0.0, -1.0, 0.0), (0.0, 1.0, 0.0)]
    out = bytearray(b'P3DM')
    out += struct.pack('<IIIIII', 0x1C, 0x100, len(points), len(normals), len(faces), 0)
    for (x, y, z) in points:
        out += struct.pack('<fffI', x, y, z, 0)
    for (x, y, z) in normals:
        out += struct.pack('<fff', x, y, z)
    for f in faces:
        verts = f['verts']
        out += struct.pack('<I', len(verts))
        for i in range(4):
            if i < len(verts):
                p, nidx, u, v = verts[i]
            else:
                p, nidx, u, v = 0, 0, 0.0, 0.0
            out += struct.pack('<IIff', p, nidx, u, v)
        out += struct.pack('<I', 0)
        out += asciiz(f['texture']) + asciiz(f['material'])
    out += b'TAGG'
    def tag(name, data):
        out.extend(b'\x01' + asciiz(name) + struct.pack('<I', len(data)) + data)
    for k, v in props:
        tag('#Property#', k.encode('ascii').ljust(64, b'\x00') + v.encode('ascii').ljust(64, b'\x00'))
    if mass is not None:
        tag('#Mass#', b''.join(struct.pack('<f', m) for m in mass))
    for name, (pts_sel, faces_sel) in (selections or {}).items():
        data = bytes(1 if i in pts_sel else 0 for i in range(len(points))) + bytes(1 if i in faces_sel else 0 for i in range(len(faces)))
        tag(name, data)
    uv = struct.pack('<I', 0)
    for f in faces:
        for (p, nidx, u, v) in f['verts']:
            uv += struct.pack('<ff', u, v)
    tag('#UVSet#', uv)
    tag('#EndOfFile#', b'')
    out += struct.pack('<f', resolution)
    return bytes(out)

def write_mlod(path, lods):
    data = bytearray(b'MLOD') + struct.pack('<II', 257, len(lods))
    for l in lods:
        data += l
    with open(path, 'wb') as fh:
        fh.write(data)

# unit cell centred on origin; corner names: c00=(-.5,-.5) c10=(.5,-.5) c11=(.5,.5) c01=(-.5,.5)
CORNERS = {'c00': (-0.5, -0.5), 'c10': (0.5, -0.5), 'c11': (0.5, 0.5), 'c01': (-0.5, 0.5)}
SHAPES = {
    'a': ('c00', 'c10', 'c11'),
    'b': ('c00', 'c11', 'c01'),
    'c': ('c00', 'c10', 'c01'),
    'd': ('c10', 'c11', 'c01'),
}

def model_variants():
    # texture period = 4 terrain cells; a level 0 cell (and a roof triangle) picks the variant matching
    # (ix mod 4, iz mod 4), so the pattern continues across cells
    out = []
    for a in range(4):
        for b in range(4):
            out.append(('%d%d' % (a, b), 0.25, a, b))
    return out

# ground cover models are made at their real size for the 7.5 m terrain grid of Chernarus (other grids scale them),
# so the engine draws them without any horizontal scaling: the normal map keeps one strength on every level and the
# bounding volume matches the drawn triangle.
GROUND_CELL = 7.5

# variant, size in terrain cells, texture span of the square, texture offset in squares, skirt depth in metres.
# The snow texture repeats every 4 terrain cells (30 m). Whole cells (00-33), half cells next to buildings
# (h00-h77) and the double cells of the first coarse level (d00-d11) take their exact place in that period, so the
# pattern continues across every cell. Quarter cells (q0000-q1515) also take their exact place in the period, so the
# coverage of a partial stage runs on across them. The coarse levels (f4, f16, f32) span whole periods.
def ground_variants():
    out = []
    for a in range(4):
        for b in range(4):
            out.append(('%d%d' % (a, b), 1.0, 0.25, a, b, 1.5))
    for a in range(8):
        for b in range(8):
            out.append(('h%d%d' % (a, b), 0.5, 0.125, a, b, 1.5))
    # quarter cells take their exact place in the 30 m period as well (16 x 16 of them): when they repeated the first
    # cell of the period, the coverage pattern of a partial snow stage broke along their edges next to buildings
    for a in range(16):
        for b in range(16):
            out.append(('q%02d%02d' % (a, b), 0.25, 0.0625, a, b, 1.5))
    for a in range(2):
        for b in range(2):
            out.append(('d%d%d' % (a, b), 2.0, 0.5, a, b, 2.5))
    out.append(('f4', 4.0, 1.0, 0, 0, 3.5))
    out.append(('f16', 16.0, 4.0, 0, 0, 6.0))
    out.append(('f32', 32.0, 8.0, 0, 0, 8.0))
    return out

def make_models():
    for fn in os.listdir(SNOW):
        if fn.endswith('.p3d'):
            os.remove(os.path.join(SNOW, fn))
    for key, corners in SHAPES.items():
        top = [(CORNERS[c][0], 0.0, CORNERS[c][1]) for c in corners]
        for name, scale, a, b in model_variants():
            uvs = [((a + 0.5 + p[0]) * scale, 4.0 - (b + 0.5 + p[2]) * scale) for p in top]
            for s in range(1, 5):
                tex = tex_path(s)
                mat = '%s\\data\\snow\\sz_snow_s%d.rvmat' % (PREFIX, s)
                # single sided, front face up (corner order as listed in SHAPES)
                face = {'verts': [(i, 0, uvs[i][0], uvs[i][1]) for i in range(3)], 'texture': tex, 'material': mat}
                lod = mlod_lod(top, [face], 1.0, props=(('lodnoshadow', '1'),))
                write_mlod(os.path.join(SNOW, 'sz_%s%s_s%d.p3d' % (key, name, s)), [lod])
        # ground cover. Skirts: a strip under each edge, drawn from both sides and lit like the snow surface, so a
        # crack or a small step between neighbouring triangles shows snow instead of the ground. Their top corners
        # sample the texture exactly like the surface edge above them (shifted by whole repeats, so they never share
        # vertices with the surface and cannot bend its normal map). Binarising centres the model on its bounding
        # box, which moves the triangle up by half the skirt depth; the script puts it back.
        for name, cells, scale, a, b, depth in ground_variants():
            size = GROUND_CELL * cells
            uvs = [((a + 0.5 + p[0]) * scale, 4.0 - (b + 0.5 + p[2]) * scale) for p in top]
            real = [(p[0] * size, 0.0, p[2] * size) for p in top]
            # points 0-2: the triangle, 3-5: the same corners at the bottom of the skirt
            pts = real + [(p[0], -depth, p[2]) for p in real]
            period = GROUND_CELL * 4.0
            for s in range(1, 5):
                tex = tex_path(s)
                mat = '%s\\data\\snow\\sz_snow_s%d.rvmat' % (PREFIX, s)
                faces = [{'verts': [(i, 0, uvs[i][0], uvs[i][1]) for i in range(3)], 'texture': tex, 'material': mat}]
                for i, j in ((0, 1), (1, 2), (2, 0)):
                    a_top = (i, 0, uvs[i][0] + 8.0, uvs[i][1])
                    b_top = (j, 0, uvs[j][0] + 8.0, uvs[j][1])
                    a_bot = (i + 3, 0, uvs[i][0] + 8.0, uvs[i][1] + depth / period)
                    b_bot = (j + 3, 0, uvs[j][0] + 8.0, uvs[j][1] + depth / period)
                    faces.append({'verts': [a_top, b_top, b_bot], 'texture': tex, 'material': mat})
                    faces.append({'verts': [a_top, b_bot, a_bot], 'texture': tex, 'material': mat})
                    faces.append({'verts': [b_top, a_top, a_bot], 'texture': tex, 'material': mat})
                    faces.append({'verts': [b_top, a_bot, b_bot], 'texture': tex, 'material': mat})
                lod = mlod_lod(pts, faces, 1.0, props=(('lodnoshadow', '1'),))
                write_mlod(os.path.join(SNOW, 'szk_%s%s_s%d.p3d' % (key, name, s)), [lod])

# ---------------- lighting blends ----------------
NUM = re.compile(r'-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?')

# roof snow: the unit roof triangle on top of a skirt one unit deep, drawn from both sides. The script scales the
# skirt to the thickness of the snow, so the snow on roofs, walls and wrecks lies as a slab with snowy sides.
def make_roof_models():
    for fn in os.listdir(SNOW):
        if (fn.startswith('szr_') or fn.startswith('szq') or fn.startswith('szf')) and fn.endswith('.p3d'):
            os.remove(os.path.join(SNOW, fn))
    count = 0
    for key, corners in SHAPES.items():
        top = [(CORNERS[c][0], 0.0, CORNERS[c][1]) for c in corners]
        pts = top + [(p[0], -1.0, p[2]) for p in top]
        for name, scale, a, b in model_variants():
            uvs = [((a + 0.5 + p[0]) * scale, 4.0 - (b + 0.5 + p[2]) * scale) for p in top]
            for s in range(1, 5):
                tex = tex_path(s)
                mat = '%s\\data\\snow\\sz_snow_s%d.rvmat' % (PREFIX, s)
                faces = [{'verts': [(i, 0, uvs[i][0], uvs[i][1]) for i in range(3)], 'texture': tex, 'material': mat}]
                for i, j in ((0, 1), (1, 2), (2, 0)):
                    a_top = (i, 0, uvs[i][0] + 8.0, uvs[i][1])
                    b_top = (j, 0, uvs[j][0] + 8.0, uvs[j][1])
                    a_bot = (i + 3, 0, uvs[i][0] + 8.0, uvs[i][1] + 0.05)
                    b_bot = (j + 3, 0, uvs[j][0] + 8.0, uvs[j][1] + 0.05)
                    faces.append({'verts': [a_top, b_top, b_bot], 'texture': tex, 'material': mat})
                    faces.append({'verts': [a_top, b_bot, a_bot], 'texture': tex, 'material': mat})
                    faces.append({'verts': [b_top, a_top, a_bot], 'texture': tex, 'material': mat})
                    faces.append({'verts': [b_top, a_bot, b_bot], 'texture': tex, 'material': mat})
                lod = mlod_lod(pts, faces, 1.0, props=(('lodnoshadow', '1'),))
                write_mlod(os.path.join(SNOW, 'szr_%s%s_s%d.p3d' % (key, name, s)), [lod])
                count += 1
    # squares of 1, 2, 4 and 8 grid cells: one object for a square instead of two triangles. Their texture keeps
    # the scale of the single cells (a square of span cells covers span quarters of the texture), and the variant
    # (a, b) is the square's place in the 4 cell texture period, so the pattern runs on across squares of any size
    quad = [(-0.5, 0.0, -0.5), (0.5, 0.0, -0.5), (0.5, 0.0, 0.5), (-0.5, 0.0, 0.5)]
    qpts = quad + [(p[0], -1.0, p[2]) for p in quad]
    for span, offsets in ((1, range(4)), (2, (0, 2)), (4, (0,)), (8, (0,))):
        for a in offsets:
            for b in offsets:
                uvs = [((a + span * (0.5 + p[0])) * 0.25, 4.0 - (b + span * (0.5 + p[2])) * 0.25) for p in quad]
                for s in range(1, 5):
                    tex = tex_path(s)
                    mat = '%s\\data\\snow\\sz_snow_s%d.rvmat' % (PREFIX, s)
                    faces = [{'verts': [(i, 0, uvs[i][0], uvs[i][1]) for i in range(4)], 'texture': tex, 'material': mat}]
                    for i, j in ((0, 1), (1, 2), (2, 3), (3, 0)):
                        a_top = (i, 0, uvs[i][0] + 8.0, uvs[i][1])
                        b_top = (j, 0, uvs[j][0] + 8.0, uvs[j][1])
                        a_bot = (i + 4, 0, uvs[i][0] + 8.0, uvs[i][1] + 0.05)
                        b_bot = (j + 4, 0, uvs[j][0] + 8.0, uvs[j][1] + 0.05)
                        faces.append({'verts': [a_top, b_top, b_bot], 'texture': tex, 'material': mat})
                        faces.append({'verts': [a_top, b_bot, a_bot], 'texture': tex, 'material': mat})
                        faces.append({'verts': [b_top, a_top, a_bot], 'texture': tex, 'material': mat})
                        faces.append({'verts': [b_top, a_bot, b_bot], 'texture': tex, 'material': mat})
                    lod = mlod_lod(qpts, faces, 1.0, props=(('lodnoshadow', '1'),))
                    write_mlod(os.path.join(SNOW, 'szq%d%d%d_s%d.p3d' % (span, a, b, s)), [lod])
                    count += 1
    # free pieces at the edges of roof planes: the c triangle with the texture of 2, 4 or 8 cells, so a large piece
    # shows the snow at about the scale of the cells around it instead of magnified
    top = [(CORNERS[c][0], 0.0, CORNERS[c][1]) for c in SHAPES['c']]
    fpts = top + [(p[0], -1.0, p[2]) for p in top]
    for span in (2, 4):
        uvs = [((span * (0.5 + p[0])) * 0.25, 4.0 - (span * (0.5 + p[2])) * 0.25) for p in top]
        for s in range(1, 5):
            tex = tex_path(s)
            mat = '%s\\data\\snow\\sz_snow_s%d.rvmat' % (PREFIX, s)
            faces = [{'verts': [(i, 0, uvs[i][0], uvs[i][1]) for i in range(3)], 'texture': tex, 'material': mat}]
            for i, j in ((0, 1), (1, 2), (2, 0)):
                a_top = (i, 0, uvs[i][0] + 8.0, uvs[i][1])
                b_top = (j, 0, uvs[j][0] + 8.0, uvs[j][1])
                a_bot = (i + 3, 0, uvs[i][0] + 8.0, uvs[i][1] + 0.05)
                b_bot = (j + 3, 0, uvs[j][0] + 8.0, uvs[j][1] + 0.05)
                faces.append({'verts': [a_top, b_top, b_bot], 'texture': tex, 'material': mat})
                faces.append({'verts': [a_top, b_bot, a_bot], 'texture': tex, 'material': mat})
                faces.append({'verts': [b_top, a_top, a_bot], 'texture': tex, 'material': mat})
                faces.append({'verts': [b_top, a_bot, b_bot], 'texture': tex, 'material': mat})
            lod = mlod_lod(fpts, faces, 1.0, props=(('lodnoshadow', '1'),))
            write_mlod(os.path.join(SNOW, 'szf%d_s%d.p3d' % (span, s)), [lod])
            count += 1
    print('roof models', count)

def blend_lighting(base_path, target_path, out_prefix):
    base = open(base_path, encoding='latin-1').read().splitlines()
    tgt = open(target_path, encoding='latin-1').read().splitlines()
    if len(base) != len(tgt):
        raise SystemExit('lighting line count mismatch %s %s' % (base_path, target_path))
    # per line: which class block + its sunAngle
    block_angle = []
    current = None
    angles = {}
    for line in base:
        m = re.match(r'\s*class\s+(\w+)', line)
        if m:
            current = m.group(1)
        a = re.match(r'\s*sunAngle\s*=\s*(-?[\d.]+)', line)
        if a and current:
            angles[current] = float(a.group(1))
        block_angle.append(current)
    for step in range(1, 11):
        t = step / 10.0
        out = []
        for i, (lb, lt) in enumerate(zip(base, tgt)):
            cls = block_angle[i]
            ang = angles.get(cls, 0.0)
            w = t
            if ang <= -8:
                w = 0.0
            elif ang < 0:
                w = t * (ang + 8) / 8.0
            nb = NUM.findall(lb); nt = NUM.findall(lt)
            sb = NUM.sub('#', lb); st = NUM.sub('#', lt)
            if w <= 0 or len(nb) != len(nt) or sb != st or not nb or re.match(r'\s*(height|overcast|sunAngle|sunOrMoon)\s*=', lb):
                out.append(lb)
                continue
            vals = ['%.5g' % (float(a) + (float(b) - float(a)) * w) for a, b in zip(nb, nt)]
            it = iter(vals)
            out.append(NUM.sub(lambda m: next(it), lb))
        with open(os.path.join(LIGHT, '%s_%02d.txt' % (out_prefix, step)), 'w', encoding='latin-1', newline='\r\n') as fh:
            fh.write('\n'.join(out) + '\n')

def make_lighting():
    os.makedirs(LIGHT, exist_ok=True)
    sakhal = os.path.join(LIGHT_SRC, 'worlds_sakhal_data', 'lighting', 'lighting_sakhal.txt')
    blend_lighting(os.path.join(LIGHT_SRC, 'dz', 'lighting', 'lighting_default.txt'), sakhal, 'sz_default')
    blend_lighting(os.path.join(LIGHT_SRC, 'dz', 'lighting', 'lighting_darknight.txt'), sakhal, 'sz_darknight')

# ---------------- footprints ----------------
PRINTS = os.path.join(SRC, 'data', 'prints')

# lit like the snow cover (same specular, fresnel and environment map), so the print only differs by its relief.
# Alpha tested like the cover: blended surfaces receive no shadows, a print in the shade of a wall would glow.
PRINT_RVMAT = '''ambient[]={1,1,1,1};
diffuse[]={1,1,1,1};
forcedDiffuse[]={0.25,0.25,0.25,0.25};
emmisive[]={0,0,0,1};
specular[]={0.25,0.25,0.25,0};
specularPower=10;
renderFlags[]={"AlphaTest64"};
PixelShaderID="Super";
VertexShaderID="Super";
class Stage1
{
	texture="%(nohq)s";
	uvSource="tex";
};
class Stage2
{
	texture="#(argb,8,8,3)color(0.5,0.5,0.5,0.5,DT)";
	uvSource="tex";
};
class Stage3
{
	texture="#(argb,8,8,3)color(0,0,0,0,MC)";
	uvSource="tex";
};
class Stage4
{
	texture="%(ao)s";
	uvSource="tex";
};
class Stage5
{
	texture="%(smdi)s";
	uvSource="tex";
};
class Stage6
{
	texture="#(ai,32,128,1)fresnel(0.14,0.17)";
	uvSource="none";
};
class Stage7
{
	texture="dz\\data\\data\\env_land_co.paa";
	uvSource="none";
};
'''

# print quad in metres (across x, along y; the toe points to +y) and texture size
PRINT_W, PRINT_L = 0.24, 0.44
PRINT_TW, PRINT_TH = 256, 512
# depth of the boot below the snow surface, height of the snow pushed up around it and relief of the sole lugs
PRINT_KINDS = {
    'shallow': dict(depth=0.022, rim=0.005, lug=0.0015, geo=False),
    'deep': dict(depth=0.050, rim=0.012, lug=0.0030, geo=True),
}

def print_field():
    """signed distance (m) to the outline of a left boot sole, negative inside, on the texture grid"""
    xs = ((np.arange(PRINT_TW) + 0.5) / PRINT_TW - 0.5) * PRINT_W
    ys = (0.5 - (np.arange(PRINT_TH) + 0.5) / PRINT_TH) * PRINT_L      # row 0 = toe end (+y)
    X, Y = np.meshgrid(xs, ys)
    def ell(cx, cy, rx, ry):
        return ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2 <= 1.0
    mask = ell(0.006, 0.065, 0.052, 0.085) | ell(-0.004, -0.02, 0.036, 0.06) | ell(-0.002, -0.09, 0.040, 0.055)
    # boundary pixels and an exact distance to them (chunked brute force, the grid is small)
    inner = mask.copy()
    inner[1:-1, 1:-1] = mask[1:-1, 1:-1] & mask[:-2, 1:-1] & mask[2:, 1:-1] & mask[1:-1, :-2] & mask[1:-1, 2:]
    edge = mask & ~inner
    ex, ey = X[edge], Y[edge]
    px, py = X.ravel(), Y.ravel()
    dist = np.empty(px.size)
    for i in range(0, px.size, 4096):
        dx = px[i:i + 4096, None] - ex[None, :]
        dy = py[i:i + 4096, None] - ey[None, :]
        dist[i:i + 4096] = np.sqrt((dx * dx + dy * dy).min(1))
    dist = dist.reshape(X.shape)
    return np.where(mask, -dist, dist), X, Y

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)

def print_height(kind, sdf, X, Y, seed):
    p = PRINT_KINDS[kind]
    r = np.random.default_rng(seed)
    # soft lumps rather than grain: snow pushed aside breaks into rounded clods of a few centimetres
    noise = tileable_noise(512, 3.4, seed)[:PRINT_TH, :PRINT_TW]
    noise = (noise - noise.mean()) / noise.std()
    wall = 0.010
    inside = smoothstep(0.0, wall, -sdf)
    # deeper under the ball of the foot (push off) and the heel (strike)
    press = 1.0 + 0.18 * smoothstep(0.02, 0.10, Y) + 0.10 * smoothstep(-0.08, -0.13, Y)
    # tread: transverse bars with a split down the middle, only on the floor of the print
    bars = (np.sin(2 * np.pi * Y / 0.017) > 0.15) & (np.abs(X - 0.002) > 0.006)
    floor = smoothstep(0.004, 0.012, -sdf - wall)
    h = -p['depth'] * press * inside + p['lug'] * bars * floor
    # snow pushed up and outwards: a ridge about a centimetre outside the wall, uneven like crumbled snow
    ridge = np.exp(-((sdf - 0.011) / 0.010) ** 2) * (sdf > -0.002)
    h += p['rim'] * ridge * np.clip(0.75 + 0.35 * noise, 0.2, 1.4)
    # crumbs: small lumps on the rim and along the walls
    h += 0.0008 * noise * np.exp(-((sdf - 0.004) / 0.012) ** 2)
    # the print fades into the surrounding snow
    fade = 1.0 - smoothstep(0.022, 0.050, sdf)
    return h * fade, fade

def normal_map(h, green_down=True):
    pu = PRINT_W / PRINT_TW
    pv = PRINT_L / PRINT_TH
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * pu)
    gr = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * pv)     # per row, rows run from the toe to the heel
    gx[:, 0] = gx[:, -1] = 0
    gr[0, :] = gr[-1, :] = 0
    n = np.dstack([-gx, -gr, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    if not green_down:
        n[..., 1] = -n[..., 1]
    return n * 0.5 + 0.5

def ambient_occlusion(h):
    """how much of the sky a point sees: the depth below the surrounding surface, blurred"""
    k = 9
    pad = np.pad(h, k, mode='edge')
    acc = np.zeros_like(h)
    for dy in range(-k, k + 1, 3):
        for dx in range(-k, k + 1, 3):
            acc += pad[k + dy:k + dy + h.shape[0], k + dx:k + dx + h.shape[1]]
    local = acc / (len(range(-k, k + 1, 3)) ** 2)
    below = np.clip(local - h, 0, None)
    return np.clip(1.0 - below / 0.02 * 0.35 - np.clip(-h, 0, None) / 0.05 * 0.25, 0.45, 1.0)

def paa(png):
    subprocess.run([IMG2PAA, png, png[:-4] + '.paa'], check=True, capture_output=True)
    os.remove(png)

def print_mesh(kind, h, mirror):
    """flat quad, or for deep prints a grid whose vertices rise with the snow pushed up around the boot"""
    if not PRINT_KINDS[kind]['geo']:
        pts = [(-PRINT_W / 2, 0.0, -PRINT_L / 2), (PRINT_W / 2, 0.0, -PRINT_L / 2), (PRINT_W / 2, 0.0, PRINT_L / 2), (-PRINT_W / 2, 0.0, PRINT_L / 2)]
        quads = [(0, 1, 2, 3)]
        return pts, quads
    nx, ny = 13, 23
    pts = []
    for j in range(ny):
        for i in range(nx):
            u = i / (nx - 1)
            v = j / (ny - 1)
            uu = 1.0 - u if mirror else u
            col = min(PRINT_TW - 1, int(uu * (PRINT_TW - 1)))
            row = min(PRINT_TH - 1, int((1 - v) * (PRINT_TH - 1)))
            # only the raised snow is geometry; the hollow stays on the base plane (it is drawn by the normal map)
            y = max(0.0, float(h[row, col])) * 0.8
            pts.append(((u - 0.5) * PRINT_W, y, (v - 0.5) * PRINT_L))
    quads = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            quads.append((a, a + 1, a + nx + 1, a + nx))
    return pts, quads

def write_print_model(path, pts, quads, tex, mat, mirror):
    """the right foot uses the left foot texture mirrored through its UVs"""
    def uvof(p):
        uu = p[0] / PRINT_W + 0.5
        vv = 0.5 - p[2] / PRINT_L
        if mirror:
            uu = 1.0 - uu
        return uu, vv
    faces = []
    for (a, b, c, d) in quads:
        for t in ((a, b, c), (a, c, d)):
            faces.append({'verts': [(k, 0, uvof(pts[k])[0], uvof(pts[k])[1]) for k in t], 'texture': tex, 'material': mat})
    lod = mlod_lod(pts, faces, 1.0, props=(('lodnoshadow', '1'),))
    write_mlod(path, [lod])

def make_prints(test=False):
    os.makedirs(PRINTS, exist_ok=True)
    for fn in os.listdir(PRINTS):
        os.remove(os.path.join(PRINTS, fn))
    sdf, X, Y = print_field()
    smdi = np.dstack([np.ones((64, 64)), np.full((64, 64), 0.12), np.full((64, 64), 0.55)])
    save_png(os.path.join(PRINTS, 'sz_print_smdi.png'), smdi, 'RGB'); paa(os.path.join(PRINTS, 'sz_print_smdi.png'))
    base = np.array([0.93, 0.945, 0.965])
    for n_kind, kind in enumerate(PRINT_KINDS):
        h, fade = print_height(kind, sdf, X, Y, 70 + n_kind)
        ao = ambient_occlusion(h)
        depth01 = np.clip(-h / PRINT_KINDS[kind]['depth'], 0, 1)
        # compressed snow on the floor is a little greyer and bluer; the walls are shaded by the AO map
        col = base[None, None, :] * (1.0 - 0.05 * depth01[..., None]) + np.array([-0.02, -0.01, 0.0])[None, None, :] * depth01[..., None]
        # the print ends where its relief has faded out; the colour there equals the snow cover's
        alpha = (fade > 0.35).astype(float)
        save_png(os.path.join(PRINTS, 'sz_print_%s_ca.png' % kind), np.dstack([np.clip(col, 0, 1), alpha]), 'RGBA')
        paa(os.path.join(PRINTS, 'sz_print_%s_ca.png' % kind))
        save_png(os.path.join(PRINTS, 'sz_print_%s_as.png' % kind), np.dstack([ao, ao, ao]), 'RGB')
        paa(os.path.join(PRINTS, 'sz_print_%s_as.png' % kind))
        variants = [('', True)]
        if test and kind == 'deep':
            variants = [('', True), ('_gl', False)]
        for suffix, green_down in variants:
            save_png(os.path.join(PRINTS, 'sz_print_%s%s_nohq.png' % (kind, suffix)), normal_map(h, green_down), 'RGB')
            paa(os.path.join(PRINTS, 'sz_print_%s%s_nohq.png' % (kind, suffix)))
            mat_name = 'sz_print_%s%s.rvmat' % (kind, suffix)
            with open(os.path.join(PRINTS, mat_name), 'w', newline='\r\n') as fh:
                fh.write(PRINT_RVMAT % {
                    'nohq': '%s\\data\\prints\\sz_print_%s%s_nohq.paa' % (PREFIX, kind, suffix),
                    'ao': '%s\\data\\prints\\sz_print_%s_as.paa' % (PREFIX, kind),
                    'smdi': '%s\\data\\prints\\sz_print_smdi.paa' % PREFIX})
        tex = '%s\\data\\prints\\sz_print_%s_ca.paa' % (PREFIX, kind)
        mat = '%s\\data\\prints\\sz_print_%s.rvmat' % (PREFIX, kind)
        pts_l, quads = print_mesh(kind, h, False)
        pts_r, _ = print_mesh(kind, h, True)
        write_print_model(os.path.join(PRINTS, 'sz_print_%s_l.p3d' % kind), pts_l, quads, tex, mat, False)
        write_print_model(os.path.join(PRINTS, 'sz_print_%s_r.p3d' % kind), pts_r, quads, tex, mat, True)
        if test and kind == 'deep':
            gl = '%s\\data\\prints\\sz_print_deep_gl.rvmat' % PREFIX
            write_print_model(os.path.join(PRINTS, 'sz_ptest_gl_l.p3d'), pts_l, quads, tex, gl, False)
            write_print_model(os.path.join(PRINTS, 'sz_ptest_gl_r.p3d'), pts_r, quads, tex, gl, True)
        print(kind, 'depth %.3f rim max %.4f ao min %.2f' % (PRINT_KINDS[kind]['depth'], h.max(), ao.min()))

# ---------------- tyre tracks ----------------
TRACKS = os.path.join(SRC, 'data', 'tracks')
# one track segment: across x, along y (the direction of travel is +y). Segments are laid end to end behind a wheel, so
# the relief repeats exactly over the segment length: the tread, the walls and the snow pushed up beside the tyre run
# on from one segment into the next
TRACK_W, TRACK_L = 0.48, 1.0
TRACK_TW, TRACK_TH = 128, 256
# each segment reaches this much further (half at each end) with the texture running on, so in bends the next segment
# covers the wedge that opens on the outside of the joint; both show the same texels where they overlap
TRACK_EXT = 0.06
# width of the tyre where it presses into the snow
TYRE_W = 0.21
# depth of the rut, height of the snow ridges beside it and relief of the tread
TRACK_KINDS = {
    'shallow': dict(depth=0.030, rim=0.008, lug=0.004, geo=False),
    'deep': dict(depth=0.070, rim=0.022, lug=0.007, geo=True),
}

def track_height(kind, seed):
    p = TRACK_KINDS[kind]
    xs = ((np.arange(TRACK_TW) + 0.5) / TRACK_TW - 0.5) * TRACK_W
    ys = (0.5 - (np.arange(TRACK_TH) + 0.5) / TRACK_TH) * TRACK_L      # row 0 = front end (+y)
    X, Y = np.meshgrid(xs, ys)
    ax = np.abs(X)
    half = TYRE_W / 2
    # tileable along the track (rows); columns fade out at the sides anyway
    noise = tileable_noise(TRACK_TH, 3.2, seed)[:, :TRACK_TW]
    noise = (noise - noise.mean()) / noise.std()
    inside = 1.0 - smoothstep(half - 0.03, half + 0.006, ax)
    floor = smoothstep(0.004, 0.016, half - 0.03 - ax)
    # tread: chevron blocks across the tyre, 28 to the metre, and the ridge of the centre groove
    pitch = TRACK_L / 28.0
    chevron = np.sin(2 * np.pi * (Y + 0.45 * ax) / pitch) > 0.2
    shoulder = ax < half - 0.02
    centre = np.exp(-(X / 0.006) ** 2)
    h = -p['depth'] * inside * (1.0 + 0.04 * noise)
    h += p['lug'] * floor * (chevron * shoulder + 0.7 * centre)
    # snow pushed up and outwards: an uneven ridge beside each wall
    ridge = np.exp(-((ax - (half + 0.032)) / 0.024) ** 2) * (ax > half - 0.006)
    h += p['rim'] * ridge * np.clip(0.75 + 0.35 * noise, 0.2, 1.5)
    h += 0.0008 * noise * np.exp(-((ax - (half + 0.012)) / 0.02) ** 2)
    fade = 1.0 - smoothstep(half + 0.06, half + 0.115, ax)
    return h * fade, fade

def track_normal_map(h):
    pu = TRACK_W / TRACK_TW
    pv = TRACK_L / TRACK_TH
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * pu)
    gr = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * pv)     # wraps: the segment repeats along its length
    gx[:, 0] = gx[:, -1] = 0
    n = np.dstack([-gx, -gr, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5

def track_occlusion(h, depth):
    k = 9
    pad = np.pad(h, ((k, k), (0, 0)), mode='wrap')
    pad = np.pad(pad, ((0, 0), (k, k)), mode='edge')
    acc = np.zeros_like(h)
    steps = range(-k, k + 1, 3)
    for dy in steps:
        for dx in steps:
            acc += pad[k + dy:k + dy + h.shape[0], k + dx:k + dx + h.shape[1]]
    local = acc / (len(steps) ** 2)
    below = np.clip(local - h, 0, None)
    return np.clip(1.0 - below / 0.02 * 0.3 - np.clip(-h, 0, None) / depth * 0.3, 0.45, 1.0)

def track_mesh(kind, h):
    """flat strip, or for deep tracks a grid whose vertices rise with the snow ridges; both ends sample the same row
    of the relief, so neighbouring segments meet without a step"""
    if not TRACK_KINDS[kind]['geo']:
        e = (TRACK_L + TRACK_EXT) / 2
        pts = [(-TRACK_W / 2, 0.0, -e), (TRACK_W / 2, 0.0, -e), (TRACK_W / 2, 0.0, e), (-TRACK_W / 2, 0.0, e)]
        return pts, [(0, 1, 2, 3)]
    nx, ny = 15, 12
    pts = []
    for j in range(ny):
        for i in range(nx):
            u = i / (nx - 1)
            # v runs over the segment plus the overlap at both ends
            v = (j / (ny - 1)) * (1 + TRACK_EXT / TRACK_L) - TRACK_EXT / TRACK_L / 2
            col = min(TRACK_TW - 1, int(u * (TRACK_TW - 1)))
            row = int(round((1 - v) * TRACK_TH)) % TRACK_TH
            y = max(0.0, float(h[row, col])) * 0.8
            pts.append(((u - 0.5) * TRACK_W, y, (v - 0.5) * TRACK_L))
    quads = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            quads.append((a, a + 1, a + nx + 1, a + nx))
    return pts, quads

def write_track_model(path, pts, quads, tex, mat):
    """the relief up close; from further away a flat strip (the normal map still draws the rut)"""
    def lod_of(points, quad_list, resolution):
        faces = []
        for (a, b, c, d) in quad_list:
            for t in ((a, b, c), (a, c, d)):
                faces.append({'verts': [(k, 0, points[k][0] / TRACK_W + 0.5, 0.5 - points[k][2] / TRACK_L) for k in t], 'texture': tex, 'material': mat})
        return mlod_lod(points, faces, resolution, props=(('lodnoshadow', '1'),))
    lods = [lod_of(pts, quads, 1.0)]
    if len(pts) > 4:
        e = (TRACK_L + TRACK_EXT) / 2
        flat = [(-TRACK_W / 2, 0.0, -e), (TRACK_W / 2, 0.0, -e), (TRACK_W / 2, 0.0, e), (-TRACK_W / 2, 0.0, e)]
        lods.append(lod_of(flat, [(0, 1, 2, 3)], 4.0))
    write_mlod(path, lods)

def make_tracks():
    os.makedirs(TRACKS, exist_ok=True)
    for fn in os.listdir(TRACKS):
        os.remove(os.path.join(TRACKS, fn))
    base = np.array([0.93, 0.945, 0.965])
    for n_kind, kind in enumerate(TRACK_KINDS):
        h, fade = track_height(kind, 90 + n_kind)
        ao = track_occlusion(h, TRACK_KINDS[kind]['depth'])
        depth01 = np.clip(-h / TRACK_KINDS[kind]['depth'], 0, 1)
        # packed snow in the rut is greyer and bluer, and the rut lies in its own shade (which the relief alone cannot
        # cast), so from a distance a track reads as two darker lines like in real snow
        col = base[None, None, :] * (1.0 - 0.14 * depth01[..., None]) + np.array([-0.035, -0.02, 0.0])[None, None, :] * depth01[..., None]
        # cut where the relief has flattened out, so the outer slope of the ridge does not end in a hard line
        alpha = (fade > 0.04).astype(float)
        stem = os.path.join(TRACKS, 'sz_track_%s' % kind)
        save_png(stem + '_ca.png', np.dstack([np.clip(col, 0, 1), alpha]), 'RGBA'); paa(stem + '_ca.png')
        save_png(stem + '_as.png', np.dstack([ao, ao, ao]), 'RGB'); paa(stem + '_as.png')
        save_png(stem + '_nohq.png', track_normal_map(h), 'RGB'); paa(stem + '_nohq.png')
        with open(stem + '.rvmat', 'w', newline='\r\n') as fh:
            fh.write(PRINT_RVMAT % {
                'nohq': '%s\\data\\tracks\\sz_track_%s_nohq.paa' % (PREFIX, kind),
                'ao': '%s\\data\\tracks\\sz_track_%s_as.paa' % (PREFIX, kind),
                'smdi': '%s\\data\\prints\\sz_print_smdi.paa' % PREFIX})
        pts, quads = track_mesh(kind, h)
        write_track_model(stem + '.p3d', pts, quads, '%s\\data\\tracks\\sz_track_%s_ca.paa' % (PREFIX, kind), '%s\\data\\tracks\\sz_track_%s.rvmat' % (PREFIX, kind))
        print('track', kind, 'depth %.3f rim max %.4f ao min %.2f verts %d' % (TRACK_KINDS[kind]['depth'], h.max(), ao.min(), len(pts)))

# ---------------- pond ice ----------------
ICE = os.path.join(SRC, 'data', 'ice')
ICE_SIZES = [2, 4, 8, 16]
# opaque glossy ice: milky pale ice once it is thick, dark clear ice while it is thin (freezing up, rotting in
# spring); procedural colour textures, the crack pattern of the frozen lakes of Sakhal (Frostline) as normal map
ICE_MAT = PREFIX + '\\data\\ice\\sz_ice.rvmat'
ICE_MAT_THIN = PREFIX + '\\data\\ice\\sz_ice_thin.rvmat'
ICE_TEX = PREFIX + '\\data\\ice\\sz_ice_co.paa'
ICE_TEX_THIN = PREFIX + '\\data\\ice\\sz_icet_co.paa'
# thick ice carries people: its plates have a roadway with the frozen lake surface of Sakhal (ice footsteps and
# hits); thin ice has none, so a player breaks through it into the water
ICE_ROAD_TEX = 'dz\\surfaces_sakhal\\data\\terrain\\sakhal_ice_lake_ca.paa'
LOD_ROADWAY = 3.0e15
LOD_GEOMETRY = 1.0e13
# the collision of thick ice: a slab under the surface (characters move on physics geometry, a roadway alone only
# gives the surface type)
ICE_SLAB = 0.25

def ice_geometry_lod(s):
    h = s * 0.5
    d = ICE_SLAB
    pts = [(-h, 0.0, -h), (h, 0.0, -h), (h, 0.0, h), (-h, 0.0, h),
           (-h, -d, -h), (h, -d, -h), (h, -d, h), (-h, -d, h)]
    # vertex order as the visible faces (front side out)
    quads = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (2, 6, 7, 3), (1, 5, 6, 2), (3, 7, 4, 0)]
    faces = [{'verts': [(i, 0, 0.0, 0.0) for i in q], 'texture': '', 'material': ''} for q in quads]
    sel = {'Component01': (set(range(len(pts))), set(range(len(faces))))}
    return mlod_lod(pts, faces, LOD_GEOMETRY, props=(('autocenter', '0'),), selections=sel, mass=[250.0] * len(pts))
# metres per texture repeat: every plate takes its place in this period, so the ice continues across plates
ICE_PERIOD = 16

def make_ice():
    """flat square ice plates (one quad, facing up) for the frozen ponds, 2 to 16 m, one model per place in the
    16 m texture period (sz_ice_<size>_<ix><iz>, ix = x0 / size mod period / size; sz_icet_* for thin ice)"""
    os.makedirs(ICE, exist_ok=True)
    for fn in os.listdir(ICE):
        if fn.endswith('.p3d'):
            os.remove(os.path.join(ICE, fn))
    make_ice_textures()
    count = 0
    for s in ICE_SIZES:
        h = s * 0.5
        pts = [(-h, 0.0, -h), (h, 0.0, -h), (h, 0.0, h), (-h, 0.0, h)]
        k = ICE_PERIOD // s
        for ix in range(k):
            for iz in range(k):
                uv = [((ix * s + p[0] + h) / ICE_PERIOD, -(iz * s + p[2] + h) / ICE_PERIOD) for p in pts]
                # two triangles, front faces up (same winding as the snow cover triangles)
                for prefix, mat, tex in (('sz_ice', ICE_MAT, ICE_TEX), ('sz_icet', ICE_MAT_THIN, ICE_TEX_THIN)):
                    faces = []
                    for tri in ((0, 1, 2), (0, 2, 3)):
                        faces.append({'verts': [(i, 0, uv[i][0], uv[i][1]) for i in tri], 'texture': tex, 'material': mat})
                    lod = mlod_lod(pts, faces, 1.0, props=(('lodnoshadow', '1'),))
                    lods = [lod]
                    if prefix == 'sz_ice':
                        lods.append(ice_geometry_lod(s))
                        road = []
                        for tri in ((0, 1, 2), (0, 2, 3)):
                            road.append({'verts': [(i, 0, uv[i][0], uv[i][1]) for i in tri], 'texture': ICE_ROAD_TEX, 'material': ''})
                        lods.append(mlod_lod(pts, road, LOD_ROADWAY))
                    write_mlod(os.path.join(ICE, '%s_%d_%d%d.p3d' % (prefix, s, ix, iz)), lods)
                    count += 1
    print('ice plates', ICE_SIZES, count, 'models')

WATER_DUMPS = {'chernarusplus': os.path.join(ROOT, 'tools', 'data', 'water_chernarusplus.txt')}

def make_ponds():
    """SZ_PondData.c: the water bodies (ponds and lakes, one water height each) of the supported maps, from a dump
    of the map's water objects (test harness command pondmap)"""
    import math
    out = ['//! Generated by tools/make_assets.py (make_ponds) from the pond objects of each map (test harness pondmap).',
           '//! One entry per water body: x0, z0, x1, z1 (the area its pond objects cover, on the 2 m grid) and the water height.',
           'class SZ_PondData', '{']
    worlds = []
    for world, path in WATER_DUMPS.items():
        objs = []
        for line in open(path, encoding='utf-8', errors='replace'):
            f = line.rstrip('\n').split('|')
            if len(f) < 8 or '\\ponds\\' not in f[0]:
                continue
            vec = lambda s: [float(x) for x in s.strip('<> ').split(',')]
            pos, ori, b0, b1 = vec(f[1]), vec(f[2]), vec(f[3]), vec(f[4])
            a = math.radians(ori[0])
            xs, zs = [], []
            for bx in (b0[0], b1[0]):
                for bz in (b0[2], b1[2]):
                    xs.append(pos[0] + bx * math.cos(a) + bz * math.sin(a))
                    zs.append(pos[2] - bx * math.sin(a) + bz * math.cos(a))
            objs.append([min(xs), min(zs), max(xs), max(zs), pos[1]])
        n = len(objs)
        par = list(range(n))
        def find(i):
            while par[i] != i:
                par[i] = par[par[i]]
                i = par[i]
            return i
        for i in range(n):
            for j in range(i + 1, n):
                p, q = objs[i], objs[j]
                if abs(p[4] - q[4]) > 0.05:
                    continue
                if p[0] <= q[2] + 1 and q[0] <= p[2] + 1 and p[1] <= q[3] + 1 and q[1] <= p[3] + 1:
                    par[find(i)] = find(j)
        groups = {}
        for i in range(n):
            groups.setdefault(find(i), []).append(i)
        bodies = []
        for idx in groups.values():
            x0 = math.floor((min(objs[i][0] for i in idx) - 2.0) / 2.0) * 2.0
            z0 = math.floor((min(objs[i][1] for i in idx) - 2.0) / 2.0) * 2.0
            x1 = math.ceil((max(objs[i][2] for i in idx) + 2.0) / 2.0) * 2.0
            z1 = math.ceil((max(objs[i][3] for i in idx) + 2.0) / 2.0) * 2.0
            ys = sorted(objs[i][4] for i in idx)
            bodies.append((x0, z0, x1, z1, ys[len(ys) // 2]))
        bodies.sort(key=lambda b: (b[1], b[0]))
        vals = []
        for b in bodies:
            vals.append('%d, %d, %d, %d, %.3f' % b)
        name = world.upper()
        out.append('\t//! %s: %d water bodies from %d pond objects' % (world, len(bodies), n))
        out.append('\tstatic const ref array<float> %s = {' % name)
        for i in range(0, len(vals), 4):
            sep = ',' if i + 4 < len(vals) else ''
            out.append('\t\t' + ', '.join(vals[i:i + 4]) + sep)
        out.append('\t};')
        out.append('')
        worlds.append((world, name))
        print(world, 'bodies', len(bodies), 'objects', n)
    out.append('\t//! water bodies of a world (lower case world name), or null when the map has no pond data')
    out.append('\tstatic array<float> ForWorld(string world)')
    out.append('\t{')
    for world, name in worlds:
        out.append('\t\tif (world == "%s")' % world)
        out.append('\t\t\treturn %s;' % name)
    out.append('\t\treturn null;')
    out.append('\t}')
    out.append('}')
    path = os.path.join(SRC, 'scripts', '4_World', 'SeasonZ', 'SZ_PondData.c')
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(out) + '\n')
    print('wrote', path)

ICE_RVMAT = '''ambient[]={1,1,1,1};
diffuse[]={1,1,1,1};
forcedDiffuse[]={0,0,0,0};
emmisive[]={0,0,0,1};
specular[]={%(spec)s,%(spec)s,%(spec)s,0};
specularPower=%(power)s;
PixelShaderID="Super";
VertexShaderID="Super";
class TexGen0
{
	uvSource="tex";
	class uvTransform
	{
		aside[]={1,0,0};
		up[]={0,1,0};
		dir[]={0,0,1};
		pos[]={0,0,0};
	};
};
class TexGen1
{
	uvSource="tex";
	class uvTransform
	{
		aside[]={2,0,0};
		up[]={0,2,0};
		dir[]={0,0,1};
		pos[]={0,0,0};
	};
};
class Stage0
{
	texture="%(co)s";
	texGen="0";
};
class Stage1
{
	texture="dz\\water_sakhal\\ice_lake\\data\\sakhal_ice_lake_nohq.paa";
	texGen="0";
};
class Stage2
{
	texture="#(argb,8,8,3)color(0.5,0.5,0.5,1,DT)";
	texGen="0";
};
class Stage3
{
	texture="#(argb,8,8,3)color(0,0,0,0,MC)";
	texGen="0";
};
class Stage4
{
	texture="#(argb,8,8,3)color(1,1,1,1,AS)";
	texGen="0";
};
class Stage5
{
	texture="#(argb,8,8,3)color(1,%(smdi_g)s,%(smdi_b)s,1,SMDI)";
	texGen="1";
};
class Stage6
{
	texture="#(ai,32,128,1)fresnel(%(fresnel)s)";
	texGen="0";
};
class Stage7
{
	texture="dz\\data\\data\\env_land_co.paa";
	texGen="0";
};
'''

def make_ice_textures():
    """colour textures of the ice over one 16 m period: milky pale ice with soft cloudy patches and faint white
    streaks of trapped air, and dark clear ice with sparse bubbles"""
    n = 512
    low = tileable_noise(n, 3.4, 41)
    mid = tileable_noise(n, 2.4, 42)
    fine = tileable_noise(n, 1.4, 43)
    streak = equalize(tileable_noise(n, 2.0, 44))
    cloud = 0.6 * low + 0.3 * mid + 0.1 * fine
    cloud = (cloud - cloud.mean()) / (cloud.std() + 1e-6)
    lines = np.clip(1.0 - np.abs(streak - 0.5) * 40.0, 0, 1) * (equalize(mid) > 0.55)
    bubbles = (equalize(fine) > 0.997).astype(np.float64)
    thick = np.zeros((n, n, 3))
    base = np.array([0.60, 0.65, 0.71])
    for c in range(3):
        thick[:, :, c] = base[c] + 0.045 * cloud + 0.12 * lines + 0.25 * bubbles
    thin = np.zeros((n, n, 3))
    tbase = np.array([0.085, 0.10, 0.12])
    for c in range(3):
        thin[:, :, c] = tbase[c] + 0.012 * cloud + 0.05 * lines + 0.35 * bubbles
    save_png(os.path.join(ICE, 'sz_ice_co.png'), np.clip(thick, 0, 1), 'RGB')
    save_png(os.path.join(ICE, 'sz_icet_co.png'), np.clip(thin, 0, 1), 'RGB')
    for name in ('sz_ice_co.png', 'sz_icet_co.png'):
        paa(os.path.join(ICE, name))
    mats = {'sz_ice.rvmat': dict(co=ICE_TEX, spec='0.5', power='80', smdi_g='0.45', smdi_b='0.55', fresnel='0.9,0.2'),
            'sz_ice_thin.rvmat': dict(co=ICE_TEX_THIN, spec='0.7', power='160', smdi_g='0.7', smdi_b='0.85', fresnel='1.2,0.25')}
    for name, v in mats.items():
        with open(os.path.join(ICE, name), 'w', newline='\n') as fh:
            fh.write(ICE_RVMAT % v)

if __name__ == '__main__':
    what = sys.argv[1:] or ['textures', 'rvmats', 'models', 'lighting']
    if 'textures' in what:
        make_textures(); convert_paa()
    if 'rooftex' in what:
        make_roof_textures()
    if 'rvmats' in what:
        make_rvmats()
    if 'models' in what:
        make_models()
    if 'roofmodels' in what or 'models' in what:
        make_roof_models()
    if 'lighting' in what:
        make_lighting()
    if 'prints' in what:
        make_prints(test='printtest' in what)
    if 'debug' in what:
        make_debug()
    if 'covermap' in what or 'textures' in what:
        make_cover_map()
    if 'ice' in what:
        make_ice()
    if 'tracks' in what:
        make_tracks()
    if 'ponds' in what:
        make_ponds()
    print('done', what)
