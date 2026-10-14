#include "main.qh"

#include <common/command/generic.qh>
#include <common/constants.qh>
#include <common/deathtypes/all.qh>
#include <common/debug.qh>
#include <common/mapinfo.qh>
#include <common/monsters/sv_monsters.qh>
#include <common/util.qh>
#include <common/vehicles/all.qh>
#include <common/weapons/_all.qh>
#include <lib/csqcmodel/sv_model.qh>
#include <lib/warpzone/common.qh>
#include <lib/warpzone/server.qh>
#include <server/anticheat.qh>
#include <server/bot/api.qh>
#include <server/bot/default/cvars.qh>
#include <server/command/common.qh>
#include <server/compat/quake3.qh>
#include <server/client.qh>
#include <server/damage.qh>
#include <server/gamelog.qh>
#include <server/hook.qh>
#include <server/ipban.qh>
#include <server/mutators/_mod.qh>
#include <server/spawnpoints.qh>
#include <server/weapons/common.qh>
#include <server/weapons/csqcprojectile.qh>
#include <server/world.qh>

int duel_action_telemetry_fh = -1;
int duel_action_telemetry_frame_index;
float duel_action_telemetry_next_status_log;
int duel_action_telemetry_target_matches;

void DuelCameraMotor_Frame()
{
	FOREACH_CLIENT(IS_BOT_CLIENT(it),
	{
		if (!it.duel_camera_motor_initialized)
		{
			it.duel_camera_motor_initialized = true;
			it.duel_camera_motor_previous_output = it.v_angle;
			it.duel_camera_motor_previous_label = it.v_angle;
			it.duel_camera_motor_rate = '0 0 0';
			continue;
		}

		vector previous = it.duel_camera_motor_previous_output;
		vector turn_delta = it.v_angle - previous;
		turn_delta.y = turn_delta.y - floor(turn_delta.y / 360) * 360;
		if (turn_delta.y >= 180)
			turn_delta.y -= 360;
		vector desired_rate = turn_delta / frametime;
		if (autocvar_duel_max_turn_speed > 0)
		{
			desired_rate.x = bound(
				-autocvar_duel_max_turn_speed,
				desired_rate.x,
				autocvar_duel_max_turn_speed);
			desired_rate.y = bound(
				-autocvar_duel_max_turn_speed,
				desired_rate.y,
				autocvar_duel_max_turn_speed);
		}
		if (autocvar_duel_max_turn_accel > 0)
		{
			float max_rate_delta = autocvar_duel_max_turn_accel * frametime;
			desired_rate.x = bound(
				it.duel_camera_motor_rate.x - max_rate_delta,
				desired_rate.x,
				it.duel_camera_motor_rate.x + max_rate_delta);
			desired_rate.y = bound(
				it.duel_camera_motor_rate.y - max_rate_delta,
				desired_rate.y,
				it.duel_camera_motor_rate.y + max_rate_delta);
		}

		it.duel_camera_motor_previous_label = previous;
		it.duel_camera_motor_rate = desired_rate;
		it.v_angle = previous + desired_rate * frametime;
		it.v_angle_z = 0;
		it.v_angle_y = it.v_angle.y - floor(it.v_angle.y / 360) * 360;
		it.duel_camera_motor_previous_output = it.v_angle;
	});
}

void DuelActionTelemetry_Close(string reason)
{
	if (duel_action_telemetry_fh < 0)
		return;
	fclose(duel_action_telemetry_fh);
	duel_action_telemetry_fh = -1;
	LOG_INFO("duel_action_telemetry:closed reason=", reason,
		" frames=", itos(duel_action_telemetry_frame_index));
}

