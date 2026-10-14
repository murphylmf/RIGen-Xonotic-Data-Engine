#include "shotgun.qh"

#ifdef SVQC

                              
                            

void W_Shotgun_Attack(Weapon thiswep, entity actor, .entity weaponentity, float isprimary, float ammocount, float damage, float bullets, float spread, float solidpenetration, float force, entity bullet_trail_effect)
{
	W_DecreaseAmmo(thiswep, actor, ammocount, weaponentity);

	W_SetupShot(actor, weaponentity, true, 5, SND_SHOTGUN_FIRE, ((isprimary) ? CH_WEAPON_A : CH_WEAPON_SINGLE), damage * bullets, thiswep.m_id);

	                                                                                                                             
	float lag = antilag_getlag(actor);
	if(lag && bullets > 0)
		antilag_takeback_all(actor, lag);

	for(int sc = 0;sc < bullets;sc = sc + 1)
		fireBullet_antilag(actor, weaponentity, w_shotorg, w_shotdir, spread, solidpenetration, damage, 0, force, thiswep.m_id, bullet_trail_effect, false);

	if(lag && bullets > 0)
		antilag_restore_all(actor);

	W_MuzzleFlash(thiswep, actor, weaponentity, w_shotorg, w_shotdir);

	              
	if(autocvar_g_casings >= 1)
	{
		makevectors(actor.v_angle);                                 
		                                                              
			SpawnCasing(((random() * 50 + 50) * v_right) - (v_forward * (random() * 25 + 25)) - ((random() * 5 - 30) * v_up), vectoangles(v_forward), 1, actor, weaponentity);
	}
}

.float swing_prev;
.entity swing_alreadyhit;
void W_Shotgun_Melee_Think(entity this)
{
	               
	float i, f, swing, swing_factor, swing_damage, meleetime, is_player;
	entity target_victim;
	vector targpos;

	if(!this.cnt)                           
	{
		this.cnt = time;
		W_PlayStrengthSound(this.realowner);
	}

	makevectors(this.realowner.v_angle);                                 

	                                           
	meleetime = WEP_CVAR_SEC(shotgun, melee_time) * W_WeaponRateFactor(this.realowner);
	swing = bound(0, (this.cnt + meleetime - time) / meleetime, 10);
	f = ((1 - swing) * WEP_CVAR_SEC(shotgun, melee_traces));

	                                                               
	if(IS_DEAD(this.realowner) && WEP_CVAR_SEC(shotgun, melee_no_doubleslap))
	{
		delete(this);
		return;
	}

	                                                    
	for(i=this.swing_prev; i < f; ++i)
	{
		swing_factor = ((1 - (i / WEP_CVAR_SEC(shotgun, melee_traces))) * 2 - 1);

		targpos = (this.realowner.origin + this.realowner.view_ofs
			+ (v_forward * WEP_CVAR_SEC(shotgun, melee_range))
			+ (v_up * swing_factor * WEP_CVAR_SEC(shotgun, melee_swing_up))
			+ (v_right * swing_factor * WEP_CVAR_SEC(shotgun, melee_swing_side)));

		WarpZone_traceline_antilag(this.realowner, this.realowner.origin + this.realowner.view_ofs, targpos, false, this.realowner, ((IS_CLIENT(this.realowner)) ? ANTILAG_LATENCY(this.realowner) : 0));

		                                     
	#ifdef SHOTGUN_MELEEDEBUG
		te_lightning2(NULL, targpos, this.realowner.origin + this.realowner.view_ofs + v_forward * 5 - v_up * 5);
		te_customflash(targpos, 40,  2, '1 1 1');
	#endif

		is_player = (IS_PLAYER(trace_ent) || trace_ent.classname == "body" || IS_MONSTER(trace_ent));

		if((trace_fraction < 1)                                                      
			&& (trace_ent.takedamage != DAMAGE_NO)
			&& (trace_ent != this.swing_alreadyhit)
			&& (is_player || WEP_CVAR_SEC(shotgun, melee_nonplayerdamage)))
		{
			target_victim = trace_ent;                                      

			if(is_player)                                                                                              
				swing_damage = (WEP_CVAR_SEC(shotgun, damage) * min(1, swing_factor + 1));
			else
				swing_damage = (WEP_CVAR_SEC(shotgun, melee_nonplayerdamage) * min(1, swing_factor + 1));

			                                                                                                                                                                                               

			Damage(target_victim, this.realowner, this.realowner,
				swing_damage, WEP_SHOTGUN.m_id | HITTYPE_SECONDARY, this.weaponentity_fld,
				this.realowner.origin + this.realowner.view_ofs,
				v_forward * WEP_CVAR_SEC(shotgun, force));

			if(accuracy_isgooddamage(this.realowner, target_victim)) { accuracy_add(this.realowner, WEP_SHOTGUN, 0, swing_damage); }

			                                     
		#ifdef SHOTGUN_MELEEDEBUG
			te_customflash(targpos, 200, 2, '15 0 0');
		#endif

			if(WEP_CVAR_SEC(shotgun, melee_multihit))                                                                              
			{
				this.swing_alreadyhit = target_victim;
				continue;                            
			}
			else
			{
				delete(this);
				return;
			}
		}
	}

	if(time >= this.cnt + meleetime)
	{
		                    
		delete(this);
		return;
	}
	else
	{
		                    
		this.swing_prev = i;
		this.nextthink = time;
	}
}

