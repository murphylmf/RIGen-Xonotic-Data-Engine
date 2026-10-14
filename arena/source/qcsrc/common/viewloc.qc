#include "viewloc.qh"

#if defined(CSQC)
	#include <common/util.qh>
	#include <common/constants.qh>
#elif defined(MENUQC)
#elif defined(SVQC)
	#include <common/stats.qh>
	#include <common/weapons/_all.qh>
#endif

                  
void viewloc_PlayerPhysics(entity this)
{
	if(this.viewloc)
	{
		if(this.viewloc.goalentity == this.viewloc.enemy)
			return;                                     

		vector old_movement = PHYS_CS(this).movement;
		PHYS_CS(this).movement_x = old_movement_y;
		if((this.viewloc.spawnflags & VIEWLOC_FREEMOVE) && !this.ladder_entity)
			PHYS_CS(this).movement_y = old_movement_x;
		else
			PHYS_CS(this).movement_y = 0;

		vector level_start, level_end;
		level_start = this.viewloc.enemy.origin;
		level_end = this.viewloc.goalentity.origin;
		vector forward = vectoangles(normalize(level_end - level_start));
		vector backward = vectoangles(normalize(level_start - level_end));

		if((this.viewloc.spawnflags & VIEWLOC_FREEMOVE) && this.angles_y < 0 && !this.ladder_entity)
			PHYS_CS(this).movement_y = -PHYS_CS(this).movement_y;

		if(this.viewloc.spawnflags & VIEWLOC_FREEAIM)
		{
			if(this.angles_y > 0)
				PHYS_CS(this).movement_x = -PHYS_CS(this).movement_x;
		}
		else
		{
			if(PHYS_CS(this).movement_x < 0)
				PHYS_CS(this).movement_x = -PHYS_CS(this).movement_x;

			if(PHYS_CS(this).movement_x < 0)        
				this.angles_y = backward.y;
			if(PHYS_CS(this).movement_x > 0)         
				this.angles_y = forward.y;
		}
	#if 0
		                                                         
		if(!(this.viewloc.spawnflags & VIEWLOC_FREEMOVE))
		{
#ifdef SVQC
			                                                        
			if (old_movement.x < 0)
				PHYS_INPUT_BUTTON_CROUCH(this) = true;
#elif defined(CSQC)
			if (old_movement.x < 0)
			{
				input_buttons |= BIT(4);
				this.flags |= FL_DUCKED;
			}
			                                                          
#endif
		}
	#endif
	}
}

#ifdef CSQC

void viewloc_SetTags(entity this)
{
	if(this.viewloc && wasfreed(this.viewloc))
		this.viewloc = NULL;

	if(this.viewloc.entnum != this.tag_networkviewloc)
	{
		if(this.tag_networkviewloc == 0)
			this.viewloc = NULL;
		else
			this.viewloc = findfloat(NULL, entnum, this.tag_networkviewloc);
	}
}

vector CursorToWorldCoord(vector mpos)
{
	vector wnear = cs_unproject(vec2(mpos));                                                                                
	vector wfar = cs_unproject(vec3(mpos.x, mpos.y, max_shot_distance));                                                                                                                                         
	traceline(wnear, wfar, MOVE_NOMONSTERS, NULL);
	return trace_endpos;
}

vector old_camera_angle = '0 0 0';
void viewloc_SetViewLocation()
{
	entity view = CSQCModel_server2csqc(player_localentnum - 1);
	if (!view) return;
	entity viewloc_ent = view.viewloc;
	if(viewloc_ent && !wasfreed(viewloc_ent) && viewloc_ent.enemy && viewloc_ent.goalentity)
	{
		bool have_sidescroll = (viewloc_ent.enemy != viewloc_ent.goalentity);
		vector position_a = viewloc_ent.enemy.origin;
		vector position_b = viewloc_ent.goalentity.origin;
		vector camera_angle = '0 0 0';
		vector camera_position;

		                                                                                            
                                                                                                                                           
		camera_position = vec_bounds_in(view.origin, position_a, position_b);

		                                   
		if (!(viewloc_ent.spawnflags & VIEWLOC_CAM_NOANGLE)) {
			camera_angle = viewloc_ent.enemy.movedir;
		}

		                                                                    
		if ((viewloc_ent.spawnflags & VIEWLOC_CAM_TRACK) || !have_sidescroll) {
			camera_angle = aim_vec (camera_position, view.origin);
		}

		                                                                                    
		if (viewloc_ent.spawnflags & VIEWLOC_CAM_SNAP_HARD) {
			camera_angle = angle_snap_vec(aim_vec(camera_position, view.origin), 90);
		}

		                                                      
		if (viewloc_ent.spawnflags & VIEWLOC_CAM_SNAP_CLOSE) {
			                                             
			camera_angle = aim_vec(camera_position, view.origin);

			                                                                                        
                                                                       
                                                                                               
      
			float camera_angle_diff = max(camera_angle.y, old_camera_angle.y) - min(camera_angle.y, old_camera_angle.y);

			if (60 <= camera_angle_diff) {                  
				old_camera_angle.y = angle_snap_f(camera_angle.y, 90);
			} else {                  
				camera_angle.y = old_camera_angle.y;
			}
		}

		                                                                                         
		if (!(viewloc_ent.spawnflags & VIEWLOC_CAM_SNAP_UNLOCK)) {
			camera_angle.x = 0;
			camera_angle.z = 0;
		}

#if 0
		LOG_TRACE(vtos(camera_position));
		LOG_TRACE(vtos(old_camera_angle));
		LOG_TRACE(vtos(camera_angle));
#endif

		freeze_org = getpropertyvec(VF_ORIGIN);
		freeze_ang = getpropertyvec(VF_ANGLES);
		setproperty(VF_ORIGIN, camera_position);
		setproperty(VF_ANGLES, camera_angle);

		if(spectatee_status)
			return;                                                  

		if (have_sidescroll) {
			vector view_angle = view.angles;
			if (!(viewloc_ent.spawnflags & VIEWLOC_FREEAIM)) {
				vector avatar_facing_dir;
				                                                                        
				if (0 == input_movevalues.y) {
					avatar_facing_dir = view_angle;                                  
				} else if (0 > input_movevalues.y) {                   
					avatar_facing_dir = vectoangles(normalize(vec_to_max(position_b, position_a) - vec_to_min(position_b, position_a)));
				} else {                    
					avatar_facing_dir = vectoangles(normalize(vec_to_min(position_b, position_a) - vec_to_max(position_b, position_a)));
				}
				view_angle.y = avatar_facing_dir.y;                                                 

				                                                   
				if (!(viewloc_ent.spawnflags & VIEWLOC_FREEMOVE)) {
					if (0 > input_movevalues.x) {           
						view_angle.x = 50;
					} else if (0 < input_movevalues.x) {             
						view_angle.x = -50;
					}
				}
			} else {
				vector mpos = CursorToWorldCoord(viewloc_mousepos);
				mpos.x = view.origin.x;                                                     
				view_angle = aim_vec(view.origin + view.view_ofs, mpos);                  
			}
			view.angles_y = view_angle.y;
			setproperty(VF_CL_VIEWANGLES, view_angle);
		}
	}
}

STATIC_INIT_LATE(viewloc_cursor)
{
	                                                           
	viewloc_mousepos = '0.5 0 0' * autocvar_vid_conwidth + '0 0.5 0' * autocvar_vid_conheight;
}

#endif
