//! One triangle of the snow cover: plane y = yc + a * (x - cx) + b * (z - cz) over a square (sub)cell
class DS_SnowTri
{
	int m_Shape; // 0 = a, 1 = b, 2 = c, 3 = d
	float m_Size;
	float m_CX;
	float m_CZ;
	float m_A;
	float m_B;
	float m_YC;
	float m_Lift; // extra height so no terrain bump pokes through an approximating triangle
	string m_Variant; // model variant: the triangle's size and place in the 30 m texture period
	float m_K; // horizontal scale of the model (1 on the 7.5 m terrain grid the models were made for)
	//! cut along a wall: drawn with the c model mapped onto the three corners below (the plane stays the one of the
	//! shape it was cut from)
	bool m_Free;
	float m_X0;
	float m_Z0;
	float m_X1;
	float m_Z1;
	float m_X2;
	float m_Z2;
}

//! One grid cell of the snow cover at one level of detail
class DS_SnowCell
{
	int m_Level;
	int m_Stage;
	int m_X;
	int m_Z;
	int m_Sig; // which neighbouring coarser cells this cell is stitched to
	float m_Avg;
	int m_Epoch; // forced re-placement generation (test harness lighting and height changes)
	int m_BuildGen; // pond ice generation the triangles were built for
	float m_RetiredAt;
	ref array<ref DS_SnowTri> m_Tris;
	ref array<Object> m_Objects;

	void DS_SnowCell()
	{
		m_Tris = new array<ref DS_SnowTri>;
		m_Objects = new array<Object>;
	}
}

//! Client: builds a snow cover out of static triangles that follow the terrain grid.
//! Five levels of detail: the exact terrain grid near the camera (level 0), then cells of 2, 4, 16 and 32 terrain
//! cells further out, up to the largest object view distance of the game options. A coarse cell floats just high
//! enough to keep the terrain between its corners underneath, and neighbouring levels meet exactly along their
//! shared edges. Every triangle model carries a skirt that hangs below its edges, so hairline cracks between
//! separate objects and short-lived steps while the layout follows the camera show snow instead of the dark ground.
//! The models are made at their real size and every triangle picks the model of its place in the 30 m texture
//! period, so the snow pattern, its relief and its lighting continue across all cells and levels.
class DS_SnowCarpet
{
	static const int LEVELS = 5;
	//! level 0 cells are built this far beyond the level 0 area, hidden under the level 1 cover, so they are ready
	//! when the camera moves on and the level 0 area grows
	static const float PREBUILD = 25.0;
	//! terrain grid the ground models were made for
	static const float MODEL_CELL = 7.5;
	//! height of the level 0 cover above the terrain and the roads on it
	static const float OFF0 = 0.04;
	//! roads and paths are drawn a little above the terrain; the cover rises over them so they cannot show through
	//! as dark lines. Walkable surfaces higher than this (floors, porches, blocks, platforms, bridges) are not roads:
	//! the cover rising over them would heap a mound of snow over the cells around them
	static const float ROAD_PROBE = 0.35;
	//! a walkable surface more than this above the ground lifts the cover only where it is as wide as a road: it
	//! continues at about the same height this far away in at least three of the four directions (a step, a bench
	//! or a low block does not). Sidewalks lie up to about 17 cm above the ground and are often narrower than that:
	//! they lift the cover without the test
	static const float ROAD_NARROW = 0.2;
	static const float ROAD_SPREAD = 1.5;
	//! cells of an earlier layout stay until the new layout has built their area; only when the builder falls far
	//! behind (very fast travel) are the oldest ones dropped
	static const float RETIRE_SECONDS = 30.0;
	static const int RETIRE_MAX = 5000;
	// time per frame for deleting the cells of earlier layouts, and for building and staging cells on foot (ms)
	static const float DROP_MS = 1.0;
	static const float BUILD_MS = 2.5;
	//! blocks of the coarsest level around the camera that are worked on first after every layout change
	static const int NEAR_BLOCKS = 9;
	//! height of the ice surface of a frozen pond above the water (the snow cover lies on it)
	static const float ICE_TOP = 0.03;
	//! level 0 cells are split this many times around buildings (7.5 m cells: 0.94 m triangles at the walls)
	static const int EXACT_DEPTH = 3;
	//! the smallest triangles at a wall are cut along it: each edge crossing is found by halving the edge this often
	//! (a 0.94 m edge to 3 cm)
	static const int CLIP_STEPS = 5;
	//! a floor this high above the ground hides the snow under it, so the cover may run under the building; the
	//! floor is looked for below RAISED_PROBE above the ground (the ground floor, not an upper storey)
	static const float RAISED_FLOOR = 0.2;
	static const float RAISED_PROBE = 2.5;
	//! deep under a wide open roof (open sheds, canopies, fuel stations) no snow falls: the roof reaches this far
	//! around the point in all four directions of the building (metres)
	static const float WIDE_ROOF = 2.0;
	protected static DS_SnowCarpet s_Instance;
	//! test harness: print every decision while building a cell
	static bool s_DebugBuild;

	// per level: cell size in terrain cells, outer radius, height above the lifted terrain, largest lift
	protected ref array<int> m_F;
	protected ref array<float> m_Rad;
	protected ref array<float> m_Off;
	protected ref array<float> m_Cap;
	protected float m_Cell;
	protected bool m_Ready;
	protected ref array<ref map<int, ref DS_SnowCell>> m_Cells;
	// per level: terrain rise above each cell's two triangles, and the lift shared by the cells around a vertex
	protected ref array<ref map<int, float>> m_Rise;
	protected ref array<ref map<int, float>> m_Lift;
	// per level: stitching signatures of the cells of the current work list
	protected ref array<ref map<int, int>> m_Sig;
	// per level: the cells of the work list being built
	protected ref array<ref map<int, bool>> m_Keep;
	protected ref array<int> m_WLevel;
	protected ref array<int> m_WX;
	protected ref array<int> m_WZ;
	protected ref array<int> m_SpiralX;
	protected ref array<int> m_SpiralZ;
	protected int m_Scan;
	protected int m_AnchorX;
	protected int m_AnchorZ;
	protected float m_S0;
	protected float m_S1;
	protected float m_S2;
	protected vector m_Camera;
	protected int m_Objects;
	// test harness statistics: calls of the costly probes (water, road, road width, blocked, wide roof, roof,
	// enclosed) while building the current cell
	protected ref array<int> m_Calls;
	protected int m_SkirtCount;
	protected float m_Cost;
	// camera position the level layout was built for
	protected vector m_ListCamera;
	// forced re-placement generation (test harness lighting normal and extra height)
	protected int m_Epoch;
	// cells of an earlier layout stay until the new layout has been built once, so moving opens no holes
	protected ref array<ref DS_SnowCell> m_Retired;
	protected int m_RetiredCursor;
	protected float m_Clock;
	// work list items of the nearest blocks: after every layout change they are checked first
	protected int m_NearEnd;
	protected int m_NearScan;
	// layout generation, and the one the running full pass of the main cursor started in
	protected int m_Layout;
	protected int m_PassLayout;
	protected int m_NormalMode;
	protected float m_ExtraOffset;
	// camera speed (m/s, smoothed) and the previous camera position: fast travel gets a larger build budget
	protected float m_Speed;
	protected vector m_PrevCamera;
	// level 0 cells: highest road surface above the terrain inside the cell
	protected ref map<int, float> m_Road0;
	// level 0 cells: which diagonal the terrain uses (1 = from the low corner to the high corner)
	protected ref map<int, int> m_Diag0;
	// frozen ponds that carry snow, per tracked height (bit 1 = sea level, 2 = 250 m, 4 = 500 m): the cover runs
	// over them at the ice level instead of leaving the water open
	protected int m_PondMode;
	// generation of the pond mode; cells built for another one are rebuilt in place
	protected int m_BuildGen;
	// road rule in use: highest walkable surface the cover rises over, and whether it has to be wide
	protected float m_RoadProbe;
	protected bool m_RoadWide;

	void DS_SnowCarpet()
	{
		m_F = new array<int>;
		m_Rad = new array<float>;
		m_Off = new array<float>;
		m_Cap = new array<float>;
		// cell size (terrain cells), outer radius (m), height above the lifted terrain (m), largest lift (m)
		AddLevel(1, 150.0, OFF0, 0.0);
		AddLevel(2, 300.0, 0.08, 0.6);
		AddLevel(4, 600.0, 0.12, 1.2);
		AddLevel(16, 1600.0, 0.5, 3.0);
		AddLevel(32, 3200.0, 0.8, 4.0);
		m_Cells = new array<ref map<int, ref DS_SnowCell>>;
		m_Rise = new array<ref map<int, float>>;
		m_Lift = new array<ref map<int, float>>;
		m_Sig = new array<ref map<int, int>>;
		m_Keep = new array<ref map<int, bool>>;
		for (int level = 0; level < LEVELS; level++)
		{
			m_Cells.Insert(new map<int, ref DS_SnowCell>);
			m_Rise.Insert(new map<int, float>);
			m_Lift.Insert(new map<int, float>);
			m_Sig.Insert(new map<int, int>);
			m_Keep.Insert(new map<int, bool>);
		}
		m_WLevel = new array<int>;
		m_WX = new array<int>;
		m_WZ = new array<int>;
		m_SpiralX = new array<int>;
		m_SpiralZ = new array<int>;
		m_Retired = new array<ref DS_SnowCell>;
		m_Calls = new array<int>;
		for (int cc = 0; cc < 7; cc++)
			m_Calls.Insert(0);
		m_Road0 = new map<int, float>;
		m_Diag0 = new map<int, int>;
		m_RoadProbe = ROAD_PROBE;
		m_RoadWide = true;
		m_AnchorX = -1000000;
		m_AnchorZ = -1000000;
		s_Instance = this;
	}

	protected void AddLevel(int cells, float radius, float offset, float cap)
	{
		m_F.Insert(cells);
		m_Rad.Insert(radius);
		m_Off.Insert(offset);
		m_Cap.Insert(cap);
	}

	void ~DS_SnowCarpet()
	{
		Clear();
		if (s_Instance == this)
			s_Instance = null;
	}

	void Init()
	{
		float detected = DetectGrid();
		m_Cell = detected;
		if (m_Cell <= 0)
			m_Cell = 2.5;

		BuildSpiral();
		m_Ready = true;
		string sizes = "";
		string radii = "";
		for (int level = 0; level < LEVELS; level++)
		{
			sizes += " " + Size(level).ToString();
			radii += " " + m_Rad[level].ToString();
		}
		Print(string.Format("[DynamicSeasons] snow cover: terrain grid detected=%1 m, level cells%2 m, radii%3 m", detected, sizes, radii));
	}

	int GetObjectCount()
	{
		return m_Objects;
	}

	int GetSkirtCount()
	{
		return m_SkirtCount;
	}

	float GetCell()
	{
		return m_Cell;
	}

