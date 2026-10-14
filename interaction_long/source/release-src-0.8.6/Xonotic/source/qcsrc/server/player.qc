#include "player.qh"

#include <common/anim.qh>
#include <common/animdecide.qh>
#include <common/csqcmodel_settings.qh>
#include <common/deathtypes/all.qh>
#include <common/effects/all.qh>
#include <common/effects/qc/_mod.qh>
#include <common/gamemodes/_mod.qh>
#include <common/gamemodes/sv_rules.qh>
#include <common/mapobjects/_mod.qh>
#include <common/mapobjects/subs.qh>
#include <common/mapobjects/teleporters.qh>
#include <common/minigames/sv_minigames.qh>
#include <common/mutators/mutator/status_effects/_mod.qh>
#include <common/mutators/mutator/waypoints/waypointsprites.qh>
#include <common/physics/player.qh>
#include <common/playerstats.qh>
#include <common/state.qh>
#include <common/wepent.qh>
#include <lib/csqcmodel/sv_model.qh>
#include <server/bot/api.qh>
#include <server/cheats.qh>
#include <server/client.qh>
#include <server/clientkill.qh>
#include <server/command/common.qh>
#include <server/command/vote.qh>
#include <server/damage.qh>
#include <server/handicap.qh>
#include <server/hook.qh>
#include <server/main.qh>
#include <server/mutators/_mod.qh>
#include <server/portals.qh>
#include <server/teamplay.qh>
#include <server/weapons/accuracy.qh>
#include <server/weapons/common.qh>
#include <server/weapons/throwing.qh>
#include <server/weapons/weaponstats.qh>
#include <server/weapons/weaponsystem.qh>
#include <server/world.qh>

void Drop_Special_Items(entity player)
{
	                                                    
	                                                  

	MUTATOR_CALLHOOK(DropSpecialItems, player);
}

void CopyBody_Think(entity this)
{
	if(this.CopyBody_nextthink && time > this.CopyBody_nextthink)
	{
		this.CopyBody_think(this);
		if(wasfreed(this))
			return;
		this.CopyBody_nextthink = this.nextthink;
		this.CopyBody_think = getthink(this);
		setthink(this, CopyBody_Think);
	}
	CSQCMODEL_AUTOUPDATE(this);
	this.nextthink = time;
}
void CopyBody(entity this, float keepvelocity)
{
	if (this.effects & EF_NODRAW)
		return;
	entity clone = new(body);
	clone.enemy = this;
	clone.lip = this.lip;
	clone.colormap = this.colormap;
	clone.iscreature = this.iscreature;
	clone.teleportable = this.teleportable;
	clone.damagedbycontents = this.damagedbycontents;
	if(clone.damagedbycontents)
		IL_PUSH(g_damagedbycontents, clone);
	clone.angles = this.angles;
	clone.v_angle = this.v_angle;
	clone.avelocity = this.avelocity;
	clone.damageforcescale = this.damageforcescale;
	clone.effects = this.effects;
	clone.glowmod = this.glowmod;
	clone.event_damage = this.event_damage;
	clone.event_heal = this.event_heal;
	clone.anim_state = this.anim_state;
	clone.anim_time = this.anim_time;
	clone.anim_lower_action = this.anim_lower_action;
	clone.anim_lower_time = this.anim_lower_time;
	clone.anim_upper_action = this.anim_upper_action;
	clone.anim_upper_time = this.anim_upper_time;
	clone.anim_implicit_state = this.anim_implicit_state;
	clone.anim_implicit_time = this.anim_implicit_time;
	clone.anim_lower_implicit_action = this.anim_lower_implicit_action;
	clone.anim_lower_implicit_time = this.anim_lower_implicit_time;
	clone.anim_upper_implicit_action = this.anim_upper_implicit_action;
	clone.anim_upper_implicit_time = this.anim_upper_implicit_time;
	clone.dphitcontentsmask = this.dphitcontentsmask;
	clone.death_time = this.death_time;
	clone.pain_finished = this.pain_finished;
	SetResourceExplicit(clone, RES_HEALTH, GetResource(this, RES_HEALTH));
	SetResourceExplicit(clone, RES_ARMOR, GetResource(this, RES_ARMOR));
	clone.armortype = this.armortype;
	clone.model = this.model;
	clone.modelindex = this.modelindex;
	clone.skin = this.skin;
	clone.species = this.species;
	clone.move_qcphysics = false;                                                
	set_movetype(clone, this.move_movetype);
	clone.solid = this.solid;
	clone.takedamage = this.takedamage;
	setcefc(clone, getcefc(this));
	clone.uncustomizeentityforclient = this.uncustomizeentityforclient;
	clone.uncustomizeentityforclient_set = this.uncustomizeentityforclient_set;
	if (keepvelocity == 1)
		clone.velocity = this.velocity;
	clone.oldvelocity = clone.velocity;
	clone.alpha = this.alpha;
	clone.fade_time = this.fade_time;
	clone.fade_rate = this.fade_rate;
	                             
	setorigin(clone, this.origin);
	setsize(clone, this.mins, this.maxs);
	clone.reset = SUB_Remove;
	clone._ps = this._ps;

	Drag_MoveDrag(this, clone);

	if(clone.colormap <= maxclients && clone.colormap > 0)
		clone.colormap = 1024 + this.clientcolors;

	CSQCMODEL_AUTOINIT(clone);
	clone.CopyBody_nextthink = this.nextthink;
	clone.CopyBody_think = getthink(this);
	clone.nextthink = time;
	setthink(clone, CopyBody_Think);
	                                                                                      
	animdecide_load_if_needed(clone);
	animdecide_setframes(clone, false, frame, frame1time, frame2, frame2time);

	IL_PUSH(g_clones, clone);

	MUTATOR_CALLHOOK(CopyBody, this, clone, keepvelocity);
}

