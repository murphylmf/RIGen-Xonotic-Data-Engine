  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
                                         

#ifndef PROTOCOL_H
#define PROTOCOL_H

                                           

protocolversion_t Protocol_EnumForName(const char *s);
const char *Protocol_NameForEnum(protocolversion_t p);
protocolversion_t Protocol_EnumForNumber(int n);
int Protocol_NumberForEnum(protocolversion_t p);
void Protocol_Names(char *buffer, size_t buffersize);

                
#define	MF_ROCKET	1			                
#define	MF_GRENADE	2			                
#define	MF_GIB		4			                
#define	MF_ROTATE	8			                       
#define	MF_TRACER	16			                    
#define	MF_ZOMGIB	32			                    
#define	MF_TRACER2	64			                              
#define	MF_TRACER3	128			               

                 
#define	EF_BRIGHTFIELD			1
#define	EF_MUZZLEFLASH 			2
#define	EF_BRIGHTLIGHT 			4
#define	EF_DIMLIGHT 			8
#define	EF_NODRAW				16
#define EF_ADDITIVE				32
#define EF_BLUE					64
#define EF_RED					128
#define EF_NOGUNBOB				256			                                                                                                                                                                                                                                                                                                      
#define EF_FULLBRIGHT			512			                        
#define EF_FLAME				1024		                     
#define EF_STARDUST				2048		                              
#define EF_NOSHADOW				4096		                                    
#define EF_NODEPTHTEST			8192		                                 
#define EF_SELECTABLE			16384		                                                                  
#define EF_DOUBLESIDED			32768		                                          
#define EF_NOSELFSHADOW			65536		                                                                                      
#define EF_DYNAMICMODELLIGHT			131072
#define EF_UNUSED18				262144
#define EF_UNUSED19				524288
#define EF_RESTARTANIM_BIT		1048576                                                                                                                                     
#define EF_TELEPORT_BIT			2097152		                                                                                           
#define EF_LOWPRECISION			4194304		                                                                                                        
#define EF_NOMODELFLAGS			8388608		                                                                            
#define EF_ROCKET				16777216	                
#define EF_GRENADE				33554432	                
#define EF_GIB					67108864	                
#define EF_ROTATE				134217728	                       
#define EF_TRACER				268435456	                    
#define EF_ZOMGIB				536870912	                    
#define EF_TRACER2				1073741824	                              
#define EF_TRACER3				0x80000000	               

                                                   
#define INTEF_FLAG1QW				1
#define INTEF_FLAG2QW				2

                                         
#define PFLAGS_NOSHADOW			1
#define PFLAGS_CORONA			2
#define PFLAGS_FULLDYNAMIC		128                                               

                                                                               
#define U_MOREBITS		(1<<0)
#define U_ORIGIN1		(1<<1)
#define U_ORIGIN2		(1<<2)
#define U_ORIGIN3		(1<<3)
#define U_ANGLE2		(1<<4)
                                                                              
#define U_STEP			(1<<5)
#define U_FRAME			(1<<6)
                                         
#define U_SIGNAL		(1<<7)

#define U_ANGLE1		(1<<8)
#define U_ANGLE3		(1<<9)
#define U_MODEL			(1<<10)
#define U_COLORMAP		(1<<11)
#define U_SKIN			(1<<12)
#define U_EFFECTS		(1<<13)
#define U_LONGENTITY	(1<<14)

                                
#define U_EXTEND1		(1<<15)
                               
#define U_DELTA			(1<<16)                                                                                                                                                                                                                              
#define U_ALPHA			(1<<17)                                                                                                                                                     
#define U_SCALE			(1<<18)                                                
#define U_EFFECTS2		(1<<19)                                                   
#define U_GLOWSIZE		(1<<20)                                                          
#define U_GLOWCOLOR		(1<<21)                                                                                                                                                                                                                                     
#define U_COLORMOD		(1<<22)                                                                                                                                            
#define U_EXTEND2		(1<<23)                          
                                
