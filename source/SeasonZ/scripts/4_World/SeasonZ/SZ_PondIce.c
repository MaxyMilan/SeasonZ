//! One pond or lake (one water height): the area its pond objects cover and, once measured, the ice plates that cover
//! its open water
class SZ_PondBody
{
	int m_Id;
	float m_X0;
	float m_Z0;
	float m_X1;
	float m_Z1;
	float m_Y;
	// 2 m grid: first cell and size
	int m_GX0;
	int m_GZ0;
	int m_NX;
	int m_NZ;
	//! 0 = not measured, 1 = measuring, 2 = plates known
	int m_Step;
	int m_Cursor;
	//! per 2 m cell while measuring: 0 = a plate may reach here (the terrain lies above the ice), 1 = open water of
	//! this body, 2 = no plate here (lower ground or another water surface)
	ref array<int> m_Cells;
	//! plates: centre, size (m) and model
	ref array<float> m_PX;
	ref array<float> m_PZ;
	ref array<int> m_PS;
	ref array<string> m_PM;
	ref array<Object> m_Objects;
	bool m_Shown;
	int m_CreateAttempts;
	float m_CreateRetryAt;
	bool m_CreateFailed;
	//! the plates show thick ice (pale, opaque) or thin ice (dark, clear)
	bool m_Thick;
	//! camera distance of the last measurement: the game knows the water of distant areas only roughly, so a body
	//! is measured again from closer by
	float m_MeasuredFrom;
	float m_RepairAfter;

	void SZ_PondBody(float x0, float z0, float x1, float z1, float y)
	{
		m_X0 = x0;
		m_Z0 = z0;
		m_X1 = x1;
		m_Z1 = z1;
		m_Y = y;
		m_PX = new array<float>;
		m_PZ = new array<float>;
		m_PS = new array<int>;
		m_PM = new array<string>;
		m_Objects = new array<Object>;
	}
}

//! Ice on ponds and lakes. Every water body of the map (SZ_PondData) is measured once when it first comes near: its
//! open water on a 2 m grid, covered with square plates of 2 to 16 m that never reach over lower ground or another
//! water surface. On clients the plates show the ice just above the water: dark clear ice while it is thin, pale ice
//! once it is thick, and the snow cover runs over thick ice (SZ_SnowCarpet). Thick ice carries people: its plates
//! have a roadway, and the server keeps the same plates around every player, so walking on it is the same on both
//! sides. Thin ice has no roadway; a player breaks through it into the water.
class SZ_PondIce
{
	static const float RADIUS = 1000.0;
	static const float KEEP_RADIUS = 1150.0;
	//! server: walkable ice around the players
	static const float SERVER_RADIUS = 300.0;
	static const float SERVER_KEEP_RADIUS = 360.0;
	static const float CELL = 2.0;
	//! the plates lie this far above the water
	static const float LIFT = 0.02;
	//! largest plate, in cells (16 m: the texture period of the plate models)
	static const int BLOCK = 8;
	static const float BUDGET = 3.0;
	//! no measuring for this long after the start and after a jump of the camera (the area is still loading)
	static const float SETTLE = 15.0;
	//! a body measured from farther than this is measured again when the camera comes within half that distance
	static const float REMEASURE_FROM = 250.0;

	protected ref array<ref SZ_PondBody> m_Bodies;
	protected int m_Cursor;
	protected int m_Objects;
	protected int m_Plates;
	protected float m_Cost;
	protected vector m_Camera;
	protected float m_Clock;
	protected float m_SettleUntil = SETTLE;
	protected vector m_LastCamera;
	protected bool m_Server;
	protected ref array<vector> m_Players;
	protected ref array<Man> m_ServerPlayers;
	protected float m_Radius = RADIUS;
	protected float m_KeepRadius = KEEP_RADIUS;
	protected float m_RescueClock;

	void Init()
	{
		m_Bodies = new array<ref SZ_PondBody>;
		string world;
		g_Game.GetWorldName(world);
		world.ToLower();
		array<float> data = SZ_PondData.ForWorld(world);
		if (data)
		{
			for (int i = 0; i + 4 < data.Count(); i += 5)
			{
				float x0 = data[i];
				float z0 = data[i + 1];
				float x1 = data[i + 2];
				float z1 = data[i + 3];
				float y = data[i + 4];
				SZ_PondBody body = new SZ_PondBody(x0, z0, x1, z1, y);
			body.m_Id = i / 5;
			m_Bodies.Insert(body);
			}
		}
		Print(string.Format("[SeasonZ] pond ice: %1 water bodies on %2", m_Bodies.Count(), world));
	}

