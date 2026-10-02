//! One map tree that has seasonal Sakhal variants
class DS_TreeItem
{
	Object m_Orig;
	Object m_Repl;
	string m_Winter;
	string m_Bare;
	string m_Summer;
	bool m_Deciduous;
	bool m_Approx;
	bool m_SummerApprox;
	bool m_Hidden;
	//! a tree (not a bush, stump or fallen trunk): only trees change beyond the near ring
	bool m_IsTree;
	float m_Hash;
	float m_Alt;
	float m_Scale;
	vector m_T0;
	vector m_T1;
	vector m_T2;
	vector m_T3;
	int m_Shown;
}

class DS_TreeTile
{
	ref array<ref DS_TreeItem> m_Items;
	// footpaths lying on the ground: hidden under a closed snow cover
	ref array<Object> m_Paths;
	ref array<float> m_PathScale;
	ref array<float> m_PathAlt;
	bool m_PathsHidden;
	bool m_Scanned;
	//! some of the tile's objects were unloaded by the game (fog, view distance): scanned again from m_RescanAt on,
	//! less often while they stay away
	bool m_Partial;
	float m_RescanAt;
	float m_Backoff;
	//! most trees the tile ever held
	int m_Expect;

	void DS_TreeTile()
	{
		m_Items = new array<ref DS_TreeItem>;
		m_Paths = new array<Object>;
		m_PathScale = new array<float>;
		m_PathAlt = new array<float>;
	}
}

//! Client: seasonal trees. Chernarus spruces, birches and poplars near the camera are shown as their Sakhal
//! variants - snow laden in winter, bare in late autumn and early spring. Purely visual: the original map tree
//! keeps its place for collision and gameplay and is only made invisible while it is replaced.
//! The same scan finds the footpath models lying on the ground (dirt and stone paths); a closed snow cover hides
//! them, so they do not show as dark lines through the snow.
class DS_TreeSwap
{
	static const float TILE = 40.0;
	//! trees are seasonal out to RADIUS. The near ring (NEAR_RADIUS) is worked nearest first and restarts whenever the
	//! camera moves on; the far ring cycles with its own share of the frame budget, so it fills in while travelling too
	static const float RADIUS = 1600.0;
	static const float NEAR_RADIUS = 480.0;
	static const float KEEP_RADIUS = 1700.0;
	static const float NEAR_BUDGET = 4.0;
	static const float FAR_BUDGET = 2.5;
	// time per frame for giving the trees of tiles out of range their original look back (ms)
	static const float TREE_MS = 2.5;
	//! first wait before a tile whose trees the game unloaded is scanned again (seconds)
	static const float RESCAN_SECONDS = 8.0;
	//! The game unloads map objects the fog hides and the object view distance leaves out, and a scan loads them
	//! again: a tile out there would be built and torn down over and over. With view distance 10 km and object view
	//! distance 3.2 km fog 0.45 unloaded trees from 1140 to 1380 m (it varies), 0.65 from 970 m and 0.85 from 800 m.
	//! Trees start out seasonal to FOG_REACH / fog, which stays inside that; where the game is seen to unload
	//! seasonal trees anyway (a shorter object view distance, thicker fog) the reach is learnt from it.
	static const float FOG_REACH = 500.0;
	//! a learnt reach is tried a tile further every LIMIT_PROBE_SECONDS, so it follows a longer view distance again
	static const float LIMIT_PROBE_SECONDS = 300.0;
	//! tiles restored per frame once the reach shrank (the fog came in)
	//! tiles checked per frame for leaving the range (a full round over the ~5000 known tiles takes two seconds)
	static const int SWEEP_TILES = 50;
	//! snow depth (cm) from which footpaths disappear under the snow: the snow cover is closed from here on
	static const float PATH_COVER_CM = 5.0;
	static const int SHOW_ORIGINAL = 0;
	static const int SHOW_BARE = 1;
	static const int SHOW_WINTER = 2;
	static const int SHOW_SUMMER = 3;
	static const string WINTER_DIR = "dz\\plants_sakhal\\winter\\";
	static const string BARE_DIR = "dz\\plants_sakhal\\latefall\\";
	static const string SUMMER_DIR = "dz\\plants_bliss\\";
	//! replacement -> original, so player actions (chopping, gathering) still reach the real map tree
	protected static ref map<Object, Object> s_ReplToOrig;

	static Object OriginalOf(Object o)
	{
		if (!o || !s_ReplToOrig)
			return null;
		return s_ReplToOrig.Get(o);
	}

	//! test harness: the seasonal tree model closest to pos (within radius), or null
	static Object NearestReplacement(vector pos, float radius)
	{
		if (!s_ReplToOrig)
			return null;
		Object best = null;
		float bestD = radius;
		for (int i = 0; i < s_ReplToOrig.Count(); i++)
		{
			Object r = s_ReplToOrig.GetKey(i);
			Object orig = s_ReplToOrig.GetElement(i);
			if (!r || !orig || !orig.IsTree())
				continue;
			float d = vector.Distance(r.GetPosition(), pos);
			if (d < bestD)
			{
				bestD = d;
				best = r;
			}
		}
		return best;
	}

	static void RemapRaycastResults(array<ref RaycastRVResult> results)
	{
		if (!results || !s_ReplToOrig || s_ReplToOrig.Count() == 0)
			return;
		foreach (RaycastRVResult res : results)
		{
			if (!res)
				continue;
			Object orig = OriginalOf(res.obj);
			if (orig)
				res.obj = orig;
			orig = OriginalOf(res.parent);
			if (orig)
				res.parent = orig;
		}
	}

	protected bool m_Available;
	protected ref map<string, string> m_WinterMap;
	protected ref map<string, string> m_BareMap;
	protected ref map<string, string> m_SummerMap;
	protected ref map<string, bool> m_SummerApprox;
	protected bool m_SummerAvailable;
	protected ref map<string, bool> m_Deciduous;
	protected ref map<string, bool> m_Approx;
	protected ref map<int, ref DS_TreeTile> m_Tiles;
	//! tiles out of range whose trees still have to get their original look back (a few per frame)
	protected ref map<int, ref DS_TreeTile> m_Restore;
	protected float m_Clock;
	//! height of each model's origin above its ground contact, in model space (measured once per model)
	protected ref map<string, vector> m_Centres;
	//! lowest point of each model's geometry, in model space (measured once per model)
	protected ref map<string, float> m_Bottoms;
	//! tile offsets from the camera tile within RADIUS, nearest first (computed once)
	protected ref array<int> m_SpiralX;
	protected ref array<int> m_SpiralZ;
	protected ref array<float> m_SpiralD;
	protected int m_NearCount;
	protected int m_NearCursor;
	protected int m_FarCursor;
	protected int m_AnchorX;
	protected int m_AnchorZ;
	protected int m_Swapped;
	protected int m_Known;
	protected float m_Doy;
	protected float m_S0;
	protected float m_S1;
	protected float m_S2;
	protected float m_Cost;
	protected int m_Tick0;
	protected int m_TickLimit;
	protected vector m_Camera;
	//! how far trees are seasonal this frame, the reach learnt from unloaded trees and the fog it was learnt in
	protected float m_Reach;
	protected float m_LimitR;
	protected float m_LimitFog;
	protected float m_ProbeAt;
	protected float m_Fog;
	//! every tile further than m_TrimTo + TILE is gone (or waiting in a pending trim)
	protected float m_TrimTo;
	protected bool m_TrimPending;
	protected int m_TrimLeft;
	protected int m_SweepCursor;