	//! finds the terrain grid spacing: along grid lines the terrain is linear between vertices
	protected float DetectGrid()
	{
		int worldSize = g_Game.GetWorld().GetWorldSize();
		if (worldSize <= 0)
			worldSize = 15360;

		array<float> candidates = {20.0, 16.0, 15.0, 12.5, 10.0, 8.0, 7.5, 6.4, 6.25, 5.0, 4.0, 3.2, 2.5, 2.0, 1.6, 1.25, 1.0};
		foreach (float s : candidates)
		{
			int informative = 0;
			bool linear = true;
			for (int i = 0; i < 80 && linear; i++)
			{
				float x0 = Math.Floor(Math.RandomFloat(worldSize * 0.1, worldSize * 0.9) / s) * s;
				float z0 = Math.Floor(Math.RandomFloat(worldSize * 0.1, worldSize * 0.9) / s) * s;
				float h0 = g_Game.SurfaceY(x0, z0);
				float hx = g_Game.SurfaceY(x0 + s, z0);
				float hz = g_Game.SurfaceY(x0, z0 + s);
				float mx = g_Game.SurfaceY(x0 + s * 0.5, z0);
				float mz = g_Game.SurfaceY(x0, z0 + s * 0.5);
				if (Math.AbsFloat(mx - (h0 + hx) * 0.5) > 0.004 || Math.AbsFloat(mz - (h0 + hz) * 0.5) > 0.004)
					linear = false;
				if (Math.AbsFloat(hx - h0) > 0.05 || Math.AbsFloat(hz - h0) > 0.05)
					informative++;
			}
			if (linear && informative >= 25)
				return s;
		}
		return 0;
	}


	//! cell size of a level in metres
	protected float Size(int level)
	{
		return m_Cell * m_F[level];
	}

	//! how many cells of a level fit along one cell of the next coarser level
	protected int Ratio(int level)
	{
		return m_F[level + 1] / m_F[level];
	}

	protected void BuildSpiral()
	{
		m_SpiralX.Clear();
		m_SpiralZ.Clear();
		int top = LEVELS - 1;
		int maxRing = Math.Ceil(m_Rad[top] / Size(top)) + 1;
		m_SpiralX.Insert(0);
		m_SpiralZ.Insert(0);
		for (int ring = 1; ring <= maxRing; ring++)
		{
			for (int k = -ring; k < ring; k++)
			{
				m_SpiralX.Insert(k);
				m_SpiralZ.Insert(-ring);
				m_SpiralX.Insert(ring);
				m_SpiralZ.Insert(k);
				m_SpiralX.Insert(-k);
				m_SpiralZ.Insert(ring);
				m_SpiralX.Insert(-ring);
				m_SpiralZ.Insert(-k);
			}
		}
	}

	protected float DistXZ(float x, float z)
	{
		float dx = x - m_Camera[0];
		float dz = z - m_Camera[2];
		return Math.Sqrt(dx * dx + dz * dz);
	}


	//! true when a cell of level 1 or up is not split into finer cells in the current layout, so its area is drawn
	//! at this level or a coarser one
	protected bool Coarse(int level, int x, int z)
	{
		if (level <= 0)
			return false;
		float s = Size(level);
		float dx = (x + 0.5) * s - m_ListCamera[0];
		float dz = (z + 0.5) * s - m_ListCamera[2];
		return Math.Sqrt(dx * dx + dz * dz) > m_Rad[level - 1];
	}

	protected void AddItem(int level, int x, int z)
	{
		m_WLevel.Insert(level);
		m_WX.Insert(x);
		m_WZ.Insert(z);
		m_Keep[level].Set(x * 65536 + z, true);
	}

	//! adds a cell to the work list, or its finer cells where it lies within the radius of the finer level
	protected void ListCell(int level, int x, int z)
	{
		if (level == 0)
		{
			AddItem(0, x, z);
			return;
		}
		float s = Size(level);
		float d = DistXZ((x + 0.5) * s, (z + 0.5) * s);
		int r = Ratio(level - 1);
		if (d > m_Rad[level - 1])
		{
			AddItem(level, x, z);
			if (level == 1 && d <= m_Rad[0] + PREBUILD)
			{
				for (int pa = 0; pa < r; pa++)
				{
					for (int pb = 0; pb < r; pb++)
						AddItem(0, x * r + pa, z * r + pb);
				}
			}
			return;
		}
		for (int a = 0; a < r; a++)
		{
			for (int b = 0; b < r; b++)
				ListCell(level - 1, x * r + a, z * r + b);
		}
	}

	//! rebuilds the ordered work list of active cells (near to far) and drops cells that left the area
	protected void RebuildWorkList()
	{
		m_ListCamera = m_Camera;
		m_Layout++;
		m_NearEnd = 0;
		m_NearScan = 0;
		m_WLevel.Clear();
		m_WX.Clear();
		m_WZ.Clear();
		int level;
		for (level = 0; level < LEVELS; level++)
			m_Keep[level].Clear();

		int top = LEVELS - 1;
		float ct = Size(top);
		int baseX = Math.Floor(m_Camera[0] / ct);
		int baseZ = Math.Floor(m_Camera[2] / ct);
		for (int i = 0; i < m_SpiralX.Count(); i++)
		{
			if (i == NEAR_BLOCKS)
				m_NearEnd = m_WLevel.Count();
			int kx = baseX + m_SpiralX[i];
			int kz = baseZ + m_SpiralZ[i];
			if (kx < 0 || kz < 0)
				continue;
			if (DistXZ((kx + 0.5) * ct, (kz + 0.5) * ct) > m_Rad[top])
				continue;
			ListCell(top, kx, kz);
		}

		for (level = 0; level < LEVELS; level++)
			DropMissing(m_Cells[level], m_Keep[level]);

		// cells along the border of a coarser level take their edge heights from that level
		for (level = 0; level < LEVELS; level++)
			m_Sig[level].Clear();
		for (int w = 0; w < m_WLevel.Count(); w++)
		{
			int lv = m_WLevel[w];
			if (lv >= top)
				continue;
			int sig = BorderSignature(lv, m_WX[w], m_WZ[w]);
			if (sig != 0)
				m_Sig[lv].Set(m_WX[w] * 65536 + m_WZ[w], sig);
		}

		// the terrain analysis caches only grow while travelling; they are cheap to rebuild
		for (level = 1; level < LEVELS; level++)
		{
			if (m_Rise[level].Count() > 30000)
			{
				m_Rise[level].Clear();
				m_Lift[level].Clear();
			}
		}
		if (m_Road0.Count() > 60000)
		{
			m_Road0.Clear();
			m_Diag0.Clear();
		}
		if (m_NearEnd == 0)
			m_NearEnd = m_WLevel.Count();
		// the main cursor keeps its place: restarting at the camera on every change would starve the far rings
		if (m_Scan >= m_WLevel.Count())
			m_Scan = 0;
	}

	protected void DropMissing(map<int, ref DS_SnowCell> cells, map<int, bool> keep)
	{
		array<int> remove = new array<int>;
		for (int i = 0; i < cells.Count(); i++)
		{
			int key = cells.GetKey(i);
			if (!keep.Contains(key))
				remove.Insert(key);
		}
		foreach (int k : remove)
		{
			DS_SnowCell c = cells.Get(k);
			if (c)
			{
				c.m_RetiredAt = m_Clock;
				m_Retired.Insert(c);
			}
			cells.Remove(k);
		}
	}

	protected bool IsWater(float x, float z)
	{
		m_Calls[0] = m_Calls[0] + 1;
		if (g_Game.SurfaceIsSea(x, z))
			return true;
		float water;
		if (!DS_Util.PondWater(x, z, water))
			return false;
		if (m_PondMode == 0)
			return true;
		return !PondCovered(water);
	}

	//! true when the ponds around this water height carry snow (the band of the nearest tracked height)
	protected bool PondCovered(float altitude)
	{
		int bit = 2;
		if (altitude < 125.0)
			bit = 1;
		else if (altitude >= 375.0)
			bit = 4;
		return (m_PondMode & bit) != 0;
	}

	//! height the snow cover lies on: the terrain, or the ice of a frozen pond that carries snow
	float GY(float x, float z)
	{
		float ground = g_Game.SurfaceY(x, z);
		if (m_PondMode == 0)
			return ground;
		float water;
		if (!DS_Util.PondWater(x, z, water))
			return ground;
		if (!PondCovered(water))
			return ground;
		float top = water + ICE_TOP;
		if (top > ground)
			return top;
		return ground;
	}

	//! per tracked height: does its ice carry snow (with a margin, so the state does not flicker at the threshold)
	protected int WantedPondMode()
	{
		int mode = 0;
		if (LevelCarriesSnow(DS_State.s_Ice0, 1))
			mode = mode | 1;
		if (LevelCarriesSnow(DS_State.s_Ice1, 2))
			mode = mode | 2;
		if (LevelCarriesSnow(DS_State.s_Ice2, 4))
			mode = mode | 4;
		return mode;
	}

	protected bool LevelCarriesSnow(float ice, int bit)
	{
		if ((m_PondMode & bit) != 0)
			return ice >= DS_Const.ICE_SNOW_OFF;
		return ice >= DS_Const.ICE_SNOW_ON;
	}

	int GetPondMode()
	{
		return m_PondMode;
	}

	//! how far a road or path surface lies above the ground the snow lies on at a point (0 where there is none). On a
	//! frozen pond that ground is the ice, so the roadway of the ice plates just under it never lifts the cover (from
	//! the bottom of shallow water it would look like a road up to 0.8 m higher)
	protected float RoadAbove(float x, float z)
	{
		float ground = GY(x, z);
		return RoadAboveGround(x, z, ground);
	}

	//! the same with the height of that ground already known
	protected float RoadAboveGround(float x, float z, float ground)
	{
		m_Calls[1] = m_Calls[1] + 1;
		float road = g_Game.SurfaceRoadY3D(x, ground + m_RoadProbe, z, RoadSurfaceDetection.UNDER);
		float d = road - ground;
		if (d < 0.002 || d > m_RoadProbe)
			return 0;
		if (d > ROAD_NARROW && m_RoadWide && !RoadWide(x, z, d))
			return 0;
		return d;
	}

	//! the walkable surface at a point continues at about the same height above the ground in at least three of the
	//! four directions, like a road or a square
	protected bool RoadWide(float x, float z, float d)
	{
		m_Calls[2] = m_Calls[2] + 1;
		int misses = 0;
		for (int k = 0; k < 4; k++)
		{
			float px = x;
			float pz = z;
			if (k == 0)
				px += ROAD_SPREAD;
			else if (k == 1)
				px -= ROAD_SPREAD;
			else if (k == 2)
				pz += ROAD_SPREAD;
			else
				pz -= ROAD_SPREAD;
			float g = GY(px, pz);
			float other = g_Game.SurfaceRoadY3D(px, g + m_RoadProbe, pz, RoadSurfaceDetection.UNDER) - g;
			if (Math.AbsFloat(other - d) > 0.1)
			{
				misses++;
				if (misses >= 2)
					break;
			}
		}
		m_Cost += 0.004;
		return misses < 2;
	}

	//! highest road surface above the terrain inside a level 0 cell, sampled every quarter cell (cached)
	protected float CellRoad0(int ix, int iz)
	{
		int key = ix * 65536 + iz;
		float v;
		if (m_Road0.Find(key, v))
			return v;
		v = 0;
		float x0 = ix * m_Cell;
		float z0 = iz * m_Cell;
		float q = m_Cell * 0.25;
		for (int i = 0; i <= 4; i++)
		{
			for (int j = 0; j <= 4; j++)
			{
				float d = RoadAbove(x0 + i * q, z0 + j * q);
				if (d > v)
					v = d;
			}
		}
		m_Cost += 0.05;
		m_Road0.Set(key, v);
		return v;
	}

