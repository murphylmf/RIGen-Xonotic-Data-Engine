#include "minelayer.qh"

#ifdef SVQC

void W_MineLayer_Stick(entity this, entity to)
{
	spamsound(this, CH_SHOTS, SND_MINE_STICK, VOL_BASE, ATTN_NORM);

	                                                                                                                                   

	entity newmine = spawn();
	IL_PUSH(g_mines, newmine);
	newmine.weaponentity_fld = this.weaponentity_fld;
	newmine.classname = this.classname;

	newmine.bot_dodge = this.bot_dodge;
	newmine.bot_dodgerating = this.bot_dodgerating;

	newmine.owner = this.owner;
	newmine.realowner = this.realowner;
	setorigin(newmine, this.origin);
	setmodel(newmine, MDL_MINELAYER_MINE);
	setsize(newmine, '-4 -4 -4', '4 4 4');
	newmine.angles = vectoangles(-trace_plane_normal);                            

	newmine.movedir = -trace_plane_normal;

	newmine.takedamage = this.takedamage;
	newmine.damageforcescale = this.damageforcescale;
	SetResourceExplicit(newmine, RES_HEALTH, GetResource(this, RES_HEALTH));
	newmine.event_damage = this.event_damage;
	newmine.spawnshieldtime = this.spawnshieldtime;
	newmine.damagedbycontents = true;
	IL_PUSH(g_damagedbycontents, newmine);

	set_movetype(newmine, MOVETYPE_NONE);                          
	newmine.projectiledeathtype = this.projectiledeathtype;

	newmine.mine_time = this.mine_time;

	settouch(newmine, func_null);
	setthink(newmine, W_MineLayer_Think);
	newmine.nextthink = time;
	newmine.cnt = this.cnt;
	newmine.flags = this.flags;
	IL_PUSH(g_projectiles, newmine);
	IL_PUSH(g_bot_dodge, newmine);

	delete(this);

	if(to)
		SetMovetypeFollow(newmine, to);
}

void W_MineLayer_Explode(entity this, entity directhitentity)
{
	if(directhitentity.takedamage == DAMAGE_AIM)
		if(IS_PLAYER(directhitentity))
			if(DIFF_TEAM(this.realowner, directhitentity))
				if(!IS_DEAD(directhitentity))
					if(IsFlying(directhitentity))
						Send_Notification(NOTIF_ONE, this.realowner, MSG_ANNCE, ANNCE_ACHIEVEMENT_AIRSHOT);

	this.event_damage = func_null;
	this.takedamage = DAMAGE_NO;

	RadiusDamage(this, this.realowner, WEP_CVAR(minelayer, damage), WEP_CVAR(minelayer, edgedamage), WEP_CVAR(minelayer, radius), NULL, NULL, WEP_CVAR(minelayer, force), this.projectiledeathtype, this.weaponentity_fld, directhitentity);

	.entity weaponentity = this.weaponentity_fld;
	Weapon thiswep = WEP_MINE_LAYER;
	if(this.realowner.(weaponentity).m_weapon == thiswep)
	{
		entity own = this.realowner;
		if(!thiswep.wr_checkammo1(thiswep, own, weaponentity))
		{
			own.cnt = thiswep.m_id;
			ATTACK_FINISHED(own, weaponentity) = time;
			own.(weaponentity).m_switchweapon = w_getbestweapon(own, weaponentity);
		}
	}
	delete(this);
}

void W_MineLayer_Explode_think(entity this)
{
	W_MineLayer_Explode(this, NULL);
}

