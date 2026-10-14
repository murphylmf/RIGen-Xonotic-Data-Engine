#include "dynlight.qh"

#ifdef SVQC
#include <common/weapons/_all.qh>
#include <common/stats.qh>

const float LOOP = 1;

.float speed;

                          
const int DFOLLOW = 4;
.float light_lev;
.float lefty;
.vector color;
.string dtagname;

                                                                      
                        
                                                                                                                                                      
                                                        
                                              
     
                                               
                                                                                                                                                                  
                                             
                            
                                                                 
                                          
                                                                                                                                                                                                                                                        
                                                  
                                                                                                                                                                                                                                                                                                                                
                                                            
      
                                                               
                                                          
                                                                   
  
void dynlight_think(entity this)
{
	if(!this.owner)
		delete(this);

	this.nextthink = time + 0.1;
}
void dynlight_find_aiment(entity this)
{
	entity targ;
	if (!this.target || this.target == "")
		objerror (this, "dynlight: no target to follow");

	targ = find(NULL, targetname, this.target);
	set_movetype(this, MOVETYPE_FOLLOW);
	this.aiment = targ;
	this.owner = targ;
	this.punchangle = targ.angles;
	this.view_ofs = this.origin - targ.origin;
	this.v_angle = this.angles - targ.angles;
	setthink(this, dynlight_think);
	this.nextthink = time + 0.1;
}
void dynlight_find_path(entity this)
{
	entity targ;
	if (!this.target || this.target == "")
		objerror (this, "dynlight: no target to follow");

	targ = find(NULL, targetname, this.target);
	this.target = targ.target;
	setorigin(this, targ.origin);
	setthink(this, train_next);                                                  
	this.nextthink = time + 0.1;
}
void dynlight_find_target(entity this)
{
	entity targ;
	if (!this.target || this.target == "")
		objerror (this, "dynlight: no target to follow");

	targ = find(NULL, targetname, this.target);
	setattachment(this, targ, this.dtagname);
	this.owner = targ;
	setthink(this, dynlight_think);
	this.nextthink = time + 0.1;
}
void dynlight_use(entity this, entity actor, entity trigger)
{
	if (this.light_lev == 0)
		this.light_lev = this.lefty;
	else
		this.light_lev = 0;
}
spawnfunc(dynlight)
{
	if (!this.light_lev)
		this.light_lev = 200;
	if (!this.color)
		this.color = '1 1 1';
	this.lefty = this.light_lev;
	this.use = dynlight_use;
	setsize (this, '0 0 0', '0 0 0');
	setorigin(this, this.origin);
	                                   
	this.solid = SOLID_NOT;
	                           
	                                  
	                                               
	                                  
	                      

               
	if (this.dtagname)
	{
		InitializeEntity(this, dynlight_find_target, INITPRIO_FINDTARGET);
		return;
	}

                   
	if (this.spawnflags & DFOLLOW)
	{
		InitializeEntity(this, dynlight_find_aiment, INITPRIO_FINDTARGET);
		return;
	}
                 
	if (this.target)
                                    
	{
		set_movetype(this, MOVETYPE_NOCLIP);
		if (!this.speed)
			this.speed = 100;
		InitializeEntity(this, dynlight_find_path, INITPRIO_FINDTARGET);
		return;
	}
}
#endif
