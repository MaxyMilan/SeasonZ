class CfgPatches
{
	class SeasonZ
	{
		units[] = {};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] = {"DZ_Data", "DZ_Scripts"};
	};
};

class CfgMods
{
	class SeasonZ
	{
		dir = "SeasonZ";
		picture = "";
		action = "";
		hideName = 0;
		hidePicture = 1;
		name = "SeasonZ";
		credits = "";
		author = "SeasonZ";
		authorID = "0";
		version = "0.5.1";
		extra = 0;
		type = "mod";
		dependencies[] = {"Game", "World", "Mission"};
		class defs
		{
			class gameScriptModule
			{
				value = "";
				files[] = {"SeasonZ/scripts/3_Game"};
			};
			class worldScriptModule
			{
				value = "";
				files[] = {"SeasonZ/scripts/4_World"};
			};
			class missionScriptModule
			{
				value = "";
				files[] = {"SeasonZ/scripts/5_Mission"};
			};
		};
	};
};

