"""Wrecked military off-roader (Humvee type), with a tubular bull bar.
(Opus, 6 Oct, c60) hanging bull-bar spikes at v7; tried H.wreck with
A7_THIN=.12 so narrow tubes and mirror arms receive a ridge or nothing.
c63 left hanging white strips on the front bull bar.
ast3b attempt 1 excludes the guard frame (50) and its uprights (48, 49).
Blocking the same parts also suppresses thin ridges and neighbouring spill;
the rest continues through the existing H.wreck route with its 12 cm filter.
ast3b attempt 2 retains the successful exclusion, restoring the wreck's
1 dm2 part filter through part_fields (its residual group has many parts).
"""
import snow_hand as H


def build(m, v):
    m._sz_parts = tuple(parts[0] for parts, _ in H.part_fields(m, .01)
                        if len(parts) == 1 and parts[0] not in (48, 49, 50))
    m._sz_exclude = (48, 49, 50)
    m._sz_rails = ([], [])
    m._sz_block = (48, 49, 50)
    return H.wreck(m, v, A7_THIN=0.12)
