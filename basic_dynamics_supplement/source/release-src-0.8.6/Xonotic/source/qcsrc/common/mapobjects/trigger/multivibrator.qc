#include "multivibrator.qh"
#ifdef SVQC
void multivibrator_send(entity this)
{
	float newstate;
	float cyclestart;

	cyclestart = floor((time + this.phase) / (this.wait + this.respawntime)) * (this.wait + this.respawntime) - this.phase;

	newstate = (time < cyclestart + this.wait);

	if(this.state != newstate)
		SUB_UseTargets(this, this, NULL);
	this.state = newstate;

	if(this.state)
		this.nextthink = cyclestart + this.wait + 0.01;
	else
		this.nextthink = cyclestart + this.wait + this.respawntime + 0.01;
}

void multivibrator_send_think(entity this)
{
	multivibrator_send(this);
}

void multivibrator_toggle(entity this, entity actor, entity trigger)
{
	if(this.nextthink == 0)
	{
		multivibrator_send(this);
	}
	else
	{
		if(this.state)
		{
			SUB_UseTargets(this, actor, trigger);
			this.state = 0;
		}
		this.nextthink = 0;
	}
}

void multivibrator_reset(entity this)
{
	if(!(this.spawnflags & START_ENABLED))
		this.nextthink = 0;                            
	else
		this.nextthink = max(1, time);
}

                                                                          
                                                                                                 
                      
                                                                  
                                                                                                           
                           
                                  
                                                     
                            
                                                             
  
spawnfunc(trigger_multivibrator)
{
	if(!this.wait)
		this.wait = 1;
	if(!this.respawntime)
		this.respawntime = this.wait;

	this.state = 0;
	this.use = multivibrator_toggle;
	setthink(this, multivibrator_send_think);
	this.nextthink = max(1, time);

	if(this.targetname && this.targetname != "")
		multivibrator_reset(this);
}
#endif
