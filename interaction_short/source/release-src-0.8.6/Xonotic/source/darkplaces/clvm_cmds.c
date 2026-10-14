#include "quakedef.h"

#include "prvm_cmds.h"
#include "csprogs.h"
#include "cl_collision.h"
#include "r_shadow.h"
#include "jpeg.h"
#include "image.h"

                                                                              
         
                          
                                                    
                 
                                         
                                                                                
                                         
                                                 

                                                                                                                                                        
                                                                       

extern cvar_t v_flipped;
extern cvar_t r_equalize_entities_fullbright;

r_refdef_view_t csqc_original_r_refdef_view;
r_refdef_view_t csqc_main_r_refdef_view;

                                  
static void VM_CL_makevectors (prvm_prog_t *prog)
{
	vec3_t angles, forward, right, up;
	VM_SAFEPARMCOUNT(1, VM_CL_makevectors);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), angles);
	AngleVectors(angles, forward, right, up);
	VectorCopy(forward, PRVM_clientglobalvector(v_forward));
	VectorCopy(right, PRVM_clientglobalvector(v_right));
	VectorCopy(up, PRVM_clientglobalvector(v_up));
}

                                        
static void VM_CL_setorigin (prvm_prog_t *prog)
{
	prvm_edict_t	*e;
	prvm_vec_t	*org;
	VM_SAFEPARMCOUNT(2, VM_CL_setorigin);

	e = PRVM_G_EDICT(OFS_PARM0);
	if (e == prog->edicts)
	{
		VM_Warning(prog, "setorigin: can not modify world entity\n");
		return;
	}
	if (e->priv.required->free)
	{
		VM_Warning(prog, "setorigin: can not modify free entity\n");
		return;
	}
	org = PRVM_G_VECTOR(OFS_PARM1);
	VectorCopy (org, PRVM_clientedictvector(e, origin));
	if(e->priv.required->mark == PRVM_EDICT_MARK_WAIT_FOR_SETORIGIN)
		e->priv.required->mark = PRVM_EDICT_MARK_SETORIGIN_CAUGHT;
	CL_LinkEdict(e);
}

static void SetMinMaxSizePRVM (prvm_prog_t *prog, prvm_edict_t *e, prvm_vec_t *min, prvm_vec_t *max)
{
	int		i;

	for (i=0 ; i<3 ; i++)
		if (min[i] > max[i])
			prog->error_cmd("SetMinMaxSize: backwards mins/maxs");

	                     
	VectorCopy (min, PRVM_clientedictvector(e, mins));
	VectorCopy (max, PRVM_clientedictvector(e, maxs));
	VectorSubtract (max, min, PRVM_clientedictvector(e, size));

	CL_LinkEdict (e);
}

static void SetMinMaxSize (prvm_prog_t *prog, prvm_edict_t *e, const vec_t *min, const vec_t *max)
{
	prvm_vec3_t mins, maxs;
	VectorCopy(min, mins);
	VectorCopy(max, maxs);
	SetMinMaxSizePRVM(prog, e, mins, maxs);
}

                                       
static void VM_CL_setmodel (prvm_prog_t *prog)
{
	prvm_edict_t	*e;
	const char		*m;
	dp_model_t *mod;
	int				i;

	VM_SAFEPARMCOUNT(2, VM_CL_setmodel);

	e = PRVM_G_EDICT(OFS_PARM0);
	PRVM_clientedictfloat(e, modelindex) = 0;
	PRVM_clientedictstring(e, model) = 0;

	m = PRVM_G_STRING(OFS_PARM1);
	mod = NULL;
	for (i = 0;i < MAX_MODELS && cl.csqc_model_precache[i];i++)
	{
		if (!strcmp(cl.csqc_model_precache[i]->name, m))
		{
			mod = cl.csqc_model_precache[i];
			PRVM_clientedictstring(e, model) = PRVM_SetEngineString(prog, mod->name);
			PRVM_clientedictfloat(e, modelindex) = -(i+1);
			break;
		}
	}

	if( !mod ) {
		for (i = 0;i < MAX_MODELS;i++)
		{
			mod = cl.model_precache[i];
			if (mod && !strcmp(mod->name, m))
			{
				PRVM_clientedictstring(e, model) = PRVM_SetEngineString(prog, mod->name);
				PRVM_clientedictfloat(e, modelindex) = i;
				break;
			}
		}
	}

	if( mod ) {
		                                                                                                    
		                                                                                                                                                                            
		SetMinMaxSize (prog, e, mod->normalmins, mod->normalmaxs);
	}
	else
	{
		SetMinMaxSize (prog, e, vec3_origin, vec3_origin);
		VM_Warning(prog, "setmodel: model '%s' not precached\n", m);
	}
}

                                                    
static void VM_CL_setsize (prvm_prog_t *prog)
{
	prvm_edict_t	*e;
	vec3_t		mins, maxs;
	VM_SAFEPARMCOUNT(3, VM_CL_setsize);

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

	SetMinMaxSize( prog, e, mins, maxs );

	CL_LinkEdict(e);
}

                                                                                                                  
static void VM_CL_sound (prvm_prog_t *prog)
{
	const char			*sample;
	int					channel;
	prvm_edict_t		*entity;
	float 				fvolume;
	float				attenuation;
	float pitchchange;
	float				startposition;
	int flags;
	vec3_t				org;

	VM_SAFEPARMCOUNTRANGE(5, 7, VM_CL_sound);

	entity = PRVM_G_EDICT(OFS_PARM0);
	channel = (int)PRVM_G_FLOAT(OFS_PARM1);
	sample = PRVM_G_STRING(OFS_PARM2);
	fvolume = PRVM_G_FLOAT(OFS_PARM3);
	attenuation = PRVM_G_FLOAT(OFS_PARM4);

	if (fvolume < 0 || fvolume > 1)
	{
		VM_Warning(prog, "VM_CL_sound: volume must be in range 0-1\n");
		return;
	}

	if (attenuation < 0 || attenuation > 4)
	{
		VM_Warning(prog, "VM_CL_sound: attenuation must be in range 0-4\n");
		return;
	}

	if (prog->argc < 6)
		pitchchange = 0;
	else
		pitchchange = PRVM_G_FLOAT(OFS_PARM5);

	if (prog->argc < 7)
		flags = 0;
	else
	{
		                                                                         
		flags = (int)PRVM_G_FLOAT(OFS_PARM6) & (CHANNELFLAG_RELIABLE | CHANNELFLAG_FORCELOOP | CHANNELFLAG_PAUSED | CHANNELFLAG_FULLVOLUME);
	}

	                                                                     
	                                                                        
	                                                                    
	                    
	if (PRVM_clientglobalfloat(sound_starttime))
		startposition = cl.time - PRVM_clientglobalfloat(sound_starttime);
	else
		startposition = 0;

	channel = CHAN_USER2ENGINE(channel);

	if (!IS_CHAN(channel))
	{
		VM_Warning(prog, "VM_CL_sound: channel must be in range 0-127\n");
		return;
	}

	CL_VM_GetEntitySoundOrigin(MAX_EDICTS + PRVM_NUM_FOR_EDICT(entity), org);
	S_StartSound_StartPosition_Flags(MAX_EDICTS + PRVM_NUM_FOR_EDICT(entity), channel, S_FindName(sample), org, fvolume, attenuation, startposition, flags, pitchchange > 0.0f ? pitchchange * 0.01f : 1.0f);
}

                                                                                      
static void VM_CL_pointsound(prvm_prog_t *prog)
{
	const char			*sample;
	float 				fvolume;
	float				attenuation;
	vec3_t				org;

	VM_SAFEPARMCOUNT(4, VM_CL_pointsound);

	VectorCopy( PRVM_G_VECTOR(OFS_PARM0), org);
	sample = PRVM_G_STRING(OFS_PARM1);
	fvolume = PRVM_G_FLOAT(OFS_PARM2);
	attenuation = PRVM_G_FLOAT(OFS_PARM3);

	if (fvolume < 0 || fvolume > 1)
	{
		VM_Warning(prog, "VM_CL_pointsound: volume must be in range 0-1\n");
		return;
	}

	if (attenuation < 0 || attenuation > 4)
	{
		VM_Warning(prog, "VM_CL_pointsound: attenuation must be in range 0-4\n");
		return;
	}

	                                                                           
	S_StartSound(MAX_EDICTS, 0, S_FindName(sample), org, fvolume, attenuation);
}

                     
static void VM_CL_spawn (prvm_prog_t *prog)
{
	prvm_edict_t *ed;
	ed = PRVM_ED_Alloc(prog);
	VM_RETURN_EDICT(ed);
}

static void CL_VM_SetTraceGlobals(prvm_prog_t *prog, const trace_t *trace, int svent)
{
	VM_SetTraceGlobals(prog, trace);
	PRVM_clientglobalfloat(trace_networkentity) = svent;
}

#define CL_HitNetworkBrushModels(move) !((move) == MOVE_WORLDONLY)
#define CL_HitNetworkPlayers(move)     !((move) == MOVE_WORLDONLY || (move) == MOVE_NOMONSTERS)

                                                                          
static void VM_CL_traceline (prvm_prog_t *prog)
{
	vec3_t	v1, v2;
	trace_t	trace;
	int		move, svent;
	prvm_edict_t	*ent;

                                

	VM_SAFEPARMCOUNTRANGE(4, 4, VM_CL_traceline);

	prog->xfunction->builtinsprofile += 30;

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), v1);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), v2);
	move = (int)PRVM_G_FLOAT(OFS_PARM2);
	ent = PRVM_G_EDICT(OFS_PARM3);

	if (VEC_IS_NAN(v1[0]) || VEC_IS_NAN(v1[1]) || VEC_IS_NAN(v1[2]) || VEC_IS_NAN(v2[0]) || VEC_IS_NAN(v2[1]) || VEC_IS_NAN(v2[2]))
		prog->error_cmd("%s: NAN errors detected in traceline('%f %f %f', '%f %f %f', %i, entity %i)\n", prog->name, v1[0], v1[1], v1[2], v2[0], v2[1], v2[2], move, PRVM_EDICT_TO_PROG(ent));

	trace = CL_TraceLine(v1, v2, move, ent, CL_GenericHitSuperContentsMask(ent), 0, 0, collision_extendtracelinelength.value, CL_HitNetworkBrushModels(move), CL_HitNetworkPlayers(move), &svent, true, false);

	CL_VM_SetTraceGlobals(prog, &trace, svent);
                             
}

  
                 
              

                                       
                                                                              
                           

                                                              
                 
  
                                                                          
static void VM_CL_tracebox (prvm_prog_t *prog)
{
	vec3_t	v1, v2, m1, m2;
	trace_t	trace;
	int		move, svent;
	prvm_edict_t	*ent;

                               
	VM_SAFEPARMCOUNTRANGE(6, 8, VM_CL_tracebox);                                              

	prog->xfunction->builtinsprofile += 30;

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), v1);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), m1);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), m2);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM3), v2);
	move = (int)PRVM_G_FLOAT(OFS_PARM4);
	ent = PRVM_G_EDICT(OFS_PARM5);

	if (VEC_IS_NAN(v1[0]) || VEC_IS_NAN(v1[1]) || VEC_IS_NAN(v1[2]) || VEC_IS_NAN(v2[0]) || VEC_IS_NAN(v2[1]) || VEC_IS_NAN(v2[2]))
		prog->error_cmd("%s: NAN errors detected in tracebox('%f %f %f', '%f %f %f', '%f %f %f', '%f %f %f', %i, entity %i)\n", prog->name, v1[0], v1[1], v1[2], m1[0], m1[1], m1[2], m2[0], m2[1], m2[2], v2[0], v2[1], v2[2], move, PRVM_EDICT_TO_PROG(ent));

	trace = CL_TraceBox(v1, m1, m2, v2, move, ent, CL_GenericHitSuperContentsMask(ent), 0, 0, collision_extendtraceboxlength.value, CL_HitNetworkBrushModels(move), CL_HitNetworkPlayers(move), &svent, true);

	CL_VM_SetTraceGlobals(prog, &trace, svent);
                            
}

static trace_t CL_Trace_Toss (prvm_prog_t *prog, prvm_edict_t *tossent, prvm_edict_t *ignore, int *svent)
{
	int i;
	float gravity;
	vec3_t start, end, mins, maxs, move;
	vec3_t original_origin;
	vec3_t original_velocity;
	vec3_t original_angles;
	vec3_t original_avelocity;
	trace_t trace;

	VectorCopy(PRVM_clientedictvector(tossent, origin)   , original_origin   );
	VectorCopy(PRVM_clientedictvector(tossent, velocity) , original_velocity );
	VectorCopy(PRVM_clientedictvector(tossent, angles)   , original_angles   );
	VectorCopy(PRVM_clientedictvector(tossent, avelocity), original_avelocity);

	gravity = PRVM_clientedictfloat(tossent, gravity);
	if (!gravity)
		gravity = 1.0f;
	gravity *= cl.movevars_gravity * 0.05;

	for (i = 0;i < 200;i++)                                                             
	{
		PRVM_clientedictvector(tossent, velocity)[2] -= gravity;
		VectorMA (PRVM_clientedictvector(tossent, angles), 0.05, PRVM_clientedictvector(tossent, avelocity), PRVM_clientedictvector(tossent, angles));
		VectorScale (PRVM_clientedictvector(tossent, velocity), 0.05, move);
		VectorAdd (PRVM_clientedictvector(tossent, origin), move, end);
		VectorCopy(PRVM_clientedictvector(tossent, origin), start);
		VectorCopy(PRVM_clientedictvector(tossent, mins), mins);
		VectorCopy(PRVM_clientedictvector(tossent, maxs), maxs);
		trace = CL_TraceBox(start, mins, maxs, end, MOVE_NORMAL, tossent, CL_GenericHitSuperContentsMask(tossent), 0, 0, collision_extendmovelength.value, true, true, NULL, true);
		VectorCopy (trace.endpos, PRVM_clientedictvector(tossent, origin));

		if (trace.fraction < 1)
			break;
	}

	VectorCopy(original_origin   , PRVM_clientedictvector(tossent, origin)   );
	VectorCopy(original_velocity , PRVM_clientedictvector(tossent, velocity) );
	VectorCopy(original_angles   , PRVM_clientedictvector(tossent, angles)   );
	VectorCopy(original_avelocity, PRVM_clientedictvector(tossent, avelocity));

	return trace;
}

static void VM_CL_tracetoss (prvm_prog_t *prog)
{
	trace_t	trace;
	prvm_edict_t	*ent;
	prvm_edict_t	*ignore;
	int svent = 0;

	prog->xfunction->builtinsprofile += 600;

	VM_SAFEPARMCOUNT(2, VM_CL_tracetoss);

	ent = PRVM_G_EDICT(OFS_PARM0);
	if (ent == prog->edicts)
	{
		VM_Warning(prog, "tracetoss: can not use world entity\n");
		return;
	}
	ignore = PRVM_G_EDICT(OFS_PARM1);

	trace = CL_Trace_Toss (prog, ent, ignore, &svent);

	CL_VM_SetTraceGlobals(prog, &trace, svent);
}


                                    
static void VM_CL_precache_model (prvm_prog_t *prog)
{
	const char	*name;
	int			i;
	dp_model_t		*m;

	VM_SAFEPARMCOUNT(1, VM_CL_precache_model);

	name = PRVM_G_STRING(OFS_PARM0);
	for (i = 0;i < MAX_MODELS && cl.csqc_model_precache[i];i++)
	{
		if(!strcmp(cl.csqc_model_precache[i]->name, name))
		{
			PRVM_G_FLOAT(OFS_RETURN) = -(i+1);
			return;
		}
	}
	PRVM_G_FLOAT(OFS_RETURN) = 0;
	m = Mod_ForName(name, false, false, name[0] == '*' ? cl.model_name[1] : NULL);
	if(m && m->loaded)
	{
		for (i = 0;i < MAX_MODELS;i++)
		{
			if (!cl.csqc_model_precache[i])
			{
				cl.csqc_model_precache[i] = (dp_model_t*)m;
				PRVM_G_FLOAT(OFS_RETURN) = -(i+1);
				return;
			}
		}
		VM_Warning(prog, "VM_CL_precache_model: no free models\n");
		return;
	}
	VM_Warning(prog, "VM_CL_precache_model: model \"%s\" not found\n", name);
}

                                               
static void VM_CL_findradius (prvm_prog_t *prog)
{
	prvm_edict_t	*ent, *chain;
	vec_t			radius, radius2;
	vec3_t			org, eorg, mins, maxs;
	int				i, numtouchedicts;
	static prvm_edict_t	*touchedicts[MAX_EDICTS];
	int             chainfield;

	VM_SAFEPARMCOUNTRANGE(2, 3, VM_CL_findradius);

	if(prog->argc == 3)
		chainfield = PRVM_G_INT(OFS_PARM2);
	else
		chainfield = prog->fieldoffsets.chain;
	if(chainfield < 0)
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
	numtouchedicts = World_EntitiesInBox(&cl.world, mins, maxs, MAX_EDICTS, touchedicts);
	if (numtouchedicts > MAX_EDICTS)
	{
		                                              
		Con_Printf("CSQC_EntitiesInBox returned %i edicts, max was %i\n", numtouchedicts, MAX_EDICTS);
		numtouchedicts = MAX_EDICTS;
	}
	for (i = 0;i < numtouchedicts;i++)
	{
		ent = touchedicts[i];
		                                                              
		                                                              
		if (PRVM_clientedictfloat(ent, solid) == SOLID_NOT && !sv_gameplayfix_blowupfallenzombies.integer)
			continue;
		                                                                   
		                                                                   
		                      
		VectorSubtract(org, PRVM_clientedictvector(ent, origin), eorg);
		if (sv_gameplayfix_findradiusdistancetobox.integer)
		{
			eorg[0] -= bound(PRVM_clientedictvector(ent, mins)[0], eorg[0], PRVM_clientedictvector(ent, maxs)[0]);
			eorg[1] -= bound(PRVM_clientedictvector(ent, mins)[1], eorg[1], PRVM_clientedictvector(ent, maxs)[1]);
			eorg[2] -= bound(PRVM_clientedictvector(ent, mins)[2], eorg[2], PRVM_clientedictvector(ent, maxs)[2]);
		}
		else
			VectorMAMAM(1, eorg, -0.5f, PRVM_clientedictvector(ent, mins), -0.5f, PRVM_clientedictvector(ent, maxs), eorg);
		if (DotProduct(eorg, eorg) < radius2)
		{
			PRVM_EDICTFIELDEDICT(ent, chainfield) = PRVM_EDICT_TO_PROG(chain);
			chain = ent;
		}
	}

	VM_RETURN_EDICT(chain);
}

                          
static void VM_CL_droptofloor (prvm_prog_t *prog)
{
	prvm_edict_t		*ent;
	vec3_t				start, end, mins, maxs;
	trace_t				trace;

	VM_SAFEPARMCOUNTRANGE(0, 2, VM_CL_droptofloor);                                                                         

	                                     
	PRVM_G_FLOAT(OFS_RETURN) = 0;

	ent = PRVM_PROG_TO_EDICT(PRVM_clientglobaledict(self));
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

	VectorCopy(PRVM_clientedictvector(ent, origin), start);
	VectorCopy(PRVM_clientedictvector(ent, mins), mins);
	VectorCopy(PRVM_clientedictvector(ent, maxs), maxs);
	VectorCopy(PRVM_clientedictvector(ent, origin), end);
	end[2] -= 256;

	trace = CL_TraceBox(start, mins, maxs, end, MOVE_NORMAL, ent, CL_GenericHitSuperContentsMask(ent), 0, 0, collision_extendmovelength.value, true, true, NULL, true);

	if (trace.fraction != 1)
	{
		VectorCopy (trace.endpos, PRVM_clientedictvector(ent, origin));
		PRVM_clientedictfloat(ent, flags) = (int)PRVM_clientedictfloat(ent, flags) | FL_ONGROUND;
		PRVM_clientedictedict(ent, groundentity) = PRVM_EDICT_TO_PROG(trace.ent);
		PRVM_G_FLOAT(OFS_RETURN) = 1;
		                                                                                          
                                                
	}
}

                                                 
static void VM_CL_lightstyle (prvm_prog_t *prog)
{
	int			i;
	const char	*c;

	VM_SAFEPARMCOUNT(2, VM_CL_lightstyle);

	i = (int)PRVM_G_FLOAT(OFS_PARM0);
	c = PRVM_G_STRING(OFS_PARM1);
	if (i >= cl.max_lightstyle)
	{
		VM_Warning(prog, "VM_CL_lightstyle >= MAX_LIGHTSTYLES\n");
		return;
	}
	strlcpy (cl.lightstyle[i].map, c, sizeof (cl.lightstyle[i].map));
	cl.lightstyle[i].map[MAX_STYLESTRING - 1] = 0;
	cl.lightstyle[i].length = (int)strlen(cl.lightstyle[i].map);
}

                                  
static void VM_CL_checkbottom (prvm_prog_t *prog)
{
	static int		cs_yes, cs_no;
	prvm_edict_t	*ent;
	vec3_t			mins, maxs, start, stop;
	trace_t			trace;
	int				x, y;
	float			mid, bottom;

	VM_SAFEPARMCOUNT(1, VM_CL_checkbottom);
	ent = PRVM_G_EDICT(OFS_PARM0);
	PRVM_G_FLOAT(OFS_RETURN) = 0;

	VectorAdd (PRVM_clientedictvector(ent, origin), PRVM_clientedictvector(ent, mins), mins);
	VectorAdd (PRVM_clientedictvector(ent, origin), PRVM_clientedictvector(ent, maxs), maxs);

                                                                       
                          
                                                
	start[2] = mins[2] - 1;
	for	(x=0 ; x<=1 ; x++)
		for	(y=0 ; y<=1 ; y++)
		{
			start[0] = x ? maxs[0] : mins[0];
			start[1] = y ? maxs[1] : mins[1];
			if (!(CL_PointSuperContents(start) & (SUPERCONTENTS_SOLID | SUPERCONTENTS_BODY)))
				goto realcheck;
		}

	cs_yes++;
	PRVM_G_FLOAT(OFS_RETURN) = true;
	return;		                  

realcheck:
	cs_no++;
  
                       
  
	start[2] = mins[2];

                                               
	start[0] = stop[0] = (mins[0] + maxs[0])*0.5;
	start[1] = stop[1] = (mins[1] + maxs[1])*0.5;
	stop[2] = start[2] - 2*sv_stepheight.value;
	trace = CL_TraceLine(start, stop, MOVE_NORMAL, ent, CL_GenericHitSuperContentsMask(ent), 0, 0, collision_extendmovelength.value, true, true, NULL, true, false);

	if (trace.fraction == 1.0)
		return;

	mid = bottom = trace.endpos[2];

                                                
	for	(x=0 ; x<=1 ; x++)
		for	(y=0 ; y<=1 ; y++)
		{
			start[0] = stop[0] = x ? maxs[0] : mins[0];
			start[1] = stop[1] = y ? maxs[1] : mins[1];

			trace = CL_TraceLine(start, stop, MOVE_NORMAL, ent, CL_GenericHitSuperContentsMask(ent), 0, 0, collision_extendmovelength.value, true, true, NULL, true, false);

			if (trace.fraction != 1.0 && trace.endpos[2] > bottom)
				bottom = trace.endpos[2];
			if (trace.fraction == 1.0 || mid - trace.endpos[2] > sv_stepheight.value)
				return;
		}

	cs_yes++;
	PRVM_G_FLOAT(OFS_RETURN) = true;
}

                                    
static void VM_CL_pointcontents (prvm_prog_t *prog)
{
	vec3_t point;
	VM_SAFEPARMCOUNT(1, VM_CL_pointcontents);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), point);
	PRVM_G_FLOAT(OFS_RETURN) = Mod_Q1BSP_NativeContentsFromSuperContents(CL_PointSuperContents(point));
}

                                                                  
static void VM_CL_particle (prvm_prog_t *prog)
{
	vec3_t org, dir;
	int		count;
	unsigned char	color;
	VM_SAFEPARMCOUNT(4, VM_CL_particle);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), org);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), dir);
	color = (int)PRVM_G_FLOAT(OFS_PARM2);
	count = (int)PRVM_G_FLOAT(OFS_PARM3);
	CL_ParticleEffect(EFFECT_SVC_PARTICLE, count, org, org, dir, dir, NULL, color);
}

                                                                         
static void VM_CL_ambientsound (prvm_prog_t *prog)
{
	vec3_t f;
	sfx_t	*s;
	VM_SAFEPARMCOUNT(4, VM_CL_ambientsound);
	s = S_FindName(PRVM_G_STRING(OFS_PARM0));
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), f);
	S_StaticSound (s, f, PRVM_G_FLOAT(OFS_PARM2), PRVM_G_FLOAT(OFS_PARM3)*64);
}

                                                                   
static void VM_CL_getlight (prvm_prog_t *prog)
{
	vec3_t ambientcolor, diffusecolor, diffusenormal;
	vec3_t p;
	int flags = prog->argc >= 2 ? PRVM_G_FLOAT(OFS_PARM1) : LP_LIGHTMAP;

	VM_SAFEPARMCOUNTRANGE(1, 3, VM_CL_getlight);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), p);
	R_CompleteLightPoint(ambientcolor, diffusecolor, diffusenormal, p, flags, r_refdef.scene.lightmapintensity, r_refdef.scene.ambientintensity);
	VectorMA(ambientcolor, 0.5, diffusecolor, PRVM_G_VECTOR(OFS_RETURN));
	if (PRVM_clientglobalvector(getlight_ambient))
		VectorCopy(ambientcolor, PRVM_clientglobalvector(getlight_ambient));
	if (PRVM_clientglobalvector(getlight_diffuse))
		VectorCopy(diffusecolor, PRVM_clientglobalvector(getlight_diffuse));
	if (PRVM_clientglobalvector(getlight_dir))
		VectorCopy(diffusenormal, PRVM_clientglobalvector(getlight_dir));
}

                                                                              
                               

