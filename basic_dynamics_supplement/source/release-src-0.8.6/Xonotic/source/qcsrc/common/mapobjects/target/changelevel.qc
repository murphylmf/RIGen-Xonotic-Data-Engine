#include "changelevel.qh"
#ifdef SVQC
.string chmap, gametype;
.entity chlevel_targ;

void target_changelevel_use(entity this, entity actor, entity trigger)
{
	if(game_stopped)
		return;

	if(this.spawnflags & CHANGELEVEL_MULTIPLAYER)
	{
		                                                 
		if(!IS_PLAYER(actor)) { return; }

		actor.chlevel_targ = this;

		int plnum = 0;
		int realplnum = 0;
		                       
		FOREACH_CLIENT(IS_PLAYER(it) && IS_REAL_CLIENT(it), {
			++realplnum;
			if(it.chlevel_targ == this)
				++plnum;
		});
		if(plnum < ceil(realplnum * min(1, this.count)))                  
			return;
	}

	if(this.gametype != "")
		MapInfo_SwitchGameType(MapInfo_Type_FromString(this.gametype, false, false));

	if (this.chmap == "")
	{
		if(IS_REAL_CLIENT(actor) && autocvar_g_campaign)                                                                                    
			campaign_forcewin = true;                                                       
		NextLevel();
	}
	else
		changelevel(this.chmap);
}

                    
                          
     
                                                 
                                   
                                                                                
           
                                            
  

spawnfunc(target_changelevel)
{
	this.use = target_changelevel_use;

	if(!this.count)
	{
		this.count = 0.7;
	}
}
#endif
