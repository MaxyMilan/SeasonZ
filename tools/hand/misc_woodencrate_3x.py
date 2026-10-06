"""misc_woodencrate_3x: three wooden crates, one standing open in front (Expansion mapping).

(Opus, 6 Oct, e1; Astra) the closed crates' lids clean, but the open crate stayed bare inside: its floor lies within
25 cm of the ground (left to the ground snow), yet the ground snow does not reach into a crate. The ground lowered
(as misc_through_static), so the open crate fills with snow."""
import snow_hand as H


def build(m, v):
    m.ground = float(m.V[:, 1].min()) - 0.25
    return H.big_tops(m, v, 0.01)
