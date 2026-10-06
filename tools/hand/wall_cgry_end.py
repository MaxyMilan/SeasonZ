"""wall_cgry_end: the broken end of a grey concrete wall, its crown falling away in a steep break.

(Opus, 6 Oct, r10, c37) with the fences' shallow depths the cap curled over the break and ran down it as a
ribbon. As the other broken wall ends (wall_cbrk_end): the props' depths (kind 0), with a short lip.
(c43) with the props' depths the snow ran down the 45-degree break as a thick white sausage: back to the walls'
shallow depths (kind 1) with the short lip."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
