//! Client: removes the grass wherever the snow cover is deep enough to bury it. The engine cuts grass under clutter
//! cutter models (the same ones gardens, tents and fireplaces use). A cut only lasts while its cutter exists: the grass
//! around a new cutter is rebuilt from the cutters present at that moment. So cutters stay on a fixed 6 m grid around
//! the camera for as long as the snow lies, and the grass comes back by itself after a thaw.
class DS_GrassCut
{
	static const float STEP = 6.0;
	static const float RADIUS = 120.0;
	static const float KEEP_RADIUS = 150.0;
	static const string MODEL = "DZ\\gear\\cultivation\\clutter_cutter_6m_x_6m.p3d";

	protected ref map<int, Object> m_Cutters;
	protected ref array<int> m_SpiralX;
	protected ref array<int> m_SpiralZ;
	protected int m_AnchorX;
	protected int m_AnchorZ;
	protected int m_Scan;
	protected bool m_Swept;
	// time since the cutters left behind were last removed
	protected float m_DropTimer;

	void DS_GrassCut()
	{
		m_Cutters = new map<int, Object>;
		m_SpiralX = new array<int>;
		m_SpiralZ = new array<int>;
		m_AnchorX = -100000;
		m_AnchorZ = -100000;
		int n = Math.Ceil(RADIUS / STEP);
		array<float> dists = new array<float>;
		for (int dx = -n; dx <= n; dx++)
		{
			for (int dz = -n; dz <= n; dz++)
			{
				float d = Math.Sqrt(dx * dx + dz * dz) * STEP;
				if (d > RADIUS)
					continue;
				int pos = dists.Count();
				while (pos > 0 && dists[pos - 1] > d)
					pos--;
				dists.InsertAt(d, pos);
				m_SpiralX.InsertAt(dx, pos);
				m_SpiralZ.InsertAt(dz, pos);
			}
		}
	}

	void ~DS_GrassCut()
	{
		Clear();
	}

	int GetCount()
	{
		return m_Cutters.Count();
	}

	//! snow depth that buries the grass of one grid cell: 4 to 6 cm, varied per cell so the grass line is ragged
	protected float Threshold(int gx, int gz)
	{
		float h = gx * 0.7310 + gz * 0.3137;
		h = h - Math.Floor(h);
		return 4.0 + 2.0 * h;
	}

	void Update(float timeslice, vector camera, float s0, float s1, float s2)
	{
		int ax = Math.Floor(camera[0] / STEP);
		int az = Math.Floor(camera[2] / STEP);
		if (ax != m_AnchorX || az != m_AnchorZ)
		{
			m_AnchorX = ax;
			m_AnchorZ = az;
			m_Scan = 0;
			m_Swept = false;
		}
		// while travelling the grid restarts at every step and a full pass never completes: the cutters left
		// behind are removed every second as well
		m_DropTimer += timeslice;
		if (m_DropTimer >= 1.0)
		{
			m_DropTimer = 0;
			DropFar(camera);
		}

		int count = m_SpiralX.Count();
		float budget = 0;
		int visited = 0;
		while (budget < 40.0 && visited < count)
		{
			if (m_Scan >= count)
			{
				m_Scan = 0;
				if (!m_Swept)
					DropFar(camera);
			}
			int gx = ax + m_SpiralX[m_Scan];
			int gz = az + m_SpiralZ[m_Scan];
			m_Scan++;
			visited++;
			int key = gx * 65536 + gz;
			float x = (gx + 0.5) * STEP;
			float z = (gz + 0.5) * STEP;
			float ground = g_Game.SurfaceY(x, z);
			float depth = DS_State.SnowAt(ground, s0, s1, s2);
			float limit = Threshold(gx, gz);
			Object have = m_Cutters.Get(key);
			if (!have && depth >= limit)
			{
				budget += 2.0;
				// the engine ignores clutter cutters inside the square a pond object covers (its banks keep their
				// grass), so cells there and on the sea get none
				if (g_Game.SurfaceIsSea(x, z) || g_Game.SurfaceIsPond(x, z))
					continue;
				Object o = g_Game.CreateStaticObjectUsingP3D(MODEL, Vector(x, ground, z), "0 0 0", 1.0, true);
				if (o)
					m_Cutters.Set(key, o);
			}
			else if (have && depth < limit - 1.0)
			{
				g_Game.ObjectDelete(have);
				m_Cutters.Remove(key);
				budget += 1.0;
			}
			else
			{
				budget += 0.1;
			}
		}
	}

	//! forgets the cutters the camera left behind (once per new anchor, after a full pass)
	protected void DropFar(vector camera)
	{
		m_Swept = true;
		array<int> drop = new array<int>;
		for (int i = 0; i < m_Cutters.Count(); i++)
		{
			int key = m_Cutters.GetKey(i);
			int gx = Math.Floor(key / 65536.0);
			int gz = key - gx * 65536;
			float dx = (gx + 0.5) * STEP - camera[0];
			float dz = (gz + 0.5) * STEP - camera[2];
			if (dx * dx + dz * dz > KEEP_RADIUS * KEEP_RADIUS)
				drop.Insert(key);
		}
		foreach (int k : drop)
		{
			Object o = m_Cutters.Get(k);
			if (o)
				g_Game.ObjectDelete(o);
			m_Cutters.Remove(k);
		}
	}

	void Clear()
	{
		if (!m_Cutters)
			return;
		for (int i = 0; i < m_Cutters.Count(); i++)
		{
			Object o = m_Cutters.GetElement(i);
			if (o)
				g_Game.ObjectDelete(o);
		}
		m_Cutters.Clear();
	}
}
