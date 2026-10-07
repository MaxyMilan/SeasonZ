// Local test harness only (never shipped): file-controlled camera tour on the client and weather/snow control on the server.

class DST_File
{
	static string ReadLine(string path)
	{
		if (!FileExist(path))
			return "";
		FileHandle fh = OpenFile(path, FileMode.READ);
		if (fh == 0)
			return "";
		string line;
		FGets(fh, line);
		CloseFile(fh);
		line.Trim();
		return line;
	}
}

//! lists every water surface object of the map (ponds, lakes, streams) into a file, one square kilometre per frame
class DST_PondMap
{
	protected int m_Tile;
	protected int m_Tiles = 16;
	protected float m_Step = 1000.0;
	protected string m_Path;
	protected ref array<string> m_Lines;
	protected int m_Count;

	void Start(string path)
	{
		m_Tile = 0;
		m_Count = 0;
		m_Path = path;
		m_Lines = new array<string>;
	}

	protected void Save()
	{
		FileHandle fh = OpenFile(m_Path, FileMode.WRITE);
		if (fh == 0)
			return;
		foreach (string line : m_Lines)
			FPrintln(fh, line);
		CloseFile(fh);
	}

	//! false when done
	bool Step()
	{
		if (m_Tile >= m_Tiles * m_Tiles)
		{
			Save();
			Print("[DSTest] pondmap done: " + m_Count.ToString() + " water objects");
			return false;
		}
		int tx = m_Tile % m_Tiles;
		int tz = m_Tile / m_Tiles;
		m_Tile++;
		float cx = (tx + 0.5) * m_Step;
		float cz = (tz + 0.5) * m_Step;
		vector c = Vector(cx, GetGame().SurfaceY(cx, cz), cz);
		array<Object> objs = new array<Object>;
		GetGame().GetObjectsAtPosition(c, m_Step * 0.75, objs, null);
		foreach (Object o : objs)
		{
			if (!o)
				continue;
			string shape = o.GetShapeName();
			shape.ToLower();
			if (shape.IndexOf("\\water") < 0)
				continue;
			vector p = o.GetPosition();
			if (p[0] < tx * m_Step || p[0] >= (tx + 1) * m_Step || p[2] < tz * m_Step || p[2] >= (tz + 1) * m_Step)
				continue;
			vector bb[2];
			o.ClippingInfo(bb);
			vector ori = o.GetOrientation();
			float wy = GetGame().GetWaterSurfaceHeightNoFakeWave(p);
			bool isPond = GetGame().SurfaceIsPond(p[0], p[2]);
			float ground = GetGame().SurfaceY(p[0], p[2]);
			m_Lines.Insert(string.Format("%1|%2|%3|%4|%5|%6|%7|%8", shape, p, ori, bb[0], bb[1], wy, isPond, ground));
			m_Count++;
		}
		return true;
	}
}
//! statistics of one map species / seasonal model pair
class DST_PairStat
{
	int m_Count;
	int m_Float;
	int m_Sunk;
	int m_Capped;
	float m_MaxSink;
	float m_SumSink;
	float m_OrigContact;
	float m_ReplContact;
	float m_OrigDepth;
	float m_ReplDepth;
	float m_K;
	string m_Example;
}

//! map wide list of every structure (buildings, walls, wrecks, rocks): model, type, bounding box centre in the
//! world, direction and size, for the visual sweep (buildscan.csv in the client profile; local test tool)
class DST_BuildScan
{
	static const float TILE = 100.0;
	protected float m_X0;
	protected float m_Z0;
	protected int m_NX;
	protected int m_NZ;
	protected int m_Index;
	protected int m_Count;
	protected float m_LogTimer;
	protected FileHandle m_File;
	bool m_Active;

	void Start(float x0, float z0, float x1, float z1)
	{
		m_X0 = x0;
		m_Z0 = z0;
		m_NX = Math.Ceil((x1 - x0) / TILE);
		m_NZ = Math.Ceil((z1 - z0) / TILE);
		m_Index = 0;
		m_Count = 0;
		m_File = OpenFile("$profile:buildscan.csv", FileMode.WRITE);
		FPrintln(m_File, "shape,type,cx,cy,cz,dirx,dirz,sx,sy,sz,ground,rock");
		m_Active = true;
		Print(string.Format("[DSTest] build scan started: %1 x %2 tiles", m_NX, m_NZ));
	}

	protected string N(float v)
	{
		return (Math.Round(v * 100.0) / 100.0).ToString();
	}

	void Step(float timeslice)
	{
		if (!m_Active)
			return;
		int budget = 0;
		while (budget < 3000 && m_Index < m_NX * m_NZ)
		{
			int tx = m_Index % m_NX;
			int tz = m_Index / m_NX;
			m_Index++;
			float cx = m_X0 + (tx + 0.5) * TILE;
			float cz = m_Z0 + (tz + 0.5) * TILE;
			vector c = Vector(cx, GetGame().SurfaceY(cx, cz), cz);
			array<Object> objs = new array<Object>;
			GetGame().GetObjectsAtPosition(c, TILE * 0.7072, objs, null);
			budget += 40 + objs.Count();
			foreach (Object o : objs)
			{
				if (!o || o.IsTree() || o.IsBush())
					continue;
				if (o.IsInherited(Man) || o.IsInherited(ItemBase) || o.IsInherited(Transport) || o.IsInherited(DayZCreature))
					continue;
				vector p = o.GetPosition();
				if (Math.Floor((p[0] - m_X0) / TILE) != tx || Math.Floor((p[2] - m_Z0) / TILE) != tz)
					continue;
				string sn = o.GetShapeName();
				sn.ToLower();
				bool rock = o.IsRock() || sn.IndexOf("\\rocks") >= 0;
				if (!rock && sn.IndexOf("structures") < 0)
					continue;
				if (sn.IndexOf("\\roads\\") >= 0 || sn.IndexOf("\\decals\\") >= 0)
					continue;
				vector mm[2];
				o.ClippingInfo(mm);
				vector centre = o.ModelToWorld((mm[0] + mm[1]) * 0.5);
				vector size = (mm[1] - mm[0]) * o.GetScale();
				vector d = o.GetDirection();
				string line = sn + "," + o.GetType() + "," + N(centre[0]) + "," + N(centre[1]) + "," + N(centre[2]) + "," + N(d[0]) + "," + N(d[2]);
				line += "," + N(size[0]) + "," + N(size[1]) + "," + N(size[2]) + "," + N(GetGame().SurfaceY(centre[0], centre[2])) + "," + rock.ToString();
				FPrintln(m_File, line);
				m_Count++;
				budget += 8;
			}
		}
		m_LogTimer += timeslice;
		if (m_LogTimer >= 10.0)
		{
			m_LogTimer = 0;
			Print(string.Format("[DSTest] build scan %1/%2 tiles, structures=%3", m_Index, m_NX * m_NZ, m_Count));
		}
		if (m_Index >= m_NX * m_NZ)
		{
			CloseFile(m_File);
			m_Active = false;
			Print(string.Format("[DSTest] build scan done: structures=%1", m_Count));
		}
	}
}

//! map wide check of how every seasonal tree model stands on the ground (local test tool). For every map tree and
//! each of its seasonal models it places the model exactly like the client does (feet together) and measures how far
//! the model would float above the terrain around its trunk ("sink": the extra drop the client now applies).
class DST_TreeScan
{
	static const float TILE = 80.0;
	protected SZ_TreeSwap m_Swap;
	protected float m_X0;
	protected float m_Z0;
	protected int m_NX;
	protected int m_NZ;
	protected int m_Index;
	protected float m_Delay;
	protected ref map<string, vector> m_Box;
	protected ref map<string, ref DST_PairStat> m_Pairs;
	protected int m_Trees;
	protected int m_Variants;
	protected int m_Float;
	protected int m_Sunk;
	protected int m_Capped;
	protected int m_OrigFloat;
	protected FileHandle m_File;
	protected float m_LogTimer;
	bool m_Active;

	void Start(SZ_TreeSwap swap, float x0, float z0, float x1, float z1)
	{
		m_Swap = swap;
		m_X0 = x0;
		m_Z0 = z0;
		m_NX = Math.Ceil((x1 - x0) / TILE);
		m_NZ = Math.Ceil((z1 - z0) / TILE);
		m_Index = 0;
		m_Delay = 3.0;
		m_Box = new map<string, vector>;
		m_Pairs = new map<string, ref DST_PairStat>;
		m_Trees = 0;
		m_Variants = 0;
		m_Float = 0;
		m_Sunk = 0;
		m_Capped = 0;
		m_OrigFloat = 0;
		m_File = OpenFile("$profile:treescan.csv", FileMode.WRITE);
		if (m_File)
			FPrintln(m_File, "x,z,shape,show,model,scale,k,drop,origDepth,replDepth,origGap,sink");
		m_Active = true;
		// originals must be back at their own scale before they are measured
		SZ_State.s_DebugNoTrees = true;
		Print(string.Format("[DSTest] tree scan started: %1 x %2 tiles from %3 %4", m_NX, m_NZ, x0, z0));
	}

	protected vector Box(string model)
	{
		vector box;
		if (m_Box.Find(model, box))
			return box;
		box = "0 0 0";
		Object o = GetGame().CreateStaticObjectUsingP3D(model, Vector(20, 3000, 20), "0 0 0", 1.0, true);
		if (o)
		{
			vector mm[2];
			o.ClippingInfo(mm);
			box = Vector(mm[0][1], mm[1][1], 1);
			GetGame().ObjectDelete(o);
		}
		m_Box.Set(model, box);
		return box;
	}

	protected void CheckTree(Object o, string key)
	{
		string origModel = o.GetShapeName();
		vector oCentre = m_Swap.ModelCentre(origModel);
		float oC = oCentre[1];
		vector tm[4];
		o.GetTransform(tm);
		float scale = tm[0].Length();
		// the original itself: how far it reaches below its foot, and how far its lowest point stays above the
		// terrain around its trunk (trees on rocks and at cliff edges)
		float oDrop;
		float oDepth;
		SZ_TreeSwap.GroundSink(tm, oCentre, m_Swap.ModelBottom(origModel), 0, oDrop, oDepth);
		float oGap = Math.Max(0, oDrop + 0.03 - oDepth);
		if (oGap > 0.05 || oDrop == 0)
			m_OrigFloat++;
		bool counted = false;
		for (int show = 1; show <= 3; show++)
		{
			string model = m_Swap.VariantModel(key, show);
			if (model == "")
				continue;
			if (!counted)
			{
				m_Trees++;
				counted = true;
			}
			vector rCentre = m_Swap.ModelCentre(model);
			float rC = rCentre[1];
			if (rC <= 0)
				continue;
			m_Variants++;
			float k;
			float shift;
			SZ_TreeSwap.FitModel(m_Swap.VariantApprox(key, show), oC, rC, k, shift);
			// the transform the client gives the seasonal model
			vector mat[4];
			mat[0] = tm[0] * k;
			mat[1] = tm[1] * k;
			mat[2] = tm[2] * k;
			mat[3] = tm[3];
			if (shift != 0)
			{
				float sx = k * rCentre[0] - oCentre[0];
				float sz = k * rCentre[2] - oCentre[2];
				mat[3] = mat[3] + tm[0] * sx + tm[1] * shift + tm[2] * sz;
			}
			float drop;
			float depth;
			float sink = SZ_TreeSwap.GroundSink(mat, rCentre, m_Swap.ModelBottom(model), oDepth, drop, depth);
			// after the sink: where the replacement still ends above the terrain while the original reaches it
			float after = Math.Min(drop + 0.03, oDepth) - (depth + sink);
			string pk = key + ">" + model;
			DST_PairStat st = m_Pairs.Get(pk);
			if (!st)
			{
				st = new DST_PairStat();
				st.m_OrigContact = oC;
				st.m_ReplContact = rC;
				st.m_OrigDepth = oDepth;
				st.m_ReplDepth = depth;
				st.m_K = k;
				st.m_Example = string.Format("%1 %2", tm[3][0], tm[3][2]);
				m_Pairs.Set(pk, st);
			}
			st.m_Count++;
			st.m_SumSink += sink;
			if (sink > st.m_MaxSink)
			{
				st.m_MaxSink = sink;
				st.m_Example = string.Format("%1 %2", tm[3][0], tm[3][2]);
			}
			// without the sink the model would float more than 5 cm somewhere around its trunk
			if (sink > 0.08)
			{
				st.m_Float++;
				m_Float++;
				if (m_File)
					FPrintln(m_File, string.Format("%1,%2,%3,%4,%5,%6,%7,%8,%9", tm[3][0], tm[3][2], key, show, model, scale, k, drop, oDepth) + string.Format(",%1,%2,%3", depth, oGap, sink));
			}
			if (after > 0.02)
			{
				st.m_Capped++;
				m_Capped++;
			}
		}
	}

	void Step(float timeslice)
	{
		if (!m_Active)
			return;
		if (m_Delay > 0)
		{
			m_Delay -= timeslice;
			return;
		}
		int budget = 0;
		while (budget < 2500 && m_Index < m_NX * m_NZ)
		{
			int tx = m_Index % m_NX;
			int tz = m_Index / m_NX;
			m_Index++;
			float cx = m_X0 + (tx + 0.5) * TILE;
			float cz = m_Z0 + (tz + 0.5) * TILE;
			vector c = Vector(cx, GetGame().SurfaceY(cx, cz), cz);
			array<Object> objs = new array<Object>;
			GetGame().GetObjectsAtPosition(c, TILE * 0.7072, objs, null);
			budget += 40 + objs.Count();
			foreach (Object o : objs)
			{
				if (!o || o.IsInherited(EntityAI) || o.IsInherited(Man))
					continue;
				vector p = o.GetPosition();
				if (Math.Floor((p[0] - m_X0) / TILE) != tx || Math.Floor((p[2] - m_Z0) / TILE) != tz)
					continue;
				if (!o.IsTree() && !o.IsBush())
				{
					string sn = o.GetShapeName();
					sn.ToLower();
					if (sn.IndexOf("plants") < 0)
						continue;
				}
				CheckTree(o, SZ_TreeSwap.ShapeKey(o));
				budget += 12;
			}
		}
		m_LogTimer += timeslice;
		if (m_LogTimer >= 10.0)
		{
			m_LogTimer = 0;
			Print(string.Format("[DSTest] tree scan %1/%2 tiles, trees=%3 variants=%4 needsSink=%5 stillFloating=%6 originalsOffGround=%7", m_Index, m_NX * m_NZ, m_Trees, m_Variants, m_Float, m_Capped, m_OrigFloat));
		}
		if (m_Index >= m_NX * m_NZ)
			Finish();
	}

	protected void Finish()
	{
		m_Active = false;
		Print(string.Format("[DSTest] tree scan done: trees=%1 variants=%2 needsSink>8cm=%3 stillFloatingWhereOriginalTouches=%4 originalsOffGround=%5", m_Trees, m_Variants, m_Float, m_Capped, m_OrigFloat));
		if (m_File)
		{
			FPrintln(m_File, "#pairs: key>model,count,needsSink,stillFloating,maxSink,meanSink,origDepth,replDepth,k,example");
			for (int i = 0; i < m_Pairs.Count(); i++)
			{
				DST_PairStat st = m_Pairs.GetElement(i);
				float mean = 0;
				if (st.m_Count > 0)
					mean = st.m_SumSink / st.m_Count;
				FPrintln(m_File, string.Format("#%1,%2,%3,%4,%5,%6,%7,%8,%9", m_Pairs.GetKey(i), st.m_Count, st.m_Float, st.m_Capped, st.m_MaxSink, mean, st.m_OrigDepth, st.m_ReplDepth, st.m_K) + "," + st.m_Example);
			}
			CloseFile(m_File);
		}
		SZ_State.s_DebugNoTrees = false;
	}
}

//! snow audit of one structure, a slice per frame: its roof pieces against the fire geometry under them, the
//! sky-facing surfaces it has without snow, and the ground snow inside and around it
class DST_AuditB
{
	static const float NOHIT = -100000.0;
	SZ_RoofBuilding b;
	SZ_SnowCarpet m_Carpet;
	bool m_Dump;
	int m_Stage;
	float m_Depth;
	float m_Thick;
	int m_W;
	int m_Hn;
	float m_HU;
	float m_HV;
	int m_Phase;
	int m_Cursor;
	ref array<float> m_Surf;
	ref array<bool> m_Exp;
	ref array<float> m_Best;
	ref array<float> m_Own;
	ref array<vector> m_Cs;
	// roof pieces: test points, floating more than 6 / 15 cm, over air, geometry through the snow, under an
	// upper part of the building
	int m_PTris;
	int m_PVis;
	int m_PPts;
	int m_PF;
	int m_PF15;
	int m_PFPieces;
	float m_PFMax;
	vector m_PFPos;
	int m_PAir;
	int m_PPier;
	float m_PPierMax;
	vector m_PPierPos;
	int m_PUnder;
	// sky-facing surfaces: expected, covered, gaps (at a sample, between samples, smaller than the grid), covered
	// by a piece floating above or sunk below
	int m_CExp;
	int m_COk;
	int m_CGapS;
	int m_CGapE;
	int m_CGapSub;
	vector m_CGapPos;
	float m_CGapTop;
	int m_CFl;
	float m_CFlMax;
	vector m_CFlPos;
	int m_CBur;
	float m_CBurMax;
	vector m_CBurPos;
	int m_CGapOver;
	int m_CNoNormal;
	// ground snow: points, not ready, snow inside or through a floor, bare ground outside
	int m_GPts;
	int m_GNR;
	int m_GIn;
	float m_GInMax;
	vector m_GInPos;
	int m_GInWall;
	int m_GGap;
	int m_GGapRoof;
	vector m_GGapPos;

	void DST_AuditB(SZ_RoofBuilding bb, SZ_SnowCarpet carpet, float depth, bool dump)
	{
		b = bb;
		m_Carpet = carpet;
		m_Dump = dump;
		m_Stage = b.m_Stage;
		m_Depth = depth;
		m_Thick = Math.Max(b.m_Offset, b.m_Slab);
		m_W = 2 * b.m_NU - 1;
		m_Hn = 2 * b.m_NV - 1;
		m_HU = b.m_StepU * 0.5;
		m_HV = b.m_StepV * 0.5;
		m_Surf = new array<float>;
		m_Exp = new array<bool>;
		m_Best = new array<float>;
		m_Own = new array<float>;
		m_Cs = new array<vector>;
		int n = m_W * m_Hn;
		for (int i = 0; i < n; i++)
		{
			m_Surf.Insert(NOHIT);
			m_Exp.Insert(false);
			m_Best.Insert(1000.0);
		}
		m_PFMax = 0;
		m_PPierMax = 0;
		m_CFlMax = 0;
		m_CBurMax = 0;
		m_GInMax = 0;
		m_CGapTop = NOHIT;
	}

	protected vector LatPos(int ra, int rc)
	{
		return b.m_Origin + b.m_U * (ra * m_HU) + b.m_V * (rc * m_HV);
	}

	protected float LU(vector p)
	{
		return ((p[0] - b.m_Origin[0]) * b.m_U[0] + (p[2] - b.m_Origin[2]) * b.m_U[2]) / m_HU;
	}

	protected float LV(vector p)
	{
		return ((p[0] - b.m_Origin[0]) * b.m_V[0] + (p[2] - b.m_Origin[2]) * b.m_V[2]) / m_HV;
	}

	//! the hits of a vertical ray on the structure itself (m_Own), the highest of them and its normal, and the
	//! highest hit on anything else solid
	protected void Ray(float x, float z, float top, float bottom, out float ownTop, out float ownNy, out float block, int geo = 0)
	{
		m_Own.Clear();
		ownTop = NOHIT;
		ownNy = -1;
		block = NOHIT;
		RaycastRVParams rp = new RaycastRVParams(Vector(x, top, z), Vector(x, bottom, z), null, 0);
		rp.type = ObjIntersectFire;
		if (geo == 1)
			rp.type = ObjIntersectView;
		else if (geo == 2)
			rp.type = ObjIntersectGeom;
		rp.flags = CollisionFlags.ALLOBJECTS;
		rp.sorted = true;
		array<ref RaycastRVResult> results = new array<ref RaycastRVResult>;
		if (!DayZPhysics.RaycastRVProxy(rp, results))
			return;
		foreach (RaycastRVResult res : results)
		{
			Object hit = res.obj;
			if (res.parent)
				hit = res.parent;
			if (!hit)
				continue;
			float hy = res.pos[1];
			if (hit == b.m_Obj)
			{
				m_Own.Insert(hy);
				if (hy > ownTop)
				{
					ownTop = hy;
					vector nd = res.dir;
					ownNy = -1;
					float nl = nd.Length();
					if (nl > 0.9 && nl < 1.1)
						ownNy = nd[1];
				}
			}
			else if (!SZ_Util.IsVegetation(hit) && !hit.IsInherited(Man) && !hit.IsInherited(DayZCreature))
			{
				if (hy > block)
					block = hy;
			}
		}
	}

	protected void Corners(SZ_RoofTri t)
	{
		m_Cs.Clear();
		if (t.m_Free)
		{
			m_Cs.Insert(t.m_P0);
			m_Cs.Insert(t.m_P1);
			m_Cs.Insert(t.m_P2);
			return;
		}
		vector hu = t.m_AxisU * 0.5;
		vector hv = t.m_AxisV * 0.5;
		vector c00 = t.m_Center - hu - hv;
		vector c10 = t.m_Center + hu - hv;
		vector c11 = t.m_Center + hu + hv;
		vector c01 = t.m_Center - hu + hv;
		if (t.m_Quad)
		{
			m_Cs.Insert(c00);
			m_Cs.Insert(c10);
			m_Cs.Insert(c11);
			m_Cs.Insert(c01);
			return;
		}
		if (t.m_Shape == 0)
		{
			m_Cs.Insert(c00);
			m_Cs.Insert(c10);
			m_Cs.Insert(c11);
		}
		else if (t.m_Shape == 1)
		{
			m_Cs.Insert(c00);
			m_Cs.Insert(c01);
			m_Cs.Insert(c11);
		}
		else if (t.m_Shape == 2)
		{
			m_Cs.Insert(c00);
			m_Cs.Insert(c10);
			m_Cs.Insert(c01);
		}
		else
		{
			m_Cs.Insert(c10);
			m_Cs.Insert(c11);
			m_Cs.Insert(c01);
		}
	}

	//! one roof piece: its centre and its corners pulled 30 percent towards the centre
	protected void PieceTest(SZ_RoofTri t)
	{
		m_PTris++;
		if (m_Stage - t.m_Drop < 1)
			return;
		m_PVis++;
		Corners(t);
		int nc = m_Cs.Count();
		vector g = "0 0 0";
		for (int ci = 0; ci < nc; ci++)
			g = g + m_Cs[ci];
		g = g * (1.0 / nc);
		int bad = 0;
		for (int q = -1; q < nc; q++)
		{
			vector p = g;
			if (q >= 0)
				p = g + (m_Cs[q] - g) * 0.7;
			float rayTop = Math.Max(b.m_Top, p[1] + 2.0);
			float ownTop;
			float ownNy;
			float block;
			m_PPts++;
			float limit = p[1] + m_Thick + 0.03;
			float support = NOHIT;
			float pierce = NOHIT;
			bool under = false;
			// fire geometry first (what the snow is built on); where it leaves the piece without support, the view and
			// collision geometry may still have the surface the eye sees (eaves often lack fire geometry)
			for (int geo = 0; geo < 3; geo++)
			{
				if (geo > 0 && support != NOHIT && p[1] - support <= 0.06)
					break;
				Ray(p[0], p[2], rayTop, p[1] - 3.0, ownTop, ownNy, block, geo);
				foreach (float h : m_Own)
				{
					if (h <= limit)
					{
						if (h > support)
							support = h;
					}
					else if (geo == 0 && h <= p[1] + m_Thick + 0.6)
					{
						if (h > pierce)
							pierce = h;
					}
					else if (geo == 0)
						under = true;
				}
			}
			if (under)
				m_PUnder++;
			if (pierce != NOHIT)
			{
				m_PPier++;
				float pAmt = pierce - p[1] - m_Thick;
				if (pAmt > m_PPierMax)
				{
					m_PPierMax = pAmt;
					m_PPierPos = p;
				}
				if (m_Dump)
					Print(string.Format("[DSTest] auditpt pierce %1 by %2", p, pAmt));
			}
			float gap;
			if (support == NOHIT)
			{
				m_PAir++;
				float floorY = Math.Max(g_Game.SurfaceY(p[0], p[2]), block);
				gap = p[1] - floorY;
			}
			else
				gap = p[1] - support;
			if (gap > 0.06)
			{
				m_PF++;
				bad++;
				if (gap > 0.15)
					m_PF15++;
				if (gap > m_PFMax)
				{
					m_PFMax = gap;
					m_PFPos = p;
				}
				if (m_Dump)
					Print(string.Format("[DSTest] auditpt float %1 gap %2 air %3", p, gap, support == NOHIT));
			}
		}
		if (bad >= 2)
			m_PFPieces++;
	}

