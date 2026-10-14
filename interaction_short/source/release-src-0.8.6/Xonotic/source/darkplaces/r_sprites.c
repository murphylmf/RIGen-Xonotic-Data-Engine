
#include "quakedef.h"
#include "r_shadow.h"

extern cvar_t r_labelsprites_scale;
extern cvar_t r_labelsprites_roundtopixels;
extern cvar_t r_track_sprites;
extern cvar_t r_track_sprites_flags;
extern cvar_t r_track_sprites_scalew;
extern cvar_t r_track_sprites_scaleh;
extern cvar_t r_overheadsprites_perspective;
extern cvar_t r_overheadsprites_pushback;
extern cvar_t r_overheadsprites_scalex;
extern cvar_t r_overheadsprites_scaley;

#define TSF_ROTATE 1
#define TSF_ROTATE_CONTINOUSLY 2

                                                                                     
                                           
#ifndef EPSILON
# define EPSILON (1.0f / 32.0f)
# define MIN_EPSILON 0.0001f
#endif

                 
                                          
                                                                                     
               
   
         
   
#define SIDE_TOP 1
#define SIDE_LEFT 2
#define SIDE_BOTTOM 3
#define SIDE_RIGHT 4

static void R_TrackSprite(const entity_render_t *ent, vec3_t origin, vec3_t left, vec3_t up, int *edge, float *dir_angle)
{
	float distance;
	vec3_t bCoord;                              
	unsigned int i;

	                                                               
	VectorSubtract(origin, r_refdef.view.origin, bCoord);
	distance = VectorLength(bCoord);

	                         
	Matrix4x4_Transform(&r_refdef.view.inverse_matrix, origin, bCoord);

	*edge = 0;                                                              
	for(i = 0; i < 4; ++i)
	{
		if(PlaneDiff(origin, &r_refdef.view.frustum[i]) < -EPSILON)
			break;
	}

	                                                   
	if(i < 4)
	{
		float x, y;                                 
		float ax, ay;                                       
		                                                                            
		
		bCoord[2] *= r_refdef.view.frustum_x;
		bCoord[1] *= r_refdef.view.frustum_y;

		                                                            
		
		ax = fabs(bCoord[1]);
		ay = fabs(bCoord[2]);
		                                                              
		if(ax < ay)
		{
			ax = ay;
			                   
			if(bCoord[2] < 0.0f)
				*edge = SIDE_BOTTOM;
			else
				*edge = SIDE_TOP;
		} else {
			if(bCoord[1] < 0.0f)
				*edge = SIDE_RIGHT;
			else
				*edge = SIDE_LEFT;
		}
		
		          
		if(ax < MIN_EPSILON)                                  
			ax = MIN_EPSILON;
		                         
		x = bCoord[1] / ax;
		y = bCoord[2] / ax;

		ax = (1.0f / VectorLength(left));
		ay = (1.0f / VectorLength(up));
		                                                        
		                                                
		                           
		                 
		         
		          
		                 
		         
		          
		
		                               
		                                    
		                                      
		                                      
		                                          
		        
		distance = sqrt((distance*distance) / (1.0 +
					r_refdef.view.frustum_x*r_refdef.view.frustum_x * x*x * ax*ax +
					r_refdef.view.frustum_y*r_refdef.view.frustum_y * y*y * ay*ay));
		                                                                 
		
		                                                   
		VectorCopy(r_refdef.view.origin, origin);
		VectorMA(origin, distance, r_refdef.view.forward, origin);
		                                               
		VectorMA(origin, distance * r_refdef.view.frustum_x * x * ax, left, origin);
		VectorMA(origin, distance * r_refdef.view.frustum_y * y * ay, up, origin);

		if(r_track_sprites_flags.integer & TSF_ROTATE_CONTINOUSLY)
		{
			                                                               
			*dir_angle = atan(-y / x) * 180.0f/M_PI;
			                               
			if(x < 0.0f)
				*dir_angle += 180.0f;
		}

		left[0] *= r_track_sprites_scalew.value;
		left[1] *= r_track_sprites_scalew.value;
		left[2] *= r_track_sprites_scalew.value;

		up[0] *= r_track_sprites_scaleh.value;
		up[1] *= r_track_sprites_scaleh.value;
		up[2] *= r_track_sprites_scaleh.value;
	}
}

