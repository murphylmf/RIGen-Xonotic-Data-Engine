#include "push.qh"

void _Movetype_PushMove(entity this, float dt)               
{
	if(this.velocity == '0 0 0' && this.avelocity == '0 0 0')
	{
		this.ltime += dt;
		return;
	}

	switch(this.solid)
	{
		                                
		case SOLID_BSP:
		case SOLID_BBOX:
		case SOLID_SLIDEBOX:
		case SOLID_CORPSE:                                     
			break;
		                           
		case SOLID_NOT:
		case SOLID_TRIGGER:
		{
			this.origin = this.origin + dt * this.velocity;
			this.angles = this.angles + dt * this.avelocity;
			this.angles_x -= 360.0 * floor(this.angles_x * (1.0 / 360.0));
			this.angles_y -= 360.0 * floor(this.angles_y * (1.0 / 360.0));
			this.angles_z -= 360.0 * floor(this.angles_z * (1.0 / 360.0));
			this.ltime += dt;
			_Movetype_LinkEdict(this, false);
			return;
		}
		default:
		{
			LOG_INFOF("_Movetype_Physics_Push: entity #%d, unrecognized solid type %d", etof(this), this.solid);
			return;
		}
	}
	if(!this.modelindex)
	{
		LOG_INFOF("_Movetype_Physics_Push: entity #%d has an invalid modelindex %d", etof(this), this.modelindex);
		return;
	}

	bool rotated = ((vlen2(this.angles) + vlen2(this.avelocity)) > 0);

	vector move1 = this.velocity * dt;
	vector moveangle = this.avelocity * dt;

	vector a = -moveangle;
	vector forward, left, up;
	MAKE_VECTORS(a, forward, left, up);
	left *= -1;                          

	vector pushorig = this.origin;
	vector pushang = this.angles;
	float pushltime = this.ltime;

	                                        

	this.origin = this.origin + dt * this.velocity;
	this.angles = this.angles + dt * this.avelocity;
	this.ltime += dt;
	_Movetype_LinkEdict(this, false);                                       

	if(this.move_movetype == MOVETYPE_FAKEPUSH)                                                         
	{
		this.angles_x -= 360.0 * floor(this.angles_x * (1.0 / 360.0));
		this.angles_y -= 360.0 * floor(this.angles_y * (1.0 / 360.0));
		this.angles_z -= 360.0 * floor(this.angles_z * (1.0 / 360.0));
		return;
	}

	IL_CLEAR(g_pushmove_moved);                                        

	for(entity check = findradius((this.absmin + this.absmax) * 0.5, vlen(this.absmax - this.absmin) * 0.5 + 1); check; check = check.chain)
	{
		switch(check.move_movetype)
		{
			case MOVETYPE_NONE:
			case MOVETYPE_PUSH:
			case MOVETYPE_FOLLOW:
			case MOVETYPE_NOCLIP:
			case MOVETYPE_FLY_WORLDONLY:
				continue;
			default:
				break;
		}

		if(check.owner == this || this.owner == check)
			continue;

		                                                                       
		                                                                      
		                          
		if (!IS_ONGROUND(check) || check.groundentity != this)
		{
			tracebox(check.origin, check.mins, check.maxs, check.origin, MOVE_NOMONSTERS, check);
			if(!trace_startsolid)
				continue;
		}
		vector pivot = check.mins + 0.5 * (check.maxs - check.mins);
		vector move;

		if(rotated)
		{
			vector org = check.origin - this.origin;
			org = org + pivot;

			vector org2;
			org2.x = (org * forward);
			org2.y = (org * left);
			org2.z = (org * up);
			move = org2 - org;
			move = move + move1;
		}
		else
			move = move1;

		check.moved_from = check.origin;
		check.moved_fromangles = check.angles;
		IL_PUSH(g_pushmove_moved, check);

		                                                               
		if(check.move_movetype == MOVETYPE_PHYSICS)
		{
			check.origin = check.origin + move;
			_Movetype_LinkEdict(check, true);
			continue;
		}

		                                  
		int savesolid = this.solid;
		this.solid = SOLID_NOT;
		if(!_Movetype_PushEntity(check, move, true))
		{
			                                
			check.angles_y += trace_fraction * moveangle.y;
			this.solid = savesolid;
			continue;                 
		}
		                                
		check.angles_y += trace_fraction * moveangle.y;
		this.solid = savesolid;

		                                                                    
		                                       
		                                                            
		if(check.move_movetype != MOVETYPE_WALK && (trace_fraction < 1 || check.groundentity != this))
			UNSET_ONGROUND(check);

		                                          
		tracebox(check.origin, check.mins, check.maxs, check.origin, MOVE_NOMONSTERS, check);
		if(trace_startsolid)
		{
			if(_Movetype_NudgeOutOfSolid_PivotIsKnownGood(check, pivot))
			{
				                                                 
				_Movetype_PushEntity(check, '0 0 0', true);
				                                                  
				continue;
			}

			                                              

			                
			if(check.mins_x == check.maxs_x)
				continue;
			if(check.solid == SOLID_NOT || check.solid == SOLID_TRIGGER)
			{
				         
				check.mins_x = check.mins_y = 0;
				check.maxs = check.mins;
				continue;
			}

			this.origin = pushorig;
			this.angles = pushang;
			this.ltime = pushltime;
			_Movetype_LinkEdict(this, false);

			                                          
			IL_EACH(g_pushmove_moved, true,
			{
				check.origin = check.moved_from;
				check.angles = check.moved_fromangles;
				_Movetype_LinkEdict(check, false);
			});

			                                                                                                           
			if(getblocked(this))
				getblocked(this)(this, check);
			break;
		}
	}
	this.angles_x -= 360.0 * floor(this.angles_x * (1.0 / 360.0));
	this.angles_y -= 360.0 * floor(this.angles_y * (1.0 / 360.0));
	this.angles_z -= 360.0 * floor(this.angles_z * (1.0 / 360.0));
	IL_CLEAR(g_pushmove_moved);            
}

void _Movetype_Physics_Push(entity this, float dt)                     
{
	float oldltime = this.ltime;
	float movetime = dt;
	if(this.nextthink < this.ltime + dt)
	{
		movetime = this.nextthink - this.ltime;
		if(movetime < 0)
			movetime = 0;
	}

	if(movetime)
	{
		                                     
		_Movetype_PushMove(this, movetime);
	}

	if(this.nextthink > oldltime && this.nextthink <= this.ltime)
	{
		this.nextthink = 0;
		getthink(this)(this);
	}
}
