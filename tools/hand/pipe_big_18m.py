"""pipe_big_18m: an 18 m pipe bridge: big pipes in a lattice truss on two legs.

(Opus, 6 Oct, b1) the truss's thin rails and diagonals carried fat faceted sausages at v4-v7. Tops narrower
than 16 cm (rails, diagonals) get a ridge or nothing, the pipes and the walkway their caps, the lip short.
(c59, the pipe_big family) pipes lying side by side at different heights shared one field and their v7 pillows
merged into broad sheets: one field per height level (H.level_fields), and parts with less than 5 dm2 of top let
the snow through and hold none (H.see_through)."""
import snow_hand as H


def build(m, v):
    H.see_through(m)
    g = H.level_fields(m)
    return H.consts(m, v, fn=lambda m_, v_: H.separate(m_, v_, g), A7_OVL=0.15, A7_LIPDROP=0.03, A7_THIN=0.16)
