"""misc_deerstand2: a high seat, a cabin of boards on four long legs with cross braces, a board roof (49-55) and a
floor of six planks (34-39) that reaches past the roof at both ends.

(Opus, 6 Oct, c35) the roof's ragged board ends hung tongues at v7 and small brackets grew beads. (c39) with big_tops
the beams under the roof's side edges (53, 55) joined its lip into a hanging sheet and the brace ends grew lumps. The
roof boards (50-52, 54), the floor planks (34-39) and the top boards of the cabin walls (27, 30, 33, 40) hold snow, the
lip is short (30% of the depth + 1 cm, sinking 1.6 cm); the legs and their braces stay bare."""
import snow_hand as H


def build(m, v):
    m._sz_parts = (50, 51, 52, 54, 34, 35, 36, 37, 38, 39, 27, 30, 33, 40)
    m._sz_rails = ([], [])
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
