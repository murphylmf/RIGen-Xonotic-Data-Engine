#include "breakable.qh"
#ifdef SVQC

#include <server/damage.qh>
#include <server/bot/api.qh>
#include <common/csqcmodel_settings.qh>
#include <lib/csqcmodel/sv_model.qh>
#include <server/weapons/common.qh>

.entity sprite;

.float dmg;
.float dmg_edge;
.float dmg_radius;
.float dmg_force;
.float debrismovetype;
.float debrissolid;
.vector debrisvelocity;
.vector debrisvelocityjitter;
.vector debrisavelocityjitter;
.float debristime;
.float debristimejitter;
.float debrisfadetime;
.float debrisdamageforcescale;
.float debrisskin;

.string mdl_dead;                             
.string debris;                                         
                
                               
                                       
                                                        
                                            
                                          
                
                                                        
                                                 
                                                                                                                         
                                         
         
                                                                            
                                                                             
               

void func_breakable_damage(entity this, entity inflictor, entity attacker, float damage, int deathtype, .entity weaponentity, vector hitloc, vector force);

  
                 
                                                                 
  
void LaunchDebris (entity this, string debrisname, vector force)
{
	entity dbr = new(debris);
	vector org = this.absmin
	           + '1 0 0' * random() * (this.absmax.x - this.absmin.x)
	           + '0 1 0' * random() * (this.absmax.y - this.absmin.y)
	           + '0 0 1' * random() * (this.absmax.z - this.absmin.z);
	setorigin(dbr, org);
	_setmodel (dbr, debrisname );
	dbr.skin = this.debrisskin;
	dbr.colormap = this.colormap;                       
	dbr.owner = this;                                           
	set_movetype(dbr, this.debrismovetype);
	dbr.solid = this.debrissolid;
	if(dbr.solid != SOLID_BSP)                                                                        
		setsize(dbr, '0 0 0', '0 0 0');                                                                
	dbr.velocity_x = this.debrisvelocity.x + this.debrisvelocityjitter.x * crandom();
	dbr.velocity_y = this.debrisvelocity.y + this.debrisvelocityjitter.y * crandom();
	dbr.velocity_z = this.debrisvelocity.z + this.debrisvelocityjitter.z * crandom();
	dbr.velocity = dbr.velocity + force * this.debrisdamageforcescale;
	dbr.angles = this.angles;
	dbr.avelocity_x = random()*this.debrisavelocityjitter.x;
	dbr.avelocity_y = random()*this.debrisavelocityjitter.y;
	dbr.avelocity_z = random()*this.debrisavelocityjitter.z;
	dbr.damageforcescale = this.debrisdamageforcescale;
	if(dbr.damageforcescale)
		dbr.takedamage = DAMAGE_YES;
	SUB_SetFade(dbr, time + this.debristime + crandom() * this.debristimejitter, this.debrisfadetime);
}

void func_breakable_colormod(entity this)
{
	float h;
	if (!(this.spawnflags & BREAKABLE_INDICATE_DAMAGE))
		return;
	h = GetResource(this, RES_HEALTH) / this.max_health;
	if(h < 0.25)
		this.colormod = '1 0 0';
	else if(h <= 0.75)
		this.colormod = '1 0 0' + '0 1 0' * (2 * h - 0.5);
	else
		this.colormod = '1 1 1';
}

void func_breakable_look_destroyed(entity this)
{
	float floorZ;

	if(this.solid == SOLID_BSP)                                                                 
		this.dropped_origin = this.origin;

	this.solid = SOLID_NOT;                                                           

	if(this.mdl_dead == "")
	{
		setorigin (this, this.origin);          
		this.effects |= EF_NODRAW;
	}
	else {
		if (this.origin == '0 0 0')	{	                                                                      
			floorZ = this.absmin.z;
			setorigin(this, ((this.absmax + this.absmin) * 0.5));
			this.origin_z = floorZ;
		}
		_setmodel(this, this.mdl_dead);
		ApplyMinMaxScaleAngles(this);
		this.effects &= ~EF_NODRAW;
	}
}

void func_breakable_look_restore(entity this)
{
	this.solid = SOLID_BSP;                                                          

	_setmodel(this, this.mdl);
	ApplyMinMaxScaleAngles(this);
	this.effects &= ~EF_NODRAW;

	if(this.mdl_dead != "")                                                                      
		setorigin(this, this.dropped_origin);
}