void DuelActionTelemetry_Open()
{
	if (duel_action_telemetry_fh >= 0)
		return;
	if (autocvar_duel_action_telemetry_file == "")
		error("duel_action_telemetry_file must be set when telemetry is enabled");
	duel_action_telemetry_fh = fopen(autocvar_duel_action_telemetry_file, FILE_WRITE);
	if (duel_action_telemetry_fh < 0)
		error(strcat("failed to open duel action telemetry file: ", autocvar_duel_action_telemetry_file));
	duel_action_telemetry_frame_index = 0;
	duel_action_telemetry_epoch_time = time;
	fputs(duel_action_telemetry_fh,
		"# schema=xonotic-duel-v11-authoritative-bot-action-v1 tick_hz=64 sampling=post_bot_ai_pre_snapshot\n");
	fputs(duel_action_telemetry_fh,
			"frame_index\tserver_time\tserver_frametime\tbot_entity\tplayer_id\tbot_name\tis_pov\tpov_target_matches\treal_client_count\tpov_observer_count\tmovement_x\tmovement_y\tmovement_z\tprevious_view_pitch\tprevious_view_yaw\tprevious_view_roll\tview_pitch\tview_yaw\tview_roll\tbutton_mask\tbutton_jump\tbutton_primary\tbutton_secondary\tbutton_crouch\tbutton_zoom\tbutton_hook\tbutton_use\tbutton_info\tbutton_drag\tbutton_chat\tbutton_zoomscript\tbutton_jetpack\tbutton_dodge\tbutton_minigame\tbutton_prydon\tbutton13\tbutton14\tbutton15\tbutton16\timpulse\tis_dead\thealth\torigin_x\torigin_y\torigin_z\tvelocity_x\tvelocity_y\tvelocity_z\tenemy_entity\tenemy_health\n");
	LOG_INFO("duel_action_telemetry:opened file=", autocvar_duel_action_telemetry_file,
		" start=", ftos(autocvar_duel_action_telemetry_start),
		" stop=", ftos(autocvar_duel_action_telemetry_stop),
		" pov=", autocvar_duel_force_pov_bot);
}

entity DuelActionTelemetry_FindPovTarget()
{
	entity target = NULL;
	int target_matches = 0;
	FOREACH_CLIENT(IS_BOT_CLIENT(it) && it.netname == autocvar_duel_force_pov_bot,
	{
		target = it;
		target_matches = target_matches + 1;
	});
	duel_action_telemetry_target_matches = target_matches;
	return target;
}

void DuelActionTelemetry_ForcePov()
{
	if (autocvar_duel_force_pov_bot == "")
		return;

	entity target = DuelActionTelemetry_FindPovTarget();
	int target_matches = duel_action_telemetry_target_matches;
	if (target_matches != 1 || !target || !IS_PLAYER(target))
	{
		if (time >= duel_action_telemetry_next_status_log)
		{
			LOG_INFO("duel_pov_lock:waiting target=", autocvar_duel_force_pov_bot,
				" matches=", itos(target_matches));
			duel_action_telemetry_next_status_log = time + 1;
		}
		return;
	}

	FOREACH_CLIENT(IS_REAL_CLIENT(it) && (IS_SPEC(it) || IS_OBSERVER(it)),
	{
		if (it.enemy != target || CS(it).spectatee_status != etof(target))
		{
			bool was_observer = IS_OBSERVER(it);
			if (Spectate(it, target))
			{
				if (was_observer)
					TRANSMUTE(Spectator, it);
				LOG_INFO("duel_pov_lock:active observer=", it.netname,
					" target=", target.netname,
					" entity=", itos(etof(target)));
			}
		}
	});
}

