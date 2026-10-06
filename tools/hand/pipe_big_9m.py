"""pipe_big_9m: a 9 m pipe bridge: several big pipes on a lattice truss.

(Opus, 6 Oct, c37) pipes lying side by side at different heights shared one field: at v7 their pillows merged into
one broad sheet bridging the height steps (marshmallow), and the truss's thin members grew rolls. Every part with
5 dm2 of top or more is its own field that spills onto no other part (H.part_fields), tops narrower than 16 cm get
a ridge or nothing, the lip is short (15% of the depth + 1 cm, sinking 1 cm).
(c59) a field per part gave every pipe segment rounded ends and seams at each joint: one field per height level
(H.level_fields: parts whose highest tops lie within 12 cm of each other share a field).
(c59b) the pillows still broke at every brace of the truss top: the brace was the highest surface there. Parts
with less than 5 dm2 of top let the snow through (H.see_through) and hold none."""
import snow_hand as H


def build(m, v):
    H.see_through(m)
    g = H.level_fields(m)
    return H.consts(m, v, fn=lambda m_, v_: H.separate(m_, v_, g), A7_OVL=0.15, A7_LIPDROP=0.03, A7_THIN=0.16)

