//! Shared logical pond state; physical plates remain local to each runtime.
class SZ_PondState
{
	protected static string s_World;
	protected static ref array<float> s_Data;
	protected static ref map<int, ref array<int>> s_Grid;

	static array<float> Data()
	{
		if (s_Grid && s_World == SZ_State.s_PondWorld)
			return s_Data;
		s_World = SZ_State.s_PondWorld;
		s_Data = SZ_PondData.ForWorld(s_World);
		s_Grid = new map<int, ref array<int>>;
		if (!s_Data)
			return null;
		for (int i = 0; i + 4 < s_Data.Count(); i += 5)
		{
			int x0 = Math.Floor(s_Data[i] / 128.0);
			int z0 = Math.Floor(s_Data[i + 1] / 128.0);
			int x1 = Math.Floor(s_Data[i + 2] / 128.0);
			int z1 = Math.Floor(s_Data[i + 3] / 128.0);
			for (int x = x0; x <= x1; x++)
			{
				for (int z = z0; z <= z1; z++)
				{
					int key = x * 65536 + z;
					array<int> ids = s_Grid.Get(key);
					if (!ids)
					{
						ids = new array<int>;
						s_Grid.Set(key, ids);
					}
					ids.Insert(i / 5);
				}
			}
		}
		return s_Data;
	}

	static bool Carries(int body)
	{
		if (!SZ_State.s_Valid || !SZ_State.s_HasPondCarry)
			return false;
		array<float> data = Data();
		if (!SZ_State.s_Valid || !data || !SZ_State.s_PondCarry || SZ_State.s_PondCarry.Count() * 5 != data.Count())
			return false;
		return body >= 0 && body < SZ_State.s_PondCarry.Count() && SZ_State.s_PondCarry[body] == 1;
	}

	static bool At(float x, float z, float water)
	{
		if (!SZ_State.s_Valid || !SZ_State.s_HasPondCarry)
			return false;
		array<float> data = Data();
		if (!data)
			return false;
		int gx = Math.Floor(x / 128.0);
		int gz = Math.Floor(z / 128.0);
		array<int> ids = s_Grid.Get(gx * 65536 + gz);
		if (!ids)
			return false;
		foreach (int id : ids)
		{
			int i = id * 5;
			if (x >= data[i] && z >= data[i + 1] && x <= data[i + 2] && z <= data[i + 3] && Math.AbsFloat(water - data[i + 4]) < 0.06)
				return Carries(id);
		}
		return false;
	}
}
