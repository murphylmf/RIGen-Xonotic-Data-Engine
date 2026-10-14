#include "walk.qh"

void _Movetype_Physics_Walk(entity this, float dt)                
{
	                                                                                 
	if (dt <= 0)
		return;

	if (GAMEPLAYFIX_UNSTICKPLAYERS(this))
		_Movetype_CheckStuck(this);

	bool applygravity = (!_Movetype_CheckWater(this) && this.move_movetype == MOVETYPE_WALK && !(this.flags & FL_WATERJUMP));

	_Movetype_CheckVelocity(this);

	                                                                   
	bool oldonground = IS_ONGROUND(this);

	vector start_origin = this.origin;
	vector start_velocity = this.velocity;

	if(PHYS_WALLCLIP(this) && this.pm_time)
	{
		if(dt >= this.pm_time || (this.flags & FL_WATERJUMP))
			this.pm_time = 0;
		else
			this.pm_time -= dt;
	}

	int clip = _Movetype_FlyMove(this, dt, applygravity, false, GAMEPLAYFIX_STEPMULTIPLETIMES(this) ? PHYS_STEPHEIGHT(this) : 0);

	if (GAMEPLAYFIX_DOWNTRACEONGROUND(this) && !(clip & 1))
	{
		                                                                   
		                                                                    
		                                     
		vector upmove = this.origin + '0 0 1';
		vector downmove = this.origin - '0 0 1';
		int type;
		if (this.move_nomonsters)
			type = max(0, this.move_nomonsters);
		else if (this.move_movetype == MOVETYPE_FLYMISSILE)
			type = MOVE_MISSILE;
		else if (this.move_movetype == MOVETYPE_FLY_WORLDONLY)
			type = MOVE_WORLDONLY;
		else if (this.solid == SOLID_TRIGGER || this.solid == SOLID_NOT)
			type = MOVE_NOMONSTERS;
		else
			type = MOVE_NORMAL;
		tracebox(upmove, this.mins, this.maxs, downmove, type, this);
		if (trace_fraction < 1 && trace_plane_normal.z > 0.7)
		{
			clip |= 1;                              
			                                                               
			this.groundentity = trace_ent;
		}
	}

	                                                                       
	if (!(clip & 1))
		UNSET_ONGROUND(this);
	else if(PHYS_WALLCLIP(this) && !this.groundentity && (PHYS_WALLCLIP(this) == 2 || start_velocity.z < -200))                                                            
		this.pm_time = 0.25;

	_Movetype_CheckVelocity(this);
	_Movetype_LinkEdict(this, true);

	if (clip & 8)             
		return;

	if (this.flags & FL_WATERJUMP)
		return;

	if (PHYS_NOSTEP(this))
		return;

	vector originalorigin = this.origin;
	vector originalvelocity = this.velocity;
	                            
	int originalflags = this.flags;
	entity originalmove_groundentity = this.groundentity;

	                                         
	if (clip & 2)
	{
		                                                       
		if (fabs(start_velocity.x) < 0.03125 && fabs(start_velocity.y) < 0.03125)
			return;

		if (this.move_movetype != MOVETYPE_FLY)
		{
			                                
			if (this.move_movetype != MOVETYPE_WALK)
				return;

			                                                                  
			if (!PHYS_JUMPSTEP(this))
				if (!oldonground && this.waterlevel == 0)
					return;
		}

		                                            
		                    
		this.origin = start_origin;
		this.velocity = start_velocity;

		          
		vector upmove = '0 0 1' * PHYS_STEPHEIGHT(this);
		if(!_Movetype_PushEntity(this, upmove, true))
		{
			                                                           
			return;
		}

		               
		this.velocity_z = 0;
		clip = _Movetype_FlyMove(this, dt, applygravity, true, 0);
		this.velocity_z += start_velocity.z;
		if (clip & 8)
		{
			                                                           
			                                                                                       
			return;
		}

		_Movetype_CheckVelocity(this);
		_Movetype_LinkEdict(this, true);

		                                                                       
		                        
		if (clip
		    && fabs(originalorigin.y - this.origin.y) < 0.03125
		    && fabs(originalorigin.x - this.origin.x) < 0.03125)
		{
			                        
			                                                                
			this.origin = originalorigin;
			this.velocity = originalvelocity;
			                            
			this.flags = originalflags;
			this.groundentity = originalmove_groundentity;
			                               
			                                      
			return;
		}

		                         

		                                     
		if ((clip & 2) && PHYS_WALLFRICTION(this))
			_Movetype_WallFriction(this, move_stepnormal);
	}
	                                                                                                                               
	else if (!GAMEPLAYFIX_STEPDOWN(this) || this.waterlevel >= 3 || start_velocity.z >= (1.0 / 32.0) 
				|| !oldonground || IS_ONGROUND(this) || (GAMEPLAYFIX_STEPDOWN_MAXSPEED(this) && vdist(start_velocity, >=, GAMEPLAYFIX_STEPDOWN_MAXSPEED(this)) && !IS_ONSLICK(this)))
	{
		return;
	}

	            
	vector downmove = '0 0 0';
	downmove.z = -PHYS_STEPHEIGHT(this) + start_velocity.z * dt;
	if(!_Movetype_PushEntity(this, downmove, true))
	{
		                                                             
		return;
	}

	if (trace_fraction < 1 && trace_plane_normal.z > 0.7)
	{
		                                                                      
		                                                                      
		                                                                     
		                                                     
		if(GAMEPLAYFIX_STEPDOWN(this) == 2)
		{
			SET_ONGROUND(this);
			this.groundentity = trace_ent;
		}
	}
	else
	{
		                         
		                                                                      
		                                                                     
		                                                                  
		this.origin = originalorigin;
		this.velocity = originalvelocity;
		this.flags = originalflags;
		this.groundentity = originalmove_groundentity;
	}

	_Movetype_CheckVelocity(this);
	_Movetype_LinkEdict(this, true);
}
