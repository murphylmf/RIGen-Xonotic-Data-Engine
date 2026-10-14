#include "capture.qh"

#include <common/deathtypes/all.qh>
#include <common/effects/qc/globalsound.qh>
#include <common/resources/sv_resources.qh>
#include <common/stats.qh>
#include <common/weapons/_all.qh>
#include <common/wepent.qh>
#include <server/client.qh>
#include <server/items/items.qh>
#include <server/teamplay.qh>
#include <server/weapons/selection.qh>
#include <server/weapons/weaponsystem.qh>

int capture_server_fh = -1;
int capture_server_tick;
int capture_next_event_id;
bool capture_server_started;
bool capture_server_done;
bool capture_server_tick_logged;
entity capture_player;
entity capture_enemy;
float capture_weapon_random_seed;
float capture_episode_seed_crc;
bool capture_episode_seed_header_seen;

#define CAPTURE_ACTION_COUNT 3908
#define CAPTURE_MAX_ENEMY_ACTORS 5
#define CAPTURE_OUTPUT_END_GRACE_TICKS 16
int capture_action_count;
int capture_action_fh = -1;
bool capture_action_ready;
int capture_action_tick;
float capture_action_forward;
float capture_action_strafe;
float capture_action_pitch;
float capture_action_yaw;
int capture_action_jump;
int capture_action_primary;
int capture_action_secondary;
int capture_action_impulse;
int capture_action_reload;

entity capture_enemy_actors[CAPTURE_MAX_ENEMY_ACTORS];
int capture_enemy_actor_count;
int capture_active_actor_slot;
int capture_timeline_actor_declared[CAPTURE_MAX_ENEMY_ACTORS];
string capture_timeline_actor_id[CAPTURE_MAX_ENEMY_ACTORS];
string capture_timeline_actor_model[CAPTURE_MAX_ENEMY_ACTORS];
int capture_timeline_actor_skin[CAPTURE_MAX_ENEMY_ACTORS];
int capture_timeline_actor_color[CAPTURE_MAX_ENEMY_ACTORS];
float capture_timeline_actor_health[CAPTURE_MAX_ENEMY_ACTORS];
float capture_timeline_actor_armor[CAPTURE_MAX_ENEMY_ACTORS];
float capture_timeline_actor_runtime_health[CAPTURE_MAX_ENEMY_ACTORS];
float capture_timeline_actor_runtime_armor[CAPTURE_MAX_ENEMY_ACTORS];
int capture_timeline_fh = -1;
bool capture_timeline_tick_ready;
int capture_timeline_tick;
int capture_timeline_current_actor_slot;
vector capture_timeline_current_origin;
vector capture_timeline_current_velocity;
float capture_timeline_current_yaw;
int capture_timeline_current_jump;

vector capture_prev_player_origin;
vector capture_prev_player_velocity;
vector capture_prev_player_angles;
float capture_prev_player_health;
float capture_prev_player_armor;
float capture_prev_player_clip;
float capture_prev_player_reserve;
vector capture_prev_enemy_step_origin;
float capture_enemy_step_distance;
int capture_enemy_step_index;
bool capture_enemy_death_latched;
vector capture_enemy_death_origin;

void Capture_Log(string text)
{
	if(capture_server_fh >= 0)
	{
		fputs(capture_server_fh, text);
		fputs(capture_server_fh, "\n");
	}
}

int Capture_NewEvent()
{
	return capture_next_event_id++;
}

float Capture_Reserve(entity actor, Weapon weapon)
{
	if(weapon == WEP_Null || weapon.ammo_type == RES_NONE)
		return 0;
	return GetResource(actor, weapon.ammo_type);
}

float Capture_WeaponRandom()
{
	float value = crc16(false,
		strcat(ftos(capture_weapon_random_seed),
			ftos(capture_weapon_random_seed + M_PI)));
	capture_weapon_random_seed = value;
	return value / 65536;
}

vector Capture_WeaponSpreadRandom(entity actor)
{
	if(!autocvar_capture_server_enable || actor != capture_player)
		return randomvec();
	vector value;
	do
	{
		value.x = Capture_WeaponRandom() * 2 - 1;
		value.y = Capture_WeaponRandom() * 2 - 1;
		value.z = Capture_WeaponRandom() * 2 - 1;
	}
	while(value * value > 1);
	return value;
}

void Capture_SetResources(entity actor, float health, float armor, float reserve)
{
	SetResourceExplicit(actor, RES_HEALTH, health);
	SetResourceExplicit(actor, RES_ARMOR, armor);
	SetResourceExplicit(actor, RES_BULLETS, reserve);
	SetResourceExplicit(actor, RES_SHELLS, reserve);
	SetResourceExplicit(actor, RES_CELLS, reserve);
	SetResourceExplicit(actor, RES_ROCKETS, reserve);
	SetResourceExplicit(actor, RES_PLASMA, reserve);
	SetResourceExplicit(actor, RES_FUEL, reserve);
}

bool Capture_ParseAuthoritativeAction(string line, int expected_tick)
{
	int fields = tokenizebyseparator(line, ",");
	if(fields != 10)
		return false;
	int tick = stoi(argv(0));
	if(tick != expected_tick)
		return false;
	capture_action_tick = tick;
	capture_action_forward = stof(argv(1));
	capture_action_strafe = stof(argv(2));
	capture_action_yaw += stof(argv(3));
	capture_action_pitch = bound(
		-89, capture_action_pitch + stof(argv(4)), 89);
	capture_action_jump = stoi(argv(5));
	capture_action_primary = stoi(argv(6));
	capture_action_secondary = stoi(argv(7));
	capture_action_impulse = stoi(argv(8));
	capture_action_reload = stoi(argv(9));
	capture_action_ready = true;
	return true;
}

bool Capture_LoadAuthoritativeActions()
{
	if(capture_action_fh >= 0)
		fclose(capture_action_fh);
	capture_action_fh = fopen(
		autocvar_capture_server_action_file, FILE_READ);
	if(capture_action_fh < 0)
	{
		LOG_WARN("capture: could not read authoritative action file ",
			autocvar_capture_server_action_file);
		return false;
	}
	capture_action_count = CAPTURE_ACTION_COUNT;
	capture_action_ready = false;
	capture_episode_seed_crc = 0;
	capture_episode_seed_header_seen = false;
	capture_weapon_random_seed = 0;
	capture_action_yaw = autocvar_capture_player_yaw;
	capture_action_pitch = autocvar_capture_player_pitch;
	for(string line; (line = fgets(capture_action_fh)); )
	{
		if(substring(line, 0, 6) == "#seed,")
		{
			capture_episode_seed_crc = crc16(false, line);
			capture_weapon_random_seed = capture_episode_seed_crc;
			capture_episode_seed_header_seen = true;
			continue;
		}
		if(line == "" || substring(line, 0, 5) == "tick,")
			continue;
		if(!capture_episode_seed_header_seen
			|| !Capture_ParseAuthoritativeAction(line, 0))
		{
			fclose(capture_action_fh);
			capture_action_fh = -1;
			LOG_WARN("capture: invalid authoritative action row ", line);
			capture_action_count = 0;
			return false;
		}
		LOG_INFOF("capture: opened %d authoritative server actions from %s",
			CAPTURE_ACTION_COUNT, autocvar_capture_server_action_file);
		return true;
	}
	fclose(capture_action_fh);
	capture_action_fh = -1;
	capture_action_count = 0;
	LOG_WARN("capture: authoritative action file contains no action rows");
	return false;
}

bool Capture_ParseEnemyTimelineTick(string line, int expected_tick)
{
	int fields = tokenizebyseparator(line, ",");
	if(fields != 11 || argv(0) != "tick")
		return false;
	int tick = stoi(argv(1));
	int actor_slot = stoi(argv(2));
	if(tick != expected_tick || actor_slot < 0
		|| actor_slot > autocvar_capture_enemy_actor_count)
		return false;
	capture_timeline_tick = tick;
	capture_timeline_current_actor_slot = actor_slot;
	capture_timeline_current_origin =
		'1 0 0' * stof(argv(3))
		+ '0 1 0' * stof(argv(4))
		+ '0 0 1' * stof(argv(5));
	capture_timeline_current_velocity =
		'1 0 0' * stof(argv(6))
		+ '0 1 0' * stof(argv(7))
		+ '0 0 1' * stof(argv(8));
	capture_timeline_current_yaw = stof(argv(9));
	capture_timeline_current_jump = stoi(argv(10));
	capture_timeline_tick_ready = true;
	return true;
}

