  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

#ifndef MODEL_SHARED_H
#define MODEL_SHARED_H

typedef enum synctype_e {ST_SYNC=0, ST_RAND } synctype_t;

  

                                           
                             

  

typedef enum modtype_e {mod_invalid, mod_brushq1, mod_sprite, mod_alias, mod_brushq2, mod_brushq3, mod_obj, mod_null} modtype_t;

typedef struct animscene_s
{
	char name[32];                         
	int firstframe;
	int framecount;
	int loop;                 
	float framerate;
}
animscene_t;

typedef struct skinframe_s
{
	rtexture_t *stain;                                                               
	rtexture_t *merged;                                 
	rtexture_t *base;                                             
	rtexture_t *pants;                             
	rtexture_t *shirt;                             
	rtexture_t *nmap;                                
	rtexture_t *gloss;                       
	rtexture_t *glow;                           
	rtexture_t *fog;                                             
	rtexture_t *reflect;                                        
	                                     
	                                                                         
	                
	                                                                   
	                                       
	struct skinframe_s *next;                      
	char basename[MAX_QPATH];                
	int textureflags;                        
	int comparewidth;
	int compareheight;
	int comparecrc;
	                                                                          
	                                                                          
	            
	unsigned int loadsequence;
	                                                        
	qboolean hasalpha;
	                                       
	float avgcolor[4];
	                                                                                                                                                      
	unsigned char *qpixels;
	int qwidth;
	int qheight;
	qboolean qhascolormapping;
	qboolean qgeneratebase;
	qboolean qgeneratemerged;
	qboolean qgeneratenmap;
	qboolean qgenerateglow;
}
skinframe_t;

struct md3vertex_s;
struct trivertx_s;
typedef struct texvecvertex_s
{
	signed char svec[3];
	signed char tvec[3];
}
texvecvertex_t;

typedef struct blendweights_s
{
	unsigned char index[4];
	unsigned char influence[4];
}
blendweights_t;

typedef struct r_vertexgeneric_s
{
	           
	float vertex3f[3];
	float color4f[4];
	float texcoord2f[2];
}
r_vertexgeneric_t;

typedef struct r_vertexmesh_s
{
	           
	float vertex3f[3];
	float color4f[4];
	float texcoordtexture2f[2];
	float texcoordlightmap2f[2];
	float svector3f[3];
	float tvector3f[3];
	float normal3f[3];
	unsigned char skeletalindex4ub[4];
	unsigned char skeletalweight4ub[4];
}
r_vertexmesh_t;

typedef struct r_meshbuffer_s
{
	int bufferobject;          
	void *devicebuffer;            
	size_t size;
	qboolean isindexbuffer;
	qboolean isuniformbuffer;
	qboolean isdynamic;
	qboolean isindex16;
	char name[MAX_QPATH];
}
r_meshbuffer_t;

                                                
                                                    
typedef struct surfmesh_s
{
	                                 
	int num_triangles;                                   
	int *data_element3i;                                                                            
	r_meshbuffer_t *data_element3i_indexbuffer;
	int data_element3i_bufferoffset;
	unsigned short *data_element3s;                                                                                                        
	r_meshbuffer_t *data_element3s_indexbuffer;
	int data_element3s_bufferoffset;
	int *data_neighbor3i;                                                              
	                               
	int num_vertices;                                  
	float *data_vertex3f;                                   
	float *data_svector3f;                                                                        
	float *data_tvector3f;                                                                       
	float *data_normal3f;                                                                      
	float *data_texcoordtexture2f;                                                
	float *data_texcoordlightmap2f;                                                 
	float *data_lightmapcolor4f;
	unsigned char *data_skeletalindex4ub;
	unsigned char *data_skeletalweight4ub;
	int *data_lightmapoffsets;                                                             
	r_vertexmesh_t *data_vertexmesh;                              
	                                                         
	r_meshbuffer_t *vbo_vertexbuffer;
	int vbooffset_vertex3f;
	int vbooffset_svector3f;
	int vbooffset_tvector3f;
	int vbooffset_normal3f;
	int vbooffset_texcoordtexture2f;
	int vbooffset_texcoordlightmap2f;
	int vbooffset_lightmapcolor4f;
	int vbooffset_skeletalindex4ub;
	int vbooffset_skeletalweight4ub;
	int vbooffset_vertexmesh;
	                                                                
	int num_morphframes;
	struct md3vertex_s *data_morphmd3vertex;
	struct trivertx_s *data_morphmdlvertex;
	struct texvecvertex_s *data_morphtexvecvertex;
	float *data_morphmd2framesize6f;
	float num_morphmdlframescale[3];
	float num_morphmdlframetranslate[3];
	                                                                
	struct blendweights_s *data_blendweights;
	int num_blends;
	unsigned short *blends;
	                                                       
	qboolean isanimated;

	                                         
	r_meshbuffer_t *vertexmesh_vertexbuffer;

	                                             
	int num_vertexhashsize;                                  
	int *data_vertexhash;                                                                                          
	int max_vertices;                                                                           
	int max_triangles;                                       
}
surfmesh_t;

#define SHADOWMESHVERTEXHASH 1024
typedef struct shadowmeshvertexhash_s
{
	struct shadowmeshvertexhash_s *next;
}
shadowmeshvertexhash_t;

typedef struct shadowmesh_s
{
	                     
	struct shadowmesh_s *next;
	                                            
	rtexture_t *map_diffuse;
	rtexture_t *map_specular;
	rtexture_t *map_normal;
	               
	int numverts, maxverts;
	int numtriangles, maxtriangles;
	              
	float *vertex3f;
	                                            
	float *svector3f;
	float *tvector3f;
	float *normal3f;
	float *texcoord2f;
	              
	int *element3i;
	r_meshbuffer_t *element3i_indexbuffer;
	int element3i_bufferoffset;
	unsigned short *element3s;
	r_meshbuffer_t *element3s_indexbuffer;
	int element3s_bufferoffset;
	                                     
	                                                 
	r_vertexmesh_t *vertexmesh;                
	                                                    
	int sideoffsets[6], sidetotals[6];
	                                            
	int *neighbor3i;
	                                                                     
	                        
	shadowmeshvertexhash_t **vertexhashtable, *vertexhashentries;
	r_meshbuffer_t *vbo_vertexbuffer;
	int vbooffset_vertex3f;
	int vbooffset_svector3f;
	int vbooffset_tvector3f;
	int vbooffset_normal3f;
	int vbooffset_texcoord2f;
	int vbooffset_vertexmesh;
}
shadowmesh_t;

                                                                                
                                             