#define U_GLOWTRAIL		(1<<24)                                                                                            
#define U_VIEWMODEL		(1<<25)                                                                                                                                                      
#define U_FRAME2		(1<<26)                                                 
#define U_MODEL2		(1<<27)                                                      
#define U_EXTERIORMODEL	(1<<28)                                                                                                                       
#define U_UNUSED29		(1<<29)                    
#define U_UNUSED30		(1<<30)                    
#define U_EXTEND3		(1<<31)                                            

#define	SU_VIEWHEIGHT	(1<<0)
#define	SU_IDEALPITCH	(1<<1)
#define	SU_PUNCH1		(1<<2)
#define	SU_PUNCH2		(1<<3)
#define	SU_PUNCH3		(1<<4)
#define	SU_VELOCITY1	(1<<5)
#define	SU_VELOCITY2	(1<<6)
#define	SU_VELOCITY3	(1<<7)
                                         
#define	SU_ITEMS		(1<<9)
#define	SU_ONGROUND		(1<<10)		                                 
#define	SU_INWATER		(1<<11)		                                 
#define	SU_WEAPONFRAME	(1<<12)
#define	SU_ARMOR		(1<<13)
#define	SU_WEAPON		(1<<14)
#define SU_EXTEND1		(1<<15)
                    
#define SU_PUNCHVEC1	(1<<16)
#define SU_PUNCHVEC2	(1<<17)
#define SU_PUNCHVEC3	(1<<18)
#define SU_VIEWZOOM		(1<<19)                                                
#define SU_UNUSED20		(1<<20)
#define SU_UNUSED21		(1<<21)
#define SU_UNUSED22		(1<<22)
#define SU_EXTEND2		(1<<23)                                            
                     
#define SU_UNUSED24		(1<<24)
#define SU_UNUSED25		(1<<25)
#define SU_UNUSED26		(1<<26)
#define SU_UNUSED27		(1<<27)
#define SU_UNUSED28		(1<<28)
#define SU_UNUSED29		(1<<29)
#define SU_UNUSED30		(1<<30)
#define SU_EXTEND3		(1<<31)                                            

                                                
#define	SND_VOLUME		(1<<0)		         
#define	SND_ATTENUATION	(1<<1)		         
#define	SND_LOOPING		(1<<2)		         
#define	SND_LARGEENTITY	(1<<3)		                                          
#define	SND_LARGESOUND	(1<<4)		                              
#define	SND_SPEEDUSHORT4000	(1<<5)		                                                                              


                                   
#define	DEFAULT_VIEWHEIGHT	22


                                
                                                  
#define	GAME_COOP			0
#define	GAME_DEATHMATCH		1

                    
                                                                
                                            
                    

  
                   
  
#define	svc_bad				0
#define	svc_nop				1
#define	svc_disconnect		2
#define	svc_updatestat		3	                
#define	svc_version			4	                        
#define	svc_setview			5	                        
#define	svc_sound			6	             
#define	svc_time			7	                      
#define	svc_print			8	                                  
#define	svc_stufftext		9	                                                
								                                     
#define	svc_setangle		10	                                                     

#define	svc_serverinfo		11	                 
						                         
						                           
						                             
#define	svc_lightstyle		12	                  
#define	svc_updatename		13	                  
#define	svc_updatefrags		14	                 
#define	svc_clientdata		15	                     
#define	svc_stopsound		16	             
#define	svc_updatecolors	17	                
#define	svc_particle		18	                    
#define	svc_damage			19

#define	svc_spawnstatic		20
                      
#define	svc_spawnbaseline	22

#define	svc_temp_entity		23

#define	svc_setpause		24	                  
#define	svc_signonnum		25	                                       

#define	svc_centerprint		26	                                          

#define	svc_killedmonster	27
#define	svc_foundsecret		28

#define	svc_spawnstaticsound	29	                                              

#define	svc_intermission	30		                 
#define	svc_finale			31		                               

#define	svc_cdtrack			32		                                
#define svc_sellscreen		33

#define svc_cutscene		34