bool Capture_LoadEnemyTimeline()
{
	if(!autocvar_capture_enemy_timeline_enable)
		return true;
	int requested_actors = autocvar_capture_enemy_actor_count;
	if(requested_actors < 2 || requested_actors > CAPTURE_MAX_ENEMY_ACTORS)
	{
		LOG_WARNF("capture: invalid enemy actor count %d", requested_actors);
		return false;
	}
	for(int actor_index = 0; actor_index < CAPTURE_MAX_ENEMY_ACTORS; ++actor_index)
	{
		capture_timeline_actor_declared[actor_index] = 0;
		if(capture_timeline_actor_id[actor_index] != "")
			strunzone(capture_timeline_actor_id[actor_index]);
		if(capture_timeline_actor_model[actor_index] != "")
			strunzone(capture_timeline_actor_model[actor_index]);
		capture_timeline_actor_id[actor_index] = "";
		capture_timeline_actor_model[actor_index] = "";
	}
	if(capture_timeline_fh >= 0)
		fclose(capture_timeline_fh);
	capture_timeline_fh = fopen(
		autocvar_capture_enemy_timeline_file, FILE_READ);
	if(capture_timeline_fh < 0)
	{
		LOG_WARN("capture: could not read enemy timeline file ",
			autocvar_capture_enemy_timeline_file);
		return false;
	}
	capture_timeline_tick_ready = false;
	for(string line; (line = fgets(capture_timeline_fh)); )
	{
		if(line == "" || substring(line, 0, 5) == "kind,")
			continue;
		int fields = tokenizebyseparator(line, ",");
		string kind = argv(0);
		if(kind == "actor")
		{
			if(fields != 8)
			{
				fclose(capture_timeline_fh);
				capture_timeline_fh = -1;
				LOG_WARN("capture: invalid enemy actor row ", line);
				return false;
			}
			int slot = stoi(argv(1));
			if(slot < 1 || slot > requested_actors
				|| capture_timeline_actor_declared[slot - 1])
			{
				fclose(capture_timeline_fh);
				capture_timeline_fh = -1;
				LOG_WARN("capture: invalid enemy actor slot row ", line);
				return false;
			}
			capture_timeline_actor_declared[slot - 1] = 1;
			capture_timeline_actor_id[slot - 1] = strzone(argv(2));
			capture_timeline_actor_model[slot - 1] = strzone(argv(3));
			capture_timeline_actor_skin[slot - 1] = stoi(argv(4));
			capture_timeline_actor_color[slot - 1] = stoi(argv(5));
			capture_timeline_actor_health[slot - 1] = stof(argv(6));
			capture_timeline_actor_armor[slot - 1] = stof(argv(7));
			capture_timeline_actor_runtime_health[slot - 1] = stof(argv(6));
			capture_timeline_actor_runtime_armor[slot - 1] = stof(argv(7));
			continue;
		}
		for(int declared_index = 0;
			declared_index < requested_actors; ++declared_index)
		{
			if(!capture_timeline_actor_declared[declared_index])
			{
				fclose(capture_timeline_fh);
				capture_timeline_fh = -1;
				LOG_WARNF("capture: missing enemy actor declaration %d",
					declared_index + 1);
				return false;
			}
		}
		if(!Capture_ParseEnemyTimelineTick(line, 0))
		{
			fclose(capture_timeline_fh);
			capture_timeline_fh = -1;
			LOG_WARN("capture: invalid first enemy timeline tick ", line);
			return false;
		}
		LOG_INFOF("capture: loaded %d enemy actors and opened timeline %s",
			requested_actors, autocvar_capture_enemy_timeline_file);
		return true;
	}
	fclose(capture_timeline_fh);
	capture_timeline_fh = -1;
	LOG_WARN("capture: enemy timeline contains no tick rows");
	return false;
}

void Capture_ApplyAuthoritativeAction(entity actor)
{
	if(!autocvar_capture_server_enable || actor != capture_player)
		return;
	actor.capture_physics_ready = true;
	if(!capture_server_started || capture_server_done
		|| capture_server_tick < 0 || capture_server_tick >= capture_action_count
		|| !capture_action_ready
		|| capture_action_tick != capture_server_tick)
		return;
	CS(actor).movement = '1 0 0' * capture_action_forward
		+ '0 1 0' * capture_action_strafe;
	actor.v_angle = '1 0 0' * capture_action_pitch
		+ '0 1 0' * capture_action_yaw;
	actor.angles = actor.v_angle;
	actor.fixangle = true;
	PHYS_INPUT_BUTTON_JUMP(actor) = capture_action_jump;
	PHYS_INPUT_BUTTON_ATCK(actor) = capture_action_primary;
	PHYS_INPUT_BUTTON_ATCK2(actor) = capture_action_secondary;
	CS(actor).impulse = capture_action_reload
		? 20 : capture_action_impulse;
}

void Capture_ResetActor(entity actor, vector origin, float pitch, float yaw)
{
	setorigin(actor, origin);
	actor.velocity = '0 0 0';
	actor.avelocity = '0 0 0';
	actor.oldvelocity = '0 0 0';
	actor.angles = '1 0 0' * pitch + '0 1 0' * yaw;
	actor.v_angle = actor.angles;
	actor.fixangle = true;
	actor.deadflag = DEAD_NO;
}

void Capture_SetEnemyActorVisible(entity actor, bool visible)
{
	actor.move_qcphysics = false;
	set_movetype(actor, MOVETYPE_NONE);
	actor.velocity = '0 0 0';
	actor.oldvelocity = '0 0 0';
	actor.avelocity = '0 0 0';
	PHYS_INPUT_BUTTON_ATCK(actor) = false;
	PHYS_INPUT_BUTTON_ATCK2(actor) = false;
	PHYS_INPUT_BUTTON_JUMP(actor) = false;
	if(visible)
	{
		actor.effects &= ~EF_NODRAW;
		actor.solid = SOLID_SLIDEBOX;
		actor.takedamage = GetResource(actor, RES_HEALTH) >= 1
			? DAMAGE_AIM : DAMAGE_NO;
	}
	else
	{
		actor.effects |= EF_NODRAW;
		actor.solid = SOLID_NOT;
		actor.takedamage = DAMAGE_NO;
	}
}

void Capture_ConfigurePlayerWeapon(entity actor)
{
	Weapon weapon = Weapon_from_name(autocvar_capture_weapon);
	if(weapon == WEP_Null)
		weapon = WEP_MACHINEGUN;
	STAT(WEAPONS, actor) = weapon.m_wepset;
	W_GiveWeapon(actor, weapon.m_id);
	W_SwitchWeapon_Force(actor, weapon, weaponentities[0]);
	entity weapon_entity = actor.(weaponentities[0]);
	weapon_entity.m_weapon = weapon;
	weapon_entity.m_switchweapon = weapon;
	weapon_entity.clip_load = autocvar_capture_clip;
	weapon_entity.old_clip_load = autocvar_capture_clip;
	weapon_entity.(weapon_load[weapon.m_id]) = autocvar_capture_clip;
}

