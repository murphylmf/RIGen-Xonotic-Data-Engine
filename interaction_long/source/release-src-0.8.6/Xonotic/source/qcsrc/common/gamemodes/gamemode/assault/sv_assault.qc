#include "sv_assault.qh"

#include <server/command/vote.qh>
#include <common/mapobjects/func/breakable.qh>
#include <common/mapobjects/triggers.qh>
#include <common/turrets/sv_turrets.qh>
#include <server/damage.qh>
#include <server/world.qh>
#include <server/spawnpoints.qh>

.entity sprite;
#define AS_ROUND_DELAY 5

                   
void assault_objective_use(entity this, entity actor, entity trigger)
{
	                     
	SetResourceExplicit(this, RES_HEALTH, 100);
	                                                                          
	                                                

	IL_EACH(g_assault_objectivedecreasers, it.target == this.targetname,
	{
		target_objective_decrease_activate(it);
	});
}

vector target_objective_spawn_evalfunc(entity this, entity player, entity spot, vector current)
{
	float hlth = GetResource(this, RES_HEALTH);
	if (hlth < 0 || hlth >= ASSAULT_VALUE_INACTIVE)
		return '-1 0 0';
	return current;
}

                                                        
                              
void assault_objective_reset(entity this)
{
	SetResourceExplicit(this, RES_HEALTH, ASSAULT_VALUE_INACTIVE);
}

                                             
void assault_objective_decrease_use(entity this, entity actor, entity trigger)
{
	if(actor.team != assault_attacker_team)
	{
		                                
		return;
	}

	if(trigger.assault_sprite)
	{
		WaypointSprite_Disown(trigger.assault_sprite, waypointsprite_deadlifetime);
		if(trigger.classname == "func_assault_destructible")
			trigger.sprite = NULL;                             
	}
	else
		return;                                             

	float hlth = GetResource(this.enemy, RES_HEALTH);
	if (hlth < ASSAULT_VALUE_INACTIVE)
	{
		if (hlth - this.dmg > 0.5)
		{
			GameRules_scoring_add_team(actor, SCORE, this.dmg);
			TakeResource(this.enemy, RES_HEALTH, this.dmg);
		}
		else
		{
			GameRules_scoring_add_team(actor, SCORE, hlth);
			GameRules_scoring_add_team(actor, ASSAULT_OBJECTIVES, 1);
			SetResourceExplicit(this.enemy, RES_HEALTH, -1);

			if(this.enemy.message)
				FOREACH_CLIENT(IS_PLAYER(it), { centerprint(it, this.enemy.message); });

			SUB_UseTargets(this.enemy, this, trigger);
		}
	}
}

void assault_setenemytoobjective(entity this)
{
	IL_EACH(g_assault_objectives, it.targetname == this.target,
	{
		if(this.enemy == NULL)
			this.enemy = it;
		else
			objerror(this, "more than one objective as target - fix the map!");
		break;
	});

	if(this.enemy == NULL)
		objerror(this, "no objective as target - fix the map!");
}

bool assault_decreaser_sprite_visible(entity this, entity player, entity view)
{
	if(GetResource(this.assault_decreaser.enemy, RES_HEALTH) >= ASSAULT_VALUE_INACTIVE)
		return false;

	return true;
}

void target_objective_decrease_activate(entity this)
{
	entity spr;
	this.owner = NULL;
	FOREACH_ENTITY_STRING(target, this.targetname,
	{
		if(it.assault_sprite != NULL)
		{
			WaypointSprite_Disown(it.assault_sprite, waypointsprite_deadlifetime);
			if(it.classname == "func_assault_destructible")
				it.sprite = NULL;                             
		}

		spr = WaypointSprite_SpawnFixed(WP_AssaultDefend, 0.5 * (it.absmin + it.absmax), it, assault_sprite, RADARICON_OBJECTIVE);
		spr.assault_decreaser = this;
		spr.waypointsprite_visible_for_player = assault_decreaser_sprite_visible;
		WaypointSprite_UpdateRule(spr, assault_attacker_team, SPRITERULE_TEAMPLAY);
		if(it.classname == "func_assault_destructible")
		{
			WaypointSprite_UpdateSprites(spr, WP_AssaultDefend, WP_AssaultDestroy, WP_AssaultDestroy);
			WaypointSprite_UpdateMaxHealth(spr, it.max_health);
			WaypointSprite_UpdateHealth(spr, GetResource(it, RES_HEALTH));
			it.sprite = spr;
		}
		else
			WaypointSprite_UpdateSprites(spr, WP_AssaultDefend, WP_AssaultPush, WP_AssaultPush);
	});
}

