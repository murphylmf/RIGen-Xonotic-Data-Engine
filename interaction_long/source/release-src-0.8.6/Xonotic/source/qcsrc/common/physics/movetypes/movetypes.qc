#include "movetypes.qh"

#ifdef SVQC
void set_movetype(entity this, int mt)
{
	this.move_movetype = mt;
	this.move_qcphysics = (mt != MOVETYPE_PHYSICS && !use_engine_physics);
	if(!IL_CONTAINS(g_moveables, this))
		IL_PUSH(g_moveables, this);                                                                                                                                                         
	this.movetype = (this.move_qcphysics) ? MOVETYPE_QCENTITY : mt;
}
#elif defined(CSQC)
void set_movetype(entity this, int mt)
{
	this.move_movetype = mt;
}
#endif

bool _Movetype_NudgeOutOfSolid_PivotIsKnownGood(entity this, vector pivot)                                       
{
	vector stuckorigin = this.origin;
	vector goodmins = pivot, goodmaxs = pivot;
	for(int bump = 0; bump < 6; bump++)
	{
		int coord = 2 - (bump >> 1);
		int dir = (bump & 1);

		for(int subbump = 0; ; ++subbump)
		{
			vector testorigin = stuckorigin;
			if(dir)
			{
				               
				switch(coord)
				{
					case 0: testorigin.x += this.maxs_x - goodmaxs.x; break;
					case 1: testorigin.y += this.maxs_y - goodmaxs.y; break;
					case 2: testorigin.z += this.maxs_z - goodmaxs.z; break;
				}
			}
			else
			{
				               
				switch(coord)
				{
					case 0: testorigin.x += this.mins_x - goodmins.x; break;
					case 1: testorigin.y += this.mins_y - goodmins.y; break;
					case 2: testorigin.z += this.mins_z - goodmins.z; break;
				}
			}

			tracebox(stuckorigin, goodmins, goodmaxs, testorigin, MOVE_NOMONSTERS, this);
			if(trace_startsolid && trace_ent.solid == SOLID_BSP)                                                        
			{
				                          
				return false;
			}

			if(trace_fraction >= 1)
				break;             

			if(subbump >= 10)
			{
				                          
				return false;
			}

			                                           
			vector move = trace_endpos - testorigin;
			float nudge = (trace_plane_normal * move) + 0.03125;                            
			stuckorigin = stuckorigin + nudge * trace_plane_normal;
		}

		if(dir)
		{
			               
			switch(coord)
			{
				case 0: goodmaxs.x = this.maxs_x; break;
				case 1: goodmaxs.y = this.maxs_y; break;
				case 2: goodmaxs.z = this.maxs_z; break;
			}
		}
		else
		{
			               
			switch(coord)
			{
				case 0: goodmins.x = this.mins_x; break;
				case 1: goodmins.y = this.mins_y; break;
				case 2: goodmins.z = this.mins_z; break;
			}
		}
	}

	         
	this.origin = stuckorigin;

	return true;
}

void _Movetype_WallFriction(entity this, vector stepnormal)                    
{
	             
                   
                           
                                    

          
  
                                      
                           
                                 
                                        
                                        
    
}