bool Capture_TryReset()
{
	capture_player = NULL;
	capture_enemy = NULL;
	capture_enemy_actor_count = 0;
	FOREACH_CLIENT(IS_REAL_CLIENT(it) && IS_PLAYER(it),
	{
		capture_player = it;
		break;
	});
	FOREACH_CLIENT(IS_BOT_CLIENT(it) && IS_PLAYER(it),
	{
		if(capture_enemy_actor_count < CAPTURE_MAX_ENEMY_ACTORS)
		{
			capture_enemy_actors[capture_enemy_actor_count] = it;
			++capture_enemy_actor_count;
		}
	});
	if(capture_enemy_actor_count > 0)
		capture_enemy = capture_enemy_actors[0];
	if(capture_enemy)
		capture_enemy.capture_identity_locked = false;
	if(!capture_player
		|| (autocvar_capture_enemy_present && !capture_enemy))
		return false;
	                                                                          
	                                                                     
	                                                       
	if(capture_player.move_movetype != MOVETYPE_WALK
		|| !capture_player.capture_physics_ready)
		return false;

	cvar_set("bot_nofire", "1");
	                                                                      
	                                                                        
	                                                                      
	                                                           
	if(!autocvar_capture_enemy_present && capture_enemy)
	{
		cvar_set("bot_number", "0");
		dropclient(capture_enemy);
		capture_enemy = NULL;
	}
	if(!Capture_LoadEnemyTimeline())
		return false;
	Capture_ResetActor(capture_player, autocvar_capture_player_origin,
		autocvar_capture_player_pitch, autocvar_capture_player_yaw);
	Capture_SetResources(capture_player,
		autocvar_capture_player_health,
		autocvar_capture_player_armor,
		autocvar_capture_reserve);
	if(autocvar_capture_enemy_present
		&& !autocvar_capture_enemy_timeline_enable)
	{
		Capture_ResetActor(capture_enemy,
			autocvar_capture_enemy_origin, 0, autocvar_capture_enemy_yaw);
		                                                               
		                                                                      
		                                                                     
		capture_enemy.move_qcphysics = false;
		capture_enemy.respawn_flags |= RESPAWN_DENY;
		set_movetype(capture_enemy, MOVETYPE_NONE);
		Capture_SetResources(capture_enemy,
			autocvar_capture_enemy_health,
			autocvar_capture_enemy_armor,
			autocvar_capture_reserve);
	}
	                                                                        
	                                                                        
	                                                                          
	                                        
	Capture_ConfigurePlayerWeapon(capture_player);
	if(autocvar_capture_enemy_present
		&& autocvar_capture_enemy_timeline_enable)
	{
		  
                                                                           
                                                                             
                                                                          
                                                                             
                                                            
     
		if(teamplay)
		{
			int player_team_index = Entity_GetTeamIndex(capture_player);
			if(!Team_IsValidIndex(player_team_index))
				return false;
			int enemy_team_index = Entity_GetTeamIndex(capture_enemy);
			                                                                
			                                                                       
			                                                                    
			                                                                     
			                                                                      
			                                                               
			if(!Team_IsValidIndex(enemy_team_index)
				|| enemy_team_index == player_team_index)
			{
				enemy_team_index = player_team_index == 1 ? 2 : 1;
				if(!Player_SetTeamIndex(capture_enemy, enemy_team_index))
					return false;
			}
		}
		capture_enemy.capture_identity_locked = true;
		Capture_ResetActor(capture_enemy,
			autocvar_capture_enemy_origin, 0,
			autocvar_capture_enemy_yaw);
		capture_enemy.move_qcphysics = false;
		capture_enemy.respawn_flags |= RESPAWN_DENY;
		set_movetype(capture_enemy, MOVETYPE_NONE);
		Capture_SetResources(capture_enemy,
			capture_timeline_actor_runtime_health[0],
			capture_timeline_actor_runtime_armor[0],
			autocvar_capture_reserve);
		setplayermodel(capture_enemy,
			strcat("models/player/",
				capture_timeline_actor_model[0], ".iqm"));
		                                                                       
		                                                                      
		                                                                      
		                                                                  
		setsize(capture_enemy, STAT(PL_MIN, capture_enemy),
			STAT(PL_MAX, capture_enemy));
		capture_enemy.skin = capture_timeline_actor_skin[0];
		capture_enemy.clientcolors = capture_timeline_actor_color[0];
		capture_enemy.colormap = 1024 + capture_timeline_actor_color[0];
		Capture_ConfigurePlayerWeapon(capture_enemy);
		Capture_SetEnemyActorVisible(capture_enemy, false);
		capture_active_actor_slot = 0;
	}
	else if(autocvar_capture_enemy_present)
	{
		setplayermodel(capture_enemy,
			strcat("models/player/", autocvar_capture_enemy_model, ".iqm"));
		setsize(capture_enemy, STAT(PL_MIN, capture_enemy),
			STAT(PL_MAX, capture_enemy));
		capture_enemy.skin = autocvar_capture_enemy_skin;
		capture_enemy.clientcolors = autocvar_capture_enemy_color;
		capture_enemy.colormap = 1024 + autocvar_capture_enemy_color;
		PHYS_INPUT_BUTTON_ATCK(capture_enemy) = false;
		PHYS_INPUT_BUTTON_ATCK2(capture_enemy) = false;
		PHYS_INPUT_BUTTON_JUMP(capture_enemy) = false;
	}

	if(!Capture_LoadAuthoritativeActions())
		return false;
	if(capture_server_fh >= 0)
		fclose(capture_server_fh);
	capture_server_fh = fopen(autocvar_capture_server_log, FILE_WRITE);
	if(capture_server_fh < 0)
	{
		LOG_WARN("capture: could not open server telemetry ", autocvar_capture_server_log);
		return false;
	}
	capture_server_tick = 0;
	capture_next_event_id = 1;
	capture_server_started = true;
	capture_server_done = false;
	capture_server_tick_logged = false;
	capture_prev_player_origin = capture_player.origin;
	capture_prev_player_velocity = capture_player.velocity;
	capture_prev_player_angles = capture_player.v_angle;
	capture_prev_player_health = GetResource(capture_player, RES_HEALTH);
	capture_prev_player_armor = GetResource(capture_player, RES_ARMOR);
	entity weapon_entity = capture_player.(weaponentities[0]);
	capture_prev_player_clip = weapon_entity.clip_load;
	capture_prev_player_reserve = Capture_Reserve(capture_player, weapon_entity.m_weapon);
	capture_prev_enemy_step_origin = autocvar_capture_enemy_present
		? capture_enemy.origin : '0 0 0';
	capture_enemy_step_distance = 0;
	capture_enemy_step_index = 0;
	capture_enemy_death_latched = false;
	capture_enemy_death_origin = autocvar_capture_enemy_present
		? capture_enemy.origin : '0 0 0';

	vector anchor_mins = PL_MIN_CONST + '0.1 0.1 0.1';
	vector anchor_maxs = PL_MAX_CONST - '0.1 0.1 0.1';
	tracebox(capture_player.origin, anchor_mins, anchor_maxs,
		capture_player.origin, MOVE_WORLDONLY, capture_player);
	bool player_clear = !trace_startsolid && !trace_allsolid;
	tracebox(capture_player.origin + '0 0 1', anchor_mins, anchor_maxs,
		capture_player.origin - '0 0 96', MOVE_WORLDONLY, capture_player);
	bool player_ground = !trace_startsolid && trace_fraction < 1;
	float player_ground_distance = capture_player.origin.z - trace_endpos.z;
	bool enemy_clear = false;
	bool enemy_ground = false;
	float enemy_ground_distance = 0;
	float anchor_los_fraction = 0;
	if(autocvar_capture_enemy_present)
	{
		tracebox(capture_enemy.origin, anchor_mins, anchor_maxs,
			capture_enemy.origin, MOVE_WORLDONLY, capture_enemy);
		enemy_clear = (!trace_startsolid && !trace_allsolid);
		tracebox(capture_enemy.origin + '0 0 1', anchor_mins, anchor_maxs,
			capture_enemy.origin - '0 0 96', MOVE_WORLDONLY, capture_enemy);
		enemy_ground = (!trace_startsolid && trace_fraction < 1);
		enemy_ground_distance = capture_enemy.origin.z - trace_endpos.z;
		traceline(capture_player.origin + '0 0 24',
			capture_enemy.origin + '0 0 24',
			MOVE_WORLDONLY, capture_player);
		anchor_los_fraction = trace_fraction;
	}

	string reset_row = sprintf(
		"{\"kind\":\"reset\",\"episode_id\":\"%s\",\"server_time\":%.9f,"
		"\"server_tick\":0,\"map\":\"%s\",\"player_entity\":%d,"
		"\"enemy_present\":%d,\"enemy_entity\":%d,"
		"\"weapon\":\"%s\",\"enemy_model\":\"%s\","
		"\"enemy_skin\":%d,\"enemy_color\":%d,",
		autocvar_capture_episode_id, time, GetMapname(),
		etof(capture_player), autocvar_capture_enemy_present,
		(autocvar_capture_enemy_present ? etof(capture_enemy) : 0),
		autocvar_capture_weapon,
		(autocvar_capture_enemy_present ? autocvar_capture_enemy_model : ""),
		(autocvar_capture_enemy_present ? autocvar_capture_enemy_skin : -1),
		(autocvar_capture_enemy_present ? autocvar_capture_enemy_color : -1));
	reset_row = strcat(reset_row, sprintf(
		"\"seed_header_seen\":%d,\"seed_crc\":%.0f,"
		"\"weapon_rng_seed\":%.6f,",
		capture_episode_seed_header_seen, capture_episode_seed_crc,
		capture_weapon_random_seed));
	reset_row = strcat(reset_row, sprintf(
		"\"anchor\":{\"id\":\"%s\",\"player_clear\":%d,\"enemy_clear\":%d,"
		"\"player_ground\":%d,\"enemy_ground\":%d,"
		"\"player_ground_distance\":%.6f,",
		autocvar_capture_anchor_id,
		player_clear, enemy_clear, player_ground, enemy_ground,
		player_ground_distance));
	reset_row = strcat(reset_row, sprintf(
		"\"enemy_ground_distance\":%.6f,\"los_fraction\":%.9f}}",
		enemy_ground_distance, anchor_los_fraction));
	Capture_Log(reset_row);
	if(autocvar_capture_enemy_present)
	{
		string policy_row = sprintf(
			"{\"kind\":\"enemy_policy\",\"episode_id\":\"%s\","
			"\"policy\":\"%s\",\"policy_seed\":%d,\"motion_mode\":%d,"
			"\"motion_start_tick\":%d,\"motion_distance\":%.6f,"
			"\"reads_camera\":false,\"reads_crosshair\":false,"
			"\"reads_live_player_state\":false,\"fires\":false,"
			"\"jumps\":%d,",
			autocvar_capture_episode_id, autocvar_capture_enemy_policy,
			autocvar_capture_enemy_policy_seed,
			autocvar_capture_enemy_motion,
			autocvar_capture_enemy_motion_start_tick,
			autocvar_capture_enemy_motion_distance,
			autocvar_capture_enemy_jump_enabled);
		policy_row = strcat(policy_row, sprintf(
			"\"movement_audio\":\"native_surface_footsteps_v1\","
			"\"movement_audio_enabled\":%d,\"step_stride\":%.6f}",
			autocvar_capture_enemy_movement_audio,
			autocvar_capture_enemy_step_stride));
		Capture_Log(policy_row);
		if(autocvar_capture_enemy_motion == 5)
		{
			string program_row = sprintf(
				"{\"kind\":\"enemy_motion_program\",\"episode_id\":\"%s\","
				"\"schema_version\":\"xonotic-stage2-enemy-motion-program-v1\","
				"\"speed_units_per_second\":%.6f,\"block_seconds\":%.6f,",
				autocvar_capture_episode_id,
				autocvar_capture_enemy_motion_speed,
				autocvar_capture_enemy_motion_block_seconds);
			program_row = strcat(program_row, sprintf(
				"\"direction_codes\":[%d,%d,%d,%d,%d],",
				autocvar_capture_enemy_motion_block_0,
				autocvar_capture_enemy_motion_block_1,
				autocvar_capture_enemy_motion_block_2,
				autocvar_capture_enemy_motion_block_3,
				autocvar_capture_enemy_motion_block_4));
			program_row = strcat(program_row,
				"\"code_meanings\":{\"0\":\"stationary\","
				"\"1\":\"player_left\",\"2\":\"player_right\","
				"\"3\":\"toward_player\",\"4\":\"away_from_player\"},"
				"\"reads_camera\":false,\"reads_live_player_state\":false}");
			Capture_Log(program_row);
			if(autocvar_capture_enemy_jump_enabled)
			{
				Capture_Log(sprintf(
					"{\"kind\":\"enemy_jump_program\",\"episode_id\":\"%s\","
					"\"schema_version\":\"xonotic-stage2-enemy-jump-program-v1\","
					"\"height_units\":%.6f,\"duration_ticks\":%d,"
					"\"start_tick_in_block\":%d,\"jump_blocks\":[%d,%d,%d,%d,%d],"
					"\"reads_camera\":false,\"reads_live_player_state\":false}",
					autocvar_capture_episode_id,
					autocvar_capture_enemy_jump_height,
					autocvar_capture_enemy_jump_duration_ticks,
					autocvar_capture_enemy_jump_start_tick_in_block,
					autocvar_capture_enemy_jump_block_0,
					autocvar_capture_enemy_jump_block_1,
					autocvar_capture_enemy_jump_block_2,
					autocvar_capture_enemy_jump_block_3,
					autocvar_capture_enemy_jump_block_4));
			}
		}
	}
	stuffcmd(capture_player,
		sprintf("\ncapture_episode_reset \"%s\"\n", autocvar_capture_episode_id));
	return true;
}