#define Q3TEXTUREFLAG_TWOSIDED 1
#define Q3TEXTUREFLAG_NOPICMIP 16
#define Q3TEXTUREFLAG_POLYGONOFFSET 32
#define Q3TEXTUREFLAG_REFRACTION 256
#define Q3TEXTUREFLAG_REFLECTION 512
#define Q3TEXTUREFLAG_WATERSHADER 1024
#define Q3TEXTUREFLAG_CAMERA 2048
#define Q3TEXTUREFLAG_TRANSPARENTSORT 4096

#define Q3PATHLENGTH 64
#define TEXTURE_MAXFRAMES 64
#define Q3WAVEPARMS 4
#define Q3DEFORM_MAXPARMS 3
#define Q3SHADER_MAXLAYERS 8
#define Q3RGBGEN_MAXPARMS 3
#define Q3ALPHAGEN_MAXPARMS 1
#define Q3TCGEN_MAXPARMS 6
#define Q3TCMOD_MAXPARMS 6
#define Q3MAXTCMODS 8
#define Q3MAXDEFORMS 4

typedef enum q3wavefunc_e
{
	Q3WAVEFUNC_NONE,
	Q3WAVEFUNC_INVERSESAWTOOTH,
	Q3WAVEFUNC_NOISE,
	Q3WAVEFUNC_SAWTOOTH,
	Q3WAVEFUNC_SIN,
	Q3WAVEFUNC_SQUARE,
	Q3WAVEFUNC_TRIANGLE,
	Q3WAVEFUNC_COUNT
}
q3wavefunc_e;
typedef int q3wavefunc_t;
#define Q3WAVEFUNC_USER_COUNT 4
#define Q3WAVEFUNC_USER_SHIFT 8                                 

typedef enum q3deform_e
{
	Q3DEFORM_NONE,
	Q3DEFORM_PROJECTIONSHADOW,
	Q3DEFORM_AUTOSPRITE,
	Q3DEFORM_AUTOSPRITE2,
	Q3DEFORM_TEXT0,
	Q3DEFORM_TEXT1,
	Q3DEFORM_TEXT2,
	Q3DEFORM_TEXT3,
	Q3DEFORM_TEXT4,
	Q3DEFORM_TEXT5,
	Q3DEFORM_TEXT6,
	Q3DEFORM_TEXT7,
	Q3DEFORM_BULGE,
	Q3DEFORM_WAVE,
	Q3DEFORM_NORMAL,
	Q3DEFORM_MOVE,
	Q3DEFORM_COUNT
}
q3deform_t;

typedef enum q3rgbgen_e
{
	Q3RGBGEN_IDENTITY,
	Q3RGBGEN_CONST,
	Q3RGBGEN_ENTITY,
	Q3RGBGEN_EXACTVERTEX,
	Q3RGBGEN_IDENTITYLIGHTING,
	Q3RGBGEN_LIGHTINGDIFFUSE,
	Q3RGBGEN_ONEMINUSENTITY,
	Q3RGBGEN_ONEMINUSVERTEX,
	Q3RGBGEN_VERTEX,
	Q3RGBGEN_WAVE,
	Q3RGBGEN_COUNT
}
q3rgbgen_t;

typedef enum q3alphagen_e
{
	Q3ALPHAGEN_IDENTITY,
	Q3ALPHAGEN_CONST,
	Q3ALPHAGEN_ENTITY,
	Q3ALPHAGEN_LIGHTINGSPECULAR,
	Q3ALPHAGEN_ONEMINUSENTITY,
	Q3ALPHAGEN_ONEMINUSVERTEX,
	Q3ALPHAGEN_PORTAL,
	Q3ALPHAGEN_VERTEX,
	Q3ALPHAGEN_WAVE,
	Q3ALPHAGEN_COUNT
}
q3alphagen_t;

typedef enum q3tcgen_e
{
	Q3TCGEN_NONE,
	Q3TCGEN_TEXTURE,               
	Q3TCGEN_ENVIRONMENT,          
	Q3TCGEN_LIGHTMAP,
	Q3TCGEN_VECTOR,
	Q3TCGEN_COUNT
}
q3tcgen_t;

typedef enum q3tcmod_e
{
	Q3TCMOD_NONE,
	Q3TCMOD_ENTITYTRANSLATE,
	Q3TCMOD_ROTATE,
	Q3TCMOD_SCALE,
	Q3TCMOD_SCROLL,
	Q3TCMOD_STRETCH,
	Q3TCMOD_TRANSFORM,
	Q3TCMOD_TURBULENT,
	Q3TCMOD_PAGE,
	Q3TCMOD_COUNT
}
q3tcmod_t;

typedef struct q3shaderinfo_layer_rgbgen_s
{
	q3rgbgen_t rgbgen;
	float parms[Q3RGBGEN_MAXPARMS];
	q3wavefunc_t wavefunc;
	float waveparms[Q3WAVEPARMS];
}
q3shaderinfo_layer_rgbgen_t;

typedef struct q3shaderinfo_layer_alphagen_s
{
	q3alphagen_t alphagen;
	float parms[Q3ALPHAGEN_MAXPARMS];
	q3wavefunc_t wavefunc;
	float waveparms[Q3WAVEPARMS];
}
q3shaderinfo_layer_alphagen_t;

