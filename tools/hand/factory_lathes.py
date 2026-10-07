"""factory_lathes: a large industrial factory with pitched roof halls and broad chimney stacks.

(Astra Laplace, 7 Oct 2026, b1) the coarse volume produced huge triangular roof fans, bare
fields and a long facade sheet at every depth. Surface blankets follow each upward roof
region with short supported lips; a v3 minimum stabilizes the thin layer on the steep roofs.
"""
import snow_hand as H


def build(m, v):
    return H.auto(m, max(v, 3), over=0.012, smooth=0.04, bury=False)