void target_objective_decrease_findtarget(entity this)
{
	assault_setenemytoobjective(this);
}

void target_assault_roundend_reset(entity this)
{
	                             
	++this.cnt;                    
	this.winning = false;            
}

void target_assault_roundend_use(entity this, entity actor, entity trigger)
{
	this.winning = 1;                                   
}

void assault_roundstart_use(entity this, entity actor, entity trigger)
{
	SUB_UseTargets(this, this, trigger);

	                       
	IL_EACH(g_turrets, true,
	{
		                    
		if(it.team == NUM_TEAM_1)
			it.team = NUM_TEAM_2;
		else
			it.team = NUM_TEAM_1;

		                        
		turret_respawn(it);
	});
}
void assault_roundstart_use_this(entity this)
{
	assault_roundstart_use(this, NULL, NULL);
}

void assault_wall_think(entity this)
{
	if(GetResource(this.enemy, RES_HEALTH) < 0)
	{
		this.model = "";
		this.solid = SOLID_NOT;
	}
	else
	{
		this.model = this.mdl;
		this.solid = SOLID_BSP;
	}

	this.nextthink = time + 0.2;
}

                    
                                                            
void assault_new_round(entity this)
{
	                   
	this.winning = this.winning + 1;

	                               
	if(assault_attacker_team == NUM_TEAM_1)
		assault_attacker_team = NUM_TEAM_2;
	else
		assault_attacker_team = NUM_TEAM_1;

	IL_EACH(g_saved_team, !IS_CLIENT(it),
	{
		if(it.team_saved == NUM_TEAM_1)
			it.team_saved = NUM_TEAM_2;
		else if(it.team_saved == NUM_TEAM_2)
			it.team_saved = NUM_TEAM_1;
	});

	                                   
	cvar_set("timelimit", ftos(ceil(time - AS_ROUND_DELAY - game_starttime) / 60));
	bprint("Starting second round...\n");
	ReadyRestart_force(true);                       
}

entity as_round;
.entity ent_winning;
void as_round_think()
{
	game_stopped = false;
	assault_new_round(as_round.ent_winning);
	delete(as_round);
	as_round = NULL;
}

                                                                                                   
                                                                         
int WinningCondition_Assault()
{
	if(as_round)
		return WINNING_NO;

	WinningConditionHelper(NULL);                   

	int status = WINNING_NO;
	                                                                              
	if(assault_attacker_team == NUM_TEAM_1)
	{
		SetWinners(team, NUM_TEAM_2);
	}
	else
	{
		SetWinners(team, NUM_TEAM_1);
	}

	entity ent;
	ent = find(NULL, classname, "target_assault_roundend");
	if(ent)
	{
		if(ent.winning)	                                                 
		{
			bprint(Team_ColoredFullName(assault_attacker_team), " destroyed the objective in ", process_time(2, ceil(time - game_starttime)), "\n");
			SetWinners(team, assault_attacker_team);

			TeamScore_AddToTeam(assault_attacker_team, ST_ASSAULT_OBJECTIVES, 666 - TeamScore_AddToTeam(assault_attacker_team, ST_ASSAULT_OBJECTIVES, 0));

			if(ent.cnt == 1 || autocvar_g_campaign)                                                           
			{
				status = WINNING_YES;
			}
			else
			{
				Send_Notification(NOTIF_ALL, NULL, MSG_CENTER, CENTER_ASSAULT_OBJ_DESTROYED, ceil(time - game_starttime));
				as_round = new(as_round);
				as_round.think = as_round_think;
				as_round.ent_winning = ent;
				as_round.nextthink = time + AS_ROUND_DELAY;
				game_stopped = true;

				                                                          
				if(autocvar_timelimit > 0)
				if(time + AS_ROUND_DELAY >= game_starttime + autocvar_timelimit * 60)
					cvar_set("timelimit", ftos(autocvar_timelimit + AS_ROUND_DELAY / 60));
			}
		}
	}

	return status;
}

             
spawnfunc(info_player_attacker)
{
	if (!g_assault) { delete(this); return; }

	this.team = NUM_TEAM_1;                                 
	spawnfunc_info_player_deathmatch(this);
}

spawnfunc(info_player_defender)
{
	if (!g_assault) { delete(this); return; }

	this.team = NUM_TEAM_2;                                  
	spawnfunc_info_player_deathmatch(this);
}

spawnfunc(target_objective)
{
	if (!g_assault) { delete(this); return; }

	IL_PUSH(g_assault_objectives, this);
	this.use = assault_objective_use;
	this.reset = assault_objective_reset;
	this.reset(this);
	this.spawn_evalfunc = target_objective_spawn_evalfunc;
}