typedef struct q3shaderinfo_layer_tcgen_s
{
	q3tcgen_t tcgen;
	float parms[Q3TCGEN_MAXPARMS];
}
q3shaderinfo_layer_tcgen_t;

typedef struct q3shaderinfo_layer_tcmod_s
{
	q3tcmod_t tcmod;
	float parms[Q3TCMOD_MAXPARMS];
	q3wavefunc_t wavefunc;
	float waveparms[Q3WAVEPARMS];
}
q3shaderinfo_layer_tcmod_t;

typedef struct q3shaderinfo_layer_s
{
	int alphatest;
	int clampmap;
	float framerate;
	int numframes;
	int dptexflags;
	char** texturename;
	int blendfunc[2];
	q3shaderinfo_layer_rgbgen_t rgbgen;
	q3shaderinfo_layer_alphagen_t alphagen;
	q3shaderinfo_layer_tcgen_t tcgen;
	q3shaderinfo_layer_tcmod_t tcmods[Q3MAXTCMODS];
}
q3shaderinfo_layer_t;

typedef struct q3shaderinfo_deform_s
{
	q3deform_t deform;
	float parms[Q3DEFORM_MAXPARMS];
	q3wavefunc_t wavefunc;
	float waveparms[Q3WAVEPARMS];
}
q3shaderinfo_deform_t;

typedef enum dpoffsetmapping_technique_s
{
	OFFSETMAPPING_OFF,			       
	OFFSETMAPPING_DEFAULT,		           
	OFFSETMAPPING_LINEAR,		         
	OFFSETMAPPING_RELIEF		         
}dpoffsetmapping_technique_t;

typedef enum dptransparentsort_category_e
{
	TRANSPARENTSORT_SKY,
	TRANSPARENTSORT_DISTANCE,
	TRANSPARENTSORT_HUD,
}dptransparentsortcategory_t;

typedef struct q3shaderinfo_s
{
	char name[Q3PATHLENGTH];
#define Q3SHADERINFO_COMPARE_START surfaceparms
	int surfaceparms;
	int surfaceflags;
	int textureflags;
	int numlayers;
	qboolean lighting;
	qboolean vertexalpha;
	qboolean textureblendalpha;
	q3shaderinfo_layer_t layers[Q3SHADER_MAXLAYERS];
	char skyboxname[Q3PATHLENGTH];
	q3shaderinfo_deform_t deforms[Q3MAXDEFORMS];

	                         

	                 
	qboolean dpnortlight;
	qboolean dpshadow;
	qboolean dpnoshadow;

	                                                 
	qboolean dpmeshcollisions;

	                                   
	qboolean dpshaderkill;

	                  
	char dpreflectcube[Q3PATHLENGTH];

	             
	float reflectmin;                                                                                      
	float reflectmax;                                                                                          
	float refractfactor;                                                                
	vec4_t refractcolor4f;                                                     
	float reflectfactor;                                                                
	vec4_t reflectcolor4f;                                                     
	float r_water_wateralpha;                                                         
	float r_water_waterscroll[2];                                                

	                
	dpoffsetmapping_technique_t offsetmapping;
	float offsetscale;
	float offsetbias;                                                                           

	                                                           
	float biaspolygonoffset, biaspolygonfactor;

	                            
	dptransparentsortcategory_t transparentsort;

	        
	float specularscalemod;
	float specularpowermod;

	                              
	float rtlightambient;
#define Q3SHADERINFO_COMPARE_END rtlightambient
}
q3shaderinfo_t;

typedef struct texture_shaderpass_s
{
	qboolean alphatest;                                    
	float framerate;
	int numframes;
	skinframe_t *skinframes[TEXTURE_MAXFRAMES];
	int blendfunc[2];
	q3shaderinfo_layer_rgbgen_t rgbgen;
	q3shaderinfo_layer_alphagen_t alphagen;
	q3shaderinfo_layer_tcgen_t tcgen;
	q3shaderinfo_layer_tcmod_t tcmods[Q3MAXTCMODS];
}
texture_shaderpass_t;

typedef enum texturelayertype_e
{
	TEXTURELAYERTYPE_INVALID,
	TEXTURELAYERTYPE_LITTEXTURE,
	TEXTURELAYERTYPE_TEXTURE,
	TEXTURELAYERTYPE_FOG
}
texturelayertype_t;

typedef struct texturelayer_s
{
	texturelayertype_t type;
	qboolean depthmask;
	int blendfunc1;
	int blendfunc2;
	rtexture_t *texture;
	matrix4x4_t texmatrix;
	vec4_t color;
}
texturelayer_t;