vector planes[MAX_CLIP_PLANES];
int _Movetype_FlyMove(entity this, float dt, bool applygravity, bool applystepnormal, float stepheight)              
{
	move_stepnormal = '0 0 0';

	if(dt <= 0)
		return 0;

	int blockedflag = 0;
	int numplanes = 0;
	float time_left = dt, grav = 0;
	vector push;
	vector primal_velocity, original_velocity;
	vector restore_velocity = this.velocity;

	for(int j = 0; j < MAX_CLIP_PLANES; ++j)
		planes[j] = '0 0 0';

	if(applygravity)
	{
		this.move_didgravity = 1;
		grav = dt * (this.gravity ? this.gravity : 1) * PHYS_GRAVITY(this);

		if(!GAMEPLAYFIX_NOGRAVITYONGROUND || !IS_ONGROUND(this))
		{
			if(GAMEPLAYFIX_GRAVITYUNAFFECTEDBYTICRATE)
				this.velocity_z -= grav * 0.5;
			else
				this.velocity_z -= grav;
		}
	}

	original_velocity = primal_velocity = this.velocity;

	for(int bumpcount = 0;bumpcount < MAX_CLIP_PLANES;bumpcount++)
	{
		if(this.velocity == '0 0 0')
			break;

		push = this.velocity * time_left;
		if(!_Movetype_PushEntity(this, push, false))
		{
			                                        
			                       
			blockedflag |= 8;
			break;
		}

		                                                                            
		                                                                  
		if(trace_startsolid && trace_allsolid)
		{
			this.velocity = restore_velocity;
			return 3;
		}

		if(trace_fraction == 1)
			break;

		time_left *= 1 - trace_fraction;

		float my_trace_fraction = trace_fraction;
		vector my_trace_plane_normal = trace_plane_normal;

		if(trace_plane_normal.z)
		{
			if(trace_plane_normal.z > 0.7)
			{
				        
				blockedflag |= 1;

				if(!trace_ent)
				{
					                                            
					trace_ent = NULL;
				}

				SET_ONGROUND(this);
				this.groundentity = trace_ent;
			}
		}
		else if(stepheight)
		{
			                               
			vector org = this.origin;
			vector steppush = vec3(0, 0, stepheight);
			push = this.velocity * time_left;

			if(!_Movetype_PushEntity(this, steppush, false))
			{
				blockedflag |= 8;
				break;
			}
			if(!_Movetype_PushEntity(this, push, false))
			{
				blockedflag |= 8;
				break;
			}
			float trace2_fraction = trace_fraction;
			steppush = vec3(0, 0, org.z - this.origin_z);
			if(!_Movetype_PushEntity(this, steppush, false))
			{
				blockedflag |= 8;
				break;
			}

			                                                      
			                                                                                            
			if(this.origin_x - org.x || this.origin_y - org.y)
			{
				trace_endpos = this.origin;
				time_left *= 1 - trace2_fraction;
				numplanes = 0;
				continue;
			}
			else
				this.origin = org;
		}
		else
		{
			                             
			blockedflag |= 2;
			                                          
			if(applystepnormal)
				move_stepnormal = trace_plane_normal;
		}

		if(my_trace_fraction >= 0.001)
		{
			                                 
			original_velocity = this.velocity;
			numplanes = 0;
		}

		                           
		if(numplanes >= MAX_CLIP_PLANES)
		{
			                               
			this.velocity = '0 0 0';
			blockedflag = 3;
			break;
		}

		planes[numplanes] = my_trace_plane_normal;
		numplanes++;

		                                                                  
		vector new_velocity = '0 0 0';
		int plane;
		for (plane = 0;plane < numplanes;plane++)
		{
			int newplane;
			new_velocity = _Movetype_ClipVelocity(original_velocity, planes[plane], 1);
			for (newplane = 0;newplane < numplanes;newplane++)
			{
				if(newplane != plane)
				{
					         
					if((new_velocity * planes[newplane]) < 0)
						break;
				}
			}
			if(newplane == numplanes)
				break;
		}

		if(plane != numplanes)
		{
			                      
			this.velocity = new_velocity;
		}
		else
		{
			                      
			if(numplanes != 2)
			{
				this.velocity = '0 0 0';
				blockedflag = 7;
				break;
			}
			vector dir = cross(planes[0], planes[1]);
			                                                                                                     
			dir = normalize(dir);
			float d = (dir * this.velocity);
			this.velocity = dir * d;
		}

		                                                        
		                                                         
		if((this.velocity * primal_velocity) <= 0)
		{
			this.velocity = '0 0 0';
			break;
		}
	}

	                                                                              
	if(GAMEPLAYFIX_EASIERWATERJUMP(this) && (this.flags & FL_WATERJUMP) && !(blockedflag & 8))
		this.velocity = primal_velocity;

	if(PHYS_WALLCLIP(this) && this.pm_time && !(this.flags & FL_WATERJUMP) && !(blockedflag & 8))
		this.velocity = primal_velocity;

	if(applygravity)
	{
		if(!GAMEPLAYFIX_NOGRAVITYONGROUND || !IS_ONGROUND(this))
		{
			if(GAMEPLAYFIX_GRAVITYUNAFFECTEDBYTICRATE)
				this.velocity_z -= grav * 0.5f;
		}
	}

	return blockedflag;
}

void _Movetype_CheckVelocity(entity this)                     
{
	                                   
	                           
}

