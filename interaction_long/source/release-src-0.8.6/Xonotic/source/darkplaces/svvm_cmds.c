#include "quakedef.h"

#include "prvm_cmds.h"
#include "jpeg.h"

                                                                              
         



const char *vm_sv_extensions =
"BX_WAL_SUPPORT "
"DP_BUTTONCHAT "
"DP_BUTTONUSE "
"DP_CL_LOADSKY "
"DP_CON_ALIASPARAMETERS "
"DP_CON_BESTWEAPON "
"DP_CON_EXPANDCVAR "
"DP_CON_SET "
"DP_CON_SETA "
"DP_CON_STARTMAP "
"DP_COVERAGE "
"DP_CRYPTO "
"DP_CSQC_BINDMAPS "
"DP_CSQC_ENTITYWORLDOBJECT "
"DP_CSQC_ENTITYMODELLIGHT "
"DP_CSQC_ENTITYTRANSPARENTSORTING_OFFSET "
"DP_CSQC_MAINVIEW "
"DP_CSQC_MINFPS_QUALITY "
"DP_CSQC_MULTIFRAME_INTERPOLATION "
"DP_CSQC_BOXPARTICLES "
"DP_CSQC_SPAWNPARTICLE "
"DP_CSQC_QUERYRENDERENTITY "
"DP_CSQC_ROTATEMOVES "
"DP_CSQC_SETPAUSE "
"DP_CSQC_V_CALCREFDEF_WIP1 "
"DP_CSQC_V_CALCREFDEF_WIP2 "
"DP_EF_ADDITIVE "
"DP_EF_BLUE "
"DP_EF_DOUBLESIDED "
"DP_EF_DYNAMICMODELLIGHT "
"DP_EF_FLAME "
"DP_EF_FULLBRIGHT "
"DP_EF_NODEPTHTEST "
"DP_EF_NODRAW "
"DP_EF_NOGUNBOB "
"DP_EF_NOSELFSHADOW "
"DP_EF_NOSHADOW "
"DP_EF_RED "
"DP_EF_RESTARTANIM_BIT "
"DP_EF_STARDUST "
"DP_EF_TELEPORT_BIT "
"DP_ENT_ALPHA "
"DP_ENT_COLORMOD "
"DP_ENT_CUSTOMCOLORMAP "
"DP_ENT_EXTERIORMODELTOCLIENT "
"DP_ENT_GLOW "
"DP_ENT_GLOWMOD "
"DP_ENT_LOWPRECISION "
"DP_ENT_SCALE "
"DP_ENT_TRAILEFFECTNUM "
"DP_ENT_VIEWMODEL "
"DP_GFX_EXTERNALTEXTURES "
"DP_GFX_EXTERNALTEXTURES_PERMAP "
"DP_GFX_FOG "
"DP_GFX_MODEL_INTERPOLATION "
"DP_GFX_QUAKE3MODELTAGS "
"DP_GFX_SKINFILES "
"DP_GFX_SKYBOX "
"DP_GFX_FONTS "
"DP_GFX_FONTS_FREETYPE "
"DP_UTF8 "
"DP_FONT_VARIABLEWIDTH "
"DP_HALFLIFE_MAP "
"DP_HALFLIFE_MAP_CVAR "
"DP_HALFLIFE_SPRITE "
"DP_INPUTBUTTONS "
"DP_LIGHTSTYLE_STATICVALUE "
"DP_LITSPRITES "
"DP_LITSUPPORT "
"DP_MONSTERWALK "
"DP_MOVETYPEBOUNCEMISSILE "
"DP_MOVETYPEFLYWORLDONLY "
"DP_MOVETYPEFOLLOW "
"DP_NULL_MODEL "
"DP_QC_ASINACOSATANATAN2TAN "
"DP_QC_AUTOCVARS "
"DP_QC_CHANGEPITCH "
"DP_QC_CMD "
"DP_QC_COPYENTITY "
"DP_QC_CRC16 "
"DP_QC_CVAR_DEFSTRING "
"DP_QC_CVAR_DESCRIPTION "
"DP_QC_CVAR_STRING "
"DP_QC_CVAR_TYPE "
"DP_QC_DIGEST "
"DP_QC_DIGEST_SHA256 "
"DP_QC_EDICT_NUM "
"DP_QC_ENTITYDATA "
"DP_QC_ENTITYSTRING "
"DP_QC_ETOS "
"DP_QC_EXTRESPONSEPACKET "
"DP_QC_FINDCHAIN "
"DP_QC_FINDCHAINFLAGS "
"DP_QC_FINDCHAINFLOAT "
"DP_QC_FINDCHAIN_TOFIELD "
"DP_QC_FINDFLAGS "
"DP_QC_FINDFLOAT "
"DP_QC_FS_SEARCH "
"DP_QC_GETLIGHT "
"DP_QC_GETSURFACE "
"DP_QC_GETSURFACETRIANGLE "
"DP_QC_GETSURFACEPOINTATTRIBUTE "
"DP_QC_GETTAGINFO "
"DP_QC_GETTAGINFO_BONEPROPERTIES "
"DP_QC_GETTIME "
"DP_QC_GETTIME_CDTRACK "
"DP_QC_I18N "
"DP_QC_LOG "
"DP_QC_MINMAXBOUND "
"DP_QC_MULTIPLETEMPSTRINGS "
"DP_QC_NUM_FOR_EDICT "
"DP_QC_RANDOMVEC "
"DP_QC_SINCOSSQRTPOW "
"DP_QC_SPRINTF "
"DP_QC_STRFTIME "
"DP_QC_STRINGBUFFERS "
"DP_QC_STRINGBUFFERS_CVARLIST "
"DP_QC_STRINGBUFFERS_EXT_WIP "
"DP_QC_STRINGCOLORFUNCTIONS "
"DP_QC_STRING_CASE_FUNCTIONS "
"DP_QC_STRREPLACE "
"DP_QC_TOKENIZEBYSEPARATOR "
"DP_QC_TOKENIZE_CONSOLE "
"DP_QC_TRACEBOX "
"DP_QC_TRACETOSS "
"DP_QC_TRACE_MOVETYPE_HITMODEL "
"DP_QC_TRACE_MOVETYPE_WORLDONLY "
"DP_QC_UNLIMITEDTEMPSTRINGS "
"DP_QC_URI_ESCAPE "
"DP_QC_URI_GET "
"DP_QC_URI_POST "
"DP_QC_VECTOANGLES_WITH_ROLL "
"DP_QC_VECTORVECTORS "
"DP_QC_WHICHPACK "
"DP_QUAKE2_MODEL "
"DP_QUAKE2_SPRITE "
"DP_QUAKE3_MAP "
"DP_QUAKE3_MODEL "
"DP_REGISTERCVAR "
"DP_SKELETONOBJECTS "
"DP_SND_DIRECTIONLESSATTNNONE "
"DP_SND_FAKETRACKS "
"DP_SND_SOUND7_WIP1 "
"DP_SND_SOUND7_WIP2 "
"DP_SND_OGGVORBIS "
"DP_SND_SETPARAMS "
"DP_SND_STEREOWAV "
"DP_SND_GETSOUNDTIME "
"DP_VIDEO_DPV "
"DP_VIDEO_SUBTITLES "
"DP_SOLIDCORPSE "
"DP_SPRITE32 "
"DP_SV_BOTCLIENT "
"DP_SV_BOUNCEFACTOR "
"DP_SV_CLIENTCAMERA "
"DP_SV_CLIENTCOLORS "
"DP_SV_CLIENTNAME "
"DP_SV_CMD "
"DP_SV_CUSTOMIZEENTITYFORCLIENT "
"DP_SV_DISABLECLIENTPREDICTION "
"DP_SV_DISCARDABLEDEMO "
"DP_SV_DRAWONLYTOCLIENT "
"DP_SV_DROPCLIENT "
"DP_SV_EFFECT "
"DP_SV_ENTITYCONTENTSTRANSITION "
"DP_SV_MODELFLAGS_AS_EFFECTS "
"DP_SV_MOVETYPESTEP_LANDEVENT "
"DP_SV_NETADDRESS "
"DP_SV_NODRAWTOCLIENT "
"DP_SV_ONENTITYNOSPAWNFUNCTION "
"DP_SV_ONENTITYPREPOSTSPAWNFUNCTION "
"DP_SV_PING "
"DP_SV_PING_PACKETLOSS "
"DP_SV_PLAYERPHYSICS "
"DP_PHYSICS_ODE "
"DP_SV_POINTPARTICLES "
"DP_SV_POINTSOUND "
"DP_SV_PRECACHEANYTIME "
"DP_SV_PRINT "
"DP_SV_PUNCHVECTOR "
"DP_SV_QCSTATUS "
"DP_SV_ROTATINGBMODEL "
"DP_SV_SETCOLOR "
"DP_SV_SHUTDOWN "
"DP_SV_SLOWMO "
"DP_SV_SPAWNFUNC_PREFIX "
"DP_SV_WRITEPICTURE "
"DP_SV_WRITEUNTERMINATEDSTRING "
"DP_TE_BLOOD "
"DP_TE_BLOODSHOWER "
"DP_TE_CUSTOMFLASH "
"DP_TE_EXPLOSIONRGB "
"DP_TE_FLAMEJET "
"DP_TE_PARTICLECUBE "
"DP_TE_PARTICLERAIN "
"DP_TE_PARTICLESNOW "
"DP_TE_PLASMABURN "
"DP_TE_QUADEFFECTS1 "
"DP_TE_SMALLFLASH "
"DP_TE_SPARK "
"DP_TE_STANDARDEFFECTBUILTINS "
"DP_TRACE_HITCONTENTSMASK_SURFACEINFO "
"DP_USERMOVETYPES "
"DP_VIEWZOOM "
"EXT_BITSHIFT "
"FRIK_FILE "
"FTE_CSQC_SKELETONOBJECTS "
"FTE_QC_CHECKPVS "
"FTE_STRINGS "
"KRIMZON_SV_PARSECLIENTCOMMAND "
"NEH_CMD_PLAY2 "
"NEH_RESTOREGAME "
"NEXUIZ_PLAYERMODEL "
"NXQ_GFX_LETTERBOX "
"PRYDON_CLIENTCURSOR "
"TENEBRAE_GFX_DLIGHTS "
"TW_SV_STEPCONTROL "
"ZQ_PAUSE "
                              
;

  
                 
               

                                                                                                                                                                                                                                                                                                         

                          
                 
  
static void VM_SV_setorigin(prvm_prog_t *prog)
{
	prvm_edict_t	*e;

	VM_SAFEPARMCOUNT(2, VM_setorigin);

	e = PRVM_G_EDICT(OFS_PARM0);
	if (e == prog->edicts)
	{
		VM_Warning(prog, "setorigin: can not modify world entity\n");
		return;
	}
	if (e->priv.server->free)
	{
		VM_Warning(prog, "setorigin: can not modify free entity\n");
		return;
	}
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), PRVM_serveredictvector(e, origin));
	if(e->priv.required->mark == PRVM_EDICT_MARK_WAIT_FOR_SETORIGIN)
		e->priv.required->mark = PRVM_EDICT_MARK_SETORIGIN_CAUGHT;
	SV_LinkEdict(e);
}

                                                                                                               
static void SetMinMaxSize (prvm_prog_t *prog, prvm_edict_t *e, float *min, float *max, qboolean rotate)
{
	int		i;

	for (i=0 ; i<3 ; i++)
		if (min[i] > max[i])
			prog->error_cmd("SetMinMaxSize: backwards mins/maxs");

                     
	VectorCopy (min, PRVM_serveredictvector(e, mins));
	VectorCopy (max, PRVM_serveredictvector(e, maxs));
	VectorSubtract (max, min, PRVM_serveredictvector(e, size));

	SV_LinkEdict(e);
}

  
                 
             

                                            
                         

                                      
                 
  
static void VM_SV_setsize(prvm_prog_t *prog)
{
	prvm_edict_t	*e;
	vec3_t mins, maxs;

	VM_SAFEPARMCOUNT(3, VM_setsize);

	e = PRVM_G_EDICT(OFS_PARM0);
	if (e == prog->edicts)
	{
		VM_Warning(prog, "setsize: can not modify world entity\n");
		return;
	}
	if (e->priv.server->free)
	{
		VM_Warning(prog, "setsize: can not modify free entity\n");
		return;
	}
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), mins);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), maxs);
	SetMinMaxSize(prog, e, mins, maxs, false);
}


  
                 
              

                       
                 
  
static vec3_t quakemins = {-16, -16, -16}, quakemaxs = {16, 16, 16};
static void VM_SV_setmodel(prvm_prog_t *prog)
{
	prvm_edict_t	*e;
	dp_model_t	*mod;
	int		i;

	VM_SAFEPARMCOUNT(2, VM_setmodel);

	e = PRVM_G_EDICT(OFS_PARM0);
	if (e == prog->edicts)
	{
		VM_Warning(prog, "setmodel: can not modify world entity\n");
		return;
	}
	if (e->priv.server->free)
	{
		VM_Warning(prog, "setmodel: can not modify free entity\n");
		return;
	}
	i = SV_ModelIndex(PRVM_G_STRING(OFS_PARM1), 1);
	PRVM_serveredictstring(e, model) = PRVM_SetEngineString(prog, sv.model_precache[i]);
	PRVM_serveredictfloat(e, modelindex) = i;

	mod = SV_GetModelByIndex(i);

	if (mod)
	{
		if (mod->type != mod_alias || sv_gameplayfix_setmodelrealbox.integer)
			SetMinMaxSize(prog, e, mod->normalmins, mod->normalmaxs, true);
		else
			SetMinMaxSize(prog, e, quakemins, quakemaxs, true);
	}
	else
		SetMinMaxSize(prog, e, vec3_origin, vec3_origin, true);
}

  
                 
            

                                 

                        
                 
  
static void VM_SV_sprint(prvm_prog_t *prog)
{
	client_t	*client;
	int			entnum;
	char string[VM_STRINGTEMP_LENGTH];

	VM_SAFEPARMCOUNTRANGE(2, 8, VM_SV_sprint);

	VM_VarString(prog, 1, string, sizeof(string));

	entnum = PRVM_G_EDICTNUM(OFS_PARM0);
	                                                                    
	if (entnum == 0)
	{
		Con_Print(string);
		return;
	}

	if (entnum < 1 || entnum > svs.maxclients || !svs.clients[entnum-1].active)
	{
		VM_Warning(prog, "tried to centerprint to a non-client\n");
		return;
	}

	client = svs.clients + entnum-1;
	if (!client->netconnection)
		return;

	MSG_WriteChar(&client->netconnection->message,svc_print);
	MSG_WriteString(&client->netconnection->message, string);
}


  
                 
                 

                                 

                             
                 
  
static void VM_SV_centerprint(prvm_prog_t *prog)
{
	client_t	*client;
	int			entnum;
	char string[VM_STRINGTEMP_LENGTH];

	VM_SAFEPARMCOUNTRANGE(2, 8, VM_SV_centerprint);

	entnum = PRVM_G_EDICTNUM(OFS_PARM0);

	if (entnum < 1 || entnum > svs.maxclients || !svs.clients[entnum-1].active)
	{
		VM_Warning(prog, "tried to centerprint to a non-client\n");
		return;
	}

	client = svs.clients + entnum-1;
	if (!client->netconnection)
		return;

	VM_VarString(prog, 1, string, sizeof(string));
	MSG_WriteChar(&client->netconnection->message,svc_centerprint);
	MSG_WriteString(&client->netconnection->message, string);
}

  
                 
              

                              
                 
  
static void VM_SV_particle(prvm_prog_t *prog)
{
	vec3_t		org, dir;
	int		color;
	int		count;

	VM_SAFEPARMCOUNT(4, VM_SV_particle);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), org);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), dir);
	color = (int)PRVM_G_FLOAT(OFS_PARM2);
	count = (int)PRVM_G_FLOAT(OFS_PARM3);
	SV_StartParticle (org, dir, color, count);
}


  
                 
                  

                 
  