spawnfunc(target_objective_decrease)
{
	if (!g_assault) { delete(this); return; }

	IL_PUSH(g_assault_objectivedecreasers, this);

	if(!this.dmg)
		this.dmg = 101;

	this.use = assault_objective_decrease_use;
	SetResourceExplicit(this, RES_HEALTH, ASSAULT_VALUE_INACTIVE);
	this.max_health = ASSAULT_VALUE_INACTIVE;
	this.enemy = NULL;

	InitializeEntity(this, target_objective_decrease_findtarget, INITPRIO_FINDTARGET);
}

                                                                           
bool destructible_heal(entity targ, entity inflictor, float amount, float limit)
{
	float true_limit = ((limit != RES_LIMIT_NONE) ? limit : targ.max_health);
	float hlth = GetResource(targ, RES_HEALTH);
	if (hlth <= 0 || hlth >= true_limit)
		return false;

	GiveResourceWithLimit(targ, RES_HEALTH, amount, true_limit);
	if(targ.sprite)
	{
		WaypointSprite_UpdateHealth(targ.sprite, GetResource(targ, RES_HEALTH));
	}
	func_breakable_colormod(targ);
	return true;
}

spawnfunc(func_assault_destructible)
{
	if (!g_assault) { delete(this); return; }

	this.spawnflags = 3;
	this.event_heal = destructible_heal;
	IL_PUSH(g_assault_destructibles, this);

	if(assault_attacker_team == NUM_TEAM_1)
		this.team = NUM_TEAM_2;
	else
		this.team = NUM_TEAM_1;

	func_breakable_setup(this);
}

spawnfunc(func_assault_wall)
{
	if (!g_assault) { delete(this); return; }

	this.mdl = this.model;
	_setmodel(this, this.mdl);
	this.solid = SOLID_BSP;
	setthink(this, assault_wall_think);
	this.nextthink = time;
	InitializeEntity(this, assault_setenemytoobjective, INITPRIO_FINDTARGET);
}

spawnfunc(target_assault_roundend)
{
	if (!g_assault) { delete(this); return; }

	this.winning = 0;                                  
	this.use = target_assault_roundend_use;
	this.cnt = 0;               
	this.reset = target_assault_roundend_reset;
}

spawnfunc(target_assault_roundstart)
{
	if (!g_assault) { delete(this); return; }

	assault_attacker_team = NUM_TEAM_1;
	this.use = assault_roundstart_use;
	this.reset2 = assault_roundstart_use_this;
	InitializeEntity(this, assault_roundstart_use_this, INITPRIO_FINDTARGET);
}

                  
void havocbot_goalrating_ast_targets(entity this, float ratingscale)
{
	IL_EACH(g_assault_destructibles, it.bot_attack,
	{
		if (it.target == "")
			continue;

		bool found = false;
		entity destr = it;
		IL_EACH(g_assault_objectivedecreasers, it.targetname == destr.target,
		{
			float hlth = GetResource(it.enemy, RES_HEALTH);
			if (hlth > 0 && hlth < ASSAULT_VALUE_INACTIVE)
			{
				found = true;
				break;
			}
		});

		if(!found)
			continue;

		vector p = 0.5 * (it.absmin + it.absmax);

		                                    
		found = false;
		entity best = NULL;
		float bestvalue = FLOAT_MAX;
		entity des = it;
		for (float radius = 500; radius <= 1500 && !found; radius += 500)
		{
			FOREACH_ENTITY_RADIUS(p, radius, it.classname == "waypoint" && !(it.wpflags & WAYPOINTFLAG_GENERATED),
			{
				if(checkpvs(it.origin, des))
				{
					found = true;
					if(it.cnt < bestvalue)
					{
						best = it;
						bestvalue = it.cnt;
					}
				}
			});
		}

		if(best)
		{
		                                                   
		                                             
		                               

			navigation_routerating(this, best, ratingscale, 4000);
			best.cnt += 1;

			this.havocbot_attack_time = 0;

			if(checkpvs(this.origin + this.view_ofs, it))
			if(checkpvs(this.origin + this.view_ofs, best))
			{
			                                                      
				this.havocbot_attack_time = time + 2;
			}
		}
	});
}