	//! server: only walkable (thick) ice, around the players
	void InitServer()
	{
		m_Server = true;
		m_Radius = SERVER_RADIUS;
		m_KeepRadius = SERVER_KEEP_RADIUS;
		m_Players = new array<vector>;
		m_ServerPlayers = new array<Man>;
		Init();
	}

	int GetObjectCount()
	{
		return m_Objects;
	}

	//! test harness: bodies measured / shown and plates known
	string DebugStats()
	{
		int measured = 0;
		int shown = 0;
		int near = 0;
		int thick = 0;
		foreach (SZ_PondBody b : m_Bodies)
		{
			if (b.m_Step == 2)
				measured++;
			if (b.m_Shown)
				shown++;
			if (b.m_Shown && b.m_Thick)
				thick++;
			if (Dist(b) < RADIUS)
				near++;
		}
		return string.Format("bodies=%1 near=%2 measured=%3 shown=%4 thick=%5 plates known=%6 objects=%7", m_Bodies.Count(), near, measured, shown, thick, m_Plates, m_Objects);
	}

	protected float IceAt(float altitude)
	{
		return SZ_State.SnowAt(altitude, SZ_State.s_Ice0, SZ_State.s_Ice1, SZ_State.s_Ice2);
	}

	//! Local QA: compare native coverage with the authoritative carrying decision.
	void DebugPoint(vector pos)
	{
		foreach (SZ_PondBody b : m_Bodies)
		{
			if (DistTo(b, pos) > 0)
				continue;
			int covering = 0;
			for (int i = 0; i < b.m_Objects.Count(); i++)
			{
				float half = b.m_PS[i] * 0.5;
				if (b.m_Objects[i] && Math.AbsFloat(pos[0] - b.m_PX[i]) < half && Math.AbsFloat(pos[2] - b.m_PZ[i]) < half)
					covering++;
			}
			Print(string.Format("[SeasonZ] iceprobe id=%1 y=%2 step=%3 from=%4 thick=%5 shown=%6 plates=%7 objects=%8 covering=%9", b.m_Id, b.m_Y, b.m_Step, b.m_MeasuredFrom, b.m_Thick, b.m_Shown, b.m_PX.Count(), b.m_Objects.Count(), covering));
			Print(string.Format("[SeasonZ] iceprobe class=%1", Classify(b, pos[0], pos[2])));
		}
	}

	//! test harness: forget every measurement, so the bodies are measured again
	void DebugRemeasure()
	{
		foreach (SZ_PondBody b : m_Bodies)
		{
			if (b.m_Objects.Count() > 0)
				Hide(b);
			b.m_CreateAttempts = 0;
			b.m_CreateRetryAt = 0;
			b.m_CreateFailed = false;
			b.m_Step = 0;
			b.m_PX.Clear();
			b.m_PZ.Clear();
			b.m_PS.Clear();
			b.m_PM.Clear();
		}
		m_Plates = 0;
	}
	//! test harness: the cell classes of the body around a point, one text row per grid row, into a file
	string DebugDumpBody(vector pos, string path)
	{
		foreach (SZ_PondBody b : m_Bodies)
		{
			if (pos[0] < b.m_X0 || pos[0] > b.m_X1 || pos[2] < b.m_Z0 || pos[2] > b.m_Z1)
				continue;
			int gx0 = Math.Round(b.m_X0 / CELL);
			int gz0 = Math.Round(b.m_Z0 / CELL);
			int nx = Math.Round((b.m_X1 - b.m_X0) / CELL);
			int nz = Math.Round((b.m_Z1 - b.m_Z0) / CELL);
			FileHandle fh = OpenFile(path, FileMode.WRITE);
			if (fh == 0)
				return "no file";
			FPrintln(fh, string.Format("%1 %2 %3 %4 %5", gx0, gz0, nx, nz, b.m_Y));
			for (int cz = 0; cz < nz; cz++)
			{
				string row = "";
				for (int cx = 0; cx < nx; cx++)
				{
					float x = (gx0 + cx + 0.5) * CELL;
					float z = (gz0 + cz + 0.5) * CELL;
					int c = Classify(b, x, z);
					row += c.ToString();
				}
				FPrintln(fh, row);
			}
			CloseFile(fh);
			return string.Format("body %1..%2 y=%3 cells %4x%5", Vector(b.m_X0, 0, b.m_Z0), Vector(b.m_X1, 0, b.m_Z1), b.m_Y, nx, nz);
		}
		return "no body here";
	}

