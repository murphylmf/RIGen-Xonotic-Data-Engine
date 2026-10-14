  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
            

#include "quakedef.h"
#include "progsvm.h"
#include "csprogs.h"

prvm_prog_t prvm_prog_list[PRVM_PROG_MAX];

int		prvm_type_size[8] = {1,sizeof(string_t)/4,1,3,1,1,sizeof(func_t)/4,sizeof(void *)/4};

prvm_eval_t prvm_badvalue;                               

cvar_t prvm_language = {CVAR_SAVE, "prvm_language", "", "when set, loads PROGSFILE.LANGUAGENAME.po and common.LANGUAGENAME.po for string translations; when set to dump, PROGSFILE.pot is written from the strings in the progs"};
                                                                                    
cvar_t prvm_traceqc = {0, "prvm_traceqc", "0", "prints every QuakeC statement as it is executed (only for really thorough debugging!)"};
                                                   
cvar_t prvm_statementprofiling = {0, "prvm_statementprofiling", "0", "counts how many times each QuakeC statement has been executed, these counts are displayed in prvm_printfunction output (if enabled)"};
cvar_t prvm_timeprofiling = {0, "prvm_timeprofiling", "0", "counts how long each function has been executed, these counts are displayed in prvm_profile output (if enabled)"};
cvar_t prvm_coverage = {0, "prvm_coverage", "0", "report and count coverage events (1: per-function, 2: coverage() builtin, 4: per-statement)"};
cvar_t prvm_backtraceforwarnings = {0, "prvm_backtraceforwarnings", "0", "print a backtrace for warnings too"};
cvar_t prvm_leaktest = {0, "prvm_leaktest", "0", "try to detect memory leaks in strings or entities"};
cvar_t prvm_leaktest_follow_targetname = {0, "prvm_leaktest_follow_targetname", "0", "if set, target/targetname links are considered when leak testing; this should normally not be required, as entities created during startup - e.g. info_notnull - are never considered leaky"};
cvar_t prvm_leaktest_ignore_classnames = {0, "prvm_leaktest_ignore_classnames", "", "classnames of entities to NOT leak check because they are found by find(world, classname, ...) but are actually spawned by QC code (NOT map entities)"};
cvar_t prvm_errordump = {0, "prvm_errordump", "0", "write a savegame on crash to crash-server.dmp"};
cvar_t prvm_breakpointdump = {0, "prvm_breakpointdump", "0", "write a savegame on breakpoint to breakpoint-server.dmp"};
cvar_t prvm_reuseedicts_startuptime = {0, "prvm_reuseedicts_startuptime", "2", "allows immediate re-use of freed entity slots during start of new level (value in seconds)"};
cvar_t prvm_reuseedicts_neverinsameframe = {0, "prvm_reuseedicts_neverinsameframe", "1", "never allows re-use of freed entity slots during same frame"};

static double prvm_reuseedicts_always_allow = 0;
qboolean prvm_runawaycheck = true;

                                                                              
                   

  
               
              
               
  
static void PRVM_MEM_Alloc(prvm_prog_t *prog)
{
	int i;

	                                              
	                            
	prog->max_edicts = bound(1 + prog->reserved_edicts, prog->max_edicts, prog->limit_edicts);
	prog->num_edicts = bound(1 + prog->reserved_edicts, prog->num_edicts, prog->max_edicts);

	                                                              
	prog->edictprivate_size = max(prog->edictprivate_size,(int)sizeof(prvm_edict_private_t));

	               
	prog->edicts = (prvm_edict_t *)Mem_Alloc(prog->progs_mempool,prog->limit_edicts * sizeof(prvm_edict_t));

	                            
	prog->edictprivate = Mem_Alloc(prog->progs_mempool, prog->max_edicts * prog->edictprivate_size);

	                     
	prog->entityfieldsarea = prog->entityfields * prog->max_edicts;
	prog->edictsfields = (prvm_vec_t *)Mem_Alloc(prog->progs_mempool, prog->entityfieldsarea * sizeof(prvm_vec_t));

	                     
	for(i = 0; i < prog->max_edicts; i++)
	{
		prog->edicts[i].priv.required = (prvm_edict_private_t *)((unsigned char  *)prog->edictprivate + i * prog->edictprivate_size);
		prog->edicts[i].fields.fp = prog->edictsfields + i * prog->entityfields;
	}
}

  
               
                       
               
  
void PRVM_MEM_IncreaseEdicts(prvm_prog_t *prog)
{
	int		i;

	if(prog->max_edicts >= prog->limit_edicts)
		return;

	prog->begin_increase_edicts(prog);

	                  
	prog->max_edicts = min(prog->max_edicts + 256, prog->limit_edicts);

	prog->entityfieldsarea = prog->entityfields * prog->max_edicts;
	prog->edictsfields = (prvm_vec_t*)Mem_Realloc(prog->progs_mempool, (void *)prog->edictsfields, prog->entityfieldsarea * sizeof(prvm_vec_t));
	prog->edictprivate = (void *)Mem_Realloc(prog->progs_mempool, (void *)prog->edictprivate, prog->max_edicts * prog->edictprivate_size);

	                      
	for(i = 0; i < prog->max_edicts; i++)
	{
		prog->edicts[i].priv.required  = (prvm_edict_private_t *)((unsigned char  *)prog->edictprivate + i * prog->edictprivate_size);
		prog->edicts[i].fields.fp = prog->edictsfields + i * prog->entityfields;
	}

	prog->end_increase_edicts(prog);
}

                                                                              
              

int PRVM_ED_FindFieldOffset(prvm_prog_t *prog, const char *field)
{
	ddef_t *d;
	d = PRVM_ED_FindField(prog, field);
	if (!d)
		return -1;
	return d->ofs;
}

int PRVM_ED_FindGlobalOffset(prvm_prog_t *prog, const char *global)
{
	ddef_t *d;
	d = PRVM_ED_FindGlobal(prog, global);
	if (!d)
		return -1;
	return d->ofs;
}

func_t PRVM_ED_FindFunctionOffset(prvm_prog_t *prog, const char *function)
{
	mfunction_t *f;
	f = PRVM_ED_FindFunction(prog, function);
	if (!f)
		return 0;
	return (func_t)(f - prog->functions);
}

  
                 
                   
                 
  
prvm_prog_t *PRVM_ProgFromString(const char *str)
{
	if (!strcmp(str, "server"))
		return SVVM_prog;
	if (!strcmp(str, "client"))
		return CLVM_prog;
#ifdef CONFIG_MENU
	if (!strcmp(str, "menu"))
		return MVM_prog;
#endif
	return NULL;
}

  
                 
                           
                 
  
prvm_prog_t *PRVM_FriendlyProgFromString(const char *str)
{
	prvm_prog_t *prog = PRVM_ProgFromString(str);
	if (!prog)
	{
		Con_Printf("%s: unknown program name\n", str);
		return NULL;
	}
	if (!prog->loaded)
	{
		Con_Printf("%s: program is not loaded\n", str);
		return NULL;
	}
	return prog;
}

  
                 
                  

                        

                                                                            
                                     
                 
  
void PRVM_ED_ClearEdict(prvm_prog_t *prog, prvm_edict_t *e)
{
	memset(e->fields.fp, 0, prog->entityfields * sizeof(prvm_vec_t));
	e->priv.required->free = false;
	e->priv.required->freetime = realtime;
	if(e->priv.required->allocation_origin)
		Mem_Free((char *)e->priv.required->allocation_origin);
	e->priv.required->allocation_origin = PRVM_AllocationOrigin(prog);

	                                                                                 
	prog->init_edict(prog, e);
}

const char *PRVM_AllocationOrigin(prvm_prog_t *prog)
{
	char *buf = NULL;
	if(prog->leaktest_active)
	if(prog->depth > 0)                                                                                 
	{
		buf = (char *)PRVM_Alloc(256);
		PRVM_ShortStackTrace(prog, buf, 256);
	}
	return buf;
}

  
                 
                

                                                                     
                 
  
qboolean PRVM_ED_CanAlloc(prvm_prog_t *prog, prvm_edict_t *e)
{
	if(!e->priv.required->free)
		return false;
	if(prvm_reuseedicts_always_allow == realtime)
		return true;
	if(realtime <= e->priv.required->freetime + 0.1 && prvm_reuseedicts_neverinsameframe.integer)
		return false;                                                               
	if(e->priv.required->freetime < prog->starttime + prvm_reuseedicts_startuptime.value)
		return true;
	if(realtime > e->priv.required->freetime + 1)
		return true;
	return false;                                                                                   
}

  
                 
             

                                                  
                                                                  
                                                                    
                                                                    
                      
                 
  
prvm_edict_t *PRVM_ED_Alloc(prvm_prog_t *prog)
{
	int i;
	prvm_edict_t *e;

	                                     
	                                            
	                                 
	                                                                         
	                                         
	for (i = prog->reserved_edicts + 1;i < prog->num_edicts;i++)
	{
		e = PRVM_EDICT_NUM(i);
		if(PRVM_ED_CanAlloc(prog, e))
		{
			PRVM_ED_ClearEdict (prog, e);
			return e;
		}
	}

	if (i == prog->limit_edicts)
		prog->error_cmd("%s: PRVM_ED_Alloc: no free edicts", prog->name);

	prog->num_edicts++;
	if (prog->num_edicts >= prog->max_edicts)
		PRVM_MEM_IncreaseEdicts(prog);

	e = PRVM_EDICT_NUM(i);

	PRVM_ED_ClearEdict(prog, e);
	return e;
}

  
                 
            

                       
                                                               
                 
  
void PRVM_ED_Free(prvm_prog_t *prog, prvm_edict_t *ed)
{
	                                                         
	if (ed - prog->edicts <= prog->reserved_edicts)
		return;

	prog->free_edict(prog, ed);

	ed->priv.required->free = true;
	ed->priv.required->freetime = realtime;
	if(ed->priv.required->allocation_origin)
	{
		Mem_Free((char *)ed->priv.required->allocation_origin);
		ed->priv.required->allocation_origin = NULL;
	}
}

                                                                             

  
            
                   
            
  
static ddef_t *PRVM_ED_GlobalAtOfs (prvm_prog_t *prog, int ofs)
{
	ddef_t		*def;
	int			i;

	for (i = 0;i < prog->numglobaldefs;i++)
	{
		def = &prog->globaldefs[i];
		if (def->ofs == ofs)
			return def;
	}
	return NULL;
}

  
            
                  
            
  
ddef_t *PRVM_ED_FieldAtOfs (prvm_prog_t *prog, int ofs)
{
	ddef_t		*def;
	int			i;

	for (i = 0;i < prog->numfielddefs;i++)
	{
		def = &prog->fielddefs[i];
		if (def->ofs == ofs)
			return def;
	}
	return NULL;
}

  
            
                 
            
  
ddef_t *PRVM_ED_FindField (prvm_prog_t *prog, const char *name)
{
	ddef_t *def;
	int i;

	for (i = 0;i < prog->numfielddefs;i++)
	{
		def = &prog->fielddefs[i];
		if (!strcmp(PRVM_GetString(prog, def->s_name), name))
			return def;
	}
	return NULL;
}

  
            
                  
            
  
ddef_t *PRVM_ED_FindGlobal (prvm_prog_t *prog, const char *name)
{
	ddef_t *def;
	int i;

	for (i = 0;i < prog->numglobaldefs;i++)
	{
		def = &prog->globaldefs[i];
		if (!strcmp(PRVM_GetString(prog, def->s_name), name))
			return def;
	}
	return NULL;
}


  
            
                    
            
  
mfunction_t *PRVM_ED_FindFunction (prvm_prog_t *prog, const char *name)
{
	mfunction_t		*func;
	int				i;

	for (i = 0;i < prog->numfunctions;i++)
	{
		func = &prog->functions[i];
		if (!strcmp(PRVM_GetString(prog, func->s_name), name))
			return func;
	}
	return NULL;
}


  
            
                

                                                           
             
  
static char *PRVM_ValueString (prvm_prog_t *prog, etype_t type, prvm_eval_t *val, char *line, size_t linelength)
{
	ddef_t *def;
	mfunction_t *f;
	int n;

	type = (etype_t)((int) type & ~DEF_SAVEGLOBAL);

	switch (type)
	{
	case ev_string:
		strlcpy (line, PRVM_GetString (prog, val->string), linelength);
		break;
	case ev_entity:
		n = val->edict;
		if (n < 0 || n >= prog->max_edicts)
			dpsnprintf (line, linelength, "entity %i (invalid!)", n);
		else
			dpsnprintf (line, linelength, "entity %i", n);
		break;
	case ev_function:
		f = prog->functions + val->function;
		dpsnprintf (line, linelength, "%s()", PRVM_GetString(prog, f->s_name));
		break;
	case ev_field:
		def = PRVM_ED_FieldAtOfs ( prog, val->_int );
		dpsnprintf (line, linelength, ".%s", PRVM_GetString(prog, def->s_name));
		break;
	case ev_void:
		dpsnprintf (line, linelength, "void");
		break;
	case ev_float:
		                                          
		dpsnprintf (line, linelength, FLOAT_LOSSLESS_FORMAT, val->_float);
		break;
	case ev_vector:
		                                          
		dpsnprintf (line, linelength, "'" VECTOR_LOSSLESS_FORMAT "'", val->vector[0], val->vector[1], val->vector[2]);
		break;
	case ev_pointer:
		dpsnprintf (line, linelength, "pointer");
		break;
	default:
		dpsnprintf (line, linelength, "bad type %i", (int) type);
		break;
	}

	return line;
}

  
            
                    

                                                           
                                   
             
  
char *PRVM_UglyValueString (prvm_prog_t *prog, etype_t type, prvm_eval_t *val, char *line, size_t linelength)
{
	int i;
	const char *s;
	ddef_t *def;
	mfunction_t *f;

	type = (etype_t)((int)type & ~DEF_SAVEGLOBAL);

	switch (type)
	{
	case ev_string:
		                                                    
		                                                  
		                                            
		s = PRVM_GetString (prog, val->string);
		for (i = 0;i < (int)linelength - 2 && *s;)
		{
			if (*s == '\n')
			{
				line[i++] = '\\';
				line[i++] = 'n';
			}
			else if (*s == '\r')
			{
				line[i++] = '\\';
				line[i++] = 'r';
			}
			else if (*s == '\\')
			{
				line[i++] = '\\';
				line[i++] = '\\';
			}
			else if (*s == '"')
			{
				line[i++] = '\\';
				line[i++] = '"';
			}
			else
				line[i++] = *s;
			s++;
		}
		line[i] = '\0';
		break;
	case ev_entity:
		dpsnprintf (line, linelength, "%i", val->edict);
		break;
	case ev_function:
		f = prog->functions + val->function;
		strlcpy (line, PRVM_GetString (prog, f->s_name), linelength);
		break;
	case ev_field:
		def = PRVM_ED_FieldAtOfs ( prog, val->_int );
		dpsnprintf (line, linelength, ".%s", PRVM_GetString(prog, def->s_name));
		break;
	case ev_void:
		dpsnprintf (line, linelength, "void");
		break;
	case ev_float:
		dpsnprintf (line, linelength, FLOAT_LOSSLESS_FORMAT, val->_float);
		break;
	case ev_vector:
		dpsnprintf (line, linelength, VECTOR_LOSSLESS_FORMAT, val->vector[0], val->vector[1], val->vector[2]);
		break;
	default:
		dpsnprintf (line, linelength, "bad type %i", type);
		break;
	}

	return line;
}

  
            
                 

                                                                 
                        
            
  
