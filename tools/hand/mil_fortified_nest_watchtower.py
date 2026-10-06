"""Fortified watchtower: c37 had large shards, folds and holes at outer edges.
ast3 attempt 1 retained folds. Attempt 2 separates the upper net, lower net
and remaining structure into shared fields, limits steep sides, and rejects
lower ledges. The fields keep their own detail budgets and cannot merge.
(Astra, ast3b extra attempt 1) c67 has teeth under the roof: cap-carrier
diagnostics point chiefly to upper net 118. Tighten crown and smooth-slope
limits to reject its lower folded facets; keep roof, lower net and structure
in separate fields, block foreign parts, and shorten the unsmoothed lip.
ast3b extra attempt 2: the deep cap still had a toothed edge. Keep the
surface kernel at 5 cm with shared volume growth, and give the lip room
to round over with a lightly smoothed floor and the same tight drop limit.
"""
import snow_hand as H


def build(m, v):
    H.ledges(m, drop=.08, reach=.8, amin=.5, wmin=.12, jump=.04, ny=.5)
    H.crown(m, drop=.12, reach=.5)
    n = int(m.part_t.max()) + 1
    groups = [((118,), tuple(p for p in range(n) if p != 118)),
              ((119,), tuple(p for p in range(n) if p != 119)),
              (tuple(range(118)), tuple(range(118, n)))]
    return H.consts(m, v, fn=lambda m_, v_: H.separate(m_, v_, groups),
                    A7_OVL=.3, A7_LIPDROP=.01, A7_FLOORBLUR=.15, A7_BASEMAX=.05,
                    A7_BANDH=0., A7_THIN=.12, A5_STEEP_SMOOTH=30.,
                    A5_FULL_SMOOTH=20., A7_UNFOLD=45., A7_BEAUTY=True)
