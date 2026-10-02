//! One snow triangle on a building, stored as the transform that maps the unit triangle model onto the roof
class DS_RoofTri
{
	int m_Shape;
	string m_Variant;
	vector m_Center;
	vector m_AxisU;
	vector m_AxisV;
	vector m_Normal;
	int m_Drop; // snow stages lost on steep slopes
	//! a piece at the edge of a roof: drawn with the c model mapped onto these three corners (world, on the roof)
	bool m_Free;
	vector m_P0;
	vector m_P1;
	vector m_P2;
	//! a square of m_Span grid cells on one plane, drawn as one object (the dsq models)
	bool m_Quad;
	int m_Span;
	//! how much the piece grows around its centre so it overlaps its neighbours (1.03 = 3 percent)
	float m_Grow;

	void DS_RoofTri()
	{
		m_Grow = 1.03;
	}
}

//! the polygons of one structure, built a step at a time over several frames: per surface, splitting it into
//! planes, then the polygon of each plane, then the pieces of each polygon
class DS_CapJob
{
	ref array<int> m_Grp;
	int m_Groups;
	ref array<bool> m_GridGroup;
	ref array<ref array<int>> m_Members;
	int m_G;
	int m_Phase;
	int m_R;
	int m_PlanesUsed;
	int m_Ok;
	ref array<ref map<int, bool>> m_Sets;
	ref array<ref array<int>> m_Lists;
	ref array<float> m_Planes;
	ref map<int, int> m_RegOf;
	ref array<ref array<float>> m_Polys;
	ref array<int> m_Holes;

	void DS_CapJob()
	{
		m_Grp = new array<int>;
		m_GridGroup = new array<bool>;
		m_Members = new array<ref array<int>>;
	}
}

//! Roof snow of one building
class DS_RoofBuilding
{
	Object m_Obj;
	int m_State;
	bool m_Fine; // sampled with the close range grid
	//! 0 = building or rock, 1 = wall, fence or wreck (thin tops, fine grid), 2 = movable entity (vehicle, tent, base
	//! part, container): its snow goes when it moves
	int m_Kind;
	float m_Ground;
	float m_Dist;
	int m_Stage;
	float m_Offset;
	ref array<ref DS_RoofTri> m_Tris;
	ref array<Object> m_Objects;
	//! a small structure (block, box, bench, hay bale): sampled on a grid sized to it, with its edges found at any
	//! distance
	bool m_Small;
	//! a wall: a flat top becomes one strip of snow (its edges are found like those of the small structures)
	bool m_Wall;
	//! how far from the camera this wall carries snow (set once its pieces are known; -1 = not yet)
	float m_Reach;
	vector m_U;
	vector m_V;
	vector m_Origin;
	float m_StepU;
	float m_StepV;
	int m_NU;
	int m_NV;
	float m_Top;
	float m_Bottom;
	int m_Row;
	ref array<float> m_H;
	ref array<float> m_NY;
	//! close buildings: the grid edges between a sample on the roof and one beside it, and where the roof ends on
	//! them (found with a few more rays after the grid)
	ref array<int> m_EdgeKeys;
	int m_EdgeCursor;
	ref map<int, vector> m_Cross;
	//! thickness of the snow slab as placed (metres)
	float m_Slab;
	//! the polygons being built (state 4)
	ref DS_CapJob m_Job;
	//! the pieces of a new stage being placed over several frames (null when none); the current pieces stay until
	//! all of them are placed
	ref array<Object> m_Pending;
	int m_PendCursor;
	int m_PendStage;
	float m_PendSlab;
	float m_PendOffset;
	//! test harness: how the surfaces became polygons or grid pieces
	string m_CapInfo;
	// movable entities: where it stood, for how long, and the ground snow when it came to rest (-1 = it stood there
	// before this client saw it)
	vector m_LastPos;
	vector m_LastDir;
	float m_StillTime;
	float m_RestDepth;

	void DS_RoofBuilding()
	{
		m_Reach = -1;
		m_Tris = new array<ref DS_RoofTri>;
		m_Objects = new array<Object>;
		m_H = new array<float>;
		m_NY = new array<float>;
		m_EdgeKeys = new array<int>;
		m_Cross = new map<int, vector>;
	}
}

class DS_RoofTile
{
	ref array<ref DS_RoofBuilding> m_Buildings;
	bool m_Scanned;

	void DS_RoofTile()
	{
		m_Buildings = new array<ref DS_RoofBuilding>;
	}
}

//! Client: snow on roofs, ledges and other upward facing parts of buildings near the camera. Every building is
//! sampled once with a grid of downward rays in its own axes; the hits are joined into triangles that follow the
//! roof planes and are drawn with the same snow models as the ground cover.
class DS_RoofSnow
{
	static const float TILE = 40.0;
	static const float RADIUS = 220.0;
	static const float KEEP_RADIUS = 280.0;
	static const float NO_HIT = -100000.0;
	static const float MIN_NORMAL_Y = 0.6;
	static const float FINE_RADIUS = 90.0;
	//! small structures (blocks, boxes, benches, hay bales) carry snow this close to the camera; further out they are
	//! a few pixels on screen
	static const float SMALL_RADIUS = 90.0;
	//! walls, fences and wrecks carry snow this close to the camera: further out their tops are a line of one or two
	//! pixels (no visible change from 160 to 220 m, about 4 percent of the frame rate in a village)
	static const float WALL_RADIUS = 160.0;
	//! walls and fences with an uneven top (pickets, stones, planks) need many pieces per metre: they carry snow only
	//! this close, where their tops are more than a pixel or two high
	static const float DENSE_WALL_RADIUS = 80.0;
	static const float DENSE_WALL = 3.0;
	static const float MOVABLE_RADIUS = 160.0;
	//! a movable entity has to stand still this long (seconds) before it gets snow
	static const float MOVABLE_REST = 3.0;
	//! snow lies on roofs as a slab with snowy sides, about as thick as the snow on the ground: deep snow also covers
	//! the places where the drawn roof rises above the geometry the rays find (up to two decimetres on some roofs).
	//! Walls, fences, wrecks and vehicles carry thinner caps. Metres of slab per centimetre of snow, and the limits
	static const float SLAB_PER_CM = 0.009;
	static const float SLAB_MIN = 0.02;
	static const float SLAB_MAX = 0.22;
	static const float SLAB_CLOSED = 0.1;
	static const float THIN_PER_CM = 0.003;
	static const float THIN_MIN = 0.012;
	static const float THIN_MAX = 0.06;
	//! the slab is placed again when the snow made it this much thicker or thinner
	static const float SLAB_STEP = 0.02;
	//! roof slopes (normal height) from which snow slides off: a thinner cover above 53 degrees, none above 60
	static const float STEEP_NY = 0.6;
	//! halvings that find where a roof ends between a sample on it and one beside it (a 0.94 m edge to 6 cm)
	static const int EDGE_STEPS = 4;
	//! flat tops and plane roofs: most planes one structure is split into, and how close to its plane every sample
	//! of a plane must lie
	static const int MAX_PLANES = 160;
	static const float CAP_FLAT = 0.04;

	//! vehicles, tents, base parts and containers known to this client (filled from their EEInit)
	protected static ref array<EntityAI> s_Movables;
	//! movable entities that appeared next to the camera while this client watched: they start without snow
	protected static ref map<EntityAI, bool> s_Fresh;
	protected static float s_Clock;
	//! CPU ticks per second (measured against the frame time) and the tick the last update started at
	protected static float s_TicksPerSec;
	protected static int s_FrameTick;
	//! the update of a frame stops starting new work after this many milliseconds; structures closer than
	//! URGENT_DIST may take up to URGENT_MS, so the snow on the buildings around a player who just arrived (spawn,
	//! teleport, a fast car) is there within seconds
	static const float FRAME_MS = 4.0;
	static const float URGENT_MS = 8.0;
	static const float URGENT_DIST = 60.0;
	//! the same in CPU ticks (0 until the tick length is known)
	protected static int s_BudgetTicks;
	protected static int s_UrgentTicks;

	static bool IsMovable(Object o)
	{
		return o && (o.IsInherited(CarScript) || o.IsInherited(TentBase) || o.IsInherited(BaseBuildingBase) || o.IsInherited(DeployableContainer_Base));
	}

	//! test harness: CPU ticks per second as measured against the frame time
	static float DebugTicksPerSec()
	{
		return s_TicksPerSec;
	}

	//! test harness: times the parts of placing n roof pieces in front of the camera (ms per piece)
	string DebugPlaceBench(int n)
	{
		vector c = g_Game.GetCurrentCameraPosition() + g_Game.GetCurrentCameraDirection() * 20.0;
		DS_RoofTri t = new DS_RoofTri();
		t.m_Shape = 0;
		t.m_Variant = "12";
		t.m_AxisU = "0.9 0.1 0";
		t.m_AxisV = "0 0.05 0.9";
		t.m_Normal = "0 1 0";
		t.m_Center = c;
		int t0 = TickCount(0);
		string last;
		for (int i = 0; i < n; i++)
		{
			int st = 1 + i % 4;
			last = DS_Const.DATA + "snow\\dsr_" + ShapeName(t.m_Shape) + t.m_Variant + "_s" + st.ToString() + ".p3d";
		}
		int t1 = TickCount(0);
		array<Object> objs = new array<Object>;
		for (int j = 0; j < n; j++)
			objs.Insert(g_Game.CreateStaticObjectUsingP3D(last, c, "0 0 0", 1.0, true));
		int t2 = TickCount(0);
		vector bc;
		foreach (Object o1 : objs)
			bc = o1.GetBoundingCenter();
		int t3 = TickCount(0);
		foreach (Object o2 : objs)
			Place(o2, t, 0.1);
		int t4 = TickCount(0);
		foreach (Object o3 : objs)
			g_Game.ObjectDelete(o3);
		int t5 = TickCount(0);
		float k = 1000.0 / Math.Max(1.0, s_TicksPerSec) / Math.Max(1, n);
		return string.Format("n=%1 ms per piece: path %2 create %3 boundingcentre %4 place %5 delete %6", n, (t1 - t0) * k, (t2 - t1) * k, (t3 - t2) * k, (t4 - t3) * k, (t5 - t4) * k);
	}

	//! map structures without a script class (open sheds, containers, platforms, hay bales, barriers, bridges): they
	//! carry snow like buildings. Roads, lines, wires, poles, lamps and markings on the ground do not
	static bool IsPlainStructure(string shape)
	{
		if (shape.IndexOf("\\structures\\") < 0)
			return false;
		if (shape.IndexOf("\\roads\\bridges\\") >= 0)
			return true;
		array<string> skip = {"\\roads\\", "\\rail\\tracks\\", "rail_pole", "rail_signal", "rail_crossing_barrier", "rail_linebreak", "decal", "power_", "lamp_", "wire", "football", "garbage_ground", "_line", "cable", "antenna"};
		foreach (string s : skip)
		{
			if (shape.IndexOf(s) >= 0)
				return false;
		}
		return true;
	}

	static void RegisterMovable(EntityAI e)
	{
		if (!e)
			return;
		if (!s_Movables)
			s_Movables = new array<EntityAI>;
		if (!s_Fresh)
			s_Fresh = new map<EntityAI, bool>;
		s_Movables.Insert(e);
		// entities enter the network bubble far away; one created next to the camera was just placed or spawned
		if (s_Clock > 30.0 && vector.Distance(e.GetPosition(), g_Game.GetCurrentCameraPosition()) < 200.0)
			s_Fresh.Set(e, true);
	}

	static void UnregisterMovable(EntityAI e)
	{
		if (s_Movables)
			s_Movables.RemoveItem(e);
		if (s_Fresh)
			s_Fresh.Remove(e);
	}

	protected ref map<int, ref DS_RoofTile> m_Tiles;
	protected ref map<EntityAI, ref DS_RoofBuilding> m_Movable;
	protected float m_MovableTimer;
	protected ref array<int> m_Work;
	//! test harness: calls of PlaneEnd during the last structure's polygons
	protected int m_PlaneEnds;
	//! pieces waiting to be deleted: removed a few hundred per frame, so leaving a town or replacing a roof's pieces
	//! does not stall a frame
	protected ref array<Object> m_Trash;
	protected int m_Cursor;
	protected int m_AnchorX;
	protected int m_AnchorZ;
	protected float m_Cell;
	protected float m_Cost;
	protected int m_Objects;
	protected int m_Rays;
	protected vector m_Camera;
	protected float m_S0;
	protected float m_S1;
	protected float m_S2;

	void DS_RoofSnow()
	{
		m_Tiles = new map<int, ref DS_RoofTile>;
		m_Movable = new map<EntityAI, ref DS_RoofBuilding>;
		m_Work = new array<int>;
		m_Trash = new array<Object>;
		m_AnchorX = -100000;
		m_AnchorZ = -100000;
	}

	void ~DS_RoofSnow()
	{
		Clear();
	}

	void Init(float terrainCell)
	{
		m_Cell = terrainCell;
		if (m_Cell <= 0)
			m_Cell = 7.5;
	}

	int GetObjectCount()
	{
		return m_Objects;
	}

	int GetRayCount()
	{
		return m_Rays;
	}

	//! test harness: objects with snow and snow pieces per kind (buildings, walls and wrecks, movable entities)
	string DebugStats()
	{
		array<int> objs = {0, 0, 0};
		array<int> pieces = {0, 0, 0};
		array<int> tris = {0, 0, 0};
		for (int i = 0; i < m_Tiles.Count(); i++)
		{
			DS_RoofTile t = m_Tiles.GetElement(i);
			if (!t)
				continue;
			foreach (DS_RoofBuilding b : t.m_Buildings)
			{
				if (b.m_Objects.Count() > 0)
					objs[b.m_Kind] = objs[b.m_Kind] + 1;
				pieces[b.m_Kind] = pieces[b.m_Kind] + b.m_Objects.Count();
				tris[b.m_Kind] = tris[b.m_Kind] + b.m_Tris.Count();
			}
		}
		string moving = "";
		for (int m = 0; m < m_Movable.Count(); m++)
		{
			DS_RoofBuilding mb = m_Movable.GetElement(m);
			if (mb.m_Objects.Count() > 0)
				objs[2] = objs[2] + 1;
			pieces[2] = pieces[2] + mb.m_Objects.Count();
			tris[2] = tris[2] + mb.m_Tris.Count();
			if (mb.m_Obj)
				moving += string.Format(" [%1 state=%2 still=%3 rest=%4 tris=%5 pieces=%6 stage=%7]", mb.m_Obj.GetType(), mb.m_State, mb.m_StillTime, mb.m_RestDepth, mb.m_Tris.Count(), mb.m_Objects.Count(), mb.m_Stage);
		}
		int known = 0;
		if (s_Movables)
			known = s_Movables.Count();
		return string.Format("buildings %1 objs %2 pieces (%3 tris), walls/wrecks %4 objs %5 pieces (%6 tris), movable %7 objs %8 pieces of %9 known:", objs[0], pieces[0], tris[0], objs[1], pieces[1], tris[1], objs[2], pieces[2], known) + moving;
	}

	protected float TileDist(int tx, int tz)
	{
		float dx = (tx + 0.5) * TILE - m_Camera[0];
		float dz = (tz + 0.5) * TILE - m_Camera[2];
		return Math.Sqrt(dx * dx + dz * dz);
	}

	protected void RebuildWork()
	{
		m_Work.Clear();
		int n = Math.Ceil(KEEP_RADIUS / TILE) + 1;
		array<float> dists = new array<float>;
		for (int dx = -n; dx <= n; dx++)
		{
			for (int dz = -n; dz <= n; dz++)
			{
				int tx = m_AnchorX + dx;
				int tz = m_AnchorZ + dz;
				float d = TileDist(tx, tz);
				if (d > RADIUS)
					continue;
				int pos = dists.Count();
				while (pos > 0 && dists[pos - 1] > d)
					pos--;
				dists.InsertAt(d, pos);
				m_Work.InsertAt(tx * 65536 + tz, pos);
			}
		}

		array<int> drop = new array<int>;
		for (int i = 0; i < m_Tiles.Count(); i++)
		{
			int key = m_Tiles.GetKey(i);
			int kx = Math.Floor(key / 65536.0);
			int kz = key - kx * 65536;
			if (TileDist(kx, kz) > KEEP_RADIUS)
				drop.Insert(key);
		}
		foreach (int k : drop)
		{
			DS_RoofTile t = m_Tiles.Get(k);
			if (t)
			{
				foreach (DS_RoofBuilding b : t.m_Buildings)
					TrashAll(b);
			}
			m_Tiles.Remove(k);
		}
		m_Cursor = 0;
	}

