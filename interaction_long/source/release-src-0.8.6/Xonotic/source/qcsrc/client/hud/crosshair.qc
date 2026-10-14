#include "crosshair.qh"

#include <client/draw.qh>
#include <client/hud/panel/scoreboard.qh>
#include <client/view.qh>
#include <common/deathtypes/all.qh>
#include <common/ent_cs.qh>
#include <common/mapobjects/trigger/viewloc.qh>
#include <common/minigames/cl_minigames.qh>
#include <common/minigames/cl_minigames_hud.qh>
#include <common/mutators/mutator/overkill/oknex.qh>
#include <common/vehicles/all.qh>
#include <common/viewloc.qh>
#include <common/wepent.qh>
#include <lib/csqcmodel/cl_player.qh>
#include <lib/warpzone/common.qh>

float pickup_crosshair_time, pickup_crosshair_size;
float hitindication_crosshair_size;
float use_vortex_chargepool;

float reticle_type;

vector wcross_origin;
float wcross_scale_prev, wcross_alpha_prev;
vector wcross_color_prev;
float wcross_scale_goal_prev, wcross_alpha_goal_prev;
vector wcross_color_goal_prev;
float wcross_changedonetime;

string wcross_name_goal_prev, wcross_name_goal_prev_prev;
float wcross_resolution_goal_prev, wcross_resolution_goal_prev_prev;
float wcross_name_changestarttime, wcross_name_changedonetime;
float wcross_name_alpha_goal_prev, wcross_name_alpha_goal_prev_prev;

float wcross_ring_prev;

entity trueaim;
entity trueaim_rifle;

const float SHOTTYPE_HITTEAM = 1;
const float SHOTTYPE_HITOBSTRUCTION = 2;
const float SHOTTYPE_HITWORLD = 3;
const float SHOTTYPE_HITENEMY = 4;

void TrueAim_Init()
{
	(trueaim = new_pure(trueaim)).dphitcontentsmask = DPCONTENTS_SOLID | DPCONTENTS_BODY | DPCONTENTS_CORPSE;
	(trueaim_rifle = new_pure(trueaim_rifle)).dphitcontentsmask = DPCONTENTS_BODY | DPCONTENTS_CORPSE;
}

float EnemyHitCheck()
{
	float t, n;
	wcross_origin = project_3d_to_2d(trace_endpos);
	wcross_origin.z = 0;
	if(trace_ent)
		n = trace_ent.entnum;
	else
		n = trace_networkentity;
	if(n < 1)
		return SHOTTYPE_HITWORLD;
	if(n > maxclients)
		return SHOTTYPE_HITWORLD;
	t = entcs_GetTeam(n - 1);
	if(teamplay && t == myteam)
		return SHOTTYPE_HITTEAM;
	if(t == NUM_SPECTATOR)
		return SHOTTYPE_HITWORLD;
	return SHOTTYPE_HITENEMY;
}

