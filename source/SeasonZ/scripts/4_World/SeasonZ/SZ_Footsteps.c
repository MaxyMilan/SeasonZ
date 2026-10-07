//! Client: on the season snow cover, footsteps sound and puff like the Sakhal snow surface
class SZ_SnowGround
{
	static const string SNOW_SURFACE = "sakhal_snow";

	//! surfaces of the terrain itself and of roads/paths lying on it; interiors, wood, metal and water stay as they are
	static bool IsGroundSurface(string surface)
	{
		if (surface.Length() < 4)
			return false;
		string head = surface.Substring(0, 3);
		if (head == "cp_" || head == "en_")
			return true;
		switch (surface)
		{
			case "asphalt_ext":
			case "asphalt_destroyed_ext":
			case "concrete_ext":
			case "gravel_large_ext":
			case "gravel_small_ext":
			case "dirt_ext":
			case "sand_ext":
			case "grass_dry_ext":
			case "stone_ext":
			case "rubble_large_ext":
			case "rubble_small_ext":
				return true;
		}
		return false;
	}

	//! true when something standing at this position is on snow covered ground
	static bool IsOnSnow(vector pos, string surface)
	{
		if (!SZ_State.s_Valid)
			return false;
		bool snowyIce = surface == "sakhal_ice_lake" && SZ_Winter.FrozenPondAt(pos);
		if (!IsGroundSurface(surface) && !snowyIce)
			return false;
		float ground = g_Game.SurfaceY(pos[0], pos[2]);
		if (snowyIce)
		{
			float water;
			if (!SZ_Util.PondWater(pos[0], pos[2], water))
				return false;
			ground = water;
			if (pos[1] < water - 0.03)
				return false;
		}
		if (pos[1] - ground > 0.4)
			return false;
		if (SZ_State.SnowAt(ground, SZ_State.s_Snow0, SZ_State.s_Snow1, SZ_State.s_Snow2) < 1.0)
			return false;
		// bare ground under eaves and next to walls stays bare: no snow sound and no prints there
		if (!SZ_SnowCarpet.CoversAt(pos[0], pos[2]))
			return false;
		return true;
	}
}

modded class DayZPlayerImplement
{
	override string GetSurfaceType(SurfaceAnimationBone limbType)
	{
		string surface = super.GetSurfaceType(limbType);
		#ifndef SERVER
		if (SZ_SnowGround.IsOnSnow(GetPosition(), surface))
			return SZ_SnowGround.SNOW_SURFACE;
		#endif
		return surface;
	}

	override void OnStepEvent(string pEventType, string pUserString, int pUserInt)
	{
		super.OnStepEvent(pEventType, pUserString, pUserInt);
		#ifndef SERVER
		if (pUserInt < 100)
			SZ_Footprints.OnStep(this, pUserInt % 2 == 1);
		#endif
	}
}