	//! road lift of a level 0 grid vertex: the highest road in the four cells around it, so every point of a
	//! cell with a road is lifted at least that much
	protected float VertexRoad0(int vx, int vz)
	{
		float a = CellRoad0(vx - 1, vz - 1);
		float b = CellRoad0(vx, vz - 1);
		float c = CellRoad0(vx - 1, vz);
		float d = CellRoad0(vx, vz);
		return Math.Max(Math.Max(a, b), Math.Max(c, d));
	}

	//! which diagonal the terrain uses inside a level 0 cell (cached)
	protected bool CellDiag0(int ix, int iz)
	{
		int key = ix * 65536 + iz;
		int v;
		if (m_Diag0.Find(key, v))
			return v == 1;
		float x0 = ix * m_Cell;
		float z0 = iz * m_Cell;
		// the terrain's own diagonal, as the cells are built (see CreateCell)
		float h00 = g_Game.SurfaceY(x0, z0);
		float h11 = g_Game.SurfaceY(x0 + m_Cell, z0 + m_Cell);
		float h10 = g_Game.SurfaceY(x0 + m_Cell, z0);
		float h01 = g_Game.SurfaceY(x0, z0 + m_Cell);
		float hc = g_Game.SurfaceY(x0 + m_Cell * 0.5, z0 + m_Cell * 0.5);
		bool diag = Math.AbsFloat(hc - (h00 + h11) * 0.5) <= Math.AbsFloat(hc - (h10 + h01) * 0.5);
		v = 0;
		if (diag)
			v = 1;
		m_Diag0.Set(key, v);
		return diag;
	}

	//! road lift anywhere on level 0: linear inside each terrain triangle between the grid vertices, like the
	//! terrain itself, so the smaller pieces of a cell next to buildings meet its whole triangles without a step
	protected float RoadLift0(float x, float z)
	{
		float fx = x / m_Cell;
		float fz = z / m_Cell;
		int ix = Math.Floor(fx + 0.0001);
		int iz = Math.Floor(fz + 0.0001);
		float u = Math.Clamp(fx - ix, 0, 1);
		float v = Math.Clamp(fz - iz, 0, 1);
		float l00 = VertexRoad0(ix, iz);
		float l10 = VertexRoad0(ix + 1, iz);
		float l01 = VertexRoad0(ix, iz + 1);
		float l11 = VertexRoad0(ix + 1, iz + 1);
		if (l00 <= 0 && l10 <= 0 && l01 <= 0 && l11 <= 0)
			return 0;
		return PlaneAt(CellDiag0(ix, iz), u, v, l00, l10, l11, l01);
	}

	//! height of the snow surface near the camera (level 0), for footprints and other things lying on the snow
	static float CoverHeightAt(float x, float z)
	{
		if (!s_Instance || !s_Instance.m_Ready)
			return g_Game.SurfaceY(x, z) + OFF0;
		float ground = s_Instance.GY(x, z);
		float lift = s_Instance.RoadLift0(x, z);
		return ground + lift + OFF0 + s_Instance.m_ExtraOffset;
	}


	//! true when the snow cover shows snow at this point. Near the camera (level 0) this follows the real triangles,
	//! so the bare ground under eaves and around buildings stays bare, and the bare spots of thin snow (the coverage
	//! pattern of the cell's stage); further out the coarse levels cover everything but water.
	static bool CoversAt(float x, float z)
	{
		if (!s_Instance || !s_Instance.m_Ready)
			return false;
		int ix = Math.Floor(x / s_Instance.m_Cell);
		int iz = Math.Floor(z / s_Instance.m_Cell);
		DS_SnowCell cell = s_Instance.m_Cells[0].Get(ix * 65536 + iz);
		if (!cell)
			return true;
		if (cell.m_Stage <= 0)
			return false;
		foreach (DS_SnowTri t : cell.m_Tris)
		{
			if (s_Instance.TriContains(t, x, z))
				return !DS_CoverMap.IsBare(x, z, cell.m_Stage, t.m_Variant);
		}
		return false;
	}

	protected bool TriContains(DS_SnowTri t, float x, float z)
	{
		float s = t.m_Size;
		float ax;
		float az;
		float bx;
		float bz;
		float cx;
		float cz;
		if (t.m_Free)
		{
			ax = t.m_X0;
			az = t.m_Z0;
			bx = t.m_X1;
			bz = t.m_Z1;
			cx = t.m_X2;
			cz = t.m_Z2;
		}
		else
			TriCorners(t.m_Shape, t.m_CX - s * 0.5, t.m_CZ - s * 0.5, s, ax, az, bx, bz, cx, cz);
		float d1 = (x - bx) * (az - bz) - (ax - bx) * (z - bz);
		float d2 = (x - cx) * (bz - cz) - (bx - cx) * (z - cz);
		float d3 = (x - ax) * (cz - az) - (cx - ax) * (z - az);
		bool negative = d1 < -0.0001 || d2 < -0.0001 || d3 < -0.0001;
		bool positive = d1 > 0.0001 || d2 > 0.0001 || d3 > 0.0001;
		return !(negative && positive);
	}


	//! the level the current layout draws a point at
	protected int DrawLevelAt(float x, float z)
	{
		for (int level = LEVELS - 1; level >= 1; level--)
		{
			float s = Size(level);
			int cx = Math.Floor(x / s);
			int cz = Math.Floor(z / s);
			if (Coarse(level, cx, cz))
				return level;
		}
		return 0;
	}

	//! test harness: the cells of the current layout that cover nothing, and why
	string DebugHoles(int maxList)
	{
		int missing = 0;
		int empty = 0;
		int unstaged = 0;
		int partial = 0;
		int built = 0;
		string list = "";
		string emptyList = "";
		int listed = 0;
		int emptyListed = 0;
		for (int w = 0; w < m_WLevel.Count(); w++)
		{
			int lv = m_WLevel[w];
			int x = m_WX[w];
			int z = m_WZ[w];
			float size = Size(lv);
			DS_SnowCell c = m_Cells[lv].Get(x * 65536 + z);
			string why = "";
			if (!c)
			{
				missing++;
				why = "missing";
			}
			else if (c.m_Tris.Count() == 0)
			{
				empty++;
				if (emptyListed < maxList)
				{
					emptyList += string.Format(" [L%1 %2 %3]", lv, (x + 0.5) * size, (z + 0.5) * size);
					emptyListed++;
				}
				continue;
			}
			else if (c.m_Stage <= 0)
			{
				unstaged++;
				why = "stage0";
			}
			else if (c.m_Objects.Count() < c.m_Tris.Count())
			{
				partial++;
				why = "partial";
			}
			else
				built++;
			if (why != "" && listed < maxList)
			{
				list += string.Format(" [L%1 %2 %3 %4]", lv, (x + 0.5) * size, (z + 0.5) * size, why);
				listed++;
			}
		}
		return string.Format("cells=%1 built=%2 missing=%3 empty=%4 stage0=%5 partial=%6 retired=%7 scan=%8 objects=%9", m_WLevel.Count(), built, missing, empty, unstaged, partial, m_Retired.Count(), m_Scan, m_Objects) + " problems:" + list + " empty:" + emptyList;
	}

	//! test harness: height of the built cover above the terrain at a point and the level drawn there (-1 = none)
	float DebugCoverAt(float x, float z, out int level)
	{
		level = DrawLevelAt(x, z);
		float s = Size(level);
		int cx = Math.Floor(x / s);
		int cz = Math.Floor(z / s);
		DS_SnowCell cell = m_Cells[level].Get(cx * 65536 + cz);
		if (!cell || cell.m_Stage <= 0)
		{
			level = -1;
			return 0;
		}
		foreach (DS_SnowTri t : cell.m_Tris)
		{
			if (TriContains(t, x, z))
				return t.m_YC + t.m_A * (x - t.m_CX) + t.m_B * (z - t.m_CZ) + t.m_Lift + m_ExtraOffset - g_Game.SurfaceY(x, z);
		}
		level = -1;
		return 0;
	}

	//! test harness: the state of the cell drawn at a point
	string DebugCellAt(float x, float z)
	{
		int level = DrawLevelAt(x, z);
		float s = Size(level);
		int cx = Math.Floor(x / s);
		int cz = Math.Floor(z / s);
		DS_SnowCell cell = m_Cells[level].Get(cx * 65536 + cz);
		bool infoWater = IsWater(x, z);
		float infoTerrain = g_Game.SurfaceY(x, z);
		string info = string.Format("level=%1 list=%2 water=%3 terrain=%4 pondMode=%5", level, m_ListCamera, infoWater, infoTerrain, m_PondMode);
		if (!cell)
			return info + " cell=none";
		int inList = 0;
		for (int w = 0; w < m_WLevel.Count(); w++)
		{
			if (m_WLevel[w] == level && m_WX[w] == cell.m_X && m_WZ[w] == cell.m_Z)
				inList++;
		}
		return info + string.Format(" cell=%1,%2 tris=%3 objects=%4 stage=%5 want=%6 avg=%7 sig=%8 inList=%9", cell.m_X, cell.m_Z, cell.m_Tris.Count(), cell.m_Objects.Count(), cell.m_Stage, DesiredStage(cell, DistXZ(x, z)), cell.m_Avg, cell.m_Sig, inList);
	}

	//! test harness: the placed objects of the level 0 cell at a point, with the world height of each triangle's
	//! corners as drawn (from the object's transform) next to the planned height
	string DebugObjectsAt(float x, float z)
	{
		int ix = Math.Floor(x / m_Cell);
		int iz = Math.Floor(z / m_Cell);
		DS_SnowCell cell = m_Cells[0].Get(ix * 65536 + iz);
		if (!cell)
			return "no cell";
		string s = string.Format("cell %1,%2 stage=%3 sig=%4:", ix, iz, cell.m_Stage, cell.m_Sig);
		for (int i = 0; i < cell.m_Tris.Count() && i < cell.m_Objects.Count(); i++)
		{
			DS_SnowTri t = cell.m_Tris[i];
			Object o = cell.m_Objects[i];
			if (!o)
				continue;
			float hs = t.m_Size * 0.5;
			float ax;
			float az;
			float bx;
			float bz;
			float cx;
			float cz;
			TriCorners(t.m_Shape, t.m_CX - hs, t.m_CZ - hs, t.m_Size, ax, az, bx, bz, cx, cz);
			vector centre = o.GetBoundingCenter();
			// model space corners: the triangle lies at the height the binarising shift left it at
			float ms = MODEL_CELL;
			if (t.m_K > 0)
				ms = t.m_Size / t.m_K;
			if (t.m_Free)
			{
				vector fa = o.ModelToWorld(Vector(-ms * 0.5, 0, -ms * 0.5) - centre);
				vector fb = o.ModelToWorld(Vector(ms * 0.5, 0, -ms * 0.5) - centre);
				vector fc = o.ModelToWorld(Vector(-ms * 0.5, 0, ms * 0.5) - centre);
				Print(string.Format("[DSTest] objtri cut %1 plan=%2,%3 %4,%5 %6,%7 drawn=%8 %9", t.m_Variant, t.m_X0, t.m_Z0, t.m_X1, t.m_Z1, t.m_X2, t.m_Z2, fa, fb.ToString() + " " + fc.ToString() + " terrain=" + g_Game.SurfaceY(t.m_X0, t.m_Z0).ToString()));
				continue;
			}
			vector wa = o.ModelToWorld(Vector((ax - t.m_CX) / t.m_Size * ms, -centre[1], (az - t.m_CZ) / t.m_Size * ms) - Vector(centre[0], 0, centre[2]));
			float pa = t.m_YC + t.m_A * (ax - t.m_CX) + t.m_B * (az - t.m_CZ) + t.m_Lift + m_ExtraOffset;
			Print(string.Format("[DSTest] objtri %1%2 size=%3 cornerA=%4 drawnY=%5 planY=%6 terrain=%7", ShapeName(t.m_Shape), t.m_Variant, t.m_Size, Vector(ax, 0, az), wa[1], pa, g_Game.SurfaceY(ax, az)));
		}
		return s + string.Format(" tris=%1 objects=%2", cell.m_Tris.Count(), cell.m_Objects.Count());
	}

