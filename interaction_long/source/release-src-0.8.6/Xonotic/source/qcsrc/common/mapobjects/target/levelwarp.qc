#include "levelwarp.qh"

#ifdef SVQC
void target_levelwarp_use(entity this, entity actor, entity trigger)
{
	if(!autocvar_g_campaign)
		return;                    

	if(this.cnt)
		CampaignLevelWarp(this.cnt - 1);                  
	else
		CampaignLevelWarp(-1);              
}

spawnfunc(target_levelwarp)
{
	                                                                       
	                     
	this.use = target_levelwarp_use;
}
#endif
