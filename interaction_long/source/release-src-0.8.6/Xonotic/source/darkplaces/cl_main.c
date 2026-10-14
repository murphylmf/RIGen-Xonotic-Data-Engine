  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
                                 

#include "quakedef.h"
#include "capture_telemetry.h"
#include "cl_collision.h"
#include "cl_video.h"
#include "image.h"
#include "csprogs.h"
#include "r_shadow.h"
#include "libcurl.h"
#include "snd_main.h"

                                                                        
                                              

cvar_t csqc_progname = {0, "csqc_progname","csprogs.dat","name of csprogs.dat file to load"};
cvar_t csqc_progcrc = {CVAR_READONLY, "csqc_progcrc","-1","CRC of csprogs.dat file to load (-1 is none), only used during level changes and then reset to -1"};
cvar_t csqc_progsize = {CVAR_READONLY, "csqc_progsize","-1","file size of csprogs.dat file to load (-1 is none), only used during level changes and then reset to -1"};
cvar_t csqc_usedemoprogs = {0, "csqc_usedemoprogs","1","use csprogs stored in demos"};

cvar_t cl_shownet = {0, "cl_shownet","0","1 = print packet size, 2 = print packet message list"};
cvar_t cl_nolerp = {0, "cl_nolerp", "0","network update smoothing"};
cvar_t cl_lerpexcess = {0, "cl_lerpexcess", "0","maximum allowed lerp excess (hides, not fixes, some packet loss)"};
cvar_t cl_lerpanim_maxdelta_server = {0, "cl_lerpanim_maxdelta_server", "0.1","maximum frame delta for smoothing between server-controlled animation frames (when 0, one network frame)"};
cvar_t cl_lerpanim_maxdelta_framegroups = {0, "cl_lerpanim_maxdelta_framegroups", "0.1","maximum frame delta for smoothing between framegroups (when 0, one network frame)"};

cvar_t cl_itembobheight = {0, "cl_itembobheight", "0","how much items bob up and down (try 8)"};
cvar_t cl_itembobspeed = {0, "cl_itembobspeed", "0.5","how frequently items bob up and down"};

cvar_t lookspring = {CVAR_SAVE, "lookspring","0","returns pitch to level with the floor when no longer holding a pitch key"};
cvar_t lookstrafe = {CVAR_SAVE, "lookstrafe","0","move instead of turning"};
cvar_t sensitivity = {CVAR_SAVE, "sensitivity","3","mouse speed multiplier"};

cvar_t m_pitch = {CVAR_SAVE, "m_pitch","0.022","mouse pitch speed multiplier"};
cvar_t m_yaw = {CVAR_SAVE, "m_yaw","0.022","mouse yaw speed multiplier"};
cvar_t m_forward = {CVAR_SAVE, "m_forward","1","mouse forward speed multiplier"};
cvar_t m_side = {CVAR_SAVE, "m_side","0.8","mouse side speed multiplier"};

cvar_t freelook = {CVAR_SAVE, "freelook", "1","mouse controls pitch instead of forward/back"};

cvar_t cl_autodemo = {CVAR_SAVE, "cl_autodemo", "0", "records every game played, using the date/time and map name to name the demo file" };
cvar_t cl_autodemo_nameformat = {CVAR_SAVE, "cl_autodemo_nameformat", "autodemos/%Y-%m-%d_%H-%M", "The format of the cl_autodemo filename, followed by the map name (the date is encoded using strftime escapes)" };
cvar_t cl_autodemo_delete = {0, "cl_autodemo_delete", "0", "Delete demos after recording.  This is a bitmask, bit 1 gives the default, bit 0 the value for the current demo.  Thus, the values are: 0 = disabled; 1 = delete current demo only; 2 = delete all demos except the current demo; 3 = delete all demos from now on" };

cvar_t r_draweffects = {0, "r_draweffects", "1","renders temporary sprite effects"};

cvar_t cl_explosions_alpha_start = {CVAR_SAVE, "cl_explosions_alpha_start", "1.5","starting alpha of an explosion shell"};
cvar_t cl_explosions_alpha_end = {CVAR_SAVE, "cl_explosions_alpha_end", "0","end alpha of an explosion shell (just before it disappears)"};
cvar_t cl_explosions_size_start = {CVAR_SAVE, "cl_explosions_size_start", "16","starting size of an explosion shell"};
cvar_t cl_explosions_size_end = {CVAR_SAVE, "cl_explosions_size_end", "128","ending alpha of an explosion shell (just before it disappears)"};
cvar_t cl_explosions_lifetime = {CVAR_SAVE, "cl_explosions_lifetime", "0.5","how long an explosion shell lasts"};

cvar_t cl_stainmaps = {CVAR_SAVE, "cl_stainmaps", "0","stains lightmaps, much faster than decals but blurred"};
cvar_t cl_stainmaps_clearonload = {CVAR_SAVE, "cl_stainmaps_clearonload", "1","clear stainmaps on map restart"};

cvar_t cl_beams_polygons = {CVAR_SAVE, "cl_beams_polygons", "1","use beam polygons instead of models"};
cvar_t cl_beams_quakepositionhack = {CVAR_SAVE, "cl_beams_quakepositionhack", "1", "makes your lightning gun appear to fire from your waist (as in Quake and QuakeWorld)"};
cvar_t cl_beams_instantaimhack = {CVAR_SAVE, "cl_beams_instantaimhack", "0", "makes your lightning gun aiming update instantly"};
cvar_t cl_beams_lightatend = {CVAR_SAVE, "cl_beams_lightatend", "0", "make a light at the end of the beam"};

cvar_t cl_deathfade = {CVAR_SAVE, "cl_deathfade", "0", "fade screen to dark red when dead, value represents how fast the fade is (higher is faster)"};

cvar_t cl_noplayershadow = {CVAR_SAVE, "cl_noplayershadow", "0","hide player shadow"};

cvar_t cl_dlights_decayradius = {CVAR_SAVE, "cl_dlights_decayradius", "1", "reduces size of light flashes over time"};
cvar_t cl_dlights_decaybrightness = {CVAR_SAVE, "cl_dlights_decaybrightness", "1", "reduces brightness of light flashes over time"};

cvar_t qport = {0, "qport", "0", "identification key for playing on qw servers (allows you to maintain a connection to a quakeworld server even if your port changes)"};

cvar_t cl_prydoncursor = {0, "cl_prydoncursor", "0", "enables a mouse pointer which is able to click on entities in the world, useful for point and click mods, see PRYDON_CLIENTCURSOR extension in dpextensions.qc"};
cvar_t cl_prydoncursor_notrace = {0, "cl_prydoncursor_notrace", "0", "disables traceline used in prydon cursor reporting to the game, saving some cpu time"};

cvar_t cl_deathnoviewmodel = {0, "cl_deathnoviewmodel", "1", "hides gun model when dead"};

cvar_t cl_locs_enable = {CVAR_SAVE, "locs_enable", "1", "enables replacement of certain % codes in chat messages: %l (location), %d (last death location), %h (health), %a (armor), %x (rockets), %c (cells), %r (rocket launcher status), %p (powerup status), %w (weapon status), %t (current time in level)"};
cvar_t cl_locs_show = {0, "locs_show", "0", "shows defined locations for editing purposes"};

extern cvar_t r_equalize_entities_fullbright;

client_static_t	cls;
client_state_t	cl;

  
                     
             

                     
  
void CL_ClearState(void)
{
	int i;
	entity_t *ent;

	CL_VM_ShutDown();

                               
	Mem_EmptyPool(cls.levelmempool);
	memset (&cl, 0, sizeof(cl));

	S_StopAllSounds();

	                                    
	cl.mviewzoom[0] = cl.mviewzoom[1] = 1;
	cl.sensitivityscale = 1.0f;

	                                         
	cl.csqc_vidvars.drawworld = r_drawworld.integer != 0;
	cl.csqc_vidvars.drawenginesbar = true;
	cl.csqc_vidvars.drawcrosshair = true;

	                                                                               
	cl.statsf = (float *)cl.stats;

	cl.num_entities = 0;
	cl.num_static_entities = 0;
	cl.num_brushmodel_entities = 0;

	                                   
	cl.max_csqcrenderentities = 0;
	cl.max_entities = MAX_ENITIES_INITIAL;
	cl.max_static_entities = MAX_STATICENTITIES;
	cl.max_effects = MAX_EFFECTS;
	cl.max_beams = MAX_BEAMS;
	cl.max_dlights = MAX_DLIGHTS;
	cl.max_lightstyle = MAX_LIGHTSTYLES;
	cl.max_brushmodel_entities = MAX_EDICTS;
	cl.max_particles = MAX_PARTICLES_INITIAL;                     
	cl.max_decals = MAX_DECALS_INITIAL;                     
	cl.max_showlmps = 0;

	cl.num_dlights = 0;
	cl.num_effects = 0;
	cl.num_beams = 0;

	cl.csqcrenderentities = NULL;
	cl.entities = (entity_t *)Mem_Alloc(cls.levelmempool, cl.max_entities * sizeof(entity_t));
	cl.entities_active = (unsigned char *)Mem_Alloc(cls.levelmempool, cl.max_brushmodel_entities * sizeof(unsigned char));
	cl.static_entities = (entity_t *)Mem_Alloc(cls.levelmempool, cl.max_static_entities * sizeof(entity_t));
	cl.effects = (cl_effect_t *)Mem_Alloc(cls.levelmempool, cl.max_effects * sizeof(cl_effect_t));
	cl.beams = (beam_t *)Mem_Alloc(cls.levelmempool, cl.max_beams * sizeof(beam_t));
	cl.dlights = (dlight_t *)Mem_Alloc(cls.levelmempool, cl.max_dlights * sizeof(dlight_t));
	cl.lightstyle = (lightstyle_t *)Mem_Alloc(cls.levelmempool, cl.max_lightstyle * sizeof(lightstyle_t));
	cl.brushmodel_entities = (int *)Mem_Alloc(cls.levelmempool, cl.max_brushmodel_entities * sizeof(int));
	cl.particles = (particle_t *) Mem_Alloc(cls.levelmempool, cl.max_particles * sizeof(particle_t));
	cl.decals = (decal_t *) Mem_Alloc(cls.levelmempool, cl.max_decals * sizeof(decal_t));
	cl.showlmps = NULL;

	                                                                        
	for (i = 0;i < cl.max_entities;i++)
	{
		cl.entities[i].state_baseline = defaultstate;
		cl.entities[i].state_previous = defaultstate;
		cl.entities[i].state_current = defaultstate;
	}

	if (IS_NEXUIZ_DERIVED(gamemode))
	{
		VectorSet(cl.playerstandmins, -16, -16, -24);
		VectorSet(cl.playerstandmaxs, 16, 16, 45);
		VectorSet(cl.playercrouchmins, -16, -16, -24);
		VectorSet(cl.playercrouchmaxs, 16, 16, 25);
	}
	else
	{
		VectorSet(cl.playerstandmins, -16, -16, -24);
		VectorSet(cl.playerstandmaxs, 16, 16, 24);
		VectorSet(cl.playercrouchmins, -16, -16, -24);
		VectorSet(cl.playercrouchmaxs, 16, 16, 24);
	}

	                                       
	R_ResetSkyBox();

	ent = &cl.entities[0];
	                                                                
	ent->state_current.active = true;
	ent->render.model = cl.worldmodel = NULL;                      
	ent->render.alpha = 1;
	ent->render.flags = RENDER_SHADOW | RENDER_LIGHT;
	Matrix4x4_CreateFromQuakeEntity(&ent->render.matrix, 0, 0, 0, 0, 0, 0, 1);
	ent->render.allowdecals = true;
	CL_UpdateRenderEntity(&ent->render);

	                                
	noclip_anglehack = false;

	                                    
	memset(cl.qw_deltasequence, -1, sizeof(cl.qw_deltasequence));

	                                         
	IN_BestWeapon_ResetData();

	CL_Screen_NewMap();
}

void CL_SetInfo(const char *key, const char *value, qboolean send, qboolean allowstarkey, qboolean allowmodel, qboolean quiet)
{
	int i;
	qboolean fail = false;
	char vabuf[1024];
	if (!allowstarkey && key[0] == '*')
		fail = true;
	if (!allowmodel && (!strcasecmp(key, "pmodel") || !strcasecmp(key, "emodel")))
		fail = true;
	for (i = 0;key[i];i++)
		if (ISWHITESPACE(key[i]) || key[i] == '\"')
			fail = true;
	for (i = 0;value[i];i++)
		if (value[i] == '\r' || value[i] == '\n' || value[i] == '\"')
			fail = true;
	if (fail)
	{
		if (!quiet)
			Con_Printf("Can't setinfo \"%s\" \"%s\"\n", key, value);
		return;
	}
	InfoString_SetValue(cls.userinfo, sizeof(cls.userinfo), key, value);
	if (cls.state == ca_connected && cls.netcon)
	{
		if (cls.protocol == PROTOCOL_QUAKEWORLD)
		{
			MSG_WriteByte(&cls.netcon->message, qw_clc_stringcmd);
			MSG_WriteString(&cls.netcon->message, va(vabuf, sizeof(vabuf), "setinfo \"%s\" \"%s\"", key, value));
		}
		else if (!strcasecmp(key, "name"))
		{
			MSG_WriteByte(&cls.netcon->message, clc_stringcmd);
			MSG_WriteString(&cls.netcon->message, va(vabuf, sizeof(vabuf), "name \"%s\"", value));
		}
		else if (!strcasecmp(key, "playermodel"))
		{
			MSG_WriteByte(&cls.netcon->message, clc_stringcmd);
			MSG_WriteString(&cls.netcon->message, va(vabuf, sizeof(vabuf), "playermodel \"%s\"", value));
		}
		else if (!strcasecmp(key, "playerskin"))
		{
			MSG_WriteByte(&cls.netcon->message, clc_stringcmd);
			MSG_WriteString(&cls.netcon->message, va(vabuf, sizeof(vabuf), "playerskin \"%s\"", value));
		}
		else if (!strcasecmp(key, "topcolor"))
		{
			                                                                        
		}
		else if (!strcasecmp(key, "bottomcolor"))
		{
			                                                                        
		}
		else if (!strcasecmp(key, "rate"))
		{
			MSG_WriteByte(&cls.netcon->message, clc_stringcmd);
			MSG_WriteString(&cls.netcon->message, va(vabuf, sizeof(vabuf), "rate \"%s\"", value));
		}
		else if (!strcasecmp(key, "rate_burstsize"))
		{
			MSG_WriteByte(&cls.netcon->message, clc_stringcmd);
			MSG_WriteString(&cls.netcon->message, va(vabuf, sizeof(vabuf), "rate_burstsize \"%s\"", value));
		}
	}
}

