#include "impulse.qh"
                              
void trigger_impulse_touch_directional(entity this, entity toucher)
{
	entity targ;
	float pushdeltatime;
	float str;

	if (this.active != ACTIVE_ACTIVE)
		return;

	if (!isPushable(toucher))
		return;

	EXACTTRIGGER_TOUCH(this, toucher);

	targ = find(NULL, targetname, this.target);
	if(!targ)
	{
		objerror(this, "trigger_force without a (valid) .target!\n");
		delete(this);
		return;
	}

	                                                                          
	str = this.strength;

	pushdeltatime = time - toucher.lastpushtime;
	if (pushdeltatime > IMPULSE_MAX_PUSHDELTATIME)
	{
		pushdeltatime = 0;
	}
	toucher.lastpushtime = time;
	if(!pushdeltatime)
	{
		return;
	}

	if(this.spawnflags & IMPULSE_DIRECTIONAL_SPEEDTARGET)
	{
		float addspeed = str - toucher.velocity * normalize(targ.origin - this.origin);
		if (addspeed > 0)
		{
			float accelspeed = min(IMPULSE_DIRECTIONAL_MAX_ACCEL_FACTOR * pushdeltatime * str, addspeed);
			toucher.velocity += accelspeed * normalize(targ.origin - this.origin);
		}
	}
	else
		toucher.velocity = toucher.velocity + normalize(targ.origin - this.origin) * str * pushdeltatime;

	UNSET_ONGROUND(toucher);

#ifdef SVQC
	UpdateCSQCProjectile(toucher);
#endif
}

                                               
void trigger_impulse_touch_accel(entity this, entity toucher)
{
	float pushdeltatime;

	if (this.active != ACTIVE_ACTIVE)
		return;

	if (!isPushable(toucher))
		return;

	EXACTTRIGGER_TOUCH(this, toucher);

	pushdeltatime = time - toucher.lastpushtime;
	if (pushdeltatime > IMPULSE_MAX_PUSHDELTATIME)
	{
		pushdeltatime = 0;
	}
	toucher.lastpushtime = time;
	if(!pushdeltatime)
	{
		return;
	}

	                                                   
	toucher.velocity = toucher.velocity * (this.strength ** pushdeltatime);

#ifdef SVQC
	UpdateCSQCProjectile(toucher);
#endif
}

                                    
void trigger_impulse_touch_radial(entity this, entity toucher)
{
	float pushdeltatime;
	float str;

	if (this.active != ACTIVE_ACTIVE)
		return;

	if (!isPushable(toucher))
		return;

	EXACTTRIGGER_TOUCH(this, toucher);

	pushdeltatime = time - toucher.lastpushtime;
	if (pushdeltatime > IMPULSE_MAX_PUSHDELTATIME)
	{
		pushdeltatime = 0;
	}
	toucher.lastpushtime = time;
	if(!pushdeltatime)
	{
		return;
	}

	setsize(this, '-1 -1 -1' * this.radius,'1 1 1' * this.radius);

	str = min(this.radius, vlen(this.origin - toucher.origin));

	if(this.falloff == FALLOFF_LINEAR)
		str = (1 - str / this.radius) * this.strength;                   
	else if(this.falloff == FALLOFF_LINEAR_INV)
		str = (str / this.radius) * this.strength;                   
	else
		str = this.strength;

	toucher.velocity = toucher.velocity + normalize(toucher.origin - this.origin) * str * pushdeltatime;

#ifdef SVQC
	UpdateCSQCProjectile(toucher);
#endif
}

REGISTER_NET_LINKED(ENT_CLIENT_TRIGGER_IMPULSE)

                                               
           
                      
                                                                                                          
                                                             

                                                                                
                                                                          
                                                                                                       

                                                                      

                                                   

                       
                                                                                                  
                                                                                                        
  
#ifdef SVQC
bool trigger_impulse_send(entity this, entity to, int sf)
{
	WriteHeader(MSG_ENTITY, ENT_CLIENT_TRIGGER_IMPULSE);

	WriteByte(MSG_ENTITY, this.spawnflags);
	WriteCoord(MSG_ENTITY, this.radius);
	WriteCoord(MSG_ENTITY, this.strength);
	WriteByte(MSG_ENTITY, this.falloff);
	WriteByte(MSG_ENTITY, this.active);

	trigger_common_write(this, true);

	return true;
}

void trigger_impulse_link(entity this)
{
	trigger_link(this, trigger_impulse_send);
}

spawnfunc(trigger_impulse)
{
	this.active = ACTIVE_ACTIVE;
	WarpZoneLib_ExactTrigger_Init(this, false);
	BITSET_ASSIGN(this.effects, EF_NODEPTHTEST);

	if(this.radius)
	{
		if(!this.strength)
		{
			this.strength = IMPULSE_DEFAULT_RADIAL_STRENGTH * autocvar_g_triggerimpulse_radial_multiplier;
		}
		setorigin(this, this.origin);
		setsize(this, '-1 -1 -1' * this.radius,'1 1 1' * this.radius);
		settouch(this, trigger_impulse_touch_radial);
	}
	else
	{
		if(this.target)
		{
			if(!this.strength)
			{
				this.strength = IMPULSE_DEFAULT_DIRECTIONAL_STRENGTH * autocvar_g_triggerimpulse_directional_multiplier;
			}
			settouch(this, trigger_impulse_touch_directional);
		}
		else
		{
			if(!this.strength)
			{
				this.strength = IMPULSE_DEFAULT_ACCEL_STRENGTH;
			}
			this.strength = (this.strength ** autocvar_g_triggerimpulse_accel_power) * autocvar_g_triggerimpulse_accel_multiplier;
			settouch(this, trigger_impulse_touch_accel);
		}
	}

	trigger_impulse_link(this);
}
#elif defined(CSQC)
NET_HANDLE(ENT_CLIENT_TRIGGER_IMPULSE, bool isnew)
{
	this.spawnflags = ReadByte();
	this.radius = ReadCoord();
	this.strength = ReadCoord();
	this.falloff = ReadByte();
	this.active = ReadByte();

	trigger_common_read(this, true);
	return = true;

	this.solid = SOLID_TRIGGER;
	this.entremove = trigger_remove_generic;
	this.move_time = time;

	if (this.radius)
	{
		settouch(this, trigger_impulse_touch_radial);
	}
	else if (this.target)
	{
		settouch(this, trigger_impulse_touch_directional);
	}
	else
	{
		settouch(this, trigger_impulse_touch_accel);
	}
}
#endif