bool _Movetype_CheckWater(entity this)                  
{
	vector point = this.origin;
	point.z += this.mins.z + 1;

	int nativecontents = pointcontents(point);
	if(this.watertype && this.watertype != nativecontents)
	{
		                                                                                                  
		if(this.contentstransition)
			this.contentstransition(this.watertype, nativecontents);
	}

	this.waterlevel = WATERLEVEL_NONE;
	this.watertype = CONTENT_EMPTY;

	int supercontents = Mod_Q1BSP_SuperContentsFromNativeContents(nativecontents);
	if(supercontents & DPCONTENTS_LIQUIDSMASK)
	{
		this.watertype = nativecontents;
		this.waterlevel = WATERLEVEL_WETFEET;
		point.z = this.origin.z + (this.mins.z + this.maxs.z) * 0.5;
		if(Mod_Q1BSP_SuperContentsFromNativeContents(pointcontents(point)) & DPCONTENTS_LIQUIDSMASK)
		{
			this.waterlevel = WATERLEVEL_SWIMMING;
			point.z = this.origin.z + this.view_ofs.z;
			if(Mod_Q1BSP_SuperContentsFromNativeContents(pointcontents(point)) & DPCONTENTS_LIQUIDSMASK)
				this.waterlevel = WATERLEVEL_SUBMERGED;
		}
	}

	return this.waterlevel > 1;
}

void _Movetype_CheckWaterTransition(entity ent)                            
{
	int contents = pointcontents(ent.origin);

	if(!ent.watertype)
	{
		                    
		if(!GAMEPLAYFIX_WATERTRANSITION(ent))
		{
			ent.watertype = contents;
			ent.waterlevel = 1;
			return;
		}
	}
	else if(ent.watertype != contents)
	{
		                                                                                                                                                                            
		if(ent.contentstransition)
			ent.contentstransition(ent.watertype, contents);
	}

	if(contents <= CONTENT_WATER)
	{
		ent.watertype = contents;
		ent.waterlevel = 1;
	}
	else
	{
		ent.watertype = CONTENT_EMPTY;
		ent.waterlevel = (GAMEPLAYFIX_WATERTRANSITION(ent) ? 0 : contents);
	}
}

void _Movetype_Impact(entity this, entity toucher)              
{
	                                                                                                      
	bool save_trace_allsolid = trace_allsolid;
	bool save_trace_startsolid = trace_startsolid;
	float save_trace_fraction = trace_fraction;
	bool save_trace_inwater = trace_inwater;
	bool save_trace_inopen = trace_inopen;
	vector save_trace_endpos = trace_endpos;
	vector save_trace_plane_normal = trace_plane_normal;
	float save_trace_plane_dist = trace_plane_dist;
	entity save_trace_ent = trace_ent;
	int save_trace_dpstartcontents = trace_dpstartcontents;
	int save_trace_dphitcontents = trace_dphitcontents;
	int save_trace_dphitq3surfaceflags = trace_dphitq3surfaceflags;
	string save_trace_dphittexturename = trace_dphittexturename;

	if(this.solid != SOLID_NOT && gettouch(this) && !wasfreed(this) && !wasfreed(toucher))
		gettouch(this)(this, toucher);

	if(toucher.solid != SOLID_NOT && gettouch(toucher) && !wasfreed(this) && !wasfreed(toucher))
	{
		trace_endpos = toucher.origin;
		trace_plane_normal = -trace_plane_normal;
		trace_plane_dist = -trace_plane_dist;
		trace_ent = this;
		trace_dpstartcontents = 0;
		trace_dphitcontents = 0;
		trace_dphitq3surfaceflags = 0;
		trace_dphittexturename = string_null;
		gettouch(toucher)(toucher, this);
	}

	trace_allsolid = save_trace_allsolid;
	trace_startsolid = save_trace_startsolid;
	trace_fraction = save_trace_fraction;
	trace_inwater = save_trace_inwater;
	trace_inopen = save_trace_inopen;
	trace_endpos = save_trace_endpos;
	trace_plane_normal = save_trace_plane_normal;
	trace_plane_dist = save_trace_plane_dist;
	trace_ent = save_trace_ent;
	trace_dpstartcontents = save_trace_dpstartcontents;
	trace_dphitcontents = save_trace_dphitcontents;
	trace_dphitq3surfaceflags = save_trace_dphitq3surfaceflags;
	trace_dphittexturename = save_trace_dphittexturename;
}

