  
                                   
                                      
  
                                                                               
                                                                           
                                                                             
                                                                              
                                                                             
                                                           
  
                                                                             
                                                      
  
                                                                             
                                                                           
                                                                              
                                                                         
                                                                          
                                                                               
                   
   
#include "cl_player.qh"

#include "cl_model.qh"
#include "common.qh"
#include "interpolate.qh"

float autocvar_cl_movement_errorcompensation = 0;
bool autocvar_cl_movement_intermissionrunning = false;

               
float pmove_onground;                                                                 

vector csqcplayer_origin, csqcplayer_velocity;
float csqcplayer_sequence;
int player_pmflags;
float csqcplayer_moveframe;
vector csqcplayer_predictionerroro;
vector csqcplayer_predictionerrorv;
float csqcplayer_predictionerrortime;
float csqcplayer_predictionerrorfactor;

vector CSQCPlayer_GetPredictionErrorO()
{
	if (time >= csqcplayer_predictionerrortime) return '0 0 0';
	return csqcplayer_predictionerroro * (csqcplayer_predictionerrortime - time) * csqcplayer_predictionerrorfactor;
}

vector CSQCPlayer_GetPredictionErrorV()
{
	if (time >= csqcplayer_predictionerrortime) return '0 0 0';
	return csqcplayer_predictionerrorv * (csqcplayer_predictionerrortime - time) * csqcplayer_predictionerrorfactor;
}

void CSQCPlayer_SetPredictionError(vector o, vector v, float onground_diff)
{
	                                                             
	                                                              
	             

	                                                                                      
	  
                                          
                  
  
                                                                   
         
  
   
	if(vdist(o, >, 32) || vdist(v, >, 192))
	{
		                                       
		return;
	}

	if(!autocvar_cl_movement_errorcompensation)
	{
		csqcplayer_predictionerrorfactor = 0;
		return;
	}

	csqcplayer_predictionerroro = CSQCPlayer_GetPredictionErrorO() + o;
	csqcplayer_predictionerrorv = CSQCPlayer_GetPredictionErrorV() + v;
	csqcplayer_predictionerrorfactor = autocvar_cl_movement_errorcompensation / ((ticrate) ? ticrate : 1);
	csqcplayer_predictionerrortime = time + 1.0 / csqcplayer_predictionerrorfactor;
}

void CSQCPlayer_Unpredict(entity this)
{
	if (csqcplayer_status == CSQCPLAYERSTATUS_UNPREDICTED) return;
	if (csqcplayer_status != CSQCPLAYERSTATUS_PREDICTED) LOG_FATALF("Cannot unpredict in current status (%d)", csqcplayer_status);
	this.origin = csqcplayer_origin;
	this.velocity = csqcplayer_velocity;
	csqcplayer_moveframe = csqcplayer_sequence + 1;                                                                          
	this.flags = player_pmflags;
}

void CSQCPlayer_SetMinsMaxs(entity this)
{
	if (IS_DUCKED(this) || !(this.isplayermodel & ISPLAYER_PLAYER))
	{
		this.mins = PHYS_PL_CROUCH_MIN(this);
		this.maxs = PHYS_PL_CROUCH_MAX(this);
		this.view_ofs = PHYS_PL_CROUCH_VIEWOFS(this);
	}
	else
	{
		this.mins = PHYS_PL_MIN(this);
		this.maxs = PHYS_PL_MAX(this);
		if (IS_DEAD(this))
			this.maxs.z = 5;
		this.view_ofs = PHYS_PL_VIEWOFS(this);
	}
}

void CSQCPlayer_SavePrediction(entity this)
{
	player_pmflags = this.flags;
	csqcplayer_origin = this.origin;
	csqcplayer_velocity = this.velocity;
	csqcplayer_sequence = servercommandframe;
	csqcplayer_status = CSQCPLAYERSTATUS_PREDICTED;
}

void CSQC_ClientMovement_PlayerMove_Frame(entity this);