	protected void ScanTile(DS_RoofTile tile, int tx, int tz)
	{
		tile.m_Scanned = true;
		vector center = Vector((tx + 0.5) * TILE, 0, (tz + 0.5) * TILE);
		center[1] = g_Game.SurfaceY(center[0], center[2]);
		array<Object> objects = new array<Object>;
		g_Game.GetObjectsAtPosition(center, TILE * 0.7072, objects, null);
		m_Cost += 1.0 + objects.Count() * 0.004;

		foreach (Object o : objects)
		{
			if (!o || IsMovable(o))
				continue;
			// ground details the snow cover buries (kerbs, footpaths) carry no snow of their own
			if (DS_TreeSwap.IsPath(o))
				continue;
			vector p = o.GetPosition();
			if (Math.Floor(p[0] / TILE) != tx || Math.Floor(p[2] / TILE) != tz)
				continue;
			vector mm[2];
			o.ClippingInfo(mm);
			vector size = mm[1] - mm[0];
			int kind = -1;
			bool small = false;
			string shape = o.GetShapeName();
			shape.ToLower();
			// walls keep the fine grid of thin tops, whatever their bounding box
			bool wall = shape.IndexOf("\\walls\\") >= 0;
			bool plain = !o.IsBuilding() && !o.IsRock() && DS_State.s_DebugRoofPlain > 0 && IsPlainStructure(shape);
			if (!wall && (o.IsBuilding() || o.IsRock() || plain) && size[0] >= 2.5 && size[2] >= 2.5 && size[1] >= 2.0)
			{
				kind = 0;
			}
			else if (plain && !wall && DS_State.s_DebugRoofPlain == 3 && size[0] >= 0.9 && size[2] >= 0.9 && size[1] >= 0.5)
			{
				// smaller plain structures (blocks, barriers, boxes, benches, hay bales): a grid sized to them, and
				// flat tops drawn as single polygons
				kind = 0;
				small = true;
			}
			else
			{
				// walls, fences, car wrecks and smaller plain structures (barriers, pipes, wood piles): narrow tops
				// that hold a strip of snow
				bool thin = (plain && DS_State.s_DebugRoofPlain > 1) || wall || shape.IndexOf("\\wrecks\\") >= 0;
				if (thin && Math.Max(size[0], size[2]) >= 1.2 && size[1] >= 0.4)
					kind = 1;
			}
			if (kind < 0)
				continue;
			DS_RoofBuilding b = new DS_RoofBuilding();
			b.m_Obj = o;
			b.m_Kind = kind;
			b.m_Small = small;
			b.m_Wall = wall && kind == 1;
			b.m_Ground = g_Game.SurfaceY(p[0], p[2]);
			tile.m_Buildings.Insert(b);
		}
	}

	//! sets up the ray grid in the object's own horizontal axes. Buildings use square cells; walls, wrecks and
	//! movable entities use a fine grid with at least four samples across their narrow side
	protected void BeginScan(DS_RoofBuilding b, bool fine)
	{
		// a stage being placed belongs to the old triangles
		TrashPending(b);
		b.m_Job = null;
		// small structures are only sampled near the camera: always at full detail
		if (b.m_Small)
			fine = true;
		b.m_Fine = fine;
		vector mat[4];
		b.m_Obj.GetTransform(mat);
		vector ax = Vector(mat[0][0], 0, mat[0][2]);
		vector az = Vector(mat[2][0], 0, mat[2][2]);
		float su = ax.Length();
		float sv = az.Length();
		if (su < 0.01 || sv < 0.01)
		{
			b.m_State = 2;
			return;
		}
		b.m_U = ax * (1.0 / su);
		b.m_V = az * (1.0 / sv);
		vector mm[2];
		b.m_Obj.ClippingInfo(mm);
		float pad = 0.6;
		if (b.m_Kind != 0 || b.m_Small)
			pad = 0.15;
		float u0 = mm[0][0] * su - pad;
		float u1 = mm[1][0] * su + pad;
		float v0 = mm[0][2] * sv - pad;
		float v1 = mm[1][2] * sv + pad;
		if (b.m_Kind == 0)
		{
			// close buildings get twice the resolution; far ones stay cheap
			float step = m_Cell * 0.25;
			if (fine)
				step = m_Cell * 0.125;
			if (b.m_Small)
			{
				// small structures: three samples across their narrow side
				float side = Math.Min(u1 - u0, v1 - v0) - 2.0 * pad;
				step = Math.Clamp(side / 3.0, 0.15, step);
			}
			// very large buildings get a coarser grid
			while ((u1 - u0) / step > 44 || (v1 - v0) / step > 44)
				step *= 2.0;
			b.m_StepU = step;
			b.m_StepV = step;
		}
		else
		{
			float lenU = u1 - u0;
			float lenV = v1 - v0;
			float narrow = Math.Min(lenU, lenV) - 2.0 * pad;
			float stepNarrow = Math.Clamp(narrow / 4.0, 0.06, 0.3);
			float stepLong = Math.Clamp(Math.Max(lenU, lenV) / 24.0, 0.15, 0.5);
			if (lenU <= lenV)
			{
				b.m_StepU = stepNarrow;
				b.m_StepV = stepLong;
			}
			else
			{
				b.m_StepU = stepLong;
				b.m_StepV = stepNarrow;
			}
			while ((lenU / b.m_StepU) * (lenV / b.m_StepV) > 1200.0)
			{
				b.m_StepU = b.m_StepU * 1.25;
				b.m_StepV = b.m_StepV * 1.25;
			}
		}
		b.m_NU = Math.Ceil((u1 - u0) / b.m_StepU) + 1;
		b.m_NV = Math.Ceil((v1 - v0) / b.m_StepV) + 1;
		if (b.m_Small)
		{
			// centred on the structure, so a round or ridged top is sampled alike on both sides
			float midU = (u0 + u1) * 0.5;
			float midV = (v0 + v1) * 0.5;
			u0 = midU - (b.m_NU - 1) * b.m_StepU * 0.5;
			v0 = midV - (b.m_NV - 1) * b.m_StepV * 0.5;
		}
		b.m_Origin = Vector(mat[3][0], 0, mat[3][2]) + b.m_U * u0 + b.m_V * v0;
		b.m_Top = mat[3][1] + mm[1][1] * mat[1].Length() + 1.5;
		b.m_Bottom = b.m_Ground - 0.5;
		b.m_Row = 0;
		b.m_H.Clear();
		b.m_NY.Clear();
		b.m_EdgeKeys.Clear();
		b.m_EdgeCursor = 0;
		b.m_Cross.Clear();
		b.m_State = 1;
	}

	//! the roof height a downward ray finds at a point: the highest hit on the object itself, or NO_HIT when there
	//! is none, when something solid other than vegetation lies above it, or for porches and slabs just above the
	//! ground (the terrain cover handles those)
	protected float SampleAt(DS_RoofBuilding b, float x, float z)
	{
		float groundHere = g_Game.SurfaceY(x, z);
		RaycastRVParams rp = new RaycastRVParams(Vector(x, b.m_Top, z), Vector(x, b.m_Bottom, z), null, 0);
		rp.type = ObjIntersectFire;
		rp.flags = CollisionFlags.ALLOBJECTS;
		rp.sorted = true;
		array<ref RaycastRVResult> results = new array<ref RaycastRVResult>;
		m_Rays++;
		m_Cost += 0.035;
		if (!DayZPhysics.RaycastRVProxy(rp, results))
			return NO_HIT;
		// results come in no particular order: take the highest hit on this object
		float h = NO_HIT;
		float blockTop = NO_HIT;
		foreach (RaycastRVResult res : results)
		{
			Object hit = res.obj;
			if (res.parent)
				hit = res.parent;
			if (!hit)
				continue;
			bool own = hit == b.m_Obj;
			if (!own && b.m_Kind == 2)
			{
				// doors, hoods and other attachments belong to the vehicle
				EntityAI hitEntity = EntityAI.Cast(hit);
				if (hitEntity && hitEntity.GetHierarchyRoot() == b.m_Obj)
					own = true;
			}
			if (own)
			{
				if (res.pos[1] > h)
					h = res.pos[1];
			}
			else if (!DS_Util.IsVegetation(hit) && !hit.IsInherited(Man) && !hit.IsInherited(DayZCreature))
			{
				if (res.pos[1] > blockTop)
					blockTop = res.pos[1];
			}
		}
		if (h != NO_HIT && (blockTop > h + 0.3 || h < groundHere + 0.25))
			return NO_HIT;
		return h;
	}

	protected vector SamplePos(DS_RoofBuilding b, int i, int j)
	{
		return b.m_Origin + b.m_U * (i * b.m_StepU) + b.m_V * (j * b.m_StepV);
	}

	protected void CastRow(DS_RoofBuilding b)
	{
		int j = b.m_Row;
		for (int i = 0; i < b.m_NU; i++)
		{
			vector p = SamplePos(b, i, j);
			b.m_H.Insert(SampleAt(b, p[0], p[2]));
		}
		b.m_Row++;
		if (b.m_Row >= b.m_NV)
			FinishGrid(b);
	}

	//! the grid is complete: close buildings look for their roof edges first, everything else is built right away
	protected void FinishGrid(DS_RoofBuilding b)
	{
		if (DS_State.s_DebugRoofEdges && ((b.m_Kind == 0 && (b.m_Fine || b.m_Small)) || (b.m_Wall && DS_State.s_DebugRoofCaps > 0)))
		{
			CollectEdges(b);
			if (b.m_EdgeKeys.Count() > 0)
			{
				b.m_State = 3;
				return;
			}
		}
		BuildTris(b);
	}

	//! two samples on one continuous surface: both on the object and no step between them
	protected bool Joined(DS_RoofBuilding b, float ha, float hb)
	{
		return ha != NO_HIT && hb != NO_HIT && Math.AbsFloat(ha - hb) <= Math.Min(b.m_StepU, b.m_StepV) * 1.35;
	}

	//! the grid edges where a surface ends: between a sample on the building and one beside it, and at steps
	//! (chimneys, dormers, walls rising above a roof, a lower roof), where both sides end. Edge index: the sample
	//! index of its lower end twice, plus one along V. Cross key: the edge index twice, plus one when the surface is
	//! the one of the edge's upper end
	protected void CollectEdges(DS_RoofBuilding b)
	{
		for (int j = 0; j < b.m_NV; j++)
		{
			for (int i = 0; i < b.m_NU; i++)
			{
				float h = HAt(b, i, j);
				int e = (j * b.m_NU + i) * 2;
				if (i + 1 < b.m_NU)
					AddEdge(b, e, h, HAt(b, i + 1, j));
				if (j + 1 < b.m_NV)
					AddEdge(b, e + 1, h, HAt(b, i, j + 1));
			}
		}
		b.m_EdgeCursor = 0;
	}

	protected void AddEdge(DS_RoofBuilding b, int e, float hLow, float hHigh)
	{
		if (Joined(b, hLow, hHigh))
			return;
		if (hLow != NO_HIT)
			b.m_EdgeKeys.Insert(e * 2);
		if (hHigh != NO_HIT)
			b.m_EdgeKeys.Insert(e * 2 + 1);
	}

	//! finds where a surface ends on one edge: halving it from the sample on the surface towards the other end. A
	//! point counts as the surface while a ray finds the building there at the height the surface predicts, so a
	//! wall rising above the roof, a chimney or a lower part of the building ends it as well as the roof's rim
	protected void RefineEdge(DS_RoofBuilding b)
	{
		if (b.m_EdgeCursor >= b.m_EdgeKeys.Count())
		{
			BuildTris(b);
			return;
		}
		int key = b.m_EdgeKeys[b.m_EdgeCursor];
		b.m_EdgeCursor++;
		int e = key / 2;
		bool fromUpper = (key % 2) == 1;
		int idx = e / 2;
		bool alongV = (e % 2) == 1;
		int i0 = idx % b.m_NU;
		int j0 = idx / b.m_NU;
		int i1 = i0;
		int j1 = j0;
		float step = b.m_StepU;
		if (alongV)
		{
			j1++;
			step = b.m_StepV;
		}
		else
			i1++;
		int si = i0;
		int sj = j0;
		int xi = i1;
		int xj = j1;
		if (fromUpper)
		{
			si = i1;
			sj = j1;
			xi = i0;
			xj = j0;
		}
		float hs = HAt(b, si, sj);
		// the slope towards the edge, from the sample behind the surface sample (when it lies on the same surface)
		float slope = 0;
		int ni = si - (xi - si);
		int nj = sj - (xj - sj);
		if (ni >= 0 && ni < b.m_NU && nj >= 0 && nj < b.m_NV)
		{
			float hn = HAt(b, ni, nj);
			if (Joined(b, hs, hn))
				slope = (hs - hn) / step;
		}
		vector ps = SamplePos(b, si, sj);
		vector px = SamplePos(b, xi, xj);
		float lo = 0;
		float up = 1;
		for (int k = 0; k < EDGE_STEPS; k++)
		{
			float mid = (lo + up) * 0.5;
			vector pm = ps + (px - ps) * mid;
			float expect = hs + slope * step * mid;
			// a short ray around the expected height (an overhang up to 1.5 m above it still ends the surface)
			float hm = SampleNear(b, pm[0], pm[2], expect, 1.5, 0.4);
			if (hm != NO_HIT && Math.AbsFloat(hm - expect) <= 0.25)
				lo = mid;
			else
				up = mid;
		}
		// the first point found off the surface: the snow reaches the rim or a little into the wall (which hides
		// it), so no strip of roof shows between the snow and a wall
		float t = up;
		vector c = ps + (px - ps) * t;
		c[1] = hs + slope * step * t;
		b.m_Cross.Set(key, c);
	}

	protected float HAt(DS_RoofBuilding b, int i, int j)
	{
		return b.m_H[j * b.m_NU + i];
	}

	protected vector CornerAt(DS_RoofBuilding b, int i, int j)
	{
		vector p = SamplePos(b, i, j);
		p[1] = HAt(b, i, j);
		return p;
	}

	//! one piece at the edge of a roof, from three points on the roof (any order)
	protected DS_RoofTri AddFree(DS_RoofBuilding b, int gi, int gj, vector p0, vector p1, vector p2)
	{
		vector q1 = p1;
		vector q2 = p2;
		float det = (q1[0] - p0[0]) * (q2[2] - p0[2]) - (q1[2] - p0[2]) * (q2[0] - p0[0]);
		if (Math.AbsFloat(det) < 0.004)
			return null; // a sliver
		if (det < 0)
		{
			q1 = p2;
			q2 = p1;
		}
		vector e1 = q1 - p0;
		vector e2 = q2 - p0;
		// up normal: e2 x e1
		vector n = Vector(e2[1] * e1[2] - e2[2] * e1[1], e2[2] * e1[0] - e2[0] * e1[2], e2[0] * e1[1] - e2[1] * e1[0]);
		n.Normalize();
		float ny = n[1];
		if (ny < 0.5)
			return null; // too steep to hold snow
		DS_RoofTri t = new DS_RoofTri();
		t.m_Free = true;
		t.m_Shape = 2;
		int vx = gi % 4;
		int vz = gj % 4;
		t.m_Variant = vx.ToString() + vz.ToString();
		// a large piece takes the model whose texture covers about as many cells as its sides are long (up to the 4
		// cells of one texture period: beyond that the texture would visibly repeat inside the piece)
		float cells = Math.Max(vector.Distance(p0, q1), vector.Distance(p0, q2)) / Math.Max(b.m_StepU, 0.05);
		t.m_Span = 1;
		while (t.m_Span < 4 && cells > t.m_Span * 1.5)
			t.m_Span = t.m_Span * 2;
		t.m_P0 = p0;
		t.m_P1 = q1;
		t.m_P2 = q2;
		t.m_Normal = n;
		t.m_Center = (p0 + q1 + q2) * (1.0 / 3.0);
		if (ny < STEEP_NY)
			t.m_Drop = 1;
		b.m_Tris.Insert(t);
		return t;
	}