extern cvar_t v_yshearing;
void CSQC_R_RecalcView (void)
{
	extern matrix4x4_t viewmodelmatrix_nobob;
	extern matrix4x4_t viewmodelmatrix_withbob;
	Matrix4x4_CreateFromQuakeEntity(&r_refdef.view.matrix, cl.csqc_vieworigin[0], cl.csqc_vieworigin[1], cl.csqc_vieworigin[2], cl.csqc_viewangles[0], cl.csqc_viewangles[1], cl.csqc_viewangles[2], 1);
	if (v_yshearing.value > 0)
		Matrix4x4_QuakeToDuke3D(&r_refdef.view.matrix, &r_refdef.view.matrix, v_yshearing.value);
	Matrix4x4_Copy(&viewmodelmatrix_nobob, &r_refdef.view.matrix);
	Matrix4x4_ConcatScale(&viewmodelmatrix_nobob, cl_viewmodel_scale.value);
	Matrix4x4_Concat(&viewmodelmatrix_withbob, &r_refdef.view.matrix, &cl.csqc_viewmodelmatrixfromengine);
}

                                   
static void VM_CL_R_ClearScene (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(0, VM_CL_R_ClearScene);
	                                          
	r_refdef.scene.numentities = 0;
	r_refdef.scene.numlights = 0;
	                                                                                              
	r_refdef.view = csqc_original_r_refdef_view;
	VectorCopy(cl.csqc_vieworiginfromengine, cl.csqc_vieworigin);
	VectorCopy(cl.csqc_viewanglesfromengine, cl.csqc_viewangles);
	cl.csqc_vidvars.drawworld = r_drawworld.integer != 0;
	cl.csqc_vidvars.drawenginesbar = false;
	cl.csqc_vidvars.drawcrosshair = false;
	CSQC_R_RecalcView();
}

                                              
static void VM_CL_R_AddEntities (prvm_prog_t *prog)
{
	double t = Sys_DirtyTime();
	int			i, drawmask;
	prvm_edict_t *ed;
	VM_SAFEPARMCOUNT(1, VM_CL_R_AddEntities);
	drawmask = (int)PRVM_G_FLOAT(OFS_PARM0);
	CSQC_RelinkAllEntities(drawmask);

	PRVM_clientglobalfloat(time) = cl.time;
	for(i=1;i<prog->num_edicts;i++)
	{
		                                                                     
		cl.csqcrenderentities[i].entitynumber = 0;
		ed = &prog->edicts[i];
		if(ed->priv.required->free)
			continue;
		CSQC_Think(ed);
		if(ed->priv.required->free)
			continue;
		                                                                                                                      
		CSQC_Predraw(ed);
		if(ed->priv.required->free)
			continue;
		if(!((int)PRVM_clientedictfloat(ed, drawmask) & drawmask))
			continue;
		CSQC_AddRenderEdict(ed, i);
	}

	                                                                                           
	t = Sys_DirtyTime() - t;if (t < 0 || t >= 1800) t = 0;
	prog->functions[PRVM_clientfunction(CSQC_UpdateView)].totaltime -= t;
}

                                            
static void VM_CL_R_AddEntity (prvm_prog_t *prog)
{
	double t = Sys_DirtyTime();
	VM_SAFEPARMCOUNT(1, VM_CL_R_AddEntity);
	CSQC_AddRenderEdict(PRVM_G_EDICT(OFS_PARM0), 0);
	t = Sys_DirtyTime() - t;if (t < 0 || t >= 1800) t = 0;
	prog->functions[PRVM_clientfunction(CSQC_UpdateView)].totaltime -= t;
}

                                                        
                                        
                                            
                                        
                                            
                                                                                                 
