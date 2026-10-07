//! Winter for food and water. Crops grow with the warmth of the season and die in hard frost outdoors; greenhouses and
//! polytunnels keep them alive and growing slowly through the winter. Frozen or snowed over ground cannot be sown.
//! Wild berries and mushrooms found in the cold are mostly rotten, rose hips dried (the game already treats its
//! fruit and vegetables like this below 5 degrees; the winter mushrooms, oyster and wood ear, keep their vanilla
//! odds). Frozen ponds give no water and no fish, while the season's
//! snow cover can be eaten and melted like the snow of Sakhal. (Digging garden plots and stashes already stops at
//! 5 degrees in the game itself, driven by the season's temperatures.)
class SZ_Winter
{
	//! crops stop growing below this daily mean temperature and grow at full speed from GROW_FULL (degrees)
	static const float GROW_MIN = 5.0;
	static const float GROW_FULL = 15.0;
	//! outdoor crops die when the temperature drops this low
	static const float FROST_KILL = -2.0;
	//! an unheated greenhouse or polytunnel is this much warmer than the air outside on average, and protects down
	//! to SHELTER_FROST_KILL outside: it lengthens the season, in deep winter crops in it barely grow
	static const float SHELTER_WARMTH = 8.0;
	static const float SHELTER_FROST_KILL = -12.0;
	//! snow (cm) that covers the ground for eating, melting and sowing
	static const float SNOW_COVER_CM = 2.0;

	static bool Active()
	{
		if (!SZ_State.s_Valid || !SZ_Util.IsSeasonalWorld())
			return false;
		return g_Game.GetMission() && g_Game.GetMission().GetWorldData();
	}

	static bool Sheltered(GardenBase garden)
	{
		if (!garden)
			return false;
		return garden.IsInherited(GardenPlotGreenhouse) || garden.IsInherited(GardenPlotPolytunnel);
	}

	//! daily mean temperature at a place, with the current warm spell or cold snap
	static float DailyMean(vector pos)
	{
		float tmin;
		float tmax;
		g_Game.GetMission().GetWorldData().SZ_DailyRange(SZ_State.s_DayOfYear, pos[1], tmin, tmax);
		return 0.5 * (tmin + tmax);
	}

	//! share of the full growth speed of a crop (0 to 1)
	static float GrowthFactor(GardenBase garden, vector pos)
	{
		float mean = DailyMean(pos);
		if (Sheltered(garden))
			mean += SHELTER_WARMTH;
		return Math.Clamp((mean - GROW_MIN) / (GROW_FULL - GROW_MIN), 0, 1);
	}

	//! true when the frost of this moment kills a crop
	static bool Freezes(GardenBase garden, vector pos)
	{
		float now = g_Game.GetMission().GetWorldData().GetBaseEnvTemperatureAtPosition(pos);
		if (Sheltered(garden))
			return now <= SHELTER_FROST_KILL;
		return now <= FROST_KILL;
	}

	static float SnowDepth(vector pos)
	{
		return SZ_State.SnowAt(pos[1], SZ_State.s_Snow0, SZ_State.s_Snow1, SZ_State.s_Snow2);
	}

	//! outdoor soil that is frozen or under snow cannot be sown
	static bool GroundFrozen(GardenBase garden, vector pos)
	{
		if (Sheltered(garden))
			return false;
		if (DailyMean(pos) < 0)
			return true;
		return SnowDepth(pos) >= SNOW_COVER_CM;
	}

	//! the season's snow lies at this point: on the ground or on a frozen pond, not on a floor or a roof and not on
	//! open water
	static bool SnowCoverAt(vector pos)
	{
		float ground = g_Game.SurfaceY(pos[0], pos[2]);
		if (g_Game.SurfaceIsSea(pos[0], pos[2]))
			return false;
		float surface = ground;
		float water;
		if (SZ_Util.PondWater(pos[0], pos[2], water))
		{
			if (!FrozenPondAt(pos))
				return false;
			surface = water;
		}
		if (pos[1] > surface + 0.6)
			return false;
		return SnowDepth(Vector(pos[0], surface, pos[2])) >= SNOW_COVER_CM;
	}

	//! a pond whose ice carries snow: no open water there
	static bool FrozenPondAt(vector pos)
	{
		float water;
		if (!SZ_Util.PondWater(pos[0], pos[2], water))
			return false;
		return SZ_PondState.At(pos[0], pos[2], water);
	}

	//! a character standing on ice that carries people (not in the water under it)
	static bool OnIceAt(vector pos)
	{
		float water;
		if (!SZ_Util.PondWater(pos[0], pos[2], water))
			return false;
		if (pos[1] < water - 0.03)
			return false;
		return SZ_PondState.At(pos[0], pos[2], water);
	}

	//! wild food found in the cold: little of it left, nine in ten rotten (rose hips: dried)
	static void WildFoodInCold(Edible_Base food, bool keepsDried)
	{
		if (!food || !Active())
			return;
		float baseTemp = g_Game.GetMission().GetWorldData().GetBaseEnvTemperature();
		if (baseTemp > GameConstants.COLD_AREA_TEMPERATURE_THRESHOLD)
			return;
		float share = Math.RandomFloat(0.1, 0.8);
		food.SetQuantity(food.GetQuantityMax() * share);
		int roll = Math.RandomInt(0, 10);
		if (keepsDried || roll >= 9)
		{
			food.ChangeFoodStage(FoodStageType.DRIED);
			food.SetHealth("", "", food.GetMaxHealth() * 0.4);
		}
		else
		{
			food.ChangeFoodStage(FoodStageType.ROTTEN);
			food.SetHealth("", "", food.GetMaxHealth() * 0.1);
		}
	}
}

