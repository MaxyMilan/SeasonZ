//! One snow triangle on a building, stored as the transform that maps the unit triangle model onto the roof
class SZ_RoofTri
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
	//! a square of m_Span grid cells on one plane, drawn as one object (the szq models)
	bool m_Quad;
	int m_Span;
	//! how much the piece grows around its centre so it overlaps its neighbours (1.03 = 3 percent)
	float m_Grow;
	//! a grid piece filling a gap between polygons lies this much lower (see FillGaps)
	float m_Lower;

	void SZ_RoofTri()
	{
		m_Grow = 1.03;
	}
}

//! the polygons of one structure, built a step at a time over several frames: per surface, splitting it into
//! planes, then the polygon of each plane, then the pieces of each polygon
class SZ_CapJob
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

	void SZ_CapJob()
	{
		m_Grp = new array<int>;
		m_GridGroup = new array<bool>;
		m_Members = new array<ref array<int>>;
	}
}

//! Roof snow of one building
class SZ_RoofBuilding
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
	ref array<ref SZ_RoofTri> m_Tris;
	ref array<Object> m_Objects;
	//! a small structure (block, box, bench, hay bale): sampled on a grid sized to it, with its edges found at any
	//! distance
	bool m_Small;
	//! a wall: a flat top becomes one strip of snow (its edges are found like those of the small structures)
	bool m_Wall;
	//! a rock or stone
	bool m_Rock;
	//! the snow baked for this model (see SZ_BakedSnow): the name of its models, "" when it has none or when something
	//! else stands over it here (its snow is sampled like that of the other structures then)
	string m_Baked;
	//! baked snow: how far it is raised above the roof (grows with the distance, like the offset of the pieces)
	float m_Lift;
	//! the geometry the rays look for: the fire geometry, or the collision geometry of a structure that has no fire
	//! geometry (hay stacks, some pumps and racks)
	int m_Geo;
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
	//! close range samples left without snow because they lie on stairs (see DropStairs)
	ref map<int, bool> m_Stair;
	//! slopes measured with short rays where the samples of a surface do not tell them (see CrossSlope)
	ref map<int, float> m_Cross2;
	//! close buildings: the grid edges between a sample on the roof and one beside it, and where the roof ends on
	//! them (found with a few more rays after the grid)
	ref array<int> m_EdgeKeys;
	int m_EdgeCursor;
	ref map<int, vector> m_Cross;
	//! thickness of the snow slab as placed (metres)
	float m_Slab;
	//! the polygons being built (state 4)
	ref SZ_CapJob m_Job;
	//! the pieces of a new stage being placed over several frames (null when none); the current pieces stay until
	//! all of them are placed
	ref array<Object> m_Pending;
	int m_PendCursor;
	int m_PendStage;
	float m_PendSlab;
	float m_PendOffset;
	//! baked snow: in the quick round that follows the snow depth (see UpdateBakedRing); dropped once its tile is
	bool m_InRing;
	bool m_Dropped;
	//! test harness: how the surfaces became polygons or grid pieces
	string m_CapInfo;
	// movable entities: where it stood, for how long, and the ground snow when it came to rest (-1 = it stood there
	// before this client saw it)
	vector m_LastPos;
	vector m_LastDir;
	float m_StillTime;
	float m_RestDepth;

	void SZ_RoofBuilding()
	{
		m_Reach = -1;
		m_Geo = ObjIntersectFire;
		m_Tris = new array<ref SZ_RoofTri>;
		m_Objects = new array<Object>;
		m_H = new array<float>;
		m_NY = new array<float>;
		m_Stair = new map<int, bool>;
		m_Cross2 = new map<int, float>;
		m_EdgeKeys = new array<int>;
		m_Cross = new map<int, vector>;
	}
}

class SZ_RoofTile
{
	ref array<ref SZ_RoofBuilding> m_Buildings;
	bool m_Scanned;
	int m_UpdateCursor;

	void SZ_RoofTile()
	{
		m_Buildings = new array<ref SZ_RoofBuilding>;
	}
}