static void R_RotateSprite(const mspriteframe_t *frame, vec3_t origin, vec3_t left, vec3_t up, int edge, float dir_angle)
{
	if(!(r_track_sprites_flags.integer & TSF_ROTATE))
	{
		                                                            
		if(edge == SIDE_TOP)
			VectorMA(origin, -(fabs(frame->up)+fabs(frame->down)), up, origin);
	} else {
		static float rotation_angles[5] =
		{
			0,           
			-90.0f,	     
			0.0f,	       
			90.0f,	         
			180.0f,	        
		};
		
		                                                            
		                                                           
		matrix4x4_t rotm;
		vec3_t axis;
		vec3_t temp;
		vec2_t dir;
		float angle;

		if(edge < 1 || edge > 4)
			return;                                                                                                         
		
		dir[0] = frame->right + frame->left;
		dir[1] = frame->down + frame->up;

		                                                        
		if(dir[0] < MIN_EPSILON && dir[1] < MIN_EPSILON)
		{
			return;
		}

		                                                                                          

		                                                                         
		                                                                                                       

		angle = atan(dir[1] / dir[0]) * 180.0f/M_PI;

		                               
		if(dir[0] < 0.0f)
			angle += 180.0f;

		                                             
		                                                                          
		CrossProduct(up, left, axis);
		if(r_track_sprites_flags.integer & TSF_ROTATE_CONTINOUSLY)
			Matrix4x4_CreateRotate(&rotm, dir_angle - angle, axis[0], axis[1], axis[2]);
		else
			Matrix4x4_CreateRotate(&rotm, rotation_angles[edge] - angle, axis[0], axis[1], axis[2]);
		Matrix4x4_Transform(&rotm, up, temp);
		VectorCopy(temp, up);
		Matrix4x4_Transform(&rotm, left, temp);
		VectorCopy(temp, left);
	}
}

static float spritetexcoord2f[4*2] = {0, 1, 0, 0, 1, 0, 1, 1};