char *PRVM_GlobalString (prvm_prog_t *prog, int ofs, char *line, size_t linelength)
{
	char	*s;
	           
	ddef_t	*def;
	prvm_eval_t	*val;
	char valuebuf[MAX_INPUTLINE];

	val = (prvm_eval_t *)&prog->globals.fp[ofs];
	def = PRVM_ED_GlobalAtOfs(prog, ofs);
	if (!def)
		dpsnprintf (line, linelength, "GLOBAL%i", ofs);
	else
	{
		s = PRVM_ValueString (prog, (etype_t)def->type, val, valuebuf, sizeof(valuebuf));
		dpsnprintf (line, linelength, "%s (=%s)", PRVM_GetString(prog, def->s_name), s);
	}

	                   
	                     
	                     
	                    

	return line;
}

char *PRVM_GlobalStringNoContents (prvm_prog_t *prog, int ofs, char *line, size_t linelength)
{
	           
	ddef_t	*def;

	def = PRVM_ED_GlobalAtOfs(prog, ofs);
	if (!def)
		dpsnprintf (line, linelength, "GLOBAL%i", ofs);
	else
		dpsnprintf (line, linelength, "%s", PRVM_GetString(prog, def->s_name));

	                   
	                     
	                     
	                    

	return line;
}


  
             
             

             
             
  
                                                                        
                                                                                                    
void PRVM_ED_Print(prvm_prog_t *prog, prvm_edict_t *ed, const char *wildcard_fieldname)
{
	size_t	l;
	ddef_t	*d;
	prvm_eval_t	*val;
	int		i, j;
	const char	*name;
	int		type;
	char	tempstring[MAX_INPUTLINE], tempstring2[260];                            
	char	valuebuf[MAX_INPUTLINE];

	if (ed->priv.required->free)
	{
		Con_Printf("%s: FREE\n",prog->name);
		return;
	}

	tempstring[0] = 0;
	dpsnprintf(tempstring, sizeof(tempstring), "\n%s EDICT %i:\n", prog->name, PRVM_NUM_FOR_EDICT(ed));
	for (i = 1;i < prog->numfielddefs;i++)
	{
		d = &prog->fielddefs[i];
		name = PRVM_GetString(prog, d->s_name);
		if(strlen(name) > 1 && name[strlen(name)-2] == '_' && (name[strlen(name)-1] == 'x' || name[strlen(name)-1] == 'y' || name[strlen(name)-1] == 'z'))
			continue;	                       

		                            
		if(wildcard_fieldname)
			if( !matchpattern(name, wildcard_fieldname, 1) )
				                     
				continue;

		val = (prvm_eval_t *)(ed->fields.fp + d->ofs);

	                                              
		type = d->type & ~DEF_SAVEGLOBAL;

		for (j=0 ; j<prvm_type_size[type] ; j++)
			if (val->ivector[j])
				break;
		if (j == prvm_type_size[type])
			continue;

		if (strlen(name) > sizeof(tempstring2)-4)
		{
			memcpy (tempstring2, name, sizeof(tempstring2)-4);
			tempstring2[sizeof(tempstring2)-4] = tempstring2[sizeof(tempstring2)-3] = tempstring2[sizeof(tempstring2)-2] = '.';
			tempstring2[sizeof(tempstring2)-1] = 0;
			name = tempstring2;
		}
		strlcat(tempstring, name, sizeof(tempstring));
		for (l = strlen(name);l < 14;l++)
			strlcat(tempstring, " ", sizeof(tempstring));
		strlcat(tempstring, " ", sizeof(tempstring));

		name = PRVM_ValueString(prog, (etype_t)d->type, val, valuebuf, sizeof(valuebuf));
		if (strlen(name) > sizeof(tempstring2)-4)
		{
			memcpy (tempstring2, name, sizeof(tempstring2)-4);
			tempstring2[sizeof(tempstring2)-4] = tempstring2[sizeof(tempstring2)-3] = tempstring2[sizeof(tempstring2)-2] = '.';
			tempstring2[sizeof(tempstring2)-1] = 0;
			name = tempstring2;
		}
		strlcat(tempstring, name, sizeof(tempstring));
		strlcat(tempstring, "\n", sizeof(tempstring));
		if (strlen(tempstring) >= sizeof(tempstring)/2)
		{
			Con_Print(tempstring);
			tempstring[0] = 0;
		}
	}
	if (tempstring[0])
		Con_Print(tempstring);
}

  
             
             

             
             
  
extern cvar_t developer_entityparsing;
void PRVM_ED_Write (prvm_prog_t *prog, qfile_t *f, prvm_edict_t *ed)
{
	ddef_t	*d;
	prvm_eval_t	*val;
	int		i, j;
	const char	*name;
	int		type;
	char vabuf[1024];
	char valuebuf[MAX_INPUTLINE];

	FS_Print(f, "{\n");

	if (ed->priv.required->free)
	{
		FS_Print(f, "}\n");
		return;
	}

	for (i = 1;i < prog->numfielddefs;i++)
	{
		d = &prog->fielddefs[i];
		name = PRVM_GetString(prog, d->s_name);

		if(developer_entityparsing.integer)
			Con_Printf("PRVM_ED_Write: at entity %d field %s\n", PRVM_NUM_FOR_EDICT(ed), name);

		                                                                                                                                                    
		if(strlen(name) > 1 && name[strlen(name)-2] == '_')
			continue;	                                                                                                                                                              

		val = (prvm_eval_t *)(ed->fields.fp + d->ofs);

	                                              
		type = d->type & ~DEF_SAVEGLOBAL;
		for (j=0 ; j<prvm_type_size[type] ; j++)
			if (val->ivector[j])
				break;
		if (j == prvm_type_size[type])
			continue;

		FS_Printf(f,"\"%s\" ",name);
		prog->statestring = va(vabuf, sizeof(vabuf), "PRVM_ED_Write, ent=%d, name=%s", i, name);
		FS_Printf(f,"\"%s\"\n", PRVM_UglyValueString(prog, (etype_t)d->type, val, valuebuf, sizeof(valuebuf)));
		prog->statestring = NULL;
	}

	FS_Print(f, "}\n");
}

void PRVM_ED_PrintNum (prvm_prog_t *prog, int ent, const char *wildcard_fieldname)
{
	PRVM_ED_Print(prog, PRVM_EDICT_NUM(ent), wildcard_fieldname);
}

  
             
                     

                                                            
             
  
void PRVM_ED_PrintEdicts_f (void)
{
	prvm_prog_t *prog;
	int		i;
	const char *wildcard_fieldname;

	if(Cmd_Argc() < 2 || Cmd_Argc() > 3)
	{
		Con_Print("prvm_edicts <program name> <optional field name wildcard>\n");
		return;
	}

	if (!(prog = PRVM_FriendlyProgFromString(Cmd_Argv(1))))
		return;

	if( Cmd_Argc() == 3)
		wildcard_fieldname = Cmd_Argv(2);
	else
		wildcard_fieldname = NULL;

	Con_Printf("%s: %i entities\n", prog->name, prog->num_edicts);
	for (i=0 ; i<prog->num_edicts ; i++)
		PRVM_ED_PrintNum (prog, i, wildcard_fieldname);
}

  
             
                    

                                    
             
  
static void PRVM_ED_PrintEdict_f (void)
{
	prvm_prog_t *prog;
	int		i;
	const char	*wildcard_fieldname;

	if(Cmd_Argc() < 3 || Cmd_Argc() > 4)
	{
		Con_Print("prvm_edict <program name> <edict number> <optional field name wildcard>\n");
		return;
	}

	if (!(prog = PRVM_FriendlyProgFromString(Cmd_Argv(1))))
		return;

	i = atoi (Cmd_Argv(2));
	if (i >= prog->num_edicts)
	{
		Con_Print("Bad edict number\n");
		return;
	}
	if( Cmd_Argc() == 4)
		                             
		wildcard_fieldname = Cmd_Argv(3);
	else
		          
		wildcard_fieldname = NULL;
	PRVM_ED_PrintNum (prog, i, wildcard_fieldname);
}

  
             
             

             
             
  
                                                              
                                        
static void PRVM_ED_Count_f (void)
{
	prvm_prog_t *prog;

	if(Cmd_Argc() != 2)
	{
		Con_Print("prvm_count <program name>\n");
		return;
	}

	if (!(prog = PRVM_FriendlyProgFromString(Cmd_Argv(1))))
		return;

	prog->count_edicts(prog);
}

  
                                                                              

                      

                                                 
                                                                              
  

  
             
                    
             
  
void PRVM_ED_WriteGlobals (prvm_prog_t *prog, qfile_t *f)
{
	ddef_t		*def;
	int			i;
	const char		*name;
	int			type;
	char vabuf[1024];
	char valuebuf[MAX_INPUTLINE];

	FS_Print(f,"{\n");
	for (i = 0;i < prog->numglobaldefs;i++)
	{
		def = &prog->globaldefs[i];
		type = def->type;
		if ( !(def->type & DEF_SAVEGLOBAL) )
			continue;
		type &= ~DEF_SAVEGLOBAL;

		if (type != ev_string && type != ev_float && type != ev_entity)
			continue;

		name = PRVM_GetString(prog, def->s_name);

		if(developer_entityparsing.integer)
			Con_Printf("PRVM_ED_WriteGlobals: at global %s\n", name);

		prog->statestring = va(vabuf, sizeof(vabuf), "PRVM_ED_WriteGlobals, name=%s", name);
		FS_Printf(f,"\"%s\" ", name);
		FS_Printf(f,"\"%s\"\n", PRVM_UglyValueString(prog, (etype_t)type, (prvm_eval_t *)&prog->globals.fp[def->ofs], valuebuf, sizeof(valuebuf)));
		prog->statestring = NULL;
	}
	FS_Print(f,"}\n");
}

  
             
                    
             
  
void PRVM_ED_ParseGlobals (prvm_prog_t *prog, const char *data)
{
	char keyname[MAX_INPUTLINE];
	ddef_t *key;

	while (1)
	{
		            
		if (!COM_ParseToken_Simple(&data, false, false, true))
			prog->error_cmd("PRVM_ED_ParseGlobals: EOF without closing brace");
		if (com_token[0] == '}')
			break;

		if (developer_entityparsing.integer)
			Con_Printf("Key: \"%s\"", com_token);

		strlcpy (keyname, com_token, sizeof(keyname));

		              
		if (!COM_ParseToken_Simple(&data, false, true, true))
			prog->error_cmd("PRVM_ED_ParseGlobals: EOF without closing brace");

		if (developer_entityparsing.integer)
			Con_Printf(" \"%s\"\n", com_token);

		if (com_token[0] == '}')
			prog->error_cmd("PRVM_ED_ParseGlobals: closing brace without data");

		key = PRVM_ED_FindGlobal (prog, keyname);
		if (!key)
		{
			Con_DPrintf("'%s' is not a global on %s\n", keyname, prog->name);
			continue;
		}

		if (!PRVM_ED_ParseEpair(prog, NULL, key, com_token, true))
			prog->error_cmd("PRVM_ED_ParseGlobals: parse error");
	}
}

                                                                              


  
             
                 

                                  
                      
             
  
qboolean PRVM_ED_ParseEpair(prvm_prog_t *prog, prvm_edict_t *ent, ddef_t *key, const char *s, qboolean parsebackslash)
{
	int i, l;
	char *new_p;
	ddef_t *def;
	prvm_eval_t *val;
	mfunction_t *func;

	if (ent)
		val = (prvm_eval_t *)(ent->fields.fp + key->ofs);
	else
		val = (prvm_eval_t *)(prog->globals.fp + key->ofs);
	switch (key->type & ~DEF_SAVEGLOBAL)
	{
	case ev_string:
		l = (int)strlen(s) + 1;
		val->string = PRVM_AllocString(prog, l, &new_p);
		for (i = 0;i < l;i++)
		{
			if (s[i] == '\\' && s[i+1] && parsebackslash)
			{
				i++;
				if (s[i] == 'n')
					*new_p++ = '\n';
				else if (s[i] == 'r')
					*new_p++ = '\r';
				else
					*new_p++ = s[i];
			}
			else
				*new_p++ = s[i];
		}
		break;

	case ev_float:
		while (*s && ISWHITESPACE(*s))
			s++;
		val->_float = atof(s);
		break;

	case ev_vector:
		for (i = 0;i < 3;i++)
		{
			while (*s && ISWHITESPACE(*s))
				s++;
			if (!*s)
				break;
			val->vector[i] = atof(s);
			while (!ISWHITESPACE(*s))
				s++;
			if (!*s)
				break;
		}
		break;

	case ev_entity:
		while (*s && ISWHITESPACE(*s))
			s++;
		i = atoi(s);
		if (i >= prog->limit_edicts)
			Con_Printf("PRVM_ED_ParseEpair: ev_entity reference too large (edict %u >= MAX_EDICTS %u) on %s\n", (unsigned int)i, prog->limit_edicts, prog->name);
		while (i >= prog->max_edicts)
			PRVM_MEM_IncreaseEdicts(prog);
		                                                                    
		if (ent)
			val = (prvm_eval_t *)(ent->fields.fp + key->ofs);
		val->edict = PRVM_EDICT_TO_PROG(PRVM_EDICT_NUM((int)i));
		break;

	case ev_field:
		if (*s != '.')
		{
			Con_DPrintf("PRVM_ED_ParseEpair: Bogus field name %s in %s\n", s, prog->name);
			return false;
		}
		def = PRVM_ED_FindField(prog, s + 1);
		if (!def)
		{
			Con_DPrintf("PRVM_ED_ParseEpair: Can't find field %s in %s\n", s, prog->name);
			return false;
		}
		val->_int = def->ofs;
		break;

	case ev_function:
		func = PRVM_ED_FindFunction(prog, s);
		if (!func)
		{
			Con_Printf("PRVM_ED_ParseEpair: Can't find function %s in %s\n", s, prog->name);
			return false;
		}
		val->function = func - prog->functions;
		break;

	default:
		Con_Printf("PRVM_ED_ParseEpair: Unknown key->type %i for key \"%s\" on %s\n", key->type, PRVM_GetString(prog, key->s_name), prog->name);
		return false;
	}
	return true;
}

  
             
                  

                                                                  
               

      
                                     
                          
                          

                                                                            
                  
             
  
