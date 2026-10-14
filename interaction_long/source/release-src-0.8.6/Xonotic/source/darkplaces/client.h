  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
           

#ifndef CLIENT_H
#define CLIENT_H

#include "matrixlib.h"
#include "snd_main.h"

                                               
typedef enum r_stat_e
{
	r_stat_timedelta,
	r_stat_quality,
	r_stat_renders,
	r_stat_entities,
	r_stat_entities_surfaces,
	r_stat_entities_triangles,
	r_stat_world_leafs,
	r_stat_world_portals,
	r_stat_world_surfaces,
	r_stat_world_triangles,
	r_stat_lightmapupdates,
	r_stat_lightmapupdatepixels,
	r_stat_particles,
	r_stat_drawndecals,
	r_stat_totaldecals,
	r_stat_draws,
	r_stat_draws_vertices,
	r_stat_draws_elements,
	r_stat_lights,
	r_stat_lights_clears,
	r_stat_lights_scissored,
	r_stat_lights_lighttriangles,
	r_stat_lights_shadowtriangles,
	r_stat_lights_dynamicshadowtriangles,
	r_stat_bouncegrid_lights,
	r_stat_bouncegrid_particles,
	r_stat_bouncegrid_traces,
	r_stat_bouncegrid_hits,
	r_stat_bouncegrid_splats,
	r_stat_bouncegrid_bounces,
	r_stat_photoncache_animated,
	r_stat_photoncache_cached,
	r_stat_photoncache_traced,
	r_stat_bloom,
	r_stat_bloom_copypixels,
	r_stat_bloom_drawpixels,
	r_stat_indexbufferuploadcount,
	r_stat_indexbufferuploadsize,
	r_stat_vertexbufferuploadcount,
	r_stat_vertexbufferuploadsize,
	r_stat_framedatacurrent,
	r_stat_framedatasize,
	r_stat_bufferdatacurrent_vertex,                                               
	r_stat_bufferdatacurrent_index16,
	r_stat_bufferdatacurrent_index32,
	r_stat_bufferdatacurrent_uniform,
	r_stat_bufferdatasize_vertex,                                               
	r_stat_bufferdatasize_index16,
	r_stat_bufferdatasize_index32,
	r_stat_bufferdatasize_uniform,
	r_stat_animcache_vertexmesh_count,
	r_stat_animcache_vertexmesh_vertices,
	r_stat_animcache_vertexmesh_maxvertices,
	r_stat_animcache_skeletal_count,
	r_stat_animcache_skeletal_bones,
	r_stat_animcache_skeletal_maxbones,
	r_stat_animcache_shade_count,
	r_stat_animcache_shade_vertices,
	r_stat_animcache_shade_maxvertices,
	r_stat_animcache_shape_count,
	r_stat_animcache_shape_vertices,
	r_stat_animcache_shape_maxvertices,
	r_stat_batch_batches,
	r_stat_batch_withgaps,
	r_stat_batch_surfaces,
	r_stat_batch_vertices,
	r_stat_batch_triangles,
	r_stat_batch_fast_batches,
	r_stat_batch_fast_surfaces,
	r_stat_batch_fast_vertices,
	r_stat_batch_fast_triangles,
	r_stat_batch_copytriangles_batches,
	r_stat_batch_copytriangles_surfaces,
	r_stat_batch_copytriangles_vertices,
	r_stat_batch_copytriangles_triangles,
	r_stat_batch_dynamic_batches,
	r_stat_batch_dynamic_surfaces,
	r_stat_batch_dynamic_vertices,
	r_stat_batch_dynamic_triangles,
	r_stat_batch_dynamicskeletal_batches,
	r_stat_batch_dynamicskeletal_surfaces,
	r_stat_batch_dynamicskeletal_vertices,
	r_stat_batch_dynamicskeletal_triangles,
	r_stat_batch_dynamic_batches_because_cvar,
	r_stat_batch_dynamic_surfaces_because_cvar,
	r_stat_batch_dynamic_vertices_because_cvar,
	r_stat_batch_dynamic_triangles_because_cvar,
	r_stat_batch_dynamic_batches_because_lightmapvertex,
	r_stat_batch_dynamic_surfaces_because_lightmapvertex,
	r_stat_batch_dynamic_vertices_because_lightmapvertex,
	r_stat_batch_dynamic_triangles_because_lightmapvertex,
	r_stat_batch_dynamic_batches_because_deformvertexes_autosprite,
	r_stat_batch_dynamic_surfaces_because_deformvertexes_autosprite,
	r_stat_batch_dynamic_vertices_because_deformvertexes_autosprite,
	r_stat_batch_dynamic_triangles_because_deformvertexes_autosprite,
	r_stat_batch_dynamic_batches_because_deformvertexes_autosprite2,
	r_stat_batch_dynamic_surfaces_because_deformvertexes_autosprite2,
	r_stat_batch_dynamic_vertices_because_deformvertexes_autosprite2,
	r_stat_batch_dynamic_triangles_because_deformvertexes_autosprite2,
	r_stat_batch_dynamic_batches_because_deformvertexes_normal,
	r_stat_batch_dynamic_surfaces_because_deformvertexes_normal,
	r_stat_batch_dynamic_vertices_because_deformvertexes_normal,
	r_stat_batch_dynamic_triangles_because_deformvertexes_normal,
	r_stat_batch_dynamic_batches_because_deformvertexes_wave,
	r_stat_batch_dynamic_surfaces_because_deformvertexes_wave,
	r_stat_batch_dynamic_vertices_because_deformvertexes_wave,
	r_stat_batch_dynamic_triangles_because_deformvertexes_wave,
	r_stat_batch_dynamic_batches_because_deformvertexes_bulge,
	r_stat_batch_dynamic_surfaces_because_deformvertexes_bulge,
	r_stat_batch_dynamic_vertices_because_deformvertexes_bulge,
	r_stat_batch_dynamic_triangles_because_deformvertexes_bulge,
	r_stat_batch_dynamic_batches_because_deformvertexes_move,
	r_stat_batch_dynamic_surfaces_because_deformvertexes_move,
	r_stat_batch_dynamic_vertices_because_deformvertexes_move,
	r_stat_batch_dynamic_triangles_because_deformvertexes_move,
	r_stat_batch_dynamic_batches_because_tcgen_lightmap,
	r_stat_batch_dynamic_surfaces_because_tcgen_lightmap,
	r_stat_batch_dynamic_vertices_because_tcgen_lightmap,
	r_stat_batch_dynamic_triangles_because_tcgen_lightmap,
	r_stat_batch_dynamic_batches_because_tcgen_vector,
	r_stat_batch_dynamic_surfaces_because_tcgen_vector,
	r_stat_batch_dynamic_vertices_because_tcgen_vector,
	r_stat_batch_dynamic_triangles_because_tcgen_vector,
	r_stat_batch_dynamic_batches_because_tcgen_environment,
	r_stat_batch_dynamic_surfaces_because_tcgen_environment,
	r_stat_batch_dynamic_vertices_because_tcgen_environment,
	r_stat_batch_dynamic_triangles_because_tcgen_environment,
	r_stat_batch_dynamic_batches_because_tcmod_turbulent,
	r_stat_batch_dynamic_surfaces_because_tcmod_turbulent,
	r_stat_batch_dynamic_vertices_because_tcmod_turbulent,
	r_stat_batch_dynamic_triangles_because_tcmod_turbulent,
	r_stat_batch_dynamic_batches_because_interleavedarrays,
	r_stat_batch_dynamic_surfaces_because_interleavedarrays,
	r_stat_batch_dynamic_vertices_because_interleavedarrays,
	r_stat_batch_dynamic_triangles_because_interleavedarrays,
	r_stat_batch_dynamic_batches_because_nogaps,
	r_stat_batch_dynamic_surfaces_because_nogaps,
	r_stat_batch_dynamic_vertices_because_nogaps,
	r_stat_batch_dynamic_triangles_because_nogaps,
	r_stat_batch_dynamic_batches_because_derived,
	r_stat_batch_dynamic_surfaces_because_derived,
	r_stat_batch_dynamic_vertices_because_derived,
	r_stat_batch_dynamic_triangles_because_derived,
	r_stat_batch_entitycache_count,
	r_stat_batch_entitycache_surfaces,
	r_stat_batch_entitycache_vertices,
	r_stat_batch_entitycache_triangles,
	r_stat_batch_entityanimate_count,
	r_stat_batch_entityanimate_surfaces,
	r_stat_batch_entityanimate_vertices,
	r_stat_batch_entityanimate_triangles,
	r_stat_batch_entityskeletal_count,
	r_stat_batch_entityskeletal_surfaces,
	r_stat_batch_entityskeletal_vertices,
	r_stat_batch_entityskeletal_triangles,
	r_stat_batch_entitystatic_count,
	r_stat_batch_entitystatic_surfaces,
	r_stat_batch_entitystatic_vertices,
	r_stat_batch_entitystatic_triangles,
	r_stat_batch_entitycustom_count,
	r_stat_batch_entitycustom_surfaces,
	r_stat_batch_entitycustom_vertices,
	r_stat_batch_entitycustom_triangles,
	r_stat_count                 
}
r_stat_t;

                              
#define LIGHTFLAG_NORMALMODE 1
#define LIGHTFLAG_REALTIMEMODE 2