static void VM_SV_ambientsound(prvm_prog_t *prog)
{
	const char	*samp;
	vec3_t		pos;
	prvm_vec_t	vol, attenuation;
	int			soundnum, large;

	VM_SAFEPARMCOUNT(4, VM_SV_ambientsound);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	samp = PRVM_G_STRING(OFS_PARM1);
	vol = PRVM_G_FLOAT(OFS_PARM2);
	attenuation = PRVM_G_FLOAT(OFS_PARM3);

                                              
	soundnum = SV_SoundIndex(samp, 1);
	if (!soundnum)
		return;

	large = false;
	if (soundnum >= 256)
		large = true;

	                                                             

	if (large)
		MSG_WriteByte (&sv.signon, svc_spawnstaticsound2);
	else
		MSG_WriteByte (&sv.signon, svc_spawnstaticsound);

	MSG_WriteVector(&sv.signon, pos, sv.protocol);

	if (large || sv.protocol == PROTOCOL_NEHAHRABJP || sv.protocol == PROTOCOL_NEHAHRABJP2 || sv.protocol == PROTOCOL_NEHAHRABJP3)
		MSG_WriteShort (&sv.signon, soundnum);
	else
		MSG_WriteByte (&sv.signon, soundnum);

	MSG_WriteByte (&sv.signon, (int)(vol*255));
	MSG_WriteByte (&sv.signon, (int)(attenuation*64));

}

  
                 
           

                                                                 
                  

                                                                   
                                            

                                                                  
                                  

                 
  
static void VM_SV_sound(prvm_prog_t *prog)
{
	const char	*sample;
	int			channel;
	prvm_edict_t		*entity;
	int 		nvolume;
	int flags;
	float attenuation;
	float pitchchange;

	VM_SAFEPARMCOUNTRANGE(4, 7, VM_SV_sound);

	entity = PRVM_G_EDICT(OFS_PARM0);
	channel = (int)PRVM_G_FLOAT(OFS_PARM1);
	sample = PRVM_G_STRING(OFS_PARM2);
	nvolume = (int)(PRVM_G_FLOAT(OFS_PARM3) * 255);
	if (prog->argc < 5)
	{
		Con_DPrintf("VM_SV_sound: given only 4 parameters, expected 5, assuming attenuation = ATTN_NORMAL\n");
		attenuation = 1;
	}
	else
		attenuation = PRVM_G_FLOAT(OFS_PARM4);
	if (prog->argc < 6)
		pitchchange = 0;
	else
		pitchchange = PRVM_G_FLOAT(OFS_PARM5) * 0.01f;

	if (prog->argc < 7)
	{
		flags = 0;
		if(channel >= 8 && channel <= 15)                    
		{
			flags |= CHANNELFLAG_RELIABLE;
			channel -= 8;
		}
	}
	else
	{
		                                                                         
		flags = (int)PRVM_G_FLOAT(OFS_PARM6) & (CHANNELFLAG_RELIABLE | CHANNELFLAG_FORCELOOP | CHANNELFLAG_PAUSED | CHANNELFLAG_FULLVOLUME);
	}

	if (nvolume < 0 || nvolume > 255)
	{
		VM_Warning(prog, "SV_StartSound: volume must be in range 0-1\n");
		return;
	}

	if (attenuation < 0 || attenuation > 4)
	{
		VM_Warning(prog, "SV_StartSound: attenuation must be in range 0-4\n");
		return;
	}

	channel = CHAN_USER2ENGINE(channel);

	if (!IS_CHAN(channel))
	{
		VM_Warning(prog, "SV_StartSound: channel must be in range 0-127\n");
		return;
	}

	SV_StartSound (entity, channel, sample, nvolume, attenuation, flags & CHANNELFLAG_RELIABLE, pitchchange);
}

  
                 
                

                                                        
                                                           
                                              

                 
  
static void VM_SV_pointsound(prvm_prog_t *prog)
{
	const char	*sample;
	int 		nvolume;
	float		attenuation;
	float		pitchchange;
	vec3_t		org;

	VM_SAFEPARMCOUNTRANGE(4, 5, VM_SV_pointsound);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), org);
	sample = PRVM_G_STRING(OFS_PARM1);
	nvolume = (int)(PRVM_G_FLOAT(OFS_PARM2) * 255);
	attenuation = PRVM_G_FLOAT(OFS_PARM3);
	pitchchange = prog->argc < 5 ? 0 : PRVM_G_FLOAT(OFS_PARM4) * 0.01f;

	if (nvolume < 0 || nvolume > 255)
	{
		VM_Warning(prog, "SV_StartPointSound: volume must be in range 0-1\n");
		return;
	}

	if (attenuation < 0 || attenuation > 4)
	{
		VM_Warning(prog, "SV_StartPointSound: attenuation must be in range 0-4\n");
		return;
	}

	SV_StartPointSound (org, sample, nvolume, attenuation, pitchchange);
}

  
                 
               

                                       
                                                                              
                           

                                              
                 
  
static void VM_SV_traceline(prvm_prog_t *prog)
{
	vec3_t	v1, v2;
	trace_t	trace;
	int		move;
	prvm_edict_t	*ent;

	VM_SAFEPARMCOUNTRANGE(4, 8, VM_SV_traceline);                                              

	prog->xfunction->builtinsprofile += 30;

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), v1);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), v2);
	move = (int)PRVM_G_FLOAT(OFS_PARM2);
	ent = PRVM_G_EDICT(OFS_PARM3);

	if (VEC_IS_NAN(v1[0]) || VEC_IS_NAN(v1[1]) || VEC_IS_NAN(v1[2]) || VEC_IS_NAN(v2[0]) || VEC_IS_NAN(v2[1]) || VEC_IS_NAN(v2[2]))
		prog->error_cmd("%s: NAN errors detected in traceline('%f %f %f', '%f %f %f', %i, entity %i)\n", prog->name, v1[0], v1[1], v1[2], v2[0], v2[1], v2[2], move, PRVM_EDICT_TO_PROG(ent));

	trace = SV_TraceLine(v1, v2, move, ent, SV_GenericHitSuperContentsMask(ent), 0, 0, collision_extendtracelinelength.value);

	VM_SetTraceGlobals(prog, &trace);
}


  
                 
              

                                       
                                                                              
                           

                                                              
                 
  
                                                                          
static void VM_SV_tracebox(prvm_prog_t *prog)
{
	vec3_t v1, v2, m1, m2;
	trace_t	trace;
	int		move;
	prvm_edict_t	*ent;

	VM_SAFEPARMCOUNTRANGE(6, 8, VM_SV_tracebox);                                              

	prog->xfunction->builtinsprofile += 30;

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), v1);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), m1);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), m2);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM3), v2);
	move = (int)PRVM_G_FLOAT(OFS_PARM4);
	ent = PRVM_G_EDICT(OFS_PARM5);

	if (VEC_IS_NAN(v1[0]) || VEC_IS_NAN(v1[1]) || VEC_IS_NAN(v1[2]) || VEC_IS_NAN(v2[0]) || VEC_IS_NAN(v2[1]) || VEC_IS_NAN(v2[2]))
		prog->error_cmd("%s: NAN errors detected in tracebox('%f %f %f', '%f %f %f', '%f %f %f', '%f %f %f', %i, entity %i)\n", prog->name, v1[0], v1[1], v1[2], m1[0], m1[1], m1[2], m2[0], m2[1], m2[2], v2[0], v2[1], v2[2], move, PRVM_EDICT_TO_PROG(ent));

	trace = SV_TraceBox(v1, m1, m2, v2, move, ent, SV_GenericHitSuperContentsMask(ent), 0, 0, collision_extendtraceboxlength.value);

	VM_SetTraceGlobals(prog, &trace);
}

static trace_t SV_Trace_Toss(prvm_prog_t *prog, prvm_edict_t *tossent, prvm_edict_t *ignore)
{
	int i;
	float gravity;
	vec3_t move, end, tossentorigin, tossentmins, tossentmaxs;
	vec3_t original_origin;
	vec3_t original_velocity;
	vec3_t original_angles;
	vec3_t original_avelocity;
	trace_t trace;

	VectorCopy(PRVM_serveredictvector(tossent, origin)   , original_origin   );
	VectorCopy(PRVM_serveredictvector(tossent, velocity) , original_velocity );
	VectorCopy(PRVM_serveredictvector(tossent, angles)   , original_angles   );
	VectorCopy(PRVM_serveredictvector(tossent, avelocity), original_avelocity);

	gravity = PRVM_serveredictfloat(tossent, gravity);
	if (!gravity)
		gravity = 1.0f;
	gravity *= sv_gravity.value * 0.025;

	for (i = 0;i < 200;i++)                                                             
	{
		SV_CheckVelocity (tossent);
		PRVM_serveredictvector(tossent, velocity)[2] -= gravity;
		VectorMA (PRVM_serveredictvector(tossent, angles), 0.05, PRVM_serveredictvector(tossent, avelocity), PRVM_serveredictvector(tossent, angles));
		VectorScale (PRVM_serveredictvector(tossent, velocity), 0.05, move);
		VectorAdd (PRVM_serveredictvector(tossent, origin), move, end);
		VectorCopy(PRVM_serveredictvector(tossent, origin), tossentorigin);
		VectorCopy(PRVM_serveredictvector(tossent, mins), tossentmins);
		VectorCopy(PRVM_serveredictvector(tossent, maxs), tossentmaxs);
		trace = SV_TraceBox(tossentorigin, tossentmins, tossentmaxs, end, MOVE_NORMAL, tossent, SV_GenericHitSuperContentsMask(tossent), 0, 0, collision_extendmovelength.value);
		VectorCopy (trace.endpos, PRVM_serveredictvector(tossent, origin));
		PRVM_serveredictvector(tossent, velocity)[2] -= gravity;

		if (trace.fraction < 1)
			break;
	}

	VectorCopy(original_origin   , PRVM_serveredictvector(tossent, origin)   );
	VectorCopy(original_velocity , PRVM_serveredictvector(tossent, velocity) );
	VectorCopy(original_angles   , PRVM_serveredictvector(tossent, angles)   );
	VectorCopy(original_avelocity, PRVM_serveredictvector(tossent, avelocity));

	return trace;
}

static void VM_SV_tracetoss(prvm_prog_t *prog)
{
	trace_t	trace;
	prvm_edict_t	*ent;
	prvm_edict_t	*ignore;

	VM_SAFEPARMCOUNT(2, VM_SV_tracetoss);

	prog->xfunction->builtinsprofile += 600;

	ent = PRVM_G_EDICT(OFS_PARM0);
	if (ent == prog->edicts)
	{
		VM_Warning(prog, "tracetoss: can not use world entity\n");
		return;
	}
	ignore = PRVM_G_EDICT(OFS_PARM1);

	trace = SV_Trace_Toss(prog, ent, ignore);

	VM_SetTraceGlobals(prog, &trace);
}

                                                                              

static int checkpvsbytes;
static unsigned char checkpvs[MAX_MAP_LEAFS/8];

static int VM_SV_newcheckclient(prvm_prog_t *prog, int check)
{
	int		i;
	prvm_edict_t	*ent;
	vec3_t	org;

                        

	check = bound(1, check, svs.maxclients);
	if (check == svs.maxclients)
		i = 1;
	else
		i = check + 1;

	for ( ;  ; i++)
	{
		                 
		prog->xfunction->builtinsprofile++;
		              
		if (i == svs.maxclients+1)
			i = 1;
		                             
		ent = PRVM_EDICT_NUM(i);
		                                                                                               
		if (i != check && (ent->priv.server->free || PRVM_serveredictfloat(ent, health) <= 0 || ((int)PRVM_serveredictfloat(ent, flags) & FL_NOTARGET)))
			continue;
		                                                     
		break;
	}

                             
	VectorAdd(PRVM_serveredictvector(ent, origin), PRVM_serveredictvector(ent, view_ofs), org);
	checkpvsbytes = 0;
	if (sv.worldmodel && sv.worldmodel->brush.FatPVS)
		checkpvsbytes = sv.worldmodel->brush.FatPVS(sv.worldmodel, org, 0, checkpvs, sizeof(checkpvs), false);

	return i;
}

  
                 
                 

                                                                    
             

                                                                  

                                                                        
                          

                   
                 
  
int c_invis, c_notvis;
static void VM_SV_checkclient(prvm_prog_t *prog)
{
	prvm_edict_t	*ent, *self;
	vec3_t	view;

	VM_SAFEPARMCOUNT(0, VM_SV_checkclient);

	                                     
	if (sv.time - sv.lastchecktime >= 0.1)
	{
		sv.lastcheck = VM_SV_newcheckclient(prog, sv.lastcheck);
		sv.lastchecktime = sv.time;
	}

	                                      
	ent = PRVM_EDICT_NUM(sv.lastcheck);
	if (ent->priv.server->free || PRVM_serveredictfloat(ent, health) <= 0)
	{
		VM_RETURN_EDICT(prog->edicts);
		return;
	}

	                                                                  
	self = PRVM_PROG_TO_EDICT(PRVM_serverglobaledict(self));
	VectorAdd(PRVM_serveredictvector(self, origin), PRVM_serveredictvector(self, view_ofs), view);
	if (sv.worldmodel && checkpvsbytes && !sv.worldmodel->brush.BoxTouchingPVS(sv.worldmodel, checkpvs, view, view))
	{
		c_notvis++;
		VM_RETURN_EDICT(prog->edicts);
		return;
	}

	                          
	c_invis++;
	VM_RETURN_EDICT(ent);
}

                                                                              

  
                 
              

                                        
                                  

                                                     
                 
  
static void VM_SV_checkpvs(prvm_prog_t *prog)
{
	vec3_t viewpos, absmin, absmax;
	prvm_edict_t *viewee;
#if 1
	unsigned char *pvs;
#else
	int fatpvsbytes;
	unsigned char fatpvs[MAX_MAP_LEAFS/8];
#endif

	VM_SAFEPARMCOUNT(2, VM_SV_checkpvs);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), viewpos);
	viewee = PRVM_G_EDICT(OFS_PARM1);

	if(viewee->priv.server->free)
	{
		VM_Warning(prog, "checkpvs: can not check free entity\n");
		PRVM_G_FLOAT(OFS_RETURN) = 4;
		return;
	}

