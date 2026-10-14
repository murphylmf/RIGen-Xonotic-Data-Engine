  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
                                                          

#include "quakedef.h"
#include "capture_telemetry.h"
#ifdef CONFIG_CD
#include "cdaudio.h"
#endif
#include "cl_collision.h"
#include "csprogs.h"
#include "libcurl.h"
#include "utf8lib.h"
#ifdef CONFIG_MENU
#include "menu.h"
#endif
#include "cl_video.h"

const char *svc_strings[128] =
{
	"svc_bad",
	"svc_nop",
	"svc_disconnect",
	"svc_updatestat",
	"svc_version",		                       
	"svc_setview",		                        
	"svc_sound",			             
	"svc_time",			                      
	"svc_print",			                                  
	"svc_stufftext",		                                                
						                                     
	"svc_setangle",		                                                   

	"svc_serverinfo",		                
						                         
						                                                      
						                          
	"svc_lightstyle",		                  
	"svc_updatename",		                  
	"svc_updatefrags",	                 
	"svc_clientdata",		                     
	"svc_stopsound",		             
	"svc_updatecolors",	                
	"svc_particle",		                    
	"svc_damage",			                                         

	"svc_spawnstatic",
	"OBSOLETE svc_spawnbinary",
	"svc_spawnbaseline",

	"svc_temp_entity",		             
	"svc_setpause",
	"svc_signonnum",
	"svc_centerprint",
	"svc_killedmonster",
	"svc_foundsecret",
	"svc_spawnstaticsound",
	"svc_intermission",
	"svc_finale",			                               
	"svc_cdtrack",			                                
	"svc_sellscreen",
	"svc_cutscene",
	"svc_showlmp",	                                                          
	"svc_hidelmp",	                     
	"svc_skybox",                    
	"",      
	"",      
	"",      
	"",      
	"",      
	"",      
	"",      
	"",      
	"",      
	"",      
	"",      
	"",      
	"svc_downloaddata",                                                             
	"svc_updatestatubyte",                                     
	"svc_effect",                                                                                                
	"svc_effect2",                                                                                                  
	"svc_sound2",                                             
	"svc_spawnbaseline2",                                           
	"svc_spawnstatic2",                                            
	"svc_entities",                                                                                             
	"svc_csqcentities",                                                                          
	"svc_spawnstaticsound2",                                                       
	"svc_trailparticles",                                                                       
	"svc_pointparticles",                                                                           
	"svc_pointparticles1",                                                                                                              
};

const char *qw_svc_strings[128] =
{
	"qw_svc_bad",					    
	"qw_svc_nop",					    
	"qw_svc_disconnect",			    
	"qw_svc_updatestat",			                     
	"",								    
	"qw_svc_setview",				                             
	"qw_svc_sound",					                  
	"",								    
	"qw_svc_print",					                                                 
	"qw_svc_stufftext",				                                                     
	"qw_svc_setangle",				                                                           
	"qw_svc_serverdata",			                            
	"qw_svc_lightstyle",			                        
	"",								     
	"qw_svc_updatefrags",			                       
	"",								     
	"qw_svc_stopsound",				                   
	"",								     
	"",								     
	"qw_svc_damage",				     
	"qw_svc_spawnstatic",			     
	"",								     
	"qw_svc_spawnbaseline",			     
	"qw_svc_temp_entity",			                 
	"qw_svc_setpause",				                        
	"",								     
	"qw_svc_centerprint",			                                                
	"qw_svc_killedmonster",			     
	"qw_svc_foundsecret",			     
	"qw_svc_spawnstaticsound",		                                                    
	"qw_svc_intermission",			                                        
	"qw_svc_finale",				                       
	"qw_svc_cdtrack",				                      
	"qw_svc_sellscreen",			     
	"qw_svc_smallkick",				                                    
	"qw_svc_bigkick",				                                    
	"qw_svc_updateping",			                        
	"qw_svc_updateentertime",		                        
	"qw_svc_updatestatlong",		                       
	"qw_svc_muzzleflash",			                        
	"qw_svc_updateuserinfo",		                                
	"qw_svc_download",				                                   
	"qw_svc_playerinfo",			                  
	"qw_svc_nails",					                                                 
	"qw_svc_chokecount",			                               
	"qw_svc_modellist",				                   
	"qw_svc_soundlist",				                   
	"qw_svc_packetentities",		               
	"qw_svc_deltapacketentities",	               
	"qw_svc_maxspeed",				                                         
	"qw_svc_entgravity",			                                        
	"qw_svc_setinfo",				                             
	"qw_svc_serverinfo",			                    
	"qw_svc_updatepl",				                       
};

                                                                               

cvar_t cl_worldmessage = {CVAR_READONLY, "cl_worldmessage", "", "title of current level"};
cvar_t cl_worldname = {CVAR_READONLY, "cl_worldname", "", "name of current worldmodel"};
cvar_t cl_worldnamenoextension = {CVAR_READONLY, "cl_worldnamenoextension", "", "name of current worldmodel without extension"};
cvar_t cl_worldbasename = {CVAR_READONLY, "cl_worldbasename", "", "name of current worldmodel without maps/ prefix or extension"};

cvar_t developer_networkentities = {0, "developer_networkentities", "0", "prints received entities, value is 0-10 (higher for more info, 10 being the most verbose)"};
cvar_t cl_gameplayfix_soundsmovewithentities = {0, "cl_gameplayfix_soundsmovewithentities", "1", "causes sounds made by lifts, players, projectiles, and any other entities, to move with the entity, so for example a rocket noise follows the rocket rather than staying at the starting position"};
cvar_t cl_sound_wizardhit = {0, "cl_sound_wizardhit", "wizard/hit.wav", "sound to play during TE_WIZSPIKE (empty cvar disables sound)"};
cvar_t cl_sound_hknighthit = {0, "cl_sound_hknighthit", "hknight/hit.wav", "sound to play during TE_KNIGHTSPIKE (empty cvar disables sound)"};
cvar_t cl_sound_tink1 = {0, "cl_sound_tink1", "weapons/tink1.wav", "sound to play with 80% chance during TE_SPIKE/TE_SUPERSPIKE (empty cvar disables sound)"};
cvar_t cl_sound_ric1 = {0, "cl_sound_ric1", "weapons/ric1.wav", "sound to play with 5% chance during TE_SPIKE/TE_SUPERSPIKE (empty cvar disables sound)"};
cvar_t cl_sound_ric2 = {0, "cl_sound_ric2", "weapons/ric2.wav", "sound to play with 5% chance during TE_SPIKE/TE_SUPERSPIKE (empty cvar disables sound)"};
cvar_t cl_sound_ric3 = {0, "cl_sound_ric3", "weapons/ric3.wav", "sound to play with 10% chance during TE_SPIKE/TE_SUPERSPIKE (empty cvar disables sound)"};
cvar_t cl_readpicture_force = {0, "cl_readpicture_force", "0", "when enabled, the low quality pictures read by ReadPicture() are preferred over the high quality pictures on the file system"};

#define RIC_GUNSHOT		1
#define RIC_GUNSHOTQUAD	2
cvar_t cl_sound_ric_gunshot = {0, "cl_sound_ric_gunshot", "0", "specifies if and when the related cl_sound_ric and cl_sound_tink sounds apply to TE_GUNSHOT/TE_GUNSHOTQUAD, 0 = no sound, 1 = TE_GUNSHOT, 2 = TE_GUNSHOTQUAD, 3 = TE_GUNSHOT and TE_GUNSHOTQUAD"};
cvar_t cl_sound_r_exp3 = {0, "cl_sound_r_exp3", "weapons/r_exp3.wav", "sound to play during TE_EXPLOSION and related effects (empty cvar disables sound)"};
cvar_t cl_serverextension_download = {0, "cl_serverextension_download", "0", "indicates whether the server supports the download command"};
cvar_t cl_joinbeforedownloadsfinish = {CVAR_SAVE, "cl_joinbeforedownloadsfinish", "1", "if non-zero the game will begin after the map is loaded before other downloads finish"};
cvar_t cl_nettimesyncfactor = {CVAR_SAVE, "cl_nettimesyncfactor", "0", "rate at which client time adapts to match server time, 1 = instantly, 0.125 = slowly, 0 = not at all (bounding still applies)"};
cvar_t cl_nettimesyncboundmode = {CVAR_SAVE, "cl_nettimesyncboundmode", "6", "method of restricting client time to valid values, 0 = no correction, 1 = tight bounding (jerky with packet loss), 2 = loose bounding (corrects it if out of bounds), 3 = leniant bounding (ignores temporary errors due to varying framerate), 4 = slow adjustment method from Quake3, 5 = slighttly nicer version of Quake3 method, 6 = bounding + Quake3"};
cvar_t cl_nettimesyncboundtolerance = {CVAR_SAVE, "cl_nettimesyncboundtolerance", "0.25", "how much error is tolerated by bounding check, as a fraction of frametime, 0.25 = up to 25% margin of error tolerated, 1 = use only new time, 0 = use only old time (same effect as setting cl_nettimesyncfactor to 1)"};
cvar_t cl_iplog_name = {CVAR_SAVE, "cl_iplog_name", "darkplaces_iplog.txt", "name of iplog file containing player addresses for iplog_list command and automatic ip logging when parsing status command"};

static qboolean QW_CL_CheckOrDownloadFile(const char *filename);
static void QW_CL_RequestNextDownload(void);
static void QW_CL_NextUpload(void);
                                          
static void QW_CL_StopUpload(void);

  
                  
                        
                  
  
static void CL_ParseStartSoundPacket(int largesoundindex)
{
	vec3_t  pos;
	int 	channel, ent;
	int 	sound_num;
	int 	nvolume;
	int 	field_mask;
	float 	attenuation;
	float	speed;
	int		fflags = CHANNELFLAG_NONE;

	if (cls.protocol == PROTOCOL_QUAKEWORLD)
	{
		channel = MSG_ReadShort(&cl_message);

		if (channel & (1<<15))
			nvolume = MSG_ReadByte(&cl_message);
		else
			nvolume = DEFAULT_SOUND_PACKET_VOLUME;

		if (channel & (1<<14))
			attenuation = MSG_ReadByte(&cl_message) / 64.0;
		else
			attenuation = DEFAULT_SOUND_PACKET_ATTENUATION;

		speed = 1.0f;

		ent = (channel>>3)&1023;
		channel &= 7;

		sound_num = MSG_ReadByte(&cl_message);
	}
	else
	{
		field_mask = MSG_ReadByte(&cl_message);

		if (field_mask & SND_VOLUME)
			nvolume = MSG_ReadByte(&cl_message);
		else
			nvolume = DEFAULT_SOUND_PACKET_VOLUME;

		if (field_mask & SND_ATTENUATION)
			attenuation = MSG_ReadByte(&cl_message) / 64.0;
		else
			attenuation = DEFAULT_SOUND_PACKET_ATTENUATION;

		if (field_mask & SND_SPEEDUSHORT4000)
			speed = ((unsigned short)MSG_ReadShort(&cl_message)) / 4000.0f;
		else
			speed = 1.0f;

		if (field_mask & SND_LARGEENTITY)
		{
			ent = (unsigned short) MSG_ReadShort(&cl_message);
			channel = MSG_ReadChar(&cl_message);
		}
		else
		{
			channel = (unsigned short) MSG_ReadShort(&cl_message);
			ent = channel >> 3;
			channel &= 7;
		}

		if (largesoundindex || (field_mask & SND_LARGESOUND) || cls.protocol == PROTOCOL_NEHAHRABJP2 || cls.protocol == PROTOCOL_NEHAHRABJP3)
			sound_num = (unsigned short) MSG_ReadShort(&cl_message);
		else
			sound_num = MSG_ReadByte(&cl_message);
	}

	channel = CHAN_NET2ENGINE(channel);

	MSG_ReadVector(&cl_message, pos, cls.protocol);

	if (sound_num < 0 || sound_num >= MAX_SOUNDS)
	{
		Con_Printf("CL_ParseStartSoundPacket: sound_num (%i) >= MAX_SOUNDS (%i)\n", sound_num, MAX_SOUNDS);
		return;
	}

	if (ent >= MAX_EDICTS)
	{
		Con_Printf("CL_ParseStartSoundPacket: ent = %i", ent);
		return;
	}

	if (ent >= cl.max_entities)
		CL_ExpandEntities(ent);

	if( !CL_VM_Event_Sound(sound_num, nvolume / 255.0f, channel, attenuation, ent, pos, fflags, speed) )
		S_StartSound_StartPosition_Flags (ent, channel, cl.sound_precache[sound_num], pos, nvolume/255.0f, attenuation, 0, fflags, speed);
}

  
                  
                   

                                                                            
                                 
                  
  

static unsigned char olddata[NET_MAXMESSAGE];
void CL_KeepaliveMessage (qboolean readmessages)
{
	static double lastdirtytime = 0;
	static qboolean recursive = false;
	double dirtytime;
	double deltatime;
	static double countdownmsg = 0;
	static double countdownupdate = 0;
	sizebuf_t old;

	qboolean thisrecursive;

	thisrecursive = recursive;
	recursive = true;

	dirtytime = Sys_DirtyTime();
	deltatime = dirtytime - lastdirtytime;
	lastdirtytime = dirtytime;
	if (deltatime <= 0 || deltatime >= 1800.0)
		return;

	countdownmsg -= deltatime;
	countdownupdate -= deltatime;

	if(!thisrecursive)
	{
		if(cls.state != ca_dedicated)
		{
			if(countdownupdate <= 0)                                   
			{
				SCR_UpdateLoadingScreenIfShown();
				countdownupdate = 2;
			}
		}
	}

	                                                                  
	if (sv.active || !cls.netcon || cls.protocol == PROTOCOL_QUAKEWORLD || cls.signon >= SIGNONS)
	{
		recursive = thisrecursive;
		return;
	}

	if (readmessages)
	{
		                                                 
		old = cl_message;
		memcpy(olddata, cl_message.data, cl_message.cursize);

		NetConn_ClientFrame();

		cl_message = old;
		memcpy(cl_message.data, olddata, cl_message.cursize);
	}

	if (cls.netcon && countdownmsg <= 0)                                   
	{
		sizebuf_t	msg;
		unsigned char		buf[4];
		countdownmsg = 5;
		                  
		                                                                                
		Con_Print("--> client to server keepalive\n");
		memset(&msg, 0, sizeof(msg));
		msg.data = buf;
		msg.maxsize = sizeof(buf);
		MSG_WriteChar(&msg, clc_nop);
		NetConn_SendUnreliableMessage(cls.netcon, &msg, cls.protocol, 10000, 0, false);
	}

	recursive = thisrecursive;
}

void CL_ParseEntityLump(char *entdata)
{
	qboolean loadedsky = false;
	const char *data;
	char key[128], value[MAX_INPUTLINE];
	FOG_clear();                               
	                                                                    
	R_SetSkyBox(cl.worldmodel->brush.skybox);
	data = entdata;
	if (!data)
		return;
	if (!COM_ParseToken_Simple(&data, false, false, true))
		return;         
	if (com_token[0] != '{')
		return;         
	while (1)
	{
		if (!COM_ParseToken_Simple(&data, false, false, true))
			return;         
		if (com_token[0] == '}')
			break;                     
		if (com_token[0] == '_')
			strlcpy (key, com_token + 1, sizeof (key));
		else
			strlcpy (key, com_token, sizeof (key));
		while (key[strlen(key)-1] == ' ')                          
			key[strlen(key)-1] = 0;
		if (!COM_ParseToken_Simple(&data, false, false, true))
			return;         
		strlcpy (value, com_token, sizeof (value));
		if (!strcmp("sky", key))
		{
			loadedsky = true;
			R_SetSkyBox(value);
		}
		else if (!strcmp("skyname", key))                                                   
		{
			loadedsky = true;
			R_SetSkyBox(value);
		}
		else if (!strcmp("qlsky", key))                                                
		{
			loadedsky = true;
			R_SetSkyBox(value);
		}
		else if (!strcmp("fog", key))
		{
			FOG_clear();                                       
			r_refdef.fog_start = 0;
			r_refdef.fog_alpha = 1;
			r_refdef.fog_end = 16384;
			r_refdef.fog_height = 1<<30;
			r_refdef.fog_fadedepth = 128;
#if _MSC_VER >= 1400
#define sscanf sscanf_s
#endif
			sscanf(value, "%f %f %f %f %f %f %f %f %f", &r_refdef.fog_density, &r_refdef.fog_red, &r_refdef.fog_green, &r_refdef.fog_blue, &r_refdef.fog_alpha, &r_refdef.fog_start, &r_refdef.fog_end, &r_refdef.fog_height, &r_refdef.fog_fadedepth);
		}
		else if (!strcmp("fog_density", key))
			r_refdef.fog_density = atof(value);
		else if (!strcmp("fog_red", key))
			r_refdef.fog_red = atof(value);
		else if (!strcmp("fog_green", key))
			r_refdef.fog_green = atof(value);
		else if (!strcmp("fog_blue", key))
			r_refdef.fog_blue = atof(value);
		else if (!strcmp("fog_alpha", key))
			r_refdef.fog_alpha = atof(value);
		else if (!strcmp("fog_start", key))
			r_refdef.fog_start = atof(value);
		else if (!strcmp("fog_end", key))
			r_refdef.fog_end = atof(value);
		else if (!strcmp("fog_height", key))
			r_refdef.fog_height = atof(value);
		else if (!strcmp("fog_fadedepth", key))
			r_refdef.fog_fadedepth = atof(value);
		else if (!strcmp("fog_heighttexture", key))
		{
			FOG_clear();                                       
#if _MSC_VER >= 1400
			sscanf_s(value, "%f %f %f %f %f %f %f %f %f %s", &r_refdef.fog_density, &r_refdef.fog_red, &r_refdef.fog_green, &r_refdef.fog_blue, &r_refdef.fog_alpha, &r_refdef.fog_start, &r_refdef.fog_end, &r_refdef.fog_height, &r_refdef.fog_fadedepth, r_refdef.fog_height_texturename, (unsigned int)sizeof(r_refdef.fog_height_texturename));
#else
			sscanf(value, "%f %f %f %f %f %f %f %f %f %63s", &r_refdef.fog_density, &r_refdef.fog_red, &r_refdef.fog_green, &r_refdef.fog_blue, &r_refdef.fog_alpha, &r_refdef.fog_start, &r_refdef.fog_end, &r_refdef.fog_height, &r_refdef.fog_fadedepth, r_refdef.fog_height_texturename);
#endif
			r_refdef.fog_height_texturename[63] = 0;
		}
	}

	if (!loadedsky && cl.worldmodel->brush.isq2bsp)
		R_SetSkyBox("unit1_");
}

static const vec3_t defaultmins = {-4096, -4096, -4096};
static const vec3_t defaultmaxs = {4096, 4096, 4096};
static void CL_SetupWorldModel(void)
{
	prvm_prog_t *prog = CLVM_prog;
	                         
	cl.entities[0].render.model = cl.worldmodel = CL_GetModelByIndex(1);
	CL_UpdateRenderEntity(&cl.entities[0].render);

	                                                                                                
	                                          
	if (cl.worldmodel)
	{
		strlcpy(cl.worldname, cl.worldmodel->name, sizeof(cl.worldname));
		FS_StripExtension(cl.worldname, cl.worldnamenoextension, sizeof(cl.worldnamenoextension));
		strlcpy(cl.worldbasename, !strncmp(cl.worldnamenoextension, "maps/", 5) ? cl.worldnamenoextension + 5 : cl.worldnamenoextension, sizeof(cl.worldbasename));
		Cvar_SetQuick(&cl_worldmessage, cl.worldmessage);
		Cvar_SetQuick(&cl_worldname, cl.worldname);
		Cvar_SetQuick(&cl_worldnamenoextension, cl.worldnamenoextension);
		Cvar_SetQuick(&cl_worldbasename, cl.worldbasename);
		World_SetSize(&cl.world, cl.worldname, cl.worldmodel->normalmins, cl.worldmodel->normalmaxs, prog);
	}
	else
	{
		Cvar_SetQuick(&cl_worldmessage, cl.worldmessage);
		Cvar_SetQuick(&cl_worldnamenoextension, "");
		Cvar_SetQuick(&cl_worldbasename, "");
		World_SetSize(&cl.world, "", defaultmins, defaultmaxs, prog);
	}
	World_Start(&cl.world);

	                                                  
	CL_Locs_Reload_f();

	                                      
	CL_KeepaliveMessage(false);

	                                             
	R_Modules_NewMap();

	                                      
	CL_KeepaliveMessage(false);

	                                      
	cl.foundtalk2wav = FS_FileExists("sound/misc/talk2.wav");

	                         
	Mem_CheckSentinelsGlobal();

#ifdef CONFIG_MENU
	                 
	MR_NewMap();
#endif

	                    
	if (cl.loadcsqc)
	{
		cl.loadcsqc = false;

		CL_VM_Init();
	}
}

