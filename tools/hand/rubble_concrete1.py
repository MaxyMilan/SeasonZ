"""rubble_concrete1: a heap of broken concrete slabs and debris.

(Opus, 6 Oct, c37) triangular holes along the front edge at v1-v2, a faceted cap and small icicle drips at the rim at v7. Broken masonry and rubble hold snow like rock (the rough treatment: the layer thins out
before the slope limit instead of ending in beads, cracks bridged), the low parts included, a short lip."""
import snow_hand as H


def build(m, v):
    m.rough = True
    if not getattr(m, '_sz_low', False):
        m.ground -= 0.22
        m._sz_low = True
    return H.consts(m, v, A7_CREVICE=0.15, A7_OVL=0.3, A7_LIPDROP=0.05)