	//! test harness: builds the level 0 cell at a point once more, printing every decision (nothing is placed)
	string DebugBuildCell(float x, float z)
	{
		int ix = Math.Floor(x / m_Cell);
		int iz = Math.Floor(z / m_Cell);
		s_DebugBuild = true;
		DS_SnowCell dbgCell = CreateCell(0, ix, iz);
		s_DebugBuild = false;
		return string.Format("cell %1,%2 tris=%3", ix, iz, dbgCell.m_Tris.Count());
	}

	//! test harness: every built triangle over a point, on all levels and in the retired cells of earlier layouts,
	//! with its height above the terrain there
	string DebugAllAt(float x, float z)
	{
		float ground = g_Game.SurfaceY(x, z);
		string s = "";
		for (int level = 0; level < LEVELS; level++)
		{
			float size = Size(level);
			int cx = Math.Floor(x / size);
			int cz = Math.Floor(z / size);
			DS_SnowCell cell = m_Cells[level].Get(cx * 65536 + cz);
			if (cell)
				s += DebugCellTris(cell, x, z, ground, "L" + level.ToString());
		}
		int retiredHere = 0;
		foreach (DS_SnowCell rc : m_Retired)
		{
			if (!rc)
				continue;
			string r = DebugCellTris(rc, x, z, ground, "R" + rc.m_Level.ToString());
			if (r != "")
			{
				s += r;
				retiredHere++;
			}
		}
		return string.Format("retired=%1 here=%2 drawLevel=%3:", m_Retired.Count(), retiredHere, DrawLevelAt(x, z)) + s;
	}

	protected string DebugCellTris(DS_SnowCell cell, float x, float z, float ground, string tag)
	{
		string s = "";
		foreach (DS_SnowTri t : cell.m_Tris)
		{
			if (!TriContains(t, x, z))
				continue;
			float h = t.m_YC + t.m_A * (x - t.m_CX) + t.m_B * (z - t.m_CZ) + t.m_Lift + m_ExtraOffset - ground;
			s += string.Format(" [%1 cell=%2,%3 stage=%4 objs=%5 tri=%6%7 above=%8]", tag, cell.m_X, cell.m_Z, cell.m_Stage, cell.m_Objects.Count(), ShapeName(t.m_Shape), t.m_Variant, h);
		}
		return s;
	}

	//! true when a terrain point lies inside a building: a large solid structure stands above it and the surface
	//! under its roof is an interior one (CfgSurfaces interior, as the game itself tells a fireplace indoors from
	//! one outdoors). Eaves, awnings, porches and open canopies have the terrain or an outdoor surface under them,
	//! so the snow runs up to the walls.
	protected bool ProbeBlocked(float x, float z)
	{
		m_Calls[3] = m_Calls[3] + 1;
		m_Cost += 0.05;
		float ground = g_Game.SurfaceY(x, z);
		vector from = Vector(x, ground + 40.0, z);
		vector to = Vector(x, ground + 0.05, z);
		vector hitPos;
		vector hitDir;
		int component;
		set<Object> hits = new set<Object>;
		if (!DayZPhysics.RaycastRV(from, to, hitPos, hitDir, component, hits, null, null, false, false, ObjIntersectView, 0.0))
			return false;

		// only a roof or ceiling well above the ground means "inside"; floors and low props keep their snow
		if (hitPos[1] - ground < 1.0)
			return false;

		Object building = null;
		for (int i = 0; i < hits.Count(); i++)
		{
			Object o = hits.Get(i);
			if (!o)
				continue;
			if (o.IsRock() || DS_Util.IsVegetation(o))
				continue;
			if (o.IsInherited(Man) || o.IsInherited(DayZCreature) || o.IsInherited(ItemBase) || o.IsInherited(Transport) || o.IsInherited(Camera))
				continue;
			vector minMax[2];
			o.ClippingInfo(minMax);
			vector size = minMax[1] - minMax[0];
			if (size[0] >= 3.0 && size[2] >= 3.0 && size[1] >= 2.0)
			{
				building = o;
				break;
			}
		}
		if (!building)
			return false;
		// a raised ground floor hides the snow under it: the cover runs under the building, its walls and foundation
		// hide the edge, and nothing has to be cut out
		string groundType;
		float groundFloor = g_Game.SurfaceGetType3D(x, ground + RAISED_PROBE, z, groundType);
		if (groundFloor - ground >= RAISED_FLOOR)
			return false;
		if (IsInteriorSurface(groundType))
			return true;
		string floorType;
		g_Game.SurfaceGetType3D(x, hitPos[1] - 0.1, z, floorType);
		if (IsInteriorSurface(floorType))
			return true;
		// sheds and barns standing on the bare ground: inside when walls close the point in on three sides or more
		if (Enclosed(x, z, ground, building))
			return true;
		return UnderWideRoof(x, z, building);
	}

	//! true when the roof of the building also covers the ground WIDE_ROOF metres away in all four directions of
	//! the building: snow does not get there (it does under eaves and narrow canopies)
	protected bool UnderWideRoof(float x, float z, Object building)
	{
		m_Calls[4] = m_Calls[4] + 1;
		vector axes[4];
		building.GetTransform(axes);
		vector ax = Vector(axes[0][0], 0, axes[0][2]).Normalized();
		vector az = Vector(axes[2][0], 0, axes[2][2]).Normalized();
		array<vector> offs = new array<vector>;
		offs.Insert(ax * WIDE_ROOF);
		offs.Insert(ax * (-1.0 * WIDE_ROOF));
		offs.Insert(az * WIDE_ROOF);
		offs.Insert(az * (-1.0 * WIDE_ROOF));
		foreach (vector off : offs)
		{
			if (!RoofOf(x + off[0], z + off[2], building))
				return false;
		}
		return true;
	}

	//! the building's roof lies more than a metre above the ground at a point
	protected bool RoofOf(float x, float z, Object building)
	{
		m_Calls[5] = m_Calls[5] + 1;
		m_Cost += 0.03;
		float ground = g_Game.SurfaceY(x, z);
		vector hitPos;
		vector hitDir;
		int component;
		set<Object> hits = new set<Object>;
		if (!DayZPhysics.RaycastRV(Vector(x, ground + 40.0, z), Vector(x, ground + 0.05, z), hitPos, hitDir, component, hits, null, null, false, false, ObjIntersectView, 0.0))
			return false;
		return hitPos[1] - ground >= 1.0 && hits.Find(building) >= 0;
	}

	//! true when walls of the building stand around a point on at least three of its four sides (within 12 m),
	//! looking along the building's own axes, so a point under the eaves of a turned building is not closed in
	protected bool Enclosed(float x, float z, float ground, Object building)
	{
		m_Calls[6] = m_Calls[6] + 1;
		m_Cost += 0.12;
		vector axes[4];
		building.GetTransform(axes);
		vector ax = Vector(axes[0][0], 0, axes[0][2]).Normalized();
		vector az = Vector(axes[2][0], 0, axes[2][2]).Normalized();
		array<vector> dirs = new array<vector>;
		dirs.Insert(ax);
		dirs.Insert(ax * -1.0);
		dirs.Insert(az);
		dirs.Insert(az * -1.0);
		vector from = Vector(x, ground + 1.0, z);
		int walls = 0;
		int open = 0;
		foreach (vector d : dirs)
		{
			vector hitPos;
			vector hitDir;
			int component;
			set<Object> hits = new set<Object>;
			bool hit = DayZPhysics.RaycastRV(from, from + d * 12.0, hitPos, hitDir, component, hits, null, null, false, false, ObjIntersectView, 0.0);
			if (hit && hits.Find(building) >= 0)
				walls++;
			else
				open++;
			if (open >= 2)
				return false;
		}
		return walls >= 3;
	}

	protected ref map<string, bool> m_Interior;

	protected bool IsInteriorSurface(string surface)
	{
		if (surface == "")
			return false;
		if (!m_Interior)
			m_Interior = new map<string, bool>;
		bool interior;
		if (m_Interior.Find(surface, interior))
			return interior;
		interior = g_Game.ConfigGetInt("CfgSurfaces " + surface + " interior") == 1;
		m_Interior.Set(surface, interior);
		return interior;
	}

	//! test harness: what the inside test sees at a point
	string DebugProbe(float x, float z)
	{
		float ground = g_Game.SurfaceY(x, z);
		vector hitPos;
		vector hitDir;
		int component;
		set<Object> hits = new set<Object>;
		bool hit = DayZPhysics.RaycastRV(Vector(x, ground + 40.0, z), Vector(x, ground + 0.05, z), hitPos, hitDir, component, hits, null, null, false, false, ObjIntersectView, 0.0);
		string names = "";
		for (int i = 0; i < hits.Count(); i++)
		{
			if (hits.Get(i))
				names += " " + hits.Get(i).GetShapeName();
		}
		string floorType;
		float floorY = g_Game.SurfaceGetType3D(x, hitPos[1] - 0.1, z, floorType);
		bool blocked = ProbeBlocked(x, z);
		string rays = "";
		array<vector> dbgDirs = {"1 0 0", "-1 0 0", "0 0 1", "0 0 -1"};
		foreach (vector dd : dbgDirs)
		{
			vector rFrom = Vector(x, ground + 1.0, z);
			vector rHit;
			vector rDir;
			int rComp;
			set<Object> rHits = new set<Object>;
			bool rOk = DayZPhysics.RaycastRV(rFrom, rFrom + dd * 12.0, rHit, rDir, rComp, rHits, null, null, false, false, ObjIntersectView, 0.0);
			string rName = "-";
			if (rOk && rHits.Count() > 0 && rHits.Get(0))
				rName = rHits.Get(0).GetType();
			if (rOk)
				rays += string.Format(" %1:%2@%3", dd, rName, vector.Distance(rFrom, rHit));
			else
				rays += string.Format(" %1:open", dd);
		}
		string gType;
		float gFloor = g_Game.SurfaceGetType3D(x, ground + RAISED_PROBE, z, gType);
		return string.Format("hit=%1 roof=%2 floorY=%3 floor=%4 groundFloor=%5 %6 blocked=%7 rays:%8", hit, hitPos[1] - ground, floorY - ground, floorType, gFloor - ground, gType, blocked, rays);
	}

