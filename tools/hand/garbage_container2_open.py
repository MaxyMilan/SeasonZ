"""garbage_container2_open: an open steel waste container, rubbish inside, the lid flipped back (Expansion mapping).

(Opus, 6 Oct, e1; Astra Boyle/McClintock) the corner posts of the rim grew balls at v1-v4 and the rim strips stayed
bare between them; the wreck route kept them (they are part of the body, part 1). Part table: 1 body and rim,
2 the rubbish inside (1.55 m2 of top), 24 the lid. (e1c) the hanging lid's snow stood as a vertical strip in the
hinge recess: only the rubbish holds snow (mine_rail_tram's way), the pillow fills the tub and rolls over the thin
rim; the 3 cm steel rim itself stays bare."""
import snow_hand as H


def build(m, v):
    m._sz_parts = (2,)
    m._sz_rails = ([], [])
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