	void DS_TreeSwap()
	{
		m_WinterMap = new map<string, string>;
		m_BareMap = new map<string, string>;
		m_SummerMap = new map<string, string>;
		m_SummerApprox = new map<string, bool>;
		m_Deciduous = new map<string, bool>;
		m_Approx = new map<string, bool>;
		m_Tiles = new map<int, ref DS_TreeTile>;
		m_Restore = new map<int, ref DS_TreeTile>;
		m_Centres = new map<string, vector>;
		m_Bottoms = new map<string, float>;
		m_SpiralX = new array<int>;
		m_SpiralZ = new array<int>;
		m_SpiralD = new array<float>;
		BuildSpiral();
		m_AnchorX = -100000;
		m_AnchorZ = -100000;
		m_Reach = RADIUS;
		m_LimitR = RADIUS;
		m_TrimTo = RADIUS;
		if (!s_ReplToOrig)
			s_ReplToOrig = new map<Object, Object>;
	}

	//! sorts the tile offsets by distance once: distance (quarter metres), then the offset, packed into one number
	protected void BuildSpiral()
	{
		int n = Math.Ceil(RADIUS / TILE) + 1;
		array<int> codes = new array<int>;
		for (int dx = -n; dx <= n; dx++)
		{
			for (int dz = -n; dz <= n; dz++)
			{
				float d = Math.Sqrt(dx * dx + dz * dz) * TILE;
				if (d > RADIUS)
					continue;
				int quarter = Math.Round(d * 4.0);
				codes.Insert(quarter * 65536 + (dx + 128) * 256 + (dz + 128));
			}
		}
		codes.Sort();
		m_NearCount = 0;
		foreach (int code : codes)
		{
			int low = code % 65536;
			int ox = low / 256 - 128;
			int oz = low % 256 - 128;
			m_SpiralX.Insert(ox);
			m_SpiralZ.Insert(oz);
			float dist = (code / 65536) * 0.25;
			m_SpiralD.Insert(dist);
			if (dist <= NEAR_RADIUS)
				m_NearCount++;
		}
	}

	void ~DS_TreeSwap()
	{
		Clear();
	}