	protected int BlockedProbes(float ax, float az, float bx, float bz, float cx, float cz, out bool centre)
	{
		float gx = (ax + bx + cx) / 3.0;
		float gz = (az + bz + cz) / 3.0;
		int n = 0;
		centre = ProbeBlocked(gx, gz);
		if (centre)
			n++;
		if (ProbeBlocked(gx + (ax - gx) * 0.8, gz + (az - gz) * 0.8))
			n++;
		if (ProbeBlocked(gx + (bx - gx) * 0.8, gz + (bz - gz) * 0.8))
			n++;
		if (ProbeBlocked(gx + (cx - gx) * 0.8, gz + (cz - gz) * 0.8))
			n++;
		return n;
	}

	//! whether a corner of the wall triangles lies inside a building. Cached: the corners of all subdivisions lie on
	//! the grid of eighth cells and are shared by up to eight triangles (buildings do not move)
	protected ref map<int, bool> m_CornerIn;

	protected bool CornerBlocked(float x, float z)
	{
		if (!m_CornerIn)
			m_CornerIn = new map<int, bool>;
		float q = m_Cell / 8.0;
		// whole numbers first: the key does not fit the precision of a float
		int qx = Math.Round(x / q);
		int qz = Math.Round(z / q);
		int key = qx * 65536 + qz;
		bool inside;
		if (m_CornerIn.Find(key, inside))
			return inside;
		if (m_CornerIn.Count() > 400000)
			m_CornerIn.Clear();
		inside = ProbeBlocked(x, z);
		m_CornerIn.Set(key, inside);
		return inside;
	}

	protected bool AnyCornerFree(float ax, float az, float bx, float bz, float cx, float cz)
	{
		return !CornerBlocked(ax, az) || !CornerBlocked(bx, bz) || !CornerBlocked(cx, cz);
	}

	//! where the snow ends on the edge from a point outside (f) to a point inside a building (b), found by halving
	//! the edge; it reaches just past the wall line, so the wall hides the cut
	protected vector WallCross(float fx, float fz, float bx, float bz)
	{
		float lo = 0;
		float hi = 1;
		for (int i = 0; i < CLIP_STEPS; i++)
		{
			float mid = (lo + hi) * 0.5;
			if (ProbeBlocked(fx + (bx - fx) * mid, fz + (bz - fz) * mid))
				hi = mid;
			else
				lo = mid;
		}
		return Vector(fx + (bx - fx) * hi, 0, fz + (bz - fz) * hi);
	}

	//! one piece of a triangle cut at a wall: corners in the order of the triangle it was cut from (front face up)
	protected void AddCut(DS_SnowCell cell, int shape, float x0, float z0, float s, float h00, float h10, float h11, float h01, vector p0, vector p1, vector p2)
	{
		float twice = (p1[0] - p0[0]) * (p2[2] - p0[2]) - (p1[2] - p0[2]) * (p2[0] - p0[0]);
		if (twice < 0.004)
			return; // a sliver
		DS_SnowTri t = MakeTri(shape, x0, z0, s, h00, h10, h11, h01);
		t.m_Free = true;
		t.m_X0 = p0[0];
		t.m_Z0 = p0[2];
		t.m_X1 = p1[0];
		t.m_Z1 = p1[2];
		t.m_X2 = p2[0];
		t.m_Z2 = p2[2];
		cell.m_Tris.Insert(t);
	}

	//! a smallest triangle at a wall: whole while at most one corner is inside (the wall hides the corner that
	//! reaches into it), cut along the wall when two corners are inside, so the snow still reaches the wall, and gone
	//! when it lies inside
	protected void BuildWallTri(DS_SnowCell cell, int shape, float x0, float z0, float s, float h00, float h10, float h11, float h01)
	{
		if (TriWater(shape, x0, z0, s))
			return;
		float ax;
		float az;
		float bx;
		float bz;
		float cx;
		float cz;
		TriCorners(shape, x0, z0, s, ax, az, bx, bz, cx, cz);
		if (DS_State.s_DebugOldWalls)
		{
			bool oldCentre;
			int oldBlocked = BlockedProbes(ax, az, bx, bz, cx, cz, oldCentre);
			if (!oldCentre && oldBlocked <= 1)
				cell.m_Tris.Insert(MakeTri(shape, x0, z0, s, h00, h10, h11, h01));
			return;
		}
		array<vector> v = new array<vector>;
		v.Insert(Vector(ax, 0, az));
		v.Insert(Vector(bx, 0, bz));
		v.Insert(Vector(cx, 0, cz));
		array<bool> k = new array<bool>;
		k.Insert(CornerBlocked(ax, az));
		k.Insert(CornerBlocked(bx, bz));
		k.Insert(CornerBlocked(cx, cz));
		int inside = 0;
		for (int i = 0; i < 3; i++)
		{
			if (k[i])
				inside++;
		}
		if (s_DebugBuild)
			Print(string.Format("[DSTest] build wall shape=%1 x0=%2 z0=%3 s=%4 corners=%5 %6 %7 inside=%8", shape, x0, z0, s, k[0], k[1], k[2], inside));
		if (inside <= 1)
		{
			cell.m_Tris.Insert(MakeTri(shape, x0, z0, s, h00, h10, h11, h01));
			return;
		}
		if (inside == 3)
			return;

		// the corner outside, then the two inside in the triangle's order
		int odd = 0;
		for (int j = 0; j < 3; j++)
		{
			if (!k[j])
				odd = j;
		}
		vector o = v[odd];
		vector n1 = v[(odd + 1) % 3];
		vector n2 = v[(odd + 2) % 3];
		vector q1 = WallCross(o[0], o[2], n1[0], n1[2]);
		vector q2 = WallCross(o[0], o[2], n2[0], n2[2]);
		AddCut(cell, shape, x0, z0, s, h00, h10, h11, h01, o, q1, q2);
	}

	protected DS_SnowTri MakeTri(int shape, float x0, float z0, float s, float h00, float h10, float h11, float h01)
	{
		DS_SnowTri t = new DS_SnowTri();
		t.m_Shape = shape;
		t.m_Size = s;
		t.m_CX = x0 + s * 0.5;
		t.m_CZ = z0 + s * 0.5;
		SetPlane(t, h00, h10, h11, h01);
		return t;
	}

	//! plane of a triangle through the corner heights of its square
	protected void SetPlane(DS_SnowTri t, float h00, float h10, float h11, float h01)
	{
		int shape = t.m_Shape;
		float s = t.m_Size;
		if (shape == 0)
		{
			t.m_A = (h10 - h00) / s;
			t.m_B = (h11 - h10) / s;
			t.m_YC = h00 + (t.m_A + t.m_B) * s * 0.5;
		}
		else if (shape == 1)
		{
			t.m_A = (h11 - h01) / s;
			t.m_B = (h01 - h00) / s;
			t.m_YC = h00 + (t.m_A + t.m_B) * s * 0.5;
		}
		else if (shape == 2)
		{
			t.m_A = (h10 - h00) / s;
			t.m_B = (h01 - h00) / s;
			t.m_YC = h00 + (t.m_A + t.m_B) * s * 0.5;
		}
		else
		{
			t.m_A = (h11 - h01) / s;
			t.m_B = (h11 - h10) / s;
			t.m_YC = h10 - t.m_A * s * 0.5 + t.m_B * s * 0.5;
		}
	}

	//! corner points of a triangle shape in a (sub)cell, for probing / water tests
	protected void TriCorners(int shape, float x0, float z0, float s, out float ax, out float az, out float bx, out float bz, out float cx, out float cz)
	{
		float x1 = x0 + s;
		float z1 = z0 + s;
		if (shape == 0)
		{
			ax = x0; az = z0; bx = x1; bz = z0; cx = x1; cz = z1;
		}
		else if (shape == 1)
		{
			ax = x0; az = z0; bx = x1; bz = z1; cx = x0; cz = z1;
		}
		else if (shape == 2)
		{
			ax = x0; az = z0; bx = x1; bz = z0; cx = x0; cz = z1;
		}
		else
		{
			ax = x1; az = z0; bx = x1; bz = z1; cx = x0; cz = z1;
		}
	}


	//! true when water lies under a triangle: its corners and centre, and on large triangles its edge midpoints
	protected bool TriWater(int shape, float x0, float z0, float s)
	{
		float ax;
		float az;
		float bx;
		float bz;
		float cx;
		float cz;
		TriCorners(shape, x0, z0, s, ax, az, bx, bz, cx, cz);
		m_Cost += 0.04;
		if (IsWater(ax, az) || IsWater(bx, bz) || IsWater(cx, cz) || IsWater((ax + bx + cx) / 3.0, (az + bz + cz) / 3.0))
			return true;
		if (s < 20.0)
			return false;
		m_Cost += 0.03;
		return IsWater((ax + bx) * 0.5, (az + bz) * 0.5) || IsWater((bx + cx) * 0.5, (bz + cz) * 0.5) || IsWater((cx + ax) * 0.5, (cz + az) * 0.5);
	}

	//! level 0: exact triangles, refined around buildings down to an eighth of a cell (about a metre); those are cut
	//! along the walls, so the snow follows a wall in a straight line instead of in steps
	protected void BuildExact(DS_SnowCell cell, float x0, float z0, float s, bool diag, int depth)
	{
		m_Cost += 0.05;
		float h00 = H0(x0, z0);
		float h10 = H0(x0 + s, z0);
		float h11 = H0(x0 + s, z0 + s);
		float h01 = H0(x0, z0 + s);

		float hmin = Math.Min(Math.Min(h00, h10), Math.Min(h11, h01));
		float hmax = Math.Max(Math.Max(h00, h10), Math.Max(h11, h01));
		if (s_DebugBuild)
			Print(string.Format("[DSTest] build square x0=%1 z0=%2 s=%3 depth=%4 h=%5 %6 %7 %8 terrain=%9", x0, z0, s, depth, h00, h10, h11, h01, GY(x0, z0)));
		if (hmax - hmin > s * 1.3)
			return; // cliff

		int shapeA = 2;
		int shapeB = 3;
		if (diag)
		{
			shapeA = 0;
			shapeB = 1;
		}

		if (depth >= EXACT_DEPTH)
		{
			BuildWallTri(cell, shapeA, x0, z0, s, h00, h10, h11, h01);
			BuildWallTri(cell, shapeB, x0, z0, s, h00, h10, h11, h01);
			return;
		}

		bool subdivide = false;
		bool addA = false;
		bool addB = false;
		float ax;
		float az;
		float bx;
		float bz;
		float cx;
		float cz;
		bool centreA;
		bool centreB;

		if (!TriWater(shapeA, x0, z0, s))
		{
			TriCorners(shapeA, x0, z0, s, ax, az, bx, bz, cx, cz);
			int blockedA = BlockedProbes(ax, az, bx, bz, cx, cz, centreA);
			if (blockedA == 0)
				addA = true;
			else if (blockedA < 4 || (!DS_State.s_DebugOldWalls && AnyCornerFree(ax, az, bx, bz, cx, cz)))
				subdivide = true; // the wall runs through it (a corner sticking out of a building counts too)
		}
		if (!TriWater(shapeB, x0, z0, s))
		{
			TriCorners(shapeB, x0, z0, s, ax, az, bx, bz, cx, cz);
			int blockedB = BlockedProbes(ax, az, bx, bz, cx, cz, centreB);
			if (blockedB == 0)
				addB = true;
			else if (blockedB < 4 || (!DS_State.s_DebugOldWalls && AnyCornerFree(ax, az, bx, bz, cx, cz)))
				subdivide = true;
		}

		if (subdivide)
		{
			if (s_DebugBuild)
				Print(string.Format("[DSTest] build split x0=%1 z0=%2 s=%3 addA=%4 addB=%5", x0, z0, s, addA, addB));
			float hs = s * 0.5;
			BuildExact(cell, x0, z0, hs, diag, depth + 1);
			BuildExact(cell, x0 + hs, z0, hs, diag, depth + 1);
			BuildExact(cell, x0, z0 + hs, hs, diag, depth + 1);
			BuildExact(cell, x0 + hs, z0 + hs, hs, diag, depth + 1);
			return;
		}

		if (addA)
			cell.m_Tris.Insert(MakeTri(shapeA, x0, z0, s, h00, h10, h11, h01));
		if (addB)
			cell.m_Tris.Insert(MakeTri(shapeB, x0, z0, s, h00, h10, h11, h01));
		if (s_DebugBuild)
			Print(string.Format("[DSTest] build keep x0=%1 z0=%2 s=%3 addA=%4 addB=%5", x0, z0, s, addA, addB));
	}

