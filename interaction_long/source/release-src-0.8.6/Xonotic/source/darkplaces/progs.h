  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

#ifndef PROGS_H
#define PROGS_H
#include "pr_comp.h"			                       

#define ENTITYGRIDAREAS 16
#define MAX_ENTITYCLUSTERS 16

#define	GEOMTYPE_NONE      -1
#define	GEOMTYPE_SOLID      0
#define	GEOMTYPE_BOX		1
#define	GEOMTYPE_SPHERE		2
#define	GEOMTYPE_CAPSULE	3
#define	GEOMTYPE_TRIMESH	4
#define	GEOMTYPE_CYLINDER	5
#define	GEOMTYPE_CAPSULE_X	6
#define	GEOMTYPE_CAPSULE_Y	7
#define	GEOMTYPE_CAPSULE_Z	8
#define	GEOMTYPE_CYLINDER_X	9
#define	GEOMTYPE_CYLINDER_Y	10
#define	GEOMTYPE_CYLINDER_Z	11

#define JOINTTYPE_NONE      0
#define JOINTTYPE_POINT     1
#define JOINTTYPE_HINGE     2
#define JOINTTYPE_SLIDER    3
#define JOINTTYPE_UNIVERSAL 4
#define JOINTTYPE_HINGE2    5
#define JOINTTYPE_FIXED    -1

#define FORCETYPE_NONE       0
#define FORCETYPE_FORCE      1
#define FORCETYPE_FORCEATPOS 2
#define FORCETYPE_TORQUE     3

#define ODEFUNC_ENABLE		1
#define ODEFUNC_DISABLE		2
#define ODEFUNC_FORCE       3
#define ODEFUNC_TORQUE      4

typedef struct edict_odefunc_s
{
	int type;
	vec3_t v1;
	vec3_t v2;
	struct edict_odefunc_s *next;
}edict_odefunc_t;

typedef struct edict_engineprivate_s
{
	                               
	qboolean free;
	                                                                        
	                                                              
	float freetime;
	                             
	int mark;
	                                                                   
	const char *allocation_origin;
	                                                                          
	                                                             
	qboolean move;

	                                                                       
	vec3_t cullmins, cullmaxs;
	int pvs_numclusters;
	int pvs_clusterlist[MAX_ENTITYCLUSTERS];

	                                               
	link_t areagrid[ENTITYGRIDAREAS];
	                                                                 
	                                                                     
	int areagridmarknumber;
	                                      
	vec3_t areamins, areamaxs;

	                                                                               
	                  
	entity_state_t baseline;

	                                                          
	int suspendedinairflag;

	                                                                               
	qboolean waterposition_forceupdate;                                                                                      
	vec3_t waterposition_origin;                                 

	                                                                        
	                                            
	vec3_t moved_from;
	vec3_t moved_fromangles;

	framegroupblend_t framegroupblend[MAX_FRAMEGROUPBLENDS];
	frameblend_t frameblend[MAX_FRAMEBLENDS];
	skeleton_t skeleton;

	                     
	qboolean ode_physics;
	void *ode_body;
	void *ode_geom;
	void *ode_joint;
	float *ode_vertex3f;
	int *ode_element3i;
	int ode_numvertices;
	int ode_numtriangles;
	edict_odefunc_t *ode_func;
	vec3_t ode_mins;
	vec3_t ode_maxs;
	vec3_t ode_scale;
	vec_t ode_mass;
	float ode_friction;
	vec3_t ode_origin;
	vec3_t ode_velocity;
	vec3_t ode_angles;
	vec3_t ode_avelocity;
	qboolean ode_gravity;
	int ode_modelindex;
	vec_t ode_movelimit;                                         
	matrix4x4_t ode_offsetmatrix;
	matrix4x4_t ode_offsetimatrix;
	int ode_joint_type;
	int ode_joint_enemy;
	int ode_joint_aiment;
	vec3_t ode_joint_origin;                
	vec3_t ode_joint_angles;              
	vec3_t ode_joint_velocity;                     
	vec3_t ode_joint_movedir;              
	void *ode_massbuf;
}
edict_engineprivate_t;

#endif
