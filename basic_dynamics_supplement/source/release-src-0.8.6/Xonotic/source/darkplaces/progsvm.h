  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
  
                                                                                  
                                 

                                                                                    
                                                    
                                    
  

#ifndef PROGSVM_H
#define PROGSVM_H

#include "pr_comp.h"			                       
#include "progdefs.h"			                             
#include "clprogdefs.h"			                             

#ifndef DP_SMALLMEMORY
#define PROFILING
#endif

typedef struct prvm_stack_s
{
	int				s;
	mfunction_t		*f;
	double			tprofile_acc;
	double			profile_acc;
	double			builtinsprofile_acc;
} prvm_stack_t;


typedef union prvm_eval_s
{
	prvm_int_t		string;
	prvm_vec_t	_float;
	prvm_vec_t	vector[3];
	prvm_int_t		function;
	prvm_int_t		ivector[3];
	prvm_int_t		_int;
	prvm_int_t		edict;
} prvm_eval_t;

typedef struct prvm_required_field_s
{
	int type;
	const char *name;
} prvm_required_field_t;


                                                                                 
                          
typedef struct prvm_edict_private_s
{
	qboolean free;
	float freetime;                                                                   
	int mark;                                                                                            
#define PRVM_EDICT_MARK_WAIT_FOR_SETORIGIN -1
#define PRVM_EDICT_MARK_SETORIGIN_CAUGHT -2
	const char *allocation_origin;
} prvm_edict_private_t;

typedef struct prvm_edict_s
{
	                                                              
	                           
	union
	{
		prvm_edict_private_t *required;
		prvm_vec_t *fp;
		prvm_int_t *ip;
		                                                            
		                                                                
		edict_engineprivate_t *server;
		                                          
		                                                                     
		                                                  
		                                          
		                              
		                      
		                                
		                                 
		      
		                                          
		                  
		                   
		                      
		                                
		                                 
		                                              
	} priv;
	                                                      
	union
	{
		prvm_vec_t *fp;
		prvm_int_t *ip;
                       
                         
	} fields;
} prvm_edict_t;

#define VMPOLYGONS_MAXPOINTS 64

typedef struct vmpolygons_triangle_s
{
	rtexture_t		*texture;
	int				drawflag;
	qboolean hasalpha;
	unsigned short	elements[3];
} vmpolygons_triangle_t;

typedef struct vmpolygons_s
{
	mempool_t		*pool;
	qboolean		initialized;

	int				max_vertices;
	int				num_vertices;
	float			*data_vertex3f;
	float			*data_color4f;
	float			*data_texcoord2f;

	int				max_triangles;
	int				num_triangles;
	vmpolygons_triangle_t *data_triangles;
	unsigned short	*data_sortedelement3s;

	qboolean		begin_active;
	int	begin_draw2d;
	rtexture_t		*begin_texture;
	int				begin_drawflag;
	int				begin_vertices;
	float			begin_vertex[VMPOLYGONS_MAXPOINTS][3];
	float			begin_color[VMPOLYGONS_MAXPOINTS][4];
	float			begin_texcoord[VMPOLYGONS_MAXPOINTS][2];
	qboolean		begin_texture_hasalpha;
} vmpolygons_t;

extern prvm_eval_t prvm_badvalue;

#define PRVM_alledictfloat(ed, fieldname)    (PRVM_EDICTFIELDFLOAT(ed, prog->fieldoffsets.fieldname))
#define PRVM_alledictvector(ed, fieldname)   (PRVM_EDICTFIELDVECTOR(ed, prog->fieldoffsets.fieldname))
#define PRVM_alledictstring(ed, fieldname)   (PRVM_EDICTFIELDSTRING(ed, prog->fieldoffsets.fieldname))
#define PRVM_alledictedict(ed, fieldname)    (PRVM_EDICTFIELDEDICT(ed, prog->fieldoffsets.fieldname))
#define PRVM_alledictfunction(ed, fieldname) (PRVM_EDICTFIELDFUNCTION(ed, prog->fieldoffsets.fieldname))
#define PRVM_allglobalfloat(fieldname)       (PRVM_GLOBALFIELDFLOAT(prog->globaloffsets.fieldname))
#define PRVM_allglobalvector(fieldname)      (PRVM_GLOBALFIELDVECTOR(prog->globaloffsets.fieldname))
#define PRVM_allglobalstring(fieldname)      (PRVM_GLOBALFIELDSTRING(prog->globaloffsets.fieldname))
#define PRVM_allglobaledict(fieldname)       (PRVM_GLOBALFIELDEDICT(prog->globaloffsets.fieldname))
#define PRVM_allglobalfunction(fieldname)    (PRVM_GLOBALFIELDFUNCTION(prog->globaloffsets.fieldname))
#define PRVM_allfunction(funcname)           (prog->funcoffsets.funcname)

