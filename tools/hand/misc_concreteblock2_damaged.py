"""misc_concreteblock2_damaged: as misc_concreteblock2 (a broken end): only the block holds snow, the three lifting
loops stand out of the pillow (r10: a lump at the broken end's loop)."""
import snow_hand as H


def build(m, v):
    return H.big_tops(m, v, 0.02)