	//! a grid cell a surface ends in (the roof's rim, a chimney, a step). Its corners are grouped by the surface they
	//! lie on; every group gets the piece made of its corners and the points where its surface ends on the sides of
	//! the cell (marching squares), so the snow ends in a straight line at the rim or the wall
	protected void BuildEdgeCell(DS_RoofBuilding b, int i, int j, array<int> sgrp, array<bool> gridGroup)
	{
		int nu = b.m_NU;
		array<int> ci = {i, i + 1, i + 1, i};
		array<int> cj = {j, j, j + 1, j + 1};
		// the sides of the cell in walking order (corner k to corner k + 1): grid edge index, and whether the walk
		// runs from the edge's lower end to its upper end
		array<int> ee = {(j * nu + i) * 2, (j * nu + i + 1) * 2 + 1, ((j + 1) * nu + i) * 2, (j * nu + i) * 2 + 1};
		array<bool> fwd = {true, true, false, false};
		array<float> h = new array<float>;
		for (int k = 0; k < 4; k++)
			h.Insert(HAt(b, ci[k], cj[k]));
		array<int> grp = {-1, -1, -1, -1};
		for (int a = 0; a < 4; a++)
		{
			if (h[a] == NO_HIT || grp[a] >= 0)
				continue;
			grp[a] = a;
			for (int d = 1; d < 4; d++)
			{
				int pf = (a + d - 1) % 4;
				int cf = (a + d) % 4;
				if (grp[cf] >= 0 || !Joined(b, h[pf], h[cf]))
					break;
				grp[cf] = a;
			}
			for (int d2 = 1; d2 < 4; d2++)
			{
				int pb = (a - d2 + 5) % 4;
				int cb = (a - d2 + 4) % 4;
				if (grp[cb] >= 0 || !Joined(b, h[pb], h[cb]))
					break;
				grp[cb] = a;
			}
		}
		for (int g = 0; g < 4; g++)
		{
			if (grp[g] != g)
				continue;
			if (!GridSample(sgrp, gridGroup, cj[g] * nu + ci[g]))
				continue;
			array<vector> poly = new array<vector>;
			bool ok = true;
			for (int s = 0; s < 4; s++)
			{
				int n = (s + 1) % 4;
				bool inS = grp[s] == g;
				bool inN = grp[n] == g;
				if (inS)
					poly.Insert(CornerAt(b, ci[s], cj[s]));
				if (inS == inN)
					continue;
				// the group's surface ends on this side: the point found from its corner on the side
				int key = ee[s] * 2;
				if (inS != fwd[s])
					key++;
				vector x;
				if (!b.m_Cross.Find(key, x))
				{
					ok = false;
					break;
				}
				poly.Insert(x);
			}
			if (!ok)
				continue;
			for (int f = 1; f + 1 < poly.Count(); f++)
				AddFree(b, i, j, poly[0], poly[f], poly[f + 1]);
		}
	}

	protected bool FullCell(DS_RoofBuilding b, int i, int j)
	{
		float h00 = HAt(b, i, j);
		float h10 = HAt(b, i + 1, j);
		float h11 = HAt(b, i + 1, j + 1);
		float h01 = HAt(b, i, j + 1);
		if (h00 == NO_HIT || h10 == NO_HIT || h11 == NO_HIT || h01 == NO_HIT)
			return false;
		float lo = Math.Min(Math.Min(h00, h10), Math.Min(h11, h01));
		float hi = Math.Max(Math.Max(h00, h10), Math.Max(h11, h01));
		return hi - lo <= Math.Min(b.m_StepU, b.m_StepV) * 1.35;
	}

	protected bool BlockFree(array<bool> used, int nu, int i, int j, int span)
	{
		for (int a = 0; a < span; a++)
		{
			for (int c = 0; c < span; c++)
			{
				int idx = (j + c) * nu + i + a;
				if (used[idx])
					return false;
			}
		}
		return true;
	}

	//! every sample of the block lies on the plane through its corners
	protected bool BlockPlanar(DS_RoofBuilding b, int i, int j, int span)
	{
		for (int a = 0; a < span; a++)
		{
			for (int c = 0; c < span; c++)
			{
				if (!FullCell(b, i + a, j + c))
					return false;
			}
		}
		float c00 = HAt(b, i, j);
		float c20 = HAt(b, i + span, j);
		float c22 = HAt(b, i + span, j + span);
		float c02 = HAt(b, i, j + span);
		if (!Planar(c00, c20, c22, c02))
			return false;
		float inv = 1.0 / span;
		for (int pa = 0; pa <= span; pa++)
		{
			for (int pc = 0; pc <= span; pc++)
			{
				float expect = c00 + (c20 - c00) * (pa * inv) + (c02 - c00) * (pc * inv);
				float actual = HAt(b, i + pa, j + pc);
				if (Math.AbsFloat(actual - expect) > 0.05)
					return false;
			}
		}
		return true;
	}

	protected bool Planar(float h00, float h10, float h11, float h01)
	{
		return Math.AbsFloat(h00 + h11 - h10 - h01) <= 0.06;
	}

	//! adds one triangle: shape 0..3 like the ground cover over the square (gi, gj) of su by sv metres
	protected void AddTri(DS_RoofBuilding b, int shape, int gi, int gj, float su, float sv, float h00, float h10, float h11, float h01)
	{
		AddTriAt(b, shape, gi * b.m_StepU, gj * b.m_StepV, gi, gj, su, sv, h00, h10, h11, h01);
	}

	//! the same for a rectangle starting at (u0, v0) metres along the grid axes; vi, vj pick the texture variant
	protected void AddTriAt(DS_RoofBuilding b, int shape, float u0, float v0, int vi, int vj, float su, float sv, float h00, float h10, float h11, float h01)
	{
		float a;
		float bb;
		float yc;
		if (shape == 0)
		{
			a = (h10 - h00) / su;
			bb = (h11 - h10) / sv;
			yc = h00 + (a * su + bb * sv) * 0.5;
		}
		else if (shape == 1)
		{
			a = (h11 - h01) / su;
			bb = (h01 - h00) / sv;
			yc = h00 + (a * su + bb * sv) * 0.5;
		}
		else if (shape == 2)
		{
			a = (h10 - h00) / su;
			bb = (h01 - h00) / sv;
			yc = h00 + (a * su + bb * sv) * 0.5;
		}
		else
		{
			a = (h11 - h01) / su;
			bb = (h11 - h10) / sv;
			yc = h10 - a * su * 0.5 + bb * sv * 0.5;
		}

		DS_RoofTri t = new DS_RoofTri();
		t.m_Shape = shape;
		int vx = vi % 4;
		int vz = vj % 4;
		t.m_Variant = vx.ToString() + vz.ToString();
		vector c = b.m_Origin + b.m_U * (u0 + su * 0.5) + b.m_V * (v0 + sv * 0.5);
		t.m_Center = Vector(c[0], yc, c[2]);
		t.m_AxisU = b.m_U * su + Vector(0, a * su, 0);
		t.m_AxisV = b.m_V * sv + Vector(0, bb * sv, 0);
		t.m_Normal = (Vector(0, 1, 0) - b.m_U * a - b.m_V * bb).Normalized();
		float ny = t.m_Normal[1];
		if (ny < 0.5)
			return; // too steep to hold snow
		if (ny < STEEP_NY)
			t.m_Drop = 1;
		b.m_Tris.Insert(t);
	}

	protected void AddSquare(DS_RoofBuilding b, int gi, int gj, int span)
	{
		float su = b.m_StepU * span;
		float sv = b.m_StepV * span;
		float h00 = HAt(b, gi, gj);
		float h10 = HAt(b, gi + span, gj);
		float h11 = HAt(b, gi + span, gj + span);
		float h01 = HAt(b, gi, gj + span);
		// a flat square is one object
		if (Planar(h00, h10, h11, h01))
		{
			AddQuad(b, gi, gj, span, h00, h10, h11, h01);
			return;
		}
		// the higher diagonal keeps the snow on top of ridges instead of inside them
		if ((h00 + h11) >= (h10 + h01))
		{
			AddTri(b, 0, gi, gj, su, sv, h00, h10, h11, h01);
			AddTri(b, 1, gi, gj, su, sv, h00, h10, h11, h01);
		}
		else
		{
			AddTri(b, 2, gi, gj, su, sv, h00, h10, h11, h01);
			AddTri(b, 3, gi, gj, su, sv, h00, h10, h11, h01);
		}
	}

	//! one square of span x span grid cells on a plane (its corners within a few centimetres of one plane)
	protected void AddQuad(DS_RoofBuilding b, int gi, int gj, int span, float h00, float h10, float h11, float h01)
	{
		float su = b.m_StepU * span;
		float sv = b.m_StepV * span;
		float a = ((h10 - h00) + (h11 - h01)) * 0.5 / su;
		float bb = ((h01 - h00) + (h11 - h10)) * 0.5 / sv;
		DS_RoofTri t = new DS_RoofTri();
		t.m_Quad = true;
		t.m_Span = span;
		int vx = gi % 4;
		int vz = gj % 4;
		if (span >= 4)
		{
			vx = 0;
			vz = 0;
		}
		t.m_Variant = vx.ToString() + vz.ToString();
		vector c = b.m_Origin + b.m_U * (gi * b.m_StepU + su * 0.5) + b.m_V * (gj * b.m_StepV + sv * 0.5);
		t.m_Center = Vector(c[0], (h00 + h10 + h11 + h01) * 0.25, c[2]);
		t.m_AxisU = b.m_U * su + Vector(0, a * su, 0);
		t.m_AxisV = b.m_V * sv + Vector(0, bb * sv, 0);
		t.m_Normal = (Vector(0, 1, 0) - b.m_U * a - b.m_V * bb).Normalized();
		float ny = t.m_Normal[1];
		if (ny < 0.5)
			return; // too steep to hold snow
		if (ny < STEEP_NY)
			t.m_Drop = 1;
		// a square is larger than a triangle of the same cells: it grows by 2 centimetres, not by 3 percent
		t.m_Grow = 1.0 + Math.Min(0.03, 0.02 / Math.Max(Math.Min(su, sv), 0.1));
		b.m_Tris.Insert(t);
	}

	//! the grid is complete and its edges found: flat tops and plane roofs become polygons over the next frames
	//! (state 4), everything else is built right away (state 2)
	protected void BuildTris(DS_RoofBuilding b)
	{
		b.m_Tris.Clear();
		b.m_CapInfo = "";
		b.m_Job = null;
		if (b.m_Cross.Count() > 0 && (DS_State.s_DebugRoofCaps >= 2 || (DS_State.s_DebugRoofCaps == 1 && (b.m_Small || b.m_Wall))))
		{
			DS_CapJob job = new DS_CapJob();
			job.m_Groups = GroupSurfaces(b, job.m_Grp);
			for (int g = 0; g < job.m_Groups; g++)
			{
				job.m_GridGroup.Insert(true);
				job.m_Members.Insert(new array<int>);
			}
			int total = job.m_Grp.Count();
			for (int k = 0; k < total; k++)
			{
				int kg = job.m_Grp[k];
				if (kg >= 0)
					job.m_Members[kg].Insert(k);
			}
			b.m_Job = job;
			b.m_State = 4;
			return;
		}
		FinishTris(b);
	}

	//! grid pieces for the surfaces not drawn as polygons; then the ray grid is no longer needed
	protected void FinishTris(DS_RoofBuilding b)
	{
		array<int> sgrp = null;
		array<bool> gridGroup = null;
		if (b.m_Job)
		{
			sgrp = b.m_Job.m_Grp;
			gridGroup = b.m_Job.m_GridGroup;
			b.m_CapInfo = string.Format("groups %1 as polygons %2 planes %3", b.m_Job.m_Groups, b.m_Job.m_Ok, b.m_Job.m_PlanesUsed);
		}
		bool anyGrid = gridGroup == null;
		if (gridGroup)
		{
			foreach (bool left : gridGroup)
			{
				if (left)
					anyGrid = true;
			}
		}
		if (anyGrid)
		{
			// the rest of a wall keeps the plain grid pieces: cut to its edges, a long uneven top would multiply them
			if (b.m_Wall)
				b.m_Cross.Clear();
			BuildGridTris(b, sgrp, gridGroup);
		}
		b.m_Job = null;
		b.m_H.Clear();
		b.m_NY.Clear();
		b.m_EdgeKeys.Clear();
		b.m_Cross.Clear();
		b.m_State = 2;
		if (b.m_Kind == 1)
		{
			float length = Math.Max(b.m_NU * b.m_StepU, b.m_NV * b.m_StepV);
			b.m_Reach = WALL_RADIUS;
			if (b.m_Tris.Count() > DENSE_WALL * Math.Max(length, 1.0))
				b.m_Reach = DENSE_WALL_RADIUS;
		}
	}

	//! one step of a structure's polygons; true when they are all done
	protected bool CapStep(DS_RoofBuilding b)
	{
		DS_CapJob job = b.m_Job;
		if (!job || job.m_G >= job.m_Groups)
			return true;
		m_Cost += 0.5;
		int g = job.m_G;
		if (job.m_Phase == 0)
		{
			// the surface split into planes
			job.m_Sets = new array<ref map<int, bool>>;
			job.m_Lists = new array<ref array<int>>;
			job.m_Planes = new array<float>;
			job.m_RegOf = new map<int, int>;
			job.m_Polys = new array<ref array<float>>;
			bool split = SplitPlanes(b, job.m_Grp, g, job.m_Members[g], job.m_RegOf, job.m_Sets, job.m_Lists, job.m_Planes);
			if (!split || job.m_PlanesUsed + job.m_Sets.Count() > MAX_PLANES)
			{
				NextGroup(job);
				return false;
			}
			job.m_PlanesUsed += job.m_Sets.Count();
			job.m_R = 0;
			job.m_Phase = 1;
			return false;
		}
		if (job.m_Phase == 1)
		{
			int r = job.m_R;
			if (r < job.m_Sets.Count())
			{
				// the polygon of one plane
				array<float> hull = RegionHull(b, job.m_Grp, job.m_RegOf, job.m_Sets, job.m_Lists, job.m_Planes, r);
				if (!hull || hull.Count() < 6)
				{
					NextGroup(job);
					return false;
				}
				SimplifyHull(hull);
				if (hull.Count() < 6 || !HullClear(b, job.m_Sets[r], hull, job.m_Planes, r))
				{
					NextGroup(job);
					return false;
				}
				SquareCorners(b, hull, job.m_Planes, r);
				SimplifyHull(hull);
				job.m_Polys.Insert(hull);
				job.m_R++;
				return false;
			}
			// all planes done: the polygons have to cover the surface
			job.m_Holes = new array<int>;
			if (!Covered(b, job.m_Grp, g, job.m_Members[g], job.m_Polys, job.m_Holes))
			{
				NextGroup(job);
				return false;
			}
			job.m_GridGroup[g] = false;
			job.m_Ok++;
			job.m_R = 0;
			job.m_Phase = 2;
			return false;
		}
		// the pieces of one polygon: small structures and walls a few bands, buildings filled with grid pieces so
		// the texture continues like on the ground
		if (job.m_R < job.m_Polys.Count())
		{
			if (b.m_Small || b.m_Wall)
				EmitFan(b, job.m_Polys[job.m_R], job.m_Planes, job.m_R);
			else
				EmitCap(b, job.m_Polys[job.m_R], job.m_Planes, job.m_R);
			job.m_R++;
			return false;
		}
		// the few cells where three or four planes meet and the polygons leave a gap get their grid square
		foreach (int hk : job.m_Holes)
		{
			int hki = hk % b.m_NU;
			int hkj = hk / b.m_NU;
			AddSquare(b, hki, hkj, 1);
		}
		NextGroup(job);
		return false;
	}

	protected void NextGroup(DS_CapJob job)
	{
		job.m_G++;
		job.m_Phase = 0;
		job.m_R = 0;
		job.m_Sets = null;
		job.m_Lists = null;
		job.m_Planes = null;
		job.m_RegOf = null;
		job.m_Polys = null;
		job.m_Holes = null;
	}

	//! grid pieces only for the surfaces not drawn as polygons (all of them without a filter)
	protected bool GridSample(array<int> sgrp, array<bool> gridGroup, int k)
	{
		if (!gridGroup)
			return true;
		int g = sgrp[k];
		return g >= 0 && gridGroup[g];
	}