#define	svc_showlmp			35		                                                             
#define	svc_hidelmp			36		                    
#define	svc_skybox			37		                   

                                  
#define svc_downloaddata	50		                           
#define svc_updatestatubyte	51		                           
#define svc_effect			52		                                                                                      
#define svc_effect2			53		                                                                                        
#define	svc_sound2			54		                                                               
#define	svc_precache		54		                                                                                                         
#define	svc_spawnbaseline2	55		                                   
#define svc_spawnstatic2	56		                                   
#define svc_entities		57		                                                                                   
#define svc_csqcentities	58		                                                                 
#define	svc_spawnstaticsound2	59	                                               
#define svc_trailparticles	60		                                                               
#define svc_pointparticles	61		                                                                   
#define svc_pointparticles1	62		                                                                                                      

  
                   
  
#define	clc_bad			0
#define	clc_nop 		1
#define	clc_disconnect	2
#define	clc_move		3			              
#define	clc_stringcmd	4		                   

                                  
#define clc_ackframe	50		                    
#define clc_ackdownloaddata	51	                                                                                                                                     
#define clc_unusedlh2 	52
#define clc_unusedlh3 	53
#define clc_unusedlh4 	54
#define clc_unusedlh5 	55
#define clc_unusedlh6 	56
#define clc_unusedlh7 	57
#define clc_unusedlh8 	58
#define clc_unusedlh9 	59

  
                     
  
#define	TE_SPIKE			0                   
#define	TE_SUPERSPIKE		1                   
#define	TE_GUNSHOT			2                   
#define	TE_EXPLOSION		3                   
#define	TE_TAREXPLOSION		4                   
#define	TE_LIGHTNING1		5                                               
#define	TE_LIGHTNING2		6                                               
#define	TE_WIZSPIKE			7                   
#define	TE_KNIGHTSPIKE		8                   
#define	TE_LIGHTNING3		9                                               
#define	TE_LAVASPLASH		10                   
#define	TE_TELEPORT			11                   
#define TE_EXPLOSION2		12                                                       

               
#define TE_BEAM				13                                               
               

                                                                                                                     
#define	TE_EXPLOSION3		16                                                          
#define TE_LIGHTNING4NEH	17                                                              

                                                   
#define	TE_BLOOD			50                                                                    
#define	TE_SPARK			51                                                                    
#define	TE_BLOODSHOWER		52                                                                  
#define	TE_EXPLOSIONRGB		53                                                       
#define TE_PARTICLECUBE		54                                                                                                      
#define TE_PARTICLERAIN		55                                                                     
#define TE_PARTICLESNOW		56                                                                     
#define TE_GUNSHOTQUAD		57                   
#define TE_SPIKEQUAD		58                   
#define TE_SUPERSPIKEQUAD	59                   
                            
#define TE_EXPLOSIONQUAD	70                   
#define	TE_UNUSED1			71          
#define TE_SMALLFLASH		72                   
#define TE_CUSTOMFLASH		73                                                                                                       
#define TE_FLAMEJET			74                                                  
#define TE_PLASMABURN		75                   
                                     
#define TE_TEI_G3			76                                               
#define TE_TEI_SMOKE		77                                             
#define TE_TEI_BIGEXPLOSION	78                   
#define TE_TEI_PLASMAHIT	79                                             


                                                             
#define RENDER_STEP 1
#define RENDER_GLOWTRAIL 2
#define RENDER_VIEWMODEL 4
#define RENDER_EXTERIORMODEL 8
#define RENDER_LOWPRECISION 16                                                       
#define RENDER_COLORMAPPED 32
#define RENDER_WORLDOBJECT 64                                               
#define RENDER_COMPLEXANIMATION 128

#define RENDER_SHADOW 65536               
#define RENDER_LIGHT 131072                 
#define RENDER_NOSELFSHADOW 262144                                                                              
                                                                                                                                                                   
#define RENDER_EQUALIZE 524288                                                                                                                                  
#define RENDER_NODEPTHTEST 1048576
#define RENDER_ADDITIVE 2097152
#define RENDER_DOUBLESIDED 4194304
#define RENDER_CUSTOMIZEDMODELLIGHT 4096
#define RENDER_DYNAMICMODELLIGHT 8388608                                

#define MAX_FRAMEGROUPBLENDS 4
typedef struct framegroupblend_s
{
	                                    
	                                             
	int frame;
	float lerp;
	                                                       
	double start;
}
framegroupblend_t;