	void Init()
	{
		// the seasonal models ship with the Frostline data; without it the trees simply stay as they are
		m_Available = g_Game.ConfigIsExisting("CfgPatches DZ_Plants_Sakhal");

		string spruces = "t_PiceaAbies_1f t_PiceaAbies_1s t_PiceaAbies_1sb t_piceaabies_2d t_PiceaAbies_2f t_PiceaAbies_2fb t_PiceaAbies_2s t_PiceaAbies_2sb t_piceaabies_3d b_PiceaAbies_1f b_PiceaAbies_1fb d_piceaabies_fallen d_piceaabies_fallenb d_piceaabies_fallenc d_piceaabies_stump d_piceaabies_stumpb";
		array<string> list = new array<string>;
		spruces.Split(" ", list);
		foreach (string s : list)
			AddEvergreen(s, s);
		// larger Chernarus spruces without an exact Sakhal twin use the nearest model, scaled to the same height
		AddEvergreen("t_PiceaAbies_3f", "t_PiceaAbies_2f", true);
		AddEvergreen("t_PiceaAbies_3s", "t_PiceaAbies_2s", true);

		string birches = "t_BetulaPendula_1f t_BetulaPendula_1fb t_BetulaPendula_1s t_BetulaPendula_2f t_BetulaPendula_2fb t_BetulaPendula_2fc t_BetulaPendula_2s t_BetulaPendula_2w t_BetulaPendula_3f t_BetulaPendula_3fb t_BetulaPendula_3fc t_BetulaPendula_3s b_BetulaPendula_1f b_betulaHumilis_1s";
		list.Clear();
		birches.Split(" ", list);
		foreach (string b : list)
			AddDeciduous(b, b, b);

		// poplars only exist bare, so they stay bare through the winter
		AddDeciduous("t_populusAlba_1f", "", "t_populusAlba_1f");
		AddDeciduous("t_populusAlba_2s", "", "t_populusAlba_2s");
		AddDeciduous("t_populusAlba_3s", "", "t_populusAlba_3s");
		AddDeciduous("t_populusNigra_3s", "", "t_populusNigra_3s");

		// broadleaf trees without a Sakhal twin lose their leaves as a birch of the same size class,
		// scaled to the original height (Chernarus name : birch model)
		string others = "t_carpinus_2s:2s t_FagusSylvatica_1f:1f t_FagusSylvatica_1fb:1fb t_FagusSylvatica_1fc:1f t_FagusSylvatica_1fd:1f t_FagusSylvatica_1fe:1f t_FagusSylvatica_1s:1s t_FagusSylvatica_2d:2f t_FagusSylvatica_2f:2f t_FagusSylvatica_2fb:2fb t_FagusSylvatica_2fc:2fc t_FagusSylvatica_2s:2s t_FagusSylvatica_2sb:2s t_FagusSylvatica_3d:3f t_FagusSylvatica_3f:3f t_FagusSylvatica_3fb:3fb t_FagusSylvatica_3s:3s";
		others += " t_FraxinusExcelsior_2f:2f t_FraxinusExcelsior_2s:2s t_FraxinusExcelsior_2w:2w t_FraxinusExcelsior_3s:3s t_juglansRegia_2s:2s t_juglansRegia_3s:3s";
		others += " t_LarixDecidua_1f:1f t_LarixDecidua_1s:1s t_LarixDecidua_2f:2f t_LarixDecidua_2fb:2fb t_LarixDecidua_2s:2s t_LarixDecidua_3f:3f t_LarixDecidua_3fb:3fb";
		others += " t_malusDomestica_1s:1s t_malusDomestica_2s:2s t_malusDomestica_3s:3s t_prunusDomestica_2s:2s t_pyrusCommunis_2s:2s t_pyrusCommunis_3s:3s t_pyrusCommunis_3sb:3s";
		others += " t_quercusRobur_1f:1f t_quercusRobur_1fb:1fb t_quercusRobur_1fc:1f t_quercusRobur_1fd:1f t_quercusRobur_1s:1s t_quercusRobur_2d:2f t_quercusRobur_2f:2f t_quercusRobur_2fb:2fb t_quercusRobur_2fc:2fc t_quercusRobur_2s:2s t_quercusRobur_2sb:2s t_quercusRobur_2sc:2s t_quercusRobur_3d:3f t_quercusRobur_3f:3f t_quercusRobur_3fb:3fb t_quercusRobur_3s:3s t_quercusRobur_3sb:3s";
		others += " t_robiniaPseudoacacia_1f:1f t_robiniaPseudoacacia_2f:2f t_robiniaPseudoacacia_2s:2s t_robiniaPseudoacacia_3f:3f t_salixAlba_2s:2s t_salixAlba_2sb:2s t_salixAlba_2sb_swamp:2s t_sorbus_2s:2s t_town_1s:1s t_town_1sb:1s";
		list.Clear();
		others.Split(" ", list);
		foreach (string pair : list)
		{
			array<string> kv = new array<string>;
			pair.Split(":", kv);
			if (kv.Count() == 2)
				AddDeciduous(kv[0], "t_BetulaPendula_" + kv[1], "t_BetulaPendula_" + kv[1], true);
		}

		// broadleaf bushes: small ones become dwarf birch, large ones pea shrub
		string bushes = "b_corylusAvellana_1f:s b_corylusAvellana_2s:l b_crataegusLaevigata_1s:s b_crataegusLaevigata_2s:l b_prunusSpinosa_1s:s b_prunusSpinosa_2s:l b_rosaCanina_1s:s b_rosaCanina_2s:l b_sambucusNigra_1s:s b_sambucusNigra_2s:l b_FagusSylvatica_1f:s b_quercusRobur_1f:s";
		list.Clear();
		bushes.Split(" ", list);
		foreach (string bp : list)
		{
			array<string> bkv = new array<string>;
			bp.Split(":", bkv);
			if (bkv.Count() != 2)
				continue;
			if (bkv[1] == "s")
				AddDeciduous(bkv[0], "b_betulaHumilis_1s", "b_betulaHumilis_1s", true);
			else
				AddBush(bkv[0], true);
		}

		// fresh green foliage for spring and summer comes from the Livonia summer models (Chernarus name : Livonia model)
		m_SummerAvailable = g_Game.ConfigIsExisting("CfgPatches DZ_Plants_Bliss");
		string summer = "t_FagusSylvatica_1f:Tree\\t_FagusSylvatica_1f t_FagusSylvatica_1fb:Tree\\t_FagusSylvatica_1fb t_FagusSylvatica_1fc:Tree\\t_FagusSylvatica_1fc t_FagusSylvatica_1fd:Tree\\t_FagusSylvatica_1fd t_FagusSylvatica_1fe:Tree\\t_FagusSylvatica_1fe t_FagusSylvatica_1s:Tree\\t_FagusSylvatica_1s t_FagusSylvatica_2d:Tree\\t_FagusSylvatica_2d t_FagusSylvatica_2f:Tree\\t_FagusSylvatica_2f t_FagusSylvatica_2fb:Tree\\t_FagusSylvatica_2fb t_FagusSylvatica_2fc:Tree\\t_FagusSylvatica_2fc t_FagusSylvatica_2s:Tree\\t_FagusSylvatica_2s t_FagusSylvatica_2sb:Tree\\t_FagusSylvatica_2sb t_FagusSylvatica_3d:Tree\\t_FagusSylvatica_3d t_FagusSylvatica_3f:Tree\\t_FagusSylvatica_3f t_FagusSylvatica_3fb:Tree\\t_FagusSylvatica_3fb t_FagusSylvatica_3s:Tree\\t_FagusSylvatica_3s";
		summer += " t_FagusSylvatica_2sb_Trail_B:Tree\\t_FagusSylvatica_2sb_Trail_B t_FagusSylvatica_2sb_Trail_G:Tree\\t_FagusSylvatica_2sb_Trail_G t_FagusSylvatica_2sb_Trail_R:Tree\\t_FagusSylvatica_2sb_Trail_R t_FagusSylvatica_2sb_Trail_Y:Tree\\t_FagusSylvatica_2sb_Trail_Y";
		summer += " t_LarixDecidua_1f:Tree\\t_LarixDecidua_1f t_LarixDecidua_1s:Tree\\t_LarixDecidua_1s t_LarixDecidua_2f:Tree\\t_LarixDecidua_2f t_LarixDecidua_2fb:Tree\\t_LarixDecidua_2fb t_LarixDecidua_2s:Tree\\t_LarixDecidua_2s t_LarixDecidua_3f:Tree\\t_LarixDecidua_3f t_LarixDecidua_3fb:Tree\\t_LarixDecidua_3fb";
		summer += " t_juglansRegia_2s:Tree\\t_juglansRegia_2s t_juglansRegia_3s:Tree\\t_juglansRegia_3s t_malusDomestica_1s:Tree\\t_malusDomestica_2s t_malusDomestica_2s:Tree\\t_malusDomestica_2s t_malusDomestica_3s:Tree\\t_malusDomestica_3s";
		summer += " t_pyrusCommunis_2s:Tree\\t_pyrusCommunis_2s t_pyrusCommunis_3s:Tree\\t_pyrusCommunis_3s t_pyrusCommunis_3sb:Tree\\t_pyrusCommunis_3s t_salixAlba_2s:Tree\\t_salixAlba_2sb t_salixAlba_2sb:Tree\\t_salixAlba_2sb t_salixAlba_2sb_swamp:Tree\\t_salixAlba_2sb t_sorbus_2s:Tree\\t_sorbus_2s t_populusNigra_3s:Tree\\t_populusNigra_3sb";
		summer += " t_BetulaPendula_1f:Tree\\t_BetulaPendulaE_1s t_BetulaPendula_1fb:Tree\\t_BetulaPendulaE_1s t_BetulaPendula_1s:Tree\\t_BetulaPendulaE_1s t_BetulaPendula_2f:Tree\\t_BetulaPendulaE_2f t_BetulaPendula_2fb:Tree\\t_BetulaPendulaE_2f t_BetulaPendula_2fc:Tree\\t_BetulaPendulaE_2f t_BetulaPendula_2s:Tree\\t_BetulaPendulaE_2s t_BetulaPendula_2w:Tree\\t_BetulaPendulaE_2w t_BetulaPendula_3f:Tree\\t_BetulaPendulaE_3f t_BetulaPendula_3fb:Tree\\t_BetulaPendulaE_3f t_BetulaPendula_3fc:Tree\\t_BetulaPendulaE_3f t_BetulaPendula_3s:Tree\\t_BetulaPendulaE_3s";
		summer += " t_quercusRobur_1f:Tree\\t_FagusSylvatica_1f t_quercusRobur_1fb:Tree\\t_FagusSylvatica_1fb t_quercusRobur_1fc:Tree\\t_FagusSylvatica_1fc t_quercusRobur_1fd:Tree\\t_FagusSylvatica_1fd t_quercusRobur_1s:Tree\\t_FagusSylvatica_1s t_quercusRobur_2d:Tree\\t_FagusSylvatica_2d t_quercusRobur_2f:Tree\\t_FagusSylvatica_2f t_quercusRobur_2fb:Tree\\t_FagusSylvatica_2fb t_quercusRobur_2fc:Tree\\t_FagusSylvatica_2fc t_quercusRobur_2s:Tree\\t_FagusSylvatica_2s t_quercusRobur_2sb:Tree\\t_FagusSylvatica_2sb t_quercusRobur_2sc:Tree\\t_FagusSylvatica_2s t_quercusRobur_3d:Tree\\t_FagusSylvatica_3d t_quercusRobur_3f:Tree\\t_FagusSylvatica_3f t_quercusRobur_3fb:Tree\\t_FagusSylvatica_3fb t_quercusRobur_3s:Tree\\t_FagusSylvatica_3s t_quercusRobur_3sb:Tree\\t_FagusSylvatica_3s";
		summer += " t_carpinus_2s:Tree\\t_acer_2s t_FraxinusExcelsior_2f:Tree\\t_FagusSylvaticaE_2s t_FraxinusExcelsior_2s:Tree\\t_FagusSylvaticaE_2s t_FraxinusExcelsior_2w:Tree\\t_FagusSylvaticaE_2s t_FraxinusExcelsior_3s:Tree\\t_FagusSylvaticaE_3f t_prunusDomestica_2s:Tree\\t_malusDomestica_2s t_robiniaPseudoacacia_1f:Tree\\t_FagusSylvatica_1f t_robiniaPseudoacacia_2f:Tree\\t_FagusSylvatica_2f t_robiniaPseudoacacia_2s:Tree\\t_FagusSylvatica_2s t_robiniaPseudoacacia_3f:Tree\\t_FagusSylvatica_3f t_town_1s:Tree\\t_acer_2s t_town_1sb:Tree\\t_acer_2s t_populusAlba_1f:Tree\\t_populusNigra_3sb t_populusAlba_2s:Tree\\t_populusNigra_3sb t_populusAlba_3s:Tree\\t_populusNigra_3sb";
		summer += " b_prunusSpinosa_1s:Bush\\b_prunusSpinosa_1s b_prunusSpinosa_2s:Bush\\b_prunusSpinosa_2s b_rosaCanina_1s:Bush\\b_rosaCanina_1s b_rosaCanina_2s:Bush\\b_rosaCanina_2s b_sambucusNigra_1s:Bush\\b_sambucusNigra_1s b_sambucusNigra_2s:Bush\\b_sambucusNigra_2s b_FagusSylvatica_1f:Bush\\b_FagusSylvatica_1f b_betulaHumilis_1s:Bush\\b_betulaNana_1s b_corylusAvellana_1f:Bush\\b_corylusHeterophylla_1s b_corylusAvellana_2s:Bush\\b_corylusHeterophylla_2s";
		list.Clear();
		summer.Split(" ", list);
		foreach (string sp : list)
		{
			array<string> skv = new array<string>;
			sp.Split(":", skv);
			if (skv.Count() != 2)
				continue;
			string skey = skv[0];
			skey.ToLower();
			m_SummerMap.Set(skey, SUMMER_DIR + skv[1] + "_summer.p3d");
			m_Deciduous.Set(skey, true);
			string model = skv[1];
			model.ToLower();
			string own = skey;
			if (model.IndexOf(own) < 0)
				m_SummerApprox.Set(skey, true);
		}

		Print(string.Format("[DynamicSeasons] seasonal trees: frostline=%1 livonia=%2 species models=%3", m_Available, m_SummerAvailable, m_WinterMap.Count() + m_BareMap.Count() + m_SummerMap.Count()));
	}