static void PRVM_GameCommand(const char *whichprogs, const char *whichcmd)
{
	prvm_prog_t *prog;
	if(Cmd_Argc() < 1)
	{
		Con_Printf("%s text...\n", whichcmd);
		return;
	}

	if (!(prog = PRVM_FriendlyProgFromString(whichprogs)))
		return;

	if(!PRVM_allfunction(GameCommand))
	{
		Con_Printf("%s program do not support GameCommand!\n", whichprogs);
	}
	else
	{
		int restorevm_tempstringsbuf_cursize;
		const char *s;

		s = Cmd_Args();

		restorevm_tempstringsbuf_cursize = prog->tempstringsbuf.cursize;
		PRVM_G_INT(OFS_PARM0) = PRVM_SetTempString(prog, s ? s : "");
		prog->ExecuteProgram(prog, PRVM_allfunction(GameCommand), "QC function GameCommand is missing");
		prog->tempstringsbuf.cursize = restorevm_tempstringsbuf_cursize;
	}
}
static void PRVM_GameCommand_Server_f(void)
{
	PRVM_GameCommand("server", "sv_cmd");
}
static void PRVM_GameCommand_Client_f(void)
{
	PRVM_GameCommand("client", "cl_cmd");
}
static void PRVM_GameCommand_Menu_f(void)
{
	PRVM_GameCommand("menu", "menu_cmd");
}

  
             
                  

                                                    
             
  
static void PRVM_ED_EdictGet_f(void)
{
	prvm_prog_t *prog;
	prvm_edict_t *ed;
	ddef_t *key;
	const char *s;
	prvm_eval_t *v;
	char valuebuf[MAX_INPUTLINE];

	if(Cmd_Argc() != 4 && Cmd_Argc() != 5)
	{
		Con_Print("prvm_edictget <program name> <edict number> <field> [<cvar>]\n");
		return;
	}

	if (!(prog = PRVM_FriendlyProgFromString(Cmd_Argv(1))))
		return;

	ed = PRVM_EDICT_NUM(atoi(Cmd_Argv(2)));

	if((key = PRVM_ED_FindField(prog, Cmd_Argv(3))) == 0)
	{
		Con_Printf("Key %s not found !\n", Cmd_Argv(3));
		goto fail;
	}

	v = (prvm_eval_t *)(ed->fields.fp + key->ofs);
	s = PRVM_UglyValueString(prog, (etype_t)key->type, v, valuebuf, sizeof(valuebuf));
	if(Cmd_Argc() == 5)
	{
		cvar_t *cvar = Cvar_FindVar(Cmd_Argv(4));
		if (cvar && cvar->flags & CVAR_READONLY)
		{
			Con_Printf("prvm_edictget: %s is read-only\n", cvar->name);
			goto fail;
		}
		Cvar_Get(Cmd_Argv(4), s, 0, NULL);
	}
	else
		Con_Printf("%s\n", s);

fail:
	;
}

static void PRVM_ED_GlobalGet_f(void)
{
	prvm_prog_t *prog;
	ddef_t *key;
	const char *s;
	prvm_eval_t *v;
	char valuebuf[MAX_INPUTLINE];

	if(Cmd_Argc() != 3 && Cmd_Argc() != 4)
	{
		Con_Print("prvm_globalget <program name> <global> [<cvar>]\n");
		return;
	}

	if (!(prog = PRVM_FriendlyProgFromString(Cmd_Argv(1))))
		return;

	key = PRVM_ED_FindGlobal(prog, Cmd_Argv(2));
	if(!key)
	{
		Con_Printf( "No global '%s' in %s!\n", Cmd_Argv(2), Cmd_Argv(1) );
		goto fail;
	}

	v = (prvm_eval_t *) &prog->globals.fp[key->ofs];
	s = PRVM_UglyValueString(prog, (etype_t)key->type, v, valuebuf, sizeof(valuebuf));
	if(Cmd_Argc() == 4)
	{
		cvar_t *cvar = Cvar_FindVar(Cmd_Argv(3));
		if (cvar && cvar->flags & CVAR_READONLY)
		{
			Con_Printf("prvm_globalget: %s is read-only\n", cvar->name);
			goto fail;
		}
		Cvar_Get(Cmd_Argv(3), s, 0, NULL);
	}
	else
		Con_Printf("%s\n", s);

fail:
	;
}

  
             
                  

                                                   
             
  
static void PRVM_ED_EdictSet_f(void)
{
	prvm_prog_t *prog;
	prvm_edict_t *ed;
	ddef_t *key;

	if(Cmd_Argc() != 5)
	{
		Con_Print("prvm_edictset <program name> <edict number> <field> <value>\n");
		return;
	}

	if (!(prog = PRVM_FriendlyProgFromString(Cmd_Argv(1))))
		return;

	ed = PRVM_EDICT_NUM(atoi(Cmd_Argv(2)));

	if((key = PRVM_ED_FindField(prog, Cmd_Argv(3))) == 0)
		Con_Printf("Key %s not found !\n", Cmd_Argv(3));
	else
		PRVM_ED_ParseEpair(prog, ed, key, Cmd_Argv(4), true);
}

  
                    
                  

                                                                   
                                                
                                              
                    
  
const char *PRVM_ED_ParseEdict (prvm_prog_t *prog, const char *data, prvm_edict_t *ent)
{
	ddef_t *key;
	qboolean anglehack;
	qboolean init;
	char keyname[256];
	size_t n;

	init = false;

                                      
	while (1)
	{
	            
		if (!COM_ParseToken_Simple(&data, false, false, true))
			prog->error_cmd("PRVM_ED_ParseEdict: EOF without closing brace");
		if (developer_entityparsing.integer)
			Con_Printf("Key: \"%s\"", com_token);
		if (com_token[0] == '}')
			break;

		                                                              
		                                                       
		if (!strcmp(com_token, "angle"))
		{
			strlcpy (com_token, "angles", sizeof(com_token));
			anglehack = true;
		}
		else
			anglehack = false;

		                                                        
		if (!strcmp(com_token, "light"))
			strlcpy (com_token, "light_lev", sizeof(com_token));	                            

		strlcpy (keyname, com_token, sizeof(keyname));

		                                                    
		n = strlen(keyname);
		while (n && keyname[n-1] == ' ')
		{
			keyname[n-1] = 0;
			n--;
		}

	              
		if (!COM_ParseToken_Simple(&data, false, false, true))
			prog->error_cmd("PRVM_ED_ParseEdict: EOF without closing brace");
		if (developer_entityparsing.integer)
			Con_Printf(" \"%s\"\n", com_token);

		if (com_token[0] == '}')
			prog->error_cmd("PRVM_ED_ParseEdict: closing brace without data");

		init = true;

		                                                                            
		if (!keyname[0])
			continue;

                                                                    
                                         
		if (keyname[0] == '_')
			continue;

		key = PRVM_ED_FindField (prog, keyname);
		if (!key)
		{
			Con_DPrintf("%s: '%s' is not a field\n", prog->name, keyname);
			continue;
		}

		if (anglehack)
		{
			char	temp[32];
			strlcpy (temp, com_token, sizeof(temp));
			dpsnprintf (com_token, sizeof(com_token), "0 %s 0", temp);
		}

		if (!PRVM_ED_ParseEpair(prog, ent, key, com_token, strcmp(keyname, "wad") != 0))
			prog->error_cmd("PRVM_ED_ParseEdict: parse error");
	}

	if (!init) {
		ent->priv.required->free = true;
		ent->priv.required->freetime = realtime;
	}

	return data;
}


  
                
                    

                                                                         
                                                                           
                               

                                                        
                                                      

                                                                         
                                                                               
                
  
void PRVM_ED_LoadFromFile (prvm_prog_t *prog, const char *data)
{
	prvm_edict_t *ent;
	int parsed, inhibited, spawned, died;
	const char *funcname;
	mfunction_t *func;
	char vabuf[1024];

	parsed = 0;
	inhibited = 0;
	spawned = 0;
	died = 0;

	prvm_reuseedicts_always_allow = realtime;

             
	while (1)
	{
                          
		if (!COM_ParseToken_Simple(&data, false, false, true))
			break;
		if (com_token[0] != '{')
			prog->error_cmd("PRVM_ED_LoadFromFile: %s: found %s when expecting {", prog->name, com_token);

		                                                  
		if(prog->loadintoworld)
		{
			prog->loadintoworld = false;
			ent = PRVM_EDICT_NUM(0);
		}
		else
			ent = PRVM_ED_Alloc(prog);

		           
		if (ent != prog->edicts)	       
			memset (ent->fields.fp, 0, prog->entityfields * sizeof(prvm_vec_t));

		data = PRVM_ED_ParseEdict (prog, data, ent);
		parsed++;

		                      
		if(!prog->load_edict(prog, ent))
		{
			PRVM_ED_Free(prog, ent);
			inhibited++;
			continue;
		}

		if (PRVM_serverfunction(SV_OnEntityPreSpawnFunction))
		{
			             
			PRVM_serverglobalfloat(time) = sv.time;
			PRVM_serverglobaledict(self) = PRVM_EDICT_TO_PROG(ent);
			prog->ExecuteProgram(prog, PRVM_serverfunction(SV_OnEntityPreSpawnFunction), "QC function SV_OnEntityPreSpawnFunction is missing");
		}

		if(ent->priv.required->free)
		{
			inhibited++;
			continue;
		}

  
                                                                                      
  
		if(!ent->priv.required->free)
		{
			if (!PRVM_alledictstring(ent, classname))
			{
				Con_Print("No classname for:\n");
				PRVM_ED_Print(prog, ent, NULL);
				PRVM_ED_Free (prog, ent);
				continue;
			}

			                              
			funcname = PRVM_GetString(prog, PRVM_alledictstring(ent, classname));
			func = PRVM_ED_FindFunction (prog, va(vabuf, sizeof(vabuf), "spawnfunc_%s", funcname));
			if(!func)
				if(!PRVM_allglobalfloat(require_spawnfunc_prefix))
					func = PRVM_ED_FindFunction (prog, funcname);

			if (!func)
			{
				                                    
				if (PRVM_serverfunction(SV_OnEntityNoSpawnFunction))
				{
					             
					PRVM_serverglobalfloat(time) = sv.time;
					PRVM_serverglobaledict(self) = PRVM_EDICT_TO_PROG(ent);
					prog->ExecuteProgram(prog, PRVM_serverfunction(SV_OnEntityNoSpawnFunction), "QC function SV_OnEntityNoSpawnFunction is missing");
				}
				else
				{
					if (developer.integer > 0)                                            
					{
						Con_Print("No spawn function for:\n");
						PRVM_ED_Print(prog, ent, NULL);
					}
					PRVM_ED_Free (prog, ent);
					continue;                                     
				}
			}
			else
			{
				             
				PRVM_serverglobalfloat(time) = sv.time;
				PRVM_allglobaledict(self) = PRVM_EDICT_TO_PROG(ent);
				prog->ExecuteProgram(prog, func - prog->functions, "");
			}
		}

		if(!ent->priv.required->free)
		if (PRVM_serverfunction(SV_OnEntityPostSpawnFunction))
		{
			             
			PRVM_serverglobalfloat(time) = sv.time;
			PRVM_serverglobaledict(self) = PRVM_EDICT_TO_PROG(ent);
			prog->ExecuteProgram(prog, PRVM_serverfunction(SV_OnEntityPostSpawnFunction), "QC function SV_OnEntityPostSpawnFunction is missing");
		}

		spawned++;
		if (ent->priv.required->free)
			died++;
	}

	Con_DPrintf("%s: %i new entities parsed, %i new inhibited, %i (%i new) spawned (whereas %i removed self, %i stayed)\n", prog->name, parsed, inhibited, prog->num_edicts, spawned, died, spawned - died);

	prvm_reuseedicts_always_allow = 0;
}