struct matrix4x4_s;
struct model_s;

typedef struct skeleton_s
{
	const struct model_s *model;
	struct matrix4x4_s *relativetransforms;
}
skeleton_t;

typedef enum entity_state_active_e
{
	ACTIVE_NOT = 0,
	ACTIVE_NETWORK = 1,
	ACTIVE_SHARED = 2
}
entity_state_active_t;

                                                                
typedef struct entity_state_s
{
	                                     
	double time;                                                                  
	float netcenter[3];                                                                                                           
	float origin[3];
	float angles[3];
	int effects;
	unsigned int customizeentityforclient;     
	unsigned short number;                                   
	unsigned short modelindex;
	unsigned short frame;
	unsigned short tagentity;
	unsigned short specialvisibilityradius;                                    
	unsigned short viewmodelforclient;     
	unsigned short exteriormodelforclient;                                                                                  
	unsigned short nodrawtoclient;     
	unsigned short drawonlytoclient;     
	unsigned short traileffectnum;
	unsigned short light[4];                                             
	unsigned char active;                         
	unsigned char lightstyle;
	unsigned char lightpflags;
	unsigned char colormap;
	unsigned char skin;                                                                              
	unsigned char alpha;
	unsigned char scale;
	unsigned char glowsize;
	unsigned char glowcolor;
	unsigned char flags;
	unsigned char internaleffects;                           
	unsigned char tagindex;
	unsigned char colormod[3];
	unsigned char glowmod[3];
	                                   
	framegroupblend_t framegroupblend[4];
	skeleton_t skeletonobject;
}
entity_state_t;

                        
extern entity_state_t defaultstate;
                                               
void EntityFrameQuake_ReadEntity(int bits);
                                                                              
                                          
void Protocol_UpdateClientStats(const int *stats);
                                                                     
                                                                              
                                
void Protocol_WriteStatsReliable(void);
                                                        
                        
qboolean EntityFrameQuake_WriteFrame(sizebuf_t *msg, int maxsize, int numstates, const entity_state_t **states);
                                                                                            
void EntityFrameQuake_ISeeDeadEntities(void);

  
                    
                                                               

                                                                       
                              

                                                                              
                    

                                                 
                                                                              
                                                                          
                                                                              
                    
                                                                    
                                                                            
                                              
                                                                    

                                                 
                                                                              
                                                               
                                                       
                                                                            
                                          
                                                          

                                                                     
                                         
  

  
                    
                                                                                                                                           

                                                                                                   

                                                 
                                                                                                                                                   

                               
                                        
                                                                                                                                                                                            
                                                                
                                           
                                                                                 
                                              
          





                                                                                                                             
  

#define MAX_ENTITY_HISTORY 64
#define MAX_ENTITY_DATABASE (MAX_EDICTS * 2)

                                                                    
typedef struct entity_frame_s
{
	double time;
	int framenum;
	int numentities;
	int firstentitynum;
	int lastentitynum;
	vec3_t eye;
	entity_state_t entitydata[MAX_ENTITY_DATABASE];
}
entity_frame_t;

typedef struct entity_frameinfo_s
{
	double time;
	int framenum;
	int firstentity;                                                     
	int endentity;                                                    
}
entity_frameinfo_t;