void CL_ExpandEntities(int num)
{
	int i, oldmaxentities;
	entity_t *oldentities;
	if (num >= cl.max_entities)
	{
		if (!cl.entities)
			Sys_Error("CL_ExpandEntities: cl.entities not initialized");
		if (num >= MAX_EDICTS)
			Host_Error("CL_ExpandEntities: num %i >= %i", num, MAX_EDICTS);
		oldmaxentities = cl.max_entities;
		oldentities = cl.entities;
		cl.max_entities = (num & ~255) + 256;
		cl.entities = (entity_t *)Mem_Alloc(cls.levelmempool, cl.max_entities * sizeof(entity_t));
		memcpy(cl.entities, oldentities, oldmaxentities * sizeof(entity_t));
		Mem_Free(oldentities);
		for (i = oldmaxentities;i < cl.max_entities;i++)
		{
			cl.entities[i].state_baseline = defaultstate;
			cl.entities[i].state_previous = defaultstate;
			cl.entities[i].state_current = defaultstate;
		}
	}
}

void CL_ExpandCSQCRenderEntities(int num)
{
	int i;
	int oldmaxcsqcrenderentities;
	entity_render_t *oldcsqcrenderentities;
	if (num >= cl.max_csqcrenderentities)
	{
		if (num >= MAX_EDICTS)
			Host_Error("CL_ExpandEntities: num %i >= %i", num, MAX_EDICTS);
		oldmaxcsqcrenderentities = cl.max_csqcrenderentities;
		oldcsqcrenderentities = cl.csqcrenderentities;
		cl.max_csqcrenderentities = (num & ~255) + 256;
		cl.csqcrenderentities = (entity_render_t *)Mem_Alloc(cls.levelmempool, cl.max_csqcrenderentities * sizeof(entity_render_t));
		if (oldcsqcrenderentities)
		{
			memcpy(cl.csqcrenderentities, oldcsqcrenderentities, oldmaxcsqcrenderentities * sizeof(entity_render_t));
			for (i = 0;i < r_refdef.scene.numentities;i++)
				if(r_refdef.scene.entities[i] >= oldcsqcrenderentities && r_refdef.scene.entities[i] < (oldcsqcrenderentities + oldmaxcsqcrenderentities))
					r_refdef.scene.entities[i] = cl.csqcrenderentities + (r_refdef.scene.entities[i] - oldcsqcrenderentities);
			Mem_Free(oldcsqcrenderentities);
		}
	}
}

  
                     
             

                                        
                                                                   
                     
  
void CL_Disconnect(void)
{
	if (cls.state == ca_dedicated)
		return;

	if (COM_CheckParm("-profilegameonly"))
		Sys_AllowProfiling(false);

	Curl_Clear_forthismap();

	Con_DPrintf("CL_Disconnect\n");

    Cvar_SetValueQuick(&csqc_progcrc, -1);
	Cvar_SetValueQuick(&csqc_progsize, -1);
	CL_VM_ShutDown();
                                    
	S_StopAllSounds ();

	cl.parsingtextexpectingpingforscores = 0;                                      

	                        
	cl.cshifts[0].percent = 0;
	cl.cshifts[1].percent = 0;
	cl.cshifts[2].percent = 0;
	cl.cshifts[3].percent = 0;

	cl.worldmodel = NULL;

	CL_Parse_ErrorCleanUp();

	if (cls.demoplayback)
		CL_StopPlayback();
	else if (cls.netcon)
	{
		sizebuf_t buf;
		unsigned char bufdata[8];
		if (cls.demorecording)
			CL_Stop_f();

		                                                               
		                                              
		memset(&buf, 0, sizeof(buf));
		buf.data = bufdata;
		buf.maxsize = sizeof(bufdata);
		if (cls.protocol == PROTOCOL_QUAKEWORLD)
		{
			Con_DPrint("Sending drop command\n");
			MSG_WriteByte(&buf, qw_clc_stringcmd);
			MSG_WriteString(&buf, "drop");
		}
		else
		{
			Con_DPrint("Sending clc_disconnect\n");
			MSG_WriteByte(&buf, clc_disconnect);
		}
		NetConn_SendUnreliableMessage(cls.netcon, &buf, cls.protocol, 10000, 0, false);
		NetConn_SendUnreliableMessage(cls.netcon, &buf, cls.protocol, 10000, 0, false);
		NetConn_SendUnreliableMessage(cls.netcon, &buf, cls.protocol, 10000, 0, false);
		NetConn_Close(cls.netcon);
		cls.netcon = NULL;
	}
	cls.state = ca_disconnected;
	cl.islocalgame = false;

	cls.demoplayback = cls.timedemo = false;
	cls.signon = 0;
}

void CL_Disconnect_f(void)
{
	CL_Disconnect ();
	if (sv.active)
		Host_ShutdownServer ();
}




  
                     
                      

                                              
                     
  
void CL_EstablishConnection(const char *host, int firstarg)
{
	if (cls.state == ca_dedicated)
		return;

	                                                         
	if (COM_CheckParm("-benchmark"))
		return;

	                                     
#ifdef CONFIG_MENU
	M_Update_Return_Reason("");
#endif
	cls.demonum = -1;

	                                    
	if (cls.demoplayback)
		CL_StopPlayback();

	                                                          
	Curl_Clear_forthismap();

	                                                                   
	NetConn_UpdateSockets();

	if (LHNETADDRESS_FromString(&cls.connect_address, host, 26000) && (cls.connect_mysocket = NetConn_ChooseClientSocketForAddress(&cls.connect_address)))
	{
		cls.connect_trying = true;
		cls.connect_remainingtries = 3;
		cls.connect_nextsendtime = 0;

		                                 
		if(firstarg >= 0)
		{
			int i;
			*cls.connect_userinfo = 0;
			for(i = firstarg; i+2 <= Cmd_Argc(); i += 2)
				InfoString_SetValue(cls.connect_userinfo, sizeof(cls.connect_userinfo), Cmd_Argv(i), Cmd_Argv(i+1));
		}
		else if(firstarg < -1)
		{
			                             
			            
			*cls.connect_userinfo = 0;
		}

#ifdef CONFIG_MENU
		M_Update_Return_Reason("Trying to connect...");
#endif
	}
	else
	{
		Con_Print("Unable to find a suitable network socket to connect to server.\n");
#ifdef CONFIG_MENU
		M_Update_Return_Reason("No network");
#endif
	}
}

  
              
                  
              
  
static void CL_PrintEntities_f(void)
{
	entity_t *ent;
	int i;

	for (i = 0, ent = cl.entities;i < cl.num_entities;i++, ent++)
	{
		const char* modelname;

		if (!ent->state_current.active)
			continue;

		if (ent->render.model)
			modelname = ent->render.model->name;
		else
			modelname = "--no model--";
		Con_Printf("%3i: %-25s:%4i (%5i %5i %5i) [%3i %3i %3i] %4.2f %5.3f\n", i, modelname, ent->render.framegroupblend[0].frame, (int) ent->state_current.origin[0], (int) ent->state_current.origin[1], (int) ent->state_current.origin[2], (int) ent->state_current.angles[0] % 360, (int) ent->state_current.angles[1] % 360, (int) ent->state_current.angles[2] % 360, ent->render.scale, ent->render.alpha);
	}
}

  
               
                   

                                                       
               
  
static void CL_ModelIndexList_f(void)
{
	int i;
	dp_model_t *model;

	               
	Con_Printf("%3s: %-30s %-8s %-8s\n", "ID", "Name", "Type", "Triangles");

	for (i = -MAX_MODELS;i < MAX_MODELS;i++)
	{
		model = CL_GetModelByIndex(i);
		if (!model)
			continue;
		if(model->loaded || i == 1)
			Con_Printf("%3i: %-30s %-8s %-10i\n", i, model->name, model->modeldatatypestring, model->surfmesh.num_triangles);
		else
			Con_Printf("%3i: %-30s %-30s\n", i, model->name, "--no local model found--");
		i++;
	}
}

  
               
                   

                                        
               
  
static void CL_SoundIndexList_f(void)
{
	int i = 1;

	while(cl.sound_precache[i] && i != MAX_SOUNDS)
	{               
		Con_Printf("%i : %s\n", i, cl.sound_precache[i]->name);
		i++;
	}
}

  
               
                     

                                                                            
               
  
void CL_UpdateRenderEntity(entity_render_t *ent)
{
	vec3_t org;
	vec_t scale;
	dp_model_t *model = ent->model;
	                                             
	Matrix4x4_Invert_Simple(&ent->inversematrix, &ent->matrix);
	                                   
	VM_FrameBlendFromFrameGroupBlend(ent->frameblend, ent->framegroupblend, ent->model, cl.time);
	                                              
	Matrix4x4_OriginFromMatrix(&ent->matrix, org);
	                                                            
	ent->scale = scale = Matrix4x4_ScaleFromMatrix(&ent->matrix);
	if (model)
	{
		                                                                                                          
#ifdef MATRIX4x4_OPENGLORIENTATION
		if (ent->matrix.m[0][2] != 0 || ent->matrix.m[1][2] != 0)
#else
		if (ent->matrix.m[2][0] != 0 || ent->matrix.m[2][1] != 0)
#endif
		{
			                
			VectorMA(org, scale, model->rotatedmins, ent->mins);
			VectorMA(org, scale, model->rotatedmaxs, ent->maxs);
		}
#ifdef MATRIX4x4_OPENGLORIENTATION
		else if (ent->matrix.m[1][0] != 0 || ent->matrix.m[0][1] != 0)
#else
		else if (ent->matrix.m[0][1] != 0 || ent->matrix.m[1][0] != 0)
#endif
		{
			      
			VectorMA(org, scale, model->yawmins, ent->mins);
			VectorMA(org, scale, model->yawmaxs, ent->maxs);
		}
		else
		{
			VectorMA(org, scale, model->normalmins, ent->mins);
			VectorMA(org, scale, model->normalmaxs, ent->maxs);
		}
	}
	else
	{
		ent->mins[0] = org[0] - 16;
		ent->mins[1] = org[1] - 16;
		ent->mins[2] = org[2] - 16;
		ent->maxs[0] = org[0] + 16;
		ent->maxs[1] = org[1] + 16;
		ent->maxs[2] = org[2] + 16;
	}
}

  
               
            

                                                                      
                 
               
  
static float CL_LerpPoint(void)
{
	float f;

	if (cl_nettimesyncboundmode.integer == 1)
		cl.time = bound(cl.mtime[1], cl.time, cl.mtime[0]);

	                                                                                           
	if (cl.mtime[0] <= cl.mtime[1])
	{
		cl.time = cl.mtime[0];
		return 1;
	}

	f = (cl.time - cl.mtime[1]) / (cl.mtime[0] - cl.mtime[1]);
	return bound(0, f, 1 + cl_lerpexcess.value);
}

void CL_ClearTempEntities (void)
{
	r_refdef.scene.numtempentities = 0;
	                                      
	if (r_refdef.scene.expandtempentities)
	{
		Con_Printf("CL_NewTempEntity: grow maxtempentities from %i to %i\n", r_refdef.scene.maxtempentities, r_refdef.scene.maxtempentities * 2);
		r_refdef.scene.maxtempentities *= 2;
		r_refdef.scene.tempentities = (entity_render_t *)Mem_Realloc(cls.permanentmempool, r_refdef.scene.tempentities, sizeof(entity_render_t) * r_refdef.scene.maxtempentities);
		r_refdef.scene.expandtempentities = false;
	}
}

entity_render_t *CL_NewTempEntity(double shadertime)
{
	entity_render_t *render;

	if (r_refdef.scene.numentities >= r_refdef.scene.maxentities)
		return NULL;
	if (r_refdef.scene.numtempentities >= r_refdef.scene.maxtempentities)
	{
		r_refdef.scene.expandtempentities = true;                                                                                    
		return NULL;
	}
	render = &r_refdef.scene.tempentities[r_refdef.scene.numtempentities++];
	memset (render, 0, sizeof(*render));
	r_refdef.scene.entities[r_refdef.scene.numentities++] = render;

	render->shadertime = shadertime;
	render->alpha = 1;
	VectorSet(render->colormod, 1, 1, 1);
	VectorSet(render->glowmod, 1, 1, 1);
	return render;
}

void CL_Effect(vec3_t org, int modelindex, int startframe, int framecount, float framerate)
{
	int i;
	cl_effect_t *e;
	if (!modelindex)                
		return;
	if (framerate < 1)
	{
		Con_Printf("CL_Effect: framerate %f is < 1\n", framerate);
		return;
	}
	if (framecount < 1)
	{
		Con_Printf("CL_Effect: framecount %i is < 1\n", framecount);
		return;
	}
	for (i = 0, e = cl.effects;i < cl.max_effects;i++, e++)
	{
		if (e->active)
			continue;
		e->active = true;
		VectorCopy(org, e->origin);
		e->modelindex = modelindex;
		e->starttime = cl.time;
		e->startframe = startframe;
		e->endframe = startframe + framecount;
		e->framerate = framerate;

		e->frame = 0;
		e->frame1time = cl.time;
		e->frame2time = cl.time;
		cl.num_effects = max(cl.num_effects, i + 1);
		break;
	}
}