#if 1
	if(!sv.worldmodel || !sv.worldmodel->brush.GetPVS || !sv.worldmodel->brush.BoxTouchingPVS)
	{
		                                            
		PRVM_G_FLOAT(OFS_RETURN) = 3;
		return;
	}
	pvs = sv.worldmodel->brush.GetPVS(sv.worldmodel, viewpos);
	if(!pvs)
	{
		                                   
		PRVM_G_FLOAT(OFS_RETURN) = 2;
		return;
	}
	VectorCopy(PRVM_serveredictvector(viewee, absmin), absmin);
	VectorCopy(PRVM_serveredictvector(viewee, absmax), absmax);
	PRVM_G_FLOAT(OFS_RETURN) = sv.worldmodel->brush.BoxTouchingPVS(sv.worldmodel, pvs, absmin, absmax);
#else
	                                       
	if(!sv.worldmodel || !sv.worldmodel->brush.FatPVS || !sv.worldmodel->brush.BoxTouchingPVS)
	{
		                                            
		PRVM_G_FLOAT(OFS_RETURN) = 3;
		return;
	}
	fatpvsbytes = sv.worldmodel->brush.FatPVS(sv.worldmodel, viewpos, 8, fatpvs, sizeof(fatpvs), false);
	if(!fatpvsbytes)
	{
		                                   
		PRVM_G_FLOAT(OFS_RETURN) = 2;
		return;
	}
	VectorCopy(PRVM_serveredictvector(viewee, absmin), absmin);
	VectorCopy(PRVM_serveredictvector(viewee, absmax), absmax);
	PRVM_G_FLOAT(OFS_RETURN) = sv.worldmodel->brush.BoxTouchingPVS(sv.worldmodel, fatpvs, absmin, absmax);
#endif
}


  
                 
              

                                                

                                
                 
  
static void VM_SV_stuffcmd(prvm_prog_t *prog)
{
	int		entnum;
	client_t	*old;
	char	string[VM_STRINGTEMP_LENGTH];

	VM_SAFEPARMCOUNTRANGE(2, 8, VM_SV_stuffcmd);

	entnum = PRVM_G_EDICTNUM(OFS_PARM0);
	if (entnum < 1 || entnum > svs.maxclients || !svs.clients[entnum-1].active)
	{
		VM_Warning(prog, "Can't stuffcmd to a non-client\n");
		return;
	}

	VM_VarString(prog, 1, string, sizeof(string));

	old = host_client;
	host_client = svs.clients + entnum-1;
	Host_ClientCommands ("%s", string);
	host_client = old;
}

  
                 
                

                                                                     

                           
                 
  
static void VM_SV_findradius(prvm_prog_t *prog)
{
	prvm_edict_t *ent, *chain;
	vec_t radius, radius2;
	vec3_t org, eorg, mins, maxs;
	int i;
	int numtouchedicts;
	static prvm_edict_t *touchedicts[MAX_EDICTS];
	int chainfield;

	VM_SAFEPARMCOUNTRANGE(2, 3, VM_SV_findradius);

	if(prog->argc == 3)
		chainfield = PRVM_G_INT(OFS_PARM2);
	else
		chainfield = prog->fieldoffsets.chain;
	if (chainfield < 0)
		prog->error_cmd("VM_findchain: %s doesnt have the specified chain field !", prog->name);

	chain = (prvm_edict_t *)prog->edicts;

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), org);
	radius = PRVM_G_FLOAT(OFS_PARM1);
	radius2 = radius * radius;

	mins[0] = org[0] - (radius + 1);
	mins[1] = org[1] - (radius + 1);
	mins[2] = org[2] - (radius + 1);
	maxs[0] = org[0] + (radius + 1);
	maxs[1] = org[1] + (radius + 1);
	maxs[2] = org[2] + (radius + 1);
	numtouchedicts = SV_EntitiesInBox(mins, maxs, MAX_EDICTS, touchedicts);
	if (numtouchedicts > MAX_EDICTS)
	{
		                     
		Con_Printf("SV_EntitiesInBox returned %i edicts, max was %i\n", numtouchedicts, MAX_EDICTS);
		numtouchedicts = MAX_EDICTS;
	}
	for (i = 0;i < numtouchedicts;i++)
	{
		ent = touchedicts[i];
		prog->xfunction->builtinsprofile++;
		                                                              
		                                                              
		if (PRVM_serveredictfloat(ent, solid) == SOLID_NOT && !sv_gameplayfix_blowupfallenzombies.integer)
			continue;
		                                                                   
		                                                                   
		                      
		VectorSubtract(org, PRVM_serveredictvector(ent, origin), eorg);
		if (sv_gameplayfix_findradiusdistancetobox.integer)
		{
			eorg[0] -= bound(PRVM_serveredictvector(ent, mins)[0], eorg[0], PRVM_serveredictvector(ent, maxs)[0]);
			eorg[1] -= bound(PRVM_serveredictvector(ent, mins)[1], eorg[1], PRVM_serveredictvector(ent, maxs)[1]);
			eorg[2] -= bound(PRVM_serveredictvector(ent, mins)[2], eorg[2], PRVM_serveredictvector(ent, maxs)[2]);
		}
		else
			VectorMAMAM(1, eorg, -0.5f, PRVM_serveredictvector(ent, mins), -0.5f, PRVM_serveredictvector(ent, maxs), eorg);
		if (DotProduct(eorg, eorg) < radius2)
		{
			PRVM_EDICTFIELDEDICT(ent,chainfield) = PRVM_EDICT_TO_PROG(chain);
			chain = ent;
		}
	}

	VM_RETURN_EDICT(chain);
}

static void VM_SV_precache_sound(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_precache_sound);
	PRVM_G_FLOAT(OFS_RETURN) = SV_SoundIndex(PRVM_G_STRING(OFS_PARM0), 2);
}

static void VM_SV_precache_model(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_precache_model);
	SV_ModelIndex(PRVM_G_STRING(OFS_PARM0), 2);
	PRVM_G_INT(OFS_RETURN) = PRVM_G_INT(OFS_PARM0);
}

  
               
              

                                                 
               
  
static void VM_SV_walkmove(prvm_prog_t *prog)
{
	prvm_edict_t	*ent;
	float	yaw, dist;
	vec3_t	move;
	mfunction_t	*oldf;
	int 	oldself;
	qboolean	settrace;

	VM_SAFEPARMCOUNTRANGE(2, 3, VM_SV_walkmove);

	                                     
	PRVM_G_FLOAT(OFS_RETURN) = 0;

	ent = PRVM_PROG_TO_EDICT(PRVM_serverglobaledict(self));
	if (ent == prog->edicts)
	{
		VM_Warning(prog, "walkmove: can not modify world entity\n");
		return;
	}
	if (ent->priv.server->free)
	{
		VM_Warning(prog, "walkmove: can not modify free entity\n");
		return;
	}
	yaw = PRVM_G_FLOAT(OFS_PARM0);
	dist = PRVM_G_FLOAT(OFS_PARM1);
	settrace = prog->argc >= 3 && PRVM_G_FLOAT(OFS_PARM2);

	if ( !( (int)PRVM_serveredictfloat(ent, flags) & (FL_ONGROUND|FL_FLY|FL_SWIM) ) )
		return;

	yaw = yaw*M_PI*2 / 360;

	move[0] = cos(yaw)*dist;
	move[1] = sin(yaw)*dist;
	move[2] = 0;

                                                               
	oldf = prog->xfunction;
	oldself = PRVM_serverglobaledict(self);

	PRVM_G_FLOAT(OFS_RETURN) = SV_movestep(ent, move, true, false, settrace);


                        
	prog->xfunction = oldf;
	PRVM_serverglobaledict(self) = oldself;
}

  
               
                 

                  
               
  

static void VM_SV_droptofloor(prvm_prog_t *prog)
{
	prvm_edict_t		*ent;
	vec3_t		end, entorigin, entmins, entmaxs;
	trace_t		trace;

	VM_SAFEPARMCOUNTRANGE(0, 2, VM_SV_droptofloor);                                                                         

	                                     
	PRVM_G_FLOAT(OFS_RETURN) = 0;

	ent = PRVM_PROG_TO_EDICT(PRVM_serverglobaledict(self));
	if (ent == prog->edicts)
	{
		VM_Warning(prog, "droptofloor: can not modify world entity\n");
		return;
	}
	if (ent->priv.server->free)
	{
		VM_Warning(prog, "droptofloor: can not modify free entity\n");
		return;
	}

	VectorCopy (PRVM_serveredictvector(ent, origin), end);
	end[2] -= 256;

	if (sv_gameplayfix_droptofloorstartsolid_nudgetocorrect.integer)
		SV_NudgeOutOfSolid(ent);

	VectorCopy(PRVM_serveredictvector(ent, origin), entorigin);
	VectorCopy(PRVM_serveredictvector(ent, mins), entmins);
	VectorCopy(PRVM_serveredictvector(ent, maxs), entmaxs);
	trace = SV_TraceBox(entorigin, entmins, entmaxs, end, MOVE_NORMAL, ent, SV_GenericHitSuperContentsMask(ent), 0, 0, collision_extendmovelength.value);
	if (trace.startsolid && sv_gameplayfix_droptofloorstartsolid.integer)
	{
		vec3_t offset, org;
		VectorSet(offset, 0.5f * (PRVM_serveredictvector(ent, mins)[0] + PRVM_serveredictvector(ent, maxs)[0]), 0.5f * (PRVM_serveredictvector(ent, mins)[1] + PRVM_serveredictvector(ent, maxs)[1]), PRVM_serveredictvector(ent, mins)[2]);
		VectorAdd(PRVM_serveredictvector(ent, origin), offset, org);
		trace = SV_TraceLine(org, end, MOVE_NORMAL, ent, SV_GenericHitSuperContentsMask(ent), 0, 0, collision_extendmovelength.value);
		VectorSubtract(trace.endpos, offset, trace.endpos);
		if (trace.startsolid)
		{
			Con_DPrintf("droptofloor at %f %f %f - COULD NOT FIX BADLY PLACED ENTITY\n", PRVM_serveredictvector(ent, origin)[0], PRVM_serveredictvector(ent, origin)[1], PRVM_serveredictvector(ent, origin)[2]);
			SV_LinkEdict(ent);
			PRVM_serveredictfloat(ent, flags) = (int)PRVM_serveredictfloat(ent, flags) | FL_ONGROUND;
			PRVM_serveredictedict(ent, groundentity) = 0;
			PRVM_G_FLOAT(OFS_RETURN) = 1;
		}
		else if (trace.fraction < 1)
		{
			Con_DPrintf("droptofloor at %f %f %f - FIXED BADLY PLACED ENTITY\n", PRVM_serveredictvector(ent, origin)[0], PRVM_serveredictvector(ent, origin)[1], PRVM_serveredictvector(ent, origin)[2]);
			VectorCopy (trace.endpos, PRVM_serveredictvector(ent, origin));
			if (sv_gameplayfix_droptofloorstartsolid_nudgetocorrect.integer)
				SV_NudgeOutOfSolid(ent);
			SV_LinkEdict(ent);
			PRVM_serveredictfloat(ent, flags) = (int)PRVM_serveredictfloat(ent, flags) | FL_ONGROUND;
			PRVM_serveredictedict(ent, groundentity) = PRVM_EDICT_TO_PROG(trace.ent);
			PRVM_G_FLOAT(OFS_RETURN) = 1;
			                                                                                          
			ent->priv.server->suspendedinairflag = true;
		}
	}
	else
	{
		if (!trace.allsolid && trace.fraction < 1)
		{
			VectorCopy (trace.endpos, PRVM_serveredictvector(ent, origin));
			SV_LinkEdict(ent);
			PRVM_serveredictfloat(ent, flags) = (int)PRVM_serveredictfloat(ent, flags) | FL_ONGROUND;
			PRVM_serveredictedict(ent, groundentity) = PRVM_EDICT_TO_PROG(trace.ent);
			PRVM_G_FLOAT(OFS_RETURN) = 1;
			                                                                                          
			ent->priv.server->suspendedinairflag = true;
		}
	}
}

  
               
                

                                          
               
  
static void VM_SV_lightstyle(prvm_prog_t *prog)
{
	int		style;
	const char	*val;
	client_t	*client;
	int			j;

	VM_SAFEPARMCOUNT(2, VM_SV_lightstyle);

	style = (int)PRVM_G_FLOAT(OFS_PARM0);
	val = PRVM_G_STRING(OFS_PARM1);

	if( (unsigned) style >= MAX_LIGHTSTYLES ) {
		prog->error_cmd( "PF_lightstyle: style: %i >= 64", style );
	}

                          
	strlcpy(sv.lightstyles[style], val, sizeof(sv.lightstyles[style]));

                                             
	if (sv.state != ss_active)
		return;

	for (j = 0, client = svs.clients;j < svs.maxclients;j++, client++)
	{
		if (client->active && client->netconnection)
		{
			MSG_WriteChar (&client->netconnection->message, svc_lightstyle);
			MSG_WriteChar (&client->netconnection->message,style);
			MSG_WriteString (&client->netconnection->message, val);
		}
	}
}

  
             
                 
             
  
static void VM_SV_checkbottom(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_checkbottom);
	PRVM_G_FLOAT(OFS_RETURN) = SV_CheckBottom (PRVM_G_EDICT(OFS_PARM0));
}

  
             
                   
             
  
static void VM_SV_pointcontents(prvm_prog_t *prog)
{
	vec3_t point;
	VM_SAFEPARMCOUNT(1, VM_SV_pointcontents);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), point);
	PRVM_G_FLOAT(OFS_RETURN) = Mod_Q1BSP_NativeContentsFromSuperContents(SV_PointSuperContents(point));
}

  
             
         

                                           
                                
             
  
