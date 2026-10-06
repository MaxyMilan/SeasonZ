"""Water trough trailer: long half-round trough, two-wheel chassis and drawbar.
(Opus, 6 Oct, c37) belly patches and a drawbar blob at v5-v7; tried tops
over 1 dm2, slopes up to 45 degrees (full at 30), and a short lip.
c62 retained the drawbar blob and outer belly patch.
ast3b attempt 1 selects the trough/rim (0) and the two wheel shells (4, 18).
Drawbar parts 2/15/29 receive no snow. Narrow rims join the shared field;
a very short lip and unsmoothed carrier floor limit spill onto the belly.
ast3b attempt 2 separates trough and wheels: attempt 1 joined wheel snow
to the rim at v6-v7. Each field blocks every other source part.
"""
import snow_hand as H


def build(m, v):
    groups = [((p,), tuple(q for q in range(int(m.part_t.max()) + 1) if q != p))
              for p in (0, 4, 18)]
    return H.consts(m, v, fn=lambda m_, v_: H.separate(m_, v_, groups),
                    A7_THIN=0., A7_OVL=.05, A7_LIPDROP=.01,
                    A7_FLOORBLUR=0., A5_STEEP_SMOOTH=45., A5_FULL_SMOOTH=30.)

