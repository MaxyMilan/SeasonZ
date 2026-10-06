"""houseblock_2f7: a two-storey block of flats with a steep gabled roof over a lower front roof and dormer strips.

(Opus, 6 Oct, b1) v4-v7 clean; at v1-v3 the volumetric cap tore along the gable and over the lower front roof into
crumpled sheets and flaps (v3 still broken at the left gable). The blanket recipe instead (H.auto: each top region its
own blanket), as house_2w03."""
import snow_hand as H


def build(m, v):
    return H.auto(m, v)