void player_setupanimsformodel(entity this)
{
	                      
	animdecide_load_if_needed(this);
	animdecide_setstate(this, 0, false);
}

void player_anim(entity this)
{
	int deadbits = (this.anim_state & (ANIMSTATE_DEAD1 | ANIMSTATE_DEAD2));
	if(IS_DEAD(this)) {
		if (!deadbits) {
			                                          
			if(random() < 0.5)
				deadbits = ANIMSTATE_DEAD1;
			else
				deadbits = ANIMSTATE_DEAD2;
		}
	} else {
		                                    
		deadbits = 0;
	}
	int animbits = deadbits;
	if(STAT(FROZEN, this))
		animbits |= ANIMSTATE_FROZEN;
	if(this.move_movetype == MOVETYPE_FOLLOW)
		animbits |= ANIMSTATE_FOLLOW;
	if(IS_DUCKED(this))
		animbits |= ANIMSTATE_DUCK;
	animdecide_setstate(this, animbits, false);
	animdecide_setimplicitstate(this, IS_ONGROUND(this));
}

void PlayerCorpseDamage(entity this, entity inflictor, entity attacker, float damage, int deathtype, .entity weaponentity, vector hitloc, vector force)
{
	float take, save;
	vector v;
	Violence_GibSplash_At(hitloc, force, 2, bound(0, damage, 200) / 16, this, attacker);

	v = healtharmor_applydamage(GetResource(this, RES_ARMOR), autocvar_g_balance_armor_blockpercent, deathtype, damage);
	take = v.x;
	save = v.y;

	if(sound_allowed(MSG_BROADCAST, attacker))
	{
		if (save > 10)
			sound (this, CH_SHOTS, SND_ARMORIMPACT, VOL_BASE, ATTEN_NORM);
		else if (take > 30)
			sound (this, CH_SHOTS, SND_BODYIMPACT2, VOL_BASE, ATTEN_NORM);
		else if (take > 10)
			sound (this, CH_SHOTS, SND_BODYIMPACT1, VOL_BASE, ATTEN_NORM);
	}

	if (take > 50)
		Violence_GibSplash_At(hitloc, force * -0.1, 3, 1, this, attacker);
	if (take > 100)
		Violence_GibSplash_At(hitloc, force * -0.2, 3, 1, this, attacker);

	TakeResource(this, RES_ARMOR, save);
	TakeResource(this, RES_HEALTH, take);
	                                   
	this.pauseregen_finished = max(this.pauseregen_finished, time + autocvar_g_balance_pause_health_regen);

	this.dmg_save = this.dmg_save + save;                    
	this.dmg_take = this.dmg_take + take;                    
	this.dmg_inflictor = inflictor;

	if (GetResource(this, RES_HEALTH) <= -autocvar_sv_gibhealth && this.alpha >= 0)
	{
		                                    
		this.frame = 0;
		                            
		this.view_ofs = '0 0 4';

		Violence_GibSplash(this, 1, 1, attacker);
		this.alpha = -1;
		this.solid = SOLID_NOT;                 
		this.takedamage = DAMAGE_NO;                 
		if(this.damagedbycontents)
			IL_REMOVE(g_damagedbycontents, this);
		this.damagedbycontents = false;
	}
}

