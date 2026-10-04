//! Registers the entities that carry snow while they stand still (vehicles, tents, base parts, containers) with the
//! client's roof snow (SZ_RoofSnow), and the vehicles with the tyre tracks (SZ_TyreTracks). Barrels carry none: a
//! slab on their small round lid looks wrong
modded class CarScript
{
	override void EEInit()
	{
		super.EEInit();
		if (!g_Game.IsDedicatedServer())
		{
			SZ_RoofSnow.RegisterMovable(this);
			SZ_TyreTracks.Register(this);
		}
	}

	override void EEDelete(EntityAI parent)
	{
		SZ_RoofSnow.UnregisterMovable(this);
		SZ_TyreTracks.Unregister(this);
		super.EEDelete(parent);
	}
}

modded class TentBase
{
	override void EEInit()
	{
		super.EEInit();
		if (!g_Game.IsDedicatedServer())
			SZ_RoofSnow.RegisterMovable(this);
	}

	override void EEDelete(EntityAI parent)
	{
		SZ_RoofSnow.UnregisterMovable(this);
		super.EEDelete(parent);
	}
}

modded class BaseBuildingBase
{
	override void EEInit()
	{
		super.EEInit();
		if (!g_Game.IsDedicatedServer())
			SZ_RoofSnow.RegisterMovable(this);
	}

	override void EEDelete(EntityAI parent)
	{
		SZ_RoofSnow.UnregisterMovable(this);
		super.EEDelete(parent);
	}
}

modded class DeployableContainer_Base
{
	override void EEInit()
	{
		super.EEInit();
		if (!g_Game.IsDedicatedServer() && !IsInherited(Barrel_ColorBase))
			SZ_RoofSnow.RegisterMovable(this);
	}

	override void EEDelete(EntityAI parent)
	{
		SZ_RoofSnow.UnregisterMovable(this);
		super.EEDelete(parent);
	}
}

