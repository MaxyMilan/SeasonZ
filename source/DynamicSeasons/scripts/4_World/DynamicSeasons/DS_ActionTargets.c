//! Aiming at a seasonal tree model targets the real map tree behind it, so chopping and gathering keep working
modded class ActionTargets
{
	override protected array<int> SortResultsDistance(array<ref RaycastRVResult> results)
	{
		DS_TreeSwap.RemapRaycastResults(results);
		return super.SortResultsDistance(results);
	}
}

