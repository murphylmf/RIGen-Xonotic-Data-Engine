#include "relay_activators.qh"

#ifdef SVQC
void relay_activators_use(entity this, entity actor, entity trigger)
{
	if(this.active != ACTIVE_ACTIVE)
		return;

	for(entity trg = NULL; (trg = find(trg, targetname, this.target)); )
	{
		if (trg.setactive)
			trg.setactive(trg, this.cnt);
		else
		{
			                                  
			generic_setactive(trg, this.cnt);
		}
	}
}

void relay_activators_init(entity this)
{
	this.reset = relay_activators_init;                               
	this.active = ACTIVE_ACTIVE;
	this.use = relay_activators_use;
}

spawnfunc(relay_activate)
{
	this.cnt = ACTIVE_ACTIVE;
	relay_activators_init(this);
}

spawnfunc(relay_deactivate)
{
	this.cnt = ACTIVE_NOT;
	relay_activators_init(this);
}

spawnfunc(relay_activatetoggle)
{
	this.cnt = ACTIVE_TOGGLE;
	relay_activators_init(this);
}
#endif
