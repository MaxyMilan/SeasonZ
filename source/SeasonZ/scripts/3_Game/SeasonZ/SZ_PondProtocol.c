//! Shared 3_Game metadata: no world-layer types in RPC/persistence validation.
//! Bump LAYOUT when the order/extent of SZ_PondData changes. Layout 1 has 411 Chernarus bodies.
class SZ_PondProtocol
{
	static const int LAYOUT = 1;
	static const int CHERNARUS_COUNT = 411;

	static int CountForWorld(string world)
	{
		if (world == "chernarusplus")
			return CHERNARUS_COUNT;
		return 0;
	}

	static bool Valid(int layout, string world, array<int> carry)
	{
		if (layout != LAYOUT || world == "" || !carry || carry.Count() != CountForWorld(world))
			return false;
		for (int i = 0; i < carry.Count(); i++)
		{
			if (carry[i] != 0 && carry[i] != 1)
				return false;
		}
		return true;
	}
}
