"""house_2w03: a two-storey house with a steep hipped roof (the roof planes and the ridge are separate panels over the body).

(Opus, 6 Oct, b1) every depth covered other roof planes and v7 left the roof nearly bare with loose shards. (c64)
not a glass flag (treating the panels as solid changed nothing): the roof is pitched close to the 60-degree slope
limit and its layer closed or tore apart from depth to depth, as on barn_brick2. Slope limit 70 degrees (full depth
to 55); v1 and v2 show the v3 cap (the thin layer does not close on so steep a roof)."""
import snow_hand as H


def _cap(m_, v_):
    return H.big_tops(m_, max(v_, 3), 0.01)


def build(m, v):
    return H.consts(m, v, fn=_cap, A5_STEEP_SMOOTH=70.0, A5_FULL_SMOOTH=55.0)