void PlayerDamage(entity this, entity inflictor, entity attacker, float damage, int deathtype, .entity weaponentity, vector hitloc, vector force)
{
	vector v;
	float initial_health = max(GetResource(this, RES_HEALTH), 0);
	float initial_armor = max(GetResource(this, RES_ARMOR), 0);
	float take = 0, save = 0;

	if (damage)
	{
		if(!DEATH_ISSPECIAL(deathtype))
		{
			damage *= Handicap_GetTotalHandicap(this);
			if (this != attacker && IS_PLAYER(attacker))
			{
				damage /= Handicap_GetTotalHandicap(attacker);
			}
		}

		if (STAT(FROZEN, this))
		{
			if (!ITEM_DAMAGE_NEEDKILL(deathtype))
				damage = 0;
		}
		else if (StatusEffects_active(STATUSEFFECT_SpawnShield, this) && autocvar_g_spawnshield_blockdamage < 1)
			damage *= 1 - bound(0, autocvar_g_spawnshield_blockdamage, 1);

		if(deathtype & HITTYPE_SOUND)                                                    
		{
			vector ear1, ear2;
			vector d;
			float f;
			ear1 = this.origin;
			ear1_z += 0.125 * this.view_ofs.z + 0.875 * this.maxs.z;       
			ear2 = ear1;
			makevectors(this.angles);
			ear1 += v_right * -10;
			ear2 += v_right * +10;
			d = inflictor.origin - this.origin;
			if (d)
				f = (d * v_right) / vlen(d);                                          
			else
				f = 0;                   
			force = v_right * vlen(force);
			Violence_GibSplash_At(ear1, force * -1, 2, bound(0, damage, 25) / 2 * (0.5 - 0.5 * f), this, attacker);
			Violence_GibSplash_At(ear2, force,      2, bound(0, damage, 25) / 2 * (0.5 + 0.5 * f), this, attacker);
			if(f > 0)
			{
				hitloc = ear1;
				force = force * -1;
			}
			else
			{
				hitloc = ear2;
				                        
			}
		}
		else
			Violence_GibSplash_At(hitloc, force, 2, bound(0, damage, 200) / 16, this, attacker);

		v = healtharmor_applydamage(GetResource(this, RES_ARMOR), autocvar_g_balance_armor_blockpercent, deathtype, damage);
		take = v.x;
		save = v.y;
	}

	if(attacker == this)
	{
		                                                                   
		                               
		                     
		this.istypefrag = 0;
	}
	else if(IS_PLAYER(attacker))
	{
		this.pusher = attacker;
		this.pushltime = time + autocvar_g_maxpushtime;
		this.istypefrag = PHYS_INPUT_BUTTON_CHAT(this);
	}
	else if(time < this.pushltime)
	{
		attacker = this.pusher;
		this.pushltime = max(this.pushltime, time + 0.6);
	}
	else
	{
		this.pushltime = 0;
		this.istypefrag = 0;
	}

	MUTATOR_CALLHOOK(PlayerDamage_SplitHealthArmor, inflictor, attacker, this, force, take, save, deathtype, damage);
	take = bound(0, M_ARGV(4, float), GetResource(this, RES_HEALTH));
	save = bound(0, M_ARGV(5, float), GetResource(this, RES_ARMOR));
	float excess = max(0, damage - take - save);

	if(sound_allowed(MSG_BROADCAST, attacker))
	{
		if (save > 10 && (initial_health - take) > 0)                                                 
			sound (this, CH_SHOTS, SND_ARMORIMPACT, VOL_BASE, ATTEN_NORM);
		else if (take > 30)
			sound (this, CH_SHOTS, SND_BODYIMPACT2, VOL_BASE, ATTEN_NORM);
		else if (take > 10)
			sound (this, CH_SHOTS, SND_BODYIMPACT1, VOL_BASE, ATTEN_NORM);                               
	}

	if (take > 50)
		Violence_GibSplash_At(hitloc, force * -0.1, 3, 1, this, attacker);
	if (take > 100)
		Violence_GibSplash_At(hitloc, force * -0.2, 3, 1, this, attacker);

	if (!StatusEffects_active(STATUSEFFECT_SpawnShield, this) || autocvar_g_spawnshield_blockdamage < 1)
	{
		if (!(this.flags & FL_GODMODE))
		{
			TakeResource(this, RES_ARMOR, save);
			TakeResource(this, RES_HEALTH, take);
			                                   
			if(take)
				this.pauseregen_finished = max(this.pauseregen_finished, time + autocvar_g_balance_pause_health_regen);

			if (time > this.pain_finished && !STAT(FROZEN, this))                                          
			{
				this.pain_finished = time + 0.5;	         

				if(autocvar_sv_gentle < 1) {
					if(this.classname != "body")                                                                               
					{
						if (!this.animstate_override)
						{
							if (random() > 0.5)
								animdecide_setaction(this, ANIMACTION_PAIN1, true);
							else
								animdecide_setaction(this, ANIMACTION_PAIN2, true);
						}
					}
					float myhp = GetResource(this, RES_HEALTH);
					if(myhp > 1)
					if(myhp < 25 || !(DEATH_WEAPONOF(deathtype).spawnflags & WEP_FLAG_CANCLIMB) || take > 20 || attacker != this)
					if(sound_allowed(MSG_BROADCAST, attacker))
					                                                                                                              
					{
						if(deathtype == DEATH_FALL.m_id)
							PlayerSound(this, playersound_fall, CH_PAIN, VOL_BASE, VOICETYPE_PLAYERSOUND);
						else if(myhp > 75)
							PlayerSound(this, playersound_pain100, CH_PAIN, VOL_BASE, VOICETYPE_PLAYERSOUND);
						else if(myhp > 50)
							PlayerSound(this, playersound_pain75, CH_PAIN, VOL_BASE, VOICETYPE_PLAYERSOUND);
						else if(myhp > 25)
							PlayerSound(this, playersound_pain50, CH_PAIN, VOL_BASE, VOICETYPE_PLAYERSOUND);
						else
							PlayerSound(this, playersound_pain25, CH_PAIN, VOL_BASE, VOICETYPE_PLAYERSOUND);
					}
				}
			}

			                                
			float shake;
			if(IS_BOT_CLIENT(this) && GetResource(this, RES_HEALTH) >= 1)
			{
				shake = damage * 5 / (bound(0,skill,100) + 1);
				this.v_angle_x = this.v_angle.x + (random() * 2 - 1) * shake;
				this.v_angle_y = this.v_angle.y + (random() * 2 - 1) * shake;
				this.v_angle_x = bound(-90, this.v_angle.x, 90);
			}
		}
		else
			this.max_armorvalue += (save + take);
	}
	this.dmg_save = this.dmg_save + save;                    
	this.dmg_take = this.dmg_take + take;                    
	this.dmg_inflictor = inflictor;

	bool abot = (IS_BOT_CLIENT(attacker));
	bool vbot = (IS_BOT_CLIENT(this));

	bool valid_damage_for_weaponstats = false;
	Weapon awep = WEP_Null;

	if (!(round_handler_IsActive() && !round_handler_IsRoundStarted()) && time >= game_starttime)
	if(vbot || IS_REAL_CLIENT(this))
	if(abot || IS_REAL_CLIENT(attacker))
	if(attacker && this != attacker)
	if (DIFF_TEAM(this, attacker) && (!STAT(FROZEN, this) || this.freeze_time > time))
	{
		if(DEATH_ISSPECIAL(deathtype))
			awep = attacker.(weaponentity).m_weapon;
		else
			awep = DEATH_WEAPONOF(deathtype);
		valid_damage_for_weaponstats = true;
	}

	float dh = initial_health - max(GetResource(this, RES_HEALTH), 0);                     
	float da = initial_armor - max(GetResource(this, RES_ARMOR), 0);                    
	if(valid_damage_for_weaponstats)
	{
		WeaponStats_LogDamage(awep.m_id, abot, this.(weaponentity).m_weapon.m_id, vbot, dh + da);
	}

	bool forbid_logging_damage = MUTATOR_CALLHOOK(PlayerDamaged, attacker, this, dh, da, hitloc, deathtype, damage);

	if ((dh || da) && !forbid_logging_damage)
	{
		float realdmg = damage - excess;
		if ((this != attacker || deathtype == DEATH_KILL.m_id) && realdmg && !STAT(FROZEN, this)
			&& (!(round_handler_IsActive() && !round_handler_IsRoundStarted()) && time >= game_starttime))
		{
			if (IS_PLAYER(attacker) && DIFF_TEAM(attacker, this) && deathtype != DEATH_KILL.m_id)
				GameRules_scoring_add(attacker, DMG, realdmg);
			if (IS_PLAYER(this))
				GameRules_scoring_add(this, DMGTAKEN, realdmg);
		}
	}

	if (GetResource(this, RES_HEALTH) < 1)
	{
		bool defer_ClientKill_Now_TeamChange = false;

		if(this.alivetime)
		{
			PlayerStats_GameReport_Event_Player(this, PLAYERSTATS_ALIVETIME, time - this.alivetime);
			this.alivetime = 0;
		}

		if(valid_damage_for_weaponstats)
			WeaponStats_LogKill(awep.m_id, abot, this.(weaponentity).m_weapon.m_id, vbot);

		if(autocvar_sv_gentle < 1)
		if(sound_allowed(MSG_BROADCAST, attacker))
		{
			if(deathtype == DEATH_DROWN.m_id)
				PlayerSound(this, playersound_drown, CH_PAIN, VOL_BASE, VOICETYPE_PLAYERSOUND);
			else
				PlayerSound(this, playersound_death, CH_PAIN, VOL_BASE, VOICETYPE_PLAYERSOUND);
		}

		                            
		if(this.killindicator)
		{
			delete(this.killindicator);
			this.killindicator = NULL;
			if(this.killindicator_teamchange)
				defer_ClientKill_Now_TeamChange = true;

			if(this.classname == "body")
			if(deathtype == DEATH_KILL.m_id)
			{
				                                                    
				Send_Effect(EFFECT_ROCKET_EXPLODE, this.origin, '0 0 0', 1);
			}
		}

		                            
		if(this.classname != "body")
			Obituary(attacker, inflictor, this, deathtype, weaponentity);

		                                              
		Weapon w = DEATH_WEAPONOF(deathtype);
		if(w != WEP_Null && accuracy_isgooddamage(attacker, this))
			CS(attacker).accuracy.(accuracy_frags[w.m_id-1]) += 1;

		this.respawn_time = 0;
		MUTATOR_CALLHOOK(PlayerDies, inflictor, attacker, this, deathtype, damage);
		damage = M_ARGV(4, float);
		excess = max(0, damage - take - save);

		                                            
		for(int slot = 0; slot < MAX_WEAPONSLOTS; ++slot)
		{
			.entity went = weaponentities[slot];
			if(!this.(went))
				continue;                                                                                     
			Weapon wep = this.(went).m_weapon;
			wep.wr_playerdeath(wep, this, went);
		}

		RemoveGrapplingHooks(this);

		Portal_ClearAllLater(this);

		this.fixangle = true;

		if(defer_ClientKill_Now_TeamChange)
			ClientKill_Now_TeamChange(this);                                  

		                                                      
		                                                              
		if(GetResource(this, RES_HEALTH) >= 1 || !(IS_PLAYER(this) || this.classname == "body"))
			return;

		if (!this.respawn_time)                                             
			calculate_player_respawn_time(this);

		                                         

		Unfreeze(this, false);                          

		                  
		WaypointSprite_PlayerDead(this);
		                 
		for(int slot = 0; slot < MAX_WEAPONSLOTS; ++slot)
		{
			.entity went = weaponentities[slot];
			SpawnThrownWeapon(this, this.origin + (this.mins + this.maxs) * 0.5, this.(went).m_weapon, went);
		}

		                       
		this.alpha = default_player_alpha;
		                                       
		this.angles_x = 0;
		this.angles_z = 0;
		             
		this.avelocity = '0 0 0';
		                      
		this.view_ofs = '0 0 -8';
		if(this.move_movetype == MOVETYPE_NOCLIP)
		{
			                                                                                  
			                                                       
			this.velocity = '0 0 0';
		}
		else
		{
			                  
			set_movetype(this, MOVETYPE_TOSS);
		}
		                   
		this.solid = SOLID_CORPSE;
		PS(this).ballistics_density = autocvar_g_ballistics_density_corpse;
		                           
		UNSET_ONGROUND(this);
		                  
		this.deadflag = DEAD_DYING;
		                                  
		this.teleportable = TELEPORT_SIMPLE;

		STAT(AIR_FINISHED, this) = 0;

		this.death_time = time;
		if (random() < 0.5)
			animdecide_setstate(this, this.anim_state | ANIMSTATE_DEAD1, true);
		else
			animdecide_setstate(this, this.anim_state | ANIMSTATE_DEAD2, true);

		                                       
		this.event_damage = PlayerCorpseDamage;
		this.event_heal = func_null;
		                                                               
		this.event_damage(this, inflictor, attacker, excess, deathtype, weaponentity, hitloc, force);

		                           
		SUB_SetFade (this, time + 6 + random (), 1);
		                                                 
		if(this.classname == "body" && getthink(this) != CopyBody_Think) {
			this.CopyBody_think = getthink(this);
			this.CopyBody_nextthink = this.nextthink;
			setthink(this, CopyBody_Think);
			this.nextthink = time;
		}

		if(autocvar_sv_gentle > 0 || autocvar_ekg || this.classname == "body") {
			                
			                                                                                     
			this.event_damage(this, inflictor, attacker, autocvar_sv_gibhealth + 1, deathtype, weaponentity, hitloc, force);
		}

		                                                
		if(this.classname != "body")
		{
			FOREACH(Weapons, it != WEP_Null,
			{
				it.wr_resetplayer(it, this);
				for(int slot = 0; slot < MAX_WEAPONSLOTS; ++slot)
				{
					ATTACK_FINISHED_FOR(this, it.m_id, slot) = 0;
				}
			});
		}
		MUTATOR_CALLHOOK(PlayerDied, this);
	}
}

