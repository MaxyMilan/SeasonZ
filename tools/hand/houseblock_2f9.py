"""houseblock_2f9: a three-storey block of flats with a steep gabled roof and two chimneys.

(Opus, 6 Oct, b1) v3-v7 clean; at v1 and v2 the thin layer tore over the whole roof into crumpled shards (the 5-7 cm
layer does not close on so steep a roof). v1 and v2 show the v3 cap."""
import snow_hand as H


def build(m, v):
    return H.big_tops(m, max(v, 3), 0.01)
