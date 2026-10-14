#include "quake3.qh"

#include <common/gamemodes/_mod.qh>
#include <common/gamemodes/gamemode/ctf/sv_ctf.qh>
#include <common/mapobjects/trigger/counter.qh>
#include <common/mapobjects/triggers.qh>
#include <common/mutators/mutator/buffs/buffs.qh>
#include <common/mutators/mutator/buffs/sv_buffs.qh>
#include <common/mutators/mutator/powerups/_mod.qh>
#include <common/mutators/mutator/status_effects/_mod.qh>
#include <common/notifications/all.qh>
#include <common/resources/sv_resources.qh>
#include <common/stats.qh>
#include <common/weapons/_all.qh>
#include <common/weapons/_all.qh>
#include <server/client.qh>
#include <server/items/items.qh>
#include <server/items/spawning.qh>
#include <server/world.qh>

                        
                                                                             
                        

                                         
                                                 
                                                 
                                                 
                                                 
                                                 
                                                 
                                                 
                                             
                                                 
                                            
                                                     
                                             
                                             
                                                 
                                                 
                                             
                                                 
                              

                                                                                          
  

                 
SPAWNFUNC_Q3_COND(weapon_shotgun, ammo_shells, (q3compat & Q3COMPAT_ARENA), WEP_MACHINEGUN, WEP_SHOTGUN)

                 
                                                                                                                            
SPAWNFUNC_Q3AMMO_COND(ammo_bullets, (q3compat & Q3COMPAT_ARENA), WEP_SHOTGUN, WEP_MACHINEGUN)

               
SPAWNFUNC_Q3AMMO(ammo_grenades, WEP_MORTAR)

                                          
                                                                                                                                                                                 
SPAWNFUNC_Q3(weapon_prox_launcher, ammo_mines, WEP_MORTAR)

                              
SPAWNFUNC_Q3(weapon_chaingun, ammo_belt, WEP_HLAC)

                                       
SPAWNFUNC_Q3(weapon_hmg, ammo_hmg, WEP_HLAC)

                                                            
SPAWNFUNC_Q3_COND(weapon_nailgun, ammo_nails, autocvar_sv_mapformat_is_quake3, WEP_CRYLINK, WEP_ELECTRO)

                
SPAWNFUNC_Q3(weapon_lightning, ammo_lightning, WEP_ELECTRO)

                  
SPAWNFUNC_Q3(weapon_plasmagun, ammo_cells, WEP_HAGAR)

                 
SPAWNFUNC_Q3(weapon_railgun, ammo_slugs, WEP_VORTEX)

                             
SPAWNFUNC_Q3_COND(weapon_bfg, ammo_bfg, cvar_string("g_mod_balance") == "XDF", WEP_CRYLINK, WEP_FIREBALL)
	                                                                                      

                         
SPAWNFUNC_WEAPON(weapon_grapplinghook, WEP_HOOK)

           
SPAWNFUNC_Q3AMMO(ammo_rockets, WEP_DEVASTATOR)

                   
SPAWNFUNC_ITEM(weapon_gauntlet, WEP_TUBA)

        
SPAWNFUNC_ITEM(item_armor_body, ITEM_ArmorMega)
SPAWNFUNC_ITEM(item_armor_combat, ITEM_ArmorBig)
SPAWNFUNC_ITEM(item_armor_shard, ITEM_ArmorSmall)
SPAWNFUNC_ITEM(item_armor_green, ITEM_ArmorMedium)        

           
SPAWNFUNC_ITEM(item_quad, ITEM_Strength)
SPAWNFUNC_ITEM(item_enviro, ITEM_Shield)
SPAWNFUNC_ITEM(item_haste, ITEM_Speed)
SPAWNFUNC_ITEM(item_invis, ITEM_Invisibility)

                                         
SPAWNFUNC_ITEM(holdable_medkit, ITEM_ArmorBig)

.float wait;
.float delay;

                            
void target_init_verify(entity this)
{
	entity trigger, targ;
	for(trigger = NULL; (trigger = find(trigger, classname, "trigger_multiple")); )
		for(targ = NULL; (targ = find(targ, targetname, trigger.target)); )
			if (targ.classname == "target_init" || targ.classname == "target_give" || targ.classname == "target_items")
			{
				trigger.wait = 0;
				trigger.delay = 0;
				targ.wait = 0;
				targ.delay = 0;

				                                            
				                                  
				                  
			}
}

