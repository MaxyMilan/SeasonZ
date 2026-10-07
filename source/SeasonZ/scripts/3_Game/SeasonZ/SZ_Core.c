// SeasonZ - shared definitions (server + client)

class SZ_Const
{
	static const int RPC_STATE = 83610418;
	static const string PROFILE_DIR = "$profile:SeasonZ";
	static const string CONFIG_FILE = "$profile:SeasonZ/config.json";
	static const string STATE_FILE = "$profile:SeasonZ/state.json";
	//! the profile folder of the mod before it was named SeasonZ: its files are copied over once
	static const string OLD_CONFIG_FILE = "$profile:DynamicSeasons/config.json";
	static const string OLD_STATE_FILE = "$profile:DynamicSeasons/state.json";
	static const string DATA = "SeasonZ\\data\\";
	//! the snow baked per model: one PBO per first letter of the model name (SeasonZ_Baked_<letter>.pbo with that
	//! prefix, see tools/split_stage.py), so that no PBO grows past the 2 GB the tools and the game can address
	static const string BAKED = "SeasonZ_Baked_";
	static const float LEVEL_ALT_0 = 0.0;
	static const float LEVEL_ALT_1 = 250.0;
	static const float LEVEL_ALT_2 = 500.0;
	//! ice on ponds shows from this thickness (cm)
	static const float ICE_VISIBLE = 0.5;
	//! from this thickness (cm) the ice carries snow: the snow cover continues over frozen ponds at the water level,
	//! and it stops again below ICE_SNOW_OFF
	static const float ICE_SNOW_ON = 4.0;
	static const float ICE_SNOW_OFF = 3.0;
}

class SZ_Calendar
{
	static int MonthStart(int month)
	{
		switch (month)
		{
			case 1: return 0;
			case 2: return 31;
			case 3: return 59;
			case 4: return 90;
			case 5: return 120;
			case 6: return 151;
			case 7: return 181;
			case 8: return 212;
			case 9: return 243;
			case 10: return 273;
			case 11: return 304;
		}
		return 334;
	}

	static float Wrap(float doy)
	{
		// Bounded normalization; NaN/infinity must not reach a loop or an array index.
		if (!(doy >= -1000000 && doy <= 1000000))
			return 0;
		doy = Math.ModFloat(doy, 365.0);
		if (doy < 0)
			doy += 365.0;
		// A tiny negative remainder can round up to 365 when added in float32.
		if (doy >= 365.0)
			doy = 0;
		return doy;
	}

	//! 0-based fractional day of year (365 day calendar)
	static float DayOfYear(int month, int day, float dayFraction)
	{
		return Wrap(MonthStart(month) + day - 1 + dayFraction);
	}

	static void ToMonthDay(float doy, out int month, out int day)
	{
		int d = Math.Floor(Wrap(doy));
		month = 12;
		for (int m = 2; m <= 12; m++)
		{
			if (d < MonthStart(m))
			{
				month = m - 1;
				break;
			}
		}
		day = d - MonthStart(month) + 1;
	}

	static float Phase(float doy)
	{
		return (doy - 15.0) / 365.0 * Math.PI2;
	}

	//! smooth season weights, 1 at the middle of the season, 0 at the opposite season
	static float Winter(float doy)
	{
		return Math.Max(0.0, Math.Cos(Phase(doy)));
	}

	static float Summer(float doy)
	{
		return Math.Max(0.0, -Math.Cos(Phase(doy)));
	}

	static float Spring(float doy)
	{
		return Math.Max(0.0, Math.Sin(Phase(doy)));
	}

	static float Autumn(float doy)
	{
		return Math.Max(0.0, -Math.Sin(Phase(doy)));
	}

	static string SeasonName(float doy)
	{
		int month;
		int day;
		ToMonthDay(doy, month, day);
		if (month == 12 || month <= 2)
			return "winter";
		if (month <= 5)
			return "spring";
		if (month <= 8)
			return "summer";
		return "autumn";
	}
}

//! Latest known season state. Written by the server controller, mirrored on clients through RPC.
class SZ_State
{
	static bool s_Valid = false;
	static float s_DayOfYear = 0;
	static float s_Snow0 = 0;
	static float s_Snow1 = 0;
	static float s_Snow2 = 0;
	//! current warm spell (positive) or cold snap (negative) on top of the climate curve, degrees
	static float s_TempAnomaly = 0;
	//! server: strength of the winter haze (config WinterHaze)
	static float s_WinterHaze = 1.0;
	//! ice on ponds and lakes at the three tracked heights (cm)
	static float s_Ice0 = 0;
	static float s_Ice1 = 0;
	static float s_Ice2 = 0;
	//! RPC v2: stable SZ_PondData index, server-owned hysteresis; no client-local reconstruction.
	static ref array<int> s_PondCarry;
	static string s_PondWorld;
	static int s_PondRevision;
	static bool s_HasPondCarry;
	static void ResetSession()
	{
		s_Valid = false;
		s_PondCarry = null;
		s_PondWorld = "";
		s_PondRevision = 0;
		s_HasPondCarry = false;
	}

