#include "sv_tdm.qh"

                                 
int autocvar_g_tdm_teams;
int autocvar_g_tdm_teams_override;

                                                              
                                                                                                                           
                                                                                                                                             
     
                                                                                                        
                                                                              
spawnfunc(tdm_team)
{
	if(!g_tdm || !this.cnt) { delete(this); return; }

	this.team = this.cnt + 1;
}

                                                                          
void tdm_SpawnTeam (string teamname, int teamcolor)
{
	entity this = new_pure(tdm_team);
	this.netname = teamname;
	this.cnt = teamcolor - 1;
	this.team = teamcolor;
	this.spawnfunc_checked = true;
	                           
}

void tdm_DelayedInit(entity this)
{
	                                        
	if(find(NULL, classname, "tdm_team") == NULL)
	{
		LOG_TRACE("No \"tdm_team\" entities found on this map, creating them anyway.");

		int numteams = autocvar_g_tdm_teams_override;
		if(numteams < 2) { numteams = autocvar_g_tdm_teams; }

		int teams = BITS(bound(2, numteams, 4));
		if(teams & BIT(0))
			tdm_SpawnTeam("Red", NUM_TEAM_1);
		if(teams & BIT(1))
			tdm_SpawnTeam("Blue", NUM_TEAM_2);
		if(teams & BIT(2))
			tdm_SpawnTeam("Yellow", NUM_TEAM_3);
		if(teams & BIT(3))
			tdm_SpawnTeam("Pink", NUM_TEAM_4);
	}
}

void tdm_Initialize()
{
	GameRules_teams(true);
	GameRules_spawning_teams(autocvar_g_tdm_team_spawns);
	GameRules_limit_score(autocvar_g_tdm_point_limit);
	GameRules_limit_lead(autocvar_g_tdm_point_leadlimit);

	InitializeEntity(NULL, tdm_DelayedInit, INITPRIO_GAMETYPE);
}

MUTATOR_HOOKFUNCTION(tdm, TeamBalance_CheckAllowedTeams, CBC_ORDER_EXCLUSIVE)
{
	M_ARGV(1, string) = "tdm_team";
}

MUTATOR_HOOKFUNCTION(tdm, Scores_CountFragsRemaining)
{
	                           
	return true;
}