static void PRVM_FindOffsets(prvm_prog_t *prog)
{
	                                            
	memset(&prog->fieldoffsets, -1, sizeof(prog->fieldoffsets));
	memset(&prog->globaloffsets, -1, sizeof(prog->globaloffsets));
	                                   
	memset(&prog->funcoffsets, 0, sizeof(prog->funcoffsets));
#define PRVM_DECLARE_serverglobalfloat(x)
#define PRVM_DECLARE_serverglobalvector(x)
#define PRVM_DECLARE_serverglobalstring(x)
#define PRVM_DECLARE_serverglobaledict(x)
#define PRVM_DECLARE_serverglobalfunction(x)
#define PRVM_DECLARE_clientglobalfloat(x)
#define PRVM_DECLARE_clientglobalvector(x)
#define PRVM_DECLARE_clientglobalstring(x)
#define PRVM_DECLARE_clientglobaledict(x)
#define PRVM_DECLARE_clientglobalfunction(x)
#define PRVM_DECLARE_menuglobalfloat(x)
#define PRVM_DECLARE_menuglobalvector(x)
#define PRVM_DECLARE_menuglobalstring(x)
#define PRVM_DECLARE_menuglobaledict(x)
#define PRVM_DECLARE_menuglobalfunction(x)
#define PRVM_DECLARE_serverfieldfloat(x)
#define PRVM_DECLARE_serverfieldvector(x)
#define PRVM_DECLARE_serverfieldstring(x)
#define PRVM_DECLARE_serverfieldedict(x)
#define PRVM_DECLARE_serverfieldfunction(x)
#define PRVM_DECLARE_clientfieldfloat(x)
#define PRVM_DECLARE_clientfieldvector(x)
#define PRVM_DECLARE_clientfieldstring(x)
#define PRVM_DECLARE_clientfieldedict(x)
#define PRVM_DECLARE_clientfieldfunction(x)
#define PRVM_DECLARE_menufieldfloat(x)
#define PRVM_DECLARE_menufieldvector(x)
#define PRVM_DECLARE_menufieldstring(x)
#define PRVM_DECLARE_menufieldedict(x)
#define PRVM_DECLARE_menufieldfunction(x)
#define PRVM_DECLARE_serverfunction(x)
#define PRVM_DECLARE_clientfunction(x)
#define PRVM_DECLARE_menufunction(x)
#define PRVM_DECLARE_field(x) prog->fieldoffsets.x = PRVM_ED_FindFieldOffset(prog, #x);
#define PRVM_DECLARE_global(x) prog->globaloffsets.x = PRVM_ED_FindGlobalOffset(prog, #x);
#define PRVM_DECLARE_function(x) prog->funcoffsets.x = PRVM_ED_FindFunctionOffset(prog, #x);
#include "prvm_offsets.h"
#undef PRVM_DECLARE_serverglobalfloat
#undef PRVM_DECLARE_serverglobalvector
#undef PRVM_DECLARE_serverglobalstring
#undef PRVM_DECLARE_serverglobaledict
#undef PRVM_DECLARE_serverglobalfunction
#undef PRVM_DECLARE_clientglobalfloat
#undef PRVM_DECLARE_clientglobalvector
#undef PRVM_DECLARE_clientglobalstring
#undef PRVM_DECLARE_clientglobaledict
#undef PRVM_DECLARE_clientglobalfunction
#undef PRVM_DECLARE_menuglobalfloat
#undef PRVM_DECLARE_menuglobalvector
#undef PRVM_DECLARE_menuglobalstring
#undef PRVM_DECLARE_menuglobaledict
#undef PRVM_DECLARE_menuglobalfunction
#undef PRVM_DECLARE_serverfieldfloat
#undef PRVM_DECLARE_serverfieldvector
#undef PRVM_DECLARE_serverfieldstring
#undef PRVM_DECLARE_serverfieldedict
#undef PRVM_DECLARE_serverfieldfunction
#undef PRVM_DECLARE_clientfieldfloat
#undef PRVM_DECLARE_clientfieldvector
#undef PRVM_DECLARE_clientfieldstring
#undef PRVM_DECLARE_clientfieldedict
#undef PRVM_DECLARE_clientfieldfunction
#undef PRVM_DECLARE_menufieldfloat
#undef PRVM_DECLARE_menufieldvector
#undef PRVM_DECLARE_menufieldstring
#undef PRVM_DECLARE_menufieldedict
#undef PRVM_DECLARE_menufieldfunction
#undef PRVM_DECLARE_serverfunction
#undef PRVM_DECLARE_clientfunction
#undef PRVM_DECLARE_menufunction
#undef PRVM_DECLARE_field
#undef PRVM_DECLARE_global
#undef PRVM_DECLARE_function
}

           
  
                        
 
          
              
 
          

                                                       

                      
 
  
  

  
               
              
               
  

#define PO_HASHSIZE 16384
typedef struct po_string_s
{
	char *key, *value;
	struct po_string_s *nextonhashchain;
}
po_string_t;
typedef struct po_s
{
	po_string_t *hashtable[PO_HASHSIZE];
}
po_t;
static void PRVM_PO_UnparseString(char *out, const char *in, size_t outsize)
{
	for(;;)
	{
		switch(*in)
		{
			case 0:
				*out++ = 0;
				return;
			case '\a': if(outsize >= 2) { *out++ = '\\'; *out++ = 'a'; outsize -= 2; } break;
			case '\b': if(outsize >= 2) { *out++ = '\\'; *out++ = 'b'; outsize -= 2; } break;
			case '\t': if(outsize >= 2) { *out++ = '\\'; *out++ = 't'; outsize -= 2; } break;
			case '\r': if(outsize >= 2) { *out++ = '\\'; *out++ = 'r'; outsize -= 2; } break;
			case '\n': if(outsize >= 2) { *out++ = '\\'; *out++ = 'n'; outsize -= 2; } break;
			case '\\': if(outsize >= 2) { *out++ = '\\'; *out++ = '\\'; outsize -= 2; } break;
			case '"': if(outsize >= 2) { *out++ = '\\'; *out++ = '"'; outsize -= 2; } break;
			default:
				if(*in >= 0 && *in <= 0x1F)
				{
					if(outsize >= 4)
					{
						*out++ = '\\';
						*out++ = '0' + ((*in & 0700) >> 6);
						*out++ = '0' + ((*in & 0070) >> 3);
						*out++ = '0' +  (*in & 0007)      ;
						outsize -= 4;
					}
				}
				else
				{
					if(outsize >= 1)
					{
						*out++ = *in;
						outsize -= 1;
					}
				}
				break;
		}
		++in;
	}
}
static void PRVM_PO_ParseString(char *out, const char *in, size_t outsize)
{
	for(;;)
	{
		switch(*in)
		{
			case 0:
				*out++ = 0;
				return;
			case '\\':
				++in;
				switch(*in)
				{
					case 'a': if(outsize > 0) { *out++ = '\a'; --outsize; } break;
					case 'b': if(outsize > 0) { *out++ = '\b'; --outsize; } break;
					case 't': if(outsize > 0) { *out++ = '\t'; --outsize; } break;
					case 'r': if(outsize > 0) { *out++ = '\r'; --outsize; } break;
					case 'n': if(outsize > 0) { *out++ = '\n'; --outsize; } break;
					case '\\': if(outsize > 0) { *out++ = '\\'; --outsize; } break;
					case '"': if(outsize > 0) { *out++ = '"'; --outsize; } break;
					case '0': case '1': case '2': case '3': case '4': case '5': case '6': case '7':
						if(outsize > 0) 
							*out = *in - '0';
						++in;
						if(*in >= '0' && *in <= '7')
						{
							if(outsize > 0)
								*out = (*out << 3) | (*in - '0');
							++in;
						}
						if(*in >= '0' && *in <= '7')
						{
							if(outsize > 0)
								*out = (*out << 3) | (*in - '0');
							++in;
						}
						--in;
						if(outsize > 0)
						{
							++out;
							--outsize;
						}
						break;
					default:
						if(outsize > 0) { *out++ = *in; --outsize; }
						break;
				}
				break;
			default:
				if(outsize > 0)
				{
					*out++ = *in;
					--outsize;
				}
				break;
		}
		++in;
	}
}
static po_t *PRVM_PO_Load(const char *filename, const char *filename2, mempool_t *pool)
{
	po_t *po = NULL;
	const char *p, *q;
	int mode;
	char inbuf[MAX_INPUTLINE];
	char decodedbuf[MAX_INPUTLINE];
	size_t decodedpos;
	int hashindex;
	po_string_t thisstr;
	int i;

	for (i = 0; i < 2; ++i)
	{
		const char *buf = (const char *)
			FS_LoadFile((i > 0 ? filename : filename2), pool, true, NULL);
		                                           
		                                                 
		                                  

		if(!buf)
			continue;

		if (!po)
		{
			po = (po_t *)Mem_Alloc(pool, sizeof(*po));
			memset(po, 0, sizeof(*po));
		}

		memset(&thisstr, 0, sizeof(thisstr));                         

		p = buf;
		while(*p)
		{
			if(*p == '#')
			{
				                  
				p = strchr(p, '\n');
				if(!p)
					break;
				++p;
				continue;
			}
			if(*p == '\r' || *p == '\n')
			{
				++p;
				continue;
			}
			if(!strncmp(p, "msgid \"", 7))
			{
				mode = 0;
				p += 6;
			}
			else if(!strncmp(p, "msgstr \"", 8))
			{
				mode = 1;
				p += 7;
			}
			else
			{
				p = strchr(p, '\n');
				if(!p)
					break;
				++p;
				continue;
			}
			decodedpos = 0;
			while(*p == '"')
			{
				++p;
				q = strchr(p, '\n');
				if(!q)
					break;
				if(*(q-1) == '\r')
					--q;
				if(*(q-1) != '"')
					break;
				if((size_t)(q - p) >= (size_t) sizeof(inbuf))
					break;
				strlcpy(inbuf, p, q - p);                                    
				PRVM_PO_ParseString(decodedbuf + decodedpos, inbuf, sizeof(decodedbuf) - decodedpos);
				decodedpos += strlen(decodedbuf + decodedpos);
				if(*q == '\r')
					++q;
				if(*q == '\n')
					++q;
				p = q;
			}
			if(mode == 0)
			{
				if(thisstr.key)
					Mem_Free(thisstr.key);
				thisstr.key = (char *)Mem_Alloc(pool, decodedpos + 1);
				memcpy(thisstr.key, decodedbuf, decodedpos + 1);
			}
			else if(decodedpos > 0 && thisstr.key)                                  
			{
				thisstr.value = (char *)Mem_Alloc(pool, decodedpos + 1);
				memcpy(thisstr.value, decodedbuf, decodedpos + 1);
				hashindex = CRC_Block((const unsigned char *) thisstr.key, strlen(thisstr.key)) % PO_HASHSIZE;
				thisstr.nextonhashchain = po->hashtable[hashindex];
				po->hashtable[hashindex] = (po_string_t *)Mem_Alloc(pool, sizeof(thisstr));
				memcpy(po->hashtable[hashindex], &thisstr, sizeof(thisstr));
				memset(&thisstr, 0, sizeof(thisstr));
			}
		}
		
		Mem_Free((char *) buf);
	}

	return po;
}
static const char *PRVM_PO_Lookup(po_t *po, const char *str)
{
	int hashindex = CRC_Block((const unsigned char *) str, strlen(str)) % PO_HASHSIZE;
	po_string_t *p = po->hashtable[hashindex];
	while(p)
	{
		if(!strcmp(str, p->key))
			return p->value;
		p = p->nextonhashchain;
	}
	return NULL;
}
static void PRVM_PO_Destroy(po_t *po)
{
	int i;
	for(i = 0; i < PO_HASHSIZE; ++i)
	{
		po_string_t *p = po->hashtable[i];
		while(p)
		{
			po_string_t *q = p;
			p = p->nextonhashchain;
			Mem_Free(q->key);
			Mem_Free(q->value);
			Mem_Free(q);
		}
	}
	Mem_Free(po);
}