//! a player walking on thick pond ice stands on the ice, not in the water below it (no wet feet, no water cooling)
modded class Environment
{
	override protected void CheckWaterContact(out float pWaterLevel)
	{
		super.CheckWaterContact(pWaterLevel);
		if (!m_IsInWater || !m_Player || m_Player.IsSwimming() || !SZ_Winter.Active())
			return;
		if (!SZ_Winter.OnIceAt(m_Player.GetPosition()))
			return;
		m_IsInWater = false;
		pWaterLevel = 0;
		m_LiquidType = LIQUID_NONE;
		m_Player.SetInWater(false);
	}
}
//! crops: growth follows the temperature, hard frost kills them outdoors
modded class PlantBase
{
	override void Tick()
	{
		if (m_TimeTicker && SZ_Winter.Active())
		{
			GardenBase garden = GetGarden();
			if (m_PlantState == EPlantState.GROWING || m_PlantState == EPlantState.MATURE)
			{
				if (SZ_Winter.Freezes(garden, GetPosition()))
				{
					SetSpoiled();
					return;
				}
			}
			if (m_PlantState == EPlantState.GROWING)
			{
				float growth = SZ_Winter.GrowthFactor(garden, GetPosition());
				m_TimeTracker -= m_TimeTicker.GetDuration() * m_DebugTickSpeedMultiplier * (1.0 - growth);
			}
		}
		super.Tick();
	}
}

//! no sowing in frozen or snowed over soil outdoors
modded class GardenBase
{
	override bool CanPlantSeed(string selection_component)
	{
		if (!super.CanPlantSeed(selection_component))
			return false;
		if (SZ_Winter.Active() && SZ_Winter.GroundFrozen(this, GetPosition()))
			return false;
		return true;
	}
}

//! water and snow at the cursor: frozen ponds hold no open water, the season's snow cover is snow
modded class CCTWaterSurfaceEx
{
	override bool Can(PlayerBase player, ActionTarget target)
	{
		bool ok = super.Can(player, target);
		if (!target || target.GetObject() || !SZ_Winter.Active())
			return ok;
		vector hit = target.GetCursorHitPos();
		bool wantsSnow = (m_AllowedLiquidSource & LIQUID_SNOW) != 0;
		if (ok)
		{
			bool frozen = SZ_Winter.FrozenPondAt(hit);
			if (!frozen)
				return true;
			if (!wantsSnow)
				return false;
			bool snowOnIce = SZ_Winter.SnowCoverAt(hit);
			return snowOnIce;
		}
		if (!wantsSnow)
			return false;
		if (vector.DistanceSq(player.GetPosition(), hit) > m_MaximalActionDistanceSq)
			return false;
		bool snow = SZ_Winter.SnowCoverAt(hit);
		return snow;
	}
}

//! melting the season's snow in a pot or a bottle
modded class ActionFillBottleSnow
{
	override int GetLiquidType(PlayerBase player, ActionTarget target, ItemBase item)
	{
		int liquid = super.GetLiquidType(player, target, item);
		if (liquid != LIQUID_NONE || !target || target.GetObject() || !SZ_Winter.Active())
			return liquid;
		bool snow = SZ_Winter.SnowCoverAt(target.GetCursorHitPos());
		if (snow)
			return LIQUID_SNOW & m_AllowedLiquidMask;
		return liquid;
	}
}

// wild food of the season: berries and mushrooms appear dried or rotten in the cold
modded class SambucusBerry
{
	override void EEOnCECreate()
	{
		super.EEOnCECreate();
		SZ_Winter.WildFoodInCold(this, false);
	}
}

//! rose hips stay on the bushes through the winter, dried
modded class CaninaBerry
{
	override void EEOnCECreate()
	{
		super.EEOnCECreate();
		SZ_Winter.WildFoodInCold(this, true);
	}
}

modded class AgaricusMushroom
{
	override void EEOnCECreate()
	{
		super.EEOnCECreate();
		SZ_Winter.WildFoodInCold(this, false);
	}
}

modded class AmanitaMushroom
{
	override void EEOnCECreate()
	{
		super.EEOnCECreate();
		SZ_Winter.WildFoodInCold(this, false);
	}
}

modded class BoletusMushroom
{
	override void EEOnCECreate()
	{
		super.EEOnCECreate();
		SZ_Winter.WildFoodInCold(this, false);
	}
}

modded class LactariusMushroom
{
	override void EEOnCECreate()
	{
		super.EEOnCECreate();
		SZ_Winter.WildFoodInCold(this, false);
	}
}

modded class MacrolepiotaMushroom
{
	override void EEOnCECreate()
	{
		super.EEOnCECreate();
		SZ_Winter.WildFoodInCold(this, false);
	}
}

modded class PsilocybeMushroom
{
	override void EEOnCECreate()
	{
		super.EEOnCECreate();
		SZ_Winter.WildFoodInCold(this, false);
	}
}