#define PRVM_drawedictfloat(ed, fieldname)    (PRVM_EDICTFIELDFLOAT(ed, prog->fieldoffsets.fieldname))
#define PRVM_drawedictvector(ed, fieldname)   (PRVM_EDICTFIELDVECTOR(ed, prog->fieldoffsets.fieldname))
#define PRVM_drawedictstring(ed, fieldname)   (PRVM_EDICTFIELDSTRING(ed, prog->fieldoffsets.fieldname))
#define PRVM_drawedictedict(ed, fieldname)    (PRVM_EDICTFIELDEDICT(ed, prog->fieldoffsets.fieldname))
#define PRVM_drawedictfunction(ed, fieldname) (PRVM_EDICTFIELDFUNCTION(ed, prog->fieldoffsets.fieldname))
#define PRVM_drawglobalfloat(fieldname)       (PRVM_GLOBALFIELDFLOAT(prog->globaloffsets.fieldname))
#define PRVM_drawglobalvector(fieldname)      (PRVM_GLOBALFIELDVECTOR(prog->globaloffsets.fieldname))
#define PRVM_drawglobalstring(fieldname)      (PRVM_GLOBALFIELDSTRING(prog->globaloffsets.fieldname))
#define PRVM_drawglobaledict(fieldname)       (PRVM_GLOBALFIELDEDICT(prog->globaloffsets.fieldname))
#define PRVM_drawglobalfunction(fieldname)    (PRVM_GLOBALFIELDFUNCTION(prog->globaloffsets.fieldname))
#define PRVM_drawfunction(funcname)           (prog->funcoffsets.funcname)

#define PRVM_gameedictfloat(ed, fieldname)    (PRVM_EDICTFIELDFLOAT(ed, prog->fieldoffsets.fieldname))
#define PRVM_gameedictvector(ed, fieldname)   (PRVM_EDICTFIELDVECTOR(ed, prog->fieldoffsets.fieldname))
#define PRVM_gameedictstring(ed, fieldname)   (PRVM_EDICTFIELDSTRING(ed, prog->fieldoffsets.fieldname))
#define PRVM_gameedictedict(ed, fieldname)    (PRVM_EDICTFIELDEDICT(ed, prog->fieldoffsets.fieldname))
#define PRVM_gameedictfunction(ed, fieldname) (PRVM_EDICTFIELDFUNCTION(ed, prog->fieldoffsets.fieldname))
#define PRVM_gameglobalfloat(fieldname)       (PRVM_GLOBALFIELDFLOAT(prog->globaloffsets.fieldname))
#define PRVM_gameglobalvector(fieldname)      (PRVM_GLOBALFIELDVECTOR(prog->globaloffsets.fieldname))
#define PRVM_gameglobalstring(fieldname)      (PRVM_GLOBALFIELDSTRING(prog->globaloffsets.fieldname))
#define PRVM_gameglobaledict(fieldname)       (PRVM_GLOBALFIELDEDICT(prog->globaloffsets.fieldname))
#define PRVM_gameglobalfunction(fieldname)    (PRVM_GLOBALFIELDFUNCTION(prog->globaloffsets.fieldname))
#define PRVM_gamefunction(funcname)           (prog->funcoffsets.funcname)