	protected void AddEvergreen(string chernarus, string sakhal, bool approx = false)
	{
		string key = chernarus;
		key.ToLower();
		m_WinterMap.Set(key, WINTER_DIR + sakhal + "_winter.p3d");
		if (approx)
			m_Approx.Set(key, true);
	}

	protected void AddDeciduous(string chernarus, string sakhalWinter, string sakhalBare, bool approx = false)
	{
		string key = chernarus;
		key.ToLower();
		if (sakhalWinter != "")
			m_WinterMap.Set(key, WINTER_DIR + sakhalWinter + "_winter.p3d");
		if (sakhalBare != "")
			m_BareMap.Set(key, BARE_DIR + sakhalBare + "_latefall.p3d");
		m_Deciduous.Set(key, true);
		if (approx)
			m_Approx.Set(key, true);
	}

	//! the Sakhal pea shrub is named "leafless" instead of "latefall"
	protected void AddBush(string chernarus, bool approx)
	{
		string key = chernarus;
		key.ToLower();
		m_WinterMap.Set(key, WINTER_DIR + "b_caraganaArborescens_2s_winter.p3d");
		m_BareMap.Set(key, BARE_DIR + "b_caraganaArborescens_2s_leafless.p3d");
		m_Deciduous.Set(key, true);
		if (approx)
			m_Approx.Set(key, true);
	}

	int GetSwappedCount()
	{
		return m_Swapped;
	}

	int GetKnownCount()
	{
		return m_Known;
	}

	//! lower case model file name without folder and extension, the key of the species maps
	static string ShapeKey(Object o)
	{
		string shape = o.GetShapeName();
		shape.ToLower();
		return KeyOfShape(shape);
	}

	//! the species key (file name without folder and extension) of a lower case model path
	static string KeyOfShape(string lower)
	{
		string shape = lower;
		int slash = shape.LastIndexOf("\\");
		if (slash >= 0)
			shape = shape.Substring(slash + 1, shape.Length() - slash - 1);
		int dot = shape.LastIndexOf(".");
		if (dot > 0)
			shape = shape.Substring(0, dot);
		return shape;
	}

	//! seasonal model for a map tree species (empty when the species has no such variant)
	string VariantModel(string key, int show)
	{
		if (show == SHOW_WINTER && m_Available)
			return m_WinterMap.Get(key);
		if (show == SHOW_BARE && m_Available)
			return m_BareMap.Get(key);
		if (show == SHOW_SUMMER && m_SummerAvailable)
			return m_SummerMap.Get(key);
		return "";
	}

	bool VariantApprox(string key, int show)
	{
		if (show == SHOW_SUMMER)
			return m_SummerApprox.Contains(key);
		return m_Approx.Contains(key);
	}

	//! how a seasonal model is fitted onto a map tree. Map trees keep their origin at the model centre, so a model of
	//! another size or shape placed on the same origin would stand higher or lower. k scales a stand-in species to
	//! the original height (the height of a model is twice its origin height above the trunk foot); shift is how far
	//! the model moves along the tree's up axis (in the original's model units) so both trunks stand on the same foot.
	static void FitModel(bool approx, float origContact, float replContact, out float k, out float shift)
	{
		k = 1.0;
		if (approx && replContact > 0.25 && origContact > 0.25)
			k = Math.Clamp(origContact / replContact, 0.6, 1.8);
		shift = 0;
		// without a measured contact on both models the centres stay together (the v0.2 placement)
		if (origContact > 0 && replContact > 0)
			shift = k * replContact - origContact;
	}

