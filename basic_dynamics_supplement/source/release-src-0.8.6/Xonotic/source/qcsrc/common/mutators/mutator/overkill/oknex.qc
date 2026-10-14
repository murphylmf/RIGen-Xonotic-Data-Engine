#include "oknex.qh"

#ifdef SVQC

.float oknex_lasthit;
#endif

#if defined(GAMEQC)

METHOD(OverkillNex, wr_glow, vector(OverkillNex this, int actor_colors, entity wepent))
{
	if (!WEP_CVAR(oknex, charge)) return '0 0 0';
	float charge = max(0.25, wepent.oknex_charge);
	float animlimit = WEP_CVAR(oknex, charge_animlimit);
	float f = min(1, charge / animlimit);
	vector mycolors = colormapPaletteColor(actor_colors & 0x0F, true);
	vector g = f * (mycolors * 0.3);
	if (charge > animlimit)
	{
		f = (charge - animlimit) / (1 - animlimit);
		g += f * (mycolors * 0.7);
	}
	                                                                              
	if (g == '0 0 0')
		g = '0 0 0.000001';
	return g;
}
#endif

#ifdef SVQC
REGISTER_MUTATOR(oknex_charge, true);

MUTATOR_HOOKFUNCTION(oknex_charge, GetPressedKeys)
{
	entity player = M_ARGV(0, entity);

	             
	if(!WEP_CVAR(oknex, charge) || !WEP_CVAR(oknex, charge_velocity_rate))
		return;

	for(int slot = 0; slot < MAX_WEAPONSLOTS; ++slot)
	{
		.entity weaponentity = weaponentities[slot];

		if (player.(weaponentity).m_weapon == WEP_OVERKILL_NEX && WEP_CVAR(oknex, charge) && WEP_CVAR(oknex, charge_velocity_rate) && vdist(vec2(player.velocity), >, WEP_CVAR(oknex, charge_minspeed)))
		{
			float xyspeed = vlen(vec2(player.velocity));
			                                                                                                                        
				xyspeed = min(xyspeed, WEP_CVAR(oknex, charge_maxspeed));
			float f = (xyspeed - WEP_CVAR(oknex, charge_minspeed)) / (WEP_CVAR(oknex, charge_maxspeed) - WEP_CVAR(oknex, charge_minspeed));
			                       
			player.(weaponentity).oknex_charge = min(1, player.(weaponentity).oknex_charge + WEP_CVAR(oknex, charge_velocity_rate) * f * PHYS_INPUT_TIMELENGTH);
		}
	}
}

void W_OverkillNex_Attack(Weapon thiswep, entity actor, .entity weaponentity, float issecondary)
{
	float mydmg, myforce, mymindist, mymaxdist, myhalflife, myforcehalflife, myammo, charge;

	mydmg = WEP_CVAR_BOTH(oknex, !issecondary, damage);
	myforce = WEP_CVAR_BOTH(oknex, !issecondary, force);
	mymindist = WEP_CVAR_BOTH(oknex, !issecondary, damagefalloff_mindist);
	mymaxdist = WEP_CVAR_BOTH(oknex, !issecondary, damagefalloff_maxdist);
	myhalflife = WEP_CVAR_BOTH(oknex, !issecondary, damagefalloff_halflife);
	myforcehalflife = WEP_CVAR_BOTH(oknex, !issecondary, damagefalloff_forcehalflife);
	myammo = WEP_CVAR_BOTH(oknex, !issecondary, ammo);

	float flying;
	flying = IsFlying(actor);                                                                       

	if (WEP_CVAR(oknex, charge))
	{
		charge = WEP_CVAR(oknex, charge_mindmg) / mydmg + (1 - WEP_CVAR(oknex, charge_mindmg) / mydmg) * actor.(weaponentity).oknex_charge;
		actor.(weaponentity).oknex_charge *= WEP_CVAR(oknex, charge_shot_multiplier);                                       
		                      
		                     
	}
	else
	{
		charge = 1;
	}
	mydmg *= charge;
	myforce *= charge;

	W_SetupShot(actor, weaponentity, true, 5, SND_NEXFIRE, CH_WEAPON_A, mydmg, thiswep.m_id);
	if(charge > WEP_CVAR(oknex, charge_animlimit) && WEP_CVAR(oknex, charge_animlimit))                                                             
	{
		sound(actor, CH_WEAPON_B, SND_NEXCHARGE, VOL_BASE * (charge - 0.5 * WEP_CVAR(oknex, charge_animlimit)) / (1 - 0.5 * WEP_CVAR(oknex, charge_animlimit)), ATTN_NORM);
	}

	yoda = 0;
	impressive_hits = 0;
	FireRailgunBullet(actor, weaponentity, w_shotorg, w_shotorg + w_shotdir * max_shot_distance, mydmg, true, myforce, mymindist, mymaxdist, myhalflife, myforcehalflife, thiswep.m_id);

	if(yoda && flying)
		Send_Notification(NOTIF_ONE, actor, MSG_ANNCE, ANNCE_ACHIEVEMENT_YODA);
	if(impressive_hits && actor.oknex_lasthit)
	{
		Send_Notification(NOTIF_ONE, actor, MSG_ANNCE, ANNCE_ACHIEVEMENT_IMPRESSIVE);
		impressive_hits = 0;                          
	}

	actor.oknex_lasthit = impressive_hits;

	                                      
	SendCSQCVortexBeamParticle(charge);

	W_DecreaseAmmo(thiswep, actor, myammo, weaponentity);
}