static qboolean QW_CL_CheckOrDownloadFile(const char *filename)
{
	qfile_t *file;
	char vabuf[1024];

	                                 
	file = FS_OpenVirtualFile(filename, true);
	if (file)
	{
		FS_Close(file);
		return true;
	}

	                                           
	if (cls.demorecording)
	{
		Con_Printf("Unable to download \"%s\" when recording.\n", filename);
		return true;
	}

	                                            
	if (!cls.netcon)
		return true;

	strlcpy(cls.qw_downloadname, filename, sizeof(cls.qw_downloadname));
	Con_Printf("Downloading %s\n", filename);

	if (!cls.qw_downloadmemory)
	{
		cls.qw_downloadmemory = NULL;
		cls.qw_downloadmemorycursize = 0;
		cls.qw_downloadmemorymaxsize = 1024*1024;                               
	}

	MSG_WriteByte(&cls.netcon->message, qw_clc_stringcmd);
	MSG_WriteString(&cls.netcon->message, va(vabuf, sizeof(vabuf), "download %s", filename));

	cls.qw_downloadnumber++;
	cls.qw_downloadpercent = 0;
	cls.qw_downloadmemorycursize = 0;

	return false;
}

static void QW_CL_ProcessUserInfo(int slot);
static void QW_CL_RequestNextDownload(void)
{
	int i;
	char vabuf[1024];

	                                        
	cls.qw_downloadname[0] = 0;

	                                               
	if (!cls.netcon)
	{
		return;
	}

	switch (cls.qw_downloadtype)
	{
	case dl_single:
		break;
	case dl_skin:
		if (cls.qw_downloadnumber == 0)
			Con_Printf("Checking skins...\n");
		for (;cls.qw_downloadnumber < cl.maxclients;cls.qw_downloadnumber++)
		{
			if (!cl.scores[cls.qw_downloadnumber].name[0])
				continue;
			                                                          
			if (!QW_CL_CheckOrDownloadFile(va(vabuf, sizeof(vabuf), "skins/%s.pcx", cl.scores[cls.qw_downloadnumber].qw_skin)))
				return;
		}

		cls.qw_downloadtype = dl_none;

		                                  
		for (i = 0;i < cl.maxclients;i++)
			QW_CL_ProcessUserInfo(i);

		                                                        
		if (cls.signon != SIGNONS)
		{
			cls.signon = SIGNONS-1;
			                                                               
			MSG_WriteByte(&cls.netcon->message, qw_clc_stringcmd);
			MSG_WriteString(&cls.netcon->message, va(vabuf, sizeof(vabuf), "begin %i", cl.qw_servercount));
		}
		break;
	case dl_model:
		if (cls.qw_downloadnumber == 0)
		{
			Con_Printf("Checking models...\n");
			cls.qw_downloadnumber = 1;
		}

		for (;cls.qw_downloadnumber < MAX_MODELS && cl.model_name[cls.qw_downloadnumber][0];cls.qw_downloadnumber++)
		{
			                 
			if (cl.model_name[cls.qw_downloadnumber][0] == '*')
				continue;
			if (!strcmp(cl.model_name[cls.qw_downloadnumber], "progs/spike.mdl"))
				cl.qw_modelindex_spike = cls.qw_downloadnumber;
			if (!strcmp(cl.model_name[cls.qw_downloadnumber], "progs/player.mdl"))
				cl.qw_modelindex_player = cls.qw_downloadnumber;
			if (!strcmp(cl.model_name[cls.qw_downloadnumber], "progs/flag.mdl"))
				cl.qw_modelindex_flag = cls.qw_downloadnumber;
			if (!strcmp(cl.model_name[cls.qw_downloadnumber], "progs/s_explod.spr"))
				cl.qw_modelindex_s_explod = cls.qw_downloadnumber;
			                                                          
			if (!QW_CL_CheckOrDownloadFile(cl.model_name[cls.qw_downloadnumber]))
				return;
		}

		cls.qw_downloadtype = dl_none;

		                                                                         
		                             
		if (!sv.active)
			Mod_ClearUsed();
		for (i = 1;i < MAX_MODELS && cl.model_name[i][0];i++)
			Mod_FindName(cl.model_name[i], cl.model_name[i][0] == '*' ? cl.model_name[1] : NULL);
		                                                                     
		cl.model_bolt = Mod_ForName("progs/bolt.mdl", false, false, NULL);
		cl.model_bolt2 = Mod_ForName("progs/bolt2.mdl", false, false, NULL);
		cl.model_bolt3 = Mod_ForName("progs/bolt3.mdl", false, false, NULL);
		cl.model_beam = Mod_ForName("progs/beam.mdl", false, false, NULL);

		                                                         
		                    

		                                            

		              
		cl.model_precache[1] = Mod_ForName(cl.model_name[1], false, false, NULL);
		if (cl.model_precache[1]->Draw == NULL)
			Con_Printf("Map %s could not be found or downloaded\n", cl.model_name[1]);

		                
		for (i = 2;i < MAX_MODELS && cl.model_name[i][0];i++)
			if ((cl.model_precache[i] = Mod_ForName(cl.model_name[i], false, false, cl.model_name[i][0] == '*' ? cl.model_name[1] : NULL))->Draw == NULL)
				Con_Printf("Model %s could not be found or downloaded\n", cl.model_name[i]);

		                         
		Mem_CheckSentinelsGlobal();

		                                                                    
		                   
		CL_SetupWorldModel();

		                                     
		CL_SetInfo("pmodel", va(vabuf, sizeof(vabuf), "%i", FS_CRCFile("progs/player.mdl", NULL)), true, true, true, true);
		CL_SetInfo("emodel", va(vabuf, sizeof(vabuf), "%i", FS_CRCFile("progs/eyes.mdl", NULL)), true, true, true, true);

		                                                               
		MSG_WriteByte(&cls.netcon->message, qw_clc_stringcmd);
		MSG_WriteString(&cls.netcon->message, va(vabuf, sizeof(vabuf), "prespawn %i 0 %i", cl.qw_servercount, cl.model_precache[1]->brush.qw_md4sum2));

		if (cls.qw_downloadmemory)
		{
			Mem_Free(cls.qw_downloadmemory);
			cls.qw_downloadmemory = NULL;
		}

		               
		cl.loadfinished = true;
		break;
	case dl_sound:
		if (cls.qw_downloadnumber == 0)
		{
			Con_Printf("Checking sounds...\n");
			cls.qw_downloadnumber = 1;
		}

		for (;cl.sound_name[cls.qw_downloadnumber][0];cls.qw_downloadnumber++)
		{
			                                                          
			if (!QW_CL_CheckOrDownloadFile(va(vabuf, sizeof(vabuf), "sound/%s", cl.sound_name[cls.qw_downloadnumber])))
				return;
		}

		cls.qw_downloadtype = dl_none;

		                                                       
		S_ClearUsed();

		                                         
		cl.sfx_wizhit = S_PrecacheSound(cl_sound_wizardhit.string, false, true);
		cl.sfx_knighthit = S_PrecacheSound(cl_sound_hknighthit.string, false, true);
		cl.sfx_tink1 = S_PrecacheSound(cl_sound_tink1.string, false, true);
		cl.sfx_ric1 = S_PrecacheSound(cl_sound_ric1.string, false, true);
		cl.sfx_ric2 = S_PrecacheSound(cl_sound_ric2.string, false, true);
		cl.sfx_ric3 = S_PrecacheSound(cl_sound_ric3.string, false, true);
		cl.sfx_r_exp3 = S_PrecacheSound(cl_sound_r_exp3.string, false, true);

		                          
		for (i = 1;i < MAX_SOUNDS && cl.sound_name[i][0];i++)
			cl.sound_precache[i] = S_PrecacheSound(cl.sound_name[i], true, true);

		                                                         
		                  

		                         
		Mem_CheckSentinelsGlobal();

		                                                  
		MSG_WriteByte(&cls.netcon->message, qw_clc_stringcmd);
		MSG_WriteString(&cls.netcon->message, va(vabuf, sizeof(vabuf), "modellist %i %i", cl.qw_servercount, 0));
		break;
	case dl_none:
	default:
		Con_Printf("Unknown download type.\n");
	}
}

static void QW_CL_ParseDownload(void)
{
	int size = (signed short)MSG_ReadShort(&cl_message);
	int percent = MSG_ReadByte(&cl_message);

	                                                                                                                      

	                                               
	if (!cls.netcon)
	{
		if (size > 0)
			cl_message.readcount += size;
		return;
	}

	if (size == -1)
	{
		Con_Printf("File not found.\n");
		QW_CL_RequestNextDownload();
		return;
	}

	if (cl_message.readcount + (unsigned short)size > cl_message.cursize)
		Host_Error("corrupt download message\n");

	                                                                  
	if (!cls.qw_downloadmemory || cls.qw_downloadmemorymaxsize < cls.qw_downloadmemorycursize + size)
	{
		unsigned char *old;
		while (cls.qw_downloadmemorymaxsize < cls.qw_downloadmemorycursize + size)
			cls.qw_downloadmemorymaxsize *= 2;
		old = cls.qw_downloadmemory;
		cls.qw_downloadmemory = (unsigned char *)Mem_Alloc(cls.permanentmempool, cls.qw_downloadmemorymaxsize);
		if (old)
		{
			memcpy(cls.qw_downloadmemory, old, cls.qw_downloadmemorycursize);
			Mem_Free(old);
		}
	}

	                                      
	MSG_ReadBytes(&cl_message, size, cls.qw_downloadmemory + cls.qw_downloadmemorycursize);
	cls.qw_downloadmemorycursize += size;
	cls.qw_downloadspeedcount += size;

	cls.qw_downloadpercent = percent;

	if (percent != 100)
	{
		                        
		MSG_WriteByte(&cls.netcon->message, qw_clc_stringcmd);
		MSG_WriteString(&cls.netcon->message, "nextdl");
	}
	else
	{
		                
		Con_Printf("Downloaded \"%s\"\n", cls.qw_downloadname);

		FS_WriteFile(cls.qw_downloadname, cls.qw_downloadmemory, cls.qw_downloadmemorycursize);

		cls.qw_downloadpercent = 0;

		                                                     
		QW_CL_RequestNextDownload();
	}
}

static void QW_CL_ParseModelList(void)
{
	int n;
	int nummodels = MSG_ReadByte(&cl_message);
	char *str;
	char vabuf[1024];

	                            
	for (;;)
	{
		str = MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring));
		if (!str[0])
			break;
		nummodels++;
		if (nummodels==MAX_MODELS)
			Host_Error("Server sent too many model precaches");
		if (strlen(str) >= MAX_QPATH)
			Host_Error("Server sent a precache name of %i characters (max %i)", (int)strlen(str), MAX_QPATH - 1);
		strlcpy(cl.model_name[nummodels], str, sizeof (cl.model_name[nummodels]));
	}

	n = MSG_ReadByte(&cl_message);
	if (n)
	{
		MSG_WriteByte(&cls.netcon->message, qw_clc_stringcmd);
		MSG_WriteString(&cls.netcon->message, va(vabuf, sizeof(vabuf), "modellist %i %i", cl.qw_servercount, n));
		return;
	}

	cls.signon = 2;
	cls.qw_downloadnumber = 0;
	cls.qw_downloadtype = dl_model;
	QW_CL_RequestNextDownload();
}

static void QW_CL_ParseSoundList(void)
{
	int n;
	int numsounds = MSG_ReadByte(&cl_message);
	char *str;
	char vabuf[1024];

	                            
	for (;;)
	{
		str = MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring));
		if (!str[0])
			break;
		numsounds++;
		if (numsounds==MAX_SOUNDS)
			Host_Error("Server sent too many sound precaches");
		if (strlen(str) >= MAX_QPATH)
			Host_Error("Server sent a precache name of %i characters (max %i)", (int)strlen(str), MAX_QPATH - 1);
		strlcpy(cl.sound_name[numsounds], str, sizeof (cl.sound_name[numsounds]));
	}

	n = MSG_ReadByte(&cl_message);

	if (n)
	{
		MSG_WriteByte(&cls.netcon->message, qw_clc_stringcmd);
		MSG_WriteString(&cls.netcon->message, va(vabuf, sizeof(vabuf), "soundlist %i %i", cl.qw_servercount, n));
		return;
	}

	cls.signon = 2;
	cls.qw_downloadnumber = 0;
	cls.qw_downloadtype = dl_sound;
	QW_CL_RequestNextDownload();
}

static void QW_CL_Skins_f(void)
{
	cls.qw_downloadnumber = 0;
	cls.qw_downloadtype = dl_skin;
	QW_CL_RequestNextDownload();
}

static void QW_CL_Changing_f(void)
{
	if (cls.qw_downloadmemory)                                  
		return;

	S_StopAllSounds();
	cl.intermission = 0;
	cls.signon = 1;	                                           
	Con_Printf("\nChanging map...\n");
}

void QW_CL_NextUpload(void)
{
	int r, percent, size;

	if (!cls.qw_uploaddata)
		return;

	r = cls.qw_uploadsize - cls.qw_uploadpos;
	if (r > 768)
		r = 768;
	size = min(1, cls.qw_uploadsize);
	percent = (cls.qw_uploadpos+r)*100/size;

	MSG_WriteByte(&cls.netcon->message, qw_clc_upload);
	MSG_WriteShort(&cls.netcon->message, r);
	MSG_WriteByte(&cls.netcon->message, percent);
	SZ_Write(&cls.netcon->message, cls.qw_uploaddata + cls.qw_uploadpos, r);

	Con_DPrintf("UPLOAD: %6d: %d written\n", cls.qw_uploadpos, r);

	cls.qw_uploadpos += r;

	if (cls.qw_uploadpos < cls.qw_uploadsize)
		return;

	Con_Printf("Upload completed\n");

	QW_CL_StopUpload();
}

void QW_CL_StartUpload(unsigned char *data, int size)
{
	                                          
	if (!cls.netcon)
		return;

	                                       
	QW_CL_StopUpload();

	Con_DPrintf("Starting upload of %d bytes...\n", size);

	cls.qw_uploaddata = (unsigned char *)Mem_Alloc(cls.permanentmempool, size);
	memcpy(cls.qw_uploaddata, data, size);
	cls.qw_uploadsize = size;
	cls.qw_uploadpos = 0;

	QW_CL_NextUpload();
}

#if 0
qboolean QW_CL_IsUploading(void)
{
	return cls.qw_uploaddata != NULL;
}
#endif

void QW_CL_StopUpload(void)
{
	if (cls.qw_uploaddata)
		Mem_Free(cls.qw_uploaddata);
	cls.qw_uploaddata = NULL;
	cls.qw_uploadsize = 0;
	cls.qw_uploadpos = 0;
}

static void QW_CL_ProcessUserInfo(int slot)
{
	int topcolor, bottomcolor;
	char temp[2048];
	InfoString_GetValue(cl.scores[slot].qw_userinfo, "name", cl.scores[slot].name, sizeof(cl.scores[slot].name));
	InfoString_GetValue(cl.scores[slot].qw_userinfo, "topcolor", temp, sizeof(temp));topcolor = atoi(temp);
	InfoString_GetValue(cl.scores[slot].qw_userinfo, "bottomcolor", temp, sizeof(temp));bottomcolor = atoi(temp);
	cl.scores[slot].colors = topcolor * 16 + bottomcolor;
	InfoString_GetValue(cl.scores[slot].qw_userinfo, "*spectator", temp, sizeof(temp));
	cl.scores[slot].qw_spectator = temp[0] != 0;
	InfoString_GetValue(cl.scores[slot].qw_userinfo, "team", cl.scores[slot].qw_team, sizeof(cl.scores[slot].qw_team));
	InfoString_GetValue(cl.scores[slot].qw_userinfo, "skin", cl.scores[slot].qw_skin, sizeof(cl.scores[slot].qw_skin));
	if (!cl.scores[slot].qw_skin[0])
		strlcpy(cl.scores[slot].qw_skin, "base", sizeof(cl.scores[slot].qw_skin));
	                   
}

static void QW_CL_UpdateUserInfo(void)
{
	int slot;
	slot = MSG_ReadByte(&cl_message);
	if (slot >= cl.maxclients)
	{
		Con_Printf("svc_updateuserinfo >= cl.maxclients\n");
		MSG_ReadLong(&cl_message);
		MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring));
		return;
	}
	cl.scores[slot].qw_userid = MSG_ReadLong(&cl_message);
	strlcpy(cl.scores[slot].qw_userinfo, MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)), sizeof(cl.scores[slot].qw_userinfo));

	QW_CL_ProcessUserInfo(slot);
}

static void QW_CL_SetInfo(void)
{
	int slot;
	char key[2048];
	char value[2048];
	slot = MSG_ReadByte(&cl_message);
	strlcpy(key, MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)), sizeof(key));
	strlcpy(value, MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)), sizeof(value));
	if (slot >= cl.maxclients)
	{
		Con_Printf("svc_setinfo >= cl.maxclients\n");
		return;
	}
	InfoString_SetValue(cl.scores[slot].qw_userinfo, sizeof(cl.scores[slot].qw_userinfo), key, value);

	QW_CL_ProcessUserInfo(slot);
}

static void QW_CL_ServerInfo(void)
{
	char key[2048];
	char value[2048];
	char temp[32];
	strlcpy(key, MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)), sizeof(key));
	strlcpy(value, MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)), sizeof(value));
	Con_DPrintf("SERVERINFO: %s=%s\n", key, value);
	InfoString_SetValue(cl.qw_serverinfo, sizeof(cl.qw_serverinfo), key, value);
	InfoString_GetValue(cl.qw_serverinfo, "teamplay", temp, sizeof(temp));
	cl.qw_teamplay = atoi(temp);
}

static void QW_CL_ParseNails(void)
{
	int i, j;
	int numnails = MSG_ReadByte(&cl_message);
	vec_t *v;
	unsigned char bits[6];
	for (i = 0;i < numnails;i++)
	{
		for (j = 0;j < 6;j++)
			bits[j] = MSG_ReadByte(&cl_message);
		if (cl.qw_num_nails >= 255)
			continue;
		v = cl.qw_nails[cl.qw_num_nails++];
		v[0] = ( ( bits[0] + ((bits[1]&15)<<8) ) <<1) - 4096;
		v[1] = ( ( (bits[1]>>4) + (bits[2]<<4) ) <<1) - 4096;
		v[2] = ( ( bits[3] + ((bits[4]&15)<<8) ) <<1) - 4096;
		v[3] = -360*(bits[4]>>4)/16;
		v[4] = 360*bits[5]/256;
		v[5] = 0;
	}
}

static void CL_UpdateItemsAndWeapon(void)
{
	int j;
	                              

	                  
	if (cl.olditems != cl.stats[STAT_ITEMS])
		for (j = 0;j < 32;j++)
			if ((cl.stats[STAT_ITEMS] & (1<<j)) && !(cl.olditems & (1<<j)))
				cl.item_gettime[j] = cl.time;
	cl.olditems = cl.stats[STAT_ITEMS];

	                                           
	if (cl.activeweapon != cl.stats[STAT_ACTIVEWEAPON])
		cl.weapontime = cl.time;
	cl.activeweapon = cl.stats[STAT_ACTIVEWEAPON];
}