void Capture_AdvanceEnemyFootsteps(vector target)
{
	float segment_distance = vlen(target - capture_prev_enemy_step_origin);
	capture_prev_enemy_step_origin = target;
	if(!autocvar_capture_enemy_movement_audio
		|| autocvar_capture_enemy_motion == 0)
		return;
	float stride = max(8, autocvar_capture_enemy_step_stride);
	capture_enemy_step_distance += segment_distance;
	if(capture_enemy_step_distance < stride)
		return;
	capture_enemy_step_distance -= stride;

	trace_dphitq3surfaceflags = 0;
	tracebox(capture_enemy.origin, capture_enemy.mins, capture_enemy.maxs,
		capture_enemy.origin - '0 0 1', MOVE_NOMONSTERS, capture_enemy);
	if(trace_dphitq3surfaceflags & Q3SURFACEFLAG_NOSTEPS)
		return;
	bool metal = boolean(
		trace_dphitq3surfaceflags & Q3SURFACEFLAG_METALSTEPS);
	entity gs = (metal ? GS_STEP_METAL : GS_STEP);
	int variant = (
		autocvar_capture_enemy_policy_seed
		+ capture_enemy_step_index * 5
	) % 6;
	float variant_r = (variant + 0.5) / 6;
	string sample = GlobalSound_sample(gs.m_globalsoundstr, variant_r);
	int event_id = Capture_NewEvent();
	string row = sprintf(
		"{\"kind\":\"event\",\"event\":\"enemy_footstep\","
		"\"event_id\":%d,\"parent_event_id\":null,"
		"\"server_tick\":%d,\"server_time\":%.9f,"
		"\"source_entity\":%d,",
		event_id, capture_server_tick, time, etof(capture_enemy));
	row = strcat(row, sprintf(
		"\"surface\":\"%s\",\"variant\":%d,\"sample\":\"%s\","
		"\"stride\":%.6f,",
		(metal ? "metal" : "standard"), variant + 1, sample, stride));
	row = strcat(row, sprintf(
		"\"position\":[%.6f,%.6f,%.6f]}",
		capture_enemy.origin.x, capture_enemy.origin.y,
		capture_enemy.origin.z));
	Capture_Log(row);
	GlobalSound_fixed_variant(
		capture_enemy, gs, variant_r, CH_PLAYER, VOL_BASE);
	++capture_enemy_step_index;
}

int Capture_EnemyMotionBlockCode(int block)
{
	switch(block)
	{
		case 0: return autocvar_capture_enemy_motion_block_0;
		case 1: return autocvar_capture_enemy_motion_block_1;
		case 2: return autocvar_capture_enemy_motion_block_2;
		case 3: return autocvar_capture_enemy_motion_block_3;
		case 4: return autocvar_capture_enemy_motion_block_4;
	}
	return 0;
}

int Capture_EnemyJumpBlockEnabled(int block)
{
	switch(block)
	{
		case 0: return autocvar_capture_enemy_jump_block_0;
		case 1: return autocvar_capture_enemy_jump_block_1;
		case 2: return autocvar_capture_enemy_jump_block_2;
		case 3: return autocvar_capture_enemy_jump_block_3;
		case 4: return autocvar_capture_enemy_jump_block_4;
	}
	return 0;
}

void Capture_StopEnemyMotion()
{
	capture_enemy.move_qcphysics = false;
	set_movetype(capture_enemy, MOVETYPE_NONE);
	capture_enemy.velocity = '0 0 0';
	capture_enemy.oldvelocity = '0 0 0';
	capture_enemy.avelocity = '0 0 0';
	PHYS_INPUT_BUTTON_ATCK(capture_enemy) = false;
	PHYS_INPUT_BUTTON_ATCK2(capture_enemy) = false;
	PHYS_INPUT_BUTTON_JUMP(capture_enemy) = false;
}

void Capture_FreezeDeadEnemy()
{
	if(!capture_enemy_death_latched)
	{
		                                                                       
		                                                                      
		                                                                    
		capture_enemy_death_latched = true;
		capture_enemy_death_origin = capture_enemy.origin;
	}
	Capture_StopEnemyMotion();
	setorigin(capture_enemy, capture_enemy_death_origin);
}

vector Capture_EnemyMotionDirection(int code, vector lateral, vector radial)
{
	switch(code)
	{
		                                                                 
		                                                               
		case 1: return lateral;
		case 2: return -lateral;
		case 3: return radial;
		case 4: return -radial;
		                                                                       
		case 5: return normalize(lateral + radial);
		case 6: return normalize(-lateral + radial);
		case 7: return normalize(lateral - radial);
		case 8: return normalize(-lateral - radial);
	}
	return '0 0 0';
}