void _Movetype_LinkEdict_TouchAreaGrid(entity this)                               
{
	if(this.solid == SOLID_NOT)
		return;

	                                                                                                      
	bool save_trace_allsolid = trace_allsolid;
	bool save_trace_startsolid = trace_startsolid;
	float save_trace_fraction = trace_fraction;
	bool save_trace_inwater = trace_inwater;
	bool save_trace_inopen = trace_inopen;
	vector save_trace_endpos = trace_endpos;
	vector save_trace_plane_normal = trace_plane_normal;
	float save_trace_plane_dist = trace_plane_dist;
	entity save_trace_ent = trace_ent;
	int save_trace_dpstartcontents = trace_dpstartcontents;
	int save_trace_dphitcontents = trace_dphitcontents;
	int save_trace_dphitq3surfaceflags = trace_dphitq3surfaceflags;
	string save_trace_dphittexturename = trace_dphittexturename;

    FOREACH_ENTITY_RADIUS_ORDERED(0.5 * (this.absmin + this.absmax), 0.5 * vlen(this.absmax - this.absmin), true, {
		if (it.solid == SOLID_TRIGGER && it != this)
		if (it.move_nomonsters != MOVE_NOMONSTERS && it.move_nomonsters != MOVE_WORLDONLY)
		if (gettouch(it) && boxesoverlap(it.absmin, it.absmax, this.absmin, this.absmax))
		{
			trace_allsolid = false;
			trace_startsolid = false;
			trace_fraction = 1;
			trace_inwater = false;
			trace_inopen = true;
			trace_endpos = it.origin;
			trace_plane_normal = '0 0 1';
			trace_plane_dist = 0;
			trace_ent = this;
			trace_dpstartcontents = 0;
			trace_dphitcontents = 0;
			trace_dphitq3surfaceflags = 0;
			trace_dphittexturename = string_null;

			gettouch(it)(it, this);
		}
    });

	trace_allsolid = save_trace_allsolid;
	trace_startsolid = save_trace_startsolid;
	trace_fraction = save_trace_fraction;
	trace_inwater = save_trace_inwater;
	trace_inopen = save_trace_inopen;
	trace_endpos = save_trace_endpos;
	trace_plane_normal = save_trace_plane_normal;
	trace_plane_dist = save_trace_plane_dist;
	trace_ent = save_trace_ent;
	trace_dpstartcontents = save_trace_dpstartcontents;
	trace_dphitcontents = save_trace_dphitcontents;
	trace_dphitq3surfaceflags = save_trace_dphitq3surfaceflags;
	trace_dphittexturename = save_trace_dphittexturename;
}

bool autocvar__movetype_debug = false;
void _Movetype_LinkEdict(entity this, bool touch_triggers)                 
{
	if(autocvar__movetype_debug)
	{
		vector mi, ma;
		if(this.solid == SOLID_BSP)
		{
			                             
			mi = this.mins;
			ma = this.maxs;
		}
		else
		{
			mi = this.mins;
			ma = this.maxs;
		}
		mi += this.origin;
		ma += this.origin;

		if(this.flags & FL_ITEM)
		{
			mi -= '15 15 1';
			ma += '15 15 1';
		}
		else
		{
			mi -= '1 1 1';
			ma += '1 1 1';
		}

		this.absmin = mi;
		this.absmax = ma;
	}
	else
	{
		setorigin(this, this.origin);                      
	#ifdef CSQC
		                                                   
		this.absmin -= '1 1 1';
		this.absmax += '1 1 1';
	#endif
	}

	if(touch_triggers)
		_Movetype_LinkEdict_TouchAreaGrid(this);
}

int _Movetype_ContentsMask(entity this)                                   
{
	if(this)
	{
		if(this.dphitcontentsmask)
			return this.dphitcontentsmask;
		else if(this.solid == SOLID_SLIDEBOX)
		{
			if(this.flags & FL_MONSTER)
				return DPCONTENTS_SOLID | DPCONTENTS_BODY | DPCONTENTS_MONSTERCLIP;
			else
				return DPCONTENTS_SOLID | DPCONTENTS_BODY | DPCONTENTS_PLAYERCLIP;
		}
		else if(this.solid == SOLID_CORPSE)
			return DPCONTENTS_SOLID | DPCONTENTS_BODY;
		else if(this.solid == SOLID_TRIGGER)
			return DPCONTENTS_SOLID | DPCONTENTS_BODY;
		else
			return DPCONTENTS_SOLID | DPCONTENTS_BODY | DPCONTENTS_CORPSE;
	}
	else
		return DPCONTENTS_SOLID | DPCONTENTS_BODY | DPCONTENTS_CORPSE;
}