static void VM_SV_aim(prvm_prog_t *prog)
{
	prvm_edict_t	*ent, *check, *bestent;
	vec3_t	start, dir, end, bestdir;
	int		i, j;
	trace_t	tr;
	float	dist, bestdist;
	              

	VM_SAFEPARMCOUNT(2, VM_SV_aim);

	                                     
	VectorCopy(PRVM_serverglobalvector(v_forward), PRVM_G_VECTOR(OFS_RETURN));
	                                                                         
	if (sv_aim.value >= 1)
		return;

	ent = PRVM_G_EDICT(OFS_PARM0);
	if (ent == prog->edicts)
	{
		VM_Warning(prog, "aim: can not use world entity\n");
		return;
	}
	if (ent->priv.server->free)
	{
		VM_Warning(prog, "aim: can not use free entity\n");
		return;
	}
	                                  

	VectorCopy (PRVM_serveredictvector(ent, origin), start);
	start[2] += 20;

                               
	VectorCopy (PRVM_serverglobalvector(v_forward), dir);
	VectorMA (start, 2048, dir, end);
	tr = SV_TraceLine(start, end, MOVE_NORMAL, ent, SUPERCONTENTS_SOLID | SUPERCONTENTS_BODY, 0, 0, collision_extendmovelength.value);
	if (tr.ent && PRVM_serveredictfloat(((prvm_edict_t *)tr.ent), takedamage) == DAMAGE_AIM
	&& (!teamplay.integer || PRVM_serveredictfloat(ent, team) <=0 || PRVM_serveredictfloat(ent, team) != PRVM_serveredictfloat(((prvm_edict_t *)tr.ent), team)) )
	{
		VectorCopy (PRVM_serverglobalvector(v_forward), PRVM_G_VECTOR(OFS_RETURN));
		return;
	}


                            
	VectorCopy (dir, bestdir);
	bestdist = sv_aim.value;
	bestent = NULL;

	check = PRVM_NEXT_EDICT(prog->edicts);
	for (i=1 ; i<prog->num_edicts ; i++, check = PRVM_NEXT_EDICT(check) )
	{
		prog->xfunction->builtinsprofile++;
		if (PRVM_serveredictfloat(check, takedamage) != DAMAGE_AIM)
			continue;
		if (check == ent)
			continue;
		if (teamplay.integer && PRVM_serveredictfloat(ent, team) > 0 && PRVM_serveredictfloat(ent, team) == PRVM_serveredictfloat(check, team))
			continue;	                        
		for (j=0 ; j<3 ; j++)
			end[j] = PRVM_serveredictvector(check, origin)[j]
			+ 0.5*(PRVM_serveredictvector(check, mins)[j] + PRVM_serveredictvector(check, maxs)[j]);
		VectorSubtract (end, start, dir);
		VectorNormalize (dir);
		dist = DotProduct (dir, PRVM_serverglobalvector(v_forward));
		if (dist < bestdist)
			continue;	                 
		tr = SV_TraceLine(start, end, MOVE_NORMAL, ent, SUPERCONTENTS_SOLID | SUPERCONTENTS_BODY, 0, 0, collision_extendmovelength.value);
		if (tr.ent == check)
		{	                        
			bestdist = dist;
			bestent = check;
		}
	}

	if (bestent)
	{
		VectorSubtract (PRVM_serveredictvector(bestent, origin), PRVM_serveredictvector(ent, origin), dir);
		dist = DotProduct (dir, PRVM_serverglobalvector(v_forward));
		VectorScale (PRVM_serverglobalvector(v_forward), dist, end);
		end[2] = dir[2];
		VectorNormalize (end);
		VectorCopy (end, PRVM_G_VECTOR(OFS_RETURN));
	}
	else
	{
		VectorCopy (bestdir, PRVM_G_VECTOR(OFS_RETURN));
	}
}

  
                                                                               

               

                                                                               
  

#define	MSG_BROADCAST	0		                    
#define	MSG_ONE			1		                               
#define	MSG_ALL			2		                  
#define	MSG_INIT		3		                           
#define	MSG_ENTITY		5

static sizebuf_t *WriteDest(prvm_prog_t *prog)
{
	int		entnum;
	int		dest;
	prvm_edict_t	*ent;

	dest = (int)PRVM_G_FLOAT(OFS_PARM0);
	switch (dest)
	{
	case MSG_BROADCAST:
		return &sv.datagram;

	case MSG_ONE:
		ent = PRVM_PROG_TO_EDICT(PRVM_serverglobaledict(msg_entity));
		entnum = PRVM_NUM_FOR_EDICT(ent);
		if (entnum < 1 || entnum > svs.maxclients || !svs.clients[entnum-1].active || !svs.clients[entnum-1].netconnection)
		{
			VM_Warning(prog, "WriteDest: tried to write to non-client\n");
			return &sv.reliable_datagram;
		}
		else
			return &svs.clients[entnum-1].netconnection->message;

	default:
		VM_Warning(prog, "WriteDest: bad destination\n");
	case MSG_ALL:
		return &sv.reliable_datagram;

	case MSG_INIT:
		return &sv.signon;

	case MSG_ENTITY:
		return sv.writeentitiestoclient_msg;
	}

	              
}

static void VM_SV_WriteByte(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(2, VM_SV_WriteByte);
	MSG_WriteByte (WriteDest(prog), (int)PRVM_G_FLOAT(OFS_PARM1));
}

static void VM_SV_WriteChar(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(2, VM_SV_WriteChar);
	MSG_WriteChar (WriteDest(prog), (int)PRVM_G_FLOAT(OFS_PARM1));
}

static void VM_SV_WriteShort(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(2, VM_SV_WriteShort);
	MSG_WriteShort (WriteDest(prog), (int)PRVM_G_FLOAT(OFS_PARM1));
}

static void VM_SV_WriteLong(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(2, VM_SV_WriteLong);
	MSG_WriteLong (WriteDest(prog), (int)PRVM_G_FLOAT(OFS_PARM1));
}

static void VM_SV_WriteAngle(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(2, VM_SV_WriteAngle);
	MSG_WriteAngle (WriteDest(prog), PRVM_G_FLOAT(OFS_PARM1), sv.protocol);
}

static void VM_SV_WriteCoord(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(2, VM_SV_WriteCoord);
	MSG_WriteCoord (WriteDest(prog), PRVM_G_FLOAT(OFS_PARM1), sv.protocol);
}

static void VM_SV_WriteString(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(2, VM_SV_WriteString);
	MSG_WriteString (WriteDest(prog), PRVM_G_STRING(OFS_PARM1));
}

static void VM_SV_WriteUnterminatedString(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(2, VM_SV_WriteUnterminatedString);
	MSG_WriteUnterminatedString (WriteDest(prog), PRVM_G_STRING(OFS_PARM1));
}


static void VM_SV_WriteEntity(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(2, VM_SV_WriteEntity);
	MSG_WriteShort (WriteDest(prog), PRVM_G_EDICTNUM(OFS_PARM1));
}

                                                 
           
                                   
                              
                     
                                                                                      
static void VM_SV_WritePicture(prvm_prog_t *prog)
{
	const char *imgname;
	void *buf;
	size_t size;

	VM_SAFEPARMCOUNT(3, VM_SV_WritePicture);

	imgname = PRVM_G_STRING(OFS_PARM1);
	size = (size_t) PRVM_G_FLOAT(OFS_PARM2);
	if(size > 65535)
		size = 65535;

	MSG_WriteString(WriteDest(prog), imgname);
	if(Image_Compress(imgname, size, &buf, &size))
	{
		                 
		MSG_WriteShort(WriteDest(prog), (int)size);
		SZ_Write(WriteDest(prog), (unsigned char *) buf, (int)size);
	}
	else
	{
		              
		MSG_WriteShort(WriteDest(prog), 0);
	}
}

                                                          

static void VM_SV_makestatic(prvm_prog_t *prog)
{
	prvm_edict_t *ent;
	int i, large;

	                                                                         
	                                                                          
	VM_SAFEPARMCOUNTRANGE(0, 1, VM_SV_makestatic);

	if (prog->argc >= 1)
		ent = PRVM_G_EDICT(OFS_PARM0);
	else
		ent = PRVM_PROG_TO_EDICT(PRVM_serverglobaledict(self));
	if (ent == prog->edicts)
	{
		VM_Warning(prog, "makestatic: can not modify world entity\n");
		return;
	}
	if (ent->priv.server->free)
	{
		VM_Warning(prog, "makestatic: can not modify free entity\n");
		return;
	}

	large = false;
	if (PRVM_serveredictfloat(ent, modelindex) >= 256 || PRVM_serveredictfloat(ent, frame) >= 256)
		large = true;

	if (large)
	{
		MSG_WriteByte (&sv.signon,svc_spawnstatic2);
		MSG_WriteShort (&sv.signon, (int)PRVM_serveredictfloat(ent, modelindex));
		MSG_WriteShort (&sv.signon, (int)PRVM_serveredictfloat(ent, frame));
	}
	else if (sv.protocol == PROTOCOL_NEHAHRABJP || sv.protocol == PROTOCOL_NEHAHRABJP2 || sv.protocol == PROTOCOL_NEHAHRABJP3)
	{
		MSG_WriteByte (&sv.signon,svc_spawnstatic);
		MSG_WriteShort (&sv.signon, (int)PRVM_serveredictfloat(ent, modelindex));
		MSG_WriteByte (&sv.signon, (int)PRVM_serveredictfloat(ent, frame));
	}
	else
	{
		MSG_WriteByte (&sv.signon,svc_spawnstatic);
		MSG_WriteByte (&sv.signon, (int)PRVM_serveredictfloat(ent, modelindex));
		MSG_WriteByte (&sv.signon, (int)PRVM_serveredictfloat(ent, frame));
	}

	MSG_WriteByte (&sv.signon, (int)PRVM_serveredictfloat(ent, colormap));
	MSG_WriteByte (&sv.signon, (int)PRVM_serveredictfloat(ent, skin));
	for (i=0 ; i<3 ; i++)
	{
		MSG_WriteCoord(&sv.signon, PRVM_serveredictvector(ent, origin)[i], sv.protocol);
		MSG_WriteAngle(&sv.signon, PRVM_serveredictvector(ent, angles)[i], sv.protocol);
	}

                            
	PRVM_ED_Free(prog, ent);
}

                                                                               

  
              
                   
              
  
static void VM_SV_setspawnparms(prvm_prog_t *prog)
{
	prvm_edict_t	*ent;
	int		i;
	client_t	*client;

	VM_SAFEPARMCOUNT(1, VM_SV_setspawnparms);

	ent = PRVM_G_EDICT(OFS_PARM0);
	i = PRVM_NUM_FOR_EDICT(ent);
	if (i < 1 || i > svs.maxclients || !svs.clients[i-1].active)
	{
		Con_Print("tried to setspawnparms on a non-client\n");
		return;
	}

	                                       
	client = svs.clients + i-1;
	for (i=0 ; i< NUM_SPAWN_PARMS ; i++)
		(&PRVM_serverglobalfloat(parm1))[i] = client->spawn_parms[i];
}

  
                 
              

                                                                      

                                                                                  
                                                           

                
                 
  
static void VM_SV_getlight(prvm_prog_t *prog)
{
	vec3_t ambientcolor, diffusecolor, diffusenormal;
	vec3_t p;
	VM_SAFEPARMCOUNT(1, VM_SV_getlight);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), p);
	VectorClear(ambientcolor);
	VectorClear(diffusecolor);
	VectorClear(diffusenormal);
	if (sv.worldmodel && sv.worldmodel->brush.LightPoint)
		sv.worldmodel->brush.LightPoint(sv.worldmodel, p, ambientcolor, diffusecolor, diffusenormal);
	VectorMA(ambientcolor, 0.5, diffusecolor, PRVM_G_VECTOR(OFS_RETURN));
}

typedef struct
{
	unsigned char	type;	                                     
	int		fieldoffset;
}customstat_t;

static customstat_t *vm_customstats = NULL;	                                 
static int vm_customstats_last;

void VM_CustomStats_Clear (void)
{
	if(vm_customstats)
	{
		Z_Free(vm_customstats);
		vm_customstats = NULL;
		vm_customstats_last = -1;
	}
}

void VM_SV_UpdateCustomStats (client_t *client, prvm_edict_t *ent, sizebuf_t *msg, int *stats)
{
	prvm_prog_t *prog = SVVM_prog;
	int			i;
	char		s[17];
	union {
		int i;
		float f;
	} u;

	if(!vm_customstats)
		return;

	for(i=0; i<vm_customstats_last+1 ;i++)
	{
		if(!vm_customstats[i].type)
			continue;
		switch(vm_customstats[i].type)
		{
		                    
		case 1:
			memset(s, 0, 17);
			strlcpy(s, PRVM_E_STRING(ent, vm_customstats[i].fieldoffset), 16);
			stats[i+32] = s[ 0] + s[ 1] * 256 + s[ 2] * 65536 + s[ 3] * 16777216;
			stats[i+33] = s[ 4] + s[ 5] * 256 + s[ 6] * 65536 + s[ 7] * 16777216;
			stats[i+34] = s[ 8] + s[ 9] * 256 + s[10] * 65536 + s[11] * 16777216;
			stats[i+35] = s[12] + s[13] * 256 + s[14] * 65536 + s[15] * 16777216;
			break;
		                        
		case 8:
			                                                                                                                              
			u.f = PRVM_E_FLOAT(ent, vm_customstats[i].fieldoffset);
			stats[i+32] = u.i;
			break;
		                              
		case 2:
			stats[i+32] = (int)PRVM_E_FLOAT(ent, vm_customstats[i].fieldoffset);
			break;
		default:
			break;
		}
	}
}

                                                                
                                   
                                                                             
                                                                                            
                                                                  
                                                                                 
                                                                                                                                   
static void VM_SV_AddStat(prvm_prog_t *prog)
{
	int		off, i;
	unsigned char	type;

	VM_SAFEPARMCOUNT(3, VM_SV_AddStat);

	if(!vm_customstats)
	{
		vm_customstats = (customstat_t *)Z_Malloc((MAX_CL_STATS-32) * sizeof(customstat_t));
		if(!vm_customstats)
		{
			VM_Warning(prog, "PF_SV_AddStat: not enough memory\n");
			return;
		}
	}
	i		= (int)PRVM_G_FLOAT(OFS_PARM0);
	type	= (int)PRVM_G_FLOAT(OFS_PARM1);
	off		= PRVM_G_INT  (OFS_PARM2);
	i -= 32;

	if(i < 0)
	{
		VM_Warning(prog, "PF_SV_AddStat: index may not be less than 32\n");
		return;
	}
	if(i >= (MAX_CL_STATS-32))
	{
		VM_Warning(prog, "PF_SV_AddStat: index >= MAX_CL_STATS\n");
		return;
	}
	if(i > (MAX_CL_STATS-32-4) && type == 1)
	{
		VM_Warning(prog, "PF_SV_AddStat: index > (MAX_CL_STATS-4) with string\n");
		return;
	}
	vm_customstats[i].type		= type;
	vm_customstats[i].fieldoffset	= off;
	if(vm_customstats_last < i)
		vm_customstats_last = i;
}

  
                 
                

                                      

                    
                 
  
static void VM_SV_copyentity(prvm_prog_t *prog)
{
	prvm_edict_t *in, *out;
	VM_SAFEPARMCOUNT(2, VM_SV_copyentity);
	in = PRVM_G_EDICT(OFS_PARM0);
	if (in == prog->edicts)
	{
		VM_Warning(prog, "copyentity: can not read world entity\n");
		return;
	}
	if (in->priv.server->free)
	{
		VM_Warning(prog, "copyentity: can not read free entity\n");
		return;
	}
	out = PRVM_G_EDICT(OFS_PARM1);
	if (out == prog->edicts)
	{
		VM_Warning(prog, "copyentity: can not modify world entity\n");
		return;
	}
	if (out->priv.server->free)
	{
		VM_Warning(prog, "copyentity: can not modify free entity\n");
		return;
	}
	memcpy(out->fields.fp, in->fields.fp, prog->entityfields * sizeof(prvm_vec_t));
	if (VectorCompare(PRVM_serveredictvector(out, absmin), PRVM_serveredictvector(out, absmax)))
		return;
	SV_LinkEdict(out);
}


  
                 
              

                                                                             

                          
                 
  
static void VM_SV_setcolor(prvm_prog_t *prog)
{
	client_t *client;
	int entnum, i;

	VM_SAFEPARMCOUNT(2, VM_SV_setcolor);
	entnum = PRVM_G_EDICTNUM(OFS_PARM0);
	i = (int)PRVM_G_FLOAT(OFS_PARM1);

	if (entnum < 1 || entnum > svs.maxclients || !svs.clients[entnum-1].active)
	{
		Con_Print("tried to setcolor a non-client\n");
		return;
	}

	client = svs.clients + entnum-1;
	if (client->edict)
	{
		PRVM_serveredictfloat(client->edict, clientcolors) = i;
		PRVM_serveredictfloat(client->edict, team) = (i & 15) + 1;
	}
	client->colors = i;
	if (client->old_colors != client->colors)
	{
		client->old_colors = client->colors;
		                                   
		MSG_WriteByte (&sv.reliable_datagram, svc_updatecolors);
		MSG_WriteByte (&sv.reliable_datagram, client - svs.clients);
		MSG_WriteByte (&sv.reliable_datagram, client->colors);
	}
}

  
                 
            

                                                            
                 
  
static void VM_SV_effect(prvm_prog_t *prog)
{
	int i;
	const char *s;
	vec3_t org;
	VM_SAFEPARMCOUNT(5, VM_SV_effect);
	s = PRVM_G_STRING(OFS_PARM1);
	if (!s[0])
	{
		VM_Warning(prog, "effect: no model specified\n");
		return;
	}

	i = SV_ModelIndex(s, 1);
	if (!i)
	{
		VM_Warning(prog, "effect: model not precached\n");
		return;
	}

	if (PRVM_G_FLOAT(OFS_PARM3) < 1)
	{
		VM_Warning(prog, "effect: framecount < 1\n");
		return;
	}

	if (PRVM_G_FLOAT(OFS_PARM4) < 1)
	{
		VM_Warning(prog, "effect: framerate < 1\n");
		return;
	}

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), org);
	SV_StartEffect(org, i, (int)PRVM_G_FLOAT(OFS_PARM2), (int)PRVM_G_FLOAT(OFS_PARM3), (int)PRVM_G_FLOAT(OFS_PARM4));
}