	//! the pieces of the ray grid: planar blocks as squares, the cells along the edges cut to where the roof ends
	protected void BuildGridTris(DS_RoofBuilding b, array<int> sgrp, array<bool> gridGroup)
	{
		int nu = b.m_NU - 1;
		int nv = b.m_NV - 1;
		array<bool> used = new array<bool>;
		used.Resize(nu * nv);
		for (int k = 0; k < nu * nv; k++)
			used[k] = false;

		// flat blocks on one plane become a single square: 8x8 first, then 4x4 and 2x2
		for (int pass = 0; pass < 3; pass++)
		{
			int span = 8;
			if (pass == 1)
				span = 4;
			else if (pass == 2)
				span = 2;
			if (span > DS_State.s_DebugRoofMaxSpan)
				continue;
			for (int j = 0; j + span <= nv; j += span)
			{
				for (int i = 0; i + span <= nu; i += span)
				{
					if (!BlockFree(used, nu, i, j, span) || !BlockPlanar(b, i, j, span) || !GridSample(sgrp, gridGroup, j * b.m_NU + i))
						continue;
					AddSquare(b, i, j, span);
					for (int ua = 0; ua < span; ua++)
					{
						for (int uc = 0; uc < span; uc++)
						{
							int ui = (j + uc) * nu + i + ua;
							used[ui] = true;
						}
					}
				}
			}
		}

		for (int jj = 0; jj < nv; jj++)
		{
			for (int ii = 0; ii < nu; ii++)
			{
				if (used[jj * nu + ii])
					continue;
				if (FullCell(b, ii, jj))
				{
					if (GridSample(sgrp, gridGroup, jj * b.m_NU + ii))
						AddSquare(b, ii, jj, 1);
					continue;
				}
				if (b.m_Cross.Count() > 0)
				{
					BuildEdgeCell(b, ii, jj, sgrp, gridGroup);
					continue;
				}
				// three roof corners: one triangle along the roof edge
				float h00 = HAt(b, ii, jj);
				float h10 = HAt(b, ii + 1, jj);
				float h11 = HAt(b, ii + 1, jj + 1);
				float h01 = HAt(b, ii, jj + 1);
				int missing = -1;
				int count = 0;
				if (h00 != NO_HIT) count++; else missing = 0;
				if (h10 != NO_HIT) count++; else missing = 1;
				if (h11 != NO_HIT) count++; else missing = 2;
				if (h01 != NO_HIT) count++; else missing = 3;
				if (count != 3)
					continue;
				int anyCorner = jj * b.m_NU + ii;
				if (missing == 0)
					anyCorner = jj * b.m_NU + ii + 1;
				if (!GridSample(sgrp, gridGroup, anyCorner))
					continue;
				float lo = 1000000;
				float hi = -1000000;
				if (h00 != NO_HIT) { lo = Math.Min(lo, h00); hi = Math.Max(hi, h00); }
				if (h10 != NO_HIT) { lo = Math.Min(lo, h10); hi = Math.Max(hi, h10); }
				if (h11 != NO_HIT) { lo = Math.Min(lo, h11); hi = Math.Max(hi, h11); }
				if (h01 != NO_HIT) { lo = Math.Min(lo, h01); hi = Math.Max(hi, h01); }
				float stepMin = Math.Min(b.m_StepU, b.m_StepV);
				if (hi - lo > stepMin * 1.35)
					continue;
				if (missing == 0)
					AddTri(b, 3, ii, jj, b.m_StepU, b.m_StepV, h10, h10, h11, h01);
				else if (missing == 1)
					AddTri(b, 1, ii, jj, b.m_StepU, b.m_StepV, h00, h00, h11, h01);
				else if (missing == 2)
					AddTri(b, 2, ii, jj, b.m_StepU, b.m_StepV, h00, h10, h00, h01);
				else
					AddTri(b, 0, ii, jj, b.m_StepU, b.m_StepV, h00, h10, h11, h00);
			}
		}
	}

	//! test harness: a sample as world position and height above the ground
	protected string CapSample(DS_RoofBuilding b, int k)
	{
		vector p = b.m_Origin + b.m_U * SU(b, k) + b.m_V * SV(b, k);
		return string.Format("%1 %2 h=%3", p[0], p[2], b.m_H[k] - b.m_Ground);
	}

	//! the polygons of walls and small structures: cut into bands across their long side, at least a metre and no
	//! more than three times as long as wide, so the snow texture is stretched no more than on the grid pieces. A band
	//! that is a whole rectangle becomes two pieces with one texture mapping, the bands at the ends a fan
	protected void EmitFan(DS_RoofBuilding b, array<float> poly, array<float> planes, int p)
	{
		int pn = poly.Count() / 2;
		float minU = 1000000;
		float maxU = -1000000;
		float minV = 1000000;
		float maxV = -1000000;
		for (int h = 0; h < pn; h++)
		{
			minU = Math.Min(minU, poly[h * 2]);
			maxU = Math.Max(maxU, poly[h * 2]);
			minV = Math.Min(minV, poly[h * 2 + 1]);
			maxV = Math.Max(maxV, poly[h * 2 + 1]);
		}
		bool alongU = (maxU - minU) >= (maxV - minV);
		float longExt = Math.Max(maxU - minU, maxV - minV);
		float shortExt = Math.Min(maxU - minU, maxV - minV);
		int n = Math.Ceil(longExt / Math.Max(1.0, shortExt * 3.0));
		if (n < 1)
			n = 1;
		if (n > 16)
			n = 16;
		float step = longExt / n;
		for (int k = 0; k < n; k++)
		{
			float u0 = minU;
			float u1 = maxU;
			float v0 = minV;
			float v1 = maxV;
			if (alongU)
			{
				u0 = minU + k * step;
				u1 = u0 + step;
			}
			else
			{
				v0 = minV + k * step;
				v1 = v0 + step;
			}
			array<float> piece = ClipCell(poly, u0, v0, u1, v1);
			int qn = piece.Count() / 2;
			if (qn < 3)
				continue;
			if (qn == 4 && IsRect(piece, u0, v0, u1, v1))
			{
				float su = u1 - u0;
				float sv = v1 - v0;
				float h00 = PlaneH(planes, p, u0, v0);
				float h10 = PlaneH(planes, p, u1, v0);
				float h11 = PlaneH(planes, p, u1, v1);
				float h01 = PlaneH(planes, p, u0, v1);
				AddTriAt(b, 0, u0, v0, k, p, su, sv, h00, h10, h11, h01);
				AddTriAt(b, 1, u0, v0, k, p, su, sv, h00, h10, h11, h01);
				continue;
			}
			vector w0 = CapPoint(b, piece[0], piece[1], planes, p);
			for (int f = 1; f + 1 < qn; f++)
			{
				vector w1 = CapPoint(b, piece[f * 2], piece[f * 2 + 1], planes, p);
				vector w2 = CapPoint(b, piece[f * 2 + 2], piece[f * 2 + 3], planes, p);
				DS_RoofTri t = AddFree(b, k, p, w0, w1, w2);
				if (!t)
					continue;
				// large pieces overlap their neighbours by a centimetre or two, not by 3 percent
				float longest = Math.Max(vector.Distance(w0, w1), Math.Max(vector.Distance(w1, w2), vector.Distance(w2, w0)));
				t.m_Grow = 1.0 + Math.Min(0.03, 0.02 / Math.Max(longest, 0.1));
			}
		}
	}

	//! a clipped piece is the whole rectangle (its four corners, within a millimetre)
	protected bool IsRect(array<float> piece, float u0, float v0, float u1, float v1)
	{
		for (int k = 0; k < 4; k++)
		{
			float pu = piece[k * 2];
			float pv = piece[k * 2 + 1];
			bool onU = Math.AbsFloat(pu - u0) < 0.001 || Math.AbsFloat(pu - u1) < 0.001;
			bool onV = Math.AbsFloat(pv - v0) < 0.001 || Math.AbsFloat(pv - v1) < 0.001;
			if (!onU || !onV)
				return false;
		}
		return true;
	}

	//! fills a polygon with pieces: the 2x2 cell blocks its edge runs through become the part of the block inside it
	//! (a fan of a few triangles), the cells wholly inside become squares on its plane, joined into squares of 8, 4
	//! and 2 cells on the grid where they can (the texture runs on across all of them, like on the ground). Straight
	//! rims, exact ridges and hips, and few objects
	protected void EmitCap(DS_RoofBuilding b, array<float> poly, array<float> planes, int p)
	{
		int ncu = b.m_NU - 1;
		int ncv = b.m_NV - 1;
		int pn = poly.Count() / 2;
		float minU = 1000000;
		float maxU = -1000000;
		float minV = 1000000;
		float maxV = -1000000;
		for (int h = 0; h < pn; h++)
		{
			minU = Math.Min(minU, poly[h * 2]);
			maxU = Math.Max(maxU, poly[h * 2]);
			minV = Math.Min(minV, poly[h * 2 + 1]);
			maxV = Math.Max(maxV, poly[h * 2 + 1]);
		}
		int i0 = Math.Floor(minU / b.m_StepU);
		int i1 = Math.Floor(maxU / b.m_StepU);
		int j0 = Math.Floor(minV / b.m_StepV);
		int j1 = Math.Floor(maxV / b.m_StepV);
		if (i0 < 0)
			i0 = 0;
		if (j0 < 0)
			j0 = 0;
		if (i1 > ncu - 1)
			i1 = ncu - 1;
		if (j1 > ncv - 1)
			j1 = ncv - 1;
		if (i1 < i0 || j1 < j0)
			return;
		// the range starts on a block boundary, so the blocks lie on the grid
		int eb = DS_State.s_DebugEdgeBlock;
		if (eb < 1)
			eb = 1;
		i0 = i0 - (i0 % eb);
		j0 = j0 - (j0 % eb);
		int wu = i1 - i0 + 1;
		int wv = j1 - j0 + 1;
		// which cells lie wholly inside (their four corners inside the convex polygon)
		array<bool> inside = new array<bool>;
		array<bool> used = new array<bool>;
		for (int j = j0; j <= j1; j++)
		{
			for (int i = i0; i <= i1; i++)
			{
				float cu0 = i * b.m_StepU;
				float cv0 = j * b.m_StepV;
				float cu1 = cu0 + b.m_StepU;
				float cv1 = cv0 + b.m_StepV;
				bool all = InPoly(poly, cu0, cv0, -0.002) && InPoly(poly, cu1, cv0, -0.002) && InPoly(poly, cu1, cv1, -0.002) && InPoly(poly, cu0, cv1, -0.002);
				inside.Insert(all);
				used.Insert(false);
			}
		}
		// the blocks the edge runs through: the part of the block inside the polygon
		for (int ej = j0; ej <= j1; ej += eb)
		{
			for (int ei = i0; ei <= i1; ei += eb)
			{
				bool whole = true;
				for (int ea = 0; ea < eb && whole; ea++)
				{
					for (int ec = 0; ec < eb && whole; ec++)
					{
						int ci = ei + ea;
						int cj = ej + ec;
						if (ci > i1 || cj > j1 || !inside[(cj - j0) * wu + (ci - i0)])
							whole = false;
					}
				}
				if (whole)
					continue;
				for (int ma = 0; ma < eb; ma++)
				{
					for (int mc = 0; mc < eb; mc++)
					{
						int mi = ei + ma;
						int mj = ej + mc;
						if (mi > i1 || mj > j1)
							continue;
						int lm = (mj - j0) * wu + (mi - i0);
						used[lm] = true;
					}
				}
				array<float> piece = ClipCell(poly, ei * b.m_StepU, ej * b.m_StepV, (ei + eb) * b.m_StepU, (ej + eb) * b.m_StepV);
				int qn = piece.Count() / 2;
				if (qn < 3)
					continue;
				vector w0 = CapPoint(b, piece[0], piece[1], planes, p);
				for (int f = 1; f + 1 < qn; f++)
				{
					vector w1 = CapPoint(b, piece[f * 2], piece[f * 2 + 1], planes, p);
					vector w2 = CapPoint(b, piece[f * 2 + 2], piece[f * 2 + 3], planes, p);
					AddFree(b, ei, ej, w0, w1, w2);
				}
			}
		}
		// squares of whole cells on the plane: 8x8, 4x4, 2x2, then single cells (on the grid)
		for (int pass = 0; pass < 4; pass++)
		{
			int span = 8;
			if (pass == 1)
				span = 4;
			else if (pass == 2)
				span = 2;
			else if (pass == 3)
				span = 1;
			if (span > DS_State.s_DebugRoofMaxSpan)
				continue;
			int bi0 = Math.Ceil(i0 / (span * 1.0)) * span;
			int bj0 = Math.Ceil(j0 / (span * 1.0)) * span;
			for (int bj = bj0; bj + span - 1 <= j1; bj += span)
			{
				for (int bi = bi0; bi + span - 1 <= i1; bi += span)
				{
					bool free = true;
					for (int sa = 0; sa < span && free; sa++)
					{
						for (int sc = 0; sc < span && free; sc++)
						{
							int li = (bj + sc - j0) * wu + (bi + sa - i0);
							if (!inside[li] || used[li])
								free = false;
						}
					}
					if (!free)
						continue;
					PlaneSquare(b, bi, bj, span, planes, p);
					for (int ua = 0; ua < span; ua++)
					{
						for (int uc = 0; uc < span; uc++)
						{
							int lu = (bj + uc - j0) * wu + (bi + ua - i0);
							used[lu] = true;
						}
					}
				}
			}
		}
	}

	//! a square of span x span grid cells lying on plane p
	protected void PlaneSquare(DS_RoofBuilding b, int gi, int gj, int span, array<float> planes, int p)
	{
		float su = b.m_StepU * span;
		float sv = b.m_StepV * span;
		float u0 = gi * b.m_StepU;
		float v0 = gj * b.m_StepV;
		float h00 = PlaneH(planes, p, u0, v0);
		float h10 = PlaneH(planes, p, u0 + su, v0);
		float h11 = PlaneH(planes, p, u0 + su, v0 + sv);
		float h01 = PlaneH(planes, p, u0, v0 + sv);
		AddQuad(b, gi, gj, span, h00, h10, h11, h01);
	}

	//! the part of a grid cell inside a convex counter-clockwise polygon (Sutherland-Hodgman), as u, v pairs
	protected array<float> ClipCell(array<float> poly, float u0, float v0, float u1, float v1)
	{
		array<float> cur = {u0, v0, u1, v0, u1, v1, u0, v1};
		int n = poly.Count() / 2;
		for (int e = 0; e < n && cur.Count() >= 6; e++)
		{
			int e2 = (e + 1) % n;
			float ax = poly[e * 2];
			float az = poly[e * 2 + 1];
			float lx = poly[e2 * 2] - ax;
			float lz = poly[e2 * 2 + 1] - az;
			array<float> next = new array<float>;
			int m = cur.Count() / 2;
			for (int k = 0; k < m; k++)
			{
				int k2 = (k + 1) % m;
				float pu = cur[k * 2];
				float pv = cur[k * 2 + 1];
				float qu = cur[k2 * 2];
				float qv = cur[k2 * 2 + 1];
				float dp = lx * (pv - az) - lz * (pu - ax);
				float dq = lx * (qv - az) - lz * (qu - ax);
				if (dp >= 0)
				{
					next.Insert(pu);
					next.Insert(pv);
				}
				if ((dp >= 0) != (dq >= 0))
				{
					float t = dp / (dp - dq);
					next.Insert(pu + (qu - pu) * t);
					next.Insert(pv + (qv - pv) * t);
				}
			}
			cur = next;
		}
		return cur;
	}

	//! labels every sample on the object with the surface it belongs to: neighbours joined without a step share one.
	//! Returns the number of surfaces
	protected int GroupSurfaces(DS_RoofBuilding b, array<int> grp)
	{
		int nu = b.m_NU;
		int nv = b.m_NV;
		int total = nu * nv;
		grp.Clear();
		for (int k = 0; k < total; k++)
			grp.Insert(-1);
		int groups = 0;
		array<int> todo = new array<int>;
		for (int s = 0; s < total; s++)
		{
			if (grp[s] >= 0 || b.m_H[s] == NO_HIT)
				continue;
			grp[s] = groups;
			todo.Insert(s);
			while (todo.Count() > 0)
			{
				int cur = todo[todo.Count() - 1];
				todo.Remove(todo.Count() - 1);
				int ci = cur % nu;
				int cj = cur / nu;
				for (int d = 0; d < 4; d++)
				{
					int ni = ci;
					int nj = cj;
					if (d == 0)
						ni++;
					else if (d == 1)
						ni--;
					else if (d == 2)
						nj++;
					else
						nj--;
					if (ni < 0 || nj < 0 || ni >= nu || nj >= nv)
						continue;
					int nidx = nj * nu + ni;
					if (grp[nidx] >= 0 || !Joined(b, b.m_H[cur], b.m_H[nidx]))
						continue;
					grp[nidx] = groups;
					todo.Insert(nidx);
				}
			}
			groups++;
		}
		return groups;
	}