#define LOADPROGRESSWEIGHT_SOUND            1.0
#define LOADPROGRESSWEIGHT_MODEL            4.0
#define LOADPROGRESSWEIGHT_WORLDMODEL      30.0
#define LOADPROGRESSWEIGHT_WORLDMODEL_INIT  2.0

static void CL_BeginDownloads(qboolean aborteddownload)
{
	char vabuf[1024];
	                               
	if (cls.protocol == PROTOCOL_QUAKEWORLD)
		return;

	                                                  
	if(Curl_Have_forthismap())
	{
		Curl_Register_predownload();                   
		return;
	}

	                    
	                                                 
	if(!cl.loadbegun)
		SCR_PushLoadingScreen(false, "Loading precaches", 1);
	cl.loadbegun = true;

	                                                                          
	if (cls.qw_downloadname[0])
		return;

	if (cl.downloadcsqc)
	{
		size_t progsize;
		cl.downloadcsqc = false;
		if (cls.netcon
		 && !sv.active
		 && csqc_progname.string
		 && csqc_progname.string[0]
		 && csqc_progcrc.integer >= 0
		 && cl_serverextension_download.integer
		 && (FS_CRCFile(csqc_progname.string, &progsize) != csqc_progcrc.integer || ((int)progsize != csqc_progsize.integer && csqc_progsize.integer != -1))
		 && !FS_FileExists(va(vabuf, sizeof(vabuf), "dlcache/%s.%i.%i", csqc_progname.string, csqc_progsize.integer, csqc_progcrc.integer)))
		{
			Con_Printf("Downloading new CSQC code to dlcache/%s.%i.%i\n", csqc_progname.string, csqc_progsize.integer, csqc_progcrc.integer);
			if(cl_serverextension_download.integer == 2 && FS_HasZlib())
				Cmd_ForwardStringToServer(va(vabuf, sizeof(vabuf), "download %s deflate", csqc_progname.string));
			else
				Cmd_ForwardStringToServer(va(vabuf, sizeof(vabuf), "download %s", csqc_progname.string));
			return;
		}
	}

	if (cl.loadmodel_current < cl.loadmodel_total)
	{
		                 
		if(cl.loadmodel_current == 1)
		{
			                                                                                   
			SCR_PushLoadingScreen(false, "Loading precached models",
				(
					(cl.loadmodel_total - 1) * LOADPROGRESSWEIGHT_MODEL
				+	LOADPROGRESSWEIGHT_WORLDMODEL
				+	LOADPROGRESSWEIGHT_WORLDMODEL_INIT
				) / (
					(cl.loadmodel_total - 1) * LOADPROGRESSWEIGHT_MODEL
				+	LOADPROGRESSWEIGHT_WORLDMODEL
				+	LOADPROGRESSWEIGHT_WORLDMODEL_INIT
				+	cl.loadsound_total * LOADPROGRESSWEIGHT_SOUND
				)
			);
			SCR_BeginLoadingPlaque(false);
		}
		for (;cl.loadmodel_current < cl.loadmodel_total;cl.loadmodel_current++)
		{
			SCR_PushLoadingScreen(false, cl.model_name[cl.loadmodel_current],
				(
					(cl.loadmodel_current == 1) ? LOADPROGRESSWEIGHT_WORLDMODEL : LOADPROGRESSWEIGHT_MODEL
				) / (
					(cl.loadmodel_total - 1) * LOADPROGRESSWEIGHT_MODEL
				+	LOADPROGRESSWEIGHT_WORLDMODEL
				+	LOADPROGRESSWEIGHT_WORLDMODEL_INIT
				)
			);
			if (cl.model_precache[cl.loadmodel_current] && cl.model_precache[cl.loadmodel_current]->Draw)
			{
				SCR_PopLoadingScreen(false);
				if(cl.loadmodel_current == 1)
				{
					SCR_PushLoadingScreen(false, cl.model_name[cl.loadmodel_current], 1.0 / cl.loadmodel_total);
					SCR_PopLoadingScreen(false);
				}
				continue;
			}
			CL_KeepaliveMessage(true);

			                                                                                
			if (sv.active)
				cl.model_precache[cl.loadmodel_current] = sv.models[cl.loadmodel_current];
			else
			{
				if(cl.loadmodel_current == 1)
				{
					                                                                                              
					Mod_FreeQ3Shaders();
				}
				cl.model_precache[cl.loadmodel_current] = Mod_ForName(cl.model_name[cl.loadmodel_current], false, false, cl.model_name[cl.loadmodel_current][0] == '*' ? cl.model_name[1] : NULL);
			}
			SCR_PopLoadingScreen(false);
			if (cl.model_precache[cl.loadmodel_current] && cl.model_precache[cl.loadmodel_current]->Draw && cl.loadmodel_current == 1)
			{
				                                                             
				SCR_PushLoadingScreen(true, "world model setup",
					(
						LOADPROGRESSWEIGHT_WORLDMODEL_INIT
					) / (
						(cl.loadmodel_total - 1) * LOADPROGRESSWEIGHT_MODEL
					+	LOADPROGRESSWEIGHT_WORLDMODEL
					+	LOADPROGRESSWEIGHT_WORLDMODEL_INIT
					)
				);
				CL_SetupWorldModel();
				SCR_PopLoadingScreen(true);
				if (!cl.loadfinished && cl_joinbeforedownloadsfinish.integer)
				{
					cl.loadfinished = true;
					                                                         
					if (cls.netcon)
						Cmd_ForwardStringToServer("prespawn");
				}
			}
		}
		SCR_PopLoadingScreen(false);
		                          
	}

	if (cl.loadsound_current < cl.loadsound_total)
	{
		                 
		if(cl.loadsound_current == 1)
			SCR_PushLoadingScreen(false, "Loading precached sounds",
				(
					cl.loadsound_total * LOADPROGRESSWEIGHT_SOUND
				) / (
					(cl.loadmodel_total - 1) * LOADPROGRESSWEIGHT_MODEL
				+	LOADPROGRESSWEIGHT_WORLDMODEL
				+	LOADPROGRESSWEIGHT_WORLDMODEL_INIT
				+	cl.loadsound_total * LOADPROGRESSWEIGHT_SOUND
				)
			);
		for (;cl.loadsound_current < cl.loadsound_total;cl.loadsound_current++)
		{
			SCR_PushLoadingScreen(false, cl.sound_name[cl.loadsound_current], 1.0 / cl.loadsound_total);
			if (cl.sound_precache[cl.loadsound_current] && S_IsSoundPrecached(cl.sound_precache[cl.loadsound_current]))
			{
				SCR_PopLoadingScreen(false);
				continue;
			}
			CL_KeepaliveMessage(true);
			cl.sound_precache[cl.loadsound_current] = S_PrecacheSound(cl.sound_name[cl.loadsound_current], false, true);
			SCR_PopLoadingScreen(false);
		}
		SCR_PopLoadingScreen(false);
		                          
	}

	if(IS_NEXUIZ_DERIVED(gamemode))
		Cvar_SetValueQuick(&cl_serverextension_download, false);
		                                                                                 
		                                                                        
		                                                                         
		                                                
		                                                                                       
		                  
		                                                                

	                                                                     
	                                                               

	if (cl.downloadmodel_current < cl.loadmodel_total)
	{
		                 

		for (;cl.downloadmodel_current < cl.loadmodel_total;cl.downloadmodel_current++)
		{
			if (aborteddownload)
			{

				if (cl.downloadmodel_current == 1)
				{
					                                                      
					Mod_FreeQ3Shaders();
					CL_SetupWorldModel();
					if (!cl.loadfinished && cl_joinbeforedownloadsfinish.integer)
					{
						cl.loadfinished = true;
						                                                         
						if (cls.netcon)
							Cmd_ForwardStringToServer("prespawn");
					}
				}
				aborteddownload = false;
				continue;
			}
			if (cl.model_precache[cl.downloadmodel_current] && cl.model_precache[cl.downloadmodel_current]->Draw)
				continue;
			CL_KeepaliveMessage(true);
			if (cl.model_name[cl.downloadmodel_current][0] != '*' && strcmp(cl.model_name[cl.downloadmodel_current], "null") && !FS_FileExists(cl.model_name[cl.downloadmodel_current]))
			{
				if (cl.downloadmodel_current == 1)
					Con_Printf("Map %s not found\n", cl.model_name[cl.downloadmodel_current]);
				else
					Con_Printf("Model %s not found\n", cl.model_name[cl.downloadmodel_current]);
				                                                         
				if (cl_serverextension_download.integer && cls.netcon && cl.model_name[cl.downloadmodel_current][0] != '*' && !sv.active)
				{
					Cmd_ForwardStringToServer(va(vabuf, sizeof(vabuf), "download %s", cl.model_name[cl.downloadmodel_current]));
					                                                     
					return;
				}
			}

			if(cl.downloadmodel_current == 1)
			{
				                                                                                              
				Mod_FreeQ3Shaders();
			}

			cl.model_precache[cl.downloadmodel_current] = Mod_ForName(cl.model_name[cl.downloadmodel_current], false, true, cl.model_name[cl.downloadmodel_current][0] == '*' ? cl.model_name[1] : NULL);
			if (cl.downloadmodel_current == 1)
			{
				                                                             
				                                                             
				                                           
				CL_SetupWorldModel();
				if (!cl.loadfinished && cl_joinbeforedownloadsfinish.integer)
				{
					cl.loadfinished = true;
					                                                         
					if (cls.netcon)
						Cmd_ForwardStringToServer("prespawn");
				}
			}
		}

		                          
	}

	if (cl.downloadsound_current < cl.loadsound_total)
	{
		                 

		for (;cl.downloadsound_current < cl.loadsound_total;cl.downloadsound_current++)
		{
			char soundname[MAX_QPATH];
			if (aborteddownload)
			{
				aborteddownload = false;
				continue;
			}
			if (cl.sound_precache[cl.downloadsound_current] && S_IsSoundPrecached(cl.sound_precache[cl.downloadsound_current]))
				continue;
			CL_KeepaliveMessage(true);
			dpsnprintf(soundname, sizeof(soundname), "sound/%s", cl.sound_name[cl.downloadsound_current]);
			if (!FS_FileExists(soundname) && !FS_FileExists(cl.sound_name[cl.downloadsound_current]))
			{
				Con_Printf("Sound %s not found\n", soundname);
				if (cl_serverextension_download.integer && cls.netcon && !sv.active)
				{
					Cmd_ForwardStringToServer(va(vabuf, sizeof(vabuf), "download %s", soundname));
					                                                     
					return;
				}
			}
			cl.sound_precache[cl.downloadsound_current] = S_PrecacheSound(cl.sound_name[cl.downloadsound_current], false, true);
		}

		                          
	}

	SCR_PopLoadingScreen(false);

	if (!cl.loadfinished)
	{
		cl.loadfinished = true;

		                         
		Mem_CheckSentinelsGlobal();

		                                                         
		if (cls.netcon)
			Cmd_ForwardStringToServer("prespawn");
	}
}

static void CL_BeginDownloads_f(void)
{
	                                                                          
	                                              
	if(cl.loadbegun)
		Con_Printf("cl_begindownloads is only valid once per match\n");
	else
		CL_BeginDownloads(false);
}

static void CL_StopDownload(int size, int crc)
{
	if (cls.qw_downloadmemory && cls.qw_downloadmemorycursize == size && CRC_Block(cls.qw_downloadmemory, cls.qw_downloadmemorycursize) == crc)
	{
		int existingcrc;
		size_t existingsize;
		const char *extension;

		if(cls.qw_download_deflate)
		{
			unsigned char *out;
			size_t inflated_size;
			out = FS_Inflate(cls.qw_downloadmemory, cls.qw_downloadmemorycursize, &inflated_size, tempmempool);
			Mem_Free(cls.qw_downloadmemory);
			if(out)
			{
				Con_Printf("Inflated download: new size: %u (%g%%)\n", (unsigned)inflated_size, 100.0 - 100.0*(cls.qw_downloadmemorycursize / (float)inflated_size));
				cls.qw_downloadmemory = out;
				cls.qw_downloadmemorycursize = (int)inflated_size;
			}
			else
			{
				cls.qw_downloadmemory = NULL;
				cls.qw_downloadmemorycursize = 0;
				Con_Printf("Cannot inflate download, possibly corrupt or zlib not present\n");
			}
		}

		if(!cls.qw_downloadmemory)
		{
			Con_Printf("Download \"%s\" is corrupt (see above!)\n", cls.qw_downloadname);
		}
		else
		{
			crc = CRC_Block(cls.qw_downloadmemory, cls.qw_downloadmemorycursize);
			size = cls.qw_downloadmemorycursize;
			                
			                                                
			                                          
			existingcrc = FS_CRCFile(cls.qw_downloadname, &existingsize);
			if (existingsize || IS_NEXUIZ_DERIVED(gamemode) || !strcmp(cls.qw_downloadname, csqc_progname.string))
				                                                                                                                         
			{
				if ((int)existingsize != size || existingcrc != crc)
				{
					                                                       
					char name[MAX_QPATH*2];
					dpsnprintf(name, sizeof(name), "dlcache/%s.%i.%i", cls.qw_downloadname, size, crc);
					if (!FS_FileExists(name))
					{
						Con_Printf("Downloaded \"%s\" (%i bytes, %i CRC)\n", name, size, crc);
						FS_WriteFile(name, cls.qw_downloadmemory, cls.qw_downloadmemorycursize);
						if(!strcmp(cls.qw_downloadname, csqc_progname.string))
						{
							if(cls.caughtcsprogsdata)
								Mem_Free(cls.caughtcsprogsdata);
							cls.caughtcsprogsdata = (unsigned char *) Mem_Alloc(cls.permanentmempool, cls.qw_downloadmemorycursize);
							memcpy(cls.caughtcsprogsdata, cls.qw_downloadmemory, cls.qw_downloadmemorycursize);
							cls.caughtcsprogsdatasize = cls.qw_downloadmemorycursize;
							Con_DPrintf("Buffered \"%s\"\n", name);
						}
					}
				}
			}
			else
			{
				                                                        
				                                  
				                                                              
				                                                                  
				                
				Con_Printf("Downloaded \"%s\" (%i bytes, %i CRC)\n", cls.qw_downloadname, size, crc);
				FS_WriteFile(cls.qw_downloadname, cls.qw_downloadmemory, cls.qw_downloadmemorycursize);
				extension = FS_FileExtension(cls.qw_downloadname);
				if (!strcasecmp(extension, "pak") || !strcasecmp(extension, "pk3"))
					FS_Rescan();
			}
		}
	}
	else if (cls.qw_downloadmemory && size)
	{
		Con_Printf("Download \"%s\" is corrupt (%i bytes, %i CRC, should be %i bytes, %i CRC), discarding\n", cls.qw_downloadname, size, crc, (int)cls.qw_downloadmemorycursize, (int)CRC_Block(cls.qw_downloadmemory, cls.qw_downloadmemorycursize));
		CL_BeginDownloads(true);
	}

	if (cls.qw_downloadmemory)
		Mem_Free(cls.qw_downloadmemory);
	cls.qw_downloadmemory = NULL;
	cls.qw_downloadname[0] = 0;
	cls.qw_downloadmemorymaxsize = 0;
	cls.qw_downloadmemorycursize = 0;
	cls.qw_downloadpercent = 0;
}

static void CL_ParseDownload(void)
{
	int i, start, size;
	static unsigned char data[NET_MAXMESSAGE];
	start = MSG_ReadLong(&cl_message);
	size = (unsigned short)MSG_ReadShort(&cl_message);

	                                                                    
	for (i = 0;i < CL_MAX_DOWNLOADACKS;i++)
	{
		if (!cls.dp_downloadack[i].start && !cls.dp_downloadack[i].size)
		{
			cls.dp_downloadack[i].start = start;
			cls.dp_downloadack[i].size = size;
			break;
		}
	}

	MSG_ReadBytes(&cl_message, size, data);

	if (!cls.qw_downloadname[0])
	{
		if (size > 0)
			Con_Printf("CL_ParseDownload: received %i bytes with no download active\n", size);
		return;
	}

	if (start + size > cls.qw_downloadmemorymaxsize)
		Host_Error("corrupt download message\n");

	                                                               
	                          
	memcpy(cls.qw_downloadmemory + start, data, size);
	cls.qw_downloadmemorycursize = start + size;
	cls.qw_downloadpercent = (int)floor((start+size) * 100.0 / cls.qw_downloadmemorymaxsize);
	cls.qw_downloadpercent = bound(0, cls.qw_downloadpercent, 100);
	cls.qw_downloadspeedcount += size;
}

static void CL_DownloadBegin_f(void)
{
	int size = atoi(Cmd_Argv(1));

	if (size < 0 || size > 1<<30 || FS_CheckNastyPath(Cmd_Argv(2), false))
	{
		Con_Printf("cl_downloadbegin: received bogus information\n");
		CL_StopDownload(0, 0);
		return;
	}

	if (cls.qw_downloadname[0])
		Con_Printf("Download of %s aborted\n", cls.qw_downloadname);

	CL_StopDownload(0, 0);

	                                                             
	strlcpy(cls.qw_downloadname, Cmd_Argv(2), sizeof(cls.qw_downloadname));
	cls.qw_downloadmemorymaxsize = size;
	cls.qw_downloadmemory = (unsigned char *) Mem_Alloc(cls.permanentmempool, cls.qw_downloadmemorymaxsize);
	cls.qw_downloadnumber++;

	cls.qw_download_deflate = false;
	if(Cmd_Argc() >= 4)
	{
		if(!strcmp(Cmd_Argv(3), "deflate"))
			cls.qw_download_deflate = true;
		                               
	}

	Cmd_ForwardStringToServer("sv_startdownload");
}

static void CL_StopDownload_f(void)
{
	Curl_CancelAll();
	if (cls.qw_downloadname[0])
	{
		Con_Printf("Download of %s aborted\n", cls.qw_downloadname);
		CL_StopDownload(0, 0);
	}
	CL_BeginDownloads(true);
}

static void CL_DownloadFinished_f(void)
{
	if (Cmd_Argc() < 3)
	{
		Con_Printf("Malformed cl_downloadfinished command\n");
		return;
	}
	CL_StopDownload(atoi(Cmd_Argv(1)), atoi(Cmd_Argv(2)));
	CL_BeginDownloads(false);
}

