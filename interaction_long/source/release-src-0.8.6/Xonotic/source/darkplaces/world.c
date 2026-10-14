  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
                                   

#include "quakedef.h"
#include "clvm_cmds.h"
#include "cl_collision.h"

  

                                                      

                                                                        

  

static void World_Physics_Init(void);
void World_Init(void)
{
	Collision_Init();
	World_Physics_Init();
}

static void World_Physics_Shutdown(void);
void World_Shutdown(void)
{
	World_Physics_Shutdown();
}

static void World_Physics_Start(world_t *world);
void World_Start(world_t *world)
{
	World_Physics_Start(world);
}

static void World_Physics_End(world_t *world);
void World_End(world_t *world)
{
	World_Physics_End(world);
}

                                                                              

                                             
void World_ClearLink (link_t *l)
{
	l->entitynumber = 0;
	l->prev = l->next = l;
}

void World_RemoveLink (link_t *l)
{
	l->next->prev = l->prev;
	l->prev->next = l->next;
}

void World_InsertLinkBefore (link_t *l, link_t *before, int entitynumber)
{
	l->entitynumber = entitynumber;
	l->next = before;
	l->prev = before->prev;
	l->prev->next = l;
	l->next->prev = l;
}

  
                                                                               

                    

                                                                               
  

void World_PrintAreaStats(world_t *world, const char *worldname)
{
	Con_Printf("%s areagrid check stats: %d calls %d nodes (%f per call) %d entities (%f per call)\n", worldname, world->areagrid_stats_calls, world->areagrid_stats_nodechecks, (double) world->areagrid_stats_nodechecks / (double) world->areagrid_stats_calls, world->areagrid_stats_entitychecks, (double) world->areagrid_stats_entitychecks / (double) world->areagrid_stats_calls);
	world->areagrid_stats_calls = 0;
	world->areagrid_stats_nodechecks = 0;
	world->areagrid_stats_entitychecks = 0;
}

  
               
             

               
  
void World_SetSize(world_t *world, const char *filename, const vec3_t mins, const vec3_t maxs, prvm_prog_t *prog)
{
	int i;

	strlcpy(world->filename, filename, sizeof(world->filename));
	VectorCopy(mins, world->mins);
	VectorCopy(maxs, world->maxs);
	world->prog = prog;

	                                                 
	if (world->areagrid_marknumber < 1)
		world->areagrid_marknumber = 1;
	                                                                                      
	world->areagrid_size[0] = max(world->maxs[0] - world->mins[0], AREA_GRID * sv_areagrid_mingridsize.value);
	world->areagrid_size[1] = max(world->maxs[1] - world->mins[1], AREA_GRID * sv_areagrid_mingridsize.value);
	world->areagrid_size[2] = max(world->maxs[2] - world->mins[2], AREA_GRID * sv_areagrid_mingridsize.value);
	                                                                                
	world->areagrid_mins[0] = (world->mins[0] + world->maxs[0] - world->areagrid_size[0]) * 0.5f;
	world->areagrid_mins[1] = (world->mins[1] + world->maxs[1] - world->areagrid_size[1]) * 0.5f;
	world->areagrid_mins[2] = (world->mins[2] + world->maxs[2] - world->areagrid_size[2]) * 0.5f;
	world->areagrid_maxs[0] = (world->mins[0] + world->maxs[0] + world->areagrid_size[0]) * 0.5f;
	world->areagrid_maxs[1] = (world->mins[1] + world->maxs[1] + world->areagrid_size[1]) * 0.5f;
	world->areagrid_maxs[2] = (world->mins[2] + world->maxs[2] + world->areagrid_size[2]) * 0.5f;
	                                                 
	VectorNegate(world->areagrid_mins, world->areagrid_bias);
	world->areagrid_scale[0] = AREA_GRID / world->areagrid_size[0];
	world->areagrid_scale[1] = AREA_GRID / world->areagrid_size[1];
	world->areagrid_scale[2] = AREA_GRID / world->areagrid_size[2];
	World_ClearLink(&world->areagrid_outside);
	for (i = 0;i < AREA_GRIDNODES;i++)
		World_ClearLink(&world->areagrid[i]);
	if (developer_extra.integer)
		Con_DPrintf("areagrid settings: divisions %ix%ix1 : box %f %f %f : %f %f %f size %f %f %f grid %f %f %f (mingrid %f)\n", AREA_GRID, AREA_GRID, world->areagrid_mins[0], world->areagrid_mins[1], world->areagrid_mins[2], world->areagrid_maxs[0], world->areagrid_maxs[1], world->areagrid_maxs[2], world->areagrid_size[0], world->areagrid_size[1], world->areagrid_size[2], 1.0f / world->areagrid_scale[0], 1.0f / world->areagrid_scale[1], 1.0f / world->areagrid_scale[2], sv_areagrid_mingridsize.value);
}

  
               
               

               
  
void World_UnlinkAll(world_t *world)
{
	prvm_prog_t *prog = world->prog;
	int i;
	link_t *grid;
	                                 
	grid = &world->areagrid_outside;
	while (grid->next != grid)
		World_UnlinkEdict(PRVM_EDICT_NUM(grid->next->entitynumber));
	for (i = 0, grid = world->areagrid;i < AREA_GRIDNODES;i++, grid++)
		while (grid->next != grid)
			World_UnlinkEdict(PRVM_EDICT_NUM(grid->next->entitynumber));
}

  
               

               
  
void World_UnlinkEdict(prvm_edict_t *ent)
{
	int i;
	for (i = 0;i < ENTITYGRIDAREAS;i++)
	{
		if (ent->priv.server->areagrid[i].prev)
		{
			World_RemoveLink (&ent->priv.server->areagrid[i]);
			ent->priv.server->areagrid[i].prev = ent->priv.server->areagrid[i].next = NULL;
		}
	}
}

int World_EntitiesInBox(world_t *world, const vec3_t requestmins, const vec3_t requestmaxs, int maxlist, prvm_edict_t **list)
{
	prvm_prog_t *prog = world->prog;
	int numlist;
	link_t *grid;
	link_t *l;
	prvm_edict_t *ent;
	vec3_t paddedmins, paddedmaxs;
	int igrid[3], igridmins[3], igridmaxs[3];

	                                                                                                                         
	                                                                                             
	                                                                                             
	VectorCopy(requestmins, paddedmins);
	VectorCopy(requestmaxs, paddedmaxs);

	                                                               
	                                             
	world->areagrid_stats_calls++;
	world->areagrid_marknumber++;
	igridmins[0] = (int) floor((paddedmins[0] + world->areagrid_bias[0]) * world->areagrid_scale[0]);
	igridmins[1] = (int) floor((paddedmins[1] + world->areagrid_bias[1]) * world->areagrid_scale[1]);
	                                                                                              
	igridmaxs[0] = (int) floor((paddedmaxs[0] + world->areagrid_bias[0]) * world->areagrid_scale[0]) + 1;
	igridmaxs[1] = (int) floor((paddedmaxs[1] + world->areagrid_bias[1]) * world->areagrid_scale[1]) + 1;
	                                                                                                  
	igridmins[0] = max(0, igridmins[0]);
	igridmins[1] = max(0, igridmins[1]);
	                                      
	igridmaxs[0] = min(AREA_GRID, igridmaxs[0]);
	igridmaxs[1] = min(AREA_GRID, igridmaxs[1]);
	                                              

	                     
	                                                                                      

	numlist = 0;
	                                                                    
	                          
	if (world->areagrid_outside.next)
	{
		grid = &world->areagrid_outside;
		for (l = grid->next;l != grid;l = l->next)
		{
			ent = PRVM_EDICT_NUM(l->entitynumber);
			if (ent->priv.server->areagridmarknumber != world->areagrid_marknumber)
			{
				ent->priv.server->areagridmarknumber = world->areagrid_marknumber;
				if (!ent->priv.server->free && BoxesOverlap(paddedmins, paddedmaxs, ent->priv.server->areamins, ent->priv.server->areamaxs))
				{
					if (numlist < maxlist)
						list[numlist] = ent;
					numlist++;
				}
				world->areagrid_stats_entitychecks++;
			}
		}
	}
	                           
	for (igrid[1] = igridmins[1];igrid[1] < igridmaxs[1];igrid[1]++)
	{
		grid = world->areagrid + igrid[1] * AREA_GRID + igridmins[0];
		for (igrid[0] = igridmins[0];igrid[0] < igridmaxs[0];igrid[0]++, grid++)
		{
			if (grid->next)
			{
				for (l = grid->next;l != grid;l = l->next)
				{
					ent = PRVM_EDICT_NUM(l->entitynumber);
					if (ent->priv.server->areagridmarknumber != world->areagrid_marknumber)
					{
						ent->priv.server->areagridmarknumber = world->areagrid_marknumber;
						if (!ent->priv.server->free && BoxesOverlap(paddedmins, paddedmaxs, ent->priv.server->areamins, ent->priv.server->areamaxs))
						{
							if (numlist < maxlist)
								list[numlist] = ent;
							numlist++;
						}
						                                                                                                                                                                                                                                                                                                                                                                                                                           
					}
					world->areagrid_stats_entitychecks++;
				}
			}
		}
	}
	return numlist;
}

static void World_LinkEdict_AreaGrid(world_t *world, prvm_edict_t *ent)
{
	prvm_prog_t *prog = world->prog;
	link_t *grid;
	int igrid[3], igridmins[3], igridmaxs[3], gridnum, entitynumber = PRVM_NUM_FOR_EDICT(ent);

	if (entitynumber <= 0 || entitynumber >= prog->max_edicts || PRVM_EDICT_NUM(entitynumber) != ent)
	{
		Con_Printf ("World_LinkEdict_AreaGrid: invalid edict %p (edicts is %p, edict compared to prog->edicts is %i)\n", (void *)ent, (void *)prog->edicts, entitynumber);
		return;
	}

	igridmins[0] = (int) floor((ent->priv.server->areamins[0] + world->areagrid_bias[0]) * world->areagrid_scale[0]);
	igridmins[1] = (int) floor((ent->priv.server->areamins[1] + world->areagrid_bias[1]) * world->areagrid_scale[1]);
	                                                                                                                   
	igridmaxs[0] = (int) floor((ent->priv.server->areamaxs[0] + world->areagrid_bias[0]) * world->areagrid_scale[0]) + 1;
	igridmaxs[1] = (int) floor((ent->priv.server->areamaxs[1] + world->areagrid_bias[1]) * world->areagrid_scale[1]) + 1;
	                                                                                                                       
	if (igridmins[0] < 0 || igridmaxs[0] > AREA_GRID || igridmins[1] < 0 || igridmaxs[1] > AREA_GRID || ((igridmaxs[0] - igridmins[0]) * (igridmaxs[1] - igridmins[1])) > ENTITYGRIDAREAS)
	{
		                                                    
		World_InsertLinkBefore (&ent->priv.server->areagrid[0], &world->areagrid_outside, entitynumber);
		return;
	}

	gridnum = 0;
	for (igrid[1] = igridmins[1];igrid[1] < igridmaxs[1];igrid[1]++)
	{
		grid = world->areagrid + igrid[1] * AREA_GRID + igridmins[0];
		for (igrid[0] = igridmins[0];igrid[0] < igridmaxs[0];igrid[0]++, grid++, gridnum++)
			World_InsertLinkBefore (&ent->priv.server->areagrid[gridnum], grid, entitynumber);
	}
}

  
               
               

               
  
void World_LinkEdict(world_t *world, prvm_edict_t *ent, const vec3_t mins, const vec3_t maxs)
{
	prvm_prog_t *prog = world->prog;
	                                 
	if (ent->priv.server->areagrid[0].prev)
		World_UnlinkEdict(ent);

	                      
	if (ent == prog->edicts)
		return;

	                          
	if (ent->priv.server->free)
		return;

	VectorCopy(mins, ent->priv.server->areamins);
	VectorCopy(maxs, ent->priv.server->areamaxs);
	World_LinkEdict_AreaGrid(world, ent);
}




                                                                              
                         
                                                                              

#ifdef USEODE
cvar_t physics_ode_quadtree_depth = {0, "physics_ode_quadtree_depth","5", "desired subdivision level of quadtree culling space"};
cvar_t physics_ode_allowconvex = {0, "physics_ode_allowconvex", "0", "allow usage of Convex Hull primitive type on trimeshes that have custom 'collisionconvex' mesh. If disabled, trimesh primitive type are used."};
cvar_t physics_ode_contactsurfacelayer = {0, "physics_ode_contactsurfacelayer","1", "allows objects to overlap this many units to reduce jitter"};
cvar_t physics_ode_worldstep_iterations = {0, "physics_ode_worldstep_iterations", "20", "parameter to dWorldQuickStep"};
cvar_t physics_ode_contact_mu = {0, "physics_ode_contact_mu", "1", "contact solver mu parameter - friction pyramid approximation 1 (see ODE User Guide)"};
cvar_t physics_ode_contact_erp = {0, "physics_ode_contact_erp", "0.96", "contact solver erp parameter - Error Restitution Percent (see ODE User Guide)"};
cvar_t physics_ode_contact_cfm = {0, "physics_ode_contact_cfm", "0", "contact solver cfm parameter - Constraint Force Mixing (see ODE User Guide)"};
cvar_t physics_ode_contact_maxpoints = {0, "physics_ode_contact_maxpoints", "16", "maximal number of contact points between 2 objects, higher = stable (and slower), can be up to 32"};
cvar_t physics_ode_world_erp = {0, "physics_ode_world_erp", "-1", "world solver erp parameter - Error Restitution Percent (see ODE User Guide); use defaults when set to -1"};
cvar_t physics_ode_world_cfm = {0, "physics_ode_world_cfm", "-1", "world solver cfm parameter - Constraint Force Mixing (see ODE User Guide); not touched when -1"};
cvar_t physics_ode_world_damping = {0, "physics_ode_world_damping", "1", "enabled damping scale (see ODE User Guide), this scales all damping values, be aware that behavior depends of step type"};
cvar_t physics_ode_world_damping_linear = {0, "physics_ode_world_damping_linear", "0.01", "world linear damping scale (see ODE User Guide); use defaults when set to -1"};
cvar_t physics_ode_world_damping_linear_threshold = {0, "physics_ode_world_damping_linear_threshold", "0.1", "world linear damping threshold (see ODE User Guide); use defaults when set to -1"};
cvar_t physics_ode_world_damping_angular = {0, "physics_ode_world_damping_angular", "0.05", "world angular damping scale (see ODE User Guide); use defaults when set to -1"};
cvar_t physics_ode_world_damping_angular_threshold = {0, "physics_ode_world_damping_angular_threshold", "0.1", "world angular damping threshold (see ODE User Guide); use defaults when set to -1"};
cvar_t physics_ode_world_gravitymod = {0, "physics_ode_world_gravitymod", "1", "multiplies gravity got from sv_gravity, this may be needed to tweak if strong damping is used"};
cvar_t physics_ode_iterationsperframe = {0, "physics_ode_iterationsperframe", "1", "divisor for time step, runs multiple physics steps per frame"};
cvar_t physics_ode_constantstep = {0, "physics_ode_constantstep", "0", "use constant step instead of variable step which tends to increase stability, if set to 1 uses sys_ticrate, instead uses it's own value"};
cvar_t physics_ode_autodisable = {0, "physics_ode_autodisable", "1", "automatic disabling of objects which dont move for long period of time, makes object stacking a lot faster"};
cvar_t physics_ode_autodisable_steps = {0, "physics_ode_autodisable_steps", "10", "how many steps object should be dormant to be autodisabled"};
cvar_t physics_ode_autodisable_time = {0, "physics_ode_autodisable_time", "0", "how many seconds object should be dormant to be autodisabled"};
cvar_t physics_ode_autodisable_threshold_linear = {0, "physics_ode_autodisable_threshold_linear", "0.6", "body will be disabled if it's linear move below this value"};
cvar_t physics_ode_autodisable_threshold_angular = {0, "physics_ode_autodisable_threshold_angular", "6", "body will be disabled if it's angular move below this value"};
cvar_t physics_ode_autodisable_threshold_samples = {0, "physics_ode_autodisable_threshold_samples", "5", "average threshold with this number of samples"};
cvar_t physics_ode_movelimit = {0, "physics_ode_movelimit", "0.5", "clamp velocity if a single move would exceed this percentage of object thickness, to prevent flying through walls, be aware that behavior depends of step type"};
cvar_t physics_ode_spinlimit = {0, "physics_ode_spinlimit", "10000", "reset spin velocity if it gets too large"};
cvar_t physics_ode_trick_fixnan = {0, "physics_ode_trick_fixnan", "1", "engine trick that checks and fixes NaN velocity/origin/angles on objects, a value of 2 makes console prints on each fix"};
cvar_t physics_ode_printstats = {0, "physics_ode_printstats", "0", "print ODE stats each frame"};