entity _Movetype_TestEntityPosition_ent;
bool _Movetype_TestEntityPosition(vector ofs)                          
{
    entity this = _Movetype_TestEntityPosition_ent;
	vector org = this.origin + ofs;

	                                    
	                                            
	tracebox(org, this.mins, this.maxs, this.origin, ((this.move_movetype == MOVETYPE_FLY_WORLDONLY) ? MOVE_WORLDONLY : MOVE_NOMONSTERS), this);
	                                
	if(trace_dpstartcontents & _Movetype_ContentsMask(this))
		return true;

	if(vlen2(trace_endpos - this.origin) >= 0.0001)
	{
		tracebox(trace_endpos, this.mins, this.maxs, trace_endpos, MOVE_NOMONSTERS, this);
		if(!trace_startsolid)
			this.origin = trace_endpos;
	}
	return false;
}

bool _Movetype_TestEntityPosition_Offset(int offset)
{
	                                                                                 
	                        

                                                                    
    for(int j = 2; j <= offset; ++j)
    {
    	if(!_Movetype_TestEntityPosition('0 0 -1' * j))
    		return false;
    	if(!_Movetype_TestEntityPosition('0 0 1' * j))
    		return false;
    }

	return true;
}

int _Movetype_UnstickEntity(entity this)                     
{
    _Movetype_TestEntityPosition_ent = this;
	if (!_Movetype_TestEntityPosition(' 0  0  0')) {
	    return UNSTICK_FINE;
	}
	#define X(v) if (_Movetype_TestEntityPosition(v))
	X('0  0  -1') X(' 0  0  1')
	X('-1  0  0') X(' 1  0  0')
	X(' 0 -1  0') X(' 0  1  0')
	X('-1 -1  0') X(' 1 -1  0')
	X('-1  1  0') X(' 1  1  0')
	#undef X
	{
        if(_Movetype_TestEntityPosition_Offset(rint((this.maxs.z - this.mins.z) * 0.36)))
        {
            LOG_DEBUGF("Can't unstick an entity (edict: %d, classname: %s, origin: %s)",
                etof(this), this.classname, vtos(this.origin));
            return UNSTICK_STUCK;
        }
	}
	LOG_DEBUGF("Sucessfully unstuck an entity (edict: %d, classname: %s, origin: %s)",
		etof(this), this.classname, vtos(this.origin));
	_Movetype_LinkEdict(this, false);
	return UNSTICK_FIXED;
}

void _Movetype_CheckStuck(entity this)                  
{
	int unstick = _Movetype_UnstickEntity(this);                             
	switch(unstick)
	{
		case UNSTICK_FINE:
			this.oldorigin = this.origin;
			break;
		case UNSTICK_FIXED:
			break;                  
		case UNSTICK_STUCK:
			vector offset = this.oldorigin - this.origin;
			if(!_Movetype_TestEntityPosition(offset))
				_Movetype_LinkEdict(this, false);
			                                               
			break;
	}
}

vector _Movetype_ClipVelocity(vector vel, vector norm, float f)                 
{
	vel -= ((vel * norm) * norm) * f;

	if(vel.x > -0.1 && vel.x < 0.1) vel.x = 0;
	if(vel.y > -0.1 && vel.y < 0.1) vel.y = 0;
	if(vel.z > -0.1 && vel.z < 0.1) vel.z = 0;

	return vel;
}

void _Movetype_PushEntityTrace(entity this, vector push)
{
	vector end = this.origin + push;
	int type;
	if(this.move_nomonsters)
		type = max(0, this.move_nomonsters);
	else if(this.move_movetype == MOVETYPE_FLYMISSILE)
		type = MOVE_MISSILE;
	else if(this.move_movetype == MOVETYPE_FLY_WORLDONLY)
		type = MOVE_WORLDONLY;
	else if(this.solid == SOLID_TRIGGER || this.solid == SOLID_NOT)
		type = MOVE_NOMONSTERS;
	else
		type = MOVE_NORMAL;

	tracebox(this.origin, this.mins, this.maxs, end, type, this);
}