void CSQCPlayer_Physics(entity this)
{
	if(!autocvar_cl_movement) { return; }

	                                                                                                                     

	vector oldv_angle = this.v_angle;
	vector oldangles = this.angles;                                                          
	this.v_angle = PHYS_INPUT_ANGLES(this);
	this.angles = PHYS_WORLD_ANGLES(this);

	CSQC_ClientMovement_PlayerMove_Frame(this);

	Movetype_Physics_NoMatchTicrate(this, PHYS_INPUT_TIMELENGTH, true);

	view_angles = this.v_angle;
	input_angles = this.angles;
	this.v_angle = oldv_angle;
	this.angles = oldangles;

	this.pmove_flags =
			((IS_DUCKED(this)) ? PMF_DUCKED : 0) |
			((IS_JUMP_HELD(this)) ? PMF_JUMP_HELD : 0) |
			((IS_ONGROUND(this)) ? PMF_ONGROUND : 0);
}

void CSQCPlayer_PredictTo(entity this, float endframe, bool apply_error)
{
	CSQCPlayer_Unpredict(this);
	if (apply_error)
	{
		this.origin += CSQCPlayer_GetPredictionErrorO();
		this.velocity += CSQCPlayer_GetPredictionErrorV();
	}
	CSQCPlayer_SetMinsMaxs(this);

	csqcplayer_status = CSQCPLAYERSTATUS_PREDICTED;

#if 0
	                     
	                                                                 
	if (STAT(HEALTH) <= 0)
	{
		csqcplayer_moveframe = clientcommandframe;
		getinputstate(csqcplayer_moveframe-1);
		LOG_INFO("the Weird code path got hit");
		return;
	}
#endif

	if (csqcplayer_moveframe >= endframe)
	{
		getinputstate(csqcplayer_moveframe - 1);
	}
	else
	{
		do
		{
			if (!getinputstate(csqcplayer_moveframe)) break;
			                                
    
                                
     
                           
                              
     
                             
      
			CSQCPlayer_Physics(this);
			CSQCPlayer_SetMinsMaxs(this);
			++csqcplayer_moveframe;
		}
		while (csqcplayer_moveframe < endframe);
	}

	                                                                         
	input_angles = view_angles;
}

bool CSQCPlayer_IsLocalPlayer(entity this)
{
	return (this == csqcplayer);
}

float stairsmoothz;
float autocvar_cl_stairsmoothspeed = 200;
float autocvar_cl_smoothviewheight = 0.05;
float smooth_prevtime;
float viewheightavg;
vector CSQCPlayer_ApplySmoothing(entity this, vector v)
{
	float smoothtime = bound(0, time - smooth_prevtime, 0.1);
	smooth_prevtime = max(smooth_prevtime, drawtime);                                                       

	if(this.csqcmodel_teleported || !(this.pmove_flags & PMF_ONGROUND) || autocvar_cl_stairsmoothspeed <= 0 || this.ground_networkentity)
		stairsmoothz = v.z;
	else
	{
		if(stairsmoothz < v.z)
			v.z = stairsmoothz = bound(v.z - PHYS_STEPHEIGHT(this), stairsmoothz + smoothtime * autocvar_cl_stairsmoothspeed, v.z);
		else if(stairsmoothz > v.z)
			v.z = stairsmoothz = bound(v.z, stairsmoothz - smoothtime * autocvar_cl_stairsmoothspeed, v.z + PHYS_STEPHEIGHT(this));
	}

	float viewheight = bound(0, (time - smooth_prevtime) / max(0.0001, autocvar_cl_smoothviewheight), 1);
	viewheightavg = viewheightavg * (1 - viewheight) + this.view_ofs.z * viewheight;
	v.z += viewheightavg;

	smooth_prevtime = time;

	return v;
}

                                                                        
.float stairsmooth_offset;
.float stairsmooth_prevtime;
.float stairsmooth_drawtime;                                
vector CSQCModel_ApplyStairSmoothing(entity this, bool isonground, vector v)
{
	float smoothtime = bound(0, time - this.stairsmooth_prevtime, 0.1);
	this.stairsmooth_prevtime = max(this.stairsmooth_prevtime, this.stairsmooth_drawtime);                                                                   

	if(this.csqcmodel_teleported || !isonground || autocvar_cl_stairsmoothspeed <= 0 || this.ground_networkentity)
		this.stairsmooth_offset = v.z;
	else
	{
		if(this.stairsmooth_offset < v.z)
			v.z = this.stairsmooth_offset = bound(v.z - PHYS_STEPHEIGHT(this), this.stairsmooth_offset + smoothtime * autocvar_cl_stairsmoothspeed, v.z);
		else if(this.stairsmooth_offset > v.z)
			v.z = this.stairsmooth_offset = bound(v.z, this.stairsmooth_offset - smoothtime * autocvar_cl_stairsmoothspeed, v.z + PHYS_STEPHEIGHT(this));
	}

	this.stairsmooth_prevtime = time;
	this.stairsmooth_drawtime = drawtime;

	return v;
}