	protected float SU(DS_RoofBuilding b, int k)
	{
		int i = k % b.m_NU;
		return i * b.m_StepU;
	}

	protected float SV(DS_RoofBuilding b, int k)
	{
		int j = k / b.m_NU;
		return j * b.m_StepV;
	}

	//! height of plane r (h0 at its centre cu, cv, slopes gu and gv along the grid axes) at a grid point
	protected float PlaneH(array<float> planes, int r, float u, float v)
	{
		return planes[r * 5] + planes[r * 5 + 1] * (u - planes[r * 5 + 3]) + planes[r * 5 + 2] * (v - planes[r * 5 + 4]);
	}

	//! least squares plane through samples: height h0 at their centre (cu, cv), slopes gu and gv along the grid
	//! axes. Returns how far the furthest sample lies from it
	protected float FitSamples(DS_RoofBuilding b, array<int> list, out float h0, out float gu, out float gv, out float cu, out float cv)
	{
		float n = 0;
		float su = 0;
		float sv = 0;
		float sh = 0;
		foreach (int k : list)
		{
			n += 1.0;
			su += SU(b, k);
			sv += SV(b, k);
			sh += b.m_H[k];
		}
		cu = su / n;
		cv = sv / n;
		h0 = sh / n;
		float suu = 0;
		float svv = 0;
		float suv = 0;
		float suh = 0;
		float svh = 0;
		foreach (int m : list)
		{
			float du = SU(b, m) - cu;
			float dv = SV(b, m) - cv;
			float dh = b.m_H[m] - h0;
			suu += du * du;
			svv += dv * dv;
			suv += du * dv;
			suh += du * dh;
			svh += dv * dh;
		}
		gu = 0;
		gv = 0;
		float det = suu * svv - suv * suv;
		if (det > 0.01 * (suu + svv) * (suu + svv) && det > 0.000001)
		{
			gu = (suh * svv - svh * suv) / det;
			gv = (svh * suu - suh * suv) / det;
		}
		else if (suu >= svv && suu > 0.0001)
		{
			gu = suh / suu;
		}
		else if (svv > 0.0001)
		{
			gv = svh / svv;
		}
		float worst = 0;
		foreach (int q : list)
		{
			float err = Math.AbsFloat(b.m_H[q] - (h0 + gu * (SU(b, q) - cu) + gv * (SV(b, q) - cv)));
			if (err > worst)
				worst = err;
		}
		return worst;
	}

	protected void AddRegion(array<int> list, map<int, int> regOf, array<ref map<int, bool>> sets, array<ref array<int>> lists, array<float> planes, float h0, float gu, float gv, float cu, float cv)
	{
		int r = sets.Count();
		map<int, bool> own = new map<int, bool>;
		array<int> keep = new array<int>;
		foreach (int k : list)
		{
			own.Set(k, true);
			keep.Insert(k);
			if (!regOf.Contains(k))
				regOf.Set(k, r);
		}
		sets.Insert(own);
		lists.Insert(keep);
		planes.Insert(h0);
		planes.Insert(gu);
		planes.Insert(gv);
		planes.Insert(cu);
		planes.Insert(cv);
	}

	//! splits one surface into planes: a flat or evenly sloped surface is one; otherwise the planar grid cells grow
	//! into regions of equal slope, and every other sample joins the plane it lies on. False when a sample lies on
	//! none (a curved surface)
	protected bool SplitPlanes(DS_RoofBuilding b, array<int> grp, int g, array<int> mine, map<int, int> regOf, array<ref map<int, bool>> sets, array<ref array<int>> lists, array<float> planes)
	{
		int nu = b.m_NU;
		int nv = b.m_NV;
		float h0;
		float gu;
		float gv;
		float cu;
		float cv;
		if (FitSamples(b, mine, h0, gu, gv, cu, cv) <= CAP_FLAT)
		{
			AddRegion(mine, regOf, sets, lists, planes, h0, gu, gv, cu, cv);
			return true;
		}
		if (mine.Count() < 4)
			return false;
		// planar cells (keyed by their first corner) and their slopes
		map<int, int> cellState = new map<int, int>;
		map<int, float> cgu = new map<int, float>;
		map<int, float> cgv = new map<int, float>;
		foreach (int k : mine)
		{
			int ki = k % nu;
			int kj = k / nu;
			if (ki + 1 >= nu || kj + 1 >= nv)
				continue;
			int k10 = k + 1;
			int k01 = k + nu;
			int k11 = k01 + 1;
			if (grp[k10] != g || grp[k01] != g || grp[k11] != g)
				continue;
			float a00 = b.m_H[k];
			float a10 = b.m_H[k10];
			float a01 = b.m_H[k01];
			float a11 = b.m_H[k11];
			if (Math.AbsFloat(a00 + a11 - a10 - a01) > CAP_FLAT)
				continue;
			cellState.Set(k, -1);
			cgu.Set(k, ((a10 - a00) + (a11 - a01)) / (2.0 * b.m_StepU));
			cgv.Set(k, ((a01 - a00) + (a11 - a10)) / (2.0 * b.m_StepV));
		}
		// candidate planes: regions of equal slope grown from each planar cell not taken yet
		array<ref array<int>> cands = new array<ref array<int>>;
		array<float> cpl = new array<float>;
		array<int> todo = new array<int>;
		for (int s = 0; s < cellState.Count(); s++)
		{
			int seed = cellState.GetKey(s);
			if (cellState.Get(seed) != -1)
				continue;
			float su0 = cgu.Get(seed);
			float sv0 = cgv.Get(seed);
			array<int> cellsOf = new array<int>;
			cellState.Set(seed, 1);
			todo.Insert(seed);
			while (todo.Count() > 0)
			{
				int cur = todo[todo.Count() - 1];
				todo.Remove(todo.Count() - 1);
				cellsOf.Insert(cur);
				int curI = cur % nu;
				for (int d = 0; d < 4; d++)
				{
					int nc = cur + 1;
					if (d == 1)
					{
						if (curI == 0)
							continue;
						nc = cur - 1;
					}
					else if (d == 2)
						nc = cur + nu;
					else if (d == 3)
						nc = cur - nu;
					int st;
					if (!cellState.Find(nc, st) || st != -1)
						continue;
					if (Math.AbsFloat(cgu.Get(nc) - su0) > 0.06 || Math.AbsFloat(cgv.Get(nc) - sv0) > 0.06)
						continue;
					cellState.Set(nc, 1);
					todo.Insert(nc);
				}
			}
			if (cellsOf.Count() < 2)
				continue;
			// the corners of its cells, less those off its plane (the far corners of a cell across a ridge)
			map<int, bool> seen = new map<int, bool>;
			array<int> corners = new array<int>;
			foreach (int cc : cellsOf)
			{
				for (int e = 0; e < 4; e++)
				{
					int q = cc;
					if (e == 1)
						q = cc + 1;
					else if (e == 2)
						q = cc + nu;
					else if (e == 3)
						q = cc + nu + 1;
					if (seen.Contains(q))
						continue;
					seen.Set(q, true);
					corners.Insert(q);
				}
			}
			FitSamples(b, corners, h0, gu, gv, cu, cv);
			array<int> keep = new array<int>;
			foreach (int q2 : corners)
			{
				if (Math.AbsFloat(b.m_H[q2] - (h0 + gu * (SU(b, q2) - cu) + gv * (SV(b, q2) - cv))) <= CAP_FLAT)
					keep.Insert(q2);
			}
			if (keep.Count() < 3)
				continue;
			if (FitSamples(b, keep, h0, gu, gv, cu, cv) > CAP_FLAT)
				continue;
			cands.Insert(keep);
			cpl.Insert(h0);
			cpl.Insert(gu);
			cpl.Insert(gv);
			cpl.Insert(cu);
			cpl.Insert(cv);
		}
		// neighbouring candidates on one plane (a roof plane split by a chimney or by the noise of its slope) are
		// joined: overlapping polygons of one plane would fight over the same pixels. The pairs of candidates that
		// share or touch a sample are found once, then joined with union-find
		array<bool> drop = new array<bool>;
		array<int> parent = new array<int>;
		for (int c0 = 0; c0 < cands.Count(); c0++)
		{
			drop.Insert(false);
			parent.Insert(c0);
		}
		map<int, ref array<int>> owners = new map<int, ref array<int>>;
		for (int uc = 0; uc < cands.Count(); uc++)
		{
			foreach (int us0 : cands[uc])
			{
				array<int> ul0;
				if (!owners.Find(us0, ul0))
				{
					ul0 = new array<int>;
					owners.Set(us0, ul0);
				}
				ul0.Insert(uc);
			}
		}
		map<int, bool> pairSeen = new map<int, bool>;
		array<int> pairA = new array<int>;
		array<int> pairB = new array<int>;
		for (int uq = 0; uq < cands.Count(); uq++)
		{
			foreach (int us : cands[uq])
			{
				int usi = us % nu;
				for (int ud = 0; ud < 5; ud++)
				{
					int un = us;
					if (ud == 1)
					{
						if (usi + 1 >= nu)
							continue;
						un = us + 1;
					}
					else if (ud == 2)
					{
						if (usi == 0)
							continue;
						un = us - 1;
					}
					else if (ud == 3)
						un = us + nu;
					else if (ud == 4)
						un = us - nu;
					array<int> ul;
					if (!owners.Find(un, ul))
						continue;
					foreach (int uq2 : ul)
					{
						if (uq2 <= uq)
							continue;
						int ukey = uq * 4096 + uq2;
						if (pairSeen.Contains(ukey))
							continue;
						pairSeen.Set(ukey, true);
						pairA.Insert(uq);
						pairB.Insert(uq2);
					}
				}
			}
		}
		for (int up2 = 0; up2 < pairA.Count(); up2++)
		{
			int ra = UnionRoot(parent, pairA[up2]);
			int rb = UnionRoot(parent, pairB[up2]);
			if (ra == rb)
				continue;
			array<int> both = new array<int>;
			map<int, bool> inBoth = new map<int, bool>;
			foreach (int b1 : cands[ra])
			{
				inBoth.Set(b1, true);
				both.Insert(b1);
			}
			foreach (int b2 : cands[rb])
			{
				if (!inBoth.Contains(b2))
					both.Insert(b2);
			}
			if (FitSamples(b, both, h0, gu, gv, cu, cv) > CAP_FLAT)
				continue;
			parent[rb] = ra;
			cands[ra] = both;
			cpl[ra * 5] = h0;
			cpl[ra * 5 + 1] = gu;
			cpl[ra * 5 + 2] = gv;
			cpl[ra * 5 + 3] = cu;
			cpl[ra * 5 + 4] = cv;
			drop[rb] = true;
		}
		// a candidate whose samples all lie on other candidates' planes, but not all on one of them, is the strip of
		// cells across a ridge or a valley: dropped (the smallest first)
		array<int> order = new array<int>;
		for (int c = 0; c < cands.Count(); c++)
		{
			if (drop[c])
				continue;
			int pos = order.Count();
			while (pos > 0 && cands[order[pos - 1]].Count() > cands[c].Count())
				pos--;
			order.InsertAt(c, pos);
		}
		foreach (int oc : order)
		{
			bool allOn = true;
			map<int, bool> hosts = new map<int, bool>;
			foreach (int q3 : cands[oc])
			{
				int host = -1;
				for (int o = 0; o < cands.Count(); o++)
				{
					if (o == oc || drop[o])
						continue;
					if (Math.AbsFloat(b.m_H[q3] - PlaneH(cpl, o, SU(b, q3), SV(b, q3))) <= CAP_FLAT)
					{
						host = o;
						break;
					}
				}
				if (host < 0)
				{
					allOn = false;
					break;
				}
				hosts.Set(host, true);
			}
			if (allOn && hosts.Count() >= 2)
				drop[oc] = true;
		}
		for (int c2 = 0; c2 < cands.Count(); c2++)
		{
			if (drop[c2])
				continue;
			AddRegion(cands[c2], regOf, sets, lists, planes, cpl[c2 * 5], cpl[c2 * 5 + 1], cpl[c2 * 5 + 2], cpl[c2 * 5 + 3], cpl[c2 * 5 + 4]);
			if (DS_State.s_DebugCapLog)
				Print(string.Format("[DSTest] capplane %1 samples=%2 slopes %3 %4", sets.Count() - 1, cands[c2].Count(), cpl[c2 * 5 + 1], cpl[c2 * 5 + 2]));
		}
		// the other samples: those on a neighbouring plane are its edge (a hip or a ridge runs through them; the
		// polygons reach them), the rest (chimney tops, small parts) form planes of their own
		array<int> loose = new array<int>;
		foreach (int k2 : mine)
		{
			if (regOf.Contains(k2))
				continue;
			if (OnNeighbourPlane(b, k2, regOf, planes) < 0)
				loose.Insert(k2);
		}
		if (loose.Count() > 0)
		{
			map<int, bool> looseSet = new map<int, bool>;
			foreach (int l0 : loose)
				looseSet.Set(l0, true);
			foreach (int l1 : loose)
			{
				if (regOf.Contains(l1))
					continue;
				array<int> part = new array<int>;
				map<int, bool> inPart = new map<int, bool>;
				inPart.Set(l1, true);
				todo.Insert(l1);
				while (todo.Count() > 0)
				{
					int pc = todo[todo.Count() - 1];
					todo.Remove(todo.Count() - 1);
					part.Insert(pc);
					int pci = pc % nu;
					for (int d2 = 0; d2 < 4; d2++)
					{
						int pn = pc + 1;
						if (d2 == 0 && pci + 1 >= nu)
							continue;
						if (d2 == 1)
						{
							if (pci == 0)
								continue;
							pn = pc - 1;
						}
						else if (d2 == 2)
							pn = pc + nu;
						else if (d2 == 3)
							pn = pc - nu;
						if (!looseSet.Contains(pn) || inPart.Contains(pn) || !Joined(b, b.m_H[pc], b.m_H[pn]))
							continue;
						inPart.Set(pn, true);
						todo.Insert(pn);
					}
				}
				if (FitSamples(b, part, h0, gu, gv, cu, cv) > CAP_FLAT)
				{
					if (DS_State.s_DebugCapLog)
						Print(string.Format("[DSTest] capsplit uneven part of %1 samples at %2", part.Count(), CapSample(b, part[0])));
					return false;
				}
				AddRegion(part, regOf, sets, lists, planes, h0, gu, gv, cu, cv);
				if (DS_State.s_DebugCapLog)
					Print(string.Format("[DSTest] capplane %1 small part samples=%2 at %3", sets.Count() - 1, part.Count(), CapSample(b, part[0])));
			}
		}
		return sets.Count() > 0;
	}

	//! union-find: the root of a candidate, with path halving
	protected int UnionRoot(array<int> parent, int c)
	{
		while (parent[c] != c)
		{
			parent[c] = parent[parent[c]];
			c = parent[c];
		}
		return c;
	}

	//! where plane r ends between a sample on it and a neighbour off it, found with rays (a step: a chimney, the wall
	//! of a dormer, the drop to a lower part)
	protected void PlaneEnd(DS_RoofBuilding b, float uk, float vk, float un, float vn, array<float> planes, int r, out float eu, out float ev)
	{
		m_PlaneEnds++;
		float lo = 0;
		float up = 1;
		for (int k = 0; k < EDGE_STEPS; k++)
		{
			float mid = (lo + up) * 0.5;
			float mu = uk + (un - uk) * mid;
			float mv = vk + (vn - vk) * mid;
			vector w = b.m_Origin + b.m_U * mu + b.m_V * mv;
			float expect = PlaneH(planes, r, mu, mv);
			float hm = SampleNear(b, w[0], w[2], expect, 1.5, 0.3);
			if (hm != NO_HIT && Math.AbsFloat(hm - expect) <= 0.05)
				lo = mid;
			else
				up = mid;
		}
		eu = uk + (un - uk) * up;
		ev = vk + (vn - vk) * up;
	}