cvar_t physics_ode = {0, "physics_ode", "0", "run ODE physics (VERY experimental and potentially buggy)"};

                                                                        
                 

#ifdef LINK_TO_LIBODE
#include "ode/ode.h"
#else
#ifdef WINAPI
                          
#define ODE_API
#else
#define ODE_API
#endif

                                                                            
                    
typedef double dReal;

typedef dReal dVector3[4];
typedef dReal dVector4[4];
typedef dReal dMatrix3[4*3];
typedef dReal dMatrix4[4*4];
typedef dReal dMatrix6[8*6];
typedef dReal dQuaternion[4];

struct dxWorld;		                    
struct dxSpace;		                     
struct dxBody;		                                  
struct dxGeom;		                                 
struct dxJoint;
struct dxJointNode;
struct dxJointGroup;
struct dxTriMeshData;

#define dInfinity 3.402823466e+38f

typedef struct dxWorld *dWorldID;
typedef struct dxSpace *dSpaceID;
typedef struct dxBody *dBodyID;
typedef struct dxGeom *dGeomID;
typedef struct dxJoint *dJointID;
typedef struct dxJointGroup *dJointGroupID;
typedef struct dxTriMeshData *dTriMeshDataID;

typedef struct dJointFeedback
{
	dVector3 f1;		                             
	dVector3 t1;		                              
	dVector3 f2;		                             
	dVector3 t2;		                              
}
dJointFeedback;

typedef enum dJointType
{
	dJointTypeNone = 0,
	dJointTypeBall,
	dJointTypeHinge,
	dJointTypeSlider,
	dJointTypeContact,
	dJointTypeUniversal,
	dJointTypeHinge2,
	dJointTypeFixed,
	dJointTypeNull,
	dJointTypeAMotor,
	dJointTypeLMotor,
	dJointTypePlane2D,
	dJointTypePR,
	dJointTypePU,
	dJointTypePiston
}
dJointType;

#define D_ALL_PARAM_NAMES(start) \
                                         \
  dParamLoStop = start, \
  dParamHiStop, \
  dParamVel, \
  dParamFMax, \
  dParamFudgeFactor, \
  dParamBounce, \
  dParamCFM, \
  dParamStopERP, \
  dParamStopCFM, \
                                  \
  dParamSuspensionERP, \
  dParamSuspensionCFM, \
  dParamERP, \

#define D_ALL_PARAM_NAMES_X(start,x) \
                                         \
  dParamLoStop ## x = start, \
  dParamHiStop ## x, \
  dParamVel ## x, \
  dParamFMax ## x, \
  dParamFudgeFactor ## x, \
  dParamBounce ## x, \
  dParamCFM ## x, \
  dParamStopERP ## x, \
  dParamStopCFM ## x, \
                                  \
  dParamSuspensionERP ## x, \
  dParamSuspensionCFM ## x, \
  dParamERP ## x,

enum {
  D_ALL_PARAM_NAMES(0)
  D_ALL_PARAM_NAMES_X(0x100,2)
  D_ALL_PARAM_NAMES_X(0x200,3)

                                                                          
                                                   
     
  dParamGroup=0x100
};

typedef struct dMass
{
	dReal mass;
	dVector3 c;
	dMatrix3 I;
}
dMass;

enum
{
	dContactMu2			= 0x001,
	dContactFDir1		= 0x002,
	dContactBounce		= 0x004,
	dContactSoftERP		= 0x008,
	dContactSoftCFM		= 0x010,
	dContactMotion1		= 0x020,
	dContactMotion2		= 0x040,
	dContactMotionN		= 0x080,
	dContactSlip1		= 0x100,
	dContactSlip2		= 0x200,
	
	dContactApprox0		= 0x0000,
	dContactApprox1_1	= 0x1000,
	dContactApprox1_2	= 0x2000,
	dContactApprox1		= 0x3000
};

typedef struct dSurfaceParameters
{
	                            
	int mode;
	dReal mu;

	                                                           
	dReal mu2;
	dReal bounce;
	dReal bounce_vel;
	dReal soft_erp;
	dReal soft_cfm;
	dReal motion1,motion2,motionN;
	dReal slip1,slip2;
} dSurfaceParameters;

typedef struct dContactGeom
{
	dVector3 pos;                               
	dVector3 normal;                         
	dReal depth;                                 
	dGeomID g1,g2;                                 
	int side1,side2;                              
}
dContactGeom;

typedef struct dContact
{
	dSurfaceParameters surface;
	dContactGeom geom;
	dVector3 fdir1;
}
dContact;

typedef void dNearCallback (void *data, dGeomID o1, dGeomID o2);

      
                                                        
#define dSAP_AXES_XYZ  ((0)|(1<<2)|(2<<4))
#define dSAP_AXES_XZY  ((0)|(2<<2)|(1<<4))
#define dSAP_AXES_YXZ  ((1)|(0<<2)|(2<<4))
#define dSAP_AXES_YZX  ((1)|(2<<2)|(0<<4))
#define dSAP_AXES_ZXY  ((2)|(0<<2)|(1<<4))
#define dSAP_AXES_ZYX  ((2)|(1<<2)|(0<<4))

const char*     (ODE_API *dGetConfiguration)(void);
int             (ODE_API *dCheckConfiguration)( const char* token );
int             (ODE_API *dInitODE)(void);
                                                                 
                                                                                     
                                                               
void            (ODE_API *dCloseODE)(void);

                                                        
                                                   
                                                                                                                                                                           
                                                                                  
void            (ODE_API *dMassSetSphereTotal)(dMass *, dReal total_mass, dReal radius);
                                                                                                                
void            (ODE_API *dMassSetCapsuleTotal)(dMass *, dReal total_mass, int direction, dReal radius, dReal length);
                                                                                                                 
void            (ODE_API *dMassSetCylinderTotal)(dMass *, dReal total_mass, int direction, dReal radius, dReal length);
                                                                                               
void            (ODE_API *dMassSetBoxTotal)(dMass *, dReal total_mass, dReal lx, dReal ly, dReal lz);
                                                                                
                                                                                         
                                                                 
                                                                                
                                                                    
                                                                
  
dWorldID        (ODE_API *dWorldCreate)(void);
void            (ODE_API *dWorldDestroy)(dWorldID world);
void            (ODE_API *dWorldSetGravity)(dWorldID, dReal x, dReal y, dReal z);
void            (ODE_API *dWorldGetGravity)(dWorldID, dVector3 gravity);
void            (ODE_API *dWorldSetERP)(dWorldID, dReal erp);
                                                    
void            (ODE_API *dWorldSetCFM)(dWorldID, dReal cfm);
                                                    
                                                                  
                                                                                                                          
void            (ODE_API *dWorldQuickStep)(dWorldID w, dReal stepsize);
void            (ODE_API *dWorldSetQuickStepNumIterations)(dWorldID, int num);
                                                                       
                                                                                  
                                                           
                                                                                   
                                                                        
void            (ODE_API *dWorldSetContactSurfaceLayer)(dWorldID, dReal depth);
                                                                    
                                                                                          
                                                                                        
                                                                   
                                                                           
void            (ODE_API *dWorldSetAutoDisableLinearThreshold)(dWorldID, dReal linear_threshold);
                                                                            
void            (ODE_API *dWorldSetAutoDisableAngularThreshold)(dWorldID, dReal angular_threshold);
                                                                                  
                                                                                                                  
                                                                                   
                                                                                                                    
                                                                               
void            (ODE_API *dWorldSetAutoDisableAverageSamplesCount)(dWorldID, unsigned int average_samples_count );
                                                                 
void            (ODE_API *dWorldSetAutoDisableSteps)(dWorldID, int steps);
                                                                
void            (ODE_API *dWorldSetAutoDisableTime)(dWorldID, dReal time);
                                                                
void            (ODE_API *dWorldSetAutoDisableFlag)(dWorldID, int do_auto_disable);
                                                                         
void            (ODE_API *dWorldSetLinearDampingThreshold)(dWorldID w, dReal threshold);
                                                                          
void            (ODE_API *dWorldSetAngularDampingThreshold)(dWorldID w, dReal threshold);
                                                                
void            (ODE_API *dWorldSetLinearDamping)(dWorldID w, dReal scale);
                                                                 
void            (ODE_API *dWorldSetAngularDamping)(dWorldID w, dReal scale);
                                                                                                   
                                                                  
                                                                                   
                                                                         
                                                                                                         
                                                                          
                                                                                                           
                                                                             
                                                                                                                 
                                                               
                                                                          
                                                              
                                                                          
                                                              
                                                                                   
                                                                  
                                                    
dBodyID         (ODE_API *dBodyCreate)(dWorldID);
void            (ODE_API *dBodyDestroy)(dBodyID);
void            (ODE_API *dBodySetData)(dBodyID, void *data);
void *          (ODE_API *dBodyGetData)(dBodyID);
void            (ODE_API *dBodySetPosition)(dBodyID, dReal x, dReal y, dReal z);
void            (ODE_API *dBodySetRotation)(dBodyID, const dMatrix3 R);
                                                                              
void            (ODE_API *dBodySetLinearVel)(dBodyID, dReal x, dReal y, dReal z);
void            (ODE_API *dBodySetAngularVel)(dBodyID, dReal x, dReal y, dReal z);
const dReal *   (ODE_API *dBodyGetPosition)(dBodyID);
                                                                           
const dReal *   (ODE_API *dBodyGetRotation)(dBodyID);
                                                                    
                                                         
                                                                                 
const dReal *   (ODE_API *dBodyGetLinearVel)(dBodyID);
const dReal *   (ODE_API *dBodyGetAngularVel)(dBodyID);
void            (ODE_API *dBodySetMass)(dBodyID, const dMass *mass);
                                                                
void            (ODE_API *dBodyAddForce)(dBodyID, dReal fx, dReal fy, dReal fz);
void            (ODE_API *dBodyAddTorque)(dBodyID, dReal fx, dReal fy, dReal fz);
                                                                                     
                                                                                      
void            (ODE_API *dBodyAddForceAtPos)(dBodyID, dReal fx, dReal fy, dReal fz, dReal px, dReal py, dReal pz);
                                                                                                                        
                                                                                                                        
                                                                                                                           
                                                    
                                                     
                                                                                 
                                                                                  
                                                                                                         
                                                                                                         
                                                                                                      
                                                                                                         
                                                                                                        
                                                                                                          
                                                                           
                                                                                            
                                                                 
                                                                                  
int             (ODE_API *dBodyGetNumJoints)(dBodyID b);
dJointID        (ODE_API *dBodyGetJoint)(dBodyID, int index);
                                                      
                                                        
                                                       
void            (ODE_API *dBodyEnable)(dBodyID);
void            (ODE_API *dBodyDisable)(dBodyID);
int             (ODE_API *dBodyIsEnabled)(dBodyID);
void            (ODE_API *dBodySetGravityMode)(dBodyID b, int mode);
int             (ODE_API *dBodyGetGravityMode)(dBodyID b);
                                                                                        
                                                          
                                                         
                                                                
                                                              
                                                                           
                                                               
                                                                            
                                                                                                 
                                                                       
                                                                                        
                                                                        
                                                                                         
                                                                
                                                                                 
                                                               
                                                                            
dJointID        (ODE_API *dJointCreateBall)(dWorldID, dJointGroupID);
dJointID        (ODE_API *dJointCreateHinge)(dWorldID, dJointGroupID);
dJointID        (ODE_API *dJointCreateSlider)(dWorldID, dJointGroupID);
dJointID        (ODE_API *dJointCreateContact)(dWorldID, dJointGroupID, const dContact *);
dJointID        (ODE_API *dJointCreateHinge2)(dWorldID, dJointGroupID);
dJointID        (ODE_API *dJointCreateUniversal)(dWorldID, dJointGroupID);
                                                                     
                                                                     
                                                                         
dJointID        (ODE_API *dJointCreateFixed)(dWorldID, dJointGroupID);
                                                                       
                                                                         
                                                                         
                                                                          
void            (ODE_API *dJointDestroy)(dJointID);
dJointGroupID   (ODE_API *dJointGroupCreate)(int max_size);
void            (ODE_API *dJointGroupDestroy)(dJointGroupID);
void            (ODE_API *dJointGroupEmpty)(dJointGroupID);
                                                          
void            (ODE_API *dJointAttach)(dJointID, dBodyID body1, dBodyID body2);
                                                    
                                                     
                                                       
void            (ODE_API *dJointSetData)(dJointID, void *data);
void *          (ODE_API *dJointGetData)(dJointID);
                                                     
dBodyID         (ODE_API *dJointGetBody)(dJointID, int index);
                                                                           
                                                         
void            (ODE_API *dJointSetBallAnchor)(dJointID, dReal x, dReal y, dReal z);
                                                                                       
void            (ODE_API *dJointSetBallParam)(dJointID, int parameter, dReal value);
void            (ODE_API *dJointSetHingeAnchor)(dJointID, dReal x, dReal y, dReal z);
                                                                                                                          
void            (ODE_API *dJointSetHingeAxis)(dJointID, dReal x, dReal y, dReal z);
                                                                                                          
void            (ODE_API *dJointSetHingeParam)(dJointID, int parameter, dReal value);
                                                                                
void            (ODE_API *dJointSetSliderAxis)(dJointID, dReal x, dReal y, dReal z);
                                                                                                                         
void            (ODE_API *dJointSetSliderParam)(dJointID, int parameter, dReal value);
                                                                               
void            (ODE_API *dJointSetHinge2Anchor)(dJointID, dReal x, dReal y, dReal z);
void            (ODE_API *dJointSetHinge2Axis1)(dJointID, dReal x, dReal y, dReal z);
void            (ODE_API *dJointSetHinge2Axis2)(dJointID, dReal x, dReal y, dReal z);
void            (ODE_API *dJointSetHinge2Param)(dJointID, int parameter, dReal value);
                                                                                                  
void            (ODE_API *dJointSetUniversalAnchor)(dJointID, dReal x, dReal y, dReal z);
void            (ODE_API *dJointSetUniversalAxis1)(dJointID, dReal x, dReal y, dReal z);
                                                                                                                              
void            (ODE_API *dJointSetUniversalAxis2)(dJointID, dReal x, dReal y, dReal z);
                                                                                                                              
