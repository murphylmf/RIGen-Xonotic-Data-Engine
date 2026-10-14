#include "hurt.qh"
#ifdef SVQC
void trigger_hurt_use(entity this, entity actor, entity trigger)
{
	if(IS_PLAYER(actor))
		this.enemy = actor;
	else
		this.enemy = NULL;                                                          
}

.float triggerhurttime;
void trigger_hurt_touch(entity this, entity toucher)
{
	if (!toucher.takedamage)
		return;
	if (this.active != ACTIVE_ACTIVE)
		return;

	if(this.team)
		if(((this.spawnflags & INVERT_TEAMS) == 0) == (this.team != toucher.team))
			return;

	                                                                            
	if (toucher.iscreature)
	{
		if (time >= toucher.triggerhurttime + (q3compat && !(this.spawnflags & HURT_SLOW) ? 0.05 : 1))
		{
			EXACTTRIGGER_TOUCH(this, toucher);
			toucher.triggerhurttime = time;

			entity own;
			own = this.enemy;
			if (!IS_PLAYER(own))
			{
				own = this;
				this.enemy = NULL;                        
			}

			Damage (toucher, this, own, this.dmg, DEATH_HURTTRIGGER.m_id, DMG_NOWEP, toucher.origin, '0 0 0');
		}
	}
	else if(toucher.damagedbytriggers)
	{
		EXACTTRIGGER_TOUCH(this, toucher);
		Damage(toucher, this, this, this.dmg, DEATH_HURTTRIGGER.m_id, DMG_NOWEP, toucher.origin, '0 0 0');
	}
}

                                            
                                     
                        
                   
  
.entity trigger_hurt_next;
entity trigger_hurt_last;
entity trigger_hurt_first;
spawnfunc(trigger_hurt)
{
	EXACTTRIGGER_INIT;
	this.active = ACTIVE_ACTIVE;
	settouch(this, trigger_hurt_touch);
	this.use = trigger_hurt_use;
	this.enemy = world;                  
	if (!this.dmg)
		this.dmg = ((q3compat) ? 5 : 10000);
	if (this.message == "")
		this.message = "was in the wrong place";
	if (this.message2 == "")
		this.message2 = "was thrown into a world of hurt by";
	                                                            

	if(!trigger_hurt_first)
		trigger_hurt_first = this;
	if(trigger_hurt_last)
		trigger_hurt_last.trigger_hurt_next = this;
	trigger_hurt_last = this;
}

bool tracebox_hits_trigger_hurt(vector start, vector e_min, vector e_max, vector end)
{
	entity th;

	for(th = trigger_hurt_first; th; th = th.trigger_hurt_next)
		if(tracebox_hits_box(start, e_min, e_max, end, th.absmin, th.absmax))
			return true;

	return false;
}
#endif