static void CL_SendPlayerInfo(void)
{
	char vabuf[1024];
	MSG_WriteByte (&cls.netcon->message, clc_stringcmd);
	MSG_WriteString (&cls.netcon->message, va(vabuf, sizeof(vabuf), "name \"%s\"", cl_name.string));

	MSG_WriteByte (&cls.netcon->message, clc_stringcmd);
	MSG_WriteString (&cls.netcon->message, va(vabuf, sizeof(vabuf), "color %i %i", cl_color.integer >> 4, cl_color.integer & 15));

	MSG_WriteByte (&cls.netcon->message, clc_stringcmd);
	MSG_WriteString (&cls.netcon->message, va(vabuf, sizeof(vabuf), "rate %i", cl_rate.integer));

	MSG_WriteByte (&cls.netcon->message, clc_stringcmd);
	MSG_WriteString (&cls.netcon->message, va(vabuf, sizeof(vabuf), "rate_burstsize %i", cl_rate_burstsize.integer));

	if (cl_pmodel.integer)
	{
		MSG_WriteByte (&cls.netcon->message, clc_stringcmd);
		MSG_WriteString (&cls.netcon->message, va(vabuf, sizeof(vabuf), "pmodel %i", cl_pmodel.integer));
	}
	if (*cl_playermodel.string)
	{
		MSG_WriteByte (&cls.netcon->message, clc_stringcmd);
		MSG_WriteString (&cls.netcon->message, va(vabuf, sizeof(vabuf), "playermodel %s", cl_playermodel.string));
	}
	if (*cl_playerskin.string)
	{
		MSG_WriteByte (&cls.netcon->message, clc_stringcmd);
		MSG_WriteString (&cls.netcon->message, va(vabuf, sizeof(vabuf), "playerskin %s", cl_playerskin.string));
	}
}

  
                     
              

                                                               
                     
  
static void CL_SignonReply (void)
{
	Con_DPrintf("CL_SignonReply: %i\n", cls.signon);

	switch (cls.signon)
	{
	case 1:
		if (cls.netcon)
		{
			                                             
			                                                                 
			CL_SendPlayerInfo();

			                                       
			                                                                 
			                                                       
			Cbuf_AddText("\ncl_begindownloads\n");

			                                                      
			                                                     
		}
		else                                                                   
			CL_BeginDownloads(false);
		break;

	case 2:
		if (cls.netcon)
		{
			                                                                  
			                             
			                       

			                                                                       
			MSG_WriteByte (&cls.netcon->message, clc_stringcmd);
			MSG_WriteString (&cls.netcon->message, "spawn");
		}
		break;

	case 3:
		if (cls.netcon)
		{
			MSG_WriteByte (&cls.netcon->message, clc_stringcmd);
			MSG_WriteString (&cls.netcon->message, "begin");
		}
		break;

	case 4:
		                                                                      
		                                                                
		                                                                     
		Mod_FreeQ3Shaders();
		Mod_PurgeUnused();
		S_PurgeUnused();

		Con_ClearNotify();
		if (COM_CheckParm("-profilegameonly"))
			Sys_AllowProfiling(true);
		break;
	}
}

  
                  
                  
                  
  
static void CL_ParseServerInfo (void)
{
	char *str;
	int i;
	protocolversion_t protocol;
	int nummodels, numsounds;
	char vabuf[1024];

	                                                                    
	CL_VideoStop();

	Con_DPrint("Serverinfo packet received.\n");
	Collision_Cache_Reset(true);

	                                                         
	if (!sv.active)
	{
		SCR_BeginLoadingPlaque(false);
		S_StopAllSounds();
		                                                                      
		Mod_FreeQ3Shaders();
	}

	                         
	Mem_CheckSentinelsGlobal();

	                                 
	Cvar_SetValueQuick(&cl_serverextension_download, 0);

  
                                 
  
	CL_ClearState ();

                                
	i = MSG_ReadLong(&cl_message);
	protocol = Protocol_EnumForNumber(i);
	if (protocol == PROTOCOL_UNKNOWN)
	{
		Host_Error("CL_ParseServerInfo: Server is unrecognized protocol number (%i)", i);
		return;
	}
	                                                                    
	if (protocol == PROTOCOL_QUAKEDP && cls.demoplayback && gamemode == GAME_NEHAHRA)
		protocol = PROTOCOL_NEHAHRAMOVIE;
	cls.protocol = protocol;
	Con_DPrintf("Server protocol is %s\n", Protocol_NameForEnum(cls.protocol));

	cl.num_entities = 1;

	if (protocol == PROTOCOL_QUAKEWORLD)
	{
		char gamedir[1][MAX_QPATH];

		cl.qw_servercount = MSG_ReadLong(&cl_message);

		str = MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring));
		Con_Printf("server gamedir is %s\n", str);
		strlcpy(gamedir[0], str, sizeof(gamedir[0]));

		                           
		if (!FS_ChangeGameDirs(1, gamedir, true, false))
			Host_Error("CL_ParseServerInfo: unable to switch to server specified gamedir");

		cl.gametype = GAME_DEATHMATCH;
		cl.maxclients = 32;

		                      
		i = MSG_ReadByte(&cl_message);
		                                                                                                                                              
		                                   
		cl.realplayerentity = cl.playerentity = cl.viewentity = (i & 127) + 1;
		cl.scores = (scoreboard_t *)Mem_Alloc(cls.levelmempool, cl.maxclients*sizeof(*cl.scores));

		                          
		str = MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring));
		strlcpy (cl.worldmessage, str, sizeof(cl.worldmessage));

		                                                       
		cl.movevars_gravity            = MSG_ReadFloat(&cl_message);
		cl.movevars_stopspeed          = MSG_ReadFloat(&cl_message);
		cl.movevars_maxspeed           = MSG_ReadFloat(&cl_message);
		cl.movevars_spectatormaxspeed  = MSG_ReadFloat(&cl_message);
		cl.movevars_accelerate         = MSG_ReadFloat(&cl_message);
		cl.movevars_airaccelerate      = MSG_ReadFloat(&cl_message);
		cl.movevars_wateraccelerate    = MSG_ReadFloat(&cl_message);
		cl.movevars_friction           = MSG_ReadFloat(&cl_message);
		cl.movevars_waterfriction      = MSG_ReadFloat(&cl_message);
		cl.movevars_entgravity         = MSG_ReadFloat(&cl_message);

		                                        
		cl.movevars_wallfriction = 0;
		cl.movevars_timescale = 1;
		cl.movevars_jumpvelocity = 270;
		cl.movevars_edgefriction = 1;
		cl.movevars_maxairspeed = 30;
		cl.movevars_stepheight = 18;
		cl.movevars_airaccel_qw = 1;
		cl.movevars_airaccel_sideways_friction = 0;

		                                                              
		Con_Printf("\n\n<===================================>\n\n\2%s\n", str);

		                         
		Mem_CheckSentinelsGlobal();

		if (cls.netcon)
		{
			MSG_WriteByte(&cls.netcon->message, qw_clc_stringcmd);
			MSG_WriteString(&cls.netcon->message, va(vabuf, sizeof(vabuf), "soundlist %i %i", cl.qw_servercount, 0));
		}

		cl.loadbegun = false;
		cl.loadfinished = false;

		cls.state = ca_connected;
		cls.signon = 1;

		                                                                 
		                      
		                                               
		                                                              

		strlcpy(cl.worldname, "", sizeof(cl.worldname));
		strlcpy(cl.worldnamenoextension, "", sizeof(cl.worldnamenoextension));
		strlcpy(cl.worldbasename, "qw", sizeof(cl.worldbasename));
		Cvar_SetQuick(&cl_worldname, cl.worldname);
		Cvar_SetQuick(&cl_worldnamenoextension, cl.worldnamenoextension);
		Cvar_SetQuick(&cl_worldbasename, cl.worldbasename);

		                         
		Mem_CheckSentinelsGlobal();
	}
	else
	{
	                   
		cl.maxclients = MSG_ReadByte(&cl_message);
		if (cl.maxclients < 1 || cl.maxclients > MAX_SCOREBOARD)
		{
			Host_Error("Bad maxclients (%u) from server", cl.maxclients);
			return;
		}
		cl.scores = (scoreboard_t *)Mem_Alloc(cls.levelmempool, cl.maxclients*sizeof(*cl.scores));

	                 
		cl.gametype = MSG_ReadByte(&cl_message);
		                                                            
		                                        
		if (cl.maxclients == 1 && cls.protocol == PROTOCOL_QUAKE)
			cl.gametype = GAME_COOP;

	                       
		str = MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring));
		strlcpy (cl.worldmessage, str, sizeof(cl.worldmessage));

	                                                              
		if (cls.protocol != PROTOCOL_NEHAHRAMOVIE)                                              
			Con_Printf("\n<===================================>\n\n\2%s\n", str);

		                         
		Mem_CheckSentinelsGlobal();

		                            
		for (nummodels=1 ; ; nummodels++)
		{
			str = MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring));
			if (!str[0])
				break;
			if (nummodels==MAX_MODELS)
				Host_Error ("Server sent too many model precaches");
			if (strlen(str) >= MAX_QPATH)
				Host_Error ("Server sent a precache name of %i characters (max %i)", (int)strlen(str), MAX_QPATH - 1);
			strlcpy (cl.model_name[nummodels], str, sizeof (cl.model_name[nummodels]));
		}
		                            
		for (numsounds=1 ; ; numsounds++)
		{
			str = MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring));
			if (!str[0])
				break;
			if (numsounds==MAX_SOUNDS)
				Host_Error("Server sent too many sound precaches");
			if (strlen(str) >= MAX_QPATH)
				Host_Error("Server sent a precache name of %i characters (max %i)", (int)strlen(str), MAX_QPATH - 1);
			strlcpy (cl.sound_name[numsounds], str, sizeof (cl.sound_name[numsounds]));
		}

		                                                                                                      
		strlcpy(cl.worldname, cl.model_name[1], sizeof(cl.worldname));
		FS_StripExtension(cl.worldname, cl.worldnamenoextension, sizeof(cl.worldnamenoextension));
		strlcpy(cl.worldbasename, !strncmp(cl.worldnamenoextension, "maps/", 5) ? cl.worldnamenoextension + 5 : cl.worldnamenoextension, sizeof(cl.worldbasename));
		Cvar_SetQuick(&cl_worldmessage, cl.worldmessage);
		Cvar_SetQuick(&cl_worldname, cl.worldname);
		Cvar_SetQuick(&cl_worldnamenoextension, cl.worldnamenoextension);
		Cvar_SetQuick(&cl_worldbasename, cl.worldbasename);

		                                                                         
		                             
		if (!sv.active)
			Mod_ClearUsed();
		for (i = 1;i < nummodels;i++)
			Mod_FindName(cl.model_name[i], cl.model_name[i][0] == '*' ? cl.model_name[1] : NULL);
		                                                                     
		cl.model_bolt = Mod_ForName("progs/bolt.mdl", false, false, NULL);
		cl.model_bolt2 = Mod_ForName("progs/bolt2.mdl", false, false, NULL);
		cl.model_bolt3 = Mod_ForName("progs/bolt3.mdl", false, false, NULL);
		cl.model_beam = Mod_ForName("progs/beam.mdl", false, false, NULL);

		                                                         
		                    
		                  

		                                                       
		S_ClearUsed();

		                                         
		cl.sfx_wizhit = S_PrecacheSound(cl_sound_wizardhit.string, false, true);
		cl.sfx_knighthit = S_PrecacheSound(cl_sound_hknighthit.string, false, true);
		cl.sfx_tink1 = S_PrecacheSound(cl_sound_tink1.string, false, true);
		cl.sfx_ric1 = S_PrecacheSound(cl_sound_ric1.string, false, true);
		cl.sfx_ric2 = S_PrecacheSound(cl_sound_ric2.string, false, true);
		cl.sfx_ric3 = S_PrecacheSound(cl_sound_ric3.string, false, true);
		cl.sfx_r_exp3 = S_PrecacheSound(cl_sound_r_exp3.string, false, true);

		                          
		for (i = 1;i < MAX_SOUNDS && cl.sound_name[i][0];i++)
			cl.sound_precache[i] = S_PrecacheSound(cl.sound_name[i], true, true);

		                                            
		cl.loadmodel_current = 1;
		cl.downloadmodel_current = 1;
		cl.loadmodel_total = nummodels;
		cl.loadsound_current = 1;
		cl.downloadsound_current = 1;
		cl.loadsound_total = numsounds;
		cl.downloadcsqc = true;
		cl.loadbegun = false;
		cl.loadfinished = false;
		cl.loadcsqc = true;

		                         
		Mem_CheckSentinelsGlobal();

	                                                                                                  
		if (cl_autodemo.integer && cls.netcon && cls.protocol != PROTOCOL_QUAKEWORLD)
		{
			char demofile[MAX_OSPATH];

			if (cls.demorecording)
			{
				                                        
				CL_Stop_f();
			}

			                        
			dpsnprintf (demofile, sizeof(demofile), "%s_%s.dem", Sys_TimeString (cl_autodemo_nameformat.string), cl.worldbasename);

			Con_Printf ("Auto-recording to %s.\n", demofile);

			                                 
			Cvar_SetValueQuick(&cl_autodemo_delete,
				(cl_autodemo_delete.integer & ~0x1)
				|
				((cl_autodemo_delete.integer & 0x2) ? 0x1 : 0)
			);

			cls.demofile = FS_OpenRealFile(demofile, "wb", false);
			if (cls.demofile)
			{
				cls.forcetrack = -1;
				FS_Printf (cls.demofile, "%i\n", cls.forcetrack);
				cls.demorecording = true;
				strlcpy(cls.demoname, demofile, sizeof(cls.demoname));
				cls.demo_lastcsprogssize = -1;
				cls.demo_lastcsprogscrc = -1;
			}
			else
				Con_Print ("ERROR: couldn't open.\n");
		}
	}
	cl.islocalgame = NetConn_IsLocalGame();
}

void CL_ValidateState(entity_state_t *s)
{
	dp_model_t *model;

	if (!s->active)
		return;

	if (s->modelindex >= MAX_MODELS)
		Host_Error("CL_ValidateState: modelindex (%i) >= MAX_MODELS (%i)\n", s->modelindex, MAX_MODELS);

	                                                                         
	                                                                      
	                                                 
	                                                            

	                               
	if (!(s->flags & RENDER_COLORMAPPED) && s->colormap > cl.maxclients)
		Con_DPrintf("CL_ValidateState: colormap (%i) > cl.maxclients (%i)\n", s->colormap, cl.maxclients);

	if (developer_extra.integer)
	{
		model = CL_GetModelByIndex(s->modelindex);
		if (model && model->type && s->frame >= model->numframes)
			Con_DPrintf("CL_ValidateState: no such frame %i in \"%s\" (which has %i frames)\n", s->frame, model->name, model->numframes);
		if (model && model->type && s->skin > 0 && s->skin >= model->numskins && !(s->lightpflags & PFLAGS_FULLDYNAMIC))
			Con_DPrintf("CL_ValidateState: no such skin %i in \"%s\" (which has %i skins)\n", s->skin, model->name, model->numskins);
	}
}

