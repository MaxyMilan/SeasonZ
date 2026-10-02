class CfgPatches
{
	class DynamicSeasons
	{
		units[] = {};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] = {"DZ_Data", "DZ_Scripts"};
	};
};

class CfgMods
{
	class DynamicSeasons
	{
		dir = "DynamicSeasons";
		picture = "";
		action = "";
		hideName = 0;
		hidePicture = 1;
		name = "SeasonZ - Dynamic Seasons";
		credits = "";
		author = "Dynamic Seasons";
		authorID = "0";
		version = "0.4.0";
		extra = 0;
		type = "mod";
		dependencies[] = {"Game", "World", "Mission"};
		class defs
		{
			class gameScriptModule
			{
				value = "";
				files[] = {"DynamicSeasons/scripts/3_Game"};
			};
			class worldScriptModule
			{
				value = "";
				files[] = {"DynamicSeasons/scripts/4_World"};
			};
			class missionScriptModule
			{
				value = "";
				files[] = {"DynamicSeasons/scripts/5_Mission"};
			};
		};
	};
};