void Capture_ApplyEnemyTimeline()
{
	if(!capture_timeline_tick_ready)
	{
		string next_line = capture_timeline_fh >= 0
			? fgets(capture_timeline_fh) : "";
		if(next_line == ""
			|| !Capture_ParseEnemyTimelineTick(
				next_line, capture_server_tick))
		{
			Capture_Log(sprintf(
				"{\"kind\":\"fatal\",\"reason\":\"enemy_timeline_tick_missing_or_invalid\","
				"\"server_tick\":%d}", capture_server_tick));
			capture_server_done = true;
			stuffcmd(capture_player, "\ncapture_output_end\n");
			return;
		}
	}
	if(capture_timeline_tick != capture_server_tick)
	{
		Capture_Log(sprintf(
			"{\"kind\":\"fatal\",\"reason\":\"enemy_timeline_tick_mismatch\","
			"\"server_tick\":%d,\"timeline_tick\":%d}",
			capture_server_tick, capture_timeline_tick));
		capture_server_done = true;
		stuffcmd(capture_player, "\ncapture_output_end\n");
		return;
	}
	int slot = capture_timeline_current_actor_slot;
	bool actor_switched = slot != capture_active_actor_slot;
	if(actor_switched)
	{
		if(capture_active_actor_slot > 0)
		{
			capture_timeline_actor_runtime_health[
				capture_active_actor_slot - 1] =
				GetResource(capture_enemy, RES_HEALTH);
			capture_timeline_actor_runtime_armor[
				capture_active_actor_slot - 1] =
				GetResource(capture_enemy, RES_ARMOR);
		}
		string previous_id = capture_active_actor_slot > 0
			? capture_timeline_actor_id[capture_active_actor_slot - 1] : "";
		string next_id = slot > 0
			? capture_timeline_actor_id[slot - 1] : "";
		Capture_Log(sprintf(
			"{\"kind\":\"actor_switch\",\"episode_id\":\"%s\","
			"\"server_tick\":%d,\"previous_slot\":%d,\"previous_actor_id\":\"%s\","
			"\"active_slot\":%d,\"active_actor_id\":\"%s\","
			"\"active_model\":\"%s\",\"active_skin\":%d,\"active_color\":%d}",
			autocvar_capture_episode_id, capture_server_tick,
			capture_active_actor_slot, previous_id, slot, next_id,
			(slot > 0 ? capture_timeline_actor_model[slot - 1] : ""),
			(slot > 0 ? capture_timeline_actor_skin[slot - 1] : 0),
			(slot > 0 ? capture_timeline_actor_color[slot - 1] : 0)));
		capture_active_actor_slot = slot;
		if(slot > 0)
		{
			setplayermodel(capture_enemy,
				strcat("models/player/",
					capture_timeline_actor_model[slot - 1], ".iqm"));
			setsize(capture_enemy, STAT(PL_MIN, capture_enemy),
				STAT(PL_MAX, capture_enemy));
			capture_enemy.skin = capture_timeline_actor_skin[slot - 1];
			capture_enemy.clientcolors = capture_timeline_actor_color[slot - 1];
			capture_enemy.colormap = 1024
				+ capture_timeline_actor_color[slot - 1];
			Capture_SetResources(capture_enemy,
				capture_timeline_actor_runtime_health[slot - 1],
				capture_timeline_actor_runtime_armor[slot - 1],
				autocvar_capture_reserve);
			if(capture_timeline_actor_runtime_health[slot - 1] >= 1)
				capture_enemy.deadflag = DEAD_NO;
		}
		capture_enemy_death_latched = false;
		capture_enemy_step_distance = 0;
		capture_enemy_step_index = 0;
	}
	Capture_SetEnemyActorVisible(capture_enemy, slot > 0);
	if(slot == 0)
	{
		capture_timeline_tick_ready = false;
		return;
	}
	if(GetResource(capture_enemy, RES_HEALTH) < 1)
	{
		Capture_FreezeDeadEnemy();
		capture_timeline_tick_ready = false;
		return;
	}
	                                                                           
	                                                                          
	                                                                           
	float requested_x = capture_timeline_current_origin.x;
	float requested_y = capture_timeline_current_origin.y;
	                                                                          
	                                                                           
	                                                                       
	float requested_z = capture_timeline_current_origin.z + 0.125;
	vector requested_target;
	requested_target.x = requested_x;
	requested_target.y = requested_y;
	requested_target.z = requested_z;
	vector target = requested_target;
	if(!capture_timeline_current_jump)
	{
		                                                                    
		                                                                     
		                                                              
		                                                                      
		                                                                    
		                                                                  
		                                                                         
		                                                                      
		                                                                        
		vector ground_probe_start = target + '0 0 18';
		vector ground_probe_end = target - '0 0 32';
		tracebox(ground_probe_start, capture_enemy.mins, capture_enemy.maxs,
			ground_probe_end, MOVE_WORLDONLY, capture_enemy);
		if(trace_startsolid || trace_allsolid || trace_fraction >= 0.999999)
		{
			string ground_row = sprintf(
				"{\"kind\":\"fatal\","
				"\"reason\":\"enemy_ground_support_missing\","
				"\"server_tick\":%d,\"actor_slot\":%d,"
				"\"trace_fraction\":%.9f,\"trace_startsolid\":%d,"
				"\"trace_allsolid\":%d,",
				capture_server_tick, slot, trace_fraction,
				trace_startsolid, trace_allsolid);
			ground_row = strcat(ground_row, sprintf(
				"\"target\":[%.6f,%.6f,%.6f],"
				"\"probe_start\":[%.6f,%.6f,%.6f],",
				target.x, target.y, target.z,
				ground_probe_start.x, ground_probe_start.y,
				ground_probe_start.z));
			ground_row = strcat(ground_row, sprintf(
				"\"probe_end\":[%.6f,%.6f,%.6f]}",
				ground_probe_end.x, ground_probe_end.y,
				ground_probe_end.z));
			Capture_Log(ground_row);
			capture_enemy.velocity = '0 0 0';
			capture_enemy.oldvelocity = '0 0 0';
			capture_timeline_tick_ready = false;
			capture_server_done = true;
			stuffcmd(capture_player, "\ncapture_output_end\n");
			return;
		}
		target = trace_endpos;
		                                                                       
		                                                                     
		                                                         
		if(!actor_switched
			&& fabs(target.z - capture_enemy.origin.z) > 18)
		{
			string discontinuity_row = sprintf(
				"{\"kind\":\"fatal\","
					"\"reason\":\"enemy_ground_discontinuity\","
					"\"server_tick\":%d,\"actor_slot\":%d,"
					"\"previous_z\":%.6f,\"target_z\":%.6f,",
				capture_server_tick, slot,
				capture_enemy.origin.z, target.z);
			discontinuity_row = strcat(discontinuity_row, sprintf(
				"\"requested\":[%.6f,%.6f,%.6f]}",
				requested_x, requested_y, requested_z));
			Capture_Log(discontinuity_row);
			capture_enemy.velocity = '0 0 0';
			capture_enemy.oldvelocity = '0 0 0';
			capture_timeline_tick_ready = false;
			capture_server_done = true;
			stuffcmd(capture_player, "\ncapture_output_end\n");
			return;
		}
	}
	vector trace_start;
	if(actor_switched)
	{
		trace_start = target;
	}
	else
	{
		trace_start.x = capture_enemy.origin.x;
		trace_start.y = capture_enemy.origin.y;
		trace_start.z = capture_enemy.origin.z;
	}
	float collision_start_x = trace_start.x;
	float collision_start_y = trace_start.y;
	float collision_start_z = trace_start.z;
	tracebox(trace_start, capture_enemy.mins, capture_enemy.maxs,
		target, MOVE_WORLDONLY, capture_enemy);
	if(trace_startsolid || trace_allsolid || trace_fraction < 0.999999)
	{
		                                                                      
		                                                                       
		string collision_row = sprintf(
			"{\"kind\":\"fatal\",\"reason\":\"enemy_world_collision\","
			"\"server_tick\":%d,\"actor_slot\":%d,\"actor_switched\":%d,"
			"\"trace_fraction\":%.9f,\"trace_startsolid\":%d,"
			"\"trace_allsolid\":%d,",
			capture_server_tick, slot, actor_switched,
			trace_fraction, trace_startsolid, trace_allsolid);
		collision_row = strcat(collision_row, sprintf(
			"\"start\":[%.6f,%.6f,%.6f],"
			"\"requested\":[%.6f,%.6f,%.6f],",
			collision_start_x, collision_start_y, collision_start_z,
			requested_x, requested_y, requested_z));
		collision_row = strcat(collision_row, sprintf(
			"\"safe_end\":[%.6f,%.6f,%.6f],"
			"\"mins\":[%.6f,%.6f,%.6f],",
			trace_endpos.x, trace_endpos.y, trace_endpos.z,
			capture_enemy.mins.x, capture_enemy.mins.y,
			capture_enemy.mins.z));
		collision_row = strcat(collision_row, sprintf(
			"\"maxs\":[%.6f,%.6f,%.6f]}",
			capture_enemy.maxs.x, capture_enemy.maxs.y,
			capture_enemy.maxs.z));
		Capture_Log(collision_row);
		capture_enemy.velocity = '0 0 0';
		capture_enemy.oldvelocity = '0 0 0';
		setorigin(capture_enemy, trace_endpos);
		capture_timeline_tick_ready = false;
		capture_server_done = true;
		stuffcmd(capture_player, "\ncapture_output_end\n");
		return;
	}
	vector timeline_velocity = capture_timeline_current_velocity;
	setorigin(capture_enemy, target);
	capture_enemy.velocity = timeline_velocity;
	capture_enemy.oldvelocity = timeline_velocity;
	capture_enemy.v_angle = '0 1 0'
		* capture_timeline_current_yaw;
	capture_enemy.angles = capture_enemy.v_angle;
	capture_enemy.fixangle = true;
	PHYS_INPUT_BUTTON_ATCK(capture_enemy) = false;
	PHYS_INPUT_BUTTON_ATCK2(capture_enemy) = false;
	PHYS_INPUT_BUTTON_JUMP(capture_enemy) = capture_timeline_current_jump;
	if(capture_timeline_current_jump)
		UNSET_ONGROUND(capture_enemy);
	else
	{
		SET_ONGROUND(capture_enemy);
		Capture_AdvanceEnemyFootsteps(target);
	}
	capture_prev_enemy_step_origin = target;
	capture_timeline_tick_ready = false;
	if(capture_server_tick == CAPTURE_ACTION_COUNT - 1)
	{
		string extra_line = capture_timeline_fh >= 0
			? fgets(capture_timeline_fh) : "";
		if(extra_line != "")
		{
			Capture_Log(sprintf(
				"{\"kind\":\"fatal\",\"reason\":\"enemy_timeline_extra_rows\","
				"\"server_tick\":%d}", capture_server_tick));
			capture_server_done = true;
			stuffcmd(capture_player, "\ncapture_output_end\n");
		}
		if(capture_timeline_fh >= 0)
			fclose(capture_timeline_fh);
		capture_timeline_fh = -1;
	}
}