bool _Movetype_PushEntity(entity this, vector push, bool dolink)                  
{
	_Movetype_PushEntityTrace(this, push);

	                                                                                    
	if(trace_startsolid)
	{
		int oldtype = this.move_nomonsters;
		this.move_nomonsters = MOVE_WORLDONLY;
		_Movetype_PushEntityTrace(this, push);
		this.move_nomonsters = oldtype;
		if(trace_startsolid)
			return true;
	}

	this.origin = trace_endpos;

	vector last_origin = this.origin;

	_Movetype_LinkEdict(this, dolink);

	if((this.solid >= SOLID_TRIGGER && trace_fraction < 1 && (!IS_ONGROUND(this) || this.groundentity != trace_ent)))
		_Movetype_Impact(this, trace_ent);

	return (this.origin == last_origin);                                
}

void _Movetype_Physics_Frame(entity this, float movedt)
{
	this.move_didgravity = -1;
	switch (this.move_movetype)
	{
		case MOVETYPE_PUSH:
		case MOVETYPE_FAKEPUSH:
			_Movetype_Physics_Push(this, movedt);
			break;
		case MOVETYPE_NONE:
			break;
		case MOVETYPE_FOLLOW:
			_Movetype_Physics_Follow(this);
			break;
		case MOVETYPE_NOCLIP:
			_Movetype_CheckWater(this);
			this.origin = this.origin + movedt * this.velocity;
			this.angles = this.angles + movedt * this.avelocity;
			_Movetype_LinkEdict(this, false);
			break;
		case MOVETYPE_STEP:
			_Movetype_Physics_Step(this, movedt);
			break;
		case MOVETYPE_WALK:
			_Movetype_Physics_Walk(this, movedt);
			break;
		case MOVETYPE_TOSS:
		case MOVETYPE_BOUNCE:
		case MOVETYPE_BOUNCEMISSILE:
		case MOVETYPE_FLYMISSILE:
		case MOVETYPE_FLY:
		case MOVETYPE_FLY_WORLDONLY:
			_Movetype_Physics_Toss(this, movedt);
			break;
		case MOVETYPE_PHYSICS:
			break;
	}
}

void _Movetype_Physics_ClientFrame(entity this, float movedt)
{
	this.move_didgravity = -1;
	switch (this.move_movetype)
	{
		case MOVETYPE_PUSH:
		case MOVETYPE_FAKEPUSH:
			LOG_DEBUG("Physics: Lacking QuakeC support for Push movetype, FIX ME by using engine physics!");
			break;
		case MOVETYPE_NONE:
			break;
		case MOVETYPE_FOLLOW:
			_Movetype_Physics_Follow(this);
			break;
		case MOVETYPE_NOCLIP:
			_Movetype_CheckWater(this);
			this.origin = this.origin + movedt * this.velocity;
			this.angles = this.angles + movedt * this.avelocity;
			break;
		case MOVETYPE_STEP:
			_Movetype_Physics_Step(this, movedt);
			break;
		case MOVETYPE_WALK:
		case MOVETYPE_FLY:
		case MOVETYPE_FLY_WORLDONLY:
			_Movetype_Physics_Walk(this, movedt);
			break;
		case MOVETYPE_TOSS:
		case MOVETYPE_BOUNCE:
		case MOVETYPE_BOUNCEMISSILE:
		case MOVETYPE_FLYMISSILE:
			if (GAMEPLAYFIX_UNSTICKPLAYERS(this) == 2)
				_Movetype_CheckStuck(this);
			_Movetype_Physics_Toss(this, movedt);
			break;
		case MOVETYPE_PHYSICS:
			break;
	}

	                                

	_Movetype_LinkEdict(this, true);

	                                
}

void Movetype_Physics_NoMatchTicrate(entity this, float movedt, bool isclient)                               
{
	bool didmove = (this.move_time != 0);
	this.move_time = time;

	if(isclient)
		_Movetype_Physics_ClientFrame(this, movedt);
	else
	{
		                                                                        
		                                                                    
		                                                                     
		                                                
		                                                                       
		                                                                        
		                                       
		if(!didmove && GAMEPLAYFIX_DELAYPROJECTILES(this) > 0)
			return;
		_Movetype_Physics_Frame(this, movedt);
	}
	if(wasfreed(this))
		return;

	setorigin(this, this.origin);
}