static void VM_CL_R_SetView (prvm_prog_t *prog)
{
	int		c;
	prvm_vec_t	*f;
	float	k;

	VM_SAFEPARMCOUNTRANGE(1, 3, VM_CL_R_SetView);

	c = (int)PRVM_G_FLOAT(OFS_PARM0);

	                
	if (prog->argc < 2)
	{
		switch(c)
		{
		case VF_MIN:
			VectorSet(PRVM_G_VECTOR(OFS_RETURN), r_refdef.view.x, r_refdef.view.y, 0);
			break;
		case VF_MIN_X:
			PRVM_G_FLOAT(OFS_RETURN) = r_refdef.view.x;
			break;
		case VF_MIN_Y:
			PRVM_G_FLOAT(OFS_RETURN) = r_refdef.view.y;
			break;
		case VF_SIZE:
			VectorSet(PRVM_G_VECTOR(OFS_RETURN), r_refdef.view.width, r_refdef.view.height, 0);
			break;
		case VF_SIZE_X:
			PRVM_G_FLOAT(OFS_RETURN) = r_refdef.view.width;
			break;
		case VF_SIZE_Y:
			PRVM_G_FLOAT(OFS_RETURN) = r_refdef.view.height;
			break;
		case VF_VIEWPORT:
			VM_Warning(prog, "VM_CL_R_GetView : VF_VIEWPORT can't be retrieved, use VF_MIN/VF_SIZE instead\n");
			break;
		case VF_FOV:
			VectorSet(PRVM_G_VECTOR(OFS_RETURN), r_refdef.view.ortho_x, r_refdef.view.ortho_y, 0);
			break;
		case VF_FOVX:
			PRVM_G_FLOAT(OFS_RETURN) = r_refdef.view.ortho_x;
			break;
		case VF_FOVY:
			PRVM_G_FLOAT(OFS_RETURN) = r_refdef.view.ortho_y;
			break;
		case VF_ORIGIN:
			VectorCopy(cl.csqc_vieworigin, PRVM_G_VECTOR(OFS_RETURN));
			break;
		case VF_ORIGIN_X:
			PRVM_G_FLOAT(OFS_RETURN) = cl.csqc_vieworigin[0];
			break;
		case VF_ORIGIN_Y:
			PRVM_G_FLOAT(OFS_RETURN) = cl.csqc_vieworigin[1];
			break;
		case VF_ORIGIN_Z:
			PRVM_G_FLOAT(OFS_RETURN) = cl.csqc_vieworigin[2];
			break;
		case VF_ANGLES:
			VectorCopy(cl.csqc_viewangles, PRVM_G_VECTOR(OFS_RETURN));
			break;
		case VF_ANGLES_X:
			PRVM_G_FLOAT(OFS_RETURN) = cl.csqc_viewangles[0];
			break;
		case VF_ANGLES_Y:
			PRVM_G_FLOAT(OFS_RETURN) = cl.csqc_viewangles[1];
			break;
		case VF_ANGLES_Z:
			PRVM_G_FLOAT(OFS_RETURN) = cl.csqc_viewangles[2];
			break;
		case VF_DRAWWORLD:
			PRVM_G_FLOAT(OFS_RETURN) = cl.csqc_vidvars.drawworld;
			break;
		case VF_DRAWENGINESBAR:
			PRVM_G_FLOAT(OFS_RETURN) = cl.csqc_vidvars.drawenginesbar;
			break;
		case VF_DRAWCROSSHAIR:
			PRVM_G_FLOAT(OFS_RETURN) = cl.csqc_vidvars.drawcrosshair;
			break;
		case VF_CL_VIEWANGLES:
			VectorCopy(cl.viewangles, PRVM_G_VECTOR(OFS_RETURN));;
			break;
		case VF_CL_VIEWANGLES_X:
			PRVM_G_FLOAT(OFS_RETURN) = cl.viewangles[0];
			break;
		case VF_CL_VIEWANGLES_Y:
			PRVM_G_FLOAT(OFS_RETURN) = cl.viewangles[1];
			break;
		case VF_CL_VIEWANGLES_Z:
			PRVM_G_FLOAT(OFS_RETURN) = cl.viewangles[2];
			break;
		case VF_PERSPECTIVE:
			PRVM_G_FLOAT(OFS_RETURN) = r_refdef.view.useperspective;
			break;
		case VF_CLEARSCREEN:
			PRVM_G_FLOAT(OFS_RETURN) = r_refdef.view.isoverlay;
			break;
		case VF_MAINVIEW:
			PRVM_G_FLOAT(OFS_RETURN) = r_refdef.view.ismain;
			break;
		case VF_FOG_DENSITY:
			PRVM_G_FLOAT(OFS_RETURN) = r_refdef.fog_density;
			break;
		case VF_FOG_COLOR:
			PRVM_G_VECTOR(OFS_RETURN)[0] = r_refdef.fog_red;
			PRVM_G_VECTOR(OFS_RETURN)[1] = r_refdef.fog_green;
			PRVM_G_VECTOR(OFS_RETURN)[2] = r_refdef.fog_blue;
			break;
		case VF_FOG_COLOR_R:
			PRVM_G_VECTOR(OFS_RETURN)[0] = r_refdef.fog_red;
			break;
		case VF_FOG_COLOR_G:
			PRVM_G_VECTOR(OFS_RETURN)[1] = r_refdef.fog_green;
			break;
		case VF_FOG_COLOR_B:
			PRVM_G_VECTOR(OFS_RETURN)[2] = r_refdef.fog_blue;
			break;
		case VF_FOG_ALPHA:
			PRVM_G_FLOAT(OFS_RETURN) = r_refdef.fog_alpha;
			break;
		case VF_FOG_START:
			PRVM_G_FLOAT(OFS_RETURN) = r_refdef.fog_start;
			break;
		case VF_FOG_END:
			PRVM_G_FLOAT(OFS_RETURN) = r_refdef.fog_end;
			break;
		case VF_FOG_HEIGHT:
			PRVM_G_FLOAT(OFS_RETURN) = r_refdef.fog_height;
			break;
		case VF_FOG_FADEDEPTH:
			PRVM_G_FLOAT(OFS_RETURN) = r_refdef.fog_fadedepth;
			break;
		case VF_MINFPS_QUALITY:
			PRVM_G_FLOAT(OFS_RETURN) = r_refdef.view.quality;
			break;
		default:
			PRVM_G_FLOAT(OFS_RETURN) = 0;
			VM_Warning(prog, "VM_CL_R_GetView : unknown parm %i\n", c);
			return;
		}
		return;
	}

	f = PRVM_G_VECTOR(OFS_PARM1);
	k = PRVM_G_FLOAT(OFS_PARM1);
	switch(c)
	{
	case VF_MIN:
		r_refdef.view.x = (int)(f[0]);
		r_refdef.view.y = (int)(f[1]);
		DrawQ_RecalcView();
		break;
	case VF_MIN_X:
		r_refdef.view.x = (int)(k);
		DrawQ_RecalcView();
		break;
	case VF_MIN_Y:
		r_refdef.view.y = (int)(k);
		DrawQ_RecalcView();
		break;
	case VF_SIZE:
		r_refdef.view.width = (int)(f[0]);
		r_refdef.view.height = (int)(f[1]);
		DrawQ_RecalcView();
		break;
	case VF_SIZE_X:
		r_refdef.view.width = (int)(k);
		DrawQ_RecalcView();
		break;
	case VF_SIZE_Y:
		r_refdef.view.height = (int)(k);
		DrawQ_RecalcView();
		break;
	case VF_VIEWPORT:
		r_refdef.view.x = (int)(f[0]);
		r_refdef.view.y = (int)(f[1]);
		f = PRVM_G_VECTOR(OFS_PARM2);
		r_refdef.view.width = (int)(f[0]);
		r_refdef.view.height = (int)(f[1]);
		DrawQ_RecalcView();
		break;
	case VF_FOV:
		r_refdef.view.frustum_x = tan(f[0] * M_PI / 360.0);r_refdef.view.ortho_x = f[0];
		r_refdef.view.frustum_y = tan(f[1] * M_PI / 360.0);r_refdef.view.ortho_y = f[1];
		break;
	case VF_FOVX:
		r_refdef.view.frustum_x = tan(k * M_PI / 360.0);r_refdef.view.ortho_x = k;
		break;
	case VF_FOVY:
		r_refdef.view.frustum_y = tan(k * M_PI / 360.0);r_refdef.view.ortho_y = k;
		break;
	case VF_ORIGIN:
		VectorCopy(f, cl.csqc_vieworigin);
		CSQC_R_RecalcView();
		break;
	case VF_ORIGIN_X:
		cl.csqc_vieworigin[0] = k;
		CSQC_R_RecalcView();
		break;
	case VF_ORIGIN_Y:
		cl.csqc_vieworigin[1] = k;
		CSQC_R_RecalcView();
		break;
	case VF_ORIGIN_Z:
		cl.csqc_vieworigin[2] = k;
		CSQC_R_RecalcView();
		break;
	case VF_ANGLES:
		VectorCopy(f, cl.csqc_viewangles);
		CSQC_R_RecalcView();
		break;
	case VF_ANGLES_X:
		cl.csqc_viewangles[0] = k;
		CSQC_R_RecalcView();
		break;
	case VF_ANGLES_Y:
		cl.csqc_viewangles[1] = k;
		CSQC_R_RecalcView();
		break;
	case VF_ANGLES_Z:
		cl.csqc_viewangles[2] = k;
		CSQC_R_RecalcView();
		break;
	case VF_DRAWWORLD:
		cl.csqc_vidvars.drawworld = ((k != 0) && r_drawworld.integer);
		break;
	case VF_DRAWENGINESBAR:
		cl.csqc_vidvars.drawenginesbar = k != 0;
		break;
	case VF_DRAWCROSSHAIR:
		cl.csqc_vidvars.drawcrosshair = k != 0;
		break;
	case VF_CL_VIEWANGLES:
		VectorCopy(f, cl.viewangles);
		break;
	case VF_CL_VIEWANGLES_X:
		cl.viewangles[0] = k;
		break;
	case VF_CL_VIEWANGLES_Y:
		cl.viewangles[1] = k;
		break;
	case VF_CL_VIEWANGLES_Z:
		cl.viewangles[2] = k;
		break;
	case VF_PERSPECTIVE:
		r_refdef.view.useperspective = k != 0;
		break;
	case VF_CLEARSCREEN:
		r_refdef.view.isoverlay = !k;
		break;
	case VF_MAINVIEW:
		PRVM_G_FLOAT(OFS_RETURN) = r_refdef.view.ismain;
		break;
	case VF_FOG_DENSITY:
		r_refdef.fog_density = k;
		break;
	case VF_FOG_COLOR:
		r_refdef.fog_red = f[0];
		r_refdef.fog_green = f[1];
		r_refdef.fog_blue = f[2];
		break;
	case VF_FOG_COLOR_R:
		r_refdef.fog_red = k;
		break;
	case VF_FOG_COLOR_G:
		r_refdef.fog_green = k;
		break;
	case VF_FOG_COLOR_B:
		r_refdef.fog_blue = k;
		break;
	case VF_FOG_ALPHA:
		r_refdef.fog_alpha = k;
		break;
	case VF_FOG_START:
		r_refdef.fog_start = k;
		break;
	case VF_FOG_END:
		r_refdef.fog_end = k;
		break;
	case VF_FOG_HEIGHT:
		r_refdef.fog_height = k;
		break;
	case VF_FOG_FADEDEPTH:
		r_refdef.fog_fadedepth = k;
		break;
	case VF_MINFPS_QUALITY:
		r_refdef.view.quality = k;
		break;
	default:
		PRVM_G_FLOAT(OFS_RETURN) = 0;
		VM_Warning(prog, "VM_CL_R_SetView : unknown parm %i\n", c);
		return;
	}
	PRVM_G_FLOAT(OFS_RETURN) = 1;
}

                                                                                                                                      
static void VM_CL_R_AddDynamicLight (prvm_prog_t *prog)
{
	double t = Sys_DirtyTime();
	vec3_t org;
	float radius = 300;
	vec3_t col;
	int style = -1;
	const char *cubemapname = NULL;
	int pflags = PFLAGS_CORONA | PFLAGS_FULLDYNAMIC;
	float coronaintensity = 1;
	float coronasizescale = 0.25;
	qboolean castshadow = true;
	float ambientscale = 0;
	float diffusescale = 1;
	float specularscale = 1;
	matrix4x4_t matrix;
	vec3_t forward, left, up;
	VM_SAFEPARMCOUNTRANGE(3, 8, VM_CL_R_AddDynamicLight);

	                                           
	if (r_refdef.scene.numlights >= MAX_DLIGHTS)
		return;

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), org);
	radius = PRVM_G_FLOAT(OFS_PARM1);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), col);
	if (prog->argc >= 4)
	{
		style = (int)PRVM_G_FLOAT(OFS_PARM3);
		if (style >= MAX_LIGHTSTYLES)
		{
			Con_DPrintf("VM_CL_R_AddDynamicLight: out of bounds lightstyle index %i\n", style);
			style = -1;
		}
	}
	if (prog->argc >= 5)
		cubemapname = PRVM_G_STRING(OFS_PARM4);
	if (prog->argc >= 6)
		pflags = (int)PRVM_G_FLOAT(OFS_PARM5);
	coronaintensity = (pflags & PFLAGS_CORONA) != 0;
	castshadow = (pflags & PFLAGS_NOSHADOW) == 0;

	VectorScale(PRVM_clientglobalvector(v_forward), radius, forward);
	VectorScale(PRVM_clientglobalvector(v_right), -radius, left);
	VectorScale(PRVM_clientglobalvector(v_up), radius, up);
	Matrix4x4_FromVectors(&matrix, forward, left, up, org);

	R_RTLight_Update(&r_refdef.scene.templights[r_refdef.scene.numlights], false, &matrix, col, style, cubemapname, castshadow, coronaintensity, coronasizescale, ambientscale, diffusescale, specularscale, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
	r_refdef.scene.lights[r_refdef.scene.numlights] = &r_refdef.scene.templights[r_refdef.scene.numlights];r_refdef.scene.numlights++;
	t = Sys_DirtyTime() - t;if (t < 0 || t >= 1800) t = 0;
	prog->functions[PRVM_clientfunction(CSQC_UpdateView)].totaltime -= t;
}

                                                                              

                                                
static void VM_CL_unproject (prvm_prog_t *prog)
{
	vec3_t f;
	vec3_t temp;
	vec3_t result;

	VM_SAFEPARMCOUNT(1, VM_CL_unproject);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), f);
	VectorSet(temp,
		f[2],
		(-1.0 + 2.0 * (f[0] / vid_conwidth.integer)) * f[2] * -r_refdef.view.frustum_x,
		(-1.0 + 2.0 * (f[1] / vid_conheight.integer)) * f[2] * -r_refdef.view.frustum_y);
	if(v_flipped.integer)
		temp[1] = -temp[1];
	Matrix4x4_Transform(&r_refdef.view.matrix, temp, result);
	VectorCopy(result, PRVM_G_VECTOR(OFS_RETURN));
}

                                              
static void VM_CL_project (prvm_prog_t *prog)
{
	vec3_t f;
	vec3_t v;
	matrix4x4_t m;

	VM_SAFEPARMCOUNT(1, VM_CL_project);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), f);
	Matrix4x4_Invert_Full(&m, &r_refdef.view.matrix);
	Matrix4x4_Transform(&m, f, v);
	if(v_flipped.integer)
		v[1] = -v[1];
	VectorSet(PRVM_G_VECTOR(OFS_RETURN),
		vid_conwidth.integer * (0.5*(1.0+v[1]/v[0]/-r_refdef.view.frustum_x)),
		vid_conheight.integer * (0.5*(1.0+v[2]/v[0]/-r_refdef.view.frustum_y)),
		v[0]);
	               
	                                                                                                      
	                                                                                                           
}

                                             
static void VM_CL_getstatf (prvm_prog_t *prog)
{
	int i;
	union
	{
		float f;
		int l;
	}dat;
	VM_SAFEPARMCOUNT(1, VM_CL_getstatf);
	i = (int)PRVM_G_FLOAT(OFS_PARM0);
	if(i < 0 || i >= MAX_CL_STATS)
	{
		VM_Warning(prog, "VM_CL_getstatf: index>=MAX_CL_STATS or index<0\n");
		return;
	}
	dat.l = cl.stats[i];
	PRVM_G_FLOAT(OFS_RETURN) =  dat.f;
}

                                             
static void VM_CL_getstati (prvm_prog_t *prog)
{
	int i, index;
	int firstbit, bitcount;

	VM_SAFEPARMCOUNTRANGE(1, 3, VM_CL_getstati);

	index = (int)PRVM_G_FLOAT(OFS_PARM0);
	if (prog->argc > 1)
	{
		firstbit = (int)PRVM_G_FLOAT(OFS_PARM1);
		if (prog->argc > 2)
			bitcount = (int)PRVM_G_FLOAT(OFS_PARM2);
		else
			bitcount = 1;
	}
	else
	{
		firstbit = 0;
		bitcount = 32;
	}

	if(index < 0 || index >= MAX_CL_STATS)
	{
		VM_Warning(prog, "VM_CL_getstati: index>=MAX_CL_STATS or index<0\n");
		return;
	}
	i = cl.stats[index];
	if (bitcount != 32)	                                                                      
		i = (((unsigned int)i)&(((1<<bitcount)-1)<<firstbit))>>firstbit;
	PRVM_G_FLOAT(OFS_RETURN) = i;
}

                                                   
static void VM_CL_getstats (prvm_prog_t *prog)
{
	int i;
	char t[17];
	VM_SAFEPARMCOUNT(1, VM_CL_getstats);
	i = (int)PRVM_G_FLOAT(OFS_PARM0);
	if(i < 0 || i > MAX_CL_STATS-4)
	{
		PRVM_G_INT(OFS_RETURN) = OFS_NULL;
		VM_Warning(prog, "VM_CL_getstats: index>MAX_CL_STATS-4 or index<0\n");
		return;
	}
	strlcpy(t, (char*)&cl.stats[i], sizeof(t));
	PRVM_G_INT(OFS_RETURN) = PRVM_SetTempString(prog, t);
}

                                                              
static void VM_CL_setmodelindex (prvm_prog_t *prog)
{
	int				i;
	prvm_edict_t	*t;
	struct model_s	*model;

	VM_SAFEPARMCOUNT(2, VM_CL_setmodelindex);

	t = PRVM_G_EDICT(OFS_PARM0);

	i = (int)PRVM_G_FLOAT(OFS_PARM1);

	PRVM_clientedictstring(t, model) = 0;
	PRVM_clientedictfloat(t, modelindex) = 0;

	if (!i)
		return;

	model = CL_GetModelByIndex(i);
	if (!model)
	{
		VM_Warning(prog, "VM_CL_setmodelindex: null model\n");
		return;
	}
	PRVM_clientedictstring(t, model) = PRVM_SetEngineString(prog, model->name);
	PRVM_clientedictfloat(t, modelindex) = i;

	                                                                                                    
	if (model)
	{
		SetMinMaxSize (prog, t, model->normalmins, model->normalmaxs);
	}
	else
		SetMinMaxSize (prog, t, vec3_origin, vec3_origin);
}

                                                          
static void VM_CL_modelnameforindex (prvm_prog_t *prog)
{
	dp_model_t *model;

	VM_SAFEPARMCOUNT(1, VM_CL_modelnameforindex);

	PRVM_G_INT(OFS_RETURN) = OFS_NULL;
	model = CL_GetModelByIndex((int)PRVM_G_FLOAT(OFS_PARM0));
	PRVM_G_INT(OFS_RETURN) = model ? PRVM_SetEngineString(prog, model->name) : 0;
}

                                                            
static void VM_CL_particleeffectnum (prvm_prog_t *prog)
{
	int			i;
	VM_SAFEPARMCOUNT(1, VM_CL_particleeffectnum);
	i = CL_ParticleEffectIndexForName(PRVM_G_STRING(OFS_PARM0));
	if (i == 0)
		i = -1;
	PRVM_G_FLOAT(OFS_RETURN) = i;
}

                                                                                                            
static void VM_CL_trailparticles (prvm_prog_t *prog)
{
	int				i;
	vec3_t			start, end, velocity;
	prvm_edict_t	*t;
	VM_SAFEPARMCOUNTRANGE(4, 5, VM_CL_trailparticles);

	t = PRVM_G_EDICT(OFS_PARM0);
	i		= (int)PRVM_G_FLOAT(OFS_PARM1);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), start);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM3), end);
	VectorCopy(PRVM_clientedictvector(t, velocity), velocity);

	if (i < 0)
		return;
	CL_ParticleTrail(i, 1, start, end, velocity, velocity, NULL, prog->argc >= 5 ? (int)PRVM_G_FLOAT(OFS_PARM4) : 0, true, true, NULL, NULL, 1);
}

                                                                                                             
static void VM_CL_pointparticles (prvm_prog_t *prog)
{
	int			i;
	float n;
	vec3_t f, v;
	VM_SAFEPARMCOUNTRANGE(4, 5, VM_CL_pointparticles);
	i = (int)PRVM_G_FLOAT(OFS_PARM0);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), f);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), v);
	n = PRVM_G_FLOAT(OFS_PARM3);
	if (i < 0)
		return;
	CL_ParticleEffect(i, n, f, f, v, v, NULL, prog->argc >= 5 ? (int)PRVM_G_FLOAT(OFS_PARM4) : 0);
}

                                                                                                                                                                               
static void VM_CL_boxparticles (prvm_prog_t *prog)
{
	int effectnum;
	                     
	vec3_t origin_from, origin_to, dir_from, dir_to;
	float count;
	int flags;
	qboolean istrail;
	float tintmins[4], tintmaxs[4], fade;
	VM_SAFEPARMCOUNTRANGE(7, 8, VM_CL_boxparticles);

	effectnum = (int)PRVM_G_FLOAT(OFS_PARM0);
	if (effectnum < 0)
		return;
	                                                           
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), origin_from);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM3), origin_to  );
	VectorCopy(PRVM_G_VECTOR(OFS_PARM4), dir_from   );
	VectorCopy(PRVM_G_VECTOR(OFS_PARM5), dir_to     );
	count = PRVM_G_FLOAT(OFS_PARM6);
	if(prog->argc >= 8)
		flags = PRVM_G_FLOAT(OFS_PARM7);
	else
		flags = 0;

	Vector4Set(tintmins, 1, 1, 1, 1);
	Vector4Set(tintmaxs, 1, 1, 1, 1);
	fade = 1;
	istrail = false;

	if(flags & 1)              
	{
		tintmins[3] = PRVM_clientglobalfloat(particles_alphamin);
		tintmaxs[3] = PRVM_clientglobalfloat(particles_alphamax);
	}
	if(flags & 2)              
	{
		VectorCopy(PRVM_clientglobalvector(particles_colormin), tintmins);
		VectorCopy(PRVM_clientglobalvector(particles_colormax), tintmaxs);
	}
	if(flags & 4)             
	{
		fade = PRVM_clientglobalfloat(particles_fade);
	}
	if(flags & 128)                 
	{
		istrail = true;
	}

	if (istrail)
		CL_ParticleTrail(effectnum, count, origin_from, origin_to, dir_from, dir_to, NULL, 0, true, true, tintmins, tintmaxs, fade);
	else
		CL_ParticleBox(effectnum, count, origin_from, origin_to, dir_from, dir_to, NULL, 0, true, true, tintmins, tintmaxs, fade);
}

                                 
static void VM_CL_setpause(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_CL_setpause);
	if ((int)PRVM_G_FLOAT(OFS_PARM0) != 0)
		cl.csqc_paused = true;
	else
		cl.csqc_paused = false;
}

                                                    
static void VM_CL_setcursormode (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_CL_setcursormode);
	cl.csqc_wantsmousemove = PRVM_G_FLOAT(OFS_PARM0) != 0;
	cl_ignoremousemoves = 2;
}

                                     
static void VM_CL_getmousepos(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(0,VM_CL_getmousepos);

	if (key_consoleactive || key_dest != key_game)
		VectorSet(PRVM_G_VECTOR(OFS_RETURN), 0, 0, 0);
	else if (cl.csqc_wantsmousemove)
		VectorSet(PRVM_G_VECTOR(OFS_RETURN), in_windowmouse_x * vid_conwidth.integer / vid.width, in_windowmouse_y * vid_conheight.integer / vid.height, 0);
	else
		VectorSet(PRVM_G_VECTOR(OFS_RETURN), in_mouse_x * vid_conwidth.integer / vid.width, in_mouse_y * vid_conheight.integer / vid.height, 0);
}

                                                     
static void VM_CL_getinputstate (prvm_prog_t *prog)
{
	unsigned int i, frame;
	VM_SAFEPARMCOUNT(1, VM_CL_getinputstate);
	frame = (unsigned int)PRVM_G_FLOAT(OFS_PARM0);
	PRVM_G_FLOAT(OFS_RETURN) = false;
	for (i = 0;i < CL_MAX_USERCMDS;i++)
	{
		if (cl.movecmd[i].sequence == frame)
		{
			VectorCopy(cl.movecmd[i].viewangles, PRVM_clientglobalvector(input_angles));
			PRVM_clientglobalfloat(input_buttons) = cl.movecmd[i].buttons;                                                                                  
			PRVM_clientglobalvector(input_movevalues)[0] = cl.movecmd[i].forwardmove;
			PRVM_clientglobalvector(input_movevalues)[1] = cl.movecmd[i].sidemove;
			PRVM_clientglobalvector(input_movevalues)[2] = cl.movecmd[i].upmove;
			PRVM_clientglobalfloat(input_timelength) = cl.movecmd[i].frametime;
			                                  
			if(cl.movecmd[i].crouch)
			{
				VectorCopy(cl.playercrouchmins, PRVM_clientglobalvector(pmove_mins));
				VectorCopy(cl.playercrouchmaxs, PRVM_clientglobalvector(pmove_maxs));
			}
			else
			{
				VectorCopy(cl.playerstandmins, PRVM_clientglobalvector(pmove_mins));
				VectorCopy(cl.playerstandmaxs, PRVM_clientglobalvector(pmove_maxs));
			}
			PRVM_G_FLOAT(OFS_RETURN) = true;
		}
	}
}

                                                       
static void VM_CL_setsensitivityscale (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_CL_setsensitivityscale);
	cl.sensitivityscale = PRVM_G_FLOAT(OFS_PARM0);
}

                                                 
#define PMF_JUMP_HELD 1                 
#define PMF_LADDER 2                                                                            
#define PMF_DUCKED 4                                                                               
#define PMF_ONGROUND 8                                                                                                                          
static void VM_CL_runplayerphysics (prvm_prog_t *prog)
{
	cl_clientmovement_state_t s;
	prvm_edict_t *ent;

	memset(&s, 0, sizeof(s));

	VM_SAFEPARMCOUNTRANGE(0, 1, VM_CL_runplayerphysics);

	ent = (prog->argc == 1 ? PRVM_G_EDICT(OFS_PARM0) : prog->edicts);
	if(ent == prog->edicts)
	{
		                 
		s.self = NULL;
		VectorCopy(PRVM_clientglobalvector(pmove_org), s.origin);
		VectorCopy(PRVM_clientglobalvector(pmove_vel), s.velocity);
		VectorCopy(PRVM_clientglobalvector(pmove_mins), s.mins);
		VectorCopy(PRVM_clientglobalvector(pmove_maxs), s.maxs);
		s.crouched = 0;
		s.waterjumptime = PRVM_clientglobalfloat(pmove_waterjumptime);
		s.cmd.canjump = (int)PRVM_clientglobalfloat(pmove_jump_held) == 0;
	}
	else
	{
		          
		s.self = ent;
		VectorCopy(PRVM_clientedictvector(ent, origin), s.origin);
		VectorCopy(PRVM_clientedictvector(ent, velocity), s.velocity);
		VectorCopy(PRVM_clientedictvector(ent, mins), s.mins);
		VectorCopy(PRVM_clientedictvector(ent, maxs), s.maxs);
		s.crouched = ((int)PRVM_clientedictfloat(ent, pmove_flags) & PMF_DUCKED) != 0;
		s.waterjumptime = 0;                                                                     
		s.cmd.canjump = ((int)PRVM_clientedictfloat(ent, pmove_flags) & PMF_JUMP_HELD) == 0;
	}

	VectorCopy(PRVM_clientglobalvector(input_angles), s.cmd.viewangles);
	s.cmd.forwardmove = PRVM_clientglobalvector(input_movevalues)[0];
	s.cmd.sidemove = PRVM_clientglobalvector(input_movevalues)[1];
	s.cmd.upmove = PRVM_clientglobalvector(input_movevalues)[2];
	s.cmd.buttons = PRVM_clientglobalfloat(input_buttons);
	s.cmd.frametime = PRVM_clientglobalfloat(input_timelength);
	s.cmd.jump = (s.cmd.buttons & 2) != 0;
	s.cmd.crouch = (s.cmd.buttons & 16) != 0;

	CL_ClientMovement_PlayerMove_Frame(&s);

	if(ent == prog->edicts)
	{
		                 
		VectorCopy(s.origin, PRVM_clientglobalvector(pmove_org));
		VectorCopy(s.velocity, PRVM_clientglobalvector(pmove_vel));
		PRVM_clientglobalfloat(pmove_jump_held) = !s.cmd.canjump;
		PRVM_clientglobalfloat(pmove_waterjumptime) = s.waterjumptime;
	}
	else
	{
		          
		VectorCopy(s.origin, PRVM_clientedictvector(ent, origin));
		VectorCopy(s.velocity, PRVM_clientedictvector(ent, velocity));
		PRVM_clientedictfloat(ent, pmove_flags) =
			(s.crouched ? PMF_DUCKED : 0) |
			(s.cmd.canjump ? 0 : PMF_JUMP_HELD) |
			(s.onground ? PMF_ONGROUND : 0);
	}
}

                                                                           
static void VM_CL_getplayerkey (prvm_prog_t *prog)
{
	int			i;
	char		t[128];
	const char	*c;

	VM_SAFEPARMCOUNT(2, VM_CL_getplayerkey);

	i = (int)PRVM_G_FLOAT(OFS_PARM0);
	c = PRVM_G_STRING(OFS_PARM1);
	PRVM_G_INT(OFS_RETURN) = OFS_NULL;
	Sbar_SortFrags();

	if (i < 0)
		i = Sbar_GetSortedPlayerIndex(-1-i);
	if(i < 0 || i >= cl.maxclients)
		return;

	t[0] = 0;

	if(!strcasecmp(c, "name"))
		strlcpy(t, cl.scores[i].name, sizeof(t));
	else
		if(!strcasecmp(c, "frags"))
			dpsnprintf(t, sizeof(t), "%i", cl.scores[i].frags);
	else
		if(!strcasecmp(c, "ping"))
			dpsnprintf(t, sizeof(t), "%i", cl.scores[i].qw_ping);
	else
		if(!strcasecmp(c, "pl"))
			dpsnprintf(t, sizeof(t), "%i", cl.scores[i].qw_packetloss);
	else
		if(!strcasecmp(c, "movementloss"))
			dpsnprintf(t, sizeof(t), "%i", cl.scores[i].qw_movementloss);
	else
		if(!strcasecmp(c, "entertime"))
			dpsnprintf(t, sizeof(t), "%f", cl.scores[i].qw_entertime);
	else
		if(!strcasecmp(c, "colors"))
			dpsnprintf(t, sizeof(t), "%i", cl.scores[i].colors);
	else
		if(!strcasecmp(c, "topcolor"))
			dpsnprintf(t, sizeof(t), "%i", cl.scores[i].colors & 0xf0);
	else
		if(!strcasecmp(c, "bottomcolor"))
			dpsnprintf(t, sizeof(t), "%i", (cl.scores[i].colors &15)<<4);
	else
		if(!strcasecmp(c, "viewentity"))
			dpsnprintf(t, sizeof(t), "%i", i+1);
	if(!t[0])
		return;
	PRVM_G_INT(OFS_RETURN) = PRVM_SetTempString(prog, t);
}

                                                                                          
static void VM_CL_setlistener (prvm_prog_t *prog)
{
	vec3_t origin, forward, left, up;
	VM_SAFEPARMCOUNT(4, VM_CL_setlistener);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), origin);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), forward);
	VectorNegate(PRVM_G_VECTOR(OFS_PARM2), left);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM3), up);
	Matrix4x4_FromVectors(&cl.csqc_listenermatrix, forward, left, up, origin);
	cl.csqc_usecsqclistener = true;	                                 
}

                                                      
static void VM_CL_registercmd (prvm_prog_t *prog)
{
	char *t;
	VM_SAFEPARMCOUNT(1, VM_CL_registercmd);
	if(!Cmd_Exists(PRVM_G_STRING(OFS_PARM0)))
	{
		size_t alloclen;

		alloclen = strlen(PRVM_G_STRING(OFS_PARM0)) + 1;
		t = (char *)Z_Malloc(alloclen);
		memcpy(t, PRVM_G_STRING(OFS_PARM0), alloclen);
		Cmd_AddCommand(t, NULL, "console command created by QuakeC");
	}
	else
		Cmd_AddCommand(PRVM_G_STRING(OFS_PARM0), NULL, "console command created by QuakeC");

}

                                  
static void VM_CL_ReadByte (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(0, VM_CL_ReadByte);
	PRVM_G_FLOAT(OFS_RETURN) = MSG_ReadByte(&cl_message);
}

                                  
static void VM_CL_ReadChar (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(0, VM_CL_ReadChar);
	PRVM_G_FLOAT(OFS_RETURN) = MSG_ReadChar(&cl_message);
}

                                   
static void VM_CL_ReadShort (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(0, VM_CL_ReadShort);
	PRVM_G_FLOAT(OFS_RETURN) = MSG_ReadShort(&cl_message);
}

                                  
static void VM_CL_ReadLong (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(0, VM_CL_ReadLong);
	PRVM_G_FLOAT(OFS_RETURN) = MSG_ReadLong(&cl_message);
}

                                   
static void VM_CL_ReadCoord (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(0, VM_CL_ReadCoord);
	PRVM_G_FLOAT(OFS_RETURN) = MSG_ReadCoord(&cl_message, cls.protocol);
}

                                   
static void VM_CL_ReadAngle (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(0, VM_CL_ReadAngle);
	PRVM_G_FLOAT(OFS_RETURN) = MSG_ReadAngle(&cl_message, cls.protocol);
}

                                     
static void VM_CL_ReadString (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(0, VM_CL_ReadString);
	PRVM_G_INT(OFS_RETURN) = PRVM_SetTempString(prog, MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring)));
}

                                   
static void VM_CL_ReadFloat (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(0, VM_CL_ReadFloat);
	PRVM_G_FLOAT(OFS_RETURN) = MSG_ReadFloat(&cl_message);
}

                                                      
extern cvar_t cl_readpicture_force;
static void VM_CL_ReadPicture (prvm_prog_t *prog)
{
	const char *name;
	unsigned char *data;
	unsigned char *buf;
	unsigned short size;
	int i;
	cachepic_t *pic;

	VM_SAFEPARMCOUNT(0, VM_CL_ReadPicture);

	name = MSG_ReadString(&cl_message, cl_readstring, sizeof(cl_readstring));
	size = (unsigned short) MSG_ReadShort(&cl_message);

	                                         
	                                               
	                                                                                              

	pic = Draw_CachePic_Flags (name, CACHEPICFLAG_NOTPERSISTENT);

	if(size)
	{
		if(pic->tex == r_texture_notexture)
			pic->tex = NULL;                                                
		if(pic->tex && !cl_readpicture_force.integer)
		{
			                           
			                                         
			for(i = 0; i < size; ++i)
				(void) MSG_ReadByte(&cl_message);
		}
		else
		{
			                    
			                                   
			buf = (unsigned char *) Mem_Alloc(tempmempool, size);
			MSG_ReadBytes(&cl_message, size, buf);
			data = JPEG_LoadImage_BGRA(buf, size, NULL);
			Mem_Free(buf);
			Draw_NewPic(name, image_width, image_height, false, data);
			Mem_Free(data);
		}
	}

	PRVM_G_INT(OFS_RETURN) = PRVM_SetTempString(prog, name);
}

                                                          