void DuelActionTelemetry_Frame()
{
	if (!autocvar_duel_action_telemetry)
	{
		DuelActionTelemetry_Close("disabled");
		return;
	}
	DuelActionTelemetry_Open();
	entity target = DuelActionTelemetry_FindPovTarget();
	int target_matches = duel_action_telemetry_target_matches;
	int real_client_count = 0;
	int pov_observer_count = 0;
	FOREACH_CLIENT(IS_REAL_CLIENT(it),
	{
		real_client_count += 1;
		if (target && it.enemy == target && CS(it).spectatee_status == etof(target)
			&& IS_SPEC(it))
			pov_observer_count += 1;
	});

	FOREACH_CLIENT(IS_BOT_CLIENT(it),
	{
		entity opponent = it.enemy;
		int opponent_entity = 0;
		float opponent_health = -1;
		if (opponent)
		{
			opponent_entity = etof(opponent);
			opponent_health = GetResource(opponent, RES_HEALTH);
		}
			                                                                 
			                                                                     
			string row = sprintf("%d\t%.9f\t%.9f\t%d\t%d\t%s\t%d",
				duel_action_telemetry_frame_index, time, frametime,
				etof(it), it.playerid, it.netname, it == target);
			row = strcat(row, sprintf("\t%d\t%d\t%d\t%.9f\t%.9f\t%.9f",
				target_matches, real_client_count, pov_observer_count,
				CS(it).movement.x, CS(it).movement.y, CS(it).movement.z));
			row = strcat(row, sprintf("\t%.9f\t%.9f\t%.9f\t%.9f\t%.9f\t%.9f",
				it.duel_camera_motor_previous_label.x,
				it.duel_camera_motor_previous_label.y,
				it.duel_camera_motor_previous_label.z,
				it.v_angle.x, it.v_angle.y, it.v_angle.z));
			row = strcat(row, sprintf("\t%d\t%d\t%d\t%d\t%d\t%d",
				PHYS_INPUT_BUTTON_MASK(it), PHYS_INPUT_BUTTON_JUMP(it),
				PHYS_INPUT_BUTTON_ATCK(it), PHYS_INPUT_BUTTON_ATCK2(it),
				PHYS_INPUT_BUTTON_CROUCH(it), PHYS_INPUT_BUTTON_ZOOM(it)));
			row = strcat(row, sprintf("\t%d\t%d\t%d\t%d\t%d\t%d",
				PHYS_INPUT_BUTTON_HOOK(it), PHYS_INPUT_BUTTON_USE(it),
				PHYS_INPUT_BUTTON_INFO(it), PHYS_INPUT_BUTTON_DRAG(it),
				PHYS_INPUT_BUTTON_CHAT(it), PHYS_INPUT_BUTTON_ZOOMSCRIPT(it)));
			row = strcat(row, sprintf("\t%d\t%d\t%d\t%d\t%d\t%d",
				PHYS_INPUT_BUTTON_JETPACK(it), PHYS_INPUT_BUTTON_DODGE(it),
				PHYS_INPUT_BUTTON_MINIGAME(it), PHYS_INPUT_BUTTON_PRYDON(it),
				CS(it).button13, CS(it).button14));
			row = strcat(row, sprintf("\t%d\t%d\t%d\t%d\t%d\t%.9f\t%.9f",
				CS(it).button15, CS(it).button16, CS(it).impulse, IS_DEAD(it),
				GetResource(it, RES_HEALTH), it.origin.x, it.origin.y));
			row = strcat(row, sprintf("\t%.9f\t%.9f\t%.9f\t%.9f\t%d",
				it.origin.z, it.velocity.x, it.velocity.y, it.velocity.z, opponent_entity));
			row = strcat(row, sprintf("\t%.9f\n", opponent_health));
			fputs(duel_action_telemetry_fh, row);
		});
	duel_action_telemetry_frame_index += 1;
}

void DuelActionTelemetry_Shutdown()
{
	DuelActionTelemetry_Close("server_shutdown");
}

void dropclient_do(entity this)
{
	if (this.owner)
		dropclient(this.owner);
	delete(this);
}
   
                                                      
                                                                                          
  
                                                                                       
                                                                           
   
bool dropclient_schedule(entity this)
{
	bool scheduled = false;
	FOREACH_ENTITY_CLASS("dropclient_handler", true,
	{
		if(it.owner == this)
		{
			scheduled = true;
			break;                                                   
		}
	});
	if (scheduled)
		return false;

	entity e = new_pure(dropclient_handler);
	setthink(e, dropclient_do);
	e.owner = this;
	e.nextthink = time + 0.1;
	return true;
}