typedef struct texture_s
{
	        
	       
	                
	       
	unsigned int width, height;
	              
	                     

	                      
	int basematerialflags;
	                                                      
	int currentmaterialflags;
	                                              
	float basealpha;

	                                                   
	                                                               
	float biaspolygonfactor;
	float biaspolygonoffset;

	                                                                                 
	skinframe_t *currentskinframe;
	                                                                                   
	skinframe_t *backgroundcurrentskinframe;

	                                                  
	int anim_total[2];
	                                                         
	                                  
	struct texture_s *anim_frames[2][10];
	                                                                                                     
	                                                                
	int animated;

	                                                    
	int update_lastrenderframe;
	void *update_lastrenderentity;
	                                                                                                      
	float currentalpha;
	                                         
	struct texture_s *currentframe;
	                                                              
	matrix4x4_t currenttexmatrix;
	matrix4x4_t currentbackgroundtexmatrix;

	                             
	q3shaderinfo_deform_t deforms[Q3MAXDEFORMS];
	texture_shaderpass_t *shaderpasses[Q3SHADER_MAXLAYERS];                                  
	texture_shaderpass_t *materialshaderpass;                                          
	texture_shaderpass_t *backgroundshaderpass;                                          
	unsigned char startpreshaderpass;                               
	unsigned char endpreshaderpass;                             
	unsigned char startpostshaderpass;                               
	unsigned char endpostshaderpass;                              

	qboolean colormapping;
	rtexture_t *basetexture;                                             
	rtexture_t *pantstexture;                             
	rtexture_t *shirttexture;                             
	rtexture_t *nmaptexture;                                
	rtexture_t *glosstexture;                       
	rtexture_t *glowtexture;                           
	rtexture_t *fogtexture;                                             
	rtexture_t *reflectmasktexture;                             
	rtexture_t *reflectcubetexture;                            
	rtexture_t *backgroundbasetexture;                                             
	rtexture_t *backgroundnmaptexture;                                
	rtexture_t *backgroundglosstexture;                       
	rtexture_t *backgroundglowtexture;                           
	float specularpower;

	                                                                                       
	                                                                           
	                                                           
	                                                                                                 
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
	                                                          
	float render_colormap_pants[3];
	                                                          
	float render_colormap_shirt[3];

	                  
	int customblendfunc[2];

	int currentnumlayers;
	texturelayer_t currentlayers[16];

	        
	char name[64];
	int surfaceflags;
	int supercontents;

	        
	                                                                        
	                                       
	int q2flags;
	int q2value;
	int q2contents;

	        
	                                                                                                               
	struct texture_s *skynoshadowtexture;

	             
	float reflectmin;                                                                                      
	float reflectmax;                                                                                          
	float refractfactor;                                                                
	vec4_t refractcolor4f;                                                     
	float reflectfactor;                                                                
	vec4_t reflectcolor4f;                                                     
	float r_water_wateralpha;                                                         
	float r_water_waterscroll[2];                   
	int camera_entity;                                    

	                
	dpoffsetmapping_technique_t offsetmapping;
	float offsetscale;
	float offsetbias;

	                            
	dptransparentsortcategory_t transparentsort;

	        
	float specularscalemod;
	float specularpowermod;

	                      
	float rtlightambient;
}
 texture_t;

typedef struct mtexinfo_s
{
	float		vecs[2][4];		                    
	int			textureindex;
	int			q1flags;
	int			q2flags;			                           
	int			q2value;			                      
	char		q2texture[32];	                                
	int			q2nexttexinfo;	                                    
}
mtexinfo_t;

typedef struct msurface_lightmapinfo_s
{
	                                                  
	mtexinfo_t *texinfo;         
	                                                                              
	unsigned char styles[MAXLIGHTMAPS];         
	                                                  
	unsigned char *samples;         
	                                                   
	unsigned char *nmapsamples;         
	                                                        
	unsigned char *stainsamples;         
	int texturemins[2];         
	int extents[2];         
	int lightmaporigin[2];         
}
msurface_lightmapinfo_t;

struct q3deffect_s;
typedef struct msurface_s
{
	                                   
	vec3_t mins;
	vec3_t maxs;
	                                    
	texture_t *texture;
	                                                             
	rtexture_t *lightmaptexture;
	                                                                       
	rtexture_t *deluxemaptexture;
	                                                        
	msurface_lightmapinfo_t *lightmapinfo;         
	                           
	struct q3deffect_s *effect;         
	                                                              
	int num_firstcollisiontriangle;
	int *deprecatedq3data_collisionelement3i;         
	float *deprecatedq3data_collisionvertex3f;         
	float *deprecatedq3data_collisionbbox6f;                                                                                             
	float *deprecatedq3data_bbox6f;                                                                                             

	                                                                       
	int num_triangles;                       
	int num_firsttriangle;                  
	int num_vertices;                      
	int num_firstvertex;                

	                                     
	int num_firstshadowmeshtriangle;                                      

	                                                              
	int num_collisiontriangles;         
	int num_collisionvertices;         
	int deprecatedq3num_collisionbboxstride;
	int deprecatedq3num_bboxstride;
	                                                               
	int deprecatedq3collisionmarkframe;                                             

	                                                              
	qboolean included;
}
msurface_t;

#include "matrixlib.h"
#include "bih.h"

#include "model_brush.h"
#include "model_sprite.h"
#include "model_alias.h"

typedef struct model_sprite_s
{
	int				sprnum_type;
	mspriteframe_t	*sprdata_frames;
}
model_sprite_t;

struct trace_s;

typedef struct model_brush_lightstyleinfo_s
{
	int style;
	int value;
	int numsurfaces;
	int *surfacelist;
}
model_brush_lightstyleinfo_t;