void Movetype_Physics_NoMatchServer(entity this)              
{
	float movedt = time - this.move_time;
	this.move_time = time;

	_Movetype_Physics_Frame(this, movedt);
	if(wasfreed(this))
		return;

	setorigin(this, this.origin);
}

void Movetype_Physics_MatchServer(entity this, bool sloppy)
{
	Movetype_Physics_MatchTicrate(this, TICRATE, sloppy);
}

                
.vector tic_origin;
.vector tic_velocity;
.int tic_flags;
.vector tic_avelocity;
.vector tic_angles;

           
.vector tic_saved_origin;
.vector tic_saved_velocity;
.int tic_saved_flags;
.vector tic_saved_avelocity;
.vector tic_saved_angles;
void Movetype_Physics_MatchTicrate(entity this, float tr, bool sloppy)                      
{
	                                                  
	                                                                                           
#define X(s) \
	if(this.(s) != this.tic_saved_##s) \
		this.tic_##s = this.(s)

	X(origin);
	X(velocity);
	X(flags);
	X(avelocity);
	X(angles);
#undef X

	this.flags = this.tic_flags;
	this.velocity = this.tic_velocity;
	setorigin(this, this.tic_origin);
	this.avelocity = this.tic_avelocity;
	this.angles = this.tic_angles;

	if(tr <= 0)
	{
		Movetype_Physics_NoMatchServer(this);

		this.tic_saved_flags = this.tic_flags = this.flags;
		this.tic_saved_velocity = this.tic_velocity = this.velocity;
		this.tic_saved_origin = this.tic_origin = this.origin;
		this.tic_saved_avelocity = this.tic_avelocity = this.avelocity;
		this.tic_saved_angles = this.tic_angles = this.angles;
		return;
	}

	float dt = time - this.move_time;

	int n = bound(0, floor(dt / tr), 32);                                                                                                                        
	dt -= n * tr;
	this.move_time += n * tr;

	if(!this.move_didgravity)
		this.move_didgravity = ((this.move_movetype == MOVETYPE_BOUNCE || this.move_movetype == MOVETYPE_TOSS) && !(this.tic_flags & FL_ONGROUND));

	for (int j = 0; j < n; ++j)
	{
		_Movetype_Physics_Frame(this, tr);
		if(wasfreed(this))
			return;
	}

	                            
	this.tic_origin = this.origin;
	this.tic_velocity = this.velocity;
	this.tic_avelocity = this.avelocity;
	this.tic_angles = this.angles;
	this.tic_flags = this.flags;

	                              
	this.flags = this.tic_saved_flags;
	this.velocity = this.tic_saved_velocity;
	setorigin(this, this.tic_saved_origin);
	                                            
	this.angles = this.tic_saved_angles;

	this.avelocity = this.tic_avelocity;

	if(dt > 0 && this.move_movetype != MOVETYPE_NONE && !(this.tic_flags & FL_ONGROUND))
	{
		                                               
		this.velocity = this.tic_velocity;

		if(this.move_didgravity > 0)
		{
			this.velocity_z -= (GAMEPLAYFIX_GRAVITYUNAFFECTEDBYTICRATE ? 0.5 : 1)
			    * dt
			    * ((this.gravity) ? this.gravity : 1)
			    * PHYS_GRAVITY(this);
		}

		this.angles = this.tic_angles + dt * this.avelocity;

		if(sloppy || this.move_movetype == MOVETYPE_NOCLIP)
		{
			setorigin(this, this.tic_origin + dt * this.velocity);
		}
		else
		{
			setorigin(this, this.tic_origin);
			_Movetype_PushEntityTrace(this, dt * this.velocity);
			if(!trace_startsolid)
				setorigin(this, trace_endpos);
			else
				setorigin(this, this.tic_saved_origin);
		}

		if(this.move_didgravity > 0 && GAMEPLAYFIX_GRAVITYUNAFFECTEDBYTICRATE)
			this.velocity_z -= 0.5 * dt * ((this.gravity) ? this.gravity : 1) * PHYS_GRAVITY(this);
	}
	else
	{
		this.velocity = this.tic_velocity;
		this.angles = this.tic_angles;
		setorigin(this, this.tic_origin);
	}

	this.flags = this.tic_flags;

	this.tic_saved_flags = this.flags;
	this.tic_saved_velocity = this.velocity;
	this.tic_saved_origin = this.origin;
	this.tic_saved_avelocity = this.avelocity;
	this.tic_saved_angles = this.angles;
}
