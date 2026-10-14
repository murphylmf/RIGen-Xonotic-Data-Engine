#include "bobbing.qh"
#ifdef SVQC
.float height;
void func_bobbing_controller_think(entity this)
{
	vector v;
	this.nextthink = time + 0.1;

	if(this.owner.active != ACTIVE_ACTIVE)
	{
		this.owner.velocity = '0 0 0';
		return;
	}

	                                       
	makevectors((this.nextthink * this.owner.cnt + this.owner.phase * 360) * '0 1 0');
	v = this.owner.destvec + this.owner.movedir * v_forward_y;
	if(this.owner.classname == "func_bobbing")                                                           
		                                    
		this.owner.velocity = (v - this.owner.origin) * 10;
}

                                                         
                                                              
                                                       
                                             
                                                                           
                                               
                                                             
                    
  
spawnfunc(func_bobbing)
{
	entity controller;
	if (this.noise != "")
	{
		precache_sound(this.noise);
		soundto(MSG_INIT, this, CH_TRIGGER_SINGLE, this.noise, VOL_BASE, ATTEN_IDLE, 0);
	}
	if (!this.speed)
		this.speed = 4;
	if (!this.height)
		this.height = 32;
	                           
	this.destvec = this.origin;
	                            
	this.cnt = 360 / this.speed;

	this.active = ACTIVE_ACTIVE;

	this.draggable = drag_undraggable;

	                      
	setblocked(this, generic_plat_blocked);
	if(this.dmg && (this.message == ""))
		this.message = " was squished";
	if(this.dmg && (this.message2 == ""))
		this.message2 = "was squished by";
	if(this.dmg && (!this.dmgtime))
		this.dmgtime = 0.25;
	this.dmgtime2 = time;

	                 
	if (this.spawnflags & BOBBING_XAXIS)
		this.movedir = '1 0 0' * this.height;
	else if (this.spawnflags & BOBBING_YAXIS)
		this.movedir = '0 1 0' * this.height;
	else     
		this.movedir = '0 0 1' * this.height;

	if (!InitMovingBrushTrigger(this))
		return;

	                            
	controller = new_pure(func_bobbing_controller);
	controller.owner = this;
	controller.nextthink = time + 1;
	setthink(controller, func_bobbing_controller_think);
	this.nextthink = this.ltime + 999999999;
	setthink(this, SUB_NullThink);

	                                                    
	this.effects |= EF_LOWPRECISION;

	                                          
}
#endif