static void VM_CL_makestatic (prvm_prog_t *prog)
{
	prvm_edict_t *ent;

	VM_SAFEPARMCOUNT(1, VM_CL_makestatic);

	ent = PRVM_G_EDICT(OFS_PARM0);
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

	if (cl.num_static_entities < cl.max_static_entities)
	{
		int renderflags;
		entity_t *staticent = &cl.static_entities[cl.num_static_entities++];

		                               
		memset(staticent, 0, sizeof(*staticent));
		staticent->render.model = CL_GetModelByIndex((int)PRVM_clientedictfloat(ent, modelindex));
		staticent->render.framegroupblend[0].frame = (int)PRVM_clientedictfloat(ent, frame);
		staticent->render.framegroupblend[0].lerp = 1;
		                               
		staticent->render.framegroupblend[0].start = lhrandom(-10, -1);
		staticent->render.skinnum = (int)PRVM_clientedictfloat(ent, skin);
		staticent->render.effects = (int)PRVM_clientedictfloat(ent, effects);
		staticent->render.alpha = PRVM_clientedictfloat(ent, alpha);
		staticent->render.scale = PRVM_clientedictfloat(ent, scale);
		VectorCopy(PRVM_clientedictvector(ent, colormod), staticent->render.colormod);
		VectorCopy(PRVM_clientedictvector(ent, glowmod), staticent->render.glowmod);

		                  
		if (!staticent->render.alpha)
			staticent->render.alpha = 1.0f;
		if (!staticent->render.scale)
			staticent->render.scale = 1.0f;
		if (!VectorLength2(staticent->render.colormod))
			VectorSet(staticent->render.colormod, 1, 1, 1);
		if (!VectorLength2(staticent->render.glowmod))
			VectorSet(staticent->render.glowmod, 1, 1, 1);

		renderflags = (int)PRVM_clientedictfloat(ent, renderflags);
		if (renderflags & RF_USEAXIS)
		{
			vec3_t forward, left, up, origin;
			VectorCopy(PRVM_clientglobalvector(v_forward), forward);
			VectorNegate(PRVM_clientglobalvector(v_right), left);
			VectorCopy(PRVM_clientglobalvector(v_up), up);
			VectorCopy(PRVM_clientedictvector(ent, origin), origin);
			Matrix4x4_FromVectors(&staticent->render.matrix, forward, left, up, origin);
			Matrix4x4_Scale(&staticent->render.matrix, staticent->render.scale, 1);
		}
		else
			Matrix4x4_CreateFromQuakeEntity(&staticent->render.matrix, PRVM_clientedictvector(ent, origin)[0], PRVM_clientedictvector(ent, origin)[1], PRVM_clientedictvector(ent, origin)[2], PRVM_clientedictvector(ent, angles)[0], PRVM_clientedictvector(ent, angles)[1], PRVM_clientedictvector(ent, angles)[2], staticent->render.scale);

		                           
		if(!r_fullbright.integer)
		{
			if (!(staticent->render.effects & EF_FULLBRIGHT))
				staticent->render.flags |= RENDER_LIGHT;
			else if(r_equalize_entities_fullbright.integer)
				staticent->render.flags |= RENDER_LIGHT | RENDER_EQUALIZE;
		}
		                                            
		if (!(staticent->render.effects & (EF_NOSHADOW | EF_ADDITIVE | EF_NODEPTHTEST)) && (staticent->render.alpha >= 1))
			staticent->render.flags |= RENDER_SHADOW;
		if (staticent->render.effects & EF_NODEPTHTEST)
			staticent->render.flags |= RENDER_NODEPTHTEST;
		if (staticent->render.effects & EF_ADDITIVE)
			staticent->render.flags |= RENDER_ADDITIVE;
		if (staticent->render.effects & EF_DOUBLESIDED)
			staticent->render.flags |= RENDER_DOUBLESIDED;

		staticent->render.allowdecals = true;
		CL_UpdateRenderEntity(&staticent->render);
	}
	else
		Con_Printf("Too many static entities");

                            
	PRVM_ED_Free(prog, ent);
}

                                                                     

  
                 
                

                                      

                    
                 
  
static void VM_CL_copyentity (prvm_prog_t *prog)
{
	prvm_edict_t *in, *out;
	VM_SAFEPARMCOUNT(2, VM_CL_copyentity);
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

	if (VectorCompare(PRVM_clientedictvector(out, absmin), PRVM_clientedictvector(out, absmax)))
		return;
	CL_LinkEdict(out);
}

                                                                     

                                                                                                                   
static void VM_CL_effect (prvm_prog_t *prog)
{
#if 1
	Con_Printf("WARNING: VM_CL_effect not implemented\n");                                                                                                         
#else
	vec3_t org;
	VM_SAFEPARMCOUNT(5, VM_CL_effect);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), org);
	CL_Effect(org, (int)PRVM_G_FLOAT(OFS_PARM1), (int)PRVM_G_FLOAT(OFS_PARM2), (int)PRVM_G_FLOAT(OFS_PARM3), PRVM_G_FLOAT(OFS_PARM4));
#endif
}

                                                                               
static void VM_CL_te_blood (prvm_prog_t *prog)
{
	vec3_t pos, vel, pos2;
	VM_SAFEPARMCOUNT(3, VM_CL_te_blood);
	if (PRVM_G_FLOAT(OFS_PARM2) < 1)
		return;
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), vel);
	CL_FindNonSolidLocation(pos, pos2, 4);
	CL_ParticleEffect(EFFECT_TE_BLOOD, PRVM_G_FLOAT(OFS_PARM2), pos2, pos2, vel, vel, NULL, 0);
}

                                                                                                                        
static void VM_CL_te_bloodshower (prvm_prog_t *prog)
{
	vec_t speed;
	vec3_t mincorner, maxcorner, vel1, vel2;
	VM_SAFEPARMCOUNT(4, VM_CL_te_bloodshower);
	if (PRVM_G_FLOAT(OFS_PARM3) < 1)
		return;
	speed = PRVM_G_FLOAT(OFS_PARM2);
	vel1[0] = -speed;
	vel1[1] = -speed;
	vel1[2] = -speed;
	vel2[0] = speed;
	vel2[1] = speed;
	vel2[2] = speed;
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), mincorner);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), maxcorner);
	CL_ParticleEffect(EFFECT_TE_BLOOD, PRVM_G_FLOAT(OFS_PARM3), mincorner, maxcorner, vel1, vel2, NULL, 0);
}

                                                                           
static void VM_CL_te_explosionrgb (prvm_prog_t *prog)
{
	vec3_t		pos;
	vec3_t		pos2;
	matrix4x4_t	tempmatrix;
	VM_SAFEPARMCOUNT(2, VM_CL_te_explosionrgb);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_FindNonSolidLocation(pos, pos2, 10);
	CL_ParticleExplosion(pos2);
	Matrix4x4_CreateTranslate(&tempmatrix, pos2[0], pos2[1], pos2[2]);
	CL_AllocLightFlash(NULL, &tempmatrix, 350, PRVM_G_VECTOR(OFS_PARM1)[0], PRVM_G_VECTOR(OFS_PARM1)[1], PRVM_G_VECTOR(OFS_PARM1)[2], 700, 0.5, 0, -1, true, 1, 0.25, 0.25, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
}

                                                                                                                                                                       
static void VM_CL_te_particlecube (prvm_prog_t *prog)
{
	vec3_t mincorner, maxcorner, vel;
	VM_SAFEPARMCOUNT(7, VM_CL_te_particlecube);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), mincorner);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), maxcorner);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), vel);
	CL_ParticleCube(mincorner, maxcorner, vel, (int)PRVM_G_FLOAT(OFS_PARM3), (int)PRVM_G_FLOAT(OFS_PARM4), PRVM_G_FLOAT(OFS_PARM5), PRVM_G_FLOAT(OFS_PARM6));
}

                                                                                                                             
static void VM_CL_te_particlerain (prvm_prog_t *prog)
{
	vec3_t mincorner, maxcorner, vel;
	VM_SAFEPARMCOUNT(5, VM_CL_te_particlerain);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), mincorner);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), maxcorner);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), vel);
	CL_ParticleRain(mincorner, maxcorner, vel, (int)PRVM_G_FLOAT(OFS_PARM3), (int)PRVM_G_FLOAT(OFS_PARM4), 0);
}

                                                                                                                             
static void VM_CL_te_particlesnow (prvm_prog_t *prog)
{
	vec3_t mincorner, maxcorner, vel;
	VM_SAFEPARMCOUNT(5, VM_CL_te_particlesnow);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), mincorner);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), maxcorner);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), vel);
	CL_ParticleRain(mincorner, maxcorner, vel, (int)PRVM_G_FLOAT(OFS_PARM3), (int)PRVM_G_FLOAT(OFS_PARM4), 1);
}

                                                            
static void VM_CL_te_spark (prvm_prog_t *prog)
{
	vec3_t pos, pos2, vel;
	VM_SAFEPARMCOUNT(3, VM_CL_te_spark);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), vel);
	CL_FindNonSolidLocation(pos, pos2, 4);
	CL_ParticleEffect(EFFECT_TE_SPARK, PRVM_G_FLOAT(OFS_PARM2), pos2, pos2, vel, vel, NULL, 0);
}

extern cvar_t cl_sound_ric_gunshot;
                                                         
static void VM_CL_te_gunshotquad (prvm_prog_t *prog)
{
	vec3_t		pos, pos2;
	int			rnd;
	VM_SAFEPARMCOUNT(1, VM_CL_te_gunshotquad);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_FindNonSolidLocation(pos, pos2, 4);
	CL_ParticleEffect(EFFECT_TE_GUNSHOTQUAD, 1, pos2, pos2, vec3_origin, vec3_origin, NULL, 0);
	if(cl_sound_ric_gunshot.integer >= 2)
	{
		if (rand() % 5)			S_StartSound(-1, 0, cl.sfx_tink1, pos2, 1, 1);
		else
		{
			rnd = rand() & 3;
			if (rnd == 1)		S_StartSound(-1, 0, cl.sfx_ric1, pos2, 1, 1);
			else if (rnd == 2)	S_StartSound(-1, 0, cl.sfx_ric2, pos2, 1, 1);
			else				S_StartSound(-1, 0, cl.sfx_ric3, pos2, 1, 1);
		}
	}
}

                                                       
static void VM_CL_te_spikequad (prvm_prog_t *prog)
{
	vec3_t		pos, pos2;
	int			rnd;
	VM_SAFEPARMCOUNT(1, VM_CL_te_spikequad);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_FindNonSolidLocation(pos, pos2, 4);
	CL_ParticleEffect(EFFECT_TE_SPIKEQUAD, 1, pos2, pos2, vec3_origin, vec3_origin, NULL, 0);
	if (rand() % 5)			S_StartSound(-1, 0, cl.sfx_tink1, pos2, 1, 1);
	else
	{
		rnd = rand() & 3;
		if (rnd == 1)		S_StartSound(-1, 0, cl.sfx_ric1, pos2, 1, 1);
		else if (rnd == 2)	S_StartSound(-1, 0, cl.sfx_ric2, pos2, 1, 1);
		else				S_StartSound(-1, 0, cl.sfx_ric3, pos2, 1, 1);
	}
}

                                                            
static void VM_CL_te_superspikequad (prvm_prog_t *prog)
{
	vec3_t		pos, pos2;
	int			rnd;
	VM_SAFEPARMCOUNT(1, VM_CL_te_superspikequad);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_FindNonSolidLocation(pos, pos2, 4);
	CL_ParticleEffect(EFFECT_TE_SUPERSPIKEQUAD, 1, pos2, pos2, vec3_origin, vec3_origin, NULL, 0);
	if (rand() % 5)			S_StartSound(-1, 0, cl.sfx_tink1, pos, 1, 1);
	else
	{
		rnd = rand() & 3;
		if (rnd == 1)		S_StartSound(-1, 0, cl.sfx_ric1, pos2, 1, 1);
		else if (rnd == 2)	S_StartSound(-1, 0, cl.sfx_ric2, pos2, 1, 1);
		else				S_StartSound(-1, 0, cl.sfx_ric3, pos2, 1, 1);
	}
}

                                                           
static void VM_CL_te_explosionquad (prvm_prog_t *prog)
{
	vec3_t		pos, pos2;
	VM_SAFEPARMCOUNT(1, VM_CL_te_explosionquad);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_FindNonSolidLocation(pos, pos2, 10);
	CL_ParticleEffect(EFFECT_TE_EXPLOSIONQUAD, 1, pos2, pos2, vec3_origin, vec3_origin, NULL, 0);
	S_StartSound(-1, 0, cl.sfx_r_exp3, pos2, 1, 1);
}

                                                         
static void VM_CL_te_smallflash (prvm_prog_t *prog)
{
	vec3_t		pos, pos2;
	VM_SAFEPARMCOUNT(1, VM_CL_te_smallflash);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_FindNonSolidLocation(pos, pos2, 10);
	CL_ParticleEffect(EFFECT_TE_SMALLFLASH, 1, pos2, pos2, vec3_origin, vec3_origin, NULL, 0);
}

                                                                                                       
static void VM_CL_te_customflash (prvm_prog_t *prog)
{
	vec3_t		pos, pos2;
	matrix4x4_t	tempmatrix;
	VM_SAFEPARMCOUNT(4, VM_CL_te_customflash);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_FindNonSolidLocation(pos, pos2, 4);
	Matrix4x4_CreateTranslate(&tempmatrix, pos2[0], pos2[1], pos2[2]);
	CL_AllocLightFlash(NULL, &tempmatrix, PRVM_G_FLOAT(OFS_PARM1), PRVM_G_VECTOR(OFS_PARM3)[0], PRVM_G_VECTOR(OFS_PARM3)[1], PRVM_G_VECTOR(OFS_PARM3)[2], PRVM_G_FLOAT(OFS_PARM1) / PRVM_G_FLOAT(OFS_PARM2), PRVM_G_FLOAT(OFS_PARM2), 0, -1, true, 1, 0.25, 1, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
}

                                                                  
static void VM_CL_te_gunshot (prvm_prog_t *prog)
{
	vec3_t		pos, pos2;
	int			rnd;
	VM_SAFEPARMCOUNT(1, VM_CL_te_gunshot);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_FindNonSolidLocation(pos, pos2, 4);
	CL_ParticleEffect(EFFECT_TE_GUNSHOT, 1, pos2, pos2, vec3_origin, vec3_origin, NULL, 0);
	if(cl_sound_ric_gunshot.integer == 1 || cl_sound_ric_gunshot.integer == 3)
	{
		if (rand() % 5)			S_StartSound(-1, 0, cl.sfx_tink1, pos2, 1, 1);
		else
		{
			rnd = rand() & 3;
			if (rnd == 1)		S_StartSound(-1, 0, cl.sfx_ric1, pos2, 1, 1);
			else if (rnd == 2)	S_StartSound(-1, 0, cl.sfx_ric2, pos2, 1, 1);
			else				S_StartSound(-1, 0, cl.sfx_ric3, pos2, 1, 1);
		}
	}
}

                                                                
static void VM_CL_te_spike (prvm_prog_t *prog)
{
	vec3_t		pos, pos2;
	int			rnd;
	VM_SAFEPARMCOUNT(1, VM_CL_te_spike);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_FindNonSolidLocation(pos, pos2, 4);
	CL_ParticleEffect(EFFECT_TE_SPIKE, 1, pos2, pos2, vec3_origin, vec3_origin, NULL, 0);
	if (rand() % 5)			S_StartSound(-1, 0, cl.sfx_tink1, pos2, 1, 1);
	else
	{
		rnd = rand() & 3;
		if (rnd == 1)		S_StartSound(-1, 0, cl.sfx_ric1, pos2, 1, 1);
		else if (rnd == 2)	S_StartSound(-1, 0, cl.sfx_ric2, pos2, 1, 1);
		else				S_StartSound(-1, 0, cl.sfx_ric3, pos2, 1, 1);
	}
}

                                                                     
static void VM_CL_te_superspike (prvm_prog_t *prog)
{
	vec3_t		pos, pos2;
	int			rnd;
	VM_SAFEPARMCOUNT(1, VM_CL_te_superspike);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_FindNonSolidLocation(pos, pos2, 4);
	CL_ParticleEffect(EFFECT_TE_SUPERSPIKE, 1, pos2, pos2, vec3_origin, vec3_origin, NULL, 0);
	if (rand() % 5)			S_StartSound(-1, 0, cl.sfx_tink1, pos2, 1, 1);
	else
	{
		rnd = rand() & 3;
		if (rnd == 1)		S_StartSound(-1, 0, cl.sfx_ric1, pos2, 1, 1);
		else if (rnd == 2)	S_StartSound(-1, 0, cl.sfx_ric2, pos2, 1, 1);
		else				S_StartSound(-1, 0, cl.sfx_ric3, pos2, 1, 1);
	}
}

                                                                    
static void VM_CL_te_explosion (prvm_prog_t *prog)
{
	vec3_t		pos, pos2;
	VM_SAFEPARMCOUNT(1, VM_CL_te_explosion);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_FindNonSolidLocation(pos, pos2, 10);
	CL_ParticleEffect(EFFECT_TE_EXPLOSION, 1, pos2, pos2, vec3_origin, vec3_origin, NULL, 0);
	S_StartSound(-1, 0, cl.sfx_r_exp3, pos2, 1, 1);
}

                                                                       
static void VM_CL_te_tarexplosion (prvm_prog_t *prog)
{
	vec3_t		pos, pos2;
	VM_SAFEPARMCOUNT(1, VM_CL_te_tarexplosion);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_FindNonSolidLocation(pos, pos2, 10);
	CL_ParticleEffect(EFFECT_TE_TAREXPLOSION, 1, pos2, pos2, vec3_origin, vec3_origin, NULL, 0);
	S_StartSound(-1, 0, cl.sfx_r_exp3, pos2, 1, 1);
}

                                                                   
static void VM_CL_te_wizspike (prvm_prog_t *prog)
{
	vec3_t		pos, pos2;
	VM_SAFEPARMCOUNT(1, VM_CL_te_wizspike);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_FindNonSolidLocation(pos, pos2, 4);
	CL_ParticleEffect(EFFECT_TE_WIZSPIKE, 1, pos2, pos2, vec3_origin, vec3_origin, NULL, 0);
	S_StartSound(-1, 0, cl.sfx_wizhit, pos2, 1, 1);
}

                                                                      
static void VM_CL_te_knightspike (prvm_prog_t *prog)
{
	vec3_t		pos, pos2;
	VM_SAFEPARMCOUNT(1, VM_CL_te_knightspike);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_FindNonSolidLocation(pos, pos2, 4);
	CL_ParticleEffect(EFFECT_TE_KNIGHTSPIKE, 1, pos2, pos2, vec3_origin, vec3_origin, NULL, 0);
	S_StartSound(-1, 0, cl.sfx_knighthit, pos2, 1, 1);
}

                                                                     
static void VM_CL_te_lavasplash (prvm_prog_t *prog)
{
	vec3_t		pos;
	VM_SAFEPARMCOUNT(1, VM_CL_te_lavasplash);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_ParticleEffect(EFFECT_TE_LAVASPLASH, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
}

                                                                   
static void VM_CL_te_teleport (prvm_prog_t *prog)
{
	vec3_t		pos;
	VM_SAFEPARMCOUNT(1, VM_CL_te_teleport);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_ParticleEffect(EFFECT_TE_TELEPORT, 1, pos, pos, vec3_origin, vec3_origin, NULL, 0);
}

                                                                                                          
static void VM_CL_te_explosion2 (prvm_prog_t *prog)
{
	vec3_t		pos, pos2, color;
	matrix4x4_t	tempmatrix;
	int			colorStart, colorLength;
	unsigned char		*tempcolor;
	VM_SAFEPARMCOUNT(3, VM_CL_te_explosion2);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	colorStart = (int)PRVM_G_FLOAT(OFS_PARM1);
	colorLength = (int)PRVM_G_FLOAT(OFS_PARM2);
	CL_FindNonSolidLocation(pos, pos2, 10);
	CL_ParticleExplosion2(pos2, colorStart, colorLength);
	tempcolor = palette_rgb[(rand()%colorLength) + colorStart];
	color[0] = tempcolor[0] * (2.0f / 255.0f);
	color[1] = tempcolor[1] * (2.0f / 255.0f);
	color[2] = tempcolor[2] * (2.0f / 255.0f);
	Matrix4x4_CreateTranslate(&tempmatrix, pos2[0], pos2[1], pos2[2]);
	CL_AllocLightFlash(NULL, &tempmatrix, 350, color[0], color[1], color[2], 700, 0.5, 0, -1, true, 1, 0.25, 0.25, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
	S_StartSound(-1, 0, cl.sfx_r_exp3, pos2, 1, 1);
}


                                                                                               
static void VM_CL_te_lightning1 (prvm_prog_t *prog)
{
	vec3_t		start, end;
	VM_SAFEPARMCOUNT(3, VM_CL_te_lightning1);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), start);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), end);
	CL_NewBeam(PRVM_G_EDICTNUM(OFS_PARM0), start, end, cl.model_bolt, true);
}

                                                                                               
static void VM_CL_te_lightning2 (prvm_prog_t *prog)
{
	vec3_t		start, end;
	VM_SAFEPARMCOUNT(3, VM_CL_te_lightning2);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), start);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), end);
	CL_NewBeam(PRVM_G_EDICTNUM(OFS_PARM0), start, end, cl.model_bolt2, true);
}

                                                                                               
static void VM_CL_te_lightning3 (prvm_prog_t *prog)
{
	vec3_t		start, end;
	VM_SAFEPARMCOUNT(3, VM_CL_te_lightning3);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), start);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), end);
	CL_NewBeam(PRVM_G_EDICTNUM(OFS_PARM0), start, end, cl.model_bolt3, false);
}

                                                                                         
static void VM_CL_te_beam (prvm_prog_t *prog)
{
	vec3_t		start, end;
	VM_SAFEPARMCOUNT(3, VM_CL_te_beam);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), start);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM2), end);
	CL_NewBeam(PRVM_G_EDICTNUM(OFS_PARM0), start, end, cl.model_beam, false);
}

                                                         
static void VM_CL_te_plasmaburn (prvm_prog_t *prog)
{
	vec3_t		pos, pos2;
	VM_SAFEPARMCOUNT(1, VM_CL_te_plasmaburn);

	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	CL_FindNonSolidLocation(pos, pos2, 4);
	CL_ParticleEffect(EFFECT_TE_PLASMABURN, 1, pos2, pos2, vec3_origin, vec3_origin, NULL, 0);
}

                                                                                     
static void VM_CL_te_flamejet (prvm_prog_t *prog)
{
	vec3_t		pos, pos2, vel;
	VM_SAFEPARMCOUNT(3, VM_CL_te_flamejet);
	if (PRVM_G_FLOAT(OFS_PARM2) < 1)
		return;
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), pos);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), vel);
	CL_FindNonSolidLocation(pos, pos2, 4);
	CL_ParticleEffect(EFFECT_TE_FLAMEJET, PRVM_G_FLOAT(OFS_PARM2), pos2, pos2, vel, vel, NULL, 0);
}


                                                                      
static void VM_CL_setattachment (prvm_prog_t *prog)
{
	prvm_edict_t *e;
	prvm_edict_t *tagentity;
	const char *tagname;
	int modelindex;
	int tagindex;
	dp_model_t *model;
	VM_SAFEPARMCOUNT(3, VM_CL_setattachment);

	e = PRVM_G_EDICT(OFS_PARM0);
	tagentity = PRVM_G_EDICT(OFS_PARM1);
	tagname = PRVM_G_STRING(OFS_PARM2);

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
		modelindex = (int)PRVM_clientedictfloat(tagentity, modelindex);
		model = CL_GetModelByIndex(modelindex);
		if (model)
		{
			tagindex = Mod_Alias_GetTagIndexForName(model, (int)PRVM_clientedictfloat(tagentity, skin), tagname);
			if (tagindex == 0)
				Con_DPrintf("setattachment(edict %i, edict %i, string \"%s\"): tried to find tag named \"%s\" on entity %i (model \"%s\") but could not find it\n", PRVM_NUM_FOR_EDICT(e), PRVM_NUM_FOR_EDICT(tagentity), tagname, tagname, PRVM_NUM_FOR_EDICT(tagentity), model->name);
		}
		else
			Con_DPrintf("setattachment(edict %i, edict %i, string \"%s\"): tried to find tag named \"%s\" on entity %i but it has no model\n", PRVM_NUM_FOR_EDICT(e), PRVM_NUM_FOR_EDICT(tagentity), tagname, tagname, PRVM_NUM_FOR_EDICT(tagentity));
	}

	PRVM_clientedictedict(e, tag_entity) = PRVM_EDICT_TO_PROG(tagentity);
	PRVM_clientedictfloat(e, tag_index) = tagindex;
}

                                         
                                           