	//! horizontal distance from the camera (server: the nearest player) to the body's area
	protected float Dist(SZ_PondBody b)
	{
		if (!m_Server)
			return DistTo(b, m_Camera);
		float best = 1000000.0;
		foreach (vector p : m_Players)
		{
			float d = DistTo(b, p);
			if (d < best)
				best = d;
		}
		return best;
	}

	protected float DistTo(SZ_PondBody b, vector pos)
	{
		float dx = 0;
		float dz = 0;
		if (pos[0] < b.m_X0)
			dx = b.m_X0 - pos[0];
		else if (pos[0] > b.m_X1)
			dx = pos[0] - b.m_X1;
		if (pos[2] < b.m_Z0)
			dz = b.m_Z0 - pos[2];
		else if (pos[2] > b.m_Z1)
			dz = pos[2] - b.m_Z1;
		return Math.Sqrt(dx * dx + dz * dz);
	}

	//! server: the players' positions, then the same work as on a client
	void UpdateServer(float timeslice)
	{
		if (!m_Bodies || m_Bodies.Count() == 0)
			return;
		m_Players.Clear();
		m_ServerPlayers.Clear();
		g_Game.GetPlayers(m_ServerPlayers);
		m_RescueClock += timeslice;
		bool rescue = m_RescueClock >= 1.0;
		if (rescue)
			m_RescueClock = 0;
		foreach (Man man : m_ServerPlayers)
		{
			if (!man)
				continue;
			m_Players.Insert(man.GetPosition());
		}
		m_Clock += timeslice;
		Work();
		if (rescue)
		{
			foreach (Man swimmer : m_ServerPlayers)
			{
				if (swimmer)
					RescueUnderIce(swimmer);
			}
		}
	}

	//! server: a player in the water under ice that carries people (logged out while swimming, or swimming while the
	//! pond froze over) climbs out onto the ice instead of being trapped under its plates and drowning
	protected void RescueUnderIce(Man man)
	{
		if (!man.IsAlive() || man.GetParent())
			return;
		vector pos = man.GetPosition();
		float water;
		if (!SZ_Util.PondWater(pos[0], pos[2], water))
			return;
		if (!SZ_PondState.At(pos[0], pos[2], water))
			return; // a lingering roadway or a bridge must not rescue through thawed ice
		if (pos[1] > water - 0.05)
			return;
		// the roadway of a plate above the player (without one the ice is thin or open here: nothing to climb onto)
		float road = g_Game.SurfaceRoadY3D(pos[0], water + 1.0, pos[2], RoadSurfaceDetection.UNDER);
		if (road < water + LIFT * 0.5 || road > water + 0.5)
		{
			RepairCoverage(pos, water);
			return;
		}
		man.SetPosition(Vector(pos[0], road + 0.05, pos[2]));
		Print(string.Format("[SeasonZ] pond ice: a player under the ice at %1 climbed out onto it", pos));
	}

	//! Water geometry can finish streaming after a server measurement. Do not cache its missing cells forever.
	//! Retain the old plates until the normal bounded measurement finishes; never teleport without a native road.
	protected void RepairCoverage(vector pos, float water)
	{
		foreach (SZ_PondBody b : m_Bodies)
		{
			if (DistTo(b, pos) > 0 || Math.AbsFloat(water - b.m_Y) >= 0.06 || !b.m_Thick || !b.m_Shown || b.m_Step != 2 || b.m_CreateFailed || m_Clock < b.m_RepairAfter)
				continue;
			bool covered = false;
			for (int i = 0; i < b.m_Objects.Count(); i++)
			{
				float half = b.m_PS[i] * 0.5;
				if (b.m_Objects[i] && Math.AbsFloat(pos[0] - b.m_PX[i]) < half && Math.AbsFloat(pos[2] - b.m_PZ[i]) < half)
					covered = true;
			}
			if (covered)
				continue;
			b.m_RepairAfter = m_Clock + 5.0;
			b.m_Step = 0;
			Print(string.Format("[SeasonZ] pond ice: rechecking stale server coverage body=%1 at %2", b.m_Id, pos));
		}
	}

	void Update(float timeslice, vector camera)
	{
		if (!m_Bodies || m_Bodies.Count() == 0)
			return;
		m_Clock += timeslice;
		if (m_Clock > 1.0 && vector.Distance(camera, m_LastCamera) > 200.0)
			m_SettleUntil = m_Clock + SETTLE;
		m_LastCamera = camera;
		m_Camera = camera;
		Work();
		SZ_State.s_StatIce = m_Objects;
	}