void W_MineLayer_DoRemoteExplode(entity this)
{
	this.event_damage = func_null;
	this.takedamage = DAMAGE_NO;

	if(this.move_movetype == MOVETYPE_NONE || this.move_movetype == MOVETYPE_FOLLOW)
		this.velocity = this.movedir;                                                                  

	RadiusDamage(this, this.realowner, WEP_CVAR(minelayer, remote_damage), WEP_CVAR(minelayer, remote_edgedamage), WEP_CVAR(minelayer, remote_radius),
						NULL, NULL, WEP_CVAR(minelayer, remote_force), this.projectiledeathtype | HITTYPE_BOUNCE, this.weaponentity_fld, NULL);

	.entity weaponentity = this.weaponentity_fld;
	Weapon thiswep = WEP_MINE_LAYER;
	if(this.realowner.(weaponentity).m_weapon == thiswep)
	{
		entity own = this.realowner;
		if(!thiswep.wr_checkammo1(thiswep, own, weaponentity))
		{
			own.cnt = thiswep.m_id;
			ATTACK_FINISHED(own, weaponentity) = time;
			own.(weaponentity).m_switchweapon = w_getbestweapon(own, weaponentity);
		}
	}
	delete(this);
}

void W_MineLayer_RemoteExplode(entity this)
{
	if(!IS_DEAD(this.realowner))
		if((this.spawnshieldtime >= 0)
			? (time >= this.spawnshieldtime)         
			: (vdist(NearestPointOnBox(this.realowner, this.origin) - this.origin, >, WEP_CVAR(minelayer, remote_radius)))                 
		)
		{
			W_MineLayer_DoRemoteExplode(this);
		}
}

void W_MineLayer_ProximityExplode(entity this)
{
	                                                                                                                      
	if(WEP_CVAR(minelayer, protection) && this.mine_explodeanyway == 0)
	{
		entity head;
		head = findradius(this.origin, WEP_CVAR(minelayer, radius));
		while(head)
		{
			if(head == this.realowner || SAME_TEAM(head, this.realowner))
				return;
			head = head.chain;
		}
	}

	this.mine_time = 0;
	W_MineLayer_Explode(this, NULL);
}

int W_MineLayer_Count(entity e, .entity weaponentity)
{
	int minecount = 0;
	IL_EACH(g_mines, it.realowner == e && it.weaponentity_fld == weaponentity,
	{
		minecount += 1;
	});

	return minecount;
}

void W_MineLayer_Think(entity this)
{
	entity head;

	this.nextthink = time;

	if(this.move_movetype == MOVETYPE_FOLLOW)
	{
		if(LostMovetypeFollow(this))
		{
			UnsetMovetypeFollow(this);
			set_movetype(this, MOVETYPE_NONE);
		}
	}

	                                                                                                 
	                                                                  
	if((time > this.cnt) && (!this.mine_time) && (this.cnt > 0))
	{
		if(WEP_CVAR(minelayer, lifetime_countdown) > 0)
			spamsound(this, CH_SHOTS, SND_MINE_TRIGGER, VOL_BASE, ATTN_NORM);
		this.mine_time = time + WEP_CVAR(minelayer, lifetime_countdown);
		this.mine_explodeanyway = 1;                                                                                              
	}

	                                                           
	                                                                                                
	if(!IS_PLAYER(this.realowner) || IS_DEAD(this.realowner) || STAT(FROZEN, this.realowner))
	{
		this.projectiledeathtype |= HITTYPE_BOUNCE;
		W_MineLayer_Explode(this, NULL);
		return;
	}

	                                                           
	head = findradius(this.origin, WEP_CVAR(minelayer, proximityradius));
	while(head)
	{
		if(IS_PLAYER(head) && !IS_DEAD(head) && !STAT(FROZEN, head) && !IS_INDEPENDENT_PLAYER(head))
		if(head != this.realowner && DIFF_TEAM(head, this.realowner))                                
		if(!this.mine_time)
		{
			spamsound(this, CH_SHOTS, SND_MINE_TRIGGER, VOL_BASE, ATTN_NORM);
			this.mine_time = time + WEP_CVAR(minelayer, time);
		}
		head = head.chain;
	}

	                          
	if(this.mine_time && time >= this.mine_time)
	{
		W_MineLayer_ProximityExplode(this);
		return;
	}

	                    
	.entity weaponentity = this.weaponentity_fld;
	if(this.realowner.(weaponentity).m_weapon == WEP_MINE_LAYER)
	if(!IS_DEAD(this.realowner))
	if(this.minelayer_detonate)
		W_MineLayer_RemoteExplode(this);
}