void CreatureFrame_hotliquids(entity this)
{
	if (this.contents_damagetime >= time)
	{
		return;
	}

	this.contents_damagetime = time + autocvar_g_balance_contents_damagerate;

	if (this.flags & FL_PROJECTILE)
	{
		if (this.watertype == CONTENT_LAVA)
			Damage (this, NULL, NULL, autocvar_g_balance_contents_projectiledamage * autocvar_g_balance_contents_damagerate * this.waterlevel, DEATH_LAVA.m_id, DMG_NOWEP, this.origin, '0 0 0');
		else if (this.watertype == CONTENT_SLIME)
			Damage (this, NULL, NULL, autocvar_g_balance_contents_projectiledamage * autocvar_g_balance_contents_damagerate * this.waterlevel, DEATH_SLIME.m_id, DMG_NOWEP, this.origin, '0 0 0');
	}
	else
	{
		if (STAT(FROZEN, this))
		{
			if (this.watertype == CONTENT_LAVA)
				Damage(this, NULL, NULL, 10000, DEATH_LAVA.m_id, DMG_NOWEP, this.origin, '0 0 0');
			else if (this.watertype == CONTENT_SLIME)
				Damage(this, NULL, NULL, 10000, DEATH_SLIME.m_id, DMG_NOWEP, this.origin, '0 0 0');
		}
		else if (this.watertype == CONTENT_LAVA)
		{
			if (this.watersound_finished < time)
			{
				this.watersound_finished = time + 0.5;
				sound (this, CH_PLAYER_SINGLE, SND_LAVA, VOL_BASE, ATTEN_NORM);
			}
			Damage (this, NULL, NULL, autocvar_g_balance_contents_playerdamage_lava * autocvar_g_balance_contents_damagerate * this.waterlevel, DEATH_LAVA.m_id, DMG_NOWEP, this.origin, '0 0 0');
			if(autocvar_g_balance_contents_playerdamage_lava_burn)
				Fire_AddDamage(this, NULL, autocvar_g_balance_contents_playerdamage_lava_burn * this.waterlevel, autocvar_g_balance_contents_playerdamage_lava_burn_time * this.waterlevel, DEATH_LAVA.m_id);
		}
		else if (this.watertype == CONTENT_SLIME)
		{
			if (this.watersound_finished < time)
			{
				this.watersound_finished = time + 0.5;
				sound (this, CH_PLAYER_SINGLE, SND_SLIME, VOL_BASE, ATTEN_NORM);
			}
			Damage (this, NULL, NULL, autocvar_g_balance_contents_playerdamage_slime * autocvar_g_balance_contents_damagerate * this.waterlevel, DEATH_SLIME.m_id, DMG_NOWEP, this.origin, '0 0 0');
		}
	}
}

void CreatureFrame_Liquids(entity this)
{
	if (this.watertype <= CONTENT_WATER && this.waterlevel > 0)                                                                                  
	{
		if (!(this.flags & FL_INWATER))
		{
			this.flags |= FL_INWATER;
			this.contents_damagetime = 0;
		}

		CreatureFrame_hotliquids(this);
	}
	else
	{
		if (this.flags & FL_INWATER)
		{
			                         
			this.flags &= ~FL_INWATER;
			this.contents_damagetime = 0;
		}
	}
}

void CreatureFrame_FallDamage(entity this)
{
	if(IS_VEHICLE(this) || (this.flags & FL_PROJECTILE))
		return;                                                      
	if(!(this.velocity || this.oldvelocity))
		return;                                                                       

	                           
	bool have_hook = false;
	for(int slot = 0; slot < MAX_WEAPONSLOTS; ++slot)
	{
	    .entity weaponentity = weaponentities[slot];
	    if(this.(weaponentity).hook && this.(weaponentity).hook.state)
	    {
	    	have_hook = true;
	    	break;
	    }
	}
	if(!have_hook)
	{
		float dm;                                                                                            
		if(autocvar_g_balance_falldamage_onlyvertical)
			dm = fabs(this.oldvelocity.z) - vlen(this.velocity);
		else
			dm = vlen(this.oldvelocity) - vlen(this.velocity);
		if (IS_DEAD(this))
			dm = (dm - autocvar_g_balance_falldamage_deadminspeed) * autocvar_g_balance_falldamage_factor;
		else
			dm = min((dm - autocvar_g_balance_falldamage_minspeed) * autocvar_g_balance_falldamage_factor, autocvar_g_balance_falldamage_maxdamage);
		if (dm > 0)
		{
			tracebox(this.origin, this.mins, this.maxs, this.origin - '0 0 1', MOVE_NOMONSTERS, this);
			if (!(trace_dphitq3surfaceflags & Q3SURFACEFLAG_NODAMAGE))
				Damage (this, NULL, NULL, dm, DEATH_FALL.m_id, DMG_NOWEP, this.origin, '0 0 0');
		}
	}

	if(autocvar_g_maxspeed > 0 && vdist(this.velocity, >, autocvar_g_maxspeed))
		Damage (this, NULL, NULL, 100000, DEATH_SHOOTING_STAR.m_id, DMG_NOWEP, this.origin, '0 0 0');
}

void CreatureFrame_All()
{
	if(game_stopped || time < game_starttime)
		return;

	IL_EACH(g_damagedbycontents, it.damagedbycontents,
	{
		if (it.move_movetype == MOVETYPE_NOCLIP) continue;
		CreatureFrame_Liquids(it);
		CreatureFrame_FallDamage(it);
		it.oldvelocity = it.velocity;
	});
}

void Pause_TryPause_Dedicated(entity this)
{
	if (player_count == 0)
		setpause(1);
}

