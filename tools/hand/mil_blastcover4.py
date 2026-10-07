"""mil_blastcover4: a long earth berm with a timber-lined interior and short end returns.

(Astra Kepler, 7 Oct 2026, b1) shallow snow left a broad bare band and large radial triangular gaps. The measured
source has the same bank-and-timber construction as repaired blastcover1 and blastcover3. Continuous surface
blankets follow its exposed slopes and timber tops, with short lips and the supplied terrain height retained.
"""
import snow_hand as H


def build(m, v):
    return H.auto(m, v, over=0.015, smooth=0.06, bury=False)
