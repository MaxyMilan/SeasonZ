"""rock_wallh3: a horizontal rock wall.

(Opus, 6 Oct) b1: a crack showed as a dark slit through the cap; c46: out of memory in parallel.
(Opus, 6 Oct, c66) built alone under a memory guard on a coarse lattice (5 cm, 2.5 cm vertically): the 3 cm
lattice ran out of memory (tens of millions of faces in the weld); a rock cap's lumps are coarser than that anyway.
A short lip (30% of the depth + 1 cm, sinking 1.6 cm at most), no cornices with pointed drips. Cracks in the crown up to 15 cm wide are bridged
(A7_CREVICE): c66 left a dark slit through rock_wallh3's cap."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05, A7_CREVICE=0.15, A7_GRIDMAX=0.05, A7_GYMIN=0.025)

