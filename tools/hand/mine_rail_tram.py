"""mine_rail_tram: an open mine cart (a deep tub on a wheeled frame).

(Opus, 6 Oct, c37) the tub stayed bare and the couplings grew shards. (ast3, Astra) part 46 holds the tub's floor
and rim; the rest (frame, wheels, couplings) holds none. The tub floor still stayed bare: it sees the sky straight
up but little of the slanted rays, under the 45% the caps ask for (A7_SKYMIN .12 here). A short lip.
(Astra, ast3b extra attempt 1) debug corrects that diagnosis: the central floor
is part 46, 36 cm above cutoff, clear straight up and 56-100% sky-open.
c67 already has floor snow at all seven depths, hidden in the low views.
Keep the tub selection; a 6 cm surface kernel with shared volume growth
and a short unsmoothed lip limits deep rim bulbs while the floor deepens."""
import snow_hand as H


def build(m, v):
    m._sz_parts = (46,)
    m._sz_rails = ([], [])
    return H.consts(m, v, A7_SKYMIN=.12, A7_THIN=0., A7_OVL=.05,
                    A7_LIPDROP=.01, A7_FLOORBLUR=0., A7_BASEMAX=.06)