	//! marks the lattice points under one triangle of a piece with the height of the piece above their surface
	protected void Raster(vector pa, vector pb, vector pc)
	{
		float au = LU(pa);
		float bu = LU(pb);
		float cu = LU(pc);
		float av = LV(pa);
		float bv = LV(pb);
		float cv = LV(pc);
		int a0 = Math.Max(0, Math.Floor(Math.Min(au, Math.Min(bu, cu))));
		int a1 = Math.Min(m_W - 1, Math.Ceil(Math.Max(au, Math.Max(bu, cu))));
		int c0 = Math.Max(0, Math.Floor(Math.Min(av, Math.Min(bv, cv))));
		int c1 = Math.Min(m_Hn - 1, Math.Ceil(Math.Max(av, Math.Max(bv, cv))));
		float den = (pb[2] - pc[2]) * (pa[0] - pc[0]) + (pc[0] - pb[0]) * (pa[2] - pc[2]);
		if (Math.AbsFloat(den) < 0.000001)
			return;
		for (int ra = a0; ra <= a1; ra++)
		{
			for (int rc = c0; rc <= c1; rc++)
			{
				int pa2 = ra % 2;
				int pc2 = rc % 2;
				if (pa2 != pc2)
					continue;
				int idx = rc * m_W + ra;
				if (m_Surf[idx] == NOHIT)
					continue;
				vector w = LatPos(ra, rc);
				float w1 = ((pb[2] - pc[2]) * (w[0] - pc[0]) + (pc[0] - pb[0]) * (w[2] - pc[2])) / den;
				float w2 = ((pc[2] - pa[2]) * (w[0] - pc[0]) + (pa[0] - pc[0]) * (w[2] - pc[2])) / den;
				float w3 = 1.0 - w1 - w2;
				if (w1 < -0.02 || w2 < -0.02 || w3 < -0.02)
					continue;
				float y = w1 * pa[1] + w2 * pb[1] + w3 * pc[1];
				float d = y - m_Surf[idx];
				if (Math.AbsFloat(d) < Math.AbsFloat(m_Best[idx]))
					m_Best[idx] = d;
			}
		}
	}

	//! a stair sample of the grid next to a lattice point
	protected bool NearStair(int ra, int rc)
	{
		for (int da = -1; da <= 1; da++)
		{
			for (int dc = -1; dc <= 1; dc++)
			{
				int sa = ra + da;
				int sc = rc + dc;
				if (sa < 0 || sc < 0 || sa >= m_W || sc >= m_Hn)
					continue;
				int ma = sa % 2;
				int mc = sc % 2;
				if (ma != 0 || mc != 0)
					continue;
				int k = (sc / 2) * b.m_NU + sa / 2;
				if (b.m_Stair.Contains(k))
					return true;
			}
		}
		return false;
	}

	//! how many grid samples around a lattice point found a surface
	protected int SamplesNear(int ra, int rc)
	{
		int n = 0;
		for (int da = -1; da <= 1; da++)
		{
			for (int dc = -1; dc <= 1; dc++)
			{
				int sa = ra + da;
				int sc = rc + dc;
				if (sa < 0 || sc < 0 || sa >= m_W || sc >= m_Hn)
					continue;
				int ma = sa % 2;
				int mc = sc % 2;
				if (ma != 0 || mc != 0)
					continue;
				int k = (sc / 2) * b.m_NU + sa / 2;
				if (k < b.m_H.Count() && b.m_H[k] != NOHIT)
					n++;
			}
		}
		return n;
	}

	protected void CoverRay(int idx)
	{
		int ra = idx % m_W;
		int rc = idx / m_W;
		int pa2 = ra % 2;
		int pc2 = rc % 2;
		if (pa2 != pc2)
			return;
		vector w = LatPos(ra, rc);
		float ground = g_Game.SurfaceY(w[0], w[2]);
		float ownTop;
		float ownNy;
		float block;
		// the geometry the snow of this structure was built on (collision geometry for structures without fire geometry)
		int covGeo = 0;
		if (b.m_Geo == ObjIntersectGeom)
			covGeo = 2;
		Ray(w[0], w[2], b.m_Top, b.m_Bottom, ownTop, ownNy, block, covGeo);
		if (ownTop == NOHIT || block > ownTop + 0.3 || ownTop < ground + 0.25)
			return;
		m_Surf[idx] = ownTop;
		if (NearStair(ra, rc))
			return;
		m_Exp[idx] = true;
	}

	//! the slope of the surface at a lattice point along one diagonal of the lattice (from the neighbours on the
	//! same surface); ok is false when there is none
	protected float DiagSlope(int ra, int rc, int da, int dc, float h, float dist, out bool ok)
	{
		ok = false;
		float hp = NOHIT;
		float hm = NOHIT;
		int pa = ra + da;
		int pc = rc + dc;
		int ma = ra - da;
		int mc = rc - dc;
		if (pa >= 0 && pc >= 0 && pa < m_W && pc < m_Hn)
			hp = m_Surf[pc * m_W + pa];
		if (ma >= 0 && mc >= 0 && ma < m_W && mc < m_Hn)
			hm = m_Surf[mc * m_W + ma];
		if (hp != NOHIT && Math.AbsFloat(hp - h) > dist * 2.0)
			hp = NOHIT;
		if (hm != NOHIT && Math.AbsFloat(hm - h) > dist * 2.0)
			hm = NOHIT;
		if (hp != NOHIT && hm != NOHIT)
		{
			ok = true;
			return (hp - hm) / (2.0 * dist);
		}
		if (hp != NOHIT)
		{
			ok = true;
			return (hp - h) / dist;
		}
		if (hm != NOHIT)
		{
			ok = true;
			return (h - hm) / dist;
		}
		return 0;
	}

	//! surfaces too steep to hold snow (normal below 0.5, below 0.6 when thin snow slides off) expect none
	protected void SlopeFilter()
	{
		float dist = Math.Sqrt(m_HU * m_HU + m_HV * m_HV);
		int n = m_W * m_Hn;
		for (int idx = 0; idx < n; idx++)
		{
			if (!m_Exp[idx])
				continue;
			int ra = idx % m_W;
			int rc = idx / m_W;
			bool ok1;
			bool ok2;
			float s1 = DiagSlope(ra, rc, 1, 1, m_Surf[idx], dist, ok1);
			float s2 = DiagSlope(ra, rc, 1, -1, m_Surf[idx], dist, ok2);
			if (!ok1 && !ok2)
			{
				m_CNoNormal++;
				continue;
			}
			float ny = 1.0 / Math.Sqrt(1.0 + s1 * s1 + s2 * s2);
			if (ny < 0.5 || (ny < 0.6 && m_Stage - 1 < 1))
				m_Exp[idx] = false;
		}
	}

	protected void CoverClassify()
	{
		int n = m_W * m_Hn;
		for (int idx = 0; idx < n; idx++)
		{
			if (!m_Exp[idx])
				continue;
			m_CExp++;
			int ra = idx % m_W;
			int rc = idx / m_W;
			vector w = LatPos(ra, rc);
			w[1] = m_Surf[idx];
			float d = m_Best[idx];
			if (d > 999.0)
			{
				int pa2 = ra % 2;
				int nearN = SamplesNear(ra, rc);
				if (pa2 == 0 && nearN > 0)
					m_CGapS++;
				else if (nearN > 0)
					m_CGapE++;
				else
					m_CGapSub++;
				if (nearN > 0 && w[1] > m_CGapTop)
				{
					m_CGapTop = w[1];
					m_CGapPos = w;
				}
				if (m_Dump)
					Print(string.Format("[DSTest] auditpt gap %1 samples %2", w, nearN));
				continue;
			}
			if (d > 0.1)
			{
				m_CFl++;
				if (d > m_CFlMax)
				{
					m_CFlMax = d;
					m_CFlPos = w;
				}
				if (m_Dump)
					Print(string.Format("[DSTest] auditpt coverfloat %1 by %2", w, d));
				continue;
			}
			if (d < -m_Thick - 0.3)
			{
				// the nearest piece lies far below: this surface (a chimney, a higher ledge) has no snow of its own
				m_CGapOver++;
				if (m_Dump)
					Print(string.Format("[DSTest] auditpt gapover %1 by %2", w, -d));
				continue;
			}
			if (d < -0.1)
			{
				m_CBur++;
				if (-d > m_CBurMax)
				{
					m_CBurMax = -d;
					m_CBurPos = w;
				}
				if (m_Dump)
					Print(string.Format("[DSTest] auditpt buried %1 by %2", w, -d));
				continue;
			}
			m_COk++;
		}
	}

	//! how far the drawn ground snow lies above the floor at a point inside the building (-1 when it is not seen
	//! inside: no level 0 cover there, or outside)
	protected float CarpetShows(float x, float z)
	{
		int lv;
		float above = m_Carpet.DebugCoverAt(x, z, lv);
		if (lv != 0)
			return -1.0;
		float ground = g_Game.SurfaceY(x, z);
		float top = ground + above;
		string ft;
		float fy = g_Game.SurfaceGetType3D(x, ground + 2.5, z, ft);
		bool interiorFloor = fy > ground + 0.005 && fy < ground + 2.45 && m_Carpet.DebugInterior(ft);
		if (interiorFloor && top > fy - 0.01)
			return top - fy;
		if (m_Carpet.DebugInside(x, z))
			return top - Math.Max(fy, ground);
		return -1.0;
	}

	//! the ground snow at a sample point of the grid: snow inside the building or through its floor, or bare ground
	//! outside it
	protected void GroundPoint(int idx)
	{
		int ra = idx % m_W;
		int rc = idx / m_W;
		int pa2 = ra % 2;
		int pc2 = rc % 2;
		if (pa2 != 0 || pc2 != 0)
			return;
		vector w = LatPos(ra, rc);
		float x = w[0];
		float z = w[2];
		if (g_Game.SurfaceIsPond(x, z) || g_Game.SurfaceIsSea(x, z))
			return;
		m_GPts++;
		float ground = g_Game.SurfaceY(x, z);
		int lv;
		float above = m_Carpet.DebugCoverAt(x, z, lv);
		if (lv > 0)
		{
			m_GNR++;
			return;
		}
		if (lv == 0)
		{
			float over = CarpetShows(x, z);
			if (over > -0.01)
			{
				// at the wall line the cover reaches a few centimetres into the wall: only snow seen inside all around
				// the point counts
				int deep = 0;
				for (int nb = 0; nb < 4; nb++)
				{
					vector off = b.m_U * 0.2;
					if (nb == 1)
						off = b.m_U * -0.2;
					else if (nb == 2)
						off = b.m_V * 0.2;
					else if (nb == 3)
						off = b.m_V * -0.2;
					if (CarpetShows(x + off[0], z + off[2]) > -0.01)
						deep++;
				}
				if (deep < 4)
				{
					m_GInWall++;
					return;
				}
				m_GIn++;
				if (over > m_GInMax || m_GIn == 1)
				{
					m_GInMax = over;
					m_GInPos = Vector(x, ground + above, z);
				}
				if (m_Dump)
					Print(string.Format("[DSTest] auditpt carpetin %1 over %2", Vector(x, ground + above, z), over));
			}
			return;
		}
		// no ground snow drawn here
		if (m_Carpet.DebugCell0(x, z) < 0)
		{
			m_GNR++;
			return;
		}
		if (m_Carpet.DebugInside(x, z))
			return;
		m_GGap++;
		float ownTop;
		float ownNy;
		float block;
		Ray(x, z, b.m_Top, ground + 0.05, ownTop, ownNy, block);
		if (ownTop != NOHIT)
			m_GGapRoof++;
		if (m_GGap == 1)
			m_GGapPos = Vector(x, ground, z);
		if (m_Dump)
			Print(string.Format("[DSTest] auditpt groundgap %1 roof %2", Vector(x, ground, z), ownTop != NOHIT));
	}

	//! true when done
	bool Step()
	{
		if (!b || !b.m_Obj)
			return true;
		int budget;
		if (m_Phase == 0)
		{
			budget = 120;
			while (m_Cursor < b.m_Tris.Count() && budget > 0)
			{
				PieceTest(b.m_Tris[m_Cursor]);
				m_Cursor++;
				budget--;
			}
			if (m_Cursor >= b.m_Tris.Count())
			{
				m_Phase = 1;
				m_Cursor = 0;
			}
			return false;
		}
		int n = m_W * m_Hn;
		if (m_Phase == 1)
		{
			budget = 700;
			while (m_Cursor < n && budget > 0)
			{
				CoverRay(m_Cursor);
				m_Cursor++;
				budget--;
			}
			if (m_Cursor < n)
				return false;
			SlopeFilter();
			foreach (SZ_RoofTri t : b.m_Tris)
			{
				if (m_Stage - t.m_Drop < 1)
					continue;
				Corners(t);
				Raster(m_Cs[0], m_Cs[1], m_Cs[2]);
				if (m_Cs.Count() == 4)
					Raster(m_Cs[0], m_Cs[2], m_Cs[3]);
			}
			CoverClassify();
			m_Phase = 2;
			m_Cursor = 0;
			bool ground = b.m_Kind == 0 && !b.m_Small && !b.m_Obj.IsRock();
			if (!ground)
				return true;
			return false;
		}
		budget = 250;
		while (m_Cursor < n && budget > 0)
		{
			GroundPoint(m_Cursor);
			m_Cursor++;
			budget--;
		}
		return m_Cursor >= n;
	}

	static string Header()
	{
		string h = "stop,label,shape,type,x,z,ground,kind,small,wall,rock,nu,nv,step,depth,stage,thick,tris,stairs";
		h += ",pvis,ppts,pf,pf15,pfpieces,pfmax,pfx,pfz,pfy,pair,ppier,ppiermax,ppierx,ppierz,ppiery,punder";
		h += ",cexp,cok,cgaps,cgape,cgapsub,cgapx,cgapz,cgapy,cfl,cflmax,cflx,cflz,cbur,cburmax,cburx,cburz,cnonormal,cgapover";
		h += ",gpts,gnr,gin,ginmax,ginx,ginz,giny,ggap,ggaproof,ggapx,ggapz,ginwall,geo";
		return h;
	}

	protected string V3(vector v)
	{
		return string.Format("%1,%2,%3", v[0], v[2], v[1]);
	}

	protected string V2(vector v)
	{
		return string.Format("%1,%2", v[0], v[2]);
	}

	string Line(int stop, string label)
	{
		vector p = b.m_Obj.GetPosition();
		string shape = b.m_Obj.GetShapeName();
		shape.ToLower();
		string s = string.Format("%1,%2,%3,%4,%5,%6,%7,%8,%9", stop, label, shape, b.m_Obj.GetType(), p[0], p[2], b.m_Ground, b.m_Kind, b.m_Small);
		s += string.Format(",%1,%2,%3,%4,%5,%6,%7,%8,%9", b.m_Wall, b.m_Obj.IsRock(), b.m_NU, b.m_NV, b.m_StepU, m_Depth, m_Stage, m_Thick, m_PTris);
		s += string.Format(",%1,%2,%3,%4,%5,%6,%7,%8", b.m_Stair.Count(), m_PVis, m_PPts, m_PF, m_PF15, m_PFPieces, m_PFMax, V3(m_PFPos));
		s += string.Format(",%1,%2,%3,%4,%5", m_PAir, m_PPier, m_PPierMax, V3(m_PPierPos), m_PUnder);
		s += string.Format(",%1,%2,%3,%4,%5,%6", m_CExp, m_COk, m_CGapS, m_CGapE, m_CGapSub, V3(m_CGapPos));
		s += string.Format(",%1,%2,%3,%4,%5,%6,%7,%8", m_CFl, m_CFlMax, V2(m_CFlPos), m_CBur, m_CBurMax, V2(m_CBurPos), m_CNoNormal, m_CGapOver);
		s += string.Format(",%1,%2,%3,%4,%5,%6,%7,%8,%9", m_GPts, m_GNR, m_GIn, m_GInMax, V3(m_GInPos), m_GGap, m_GGapRoof, V2(m_GGapPos), m_GInWall);
		s += "," + b.m_Geo.ToString();
		return s;
	}
}

//! a tour of audit stops (audit_stops.txt lines "x z label"): the camera waits above each stop until the snow there
//! is complete, then every structure within the radius is audited into the output file (at most perModel per model)
class DST_Audit
{
	SZ_RoofSnow m_Roofs;
	SZ_SnowCarpet m_Carpet;
	Camera m_Cam;
	ref array<vector> m_Stops;
	ref array<string> m_Labels;
	ref map<string, int> m_Count;
	ref map<string, bool> m_Seen;
	ref array<SZ_RoofBuilding> m_Queue;
	ref DST_AuditB m_Cur;
	int m_Stop;
	int m_Last;
	int m_Phase;
	int m_QI;
	float m_T;
	float m_Radius;
	int m_PerModel;
	string m_Out;
	bool m_Active;
	bool m_Dump;
	int m_Lines;
	int m_Pending;
	ref map<string, int> m_Unsnowed;
	string m_UnsnowedOut;

	void DST_Audit()
	{
		m_Stops = new array<vector>;
		m_Labels = new array<string>;
		m_Count = new map<string, int>;
		m_Seen = new map<string, bool>;
		m_Queue = new array<SZ_RoofBuilding>;
		m_Unsnowed = new map<string, int>;
	}

	bool Start(string stopsPath, string outPath, float radius, int perModel, int first, int last)
	{
		m_Stops.Clear();
		m_Labels.Clear();
		FileHandle fh = OpenFile(stopsPath, FileMode.READ);
		if (fh == 0)
			return false;
		string line;
		while (FGets(fh, line) >= 0)
		{
			line = line.Trim();
			if (line == "")
				continue;
			TStringArray parts = new TStringArray;
			line.Split(" ", parts);
			if (parts.Count() < 2)
				continue;
			m_Stops.Insert(Vector(parts[0].ToFloat(), 0, parts[1].ToFloat()));
			string label = "-";
			if (parts.Count() >= 3)
				label = parts[2];
			m_Labels.Insert(label);
		}
		CloseFile(fh);
		m_Out = outPath;
		m_Radius = radius;
		m_PerModel = perModel;
		m_Last = Math.Min(last, m_Stops.Count() - 1);
		if (!FileExist(m_Out))
			Write(DST_AuditB.Header());
		m_UnsnowedOut = outPath;
		m_UnsnowedOut.Replace("$profile:", "$profile:unsnowed_");
		if (!FileExist(m_UnsnowedOut))
		{
			FileHandle fh2 = OpenFile(m_UnsnowedOut, FileMode.WRITE);
			if (fh2 != 0)
			{
				FPrintln(fh2, "stop,label,shape,type,x,z,ground,sx,sy,sz,top,ny,building,rock,plain,path,points");
				CloseFile(fh2);
			}
		}
		m_Stop = first - 1;
		m_Active = true;
		m_Lines = 0;
		NextStop();
		return true;
	}

	protected void Write(string s)
	{
		FileHandle fw = OpenFile(m_Out, FileMode.APPEND);
		if (fw == 0)
			return;
		FPrintln(fw, s);
		CloseFile(fw);
	}

	protected void NextStop()
	{
		m_Stop++;
		m_Queue.Clear();
		m_QI = 0;
		m_Cur = null;
		if (m_Stop > m_Last || m_Stop >= m_Stops.Count())
		{
			m_Active = false;
			Print(string.Format("[DSTest] audit done lines=%1 models=%2", m_Lines, m_Count.Count()));
			return;
		}
		vector s = m_Stops[m_Stop];
		float gy = GetGame().SurfaceY(s[0], s[2]);
		if (m_Cam)
		{
			m_Cam.SetPosition(Vector(s[0], gy + 40.0, s[2] - 0.5));
			m_Cam.LookAt(Vector(s[0], gy, s[2] + 8.0));
			m_Cam.SetActive(true);
		}
		m_Phase = 1;
		m_T = 0;
	}

	//! the highest hit of a vertical ray on an object (-100000 when there is none or something else lies on it)
	protected float OwnTop(Object o, float x, float z, float top, float bottom)
	{
		RaycastRVParams rp = new RaycastRVParams(Vector(x, top, z), Vector(x, bottom, z), null, 0);
		rp.type = ObjIntersectFire;
		rp.flags = CollisionFlags.ALLOBJECTS;
		rp.sorted = true;
		array<ref RaycastRVResult> results = new array<ref RaycastRVResult>;
		if (!DayZPhysics.RaycastRVProxy(rp, results))
			return -100000.0;
		float h = -100000.0;
		float block = -100000.0;
		foreach (RaycastRVResult res : results)
		{
			Object hit = res.obj;
			if (res.parent)
				hit = res.parent;
			if (!hit)
				continue;
			if (hit == o)
				h = Math.Max(h, res.pos[1]);
			else if (!SZ_Util.IsVegetation(hit) && !hit.IsInherited(Man))
				block = Math.Max(block, res.pos[1]);
		}
		if (block > h + 0.3)
			return -100000.0;
		return h;
	}

	//! map objects near the stop the roof snow does not know that have an open top the snow would lie on (at most two
	//! placements per model, into unsnowed_<out>)
	protected void Unsnowed(vector s)
	{
		map<Object, bool> known = new map<Object, bool>;
		m_Roofs.DebugKnown(s, m_Radius + 40.0, known);
		array<Object> objs = new array<Object>;
		GetGame().GetObjectsAtPosition(Vector(s[0], GetGame().SurfaceY(s[0], s[2]), s[2]), m_Radius, objs, null);
		foreach (Object o : objs)
		{
			if (!o || known.Contains(o))
				continue;
			if (SZ_Util.IsVegetation(o) || o.IsInherited(ItemBase) || o.IsInherited(Transport) || o.IsInherited(Man) || o.IsInherited(DayZCreature))
				continue;
			string shape = o.GetShapeName();
			if (shape == "")
				continue;
			shape.ToLower();
			if (shape.IndexOf("seasonz") >= 0 || m_Unsnowed.Get(shape) >= 2)
				continue;
			vector mm[2];
			o.ClippingInfo(mm);
			vector size = mm[1] - mm[0];
			if (size[0] < 0.4 || size[2] < 0.4 || size[1] < 0.3)
				continue;
			// a 4 x 4 grid over the box: points where the top is the object's own, open to the sky and flat enough
			int good = 0;
			vector mat[4];
			o.GetTransform(mat);
			float bestTop = -100000.0;
			float bestNy = -1;
			float ground = 0;
			for (int gi = 0; gi < 16; gi++)
			{
				int gu = gi % 4;
				int gv = gi / 4;
				float gfu = 0.125 + 0.25 * gu;
				float gfv = 0.125 + 0.25 * gv;
				vector lp = Vector(mm[0][0] + size[0] * gfu, mm[1][1], mm[0][2] + size[2] * gfv);
				vector c = o.ModelToWorld(lp);
				float gnd = GetGame().SurfaceY(c[0], c[2]);
				float h = OwnTop(o, c[0], c[2], c[1] + 1.0, gnd - 0.5);
				if (h < gnd + 0.25)
					continue;
				// the slope from two short rays beside the point (a top narrower than that is no place for snow)
				vector du = Vector(mat[0][0], 0, mat[0][2]).Normalized() * 0.12;
				vector dv = Vector(mat[2][0], 0, mat[2][2]).Normalized() * 0.12;
				float hu = OwnTop(o, c[0] + du[0], c[2] + du[2], c[1] + 1.0, gnd - 0.5);
				float hv = OwnTop(o, c[0] + dv[0], c[2] + dv[2], c[1] + 1.0, gnd - 0.5);
				float slu = 0;
				float slv = 0;
				bool slopeKnown = false;
				if (hu > -99999.0 && Math.AbsFloat(hu - h) < 0.3)
				{
					slu = (hu - h) / 0.12;
					slopeKnown = true;
				}
				if (hv > -99999.0 && Math.AbsFloat(hv - h) < 0.3)
				{
					slv = (hv - h) / 0.12;
					slopeKnown = true;
				}
				if (!slopeKnown)
					continue;
				float ny = 1.0 / Math.Sqrt(1.0 + slu * slu + slv * slv);
				if (ny < 0.6)
					continue;
				good++;
				if (h - gnd > bestTop)
				{
					bestTop = h - gnd;
					bestNy = ny;
					ground = gnd;
				}
			}
			if (good < 2)
				continue;
			m_Unsnowed.Set(shape, m_Unsnowed.Get(shape) + 1);
			vector p = o.GetPosition();
			string line = string.Format("%1,%2,%3,%4,%5,%6,%7,%8,%9", m_Stop, m_Labels[m_Stop], shape, o.GetType(), p[0], p[2], ground, size[0], size[1]);
			line += string.Format(",%1,%2,%3,%4,%5,%6,%7,%8", size[2], bestTop, bestNy, o.IsBuilding(), o.IsRock(), SZ_RoofSnow.IsPlainStructure(shape), SZ_TreeSwap.IsPath(o), good);
			FileHandle fu = OpenFile(m_UnsnowedOut, FileMode.APPEND);
			if (fu != 0)
			{
				FPrintln(fu, line);
				CloseFile(fu);
			}
		}
	}