	static bool s_LightingDirty = false;
	// client statistics, for the log and the local test harness
	static int s_StatCarpet = 0;
	static int s_StatTrees = 0;
	static int s_StatTreesKnown = 0;
	static float s_StatTreeReach = 0;
	static int s_StatTreesLost = 0;
	static int s_StatRoofs = 0;
	static int s_StatSkirts = 0;
	static int s_StatRays = 0;
	static int s_StatCutters = 0;
	static int s_StatIce = 0;
	static vector s_DebugTreePos = "0 0 0";
	static bool s_DebugNoTrees = false;
	//! test harness: the seasonal trees stay as they are, their update stops (to measure its cost)
	static bool s_DebugTreesFreeze = false;
	// local test harness only: limits the seasonal trees to this radius in metres (-1 = off)
	static float s_DebugTreeRadius = -1;
	// local test harness only: extra height of the whole snow cover in metres
	static float s_DebugExtraOffset = 0;
	// local test harness only: hides the snow cover
	static bool s_DebugNoCarpet = false;
	//! Performance prototype: exact building-edge detail radius (negative keeps production 70 m).
	static float s_DebugCarpetDetailNear = -1;
	//! Local A/B only: preserve 70 m exact detail, coarsen only the outer level-0 fringe.
	static bool s_DebugCarpetOuterCoarse;
	//! Prototype: no cover traversal after the last snow object has melted.
	static bool s_DebugCarpetIdle = true;
	// local test harness only: the wall rule from before the cut along the walls (A/B comparisons)
	static bool s_DebugOldWalls = false;
	// local test harness only: extra height of the roof snow (metres)
	static float s_DebugRoofOffset = 0;
	// local test harness only: largest block of roof cells joined into one square (1 = no joining)
	static int s_DebugRoofMaxSpan = 8;
	// local test harness only: size of the cell blocks a roof polygon's edge is cut in (cells)
	static int s_DebugEdgeBlock = 4;
	// local test harness only: plain structures with roof snow (0 none, 1 large ones, 2 also the small ones on the
	// fine grid of the walls, 3 also the small ones on the grid of the buildings) and the search for roof edges
	static int s_DebugRoofPlain = 3;
	static bool s_DebugRoofEdges = true;
	// local test harness only: flat tops drawn as single polygons (0 off, 1 small structures, 2 every structure)
	static int s_DebugRoofCaps = 2;
	// local test harness only: the grid of far buildings fitted to their box, and roof corners squared off in the grid
	static bool s_DebugRoofFit = true;
	static bool s_DebugRoofCorner = true;
	// local test harness only: the grid pieces filling gaps between roof polygons follow a valley or a ridge
	static bool s_DebugRoofFillDiag = true;
	// local test harness only: an uneven part of a building's roof no longer turns the whole roof into grid pieces
	// (off: tested on House_1W01/1W12, the polygons then leave a notch at the foot of a hip; the grid is cleaner)
	static bool s_DebugRoofUneven = false;
	// local test harness only: rocks carry the thin slab of walls (off: tested on rock_wallh2/rock_wallv, the rock
	// then shows through the snow in many places)
	static bool s_DebugRockThin = false;
	// local test harness only: no roof snow at all (to measure its cost)
	static bool s_DebugRoofOff = false;
	// local test harness only: the models with snow baked per model draw it as one object (off: sampled like the rest)
	static bool s_DebugBaked = true;
	// level 0 snow cover further than SZ_SnowCarpet.DETAIL_NEAR is split one step less around buildings (local test
	// harness: off = the full split everywhere, to measure it)
	static bool s_CarpetFarDetail = true;
	// local test harness only: log how every surface of a structure becomes polygons or grid pieces
	static bool s_DebugCapLog = false;
	// local test harness only: how far walls, fences and wrecks carry snow (metres, -1 = the default)
	static float s_DebugWallRadius = -1;
	// test harness statistics: the longest roof snow update of a frame and the longest single roof build (ms), with
	// the structure that took it
	static float s_StatRoofFrameMax = 0;
	static float s_StatRoofBuildMax = 0;
	static string s_StatRoofBuildWho = "";
	static float s_StatRoofPlaceMax = 0;
	static string s_StatRoofPlaceWho = "";
	static float s_StatRoofBuildSum = 0;
	static int s_StatRoofBuilds = 0;
	static int s_StatRoofFrames = 0;
	static int s_StatRoofSlow = 0;
	// the roof snow had work left at the end of the last frame (test harness: a view is settled only without it)
	static bool s_StatRoofBusy = false;
	// test harness statistics: roof snow time per part (ticks): 0 trash, 1 movables, 2 tile scans, 3 rays and
	// polygons, 4 placing pieces, 5 everything
	static ref array<int> s_StatRoofTicks;
	// test harness statistics: the longest update of each client part (ticks): 0 cover, 1 trees, 2 roofs, 3 grass,
	// 4 ice, 5 footprints and tracks; and the number of frames over 8 ms of all parts together
	static ref array<int> s_StatPartMax;
	static ref array<int> s_StatPartSum;
	static int s_StatPartSlow = 0;
	static int s_StatPartFrames = 0;
	// test harness statistics: the longest snow cover step (ticks): 0 new layout, 1 blocks near the camera,
	// 2 main cursor, 3 retired cells, 4 one single cell
	static ref array<int> s_StatCoverMax;
	static string s_StatCoverWorst = "";
	// test harness statistics: the longest tree step (ticks): 0 reach, 1 new anchor, 2 trim and restore, 3 near
	// tiles, 4 far tiles, 5 one tile scan
	static ref array<int> s_StatTreeMax;
	// local test harness only: highest walkable surface the snow cover rises over (metres, -1 = the default) and
	// whether such a surface has to be wide like a road (-1 = the default, 0 = no, 1 = yes)
	static float s_DebugRoadProbe = -1;
	static int s_DebugRoadWide = -1;
	// lighting normal of the snow cover: 2 = the terrain normal smoothed over the triangle's corners (default, hides
	// the facets of the triangles and the slight rise over paths), 0 = triangle plane, 1 = straight up (test harness)
	static int s_DebugNormalMode = 2;
	// local test harness only: forces the season date on the server (-1 = off)
	static float s_DebugDoy = -1;
	// local test harness only: pins the temperature anomaly on the server (below -100 = off)
	static float s_DebugAnomaly = -999;
	// local test harness only: logs every weather decision
	static bool s_DebugWeatherLog = false;
	// local test harness only: forces the light step (0-10), the lighting base (0 default, 1 dark nights) and the
	// snow cover the colour grade uses (0-1); -1 = off
	static int s_DebugLightIndex = -1;
	static int s_DebugLightBase = -1;
	static float s_DebugCover = -1;

