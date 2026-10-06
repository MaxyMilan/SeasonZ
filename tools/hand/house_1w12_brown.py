"""house_1w12_brown: a one-storey log house with a steep hipped roof and a chimney.

(Opus, 6 Oct, b1) v3-v7 clean; at v1 and v2 the thin layer tore along the hips into crumpled sheets and flaps (the
5-7 cm layer does not close on so steep a roof). v1 and v2 show the v3 cap, as white as the other roofs at a light
snow."""
import snow_hand as H


def build(m, v):
    return H.big_tops(m, max(v, 3), 0.01)