void CL_MoveLerpEntityStates(entity_t *ent)
{
	float odelta[3], adelta[3];
	VectorSubtract(ent->state_current.origin, ent->persistent.neworigin, odelta);
	VectorSubtract(ent->state_current.angles, ent->persistent.newangles, adelta);
	if (!ent->state_previous.active || ent->state_previous.modelindex != ent->state_current.modelindex)
	{
		                                                     
		ent->persistent.lerpdeltatime = 0;
		ent->persistent.lerpstarttime = cl.mtime[1];
		VectorCopy(ent->state_current.origin, ent->persistent.oldorigin);
		VectorCopy(ent->state_current.angles, ent->persistent.oldangles);
		VectorCopy(ent->state_current.origin, ent->persistent.neworigin);
		VectorCopy(ent->state_current.angles, ent->persistent.newangles);
		                                        
		ent->render.framegroupblend[0].frame = ent->render.framegroupblend[1].frame = ent->state_current.frame;
		ent->render.framegroupblend[0].start = ent->render.framegroupblend[1].start = cl.time;
		ent->render.framegroupblend[0].lerp = 1;ent->render.framegroupblend[1].lerp = 0;
		ent->render.shadertime = cl.time;
		                                 
		ent->persistent.muzzleflash = 0;
		ent->persistent.trail_allowed = false;
	}
	else if ((ent->state_previous.effects & EF_TELEPORT_BIT) != (ent->state_current.effects & EF_TELEPORT_BIT))
	{
		                             
		ent->persistent.lerpdeltatime = 0;
		ent->persistent.lerpstarttime = cl.mtime[1];
		VectorCopy(ent->state_current.origin, ent->persistent.oldorigin);
		VectorCopy(ent->state_current.angles, ent->persistent.oldangles);
		VectorCopy(ent->state_current.origin, ent->persistent.neworigin);
		VectorCopy(ent->state_current.angles, ent->persistent.newangles);
		ent->persistent.trail_allowed = false;

		                                                            
		                                          
		                                                                             
		                                             
		{
			ent->render.framegroupblend[0].frame = ent->render.framegroupblend[1].frame = ent->state_current.frame;
			ent->render.framegroupblend[0].start = ent->render.framegroupblend[1].start = cl.time;
			ent->render.framegroupblend[0].lerp = 1;ent->render.framegroupblend[1].lerp = 0;
		}

		                                                                     
	}
	else if ((ent->state_previous.effects & EF_RESTARTANIM_BIT) != (ent->state_current.effects & EF_RESTARTANIM_BIT))
	{
		ent->render.framegroupblend[1] = ent->render.framegroupblend[0];
		ent->render.framegroupblend[1].lerp = 1;
		ent->render.framegroupblend[0].frame = ent->state_current.frame;
		ent->render.framegroupblend[0].start = cl.time;
		ent->render.framegroupblend[0].lerp = 0;
	}
	else if (DotProduct(odelta, odelta) > 1000*1000
		|| (cl.fixangle[0] && !cl.fixangle[1])
		|| (ent->state_previous.tagindex != ent->state_current.tagindex)
		|| (ent->state_previous.tagentity != ent->state_current.tagentity))
	{
		                             
		                                                                      
		                            
		ent->persistent.lerpdeltatime = 0;
		ent->persistent.lerpstarttime = cl.mtime[1];
		VectorCopy(ent->state_current.origin, ent->persistent.oldorigin);
		VectorCopy(ent->state_current.angles, ent->persistent.oldangles);
		VectorCopy(ent->state_current.origin, ent->persistent.neworigin);
		VectorCopy(ent->state_current.angles, ent->persistent.newangles);
		ent->persistent.trail_allowed = false;
	}
	else if (ent->state_current.flags & RENDER_STEP)
	{
		                        
		if (DotProduct(odelta, odelta) + DotProduct(adelta, adelta) > 0.01)
		{
			ent->persistent.lerpdeltatime = bound(0, cl.mtime[1] - ent->persistent.lerpstarttime, 0.1);
			ent->persistent.lerpstarttime = cl.mtime[1];
			VectorCopy(ent->persistent.neworigin, ent->persistent.oldorigin);
			VectorCopy(ent->persistent.newangles, ent->persistent.oldangles);
			VectorCopy(ent->state_current.origin, ent->persistent.neworigin);
			VectorCopy(ent->state_current.angles, ent->persistent.newangles);
		}
	}
	else
	{
		                
		ent->persistent.lerpstarttime = ent->state_previous.time;
		                               
		if (cl.islocalgame && !sv_fixedframeratesingleplayer.integer)
			ent->persistent.lerpdeltatime = 0;
		else
			ent->persistent.lerpdeltatime = bound(0, ent->state_current.time - ent->state_previous.time, 0.1);
		VectorCopy(ent->persistent.neworigin, ent->persistent.oldorigin);
		VectorCopy(ent->persistent.newangles, ent->persistent.oldangles);
		VectorCopy(ent->state_current.origin, ent->persistent.neworigin);
		VectorCopy(ent->state_current.angles, ent->persistent.newangles);
	}
	                                          
	if (ent->state_current.effects & EF_MUZZLEFLASH)
		ent->persistent.muzzleflash = 1;

	                        
	if ((ent->state_previous.effects & EF_RESTARTANIM_BIT) != (ent->state_current.effects & EF_RESTARTANIM_BIT))
	{
		ent->render.framegroupblend[1] = ent->render.framegroupblend[0];
		ent->render.framegroupblend[1].lerp = 1;
		ent->render.framegroupblend[0].frame = ent->state_current.frame;
		ent->render.framegroupblend[0].start = cl.time;
		ent->render.framegroupblend[0].lerp = 0;
	}
}

  
                  
                
                  
  
static void CL_ParseBaseline (entity_t *ent, int large)
{
	int i;

	ent->state_baseline = defaultstate;
	                                         
	ent->state_baseline.active = true;
	if (large)
	{
		ent->state_baseline.modelindex = (unsigned short) MSG_ReadShort(&cl_message);
		ent->state_baseline.frame = (unsigned short) MSG_ReadShort(&cl_message);
	}
	else if (cls.protocol == PROTOCOL_NEHAHRABJP || cls.protocol == PROTOCOL_NEHAHRABJP2 || cls.protocol == PROTOCOL_NEHAHRABJP3)
	{
		ent->state_baseline.modelindex = (unsigned short) MSG_ReadShort(&cl_message);
		ent->state_baseline.frame = MSG_ReadByte(&cl_message);
	}
	else
	{
		ent->state_baseline.modelindex = MSG_ReadByte(&cl_message);
		ent->state_baseline.frame = MSG_ReadByte(&cl_message);
	}
	ent->state_baseline.colormap = MSG_ReadByte(&cl_message);
	ent->state_baseline.skin = MSG_ReadByte(&cl_message);
	for (i = 0;i < 3;i++)
	{
		ent->state_baseline.origin[i] = MSG_ReadCoord(&cl_message, cls.protocol);
		ent->state_baseline.angles[i] = MSG_ReadAngle(&cl_message, cls.protocol);
	}
	ent->state_previous = ent->state_current = ent->state_baseline;
}


  
                  
                  

                                                 
                  
  
static void CL_ParseClientdata (void)
{
	int i, bits;

	VectorCopy (cl.mpunchangle[0], cl.mpunchangle[1]);
	VectorCopy (cl.mpunchvector[0], cl.mpunchvector[1]);
	VectorCopy (cl.mvelocity[0], cl.mvelocity[1]);
	cl.mviewzoom[1] = cl.mviewzoom[0];

	if (cls.protocol == PROTOCOL_QUAKE || cls.protocol == PROTOCOL_QUAKEDP || cls.protocol == PROTOCOL_NEHAHRAMOVIE || cls.protocol == PROTOCOL_NEHAHRABJP || cls.protocol == PROTOCOL_NEHAHRABJP2 || cls.protocol == PROTOCOL_NEHAHRABJP3 || cls.protocol == PROTOCOL_DARKPLACES1 || cls.protocol == PROTOCOL_DARKPLACES2 || cls.protocol == PROTOCOL_DARKPLACES3 || cls.protocol == PROTOCOL_DARKPLACES4 || cls.protocol == PROTOCOL_DARKPLACES5)
	{
		cl.stats[STAT_VIEWHEIGHT] = DEFAULT_VIEWHEIGHT;
		cl.stats[STAT_ITEMS] = 0;
		cl.stats[STAT_VIEWZOOM] = 255;
	}
	cl.idealpitch = 0;
	cl.mpunchangle[0][0] = 0;
	cl.mpunchangle[0][1] = 0;
	cl.mpunchangle[0][2] = 0;
	cl.mpunchvector[0][0] = 0;
	cl.mpunchvector[0][1] = 0;
	cl.mpunchvector[0][2] = 0;
	cl.mvelocity[0][0] = 0;
	cl.mvelocity[0][1] = 0;
	cl.mvelocity[0][2] = 0;
	cl.mviewzoom[0] = 1;

	bits = (unsigned short) MSG_ReadShort(&cl_message);
	if (bits & SU_EXTEND1)
		bits |= (MSG_ReadByte(&cl_message) << 16);
	if (bits & SU_EXTEND2)
		bits |= (MSG_ReadByte(&cl_message) << 24);

	if (bits & SU_VIEWHEIGHT)
		cl.stats[STAT_VIEWHEIGHT] = MSG_ReadChar(&cl_message);

	if (bits & SU_IDEALPITCH)
		cl.idealpitch = MSG_ReadChar(&cl_message);

	for (i = 0;i < 3;i++)
	{
		if (bits & (SU_PUNCH1<<i) )
		{
			if (cls.protocol == PROTOCOL_QUAKE || cls.protocol == PROTOCOL_QUAKEDP || cls.protocol == PROTOCOL_NEHAHRAMOVIE || cls.protocol == PROTOCOL_NEHAHRABJP || cls.protocol == PROTOCOL_NEHAHRABJP2 || cls.protocol == PROTOCOL_NEHAHRABJP3)
				cl.mpunchangle[0][i] = MSG_ReadChar(&cl_message);
			else
				cl.mpunchangle[0][i] = MSG_ReadAngle16i(&cl_message);
		}
		if (bits & (SU_PUNCHVEC1<<i))
		{
			if (cls.protocol == PROTOCOL_DARKPLACES1 || cls.protocol == PROTOCOL_DARKPLACES2 || cls.protocol == PROTOCOL_DARKPLACES3 || cls.protocol == PROTOCOL_DARKPLACES4)
				cl.mpunchvector[0][i] = MSG_ReadCoord16i(&cl_message);
			else
				cl.mpunchvector[0][i] = MSG_ReadCoord32f(&cl_message);
		}
		if (bits & (SU_VELOCITY1<<i) )
		{
			if (cls.protocol == PROTOCOL_QUAKE || cls.protocol == PROTOCOL_QUAKEDP || cls.protocol == PROTOCOL_NEHAHRAMOVIE || cls.protocol == PROTOCOL_NEHAHRABJP || cls.protocol == PROTOCOL_NEHAHRABJP2 || cls.protocol == PROTOCOL_NEHAHRABJP3 || cls.protocol == PROTOCOL_DARKPLACES1 || cls.protocol == PROTOCOL_DARKPLACES2 || cls.protocol == PROTOCOL_DARKPLACES3 || cls.protocol == PROTOCOL_DARKPLACES4)
				cl.mvelocity[0][i] = MSG_ReadChar(&cl_message)*16;
			else
				cl.mvelocity[0][i] = MSG_ReadCoord32f(&cl_message);
		}
	}

	                                                               
	if (bits & SU_ITEMS || cls.protocol == PROTOCOL_QUAKE || cls.protocol == PROTOCOL_QUAKEDP || cls.protocol == PROTOCOL_NEHAHRAMOVIE || cls.protocol == PROTOCOL_NEHAHRABJP || cls.protocol == PROTOCOL_NEHAHRABJP2 || cls.protocol == PROTOCOL_NEHAHRABJP3 || cls.protocol == PROTOCOL_DARKPLACES1 || cls.protocol == PROTOCOL_DARKPLACES2 || cls.protocol == PROTOCOL_DARKPLACES3 || cls.protocol == PROTOCOL_DARKPLACES4 || cls.protocol == PROTOCOL_DARKPLACES5)
		cl.stats[STAT_ITEMS] = MSG_ReadLong(&cl_message);

	cl.onground = (bits & SU_ONGROUND) != 0;
	cl.inwater = (bits & SU_INWATER) != 0;

	if (cls.protocol == PROTOCOL_DARKPLACES5)
	{
		cl.stats[STAT_WEAPONFRAME] = (bits & SU_WEAPONFRAME) ? MSG_ReadShort(&cl_message) : 0;
		cl.stats[STAT_ARMOR] = (bits & SU_ARMOR) ? MSG_ReadShort(&cl_message) : 0;
		cl.stats[STAT_WEAPON] = (bits & SU_WEAPON) ? MSG_ReadShort(&cl_message) : 0;
		cl.stats[STAT_HEALTH] = MSG_ReadShort(&cl_message);
		cl.stats[STAT_AMMO] = MSG_ReadShort(&cl_message);
		cl.stats[STAT_SHELLS] = MSG_ReadShort(&cl_message);
		cl.stats[STAT_NAILS] = MSG_ReadShort(&cl_message);
		cl.stats[STAT_ROCKETS] = MSG_ReadShort(&cl_message);
		cl.stats[STAT_CELLS] = MSG_ReadShort(&cl_message);
		cl.stats[STAT_ACTIVEWEAPON] = (unsigned short) MSG_ReadShort(&cl_message);
	}
	else if (cls.protocol == PROTOCOL_QUAKE || cls.protocol == PROTOCOL_QUAKEDP || cls.protocol == PROTOCOL_NEHAHRAMOVIE || cls.protocol == PROTOCOL_NEHAHRABJP || cls.protocol == PROTOCOL_NEHAHRABJP2 || cls.protocol == PROTOCOL_NEHAHRABJP3 || cls.protocol == PROTOCOL_DARKPLACES1 || cls.protocol == PROTOCOL_DARKPLACES2 || cls.protocol == PROTOCOL_DARKPLACES3 || cls.protocol == PROTOCOL_DARKPLACES4)
	{
		cl.stats[STAT_WEAPONFRAME] = (bits & SU_WEAPONFRAME) ? MSG_ReadByte(&cl_message) : 0;
		cl.stats[STAT_ARMOR] = (bits & SU_ARMOR) ? MSG_ReadByte(&cl_message) : 0;
		if (cls.protocol == PROTOCOL_NEHAHRABJP || cls.protocol == PROTOCOL_NEHAHRABJP2 || cls.protocol == PROTOCOL_NEHAHRABJP3)
			cl.stats[STAT_WEAPON] = (bits & SU_WEAPON) ? (unsigned short)MSG_ReadShort(&cl_message) : 0;
		else
			cl.stats[STAT_WEAPON] = (bits & SU_WEAPON) ? MSG_ReadByte(&cl_message) : 0;
		cl.stats[STAT_HEALTH] = MSG_ReadShort(&cl_message);
		cl.stats[STAT_AMMO] = MSG_ReadByte(&cl_message);
		cl.stats[STAT_SHELLS] = MSG_ReadByte(&cl_message);
		cl.stats[STAT_NAILS] = MSG_ReadByte(&cl_message);
		cl.stats[STAT_ROCKETS] = MSG_ReadByte(&cl_message);
		cl.stats[STAT_CELLS] = MSG_ReadByte(&cl_message);
		if (gamemode == GAME_HIPNOTIC || gamemode == GAME_ROGUE || gamemode == GAME_QUOTH || IS_OLDNEXUIZ_DERIVED(gamemode))
			cl.stats[STAT_ACTIVEWEAPON] = (1<<MSG_ReadByte(&cl_message));
		else
			cl.stats[STAT_ACTIVEWEAPON] = MSG_ReadByte(&cl_message);
	}

	if (bits & SU_VIEWZOOM)
	{
		if (cls.protocol == PROTOCOL_DARKPLACES2 || cls.protocol == PROTOCOL_DARKPLACES3 || cls.protocol == PROTOCOL_DARKPLACES4)
			cl.stats[STAT_VIEWZOOM] = MSG_ReadByte(&cl_message);
		else
			cl.stats[STAT_VIEWZOOM] = (unsigned short) MSG_ReadShort(&cl_message);
	}

	                         
	cl.mviewzoom[0] = (float) max(cl.stats[STAT_VIEWZOOM], 2) * (1.0f / 255.0f);
}

  
                     
              
                     
  
static void CL_ParseStatic (int large)
{
	entity_t *ent;

	if (cl.num_static_entities >= cl.max_static_entities)
		Host_Error ("Too many static entities");
	ent = &cl.static_entities[cl.num_static_entities++];
	CL_ParseBaseline (ent, large);

	if (ent->state_baseline.modelindex == 0)
	{
		Con_DPrintf("svc_parsestatic: static entity without model at %f %f %f\n", ent->state_baseline.origin[0], ent->state_baseline.origin[1], ent->state_baseline.origin[2]);
		cl.num_static_entities--;
		                                                           
		return;
	}

                               
	ent->render.model = CL_GetModelByIndex(ent->state_baseline.modelindex);
	ent->render.framegroupblend[0].frame = ent->state_baseline.frame;
	ent->render.framegroupblend[0].lerp = 1;
	                               
	ent->render.framegroupblend[0].start = lhrandom(-10, -1);
	ent->render.skinnum = ent->state_baseline.skin;
	ent->render.effects = ent->state_baseline.effects;
	ent->render.alpha = 1;

	                                                              
	                                                              

	Matrix4x4_CreateFromQuakeEntity(&ent->render.matrix, ent->state_baseline.origin[0], ent->state_baseline.origin[1], ent->state_baseline.origin[2], ent->state_baseline.angles[0], ent->state_baseline.angles[1], ent->state_baseline.angles[2], 1);
	ent->render.allowdecals = true;
	CL_UpdateRenderEntity(&ent->render);
}

  
                   
                   
                   
  
static void CL_ParseStaticSound (int large)
{
	vec3_t		org;
	int			sound_num, vol, atten;

	MSG_ReadVector(&cl_message, org, cls.protocol);
	if (large || cls.protocol == PROTOCOL_NEHAHRABJP2)
		sound_num = (unsigned short) MSG_ReadShort(&cl_message);
	else
		sound_num = MSG_ReadByte(&cl_message);

	if (sound_num < 0 || sound_num >= MAX_SOUNDS)
	{
		Con_Printf("CL_ParseStaticSound: sound_num(%i) >= MAX_SOUNDS (%i)\n", sound_num, MAX_SOUNDS);
		return;
	}

	vol = MSG_ReadByte(&cl_message);
	atten = MSG_ReadByte(&cl_message);

	S_StaticSound (cl.sound_precache[sound_num], org, vol/255.0f, atten);
}

static void CL_ParseEffect (void)
{
	vec3_t		org;
	int			modelindex, startframe, framecount, framerate;

	MSG_ReadVector(&cl_message, org, cls.protocol);
	modelindex = MSG_ReadByte(&cl_message);
	startframe = MSG_ReadByte(&cl_message);
	framecount = MSG_ReadByte(&cl_message);
	framerate = MSG_ReadByte(&cl_message);

	CL_Effect(org, modelindex, startframe, framecount, framerate);
}

static void CL_ParseEffect2 (void)
{
	vec3_t		org;
	int			modelindex, startframe, framecount, framerate;

	MSG_ReadVector(&cl_message, org, cls.protocol);
	modelindex = (unsigned short) MSG_ReadShort(&cl_message);
	startframe = (unsigned short) MSG_ReadShort(&cl_message);
	framecount = MSG_ReadByte(&cl_message);
	framerate = MSG_ReadByte(&cl_message);

	CL_Effect(org, modelindex, startframe, framecount, framerate);
}

void CL_NewBeam (int ent, vec3_t start, vec3_t end, dp_model_t *m, int lightning)
{
	int i;
	beam_t *b = NULL;

	if (ent >= MAX_EDICTS)
	{
		Con_Printf("CL_NewBeam: invalid entity number %i\n", ent);
		ent = 0;
	}

	if (ent >= cl.max_entities)
		CL_ExpandEntities(ent);

	                                         
	i = cl.max_beams;
	if (ent)
		for (i = 0, b = cl.beams;i < cl.max_beams;i++, b++)
			if (b->entity == ent)
				break;
	                                                               
	if (i == cl.max_beams)
		for (i = 0, b = cl.beams;i < cl.max_beams;i++, b++)
			if (!b->model)
				break;
	if (i < cl.max_beams)
	{
		cl.num_beams = max(cl.num_beams, i + 1);
		b->entity = ent;
		b->lightning = lightning;
		b->model = m;
		b->endtime = cl.mtime[0] + 0.2;
		VectorCopy (start, b->start);
		VectorCopy (end, b->end);
	}
	else
		Con_Print("beam list overflow!\n");
}

static void CL_ParseBeam (dp_model_t *m, int lightning)
{
	int ent;
	vec3_t start, end;

	ent = (unsigned short) MSG_ReadShort(&cl_message);
	MSG_ReadVector(&cl_message, start, cls.protocol);
	MSG_ReadVector(&cl_message, end, cls.protocol);

	if (ent >= MAX_EDICTS)
	{
		Con_Printf("CL_ParseBeam: invalid entity number %i\n", ent);
		ent = 0;
	}

	CL_NewBeam(ent, start, end, m, lightning);
}