	protected string Key(SZ_RoofBuilding bb)
	{
		vector p = bb.m_Obj.GetPosition();
		int kx = Math.Round(p[0] * 10.0);
		int kz = Math.Round(p[2] * 10.0);
		return bb.m_Obj.GetShapeName() + "@" + kx.ToString() + "," + kz.ToString();
	}

	void Step(float timeslice)
	{
		if (!m_Active || !m_Roofs || !m_Carpet)
			return;
		m_T += timeslice;
		if (m_Phase == 1)
		{
			if (m_T < 1.5)
				return;
			vector s = m_Stops[m_Stop];
			array<SZ_RoofBuilding> ready = new array<SZ_RoofBuilding>;
			array<SZ_RoofBuilding> waiting = new array<SZ_RoofBuilding>;
			int tiles;
			m_Roofs.DebugReady(s, m_Radius, ready, waiting, tiles);
			// only the structures still to be audited are waited for
			int pending = tiles;
			foreach (SZ_RoofBuilding wb : waiting)
			{
				if (wb.m_Obj && !m_Seen.Contains(Key(wb)) && m_Count.Get(wb.m_Obj.GetShapeName()) < m_PerModel)
					pending++;
			}
			int lv;
			m_Carpet.DebugCoverAt(s[0], s[2], lv);
			int built = 0;
			for (int ri = 0; ri < 5; ri++)
			{
				float rx = s[0];
				float rz = s[2];
				if (ri == 1)
					rx += 25.0;
				else if (ri == 2)
					rx -= 25.0;
				else if (ri == 3)
					rz += 25.0;
				else if (ri == 4)
					rz -= 25.0;
				if (m_Carpet.DebugCell0(rx, rz) >= 0)
					built++;
			}
			bool carpetOk = built >= 5;
			if (!((pending == 0 && carpetOk && m_T >= 2.0) || m_T > 45.0))
				return;
			m_Pending = pending;
			foreach (SZ_RoofBuilding rb : ready)
			{
				string key = Key(rb);
				if (m_Seen.Contains(key))
					continue;
				string model = rb.m_Obj.GetShapeName();
				if (m_Count.Get(model) >= m_PerModel)
					continue;
				m_Seen.Set(key, true);
				m_Count.Set(model, m_Count.Get(model) + 1);
				m_Queue.Insert(rb);
			}
			Print(string.Format("[DSTest] audit stop %1/%2 %3 queue=%4 ready=%5 pending=%6 carpet=%7 wait=%8", m_Stop, m_Stops.Count(), m_Labels[m_Stop], m_Queue.Count(), ready.Count(), pending, lv, m_T));
			Unsnowed(s);
			m_Phase = 2;
			return;
		}
		// as much audit work per frame as fits in about 80 ms (the frame rate does not matter here)
		int tick0 = TickCount(0);
		float tps = SZ_RoofSnow.DebugTicksPerSec();
		int budget = 80000000;
		if (tps > 0)
			budget = tps * 0.08;
		while (TickCount(tick0) < budget)
		{
			if (!m_Cur)
			{
				if (m_QI >= m_Queue.Count())
				{
					NextStop();
					return;
				}
				SZ_RoofBuilding qb = m_Queue[m_QI];
				m_QI++;
				if (!qb || !qb.m_Obj)
					continue;
				m_Cur = new DST_AuditB(qb, m_Carpet, m_Roofs.DebugDepth(qb), m_Dump);
			}
			if (m_Cur.Step())
			{
				if (m_Cur.b && m_Cur.b.m_Obj)
				{
					Write(m_Cur.Line(m_Stop, m_Labels[m_Stop]));
					m_Lines++;
				}
				m_Cur = null;
			}
		}
	}
}


//! how far the listed placements stand from upright, per model: "shape x y z" per line, 400 per frame
class DST_Tilt
{
	protected ref array<string> m_Shapes = new array<string>;
	protected ref array<vector> m_Pos = new array<vector>;
	protected ref map<string, ref array<int>> m_Count = new map<string, ref array<int>>;
	protected int m_I;

	bool Start(string listPath)
	{
		FileHandle fh = OpenFile(listPath, FileMode.READ);
		if (fh == 0)
			return false;
		string line;
		while (FGets(fh, line) >= 0)
		{
			TStringArray parts = new TStringArray;
			line.Split(" ", parts);
			if (parts.Count() < 4)
				continue;
			m_Shapes.Insert(parts[0]);
			m_Pos.Insert(Vector(parts[1].ToFloat(), parts[2].ToFloat(), parts[3].ToFloat()));
		}
		CloseFile(fh);
		return true;
	}

	//! false when done: per model the placements within 12, 20 and 30 degrees of upright, steeper, and not found
	bool Step()
	{
		int n = 0;
		while (m_I < m_Shapes.Count() && n < 400)
		{
			string shape = m_Shapes[m_I];
			vector p = m_Pos[m_I];
			m_I++;
			n++;
			array<int> c;
			if (!m_Count.Find(shape, c))
			{
				c = new array<int>;
				for (int z = 0; z < 5; z++)
					c.Insert(0);
				m_Count.Set(shape, c);
			}
			array<Object> objs = new array<Object>;
			g_Game.GetObjectsAtPosition(p, 2.0, objs, null);
			Object found = null;
			foreach (Object o : objs)
			{
				if (!o)
					continue;
				string s = o.GetShapeName();
				s.ToLower();
				if (s == shape)
				{
					found = o;
					break;
				}
			}
			if (!found)
			{
				c[4] = c[4] + 1;
				continue;
			}
			vector up = found.GetTransformAxis(1).Normalized();
			if (up[1] >= 0.978)
				c[0] = c[0] + 1;
			else if (up[1] >= 0.94)
				c[1] = c[1] + 1;
			else if (up[1] >= 0.866)
				c[2] = c[2] + 1;
			else
				c[3] = c[3] + 1;
		}
		if (m_I < m_Shapes.Count())
			return true;
		for (int i = 0; i < m_Count.Count(); i++)
		{
			array<int> k = m_Count.GetElement(i);
			Print(string.Format("[DSTest] tilt %1 upright=%2 to20=%3 to30=%4 steeper=%5 missing=%6", m_Count.GetKey(i), k[0], k[1], k[2], k[3], k[4]));
		}
		Print("[DSTest] tilt done " + m_Shapes.Count().ToString());
		return false;
	}
}


//! bakes the roof snow of the listed models (one per frame): each is sampled on a copy standing alone high above the
//! map, with the ground the world object stands on, and written to $profile:szbake (tools/bake_snow.py makes the models)
class DST_Bake
{
	protected ref array<string> m_Shapes = new array<string>;
	protected ref array<vector> m_Pos = new array<vector>;
	protected int m_I;
	protected float m_Refine;
	protected int m_Done;
	protected int m_None;
	protected int m_Missing;
	protected vector m_Site = "7500 1500 7500";

	bool Start(string listPath, float refine)
	{
		FileHandle fh = OpenFile(listPath, FileMode.READ);
		if (fh == 0)
			return false;
		string line;
		while (FGets(fh, line) >= 0)
		{
			line = line.Trim();
			if (line == "")
				continue;
			TStringArray parts = new TStringArray;
			line.Split(" ", parts);
			if (parts.Count() < 4)
				continue;
			m_Shapes.Insert(parts[0]);
			m_Pos.Insert(Vector(parts[1].ToFloat(), parts[2].ToFloat(), parts[3].ToFloat()));
		}
		CloseFile(fh);
		m_Refine = refine;
		MakeDirectory("$profile:szbake");
		Print(string.Format("[DSTest] bake start %1 models refine %2", m_Shapes.Count(), m_Refine));
		return true;
	}

	//! false when done
	bool Step(SZ_RoofSnow roofs)
	{
		if (m_I >= m_Shapes.Count())
		{
			Print(string.Format("[DSTest] bake done baked=%1 none=%2 missing=%3", m_Done, m_None, m_Missing));
			return false;
		}
		string shape = m_Shapes[m_I];
		vector p = m_Pos[m_I];
		m_I++;
		Object world = null;
		array<Object> objs = new array<Object>;
		g_Game.GetObjectsAtPosition(p, 2.0, objs, null);
		foreach (Object o : objs)
		{
			if (!o)
				continue;
			string s = o.GetShapeName();
			s.ToLower();
			if (s == shape)
			{
				world = o;
				break;
			}
		}
		if (!world)
		{
			m_Missing++;
			Print("[DSTest] bake " + shape + " missing");
			return true;
		}
		vector wp = world.GetPosition();
		float groundRel = g_Game.SurfaceY(wp[0], wp[2]) - wp[1];
		Object copy = g_Game.CreateStaticObjectUsingP3D(shape, m_Site, "0 0 0", 1.0, true);
		if (!copy)
		{
			m_Missing++;
			Print("[DSTest] bake " + shape + " nocopy");
			return true;
		}
		// upright and unsheared: models placed along the slope would otherwise follow the terrain far below
		vector siteMat[4];
		siteMat[0] = "1 0 0";
		siteMat[1] = "0 1 0";
		siteMat[2] = "0 0 1";
		siteMat[3] = m_Site;
		copy.SetTransform(siteMat);
		string name = shape;
		name.Replace("\\", "~");
		name.Replace(".p3d", "");
		string res = roofs.BakeObject(world, copy, m_Site[1] + groundRel, "$profile:szbake\\" + name + ".txt", m_Refine);
		g_Game.ObjectDelete(copy);
		if (res == "none")
			m_None++;
		else
			m_Done++;
		Print(string.Format("[DSTest] bake %1/%2 %3 %4", m_I, m_Shapes.Count(), shape, res));
		return true;
	}
}


modded class MissionServer
{
	protected float m_DST_Poll;
	protected string m_DST_Last;

	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);
		// drive=v (with turn=deg/s and drivesecs=s set before it): the vehicles found within 30 m of the first player
		// roll forward along their own direction at v m/s, turning at the given rate
		if (m_DST_DriveTime > 0 && m_DST_DriveCars)
		{
			m_DST_DriveTime -= timeslice;
			foreach (CarScript dvCar : m_DST_DriveCars)
			{
				if (!dvCar)
					continue;
				vector dvDir = dvCar.GetDirection();
				vector dvVel = GetVelocity(dvCar);
				vector dvNew = dvDir * m_DST_DriveSpeed;
				dvNew[1] = dvVel[1];
				dBodyActive(dvCar, ActiveState.ACTIVE);
				SetVelocity(dvCar, dvNew);
				dBodySetAngularVelocity(dvCar, Vector(0, m_DST_DriveTurn * Math.DEG2RAD, 0));
			}
			if (m_DST_DriveTime <= 0)
				Print("[DSTest] drive done");
		}
		m_DST_Poll += timeslice;
		if (m_DST_Poll < 1.0)
			return;
		m_DST_Poll = 0;
		// keeps the test players fed, warm and healthy so long test runs are not cut short by starving
		m_DST_Care += 1.0;
		if (m_DST_Care >= 20.0)
		{
			m_DST_Care = 0;
			array<Man> carePlayers = new array<Man>;
			GetGame().GetPlayers(carePlayers);
			foreach (Man careMan : carePlayers)
			{
				PlayerBase careP = PlayerBase.Cast(careMan);
				if (!careP || !careP.IsAlive())
					continue;
				careP.GetStatEnergy().Set(careP.GetStatEnergy().GetMax());
				careP.GetStatWater().Set(careP.GetStatWater().GetMax());
				careP.SetHealth("", "", careP.GetMaxHealth("", ""));
				careP.SetHealth("", "Blood", careP.GetMaxHealth("", "Blood"));
				careP.SetHealth("", "Shock", careP.GetMaxHealth("", "Shock"));
				// no cold damage or hit effects in the screenshots of long winter runs
				careP.SetAllowDamage(false);
			}
		}

		string cmd = DST_File.ReadLine("$profile:dstest_weather.txt");
		if (m_DST_Track > 0)
		{
			array<Man> trPlayers = new array<Man>;
			GetGame().GetPlayers(trPlayers);
			foreach (Man trMan : trPlayers)
			{
				DayZPlayerImplement trP = DayZPlayerImplement.Cast(trMan);
				if (!trP)
					continue;
				vector trPos = trP.GetPosition();
				float trWater;
				bool trPond = SZ_Util.PondWater(trPos[0], trPos[2], trWater);
				int trIce = 0;
				if (m_SZ_Server && m_SZ_Server.GetIce())
					trIce = m_SZ_Server.GetIce().GetObjectCount();
				float trRoad = GetGame().SurfaceRoadY3D(trPos[0], trPos[1] + 2.0, trPos[2], RoadSurfaceDetection.UNDER);
				vector trWl = HumanCommandSwim.WaterLevelCheck(trP, trPos);
				int trCmd = trP.GetCurrentCommandID();
				bool trInWater = false;
				PlayerBase trPB = PlayerBase.Cast(trP);
				if (trPB)
					trInWater = trPB.IsInWater();
				Print(string.Format("[DSTest] server player %1 cmd=%2 swimming=%3 inWater=%4 aboveWater=%5 road=%6 waterLevelCheck=%7 iceplates=%8", trPos, trCmd, trP.IsSwimming(), trInWater, trPos[1] - trWater, trRoad, trWl, trIce));
			}
		}
		if (m_DST_Gardens && m_DST_Gardens.Count() > 0)
		{
			m_DST_GardenTimer += 1.0;
			if (m_DST_GardenTimer >= 5.0)
			{
				m_DST_GardenTimer = 0;
				foreach (GardenBase lgGarden : m_DST_Gardens)
				{
					if (!lgGarden)
						continue;
					string lgOut = "";
					for (int lgI = 0; lgI < lgGarden.GetGardenSlotsCount(); lgI++)
					{
						Slot lgSlot = lgGarden.GetSlotByIndex(lgI);
						if (!lgSlot || !lgSlot.GetPlant())
							continue;
						PlantBase lgPlant = lgSlot.GetPlant();
						lgOut += string.Format(" %1/%2", lgPlant.GetPlantState(), lgPlant.GetPlantStateIndex());
					}
					float lgGrowth = SZ_Winter.GrowthFactor(lgGarden, lgGarden.GetPosition());
					bool lgFreeze = SZ_Winter.Freezes(lgGarden, lgGarden.GetPosition());
					bool lgFrozen = SZ_Winter.GroundFrozen(lgGarden, lgGarden.GetPosition());
					float lgMean = SZ_Winter.DailyMean(lgGarden.GetPosition());
					float lgNow = GetGame().GetMission().GetWorldData().GetBaseEnvTemperatureAtPosition(lgGarden.GetPosition());
					Print(string.Format("[DSTest] garden %1 mean=%2 now=%3 growth=%4 frostNow=%5 groundFrozen=%6 plants(state/stage):%7", lgGarden.GetType(), lgMean, lgNow, lgGrowth, lgFreeze, lgFrozen, lgOut));
				}
			}
		}
		if (m_DST_LogEvery > 0 && m_SZ_Server)
		{
			m_DST_LogTimer += 1.0;
			if (m_DST_LogTimer >= m_DST_LogEvery)
			{
				m_DST_LogTimer = 0;
				m_SZ_Server.LogStatus("test");
			}
		}
		if (cmd == "" || cmd == m_DST_Last)
			return;
		m_DST_Last = cmd;

		TStringArray parts = new TStringArray;
		cmd.Split(" ", parts);
		Weather w = GetGame().GetWeather();
		w.GetSnowfall().SetLimits(0, 1);
		foreach (string part : parts)
		{
			TStringArray kv = new TStringArray;
			part.Split("=", kv);
			if (kv.Count() != 2)
				continue;
			string key = kv[0];
			float value = kv[1].ToFloat();
			// snowlv=a:b:c sets the snow of the three heights (0, 250, 500 m) on their own
			if (key == "snowlv" && m_SZ_Server)
			{
				TStringArray lv3 = new TStringArray;
				kv[1].Split(":", lv3);
				if (lv3.Count() == 3)
					m_SZ_Server.SetSnow(lv3[0].ToFloat(), lv3[1].ToFloat(), lv3[2].ToFloat());
			}
			else if (key == "overcast")
				w.GetOvercast().Set(value, 0, 7200);
			else if (key == "snowfall")
				w.GetSnowfall().Set(value, 0, 7200);
			else if (key == "rain")
				w.GetRain().Set(value, 0, 7200);
			else if (key == "fog")
				w.GetFog().Set(value, 0, 7200);
			else if (key == "snow")
			{
				if (m_SZ_Server)
				{
					m_SZ_Server.SetSnow(value, value * 1.4, value * 2.0);
				}
				else
				{
					SZ_State.s_Snow0 = value;
					SZ_State.s_Snow1 = value * 1.4;
					SZ_State.s_Snow2 = value * 2.0;
				}
			}
			else if (key == "anomaly")
			{
				SZ_State.s_DebugAnomaly = value;
				if (value > -100)
					SZ_State.s_TempAnomaly = value;
			}
			else if (key == "icelv" && m_SZ_Server)
			{
				TStringArray iceLevels = new TStringArray;
				kv[1].Split(":", iceLevels);
				if (iceLevels.Count() == 3)
				{
					float iceA = iceLevels[0].ToFloat();
					float iceB = iceLevels[1].ToFloat();
					float iceC = iceLevels[2].ToFloat();
					if (SZ_PersistentState.InRange(iceA, 0, 10000) && SZ_PersistentState.InRange(iceB, 0, 10000) && SZ_PersistentState.InRange(iceC, 0, 10000))
						m_SZ_Server.SetPondIce(iceA, iceB, iceC);
				}
			}
			else if (key == "featstate" && value == 1 && m_SZ_Server)
			{
				m_SZ_Server.LogStatus("feature QA server");
				m_SZ_Server.SendState(null);
				DST_FeatureState.Log("server");
			}
			else if (key == "plantpause" && value == 1 && m_DST_Gardens)
			{
				foreach (GardenBase pauseGarden : m_DST_Gardens)
				{
					if (!pauseGarden)
						continue;
					for (int slotIndex = 0; slotIndex < pauseGarden.GetGardenSlotsCount(); slotIndex++)
					{
						Slot pauseSlot = pauseGarden.GetSlotByIndex(slotIndex);
						if (pauseSlot && pauseSlot.GetPlant())
						{
							PlantBase pausePlant = pauseSlot.GetPlant();
							int pauseState = pausePlant.GetPlantState();
							if (pauseState == EPlantState.GROWING || pauseState == EPlantState.PAUSED || pauseState == EPlantState.MATURE)
								pausePlant.SetPlantState(EPlantState.PAUSED);
						}
					}
				}
				Print("[DSTest] plantpause: test plants forced into PAUSED; also test natural water starvation");
			}
			else if (key == "ice")
			{
				// ice=v: pond ice of v cm at every height
				if (m_SZ_Server)
					m_SZ_Server.SetPondIce(value, value, value);
			}
			else if (key == "plantspeed")
			{
				PlantBase.DebugSetTickSpeedMultiplier(value);
			}
			else if (key == "foodtest")
			{
				// foodtest=1: wild food as the central economy would spawn it now (EEOnCECreate), next to the first player
				array<Man> ftPlayers = new array<Man>;
				GetGame().GetPlayers(ftPlayers);
				if (ftPlayers.Count() > 0)
				{
					TStringArray ftTypes = {"SambucusBerry", "CaninaBerry", "BoletusMushroom", "PleurotusMushroom", "Apple"};
					string ftOut = "";
					float ftTemp = GetGame().GetMission().GetWorldData().GetBaseEnvTemperature();
					foreach (string ftType : ftTypes)
					{
						Edible_Base ftFood = Edible_Base.Cast(GetGame().CreateObjectEx(ftType, ftPlayers[0].GetPosition() + "1 0 1", ECE_PLACE_ON_SURFACE));
						if (!ftFood)
							continue;
						ftFood.EEOnCECreate();
						ftOut += string.Format(" %1: stage=%2 quantity=%3", ftType, ftFood.GetFoodStageType(), ftFood.GetQuantity());
						GetGame().ObjectDelete(ftFood);
					}
					Print(string.Format("[DSTest] foodtest base temp %1:%2", ftTemp, ftOut));
				}
			}
			else if (key == "garden")
			{
				// garden=0: an outdoor plot, garden=1: a greenhouse plot, 5 m in front of the first player, watered and
				// sown with tomatoes
				array<Man> gdPlayers = new array<Man>;
				GetGame().GetPlayers(gdPlayers);
				if (gdPlayers.Count() > 0)
				{
					vector gdPos = gdPlayers[0].GetPosition() + gdPlayers[0].GetDirection() * 5.0;
					gdPos[1] = GetGame().SurfaceY(gdPos[0], gdPos[2]);
					string gdClass = "GardenPlot";
					if (value > 0.5)
						gdClass = "GardenPlotGreenhouse";
					GardenBase gdGarden = GardenBase.Cast(GetGame().CreateObjectEx(gdClass, gdPos, ECE_PLACE_ON_SURFACE));
					if (gdGarden)
					{
						gdGarden.WaterAllSlots();
						for (int gdI = 1; gdI <= gdGarden.GetGardenSlotsCount(); gdI++)
						{
							int gdSlotId = InventorySlots.GetSlotIdFromString("SeedBase_" + gdI.ToString());
							gdGarden.GetInventory().CreateAttachmentEx("TomatoSeeds", gdSlotId);
						}
						if (!m_DST_Gardens)
							m_DST_Gardens = new array<GardenBase>;
						m_DST_Gardens.Insert(gdGarden);
					}
					Print(string.Format("[DSTest] garden %1 at %2 -> %3", gdClass, gdPos, gdGarden));
				}
			}
			else if (key == "logevery")
			{
				m_DST_LogEvery = value;
				m_DST_LogTimer = 0;
			}
			else if (key == "wlog")
			{
				SZ_State.s_DebugWeatherLog = value > 0;
			}
			else if (key == "wtest")
			{
				// runs weather decisions back to back: overcast (clear/cloudy/bad) and fog
				WorldData wtd = GetGame().GetMission().GetWorldData();
				bool wasLog = SZ_State.s_DebugWeatherLog;
				SZ_State.s_DebugWeatherLog = true;
				for (int wi = 0; wi < value; wi++)
				{
					wtd.WeatherOnBeforeChange(EWeatherPhenomenon.OVERCAST, 0.5, 0, 600);
					wtd.WeatherOnBeforeChange(EWeatherPhenomenon.FOG, 0.1, 0, 600);
				}
				SZ_State.s_DebugWeatherLog = wasLog;
				Print("[DSTest] weather test done: " + value.ToString());
			}
			else if (key == "doy")
			{
				SZ_State.s_DebugDoy = value;
			}
			else if (key == "hour")
			{
				int year;
				int month;
				int day;
				int hour;
				int minute;
				GetGame().GetWorld().GetDate(year, month, day, hour, minute);
				GetGame().GetWorld().SetDate(year, month, day, value, 0);
			}
			else if (key == "tpx")
			{
				m_DST_TpX = value;
			}
			else if (key == "give")
			{
				array<Man> givePlayers = new array<Man>;
				GetGame().GetPlayers(givePlayers);
				foreach (Man giveMan : givePlayers)
				{
					PlayerBase giveP = PlayerBase.Cast(giveMan);
					if (giveP)
					{
						EntityAI given = giveP.GetHumanInventory().CreateInHands(kv[1]);
						Print(string.Format("[DSTest] give %1 -> %2", kv[1], given));
					}
				}
			}
			else if (key == "spawn")
			{
				// spawn=Class: places the object 6 m in front of the first player; spawn=car adds a complete hatchback
				array<Man> spPlayers = new array<Man>;
				GetGame().GetPlayers(spPlayers);
				if (spPlayers.Count() > 0)
				{
					Man spMan = spPlayers[0];
					vector spPos = spMan.GetPosition() + spMan.GetDirection() * 6.0;
					spPos[1] = GetGame().SurfaceY(spPos[0], spPos[2]);
					string spClass = kv[1];
					if (spClass == "car")
						spClass = "OffroadHatchback";
					EntityAI spawned = EntityAI.Cast(GetGame().CreateObjectEx(spClass, spPos, ECE_PLACE_ON_SURFACE));
					if (spawned && spClass == "OffroadHatchback")
					{
						TStringArray spParts = {"HatchbackWheel", "HatchbackWheel", "HatchbackWheel", "HatchbackWheel", "HatchbackDoors_Driver", "HatchbackDoors_CoDriver", "HatchbackHood", "HatchbackTrunk", "CarBattery", "CarRadiator", "SparkPlug", "HeadlightH7", "HeadlightH7"};
						foreach (string spPart : spParts)
							spawned.GetInventory().CreateAttachment(spPart);
					}
					Print(string.Format("[DSTest] spawn %1 at %2 -> %3", spClass, spPos, spawned));
				}
			}
			else if (key == "nudge")
			{
				// handled below
			}
			if (key == "killtree")
			{
				// killtree=r: destroys the map tree nearest to the first player within r metres, as felling it would
				array<Man> ktPlayers = new array<Man>;
				GetGame().GetPlayers(ktPlayers);
				if (ktPlayers.Count() > 0)
				{
					array<Object> ktObjs = new array<Object>;
					GetGame().GetObjectsAtPosition(ktPlayers[0].GetPosition(), value, ktObjs, null);
					Object ktBest = null;
					float ktD = value;
					foreach (Object ktO : ktObjs)
					{
						if (!ktO || !ktO.IsTree())
							continue;
						float ktDist = vector.Distance(ktO.GetPosition(), ktPlayers[0].GetPosition());
						if (ktDist < ktD)
						{
							ktD = ktDist;
							ktBest = ktO;
						}
					}
					bool ktDead = false;
					if (ktBest)
					{
						ktBest.SetHealth("", "", 0);
						ktDead = ktBest.IsDamageDestroyed();
					}
					Print(string.Format("[DSTest] killtree %1 destroyed=%2", ktBest, ktDead));
				}
			}
			if (key == "nudge")
			{
				// nudge=v: pushes the vehicles within 30 m of the first player east at about v m/s (a physics impulse,
				// so the move reaches the clients like a real drive)
				array<Man> ndPlayers = new array<Man>;
				GetGame().GetPlayers(ndPlayers);
				if (ndPlayers.Count() > 0)
				{
					array<Object> ndObjs = new array<Object>;
					GetGame().GetObjectsAtPosition(ndPlayers[0].GetPosition(), 30.0, ndObjs, null);
					foreach (Object ndO : ndObjs)
					{
						CarScript ndCar = CarScript.Cast(ndO);
						if (!ndCar)
							continue;
						float ndMass = dBodyGetMass(ndCar);
						dBodyActive(ndCar, ActiveState.ACTIVE);
						dBodyApplyImpulse(ndCar, Vector(value * ndMass, 0, 0));
						Print(string.Format("[DSTest] nudge %1 mass=%2 from %3", ndCar, ndMass, ndCar.GetPosition()));
					}
				}
			}
			else if (key == "turn")
			{
				m_DST_DriveTurn = value;
			}
			else if (key == "haze")
			{
				// haze=v: strength of the winter haze (config WinterHaze), applied right away
				SZ_State.s_WinterHaze = value;
				GetGame().GetMission().GetWorldData().SZ_EnforceHaze();
				float hzFloor = GetGame().GetMission().GetWorldData().SZ_HazeFloor();
				Print(string.Format("[DSTest] haze strength=%1 floor=%2 fog forecast=%3 actual=%4", value, hzFloor, GetGame().GetWeather().GetFog().GetForecast(), GetGame().GetWeather().GetFog().GetActual()));
			}
			else if (key == "drivesecs")
			{
				m_DST_DriveSecs = value;
			}
			else if (key == "drive")
			{
				m_DST_DriveCars = new array<CarScript>;
				array<Man> dkPlayers = new array<Man>;
				GetGame().GetPlayers(dkPlayers);
				if (dkPlayers.Count() > 0)
				{
					array<Object> dkObjs = new array<Object>;
					GetGame().GetObjectsAtPosition(dkPlayers[0].GetPosition(), 30.0, dkObjs, null);
					foreach (Object dkO : dkObjs)
					{
						CarScript dkCar = CarScript.Cast(dkO);
						if (dkCar)
							m_DST_DriveCars.Insert(dkCar);
					}
				}
				m_DST_DriveSpeed = value;
				m_DST_DriveTime = 8.0;
				if (m_DST_DriveSecs > 0)
					m_DST_DriveTime = m_DST_DriveSecs;
				Print(string.Format("[DSTest] drive cars=%1 speed=%2 turn=%3 secs=%4", m_DST_DriveCars.Count(), m_DST_DriveSpeed, m_DST_DriveTurn, m_DST_DriveTime));
			}
			else if (key == "tpz")
			{
				array<Man> players = new array<Man>;
				GetGame().GetPlayers(players);
				foreach (Man pl : players)
				{
					vector tp = Vector(m_DST_TpX, 0, value);
					tp[1] = GetGame().SurfaceY(tp[0], tp[2]);
					// on a pond: just above the water (a frozen pond catches the player, open water does not)
					float tpWater;
					if (SZ_Util.PondWater(tp[0], tp[2], tpWater))
						tp[1] = tpWater + 0.4;
					pl.SetPosition(tp);
				}
			}
			else if (key == "trackp")
			{
				m_DST_Track = value;
			}
		}
		Print("[DSTest] server command: " + cmd);
	}
	protected float m_DST_TpX;
	protected float m_DST_Care;
	protected ref array<CarScript> m_DST_DriveCars;
	protected float m_DST_DriveTime;
	protected float m_DST_DriveSpeed;
	protected float m_DST_DriveTurn;
	protected float m_DST_DriveSecs;
	protected float m_DST_LogEvery;
	protected float m_DST_LogTimer;
	protected ref array<GardenBase> m_DST_Gardens;
	protected float m_DST_GardenTimer;
	protected float m_DST_Track;
}