.float oknex_chargepool_pauseregen_finished;

METHOD(OverkillNex, wr_aim, void(entity thiswep, entity actor, .entity weaponentity))
{
	if(bot_aim(actor, weaponentity, 1000000, 0, 1, false, true))
		PHYS_INPUT_BUTTON_ATCK(actor) = true;
	else
	{
		if(WEP_CVAR(oknex, charge))
			PHYS_INPUT_BUTTON_ATCK2(actor) = true;
	}
}

METHOD(OverkillNex, wr_think, void(entity thiswep, entity actor, .entity weaponentity, int fire))
{
	if (WEP_CVAR(oknex, charge) && actor.(weaponentity).oknex_charge < WEP_CVAR(oknex, charge_limit))
	{
		actor.(weaponentity).oknex_charge = min(1, actor.(weaponentity).oknex_charge + WEP_CVAR(oknex, charge_rate) * frametime / W_TICSPERFRAME);
	}

	if (WEP_CVAR_SEC(oknex, chargepool))
		if (actor.(weaponentity).oknex_chargepool_ammo < 1)
		{
			if (actor.oknex_chargepool_pauseregen_finished < time)
				actor.(weaponentity).oknex_chargepool_ammo = min(1, actor.(weaponentity).oknex_chargepool_ammo + WEP_CVAR_SEC(oknex, chargepool_regen) * frametime / W_TICSPERFRAME);
			actor.pauseregen_finished = max(actor.pauseregen_finished, time + WEP_CVAR_SEC(oknex, chargepool_pause_regen));
		}

	if ((WEP_CVAR_SEC(oknex, refire_type) == 1) && (fire & 2) && (time >= actor.jump_interval))
	{
		                                                            
		actor.jump_interval = time + WEP_CVAR_SEC(oknex, refire) * W_WeaponRateFactor(actor);
		makevectors(actor.v_angle);
		W_Blaster_Attack(actor, weaponentity, WEP_BLASTER.m_id | HITTYPE_SECONDARY);
		if ((actor.(weaponentity).wframe == WFRAME_IDLE) ||
			(actor.(weaponentity).wframe == WFRAME_FIRE2))
		{
			                                
			actor.(weaponentity).wframe = WFRAME_FIRE2;
			FOREACH_CLIENT(true, LAMBDA(
				if (it == actor || (IS_SPEC(it) && it.enemy == actor))
				{
					wframe_send(it, actor.(weaponentity), WFRAME_FIRE2, autocvar_g_weaponratefactor, true);
				}
			));
			animdecide_setaction(actor, ANIMACTION_SHOOT, true);
		}
	}

	if (autocvar_g_balance_oknex_reload_ammo && actor.(weaponentity).clip_load < WEP_CVAR_PRI(oknex, ammo))
	{
		                
		thiswep.wr_reload(thiswep, actor, weaponentity);
		return;
	}
	if (fire & 1)                  
	{
		if (!weapon_prepareattack(thiswep, actor, weaponentity, false, WEP_CVAR_PRI(oknex, refire)))
		{
			return;
		}
		W_OverkillNex_Attack(thiswep, actor, weaponentity, 0);
		weapon_thinkf(actor, weaponentity, WFRAME_FIRE1, WEP_CVAR_PRI(oknex, animtime), w_ready);
		return;
	}
	if ((fire & 2) && (WEP_CVAR(oknex, secondary) == 2) && (WEP_CVAR_SEC(oknex, refire_type) == 0))
	{
		                   
		if (!weapon_prepareattack(thiswep, actor, weaponentity, true, WEP_CVAR_SEC(oknex, refire)))
		{
			return;
		}
		makevectors(actor.v_angle);
		W_Blaster_Attack(actor, weaponentity, WEP_BLASTER.m_id | HITTYPE_SECONDARY);
		weapon_thinkf(actor, weaponentity, WFRAME_FIRE2, WEP_CVAR_SEC(oknex, animtime), w_ready);
		return;
	}
	                                                                                                                                                          
	   
	                              
	    
	                                                                                         
	                                          
	  
	                                             
	     
	                                        
	      
	                                   
	       
	                                             
	                                                                                                                                        

	                                                                                            
	                                                                                                       
	                                                                
	                       

	                                                                              
	       
	      

	                                       
	      
	                                                              
	       
	                                                                                            
	                                             
	        
	                                                                                           
	                                                 
	         
	                                                                                                                
	                         
	                   
	          
	                                                                                                                                           
	          
	                                                                                                    
	         
	            
	         
	                                                                                                            
	                         
	                   
	          
	                                                                                                                                   
	          
	         
	        
	                                                                              
	       
	      

	         
	      
	                                                                                           
	                                                                             
	      
	     
	    
	                                      
	    
	                                                                                              
	     
	                                                           
	                                                                                              
	     
	    
	   
}