void            (ODE_API *dJointSetUniversalParam)(dJointID, int parameter, dReal value);
                                                                                                     
                                                                                    
                                                                                   
                                                                                   
                                                                                    
                                                                         
                                                                                    
                                                                                                                        
                                                                                   
                                                                                   
                                                                                   
                                                                                      
                                                                                    
                                                                         
                                                                                        
                                                                                                                              
                                                                                        
                                                                               
                                                      
                                                                                       
                                                                       
                                                                                                         
                                                                                   
                                                                                        
                                                                     
                                                                                                           
                                                                       
                                                                                                         
                                                                                        
                                                                                          
                                                                                          
                                                                                              
                                                                            
                                                                             
                                                                         
                                                                             
                                                                              
                                                                           
                                                                          
                                                           
                                                               
                                                               
                                                                   
                                                                            
                                                                           
                                                                              
                                                                               
                                                                             
                                                                             
                                                                           
                                                             
                                                                 
                                                                 
                                                                                 
                                                                                  
                                                                                
                                                                                
                                                                              
                                                                                              
                                                                
                                                                
                                                                    
                                                                    
                                                                          
                                                           
                                                               
                                                        
                                                            
                                                                         
                                                                         
                                                                       
                                                                          
                                                           
                                                               
                                                                         
                                                                         
                                                                         
                                                                            
                                                                                       
                                                         
                                                             
                                                         
                                                             
                                                                       
                                                               
                                                                   
                                                            
                                                                
                                                                              
                                                                               
                                                                            
                                                                           
                                                              
                                                                                      
                                                                        
                                                                      
                                                                          
                                                                           
                                                           
                                                              
                                                                                      
                                                                           
                                                                          
                                                                
                                                                               
int             (ODE_API *dAreConnected)(dBodyID, dBodyID);
int             (ODE_API *dAreConnectedExcluding)(dBodyID body1, dBodyID body2, int joint_type);
  
dSpaceID        (ODE_API *dSimpleSpaceCreate)(dSpaceID space);
dSpaceID        (ODE_API *dHashSpaceCreate)(dSpaceID space);
dSpaceID        (ODE_API *dQuadTreeSpaceCreate)(dSpaceID space, const dVector3 Center, const dVector3 Extents, int Depth);
                                                                                        
void            (ODE_API *dSpaceDestroy)(dSpaceID);
                                                                                             
                                                                                               
                                                                        
                                                              
                                                                             
                                                               
                                                                              
                                                                    
                                                          
                                                             
                                                            
                                                   
                                                         
                                                            
                                                            
  
void            (ODE_API *dGeomDestroy)(dGeomID geom);
void            (ODE_API *dGeomSetData)(dGeomID geom, void* data);
void *          (ODE_API *dGeomGetData)(dGeomID geom);
void            (ODE_API *dGeomSetBody)(dGeomID geom, dBodyID body);
dBodyID         (ODE_API *dGeomGetBody)(dGeomID geom);
void            (ODE_API *dGeomSetPosition)(dGeomID geom, dReal x, dReal y, dReal z);
void            (ODE_API *dGeomSetRotation)(dGeomID geom, const dMatrix3 R);
                                                                                   
                                                            
                                                                           
                                                            
                                                                         
                                                                                  
                                                                       
int             (ODE_API *dGeomIsSpace)(dGeomID geom);
                                                    
                                                         
                                                                                    
                                                                                   
                                                           
                                                          
                                                       
                                                        
                                                          
                                                                                             
                                                                                    
                                                                                         
                                                                                                  
                                                                                         
                                                                                            
                                                            
                                                         
                                                                  
                                                                                 
                                                                  
                                                                               
                                                                                        
int             (ODE_API *dCollide)(dGeomID o1, dGeomID o2, int flags, dContactGeom *contact, int skip);
  
void            (ODE_API *dSpaceCollide)(dSpaceID space, void *data, dNearCallback *callback);
void            (ODE_API *dSpaceCollide2)(dGeomID space1, dGeomID space2, void *data, dNearCallback *callback);
  
dGeomID         (ODE_API *dCreateSphere)(dSpaceID space, dReal radius);
                                                                                
                                                                  
                                                                                              
  
dGeomID         (ODE_API *dCreateConvex)(dSpaceID space, dReal *_planes, unsigned int _planecount, dReal *_points, unsigned int _pointcount,unsigned int *_polygons);
                                                                                                                                                              
  
dGeomID         (ODE_API *dCreateBox)(dSpaceID space, dReal lx, dReal ly, dReal lz);
                                                                                           
                                                                              
                                                                                        
                                                                                        
  
                                                                                              
                                                                                                    
                                                                                 
                                                                                            
  
dGeomID         (ODE_API *dCreateCapsule)(dSpaceID space, dReal radius, dReal length);
                                                                                                  
                                                                                                    
                                                                                                  
  
dGeomID         (ODE_API *dCreateCylinder)(dSpaceID space, dReal radius, dReal length);
                                                                                                  
                                                                                                    
  
                                                                      
                                                                          
                                                            
                                                                                                                  
                                                                                    
  
dGeomID         (ODE_API *dCreateGeomTransform)(dSpaceID space);
void            (ODE_API *dGeomTransformSetGeom)(dGeomID g, dGeomID obj);
                                                              
void            (ODE_API *dGeomTransformSetCleanup)(dGeomID g, int mode);
                                                                 
                                                                        
                                                              

enum { TRIMESH_FACE_NORMALS };
typedef int dTriCallback(dGeomID TriMesh, dGeomID RefObject, int TriangleIndex);
typedef void dTriArrayCallback(dGeomID TriMesh, dGeomID RefObject, const int* TriIndices, int TriCount);
typedef int dTriRayCallback(dGeomID TriMesh, dGeomID Ray, int TriangleIndex, dReal u, dReal v);
typedef int dTriTriMergeCallback(dGeomID TriMesh, int FirstTriangleIndex, int SecondTriangleIndex);

dTriMeshDataID  (ODE_API *dGeomTriMeshDataCreate)(void);
void            (ODE_API *dGeomTriMeshDataDestroy)(dTriMeshDataID g);
                                                                                               
                                                                                
                                                                                              
                                                                         
void            (ODE_API *dGeomTriMeshDataBuildSingle)(dTriMeshDataID g, const void* Vertices, int VertexStride, int VertexCount,  const void* Indices, int IndexCount, int TriStride);
                                                                                                                                                                                                               
                                                                                                                                                                                           
                                                                                                                                                                                                                 
                                                                                                                                                             
                                                                                                                                                                                  
                                                                          
                                                                                                           
                                                                                             
                                                                                        
                                                                
                                                                                                       
                                                                        
                                                                                              
                                                                    
                                                                                                        
                                                                              
dGeomID         (ODE_API *dCreateTriMesh)(dSpaceID space, dTriMeshDataID Data, dTriCallback* Callback, dTriArrayCallback* ArrayCallback, dTriRayCallback* RayCallback);
                                                                                 
                                                            
                                                                                        
                                                                               
                                                                 
                                                                     
                                                                                                                     
                                                                                                        
                                                                      
                                                                      

static dllfunction_t odefuncs[] =
{
	{"dGetConfiguration",							(void **) &dGetConfiguration},
	{"dCheckConfiguration",							(void **) &dCheckConfiguration},
	{"dInitODE",									(void **) &dInitODE},
                                               
                                                                           
                                                                               
	{"dCloseODE",									(void **) &dCloseODE},
                                                 
                                                    
                                                               
                                                        
	{"dMassSetSphereTotal",							(void **) &dMassSetSphereTotal},
                                                          
	{"dMassSetCapsuleTotal",						(void **) &dMassSetCapsuleTotal},
                                                           
	{"dMassSetCylinderTotal",						(void **) &dMassSetCylinderTotal},
                                                   
	{"dMassSetBoxTotal",							(void **) &dMassSetBoxTotal},
                                                          
                                                                  
                                                   
                                                        
                                                   
                                             

	{"dWorldCreate",								(void **) &dWorldCreate},
	{"dWorldDestroy",								(void **) &dWorldDestroy},
	{"dWorldSetGravity",							(void **) &dWorldSetGravity},
	{"dWorldGetGravity",							(void **) &dWorldGetGravity},
	{"dWorldSetERP",								(void **) &dWorldSetERP},
                                                    
	{"dWorldSetCFM",								(void **) &dWorldSetCFM},
                                                    
                                                 
                                                                  
	{"dWorldQuickStep",								(void **) &dWorldQuickStep},
	{"dWorldSetQuickStepNumIterations",				(void **) &dWorldSetQuickStepNumIterations},
                                                                                      
                                                                 
                                                                 
                                                                                       
                                                                                       
	{"dWorldSetContactSurfaceLayer",				(void **) &dWorldSetContactSurfaceLayer},
                                                                                
                                                          
                                                                               
                                                                               
                                                                                             
	{"dWorldSetAutoDisableLinearThreshold",			(void **) &dWorldSetAutoDisableLinearThreshold},
                                                                                              
	{"dWorldSetAutoDisableAngularThreshold",		(void **) &dWorldSetAutoDisableAngularThreshold},
                                                                                                         
                                                                                                         
                                                                                                           
                                                                                                           
                                                                                                    
	{"dWorldSetAutoDisableAverageSamplesCount",		(void **) &dWorldSetAutoDisableAverageSamplesCount},
                                                                           
	{"dWorldSetAutoDisableSteps",					(void **) &dWorldSetAutoDisableSteps},
                                                                         
	{"dWorldSetAutoDisableTime",					(void **) &dWorldSetAutoDisableTime},
                                                                         
	{"dWorldSetAutoDisableFlag",					(void **) &dWorldSetAutoDisableFlag},
                                                                                      
	{"dWorldSetLinearDampingThreshold",				(void **) &dWorldSetLinearDampingThreshold},
                                                                                       
	{"dWorldSetAngularDampingThreshold",			(void **) &dWorldSetAngularDampingThreshold},
                                                                      
	{"dWorldSetLinearDamping",						(void **) &dWorldSetLinearDamping},
                                                                        
	{"dWorldSetAngularDamping",						(void **) &dWorldSetAngularDamping},
                                                           
                                                                         
                                                                         
                                                                                           
                                                                                           
                                                                                             
                                                                                             
                                                                                                  
                                                                                                  
                                                                         
                                                                         
                                                                        
                                                                        
                                                                        
                                                                        
                                                                               
                                                      
	{"dBodyCreate",									(void **) &dBodyCreate},
	{"dBodyDestroy",								(void **) &dBodyDestroy},
	{"dBodySetData",								(void **) &dBodySetData},
	{"dBodyGetData",								(void **) &dBodyGetData},
	{"dBodySetPosition",							(void **) &dBodySetPosition},
	{"dBodySetRotation",							(void **) &dBodySetRotation},
                                                               
	{"dBodySetLinearVel",							(void **) &dBodySetLinearVel},
	{"dBodySetAngularVel",							(void **) &dBodySetAngularVel},
	{"dBodyGetPosition",							(void **) &dBodyGetPosition},
                                                             
	{"dBodyGetRotation",							(void **) &dBodyGetRotation},
                                                             
                                                               
                                                                 
	{"dBodyGetLinearVel",							(void **) &dBodyGetLinearVel},
	{"dBodyGetAngularVel",							(void **) &dBodyGetAngularVel},
	{"dBodySetMass",								(void **) &dBodySetMass},
                                                    
	{"dBodyAddForce",								(void **) &dBodyAddForce},
	{"dBodyAddTorque",								(void **) &dBodyAddTorque},
                                                           
                                                             
	{"dBodyAddForceAtPos",							(void **) &dBodyAddForceAtPos},
                                                                    
                                                                    
                                                                         
                                                      
                                                        
                                                      
                                                        
                                                                 
                                                                 
                                                           
                                                                 
                                                               
                                                                  
                                                                             
                                                                             
                                                                             
                                                                             
	{"dBodyGetNumJoints",							(void **) &dBodyGetNumJoints},
	{"dBodyGetJoint",								(void **) &dBodyGetJoint},
                                                          
                                                             
                                                           
	{"dBodyEnable",									(void **) &dBodyEnable},
	{"dBodyDisable",								(void **) &dBodyDisable},
	{"dBodyIsEnabled",								(void **) &dBodyIsEnabled},
	{"dBodySetGravityMode",							(void **) &dBodySetGravityMode},
	{"dBodyGetGravityMode",							(void **) &dBodyGetGravityMode},
                                                                    
                                                             
                                                           
                                                                        
                                                                    
                                                                    
                                                                      
                                                                      
                                                          
                                                                                    
                                                                                    
                                                                                      
                                                                                      
                                                                        
                                                                        
                                                                      
                                                                      
	{"dJointCreateBall",							(void **) &dJointCreateBall},
	{"dJointCreateHinge",							(void **) &dJointCreateHinge},
	{"dJointCreateSlider",							(void **) &dJointCreateSlider},
	{"dJointCreateContact",							(void **) &dJointCreateContact},
	{"dJointCreateHinge2",							(void **) &dJointCreateHinge2},
	{"dJointCreateUniversal",						(void **) &dJointCreateUniversal},
                                                        
                                                        
                                                               
	{"dJointCreateFixed",							(void **) &dJointCreateFixed},
                                                           
                                                               
                                                               
                                                                 
	{"dJointDestroy",								(void **) &dJointDestroy},
	{"dJointGroupCreate",							(void **) &dJointGroupCreate},
	{"dJointGroupDestroy",							(void **) &dJointGroupDestroy},
	{"dJointGroupEmpty",							(void **) &dJointGroupEmpty},
                                                               
	{"dJointAttach",								(void **) &dJointAttach},
                                                    
                                                      
                                                          
	{"dJointSetData",								(void **) &dJointSetData},
	{"dJointGetData",								(void **) &dJointGetData},
                                                      
	{"dJointGetBody",								(void **) &dJointGetBody},
                                                             
                                                             
	{"dJointSetBallAnchor",							(void **) &dJointSetBallAnchor},
                                                                  
	{"dJointSetBallParam",							(void **) &dJointSetBallParam},
	{"dJointSetHingeAnchor",						(void **) &dJointSetHingeAnchor},
                                                                           
	{"dJointSetHingeAxis",							(void **) &dJointSetHingeAxis},
                                                                         
	{"dJointSetHingeParam",							(void **) &dJointSetHingeParam},
                                                                  
	{"dJointSetSliderAxis",							(void **) &dJointSetSliderAxis},
                                                                         
	{"dJointSetSliderParam",						(void **) &dJointSetSliderParam},
                                                                  
	{"dJointSetHinge2Anchor",						(void **) &dJointSetHinge2Anchor},
	{"dJointSetHinge2Axis1",						(void **) &dJointSetHinge2Axis1},
	{"dJointSetHinge2Axis2",						(void **) &dJointSetHinge2Axis2},
	{"dJointSetHinge2Param",						(void **) &dJointSetHinge2Param},
                                                                      
	{"dJointSetUniversalAnchor",					(void **) &dJointSetUniversalAnchor},
	{"dJointSetUniversalAxis1",						(void **) &dJointSetUniversalAxis1},
                                                                                  
	{"dJointSetUniversalAxis2",						(void **) &dJointSetUniversalAxis2},
                                                                                  
	{"dJointSetUniversalParam",						(void **) &dJointSetUniversalParam},
                                                                           
                                                             
                                                           
                                                           
                                                           
                                                             
                                                             
                                                                        
                                                           
                                                           
                                                           
                                                           
                                                           
                                                             
                                                                    
                                                                               
                                                                  
                                                                  
                                                        
                                                                 
                                                                      
                                                                 
                                                                  
                                                                  
                                                                 
                                                                      
                                                                      
                                                                 
                                                                  
                                                                      
                                                                      
                                                                             
                                                                 
                                                                  
                                                               
                                                                  
                                                                    
                                                               
                                                                 
                                                                 
                                                                        
                                                                        
                                                                               
                                                                 
                                                                  
                                                                    
                                                                      
                                                                  
                                                                  
                                                                  
                                                                    
                                                                           
                                                                           
                                                                         
                                                                           
                                                                        
                                                                        
                                                                        
                                                                         
                                                                         
                                                                         
                                                                                
                                                                                
                                                             
                                                                 
                                                                        
                                                           
                                                                  
                                                           
                                                           
                                                           
                                                             
                                                                 
                                                                        
                                                           
                                                           
                                                           
                                                           
                                                             
                                                             
                                                                    
                                                             
                                                                    
                                                           
                                                                        
                                                                               
                                                                  
                                                                         
                                                                    
                                                                      
                                                                 
                                                                  
                                                                      
                                                                 
                                                                      
                                                                  
                                                                         
                                                                  
                                                                 
                                                                      
                                                                 
                                                                  
                                                                 
                                                           
                                                                  
	{"dAreConnected",								(void **) &dAreConnected},
	{"dAreConnectedExcluding",						(void **) &dAreConnectedExcluding},
	{"dSimpleSpaceCreate",							(void **) &dSimpleSpaceCreate},
	{"dHashSpaceCreate",							(void **) &dHashSpaceCreate},
	{"dQuadTreeSpaceCreate",						(void **) &dQuadTreeSpaceCreate},
                                                                           
	{"dSpaceDestroy",								(void **) &dSpaceDestroy},
                                                                 
                                                                 
                                                           
                                                           
                                                             
                                                             
                                                                      
                                                                      
                                               
                                                    
                                                   
                                                   
                                                             
                                                      
                                                        
	{"dGeomDestroy",								(void **) &dGeomDestroy},
	{"dGeomSetData",								(void **) &dGeomSetData},
	{"dGeomGetData",								(void **) &dGeomGetData},
	{"dGeomSetBody",								(void **) &dGeomSetBody},
	{"dGeomGetBody",								(void **) &dGeomGetBody},
	{"dGeomSetPosition",							(void **) &dGeomSetPosition},
	{"dGeomSetRotation",							(void **) &dGeomSetRotation},
                                                               
                                                           
                                                             
                                                           
                                                             
                                                               
                                                    
	{"dGeomIsSpace",								(void **) &dGeomIsSpace},
                                                      
                                                      
                                                                  
                                                                 
                                                                  
                                                                 
                                                   
                                                    
                                                        
                                                                      
                                                                      
                                                                         
                                                                               
                                                                               
                                                                                  
                                                           
                                                      
                                                                      
                                                                        
                                                                      
                                                                        
                                                                         
	{"dCollide",									(void **) &dCollide},
	{"dSpaceCollide",								(void **) &dSpaceCollide},
	{"dSpaceCollide2",								(void **) &dSpaceCollide2},
	{"dCreateSphere",								(void **) &dCreateSphere},
                                                                  
                                                                  
                                                                    
	{"dCreateConvex",								(void **) &dCreateConvex},
                                                        
	{"dCreateBox",									(void **) &dCreateBox},
                                                               
                                                               
                                                               
                                                               
                                                    
                                                                 
                                                                 
                                                                  
	{"dCreateCapsule",								(void **) &dCreateCapsule},
                                                                    
                                                                    
                                                                      
	{"dCreateCylinder",								(void **) &dCreateCylinder},
                                                                      
                                                                      
                                                 
                                                             
                                                             
                                                   
                                                   
	{"dCreateGeomTransform",						(void **) &dCreateGeomTransform},
	{"dGeomTransformSetGeom",						(void **) &dGeomTransformSetGeom},
                                                                    
	{"dGeomTransformSetCleanup",					(void **) &dGeomTransformSetCleanup},
                                                                         
                                                                    
                                                                    
	{"dGeomTriMeshDataCreate",                      (void **) &dGeomTriMeshDataCreate},
	{"dGeomTriMeshDataDestroy",                     (void **) &dGeomTriMeshDataDestroy},
                                                                                   
                                                                                   
                                                                                            
                                                                                            
	{"dGeomTriMeshDataBuildSingle",                 (void **) &dGeomTriMeshDataBuildSingle},
                                                                                            
                                                                                           
                                                                                            
                                                                                           
                                                                                            
                                                                                          
                                                                                         
                                                                                         
                                                                                       
                                                                                       
                                                                                            
                                                                                            
                                                                                          
                                                                                          
                                                                                               
                                                                                               
	{"dCreateTriMesh",                              (void **) &dCreateTriMesh},
                                                                                   
                                                                                   
                                                                                    
                                                                                       
                                                                                        
                                                                                            
                                                                                       
                                                                                    
                                                                                            
                                                                                      
	{NULL, NULL}
};

                     
dllhandle_t ode_dll = NULL;
#endif
#endif