float TrueAimCheck(entity wepent)
{
	if(wepent.activeweapon.spawnflags & WEP_FLAG_NOTRUEAIM)
		return SHOTTYPE_HITWORLD;

	float nudge = 1;                                                                                                                                       
	vector vecs, trueaimpoint, w_shotorg;
	vector mi, ma, dv;
	float shottype;
	entity ta;
	float mv;

	mi = ma = '0 0 0';
	ta = trueaim;
	mv = MOVE_NOMONSTERS;

	switch(wepent.activeweapon)              
	{
		case WEP_VORTEX:
		case WEP_OVERKILL_NEX:
		case WEP_VAPORIZER:
			mv = MOVE_NORMAL;
			break;
		case WEP_RIFLE:
			ta = trueaim_rifle;
			mv = MOVE_NORMAL;
			if(zoomscript_caught)
			{
				tracebox(view_origin, '0 0 0', '0 0 0', view_origin + view_forward * max_shot_distance, mv, ta);
				return EnemyHitCheck();
			}
			break;
		case WEP_DEVASTATOR:                          
			mi = '-3 -3 -3';
			ma = '3 3 3';
			break;
		case WEP_FIREBALL:                          
			mi = '-16 -16 -16';
			ma = '16 16 16';
			break;
		case WEP_SEEKER:                          
			mi = '-2 -2 -2';
			ma = '2 2 2';
			break;
		case WEP_ELECTRO:                          
			mi = '0 0 -3';
			ma = '0 0 -3';
			break;
	}

	vector traceorigin = entcs_receiver(player_localentnum - 1).origin + (eZ * STAT(VIEWHEIGHT));

	vecs = decompressShotOrigin(STAT(SHOTORG));

	traceline(traceorigin, traceorigin + view_forward * max_shot_distance, mv, ta);
	trueaimpoint = trace_endpos;
	                                                                             
	                                                        
	trueaimpoint += view_forward;

	if(vdist((trueaimpoint - traceorigin), <, g_trueaim_minrange))
		trueaimpoint = traceorigin + view_forward * g_trueaim_minrange;

	if(vecs.x > 0)
		vecs.y = -vecs.y;
	else
		vecs = '0 0 0';

	dv = view_right * vecs.y + view_up * vecs.z;
	w_shotorg = traceorigin + dv;

	                                                             
	tracebox(w_shotorg, mi, ma, w_shotorg + view_forward * (vecs.x + nudge), MOVE_NORMAL, ta);                                                               
	w_shotorg = trace_endpos - view_forward * nudge;

	tracebox(w_shotorg, mi, ma, trueaimpoint, MOVE_NORMAL, ta);
	shottype = EnemyHitCheck();
	if(shottype != SHOTTYPE_HITWORLD)
		return shottype;

#if 0
	                                                        
	                                        
	if(vlen(trace_endpos - trueaimpoint) > vlen(ma) + vlen(mi) + 1)
		                                                                                                                              
		return SHOTTYPE_HITOBSTRUCTION;
#endif

	return SHOTTYPE_HITWORLD;
}

void HUD_Crosshair_Vehicle(entity this)
{
	if(hud != HUD_BUMBLEBEE_GUN)
	{
		Vehicle info = REGISTRY_GET(Vehicles, hud);
		info.vr_crosshair(info, this);
	}
}

vector crosshair_getcolor(entity this, float health_stat)
{
	static float rainbow_last_flicker;
	static vector rainbow_prev_color;
	vector wcross_color = '0 0 0';
	switch(autocvar_crosshair_color_special)
	{
		case 1:                
		{
			if(this != WEP_Null && hud == HUD_NORMAL)
			{
				wcross_color = this.wpcolor;
				break;
			}
			else { goto normalcolor; }
		}

		case 2:                                   
		{
			vector v = healtharmor_maxdamage(health_stat, STAT(ARMOR), armorblockpercent, DEATH_WEAPON.m_id);
			float health_and_armor = floor(v.x + 1);
			wcross_color = HUD_Get_Num_Color(health_and_armor, 200, false);
			break;
		}

		case 3:                        
		{
			if(time >= rainbow_last_flicker)
			{
				rainbow_prev_color = randomvec() * autocvar_crosshair_color_special_rainbow_brightness;
				rainbow_last_flicker = time + autocvar_crosshair_color_special_rainbow_delay;
			}
			wcross_color = rainbow_prev_color;
			break;
		}
LABEL(normalcolor)
		default: { wcross_color = stov(autocvar_crosshair_color); break; }
	}

	return wcross_color;
}

.entity tag_entity;
void HUD_Crosshair_ApplyPlayerAlpha(float new_alpha)
{
	csqcplayer.alpha = new_alpha;
	FOREACH_ENTITY_CLASS("ENT_CLIENT_MODEL", it.tag_entity == csqcplayer,
	{
		it.alpha = new_alpha;
	});
}

