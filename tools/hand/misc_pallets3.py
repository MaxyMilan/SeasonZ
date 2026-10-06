"""misc_pallets3: six euro pallets stacked, the top one (deck boards 154-160, its stringer boards 170-172 showing at the
ends) turned a little against the rest, so a strip of every lower deck shows beside it.

Only the top pallet holds snow: one addonfine cap (snow_addon via hybrid) over its deck, bridging the board gaps as the
snow deepens, its lip rolling over the deck's edges. The strips of the lower decks (2-7 cm wide, 19 cm and more below)
emit nothing: their own beads merged with the top cap's lip into curtains down the side (c20-c23), and a broken board
sticking out on the left grew a twisted ribbon. Under the top cap's lip they are sheltered from v3 on anyway."""
import snow_hand as H


def build(m, v):
    m._sz_rails = ([], [])
    m._sz_parts = (154, 155, 156, 157, 158, 159, 160, 170, 171, 172)
    return H.hybrid(m, v)