	//! Tree models are built standing on their modelling origin and get re-centred on their bounding box when
	//! binarised. The bounding centre is that shift: the modelling origin (the foot of the trunk) lies at minus the
	//! centre in model space, and the map stands exactly that point on the terrain (checked against Chernarus map
	//! trees). Measured once per model.
	vector ModelCentre(string p3d)
	{
		vector c;
		if (m_Centres.Find(p3d, c))
			return c;
		c = "0 0 0";
		float bottom = 0;
		Object o = g_Game.CreateStaticObjectUsingP3D(p3d, Vector(7700, 1600, 7700), "0 0 0", 1.0, true);
		if (o)
		{
			c = o.GetBoundingCenter();
			vector mm[2];
			o.ClippingInfo(mm);
			bottom = mm[0][1];
			g_Game.ObjectDelete(o);
		}
		m_Centres.Set(p3d, c);
		m_Bottoms.Set(p3d, bottom);
		m_Cost += 0.5;
		return c;
	}

	//! lowest point of a model's geometry in model space (below zero, the model centre)
	float ModelBottom(string p3d)
	{
		ModelCentre(p3d);
		return m_Bottoms.Get(p3d);
	}

	//! how far a placed tree model must sink to reach the terrain all around its trunk as far as the map tree it
	//! replaces does. Map trees on slopes stand with their foot on the uphill side and reach down with a long trunk
	//! base; a seasonal model with a shorter base would show a gap on the downhill side. Trees standing on rocks or
	//! at cliff edges do not reach the terrain at all; there the seasonal model reaches exactly as far as the
	//! original, so it is never pushed into the rock. Trees whose foot stands on an object (planters, platforms,
	//! rocks) keep their foot where the original's is. mat is the model's world transform, centre and bottom its
	//! measured centre and lowest point, reach how far the original reaches below its foot (metres, 0 for the
	//! original itself). drop: how far the terrain around the trunk falls below the foot; depth: how far the model
	//! reaches below its foot.
	static float GroundSink(vector mat[4], vector centre, float bottom, float reach, out float drop, out float depth)
	{
		vector foot = mat[3] - mat[0] * centre[0] - mat[1] * centre[1] - mat[2] * centre[2];
		float scale = mat[1].Length();
		vector up = mat[1].Normalized();
		depth = (-centre[1] - bottom) * scale * up[1];
		float ground = g_Game.SurfaceY(foot[0], foot[2]);
		if (foot[1] - ground > 0.3)
		{
			// the tree stands on an object, not on the terrain
			drop = 0;
			return 0;
		}
		float radius = Math.Clamp(0.5 * scale, 0.3, 1.0);
		float low = ground;
		for (int i = 0; i < 8; i++)
		{
			float a = i * Math.PI * 0.25;
			float h = g_Game.SurfaceY(foot[0] + Math.Cos(a) * radius, foot[2] + Math.Sin(a) * radius);
			low = Math.Min(low, h);
		}
		drop = foot[1] - low;
		// the lowest point of the model should end a few centimetres below the lowest terrain around the trunk, but
		// no deeper than the original reaches
		float need = Math.Min(drop + 0.03, reach);
		float sink = need - depth;
		if (sink <= 0)
			return 0;
		return Math.Min(sink, 3.0);
	}

	//! height of a model's origin above the foot of its trunk (model space)
	float ContactHeight(string p3d)
	{
		vector c = ModelCentre(p3d);
		return c[1];
	}

	protected int TileKey(int tx, int tz)
	{
		return tx * 65536 + tz;
	}

	protected float TileDist(int tx, int tz)
	{
		float dx = (tx + 0.5) * TILE - m_Camera[0];
		float dz = (tz + 0.5) * TILE - m_Camera[2];
		return Math.Sqrt(dx * dx + dz * dz);
	}

	//! after the camera moved to another tile: the near ring starts over and tiles well outside the area are restored
	protected void OnNewAnchor()
	{
		m_NearCursor = 0;
	}

	//! finds the tile's seasonal trees and footpaths; a rescan only adds the objects the tile does not know yet
	//! (the game loads them again after fog or a shorter view distance unloaded them)
	protected void ScanTile(DS_TreeTile tile, int tx, int tz, bool rescan)
	{
		tile.m_Scanned = true;
		vector center = Vector((tx + 0.5) * TILE, 0, (tz + 0.5) * TILE);
		center[1] = g_Game.SurfaceY(center[0], center[2]);
		array<Object> objects = new array<Object>;
		g_Game.GetObjectsAtPosition(center, TILE * 0.7072, objects, null);
		m_Cost += 1.0 + objects.Count() * 0.004;
		map<Object, bool> known = null;
		if (rescan)
		{
			known = new map<Object, bool>;
			foreach (DS_TreeItem ki : tile.m_Items)
			{
				if (ki.m_Orig)
					known.Set(ki.m_Orig, true);
			}
			foreach (Object kp : tile.m_Paths)
			{
				if (kp)
					known.Set(kp, true);
			}
		}

		foreach (Object o : objects)
		{
			if (!o || o.IsInherited(EntityAI) || o.IsInherited(Man))
				continue;
			if (known && known.Contains(o))
				continue;
			vector p = o.GetPosition();
			if (Math.Floor(p[0] / TILE) != tx || Math.Floor(p[2] / TILE) != tz)
				continue;

			// the mod's own snow, ice and grass pieces are most of the objects in a town tile: they go first
			string full = o.GetShapeName();
			full.ToLower();
			if (full.IndexOf("dynamicseasons\\") >= 0)
				continue;
			if (IsPathShape(full))
			{
				tile.m_Paths.Insert(o);
				tile.m_PathScale.Insert(o.GetScale());
				tile.m_PathAlt.Insert(p[1]);
				continue;
			}

			string shape = KeyOfShape(full);

			string winter = "";
			string bare = "";
			string green = "";
			if (m_Available)
			{
				winter = m_WinterMap.Get(shape);
				bare = m_BareMap.Get(shape);
			}
			if (m_SummerAvailable)
				green = m_SummerMap.Get(shape);
			if (winter == "" && bare == "" && green == "")
				continue;

			DS_TreeItem item = new DS_TreeItem();
			item.m_Orig = o;
			item.m_Winter = winter;
			item.m_Bare = bare;
			item.m_Summer = green;
			item.m_Deciduous = m_Deciduous.Contains(shape);
			item.m_Approx = m_Approx.Contains(shape);
			item.m_SummerApprox = m_SummerApprox.Contains(shape);
			item.m_IsTree = shape.IndexOf("t_") == 0;
			item.m_Alt = p[1];
			item.m_Scale = o.GetScale();
			vector tm[4];
			o.GetTransform(tm);
			item.m_T0 = tm[0];
			item.m_T1 = tm[1];
			item.m_T2 = tm[2];
			item.m_T3 = tm[3];
			float hx = p[0] * 0.7310 + p[2] * 0.3137;
			item.m_Hash = hx - Math.Floor(hx);
			tile.m_Items.Insert(item);
			m_Known++;
		}

		int count = tile.m_Items.Count();
		if (count >= tile.m_Expect)
		{
			tile.m_Expect = count;
			tile.m_Partial = false;
			tile.m_Backoff = RESCAN_SECONDS;
		}
		else
		{
			tile.m_Partial = true;
			if (tile.m_Backoff < RESCAN_SECONDS)
				tile.m_Backoff = RESCAN_SECONDS;
			tile.m_RescanAt = m_Clock + tile.m_Backoff;
			tile.m_Backoff = Math.Min(tile.m_Backoff * 1.5, 60.0);
		}
	}