	//! snow depth in cm at a given altitude, interpolated between the tracked levels
	static float SnowAt(float altitude, float s0, float s1, float s2)
	{
		if (altitude <= SZ_Const.LEVEL_ALT_0)
			return s0;
		if (altitude <= SZ_Const.LEVEL_ALT_1)
			return Math.Lerp(s0, s1, (altitude - SZ_Const.LEVEL_ALT_0) / (SZ_Const.LEVEL_ALT_1 - SZ_Const.LEVEL_ALT_0));
		if (altitude <= SZ_Const.LEVEL_ALT_2)
			return Math.Lerp(s1, s2, (altitude - SZ_Const.LEVEL_ALT_1) / (SZ_Const.LEVEL_ALT_2 - SZ_Const.LEVEL_ALT_1));
		return s2;
	}
}

class SZ_Util
{
	static bool IsSeasonalWorld()
	{
		string worldName;
		g_Game.GetWorldName(worldName);
		worldName.ToLower();
		return worldName != "sakhal";
	}

	static string Pad2(int value)
	{
		if (value < 10)
			return "0" + value.ToString();
		return value.ToString();
	}

	//! pond or lake water above the terrain at a point (not the sea), and its height. Uses the water height a
	//! player would swim in: SurfaceIsPond misses spots between the turned water squares of large lakes.
	static bool PondWater(float x, float z, out float water)
	{
		float ground = g_Game.SurfaceY(x, z);
		water = g_Game.GetWaterSurfaceHeightNoFakeWave(Vector(x, ground, z));
		if (water <= ground + 0.005)
			return false;
		return !g_Game.SurfaceIsSea(x, z);
	}

	//! trees, bushes and the seasonal tree models that stand in for them
	static bool IsVegetation(Object o)
	{
		if (!o)
			return false;
		if (o.IsTree() || o.IsBush())
			return true;
		string shape = o.GetShapeName();
		shape.ToLower();
		return shape.IndexOf("plants") >= 0;
	}
}