bool autocvar_v_deathtilt;
float autocvar_v_deathtiltangle;
void CSQCPlayer_ApplyDeathTilt(entity this)
{
	if(!this.csqcmodel_isdead || !autocvar_v_deathtilt)
		return;
	                                                                                         
	                                                                   
	if (autocvar_cl_eventchase_death == 2 && this.csqcmodel_isdead)
		return;
	view_angles.z += min((time - this.death_time) * 8, 1) * autocvar_v_deathtiltangle;
}

float autocvar_v_idlescale;
float autocvar_v_ipitch_cycle;
float autocvar_v_iyaw_cycle;
float autocvar_v_iroll_cycle;
float autocvar_v_ipitch_level;
float autocvar_v_iyaw_level;
float autocvar_v_iroll_level;
void CSQCPlayer_ApplyIdleScaling(entity this)
{
	if(!autocvar_v_idlescale)
		return;
	view_angles.x += autocvar_v_idlescale * sin(time * autocvar_v_ipitch_cycle) * autocvar_v_ipitch_level;
	view_angles.y += autocvar_v_idlescale * sin(time * autocvar_v_iyaw_cycle) * autocvar_v_iyaw_level;
	view_angles.z += autocvar_v_idlescale * sin(time * autocvar_v_iroll_cycle) * autocvar_v_iroll_level;
	                                                                                         
}

