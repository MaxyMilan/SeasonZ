"""table_crushed: a crushed table lying in pieces, its boards 10-50 cm over the ground (Expansion mapping).

(Opus, 6 Oct, e1; Astra Boyle) most boards stayed bare (under the 25 cm the ground snow takes over), only a raised
fragment carried two lobes. The ground lowered, as the other low Expansion props."""
import snow_hand as H


def build(m, v):
    m.ground = float(m.V[:, 1].min()) - 0.25
    return H.big_tops(m, v, 0.01)