void func_breakable_behave_destroyed(entity this)
{
	SetResourceExplicit(this, RES_HEALTH, this.max_health);
	this.takedamage = DAMAGE_NO;
	if(this.bot_attack)
		IL_REMOVE(g_bot_targets, this);
	this.bot_attack = false;
	this.event_damage = func_null;
	this.state = STATE_BROKEN;
	if(this.spawnflags & BREAKABLE_NODAMAGE)
		this.use = func_null;
	func_breakable_colormod(this);
	if (this.noise1)
		stopsound (this, CH_TRIGGER_SINGLE);

	IL_EACH(g_projectiles, it.classname == "grapplinghook" && it.aiment == this,
	{
		RemoveHook(it);
	});
}

void func_breakable_think(entity this)
{
	this.nextthink = time;
	CSQCMODEL_AUTOUPDATE(this);
}

void func_breakable_destroy(entity this, entity actor, entity trigger);
void func_breakable_behave_restore(entity this)
{
	SetResourceExplicit(this, RES_HEALTH, this.max_health);
	if(this.sprite)
	{
		WaypointSprite_UpdateMaxHealth(this.sprite, this.max_health);
		WaypointSprite_UpdateHealth(this.sprite, GetResource(this, RES_HEALTH));
	}
	if(!(this.spawnflags & BREAKABLE_NODAMAGE))
	{
		this.takedamage = DAMAGE_AIM;
		if(!this.bot_attack)
			IL_PUSH(g_bot_targets, this);
		this.bot_attack = true;
		this.event_damage = func_breakable_damage;
	}
	if(this.spawnflags & BREAKABLE_NODAMAGE)
		this.use = func_breakable_destroy;                                                     
	this.state = STATE_ALIVE;
	                                            
	setthink(this, func_breakable_think);
	this.nextthink = time + 0.1;
	func_breakable_colormod(this);
	if (this.noise1)
		_sound (this, CH_TRIGGER_SINGLE, this.noise1, VOL_BASE, ATTEN_NORM);
}

void func_breakable_init_for_player(entity this, entity player)
{
	if (this.noise1 && this.state == STATE_ALIVE && IS_REAL_CLIENT(player))
	{
		msg_entity = player;
		soundto (MSG_ONE, this, CH_TRIGGER_SINGLE, this.noise1, VOL_BASE, ATTEN_NORM, 0);
	}
}

void func_breakable_destroyed(entity this)
{
	func_breakable_look_destroyed(this);
	func_breakable_behave_destroyed(this);
}

void func_breakable_restore(entity this, entity actor, entity trigger)
{
	func_breakable_look_restore(this);
	func_breakable_behave_restore(this);
}

void func_breakable_restore_self(entity this)
{
	                                                                                     
	float oldhit = this.dphitcontentsmask;
	this.dphitcontentsmask = DPCONTENTS_BODY;                                                                                               
	tracebox(this.origin, this.mins, this.maxs, this.origin, MOVE_NORMAL, this);
	this.dphitcontentsmask = oldhit;
	if(trace_startsolid || trace_fraction < 1)
	{
		this.nextthink = time + 5;                                                      
		return;
	}
	func_breakable_restore(this, NULL, NULL);
}

vector debrisforce;                                   
void func_breakable_destroy(entity this, entity actor, entity trigger)
{
	float n, i;
	string oldmsg;

	entity act = this.owner;
	this.owner = NULL;                                     

	                              
	n = tokenize_console(this.debris);
	for(i = 0; i < n; ++i)
		LaunchDebris(this, argv(i), debrisforce);

	func_breakable_destroyed(this);

	if(this.noise)
		_sound (this, CH_TRIGGER, this.noise, VOL_BASE, ATTEN_NORM);

	if(this.dmg)
		RadiusDamage(this, act, this.dmg, this.dmg_edge, this.dmg_radius, this, NULL, this.dmg_force, DEATH_HURTTRIGGER.m_id, DMG_NOWEP, NULL);

	if(this.cnt)        
		__pointparticles(this.cnt, this.absmin * 0.5 + this.absmax * 0.5, '0 0 0', this.count);

	if(this.respawntime)
	{
		CSQCMODEL_AUTOUPDATE(this);
		setthink(this, func_breakable_restore_self);
		this.nextthink = time + this.respawntime + crandom() * this.respawntimejitter;
	}

	oldmsg = this.message;
	this.message = "";
	SUB_UseTargets(this, act, trigger);
	this.message = oldmsg;
}