	//! the highest point of the structure on a short vertical span around a height (NO_HIT when there is none): a
	//! test whether a surface continues where a plane predicts it, at half the cost of a ray through the building
	protected float SampleNear(DS_RoofBuilding b, float x, float z, float expect, float above, float below)
	{
		RaycastRVParams rp = new RaycastRVParams(Vector(x, expect + above, z), Vector(x, expect - below, z), null, 0);
		rp.type = ObjIntersectFire;
		rp.flags = CollisionFlags.ALLOBJECTS;
		rp.sorted = false;
		array<ref RaycastRVResult> results = new array<ref RaycastRVResult>;
		m_Rays++;
		m_Cost += 0.02;
		if (!DayZPhysics.RaycastRVProxy(rp, results))
			return NO_HIT;
		float h = NO_HIT;
		foreach (RaycastRVResult res : results)
		{
			Object hit = res.obj;
			if (res.parent)
				hit = res.parent;
			if (hit == b.m_Obj && res.pos[1] > h)
				h = res.pos[1];
		}
		return h;
	}

	//! the plane of a neighbour (of the same surface) that a sample lies on, or -1
	protected int OnNeighbourPlane(DS_RoofBuilding b, int k, map<int, int> regOf, array<float> planes)
	{
		int nu = b.m_NU;
		int ki = k % nu;
		int best = -1;
		float bestErr = CAP_FLAT * 1.5;
		for (int d = 0; d < 4; d++)
		{
			int nb = k + 1;
			if (d == 0 && ki + 1 >= nu)
				continue;
			if (d == 1)
			{
				if (ki == 0)
					continue;
				nb = k - 1;
			}
			else if (d == 2)
				nb = k + nu;
			else if (d == 3)
				nb = k - nu;
			int rq;
			if (!regOf.Find(nb, rq))
				continue;
			float err = Math.AbsFloat(b.m_H[k] - PlaneH(planes, rq, SU(b, k), SV(b, k)));
			if (err <= bestErr)
			{
				bestErr = err;
				best = rq;
			}
		}
		return best;
	}

	//! the convex hull of a plane's samples and the points where it ends towards each neighbour that is not on it:
	//! the edge point found by the rays (rim, step), or where it meets the neighbour's plane (ridge, hip, valley)
	protected array<float> RegionHull(DS_RoofBuilding b, array<int> grp, map<int, int> regOf, array<ref map<int, bool>> sets, array<ref array<int>> lists, array<float> planes, int r)
	{
		int nu = b.m_NU;
		int nv = b.m_NV;
		map<int, bool> own = sets[r];
		array<float> pu = new array<float>;
		array<float> pv = new array<float>;
		foreach (int k : lists[r])
		{
			int i = k % nu;
			int j = k / nu;
			// a sample with all four neighbours on the plane lies inside its polygon: only the border counts
			if (i > 0 && j > 0 && i + 1 < nu && j + 1 < nv && own.Contains(k + 1) && own.Contains(k - 1) && own.Contains(k + nu) && own.Contains(k - nu))
				continue;
			float uk = i * b.m_StepU;
			float vk = j * b.m_StepV;
			pu.Insert(uk);
			pv.Insert(vk);
			for (int d = 0; d < 4; d++)
			{
				int ni = i;
				int nj = j;
				int key;
				if (d == 0)
				{
					ni = i + 1;
					key = (j * nu + i) * 4;
				}
				else if (d == 1)
				{
					ni = i - 1;
					key = (j * nu + i - 1) * 4 + 1;
				}
				else if (d == 2)
				{
					nj = j + 1;
					key = ((j * nu + i) * 2 + 1) * 2;
				}
				else
				{
					nj = j - 1;
					key = (((j - 1) * nu + i) * 2 + 1) * 2 + 1;
				}
				if (ni < 0 || nj < 0 || ni >= nu || nj >= nv)
					continue;
				int n = nj * nu + ni;
				if (own.Contains(n))
					continue;
				if (grp[n] != grp[k])
				{
					vector c;
					if (!b.m_Cross.Find(key, c))
						return null;
					vector rel = c - b.m_Origin;
					pu.Insert(rel[0] * b.m_U[0] + rel[2] * b.m_U[2]);
					pv.Insert(rel[0] * b.m_V[0] + rel[2] * b.m_V[2]);
					continue;
				}
				// the same surface on another plane, or a sample on no plane (on a hip or a ridge)
				float un = ni * b.m_StepU;
				float vn = nj * b.m_StepV;
				int q;
				if (!regOf.Find(n, q))
				{
					if (Math.AbsFloat(b.m_H[n] - PlaneH(planes, r, un, vn)) <= CAP_FLAT * 1.5)
					{
						pu.Insert(un);
						pv.Insert(vn);
						continue;
					}
					// the sample lies on the plane of one of its neighbours: where the two planes meet, as below
					q = OnNeighbourPlane(b, n, regOf, planes);
					if (q < 0 || q == r)
					{
						float fu;
						float fv;
						PlaneEnd(b, uk, vk, un, vn, planes, r, fu, fv);
						pu.Insert(fu);
						pv.Insert(fv);
						continue;
					}
				}
				if (q == r)
					continue;
				float dk = PlaneH(planes, r, uk, vk) - PlaneH(planes, q, uk, vk);
				float dn = PlaneH(planes, r, un, vn) - PlaneH(planes, q, un, vn);
				if ((dk >= 0 && dn <= 0) || (dk <= 0 && dn >= 0))
				{
					// the planes meet between the samples: a ridge, a hip or a valley
					float t = 0.5;
					if (Math.AbsFloat(dk - dn) > 0.0001)
						t = Math.Clamp(dk / (dk - dn), 0.0, 1.0);
					pu.Insert(uk + (un - uk) * t);
					pv.Insert(vk + (vn - vk) * t);
				}
				else
				{
					// a step between them: where this plane ends
					float eu;
					float ev;
					PlaneEnd(b, uk, vk, un, vn, planes, r, eu, ev);
					pu.Insert(eu);
					pv.Insert(ev);
				}
			}
		}
		return ConvexHull(pu, pv);
	}

	//! every grid cell of the surface lies under one of its polygons (a few centimetres of tolerance); the cells that
	//! do not are listed (true while they are only a few)
	protected bool Covered(DS_RoofBuilding b, array<int> grp, int g, array<int> mine, array<ref array<float>> polys, array<int> holes)
	{
		int nu = b.m_NU;
		int nv = b.m_NV;
		int cells = 0;
		foreach (int k : mine)
		{
			int i = k % nu;
			int j = k / nu;
			if (i + 1 >= nu || j + 1 >= nv)
				continue;
			if (grp[k + 1] != g || grp[k + nu] != g || grp[k + nu + 1] != g)
				continue;
			cells++;
			float u = (i + 0.5) * b.m_StepU;
			float v = (j + 0.5) * b.m_StepV;
			bool any = false;
			foreach (array<float> poly : polys)
			{
				if (InPoly(poly, u, v, -0.03))
				{
					any = true;
					break;
				}
			}
			if (!any)
				holes.Insert(k);
		}
		return holes.Count() <= Math.Max(2, cells / 10);
	}

	//! a point lies inside a counter-clockwise polygon by more than margin (a negative margin allows a little outside)
	protected bool InPoly(array<float> poly, float u, float v, float margin)
	{
		int n = poly.Count() / 2;
		for (int e = 0; e < n; e++)
		{
			int e2 = (e + 1) % n;
			float ax = poly[e * 2];
			float az = poly[e * 2 + 1];
			float lx = poly[e2 * 2] - ax;
			float lz = poly[e2 * 2 + 1] - az;
			float len = Math.Sqrt(lx * lx + lz * lz);
			if (len < 0.0001)
				continue;
			if ((lx * (v - az) - lz * (u - ax)) / len < margin)
				return false;
		}
		return true;
	}

	protected float Cross2(array<float> pu, array<float> pv, int o, int a, int c)
	{
		return (pu[a] - pu[o]) * (pv[c] - pv[o]) - (pv[a] - pv[o]) * (pu[c] - pu[o]);
	}

	//! monotone chain hull, counter-clockwise, as u, v pairs (null for fewer than three points)
	protected array<float> ConvexHull(array<float> pu, array<float> pv)
	{
		int n = pu.Count();
		if (n < 3)
			return null;
		array<int> idx = new array<int>;
		for (int a = 0; a < n; a++)
		{
			int pos = idx.Count();
			while (pos > 0 && (pu[idx[pos - 1]] > pu[a] || (pu[idx[pos - 1]] == pu[a] && pv[idx[pos - 1]] > pv[a])))
				pos--;
			idx.InsertAt(a, pos);
		}
		array<int> hull = new array<int>;
		for (int l = 0; l < n; l++)
		{
			while (hull.Count() >= 2 && Cross2(pu, pv, hull[hull.Count() - 2], hull[hull.Count() - 1], idx[l]) <= 0.000001)
				hull.Remove(hull.Count() - 1);
			hull.Insert(idx[l]);
		}
		int lower = hull.Count() + 1;
		for (int r = n - 2; r >= 0; r--)
		{
			while (hull.Count() >= lower && Cross2(pu, pv, hull[hull.Count() - 2], hull[hull.Count() - 1], idx[r]) <= 0.000001)
				hull.Remove(hull.Count() - 1);
			hull.Insert(idx[r]);
		}
		// the last point is the first one again
		hull.Remove(hull.Count() - 1);
		if (hull.Count() < 3)
			return null;
		array<float> res = new array<float>;
		foreach (int h : hull)
		{
			res.Insert(pu[h]);
			res.Insert(pv[h]);
		}
		return res;
	}

	//! drops polygon corners that lie within two centimetres of the line through their neighbours (the edge points
	//! of a straight rim scatter by a centimetre or so)
	protected void SimplifyHull(array<float> hull)
	{
		bool changed = true;
		while (changed && hull.Count() > 6)
		{
			changed = false;
			int n = hull.Count() / 2;
			for (int k = 0; k < n; k++)
			{
				int a = (k + n - 1) % n;
				int c = (k + 1) % n;
				float ax = hull[a * 2];
				float az = hull[a * 2 + 1];
				float lx = hull[c * 2] - ax;
				float lz = hull[c * 2 + 1] - az;
				float len = Math.Sqrt(lx * lx + lz * lz);
				float dist = 0;
				if (len > 0.0001)
					dist = Math.AbsFloat((hull[k * 2] - ax) * lz - (hull[k * 2 + 1] - az) * lx) / len;
				if (dist < 0.02)
				{
					hull.RemoveOrdered(k * 2 + 1);
					hull.RemoveOrdered(k * 2);
					changed = true;
					break;
				}
			}
		}
	}

	//! the polygon of a plane may only cover its own samples and higher parts standing on it: a sample without the
	//! plane well inside it (a hole, a notch, the inner corner of an L, a lower roof) means the plane is not convex
	protected bool HullClear(DS_RoofBuilding b, map<int, bool> own, array<float> hull, array<float> planes, int r)
	{
		int nu = b.m_NU;
		int nv = b.m_NV;
		int n = hull.Count() / 2;
		float minU = 1000000;
		float maxU = -1000000;
		float minV = 1000000;
		float maxV = -1000000;
		for (int h = 0; h < n; h++)
		{
			minU = Math.Min(minU, hull[h * 2]);
			maxU = Math.Max(maxU, hull[h * 2]);
			minV = Math.Min(minV, hull[h * 2 + 1]);
			maxV = Math.Max(maxV, hull[h * 2 + 1]);
		}
		int i0 = Math.Floor(minU / b.m_StepU);
		int i1 = Math.Ceil(maxU / b.m_StepU);
		int j0 = Math.Floor(minV / b.m_StepV);
		int j1 = Math.Ceil(maxV / b.m_StepV);
		if (i0 < 0)
			i0 = 0;
		if (j0 < 0)
			j0 = 0;
		if (i1 > nu - 1)
			i1 = nu - 1;
		if (j1 > nv - 1)
			j1 = nv - 1;
		for (int j = j0; j <= j1; j++)
		{
			for (int i = i0; i <= i1; i++)
			{
				int k = j * nu + i;
				if (own.Contains(k))
					continue;
				float u = i * b.m_StepU;
				float v = j * b.m_StepV;
				// on the plane (an edge sample) or above it (a chimney, a dormer standing on it)
				if (b.m_H[k] != NO_HIT && b.m_H[k] > PlaneH(planes, r, u, v) - CAP_FLAT * 1.5)
					continue;
				if (InPoly(hull, u, v, 0.04))
				{
					if (DS_State.s_DebugCapLog)
					{
						float above = -999;
						if (b.m_H[k] != NO_HIT)
							above = b.m_H[k] - PlaneH(planes, r, u, v);
						Print(string.Format("[DSTest] capclear plane %1 (h0=%2 slopes %3 %4, %5 corners) covers %6 which lies %7 from it", r, planes[r * 5] - b.m_Ground, planes[r * 5 + 1], planes[r * 5 + 2], n, CapSample(b, k), above));
					}
					return false;
				}
			}
		}
		return true;
	}

	//! rectangular tops: the grid samples miss the corners, so the hull cuts them off with a short edge between two
	//! edges at right angles. The corner replaces that edge when a ray finds the surface just inside it
	protected void SquareCorners(DS_RoofBuilding b, array<float> hull, array<float> planes, int r)
	{
		float maxCut = Math.Max(b.m_StepU, b.m_StepV) * 1.6;
		int k = 0;
		int guard = 0;
		while (guard < 64)
		{
			guard++;
			int n = hull.Count() / 2;
			if (k >= n || n < 4)
				return;
			float mx = 0;
			float mz = 0;
			for (int m = 0; m < n; m++)
			{
				mx += hull[m * 2];
				mz += hull[m * 2 + 1];
			}
			mx /= n;
			mz /= n;
			int io = (k + n - 1) % n;
			int ip = k;
			int iq = (k + 1) % n;
			int ir = (k + 2) % n;
			k++;
			float px = hull[ip * 2];
			float pz = hull[ip * 2 + 1];
			float qx = hull[iq * 2];
			float qz = hull[iq * 2 + 1];
			float cut = Math.Sqrt((qx - px) * (qx - px) + (qz - pz) * (qz - pz));
			float d1x = px - hull[io * 2];
			float d1z = pz - hull[io * 2 + 1];
			float d2x = hull[ir * 2] - qx;
			float d2z = hull[ir * 2 + 1] - qz;
			float l1 = Math.Sqrt(d1x * d1x + d1z * d1z);
			float l2 = Math.Sqrt(d2x * d2x + d2z * d2z);
			if (cut > maxCut || l1 < cut || l2 < cut || l1 < 0.01 || l2 < 0.01)
				continue;
			d1x /= l1;
			d1z /= l1;
			d2x /= l2;
			d2z /= l2;
			if (Math.AbsFloat(d1x * d2x + d1z * d2z) > 0.26)
				continue;
			float det = d1x * d2z - d1z * d2x;
			if (Math.AbsFloat(det) < 0.5)
				continue;
			float wx = qx - px;
			float wz = qz - pz;
			float t = (wx * d2z - wz * d2x) / det;
			float s = (d1x * wz - d1z * wx) / det;
			if (t <= 0 || s <= 0 || t > maxCut || s > maxCut)
				continue;
			float cx = px + d1x * t;
			float cz = pz + d1z * t;
			float toMid = Math.Sqrt((mx - cx) * (mx - cx) + (mz - cz) * (mz - cz));
			if (toMid < 0.1)
				continue;
			float tu = cx + (mx - cx) / toMid * 0.04;
			float tv = cz + (mz - cz) / toMid * 0.04;
			vector wp = b.m_Origin + b.m_U * tu + b.m_V * tv;
			float cornerH = PlaneH(planes, r, tu, tv);
			float hit = SampleNear(b, wp[0], wp[2], cornerH, 1.5, 0.3);
			if (hit == NO_HIT || Math.AbsFloat(hit - cornerH) > 0.05)
				continue;
			hull[ip * 2] = cx;
			hull[ip * 2 + 1] = cz;
			hull.RemoveOrdered(iq * 2 + 1);
			hull.RemoveOrdered(iq * 2);
			if (iq < ip)
				k--;
		}
	}

	protected vector CapPoint(DS_RoofBuilding b, float u, float v, array<float> planes, int p)
	{
		vector w = b.m_Origin + b.m_U * u + b.m_V * v;
		w[1] = planes[p * 5] + planes[p * 5 + 1] * (u - planes[p * 5 + 3]) + planes[p * 5 + 2] * (v - planes[p * 5 + 4]);
		return w;
	}


	protected int StageFor(DS_RoofBuilding b)
	{
		if (b.m_Tris.Count() == 0)
			return 0;
		return StageForDepth(DepthFor(b));
	}