static void World_Physics_Init(void)
{
#ifdef USEODE
#ifndef LINK_TO_LIBODE
	const char* dllnames [] =
	{
# if defined(WIN32)
		"libode3.dll",
		"libode2.dll",
		"libode1.dll",
# elif defined(MACOSX)
		"libode.3.dylib",
		"libode.2.dylib",
		"libode.1.dylib",
# else
		"libode.so.3",
		"libode.so.2",
		"libode.so.1",
# endif
		NULL
	};
#endif

	Cvar_RegisterVariable(&physics_ode_quadtree_depth);
	Cvar_RegisterVariable(&physics_ode_contactsurfacelayer);
	Cvar_RegisterVariable(&physics_ode_worldstep_iterations);
	Cvar_RegisterVariable(&physics_ode_contact_mu);
	Cvar_RegisterVariable(&physics_ode_contact_erp);
	Cvar_RegisterVariable(&physics_ode_contact_cfm);
	Cvar_RegisterVariable(&physics_ode_contact_maxpoints);
	Cvar_RegisterVariable(&physics_ode_world_erp);
	Cvar_RegisterVariable(&physics_ode_world_cfm);
	Cvar_RegisterVariable(&physics_ode_world_damping);
	Cvar_RegisterVariable(&physics_ode_world_damping_linear);
	Cvar_RegisterVariable(&physics_ode_world_damping_linear_threshold);
	Cvar_RegisterVariable(&physics_ode_world_damping_angular);
	Cvar_RegisterVariable(&physics_ode_world_damping_angular_threshold);
	Cvar_RegisterVariable(&physics_ode_world_gravitymod);
	Cvar_RegisterVariable(&physics_ode_iterationsperframe);
	Cvar_RegisterVariable(&physics_ode_constantstep);
	Cvar_RegisterVariable(&physics_ode_movelimit);
	Cvar_RegisterVariable(&physics_ode_spinlimit);
	Cvar_RegisterVariable(&physics_ode_trick_fixnan);
	Cvar_RegisterVariable(&physics_ode_autodisable);
	Cvar_RegisterVariable(&physics_ode_autodisable_steps);
	Cvar_RegisterVariable(&physics_ode_autodisable_time);
	Cvar_RegisterVariable(&physics_ode_autodisable_threshold_linear);
	Cvar_RegisterVariable(&physics_ode_autodisable_threshold_angular);
	Cvar_RegisterVariable(&physics_ode_autodisable_threshold_samples);
	Cvar_RegisterVariable(&physics_ode_printstats);
	Cvar_RegisterVariable(&physics_ode_allowconvex);
	Cvar_RegisterVariable(&physics_ode);

#ifndef LINK_TO_LIBODE
	               
	if (Sys_LoadLibrary (dllnames, &ode_dll, odefuncs))
#endif
	{
		dInitODE();
                 
#ifndef LINK_TO_LIBODE
# ifdef dSINGLE
		if (!dCheckConfiguration("ODE_single_precision"))
# else
		if (!dCheckConfiguration("ODE_double_precision"))
# endif
		{
# ifdef dSINGLE
			Con_Printf("ODE library not compiled for single precision - incompatible!  Not using ODE physics.\n");
# else
			Con_Printf("ODE library not compiled for double precision - incompatible!  Not using ODE physics.\n");
# endif
			Sys_UnloadLibrary(&ode_dll);
			ode_dll = NULL;
		}
		else
		{
# ifdef dSINGLE
			Con_Printf("ODE library loaded with single precision.\n");
# else
			Con_Printf("ODE library loaded with double precision.\n");
# endif
			Con_Printf("ODE configuration list: %s\n", dGetConfiguration());
		}
#endif
	}
#endif
}

static void World_Physics_Shutdown(void)
{
#ifdef USEODE
#ifndef LINK_TO_LIBODE
	if (ode_dll)
#endif
	{
		dCloseODE();
#ifndef LINK_TO_LIBODE
		Sys_UnloadLibrary(&ode_dll);
		ode_dll = NULL;
#endif
	}
#endif
}

#ifdef USEODE
static void World_Physics_UpdateODE(world_t *world)
{
	dWorldID odeworld;

	odeworld = (dWorldID)world->physics.ode_world;

	              
	if (physics_ode_world_erp.value >= 0)
		dWorldSetERP(odeworld, physics_ode_world_erp.value);
	if (physics_ode_world_cfm.value >= 0)
		dWorldSetCFM(odeworld, physics_ode_world_cfm.value);
	          
	if (physics_ode_world_damping.integer)
	{
		dWorldSetLinearDamping(odeworld, (physics_ode_world_damping_linear.value >= 0) ? (physics_ode_world_damping_linear.value * physics_ode_world_damping.value) : 0);
		dWorldSetLinearDampingThreshold(odeworld, (physics_ode_world_damping_linear_threshold.value >= 0) ? (physics_ode_world_damping_linear_threshold.value * physics_ode_world_damping.value) : 0);
		dWorldSetAngularDamping(odeworld, (physics_ode_world_damping_angular.value >= 0) ? (physics_ode_world_damping_angular.value * physics_ode_world_damping.value) : 0);
		dWorldSetAngularDampingThreshold(odeworld, (physics_ode_world_damping_angular_threshold.value >= 0) ? (physics_ode_world_damping_angular_threshold.value * physics_ode_world_damping.value) : 0);
	}
	else
	{
		dWorldSetLinearDamping(odeworld, 0);
		dWorldSetLinearDampingThreshold(odeworld, 0);
		dWorldSetAngularDamping(odeworld, 0);
		dWorldSetAngularDampingThreshold(odeworld, 0);
	}
	              
	dWorldSetAutoDisableFlag(odeworld, (physics_ode_autodisable.integer) ? 1 : 0);
	if (physics_ode_autodisable.integer)
	{
		dWorldSetAutoDisableSteps(odeworld, bound(1, physics_ode_autodisable_steps.integer, 100)); 
		dWorldSetAutoDisableTime(odeworld, physics_ode_autodisable_time.value);
		dWorldSetAutoDisableAverageSamplesCount(odeworld, bound(1, physics_ode_autodisable_threshold_samples.integer, 100));
		dWorldSetAutoDisableLinearThreshold(odeworld, physics_ode_autodisable_threshold_linear.value); 
		dWorldSetAutoDisableAngularThreshold(odeworld, physics_ode_autodisable_threshold_angular.value); 
	}
}

static void World_Physics_EnableODE(world_t *world)
{
	dVector3 center, extents;
	if (world->physics.ode)
		return;
#ifndef LINK_TO_LIBODE
	if (!ode_dll)
		return;
#endif
	world->physics.ode = true;
	VectorMAM(0.5f, world->mins, 0.5f, world->maxs, center);
	VectorSubtract(world->maxs, center, extents);
	world->physics.ode_world = dWorldCreate();
	world->physics.ode_space = dQuadTreeSpaceCreate(NULL, center, extents, bound(1, physics_ode_quadtree_depth.integer, 10));
	world->physics.ode_contactgroup = dJointGroupCreate(0);

	World_Physics_UpdateODE(world);
}
#endif

static void World_Physics_Start(world_t *world)
{
#ifdef USEODE
	if (world->physics.ode)
		return;
	World_Physics_EnableODE(world);
#endif
}

static void World_Physics_End(world_t *world)
{
#ifdef USEODE
	if (world->physics.ode)
	{
		dWorldDestroy((dWorldID)world->physics.ode_world);
		dSpaceDestroy((dSpaceID)world->physics.ode_space);
		dJointGroupDestroy((dJointGroupID)world->physics.ode_contactgroup);
		world->physics.ode = false;
	}
#endif
}

void World_Physics_RemoveJointFromEntity(world_t *world, prvm_edict_t *ed)
{
	ed->priv.server->ode_joint_type = 0;
#ifdef USEODE
	if(ed->priv.server->ode_joint)
		dJointDestroy((dJointID)ed->priv.server->ode_joint);
	ed->priv.server->ode_joint = NULL;
#endif
}

void World_Physics_RemoveFromEntity(world_t *world, prvm_edict_t *ed)
{
	edict_odefunc_t *f, *nf;

	                                                          
	ed->priv.server->ode_physics = false;
#ifdef USEODE
	if (ed->priv.server->ode_geom)
		dGeomDestroy((dGeomID)ed->priv.server->ode_geom);
	ed->priv.server->ode_geom = NULL;
	if (ed->priv.server->ode_body)
	{
		dJointID j;
		dBodyID b1, b2;
		prvm_edict_t *ed2;
		while(dBodyGetNumJoints((dBodyID)ed->priv.server->ode_body))
		{
			j = dBodyGetJoint((dBodyID)ed->priv.server->ode_body, 0);
			ed2 = (prvm_edict_t *) dJointGetData(j);
			b1 = dJointGetBody(j, 0);
			b2 = dJointGetBody(j, 1);
			if(b1 == (dBodyID)ed->priv.server->ode_body)
			{
				b1 = 0;
				ed2->priv.server->ode_joint_enemy = 0;
			}
			if(b2 == (dBodyID)ed->priv.server->ode_body)
			{
				b2 = 0;
				ed2->priv.server->ode_joint_aiment = 0;
			}
			dJointAttach(j, b1, b2);
		}
		dBodyDestroy((dBodyID)ed->priv.server->ode_body);
	}
	ed->priv.server->ode_body = NULL;
#endif
	if (ed->priv.server->ode_vertex3f)
		Mem_Free(ed->priv.server->ode_vertex3f);
	ed->priv.server->ode_vertex3f = NULL;
	ed->priv.server->ode_numvertices = 0;
	if (ed->priv.server->ode_element3i)
		Mem_Free(ed->priv.server->ode_element3i);
	ed->priv.server->ode_element3i = NULL;
	ed->priv.server->ode_numtriangles = 0;
	if(ed->priv.server->ode_massbuf)
		Mem_Free(ed->priv.server->ode_massbuf);
	ed->priv.server->ode_massbuf = NULL;
	                        
	for(f = ed->priv.server->ode_func; f; f = nf)
	{
		nf = f->next;
		Mem_Free(f);
	}
	ed->priv.server->ode_func = NULL;
}