	protected void Work()
	{
		m_Cost = 0;
		int n = m_Bodies.Count();
		int visited = 0;
		while (m_Cost < BUDGET && visited < n)
		{
			if (m_Cursor >= n)
				m_Cursor = 0;
			m_Cost += 0.01;
			if (Process(m_Bodies[m_Cursor]))
			{
				m_Cursor++;
				visited++;
			}
		}
	}

	//! false while the body still needs work this frame
	protected bool Process(SZ_PondBody b)
	{
		float ice = IceAt(b.m_Y);
		// thick ice carries snow and people and looks pale; thin ice (freezing up, rotting in spring) is dark like
		// clear ice and the server has no plates for it
		bool thick = SZ_PondState.Carries(b.m_Id);
		// Keep physical state current even while the body is hidden or unmeasured.
		if (thick != b.m_Thick)
		{
			if (b.m_Objects.Count() > 0 || b.m_CreateAttempts > 0)
				Hide(b);
			b.m_Thick = thick;
		}
		bool frozen = ice >= SZ_Const.ICE_VISIBLE;
		if (m_Server)
			frozen = thick;
		if (!frozen)
		{
			if (b.m_Objects.Count() > 0 || b.m_CreateAttempts > 0)
				Hide(b);
			return true;
		}
		float dist = Dist(b);
		if (dist > m_KeepRadius)
		{
			if (b.m_Objects.Count() > 0 || b.m_CreateAttempts > 0)
				Hide(b);
			return true;
		}
		if (dist > m_Radius && !b.m_Shown && b.m_Objects.Count() == 0)
			return true;
		if (b.m_Step == 2 && b.m_MeasuredFrom > REMEASURE_FROM && dist < b.m_MeasuredFrom * 0.5 && m_Clock >= m_SettleUntil)
			b.m_Step = 0;
		if (b.m_Step < 2)
			return Measure(b);
		if (!b.m_Shown)
			return Show(b);
		return true;
	}

	protected bool Measure(SZ_PondBody b)
	{
		if (b.m_Step == 0)
		{
			if (m_Clock < m_SettleUntil)
				return true;
			b.m_GX0 = Math.Round(b.m_X0 / CELL);
			b.m_GZ0 = Math.Round(b.m_Z0 / CELL);
			b.m_NX = Math.Round((b.m_X1 - b.m_X0) / CELL);
			b.m_NZ = Math.Round((b.m_Z1 - b.m_Z0) / CELL);
			b.m_Cells = new array<int>;
			b.m_Cells.Resize(b.m_NX * b.m_NZ);
			b.m_Cursor = 0;
			b.m_Step = 1;
			b.m_MeasuredFrom = Dist(b);
		}
		int total = b.m_NX * b.m_NZ;
		while (b.m_Cursor < total && m_Cost < BUDGET)
		{
			int i = b.m_Cursor;
			int cx = i % b.m_NX;
			int cz = i / b.m_NX;
			float x = (b.m_GX0 + cx + 0.5) * CELL;
			float z = (b.m_GZ0 + cz + 0.5) * CELL;
			b.m_Cells[i] = Classify(b, x, z);
			b.m_Cursor++;
			m_Cost += 0.002;
		}
		if (b.m_Cursor < total)
			return false;
		// a new measurement replaces the plates of an earlier one
		if (b.m_Objects.Count() > 0)
			Hide(b);
		m_Plates -= b.m_PX.Count();
		b.m_PX.Clear();
		b.m_PZ.Clear();
		b.m_PS.Clear();
		b.m_PM.Clear();
		Tile(b);
		b.m_Cells = null;
		b.m_Step = 2;
		m_Plates += b.m_PX.Count();
		return true;
	}

	protected int Classify(SZ_PondBody b, float x, float z)
	{
		float ground = g_Game.SurfaceY(x, z);
		// the water a player would swim in (SurfaceIsPond misses spots between the turned squares of large lakes)
		float water = g_Game.GetWaterSurfaceHeightNoFakeWave(Vector(x, ground, z));
		if (Math.AbsFloat(water - b.m_Y) < 0.06)
		{
			if (ground < b.m_Y)
				return 1;
			return 0;
		}
		if (ground < b.m_Y + LIFT + 0.03)
			return 2;
		return 0;
	}

