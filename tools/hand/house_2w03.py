"""house_2w03: a two-storey house with a steep hipped roof (the roof planes and the ridge are separate panels over the body).

(Opus, 6 Oct, b1) every depth covered other roof planes and v7 left the roof nearly bare with loose shards. (c64) not
a glass flag; slope limit 70/55 with v1-v2 = v3 still gave broken flat facets and star-shaped spikes on the hips: the
volumetric cap does not hold on this roof. The blanket recipe instead (H.auto: each top region its own blanket)."""
import snow_hand as H


def build(m, v):
    return H.auto(m, v)

