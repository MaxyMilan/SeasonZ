"""Camouflage shelter: c37 left every depth empty despite a broad net surface.
Part 31 is the continuous net; its mostly downward winding makes signed top
area unreliable. Select it explicitly, keep steep skirts bare and shorten lips.
ast3 attempt 3 uses ledges: attempt 1 left skirt patches, while attempt 2's
crown filter cut a broad fold. Minor lower ledges go; the main net stays.
"""
import snow_hand as H


def build(m, v):
    m._sz_parts = (31,)
    m._sz_rails = ([], [])
    H.ledges(m, drop=.12, reach=1., amin=1., wmin=.16, jump=.08, ny=.55)
    return H.consts(m, v, A5_STEEP=55., A7_FADE=8.,
                    A7_OVL=.1, A7_LIPDROP=.02, A7_BANDH=0.)