void World_Physics_ApplyCmd(prvm_edict_t *ed, edict_odefunc_t *f)
{
#ifdef USEODE
	dBodyID body = (dBodyID)ed->priv.server->ode_body;

	switch(f->type)
	{
	case ODEFUNC_ENABLE:
		dBodyEnable(body);
		break;
	case ODEFUNC_DISABLE:
		dBodyDisable(body);
		break;
	case ODEFUNC_FORCE:
		dBodyEnable(body);
		dBodyAddForceAtPos(body, f->v1[0], f->v1[1], f->v1[2], f->v2[0], f->v2[1], f->v2[2]);
		break;
	case ODEFUNC_TORQUE:
		dBodyEnable(body);
		dBodyAddTorque(body, f->v1[0], f->v1[1], f->v1[2]);
		break;
	default:
		break;
	}
#endif
}

#ifdef USEODE
static void World_Physics_Frame_BodyToEntity(world_t *world, prvm_edict_t *ed)
{
	prvm_prog_t *prog = world->prog;
	const dReal *avel;
	const dReal *o;
	const dReal *r;                                                            
	const dReal *vel;
	dBodyID body = (dBodyID)ed->priv.server->ode_body;
	int movetype;
	matrix4x4_t bodymatrix;
	matrix4x4_t entitymatrix;
	vec3_t angles;
	vec3_t avelocity;
	vec3_t forward, left, up;
	vec3_t origin;
	vec3_t spinvelocity;
	vec3_t velocity;
	int jointtype;
	if (!body)
		return;
	movetype = (int)PRVM_gameedictfloat(ed, movetype);
	if (movetype != MOVETYPE_PHYSICS)
	{
		jointtype = (int)PRVM_gameedictfloat(ed, jointtype);
		switch(jointtype)
		{
			                                   
			case JOINTTYPE_POINT:
				break;
			case JOINTTYPE_HINGE:
				break;
			case JOINTTYPE_SLIDER:
				break;
			case JOINTTYPE_UNIVERSAL:
				break;
			case JOINTTYPE_HINGE2:
				break;
			case JOINTTYPE_FIXED:
				break;
		}
		return;
	}
	                                                
	o = dBodyGetPosition(body);
	r = dBodyGetRotation(body);
	vel = dBodyGetLinearVel(body);
	avel = dBodyGetAngularVel(body);
	VectorCopy(o, origin);
	forward[0] = r[0];
	forward[1] = r[4];
	forward[2] = r[8];
	left[0] = r[1];
	left[1] = r[5];
	left[2] = r[9];
	up[0] = r[2];
	up[1] = r[6];
	up[2] = r[10];
	VectorCopy(vel, velocity);
	VectorCopy(avel, spinvelocity);
	Matrix4x4_FromVectors(&bodymatrix, forward, left, up, origin);
	Matrix4x4_Concat(&entitymatrix, &bodymatrix, &ed->priv.server->ode_offsetimatrix);
	Matrix4x4_ToVectors(&entitymatrix, forward, left, up, origin);

	AnglesFromVectors(angles, forward, up, false);
	VectorSet(avelocity, RAD2DEG(spinvelocity[PITCH]), RAD2DEG(spinvelocity[ROLL]), RAD2DEG(spinvelocity[YAW]));

	{
		float pitchsign = 1;
		if(prog == SVVM_prog)                          
		{
			pitchsign = SV_GetPitchSign(prog, ed);
		}
		else if(prog == CLVM_prog)
		{
			pitchsign = CL_GetPitchSign(prog, ed);
		}
		angles[PITCH] *= pitchsign;
		avelocity[PITCH] *= pitchsign;
	}

	VectorCopy(origin, PRVM_gameedictvector(ed, origin));
	VectorCopy(velocity, PRVM_gameedictvector(ed, velocity));
	                                                              
	                                                        
	                                                    
	                                                                   
	VectorCopy(angles, PRVM_gameedictvector(ed, angles));
	VectorCopy(avelocity, PRVM_gameedictvector(ed, avelocity));

	                                                                       
	VectorCopy(origin, ed->priv.server->ode_origin);
	VectorCopy(velocity, ed->priv.server->ode_velocity);
	VectorCopy(angles, ed->priv.server->ode_angles);
	VectorCopy(avelocity, ed->priv.server->ode_avelocity);
	ed->priv.server->ode_gravity = dBodyGetGravityMode(body) != 0;

	if(prog == SVVM_prog)                          
	{
		SV_LinkEdict(ed);
		SV_LinkEdict_TouchAreaGrid(ed);
	}
}

static void World_Physics_Frame_ForceFromEntity(world_t *world, prvm_edict_t *ed)
{
	prvm_prog_t *prog = world->prog;
	int forcetype = 0, movetype = 0, enemy = 0;
	vec3_t movedir, origin;

	movetype = (int)PRVM_gameedictfloat(ed, movetype);
	forcetype = (int)PRVM_gameedictfloat(ed, forcetype);
	if (movetype == MOVETYPE_PHYSICS)
		forcetype = FORCETYPE_NONE;                   
	if (!forcetype)
		return;
	enemy = PRVM_gameedictedict(ed, enemy);
	if (enemy <= 0 || enemy >= prog->num_edicts || prog->edicts[enemy].priv.required->free || prog->edicts[enemy].priv.server->ode_body == 0)
		return;
	VectorCopy(PRVM_gameedictvector(ed, movedir), movedir);
	VectorCopy(PRVM_gameedictvector(ed, origin), origin);
	dBodyEnable((dBodyID)prog->edicts[enemy].priv.server->ode_body);
	switch(forcetype)
	{
		case FORCETYPE_FORCE:
			if (movedir[0] || movedir[1] || movedir[2])
				dBodyAddForce((dBodyID)prog->edicts[enemy].priv.server->ode_body, movedir[0], movedir[1], movedir[2]);
			break;
		case FORCETYPE_FORCEATPOS:
			if (movedir[0] || movedir[1] || movedir[2])
				dBodyAddForceAtPos((dBodyID)prog->edicts[enemy].priv.server->ode_body, movedir[0], movedir[1], movedir[2], origin[0], origin[1], origin[2]);
			break;
		case FORCETYPE_TORQUE:
			if (movedir[0] || movedir[1] || movedir[2])
				dBodyAddTorque((dBodyID)prog->edicts[enemy].priv.server->ode_body, movedir[0], movedir[1], movedir[2]);
			break;
		case FORCETYPE_NONE:
		default:
			            
			break;
	}
}

static void World_Physics_Frame_JointFromEntity(world_t *world, prvm_edict_t *ed)
{
	prvm_prog_t *prog = world->prog;
	dJointID j = 0;
	dBodyID b1 = 0;
	dBodyID b2 = 0;
	int movetype = 0;
	int jointtype = 0;
	int enemy = 0, aiment = 0;
	vec3_t origin, velocity, angles, forward, left, up, movedir;
	vec_t CFM, ERP, FMax, Stop, Vel;

	movetype = (int)PRVM_gameedictfloat(ed, movetype);
	jointtype = (int)PRVM_gameedictfloat(ed, jointtype);
	VectorClear(origin);
	VectorClear(velocity);
	VectorClear(angles);
	VectorClear(movedir);
	enemy = PRVM_gameedictedict(ed, enemy);
	aiment = PRVM_gameedictedict(ed, aiment);
	VectorCopy(PRVM_gameedictvector(ed, origin), origin);
	VectorCopy(PRVM_gameedictvector(ed, velocity), velocity);
	VectorCopy(PRVM_gameedictvector(ed, angles), angles);
	VectorCopy(PRVM_gameedictvector(ed, movedir), movedir);
	if(movetype == MOVETYPE_PHYSICS)
		jointtype = JOINTTYPE_NONE;                   
	if(enemy <= 0 || enemy >= prog->num_edicts || prog->edicts[enemy].priv.required->free || prog->edicts[enemy].priv.server->ode_body == 0)
		enemy = 0;
	if(aiment <= 0 || aiment >= prog->num_edicts || prog->edicts[aiment].priv.required->free || prog->edicts[aiment].priv.server->ode_body == 0)
		aiment = 0;
	                                                                    
	                                                                              
	                                                                    
	if(movedir[0] > 0 && movedir[1] > 0)
	{
		float K = movedir[0];
		float D = movedir[1];
		float R = 2.0 * D * sqrt(K);                                                    
		CFM = 1.0 / (world->physics.ode_step * K + R);              
		ERP = world->physics.ode_step * K * CFM;
		Vel = 0;
		FMax = 0;
		Stop = movedir[2];
	}
	else if(movedir[1] < 0)
	{
		CFM = 0;
		ERP = 0;
		Vel = movedir[0];
		FMax = -movedir[1];                                                            
		Stop = movedir[2] > 0 ? movedir[2] : dInfinity;
	}
	else                                                                      
	{
		CFM = 0;
		ERP = 0;
		Vel = 0;
		FMax = 0;
		Stop = dInfinity;
	}
	if(jointtype == ed->priv.server->ode_joint_type && VectorCompare(origin, ed->priv.server->ode_joint_origin) && VectorCompare(velocity, ed->priv.server->ode_joint_velocity) && VectorCompare(angles, ed->priv.server->ode_joint_angles) && enemy == ed->priv.server->ode_joint_enemy && aiment == ed->priv.server->ode_joint_aiment && VectorCompare(movedir, ed->priv.server->ode_joint_movedir))
		return;                 
	AngleVectorsFLU(angles, forward, left, up);
	switch(jointtype)
	{
		case JOINTTYPE_POINT:
			j = dJointCreateBall((dWorldID)world->physics.ode_world, 0);
			break;
		case JOINTTYPE_HINGE:
			j = dJointCreateHinge((dWorldID)world->physics.ode_world, 0);
			break;
		case JOINTTYPE_SLIDER:
			j = dJointCreateSlider((dWorldID)world->physics.ode_world, 0);
			break;
		case JOINTTYPE_UNIVERSAL:
			j = dJointCreateUniversal((dWorldID)world->physics.ode_world, 0);
			break;
		case JOINTTYPE_HINGE2:
			j = dJointCreateHinge2((dWorldID)world->physics.ode_world, 0);
			break;
		case JOINTTYPE_FIXED:
			j = dJointCreateFixed((dWorldID)world->physics.ode_world, 0);
			break;
		case JOINTTYPE_NONE:
		default:
			           
			j = 0;
			break;
	}
	if(ed->priv.server->ode_joint)
	{
		                                                                  
		dJointAttach((dJointID)ed->priv.server->ode_joint, 0, 0);
		dJointDestroy((dJointID)ed->priv.server->ode_joint);
	}
	ed->priv.server->ode_joint = (void *) j;
	ed->priv.server->ode_joint_type = jointtype;
	ed->priv.server->ode_joint_enemy = enemy;
	ed->priv.server->ode_joint_aiment = aiment;
	VectorCopy(origin, ed->priv.server->ode_joint_origin);
	VectorCopy(velocity, ed->priv.server->ode_joint_velocity);
	VectorCopy(angles, ed->priv.server->ode_joint_angles);
	VectorCopy(movedir, ed->priv.server->ode_joint_movedir);
	if(j)
	{
		                                                               
		dJointSetData(j, (void *) ed);
		if(enemy)
			b1 = (dBodyID)prog->edicts[enemy].priv.server->ode_body;
		if(aiment)
			b2 = (dBodyID)prog->edicts[aiment].priv.server->ode_body;
		dJointAttach(j, b1, b2);

		switch(jointtype)
		{
			case JOINTTYPE_POINT:
				dJointSetBallAnchor(j, origin[0], origin[1], origin[2]);
				break;
			case JOINTTYPE_HINGE:
				dJointSetHingeAnchor(j, origin[0], origin[1], origin[2]);
				dJointSetHingeAxis(j, forward[0], forward[1], forward[2]);
				dJointSetHingeParam(j, dParamFMax, FMax);
				dJointSetHingeParam(j, dParamHiStop, Stop);
				dJointSetHingeParam(j, dParamLoStop, -Stop);
				dJointSetHingeParam(j, dParamStopCFM, CFM);
				dJointSetHingeParam(j, dParamStopERP, ERP);
				dJointSetHingeParam(j, dParamVel, Vel);
				break;
			case JOINTTYPE_SLIDER:
				dJointSetSliderAxis(j, forward[0], forward[1], forward[2]);
				dJointSetSliderParam(j, dParamFMax, FMax);
				dJointSetSliderParam(j, dParamHiStop, Stop);
				dJointSetSliderParam(j, dParamLoStop, -Stop);
				dJointSetSliderParam(j, dParamStopCFM, CFM);
				dJointSetSliderParam(j, dParamStopERP, ERP);
				dJointSetSliderParam(j, dParamVel, Vel);
				break;
			case JOINTTYPE_UNIVERSAL:
				dJointSetUniversalAnchor(j, origin[0], origin[1], origin[2]);
				dJointSetUniversalAxis1(j, forward[0], forward[1], forward[2]);
				dJointSetUniversalAxis2(j, up[0], up[1], up[2]);
				dJointSetUniversalParam(j, dParamFMax, FMax);
				dJointSetUniversalParam(j, dParamHiStop, Stop);
				dJointSetUniversalParam(j, dParamLoStop, -Stop);
				dJointSetUniversalParam(j, dParamStopCFM, CFM);
				dJointSetUniversalParam(j, dParamStopERP, ERP);
				dJointSetUniversalParam(j, dParamVel, Vel);
				dJointSetUniversalParam(j, dParamFMax2, FMax);
				dJointSetUniversalParam(j, dParamHiStop2, Stop);
				dJointSetUniversalParam(j, dParamLoStop2, -Stop);
				dJointSetUniversalParam(j, dParamStopCFM2, CFM);
				dJointSetUniversalParam(j, dParamStopERP2, ERP);
				dJointSetUniversalParam(j, dParamVel2, Vel);
				break;
			case JOINTTYPE_HINGE2:
				dJointSetHinge2Anchor(j, origin[0], origin[1], origin[2]);
				dJointSetHinge2Axis1(j, forward[0], forward[1], forward[2]);
				dJointSetHinge2Axis2(j, velocity[0], velocity[1], velocity[2]);
				dJointSetHinge2Param(j, dParamFMax, FMax);
				dJointSetHinge2Param(j, dParamHiStop, Stop);
				dJointSetHinge2Param(j, dParamLoStop, -Stop);
				dJointSetHinge2Param(j, dParamStopCFM, CFM);
				dJointSetHinge2Param(j, dParamStopERP, ERP);
				dJointSetHinge2Param(j, dParamVel, Vel);
				dJointSetHinge2Param(j, dParamFMax2, FMax);
				dJointSetHinge2Param(j, dParamHiStop2, Stop);
				dJointSetHinge2Param(j, dParamLoStop2, -Stop);
				dJointSetHinge2Param(j, dParamStopCFM2, CFM);
				dJointSetHinge2Param(j, dParamStopERP2, ERP);
				dJointSetHinge2Param(j, dParamVel2, Vel);
				break;
			case JOINTTYPE_FIXED:
				break;
			case 0:
			default:
				Sys_Error("what? but above the joint was valid...\n");
				break;
		}
#undef SETPARAMS

	}
}

                            
                                                     
dReal test_convex_planes[] = 
{
    1.0f ,0.0f ,0.0f ,2.25f,
    0.0f ,1.0f ,0.0f ,2.25f,
    0.0f ,0.0f ,1.0f ,2.25f,
    -1.0f,0.0f ,0.0f ,2.25f,
    0.0f ,-1.0f,0.0f ,2.25f,
    0.0f ,0.0f ,-1.0f,2.25f
};
const unsigned int test_convex_planecount = 6;
                    