void CL_AllocLightFlash(entity_render_t *ent, matrix4x4_t *matrix, float radius, float red, float green, float blue, float decay, float lifetime, int cubemapnum, int style, int shadowenable, vec_t corona, vec_t coronasizescale, vec_t ambientscale, vec_t diffusescale, vec_t specularscale, int flags)
{
	int i;
	dlight_t *dl;

                              
	dl = cl.dlights;
	for (i = 0;i < cl.max_dlights;i++, dl++)
		if (!dl->radius)
			break;

	                     
	if (i == cl.max_dlights)
		return;

	                                                                                                                          
	memset (dl, 0, sizeof(*dl));
	cl.num_dlights = max(cl.num_dlights, i + 1);
	Matrix4x4_Normalize(&dl->matrix, matrix);
	dl->ent = ent;
	Matrix4x4_OriginFromMatrix(&dl->matrix, dl->origin);
	CL_FindNonSolidLocation(dl->origin, dl->origin, 6);
	Matrix4x4_SetOrigin(&dl->matrix, dl->origin[0], dl->origin[1], dl->origin[2]);
	dl->radius = radius;
	dl->color[0] = red;
	dl->color[1] = green;
	dl->color[2] = blue;
	dl->initialradius = radius;
	dl->initialcolor[0] = red;
	dl->initialcolor[1] = green;
	dl->initialcolor[2] = blue;
	dl->decay = decay / radius;                                             
	dl->intensity = 1;                             
	if (lifetime)
		dl->die = cl.time + lifetime;
	else
		dl->die = 0;
	if (cubemapnum > 0)
		dpsnprintf(dl->cubemapname, sizeof(dl->cubemapname), "cubemaps/%i", cubemapnum);
	else
		dl->cubemapname[0] = 0;
	dl->style = style;
	dl->shadow = shadowenable;
	dl->corona = corona;
	dl->flags = flags;
	dl->coronasizescale = coronasizescale;
	dl->ambientscale = ambientscale;
	dl->diffusescale = diffusescale;
	dl->specularscale = specularscale;
}

static void CL_DecayLightFlashes(void)
{
	int i, oldmax;
	dlight_t *dl;
	float time;

	time = bound(0, cl.time - cl.oldtime, 0.1);
	oldmax = cl.num_dlights;
	cl.num_dlights = 0;
	for (i = 0, dl = cl.dlights;i < oldmax;i++, dl++)
	{
		if (dl->radius)
		{
			dl->intensity -= time * dl->decay;
			if (cl.time < dl->die && dl->intensity > 0)
			{
				if (cl_dlights_decayradius.integer)
					dl->radius = dl->initialradius * dl->intensity;
				else
					dl->radius = dl->initialradius;
				if (cl_dlights_decaybrightness.integer)
					VectorScale(dl->initialcolor, dl->intensity, dl->color);
				else
					VectorCopy(dl->initialcolor, dl->color);
				cl.num_dlights = i + 1;
			}
			else
				dl->radius = 0;
		}
	}
}

                                 
void CL_RelinkLightFlashes(void)
{
	int i, j, k, l;
	dlight_t *dl;
	float frac, f;
	matrix4x4_t tempmatrix;

	if (r_dynamic.integer)
	{
		for (i = 0, dl = cl.dlights;i < cl.num_dlights && r_refdef.scene.numlights < MAX_DLIGHTS;i++, dl++)
		{
			if (dl->radius)
			{
				tempmatrix = dl->matrix;
				Matrix4x4_Scale(&tempmatrix, dl->radius, 1);
				                                             
				R_RTLight_Update(&dl->rtlight, false, &tempmatrix, dl->color, dl->style, dl->cubemapname, dl->shadow, dl->corona, dl->coronasizescale, dl->ambientscale, dl->diffusescale, dl->specularscale, dl->flags);
				r_refdef.scene.lights[r_refdef.scene.numlights++] = &dl->rtlight;
			}
		}
	}

	if (!cl.lightstyle)
	{
		for (j = 0;j < cl.max_lightstyle;j++)
		{
			r_refdef.scene.rtlightstylevalue[j] = 1;
			r_refdef.scene.lightstylevalue[j] = 256;
		}
		return;
	}

                   
                                                             
	f = cl.time * 10;
	i = (int)floor(f);
	frac = f - i;
	for (j = 0;j < cl.max_lightstyle;j++)
	{
		if (!cl.lightstyle[j].length)
		{
			r_refdef.scene.rtlightstylevalue[j] = 1;
			r_refdef.scene.lightstylevalue[j] = 256;
			continue;
		}
		                             
		if (cl.lightstyle[j].map[0] == '=')
		{
			r_refdef.scene.rtlightstylevalue[j] = atof(cl.lightstyle[j].map + 1);
			if ( r_lerplightstyles.integer || ((int)f - f) < 0.01)
				r_refdef.scene.lightstylevalue[j] = r_refdef.scene.rtlightstylevalue[j];
			continue;
		}
		k = i % cl.lightstyle[j].length;
		l = (i-1) % cl.lightstyle[j].length;
		k = cl.lightstyle[j].map[k] - 'a';
		l = cl.lightstyle[j].map[l] - 'a';
		                                                                 
		                               
		                                                                
		                                                                  
		                                                       
		r_refdef.scene.rtlightstylevalue[j] = ((k*frac)+(l*(1-frac)))*(22/256.0f);
		r_refdef.scene.lightstylevalue[j] = r_lerplightstyles.integer ? (unsigned short)(((k*frac)+(l*(1-frac)))*22) : k*22;
	}
}

static void CL_AddQWCTFFlagModel(entity_t *player, int skin)
{
	int frame = player->render.framegroupblend[0].frame;
	float f;
	entity_render_t *flagrender;
	matrix4x4_t flagmatrix;

	                                  
	f = 14;
	if (frame >= 29 && frame <= 40)
	{
		if (frame >= 29 && frame <= 34)
		{         
			if      (frame == 29) f = f + 2;
			else if (frame == 30) f = f + 8;
			else if (frame == 31) f = f + 12;
			else if (frame == 32) f = f + 11;
			else if (frame == 33) f = f + 10;
			else if (frame == 34) f = f + 4;
		}
		else if (frame >= 35 && frame <= 40)
		{        
			if      (frame == 35) f = f + 2;
			else if (frame == 36) f = f + 10;
			else if (frame == 37) f = f + 10;
			else if (frame == 38) f = f + 8;
			else if (frame == 39) f = f + 4;
			else if (frame == 40) f = f + 2;
		}
	}
	else if (frame >= 103 && frame <= 118)
	{
		if      (frame >= 103 && frame <= 104) f = f + 6;              
		else if (frame >= 105 && frame <= 106) f = f + 6;         
		else if (frame >= 107 && frame <= 112) f = f + 7;                
		else if (frame >= 112 && frame <= 118) f = f + 7;              
	}
	                                    

	flagrender = CL_NewTempEntity(player->render.shadertime);
	if (!flagrender)
		return;

	flagrender->model = CL_GetModelByIndex(cl.qw_modelindex_flag);
	flagrender->skinnum = skin;
	flagrender->alpha = 1;
	VectorSet(flagrender->colormod, 1, 1, 1);
	VectorSet(flagrender->glowmod, 1, 1, 1);
	                                       
	Matrix4x4_CreateFromQuakeEntity(&flagmatrix, -f, -22, 0, 0, 0, -45, 1);
	Matrix4x4_Concat(&flagrender->matrix, &player->render.matrix, &flagmatrix);
	CL_UpdateRenderEntity(flagrender);
}

matrix4x4_t viewmodelmatrix_withbob;
matrix4x4_t viewmodelmatrix_nobob;

static const vec3_t muzzleflashorigin = {18, 0, 0};

