//! Client: on the season snow cover, footsteps sound and puff like the Sakhal snow surface
class DS_SnowGround
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
		if (!DS_State.s_Valid || !IsGroundSurface(surface))
			return false;
		float ground = g_Game.SurfaceY(pos[0], pos[2]);
		if (pos[1] - ground > 0.4)
			return false;
		if (DS_State.SnowAt(ground, DS_State.s_Snow0, DS_State.s_Snow1, DS_State.s_Snow2) < 1.0)
			return false;
		// bare ground under eaves and next to walls stays bare: no snow sound and no prints there
		if (!DS_SnowCarpet.CoversAt(pos[0], pos[2]))
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
		if (DS_SnowGround.IsOnSnow(GetPosition(), surface))
			return DS_SnowGround.SNOW_SURFACE;
		#endif
		return surface;
	}

	override void OnStepEvent(string pEventType, string pUserString, int pUserInt)
	{
		super.OnStepEvent(pEventType, pUserString, pUserInt);
		#ifndef SERVER
		if (pUserInt < 100)
			DS_Footprints.OnStep(this, pUserInt % 2 == 1);
		#endif
	}
}