void PRVM_LeakTest(prvm_prog_t *prog);
void PRVM_Prog_Reset(prvm_prog_t *prog)
{
	if (prog->loaded)
	{
		PRVM_LeakTest(prog);
		prog->reset_cmd(prog);
		Mem_FreePool(&prog->progs_mempool);
		if(prog->po)
			PRVM_PO_Destroy((po_t *) prog->po);
	}
	memset(prog,0,sizeof(prvm_prog_t));
	prog->break_statement = -1;
	prog->watch_global_type = ev_void;
	prog->watch_field_type = ev_void;
}

  
               
            
               
  
static void PRVM_LoadLNO( prvm_prog_t *prog, const char *progname ) {
	fs_offset_t filesize;
	unsigned char *lno;
	unsigned int *header;
	char filename[512];

	FS_StripExtension( progname, filename, sizeof( filename ) );
	strlcat( filename, ".lno", sizeof( filename ) );

	lno = FS_LoadFile( filename, tempmempool, false, &filesize );
	if( !lno ) {
		return;
	}

  
                                                
                                                
                                                      
                                                      
                                                     
                                                      
                                                                        
  
	if ((unsigned int)filesize < (6 + prog->progs_numstatements) * sizeof(int))
	{
		Mem_Free(lno);
		return;
	}

	header = (unsigned int *) lno;
	if( header[ 0 ] == *(unsigned int *) "LNOF" &&
		LittleLong( header[ 1 ] ) == 1 &&
		(unsigned int)LittleLong( header[ 2 ] ) == (unsigned int)prog->progs_numglobaldefs &&
		(unsigned int)LittleLong( header[ 3 ] ) == (unsigned int)prog->progs_numglobals &&
		(unsigned int)LittleLong( header[ 4 ] ) == (unsigned int)prog->progs_numfielddefs &&
		(unsigned int)LittleLong( header[ 5 ] ) == (unsigned int)prog->progs_numstatements )
	{
		prog->statement_linenums = (int *)Mem_Alloc(prog->progs_mempool, prog->progs_numstatements * sizeof( int ) );
		memcpy( prog->statement_linenums, header + 6, prog->progs_numstatements * sizeof( int ) );

		                             
		if ((unsigned int)filesize > ((6 + 2 * prog->progs_numstatements) * sizeof( int )))
		{
			prog->statement_columnnums = (int *)Mem_Alloc(prog->progs_mempool, prog->progs_numstatements * sizeof( int ) );
			memcpy( prog->statement_columnnums, header + 6 + prog->progs_numstatements, prog->progs_numstatements * sizeof( int ) );
		}
	}
	Mem_Free( lno );
}

  
               
              
               
  
static void PRVM_UpdateBreakpoints(prvm_prog_t *prog);
void PRVM_Prog_Load(prvm_prog_t *prog, const char * filename, unsigned char * data, fs_offset_t size, int numrequiredfunc, const char **required_func, int numrequiredfields, prvm_required_field_t *required_field, int numrequiredglobals, prvm_required_field_t *required_global)
{
	int i;
	dprograms_t *dprograms;
	dstatement_t *instatements;
	ddef_t *infielddefs;
	ddef_t *inglobaldefs;
	int *inglobals;
	dfunction_t *infunctions;
	char *instrings;
	fs_offset_t filesize;
	int requiredglobalspace;
	opcode_t op;
	int a;
	int b;
	int c;
	union
	{
		unsigned int i;
		float f;
	}
	u;
	unsigned int d;
	char vabuf[1024];
	char vabuf2[1024];
	cvar_t *cvar;

	if (prog->loaded)
		prog->error_cmd("PRVM_LoadProgs: there is already a %s program loaded!", prog->name );

	Host_LockSession();                                      
	Crypto_LoadKeys();                                             

	if (data)
	{
		dprograms = (dprograms_t *) data;
		filesize = size;
	}
	else
		dprograms = (dprograms_t *)FS_LoadFile (filename, prog->progs_mempool, false, &filesize);
	if (dprograms == NULL || filesize < (fs_offset_t)sizeof(dprograms_t))
		prog->error_cmd("PRVM_LoadProgs: couldn't load %s for %s", filename, prog->name);
	                                                                                              

	prog->profiletime = Sys_DirtyTime();
	prog->starttime = realtime;

	Con_DPrintf("%s programs occupy %iK.\n", prog->name, (int)(filesize/1024));

	requiredglobalspace = 0;
	for (i = 0;i < numrequiredglobals;i++)
		requiredglobalspace += required_global[i].type == ev_vector ? 3 : 1;

	prog->filecrc = CRC_Block((unsigned char *)dprograms, filesize);

                       
	prog->progs_version = LittleLong(dprograms->version);
	prog->progs_crc = LittleLong(dprograms->crc);
	if (prog->progs_version != PROG_VERSION)
		prog->error_cmd("%s: %s has wrong version number (%i should be %i)", prog->name, filename, prog->progs_version, PROG_VERSION);
	instatements = (dstatement_t *)((unsigned char *)dprograms + LittleLong(dprograms->ofs_statements));
	prog->progs_numstatements = LittleLong(dprograms->numstatements);
	inglobaldefs = (ddef_t *)((unsigned char *)dprograms + LittleLong(dprograms->ofs_globaldefs));
	prog->progs_numglobaldefs = LittleLong(dprograms->numglobaldefs);
	infielddefs = (ddef_t *)((unsigned char *)dprograms + LittleLong(dprograms->ofs_fielddefs));
	prog->progs_numfielddefs = LittleLong(dprograms->numfielddefs);
	infunctions = (dfunction_t *)((unsigned char *)dprograms + LittleLong(dprograms->ofs_functions));
	prog->progs_numfunctions = LittleLong(dprograms->numfunctions);
	instrings = (char *)((unsigned char *)dprograms + LittleLong(dprograms->ofs_strings));
	prog->progs_numstrings = LittleLong(dprograms->numstrings);
	inglobals = (int *)((unsigned char *)dprograms + LittleLong(dprograms->ofs_globals));
	prog->progs_numglobals = LittleLong(dprograms->numglobals);
	prog->progs_entityfields = LittleLong(dprograms->entityfields);

	prog->numstatements = prog->progs_numstatements;
	prog->numglobaldefs = prog->progs_numglobaldefs;
	prog->numfielddefs = prog->progs_numfielddefs;
	prog->numfunctions = prog->progs_numfunctions;
	prog->numstrings = prog->progs_numstrings;
	prog->numglobals = prog->progs_numglobals;
	prog->entityfields = prog->progs_entityfields;

	if (LittleLong(dprograms->ofs_strings) + prog->progs_numstrings > (int)filesize)
		prog->error_cmd("%s: %s strings go past end of file", prog->name, filename);
	prog->strings = (char *)Mem_Alloc(prog->progs_mempool, prog->progs_numstrings);
	memcpy(prog->strings, instrings, prog->progs_numstrings);
	prog->stringssize = prog->progs_numstrings;

	prog->numknownstrings = 0;
	prog->maxknownstrings = 0;
	prog->knownstrings = NULL;
	prog->knownstrings_freeable = NULL;

	Mem_ExpandableArray_NewArray(&prog->stringbuffersarray, prog->progs_mempool, sizeof(prvm_stringbuffer_t), 64);

	                                                                        
	prog->globaldefs = (ddef_t *)Mem_Alloc(prog->progs_mempool, (prog->progs_numglobaldefs + numrequiredglobals) * sizeof(ddef_t));
	prog->globals.fp = (prvm_vec_t *)Mem_Alloc(prog->progs_mempool, (prog->progs_numglobals + requiredglobalspace + 2) * sizeof(prvm_vec_t));
		                                                                         
		                                                       
		                                                                     
	prog->fielddefs = (ddef_t *)Mem_Alloc(prog->progs_mempool, (prog->progs_numfielddefs + numrequiredfields) * sizeof(ddef_t));
	                                                         
	prog->statements = (mstatement_t *)Mem_Alloc(prog->progs_mempool, prog->progs_numstatements * sizeof(mstatement_t));
	                                               
	prog->statement_profile = (double *)Mem_Alloc(prog->progs_mempool, prog->progs_numstatements * sizeof(*prog->statement_profile));
	prog->explicit_profile = (double *)Mem_Alloc(prog->progs_mempool, prog->progs_numstatements * sizeof(*prog->statement_profile));
	                                                      
	prog->functions = (mfunction_t *)Mem_Alloc(prog->progs_mempool, sizeof(mfunction_t) * prog->progs_numfunctions);

	for (i = 0;i < prog->progs_numfunctions;i++)
	{
		prog->functions[i].first_statement = LittleLong(infunctions[i].first_statement);
		prog->functions[i].parm_start = LittleLong(infunctions[i].parm_start);
		prog->functions[i].s_name = LittleLong(infunctions[i].s_name);
		prog->functions[i].s_file = LittleLong(infunctions[i].s_file);
		prog->functions[i].numparms = LittleLong(infunctions[i].numparms);
		prog->functions[i].locals = LittleLong(infunctions[i].locals);
		memcpy(prog->functions[i].parm_size, infunctions[i].parm_size, sizeof(infunctions[i].parm_size));
		if(prog->functions[i].first_statement >= prog->numstatements)
			prog->error_cmd("PRVM_LoadProgs: out of bounds function statement (function %d) in %s", i, prog->name);
		                                                                            
	}

	                                                 
	for (i=0 ; i<prog->numglobaldefs ; i++)
	{
		prog->globaldefs[i].type = LittleShort(inglobaldefs[i].type);
		prog->globaldefs[i].ofs = LittleShort(inglobaldefs[i].ofs);
		prog->globaldefs[i].s_name = LittleLong(inglobaldefs[i].s_name);
		                                
	}

	                              
	for (i = 0;i < numrequiredglobals;i++)
	{
		prog->globaldefs[prog->numglobaldefs].type = required_global[i].type;
		prog->globaldefs[prog->numglobaldefs].ofs = prog->numglobals;
		prog->globaldefs[prog->numglobaldefs].s_name = PRVM_SetEngineString(prog, required_global[i].name);
		if (prog->globaldefs[prog->numglobaldefs].type == ev_vector)
			prog->numglobals += 3;
		else
			prog->numglobals++;
		prog->numglobaldefs++;
	}

	                                               
	for (i = 0;i < prog->numfielddefs;i++)
	{
		prog->fielddefs[i].type = LittleShort(infielddefs[i].type);
		if (prog->fielddefs[i].type & DEF_SAVEGLOBAL)
			prog->error_cmd("PRVM_LoadProgs: prog->fielddefs[i].type & DEF_SAVEGLOBAL in %s", prog->name);
		prog->fielddefs[i].ofs = LittleShort(infielddefs[i].ofs);
		prog->fielddefs[i].s_name = LittleLong(infielddefs[i].s_name);
		                                
	}

	                             
	for (i = 0;i < numrequiredfields;i++)
	{
		prog->fielddefs[prog->numfielddefs].type = required_field[i].type;
		prog->fielddefs[prog->numfielddefs].ofs = prog->entityfields;
		prog->fielddefs[prog->numfielddefs].s_name = PRVM_SetEngineString(prog, required_field[i].name);
		if (prog->fielddefs[prog->numfielddefs].type == ev_vector)
			prog->entityfields += 3;
		else
			prog->entityfields++;
		prog->numfielddefs++;
	}

	                                                          
	                                                         
#define remapglobal(index) (index)
#define remapfield(index) (index)

	               
	                                                                                                                                              
	for (i = 0;i < prog->progs_numglobals;i++)
	{
		u.i = LittleLong(inglobals[i]);
		                                                                      
		if (u.i)
		{
			d = u.i & 0xFF800000;
			if ((d == 0xFF800000) || (d == 0))
			{
				                                          
				prog->globals.ip[remapglobal(i)] = u.i;
			}
			else
			{
				                                        
				prog->globals.fp[remapglobal(i)] = u.f;
			}
		}
	}

	                                                         
	                                                  
	for (i = 0;i < prog->progs_numstatements;i++)
	{
		op = (opcode_t)LittleShort(instatements[i].op);
		a = (unsigned short)LittleShort(instatements[i].a);
		b = (unsigned short)LittleShort(instatements[i].b);
		c = (unsigned short)LittleShort(instatements[i].c);
		switch (op)
		{
		case OP_IF:
		case OP_IFNOT:
			b = (short)b;
			if (a >= prog->progs_numglobals || b + i < 0 || b + i >= prog->progs_numstatements)
				prog->error_cmd("PRVM_LoadProgs: out of bounds IF/IFNOT (statement %d) in %s", i, prog->name);
			prog->statements[i].op = op;
			prog->statements[i].operand[0] = remapglobal(a);
			prog->statements[i].operand[1] = -1;
			prog->statements[i].operand[2] = -1;
			prog->statements[i].jumpabsolute = i + b;
			break;
		case OP_GOTO:
			a = (short)a;
			if (a + i < 0 || a + i >= prog->progs_numstatements)
				prog->error_cmd("PRVM_LoadProgs: out of bounds GOTO (statement %d) in %s", i, prog->name);
			prog->statements[i].op = op;
			prog->statements[i].operand[0] = -1;
			prog->statements[i].operand[1] = -1;
			prog->statements[i].operand[2] = -1;
			prog->statements[i].jumpabsolute = i + a;
			break;
		default:
			Con_DPrintf("PRVM_LoadProgs: unknown opcode %d at statement %d in %s\n", (int)op, i, prog->name);
			break;
		                       
		case OP_ADD_F:
		case OP_ADD_V:
		case OP_SUB_F:
		case OP_SUB_V:
		case OP_MUL_F:
		case OP_MUL_V:
		case OP_MUL_FV:
		case OP_MUL_VF:
		case OP_DIV_F:
		case OP_BITAND:
		case OP_BITOR:
		case OP_GE:
		case OP_LE:
		case OP_GT:
		case OP_LT:
		case OP_AND:
		case OP_OR:
		case OP_EQ_F:
		case OP_EQ_V:
		case OP_EQ_S:
		case OP_EQ_E:
		case OP_EQ_FNC:
		case OP_NE_F:
		case OP_NE_V:
		case OP_NE_S:
		case OP_NE_E:
		case OP_NE_FNC:
		case OP_ADDRESS:
		case OP_LOAD_F:
		case OP_LOAD_FLD:
		case OP_LOAD_ENT:
		case OP_LOAD_S:
		case OP_LOAD_FNC:
		case OP_LOAD_V:
			if (a >= prog->progs_numglobals || b >= prog->progs_numglobals || c >= prog->progs_numglobals)
				prog->error_cmd("PRVM_LoadProgs: out of bounds global index (statement %d)", i);
			prog->statements[i].op = op;
			prog->statements[i].operand[0] = remapglobal(a);
			prog->statements[i].operand[1] = remapglobal(b);
			prog->statements[i].operand[2] = remapglobal(c);
			prog->statements[i].jumpabsolute = -1;
			break;
		                     
		case OP_NOT_F:
		case OP_NOT_V:
		case OP_NOT_S:
		case OP_NOT_FNC:
		case OP_NOT_ENT:
			if (a >= prog->progs_numglobals || c >= prog->progs_numglobals)
				prog->error_cmd("PRVM_LoadProgs: out of bounds global index (statement %d) in %s", i, prog->name);
			prog->statements[i].op = op;
			prog->statements[i].operand[0] = remapglobal(a);
			prog->statements[i].operand[1] = -1;
			prog->statements[i].operand[2] = remapglobal(c);
			prog->statements[i].jumpabsolute = -1;
			break;
		            
		case OP_STOREP_F:
		case OP_STOREP_ENT:
		case OP_STOREP_FLD:
		case OP_STOREP_S:
		case OP_STOREP_FNC:
		case OP_STORE_F:
		case OP_STORE_ENT:
		case OP_STORE_FLD:
		case OP_STORE_S:
		case OP_STORE_FNC:
		case OP_STATE:
		case OP_STOREP_V:
		case OP_STORE_V:
			if (a >= prog->progs_numglobals || b >= prog->progs_numglobals)
				prog->error_cmd("PRVM_LoadProgs: out of bounds global index (statement %d) in %s", i, prog->name);
			prog->statements[i].op = op;
			prog->statements[i].operand[0] = remapglobal(a);
			prog->statements[i].operand[1] = remapglobal(b);
			prog->statements[i].operand[2] = -1;
			prog->statements[i].jumpabsolute = -1;
			break;
		           
		case OP_CALL0:
			if ( a < prog->progs_numglobals)
				if ( prog->globals.ip[remapglobal(a)] >= 0 )
					if ( prog->globals.ip[remapglobal(a)] < prog->progs_numfunctions )
						if ( prog->functions[prog->globals.ip[remapglobal(a)]].first_statement == -642 )
							++prog->numexplicitcoveragestatements;
		case OP_CALL1:
		case OP_CALL2:
		case OP_CALL3:
		case OP_CALL4:
		case OP_CALL5:
		case OP_CALL6:
		case OP_CALL7:
		case OP_CALL8:
		case OP_DONE:
		case OP_RETURN:
			if ( a >= prog->progs_numglobals)
				prog->error_cmd("PRVM_LoadProgs: out of bounds global index (statement %d) in %s", i, prog->name);
			prog->statements[i].op = op;
			prog->statements[i].operand[0] = remapglobal(a);
			prog->statements[i].operand[1] = -1;
			prog->statements[i].operand[2] = -1;
			prog->statements[i].jumpabsolute = -1;
			break;
		}
	}
	if(prog->numstatements < 1)
	{
		prog->error_cmd("PRVM_LoadProgs: empty program in %s", prog->name);
	}
	else switch(prog->statements[prog->numstatements - 1].op)
	{
		case OP_RETURN:
		case OP_GOTO:
		case OP_DONE:
			break;
		default:
			prog->error_cmd("PRVM_LoadProgs: program may fall off the edge (does not end with RETURN, GOTO or DONE) in %s", prog->name);
			break;
	}

	                               
	if(!data)
		Mem_Free(dprograms);
	dprograms = NULL;

	                           
	for(i=0 ; i < numrequiredfunc ; i++)
		if(PRVM_ED_FindFunction(prog, required_func[i]) == 0)
			prog->error_cmd("%s: %s not found in %s",prog->name, required_func[i], filename);

	PRVM_LoadLNO(prog, filename);

	PRVM_Init_Exec(prog);

	if(*prvm_language.string)
	                                                                                 
	                                                                               
	{
		qboolean deftrans = prog == CLVM_prog;
		const char *realfilename = (prog != CLVM_prog ? filename : csqc_progname.string);
		if(deftrans)                                                                    
		{
			for (i=0 ; i<prog->numglobaldefs ; i++)
			{
				const char *name;
				name = PRVM_GetString(prog, prog->globaldefs[i].s_name);
				if((prog->globaldefs[i].type & ~DEF_SAVEGLOBAL) == ev_string)
				if(name && !strncmp(name, "dotranslate_", 12))
				{
					deftrans = false;
					break;
				}
			}
		}
		if(!strcmp(prvm_language.string, "dump"))
		{
			qfile_t *f = FS_OpenRealFile(va(vabuf, sizeof(vabuf), "%s.pot", realfilename), "w", false);
			Con_Printf("Dumping to %s.pot\n", realfilename);
			if(f)
			{
				for (i=0 ; i<prog->numglobaldefs ; i++)
				{
					const char *name;
					name = PRVM_GetString(prog, prog->globaldefs[i].s_name);
					if(deftrans ? (!name || strncmp(name, "notranslate_", 12)) : (name && !strncmp(name, "dotranslate_", 12)))
					if((prog->globaldefs[i].type & ~DEF_SAVEGLOBAL) == ev_string)
					{
						prvm_eval_t *val = PRVM_GLOBALFIELDVALUE(prog->globaldefs[i].ofs);
						const char *value = PRVM_GetString(prog, val->string);
						if(*value)
						{
							char buf[MAX_INPUTLINE];
							PRVM_PO_UnparseString(buf, value, sizeof(buf));
							FS_Printf(f, "msgid \"%s\"\nmsgstr \"\"\n\n", buf);
						}
					}
				}
				FS_Close(f);
			}
		}
		else
		{
			po_t *po = PRVM_PO_Load(
					va(vabuf, sizeof(vabuf), "%s.%s.po", realfilename, prvm_language.string),
					va(vabuf2, sizeof(vabuf2), "common.%s.po", prvm_language.string),
					prog->progs_mempool);
			if(po)
			{
				for (i=0 ; i<prog->numglobaldefs ; i++)
				{
					const char *name;
					name = PRVM_GetString(prog, prog->globaldefs[i].s_name);
					if(deftrans ? (!name || strncmp(name, "notranslate_", 12)) : (name && !strncmp(name, "dotranslate_", 12)))
					if((prog->globaldefs[i].type & ~DEF_SAVEGLOBAL) == ev_string)
					{
						prvm_eval_t *val = PRVM_GLOBALFIELDVALUE(prog->globaldefs[i].ofs);
						const char *value = PRVM_GetString(prog, val->string);
						if(*value)
						{
							value = PRVM_PO_Lookup(po, value);
							if(value)
								val->string = PRVM_SetEngineString(prog, value);
						}
					}
				}
			}
		}
	}

	for (cvar = cvar_vars; cvar; cvar = cvar->next)
		cvar->globaldefindex[prog - prvm_prog_list] = -1;

	for (i=0 ; i<prog->numglobaldefs ; i++)
	{
		const char *name;
		name = PRVM_GetString(prog, prog->globaldefs[i].s_name);
		                                     
		if(name
			&& !strncmp(name, "autocvar_", 9)
			&& !(strlen(name) > 1 && name[strlen(name)-2] == '_' && (name[strlen(name)-1] == 'x' || name[strlen(name)-1] == 'y' || name[strlen(name)-1] == 'z'))
		)
		{
			prvm_eval_t *val = PRVM_GLOBALFIELDVALUE(prog->globaldefs[i].ofs);
			cvar = Cvar_FindVar(name + 9);
			                                                                                            
			if(!cvar)
			{
				const char *value;
				char buf[64];
				Con_DPrintf("PRVM_LoadProgs: no cvar for autocvar global %s in %s, creating...\n", name, prog->name);
				switch(prog->globaldefs[i].type & ~DEF_SAVEGLOBAL)
				{
					case ev_float:
						if((float)((int)(val->_float)) == val->_float)
							dpsnprintf(buf, sizeof(buf), "%i", (int)(val->_float));
						else
							dpsnprintf(buf, sizeof(buf), "%.9g", val->_float);
						value = buf;
						break;
					case ev_vector:
						dpsnprintf(buf, sizeof(buf), "%.9g %.9g %.9g", val->vector[0], val->vector[1], val->vector[2]); value = buf;
						break;
					case ev_string:
						value = PRVM_GetString(prog, val->string);
						break;
					default:
						Con_Printf("PRVM_LoadProgs: invalid type of autocvar global %s in %s\n", name, prog->name);
						goto fail;
				}
				cvar = Cvar_Get(name + 9, value, 0, NULL);
				if((prog->globaldefs[i].type & ~DEF_SAVEGLOBAL) == ev_string)
				{
					val->string = PRVM_SetEngineString(prog, cvar->string);
					cvar->globaldefindex_stringno[prog - prvm_prog_list] = val->string;
				}
				if(!cvar)
					prog->error_cmd("PRVM_LoadProgs: could not create cvar for autocvar global %s in %s", name, prog->name);
				cvar->globaldefindex[prog - prvm_prog_list] = i;
			}
			else if((cvar->flags & CVAR_PRIVATE) == 0)
			{
				                                      
				int j;
				const char *s;
				switch(prog->globaldefs[i].type & ~DEF_SAVEGLOBAL)
				{
					case ev_float:
						val->_float = cvar->value;
						break;
					case ev_vector:
						s = cvar->string;
						VectorClear(val->vector);
						for (j = 0;j < 3;j++)
						{
							while (*s && ISWHITESPACE(*s))
								s++;
							if (!*s)
								break;
							val->vector[j] = atof(s);
							while (!ISWHITESPACE(*s))
								s++;
							if (!*s)
								break;
						}
						break;
					case ev_string:
						val->string = PRVM_SetEngineString(prog, cvar->string);
						cvar->globaldefindex_stringno[prog - prvm_prog_list] = val->string;
						break;
					default:
						Con_Printf("PRVM_LoadProgs: invalid type of autocvar global %s in %s\n", name, prog->name);
						goto fail;
				}
				cvar->globaldefindex[prog - prvm_prog_list] = i;
			}
			else
				Con_Printf("PRVM_LoadProgs: private cvar for autocvar global %s in %s\n", name, prog->name);
		}
fail:
		;
	}

	prog->loaded = TRUE;

	PRVM_UpdateBreakpoints(prog);

	                              

	prog->flag = 0;

	PRVM_FindOffsets(prog);

	prog->init_cmd(prog);

	                
	PRVM_MEM_Alloc(prog);

	                                                                      
	                            
	prog->inittime = realtime;
}