#define PRVM_serveredictfloat(ed, fieldname)    (PRVM_EDICTFIELDFLOAT(ed, prog->fieldoffsets.fieldname))
#define PRVM_serveredictvector(ed, fieldname)   (PRVM_EDICTFIELDVECTOR(ed, prog->fieldoffsets.fieldname))
#define PRVM_serveredictstring(ed, fieldname)   (PRVM_EDICTFIELDSTRING(ed, prog->fieldoffsets.fieldname))
#define PRVM_serveredictedict(ed, fieldname)    (PRVM_EDICTFIELDEDICT(ed, prog->fieldoffsets.fieldname))
#define PRVM_serveredictfunction(ed, fieldname) (PRVM_EDICTFIELDFUNCTION(ed, prog->fieldoffsets.fieldname))
#define PRVM_serverglobalfloat(fieldname)       (PRVM_GLOBALFIELDFLOAT(prog->globaloffsets.fieldname))
#define PRVM_serverglobalvector(fieldname)      (PRVM_GLOBALFIELDVECTOR(prog->globaloffsets.fieldname))
#define PRVM_serverglobalstring(fieldname)      (PRVM_GLOBALFIELDSTRING(prog->globaloffsets.fieldname))
#define PRVM_serverglobaledict(fieldname)       (PRVM_GLOBALFIELDEDICT(prog->globaloffsets.fieldname))
#define PRVM_serverglobalfunction(fieldname)    (PRVM_GLOBALFIELDFUNCTION(prog->globaloffsets.fieldname))
#define PRVM_serverfunction(funcname)           (prog->funcoffsets.funcname)

#define PRVM_clientedictfloat(ed, fieldname)    (PRVM_EDICTFIELDFLOAT(ed, prog->fieldoffsets.fieldname))
#define PRVM_clientedictvector(ed, fieldname)   (PRVM_EDICTFIELDVECTOR(ed, prog->fieldoffsets.fieldname))
#define PRVM_clientedictstring(ed, fieldname)   (PRVM_EDICTFIELDSTRING(ed, prog->fieldoffsets.fieldname))
#define PRVM_clientedictedict(ed, fieldname)    (PRVM_EDICTFIELDEDICT(ed, prog->fieldoffsets.fieldname))
#define PRVM_clientedictfunction(ed, fieldname) (PRVM_EDICTFIELDFUNCTION(ed, prog->fieldoffsets.fieldname))
#define PRVM_clientglobalfloat(fieldname)       (PRVM_GLOBALFIELDFLOAT(prog->globaloffsets.fieldname))
#define PRVM_clientglobalvector(fieldname)      (PRVM_GLOBALFIELDVECTOR(prog->globaloffsets.fieldname))
#define PRVM_clientglobalstring(fieldname)      (PRVM_GLOBALFIELDSTRING(prog->globaloffsets.fieldname))
#define PRVM_clientglobaledict(fieldname)       (PRVM_GLOBALFIELDEDICT(prog->globaloffsets.fieldname))
#define PRVM_clientglobalfunction(fieldname)    (PRVM_GLOBALFIELDFUNCTION(prog->globaloffsets.fieldname))
#define PRVM_clientfunction(funcname)           (prog->funcoffsets.funcname)

#define PRVM_menuedictfloat(ed, fieldname)    (PRVM_EDICTFIELDFLOAT(ed, prog->fieldoffsets.fieldname))
#define PRVM_menuedictvector(ed, fieldname)   (PRVM_EDICTFIELDVECTOR(ed, prog->fieldoffsets.fieldname))
#define PRVM_menuedictstring(ed, fieldname)   (PRVM_EDICTFIELDSTRING(ed, prog->fieldoffsets.fieldname))
#define PRVM_menuedictedict(ed, fieldname)    (PRVM_EDICTFIELDEDICT(ed, prog->fieldoffsets.fieldname))
#define PRVM_menuedictfunction(ed, fieldname) (PRVM_EDICTFIELDFUNCTION(ed, prog->fieldoffsets.fieldname))
#define PRVM_menuglobalfloat(fieldname)       (PRVM_GLOBALFIELDFLOAT(prog->globaloffsets.fieldname))
#define PRVM_menuglobalvector(fieldname)      (PRVM_GLOBALFIELDVECTOR(prog->globaloffsets.fieldname))
#define PRVM_menuglobalstring(fieldname)      (PRVM_GLOBALFIELDSTRING(prog->globaloffsets.fieldname))
#define PRVM_menuglobaledict(fieldname)       (PRVM_GLOBALFIELDEDICT(prog->globaloffsets.fieldname))
#define PRVM_menuglobalfunction(fieldname)    (PRVM_GLOBALFIELDFUNCTION(prog->globaloffsets.fieldname))
#define PRVM_menufunction(funcname)           (prog->funcoffsets.funcname)