static void VM_SV_te_blood(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(3, VM_SV_te_blood);
	if (PRVM_G_FLOAT(OFS_PARM2) < 1)
		return;
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_BLOOD);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	           
	MSG_WriteChar(&sv.datagram, bound(-128, (int) PRVM_G_VECTOR(OFS_PARM1)[0], 127));
	MSG_WriteChar(&sv.datagram, bound(-128, (int) PRVM_G_VECTOR(OFS_PARM1)[1], 127));
	MSG_WriteChar(&sv.datagram, bound(-128, (int) PRVM_G_VECTOR(OFS_PARM1)[2], 127));
	        
	MSG_WriteByte(&sv.datagram, bound(0, (int) PRVM_G_FLOAT(OFS_PARM2), 255));
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_bloodshower(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(4, VM_SV_te_bloodshower);
	if (PRVM_G_FLOAT(OFS_PARM3) < 1)
		return;
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_BLOODSHOWER);
	      
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	      
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[2], sv.protocol);
	        
	MSG_WriteCoord(&sv.datagram, PRVM_G_FLOAT(OFS_PARM2), sv.protocol);
	        
	MSG_WriteShort(&sv.datagram, (int)bound(0, PRVM_G_FLOAT(OFS_PARM3), 65535));
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_explosionrgb(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(2, VM_SV_te_explosionrgb);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_EXPLOSIONRGB);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	        
	MSG_WriteByte(&sv.datagram, bound(0, (int) (PRVM_G_VECTOR(OFS_PARM1)[0] * 255), 255));
	MSG_WriteByte(&sv.datagram, bound(0, (int) (PRVM_G_VECTOR(OFS_PARM1)[1] * 255), 255));
	MSG_WriteByte(&sv.datagram, bound(0, (int) (PRVM_G_VECTOR(OFS_PARM1)[2] * 255), 255));
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_particlecube(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(7, VM_SV_te_particlecube);
	if (PRVM_G_FLOAT(OFS_PARM3) < 1)
		return;
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_PARTICLECUBE);
	      
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	      
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[2], sv.protocol);
	           
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[2], sv.protocol);
	        
	MSG_WriteShort(&sv.datagram, (int)bound(0, PRVM_G_FLOAT(OFS_PARM3), 65535));
	        
	MSG_WriteByte(&sv.datagram, (int)PRVM_G_FLOAT(OFS_PARM4));
	                     
	MSG_WriteByte(&sv.datagram, ((int) PRVM_G_FLOAT(OFS_PARM5)) != 0);
	            
	MSG_WriteCoord(&sv.datagram, PRVM_G_FLOAT(OFS_PARM6), sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_particlerain(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(5, VM_SV_te_particlerain);
	if (PRVM_G_FLOAT(OFS_PARM3) < 1)
		return;
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_PARTICLERAIN);
	      
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	      
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[2], sv.protocol);
	           
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[2], sv.protocol);
	        
	MSG_WriteShort(&sv.datagram, (int)bound(0, PRVM_G_FLOAT(OFS_PARM3), 65535));
	        
	MSG_WriteByte(&sv.datagram, (int)PRVM_G_FLOAT(OFS_PARM4));
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_particlesnow(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(5, VM_SV_te_particlesnow);
	if (PRVM_G_FLOAT(OFS_PARM3) < 1)
		return;
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_PARTICLESNOW);
	      
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	      
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[2], sv.protocol);
	           
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[2], sv.protocol);
	        
	MSG_WriteShort(&sv.datagram, (int)bound(0, PRVM_G_FLOAT(OFS_PARM3), 65535));
	        
	MSG_WriteByte(&sv.datagram, (int)PRVM_G_FLOAT(OFS_PARM4));
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_spark(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(3, VM_SV_te_spark);
	if (PRVM_G_FLOAT(OFS_PARM2) < 1)
		return;
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_SPARK);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	           
	MSG_WriteChar(&sv.datagram, bound(-128, (int) PRVM_G_VECTOR(OFS_PARM1)[0], 127));
	MSG_WriteChar(&sv.datagram, bound(-128, (int) PRVM_G_VECTOR(OFS_PARM1)[1], 127));
	MSG_WriteChar(&sv.datagram, bound(-128, (int) PRVM_G_VECTOR(OFS_PARM1)[2], 127));
	        
	MSG_WriteByte(&sv.datagram, bound(0, (int) PRVM_G_FLOAT(OFS_PARM2), 255));
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_gunshotquad(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_te_gunshotquad);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_GUNSHOTQUAD);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_spikequad(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_te_spikequad);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_SPIKEQUAD);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_superspikequad(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_te_superspikequad);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_SUPERSPIKEQUAD);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_explosionquad(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_te_explosionquad);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_EXPLOSIONQUAD);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_smallflash(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_te_smallflash);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_SMALLFLASH);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_customflash(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(4, VM_SV_te_customflash);
	if (PRVM_G_FLOAT(OFS_PARM1) < 8 || PRVM_G_FLOAT(OFS_PARM2) < (1.0 / 256.0))
		return;
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_CUSTOMFLASH);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	         
	MSG_WriteByte(&sv.datagram, (int)bound(0, PRVM_G_FLOAT(OFS_PARM1) / 8 - 1, 255));
	           
	MSG_WriteByte(&sv.datagram, (int)bound(0, PRVM_G_FLOAT(OFS_PARM2) * 256 - 1, 255));
	        
	MSG_WriteByte(&sv.datagram, (int)bound(0, PRVM_G_VECTOR(OFS_PARM3)[0] * 255, 255));
	MSG_WriteByte(&sv.datagram, (int)bound(0, PRVM_G_VECTOR(OFS_PARM3)[1] * 255, 255));
	MSG_WriteByte(&sv.datagram, (int)bound(0, PRVM_G_VECTOR(OFS_PARM3)[2] * 255, 255));
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_gunshot(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_te_gunshot);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_GUNSHOT);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_spike(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_te_spike);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_SPIKE);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_superspike(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_te_superspike);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_SUPERSPIKE);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_explosion(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_te_explosion);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_EXPLOSION);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_tarexplosion(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_te_tarexplosion);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_TAREXPLOSION);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_wizspike(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_te_wizspike);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_WIZSPIKE);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_knightspike(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_te_knightspike);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_KNIGHTSPIKE);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_lavasplash(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_te_lavasplash);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_LAVASPLASH);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_teleport(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_te_teleport);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_TELEPORT);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_explosion2(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(3, VM_SV_te_explosion2);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_EXPLOSION2);
	         
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	        
	MSG_WriteByte(&sv.datagram, (int)PRVM_G_FLOAT(OFS_PARM1));
	MSG_WriteByte(&sv.datagram, (int)PRVM_G_FLOAT(OFS_PARM2));
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_lightning1(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(3, VM_SV_te_lightning1);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_LIGHTNING1);
	               
	MSG_WriteShort(&sv.datagram, PRVM_G_EDICTNUM(OFS_PARM0));
	        
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[2], sv.protocol);
	      
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_lightning2(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(3, VM_SV_te_lightning2);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_LIGHTNING2);
	               
	MSG_WriteShort(&sv.datagram, PRVM_G_EDICTNUM(OFS_PARM0));
	        
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[2], sv.protocol);
	      
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_lightning3(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(3, VM_SV_te_lightning3);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_LIGHTNING3);
	               
	MSG_WriteShort(&sv.datagram, PRVM_G_EDICTNUM(OFS_PARM0));
	        
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[2], sv.protocol);
	      
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_beam(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(3, VM_SV_te_beam);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_BEAM);
	               
	MSG_WriteShort(&sv.datagram, PRVM_G_EDICTNUM(OFS_PARM0));
	        
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[2], sv.protocol);
	      
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM2)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_plasmaburn(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_SV_te_plasmaburn);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_PLASMABURN);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	SV_FlushBroadcastMessages();
}

static void VM_SV_te_flamejet(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(3, VM_SV_te_flamejet);
	MSG_WriteByte(&sv.datagram, svc_temp_entity);
	MSG_WriteByte(&sv.datagram, TE_FLAMEJET);
	      
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM0)[2], sv.protocol);
	      
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[0], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[1], sv.protocol);
	MSG_WriteCoord(&sv.datagram, PRVM_G_VECTOR(OFS_PARM1)[2], sv.protocol);
	        
	MSG_WriteByte(&sv.datagram, (int)PRVM_G_FLOAT(OFS_PARM2));
	SV_FlushBroadcastMessages();
}

                                                                                                                     
                                                                        
static void VM_SV_clientcommand(prvm_prog_t *prog)
{
	client_t *temp_client;
	int i;
	VM_SAFEPARMCOUNT(2, VM_SV_clientcommand);

	                             
	i = (PRVM_NUM_FOR_EDICT(PRVM_G_EDICT(OFS_PARM0)) - 1);
	if (i < 0 || i >= svs.maxclients || !svs.clients[i].active)
	{
		Con_Print("PF_clientcommand: entity is not a client\n");
		return;
	}

	temp_client = host_client;
	host_client = svs.clients + i;
	Cmd_ExecuteString (PRVM_G_STRING(OFS_PARM1), src_client, true);
	host_client = temp_client;
}

                                                                                                                                                                             
static void VM_SV_setattachment(prvm_prog_t *prog)
{
	prvm_edict_t *e = PRVM_G_EDICT(OFS_PARM0);
	prvm_edict_t *tagentity = PRVM_G_EDICT(OFS_PARM1);
	const char *tagname = PRVM_G_STRING(OFS_PARM2);
	dp_model_t *model;
	int tagindex;
	VM_SAFEPARMCOUNT(3, VM_SV_setattachment);

	if (e == prog->edicts)
	{
		VM_Warning(prog, "setattachment: can not modify world entity\n");
		return;
	}
	if (e->priv.server->free)
	{
		VM_Warning(prog, "setattachment: can not modify free entity\n");
		return;
	}

	if (tagentity == NULL)
		tagentity = prog->edicts;

	tagindex = 0;

	if (tagentity != NULL && tagentity != prog->edicts && tagname && tagname[0])
	{
		model = SV_GetModelFromEdict(tagentity);
		if (model)
		{
			tagindex = Mod_Alias_GetTagIndexForName(model, (int)PRVM_serveredictfloat(tagentity, skin), tagname);
			if (tagindex == 0)
				Con_DPrintf("setattachment(edict %i, edict %i, string \"%s\"): tried to find tag named \"%s\" on entity %i (model \"%s\") but could not find it\n", PRVM_NUM_FOR_EDICT(e), PRVM_NUM_FOR_EDICT(tagentity), tagname, tagname, PRVM_NUM_FOR_EDICT(tagentity), model->name);
		}
		else
			Con_DPrintf("setattachment(edict %i, edict %i, string \"%s\"): tried to find tag named \"%s\" on entity %i but it has no model\n", PRVM_NUM_FOR_EDICT(e), PRVM_NUM_FOR_EDICT(tagentity), tagname, tagname, PRVM_NUM_FOR_EDICT(tagentity));
	}

	PRVM_serveredictedict(e, tag_entity) = PRVM_EDICT_TO_PROG(tagentity);
	PRVM_serveredictfloat(e, tag_index) = tagindex;
}

                                         
                                           

static int SV_GetTagIndex (prvm_prog_t *prog, prvm_edict_t *e, const char *tagname)
{
	int i;

	i = (int)PRVM_serveredictfloat(e, modelindex);
	if (i < 1 || i >= MAX_MODELS)
		return -1;

	return Mod_Alias_GetTagIndexForName(SV_GetModelByIndex(i), (int)PRVM_serveredictfloat(e, skin), tagname);
}

static int SV_GetExtendedTagInfo (prvm_prog_t *prog, prvm_edict_t *e, int tagindex, int *parentindex, const char **tagname, matrix4x4_t *tag_localmatrix)
{
	int r;
	dp_model_t *model;

	*tagname = NULL;
	*parentindex = 0;
	Matrix4x4_CreateIdentity(tag_localmatrix);

	if (tagindex >= 0 && (model = SV_GetModelFromEdict(e)) && model->num_bones)
	{
		r = Mod_Alias_GetExtendedTagInfoForIndex(model, (int)PRVM_serveredictfloat(e, skin), e->priv.server->frameblend, &e->priv.server->skeleton, tagindex - 1, parentindex, tagname, tag_localmatrix);

		if(!r)            
			*parentindex += 1;

		return r;
	}

	return 1;
}

void SV_GetEntityMatrix (prvm_prog_t *prog, prvm_edict_t *ent, matrix4x4_t *out, qboolean viewmatrix)
{
	float scale;
	float pitchsign = 1;

	scale = PRVM_serveredictfloat(ent, scale);
	if (!scale)
		scale = 1.0f;
	
	if (viewmatrix)
		Matrix4x4_CreateFromQuakeEntity(out, PRVM_serveredictvector(ent, origin)[0], PRVM_serveredictvector(ent, origin)[1], PRVM_serveredictvector(ent, origin)[2] + PRVM_serveredictvector(ent, view_ofs)[2], PRVM_serveredictvector(ent, v_angle)[0], PRVM_serveredictvector(ent, v_angle)[1], PRVM_serveredictvector(ent, v_angle)[2], scale * cl_viewmodel_scale.value);
	else
	{
		pitchsign = SV_GetPitchSign(prog, ent);
		Matrix4x4_CreateFromQuakeEntity(out, PRVM_serveredictvector(ent, origin)[0], PRVM_serveredictvector(ent, origin)[1], PRVM_serveredictvector(ent, origin)[2], pitchsign * PRVM_serveredictvector(ent, angles)[0], PRVM_serveredictvector(ent, angles)[1], PRVM_serveredictvector(ent, angles)[2], scale);
	}
}