static void PRVM_Fields_f (void)
{
	prvm_prog_t *prog;
	int i, j, ednum, used, usedamount;
	int *counts;
	char tempstring[MAX_INPUTLINE], tempstring2[260];
	const char *name;
	prvm_edict_t *ed;
	ddef_t *d;
	prvm_eval_t *val;

	       
	  
                
  
                                 
         
  
   

	if(Cmd_Argc() != 2)
	{
		Con_Print("prvm_fields <program name>\n");
		return;
	}

	if (!(prog = PRVM_FriendlyProgFromString(Cmd_Argv(1))))
		return;

	counts = (int *)Mem_Alloc(tempmempool, prog->numfielddefs * sizeof(int));
	for (ednum = 0;ednum < prog->max_edicts;ednum++)
	{
		ed = PRVM_EDICT_NUM(ednum);
		if (ed->priv.required->free)
			continue;
		for (i = 1;i < prog->numfielddefs;i++)
		{
			d = &prog->fielddefs[i];
			name = PRVM_GetString(prog, d->s_name);
			if (name[strlen(name)-2] == '_')
				continue;	                       
			val = (prvm_eval_t *)(ed->fields.fp + d->ofs);
			                                              
			for (j = 0;j < prvm_type_size[d->type & ~DEF_SAVEGLOBAL];j++)
			{
				if (val->ivector[j])
				{
					counts[i]++;
					break;
				}
			}
		}
	}
	used = 0;
	usedamount = 0;
	tempstring[0] = 0;
	for (i = 0;i < prog->numfielddefs;i++)
	{
		d = &prog->fielddefs[i];
		name = PRVM_GetString(prog, d->s_name);
		if (name[strlen(name)-2] == '_')
			continue;	                       
		switch(d->type & ~DEF_SAVEGLOBAL)
		{
		case ev_string:
			strlcat(tempstring, "string   ", sizeof(tempstring));
			break;
		case ev_entity:
			strlcat(tempstring, "entity   ", sizeof(tempstring));
			break;
		case ev_function:
			strlcat(tempstring, "function ", sizeof(tempstring));
			break;
		case ev_field:
			strlcat(tempstring, "field    ", sizeof(tempstring));
			break;
		case ev_void:
			strlcat(tempstring, "void     ", sizeof(tempstring));
			break;
		case ev_float:
			strlcat(tempstring, "float    ", sizeof(tempstring));
			break;
		case ev_vector:
			strlcat(tempstring, "vector   ", sizeof(tempstring));
			break;
		case ev_pointer:
			strlcat(tempstring, "pointer  ", sizeof(tempstring));
			break;
		default:
			dpsnprintf (tempstring2, sizeof(tempstring2), "bad type %i ", d->type & ~DEF_SAVEGLOBAL);
			strlcat(tempstring, tempstring2, sizeof(tempstring));
			break;
		}
		if (strlen(name) > sizeof(tempstring2)-4)
		{
			memcpy (tempstring2, name, sizeof(tempstring2)-4);
			tempstring2[sizeof(tempstring2)-4] = tempstring2[sizeof(tempstring2)-3] = tempstring2[sizeof(tempstring2)-2] = '.';
			tempstring2[sizeof(tempstring2)-1] = 0;
			name = tempstring2;
		}
		strlcat(tempstring, name, sizeof(tempstring));
		for (j = (int)strlen(name);j < 25;j++)
			strlcat(tempstring, " ", sizeof(tempstring));
		dpsnprintf(tempstring2, sizeof(tempstring2), "%5d", counts[i]);
		strlcat(tempstring, tempstring2, sizeof(tempstring));
		strlcat(tempstring, "\n", sizeof(tempstring));
		if (strlen(tempstring) >= sizeof(tempstring)/2)
		{
			Con_Print(tempstring);
			tempstring[0] = 0;
		}
		if (counts[i])
		{
			used++;
			usedamount += prvm_type_size[d->type & ~DEF_SAVEGLOBAL];
		}
	}
	Mem_Free(counts);
	Con_Printf("%s: %i entity fields (%i in use), totalling %i bytes per edict (%i in use), %i edicts allocated, %i bytes total spent on edict fields (%i needed)\n", prog->name, prog->entityfields, used, prog->entityfields * 4, usedamount * 4, prog->max_edicts, prog->entityfields * 4 * prog->max_edicts, usedamount * 4 * prog->max_edicts);
}

static void PRVM_Globals_f (void)
{
	prvm_prog_t *prog;
	int i;
	const char *wildcard;
	int numculled;
		numculled = 0;
	       
	                 
  
                                 
         
    
	if(Cmd_Argc () < 2 || Cmd_Argc() > 3)
	{
		Con_Print("prvm_globals <program name> <optional name wildcard>\n");
		return;
	}

	if (!(prog = PRVM_FriendlyProgFromString(Cmd_Argv(1))))
		return;

	if( Cmd_Argc() == 3)
		wildcard = Cmd_Argv(2);
	else
		wildcard = NULL;

	Con_Printf("%s :", prog->name);

	for (i = 0;i < prog->numglobaldefs;i++)
	{
		if(wildcard)
			if( !matchpattern( PRVM_GetString(prog, prog->globaldefs[i].s_name), wildcard, 1) )
			{
				numculled++;
				continue;
			}
		Con_Printf("%s\n", PRVM_GetString(prog, prog->globaldefs[i].s_name));
	}
	Con_Printf("%i global variables, %i culled, totalling %i bytes\n", prog->numglobals, numculled, prog->numglobals * 4);
}

  
               
           
               
  
static void PRVM_Global_f(void)
{
	prvm_prog_t *prog;
	ddef_t *global;
	char valuebuf[MAX_INPUTLINE];
	if( Cmd_Argc() != 3 ) {
		Con_Printf( "prvm_global <program name> <global name>\n" );
		return;
	}

	if (!(prog = PRVM_FriendlyProgFromString(Cmd_Argv(1))))
		return;

	global = PRVM_ED_FindGlobal( prog, Cmd_Argv(2) );
	if( !global )
		Con_Printf( "No global '%s' in %s!\n", Cmd_Argv(2), Cmd_Argv(1) );
	else
		Con_Printf( "%s: %s\n", Cmd_Argv(2), PRVM_ValueString( prog, (etype_t)global->type, PRVM_GLOBALFIELDVALUE(global->ofs), valuebuf, sizeof(valuebuf) ) );
}

  
               
              
               
  
static void PRVM_GlobalSet_f(void)
{
	prvm_prog_t *prog;
	ddef_t *global;
	if( Cmd_Argc() != 4 ) {
		Con_Printf( "prvm_globalset <program name> <global name> <value>\n" );
		return;
	}

	if (!(prog = PRVM_FriendlyProgFromString(Cmd_Argv(1))))
		return;

	global = PRVM_ED_FindGlobal( prog, Cmd_Argv(2) );
	if( !global )
		Con_Printf( "No global '%s' in %s!\n", Cmd_Argv(2), Cmd_Argv(1) );
	else
		PRVM_ED_ParseEpair( prog, NULL, global, Cmd_Argv(3), true );
}

  
                      
                      
                      
  
typedef struct
{
	char break_statement[256];
	char watch_global[256];
	int watch_edict;
	char watch_field[256];
}
debug_data_t;
static debug_data_t debug_data[PRVM_PROG_MAX];

void PRVM_Breakpoint(prvm_prog_t *prog, int stack_index, const char *text)
{
	char vabuf[1024];
	Con_Printf("PRVM_Breakpoint: %s\n", text);
	PRVM_PrintState(prog, stack_index);
	if (prvm_breakpointdump.integer)
		Host_Savegame_to(prog, va(vabuf, sizeof(vabuf), "breakpoint-%s.dmp", prog->name));
}

void PRVM_Watchpoint(prvm_prog_t *prog, int stack_index, const char *text, etype_t type, prvm_eval_t *o, prvm_eval_t *n)
{
	size_t sz = sizeof(prvm_vec_t) * ((type & ~DEF_SAVEGLOBAL) == ev_vector ? 3 : 1);
	if (memcmp(o, n, sz))
	{
		char buf[1024];
		char valuebuf_o[128];
		char valuebuf_n[128];
		PRVM_UglyValueString(prog, type, o, valuebuf_o, sizeof(valuebuf_o));
		PRVM_UglyValueString(prog, type, n, valuebuf_n, sizeof(valuebuf_n));
		dpsnprintf(buf, sizeof(buf), "%s: %s -> %s", text, valuebuf_o, valuebuf_n);
		PRVM_Breakpoint(prog, stack_index, buf);
		memcpy(o, n, sz);
	}
}