#if 1
#define PRVM_EDICTFIELDVALUE(ed, fieldoffset)    ((fieldoffset) < 0 ? Con_Printf("Invalid fieldoffset at %s:%i\n", __FILE__, __LINE__), &prvm_badvalue : (prvm_eval_t *)((ed)->fields.fp + (fieldoffset)))
#define PRVM_EDICTFIELDFLOAT(ed, fieldoffset)    (PRVM_EDICTFIELDVALUE(ed, fieldoffset)->_float)
#define PRVM_EDICTFIELDVECTOR(ed, fieldoffset)   (PRVM_EDICTFIELDVALUE(ed, fieldoffset)->vector)
#define PRVM_EDICTFIELDSTRING(ed, fieldoffset)   (PRVM_EDICTFIELDVALUE(ed, fieldoffset)->string)
#define PRVM_EDICTFIELDEDICT(ed, fieldoffset)    (PRVM_EDICTFIELDVALUE(ed, fieldoffset)->edict)
#define PRVM_EDICTFIELDFUNCTION(ed, fieldoffset) (PRVM_EDICTFIELDVALUE(ed, fieldoffset)->function)
#define PRVM_GLOBALFIELDVALUE(fieldoffset)       ((fieldoffset) < 0 ? Con_Printf("Invalid fieldoffset at %s:%i\n", __FILE__, __LINE__), &prvm_badvalue : (prvm_eval_t *)(prog->globals.fp + (fieldoffset)))
#define PRVM_GLOBALFIELDFLOAT(fieldoffset)       (PRVM_GLOBALFIELDVALUE(fieldoffset)->_float)
#define PRVM_GLOBALFIELDVECTOR(fieldoffset)      (PRVM_GLOBALFIELDVALUE(fieldoffset)->vector)
#define PRVM_GLOBALFIELDSTRING(fieldoffset)      (PRVM_GLOBALFIELDVALUE(fieldoffset)->string)
#define PRVM_GLOBALFIELDEDICT(fieldoffset)       (PRVM_GLOBALFIELDVALUE(fieldoffset)->edict)
#define PRVM_GLOBALFIELDFUNCTION(fieldoffset)    (PRVM_GLOBALFIELDVALUE(fieldoffset)->function)
#else
#define PRVM_EDICTFIELDVALUE(ed, fieldoffset) ((prvm_eval_t *)(ed->fields.fp + fieldoffset))
#define PRVM_EDICTFIELDFLOAT(ed, fieldoffset) (((prvm_eval_t *)(ed->fields.fp + fieldoffset))->_float)
#define PRVM_EDICTFIELDVECTOR(ed, fieldoffset) (((prvm_eval_t *)(ed->fields.fp + fieldoffset))->vector)
#define PRVM_EDICTFIELDSTRING(ed, fieldoffset) (((prvm_eval_t *)(ed->fields.fp + fieldoffset))->string)
#define PRVM_EDICTFIELDEDICT(ed, fieldoffset) (((prvm_eval_t *)(ed->fields.fp + fieldoffset))->edict)
#define PRVM_EDICTFIELDFUNCTION(ed, fieldoffset) (((prvm_eval_t *)(ed->fields.fp + fieldoffset))->function)
#define PRVM_GLOBALFIELDVALUE(fieldoffset) ((prvm_eval_t *)(prog->globals.fp + fieldoffset))
#define PRVM_GLOBALFIELDFLOAT(fieldoffset) (((prvm_eval_t *)(prog->globals.fp + fieldoffset))->_float)
#define PRVM_GLOBALFIELDVECTOR(fieldoffset) (((prvm_eval_t *)(prog->globals.fp + fieldoffset))->vector)
#define PRVM_GLOBALFIELDSTRING(fieldoffset) (((prvm_eval_t *)(prog->globals.fp + fieldoffset))->string)
#define PRVM_GLOBALFIELDEDICT(fieldoffset) (((prvm_eval_t *)(prog->globals.fp + fieldoffset))->edict)
#define PRVM_GLOBALFIELDFUNCTION(fieldoffset) (((prvm_eval_t *)(prog->globals.fp + fieldoffset))->function)
#endif

                                                                              
#define PRVM_OP_STATE		1

#ifdef DP_SMALLMEMORY
#define	PRVM_MAX_STACK_DEPTH		128
#define	PRVM_LOCALSTACK_SIZE		2048