void HUD_Crosshair(entity this)
{
	                                                                                                         
	if(autocvar_chase_active > 0 && autocvar_crosshair_chase && STAT(HEALTH) <= 0 && csqcplayer)
		csqcplayer.alpha = csqcplayer.m_alpha;

	if (autocvar_chase_active > 0 && (autocvar_chase_front || autocvar_cl_lockview))
	{
		if (csqcplayer.alpha != csqcplayer.m_alpha)
			HUD_Crosshair_ApplyPlayerAlpha(csqcplayer.m_alpha);
		return;
	}

	float f, i, j;
	vector v;
	if(!scoreboard_active && !camera_active && intermission != 2 && !STAT(GAME_STOPPED) && !autocvar_cl_lockview
		&& spectatee_status != -1 && (!csqcplayer.viewloc || (!spectatee_status && (csqcplayer.viewloc.spawnflags & VIEWLOC_FREEAIM))) && !MUTATOR_CALLHOOK(DrawCrosshair)
		&& !HUD_MinigameMenu_IsOpened())
	{
		if (!autocvar_crosshair_enabled)                                       
			return;

		if (spectatee_status > 0 && STAT(CAMERA_SPECTATOR) == 2)
			return;

		if (hud != HUD_NORMAL)
		{
			HUD_Crosshair_Vehicle(this);
			return;
		}

		string wcross_style;
		float wcross_alpha, wcross_resolution;
		wcross_style = autocvar_crosshair;
		if (csqcplayer.viewloc && (csqcplayer.viewloc.spawnflags & VIEWLOC_FREEAIM) && autocvar_crosshair_2d != "")
			wcross_style = autocvar_crosshair_2d;
		if (wcross_style == "0")
			return;
		wcross_resolution = autocvar_crosshair_size;
		if (wcross_resolution == 0)
			return;
		wcross_alpha = autocvar_crosshair_alpha;
		if (wcross_alpha == 0)
			return;

		                
		float shottype;

		static int crosshair_chase_state = 0;

		                                                                        
		if(csqcplayer.viewloc && (csqcplayer.viewloc.spawnflags & VIEWLOC_FREEAIM))
			wcross_origin = viewloc_mousepos;
		else if(autocvar_chase_active > 0 && autocvar_crosshair_chase)
		{
			vector player_org = ((csqcplayer) ? csqcplayer.origin + csqcplayer.view_ofs : view_origin);
			float my_alpha = (!csqcplayer.m_alpha) ? 1 : csqcplayer.m_alpha;
			float chase_playeralpha = bound(0.001, autocvar_crosshair_chase_playeralpha, 1);
			if(csqcplayer && chase_playeralpha < 1 && my_alpha > chase_playeralpha)
			{
				crosshair_chase_state = 2;
				bool hit = false;
				if (pointinsidebox(view_origin, csqcplayer.absmin, csqcplayer.absmax))
					hit = true;
				else
				{
					WarpZone_TraceLine(view_origin, view_origin + max_shot_distance * view_forward, MOVE_NORMAL, NULL);
					if(trace_ent == csqcplayer)
						hit = true;
				}
				float prev_alpha = csqcplayer.alpha;
				float new_alpha;
				if(hit)
					new_alpha = max(csqcplayer.alpha - frametime * 5, chase_playeralpha);
				else
					new_alpha = min(csqcplayer.alpha + frametime * 5, my_alpha);

				if (new_alpha != prev_alpha)
					HUD_Crosshair_ApplyPlayerAlpha(new_alpha);
			}
			traceline(player_org, player_org + max_shot_distance * view_forward, MOVE_WORLDONLY, NULL);
			wcross_origin = project_3d_to_2d(trace_endpos);
		}
		else
			wcross_origin = project_3d_to_2d(view_origin + max_shot_distance * view_forward);
		wcross_origin.z = 0;
		if (crosshair_chase_state == 2)                        
			crosshair_chase_state = 1;
		else if (crosshair_chase_state == 1)                                    
		{
			                                        
			if (csqcplayer)
				HUD_Crosshair_ApplyPlayerAlpha(csqcplayer.m_alpha);
			crosshair_chase_state = 0;                              
		}

		if(autocvar_crosshair_hittest)
		{
			vector wcross_oldorigin;
			entity thiswep = viewmodels[0];                    
			wcross_oldorigin = wcross_origin;
			shottype = TrueAimCheck(thiswep);
			if(shottype == SHOTTYPE_HITWORLD)
			{
				v = wcross_origin - wcross_oldorigin;
				v.x /= vid_conwidth;
				v.y /= vid_conheight;
				if(vdist(v, >, 0.01))
					shottype = SHOTTYPE_HITOBSTRUCTION;
			}
			if(!autocvar_crosshair_hittest_showimpact)
				wcross_origin = wcross_oldorigin;
		}
		else
			shottype = SHOTTYPE_HITWORLD;

		vector wcross_color = '0 0 0', wcross_size = '0 0 0';
		string wcross_name = "";
		float wcross_scale, wcross_blur;

		entity e = WEP_Null;
		if(autocvar_crosshair_per_weapon || (autocvar_crosshair_color_special == 1))
		{
			entity wepent = viewmodels[0];                    
			e = wepent.switchingweapon;
			if(e)
			{
				if(autocvar_crosshair_per_weapon)
				{
					                                                                                            
					                                                                       
					                             
						         

					                                                               
					wcross_resolution *= e.w_crosshair_size;
					wcross_name = e.w_crosshair;
				}
			}
		}

		if(wcross_name == "")
			wcross_name = strcat("gfx/crosshair", wcross_style);

		                                
		wcross_color = crosshair_getcolor(e, STAT(HEALTH));

		if(autocvar_crosshair_effect_scalefade)
		{
			wcross_scale = wcross_resolution;
			wcross_resolution = 1;
		}
		else
		{
			wcross_scale = 1;
		}

		if(autocvar_crosshair_pickup)
		{
			float stat_pickup_time = STAT(LAST_PICKUP);

			if(pickup_crosshair_time < stat_pickup_time)
			{
				if(time - stat_pickup_time < 5)                                               
					pickup_crosshair_size = 1;

				pickup_crosshair_time = stat_pickup_time;
			}

			if(pickup_crosshair_size > 0)
				pickup_crosshair_size -= autocvar_crosshair_pickup_speed * frametime;
			else
				pickup_crosshair_size = 0;

			wcross_scale += sin(pickup_crosshair_size) * autocvar_crosshair_pickup;
		}

		                                                                
		if(autocvar_crosshair_hitindication)
		{
			vector col = ((autocvar_crosshair_color_special == 1) ? stov(autocvar_crosshair_hitindication_per_weapon_color) : stov(autocvar_crosshair_hitindication_color));

			if(unaccounted_damage)
			{
				hitindication_crosshair_size = 1;
			}

			if(hitindication_crosshair_size > 0)
				hitindication_crosshair_size -= autocvar_crosshair_hitindication_speed * frametime;
			else
				hitindication_crosshair_size = 0;

			wcross_scale += sin(hitindication_crosshair_size) * autocvar_crosshair_hitindication;
			wcross_color.x += sin(hitindication_crosshair_size) * col.x;
			wcross_color.y += sin(hitindication_crosshair_size) * col.y;
			wcross_color.z += sin(hitindication_crosshair_size) * col.z;
		}

		                                                                                       
		                                                                        
		                                   
			                                                                               
		if(shottype == SHOTTYPE_HITTEAM)
			wcross_scale /= autocvar_crosshair_hittest;                                  

		f = fabs(autocvar_crosshair_effect_time);
		if(wcross_scale != wcross_scale_goal_prev || wcross_alpha != wcross_alpha_goal_prev || wcross_color != wcross_color_goal_prev)
		{
			wcross_changedonetime = time + f;
		}
		if(wcross_name != wcross_name_goal_prev || wcross_resolution != wcross_resolution_goal_prev)
		{
			wcross_name_changestarttime = time;
			wcross_name_changedonetime = time + f;
			if(wcross_name_goal_prev_prev)
				strunzone(wcross_name_goal_prev_prev);
			wcross_name_goal_prev_prev = wcross_name_goal_prev;
			wcross_name_goal_prev = strzone(wcross_name);
			wcross_name_alpha_goal_prev_prev = wcross_name_alpha_goal_prev;
			wcross_resolution_goal_prev_prev = wcross_resolution_goal_prev;
			wcross_resolution_goal_prev = wcross_resolution;
		}

		wcross_scale_goal_prev = wcross_scale;
		wcross_alpha_goal_prev = wcross_alpha;
		wcross_color_goal_prev = wcross_color;

		if((shottype == SHOTTYPE_HITTEAM && autocvar_crosshair_hittest_blur_teammate)
			|| (shottype == SHOTTYPE_HITOBSTRUCTION && autocvar_crosshair_hittest_blur_wall && !autocvar_chase_active))
		{
			wcross_blur = 1;
			wcross_alpha *= 0.75;
		}
		else
			wcross_blur = 0;
		                              
		                                  
		                           
		if(time < wcross_changedonetime)
		{
			f = frametime / (wcross_changedonetime - time + frametime);
			wcross_scale = f * wcross_scale + (1 - f) * wcross_scale_prev;
			wcross_alpha = f * wcross_alpha + (1 - f) * wcross_alpha_prev;
			wcross_color = f * wcross_color + (1 - f) * wcross_color_prev;
		}

		wcross_scale_prev = wcross_scale;
		wcross_alpha_prev = wcross_alpha;
		wcross_color_prev = wcross_color;

		MUTATOR_CALLHOOK(UpdateCrosshair);

		wcross_scale *= 1 - autocvar__menu_alpha;
		wcross_alpha *= 1 - autocvar__menu_alpha;
		wcross_size = draw_getimagesize(wcross_name) * wcross_scale;

		if(wcross_scale >= 0.001 && wcross_alpha >= 0.001)
		{
			                                   
			if (autocvar_crosshair_ring || autocvar_crosshair_ring_reload)
			{
				                         
				float ring_value = 0, ring_scale = 0, ring_alpha = 0, ring_inner_value = 0, ring_inner_alpha = 0;
				string ring_image = string_null, ring_inner_image = string_null;
				vector ring_rgb = '0 0 0', ring_inner_rgb = '0 0 0';

				ring_scale = autocvar_crosshair_ring_size;

				entity wepent = viewmodels[0];                    

				int weapon_clipload = wepent.clip_load;
				int weapon_clipsize = wepent.clip_size;

				float arc_heat = wepent.arc_heat_percent;

				if(vortex_charge_movingavg == 0)                                                              
					vortex_charge_movingavg = wepent.vortex_charge;

				float charge = 0;
				float chargepool = 0;
				bool ring_vortex_enabled = false;
				if (autocvar_crosshair_ring && autocvar_crosshair_ring_vortex)
				{
					if (wepent.activeweapon == WEP_VORTEX)
					{
						charge = wepent.vortex_charge;
						chargepool = wepent.vortex_chargepool_ammo;
					}
					else if (wepent.activeweapon == WEP_OVERKILL_NEX)
					{
						charge = wepent.oknex_charge;
						chargepool = wepent.oknex_chargepool_ammo;
					}
					if (charge)
						ring_vortex_enabled = true;
				}

				if (ring_vortex_enabled)
				{
					if (chargepool || use_vortex_chargepool) {
						use_vortex_chargepool = 1;
						ring_inner_value = chargepool;
					} else {
						float rate = autocvar_crosshair_ring_vortex_currentcharge_movingavg_rate;
						vortex_charge_movingavg = (1 - rate) * vortex_charge_movingavg + rate * charge;
						ring_inner_value = bound(0, autocvar_crosshair_ring_vortex_currentcharge_scale * (charge - vortex_charge_movingavg), 1);
					}

					ring_inner_alpha = autocvar_crosshair_ring_vortex_inner_alpha;
					ring_inner_rgb = vec3(autocvar_crosshair_ring_vortex_inner_color_red, autocvar_crosshair_ring_vortex_inner_color_green, autocvar_crosshair_ring_vortex_inner_color_blue);
					ring_inner_image = "gfx/crosshair_ring_inner";

					                                                               
					ring_value = charge;
					ring_alpha = autocvar_crosshair_ring_vortex_alpha;
					ring_rgb = wcross_color;
					ring_image = "gfx/crosshair_ring_nexgun";
				}
				else if (autocvar_crosshair_ring && wepent.activeweapon == WEP_MINE_LAYER && WEP_CVAR(minelayer, limit) && autocvar_crosshair_ring_minelayer)
				{
					ring_value = bound(0, wepent.minelayer_mines / WEP_CVAR(minelayer, limit), 1);
					ring_alpha = autocvar_crosshair_ring_minelayer_alpha;
					ring_rgb = wcross_color;
					ring_image = "gfx/crosshair_ring";
				}
				else if (wepent.activeweapon == WEP_HAGAR && wepent.hagar_load && autocvar_crosshair_ring_hagar)
				{
					ring_value = bound(0, wepent.hagar_load / WEP_CVAR_SEC(hagar, load_max), 1);
					ring_alpha = autocvar_crosshair_ring_hagar_alpha;
					ring_rgb = wcross_color;
					ring_image = "gfx/crosshair_ring";
				}
				else if(autocvar_crosshair_ring_reload && weapon_clipsize)                                        
				{
					ring_value = bound(0, weapon_clipload / weapon_clipsize, 1);
					ring_scale = autocvar_crosshair_ring_reload_size;
					ring_alpha = autocvar_crosshair_ring_reload_alpha;
					ring_rgb = wcross_color;

					                                                                                                    
					                                                                                                
					if ((wepent.activeweapon == WEP_RIFLE) && (weapon_clipsize == 80))
						ring_image = "gfx/crosshair_ring_rifle";
					else
						ring_image = "gfx/crosshair_ring";
				}
				else if ( autocvar_crosshair_ring && autocvar_crosshair_ring_arc && arc_heat && wepent.activeweapon == WEP_ARC )
				{
					ring_value = arc_heat;
					ring_alpha = (1-arc_heat)*autocvar_crosshair_ring_arc_cold_alpha +
						arc_heat*autocvar_crosshair_ring_arc_hot_alpha;
					ring_rgb = (1-arc_heat)*wcross_color + arc_heat*autocvar_crosshair_ring_arc_hot_color;
					ring_image = "gfx/crosshair_ring";
				}

				                                                  
				if(autocvar_crosshair_effect_time > 0)
				{
					f = (time - wcross_name_changestarttime) / autocvar_crosshair_effect_time;
					if (f >= 1)
					{
						wcross_ring_prev = ((ring_image) ? true : false);
					}

					if(wcross_ring_prev)
					{
						if(f < 1)
							ring_alpha *= fabs(1 - bound(0, f, 1));
					}
					else
					{
						if(f < 1)
							ring_alpha *= bound(0, f, 1);
					}
				}

				if (autocvar_crosshair_ring_inner && ring_inner_value)                                                                 
					DrawCircleClippedPic(wcross_origin, wcross_size.x * wcross_resolution * ring_scale, ring_inner_image, ring_inner_value, ring_inner_rgb, wcross_alpha * ring_inner_alpha, DRAWFLAG_ADDITIVE);

				if (ring_value)
					DrawCircleClippedPic(wcross_origin, wcross_size.x * wcross_resolution * ring_scale, ring_image, ring_value, ring_rgb, wcross_alpha * ring_alpha, DRAWFLAG_ADDITIVE);
			}

#define CROSSHAIR_DO_BLUR(M,sz,wcross_name,wcross_alpha) \
			MACRO_BEGIN \
				vector scaled_sz = sz * wcross_size; \
				if(wcross_blur > 0) \
				{ \
					for(i = -2; i <= 2; ++i) \
					for(j = -2; j <= 2; ++j) \
					M(i,j,sz,scaled_sz,wcross_name,wcross_alpha*0.04); \
				} \
				else \
				{ \
					M(0,0,sz,scaled_sz,wcross_name,wcross_alpha); \
				} \
			MACRO_END

#define CROSSHAIR_DRAW_SINGLE(i,j,sz,scaled_sz,wcross_name,wcross_alpha) \
			drawpic(wcross_origin - ('0.5 0 0' * (scaled_sz.x + i * wcross_blur) + '0 0.5 0' * (scaled_sz.y + j * wcross_blur)), wcross_name, scaled_sz, wcross_color, wcross_alpha, DRAWFLAG_NORMAL)

#define CROSSHAIR_DRAW(sz,wcross_name,wcross_alpha) \
			CROSSHAIR_DO_BLUR(CROSSHAIR_DRAW_SINGLE,sz,wcross_name,wcross_alpha)

			if(time < wcross_name_changedonetime && wcross_name != wcross_name_goal_prev_prev && wcross_name_goal_prev_prev)
			{
				f = (wcross_name_changedonetime - time) / (wcross_name_changedonetime - wcross_name_changestarttime);
				wcross_size = draw_getimagesize(wcross_name_goal_prev_prev) * wcross_scale;
				CROSSHAIR_DRAW(wcross_resolution_goal_prev_prev, wcross_name_goal_prev_prev, wcross_alpha * f * wcross_name_alpha_goal_prev_prev);
				f = 1 - f;
			}
			else
			{
				f = 1;
			}
			wcross_name_alpha_goal_prev = f;

			wcross_size = draw_getimagesize(wcross_name) * wcross_scale;
			CROSSHAIR_DRAW(wcross_resolution, wcross_name, wcross_alpha * f);

			if(autocvar_crosshair_dot)
			{
				vector wcross_color_old;
				wcross_color_old = wcross_color;

				if((autocvar_crosshair_dot_color_custom) && (autocvar_crosshair_dot_color != "0"))
					wcross_color = stov(autocvar_crosshair_dot_color);

				CROSSHAIR_DRAW(wcross_resolution * autocvar_crosshair_dot_size, "gfx/crosshairdot", f * autocvar_crosshair_dot_alpha);
				                                            
				wcross_color = wcross_color_old;
			}
		}
	}
	else
	{
		wcross_scale_prev = 0;
		wcross_alpha_prev = 0;
		wcross_scale_goal_prev = 0;
		wcross_alpha_goal_prev = 0;
		wcross_changedonetime = 0;
		strfree(wcross_name_goal_prev);
		strfree(wcross_name_goal_prev_prev);
		wcross_name_changestarttime = 0;
		wcross_name_changedonetime = 0;
		wcross_name_alpha_goal_prev = 0;
		wcross_name_alpha_goal_prev_prev = 0;
		wcross_resolution_goal_prev = 0;
		wcross_resolution_goal_prev_prev = 0;
	}
}