void W_MineLayer_Touch(entity this, entity toucher)
{
	if(this.move_movetype == MOVETYPE_NONE || this.move_movetype == MOVETYPE_FOLLOW)
		return;                                                                                 

	PROJECTILE_TOUCH(this, toucher);

	if((toucher && IS_PLAYER(toucher) && !IS_DEAD(toucher)) || toucher.owner == this.owner)
	{
		                             
		              
	}
	else
	{
		W_MineLayer_Stick(this, toucher);
	}
}

void W_MineLayer_Damage(entity this, entity inflictor, entity attacker, float damage, int deathtype, .entity weaponentity, vector hitloc, vector force)
{
	if(GetResource(this, RES_HEALTH) <= 0)
		return;

	float is_from_enemy = (inflictor.realowner != this.realowner);

	if(!W_CheckProjectileDamage(inflictor.realowner, this.realowner, deathtype, (is_from_enemy ? 1 : -1)))
		return;                                     

	TakeResource(this, RES_HEALTH, damage);
	this.angles = vectoangles(this.velocity);

	if(GetResource(this, RES_HEALTH) <= 0)
		W_PrepareExplosionByDamage(this, attacker, W_MineLayer_Explode_think);
}

void W_MineLayer_Attack(Weapon thiswep, entity actor, .entity weaponentity)
{
	                                                                    
	if(WEP_CVAR(minelayer, limit))
	{
		int minecount = W_MineLayer_Count(actor, weaponentity);
		if(minecount >= WEP_CVAR(minelayer, limit))
		{
			                                                         
			Send_Notification(NOTIF_ONE, actor, MSG_MULTI, WEAPON_MINELAYER_LIMIT, WEP_CVAR(minelayer, limit));
			play2(actor, SND(UNAVAILABLE));
			return;
		}
	}

	W_DecreaseAmmo(thiswep, actor, WEP_CVAR(minelayer, ammo), weaponentity);

	W_SetupShot_ProjectileSize(actor, weaponentity, '-4 -4 -4', '4 4 4', false, 5, SND_MINE_FIRE, CH_WEAPON_A, WEP_CVAR(minelayer, damage), thiswep.m_id);
	W_MuzzleFlash(thiswep, actor, weaponentity, w_shotorg, w_shotdir);

	entity mine = WarpZone_RefSys_SpawnSameRefSys(actor);
	mine.weaponentity_fld = weaponentity;
	IL_PUSH(g_mines, mine);
	mine.owner = mine.realowner = actor;
	if(WEP_CVAR(minelayer, detonatedelay) >= 0)
		mine.spawnshieldtime = time + WEP_CVAR(minelayer, detonatedelay);
	else
		mine.spawnshieldtime = -1;
	mine.classname = "mine";
	mine.bot_dodge = true;
	mine.bot_dodgerating = WEP_CVAR(minelayer, damage) * 2;                                                                           

	mine.takedamage = DAMAGE_YES;
	mine.damageforcescale = WEP_CVAR(minelayer, damageforcescale);
	SetResourceExplicit(mine, RES_HEALTH, WEP_CVAR(minelayer, health));
	mine.event_damage = W_MineLayer_Damage;
	mine.damagedbycontents = true;
	IL_PUSH(g_damagedbycontents, mine);

	set_movetype(mine, MOVETYPE_TOSS);
	PROJECTILE_MAKETRIGGER(mine);
	mine.projectiledeathtype = thiswep.m_id;
	mine.weaponentity_fld = weaponentity;
	setsize(mine, '-4 -4 -4', '4 4 4');                                       

	setorigin(mine, w_shotorg - v_forward * 4);                                                       
	W_SetupProjVelocity_Basic(mine, WEP_CVAR(minelayer, speed), 0);
	mine.angles = vectoangles(mine.velocity);

	settouch(mine, W_MineLayer_Touch);
	setthink(mine, W_MineLayer_Think);
	mine.nextthink = time;
	mine.cnt = (WEP_CVAR(minelayer, lifetime) - WEP_CVAR(minelayer, lifetime_countdown));
	mine.flags = FL_PROJECTILE;
	IL_PUSH(g_projectiles, mine);
	IL_PUSH(g_bot_dodge, mine);
	mine.missile_flags = MIF_SPLASH | MIF_ARC | MIF_PROXY;

	if(mine.cnt > 0) { mine.cnt += time; }

	CSQCProjectile(mine, true, PROJECTILE_MINE, true);

	                    

	MUTATOR_CALLHOOK(EditProjectile, actor, mine);
}