float autocvar_cl_bob = 0;
float autocvar_cl_bobcycle = 0.5;
float autocvar_cl_bob_limit = 7;
float autocvar_cl_bob_limit_heightcheck = 0;
float autocvar_cl_bob_velocity_limit = 400;
float autocvar_cl_bobup = 0.5;
float autocvar_cl_bobfall = 0.05;
float autocvar_cl_bobfallcycle = 3;
float autocvar_cl_bobfallminspeed = 200;
float autocvar_cl_bob2 = 0;
float autocvar_cl_bob2cycle = 1;
float autocvar_cl_bob2smooth = 0.05;
float bobfall_swing;
float bobfall_speed;
float bob2_smooth;
vector CSQCPlayer_ApplyBobbing(entity this, vector v)
{
	if(this.csqcmodel_isdead || PHYS_INVEHICLE(this) || !(this.isplayermodel & ISPLAYER_PLAYER))
		return v;

	                                                  
	float bob, cycle;

	                             
	if(autocvar_cl_bob && autocvar_cl_bobcycle)
	{
		float bob_limit = autocvar_cl_bob_limit;

		if(autocvar_cl_bob_limit_heightcheck)
		{
			                                                                                           
			vector bob_height_check_dest = v;
			bob_height_check_dest.z += autocvar_cl_bob_limit * 1.1;
			traceline(v, bob_height_check_dest, MOVE_NOMONSTERS, NULL);
			float trace1fraction = trace_fraction;

			bob_height_check_dest = v;
			bob_height_check_dest.z += autocvar_cl_bob_limit * -0.5;
			traceline(v, bob_height_check_dest, MOVE_NOMONSTERS, NULL);
			float trace2fraction = trace_fraction;

			bob_limit *= min(trace1fraction, trace2fraction);
		}

		                                                                    
		                                                                     
		cycle = time / autocvar_cl_bobcycle;
		cycle -= rint(cycle);
		if(cycle < autocvar_cl_bobup)
			cycle = sin(M_PI * cycle / autocvar_cl_bobup);
		else
			cycle = sin(M_PI + M_PI * (cycle - autocvar_cl_bobup) / (1.0 - autocvar_cl_bobup));
		                                                  
		                                           
		float xyspeed = bound(0, sqrt(this.velocity.x * this.velocity.x + this.velocity.y * this.velocity.y), autocvar_cl_bob_velocity_limit);
		bob = xyspeed * autocvar_cl_bob;
		bob = bound(0, bob, bob_limit);
		bob = bob * 0.3 + bob * 0.7 * cycle;
		v.z += bob;
	}

	                               
	if(autocvar_cl_bob2 && autocvar_cl_bob2cycle)
	{
		cycle = time / autocvar_cl_bob2cycle;
		cycle -= rint(cycle);
		if(cycle < 0.5)
			cycle = cos(M_PI * cycle / 0.5);                                                               
		else
			cycle = cos(M_PI + M_PI * (cycle - 0.5) / 0.5);
		bob = autocvar_cl_bob2 * cycle;

		                                                                            
		                                                                           
		if(IS_ONGROUND(this) && !(input_buttons & BIT(1)))                                                                                                
			bob2_smooth = 1;
		else
		{
			if(bob2_smooth > 0)
				bob2_smooth -= bound(0, autocvar_cl_bob2smooth, 1);
			else
				bob2_smooth = 0;
		}

		                                                                      
		makevectors(view_angles);
		                                                                                               
		float side = bound(-autocvar_cl_bob_velocity_limit, (this.velocity * v_right) * bob2_smooth, autocvar_cl_bob_velocity_limit);
		float front = bound(-autocvar_cl_bob_velocity_limit, (this.velocity * v_forward) * bob2_smooth, autocvar_cl_bob_velocity_limit);
		v_forward = v_forward * bob;
		v_right = v_right * bob;
		                                                                     
		                                                                   
		vector bob2vel;
		bob2vel.x = side * v_forward.x + front * v_right.x + 0 * v_up.x;
		bob2vel.y = side * v_forward.y + front * v_right.y + 0 * v_up.y;
		bob2vel.z = side * v_forward.z + front * v_right.z + 0 * v_up.z;
		v.x += bob2vel.x;
		v.y += bob2vel.y;
	}

	                    
	                                                                     
	if(autocvar_cl_bobfall && autocvar_cl_bobfallcycle)
	{
		if(!IS_ONGROUND(this))
		{
			bobfall_speed = bound(-400, this.velocity.z, 0) * bound(0, autocvar_cl_bobfall, 0.1);
			if(this.velocity.z < -autocvar_cl_bobfallminspeed)
				bobfall_swing = 1;
			else
				bobfall_swing = 0;           
		}
		else
		{
			bobfall_swing = max(0, bobfall_swing - autocvar_cl_bobfallcycle * frametime);
			float bobfall = sin(M_PI * bobfall_swing) * bobfall_speed;
			v.z += bobfall;
		}
	}

	return v;
}

float autocvar_cl_rollangle;
float autocvar_cl_rollspeed;
float CSQCPlayer_CalcRoll(entity this)
{
	if (!autocvar_cl_rollangle) return 0;

	makevectors(view_angles);
	float side = (this.velocity * v_right);
	float sign = (side < 0) ? -1 : 1;
	side = fabs(side);

	if(side < autocvar_cl_rollspeed)
		side = side * autocvar_cl_rollangle / autocvar_cl_rollspeed;
	else
		side = autocvar_cl_rollangle;

	return side * sign;
}