	//! height of the two-triangle approximation of a square at relative position (u, v) in 0..1
	protected float PlaneAt(bool diag, float u, float v, float h00, float h10, float h11, float h01)
	{
		if (diag)
		{
			if (u >= v)
				return h00 + (h10 - h00) * u + (h11 - h10) * v;
			return h00 + (h11 - h01) * u + (h01 - h00) * v;
		}
		if (u + v <= 1.0)
			return h00 + (h10 - h00) * u + (h01 - h00) * v;
		return h11 + (h11 - h01) * (u - 1.0) + (h11 - h10) * (v - 1.0);
	}


	//! largest rise of the real terrain (and the roads on it) above the approximation; the terrain is linear
	//! between its grid vertices, so checking the vertices inside the square is exact (the largest cells look at
	//! every second vertex)
	protected float MaxRise(float x0, float z0, float s, bool diag, float h00, float h10, float h11, float h01)
	{
		int n = Math.Round(s / m_Cell);
		if (n < 2)
			return 0;
		// roads are narrower than the terrain grid: the smaller cells look at them twice as closely
		int m = n;
		if (n <= 4)
			m = n * 2;
		if (m > 16)
			m = 16;
		float rise = 0;
		for (int i = 0; i <= m; i++)
		{
			for (int j = 0; j <= m; j++)
			{
				float u = i / (m * 1.0);
				float v = j / (m * 1.0);
				float h = GY(x0 + s * u, z0 + s * v);
				float road = RoadAboveGround(x0 + s * u, z0 + s * v, h);
				float plane = PlaneAt(diag, u, v, h00, h10, h11, h01);
				float d = h + road - plane;
				if (d > rise)
					rise = d;
			}
		}
		m_Cost += 0.004 * (m + 1) * (m + 1);
		return rise;
	}

	protected bool CoarseDiag(float x0, float z0, float s, float h00, float h10, float h11, float h01)
	{
		float hc = GY(x0 + s * 0.5, z0 + s * 0.5);
		return Math.AbsFloat(hc - (h00 + h11) * 0.5) <= Math.AbsFloat(hc - (h10 + h01) * 0.5);
	}


	//! how far the terrain rises above the two triangles of a coarse cell (cached)
	protected float CellRise(int level, int cx, int cz)
	{
		map<int, float> cache = m_Rise[level];
		int key = cx * 65536 + cz;
		float rise;
		if (cache.Find(key, rise))
			return rise;
		float s = Size(level);
		float x0 = cx * s;
		float z0 = cz * s;
		float h00 = GY(x0, z0);
		float h10 = GY(x0 + s, z0);
		float h11 = GY(x0 + s, z0 + s);
		float h01 = GY(x0, z0 + s);
		bool diag = CoarseDiag(x0, z0, s, h00, h10, h11, h01);
		rise = MaxRise(x0, z0, s, diag, h00, h10, h11, h01);
		cache.Set(key, rise);
		return rise;
	}

	//! lift of a coarse grid vertex: the largest rise of the four cells sharing it. Lifting every corner of a
	//! cell by at least its rise keeps the whole cell above the terrain, and neighbours share the corner heights,
	//! so no terrain shows through and no cracks open between cells.
	protected float VertexLift(int level, int vx, int vz)
	{
		map<int, float> cache = m_Lift[level];
		int key = vx * 65536 + vz;
		float lift;
		if (cache.Find(key, lift))
			return lift;
		float r0 = CellRise(level, vx - 1, vz - 1);
		float r1 = CellRise(level, vx, vz - 1);
		float r2 = CellRise(level, vx - 1, vz);
		float r3 = CellRise(level, vx, vz);
		lift = Math.Max(Math.Max(r0, r1), Math.Max(r2, r3));
		if (lift > m_Cap[level])
			lift = m_Cap[level];
		cache.Set(key, lift);
		return lift;
	}

	//! corner height of a cell of level 1 or up (vertex coordinates in cells of that level): the lifted terrain, or
	//! exactly on the edge of a neighbouring coarser cell, so both levels meet without a step
	protected float HL(int level, int vx, int vz)
	{
		if (level < LEVELS - 1)
		{
			int r = Ratio(level);
			int up = level + 1;
			int px = Math.Floor(vx / (r * 1.0));
			int pz = Math.Floor(vz / (r * 1.0));
			int mx = vx - px * r;
			int mz = vz - pz * r;
			if (mx == 0 && mz == 0)
			{
				if (Coarse(up, px - 1, pz - 1) || Coarse(up, px, pz - 1) || Coarse(up, px - 1, pz) || Coarse(up, px, pz))
					return HL(up, px, pz);
			}
			else if (mx == 0)
			{
				if (Coarse(up, px - 1, pz) || Coarse(up, px, pz))
				{
					float za = HL(up, px, pz);
					float zb = HL(up, px, pz + 1);
					return za + (zb - za) * (mz / (r * 1.0));
				}
			}
			else if (mz == 0)
			{
				if (Coarse(up, px, pz - 1) || Coarse(up, px, pz))
				{
					float xa = HL(up, px, pz);
					float xb = HL(up, px + 1, pz);
					return xa + (xb - xa) * (mx / (r * 1.0));
				}
			}
		}
		// call results go into locals first: in "native() + scriptFunction()" the engine can lose the native result
		// when the script function calls the same native again
		float s = Size(level);
		float lift = VertexLift(level, vx, vz);
		float ground = GY(vx * s, vz * s);
		return ground + lift + m_Off[level];
	}

	//! vertex height of the level 0 cover: the exact terrain (and roads), or exactly on the edge of a neighbouring
	//! level 1 cell, so both levels meet without a step
	protected float H0(float x, float z)
	{
		float c1 = Size(1);
		float fx = x / c1;
		float fz = z / c1;
		int lx = Math.Round(fx);
		int lz = Math.Round(fz);
		bool onX = Math.AbsFloat(fx - lx) < 0.0005;
		bool onZ = Math.AbsFloat(fz - lz) < 0.0005;
		if (onX && onZ)
		{
			if (Coarse(1, lx - 1, lz - 1) || Coarse(1, lx, lz - 1) || Coarse(1, lx - 1, lz) || Coarse(1, lx, lz))
				return HL(1, lx, lz);
		}
		else if (onX)
		{
			int bz = Math.Floor(fz);
			if (Coarse(1, lx - 1, bz) || Coarse(1, lx, bz))
			{
				float za = HL(1, lx, bz);
				float zb = HL(1, lx, bz + 1);
				return za + (zb - za) * (fz - bz);
			}
		}
		else if (onZ)
		{
			int bx = Math.Floor(fx);
			if (Coarse(1, bx, lz - 1) || Coarse(1, bx, lz))
			{
				float xa = HL(1, bx, lz);
				float xb = HL(1, bx + 1, lz);
				return xa + (xb - xa) * (fx - bx);
			}
		}
		float ground = GY(x, z);
		float road = RoadLift0(x, z);
		return ground + road + OFF0;
	}

	//! which neighbouring coarser cells a cell touches; its edge heights come from those cells
	protected int BorderSignature(int level, int x, int z)
	{
		int r = Ratio(level);
		int up = level + 1;
		int px = Math.Floor(x / (r * 1.0));
		int pz = Math.Floor(z / (r * 1.0));
		int ux = x - px * r;
		int uz = z - pz * r;
		int sig = 0;
		// a cell built ahead inside a coarser cell (hidden under it) takes that cell's edge heights
		if (Coarse(up, px, pz))
			sig = 512;
		if (ux != 0 && ux != r - 1 && uz != 0 && uz != r - 1)
			return sig;
		int bit = 1;
		for (int ddx = -1; ddx <= 1; ddx++)
		{
			for (int ddz = -1; ddz <= 1; ddz++)
			{
				if (ddx == 0 && ddz == 0)
					continue;
				bool touchX = ddx == 0 || (ddx < 0 && ux == 0) || (ddx > 0 && ux == r - 1);
				bool touchZ = ddz == 0 || (ddz < 0 && uz == 0) || (ddz > 0 && uz == r - 1);
				if (touchX && touchZ && Coarse(up, px + ddx, pz + ddz))
					sig = sig | bit;
				bit = bit * 2;
			}
		}
		return sig;
	}

	//! coarse levels: two triangles over a large cell, corners lifted so the terrain stays underneath
	protected void BuildCoarse(DS_SnowCell cell, int level, int cx, int cz, float s)
	{
		m_Cost += 0.05;
		float x0 = cx * s;
		float z0 = cz * s;
		float g00 = GY(x0, z0);
		float g10 = GY(x0 + s, z0);
		float g11 = GY(x0 + s, z0 + s);
		float g01 = GY(x0, z0 + s);
		bool diag = CoarseDiag(x0, z0, s, g00, g10, g11, g01);
		float h00 = HL(level, cx, cz);
		float h10 = HL(level, cx + 1, cz);
		float h11 = HL(level, cx + 1, cz + 1);
		float h01 = HL(level, cx, cz + 1);

		int shapeA = 2;
		int shapeB = 3;
		if (diag)
		{
			shapeA = 0;
			shapeB = 1;
		}
		if (!TriWater(shapeA, x0, z0, s))
			cell.m_Tris.Insert(MakeTri(shapeA, x0, z0, s, h00, h10, h11, h01));
		if (!TriWater(shapeB, x0, z0, s))
			cell.m_Tris.Insert(MakeTri(shapeB, x0, z0, s, h00, h10, h11, h01));
	}