	protected int CellAt(SZ_PondBody b, int gx, int gz)
	{
		int cx = gx - b.m_GX0;
		int cz = gz - b.m_GZ0;
		if (cx < 0 || cz < 0 || cx >= b.m_NX || cz >= b.m_NZ)
			return 2;
		return b.m_Cells[cz * b.m_NX + cx];
	}

	//! plates over the open water: squares on the world grid, as large as the water allows
	protected void Tile(SZ_PondBody b)
	{
		int bx0 = Math.Floor(b.m_GX0 / (BLOCK * 1.0));
		int bz0 = Math.Floor(b.m_GZ0 / (BLOCK * 1.0));
		int bx1 = Math.Floor((b.m_GX0 + b.m_NX - 1) / (BLOCK * 1.0));
		int bz1 = Math.Floor((b.m_GZ0 + b.m_NZ - 1) / (BLOCK * 1.0));
		for (int bz = bz0; bz <= bz1; bz++)
		{
			for (int bx = bx0; bx <= bx1; bx++)
				Cover(b, bx * BLOCK, bz * BLOCK, BLOCK);
		}
	}

	protected void Cover(SZ_PondBody b, int gx, int gz, int n)
	{
		bool water = false;
		bool blocked = false;
		for (int j = 0; j < n && !blocked; j++)
		{
			for (int i = 0; i < n; i++)
			{
				int c = CellAt(b, gx + i, gz + j);
				if (c == 1)
				{
					water = true;
				}
				else if (c == 2)
				{
					blocked = true;
					break;
				}
			}
		}
		if (!blocked)
		{
			if (water)
			{
				b.m_PX.Insert((gx + n * 0.5) * CELL);
				b.m_PZ.Insert((gz + n * 0.5) * CELL);
				b.m_PS.Insert(n * CELL);
				// the model of the plate's place in the texture period
				int period = BLOCK / n;
				int vx = Wrap(gx / n, period);
				int vz = Wrap(gz / n, period);
				int size = n * 2;
				b.m_PM.Insert("_" + size.ToString() + "_" + vx.ToString() + vz.ToString() + ".p3d");
			}
			return;
		}
		if (n == 1)
			return;
		int h = n / 2;
		Cover(b, gx, gz, h);
		Cover(b, gx + h, gz, h);
		Cover(b, gx, gz + h, h);
		Cover(b, gx + h, gz + h, h);
	}

	protected int Wrap(int v, int n)
	{
		int r = v % n;
		if (r < 0)
			r += n;
		return r;
	}

	protected bool Show(SZ_PondBody b)
	{
		if (b.m_CreateFailed || m_Clock < b.m_CreateRetryAt)
			return true; // yield this body; shown remains false
		while (b.m_Objects.Count() < b.m_PX.Count() && m_Cost < BUDGET)
		{
			int i = b.m_Objects.Count();
			string model = SZ_Const.DATA + "ice\\sz_icet" + b.m_PM[i];
			if (b.m_Thick)
				model = SZ_Const.DATA + "ice\\sz_ice" + b.m_PM[i];
			Object o = g_Game.CreateStaticObjectUsingP3D(model, Vector(b.m_PX[i], b.m_Y + LIFT, b.m_PZ[i]), "0 0 0", 1.0, true);
			m_Cost += 0.2;
			if (!o)
			{
				b.m_CreateAttempts++;
				b.m_CreateRetryAt = m_Clock + b.m_CreateAttempts * 5.0;
				b.m_CreateFailed = b.m_CreateAttempts >= 3;
				if (b.m_CreateAttempts == 1 || b.m_CreateFailed)
					Print(string.Format("[SeasonZ] ice creation failed model=%1 attempts=%2; repair assets and remeasure", model, b.m_CreateAttempts));
				return true;
			}
			b.m_Objects.Insert(o);
			m_Objects++;
			b.m_CreateAttempts = 0;
		}
		if (b.m_Objects.Count() < b.m_PX.Count())
			return false;
		b.m_Shown = true;
		return true;
	}

	protected void Hide(SZ_PondBody b)
	{
		foreach (Object o : b.m_Objects)
		{
			if (o)
			{
				g_Game.ObjectDelete(o);
				m_Objects--;
			}
		}
		b.m_Objects.Clear();
		b.m_Shown = false;
		b.m_CreateAttempts = 0;
		b.m_CreateRetryAt = 0;
		b.m_CreateFailed = false;
		m_Cost += 0.05;
	}

	void Clear()
	{
		if (!m_Bodies)
			return;
		foreach (SZ_PondBody b : m_Bodies)
		{
			if (b.m_Objects.Count() > 0)
				Hide(b);
		}
	}
}