static int CL_GetTagIndex (prvm_prog_t *prog, prvm_edict_t *e, const char *tagname)
{
	dp_model_t *model = CL_GetModelFromEdict(e);
	if (model)
		return Mod_Alias_GetTagIndexForName(model, (int)PRVM_clientedictfloat(e, skin), tagname);
	else
		return -1;
}

static int CL_GetExtendedTagInfo (prvm_prog_t *prog, prvm_edict_t *e, int tagindex, int *parentindex, const char **tagname, matrix4x4_t *tag_localmatrix)
{
	int r;
	dp_model_t *model;

	*tagname = NULL;
	*parentindex = 0;
	Matrix4x4_CreateIdentity(tag_localmatrix);

	if (tagindex >= 0
	 && (model = CL_GetModelFromEdict(e))
	 && model->animscenes)
	{
		r = Mod_Alias_GetExtendedTagInfoForIndex(model, (int)PRVM_clientedictfloat(e, skin), e->priv.server->frameblend, &e->priv.server->skeleton, tagindex - 1, parentindex, tagname, tag_localmatrix);

		if(!r)            
			*parentindex += 1;

		return r;
	}

	return 1;
}

int CL_GetPitchSign(prvm_prog_t *prog, prvm_edict_t *ent)
{
	dp_model_t *model;
	if ((model = CL_GetModelFromEdict(ent)) && model->type == mod_alias)
		return -1;
	return 1;
}

void CL_GetEntityMatrix (prvm_prog_t *prog, prvm_edict_t *ent, matrix4x4_t *out, qboolean viewmatrix)
{
	float scale;
	float pitchsign = 1;

	scale = PRVM_clientedictfloat(ent, scale);
	if (!scale)
		scale = 1.0f;

	if(viewmatrix)
		*out = r_refdef.view.matrix;
	else if ((int)PRVM_clientedictfloat(ent, renderflags) & RF_USEAXIS)
	{
		vec3_t forward;
		vec3_t left;
		vec3_t up;
		vec3_t origin;
		VectorScale(PRVM_clientglobalvector(v_forward), scale, forward);
		VectorScale(PRVM_clientglobalvector(v_right), -scale, left);
		VectorScale(PRVM_clientglobalvector(v_up), scale, up);
		VectorCopy(PRVM_clientedictvector(ent, origin), origin);
		Matrix4x4_FromVectors(out, forward, left, up, origin);
	}
	else
	{
		pitchsign = CL_GetPitchSign(prog, ent);
		Matrix4x4_CreateFromQuakeEntity(out, PRVM_clientedictvector(ent, origin)[0], PRVM_clientedictvector(ent, origin)[1], PRVM_clientedictvector(ent, origin)[2], pitchsign * PRVM_clientedictvector(ent, angles)[0], PRVM_clientedictvector(ent, angles)[1], PRVM_clientedictvector(ent, angles)[2], scale);
	}
}

static int CL_GetEntityLocalTagMatrix(prvm_prog_t *prog, prvm_edict_t *ent, int tagindex, matrix4x4_t *out)
{
	dp_model_t *model;
	if (tagindex >= 0
	 && (model = CL_GetModelFromEdict(ent))
	 && model->animscenes)
	{
		VM_GenerateFrameGroupBlend(prog, ent->priv.server->framegroupblend, ent);
		VM_FrameBlendFromFrameGroupBlend(ent->priv.server->frameblend, ent->priv.server->framegroupblend, model, cl.time);
		VM_UpdateEdictSkeleton(prog, ent, model, ent->priv.server->frameblend);
		return Mod_Alias_GetTagMatrix(model, ent->priv.server->frameblend, &ent->priv.server->skeleton, tagindex, out);
	}
	*out = identitymatrix;
	return 0;
}

                        
                                    
                   
                  
                                  
                                   
                                       
extern cvar_t cl_bob;
extern cvar_t cl_bobcycle;
extern cvar_t cl_bobup;
int CL_GetTagMatrix (prvm_prog_t *prog, matrix4x4_t *out, prvm_edict_t *ent, int tagindex, prvm_vec_t *shadingorigin)
{
	int ret;
	int attachloop;
	matrix4x4_t entitymatrix, tagmatrix, attachmatrix;
	dp_model_t *model;

	*out = identitymatrix;                                               

	if (ent == prog->edicts)
		return 1;
	if (ent->priv.server->free)
		return 2;

	model = CL_GetModelFromEdict(ent);
	if(!model)
		return 3;

	tagmatrix = identitymatrix;
	attachloop = 0;
	for(;;)
	{
		if(attachloop >= 256)
			return 5;
		                                                                     
		                          
		ret = CL_GetEntityLocalTagMatrix(prog, ent, tagindex - 1, &attachmatrix);
		if(ret && attachloop == 0)
			return ret;
		CL_GetEntityMatrix(prog, ent, &entitymatrix, false);
		Matrix4x4_Concat(&tagmatrix, &attachmatrix, out);
		Matrix4x4_Concat(out, &entitymatrix, &tagmatrix);
		                                              
		if (PRVM_clientedictedict(ent, tag_entity))
		{
			tagindex = (int)PRVM_clientedictfloat(ent, tag_index);
			ent = PRVM_EDICT_NUM(PRVM_clientedictedict(ent, tag_entity));
		}
		else
			break;
		attachloop++;
	}

	                         
	if ((int)PRVM_clientedictfloat(ent, renderflags) & RF_VIEWMODEL)
	{
		Matrix4x4_Copy(&tagmatrix, out);

		CL_GetEntityMatrix(prog, prog->edicts, &entitymatrix, true);
		Matrix4x4_Concat(out, &entitymatrix, &tagmatrix);

		  
                                       
                                                                                  
   
                     
                                                                     
                                                                      
                                                                       
                                                                        
                                     
                       
                              
                                               
       
                                                                             
                                                     
                                              
                                                                                                                                                                                                  
                                 
                                                        
   
    

		                                
		if (shadingorigin)
			Matrix4x4_OriginFromMatrix(&r_refdef.view.matrix, shadingorigin);
	}
	else
	{
		                                                    
		if (shadingorigin)
			Matrix4x4_OriginFromMatrix(out, shadingorigin);
	}
	return 0;
}

                                                                        
static void VM_CL_gettagindex (prvm_prog_t *prog)
{
	prvm_edict_t *ent;
	const char *tag_name;
	int tag_index;

	VM_SAFEPARMCOUNT(2, VM_CL_gettagindex);

	ent = PRVM_G_EDICT(OFS_PARM0);
	tag_name = PRVM_G_STRING(OFS_PARM1);
	if (ent == prog->edicts)
	{
		VM_Warning(prog, "VM_CL_gettagindex(entity #%i): can't affect world entity\n", PRVM_NUM_FOR_EDICT(ent));
		return;
	}
	if (ent->priv.server->free)
	{
		VM_Warning(prog, "VM_CL_gettagindex(entity #%i): can't affect free entity\n", PRVM_NUM_FOR_EDICT(ent));
		return;
	}

	tag_index = 0;
	if (!CL_GetModelFromEdict(ent))
		Con_DPrintf("VM_CL_gettagindex(entity #%i): null or non-precached model\n", PRVM_NUM_FOR_EDICT(ent));
	else
	{
		tag_index = CL_GetTagIndex(prog, ent, tag_name);
		if (tag_index == 0)
			if(developer_extra.integer)
				Con_DPrintf("VM_CL_gettagindex(entity #%i): tag \"%s\" not found\n", PRVM_NUM_FOR_EDICT(ent), tag_name);
	}
	PRVM_G_FLOAT(OFS_RETURN) = tag_index;
}

                                                                        
static void VM_CL_gettaginfo (prvm_prog_t *prog)
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

	VM_SAFEPARMCOUNT(2, VM_CL_gettaginfo);

	e = PRVM_G_EDICT(OFS_PARM0);
	tagindex = (int)PRVM_G_FLOAT(OFS_PARM1);
	returncode = CL_GetTagMatrix(prog, &tag_matrix, e, tagindex, NULL);
	Matrix4x4_ToVectors(&tag_matrix, forward, left, up, origin);
	VectorCopy(forward, PRVM_clientglobalvector(v_forward));
	VectorScale(left, -1, PRVM_clientglobalvector(v_right));
	VectorCopy(up, PRVM_clientglobalvector(v_up));
	VectorCopy(origin, PRVM_G_VECTOR(OFS_RETURN));
	model = CL_GetModelFromEdict(e);
	VM_GenerateFrameGroupBlend(prog, e->priv.server->framegroupblend, e);
	VM_FrameBlendFromFrameGroupBlend(e->priv.server->frameblend, e->priv.server->framegroupblend, model, cl.time);
	VM_UpdateEdictSkeleton(prog, e, model, e->priv.server->frameblend);
	CL_GetExtendedTagInfo(prog, e, tagindex, &parentindex, &tagname, &tag_localmatrix);
	Matrix4x4_ToVectors(&tag_localmatrix, forward, left, up, origin);

	PRVM_clientglobalfloat(gettaginfo_parent) = parentindex;
	PRVM_clientglobalstring(gettaginfo_name) = tagname ? PRVM_SetTempString(prog, tagname) : 0;
	VectorCopy(forward, PRVM_clientglobalvector(gettaginfo_forward));
	VectorScale(left, -1, PRVM_clientglobalvector(gettaginfo_right));
	VectorCopy(up, PRVM_clientglobalvector(gettaginfo_up));
	VectorCopy(origin, PRVM_clientglobalvector(gettaginfo_offset));

	switch(returncode)
	{
		case 1:
			VM_Warning(prog, "gettagindex: can't affect world entity\n");
			break;
		case 2:
			VM_Warning(prog, "gettagindex: can't affect free entity\n");
			break;
		case 3:
			Con_DPrintf("CL_GetTagMatrix(entity #%i): null or non-precached model\n", PRVM_NUM_FOR_EDICT(e));
			break;
		case 4:
			Con_DPrintf("CL_GetTagMatrix(entity #%i): model has no tag with requested index %i\n", PRVM_NUM_FOR_EDICT(e), tagindex);
			break;
		case 5:
			Con_DPrintf("CL_GetTagMatrix(entity #%i): runaway loop at attachment chain\n", PRVM_NUM_FOR_EDICT(e));
			break;
	}
}

                                                                              

                      
                        
                                       
                      

                        
typedef struct vmparticletheme_s
{
	unsigned short typeindex;
	qboolean initialized;
	pblend_t blendmode;
	porientation_t orientation;
	int color1;
	int color2;
	int tex;
	float size;
	float sizeincrease;
	float alpha;
	float alphafade;
	float gravity;
	float bounce;
	float airfriction;
	float liquidfriction;
	float originjitter;
	float velocityjitter;
	qboolean qualityreduction;
	float lifetime;
	float stretch;
	int staincolor1;
	int staincolor2;
	int staintex;
	float stainalpha;
	float stainsize;
	float delayspawn;
	float delaycollision;
	float angle;
	float spin;
}vmparticletheme_t;

                   
typedef struct vmparticlespawner_s
{
	mempool_t			*pool;
	qboolean			initialized;
	qboolean			verified;
	vmparticletheme_t	*themes;
	int					max_themes;
}vmparticlespawner_t;

vmparticlespawner_t vmpartspawner;

                                  
static void VM_InitParticleSpawner (prvm_prog_t *prog, int maxthemes)
{
	                                             
	if (maxthemes < 4)
		maxthemes = 4;
	if (maxthemes > 2048)
		maxthemes = 2048;
	                                
	if (vmpartspawner.initialized)              
	{
		Mem_FreePool(&vmpartspawner.pool);
		memset(&vmpartspawner, 0, sizeof(vmparticlespawner_t));
	}
	vmpartspawner.pool = Mem_AllocPool("VMPARTICLESPAWNER", 0, NULL);
	vmpartspawner.themes = (vmparticletheme_t *)Mem_Alloc(vmpartspawner.pool, sizeof(vmparticletheme_t)*maxthemes);
	vmpartspawner.max_themes = maxthemes;
	vmpartspawner.initialized = true;
	vmpartspawner.verified = true;
}

                                         
static void VM_ResetParticleTheme (vmparticletheme_t *theme)
{
	theme->initialized = true;
	theme->typeindex = pt_static;
	theme->blendmode = PBLEND_ADD;
	theme->orientation = PARTICLE_BILLBOARD;
	theme->color1 = 0x808080;
	theme->color2 = 0xFFFFFF;
	theme->tex = 63;
	theme->size = 2;
	theme->sizeincrease = 0;
	theme->alpha = 256;
	theme->alphafade = 512;
	theme->gravity = 0.0f;
	theme->bounce = 0.0f;
	theme->airfriction = 1.0f;
	theme->liquidfriction = 4.0f;
	theme->originjitter = 0.0f;
	theme->velocityjitter = 0.0f;
	theme->qualityreduction = false;
	theme->lifetime = 4;
	theme->stretch = 1;
	theme->staincolor1 = -1;
	theme->staincolor2 = -1;
	theme->staintex = -1;
	theme->delayspawn = 0.0f;
	theme->delaycollision = 0.0f;
	theme->angle = 0.0f;
	theme->spin = 0.0f;
}

                               
static void VM_CL_ParticleThemeToGlobals(vmparticletheme_t *theme, prvm_prog_t *prog)
{
	PRVM_clientglobalfloat(particle_type) = theme->typeindex;
	PRVM_clientglobalfloat(particle_blendmode) = theme->blendmode;
	PRVM_clientglobalfloat(particle_orientation) = theme->orientation;
	                                                                            
	VectorSet(PRVM_clientglobalvector(particle_color1), (theme->color1 >> 16) & 0xFF, (theme->color1 >> 8) & 0xFF, (theme->color1 >> 0) & 0xFF);
	VectorSet(PRVM_clientglobalvector(particle_color2), (theme->color2 >> 16) & 0xFF, (theme->color2 >> 8) & 0xFF, (theme->color2 >> 0) & 0xFF);
	PRVM_clientglobalfloat(particle_tex) = (prvm_vec_t)theme->tex;
	PRVM_clientglobalfloat(particle_size) = theme->size;
	PRVM_clientglobalfloat(particle_sizeincrease) = theme->sizeincrease;
	PRVM_clientglobalfloat(particle_alpha) = theme->alpha/256;
	PRVM_clientglobalfloat(particle_alphafade) = theme->alphafade/256;
	PRVM_clientglobalfloat(particle_time) = theme->lifetime;
	PRVM_clientglobalfloat(particle_gravity) = theme->gravity;
	PRVM_clientglobalfloat(particle_bounce) = theme->bounce;
	PRVM_clientglobalfloat(particle_airfriction) = theme->airfriction;
	PRVM_clientglobalfloat(particle_liquidfriction) = theme->liquidfriction;
	PRVM_clientglobalfloat(particle_originjitter) = theme->originjitter;
	PRVM_clientglobalfloat(particle_velocityjitter) = theme->velocityjitter;
	PRVM_clientglobalfloat(particle_qualityreduction) = theme->qualityreduction;
	PRVM_clientglobalfloat(particle_stretch) = theme->stretch;
	VectorSet(PRVM_clientglobalvector(particle_staincolor1), ((int)theme->staincolor1 >> 16) & 0xFF, ((int)theme->staincolor1 >> 8) & 0xFF, ((int)theme->staincolor1 >> 0) & 0xFF);
	VectorSet(PRVM_clientglobalvector(particle_staincolor2), ((int)theme->staincolor2 >> 16) & 0xFF, ((int)theme->staincolor2 >> 8) & 0xFF, ((int)theme->staincolor2 >> 0) & 0xFF);
	PRVM_clientglobalfloat(particle_staintex) = (prvm_vec_t)theme->staintex;
	PRVM_clientglobalfloat(particle_stainalpha) = (prvm_vec_t)theme->stainalpha/256;
	PRVM_clientglobalfloat(particle_stainsize) = (prvm_vec_t)theme->stainsize;
	PRVM_clientglobalfloat(particle_delayspawn) = theme->delayspawn;
	PRVM_clientglobalfloat(particle_delaycollision) = theme->delaycollision;
	PRVM_clientglobalfloat(particle_angle) = theme->angle;
	PRVM_clientglobalfloat(particle_spin) = theme->spin;
}

                                
static void VM_CL_ParticleThemeFromGlobals(vmparticletheme_t *theme, prvm_prog_t *prog)
{
	theme->typeindex = (unsigned short)PRVM_clientglobalfloat(particle_type);
	theme->blendmode = (pblend_t)(int)PRVM_clientglobalfloat(particle_blendmode);
	theme->orientation = (porientation_t)(int)PRVM_clientglobalfloat(particle_orientation);
	theme->color1 = ((int)PRVM_clientglobalvector(particle_color1)[0] << 16) + ((int)PRVM_clientglobalvector(particle_color1)[1] << 8) + ((int)PRVM_clientglobalvector(particle_color1)[2]);
	theme->color2 = ((int)PRVM_clientglobalvector(particle_color2)[0] << 16) + ((int)PRVM_clientglobalvector(particle_color2)[1] << 8) + ((int)PRVM_clientglobalvector(particle_color2)[2]);
	theme->tex = (int)PRVM_clientglobalfloat(particle_tex);
	theme->size = PRVM_clientglobalfloat(particle_size);
	theme->sizeincrease = PRVM_clientglobalfloat(particle_sizeincrease);
	theme->alpha = PRVM_clientglobalfloat(particle_alpha)*256;
	theme->alphafade = PRVM_clientglobalfloat(particle_alphafade)*256;
	theme->lifetime = PRVM_clientglobalfloat(particle_time);
	theme->gravity = PRVM_clientglobalfloat(particle_gravity);
	theme->bounce = PRVM_clientglobalfloat(particle_bounce);
	theme->airfriction = PRVM_clientglobalfloat(particle_airfriction);
	theme->liquidfriction = PRVM_clientglobalfloat(particle_liquidfriction);
	theme->originjitter = PRVM_clientglobalfloat(particle_originjitter);
	theme->velocityjitter = PRVM_clientglobalfloat(particle_velocityjitter);
	theme->qualityreduction = PRVM_clientglobalfloat(particle_qualityreduction) != 0 ? true : false;
	theme->stretch = PRVM_clientglobalfloat(particle_stretch);
	theme->staincolor1 = ((int)PRVM_clientglobalvector(particle_staincolor1)[0])*65536 + (int)(PRVM_clientglobalvector(particle_staincolor1)[1])*256 + (int)(PRVM_clientglobalvector(particle_staincolor1)[2]);
	theme->staincolor2 = (int)(PRVM_clientglobalvector(particle_staincolor2)[0])*65536 + (int)(PRVM_clientglobalvector(particle_staincolor2)[1])*256 + (int)(PRVM_clientglobalvector(particle_staincolor2)[2]);
	theme->staintex =(int)PRVM_clientglobalfloat(particle_staintex);
	theme->stainalpha = PRVM_clientglobalfloat(particle_stainalpha)*256;
	theme->stainsize = PRVM_clientglobalfloat(particle_stainsize);
	theme->delayspawn = PRVM_clientglobalfloat(particle_delayspawn);
	theme->delaycollision = PRVM_clientglobalfloat(particle_delaycollision);
	theme->angle = PRVM_clientglobalfloat(particle_angle);
	theme->spin = PRVM_clientglobalfloat(particle_spin);
}

                                  
                                                