static void CL_ParseTempEntity(void)
{
	int type;
	vec3_t pos, pos2;
	vec3_t vel1, vel2;
	vec3_t dir;
	vec3_t color;
	int rnd;
	int colorStart, colorLength, count;
	float velspeed, radius;
	unsigned char *tempcolor;
	matrix4x4_t tempmatrix;

	if (cls.protocol == PROTOCOL_QUAKEWORLD)
	{
		type = MSG_ReadByte(&cl_message);
		switch (type)
		{
		case QW_TE_WIZSPIKE:
			                     
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			CL_ParticleEffect(EFFECT_TE_WIZSPIKE, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			S_StartSound(-1, 0, cl.sfx_wizhit, pos, 1, 1);
			break;

		case QW_TE_KNIGHTSPIKE:
			                     
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			CL_ParticleEffect(EFFECT_TE_KNIGHTSPIKE, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			S_StartSound(-1, 0, cl.sfx_knighthit, pos, 1, 1);
			break;

		case QW_TE_SPIKE:
			                     
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			CL_ParticleEffect(EFFECT_TE_SPIKE, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			if (rand() % 5)
				S_StartSound(-1, 0, cl.sfx_tink1, pos, 1, 1);
			else
			{
				rnd = rand() & 3;
				if (rnd == 1)
					S_StartSound(-1, 0, cl.sfx_ric1, pos, 1, 1);
				else if (rnd == 2)
					S_StartSound(-1, 0, cl.sfx_ric2, pos, 1, 1);
				else
					S_StartSound(-1, 0, cl.sfx_ric3, pos, 1, 1);
			}
			break;
		case QW_TE_SUPERSPIKE:
			                           
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			CL_ParticleEffect(EFFECT_TE_SUPERSPIKE, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			if (rand() % 5)
				S_StartSound(-1, 0, cl.sfx_tink1, pos, 1, 1);
			else
			{
				rnd = rand() & 3;
				if (rnd == 1)
					S_StartSound(-1, 0, cl.sfx_ric1, pos, 1, 1);
				else if (rnd == 2)
					S_StartSound(-1, 0, cl.sfx_ric2, pos, 1, 1);
				else
					S_StartSound(-1, 0, cl.sfx_ric3, pos, 1, 1);
			}
			break;

		case QW_TE_EXPLOSION:
			                   
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 10);
			CL_ParticleEffect(EFFECT_TE_EXPLOSION, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			S_StartSound(-1, 0, cl.sfx_r_exp3, pos, 1, 1);
			CL_Effect(pos, cl.qw_modelindex_s_explod, 0, 6, 10);
			break;

		case QW_TE_TAREXPLOSION:
			                    
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 10);
			CL_ParticleEffect(EFFECT_TE_TAREXPLOSION, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			S_StartSound(-1, 0, cl.sfx_r_exp3, pos, 1, 1);
			break;

		case QW_TE_LIGHTNING1:
			                  
			CL_ParseBeam(cl.model_bolt, true);
			break;

		case QW_TE_LIGHTNING2:
			                  
			CL_ParseBeam(cl.model_bolt2, true);
			break;

		case QW_TE_LIGHTNING3:
			                  
			CL_ParseBeam(cl.model_bolt3, false);
			break;

		case QW_TE_LAVASPLASH:
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_ParticleEffect(EFFECT_TE_LAVASPLASH, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			break;

		case QW_TE_TELEPORT:
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_ParticleEffect(EFFECT_TE_TELEPORT, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			break;

		case QW_TE_GUNSHOT:
			                      
			radius = MSG_ReadByte(&cl_message);
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			VectorSet(pos2, pos[0] + radius, pos[1] + radius, pos[2] + radius);
			VectorSet(pos, pos[0] - radius, pos[1] - radius, pos[2] - radius);
			CL_ParticleEffect(EFFECT_TE_GUNSHOT, radius, pos, pos2, vec3_origin, vec3_origin, NULL, 0);
			if(cl_sound_ric_gunshot.integer & RIC_GUNSHOT)
			{
				if (rand() % 5)
					S_StartSound(-1, 0, cl.sfx_tink1, pos, 1, 1);
				else
				{
					rnd = rand() & 3;
					if (rnd == 1)
						S_StartSound(-1, 0, cl.sfx_ric1, pos, 1, 1);
					else if (rnd == 2)
						S_StartSound(-1, 0, cl.sfx_ric2, pos, 1, 1);
					else
						S_StartSound(-1, 0, cl.sfx_ric3, pos, 1, 1);
				}
			}
			break;

		case QW_TE_BLOOD:
			count = MSG_ReadByte(&cl_message);
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			CL_ParticleEffect(EFFECT_TE_BLOOD, count, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			break;

		case QW_TE_LIGHTNINGBLOOD:
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			CL_ParticleEffect(EFFECT_TE_BLOOD, 2.5, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			break;

		default:
			Host_Error("CL_ParseTempEntity: bad type %d (hex %02X)", type, type);
		}
	}
	else
	{
		type = MSG_ReadByte(&cl_message);
		switch (type)
		{
		case TE_WIZSPIKE:
			                     
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			CL_ParticleEffect(EFFECT_TE_WIZSPIKE, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			S_StartSound(-1, 0, cl.sfx_wizhit, pos, 1, 1);
			break;

		case TE_KNIGHTSPIKE:
			                     
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			CL_ParticleEffect(EFFECT_TE_KNIGHTSPIKE, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			S_StartSound(-1, 0, cl.sfx_knighthit, pos, 1, 1);
			break;

		case TE_SPIKE:
			                     
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			CL_ParticleEffect(EFFECT_TE_SPIKE, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			if (rand() % 5)
				S_StartSound(-1, 0, cl.sfx_tink1, pos, 1, 1);
			else
			{
				rnd = rand() & 3;
				if (rnd == 1)
					S_StartSound(-1, 0, cl.sfx_ric1, pos, 1, 1);
				else if (rnd == 2)
					S_StartSound(-1, 0, cl.sfx_ric2, pos, 1, 1);
				else
					S_StartSound(-1, 0, cl.sfx_ric3, pos, 1, 1);
			}
			break;
		case TE_SPIKEQUAD:
			                          
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			CL_ParticleEffect(EFFECT_TE_SPIKEQUAD, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			if (rand() % 5)
				S_StartSound(-1, 0, cl.sfx_tink1, pos, 1, 1);
			else
			{
				rnd = rand() & 3;
				if (rnd == 1)
					S_StartSound(-1, 0, cl.sfx_ric1, pos, 1, 1);
				else if (rnd == 2)
					S_StartSound(-1, 0, cl.sfx_ric2, pos, 1, 1);
				else
					S_StartSound(-1, 0, cl.sfx_ric3, pos, 1, 1);
			}
			break;
		case TE_SUPERSPIKE:
			                           
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			CL_ParticleEffect(EFFECT_TE_SUPERSPIKE, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			if (rand() % 5)
				S_StartSound(-1, 0, cl.sfx_tink1, pos, 1, 1);
			else
			{
				rnd = rand() & 3;
				if (rnd == 1)
					S_StartSound(-1, 0, cl.sfx_ric1, pos, 1, 1);
				else if (rnd == 2)
					S_StartSound(-1, 0, cl.sfx_ric2, pos, 1, 1);
				else
					S_StartSound(-1, 0, cl.sfx_ric3, pos, 1, 1);
			}
			break;
		case TE_SUPERSPIKEQUAD:
			                                
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			CL_ParticleEffect(EFFECT_TE_SUPERSPIKEQUAD, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			if (rand() % 5)
				S_StartSound(-1, 0, cl.sfx_tink1, pos, 1, 1);
			else
			{
				rnd = rand() & 3;
				if (rnd == 1)
					S_StartSound(-1, 0, cl.sfx_ric1, pos, 1, 1);
				else if (rnd == 2)
					S_StartSound(-1, 0, cl.sfx_ric2, pos, 1, 1);
				else
					S_StartSound(-1, 0, cl.sfx_ric3, pos, 1, 1);
			}
			break;
			                                                
		case TE_BLOOD:
			             
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			dir[0] = MSG_ReadChar(&cl_message);
			dir[1] = MSG_ReadChar(&cl_message);
			dir[2] = MSG_ReadChar(&cl_message);
			count = MSG_ReadByte(&cl_message);
			CL_ParticleEffect(EFFECT_TE_BLOOD, count, pos, pos, dir, dir, NULL, 0);
			break;
		case TE_SPARK:
			               
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			dir[0] = MSG_ReadChar(&cl_message);
			dir[1] = MSG_ReadChar(&cl_message);
			dir[2] = MSG_ReadChar(&cl_message);
			count = MSG_ReadByte(&cl_message);
			CL_ParticleEffect(EFFECT_TE_SPARK, count, pos, pos, dir, dir, NULL, 0);
			break;
		case TE_PLASMABURN:
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			CL_ParticleEffect(EFFECT_TE_PLASMABURN, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			break;
			                                     
		case TE_BLOODSHOWER:
			                 
			MSG_ReadVector(&cl_message, pos, cls.protocol);        
			MSG_ReadVector(&cl_message, pos2, cls.protocol);        
			velspeed = MSG_ReadCoord(&cl_message, cls.protocol);         
			count = (unsigned short) MSG_ReadShort(&cl_message);                       
			vel1[0] = -velspeed;
			vel1[1] = -velspeed;
			vel1[2] = -velspeed;
			vel2[0] = velspeed;
			vel2[1] = velspeed;
			vel2[2] = velspeed;
			CL_ParticleEffect(EFFECT_TE_BLOOD, count, pos, pos2, vel1, vel2, NULL, 0);
			break;

		case TE_PARTICLECUBE:
			                                  
			MSG_ReadVector(&cl_message, pos, cls.protocol);        
			MSG_ReadVector(&cl_message, pos2, cls.protocol);        
			MSG_ReadVector(&cl_message, dir, cls.protocol);       
			count = (unsigned short) MSG_ReadShort(&cl_message);                       
			colorStart = MSG_ReadByte(&cl_message);         
			colorLength = MSG_ReadByte(&cl_message);                    
			velspeed = MSG_ReadCoord(&cl_message, cls.protocol);             
			CL_ParticleCube(pos, pos2, dir, count, colorStart, colorLength != 0, velspeed);
			break;

		case TE_PARTICLERAIN:
			                                  
			MSG_ReadVector(&cl_message, pos, cls.protocol);        
			MSG_ReadVector(&cl_message, pos2, cls.protocol);        
			MSG_ReadVector(&cl_message, dir, cls.protocol);       
			count = (unsigned short) MSG_ReadShort(&cl_message);                       
			colorStart = MSG_ReadByte(&cl_message);         
			CL_ParticleRain(pos, pos2, dir, count, colorStart, 0);
			break;

		case TE_PARTICLESNOW:
			                                  
			MSG_ReadVector(&cl_message, pos, cls.protocol);        
			MSG_ReadVector(&cl_message, pos2, cls.protocol);        
			MSG_ReadVector(&cl_message, dir, cls.protocol);       
			count = (unsigned short) MSG_ReadShort(&cl_message);                       
			colorStart = MSG_ReadByte(&cl_message);         
			CL_ParticleRain(pos, pos2, dir, count, colorStart, 1);
			break;

		case TE_GUNSHOT:
			                      
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			CL_ParticleEffect(EFFECT_TE_GUNSHOT, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			if(cl_sound_ric_gunshot.integer & RIC_GUNSHOT)
			{
				if (rand() % 5)
					S_StartSound(-1, 0, cl.sfx_tink1, pos, 1, 1);
				else
				{
					rnd = rand() & 3;
					if (rnd == 1)
						S_StartSound(-1, 0, cl.sfx_ric1, pos, 1, 1);
					else if (rnd == 2)
						S_StartSound(-1, 0, cl.sfx_ric2, pos, 1, 1);
					else
						S_StartSound(-1, 0, cl.sfx_ric3, pos, 1, 1);
				}
			}
			break;

		case TE_GUNSHOTQUAD:
			                           
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			CL_ParticleEffect(EFFECT_TE_GUNSHOTQUAD, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			if(cl_sound_ric_gunshot.integer & RIC_GUNSHOTQUAD)
			{
				if (rand() % 5)
					S_StartSound(-1, 0, cl.sfx_tink1, pos, 1, 1);
				else
				{
					rnd = rand() & 3;
					if (rnd == 1)
						S_StartSound(-1, 0, cl.sfx_ric1, pos, 1, 1);
					else if (rnd == 2)
						S_StartSound(-1, 0, cl.sfx_ric2, pos, 1, 1);
					else
						S_StartSound(-1, 0, cl.sfx_ric3, pos, 1, 1);
				}
			}
			break;

		case TE_EXPLOSION:
			                   
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 10);
			CL_ParticleEffect(EFFECT_TE_EXPLOSION, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			S_StartSound(-1, 0, cl.sfx_r_exp3, pos, 1, 1);
			break;

		case TE_EXPLOSIONQUAD:
			                        
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 10);
			CL_ParticleEffect(EFFECT_TE_EXPLOSIONQUAD, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			S_StartSound(-1, 0, cl.sfx_r_exp3, pos, 1, 1);
			break;

		case TE_EXPLOSION3:
			                                           
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 10);
			color[0] = MSG_ReadCoord(&cl_message, cls.protocol) * (2.0f / 1.0f);
			color[1] = MSG_ReadCoord(&cl_message, cls.protocol) * (2.0f / 1.0f);
			color[2] = MSG_ReadCoord(&cl_message, cls.protocol) * (2.0f / 1.0f);
			CL_ParticleExplosion(pos);
			Matrix4x4_CreateTranslate(&tempmatrix, pos[0], pos[1], pos[2]);
			CL_AllocLightFlash(NULL, &tempmatrix, 350, color[0], color[1], color[2], 700, 0.5, 0, -1, true, 1, 0.25, 0.25, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
			S_StartSound(-1, 0, cl.sfx_r_exp3, pos, 1, 1);
			break;

		case TE_EXPLOSIONRGB:
			                             
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 10);
			CL_ParticleExplosion(pos);
			color[0] = MSG_ReadByte(&cl_message) * (2.0f / 255.0f);
			color[1] = MSG_ReadByte(&cl_message) * (2.0f / 255.0f);
			color[2] = MSG_ReadByte(&cl_message) * (2.0f / 255.0f);
			Matrix4x4_CreateTranslate(&tempmatrix, pos[0], pos[1], pos[2]);
			CL_AllocLightFlash(NULL, &tempmatrix, 350, color[0], color[1], color[2], 700, 0.5, 0, -1, true, 1, 0.25, 0.25, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
			S_StartSound(-1, 0, cl.sfx_r_exp3, pos, 1, 1);
			break;

		case TE_TAREXPLOSION:
			                    
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 10);
			CL_ParticleEffect(EFFECT_TE_TAREXPLOSION, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			S_StartSound(-1, 0, cl.sfx_r_exp3, pos, 1, 1);
			break;

		case TE_SMALLFLASH:
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 10);
			CL_ParticleEffect(EFFECT_TE_SMALLFLASH, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			break;

		case TE_CUSTOMFLASH:
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 4);
			radius = (MSG_ReadByte(&cl_message) + 1) * 8;
			velspeed = (MSG_ReadByte(&cl_message) + 1) * (1.0 / 256.0);
			color[0] = MSG_ReadByte(&cl_message) * (2.0f / 255.0f);
			color[1] = MSG_ReadByte(&cl_message) * (2.0f / 255.0f);
			color[2] = MSG_ReadByte(&cl_message) * (2.0f / 255.0f);
			Matrix4x4_CreateTranslate(&tempmatrix, pos[0], pos[1], pos[2]);
			CL_AllocLightFlash(NULL, &tempmatrix, radius, color[0], color[1], color[2], radius / velspeed, velspeed, 0, -1, true, 1, 0.25, 1, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
			break;

		case TE_FLAMEJET:
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			MSG_ReadVector(&cl_message, dir, cls.protocol);
			count = MSG_ReadByte(&cl_message);
			CL_ParticleEffect(EFFECT_TE_FLAMEJET, count, pos, pos, dir, dir, NULL, 0);
			break;

		case TE_LIGHTNING1:
			                  
			CL_ParseBeam(cl.model_bolt, true);
			break;

		case TE_LIGHTNING2:
			                  
			CL_ParseBeam(cl.model_bolt2, true);
			break;

		case TE_LIGHTNING3:
			                  
			CL_ParseBeam(cl.model_bolt3, false);
			break;

	               
		case TE_BEAM:
			                      
			CL_ParseBeam(cl.model_beam, false);
			break;
	               

	                                                         
		case TE_LIGHTNING4NEH:
			CL_ParseBeam(Mod_ForName(MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)), true, false, NULL), false);
			break;

		case TE_LAVASPLASH:
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_ParticleEffect(EFFECT_TE_LAVASPLASH, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			break;

		case TE_TELEPORT:
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_ParticleEffect(EFFECT_TE_TELEPORT, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			break;

		case TE_EXPLOSION2:
			                         
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 10);
			colorStart = MSG_ReadByte(&cl_message);
			colorLength = MSG_ReadByte(&cl_message);
			if (colorLength == 0)
				colorLength = 1;
			CL_ParticleExplosion2(pos, colorStart, colorLength);
			tempcolor = palette_rgb[(rand()%colorLength) + colorStart];
			color[0] = tempcolor[0] * (2.0f / 255.0f);
			color[1] = tempcolor[1] * (2.0f / 255.0f);
			color[2] = tempcolor[2] * (2.0f / 255.0f);
			Matrix4x4_CreateTranslate(&tempmatrix, pos[0], pos[1], pos[2]);
			CL_AllocLightFlash(NULL, &tempmatrix, 350, color[0], color[1], color[2], 700, 0.5, 0, -1, true, 1, 0.25, 0.25, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
			S_StartSound(-1, 0, cl.sfx_r_exp3, pos, 1, 1);
			break;

		case TE_TEI_G3:
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			MSG_ReadVector(&cl_message, pos2, cls.protocol);
			MSG_ReadVector(&cl_message, dir, cls.protocol);
			CL_ParticleTrail(EFFECT_TE_TEI_G3, 1, pos, pos2, dir, dir, NULL, 0, true, true, NULL, NULL, 1);
			break;

		case TE_TEI_SMOKE:
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			MSG_ReadVector(&cl_message, dir, cls.protocol);
			count = MSG_ReadByte(&cl_message);
			CL_FindNonSolidLocation(pos, pos, 4);
			CL_ParticleEffect(EFFECT_TE_TEI_SMOKE, count, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			break;

		case TE_TEI_BIGEXPLOSION:
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			CL_FindNonSolidLocation(pos, pos, 10);
			CL_ParticleEffect(EFFECT_TE_TEI_BIGEXPLOSION, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			S_StartSound(-1, 0, cl.sfx_r_exp3, pos, 1, 1);
			break;

		case TE_TEI_PLASMAHIT:
			MSG_ReadVector(&cl_message, pos, cls.protocol);
			MSG_ReadVector(&cl_message, dir, cls.protocol);
			count = MSG_ReadByte(&cl_message);
			CL_FindNonSolidLocation(pos, pos, 5);
			CL_ParticleEffect(EFFECT_TE_TEI_PLASMAHIT, count, pos, pos, vec3_origin, vec3_origin, NULL, 0);
			break;

		default:
			Host_Error("CL_ParseTempEntity: bad type %d (hex %02X)", type, type);
		}
	}
}

static void CL_ParseTrailParticles(void)
{
	int entityindex;
	int effectindex;
	vec3_t start, end;
	entityindex = (unsigned short)MSG_ReadShort(&cl_message);
	if (entityindex >= MAX_EDICTS)
		entityindex = 0;
	if (entityindex >= cl.max_entities)
		CL_ExpandEntities(entityindex);
	effectindex = (unsigned short)MSG_ReadShort(&cl_message);
	MSG_ReadVector(&cl_message, start, cls.protocol);
	MSG_ReadVector(&cl_message, end, cls.protocol);
	CL_ParticleTrail(effectindex, 1, start, end, vec3_origin, vec3_origin, entityindex > 0 ? cl.entities + entityindex : NULL, 0, true, true, NULL, NULL, 1);
}

static void CL_ParsePointParticles(void)
{
	int effectindex, count;
	vec3_t origin, velocity;
	effectindex = (unsigned short)MSG_ReadShort(&cl_message);
	MSG_ReadVector(&cl_message, origin, cls.protocol);
	MSG_ReadVector(&cl_message, velocity, cls.protocol);
	count = (unsigned short)MSG_ReadShort(&cl_message);
	CL_ParticleEffect(effectindex, count, origin, origin, velocity, velocity, NULL, 0);
}

static void CL_ParsePointParticles1(void)
{
	int effectindex;
	vec3_t origin;
	effectindex = (unsigned short)MSG_ReadShort(&cl_message);
	MSG_ReadVector(&cl_message, origin, cls.protocol);
	CL_ParticleEffect(effectindex, 1, origin, origin, vec3_origin, vec3_origin, NULL, 0);
}

typedef struct cl_iplog_item_s
{
	char *address;
	char *name;
}
cl_iplog_item_t;

static qboolean cl_iplog_loaded = false;
static int cl_iplog_numitems = 0;
static int cl_iplog_maxitems = 0;
static cl_iplog_item_t *cl_iplog_items;

static void CL_IPLog_Load(void);
static void CL_IPLog_Add(const char *address, const char *name, qboolean checkexisting, qboolean addtofile)
{
	int i;
	size_t sz_name, sz_address;
	if (!address || !address[0] || !name || !name[0])
		return;
	if (!cl_iplog_loaded)
		CL_IPLog_Load();
	if (developer_extra.integer)
		Con_DPrintf("CL_IPLog_Add(\"%s\", \"%s\", %i, %i);\n", address, name, checkexisting, addtofile);
	                           
	if (checkexisting)
	{
		for (i = 0;i < cl_iplog_numitems;i++)
		{
			if (!strcmp(cl_iplog_items[i].address, address) && !strcmp(cl_iplog_items[i].name, name))
			{
				if (developer_extra.integer)
					Con_DPrintf("... found existing \"%s\" \"%s\"\n", cl_iplog_items[i].address, cl_iplog_items[i].name);
				return;
			}
		}
	}
	                                                    
	if (cl_iplog_maxitems <= cl_iplog_numitems || !cl_iplog_items)
	{
		cl_iplog_item_t *olditems = cl_iplog_items;
		cl_iplog_maxitems = max(1024, cl_iplog_maxitems + 256);
		cl_iplog_items = (cl_iplog_item_t *) Mem_Alloc(cls.permanentmempool, cl_iplog_maxitems * sizeof(cl_iplog_item_t));
		if (olditems)
		{
			if (cl_iplog_numitems)
				memcpy(cl_iplog_items, olditems, cl_iplog_numitems * sizeof(cl_iplog_item_t));
			Mem_Free(olditems);
		}
	}
	sz_address = strlen(address) + 1;
	sz_name = strlen(name) + 1;
	cl_iplog_items[cl_iplog_numitems].address = (char *) Mem_Alloc(cls.permanentmempool, sz_address);
	cl_iplog_items[cl_iplog_numitems].name = (char *) Mem_Alloc(cls.permanentmempool, sz_name);
	strlcpy(cl_iplog_items[cl_iplog_numitems].address, address, sz_address);
	                                                                          
	                                                       
	strlcpy(cl_iplog_items[cl_iplog_numitems].name, name, sz_name);
	cl_iplog_numitems++;
	if (addtofile)
	{
		                               
		                                                                       
		                                   
                           
#ifndef DP_MOBILETOUCH
		Log_Printf(cl_iplog_name.string, "%s %s\n", address, name);
		if (developer_extra.integer)
			Con_DPrintf("CL_IPLog_Add: appending this line to %s: %s %s\n", cl_iplog_name.string, address, name);
#endif
	}
}

static void CL_IPLog_Load(void)
{
	int i, len, linenumber;
	char *text, *textend;
	unsigned char *filedata;
	fs_offset_t filesize;
	char line[MAX_INPUTLINE];
	char address[MAX_INPUTLINE];
	cl_iplog_loaded = true;
	                                                                       
	                                   
                           
#ifndef DP_MOBILETOUCH
	filedata = FS_LoadFile(cl_iplog_name.string, tempmempool, true, &filesize);
#else
	filedata = NULL;
#endif
	if (!filedata)
		return;
	text = (char *)filedata;
	textend = text + filesize;
	for (linenumber = 1;text < textend;linenumber++)
	{
		for (len = 0;text < textend && *text != '\r' && *text != '\n';text++)
			if (len < (int)sizeof(line) - 1)
				line[len++] = *text;
		line[len] = 0;
		if (text < textend && *text == '\r' && text[1] == '\n')
			text++;
		if (text < textend && *text == '\n')
			text++;
		if (line[0] == '/' && line[1] == '/')
			continue;                                               
		for (i = 0;i < len && !ISWHITESPACE(line[i]);i++)
			address[i] = line[i];
		address[i] = 0;
		                                   
		i++;
		                                                 
		                                              
		if (address[0] && line[i])
			CL_IPLog_Add(address, line + i, false, false);
		else
			Con_Printf("%s:%i: could not parse address and name:\n%s\n", cl_iplog_name.string, linenumber, line);
	}
}

static void CL_IPLog_List_f(void)
{
	int i, j;
	const char *addressprefix;
	if (Cmd_Argc() > 2)
	{
		Con_Printf("usage: %s 123.456.789.\n", Cmd_Argv(0));
		return;
	}
	addressprefix = "";
	if (Cmd_Argc() >= 2)
		addressprefix = Cmd_Argv(1);
	if (!cl_iplog_loaded)
		CL_IPLog_Load();
	if (addressprefix && addressprefix[0])
		Con_Printf("Listing iplog addresses beginning with %s\n", addressprefix);
	else
		Con_Printf("Listing all iplog entries\n");
	Con_Printf("address         name\n");
	for (i = 0;i < cl_iplog_numitems;i++)
	{
		if (addressprefix && addressprefix[0])
		{
			for (j = 0;addressprefix[j];j++)
				if (addressprefix[j] != cl_iplog_items[i].address[j])
					break;
			                                                               
			                                 
			if (addressprefix[j])
				continue;
		}
		                                                              
		                                                                    
		                                              
		if (strlen(cl_iplog_items[i].address) < 15)
			Con_Printf("%-15s %s\n", cl_iplog_items[i].address, cl_iplog_items[i].name);
		else
			Con_Printf("%5s %s\n", cl_iplog_items[i].address, cl_iplog_items[i].name);
	}
}

                                                                         
static qboolean CL_ExaminePrintString(const char *text)
{
	int len;
	const char *t;
	char temp[MAX_INPUTLINE];
	if (!strcmp(text, "Client ping times:\n"))
	{
		cl.parsingtextmode = CL_PARSETEXTMODE_PING;
		                             
		if (cls.demoplayback)
			cl.parsingtextexpectingpingforscores = 1;
		for(cl.parsingtextplayerindex = 0; cl.parsingtextplayerindex < cl.maxclients && !cl.scores[cl.parsingtextplayerindex].name[0]; cl.parsingtextplayerindex++)
			;
		if (cl.parsingtextplayerindex >= cl.maxclients)                                                                       
		{
			Con_Printf("ping reply but empty scoreboard?!?\n");
			cl.parsingtextmode = CL_PARSETEXTMODE_NONE;
			cl.parsingtextexpectingpingforscores = 0;
		}
		cl.parsingtextexpectingpingforscores = cl.parsingtextexpectingpingforscores ? 2 : 0;
		return !cl.parsingtextexpectingpingforscores;
	}
	if (!strncmp(text, "host:    ", 9))
	{
		                                                           
		cl.parsingtextmode = CL_PARSETEXTMODE_STATUS;
		cl.parsingtextplayerindex = 0;
		return true;
	}
	if (cl.parsingtextmode == CL_PARSETEXTMODE_PING)
	{
		                                                                 
		qboolean expected = cl.parsingtextexpectingpingforscores != 0;
		cl.parsingtextexpectingpingforscores = 0;
		cl.parsingtextmode = CL_PARSETEXTMODE_NONE;
		t = text;
		while (*t == ' ')
			t++;
		if ((*t >= '0' && *t <= '9') || *t == '-')
		{
			int ping = atoi(t);
			while ((*t >= '0' && *t <= '9') || *t == '-')
				t++;
			if (*t == ' ')
			{
				int charindex = 0;
				t++;
				if(cl.parsingtextplayerindex < cl.maxclients)
				{
					for (charindex = 0;cl.scores[cl.parsingtextplayerindex].name[charindex] == t[charindex];charindex++)
						;
					                                                                                                                                                                                        
					                                                                                        
					if (t[charindex] == '\n')
					{
						cl.scores[cl.parsingtextplayerindex].qw_ping = bound(0, ping, 9999);
						for (cl.parsingtextplayerindex++;cl.parsingtextplayerindex < cl.maxclients && !cl.scores[cl.parsingtextplayerindex].name[0];cl.parsingtextplayerindex++)
							;
						                                                                                    
						{
							                                                            
							cl.parsingtextmode = CL_PARSETEXTMODE_PING;
							cl.parsingtextexpectingpingforscores = expected;
						}
						return !expected;
					}
				}
				if (!strncmp(t, "unconnected\n", 12))
				{
					              
					cl.parsingtextmode = CL_PARSETEXTMODE_PING;
					cl.parsingtextexpectingpingforscores = expected;
					return !expected;
				}
				else
					Con_DPrintf("player names '%s' and '%s' didn't match\n", cl.scores[cl.parsingtextplayerindex].name, t);
			}
		}
	}
	if (cl.parsingtextmode == CL_PARSETEXTMODE_STATUS)
	{
		if (!strncmp(text, "players: ", 9))
		{
			cl.parsingtextmode = CL_PARSETEXTMODE_STATUS_PLAYERID;
			cl.parsingtextplayerindex = 0;
			return true;
		}
		else if (!strstr(text, ": "))
		{
			cl.parsingtextmode = CL_PARSETEXTMODE_NONE;                       
			return true;
		}
	}
	if (cl.parsingtextmode == CL_PARSETEXTMODE_STATUS_PLAYERID)
	{
		                                                                   
		cl.parsingtextmode = CL_PARSETEXTMODE_NONE;
		if (text[0] == '#' && text[1] >= '0' && text[1] <= '9')
		{
			t = text + 1;
			cl.parsingtextplayerindex = atoi(t) - 1;
			while (*t >= '0' && *t <= '9')
				t++;
			if (*t == ' ')
			{
				cl.parsingtextmode = CL_PARSETEXTMODE_STATUS_PLAYERIP;
				return true;
			}
			                                                          
		}
	}
	if (cl.parsingtextmode == CL_PARSETEXTMODE_STATUS_PLAYERIP)
	{
		                                                                   
		cl.parsingtextmode = CL_PARSETEXTMODE_NONE;
		if (text[0] == ' ')
		{
			t = text;
			while (*t == ' ')
				t++;
			for (len = 0;*t && *t != '\n';t++)
				if (len < (int)sizeof(temp) - 1)
					temp[len++] = *t;
			temp[len] = 0;
			                                                             
			                                                                
			if (strcmp(temp, "botclient")
			 && cl.parsingtextplayerindex >= 0
			 && cl.parsingtextplayerindex < cl.maxclients
			 && cl.scores[cl.parsingtextplayerindex].name[0])
			{
				                                            
				                                                              
				                                
				CL_IPLog_Add(temp, cl.scores[cl.parsingtextplayerindex].name, true, true);
			}
			cl.parsingtextmode = CL_PARSETEXTMODE_STATUS_PLAYERID;
			return true;
		}
	}
	return true;
}

extern cvar_t slowmo;
extern cvar_t cl_lerpexcess;
static void CL_NetworkTimeReceived(double newtime)
{
	double timehigh;
	cl.mtime[1] = cl.mtime[0];
	cl.mtime[0] = newtime;
	if (cl_nolerp.integer || cls.timedemo || (cl.islocalgame && !sv_fixedframeratesingleplayer.integer) || cl.mtime[1] == cl.mtime[0] || cls.signon < SIGNONS)
		cl.time = cl.mtime[1] = newtime;
	else if (cls.demoplayback)
	{
		                                                                                   
		                                                                    
		                                                              
		if (cl.time < newtime - 0.1)
			cl.mtime[1] = cl.time = newtime;
	}
	else if (cls.protocol != PROTOCOL_QUAKEWORLD)
	{
		cl.mtime[1] = max(cl.mtime[1], cl.mtime[0] - 0.1);
		if (developer_extra.integer && vid_activewindow)
		{
			if (cl.time < cl.mtime[1] - (cl.mtime[0] - cl.mtime[1]))
				Con_DPrintf("--- cl.time < cl.mtime[1] (%f < %f ... %f)\n", cl.time, cl.mtime[1], cl.mtime[0]);
			else if (cl.time > cl.mtime[0] + (cl.mtime[0] - cl.mtime[1]))
				Con_DPrintf("--- cl.time > cl.mtime[0] (%f > %f ... %f)\n", cl.time, cl.mtime[1], cl.mtime[0]);
		}
		cl.time += (cl.mtime[1] - cl.time) * bound(0, cl_nettimesyncfactor.value, 1);
		timehigh = cl.mtime[1] + (cl.mtime[0] - cl.mtime[1]) * cl_nettimesyncboundtolerance.value;
		if (cl_nettimesyncboundmode.integer == 1)
			cl.time = bound(cl.mtime[1], cl.time, cl.mtime[0]);
		else if (cl_nettimesyncboundmode.integer == 2)
		{
			if (cl.time < cl.mtime[1] || cl.time > timehigh)
				cl.time = cl.mtime[1];
		}
		else if (cl_nettimesyncboundmode.integer == 3)
		{
			if ((cl.time < cl.mtime[1] && cl.oldtime < cl.mtime[1]) || (cl.time > timehigh && cl.oldtime > timehigh))
				cl.time = cl.mtime[1];
		}
		else if (cl_nettimesyncboundmode.integer == 4)
		{
			if (fabs(cl.time - cl.mtime[1]) > 0.5)
				cl.time = cl.mtime[1];         
			else if (fabs(cl.time - cl.mtime[1]) > 0.1)
				cl.time += 0.5 * (cl.mtime[1] - cl.time);        
			else if (cl.time > cl.mtime[1])
				cl.time -= 0.002 * cl.movevars_timescale;                             
			else
				cl.time += 0.001 * cl.movevars_timescale;                     
		}
		else if (cl_nettimesyncboundmode.integer == 5)
		{
			if (fabs(cl.time - cl.mtime[1]) > 0.5)
				cl.time = cl.mtime[1];         
			else if (fabs(cl.time - cl.mtime[1]) > 0.1)
				cl.time += 0.5 * (cl.mtime[1] - cl.time);        
			else
				cl.time = bound(cl.time - 0.002 * cl.movevars_timescale, cl.mtime[1], cl.time + 0.001 * cl.movevars_timescale);
		}
		else if (cl_nettimesyncboundmode.integer == 6)
		{
			cl.time = bound(cl.mtime[1], cl.time, cl.mtime[0]);
			cl.time = bound(cl.time - 0.002 * cl.movevars_timescale, cl.mtime[1], cl.time + 0.001 * cl.movevars_timescale);
		}
	}
	                                                                        
	                           
	cl.movement_replay = true;
	                                                          
	cl.onground = false;
	                                                                   
	                    
	                                                                                    
	cl.fixangle[1] = cl.fixangle[0];
	cl.fixangle[0] = false;
	if (!cls.demoplayback)
		VectorCopy(cl.mviewangles[0], cl.mviewangles[1]);
	                                                                
	CSQC_UpdateNetworkTimes(cl.mtime[0], cl.mtime[1]);

	if (cl.mtime[0] > cl.mtime[1])
		World_Physics_Frame(&cl.world, cl.mtime[0] - cl.mtime[1], cl.movevars_gravity);

	                                                                                     
	if(cl_lerpexcess.value > 0)
	{
		int i;
		for (i = 1;i < cl.num_entities;i++)
		{
			if (cl.entities_active[i])
			{
				entity_t *ent = cl.entities + i;
				ent->persistent.lerpdeltatime = 0;
			}
		}
	}
}

#define SHOWNET(x) if(cl_shownet.integer==2)Con_Printf("%3i:%s(%i)\n", cl_message.readcount-1, x, cmd);

  
                     
                     
                     
  
int parsingerror = false;
void CL_ParseServerMessage(void)
{
	int			cmd;
	int			i;
	protocolversion_t protocol;
	unsigned char		cmdlog[32];
	const char		*cmdlogname[32], *temp;
	int			cmdindex, cmdcount = 0;
	qboolean	qwplayerupdatereceived;
	qboolean	strip_pqc;
	char vabuf[1024];

	                                                                        
	                                                                        
	                             
	                        
	                                     

	cl.last_received_message = realtime;

	CL_KeepaliveMessage(false);

  
                                           
  
	if (cl_shownet.integer == 1)
		Con_Printf("%f %i\n", realtime, cl_message.cursize);
	else if (cl_shownet.integer == 2)
		Con_Print("------------------\n");

  
                    
  
	                      

	parsingerror = true;

	if (cls.protocol == PROTOCOL_QUAKEWORLD)
	{
		CL_NetworkTimeReceived(realtime);                   

		                    
		cl.qw_num_nails = 0;

		                        
		cl.qw_weaponkick = min(cl.qw_weaponkick + 10 * bound(0, cl.time - cl.oldtime, 0.1), 0);

		cls.servermovesequence = cls.netcon->qw.incoming_sequence;

		qwplayerupdatereceived = false;

		while (1)
		{
			if (cl_message.badread)
				Host_Error ("CL_ParseServerMessage: Bad QW server message");

			cmd = MSG_ReadByte(&cl_message);

			if (cmd == -1)
			{
				SHOWNET("END OF MESSAGE");
				break;		                 
			}

			cmdindex = cmdcount & 31;
			cmdcount++;
			cmdlog[cmdindex] = cmd;

			SHOWNET(qw_svc_strings[cmd]);
			cmdlogname[cmdindex] = qw_svc_strings[cmd];
			if (!cmdlogname[cmdindex])
			{
				                                                                                                                                                  
				const char *d = "<unknown>";
				cmdlogname[cmdindex] = d;
			}

			                 
			switch (cmd)
			{
			default:
				{
					char description[32*64], logtemp[64];
					int count;
					strlcpy(description, "packet dump: ", sizeof(description));
					i = cmdcount - 32;
					if (i < 0)
						i = 0;
					count = cmdcount - i;
					i &= 31;
					while(count > 0)
					{
						dpsnprintf(logtemp, sizeof(logtemp), "%3i:%s ", cmdlog[i], cmdlogname[i]);
						strlcat(description, logtemp, sizeof(description));
						count--;
						i++;
						i &= 31;
					}
					description[strlen(description)-1] = '\n';                                         
					Con_Print(description);
					Host_Error("CL_ParseServerMessage: Illegible server message");
				}
				break;

			case qw_svc_nop:
				                             
				break;

			case qw_svc_disconnect:
				Con_Printf("Server disconnected\n");
				if (cls.demonum != -1)
					CL_NextDemo();
				else
					CL_Disconnect();
				return;

			case qw_svc_print:
				i = MSG_ReadByte(&cl_message);
				temp = MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring));
				if (CL_ExaminePrintString(temp))                                                                          
				{
					if (i == 3)        
						CSQC_AddPrintText(va(vabuf, sizeof(vabuf), "\1%s", temp));	             
					else
						CSQC_AddPrintText(temp);
				}
				break;

			case qw_svc_centerprint:
				CL_VM_Parse_CenterPrint(MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)));	             
				break;

			case qw_svc_stufftext:
				CL_VM_Parse_StuffCmd(MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)));	             
				break;

			case qw_svc_damage:
				                                         
				V_ParseDamage ();
				break;

			case qw_svc_serverdata:
				                                                            
				CL_ParseServerInfo();
				break;

			case qw_svc_setangle:
				for (i=0 ; i<3 ; i++)
					cl.viewangles[i] = MSG_ReadAngle(&cl_message, cls.protocol);
				if (!cls.demoplayback)
				{
					cl.fixangle[0] = true;
					VectorCopy(cl.viewangles, cl.mviewangles[0]);
					                                       
					if (!cl.fixangle[1])
						VectorCopy(cl.viewangles, cl.mviewangles[1]);
				}
				break;

			case qw_svc_lightstyle:
				i = MSG_ReadByte(&cl_message);
				if (i >= cl.max_lightstyle)
				{
					Con_Printf ("svc_lightstyle >= MAX_LIGHTSTYLES");
					break;
				}
				strlcpy (cl.lightstyle[i].map,  MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)), sizeof (cl.lightstyle[i].map));
				cl.lightstyle[i].map[MAX_STYLESTRING - 1] = 0;
				cl.lightstyle[i].length = (int)strlen(cl.lightstyle[i].map);
				break;

			case qw_svc_sound:
				CL_ParseStartSoundPacket(false);
				break;

			case qw_svc_stopsound:
				i = (unsigned short) MSG_ReadShort(&cl_message);
				S_StopSound(i>>3, i&7);
				break;

			case qw_svc_updatefrags:
				i = MSG_ReadByte(&cl_message);
				if (i >= cl.maxclients)
					Host_Error("CL_ParseServerMessage: svc_updatefrags >= cl.maxclients");
				cl.scores[i].frags = (signed short) MSG_ReadShort(&cl_message);
				break;

			case qw_svc_updateping:
				i = MSG_ReadByte(&cl_message);
				if (i >= cl.maxclients)
					Host_Error("CL_ParseServerMessage: svc_updateping >= cl.maxclients");
				cl.scores[i].qw_ping = MSG_ReadShort(&cl_message);
				break;

			case qw_svc_updatepl:
				i = MSG_ReadByte(&cl_message);
				if (i >= cl.maxclients)
					Host_Error("CL_ParseServerMessage: svc_updatepl >= cl.maxclients");
				cl.scores[i].qw_packetloss = MSG_ReadByte(&cl_message);
				break;

			case qw_svc_updateentertime:
				i = MSG_ReadByte(&cl_message);
				if (i >= cl.maxclients)
					Host_Error("CL_ParseServerMessage: svc_updateentertime >= cl.maxclients");
				              
				cl.scores[i].qw_entertime = cl.time - MSG_ReadFloat(&cl_message);
				break;

			case qw_svc_spawnbaseline:
				i = (unsigned short) MSG_ReadShort(&cl_message);
				if (i < 0 || i >= MAX_EDICTS)
					Host_Error ("CL_ParseServerMessage: svc_spawnbaseline: invalid entity number %i", i);
				if (i >= cl.max_entities)
					CL_ExpandEntities(i);
				CL_ParseBaseline(cl.entities + i, false);
				break;
			case qw_svc_spawnstatic:
				CL_ParseStatic(false);
				break;
			case qw_svc_temp_entity:
				if(!CL_VM_Parse_TempEntity())
					CL_ParseTempEntity ();
				break;

			case qw_svc_killedmonster:
				cl.stats[STAT_MONSTERS]++;
				break;

			case qw_svc_foundsecret:
				cl.stats[STAT_SECRETS]++;
				break;

			case qw_svc_updatestat:
				i = MSG_ReadByte(&cl_message);
				if (i < 0 || i >= MAX_CL_STATS)
					Host_Error ("svc_updatestat: %i is invalid", i);
				cl.stats[i] = MSG_ReadByte(&cl_message);
				break;

			case qw_svc_updatestatlong:
				i = MSG_ReadByte(&cl_message);
				if (i < 0 || i >= MAX_CL_STATS)
					Host_Error ("svc_updatestatlong: %i is invalid", i);
				cl.stats[i] = MSG_ReadLong(&cl_message);
				break;

			case qw_svc_spawnstaticsound:
				CL_ParseStaticSound (false);
				break;

			case qw_svc_cdtrack:
				cl.cdtrack = cl.looptrack = MSG_ReadByte(&cl_message);
#ifdef CONFIG_CD
				if ( (cls.demoplayback || cls.demorecording) && (cls.forcetrack != -1) )
					CDAudio_Play ((unsigned char)cls.forcetrack, true);
				else
					CDAudio_Play ((unsigned char)cl.cdtrack, true);
#endif
				break;

			case qw_svc_intermission:
				if(!cl.intermission)
					cl.completed_time = cl.time;
				cl.intermission = 1;
				MSG_ReadVector(&cl_message, cl.qw_intermission_origin, cls.protocol);
				for (i = 0;i < 3;i++)
					cl.qw_intermission_angles[i] = MSG_ReadAngle(&cl_message, cls.protocol);
				break;

			case qw_svc_finale:
				if(!cl.intermission)
					cl.completed_time = cl.time;
				cl.intermission = 2;
				SCR_CenterPrint(MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)));
				break;

			case qw_svc_sellscreen:
				Cmd_ExecuteString ("help", src_command, true);
				break;

			case qw_svc_smallkick:
				cl.qw_weaponkick = -2;
				break;
			case qw_svc_bigkick:
				cl.qw_weaponkick = -4;
				break;

			case qw_svc_muzzleflash:
				i = (unsigned short) MSG_ReadShort(&cl_message);
				                                          
				if (i < 0 || i >= MAX_EDICTS)
					Host_Error("CL_ParseServerMessage: svc_spawnbaseline: invalid entity number %i", i);
				if (i >= cl.max_entities)
					CL_ExpandEntities(i);
				cl.entities[i].persistent.muzzleflash = 1.0f;
				break;

			case qw_svc_updateuserinfo:
				QW_CL_UpdateUserInfo();
				break;

			case qw_svc_setinfo:
				QW_CL_SetInfo();
				break;

			case qw_svc_serverinfo:
				QW_CL_ServerInfo();
				break;

			case qw_svc_download:
				QW_CL_ParseDownload();
				break;

			case qw_svc_playerinfo:
				                                                             
				                                             
				if (!qwplayerupdatereceived)
				{
					qwplayerupdatereceived = true;
					for (i = 1;i < cl.maxclients;i++)
						cl.entities_active[i] = false;
				}
				EntityStateQW_ReadPlayerUpdate();
				break;

			case qw_svc_nails:
				QW_CL_ParseNails();
				break;

			case qw_svc_chokecount:
				(void) MSG_ReadByte(&cl_message);
				                           
				                       
				                                                                                          
				break;

			case qw_svc_modellist:
				QW_CL_ParseModelList();
				break;

			case qw_svc_soundlist:
				QW_CL_ParseSoundList();
				break;

			case qw_svc_packetentities:
				EntityFrameQW_CL_ReadFrame(false);
				                                         
				if (cls.signon == SIGNONS - 1)
				{
					cls.signon = SIGNONS;
					CL_SignonReply ();
				}
				break;

			case qw_svc_deltapacketentities:
				EntityFrameQW_CL_ReadFrame(true);
				                                         
				if (cls.signon == SIGNONS - 1)
				{
					cls.signon = SIGNONS;
					CL_SignonReply ();
				}
				break;

			case qw_svc_maxspeed:
				cl.movevars_maxspeed = MSG_ReadFloat(&cl_message);
				break;

			case qw_svc_entgravity:
				cl.movevars_entgravity = MSG_ReadFloat(&cl_message);
				if (!cl.movevars_entgravity)
					cl.movevars_entgravity = 1.0f;
				break;

			case qw_svc_setpause:
				cl.paused = MSG_ReadByte(&cl_message) != 0;
#ifdef CONFIG_CD
				if (cl.paused)
					CDAudio_Pause ();
				else
					CDAudio_Resume ();
#endif
				S_PauseGameSounds (cl.paused);
				break;
			}
		}

		if (qwplayerupdatereceived)
		{
			                                                                  
			for (i = 1;i <= cl.maxclients;i++)
				if (!cl.entities_active[i])
					cl.entities[i].state_current.active = false;
		}
	}
	else
	{
		while (1)
		{
			if (cl_message.badread)
				Host_Error ("CL_ParseServerMessage: Bad server message");

			cmd = MSG_ReadByte(&cl_message);

			if (cmd == -1)
			{
                                     
				SHOWNET("END OF MESSAGE");
				break;		                 
			}

			cmdindex = cmdcount & 31;
			cmdcount++;
			cmdlog[cmdindex] = cmd;

			                                                                  
			if (cmd & 128)
			{
				                                                                                                                                                  
				temp = "entity";
				cmdlogname[cmdindex] = temp;
				SHOWNET("fast update");
				if (cls.signon == SIGNONS - 1)
				{
					                                         
					cls.signon = SIGNONS;
					CL_SignonReply ();
				}
				EntityFrameQuake_ReadEntity (cmd&127);
				continue;
			}

			SHOWNET(svc_strings[cmd]);
			cmdlogname[cmdindex] = svc_strings[cmd];
			if (!cmdlogname[cmdindex])
			{
				                                                                                                                                                  
				const char *d = "<unknown>";
				cmdlogname[cmdindex] = d;
			}

			                 
			switch (cmd)
			{
			default:
				{
					char description[32*64], tempdesc[64];
					int count;
					strlcpy (description, "packet dump: ", sizeof(description));
					i = cmdcount - 32;
					if (i < 0)
						i = 0;
					count = cmdcount - i;
					i &= 31;
					while(count > 0)
					{
						dpsnprintf (tempdesc, sizeof (tempdesc), "%3i:%s ", cmdlog[i], cmdlogname[i]);
						strlcat (description, tempdesc, sizeof (description));
						count--;
						i++;
						i &= 31;
					}
					description[strlen(description)-1] = '\n';                                         
					Con_Print(description);
					Host_Error ("CL_ParseServerMessage: Illegible server message");
				}
				break;

			case svc_nop:
				if (cls.signon < SIGNONS)
					Con_Print("<-- server to client keepalive\n");
				break;

			case svc_time:
			{
				double previous_network_time = cl.mtime[0];
				CL_NetworkTimeReceived(MSG_ReadFloat(&cl_message));
				if (cl.mtime[0] != previous_network_time)
					Capture_DemoNetworkTimeAdvanced();
				break;
			}

			case svc_clientdata:
				CL_ParseClientdata();
				break;

			case svc_version:
				i = MSG_ReadLong(&cl_message);
				protocol = Protocol_EnumForNumber(i);
				if (protocol == PROTOCOL_UNKNOWN)
					Host_Error("CL_ParseServerMessage: Server is unrecognized protocol number (%i)", i);
				                                                                    
				if (protocol == PROTOCOL_QUAKEDP && cls.demoplayback && gamemode == GAME_NEHAHRA)
					protocol = PROTOCOL_NEHAHRAMOVIE;
				cls.protocol = protocol;
				break;

			case svc_disconnect:
				Con_Printf ("Server disconnected\n");
				if (cls.demonum != -1)
					CL_NextDemo ();
				else
					CL_Disconnect ();
				break;

			case svc_print:
				temp = MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring));
				if (CL_ExaminePrintString(temp))                                                                          
					CSQC_AddPrintText(temp);	             
				break;

			case svc_centerprint:
				CL_VM_Parse_CenterPrint(MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)));	             
				break;

			case svc_stufftext:
				temp = MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring));
				                          
     
                      
                                    
                                    
     
            switch(cls.protocol)
				{
					case PROTOCOL_QUAKE:
					case PROTOCOL_QUAKEDP:
						                               
						                          
						strip_pqc = true;
						break;
					case PROTOCOL_DARKPLACES7:
					default:
						                            
						                  
						strip_pqc = false;
						break;
				}
				if(strip_pqc)
				{
					                               
					                               
					                            
					                                    
					if(*temp == 0x01)
					{
						++temp;
						while(*temp >= 0x01 && *temp <= 0x1F)
							++temp;
					}
				}
				Capture_DemoControlMessageParsed(temp);
				CL_VM_Parse_StuffCmd(temp);	             
				break;

			case svc_damage:
				V_ParseDamage ();
				break;

			case svc_serverinfo:
				CL_ParseServerInfo ();
				break;

			case svc_setangle:
				for (i=0 ; i<3 ; i++)
					cl.viewangles[i] = MSG_ReadAngle(&cl_message, cls.protocol);
				if (!cls.demoplayback)
				{
					cl.fixangle[0] = true;
					VectorCopy(cl.viewangles, cl.mviewangles[0]);
					                                       
					if (!cl.fixangle[1])
						VectorCopy(cl.viewangles, cl.mviewangles[1]);
				}
				break;

			case svc_setview:
				cl.viewentity = (unsigned short)MSG_ReadShort(&cl_message);
				if (cl.viewentity >= MAX_EDICTS)
					Host_Error("svc_setview >= MAX_EDICTS");
				if (cl.viewentity >= cl.max_entities)
					CL_ExpandEntities(cl.viewentity);
				                                                                     
				if (!cl.realplayerentity)
					cl.realplayerentity = cl.viewentity;
				                                                             
				if (cl.viewentity >= 1 && cl.viewentity <= cl.maxclients)
					cl.playerentity = cl.viewentity;
				break;

			case svc_lightstyle:
				i = MSG_ReadByte(&cl_message);
				if (i >= cl.max_lightstyle)
				{
					Con_Printf ("svc_lightstyle >= MAX_LIGHTSTYLES");
					break;
				}
				strlcpy (cl.lightstyle[i].map,  MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)), sizeof (cl.lightstyle[i].map));
				cl.lightstyle[i].map[MAX_STYLESTRING - 1] = 0;
				cl.lightstyle[i].length = (int)strlen(cl.lightstyle[i].map);
				break;

			case svc_sound:
				CL_ParseStartSoundPacket(false);
				break;

			case svc_precache:
				if (cls.protocol == PROTOCOL_DARKPLACES1 || cls.protocol == PROTOCOL_DARKPLACES2 || cls.protocol == PROTOCOL_DARKPLACES3)
				{
					                                                                                     
					CL_ParseStartSoundPacket(true);
				}
				else
				{
					char *s;
					i = (unsigned short)MSG_ReadShort(&cl_message);
					s = MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring));
					if (i < 32768)
					{
						if (i >= 1 && i < MAX_MODELS)
						{
							dp_model_t *model = Mod_ForName(s, false, false, s[0] == '*' ? cl.model_name[1] : NULL);
							if (!model)
								Con_DPrintf("svc_precache: Mod_ForName(\"%s\") failed\n", s);
							cl.model_precache[i] = model;
						}
						else
							Con_Printf("svc_precache: index %i outside range %i...%i\n", i, 1, MAX_MODELS);
					}
					else
					{
						i -= 32768;
						if (i >= 1 && i < MAX_SOUNDS)
						{
							sfx_t *sfx = S_PrecacheSound (s, true, true);
							if (!sfx && snd_initialized.integer)
								Con_DPrintf("svc_precache: S_PrecacheSound(\"%s\") failed\n", s);
							cl.sound_precache[i] = sfx;
						}
						else
							Con_Printf("svc_precache: index %i outside range %i...%i\n", i, 1, MAX_SOUNDS);
					}
				}
				break;

			case svc_stopsound:
				i = (unsigned short) MSG_ReadShort(&cl_message);
				S_StopSound(i>>3, i&7);
				break;

			case svc_updatename:
				i = MSG_ReadByte(&cl_message);
				if (i >= cl.maxclients)
					Host_Error ("CL_ParseServerMessage: svc_updatename >= cl.maxclients");
				strlcpy (cl.scores[i].name, MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)), sizeof (cl.scores[i].name));
				break;

			case svc_updatefrags:
				i = MSG_ReadByte(&cl_message);
				if (i >= cl.maxclients)
					Host_Error ("CL_ParseServerMessage: svc_updatefrags >= cl.maxclients");
				cl.scores[i].frags = (signed short) MSG_ReadShort(&cl_message);
				break;

			case svc_updatecolors:
				i = MSG_ReadByte(&cl_message);
				if (i >= cl.maxclients)
					Host_Error ("CL_ParseServerMessage: svc_updatecolors >= cl.maxclients");
				cl.scores[i].colors = MSG_ReadByte(&cl_message);
				break;

			case svc_particle:
				CL_ParseParticleEffect ();
				break;

			case svc_effect:
				CL_ParseEffect ();
				break;

			case svc_effect2:
				CL_ParseEffect2 ();
				break;

			case svc_spawnbaseline:
				i = (unsigned short) MSG_ReadShort(&cl_message);
				if (i < 0 || i >= MAX_EDICTS)
					Host_Error ("CL_ParseServerMessage: svc_spawnbaseline: invalid entity number %i", i);
				if (i >= cl.max_entities)
					CL_ExpandEntities(i);
				CL_ParseBaseline (cl.entities + i, false);
				break;
			case svc_spawnbaseline2:
				i = (unsigned short) MSG_ReadShort(&cl_message);
				if (i < 0 || i >= MAX_EDICTS)
					Host_Error ("CL_ParseServerMessage: svc_spawnbaseline2: invalid entity number %i", i);
				if (i >= cl.max_entities)
					CL_ExpandEntities(i);
				CL_ParseBaseline (cl.entities + i, true);
				break;
			case svc_spawnstatic:
				CL_ParseStatic (false);
				break;
			case svc_spawnstatic2:
				CL_ParseStatic (true);
				break;
			case svc_temp_entity:
				if(!CL_VM_Parse_TempEntity())
					CL_ParseTempEntity ();
				break;

			case svc_setpause:
				cl.paused = MSG_ReadByte(&cl_message) != 0;
#ifdef CONFIG_CD
				if (cl.paused)
					CDAudio_Pause ();
				else
					CDAudio_Resume ();
#endif
				S_PauseGameSounds (cl.paused);
				break;

			case svc_signonnum:
				i = MSG_ReadByte(&cl_message);
				                                                                 
				                                                           
				if (i <= cls.signon && i != 1)
					Host_Error ("Received signon %i when at %i", i, cls.signon);
				cls.signon = i;
				CL_SignonReply ();
				break;

			case svc_killedmonster:
				cl.stats[STAT_MONSTERS]++;
				break;

			case svc_foundsecret:
				cl.stats[STAT_SECRETS]++;
				break;

			case svc_updatestat:
				i = MSG_ReadByte(&cl_message);
				if (i < 0 || i >= MAX_CL_STATS)
					Host_Error ("svc_updatestat: %i is invalid", i);
				cl.stats[i] = MSG_ReadLong(&cl_message);
				break;

			case svc_updatestatubyte:
				i = MSG_ReadByte(&cl_message);
				if (i < 0 || i >= MAX_CL_STATS)
					Host_Error ("svc_updatestat: %i is invalid", i);
				cl.stats[i] = MSG_ReadByte(&cl_message);
				break;

			case svc_spawnstaticsound:
				CL_ParseStaticSound (false);
				break;

			case svc_spawnstaticsound2:
				CL_ParseStaticSound (true);
				break;

			case svc_cdtrack:
				cl.cdtrack = MSG_ReadByte(&cl_message);
				cl.looptrack = MSG_ReadByte(&cl_message);
#ifdef CONFIG_CD
				if ( (cls.demoplayback || cls.demorecording) && (cls.forcetrack != -1) )
					CDAudio_Play ((unsigned char)cls.forcetrack, true);
				else
					CDAudio_Play ((unsigned char)cl.cdtrack, true);
#endif
				break;

			case svc_intermission:
				if(!cl.intermission)
					cl.completed_time = cl.time;
				cl.intermission = 1;
				CL_VM_UpdateIntermissionState(cl.intermission);
				break;

			case svc_finale:
				if(!cl.intermission)
					cl.completed_time = cl.time;
				cl.intermission = 2;
				CL_VM_UpdateIntermissionState(cl.intermission);
				SCR_CenterPrint(MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)));
				break;

			case svc_cutscene:
				if(!cl.intermission)
					cl.completed_time = cl.time;
				cl.intermission = 3;
				CL_VM_UpdateIntermissionState(cl.intermission);
				SCR_CenterPrint(MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)));
				break;

			case svc_sellscreen:
				Cmd_ExecuteString ("help", src_command, true);
				break;
			case svc_hidelmp:
				if (gamemode == GAME_TENEBRAE)
				{
					                            
					MSG_ReadCoord(&cl_message, cls.protocol);
					MSG_ReadCoord(&cl_message, cls.protocol);
					MSG_ReadCoord(&cl_message, cls.protocol);
					MSG_ReadCoord(&cl_message, cls.protocol);
					MSG_ReadCoord(&cl_message, cls.protocol);
					MSG_ReadCoord(&cl_message, cls.protocol);
					(void) MSG_ReadByte(&cl_message);
					MSG_ReadLong(&cl_message);
					MSG_ReadLong(&cl_message);
					MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring));
				}
				else
					SHOWLMP_decodehide();
				break;
			case svc_showlmp:
				if (gamemode == GAME_TENEBRAE)
				{
					                  
					MSG_ReadCoord(&cl_message, cls.protocol);
					MSG_ReadCoord(&cl_message, cls.protocol);
					MSG_ReadCoord(&cl_message, cls.protocol);
					(void) MSG_ReadByte(&cl_message);
					MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring));
				}
				else
					SHOWLMP_decodeshow();
				break;
			case svc_skybox:
				R_SetSkyBox(MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)));
				break;
			case svc_entities:
				if (cls.signon == SIGNONS - 1)
				{
					                                         
					cls.signon = SIGNONS;
					CL_SignonReply ();
				}
				if (cls.protocol == PROTOCOL_DARKPLACES1 || cls.protocol == PROTOCOL_DARKPLACES2 || cls.protocol == PROTOCOL_DARKPLACES3)
					EntityFrame_CL_ReadFrame();
				else if (cls.protocol == PROTOCOL_DARKPLACES4)
					EntityFrame4_CL_ReadFrame();
				else
					EntityFrame5_CL_ReadFrame();
				break;
			case svc_csqcentities:
				CSQC_ReadEntities();
				break;
			case svc_downloaddata:
				CL_ParseDownload();
				break;
			case svc_trailparticles:
				CL_ParseTrailParticles();
				break;
			case svc_pointparticles:
				CL_ParsePointParticles();
				break;
			case svc_pointparticles1:
				CL_ParsePointParticles1();
				break;
			}
                                    
		}
	}

	if (cls.signon == SIGNONS)
		CL_UpdateItemsAndWeapon();
                               

	EntityFrameQuake_ISeeDeadEntities();
                                    

	CL_UpdateMoveVars();
                                  

	parsingerror = false;

	                                                                          
	              
	if (cls.demorecording)
	{
		CL_WriteDemoMessage (&cl_message);
                              
	}
}