void Capture_MoveEnemy()
{
	if(!autocvar_capture_enemy_present)
		return;
	if(autocvar_capture_enemy_timeline_enable)
	{
		Capture_ApplyEnemyTimeline();
		return;
	}
	if(GetResource(capture_enemy, RES_HEALTH) < 1)
	{
		Capture_FreezeDeadEnemy();
		return;
	}
	vector offset = '0 0 0';
	vector commanded_velocity = '0 0 0';
	float jump_offset = 0;
	float jump_velocity = 0;
	bool jump_airborne = false;
	bool jump_button = false;
	vector radial = normalize(
		autocvar_capture_player_origin - autocvar_capture_enemy_origin);
	int policy_tick = capture_server_tick
		- autocvar_capture_enemy_motion_start_tick;
	float t = max(0, policy_tick) / 64.0;
	if(policy_tick < 0)
	{
		capture_enemy.velocity = '0 0 0';
		return;
	}
	switch(autocvar_capture_enemy_motion)
	{
		case 1:
			offset = autocvar_capture_enemy_motion_vector
				* (sin(t * M_PI * 0.8) * autocvar_capture_enemy_motion_distance);
			commanded_velocity = autocvar_capture_enemy_motion_vector
				* (cos(t * M_PI * 0.8) * M_PI * 0.8
				* autocvar_capture_enemy_motion_distance);
			break;
		case 2:
			                                                                    
			offset = radial
				* (sin(t * M_PI * 0.4) * autocvar_capture_enemy_motion_distance);
			commanded_velocity = radial
				* (cos(t * M_PI * 0.4) * M_PI * 0.4
				* autocvar_capture_enemy_motion_distance);
			break;
		case 3:
			                                               
			                                                         
			                                                              
			float phase = t - floor(t / 3) * 3;
			float scalar = 0;
			float scalar_velocity = 0;
			if(phase < 0.5)
			{
				scalar = sin(phase * M_PI);
				scalar_velocity = cos(phase * M_PI) * M_PI;
			}
			else if(phase < 1)
				scalar = 1;
			else if(phase < 2)
			{
				scalar = cos((phase - 1) * M_PI);
				scalar_velocity = -sin((phase - 1) * M_PI) * M_PI;
			}
			else if(phase < 2.5)
				scalar = -1;
			else
			{
				scalar = -cos((phase - 2.5) * M_PI);
				scalar_velocity = sin((phase - 2.5) * M_PI) * M_PI;
			}
			offset = autocvar_capture_enemy_motion_vector
				* (scalar * autocvar_capture_enemy_motion_distance);
			commanded_velocity = autocvar_capture_enemy_motion_vector
				* (scalar_velocity * autocvar_capture_enemy_motion_distance);
			break;
		case 5:
			                                                             
			                                                                     
			                                                                       
			                                 
			float block_seconds = max(0.125,
				autocvar_capture_enemy_motion_block_seconds);
			float fixed_speed = max(0,
				autocvar_capture_enemy_motion_speed);
			vector lateral = autocvar_capture_enemy_motion_vector;
			lateral.z = 0;
			lateral = normalize(lateral);
			vector prompt_radial =
				autocvar_capture_player_origin
				- autocvar_capture_enemy_origin;
			prompt_radial.z = 0;
			prompt_radial = normalize(prompt_radial);
			for(int block = 0; block < 5; ++block)
			{
				float elapsed = bound(0,
					t - block * block_seconds, block_seconds);
				int code = Capture_EnemyMotionBlockCode(block);
				offset += Capture_EnemyMotionDirection(
					code, lateral, prompt_radial)
					* fixed_speed * elapsed;
			}
			int active_block = floor(t / block_seconds);
			if(active_block >= 0 && active_block < 5)
			{
				int active_code = Capture_EnemyMotionBlockCode(
					active_block);
				commanded_velocity = Capture_EnemyMotionDirection(
					active_code, lateral, prompt_radial)
					* fixed_speed;
			}
			break;
	}
	if(autocvar_capture_enemy_jump_enabled
		&& autocvar_capture_enemy_motion == 5)
	{
		float jump_block_seconds = max(0.125,
			autocvar_capture_enemy_motion_block_seconds);
		int jump_block_ticks = max(1,
			floor(jump_block_seconds * 64 + 0.5));
		int jump_block = floor(policy_tick / jump_block_ticks);
		if(jump_block >= 0 && jump_block < 5
			&& Capture_EnemyJumpBlockEnabled(jump_block))
		{
			int local_tick = policy_tick - jump_block * jump_block_ticks;
			int jump_start = max(0,
				autocvar_capture_enemy_jump_start_tick_in_block);
			int jump_duration = max(8,
				autocvar_capture_enemy_jump_duration_ticks);
			if(local_tick >= jump_start
				&& local_tick <= jump_start + jump_duration)
			{
				float progress = bound(0,
					(local_tick - jump_start) / jump_duration, 1);
				float jump_height = max(0,
					autocvar_capture_enemy_jump_height);
				jump_offset = 4 * jump_height * progress * (1 - progress);
				jump_velocity = (4 * jump_height
					/ (jump_duration / 64.0)) * (1 - 2 * progress);
				jump_airborne = jump_offset > 0.01;
				jump_button = local_tick == jump_start;
			}
		}
	}
	vector ground_target = autocvar_capture_enemy_origin + offset;
	vector target = ground_target;
	if(jump_offset > 0)
	{
		tracebox(ground_target, capture_enemy.mins, capture_enemy.maxs,
			ground_target + '0 0 1' * jump_offset,
			MOVE_WORLDONLY, capture_enemy);
		target = trace_endpos;
		if(target.z - ground_target.z < jump_offset - 0.01)
			jump_velocity = 0;
	}
	commanded_velocity.z = jump_velocity;
	capture_enemy.move_qcphysics = false;
	set_movetype(capture_enemy, MOVETYPE_NONE);
	capture_enemy.velocity = commanded_velocity;
	capture_enemy.oldvelocity = commanded_velocity;
	setorigin(capture_enemy, target);
	if(jump_airborne)
	{
		UNSET_ONGROUND(capture_enemy);
		capture_prev_enemy_step_origin = ground_target;
	}
	else
	{
		SET_ONGROUND(capture_enemy);
		Capture_AdvanceEnemyFootsteps(ground_target);
	}
	capture_enemy.v_angle = '0 1 0' * autocvar_capture_enemy_yaw;
	capture_enemy.angles = capture_enemy.v_angle;
	capture_enemy.fixangle = true;
	PHYS_INPUT_BUTTON_ATCK(capture_enemy) = false;
	PHYS_INPUT_BUTTON_ATCK2(capture_enemy) = false;
	PHYS_INPUT_BUTTON_JUMP(capture_enemy) = jump_button;
}