dReal test_convex_points[] = 
{
	2.25f,2.25f,2.25f,              
	-2.25f,2.25f,2.25f,             
    2.25f,-2.25f,2.25f,             
    -2.25f,-2.25f,2.25f,            
    2.25f,2.25f,-2.25f,             
    -2.25f,2.25f,-2.25f,            
    2.25f,-2.25f,-2.25f,            
    -2.25f,-2.25f,-2.25f,           
};
const unsigned int test_convex_pointcount = 8;
                                          
unsigned int test_convex_polygons[] = 
{
	4,0,2,6,4,              
    4,1,0,4,5,              
    4,0,1,3,2,              
    4,3,1,5,7,              
    4,2,3,7,6,              
    4,5,4,6,7,              
};

static void World_Physics_Frame_BodyFromEntity(world_t *world, prvm_edict_t *ed)
{
	prvm_prog_t *prog = world->prog;
	const float *iv;
	const int *ie;
	dBodyID body;
	dMass mass;
	const dReal *ovelocity, *ospinvelocity;
	void *dataID;
	dp_model_t *model;
	float *ov;
	int *oe;
	int axisindex;
	int modelindex = 0;
	int movetype = MOVETYPE_NONE;
	int numtriangles;
	int numvertices;
	int solid = SOLID_NOT, geomtype = 0;
	int triangleindex;
	int vertexindex;
	mempool_t *mempool;
	qboolean modified = false;
	vec3_t angles;
	vec3_t avelocity;
	vec3_t entmaxs;
	vec3_t entmins;
	vec3_t forward;
	vec3_t geomcenter;
	vec3_t geomsize;
	vec3_t left;
	vec3_t origin;
	vec3_t spinvelocity;
	vec3_t up;
	vec3_t velocity;
	vec_t f;
	vec_t length;
	vec_t massval = 1.0f;
	vec_t movelimit;
	vec_t radius;
	vec3_t scale;
	vec_t spinlimit;
	vec_t test;
	qboolean gravity;
	qboolean geom_modified = false;
	edict_odefunc_t *func, *nextf;

	dReal *planes, *planesData, *pointsData;
	unsigned int *polygons, *polygonsData, polyvert;
	qboolean *mapped, *used, convex_compatible;
	int numplanes = 0, numpoints = 0, i;

#ifndef LINK_TO_LIBODE
	if (!ode_dll)
		return;
#endif
	VectorClear(entmins);
	VectorClear(entmaxs);

	solid = (int)PRVM_gameedictfloat(ed, solid);
	geomtype = (int)PRVM_gameedictfloat(ed, geomtype);
	movetype = (int)PRVM_gameedictfloat(ed, movetype);
	                                                   
	if (PRVM_gameedictvector(ed, modelscale_vec)[0] != 0.0 || PRVM_gameedictvector(ed, modelscale_vec)[1] != 0.0 || PRVM_gameedictvector(ed, modelscale_vec)[2] != 0.0)
		VectorCopy(PRVM_gameedictvector(ed, modelscale_vec), scale);
	else if (PRVM_gameedictfloat(ed, scale))
		VectorSet(scale, PRVM_gameedictfloat(ed, scale), PRVM_gameedictfloat(ed, scale), PRVM_gameedictfloat(ed, scale));
	else
		VectorSet(scale, 1.0f, 1.0f, 1.0f);
	modelindex = 0;
	if (PRVM_gameedictfloat(ed, mass))
		massval = PRVM_gameedictfloat(ed, mass);
	if (movetype != MOVETYPE_PHYSICS)
		massval = 1.0f;
	mempool = prog->progs_mempool;
	model = NULL;
	if (!geomtype)
	{
		                                                                     
		if (solid == SOLID_PHYSICS_TRIMESH || solid == SOLID_BSP)
			geomtype = GEOMTYPE_TRIMESH;
		else if (solid == SOLID_NOT || solid == SOLID_TRIGGER)
			geomtype = GEOMTYPE_NONE;
		else if (solid == SOLID_PHYSICS_SPHERE)
			geomtype = GEOMTYPE_SPHERE;
		else if (solid == SOLID_PHYSICS_CAPSULE)
			geomtype = GEOMTYPE_CAPSULE;
		else if (solid == SOLID_PHYSICS_CYLINDER)
			geomtype = GEOMTYPE_CYLINDER;
		else if (solid == SOLID_PHYSICS_BOX)
			geomtype = GEOMTYPE_BOX;
		else
			geomtype = GEOMTYPE_BOX;
	}
	if (geomtype == GEOMTYPE_TRIMESH)
	{
		modelindex = (int)PRVM_gameedictfloat(ed, modelindex);
		if (world == &sv.world)
			model = SV_GetModelByIndex(modelindex);
		else if (world == &cl.world)
			model = CL_GetModelByIndex(modelindex);
		else
			model = NULL;
		if (model)
		{
			entmins[0] = model->normalmins[0] * scale[0];
			entmins[1] = model->normalmins[1] * scale[1];
			entmins[2] = model->normalmins[2] * scale[2];
			entmaxs[0] = model->normalmaxs[0] * scale[0];
			entmaxs[1] = model->normalmaxs[1] * scale[1];
			entmaxs[2] = model->normalmaxs[2] * scale[2];
			geom_modified = !VectorCompare(ed->priv.server->ode_scale, scale) || ed->priv.server->ode_modelindex != modelindex;
		}
		else
		{
			Con_Printf("entity %i (classname %s) has no model\n", PRVM_NUM_FOR_EDICT(ed), PRVM_GetString(prog, PRVM_gameedictstring(ed, classname)));
			geomtype = GEOMTYPE_BOX;
			VectorCopy(PRVM_gameedictvector(ed, mins), entmins);
			VectorCopy(PRVM_gameedictvector(ed, maxs), entmaxs);
			modelindex = 0;
			geom_modified = !VectorCompare(ed->priv.server->ode_mins, entmins) || !VectorCompare(ed->priv.server->ode_maxs, entmaxs);
		}
	}
	else if (geomtype && geomtype != GEOMTYPE_NONE)
	{
		VectorCopy(PRVM_gameedictvector(ed, mins), entmins);
		VectorCopy(PRVM_gameedictvector(ed, maxs), entmaxs);
		geom_modified = !VectorCompare(ed->priv.server->ode_mins, entmins) || !VectorCompare(ed->priv.server->ode_maxs, entmaxs);
	}
	else
	{
		                                      
		if (ed->priv.server->ode_physics)
			World_Physics_RemoveFromEntity(world, ed);
		return;
	}

	VectorSubtract(entmaxs, entmins, geomsize);
	if (VectorLength2(geomsize) == 0)
	{
		                                               
		if (ed->priv.server->ode_physics)
			World_Physics_RemoveFromEntity(world, ed);
		return;
	}

	               
	ed->priv.server->ode_friction = PRVM_gameedictfloat(ed, friction) ? PRVM_gameedictfloat(ed, friction) : 1.0f;

	                                                 
	if (!ed->priv.server->ode_physics || ed->priv.server->ode_mass != massval || geom_modified)
	{
		modified = true;
		World_Physics_RemoveFromEntity(world, ed);
		ed->priv.server->ode_physics = true;
		VectorMAM(0.5f, entmins, 0.5f, entmaxs, geomcenter);
		if (PRVM_gameedictvector(ed, massofs))
			VectorCopy(geomcenter, PRVM_gameedictvector(ed, massofs));

		                 
		if (geomsize[0] * geomsize[1] * geomsize[2] == 0)
		{
			if (movetype == MOVETYPE_PHYSICS)
				Con_Printf("entity %i (classname %s) .mass * .size_x * .size_y * .size_z == 0\n", PRVM_NUM_FOR_EDICT(ed), PRVM_GetString(prog, PRVM_gameedictstring(ed, classname)));
			VectorSet(geomsize, 1.0f, 1.0f, 1.0f);
		}

		              
		switch(geomtype)
		{
		case GEOMTYPE_TRIMESH:
			                                                                                      
			if (!model->brush.collisionmesh)
				Mod_CreateCollisionMesh(model);
			if (!model->brush.collisionmesh)
			{
				Con_Printf("entity %i (classname %s) has no geometry\n", PRVM_NUM_FOR_EDICT(ed), PRVM_GetString(prog, PRVM_gameedictstring(ed, classname)));
				goto treatasbox;
			}

			                                              
			convex_compatible = false;
			for (i = 0;i < model->nummodelsurfaces;i++)
			{
				if (!strcmp(((msurface_t *)(model->data_surfaces + model->firstmodelsurface + i))->texture->name, "collisionconvex"))
				{
					convex_compatible = true;
					break;
				}
			}

			                                                               
			                                                                  
			                                                                 
			                                                                 
			                                                              
			ed->priv.server->ode_numvertices = numvertices = model->brush.collisionmesh->numverts;
			ed->priv.server->ode_vertex3f = (float *)Mem_Alloc(mempool, numvertices * sizeof(float[3]));

			                                                                         
			VectorSet(entmins, 0, 0, 0);
			VectorSet(entmaxs, 0, 0, 0);
			for (vertexindex = 0, ov = ed->priv.server->ode_vertex3f, iv = model->brush.collisionmesh->vertex3f;vertexindex < numvertices;vertexindex++, ov += 3, iv += 3)
			{
				ov[0] = iv[0] * scale[0];
				ov[1] = iv[1] * scale[1];
				ov[2] = iv[2] * scale[2];
				entmins[0] = min(entmins[0], ov[0]);
				entmins[1] = min(entmins[1], ov[1]);
				entmins[2] = min(entmins[2], ov[2]);
				entmaxs[0] = max(entmaxs[0], ov[0]);
				entmaxs[1] = max(entmaxs[1], ov[1]);
				entmaxs[2] = max(entmaxs[2], ov[2]);
			}
			if (!PRVM_gameedictvector(ed, massofs))
				VectorMAM(0.5f, entmins, 0.5f, entmaxs, geomcenter);
			for (vertexindex = 0, ov = ed->priv.server->ode_vertex3f, iv = model->brush.collisionmesh->vertex3f;vertexindex < numvertices;vertexindex++, ov += 3, iv += 3)
			{
				ov[0] = ov[0] - geomcenter[0];
				ov[1] = ov[1] - geomcenter[1];
				ov[2] = ov[2] - geomcenter[2];
			}
			VectorSubtract(entmaxs, entmins, geomsize);
			if (VectorLength2(geomsize) == 0)
			{
				if (movetype == MOVETYPE_PHYSICS)
					Con_Printf("entity %i collision mesh has null geomsize\n", PRVM_NUM_FOR_EDICT(ed));
				VectorSet(geomsize, 1.0f, 1.0f, 1.0f);
			}
			ed->priv.server->ode_numtriangles = numtriangles = model->brush.collisionmesh->numtriangles;
			ed->priv.server->ode_element3i = (int *)Mem_Alloc(mempool, numtriangles * sizeof(int[3]));
			                                                                                                                                    
			for (triangleindex = 0, oe = ed->priv.server->ode_element3i, ie = model->brush.collisionmesh->element3i;triangleindex < numtriangles;triangleindex++, oe += 3, ie += 3)
			{
				oe[0] = ie[2];
				oe[1] = ie[1];
				oe[2] = ie[0];
			}
			              
			Matrix4x4_CreateTranslate(&ed->priv.server->ode_offsetmatrix, geomcenter[0], geomcenter[1], geomcenter[2]);
			if (!convex_compatible || !physics_ode_allowconvex.integer)
			{
				          
				dataID = dGeomTriMeshDataCreate();
				dGeomTriMeshDataBuildSingle((dTriMeshDataID)dataID, (void*)ed->priv.server->ode_vertex3f, sizeof(float[3]), ed->priv.server->ode_numvertices, ed->priv.server->ode_element3i, ed->priv.server->ode_numtriangles*3, sizeof(int[3]));
				ed->priv.server->ode_geom = (void *)dCreateTriMesh((dSpaceID)world->physics.ode_space, (dTriMeshDataID)dataID, NULL, NULL, NULL);
				dMassSetBoxTotal(&mass, massval, geomsize[0], geomsize[1], geomsize[2]);
			}
			else
			{
				                                              
				                                         
				                                                                                 
				                                                              

				Con_Printf("Build convex hull for model %s...\n", model->name);
				                                          
				                                                                         
				                                          
				                                    
				                                                                                      
				                                        
				                                                                                                      
				                                                                                         
				polygonsData = polygons = (unsigned int *)Mem_Alloc(mempool, numtriangles*sizeof(int)*4);
				planesData = planes = (dReal *)Mem_Alloc(mempool, numtriangles*sizeof(dReal)*4);
				mapped = (qboolean *)Mem_Alloc(mempool, numvertices*sizeof(qboolean));
				used = (qboolean *)Mem_Alloc(mempool, numtriangles*sizeof(qboolean));
				memset(mapped, 0, numvertices*sizeof(qboolean));
				memset(used, 0, numtriangles*sizeof(qboolean));
				numplanes = numpoints = polyvert = 0;
				                    
				                                    
				Con_Printf("Building...\n");
				iv = ed->priv.server->ode_vertex3f;
				for (triangleindex = 0; triangleindex < numtriangles; triangleindex++)
				{
					                            
					if (used[triangleindex])
						continue; 
					               
					                                     
					ie = &model->brush.collisionmesh->element3i[triangleindex*3];
					used[triangleindex] = true;
					TriangleNormal(&iv[ie[0]*3], &iv[ie[1]*3], &iv[ie[2]*3], planes);
					VectorNormalize(planes);
					polygons[0] = 3;
					polygons[3] = (unsigned int)ie[0]; mapped[polygons[3]] = true;
					polygons[2] = (unsigned int)ie[1]; mapped[polygons[2]] = true;
					polygons[1] = (unsigned int)ie[2]; mapped[polygons[1]] = true;

					                                         
					for (i = triangleindex; i < numtriangles; i++)
					{
						if (used[i])
							continue;
						                                   
						for (polyvert = 1; polyvert <= polygons[0]; polyvert++)
						{
							                                                                        
						}
					}

					                               
					planes[3] = DotProduct(&iv[polygons[1]*3], planes);
					polygons += (polygons[0]+1);
					planes += 4;
					numplanes++;
				}
				Mem_Free(used);
				              
				for (vertexindex = 0, numpoints = 0; vertexindex < numvertices; vertexindex++)
					if (mapped[vertexindex])
						numpoints++;
				pointsData = (dReal *)Mem_Alloc(mempool, numpoints*sizeof(dReal)*3 + numplanes*sizeof(dReal)*4);                      
				for (vertexindex = 0, numpoints = 0; vertexindex < numvertices; vertexindex++)
				{
					if (mapped[vertexindex])
					{
						VectorCopy(&iv[vertexindex*3], &pointsData[numpoints*3]);
						numpoints++;
					}
				}
				Mem_Free(mapped);
				Con_Printf("Points: \n");
				for (i = 0; i < (int)numpoints; i++)
					Con_Printf("%3i: %3.1f %3.1f %3.1f\n", i, pointsData[i*3], pointsData[i*3+1], pointsData[i*3+2]);
				              
				planes = planesData;
				planesData = pointsData + numpoints*3;
				memcpy(planesData, planes, numplanes*sizeof(dReal)*4);
				Mem_Free(planes);
				Con_Printf("planes...\n");
				for (i = 0; i < numplanes; i++)
					Con_Printf("%3i: %1.1f %1.1f %1.1f %1.1f\n", i, planesData[i*4], planesData[i*4 + 1], planesData[i*4 + 2], planesData[i*4 + 3]);
				                
				polyvert = polygons - polygonsData;
				polygons = polygonsData;
				polygonsData = (unsigned int *)Mem_Alloc(mempool, polyvert*sizeof(int));
				memcpy(polygonsData, polygons, polyvert*sizeof(int));
				Mem_Free(polygons);
				Con_Printf("Polygons: \n");
				polygons = polygonsData;
				for (i = 0; i < numplanes; i++)
				{
					Con_Printf("%3i : %i ", i, polygons[0]);
					for (triangleindex = 1; triangleindex <= (int)polygons[0]; triangleindex++)
						Con_Printf("%3i ", polygons[triangleindex]);
					polygons += (polygons[0]+1);
					Con_Printf("\n");
				}
				Mem_Free(ed->priv.server->ode_element3i);
				ed->priv.server->ode_element3i = (int *)polygonsData;
				Mem_Free(ed->priv.server->ode_vertex3f);
				ed->priv.server->ode_vertex3f = (float *)pointsData;
				                                                                                                                                   
				                                      
				Con_Printf("Check...\n");
				polygons = polygonsData;
				for (i = 0; i < numplanes; i++)
				{
					if((pointsData[(polygons[1]*3)+0]*pointsData[(polygons[2]*3)+1]*pointsData[(polygons[3]*3)+2] +
						pointsData[(polygons[1]*3)+1]*pointsData[(polygons[2]*3)+2]*pointsData[(polygons[3]*3)+0] +
						pointsData[(polygons[1]*3)+2]*pointsData[(polygons[2]*3)+0]*pointsData[(polygons[3]*3)+1] -
						pointsData[(polygons[1]*3)+2]*pointsData[(polygons[2]*3)+1]*pointsData[(polygons[3]*3)+0] -
						pointsData[(polygons[1]*3)+1]*pointsData[(polygons[2]*3)+0]*pointsData[(polygons[3]*3)+2] -
						pointsData[(polygons[1]*3)+0]*pointsData[(polygons[2]*3)+2]*pointsData[(polygons[3]*3)+1]) < 0)
						Con_Printf("WARNING: Polygon %d is not defined counterclockwise\n", i);
					if (planesData[(i*4)+3] < 0)
						Con_Printf("WARNING: Plane %d does not contain the origin\n", i);
					polygons += (*polygons + 1);
				}
				              
				Con_Printf("Create geom...\n");
				ed->priv.server->ode_geom = (void *)dCreateConvex((dSpaceID)world->physics.ode_space, planesData, numplanes, pointsData, numpoints, polygonsData);
				dMassSetBoxTotal(&mass, massval, geomsize[0], geomsize[1], geomsize[2]);
				Con_Printf("Done!\n");
			}
			break;
		case GEOMTYPE_BOX:
treatasbox:
			Matrix4x4_CreateTranslate(&ed->priv.server->ode_offsetmatrix, geomcenter[0], geomcenter[1], geomcenter[2]);
			ed->priv.server->ode_geom = (void *)dCreateBox((dSpaceID)world->physics.ode_space, geomsize[0], geomsize[1], geomsize[2]);
			dMassSetBoxTotal(&mass, massval, geomsize[0], geomsize[1], geomsize[2]);
			break;
		case GEOMTYPE_SPHERE:
			Matrix4x4_CreateTranslate(&ed->priv.server->ode_offsetmatrix, geomcenter[0], geomcenter[1], geomcenter[2]);
			ed->priv.server->ode_geom = (void *)dCreateSphere((dSpaceID)world->physics.ode_space, geomsize[0] * 0.5f);
			dMassSetSphereTotal(&mass, massval, geomsize[0] * 0.5f);
			break;
		case GEOMTYPE_CAPSULE:
			axisindex = 0;
			if (geomsize[axisindex] < geomsize[1])
				axisindex = 1;
			if (geomsize[axisindex] < geomsize[2])
				axisindex = 2;
			                                                                 
			                                                             
			                                                           
			                  
			if (axisindex == 0)
			{
				Matrix4x4_CreateFromQuakeEntity(&ed->priv.server->ode_offsetmatrix, geomcenter[0], geomcenter[1], geomcenter[2], 0, 0, 90, 1);
				radius = min(geomsize[1], geomsize[2]) * 0.5f;
			}
			else if (axisindex == 1)
			{
				Matrix4x4_CreateFromQuakeEntity(&ed->priv.server->ode_offsetmatrix, geomcenter[0], geomcenter[1], geomcenter[2], 90, 0, 0, 1);
				radius = min(geomsize[0], geomsize[2]) * 0.5f;
			}
			else
			{
				Matrix4x4_CreateFromQuakeEntity(&ed->priv.server->ode_offsetmatrix, geomcenter[0], geomcenter[1], geomcenter[2], 0, 0, 0, 1);
				radius = min(geomsize[0], geomsize[1]) * 0.5f;
			}
			length = geomsize[axisindex] - radius*2;
			                                                                 
			                                                                  
			                                                        
			ed->priv.server->ode_geom = (void *)dCreateCapsule((dSpaceID)world->physics.ode_space, radius, length);
			dMassSetCapsuleTotal(&mass, massval, axisindex+1, radius, length);
			break;
		case GEOMTYPE_CAPSULE_X:
			Matrix4x4_CreateFromQuakeEntity(&ed->priv.server->ode_offsetmatrix, geomcenter[0], geomcenter[1], geomcenter[2], 0, 0, 90, 1);
			radius = min(geomsize[1], geomsize[2]) * 0.5f;
			length = geomsize[0] - radius*2;
			                                                    
			if (length <= 0)
			{
				radius -= (1 - length)*0.5;
				length = 1;
			}
			ed->priv.server->ode_geom = (void *)dCreateCapsule((dSpaceID)world->physics.ode_space, radius, length);
			dMassSetCapsuleTotal(&mass, massval, 1, radius, length);
			break;
		case GEOMTYPE_CAPSULE_Y:
			Matrix4x4_CreateFromQuakeEntity(&ed->priv.server->ode_offsetmatrix, geomcenter[0], geomcenter[1], geomcenter[2], 90, 0, 0, 1);
			radius = min(geomsize[0], geomsize[2]) * 0.5f;
			length = geomsize[1] - radius*2;
			                                                    
			if (length <= 0)
			{
				radius -= (1 - length)*0.5;
				length = 1;
			}
			ed->priv.server->ode_geom = (void *)dCreateCapsule((dSpaceID)world->physics.ode_space, radius, length);
			dMassSetCapsuleTotal(&mass, massval, 2, radius, length);
			break;
		case GEOMTYPE_CAPSULE_Z:
			Matrix4x4_CreateFromQuakeEntity(&ed->priv.server->ode_offsetmatrix, geomcenter[0], geomcenter[1], geomcenter[2], 0, 0, 0, 1);
			radius = min(geomsize[1], geomsize[0]) * 0.5f;
			length = geomsize[2] - radius*2;
			                                                    
			if (length <= 0)
			{
				radius -= (1 - length)*0.5;
				length = 1;
			}
			ed->priv.server->ode_geom = (void *)dCreateCapsule((dSpaceID)world->physics.ode_space, radius, length);
			dMassSetCapsuleTotal(&mass, massval, 3, radius, length);
			break;
		case GEOMTYPE_CYLINDER:
			axisindex = 0;
			if (geomsize[axisindex] < geomsize[1])
				axisindex = 1;
			if (geomsize[axisindex] < geomsize[2])
				axisindex = 2;
			                                                                 
			                                                             
			                                                           
			                  
			if (axisindex == 0)
			{
				Matrix4x4_CreateFromQuakeEntity(&ed->priv.server->ode_offsetmatrix, geomcenter[0], geomcenter[1], geomcenter[2], 0, 0, 90, 1);
				radius = min(geomsize[1], geomsize[2]) * 0.5f;
			}
			else if (axisindex == 1)
			{
				Matrix4x4_CreateFromQuakeEntity(&ed->priv.server->ode_offsetmatrix, geomcenter[0], geomcenter[1], geomcenter[2], 90, 0, 0, 1);
				radius = min(geomsize[0], geomsize[2]) * 0.5f;
			}
			else
			{
				Matrix4x4_CreateFromQuakeEntity(&ed->priv.server->ode_offsetmatrix, geomcenter[0], geomcenter[1], geomcenter[2], 0, 0, 0, 1);
				radius = min(geomsize[0], geomsize[1]) * 0.5f;
			}
			length = geomsize[axisindex];
			                                                    
			if (length <= 0)
			{
				radius -= (1 - length)*0.5;
				length = 1;
			}
			ed->priv.server->ode_geom = (void *)dCreateCylinder((dSpaceID)world->physics.ode_space, radius, length);
			dMassSetCylinderTotal(&mass, massval, axisindex+1, radius, length);
			break;
		case GEOMTYPE_CYLINDER_X:
			Matrix4x4_CreateFromQuakeEntity(&ed->priv.server->ode_offsetmatrix, geomcenter[0], geomcenter[1], geomcenter[2], 0, 0, 90, 1);
			radius = min(geomsize[1], geomsize[2]) * 0.5f;
			length = geomsize[0];
			ed->priv.server->ode_geom = (void *)dCreateCylinder((dSpaceID)world->physics.ode_space, radius, length);
			dMassSetCylinderTotal(&mass, massval, 1, radius, length);
			break;
		case GEOMTYPE_CYLINDER_Y:
			Matrix4x4_CreateFromQuakeEntity(&ed->priv.server->ode_offsetmatrix, geomcenter[0], geomcenter[1], geomcenter[2], 90, 0, 0, 1);
			radius = min(geomsize[0], geomsize[2]) * 0.5f;
			length = geomsize[1];
			ed->priv.server->ode_geom = (void *)dCreateCylinder((dSpaceID)world->physics.ode_space, radius, length);
			dMassSetCylinderTotal(&mass, massval, 2, radius, length);
			break;
		case GEOMTYPE_CYLINDER_Z:
			Matrix4x4_CreateFromQuakeEntity(&ed->priv.server->ode_offsetmatrix, geomcenter[0], geomcenter[1], geomcenter[2], 0, 0, 0, 1);
			radius = min(geomsize[0], geomsize[1]) * 0.5f;
			length = geomsize[2];
			ed->priv.server->ode_geom = (void *)dCreateCylinder((dSpaceID)world->physics.ode_space, radius, length);
			dMassSetCylinderTotal(&mass, massval, 3, radius, length);
			break;
		default:
			Sys_Error("World_Physics_BodyFromEntity: unrecognized geomtype value %i was accepted by filter\n", solid);
			                                                              
			                                                             
			                                                   
			goto treatasbox;
		}
		ed->priv.server->ode_mass = massval;
		ed->priv.server->ode_modelindex = modelindex;
		VectorCopy(entmins, ed->priv.server->ode_mins);
		VectorCopy(entmaxs, ed->priv.server->ode_maxs);
		VectorCopy(scale, ed->priv.server->ode_scale);
		ed->priv.server->ode_movelimit = min(geomsize[0], min(geomsize[1], geomsize[2]));
		Matrix4x4_Invert_Simple(&ed->priv.server->ode_offsetimatrix, &ed->priv.server->ode_offsetmatrix);
		ed->priv.server->ode_massbuf = Mem_Alloc(mempool, sizeof(mass));
		memcpy(ed->priv.server->ode_massbuf, &mass, sizeof(dMass));
	}

	if (ed->priv.server->ode_geom)
		dGeomSetData((dGeomID)ed->priv.server->ode_geom, (void*)ed);
	if (movetype == MOVETYPE_PHYSICS && ed->priv.server->ode_geom)
	{
		                    
		if (ed->priv.server->ode_body == NULL)
		{
			ed->priv.server->ode_body = (void *)(body = dBodyCreate((dWorldID)world->physics.ode_world));
			dGeomSetBody((dGeomID)ed->priv.server->ode_geom, body);
			dBodySetData(body, (void*)ed);
			dBodySetMass(body, (dMass *) ed->priv.server->ode_massbuf);
			modified = true;
		}
	}
	else
	{
		                        
		if (ed->priv.server->ode_body != NULL)
		{
			if(ed->priv.server->ode_geom)
				dGeomSetBody((dGeomID)ed->priv.server->ode_geom, 0);
			dBodyDestroy((dBodyID) ed->priv.server->ode_body);
			ed->priv.server->ode_body = NULL;
			modified = true;
		}
	}

	                               
	VectorClear(origin);
	VectorClear(velocity);
	                       
	                    
	                  
	                            
	VectorClear(angles);
	VectorClear(avelocity);
	gravity = true;
	VectorCopy(PRVM_gameedictvector(ed, origin), origin);
	VectorCopy(PRVM_gameedictvector(ed, velocity), velocity);
	                                                              
	                                                        
	                                                    
	                                                                   
	VectorCopy(PRVM_gameedictvector(ed, angles), angles);
	VectorCopy(PRVM_gameedictvector(ed, avelocity), avelocity);
	if (PRVM_gameedictfloat(ed, gravity) != 0.0f && PRVM_gameedictfloat(ed, gravity) < 0.5f) gravity = false;
	if (ed == prog->edicts)
		gravity = false;

	                                    
	                                                    
	{
		float pitchsign = 1;
		vec3_t qangles, qavelocity;
		VectorCopy(angles, qangles);
		VectorCopy(avelocity, qavelocity);

		if(prog == SVVM_prog)                          
		{
			pitchsign = SV_GetPitchSign(prog, ed);
		}
		else if(prog == CLVM_prog)
		{
			pitchsign = CL_GetPitchSign(prog, ed);
		}
		qangles[PITCH] *= pitchsign;
		qavelocity[PITCH] *= pitchsign;

		AngleVectorsFLU(qangles, forward, left, up);
		                                                             
		                                     
		VectorSet(spinvelocity, DEG2RAD(qavelocity[PITCH]), DEG2RAD(qavelocity[ROLL]), DEG2RAD(qavelocity[YAW]));
	}

	                                    
	switch (solid)
	{
	case SOLID_BBOX:
	case SOLID_SLIDEBOX:
	case SOLID_CORPSE:
		VectorSet(forward, 1, 0, 0);
		VectorSet(left, 0, 1, 0);
		VectorSet(up, 0, 0, 1);
		VectorSet(spinvelocity, 0, 0, 0);
		break;
	}


	                          
	if (physics_ode_trick_fixnan.integer)
	{
		test = VectorLength2(origin) + VectorLength2(forward) + VectorLength2(left) + VectorLength2(up) + VectorLength2(velocity) + VectorLength2(spinvelocity);
		if (VEC_IS_NAN(test))
		{
			modified = true;
			                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
			if (physics_ode_trick_fixnan.integer >= 2)
				Con_Printf("Fixing NAN values on entity %i : .classname = \"%s\" .origin = '%f %f %f' .velocity = '%f %f %f' .angles = '%f %f %f' .avelocity = '%f %f %f'\n", PRVM_NUM_FOR_EDICT(ed), PRVM_GetString(prog, PRVM_gameedictstring(ed, classname)), origin[0], origin[1], origin[2], velocity[0], velocity[1], velocity[2], angles[0], angles[1], angles[2], avelocity[0], avelocity[1], avelocity[2]);
			test = VectorLength2(origin);
			if (VEC_IS_NAN(test))
				VectorClear(origin);
			test = VectorLength2(forward) * VectorLength2(left) * VectorLength2(up);
			if (VEC_IS_NAN(test))
			{
				VectorSet(angles, 0, 0, 0);
				VectorSet(forward, 1, 0, 0);
				VectorSet(left, 0, 1, 0);
				VectorSet(up, 0, 0, 1);
			}
			test = VectorLength2(velocity);
			if (VEC_IS_NAN(test))
				VectorClear(velocity);
			test = VectorLength2(spinvelocity);
			if (VEC_IS_NAN(test))
			{
				VectorClear(avelocity);
				VectorClear(spinvelocity);
			}
		}
	}

	                                           
	if (!VectorCompare(origin, ed->priv.server->ode_origin)
	 || !VectorCompare(velocity, ed->priv.server->ode_velocity)
	 || !VectorCompare(angles, ed->priv.server->ode_angles)
	 || !VectorCompare(avelocity, ed->priv.server->ode_avelocity)
	 || gravity != ed->priv.server->ode_gravity)
		modified = true;

	                                              
	body = (dBodyID)ed->priv.server->ode_body;
	if (modified && ed->priv.server->ode_geom)
	{
		dVector3 r[3];
		matrix4x4_t entitymatrix;
		matrix4x4_t bodymatrix;

#if 0
		Con_Printf("entity %i got changed by QC\n", (int) (ed - prog->edicts));
		if(!VectorCompare(origin, ed->priv.server->ode_origin))
			Con_Printf("  origin: %f %f %f -> %f %f %f\n", ed->priv.server->ode_origin[0], ed->priv.server->ode_origin[1], ed->priv.server->ode_origin[2], origin[0], origin[1], origin[2]);
		if(!VectorCompare(velocity, ed->priv.server->ode_velocity))
			Con_Printf("  velocity: %f %f %f -> %f %f %f\n", ed->priv.server->ode_velocity[0], ed->priv.server->ode_velocity[1], ed->priv.server->ode_velocity[2], velocity[0], velocity[1], velocity[2]);
		if(!VectorCompare(angles, ed->priv.server->ode_angles))
			Con_Printf("  angles: %f %f %f -> %f %f %f\n", ed->priv.server->ode_angles[0], ed->priv.server->ode_angles[1], ed->priv.server->ode_angles[2], angles[0], angles[1], angles[2]);
		if(!VectorCompare(avelocity, ed->priv.server->ode_avelocity))
			Con_Printf("  avelocity: %f %f %f -> %f %f %f\n", ed->priv.server->ode_avelocity[0], ed->priv.server->ode_avelocity[1], ed->priv.server->ode_avelocity[2], avelocity[0], avelocity[1], avelocity[2]);
		if(gravity != ed->priv.server->ode_gravity)
			Con_Printf("  gravity: %i -> %i\n", ed->priv.server->ode_gravity, gravity);
#endif
		                                                                       
		VectorCopy(origin, ed->priv.server->ode_origin);
		VectorCopy(velocity, ed->priv.server->ode_velocity);
		VectorCopy(angles, ed->priv.server->ode_angles);
		VectorCopy(avelocity, ed->priv.server->ode_avelocity);
		ed->priv.server->ode_gravity = gravity;

		Matrix4x4_FromVectors(&entitymatrix, forward, left, up, origin);
		Matrix4x4_Concat(&bodymatrix, &entitymatrix, &ed->priv.server->ode_offsetmatrix);
		Matrix4x4_ToVectors(&bodymatrix, forward, left, up, origin);
		r[0][0] = forward[0];
		r[1][0] = forward[1];
		r[2][0] = forward[2];
		r[0][1] = left[0];
		r[1][1] = left[1];
		r[2][1] = left[2];
		r[0][2] = up[0];
		r[1][2] = up[1];
		r[2][2] = up[2];
		if (body)
		{
			if (movetype == MOVETYPE_PHYSICS)
			{
				dGeomSetBody((dGeomID)ed->priv.server->ode_geom, body);
				dBodySetPosition(body, origin[0], origin[1], origin[2]);
				dBodySetRotation(body, r[0]);
				dBodySetLinearVel(body, velocity[0], velocity[1], velocity[2]);
				dBodySetAngularVel(body, spinvelocity[0], spinvelocity[1], spinvelocity[2]);
				dBodySetGravityMode(body, gravity);
			}
			else
			{
				dGeomSetBody((dGeomID)ed->priv.server->ode_geom, body);
				dBodySetPosition(body, origin[0], origin[1], origin[2]);
				dBodySetRotation(body, r[0]);
				dBodySetLinearVel(body, velocity[0], velocity[1], velocity[2]);
				dBodySetAngularVel(body, spinvelocity[0], spinvelocity[1], spinvelocity[2]);
				dBodySetGravityMode(body, gravity);
				dGeomSetBody((dGeomID)ed->priv.server->ode_geom, 0);
			}
		}
		else
		{
			                                                                   
			dGeomSetBody((dGeomID)ed->priv.server->ode_geom, 0);                                                                     
			dGeomSetPosition((dGeomID)ed->priv.server->ode_geom, origin[0], origin[1], origin[2]);
			dGeomSetRotation((dGeomID)ed->priv.server->ode_geom, r[0]);
		}
	}

	if (body)
	{

		                                                                  
		ovelocity = dBodyGetLinearVel(body);
		ospinvelocity = dBodyGetAngularVel(body);
		movelimit = ed->priv.server->ode_movelimit * world->physics.ode_movelimit;
		test = VectorLength2(ovelocity);
		if (test > movelimit*movelimit)
		{
			                                              
			                                                              
			f = movelimit / sqrt(test);
			VectorScale(ovelocity, f, velocity);
			VectorScale(ospinvelocity, f, spinvelocity);
			dBodySetLinearVel(body, velocity[0], velocity[1], velocity[2]);
			dBodySetAngularVel(body, spinvelocity[0], spinvelocity[1], spinvelocity[2]);
		}

		                                                  
		spinlimit = physics_ode_spinlimit.value;
		test = VectorLength2(ospinvelocity);
		if (test > spinlimit)
		{
			dBodySetAngularVel(body, 0, 0, 0);
		}

		                                  
		for(func = ed->priv.server->ode_func; func; func = nextf)
		{
			nextf = func->next;
			World_Physics_ApplyCmd(ed, func);
			Mem_Free(func);
		}
		ed->priv.server->ode_func = NULL;
	}
}

