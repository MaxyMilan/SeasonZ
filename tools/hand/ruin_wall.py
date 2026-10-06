"""ruin_wall: a low ruined wall of rubble, its broken crown rising and falling along it.

Rubble holds snow like the rocks and the ground: the props' depths (5-23 cm, kind 0) instead of a fence's 1.5-6.5 cm,
with which the v1-v2 cap broke into shards along the broken stones' facets (m1)."""
import snow_hand as H


def build(m, v):
    m.kind = 0
    return H.hybrid(m, v)