void CL_Parse_DumpPacket(void)
{
	if (!parsingerror)
		return;
	Con_Print("Packet dump:\n");
	SZ_HexDumpToConsole(&cl_message);
	parsingerror = false;
}

void CL_Parse_ErrorCleanUp(void)
{
	CL_StopDownload(0, 0);
	QW_CL_StopUpload();
}

void CL_Parse_Init(void)
{
	Cvar_RegisterVariable(&cl_worldmessage);
	Cvar_RegisterVariable(&cl_worldname);
	Cvar_RegisterVariable(&cl_worldnamenoextension);
	Cvar_RegisterVariable(&cl_worldbasename);

	Cvar_RegisterVariable(&developer_networkentities);
	Cvar_RegisterVariable(&cl_gameplayfix_soundsmovewithentities);

	Cvar_RegisterVariable(&cl_sound_wizardhit);
	Cvar_RegisterVariable(&cl_sound_hknighthit);
	Cvar_RegisterVariable(&cl_sound_tink1);
	Cvar_RegisterVariable(&cl_sound_ric1);
	Cvar_RegisterVariable(&cl_sound_ric2);
	Cvar_RegisterVariable(&cl_sound_ric3);
	Cvar_RegisterVariable(&cl_sound_ric_gunshot);
	Cvar_RegisterVariable(&cl_sound_r_exp3);

	Cvar_RegisterVariable(&cl_joinbeforedownloadsfinish);

	                                                                               
	Cvar_RegisterVariable(&cl_serverextension_download);

	Cvar_RegisterVariable(&cl_nettimesyncfactor);
	Cvar_RegisterVariable(&cl_nettimesyncboundmode);
	Cvar_RegisterVariable(&cl_nettimesyncboundtolerance);
	Cvar_RegisterVariable(&cl_iplog_name);
	Cvar_RegisterVariable(&cl_readpicture_force);

	Cmd_AddCommand("nextul", QW_CL_NextUpload, "sends next fragment of current upload buffer (screenshot for example)");
	Cmd_AddCommand("stopul", QW_CL_StopUpload, "aborts current upload (screenshot for example)");
	Cmd_AddCommand("skins", QW_CL_Skins_f, "downloads missing qw skins from server");
	Cmd_AddCommand("changing", QW_CL_Changing_f, "sent by qw servers to tell client to wait for level change");
	Cmd_AddCommand("cl_begindownloads", CL_BeginDownloads_f, "used internally by darkplaces client while connecting (causes loading of models and sounds or triggers downloads for missing ones)");
	Cmd_AddCommand("cl_downloadbegin", CL_DownloadBegin_f, "(networking) informs client of download file information, client replies with sv_startsoundload to begin the transfer");
	Cmd_AddCommand("stopdownload", CL_StopDownload_f, "terminates a download");
	Cmd_AddCommand("cl_downloadfinished", CL_DownloadFinished_f, "signals that a download has finished and provides the client with file size and crc to check its integrity");
	Cmd_AddCommand("iplog_list", CL_IPLog_List_f, "lists names of players whose IP address begins with the supplied text (example: iplog_list 123.456.789)");
}

void CL_Parse_Shutdown(void)
{
}