void DrawReticle(entity this)
{
	if(!autocvar_cl_reticle || MUTATOR_CALLHOOK(DrawReticle))
	{
		reticle_type = 0;
		return;
	}

	float is_dead = (STAT(HEALTH) <= 0);
	string reticle_image = string_null;
	bool wep_zoomed = false;
	for(int slot = 0; slot < MAX_WEAPONSLOTS; ++slot)
	{
		entity wepe = viewmodels[slot];
		Weapon wep = wepe.activeweapon;
		if(wep != WEP_Null && wep.wr_zoom)
		{
			bool do_zoom = wep.wr_zoom(wep, NULL);
			if(!reticle_image && wep.w_reticle && wep.w_reticle != "")
				reticle_image = wep.w_reticle;
			wep_zoomed += do_zoom;
		}
	}
	                                                  
	                                                                                                   
	                                                                                                  
	                                                                                
	if(spectatee_status || is_dead || hud != HUD_NORMAL || this.viewloc)
	{
		                             
		reticle_type = 0;
	}
	else if(wep_zoomed && autocvar_cl_reticle_weapon)
	{
		if(reticle_image) { reticle_type = 2; }
		else { reticle_type = 0; }
	}
	else if(button_zoom || zoomscript_caught)
	{
		              
		reticle_type = 1;
	}

	if(reticle_type)
	{
		vector reticle_pos = '0 0 0', reticle_size = '0 0 0';
		if(autocvar_cl_reticle_stretch)
		{
			reticle_size.x = vid_conwidth;
			reticle_size.y = vid_conheight;
			reticle_pos.x = 0;
			reticle_pos.y = 0;
		}
		else
		{
			reticle_size.x = max(vid_conwidth, vid_conheight);
			reticle_size.y = max(vid_conwidth, vid_conheight);
			reticle_pos.x = (vid_conwidth - reticle_size.x) / 2;
			reticle_pos.y = (vid_conheight - reticle_size.y) / 2;
		}

		float f = (zoomscript_caught) ? 1 : current_zoomfraction;

		if(f)
		{
			switch(reticle_type)
			{
				case 1: drawpic(reticle_pos, "gfx/reticle_normal", reticle_size, '1 1 1', f * autocvar_cl_reticle_normal_alpha, DRAWFLAG_NORMAL); break;
				case 2: if(reticle_image) drawpic(reticle_pos, reticle_image, reticle_size, '1 1 1', f * autocvar_cl_reticle_weapon_alpha, DRAWFLAG_NORMAL); break;
			}
		}
	}
}