typedef struct model_brush_s
{
	                                             
	qboolean ishlbsp;
	                                                                                  
	qboolean isbsp2rmqe;
	                                                                                             
	qboolean isbsp2;
	                                                    
	qboolean isq2bsp;
	                                                    
	qboolean isq3bsp;
	                                                                                     
	qboolean skymasking;
	                                             
	char *entities;

	                                 
	struct model_s *parentmodel;
	                                                                
	int submodel;

	                                                                        
	                     
	int numsubmodels;
	                                    
	struct model_s **submodels;

	int num_planes;
	mplane_t *data_planes;

	int num_nodes;
	mnode_t *data_nodes;

	                                        
	int num_visleafs;
	                                                      
	int num_leafs;
	mleaf_t *data_leafs;

	int num_leafbrushes;
	int *data_leafbrushes;

	int num_leafsurfaces;
	int *data_leafsurfaces;

	int num_portals;
	mportal_t *data_portals;

	int num_portalpoints;
	mvertex_t *data_portalpoints;

	int num_brushes;
	q3mbrush_t *data_brushes;

	int num_brushsides;
	q3mbrushside_t *data_brushsides;

	      
	int num_pvsclusters;
	int num_pvsclusterbytes;
	unsigned char *data_pvsclusters;
	          
	                                                                                          
	                                                            

	                                   
	int num_collisionvertices;
	int num_collisiontriangles;
	float *data_collisionvertex3f;
	int *data_collisionelement3i;

	                                                                                                                                                                         
	shadowmesh_t *shadowmesh;

	                                                                                                            
	shadowmesh_t *collisionmesh;

	                   
	int (*SuperContentsFromNativeContents)(int nativecontents);
	int (*NativeContentsFromSuperContents)(int supercontents);
	unsigned char *(*GetPVS)(struct model_s *model, const vec3_t p);
	int (*FatPVS)(struct model_s *model, const vec3_t org, vec_t radius, unsigned char *pvsbuffer, int pvsbufferlength, qboolean merge);
	int (*BoxTouchingPVS)(struct model_s *model, const unsigned char *pvs, const vec3_t mins, const vec3_t maxs);
	int (*BoxTouchingLeafPVS)(struct model_s *model, const unsigned char *pvs, const vec3_t mins, const vec3_t maxs);
	int (*BoxTouchingVisibleLeafs)(struct model_s *model, const unsigned char *visibleleafs, const vec3_t mins, const vec3_t maxs);
	int (*FindBoxClusters)(struct model_s *model, const vec3_t mins, const vec3_t maxs, int maxclusters, int *clusterlist);
	void (*LightPoint)(struct model_s *model, const vec3_t p, vec3_t ambientcolor, vec3_t diffusecolor, vec3_t diffusenormal);
	void (*FindNonSolidLocation)(struct model_s *model, const vec3_t in, vec3_t out, vec_t radius);
	mleaf_t *(*PointInLeaf)(struct model_s *model, const vec3_t p);
	                                                                           
	void (*AmbientSoundLevelsForPoint)(struct model_s *model, const vec3_t p, unsigned char *out, int outsize);
	void (*RoundUpToHullSize)(struct model_s *cmodel, const vec3_t inmins, const vec3_t inmaxs, vec3_t outmins, vec3_t outmaxs);
	                                                                                                      
	qboolean (*TraceLineOfSight)(struct model_s *model, const vec3_t start, const vec3_t end, const vec3_t acceptmins, const vec3_t acceptmaxs);

	char skybox[MAX_QPATH];

	skinframe_t *solidskyskinframe;
	skinframe_t *alphaskyskinframe;

	qboolean supportwateralpha;

	             
	int qw_md4sum;
	int qw_md4sum2;
}
model_brush_t;

typedef struct model_brushq1_s
{
	mmodel_t		*submodels;

	int				numvertexes;
	mvertex_t		*vertexes;

	int				numedges;
	medge_t			*edges;

	int				numtexinfo;
	mtexinfo_t		*texinfo;

	int				numsurfedges;
	int				*surfedges;

	int				numclipnodes;
	mclipnode_t		*clipnodes;

	hull_t			hulls[MAX_MAP_HULLS];

	int				num_compressedpvs;
	unsigned char			*data_compressedpvs;

	int				num_lightdata;
	unsigned char			*lightdata;
	unsigned char			*nmaplightdata;                  

	                                          
	int				num_lightstyles;
	model_brush_lightstyleinfo_t *data_lightstyleinfo;

	                                                                         
	unsigned char *lightmapupdateflags;
	qboolean firstrender;                                                            
}
model_brushq1_t;

typedef struct model_brushq2_s
{
	int dummy;                                     
}
model_brushq2_t;

typedef struct model_brushq3_s
{
	int num_models;
	q3dmodel_t *data_models;

	                                                  
	int num_vertices;
	float *data_vertex3f;
	float *data_normal3f;
	float *data_texcoordtexture2f;
	float *data_texcoordlightmap2f;
	float *data_color4f;

	                       
	int num_triangles;
	int *data_element3i;

	int num_effects;
	q3deffect_t *data_effects;

	                    
	int num_originallightmaps;
	int num_mergedlightmaps;
	int num_lightmapmergedwidthpower;
	int num_lightmapmergedheightpower;
	int num_lightmapmergedwidthheightdeluxepower;
	int num_lightmapmerge;
	rtexture_t **data_lightmaps;
	rtexture_t **data_deluxemaps;

	                                            
	int num_lightgrid;
	q3dlightgrid_t *data_lightgrid;
	                                                           
	float num_lightgrid_cellsize[3];
	                               
	float num_lightgrid_scale[3];
	                                                   
	int num_lightgrid_imins[3];
	int num_lightgrid_imaxs[3];
	int num_lightgrid_isize[3];
	                                                      
	matrix4x4_t num_lightgrid_indexfromworld;

	                                                                   
	                                                                      
	                                              
	qboolean deluxemapping;
	                                                                       
	                               
	qboolean deluxemapping_modelspace;
	                                                                      
	                                                     
	int lightmapsize;
}
model_brushq3_t;

struct frameblend_s;
struct skeleton_s;

