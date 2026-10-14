#include "door_rotating.qh"
                                                                                                                      
                                                                           

                                                                                    

                                                                                                         
                                                                                                                                          
                                   
                                                                                                        

                                                                                                                                                                                                                   

                                                                                                  
                                                                                             
                                                                                                               
                                       
                                     
                                                            
                                                 
        
           
        
       
              
                 
                                                     
  

#ifdef GAMEQC
void door_rotating_hit_top(entity this)
{
	if (this.noise1 != "")
		_sound (this, CH_TRIGGER_SINGLE, this.noise1, VOL_BASE, ATTEN_NORM);
	this.state = STATE_TOP;
	if (this.spawnflags & DOOR_TOGGLE)
		return;		                                
	setthink(this, door_rotating_go_down);
	this.nextthink = this.ltime + this.wait;
}

void door_rotating_hit_bottom(entity this)
{
	if (this.noise1 != "")
		_sound (this, CH_TRIGGER_SINGLE, this.noise1, VOL_BASE, ATTEN_NORM);
	if (this.lip==666)                                                                            
	{
		this.pos2 = '0 0 0' - this.pos2;
		this.lip = 0;
	}
	this.state = STATE_BOTTOM;
}

void door_rotating_go_down(entity this)
{
	if (this.noise2 != "")
		_sound (this, CH_TRIGGER_SINGLE, this.noise2, VOL_BASE, ATTEN_NORM);
	if (this.max_health)
	{
		this.takedamage = DAMAGE_YES;
		SetResourceExplicit(this, RES_HEALTH, this.max_health);
	}

	this.state = STATE_DOWN;
	SUB_CalcAngleMove (this, this.pos1, TSPEED_LINEAR, this.speed, door_rotating_hit_bottom);
}

void door_rotating_go_up(entity this, entity oth)
{
	if (this.state == STATE_UP)
		return;		                   

	if (this.state == STATE_TOP)
	{	                      
		this.nextthink = this.ltime + this.wait;
		return;
	}
	if (this.noise2 != "")
		_sound (this, CH_TRIGGER_SINGLE, this.noise2, VOL_BASE, ATTEN_NORM);
	this.state = STATE_UP;
	SUB_CalcAngleMove (this, this.pos2, TSPEED_LINEAR, this.speed, door_rotating_hit_top);

	string oldmessage;
	oldmessage = this.message;
	this.message = "";
	SUB_UseTargets(this, NULL, oth);                             
	this.message = oldmessage;
}
#endif

#ifdef SVQC
void door_rotating_reset(entity this)
{
	this.angles = this.pos1;
	this.avelocity = '0 0 0';
	this.state = STATE_BOTTOM;
	setthink(this, func_null);
	this.nextthink = 0;
}

void door_rotating_init_startopen(entity this)
{
	this.angles = this.movedir;
	this.pos2 = '0 0 0';
	this.pos1 = this.movedir;
}

spawnfunc(func_door_rotating)
{
	                                                      
	                                      

	                                                  
	if (this.spawnflags & DOOR_ROTATING_XAXIS)
		this.movedir = '0 0 1';
	else if (this.spawnflags & DOOR_ROTATING_YAXIS)
		this.movedir = '1 0 0';
	else     
		this.movedir = '0 1 0';

	if (this.angles_y==0) this.angles_y = 90;

	this.movedir = this.movedir * this.angles_y;
	this.angles = '0 0 0';

	this.avelocity = this.movedir;
	if (!InitMovingBrushTrigger(this))
		return;
	this.velocity = '0 0 0';
	                                  
	this.classname = "door_rotating";

	setblocked(this, door_blocked);
	this.use = door_use;

	this.pos1 = '0 0 0';
	this.pos2 = this.movedir;

                                                                             
                                 
	if (this.spawnflags & DOOR_START_OPEN)
		InitializeEntity(this, door_rotating_init_startopen, INITPRIO_SETLOCATION);

	door_init_shared(this);
	if (!this.speed)
	{
		this.speed = 50;
	}
	this.lip = 0;                                                                            

	settouch(this, door_touch);

                                                                       
                                      
	InitializeEntity(this, LinkDoors, INITPRIO_LINKDOORS);

	this.reset = door_rotating_reset;
}
#endif
