"""misc_hedgehog_concrete: an anti-tank hedgehog of three crossed concrete beams (1, 2, 3) on a centre block (0),
1.4 m high; the beams' upper faces are pitched 45-55 degrees.

(Opus, 6 Oct, c37) with the building default (only parts with at least 1 dm2 of top flatter than 45 degrees) the
hedgehog got no snow at all; with one field for all (r10) the snow of the beams ran together at the crossing and down
the flanks. Each beam and the block is its own field (no bridging between the beams), with a short lip (30% of the
depth + 1 cm, sinking 1.6 cm at most).
(c43) separate fields grew fat round sausages along every beam from v4: beams pitched 45-55 degrees shed snow, so
the second depth is the deepest."""
import snow_hand as H


def build(m, v):
    groups = [((p,), ()) for p in range(int(m.part_t.max()) + 1)]
    return H.consts(m, v, fn=lambda m_, v_: H.separate(m_, min(v_, 2), groups), A7_OVL=0.3, A7_LIPDROP=0.05)
