"""misc_gcontainer_big: a large open skip full of rubbish; part 0 is the chassis with the lifting A-frames at both
ends, the rim (3-5, 11, 12) and the load (13-23) hold the snow.

(Opus, 6 Oct) m1: the A-frame carried a thick sausage and the load's pillow hung over the rim onto it. c35-c44: with
part 0 only blocked (no spill onto it) a ragged sheet still hung over one end above the A-frame, with a short lip, no
lip, a load cut 12 cm inside the end walls and flat-only end walls alike: blocking keeps a part's own snow. Part 0
holds none of its own now either (excluded and blocked), the lip is short (30% of the depth + 1 cm, sinking 1.6 cm)."""
import snow_hand as H


def build(m, v):
    m._sz_rails = ([], [])
    m._sz_exclude = (0,)
    m._sz_block = (0,)
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
