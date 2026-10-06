"""misc_through_static: a cattle trough, an open half-round tub on a tube stand.

(Opus, 6 Oct, o1) the volumetric cap left it bare, the open tub too; the blanket (H.auto) only the rim. The tub's floor
lies 7 cm over the legs' feet, under the 25 cm over the ground where the ground snow takes over: but the ground snow
does not reach into a tub on legs. The ground lowered for it, only the tub (part 1), as mine_rail_tram: a low sky
share for the deep floor, a short lip, a small surface kernel against rim lumps."""
import snow_hand as H


def build(m, v):
    m.ground = float(m.V[:, 1].min()) - 0.25
    m._sz_parts = (1,)
    m._sz_rails = ([], [])
    return H.consts(m, v, A7_SKYMIN=.12, A7_THIN=0., A7_OVL=.05,
                    A7_LIPDROP=.01, A7_FLOORBLUR=0., A7_BASEMAX=.035)