float autocvar_chase_back;
float autocvar_chase_up;
bool autocvar_chase_overhead;
float autocvar_chase_pitchangle;
vector CSQCPlayer_ApplyChase(entity this, vector v)
{
	vector forward;
	vector chase_dest;

	if(autocvar_chase_overhead)
	{
		view_angles.x = 0;
		makevectors(view_angles);
		forward = v_forward;
		vector up = v_up;
		                                                                                                               
		chase_dest.x = v.x - forward.x * autocvar_chase_back + up.x * autocvar_chase_up;
		chase_dest.y = v.y - forward.y * autocvar_chase_back + up.y * autocvar_chase_up;
		chase_dest.z = v.z - forward.z * autocvar_chase_back + up.z * autocvar_chase_up;

		                                                                                 
		traceline(v, chase_dest, MOVE_NOMONSTERS, NULL);

		vector bestvieworg = trace_endpos;
		vector offset = '0 0 0';
		for(offset.x = -16; offset.x <= 16; offset.x += 8)
		{
			for(offset.y = -16; offset.y <= 16; offset.y += 8)
			{
				makevectors(view_angles);
				up = v_up;
				chase_dest.x = v.x - forward.x * autocvar_chase_back + up.x * autocvar_chase_up + offset.x;
				chase_dest.y = v.y - forward.y * autocvar_chase_back + up.y * autocvar_chase_up + offset.y;
				chase_dest.z = v.z - forward.z * autocvar_chase_back + up.z * autocvar_chase_up + offset.z;
				traceline(v, chase_dest, MOVE_NOMONSTERS, NULL);
				if(bestvieworg.z > trace_endpos.z)
					bestvieworg.z = trace_endpos.z;
			}
		}
		bestvieworg.z -= 8;
		v = bestvieworg;

		view_angles.x = autocvar_chase_pitchangle;
		                                                                                         
	}
	else
	{
		makevectors(view_angles);
		forward = v_forward;
		if(autocvar_chase_front && spectatee_status != -1)
			forward = normalize(forward * -1);
		                                                                                                               
		float cdist = -autocvar_chase_back - 8;
		chase_dest.x = v.x + forward.x * cdist;
		chase_dest.y = v.y + forward.y * cdist;
		chase_dest.z = v.z + forward.z * cdist + autocvar_chase_up;
		if (this.move_movetype == MOVETYPE_NOCLIP)
		{
			                                      
			trace_endpos = chase_dest;
			trace_plane_normal = '0 0 0';
		}
		else
		{
			traceline(v, chase_dest, MOVE_NOMONSTERS, NULL);
		}
		v.x = 1 * trace_endpos.x + 8 * forward.x + 4 * trace_plane_normal.x;
		v.y = 1 * trace_endpos.y + 8 * forward.y + 4 * trace_plane_normal.y;
		v.z = 1 * trace_endpos.z + 8 * forward.z + 4 * trace_plane_normal.z;

		if(autocvar_chase_front && spectatee_status != -1)
		{
			                                                           
			vector newang = vectoangles(forward);
			view_angles.x = view_angles.x * -1;                                     
			view_angles.y = newang.y;
		}
	}

#if 0
	tracebox(v, '-4 -4 -4', '4 4 4', v - v_forward * autocvar_chase_back, MOVE_NORMAL, this);
	v = trace_endpos;
	tracebox(v, '-4 -4 -4', '4 4 4', v + v_up * autocvar_chase_up, MOVE_NORMAL, this);
	v = trace_endpos;
#endif
	return v;
}