//! Client: snow on roofs, ledges and other upward facing parts of buildings near the camera. Every building is
//! sampled once with a grid of downward rays in its own axes; the hits are joined into triangles that follow the
//! roof planes and are drawn with the same snow models as the ground cover.
class SZ_RoofSnow
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
	//! the narrow side of the smallest structure that carries snow (a garbage bin, a stone)
	static const float SMALL_MIN = 0.6;
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
	//! close range grid: stairs and ramps. Their fire geometry is one sloping surface over the steps, so snow drawn on
	//! it is a slab hiding them. Neighbouring samples more than JOIN_TOL apart in height, both on a walkable surface
	//! (the roadway of stairs runs up to STAIR_ROAD above or below the fire geometry), form a stair when they come
	//! down to within STAIR_FOOT of the ground; a walkable roof higher up keeps its snow
	static const float JOIN_TOL = 0.08;
	static const float STAIR_ROAD = 0.25;
	static const float STAIR_FOOT = 0.6;
	//! stairs climb 30 to 40 degrees; ramps for vehicles and loading (up to about 15 degrees) are no stairs and keep
	//! their snow: metres of rise per metre between two samples on a stair
	static const float STAIR_SLOPE = 0.4;
	//! where a surface ends at a stair, how far from its height the refining rays may still find it (the snow of a
	//! landing does not reach out over the top steps)
	static const float STEP_REFINE = 0.08;
	//! close range grid: two neighbouring samples are on two surfaces with a step between them when the height
	//! between them is this much more than the slope on either side of them (the edge of a roof above a lower roof
	//! or a ledge; snow drawn across makes a band in the air)
	static const float DROP_TOL = 0.25;
	//! a surface sampled in one row only (a narrow roof, a lean-to below the eaves of a higher roof): its slope
	//! across the row is measured with a short ray this far to either side, and a surface ends at an edge with no
	//! sample of it behind: its slope towards the edge is measured this far in
	static const float CROSS_PROBE = 0.25;
	//! the probes of CrossSlope agree on a straight surface within this
	static const float CROSS_AGREE = 0.05;
	//! small structures: no snow piece below the lowest or above the highest point found on them by more than this
	static const float RANGE_TOL = 0.25;
	//! rocks and stones: no snow on faces steeper than about 41 degrees (it does not stay there; on a rock the piece
	//! stood out as a white plate on the flank)
	static const float ROCK_NY = 0.75;
	//! baked snow: the snow depth (cm) from which each of the seven models is drawn (the first three follow the stages
	//! of the roof snow, the others a closed cover growing deeper), and the change of the lift (m) for which it is
	//! placed again
	static const ref array<float> BAKED_DEPTHS = {0.5, 2.0, 5.0, 10.0, 14.0, 19.0, 25.0};
	static const float BAKED_LIFT_STEP = 0.01;
	//! baked snow: placements tilted more than about 12 degrees are sampled instead
	static const float BAKED_UPRIGHT = 0.978;
	//! baking: a point of a piece counts as resting on the structure when the structure lies at most this far under it
	static const float BAKE_SUPPORT = 0.1;
	static const float EDGE_PROBE = 0.2;
	//! surfaces lower than this above the ground are checked for a see-through roof over them (see SampleAt)
	static const float SEE_THROUGH = 1.5;
	//! walls, fences and wrecks: a piece is dropped when two of its test points (its centre and its corners pulled
	//! 30 percent in) find the top more than this far below it or not at all. Fences of planks or pickets with an
	//! uneven top would otherwise carry straight strips of snow hanging over the gaps
	static const float WALL_GAP = 0.05;

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
	//! structures looked at per frame once their snow is built: the update goes round all of them in turn (a town
	//! has a few thousand within KEEP_RADIUS, a full round takes a few tenths of a second), instead of checking every
	//! one of them every frame
	static const int VISITS_PER_FRAME = 250;
	//! the same in CPU ticks (0 until the tick length is known)
	protected static int s_BudgetTicks;
	protected static int s_UrgentTicks;
	//! baking (test harness): the height of the ground under the copy being sampled (the rules near the ground use it
	//! instead of the terrain; NO_HIT = the terrain) and how much finer than at close range its grid is
	protected static float s_BakeGround = -100000.0;
	protected static float s_BakeRefine = 1.0;
	protected static bool s_Baking;

	//! the ground under a point: the terrain, or the ground of the copy being baked
	protected static float GroundAt(float x, float z)
	{
		if (s_BakeGround != NO_HIT)
			return s_BakeGround;
		return g_Game.SurfaceY(x, z);
	}

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
		SZ_RoofTri t = new SZ_RoofTri();
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
			last = SZ_Const.DATA + "snow\\szr_" + ShapeName(t.m_Shape) + t.m_Variant + "_s" + st.ToString() + ".p3d";
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
		// the Livonia objects placed on Chernarus (wrapped hay bales, wrecks, sheds, pipes) lie in structures_bliss
		if (shape.IndexOf("\\structures\\") < 0 && shape.IndexOf("\\structures_bliss\\") < 0)
			return false;
		if (shape.IndexOf("\\roads\\bridges\\") >= 0)
			return true;
		// transformers carry snow on their housings and bases; the poles, wires and cables around them do not
		if (shape.IndexOf("power_transformer") >= 0 && shape.IndexOf("cable") < 0)
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

	protected ref map<int, ref SZ_RoofTile> m_Tiles;
	protected ref map<EntityAI, ref SZ_RoofBuilding> m_Movable;
	protected float m_MovableTimer;
	protected ref array<int> m_Work;
	//! test harness: calls of PlaneEnd during the last structure's polygons
	protected int m_PlaneEnds;
	//! pieces waiting to be deleted: removed a few hundred per frame, so leaving a town or replacing a roof's pieces
	//! does not stall a frame
	protected ref array<Object> m_Trash;
	protected int m_Cursor;
	//! the structures with baked snow around the camera, checked a few hundred per frame for a change of their
	//! model: the main round waits on structures still sampled or placing pieces, so a new depth reached them late
	protected ref array<SZ_RoofBuilding> m_BakedRing;
	protected int m_BakedCursor;
	//! a round runs only after the snow depth changed (by a quarter centimetre at any of the three heights): at rest
	//! it costs nothing
	protected bool m_RingActive;
	protected int m_RingLeft;
	protected float m_RingS0 = -1;
	protected float m_RingS1 = -1;
	protected float m_RingS2 = -1;
	static const int BAKED_RING_PER_FRAME = 200;
	static const float BAKED_RING_STEP = 0.25;
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

	void SZ_RoofSnow()
	{
		m_Tiles = new map<int, ref SZ_RoofTile>;
		m_Movable = new map<EntityAI, ref SZ_RoofBuilding>;
		m_Work = new array<int>;
		m_Trash = new array<Object>;
		m_AnchorX = -100000;
		m_AnchorZ = -100000;
	}

	void ~SZ_RoofSnow()
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

	void PerfInventory(FileHandle file)
	{
		map<string, int> baked = new map<string, int>;
		map<string, int> sampled = new map<string, int>;
		for (int i = 0; i < m_Tiles.Count(); i++)
		{
			SZ_RoofTile tile = m_Tiles.GetElement(i);
			foreach (SZ_RoofBuilding building : tile.m_Buildings)
			{
				foreach (Object obj : building.m_Objects)
				{
					if (building.m_Baked != "")
						SZ_PerfInventory.Add(baked, obj);
					else
						SZ_PerfInventory.Add(sampled, obj);
				}
			}
		}
		SZ_PerfInventory.Write(file, "roof_baked", baked);
		SZ_PerfInventory.Write(file, "roof_sampled", sampled);
		Print(string.Format("[DSTest] inventory roof pending_trash=%1 movable_sources=%2", m_Trash.Count(), m_Movable.Count()));
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
			SZ_RoofTile t = m_Tiles.GetElement(i);
			if (!t)
				continue;
			foreach (SZ_RoofBuilding b : t.m_Buildings)
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
			SZ_RoofBuilding mb = m_Movable.GetElement(m);
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
			SZ_RoofTile t = m_Tiles.Get(k);
			if (t)
			{
				foreach (SZ_RoofBuilding b : t.m_Buildings)
				{
					b.m_Dropped = true;
					TrashAll(b);
				}
			}
			m_Tiles.Remove(k);
		}
		m_Cursor = 0;
	}

	protected void ScanTile(SZ_RoofTile tile, int tx, int tz)
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
			if (SZ_TreeSwap.IsPath(o))
				continue;
			vector p = o.GetPosition();
			if (Math.Floor(p[0] / TILE) != tx || Math.Floor(p[2] / TILE) != tz)
				continue;
			SZ_RoofBuilding b = Classify(o);
			if (b)
				tile.m_Buildings.Insert(b);
		}
	}

	//! the snow record of a map object that carries snow, null for the others
	protected SZ_RoofBuilding Classify(Object o)
	{
		vector mm[2];
		o.ClippingInfo(mm);
		vector size = mm[1] - mm[0];
		int kind = -1;
		bool small = false;
		string shape = o.GetShapeName();
		shape.ToLower();
		// the long straw stack: its geometry lies inside the hay on top and sticks out of it at the ends, so its
		// snow would be hidden on top and stand as white blocks at the ends. The stack of wrapped bales: its
		// geometry runs as a slope from the lower bales to the upper ones, the snow would stand there as a plate
		if (shape.IndexOf("farm_strawstack") >= 0 || shape.IndexOf("haybale_packed_stack") >= 0)
			return null;
		// walls keep the fine grid of thin tops, whatever their bounding box
		bool wall = shape.IndexOf("\\walls\\") >= 0;
		bool plain = !o.IsBuilding() && !o.IsRock() && SZ_State.s_DebugRoofPlain > 0 && IsPlainStructure(shape);
		// small buildings (outhouses, coops, kennels, kiosks) and loose stones: like the small plain structures.
		// Poles, lamps and wires stay without snow (see IsPlainStructure)
		bool smallBody = plain || o.IsRock() || (o.IsBuilding() && IsPlainStructure(shape));
		if (!wall && (o.IsBuilding() || o.IsRock() || plain) && size[0] >= 2.5 && size[2] >= 2.5 && size[1] >= 2.0)
		{
			kind = 0;
		}
		else if (smallBody && !wall && SZ_State.s_DebugRoofPlain == 3 && size[0] >= SMALL_MIN && size[2] >= SMALL_MIN && size[1] >= 0.5)
		{
			// smaller structures (blocks, barriers, boxes, benches, bins, hay bales, small buildings, stones): a
			// grid sized to them, and flat tops drawn as single polygons
			kind = 0;
			small = true;
		}
		else
		{
			// walls, fences, car wrecks and smaller plain structures (barriers, pipes, wood piles): narrow tops
			// that hold a strip of snow; the short corner and post pieces of walls too
			bool thin = (plain && SZ_State.s_DebugRoofPlain > 1) || wall || shape.IndexOf("\\wrecks\\") >= 0;
			float minLength = 1.2;
			if (wall)
				minLength = 0.5;
			if (thin && Math.Max(size[0], size[2]) >= minLength && size[1] >= 0.4)
				kind = 1;
		}
		if (kind < 0)
			return null;
		SZ_RoofBuilding b = new SZ_RoofBuilding();
		b.m_Obj = o;
		b.m_Kind = kind;
		b.m_Small = small;
		b.m_Wall = wall && kind == 1;
		b.m_Rock = o.IsRock();
		vector p = o.GetPosition();
		b.m_Ground = g_Game.SurfaceY(p[0], p[2]);
		if (SZ_State.s_DebugBaked && !s_Baking)
		{
			b.m_Baked = SZ_BakedSnow.Find(shape);
			// baked and found to carry no snow (signs, wire fences): nothing to sample
			if (b.m_Baked == "-")
				return null;
		}
		return b;
	}

	//! sets up the ray grid in the object's own horizontal axes. Buildings use square cells; walls, wrecks and
	//! movable entities use a fine grid with at least four samples across their narrow side
	protected void BeginScan(SZ_RoofBuilding b, bool fine)
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
		// far buildings have no edge refinement, so their snow ends at the last cell fully on the roof: their grid is
		// fitted to the building's box a little inside it instead, and on the many roofs that reach out to the box the
		// outermost samples lie on the rim, so the snow reaches the rim and the corners
		bool fit = SZ_State.s_DebugRoofFit && b.m_Kind == 0 && !fine && !b.m_Small;
		if (fit)
			pad = -0.05;
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
			step = step / s_BakeRefine;
			if (b.m_Small)
			{
				// small structures: three samples across their narrow side
				float side = Math.Min(u1 - u0, v1 - v0) - 2.0 * pad;
				step = Math.Clamp(side / (3.0 * s_BakeRefine), 0.15 / s_BakeRefine, step);
			}
			// very large buildings get a coarser grid
			while ((u1 - u0) / step > 44 * s_BakeRefine || (v1 - v0) / step > 44 * s_BakeRefine)
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
		if (fit)
		{
			b.m_StepU = (u1 - u0) / Math.Max(1, b.m_NU - 1);
			b.m_StepV = (v1 - v0) / Math.Max(1, b.m_NV - 1);
		}
		if (b.m_Small)
		{
			// centred on the structure, so a round or ridged top is sampled alike on both sides
			float midU = (u0 + u1) * 0.5;
			float midV = (v0 + v1) * 0.5;
			u0 = midU - (b.m_NU - 1) * b.m_StepU * 0.5;
			v0 = midV - (b.m_NV - 1) * b.m_StepV * 0.5;
		}
		b.m_Origin = Vector(mat[3][0], 0, mat[3][2]) + b.m_U * u0 + b.m_V * v0;
		// small structures and narrow ones start their rays 6 m up: a table, bed or shelf inside a building (DayZ
		// Expansion's interiors and mapping place furniture as separate objects) has the ceiling above it, which then
		// blocks every sample; 1.5 m stopped short of most ceilings and the furniture got snow indoors
		float above = 1.5;
		if (b.m_Small || b.m_Kind == 1)
			above = 6.0;
		b.m_Top = mat[3][1] + mm[1][1] * mat[1].Length() + above;
		b.m_Bottom = b.m_Ground - 0.5;
		b.m_Row = 0;
		b.m_H.Clear();
		b.m_NY.Clear();
		b.m_Stair.Clear();
		b.m_Cross2.Clear();
		b.m_EdgeKeys.Clear();
		b.m_EdgeCursor = 0;
		b.m_Cross.Clear();
		b.m_State = 1;
	}

	//! the roof height a downward ray finds at a point: the highest hit on the object itself, or NO_HIT when there
	//! is none, when something solid other than vegetation lies above it, or for porches and slabs just above the
	//! ground (the terrain cover handles those)
	protected float SampleAt(SZ_RoofBuilding b, float x, float z)
	{
		float groundHere = GroundAt(x, z);
		RaycastRVParams rp = new RaycastRVParams(Vector(x, b.m_Top, z), Vector(x, b.m_Bottom, z), null, 0);
		rp.type = b.m_Geo;
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
			else if (!SZ_Util.IsVegetation(hit) && !hit.IsInherited(Man) && !hit.IsInherited(DayZCreature))
			{
				if (res.pos[1] > blockTop)
					blockTop = res.pos[1];
			}
		}
		if (h != NO_HIT && (blockTop > h + 0.3 || h < groundHere + 0.25))
			return NO_HIT;
		// a low surface under a see-through roof (greenhouse glass, polytunnel film): the roof has view geometry but
		// little or no fire geometry, so the highest fire hit can be a bed or the floor inside
		if (h != NO_HIT && b.m_Kind == 0 && h < groundHere + SEE_THROUGH && RoofInView(b, x, z, h))
			return NO_HIT;
		return h;
	}

	//! the structure's view geometry lies over a point well above a height
	protected bool RoofInView(SZ_RoofBuilding b, float x, float z, float h)
	{
		if (b.m_Top < h + 0.6)
			return false;
		RaycastRVParams rp = new RaycastRVParams(Vector(x, b.m_Top, z), Vector(x, h + 0.5, z), null, 0);
		rp.type = ObjIntersectView;
		rp.flags = CollisionFlags.ALLOBJECTS;
		rp.sorted = false;
		array<ref RaycastRVResult> results = new array<ref RaycastRVResult>;
		m_Rays++;
		m_Cost += 0.02;
		if (!DayZPhysics.RaycastRVProxy(rp, results))
			return false;
		foreach (RaycastRVResult res : results)
		{
			Object hit = res.obj;
			if (res.parent)
				hit = res.parent;
			if (hit == b.m_Obj)
				return true;
		}
		return false;
	}

	protected vector SamplePos(SZ_RoofBuilding b, int i, int j)
	{
		return b.m_Origin + b.m_U * (i * b.m_StepU) + b.m_V * (j * b.m_StepV);
	}

	protected void CastRow(SZ_RoofBuilding b)
	{
		int j = b.m_Row;
		for (int i = 0; i < b.m_NU; i++)
		{
			vector p = SamplePos(b, i, j);
			b.m_H.Insert(SampleAt(b, p[0], p[2]));
		}
		b.m_Row++;
		if (b.m_Row < b.m_NV)
			return;
		if (b.m_Geo == ObjIntersectFire && (b.m_Kind == 0 || (b.m_Kind == 1 && !b.m_Wall)) && !AnyHit(b))
		{
			// a structure without fire geometry (hay stacks, pumps, racks, crash barriers, tombstones, signs): sampled
			// again on its collision geometry. Walls and fences without fire geometry (wire mesh, gates) keep none:
			// their collision box would draw a solid strip over the mesh
			b.m_Geo = ObjIntersectGeom;
			b.m_Row = 0;
			b.m_H.Clear();
			return;
		}
		FinishGrid(b);
	}

	protected bool AnyHit(SZ_RoofBuilding b)
	{
		foreach (float h : b.m_H)
		{
			if (h != NO_HIT)
				return true;
		}
		return false;
	}

	//! the grid is complete: close buildings look for their roof edges first, everything else is built right away
	protected void FinishGrid(SZ_RoofBuilding b)
	{
		FlattenSpikes(b);
		DropStairs(b);
		if (SZ_State.s_DebugRoofEdges && ((b.m_Kind == 0 && (b.m_Fine || b.m_Small)) || (b.m_Wall && SZ_State.s_DebugRoofCaps > 0)))
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

	//! a sample on a thin part standing out of a roof (a mast foot, a pipe, a bracket, a vent) would fold the snow up to
	//! it in steep flaps: where the roof, carried on from two samples beyond it, runs below it by more than this in both
	//! directions, the sample takes the roof's height. The snow lies on and the thin part stands out of it. Near a roof
	//! edge the roof is carried on from the side that has two samples. A part two samples wide is flattened as well when
	//! it stands out less than a fold (a taller one, a chimney, keeps its own cap). A ridge, a hip, the top of a hipped
	//! roof and a parapet are carried on to their own height and stay
	static const float SPIKE = 0.25;

	protected void FlattenSpikes(SZ_RoofBuilding b)
	{
		if (b.m_Kind != 0 || !SZ_State.s_DebugRoofCorner)
			return;
		int nu = b.m_NU;
		int nv = b.m_NV;
		float fold = Math.Min(b.m_StepU, b.m_StepV) * 1.35;
		array<int> which = new array<int>;
		array<float> level = new array<float>;
		for (int j = 0; j < nv; j++)
		{
			for (int i = 0; i < nu; i++)
			{
				int k = j * nu + i;
				if (b.m_H[k] == NO_HIT)
					continue;
				float eu = SpikeBase(b, i, j, 1, 0, fold);
				if (eu == NO_HIT)
					continue;
				float ev = SpikeBase(b, i, j, 0, 1, fold);
				if (ev == NO_HIT)
					continue;
				which.Insert(k);
				// the higher of the two: on a ridge the line along it keeps the ridge's height
				level.Insert(Math.Max(eu, ev));
			}
		}
		for (int n = 0; n < which.Count(); n++)
			b.m_H[which[n]] = level[n];
	}

	//! the height of grid sample (i, j); NO_HIT off the grid
	protected float GridAt(SZ_RoofBuilding b, int i, int j)
	{
		if (i < 0 || j < 0 || i >= b.m_NU || j >= b.m_NV)
			return NO_HIT;
		return b.m_H[j * b.m_NU + i];
	}

	//! the roof carried on to sample (i, j) along (di, dj) from the samples n and n + dn steps away (n the first step
	//! beyond the part standing out, dist = |n|, dn -1 or 1); NO_HIT when one of the two is missing
	protected float CarryFrom(SZ_RoofBuilding b, int i, int j, int di, int dj, int n, int dist, int dn)
	{
		float a1 = GridAt(b, i + n * di, j + n * dj);
		if (a1 == NO_HIT)
			return NO_HIT;
		float a2 = GridAt(b, i + (n + dn) * di, j + (n + dn) * dj);
		if (a2 == NO_HIT)
			return NO_HIT;
		return a1 + (a1 - a2) * dist;
	}

	//! the roof height under sample (i, j) when the sample stands out of the roof along (di, dj): alone, or together
	//! with the next or the previous sample when both stand out less than a fold; NO_HIT when it does not. Whether it
	//! stands out is judged on the roof carried on from beyond both ends, the higher one (NO_HIT is the lowest of all
	//! heights, so a missing end counts for nothing): a ridge and a hip carry on to their own height
	protected float SpikeBase(SZ_RoofBuilding b, int i, int j, int di, int dj, float fold)
	{
		float h = GridAt(b, i, j);
		float lo = CarryFrom(b, i, j, di, dj, -1, 1, -1);
		float hi = CarryFrom(b, i, j, di, dj, 1, 1, 1);
		float e = Math.Max(lo, hi);
		if (e == NO_HIT)
			return NO_HIT;
		if (h - e >= SPIKE)
			return Across(b, i, j, di, dj, -1, 1, e);
		// two samples wide: the low end stays, the high end moves past the next sample (or the other way round)
		if (h - lo >= SPIKE)
		{
			float e2 = Math.Max(lo, CarryFrom(b, i, j, di, dj, 2, 2, 1));
			if (e2 != NO_HIT && h - e2 >= SPIKE && h - e2 <= fold && PairOut(b, i + di, j + dj, di, dj, -1, fold))
				return Across(b, i, j, di, dj, -1, 2, e2);
		}
		if (h - hi >= SPIKE)
		{
			float e3 = Math.Max(hi, CarryFrom(b, i, j, di, dj, -2, 2, -1));
			if (e3 != NO_HIT && h - e3 >= SPIKE && h - e3 <= fold && PairOut(b, i - di, j - dj, di, dj, 1, fold))
				return Across(b, i, j, di, dj, -2, 1, e3);
		}
		return NO_HIT;
	}

	//! the roof under a part standing out, from the samples s (below 0) and t (above 0) steps away beyond its ends: on
	//! the straight line between them (exact on a plane, a little below a ridge), or the carried on height e where one
	//! of them is missing
	protected float Across(SZ_RoofBuilding b, int i, int j, int di, int dj, int s, int t, float e)
	{
		float a = GridAt(b, i + s * di, j + s * dj);
		float c = GridAt(b, i + t * di, j + t * dj);
		if (a == NO_HIT || c == NO_HIT)
			return e;
		float f = -s;
		f = f / (t - s);
		return a + (c - a) * f;
	}

	//! the other sample of a part two samples wide stands out as well: the part is this sample and the one at back
	//! (-1 or 1 steps along (di, dj)), carried on from beyond both
	protected bool PairOut(SZ_RoofBuilding b, int i, int j, int di, int dj, int back, float fold)
	{
		float h = GridAt(b, i, j);
		if (h == NO_HIT)
			return false;
		float e = Math.Max(CarryFrom(b, i, j, di, dj, 2 * back, 2, back), CarryFrom(b, i, j, di, dj, -back, 1, -back));
		return e != NO_HIT && h - e >= SPIKE && h - e <= fold;
	}

	//! two samples on one continuous surface: both on the object and no step between them
	protected bool Joined(SZ_RoofBuilding b, float ha, float hb)
	{
		return ha != NO_HIT && hb != NO_HIT && Math.AbsFloat(ha - hb) <= Math.Min(b.m_StepU, b.m_StepV) * 1.35;
	}

	//! Joined for two neighbouring samples of the grid (by index), unless there is a step between them
	protected bool JoinedK(SZ_RoofBuilding b, int ka, int kb)
	{
		if (!Joined(b, b.m_H[ka], b.m_H[kb]))
			return false;
		return !DropStep(b, ka, kb);
	}

	//! close range grid: the height between two neighbouring samples is much steeper than the slope beside them on
	//! either side (a roof edge above a lower roof, a ledge, a chimney): two surfaces, not one
	protected bool DropStep(SZ_RoofBuilding b, int ka, int kb)
	{
		if (b.m_Kind != 0 || !b.m_Fine)
			return false;
		float across = Math.AbsFloat(b.m_H[kb] - b.m_H[ka]);
		if (across <= DROP_TOL)
			return false;
		int dk = kb - ka;
		float side = -1.0;
		int ka2 = ka - dk;
		if (SameLine(b, ka, ka2) && Joined(b, b.m_H[ka2], b.m_H[ka]))
			side = Math.AbsFloat(b.m_H[ka] - b.m_H[ka2]);
		int kb2 = kb + dk;
		if (SameLine(b, kb, kb2) && Joined(b, b.m_H[kb], b.m_H[kb2]))
			side = Math.Max(side, Math.AbsFloat(b.m_H[kb2] - b.m_H[kb]));
		if (side < 0)
			return false;
		return across > side + DROP_TOL;
	}

	//! a sample index and its neighbour one step further along the same row or column of the grid
	protected bool SameLine(SZ_RoofBuilding b, int k, int k2)
	{
		if (k2 < 0 || k2 >= b.m_H.Count())
			return false;
		int d = k2 - k;
		if (d == 1 || d + 1 == 0)
		{
			int r1 = k / b.m_NU;
			int r2 = k2 / b.m_NU;
			return r1 == r2;
		}
		return true;
	}

	//! the sampled surface is walkable there: a roadway lies within STAIR_ROAD of it (cached per sample)
	protected bool Walkable(SZ_RoofBuilding b, int k, map<int, bool> cache)
	{
		bool known;
		if (cache.Find(k, known))
			return known;
		int i = k % b.m_NU;
		int j = k / b.m_NU;
		vector p = SamplePos(b, i, j);
		float h = b.m_H[k];
		float road = g_Game.SurfaceRoadY3D(p[0], h + STAIR_ROAD + 0.05, p[2], RoadSurfaceDetection.UNDER);
		bool walk = road <= h + STAIR_ROAD && road >= h - STAIR_ROAD;
		cache.Set(k, walk);
		return walk;
	}

	//! close range grid: samples on stairs that come down to the ground get no snow (see STAIR_FOOT, STAIR_SLOPE)
	protected void DropStairs(SZ_RoofBuilding b)
	{
		if (b.m_Kind != 0 || !b.m_Fine || b.m_Small)
			return;
		int nu = b.m_NU;
		int total = b.m_H.Count();
		map<int, bool> walk = new map<int, bool>;
		array<int> parent = new array<int>;
		array<bool> sloped = new array<bool>;
		for (int k = 0; k < total; k++)
		{
			parent.Insert(k);
			sloped.Insert(false);
		}
		bool found = false;
		for (int a = 0; a < total; a++)
		{
			float ha = b.m_H[a];
			if (ha == NO_HIT)
				continue;
			for (int dir = 0; dir < 2; dir++)
			{
				int n = a + 1;
				if (dir == 1)
					n = a + nu;
				if (!SameLine(b, a, n))
					continue;
				float hn = b.m_H[n];
				float run = b.m_StepU;
				if (dir == 1)
					run = b.m_StepV;
				if (!Joined(b, ha, hn) || Math.AbsFloat(hn - ha) <= Math.Max(JOIN_TOL, run * STAIR_SLOPE))
					continue;
				if (!Walkable(b, a, walk) || !Walkable(b, n, walk))
					continue;
				sloped[a] = true;
				sloped[n] = true;
				int ra = UnionRoot(parent, a);
				int rn = UnionRoot(parent, n);
				if (ra != rn)
					parent[ra] = rn;
				found = true;
			}
		}
		if (!found)
			return;
		// the lowest point of every walkable slope above the ground
		map<int, float> lowest = new map<int, float>;
		for (int s = 0; s < total; s++)
		{
			if (!sloped[s])
				continue;
			int si = s % nu;
			int sj = s / nu;
			vector sp = SamplePos(b, si, sj);
			float ground = GroundAt(sp[0], sp[2]);
			float above = b.m_H[s] - ground;
			int root = UnionRoot(parent, s);
			float low;
			if (!lowest.Find(root, low) || above < low)
				lowest.Set(root, above);
		}
		for (int c = 0; c < total; c++)
		{
			if (!sloped[c])
				continue;
			int rc = UnionRoot(parent, c);
			float foot = lowest.Get(rc);
			if (foot > STAIR_FOOT)
				continue;
			b.m_H[c] = NO_HIT;
			b.m_Stair.Set(c, true);
		}
	}

	//! the grid edges where a surface ends: between a sample on the building and one beside it, and at steps
	//! (chimneys, dormers, walls rising above a roof, a lower roof), where both sides end. Edge index: the sample
	//! index of its lower end twice, plus one along V. Cross key: the edge index twice, plus one when the surface is
	//! the one of the edge's upper end
	protected void CollectEdges(SZ_RoofBuilding b)
	{
		for (int j = 0; j < b.m_NV; j++)
		{
			for (int i = 0; i < b.m_NU; i++)
			{
				int k = j * b.m_NU + i;
				int e = k * 2;
				if (i + 1 < b.m_NU)
					AddEdge(b, e, k, k + 1);
				if (j + 1 < b.m_NV)
					AddEdge(b, e + 1, k, k + b.m_NU);
			}
		}
		b.m_EdgeCursor = 0;
	}

	protected void AddEdge(SZ_RoofBuilding b, int e, int kLow, int kHigh)
	{
		if (JoinedK(b, kLow, kHigh))
			return;
		if (b.m_H[kLow] != NO_HIT)
			b.m_EdgeKeys.Insert(e * 2);
		if (b.m_H[kHigh] != NO_HIT)
			b.m_EdgeKeys.Insert(e * 2 + 1);
	}

	//! finds where a surface ends on one edge: halving it from the sample on the surface towards the other end. A
	//! point counts as the surface while a ray finds the building there at the height the surface predicts, so a
	//! wall rising above the roof, a chimney or a lower part of the building ends it as well as the roof's rim
	protected void RefineEdge(SZ_RoofBuilding b)
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
		bool slopeKnown = false;
		int ni = si - (xi - si);
		int nj = sj - (xj - sj);
		if (ni >= 0 && ni < b.m_NU && nj >= 0 && nj < b.m_NV)
		{
			if (JoinedK(b, sj * b.m_NU + si, nj * b.m_NU + ni))
			{
				float hn = HAt(b, ni, nj);
				slope = (hs - hn) / step;
				slopeKnown = true;
			}
		}
		// next to stairs the surface ends where the rays leave its height, so the snow of a landing does not reach
		// out over the top steps
		float within = 0.25;
		int kx = xj * b.m_NU + xi;
		if (b.m_Stair.Contains(kx))
			within = STEP_REFINE;
		vector ps = SamplePos(b, si, sj);
		vector px = SamplePos(b, xi, xj);
		bool measured = b.m_Kind == 0 && SZ_State.s_DebugRoofCorner;
		if ((!slopeKnown || measured) && b.m_Kind == 0)
		{
			// no sample of this surface behind it: a short ray just inside measures its slope towards the edge, so
			// the end found follows a sloping roof instead of a level line above it. Buildings measure it always: at
			// a corner or the foot of a hip the sample behind lies on the level eave while the roof falls away
			// towards the edge, and the snow would run on level as a shelf above the overhang
			vector pf = ps + (px - ps) * (EDGE_PROBE / step);
			float hp = SampleNear(b, pf[0], pf[2], hs, 0.4, 0.4);
			if (hp != NO_HIT && Math.AbsFloat(hp - hs) <= EDGE_PROBE * 1.5)
				slope = (hp - hs) / EDGE_PROBE;
		}
		float lo = 0;
		float up = 1;
		// the farthest point found on the surface and its height there
		float tLo = 0;
		float hLo = hs;
		for (int k = 0; k < EDGE_STEPS; k++)
		{
			float mid = (lo + up) * 0.5;
			vector pm = ps + (px - ps) * mid;
			float expect = hs + slope * step * mid;
			// a short ray around the expected height (an overhang up to 1.5 m above it still ends the surface)
			float hm = SampleNear(b, pm[0], pm[2], expect, 1.5, 0.4);
			if (hm != NO_HIT && Math.AbsFloat(hm - expect) <= within)
			{
				lo = mid;
				if (mid > tLo)
				{
					tLo = mid;
					hLo = hm;
				}
			}
			else
				up = mid;
		}
		// the first point found off the surface: the snow reaches the rim or a little into the wall (which hides
		// it), so no strip of roof shows between the snow and a wall
		float t = up;
		vector c = ps + (px - ps) * t;
		c[1] = hs + slope * step * t;
		// at the height the rays found the surface (carried on to the rim), not the one predicted
		if (measured && tLo > 0.05)
			c[1] = hs + (hLo - hs) * (t / tLo);
		b.m_Cross.Set(key, c);
	}

	protected float HAt(SZ_RoofBuilding b, int i, int j)
	{
		return b.m_H[j * b.m_NU + i];
	}

	protected vector CornerAt(SZ_RoofBuilding b, int i, int j)
	{
		vector p = SamplePos(b, i, j);
		p[1] = HAt(b, i, j);
		return p;
	}

	//! one piece at the edge of a roof, from three points on the roof (any order)
	protected SZ_RoofTri AddFree(SZ_RoofBuilding b, int gi, int gj, vector p0, vector p1, vector p2)
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
		SZ_RoofTri t = new SZ_RoofTri();
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
	protected void BuildEdgeCell(SZ_RoofBuilding b, int i, int j, array<int> sgrp, array<bool> gridGroup)
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
				if (grp[cf] >= 0 || !JoinedK(b, cj[pf] * nu + ci[pf], cj[cf] * nu + ci[cf]))
					break;
				grp[cf] = a;
			}
			for (int d2 = 1; d2 < 4; d2++)
			{
				int pb = (a - d2 + 5) % 4;
				int cb = (a - d2 + 4) % 4;
				if (grp[cb] >= 0 || !JoinedK(b, cj[pb] * nu + ci[pb], cj[cb] * nu + ci[cb]))
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
			// the side of the cell each point of the piece lies on (-1: a corner of the cell)
			array<int> sides = new array<int>;
			bool ok = true;
			for (int s = 0; s < 4; s++)
			{
				int n = (s + 1) % 4;
				bool inS = grp[s] == g;
				bool inN = grp[n] == g;
				if (inS)
				{
					poly.Insert(CornerAt(b, ci[s], cj[s]));
					sides.Insert(-1);
				}
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
				sides.Insert(s);
			}
			if (!ok)
				continue;
			if (SZ_State.s_DebugRoofCorner)
				SquareCorner(b, ci, cj, grp, g, poly, sides);
			for (int f = 1; f + 1 < poly.Count(); f++)
				AddFree(b, i, j, poly[0], poly[f], poly[f + 1]);
		}
	}

	//! the surface of a piece ends on two neighbouring sides of its cell: the rim of nearly every roof turns a right
	//! angle there in the building's own axes (an outer corner of the roof, or the inner corner of an L-shaped roof or
	//! around a chimney). The straight line between the two ends would cut the corner of the roof off, or hang over the
	//! air at an inner corner, so the point of the right angle is added to the piece when a short ray beside it finds
	//! the roof there (outer corner) or does not (inner corner)
	protected void SquareCorner(SZ_RoofBuilding b, array<int> ci, array<int> cj, array<int> grp, int g, array<vector> poly, array<int> sides)
	{
		int n = poly.Count();
		for (int a = 0; a < n; a++)
		{
			int c = (a + 1) % n;
			int sa = sides[a];
			int sc = sides[c];
			if (sa < 0 || sc < 0 || (sa + sc) % 2 == 0)
				continue;
			// the corner of the cell the two sides share (side s runs from corner s to corner s + 1)
			int k = sa;
			if ((sa + 1) % 4 == sc)
				k = sc;
			// sides 0 and 2 run along U, 1 and 3 along V
			vector pu = poly[a];
			vector pv = poly[c];
			if (sa % 2 == 1)
			{
				pu = poly[c];
				pv = poly[a];
			}
			bool outer = grp[k] == g;
			float hk;
			if (outer)
				hk = HAt(b, ci[k], cj[k]);
			else
			{
				float h1 = HAt(b, ci[(k + 1) % 4], cj[(k + 1) % 4]);
				float h2 = HAt(b, ci[(k + 2) % 4], cj[(k + 2) % 4]);
				float h3 = HAt(b, ci[(k + 3) % 4], cj[(k + 3) % 4]);
				if (h1 == NO_HIT || h2 == NO_HIT || h3 == NO_HIT)
					return;
				hk = h1 + h3 - h2;
			}
			// the right angle: along U where the U side ends, along V where the V side ends, on the plane of the cell
			float along = (pv[0] - pu[0]) * b.m_V[0] + (pv[2] - pu[2]) * b.m_V[2];
			vector x = pu + b.m_V * along;
			x[1] = pu[1] + pv[1] - hk;
			// a corner right next to one of the two ends adds nothing but a sliver
			if (Math.AbsFloat(along) < 0.02 || vector.DistanceSq(Vector(x[0], 0, x[2]), Vector(pv[0], 0, pv[2])) < 0.0004)
				return;
			vector kp = SamplePos(b, ci[k], cj[k]);
			float du = (kp[0] - x[0]) * b.m_U[0] + (kp[2] - x[2]) * b.m_U[2];
			float dv = (kp[0] - x[0]) * b.m_V[0] + (kp[2] - x[2]) * b.m_V[2];
			vector probe = x + b.m_U * Math.Clamp(du * 0.5, -0.06, 0.06) + b.m_V * Math.Clamp(dv * 0.5, -0.06, 0.06);
			float hp = SampleNear(b, probe[0], probe[2], x[1], 0.2, 0.3);
			bool onRoof = hp != NO_HIT && Math.AbsFloat(hp - x[1]) <= 0.15;
			if (onRoof != outer)
				return;
			poly.InsertAt(x, c);
			sides.InsertAt(-1, c);
			if (!outer)
			{
				// an L-shaped piece: fanned out from its inner corner, which sees all its other corners
				array<vector> turned = new array<vector>;
				int m = poly.Count();
				for (int r = 0; r < m; r++)
					turned.Insert(poly[(c + r) % m]);
				poly.Clear();
				poly.InsertAll(turned);
			}
			return;
		}
	}

	protected bool FullCell(SZ_RoofBuilding b, int i, int j)
	{
		float h00 = HAt(b, i, j);
		float h10 = HAt(b, i + 1, j);
		float h11 = HAt(b, i + 1, j + 1);
		float h01 = HAt(b, i, j + 1);
		if (h00 == NO_HIT || h10 == NO_HIT || h11 == NO_HIT || h01 == NO_HIT)
			return false;
		float lo = Math.Min(Math.Min(h00, h10), Math.Min(h11, h01));
		float hi = Math.Max(Math.Max(h00, h10), Math.Max(h11, h01));
		if (hi - lo > Math.Min(b.m_StepU, b.m_StepV) * 1.35)
			return false;
		// all four sides on one surface: a cell across stair treads or a step between roofs is no full cell
		int k00 = j * b.m_NU + i;
		int k10 = k00 + 1;
		int k01 = k00 + b.m_NU;
		int k11 = k01 + 1;
		return JoinedK(b, k00, k10) && JoinedK(b, k10, k11) && JoinedK(b, k11, k01) && JoinedK(b, k01, k00);
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
	protected bool BlockPlanar(SZ_RoofBuilding b, int i, int j, int span)
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
	protected void AddTri(SZ_RoofBuilding b, int shape, int gi, int gj, float su, float sv, float h00, float h10, float h11, float h01)
	{
		AddTriAt(b, shape, gi * b.m_StepU, gj * b.m_StepV, gi, gj, su, sv, h00, h10, h11, h01);
	}

	//! the same for a rectangle starting at (u0, v0) metres along the grid axes; vi, vj pick the texture variant
	protected void AddTriAt(SZ_RoofBuilding b, int shape, float u0, float v0, int vi, int vj, float su, float sv, float h00, float h10, float h11, float h01)
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

		SZ_RoofTri t = new SZ_RoofTri();
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

	protected void AddSquare(SZ_RoofBuilding b, int gi, int gj, int span)
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
		// the diagonal the roof runs straight along: a ridge, a hip or a valley across the square lies on it. Where
		// that is unclear, the higher one keeps the snow on top of ridges instead of inside them (in a valley it would
		// bridge it, a row of steps along the valley)
		bool alongA = (h00 + h11) >= (h10 + h01);
		if (SZ_State.s_DebugRoofFillDiag)
		{
			float bendA = Bend(b, gi, gj, span, span, h00, h11);
			float bendB = Bend(b, gi + span, gj, -span, span, h10, h01);
			if (bendA >= 0 && bendB >= 0 && Math.AbsFloat(bendA - bendB) > 0.05)
				alongA = bendA < bendB;
		}
		if (alongA)
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

	//! how much the roof bends along a diagonal of a grid square, from corner (i, j) in steps (di, dj) to the opposite
	//! corner: the mean size of the second differences of the heights on the line through the two corners (h0, h1) and
	//! the samples beyond them; -1 when both samples beyond are off the roof
	protected float Bend(SZ_RoofBuilding b, int i, int j, int di, int dj, float h0, float h1)
	{
		float sum = 0;
		int n = 0;
		float before = GridAt(b, i - di, j - dj);
		if (before != NO_HIT)
		{
			sum += Math.AbsFloat(before - 2.0 * h0 + h1);
			n++;
		}
		float after = GridAt(b, i + 2 * di, j + 2 * dj);
		if (after != NO_HIT)
		{
			sum += Math.AbsFloat(h0 - 2.0 * h1 + after);
			n++;
		}
		if (n == 0)
			return -1;
		return sum / n;
	}

	//! one square of span x span grid cells on a plane (its corners within a few centimetres of one plane)
	protected void AddQuad(SZ_RoofBuilding b, int gi, int gj, int span, float h00, float h10, float h11, float h01)
	{
		float su = b.m_StepU * span;
		float sv = b.m_StepV * span;
		float a = ((h10 - h00) + (h11 - h01)) * 0.5 / su;
		float bb = ((h01 - h00) + (h11 - h10)) * 0.5 / sv;
		SZ_RoofTri t = new SZ_RoofTri();
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
	protected void BuildTris(SZ_RoofBuilding b)
	{
		b.m_Tris.Clear();
		b.m_CapInfo = "";
		b.m_Job = null;
		// rocks keep the grid: the planes of a curved rock become plates standing off its flanks (their snow is baked;
		// this is the snow of the tilted ones)
		if (b.m_Cross.Count() > 0 && !b.m_Rock && (SZ_State.s_DebugRoofCaps >= 2 || (SZ_State.s_DebugRoofCaps == 1 && (b.m_Small || b.m_Wall))))
		{
			SZ_CapJob job = new SZ_CapJob();
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
	protected void FinishTris(SZ_RoofBuilding b)
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
		if (b.m_Kind == 0 && b.m_Job && SZ_State.s_DebugRoofCorner)
			FillGaps(b);
		// small structures too: the slats, beams and frames of benches, sawhorses and racks leave gaps the grid
		// pieces would bridge. Buildings keep theirs (eaves and overhangs often have no fire geometry)
		if (b.m_Kind == 1 || b.m_Small)
			DropUnsupported(b);
		if (b.m_Small && SZ_State.s_DebugRoofCorner)
			DropOutOfRange(b);
		if (b.m_Rock && SZ_State.s_DebugRoofCorner)
			DropSteep(b, ROCK_NY);
		b.m_Job = null;
		b.m_H.Clear();
		b.m_NY.Clear();
		b.m_Stair.Clear();
		b.m_Cross2.Clear();
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

	//! test points of a grid cell for the coverage check of FillGaps: its centre and four points a quarter in from its
	//! corners (in cells)
	static const ref array<float> FILL_U = {0.5, 0.25, 0.75, 0.75, 0.25};
	static const ref array<float> FILL_V = {0.5, 0.25, 0.25, 0.75, 0.75};
	//! grid pieces filling a gap lie this much lower than the polygons: where they reach under a polygon they stay
	//! hidden instead of flickering against it
	static const float FILL_LOWER = 0.015;

	//! the polygons of plane roofs can leave gaps where their planes meet (valleys, ridges, the junction of two roofs,
	//! small parts between them) and at corners: every grid cell is checked at five points, and where one of them lies
	//! under no piece, those of the cell's own grid pieces that cover it are added, a little lower
	protected void FillGaps(SZ_RoofBuilding b)
	{
		int nu = b.m_NU - 1;
		int nv = b.m_NV - 1;
		if (nu <= 0 || nv <= 0)
			return;
		int nq = FILL_U.Count();
		array<bool> cov = new array<bool>;
		cov.Resize(nu * nv * nq);
		for (int z = 0; z < cov.Count(); z++)
			cov[z] = false;
		array<vector> cs = new array<vector>;
		array<float> pu = new array<float>;
		array<float> pv = new array<float>;
		int existing = b.m_Tris.Count();
		for (int t = 0; t < existing; t++)
		{
			PieceCorners(b.m_Tris[t], cs);
			PieceGrid(b, cs, pu, pv);
			float lu = pu[0];
			float hu = pu[0];
			float lv = pv[0];
			float hv = pv[0];
			for (int c = 1; c < pu.Count(); c++)
			{
				lu = Math.Min(lu, pu[c]);
				hu = Math.Max(hu, pu[c]);
				lv = Math.Min(lv, pv[c]);
				hv = Math.Max(hv, pv[c]);
			}
			int i0 = Math.Max(0, Math.Floor(lu));
			int i1 = Math.Min(nu - 1, Math.Floor(hu));
			int j0 = Math.Max(0, Math.Floor(lv));
			int j1 = Math.Min(nv - 1, Math.Floor(hv));
			for (int cj = j0; cj <= j1; cj++)
			{
				for (int ci = i0; ci <= i1; ci++)
				{
					int cb = (cj * nu + ci) * nq;
					for (int q = 0; q < nq; q++)
					{
						if (!cov[cb + q] && InConvex(pu, pv, ci + FILL_U[q], cj + FILL_V[q]))
							cov[cb + q] = true;
					}
				}
			}
		}
		m_Cost += existing * 0.01;
		for (int j = 0; j < nv; j++)
		{
			for (int i = 0; i < nu; i++)
			{
				int cellBase = (j * nu + i) * nq;
				bool gap = false;
				for (int q1 = 0; q1 < nq; q1++)
				{
					if (!cov[cellBase + q1])
					{
						gap = true;
						break;
					}
				}
				if (!gap)
					continue;
				int before = b.m_Tris.Count();
				if (FullCell(b, i, j))
					AddFillSquare(b, i, j);
				else if (b.m_Cross.Count() > 0)
					BuildEdgeCell(b, i, j, null, null);
				// only the new pieces over one of the open points of the cell stay
				for (int n = b.m_Tris.Count() - 1; n >= before; n--)
				{
					PieceCorners(b.m_Tris[n], cs);
					PieceGrid(b, cs, pu, pv);
					bool fills = false;
					for (int q2 = 0; q2 < nq; q2++)
					{
						if (!cov[cellBase + q2] && InConvex(pu, pv, i + FILL_U[q2], j + FILL_V[q2]))
						{
							fills = true;
							break;
						}
					}
					if (fills)
						b.m_Tris[n].m_Lower = FILL_LOWER;
					else
						b.m_Tris.RemoveOrdered(n);
				}
			}
		}
	}

	//! the grid square of a cell filling a gap. Where a valley or a ridge runs across the cell its two diagonals give
	//! different surfaces: AddSquare takes the higher one, which bridges a valley above the polygons on either side and
	//! shows as a row of steps along it. A ray at the cell's centre finds the roof there; the diagonal that runs closest
	//! to it is taken (the lower one when the ray finds nothing, so the piece stays under the polygons)
	protected void AddFillSquare(SZ_RoofBuilding b, int i, int j)
	{
		float h00 = HAt(b, i, j);
		float h10 = HAt(b, i + 1, j);
		float h11 = HAt(b, i + 1, j + 1);
		float h01 = HAt(b, i, j + 1);
		float da = (h00 + h11) * 0.5;
		float db = (h10 + h01) * 0.5;
		float apart = Math.AbsFloat(da - db);
		if (!SZ_State.s_DebugRoofFillDiag || apart < 0.03 || Planar(h00, h10, h11, h01))
		{
			AddSquare(b, i, j, 1);
			return;
		}
		vector w = b.m_Origin + b.m_U * ((i + 0.5) * b.m_StepU) + b.m_V * ((j + 0.5) * b.m_StepV);
		float hc = SampleNear(b, w[0], w[2], (da + db) * 0.5, apart + 0.3, apart + 0.3);
		bool alongA = da <= db;
		if (hc != NO_HIT)
			alongA = Math.AbsFloat(hc - da) <= Math.AbsFloat(hc - db);
		if (alongA)
		{
			AddTri(b, 0, i, j, b.m_StepU, b.m_StepV, h00, h10, h11, h01);
			AddTri(b, 1, i, j, b.m_StepU, b.m_StepV, h00, h10, h11, h01);
		}
		else
		{
			AddTri(b, 2, i, j, b.m_StepU, b.m_StepV, h00, h10, h11, h01);
			AddTri(b, 3, i, j, b.m_StepU, b.m_StepV, h00, h10, h11, h01);
		}
	}

	//! the corners of a piece in grid cells along U and V
	protected void PieceGrid(SZ_RoofBuilding b, array<vector> cs, array<float> pu, array<float> pv)
	{
		pu.Clear();
		pv.Clear();
		foreach (vector p : cs)
		{
			float dx = p[0] - b.m_Origin[0];
			float dz = p[2] - b.m_Origin[2];
			pu.Insert((dx * b.m_U[0] + dz * b.m_U[2]) / b.m_StepU);
			pv.Insert((dx * b.m_V[0] + dz * b.m_V[2]) / b.m_StepV);
		}
	}

	//! a point lies in a convex polygon (or on its rim), in either winding
	protected bool InConvex(array<float> pu, array<float> pv, float x, float y)
	{
		int n = pu.Count();
		if (n < 3)
			return false;
		bool neg = false;
		bool pos = false;
		for (int k = 0; k < n; k++)
		{
			int m = (k + 1) % n;
			float cr = (pu[m] - pu[k]) * (y - pv[k]) - (pv[m] - pv[k]) * (x - pu[k]);
			if (cr < -0.0001)
				neg = true;
			else if (cr > 0.0001)
				pos = true;
			if (neg && pos)
				return false;
		}
		return true;
	}

	//! the corners of a piece (three, or four for a square), on its plane
	protected void PieceCorners(SZ_RoofTri t, array<vector> cs)
	{
		cs.Clear();
		if (t.m_Free)
		{
			cs.Insert(t.m_P0);
			cs.Insert(t.m_P1);
			cs.Insert(t.m_P2);
			return;
		}
		vector hu = t.m_AxisU * 0.5;
		vector hv = t.m_AxisV * 0.5;
		vector c00 = t.m_Center - hu - hv;
		vector c10 = t.m_Center + hu - hv;
		vector c11 = t.m_Center + hu + hv;
		vector c01 = t.m_Center - hu + hv;
		if (t.m_Quad || t.m_Shape == 0 || t.m_Shape == 1 || t.m_Shape == 2)
			cs.Insert(c00);
		if (t.m_Quad || t.m_Shape == 0 || t.m_Shape == 2 || t.m_Shape == 3)
			cs.Insert(c10);
		if (t.m_Quad || t.m_Shape == 0 || t.m_Shape == 1 || t.m_Shape == 3)
			cs.Insert(c11);
		if (t.m_Quad || t.m_Shape == 1 || t.m_Shape == 2 || t.m_Shape == 3)
			cs.Insert(c01);
	}

	//! walls, fences, wrecks and small structures: drops the pieces that hang over a gap (see WALL_GAP)
	protected void DropUnsupported(SZ_RoofBuilding b)
	{
		array<vector> cs = new array<vector>;
		for (int i = b.m_Tris.Count() - 1; i >= 0; i--)
		{
			SZ_RoofTri t = b.m_Tris[i];
			PieceCorners(t, cs);
			int nc = cs.Count();
			if (nc < 3)
				continue;
			vector g = "0 0 0";
			for (int c = 0; c < nc; c++)
				g = g + cs[c];
			g = g * (1.0 / nc);
			int bad = 0;
			for (int q = -1; q < nc && bad < 2; q++)
			{
				vector p = g;
				if (q >= 0)
					p = g + (cs[q] - g) * 0.7;
				float h = SampleNear(b, p[0], p[2], p[1], 0.1, 0.4);
				if (h == NO_HIT || p[1] - h > WALL_GAP)
					bad++;
			}
			if (bad >= 2)
				b.m_Tris.Remove(i);
		}
	}

	//! drops the pieces steeper than a slope (normal y below ny)
	protected void DropSteep(SZ_RoofBuilding b, float ny)
	{
		for (int i = b.m_Tris.Count() - 1; i >= 0; i--)
		{
			if (b.m_Tris[i].m_Normal[1] < ny)
				b.m_Tris.Remove(i);
		}
	}

	//! small structures: drops the pieces reaching well below the lowest or above the highest point the rays found
	//! on the structure. They belong to a plane carried on past it: on a barrier basket the wire rim and the sand
	//! inside it make a steep plane that runs down the basket's side
	protected void DropOutOfRange(SZ_RoofBuilding b)
	{
		float lo = 1000000;
		float hi = -1000000;
		foreach (float h : b.m_H)
		{
			if (h == NO_HIT)
				continue;
			lo = Math.Min(lo, h);
			hi = Math.Max(hi, h);
		}
		if (hi < lo)
			return;
		array<vector> cs = new array<vector>;
		for (int i = b.m_Tris.Count() - 1; i >= 0; i--)
		{
			PieceCorners(b.m_Tris[i], cs);
			foreach (vector c : cs)
			{
				if (c[1] < lo - RANGE_TOL || c[1] > hi + RANGE_TOL)
				{
					b.m_Tris.Remove(i);
					break;
				}
			}
		}
	}

	//! one step of a structure's polygons; true when they are all done
	protected bool CapStep(SZ_RoofBuilding b)
	{
		SZ_CapJob job = b.m_Job;
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

	protected void NextGroup(SZ_CapJob job)
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
	protected void BuildGridTris(SZ_RoofBuilding b, array<int> sgrp, array<bool> gridGroup)
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
			if (span > SZ_State.s_DebugRoofMaxSpan)
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
	protected string CapSample(SZ_RoofBuilding b, int k)
	{
		vector p = b.m_Origin + b.m_U * SU(b, k) + b.m_V * SV(b, k);
		return string.Format("%1 %2 h=%3", p[0], p[2], b.m_H[k] - b.m_Ground);
	}

	//! the polygons of walls and small structures: cut into bands across their long side, at least a metre and no
	//! more than three times as long as wide, so the snow texture is stretched no more than on the grid pieces. A band
	//! that is a whole rectangle becomes two pieces with one texture mapping, the bands at the ends a fan
	protected void EmitFan(SZ_RoofBuilding b, array<float> poly, array<float> planes, int p)
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
				SZ_RoofTri t = AddFree(b, k, p, w0, w1, w2);
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
	protected void EmitCap(SZ_RoofBuilding b, array<float> poly, array<float> planes, int p)
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
		int eb = SZ_State.s_DebugEdgeBlock;
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
			if (span > SZ_State.s_DebugRoofMaxSpan)
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
	protected void PlaneSquare(SZ_RoofBuilding b, int gi, int gj, int span, array<float> planes, int p)
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
	protected int GroupSurfaces(SZ_RoofBuilding b, array<int> grp)
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
					if (grp[nidx] >= 0 || !JoinedK(b, cur, nidx))
						continue;
					grp[nidx] = groups;
					todo.Insert(nidx);
				}
			}
			groups++;
		}
		return groups;
	}

	protected float SU(SZ_RoofBuilding b, int k)
	{
		int i = k % b.m_NU;
		return i * b.m_StepU;
	}

	protected float SV(SZ_RoofBuilding b, int k)
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
	protected float FitSamples(SZ_RoofBuilding b, array<int> list, out float h0, out float gu, out float gv, out float cu, out float cv)
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
			gv = CrossSlope(b, cu, cv, h0, true);
		}
		else if (svv > 0.0001)
		{
			gv = svh / svv;
			gu = CrossSlope(b, cu, cv, h0, false);
		}
		else
		{
			gu = CrossSlope(b, cu, cv, h0, false);
			gv = CrossSlope(b, cu, cv, h0, true);
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

	//! slope of a building's surface along one grid axis at a point (grid coordinates, metres), measured with a short
	//! ray to either side: for surfaces sampled in one row only, whose samples do not tell it (0 when not found)
	protected float CrossSlope(SZ_RoofBuilding b, float u, float v, float h, bool alongV)
	{
		if (b.m_Kind != 0)
			return 0;
		int iu = Math.Round(u / b.m_StepU * 2.0);
		int iv = Math.Round(v / b.m_StepV * 2.0);
		int key = (iu * 4096 + iv) * 2;
		if (alongV)
			key++;
		float known;
		if (b.m_Cross2.Find(key, known))
			return known;
		vector axis = b.m_U;
		if (alongV)
			axis = b.m_V;
		vector p = b.m_Origin + b.m_U * u + b.m_V * v;
		vector pa = p + axis * CROSS_PROBE;
		vector pb = p - axis * CROSS_PROBE;
		float ha = SampleNear(b, pa[0], pa[2], h, 0.5, 0.5);
		float hb = SampleNear(b, pb[0], pb[2], h, 0.5, 0.5);
		float g = 0;
		if (!SZ_State.s_DebugRoofCorner)
		{
			if (ha != NO_HIT && hb != NO_HIT)
				g = (ha - hb) / (2.0 * CROSS_PROBE);
			else if (ha != NO_HIT)
				g = (ha - h) / CROSS_PROBE;
			else if (hb != NO_HIT)
				g = (h - hb) / CROSS_PROBE;
		}
		else if (ha != NO_HIT && hb != NO_HIT)
		{
			// only a surface running on straight through the point: the two probes can land on different parts (the
			// wire rim and the sand of a barrier basket), and a strip of snow tilted by their difference stands out
			if (Math.AbsFloat((ha - h) - (h - hb)) <= CROSS_AGREE)
				g = (ha - hb) / (2.0 * CROSS_PROBE);
		}
		else if (ha != NO_HIT || hb != NO_HIT)
		{
			// one side only (the edge of the surface): a second probe further out on that side has to agree
			float side = 1.0;
			float h1 = ha;
			if (ha == NO_HIT)
			{
				side = -1.0;
				h1 = hb;
			}
			vector p2 = p + axis * (2.0 * CROSS_PROBE * side);
			float h2 = SampleNear(b, p2[0], p2[2], h1 + (h1 - h), 0.3, 0.3);
			if (h2 != NO_HIT && Math.AbsFloat((h2 - h1) - (h1 - h)) <= CROSS_AGREE)
				g = (h1 - h) / CROSS_PROBE * side;
		}
		if (Math.AbsFloat(g) > 1.5)
			g = 0;
		b.m_Cross2.Set(key, g);
		return g;
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
	protected bool SplitPlanes(SZ_RoofBuilding b, array<int> grp, int g, array<int> mine, map<int, int> regOf, array<ref map<int, bool>> sets, array<ref array<int>> lists, array<float> planes)
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
			if (SZ_State.s_DebugCapLog)
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
			// an uneven part of a building's roof (a curved porch roof, a bulge) is left to the grid pieces: the planes
			// around it become polygons, its cells are holes of the surface (see Covered) filled with grid squares.
			// Other structures (stones) are drawn on the grid as a whole
			bool keepUneven = SZ_State.s_DebugRoofUneven && b.m_Obj && b.m_Obj.IsBuilding();
			map<int, bool> uneven = new map<int, bool>;
			foreach (int l1 : loose)
			{
				if (regOf.Contains(l1) || uneven.Contains(l1))
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
						if (!looseSet.Contains(pn) || inPart.Contains(pn) || !JoinedK(b, pc, pn))
							continue;
						inPart.Set(pn, true);
						todo.Insert(pn);
					}
				}
				if (FitSamples(b, part, h0, gu, gv, cu, cv) > CAP_FLAT)
				{
					if (SZ_State.s_DebugCapLog)
						Print(string.Format("[DSTest] capsplit uneven part of %1 samples at %2", part.Count(), CapSample(b, part[0])));
					if (!keepUneven)
						return false;
					foreach (int uk : part)
						uneven.Set(uk, true);
					continue;
				}
				// one or two samples at a building's roof edge or corner that do not lie on the planes beside them
				// (a fascia, the foot of a hip) but join them: a flat polygon of their own would stand out of the roof
				// as a shelf. The planes beside them reach to them and the grid pieces fill the rest (FillGaps). A
				// chimney top is not joined to the roof and keeps its own cap
				if (keepUneven && part.Count() <= 2 && JoinsPlane(b, part, regOf))
				{
					foreach (int jk : part)
						uneven.Set(jk, true);
					continue;
				}
				AddRegion(part, regOf, sets, lists, planes, h0, gu, gv, cu, cv);
				if (SZ_State.s_DebugCapLog)
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

	//! one of the samples of a part joins a neighbour that lies on a plane (no step between them)
	protected bool JoinsPlane(SZ_RoofBuilding b, array<int> part, map<int, int> regOf)
	{
		int nu = b.m_NU;
		int total = b.m_H.Count();
		foreach (int k : part)
		{
			int ki = k % nu;
			for (int d = 0; d < 4; d++)
			{
				int n = k + 1;
				if (d == 0 && ki + 1 >= nu)
					continue;
				if (d == 1)
				{
					if (ki == 0)
						continue;
					n = k - 1;
				}
				else if (d == 2)
					n = k + nu;
				else if (d == 3)
					n = k - nu;
				if (n < 0 || n >= total)
					continue;
				if (regOf.Contains(n) && JoinedK(b, k, n))
					return true;
			}
		}
		return false;
	}

	//! where plane r ends between a sample on it and a neighbour off it, found with rays (a step: a chimney, the wall
	//! of a dormer, the drop to a lower part)
	protected void PlaneEnd(SZ_RoofBuilding b, float uk, float vk, float un, float vn, array<float> planes, int r, out float eu, out float ev)
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
	protected float SampleNear(SZ_RoofBuilding b, float x, float z, float expect, float above, float below)
	{
		RaycastRVParams rp = new RaycastRVParams(Vector(x, expect + above, z), Vector(x, expect - below, z), null, 0);
		rp.type = b.m_Geo;
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
	protected int OnNeighbourPlane(SZ_RoofBuilding b, int k, map<int, int> regOf, array<float> planes)
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
	protected array<float> RegionHull(SZ_RoofBuilding b, array<int> grp, map<int, int> regOf, array<ref map<int, bool>> sets, array<ref array<int>> lists, array<float> planes, int r)
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
	protected bool Covered(SZ_RoofBuilding b, array<int> grp, int g, array<int> mine, array<ref array<float>> polys, array<int> holes)
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
	protected bool HullClear(SZ_RoofBuilding b, map<int, bool> own, array<float> hull, array<float> planes, int r)
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
					if (SZ_State.s_DebugCapLog)
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
	protected void SquareCorners(SZ_RoofBuilding b, array<float> hull, array<float> planes, int r)
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
			// the two edges beside the cut run along the rim: at least a little longer than a sliver (a round top has
			// short edges in all directions, which the right angle test below rejects)
			float minSide = 0.3;
			if (!SZ_State.s_DebugRoofCorner)
				minSide = cut;
			if (cut > maxCut || l1 < minSide || l2 < minSide || l1 < 0.01 || l2 < 0.01)
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
			// the rim of a roof often lies a few centimetres off the plane fitted to the roof
			float tol = 0.12;
			if (!SZ_State.s_DebugRoofCorner)
				tol = 0.05;
			if (hit == NO_HIT || Math.AbsFloat(hit - cornerH) > tol)
				continue;
			hull[ip * 2] = cx;
			hull[ip * 2 + 1] = cz;
			hull.RemoveOrdered(iq * 2 + 1);
			hull.RemoveOrdered(iq * 2);
			if (iq < ip)
				k--;
		}
	}

	protected vector CapPoint(SZ_RoofBuilding b, float u, float v, array<float> planes, int p)
	{
		vector w = b.m_Origin + b.m_U * u + b.m_V * v;
		w[1] = planes[p * 5] + planes[p * 5 + 1] * (u - planes[p * 5 + 3]) + planes[p * 5 + 2] * (v - planes[p * 5 + 4]);
		return w;
	}


	protected int StageFor(SZ_RoofBuilding b)
	{
		if (b.m_Baked != "")
			return BakedVariant(b);
		if (b.m_Tris.Count() == 0)
			return 0;
		return StageForDepth(DepthFor(b));
	}

	//! snow depth on the object (cm): the ground snow at its foot, minus what lay there when a vehicle came to rest
	protected float DepthFor(SZ_RoofBuilding b)
	{
		float depth = SZ_State.SnowAt(b.m_Ground, m_S0, m_S1, m_S2);
		if (b.m_Kind == 2 && b.m_RestDepth >= 0)
			depth = Math.Max(0, depth - b.m_RestDepth);
		return depth;
	}

	protected float SlabFor(SZ_RoofBuilding b)
	{
		float depth = DepthFor(b);
		// rocks: the snow lies on their flatter faces and ends where a face gets too steep, so the edge of a thick
		// slab stands there as a white plate; they get the thin slab of walls
		if (b.m_Kind == 0 && !(b.m_Rock && SZ_State.s_DebugRockThin))
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

	//! baked snow: the model for the snow depth on the structure (0 = none, see BAKED_DEPTHS)
	protected int BakedVariant(SZ_RoofBuilding b)
	{
		float depth = DepthFor(b);
		int variant = 0;
		while (variant < BAKED_DEPTHS.Count() && depth >= BAKED_DEPTHS[variant])
			variant++;
		return variant;
	}

	//! baked snow: how far it is raised above the roof at its distance (the part of OffsetFor that grows with the
	//! distance; the models hold the rest)
	protected float BakedLift(SZ_RoofBuilding b)
	{
		float lift = 0.0003 * b.m_Dist;
		if (b.m_Kind == 1)
			lift = 0.0002 * b.m_Dist;
		return lift + SZ_State.s_DebugRoofOffset;
	}

	//! a structure with baked snow: one object for all of it, replaced when the snow changes and raised a little as the
	//! camera moves away. False when something stands over it here: it is sampled like the other structures then
	protected bool UpdateBaked(SZ_RoofBuilding b, bool anySnow)
	{
		if (b.m_State == 0)
		{
			if (!anySnow)
				return true;
			// the baked snow lies on the model's own top: a placement tilted far from upright (a rock on its side) or
			// one under something else is sampled instead
			vector up = b.m_Obj.GetTransformAxis(1).Normalized();
			if (up[1] < BAKED_UPRIGHT || BakedCovered(b))
			{
				b.m_Baked = "";
				return false;
			}
			b.m_State = 2;
			b.m_Fine = true;
		}
		int want = BakedVariant(b);
		float lift = BakedLift(b);
		if (want != b.m_Stage)
		{
			Trash(b);
			b.m_Stage = want;
			if (want > 0)
			{
				Object o = MakeBaked(b, want, lift);
				if (o)
					b.m_Objects.Insert(o);
			}
		}
		else if (want > 0 && b.m_Objects.Count() > 0 && b.m_Objects[0] && Math.AbsFloat(lift - b.m_Lift) >= BAKED_LIFT_STEP)
		{
			PlaceBaked(b, b.m_Objects[0], lift);
		}
		return true;
	}

	protected Object MakeBaked(SZ_RoofBuilding b, int variant, float lift)
	{
		if (b.m_Baked == "")
			return null;
		string p3d = SZ_Const.BAKED + b.m_Baked.Substring(0, 1) + "\\" + b.m_Baked + "_v" + variant.ToString() + ".p3d";
		Object o = g_Game.CreateStaticObjectUsingP3D(p3d, b.m_Obj.GetPosition(), "0 0 0", 1.0, true);
		if (!o)
			return null;
		PlaceBaked(b, o, lift);
		m_Objects++;
		m_Cost += 0.05;
		return o;
	}

	//! the baked model lies in the structure's own space: it takes the structure's transform (the binarised model is
	//! centred on its bounding box, which is put back), raised by the lift
	protected void PlaceBaked(SZ_RoofBuilding b, Object o, float lift)
	{
		vector mat[4];
		b.m_Obj.GetTransform(mat);
		vector centre = o.GetBoundingCenter();
		mat[3] = mat[3] + mat[0] * centre[0] + mat[1] * centre[1] + mat[2] * centre[2];
		mat[3][1] = mat[3][1] + lift;
		o.SetTransform(mat);
		b.m_Lift = lift;
	}

	//! something solid other than vegetation stands over a structure here (a shed roof over a wreck, a shelter over a
	//! bench): its baked snow would lie under it. Five rays: the middle of its box and halfway to each corner
	protected bool BakedCovered(SZ_RoofBuilding b)
	{
		vector mat[4];
		b.m_Obj.GetTransform(mat);
		vector mm[2];
		b.m_Obj.ClippingInfo(mm);
		vector mid = (mm[0] + mm[1]) * 0.5;
		vector half = (mm[1] - mm[0]) * 0.25;
		float boxTop = mat[3][1] + mm[1][1] * mat[1][1];
		float bottom = mat[3][1] + mm[0][1] * mat[1][1] - 0.5;
		array<float> fu = {0.0, -1.0, 1.0, 1.0, -1.0};
		array<float> fv = {0.0, -1.0, -1.0, 1.0, 1.0};
		for (int k = 0; k < 5; k++)
		{
			vector p = mat[3] + mat[0] * (mid[0] + half[0] * fu[k]) + mat[2] * (mid[2] + half[2] * fv[k]);
			RaycastRVParams rp = new RaycastRVParams(Vector(p[0], boxTop + 20.0, p[2]), Vector(p[0], bottom, p[2]), null, 0);
			rp.type = ObjIntersectFire;
			rp.flags = CollisionFlags.ALLOBJECTS;
			rp.sorted = false;
			array<ref RaycastRVResult> results = new array<ref RaycastRVResult>;
			m_Rays++;
			m_Cost += 0.035;
			if (!DayZPhysics.RaycastRVProxy(rp, results))
				continue;
			float own = NO_HIT;
			float other = NO_HIT;
			foreach (RaycastRVResult res : results)
			{
				Object hit = res.obj;
				if (res.parent)
					hit = res.parent;
				if (!hit)
					continue;
				if (hit == b.m_Obj)
					own = Math.Max(own, res.pos[1]);
				else if (!SZ_Util.IsVegetation(hit) && !hit.IsInherited(Man) && !hit.IsInherited(DayZCreature))
					other = Math.Max(other, res.pos[1]);
			}
			float under = own;
			if (under == NO_HIT)
				under = boxTop;
			if (other != NO_HIT && other > under + 0.3)
				return true;
		}
		return false;
	}

	protected void DeleteObjects(SZ_RoofBuilding b)
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
	protected void Place(Object o, SZ_RoofTri t, float offset)
	{
		// every triangle is its own object: shared edges computed from two transforms miss each other by a fraction of
		// a millimetre and the surface below shows through as a dotted line. Each triangle grows around its centroid
		// (3 percent, less for the large pieces of flat tops), so neighbours overlap by a few millimetres instead.
		float grow = t.m_Grow;
		vector mat[4];
		vector centre = o.GetBoundingCenter();
		vector up = Vector(0, offset - t.m_Lower, 0);
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

	protected void ApplyStage(SZ_RoofBuilding b, int stage)
	{
		int tick0 = TickCount(0);
		ApplyStageNow(b, stage);
		if (s_TicksPerSec > 0)
		{
			float ms = TickCount(tick0) / s_TicksPerSec * 1000.0;
			if (ms > SZ_State.s_StatRoofPlaceMax && b.m_Obj)
			{
				SZ_State.s_StatRoofPlaceMax = ms;
				SZ_State.s_StatRoofPlaceWho = b.m_Obj.GetShapeName() + " pieces " + b.m_Objects.Count().ToString();
			}
		}
	}

	protected void ApplyStageNow(SZ_RoofBuilding b, int stage)
	{
		DeleteObjects(b);
		b.m_Stage = stage;
		if (stage <= 0)
			return;
		float offset = OffsetFor(b);
		b.m_Offset = offset;
		b.m_Slab = SlabFor(b);
		float slab = Math.Max(offset, b.m_Slab + SZ_State.s_DebugRoofOffset);
		foreach (SZ_RoofTri t : b.m_Tris)
		{
			Object o = MakePiece(t, stage, slab);
			if (o)
				b.m_Objects.Insert(o);
		}
	}

	//! height of the snow above the surface the rays found
	protected float OffsetFor(SZ_RoofBuilding b)
	{
		float offset = 0.05 + 0.0003 * b.m_Dist;
		// walls and wrecks: a gap of a few centimetres would show from the side. Vehicles and other movable entities
		// are sampled on their fire geometry, which follows the body only to a centimetre or two: their snow lies a
		// little higher, so the curved body does not show through it
		if (b.m_Kind == 1)
			offset = 0.015 + 0.0002 * b.m_Dist;
		else if (b.m_Kind == 2)
			offset = 0.04 + 0.0002 * b.m_Dist;
		return offset + SZ_State.s_DebugRoofOffset;
	}

	//! one snow piece of a triangle at a stage (null when the stage drops it)
	protected Object MakePiece(SZ_RoofTri t, int stage, float slab)
	{
		int st = stage - t.m_Drop;
		if (st < 1)
			return null;
		string p3d;
		if (t.m_Quad)
			p3d = SZ_Const.DATA + "snow\\szq" + t.m_Span.ToString() + t.m_Variant + "_s" + st.ToString() + ".p3d";
		else if (t.m_Free && t.m_Span > 1)
			p3d = SZ_Const.DATA + "snow\\szf" + t.m_Span.ToString() + "_s" + st.ToString() + ".p3d";
		else
			p3d = SZ_Const.DATA + "snow\\szr_" + ShapeName(t.m_Shape) + t.m_Variant + "_s" + st.ToString() + ".p3d";
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
		if (!SZ_State.s_StatRoofTicks)
		{
			SZ_State.s_StatRoofTicks = new array<int>;
			for (int k = 0; k < 6; k++)
				SZ_State.s_StatRoofTicks.Insert(0);
		}
		SZ_State.s_StatRoofTicks[part] = SZ_State.s_StatRoofTicks[part] + TickCount(tick0);
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
	protected void StatStep(int tick0, SZ_RoofBuilding b)
	{
		if (s_TicksPerSec <= 0)
			return;
		float ms = TickCount(tick0) / s_TicksPerSec * 1000.0;
		SZ_State.s_StatRoofBuildSum += ms;
		SZ_State.s_StatRoofBuilds++;
		if (ms > SZ_State.s_StatRoofBuildMax && b.m_Obj)
		{
			SZ_State.s_StatRoofBuildMax = ms;
			string what = "rays";
			if (b.m_State == 3)
				what = "edge";
			else if (b.m_Job)
				what = string.Format("polygons (group %1 phase %2 step %3)", b.m_Job.m_G, b.m_Job.m_Phase, b.m_Job.m_R);
			else if (b.m_State == 2)
				what = "finish";
			SZ_State.s_StatRoofBuildWho = b.m_Obj.GetShapeName() + " samples " + (b.m_NU * b.m_NV).ToString() + " " + what;
		}
	}

	//! starts placing a building's pieces for a stage; the current pieces stay until the new ones are all placed.
	//! False when the frame's budget ran out before they were
	protected bool StartPlace(SZ_RoofBuilding b, int stage)
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
	protected bool ContinuePlace(SZ_RoofBuilding b)
	{
		float slab = Math.Max(b.m_PendOffset, b.m_PendSlab + SZ_State.s_DebugRoofOffset);
		int n = b.m_Tris.Count();
		while (b.m_PendCursor < n)
		{
			if ((b.m_PendCursor & 7) == 0 && OverBudget(b.m_Dist < URGENT_DIST))
				return false;
			SZ_RoofTri t = b.m_Tris[b.m_PendCursor];
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
	protected void Trash(SZ_RoofBuilding b)
	{
		foreach (Object o : b.m_Objects)
		{
			if (o)
				m_Trash.Insert(o);
		}
		b.m_Objects.Clear();
	}

	//! the pieces of a stage that was being placed go to the trash
	protected void TrashPending(SZ_RoofBuilding b)
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

	protected void TrashAll(SZ_RoofBuilding b)
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
		UpdateFrame(timeslice, camera, s0, s1, s2);
	}

	//! the quick round over the structures with baked snow: each takes the model of the depth now (a few hundred
	//! per frame, a town of a few thousand in a few seconds). Those that went out of range are left to the main round
	protected void UpdateBakedRing(vector camera, bool anySnow)
	{
		if (!m_BakedRing || m_BakedRing.Count() == 0)
			return;
		if (!m_RingActive)
		{
			if (Math.AbsFloat(m_S0 - m_RingS0) < BAKED_RING_STEP && Math.AbsFloat(m_S1 - m_RingS1) < BAKED_RING_STEP && Math.AbsFloat(m_S2 - m_RingS2) < BAKED_RING_STEP)
				return;
			m_RingS0 = m_S0;
			m_RingS1 = m_S1;
			m_RingS2 = m_S2;
			m_RingActive = true;
			m_RingLeft = m_BakedRing.Count();
		}
		int n = Math.Min(BAKED_RING_PER_FRAME, m_RingLeft);
		for (int k = 0; k < n; k++)
		{
			// Allow one visit for progress, then yield without discarding pending visits.
			if (k > 0 && OverBudget())
				break;
			m_RingLeft--;
			if (m_BakedCursor >= m_BakedRing.Count())
				m_BakedCursor = 0;
			if (m_BakedRing.Count() == 0)
				return;
			SZ_RoofBuilding b = m_BakedRing[m_BakedCursor];
			if (!b || !b.m_Obj || b.m_Dropped || b.m_Baked == "" || b.m_State != 2)
			{
				if (b)
					b.m_InRing = false;
				m_BakedRing.Remove(m_BakedCursor);
				continue;
			}
			m_BakedCursor++;
			vector bp = b.m_Obj.GetPosition();
			float dx = bp[0] - camera[0];
			float dz = bp[2] - camera[2];
			float dist = Math.Sqrt(dx * dx + dz * dz);
			if (b.m_Small && dist > SMALL_RADIUS)
				continue;
			if (b.m_Kind == 1)
			{
				float wallRadius = WALL_RADIUS;
				if (b.m_Reach > 0)
					wallRadius = b.m_Reach;
				if (SZ_State.s_DebugWallRadius > 0)
					wallRadius = SZ_State.s_DebugWallRadius;
				if (dist > wallRadius)
					continue;
			}
			b.m_Dist = dist;
			UpdateBaked(b, anySnow);
		}
		if (m_RingLeft <= 0)
			m_RingActive = false;
	}

	protected void UpdateFrame(float timeslice, vector camera, float s0, float s1, float s2)
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
			if (frameMs > SZ_State.s_StatRoofFrameMax)
				SZ_State.s_StatRoofFrameMax = frameMs;
			SZ_State.s_StatRoofFrames++;
			if (frameMs > 8.0)
				SZ_State.s_StatRoofSlow++;
		}
	}

	protected void UpdateRoofs(float timeslice, vector camera, float s0, float s1, float s2)
	{
		if (SZ_State.s_DebugRoofOff)
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
		int looked = 0;
		bool busy = false;
		tk = TickCount(0);
		UpdateBakedRing(camera, anySnow);
		StatTicks(4, tk);
		while (m_Cost < 20.0 && visited < count && looked < VISITS_PER_FRAME)
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

			SZ_RoofTile tile = m_Tiles.Get(key);
			if (!tile)
			{
				if (!anySnow)
					continue;
				tile = new SZ_RoofTile();
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
			while (tile.m_UpdateCursor < tile.m_Buildings.Count())
			{
				if (looked >= VISITS_PER_FRAME || OverBudget(TileDist(ktx, ktz) < URGENT_DIST + TILE))
				{
					m_Cursor--;
					visited = count;
					busy = true;
					break;
				}
				SZ_RoofBuilding b = tile.m_Buildings[tile.m_UpdateCursor];
				tile.m_UpdateCursor++;
				if (!b.m_Obj)
					continue;
				looked++;
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
					if (SZ_State.s_DebugWallRadius > 0)
						wallRadius = SZ_State.s_DebugWallRadius;
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
						tile.m_UpdateCursor--;
						m_Cursor--;
						visited = count;
						busy = true;
						break;
					}
					continue;
				}
				if (b.m_Baked != "")
				{
					tk = TickCount(0);
					bool baked = UpdateBaked(b, anySnow);
					StatTicks(4, tk);
					if (baked)
					{
						if (!b.m_InRing && b.m_State == 2)
						{
							if (!m_BakedRing)
								m_BakedRing = new array<SZ_RoofBuilding>;
							m_BakedRing.Insert(b);
							b.m_InRing = true;
						}
						continue;
					}
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
					// continue this building and tile next frame
					tile.m_UpdateCursor--;
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
						tile.m_UpdateCursor--;
						m_Cursor--;
						visited = count;
						busy = true;
						break;
					}
				}
			}
			if (tile.m_UpdateCursor >= tile.m_Buildings.Count())
				tile.m_UpdateCursor = 0;
		}
		if (m_Cost >= 20.0 || m_Trash.Count() > 0 || m_RingActive)
			busy = true;
		SZ_State.s_StatRoofBusy = busy;
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
				SZ_RoofBuilding nb = new SZ_RoofBuilding();
				nb.m_Obj = e;
				nb.m_Kind = 2;
				nb.m_LastPos = e.GetPosition();
				nb.m_LastDir = e.GetDirection();
				nb.m_Ground = g_Game.SurfaceY(nb.m_LastPos[0], nb.m_LastPos[2]);
				nb.m_RestDepth = -1;
				if (s_Fresh && s_Fresh.Contains(e))
					nb.m_RestDepth = SZ_State.SnowAt(nb.m_Ground, m_S0, m_S1, m_S2);
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
				SZ_RoofBuilding gb = m_Movable.Get(gk);
				if (gb)
					DeleteObjects(gb);
				m_Movable.Remove(gk);
			}
		}

		for (int i = 0; i < m_Movable.Count(); i++)
		{
			SZ_RoofBuilding b = m_Movable.GetElement(i);
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
				b.m_RestDepth = SZ_State.SnowAt(b.m_Ground, m_S0, m_S1, m_S2);
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
			SZ_RoofTile t = m_Tiles.GetElement(i);
			if (!t)
				continue;
			foreach (SZ_RoofBuilding b : t.m_Buildings)
				TrashAll(b);
		}
		m_Tiles.Clear();
		if (m_BakedRing)
		{
			foreach (SZ_RoofBuilding rb : m_BakedRing)
			{
				if (rb)
					rb.m_InRing = false;
			}
			m_BakedRing.Clear();
		}
		m_BakedCursor = 0;
		m_RingActive = false;
		if (m_Movable)
		{
			for (int m = 0; m < m_Movable.Count(); m++)
			{
				SZ_RoofBuilding mb = m_Movable.GetElement(m);
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
			SZ_RoofTile t = m_Tiles.GetElement(i);
			if (!t)
				continue;
			foreach (SZ_RoofBuilding b : t.m_Buildings)
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
				SZ_RoofTile kt = m_Tiles.GetElement(k);
				if (!kt)
					continue;
				foreach (SZ_RoofBuilding kb : kt.m_Buildings)
				{
					kb.m_Dropped = true;
					DeleteObjects(kb);
				}
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
			SZ_RoofTile bt = m_Tiles.GetElement(bi);
			if (!bt)
				continue;
			foreach (SZ_RoofBuilding bb : bt.m_Buildings)
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
			SZ_RoofTile t = m_Tiles.GetElement(i);
			if (!t)
				continue;
			foreach (SZ_RoofBuilding b : t.m_Buildings)
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
		SZ_RoofBuilding best = null;
		float bestD = 30.0;
		for (int i = 0; i < m_Tiles.Count(); i++)
		{
			SZ_RoofTile t = m_Tiles.GetElement(i);
			if (!t)
				continue;
			foreach (SZ_RoofBuilding b : t.m_Buildings)
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
		SZ_State.s_DebugCapLog = true;
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
		SZ_State.s_DebugCapLog = false;
		best.m_Stage = -1;
		return best.m_Obj.GetType() + " " + best.m_CapInfo + " tris=" + best.m_Tris.Count().ToString();
	}

	//! test harness (baking): samples the snow of a map object at full detail on a copy of it standing alone (no other
	//! object over it, a flat ground at the given height under it) and writes its pieces to a file in the model's own
	//! space, in millimetres: per piece its kind (g grid, q square, f free), the stages it loses, how much lower it
	//! lies, its normal (x1000) and its corners on the roof. Rocks add their heights on a fine grid. Returns a summary
	string BakeObject(Object world, Object copy, float ground, string path, float refine)
	{
		s_Baking = true;
		SZ_RoofBuilding b = Classify(world);
		s_Baking = false;
		if (!b)
			return "none";
		b.m_Obj = copy;
		b.m_Ground = ground;
		b.m_Dist = 0;
		b.m_Baked = "";
		s_BakeGround = ground;
		s_BakeRefine = refine;
		BeginScan(b, true);
		int guard = 0;
		while ((b.m_State == 1 || b.m_State == 3 || b.m_State == 4) && guard < 500000)
		{
			guard++;
			if (b.m_State == 1)
				CastRow(b);
			else if (b.m_State == 3)
				RefineEdge(b);
			else if (CapStep(b))
				FinishTris(b);
		}
		// a structure without fire geometry: a copy made from its model is not hit on its collision geometry, so it
		// is sampled where it stands (on the terrain there, with what stands around it)
		Object frame = copy;
		if (b.m_Tris.Count() == 0 && b.m_Geo == ObjIntersectGeom)
		{
			frame = world;
			b.m_Obj = world;
			vector wp = world.GetPosition();
			b.m_Ground = g_Game.SurfaceY(wp[0], wp[2]);
			s_BakeGround = NO_HIT;
			BeginScan(b, true);
			guard = 0;
			while ((b.m_State == 1 || b.m_State == 3 || b.m_State == 4) && guard < 500000)
			{
				guard++;
				if (b.m_State == 1)
					CastRow(b);
				else if (b.m_State == 3)
					RefineEdge(b);
				else if (CapStep(b))
					FinishTris(b);
			}
			ground = b.m_Ground;
		}
		vector mat[4];
		frame.GetTransform(mat);
		FileHandle fh = OpenFile(path, FileMode.WRITE);
		if (fh == 0)
		{
			s_BakeGround = NO_HIT;
			s_BakeRefine = 1.0;
			return "nofile";
		}
		string shape = world.GetShapeName();
		shape.ToLower();
		FPrintln(fh, string.Format("model %1 kind %2 small %3 wall %4 rock %5 geo %6 state %7 ground %8 inplace %9", shape, b.m_Kind, b.m_Small, b.m_Wall, b.m_Rock, b.m_Geo, b.m_State, MM(ground - mat[3][1]), frame == world));
		FPrintln(fh, string.Format("axes %1 %2 %3 step %4 %5 grid %6 %7", mat[0], mat[1], mat[2], MM(b.m_StepU), MM(b.m_StepV), b.m_NU, b.m_NV));
		FPrintln(fh, "caps " + b.m_CapInfo);
		array<vector> cs = new array<vector>;
		foreach (SZ_RoofTri t : b.m_Tris)
		{
			PieceCorners(t, cs);
			string kindText = "g";
			if (t.m_Free)
				kindText = "f";
			else if (t.m_Quad)
				kindText = "q";
			vector ln = frame.VectorToLocal(t.m_Normal).Normalized();
			string line = string.Format("t %1 %2 %3 %4 %5 %6 %7", kindText, t.m_Drop, MM(t.m_Lower), Math.Round(ln[0] * 1000), Math.Round(ln[1] * 1000), Math.Round(ln[2] * 1000), cs.Count());
			foreach (vector c : cs)
			{
				vector lc = frame.CoordToLocal(c);
				line += " " + MM(lc[0]).ToString() + " " + MM(lc[1]).ToString() + " " + MM(lc[2]).ToString();
			}
			line += " s " + BakeSupport(b, cs).ToString();
			FPrintln(fh, line);
		}
		if (frame == copy)
		{
			// every model: its height on a fine grid over its box (x = no hit), from 5 cm (small models) to 30 cm (the
			// largest), at most about 350 samples along a side. The generator checks the pieces against it and draws
			// curved and rough tops (rocks, tanks, wrecks, barriers) from it. "e" lines: where a surface ends between
			// two samples, found with a few more rays
			vector mm[2];
			copy.ClippingInfo(mm);
			float side = Math.Max(mm[1][0] - mm[0][0], mm[1][2] - mm[0][2]);
			float gs = Math.Clamp(side / 150.0, 0.05, 0.3);
			gs = Math.Round(gs * 200.0) / 200.0;
			if (side / gs > 350.0)
				gs = Math.Ceil(side / 350.0 * 200.0) / 200.0;
			int gnu = Math.Ceil((mm[1][0] - mm[0][0]) / gs) + 1;
			int gnv = Math.Ceil((mm[1][2] - mm[0][2]) / gs) + 1;
			FPrintln(fh, string.Format("grid %1 %2 %3 %4 %5", gnu, gnv, MM(gs), MM(mm[0][0]), MM(mm[0][2])));
			b.m_Top = mat[3][1] + mm[1][1] + 1.5;
			b.m_Bottom = ground - 0.5;
			float ox = mat[3][0] + mm[0][0];
			float oz = mat[3][2] + mm[0][2];
			array<float> hs = new array<float>;
			int gi;
			int gj;
			for (gj = 0; gj < gnv; gj++)
			{
				string row = "r";
				for (gi = 0; gi < gnu; gi++)
				{
					float gh = SampleAt(b, ox + gi * gs, oz + gj * gs);
					hs.Insert(gh);
					if (gh == NO_HIT)
						row += " x";
					else
						row += " " + MM(gh - mat[3][1]).ToString();
				}
				FPrintln(fh, row);
			}
			for (gj = 0; gj < gnv; gj++)
			{
				for (gi = 0; gi < gnu; gi++)
				{
					float ha = hs[gj * gnu + gi];
					if (gi + 1 < gnu)
						BakeEdgeLine(fh, b, ox, oz, gs, gi, gj, 0, ha, hs[gj * gnu + gi + 1]);
					if (gj + 1 < gnv)
						BakeEdgeLine(fh, b, ox, oz, gs, gi, gj, 1, ha, hs[(gj + 1) * gnu + gi]);
				}
			}
		}
		CloseFile(fh);
		s_BakeGround = NO_HIT;
		s_BakeRefine = 1.0;
		return string.Format("kind=%1 small=%2 wall=%3 rock=%4 tris=%5 step=%6 caps: %7", b.m_Kind, b.m_Small, b.m_Wall, b.m_Rock, b.m_Tris.Count(), b.m_StepU, b.m_CapInfo);
	}

	protected static int MM(float metres)
	{
		return Math.Round(metres * 1000.0);
	}

	//! baking: where the surface at one of two neighbouring grid samples ends when the other has nothing or a surface
	//! much higher or lower: "e <i> <j> <dir> <t>" for the samples (i, j) and the next along u (dir 0) or v (dir 1), t
	//! (0-1000) measured from (i, j). The end found is that of the surface hit, or of the higher one
	protected void BakeEdgeLine(FileHandle fh, SZ_RoofBuilding b, float ox, float oz, float gs, int i, int j, int dir, float ha, float hc)
	{
		if (ha == NO_HIT && hc == NO_HIT)
			return;
		float thr = Math.Max(0.3, 2.75 * gs);
		if (ha != NO_HIT && hc != NO_HIT && Math.AbsFloat(ha - hc) <= thr)
			return;
		bool fromA = hc == NO_HIT || (ha != NO_HIT && ha > hc);
		float ax = ox + i * gs;
		float az = oz + j * gs;
		float cx = ax;
		float cz = az;
		if (dir == 0)
			cx = cx + gs;
		else
			cz = cz + gs;
		float sx = ax;
		float sz = az;
		float ex = cx;
		float ez = cz;
		float hsurf = ha;
		float hother = hc;
		if (!fromA)
		{
			sx = cx;
			sz = cz;
			ex = ax;
			ez = az;
			hsurf = hc;
			hother = ha;
		}
		float lo = 0.0;
		float hi = 1.0;
		for (int it = 0; it < 5; it++)
		{
			float mid = (lo + hi) * 0.5;
			float h = SampleAt(b, sx + (ex - sx) * mid, sz + (ez - sz) * mid);
			bool same = false;
			if (h != NO_HIT)
			{
				if (hother == NO_HIT)
					same = Math.AbsFloat(h - hsurf) <= mid * gs * 1.8 + 0.05;
				else
					same = Math.AbsFloat(h - hsurf) < Math.AbsFloat(h - hother);
			}
			if (same)
				lo = mid;
			else
				hi = mid;
		}
		float t = (lo + hi) * 0.5;
		if (!fromA)
			t = 1.0 - t;
		FPrintln(fh, string.Format("e %1 %2 %3 %4", i, j, dir, Math.Round(t * 1000.0)));
	}

	//! baking: at how many of five points of a piece (its middle and four points 70% out to its corners) the structure
	//! itself lies just under it, in any of its geometries (fire, view, collision). A piece over air (a plane carried on
	//! past a cab roof, over a flight of open stairs) is found here and left out of the baked snow
	protected int BakeSupport(SZ_RoofBuilding b, array<vector> cs)
	{
		int n = cs.Count();
		if (n < 3)
			return 0;
		vector g = "0 0 0";
		foreach (vector c : cs)
			g = g + c;
		g = g * (1.0 / n);
		int count = 0;
		for (int q = -1; q < n && q < 4; q++)
		{
			vector p = g;
			if (q >= 0)
				p = g + (cs[q] - g) * 0.7;
			if (BakeSupported(b, p))
				count++;
		}
		return count;
	}

	protected bool BakeSupported(SZ_RoofBuilding b, vector p)
	{
		array<int> geos = {ObjIntersectFire, ObjIntersectView, ObjIntersectGeom};
		foreach (int geo : geos)
		{
			RaycastRVParams rp = new RaycastRVParams(p + Vector(0, 0.3, 0), p - Vector(0, 0.6, 0), null, 0);
			rp.type = geo;
			rp.flags = CollisionFlags.ALLOBJECTS;
			rp.sorted = false;
			array<ref RaycastRVResult> results = new array<ref RaycastRVResult>;
			if (!DayZPhysics.RaycastRVProxy(rp, results))
				continue;
			foreach (RaycastRVResult res : results)
			{
				Object hit = res.obj;
				if (res.parent)
					hit = res.parent;
				if (hit == b.m_Obj && res.pos[1] >= p[1] - BAKE_SUPPORT && res.pos[1] <= p[1] + 0.3)
					return true;
			}
		}
		return false;
	}

	//! test harness: the snow triangles of the structure nearest to a point
	string DebugTris(float x, float z)
	{
		SZ_RoofBuilding best = null;
		float bestD = 30.0;
		for (int i = 0; i < m_Tiles.Count(); i++)
		{
			SZ_RoofTile t = m_Tiles.GetElement(i);
			if (!t)
				continue;
			foreach (SZ_RoofBuilding b : t.m_Buildings)
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
		array<vector> dbgCs = new array<vector>;
		for (int k = 0; k < best.m_Tris.Count(); k++)
		{
			SZ_RoofTri tr = best.m_Tris[k];
			string objPos = "-";
			if (k < best.m_Objects.Count() && best.m_Objects[k])
				objPos = best.m_Objects[k].GetPosition().ToString();
			PieceCorners(tr, dbgCs);
			string pts = "";
			foreach (vector dc : dbgCs)
				pts += string.Format(" (%1 %2 %3)", Math.Round(dc[0] * 100) / 100, Math.Round((dc[1] - best.m_Ground) * 100) / 100, Math.Round(dc[2] * 100) / 100);
			string kindText = "grid";
			if (tr.m_Free)
				kindText = "free";
			else if (tr.m_Quad)
				kindText = "quad";
			if (tr.m_Lower > 0)
				kindText += "+fill";
			Print(string.Format("[DSTest] rooftri %1 %2 ny=%3 pts%4", k, kindText, tr.m_Normal[1], pts));
		}
		return string.Format("%1 tris=%2 objects=%3 stage=%4 offset=%5 caps: %6", best.m_Obj.GetType(), best.m_Tris.Count(), best.m_Objects.Count(), best.m_Stage, best.m_Offset, best.m_CapInfo);
	}

	//! test harness: the structures within a radius of a point whose snow is complete (sampled at the detail of
	//! their distance, their stage placed), the others there (waiting), and the tiles around the point not scanned
	//! yet
	void DebugBaked(float x, float z, float radius)
	{
		for (int i = 0; i < m_Tiles.Count(); i++)
		{
			SZ_RoofTile t = m_Tiles.GetElement(i);
			if (!t)
				continue;
			foreach (SZ_RoofBuilding b : t.m_Buildings)
			{
				if (!b.m_Obj || b.m_Objects.Count() == 0)
					continue;
				vector p = b.m_Obj.GetPosition();
				if ((p[0] - x) * (p[0] - x) + (p[2] - z) * (p[2] - z) > radius * radius)
					continue;
				Object o = b.m_Objects[0];
				vector box[2];
				string extent = "-";
				if (o)
				{
					o.ClippingInfo(box);
					extent = (box[1] - box[0]).ToString() + " at " + o.GetPosition().ToString();
				}
				Print(string.Format("[DSTest] bakednear %1 baked=%2 pieces=%3 scale=%4 pos=%5 snow=%6", b.m_Obj.GetShapeName(), b.m_Baked, b.m_Objects.Count(), b.m_Obj.GetScale(), p, extent));
			}
		}
	}

	void DebugReady(vector c, float radius, array<SZ_RoofBuilding> ready, array<SZ_RoofBuilding> waiting, out int tiles)
	{
		tiles = 0;
		// tiles around the point that are not scanned yet hold structures nobody knows of so far
		int tx0 = Math.Floor((c[0] - radius) / TILE);
		int tx1 = Math.Floor((c[0] + radius) / TILE);
		int tz0 = Math.Floor((c[2] - radius) / TILE);
		int tz1 = Math.Floor((c[2] + radius) / TILE);
		for (int tx = tx0; tx <= tx1; tx++)
		{
			for (int tz = tz0; tz <= tz1; tz++)
			{
				SZ_RoofTile st = m_Tiles.Get(tx * 65536 + tz);
				if (!st || !st.m_Scanned)
					tiles++;
			}
		}
		for (int i = 0; i < m_Tiles.Count(); i++)
		{
			SZ_RoofTile t = m_Tiles.GetElement(i);
			if (!t)
				continue;
			foreach (SZ_RoofBuilding b : t.m_Buildings)
			{
				if (!b.m_Obj)
					continue;
				vector p = b.m_Obj.GetPosition();
				float dx = p[0] - c[0];
				float dz = p[2] - c[2];
				if (dx * dx + dz * dz > radius * radius)
					continue;
				bool done = b.m_State == 2 && !b.m_Pending && b.m_Stage == StageFor(b);
				if (done && b.m_Kind == 0 && !b.m_Small && b.m_Dist < FINE_RADIUS && !b.m_Fine)
					done = false;
				if (done)
					ready.Insert(b);
				else
					waiting.Insert(b);
			}
		}
	}

	//! test harness: the snow depth a structure carries (cm)
	float DebugDepth(SZ_RoofBuilding b)
	{
		return DepthFor(b);
	}

	//! test harness: every object the roof snow knows within a radius of a point (whether it carries snow or not)
	void DebugKnown(vector c, float radius, map<Object, bool> known)
	{
		for (int i = 0; i < m_Tiles.Count(); i++)
		{
			SZ_RoofTile t = m_Tiles.GetElement(i);
			if (!t)
				continue;
			foreach (SZ_RoofBuilding b : t.m_Buildings)
			{
				if (!b.m_Obj)
					continue;
				vector p = b.m_Obj.GetPosition();
				float dx = p[0] - c[0];
				float dz = p[2] - c[2];
				if (dx * dx + dz * dz <= radius * radius)
					known.Set(b.m_Obj, true);
			}
		}
	}

	//! test harness: the structures the roof snow keeps within a radius of a point, and every other object there with
	//! the reason it is not one of them
	string DebugNear(float x, float z, float radius)
	{
		map<Object, bool> known = new map<Object, bool>;
		string s = "";
		for (int i = 0; i < m_Tiles.Count(); i++)
		{
			SZ_RoofTile t = m_Tiles.GetElement(i);
			if (!t)
				continue;
			foreach (SZ_RoofBuilding b : t.m_Buildings)
			{
				if (!b.m_Obj)
					continue;
				vector p = b.m_Obj.GetPosition();
				if ((p[0] - x) * (p[0] - x) + (p[2] - z) * (p[2] - z) > radius * radius)
					continue;
				known.Set(b.m_Obj, true);
				vector dbgUp = b.m_Obj.GetTransformAxis(1).Normalized();
				s += string.Format(" [%1 kind=%2 small=%3 wall=%4 geo=%5 state=%6 tris=%7 objs=%8 baked=%9", b.m_Obj.GetShapeName(), b.m_Kind, b.m_Small, b.m_Wall, b.m_Geo, b.m_State, b.m_Tris.Count(), b.m_Objects.Count(), b.m_Baked);
				s += string.Format(" up=%1 stage=%2]", dbgUp[1], b.m_Stage);
			}
		}
		array<Object> objs = new array<Object>;
		g_Game.GetObjectsAtPosition(Vector(x, g_Game.SurfaceY(x, z), z), radius, objs, null);
		foreach (Object o : objs)
		{
			if (!o || known.Contains(o) || SZ_Util.IsVegetation(o))
				continue;
			string shape = o.GetShapeName();
			if (shape == "")
				continue;
			shape.ToLower();
			vector mm[2];
			o.ClippingInfo(mm);
			vector size = mm[1] - mm[0];
			vector op = o.GetPosition();
			int tx = Math.Floor(op[0] / TILE);
			int tz = Math.Floor(op[2] / TILE);
			SZ_RoofTile ot = m_Tiles.Get(tx * 65536 + tz);
			string tileState = "none";
			if (ot && ot.m_Scanned)
				tileState = "scanned";
			else if (ot)
				tileState = "unscanned";
			s += string.Format(" {%1 size=%2 building=%3 plain=%4 movable=%5 path=%6 tile=%7}", shape, size, o.IsBuilding(), IsPlainStructure(shape), IsMovable(o), SZ_TreeSwap.IsPath(o), tileState);
		}
		return s;
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
		SZ_RoofBuilding b = new SZ_RoofBuilding();
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
						else if (!SZ_Util.IsVegetation(hit) && !hit.IsInherited(Man) && !hit.IsInherited(DayZCreature))
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

