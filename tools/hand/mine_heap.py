"""mine_heap: a large irregular spoil heap of loose earth and rock beside a mine.

(Astra Faraday, 7 Oct 2026, b1) the volumetric cap split into radial sheets with long open cuts and shards.
Continuous surface blankets follow the measured exposed heap instead. The accumulation threshold reaches the
supplied terrain height, leaving no bare foot ring; short lips and gentle local smoothing retain the actual
rough heap silhouette without bridging unrelated levels or burying down steep faces.
"""
import snow_hand as H


def build(m, v):
    if not getattr(m, '_sz_faraday_heap', False):
        m.ground -= 0.25
        m._sz_faraday_heap = True
    return H.auto(m, v, over=0.015, smooth=0.06, fill=0.01, bury=False)