typedef struct tridecal_s
{
	                                
	float			texcoord2f[3][2];
	float			vertex3f[3][3];
	float			color4f[3][4];
	float			plane[4];                    
	                                                                                  
	float			lived;
	                                                                      
	int				triangleindex;
	                         
	int				surfaceindex;
	                                              
	unsigned int	decalsequence;
}
tridecal_t;

typedef struct decalsystem_s
{
	dp_model_t *model;
	double lastupdatetime;
	int maxdecals;
	int freedecal;
	int numdecals;
	tridecal_t *decals;
	float *vertex3f;
	float *texcoord2f;
	float *color4f;
	int *element3i;
	unsigned short *element3s;
}
decalsystem_t;

typedef struct effect_s
{
	int active;
	vec3_t origin;
	double starttime;
	float framerate;
	int modelindex;
	int startframe;
	int endframe;
	                              
	int frame;
	double frame1time;
	double frame2time;
}
cl_effect_t;

typedef struct beam_s
{
	int		entity;
	                                               
	int		lightning;
	struct model_s	*model;
	float	endtime;
	vec3_t	start, end;
}
beam_t;

typedef struct rtlight_particle_s
{
	float origin[3];
	float color[3];
}
rtlight_particle_t;

typedef struct rtlight_s
{
	                                                                                                                               

	                                                                                      

	                  
	                                                                         
	matrix4x4_t matrix_lighttoworld;
	                                                                         
	matrix4x4_t matrix_worldtolight;
	                                                              
	vec3_t color;
	                               
	vec_t radius;
	                
	char cubemapname[64];
	                                         
	int style;
	                                                                                                 
	int shadow;
	                                 
	vec_t corona;
	                                                                     
	vec_t coronasizescale;
	                               
	vec_t ambientscale;
	                               
	vec_t diffusescale;
	                                
	vec_t specularscale;
	                     
	int flags;

	                       
	                                
	vec3_t shadoworigin;
	           
	vec3_t cullmins;
	vec3_t cullmaxs;
	                                                                                      
	double trace_timer;

	                                                              
	                                             
	vec3_t currentcolor;
	                                                  
	float corona_visibility;
	unsigned int corona_queryindex_visiblepixels;
	unsigned int corona_queryindex_allpixels;
	                                              
	rtexture_t *currentcubemap;
	                                                                                    
	qboolean draw;
	                                                                                               
	qboolean castshadows;
	                                                                   
	int cached_numlightentities;
	int cached_numlightentities_noselfshadow;
	int cached_numshadowentities;
	int cached_numshadowentities_noselfshadow;
	int cached_numsurfaces;
	struct entity_render_s **cached_lightentities;
	struct entity_render_s **cached_lightentities_noselfshadow;
	struct entity_render_s **cached_shadowentities;
	struct entity_render_s **cached_shadowentities_noselfshadow;
	unsigned char *cached_shadowtrispvs;
	unsigned char *cached_lighttrispvs;
	int *cached_surfacelist;
	                                          
	vec3_t cached_cullmins;
	vec3_t cached_cullmaxs;
	                                                     
	                                                                       
	                                                      
	int cached_numfrustumplanes;
	mplane_t cached_frustumplanes[5];                                                 

	                     
	                                                           
	int isstatic;
	                                                                        
	int compiled;
	                                                 
	int shadowmode;
	                                                                                        
	int shadowmapsidesize;
	                                                 
	int shadowmapatlasposition[2];
	                                                                                                                                                                                                               
	int shadowmapatlassidesize;
	                                                     
	shadowmesh_t *static_meshchain_shadow_zpass;
	shadowmesh_t *static_meshchain_shadow_zfail;
	shadowmesh_t *static_meshchain_shadow_shadowmap;
	                                                      
	int static_numleafs;
	int static_numleafpvsbytes;
	int *static_leaflist;
	unsigned char *static_leafpvs;
	                          
	int static_numsurfaces;
	int *static_surfacelist;
	                                                                       
	                                         
	   
	                                                                        
	                                                                         
	                                     
	int static_numshadowtrispvsbytes;
	unsigned char *static_shadowtrispvs;
	                                                                         
	                                       
	                                               
	int static_numlighttrispvsbytes;
	unsigned char *static_lighttrispvs;
	                                                                                    
	int static_shadowmap_receivers;
	int static_shadowmap_casters;
	                                                  
	int particlecache_numparticles;
	int particlecache_maxparticles;
	int particlecache_updateparticle;
	rtlight_particle_t *particlecache_particles;

	                         
	float bouncegrid_photoncolor[3];
	float bouncegrid_photons;
	int bouncegrid_hits;
	int bouncegrid_traces;
	float bouncegrid_effectiveradius;
}
rtlight_t;

typedef struct dlight_s
{
	                                
	                
	vec_t die;
	                                                
	                
	struct entity_render_s *ent;
	           
	                                        
	vec3_t origin;
	                         
	                    
	                                        
	vec3_t angles;
	                                      
	                
	matrix4x4_t matrix;
	                 
	                                        
	vec3_t color;
	                                    
	                                        
	char cubemapname[64];
	                                  
	                    
	int selected;
	                                         
	                                        
	vec_t radius;
	                                       
	                
	vec_t decay;
	                                             
	                
	vec_t intensity;
	                                         
	                
	vec_t initialradius;
	vec3_t initialcolor;
	                                                     
	                                        
	int style;
	               
	                                        
	int shadow;
	                   
	                                        
	vec_t corona;
	                                                                    
	                                        
	vec_t coronasizescale;
	                              
	                                        
	vec_t ambientscale;
	                              
	                                        
	vec_t diffusescale;
	                               
	                                        
	vec_t specularscale;
	                    
	                                        
	int flags;
	                              
	                    
	struct dlight_s *next;
	                                       
	                    
	rtlight_t rtlight;
}
dlight_t;

                                                               
                                                                            
                                                                      
                      