static void VM_CL_InitParticleSpawner (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNTRANGE(0, 1, VM_CL_InitParticleSpawner);
	VM_InitParticleSpawner(prog, (int)PRVM_G_FLOAT(OFS_PARM0));
	vmpartspawner.themes[0].initialized = true;
	VM_ResetParticleTheme(&vmpartspawner.themes[0]);
	PRVM_G_FLOAT(OFS_RETURN) = (vmpartspawner.verified == true) ? 1 : 0;
}

                       
static void VM_CL_ResetParticle (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(0, VM_CL_ResetParticle);
	if (vmpartspawner.verified == false)
	{
		VM_Warning(prog, "VM_CL_ResetParticle: particle spawner not initialized\n");
		return;
	}
	VM_CL_ParticleThemeToGlobals(&vmpartspawner.themes[0], prog);
}

                                     
static void VM_CL_ParticleTheme (prvm_prog_t *prog)
{
	int themenum;

	VM_SAFEPARMCOUNT(1, VM_CL_ParticleTheme);
	if (vmpartspawner.verified == false)
	{
		VM_Warning(prog, "VM_CL_ParticleTheme: particle spawner not initialized\n");
		return;
	}
	themenum = (int)PRVM_G_FLOAT(OFS_PARM0);
	if (themenum < 0 || themenum >= vmpartspawner.max_themes)
	{
		VM_Warning(prog, "VM_CL_ParticleTheme: bad theme number %i\n", themenum);
		VM_CL_ParticleThemeToGlobals(&vmpartspawner.themes[0], prog);
		return;
	}
	if (vmpartspawner.themes[themenum].initialized == false)
	{
		VM_Warning(prog, "VM_CL_ParticleTheme: theme #%i not exists\n", themenum);
		VM_CL_ParticleThemeToGlobals(&vmpartspawner.themes[0], prog);
		return;
	}
	                                   
	VM_CL_ParticleThemeToGlobals(&vmpartspawner.themes[themenum], prog);
}

                            
                                           
static void VM_CL_ParticleThemeSave (prvm_prog_t *prog)
{
	int themenum;

	VM_SAFEPARMCOUNTRANGE(0, 1, VM_CL_ParticleThemeSave);
	if (vmpartspawner.verified == false)
	{
		VM_Warning(prog, "VM_CL_ParticleThemeSave: particle spawner not initialized\n");
		return;
	}
	                                         
	if (prog->argc < 1)
	{
		for (themenum = 0; themenum < vmpartspawner.max_themes; themenum++)
			if (vmpartspawner.themes[themenum].initialized == false)
				break;
		if (themenum >= vmpartspawner.max_themes)
		{
			if (vmpartspawner.max_themes == 2048)
				VM_Warning(prog, "VM_CL_ParticleThemeSave: no free theme slots\n");
			else
				VM_Warning(prog, "VM_CL_ParticleThemeSave: no free theme slots, try initparticlespawner() with highter max_themes\n");
			PRVM_G_FLOAT(OFS_RETURN) = -1;
			return;
		}
		vmpartspawner.themes[themenum].initialized = true;
		VM_CL_ParticleThemeFromGlobals(&vmpartspawner.themes[themenum], prog);
		PRVM_G_FLOAT(OFS_RETURN) = themenum;
		return;
	}
	                        
	themenum = (int)PRVM_G_FLOAT(OFS_PARM0);
	if (themenum < 0 || themenum >= vmpartspawner.max_themes)
	{
		VM_Warning(prog, "VM_CL_ParticleThemeSave: bad theme number %i\n", themenum);
		return;
	}
	vmpartspawner.themes[themenum].initialized = true;
	VM_CL_ParticleThemeFromGlobals(&vmpartspawner.themes[themenum], prog);
}

                                         
static void VM_CL_ParticleThemeFree (prvm_prog_t *prog)
{
	int themenum;

	VM_SAFEPARMCOUNT(1, VM_CL_ParticleThemeFree);
	if (vmpartspawner.verified == false)
	{
		VM_Warning(prog, "VM_CL_ParticleThemeFree: particle spawner not initialized\n");
		return;
	}
	themenum = (int)PRVM_G_FLOAT(OFS_PARM0);
	              
	if (themenum <= 0 || themenum >= vmpartspawner.max_themes)
	{
		VM_Warning(prog, "VM_CL_ParticleThemeFree: bad theme number %i\n", themenum);
		return;
	}
	if (vmpartspawner.themes[themenum].initialized == false)
	{
		VM_Warning(prog, "VM_CL_ParticleThemeFree: theme #%i already freed\n", themenum);
		VM_CL_ParticleThemeToGlobals(&vmpartspawner.themes[0], prog);
		return;
	}
	             
	VM_ResetParticleTheme(&vmpartspawner.themes[themenum]);
	vmpartspawner.themes[themenum].initialized = false;
}

                                                        
                                      
static void VM_CL_SpawnParticle (prvm_prog_t *prog)
{
	vec3_t org, dir;
	vmparticletheme_t *theme;
	particle_t *part;
	int themenum;

	VM_SAFEPARMCOUNTRANGE(2, 3, VM_CL_SpawnParticle2);
	if (vmpartspawner.verified == false)
	{
		VM_Warning(prog, "VM_CL_SpawnParticle: particle spawner not initialized\n");
		PRVM_G_FLOAT(OFS_RETURN) = 0; 
		return;
	}
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), org);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), dir);
	
	if (prog->argc < 3)                       
	{
		part = CL_NewParticle(org,
			(unsigned short)PRVM_clientglobalfloat(particle_type),
			((int)PRVM_clientglobalvector(particle_color1)[0] << 16) + ((int)PRVM_clientglobalvector(particle_color1)[1] << 8) + ((int)PRVM_clientglobalvector(particle_color1)[2]),
			((int)PRVM_clientglobalvector(particle_color2)[0] << 16) + ((int)PRVM_clientglobalvector(particle_color2)[1] << 8) + ((int)PRVM_clientglobalvector(particle_color2)[2]),
			(int)PRVM_clientglobalfloat(particle_tex),
			PRVM_clientglobalfloat(particle_size),
			PRVM_clientglobalfloat(particle_sizeincrease),
			PRVM_clientglobalfloat(particle_alpha)*256,
			PRVM_clientglobalfloat(particle_alphafade)*256,
			PRVM_clientglobalfloat(particle_gravity),
			PRVM_clientglobalfloat(particle_bounce),
			org[0],
			org[1],
			org[2],
			dir[0],
			dir[1],
			dir[2],
			PRVM_clientglobalfloat(particle_airfriction),
			PRVM_clientglobalfloat(particle_liquidfriction),
			PRVM_clientglobalfloat(particle_originjitter),
			PRVM_clientglobalfloat(particle_velocityjitter),
			(PRVM_clientglobalfloat(particle_qualityreduction)) ? true : false,
			PRVM_clientglobalfloat(particle_time),
			PRVM_clientglobalfloat(particle_stretch),
			(pblend_t)(int)PRVM_clientglobalfloat(particle_blendmode),
			(porientation_t)(int)PRVM_clientglobalfloat(particle_orientation),
			(int)(PRVM_clientglobalvector(particle_staincolor1)[0])*65536 + (int)(PRVM_clientglobalvector(particle_staincolor1)[1])*256 + (int)(PRVM_clientglobalvector(particle_staincolor1)[2]),
			(int)(PRVM_clientglobalvector(particle_staincolor2)[0])*65536 + (int)(PRVM_clientglobalvector(particle_staincolor2)[1])*256 + (int)(PRVM_clientglobalvector(particle_staincolor2)[2]),
			(int)PRVM_clientglobalfloat(particle_staintex),
			PRVM_clientglobalfloat(particle_stainalpha)*256,
			PRVM_clientglobalfloat(particle_stainsize),
			PRVM_clientglobalfloat(particle_angle),
			PRVM_clientglobalfloat(particle_spin),
			NULL);
		if (!part)
		{
			PRVM_G_FLOAT(OFS_RETURN) = 0; 
			return;
		}
		if (PRVM_clientglobalfloat(particle_delayspawn))
			part->delayedspawn = cl.time + PRVM_clientglobalfloat(particle_delayspawn);
		                                                      
		                                                                                       
	}
	else                         
	{
		themenum = (int)PRVM_G_FLOAT(OFS_PARM2);
		if (themenum <= 0 || themenum >= vmpartspawner.max_themes)
		{
			VM_Warning(prog, "VM_CL_SpawnParticle: bad theme number %i\n", themenum);
			PRVM_G_FLOAT(OFS_RETURN) = 0; 
			return;
		}
		theme = &vmpartspawner.themes[themenum];
		part = CL_NewParticle(org,
			theme->typeindex,
			theme->color1,
			theme->color2,
			theme->tex,
			theme->size,
			theme->sizeincrease,
			theme->alpha,
			theme->alphafade,
			theme->gravity,
			theme->bounce,
			org[0],
			org[1],
			org[2],
			dir[0],
			dir[1],
			dir[2],
			theme->airfriction,
			theme->liquidfriction,
			theme->originjitter,
			theme->velocityjitter,
			theme->qualityreduction,
			theme->lifetime,
			theme->stretch,
			theme->blendmode,
			theme->orientation,
			theme->staincolor1,
			theme->staincolor2,
			theme->staintex,
			theme->stainalpha,
			theme->stainsize,
			theme->angle,
			theme->spin,
			NULL);
		if (!part)
		{
			PRVM_G_FLOAT(OFS_RETURN) = 0; 
			return;
		}
		if (theme->delayspawn)
			part->delayedspawn = cl.time + theme->delayspawn;
		                            
		                                                             
	}
	PRVM_G_FLOAT(OFS_RETURN) = 1; 
}

                                                                                                       
                                    
static void VM_CL_SpawnParticleDelayed (prvm_prog_t *prog)
{
	vec3_t org, dir;
	vmparticletheme_t *theme;
	particle_t *part;
	int themenum;

	VM_SAFEPARMCOUNTRANGE(4, 5, VM_CL_SpawnParticle2);
	if (vmpartspawner.verified == false)
	{
		VM_Warning(prog, "VM_CL_SpawnParticle: particle spawner not initialized\n");
		PRVM_G_FLOAT(OFS_RETURN) = 0; 
		return;
	}
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), org);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM1), dir);
	if (prog->argc < 5)                       
		part = CL_NewParticle(org,
			(unsigned short)PRVM_clientglobalfloat(particle_type),
			((int)PRVM_clientglobalvector(particle_color1)[0] << 16) + ((int)PRVM_clientglobalvector(particle_color1)[1] << 8) + ((int)PRVM_clientglobalvector(particle_color1)[2]),
			((int)PRVM_clientglobalvector(particle_color2)[0] << 16) + ((int)PRVM_clientglobalvector(particle_color2)[1] << 8) + ((int)PRVM_clientglobalvector(particle_color2)[2]),
			(int)PRVM_clientglobalfloat(particle_tex),
			PRVM_clientglobalfloat(particle_size),
			PRVM_clientglobalfloat(particle_sizeincrease),
			PRVM_clientglobalfloat(particle_alpha)*256,
			PRVM_clientglobalfloat(particle_alphafade)*256,
			PRVM_clientglobalfloat(particle_gravity),
			PRVM_clientglobalfloat(particle_bounce),
			org[0],
			org[1],
			org[2],
			dir[0],
			dir[1],
			dir[2],
			PRVM_clientglobalfloat(particle_airfriction),
			PRVM_clientglobalfloat(particle_liquidfriction),
			PRVM_clientglobalfloat(particle_originjitter),
			PRVM_clientglobalfloat(particle_velocityjitter),
			(PRVM_clientglobalfloat(particle_qualityreduction)) ? true : false,
			PRVM_clientglobalfloat(particle_time),
			PRVM_clientglobalfloat(particle_stretch),
			(pblend_t)(int)PRVM_clientglobalfloat(particle_blendmode),
			(porientation_t)(int)PRVM_clientglobalfloat(particle_orientation),
			((int)PRVM_clientglobalvector(particle_staincolor1)[0] << 16) + ((int)PRVM_clientglobalvector(particle_staincolor1)[1] << 8) + ((int)PRVM_clientglobalvector(particle_staincolor1)[2]),
			((int)PRVM_clientglobalvector(particle_staincolor2)[0] << 16) + ((int)PRVM_clientglobalvector(particle_staincolor2)[1] << 8) + ((int)PRVM_clientglobalvector(particle_staincolor2)[2]),
			(int)PRVM_clientglobalfloat(particle_staintex),
			PRVM_clientglobalfloat(particle_stainalpha)*256,
			PRVM_clientglobalfloat(particle_stainsize),
			PRVM_clientglobalfloat(particle_angle),
			PRVM_clientglobalfloat(particle_spin),
			NULL);
	else                   
	{
		themenum = (int)PRVM_G_FLOAT(OFS_PARM4);
		if (themenum <= 0 || themenum >= vmpartspawner.max_themes)
		{
			VM_Warning(prog, "VM_CL_SpawnParticle: bad theme number %i\n", themenum);
			PRVM_G_FLOAT(OFS_RETURN) = 0;  
			return;
		}
		theme = &vmpartspawner.themes[themenum];
		part = CL_NewParticle(org,
			theme->typeindex,
			theme->color1,
			theme->color2,
			theme->tex,
			theme->size,
			theme->sizeincrease,
			theme->alpha,
			theme->alphafade,
			theme->gravity,
			theme->bounce,
			org[0],
			org[1],
			org[2],
			dir[0],
			dir[1],
			dir[2],
			theme->airfriction,
			theme->liquidfriction,
			theme->originjitter,
			theme->velocityjitter,
			theme->qualityreduction,
			theme->lifetime,
			theme->stretch,
			theme->blendmode,
			theme->orientation,
			theme->staincolor1,
			theme->staincolor2,
			theme->staintex,
			theme->stainalpha,
			theme->stainsize,
			theme->angle,
			theme->spin,
			NULL);
	}
	if (!part) 
	{ 
		PRVM_G_FLOAT(OFS_RETURN) = 0; 
		return; 
	}
	part->delayedspawn = cl.time + PRVM_G_FLOAT(OFS_PARM2);
	                                                              
	PRVM_G_FLOAT(OFS_RETURN) = 0;
}

                      
                            
                      

                                                   
                                                       
                               
                                                         
static void VM_CL_GetEntity (prvm_prog_t *prog)
{
	int entnum, fieldnum;
	vec3_t forward, left, up, org;
	VM_SAFEPARMCOUNT(2, VM_CL_GetEntityVec);

	entnum = PRVM_G_FLOAT(OFS_PARM0);
	if (entnum < 0 || entnum >= cl.num_entities)
	{
		PRVM_G_FLOAT(OFS_RETURN) = 0;
		return;
	}
	fieldnum = PRVM_G_FLOAT(OFS_PARM1);
	switch(fieldnum)
	{
		case 0:                
			PRVM_G_FLOAT(OFS_RETURN) = cl.entities_active[entnum];
			break;
		case 1:          
			Matrix4x4_OriginFromMatrix(&cl.entities[entnum].render.matrix, org);
			VectorCopy(org, PRVM_G_VECTOR(OFS_RETURN));
			break; 
		case 2:           
			Matrix4x4_ToVectors(&cl.entities[entnum].render.matrix, forward, left, up, org);
			VectorCopy(forward, PRVM_G_VECTOR(OFS_RETURN));
			break;
		case 3:         
			Matrix4x4_ToVectors(&cl.entities[entnum].render.matrix, forward, left, up, org);
			VectorNegate(left, PRVM_G_VECTOR(OFS_RETURN));
			break;
		case 4:      
			Matrix4x4_ToVectors(&cl.entities[entnum].render.matrix, forward, left, up, org);
			VectorCopy(up, PRVM_G_VECTOR(OFS_RETURN));
			break;
		case 5:         
			PRVM_G_FLOAT(OFS_RETURN) = Matrix4x4_ScaleFromMatrix(&cl.entities[entnum].render.matrix);
			break;	
		case 6:                                     
			Matrix4x4_ToVectors(&cl.entities[entnum].render.matrix, forward, left, up, org);
			VectorCopy(forward, PRVM_clientglobalvector(v_forward));
			VectorNegate(left, PRVM_clientglobalvector(v_right));
			VectorCopy(up, PRVM_clientglobalvector(v_up));
			VectorCopy(org, PRVM_G_VECTOR(OFS_RETURN));
			break;	
		case 7:         
			PRVM_G_FLOAT(OFS_RETURN) = cl.entities[entnum].render.alpha;
			break;	
		case 8:            
			VectorCopy(cl.entities[entnum].render.colormod, PRVM_G_VECTOR(OFS_RETURN));
			break;
		case 9:                  
			VectorCopy(cl.entities[entnum].render.colormap_pantscolor, PRVM_G_VECTOR(OFS_RETURN));
			break;
		case 10:                  
			VectorCopy(cl.entities[entnum].render.colormap_shirtcolor, PRVM_G_VECTOR(OFS_RETURN));
			break;
		case 11:           
			PRVM_G_FLOAT(OFS_RETURN) = cl.entities[entnum].render.skinnum;
			break;	
		case 12:        
			VectorCopy(cl.entities[entnum].render.mins, PRVM_G_VECTOR(OFS_RETURN));		
			break;	
		case 13:        
			VectorCopy(cl.entities[entnum].render.maxs, PRVM_G_VECTOR(OFS_RETURN));		
			break;	
		case 14:          
			Matrix4x4_OriginFromMatrix(&cl.entities[entnum].render.matrix, org);
			VectorAdd(cl.entities[entnum].render.mins, org, PRVM_G_VECTOR(OFS_RETURN));		
			break;	
		case 15:          
			Matrix4x4_OriginFromMatrix(&cl.entities[entnum].render.matrix, org);
			VectorAdd(cl.entities[entnum].render.maxs, org, PRVM_G_VECTOR(OFS_RETURN));		
			break;
		case 16:         
			VectorMA(cl.entities[entnum].render.render_modellight_ambient, 0.5, cl.entities[entnum].render.render_modellight_diffuse, PRVM_G_VECTOR(OFS_RETURN));
			break;	
		default:
			PRVM_G_FLOAT(OFS_RETURN) = 0;
			break;
	}
}

                      
                      
                      

                                    
                                         
                                                                              
         
static void VM_CL_R_RenderScene (prvm_prog_t *prog)
{
	double t = Sys_DirtyTime();
	vmpolygons_t *polys = &prog->vmpolygons;
	VM_SAFEPARMCOUNT(0, VM_CL_R_RenderScene);

	                   
	if(r_refdef.view.ismain)
	{
		                    
		csqc_main_r_refdef_view = r_refdef.view;

		                                                                               
		r_refdef.view.ismain = false;
		csqc_original_r_refdef_view.ismain = false;
	}

	                                                                        
	                                    
	CL_UpdateViewEntities();
	CL_UpdateEntityShading();

	                  
	R_RenderView();

	polys->num_vertices = polys->num_triangles = 0;

	                                                                                           
	t = Sys_DirtyTime() - t;if (t < 0 || t >= 1800) t = 0;
	prog->functions[PRVM_clientfunction(CSQC_UpdateView)].totaltime -= t;
}