void Capture_LogState()
{
	entity weapon_entity = capture_player.(weaponentities[0]);
	Weapon weapon = weapon_entity.m_weapon;
	float health = GetResource(capture_player, RES_HEALTH);
	float armor = GetResource(capture_player, RES_ARMOR);
	float clip = weapon_entity.clip_load;
	float reserve = Capture_Reserve(capture_player, weapon);
	string row = sprintf(
		"{\"kind\":\"state\",\"episode_id\":\"%s\",\"server_tick\":%d,\"server_time\":%.9f,",
		autocvar_capture_episode_id, capture_server_tick, time);
	row = strcat(row, sprintf(
		"\"applied_action\":{\"forward\":%.6f,\"strafe\":%.6f,\"up\":%.6f,"
		"\"pitch\":%.6f,\"yaw\":%.6f,\"jump\":%d,",
		capture_action_forward,
		capture_action_strafe, 0,
		capture_action_pitch,
		capture_action_yaw,
		capture_action_jump));
	row = strcat(row, sprintf(
		"\"primary\":%d,\"secondary\":%d,\"impulse\":%d},",
		capture_action_primary,
		capture_action_secondary,
		capture_action_reload
			? 20 : capture_action_impulse));
	row = strcat(row, sprintf(
		"\"pre\":{\"origin\":[%.6f,%.6f,%.6f],",
		capture_prev_player_origin.x, capture_prev_player_origin.y, capture_prev_player_origin.z));
	row = strcat(row, sprintf(
		"\"velocity\":[%.6f,%.6f,%.6f],",
		capture_prev_player_velocity.x, capture_prev_player_velocity.y, capture_prev_player_velocity.z));
	row = strcat(row, sprintf(
		"\"angles\":[%.6f,%.6f,%.6f],\"health\":%.6f,\"armor\":%.6f,",
		capture_prev_player_angles.x, capture_prev_player_angles.y, capture_prev_player_angles.z,
		capture_prev_player_health, capture_prev_player_armor));
	row = strcat(row, sprintf(
		"\"clip\":%.6f,\"reserve\":%.6f},",
		capture_prev_player_clip, capture_prev_player_reserve));
	row = strcat(row, sprintf(
		"\"post\":{\"origin\":[%.6f,%.6f,%.6f],",
		capture_player.origin.x, capture_player.origin.y, capture_player.origin.z));
	row = strcat(row, sprintf(
		"\"velocity\":[%.6f,%.6f,%.6f],",
		capture_player.velocity.x, capture_player.velocity.y, capture_player.velocity.z));
	row = strcat(row, sprintf(
		"\"angles\":[%.6f,%.6f,%.6f],\"health\":%.6f,\"armor\":%.6f,",
		capture_player.v_angle.x, capture_player.v_angle.y, capture_player.v_angle.z,
		health, armor));
	row = strcat(row, sprintf(
		"\"clip\":%.6f,\"reserve\":%.6f,\"weapon\":\"%s\",\"onground\":%d},",
		clip, reserve, weapon.netname, boolean(capture_player.flags & FL_ONGROUND)));
	if(autocvar_capture_enemy_present
		&& (!autocvar_capture_enemy_timeline_enable
			|| capture_active_actor_slot > 0))
	{
		traceline(capture_player.origin + '0 0 24',
			capture_enemy.origin + '0 0 24',
			MOVE_WORLDONLY, capture_player);
		float enemy_los_fraction = trace_fraction;
		float enemy_distance = vlen(
			capture_enemy.origin - capture_player.origin);
		row = strcat(row, sprintf(
			"\"enemy\":{\"present\":1,\"actor_slot\":%d,\"actor_id\":\"%s\","
			"\"origin\":[%.6f,%.6f,%.6f],",
			(autocvar_capture_enemy_timeline_enable
				? capture_active_actor_slot : 1),
			(autocvar_capture_enemy_timeline_enable
				? capture_timeline_actor_id[capture_active_actor_slot - 1] : "enemy"),
			capture_enemy.origin.x, capture_enemy.origin.y, capture_enemy.origin.z));
		row = strcat(row, sprintf(
			"\"velocity\":[%.6f,%.6f,%.6f],",
			capture_enemy.velocity.x, capture_enemy.velocity.y, capture_enemy.velocity.z));
		row = strcat(row, sprintf(
			"\"health\":%.6f,\"armor\":%.6f,\"model\":\"%s\","
			"\"skin\":%d,\"color\":%d,\"distance\":%.6f,"
			"\"los_fraction\":%.9f}}",
			GetResource(capture_enemy, RES_HEALTH),
			GetResource(capture_enemy, RES_ARMOR),
			(autocvar_capture_enemy_timeline_enable
				? capture_timeline_actor_model[capture_active_actor_slot - 1]
				: autocvar_capture_enemy_model),
			(autocvar_capture_enemy_timeline_enable
				? capture_timeline_actor_skin[capture_active_actor_slot - 1]
				: autocvar_capture_enemy_skin),
			(autocvar_capture_enemy_timeline_enable
				? capture_timeline_actor_color[capture_active_actor_slot - 1]
				: autocvar_capture_enemy_color), enemy_distance,
			enemy_los_fraction));
	}
	else
		row = strcat(row, "\"enemy\":null}");
	Capture_Log(row);
	capture_prev_player_origin = capture_player.origin;
	capture_prev_player_velocity = capture_player.velocity;
	capture_prev_player_angles = capture_player.v_angle;
	capture_prev_player_health = health;
	capture_prev_player_armor = armor;
	capture_prev_player_clip = clip;
	capture_prev_player_reserve = reserve;
}

void Capture_ServerFrame()
{
	if(!autocvar_capture_server_enable || capture_server_done)
		return;
	if(!capture_server_started)
	{
		Capture_TryReset();
		  
                                                                         
                                                                         
                                                                           
                                                                          
                                 
     
		if(capture_server_started
			&& autocvar_capture_enemy_timeline_enable)
			Capture_MoveEnemy();
		return;
	}
	if(!capture_player || !IS_PLAYER(capture_player)
		|| (autocvar_capture_enemy_present
			&& (!capture_enemy || !IS_PLAYER(capture_enemy))))
	{
		Capture_Log("{\"kind\":\"fatal\",\"reason\":\"capture_actor_missing\"}");
		capture_server_done = true;
		return;
	}
	if(capture_server_tick_logged)
	{
		++capture_server_tick;
		capture_server_tick_logged = false;
		if(capture_server_tick >= CAPTURE_ACTION_COUNT)
			return;
	}
	if(capture_server_tick >= CAPTURE_ACTION_COUNT)
	{
		  
                                                                          
                                                                            
                                                                       
                                                                            
                                                                             
                                                                          
                                           
     
		if(capture_server_tick
			== CAPTURE_ACTION_COUNT + CAPTURE_OUTPUT_END_GRACE_TICKS)
		{
			Capture_Log(sprintf(
				"{\"kind\":\"output_end\",\"server_tick\":%d,\"server_time\":%.9f}",
				capture_server_tick, time));
			stuffcmd(capture_player, "\ncapture_output_end\n");
			capture_server_done = true;
			fclose(capture_server_fh);
			capture_server_fh = -1;
			return;
		}
		++capture_server_tick;
		return;
	}
	Capture_MoveEnemy();
	if(capture_server_done)
		return;
	                                                                        
	                                                                           
	                                                                 
	if(capture_server_tick == 61)
	{
		Capture_Log(sprintf(
			"{\"kind\":\"output_begin\",\"server_tick\":%d,\"server_time\":%.9f}",
			capture_server_tick, time));
		stuffcmd(capture_player, "\ncapture_output_begin\n");
	}
}