	protected DS_SnowCell CreateCell(int level, int x, int z)
	{
		DS_SnowCell cell = new DS_SnowCell();
		cell.m_Level = level;
		cell.m_X = x;
		cell.m_Z = z;
		cell.m_BuildGen = m_BuildGen;
		float size = Size(level);
		float x0 = x * size;
		float z0 = z * size;
		float avgA = GY(x0 + size * 0.5, z0 + size * 0.5);
		float avgB = GY(x0, z0);
		cell.m_Avg = (avgA + avgB) * 0.5;

		if (level == 0)
		{
			// the diagonal of the terrain's own triangles, also where the cover lies on pond ice: with the ice height
			// on some corners and the bank on others, the other diagonal leaves the terrain's crease poking through
			float h00 = g_Game.SurfaceY(x0, z0);
			float h11 = g_Game.SurfaceY(x0 + size, z0 + size);
			float h10 = g_Game.SurfaceY(x0 + size, z0);
			float h01 = g_Game.SurfaceY(x0, z0 + size);
			float hc = g_Game.SurfaceY(x0 + size * 0.5, z0 + size * 0.5);
			bool diag = Math.AbsFloat(hc - (h00 + h11) * 0.5) <= Math.AbsFloat(hc - (h10 + h01) * 0.5);
			BuildExact(cell, x0, z0, size, diag, 0);
		}
		else
			BuildCoarse(cell, level, x, z, size);
		foreach (DS_SnowTri t : cell.m_Tris)
			SetVariant(t, level);
		return cell;
	}

	protected int Wrap(int v, int n)
	{
		int r = v % n;
		if (r < 0)
			r += n;
		return r;
	}


	//! picks the model of the triangle's size and place in the 30 m texture period
	protected void SetVariant(DS_SnowTri t, int level)
	{
		float s = t.m_Size;
		int f = m_F[level];
		float modelSize = MODEL_CELL * f;
		int ix = Math.Round((t.m_CX - s * 0.5) / s);
		int iz = Math.Round((t.m_CZ - s * 0.5) / s);
		if (level == 0)
		{
			if (s > m_Cell * 0.75)
			{
				modelSize = MODEL_CELL;
				t.m_Variant = Wrap(ix, 4).ToString() + Wrap(iz, 4).ToString();
			}
			else if (s > m_Cell * 0.375)
			{
				modelSize = MODEL_CELL * 0.5;
				t.m_Variant = "h" + Wrap(ix, 8).ToString() + Wrap(iz, 8).ToString();
			}
			else
			{
				modelSize = MODEL_CELL * 0.25;
				t.m_Variant = "q" + Wrap(ix, 4).ToString() + Wrap(iz, 4).ToString();
			}
		}
		else if (f == 2)
			t.m_Variant = "d" + Wrap(ix, 2).ToString() + Wrap(iz, 2).ToString();
		else
			t.m_Variant = "f" + f.ToString();
		t.m_K = s / modelSize;
	}

	//! new corner heights for a cell whose coarser neighbours changed: the triangles stay, only their planes move
	protected void Restitch(DS_SnowCell cell, int sig)
	{
		cell.m_Sig = sig;
		foreach (DS_SnowTri t : cell.m_Tris)
		{
			float s = t.m_Size;
			float x0 = t.m_CX - s * 0.5;
			float z0 = t.m_CZ - s * 0.5;
			float h00;
			float h10;
			float h11;
			float h01;
			if (cell.m_Level == 0)
			{
				h00 = H0(x0, z0);
				h10 = H0(x0 + s, z0);
				h11 = H0(x0 + s, z0 + s);
				h01 = H0(x0, z0 + s);
			}
			else
			{
				h00 = HL(cell.m_Level, cell.m_X, cell.m_Z);
				h10 = HL(cell.m_Level, cell.m_X + 1, cell.m_Z);
				h11 = HL(cell.m_Level, cell.m_X + 1, cell.m_Z + 1);
				h01 = HL(cell.m_Level, cell.m_X, cell.m_Z + 1);
			}
			SetPlane(t, h00, h10, h11, h01);
		}
		m_Cost += 0.02 + 0.01 * cell.m_Tris.Count();
		if (cell.m_Stage > 0)
			Retransform(cell);
	}

	protected int DesiredStage(DS_SnowCell cell, float dist)
	{
		if (cell.m_Tris.Count() == 0)
			return 0;

		float depth = DS_State.SnowAt(cell.m_Avg, m_S0, m_S1, m_S2);
		int stage = 0;
		if (depth >= 10.0)
			stage = 4;
		else if (depth >= 5.0)
			stage = 3;
		else if (depth >= 2.0)
			stage = 2;
		else if (depth >= 0.5)
			stage = 1;

		float outer = m_Rad[LEVELS - 1];
		float fadeStart = outer * 0.85;
		if (stage > 0 && dist > fadeStart)
		{
			float f = 1.0 - (dist - fadeStart) / (outer - fadeStart);
			int cap = Math.Ceil(f * 4.0);
			if (cap < 1)
				cap = 1;
			if (stage > cap)
				stage = cap;
		}
		return stage;
	}

	//! only test harness changes (lighting normal, extra height) move placed triangles: the heights themselves never
	//! depend on the camera
	protected bool NeedsReplace(DS_SnowCell cell)
	{
		return cell.m_Epoch != m_Epoch;
	}

	protected void DeleteObjects(DS_SnowCell cell)
	{
		foreach (Object o : cell.m_Objects)
		{
			if (o)
			{
				g_Game.ObjectDelete(o);
				m_Objects--;
			}
		}
		cell.m_Objects.Clear();
	}

	//! places a triangle model on its plane
	protected void SetTriTransform(Object o, DS_SnowTri t)
	{
		float s = t.m_Size;
		float k = t.m_K;
		float slopeA = t.m_A;
		float slopeB = t.m_B;
		vector mat[4];
		mat[0] = Vector(k, slopeA * k, 0);
		mat[1] = Vector(-slopeA, 1, -slopeB).Normalized();
		if (m_NormalMode == 1)
			mat[1] = "0 1 0";
		else if (m_NormalMode == 2)
		{
			float ax;
			float az;
			float bx;
			float bz;
			float cx;
			float cz;
			TriCorners(t.m_Shape, t.m_CX - s * 0.5, t.m_CZ - s * 0.5, s, ax, az, bx, bz, cx, cz);
			mat[1] = SmoothNormal(ax, az, bx, bz, cx, cz, Math.Max(s, m_Cell));
		}
		mat[2] = Vector(0, slopeB * k, k);
		vector origin = Vector(t.m_CX, t.m_YC, t.m_CZ);
		if (t.m_Free)
		{
			// cut at a wall: the corners of the c model (its right angle first) go onto the three corners, on the
			// plane of the triangle it was cut from
			float size = s / k;
			float e1x = (t.m_X1 - t.m_X0) / size;
			float e1z = (t.m_Z1 - t.m_Z0) / size;
			float e2x = (t.m_X2 - t.m_X0) / size;
			float e2z = (t.m_Z2 - t.m_Z0) / size;
			mat[0] = Vector(e1x, slopeA * e1x + slopeB * e1z, e1z);
			mat[2] = Vector(e2x, slopeA * e2x + slopeB * e2z, e2z);
			float ox = t.m_X0 + (e1x + e2x) * size * 0.5;
			float oz = t.m_Z0 + (e1z + e2z) * size * 0.5;
			origin = Vector(ox, t.m_YC + slopeA * (ox - t.m_CX) + slopeB * (oz - t.m_CZ), oz);
		}
		// the binarised model is centred on its bounding box (the skirt below the triangle moves the triangle up
		// by half the skirt depth); shifting back by the same offset puts the triangle on its plane
		vector centre = o.GetBoundingCenter();
		mat[3] = origin + Vector(0, t.m_Lift + m_ExtraOffset, 0) + mat[0] * centre[0] + mat[1] * centre[1] + mat[2] * centre[2];
		o.SetTransform(mat);
	}

	//! terrain normal averaged over the three corners, each from central differences over the given distance
	protected vector SmoothNormal(float ax, float az, float bx, float bz, float cx, float cz, float step)
	{
		vector n = CornerNormal(ax, az, step) + CornerNormal(bx, bz, step) + CornerNormal(cx, cz, step);
		return n.Normalized();
	}

	protected vector CornerNormal(float x, float z, float step)
	{
		float hx0 = GY(x - step, z);
		float hx1 = GY(x + step, z);
		float hz0 = GY(x, z - step);
		float hz1 = GY(x, z + step);
		vector n = Vector(-(hx1 - hx0) / (2.0 * step), 1.0, -(hz1 - hz0) / (2.0 * step));
		return n.Normalized();
	}

	protected string ShapeName(int shape)
	{
		if (shape == 0)
			return "a";
		if (shape == 1)
			return "b";
		if (shape == 2)
			return "c";
		return "d";
	}

	protected void ApplyStage(DS_SnowCell cell, int stage, float dist)
	{
		DeleteObjects(cell);
		cell.m_Stage = stage;
		if (stage <= 0)
			return;

		cell.m_Epoch = m_Epoch;
		string suffix = "_s" + stage.ToString() + ".p3d";
		foreach (DS_SnowTri t : cell.m_Tris)
		{
			string shapeName = ShapeName(t.m_Shape);
			if (t.m_Free)
				shapeName = "c";
			string p3d = DS_Const.DATA + "snow\\dsk_" + shapeName + t.m_Variant + suffix;
			Object o = g_Game.CreateStaticObjectUsingP3D(p3d, Vector(t.m_CX, t.m_YC, t.m_CZ), "0 0 0", 1.0, true);
			if (!o)
				continue;
			SetTriTransform(o, t);
			cell.m_Objects.Insert(o);
			m_Objects++;
			m_Cost += 0.25;
		}

	}

	protected void Retransform(DS_SnowCell cell)
	{
		cell.m_Epoch = m_Epoch;
		for (int i = 0; i < cell.m_Objects.Count() && i < cell.m_Tris.Count(); i++)
		{
			if (cell.m_Objects[i])
				SetTriTransform(cell.m_Objects[i], cell.m_Tris[i]);
		}
		m_Cost += 0.01 * cell.m_Objects.Count();
	}


	//! true when the area of a cell of an earlier layout is covered by built cells of the current layout (or lies
	//! outside it), so the old cell can go without opening a hole or overlapping its replacement
	protected bool Covered(DS_SnowCell c)
	{
		return RegionBuilt(c.m_Level, c.m_X, c.m_Z);
	}

	protected bool RegionBuilt(int level, int x, int z)
	{
		int top = LEVELS - 1;
		// outside the layout nothing has to be built
		int f = m_F[top] / m_F[level];
		int kx = Math.Floor(x / (f * 1.0));
		int kz = Math.Floor(z / (f * 1.0));
		if (kx < 0 || kz < 0)
			return true;
		float ct = Size(top);
		float dx = (kx + 0.5) * ct - m_ListCamera[0];
		float dz = (kz + 0.5) * ct - m_ListCamera[2];
		if (Math.Sqrt(dx * dx + dz * dz) > m_Rad[top])
			return true;
		// the level the current layout draws the area at, from the coarsest down
		for (int up = top; up >= level && up >= 1; up--)
		{
			int g = m_F[up] / m_F[level];
			int ux = Math.Floor(x / (g * 1.0));
			int uz = Math.Floor(z / (g * 1.0));
			if (Coarse(up, ux, uz))
				return m_Cells[up].Contains(ux * 65536 + uz);
		}
		if (level == 0)
			return m_Cells[0].Contains(x * 65536 + z);
		// the area is split into finer cells
		int r = Ratio(level - 1);
		for (int a = 0; a < r; a++)
		{
			for (int b = 0; b < r; b++)
			{
				if (!RegionBuilt(level - 1, x * r + a, z * r + b))
					return false;
			}
		}
		return true;
	}