static int SV_GetEntityLocalTagMatrix(prvm_prog_t *prog, prvm_edict_t *ent, int tagindex, matrix4x4_t *out)
{
	dp_model_t *model;
	if (tagindex >= 0 && (model = SV_GetModelFromEdict(ent)) && model->animscenes)
	{
		VM_GenerateFrameGroupBlend(prog, ent->priv.server->framegroupblend, ent);
		VM_FrameBlendFromFrameGroupBlend(ent->priv.server->frameblend, ent->priv.server->framegroupblend, model, sv.time);
		VM_UpdateEdictSkeleton(prog, ent, model, ent->priv.server->frameblend);
		return Mod_Alias_GetTagMatrix(model, ent->priv.server->frameblend, &ent->priv.server->skeleton, tagindex, out);
	}
	*out = identitymatrix;
	return 0;
}

                        
                                    
                   
                  
                                  
                                   
                                       
extern cvar_t cl_bob;
extern cvar_t cl_bobcycle;
extern cvar_t cl_bobup;
static int SV_GetTagMatrix (prvm_prog_t *prog, matrix4x4_t *out, prvm_edict_t *ent, int tagindex)
{
	int ret;
	int modelindex, attachloop;
	matrix4x4_t entitymatrix, tagmatrix, attachmatrix;
	dp_model_t *model;

	*out = identitymatrix;                                               

	if (ent == prog->edicts)
		return 1;
	if (ent->priv.server->free)
		return 2;

	modelindex = (int)PRVM_serveredictfloat(ent, modelindex);
	if (modelindex <= 0 || modelindex >= MAX_MODELS)
		return 3;

	model = SV_GetModelByIndex(modelindex);

	VM_GenerateFrameGroupBlend(prog, ent->priv.server->framegroupblend, ent);
	VM_FrameBlendFromFrameGroupBlend(ent->priv.server->frameblend, ent->priv.server->framegroupblend, model, sv.time);
	VM_UpdateEdictSkeleton(prog, ent, model, ent->priv.server->frameblend);

	tagmatrix = identitymatrix;
	                                                                       
	attachloop = 0;
	for (;;)
	{
		if (attachloop >= 256)                           
			return 5;
		                                                                     
		                          
		ret = SV_GetEntityLocalTagMatrix(prog, ent, tagindex - 1, &attachmatrix);
		if (ret && attachloop == 0)
			return ret;
		SV_GetEntityMatrix(prog, ent, &entitymatrix, false);
		Matrix4x4_Concat(&tagmatrix, &attachmatrix, out);
		Matrix4x4_Concat(out, &entitymatrix, &tagmatrix);
		                                              
		if (PRVM_serveredictedict(ent, tag_entity))
		{
			tagindex = (int)PRVM_serveredictfloat(ent, tag_index);
			ent = PRVM_EDICT_NUM(PRVM_serveredictedict(ent, tag_entity));
		}
		else
			break;
		attachloop++;
	}

	                         
	if (PRVM_serveredictedict(ent, viewmodelforclient))
	{
		Matrix4x4_Copy(&tagmatrix, out);
		ent = PRVM_EDICT_NUM(PRVM_serveredictedict(ent, viewmodelforclient));

		SV_GetEntityMatrix(prog, ent, &entitymatrix, true);
		Matrix4x4_Concat(out, &entitymatrix, &tagmatrix);

		  
                                       
                                                                                  
   
                     
                                                                     
                                                                      
                                                                       
                                                                        
                                     
                       
                              
                                               
       
                                                                             
                                                     
                                              
                                                                                                                                                                                                  
                                 
                                                        
   
    
	}
	return 0;
}

                                                