static void VM_ResizePolygons(vmpolygons_t *polys)
{
	float *oldvertex3f = polys->data_vertex3f;
	float *oldcolor4f = polys->data_color4f;
	float *oldtexcoord2f = polys->data_texcoord2f;
	vmpolygons_triangle_t *oldtriangles = polys->data_triangles;
	unsigned short *oldsortedelement3s = polys->data_sortedelement3s;
	polys->max_vertices = min(polys->max_triangles*3, 65536);
	polys->data_vertex3f = (float *)Mem_Alloc(polys->pool, polys->max_vertices*sizeof(float[3]));
	polys->data_color4f = (float *)Mem_Alloc(polys->pool, polys->max_vertices*sizeof(float[4]));
	polys->data_texcoord2f = (float *)Mem_Alloc(polys->pool, polys->max_vertices*sizeof(float[2]));
	polys->data_triangles = (vmpolygons_triangle_t *)Mem_Alloc(polys->pool, polys->max_triangles*sizeof(vmpolygons_triangle_t));
	polys->data_sortedelement3s = (unsigned short *)Mem_Alloc(polys->pool, polys->max_triangles*sizeof(unsigned short[3]));
	if (polys->num_vertices)
	{
		memcpy(polys->data_vertex3f, oldvertex3f, polys->num_vertices*sizeof(float[3]));
		memcpy(polys->data_color4f, oldcolor4f, polys->num_vertices*sizeof(float[4]));
		memcpy(polys->data_texcoord2f, oldtexcoord2f, polys->num_vertices*sizeof(float[2]));
	}
	if (polys->num_triangles)
	{
		memcpy(polys->data_triangles, oldtriangles, polys->num_triangles*sizeof(vmpolygons_triangle_t));
		memcpy(polys->data_sortedelement3s, oldsortedelement3s, polys->num_triangles*sizeof(unsigned short[3]));
	}
	if (oldvertex3f)
		Mem_Free(oldvertex3f);
	if (oldcolor4f)
		Mem_Free(oldcolor4f);
	if (oldtexcoord2f)
		Mem_Free(oldtexcoord2f);
	if (oldtriangles)
		Mem_Free(oldtriangles);
	if (oldsortedelement3s)
		Mem_Free(oldsortedelement3s);
}

static void VM_InitPolygons (vmpolygons_t* polys)
{
	memset(polys, 0, sizeof(*polys));
	polys->pool = Mem_AllocPool("VMPOLY", 0, NULL);
	polys->max_triangles = 1024;
	VM_ResizePolygons(polys);
	polys->initialized = true;
}

static void VM_DrawPolygonCallback (const entity_render_t *ent, const rtlight_t *rtlight, int numsurfaces, int *surfacelist)
{
	int surfacelistindex;
	vmpolygons_t *polys = (vmpolygons_t *)ent;
                              
	R_EntityMatrix(&identitymatrix);
	GL_CullFace(GL_NONE);
	GL_DepthTest(true);                                                  
	GL_DepthRange(0, 1);
	R_Mesh_PrepareVertices_Generic_Arrays(polys->num_vertices, polys->data_vertex3f, polys->data_color4f, polys->data_texcoord2f);

	for (surfacelistindex = 0;surfacelistindex < numsurfaces;)
	{
		int numtriangles = 0;
		rtexture_t *tex = polys->data_triangles[surfacelist[surfacelistindex]].texture;
		int drawflag = polys->data_triangles[surfacelist[surfacelistindex]].drawflag;
		DrawQ_ProcessDrawFlag(drawflag, polys->data_triangles[surfacelist[surfacelistindex]].hasalpha);
		R_SetupShader_Generic(tex, NULL, GL_MODULATE, 1, false, false, false);
		numtriangles = 0;
		for (;surfacelistindex < numsurfaces;surfacelistindex++)
		{
			if (polys->data_triangles[surfacelist[surfacelistindex]].texture != tex || polys->data_triangles[surfacelist[surfacelistindex]].drawflag != drawflag)
				break;
			VectorCopy(polys->data_triangles[surfacelist[surfacelistindex]].elements, polys->data_sortedelement3s + 3*numtriangles);
			numtriangles++;
		}
		R_Mesh_Draw(0, polys->num_vertices, 0, numtriangles, NULL, NULL, 0, polys->data_sortedelement3s, NULL, 0);
	}
}

static void VMPolygons_Store(vmpolygons_t *polys)
{
	qboolean hasalpha;
	int i;

	                          
	hasalpha = polys->begin_texture_hasalpha;
	for(i = 0; !hasalpha && (i < polys->begin_vertices); ++i)
		if(polys->begin_color[i][3] < 1)
			hasalpha = true;

	if (polys->begin_draw2d)
	{
		                                     
		drawqueuemesh_t mesh;
		mesh.texture = polys->begin_texture;
		mesh.num_vertices = polys->begin_vertices;
		mesh.num_triangles = polys->begin_vertices-2;
		mesh.data_element3i = polygonelement3i;
		mesh.data_element3s = polygonelement3s;
		mesh.data_vertex3f = polys->begin_vertex[0];
		mesh.data_color4f = polys->begin_color[0];
		mesh.data_texcoord2f = polys->begin_texcoord[0];
		DrawQ_Mesh(&mesh, polys->begin_drawflag, hasalpha);
	}
	else
	{
		                                                                 
		if (polys->max_triangles < polys->num_triangles + polys->begin_vertices-2)
		{
			while (polys->max_triangles < polys->num_triangles + polys->begin_vertices-2)
				polys->max_triangles *= 2;
			VM_ResizePolygons(polys);
		}
		if (polys->num_vertices + polys->begin_vertices <= polys->max_vertices)
		{
			                        
			                                                                                         
			                                                                    
			         
			memcpy(polys->data_vertex3f + polys->num_vertices * 3, polys->begin_vertex[0], polys->begin_vertices * sizeof(float[3]));
			memcpy(polys->data_color4f + polys->num_vertices * 4, polys->begin_color[0], polys->begin_vertices * sizeof(float[4]));
			memcpy(polys->data_texcoord2f + polys->num_vertices * 2, polys->begin_texcoord[0], polys->begin_vertices * sizeof(float[2]));
			for (i = 0;i < polys->begin_vertices-2;i++)
			{
				polys->data_triangles[polys->num_triangles].texture = polys->begin_texture;
				polys->data_triangles[polys->num_triangles].drawflag = polys->begin_drawflag;
				polys->data_triangles[polys->num_triangles].elements[0] = polys->num_vertices;
				polys->data_triangles[polys->num_triangles].elements[1] = polys->num_vertices + i+1;
				polys->data_triangles[polys->num_triangles].elements[2] = polys->num_vertices + i+2;
				polys->data_triangles[polys->num_triangles].hasalpha = hasalpha;
				polys->num_triangles++;
			}
			polys->num_vertices += polys->begin_vertices;
		}
	}
	polys->begin_active = false;
}

                                                                                           
                                    
void VM_CL_AddPolygonsToMeshQueue (prvm_prog_t *prog)
{
	int i;
	vmpolygons_t *polys = &prog->vmpolygons;
	vec3_t center;

	                                                                                             
	if( !prog )
		return;

	if (!polys->num_triangles)
		return;

	for (i = 0;i < polys->num_triangles;i++)
	{
		VectorMAMAM(1.0f / 3.0f, polys->data_vertex3f + 3*polys->data_triangles[i].elements[0], 1.0f / 3.0f, polys->data_vertex3f + 3*polys->data_triangles[i].elements[1], 1.0f / 3.0f, polys->data_vertex3f + 3*polys->data_triangles[i].elements[2], center);
		R_MeshQueue_AddTransparent(TRANSPARENTSORT_DISTANCE, center, VM_DrawPolygonCallback, (entity_render_t *)polys, i, NULL);
	}

	                                                                  
                                                                                                        
}

                                                                   
static void VM_CL_R_PolygonBegin (prvm_prog_t *prog)
{
	const char		*picname;
	skinframe_t     *sf;
	vmpolygons_t *polys = &prog->vmpolygons;
	int tf;

	                                                                       
	                                                                         
	                               

	VM_SAFEPARMCOUNTRANGE(2, 3, VM_CL_R_PolygonBegin);

	if (!polys->initialized)
		VM_InitPolygons(polys);
	if (polys->begin_active)
	{
		VM_Warning(prog, "VM_CL_R_PolygonBegin: called twice without VM_CL_R_PolygonBegin after first\n");
		return;
	}
	picname = PRVM_G_STRING(OFS_PARM0);

	sf = NULL;
	if(*picname)
	{
		tf = TEXF_ALPHA;
		if((int)PRVM_G_FLOAT(OFS_PARM1) & DRAWFLAG_MIPMAP)
			tf |= TEXF_MIPMAP;

		do
		{
			sf = R_SkinFrame_FindNextByName(sf, picname);
		}
		while(sf && sf->textureflags != tf);

		if(!sf || !sf->base)
			sf = R_SkinFrame_LoadExternal(picname, tf, true);

		if(sf)
			R_SkinFrame_MarkUsed(sf);
	}

	polys->begin_texture = (sf && sf->base) ? sf->base : r_texture_white;
	polys->begin_texture_hasalpha = (sf && sf->base) ? sf->hasalpha : false;
	polys->begin_drawflag = (int)PRVM_G_FLOAT(OFS_PARM1) & DRAWFLAG_MASK;
	polys->begin_vertices = 0;
	polys->begin_active = true;
	polys->begin_draw2d = (prog->argc >= 3 ? (int)PRVM_G_FLOAT(OFS_PARM2) : r_refdef.draw2dstage);
}

                                                                             
static void VM_CL_R_PolygonVertex (prvm_prog_t *prog)
{
	vmpolygons_t *polys = &prog->vmpolygons;

	VM_SAFEPARMCOUNT(4, VM_CL_R_PolygonVertex);

	if (!polys->begin_active)
	{
		VM_Warning(prog, "VM_CL_R_PolygonVertex: VM_CL_R_PolygonBegin wasn't called\n");
		return;
	}

	if (polys->begin_vertices >= VMPOLYGONS_MAXPOINTS)
	{
		VM_Warning(prog, "VM_CL_R_PolygonVertex: may have %i vertices max\n", VMPOLYGONS_MAXPOINTS);
		return;
	}

	polys->begin_vertex[polys->begin_vertices][0] = PRVM_G_VECTOR(OFS_PARM0)[0];
	polys->begin_vertex[polys->begin_vertices][1] = PRVM_G_VECTOR(OFS_PARM0)[1];
	polys->begin_vertex[polys->begin_vertices][2] = PRVM_G_VECTOR(OFS_PARM0)[2];
	polys->begin_texcoord[polys->begin_vertices][0] = PRVM_G_VECTOR(OFS_PARM1)[0];
	polys->begin_texcoord[polys->begin_vertices][1] = PRVM_G_VECTOR(OFS_PARM1)[1];
	polys->begin_color[polys->begin_vertices][0] = PRVM_G_VECTOR(OFS_PARM2)[0];
	polys->begin_color[polys->begin_vertices][1] = PRVM_G_VECTOR(OFS_PARM2)[1];
	polys->begin_color[polys->begin_vertices][2] = PRVM_G_VECTOR(OFS_PARM2)[2];
	polys->begin_color[polys->begin_vertices][3] = PRVM_G_FLOAT(OFS_PARM3);
	polys->begin_vertices++;
}

                     
static void VM_CL_R_PolygonEnd (prvm_prog_t *prog)
{
	vmpolygons_t *polys = &prog->vmpolygons;

	VM_SAFEPARMCOUNT(0, VM_CL_R_PolygonEnd);
	if (!polys->begin_active)
	{
		VM_Warning(prog, "VM_CL_R_PolygonEnd: VM_CL_R_PolygonBegin wasn't called\n");
		return;
	}
	polys->begin_active = false;
	if (polys->begin_vertices >= 3)
		VMPolygons_Store(polys);
	else
		VM_Warning(prog, "VM_CL_R_PolygonEnd: %i vertices isn't a good choice\n", polys->begin_vertices);
}

  
             
              

                                                                         
                   

             
  
static qboolean CL_CheckBottom (prvm_edict_t *ent)
{
	prvm_prog_t *prog = CLVM_prog;
	vec3_t	mins, maxs, start, stop;
	trace_t	trace;
	int		x, y;
	float	mid, bottom;

	VectorAdd (PRVM_clientedictvector(ent, origin), PRVM_clientedictvector(ent, mins), mins);
	VectorAdd (PRVM_clientedictvector(ent, origin), PRVM_clientedictvector(ent, maxs), maxs);

                                                                       
                          
                                                
	start[2] = mins[2] - 1;
	for	(x=0 ; x<=1 ; x++)
		for	(y=0 ; y<=1 ; y++)
		{
			start[0] = x ? maxs[0] : mins[0];
			start[1] = y ? maxs[1] : mins[1];
			if (!(CL_PointSuperContents(start) & (SUPERCONTENTS_SOLID | SUPERCONTENTS_BODY)))
				goto realcheck;
		}

	return true;		                  

realcheck:
  
                       
  
	start[2] = mins[2];

                                               
	start[0] = stop[0] = (mins[0] + maxs[0])*0.5;
	start[1] = stop[1] = (mins[1] + maxs[1])*0.5;
	stop[2] = start[2] - 2*sv_stepheight.value;
	trace = CL_TraceLine(start, stop, MOVE_NOMONSTERS, ent, CL_GenericHitSuperContentsMask(ent), 0, 0, collision_extendmovelength.value, true, false, NULL, true, false);

	if (trace.fraction == 1.0)
		return false;
	mid = bottom = trace.endpos[2];

                                                
	for	(x=0 ; x<=1 ; x++)
		for	(y=0 ; y<=1 ; y++)
		{
			start[0] = stop[0] = x ? maxs[0] : mins[0];
			start[1] = stop[1] = y ? maxs[1] : mins[1];

			trace = CL_TraceLine(start, stop, MOVE_NOMONSTERS, ent, CL_GenericHitSuperContentsMask(ent), 0, 0, collision_extendmovelength.value, true, false, NULL, true, false);

			if (trace.fraction != 1.0 && trace.endpos[2] > bottom)
				bottom = trace.endpos[2];
			if (trace.fraction == 1.0 || mid - trace.endpos[2] > sv_stepheight.value)
				return false;
		}

	return true;
}

  
             
           

                               
                                                                      
                                               
             
  
static qboolean CL_movestep (prvm_edict_t *ent, vec3_t move, qboolean relink, qboolean noenemy, qboolean settrace)
{
	prvm_prog_t *prog = CLVM_prog;
	float		dz;
	vec3_t		oldorg, neworg, end, traceendpos;
	vec3_t		mins, maxs, start;
	trace_t		trace;
	int			i, svent;
	prvm_edict_t		*enemy;

               
	VectorCopy(PRVM_clientedictvector(ent, mins), mins);
	VectorCopy(PRVM_clientedictvector(ent, maxs), maxs);
	VectorCopy (PRVM_clientedictvector(ent, origin), oldorg);
	VectorAdd (PRVM_clientedictvector(ent, origin), move, neworg);

                                
	if ( (int)PRVM_clientedictfloat(ent, flags) & (FL_SWIM | FL_FLY) )
	{
	                                                      
		for (i=0 ; i<2 ; i++)
		{
			VectorAdd (PRVM_clientedictvector(ent, origin), move, neworg);
			enemy = PRVM_PROG_TO_EDICT(PRVM_clientedictedict(ent, enemy));
			if (i == 0 && enemy != prog->edicts)
			{
				dz = PRVM_clientedictvector(ent, origin)[2] - PRVM_clientedictvector(PRVM_PROG_TO_EDICT(PRVM_clientedictedict(ent, enemy)), origin)[2];
				if (dz > 40)
					neworg[2] -= 8;
				if (dz < 30)
					neworg[2] += 8;
			}
			VectorCopy(PRVM_clientedictvector(ent, origin), start);
			trace = CL_TraceBox(start, mins, maxs, neworg, MOVE_NORMAL, ent, CL_GenericHitSuperContentsMask(ent), 0, 0, collision_extendmovelength.value, true, true, &svent, true);
			if (settrace)
				CL_VM_SetTraceGlobals(prog, &trace, svent);

			if (trace.fraction == 1)
			{
				VectorCopy(trace.endpos, traceendpos);
				if (((int)PRVM_clientedictfloat(ent, flags) & FL_SWIM) && !(CL_PointSuperContents(traceendpos) & SUPERCONTENTS_LIQUIDSMASK))
					return false;	                          

				VectorCopy (traceendpos, PRVM_clientedictvector(ent, origin));
				if (relink)
					CL_LinkEdict(ent);
				return true;
			}

			if (enemy == prog->edicts)
				break;
		}

		return false;
	}

                                                         
	neworg[2] += sv_stepheight.value;
	VectorCopy (neworg, end);
	end[2] -= sv_stepheight.value*2;

	trace = CL_TraceBox(neworg, mins, maxs, end, MOVE_NORMAL, ent, CL_GenericHitSuperContentsMask(ent), 0, 0, collision_extendmovelength.value, true, true, &svent, true);
	if (settrace)
		CL_VM_SetTraceGlobals(prog, &trace, svent);

	if (trace.startsolid)
	{
		neworg[2] -= sv_stepheight.value;
		trace = CL_TraceBox(neworg, mins, maxs, end, MOVE_NORMAL, ent, CL_GenericHitSuperContentsMask(ent), 0, 0, collision_extendmovelength.value, true, true, &svent, true);
		if (settrace)
			CL_VM_SetTraceGlobals(prog, &trace, svent);
		if (trace.startsolid)
			return false;
	}
	if (trace.fraction == 1)
	{
	                                                          
		if ( (int)PRVM_clientedictfloat(ent, flags) & FL_PARTIALGROUND )
		{
			VectorAdd (PRVM_clientedictvector(ent, origin), move, PRVM_clientedictvector(ent, origin));
			if (relink)
				CL_LinkEdict(ent);
			PRVM_clientedictfloat(ent, flags) = (int)PRVM_clientedictfloat(ent, flags) & ~FL_ONGROUND;
			return true;
		}

		return false;		                     
	}

                                               
	VectorCopy (trace.endpos, PRVM_clientedictvector(ent, origin));

	if (!CL_CheckBottom (ent))
	{
		if ( (int)PRVM_clientedictfloat(ent, flags) & FL_PARTIALGROUND )
		{	                                                        
			                           
			if (relink)
				CL_LinkEdict(ent);
			return true;
		}
		VectorCopy (oldorg, PRVM_clientedictvector(ent, origin));
		return false;
	}

	if ( (int)PRVM_clientedictfloat(ent, flags) & FL_PARTIALGROUND )
		PRVM_clientedictfloat(ent, flags) = (int)PRVM_clientedictfloat(ent, flags) & ~FL_PARTIALGROUND;

	PRVM_clientedictedict(ent, groundentity) = PRVM_EDICT_TO_PROG(trace.ent);

                 
	if (relink)
		CL_LinkEdict(ent);
	return true;
}

  
               
              

                                                 
               
  
static void VM_CL_walkmove (prvm_prog_t *prog)
{
	prvm_edict_t	*ent;
	float	yaw, dist;
	vec3_t	move;
	mfunction_t	*oldf;
	int 	oldself;
	qboolean	settrace;

	VM_SAFEPARMCOUNTRANGE(2, 3, VM_CL_walkmove);

	                                     
	PRVM_G_FLOAT(OFS_RETURN) = 0;

	ent = PRVM_PROG_TO_EDICT(PRVM_clientglobaledict(self));
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

	if ( !( (int)PRVM_clientedictfloat(ent, flags) & (FL_ONGROUND|FL_FLY|FL_SWIM) ) )
		return;

	yaw = yaw*M_PI*2 / 360;

	move[0] = cos(yaw)*dist;
	move[1] = sin(yaw)*dist;
	move[2] = 0;

                                                               
	oldf = prog->xfunction;
	oldself = PRVM_clientglobaledict(self);

	PRVM_G_FLOAT(OFS_RETURN) = CL_movestep(ent, move, true, false, settrace);


                        
	prog->xfunction = oldf;
	PRVM_clientglobaledict(self) = oldself;
}

  
               
               

                            
               
  
static void VM_CL_serverkey(prvm_prog_t *prog)
{
	char string[VM_STRINGTEMP_LENGTH];
	VM_SAFEPARMCOUNT(1, VM_CL_serverkey);
	InfoString_GetValue(cl.qw_serverinfo, PRVM_G_STRING(OFS_PARM0), string, sizeof(string));
	PRVM_G_INT(OFS_RETURN) = PRVM_SetTempString(prog, string);
}

  
                 
              

                                        
                                  

                                                     
                 
  
static void VM_CL_checkpvs (prvm_prog_t *prog)
{
	vec3_t viewpos;
	prvm_edict_t *viewee;
	vec3_t mi, ma;
#if 1
	unsigned char *pvs;
#else
	int fatpvsbytes;
	unsigned char fatpvs[MAX_MAP_LEAFS/8];
#endif

	VM_SAFEPARMCOUNT(2, VM_SV_checkpvs);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), viewpos);
	viewee = PRVM_G_EDICT(OFS_PARM1);

	if(viewee->priv.required->free)
	{
		VM_Warning(prog, "checkpvs: can not check free entity\n");
		PRVM_G_FLOAT(OFS_RETURN) = 4;
		return;
	}

	VectorAdd(PRVM_serveredictvector(viewee, origin), PRVM_serveredictvector(viewee, mins), mi);
	VectorAdd(PRVM_serveredictvector(viewee, origin), PRVM_serveredictvector(viewee, maxs), ma);