	//! snow depth on the object (cm): the ground snow at its foot, minus what lay there when a vehicle came to rest
	protected float DepthFor(DS_RoofBuilding b)
	{
		float depth = DS_State.SnowAt(b.m_Ground, m_S0, m_S1, m_S2);
		if (b.m_Kind == 2 && b.m_RestDepth >= 0)
			depth = Math.Max(0, depth - b.m_RestDepth);
		return depth;
	}

	protected float SlabFor(DS_RoofBuilding b)
	{
		float depth = DepthFor(b);
		if (b.m_Kind == 0)
		{
			float slab = Math.Clamp(depth * SLAB_PER_CM, SLAB_MIN, SLAB_MAX);
			// from 5 cm the cover is closed: it hides the roofs whose drawn surface rises above their geometry
			if (depth >= 5.0)
				slab = Math.Max(slab, SLAB_CLOSED);
			return slab;
		}
		return Math.Clamp(depth * THIN_PER_CM, THIN_MIN, THIN_MAX);
	}

	protected int StageForDepth(float depth)
	{
		if (depth >= 10.0)
			return 4;
		if (depth >= 5.0)
			return 3;
		if (depth >= 2.0)
			return 2;
		if (depth >= 0.5)
			return 1;
		return 0;
	}

	protected void DeleteObjects(DS_RoofBuilding b)
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

	//! places a snow piece: its top lies offset straight above the roof and its sides reach down to the roof along
	//! the normal. Raising the top straight up (instead of along the normal) keeps neighbouring roof planes joined at
	//! ridges and hips; the model's up axis stays the roof normal, which the engine lights the snow by
	protected void Place(Object o, DS_RoofTri t, float offset)
	{
		// every triangle is its own object: shared edges computed from two transforms miss each other by a fraction of
		// a millimetre and the surface below shows through as a dotted line. Each triangle grows around its centroid
		// (3 percent, less for the large pieces of flat tops), so neighbours overlap by a few millimetres instead.
		float grow = t.m_Grow;
		vector mat[4];
		vector centre = o.GetBoundingCenter();
		vector up = Vector(0, offset, 0);
		vector skirt = t.m_Normal * (offset * Math.Max(t.m_Normal[1], 0.2));
		if (t.m_Quad)
		{
			// the square model is centred on its middle
			mat[0] = t.m_AxisU * grow;
			mat[1] = skirt;
			mat[2] = t.m_AxisV * grow;
			mat[3] = t.m_Center + up + mat[0] * centre[0] + mat[1] * centre[1] + mat[2] * centre[2];
			o.SetTransform(mat);
			return;
		}
		if (t.m_Free)
		{
			vector g = t.m_Center;
			vector e1 = (t.m_P1 - t.m_P0) * grow;
			vector e2 = (t.m_P2 - t.m_P0) * grow;
			vector p0 = g + (t.m_P0 - g) * grow;
			mat[0] = e1;
			mat[1] = skirt;
			mat[2] = e2;
			vector freeOrigin = p0 + (e1 + e2) * 0.5 + up;
			mat[3] = freeOrigin + mat[0] * centre[0] + mat[1] * centre[1] + mat[2] * centre[2];
			o.SetTransform(mat);
			return;
		}
		float cu = 1.0 / 6.0;
		float cv = -1.0 / 6.0;
		if (t.m_Shape == 1)
		{
			cu = -1.0 / 6.0;
			cv = 1.0 / 6.0;
		}
		else if (t.m_Shape == 2)
		{
			cu = -1.0 / 6.0;
		}
		else if (t.m_Shape == 3)
		{
			cv = 1.0 / 6.0;
		}
		vector shift = (t.m_AxisU * cu + t.m_AxisV * cv) * (1.0 - grow);
		mat[0] = t.m_AxisU * grow;
		mat[1] = skirt;
		mat[2] = t.m_AxisV * grow;
		vector origin = t.m_Center + up + shift;
		mat[3] = origin + mat[0] * centre[0] + mat[1] * centre[1] + mat[2] * centre[2];
		o.SetTransform(mat);
	}

	protected void ApplyStage(DS_RoofBuilding b, int stage)
	{
		int tick0 = TickCount(0);
		ApplyStageNow(b, stage);
		if (s_TicksPerSec > 0)
		{
			float ms = TickCount(tick0) / s_TicksPerSec * 1000.0;
			if (ms > DS_State.s_StatRoofPlaceMax && b.m_Obj)
			{
				DS_State.s_StatRoofPlaceMax = ms;
				DS_State.s_StatRoofPlaceWho = b.m_Obj.GetShapeName() + " pieces " + b.m_Objects.Count().ToString();
			}
		}
	}

	protected void ApplyStageNow(DS_RoofBuilding b, int stage)
	{
		DeleteObjects(b);
		b.m_Stage = stage;
		if (stage <= 0)
			return;
		float offset = OffsetFor(b);
		b.m_Offset = offset;
		b.m_Slab = SlabFor(b);
		float slab = Math.Max(offset, b.m_Slab + DS_State.s_DebugRoofOffset);
		foreach (DS_RoofTri t : b.m_Tris)
		{
			Object o = MakePiece(t, stage, slab);
			if (o)
				b.m_Objects.Insert(o);
		}
	}

	//! height of the snow above the surface the rays found
	protected float OffsetFor(DS_RoofBuilding b)
	{
		float offset = 0.05 + 0.0003 * b.m_Dist;
		// walls and wrecks: a gap of a few centimetres would show from the side. Vehicles and other movable entities
		// are sampled on their fire geometry, which follows the body only to a centimetre or two: their snow lies a
		// little higher, so the curved body does not show through it
		if (b.m_Kind == 1)
			offset = 0.015 + 0.0002 * b.m_Dist;
		else if (b.m_Kind == 2)
			offset = 0.04 + 0.0002 * b.m_Dist;
		return offset + DS_State.s_DebugRoofOffset;
	}

	//! one snow piece of a triangle at a stage (null when the stage drops it)
	protected Object MakePiece(DS_RoofTri t, int stage, float slab)
	{
		int st = stage - t.m_Drop;
		if (st < 1)
			return null;
		string p3d;
		if (t.m_Quad)
			p3d = DS_Const.DATA + "snow\\dsq" + t.m_Span.ToString() + t.m_Variant + "_s" + st.ToString() + ".p3d";
		else if (t.m_Free && t.m_Span > 1)
			p3d = DS_Const.DATA + "snow\\dsf" + t.m_Span.ToString() + "_s" + st.ToString() + ".p3d";
		else
			p3d = DS_Const.DATA + "snow\\dsr_" + ShapeName(t.m_Shape) + t.m_Variant + "_s" + st.ToString() + ".p3d";
		Object o = g_Game.CreateStaticObjectUsingP3D(p3d, t.m_Center, "0 0 0", 1.0, true);
		if (!o)
			return null;
		Place(o, t, slab);
		m_Objects++;
		m_Cost += 0.02;
		return o;
	}

	//! test harness statistics: adds the ticks since tick0 to a part
	protected static void StatTicks(int part, int tick0)
	{
		if (!DS_State.s_StatRoofTicks)
		{
			DS_State.s_StatRoofTicks = new array<int>;
			for (int k = 0; k < 6; k++)
				DS_State.s_StatRoofTicks.Insert(0);
		}
		DS_State.s_StatRoofTicks[part] = DS_State.s_StatRoofTicks[part] + TickCount(tick0);
	}

	//! the frame's time budget is used up (the larger one for work close to the camera)
	protected bool OverBudget(bool urgent = false)
	{
		int limit = s_BudgetTicks;
		if (urgent)
			limit = s_UrgentTicks;
		return limit > 0 && TickCount(s_FrameTick) > limit;
	}

	//! test harness statistics: the longest single step of the roof work (a row of rays, an edge, a polygon step)
	protected void StatStep(int tick0, DS_RoofBuilding b)
	{
		if (s_TicksPerSec <= 0)
			return;
		float ms = TickCount(tick0) / s_TicksPerSec * 1000.0;
		DS_State.s_StatRoofBuildSum += ms;
		DS_State.s_StatRoofBuilds++;
		if (ms > DS_State.s_StatRoofBuildMax && b.m_Obj)
		{
			DS_State.s_StatRoofBuildMax = ms;
			string what = "rays";
			if (b.m_State == 3)
				what = "edge";
			else if (b.m_Job)
				what = string.Format("polygons (group %1 phase %2 step %3)", b.m_Job.m_G, b.m_Job.m_Phase, b.m_Job.m_R);
			else if (b.m_State == 2)
				what = "finish";
			DS_State.s_StatRoofBuildWho = b.m_Obj.GetShapeName() + " samples " + (b.m_NU * b.m_NV).ToString() + " " + what;
		}
	}

	//! starts placing a building's pieces for a stage; the current pieces stay until the new ones are all placed.
	//! False when the frame's budget ran out before they were
	protected bool StartPlace(DS_RoofBuilding b, int stage)
	{
		TrashPending(b);
		if (stage <= 0)
		{
			Trash(b);
			b.m_Stage = stage;
			return true;
		}
		b.m_Pending = new array<Object>;
		b.m_PendCursor = 0;
		b.m_PendStage = stage;
		b.m_PendOffset = OffsetFor(b);
		b.m_PendSlab = SlabFor(b);
		return ContinuePlace(b);
	}

	//! places pieces until the budget runs out; when all are placed they replace the current ones (true)
	protected bool ContinuePlace(DS_RoofBuilding b)
	{
		float slab = Math.Max(b.m_PendOffset, b.m_PendSlab + DS_State.s_DebugRoofOffset);
		int n = b.m_Tris.Count();
		while (b.m_PendCursor < n)
		{
			if ((b.m_PendCursor & 7) == 0 && OverBudget(b.m_Dist < URGENT_DIST))
				return false;
			DS_RoofTri t = b.m_Tris[b.m_PendCursor];
			b.m_PendCursor++;
			Object o = MakePiece(t, b.m_PendStage, slab);
			if (o)
				b.m_Pending.Insert(o);
		}
		Trash(b);
		b.m_Objects = b.m_Pending;
		b.m_Pending = null;
		b.m_Stage = b.m_PendStage;
		b.m_Offset = b.m_PendOffset;
		b.m_Slab = b.m_PendSlab;
		return true;
	}

	//! the current pieces of a building go to the trash
	protected void Trash(DS_RoofBuilding b)
	{
		foreach (Object o : b.m_Objects)
		{
			if (o)
				m_Trash.Insert(o);
		}
		b.m_Objects.Clear();
	}

	//! the pieces of a stage that was being placed go to the trash
	protected void TrashPending(DS_RoofBuilding b)
	{
		if (!b.m_Pending)
			return;
		foreach (Object o : b.m_Pending)
		{
			if (o)
				m_Trash.Insert(o);
		}
		b.m_Pending = null;
	}

	protected void TrashAll(DS_RoofBuilding b)
	{
		Trash(b);
		TrashPending(b);
	}

	//! deletes old pieces: up to a third of the frame's budget, and at least 64 so the trash cannot grow forever
	protected void EmptyTrash()
	{
		int limit = 0;
		if (s_BudgetTicks > 0)
			limit = s_BudgetTicks / 3;
		int done = 0;
		while (m_Trash.Count() > 0)
		{
			if (done >= 64 && (done & 15) == 0 && (limit <= 0 || TickCount(s_FrameTick) > limit))
				break;
			int last = m_Trash.Count() - 1;
			Object o = m_Trash[last];
			m_Trash.Remove(last);
			done++;
			if (o)
			{
				g_Game.ObjectDelete(o);
				m_Objects--;
			}
		}
	}

	void Update(float timeslice, vector camera, float s0, float s1, float s2)
	{
		// the length of a CPU tick, measured over whole frames
		if (s_FrameTick != 0 && timeslice > 0.002 && timeslice < 0.5)
		{
			float tps = TickCount(s_FrameTick) / timeslice;
			if (tps > 0)
			{
				if (s_TicksPerSec <= 0)
					s_TicksPerSec = tps;
				else
					s_TicksPerSec += (tps - s_TicksPerSec) * 0.05;
			}
		}
		s_FrameTick = TickCount(0);
		s_BudgetTicks = 0;
		s_UrgentTicks = 0;
		if (s_TicksPerSec > 0)
		{
			s_BudgetTicks = FRAME_MS * s_TicksPerSec / 1000.0;
			s_UrgentTicks = URGENT_MS * s_TicksPerSec / 1000.0;
		}
		UpdateRoofs(timeslice, camera, s0, s1, s2);
		StatTicks(5, s_FrameTick);
		if (s_TicksPerSec > 0)
		{
			float frameMs = TickCount(s_FrameTick) / s_TicksPerSec * 1000.0;
			if (frameMs > DS_State.s_StatRoofFrameMax)
				DS_State.s_StatRoofFrameMax = frameMs;
			DS_State.s_StatRoofFrames++;
			if (frameMs > 8.0)
				DS_State.s_StatRoofSlow++;
		}
	}

	protected void UpdateRoofs(float timeslice, vector camera, float s0, float s1, float s2)
	{
		if (DS_State.s_DebugRoofOff)
		{
			if (m_Tiles.Count() > 0 || m_Movable.Count() > 0)
				Clear();
			return;
		}
		s_Clock += timeslice;
		m_Camera = camera;
		m_S0 = s0;
		m_S1 = s1;
		m_S2 = s2;
		bool anySnow = Math.Max(s0, Math.Max(s1, s2)) >= 0.5;

		m_Cost = 0;
		// old pieces first (spread over frames), then the work of this frame within the time budget
		int tk = TickCount(0);
		EmptyTrash();
		StatTicks(0, tk);
		tk = TickCount(0);
		UpdateMovables(timeslice, camera, anySnow);
		StatTicks(1, tk);

		int ax = Math.Floor(camera[0] / TILE);
		int az = Math.Floor(camera[2] / TILE);
		if (ax != m_AnchorX || az != m_AnchorZ)
		{
			m_AnchorX = ax;
			m_AnchorZ = az;
			RebuildWork();
		}

		int count = m_Work.Count();
		int visited = 0;
		bool busy = false;
		while (m_Cost < 20.0 && visited < count)
		{
			if (m_Cursor >= count)
				m_Cursor = 0;
			int key = m_Work[m_Cursor];
			int ktx = Math.Floor(key / 65536.0);
			int ktz = key - ktx * 65536;
			if (OverBudget(TileDist(ktx, ktz) < URGENT_DIST + TILE))
			{
				busy = true;
				break;
			}
			m_Cursor++;
			visited++;

			DS_RoofTile tile = m_Tiles.Get(key);
			if (!tile)
			{
				if (!anySnow)
					continue;
				tile = new DS_RoofTile();
				m_Tiles.Set(key, tile);
			}
			if (!tile.m_Scanned)
			{
				int tx = Math.Floor(key / 65536.0);
				int tz = key - tx * 65536;
				tk = TickCount(0);
				ScanTile(tile, tx, tz);
				StatTicks(2, tk);
			}

			m_Cost += 0.01;
			foreach (DS_RoofBuilding b : tile.m_Buildings)
			{
				if (!b.m_Obj)
					continue;
				vector bp = b.m_Obj.GetPosition();
				float dx = bp[0] - camera[0];
				float dz = bp[2] - camera[2];
				b.m_Dist = Math.Sqrt(dx * dx + dz * dz);
				if (b.m_Small && b.m_Dist > SMALL_RADIUS)
				{
					// small structures carry snow only near the camera
					TrashAll(b);
					b.m_Stage = 0;
					continue;
				}
				if (b.m_Kind == 1)
				{
					float wallRadius = WALL_RADIUS;
					if (b.m_Reach > 0)
						wallRadius = b.m_Reach;
					if (DS_State.s_DebugWallRadius > 0)
						wallRadius = DS_State.s_DebugWallRadius;
					if (b.m_Dist > wallRadius)
					{
						TrashAll(b);
						b.m_Stage = 0;
						continue;
					}
				}
				if (b.m_Pending)
				{
					// a new stage is being placed: go on with it
					tk = TickCount(0);
					bool placed = ContinuePlace(b);
					StatTicks(4, tk);
					if (!placed)
					{
						m_Cursor--;
						visited = count;
						busy = true;
						break;
					}
					continue;
				}
				if (b.m_State == 0)
				{
					if (!anySnow)
						continue;
					BeginScan(b, b.m_Dist < FINE_RADIUS);
				}
				else if (b.m_State == 2 && !b.m_Fine && b.m_Kind == 0 && b.m_Dist < FINE_RADIUS && anySnow)
				{
					// came close: sample again at full detail, the current snow stays until the new one is built
					BeginScan(b, true);
					b.m_Stage = -1;
				}
				bool urgent = b.m_Dist < URGENT_DIST;
				while ((b.m_State == 1 || b.m_State == 3 || b.m_State == 4) && m_Cost < 20.0 && !OverBudget(urgent))
				{
					int stepTick = TickCount(0);
					if (b.m_State == 1)
						CastRow(b);
					else if (b.m_State == 3)
						RefineEdge(b);
					else if (CapStep(b))
						FinishTris(b);
					StatStep(stepTick, b);
					StatTicks(3, stepTick);
				}
				if (b.m_State != 2)
				{
					// continue this tile next frame
					m_Cursor--;
					visited = count;
					busy = true;
					break;
				}
				int want = StageFor(b);
				if (want != b.m_Stage || (want > 0 && Math.AbsFloat(SlabFor(b) - b.m_Slab) >= SLAB_STEP))
				{
					tk = TickCount(0);
					bool started = StartPlace(b, want);
					StatTicks(4, tk);
					if (!started)
					{
						m_Cursor--;
						visited = count;
						busy = true;
						break;
					}
				}
			}
		}
		if (m_Cost >= 20.0 || m_Trash.Count() > 0)
			busy = true;
		DS_State.s_StatRoofBusy = busy;
	}

