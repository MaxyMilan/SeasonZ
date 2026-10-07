//! Client: removes the grass wherever the snow cover is deep enough to bury it. The engine cuts grass under clutter
//! cutter models (the same ones gardens, tents and fireplaces use). A cut only lasts while its cutter exists: the grass
//! around a new cutter is rebuilt from the cutters present at that moment. So cutters stay on a fixed 6 m grid around
//! the camera for as long as the snow lies, and the grass comes back by itself after a thaw.
class SZ_GrassCut
{
	static const float STEP = 6.0;
	static const float RADIUS = 120.0;
	static const float KEEP_RADIUS = 150.0;
	//! pause after a full pass while the camera stays in the same grid cell: the snow depth changes far slower
	static const float REST = 1.0;
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
	// grid cell of the camera when the cutters left behind were last removed: cutters are only placed within
	// RADIUS of the camera's cell and kept to KEEP_RADIUS, so none can be out of reach before the camera moves on
	protected int m_DropX;
	protected int m_DropZ;
	// time left before the next pass at an unchanged grid cell
	protected float m_Rest;
	protected bool m_DropActive;
	protected int m_DropCursor;

	void SZ_GrassCut()
	{
		m_Cutters = new map<int, Object>;
		m_SpiralX = new array<int>;
		m_SpiralZ = new array<int>;
		m_AnchorX = -100000;
		m_AnchorZ = -100000;
		m_DropX = -200000;
		m_DropZ = -200000;
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

	void ~SZ_GrassCut()
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
		int perfStart = TickCount(0);
		float perfTicks = SZ_RoofSnow.DebugTicksPerSec() / 1000.0;
		if (SZ_State.s_DebugGrassBudget)
			ContinueDrop(camera, perfStart, perfTicks);
		else
			m_DropActive = false;
		int ax = Math.Floor(camera[0] / STEP);
		int az = Math.Floor(camera[2] / STEP);
		if (ax != m_AnchorX || az != m_AnchorZ)
		{
			m_AnchorX = ax;
			m_AnchorZ = az;
			m_Scan = 0;
			m_Swept = false;
			m_Rest = 0;
		}
		// while travelling the grid restarts at every step and a full pass never completes: the cutters left
		// behind are removed every second as well (only after the camera moved to another grid cell)
		m_DropTimer += timeslice;
		if (m_DropTimer >= 1.0)
		{
			m_DropTimer = 0;
			if (ax != m_DropX || az != m_DropZ)
				DropFar(camera);
		}
		if (m_Rest > 0)
		{
			m_Rest -= timeslice;
			return;
		}

		int count = m_SpiralX.Count();
		float budget = 0;
		int visited = 0;
		while (budget < 40.0 && visited < count)
		{
			if (SZ_State.s_DebugGrassBudget && visited > 0 && perfTicks > 0 && TickCount(perfStart) >= perfTicks)
				break;
			if (m_Scan >= count)
			{
				m_Scan = 0;
				if (!m_Swept)
					DropFar(camera);
				// a full pass is done: the next one waits a moment while the camera stays in this grid cell
				m_Rest = REST;
				break;
			}
			int gx = ax + m_SpiralX[m_Scan];
			int gz = az + m_SpiralZ[m_Scan];
			m_Scan++;
			visited++;
			int key = gx * 65536 + gz;
			float x = (gx + 0.5) * STEP;
			float z = (gz + 0.5) * STEP;
			float ground = g_Game.SurfaceY(x, z);
			float depth = SZ_State.SnowAt(ground, s0, s1, s2);
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
		if (SZ_State.s_DebugGrassBudget && m_DropActive) return;
		m_Swept = true;
		m_DropX = Math.Floor(camera[0] / STEP);
		m_DropZ = Math.Floor(camera[2] / STEP);
		if (SZ_State.s_DebugGrassBudget)
		{
			m_DropActive = true;
			m_DropCursor = 0;
			return;
		}
		array<int> drop = new array<int>;
		foreach (int key, Object cutter : m_Cutters)
		{
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

	//! Yield between native deletions. Recheck against the current camera so a
	//! reversal never deletes a cutter that has become near again.
	protected void ContinueDrop(vector camera, int started, float limit)
	{
		int visited = 0;
		int removed = 0;
		while (m_DropActive && visited < 32 && removed < 8)
		{
			if (visited > 0 && limit > 0 && TickCount(started) >= limit) break;
			if (m_DropCursor >= m_Cutters.Count()) { m_DropActive = false; break; }
			int key = m_Cutters.GetKey(m_DropCursor);
			int gx = Math.Floor(key / 65536.0);
			int gz = key - gx * 65536;
			float dx = (gx + 0.5) * STEP - camera[0];
			float dz = (gz + 0.5) * STEP - camera[2];
			visited++;
			if (dx * dx + dz * dz > KEEP_RADIUS * KEEP_RADIUS)
			{
				Object o = m_Cutters.Get(key);
				if (o) g_Game.ObjectDelete(o);
				m_Cutters.Remove(key);
				removed++;
			}
			else m_DropCursor++;
		}
	}

	void Clear()
	{
		m_DropActive = false;
		m_DropCursor = 0;
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