static void PRVM_UpdateBreakpoints(prvm_prog_t *prog)
{
	debug_data_t *debug = &debug_data[prog - prvm_prog_list];
	if (!prog->loaded)
		return;
	if (debug->break_statement[0])
	{
		if (debug->break_statement[0] >= '0' && debug->break_statement[0] <= '9')
		{
			prog->break_statement = atoi(debug->break_statement);
			prog->break_stack_index = 0;
		}
		else
		{
			mfunction_t *func;
			func = PRVM_ED_FindFunction (prog, debug->break_statement);
			if (!func)
			{
				Con_Printf("%s progs: no function or statement named %s to break on!\n", prog->name, debug->break_statement);
				prog->break_statement = -1;
			}
			else
			{
				prog->break_statement = func->first_statement;
				prog->break_stack_index = 1;
			}
		}
		if (prog->break_statement >= -1)
			Con_Printf("%s progs: breakpoint is at statement %d\n", prog->name, prog->break_statement);
	}
	else
		prog->break_statement = -1;

	if (debug->watch_global[0])
	{
		ddef_t *global = PRVM_ED_FindGlobal( prog, debug->watch_global );
		if( !global )
		{
			Con_Printf( "%s progs: no global named '%s' to watch!\n", prog->name, debug->watch_global );
			prog->watch_global_type = ev_void;
		}
		else
		{
			size_t sz = sizeof(prvm_vec_t) * ((global->type  & ~DEF_SAVEGLOBAL) == ev_vector ? 3 : 1);
			prog->watch_global = global->ofs;
			prog->watch_global_type = (etype_t)global->type;
			memcpy(&prog->watch_global_value, PRVM_GLOBALFIELDVALUE(prog->watch_global), sz);
		}
		if (prog->watch_global_type != ev_void)
			Con_Printf("%s progs: global watchpoint is at global index %d\n", prog->name, prog->watch_global);
	}
	else
		prog->watch_global_type = ev_void;

	if (debug->watch_field[0])
	{
		ddef_t *field = PRVM_ED_FindField( prog, debug->watch_field );
		if( !field )
		{
			Con_Printf( "%s progs: no field named '%s' to watch!\n", prog->name, debug->watch_field );
			prog->watch_field_type = ev_void;
		}
		else
		{
			size_t sz = sizeof(prvm_vec_t) * ((field->type & ~DEF_SAVEGLOBAL) == ev_vector ? 3 : 1);
			prog->watch_edict = debug->watch_edict;
			prog->watch_field = field->ofs;
			prog->watch_field_type = (etype_t)field->type;
			if (prog->watch_edict < prog->num_edicts)
				memcpy(&prog->watch_edictfield_value, PRVM_EDICTFIELDVALUE(PRVM_EDICT_NUM(prog->watch_edict), prog->watch_field), sz);
			else
				memset(&prog->watch_edictfield_value, 0, sz);
		}
		if (prog->watch_edict != ev_void)
			Con_Printf("%s progs: edict field watchpoint is at edict %d field index %d\n", prog->name, prog->watch_edict, prog->watch_field);
	}
	else
		prog->watch_field_type = ev_void;
}

static void PRVM_Breakpoint_f(void)
{
	prvm_prog_t *prog;

	if( Cmd_Argc() == 2 ) {
		if (!(prog = PRVM_FriendlyProgFromString(Cmd_Argv(1))))
			return;
		{
			debug_data_t *debug = &debug_data[prog - prvm_prog_list];
			debug->break_statement[0] = 0;
		}
		PRVM_UpdateBreakpoints(prog);
		return;
	}
	if( Cmd_Argc() != 3 ) {
		Con_Printf( "prvm_breakpoint <program name> <function name | statement>\n" );
		return;
	}

	if (!(prog = PRVM_ProgFromString(Cmd_Argv(1))))
		return;

	{
		debug_data_t *debug = &debug_data[prog - prvm_prog_list];
		strlcpy(debug->break_statement, Cmd_Argv(2), sizeof(debug->break_statement));
	}
	PRVM_UpdateBreakpoints(prog);
}

static void PRVM_GlobalWatchpoint_f(void)
{
	prvm_prog_t *prog;

	if( Cmd_Argc() == 2 ) {
		if (!(prog = PRVM_FriendlyProgFromString(Cmd_Argv(1))))
			return;
		{
			debug_data_t *debug = &debug_data[prog - prvm_prog_list];
			debug->watch_global[0] = 0;
		}
		PRVM_UpdateBreakpoints(prog);
		return;
	}
	if( Cmd_Argc() != 3 ) {
		Con_Printf( "prvm_globalwatchpoint <program name> <global name>\n" );
		return;
	}

	if (!(prog = PRVM_ProgFromString(Cmd_Argv(1))))
		return;

	{
		debug_data_t *debug = &debug_data[prog - prvm_prog_list];
		strlcpy(debug->watch_global, Cmd_Argv(2), sizeof(debug->watch_global));
	}
	PRVM_UpdateBreakpoints(prog);
}

static void PRVM_EdictWatchpoint_f(void)
{
	prvm_prog_t *prog;

	if( Cmd_Argc() == 2 ) {
		if (!(prog = PRVM_FriendlyProgFromString(Cmd_Argv(1))))
			return;
		{
			debug_data_t *debug = &debug_data[prog - prvm_prog_list];
			debug->watch_field[0] = 0;
		}
		PRVM_UpdateBreakpoints(prog);
		return;
	}
	if( Cmd_Argc() != 4 ) {
		Con_Printf( "prvm_edictwatchpoint <program name> <edict number> <field name>\n" );
		return;
	}

	if (!(prog = PRVM_ProgFromString(Cmd_Argv(1))))
		return;

	{
		debug_data_t *debug = &debug_data[prog - prvm_prog_list];
		debug->watch_edict = atoi(Cmd_Argv(2));
		strlcpy(debug->watch_field, Cmd_Argv(3), sizeof(debug->watch_field));
	}
	PRVM_UpdateBreakpoints(prog);
}

  
               
         
               
  
void PRVM_Init (void)
{
	Cmd_AddCommand ("prvm_edict", PRVM_ED_PrintEdict_f, "print all data about an entity number in the selected VM (server, client, menu)");
	Cmd_AddCommand ("prvm_edicts", PRVM_ED_PrintEdicts_f, "prints all data about all entities in the selected VM (server, client, menu)");
	Cmd_AddCommand ("prvm_edictcount", PRVM_ED_Count_f, "prints number of active entities in the selected VM (server, client, menu)");
	Cmd_AddCommand ("prvm_profile", PRVM_Profile_f, "prints execution statistics about the most used QuakeC functions in the selected VM (server, client, menu)");
	Cmd_AddCommand ("prvm_childprofile", PRVM_ChildProfile_f, "prints execution statistics about the most used QuakeC functions in the selected VM (server, client, menu), sorted by time taken in function with child calls");
	Cmd_AddCommand ("prvm_callprofile", PRVM_CallProfile_f, "prints execution statistics about the most time consuming QuakeC calls from the engine in the selected VM (server, client, menu)");
	Cmd_AddCommand ("prvm_fields", PRVM_Fields_f, "prints usage statistics on properties (how many entities have non-zero values) in the selected VM (server, client, menu)");
	Cmd_AddCommand ("prvm_globals", PRVM_Globals_f, "prints all global variables in the selected VM (server, client, menu)");
	Cmd_AddCommand ("prvm_global", PRVM_Global_f, "prints value of a specified global variable in the selected VM (server, client, menu)");
	Cmd_AddCommand ("prvm_globalset", PRVM_GlobalSet_f, "sets value of a specified global variable in the selected VM (server, client, menu)");
	Cmd_AddCommand ("prvm_edictset", PRVM_ED_EdictSet_f, "changes value of a specified property of a specified entity in the selected VM (server, client, menu)");
	Cmd_AddCommand ("prvm_edictget", PRVM_ED_EdictGet_f, "retrieves the value of a specified property of a specified entity in the selected VM (server, client menu) into a cvar or to the console");
	Cmd_AddCommand ("prvm_globalget", PRVM_ED_GlobalGet_f, "retrieves the value of a specified global variable in the selected VM (server, client menu) into a cvar or to the console");
	Cmd_AddCommand ("prvm_printfunction", PRVM_PrintFunction_f, "prints a disassembly (QuakeC instructions) of the specified function in the selected VM (server, client, menu)");
	Cmd_AddCommand ("cl_cmd", PRVM_GameCommand_Client_f, "calls the client QC function GameCommand with the supplied string as argument");
	Cmd_AddCommand ("menu_cmd", PRVM_GameCommand_Menu_f, "calls the menu QC function GameCommand with the supplied string as argument");
	Cmd_AddCommand ("sv_cmd", PRVM_GameCommand_Server_f, "calls the server QC function GameCommand with the supplied string as argument");

	Cmd_AddCommand ("prvm_breakpoint", PRVM_Breakpoint_f, "marks a statement or function as breakpoint (when this is executed, a stack trace is printed); to actually halt and investigate state, combine this with a gdb breakpoint on PRVM_Breakpoint, or with prvm_breakpointdump; run with just progs name to clear breakpoint");
	Cmd_AddCommand ("prvm_globalwatchpoint", PRVM_GlobalWatchpoint_f, "marks a global as watchpoint (when this is executed, a stack trace is printed); to actually halt and investigate state, combine this with a gdb breakpoint on PRVM_Breakpoint, or with prvm_breakpointdump; run with just progs name to clear watchpoint");
	Cmd_AddCommand ("prvm_edictwatchpoint", PRVM_EdictWatchpoint_f, "marks an entity field as watchpoint (when this is executed, a stack trace is printed); to actually halt and investigate state, combine this with a gdb breakpoint on PRVM_Breakpoint, or with prvm_breakpointdump; run with just progs name to clear watchpoint");

	Cvar_RegisterVariable (&prvm_language);
	Cvar_RegisterVariable (&prvm_traceqc);
	Cvar_RegisterVariable (&prvm_statementprofiling);
	Cvar_RegisterVariable (&prvm_timeprofiling);
	Cvar_RegisterVariable (&prvm_coverage);
	Cvar_RegisterVariable (&prvm_backtraceforwarnings);
	Cvar_RegisterVariable (&prvm_leaktest);
	Cvar_RegisterVariable (&prvm_leaktest_follow_targetname);
	Cvar_RegisterVariable (&prvm_leaktest_ignore_classnames);
	Cvar_RegisterVariable (&prvm_errordump);
	Cvar_RegisterVariable (&prvm_breakpointdump);
	Cvar_RegisterVariable (&prvm_reuseedicts_startuptime);
	Cvar_RegisterVariable (&prvm_reuseedicts_neverinsameframe);

	                                                                                                                           
	prvm_runawaycheck = !COM_CheckParm("-norunaway");

	                
}

  
               
             
               
  
void PRVM_Prog_Init(prvm_prog_t *prog)
{
	PRVM_Prog_Reset(prog);
	prog->leaktest_active = prvm_leaktest.integer != 0;
}

                                                                    
unsigned int PRVM_EDICT_NUM_ERROR(prvm_prog_t *prog, unsigned int n, const char *filename, int fileline)
{
	prog->error_cmd("PRVM_EDICT_NUM: %s: bad number %i (called at %s:%i)", prog->name, n, filename, fileline);
	return 0;
}

#define PRVM_KNOWNSTRINGBASE 0x40000000

const char *PRVM_GetString(prvm_prog_t *prog, int num)
{
	if (num < 0)
	{
		          
		VM_Warning(prog, "PRVM_GetString: Invalid string offset (%i < 0)\n", num);
		return "";
	}
	else if (num < prog->stringssize)
	{
		                                 
		return prog->strings + num;
	}
	else if (num <= prog->stringssize + prog->tempstringsbuf.maxsize)
	{
		                                                                                  
		num -= prog->stringssize;
		if (num < prog->tempstringsbuf.cursize)
			return (char *)prog->tempstringsbuf.data + num;
		else
		{
			VM_Warning(prog, "PRVM_GetString: Invalid temp-string offset (%i >= %i prog->tempstringsbuf.cursize)\n", num, prog->tempstringsbuf.cursize);
			return "";
		}
	}
	else if (num & PRVM_KNOWNSTRINGBASE)
	{
		                   
		num = num - PRVM_KNOWNSTRINGBASE;
		if (num >= 0 && num < prog->numknownstrings)
		{
			if (!prog->knownstrings[num])
			{
				VM_Warning(prog, "PRVM_GetString: Invalid zone-string offset (%i has been freed)\n", num);
				return "";
			}
			return prog->knownstrings[num];
		}
		else
		{
			VM_Warning(prog, "PRVM_GetString: Invalid zone-string offset (%i >= %i)\n", num, prog->numknownstrings);
			return "";
		}
	}
	else
	{
		                        
		VM_Warning(prog, "PRVM_GetString: Invalid constant-string offset (%i >= %i prog->stringssize)\n", num, prog->stringssize);
		return "";
	}
}

const char *PRVM_ChangeEngineString(prvm_prog_t *prog, int i, const char *s)
{
	const char *old;
	i = i - PRVM_KNOWNSTRINGBASE;
	if(i < 0 || i >= prog->numknownstrings)
		prog->error_cmd("PRVM_ChangeEngineString: s is not an engine string");
	old = prog->knownstrings[i];
	prog->knownstrings[i] = s;
	return old;
}

int PRVM_SetEngineString(prvm_prog_t *prog, const char *s)
{
	int i;
	if (!s)
		return 0;
	if (s >= prog->strings && s <= prog->strings + prog->stringssize)
		prog->error_cmd("PRVM_SetEngineString: s in prog->strings area");
	                                                        
	                                                                                  
	if (s >= (char *)prog->tempstringsbuf.data && s < (char *)prog->tempstringsbuf.data + prog->tempstringsbuf.maxsize)
		return prog->stringssize + (s - (char *)prog->tempstringsbuf.data);
	                                     
	for (i = 0;i < prog->numknownstrings;i++)
		if (prog->knownstrings[i] == s)
			return PRVM_KNOWNSTRINGBASE + i;
	                            
	if (developer_insane.integer)
		Con_DPrintf("new engine string %p = \"%s\"\n", s, s);
	for (i = prog->firstfreeknownstring;i < prog->numknownstrings;i++)
		if (!prog->knownstrings[i])
			break;
	if (i >= prog->numknownstrings)
	{
		if (i >= prog->maxknownstrings)
		{
			const char **oldstrings = prog->knownstrings;
			const unsigned char *oldstrings_freeable = prog->knownstrings_freeable;
			const char **oldstrings_origin = prog->knownstrings_origin;
			prog->maxknownstrings += 128;
			prog->knownstrings = (const char **)PRVM_Alloc(prog->maxknownstrings * sizeof(char *));
			prog->knownstrings_freeable = (unsigned char *)PRVM_Alloc(prog->maxknownstrings * sizeof(unsigned char));
			if(prog->leaktest_active)
				prog->knownstrings_origin = (const char **)PRVM_Alloc(prog->maxknownstrings * sizeof(char *));
			if (prog->numknownstrings)
			{
				memcpy((char **)prog->knownstrings, oldstrings, prog->numknownstrings * sizeof(char *));
				memcpy((char **)prog->knownstrings_freeable, oldstrings_freeable, prog->numknownstrings * sizeof(unsigned char));
				if(prog->leaktest_active)
					memcpy((char **)prog->knownstrings_origin, oldstrings_origin, prog->numknownstrings * sizeof(char *));
			}
		}
		prog->numknownstrings++;
	}
	prog->firstfreeknownstring = i + 1;
	prog->knownstrings[i] = s;
	prog->knownstrings_freeable[i] = false;
	if(prog->leaktest_active)
		prog->knownstrings_origin[i] = NULL;
	return PRVM_KNOWNSTRINGBASE + i;
}

                       

                                                                     
                                                     
                                                                         
                                                                         
           
                                                   