void havocbot_role_ast_offense(entity this)
{
	if(IS_DEAD(this))
	{
		this.havocbot_attack_time = 0;
		havocbot_ast_reset_role(this);
		return;
	}

	                                    
	if (!this.havocbot_role_timeout)
		this.havocbot_role_timeout = time + 120;

	if (time > this.havocbot_role_timeout)
	{
		havocbot_ast_reset_role(this);
		return;
	}

	if(this.havocbot_attack_time>time)
		return;

	if (navigation_goalrating_timeout(this))
	{
		                
		navigation_goalrating_start(this);
		havocbot_goalrating_enemyplayers(this, 10000, this.origin, 650);
		havocbot_goalrating_ast_targets(this, 20000);
		havocbot_goalrating_items(this, 30000, this.origin, 10000);
		navigation_goalrating_end(this);

		navigation_goalrating_timeout_set(this);
	}
}

void havocbot_role_ast_defense(entity this)
{
	if(IS_DEAD(this))
	{
		this.havocbot_attack_time = 0;
		havocbot_ast_reset_role(this);
		return;
	}

	                                    
	if (!this.havocbot_role_timeout)
		this.havocbot_role_timeout = time + 120;

	if (time > this.havocbot_role_timeout)
	{
		havocbot_ast_reset_role(this);
		return;
	}

	if(this.havocbot_attack_time>time)
		return;

	if (navigation_goalrating_timeout(this))
	{
		                
		navigation_goalrating_start(this);
		havocbot_goalrating_enemyplayers(this, 10000, this.origin, 3000);
		havocbot_goalrating_ast_targets(this, 20000);
		havocbot_goalrating_items(this, 30000, this.origin, 10000);
		navigation_goalrating_end(this);

		navigation_goalrating_timeout_set(this);
	}
}

void havocbot_role_ast_setrole(entity this, float role)
{
	switch(role)
	{
		case HAVOCBOT_AST_ROLE_DEFENSE:
			this.havocbot_role = havocbot_role_ast_defense;
			this.havocbot_role_timeout = 0;
			break;
		case HAVOCBOT_AST_ROLE_OFFENSE:
			this.havocbot_role = havocbot_role_ast_offense;
			this.havocbot_role_timeout = 0;
			break;
	}
}

void havocbot_ast_reset_role(entity this)
{
	if(IS_DEAD(this))
		return;

	if(this.team == assault_attacker_team)
		havocbot_role_ast_setrole(this, HAVOCBOT_AST_ROLE_OFFENSE);
	else
		havocbot_role_ast_setrole(this, HAVOCBOT_AST_ROLE_DEFENSE);
}

                
MUTATOR_HOOKFUNCTION(as, PlayerSpawn)
{
	entity player = M_ARGV(0, entity);

	if(player.team == assault_attacker_team)
		Send_Notification(NOTIF_ONE, player, MSG_CENTER, CENTER_ASSAULT_ATTACKING);
	else
		Send_Notification(NOTIF_ONE, player, MSG_CENTER, CENTER_ASSAULT_DEFENDING);
}

MUTATOR_HOOKFUNCTION(as, TurretSpawn)
{
	entity turret = M_ARGV(0, entity);

	if(!turret.team || turret.team == FLOAT_MAX)
		turret.team = assault_attacker_team;                                                                 
}

MUTATOR_HOOKFUNCTION(as, VehicleInit)
{
	entity veh = M_ARGV(0, entity);

	veh.nextthink = time + 0.5;
}

MUTATOR_HOOKFUNCTION(as, HavocBot_ChooseRole)
{
	entity bot = M_ARGV(0, entity);

	havocbot_ast_reset_role(bot);
	return true;
}

MUTATOR_HOOKFUNCTION(as, PlayHitsound)
{
	entity frag_victim = M_ARGV(0, entity);

	return (frag_victim.classname == "func_assault_destructible");
}

MUTATOR_HOOKFUNCTION(as, TeamBalance_CheckAllowedTeams)
{
	                             
	M_ARGV(0, float) = BIT(0) | BIT(1);
	return true;
}

MUTATOR_HOOKFUNCTION(as, CheckRules_World)
{
	M_ARGV(0, float) = WinningCondition_Assault();
	return true;
}

MUTATOR_HOOKFUNCTION(as, ReadLevelCvars)
{
	               
	warmup_stage = 0;
	sv_ready_restart_after_countdown = 0;
}

MUTATOR_HOOKFUNCTION(as, OnEntityPreSpawn)
{
	entity ent = M_ARGV(0, entity);

	switch(ent.classname)
	{
		case "info_player_team1":
		case "info_player_team2":
		case "info_player_team3":
		case "info_player_team4":
			return true;
	}
}

MUTATOR_HOOKFUNCTION(as, ReadyRestart_Deny)
{
	                                   
	                                                                                       
	if (autocvar_g_campaign)
		return false;
	return true;
}