typedef struct entityframe_database_s
{
	                                                                                                             
	                                                                                                          
	                                                                                             
	                                    
	                                                                                                                                          
	                       
	                                                             
	                                                                                         
	int numframes;
	                               
	int latestframenum;
	                                       
	int ackframenum;
	                                    
	vec3_t eye;
	                                             
	entity_frameinfo_t frames[MAX_ENTITY_HISTORY];
	           
	entity_state_t entitydata[MAX_ENTITY_DATABASE];

	                                                   
	entity_frame_t deltaframe;
	entity_frame_t framedata;
}
entityframe_database_t;

                                                                            
                                                           

                                                                           
                                                           

                                                                       
#define E_ORIGIN1		(1<<0)
#define E_ORIGIN2		(1<<1)
#define E_ORIGIN3		(1<<2)
#define E_ANGLE1		(1<<3)
#define E_ANGLE2		(1<<4)
#define E_ANGLE3		(1<<5)
#define E_MODEL1		(1<<6)
#define E_EXTEND1		(1<<7)

                                     
#define E_FRAME1		(1<<8)
#define E_EFFECTS1		(1<<9)
#define E_ALPHA			(1<<10)
#define E_SCALE			(1<<11)
#define E_COLORMAP		(1<<12)
#define E_SKIN			(1<<13)
#define E_FLAGS			(1<<14)
#define E_EXTEND2		(1<<15)

                                                  
#define E_FRAME2		(1<<16)
#define E_MODEL2		(1<<17)
#define E_EFFECTS2		(1<<18)
#define E_GLOWSIZE		(1<<19)
#define E_GLOWCOLOR		(1<<20)
#define E_LIGHT			(1<<21)
#define E_LIGHTPFLAGS	(1<<22)
#define E_EXTEND3		(1<<23)

#define E_SOUND1		(1<<24)
#define E_SOUNDVOL		(1<<25)
#define E_SOUNDATTEN	(1<<26)
#define E_TAGATTACHMENT	(1<<27)
#define E_LIGHTSTYLE	(1<<28)
#define E_UNUSED6		(1<<29)
#define E_UNUSED7		(1<<30)
#define E_EXTEND4		(1<<31)

                                                    
int EntityState_DeltaBits(const entity_state_t *o, const entity_state_t *n);
                          
void EntityState_WriteExtendBits(sizebuf_t *msg, unsigned int bits);
                                                  
void EntityState_WriteFields(const entity_state_t *ent, sizebuf_t *msg, unsigned int bits);
                                                                                                                 
void EntityState_WriteUpdate(const entity_state_t *ent, sizebuf_t *msg, const entity_state_t *delta);
                
int EntityState_ReadExtendBits(void);
                                                              
void EntityState_ReadFields(entity_state_t *e, unsigned int bits);

                                                     
entityframe_database_t *EntityFrame_AllocDatabase(mempool_t *mempool);
                                         
void EntityFrame_FreeDatabase(entityframe_database_t *d);
                                                                            
                              
void EntityFrame_ClearDatabase(entityframe_database_t *d);
                                                                      
void EntityFrame_AckFrame(entityframe_database_t *d, int frame);
                                                        
void EntityFrame_Clear(entity_frame_t *f, vec3_t eye, int framenum);
                                                      
void EntityFrame_FetchFrame(entityframe_database_t *d, int framenum, entity_frame_t *f);
                                                                     
void EntityFrame_AddFrame_Client(entityframe_database_t *d, vec3_t eye, int framenum, int numentities, const entity_state_t *entitydata);
                                                                     
void EntityFrame_AddFrame_Server(entityframe_database_t *d, vec3_t eye, int framenum, int numentities, const entity_state_t **entitydata);
                                            
qboolean EntityFrame_WriteFrame(sizebuf_t *msg, int maxsize, entityframe_database_t *d, int numstates, const entity_state_t **states, int viewentnum);
                                             
void EntityFrame_CL_ReadFrame(void);
                                                                      
int EntityFrame_MostRecentlyRecievedFrameNum(entityframe_database_t *d);

typedef struct entity_database4_commit_s
{
	                                      
	int framenum;
	                                       
	int numentities;
	                                                                  
	int maxentities;
	entity_state_t *entity;
}
entity_database4_commit_t;

typedef struct entity_database4_s
{
	                                      
	mempool_t *mempool;
	                  
	int referenceframenum;
	                                                          
	int maxreferenceentities;
	                                                                                                
	entity_state_t *referenceentity;
	                                                                         
	                                                  
	entity_database4_commit_t commit[MAX_ENTITY_HISTORY];
	                                                   
	entity_database4_commit_t *currentcommit;
	                                                                       
	                 
	int currententitynumber;
	                
	int latestframenumber;
}
entityframe4_database_t;

                                          
entity_state_t *EntityFrame4_GetReferenceEntity(entityframe4_database_t *d, int number);
void EntityFrame4_AddCommitEntity(entityframe4_database_t *d, const entity_state_t *s);

                      
entityframe4_database_t *EntityFrame4_AllocDatabase(mempool_t *pool);
                  