typedef struct model_s
{
	                                                         
	char			name[MAX_QPATH];
	                                            
	qboolean		loaded;
	                                                                            
	qboolean		used;
	                                                                   
	unsigned int	crc;
	                                   
	modtype_t		type;
	                              
	mempool_t		*mempool;
	                             
	rtexturepool_t	*texturepool;
	                                                                       
	int				effects;
	                                                     
	int				numframes;
	                                                    
	int				numskins;
	                                            
	synctype_t		synctype;
	                                 
	vec3_t			normalmins, normalmaxs;
	                                                             
	vec3_t			yawmins, yawmaxs;
	                                         
	vec3_t			rotatedmins, rotatedmaxs;
	                                      
	float			radius;
	                                               
	float			radius2;
	                      
	animscene_t		*skinscenes;              
	                      
	animscene_t		*animscenes;               
	                                              
	int				firstmodelsurface;
	int				nummodelsurfaces;
	int				*sortedmodelsurfaces;
	                                                      
	int				firstmodelbrush;
	int				nummodelbrushes;
	                                                        
	bih_t			collision_bih;
	bih_t			render_bih;                                                                    
	                 
	int				num_tags;
	int				num_tagframes;
	aliastag_t		*data_tags;
	                      
	int				num_bones;
	aliasbone_t		*data_bones;
	float			num_posescale;                                                                           
	float			num_poseinvscale;                                                                           
	int				num_poses;
	short			*data_poses7s;                                                                           
	float			*data_baseboneposeinverse;
	                         
	int				num_textures;
	int				max_textures;                                           
	int				num_texturesperskin;
	texture_t		*data_textures;
	qboolean		wantnormals;
	qboolean		wanttangents;
	                         
	int				num_surfaces;
	int				max_surfaces;                                           
	msurface_t		*data_surfaces;
	                                                          
	msurface_lightmapinfo_t *data_surfaces_lightmapinfo;
	                                   
	surfmesh_t		surfmesh;
	                     
	const char		*modeldatatypestring;
	                                               
	void(*AnimateVertices)(const struct model_s * RESTRICT model, const struct frameblend_s * RESTRICT frameblend, const struct skeleton_s *skeleton, float * RESTRICT vertex3f, float * RESTRICT normal3f, float * RESTRICT svector3f, float * RESTRICT tvector3f);
	                                                            
	void(*DrawSky)(struct entity_render_s *ent);
	                                                                                                 
	void(*DrawAddWaterPlanes)(struct entity_render_s *ent);
	                                               
	void(*Draw)(struct entity_render_s *ent);
	                                                                 
	void(*DrawDepth)(struct entity_render_s *ent);
	                                                                                                              
	void(*DrawDebug)(struct entity_render_s *ent);
	                                                
	void(*DrawPrepass)(struct entity_render_s *ent);
                                                                              
	void(*CompileShadowMap)(struct entity_render_s *ent, vec3_t relativelightorigin, vec3_t relativelightdirection, float lightradius, int numsurfaces, const int *surfacelist);
	                              
	void(*DrawShadowMap)(int side, struct entity_render_s *ent, const vec3_t relativelightorigin, const vec3_t relativelightdirection, float lightradius, int numsurfaces, const int *surfacelist, const unsigned char *surfacesides, const vec3_t lightmins, const vec3_t lightmaxs);
	                                                                                                      
	void(*GetLightInfo)(struct entity_render_s *ent, vec3_t relativelightorigin, float lightradius, vec3_t outmins, vec3_t outmaxs, int *outleaflist, unsigned char *outleafpvs, int *outnumleafspointer, int *outsurfacelist, unsigned char *outsurfacepvs, int *outnumsurfacespointer, unsigned char *outshadowtrispvs, unsigned char *outlighttrispvs, unsigned char *visitingleafpvs, int numfrustumplanes, const mplane_t *frustumplanes, qboolean noocclusion);
	                                                              
	void(*CompileShadowVolume)(struct entity_render_s *ent, vec3_t relativelightorigin, vec3_t relativelightdirection, float lightradius, int numsurfaces, const int *surfacelist);
	                                                           
	void(*DrawShadowVolume)(struct entity_render_s *ent, const vec3_t relativelightorigin, const vec3_t relativelightdirection, float lightradius, int numsurfaces, const int *surfacelist, const vec3_t lightmins, const vec3_t lightmaxs);
	                                                 
	void(*DrawLight)(struct entity_render_s *ent, int numsurfaces, const int *surfacelist, const unsigned char *trispvs);
	                                 
	void (*TraceBox)(struct model_s *model, const struct frameblend_s *frameblend, const struct skeleton_s *skeleton, struct trace_s *trace, const vec3_t start, const vec3_t boxmins, const vec3_t boxmaxs, const vec3_t end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask);
	void (*TraceBrush)(struct model_s *model, const struct frameblend_s *frameblend, const struct skeleton_s *skeleton, struct trace_s *trace, struct colbrushf_s *start, struct colbrushf_s *end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask);
	                                 
	void (*TraceLine)(struct model_s *model, const struct frameblend_s *frameblend, const struct skeleton_s *skeleton, struct trace_s *trace, const vec3_t start, const vec3_t end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask);
	                                                             
	void (*TracePoint)(struct model_s *model, const struct frameblend_s *frameblend, const struct skeleton_s *skeleton, struct trace_s *trace, const vec3_t start, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask);
	                                                        
	int (*PointSuperContents)(struct model_s *model, int frame, const vec3_t point);
	                                                                                                       
	void (*TraceLineAgainstSurfaces)(struct model_s *model, const struct frameblend_s *frameblend, const struct skeleton_s *skeleton, struct trace_s *trace, const vec3_t start, const vec3_t end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask);
	                                          
	model_sprite_t	sprite;
	model_brush_t	brush;
	model_brushq1_t	brushq1;
	model_brushq2_t	brushq2;
	model_brushq3_t	brushq3;
	                                                                                   
	int soundfromcenter;

	                                                                          
	qboolean lit;
	float lightmapscale;
}
dp_model_t;

                                                                              

                
extern dp_model_t *loadmodel;
extern unsigned char *mod_base;
                        
                                  
                      
extern cvar_t r_fullbrights;
extern cvar_t r_enableshadowvolumes;

void Mod_Init (void);
void Mod_Reload (void);
dp_model_t *Mod_LoadModel(dp_model_t *mod, qboolean crash, qboolean checkdisk);
dp_model_t *Mod_FindName (const char *name, const char *parentname);
dp_model_t *Mod_ForName (const char *name, qboolean crash, qboolean checkdisk, const char *parentname);
void Mod_UnloadModel (dp_model_t *mod);

void Mod_ClearUsed(void);
void Mod_PurgeUnused(void);
void Mod_RemoveStaleWorldModels(dp_model_t *skip);                             

extern dp_model_t *loadmodel;
extern char loadname[32];	                

int Mod_BuildVertexRemapTableFromElements(int numelements, const int *elements, int numvertices, int *remapvertices);
void Mod_BuildTriangleNeighbors(int *neighbors, const int *elements, int numtriangles);
void Mod_ValidateElements(int *elements, int numtriangles, int firstvertex, int numverts, const char *filename, int fileline);
void Mod_BuildNormals(int firstvertex, int numvertices, int numtriangles, const float *vertex3f, const int *elements, float *normal3f, qboolean areaweighting);
void Mod_BuildTextureVectorsFromNormals(int firstvertex, int numvertices, int numtriangles, const float *vertex3f, const float *texcoord2f, const float *normal3f, const int *elements, float *svector3f, float *tvector3f, qboolean areaweighting);

