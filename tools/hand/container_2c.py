"""container_2c: a shipping container (or a stack of them). The cap covers the roof, the top frame rails and the corner
castings (parts with 150 cm2 of top or more); the doors' top edges, locking rods, handles and hinges emit nothing, so the
roof's lip rolls cleanly over the door end (m1: bulbs on the handles, a lumpy curtain over the doors)."""
import snow_hand as H


def build(m, v):
    return H.big_tops(m, v, 0.015)