bool PlayerHeal(entity targ, entity inflictor, float amount, float limit)
{
	if(GetResource(targ, RES_HEALTH) <= 0 || GetResource(targ, RES_HEALTH) >= limit)
		return false;

	GiveResourceWithLimit(targ, RES_HEALTH, amount, limit);
	return true;
}

void precache_playermodel(string m)
{
	int globhandle, i, n;
	string f;

	                              
	int j = strstrofs(m, ":", 0);
	if(j >= 0)
		m = substring(m, 0, j);

	if(substring(m, -9, 5) == "_lod1")
		return;
	if(substring(m, -9, 5) == "_lod2")
		return;
	precache_model(m);
	f = strcat(substring(m, 0, -5), "_lod1", substring(m, -4, -1));
	if(fexists(f))
		precache_model(f);
	f = strcat(substring(m, 0, -5), "_lod2", substring(m, -4, -1));
	if(fexists(f))
		precache_model(f);

	globhandle = search_begin(strcat(m, "_*.sounds"), true, false);
	if (globhandle < 0)
		return;
	n = search_getsize(globhandle);
	for (i = 0; i < n; ++i)
	{
		                                                 
		f = search_getfilename(globhandle, i);
		PrecachePlayerSounds(f);
	}
	search_end(globhandle);
}
void precache_all_playermodels(string pattern)
{
	int globhandle = search_begin(pattern, true, false);
	if (globhandle < 0) return;
	int n = search_getsize(globhandle);
	for (int i = 0; i < n; ++i)
	{
		string s = search_getfilename(globhandle, i);
		precache_playermodel(s);
	}
	search_end(globhandle);
}

void precache_playermodels(string s)
{
	FOREACH_WORD(s, true, { precache_playermodel(it); });
}

PRECACHE(PlayerModels)
{
                                            
    if (autocvar_sv_precacheplayermodels)
    {
        PrecachePlayerSounds("sound/player/default.sounds");
        precache_all_playermodels("models/player/*.zym");
        precache_all_playermodels("models/player/*.dpm");
        precache_all_playermodels("models/player/*.md3");
        precache_all_playermodels("models/player/*.psk");
        precache_all_playermodels("models/player/*.iqm");
    }

    if (autocvar_sv_defaultcharacter)
    {
		precache_playermodels(autocvar_sv_defaultplayermodel_red);
		precache_playermodels(autocvar_sv_defaultplayermodel_blue);
		precache_playermodels(autocvar_sv_defaultplayermodel_yellow);
		precache_playermodels(autocvar_sv_defaultplayermodel_pink);
		precache_playermodels(autocvar_sv_defaultplayermodel);
    }
}