#define MAX_FRAMEBLENDS (MAX_FRAMEGROUPBLENDS * 2)
typedef struct frameblend_s
{
	int subframe;
	float lerp;
}
frameblend_t;

                                                                          
                      
  
                                                                              
                                                                             
                                                                      
  
                                                               
typedef struct entity_render_s
{
	           
	                
	              
	                
	                                      
	matrix4x4_t matrix;
	                                      
	matrix4x4_t inversematrix;
	                               
	float alpha;
	                          
	float scale;
	                             
	float transparent_offset;

	                  
	dp_model_t *model;
	                                                                 
	int entitynumber;
	                                                                                
	vec3_t colormap_pantscolor;
	vec3_t colormap_shirtcolor;
	                        
	int effects;
	                                                       
	int internaleffects;
	                   
	int skinnum;
	               
	int flags;

	                             
	float colormod[3];
	float glowmod[3];

	                                                                
	framegroupblend_t framegroupblend[MAX_FRAMEGROUPBLENDS];

	                                                    
	double shadertime;

	                                                  

	                                       
	vec3_t mins, maxs;
	                                                                                                                                     
	frameblend_t frameblend[MAX_FRAMEBLENDS];
	                                                                                                
	skeleton_t *skeleton;

	                                                               
	                                                            
	float          *animcache_vertex3f;
	r_meshbuffer_t *animcache_vertex3f_vertexbuffer;
	int             animcache_vertex3f_bufferoffset;
	float          *animcache_normal3f;
	r_meshbuffer_t *animcache_normal3f_vertexbuffer;
	int             animcache_normal3f_bufferoffset;
	float          *animcache_svector3f;
	r_meshbuffer_t *animcache_svector3f_vertexbuffer;
	int             animcache_svector3f_bufferoffset;
	float          *animcache_tvector3f;
	r_meshbuffer_t *animcache_tvector3f_vertexbuffer;
	int             animcache_tvector3f_bufferoffset;
	                                                                       
	r_vertexmesh_t *animcache_vertexmesh;
	r_meshbuffer_t *animcache_vertexmesh_vertexbuffer;
	int             animcache_vertexmesh_bufferoffset;
	                                                                       
	                                                                         
	                                                                   
	                                                              
	float *animcache_skeletaltransform3x4;
	r_meshbuffer_t *animcache_skeletaltransform3x4buffer;
	int animcache_skeletaltransform3x4offset;
	int animcache_skeletaltransform3x4size;

	                                            
	                                                  
	vec3_t custommodellight_ambient;
	vec3_t custommodellight_diffuse;
	vec3_t custommodellight_lightdir;
	                                                                          
	float custommodellight_origin[3];

	                                                       

	                                                                        
	                                                           
	float render_fullbright[3];
	                                                    
	float render_glowmod[3];
	                                                
	float render_modellight_ambient[3];
	float render_modellight_diffuse[3];
	float render_modellight_lightdir[3];
	float render_modellight_specular[3];
	                                                   
	float render_lightmap_ambient[3];
	float render_lightmap_diffuse[3];
	float render_lightmap_specular[3];
	                                                             
	float render_rtlight_diffuse[3];
	float render_rtlight_specular[3];
	                                                                     
	qboolean render_modellight_forced;
	                                                                                      
	qboolean render_rtlight_disabled;

	                                   
	                                                                                 
	int allowdecals;
	decalsystem_t decalsystem;

	                              
	                                         
	double last_trace_visibility;

	                                       
	vec_t userwavefunc_param[Q3WAVEFUNC_USER_COUNT];
}
entity_render_t;

typedef struct entity_persistent_s
{
	vec3_t trail_origin;                                                 
	vec3_t oldorigin;        
	vec3_t oldangles;        
	vec3_t neworigin;        
	vec3_t newangles;        
	vec_t lerpstarttime;        
	vec_t lerpdeltatime;        
	float muzzleflash;                                          
	float trail_time;                                                                                           
	qboolean trail_allowed;                                                                      
}
entity_persistent_t;

typedef struct entity_s
{
	                                  
	entity_state_t state_baseline;
	                                           
	entity_state_t state_previous;
	                                        
	entity_state_t state_current;

	                                        
	entity_persistent_t persistent;

	                                               
	entity_render_t render;
}
entity_t;

typedef struct usercmd_s
{
	vec3_t	viewangles;

                      
	float	forwardmove;
	float	sidemove;
	float	upmove;

	vec3_t	cursor_screen;
	vec3_t	cursor_start;
	vec3_t	cursor_end;
	vec3_t	cursor_impact;
	vec3_t	cursor_normal;
	vec_t	cursor_fraction;
	int		cursor_entitynumber;

	double time;                                                                                         
	double receivetime;                                 
	double clienttime;                                                      
	int msec;                       
	int buttons;
	int impulse;
	unsigned int sequence;
	qboolean applied;                                            
	qboolean predicted;                                            

	                     
	double frametime;
	qboolean canjump;
	qboolean jump;
	qboolean crouch;
} usercmd_t;

typedef struct lightstyle_s
{
	int		length;
	char	map[MAX_STYLESTRING];
} lightstyle_t;

typedef struct scoreboard_s
{
	char	name[MAX_SCOREBOARDNAME];
	int		frags;
	int		colors;                    
	             
	int		qw_userid;
	char	qw_userinfo[MAX_USERINFO_STRING];
	float	qw_entertime;
	int		qw_ping;
	int		qw_packetloss;
	int		qw_movementloss;
	int		qw_spectator;
	char	qw_team[8];
	char	qw_skin[MAX_QPATH];
} scoreboard_t;

typedef struct cshift_s
{
	float	destcolor[3];
	float	percent;		        
	float   alphafade;                    
} cshift_t;

#define	CSHIFT_CONTENTS	0
#define	CSHIFT_DAMAGE	1
#define	CSHIFT_BONUS	2
#define	CSHIFT_POWERUP	3
#define	CSHIFT_VCSHIFT	4
#define	NUM_CSHIFTS		5

#define	NAME_LENGTH	64


  
                                                            
  

#define	SIGNONS		4			                                              

typedef enum cactive_e
{
	ca_uninitialized,	                       
	ca_dedicated, 		                                                       
	ca_disconnected, 	                                         
	ca_connected		                                    
}
cactive_t;

typedef enum qw_downloadtype_e
{
	dl_none,
	dl_single,
	dl_skin,
	dl_model,
	dl_sound
}
qw_downloadtype_t;

typedef enum capturevideoformat_e
{
	CAPTUREVIDEOFORMAT_AVI_I420,
	CAPTUREVIDEOFORMAT_OGG_VORBIS_THEORA
}
capturevideoformat_t;

