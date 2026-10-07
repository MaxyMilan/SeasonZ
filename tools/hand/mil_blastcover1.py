"""mil_blastcover1: a wide earth berm around a timber-lined open emplacement.

(Astra Kepler, 7 Oct 2026, b1) shallow snow left broad bare fans and the deep mesh retained radial tears and
folded shards. As on the inspected mil_blastcover3, continuous surface blankets follow the exposed bank and
timber tops with short supported lips. The open centre and steep interior faces stay clear.
"""
import snow_hand as H


def build(m, v):
    return H.auto(m, v, over=0.015, smooth=0.06, bury=False)