static void VM_SV_gettagindex(prvm_prog_t *prog)
{
	prvm_edict_t *ent;
	const char *tag_name;
	int tag_index;

	VM_SAFEPARMCOUNT(2, VM_SV_gettagindex);

	ent = PRVM_G_EDICT(OFS_PARM0);
	tag_name = PRVM_G_STRING(OFS_PARM1);

	if (ent == prog->edicts)
	{
		VM_Warning(prog, "VM_SV_gettagindex(entity #%i): can't affect world entity\n", PRVM_NUM_FOR_EDICT(ent));
		return;
	}
	if (ent->priv.server->free)
	{
		VM_Warning(prog, "VM_SV_gettagindex(entity #%i): can't affect free entity\n", PRVM_NUM_FOR_EDICT(ent));
		return;
	}

	tag_index = 0;
	if (!SV_GetModelFromEdict(ent))
		Con_DPrintf("VM_SV_gettagindex(entity #%i): null or non-precached model\n", PRVM_NUM_FOR_EDICT(ent));
	else
	{
		tag_index = SV_GetTagIndex(prog, ent, tag_name);
		if (tag_index == 0)
			if(developer_extra.integer)
				Con_DPrintf("VM_SV_gettagindex(entity #%i): tag \"%s\" not found\n", PRVM_NUM_FOR_EDICT(ent), tag_name);
	}
	PRVM_G_FLOAT(OFS_RETURN) = tag_index;
}

                                                
static void VM_SV_gettaginfo(prvm_prog_t *prog)
{
	prvm_edict_t *e;
	int tagindex;
	matrix4x4_t tag_matrix;
	matrix4x4_t tag_localmatrix;
	int parentindex;
	const char *tagname;
	int returncode;
	vec3_t forward, left, up, origin;
	const dp_model_t *model;

	VM_SAFEPARMCOUNT(2, VM_SV_gettaginfo);

	e = PRVM_G_EDICT(OFS_PARM0);
	tagindex = (int)PRVM_G_FLOAT(OFS_PARM1);

	returncode = SV_GetTagMatrix(prog, &tag_matrix, e, tagindex);
	Matrix4x4_ToVectors(&tag_matrix, forward, left, up, origin);
	VectorCopy(forward, PRVM_serverglobalvector(v_forward));
	VectorNegate(left, PRVM_serverglobalvector(v_right));
	VectorCopy(up, PRVM_serverglobalvector(v_up));
	VectorCopy(origin, PRVM_G_VECTOR(OFS_RETURN));
	model = SV_GetModelFromEdict(e);
	VM_GenerateFrameGroupBlend(prog, e->priv.server->framegroupblend, e);
	VM_FrameBlendFromFrameGroupBlend(e->priv.server->frameblend, e->priv.server->framegroupblend, model, sv.time);
	VM_UpdateEdictSkeleton(prog, e, model, e->priv.server->frameblend);
	SV_GetExtendedTagInfo(prog, e, tagindex, &parentindex, &tagname, &tag_localmatrix);
	Matrix4x4_ToVectors(&tag_localmatrix, forward, left, up, origin);

	PRVM_serverglobalfloat(gettaginfo_parent) = parentindex;
	PRVM_serverglobalstring(gettaginfo_name) = tagname ? PRVM_SetTempString(prog, tagname) : 0;
	VectorCopy(forward, PRVM_serverglobalvector(gettaginfo_forward));
	VectorNegate(left, PRVM_serverglobalvector(gettaginfo_right));
	VectorCopy(up, PRVM_serverglobalvector(gettaginfo_up));
	VectorCopy(origin, PRVM_serverglobalvector(gettaginfo_offset));

	switch(returncode)
	{
		case 1:
			VM_Warning(prog, "gettagindex: can't affect world entity\n");
			break;
		case 2:
			VM_Warning(prog, "gettagindex: can't affect free entity\n");
			break;
		case 3:
			Con_DPrintf("SV_GetTagMatrix(entity #%i): null or non-precached model\n", PRVM_NUM_FOR_EDICT(e));
			break;
		case 4:
			Con_DPrintf("SV_GetTagMatrix(entity #%i): model has no tag with requested index %i\n", PRVM_NUM_FOR_EDICT(e), tagindex);
			break;
		case 5:
			Con_DPrintf("SV_GetTagMatrix(entity #%i): runaway loop at attachment chain\n", PRVM_NUM_FOR_EDICT(e));
			break;
	}
}

                                                  
static void VM_SV_dropclient(prvm_prog_t *prog)
{
	int clientnum;
	client_t *oldhostclient;
	VM_SAFEPARMCOUNT(1, VM_SV_dropclient);
	clientnum = PRVM_G_EDICTNUM(OFS_PARM0) - 1;
	if (clientnum < 0 || clientnum >= svs.maxclients)
	{
		VM_Warning(prog, "dropclient: not a client\n");
		return;
	}
	if (!svs.clients[clientnum].active)
	{
		VM_Warning(prog, "dropclient: that client slot is not connected\n");
		return;
	}
	oldhostclient = host_client;
	host_client = svs.clients + clientnum;
	SV_DropClient(false);
	host_client = oldhostclient;
}

                                        
static void VM_SV_spawnclient(prvm_prog_t *prog)
{
	int i;
	prvm_edict_t	*ed;
	VM_SAFEPARMCOUNT(0, VM_SV_spawnclient);
	prog->xfunction->builtinsprofile += 2;
	ed = prog->edicts;
	for (i = 0;i < svs.maxclients;i++)
	{
		if (!svs.clients[i].active)
		{
			prog->xfunction->builtinsprofile += 100;
			SV_ConnectClient (i, NULL);
			                                                              
			                                              
			svs.clients[i].clientconnectcalled = true;
			ed = PRVM_EDICT_NUM(i + 1);
			break;
		}
	}
	VM_RETURN_EDICT(ed);
}

                                                  
static void VM_SV_clienttype(prvm_prog_t *prog)
{
	int clientnum;
	VM_SAFEPARMCOUNT(1, VM_SV_clienttype);
	clientnum = PRVM_G_EDICTNUM(OFS_PARM0) - 1;
	if (clientnum < 0 || clientnum >= svs.maxclients)
		PRVM_G_FLOAT(OFS_RETURN) = 3;
	else if (!svs.clients[clientnum].active)
		PRVM_G_FLOAT(OFS_RETURN) = 0;
	else if (svs.clients[clientnum].netconnection)
		PRVM_G_FLOAT(OFS_RETURN) = 1;
	else
		PRVM_G_FLOAT(OFS_RETURN) = 2;
}

  
               
               

                            
               
  
static void VM_SV_serverkey(prvm_prog_t *prog)
{
	char string[VM_STRINGTEMP_LENGTH];
	VM_SAFEPARMCOUNT(1, VM_SV_serverkey);
	InfoString_GetValue(svs.serverinfo, PRVM_G_STRING(OFS_PARM0), string, sizeof(string));
	PRVM_G_INT(OFS_RETURN) = PRVM_SetTempString(prog, string);
}

                                                              
static void VM_SV_setmodelindex(prvm_prog_t *prog)
{
	prvm_edict_t	*e;
	dp_model_t	*mod;
	int		i;
	VM_SAFEPARMCOUNT(2, VM_SV_setmodelindex);

	e = PRVM_G_EDICT(OFS_PARM0);
	if (e == prog->edicts)
	{
		VM_Warning(prog, "setmodelindex: can not modify world entity\n");
		return;
	}
	if (e->priv.server->free)
	{
		VM_Warning(prog, "setmodelindex: can not modify free entity\n");
		return;
	}
	i = (int)PRVM_G_FLOAT(OFS_PARM1);
	if (i <= 0 || i >= MAX_MODELS)
	{
		VM_Warning(prog, "setmodelindex: invalid modelindex\n");
		return;
	}
	if (!sv.model_precache[i][0])
	{
		VM_Warning(prog, "setmodelindex: model not precached\n");
		return;
	}

	PRVM_serveredictstring(e, model) = PRVM_SetEngineString(prog, sv.model_precache[i]);
	PRVM_serveredictfloat(e, modelindex) = i;

	mod = SV_GetModelByIndex(i);

	if (mod)
	{
		if (mod->type != mod_alias || sv_gameplayfix_setmodelrealbox.integer)
			SetMinMaxSize(prog, e, mod->normalmins, mod->normalmaxs, true);
		else
			SetMinMaxSize(prog, e, quakemins, quakemaxs, true);
	}
	else
		SetMinMaxSize(prog, e, vec3_origin, vec3_origin, true);
}

                                                          
static void VM_SV_modelnameforindex(prvm_prog_t *prog)
{
	int i;
	VM_SAFEPARMCOUNT(1, VM_SV_modelnameforindex);

	PRVM_G_INT(OFS_RETURN) = OFS_NULL;

	i = (int)PRVM_G_FLOAT(OFS_PARM0);
	if (i <= 0 || i >= MAX_MODELS)
	{
		VM_Warning(prog, "modelnameforindex: invalid modelindex\n");
		return;
	}
	if (!sv.model_precache[i][0])
	{
		VM_Warning(prog, "modelnameforindex: model not precached\n");
		return;
	}

	PRVM_G_INT(OFS_RETURN) = PRVM_SetEngineString(prog, sv.model_precache[i]);
}

                                                            
static void VM_SV_particleeffectnum(prvm_prog_t *prog)
{
	int			i;
	VM_SAFEPARMCOUNT(1, VM_SV_particleeffectnum);
	i = SV_ParticleEffectIndex(PRVM_G_STRING(OFS_PARM0));
	if (i == 0)
		i = -1;
	PRVM_G_FLOAT(OFS_RETURN) = i;
}

                                                                                             
static void VM_SV_trailparticles(prvm_prog_t *prog)
{
	vec3_t start, end;
	VM_SAFEPARMCOUNT(4, VM_SV_trailparticles);

	if ((int)PRVM_G_FLOAT(OFS_PARM0) < 0)
		return;

	MSG_WriteByte(&sv.datagram, svc_trailparticles);
	MSG_WriteShort(&sv.datagram, PRVM_G_EDICTNUM(OFS_PARM0));
	MSG_WriteShort(&sv.datagram, (int)PRVM_G_FLOAT(OFS_PARM1));
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), start);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM3), end);
	MSG_WriteVector(&sv.datagram, start, sv.protocol);
	MSG_WriteVector(&sv.datagram, end, sv.protocol);
	SV_FlushBroadcastMessages();
}

                                                                                              
static void VM_SV_pointparticles(prvm_prog_t *prog)
{
	int effectnum, count;
	vec3_t org, vel;
	VM_SAFEPARMCOUNTRANGE(4, 8, VM_SV_pointparticles);

	if ((int)PRVM_G_FLOAT(OFS_PARM0) < 0)
		return;

	effectnum = (int)PRVM_G_FLOAT(OFS_PARM0);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), org);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), vel);
	count = bound(0, (int)PRVM_G_FLOAT(OFS_PARM3), 65535);
	if (count == 1 && !VectorLength2(vel))
	{
		                  
		MSG_WriteByte(&sv.datagram, svc_pointparticles1);
		MSG_WriteShort(&sv.datagram, effectnum);
		MSG_WriteVector(&sv.datagram, org, sv.protocol);
	}
	else
	{
		                       
		MSG_WriteByte(&sv.datagram, svc_pointparticles);
		MSG_WriteShort(&sv.datagram, effectnum);
		MSG_WriteVector(&sv.datagram, org, sv.protocol);
		MSG_WriteVector(&sv.datagram, vel, sv.protocol);
		MSG_WriteShort(&sv.datagram, count);
	}

	SV_FlushBroadcastMessages();
}

                                                       
static void VM_SV_setpause(prvm_prog_t *prog) {
	int pauseValue;
	pauseValue = (int)PRVM_G_FLOAT(OFS_PARM0);
	if (pauseValue != 0) {                 
		sv.paused = 1;
		sv.pausedstart = realtime;
	} else {                                        
		if (sv.paused != 0) {
			sv.paused = 0;
			sv.pausedstart = 0;
		}
	}
	                                   
	MSG_WriteByte(&sv.reliable_datagram, svc_setpause);
	MSG_WriteByte(&sv.reliable_datagram, sv.paused);
}

                                                                                                                                                                                                                                                                                                                                                                 
static void VM_SV_skel_create(prvm_prog_t *prog)
{
	int modelindex = (int)PRVM_G_FLOAT(OFS_PARM0);
	dp_model_t *model = SV_GetModelByIndex(modelindex);
	skeleton_t *skeleton;
	int i;
	PRVM_G_FLOAT(OFS_RETURN) = 0;
	if (!model || !model->num_bones)
		return;
	for (i = 0;i < MAX_EDICTS;i++)
		if (!prog->skeletons[i])
			break;
	if (i == MAX_EDICTS)
		return;
	prog->skeletons[i] = skeleton = (skeleton_t *)Mem_Alloc(prog->progs_mempool, sizeof(skeleton_t) + model->num_bones * sizeof(matrix4x4_t));
	PRVM_G_FLOAT(OFS_RETURN) = i + 1;
	skeleton->model = model;
	skeleton->relativetransforms = (matrix4x4_t *)(skeleton+1);
	                                  
	for (i = 0;i < skeleton->model->num_bones;i++)
		skeleton->relativetransforms[i] = identitymatrix;
}

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     
static void VM_SV_skel_build(prvm_prog_t *prog)
{
	int skeletonindex = (int)PRVM_G_FLOAT(OFS_PARM0) - 1;
	skeleton_t *skeleton;
	prvm_edict_t *ed = PRVM_G_EDICT(OFS_PARM1);
	int modelindex = (int)PRVM_G_FLOAT(OFS_PARM2);
	float retainfrac = PRVM_G_FLOAT(OFS_PARM3);
	int firstbone = PRVM_G_FLOAT(OFS_PARM4) - 1;
	int lastbone = PRVM_G_FLOAT(OFS_PARM5) - 1;
	dp_model_t *model = SV_GetModelByIndex(modelindex);
	int numblends;
	int bonenum;
	int blendindex;
	framegroupblend_t framegroupblend[MAX_FRAMEGROUPBLENDS];
	frameblend_t frameblend[MAX_FRAMEBLENDS];
	matrix4x4_t bonematrix;
	matrix4x4_t matrix;
	PRVM_G_FLOAT(OFS_RETURN) = 0;
	if (skeletonindex < 0 || skeletonindex >= MAX_EDICTS || !(skeleton = prog->skeletons[skeletonindex]))
		return;
	firstbone = max(0, firstbone);
	lastbone = min(lastbone, model->num_bones - 1);
	lastbone = min(lastbone, skeleton->model->num_bones - 1);
	VM_GenerateFrameGroupBlend(prog, framegroupblend, ed);
	VM_FrameBlendFromFrameGroupBlend(frameblend, framegroupblend, model, sv.time);
	for (numblends = 0;numblends < MAX_FRAMEBLENDS && frameblend[numblends].lerp;numblends++)
		;
	for (bonenum = firstbone;bonenum <= lastbone;bonenum++)
	{
		memset(&bonematrix, 0, sizeof(bonematrix));
		for (blendindex = 0;blendindex < numblends;blendindex++)
		{
			Matrix4x4_FromBonePose7s(&matrix, model->num_posescale, model->data_poses7s + 7 * (frameblend[blendindex].subframe * model->num_bones + bonenum));
			Matrix4x4_Accumulate(&bonematrix, &matrix, frameblend[blendindex].lerp);
		}
		Matrix4x4_Normalize3(&bonematrix, &bonematrix);
		Matrix4x4_Interpolate(&skeleton->relativetransforms[bonenum], &bonematrix, &skeleton->relativetransforms[bonenum], retainfrac);
	}
	PRVM_G_FLOAT(OFS_RETURN) = skeletonindex + 1;
}

                                                                                                                                      
static void VM_SV_skel_get_numbones(prvm_prog_t *prog)
{
	int skeletonindex = (int)PRVM_G_FLOAT(OFS_PARM0) - 1;
	skeleton_t *skeleton;
	PRVM_G_FLOAT(OFS_RETURN) = 0;
	if (skeletonindex < 0 || skeletonindex >= MAX_EDICTS || !(skeleton = prog->skeletons[skeletonindex]))
		return;
	PRVM_G_FLOAT(OFS_RETURN) = skeleton->model->num_bones;
}

                                                                                                                                        
static void VM_SV_skel_get_bonename(prvm_prog_t *prog)
{
	int skeletonindex = (int)PRVM_G_FLOAT(OFS_PARM0) - 1;
	int bonenum = (int)PRVM_G_FLOAT(OFS_PARM1) - 1;
	skeleton_t *skeleton;
	PRVM_G_INT(OFS_RETURN) = 0;
	if (skeletonindex < 0 || skeletonindex >= MAX_EDICTS || !(skeleton = prog->skeletons[skeletonindex]))
		return;
	if (bonenum < 0 || bonenum >= skeleton->model->num_bones)
		return;
	PRVM_G_INT(OFS_RETURN) = PRVM_SetTempString(prog, skeleton->model->data_bones[bonenum].name);
}

                                                                                                                                                                                                                                                                
static void VM_SV_skel_get_boneparent(prvm_prog_t *prog)
{
	int skeletonindex = (int)PRVM_G_FLOAT(OFS_PARM0) - 1;
	int bonenum = (int)PRVM_G_FLOAT(OFS_PARM1) - 1;
	skeleton_t *skeleton;
	PRVM_G_FLOAT(OFS_RETURN) = 0;
	if (skeletonindex < 0 || skeletonindex >= MAX_EDICTS || !(skeleton = prog->skeletons[skeletonindex]))
		return;
	if (bonenum < 0 || bonenum >= skeleton->model->num_bones)
		return;
	PRVM_G_FLOAT(OFS_RETURN) = skeleton->model->data_bones[bonenum].parent + 1;
}

                                                                                                                                                                                                                                 
static void VM_SV_skel_find_bone(prvm_prog_t *prog)
{
	int skeletonindex = (int)PRVM_G_FLOAT(OFS_PARM0) - 1;
	const char *tagname = PRVM_G_STRING(OFS_PARM1);
	skeleton_t *skeleton;
	PRVM_G_FLOAT(OFS_RETURN) = 0;
	if (skeletonindex < 0 || skeletonindex >= MAX_EDICTS || !(skeleton = prog->skeletons[skeletonindex]))
		return;
	PRVM_G_FLOAT(OFS_RETURN) = Mod_Alias_GetTagIndexForName(skeleton->model, 0, tagname) + 1;
}

                                                                                                                                                                                                                                
static void VM_SV_skel_get_bonerel(prvm_prog_t *prog)
{
	int skeletonindex = (int)PRVM_G_FLOAT(OFS_PARM0) - 1;
	int bonenum = (int)PRVM_G_FLOAT(OFS_PARM1) - 1;
	skeleton_t *skeleton;
	matrix4x4_t matrix;
	vec3_t forward, left, up, origin;
	VectorClear(PRVM_G_VECTOR(OFS_RETURN));
	VectorClear(PRVM_clientglobalvector(v_forward));
	VectorClear(PRVM_clientglobalvector(v_right));
	VectorClear(PRVM_clientglobalvector(v_up));
	if (skeletonindex < 0 || skeletonindex >= MAX_EDICTS || !(skeleton = prog->skeletons[skeletonindex]))
		return;
	if (bonenum < 0 || bonenum >= skeleton->model->num_bones)
		return;
	matrix = skeleton->relativetransforms[bonenum];
	Matrix4x4_ToVectors(&matrix, forward, left, up, origin);
	VectorCopy(forward, PRVM_clientglobalvector(v_forward));
	VectorNegate(left, PRVM_clientglobalvector(v_right));
	VectorCopy(up, PRVM_clientglobalvector(v_up));
	VectorCopy(origin, PRVM_G_VECTOR(OFS_RETURN));
}

                                                                                                                                                                                                                   
static void VM_SV_skel_get_boneabs(prvm_prog_t *prog)
{
	int skeletonindex = (int)PRVM_G_FLOAT(OFS_PARM0) - 1;
	int bonenum = (int)PRVM_G_FLOAT(OFS_PARM1) - 1;
	skeleton_t *skeleton;
	matrix4x4_t matrix;
	matrix4x4_t temp;
	vec3_t forward, left, up, origin;
	VectorClear(PRVM_G_VECTOR(OFS_RETURN));
	VectorClear(PRVM_clientglobalvector(v_forward));
	VectorClear(PRVM_clientglobalvector(v_right));
	VectorClear(PRVM_clientglobalvector(v_up));
	if (skeletonindex < 0 || skeletonindex >= MAX_EDICTS || !(skeleton = prog->skeletons[skeletonindex]))
		return;
	if (bonenum < 0 || bonenum >= skeleton->model->num_bones)
		return;
	matrix = skeleton->relativetransforms[bonenum];
	                      
	while ((bonenum = skeleton->model->data_bones[bonenum].parent) >= 0)
	{
		temp = matrix;
		Matrix4x4_Concat(&matrix, &skeleton->relativetransforms[bonenum], &temp);
	}
	Matrix4x4_ToVectors(&matrix, forward, left, up, origin);
	VectorCopy(forward, PRVM_clientglobalvector(v_forward));
	VectorNegate(left, PRVM_clientglobalvector(v_right));
	VectorCopy(up, PRVM_clientglobalvector(v_up));
	VectorCopy(origin, PRVM_G_VECTOR(OFS_RETURN));
}

                                                                                                                                                                                                                                      
static void VM_SV_skel_set_bone(prvm_prog_t *prog)
{
	int skeletonindex = (int)PRVM_G_FLOAT(OFS_PARM0) - 1;
	int bonenum = (int)PRVM_G_FLOAT(OFS_PARM1) - 1;
	vec3_t forward, left, up, origin;
	skeleton_t *skeleton;
	matrix4x4_t matrix;
	if (skeletonindex < 0 || skeletonindex >= MAX_EDICTS || !(skeleton = prog->skeletons[skeletonindex]))
		return;
	if (bonenum < 0 || bonenum >= skeleton->model->num_bones)
		return;
	VectorCopy(PRVM_clientglobalvector(v_forward), forward);
	VectorNegate(PRVM_clientglobalvector(v_right), left);
	VectorCopy(PRVM_clientglobalvector(v_up), up);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), origin);
	Matrix4x4_FromVectors(&matrix, forward, left, up, origin);
	skeleton->relativetransforms[bonenum] = matrix;
}

                                                                                                                                                                                                                                                              
static void VM_SV_skel_mul_bone(prvm_prog_t *prog)
{
	int skeletonindex = (int)PRVM_G_FLOAT(OFS_PARM0) - 1;
	int bonenum = (int)PRVM_G_FLOAT(OFS_PARM1) - 1;
	vec3_t forward, left, up, origin;
	skeleton_t *skeleton;
	matrix4x4_t matrix;
	matrix4x4_t temp;
	if (skeletonindex < 0 || skeletonindex >= MAX_EDICTS || !(skeleton = prog->skeletons[skeletonindex]))
		return;
	if (bonenum < 0 || bonenum >= skeleton->model->num_bones)
		return;
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), origin);
	VectorCopy(PRVM_clientglobalvector(v_forward), forward);
	VectorNegate(PRVM_clientglobalvector(v_right), left);
	VectorCopy(PRVM_clientglobalvector(v_up), up);
	Matrix4x4_FromVectors(&matrix, forward, left, up, origin);
	temp = skeleton->relativetransforms[bonenum];
	Matrix4x4_Concat(&skeleton->relativetransforms[bonenum], &matrix, &temp);
}

                                                                                                                                                                                                                                                                                      
static void VM_SV_skel_mul_bones(prvm_prog_t *prog)
{
	int skeletonindex = (int)PRVM_G_FLOAT(OFS_PARM0) - 1;
	int firstbone = PRVM_G_FLOAT(OFS_PARM1) - 1;
	int lastbone = PRVM_G_FLOAT(OFS_PARM2) - 1;
	int bonenum;
	vec3_t forward, left, up, origin;
	skeleton_t *skeleton;
	matrix4x4_t matrix;
	matrix4x4_t temp;
	if (skeletonindex < 0 || skeletonindex >= MAX_EDICTS || !(skeleton = prog->skeletons[skeletonindex]))
		return;
	VectorCopy(PRVM_G_VECTOR(OFS_PARM3), origin);
	VectorCopy(PRVM_clientglobalvector(v_forward), forward);
	VectorNegate(PRVM_clientglobalvector(v_right), left);
	VectorCopy(PRVM_clientglobalvector(v_up), up);
	Matrix4x4_FromVectors(&matrix, forward, left, up, origin);
	firstbone = max(0, firstbone);
	lastbone = min(lastbone, skeleton->model->num_bones - 1);
	for (bonenum = firstbone;bonenum <= lastbone;bonenum++)
	{
		temp = skeleton->relativetransforms[bonenum];
		Matrix4x4_Concat(&skeleton->relativetransforms[bonenum], &matrix, &temp);
	}
}

                                                                                                                                                                                                                                                      
static void VM_SV_skel_copybones(prvm_prog_t *prog)
{
	int skeletonindexdst = (int)PRVM_G_FLOAT(OFS_PARM0) - 1;
	int skeletonindexsrc = (int)PRVM_G_FLOAT(OFS_PARM1) - 1;
	int firstbone = PRVM_G_FLOAT(OFS_PARM2) - 1;
	int lastbone = PRVM_G_FLOAT(OFS_PARM3) - 1;
	int bonenum;
	skeleton_t *skeletondst;
	skeleton_t *skeletonsrc;
	if (skeletonindexdst < 0 || skeletonindexdst >= MAX_EDICTS || !(skeletondst = prog->skeletons[skeletonindexdst]))
		return;
	if (skeletonindexsrc < 0 || skeletonindexsrc >= MAX_EDICTS || !(skeletonsrc = prog->skeletons[skeletonindexsrc]))
		return;
	firstbone = max(0, firstbone);
	lastbone = min(lastbone, skeletondst->model->num_bones - 1);
	lastbone = min(lastbone, skeletonsrc->model->num_bones - 1);
	for (bonenum = firstbone;bonenum <= lastbone;bonenum++)
		skeletondst->relativetransforms[bonenum] = skeletonsrc->relativetransforms[bonenum];
}

                                                                                                                                                                                                                 
static void VM_SV_skel_delete(prvm_prog_t *prog)
{
	int skeletonindex = (int)PRVM_G_FLOAT(OFS_PARM0) - 1;
	skeleton_t *skeleton;
	if (skeletonindex < 0 || skeletonindex >= MAX_EDICTS || !(skeleton = prog->skeletons[skeletonindex]))
		return;
	Mem_Free(skeleton);
	prog->skeletons[skeletonindex] = NULL;
}

                                                                                                                                                                                    
static void VM_SV_frameforname(prvm_prog_t *prog)
{
	int modelindex = (int)PRVM_G_FLOAT(OFS_PARM0);
	dp_model_t *model = SV_GetModelByIndex(modelindex);
	const char *name = PRVM_G_STRING(OFS_PARM1);
	int i;
	PRVM_G_FLOAT(OFS_RETURN) = -1;
	if (!model || !model->animscenes)
		return;
	for (i = 0;i < model->numframes;i++)
	{
		if (!strcasecmp(model->animscenes[i].name, name))
		{
			PRVM_G_FLOAT(OFS_RETURN) = i;
			break;
		}
	}
}

                                                                                                                                                                                                                                                                                  
static void VM_SV_frameduration(prvm_prog_t *prog)
{
	int modelindex = (int)PRVM_G_FLOAT(OFS_PARM0);
	dp_model_t *model = SV_GetModelByIndex(modelindex);
	int framenum = (int)PRVM_G_FLOAT(OFS_PARM1);
	PRVM_G_FLOAT(OFS_RETURN) = 0;
	if (!model || !model->animscenes || framenum < 0 || framenum >= model->numframes)
		return;
	if (model->animscenes[framenum].framerate)
		PRVM_G_FLOAT(OFS_RETURN) = model->animscenes[framenum].framecount / model->animscenes[framenum].framerate;
}