typedef struct capturevideostate_s
{
	double startrealtime;
	double framerate;
	int framestep;
	int framestepframe;
	qboolean active;
	qboolean realtime;
	qboolean error;
	int soundrate;
	int soundchannels;
	int frame;
	double starttime;
	double lastfpstime;
	int lastfpsframe;
	int soundsampleframe;
	unsigned char *screenbuffer;
	unsigned char *outbuffer;
	char basename[MAX_QPATH];
	int width, height;

	                                
	                                                                     
	short rgbtoyuvscaletable[3][3][256];
	unsigned char yuvnormalizetable[3][256];

	                                                                                  
	                                                                                                                     
	unsigned short vidramp[256 * 3];

	                                                   
	capturevideoformat_t format;
	const char *formatextension;
	qfile_t *videofile;
		                   
		                                                                                                                                                               
	void (*endvideo) (void);
	void (*videoframes) (int num);
	void (*soundframe) (const portable_sampleframe_t *paintbuffer, size_t length);

	                       
	void *formatspecific;
}
capturevideostate_t;

#define CL_MAX_DOWNLOADACKS 4

typedef struct cl_downloadack_s
{
	int start, size;
}
cl_downloadack_t;

typedef struct cl_soundstats_s
{
	int mixedsounds;
	int totalsounds;
	int latency_milliseconds;
}
cl_soundstats_t;

  
                                                                          
                        
  
typedef struct client_static_s
{
	cactive_t state;

	                                                  
	mempool_t *levelmempool;
	mempool_t *permanentmempool;

                    
	                        
	int demonum;
	                        
	char demos[MAX_DEMOS][MAX_DEMONAME];
	                                                   
	char demoname[MAX_QPATH];

                                                                     
                                               
	qboolean demorecording;
	fs_offset_t demo_lastcsprogssize;
	int demo_lastcsprogscrc;
	qboolean demoplayback;
	qboolean demostarting;                                                                                                
	qboolean timedemo;
	                           
	int forcetrack;
	qfile_t *demofile;
	                                                                      
	double td_starttime;
	int td_frames;                       
	double td_onesecondnexttime;
	double td_onesecondframes;
	double td_onesecondrealtime;
	double td_onesecondminfps;
	double td_onesecondmaxfps;
	double td_onesecondavgfps;
	int td_onesecondavgcount;
	                       
	qboolean demopaused;

	                                               
	cl_soundstats_t soundstats;

	qboolean connect_trying;
	int connect_remainingtries;
	double connect_nextsendtime;
	lhnetsocket_t *connect_mysocket;
	lhnetaddress_t connect_address;
	lhnetaddress_t rcon_address;
	                                                    
	                                                                 
	protocolversion_t protocol;

#define MAX_RCONS 16
	int rcon_trying;
	lhnetaddress_t rcon_addresses[MAX_RCONS];
	char rcon_commands[MAX_RCONS][MAX_INPUTLINE];
	double rcon_timeout[MAX_RCONS];
	int rcon_ringpos;

                         
	               
	int signon;
	                     
	netconn_t *netcon;

	                       
	                                              
	cl_downloadack_t dp_downloadack[CL_MAX_DOWNLOADACKS];

	                                                                     
	unsigned int servermovesequence;

	                         

	                                              
	int qw_qport;
	                                                                                                           
	unsigned int qw_incoming_sequence;
	unsigned int qw_outgoing_sequence;

	                                                                   
	char qw_downloadname[MAX_QPATH];
	unsigned char *qw_downloadmemory;
	int qw_downloadmemorycursize;
	int qw_downloadmemorymaxsize;
	int qw_downloadnumber;
	int qw_downloadpercent;
	qw_downloadtype_t qw_downloadtype;
	                        
	double qw_downloadspeedtime;
	int qw_downloadspeedcount;
	int qw_downloadspeedrate;
	qboolean qw_download_deflate;

	                                                                   
	unsigned char *qw_uploaddata;
	int qw_uploadsize;
	int qw_uploadpos;

	                  
	                                                           
	                                                                                 
	char userinfo[MAX_USERINFO_STRING];

	                                            
	char connect_userinfo[MAX_USERINFO_STRING];

	                      
	capturevideostate_t capturevideo;

	                 
	crypto_t crypto;

	                               
	int proquake_servermod;                                  
	int proquake_serverversion;                                                        
	int proquake_serverflags;                                   

	                                                               
	unsigned char *caughtcsprogsdata;
	fs_offset_t caughtcsprogsdatasize;

	int r_speeds_graph_length;
	int r_speeds_graph_current;
	int *r_speeds_graph_data;

	               
	int r_speeds_graph_datamin[r_stat_count];
	int r_speeds_graph_datamax[r_stat_count];
}
client_static_t;

extern client_static_t	cls;

             
typedef struct
{
	qboolean drawworld;
	qboolean drawenginesbar;
	qboolean drawcrosshair;
}csqc_vidvars_t;

typedef enum
{
	PARTICLE_BILLBOARD = 0,
	PARTICLE_SPARK = 1,
	PARTICLE_ORIENTED_DOUBLESIDED = 2,
	PARTICLE_VBEAM = 3,
	PARTICLE_HBEAM = 4,
	PARTICLE_INVALID = -1
}
porientation_t;

typedef enum
{
	PBLEND_ALPHA = 0,
	PBLEND_ADD = 1,
	PBLEND_INVMOD = 2,
	PBLEND_INVALID = -1
}
pblend_t;

typedef struct particletype_s
{
	pblend_t blendmode;
	porientation_t orientation;
	qboolean lighting;
}
particletype_t;

typedef enum ptype_e
{
	pt_dead, pt_alphastatic, pt_static, pt_spark, pt_beam, pt_rain, pt_raindecal, pt_snow, pt_bubble, pt_blood, pt_smoke, pt_decal, pt_entityparticle, pt_total
}
ptype_t;

typedef struct decal_s
{
	                                        
	unsigned short	typeindex;
	unsigned short	texnum;
	unsigned int	decalsequence;
	vec3_t			org;
	vec3_t			normal;
	float			size;
	float			alpha;         
	unsigned char	color[3];
	unsigned char	unused1;
	int				clusterindex;                        

	                                                                       
	float			time2;                       
	unsigned int	owner;                              
	dp_model_t			*ownermodel;                                                                             
	vec3_t			relativeorigin;                                                       
	vec3_t			relativenormal;                                                                 
}
decal_t;

typedef struct particle_s
{
	                                                                                                                                        

	                                       
	vec3_t          sortorigin;                                               
	vec3_t          org;
	vec3_t          vel;                                                                       
	float           size;
	float           alpha;         
	float           stretch;                   

	                                            
	float           stainsize;
	float           stainalpha;
	float           sizeincrease;                                  
	float           alphafade;                                     
	float           time2;                                           
	float           bounce;                                                                                                                                         
	float           gravity;                                                                             
	float           airfriction;                                                                                                                
	float           liquidfriction;                                                                                                                      
                                                                           
	float           delayedspawn;                                                
	float           die;                                                                  

	                                                   
	short			angle;                             
	short			spin;                                                             

	                                                   
	unsigned char   color[3];
	unsigned char   qualityreduction;                                                                                 
	unsigned char   typeindex;
	unsigned char   blendmode;
	unsigned char   orientation;
	unsigned char   texnum;
	unsigned char   staincolor[3];
	signed char     staintexnum;
}
particle_t;