int PRVM_SetTempString(prvm_prog_t *prog, const char *s)
{
	int size;
	char *t;
	if (!s)
		return 0;
	size = (int)strlen(s) + 1;
	if (developer_insane.integer)
		Con_DPrintf("PRVM_SetTempString: cursize %i, size %i\n", prog->tempstringsbuf.cursize, size);
	if (prog->tempstringsbuf.maxsize < prog->tempstringsbuf.cursize + size)
	{
		sizebuf_t old = prog->tempstringsbuf;
		if (prog->tempstringsbuf.cursize + size >= 1<<28)
			prog->error_cmd("PRVM_SetTempString: ran out of tempstring memory!  (refusing to grow tempstring buffer over 256MB, cursize %i, size %i)\n", prog->tempstringsbuf.cursize, size);
		prog->tempstringsbuf.maxsize = max(prog->tempstringsbuf.maxsize, 65536);
		while (prog->tempstringsbuf.maxsize < prog->tempstringsbuf.cursize + size)
			prog->tempstringsbuf.maxsize *= 2;
		if (prog->tempstringsbuf.maxsize != old.maxsize || prog->tempstringsbuf.data == NULL)
		{
			Con_DPrintf("PRVM_SetTempString: enlarging tempstrings buffer (%iKB -> %iKB)\n", old.maxsize/1024, prog->tempstringsbuf.maxsize/1024);
			prog->tempstringsbuf.data = (unsigned char *) Mem_Alloc(prog->progs_mempool, prog->tempstringsbuf.maxsize);
			if (old.data)
			{
				if (old.cursize)
					memcpy(prog->tempstringsbuf.data, old.data, old.cursize);
				Mem_Free(old.data);
			}
		}
	}
	t = (char *)prog->tempstringsbuf.data + prog->tempstringsbuf.cursize;
	memcpy(t, s, size);
	prog->tempstringsbuf.cursize += size;
	return PRVM_SetEngineString(prog, t);
}

int PRVM_AllocString(prvm_prog_t *prog, size_t bufferlength, char **pointer)
{
	int i;
	if (!bufferlength)
	{
		if (pointer)
			*pointer = NULL;
		return 0;
	}
	for (i = prog->firstfreeknownstring;i < prog->numknownstrings;i++)
		if (!prog->knownstrings[i])
			break;
	if (i >= prog->numknownstrings)
	{
		if (i >= prog->maxknownstrings)
		{
			const char **oldstrings = prog->knownstrings;
			const unsigned char *oldstrings_freeable = prog->knownstrings_freeable;
			const char **oldstrings_origin = prog->knownstrings_origin;
			prog->maxknownstrings += 128;
			prog->knownstrings = (const char **)PRVM_Alloc(prog->maxknownstrings * sizeof(char *));
			prog->knownstrings_freeable = (unsigned char *)PRVM_Alloc(prog->maxknownstrings * sizeof(unsigned char));
			if(prog->leaktest_active)
				prog->knownstrings_origin = (const char **)PRVM_Alloc(prog->maxknownstrings * sizeof(char *));
			if (prog->numknownstrings)
			{
				memcpy((char **)prog->knownstrings, oldstrings, prog->numknownstrings * sizeof(char *));
				memcpy((char **)prog->knownstrings_freeable, oldstrings_freeable, prog->numknownstrings * sizeof(unsigned char));
				if(prog->leaktest_active)
					memcpy((char **)prog->knownstrings_origin, oldstrings_origin, prog->numknownstrings * sizeof(char *));
			}
			if (oldstrings)
				Mem_Free((char **)oldstrings);
			if (oldstrings_freeable)
				Mem_Free((unsigned char *)oldstrings_freeable);
			if (oldstrings_origin)
				Mem_Free((char **)oldstrings_origin);
		}
		prog->numknownstrings++;
	}
	prog->firstfreeknownstring = i + 1;
	prog->knownstrings[i] = (char *)PRVM_Alloc(bufferlength);
	prog->knownstrings_freeable[i] = true;
	if(prog->leaktest_active)
		prog->knownstrings_origin[i] = PRVM_AllocationOrigin(prog);
	if (pointer)
		*pointer = (char *)(prog->knownstrings[i]);
	return PRVM_KNOWNSTRINGBASE + i;
}

void PRVM_FreeString(prvm_prog_t *prog, int num)
{
	if (num == 0)
		prog->error_cmd("PRVM_FreeString: attempt to free a NULL string");
	else if (num >= 0 && num < prog->stringssize)
		prog->error_cmd("PRVM_FreeString: attempt to free a constant string");
	else if (num >= PRVM_KNOWNSTRINGBASE && num < PRVM_KNOWNSTRINGBASE + prog->numknownstrings)
	{
		num = num - PRVM_KNOWNSTRINGBASE;
		if (!prog->knownstrings[num])
			prog->error_cmd("PRVM_FreeString: attempt to free a non-existent or already freed string");
		if (!prog->knownstrings_freeable[num])
			prog->error_cmd("PRVM_FreeString: attempt to free a string owned by the engine");
		PRVM_Free((char *)prog->knownstrings[num]);
		if(prog->leaktest_active)
			if(prog->knownstrings_origin[num])
				PRVM_Free((char *)prog->knownstrings_origin[num]);
		prog->knownstrings[num] = NULL;
		prog->knownstrings_freeable[num] = false;
		prog->firstfreeknownstring = min(prog->firstfreeknownstring, num);
	}
	else
		prog->error_cmd("PRVM_FreeString: invalid string offset %i", num);
}

static qboolean PRVM_IsStringReferenced(prvm_prog_t *prog, string_t string)
{
	int i, j;

	for (i = 0;i < prog->numglobaldefs;i++)
	{
		ddef_t *d = &prog->globaldefs[i];
		if((etype_t)((int) d->type & ~DEF_SAVEGLOBAL) != ev_string)
			continue;
		if(string == PRVM_GLOBALFIELDSTRING(d->ofs))
			return true;
	}

	for(j = 0; j < prog->num_edicts; ++j)
	{
		prvm_edict_t *ed = PRVM_EDICT_NUM(j);
		if (ed->priv.required->free)
			continue;
		for (i=0; i<prog->numfielddefs; ++i)
		{
			ddef_t *d = &prog->fielddefs[i];
			if((etype_t)((int) d->type & ~DEF_SAVEGLOBAL) != ev_string)
				continue;
			if(string == PRVM_EDICTFIELDSTRING(ed, d->ofs))
				return true;
		}
	}

	return false;
}

static qboolean PRVM_IsEdictRelevant(prvm_prog_t *prog, prvm_edict_t *edict)
{
	char vabuf[1024];
	char vabuf2[1024];
	if(PRVM_NUM_FOR_EDICT(edict) <= prog->reserved_edicts)
		return true;                    
	if (edict->priv.required->freetime <= prog->inittime)
		return true;                          
	if (prog == SVVM_prog)
	{
		if(PRVM_serveredictfloat(edict, solid))                                           
			return true;
		if(PRVM_serveredictfloat(edict, modelindex))                
			return true;
		if(PRVM_serveredictfloat(edict, effects))                    
			return true;
		if(PRVM_serveredictfunction(edict, think))                         
			if(PRVM_serveredictfloat(edict, nextthink) > 0)                                      
				return true;
		if(PRVM_serveredictfloat(edict, takedamage))
			return true;
		if(*prvm_leaktest_ignore_classnames.string)
		{
			if(strstr(va(vabuf, sizeof(vabuf), " %s ", prvm_leaktest_ignore_classnames.string), va(vabuf2, sizeof(vabuf2), " %s ", PRVM_GetString(prog, PRVM_serveredictstring(edict, classname)))))
				return true;
		}
	}
	else if (prog == CLVM_prog)
	{
		                                   
		if(PRVM_clientedictfloat(edict, entnum))                  
			return true;
		if(PRVM_clientedictfloat(edict, modelindex))                
			return true;
		if(PRVM_clientedictfloat(edict, effects))                    
			return true;
		if(PRVM_clientedictfunction(edict, think))                         
			if(PRVM_clientedictfloat(edict, nextthink) > 0)                                      
				return true;
		if(*prvm_leaktest_ignore_classnames.string)
		{
			if(strstr(va(vabuf, sizeof(vabuf), " %s ", prvm_leaktest_ignore_classnames.string), va(vabuf2, sizeof(vabuf2), " %s ", PRVM_GetString(prog, PRVM_clientedictstring(edict, classname)))))
				return true;
		}
	}
	else
	{
		                                     
	}
	return false;
}

static qboolean PRVM_IsEdictReferenced(prvm_prog_t *prog, prvm_edict_t *edict, int mark)
{
	int i, j;
	int edictnum = PRVM_NUM_FOR_EDICT(edict);
	const char *targetname = NULL;

	if (prog == SVVM_prog && prvm_leaktest_follow_targetname.integer)
		targetname = PRVM_GetString(prog, PRVM_serveredictstring(edict, targetname));

	if(targetname)
		if(!*targetname)      
			targetname = NULL;

	for(j = 0; j < prog->num_edicts; ++j)
	{
		prvm_edict_t *ed = PRVM_EDICT_NUM(j);
		if (ed->priv.required->mark < mark)
			continue;
		if(ed == edict)
			continue;
		if(targetname)
		{
			const char *target = PRVM_GetString(prog, PRVM_serveredictstring(ed, target));
			if(target)
				if(!strcmp(target, targetname))
					return true;
		}
		for (i=0; i<prog->numfielddefs; ++i)
		{
			ddef_t *d = &prog->fielddefs[i];
			if((etype_t)((int) d->type & ~DEF_SAVEGLOBAL) != ev_entity)
				continue;
			if(edictnum == PRVM_EDICTFIELDEDICT(ed, d->ofs))
				return true;
		}
	}

	return false;
}

static void PRVM_MarkReferencedEdicts(prvm_prog_t *prog)
{
	int i, j;
	qboolean found_new;
	int stage;

	                                                                                                   
	stage = 1;
	for(j = 0; j < prog->num_edicts; ++j)
	{
		prvm_edict_t *ed = PRVM_EDICT_NUM(j);
		if(ed->priv.required->free)
			continue;
		ed->priv.required->mark = PRVM_IsEdictRelevant(prog, ed) ? stage : 0;
	}
	for (i = 0;i < prog->numglobaldefs;i++)
	{
		ddef_t *d = &prog->globaldefs[i];
		prvm_edict_t *ed;
		if((etype_t)((int) d->type & ~DEF_SAVEGLOBAL) != ev_entity)
			continue;
		j = PRVM_GLOBALFIELDEDICT(d->ofs);
		if (i < 0 || j >= prog->max_edicts) {
			Con_Printf("Invalid entity reference from global %s.\n", PRVM_GetString(prog, d->s_name));
			continue;
		}
		ed = PRVM_EDICT_NUM(j);;
		ed->priv.required->mark = stage;
	}

	                                                                                      
	do
	{
		found_new = false;
		for(j = 0; j < prog->num_edicts; ++j)
		{
			prvm_edict_t *ed = PRVM_EDICT_NUM(j);
			if(ed->priv.required->free)
				continue;
			if(ed->priv.required->mark)
				continue;
			if(PRVM_IsEdictReferenced(prog, ed, stage))
			{
				ed->priv.required->mark = stage + 1;
				found_new = true;
			}
		}
		++stage;
	}
	while(found_new);
	Con_DPrintf("leak check used %d stages to find all references\n", stage);
}

void PRVM_LeakTest(prvm_prog_t *prog)
{
	int i, j;
	qboolean leaked = false;

	if(!prog->leaktest_active)
		return;

	             
	for (i = 0; i < prog->numknownstrings; ++i)
	{
		if(prog->knownstrings[i])
		if(prog->knownstrings_freeable[i])
		if(prog->knownstrings_origin[i])
		if(!PRVM_IsStringReferenced(prog, PRVM_KNOWNSTRINGBASE + i))
		{
			Con_Printf("Unreferenced string found!\n  Value: %s\n  Origin: %s\n", prog->knownstrings[i], prog->knownstrings_origin[i]);
			leaked = true;
		}
	}

	            
	PRVM_MarkReferencedEdicts(prog);
	for(j = 0; j < prog->num_edicts; ++j)
	{
		prvm_edict_t *ed = PRVM_EDICT_NUM(j);
		if(ed->priv.required->free)
			continue;
		if(!ed->priv.required->mark)
		if(ed->priv.required->allocation_origin)
		{
			Con_Printf("Unreferenced edict found!\n  Allocated at: %s\n", ed->priv.required->allocation_origin);
			PRVM_ED_Print(prog, ed, NULL);
			Con_Print("\n");
			leaked = true;
		}

		ed->priv.required->mark = 0;                               
	}

	for (i = 0; i < (int)Mem_ExpandableArray_IndexRange(&prog->stringbuffersarray); ++i)
	{
		prvm_stringbuffer_t *stringbuffer = (prvm_stringbuffer_t*) Mem_ExpandableArray_RecordAtIndex(&prog->stringbuffersarray, i);
		if(stringbuffer)
		if(stringbuffer->origin)
		{
			Con_Printf("Open string buffer handle found!\n  Allocated at: %s\n", stringbuffer->origin);
			leaked = true;
		}
	}

	for(i = 0; i < PRVM_MAX_OPENFILES; ++i)
	{
		if(prog->openfiles[i])
		if(prog->openfiles_origin[i])
		{
			Con_Printf("Open file handle found!\n  Allocated at: %s\n", prog->openfiles_origin[i]);
			leaked = true;
		}
	}

	for(i = 0; i < PRVM_MAX_OPENSEARCHES; ++i)
	{
		if(prog->opensearches[i])
		if(prog->opensearches_origin[i])
		{
			Con_Printf("Open search handle found!\n  Allocated at: %s\n", prog->opensearches_origin[i]);
			leaked = true;
		}
	}

	if(!leaked)
		Con_Printf("Congratulations. No leaks found.\n");
}