bool W_MineLayer_PlacedMines(entity this, .entity weaponentity, bool detonate)
{
	bool minfound = false;

	IL_EACH(g_mines, it.realowner == this && it.weaponentity_fld == weaponentity,
	{
		if(detonate)
		{
			if(!it.minelayer_detonate)
			{
				it.minelayer_detonate = true;
				minfound = true;
			}
		}
		else
			minfound = true;
	});
	return minfound;
}

METHOD(MineLayer, wr_aim, void(entity thiswep, entity actor, .entity weaponentity))
{
                                            
    int minecount = W_MineLayer_Count(actor, weaponentity);
    if(minecount >= WEP_CVAR(minelayer, limit))
        PHYS_INPUT_BUTTON_ATCK(actor) = false;
    else
        PHYS_INPUT_BUTTON_ATCK(actor) = bot_aim(actor, weaponentity, WEP_CVAR(minelayer, speed), 0, WEP_CVAR(minelayer, lifetime), false, false);
    if(skill >= 2)                                            
    {
                                           
        float edgedamage, coredamage, edgeradius, recipricoledgeradius;
        float selfdamage, teamdamage, enemydamage;
        edgedamage = WEP_CVAR(minelayer, edgedamage);
        coredamage = WEP_CVAR(minelayer, damage);
        edgeradius = WEP_CVAR(minelayer, radius);
        recipricoledgeradius = 1 / edgeradius;
        selfdamage = 0;
        teamdamage = 0;
        enemydamage = 0;

        IL_EACH(g_mines, it.realowner == actor,
        {
        	entity mine = it;
        	IL_EACH(g_bot_targets, it.bot_attack,
        	{
        		float d = vlen(it.origin + (it.mins + it.maxs) * 0.5 - mine.origin);
        		d = bound(0, edgedamage + (coredamage - edgedamage) * sqrt(1 - d * recipricoledgeradius), 10000);
                                                                     
                if(it == actor)
                    selfdamage = selfdamage + d;
                else if(SAME_TEAM(it, actor))
                    teamdamage = teamdamage + d;
                else if(bot_shouldattack(actor, it))
                    enemydamage = enemydamage + d;
        	});
        });

        float desirabledamage;
        desirabledamage = enemydamage;
        if(StatusEffects_active(STATUSEFFECT_Shield, actor) && !StatusEffects_active(STATUSEFFECT_SpawnShield, actor))
            desirabledamage = desirabledamage - selfdamage * autocvar_g_balance_selfdamagepercent;
        if(teamplay && actor.team)
            desirabledamage = desirabledamage - teamdamage;

        makevectors(actor.v_angle);
        IL_EACH(g_mines, it.realowner == actor,
        {
            if(skill > 9)                                                                
            {
	            entity mine = it;
	            IL_EACH(g_bot_targets, it.bot_attack,
	            {
	            	if((v_forward * normalize(mine.origin - it.origin) < 0.1)
	                    && desirabledamage > 0.1 * coredamage
	                    ) PHYS_INPUT_BUTTON_ATCK2(actor) = true;
	            });
	        }
	        else
	        {
                                                                                       
                                                                                                        
                if((v_forward * normalize(it.origin - actor.enemy.origin) < 0.1)
                	&& IS_PLAYER(actor.enemy)
                	&& (desirabledamage >= 0.1 * coredamage)
                	)
                {
                	float distance = bound(300, vlen(actor.origin - actor.enemy.origin), 30000);
                	if(random() / distance * 300 > frametime * bound(0, (10 - skill) * 0.2, 1))
                		PHYS_INPUT_BUTTON_ATCK2(actor) = true;
                }
	        }
        });

                                                                            
                                                      
        if(desirabledamage >= 0.75 * coredamage)                                                       
            PHYS_INPUT_BUTTON_ATCK2(actor) = true;
        if((skill > 6.5) && (selfdamage > GetResource(actor, RES_HEALTH)))
            PHYS_INPUT_BUTTON_ATCK2(actor) = false;
                                                    
                                              
        if(PHYS_INPUT_BUTTON_ATCK2(actor)) PHYS_INPUT_BUTTON_ATCK(actor) = false;
    }
}
METHOD(MineLayer, wr_think, void(entity thiswep, entity actor, .entity weaponentity, int fire))
{
	actor.(weaponentity).minelayer_mines = W_MineLayer_Count(actor, weaponentity);

    if(autocvar_g_balance_minelayer_reload_ammo && actor.(weaponentity).clip_load < WEP_CVAR(minelayer, ammo))                 
    {
                                                                                                  
        if(!(W_MineLayer_PlacedMines(actor, weaponentity, false) && GetResource(actor, thiswep.ammo_type) < WEP_CVAR(minelayer, ammo))) {
            thiswep.wr_reload(thiswep, actor, weaponentity);
        }
    }
    else if(fire & 1)
    {
        if(weapon_prepareattack(thiswep, actor, weaponentity, false, WEP_CVAR(minelayer, refire)))
        {
            W_MineLayer_Attack(thiswep, actor, weaponentity);
            weapon_thinkf(actor, weaponentity, WFRAME_FIRE1, WEP_CVAR(minelayer, animtime), w_ready);
        }
    }

    if(fire & 2)
    {
        if(W_MineLayer_PlacedMines(actor, weaponentity, true))
            sound(actor, CH_WEAPON_B, SND_MINE_DET, VOL_BASE, ATTN_NORM);
    }
}
METHOD(MineLayer, wr_checkammo1, bool(entity thiswep, entity actor, .entity weaponentity))
{
                                                       
                                                                                              
       
        float ammo_amount = GetResource(actor, thiswep.ammo_type) >= WEP_CVAR(minelayer, ammo);
        ammo_amount += actor.(weaponentity).(weapon_load[thiswep.m_id]) >= WEP_CVAR(minelayer, ammo);
        return ammo_amount;
       
                  
}
METHOD(MineLayer, wr_checkammo2, bool(entity thiswep, entity actor, .entity weaponentity))
{
    if(W_MineLayer_PlacedMines(actor, weaponentity, false))
        return true;
    else
        return false;
}
METHOD(MineLayer, wr_resetplayer, void(entity thiswep, entity actor))
{
    for(int slot = 0; slot < MAX_WEAPONSLOTS; ++slot)
    {
    	.entity weaponentity = weaponentities[slot];
    	actor.(weaponentity).minelayer_mines = 0;
    }
}
METHOD(MineLayer, wr_reload, void(entity thiswep, entity actor, .entity weaponentity))
{
    W_Reload(actor, weaponentity, WEP_CVAR(minelayer, ammo), SND_RELOAD);
}
METHOD(MineLayer, wr_suicidemessage, Notification(entity thiswep))
{
    return WEAPON_MINELAYER_SUICIDE;
}
METHOD(MineLayer, wr_killmessage, Notification(entity thiswep))
{
    return WEAPON_MINELAYER_MURDER;
}

#endif
#ifdef CSQC

METHOD(MineLayer, wr_impacteffect, void(entity thiswep, entity actor))
{
    vector org2 = w_org + w_backoff * 2;
    pointparticles(EFFECT_ROCKET_EXPLODE, org2, '0 0 0', 1);
    if(!w_issilent)
        sound(actor, CH_SHOTS, SND_MINE_EXP, VOL_BASE, ATTN_NORM);
}

#endif
