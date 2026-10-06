"""wall_stone2d: a low dry-stone field wall, its stones loosely heaped (the damaged variant of the stone walls).

(Opus, 6 Oct, c37, c62, c68) on the thin fence depths (1.5-6.5 cm) the cap broke into flat shards on the stones'
facets, with or without the rough treatment and ledges. Like wall_stoned and wall_stone (approved): a dry-stone wall
holds snow like the rocks and the ground around it, the depths of the props (5-23 cm, kind 0)."""
import snow_hand as H


def build(m, v):
    m.kind = 0
    return H.hybrid(m, v)