typedef enum cl_parsingtextmode_e
{
	CL_PARSETEXTMODE_NONE,
	CL_PARSETEXTMODE_PING,
	CL_PARSETEXTMODE_STATUS,
	CL_PARSETEXTMODE_STATUS_PLAYERID,
	CL_PARSETEXTMODE_STATUS_PLAYERIP
}
cl_parsingtextmode_t;

typedef struct cl_locnode_s
{
	struct cl_locnode_s *next;
	char *name;
	vec3_t mins, maxs;
}
cl_locnode_t;

typedef struct showlmp_s
{
	qboolean	isactive;
	float		x;
	float		y;
	char		label[32];
	char		pic[128];
}
showlmp_t;

  
                                                            
                
  
typedef struct client_state_s
{
	                                                               
	int islocalgame;

	                                              
	float sendnoptime;

	                                                              
	usercmd_t cmd;
	                                                                   
	usercmd_t movecmd[CL_MAX_USERCMDS];

                                
	              
	int stats[MAX_CL_STATS];
	float *statsf;                           
	                                               
	int olditems;
	                                          
	float item_gettime[32];
	                               
	int activeweapon;
	                                        
	float weapontime;
	                                        
	float faceanimtime;
	                      
	float stairsmoothz;
	double stairsmoothtime;

	                                    
	cshift_t cshifts[NUM_CSHIFTS];
	                    
	cshift_t prev_cshifts[NUM_CSHIFTS];

                                                              
                                                                  
                                                                           
                                       

	                                
	                                                                    
	vec3_t mviewangles[2], viewangles;
	                                                   
	vec3_t mpunchangle[2], punchangle;
	                                                            
	vec3_t mpunchvector[2], punchvector;
	                                                    
	vec3_t mvelocity[2], velocity;
	                                                    
	vec_t mviewzoom[2], viewzoom;
	                                                                       
	                                                   
	                                                                     
	                                                                   
	                                     
	qboolean fixangle[2];

	                             
	                                                                                                               
	                                            
	qboolean movement_predicted;
	                                                                        
	qboolean movement_replay;
	                                                              
	vec3_t movement_origin;
	vec3_t movement_velocity;
	                                                               
	qboolean movement_replay_canjump;

	                                            
	vec3_t gunangles_prev;
	vec3_t gunangles_highpass;
	vec3_t gunangles_adjustment_lowpass;
	vec3_t gunangles_adjustment_highpass;
	                                            
	vec3_t gunorg_prev;
	vec3_t gunorg_highpass;
	vec3_t gunorg_adjustment_lowpass;
	vec3_t gunorg_adjustment_highpass;

                      
	float idealpitch;
	float pitchvel;
	qboolean nodrift;
	float driftmove;
	double laststop;

                                
	float sensitivityscale;
	csqc_vidvars_t csqc_vidvars;	                                                   
	qboolean csqc_wantsmousemove;
	qboolean csqc_paused;                                      
	struct model_s *csqc_model_precache[MAX_MODELS];

	                                     
	               

	                 
	qboolean paused;
	qboolean onground;
	qboolean inwater;

	              
	qboolean oldonground;
	double lastongroundtime;
	double hitgroundtime;
	float bob2_smooth;
	float bobfall_speed;
	float bobfall_swing;
	double calcrefdef_prevtime;

	                                            
	int intermission;
	                                
	double completed_time;

	                                         
	double mtime[2];

	                                                                        
	                                                                        
	                                                                      
	                                                                         
	                                                       
	double time, oldtime;
	                                                                    
	                                                     
	double realframetime;
	
	                                 
	float deathfade;

	                                  
	float motionbluralpha;

	                                                                    
	float last_received_message;

                                                                       
	struct model_s *model_precache[MAX_MODELS];
	struct sfx_s *sound_precache[MAX_SOUNDS];

	                                                                                                                     
	char model_name[MAX_MODELS][MAX_QPATH];
	char sound_name[MAX_SOUNDS][MAX_QPATH];

	                                 
	char worldmessage[40];                                       
	                       
	char worldbasename[MAX_QPATH];      
	char worldname[MAX_QPATH];               
	char worldnamenoextension[MAX_QPATH];           
	                                       
	int viewentity;
	                                                       
	                                                                  
	int realplayerentity;
	                                                                       
	                                                                         
	                                                                      
	                                      
	int playerentity;
	                                       
	int maxclients;
	                                                
	int gametype;

	                                                                  
	dp_model_t *model_bolt;
	dp_model_t *model_bolt2;
	dp_model_t *model_bolt3;
	dp_model_t *model_beam;
	sfx_t *sfx_wizhit;
	sfx_t *sfx_knighthit;
	sfx_t *sfx_tink1;
	sfx_t *sfx_ric1;
	sfx_t *sfx_ric2;
	sfx_t *sfx_ric3;
	sfx_t *sfx_r_exp3;
	                                                                                           
	qboolean foundtalk2wav;

                        

	                        
	struct model_s *worldmodel;

	                
	entity_t viewent;

	           
	int cdtrack, looptrack;

                  

	                  
	scoreboard_t *scores;

	                                                                                   
	cl_parsingtextmode_t parsingtextmode;
	int parsingtextplayerindex;
	                                                                                                   
	                                                                  
	                                                                      
	                                                                        
	           
	int parsingtextexpectingpingforscores;

	                        
	                                       
#define LATESTFRAMENUMS 32
	int latestframenumsposition;
	int latestframenums[LATESTFRAMENUMS];
	unsigned int latestsendnums[LATESTFRAMENUMS];
	entityframe_database_t *entitydatabase;
	entityframe4_database_t *entitydatabase4;
	entityframeqw_database_t *entitydatabaseqw;

	                                                                                
	int lastquakeentity;
	unsigned char isquakeentity[MAX_EDICTS];

	                                         
	vec3_t playerstandmins;
	vec3_t playerstandmaxs;
	vec3_t playercrouchmins;
	vec3_t playercrouchmaxs;

	                                      
	unsigned int decalsequence;

	int max_entities;
	int max_csqcrenderentities;
	int max_static_entities;
	int max_effects;
	int max_beams;
	int max_dlights;
	int max_lightstyle;
	int max_brushmodel_entities;
	int max_particles;
	int max_decals;
	int max_showlmps;

	entity_t *entities;
	entity_render_t *csqcrenderentities;
	unsigned char *entities_active;
	entity_t *static_entities;
	cl_effect_t *effects;
	beam_t *beams;
	dlight_t *dlights;
	lightstyle_t *lightstyle;
	int *brushmodel_entities;
	particle_t *particles;
	decal_t *decals;
	showlmp_t *showlmps;

	int num_entities;
	int num_static_entities;
	int num_brushmodel_entities;
	int num_effects;
	int num_beams;
	int num_dlights;
	int num_particles;
	int num_decals;
	int num_showlmps;

	double particles_updatetime;
	double decals_updatetime;
	int free_particle;
	int free_decal;

	                                      
	int loadmodel_current;
	int downloadmodel_current;
	int loadmodel_total;
	int loadsound_current;
	int downloadsound_current;
	int loadsound_total;
	qboolean downloadcsqc;
	qboolean loadcsqc;
	qboolean loadbegun;
	qboolean loadfinished;

	                   

	                                      
	char qw_serverinfo[MAX_SERVERINFO_STRING];

	                                                                      
	double last_ping_request;

	                      
	int qw_servercount;

	                          
	int qw_teamplay;

	                                                     
	                                                        
	                        

	                                     
	double lastpackettime;

	                                            
	unsigned int moveflags;
	float movevars_wallfriction;
	float movevars_waterfriction;
	float movevars_friction;
	float movevars_timescale;
	float movevars_gravity;
	float movevars_stopspeed;
	float movevars_maxspeed;
	float movevars_spectatormaxspeed;
	float movevars_accelerate;
	float movevars_airaccelerate;
	float movevars_wateraccelerate;
	float movevars_entgravity;
	float movevars_jumpvelocity;
	float movevars_edgefriction;
	float movevars_maxairspeed;
	float movevars_stepheight;
	float movevars_airaccel_qw;
	float movevars_airaccel_qw_stretchfactor;
	float movevars_airaccel_sideways_friction;
	float movevars_airstopaccelerate;
	float movevars_airstrafeaccelerate;
	float movevars_maxairstrafespeed;
	float movevars_airstrafeaccel_qw;
	float movevars_aircontrol;
	float movevars_aircontrol_power;
	float movevars_aircontrol_penalty;
	float movevars_warsowbunny_airforwardaccel;
	float movevars_warsowbunny_accel;
	float movevars_warsowbunny_topspeed;
	float movevars_warsowbunny_turnaccel;
	float movevars_warsowbunny_backtosideratio;
	float movevars_ticrate;
	float movevars_airspeedlimit_nonqw;

	                             
	int qw_modelindex_spike;
	int qw_modelindex_player;
	int qw_modelindex_flag;
	int qw_modelindex_s_explod;

	vec3_t qw_intermission_origin;
	vec3_t qw_intermission_angles;

	                                                   
	int qw_num_nails;
	vec_t qw_nails[255][6];

	float qw_weaponkick;

	unsigned int qw_validsequence;

	unsigned int qw_deltasequence[QW_UPDATE_BACKUP];

	              
	                                                            
	unsigned short csqc_server2csqcentitynumber[MAX_EDICTS];
	qboolean csqc_loaded;
	vec3_t csqc_vieworigin;
	vec3_t csqc_viewangles;
	vec3_t csqc_vieworiginfromengine;
	vec3_t csqc_viewanglesfromengine;
	matrix4x4_t csqc_viewmodelmatrixfromengine;
	qboolean csqc_usecsqclistener;
	matrix4x4_t csqc_listenermatrix;
	char csqc_printtextbuf[MAX_INPUTLINE];

	                         
	world_t world;

	                                                                      
	cl_locnode_t *locnodes;
	                                                               
	                                                                    
	vec3_t lastdeathorigin;

	                                                                    
	                             
	size_t buildlightmapmemorysize;
	unsigned char *buildlightmapmemory;

	                                  
	skeleton_t *engineskeletonobjects;
}
client_state_t;

  
        
  
extern cvar_t cl_name;
extern cvar_t cl_color;
extern cvar_t cl_rate;
extern cvar_t cl_rate_burstsize;
extern cvar_t cl_pmodel;
extern cvar_t cl_playermodel;
extern cvar_t cl_playerskin;