	//! removes the cells of earlier layouts as soon as their replacements stand, all of them after a complete pass
	//! over the current layout, and the oldest ones when travelling fast keeps the layout from completing
	protected void DropRetired(bool all)
	{
		if (all)
		{
			// a complete pass over the layout: every retired cell may go now, spread over the next frames
			foreach (DS_SnowCell expired : m_Retired)
			{
				if (expired)
					expired.m_RetiredAt = m_Clock - RETIRE_SECONDS - 1.0;
			}
			return;
		}
		int dropTicks = MsTicks(DROP_MS);
		int drop0 = TickCount(0);
		int dropped = 0;
		int checks = 0;
		int n = m_Retired.Count();
		if (m_RetiredCursor >= n)
			m_RetiredCursor = 0;
		for (int step = 0; step < n && checks < 400; step++)
		{
			// deleting objects is slow in a busy scene: a few hundred per frame at most, fewer when they are slow
			if (dropped >= 400 || (dropTicks > 0 && dropped > 0 && TickCount(drop0) > dropTicks))
				break;
			int i = m_RetiredCursor;
			if (i >= m_Retired.Count())
			{
				i = 0;
				m_RetiredCursor = 0;
			}
			if (m_Retired.Count() == 0)
				break;
			DS_SnowCell c = m_Retired[i];
			checks++;
			if (!c || m_Clock - c.m_RetiredAt > RETIRE_SECONDS || Covered(c))
			{
				if (c)
				{
					dropped += c.m_Objects.Count();
					DeleteObjects(c);
				}
				m_Retired.RemoveOrdered(i);
				continue;
			}
			m_RetiredCursor = i + 1;
		}
		// travelling fast keeps the layout from completing: then the oldest go, with four times the time
		while (m_Retired.Count() > RETIRE_MAX && (dropTicks <= 0 || TickCount(drop0) < dropTicks * 4))
		{
			DS_SnowCell old = m_Retired[0];
			if (old)
				DeleteObjects(old);
			m_Retired.RemoveOrdered(0);
		}
	}


	void Update(float timeslice, vector camera, float s0, float s1, float s2)
	{
		if (!m_Ready)
			return;

		m_S0 = s0;
		m_S1 = s1;
		m_S2 = s2;
		if (timeslice > 0.0001 && m_Clock > 0)
		{
			float moved = vector.Distance(camera, m_PrevCamera) / timeslice;
			// teleports and respawns are not travel
			if (moved > 150.0)
				moved = 0;
			m_Speed += (moved - m_Speed) * Math.Min(1.0, timeslice * 2.0);
		}
		m_PrevCamera = camera;
		m_Camera = camera;
		m_Clock += timeslice;
		if (DS_State.s_DebugNoCarpet)
		{
			if (m_Objects > 0 || m_Cells[0].Count() > 0)
				Clear();
			m_AnchorX = -1000000;
			return;
		}
		if (DS_State.s_DebugExtraOffset != m_ExtraOffset || DS_State.s_DebugNormalMode != m_NormalMode)
		{
			// test harness: re-place every cell with the new height or lighting normal
			m_ExtraOffset = DS_State.s_DebugExtraOffset;
			m_NormalMode = DS_State.s_DebugNormalMode;
			m_Epoch++;
		}
		bool anySnow = Math.Max(s0, Math.Max(s1, s2)) >= 0.5;

		int pondMode = WantedPondMode();
		if (pondMode != m_PondMode)
		{
			// frozen ponds started or stopped carrying snow: every cell is rebuilt in place, nearest first
			m_PondMode = pondMode;
			m_BuildGen++;
			for (int lv = 1; lv < LEVELS; lv++)
			{
				m_Rise[lv].Clear();
				m_Lift[lv].Clear();
			}
			m_Road0.Clear();
			m_Diag0.Clear();
			m_NearScan = 0;
			Print(string.Format("[DynamicSeasons] snow cover: frozen ponds carrying snow (bits 0m/250m/500m) = %1", m_PondMode));
		}

		// test harness: another road rule rebuilds every cell in place
		float roadProbe = ROAD_PROBE;
		if (DS_State.s_DebugRoadProbe > 0)
			roadProbe = DS_State.s_DebugRoadProbe;
		bool roadWide = DS_State.s_DebugRoadWide != 0;
		if (roadProbe != m_RoadProbe || roadWide != m_RoadWide)
		{
			m_RoadProbe = roadProbe;
			m_RoadWide = roadWide;
			m_BuildGen++;
			for (int rlv = 1; rlv < LEVELS; rlv++)
			{
				m_Rise[rlv].Clear();
				m_Lift[rlv].Clear();
			}
			m_Road0.Clear();
			m_Diag0.Clear();
			m_NearScan = 0;
			Print(string.Format("[DynamicSeasons] snow cover: road rule probe=%1 wide=%2", m_RoadProbe, m_RoadWide));
		}

		// the layout follows the camera in steps of four terrain cells
		float step = m_Cell * 4.0;
		int anchorX = Math.Floor(camera[0] / step);
		int anchorZ = Math.Floor(camera[2] / step);
		if (!DS_State.s_StatCoverMax)
		{
			DS_State.s_StatCoverMax = new array<int>;
			for (int sc = 0; sc < 7; sc++)
				DS_State.s_StatCoverMax.Insert(0);
		}
		int tick = TickCount(0);
		if (anchorX != m_AnchorX || anchorZ != m_AnchorZ)
		{
			m_AnchorX = anchorX;
			m_AnchorZ = anchorZ;
			RebuildWorkList();
		}
		tick = StatCover(0, tick);

		m_Cost = 0;
		// on foot the normal budget keeps up easily; a fast car gets up to three times as much work per frame
		float boost = Math.Clamp(1.0 + m_Speed / 15.0, 1.0, 3.0);
		// creating and deleting objects gets slower with every object in the scene: the work also stops at a time
		// limit, so a dense town or a fast car never stalls a frame
		int buildTicks = MsTicks(BUILD_MS * boost);
		int build0 = tick;
		int count = m_WLevel.Count();
		int nearDone = 0;
		// first the blocks around the camera, which change with every layout
		while (m_NearScan < m_NearEnd && m_NearScan < count && m_Cost < 3.5 * boost)
		{
			if (buildTicks > 0 && nearDone > 0 && TickCount(build0) > buildTicks)
				break;
			int itemTick = TickCount(0);
			ProcessItem(m_NearScan, anySnow);
			StatCover(4, itemTick);
			m_NearScan++;
			nearDone++;
		}
		tick = StatCover(1, tick);
		// then the main cursor, which keeps cycling through the whole layout
		int visited = 0;
		while (m_Cost < 6.0 * boost && visited < count)
		{
			if (buildTicks > 0 && TickCount(build0) > buildTicks)
				break;
			if (m_Scan >= count)
			{
				m_Scan = 0;
				// a full pass over one layout: every cell of it exists now, the earlier layouts can go
				if (m_PassLayout == m_Layout && m_Retired.Count() > 0)
					DropRetired(true);
				m_PassLayout = m_Layout;
			}
			int mainTick = TickCount(0);
			ProcessItem(m_Scan, anySnow);
			StatCover(4, mainTick);
			m_Scan++;
			visited++;
		}
		tick = StatCover(2, tick);
		if (m_Retired.Count() > 0)
			DropRetired(false);
		StatCover(3, tick);
	}

	//! a time in CPU ticks (0 while the tick length is still unknown)
	protected int MsTicks(float ms)
	{
		float tps = DS_RoofSnow.DebugTicksPerSec();
		if (tps <= 0)
			return 0;
		return ms * tps / 1000.0;
	}

	//! test harness statistics: the ticks since tick0 for one step (keeps the longest); returns the tick now
	protected int StatCover(int part, int tick0)
	{
		int now = TickCount(0);
		int d = now - tick0;
		if (d > DS_State.s_StatCoverMax[part])
			DS_State.s_StatCoverMax[part] = d;
		return now;
	}

	//! creates, stages or re-places one cell of the work list
	protected void ProcessItem(int index, bool anySnow)
	{
		int level = m_WLevel[index];
		int x = m_WX[index];
		int z = m_WZ[index];
		map<int, ref DS_SnowCell> cells = m_Cells[level];
		float size = Size(level);
		int key = x * 65536 + z;
		float dist = DistXZ((x + 0.5) * size, (z + 0.5) * size);
		int sig = 0;
		if (level < LEVELS - 1)
			sig = m_Sig[level].Get(key);
		DS_SnowCell cell = cells.Get(key);
		if (cell && cell.m_BuildGen != m_BuildGen)
		{
			// the pond ice changed the ground under this cell: the new triangles go up first, then the old ones go
			DS_SnowCell fresh = CreateCell(level, x, z);
			fresh.m_Sig = sig;
			if (anySnow)
			{
				int freshStage = DesiredStage(fresh, dist);
				if (freshStage > 0)
					ApplyStage(fresh, freshStage, dist);
			}
			DeleteObjects(cell);
			cells.Set(key, fresh);
			return;
		}
		if (cell && cell.m_Sig != sig)
			Restitch(cell, sig); // the border moved: same triangles, new edge heights
		if (!cell)
		{
			m_Cost += 0.005;
			if (!anySnow)
				return;
			int createTick = TickCount(0);
			for (int ci = 0; ci < 7; ci++)
				m_Calls[ci] = 0;
			cell = CreateCell(level, x, z);
			if (TickCount(createTick) > DS_State.s_StatCoverMax[5])
			{
				DS_State.s_StatCoverWorst = string.Format("level %1 at %2 %3 tris %4 calls", level, x * size, z * size, cell.m_Tris.Count());
				for (int cj = 0; cj < 7; cj++)
					DS_State.s_StatCoverWorst = DS_State.s_StatCoverWorst + " " + m_Calls[cj].ToString();
			}
			StatCover(5, createTick);
			cell.m_Sig = sig;
			if (sig != 0)
				m_SkirtCount++;
			cells.Set(key, cell);
		}

		int want = DesiredStage(cell, dist);
		if (want != cell.m_Stage)
		{
			int stageTick = TickCount(0);
			ApplyStage(cell, want, dist);
			StatCover(6, stageTick);
		}
		else if (cell.m_Stage > 0 && NeedsReplace(cell))
			Retransform(cell);
		else
			m_Cost += 0.02;
	}

	void Clear()
	{
		if (m_Cells)
		{
			for (int level = 0; level < m_Cells.Count(); level++)
				ClearMap(m_Cells[level]);
		}
		if (m_Retired)
			DropRetired(true);
		m_Objects = 0;
	}

	protected void ClearMap(map<int, ref DS_SnowCell> cells)
	{
		if (!cells)
			return;
		for (int i = 0; i < cells.Count(); i++)
		{
			DS_SnowCell c = cells.GetElement(i);
			if (c)
				DeleteObjects(c);
		}
		cells.Clear();
	}

}
