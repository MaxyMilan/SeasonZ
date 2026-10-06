"""roadblock_bags_endr: the right end of a sandbag wall; the top bag (0) over a stair of bags stepping down towards the
end (21, 18, 15, 13, 1).

(Opus, 6 Oct, r10, c37, c43) the pillows of the top and the stepped bags merged into one bulbous mass down the end at
v5-v7, a short lip alone did not part them. Every bag is its own field (its own pillow, no bridging between bags),
with a short lip (30% of the depth + 1 cm, sinking 1.6 cm at most)."""
import snow_hand as H


def build(m, v):
    groups = [((p,), ()) for p in range(int(m.part_t.max()) + 1)]
    return H.consts(m, v, fn=lambda m_, v_: H.separate(m_, v_, groups), A7_OVL=0.3, A7_LIPDROP=0.05)
