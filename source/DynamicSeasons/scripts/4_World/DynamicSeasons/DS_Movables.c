//! Registers the entities that carry snow while they stand still (vehicles, tents, base parts, containers) with the
//! client's roof snow (DS_RoofSnow), and the vehicles with the tyre tracks (DS_TyreTracks)
modded class CarScript
{
	override void EEInit()
	{
		super.EEInit();
		if (!g_Game.IsDedicatedServer())
		{
			DS_RoofSnow.RegisterMovable(this);
			DS_TyreTracks.Register(this);
		}
	}

	override void EEDelete(EntityAI parent)
	{
		DS_RoofSnow.UnregisterMovable(this);
		DS_TyreTracks.Unregister(this);
		super.EEDelete(parent);
	}
}

modded class TentBase
{
	override void EEInit()
	{
		super.EEInit();
		if (!g_Game.IsDedicatedServer())
			DS_RoofSnow.RegisterMovable(this);
	}

	override void EEDelete(EntityAI parent)
	{
		DS_RoofSnow.UnregisterMovable(this);
		super.EEDelete(parent);
	}
}

modded class BaseBuildingBase
{
	override void EEInit()
	{
		super.EEInit();
		if (!g_Game.IsDedicatedServer())
			DS_RoofSnow.RegisterMovable(this);
	}

	override void EEDelete(EntityAI parent)
	{
		DS_RoofSnow.UnregisterMovable(this);
		super.EEDelete(parent);
	}
}

modded class DeployableContainer_Base
{
	override void EEInit()
	{
		super.EEInit();
		if (!g_Game.IsDedicatedServer())
			DS_RoofSnow.RegisterMovable(this);
	}

	override void EEDelete(EntityAI parent)
	{
		DS_RoofSnow.UnregisterMovable(this);
		super.EEDelete(parent);
	}
}