static void R_Model_Sprite_Draw_TransparentCallback(const entity_render_t *ent, const rtlight_t *rtlight, int numsurfaces, int *surfacelist)
{
	int i;
	dp_model_t *model = ent->model;
	vec3_t left, up, org, mforward, mleft, mup, middle;
	float scale, dx, dy, hud_vs_screen;
	int edge = 0;
	float dir_angle = 0.0f;
	float vertex3f[12];

	                                                           
	Matrix4x4_ToVectors(&ent->matrix, mforward, mleft, mup, org);
	VectorSubtract(org, r_refdef.view.forward, org);
	switch(model->sprite.sprnum_type)
	{
	case SPR_VP_PARALLEL_UPRIGHT:
		                  
		                                         
		scale = ent->scale / sqrt(r_refdef.view.forward[0]*r_refdef.view.forward[0]+r_refdef.view.forward[1]*r_refdef.view.forward[1]);
		left[0] = -r_refdef.view.forward[1] * scale;
		left[1] = r_refdef.view.forward[0] * scale;
		left[2] = 0;
		up[0] = 0;
		up[1] = 0;
		up[2] = ent->scale;
		break;
	case SPR_FACING_UPRIGHT:
		                  
		                                                                   
		scale = ent->scale / sqrt((org[0] - r_refdef.view.origin[0])*(org[0] - r_refdef.view.origin[0])+(org[1] - r_refdef.view.origin[1])*(org[1] - r_refdef.view.origin[1]));
		left[0] = (org[1] - r_refdef.view.origin[1]) * scale;
		left[1] = -(org[0] - r_refdef.view.origin[0]) * scale;
		left[2] = 0;
		up[0] = 0;
		up[1] = 0;
		up[2] = ent->scale;
		break;
	default:
		Con_Printf("R_SpriteSetup: unknown sprite type %i\n", model->sprite.sprnum_type);
		                                
	case SPR_VP_PARALLEL:
		                
		                   
		VectorScale(r_refdef.view.left, ent->scale, left);
		VectorScale(r_refdef.view.up, ent->scale, up);
		break;
	case SPR_LABEL_SCALE:
		                
		                   
		                                           
		               
		                                     
	
		if(r_fb.water.renderingscene)                                                                    
			return;

		                                                                 
		VectorCopy(r_refdef.view.left, left);
		VectorCopy(r_refdef.view.up, up);
		                                                                          
		if(r_track_sprites.integer)
			R_TrackSprite(ent, org, left, up, &edge, &dir_angle);
		
		scale = 2 * ent->scale * (DotProduct(r_refdef.view.forward, org) - DotProduct(r_refdef.view.forward, r_refdef.view.origin)) * r_labelsprites_scale.value;
		VectorScale(left, scale * r_refdef.view.frustum_x / vid_conwidth.integer, left);       
		VectorScale(up, scale * r_refdef.view.frustum_y / vid_conheight.integer, up);       
		break;
	case SPR_LABEL:
		                
		                   
		                                       
		                                                        
		                
		                                                         
		                                                                                                                                                                                         

		if(r_fb.water.renderingscene)                                                                    
			return;

		                                                                 
		VectorCopy(r_refdef.view.left, left);
		VectorCopy(r_refdef.view.up, up);
		                                                                          
		if(r_track_sprites.integer)
			R_TrackSprite(ent, org, left, up, &edge, &dir_angle);
		
		scale = 2 * (DotProduct(r_refdef.view.forward, org) - DotProduct(r_refdef.view.forward, r_refdef.view.origin));

		if(r_labelsprites_roundtopixels.integer)
		{
			hud_vs_screen = max(
				vid_conwidth.integer / (float) r_refdef.view.width,
				vid_conheight.integer / (float) r_refdef.view.height
			) / max(0.125, r_labelsprites_scale.value);

			                       
			                        
			                        
			if(hud_vs_screen <= 0.6)
				hud_vs_screen = 0;                              
			else if(hud_vs_screen <= 1.41)
				hud_vs_screen = 1;
			else if(hud_vs_screen <= 3.33)
				hud_vs_screen = 2;
			else
				hud_vs_screen = 0;                              

			if(hud_vs_screen)
			{
				                    
				VectorScale(left, scale * r_refdef.view.frustum_x / (r_refdef.view.width * hud_vs_screen), left);       
				VectorScale(up, scale * r_refdef.view.frustum_y / (r_refdef.view.height * hud_vs_screen), up);       
			}
			else
			{
				                 
				VectorScale(left, scale * r_refdef.view.frustum_x / vid_conwidth.integer * r_labelsprites_scale.value, left);       
				VectorScale(up, scale * r_refdef.view.frustum_y / vid_conheight.integer * r_labelsprites_scale.value, up);       
			}

			if(hud_vs_screen == 1)
			{
				VectorMA(r_refdef.view.origin, scale, r_refdef.view.forward, middle);                                      
				dx = 0.5 - fmod(r_refdef.view.width * 0.5 + (DotProduct(org, left) - DotProduct(middle, left)) / DotProduct(left, left) + 0.5, 1.0);
				dy = 0.5 - fmod(r_refdef.view.height * 0.5 + (DotProduct(org, up) - DotProduct(middle, up)) / DotProduct(up, up) + 0.5, 1.0);
				VectorMAMAM(1, org, dx, left, dy, up, org);
			}
		}
		else
		{
			                 
			VectorScale(left, scale * r_refdef.view.frustum_x / vid_conwidth.integer * r_labelsprites_scale.value, left);       
			VectorScale(up, scale * r_refdef.view.frustum_y / vid_conheight.integer * r_labelsprites_scale.value, up);       
		}
		break;
	case SPR_ORIENTED:
		                        
		                          
		VectorCopy(mleft, left);
		VectorCopy(mup, up);
		break;
	case SPR_VP_PARALLEL_ORIENTED:
		                                                   
		                                  
		                                                     
		left[0] = mleft[0] * r_refdef.view.forward[0] + mleft[1] * r_refdef.view.left[0] + mleft[2] * r_refdef.view.up[0];
		left[1] = mleft[0] * r_refdef.view.forward[1] + mleft[1] * r_refdef.view.left[1] + mleft[2] * r_refdef.view.up[1];
		left[2] = mleft[0] * r_refdef.view.forward[2] + mleft[1] * r_refdef.view.left[2] + mleft[2] * r_refdef.view.up[2];
		up[0] = mup[0] * r_refdef.view.forward[0] + mup[1] * r_refdef.view.left[0] + mup[2] * r_refdef.view.up[0];
		up[1] = mup[0] * r_refdef.view.forward[1] + mup[1] * r_refdef.view.left[1] + mup[2] * r_refdef.view.up[1];
		up[2] = mup[0] * r_refdef.view.forward[2] + mup[1] * r_refdef.view.left[2] + mup[2] * r_refdef.view.up[2];
		break;
	case SPR_OVERHEAD:
		                                                               
		VectorScale(r_refdef.view.left, ent->scale * r_overheadsprites_scalex.value, left);
		VectorScale(r_refdef.view.up, ent->scale * r_overheadsprites_scaley.value, up);
		VectorSubtract(org, r_refdef.view.origin, middle);
		VectorNormalize(middle);
		                    
		dir_angle = r_overheadsprites_perspective.value * (1 - fabs(DotProduct(middle, r_refdef.view.forward)));
		up[2] = up[2] + dir_angle;
		VectorNormalize(up);
		VectorScale(up, ent->scale * r_overheadsprites_scaley.value, up);
		                                                     
		org[0] = org[0] - middle[0]*r_overheadsprites_pushback.value;
		org[1] = org[1] - middle[1]*r_overheadsprites_pushback.value;
		org[2] = org[2] - middle[2]*r_overheadsprites_pushback.value;
		                            
		up[2] = up[2] + dir_angle * 0.3;
		                                   
		up[0] = up[0] + r_refdef.view.forward[0] * 0.07;
		up[1] = up[1] + r_refdef.view.forward[1] * 0.07;
		up[2] = up[2] + r_refdef.view.forward[2] * 0.07;
		break;
	}

	                                           
	for (i = 0;i < MAX_FRAMEBLENDS;i++)
	{
		if (ent->frameblend[i].lerp >= 0.01f)
		{
			mspriteframe_t *frame;
			texture_t *texture;
			RSurf_ActiveCustomEntity(&identitymatrix, &identitymatrix, ent->flags, 0, ent->colormod[0], ent->colormod[1], ent->colormod[2], ent->alpha * ent->frameblend[i].lerp, 4, vertex3f, spritetexcoord2f, NULL, NULL, NULL, NULL, 2, polygonelement3i, polygonelement3s, false, false);
			frame = model->sprite.sprdata_frames + ent->frameblend[i].subframe;
			texture = R_GetCurrentTexture(model->data_textures + ent->frameblend[i].subframe);
		
			                                                                          
			                                                                      
			              
			if (!(texture->currentmaterialflags & MATERIALFLAG_FULLBRIGHT))
			{
				VectorMAM(1.0f, texture->render_modellight_ambient, 0.25f, texture->render_modellight_diffuse, texture->render_modellight_ambient);
				VectorClear(texture->render_modellight_diffuse);
				VectorClear(texture->render_modellight_specular);
			}

			                                             
			if(model->sprite.sprnum_type == SPR_LABEL || model->sprite.sprnum_type == SPR_LABEL_SCALE)
				if(texture->currentmaterialflags & MATERIALFLAG_SHORTDEPTHRANGE)
					texture->currentmaterialflags = (texture->currentmaterialflags & ~MATERIALFLAG_SHORTDEPTHRANGE) | MATERIALFLAG_NODEPTHTEST;

			if(edge)
			{
				                                                                                           
				R_RotateSprite(frame, org, left, up, edge, dir_angle);
				edge = 0;
			}

			R_CalcSprite_Vertex3f(vertex3f, org, left, up, frame->left, frame->right, frame->down, frame->up);

			R_DrawCustomSurface_Texture(texture, &identitymatrix, texture->currentmaterialflags, 0, 4, 0, 2, false, false);
		}
	}

	rsurface.entity = NULL;
}

void R_Model_Sprite_Draw(entity_render_t *ent)
{
	vec3_t org;
	if (ent->frameblend[0].subframe < 0)
		return;

	Matrix4x4_OriginFromMatrix(&ent->matrix, org);
	R_MeshQueue_AddTransparent((ent->flags & RENDER_WORLDOBJECT) ? TRANSPARENTSORT_SKY : (ent->flags & RENDER_NODEPTHTEST) ? TRANSPARENTSORT_HUD : TRANSPARENTSORT_DISTANCE, org, R_Model_Sprite_Draw_TransparentCallback, ent, 0, rsurface.rtlight);
}

