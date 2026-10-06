"""train_wagon_flat: a flat railway wagon: a long deck on bogies, buffers and couplings at both ends.

(Opus, 6 Oct, b1) at v7 the deck's pillow joined the lower buffers and coupling and hung thick tongues over the end
walls. Parts with at least 1 dm2 of top (deck, end walls), tops narrower than 10 cm a ridge or nothing, a short lip
(30% of the depth + 1 cm, sinking 1.6 cm at most)."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.3, A7_LIPDROP=0.05, A7_THIN=0.10)