void target_init_use(entity this, entity actor, entity trigger)
{
	if (!(this.spawnflags & 1))
	{
		SetResource(actor, RES_ARMOR, start_armorvalue);
		actor.pauserotarmor_finished = time + autocvar_g_balance_pause_armor_rot;
	}

	if (!(this.spawnflags & 2))
	{
		SetResource(actor, RES_HEALTH, start_health);
		actor.pauserothealth_finished = time + autocvar_g_balance_pause_health_rot;
		actor.pauseregen_finished = time + autocvar_g_balance_pause_health_regen;
	}

	if (!(this.spawnflags & 4))
	{
		if(this.spawnflags & 32)                         
		{
			SetResource(actor, RES_SHELLS, 0);
			SetResource(actor, RES_BULLETS, 0);
			SetResource(actor, RES_ROCKETS, 0);
			SetResource(actor, RES_CELLS, 0);
			SetResource(actor, RES_PLASMA, 0);
			SetResource(actor, RES_FUEL, 0);

			STAT(WEAPONS, actor) = WEPSET(SHOTGUN);
		}
		else
		{
			SetResource(actor, RES_SHELLS, start_ammo_shells);
			SetResource(actor, RES_BULLETS, start_ammo_nails);
			SetResource(actor, RES_ROCKETS, start_ammo_rockets);
			SetResource(actor, RES_CELLS, start_ammo_cells);
			SetResource(actor, RES_PLASMA, start_ammo_plasma);
			SetResource(actor, RES_FUEL, start_ammo_fuel);

			STAT(WEAPONS, actor) = start_weapons;
		}
	}

	if (!(this.spawnflags & 8))
	{
		FOREACH(StatusEffect, it.instanceOfPowerups,
		{
			it.m_remove(it, actor, STATUSEFFECT_REMOVE_NORMAL);
		});
		entity heldbuff = buff_FirstFromFlags(actor);
		if(heldbuff)                                                  
		{
			int buffid = heldbuff.m_id;
			Send_Notification(NOTIF_ONE, actor, MSG_MULTI, ITEM_BUFF_DROP, buffid);
			sound(actor, CH_TRIGGER, SND_BUFF_LOST, VOL_BASE, ATTN_NORM);
			if(!IS_INDEPENDENT_PLAYER(actor))
				Send_Notification(NOTIF_ALL_EXCEPT, actor, MSG_INFO, INFO_ITEM_BUFF_LOST, actor.netname, buffid);
			buff_RemoveAll(actor, STATUSEFFECT_REMOVE_NORMAL);
		}
	}

	if (!(this.spawnflags & 16))
	{
		                           
	}

	SUB_UseTargets(this, actor, trigger);
}

spawnfunc(target_init)
{
	this.use = target_init_use;
	InitializeEntity(this, target_init_verify, INITPRIO_FINDTARGET);
}

                          
void target_give_init(entity this)
{
	IL_EACH(g_items, it.targetname == this.target,
	{
		if (it.classname == "item_buff")
		{
			this.netname = cons(this.netname, it.buffdef.netname);
			this.buffs_finished += it.buffs_finished;
		}
		else
		{
			this.ammo_rockets          += it.ammo_rockets;
			this.ammo_cells            += it.ammo_cells;
			this.ammo_shells           += it.ammo_shells;
			this.ammo_nails            += it.ammo_nails;
			this.invincible_finished   += it.invincible_finished;
			this.strength_finished     += it.strength_finished;
			this.speed_finished        += it.speed_finished;
			this.invisibility_finished += it.invisibility_finished;
			this.health                += it.health;
			this.armorvalue            += it.armorvalue;

			this.netname = cons(this.netname, (it.itemdef.m_weapon) ? it.itemdef.m_weapon.netname : it.itemdef.netname);
		}

		                                                                          
		setthink(it, SUB_Remove);
		it.nextthink = time;
	});
	this.spawnflags = 2;
	this.spawnfunc_checked = true;
	spawnfunc_target_items(this);
	InitializeEntity(this, target_init_verify, INITPRIO_FINDTARGET);
}

spawnfunc(target_give)
{
	InitializeEntity(this, target_give_init, INITPRIO_FINDTARGET);
}

void score_use(entity this, entity actor, entity trigger)
{
	if(!IS_PLAYER(actor))
		return;
	actor.fragsfilter_cnt += this.count;
}
spawnfunc(target_score)
{
	if(!g_cts) { delete(this); return; }

	if(!this.count)
		this.count = 1;
	this.use = score_use;
}

void fragsfilter_use(entity this, entity actor, entity trigger)
{
	if(!IS_PLAYER(actor))
		return;
	if(actor.fragsfilter_cnt >= this.frags)
		SUB_UseTargets(this, actor, trigger);
}
spawnfunc(target_fragsFilter)
{
	if(!g_cts) { delete(this); return; }

	if(!this.frags)
		this.frags = 1;
	this.use = fragsfilter_use;
}

.bool notteam;
.bool notsingle;
.bool notfree;
.bool notta;
.bool notvq3;
.bool notcpm;
.string gametype;
bool DoesQ3ARemoveThisEntity(entity this)
{
	                                                     

	                                                                                     
	                                                                               
	if(cvar_string("g_mod_physics") == "Q3")
	{
		if(this.notvq3)
			return true;
	}
	else if(this.notcpm)
		return true;

	                                                                         
	                                                 
	if(this.notta)
		return true;

	                                                                           
	if(this.notsingle)
		if(maxclients == 1)
			return true;

	if(this.notteam)
		if(teamplay)
			return true;

	if(this.notfree)
		if(!teamplay)
			return true;

	if(this.gametype)
	{
		string gametypename;
		                                                                                                                                         
		gametypename = "ffa";
		if(teamplay)
			gametypename = "team";
		if(g_ctf)
			gametypename = "ctf";
		if(g_ctf && ctf_oneflag)
			gametypename = "oneflag";
		if(g_duel)
			gametypename = "tournament";
		if(maxclients == 1)
			gametypename = "single";
		                                                      
		if(strstrofs(this.gametype, gametypename, 0) < 0)
			return true;
	}

	return false;
}

int GetAmmoConsumptionQ3(string netname)
                                                                  
                                            
{
	switch (netname)
	{
		case "arc":	   return autocvar_g_balance_arc_beam_ammo;
		case "devastator": return autocvar_g_balance_devastator_ammo;
		case "machinegun": return autocvar_g_balance_machinegun_sustained_ammo;
		case "minelayer":  return autocvar_g_balance_minelayer_ammo;
		case "seeker":	   return autocvar_g_balance_seeker_tag_ammo;
		default:	   return cvar(strcat("g_balance_", netname, "_primary_ammo"));
	}
}