#define PRVM_MAX_OPENFILES 16
#define PRVM_MAX_OPENSEARCHES 8
#else
#define	PRVM_MAX_STACK_DEPTH		1024
#define	PRVM_LOCALSTACK_SIZE		16384

#define PRVM_MAX_OPENFILES 256
#define PRVM_MAX_OPENSEARCHES 128
#endif

struct prvm_prog_s;
typedef void (*prvm_builtin_t) (struct prvm_prog_s *prog);

                                      
typedef struct prvm_prog_fieldoffsets_s
{
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
#define PRVM_DECLARE_field(x) int x;
#define PRVM_DECLARE_global(x)
#define PRVM_DECLARE_function(x)
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
prvm_prog_fieldoffsets_t;

                                       
typedef struct prvm_prog_globaloffsets_s
{
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
#define PRVM_DECLARE_field(x)
#define PRVM_DECLARE_global(x) int x;
#define PRVM_DECLARE_function(x)
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
prvm_prog_globaloffsets_t;

                                        
typedef struct prvm_prog_funcoffsets_s
{
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
#define PRVM_DECLARE_field(x)
#define PRVM_DECLARE_global(x)
#define PRVM_DECLARE_function(x) int x;
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
prvm_prog_funcoffsets_t;

                     
#define STRINGBUFFER_SAVED     1                        
#define STRINGBUFFER_QCFLAGS   1                             
#define STRINGBUFFER_TEMP      128                      
typedef struct prvm_stringbuffer_s
{
	int max_strings;
	int num_strings;
	char **strings;
	const char *origin;
	unsigned char flags;
}
prvm_stringbuffer_t;

                                                                       
                                                                                                
typedef struct prvm_prog_s
{
	double				starttime;                                              
	double				inittime;                                                                                              
	double				profiletime;                                                                                   
	mfunction_t			*functions;
	int				functions_covered;
	char				*strings;
	int					stringssize;
	ddef_t				*fielddefs;
	ddef_t				*globaldefs;
	mstatement_t		*statements;
	int					entityfields;			                                                         
	int					entityfieldsarea;		                                                                      

	                                     
	int					progs_version;
	int					progs_crc;
	int					progs_numstatements;
	int					progs_numglobaldefs;
	int					progs_numfielddefs;
	int					progs_numfunctions;
	int					progs_numstrings;
	int					progs_numglobals;
	int					progs_entityfields;

	                                                  
	int					numstatements;
	int					numglobaldefs;
	int					numfielddefs;
	int					numfunctions;
	int					numstrings;
	int					numglobals;

	int					*statement_linenums;                         
	int					*statement_columnnums;                         

	double				*statement_profile;                                                     
	int				statements_covered;
	double				*explicit_profile;                                                     
	int				explicit_covered;
	int				numexplicitcoveragestatements;

	union {
		prvm_vec_t *fp;
		prvm_int_t *ip;
                         
                            
	} globals;

	int					maxknownstrings;
	int					numknownstrings;
	                                                        
	                                                  
	int					firstfreeknownstring;
	const char			**knownstrings;
	unsigned char		*knownstrings_freeable;
	const char          **knownstrings_origin;
	const char			***stringshash;

	memexpandablearray_t	stringbuffersarray;

	                                                                         
	mempool_t			*progs_mempool;          

	prvm_builtin_t		*builtins;          
	int					numbuiltins;          

	int					argc;

	int					trace;
	int					break_statement;
	int					break_stack_index;
	int					watch_global;
	etype_t					watch_global_type;
	prvm_eval_t				watch_global_value;
	int					watch_edict;
	int					watch_field;
	etype_t					watch_field_type;
	prvm_eval_t				watch_edictfield_value;

	mfunction_t			*xfunction;
	int					xstatement;

	                                                
	                                                        
	prvm_stack_t		stack[PRVM_MAX_STACK_DEPTH+1];
	int					depth;

	prvm_int_t			localstack[PRVM_LOCALSTACK_SIZE];
	int					localstack_used;

	unsigned short		filecrc;

	                                                                              
	                                                                              

	qfile_t				*openfiles[PRVM_MAX_OPENFILES];
	const char *         openfiles_origin[PRVM_MAX_OPENFILES];
	fssearch_t			*opensearches[PRVM_MAX_OPENSEARCHES];
	const char *         opensearches_origin[PRVM_MAX_OPENSEARCHES];
	skeleton_t			*skeletons[MAX_EDICTS];

	                                                                                     
	sizebuf_t			tempstringsbuf;

	                                                                                       
	                                                                     
	vmpolygons_t		vmpolygons;

	                                                    
	int					num_edicts;
	                                                                  
	int					max_edicts;          
	                                          
	int					limit_edicts;          

	                                               
	int					reserved_edicts;          

	prvm_edict_t		*edicts;
	prvm_vec_t		*edictsfields;
	void				*edictprivate;

	                                    
	int					edictprivate_size;          

	prvm_prog_fieldoffsets_t	fieldoffsets;
	prvm_prog_globaloffsets_t	globaloffsets;
	prvm_prog_funcoffsets_t	funcoffsets;

	                                                                       
	                                    
	qboolean			allowworldwrites;

	                                                                             
	const char			*name;          

	                                                             
	int				flag;

	const char			*extensionstring;          

	qboolean			loadintoworld;          

	                                            
	qboolean			loaded;
	qboolean			leaktest_active;

	                                                                                                  
	void *po;

	                                   
	const char *statestring;

	struct animatemodel_cache *animatemodel_cache;

                                 

                                            
                           
                           

	                                                                              

	ddef_t				*self;                                            

	                                                                              
	                    

	void				(*begin_increase_edicts)(struct prvm_prog_s *prog);                                           
	void				(*end_increase_edicts)(struct prvm_prog_s *prog);          

	void				(*init_edict)(struct prvm_prog_s *prog, prvm_edict_t *edict);                                     
	void				(*free_edict)(struct prvm_prog_s *prog, prvm_edict_t *ed);                               

	void				(*count_edicts)(struct prvm_prog_s *prog);                                  

	qboolean			(*load_edict)(struct prvm_prog_s *prog, prvm_edict_t *ent);                                       

	void				(*init_cmd)(struct prvm_prog_s *prog);                                
	void				(*reset_cmd)(struct prvm_prog_s *prog);                                 

	void				(*error_cmd)(const char *format, ...) DP_FUNC_PRINTF(1);          

	void				(*ExecuteProgram)(struct prvm_prog_s *prog, func_t fnum, const char *errormessage);                                                      
} prvm_prog_t;

typedef enum prvm_progindex_e
{
	PRVM_PROG_SERVER,
	PRVM_PROG_CLIENT,
	PRVM_PROG_MENU,
	PRVM_PROG_MAX
}
prvm_progindex_t;

extern prvm_prog_t prvm_prog_list[PRVM_PROG_MAX];
prvm_prog_t *PRVM_ProgFromString(const char *str);
prvm_prog_t *PRVM_FriendlyProgFromString(const char *str);                                                                                                                          
#define PRVM_GetProg(n) (&prvm_prog_list[(n)])
#define PRVM_ProgLoaded(n) (PRVM_GetProg(n)->loaded)
#define SVVM_prog (&prvm_prog_list[PRVM_PROG_SERVER])
#define CLVM_prog (&prvm_prog_list[PRVM_PROG_CLIENT])
#ifdef CONFIG_MENU
#define MVM_prog (&prvm_prog_list[PRVM_PROG_MENU])
#endif

                                                                              
                 

extern prvm_builtin_t vm_sv_builtins[];
extern prvm_builtin_t vm_cl_builtins[];
extern prvm_builtin_t vm_m_builtins[];

extern const int vm_sv_numbuiltins;
extern const int vm_cl_numbuiltins;
extern const int vm_m_numbuiltins;

extern const char * vm_sv_extensions;                         
extern const char * vm_m_extensions;

void SVVM_init_cmd(prvm_prog_t *prog);
void SVVM_reset_cmd(prvm_prog_t *prog);

void CLVM_init_cmd(prvm_prog_t *prog);
void CLVM_reset_cmd(prvm_prog_t *prog);

#ifdef CONFIG_MENU
void MVM_init_cmd(prvm_prog_t *prog);
void MVM_reset_cmd(prvm_prog_t *prog);
#endif

void VM_Cmd_Init(prvm_prog_t *prog);
void VM_Cmd_Reset(prvm_prog_t *prog);
                                                                              

void PRVM_Init (void);

#ifdef PROFILING
void SVVM_ExecuteProgram (prvm_prog_t *prog, func_t fnum, const char *errormessage);
void CLVM_ExecuteProgram (prvm_prog_t *prog, func_t fnum, const char *errormessage);
#ifdef CONFIG_MENU
void MVM_ExecuteProgram (prvm_prog_t *prog, func_t fnum, const char *errormessage);
#endif
#else
#define SVVM_ExecuteProgram PRVM_ExecuteProgram
#define CLVM_ExecuteProgram PRVM_ExecuteProgram
#ifdef CONFIG_MENU
#define MVM_ExecuteProgram PRVM_ExecuteProgram
#endif
void PRVM_ExecuteProgram (prvm_prog_t *prog, func_t fnum, const char *errormessage);
#endif

#define PRVM_Alloc(buffersize) Mem_Alloc(prog->progs_mempool, buffersize)
#define PRVM_Free(buffer) Mem_Free(buffer)

void PRVM_Profile (prvm_prog_t *prog, int maxfunctions, double mintime, int sortby);
void PRVM_Profile_f (void);
void PRVM_ChildProfile_f (void);
void PRVM_CallProfile_f (void);
void PRVM_PrintFunction_f (void);

void PRVM_PrintState(prvm_prog_t *prog, int stack_index);
void PRVM_Crash(prvm_prog_t *prog);
void PRVM_ShortStackTrace(prvm_prog_t *prog, char *buf, size_t bufsize);
const char *PRVM_AllocationOrigin(prvm_prog_t *prog);

ddef_t *PRVM_ED_FindField(prvm_prog_t *prog, const char *name);
ddef_t *PRVM_ED_FindGlobal(prvm_prog_t *prog, const char *name);
mfunction_t *PRVM_ED_FindFunction(prvm_prog_t *prog, const char *name);

int PRVM_ED_FindFieldOffset(prvm_prog_t *prog, const char *name);
int PRVM_ED_FindGlobalOffset(prvm_prog_t *prog, const char *name);
func_t PRVM_ED_FindFunctionOffset(prvm_prog_t *prog, const char *name);
#define PRVM_ED_FindFieldOffset_FromStruct(st, field) prog->fieldoffsets . field = ((int *)(&((st *)NULL)-> field ) - ((int *)NULL))
#define PRVM_ED_FindGlobalOffset_FromStruct(st, field) prog->globaloffsets . field = ((int *)(&((st *)NULL)-> field ) - ((int *)NULL))

void PRVM_MEM_IncreaseEdicts(prvm_prog_t *prog);

qboolean PRVM_ED_CanAlloc(prvm_prog_t *prog, prvm_edict_t *e);
prvm_edict_t *PRVM_ED_Alloc(prvm_prog_t *prog);
void PRVM_ED_Free(prvm_prog_t *prog, prvm_edict_t *ed);
void PRVM_ED_ClearEdict(prvm_prog_t *prog, prvm_edict_t *e);

void PRVM_PrintFunctionStatements(prvm_prog_t *prog, const char *name);
void PRVM_ED_Print(prvm_prog_t *prog, prvm_edict_t *ed, const char *wildcard_fieldname);
void PRVM_ED_Write(prvm_prog_t *prog, qfile_t *f, prvm_edict_t *ed);
const char *PRVM_ED_ParseEdict(prvm_prog_t *prog, const char *data, prvm_edict_t *ent);

void PRVM_ED_WriteGlobals(prvm_prog_t *prog, qfile_t *f);
void PRVM_ED_ParseGlobals(prvm_prog_t *prog, const char *data);

void PRVM_ED_LoadFromFile(prvm_prog_t *prog, const char *data);

unsigned int PRVM_EDICT_NUM_ERROR(prvm_prog_t *prog, unsigned int n, const char *filename, int fileline);
#define	PRVM_EDICT(n) (((unsigned)(n) < (unsigned int)prog->max_edicts) ? (unsigned int)(n) : PRVM_EDICT_NUM_ERROR(prog, (unsigned int)(n), __FILE__, __LINE__))
#define	PRVM_EDICT_NUM(n) (prog->edicts + PRVM_EDICT(n))

                                           
#define PRVM_NUM_FOR_EDICT(e) ((int)((prvm_edict_t *)(e) - prog->edicts))
                                          

#define	PRVM_NEXT_EDICT(e) ((e) + 1)

#define PRVM_EDICT_TO_PROG(e) (PRVM_NUM_FOR_EDICT(e))
                                          
#define PRVM_PROG_TO_EDICT(n) (PRVM_EDICT_NUM(n))
                                          

                                                                              

#define	PRVM_G_FLOAT(o) (prog->globals.fp[o])
#define	PRVM_G_INT(o) (prog->globals.ip[o])
#define	PRVM_G_EDICT(o) (PRVM_PROG_TO_EDICT(prog->globals.ip[o]))
#define PRVM_G_EDICTNUM(o) PRVM_NUM_FOR_EDICT(PRVM_G_EDICT(o))
#define	PRVM_G_VECTOR(o) (&prog->globals.fp[o])
#define	PRVM_G_STRING(o) (PRVM_GetString(prog, prog->globals.ip[o]))
                                                        

                             
#define	PRVM_E_FLOAT(e,o) (e->fields.fp[o])
#define	PRVM_E_INT(e,o) (e->fields.ip[o])
                                                 
#define	PRVM_E_STRING(e,o) (PRVM_GetString(prog, e->fields.ip[o]))

extern	int		prvm_type_size[8];                                                              
                                                                                                 

void PRVM_Init_Exec(prvm_prog_t *prog);

void PRVM_ED_PrintEdicts_f (void);
void PRVM_ED_PrintNum (prvm_prog_t *prog, int ent, const char *wildcard_fieldname);

const char *PRVM_GetString(prvm_prog_t *prog, int num);
int PRVM_SetEngineString(prvm_prog_t *prog, const char *s);
const char *PRVM_ChangeEngineString(prvm_prog_t *prog, int i, const char *s);
int PRVM_SetTempString(prvm_prog_t *prog, const char *s);
int PRVM_AllocString(prvm_prog_t *prog, size_t bufferlength, char **pointer);
void PRVM_FreeString(prvm_prog_t *prog, int num);

ddef_t *PRVM_ED_FieldAtOfs(prvm_prog_t *prog, int ofs);
qboolean PRVM_ED_ParseEpair(prvm_prog_t *prog, prvm_edict_t *ent, ddef_t *key, const char *s, qboolean parsebackslash);
char *PRVM_UglyValueString(prvm_prog_t *prog, etype_t type, prvm_eval_t *val, char *line, size_t linelength);
char *PRVM_GlobalString(prvm_prog_t *prog, int ofs, char *line, size_t linelength);
char *PRVM_GlobalStringNoContents(prvm_prog_t *prog, int ofs, char *line, size_t linelength);

                                                                              

  
                  
                          
                                                       
                             
  
                                              
void PRVM_Prog_Init(prvm_prog_t *prog);
void PRVM_Prog_Load(prvm_prog_t *prog, const char *filename, unsigned char *data, fs_offset_t size, int numrequiredfunc, const char **required_func, int numrequiredfields, prvm_required_field_t *required_field, int numrequiredglobals, prvm_required_field_t *required_global);
void PRVM_Prog_Reset(prvm_prog_t *prog);

void PRVM_StackTrace(prvm_prog_t *prog);
void PRVM_Breakpoint(prvm_prog_t *prog, int stack_index, const char *text);
void PRVM_Watchpoint(prvm_prog_t *prog, int stack_index, const char *text, etype_t type, prvm_eval_t *o, prvm_eval_t *n);

void VM_Warning(prvm_prog_t *prog, const char *fmt, ...) DP_FUNC_PRINTF(2);

void VM_GenerateFrameGroupBlend(prvm_prog_t *prog, framegroupblend_t *framegroupblend, const prvm_edict_t *ed);
void VM_FrameBlendFromFrameGroupBlend(frameblend_t *frameblend, const framegroupblend_t *framegroupblend, const dp_model_t *model, double curtime);
void VM_UpdateEdictSkeleton(prvm_prog_t *prog, prvm_edict_t *ed, const dp_model_t *edmodel, const frameblend_t *frameblend);
void VM_RemoveEdictSkeleton(prvm_prog_t *prog, prvm_edict_t *ed);

void PRVM_ExplicitCoverageEvent(prvm_prog_t *prog, mfunction_t *func, int statement);

#endif
