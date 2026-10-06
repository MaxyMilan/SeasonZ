"""misc_pallets2: a euro pallet lying flat (top deck 11-16, blocks 19-21, bottom deck 0-5 on stringers 8-10) with a second one
leaning on it at about 27 degrees (deck 22-27; stringers 28, 29 and boards 30-32 behind it). The same pair as misc_pallets1, 8 cm lower and leaning 3 degrees steeper.

Each deck its own addonfine cap (H.separate): the leaning deck's pillow rolls over its edges, the strip of the lying deck in
front of its high edge gets its own pillow, and the two never flow into one (c20-c22: the leaning cap poured down 35-40 cm
over its high edge onto the lying deck, and the slot under the leaning pallet looked glued shut). The lower parts stay bare;
boards seen only through the slots get nothing (sky test)."""
import snow_hand as H

GROUPS = [((22, 23, 24, 25, 26, 27), ()), ((11, 12, 13, 14, 15, 16), ())]


def build(m, v):
    return H.separate(m, v, GROUPS)

