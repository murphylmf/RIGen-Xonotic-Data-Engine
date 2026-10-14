  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
          

#ifndef WORLD_H
#define WORLD_H

#include "collision.h"

#define MOVE_NORMAL     0
#define MOVE_NOMONSTERS 1
#define MOVE_MISSILE    2
#define MOVE_WORLDONLY  3
#define MOVE_HITMODEL   4

#define AREA_GRID 128
#define AREA_GRIDNODES (AREA_GRID * AREA_GRID)

typedef struct link_s
{
	int entitynumber;
	struct link_s	*prev, *next;
} link_t;

typedef struct world_physics_s
{
	                         
	qboolean ode;                                 
	void *ode_world;
	void *ode_space;
	void *ode_contactgroup;
	                                                                      
	int ode_iterations;
	                                                  
	vec_t ode_step;
	                                             
	vec_t ode_time;
	        
	int ode_numobjects;                       
	int ode_activeovjects;                        
	                                                                     
	                    
	vec_t ode_movelimit;
}
world_physics_t;

struct prvm_prog_s;

typedef struct world_s
{
	                    
	char filename[MAX_QPATH];
	vec3_t mins;
	vec3_t maxs;
	struct prvm_prog_s *prog;

	int areagrid_stats_calls;
	int areagrid_stats_nodechecks;
	int areagrid_stats_entitychecks;

	link_t areagrid[AREA_GRIDNODES];
	link_t areagrid_outside;
	vec3_t areagrid_bias;
	vec3_t areagrid_scale;
	vec3_t areagrid_mins;
	vec3_t areagrid_maxs;
	vec3_t areagrid_size;
	int areagrid_marknumber;

	                                                           
	world_physics_t physics;
}
world_t;

struct prvm_edict_s;

                                      
void World_ClearLink(link_t *l);
void World_RemoveLink(link_t *l);
void World_InsertLinkBefore(link_t *l, link_t *before, int entitynumber);

void World_Init(void);
void World_Shutdown(void);

                                                                             
void World_SetSize(world_t *world, const char *filename, const vec3_t mins, const vec3_t maxs, struct prvm_prog_s *prog);
                                                             
void World_UnlinkAll(world_t *world);

void World_PrintAreaStats(world_t *world, const char *worldname);

                                                                  
                                     
void World_UnlinkEdict(struct prvm_edict_s *ent);

                                                                    
void World_LinkEdict(world_t *world, struct prvm_edict_s *ent, const vec3_t mins, const vec3_t maxs);

                                            
int World_EntitiesInBox(world_t *world, const vec3_t mins, const vec3_t maxs, int maxlist, struct prvm_edict_s **list);

void World_Start(world_t *world);
void World_End(world_t *world);

                 
                               
void World_Physics_Frame(world_t *world, double frametime, double gravity);

                                      
struct prvm_edict_s;
struct edict_odefunc_s;
void World_Physics_ApplyCmd(struct prvm_edict_s *ed, struct edict_odefunc_s *f);

                                  
                                   
void World_Physics_RemoveFromEntity(world_t *world, struct prvm_edict_s *ed);
void World_Physics_RemoveJointFromEntity(world_t *world, struct prvm_edict_s *ed);

#endif

