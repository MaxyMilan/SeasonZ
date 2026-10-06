"""rubble_dirtpile_large: a heap of earth. (Opus, 6 Oct) as a smooth model its flanks (steeper than 60 degrees in places, rough
facets) stayed bare and only the crown was white (m1, r10). Earth holds snow like rock: the rough treatment (up to 72
degrees, crevices bridged up to 15 cm, a soft fade at the slope limit)."""
import snow_hand as H


def build(m, v):
    m.rough = True
    if not getattr(m, '_sz_low', False):
        # the heap's foot (within 25 cm of the ground, which tops() leaves to the terrain's cover) holds snow too: the
        # earth shows nowhere as a bare brown ring between the cap and the white ground
        m.ground -= 0.22
        m._sz_low = True
    return H.consts(m, v, A7_CREVICE=0.15)