	//! drops the trees and paths the game unloaded (their replacements go too) and plans a rescan of the tile
	protected void PruneLost(DS_TreeTile tile)
	{
		float nearestLost = 1000000.0;
		for (int i = tile.m_Items.Count() - 1; i >= 0; i--)
		{
			DS_TreeItem it = tile.m_Items[i];
			if (it.m_Orig)
				continue;
			float ldx = it.m_T3[0] - m_Camera[0];
			float ldz = it.m_T3[2] - m_Camera[2];
			nearestLost = Math.Min(nearestLost, Math.Sqrt(ldx * ldx + ldz * ldz));
			DeleteReplacement(it);
			tile.m_Items.Remove(i);
			m_Known--;
			DS_State.s_StatTreesLost++;
		}
		// trees unloaded beyond the near ring: the game draws no further here (fog or object view distance)
		if (nearestLost > NEAR_RADIUS && nearestLost < 100000.0)
		{
			float learnt = Math.Max(nearestLost - TILE, NEAR_RADIUS + TILE);
			if (learnt < m_LimitR)
			{
				m_LimitR = learnt;
				m_LimitFog = m_Fog;
				m_ProbeAt = m_Clock + LIMIT_PROBE_SECONDS;
				Print(string.Format("[DynamicSeasons] trees: the game unloads trees from %1 m at fog %2, seasonal trees within %3 m", Math.Round(nearestLost), m_Fog, Math.Round(learnt)));
			}
		}
		for (int j = tile.m_Paths.Count() - 1; j >= 0; j--)
		{
			if (tile.m_Paths[j])
				continue;
			tile.m_Paths.Remove(j);
			tile.m_PathScale.Remove(j);
			tile.m_PathAlt.Remove(j);
		}
		tile.m_Partial = true;
		tile.m_Backoff = RESCAN_SECONDS;
		tile.m_RescanAt = m_Clock + RESCAN_SECONDS;
	}

	//! leaves drop over about two and a half weeks from mid October and come back from the end of April
	protected bool IsBare(float hash)
	{
		float fall = 288.0 + 18.0 * hash;
		float leafOut = 112.0 + 18.0 * hash;
		return m_Doy >= fall || m_Doy < leafOut;
	}

	//! fresh foliage from leaf-out until the leaves start to turn in September; the map's own autumn colours follow
	protected bool IsGreen(float hash)
	{
		float leafOut = 112.0 + 18.0 * hash;
		float turn = 250.0 + 22.0 * hash;
		return m_Doy >= leafOut && m_Doy < turn;
	}

	protected int Desired(DS_TreeItem it)
	{
		if (!it.m_Orig || it.m_Orig.IsDamageDestroyed())
			return SHOW_ORIGINAL;

		float snow = DS_State.SnowAt(it.m_Alt, m_S0, m_S1, m_S2);
		// small per tree spread, so a light snow line does not flip a whole forest at once
		if (it.m_Winter != "" && snow >= 1.0 + it.m_Hash * 2.0)
			return SHOW_WINTER;
		if (it.m_Deciduous && it.m_Bare != "" && IsBare(it.m_Hash))
			return SHOW_BARE;
		if (it.m_Summer != "" && IsGreen(it.m_Hash))
			return SHOW_SUMMER;
		return SHOW_ORIGINAL;
	}

	//! map objects ignore the visibility flag, so the original is shrunk to nothing in place; its position stays
	//! valid for actions and the server keeps the real tree
	protected void HideOriginal(DS_TreeItem it)
	{
		if (!it.m_Orig || it.m_Hidden)
			return;
		it.m_Orig.SetScale(0.001);
		it.m_Orig.Update();
		it.m_Hidden = true;
	}

	protected void ShowOriginal(DS_TreeItem it)
	{
		if (!it.m_Orig || !it.m_Hidden)
			return;
		float s = it.m_Scale;
		if (s <= 0.01)
			s = 1.0;
		it.m_Orig.SetScale(s);
		it.m_Orig.Update();
		it.m_Hidden = false;
	}

	protected void DeleteReplacement(DS_TreeItem it)
	{
		if (!it.m_Repl)
			return;
		s_ReplToOrig.Remove(it.m_Repl);
		g_Game.ObjectDelete(it.m_Repl);
		it.m_Repl = null;
		m_Swapped--;
	}

	protected void Apply(DS_TreeItem it, int show)
	{
		DeleteReplacement(it);
		m_Cost += 0.3;

		if (show == SHOW_ORIGINAL || !it.m_Orig)
		{
			ShowOriginal(it);
			it.m_Shown = SHOW_ORIGINAL;
			return;
		}

		string model = it.m_Winter;
		if (show == SHOW_BARE)
			model = it.m_Bare;
		else if (show == SHOW_SUMMER)
			model = it.m_Summer;

		vector mat[4];
		mat[0] = it.m_T0;
		mat[1] = it.m_T1;
		mat[2] = it.m_T2;
		mat[3] = it.m_T3;
		Object repl = g_Game.CreateStaticObjectUsingP3D(model, mat[3], "0 0 0", 1.0, true);
		if (!repl)
		{
			ShowOriginal(it);
			it.m_Shown = SHOW_ORIGINAL;
			return;
		}

		bool approx = it.m_Approx;
		if (show == SHOW_SUMMER)
			approx = it.m_SummerApprox;
		float k;
		float shift;
		vector origCentre = ModelCentre(it.m_Orig.GetShapeName());
		vector replCentre = ModelCentre(model);
		FitModel(approx, origCentre[1], replCentre[1], k, shift);
		mat[0] = mat[0] * k;
		mat[1] = mat[1] * k;
		mat[2] = mat[2] * k;
		if (shift != 0)
		{
			// both trunk feet on the same point: along the up axis and, for leaning models, sideways as well
			float sx = k * replCentre[0] - origCentre[0];
			float sz = k * replCentre[2] - origCentre[2];
			mat[3] = mat[3] + it.m_T0 * sx + it.m_T1 * shift + it.m_T2 * sz;
		}
		// on slopes the seasonal model reaches down to the terrain on the downhill side as well
		float drop;
		float depth;
		float origDrop;
		float origDepth;
		vector origMat[4];
		origMat[0] = it.m_T0;
		origMat[1] = it.m_T1;
		origMat[2] = it.m_T2;
		origMat[3] = it.m_T3;
		GroundSink(origMat, origCentre, ModelBottom(it.m_Orig.GetShapeName()), 0, origDrop, origDepth);
		float sink = GroundSink(mat, replCentre, ModelBottom(model), origDepth, drop, depth);
		if (sink > 0)
			mat[3] = mat[3] - Vector(0, sink, 0);
		repl.SetTransform(mat);
		repl.Update();
		HideOriginal(it);
		it.m_Repl = repl;
		s_ReplToOrig.Set(repl, it.m_Orig);
		it.m_Shown = show;
		m_Swapped++;
		DS_State.s_DebugTreePos = mat[3];
	}

