"""misc_stadiumbenches: a stand of five stepped rows: seat boards 54, 57, 60, 63, 66 alternate with pairs of foot boards
(55-56, 58-59, 61-62, 64-65) 25 cm lower; 67 is the back board on top. The steel frame holds no snow.

(Opus, 6 Oct) one field over all boards merged the rows into one marshmallow at v7 (r10). Each board group is its own
cap (H.separate) and blocks its neighbours, so a seat's pillow stops at its own edge above the foot boards."""
import snow_hand as H

ROWS = [(54,), (55, 56), (57,), (58, 59), (60,), (61, 62), (63,), (64, 65), (66,), (67,)]


def build(m, v):
    groups = []
    for i, g in enumerate(ROWS):
        block = tuple(p for j in (i - 1, i + 1) if 0 <= j < len(ROWS) for p in ROWS[j])
        groups.append((g, block))
    return H.separate(m, v, groups)