prvm_builtin_t vm_sv_builtins[] = {
NULL,							                                          
VM_makevectors,					                                          
VM_SV_setorigin,				                                                
VM_SV_setmodel,					                                               
VM_SV_setsize,					                                                            
NULL,							                                                               
VM_break,						                          
VM_random,						                            
VM_SV_sound,					                                                           
VM_normalize,					                                        
VM_error,						                                   
VM_objerror,					                                      
VM_vlen,						                                   
VM_vectoyaw,					                                       
VM_spawn,						                             
VM_remove,						                                    
VM_SV_traceline,				                                                                  
VM_SV_checkclient,				                                   
VM_find,						                                                                   
VM_SV_precache_sound,			                                            
VM_SV_precache_model,			                                            
VM_SV_stuffcmd,					                                                          
VM_SV_findradius,				                                                       
VM_bprint,						                                         
VM_SV_sprint,					                                                        
VM_dprint,						                                         
VM_ftos,						                                   
VM_vtos,						                                    
VM_coredump,					                              
VM_traceon,						                             
VM_traceoff,					                              
VM_eprint,						                                    
VM_SV_walkmove,					                                                    
NULL,							              
VM_SV_droptofloor,				                                  
VM_SV_lightstyle,				                                                         
VM_rint,						                                  
VM_floor,						                                   
VM_ceil,						                                  
NULL,							              
VM_SV_checkbottom,				                                          
VM_SV_pointcontents,			                                            
NULL,							              
VM_fabs,						                                  
VM_SV_aim,						                                                
VM_cvar,						                                   
VM_localcmd,					                                      
VM_nextent,						                                       
VM_SV_particle,					                                                                          
VM_changeyaw,					                               
NULL,							              
VM_vectoangles,					                                           
VM_SV_WriteByte,				                                                
VM_SV_WriteChar,				                                                
VM_SV_WriteShort,				                                                 
VM_SV_WriteLong,				                                                
VM_SV_WriteCoord,				                                                 
VM_SV_WriteAngle,				                                                 
VM_SV_WriteString,				                                                   
VM_SV_WriteEntity,				                                                   
VM_sin,							                                                       
VM_cos,							                                                       
VM_sqrt,						                                                        
VM_changepitch,					                                                               
VM_SV_tracetoss,				                                                                        
VM_etos,						                                                   
NULL,							              
VM_SV_MoveToGoal,				                                          
VM_precache_file,				                                             
VM_SV_makestatic,				                                        
VM_changelevel,					                                         
NULL,							              
VM_cvar_set,					                                                    
VM_SV_centerprint,				                                                       
VM_SV_ambientsound,				                                                                                 
VM_SV_precache_model,			                                               
VM_SV_precache_sound,			                                               
VM_precache_file,				                                              
VM_SV_setspawnparms,			                                           
NULL,							                                                              
NULL,							                                                            
VM_stof,						                                       
NULL,							                                                           
NULL,							              
NULL,							              
NULL,							              
NULL,							              
NULL,							              
NULL,							              
NULL,							              
VM_SV_tracebox,					                                                                                                                    
VM_randomvec,					                                           
VM_SV_getlight,					                                                   
VM_registercvar,				                                                                      
VM_min,							                                                     
VM_max,							                                                     
VM_bound,						                                                                               
VM_pow,							                                                        
VM_findfloat,					                                                                                
VM_checkextension,				                                                                         
                                       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
VM_fopen,						                                                            
VM_fclose,						                                              
VM_fgets,						                                               
VM_fputs,						                                                       
VM_strlen,						                                          
VM_strcat,						                                                            
VM_substring,					                                                                         
VM_stov,						                                       
VM_strzone,						                                            
VM_strunzone,					                                            
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
                        
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
VM_bitshift,					                                                                   
NULL,							       
NULL,							       
VM_strstrofs,					                                                                               
VM_str2chr,						                                                          
VM_chr2str,						                                                  
VM_strconv,						                                                                                          
VM_strpad,						                                                               
VM_infoadd,						                                                                                
VM_infoget,						                                                             
VM_strncmp,						                                                                    
VM_strncasecmp,					                                                            
VM_strncasecmp,					                                                                        
NULL,							       
VM_SV_AddStat,					                                                                        
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
VM_SV_checkpvs,					                                                      
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
VM_SV_skel_create,				                                                                                                                                                                                                                                                                                                                                                           
VM_SV_skel_build,				                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               
VM_SV_skel_get_numbones,		                                                                                                                                
VM_SV_skel_get_bonename,		                                                                                                                                  
VM_SV_skel_get_boneparent,		                                                                                                                                                                                                                                                           
VM_SV_skel_find_bone,			                                                                                                                                                                                                                           
VM_SV_skel_get_bonerel,			                                                                                                                                                                                                                          
VM_SV_skel_get_boneabs,			                                                                                                                                                                                                             
VM_SV_skel_set_bone,			                                                                                                                                                                                                                                
VM_SV_skel_mul_bone,			                                                                                                                                                                                                                                                        
VM_SV_skel_mul_bones,			                                                                                                                                                                                                                                                                                
VM_SV_skel_copybones,			                                                                                                                                                                                                                                                
VM_SV_skel_delete,				                                                                                                                                                                                                           
VM_SV_frameforname,				                                                                                                                                                                              
VM_SV_frameduration,			                                                                                                                                                                                                                                                                            
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
                       
NULL,							                                    
NULL,							                                               
NULL,							                                             
NULL,							                                                         
NULL,							                                     
NULL,							                                                                                      
NULL,							                                                                                      
NULL,							                                                                                   
NULL,							                           
NULL,							       
NULL,							                                                 
NULL,							                                               
NULL,							       
NULL,							       
NULL,							       
NULL,							                                                                                   
NULL,							                                                 
NULL,							                                                                 
NULL,							                                                           
NULL,							                                            
NULL,							                                                                                                                           
NULL,							                                                                                                                    
NULL,							                                                                                                               
NULL,							                                                                                                    
NULL,							                                                                         
NULL,							                                    
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							                                              
NULL,							                                              
NULL,							                                                    
VM_SV_setmodelindex,			                                                               
VM_SV_modelnameforindex,		                                                           
VM_SV_particleeffectnum,		                                                             
VM_SV_trailparticles,			                                                                                             
VM_SV_pointparticles,			                                                                                                  
NULL,							                                                  
VM_print,						                                                         
NULL,							                                                      
NULL,							                                                       
NULL,							                                                  
NULL,							                                                      
NULL,							                                       
NULL,							                                                      
NULL,							                                                        
NULL,							                                                  
NULL,							                                                                            
NULL,							                                 
VM_isserver,					                                   
NULL,							                                                                                           
NULL,							                                                       
VM_wasfreed,					                                                                                
VM_SV_serverkey,				                                               
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							                                   
NULL,							                                   
NULL,							                                    
NULL,							                                   
NULL,							                                    
NULL,							                                    
NULL,							                                      
NULL,							                                    
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
                              
VM_SV_copyentity,				                                                                  
VM_SV_setcolor,					                                                                
VM_findchain,					                                                                     
VM_findchainfloat,				                                                                             
VM_SV_effect,					                                                                                                                   
VM_SV_te_blood,					                                                                               
VM_SV_te_bloodshower,			                                                                                                                        
VM_SV_te_explosionrgb,			                                                                           
VM_SV_te_particlecube,			                                                                                                                                                                       
VM_SV_te_particlerain,			                                                                                                                             
VM_SV_te_particlesnow,			                                                                                                                             
VM_SV_te_spark,					                                                                          
VM_SV_te_gunshotquad,			                                                         
VM_SV_te_spikequad,				                                                       
VM_SV_te_superspikequad,		                                                            
VM_SV_te_explosionquad,			                                                           
VM_SV_te_smallflash,			                                                         
VM_SV_te_customflash,			                                                                                                       
VM_SV_te_gunshot,				                                                                  
VM_SV_te_spike,					                                                                
VM_SV_te_superspike,			                                                                     
VM_SV_te_explosion,				                                                                    
VM_SV_te_tarexplosion,			                                                                       
VM_SV_te_wizspike,				                                                                   
VM_SV_te_knightspike,			                                                                      
VM_SV_te_lavasplash,			                                                                     
VM_SV_te_teleport,				                                                                   
VM_SV_te_explosion2,			                                                                                                          
VM_SV_te_lightning1,			                                                                                               
VM_SV_te_lightning2,			                                                                                               
VM_SV_te_lightning3,			                                                                                               
VM_SV_te_beam,					                                                                                         
VM_vectorvectors,				                                                            
VM_SV_te_plasmaburn,			                                                         
VM_getsurfacenumpoints,		                                                                       
VM_getsurfacepoint,			                                                                             
VM_getsurfacenormal,			                                                                     
VM_getsurfacetexture,		                                                                      
VM_getsurfacenearpoint,		                                                                        
VM_getsurfaceclippedpoint,	                                                                                     
VM_SV_clientcommand,			                                                                              
VM_tokenize,					                                                                
VM_argv,						                                                            
VM_SV_setattachment,			                                                                                               
VM_search_begin,				                                                                                                
VM_search_end,					                                                       
VM_search_getsize,				                                                            
VM_search_getfilename,			                                                                            
VM_cvar_string,					                                                        
VM_findflags,					                                                                                 
VM_findchainflags,				                                                                             
VM_SV_gettagindex,				                                                                        
VM_SV_gettaginfo,				                                                                        
VM_SV_dropclient,				                                                        
VM_SV_spawnclient,				                                              
VM_SV_clienttype,				                                                        
VM_SV_WriteUnterminatedString,	                                                                                        
VM_SV_te_flamejet,				                                                                                       
NULL,							       
VM_ftoe,						                                                         
VM_buf_create,					                                                
VM_buf_del,						                                                           
VM_buf_getsize,					                                                                
VM_buf_copy,					                                                                                     
VM_buf_sort,					                                                                                             
VM_buf_implode,					                                                                              
VM_bufstr_get,					                                                                                    
VM_bufstr_set,					                                                                                              
VM_bufstr_add,					                                                                                        
VM_bufstr_free,					                                                                                   
NULL,							       
VM_asin,						                                                           
VM_acos,						                                                           
VM_atan,						                                                           
VM_atan2,						                                                                     
VM_tan,							                                                          
VM_strlennocol,					                                                                                                       
VM_strdecolorize,				                                                                                  
VM_strftime,					                                                                       
VM_tokenizebyseparator,			                                                                       
VM_strtolower,					                                                                    
VM_strtoupper,					                                                                    
VM_cvar_defstring,				                                                              
VM_SV_pointsound,				                                                                                              
VM_strreplace,					                                                                                           
VM_strireplace,					                                                                                            
VM_getsurfacepointattribute,                                                                                    
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
VM_crc16,						                                                                              
VM_cvar_type,					                                                              
VM_numentityfields,				                                                          
VM_entityfieldname,				                                                                         
VM_entityfieldtype,				                                                                        
VM_getentityfieldstring,		                                                                                          
VM_putentityfieldstring,		                                                                                                   
VM_SV_WritePicture,				       
NULL,							       
VM_whichpack,					                                        
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
VM_uri_escape,					                                            
VM_uri_unescape,				                                              
VM_etof,					                                                                    
VM_uri_get,						                                                                                                                                              
VM_tokenize_console,					                                                                           
VM_argv_start_index,					                                                                          
VM_argv_end_index,						                                                                        
VM_buf_cvarlist,						                                                                                                             
VM_cvar_description,					                                                                            
VM_gettime,						                                                          
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
VM_loadfromdata,				       
VM_loadfromfile,				       
VM_SV_setpause,					                                          
VM_log,							       
VM_getsoundtime,				                                                                                 
VM_soundlength,					                                                                      
VM_buf_loadfile,                                                                                                          
VM_buf_writefile,                                                                                                                                             
VM_bufstr_find,                                                                                                                                        
VM_matchpattern,                                                                                                                   
NULL,							       
VM_physics_enable,				                                                                                     
VM_physics_addforce,			                                                                                                   
VM_physics_addtorque,			                                                                                
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
VM_callfunction,				       
VM_writetofile,					       
VM_isfunction,					       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
VM_parseentitydata,				       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
VM_SV_getextresponse,			                                   
NULL,							       
NULL,							       
VM_sprintf,                                                               
VM_getsurfacenumtriangles,		                                                                               
VM_getsurfacetriangle,			                                                                                     
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
VM_digest_hex,						       
NULL,							       
NULL,							       
VM_coverage,						       
NULL,							       
};

const int vm_sv_numbuiltins = sizeof(vm_sv_builtins) / sizeof(prvm_builtin_t);

void SVVM_init_cmd(prvm_prog_t *prog)
{
	VM_Cmd_Init(prog);
}

void SVVM_reset_cmd(prvm_prog_t *prog)
{
	World_End(&sv.world);

	if(prog->loaded && PRVM_serverfunction(SV_Shutdown))
	{
		func_t s = PRVM_serverfunction(SV_Shutdown);
		PRVM_serverglobalfloat(time) = sv.time;
		PRVM_serverfunction(SV_Shutdown) = 0;                                        
		prog->ExecuteProgram(prog, s,"SV_Shutdown() required");
	}

	VM_Cmd_Reset(prog);
}