void Capture_ServerFrameEnd(entity actor)
{
	if(!autocvar_capture_server_enable || !capture_server_started
		|| capture_server_done || capture_server_tick_logged
		|| capture_server_tick >= capture_action_count
		|| actor != capture_player)
		return;
	  
                                                                           
                                                                            
                                                                       
                                                                          
                                                                          
                                                                          
                                                                            
    
	if(autocvar_capture_enemy_present && capture_enemy
		&& GetResource(capture_enemy, RES_HEALTH) < 1)
		Capture_FreezeDeadEnemy();
	Capture_LogState();
	capture_action_ready = false;
	if(capture_server_tick < CAPTURE_ACTION_COUNT - 1)
	{
		string next_action_line = capture_action_fh >= 0
			? fgets(capture_action_fh) : "";
		if(next_action_line == ""
			|| !Capture_ParseAuthoritativeAction(
				next_action_line, capture_server_tick + 1))
		{
			Capture_Log(sprintf(
				"{\"kind\":\"fatal\",\"reason\":\"authoritative_action_tick_missing_or_invalid\","
				"\"server_tick\":%d}", capture_server_tick + 1));
			capture_server_done = true;
			stuffcmd(capture_player, "\ncapture_output_end\n");
			return;
		}
	}
	else
	{
		string extra_action_line = capture_action_fh >= 0
			? fgets(capture_action_fh) : "";
		if(extra_action_line != "")
		{
			Capture_Log(sprintf(
				"{\"kind\":\"fatal\",\"reason\":\"authoritative_action_extra_rows\","
				"\"server_tick\":%d}", capture_server_tick));
			capture_server_done = true;
			stuffcmd(capture_player, "\ncapture_output_end\n");
		}
		if(capture_action_fh >= 0)
			fclose(capture_action_fh);
		capture_action_fh = -1;
	}
	capture_server_tick_logged = true;
}

void Capture_Fire(entity actor, int deathtype, vector shot_origin, vector shot_direction)
{
	if(!autocvar_capture_server_enable || !capture_server_started || capture_server_done)
		return;
	int event_id = Capture_NewEvent();
	actor.capture_last_fire_event = event_id;
	string row = sprintf(
		"{\"kind\":\"event\",\"event\":\"fire\",\"event_id\":%d,\"parent_event_id\":null,"
		"\"server_tick\":%d,\"server_time\":%.9f,\"actor\":%d,\"weapon_id\":%d,"
		"\"secondary\":%d,",
		event_id, capture_server_tick, time, etof(actor),
		DEATH_WEAPONOF(deathtype).m_id, boolean(deathtype & HITTYPE_SECONDARY));
	row = strcat(row, sprintf(
		"\"origin\":[%.6f,%.6f,%.6f],\"direction\":[%.9f,%.9f,%.9f]}",
		shot_origin.x, shot_origin.y, shot_origin.z,
		shot_direction.x, shot_direction.y, shot_direction.z));
	Capture_Log(row);
}

void Capture_ProjectileSpawn(entity projectile, entity actor, int deathtype)
{
	if(!autocvar_capture_server_enable || !capture_server_started || capture_server_done)
		return;
	projectile.capture_event_id = Capture_NewEvent();
	string row = sprintf(
		"{\"kind\":\"event\",\"event\":\"projectile\",\"event_id\":%d,\"parent_event_id\":%d,"
		"\"server_tick\":%d,\"server_time\":%.9f,\"entity\":%d,\"actor\":%d,\"weapon_id\":%d,",
		projectile.capture_event_id, actor.capture_last_fire_event,
		capture_server_tick, time, etof(projectile), etof(actor),
		DEATH_WEAPONOF(deathtype).m_id);
	row = strcat(row, sprintf(
		"\"origin\":[%.6f,%.6f,%.6f],\"velocity\":[%.6f,%.6f,%.6f]}",
		projectile.origin.x, projectile.origin.y, projectile.origin.z,
		projectile.velocity.x, projectile.velocity.y, projectile.velocity.z));
	Capture_Log(row);
}

void Capture_DamageApplied(entity target, entity inflictor, entity attacker,
	float damage, int deathtype, vector hitloc,
	float pre_health, float pre_armor)
{
	if(!autocvar_capture_server_enable || !capture_server_started || capture_server_done)
		return;
	                                                                          
	                                                                         
	                                                                 
	if(pre_health < 1)
	{
		SetResourceExplicit(target, RES_HEALTH, 0);
		return;
	}
	int parent = attacker ? attacker.capture_last_fire_event : 0;
	if(inflictor && inflictor.capture_event_id)
		parent = inflictor.capture_event_id;
	int impact_event = Capture_NewEvent();
	int damage_event = Capture_NewEvent();
	float post_health = GetResource(target, RES_HEALTH);
	float post_armor = GetResource(target, RES_ARMOR);
	if(post_health < 1)
	{
		SetResourceExplicit(target, RES_HEALTH, 0);
		post_health = 0;
		target.takedamage = DAMAGE_NO;
		if(target == capture_enemy)
			Capture_StopEnemyMotion();
	}
	string row = sprintf(
		"{\"kind\":\"event\",\"event\":\"impact\",\"event_id\":%d,\"parent_event_id\":%d,"
		"\"server_tick\":%d,\"server_time\":%.9f,\"target\":%d,",
		impact_event, parent, capture_server_tick, time, etof(target));
	row = strcat(row, sprintf(
		"\"direct\":%d,\"splash\":%d,\"pellet\":%d,"
		"\"hitloc\":[%.6f,%.6f,%.6f]}",
		!boolean(deathtype & HITTYPE_SPLASH), boolean(deathtype & HITTYPE_SPLASH),
		DEATH_WEAPONOF(deathtype) == WEP_SHOTGUN,
		hitloc.x, hitloc.y, hitloc.z));
	Capture_Log(row);
	row = sprintf(
		"{\"kind\":\"event\",\"event\":\"damage\",\"event_id\":%d,\"parent_event_id\":%d,"
		"\"server_tick\":%d,\"server_time\":%.9f,\"target\":%d,\"attacker\":%d,",
		damage_event, impact_event, capture_server_tick, time, etof(target),
		(attacker ? etof(attacker) : 0));
	row = strcat(row, sprintf(
		"\"amount\":%.6f,\"pre_health\":%.6f,\"post_health\":%.6f,"
		"\"pre_armor\":%.6f,\"post_armor\":%.6f,\"killed\":%d}",
		damage, pre_health, post_health, pre_armor, post_armor,
		post_health < 1));
	Capture_Log(row);
	if(post_health < 1)
	{
		int death_event = Capture_NewEvent();
		Capture_Log(sprintf(
				"{\"kind\":\"event\",\"event\":\"death\",\"event_id\":%d,\"parent_event_id\":%d,"
				"\"server_tick\":%d,\"server_time\":%.9f,\"target\":%d,\"attacker\":%d}",
				death_event, damage_event, capture_server_tick, time, etof(target),
				(attacker ? etof(attacker) : 0)));
	}
}

void Capture_ReloadStart(entity actor, entity weapon_entity)
{
	if(!autocvar_capture_server_enable || !capture_server_started || capture_server_done)
		return;
	int event_id = Capture_NewEvent();
	weapon_entity.capture_event_id = event_id;
	Weapon weapon = weapon_entity.m_weapon;
	Capture_Log(sprintf(
		"{\"kind\":\"event\",\"event\":\"reload_start\",\"event_id\":%d,\"parent_event_id\":null,"
		"\"server_tick\":%d,\"server_time\":%.9f,\"actor\":%d,\"weapon\":\"%s\","
		"\"pre_clip\":%.6f,\"pre_reserve\":%.6f}",
		event_id, capture_server_tick, time, etof(actor), weapon.netname,
		weapon_entity.clip_load, Capture_Reserve(actor, weapon)));
}

void Capture_ReloadComplete(entity actor, entity weapon_entity,
	float pre_clip, float pre_reserve)
{
	if(!autocvar_capture_server_enable || !capture_server_started || capture_server_done)
		return;
	Weapon weapon = weapon_entity.m_weapon;
	int event_id = Capture_NewEvent();
	float post_reserve = Capture_Reserve(actor, weapon);
	string row = sprintf(
		"{\"kind\":\"event\",\"event\":\"reload_complete\",\"event_id\":%d,\"parent_event_id\":%d,"
		"\"server_tick\":%d,\"server_time\":%.9f,\"actor\":%d,\"weapon\":\"%s\",",
		event_id, weapon_entity.capture_event_id,
		capture_server_tick, time, etof(actor), weapon.netname);
	row = strcat(row, sprintf(
		"\"pre_clip\":%.6f,\"post_clip\":%.6f,\"pre_reserve\":%.6f,\"post_reserve\":%.6f,"
		"\"success\":%d}",
		pre_clip, weapon_entity.clip_load, pre_reserve, post_reserve,
		weapon_entity.clip_load > pre_clip && post_reserve < pre_reserve));
	Capture_Log(row);
}