METHOD(OverkillNex, wr_setup, void(entity thiswep, entity actor, .entity weaponentity))
{
	actor.oknex_lasthit = 0;
}

METHOD(OverkillNex, wr_checkammo1, bool(entity thiswep, entity actor, .entity weaponentity))
{
	float ammo_amount = GetResource(actor, thiswep.ammo_type) >= WEP_CVAR_PRI(oknex, ammo);
	ammo_amount += (autocvar_g_balance_oknex_reload_ammo && actor.(weaponentity).(weapon_load[thiswep.m_id]) >= WEP_CVAR_PRI(oknex, ammo));
	return ammo_amount;
}

METHOD(OverkillNex, wr_checkammo2, bool(entity thiswep, entity actor, .entity weaponentity))
{
	if (WEP_CVAR(oknex, secondary))
	{
		                                                    
		float ammo_amount = GetResource(actor, thiswep.ammo_type) >= WEP_CVAR_SEC(oknex, ammo);
		ammo_amount += actor.(weaponentity).(weapon_load[thiswep.m_id]) >= WEP_CVAR_SEC(oknex, ammo);
		return ammo_amount;
	}
	else
	{
		return false;                           
	}
}

METHOD(OverkillNex, wr_resetplayer, void(entity thiswep, entity actor))
{
	if (WEP_CVAR(oknex, charge)) {
		for(int slot = 0; slot < MAX_WEAPONSLOTS; ++slot)
		{
			.entity weaponentity = weaponentities[slot];
			actor.(weaponentity).oknex_charge = WEP_CVAR(oknex, charge_start);
		}
	}
	actor.oknex_lasthit = 0;
}

METHOD(OverkillNex, wr_reload, void(entity thiswep, entity actor, .entity weaponentity))
{
	W_Reload(actor, weaponentity, WEP_CVAR_PRI(oknex, ammo), SND_RELOAD);
}

METHOD(OverkillNex, wr_suicidemessage, Notification(entity thiswep))
{
	return WEAPON_THINKING_WITH_PORTALS;
}

METHOD(OverkillNex, wr_killmessage, Notification(entity thiswep))
{
	return WEAPON_OVERKILL_NEX_MURDER;
}

METHOD(OverkillNex, wr_zoom, bool(entity thiswep, entity actor))
{
	return PHYS_INPUT_BUTTON_ATCK2(actor) && !WEP_CVAR(oknex, secondary);
}

#endif
#ifdef CSQC

METHOD(OverkillNex, wr_impacteffect, void(entity thiswep, entity actor))
{
	entity this = actor;
	vector org2 = w_org + w_backoff * 2;
	pointparticles(EFFECT_VORTEX_IMPACT, org2, '0 0 0', 1);
	if(!w_issilent)
		sound(this, CH_SHOTS, SND_NEXIMPACT, VOL_BASE, ATTN_NORM);
}

METHOD(OverkillNex, wr_init, void(entity thiswep))
{
	if(autocvar_cl_reticle && autocvar_cl_reticle_weapon)
	{
		precache_pic("gfx/reticle_nex");
	}
}

METHOD(OverkillNex, wr_zoom, bool(entity thiswep, entity actor))
{
	if(button_zoom || zoomscript_caught || (!WEP_CVAR(oknex, secondary) && button_attack2))
	{
		return true;
	}
	else
	{
		                                           
		return false;
	}
}

METHOD(OverkillNex, wr_zoomdir, bool(entity thiswep))
{
    return button_attack2 && !WEP_CVAR(oknex, secondary);
}

#endif