void Pause_TryPause()
{
	int n = 0, p = 0;
	FOREACH_CLIENT(IS_REAL_CLIENT(it), {
		if (PHYS_INPUT_BUTTON_CHAT(it)) ++p;
		++n;
	});
	if (!n) return;
	if (n == p)
		setpause(1);
	else
		setpause(0);
}

void SV_PausedTic(float elapsedtime)
{
	if (!server_is_dedicated)
	{
		if (autocvar_sv_autopause)
			Pause_TryPause();
		else
			setpause(0);
	}
}

void dedicated_print(string input)
{
	if (server_is_dedicated) print(input);
}

void make_safe_for_remove(entity e)
{
    if (e.initialize_entity)
    {
        entity ent, prev = NULL;
        for (ent = initialize_entity_first; ent; )
        {
            if ((ent == e) || ((ent.classname == "initialize_entity") && (ent.enemy == e)))
            {
                                                                                              
                                         
                if (prev)
                {
                    prev.initialize_entity_next = ent.initialize_entity_next;
                    ent = prev.initialize_entity_next;
                }
                else
                {
                    initialize_entity_first = ent.initialize_entity_next;
                    ent = initialize_entity_first;
                }
            }
            else
            {
                prev = ent;
                ent = ent.initialize_entity_next;
            }
        }
    }
}

void remove_except_protected(entity e)
{
	if(e.remove_except_protected_forbidden)
		error("not allowed to remove this at this point");
	builtin_remove(e);
}

void remove_unsafely(entity e)
{
    if(e.classname == "spike")
        error("Removing spikes is forbidden (crylink bug), please report");
    builtin_remove(e);
}

void remove_safely(entity e)
{
    make_safe_for_remove(e);
    builtin_remove(e);
}

  
             
          

                                      
             
  

bool game_delay_last;

void systems_update();
void sys_phys_update(entity this, float dt);
void StartFrame()
{
	DuelActionTelemetry_ForcePov();
                                                                                                                      
    IL_EACH(g_players, IS_FAKE_CLIENT(it), sys_phys_update(it, frametime));
	DuelCameraMotor_Frame();
    IL_EACH(g_players, IS_FAKE_CLIENT(it), PlayerPreThink(it));
	DuelActionTelemetry_Frame();

	execute_next_frame();
	if (autocvar_sv_autopause && !server_is_dedicated) Pause_TryPause();

	delete_fn = remove_unsafely;                        
	serverprevtime = servertime;
	servertime = time;
	serverframetime = frametime;

#ifdef PROFILING
	if(time > client_cefc_accumulatortime + 1)
	{
		float t = client_cefc_accumulator / (time - client_cefc_accumulatortime);
		int c_seeing = 0;
		int c_seen = 0;
		FOREACH_CLIENT(true, {
			if(IS_REAL_CLIENT(it))
				++c_seeing;
			if(IS_PLAYER(it))
				++c_seen;
		});
		LOG_INFO(
		    "CEFC time: ", ftos(t * 1000), "ms; ",
            "CEFC calls per second: ", ftos(c_seeing * (c_seen - 1) / t), "; ",
            "CEFC 100% load at: ", ftos(solve_quadratic(t, -t, -1) * '0 1 0')
        );
		client_cefc_accumulatortime = time;
		client_cefc_accumulator = 0;
	}
#endif

	IL_EACH(g_projectiles, it.csqcprojectile_clientanimate, CSQCProjectile_Check(it));

	if (RedirectionThink()) return;

	UncustomizeEntitiesRun();
	InitializeEntitiesRun();

	WarpZone_StartFrame();

	sys_frametime = autocvar_sys_ticrate * autocvar_slowmo;
	if (sys_frametime <= 0) sys_frametime = 1.0 / 60.0;                          

	if (timeout_status == TIMEOUT_LEADTIME)                                                                        
		orig_slowmo = autocvar_slowmo;                                             

	                                                                                 
	bool game_delay = (time < game_starttime);
	if (autocvar_sv_eventlog && game_delay_last && !game_delay)
		GameLogEcho(":startdelay_ended");
	game_delay_last = game_delay;

	CreatureFrame_All();
	CheckRules_World();

	if (warmup_stage && !game_stopped && warmup_limit > 0 && time - game_starttime >= warmup_limit) {
		ReadyRestart(true);
		return;
	}

	bot_serverframe();
	anticheat_startframe();
	MUTATOR_CALLHOOK(SV_StartFrame);

	GlobalStats_updateglobal();
    FOREACH_CLIENT(true, GlobalStats_update(it));
    IL_EACH(g_players, IS_FAKE_CLIENT(it), PlayerPostThink(it));
}