#define MAX_CONTACTS 32
static void nearCallback (void *data, dGeomID o1, dGeomID o2)
{
	world_t *world = (world_t *)data;
	prvm_prog_t *prog = world->prog;
	dContact contact[MAX_CONTACTS];                                   
	int b1enabled = 0, b2enabled = 0;
	dBodyID b1, b2;
	dJointID c;
	int i;
	int numcontacts;
	float bouncefactor1 = 0.0f;
	float bouncestop1 = 60.0f / 800.0f;
	float bouncefactor2 = 0.0f;
	float bouncestop2 = 60.0f / 800.0f;
	float erp;
	dVector3 grav;
	prvm_edict_t *ed1, *ed2;

	if (dGeomIsSpace(o1) || dGeomIsSpace(o2))
	{
		                                   
		dSpaceCollide2(o1, o2, data, &nearCallback);
		                                                            
		                       
		                                                               
		                                                               
		return;
	}

	b1 = dGeomGetBody(o1);
	if (b1)
		b1enabled = dBodyIsEnabled(b1);
	b2 = dGeomGetBody(o2);
	if (b2)
		b2enabled = dBodyIsEnabled(b2);

	                                                                                                   
	if (!b1enabled && !b2enabled)
		return;
	
	                                                                         
	if (b1 && b2 && dAreConnectedExcluding(b1, b2, dJointTypeContact))
		return;

	ed1 = (prvm_edict_t *) dGeomGetData(o1);
	if(ed1 && ed1->priv.server->free)
		ed1 = NULL;
	if(ed1)
	{
		bouncefactor1 = PRVM_gameedictfloat(ed1, bouncefactor);
		bouncestop1 = PRVM_gameedictfloat(ed1, bouncestop);
		if (!bouncestop1)
			bouncestop1 = 60.0f / 800.0f;
	}

	ed2 = (prvm_edict_t *) dGeomGetData(o2);
	if(ed2 && ed2->priv.server->free)
		ed2 = NULL;
	if(ed2)
	{
		bouncefactor2 = PRVM_gameedictfloat(ed2, bouncefactor);
		bouncestop2 = PRVM_gameedictfloat(ed2, bouncestop);
		if (!bouncestop2)
			bouncestop2 = 60.0f / 800.0f;
	}

	if(prog == SVVM_prog)
	{
		if(ed1 && PRVM_serveredictfunction(ed1, touch))
		{
			SV_LinkEdict_TouchAreaGrid_Call(ed1, ed2 ? ed2 : prog->edicts);
		}
		if(ed2 && PRVM_serveredictfunction(ed2, touch))
		{
			SV_LinkEdict_TouchAreaGrid_Call(ed2, ed1 ? ed1 : prog->edicts);
		}
	}

	                                       
	if(bouncefactor2 > 0)
	{
		if(bouncefactor1 > 0)
		{
			                                                          
			if(bouncestop2 < bouncestop1)
				bouncestop1 = bouncestop2;
			if(bouncefactor2 > bouncefactor1)
				bouncefactor1 = bouncefactor2;
		}
		else
		{
			bouncestop1 = bouncestop2;
			bouncefactor1 = bouncefactor2;
		}
	}
	dWorldGetGravity((dWorldID)world->physics.ode_world, grav);
	bouncestop1 *= fabs(grav[2]);

	          
	                                                   
	erp = (VectorLength2(PRVM_gameedictvector(ed1, velocity)) > VectorLength2(PRVM_gameedictvector(ed2, velocity))) ? PRVM_gameedictfloat(ed1, erp) : PRVM_gameedictfloat(ed2, erp);

	                                            
	numcontacts = (int)PRVM_gameedictfloat(ed1, maxcontacts);
	if (!numcontacts)
		numcontacts = physics_ode_contact_maxpoints.integer;
	if (PRVM_gameedictfloat(ed2, maxcontacts))
		numcontacts = max(numcontacts, (int)PRVM_gameedictfloat(ed2, maxcontacts));
	else
		numcontacts = max(numcontacts, physics_ode_contact_maxpoints.integer);

	                                                          
	numcontacts = dCollide(o1, o2, min(MAX_CONTACTS, numcontacts), &(contact[0].geom), sizeof(contact[0]));
	                                             
	for (i = 0;i < numcontacts;i++)
	{
		contact[i].surface.mode = (physics_ode_contact_mu.value != -1 ? dContactApprox1 : 0) | (physics_ode_contact_erp.value != -1 ? dContactSoftERP : 0) | (physics_ode_contact_cfm.value != -1 ? dContactSoftCFM : 0) | (bouncefactor1 > 0 ? dContactBounce : 0);
		contact[i].surface.mu = physics_ode_contact_mu.value * ed1->priv.server->ode_friction * ed2->priv.server->ode_friction;
		contact[i].surface.soft_erp = physics_ode_contact_erp.value + erp;
		contact[i].surface.soft_cfm = physics_ode_contact_cfm.value;
		contact[i].surface.bounce = bouncefactor1;
		contact[i].surface.bounce_vel = bouncestop1;
		c = dJointCreateContact((dWorldID)world->physics.ode_world, (dJointGroupID)world->physics.ode_contactgroup, contact + i);
		dJointAttach(c, b1, b2);
	}
}
#endif

