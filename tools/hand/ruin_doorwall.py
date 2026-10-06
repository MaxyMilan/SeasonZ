"""ruin_doorwall: a ruined wall with a door opening, its top broken into steps.

(Opus, 6 Oct, c37) the broken steps carried lumps with sharp fins and flanges (v1 splintered edges, v7 a fin beside the door). Broken masonry and rubble hold snow like rock (the rough treatment: the layer thins out
before the slope limit instead of ending in beads, cracks bridged), the low parts included, a short lip.
(c62) sharp sheets still stood on the steep broken faces of the steps: the rough slope limit (72 degrees) let the
steep break faces carry snow. Snow up to 55 degrees here (full depth to 35).
(c65) small triangular shards stayed on the broken faces below the crown: small or narrow tops below a bigger
one stay bare (H.ledges), so only the wall's crown and its steps hold snow."""
import snow_hand as H


def build(m, v):
    m.rough = True
    H.ledges(m, 0.08, 0.4)
    if not getattr(m, '_sz_low', False):
        m.ground -= 0.22
        m._sz_low = True
    return H.consts(m, v, A7_CREVICE=0.15, A7_OVL=0.3, A7_LIPDROP=0.05, A5_STEEP=55.0, A5_FULL=35.0)