void EntityFrame4_FreeDatabase(entityframe4_database_t *d);
                                                                         
void EntityFrame4_ResetDatabase(entityframe4_database_t *d);
                                                                  
int EntityFrame4_AckFrame(entityframe4_database_t *d, int framenum, int servermode);
                                       
qboolean EntityFrame4_WriteFrame(sizebuf_t *msg, int maxsize, entityframe4_database_t *d, int numstates, const entity_state_t **states);
                                        
void EntityFrame4_CL_ReadFrame(void);

                                                             
#define E5_FULLUPDATE (1<<0)
                                                                                 
                                                                     
#define E5_ORIGIN (1<<1)
                                                                                                     
                                                                                                            
#define E5_ANGLES (1<<2)
                                     
                                      
#define E5_MODEL (1<<3)
                                
                                 
#define E5_FRAME (1<<4)
                 
#define E5_SKIN (1<<5)
                                                      
                                                       
                                                     
                                                     
#define E5_EFFECTS (1<<6)
                 
#define E5_EXTEND1 (1<<7)

                        
#define E5_FLAGS (1<<8)
                                       
#define E5_ALPHA (1<<9)
                                      
#define E5_SCALE (1<<10)
       
#define E5_ORIGIN32 (1<<11)
       
#define E5_ANGLES16 (1<<12)
       
#define E5_MODEL16 (1<<13)
                     
#define E5_COLORMAP (1<<14)
                  
#define E5_EXTEND2 (1<<15)

                       
                     
#define E5_ATTACHMENT (1<<16)
                                                                
                       
                        
#define E5_LIGHT (1<<17)
                     
                      
#define E5_GLOW (1<<18)
                     
#define E5_EFFECTS16 (1<<19)
                   
#define E5_EFFECTS32 (1<<20)
       
#define E5_FRAME16 (1<<21)
                                                           
#define E5_COLORMOD (1<<22)
                  
#define E5_EXTEND3 (1<<23)

                                                        
#define E5_GLOWMOD (1<<24)
                                             
                                                           
                                                           
                                                           
                                                               
                                   
#define E5_COMPLEXANIMATION (1<<25)
                        
#define E5_TRAILEFFECTNUM (1<<26)
         
#define E5_UNUSED27 (1<<27)
         
#define E5_UNUSED28 (1<<28)
         
#define E5_UNUSED29 (1<<29)
         
#define E5_UNUSED30 (1<<30)
            
#define E5_EXTEND4 (1<<31)

#define ENTITYFRAME5_MAXPACKETLOGS 64
#define ENTITYFRAME5_MAXSTATES 1024
#define ENTITYFRAME5_PRIORITYLEVELS 32

typedef struct entityframe5_changestate_s
{
	unsigned int number;
	unsigned int bits;
}
entityframe5_changestate_t;

typedef struct entityframe5_packetlog_s
{
	int packetnumber;
	int numstates;
	entityframe5_changestate_t states[ENTITYFRAME5_MAXSTATES];
	unsigned char statsdeltabits[(MAX_CL_STATS+7)/8];
}
entityframe5_packetlog_t;

typedef struct entityframe5_database_s
{
	                                              
	int latestframenum;
	                                         
	int viewentnum;

	                                                                
	entityframe5_packetlog_t packetlog[ENTITYFRAME5_MAXPACKETLOGS];

	                                                                     
	int maxedicts;

	                                                               
	int *deltabits;               
	                                                             
	                           
	unsigned char *priorities;               
	                                                        
	int *updateframenum;               

	                                             
	entity_state_t *states;               
	                                      
	                                                           
	                        
	unsigned char *visiblebits;                     

	            

	                                                              
	                       
	                                           

	                                                            
	                                                                       
	                                                                          
	                                                       
	                      
	                                                      

	                                     
	int prioritychaincounts[ENTITYFRAME5_PRIORITYLEVELS];
	unsigned short prioritychains[ENTITYFRAME5_PRIORITYLEVELS][ENTITYFRAME5_MAXSTATES];
}
entityframe5_database_t;