void Mod_AllocSurfMesh(mempool_t *mempool, int numvertices, int numtriangles, qboolean lightmapoffsets, qboolean vertexcolors, qboolean neighbors);
void Mod_MakeSortedSurfaces(dp_model_t *mod);

                                                                      
                                                  
void Mod_BuildVBOs(void);

shadowmesh_t *Mod_ShadowMesh_Alloc(mempool_t *mempool, int maxverts, int maxtriangles, rtexture_t *map_diffuse, rtexture_t *map_specular, rtexture_t *map_normal, int light, int neighbors, int expandable);
shadowmesh_t *Mod_ShadowMesh_ReAlloc(mempool_t *mempool, shadowmesh_t *oldmesh, int light, int neighbors);
int Mod_ShadowMesh_AddVertex(shadowmesh_t *mesh, float *vertex14f);
void Mod_ShadowMesh_AddTriangle(mempool_t *mempool, shadowmesh_t *mesh, rtexture_t *map_diffuse, rtexture_t *map_specular, rtexture_t *map_normal, float *vertex14f);
void Mod_ShadowMesh_AddMesh(mempool_t *mempool, shadowmesh_t *mesh, rtexture_t *map_diffuse, rtexture_t *map_specular, rtexture_t *map_normal, const float *vertex3f, const float *svector3f, const float *tvector3f, const float *normal3f, const float *texcoord2f, int numtris, const int *element3i);
shadowmesh_t *Mod_ShadowMesh_Begin(mempool_t *mempool, int maxverts, int maxtriangles, rtexture_t *map_diffuse, rtexture_t *map_specular, rtexture_t *map_normal, int light, int neighbors, int expandable);
shadowmesh_t *Mod_ShadowMesh_Finish(mempool_t *mempool, shadowmesh_t *firstmesh, qboolean light, qboolean neighbors, qboolean createvbo);
void Mod_ShadowMesh_CalcBBox(shadowmesh_t *firstmesh, vec3_t mins, vec3_t maxs, vec3_t center, float *radius);
void Mod_ShadowMesh_Free(shadowmesh_t *mesh);

void Mod_CreateCollisionMesh(dp_model_t *mod);

void Mod_FreeQ3Shaders(void);
void Mod_LoadQ3Shaders(void);
q3shaderinfo_t *Mod_LookupQ3Shader(const char *name);
qboolean Mod_LoadTextureFromQ3Shader(texture_t *texture, const char *name, qboolean warnmissing, qboolean fallback, int defaulttexflags);
texture_shaderpass_t *Mod_CreateShaderPass(skinframe_t *skinframe);
texture_shaderpass_t *Mod_CreateShaderPassFromQ3ShaderLayer(q3shaderinfo_layer_t *layer, int layerindex, int texflags, const char *texturename);
                                                                                                
void Mod_LoadCustomMaterial(texture_t *texture, const char *name, int supercontents, int materialflags, skinframe_t *skinframe);

extern cvar_t r_mipskins;
extern cvar_t r_mipnormalmaps;

typedef struct skinfileitem_s
{
	struct skinfileitem_s *next;
	char name[MAX_QPATH];
	char replacement[MAX_QPATH];
}
skinfileitem_t;

typedef struct skinfile_s
{
	struct skinfile_s *next;
	skinfileitem_t *items;
}
skinfile_t;

skinfile_t *Mod_LoadSkinFiles(void);
void Mod_FreeSkinFiles(skinfile_t *skinfile);
int Mod_CountSkinFiles(skinfile_t *skinfile);
void Mod_BuildAliasSkinsFromSkinFiles(texture_t *skin, skinfile_t *skinfile, const char *meshname, const char *shadername);

void Mod_SnapVertices(int numcomponents, int numvertices, float *vertices, float snap);
int Mod_RemoveDegenerateTriangles(int numtriangles, const int *inelement3i, int *outelement3i, const float *vertex3f);
void Mod_VertexRangeFromElements(int numelements, const int *elements, int *firstvertexpointer, int *lastvertexpointer);

typedef struct mod_alloclightmap_row_s
{
	int rowY;
	int currentX;
}
mod_alloclightmap_row_t;

typedef struct mod_alloclightmap_state_s
{
	int width;
	int height;
	int currentY;
	mod_alloclightmap_row_t *rows;
}
mod_alloclightmap_state_t;

void Mod_AllocLightmap_Init(mod_alloclightmap_state_t *state, mempool_t *mempool, int width, int height);
void Mod_AllocLightmap_Free(mod_alloclightmap_state_t *state);
void Mod_AllocLightmap_Reset(mod_alloclightmap_state_t *state);
qboolean Mod_AllocLightmap_Block(mod_alloclightmap_state_t *state, int blockwidth, int blockheight, int *outx, int *outy);

             
void Mod_BrushInit(void);
                                        
int Mod_Q1BSP_NativeContentsFromSuperContents(int supercontents);
int Mod_Q1BSP_SuperContentsFromNativeContents(int nativecontents);
                                                            