void CL_SetEntityColormapColors(entity_render_t *ent, int colormap)
{
	const unsigned char *cbcolor;
	if (colormap >= 0)
	{
		cbcolor = palette_rgb_pantscolormap[colormap & 0xF];
		VectorScale(cbcolor, (1.0f / 255.0f), ent->colormap_pantscolor);
		cbcolor = palette_rgb_shirtcolormap[(colormap & 0xF0) >> 4];
		VectorScale(cbcolor, (1.0f / 255.0f), ent->colormap_shirtcolor);
	}
	else
	{
		VectorClear(ent->colormap_pantscolor);
		VectorClear(ent->colormap_shirtcolor);
	}
}

                                                                                           
static void CL_UpdateNetworkEntity(entity_t *e, int recursionlimit, qboolean interpolate)
{
	const matrix4x4_t *matrix;
	matrix4x4_t blendmatrix, tempmatrix, matrix2;
	int frame;
	vec_t origin[3], angles[3], lerp;
	entity_t *t;
	entity_render_t *r;
	                                          
	                                  
	                                   
	if (!e->state_current.active || e == cl.entities)
		return;
	if (recursionlimit < 1)
		return;
	e->render.alpha = e->state_current.alpha * (1.0f / 255.0f);                       
	e->render.scale = e->state_current.scale * (1.0f / 16.0f);                       
	e->render.flags = e->state_current.flags;
	e->render.effects = e->state_current.effects;
	VectorScale(e->state_current.colormod, (1.0f / 32.0f), e->render.colormod);
	VectorScale(e->state_current.glowmod, (1.0f / 32.0f), e->render.glowmod);
	if(e >= cl.entities && e < cl.entities + cl.num_entities)
		e->render.entitynumber = e - cl.entities;
	else
		e->render.entitynumber = 0;
	if (e->state_current.flags & RENDER_COLORMAPPED)
		CL_SetEntityColormapColors(&e->render, e->state_current.colormap);
	else if (e->state_current.colormap > 0 && e->state_current.colormap <= cl.maxclients && cl.scores != NULL)
		CL_SetEntityColormapColors(&e->render, cl.scores[e->state_current.colormap-1].colors);
	else
		CL_SetEntityColormapColors(&e->render, -1);
	e->render.skinnum = e->state_current.skin;
	if (e->state_current.tagentity)
	{
		                                                         
		                                                     
		if (e->state_current.tagentity >= cl.num_entities)
			return;
		t = cl.entities + e->state_current.tagentity;
		                                         
		if (t->state_current.active)
		{
			                          
			CL_UpdateNetworkEntity(t, recursionlimit - 1, interpolate);
			r = &t->render;
		}
		else
		{
			                                                     
			                                                    
			if(!cl.csqc_server2csqcentitynumber[e->state_current.tagentity])
				return;
			r = cl.csqcrenderentities + cl.csqc_server2csqcentitynumber[e->state_current.tagentity];
			if(!r->entitynumber)
				return;                                                  
		}
		                              
		matrix = &r->matrix;
		                                               
		e->render.flags |= r->flags & (RENDER_EXTERIORMODEL | RENDER_VIEWMODEL);
		                                                                    
		if (e->state_current.tagentity && e->state_current.tagindex >= 1 && r->model)
		{
			if(!Mod_Alias_GetTagMatrix(r->model, r->frameblend, r->skeleton, e->state_current.tagindex - 1, &blendmatrix))                 
			{
				                                                 
				Matrix4x4_Concat(&tempmatrix, &r->matrix, &blendmatrix);
				                                 
				matrix = &tempmatrix;
			}
		}
	}
	else if (e->render.flags & RENDER_VIEWMODEL)
	{
		                                       
		if (e->render.effects & EF_NOGUNBOB)
			matrix = &viewmodelmatrix_nobob;                           
		else
			matrix = &viewmodelmatrix_withbob;                              
	}
	else
	{
		                                          
		matrix = &identitymatrix;
	}

	                
	                                                                           
	                                                                       
	                                                                       
	                                                                          
	                                              
	if (cl_nolerp.integer || cls.timedemo)
		interpolate = false;
	if (e == cl.entities + cl.playerentity && cl.movement_predicted && (!cl.fixangle[1] || !cl.fixangle[0]))
	{
		VectorCopy(cl.movement_origin, origin);
		VectorSet(angles, 0, cl.viewangles[1], 0);
	}
	else if (interpolate && e->persistent.lerpdeltatime > 0 && (lerp = (cl.time - e->persistent.lerpstarttime) / e->persistent.lerpdeltatime) < 1 + cl_lerpexcess.value)
	{
		                                    
		lerp = max(0, lerp);
		VectorLerp(e->persistent.oldorigin, lerp, e->persistent.neworigin, origin);
#if 0
		                                                
		VectorSubtract(e->persistent.newangles, e->persistent.oldangles, delta);
		if (delta[0] < -180) delta[0] += 360;else if (delta[0] >= 180) delta[0] -= 360;
		if (delta[1] < -180) delta[1] += 360;else if (delta[1] >= 180) delta[1] -= 360;
		if (delta[2] < -180) delta[2] += 360;else if (delta[2] >= 180) delta[2] -= 360;
		VectorMA(e->persistent.oldangles, lerp, delta, angles);
#else
		{
			vec3_t f0, u0, f1, u1;
			AngleVectors(e->persistent.oldangles, f0, NULL, u0);
			AngleVectors(e->persistent.newangles, f1, NULL, u1);
			VectorMAM(1-lerp, f0, lerp, f1, f0);
			VectorMAM(1-lerp, u0, lerp, u1, u0);
			AnglesFromVectors(angles, f0, u0, false);
		}
#endif
	}
	else
	{
		                   
		VectorCopy(e->persistent.neworigin, origin);
		VectorCopy(e->persistent.newangles, angles);
	}

	                                  
	frame = e->state_current.frame;
	e->render.model = CL_GetModelByIndex(e->state_current.modelindex);
	if (e->render.model)
	{
		if (e->render.skinnum >= e->render.model->numskins)
			e->render.skinnum = 0;
		if (frame >= e->render.model->numframes)
			frame = 0;
		                                         
		                                                                                          
		if (!(e->render.effects & 0xFF800000))
			e->render.effects |= e->render.model->effects;
		                                                                               
		if (e->render.model->type == mod_alias)
			angles[0] = -angles[0];
		if ((e->render.effects & EF_SELECTABLE) && cl.cmd.cursor_entitynumber == e->state_current.number)
		{
			VectorScale(e->render.colormod, 2, e->render.colormod);
			VectorScale(e->render.glowmod, 2, e->render.glowmod);
		}
	}
	                                                                               
	else if (e->state_current.lightpflags & PFLAGS_FULLDYNAMIC)
		angles[0] = -angles[0];
		                                                

	if ((e->render.effects & EF_ROTATE) && !(e->render.flags & RENDER_VIEWMODEL))
	{
		angles[1] = ANGLEMOD(100*cl.time);
		if (cl_itembobheight.value)
			origin[2] += (cos(cl.time * cl_itembobspeed.value * (2.0 * M_PI)) + 1.0) * 0.5 * cl_itembobheight.value;
	}

	                 
	e->render.skeleton = NULL;
	if (e->render.flags & RENDER_COMPLEXANIMATION)
	{
		e->render.framegroupblend[0] = e->state_current.framegroupblend[0];
		e->render.framegroupblend[1] = e->state_current.framegroupblend[1];
		e->render.framegroupblend[2] = e->state_current.framegroupblend[2];
		e->render.framegroupblend[3] = e->state_current.framegroupblend[3];
		if (e->state_current.skeletonobject.model && e->state_current.skeletonobject.relativetransforms)
			e->render.skeleton = &e->state_current.skeletonobject;
	}
	else if (e->render.framegroupblend[0].frame == frame)
	{
		                             
		e->render.framegroupblend[0].lerp = 1;
		e->render.framegroupblend[1].lerp = 0;
		if (e->render.framegroupblend[0].start > e->render.framegroupblend[1].start)
		{
			                                                    
			                                                          
			                                    
			float maxdelta = cl_lerpanim_maxdelta_server.value;
			if(e->render.model)
			if(e->render.model->animscenes)
			if(e->render.model->animscenes[e->render.framegroupblend[0].frame].framecount > 1 || e->render.model->animscenes[e->render.framegroupblend[1].frame].framecount > 1)
				maxdelta = cl_lerpanim_maxdelta_framegroups.value;
			maxdelta = max(maxdelta, cl.mtime[0] - cl.mtime[1]);
			e->render.framegroupblend[0].lerp = (cl.time - e->render.framegroupblend[0].start) / min(e->render.framegroupblend[0].start - e->render.framegroupblend[1].start, maxdelta);
			e->render.framegroupblend[0].lerp = bound(0, e->render.framegroupblend[0].lerp, 1);
			e->render.framegroupblend[1].lerp = 1 - e->render.framegroupblend[0].lerp;
		}
	}
	else
	{
		                         
		e->render.framegroupblend[1] = e->render.framegroupblend[0];
		e->render.framegroupblend[1].lerp = 1;
		e->render.framegroupblend[0].frame = frame;
		e->render.framegroupblend[0].start = cl.time;
		e->render.framegroupblend[0].lerp = 0;
	}

	                           
	if (matrix)
	{
		                                                            
		                                        
		Matrix4x4_CreateFromQuakeEntity(&matrix2, origin[0], origin[1], origin[2], angles[0], angles[1], angles[2], e->render.scale);
		                                                             
		Matrix4x4_Concat(&e->render.matrix, matrix, &matrix2);
		                                     
		Matrix4x4_OriginFromMatrix(&e->render.matrix, origin);
	}
	else
	{
		                                            
		Matrix4x4_CreateFromQuakeEntity(&e->render.matrix, origin[0], origin[1], origin[2], angles[0], angles[1], angles[2], e->render.scale);
	}

	                                                   
	if (gamemode == GAME_TENEBRAE && e->render.model && e->render.model->type == mod_sprite)
		e->render.flags |= RENDER_ADDITIVE;
	                                                  
	if (e->state_current.number == cl.viewentity)
		e->render.flags |= RENDER_EXTERIORMODEL;
	                           
	if(!r_fullbright.integer)
	{
		if (!(e->render.effects & EF_FULLBRIGHT))
			e->render.flags |= RENDER_LIGHT;
		else if(r_equalize_entities_fullbright.integer)
			e->render.flags |= RENDER_LIGHT | RENDER_EQUALIZE;
	}
	                                                          
	if (!(e->render.effects & (EF_NOSHADOW | EF_ADDITIVE | EF_NODEPTHTEST))
	 && (e->render.alpha >= 1)
	 && !(e->render.flags & RENDER_VIEWMODEL)
	 && (!(e->render.flags & RENDER_EXTERIORMODEL) || (!cl.intermission && cls.protocol != PROTOCOL_NEHAHRAMOVIE && !cl_noplayershadow.integer)))
		e->render.flags |= RENDER_SHADOW;
	if (e->render.flags & RENDER_VIEWMODEL)
		e->render.flags |= RENDER_NOSELFSHADOW;
	if (e->render.effects & EF_NOSELFSHADOW)
		e->render.flags |= RENDER_NOSELFSHADOW;
	if (e->render.effects & EF_NODEPTHTEST)
		e->render.flags |= RENDER_NODEPTHTEST;
	if (e->render.effects & EF_ADDITIVE)
		e->render.flags |= RENDER_ADDITIVE;
	if (e->render.effects & EF_DOUBLESIDED)
		e->render.flags |= RENDER_DOUBLESIDED;
	if (e->render.effects & EF_DYNAMICMODELLIGHT)
		e->render.flags |= RENDER_DYNAMICMODELLIGHT;

	                              
	e->render.allowdecals = true;
	CL_UpdateRenderEntity(&e->render);
}

                                          
static void CL_UpdateNetworkEntityTrail(entity_t *e)
{
	effectnameindex_t trailtype;
	vec3_t origin;

	                                                                          
	                                            
	if (e->render.model && e->render.model->soundfromcenter)
	{
		vec3_t o;
		VectorMAM(0.5f, e->render.model->normalmins, 0.5f, e->render.model->normalmaxs, o);
		Matrix4x4_Transform(&e->render.matrix, o, origin);
	}
	else
		Matrix4x4_OriginFromMatrix(&e->render.matrix, origin);

	                                                                      
	                            
	trailtype = EFFECT_NONE;
	                                                            
	if (e->render.effects & (EF_BRIGHTFIELD | EF_FLAME | EF_STARDUST))
	{
		if (e->render.effects & EF_BRIGHTFIELD)
		{
			if (IS_NEXUIZ_DERIVED(gamemode))
				trailtype = EFFECT_TR_NEXUIZPLASMA;
			else
				CL_EntityParticles(e);
		}
		if (e->render.effects & EF_FLAME)
			CL_ParticleTrail(EFFECT_EF_FLAME, bound(0, cl.time - cl.oldtime, 0.1), origin, origin, vec3_origin, vec3_origin, NULL, 0, false, true, NULL, NULL, 1);
		if (e->render.effects & EF_STARDUST)
			CL_ParticleTrail(EFFECT_EF_STARDUST, bound(0, cl.time - cl.oldtime, 0.1), origin, origin, vec3_origin, vec3_origin, NULL, 0, false, true, NULL, NULL, 1);
	}
	if (e->render.internaleffects & (INTEF_FLAG1QW | INTEF_FLAG2QW))
	{
		                                        
		CL_AddQWCTFFlagModel(e, (e->render.internaleffects & INTEF_FLAG2QW) != 0);
	}
	                              
	if (e->persistent.muzzleflash > 0)
		e->persistent.muzzleflash -= bound(0, cl.time - cl.oldtime, 0.1) * 20;
	                                                            
	if (e->render.effects && !(e->render.flags & RENDER_VIEWMODEL))
	{
		if (e->render.effects & EF_GIB)
			trailtype = EFFECT_TR_BLOOD;
		else if (e->render.effects & EF_ZOMGIB)
			trailtype = EFFECT_TR_SLIGHTBLOOD;
		else if (e->render.effects & EF_TRACER)
			trailtype = EFFECT_TR_WIZSPIKE;
		else if (e->render.effects & EF_TRACER2)
			trailtype = EFFECT_TR_KNIGHTSPIKE;
		else if (e->render.effects & EF_ROCKET)
			trailtype = EFFECT_TR_ROCKET;
		else if (e->render.effects & EF_GRENADE)
		{
			                                                                                  
			trailtype = e->render.alpha == -1 ? EFFECT_TR_NEHAHRASMOKE : EFFECT_TR_GRENADE;
		}
		else if (e->render.effects & EF_TRACER3)
			trailtype = EFFECT_TR_VORESPIKE;
	}
	            
	if (e->render.flags & RENDER_GLOWTRAIL)
		trailtype = EFFECT_TR_GLOWTRAIL;
	if (e->state_current.traileffectnum)
		trailtype = (effectnameindex_t)e->state_current.traileffectnum;
	                                                                       
	if (trailtype && e->persistent.trail_allowed)
	{
		float len;
		vec3_t vel;
		VectorSubtract(e->state_current.origin, e->state_previous.origin, vel);
		len = e->state_current.time - e->state_previous.time;
		if (len > 0)
			len = 1.0f / len;
		VectorScale(vel, len, vel);
		                                                                                                                                       
		CL_ParticleTrail(trailtype, bound(0, cl.time - cl.oldtime, 0.1), e->persistent.trail_origin, origin, vel, vel, e, e->state_current.glowcolor, false, true, NULL, NULL, 1);
	}
	                                                                     
	                                     
	e->persistent.trail_allowed = true;
	VectorCopy(origin, e->persistent.trail_origin);
}


  
               
                     
               
  
void CL_UpdateViewEntities(void)
{
	int i;
	                                                                  
	for (i = 1;i < cl.num_entities;i++)
	{
		if (cl.entities_active[i])
		{
			entity_t *ent = cl.entities + i;
			if ((ent->render.flags & RENDER_VIEWMODEL) || ent->state_current.tagentity)
				CL_UpdateNetworkEntity(ent, 32, true);
		}
	}
	                                                            
	CL_UpdateNetworkEntity(&cl.viewent, 32, true);
}

  
               
                                 
               
  
static void CL_UpdateNetworkCollisionEntities(void)
{
	entity_t *ent;
	int i;

	                                      
	cl.num_brushmodel_entities = 0;
	for (i = cl.maxclients + 1;i < cl.num_entities;i++)
	{
		if (cl.entities_active[i])
		{
			ent = cl.entities + i;
			if (ent->state_current.active && ent->render.model && ent->render.model->name[0] == '*' && ent->render.model->TraceBox)
			{
				                                          
				CL_UpdateNetworkEntity(ent, 32, false);
				cl.brushmodel_entities[cl.num_brushmodel_entities++] = i;
			}
		}
	}
}

  
               
                        
               
  
static void CL_UpdateNetworkEntities(void)
{
	entity_t *ent;
	int i;

	                                      
	for (i = 1;i < cl.num_entities;i++)
	{
		if (cl.entities_active[i])
		{
			ent = cl.entities + i;
			if (ent->state_current.active)
			{
				CL_UpdateNetworkEntity(ent, 32, true);
				                                               
				if (!(ent->render.flags & RENDER_VIEWMODEL))
					CL_UpdateNetworkEntityTrail(ent);
			}
			else
			{
				R_DecalSystem_Reset(&ent->render.decalsystem);
				cl.entities_active[i] = false;
			}
		}
	}
}