modded class MissionGameplay
{
	protected float m_DST_Poll;
	protected string m_DST_Last;
	protected Camera m_DST_Cam;
	protected float m_DST_FpsTime;
	protected int m_DST_Frames;
	protected float m_DST_FlatR;
	protected float m_DST_FlatC;
	protected float m_DST_FlatT;
	protected float m_DST_FlatH;
	protected int m_DST_FlatMode;
	protected bool m_DST_Checked;
	protected float m_DST_WalkLeft;
	protected float m_DST_WalkSpeed;
	protected ref DST_TreeScan m_DST_Scan;
	protected ref DST_BuildScan m_DST_BScan;
	protected ref DST_Audit m_DST_Audit;
	// sweep: after a camera move, "settled <tag>" is printed once the snow cover, roof snow and grass cutters near the
	// camera stopped changing
	protected string m_DST_SettleTag = "";
	protected float m_DST_SettleT;
	protected float m_DST_SettleStill;
	protected int m_DST_SettleSum;
	// camabs: "near <tag> ready" once the roof snow within 40 m of the point looked at and the ground cover around it
	// are complete (the view's subject), independent of the work further out
	protected string m_DST_NearTag = "";
	protected vector m_DST_NearPos;
	protected float m_DST_NearT;
	protected ref array<Object> m_DST_Cutters;
	protected ref array<Object> m_DST_Placed;
	// fly x0 z0 x1 z1 h secs: static camera moving along a line at h metres above the ground, looking ahead
	protected float m_DST_FlyT = -1;
	protected float m_DST_FlySecs;
	protected float m_DST_FlyH;
	protected vector m_DST_FlyA;
	protected vector m_DST_FlyB;
	protected Object m_DST_ActRepl;
	protected float m_DST_ActWait;
	protected float m_DST_ActHold;
	protected bool m_DST_ActChop;
	protected ref DST_PondMap m_DST_PondMap;
	protected ref DST_Bake m_DST_Bake;
	protected ref DST_Tilt m_DST_Tilt;
	protected ref array<Object> m_DST_Shown = new array<Object>;
	protected float m_DST_PTrack;
	protected float m_DST_PTrackT;

	//! the step jobs of the harness (kept out of OnUpdate, which is at the instruction limit)
	protected void DST_Steps(float timeslice)
	{
		if (m_DST_BScan)
			m_DST_BScan.Step(timeslice);
		if (m_DST_Audit)
			m_DST_Audit.Step(timeslice);
		if (m_DST_Bake && m_SZ_Client && m_SZ_Client.GetRoofs())
		{
			if (!m_DST_Bake.Step(m_SZ_Client.GetRoofs()))
				m_DST_Bake = null;
		}
		if (m_DST_Tilt && !m_DST_Tilt.Step())
			m_DST_Tilt = null;
	}

	//! more test harness commands (kept out of OnUpdate, which is at the instruction limit)
	protected bool DST_Extra2(string cmd)
	{
		if (cmd == "featstate")
		{
			DST_FeatureState.Log("client");
			return true;
		}
		// Deliberate authority test ONLY for the isolated local QA server, using copied disposable state.
		if (cmd == "featrpc")
		{
			if (GetGame().IsServer())
				return true;
			if (DST_File.ReadLine("$profile:feature_qa_local_only.txt") != "LOCAL_DISPOSABLE_PROFILE")
			{
				Print("[DSTest] featrpc blocked: arm only in a disposable LOCAL QA client profile");
				return true;
			}
			Param publication;
			if (SZ_Const.RPC_STATE == 83610418)
			{
				array<float> values = {2.0, 231.0, 7.0, 11.0, 13.0, 17.0, 6.0, 8.0, 10.0};
				array<int> carrying = new array<int>;
				string rpcWorld;
				GetGame().GetWorldName(rpcWorld);
				rpcWorld.ToLower();
				for (int pond = 0; pond < SZ_PondProtocol.CountForWorld(rpcWorld); pond++)
					carrying.Insert(1);
				publication = new Param4<int, string, ref array<float>, ref array<int>>(SZ_PondProtocol.LAYOUT, rpcWorld, values, carrying);
			}
			else
				publication = new Param8<float, float, float, float, float, float, float, float>(231, 7, 11, 13, 17, 6, 8, 10);
			GetGame().RPCSingleParam(null, SZ_Const.RPC_STATE, publication, true, null);
			Print("[DSTest] featrpc publication sent to the local QA server; inspect SERVER values, not this acknowledgement");
			return true;
		}
		// bake list [refine]: bakes the roof snow of the models listed in the client profile ("shape x y z" per line)
		// tilt list: how far the listed placements stand from upright, per model
		// bakednear x z r: the structures near a point with snow, one line each (shape, baked model, pieces, box)
		// showcap shape name variant x y z: a copy of a model with its baked snow (name "-": none) standing upright at a
		// point, for the review of the baked models; "showcap clear" removes it
		if (cmd.IndexOf("showcap ") == 0)
		{
			TStringArray scArgs = new TStringArray;
			cmd.Split(" ", scArgs);
			foreach (Object scOld : m_DST_Shown)
			{
				if (scOld)
					g_Game.ObjectDelete(scOld);
			}
			m_DST_Shown.Clear();
			if (scArgs.Count() >= 7)
			{
				vector scMat[4];
				scMat[0] = "1 0 0";
				scMat[1] = "0 1 0";
				scMat[2] = "0 0 1";
				scMat[3] = Vector(scArgs[4].ToFloat(), scArgs[5].ToFloat(), scArgs[6].ToFloat());
				Object scModel = g_Game.CreateStaticObjectUsingP3D(scArgs[1], scMat[3], "0 0 0", 1.0, true);
				if (scModel)
				{
					scModel.SetTransform(scMat);
					m_DST_Shown.Insert(scModel);
				}
				if (scArgs[2] != "-")
				{
					Object scCap = g_Game.CreateStaticObjectUsingP3D(SZ_Const.BAKED + scArgs[2].Substring(0, 1) + "\\" + scArgs[2] + "_v" + scArgs[3] + ".p3d", scMat[3], "0 0 0", 1.0, true);
					if (scCap)
					{
						vector scC = scCap.GetBoundingCenter();
						vector scCapMat[4];
						scCapMat[0] = "1 0 0";
						scCapMat[1] = "0 1 0";
						scCapMat[2] = "0 0 1";
						scCapMat[3] = scMat[3] + scC;
						scCap.SetTransform(scCapMat);
						m_DST_Shown.Insert(scCap);
					}
				}
			}
			Print("[DSTest] showcap ready " + m_DST_Shown.Count().ToString());
			return true;
		}
		if (cmd.IndexOf("bakednear ") == 0)
		{
			TStringArray bnArgs = new TStringArray;
			cmd.Split(" ", bnArgs);
			if (m_SZ_Client && m_SZ_Client.GetRoofs() && bnArgs.Count() >= 4)
				m_SZ_Client.GetRoofs().DebugBaked(bnArgs[1].ToFloat(), bnArgs[2].ToFloat(), bnArgs[3].ToFloat());
			Print("[DSTest] bakednear end");
			return true;
		}
		if (cmd.IndexOf("tilt ") == 0)
		{
			m_DST_Tilt = new DST_Tilt();
			if (!m_DST_Tilt.Start("$profile:" + cmd.Substring(5, cmd.Length() - 5)))
				m_DST_Tilt = null;
			return true;
		}
		// into $profile:szbake (tools/bake_snow.py makes the models); refine: how much finer than at close range
		if (cmd.IndexOf("bake ") == 0)
		{
			TStringArray bkArgs = new TStringArray;
			cmd.Split(" ", bkArgs);
			float bkRefine = 1.0;
			if (bkArgs.Count() >= 3)
				bkRefine = bkArgs[2].ToFloat();
			m_DST_Bake = new DST_Bake();
			if (!m_DST_Bake.Start("$profile:" + bkArgs[1], bkRefine))
			{
				m_DST_Bake = null;
				Print("[DSTest] bake: no list " + bkArgs[1]);
			}
			return true;
		}
		// baked 0|1: the snow baked per model on or off; the tiles are scanned again
		if (cmd.IndexOf("baked ") == 0)
		{
			SZ_State.s_DebugBaked = cmd.IndexOf("baked 1") == 0;
			if (m_SZ_Client && m_SZ_Client.GetRoofs())
				m_SZ_Client.GetRoofs().DebugReapply(true);
			Print("[DSTest] baked=" + SZ_State.s_DebugBaked.ToString() + " models=" + SZ_BakedSnow.Count().ToString());
			return true;
		}
		// audit stops out radius perModel first last [dump]: the snow audit tour over the stops in the client profile
		if (cmd.IndexOf("audit ") == 0)
		{
			TStringArray auArgs = new TStringArray;
			cmd.Split(" ", auArgs);
			if (auArgs.Count() < 7 || !m_SZ_Client)
				return true;
			if (!m_DST_Cam)
				Class.CastTo(m_DST_Cam, GetGame().CreateObject("staticcamera", GetGame().GetCurrentCameraPosition(), true));
			m_DST_Audit = new DST_Audit();
			m_DST_Audit.m_Roofs = m_SZ_Client.GetRoofs();
			m_DST_Audit.m_Carpet = m_SZ_Client.GetCarpet();
			m_DST_Audit.m_Cam = m_DST_Cam;
			m_DST_Audit.m_Dump = auArgs.Count() >= 8 && auArgs[7] == "dump";
			bool auOk = m_DST_Audit.Start("$profile:" + auArgs[1], "$profile:" + auArgs[2], auArgs[3].ToFloat(), auArgs[4].ToInt(), auArgs[5].ToInt(), auArgs[6].ToInt());
			Print("[DSTest] audit start " + auOk.ToString() + " stops=" + m_DST_Audit.m_Stops.Count().ToString());
			return true;
		}
		if (cmd.IndexOf("auditstop") == 0)
		{
			if (m_DST_Audit)
				m_DST_Audit.m_Active = false;
			Print("[DSTest] audit stopped");
			return true;
		}
		// shot name: a screenshot of the client (MakeScreenshot with the name as given)
		if (cmd.IndexOf("shot ") == 0)
		{
			string shName = cmd.Substring(5, cmd.Length() - 5);
			MakeDirectory("$profile:shots");
			MakeScreenshot(shName);
			Print("[DSTest] shot " + shName);
			return true;
		}
		// waterat x z: the engine's water tests at a point (sea, pond, ground and water height)
		if (cmd.IndexOf("waterat ") == 0)
		{
			TStringArray waArgs = new TStringArray;
			cmd.Split(" ", waArgs);
			float waX = waArgs[1].ToFloat();
			float waZ = waArgs[2].ToFloat();
			float waG = GetGame().SurfaceY(waX, waZ);
			float waW = GetGame().GetWaterSurfaceHeightNoFakeWave(Vector(waX, waG, waZ));
			Print(string.Format("[DSTest] waterat %1 %2 sea=%3 pond=%4 ground=%5 water=%6", waX, waZ, GetGame().SurfaceIsSea(waX, waZ), GetGame().SurfaceIsPond(waX, waZ), waG, waW));
			return true;
		}
		// near x z r [hide]: map objects (not snow cover, not trees) whose box covers a point within r; hide scales them
		if (cmd.IndexOf("near ") == 0)
		{
			TStringArray nrArgs = new TStringArray;
			cmd.Split(" ", nrArgs);
			float nrX = nrArgs[1].ToFloat();
			float nrZ = nrArgs[2].ToFloat();
			float nrR = nrArgs[3].ToFloat();
			bool nrHide = nrArgs.Count() >= 5 && nrArgs[4] == "hide";
			bool nrShow = nrArgs.Count() >= 5 && nrArgs[4] == "show";
			vector nrP = Vector(nrX, GetGame().SurfaceY(nrX, nrZ), nrZ);
			array<Object> nrObjs = new array<Object>;
			GetGame().GetObjectsAtPosition(nrP, 60.0, nrObjs, null);
			int nrN = 0;
			foreach (Object nrO : nrObjs)
			{
				if (!nrO || nrO.IsInherited(Man))
					continue;
				string nrShape = nrO.GetShapeName();
				string nrLow = nrShape;
				nrLow.ToLower();
				if (nrLow.IndexOf("seasonz") >= 0 || nrLow.IndexOf("clutter_cutter") >= 0)
					continue;
				// distance from the point to the object's box in its own horizontal axes
				vector nrLocal = nrO.WorldToModel(nrP);
				vector nrMM[2];
				nrO.ClippingInfo(nrMM);
				if (nrO.GetScale() < 0.01)
				{
					// a hidden object: its transform is degenerate, so the centre distance minus the box radius
					vector nrOff = nrP - nrO.GetPosition();
					nrOff[1] = 0;
					float nrRad = Math.Max(Math.Max(nrMM[1][0], -nrMM[0][0]), Math.Max(nrMM[1][2], -nrMM[0][2]));
					nrLocal = Vector(Math.Max(0, nrOff.Length() - nrRad) + nrMM[1][0], 0, 0);
				}
				float nrDX = Math.Max(0, Math.Max(nrMM[0][0] - nrLocal[0], nrLocal[0] - nrMM[1][0]));
				float nrDZ = Math.Max(0, Math.Max(nrMM[0][2] - nrLocal[2], nrLocal[2] - nrMM[1][2]));
				if (Math.Sqrt(nrDX * nrDX + nrDZ * nrDZ) > nrR)
					continue;
				nrN++;
				vector nrPos = nrO.GetPosition();
				Print(string.Format("[DSTest] near %1 type=%2 pos=%3 above=%4 box=%5..%6 scale=%7", nrShape, nrO.GetType(), nrPos, nrPos[1] - GetGame().SurfaceY(nrPos[0], nrPos[2]), nrMM[0], nrMM[1], nrO.GetScale()));
				if (nrHide)
				{
					nrO.SetScale(0.001);
					nrO.Update();
				}
				else if (nrShow)
				{
					nrO.SetScale(1.0);
					nrO.Update();
				}
			}
			Print("[DSTest] near end count=" + nrN.ToString());
			return true;
		}
		// lowobj R: low map objects (lower than 0.8 m above their base) around the camera, by model
		if (cmd.IndexOf("lowobj ") == 0)
		{
			float loR = cmd.Substring(7, cmd.Length() - 7).ToFloat();
			vector loC = GetGame().GetCurrentCameraPosition();
			array<Object> loObjs = new array<Object>;
			GetGame().GetObjectsAtPosition(loC, loR, loObjs, null);
			map<string, int> loCount = new map<string, int>;
			map<string, float> loTop = new map<string, float>;
			foreach (Object loO : loObjs)
			{
				if (!loO || loO.IsInherited(EntityAI) || loO.IsTree() || loO.IsBush())
					continue;
				string loShape = loO.GetShapeName();
				loShape.ToLower();
				if (loShape == "" || loShape.IndexOf("seasonz") >= 0 || loShape.IndexOf("plants") >= 0 || loShape.IndexOf("clutter_cutter") >= 0)
					continue;
				vector loMM[2];
				loO.ClippingInfo(loMM);
				vector loP = loO.GetPosition();
				float loGround = GetGame().SurfaceY(loP[0], loP[2]);
				float loTopY = loP[1] + loMM[1][1] * loO.GetScale() - loGround;
				if (loTopY > 0.8)
					continue;
				loCount.Set(loShape, loCount.Get(loShape) + 1);
				loTop.Set(loShape, Math.Max(loTop.Get(loShape), loTopY));
			}
			Print("[DSTest] lowobj r=" + loR.ToString() + " kinds=" + loCount.Count().ToString());
			for (int loI = 0; loI < loCount.Count(); loI++)
				Print(string.Format("[DSTest] lowobj %1 x%2 top=%3", loCount.GetKey(loI), loCount.GetElement(loI), loTop.Get(loCount.GetKey(loI))));
			Print("[DSTest] lowobj end");
			return true;
		}
		// pathinfo R: footpath models around the camera and their current scale (0.001 = hidden)
		if (cmd.IndexOf("pathinfo ") == 0)
		{
			float piR = cmd.Substring(9, cmd.Length() - 9).ToFloat();
			vector piC = GetGame().GetCurrentCameraPosition();
			array<Object> piObjs = new array<Object>;
			GetGame().GetObjectsAtPosition(piC, piR, piObjs, null);
			int piAll = 0;
			int piHidden = 0;
			string piEx = "";
			foreach (Object piO : piObjs)
			{
				if (!piO || !SZ_TreeSwap.IsPath(piO))
					continue;
				piAll++;
				if (piO.GetScale() < 0.01)
					piHidden++;
				if (piAll <= 6)
					piEx += string.Format(" (%1 scale=%2 pos=%3 type=%4)", piO.GetShapeName(), piO.GetScale(), piO.GetPosition(), piO.GetType());
			}
			Print(string.Format("[DSTest] pathinfo r=%1 paths=%2 hidden=%3", piR, piAll, piHidden) + piEx);
			return true;
		}
		// dup x z: every snow cover object in the world whose triangle covers a point, with its surface height there
		if (cmd.IndexOf("dup ") == 0)
		{
			TStringArray dpArgs = new TStringArray;
			cmd.Split(" ", dpArgs);
			float dpX = dpArgs[1].ToFloat();
			float dpZ = dpArgs[2].ToFloat();
			float dpG = GetGame().SurfaceY(dpX, dpZ);
			array<Object> dpObjs = new array<Object>;
			GetGame().GetObjectsAtPosition(Vector(dpX, dpG, dpZ), 40.0, dpObjs, null);
			int dpAll = 0;
			int dpHit = 0;
			foreach (Object dpO : dpObjs)
			{
				if (!dpO)
					continue;
				string dpShape = dpO.GetShapeName();
				dpShape.ToLower();
				if (dpShape.IndexOf("seasonz\\data\\snow\\") < 0)
					continue;
				dpAll++;
				// the point in model space: the triangle lies in the model's y = -centre plane
				vector dpLocal = dpO.WorldToModel(Vector(dpX, dpG, dpZ));
				vector dpMM[2];
				dpO.ClippingInfo(dpMM);
				if (dpLocal[0] < dpMM[0][0] - 0.01 || dpLocal[0] > dpMM[1][0] + 0.01 || dpLocal[2] < dpMM[0][2] - 0.01 || dpLocal[2] > dpMM[1][2] + 0.01)
					continue;
				// height of the model's top plane (y = max of the box) straight above the point
				vector dpTopA = dpO.ModelToWorld(Vector(dpLocal[0], dpMM[1][1], dpLocal[2]));
				dpHit++;
				Print(string.Format("[DSTest] dup %1 pos=%2 top=%3 aboveTerrain=%4 local=%5", dpShape, dpO.GetPosition(), dpTopA, dpTopA[1] - dpG, dpLocal));
			}
			Print(string.Format("[DSTest] dup end objects=%1 boxesOverPoint=%2", dpAll, dpHit));
			return true;
		}
		// place p3d x z h: a static model on the ground (aligned to the terrain) as a visual reference
		if (cmd.IndexOf("place ") == 0)
		{
			TStringArray plArgs = new TStringArray;
			cmd.Split(" ", plArgs);
			float plX = plArgs[2].ToFloat();
			float plZ = plArgs[3].ToFloat();
			float plH = plArgs[4].ToFloat();
			vector plP = Vector(plX, GetGame().SurfaceY(plX, plZ) + plH, plZ);
			Object plO = GetGame().CreateStaticObjectUsingP3D(plArgs[1], plP, "0 0 0", 1.0, true);
			if (plO)
			{
				vector plUp = GetGame().SurfaceGetNormal(plX, plZ);
				vector plFwd = Vector(0, 0, 1) - plUp * plUp[2];
				plFwd.Normalize();
				vector plSide = Vector(plUp[1] * plFwd[2] - plUp[2] * plFwd[1], plUp[2] * plFwd[0] - plUp[0] * plFwd[2], plUp[0] * plFwd[1] - plUp[1] * plFwd[0]);
				vector plM[4];
				plM[0] = plSide;
				plM[1] = plUp;
				plM[2] = plFwd;
				plM[3] = plP;
				plO.SetTransform(plM);
				vector plMM[2];
				plO.ClippingInfo(plMM);
				if (!m_DST_Placed)
					m_DST_Placed = new array<Object>;
				m_DST_Placed.Insert(plO);
				Print(string.Format("[DSTest] placed %1 at %2 box %3..%4", plArgs[1], plP, plMM[0], plMM[1]));
			}
			else
				Print("[DSTest] place failed " + plArgs[1]);
			return true;
		}
		if (cmd.IndexOf("unplace") == 0)
		{
			if (m_DST_Placed)
			{
				foreach (Object upO : m_DST_Placed)
				{
					if (upO)
						GetGame().ObjectDelete(upO);
				}
				m_DST_Placed.Clear();
			}
			Print("[DSTest] placed objects removed");
			return true;
		}
		// pondmap: every water surface object of the map into $profile:dst_ponds.txt
		if (cmd.IndexOf("pondmap") == 0)
		{
			m_DST_PondMap = new DST_PondMap();
			m_DST_PondMap.Start("$profile:dst_ponds.txt");
			Print("[DSTest] pondmap started");
			return true;
		}
		// pondinfo x z: water and terrain at a point, and the water objects around it
		if (cmd.IndexOf("pondinfo ") == 0)
		{
			TStringArray pqArgs = new TStringArray;
			cmd.Split(" ", pqArgs);
			float pqX = pqArgs[1].ToFloat();
			float pqZ = pqArgs[2].ToFloat();
			float pqG = GetGame().SurfaceY(pqX, pqZ);
			bool pqPond = GetGame().SurfaceIsPond(pqX, pqZ);
			bool pqSea = GetGame().SurfaceIsSea(pqX, pqZ);
			float pqW = GetGame().GetWaterSurfaceHeightNoFakeWave(Vector(pqX, pqG, pqZ));
			float pqW2 = GetGame().GetWaterSurfaceHeightNoFakeWave(Vector(pqX, pqG + 30, pqZ));
			float pqD = GetGame().GetWaterDepth(Vector(pqX, pqG, pqZ));
			string pqOut = string.Format("pondinfo %1 %2: ground=%3 pond=%4 sea=%5 waterY=%6 waterY(+30)=%7 depth=%8", pqX, pqZ, pqG, pqPond, pqSea, pqW, pqW2, pqD);
			array<Object> pqObjs = new array<Object>;
			GetGame().GetObjectsAtPosition(Vector(pqX, pqG, pqZ), 150, pqObjs, null);
			foreach (Object pqO : pqObjs)
			{
				if (!pqO)
					continue;
				string pqS = pqO.GetShapeName();
				pqS.ToLower();
				if (pqS.IndexOf("\\water") < 0)
					continue;
				vector pqB[2];
				pqO.ClippingInfo(pqB);
				pqOut += string.Format(" | %1 pos=%2 ori=%3 box=%4..%5", pqS, pqO.GetPosition(), pqO.GetOrientation(), pqB[0], pqB[1]);
			}
			Print("[DSTest] " + pqOut);
			return true;
		}
		// placew p3d x z h yaw: a static model level at the water surface (+h), turned by yaw
		if (cmd.IndexOf("placew ") == 0)
		{
			TStringArray pwArgs = new TStringArray;
			cmd.Split(" ", pwArgs);
			float pwX = pwArgs[2].ToFloat();
			float pwZ = pwArgs[3].ToFloat();
			float pwH = pwArgs[4].ToFloat();
			float pwYaw = 0;
			if (pwArgs.Count() > 5)
				pwYaw = pwArgs[5].ToFloat();
			float pwG = GetGame().SurfaceY(pwX, pwZ);
			float pwW = GetGame().GetWaterSurfaceHeightNoFakeWave(Vector(pwX, pwG, pwZ));
			vector pwP = Vector(pwX, pwW + pwH, pwZ);
			Object pwO = GetGame().CreateStaticObjectUsingP3D(pwArgs[1], pwP, Vector(pwYaw, 0, 0), 1.0, true);
			if (pwO)
			{
				pwO.SetOrientation(Vector(pwYaw, 0, 0));
				pwO.SetPosition(pwP);
				vector pwB[2];
				pwO.ClippingInfo(pwB);
				if (!m_DST_Placed)
					m_DST_Placed = new array<Object>;
				m_DST_Placed.Insert(pwO);
				Print(string.Format("[DSTest] placew %1 at %2 water=%3 box %4..%5", pwArgs[1], pwP, pwW, pwB[0], pwB[1]));
			}
			else
				Print("[DSTest] placew failed " + pwArgs[1]);
			return true;
		}
		// lodr x0 z0 x1 z1 n: along a line, how far a terrain drawn on a coarser grid (2, 4, 8, 16 terrain cells,
		// both diagonals) would lie above the real terrain
		if (cmd.IndexOf("lodr ") == 0)
		{
			TStringArray lrArgs = new TStringArray;
			cmd.Split(" ", lrArgs);
			float lrX0 = lrArgs[1].ToFloat();
			float lrZ0 = lrArgs[2].ToFloat();
			float lrX1 = lrArgs[3].ToFloat();
			float lrZ1 = lrArgs[4].ToFloat();
			int lrN = lrArgs[5].ToInt();
			array<int> lrF = {2, 4, 8, 16};
			foreach (int lrf : lrF)
			{
				float lrS = 7.5 * lrf;
				string lrOut = "";
				float lrMax = -100;
				for (int lrI = 0; lrI <= lrN; lrI++)
				{
					float lrT = lrI / (lrN * 1.0);
					float lrX = lrX0 + (lrX1 - lrX0) * lrT;
					float lrZ = lrZ0 + (lrZ1 - lrZ0) * lrT;
					float lrCX = Math.Floor(lrX / lrS) * lrS;
					float lrCZ = Math.Floor(lrZ / lrS) * lrS;
					float lrU = (lrX - lrCX) / lrS;
					float lrV = (lrZ - lrCZ) / lrS;
					float lrH00 = GetGame().SurfaceY(lrCX, lrCZ);
					float lrH10 = GetGame().SurfaceY(lrCX + lrS, lrCZ);
					float lrH11 = GetGame().SurfaceY(lrCX + lrS, lrCZ + lrS);
					float lrH01 = GetGame().SurfaceY(lrCX, lrCZ + lrS);
					float lrA;
					if (lrU >= lrV)
						lrA = lrH00 + (lrH10 - lrH00) * lrU + (lrH11 - lrH10) * lrV;
					else
						lrA = lrH00 + (lrH11 - lrH01) * lrU + (lrH01 - lrH00) * lrV;
					float lrB;
					if (lrU + lrV <= 1.0)
						lrB = lrH00 + (lrH10 - lrH00) * lrU + (lrH01 - lrH00) * lrV;
					else
						lrB = lrH11 + (lrH11 - lrH01) * (lrU - 1.0) + (lrH11 - lrH10) * (lrV - 1.0);
					float lrG = GetGame().SurfaceY(lrX, lrZ);
					float lrD = Math.Max(lrA, lrB) - lrG;
					lrMax = Math.Max(lrMax, lrD);
					lrOut += " " + (Math.Round(lrD * 100.0) / 100.0).ToString();
				}
				Print(string.Format("[DSTest] lodr f=%1 max=%2:", lrf, lrMax) + lrOut);
			}
			return true;
		}
		return false;
	}

	//! test harness commands of the release polish (kept out of OnUpdate, which is at the instruction limit)
	protected bool DST_Extra(string cmd)
	{
		// roadobj R step: which objects carry the walkable surfaces up to 0.8 m above the terrain around the camera,
		// with their count, mean and largest height ("road" = no object: the road network)
		if (cmd.IndexOf("roadobj ") == 0)
		{
			TStringArray rdoArgs = new TStringArray;
			cmd.Split(" ", rdoArgs);
			float rdoR = rdoArgs[1].ToFloat();
			float rdoStep = rdoArgs[2].ToFloat();
			string rdoFilter = "";
			if (rdoArgs.Count() >= 4)
				rdoFilter = rdoArgs[3];
			int rdoShown = 0;
			vector rdoC = GetGame().GetCurrentCameraPosition();
			int rdoN = Math.Ceil(rdoR / rdoStep);
			map<string, int> rdoCount = new map<string, int>;
			map<string, float> rdoSum = new map<string, float>;
			map<string, float> rdoMax = new map<string, float>;
			for (int rdoI = -rdoN; rdoI <= rdoN; rdoI++)
			{
				for (int rdoJ = -rdoN; rdoJ <= rdoN; rdoJ++)
				{
					float rdoX = rdoC[0] + rdoI * rdoStep;
					float rdoZ = rdoC[2] + rdoJ * rdoStep;
					float rdoT = GetGame().SurfaceY(rdoX, rdoZ);
					float rdoY = GetGame().SurfaceRoadY3D(rdoX, rdoT + 0.8, rdoZ, RoadSurfaceDetection.UNDER);
					float rdoD = rdoY - rdoT;
					if (rdoD < 0.002 || rdoD > 0.8)
						continue;
					string rdoKey = "road";
					RaycastRVParams rdoRp = new RaycastRVParams(Vector(rdoX, rdoY + 0.06, rdoZ), Vector(rdoX, rdoY - 0.06, rdoZ), null, 0);
					rdoRp.type = ObjIntersectGeom;
					rdoRp.flags = CollisionFlags.ALLOBJECTS;
					array<ref RaycastRVResult> rdoRes = new array<ref RaycastRVResult>;
					if (DayZPhysics.RaycastRVProxy(rdoRp, rdoRes))
					{
						foreach (RaycastRVResult rdoHit : rdoRes)
						{
							Object rdoObj = rdoHit.obj;
							if (rdoHit.parent)
								rdoObj = rdoHit.parent;
							if (!rdoObj)
								continue;
							string rdoShape = rdoObj.GetShapeName();
							rdoShape.ToLower();
							if (rdoShape.IndexOf("seasonz") >= 0)
								continue;
							rdoKey = rdoShape;
							break;
						}
					}
					string rdoBand = " >0.35";
					if (rdoD <= 0.1)
						rdoBand = " <=0.1";
					else if (rdoD <= 0.35)
						rdoBand = " 0.1-0.35";
					rdoKey = rdoKey + rdoBand;
					if (rdoFilter != "" && rdoKey.IndexOf(rdoFilter) >= 0 && rdoShown < 16)
					{
						rdoShown++;
						Print(string.Format("[DSTest] roadobj at %1 %2 +%3 %4", rdoX, rdoZ, rdoD, rdoKey));
					}
					rdoCount.Set(rdoKey, rdoCount.Get(rdoKey) + 1);
					rdoSum.Set(rdoKey, rdoSum.Get(rdoKey) + rdoD);
					rdoMax.Set(rdoKey, Math.Max(rdoMax.Get(rdoKey), rdoD));
				}
			}
			Print("[DSTest] roadobj r=" + rdoR.ToString() + " kinds=" + rdoCount.Count().ToString());
			for (int rdoK = 0; rdoK < rdoCount.Count(); rdoK++)
			{
				string rdoName = rdoCount.GetKey(rdoK);
				int rdoNum = rdoCount.GetElement(rdoK);
				Print(string.Format("[DSTest] roadobj %1 x%2 avg=%3 max=%4", rdoName, rdoNum, rdoSum.Get(rdoName) / rdoNum, rdoMax.Get(rdoName)));
			}
			Print("[DSTest] roadobj end");
			return true;
		}
		// roadprobe v / roadwide 0|1: the road rule of the snow cover (v <= 0: the default); the cover is rebuilt
		if (cmd.IndexOf("roadprobe ") == 0 || cmd.IndexOf("roadwide ") == 0)
		{
			TStringArray rpbArgs = new TStringArray;
			cmd.Split(" ", rpbArgs);
			if (rpbArgs[0] == "roadprobe")
				SZ_State.s_DebugRoadProbe = rpbArgs[1].ToFloat();
			else
				SZ_State.s_DebugRoadWide = rpbArgs[1].ToInt();
			Print(string.Format("[DSTest] road probe=%1 wide=%2", SZ_State.s_DebugRoadProbe, SZ_State.s_DebugRoadWide));
			return true;
		}
		// roofmodels: snow pieces per model near the camera, the most first
		if (cmd.IndexOf("roofmodels") == 0)
		{
			if (m_SZ_Client && m_SZ_Client.GetRoofs())
				m_SZ_Client.GetRoofs().DebugModels(30);
			Print("[DSTest] roofmodel end");
			return true;
		}
		// cutat x z r: the grass cutters within r metres of a point, one per line
		// scaleshape name x z r s: sets the scale of the map objects whose model name contains name within r metres
		// (centre distance) of a point (s = 0.001 hides, 1 shows)
		if (cmd.IndexOf("scaleshape ") == 0)
		{
			TStringArray ssArgs = new TStringArray;
			cmd.Split(" ", ssArgs);
			string ssName = ssArgs[1];
			float ssX = ssArgs[2].ToFloat();
			float ssZ = ssArgs[3].ToFloat();
			float ssR = ssArgs[4].ToFloat();
			float ssS = ssArgs[5].ToFloat();
			array<Object> ssObjs = new array<Object>;
			GetGame().GetObjectsAtPosition(Vector(ssX, GetGame().SurfaceY(ssX, ssZ), ssZ), ssR, ssObjs, null);
			int ssN = 0;
			foreach (Object ssO : ssObjs)
			{
				if (!ssO)
					continue;
				string ssShape = ssO.GetShapeName();
				ssShape.ToLower();
				if (ssShape.IndexOf(ssName) < 0 || ssShape.IndexOf("seasonz") >= 0)
					continue;
				ssO.SetScale(ssS);
				ssO.Update();
				ssN++;
				Print(string.Format("[DSTest] scaleshape %1 at %2 -> %3", ssShape, ssO.GetPosition(), ssS));
			}
			Print("[DSTest] scaleshape end count=" + ssN.ToString());
			return true;
		}
		// objbench n: times creating n roof snow pieces in front of the camera, moving them and deleting them (ticks)
		if (cmd.IndexOf("objbench ") == 0)
		{
			TStringArray obArgs = new TStringArray;
			cmd.Split(" ", obArgs);
			int obN = obArgs[1].ToInt();
			vector obC = GetGame().GetCurrentCameraPosition() + GetGame().GetCurrentCameraDirection() * 20.0;
			array<Object> obObjs = new array<Object>;
			int obT0 = TickCount(0);
			for (int obI = 0; obI < obN; obI++)
			{
				int obRow = obI / 20;
				int obCol = obI % 20;
				vector obP = obC + Vector(obCol * 0.5, 0, obRow * 0.5);
				Object obO = GetGame().CreateStaticObjectUsingP3D("SeasonZ\\data\\snow\\szr_c00_s4.p3d", obP, "0 0 0", 1.0, true);
				obObjs.Insert(obO);
			}
			int obT1 = TickCount(0);
			foreach (Object obM : obObjs)
			{
				if (!obM)
					continue;
				vector obMat[4];
				obM.GetTransform(obMat);
				obMat[0] = obMat[0] * 0.9;
				obMat[3] = obMat[3] + "0 0.1 0";
				obM.SetTransform(obMat);
			}
			int obT2 = TickCount(0);
			foreach (Object obD : obObjs)
			{
				if (obD)
					GetGame().ObjectDelete(obD);
			}
			int obT3 = TickCount(0);
			array<Object> obG = new array<Object>;
			for (int obJ = 0; obJ < obN; obJ++)
			{
				int obRow2 = obJ / 20;
				int obCol2 = obJ % 20;
				vector obQ = obC + Vector(obCol2 * 0.5, 2.0, obRow2 * 0.5);
				obG.Insert(GetGame().CreateStaticObjectUsingP3D("SeasonZ\\data\\snow\\szk_a00_s4.p3d", obQ, "0 0 0", 1.0, true));
			}
			int obT4 = TickCount(0);
			foreach (Object obGD : obG)
			{
				if (obGD)
					GetGame().ObjectDelete(obGD);
			}
			float obTps = SZ_RoofSnow.DebugTicksPerSec();
			if (obTps <= 0)
				obTps = 1;
			float obK = 1000.0 / obTps / Math.Max(1, obN);
			Print(string.Format("[DSTest] objbench n=%1 ms per object: create=%2 move=%3 delete=%4 groundcreate=%5 (ticks/s %6)", obN, (obT1 - obT0) * obK, (obT2 - obT1) * obK, (obT3 - obT2) * obK, (obT4 - obT3) * obK, obTps));
			return true;
		}
		// roofperf: the longest roof snow frame and roof build since the last call (ms), then resets them
		// partperf: the longest update of each client part since the last call (ms), then resets them
		if (cmd.IndexOf("partperf") == 0)
		{
			if (SZ_State.s_StatPartMax)
			{
				float ppK = 1000.0 / Math.Max(1.0, SZ_RoofSnow.DebugTicksPerSec());
				array<int> ppM = SZ_State.s_StatPartMax;
				Print(string.Format("[DSTest] partperf max ms: cover %1 trees %2 roofs %3 grass %4 ice %5 prints %6; %7 of %8 frames over 8 ms", ppM[0] * ppK, ppM[1] * ppK, ppM[2] * ppK, ppM[3] * ppK, ppM[4] * ppK, ppM[5] * ppK, SZ_State.s_StatPartSlow, SZ_State.s_StatPartFrames));
				array<int> ppS = SZ_State.s_StatPartSum;
				float ppA = ppK / Math.Max(1, SZ_State.s_StatPartFrames);
				Print(string.Format("[DSTest] partperf mean ms per frame: cover %1 trees %2 roofs %3 grass %4 ice %5 prints %6", ppS[0] * ppA, ppS[1] * ppA, ppS[2] * ppA, ppS[3] * ppA, ppS[4] * ppA, ppS[5] * ppA));
				for (int ppI = 0; ppI < 6; ppI++)
				{
					ppM[ppI] = 0;
					ppS[ppI] = 0;
				}
			}
			if (SZ_State.s_StatCoverMax)
			{
				float pcK = 1000.0 / Math.Max(1.0, SZ_RoofSnow.DebugTicksPerSec());
				array<int> pcM = SZ_State.s_StatCoverMax;
				Print(string.Format("[DSTest] coverperf max ms: layout %1 near %2 main %3 retired %4 one cell %5 (create %6 stage %7)", pcM[0] * pcK, pcM[1] * pcK, pcM[2] * pcK, pcM[3] * pcK, pcM[4] * pcK, pcM[5] * pcK, pcM[6] * pcK));
				for (int pcI = 0; pcI < 7; pcI++)
					pcM[pcI] = 0;
				Print("[DSTest] coverperf worst cell: " + SZ_State.s_StatCoverWorst);
			}
			if (SZ_State.s_StatTreeMax)
			{
				float ptK = 1000.0 / Math.Max(1.0, SZ_RoofSnow.DebugTicksPerSec());
				array<int> ptM = SZ_State.s_StatTreeMax;
				Print(string.Format("[DSTest] treeperf max ms: reach %1 anchor %2 restore %3 near %4 far %5 one scan %6", ptM[0] * ptK, ptM[1] * ptK, ptM[2] * ptK, ptM[3] * ptK, ptM[4] * ptK, ptM[5] * ptK));
				for (int ptI = 0; ptI < 6; ptI++)
					ptM[ptI] = 0;
			}
			SZ_State.s_StatPartSlow = 0;
			SZ_State.s_StatPartFrames = 0;
			return true;
		}
		// placebench n: the parts of placing n roof pieces, timed
		if (cmd.IndexOf("placebench ") == 0)
		{
			TStringArray pbArgs = new TStringArray;
			cmd.Split(" ", pbArgs);
			if (m_SZ_Client && m_SZ_Client.GetRoofs())
				Print("[DSTest] placebench " + m_SZ_Client.GetRoofs().DebugPlaceBench(pbArgs[1].ToInt()));
			return true;
		}
		// roofperf: the longest roof snow frame and roof build since the last call (ms), then resets them
		// raybench x z n: times n vertical rays at a point: 30 m long (sorted, all objects) and 0.6 m long
		if (cmd.IndexOf("raybench ") == 0)
		{
			TStringArray rbArgs = new TStringArray;
			cmd.Split(" ", rbArgs);
			float rbX = rbArgs[1].ToFloat();
			float rbZ = rbArgs[2].ToFloat();
			int rbN = rbArgs[3].ToInt();
			float rbG = GetGame().SurfaceY(rbX, rbZ);
			int rbHits = 0;
			int rbT0 = TickCount(0);
			for (int rbI = 0; rbI < rbN; rbI++)
			{
				float rbOff = rbI * 0.01;
				RaycastRVParams rbP = new RaycastRVParams(Vector(rbX + rbOff, rbG + 30.0, rbZ), Vector(rbX + rbOff, rbG - 0.5, rbZ), null, 0);
				rbP.type = ObjIntersectFire;
				rbP.flags = CollisionFlags.ALLOBJECTS;
				rbP.sorted = true;
				array<ref RaycastRVResult> rbR = new array<ref RaycastRVResult>;
				if (DayZPhysics.RaycastRVProxy(rbP, rbR))
					rbHits += rbR.Count();
			}
			int rbT1 = TickCount(0);
			int rbHits2 = 0;
			for (int rbJ = 0; rbJ < rbN; rbJ++)
			{
				float rbOff2 = rbJ * 0.01;
				RaycastRVParams rbQ = new RaycastRVParams(Vector(rbX + rbOff2, rbG + 9.3, rbZ), Vector(rbX + rbOff2, rbG + 8.7, rbZ), null, 0);
				rbQ.type = ObjIntersectFire;
				rbQ.flags = CollisionFlags.ALLOBJECTS;
				rbQ.sorted = false;
				array<ref RaycastRVResult> rbS = new array<ref RaycastRVResult>;
				if (DayZPhysics.RaycastRVProxy(rbQ, rbS))
					rbHits2 += rbS.Count();
			}
			int rbT2 = TickCount(0);
			int rbHits3 = 0;
			for (int rbK = 0; rbK < rbN; rbK++)
			{
				float rbOff3 = rbK * 0.01;
				vector rbHitPos;
				vector rbHitNorm;
				int rbComp;
				if (DayZPhysics.RaycastRV(Vector(rbX + rbOff3, rbG + 30.0, rbZ), Vector(rbX + rbOff3, rbG - 0.5, rbZ), rbHitPos, rbHitNorm, rbComp, null, null, null, false, false, ObjIntersectFire, 0.0))
					rbHits3++;
			}
			int rbT3 = TickCount(0);
			float rbTps = SZ_RoofSnow.DebugTicksPerSec();
			if (rbTps <= 0)
				rbTps = 1;
			float rbK2 = 1000.0 / rbTps / Math.Max(1, rbN);
			Print(string.Format("[DSTest] raybench n=%1 ms per ray: long %2 (hits %3) short %4 (hits %5) single %6 (hits %7)", rbN, (rbT1 - rbT0) * rbK2, rbHits, (rbT2 - rbT1) * rbK2, rbHits2, (rbT3 - rbT2) * rbK2, rbHits3));
			return true;
		}
		// roofperf: the longest roof snow frame and roof build since the last call (ms), then resets them
		if (cmd.IndexOf("roofperf") == 0)
		{
			float rpAvg = 0;
			if (SZ_State.s_StatRoofBuilds > 0)
				rpAvg = SZ_State.s_StatRoofBuildSum / SZ_State.s_StatRoofBuilds;
			Print(string.Format("[DSTest] roofperf frame max %1 ms (%2 of %3 frames over 8 ms), build max %4 ms, builds %5 avg %6 ms", SZ_State.s_StatRoofFrameMax, SZ_State.s_StatRoofSlow, SZ_State.s_StatRoofFrames, SZ_State.s_StatRoofBuildMax, SZ_State.s_StatRoofBuilds, rpAvg));
			Print("[DSTest] roofperf slowest " + SZ_State.s_StatRoofBuildWho);
			Print(string.Format("[DSTest] roofperf place max %1 ms (%2)", SZ_State.s_StatRoofPlaceMax, SZ_State.s_StatRoofPlaceWho));
			if (SZ_State.s_StatRoofTicks)
			{
				float rpK = 1000.0 / Math.Max(1.0, SZ_RoofSnow.DebugTicksPerSec());
				array<int> rpT = SZ_State.s_StatRoofTicks;
				Print(string.Format("[DSTest] roofperf ms total %1: trash %2 movables %3 scans %4 rays+polygons %5 placing %6", rpT[5] * rpK, rpT[0] * rpK, rpT[1] * rpK, rpT[2] * rpK, rpT[3] * rpK, rpT[4] * rpK));
				for (int rpI = 0; rpI < 6; rpI++)
					rpT[rpI] = 0;
			}
			SZ_State.s_StatRoofFrames = 0;
			SZ_State.s_StatRoofSlow = 0;
			SZ_State.s_StatRoofFrameMax = 0;
			SZ_State.s_StatRoofBuildMax = 0;
			SZ_State.s_StatRoofBuildWho = "";
			SZ_State.s_StatRoofPlaceMax = 0;
			SZ_State.s_StatRoofPlaceWho = "";
			SZ_State.s_StatRoofBuildSum = 0;
			SZ_State.s_StatRoofBuilds = 0;
			return true;
		}
		// wallradius v: how far walls, fences and wrecks carry snow (v <= 0: the default)
		if (cmd.IndexOf("wallradius ") == 0)
		{
			TStringArray wrArgs = new TStringArray;
			cmd.Split(" ", wrArgs);
			SZ_State.s_DebugWallRadius = wrArgs[1].ToFloat();
			Print("[DSTest] wall radius " + SZ_State.s_DebugWallRadius.ToString());
			return true;
		}
		if (cmd.IndexOf("cutat ") == 0)
		{
			TStringArray ctArgs = new TStringArray;
			cmd.Split(" ", ctArgs);
			float ctX = ctArgs[1].ToFloat();
			float ctZ = ctArgs[2].ToFloat();
			float ctR = ctArgs[3].ToFloat();
			array<Object> ctObjs = new array<Object>;
			GetGame().GetObjectsAtPosition(Vector(ctX, GetGame().SurfaceY(ctX, ctZ), ctZ), ctR, ctObjs, null);
			int ctN = 0;
			foreach (Object ctO : ctObjs)
			{
				if (!ctO)
					continue;
				string ctShape = ctO.GetShapeName();
				ctShape.ToLower();
				if (ctShape.IndexOf("clutter_cutter") < 0)
					continue;
				ctN++;
				vector ctP = ctO.GetPosition();
				Print(string.Format("[DSTest] cutat %1 at %2 above=%3 type=%4", ctShape, ctP, ctP[1] - GetGame().SurfaceY(ctP[0], ctP[2]), ctO.GetType()));
			}
			Print("[DSTest] cutat end count=" + ctN.ToString());
			return true;
		}
		// capdebug x z: samples the structure nearest to a point again and logs how its surfaces become polygons
		if (cmd.IndexOf("capdebug ") == 0)
		{
			TStringArray cdArgs = new TStringArray;
			cmd.Split(" ", cdArgs);
			if (cdArgs.Count() >= 3 && m_SZ_Client && m_SZ_Client.GetRoofs())
				Print("[DSTest] capdebug " + m_SZ_Client.GetRoofs().DebugCaps(cdArgs[1].ToFloat(), cdArgs[2].ToFloat()));
			return true;
		}
		// roofoff 0|1: no roof snow at all (cost measurements)
		// edgeblock n: size of the cell blocks roof polygon edges are cut in; the roofs are sampled again
		if (cmd.IndexOf("edgeblock ") == 0)
		{
			TStringArray ebArgs = new TStringArray;
			cmd.Split(" ", ebArgs);
			SZ_State.s_DebugEdgeBlock = ebArgs[1].ToInt();
			if (m_SZ_Client && m_SZ_Client.GetRoofs())
				m_SZ_Client.GetRoofs().DebugReapply(true);
			Print("[DSTest] edge block " + SZ_State.s_DebugEdgeBlock.ToString());
			return true;
		}
		if (cmd.IndexOf("roofoff ") == 0)
		{
			SZ_State.s_DebugRoofOff = cmd.IndexOf("roofoff 1") == 0;
			Print("[DSTest] roofs off=" + SZ_State.s_DebugRoofOff.ToString());
			return true;
		}
		// roofcaps n: flat tops as single polygons (0 off, 1 small structures, 2 all); the roofs are sampled again
		if (cmd.IndexOf("roofcaps ") == 0)
		{
			TStringArray rcpArgs = new TStringArray;
			cmd.Split(" ", rcpArgs);
			SZ_State.s_DebugRoofCaps = rcpArgs[1].ToInt();
			if (m_SZ_Client && m_SZ_Client.GetRoofs())
				m_SZ_Client.GetRoofs().DebugReapply(true);
			Print("[DSTest] roof caps " + SZ_State.s_DebugRoofCaps.ToString());
			return true;
		}

		return false;
	}

	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);
		if (!GetGame().GetPlayer())
			return;
		if (m_DST_ActWait > 0)
		{
			m_DST_ActWait -= timeslice;
			if (m_DST_ActWait <= 0)
			{
				PlayerBase actP = PlayerBase.Cast(GetGame().GetPlayer());
				ActionManagerClient actM = ActionManagerClient.Cast(actP.GetActionManager());
				string actTarget = "none";
				string actPrimary = "none";
				string actSecondary = "none";
				if (actM)
				{
					ActionTarget actT = actM.FindActionTarget();
					if (actT && actT.GetObject())
						actTarget = actT.GetObject().GetType() + " " + actT.GetObject().GetShapeName() + " scale " + actT.GetObject().GetScale().ToString();
					if (actM.GetContinuousAction())
						actPrimary = actM.GetContinuousAction().ClassName() + " (" + actM.GetContinuousAction().GetText() + ")";
					if (actM.GetSingleUseAction())
						actSecondary = actM.GetSingleUseAction().ClassName();
				}
				Object actOrig = SZ_TreeSwap.OriginalOf(m_DST_ActRepl);
				Print(string.Format("[DSTest] acttest result: target=%1 | original=%2 | continuous=%3 | single=%4 | in hands=%5", actTarget, actOrig, actPrimary, actSecondary, actP.GetItemInHands()));
				// chop: start the offered continuous action (the server checks and runs it like a held key)
				if (m_DST_ActChop && actM)
				{
					array<ActionBase> chopActs = actM.GetPossibleActions(ContinuousDefaultActionInput);
					string chopNames = "";
					ActionBase chopAct = null;
					if (chopActs)
					{
						foreach (ActionBase ca : chopActs)
						{
							chopNames += " " + ca.ClassName();
							if (!chopAct)
								chopAct = ca;
						}
					}
					Print("[DSTest] acttest: continuous actions offered:" + chopNames);
					if (chopAct)
					{
						ActionTarget chopT = actM.FindActionTarget();
						actM.PerformActionStart(chopAct, chopT, ItemBase.Cast(actP.GetItemInHands()));
						m_DST_ActHold = 40.0;
						Print("[DSTest] acttest: started " + chopAct.ClassName() + " on " + chopT.GetObject().ToString());
					}
				}
			}
		}
		if (m_DST_ActHold > 0)
		{
			m_DST_ActHold -= timeslice;
			PlayerBase holdP = PlayerBase.Cast(GetGame().GetPlayer());
			Object holdOrig = SZ_TreeSwap.OriginalOf(m_DST_ActRepl);
			if (m_DST_ActHold <= 0 || !holdOrig || holdOrig.IsDamageDestroyed())
			{
				m_DST_ActHold = 0;
				ActionManagerClient holdM = ActionManagerClient.Cast(holdP.GetActionManager());
				if (holdM)
					holdM.EndActionInput();
				string destroyed = "gone";
				if (holdOrig)
					destroyed = holdOrig.IsDamageDestroyed().ToString();
				Print(string.Format("[DSTest] acttest chop end: original destroyed=%1 replacement=%2", destroyed, m_DST_ActRepl));
			}
		}
		if (m_DST_PTrack > 0)
		{
			m_DST_PTrack -= timeslice;
			m_DST_PTrackT += timeslice;
			if (m_DST_PTrackT >= 0.25)
			{
				m_DST_PTrackT = 0;
				DayZPlayerImplement pkP = DayZPlayerImplement.Cast(GetGame().GetPlayer());
				vector pkPos = pkP.GetPosition();
				float pkWater;
				SZ_Util.PondWater(pkPos[0], pkPos[2], pkWater);
				float pkRoad = GetGame().SurfaceRoadY3D(pkPos[0], pkPos[1] + 2.0, pkPos[2], RoadSurfaceDetection.UNDER);
				vector pkWl = HumanCommandSwim.WaterLevelCheck(pkP, pkPos);
				Print(string.Format("[DSTest] ptrack %1 cmd=%2 aboveWater=%3 road=%4 wl=%5", pkPos, pkP.GetCurrentCommandID(), pkPos[1] - pkWater, pkRoad, pkWl));
			}
		}		if (m_DST_FlyT >= 0 && m_DST_Cam)
		{
			m_DST_FlyT += timeslice / m_DST_FlySecs;
			float flyF = Math.Min(m_DST_FlyT, 1.0);
			vector flyP = m_DST_FlyA + (m_DST_FlyB - m_DST_FlyA) * flyF;
			flyP[1] = GetGame().SurfaceY(flyP[0], flyP[2]) + m_DST_FlyH;
			vector flyDir = (m_DST_FlyB - m_DST_FlyA).Normalized();
			vector flyT = flyP + flyDir * 400.0;
			flyT[1] = GetGame().SurfaceY(flyT[0], flyT[2]) + 2.0;
			m_DST_Cam.SetPosition(flyP);
			m_DST_Cam.LookAt(flyT);
			if (m_DST_FlyT >= 1.0)
			{
				m_DST_FlyT = -1;
				Print("[DSTest] fly done");
			}
		}
		if (m_DST_Scan)
			m_DST_Scan.Step(timeslice);
		DST_Steps(timeslice);
		if (m_DST_SettleTag != "")
		{
			m_DST_SettleT += timeslice;
			int settleSum = SZ_State.s_StatCarpet * 3 + SZ_State.s_StatRoofs * 7 + SZ_State.s_StatCutters * 11 + SZ_State.s_StatRays;
			if (settleSum != m_DST_SettleSum || SZ_State.s_StatRoofBusy)
			{
				m_DST_SettleSum = settleSum;
				m_DST_SettleStill = 0;
			}
			else
				m_DST_SettleStill += timeslice;
			// still for 2.5 s (the cover and the roofs build in portions with short pauses between them); a view that
			// never settles is reported as such, so a screenshot taken anyway is known to be early
			if (m_DST_SettleT >= 3.0 && m_DST_SettleStill >= 2.5)
			{
				Print(string.Format("[DSTest] settled %1 after %2", m_DST_SettleTag, m_DST_SettleT));
				m_DST_SettleTag = "";
			}
			else if (m_DST_SettleT >= 60.0)
			{
				Print(string.Format("[DSTest] settled %1 after %2 TIMEOUT", m_DST_SettleTag, m_DST_SettleT));
				m_DST_SettleTag = "";
			}
		}
		if (m_DST_NearTag != "" && m_SZ_Client && m_SZ_Client.GetRoofs() && m_SZ_Client.GetCarpet())
		{
			m_DST_NearT += timeslice;
			array<SZ_RoofBuilding> nrReady = new array<SZ_RoofBuilding>;
			array<SZ_RoofBuilding> nrWait = new array<SZ_RoofBuilding>;
			int nrTiles;
			m_SZ_Client.GetRoofs().DebugReady(m_DST_NearPos, 40.0, nrReady, nrWait, nrTiles);
			int nrBuilt = 0;
			for (int nri = 0; nri < 5; nri++)
			{
				float nrx = m_DST_NearPos[0];
				float nrz = m_DST_NearPos[2];
				if (nri == 1)
					nrx += 20.0;
				else if (nri == 2)
					nrx -= 20.0;
				else if (nri == 3)
					nrz += 20.0;
				else if (nri == 4)
					nrz -= 20.0;
				if (m_SZ_Client.GetCarpet().DebugCell0(nrx, nrz) >= 0)
					nrBuilt++;
			}
			bool nrDone = nrWait.Count() == 0 && nrTiles == 0 && nrBuilt >= 5;
			if ((nrDone && m_DST_NearT >= 2.0) || m_DST_NearT >= 45.0)
			{
				string nrNote = "";
				if (!nrDone)
					nrNote = " TIMEOUT";
				Print(string.Format("[DSTest] near %1 ready after %2 waiting=%3 tiles=%4 cover=%5%6", m_DST_NearTag, m_DST_NearT, nrWait.Count(), nrTiles, nrBuilt, nrNote));
				m_DST_NearTag = "";
			}
		}
		if (m_DST_PondMap && !m_DST_PondMap.Step())
			m_DST_PondMap = null;
		if (m_DST_WalkLeft > 0)
		{
			HumanInputController hic = GetGame().GetPlayer().GetInputController();
			m_DST_WalkLeft -= timeslice;
			if (m_DST_WalkLeft > 0)
			{
				hic.OverrideMovementSpeed(HumanInputControllerOverrideType.ENABLED, m_DST_WalkSpeed);
				hic.OverrideMovementAngle(HumanInputControllerOverrideType.ENABLED, 0);
			}
			else
			{
				hic.OverrideMovementSpeed(HumanInputControllerOverrideType.DISABLED, 0);
				hic.OverrideMovementAngle(HumanInputControllerOverrideType.DISABLED, 0);
			}
		}
		if (!m_DST_Checked)
		{
			m_DST_Checked = true;
			DayZPlayer dp = DayZPlayer.Cast(GetGame().GetPlayer());
			DayZPlayerTypeStepSoundLookupTable table = dp.GetDayZPlayerType().GetStepSoundLookupTable();
			string ids = "";
			for (int ev = 0; ev < 120; ev++)
			{
				SoundObjectBuilder sbSnow = table.GetSoundBuilder(ev, DayZPlayerConstants.MOVEMENTIDX_RUN, ("sakhal_snow").Hash(), AnimBootsType.Boots);
				SoundObjectBuilder sbGrass = table.GetSoundBuilder(ev, DayZPlayerConstants.MOVEMENTIDX_RUN, ("cp_grass").Hash(), AnimBootsType.Boots);
				if (sbSnow || sbGrass)
					ids += string.Format(" %1:%2/%3", ev, sbSnow != null, sbGrass != null);
			}
			Print("[DSTest] step builders (event:snow/grass):" + ids);
			Print("[DSTest] step particle sakhal_snow=" + Surface.GetStepsParticleID("sakhal_snow").ToString() + " cp_grass=" + Surface.GetStepsParticleID("cp_grass").ToString());
		}
		if (m_DST_FlatMode > 0)
		{
			vector pp = GetGame().GetPlayer().GetPosition();
			if (m_DST_FlatMode == 1)
				GetGame().GetWorld().FlattenGrassSphere(pp[0], pp[2], m_DST_FlatR, m_DST_FlatC, m_DST_FlatT, m_DST_FlatH);
			else
				GetGame().GetWorld().FlattenGrassBox(pp[0], pp[2], m_DST_FlatR, 0, m_DST_FlatC, m_DST_FlatT, m_DST_FlatH);
		}
		m_DST_FpsTime += timeslice;
		m_DST_Frames++;
		if (m_DST_FpsTime >= 5.0)
		{
			float fps = m_DST_Frames / m_DST_FpsTime;
			DayZPlayerImplement dpi = DayZPlayerImplement.Cast(GetGame().GetPlayer());
			string surf = dpi.GetSurfaceType(SurfaceAnimationBone.LeftBackLimb);
			string fpsTrees = string.Format("%1/%2@%3 lost=%4", SZ_State.s_StatTrees, SZ_State.s_StatTreesKnown, Math.Round(SZ_State.s_StatTreeReach), SZ_State.s_StatTreesLost);
			Print(string.Format("[DSTest] fps %1 carpet=%2 cutters=%3 trees=%4 roofs=%5 rays=%6 prints=%7 surface=%8 fog=%9", fps, SZ_State.s_StatCarpet, SZ_State.s_StatCutters, fpsTrees, SZ_State.s_StatRoofs, SZ_State.s_StatRays, SZ_Footprints.GetCount(), surf, GetGame().GetWeather().GetFog().GetActual()));
			vector cpPos = dpi.GetPosition();
			float cpWater;
			bool cpPond = SZ_Util.PondWater(cpPos[0], cpPos[2], cpWater);
			float cpRoad = GetGame().SurfaceRoadY3D(cpPos[0], cpPos[1] + 2.0, cpPos[2], RoadSurfaceDetection.UNDER);
			vector cpWl = HumanCommandSwim.WaterLevelCheck(dpi, cpPos);
			int cpTracks = SZ_TyreTracks.GetCount();
			Print(string.Format("[DSTest] client player %1 cmd=%2 swimming=%3 aboveWater=%4 road=%5 waterLevelCheck=%6 ice=%7 tracks=%8", cpPos, dpi.GetCurrentCommandID(), dpi.IsSwimming(), cpPos[1] - cpWater, cpRoad, cpWl, SZ_State.s_StatIce, cpTracks));
			m_DST_FpsTime = 0;
			m_DST_Frames = 0;
		}
		m_DST_Poll += timeslice;
		if (m_DST_Poll < 0.15)
			return;
		m_DST_Poll = 0;

		string cmd = DST_File.ReadLine("$profile:dstest_camera.txt");
		if (cmd == "" || cmd == m_DST_Last)
			return;
		m_DST_Last = cmd;
		if (DST_Extra(cmd))
			return;
		if (DST_Extra2(cmd))
			return;

		if (cmd == "player")
		{
			if (m_DST_Cam)
				m_DST_Cam.SetActive(false);
			Print("[DSTest] camera back to player");
			return;
		}
		if (cmd.IndexOf("normals ") == 0)
		{
			SZ_State.s_DebugNormalMode = cmd.Substring(8, cmd.Length() - 8).ToInt();
			Print("[DSTest] carpet normal mode " + SZ_State.s_DebugNormalMode.ToString());
			return;
		}
		if (cmd.IndexOf("where") == 0)
		{
			vector whP = GetGame().GetPlayer().GetPosition();
			vector whC = GetGame().GetCurrentCameraPosition();
			vector whD = GetGame().GetCurrentCameraDirection();
			Print(string.Format("[DSTest] where player=%1 camera=%2 dir=%3", whP, whC, whD));
			return;
		}
		// wheels: the vehicles within 60 m of the camera, their speed and the ground contact this client sees per wheel
		if (cmd.IndexOf("wheels") == 0)
		{
			array<Object> wsObjs = new array<Object>;
			GetGame().GetObjectsAtPosition(GetGame().GetCurrentCameraPosition(), 60.0, wsObjs, null);
			foreach (Object wsO : wsObjs)
			{
				CarScript wsCar = CarScript.Cast(wsO);
				if (!wsCar)
					continue;
				vector wsV = GetVelocity(wsCar);
				float wsSpeed = wsV.Length();
				int wsN = wsCar.WheelCount();
				string wsS = string.Format("[DSTest] wheels %1 at %2 speed=%3 n=%4", wsCar.GetType(), wsCar.GetPosition(), wsSpeed, wsN);
				for (int wsI = 0; wsI < wsN; wsI++)
				{
					bool wsC = wsCar.WheelHasContact(wsI);
					vector wsP = wsCar.WheelGetContactPosition(wsI);
					vector wsL = wsCar.WorldToModel(wsP);
					wsS += string.Format(" [%1 c=%2 local=%3]", wsI, wsC, wsL);
				}
				Print(wsS);
			}
			int wsTracks = SZ_TyreTracks.GetCount();
			Print("[DSTest] wheels end tracks=" + wsTracks.ToString());
			return;
		}
		if (cmd.IndexOf("holes") == 0)
		{
			if (m_SZ_Client && m_SZ_Client.GetCarpet())
				Print("[DSTest] holes " + m_SZ_Client.GetCarpet().DebugHoles(25));
			return;
		}
		// carpetlevels: objects of the snow cover per level and the split cells of level 0 by distance
		if (cmd.IndexOf("carpetlevels") == 0)
		{
			if (m_SZ_Client && m_SZ_Client.GetCarpet())
				Print("[DSTest] carpetlevels" + m_SZ_Client.GetCarpet().DebugLevels());
			return;
		}
		// roofnear x z r: the structures the roof snow keeps near a point, and why the other objects there are not
		if (cmd.IndexOf("roofnear ") == 0)
		{
			TStringArray rnArgs = new TStringArray;
			cmd.Split(" ", rnArgs);
			if (m_SZ_Client && m_SZ_Client.GetRoofs() && rnArgs.Count() >= 4)
				Print("[DSTest] roofnear" + m_SZ_Client.GetRoofs().DebugNear(rnArgs[1].ToFloat(), rnArgs[2].ToFloat(), rnArgs[3].ToFloat()));
			return;
		}
		// prof x0 z0 x1 z1 n: height of the built cover above the terrain along a line
		if (cmd.IndexOf("prof ") == 0)
		{
			TStringArray pf = new TStringArray;
			cmd.Split(" ", pf);
			if (pf.Count() >= 6 && m_SZ_Client && m_SZ_Client.GetCarpet())
			{
				float pfX0 = pf[1].ToFloat();
				float pfZ0 = pf[2].ToFloat();
				float pfX1 = pf[3].ToFloat();
				float pfZ1 = pf[4].ToFloat();
				int pfN = pf[5].ToInt();
				string pfOut = "";
				for (int pfI = 0; pfI <= pfN; pfI++)
				{
					float pfF = pfI / (pfN * 1.0);
					float pfX = pfX0 + (pfX1 - pfX0) * pfF;
					float pfZ = pfZ0 + (pfZ1 - pfZ0) * pfF;
					int pfLv;
					float pfH = m_SZ_Client.GetCarpet().DebugCoverAt(pfX, pfZ, pfLv);
					pfOut += string.Format(" %1:%2:%3", Math.Round(pfF * 1000.0) / 1000.0, pfLv, Math.Round(pfH * 1000.0) / 1000.0);
					if (pfI % 16 == 15)
					{
						Print("[DSTest] prof" + pfOut);
						pfOut = "";
					}
				}
				if (pfOut != "")
					Print("[DSTest] prof" + pfOut);
				Print("[DSTest] prof end");
			}
			return;
		}
		// cellat x z: state of the snow cover cell drawn at a point
		if (cmd.IndexOf("cellat ") == 0)
		{
			TStringArray caArgs = new TStringArray;
			cmd.Split(" ", caArgs);
			if (caArgs.Count() >= 3 && m_SZ_Client && m_SZ_Client.GetCarpet())
				Print("[DSTest] cellat " + caArgs[1] + " " + caArgs[2] + " " + m_SZ_Client.GetCarpet().DebugCellAt(caArgs[1].ToFloat(), caArgs[2].ToFloat()));
			return;
		}
		// objat x z: placed snow cover objects of the level 0 cell at a point
		if (cmd.IndexOf("objat ") == 0)
		{
			TStringArray oaArgs = new TStringArray;
			cmd.Split(" ", oaArgs);
			if (oaArgs.Count() >= 3 && m_SZ_Client && m_SZ_Client.GetCarpet())
				Print("[DSTest] objat " + oaArgs[1] + " " + oaArgs[2] + " " + m_SZ_Client.GetCarpet().DebugObjectsAt(oaArgs[1].ToFloat(), oaArgs[2].ToFloat()));
			return;
		}
		// cellbuild x z: builds the level 0 snow cell at a point once more and prints every decision
		if (cmd.IndexOf("cellbuild ") == 0)
		{
			TStringArray cbArgs = new TStringArray;
			cmd.Split(" ", cbArgs);
			if (cbArgs.Count() >= 3 && m_SZ_Client && m_SZ_Client.GetCarpet())
				Print("[DSTest] cellbuild " + m_SZ_Client.GetCarpet().DebugBuildCell(cbArgs[1].ToFloat(), cbArgs[2].ToFloat()));
			return;
		}
		// allat x z: every built snow cover triangle over a point, current and retired
		if (cmd.IndexOf("allat ") == 0)
		{
			TStringArray alArgs = new TStringArray;
			cmd.Split(" ", alArgs);
			if (alArgs.Count() >= 3 && m_SZ_Client && m_SZ_Client.GetCarpet())
				Print("[DSTest] allat " + alArgs[1] + " " + alArgs[2] + " " + m_SZ_Client.GetCarpet().DebugAllAt(alArgs[1].ToFloat(), alArgs[2].ToFloat()));
			return;
		}
		// ray px py W H: what the harness camera sees at a window pixel (vertical field of view 0.9 rad)
		if (cmd.IndexOf("ray ") == 0 && m_DST_Cam)
		{
			TStringArray rayArgs = new TStringArray;
			cmd.Split(" ", rayArgs);
			float rayPX = rayArgs[1].ToFloat();
			float rayPY = rayArgs[2].ToFloat();
			float rayW = rayArgs[3].ToFloat();
			float rayH = rayArgs[4].ToFloat();
			vector rayM[4];
			m_DST_Cam.GetTransform(rayM);
			float rayTv = Math.Tan(0.45);
			float rayTh = rayTv * rayW / rayH;
			float rayNX = 2.0 * rayPX / rayW - 1.0;
			float rayNY = 1.0 - 2.0 * rayPY / rayH;
			vector rayDir = rayM[2] + rayM[0] * (rayNX * rayTh) + rayM[1] * (rayNY * rayTv);
			rayDir.Normalize();
			vector rayFrom = rayM[3];
			vector rayTo = rayFrom + rayDir * 600.0;
			vector rayHit;
			vector rayNorm;
			int rayComp;
			set<Object> rayObjs = new set<Object>;
			bool rayOk = DayZPhysics.RaycastRV(rayFrom, rayTo, rayHit, rayNorm, rayComp, rayObjs, null, null, false, false, ObjIntersectView, 0.0);
			string rayNames = "";
			for (int rayI = 0; rayI < rayObjs.Count(); rayI++)
			{
				if (rayObjs.Get(rayI))
					rayNames += " " + rayObjs.Get(rayI).GetShapeName();
			}
			// where the ray meets the terrain
			vector rayT = rayFrom;
			for (int rayS = 0; rayS < 6000; rayS++)
			{
				rayT = rayFrom + rayDir * (rayS * 0.1);
				if (rayT[1] <= GetGame().SurfaceY(rayT[0], rayT[2]))
					break;
			}
			Print(string.Format("[DSTest] ray %1 %2 hit=%3 at %4 normal=%5 objects:%6 terrainhit=%7", rayPX, rayPY, rayOk, rayHit, rayNorm, rayNames, rayT));
			return;
		}
		// scr x0 z0 x1 z1 n: screen positions of points on the ground along a line
		if (cmd.IndexOf("scr ") == 0)
		{
			TStringArray scArgs = new TStringArray;
			cmd.Split(" ", scArgs);
			float scX0 = scArgs[1].ToFloat();
			float scZ0 = scArgs[2].ToFloat();
			float scX1 = scArgs[3].ToFloat();
			float scZ1 = scArgs[4].ToFloat();
			int scN = scArgs[5].ToInt();
			string scOut = "";
			for (int scI = 0; scI <= scN; scI++)
			{
				float scF = scI / (scN * 1.0);
				vector scP = Vector(scX0 + (scX1 - scX0) * scF, 0, scZ0 + (scZ1 - scZ0) * scF);
				scP[1] = GetGame().SurfaceY(scP[0], scP[2]) + 0.05;
				vector scS = GetGame().GetScreenPos(scP);
				scOut += string.Format(" (%1,%2)->(%3,%4)", scP[0], scP[2], Math.Round(scS[0]), Math.Round(scS[1]));
			}
			Print("[DSTest] scr" + scOut);
			return;
		}
		// paths R: footpath models around the camera with their ends on screen
		if (cmd.IndexOf("paths ") == 0)
		{
			float paR = cmd.Substring(6, cmd.Length() - 6).ToFloat();
			vector paC = GetGame().GetCurrentCameraPosition();
			array<Object> paObjs = new array<Object>;
			GetGame().GetObjectsAtPosition(paC, paR, paObjs, null);
			foreach (Object paO : paObjs)
			{
				if (!paO || !SZ_TreeSwap.IsPath(paO))
					continue;
				vector paM[4];
				paO.GetTransform(paM);
				vector paMM[2];
				paO.ClippingInfo(paMM);
				vector paA = paO.ModelToWorld(Vector(0, 0, paMM[0][2]));
				vector paB = paO.ModelToWorld(Vector(0, 0, paMM[1][2]));
				vector paSA = GetGame().GetScreenPos(paA);
				vector paSB = GetGame().GetScreenPos(paB);
				Print(string.Format("[DSTest] path %1 pos=%2 dir=%3 box=%4..%5 endA=%6 screen(%7,%8) endB=%9", paO.GetShapeName(), paO.GetPosition(), paO.GetDirection(), paMM[0], paMM[1], paA, Math.Round(paSA[0]), Math.Round(paSA[1]), paB) + string.Format(" screen(%1,%2)", Math.Round(paSB[0]), Math.Round(paSB[1])));
			}
			Print("[DSTest] paths end");
			return;
		}
		if (cmd.IndexOf("carpet") == 0)
		{
			// carpetfar 0|1: the coarser split of the far level 0 cover off/on (cells are rebuilt as they come up)
			if (cmd.IndexOf("carpetfar") == 0)
			{
				SZ_State.s_CarpetFarDetail = cmd.IndexOf("carpetfar 1") == 0;
				Print("[DSTest] carpet far detail=" + SZ_State.s_CarpetFarDetail.ToString());
				return;
			}
			SZ_State.s_DebugNoCarpet = cmd.IndexOf("off") > 0;
			Print("[DSTest] carpet hidden=" + SZ_State.s_DebugNoCarpet.ToString());
			return;
		}
		// oldwalls 0|1: the wall rule from before the cut along the walls (rebuild with carpet off / carpet on)
		if (cmd.IndexOf("oldwalls ") == 0)
		{
			SZ_State.s_DebugOldWalls = cmd.IndexOf("oldwalls 1") == 0;
			Print("[DSTest] old wall rule=" + SZ_State.s_DebugOldWalls.ToString());
			return;
		}
		// bprobe x z [n step]: the inside-a-building test at a point (or along a line of n points eastwards)
		if (cmd.IndexOf("bprobe ") == 0)
		{
			TStringArray bpArgs = new TStringArray;
			cmd.Split(" ", bpArgs);
			float bpX = bpArgs[1].ToFloat();
			float bpZ = bpArgs[2].ToFloat();
			int bpN = 1;
			float bpStep = 0.5;
			if (bpArgs.Count() >= 5)
			{
				bpN = bpArgs[3].ToInt();
				bpStep = bpArgs[4].ToFloat();
			}
			if (m_SZ_Client && m_SZ_Client.GetCarpet())
			{
				for (int bpI = 0; bpI < bpN; bpI++)
				{
					float bpPX = bpX + bpI * bpStep;
					string bpOut = m_SZ_Client.GetCarpet().DebugProbe(bpPX, bpZ);
					Print(string.Format("[DSTest] bprobe %1 %2 %3", bpPX, bpZ, bpOut));
				}
			}
			return;
		}
		// viewdist v o: this client's view distance and object view distance (m)
		if (cmd.IndexOf("viewdist ") == 0)
		{
			TStringArray vdArgs = new TStringArray;
			cmd.Split(" ", vdArgs);
			if (vdArgs.Count() >= 3)
			{
				float vdView = vdArgs[1].ToFloat();
				float vdObj = vdArgs[2].ToFloat();
				GetGame().GetWorld().SetViewDistance(vdView);
				GetGame().GetWorld().SetObjectViewDistance(vdObj);
			}
			Print("[DSTest] " + cmd);
			return;
		}
		if (cmd.IndexOf("probe ") == 0)
		{
			// probe x z: terrain, road surfaces and objects at one point
			TStringArray prArgs = new TStringArray;
			cmd.Split(" ", prArgs);
			float prx = prArgs[1].ToFloat();
			float prz = prArgs[2].ToFloat();
			float prT = GetGame().SurfaceY(prx, prz);
			float prR1 = GetGame().SurfaceRoadY3D(prx, prT + 0.8, prz, RoadSurfaceDetection.UNDER) - prT;
			float prR2 = GetGame().SurfaceRoadY3D(prx, prT + 5.0, prz, RoadSurfaceDetection.UNDER) - prT;
			float prR3 = GetGame().SurfaceRoadY(prx, prz) - prT;
			string prSurf;
			GetGame().SurfaceGetType(prx, prz, prSurf);
			array<Object> prObjs = new array<Object>;
			GetGame().GetObjectsAtPosition(Vector(prx, prT, prz), 6.0, prObjs, null);
			string prNames = "";
			foreach (Object pro : prObjs)
			{
				if (!pro)
					continue;
				string prShape = pro.GetShapeName();
				if (prShape.IndexOf("SeasonZ") >= 0)
					continue;
				prNames += " " + prShape + "/" + pro.GetType();
			}
			Print(string.Format("[DSTest] probe %1 %2 terrain=%3 surface=%4 road08=%5 road5=%6 roadLegacy=%7 cover=%8 objects:%9", prx, prz, prT, prSurf, prR1, prR2, prR3, SZ_SnowCarpet.CoverHeightAt(prx, prz) - prT, prNames));
			return;
		}
		if (cmd.IndexOf("offs ") == 0)
		{
			SZ_State.s_DebugExtraOffset = cmd.Substring(5, cmd.Length() - 5).ToFloat();
			Print("[DSTest] extra carpet offset " + SZ_State.s_DebugExtraOffset.ToString());
			return;
		}
		if (cmd.IndexOf("roads ") == 0)
		{
			// roads R step: how far the road surface lies above the terrain around the camera
			TStringArray rdArgs = new TStringArray;
			cmd.Split(" ", rdArgs);
			float rdR = rdArgs[1].ToFloat();
			float rdStep = rdArgs[2].ToFloat();
			vector rdC = GetGame().GetCurrentCameraPosition();
			int rdN = Math.Ceil(rdR / rdStep);
			int rdHits = 0;
			int rdAll = 0;
			float rdMax = 0;
			float rdSum = 0;
			string rdEx = "";
			array<int> rdHist = {0, 0, 0, 0, 0, 0, 0};
			array<float> rdEdges = {0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 100.0};
			for (int rdi = -rdN; rdi <= rdN; rdi++)
			{
				for (int rdj = -rdN; rdj <= rdN; rdj++)
				{
					float rdx = rdC[0] + rdi * rdStep;
					float rdz = rdC[2] + rdj * rdStep;
					float rdT = GetGame().SurfaceY(rdx, rdz);
					float rdY = GetGame().SurfaceRoadY3D(rdx, rdT + 0.8, rdz, RoadSurfaceDetection.UNDER);
					rdAll++;
					if (rdY - rdT > 0.0005)
					{
						rdHits++;
						rdSum += rdY - rdT;
						rdMax = Math.Max(rdMax, rdY - rdT);
						for (int rdb = 0; rdb < 7; rdb++)
						{
							if (rdY - rdT < rdEdges[rdb])
							{
								rdHist[rdb] = rdHist[rdb] + 1;
								break;
							}
						}
						if (rdHits <= 12)
							rdEx += string.Format(" (%1 %2 +%3)", rdx, rdz, rdY - rdT);
					}
				}
			}
			float rdAvg = 0;
			if (rdHits > 0)
				rdAvg = rdSum / rdHits;
			Print(string.Format("[DSTest] roads r=%1 step=%2: %3 of %4 points on a road, above terrain avg=%5 max=%6 hist<5/10/20/30/50/80/more cm=%7/%8/%9", rdR, rdStep, rdHits, rdAll, rdAvg, rdMax, rdHist[0], rdHist[1], rdHist[2]) + string.Format("/%1/%2/%3/%4", rdHist[3], rdHist[4], rdHist[5], rdHist[6]) + rdEx);
			return;
		}
		if (cmd.IndexOf("fly ") == 0)
		{
			TStringArray flyArgs = new TStringArray;
			cmd.Split(" ", flyArgs);
			if (flyArgs.Count() >= 7)
			{
				m_DST_FlyA = Vector(flyArgs[1].ToFloat(), 0, flyArgs[2].ToFloat());
				m_DST_FlyB = Vector(flyArgs[3].ToFloat(), 0, flyArgs[4].ToFloat());
				m_DST_FlyH = flyArgs[5].ToFloat();
				m_DST_FlySecs = Math.Max(0.5, flyArgs[6].ToFloat());
				m_DST_FlyT = 0;
				vector flyStart = m_DST_FlyA;
				flyStart[1] = GetGame().SurfaceY(flyStart[0], flyStart[2]) + m_DST_FlyH;
				if (!m_DST_Cam)
					Class.CastTo(m_DST_Cam, GetGame().CreateObject("staticcamera", flyStart, true));
				if (m_DST_Cam)
				{
					m_DST_Cam.SetPosition(flyStart);
					m_DST_Cam.SetFOV(0.95993);
					m_DST_Cam.SetActive(true);
				}
				Print("[DSTest] fly " + cmd);
			}
			return;
		}
		if (cmd.IndexOf("cut ") == 0)
		{
			// cut R step mode [scale]: mode 0 = ClutterCutter6x6 entity (local), 1 = cutter model as static object
			TStringArray cutArgs = new TStringArray;
			cmd.Split(" ", cutArgs);
			float cutR = cutArgs[1].ToFloat();
			float cutStep = cutArgs[2].ToFloat();
			int cutMode = cutArgs[3].ToInt();
			float cutScale = 1.0;
			if (cutArgs.Count() > 4)
				cutScale = cutArgs[4].ToFloat();
			if (!m_DST_Cutters)
				m_DST_Cutters = new array<Object>;
			vector cutC = GetGame().GetPlayer().GetPosition();
			int cutN = Math.Ceil(cutR / cutStep);
			int cutMade = 0;
			for (int cui = -cutN; cui <= cutN; cui++)
			{
				for (int cuj = -cutN; cuj <= cutN; cuj++)
				{
					float cux = cui * cutStep;
					float cuz = cuj * cutStep;
					if (cux * cux + cuz * cuz > cutR * cutR)
						continue;
					vector cutP = Vector(cutC[0] + cux, 0, cutC[2] + cuz);
					cutP[1] = GetGame().SurfaceY(cutP[0], cutP[2]);
					Object cutO;
					if (cutMode == 0)
						cutO = GetGame().CreateObjectEx("ClutterCutter6x6", cutP, ECE_LOCAL);
					else
						cutO = GetGame().CreateStaticObjectUsingP3D("DZ\\gear\\cultivation\\clutter_cutter_6m_x_6m.p3d", cutP, "0 0 0", cutScale, true);
					if (cutO)
					{
						m_DST_Cutters.Insert(cutO);
						cutMade++;
					}
				}
			}
			Print(string.Format("[DSTest] clutter cutters mode=%1 scale=%2 made=%3 total=%4", cutMode, cutScale, cutMade, m_DST_Cutters.Count()));
			return;
		}
		if (cmd.IndexOf("uncut") == 0)
		{
			int uncut = 0;
			if (m_DST_Cutters)
			{
				foreach (Object uco : m_DST_Cutters)
				{
					if (uco)
					{
						GetGame().ObjectDelete(uco);
						uncut++;
					}
				}
				m_DST_Cutters.Clear();
			}
			Print("[DSTest] clutter cutters removed: " + uncut.ToString());
			return;
		}
		if (cmd.IndexOf("treeinfo") == 0)
		{
			TStringArray tiArgs = new TStringArray;
			cmd.Split(" ", tiArgs);
			float tiR = 40;
			if (tiArgs.Count() > 1)
				tiR = tiArgs[1].ToFloat();
			array<Object> tiObjs = new array<Object>;
			GetGame().GetObjectsAtPosition(GetGame().GetPlayer().GetPosition(), tiR, tiObjs, null);
			int tiN = 0;
			foreach (Object tio : tiObjs)
			{
				if (!tio || tio.IsInherited(EntityAI))
					continue;
				string tiShape = tio.GetShapeName();
				string tiLow = tiShape;
				tiLow.ToLower();
				if (tiLow.IndexOf("plants") < 0)
					continue;
				if (tio.GetScale() < 0.01)
					continue; // an original hidden under its seasonal replacement
				vector tip = tio.GetPosition();
				vector titm[4];
				tio.GetTransform(titm);
				// the trunk foot is the modelling origin: minus the bounding centre in model space
				vector tiC = m_SZ_Client.GetTrees().ModelCentre(tiShape);
				vector tiFoot = titm[3] - titm[0] * tiC[0] - titm[1] * tiC[1] - titm[2] * tiC[2];
				float tiTerr = GetGame().SurfaceY(tiFoot[0], tiFoot[2]);
				Print(string.Format("[DSTest] treeinfo %1 foot=%2 %3 footAboveTerrain=%4 centre=%5 scale=%6", tiShape, tiFoot[0], tiFoot[2], tiFoot[1] - tiTerr, tiC, tio.GetScale()));
				tiN++;
				if (tiN >= 60)
					break;
			}
			return;
		}
		if (cmd.IndexOf("bottom ") == 0)
		{
			TStringArray botArgs = new TStringArray;
			cmd.Split(" ", botArgs);
			if (m_SZ_Client && m_SZ_Client.GetTrees())
			{
				for (int bi = 1; bi < botArgs.Count(); bi++)
				{
					Object bo = GetGame().CreateStaticObjectUsingP3D(botArgs[bi], Vector(7700, 1700, 7700), "0 0 0", 1.0, true);
					vector bmm[2];
					float brad = 0;
					vector bcol[2];
					bool hasCol = false;
					vector bcen = "0 0 0";
					string blods = "";
					if (bo)
					{
						brad = bo.ClippingInfo(bmm);
						hasCol = bo.GetCollisionBox(bcol);
						bcen = bo.GetBoundingCenter();
						GetGame().ObjectDelete(bo);
					}
					Print(string.Format("[DSTest] model %1: contact=%2 clip=%3..%4 radius=%5 collision=%6 %7..%8 center=%9", botArgs[bi], m_SZ_Client.GetTrees().ContactHeight(botArgs[bi]), bmm[0][1], bmm[1][1], brad, hasCol, bcol[0][1], bcol[1][1], bcen) + " lods:" + blods);
				}
			}
			return;
		}
		if (cmd.IndexOf("treestats") == 0)
		{
			if (m_SZ_Client && m_SZ_Client.GetTrees())
				Print("[DSTest] treestats" + m_SZ_Client.GetTrees().DebugStats());
			return;
		}
		// watertest x z: which water actions the cursor target conditions allow at a point (frozen ponds, snow cover)
		if (cmd.IndexOf("watertest ") == 0)
		{
			TStringArray wtArgs = new TStringArray;
			cmd.Split(" ", wtArgs);
			float wtX = wtArgs[1].ToFloat();
			float wtZ = wtArgs[2].ToFloat();
			float wtG = GetGame().SurfaceY(wtX, wtZ);
			float wtY = wtG;
			if (GetGame().SurfaceIsPond(wtX, wtZ))
			{
				float wtW = GetGame().GetWaterSurfaceHeightNoFakeWave(Vector(wtX, wtG, wtZ));
				if (wtW > wtY)
					wtY = wtW;
			}
			vector wtHit = Vector(wtX, wtY, wtZ);
			ActionTarget wtT = new ActionTarget(null, null, -1, wtHit, 0);
			PlayerBase wtP = PlayerBase.Cast(GetGame().GetPlayer());
			CCTWaterSurfaceEx wtDrink = new CCTWaterSurfaceEx(10, LIQUID_GROUP_DRINKWATER - LIQUID_SNOW - LIQUID_HOTWATER);
			CCTWaterSurfaceEx wtSnow = new CCTWaterSurfaceEx(10, LIQUID_SNOW);
			CCTWaterSurfaceEx wtFish = new CCTWaterSurfaceEx(30, LIQUID_SALTWATER | LIQUID_FRESHWATER);
			bool wtD = wtDrink.Can(wtP, wtT);
			bool wtS = wtSnow.Can(wtP, wtT);
			bool wtF = wtFish.Can(wtP, wtT);
			bool wtFrozen = SZ_Winter.FrozenPondAt(wtHit);
			bool wtCover = SZ_Winter.SnowCoverAt(wtHit);
			float wtDist = vector.Distance(wtP.GetPosition(), wtHit);
			Print(string.Format("[DSTest] watertest %1: drink=%2 snow=%3 fish=%4 frozenPond=%5 snowCover=%6 dist=%7", wtHit, wtD, wtS, wtF, wtFrozen, wtCover, wtDist));
			return;
		}		// icedump x z: the cell classes of the water body at a point into $profile:dst_body.txt
		if (cmd.IndexOf("icedump ") == 0)
		{
			TStringArray idArgs = new TStringArray;
			cmd.Split(" ", idArgs);
			vector idPos = Vector(idArgs[1].ToFloat(), 0, idArgs[2].ToFloat());
			if (m_SZ_Client && m_SZ_Client.GetIce())
				Print("[DSTest] icedump " + m_SZ_Client.GetIce().DebugDumpBody(idPos, "$profile:dst_body.txt"));
			return;
		}		if (cmd.IndexOf("iceremeasure") == 0)
		{
			if (m_SZ_Client && m_SZ_Client.GetIce())
				m_SZ_Client.GetIce().DebugRemeasure();
			Print("[DSTest] iceremeasure");
			return;
		}		// light base index cover: forces the lighting base (0 default, 1 dark nights), the light step (0-10) and the
		// snow cover of the colour grade (0-1); -1 = automatic
		if (cmd.IndexOf("light ") == 0)
		{
			TStringArray lgArgs = new TStringArray;
			cmd.Split(" ", lgArgs);
			SZ_State.s_DebugLightBase = lgArgs[1].ToInt();
			SZ_State.s_DebugLightIndex = lgArgs[2].ToInt();
			SZ_State.s_DebugCover = lgArgs[3].ToFloat();
			SZ_State.s_LightingDirty = true;
			Print(string.Format("[DSTest] light base=%1 index=%2 cover=%3", SZ_State.s_DebugLightBase, SZ_State.s_DebugLightIndex, SZ_State.s_DebugCover));
			return;
		}
		// foliage i x z: species i of the overview list as it looks normal, snowy, bare and in summer, side by side on
		// flat ground at x z (east of it), with the camera in front of the row
		if (cmd.IndexOf("foliage ") == 0)
		{
			TStringArray flArgs = new TStringArray;
			cmd.Split(" ", flArgs);
			int flI = flArgs[1].ToInt();
			float flX = flArgs[2].ToFloat();
			float flZ = flArgs[3].ToFloat();
			float flSpacingK = 0.45;
			float flDistK = 1.05;
			if (flArgs.Count() > 5)
			{
				flSpacingK = flArgs[4].ToFloat();
				flDistK = flArgs[5].ToFloat();
			}
			TStringArray flKeys = {"t_PiceaAbies_2f", "t_PiceaAbies_3f", "b_PiceaAbies_1f", "t_BetulaPendula_2f", "b_betulaHumilis_1s", "t_populusAlba_2s", "t_populusNigra_3s", "t_FagusSylvatica_2f", "t_quercusRobur_2f", "t_carpinus_2s", "t_FraxinusExcelsior_2f", "t_juglansRegia_2s", "t_LarixDecidua_2f", "t_malusDomestica_2s", "t_prunusDomestica_2s", "t_pyrusCommunis_2s", "t_robiniaPseudoacacia_2f", "t_salixAlba_2s", "t_sorbus_2s", "t_town_1s", "b_corylusAvellana_2s", "b_crataegusLaevigata_2s", "b_prunusSpinosa_2s", "b_rosaCanina_2s", "b_sambucusNigra_2s", "b_FagusSylvatica_1f", "b_quercusRobur_1f"};
			if (flI < 0 || flI >= flKeys.Count() || !m_SZ_Client || !m_SZ_Client.GetTrees())
				return;
			if (m_DST_Placed)
			{
				foreach (Object flOld : m_DST_Placed)
				{
					if (flOld)
						GetGame().ObjectDelete(flOld);
				}
				m_DST_Placed.Clear();
			}
			else
			{
				m_DST_Placed = new array<Object>;
			}
			string flKey = flKeys[flI];
			string flDir = "DZ\\plants\\tree\\";
			if (flKey == "b_betulaHumilis_1s" || flKey.IndexOf("b_corylus") == 0 || flKey.IndexOf("b_crataegus") == 0 || flKey.IndexOf("b_prunus") == 0 || flKey.IndexOf("b_rosa") == 0 || flKey.IndexOf("b_sambucus") == 0)
				flDir = "DZ\\plants\\bush\\";
			string flLow = flKey;
			flLow.ToLower();
			array<string> flModels = new array<string>;
			flModels.Insert(flDir + flKey + ".p3d");
			flModels.Insert(m_SZ_Client.GetTrees().VariantModel(flLow, SZ_TreeSwap.SHOW_WINTER));
			flModels.Insert(m_SZ_Client.GetTrees().VariantModel(flLow, SZ_TreeSwap.SHOW_BARE));
			flModels.Insert(m_SZ_Client.GetTrees().VariantModel(flLow, SZ_TreeSwap.SHOW_SUMMER));
			// the original sets the size: every variant is scaled to its height, as the seasonal trees are
			float flH = 0;
			float flSpacing = 14.0;
			string flOut = "";
			for (int flC = 0; flC < 4; flC++)
			{
				string flModel = flModels[flC];
				flOut += " | " + flModel;
				if (flModel == "")
					continue;
				Object flO = GetGame().CreateStaticObjectUsingP3D(flModel, Vector(flX, 0, flZ), "0 0 0", 1.0, true);
				if (!flO)
				{
					flOut += " (failed)";
					continue;
				}
				vector flBB[2];
				flO.ClippingInfo(flBB);
				float flHeight = flBB[1][1] - flBB[0][1];
				if (flC == 0)
				{
					flH = flHeight;
					flSpacing = Math.Clamp(flHeight * flSpacingK, 3.0, 12.0);
				}
				float flK = 1.0;
				if (flC > 0 && flH > 0.1 && flHeight > 0.1)
					flK = flH / flHeight;
				float flPX = flX + flC * flSpacing;
				vector flM[4];
				flM[0] = Vector(flK, 0, 0);
				flM[1] = Vector(0, flK, 0);
				flM[2] = Vector(0, 0, flK);
				flM[3] = Vector(flPX, GetGame().SurfaceY(flPX, flZ) - flBB[0][1] * flK, flZ);
				flO.SetTransform(flM);
				flO.Update();
				m_DST_Placed.Insert(flO);
			}
			// camera south of the row, looking at its middle
			float flMid = flX + 1.5 * flSpacing;
			float flDist = Math.Max(flH * flDistK, flSpacing * 3.4);
			vector flCam = Vector(flMid, 0, flZ - flDist);
			flCam[1] = GetGame().SurfaceY(flCam[0], flCam[2]) + Math.Max(1.7, flH * 0.42);
			vector flAt = Vector(flMid, GetGame().SurfaceY(flMid, flZ) + flH * 0.45, flZ);
			if (!m_DST_Cam)
				Class.CastTo(m_DST_Cam, GetGame().CreateObject("staticcamera", flCam, true));
			if (m_DST_Cam)
			{
				m_DST_Cam.SetPosition(flCam);
				m_DST_Cam.LookAt(flAt);
				m_DST_Cam.SetFOV(0.9);
				m_DST_Cam.SetActive(true);
			}
			Print(string.Format("[DSTest] foliage %1 %2 height=%3 spacing=%4%5", flI, flKey, flH, flSpacing, flOut));
			return;
		}		if (cmd.IndexOf("ptrack ") == 0)
		{
			m_DST_PTrack = cmd.Substring(7, cmd.Length() - 7).ToFloat();
			Print("[DSTest] ptrack for " + m_DST_PTrack.ToString());
			return;
		}
		if (cmd.IndexOf("icestats") == 0)
		{
			if (m_SZ_Client && m_SZ_Client.GetIce() && m_SZ_Client.GetCarpet())
			{
				string isStats = m_SZ_Client.GetIce().DebugStats();
				int isMode = m_SZ_Client.GetCarpet().GetPondMode();
				Print(string.Format("[DSTest] icestats %1 pondMode=%2 ice=%3/%4/%5", isStats, isMode, SZ_State.s_Ice0, SZ_State.s_Ice1, SZ_State.s_Ice2));
			}
			return;
		}
		if (cmd.IndexOf("roofstats") == 0)
		{
			if (m_SZ_Client && m_SZ_Client.GetRoofs())
				Print("[DSTest] roofstats " + m_SZ_Client.GetRoofs().DebugStats());
			return;
		}
		// roofoffset v: extra height of the roof snow (placed again right away)
		if (cmd.IndexOf("roofoffset ") == 0)
		{
			TStringArray roArgs = new TStringArray;
			cmd.Split(" ", roArgs);
			SZ_State.s_DebugRoofOffset = roArgs[1].ToFloat();
			if (m_SZ_Client && m_SZ_Client.GetRoofs())
				m_SZ_Client.GetRoofs().DebugReapply();
			Print("[DSTest] roof offset " + SZ_State.s_DebugRoofOffset.ToString());
			return;
		}
		// roofgrid x z: the ray grid of the building nearest to a point
		if (cmd.IndexOf("roofgrid ") == 0)
		{
			TStringArray rgArgs = new TStringArray;
			cmd.Split(" ", rgArgs);
			int rgGeo = 0;
			if (rgArgs.Count() >= 4)
				rgGeo = rgArgs[3].ToInt();
			if (rgArgs.Count() >= 3 && m_SZ_Client && m_SZ_Client.GetRoofs())
				Print("[DSTest] roofgrid " + m_SZ_Client.GetRoofs().DebugGrid(rgArgs[1].ToFloat(), rgArgs[2].ToFloat(), rgGeo));
			return;
		}
		// roofspan n: largest block of roof cells joined into one square (all roofs are sampled again)
		if (cmd.IndexOf("roofspan ") == 0)
		{
			TStringArray rsArgs = new TStringArray;
			cmd.Split(" ", rsArgs);
			SZ_State.s_DebugRoofMaxSpan = rsArgs[1].ToInt();
			if (m_SZ_Client && m_SZ_Client.GetRoofs())
				m_SZ_Client.GetRoofs().DebugReapply(true);
			Print("[DSTest] roof max span " + SZ_State.s_DebugRoofMaxSpan.ToString());
			return;
		}
		// rooftris x z: the snow triangles of the building nearest to a point
		if (cmd.IndexOf("rooftris ") == 0)
		{
			TStringArray rtArgs = new TStringArray;
			cmd.Split(" ", rtArgs);
			if (rtArgs.Count() >= 3 && m_SZ_Client && m_SZ_Client.GetRoofs())
				Print("[DSTest] rooftris " + m_SZ_Client.GetRoofs().DebugTris(rtArgs[1].ToFloat(), rtArgs[2].ToFloat()));
			return;
		}
		// roofplain n / roofedges 0|1: which structures carry roof snow and the search for roof edges (A/B tests)
		// roofab fit corner [filldiag]: the fitted far grid, the squared roof corners and the fill pieces along valleys
		// on (1) or off (0), all roofs built again
		if (cmd.IndexOf("roofab ") == 0)
		{
			TStringArray abArgs = new TStringArray;
			cmd.Split(" ", abArgs);
			SZ_State.s_DebugRoofFit = abArgs[1].ToInt() == 1;
			SZ_State.s_DebugRoofCorner = abArgs[2].ToInt() == 1;
			if (abArgs.Count() > 3)
				SZ_State.s_DebugRoofFillDiag = abArgs[3].ToInt() == 1;
			if (abArgs.Count() > 4)
				SZ_State.s_DebugRoofUneven = abArgs[4].ToInt() == 1;
			if (abArgs.Count() > 5)
				SZ_State.s_DebugRockThin = abArgs[5].ToInt() == 1;
			if (m_SZ_Client && m_SZ_Client.GetRoofs())
				m_SZ_Client.GetRoofs().DebugReapply(true);
			Print(string.Format("[DSTest] roofab fit=%1 corner=%2 diag=%3 uneven=%4 rockthin=%5", SZ_State.s_DebugRoofFit, SZ_State.s_DebugRoofCorner, SZ_State.s_DebugRoofFillDiag, SZ_State.s_DebugRoofUneven, SZ_State.s_DebugRockThin));
			return;
		}
		if (cmd.IndexOf("roofplain ") == 0 || cmd.IndexOf("roofedges ") == 0)
		{
			TStringArray rpArgs = new TStringArray;
			cmd.Split(" ", rpArgs);
			if (rpArgs[0] == "roofplain")
				SZ_State.s_DebugRoofPlain = rpArgs[1].ToInt();
			else
				SZ_State.s_DebugRoofEdges = rpArgs[1].ToInt() == 1;
			if (m_SZ_Client && m_SZ_Client.GetRoofs())
				m_SZ_Client.GetRoofs().DebugReapply(true);
			Print(string.Format("[DSTest] roof plain=%1 edges=%2", SZ_State.s_DebugRoofPlain, SZ_State.s_DebugRoofEdges));
			return;
		}
		// acttest: aims the camera at the trunk of the seasonal tree nearest to the player and reports the action target
		if (cmd.IndexOf("acttest") == 0)
		{
			m_DST_ActChop = cmd.IndexOf("chop") > 0;
			vector atP = GetGame().GetPlayer().GetPosition();
			m_DST_ActRepl = SZ_TreeSwap.NearestReplacement(atP, 30.0);
			if (!m_DST_ActRepl)
			{
				Print("[DSTest] acttest: no seasonal tree within 30 m");
				return;
			}
			vector trunk = m_DST_ActRepl.GetPosition();
			trunk[1] = GetGame().SurfaceY(trunk[0], trunk[2]) + 1.2;
			vector away = atP - trunk;
			away[1] = 0;
			float atDist = away.Length();
			away.Normalize();
			if (atDist > 2.2)
			{
				// actions only reach about 2 m from the player: report where to stand
				vector stand = trunk + away * 1.3;
				Print(string.Format("[DSTest] acttest: stand at %1 %2 (tree %3 is %4 m away)", stand[0], stand[2], m_DST_ActRepl.GetShapeName(), atDist));
				return;
			}
			vector eye = atP;
			eye[1] = GetGame().SurfaceY(eye[0], eye[2]) + 1.6;
			if (!m_DST_Cam)
				Class.CastTo(m_DST_Cam, GetGame().CreateObject("staticcamera", eye, true));
			m_DST_Cam.SetPosition(eye);
			m_DST_Cam.LookAt(trunk);
			m_DST_Cam.SetActive(true);
			m_DST_ActWait = 1.5;
			Print(string.Format("[DSTest] acttest: tree %1 at %2, original %3, camera %4", m_DST_ActRepl.GetShapeName(), trunk, SZ_TreeSwap.OriginalOf(m_DST_ActRepl), eye));
			return;
		}
		// findshape text r: map objects within r of the player whose model path contains text
		if (cmd.IndexOf("findshape ") == 0)
		{
			TStringArray fsArgs = new TStringArray;
			cmd.Split(" ", fsArgs);
			string fsText = fsArgs[1];
			float fsR = fsArgs[2].ToFloat();
			array<Object> fsObjs = new array<Object>;
			GetGame().GetObjectsAtPosition(GetGame().GetPlayer().GetPosition(), fsR, fsObjs, null);
			int fsN = 0;
			string fsOut = "";
			foreach (Object fsO : fsObjs)
			{
				if (!fsO)
					continue;
				string fsShape = fsO.GetShapeName();
				fsShape.ToLower();
				if (fsShape.IndexOf(fsText) < 0)
					continue;
				fsN++;
				if (fsN <= 15)
					fsOut += string.Format(" (%1 %2)", fsShape, fsO.GetPosition());
			}
			Print(string.Format("[DSTest] findshape %1 r=%2 count=%3%4", fsText, fsR, fsN, fsOut));
			return;
		}
		if (cmd.IndexOf("treescan") == 0)
		{
			TStringArray scanArgs = new TStringArray;
			cmd.Split(" ", scanArgs);
			if (scanArgs.Count() >= 5 && m_SZ_Client && m_SZ_Client.GetTrees())
			{
				if (!m_DST_Scan)
					m_DST_Scan = new DST_TreeScan();
				m_DST_Scan.Start(m_SZ_Client.GetTrees(), scanArgs[1].ToFloat(), scanArgs[2].ToFloat(), scanArgs[3].ToFloat(), scanArgs[4].ToFloat());
			}
			else
				Print("[DSTest] tree scan needs: treescan x0 z0 x1 z1 (and a running tree swap)");
			return;
		}
		// buildscan x0 z0 x1 z1: every structure of the area into buildscan.csv
		if (cmd.IndexOf("buildscan") == 0)
		{
			TStringArray bsArgs = new TStringArray;
			cmd.Split(" ", bsArgs);
			if (bsArgs.Count() >= 5)
			{
				if (!m_DST_BScan)
					m_DST_BScan = new DST_BuildScan();
				m_DST_BScan.Start(bsArgs[1].ToFloat(), bsArgs[2].ToFloat(), bsArgs[3].ToFloat(), bsArgs[4].ToFloat());
			}
			return;
		}
		// camabs x y z tx ty tz tag: camera at an absolute position looking at an absolute point; "settled tag" follows
		if (cmd.IndexOf("camabs ") == 0)
		{
			TStringArray caArgs2 = new TStringArray;
			cmd.Split(" ", caArgs2);
			if (caArgs2.Count() < 8)
				return;
			vector caPos = Vector(caArgs2[1].ToFloat(), caArgs2[2].ToFloat(), caArgs2[3].ToFloat());
			vector caTgt = Vector(caArgs2[4].ToFloat(), caArgs2[5].ToFloat(), caArgs2[6].ToFloat());
			if (!m_DST_Cam)
				Class.CastTo(m_DST_Cam, GetGame().CreateObject("staticcamera", caPos, true));
			if (m_DST_Cam)
			{
				m_DST_Cam.SetPosition(caPos);
				m_DST_Cam.LookAt(caTgt);
				m_DST_Cam.SetFOV(0.9);
				m_DST_Cam.SetActive(true);
			}
			m_DST_SettleTag = caArgs2[7];
			m_DST_NearTag = caArgs2[7];
			m_DST_NearPos = caTgt;
			m_DST_NearT = 0;
			m_DST_SettleT = 0;
			m_DST_SettleStill = 0;
			m_DST_SettleSum = -1;
			return;
		}
		// camrel x z h tx tz th tag: like camabs, with heights above the ground at each point (eye level views)
		if (cmd.IndexOf("camrel ") == 0)
		{
			TStringArray crArgs = new TStringArray;
			cmd.Split(" ", crArgs);
			if (crArgs.Count() < 8)
				return;
			float crX = crArgs[1].ToFloat();
			float crZ = crArgs[2].ToFloat();
			float crTX = crArgs[4].ToFloat();
			float crTZ = crArgs[5].ToFloat();
			vector crPos = Vector(crX, GetGame().SurfaceY(crX, crZ) + crArgs[3].ToFloat(), crZ);
			vector crTgt = Vector(crTX, GetGame().SurfaceY(crTX, crTZ) + crArgs[6].ToFloat(), crTZ);
			if (!m_DST_Cam)
				Class.CastTo(m_DST_Cam, GetGame().CreateObject("staticcamera", crPos, true));
			if (m_DST_Cam)
			{
				m_DST_Cam.SetPosition(crPos);
				m_DST_Cam.LookAt(crTgt);
				m_DST_Cam.SetFOV(0.9);
				m_DST_Cam.SetActive(true);
			}
			m_DST_SettleTag = crArgs[7];
			m_DST_SettleT = 0;
			m_DST_SettleStill = 0;
			m_DST_SettleSum = -1;
			return;
		}
		if (cmd.IndexOf("trees") == 0)
		{
			if (cmd.IndexOf("treesradius ") == 0)
			{
				TStringArray trArgs = new TStringArray;
				cmd.Split(" ", trArgs);
				SZ_State.s_DebugTreeRadius = trArgs[1].ToFloat();
				Print("[DSTest] seasonal tree radius " + SZ_State.s_DebugTreeRadius.ToString());
				return;
			}
			if (cmd.IndexOf("treesfreeze") == 0)
			{
				SZ_State.s_DebugTreesFreeze = cmd.IndexOf("off") < 0;
				Print("[DSTest] seasonal tree update frozen=" + SZ_State.s_DebugTreesFreeze.ToString());
				return;
			}
			SZ_State.s_DebugNoTrees = cmd.IndexOf("off") > 0;
			Print("[DSTest] tree swap disabled=" + SZ_State.s_DebugNoTrees.ToString());
			return;
		}
		if (cmd.IndexOf("treecol") == 0)
		{
			// horizontal collision-geometry ray through the trunk of the last swapped tree
			vector tc = SZ_State.s_DebugTreePos;
			for (int hgt = 0; hgt < 3; hgt++)
			{
				float yy = GetGame().SurfaceY(tc[0], tc[2]) + 0.6 + hgt * 0.6;
				vector from = Vector(tc[0] - 3.0, yy, tc[2]);
				vector to = Vector(tc[0] + 3.0, yy, tc[2]);
				vector hitPos;
				vector hitDir;
				int comp;
				set<Object> hits = new set<Object>;
				bool hit = DayZPhysics.RaycastRV(from, to, hitPos, hitDir, comp, hits, null, GetGame().GetPlayer(), false, false, ObjIntersectGeom, 0.0);
				string names = "";
				for (int hi = 0; hi < hits.Count(); hi++)
				{
					if (hits[hi])
						names += " " + hits[hi].GetShapeName() + "@" + hits[hi].GetScale().ToString();
				}
				Print(string.Format("[DSTest] treecol h=%1 hit=%2 at=%3 objs=%4", hgt, hit, hitPos, names));
			}
			return;
		}
		if (cmd.IndexOf("walk") == 0)
		{
			TStringArray wp = new TStringArray;
			cmd.Split(" ", wp);
			m_DST_WalkSpeed = 1;
			m_DST_WalkLeft = 8;
			if (wp.Count() > 1)
				m_DST_WalkSpeed = wp[1].ToFloat();
			if (wp.Count() > 2)
				m_DST_WalkLeft = wp[2].ToFloat();
			Print("[DSTest] walking speed " + m_DST_WalkSpeed.ToString() + " for " + m_DST_WalkLeft.ToString() + " s");
			return;
		}
		if (cmd.IndexOf("trail") == 0)
		{
			vector tpp = GetGame().GetPlayer().GetPosition();
			vector tdir = GetGame().GetPlayer().GetDirection();
			vector tside = Vector(tdir[2], 0, -tdir[0]);
			for (int st = 1; st <= 14; st++)
			{
				bool tleft = (st % 2) == 1;
				float sideOff = -0.11;
				if (!tleft)
					sideOff = 0.11;
				vector sp = tpp + tdir * (st * 0.36) + tside * sideOff;
				SZ_Footprints.PlaceAt(sp, tdir, tleft);
			}
			Print("[DSTest] trail placed, prints=" + SZ_Footprints.GetCount().ToString());
			return;
		}
		// ptest x z: rows of print models (deep left/right, shallow left/right) pointing north, east, south and west,
		// 0.6 m apart; rows run east, columns north
		if (cmd.IndexOf("ptest ") == 0)
		{
			TStringArray ptArgs = new TStringArray;
			cmd.Split(" ", ptArgs);
			float ptX = ptArgs[1].ToFloat();
			float ptZ = ptArgs[2].ToFloat();
			TStringArray ptModels = {"deep_l", "deep_r", "shallow_l", "shallow_r"};
			array<vector> ptDirs = {"0 0 1", "1 0 0", "0 0 -1", "-1 0 0"};
			for (int pm = 0; pm < ptModels.Count(); pm++)
			{
				string ptName = "SeasonZ\\data\\prints\\sz_print_" + ptModels[pm] + ".p3d";
				for (int pd = 0; pd < 4; pd++)
				{
					vector ptPos = Vector(ptX + pm * 0.7, 0, ptZ + pd * 0.6);
					Object ptO = SZ_Footprints.PlaceModel(ptName, ptPos, ptDirs[pd]);
					Print(string.Format("[DSTest] ptest %1 dir=%2 at %3 -> %4", ptModels[pm], ptDirs[pd], ptPos, ptO));
				}
			}
			return;
		}
		// covtest x z n: an n x n grid of prints 0.5 m apart, placed only where the snow cover shows snow
		if (cmd.IndexOf("covtest ") == 0)
		{
			TStringArray ctArgs = new TStringArray;
			cmd.Split(" ", ctArgs);
			float ctX = ctArgs[1].ToFloat();
			float ctZ = ctArgs[2].ToFloat();
			int ctN = ctArgs[3].ToInt();
			int ctOn = 0;
			int ctOff = 0;
			for (int cx = 0; cx < ctN; cx++)
			{
				for (int cz = 0; cz < ctN; cz++)
				{
					vector ctPos = Vector(ctX + cx * 0.5, 0, ctZ + cz * 0.5);
					if (SZ_SnowCarpet.CoversAt(ctPos[0], ctPos[2]))
					{
						SZ_Footprints.PlaceModel("SeasonZ\\data\\prints\\sz_print_shallow_l.p3d", ctPos, "0 0 1");
						ctOn++;
					}
					else
					{
						ctOff++;
					}
				}
			}
			Print(string.Format("[DSTest] covtest on=%1 off=%2", ctOn, ctOff));
			return;
		}
		if (cmd.IndexOf("ahead") == 0)
		{
			TStringArray ap = new TStringArray;
			cmd.Split(" ", ap);
			float ad = 4;
			float ah = 2.5;
			if (ap.Count() > 1)
				ad = ap[1].ToFloat();
			if (ap.Count() > 2)
				ah = ap[2].ToFloat();
			vector ppos = GetGame().GetPlayer().GetPosition();
			vector pdir = GetGame().GetPlayer().GetDirection();
			vector apos = ppos + pdir * ad;
			apos[1] = GetGame().SurfaceY(apos[0], apos[2]) + ah;
			vector atgt = ppos - pdir * 3.0;
			atgt[1] = GetGame().SurfaceY(atgt[0], atgt[2]);
			if (!m_DST_Cam)
				Class.CastTo(m_DST_Cam, GetGame().CreateObject("staticcamera", apos, true));
			if (m_DST_Cam)
			{
				m_DST_Cam.SetPosition(apos);
				m_DST_Cam.LookAt(atgt);
				m_DST_Cam.SetFOV(0.9);
				m_DST_Cam.SetActive(true);
			}
			Print("[DSTest] camera ahead of player " + ppos.ToString());
			return;
		}

		if (cmd.IndexOf("tree") == 0)
		{
			vector tp = SZ_State.s_DebugTreePos;
			vector cpos = tp + Vector(10, 0, 7);
			cpos[1] = GetGame().SurfaceY(cpos[0], cpos[2]) + 2.0;
			vector ctgt = tp + Vector(0, 5, 0);
			if (!m_DST_Cam)
				Class.CastTo(m_DST_Cam, GetGame().CreateObject("staticcamera", cpos, true));
			if (m_DST_Cam)
			{
				m_DST_Cam.SetPosition(cpos);
				m_DST_Cam.LookAt(ctgt);
				m_DST_Cam.SetFOV(0.9);
				m_DST_Cam.SetActive(true);
			}
			Print("[DSTest] camera at tree " + tp.ToString());
			return;
		}

		if (cmd.IndexOf("hide") == 0 || cmd.IndexOf("show") == 0 || cmd.IndexOf("hscale") == 0 || cmd.IndexOf("hmove") == 0)
		{
			TStringArray hp = new TStringArray;
			cmd.Split(" ", hp);
			float hr = 40;
			if (hp.Count() > 1)
				hr = hp[1].ToFloat();
			array<Object> hobjs = new array<Object>;
			GetGame().GetObjectsAtPosition(GetGame().GetCurrentCameraPosition(), hr, hobjs, null);
			int touched = 0;
			foreach (Object ho : hobjs)
			{
				if (!ho || !(ho.IsTree() || ho.IsBush()))
					continue;
				if (cmd.IndexOf("hide") == 0)
				{
					ho.ClearFlags(EntityFlags.VISIBLE, false);
					ho.Update();
				}
				else if (cmd.IndexOf("hscale") == 0)
				{
					ho.SetScale(0.001);
					ho.Update();
				}
				else if (cmd.IndexOf("hmove") == 0)
				{
					vector hm[4];
					ho.GetTransform(hm);
					hm[3] = hm[3] - Vector(0, 80, 0);
					ho.SetTransform(hm);
					ho.Update();
				}
				else
				{
					ho.SetFlags(EntityFlags.VISIBLE, false);
					ho.Update();
				}
				touched++;
			}
			Print("[DSTest] " + hp[0] + " trees/bushes: " + touched.ToString());
			return;
		}

		TStringArray f = new TStringArray;
		cmd.Split(" ", f);
		if (f.Count() == 6 && (f[0] == "sphere" || f[0] == "box"))
		{
			m_DST_FlatMode = 1;
			if (f[0] == "box")
				m_DST_FlatMode = 2;
			m_DST_FlatR = f[1].ToFloat();
			m_DST_FlatC = f[2].ToFloat();
			m_DST_FlatT = f[3].ToFloat();
			m_DST_FlatH = f[4].ToFloat();
			Print("[DSTest] flatten " + cmd);
			return;
		}

		// format: x z heightAboveGround targetX targetZ targetHeight [tag]
		TStringArray p = new TStringArray;
		cmd.Split(" ", p);
		if (p.Count() < 6)
			return;
		vector pos = Vector(p[0].ToFloat(), 0, p[1].ToFloat());
		pos[1] = GetGame().SurfaceY(pos[0], pos[2]) + p[2].ToFloat();
		vector target = Vector(p[3].ToFloat(), 0, p[4].ToFloat());
		target[1] = GetGame().SurfaceY(target[0], target[2]) + p[5].ToFloat();

		if (!m_DST_Cam)
			Class.CastTo(m_DST_Cam, GetGame().CreateObject("staticcamera", pos, true));
		if (m_DST_Cam)
		{
			m_DST_Cam.SetPosition(pos);
			m_DST_Cam.LookAt(target);
			m_DST_Cam.SetFOV(0.9);
			m_DST_Cam.SetActive(true);
		}
		Print("[DSTest] camera " + cmd);
	}
}


//! Candidate-only diagnostics: packet metadata and every body bit, not just aggregate ice depths.
class DST_FeatureState
{
	static void Log(string side)
	{
		Print(string.Format("[DSTest] featstate valid=%1 doy=%2 snow=%3/%4/%5 anomaly=%6 ice=%7/%8/%9", SZ_State.s_Valid, SZ_State.s_DayOfYear, SZ_State.s_Snow0, SZ_State.s_Snow1, SZ_State.s_Snow2, SZ_State.s_TempAnomaly, SZ_State.s_Ice0, SZ_State.s_Ice1, SZ_State.s_Ice2));
		int count = 0;
		string bits;
		if (SZ_State.s_PondCarry)
		{
			count = SZ_State.s_PondCarry.Count();
			foreach (int bit : SZ_State.s_PondCarry)
				bits += bit.ToString();
		}
		Print(string.Format("[DSTest] featpond side=%1 world=%2 layout=%3 revision=%4 count=%5 carry=%6", side, SZ_State.s_PondWorld, SZ_PondProtocol.LAYOUT, SZ_State.s_PondRevision, count, bits));
	}
}