void World_Physics_Frame(world_t *world, double frametime, double gravity)
{
#ifdef USEODE
	prvm_prog_t *prog = world->prog;
	double tdelta, tdelta2, tdelta3, simulationtime, collisiontime;

	tdelta = Sys_DirtyTime();
	if (world->physics.ode && physics_ode.integer)
	{
		int i;
		prvm_edict_t *ed;

		if (!physics_ode_constantstep.value)
		{
			world->physics.ode_iterations = bound(1, physics_ode_iterationsperframe.integer, 1000);
			world->physics.ode_step = frametime / world->physics.ode_iterations;
		}
		else
		{
			world->physics.ode_time += frametime;
			            
			if (physics_ode_constantstep.value > 0 && physics_ode_constantstep.value < 1)
				world->physics.ode_step = physics_ode_constantstep.value;
			else
				world->physics.ode_step = sys_ticrate.value;
			if (world->physics.ode_time > 0.2f)
				world->physics.ode_time = world->physics.ode_step;
			                                      
			world->physics.ode_iterations = 0;
			while(world->physics.ode_time >= world->physics.ode_step)
			{
				world->physics.ode_iterations++;
				world->physics.ode_time -= world->physics.ode_step;
			}
		}	
		world->physics.ode_movelimit = physics_ode_movelimit.value / world->physics.ode_step;
		World_Physics_UpdateODE(world);

		                                                          
		if (prog)
		{
			for (i = 0, ed = prog->edicts + i;i < prog->num_edicts;i++, ed++)
				if (!prog->edicts[i].priv.required->free)
					World_Physics_Frame_BodyFromEntity(world, ed);
			                                                          
			for (i = 0, ed = prog->edicts + i;i < prog->num_edicts;i++, ed++)
				if (!prog->edicts[i].priv.required->free)
					World_Physics_Frame_JointFromEntity(world, ed);
		}

		tdelta2 = Sys_DirtyTime();
		collisiontime = 0;
		for (i = 0;i < world->physics.ode_iterations;i++)
		{
			                  
			dWorldSetGravity((dWorldID)world->physics.ode_world, 0, 0, -gravity * physics_ode_world_gravitymod.value);
			                                             
			dWorldSetContactSurfaceLayer((dWorldID)world->physics.ode_world, max(0, physics_ode_contactsurfacelayer.value));
			                                                                  
			tdelta3 = Sys_DirtyTime();
			dSpaceCollide((dSpaceID)world->physics.ode_space, (void *)world, nearCallback);
			collisiontime += (Sys_DirtyTime() - tdelta3)*10000;
			               
			if (prog)
			{
				int j;
				for (j = 0, ed = prog->edicts + j;j < prog->num_edicts;j++, ed++)
					if (!prog->edicts[j].priv.required->free)
						World_Physics_Frame_ForceFromEntity(world, ed);
			}
			                                                       
			                                                                      
			dWorldSetQuickStepNumIterations((dWorldID)world->physics.ode_world, bound(1, physics_ode_worldstep_iterations.integer, 200));
			if (world->physics.ode_step > 0)
				dWorldQuickStep((dWorldID)world->physics.ode_world, world->physics.ode_step);
			                                                   
			dJointGroupEmpty((dJointGroupID)world->physics.ode_contactgroup);
		}
		simulationtime = (Sys_DirtyTime() - tdelta2)*10000;

		                                                                            
		if (prog)
		{
			for (i = 1, ed = prog->edicts + i;i < prog->num_edicts;i++, ed++)
				if (!prog->edicts[i].priv.required->free)
					World_Physics_Frame_BodyToEntity(world, ed);

			              
			if (physics_ode_printstats.integer)
			{
				dBodyID body;

				world->physics.ode_numobjects = 0;
				world->physics.ode_activeovjects = 0;
				for (i = 1, ed = prog->edicts + i;i < prog->num_edicts;i++, ed++)
				{
					if (prog->edicts[i].priv.required->free)
						continue;
					body = (dBodyID)prog->edicts[i].priv.server->ode_body;
					if (!body)
						continue;
					world->physics.ode_numobjects++;
					if (dBodyIsEnabled(body))
						world->physics.ode_activeovjects++;
				}
				Con_Printf("ODE Stats(%s): %i iterations, %3.01f (%3.01f collision) %3.01f total : %i objects %i active %i disabled\n", prog->name, world->physics.ode_iterations, simulationtime, collisiontime, (Sys_DirtyTime() - tdelta)*10000, world->physics.ode_numobjects, world->physics.ode_activeovjects, (world->physics.ode_numobjects - world->physics.ode_activeovjects));
			}
		}
	}
#endif
}
