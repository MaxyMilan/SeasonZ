"""garbage_bin: a round bin (0) with a lid (3), two side grips (1, 2) and a thin handle tab (4) sticking 7 cm out of the
lid's rim. On its own the tab grew an ear of snow at v1-v2 and a curled flap at v7; the body's rim, 3 cm under the lid,
poked white specks out from under the lid's lip. Only the lid emits snow (addonfine via hybrid); its pillow rolls over
the tab and the rim like over the rest of its edge."""
import snow_hand as H


def build(m, v):
    m._sz_parts = (3,)
    return H.hybrid(m, v)