#if 1
	if(!cl.worldmodel || !cl.worldmodel->brush.GetPVS || !cl.worldmodel->brush.BoxTouchingPVS)
	{
		                                            
		PRVM_G_FLOAT(OFS_RETURN) = 3;
		return;
	}
	pvs = cl.worldmodel->brush.GetPVS(cl.worldmodel, viewpos);
	if(!pvs)
	{
		                                   
		PRVM_G_FLOAT(OFS_RETURN) = 2;
		return;
	}
	PRVM_G_FLOAT(OFS_RETURN) = cl.worldmodel->brush.BoxTouchingPVS(cl.worldmodel, pvs, mi, ma);
#else
	                                       
	if(!cl.worldmodel || !cl.worldmodel->brush.FatPVS || !cl.worldmodel->brush.BoxTouchingPVS)
	{
		                                            
		PRVM_G_FLOAT(OFS_RETURN) = 3;
		return;
	}
	fatpvsbytes = cl.worldmodel->brush.FatPVS(cl.worldmodel, viewpos, 8, fatpvs, sizeof(fatpvs), false);
	if(!fatpvsbytes)
	{
		                                   
		PRVM_G_FLOAT(OFS_RETURN) = 2;
		return;
	}
	PRVM_G_FLOAT(OFS_RETURN) = cl.worldmodel->brush.BoxTouchingPVS(cl.worldmodel, fatpvs, mi, ma);
#endif
}

                                                                                                                                                                                                                                                                                                                                                                 
static void VM_CL_skel_create(prvm_prog_t *prog)
{
	int modelindex = (int)PRVM_G_FLOAT(OFS_PARM0);
	dp_model_t *model = CL_GetModelByIndex(modelindex);
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
	prog->skeletons[i] = skeleton = (skeleton_t *)Mem_Alloc(cls.levelmempool, sizeof(skeleton_t) + model->num_bones * sizeof(matrix4x4_t));
	PRVM_G_FLOAT(OFS_RETURN) = i + 1;
	skeleton->model = model;
	skeleton->relativetransforms = (matrix4x4_t *)(skeleton+1);
	                                  
	for (i = 0;i < skeleton->model->num_bones;i++)
		skeleton->relativetransforms[i] = identitymatrix;
}

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     
static void VM_CL_skel_build(prvm_prog_t *prog)
{
	int skeletonindex = (int)PRVM_G_FLOAT(OFS_PARM0) - 1;
	skeleton_t *skeleton;
	prvm_edict_t *ed = PRVM_G_EDICT(OFS_PARM1);
	int modelindex = (int)PRVM_G_FLOAT(OFS_PARM2);
	float retainfrac = PRVM_G_FLOAT(OFS_PARM3);
	int firstbone = PRVM_G_FLOAT(OFS_PARM4) - 1;
	int lastbone = PRVM_G_FLOAT(OFS_PARM5) - 1;
	dp_model_t *model = CL_GetModelByIndex(modelindex);
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
	VM_FrameBlendFromFrameGroupBlend(frameblend, framegroupblend, model, cl.time);
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

                                                                                                                                      
static void VM_CL_skel_get_numbones(prvm_prog_t *prog)
{
	int skeletonindex = (int)PRVM_G_FLOAT(OFS_PARM0) - 1;
	skeleton_t *skeleton;
	PRVM_G_FLOAT(OFS_RETURN) = 0;
	if (skeletonindex < 0 || skeletonindex >= MAX_EDICTS || !(skeleton = prog->skeletons[skeletonindex]))
		return;
	PRVM_G_FLOAT(OFS_RETURN) = skeleton->model->num_bones;
}

                                                                                                                                        
static void VM_CL_skel_get_bonename(prvm_prog_t *prog)
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

                                                                                                                                                                                                                                                                
static void VM_CL_skel_get_boneparent(prvm_prog_t *prog)
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

                                                                                                                                                                                                                                 
static void VM_CL_skel_find_bone(prvm_prog_t *prog)
{
	int skeletonindex = (int)PRVM_G_FLOAT(OFS_PARM0) - 1;
	const char *tagname = PRVM_G_STRING(OFS_PARM1);
	skeleton_t *skeleton;
	PRVM_G_FLOAT(OFS_RETURN) = 0;
	if (skeletonindex < 0 || skeletonindex >= MAX_EDICTS || !(skeleton = prog->skeletons[skeletonindex]))
		return;
	PRVM_G_FLOAT(OFS_RETURN) = Mod_Alias_GetTagIndexForName(skeleton->model, 0, tagname);
}

                                                                                                                                                                                                                                
static void VM_CL_skel_get_bonerel(prvm_prog_t *prog)
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

                                                                                                                                                                                                                   
static void VM_CL_skel_get_boneabs(prvm_prog_t *prog)
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

                                                                                                                                                                                                                                      
static void VM_CL_skel_set_bone(prvm_prog_t *prog)
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

                                                                                                                                                                                                                                                              
static void VM_CL_skel_mul_bone(prvm_prog_t *prog)
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

                                                                                                                                                                                                                                                                                      
static void VM_CL_skel_mul_bones(prvm_prog_t *prog)
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

                                                                                                                                                                                                                                                      
static void VM_CL_skel_copybones(prvm_prog_t *prog)
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

                                                                                                                                                                                                                 
static void VM_CL_skel_delete(prvm_prog_t *prog)
{
	int skeletonindex = (int)PRVM_G_FLOAT(OFS_PARM0) - 1;
	skeleton_t *skeleton;
	if (skeletonindex < 0 || skeletonindex >= MAX_EDICTS || !(skeleton = prog->skeletons[skeletonindex]))
		return;
	Mem_Free(skeleton);
	prog->skeletons[skeletonindex] = NULL;
}

                                                                                                                                                                                    
static void VM_CL_frameforname(prvm_prog_t *prog)
{
	int modelindex = (int)PRVM_G_FLOAT(OFS_PARM0);
	dp_model_t *model = CL_GetModelByIndex(modelindex);
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

                                                                                                                                                                                                                                                                                  
static void VM_CL_frameduration(prvm_prog_t *prog)
{
	int modelindex = (int)PRVM_G_FLOAT(OFS_PARM0);
	dp_model_t *model = CL_GetModelByIndex(modelindex);
	int framenum = (int)PRVM_G_FLOAT(OFS_PARM1);
	PRVM_G_FLOAT(OFS_RETURN) = 0;
	if (!model || !model->animscenes || framenum < 0 || framenum >= model->numframes)
		return;
	if (model->animscenes[framenum].framerate)
		PRVM_G_FLOAT(OFS_RETURN) = model->animscenes[framenum].framecount / model->animscenes[framenum].framerate;
}

static void VM_CL_RotateMoves(prvm_prog_t *prog)
{
	  
                                         
   
                                                                        
                                                     
   
                                                                           
                                                                      
                                    
   
                                                                    
                                                                           
                                                                     
                                                                          
                                                                       
                                                                       
                                                               
                                                                         
   
                                                                     
               
   
                                                                     
                                                                     
                                                                        
                        
      
	matrix4x4_t m;
	vec3_t v = {0, 0, 0};
	vec3_t a, x, y, z;
	VM_SAFEPARMCOUNT(1, VM_CL_RotateMoves);
	VectorCopy(PRVM_G_VECTOR(OFS_PARM0), a);
	AngleVectorsFLU(a, x, y, z);
	Matrix4x4_FromVectors(&m, x, y, z, v);
	CL_RotateMoves(&m);
}

                                            
static void VM_CL_loadcubemap(prvm_prog_t *prog)
{
	const char *name;

	VM_SAFEPARMCOUNT(1, VM_CL_loadcubemap);
	name = PRVM_G_STRING(OFS_PARM0);
	R_GetCubemap(name);
}

#define REFDEFFLAG_TELEPORTED 1
#define REFDEFFLAG_JUMPING 2
#define REFDEFFLAG_DEAD 4
#define REFDEFFLAG_INTERMISSION 8
static void VM_CL_V_CalcRefdef(prvm_prog_t *prog)
{
	matrix4x4_t entrendermatrix;
	vec3_t clviewangles;
	vec3_t clvelocity;
	qboolean teleported;
	qboolean clonground;
	qboolean clcmdjump;
	qboolean cldead;
	qboolean clintermission;
	float clstatsviewheight;
	prvm_edict_t *ent;
	int flags;

	VM_SAFEPARMCOUNT(2, VM_CL_V_CalcRefdef);
	ent = PRVM_G_EDICT(OFS_PARM0);
	flags = PRVM_G_FLOAT(OFS_PARM1);

	                                                                                                       
	CL_GetTagMatrix(prog, &entrendermatrix, ent, 0, NULL);

	VectorCopy(cl.csqc_viewangles, clviewangles);
	teleported = (flags & REFDEFFLAG_TELEPORTED) != 0;
	clonground = ((int)PRVM_clientedictfloat(ent, pmove_flags) & PMF_ONGROUND) != 0;
	clcmdjump = (flags & REFDEFFLAG_JUMPING) != 0;
	clstatsviewheight = PRVM_clientedictvector(ent, view_ofs)[2];
	cldead = (flags & REFDEFFLAG_DEAD) != 0;
	clintermission = (flags & REFDEFFLAG_INTERMISSION) != 0;
	VectorCopy(PRVM_clientedictvector(ent, velocity), clvelocity);

	V_CalcRefdefUsing(&entrendermatrix, clviewangles, teleported, clonground, clcmdjump, clstatsviewheight, cldead, clintermission, clvelocity);

	VectorCopy(cl.csqc_vieworiginfromengine, cl.csqc_vieworigin);
	VectorCopy(cl.csqc_viewanglesfromengine, cl.csqc_viewangles);
	CSQC_R_RecalcView();
}

                                                                              

                                                             
                    
                                 
                 
                                           
                      

prvm_builtin_t vm_cl_builtins[] = {
NULL,							                                          
VM_CL_makevectors,				                                          
VM_CL_setorigin,				                                                
VM_CL_setmodel,					                                               
VM_CL_setsize,					                                                            
NULL,							                                                               
VM_break,						                          
VM_random,						                            
VM_CL_sound,					                                                           
VM_normalize,					                                        
VM_error,						                                   
VM_objerror,					                                      
VM_vlen,						                                   
VM_vectoyaw,					                                       
VM_CL_spawn,					                             
VM_remove,						                                    
VM_CL_traceline,				                                                                                       
NULL,							                                   
VM_find,						                                                                   
VM_precache_sound,				                                            
VM_CL_precache_model,			                                            
NULL,							                                                          
VM_CL_findradius,				                                                       
NULL,							                                         
NULL,							                                                        
VM_dprint,						                                         
VM_ftos,						                                   
VM_vtos,						                                    
VM_coredump,					                              
VM_traceon,						                             
VM_traceoff,					                              
VM_eprint,						                                    
VM_CL_walkmove,					                                                                      
NULL,							              
VM_CL_droptofloor,				                                  
VM_CL_lightstyle,				                                                         
VM_rint,						                                  
VM_floor,						                                   
VM_ceil,						                                  
NULL,							              
VM_CL_checkbottom,				                                          
VM_CL_pointcontents,			                                            
NULL,							              
VM_fabs,						                                  
NULL,							                                                
VM_cvar,						                                   
VM_localcmd,					                                      
VM_nextent,						                                       
VM_CL_particle,					                                                                          
VM_changeyaw,					                               
NULL,							              
VM_vectoangles,					                                           
NULL,							                                                
NULL,							                                                
NULL,							                                                 
NULL,							                                                
NULL,							                                                 
NULL,							                                                 
NULL,							                                                   
NULL,							              
VM_sin,							                                               
VM_cos,							                                               
VM_sqrt,						                                                
VM_changepitch,					                                                       
VM_CL_tracetoss,				                                                                
VM_etos,						                                           
NULL,							              
NULL,							                                          
VM_precache_file,				                                             
VM_CL_makestatic,				                                        
NULL,							                                         
NULL,							              
VM_cvar_set,					                                                    
NULL,							                                                       
VM_CL_ambientsound,				                                                                                 
VM_CL_precache_model,			                                               
VM_precache_sound,				                                               
VM_precache_file,				                                              
NULL,							                                           
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
VM_CL_tracebox,					                                                                                                                    
VM_randomvec,					                                           
VM_CL_getlight,					                                                   
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
NULL,							                                                                        
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
VM_CL_checkpvs,					       
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
VM_CL_skel_create,				                                                                                                                                                                                                                                                                                                                                                                 
VM_CL_skel_build,				                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     
VM_CL_skel_get_numbones,		                                                                                                                                      
VM_CL_skel_get_bonename,		                                                                                                                                        
VM_CL_skel_get_boneparent,		                                                                                                                                                                                                                                                                 
VM_CL_skel_find_bone,			                                                                                                                                                                                                                                 
VM_CL_skel_get_bonerel,			                                                                                                                                                                                                                                
VM_CL_skel_get_boneabs,			                                                                                                                                                                                                                   
VM_CL_skel_set_bone,			                                                                                                                                                                                                                                      
VM_CL_skel_mul_bone,			                                                                                                                                                                                                                                                              
VM_CL_skel_mul_bones,			                                                                                                                                                                                                                                                                                      
VM_CL_skel_copybones,			                                                                                                                                                                                                                                                      
VM_CL_skel_delete,				                                                                                                                                                                                                                 
VM_CL_frameforname,				                                                                                                                                                                                    
VM_CL_frameduration,			                                                                                                                                                                                                                                                                                  
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
                       
VM_CL_R_ClearScene,				                                    
VM_CL_R_AddEntities,			                                               
VM_CL_R_AddEntity,				                                             
VM_CL_R_SetView,				                                                         
VM_CL_R_RenderScene,			                                     
VM_CL_R_AddDynamicLight,		                                                                                      
VM_CL_R_PolygonBegin,			                                                                                           
VM_CL_R_PolygonVertex,			                                                                                   
VM_CL_R_PolygonEnd,				                           
VM_CL_R_SetView,				                                                    
VM_CL_unproject,				                                                 
VM_CL_project,					                                               
NULL,							       
NULL,							       
NULL,							       
VM_drawline,					                                                                                   
VM_iscachedpic,					                                                 
VM_precache_pic,				                                                                 
VM_getimagesize,				                                                           
VM_freepic,						                                            
VM_drawcharacter,				                                                                                                                           
VM_drawstring,					                                                                                                                               
VM_drawpic,						                                                                                                                 
VM_drawfill,					                                                                                                    
VM_drawsetcliparea,				                                                                         
VM_drawresetcliparea,			                                    
VM_drawcolorcodedstring,		                                                                                                                              
VM_stringwidth,                                               
VM_drawsubpic,					                              
VM_drawrotpic,					                              
VM_CL_getstatf,					                                              
VM_CL_getstati,					                                              
VM_CL_getstats,					                                                    
VM_CL_setmodelindex,			                                                               
VM_CL_modelnameforindex,		                                                           
VM_CL_particleeffectnum,		                                                             
VM_CL_trailparticles,			                                                                                             
VM_CL_pointparticles,			                                                                                                  
VM_centerprint,					                                                  
VM_print,						                                                         
VM_keynumtostring,				                                                      
VM_stringtokeynum,				                                                       
VM_getkeybind,					                                                                   
VM_CL_setcursormode,			                                                     
VM_CL_getmousepos,				                                      
VM_CL_getinputstate,			                                                      
VM_CL_setsensitivityscale,		                                                       
VM_CL_runplayerphysics,			                                                  
VM_CL_getplayerkey,				                                                                            
VM_CL_isdemo,					                                 
VM_isserver,					                                   
VM_CL_setlistener,				                                                                                           
VM_CL_registercmd,				                                                       
VM_wasfreed,					                                                                                
VM_CL_serverkey,				                                               
VM_CL_videoplaying,				       
VM_findfont,					                                                      
VM_loadfont,					                                                                                                 
VM_CL_loadcubemap,				                                                      
NULL,							       
VM_CL_ReadByte,					                                   
VM_CL_ReadChar,					                                   
VM_CL_ReadShort,				                                    
VM_CL_ReadLong,					                                   
VM_CL_ReadCoord,				                                    
VM_CL_ReadAngle,				                                    
VM_CL_ReadString,				                                      
VM_CL_ReadFloat,				                                    
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
                              
VM_CL_copyentity,				                                                                  
NULL,							                                                                
VM_findchain,					                                                                     
VM_findchainfloat,				                                                                             
VM_CL_effect,					                                                                                                                   
VM_CL_te_blood,					                                                                               
VM_CL_te_bloodshower,			                                                                                                                        
VM_CL_te_explosionrgb,			                                                                           
VM_CL_te_particlecube,			                                                                                                                                                                       
VM_CL_te_particlerain,			                                                                                                                             
VM_CL_te_particlesnow,			                                                                                                                             
VM_CL_te_spark,					                                                                          
VM_CL_te_gunshotquad,			                                                         
VM_CL_te_spikequad,				                                                       
VM_CL_te_superspikequad,		                                                            
VM_CL_te_explosionquad,			                                                           
VM_CL_te_smallflash,			                                                         
VM_CL_te_customflash,			                                                                                                       
VM_CL_te_gunshot,				                                                                  
VM_CL_te_spike,					                                                                
VM_CL_te_superspike,			                                                                     
VM_CL_te_explosion,				                                                                    
VM_CL_te_tarexplosion,			                                                                       
VM_CL_te_wizspike,				                                                                   
VM_CL_te_knightspike,			                                                                      
VM_CL_te_lavasplash,			                                                                     
VM_CL_te_teleport,				                                                                   
VM_CL_te_explosion2,			                                                                                                          
VM_CL_te_lightning1,			                                                                                               
VM_CL_te_lightning2,			                                                                                               
VM_CL_te_lightning3,			                                                                                               
VM_CL_te_beam,					                                                                                         
VM_vectorvectors,				                                                            
VM_CL_te_plasmaburn,			                                                         
VM_getsurfacenumpoints,		                                                                       
VM_getsurfacepoint,			                                                                             
VM_getsurfacenormal,			                                                                     
VM_getsurfacetexture,		                                                                      
VM_getsurfacenearpoint,		                                                                        
VM_getsurfaceclippedpoint,	                                                                                     
NULL,							                                                                              
VM_tokenize,					                                                                
VM_argv,						                                                            
VM_CL_setattachment,			                                                                                               
VM_search_begin,				                                                                                                
VM_search_end,					                                                       
VM_search_getsize,				                                                            
VM_search_getfilename,			                                                                            
VM_cvar_string,					                                                        
VM_findflags,					                                                                                 
VM_findchainflags,				                                                                             
VM_CL_gettagindex,				                                                                        
VM_CL_gettaginfo,				                                                                        
NULL,							                                                        
NULL,							                                              
NULL,							                                                        
NULL,							                                                                                        
VM_CL_te_flamejet,				                                                                                
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
VM_CL_pointsound,				                                                                                                         
VM_strreplace,					                                                                                           
VM_strireplace,					                                                                                            
VM_getsurfacepointattribute,                                                                            
VM_gecko_create,					                                         
VM_gecko_destroy,					                                         
VM_gecko_navigate,				                                                      
VM_gecko_keyevent,				                                                                       
VM_gecko_movemouse,				                                                             
VM_gecko_resize,					                                                          
VM_gecko_get_texture_extent,	                                                      
VM_crc16,						                                                                              
VM_cvar_type,					                                                              
VM_numentityfields,				                                                          
VM_entityfieldname,				                                                                         
VM_entityfieldtype,				                                                                        
VM_getentityfieldstring,		                                                                                          
VM_putentityfieldstring,		                                                                                                   
VM_CL_ReadPicture,				                                    
VM_CL_boxparticles,				                                                                                                                                                                
VM_whichpack,					                                        
VM_CL_GetEntity,				                                                                                                                         
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
VM_keynumtostring,				                                           
VM_findkeysforcommand,			                                                                  
VM_CL_InitParticleSpawner,		                                                                          
VM_CL_ResetParticle,			                                                    
VM_CL_ParticleTheme,			                                                               
VM_CL_ParticleThemeSave,		                                                                                               
VM_CL_ParticleThemeFree,		                                                        
VM_CL_SpawnParticle,			                                                                                     
VM_CL_SpawnParticleDelayed,		                                                                                                                               
VM_loadfromdata,				       
VM_loadfromfile,				       
VM_CL_setpause,					                                                                
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
VM_findkeysforcommand,			                                                                  
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
VM_CL_getextresponse,			                                   
NULL,							       
NULL,							       
VM_sprintf,                                                               
VM_getsurfacenumtriangles,		                                                                               
VM_getsurfacetriangle,			                                                                                     
VM_setkeybind,						                                                                 
VM_getbindmaps,						                               
VM_setbindmaps,						                                   
NULL,							       
NULL,							       
NULL,							       
NULL,							       
NULL,							       
VM_CL_RotateMoves,					       
VM_digest_hex,						       
VM_CL_V_CalcRefdef,					                                                          
NULL,							       
VM_coverage,						       
NULL
};

const int vm_cl_numbuiltins = sizeof(vm_cl_builtins) / sizeof(prvm_builtin_t);

void VM_Polygons_Reset(prvm_prog_t *prog)
{
	vmpolygons_t *polys = &prog->vmpolygons;

	                                                                                                                               
	if(polys->initialized)
	{
		Mem_FreePool(&polys->pool);
		polys->initialized = false;
	}
}

void CLVM_init_cmd(prvm_prog_t *prog)
{
	VM_Cmd_Init(prog);
	VM_Polygons_Reset(prog);
}

void CLVM_reset_cmd(prvm_prog_t *prog)
{
	World_End(&cl.world);
	VM_Cmd_Reset(prog);
	VM_Polygons_Reset(prog);
}