	protected void RestoreTile(DS_TreeTile tile)
	{
		if (!tile)
			return;
		foreach (DS_TreeItem it : tile.m_Items)
		{
			DeleteReplacement(it);
			ShowOriginal(it);
			m_Known--;
		}
		tile.m_Items.Clear();
		SetPathsHidden(tile, false);
		tile.m_Paths.Clear();
		tile.m_PathScale.Clear();
		tile.m_PathAlt.Clear();
	}

	//! ground details a closed snow cover buries: dirt and stone footpaths (their roads/parts folder also holds the
	//! real roads, which stay), the grass growing in the joints of airfield concrete panels, the road decals (joint
	//! lines, cracks, patches) and the low kerbs around the trees on squares, which would otherwise draw dark lines and
	//! grids through the snow, and the small plants the map places by hand (reeds, burdock, nettles), green summer
	//! tufts the grass cutters cannot reach
	static bool IsPath(Object o)
	{
		string shape = o.GetShapeName();
		shape.ToLower();
		return IsPathShape(shape);
	}

	//! IsPath for a lower case model path
	static bool IsPathShape(string shape)
	{
		if (shape.IndexOf("\\roads\\parts\\path_") >= 0)
			return true;
		if (shape.IndexOf("\\roads\\panels\\proxy\\grass_") >= 0)
			return true;
		if (shape.IndexOf("\\plants\\clutter\\") >= 0)
			return true;
		if (shape.IndexOf("misc_tree_pavement") >= 0)
			return true;
		return shape.IndexOf("\\roads\\decals\\") >= 0;
	}

	protected void SetPathsHidden(DS_TreeTile tile, bool hidden)
	{
		if (tile.m_PathsHidden == hidden)
			return;
		tile.m_PathsHidden = hidden;
		for (int i = 0; i < tile.m_Paths.Count(); i++)
		{
			Object o = tile.m_Paths[i];
			if (!o)
				continue;
			float s = tile.m_PathScale[i];
			if (s <= 0.01)
				s = 1.0;
			if (hidden)
				s = 0.001;
			o.SetScale(s);
			o.Update();
		}
		m_Cost += 0.02 * tile.m_Paths.Count();
	}

	//! a tile's paths share one state: hidden when the snow at the lowest of them forms a closed cover
	protected void UpdatePaths(DS_TreeTile tile)
	{
		if (tile.m_Paths.Count() == 0)
			return;
		float low = 100000.0;
		foreach (float alt : tile.m_PathAlt)
			low = Math.Min(low, alt);
		bool hide = DS_State.SnowAt(low, m_S0, m_S1, m_S2) >= PATH_COVER_CM;
		SetPathsHidden(tile, hide);
	}

	void Update(float timeslice, vector camera, float doy, float s0, float s1, float s2)
	{
		if (!m_Available && !m_SummerAvailable)
			return;
		if (DS_State.s_DebugNoTrees)
		{
			if (m_Tiles.Count() > 0)
				Clear();
			return;
		}
		if (DS_State.s_DebugTreesFreeze)
			return;

		m_Tick0 = TickCount(0);
		m_TickLimit = 0;
		float tps = DS_RoofSnow.DebugTicksPerSec();
		if (tps > 0)
			m_TickLimit = TREE_MS * tps / 1000.0;
		m_Clock += timeslice;
		m_Camera = camera;
		m_Doy = doy;
		m_S0 = s0;
		m_S1 = s1;
		m_S2 = s2;
		if (!DS_State.s_StatTreeMax)
		{
			DS_State.s_StatTreeMax = new array<int>;
			for (int st = 0; st < 6; st++)
				DS_State.s_StatTreeMax.Insert(0);
		}
		int tick = TickCount(0);
		UpdateReach();
		tick = StatTree(0, tick);

		int ax = Math.Floor(camera[0] / TILE);
		int az = Math.Floor(camera[2] / TILE);
		if (ax != m_AnchorX || az != m_AnchorZ)
		{
			m_AnchorX = ax;
			m_AnchorZ = az;
			OnNewAnchor();
		}
		tick = StatTree(1, tick);
		SweepTiles();
		RestoreQueued();
		tick = StatTree(2, tick);

		m_Cost = 0;
		int count = m_SpiralX.Count();
		// a tile's trees reach up to a tile further than its centre (in clear air the full RADIUS)
		float reachTile = m_Reach - TILE;
		if (m_Reach >= RADIUS)
			reachTile = RADIUS;
		while (count > m_NearCount && m_SpiralD[count - 1] > reachTile)
			count--;
		if (DS_State.s_DebugTreeRadius >= 0)
		{
			while (count > m_NearCount && m_SpiralD[count - 1] > DS_State.s_DebugTreeRadius)
				count--;
		}
		int visited = 0;
		while (m_Cost < NEAR_BUDGET && visited < m_NearCount)
		{
			if (m_NearCursor >= m_NearCount)
				m_NearCursor = 0;
			VisitTile(m_NearCursor, 1000000.0, false);
			m_NearCursor++;
			visited++;
		}
		tick = StatTree(3, tick);

		int farCount = count - m_NearCount;
		float farStop = m_Cost + FAR_BUDGET;
		visited = 0;
		while (farCount > 0 && m_Cost < farStop && visited < farCount)
		{
			if (m_FarCursor >= farCount)
				m_FarCursor = 0;
			// a dense far tile is swapped over several frames instead of all at once
			if (!VisitTile(m_NearCount + m_FarCursor, farStop + 1.0, true))
				break;
			m_FarCursor++;
			visited++;
		}
		StatTree(4, tick);
	}

	//! test harness statistics: the ticks since tick0 for one step (keeps the longest); returns the tick now
	protected int StatTree(int part, int tick0)
	{
		int now = TickCount(0);
		int d = now - tick0;
		if (d > DS_State.s_StatTreeMax[part])
			DS_State.s_StatTreeMax[part] = d;
		return now;
	}

	//! the reach of the seasonal trees: the fog's (FOG_REACH / fog) and the one learnt from unloaded trees. A reach
	//! learnt in fog follows the fog (the game's reach goes with 1 / fog) and is forgotten once the air clears; any
	//! learnt reach is tried a tile further now and then
	protected void UpdateReach()
	{
		m_Fog = g_Game.GetWeather().GetFog().GetActual();
		if (m_LimitR < RADIUS && m_LimitFog >= 0.1 && Math.AbsFloat(m_Fog - m_LimitFog) > 0.03)
		{
			m_LimitR = Math.Min(RADIUS, m_LimitR * m_LimitFog / Math.Max(m_Fog, 0.05));
			m_LimitFog = m_Fog;
		}
		if (m_LimitR < RADIUS && m_Clock >= m_ProbeAt)
		{
			m_LimitR = Math.Min(RADIUS, m_LimitR + TILE);
			m_ProbeAt = m_Clock + LIMIT_PROBE_SECONDS;
		}
		float reach = m_LimitR;
		if (m_Fog > 0.01)
			reach = Math.Min(reach, FOG_REACH / m_Fog);
		m_Reach = Math.Clamp(reach, NEAR_RADIUS + TILE, RADIUS);
		if (m_Reach > m_TrimTo)
		{
			m_TrimTo = m_Reach;
		}
		else if (m_Reach < m_TrimTo - TILE)
		{
			m_TrimTo = m_Reach;
			m_TrimPending = true;
		}
	}