void W_Shotgun_Attack2(Weapon thiswep, entity actor, .entity weaponentity, int fire)
{
	sound(actor, CH_WEAPON_A, SND_SHOTGUN_MELEE, VOL_BASE, ATTEN_NORM);
	weapon_thinkf(actor, weaponentity, WFRAME_FIRE2, WEP_CVAR_SEC(shotgun, animtime), w_ready);

	entity meleetemp = new_pure(meleetemp);
	meleetemp.realowner = actor;
	setthink(meleetemp, W_Shotgun_Melee_Think);
	meleetemp.nextthink = time + WEP_CVAR_SEC(shotgun, melee_delay) * W_WeaponRateFactor(actor);
	meleetemp.weaponentity_fld = weaponentity;
	W_SetupShot_Range(actor, weaponentity, true, 0, SND_Null, 0, WEP_CVAR_SEC(shotgun, damage), WEP_CVAR_SEC(shotgun, melee_range), WEP_SHOTGUN.m_id | HITTYPE_SECONDARY);
}

                                    
void W_Shotgun_Attack3_Frame2(Weapon thiswep, entity actor, .entity weaponentity, int fire)
{
	if (!thiswep.wr_checkammo2(thiswep, actor, weaponentity))
	if (!(actor.items & IT_UNLIMITED_AMMO))
	{
		W_SwitchWeapon_Force(actor, w_getbestweapon(actor, weaponentity), weaponentity);
		w_ready(thiswep, actor, weaponentity, fire);
		return;
	}

	sound(actor, CH_WEAPON_SINGLE, SND_Null, VOL_BASE, ATTN_NORM);                       
	W_Shotgun_Attack(thiswep, actor, weaponentity, true,
		WEP_CVAR_PRI(shotgun, ammo),
		WEP_CVAR_PRI(shotgun, damage),
		WEP_CVAR_PRI(shotgun, bullets),
		WEP_CVAR_PRI(shotgun, spread),
		WEP_CVAR_PRI(shotgun, solidpenetration),
		WEP_CVAR_PRI(shotgun, force),
		EFFECT_BULLET_WEAK);                                                                                    
	weapon_thinkf(actor, weaponentity, WFRAME_FIRE1, WEP_CVAR_SEC(shotgun, alt_animtime), w_ready);
}
void W_Shotgun_Attack3_Frame1(Weapon thiswep, entity actor, .entity weaponentity, int fire)
{
	if (!thiswep.wr_checkammo2(thiswep, actor, weaponentity))
	if (!(actor.items & IT_UNLIMITED_AMMO))
	{
		W_SwitchWeapon_Force(actor, w_getbestweapon(actor, weaponentity), weaponentity);
		w_ready(thiswep, actor, weaponentity, fire);
		return;
	}

	W_Shotgun_Attack(thiswep, actor, weaponentity, false,
		WEP_CVAR_PRI(shotgun, ammo),
		WEP_CVAR_PRI(shotgun, damage),
		WEP_CVAR_PRI(shotgun, bullets),
		WEP_CVAR_PRI(shotgun, spread),
		WEP_CVAR_PRI(shotgun, solidpenetration),
		WEP_CVAR_PRI(shotgun, force),
		EFFECT_BULLET_WEAK);
	weapon_thinkf(actor, weaponentity, WFRAME_FIRE1, WEP_CVAR_SEC(shotgun, alt_animtime), W_Shotgun_Attack3_Frame2);
}

.float shotgun_primarytime;

METHOD(Shotgun, wr_aim, void(entity thiswep, entity actor, .entity weaponentity))
{
    if(vdist(actor.origin - actor.enemy.origin, <=, WEP_CVAR_SEC(shotgun, melee_range)))
        PHYS_INPUT_BUTTON_ATCK2(actor) = bot_aim(actor, weaponentity, 1000000, 0, 0.001, false, false);
    else
        PHYS_INPUT_BUTTON_ATCK(actor) = bot_aim(actor, weaponentity, 1000000, 0, 0.001, false, false);
}