entityframe5_database_t *EntityFrame5_AllocDatabase(mempool_t *pool);
void EntityFrame5_FreeDatabase(entityframe5_database_t *d);
void EntityState5_WriteUpdate(int number, const entity_state_t *s, int changedbits, sizebuf_t *msg);
int EntityState5_DeltaBitsForState(entity_state_t *o, entity_state_t *n);
void EntityFrame5_CL_ReadFrame(void);
void EntityFrame5_LostFrame(entityframe5_database_t *d, int framenum);
void EntityFrame5_AckFrame(entityframe5_database_t *d, int framenum);
qboolean EntityFrame5_WriteFrame(sizebuf_t *msg, int maxsize, entityframe5_database_t *d, int numstates, const entity_state_t **states, int viewentnum, unsigned int movesequence, qboolean need_empty);

extern cvar_t developer_networkentities;

             
                   
#define qw_svc_bad				0
#define qw_svc_nop				1
#define qw_svc_disconnect		2
#define qw_svc_updatestat		3	                
#define qw_svc_setview			5	                        
#define qw_svc_sound			6	             
#define qw_svc_print			8	                                            
#define qw_svc_stufftext		9	                                                
#define qw_svc_setangle			10	                                                     
#define qw_svc_serverdata		11	                      
#define qw_svc_lightstyle		12	                  
#define qw_svc_updatefrags		14	                 
#define qw_svc_stopsound		16	             
#define qw_svc_damage			19
#define qw_svc_spawnstatic		20
#define qw_svc_spawnbaseline	22
#define qw_svc_temp_entity		23	           
#define qw_svc_setpause			24	                  
#define qw_svc_centerprint		26	                                          
#define qw_svc_killedmonster	27
#define qw_svc_foundsecret		28
#define qw_svc_spawnstaticsound	29	                                              
#define qw_svc_intermission		30		                                 
#define qw_svc_finale			31		                
#define qw_svc_cdtrack			32		               
#define qw_svc_sellscreen		33
#define qw_svc_smallkick		34		                             
#define qw_svc_bigkick			35		                             
#define qw_svc_updateping		36		                 
#define qw_svc_updateentertime	37		                 
#define qw_svc_updatestatlong	38		                
#define qw_svc_muzzleflash		39		                 
#define qw_svc_updateuserinfo	40		                         
#define qw_svc_download			41		                            
#define qw_svc_playerinfo		42		           
#define qw_svc_nails			43		                                          
#define qw_svc_chokecount		44		                        
#define qw_svc_modellist		45		            
#define qw_svc_soundlist		46		            
#define qw_svc_packetentities	47		        
#define qw_svc_deltapacketentities	48		        
#define qw_svc_maxspeed			49		                                  
#define qw_svc_entgravity		50		                                 
#define qw_svc_setinfo			51		                      
#define qw_svc_serverinfo		52		             
#define qw_svc_updatepl			53		                
             
                   
#define qw_clc_bad			0
#define qw_clc_nop			1
#define qw_clc_move			3		               
#define qw_clc_stringcmd	4		                   
#define qw_clc_delta		5		                                                                
#define qw_clc_tmove		6		                                   
#define qw_clc_upload		7		                                   
             
                               
                                                                      
#define	QW_PF_MSEC			(1<<0)
#define	QW_PF_COMMAND		(1<<1)
#define	QW_PF_VELOCITY1	(1<<2)
#define	QW_PF_VELOCITY2	(1<<3)
#define	QW_PF_VELOCITY3	(1<<4)
#define	QW_PF_MODEL		(1<<5)
#define	QW_PF_SKINNUM		(1<<6)
#define	QW_PF_EFFECTS		(1<<7)
#define	QW_PF_WEAPONFRAME	(1<<8)		                            
#define	QW_PF_DEAD			(1<<9)		                                
#define	QW_PF_GIB			(1<<10)		                                     
#define	QW_PF_NOGRAV		(1<<11)		                                     
             
                                                                        
                       
                                                          
#define QW_CM_ANGLE1 	(1<<0)
#define QW_CM_ANGLE3 	(1<<1)
#define QW_CM_FORWARD	(1<<2)
#define QW_CM_SIDE		(1<<3)
#define QW_CM_UP		(1<<4)
#define QW_CM_BUTTONS	(1<<5)
#define QW_CM_IMPULSE	(1<<6)
#define QW_CM_ANGLE2 	(1<<7)
             
                                                            
                                       
