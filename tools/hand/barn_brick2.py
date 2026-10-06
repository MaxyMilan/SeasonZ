"""barn_brick2: a brick barn with a tiled roof pitched about 50 degrees and stepped gable parapets rising above it.

(Opus, 6 Oct, b1) at the roof's corners the gable parapet's cap and the roof's lip met in pointed flaps hanging
down the gable. (c43) thin strips as ridges broke the v1 cap of the tiled roof into a bare roof with a twisted
sheet. (c50) v1/v2 left bare stripes and triangle fins on the tiles (the tiles' risers lie beyond the 60-degree
slope limit on a 50-degree roof), the eave corners still had pointed flaps, the parapet rolls stood fat.
(ast2, Astra) part table: roof and body 45, parapets 43/44 (pitched like the roof), gutters 39/40; a hand-built
strip model did not get through its own guards.
(Opus, c57) one field per part: the roof's field may not spill onto the parapets or gutters, so no flaps where they
meet; the parapets and gutters carry their own short caps. Slope limit 70 degrees (full depth to 55) so the tile
risers carry the layer and v1 is a closed thin sheet. Short lip, no thin-strip handling.
(c57) v3-v7 clean (roof, parapets, gutters, corners); v1/v2 broke on the 50-degree tiles (stripes and a smeared
sheet: the 5-7 cm layer does not close there). The roof shows its v3 cap at v1 and v2 (as white as the other
roofs at a light snow); parapets and gutters grow from v1."""
import snow_hand as H
import snow_addon as A

GROUPS = [((45,), (43, 44, 39, 40)), ((43,), (45,)), ((44,), (45,)), ((39,), (45,)), ((40,), (45,))]
C = dict(A7_OVL=0.3, A7_LIPDROP=0.05, A7_THIN=0.0, A5_STEEP_SMOOTH=70.0, A5_FULL_SMOOTH=55.0)


def _caps(m_, v_):
    H.separate(m_, v_, GROUPS)
    out = []
    for i, c in enumerate(m_._sz_sep):
        m_._snow_a7_cache = c
        out.append(A.build(m_, max(v_, 3) if i == 0 else v_))
    return H.join(out)


def build(m, v):
    return H.consts(m, v, fn=_caps, **C)