.vector originjitter;
.vector anglesjitter;
.float anglejitter;
.string gametypefilter;
.string cvarfilter;

void SV_OnEntityPreSpawnFunction(entity this)
{
	if (this)
	if (this.gametypefilter != "")
	if (!isGametypeInFilter(MapInfo_LoadedGametype, teamplay, have_team_spawns, this.gametypefilter))
	{
		delete(this);
		return;
	}
	if (this.cvarfilter != "" && !expr_evaluate(this.cvarfilter)) {
		delete(this);
		return;
	}

	if (q3compat && DoesQ3ARemoveThisEntity(this)) {
		delete(this);
		return;
	}

	set_movetype(this, this.movetype);

	if (this.monster_attack) {
		IL_PUSH(g_monster_targets, this);
    }

	                                               
	if (this.angles == '0 -1 0') {
		this.angles = '-90 0 0';
	} else if (this.angles == '0 -2 0') {
		this.angles = '+90 0 0';
    }

    #define X(out, in) MACRO_BEGIN \
        if (in != 0) { out = out + (random() * 2 - 1) * in; } \
    MACRO_END
    X(this.origin.x, this.originjitter.x); X(this.origin.y, this.originjitter.y); X(this.origin.z, this.originjitter.z);
    X(this.angles.x, this.anglesjitter.x); X(this.angles.y, this.anglesjitter.y); X(this.angles.z, this.anglesjitter.z);
    X(this.angles.y, this.anglejitter);
    #undef X

	if (MUTATOR_CALLHOOK(OnEntityPreSpawn, this)) {
		delete(this);
		return;
	}
}

string GetField_fullspawndata(entity e, string f, ...)
                                                               
                                                        
                                                       
  
                                                              
  
                                                                        
                                                                                          
                                                                                            
  
                                                     
   
{
	string v = string_null;

	if (!e.fullspawndata)
	{
		                                                                                                                          
		return v;
	}

	if (strstrofs(e.fullspawndata, "//", 0) >= 0)
	{
		                                                                 
		                                                                       
		LOG_WARNF("^1EDICT %s fullspawndata contains unsupported //comment^7%s", ftos(num_for_edict(e)), e.fullspawndata);
		return v;
	}

	                                                                                  
	                                                         

	                                                                                    
	for (int t = tokenize_console(e.fullspawndata) - 3; t > 0; t -= 2)
	{
		                                                                                       
		if (argv(t) == f)
		{
			v = argv(t + 1);
			break;
		}
	}

	                                       

	if (v && ...(0, bool) == true)
	{
		v = strreplace("\\", "/", v);
		if (whichpack(v) == "")
			return string_null;
	}

	return v;
}

void WarpZone_PostInitialize_Callback()
{
	                                      
	entity tracetest_ent = spawn();
	setsize(tracetest_ent, PL_MIN_CONST, PL_MAX_CONST);
	tracetest_ent.dphitcontentsmask = DPCONTENTS_SOLID | DPCONTENTS_BODY | DPCONTENTS_PLAYERCLIP | DPCONTENTS_BOTCLIP;
	                                                        
	for(entity e = NULL; (e = find(e, classname, "trigger_warpzone")); )
		waypoint_spawnforteleporter_wz(e, tracetest_ent);
	delete(tracetest_ent);
}

                      
void URI_Get_Callback(float id, float status, string data)
{
	if(url_URI_Get_Callback(id, status, data))
	{
		          
	}
	else if (id == URI_GET_DISCARD)
	{
		          
	}
	else if (id >= URI_GET_CURL && id <= URI_GET_CURL_END)
	{
		              
		Curl_URI_Get_Callback(id, status, data);
	}
	else if (id >= URI_GET_IPBAN && id <= URI_GET_IPBAN_END)
	{
		                  
		OnlineBanList_URI_Get_Callback(id, status, data);
	}
	else if (MUTATOR_CALLHOOK(URI_GetCallback, id, status, data))
	{
		                       
	}
	else
	{
		LOG_INFO("Received HTTP request data for an invalid id ", ftos(id), ".");
	}
}

  
                  
    

                                 
                  
  
void main ()
{

}