#define QW_U_ORIGIN1	(1<<9)
#define QW_U_ORIGIN2	(1<<10)
#define QW_U_ORIGIN3	(1<<11)
#define QW_U_ANGLE2		(1<<12)
#define QW_U_FRAME		(1<<13)
#define QW_U_REMOVE		(1<<14)		                                   
#define QW_U_MOREBITS	(1<<15)
                                                              
#define QW_U_ANGLE1		(1<<0)
#define QW_U_ANGLE3		(1<<1)
#define QW_U_MODEL		(1<<2)
#define QW_U_COLORMAP	(1<<3)
#define QW_U_SKIN		(1<<4)
#define QW_U_EFFECTS	(1<<5)
#define QW_U_SOLID		(1<<6)		                                            
             
                     
#define QW_TE_SPIKE				0
#define QW_TE_SUPERSPIKE		1
#define QW_TE_GUNSHOT			2
#define QW_TE_EXPLOSION			3
#define QW_TE_TAREXPLOSION		4
#define QW_TE_LIGHTNING1		5
#define QW_TE_LIGHTNING2		6
#define QW_TE_WIZSPIKE			7
#define QW_TE_KNIGHTSPIKE		8
#define QW_TE_LIGHTNING3		9
#define QW_TE_LAVASPLASH		10
#define QW_TE_TELEPORT			11
#define QW_TE_BLOOD				12
#define QW_TE_LIGHTNINGBLOOD	13
             
               
#define QW_EF_BRIGHTFIELD		1
#define QW_EF_MUZZLEFLASH 		2
#define QW_EF_BRIGHTLIGHT 		4
#define QW_EF_DIMLIGHT 			8
#define QW_EF_FLAG1	 			16
#define QW_EF_FLAG2	 			32
#define QW_EF_BLUE				64
#define QW_EF_RED				128

#define QW_UPDATE_BACKUP 64
#define QW_UPDATE_MASK (QW_UPDATE_BACKUP - 1)
#define QW_MAX_PACKET_ENTITIES 64

                                                 
                                                      
                                                                               
#define QW_STAT_HEALTH			0
                           
#define QW_STAT_WEAPON			2
#define QW_STAT_AMMO			3
#define QW_STAT_ARMOR			4
                                
#define QW_STAT_SHELLS			6
#define QW_STAT_NAILS			7
#define QW_STAT_ROCKETS			8
#define QW_STAT_CELLS			9
#define QW_STAT_ACTIVEWEAPON	10
#define QW_STAT_TOTALSECRETS	11
#define QW_STAT_TOTALMONSTERS	12
#define QW_STAT_SECRETS			13                                            
#define QW_STAT_MONSTERS		14                               
#define QW_STAT_ITEMS			15
                                

                                                                    
typedef struct entityframeqw_snapshot_s
{
	double time;
	qboolean invalid;
	int num_entities;
	entity_state_t entities[QW_MAX_PACKET_ENTITIES];
}
entityframeqw_snapshot_t;

typedef struct entityframeqw_database_s
{
	entityframeqw_snapshot_t snapshot[QW_UPDATE_BACKUP];
}
entityframeqw_database_t;

entityframeqw_database_t *EntityFrameQW_AllocDatabase(mempool_t *pool);
void EntityFrameQW_FreeDatabase(entityframeqw_database_t *d);
void EntityStateQW_ReadPlayerUpdate(void);
void EntityFrameQW_CL_ReadFrame(qboolean delta);

struct client_s;
void EntityFrameCSQC_LostFrame(struct client_s *client, int framenum);
qboolean EntityFrameCSQC_WriteFrame (sizebuf_t *msg, int maxsize, int numnumbers, const unsigned short *numbers, int framenum);

#endif

