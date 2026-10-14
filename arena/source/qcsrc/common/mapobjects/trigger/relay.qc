#include "relay.qh"
#ifdef SVQC

void relay_use(entity this, entity actor, entity trigger)
{
	if(this.active != ACTIVE_ACTIVE)
		return;

	SUB_UseTargets(this, actor, trigger);
}

                                                              
                                                                                                                                            
  
spawnfunc(trigger_relay)
{
	this.active = ACTIVE_ACTIVE;
	this.use = relay_use;
	this.reset = spawnfunc_trigger_relay;                               
}

spawnfunc(target_relay)
{
	spawnfunc_trigger_relay(this);
}

spawnfunc(target_delay)
{
	if(!this.wait)
		this.wait = 1;
	if(!this.delay)
		this.delay = this.wait;                              
	spawnfunc_trigger_relay(this);
}
#endif
