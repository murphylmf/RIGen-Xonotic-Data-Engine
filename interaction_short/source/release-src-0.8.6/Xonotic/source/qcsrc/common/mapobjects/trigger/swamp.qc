#include "swamp.qh"
#if defined(CSQC)
#elif defined(MENUQC)
#elif defined(SVQC)
    #include <lib/warpzone/util_server.qh>
    #include <common/weapons/_all.qh>
    #include <common/weapons/_all.qh>
    #include <common/stats.qh>
    #include <common/deathtypes/all.qh>
#endif

  
            
                                                                                  
                          
                   
             
  

#ifdef SVQC
void swamp_think(entity this)
{
	                                                 
	IL_EACH(g_swamped, it.swampslug == this,
	{
		it.swampslug = NULL;
		IL_REMOVE(g_swamped, it);
	});

	if(this.active == ACTIVE_ACTIVE)
	{
		FOREACH_ENTITY_RADIUS((this.absmin + this.absmax) * 0.5, vlen(this.absmax - this.absmin) * 0.5 + 1, it.swampslug.active == ACTIVE_NOT && IS_PLAYER(it) && !IS_DEAD(it),
		{
			vector emin = it.absmin;
			vector emax = it.absmax;
			if(this.solid == SOLID_BSP)
			{
				emin -= '1 1 1';
				emax += '1 1 1';
			}
			if(boxesoverlap(emin, emax, this.absmin, this.absmax))         
				if(WarpZoneLib_BoxTouchesBrush(emin, emax, this, it))            
				{
					if(!it.swampslug)
						IL_PUSH(g_swamped, it);
					it.swampslug = this;
				}
		});

		IL_EACH(g_swamped, it.swampslug == this,
		{
			if(time > it.swamp_interval)
			{
				Damage (it, this, this, this.dmg, DEATH_SWAMP.m_id, DMG_NOWEP, it.origin, '0 0 0');
				it.swamp_interval = time + this.swamp_interval;
			}
		});
	}

	this.nextthink = time;
}

                                             
                            
                                 
  
spawnfunc(trigger_swamp)
{
	             
	EXACTTRIGGER_INIT;
	this.active = ACTIVE_ACTIVE;
	setthink(this, swamp_think);
	this.nextthink = time;

	                                 
	if(!this.dmg)
		this.dmg = 5;
	if(!this.swamp_interval)
		this.swamp_interval = 1;
	if(!this.swamp_slowdown)
		this.swamp_slowdown = 0.5;
}
#endif