extern cvar_t rcon_password;
extern cvar_t rcon_address;

extern cvar_t cl_upspeed;
extern cvar_t cl_forwardspeed;
extern cvar_t cl_backspeed;
extern cvar_t cl_sidespeed;

extern cvar_t cl_movespeedkey;

extern cvar_t cl_yawspeed;
extern cvar_t cl_pitchspeed;

extern cvar_t cl_anglespeedkey;

extern cvar_t cl_autofire;

extern cvar_t cl_shownet;
extern cvar_t cl_nolerp;
extern cvar_t cl_nettimesyncfactor;
extern cvar_t cl_nettimesyncboundmode;
extern cvar_t cl_nettimesyncboundtolerance;

extern cvar_t cl_pitchdriftspeed;
extern cvar_t lookspring;
extern cvar_t lookstrafe;
extern cvar_t sensitivity;

extern cvar_t freelook;

extern cvar_t m_pitch;
extern cvar_t m_yaw;
extern cvar_t m_forward;
extern cvar_t m_side;

extern cvar_t cl_autodemo;
extern cvar_t cl_autodemo_nameformat;
extern cvar_t cl_autodemo_delete;

extern cvar_t r_draweffects;

extern cvar_t cl_explosions_alpha_start;
extern cvar_t cl_explosions_alpha_end;
extern cvar_t cl_explosions_size_start;
extern cvar_t cl_explosions_size_end;
extern cvar_t cl_explosions_lifetime;
extern cvar_t cl_stainmaps;
extern cvar_t cl_stainmaps_clearonload;

extern cvar_t cl_prydoncursor;
extern cvar_t cl_prydoncursor_notrace;

extern cvar_t cl_locs_enable;

extern client_state_t cl;

extern void CL_AllocLightFlash (entity_render_t *ent, matrix4x4_t *matrix, float radius, float red, float green, float blue, float decay, float lifetime, int cubemapnum, int style, int shadowenable, vec_t corona, vec_t coronasizescale, vec_t ambientscale, vec_t diffusescale, vec_t specularscale, int flags);

cl_locnode_t *CL_Locs_FindNearest(const vec3_t point);
void CL_Locs_FindLocationName(char *buffer, size_t buffersize, vec3_t point);

                                                                               

  
          
  

void CL_Shutdown (void);
void CL_Init (void);

void CL_EstablishConnection(const char *host, int firstarg);

void CL_Disconnect (void);
void CL_Disconnect_f (void);

void CL_UpdateRenderEntity(entity_render_t *ent);
void CL_SetEntityColormapColors(entity_render_t *ent, int colormap);
void CL_UpdateViewEntities(void);

  
           
  
typedef struct kbutton_s
{
	int		down[2];		                           
	int		state;			                        
}
kbutton_t;

extern	kbutton_t	in_mlook, in_klook;
extern 	kbutton_t 	in_strafe;
extern 	kbutton_t 	in_speed;

void CL_InitInput (void);
void CL_SendMove (void);

void CL_ValidateState(entity_state_t *s);
void CL_MoveLerpEntityStates(entity_t *ent);
void CL_LerpUpdate(entity_t *e);
void CL_ParseTEnt (void);
void CL_NewBeam (int ent, vec3_t start, vec3_t end, dp_model_t *m, int lightning);
void CL_RelinkBeams (void);
void CL_Beam_CalculatePositions (const beam_t *b, vec3_t start, vec3_t end);
void CL_ClientMovement_Replay(void);

void CL_ClearTempEntities (void);
entity_render_t *CL_NewTempEntity (double shadertime);

void CL_Effect(vec3_t org, int modelindex, int startframe, int framecount, float framerate);

void CL_ClearState (void);
void CL_ExpandEntities(int num);
void CL_ExpandCSQCRenderEntities(int num);
void CL_SetInfo(const char *key, const char *value, qboolean send, qboolean allowstarkey, qboolean allowmodel, qboolean quiet);


void CL_UpdateWorld (void);
void CL_WriteToServer (void);
void CL_Input (void);
extern int cl_ignoremousemoves;


float CL_KeyState (kbutton_t *key);
const char *Key_KeynumToString (int keynum, char *buf, size_t buflength);
int Key_StringToKeynum (const char *str);

  
            
  
void CL_StopPlayback(void);
void CL_ReadDemoMessage(void);
void CL_WriteDemoMessage(sizebuf_t *mesage);

