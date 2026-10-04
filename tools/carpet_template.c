//! One triangle of the snow cover: plane y = yc + a * (x - cx) + b * (z - cz) over a square (sub)cell
class SZ_SnowTri
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
}

//! One grid cell of the snow cover at one level of detail
class SZ_SnowCell
{
	int m_Level;
	int m_Stage;
	int m_X;
	int m_Z;
	int m_Sig; // which neighbouring coarser cells this cell is stitched to
	float m_Avg;
	int m_Epoch; // forced re-placement generation (test harness lighting and height changes)
	float m_RetiredAt;
	ref array<ref SZ_SnowTri> m_Tris;
	ref array<Object> m_Objects;

	void SZ_SnowCell()
	{
		m_Tris = new array<ref SZ_SnowTri>;
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
class SZ_SnowCarpet
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
	//! as dark lines. Walkable surfaces higher than this (floors, bridges) are not roads.
	static const float ROAD_PROBE = 0.8;
	//! cells of an earlier layout stay this long at most while the new layout is being built
	static const float RETIRE_SECONDS = 8.0;
	static const int RETIRE_MAX = 2000;
	//! blocks of the coarsest level around the camera that are worked on first after every layout change
	static const int NEAR_BLOCKS = 9;
	protected static SZ_SnowCarpet s_Instance;

	// per level: cell size in terrain cells, outer radius, height above the lifted terrain, largest lift
	protected ref array<int> m_F;
	protected ref array<float> m_Rad;
	protected ref array<float> m_Off;
	protected ref array<float> m_Cap;
	protected float m_Cell;
	protected bool m_Ready;
	protected ref array<ref map<int, ref SZ_SnowCell>> m_Cells;
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
	protected int m_SkirtCount;
	protected float m_Cost;
	// camera position the level layout was built for
	protected vector m_ListCamera;
	// forced re-placement generation (test harness lighting normal and extra height)
	protected int m_Epoch;
	// cells of an earlier layout stay until the new layout has been built once, so moving opens no holes
	protected ref array<ref SZ_SnowCell> m_Retired;
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
	// level 0 cells: highest road surface above the terrain inside the cell
	protected ref map<int, float> m_Road0;
	// level 0 cells: which diagonal the terrain uses (1 = from the low corner to the high corner)
	protected ref map<int, int> m_Diag0;

	void SZ_SnowCarpet()
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
		m_Cells = new array<ref map<int, ref SZ_SnowCell>>;
		m_Rise = new array<ref map<int, float>>;
		m_Lift = new array<ref map<int, float>>;
		m_Sig = new array<ref map<int, int>>;
		m_Keep = new array<ref map<int, bool>>;
		for (int level = 0; level < LEVELS; level++)
		{
			m_Cells.Insert(new map<int, ref SZ_SnowCell>);
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
		m_Retired = new array<ref SZ_SnowCell>;
		m_Road0 = new map<int, float>;
		m_Diag0 = new map<int, int>;
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

	void ~SZ_SnowCarpet()
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
		Print(string.Format("[SeasonZ] snow cover: terrain grid detected=%1 m, level cells%2 m, radii%3 m", detected, sizes, radii));
	}

	@@KEEP GetObjectCount@@
	@@KEEP GetSkirtCount@@
	@@KEEP GetCell@@
	@@KEEP DetectGrid@@

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

	@@KEEP DistXZ@@

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

	@@KEEP DropMissing@@
	@@KEEP IsWater@@
	@@KEEP RoadAbove@@
	@@KEEP CellRoad0@@
	@@KEEP VertexRoad0@@
	@@KEEP CellDiag0@@
	@@KEEP RoadLift0@@
	@@KEEP CoverHeightAt@@

	//! true when the snow cover has a triangle over this point. Near the camera (level 0) this follows the real
	//! triangles, so the bare ground under eaves and around buildings stays bare; further out the coarse levels
	//! cover everything but water.
	static bool CoversAt(float x, float z)
	{
		if (!s_Instance || !s_Instance.m_Ready)
			return false;
		int ix = Math.Floor(x / s_Instance.m_Cell);
		int iz = Math.Floor(z / s_Instance.m_Cell);
		SZ_SnowCell cell = s_Instance.m_Cells[0].Get(ix * 65536 + iz);
		if (!cell)
			return true;
		if (cell.m_Stage <= 0)
			return false;
		foreach (SZ_SnowTri t : cell.m_Tris)
		{
			if (s_Instance.TriContains(t, x, z))
				return true;
		}
		return false;
	}

	@@KEEP TriContains@@

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
			SZ_SnowCell c = m_Cells[lv].Get(x * 65536 + z);
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
		SZ_SnowCell cell = m_Cells[level].Get(cx * 65536 + cz);
		if (!cell || cell.m_Stage <= 0)
		{
			level = -1;
			return 0;
		}
		foreach (SZ_SnowTri t : cell.m_Tris)
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
		SZ_SnowCell cell = m_Cells[level].Get(cx * 65536 + cz);
		string info = string.Format("level=%1 list=%2 water=%3 terrain=%4", level, m_ListCamera, IsWater(x, z), g_Game.SurfaceY(x, z));
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

	@@KEEP ProbeBlocked@@
	@@KEEP BlockedProbes@@
	@@KEEP MakeTri@@
	@@KEEP SetPlane@@
	@@KEEP TriCorners@@

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

	@@KEEP BuildExact@@
	@@KEEP PlaneAt@@

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
				float h = g_Game.SurfaceY(x0 + s * u, z0 + s * v);
				float road = RoadAbove(x0 + s * u, z0 + s * v);
				float plane = PlaneAt(diag, u, v, h00, h10, h11, h01);
				float d = h + road - plane;
				if (d > rise)
					rise = d;
			}
		}
		m_Cost += 0.004 * (m + 1) * (m + 1);
		return rise;
	}

	@@KEEP CoarseDiag@@

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
		float h00 = g_Game.SurfaceY(x0, z0);
		float h10 = g_Game.SurfaceY(x0 + s, z0);
		float h11 = g_Game.SurfaceY(x0 + s, z0 + s);
		float h01 = g_Game.SurfaceY(x0, z0 + s);
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
		float ground = g_Game.SurfaceY(vx * s, vz * s);
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
		float ground = g_Game.SurfaceY(x, z);
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
	protected void BuildCoarse(SZ_SnowCell cell, int level, int cx, int cz, float s)
	{
		m_Cost += 0.05;
		float x0 = cx * s;
		float z0 = cz * s;
		float g00 = g_Game.SurfaceY(x0, z0);
		float g10 = g_Game.SurfaceY(x0 + s, z0);
		float g11 = g_Game.SurfaceY(x0 + s, z0 + s);
		float g01 = g_Game.SurfaceY(x0, z0 + s);
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

	protected SZ_SnowCell CreateCell(int level, int x, int z)
	{
		SZ_SnowCell cell = new SZ_SnowCell();
		cell.m_Level = level;
		cell.m_X = x;
		cell.m_Z = z;
		float size = Size(level);
		float x0 = x * size;
		float z0 = z * size;
		float avgA = g_Game.SurfaceY(x0 + size * 0.5, z0 + size * 0.5);
		float avgB = g_Game.SurfaceY(x0, z0);
		cell.m_Avg = (avgA + avgB) * 0.5;

		if (level == 0)
		{
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
		foreach (SZ_SnowTri t : cell.m_Tris)
			SetVariant(t, level);
		return cell;
	}

	@@KEEP Wrap@@

	//! picks the model of the triangle's size and place in the 30 m texture period
	protected void SetVariant(SZ_SnowTri t, int level)
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
	protected void Restitch(SZ_SnowCell cell, int sig)
	{
		cell.m_Sig = sig;
		foreach (SZ_SnowTri t : cell.m_Tris)
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

	protected int DesiredStage(SZ_SnowCell cell, float dist)
	{
		if (cell.m_Tris.Count() == 0)
			return 0;

		float depth = SZ_State.SnowAt(cell.m_Avg, m_S0, m_S1, m_S2);
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

	@@KEEP NeedsReplace@@
	@@KEEP DeleteObjects@@
	@@KEEP SetTriTransform@@
	@@KEEP SmoothNormal@@
	@@KEEP CornerNormal@@
	@@KEEP ShapeName@@
	@@KEEP ApplyStage@@
	@@KEEP Retransform@@

	//! true when the area of a cell of an earlier layout is covered by built cells of the current layout (or lies
	//! outside it), so the old cell can go without opening a hole or overlapping its replacement
	protected bool Covered(SZ_SnowCell c)
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

	@@KEEP DropRetired@@

	void Update(float timeslice, vector camera, float s0, float s1, float s2)
	{
		if (!m_Ready)
			return;

		m_S0 = s0;
		m_S1 = s1;
		m_S2 = s2;
		m_Camera = camera;
		m_Clock += timeslice;
		if (SZ_State.s_DebugNoCarpet)
		{
			if (m_Objects > 0 || m_Cells[0].Count() > 0)
				Clear();
			m_AnchorX = -1000000;
			return;
		}
		if (SZ_State.s_DebugExtraOffset != m_ExtraOffset || SZ_State.s_DebugNormalMode != m_NormalMode)
		{
			// test harness: re-place every cell with the new height or lighting normal
			m_ExtraOffset = SZ_State.s_DebugExtraOffset;
			m_NormalMode = SZ_State.s_DebugNormalMode;
			m_Epoch++;
		}
		bool anySnow = Math.Max(s0, Math.Max(s1, s2)) >= 0.5;

		// the layout follows the camera in steps of four terrain cells
		float step = m_Cell * 4.0;
		int anchorX = Math.Floor(camera[0] / step);
		int anchorZ = Math.Floor(camera[2] / step);
		if (anchorX != m_AnchorX || anchorZ != m_AnchorZ)
		{
			m_AnchorX = anchorX;
			m_AnchorZ = anchorZ;
			RebuildWorkList();
		}

		m_Cost = 0;
		int count = m_WLevel.Count();
		// first the blocks around the camera, which change with every layout
		while (m_NearScan < m_NearEnd && m_NearScan < count && m_Cost < 3.5)
		{
			ProcessItem(m_NearScan, anySnow);
			m_NearScan++;
		}
		// then the main cursor, which keeps cycling through the whole layout
		int visited = 0;
		while (m_Cost < 6.0 && visited < count)
		{
			if (m_Scan >= count)
			{
				m_Scan = 0;
				// a full pass over one layout: every cell of it exists now, the earlier layouts can go
				if (m_PassLayout == m_Layout && m_Retired.Count() > 0)
					DropRetired(true);
				m_PassLayout = m_Layout;
			}
			ProcessItem(m_Scan, anySnow);
			m_Scan++;
			visited++;
		}
		if (m_Retired.Count() > 0)
			DropRetired(false);
	}

	//! creates, stages or re-places one cell of the work list
	protected void ProcessItem(int index, bool anySnow)
	{
		int level = m_WLevel[index];
		int x = m_WX[index];
		int z = m_WZ[index];
		map<int, ref SZ_SnowCell> cells = m_Cells[level];
		float size = Size(level);
		int key = x * 65536 + z;
		float dist = DistXZ((x + 0.5) * size, (z + 0.5) * size);
		int sig = 0;
		if (level < LEVELS - 1)
			sig = m_Sig[level].Get(key);
		SZ_SnowCell cell = cells.Get(key);
		if (cell && cell.m_Sig != sig)
			Restitch(cell, sig); // the border moved: same triangles, new edge heights
		if (!cell)
		{
			m_Cost += 0.005;
			if (!anySnow)
				return;
			cell = CreateCell(level, x, z);
			cell.m_Sig = sig;
			if (sig != 0)
				m_SkirtCount++;
			cells.Set(key, cell);
		}

		int want = DesiredStage(cell, dist);
		if (want != cell.m_Stage)
			ApplyStage(cell, want, dist);
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

	@@KEEP ClearMap@@
}
