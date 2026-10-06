"""wall_cbrk_end: a broken wall; its crumbled crown holds snow like rubble and the ground: the props' depths (5-23 cm, kind 0)
instead of a fence's 1.5-6.5 cm, with which the cap broke into shards and flaps along the broken edge (r10), as ruin_wall."""
import snow_hand as H


def build(m, v):
    m.kind = 0
    return H.hybrid(m, v)