void CL_CutDemo(unsigned char **buf, fs_offset_t *filesize);
void CL_PasteDemo(unsigned char **buf, fs_offset_t *filesize);

void CL_NextDemo(void);
void CL_Stop_f(void);
void CL_Record_f(void);
void CL_PlayDemo_f(void);
void CL_TimeDemo_f(void);

  
             
  
void CL_Parse_Init(void);
void CL_Parse_Shutdown(void);
void CL_ParseServerMessage(void);
void CL_Parse_DumpPacket(void);
void CL_Parse_ErrorCleanUp(void);
void QW_CL_StartUpload(unsigned char *data, int size);
extern cvar_t qport;
void CL_KeepaliveMessage(qboolean readmessages);                                             

  
       
  
void V_StartPitchDrift (void);
void V_StopPitchDrift (void);

void V_Init (void);
float V_CalcRoll (const vec3_t angles, const vec3_t velocity);
void V_UpdateBlends (void);
void V_ParseDamage (void);

  
          
  

extern cvar_t cl_particles;
extern cvar_t cl_particles_quality;
extern cvar_t cl_particles_size;
extern cvar_t cl_particles_quake;
extern cvar_t cl_particles_blood;
extern cvar_t cl_particles_blood_alpha;
extern cvar_t cl_particles_blood_decal_alpha;
extern cvar_t cl_particles_blood_decal_scalemin;
extern cvar_t cl_particles_blood_decal_scalemax;
extern cvar_t cl_particles_blood_bloodhack;
extern cvar_t cl_particles_bulletimpacts;
extern cvar_t cl_particles_explosions_sparks;
extern cvar_t cl_particles_explosions_shell;
extern cvar_t cl_particles_rain;
extern cvar_t cl_particles_snow;
extern cvar_t cl_particles_smoke;
extern cvar_t cl_particles_smoke_alpha;
extern cvar_t cl_particles_smoke_alphafade;
extern cvar_t cl_particles_sparks;
extern cvar_t cl_particles_bubbles;
extern cvar_t cl_decals;
extern cvar_t cl_decals_time;
extern cvar_t cl_decals_fadetime;

void CL_Particles_Clear(void);
void CL_Particles_Init(void);
void CL_Particles_Shutdown(void);
particle_t *CL_NewParticle(const vec3_t sortorigin, unsigned short ptypeindex, int pcolor1, int pcolor2, int ptex, float psize, float psizeincrease, float palpha, float palphafade, float pgravity, float pbounce, float px, float py, float pz, float pvx, float pvy, float pvz, float pairfriction, float pliquidfriction, float originjitter, float velocityjitter, qboolean pqualityreduction, float lifetime, float stretch, pblend_t blendmode, porientation_t orientation, int staincolor1, int staincolor2, int staintex, float stainalpha, float stainsize, float angle, float spin, float tint[4]);

typedef enum effectnameindex_s
{
	EFFECT_NONE,
	EFFECT_TE_GUNSHOT,
	EFFECT_TE_GUNSHOTQUAD,
	EFFECT_TE_SPIKE,
	EFFECT_TE_SPIKEQUAD,
	EFFECT_TE_SUPERSPIKE,
	EFFECT_TE_SUPERSPIKEQUAD,
	EFFECT_TE_WIZSPIKE,
	EFFECT_TE_KNIGHTSPIKE,
	EFFECT_TE_EXPLOSION,
	EFFECT_TE_EXPLOSIONQUAD,
	EFFECT_TE_TAREXPLOSION,
	EFFECT_TE_TELEPORT,
	EFFECT_TE_LAVASPLASH,
	EFFECT_TE_SMALLFLASH,
	EFFECT_TE_FLAMEJET,
	EFFECT_EF_FLAME,
	EFFECT_TE_BLOOD,
	EFFECT_TE_SPARK,
	EFFECT_TE_PLASMABURN,
	EFFECT_TE_TEI_G3,
	EFFECT_TE_TEI_SMOKE,
	EFFECT_TE_TEI_BIGEXPLOSION,
	EFFECT_TE_TEI_PLASMAHIT,
	EFFECT_EF_STARDUST,
	EFFECT_TR_ROCKET,
	EFFECT_TR_GRENADE,
	EFFECT_TR_BLOOD,
	EFFECT_TR_WIZSPIKE,
	EFFECT_TR_SLIGHTBLOOD,
	EFFECT_TR_KNIGHTSPIKE,
	EFFECT_TR_VORESPIKE,
	EFFECT_TR_NEHAHRASMOKE,
	EFFECT_TR_NEXUIZPLASMA,
	EFFECT_TR_GLOWTRAIL,
	EFFECT_SVC_PARTICLE,
	EFFECT_TOTAL
}
effectnameindex_t;

int CL_ParticleEffectIndexForName(const char *name);
const char *CL_ParticleEffectNameForIndex(int i);
void CL_ParticleEffect(int effectindex, float pcount, const vec3_t originmins, const vec3_t originmaxs, const vec3_t velocitymins, const vec3_t velocitymaxs, entity_t *ent, int palettecolor);
void CL_ParticleTrail(int effectindex, float pcount, const vec3_t originmins, const vec3_t originmaxs, const vec3_t velocitymins, const vec3_t velocitymaxs, entity_t *ent, int palettecolor, qboolean spawndlight, qboolean spawnparticles, float tintmins[4], float tintmaxs[4], float fade);
void CL_ParticleBox(int effectindex, float pcount, const vec3_t originmins, const vec3_t originmaxs, const vec3_t velocitymins, const vec3_t velocitymaxs, entity_t *ent, int palettecolor, qboolean spawndlight, qboolean spawnparticles, float tintmins[4], float tintmaxs[4], float fade);
void CL_ParseParticleEffect (void);
void CL_ParticleCube (const vec3_t mins, const vec3_t maxs, const vec3_t dir, int count, int colorbase, vec_t gravity, vec_t randomvel);
void CL_ParticleRain (const vec3_t mins, const vec3_t maxs, const vec3_t dir, int count, int colorbase, int type);
void CL_EntityParticles (const entity_t *ent);
void CL_ParticleExplosion (const vec3_t org);
void CL_ParticleExplosion2 (const vec3_t org, int colorStart, int colorLength);
void R_NewExplosion(const vec3_t org);

#include "cl_screen.h"

extern qboolean sb_showscores;

float RSurf_FogVertex(const vec3_t p);
float RSurf_FogPoint(const vec3_t p);

typedef enum r_viewport_type_e
{
	R_VIEWPORTTYPE_ORTHO,
	R_VIEWPORTTYPE_PERSPECTIVE,
	R_VIEWPORTTYPE_PERSPECTIVE_INFINITEFARCLIP,
	R_VIEWPORTTYPE_PERSPECTIVECUBESIDE,
	R_VIEWPORTTYPE_TOTAL
}
r_viewport_type_t;

typedef struct r_viewport_s
{
	matrix4x4_t cameramatrix;                                                        
	matrix4x4_t viewmatrix;                                                         
	matrix4x4_t projectmatrix;                                                                  
	int x;
	int y;
	int z;
	int width;
	int height;
	int depth;
	r_viewport_type_t type;
	float screentodepth[2];                                                                                     
}
r_viewport_t;