void func_breakable_destroy_self(entity this)
{
	func_breakable_destroy(this, NULL, NULL);
}

void func_breakable_damage(entity this, entity inflictor, entity attacker, float damage, int deathtype, .entity weaponentity, vector hitloc, vector force)
{
	if(this.state == STATE_BROKEN)
		return;
	if(this.spawnflags & NOSPLASH)
		if(!(DEATH_ISSPECIAL(deathtype)) && (deathtype & HITTYPE_SPLASH))
			return;
	if(this.team)
		if(attacker.team == this.team)
			return;
	this.pain_finished = time;
	TakeResource(this, RES_HEALTH, damage);
	if(this.sprite)
	{
		WaypointSprite_Ping(this.sprite);
		WaypointSprite_UpdateHealth(this.sprite, GetResource(this, RES_HEALTH));
	}
	func_breakable_colormod(this);

	if(GetResource(this, RES_HEALTH) <= 0)
	{
		debrisforce = force;

		this.takedamage = DAMAGE_NO;
		this.event_damage = func_null;

		if(IS_CLIENT(attacker))                                                    
		{
			this.owner = attacker;
			this.realowner = attacker;
		}

		                                            
		                                                          
		this.nextthink = time;
		CSQCMODEL_AUTOUPDATE(this);
		setthink(this, func_breakable_destroy_self);
	}
}

void func_breakable_reset(entity this)
{
	this.team = this.team_saved;
	func_breakable_look_restore(this);
	if(this.spawnflags & START_DISABLED)
		func_breakable_behave_destroyed(this);
	else
		func_breakable_behave_restore(this);
}

void func_breakable_setup(entity this)
{
	float n, i;
	if(!GetResource(this, RES_HEALTH))
		SetResourceExplicit(this, RES_HEALTH, 100);
	this.max_health = GetResource(this, RES_HEALTH);

	                                                                                           
	if(!this.debrismovetype) this.debrismovetype = MOVETYPE_BOUNCE;
	if(!this.debrissolid) this.debrissolid = SOLID_NOT;
	if(this.debrisvelocity == '0 0 0') this.debrisvelocity = '0 0 140';
	if(this.debrisvelocityjitter == '0 0 0') this.debrisvelocityjitter = '70 70 70';
	if(this.debrisavelocityjitter == '0 0 0') this.debrisavelocityjitter = '600 600 600';
	if(!this.debristime) this.debristime = 3.5;
	if(!this.debristimejitter) this.debristime = 2.5;

	if(this.mdl != "")
		this.cnt = _particleeffectnum(this.mdl);
	if(this.count == 0)
		this.count = 1;

	if(this.message == "")
		this.message = "got too close to an explosion";
	if(this.message2 == "")
		this.message2 = "was pushed into an explosion by";
	if(!this.dmg_radius)
		this.dmg_radius = 150;
	if(!this.dmg_force)
		this.dmg_force = 200;

	this.mdl = this.model;
	SetBrushEntityModel(this, true);

	if(this.spawnflags & BREAKABLE_NODAMAGE)
		this.use = func_breakable_destroy;
	else
		this.use = func_breakable_restore;

	if(this.spawnflags & BREAKABLE_NODAMAGE)
	{
		this.takedamage = DAMAGE_NO;
		this.event_damage = func_null;
		this.bot_attack = false;
		this.monster_attack = false;
	}

	                          
	if (this.mdl_dead)
		precache_model(this.mdl_dead);
	n = tokenize_console(this.debris);
	for(i = 0; i < n; ++i)
		precache_model(argv(i));
	if(this.noise)
		precache_sound(this.noise);
	if(this.noise1)
		precache_sound(this.noise1);

	this.team_saved = this.team;
	IL_PUSH(g_saved_team, this);
	this.dropped_origin = this.origin;

	this.reset = func_breakable_reset;
	this.reset(this);

	if(this.monster_attack)
		IL_PUSH(g_monster_targets, this);

	IL_PUSH(g_initforplayer, this);
	this.init_for_player = func_breakable_init_for_player;

	CSQCMODEL_AUTOINIT(this);
}

                                         
spawnfunc(misc_breakablemodel) { func_breakable_setup(this); }

                                                                           
spawnfunc(func_breakable) { func_breakable_setup(this); }
#endif