METHOD(Shotgun, wr_think, void(entity thiswep, entity actor, .entity weaponentity, int fire))
{
                                                            
    if(WEP_CVAR(shotgun, reload_ammo) && actor.(weaponentity).clip_load < WEP_CVAR_PRI(shotgun, ammo))
    {
        if(actor.(weaponentity).clip_load >= 0 && GetResource(actor, thiswep.ammo_type) > 0)
        {
            thiswep.wr_reload(thiswep, actor, weaponentity);
            return;
        }
    }

    if(actor.(weaponentity).clip_load >= 0)                                  
    {
        if(fire & 1)
        {
            if(time >= actor.(weaponentity).shotgun_primarytime)                                                                                   
            {
                if(weapon_prepareattack(thiswep, actor, weaponentity, false, WEP_CVAR_PRI(shotgun, animtime)))
                {
                    W_Shotgun_Attack(thiswep, actor, weaponentity, true,
						WEP_CVAR_PRI(shotgun, ammo),
						WEP_CVAR_PRI(shotgun, damage),
						WEP_CVAR_PRI(shotgun, bullets),
						WEP_CVAR_PRI(shotgun, spread),
						WEP_CVAR_PRI(shotgun, solidpenetration),
						WEP_CVAR_PRI(shotgun, force),
						EFFECT_BULLET_WEAK);
                    actor.(weaponentity).shotgun_primarytime = time + WEP_CVAR_PRI(shotgun, refire) * W_WeaponRateFactor(actor);
                    weapon_thinkf(actor, weaponentity, WFRAME_FIRE1, WEP_CVAR_PRI(shotgun, animtime), w_ready);
                    return;
                }
            }
        }
        else if((fire & 2) && WEP_CVAR(shotgun, secondary) == 2)
        {
            if(time >= actor.(weaponentity).shotgun_primarytime)                                                                                   
            {
                if(weapon_prepareattack(thiswep, actor, weaponentity, false, WEP_CVAR_SEC(shotgun, alt_animtime)))
                {
                    W_Shotgun_Attack(thiswep, actor, weaponentity, false,
						WEP_CVAR_PRI(shotgun, ammo),
						WEP_CVAR_PRI(shotgun, damage),
						WEP_CVAR_PRI(shotgun, bullets),
						WEP_CVAR_PRI(shotgun, spread),
						WEP_CVAR_PRI(shotgun, solidpenetration),
						WEP_CVAR_PRI(shotgun, force),
						EFFECT_BULLET_WEAK);
                    actor.(weaponentity).shotgun_primarytime = time + WEP_CVAR_SEC(shotgun, alt_refire) * W_WeaponRateFactor(actor);
                    weapon_thinkf(actor, weaponentity, WFRAME_FIRE1, WEP_CVAR_SEC(shotgun, alt_animtime), W_Shotgun_Attack3_Frame1);
                    return;
                }
            }
        }
    }

    if(actor.(weaponentity).clip_load >= 0)                                  
    if(WEP_CVAR(shotgun, secondary) == 1)
    if(((fire & 1) && !IS_BOT_CLIENT(actor) && GetResource(actor, thiswep.ammo_type) <= 0 && actor.(weaponentity).clip_load == 0 && !(actor.items & IT_UNLIMITED_AMMO)) || (fire & 2))
    if(weapon_prepareattack(thiswep, actor, weaponentity, true, WEP_CVAR_SEC(shotgun, refire)))
    {
                       
                                                                                                         
        weapon_thinkf(actor, weaponentity, WFRAME_FIRE1, 0, W_Shotgun_Attack2);
    }
}
METHOD(Shotgun, wr_checkammo1, bool(entity thiswep, entity actor, .entity weaponentity))
{
    float ammo_amount = GetResource(actor, thiswep.ammo_type) >= WEP_CVAR_PRI(shotgun, ammo);
    ammo_amount += actor.(weaponentity).(weapon_load[thiswep.m_id]) >= WEP_CVAR_PRI(shotgun, ammo);
    return ammo_amount;
}
METHOD(Shotgun, wr_checkammo2, bool(entity thiswep, entity actor, .entity weaponentity))
{
    switch(WEP_CVAR(shotgun, secondary))
    {
        case 1: return true;                           
        case 2:                         
        {
            float ammo_amount = GetResource(actor, thiswep.ammo_type) >= WEP_CVAR_PRI(shotgun, ammo);
            ammo_amount += actor.(weaponentity).(weapon_load[thiswep.m_id]) >= WEP_CVAR_PRI(shotgun, ammo);
            return ammo_amount;
        }
        default: return false;                         
    }
}
METHOD(Shotgun, wr_reload, void(entity thiswep, entity actor, .entity weaponentity))
{
    W_Reload(actor, weaponentity, WEP_CVAR_PRI(shotgun, ammo), SND_RELOAD);              
}
METHOD(Shotgun, wr_suicidemessage, Notification(entity thiswep))
{
    return WEAPON_THINKING_WITH_PORTALS;
}
METHOD(Shotgun, wr_killmessage, Notification(entity thiswep))
{
    if(w_deathtype & HITTYPE_SECONDARY)
        return WEAPON_SHOTGUN_MURDER_SLAP;
    else
        return WEAPON_SHOTGUN_MURDER;
}

#endif
#ifdef CSQC
.float prevric;

METHOD(Shotgun, wr_impacteffect, void(entity thiswep, entity actor))
{
    vector org2 = w_org + w_backoff * 2;
    pointparticles(EFFECT_SHOTGUN_IMPACT, org2, w_backoff * 1000, 1);
    if(!w_issilent && time - actor.prevric > 0.25)
    {
        if(w_random < 0.05)
            sound(actor, CH_SHOTS, SND_RIC_RANDOM(), VOL_BASE, ATTEN_NORM);
        actor.prevric = time;
    }
}

#endif