typedef struct r_refdef_view_s
{
	                                                      
	                                                                               
	                           
	                                                    

	                                                                         
	                                                                       
	                                       

	                           
	matrix4x4_t matrix, inverse_matrix;
	vec3_t origin;
	vec3_t forward;
	vec3_t left;
	vec3_t right;
	vec3_t up;
	int numfrustumplanes;
	mplane_t frustum[6];
	qboolean useclipplane;
	qboolean usecustompvs;                                                                  
	mplane_t clipplane;
	float frustum_x, frustum_y;
	vec3_t frustumcorner[4];
	                                         
	int useperspective;
	float ortho_x, ortho_y;

	                           
	int x;
	int y;
	int z;
	int width;
	int height;
	int depth;
	r_viewport_t viewport;                                                                                                          

	                                                         
	int colormask[4];

	                                            
	float colorscale;

	                                                       
	qboolean clear;
	                                                                   
	qboolean isoverlay;
	                                                                                                                                  
	qboolean ismain;

	                                                                      
	                                                                 
	                                                           
	qboolean showdebug;

	                                                                                                 
	int cullface_front;
	int cullface_back;

	                                                                            
	float quality;
}
r_refdef_view_t;

typedef struct r_refdef_viewcache_s
{
	                              
	int maxentities;
	int world_numclusters;
	int world_numclusterbytes;
	int world_numleafs;
	int world_numsurfaces;

	                                                    

	                                                          
	                                                     
	unsigned char *entityvisible;

	                                                          
	                                                                      
	unsigned char *world_pvsbits;
	unsigned char *world_leafvisible;
	unsigned char *world_surfacevisible;
	                                                            
	qboolean world_novis;
}
r_refdef_viewcache_t;

                                                                                                                  
                                                                                                                             
typedef struct r_refdef_scene_s {
	                                                                   
	qboolean extraupdate;

	                                                           
	double time;

	            
	entity_render_t *worldentity;

	                             
	dp_model_t *worldmodel;

	                                        
	entity_render_t **entities;
	int numentities;
	int maxentities;

	                                                                
	entity_render_t *tempentities;
	int numtempentities;
	int maxtempentities;
	qboolean expandtempentities;

	                            
	rtlight_t *lights[MAX_DLIGHTS];
	rtlight_t templights[MAX_DLIGHTS];
	int numlights;

	                                                            
	float rtlightstylevalue[MAX_LIGHTSTYLES];	                                     
	                                                  
	                                     
	unsigned short lightstylevalue[MAX_LIGHTSTYLES];	                                   

	                                                                      
	                             
	float ambientintensity;
	                                                              
	                             
	float lightmapintensity;

	qboolean rtworld;
	qboolean rtworldshadows;
	qboolean rtdlight;
	qboolean rtdlightshadows;
} r_refdef_scene_t;

typedef struct r_refdef_s
{
	                                                                    
	                                                                      
	                                                                  

	                                         
	                                     
	float frustumscale_x, frustumscale_y;

	                                                                                                                    
	r_refdef_view_t view;
	r_refdef_viewcache_t viewcache;

	                                                               
	double nearclip;
	                                                                               
	                                                       
	double farclip;

	                         
	float viewblend[4];

	r_refdef_scene_t scene;

	float fogplane[4];
	float fogplaneviewdist;
	qboolean fogplaneviewabove;
	float fogheightfade;
	float fogcolor[3];
	float fogrange;
	float fograngerecip;
	float fogmasktabledistmultiplier;
#define FOGMASKTABLEWIDTH 1024
	float fogmasktable[FOGMASKTABLEWIDTH];
	float fogmasktable_start, fogmasktable_alpha, fogmasktable_range, fogmasktable_density;
	float fog_density;
	float fog_red;
	float fog_green;
	float fog_blue;
	float fog_alpha;
	float fog_start;
	float fog_end;
	float fog_height;
	float fog_fadedepth;
	qboolean fogenabled;
	qboolean oldgl_fogenable;

	                                                         
	char fog_height_texturename[64];                                        
	unsigned char *fog_height_table1d;
	unsigned char *fog_height_table2d;
	int fog_height_tablesize;          
	float fog_height_tablescale;
	float fog_height_texcoordscale;
	char fogheighttexturename[64];                                                

	int draw2dstage;                                                         

	                                     
	qboolean envmap;

	                                                                             
	float polygonfactor;
	float polygonoffset;
	float shadowpolygonfactor;
	float shadowpolygonoffset;

	                                                   
	double lastdrawscreentime;

	                                       
	                                         
	int stats[r_stat_count];
}
r_refdef_t;

extern r_refdef_t r_refdef;

typedef enum waterlevel_e
{
	WATERLEVEL_NONE,
	WATERLEVEL_WETFEET,
	WATERLEVEL_SWIMMING,
	WATERLEVEL_SUBMERGED
}
waterlevel_t;

typedef struct cl_clientmovement_state_s
{
	                                    
	struct prvm_edict_s *self;
	           
	vec3_t origin;
	vec3_t velocity;
	                                                           
	vec3_t mins;
	vec3_t maxs;
	                          
	qboolean onground;
	                      
	qboolean crouched;
	                                                       
	int watertype;
	           
	waterlevel_t waterlevel;
	                                        
	                                            
	float waterjumptime;

	               
	usercmd_t cmd;
}
cl_clientmovement_state_t;
void CL_ClientMovement_PlayerMove_Frame(cl_clientmovement_state_t *s);

                                          
void CL_RotateMoves(const matrix4x4_t *m);

typedef enum meshname_e {
	MESH_DEBUG,
	MESH_CSQCPOLYGONS,
	MESH_PARTICLES,
	MESH_UI,
	NUM_MESHENTITIES,
} meshname_t;
extern entity_t cl_meshentities[NUM_MESHENTITIES];
extern dp_model_t cl_meshentitymodels[NUM_MESHENTITIES];
extern const char *cl_meshentitynames[NUM_MESHENTITIES];
#define CL_Mesh_Debug() (&cl_meshentitymodels[MESH_DEBUG])
#define CL_Mesh_CSQC() (&cl_meshentitymodels[MESH_CSQCPOLYGONS])
#define CL_Mesh_Particles() (&cl_meshentitymodels[MESH_PARTICLES])
#define CL_Mesh_UI() (&cl_meshentitymodels[MESH_UI])
void CL_MeshEntities_AddToScene(void);
void CL_MeshEntities_Reset(void);
void CL_UpdateEntityShading(void);

void CL_NewFrameReceived(int num);
void CL_ParseEntityLump(char *entitystring);
void CL_FindNonSolidLocation(const vec3_t in, vec3_t out, vec_t radius);
void CL_RelinkLightFlashes(void);
void CL_Beam_AddPolygons(const beam_t *b);
void Sbar_ShowFPS(void);
void Sbar_ShowFPS_Update(void);
void Host_SaveConfig(void);
void Host_LoadConfig_f(void);
void CL_UpdateMoveVars(void);
void SCR_CaptureVideo_SoundFrame(const portable_sampleframe_t *paintbuffer, size_t length);
void V_DriftPitch(void);
void V_FadeViewFlashs(void);
void V_CalcViewBlend(void);
void V_CalcRefdefUsing (const matrix4x4_t *entrendermatrix, const vec3_t clviewangles, qboolean teleported, qboolean clonground, qboolean clcmdjump, float clstatsviewheight, qboolean cldead, qboolean clintermission, const vec3_t clvelocity);
void V_CalcRefdef(void);
void CL_Locs_Reload_f(void);

#endif