static void CL_UpdateViewModel(void)
{
	entity_t *ent;
	ent = &cl.viewent;
	ent->state_previous = ent->state_current;
	ent->state_current = defaultstate;
	ent->state_current.time = cl.time;
	ent->state_current.number = (unsigned short)-1;
	ent->state_current.active = true;
	ent->state_current.modelindex = cl.stats[STAT_WEAPON];
	ent->state_current.frame = cl.stats[STAT_WEAPONFRAME];
	ent->state_current.flags = RENDER_VIEWMODEL;
	if ((cl.stats[STAT_HEALTH] <= 0 && cl_deathnoviewmodel.integer) || cl.intermission)
		ent->state_current.modelindex = 0;
	else if (cl.stats[STAT_ITEMS] & IT_INVISIBILITY)
	{
		if (gamemode == GAME_TRANSFUSION)
			ent->state_current.alpha = 128;
		else
			ent->state_current.modelindex = 0;
	}
	ent->state_current.alpha = cl.entities[cl.viewentity].state_current.alpha;
	ent->state_current.effects = EF_NOSHADOW | (cl.entities[cl.viewentity].state_current.effects & (EF_ADDITIVE | EF_FULLBRIGHT | EF_NODEPTHTEST | EF_NOGUNBOB));

	                                                                
	if (ent->state_previous.modelindex != ent->state_current.modelindex)
	{
		ent->render.framegroupblend[0].frame = ent->render.framegroupblend[1].frame = ent->state_current.frame;
		ent->render.framegroupblend[0].start = ent->render.framegroupblend[1].start = cl.time;
		ent->render.framegroupblend[0].lerp = 1;ent->render.framegroupblend[1].lerp = 0;
	}
	CL_UpdateNetworkEntity(ent, 32, true);
}

                                                                                                               
static void CL_LinkNetworkEntity(entity_t *e)
{
	effectnameindex_t trailtype;
	vec3_t origin;
	vec3_t dlightcolor;
	vec_t dlightradius;
	char vabuf[1024];

	                                   
	if (!e->state_current.active || e == cl.entities)
		return;
	if (e->state_current.tagentity)
	{
		                                                     
		if (e->state_current.tagentity >= cl.num_entities)
			return;
		                                         
		if (!cl.entities[e->state_current.tagentity].state_current.active)
		{
			if(!cl.csqc_server2csqcentitynumber[e->state_current.tagentity])
				return;
			if(!cl.csqcrenderentities[cl.csqc_server2csqcentitynumber[e->state_current.tagentity]].entitynumber)
				return;
			                                                            
		}
	}

	                                                    
	if (e->render.model && e->render.model->soundfromcenter)
	{
		                                                                      
		vec3_t o;
		VectorMAM(0.5f, e->render.model->normalmins, 0.5f, e->render.model->normalmaxs, o);
		Matrix4x4_Transform(&e->render.matrix, o, origin);
	}
	else
		Matrix4x4_OriginFromMatrix(&e->render.matrix, origin);
	trailtype = EFFECT_NONE;
	dlightradius = 0;
	dlightcolor[0] = 0;
	dlightcolor[1] = 0;
	dlightcolor[2] = 0;
	                                                            
	if (e->render.effects & (EF_BRIGHTFIELD | EF_DIMLIGHT | EF_BRIGHTLIGHT | EF_RED | EF_BLUE | EF_FLAME | EF_STARDUST))
	{
		if (e->render.effects & EF_BRIGHTFIELD)
		{
			if (IS_NEXUIZ_DERIVED(gamemode))
				trailtype = EFFECT_TR_NEXUIZPLASMA;
		}
		if (e->render.effects & EF_DIMLIGHT)
		{
			dlightradius = max(dlightradius, 200);
			dlightcolor[0] += 1.50f;
			dlightcolor[1] += 1.50f;
			dlightcolor[2] += 1.50f;
		}
		if (e->render.effects & EF_BRIGHTLIGHT)
		{
			dlightradius = max(dlightradius, 400);
			dlightcolor[0] += 3.00f;
			dlightcolor[1] += 3.00f;
			dlightcolor[2] += 3.00f;
		}
		                          
		if (e->render.effects & EF_RED)       
		{
			dlightradius = max(dlightradius, 200);
			dlightcolor[0] += 1.50f;
			dlightcolor[1] += 0.15f;
			dlightcolor[2] += 0.15f;
		}
		if (e->render.effects & EF_BLUE)        
		{
			dlightradius = max(dlightradius, 200);
			dlightcolor[0] += 0.15f;
			dlightcolor[1] += 0.15f;
			dlightcolor[2] += 1.50f;
		}
		if (e->render.effects & EF_FLAME)
			CL_ParticleTrail(EFFECT_EF_FLAME, 1, origin, origin, vec3_origin, vec3_origin, NULL, 0, true, false, NULL, NULL, 1);
		if (e->render.effects & EF_STARDUST)
			CL_ParticleTrail(EFFECT_EF_STARDUST, 1, origin, origin, vec3_origin, vec3_origin, NULL, 0, true, false, NULL, NULL, 1);
	}
	                                                   
	if (e->persistent.muzzleflash > 0 && r_refdef.scene.numlights < MAX_DLIGHTS)
	{
		vec3_t v2;
		vec3_t color;
		trace_t trace;
		matrix4x4_t tempmatrix;
		Matrix4x4_Transform(&e->render.matrix, muzzleflashorigin, v2);
		trace = CL_TraceLine(origin, v2, MOVE_NOMONSTERS, NULL, SUPERCONTENTS_SOLID | SUPERCONTENTS_SKY, 0, 0, collision_extendmovelength.value, true, false, NULL, false, false);
		Matrix4x4_Normalize(&tempmatrix, &e->render.matrix);
		Matrix4x4_SetOrigin(&tempmatrix, trace.endpos[0], trace.endpos[1], trace.endpos[2]);
		Matrix4x4_Scale(&tempmatrix, 150, 1);
		VectorSet(color, e->persistent.muzzleflash * 4.0f, e->persistent.muzzleflash * 4.0f, e->persistent.muzzleflash * 4.0f);
		R_RTLight_Update(&r_refdef.scene.templights[r_refdef.scene.numlights], false, &tempmatrix, color, -1, NULL, true, 0, 0.25, 0, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
		r_refdef.scene.lights[r_refdef.scene.numlights] = &r_refdef.scene.templights[r_refdef.scene.numlights];r_refdef.scene.numlights++;
	}
	                                                         
	if (e->render.model && e->render.effects && !(e->render.flags & RENDER_VIEWMODEL))
	{
		if (e->render.effects & EF_GIB)
			trailtype = EFFECT_TR_BLOOD;
		else if (e->render.effects & EF_ZOMGIB)
			trailtype = EFFECT_TR_SLIGHTBLOOD;
		else if (e->render.effects & EF_TRACER)
			trailtype = EFFECT_TR_WIZSPIKE;
		else if (e->render.effects & EF_TRACER2)
			trailtype = EFFECT_TR_KNIGHTSPIKE;
		else if (e->render.effects & EF_ROCKET)
			trailtype = EFFECT_TR_ROCKET;
		else if (e->render.effects & EF_GRENADE)
		{
			                                                                                  
			trailtype = e->render.alpha == -1 ? EFFECT_TR_NEHAHRASMOKE : EFFECT_TR_GRENADE;
		}
		else if (e->render.effects & EF_TRACER3)
			trailtype = EFFECT_TR_VORESPIKE;
	}
	                               
	if (e->state_current.glowsize)
	{
		                                                    
		                                  
		dlightradius = max(dlightradius, e->state_current.glowsize * 4);
		VectorMA(dlightcolor, (1.0f / 255.0f), palette_rgb[e->state_current.glowcolor], dlightcolor);
	}
	                 
	if ((e->state_current.lightpflags & PFLAGS_FULLDYNAMIC) && r_refdef.scene.numlights < MAX_DLIGHTS)
	{
		matrix4x4_t dlightmatrix;
		vec4_t light;
		VectorScale(e->state_current.light, (1.0f / 256.0f), light);
		light[3] = e->state_current.light[3];
		if (light[0] == 0 && light[1] == 0 && light[2] == 0)
			VectorSet(light, 1, 1, 1);
		if (light[3] == 0)
			light[3] = 350;
		                                                                                            
		Matrix4x4_Normalize(&dlightmatrix, &e->render.matrix);
		Matrix4x4_Scale(&dlightmatrix, light[3], 1);
		R_RTLight_Update(&r_refdef.scene.templights[r_refdef.scene.numlights], false, &dlightmatrix, light, e->state_current.lightstyle, e->state_current.skin > 0 ? va(vabuf, sizeof(vabuf), "cubemaps/%i", e->state_current.skin) : NULL, !(e->state_current.lightpflags & PFLAGS_NOSHADOW), (e->state_current.lightpflags & PFLAGS_CORONA) != 0, 0.25, 0, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
		r_refdef.scene.lights[r_refdef.scene.numlights] = &r_refdef.scene.templights[r_refdef.scene.numlights];r_refdef.scene.numlights++;
	}
	                       
	else if (dlightradius > 0 && (dlightcolor[0] || dlightcolor[1] || dlightcolor[2]) && !(e->render.flags & RENDER_VIEWMODEL) && r_refdef.scene.numlights < MAX_DLIGHTS)
	{
		matrix4x4_t dlightmatrix;
		Matrix4x4_Normalize(&dlightmatrix, &e->render.matrix);
		                                                       
		                                                                            
		                                                   
		Matrix4x4_Scale(&dlightmatrix, dlightradius, 1);
		R_RTLight_Update(&r_refdef.scene.templights[r_refdef.scene.numlights], false, &dlightmatrix, dlightcolor, -1, NULL, true, 1, 0.25, 0, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
		r_refdef.scene.lights[r_refdef.scene.numlights] = &r_refdef.scene.templights[r_refdef.scene.numlights];r_refdef.scene.numlights++;
	}
	                 
	if (e->render.flags & RENDER_GLOWTRAIL)
		trailtype = EFFECT_TR_GLOWTRAIL;
	if (e->state_current.traileffectnum)
		trailtype = (effectnameindex_t)e->state_current.traileffectnum;
	if (trailtype)
		CL_ParticleTrail(trailtype, 1, origin, origin, vec3_origin, vec3_origin, NULL, e->state_current.glowcolor, true, false, NULL, NULL, 1);

	                                                                 
	                                                                  
	if (e->render.model && !(e->render.effects & EF_NODRAW) && r_refdef.scene.numentities < r_refdef.scene.maxentities)
		r_refdef.scene.entities[r_refdef.scene.numentities++] = &e->render;
	                                                                
	                                      
}

static void CL_RelinkWorld(void)
{
	entity_t *ent = &cl.entities[0];
	                                     
	ent->render.matrix = identitymatrix;
	ent->render.flags = RENDER_SHADOW;
	if (!r_fullbright.integer)
		ent->render.flags |= RENDER_LIGHT;
	VectorSet(ent->render.colormod, 1, 1, 1);
	VectorSet(ent->render.glowmod, 1, 1, 1);
	ent->render.allowdecals = true;
	CL_UpdateRenderEntity(&ent->render);
	r_refdef.scene.worldentity = &ent->render;
	r_refdef.scene.worldmodel = cl.worldmodel;

	                                              
	if (ent->render.model && ent->render.model->brush.isq2bsp)
		ent->render.framegroupblend[0].frame = (int)(cl.time * 2.0f);
}

static void CL_RelinkStaticEntities(void)
{
	int i;
	entity_t *e;
	for (i = 0, e = cl.static_entities;i < cl.num_static_entities && r_refdef.scene.numentities < r_refdef.scene.maxentities;i++, e++)
	{
		e->render.flags = 0;
		                                                                    
		                                     
		e->render.model = CL_GetModelByIndex(e->state_baseline.modelindex);
		                           
		if(!r_fullbright.integer)
		{
			if (!(e->render.effects & EF_FULLBRIGHT))
				e->render.flags |= RENDER_LIGHT;
			else if(r_equalize_entities_fullbright.integer)
				e->render.flags |= RENDER_LIGHT | RENDER_EQUALIZE;
		}
		                                                          
		if (!(e->render.effects & (EF_NOSHADOW | EF_ADDITIVE | EF_NODEPTHTEST)) && (e->render.alpha >= 1))
			e->render.flags |= RENDER_SHADOW;
		VectorSet(e->render.colormod, 1, 1, 1);
		VectorSet(e->render.glowmod, 1, 1, 1);
		VM_FrameBlendFromFrameGroupBlend(e->render.frameblend, e->render.framegroupblend, e->render.model, cl.time);
		e->render.allowdecals = true;
		CL_UpdateRenderEntity(&e->render);
		r_refdef.scene.entities[r_refdef.scene.numentities++] = &e->render;
	}
}

  
               
                 
               
  
static void CL_RelinkNetworkEntities(void)
{
	entity_t *ent;
	int i;

	                                      
	for (i = 1;i < cl.num_entities;i++)
	{
		if (cl.entities_active[i])
		{
			ent = cl.entities + i;
			if (ent->state_current.active)
				CL_LinkNetworkEntity(ent);
			else
				cl.entities_active[i] = false;
		}
	}
}

static void CL_RelinkEffects(void)
{
	int i, intframe;
	cl_effect_t *e;
	entity_render_t *entrender;
	float frame;

	for (i = 0, e = cl.effects;i < cl.num_effects;i++, e++)
	{
		if (e->active)
		{
			frame = (cl.time - e->starttime) * e->framerate + e->startframe;
			intframe = (int)frame;
			if (intframe < 0 || intframe >= e->endframe)
			{
				memset(e, 0, sizeof(*e));
				while (cl.num_effects > 0 && !cl.effects[cl.num_effects - 1].active)
					cl.num_effects--;
				continue;
			}

			if (intframe != e->frame)
			{
				e->frame = intframe;
				e->frame1time = e->frame2time;
				e->frame2time = cl.time;
			}

			                                                  
			                                                             
			if (r_draweffects.integer && (entrender = CL_NewTempEntity(e->starttime)))
			{
				                      
				entrender->framegroupblend[0].frame = intframe;
				entrender->framegroupblend[0].lerp = 1 - frame - intframe;
				entrender->framegroupblend[0].start = e->frame1time;
				if (intframe + 1 >= e->endframe)
				{
					entrender->framegroupblend[1].frame = 0;             
					entrender->framegroupblend[1].lerp = 0;
					entrender->framegroupblend[1].start = 0;
				}
				else
				{
					entrender->framegroupblend[1].frame = intframe + 1;
					entrender->framegroupblend[1].lerp = frame - intframe;
					entrender->framegroupblend[1].start = e->frame2time;
				}

				               
				entrender->model = CL_GetModelByIndex(e->modelindex);
				entrender->alpha = 1;
				VectorSet(entrender->colormod, 1, 1, 1);
				VectorSet(entrender->glowmod, 1, 1, 1);

				Matrix4x4_CreateFromQuakeEntity(&entrender->matrix, e->origin[0], e->origin[1], e->origin[2], 0, 0, 0, 1);
				CL_UpdateRenderEntity(entrender);
			}
		}
	}
}

void CL_Beam_CalculatePositions(const beam_t *b, vec3_t start, vec3_t end)
{
	VectorCopy(b->start, start);
	VectorCopy(b->end, end);

	                                                       
	if (b->entity == cl.viewentity)
	{
		if (cl_beams_quakepositionhack.integer && !chase_active.integer)
		{
			                                                              
			                                                                  
			       
			                                                             
			                                                                  
			                                                               
			Matrix4x4_OriginFromMatrix(&cl.entities[cl.viewentity].render.matrix, start);
		}
		if (cl_beams_instantaimhack.integer)
		{
			vec3_t dir, localend;
			vec_t len;
			                                                           
			             
			VectorSubtract(end, start, dir);
			len = VectorLength(dir);
			VectorNormalize(dir);
			VectorSet(localend, len, 0, 0);
			Matrix4x4_Transform(&r_refdef.view.matrix, localend, end);
		}
	}
}

void CL_RelinkBeams(void)
{
	int i;
	beam_t *b;
	vec3_t dist, org, start, end;
	float d;
	entity_render_t *entrender;
	double yaw, pitch;
	float forward;
	matrix4x4_t tempmatrix;

	for (i = 0, b = cl.beams;i < cl.num_beams;i++, b++)
	{
		if (!b->model)
			continue;
		if (b->endtime < cl.time)
		{
			b->model = NULL;
			continue;
		}

		CL_Beam_CalculatePositions(b, start, end);

		if (b->lightning)
		{
			if (cl_beams_lightatend.integer && r_refdef.scene.numlights < MAX_DLIGHTS)
			{
				                                                             
				vec3_t dlightcolor;
				VectorSet(dlightcolor, 0.3, 0.7, 1);
				Matrix4x4_CreateFromQuakeEntity(&tempmatrix, end[0], end[1], end[2], 0, 0, 0, 200);
				R_RTLight_Update(&r_refdef.scene.templights[r_refdef.scene.numlights], false, &tempmatrix, dlightcolor, -1, NULL, true, 1, 0.25, 1, 0, 0, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
				r_refdef.scene.lights[r_refdef.scene.numlights] = &r_refdef.scene.templights[r_refdef.scene.numlights];r_refdef.scene.numlights++;
			}
			if (cl_beams_polygons.integer)
			{
				CL_Beam_AddPolygons(b);
				continue;
			}
		}

		                          
		                                                               
		VectorSubtract(end, start, dist);
		if (dist[1] == 0 && dist[0] == 0)
		{
			yaw = 0;
			if (dist[2] > 0)
				pitch = 90;
			else
				pitch = 270;
		}
		else
		{
			yaw = atan2(dist[1], dist[0]) * 180 / M_PI;
			if (yaw < 0)
				yaw += 360;

			forward = sqrt (dist[0]*dist[0] + dist[1]*dist[1]);
			pitch = atan2(dist[2], forward) * 180 / M_PI;
			if (pitch < 0)
				pitch += 360;
		}

		                                     
		VectorCopy (start, org);
		d = VectorNormalizeLength(dist);
		while (d > 0)
		{
			entrender = CL_NewTempEntity (0);
			if (!entrender)
				return;
			entrender->model = b->model;
			Matrix4x4_CreateFromQuakeEntity(&entrender->matrix, org[0], org[1], org[2], -pitch, yaw, lhrandom(0, 360), 1);
			CL_UpdateRenderEntity(entrender);
			VectorMA(org, 30, dist, org);
			d -= 30;
		}
	}

	while (cl.num_beams > 0 && !cl.beams[cl.num_beams - 1].model)
		cl.num_beams--;
}

static void CL_RelinkQWNails(void)
{
	int i;
	vec_t *v;
	entity_render_t *entrender;

	for (i = 0;i < cl.qw_num_nails;i++)
	{
		v = cl.qw_nails[i];

		                                                  
		                                                             
		if (!(entrender = CL_NewTempEntity(0)))
			continue;

		               
		entrender->model = CL_GetModelByIndex(cl.qw_modelindex_spike);
		entrender->alpha = 1;
		VectorSet(entrender->colormod, 1, 1, 1);
		VectorSet(entrender->glowmod, 1, 1, 1);

		Matrix4x4_CreateFromQuakeEntity(&entrender->matrix, v[0], v[1], v[2], v[3], v[4], v[5], 1);
		CL_UpdateRenderEntity(entrender);
	}
}

static void CL_LerpPlayer(float frac)
{
	int i;

	cl.viewzoom = cl.mviewzoom[1] + frac * (cl.mviewzoom[0] - cl.mviewzoom[1]);
	for (i = 0;i < 3;i++)
	{
		cl.punchangle[i] = cl.mpunchangle[1][i] + frac * (cl.mpunchangle[0][i] - cl.mpunchangle[1][i]);
		cl.punchvector[i] = cl.mpunchvector[1][i] + frac * (cl.mpunchvector[0][i] - cl.mpunchvector[1][i]);
		cl.velocity[i] = cl.mvelocity[1][i] + frac * (cl.mvelocity[0][i] - cl.mvelocity[1][i]);
	}

	                                                                 
	if (cls.demoplayback || cl.fixangle[0])
	{
		for (i = 0;i < 3;i++)
		{
			float d = cl.mviewangles[0][i] - cl.mviewangles[1][i];
			if (d > 180)
				d -= 360;
			else if (d < -180)
				d += 360;
			cl.viewangles[i] = cl.mviewangles[1][i] + frac * d;
		}
	}
}

void CSQC_RelinkAllEntities (int drawmask)
{
	             
	CL_RelinkWorld();
	CL_RelinkStaticEntities();
	CL_RelinkBeams();
	CL_RelinkEffects();
	CL_RelinkLightFlashes();

	             
	if (drawmask & ENTMASK_ENGINE)
	{
		CL_RelinkNetworkEntities();
		if (drawmask & ENTMASK_ENGINEVIEWMODELS)
			CL_LinkNetworkEntity(&cl.viewent);                  
		CL_RelinkQWNails();
	}

	                    
	V_CalcViewBlend();

	CL_MeshEntities_AddToScene();
}

  
               
              

                                        
               
  
void CL_UpdateWorld(void)
{
	r_refdef.scene.extraupdate = !r_speeds.integer;
	r_refdef.scene.numentities = 0;
	r_refdef.scene.numlights = 0;
	r_refdef.view.matrix = identitymatrix;
	r_refdef.view.quality = 1;
		
	cl.num_brushmodel_entities = 0;

	if (cls.state == ca_connected && cls.signon == SIGNONS)
	{
		                          
		CL_LerpPlayer(CL_LerpPoint());
		CL_DecayLightFlashes();
		CL_ClearTempEntities();
		V_DriftPitch();
		V_FadeViewFlashs();

		                                                                
		                                                         
		CL_UpdateNetworkCollisionEntities();

		                                   
		CL_ClientMovement_Replay();

		                                                    
		CL_UpdateNetworkEntity(cl.entities + cl.viewentity, 32, true);

		                                                            
		V_CalcRefdef();

		                                                                 
		                                         
		CL_UpdateNetworkEntities();

		                                    
		CL_UpdateViewModel();

		                                                            
		if (!cl.csqc_loaded)
			CSQC_RelinkAllEntities(ENTMASK_ENGINE | ENTMASK_ENGINEVIEWMODELS);

		                                                                  
	}

	r_refdef.scene.time = cl.time;
}

                               
static void CL_PauseDemo_f (void)
{
	cls.demopaused = !cls.demopaused;
	if (cls.demopaused)
		Con_Print("Demo paused\n");
	else
		Con_Print("Demo unpaused\n");
}

  
                      
        
                      
  
static void CL_Fog_f (void)
{
	if (Cmd_Argc () == 1)
	{
		Con_Printf("\"fog\" is \"%f %f %f %f %f %f %f %f %f\"\n", r_refdef.fog_density, r_refdef.fog_red, r_refdef.fog_green, r_refdef.fog_blue, r_refdef.fog_alpha, r_refdef.fog_start, r_refdef.fog_end, r_refdef.fog_height, r_refdef.fog_fadedepth);
		return;
	}
	FOG_clear();                                       
	if(Cmd_Argc() > 1)
		r_refdef.fog_density = atof(Cmd_Argv(1));
	if(Cmd_Argc() > 2)
		r_refdef.fog_red = atof(Cmd_Argv(2));
	if(Cmd_Argc() > 3)
		r_refdef.fog_green = atof(Cmd_Argv(3));
	if(Cmd_Argc() > 4)
		r_refdef.fog_blue = atof(Cmd_Argv(4));
	if(Cmd_Argc() > 5)
		r_refdef.fog_alpha = atof(Cmd_Argv(5));
	if(Cmd_Argc() > 6)
		r_refdef.fog_start = atof(Cmd_Argv(6));
	if(Cmd_Argc() > 7)
		r_refdef.fog_end = atof(Cmd_Argv(7));
	if(Cmd_Argc() > 8)
		r_refdef.fog_height = atof(Cmd_Argv(8));
	if(Cmd_Argc() > 9)
		r_refdef.fog_fadedepth = atof(Cmd_Argv(9));
}

  
                      
                     
                      
  
static void CL_Fog_HeightTexture_f (void)
{
	if (Cmd_Argc () < 11)
	{
		Con_Printf("\"fog_heighttexture\" is \"%f %f %f %f %f %f %f %f %f %s\"\n", r_refdef.fog_density, r_refdef.fog_red, r_refdef.fog_green, r_refdef.fog_blue, r_refdef.fog_alpha, r_refdef.fog_start, r_refdef.fog_end, r_refdef.fog_height, r_refdef.fog_fadedepth, r_refdef.fog_height_texturename);
		return;
	}
	FOG_clear();                                       
	r_refdef.fog_density = atof(Cmd_Argv(1));
	r_refdef.fog_red = atof(Cmd_Argv(2));
	r_refdef.fog_green = atof(Cmd_Argv(3));
	r_refdef.fog_blue = atof(Cmd_Argv(4));
	r_refdef.fog_alpha = atof(Cmd_Argv(5));
	r_refdef.fog_start = atof(Cmd_Argv(6));
	r_refdef.fog_end = atof(Cmd_Argv(7));
	r_refdef.fog_height = atof(Cmd_Argv(8));
	r_refdef.fog_fadedepth = atof(Cmd_Argv(9));
	strlcpy(r_refdef.fog_height_texturename, Cmd_Argv(10), sizeof(r_refdef.fog_height_texturename));
}


  
                    
                

                        
                    
  
static void CL_TimeRefresh_f (void)
{
	int i;
	double timestart, timedelta;

	r_refdef.scene.extraupdate = false;

	timestart = Sys_DirtyTime();
	for (i = 0;i < 128;i++)
	{
		Matrix4x4_CreateFromQuakeEntity(&r_refdef.view.matrix, r_refdef.view.origin[0], r_refdef.view.origin[1], r_refdef.view.origin[2], 0, i / 128.0 * 360.0, 0, 1);
		r_refdef.view.quality = 1;
		CL_UpdateScreen();
	}
	timedelta = Sys_DirtyTime() - timestart;

	Con_Printf("%f seconds (%f fps)\n", timedelta, 128/timedelta);
}

static void CL_AreaStats_f(void)
{
	World_PrintAreaStats(&cl.world, "client");
}

cl_locnode_t *CL_Locs_FindNearest(const vec3_t point)
{
	int i;
	cl_locnode_t *loc;
	cl_locnode_t *best;
	vec3_t nearestpoint;
	vec_t dist, bestdist;
	best = NULL;
	bestdist = 0;
	for (loc = cl.locnodes;loc;loc = loc->next)
	{
		for (i = 0;i < 3;i++)
			nearestpoint[i] = bound(loc->mins[i], point[i], loc->maxs[i]);
		dist = VectorDistance2(nearestpoint, point);
		if (bestdist > dist || !best)
		{
			bestdist = dist;
			best = loc;
			if (bestdist < 1)
				break;
		}
	}
	return best;
}

void CL_Locs_FindLocationName(char *buffer, size_t buffersize, vec3_t point)
{
	cl_locnode_t *loc;
	loc = CL_Locs_FindNearest(point);
	if (loc)
		strlcpy(buffer, loc->name, buffersize);
	else
		dpsnprintf(buffer, buffersize, "LOC=%.0f:%.0f:%.0f", point[0], point[1], point[2]);
}

static void CL_Locs_FreeNode(cl_locnode_t *node)
{
	cl_locnode_t **pointer, **next;
	for (pointer = &cl.locnodes;*pointer;pointer = next)
	{
		next = &(*pointer)->next;
		if (*pointer == node)
		{
			*pointer = node->next;
			Mem_Free(node);
			return;
		}
	}
	Con_Printf("CL_Locs_FreeNode: no such node! (%p)\n", (void *)node);
}

static void CL_Locs_AddNode(vec3_t mins, vec3_t maxs, const char *name)
{
	cl_locnode_t *node, **pointer;
	int namelen;
	if (!name)
		name = "";
	namelen = (int)strlen(name);
	node = (cl_locnode_t *) Mem_Alloc(cls.levelmempool, sizeof(cl_locnode_t) + namelen + 1);
	VectorSet(node->mins, min(mins[0], maxs[0]), min(mins[1], maxs[1]), min(mins[2], maxs[2]));
	VectorSet(node->maxs, max(mins[0], maxs[0]), max(mins[1], maxs[1]), max(mins[2], maxs[2]));
	node->name = (char *)(node + 1);
	memcpy(node->name, name, namelen);
	node->name[namelen] = 0;
	                                                          
	for (pointer = &cl.locnodes;*pointer;pointer = &(*pointer)->next)
		;
	*pointer = node;
}

static void CL_Locs_Add_f(void)
{
	vec3_t mins, maxs;
	if (Cmd_Argc() != 5 && Cmd_Argc() != 8)
	{
		Con_Printf("usage: %s x y z[ x y z] name\n", Cmd_Argv(0));
		return;
	}
	mins[0] = atof(Cmd_Argv(1));
	mins[1] = atof(Cmd_Argv(2));
	mins[2] = atof(Cmd_Argv(3));
	if (Cmd_Argc() == 8)
	{
		maxs[0] = atof(Cmd_Argv(4));
		maxs[1] = atof(Cmd_Argv(5));
		maxs[2] = atof(Cmd_Argv(6));
		CL_Locs_AddNode(mins, maxs, Cmd_Argv(7));
	}
	else
		CL_Locs_AddNode(mins, mins, Cmd_Argv(4));
}

static void CL_Locs_RemoveNearest_f(void)
{
	cl_locnode_t *loc;
	loc = CL_Locs_FindNearest(r_refdef.view.origin);
	if (loc)
		CL_Locs_FreeNode(loc);
	else
		Con_Printf("no loc point or box found for your location\n");
}

static void CL_Locs_Clear_f(void)
{
	while (cl.locnodes)
		CL_Locs_FreeNode(cl.locnodes);
}

static void CL_Locs_Save_f(void)
{
	cl_locnode_t *loc;
	qfile_t *outfile;
	char locfilename[MAX_QPATH];
	if (!cl.locnodes)
	{
		Con_Printf("No loc points/boxes exist!\n");
		return;
	}
	if (cls.state != ca_connected || !cl.worldmodel)
	{
		Con_Printf("No level loaded!\n");
		return;
	}
	dpsnprintf(locfilename, sizeof(locfilename), "%s.loc", cl.worldnamenoextension);

	outfile = FS_OpenRealFile(locfilename, "w", false);
	if (!outfile)
		return;
	                                                                       
	                                                                 
	for (loc = cl.locnodes;loc;loc = loc->next)
		if (!VectorCompare(loc->mins, loc->maxs))
			break;
	if (loc)
	{
		FS_Printf(outfile, "// %s %s saved by %s\n// x,y,z,x,y,z,\"name\"\n\n", locfilename, Sys_TimeString("%Y-%m-%d"), engineversion);
		for (loc = cl.locnodes;loc;loc = loc->next)
			if (VectorCompare(loc->mins, loc->maxs))
				break;
		if (loc)
			Con_Printf("Warning: writing loc file containing a mixture of qizmo-style points and proquake-style boxes may not work in qizmo or proquake!\n");
	}
	for (loc = cl.locnodes;loc;loc = loc->next)
	{
		if (VectorCompare(loc->mins, loc->maxs))
		{
			int len;
			const char *s;
			const char *in = loc->name;
			char name[MAX_INPUTLINE];
			for (len = 0;len < (int)sizeof(name) - 1 && *in;)
			{
				if (*in == ' ') {s = "$loc_name_separator";in++;}
				else if (!strncmp(in, "SSG", 3)) {s = "$loc_name_ssg";in += 3;}
				else if (!strncmp(in, "NG", 2)) {s = "$loc_name_ng";in += 2;}
				else if (!strncmp(in, "SNG", 3)) {s = "$loc_name_sng";in += 3;}
				else if (!strncmp(in, "GL", 2)) {s = "$loc_name_gl";in += 2;}
				else if (!strncmp(in, "RL", 2)) {s = "$loc_name_rl";in += 2;}
				else if (!strncmp(in, "LG", 2)) {s = "$loc_name_lg";in += 2;}
				else if (!strncmp(in, "GA", 2)) {s = "$loc_name_ga";in += 2;}
				else if (!strncmp(in, "YA", 2)) {s = "$loc_name_ya";in += 2;}
				else if (!strncmp(in, "RA", 2)) {s = "$loc_name_ra";in += 2;}
				else if (!strncmp(in, "MEGA", 4)) {s = "$loc_name_mh";in += 4;}
				else s = NULL;
				if (s)
				{
					while (len < (int)sizeof(name) - 1 && *s)
						name[len++] = *s++;
					continue;
				}
				name[len++] = *in++;
			}
			name[len] = 0;
			FS_Printf(outfile, "%.0f %.0f %.0f %s\n", loc->mins[0]*8, loc->mins[1]*8, loc->mins[2]*8, name);
		}
		else
			FS_Printf(outfile, "%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,\"%s\"\n", loc->mins[0], loc->mins[1], loc->mins[2], loc->maxs[0], loc->maxs[1], loc->maxs[2], loc->name);
	}
	FS_Close(outfile);
}

void CL_Locs_Reload_f(void)
{
	int i, linenumber, limit, len;
	const char *s;
	char *filedata, *text, *textend, *linestart, *linetext, *lineend;
	fs_offset_t filesize;
	vec3_t mins, maxs;
	char locfilename[MAX_QPATH];
	char name[MAX_INPUTLINE];

	if (cls.state != ca_connected || !cl.worldmodel)
	{
		Con_Printf("No level loaded!\n");
		return;
	}

	CL_Locs_Clear_f();

	                                                                         
	dpsnprintf(locfilename, sizeof(locfilename), "%s.loc", cl.worldnamenoextension);
	filedata = (char *)FS_LoadFile(locfilename, cls.levelmempool, false, &filesize);
	if (!filedata)
	{
		                                                              
		dpsnprintf(locfilename, sizeof(locfilename), "locs/%s.loc", cl.worldbasename);
		filedata = (char *)FS_LoadFile(locfilename, cls.levelmempool, false, &filesize);
		if (!filedata)
			return;
	}
	text = filedata;
	textend = filedata + filesize;
	for (linenumber = 1;text < textend;linenumber++)
	{
		linestart = text;
		for (;text < textend && *text != '\r' && *text != '\n';text++)
			;
		lineend = text;
		if (text + 1 < textend && *text == '\r' && text[1] == '\n')
			text++;
		if (text < textend)
			text++;
		                           
		while (lineend > linestart && ISWHITESPACE(lineend[-1]))
			lineend--;
		                          
		while (linestart < lineend && ISWHITESPACE(*linestart))
			linestart++;
		                             
		if (linestart + 2 <= lineend && !strncmp(linestart, "//", 2))
			continue;
		linetext = linestart;
		limit = 3;
		for (i = 0;i < limit;i++)
		{
			if (linetext >= lineend)
				break;
			                                             
			if (i < 3)
				mins[i] = atof(linetext);
			else
				maxs[i - 3] = atof(linetext);
			                              
			while (linetext < lineend && !ISWHITESPACE(*linetext) && *linetext != ',')
				linetext++;
			                             
			if (linetext < lineend)
			{
				if (*linetext == ',')
				{
					linetext++;
					limit = 6;
					                                            
				}
				if (ISWHITESPACE(*linetext))
				{
					                  
					while (linetext < lineend && ISWHITESPACE(*linetext))
						linetext++;
				}
			}
		}
		                                              
		if (i == 6)
		{
			if (linetext >= lineend || *linetext != '"')
				continue;                                             
			lineend--;
			linetext++;
			len = min(lineend - linetext, (int)sizeof(name) - 1);
			memcpy(name, linetext, len);
			name[len] = 0;
			                          
			CL_Locs_AddNode(mins, maxs, name);
		}
		                                                                
		                                                             
		                                                                
		                
		else if (i == 3)
		{
			                                  
			for (len = 0;len < (int)sizeof(name) - 1 && linetext < lineend;)
			{
				if (*linetext == '$')
				{
					if (linetext + 18 <= lineend && !strncmp(linetext, "$loc_name_separator", 19)) {s = " ";linetext += 19;}
					else if (linetext + 13 <= lineend && !strncmp(linetext, "$loc_name_ssg", 13)) {s = "SSG";linetext += 13;}
					else if (linetext + 12 <= lineend && !strncmp(linetext, "$loc_name_ng", 12)) {s = "NG";linetext += 12;}
					else if (linetext + 13 <= lineend && !strncmp(linetext, "$loc_name_sng", 13)) {s = "SNG";linetext += 13;}
					else if (linetext + 12 <= lineend && !strncmp(linetext, "$loc_name_gl", 12)) {s = "GL";linetext += 12;}
					else if (linetext + 12 <= lineend && !strncmp(linetext, "$loc_name_rl", 12)) {s = "RL";linetext += 12;}
					else if (linetext + 12 <= lineend && !strncmp(linetext, "$loc_name_lg", 12)) {s = "LG";linetext += 12;}
					else if (linetext + 12 <= lineend && !strncmp(linetext, "$loc_name_ga", 12)) {s = "GA";linetext += 12;}
					else if (linetext + 12 <= lineend && !strncmp(linetext, "$loc_name_ya", 12)) {s = "YA";linetext += 12;}
					else if (linetext + 12 <= lineend && !strncmp(linetext, "$loc_name_ra", 12)) {s = "RA";linetext += 12;}
					else if (linetext + 12 <= lineend && !strncmp(linetext, "$loc_name_mh", 12)) {s = "MEGA";linetext += 12;}
					else s = NULL;
					if (s)
					{
						while (len < (int)sizeof(name) - 1 && *s)
							name[len++] = *s++;
						continue;
					}
				}
				name[len++] = *linetext++;
			}
			name[len] = 0;
			                            
			VectorScale(mins, (1.0 / 8.0), mins);
			CL_Locs_AddNode(mins, mins, name);
		}
		else
			continue;
	}
}

entity_t cl_meshentities[NUM_MESHENTITIES];
dp_model_t cl_meshentitymodels[NUM_MESHENTITIES];
const char *cl_meshentitynames[NUM_MESHENTITIES] =
{
	"MESH_DEBUG",
	"MESH_CSQC_POLYGONS",
	"MESH_PARTICLES",
	"MESH_UI",
};

void CL_MeshEntities_Restart(void)
{
	int i;
	entity_t *ent;
	for (i = 0; i < NUM_MESHENTITIES; i++)
	{
		ent = cl_meshentities + i;
		Mod_Mesh_Create(ent->render.model, cl_meshentitynames[i]);
	}
}

void CL_MeshEntities_Init(void)
{
	int i;
	entity_t *ent;
	for (i = 0; i < NUM_MESHENTITIES; i++)
	{
		ent = cl_meshentities + i;
		ent->state_current.active = true;
		ent->render.model = cl_meshentitymodels + i;
		ent->render.alpha = 1;
		ent->render.flags = RENDER_SHADOW | RENDER_LIGHT | RENDER_CUSTOMIZEDMODELLIGHT;
		ent->render.framegroupblend[0].lerp = 1;
		ent->render.frameblend[0].lerp = 1;
		VectorSet(ent->render.colormod, 1, 1, 1);
		VectorSet(ent->render.glowmod, 1, 1, 1);
		VectorSet(ent->render.custommodellight_ambient, 1, 1, 1);
		VectorSet(ent->render.custommodellight_diffuse, 0, 0, 0);
		VectorSet(ent->render.custommodellight_lightdir, 0, 0, 1);
		Matrix4x4_CreateIdentity(&ent->render.matrix);
		CL_UpdateRenderEntity(&ent->render);
	}
	R_RegisterModule("cl_meshentities", CL_MeshEntities_Restart, CL_MeshEntities_Restart, CL_MeshEntities_Restart, CL_MeshEntities_Restart, CL_MeshEntities_Restart);
}

void CL_MeshEntities_AddToScene(void)
{
	int i;
	entity_t *ent;
	for (i = 0; i < NUM_MESHENTITIES && r_refdef.scene.numentities < r_refdef.scene.maxentities; i++)
	{
		ent = cl_meshentities + i;
		if (ent->render.model->num_surfaces == 0)
			continue;
		Mod_Mesh_Finalize(ent->render.model);
		VectorCopy(ent->render.model->normalmins, ent->render.mins);
		VectorCopy(ent->render.model->normalmaxs, ent->render.maxs);
		r_refdef.scene.entities[r_refdef.scene.numentities++] = &ent->render;
	}
}

void CL_MeshEntities_Reset(void)
{
	int i;
	entity_t *ent;
	for (i = 0; i < NUM_MESHENTITIES && r_refdef.scene.numentities < r_refdef.scene.maxentities; i++)
	{
		ent = cl_meshentities + i;
		Mod_Mesh_Reset(ent->render.model);
	}
}

void CL_MeshEntities_Shutdown(void)
{
}

extern cvar_t r_overheadsprites_pushback;
extern cvar_t r_fullbright_directed_pitch_relative;
extern cvar_t r_fullbright_directed_pitch;
extern cvar_t r_fullbright_directed_ambient;
extern cvar_t r_fullbright_directed_diffuse;
extern cvar_t r_fullbright_directed;
extern cvar_t r_equalize_entities_minambient;
extern cvar_t r_equalize_entities_to;
extern cvar_t r_equalize_entities_by;
extern cvar_t r_hdr_glowintensity;

static void CL_UpdateEntityShading_GetDirectedFullbright(vec3_t ambient, vec3_t diffuse, vec3_t worldspacenormal)
{
	vec3_t angles;

	VectorSet(ambient, r_fullbright_directed_ambient.value, r_fullbright_directed_ambient.value, r_fullbright_directed_ambient.value);
	VectorSet(diffuse, r_fullbright_directed_diffuse.value, r_fullbright_directed_diffuse.value, r_fullbright_directed_diffuse.value);

	                                                                    
	                                                                  
	                                           
	VectorCopy(cl.viewangles, angles);
	if (r_fullbright_directed_pitch_relative.integer) {
		angles[PITCH] += r_fullbright_directed_pitch.value;
	}
	else {
		angles[PITCH] = r_fullbright_directed_pitch.value;
	}
	AngleVectors(angles, worldspacenormal, NULL, NULL);
	VectorNegate(worldspacenormal, worldspacenormal);
}

static void CL_UpdateEntityShading_Entity(entity_render_t *ent)
{
	float shadingorigin[3], f, fa, fd, fdd, a[3], c[3], dir[3];
	int q;

	for (q = 0; q < 3; q++)
		a[q] = c[q] = dir[q] = 0;

	ent->render_modellight_forced = false;
	ent->render_rtlight_disabled = false;

	                                                                         
	                                                                          
	                                                                           
	                  
	if (VectorLength2(ent->custommodellight_origin))
	{
		                                                          
		for (q = 0; q < 3; q++)
			shadingorigin[q] = ent->custommodellight_origin[q];
	}
	else if (ent->entitynumber > 0 && ent->entitynumber < cl.num_entities)
	{
		                                                                  
		int entnum = ent->entitynumber, recursion;
		for (recursion = 32; recursion > 0; --recursion)
		{
			int parentnum = cl.entities[entnum].state_current.tagentity;
			if (parentnum < 1 || parentnum >= cl.num_entities || !cl.entities_active[parentnum])
				break;
			entnum = parentnum;
		}
		                                
		Matrix4x4_OriginFromMatrix(&cl.entities[entnum].render.matrix, shadingorigin);
	}
	else
	{
		                                                                        
		                                                     
		Matrix4x4_OriginFromMatrix(&ent->matrix, shadingorigin);
	}

	if (!(ent->flags & RENDER_LIGHT) || r_fullbright.integer)
	{
		                                     
		                                                                       
		                                                              
		ent->render_rtlight_disabled = true;
		ent->render_modellight_forced = true;
		if (ent->flags & RENDER_CUSTOMIZEDMODELLIGHT)
		{
			                                 
			for (q = 0; q < 3; q++)
			{
				a[q] = ent->custommodellight_ambient[q];
				c[q] = ent->custommodellight_diffuse[q];
				dir[q] = ent->custommodellight_lightdir[q];
			}
		}
		else if (r_fullbright_directed.integer)
			CL_UpdateEntityShading_GetDirectedFullbright(a, c, dir);
		else
			for (q = 0; q < 3; q++)
				a[q] = 1;
	}
	else
	{
		                                              

		                                                        
		if (ent->flags & RENDER_CUSTOMIZEDMODELLIGHT)
		{
			ent->render_modellight_forced = true;
			for (q = 0; q < 3; q++)
			{
				a[q] = ent->custommodellight_ambient[q];
				c[q] = ent->custommodellight_diffuse[q];
				dir[q] = ent->custommodellight_lightdir[q];
			}
		}
		else if (ent->model->type == mod_sprite && !(ent->model->data_textures[0].basematerialflags & MATERIALFLAG_FULLBRIGHT))
		{
			if (ent->model->sprite.sprnum_type == SPR_OVERHEAD)                                     
				shadingorigin[2] = shadingorigin[2] + r_overheadsprites_pushback.value;
			R_CompleteLightPoint(a, c, dir, shadingorigin, LP_LIGHTMAP | LP_RTWORLD | LP_DYNLIGHT, r_refdef.scene.lightmapintensity, r_refdef.scene.ambientintensity);
			ent->render_modellight_forced = true;
			ent->render_rtlight_disabled = true;
		}
		else if (r_refdef.scene.worldmodel && r_refdef.scene.worldmodel->lit && r_refdef.scene.worldmodel->brush.LightPoint)
			R_CompleteLightPoint(a, c, dir, shadingorigin, LP_LIGHTMAP, r_refdef.scene.lightmapintensity, r_refdef.scene.ambientintensity);
		else if (r_fullbright_directed.integer)
			CL_UpdateEntityShading_GetDirectedFullbright(a, c, dir);
		else
			R_CompleteLightPoint(a, c, dir, shadingorigin, LP_LIGHTMAP, r_refdef.scene.lightmapintensity, r_refdef.scene.ambientintensity);

		if (ent->flags & RENDER_EQUALIZE)
		{
			                                   
			if (r_equalize_entities_minambient.value > 0)
			{
				fd = 0.299f * ent->render_modellight_diffuse[0] + 0.587f * ent->render_modellight_diffuse[1] + 0.114f * ent->render_modellight_diffuse[2];
				if (fd > 0)
				{
					fa = (0.299f * ent->render_modellight_ambient[0] + 0.587f * ent->render_modellight_ambient[1] + 0.114f * ent->render_modellight_ambient[2]);
					if (fa < r_equalize_entities_minambient.value * fd)
					{
						         
						                         
						                              
						        
						                           
						                                       
						        
						                                               
						                                                        
						        
						fdd = (fa + 0.25f * fd) / (0.25f + r_equalize_entities_minambient.value);
						f = fdd / fd;                                                                                                                                 
						for (q = 0; q < 3; q++)
						{
							a[q] = (1 - f)*0.25f * c[q];
							c[q] *= f;
						}
					}
				}
			}

			if (r_equalize_entities_to.value > 0 && r_equalize_entities_by.value != 0)
			{
				fa = 0.299f * a[0] + 0.587f * a[1] + 0.114f * a[2];
				fd = 0.299f * c[0] + 0.587f * c[1] + 0.114f * c[2];
				f = fa + 0.25 * fd;
				if (f > 0)
				{
					                                             
					float l2 = r_equalize_entities_by.value, l1 = 1 - l2;
					for (q = 0; q < 3; q++)
					{
						a[q] = l1 * a[q] + l2 * (fa / f);
						c[q] = l1 * c[q] + l2 * (fd / f);
					}
				}
			}
		}
	}

	for (q = 0; q < 3; q++)
	{
		ent->render_fullbright[q] = ent->colormod[q];
		ent->render_glowmod[q] = ent->glowmod[q] * r_hdr_glowintensity.value;
		ent->render_modellight_ambient[q] = a[q] * ent->colormod[q];
		ent->render_modellight_diffuse[q] = c[q] * ent->colormod[q];
		ent->render_modellight_specular[q] = c[q];
		ent->render_modellight_lightdir[q] = dir[q];
		ent->render_lightmap_ambient[q] = ent->colormod[q] * r_refdef.scene.ambientintensity;
		ent->render_lightmap_diffuse[q] = ent->colormod[q] * r_refdef.scene.lightmapintensity;
		ent->render_lightmap_specular[q] = r_refdef.scene.lightmapintensity;
		ent->render_rtlight_diffuse[q] = ent->colormod[q];
		ent->render_rtlight_specular[q] = 1;
	}

	                                                                                             
	if (ent->render_modellight_forced)
		for (q = 0; q < 3; q++)
			ent->render_lightmap_ambient[q] = ent->render_lightmap_diffuse[q] = ent->render_lightmap_specular[q] = q;
	if (ent->render_rtlight_disabled)
		for (q = 0; q < 3; q++)
			ent->render_rtlight_diffuse[q] = ent->render_rtlight_specular[q] = q;

	if (VectorLength2(ent->render_modellight_lightdir) == 0)
		VectorSet(ent->render_modellight_lightdir, 0, 0, 1);                                      
	VectorNormalize(ent->render_modellight_lightdir);
}


void CL_UpdateEntityShading(void)
{
	int i;
	CL_UpdateEntityShading_Entity(r_refdef.scene.worldentity);
	for (i = 0; i < r_refdef.scene.numentities; i++)
		CL_UpdateEntityShading_Entity(r_refdef.scene.entities[i]);
}

  
           
           
           
  
void CL_Shutdown (void)
{
	Capture_Shutdown();
	CL_Screen_Shutdown();
	CL_Particles_Shutdown();
	CL_Parse_Shutdown();
	CL_MeshEntities_Shutdown();

	Mem_FreePool (&cls.permanentmempool);
	Mem_FreePool (&cls.levelmempool);
}

  
                 
       
                 
  
void CL_Init (void)
{

	cls.levelmempool = Mem_AllocPool("client (per-level memory)", 0, NULL);
	cls.permanentmempool = Mem_AllocPool("client (long term memory)", 0, NULL);

	memset(&r_refdef, 0, sizeof(r_refdef));
	                                          
	r_refdef.scene.maxentities = MAX_EDICTS + 256 + 512;
	r_refdef.scene.entities = (entity_render_t **)Mem_Alloc(cls.permanentmempool, sizeof(entity_render_t *) * r_refdef.scene.maxentities);

	                    
	r_refdef.scene.maxtempentities = MAX_TEMPENTITIES;
	r_refdef.scene.tempentities = (entity_render_t *)Mem_Alloc(cls.permanentmempool, sizeof(entity_render_t) * r_refdef.scene.maxtempentities);

	CL_InitInput ();
	Capture_Init();

  
                        
  
	Cvar_RegisterVariable (&cl_upspeed);
	Cvar_RegisterVariable (&cl_forwardspeed);
	Cvar_RegisterVariable (&cl_backspeed);
	Cvar_RegisterVariable (&cl_sidespeed);
	Cvar_RegisterVariable (&cl_movespeedkey);
	Cvar_RegisterVariable (&cl_yawspeed);
	Cvar_RegisterVariable (&cl_pitchspeed);
	Cvar_RegisterVariable (&cl_anglespeedkey);
	Cvar_RegisterVariable (&cl_shownet);
	Cvar_RegisterVariable (&cl_nolerp);
	Cvar_RegisterVariable (&cl_lerpexcess);
	Cvar_RegisterVariable (&cl_lerpanim_maxdelta_server);
	Cvar_RegisterVariable (&cl_lerpanim_maxdelta_framegroups);
	Cvar_RegisterVariable (&cl_deathfade);
	Cvar_RegisterVariable (&lookspring);
	Cvar_RegisterVariable (&lookstrafe);
	Cvar_RegisterVariable (&sensitivity);
	Cvar_RegisterVariable (&freelook);

	Cvar_RegisterVariable (&m_pitch);
	Cvar_RegisterVariable (&m_yaw);
	Cvar_RegisterVariable (&m_forward);
	Cvar_RegisterVariable (&m_side);

	Cvar_RegisterVariable (&cl_itembobspeed);
	Cvar_RegisterVariable (&cl_itembobheight);

	Cmd_AddCommand ("entities", CL_PrintEntities_f, "print information on network entities known to client");
	Cmd_AddCommand ("disconnect", CL_Disconnect_f, "disconnect from server (or disconnect all clients if running a server)");
	Cmd_AddCommand ("record", CL_Record_f, "record a demo");
	Cmd_AddCommand ("stop", CL_Stop_f, "stop recording or playing a demo");
	Cmd_AddCommand ("playdemo", CL_PlayDemo_f, "watch a demo file");
	Cmd_AddCommand ("timedemo", CL_TimeDemo_f, "play back a demo as fast as possible and save statistics to benchmark.log");

	                                       
	Cmd_AddCommand ("cl_modelindexlist", CL_ModelIndexList_f, "list information on all models in the client modelindex");
	                                       
	Cmd_AddCommand ("cl_soundindexlist", CL_SoundIndexList_f, "list all sounds in the client soundindex");

	Cvar_RegisterVariable (&cl_autodemo);
	Cvar_RegisterVariable (&cl_autodemo_nameformat);
	Cvar_RegisterVariable (&cl_autodemo_delete);

	Cmd_AddCommand ("fog", CL_Fog_f, "set global fog parameters (density red green blue [alpha [mindist [maxdist [top [fadedepth]]]]])");
	Cmd_AddCommand ("fog_heighttexture", CL_Fog_HeightTexture_f, "set global fog parameters (density red green blue alpha mindist maxdist top depth textures/mapname/fogheight.tga)");

	                             
	Cmd_AddCommand ("pausedemo", CL_PauseDemo_f, "pause demo playback (can also safely pause demo recording if using QUAKE, QUAKEDP or NEHAHRAMOVIE protocol, useful for making movies)");

	Cmd_AddCommand ("cl_areastats", CL_AreaStats_f, "prints statistics on entity culling during collision traces");

	Cvar_RegisterVariable(&r_draweffects);
	Cvar_RegisterVariable(&cl_explosions_alpha_start);
	Cvar_RegisterVariable(&cl_explosions_alpha_end);
	Cvar_RegisterVariable(&cl_explosions_size_start);
	Cvar_RegisterVariable(&cl_explosions_size_end);
	Cvar_RegisterVariable(&cl_explosions_lifetime);
	Cvar_RegisterVariable(&cl_stainmaps);
	Cvar_RegisterVariable(&cl_stainmaps_clearonload);
	Cvar_RegisterVariable(&cl_beams_polygons);
	Cvar_RegisterVariable(&cl_beams_quakepositionhack);
	Cvar_RegisterVariable(&cl_beams_instantaimhack);
	Cvar_RegisterVariable(&cl_beams_lightatend);
	Cvar_RegisterVariable(&cl_noplayershadow);
	Cvar_RegisterVariable(&cl_dlights_decayradius);
	Cvar_RegisterVariable(&cl_dlights_decaybrightness);

	Cvar_RegisterVariable(&cl_prydoncursor);
	Cvar_RegisterVariable(&cl_prydoncursor_notrace);

	Cvar_RegisterVariable(&cl_deathnoviewmodel);

	                     
	Cvar_RegisterVariable(&qport);
	Cvar_SetValueQuick(&qport, (rand() * RAND_MAX + rand()) & 0xffff);

	Cmd_AddCommand("timerefresh", CL_TimeRefresh_f, "turn quickly and print rendering statistcs");

	Cvar_RegisterVariable(&cl_locs_enable);
	Cvar_RegisterVariable(&cl_locs_show);
	Cmd_AddCommand("locs_add", CL_Locs_Add_f, "add a point or box location (usage: x y z[ x y z] \"name\", if two sets of xyz are supplied it is a box, otherwise point)");
	Cmd_AddCommand("locs_removenearest", CL_Locs_RemoveNearest_f, "remove the nearest point or box (note: you need to be very near a box to remove it)");
	Cmd_AddCommand("locs_clear", CL_Locs_Clear_f, "remove all loc points/boxes");
	Cmd_AddCommand("locs_reload", CL_Locs_Reload_f, "reload .loc file for this map");
	Cmd_AddCommand("locs_save", CL_Locs_Save_f, "save .loc file for this map containing currently defined points and boxes");

	CL_Parse_Init();
	CL_Particles_Init();
	CL_Screen_Init();
	CL_MeshEntities_Init();

	CL_Video_Init();
}