	//! tiles that left the range (the camera moved on, or the fog came in and the reach shrank) go to the restore
	//! queue: a share of the known tiles is checked every frame, so no frame walks through all of them
	protected void SweepTiles()
	{
		float keep = Math.Min(KEEP_RADIUS, m_Reach + 2.0 * TILE);
		if (m_TrimPending)
		{
			keep = m_Reach + TILE;
			// the fog came in: one full round with the shorter range
			if (m_TrimLeft <= 0)
				m_TrimLeft = m_Tiles.Count() + 1;
		}
		for (int checks = 0; checks < SWEEP_TILES && m_Tiles.Count() > 0; checks++)
		{
			if (m_SweepCursor >= m_Tiles.Count())
				m_SweepCursor = 0;
			int key = m_Tiles.GetKey(m_SweepCursor);
			int kx = Math.Floor(key / 65536.0);
			int kz = key - kx * 65536;
			if (TileDist(kx, kz) > keep)
			{
				// the map fills the gap: the same place is checked again with the next tile in it
				m_Restore.Set(key, m_Tiles.Get(key));
				m_Tiles.Remove(key);
			}
			else
				m_SweepCursor++;
			if (m_TrimPending)
			{
				m_TrimLeft--;
				if (m_TrimLeft <= 0)
					m_TrimPending = false;
			}
		}
		if (m_Tiles.Count() == 0)
		{
			m_TrimPending = false;
			m_TrimLeft = 0;
		}
	}

	//! gives the trees of tiles that left the range their original look back, as many tiles as the frame's time allows
	//! (a whole row of tiles leaves at once when the camera crosses a tile border)
	protected void RestoreQueued()
	{
		int done = 0;
		while (m_Restore.Count() > 0)
		{
			if (done > 0 && OverTime())
				break;
			int rk = m_Restore.GetKey(0);
			DS_TreeTile rt = m_Restore.Get(rk);
			m_Restore.Remove(rk);
			if (rt)
				RestoreTile(rt);
			done++;
		}
	}

	//! how far the trees are seasonal right now (metres)
	float GetReach()
	{
		return m_Reach;
	}

	//! the frame's time for swapping trees is used up
	protected bool OverTime()
	{
		return m_TickLimit > 0 && TickCount(m_Tick0) > m_TickLimit;
	}

	//! scans a tile of the spiral once and brings its trees to the season (seasons and snow change slowly: checking
	//! every tree once every few frames is plenty). Stops swapping once the frame's cost passes limit; false when trees
	//! of the tile are still waiting. Far tiles change their trees only for snow and bare branches: bushes and stumps
	//! are a few pixels at that distance and the original foliage passes for summer (each replacement costs frame time).
	protected bool VisitTile(int index, float limit, bool far)
	{
		int tx = m_AnchorX + m_SpiralX[index];
		int tz = m_AnchorZ + m_SpiralZ[index];
		int key = TileKey(tx, tz);
		DS_TreeTile tile = m_Tiles.Get(key);
		if (!tile)
		{
			// back in range before its trees were restored: it keeps its state
			tile = m_Restore.Get(key);
			if (tile)
				m_Restore.Remove(key);
			else
				tile = new DS_TreeTile();
			m_Tiles.Set(key, tile);
		}
		if (!tile.m_Scanned)
		{
			int scanTick = TickCount(0);
			ScanTile(tile, tx, tz, false);
			StatTree(5, scanTick);
		}
		else if (tile.m_Partial && m_Clock >= tile.m_RescanAt)
			ScanTile(tile, tx, tz, true);

		m_Cost += 0.03 + tile.m_Items.Count() * 0.012;
		UpdatePaths(tile);
		bool complete = true;
		bool lost = false;
		foreach (DS_TreeItem it : tile.m_Items)
		{
			if (!it.m_Orig)
			{
				lost = true;
				continue;
			}
			int want = Desired(it);
			if (far && (!it.m_IsTree || want == SHOW_SUMMER))
				want = SHOW_ORIGINAL;
			if (want == it.m_Shown)
				continue;
			if (m_Cost > limit)
			{
				complete = false;
				break;
			}
			Apply(it, want);
		}
		if (lost)
			PruneLost(tile);
		return complete;
	}

	void Clear()
	{
		if (!m_Tiles)
			return;
		ClearTiles();
	}

	//! test harness: swapped trees by distance ring, kind (t_ tree, b_ bush, other) and shown variant
	string DebugStats()
	{
		array<int> counts = new array<int>;
		for (int c = 0; c < 2 * 3 * 4; c++)
			counts.Insert(0);
		for (int i = 0; i < m_Tiles.Count(); i++)
		{
			int key = m_Tiles.GetKey(i);
			int kx = Math.Floor(key / 65536.0);
			int kz = key - kx * 65536;
			int ring = 0;
			if (TileDist(kx, kz) > NEAR_RADIUS)
				ring = 1;
			DS_TreeTile tile = m_Tiles.GetElement(i);
			foreach (DS_TreeItem it : tile.m_Items)
			{
				if (!it.m_Orig || it.m_Shown == SHOW_ORIGINAL)
					continue;
				string shape = ShapeKey(it.m_Orig);
				int kind = 2;
				if (shape.IndexOf("t_") == 0)
					kind = 0;
				else if (shape.IndexOf("b_") == 0)
					kind = 1;
				int idx = (ring * 3 + kind) * 4 + it.m_Shown;
				counts[idx] = counts[idx] + 1;
			}
		}
		string s = "";
		array<string> rings = {"near", "far"};
		array<string> kinds = {"tree", "bush", "other"};
		for (int r = 0; r < 2; r++)
		{
			for (int k = 0; k < 3; k++)
			{
				int b = (r * 3 + k) * 4;
				s += string.Format(" %1/%2: bare=%3 winter=%4 summer=%5", rings[r], kinds[k], counts[b + SHOW_BARE], counts[b + SHOW_WINTER], counts[b + SHOW_SUMMER]);
			}
		}
		return s;
	}

	protected void ClearTiles()
	{
		for (int i = 0; i < m_Tiles.Count(); i++)
			RestoreTile(m_Tiles.GetElement(i));
		m_Tiles.Clear();
		for (int r = 0; r < m_Restore.Count(); r++)
			RestoreTile(m_Restore.GetElement(r));
		m_Restore.Clear();
		m_NearCursor = 0;
		m_FarCursor = 0;
		m_Swapped = 0;
		m_Known = 0;
		m_AnchorX = -100000;
		m_AnchorZ = -100000;
	}
}