void CSQCPlayer_CalcRefdef(entity this)
{
	if(use_engine_refdef)
	{
		int refdefflags = 0;
		if (this.csqcmodel_teleported) refdefflags |= REFDEFFLAG_TELEPORTED;
		if (input_buttons & BIT(1)) refdefflags |= REFDEFFLAG_JUMPING;
		                                                              
		if (PHYS_HEALTH(NULL) <= 0 && PHYS_HEALTH(NULL) != -666 && PHYS_HEALTH(NULL) != -2342) refdefflags |= REFDEFFLAG_DEAD;
		if (intermission) refdefflags |= REFDEFFLAG_INTERMISSION;
		V_CalcRefdef(this, refdefflags);                                                                                     
		return;
	}

	vector vieworg = this.origin;
	if(intermission)
	{
		                                                          
		vieworg.z += this.view_ofs.z;
	}
	else
	{
		vieworg = CSQCPlayer_ApplySmoothing(this, vieworg);
		if(autocvar_chase_active)
			vieworg = CSQCPlayer_ApplyChase(this, vieworg);
		else
		{
			         
			CSQCPlayer_ApplyDeathTilt(this);
			view_angles = view_angles + view_punchangle;
			view_angles.z += CSQCPlayer_CalcRoll(this);
			                                                  
			         
			vieworg = vieworg + view_punchvector;
			vieworg = CSQCPlayer_ApplyBobbing(this, vieworg);
		}
		CSQCPlayer_ApplyIdleScaling(this);
	}
	setproperty(VF_ORIGIN, vieworg);
	setproperty(VF_ANGLES, view_angles);
}

                                        
void CSQCPlayer_SetCamera()
{
	vector v0 = ((intermission && !autocvar_cl_movement_intermissionrunning) ? '0 0 0' : pmove_vel);                                                                                       
	float vh = PHYS_VIEWHEIGHT(NULL);
	vector pl_viewofs = PHYS_PL_VIEWOFS(NULL);
	vector pl_viewofs_crouch = PHYS_PL_CROUCH_VIEWOFS(NULL);
	entity e = csqcplayer;
	if (e)
	{
		if (servercommandframe == 0 || clientcommandframe == 0)
		{
			InterpolateOrigin_Do(e);
			e.view_ofs = '0 0 1' * vh;

			                                   
			if (vh == pl_viewofs.z) e.flags &= ~FL_DUCKED;
			else if (vh == pl_viewofs_crouch.z) e.flags |= FL_DUCKED;

			                                     
			e.flags = BITSET(e.flags, FL_ONGROUND, pmove_onground);

			CSQCPlayer_SetMinsMaxs(e);

			                                
			e.view_ofs = '0 0 1' * vh;

			               
			e.velocity = v0;
		}
		else
		{
			int flg = e.iflags; e.iflags &= ~(IFLAG_ORIGIN | IFLAG_ANGLES);
			InterpolateOrigin_Do(e);
			e.iflags = flg;

			if (csqcplayer_status == CSQCPLAYERSTATUS_FROMSERVER)
			{
				vector o = e.origin;
				csqcplayer_status = CSQCPLAYERSTATUS_PREDICTED;
				CSQCPlayer_PredictTo(e, servercommandframe + 1, false);
				CSQCPlayer_SetPredictionError(e.origin - o, e.velocity - v0, pmove_onground - IS_ONGROUND(e));
				e.origin = o;
				e.velocity = v0;

				                                   
				if (vh == pl_viewofs.z) e.flags &= ~FL_DUCKED;
				else if(vh == pl_viewofs_crouch.z) e.flags |= FL_DUCKED;

				                                     
				e.flags = BITSET(e.flags, FL_ONGROUND, pmove_onground);

				CSQCPlayer_SavePrediction(e);
			}
			CSQCPlayer_PredictTo(e, clientcommandframe + 1, true);

#ifdef CSQCMODEL_SERVERSIDE_CROUCH
			                                         
			if (vh == pl_viewofs.z) e.flags &= ~FL_DUCKED;
			else if (vh == pl_viewofs_crouch.z) e.flags |= FL_DUCKED;
#endif
			CSQCPlayer_SetMinsMaxs(e);

			if (!IS_DEAD(e))
				e.angles.y = input_angles.y;
		}

		         
		e.stairsmooth_drawtime = drawtime;                                                                                                    
		e.origin = CSQCModel_ApplyStairSmoothing(e, (e.pmove_flags & PMF_ONGROUND), e.origin);
		setorigin(e, e.origin);
	}

	const entity view = CSQCModel_server2csqc(player_localentnum - 1);
	if (view)
	{
		if (view != csqcplayer)
		{
			InterpolateOrigin_Do(view);
			view.view_ofs = '0 0 1' * vh;
		}
		CSQCPlayer_CalcRefdef(view);
	}
	else
	{
		                                         
		                          
		  
                                                   
                                      
    
	}
	CSQCPLAYER_HOOK_POSTCAMERASETUP();
}

void CSQCPlayer_Remove(entity this)
{
	csqcplayer = NULL;
	cvar_settemp("cl_movement_replay", "1");
}

bool CSQCPlayer_PreUpdate(entity this)
{
	if (this != csqcplayer) return false;
	if (csqcplayer_status != CSQCPLAYERSTATUS_FROMSERVER) CSQCPlayer_Unpredict(this);
	return true;
}

bool CSQCPlayer_PostUpdate(entity this)
{
	if (this.entnum != player_localnum + 1) return false;
	csqcplayer = this;
	csqcplayer_status = CSQCPLAYERSTATUS_FROMSERVER;
	if (cvar("cl_movement_replay"))
		cvar_settemp("cl_movement_replay", "0");
	this.entremove = CSQCPlayer_Remove;
	return true;
}