int Mod_Q2BSP_SuperContentsFromNativeContents(int nativecontents);
int Mod_Q2BSP_NativeContentsFromSuperContents(int supercontents);

                                                                           
struct entity_render_s;
void R_Q1BSP_DrawAddWaterPlanes(struct entity_render_s *ent);
void R_Q1BSP_DrawSky(struct entity_render_s *ent);
void R_Q1BSP_Draw(struct entity_render_s *ent);
void R_Q1BSP_DrawDepth(struct entity_render_s *ent);
void R_Q1BSP_DrawDebug(struct entity_render_s *ent);
void R_Q1BSP_DrawPrepass(struct entity_render_s *ent);
void R_Q1BSP_GetLightInfo(struct entity_render_s *ent, vec3_t relativelightorigin, float lightradius, vec3_t outmins, vec3_t outmaxs, int *outleaflist, unsigned char *outleafpvs, int *outnumleafspointer, int *outsurfacelist, unsigned char *outsurfacepvs, int *outnumsurfacespointer, unsigned char *outshadowtrispvs, unsigned char *outlighttrispvs, unsigned char *visitingleafpvs, int numfrustumplanes, const mplane_t *frustumplanes, qboolean noocclusion);
void R_Q1BSP_CompileShadowMap(struct entity_render_s *ent, vec3_t relativelightorigin, vec3_t relativelightdirection, float lightradius, int numsurfaces, const int *surfacelist);
void R_Q1BSP_DrawShadowMap(int side, struct entity_render_s *ent, const vec3_t relativelightorigin, const vec3_t relativelightdirection, float lightradius, int modelnumsurfaces, const int *modelsurfacelist, const unsigned char *surfacesides, const vec3_t lightmins, const vec3_t lightmaxs);
void R_Q1BSP_CompileShadowVolume(struct entity_render_s *ent, vec3_t relativelightorigin, vec3_t relativelightdirection, float lightradius, int numsurfaces, const int *surfacelist);
void R_Q1BSP_DrawShadowVolume(struct entity_render_s *ent, const vec3_t relativelightorigin, const vec3_t relativelightdirection, float lightradius, int numsurfaces, const int *surfacelist, const vec3_t lightmins, const vec3_t lightmaxs);
void R_Q1BSP_DrawLight(struct entity_render_s *ent, int numsurfaces, const int *surfacelist, const unsigned char *trispvs);

                                                                   
void Mod_Mesh_Create(dp_model_t *mod, const char *name);
void Mod_Mesh_Destroy(dp_model_t *mod);
void Mod_Mesh_Reset(dp_model_t *mod);
texture_t *Mod_Mesh_GetTexture(dp_model_t *mod, const char *name);
msurface_t *Mod_Mesh_AddSurface(dp_model_t *mod, texture_t *tex);
int Mod_Mesh_IndexForVertex(dp_model_t *mod, msurface_t *surf, float x, float y, float z, float nx, float ny, float nz, float s, float t, float u, float v, float r, float g, float b, float a);
void Mod_Mesh_AddTriangle(dp_model_t *mod, msurface_t *surf, int e0, int e1, int e2);
void Mod_Mesh_Finalize(dp_model_t *mod);

                                                           
void Mod_CollisionBIH_TracePoint(dp_model_t *model, const struct frameblend_s *frameblend, const skeleton_t *skeleton, struct trace_s *trace, const vec3_t start, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask);
void Mod_CollisionBIH_TraceLine(dp_model_t *model, const struct frameblend_s *frameblend, const skeleton_t *skeleton, struct trace_s *trace, const vec3_t start, const vec3_t end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask);
void Mod_CollisionBIH_TraceBox(dp_model_t *model, const struct frameblend_s *frameblend, const skeleton_t *skeleton, struct trace_s *trace, const vec3_t start, const vec3_t boxmins, const vec3_t boxmaxs, const vec3_t end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask);
void Mod_CollisionBIH_TraceBrush(dp_model_t *model, const struct frameblend_s *frameblend, const skeleton_t *skeleton, struct trace_s *trace, struct colbrushf_s *start, struct colbrushf_s *end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask);
void Mod_CollisionBIH_TracePoint_Mesh(dp_model_t *model, const struct frameblend_s *frameblend, const skeleton_t *skeleton, struct trace_s *trace, const vec3_t start, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask);
qboolean Mod_CollisionBIH_TraceLineOfSight(struct model_s *model, const vec3_t start, const vec3_t end, const vec3_t acceptmins, const vec3_t acceptmaxs);
int Mod_CollisionBIH_PointSuperContents(struct model_s *model, int frame, const vec3_t point);
int Mod_CollisionBIH_PointSuperContents_Mesh(struct model_s *model, int frame, const vec3_t point);
bih_t *Mod_MakeCollisionBIH(dp_model_t *model, qboolean userendersurfaces, bih_t *out);

               
struct frameblend_s;
struct skeleton_s;
void Mod_AliasInit(void);
int Mod_Alias_GetTagMatrix(const dp_model_t *model, const struct frameblend_s *frameblend, const struct skeleton_s *skeleton, int tagindex, matrix4x4_t *outmatrix);
int Mod_Alias_GetTagIndexForName(const dp_model_t *model, unsigned int skin, const char *tagname);
int Mod_Alias_GetExtendedTagInfoForIndex(const dp_model_t *model, unsigned int skin, const struct frameblend_s *frameblend, const struct skeleton_s *skeleton, int tagindex, int *parentindex, const char **tagname, matrix4x4_t *tag_localmatrix);

void Mod_Skeletal_FreeBuffers(void);

                
void Mod_SpriteInit(void);

          
void Mod_Q1BSP_Load(dp_model_t *mod, void *buffer, void *bufferend);
void Mod_IBSP_Load(dp_model_t *mod, void *buffer, void *bufferend);
void Mod_MAP_Load(dp_model_t *mod, void *buffer, void *bufferend);
void Mod_OBJ_Load(dp_model_t *mod, void *buffer, void *bufferend);
void Mod_IDP0_Load(dp_model_t *mod, void *buffer, void *bufferend);
void Mod_IDP2_Load(dp_model_t *mod, void *buffer, void *bufferend);
void Mod_IDP3_Load(dp_model_t *mod, void *buffer, void *bufferend);
void Mod_ZYMOTICMODEL_Load(dp_model_t *mod, void *buffer, void *bufferend);
void Mod_DARKPLACESMODEL_Load(dp_model_t *mod, void *buffer, void *bufferend);
void Mod_PSKMODEL_Load(dp_model_t *mod, void *buffer, void *bufferend);
void Mod_IDSP_Load(dp_model_t *mod, void *buffer, void *bufferend);
void Mod_IDS2_Load(dp_model_t *mod, void *buffer, void *bufferend);
void Mod_INTERQUAKEMODEL_Load(dp_model_t *mod, void *buffer, void *bufferend);

#endif	                 