	//! vehicles, tents, base parts and containers near the camera: snow while they stand still, none once they move
	protected void UpdateMovables(float timeslice, vector camera, bool anySnow)
	{
		m_MovableTimer += timeslice;
		if (m_MovableTimer >= 1.0 && s_Movables)
		{
			m_MovableTimer = 0;
			foreach (EntityAI e : s_Movables)
			{
				if (!e || m_Movable.Contains(e))
					continue;
				if (vector.Distance(e.GetPosition(), camera) > MOVABLE_RADIUS)
					continue;
				DS_RoofBuilding nb = new DS_RoofBuilding();
				nb.m_Obj = e;
				nb.m_Kind = 2;
				nb.m_LastPos = e.GetPosition();
				nb.m_LastDir = e.GetDirection();
				nb.m_Ground = g_Game.SurfaceY(nb.m_LastPos[0], nb.m_LastPos[2]);
				nb.m_RestDepth = -1;
				if (s_Fresh && s_Fresh.Contains(e))
					nb.m_RestDepth = DS_State.SnowAt(nb.m_Ground, m_S0, m_S1, m_S2);
				m_Movable.Set(e, nb);
			}
			array<EntityAI> gone = new array<EntityAI>;
			for (int g = 0; g < m_Movable.Count(); g++)
			{
				EntityAI ge = m_Movable.GetKey(g);
				if (!ge || vector.Distance(ge.GetPosition(), camera) > MOVABLE_RADIUS + 20.0)
					gone.Insert(ge);
			}
			foreach (EntityAI gk : gone)
			{
				DS_RoofBuilding gb = m_Movable.Get(gk);
				if (gb)
					DeleteObjects(gb);
				m_Movable.Remove(gk);
			}
		}

		for (int i = 0; i < m_Movable.Count(); i++)
		{
			DS_RoofBuilding b = m_Movable.GetElement(i);
			EntityAI ent = EntityAI.Cast(b.m_Obj);
			if (!ent)
				continue;
			vector pos = ent.GetPosition();
			vector dir = ent.GetDirection();
			bool moved = vector.Distance(pos, b.m_LastPos) > 0.03 || vector.Dot(dir, b.m_LastDir) < 0.9995 || ent.GetHierarchyParent() != null;
			if (moved)
			{
				if (b.m_Objects.Count() > 0)
					DeleteObjects(b);
				b.m_Tris.Clear();
				b.m_State = 0;
				b.m_Stage = 0;
				b.m_StillTime = 0;
				b.m_LastPos = pos;
				b.m_LastDir = dir;
				b.m_Ground = g_Game.SurfaceY(pos[0], pos[2]);
				// only snow that falls from now on lies on it
				b.m_RestDepth = DS_State.SnowAt(b.m_Ground, m_S0, m_S1, m_S2);
				continue;
			}
			b.m_StillTime += timeslice;
			if (b.m_StillTime < MOVABLE_REST)
				continue;
			b.m_Dist = vector.Distance(pos, camera);
			if (b.m_State == 0)
			{
				if (!anySnow)
					continue;
				BeginScan(b, true);
			}
			while ((b.m_State == 1 || b.m_State == 3 || b.m_State == 4) && m_Cost < 3.0)
			{
				if (b.m_State == 1)
					CastRow(b);
				else if (b.m_State == 3)
					RefineEdge(b);
				else if (CapStep(b))
					FinishTris(b);
			}
			if (b.m_State != 2)
				continue;
			int want = StageFor(b);
			if (want != b.m_Stage || (want > 0 && Math.AbsFloat(SlabFor(b) - b.m_Slab) >= SLAB_STEP))
				ApplyStage(b, want);
		}
	}

	void Clear()
	{
		if (!m_Tiles)
			return;
		for (int i = 0; i < m_Tiles.Count(); i++)
		{
			DS_RoofTile t = m_Tiles.GetElement(i);
			if (!t)
				continue;
			foreach (DS_RoofBuilding b : t.m_Buildings)
				TrashAll(b);
		}
		m_Tiles.Clear();
		if (m_Movable)
		{
			for (int m = 0; m < m_Movable.Count(); m++)
			{
				DS_RoofBuilding mb = m_Movable.GetElement(m);
				if (mb)
					DeleteObjects(mb);
			}
			m_Movable.Clear();
		}
		foreach (Object o : m_Trash)
		{
			if (o)
				g_Game.ObjectDelete(o);
		}
		m_Trash.Clear();
		m_Work.Clear();
		m_Objects = 0;
		m_AnchorX = -100000;
		m_AnchorZ = -100000;
	}

	//! test harness: places the snow of every building again (after a change of the debug offset)
	void DebugReapply(bool rescan = false)
	{
		for (int i = 0; i < m_Tiles.Count(); i++)
		{
			DS_RoofTile t = m_Tiles.GetElement(i);
			if (!t)
				continue;
			foreach (DS_RoofBuilding b : t.m_Buildings)
			{
				if (rescan)
				{
					TrashAll(b);
					b.m_Tris.Clear();
					b.m_State = 0;
					b.m_Stage = 0;
				}
				else if (b.m_State == 2)
				{
					TrashPending(b);
					b.m_Stage = -1;
				}
			}
		}
		if (rescan)
		{
			// the tiles are scanned again (which objects carry snow may have changed)
			for (int k = 0; k < m_Tiles.Count(); k++)
			{
				DS_RoofTile kt = m_Tiles.GetElement(k);
				if (!kt)
					continue;
				foreach (DS_RoofBuilding kb : kt.m_Buildings)
					DeleteObjects(kb);
			}
			m_Tiles.Clear();
			m_Cursor = 0;
		}
	}

	//! test harness: snow pieces per model of the structures near the camera, the most first
	void DebugModels(int top)
	{
		// pieces per kind and distance band (0-60, 60-120, 120-180, 180+ m)
		array<int> band = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
		for (int bi = 0; bi < m_Tiles.Count(); bi++)
		{
			DS_RoofTile bt = m_Tiles.GetElement(bi);
			if (!bt)
				continue;
			foreach (DS_RoofBuilding bb : bt.m_Buildings)
			{
				int bk = bb.m_Kind;
				if (bb.m_Small)
					bk = 2;
				int bd = Math.Min(3, Math.Floor(bb.m_Dist / 60.0));
				band[bk * 4 + bd] = band[bk * 4 + bd] + bb.m_Objects.Count();
			}
		}
		Print(string.Format("[DSTest] roofband buildings %1/%2/%3/%4 walls %5/%6/%7/%8", band[0], band[1], band[2], band[3], band[4], band[5], band[6], band[7]) + string.Format(" small %1/%2/%3/%4", band[8], band[9], band[10], band[11]));
		map<string, int> pieces = new map<string, int>;
		map<string, int> objs = new map<string, int>;
		for (int i = 0; i < m_Tiles.Count(); i++)
		{
			DS_RoofTile t = m_Tiles.GetElement(i);
			if (!t)
				continue;
			foreach (DS_RoofBuilding b : t.m_Buildings)
			{
				if (!b.m_Obj || b.m_Objects.Count() == 0)
					continue;
				TStringArray parts = new TStringArray;
				string full = b.m_Obj.GetShapeName();
				full.Split("\\", parts);
				string key = parts[parts.Count() - 1] + " k" + b.m_Kind.ToString();
				if (b.m_Small)
					key += "s";
				pieces.Set(key, pieces.Get(key) + b.m_Objects.Count());
				objs.Set(key, objs.Get(key) + 1);
			}
		}
		for (int n = 0; n < top && pieces.Count() > 0; n++)
		{
			int best = 0;
			for (int k = 1; k < pieces.Count(); k++)
			{
				if (pieces.GetElement(k) > pieces.GetElement(best))
					best = k;
			}
			string name = pieces.GetKey(best);
			Print(string.Format("[DSTest] roofmodel %1 pieces=%2 objs=%3", name, pieces.GetElement(best), objs.Get(name)));
			pieces.RemoveElement(best);
		}
	}


	//! test harness: samples the kind 0 structure nearest to a point again at once, logging every surface
	string DebugCaps(float x, float z)
	{
		DS_RoofBuilding best = null;
		float bestD = 30.0;
		for (int i = 0; i < m_Tiles.Count(); i++)
		{
			DS_RoofTile t = m_Tiles.GetElement(i);
			if (!t)
				continue;
			foreach (DS_RoofBuilding b : t.m_Buildings)
			{
				if (!b.m_Obj || b.m_Kind != 0)
					continue;
				vector p = b.m_Obj.GetPosition();
				float d = Math.Sqrt((p[0] - x) * (p[0] - x) + (p[2] - z) * (p[2] - z));
				if (d < bestD)
				{
					bestD = d;
					best = b;
				}
			}
		}
		if (!best)
			return "none";
		DS_State.s_DebugCapLog = true;
		BeginScan(best, true);
		int guard = 0;
		while ((best.m_State == 1 || best.m_State == 3 || best.m_State == 4) && guard < 100000)
		{
			guard++;
			if (best.m_State == 1)
				CastRow(best);
			else if (best.m_State == 3)
				RefineEdge(best);
			else if (CapStep(best))
				FinishTris(best);
		}
		DS_State.s_DebugCapLog = false;
		best.m_Stage = -1;
		return best.m_Obj.GetType() + " " + best.m_CapInfo + " tris=" + best.m_Tris.Count().ToString();
	}

	//! test harness: the snow triangles of the structure nearest to a point
	string DebugTris(float x, float z)
	{
		DS_RoofBuilding best = null;
		float bestD = 30.0;
		for (int i = 0; i < m_Tiles.Count(); i++)
		{
			DS_RoofTile t = m_Tiles.GetElement(i);
			if (!t)
				continue;
			foreach (DS_RoofBuilding b : t.m_Buildings)
			{
				if (!b.m_Obj || b.m_Kind != 0)
					continue;
				vector p = b.m_Obj.GetPosition();
				float d = Math.Sqrt((p[0] - x) * (p[0] - x) + (p[2] - z) * (p[2] - z));
				if (d < bestD)
				{
					bestD = d;
					best = b;
				}
			}
		}
		if (!best)
			return "none";
		for (int k = 0; k < best.m_Tris.Count(); k++)
		{
			DS_RoofTri tr = best.m_Tris[k];
			string objPos = "-";
			if (k < best.m_Objects.Count() && best.m_Objects[k])
				objPos = best.m_Objects[k].GetPosition().ToString();
			Print(string.Format("[DSTest] rooftri %1 %2%3 centre=%4 u=%5 v=%6 ny=%7 drop=%8 obj=%9", k, ShapeName(tr.m_Shape), tr.m_Variant, tr.m_Center, tr.m_AxisU.Length(), tr.m_AxisV.Length(), tr.m_Normal[1], tr.m_Drop, objPos));
		}
		return string.Format("%1 tris=%2 objects=%3 stage=%4 offset=%5 caps: %6", best.m_Obj.GetType(), best.m_Tris.Count(), best.m_Objects.Count(), best.m_Stage, best.m_Offset, best.m_CapInfo);
	}

	//! test harness: samples the structure nearest to a point once more and prints its ray grid row by row: the hit
	//! height above the ground in cm, or why there is none (N no hit at all, L too low, B something solid above it)
	string DebugGrid(float x, float z, int geo = 0)
	{
		Object best = null;
		float bestD = 30.0;
		array<Object> objs = new array<Object>;
		g_Game.GetObjectsAtPosition(Vector(x, g_Game.SurfaceY(x, z), z), 30.0, objs, null);
		foreach (Object o : objs)
		{
			if (!o)
				continue;
			string dbgShape = o.GetShapeName();
			dbgShape.ToLower();
			if (!(o.IsBuilding() || o.IsRock() || IsPlainStructure(dbgShape)))
				continue;
			vector mm[2];
			o.ClippingInfo(mm);
			vector sz = mm[1] - mm[0];
			if (sz[0] < 0.9 || sz[2] < 0.9 || sz[1] < 0.5)
				continue;
			float d = vector.Distance(o.GetPosition(), Vector(x, o.GetPosition()[1], z));
			if (d < bestD)
			{
				bestD = d;
				best = o;
			}
		}
		if (!best)
			return "no building";
		DS_RoofBuilding b = new DS_RoofBuilding();
		b.m_Obj = best;
		b.m_Kind = 0;
		vector bp = best.GetPosition();
		b.m_Ground = g_Game.SurfaceY(bp[0], bp[2]);
		BeginScan(b, true);
		Print(string.Format("[DSTest] roofgrid %1 %2 nu=%3 nv=%4 step=%5 origin=%6 u=%7 v=%8", best.GetType(), best.GetShapeName(), b.m_NU, b.m_NV, b.m_StepU, b.m_Origin, b.m_U, b.m_V.ToString() + " ground=" + b.m_Ground.ToString()));
		for (int j = 0; j < b.m_NV; j++)
		{
			string row = "";
			for (int i = 0; i < b.m_NU; i++)
			{
				vector p = b.m_Origin + b.m_U * (i * b.m_StepU) + b.m_V * (j * b.m_StepV);
				float groundHere = g_Game.SurfaceY(p[0], p[2]);
				RaycastRVParams rp = new RaycastRVParams(Vector(p[0], b.m_Top, p[2]), Vector(p[0], b.m_Bottom, p[2]), null, 0);
				rp.type = ObjIntersectFire;
				if (geo == 2)
					rp.type = ObjIntersectView;
				else if (geo == 3)
					rp.type = ObjIntersectGeom;
				else if (geo == 4)
					rp.type = ObjIntersectIFire;
				rp.flags = CollisionFlags.ALLOBJECTS;
				rp.sorted = true;
				array<ref RaycastRVResult> results = new array<ref RaycastRVResult>;
				string cellText = "  N ";
				if (DayZPhysics.RaycastRVProxy(rp, results))
				{
					float h = NO_HIT;
					float ny = 0;
					float blockTop = NO_HIT;
					foreach (RaycastRVResult res : results)
					{
						Object hit = res.obj;
						if (res.parent)
							hit = res.parent;
						if (!hit)
							continue;
						if (hit == best)
						{
							if (res.pos[1] > h)
							{
								h = res.pos[1];
								ny = res.dir[1];
							}
						}
						else if (!DS_Util.IsVegetation(hit) && !hit.IsInherited(Man) && !hit.IsInherited(DayZCreature))
						{
							if (res.pos[1] > blockTop)
								blockTop = res.pos[1];
						}
					}
					if (h == NO_HIT)
						cellText = "  N ";
					else if (blockTop > h + 0.3)
						cellText = "  B ";
					else if (h < groundHere + 0.25)
						cellText = "  L ";
					else
					{
						int cm = Math.Round((h - b.m_Ground) * 100.0);
						int nyp = Math.Round(ny * 9.0);
						cellText = " " + cm.ToString() + "/" + nyp.ToString();
					}
				}
				row += cellText;
			}
			Print(string.Format("[DSTest] roofgrid row %1:%2", j, row));
		}
		return "done";
	}
}

