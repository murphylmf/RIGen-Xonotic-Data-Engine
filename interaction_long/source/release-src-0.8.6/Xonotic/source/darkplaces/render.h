  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

#ifndef RENDER_H
#define RENDER_H

#include "svbsp.h"

                 
extern float ixtable[4096];

            
void FOG_clear(void);

            
extern cvar_t r_sky;
extern cvar_t r_skyscroll1;
extern cvar_t r_skyscroll2;
extern cvar_t r_sky_scissor;
extern cvar_t r_q3bsp_renderskydepth;
extern int skyrenderlater, skyrendermasked;
extern int skyscissor[4];
int R_SetSkyBox(const char *sky);
void R_SkyStartFrame(void);
void R_Sky(void);
void R_ResetSkyBox(void);

                          
void SHOWLMP_decodehide(void);
void SHOWLMP_decodeshow(void);
void SHOWLMP_drawall(void);

                         
extern int r_timereport_active;

                 
extern cvar_t r_ambient;
extern cvar_t gl_flashblend;

            
extern cvar_t r_novis;

extern cvar_t r_trippy;
extern cvar_t r_fxaa;

extern cvar_t r_lerpsprites;
extern cvar_t r_lerpmodels;
extern cvar_t r_lerplightstyles;
extern cvar_t r_waterscroll;

extern cvar_t developer_texturelogging;

                                                                   
extern svbsp_t r_svbsp;

typedef struct rmesh_s
{
	                        
	int maxvertices;
	int numvertices;
	float *vertex3f;
	float *svector3f;
	float *tvector3f;
	float *normal3f;
	float *texcoord2f;
	float *texcoordlightmap2f;
	float *color4f;
	                         
	int maxtriangles;
	int numtriangles;
	int *element3i;
	int *neighbor3i;
	                   
	float epsilon2;
}
rmesh_t;

                                 
void R_ModulateColors(float *in, float *out, int verts, float r, float g, float b);
void R_FillColors(float *out, int verts, float r, float g, float b, float a);
void R_Mesh_AddPolygon3f(rmesh_t *mesh, int numvertices, float *vertex3f);
void R_Mesh_AddBrushMeshFromPlanes(rmesh_t *mesh, int numplanes, mplane_t *planes);

#define	TOP_RANGE		16			                         
#define	BOTTOM_RANGE	96

                                                                               

extern cvar_t r_nearclip;

                                                 
extern cvar_t r_showoverdraw;
extern cvar_t r_showtris;
extern cvar_t r_shownormals;
extern cvar_t r_showlighting;
extern cvar_t r_showshadowvolumes;
extern cvar_t r_showcollisionbrushes;
extern cvar_t r_showcollisionbrushes_polygonfactor;
extern cvar_t r_showcollisionbrushes_polygonoffset;
extern cvar_t r_showdisabledepthtest;

extern cvar_t r_drawentities;
extern cvar_t r_draw2d;
extern qboolean r_draw2d_force;
extern cvar_t r_drawviewmodel;
extern cvar_t r_drawworld;
extern cvar_t r_speeds;
extern cvar_t r_fullbright;
extern cvar_t r_wateralpha;
extern cvar_t r_dynamic;

void R_UpdateVariables(void);                                                                                
void R_RenderView(void);                                                                                 
void R_RenderView_UpdateViewVectors(void);                                                                            

typedef enum r_refdef_scene_type_s {
	RST_CLIENT,
	RST_MENU,
	RST_COUNT
} r_refdef_scene_type_t;

void R_SelectScene( r_refdef_scene_type_t scenetype );
r_refdef_scene_t * R_GetScenePointer( r_refdef_scene_type_t scenetype );

void R_SkinFrame_PrepareForPurge(void);
void R_SkinFrame_MarkUsed(skinframe_t *skinframe);
void R_SkinFrame_PurgeSkinFrame(skinframe_t *skinframe);
void R_SkinFrame_Purge(void);
                                               
skinframe_t *R_SkinFrame_FindNextByName( skinframe_t *last, const char *name );
skinframe_t *R_SkinFrame_Find(const char *name, int textureflags, int comparewidth, int compareheight, int comparecrc, qboolean add);
skinframe_t *R_SkinFrame_LoadExternal(const char *name, int textureflags, qboolean complain);
skinframe_t *R_SkinFrame_LoadInternalBGRA(const char *name, int textureflags, const unsigned char *skindata, int width, int height, qboolean sRGB);
skinframe_t *R_SkinFrame_LoadInternalQuake(const char *name, int textureflags, int loadpantsandshirt, int loadglowtexture, const unsigned char *skindata, int width, int height);
skinframe_t *R_SkinFrame_LoadInternal8bit(const char *name, int textureflags, const unsigned char *skindata, int width, int height, const unsigned int *palette, const unsigned int *alphapalette);
skinframe_t *R_SkinFrame_LoadMissing(void);

rtexture_t *R_GetCubemap(const char *basename);

void R_View_WorldVisibility(qboolean forcenovis);
void R_DrawDecals(void);
void R_DrawParticles(void);
void R_DrawExplosions(void);

#define gl_solid_format 3
#define gl_alpha_format 4

int R_CullBox(const vec3_t mins, const vec3_t maxs);
int R_CullBoxCustomPlanes(const vec3_t mins, const vec3_t maxs, int numplanes, const mplane_t *planes);
qboolean R_CanSeeBox(int numsamples, vec_t eyejitter, vec_t entboxenlarge, vec3_t eye, vec3_t entboxmins, vec3_t entboxmaxs);

#include "r_modules.h"

#include "meshqueue.h"

                               
void R_FrameData_Reset(void);
                                                                                 
void R_FrameData_NewFrame(void);
                                                    
void *R_FrameData_Alloc(size_t size);
                                                             
void *R_FrameData_Store(size_t size, void *data);
                                                                                      
void R_FrameData_SetMark(void);
                                                        
void R_FrameData_ReturnToMark(void);

                                                                         
                                                                       
typedef enum r_bufferdata_type_e
{
	R_BUFFERDATA_VERTEX,                  
	R_BUFFERDATA_INDEX16,                                             
	R_BUFFERDATA_INDEX32,                                             
	R_BUFFERDATA_UNIFORM,                   
	R_BUFFERDATA_COUNT                                     
}
r_bufferdata_type_t;

                                                 
void R_BufferData_Reset(void);
                                           
void R_BufferData_NewFrame(void);
                                                                                                                                
r_meshbuffer_t *R_BufferData_Store(size_t size, const void *data, r_bufferdata_type_t type, int *returnbufferoffset);

                               
void R_AnimCache_Free(void);
                                                             
void R_AnimCache_ClearCache(void);
                                                                                                           
qboolean R_AnimCache_GetEntity(entity_render_t *ent, qboolean wantnormals, qboolean wanttangents);
                                                           
void R_AnimCache_CacheVisibleEntities(void);

#include "r_lerpanim.h"

extern cvar_t r_render;
extern cvar_t r_renderview;
extern cvar_t r_waterwarp;

extern cvar_t r_textureunits;

extern cvar_t r_glsl_offsetmapping;
extern cvar_t r_glsl_offsetmapping_reliefmapping;
extern cvar_t r_glsl_offsetmapping_scale;
extern cvar_t r_glsl_offsetmapping_lod;
extern cvar_t r_glsl_offsetmapping_lod_distance;
extern cvar_t r_glsl_deluxemapping;

extern cvar_t gl_polyblend;
extern cvar_t gl_dither;

extern cvar_t cl_deathfade;

extern cvar_t r_smoothnormals_areaweighting;

extern cvar_t r_test;

#include "gl_backend.h"

extern rtexture_t *r_texture_blanknormalmap;
extern rtexture_t *r_texture_white;
extern rtexture_t *r_texture_grey128;
extern rtexture_t *r_texture_black;
extern rtexture_t *r_texture_notexture;
extern rtexture_t *r_texture_whitecube;
extern rtexture_t *r_texture_normalizationcube;
extern rtexture_t *r_texture_fogattenuation;
extern rtexture_t *r_texture_fogheighttexture;

extern unsigned int r_queries[MAX_OCCLUSION_QUERIES];
extern unsigned int r_numqueries;
extern unsigned int r_maxqueries;

void R_TimeReport(const char *name);

          
void R_Stain(const vec3_t origin, float radius, int cr1, int cg1, int cb1, int ca1, int cr2, int cg2, int cb2, int ca2);

void R_CalcBeam_Vertex3f(float *vert, const float *org1, const float *org2, float width);
void R_CalcSprite_Vertex3f(float *vertex3f, const float *origin, const float *left, const float *up, float scalex1, float scalex2, float scaley1, float scaley2);

extern mempool_t *r_main_mempool;

typedef struct rsurfacestate_s
{
	                               
	                                                              
	                                       
	                                                                         
	                
	  
	                                                                        
	                                                                       
	  
	                                                                         
	                       
	  
	                                                                       
	                                                            
	qboolean                    forcecurrenttextureupdate;                                                                                                                              
	qboolean                    modelgeneratedvertex;
	                                                                     
	                                                                        
	                                                                        
	                                                                        
	            
	int                         entityskeletalnumtransforms;                                              
	float                      *entityskeletaltransform3x4;                                        
	const r_meshbuffer_t       *entityskeletaltransform3x4buffer;                  
	int                         entityskeletaltransform3x4offset;
	int                         entityskeletaltransform3x4size;
	float                      *modelvertex3f;
	const r_meshbuffer_t       *modelvertex3f_vertexbuffer;
	int                         modelvertex3f_bufferoffset;
	float                      *modelsvector3f;
	const r_meshbuffer_t       *modelsvector3f_vertexbuffer;
	int                         modelsvector3f_bufferoffset;
	float                      *modeltvector3f;
	const r_meshbuffer_t       *modeltvector3f_vertexbuffer;
	int                         modeltvector3f_bufferoffset;
	float                      *modelnormal3f;
	const r_meshbuffer_t       *modelnormal3f_vertexbuffer;
	int                         modelnormal3f_bufferoffset;
	float                      *modellightmapcolor4f;
	const r_meshbuffer_t       *modellightmapcolor4f_vertexbuffer;
	int                         modellightmapcolor4f_bufferoffset;
	float                      *modeltexcoordtexture2f;
	const r_meshbuffer_t       *modeltexcoordtexture2f_vertexbuffer;
	int                         modeltexcoordtexture2f_bufferoffset;
	float                      *modeltexcoordlightmap2f;
	const r_meshbuffer_t       *modeltexcoordlightmap2f_vertexbuffer;
	int                         modeltexcoordlightmap2f_bufferoffset;
	unsigned char              *modelskeletalindex4ub;
	const r_meshbuffer_t       *modelskeletalindex4ub_vertexbuffer;
	int                         modelskeletalindex4ub_bufferoffset;
	unsigned char              *modelskeletalweight4ub;
	const r_meshbuffer_t       *modelskeletalweight4ub_vertexbuffer;
	int                         modelskeletalweight4ub_bufferoffset;
	r_vertexmesh_t             *modelvertexmesh;
	const r_meshbuffer_t       *modelvertexmesh_vertexbuffer;
	int                         modelvertexmesh_bufferoffset;
	int                        *modelelement3i;
	const r_meshbuffer_t       *modelelement3i_indexbuffer;
	int                         modelelement3i_bufferoffset;
	unsigned short             *modelelement3s;
	const r_meshbuffer_t       *modelelement3s_indexbuffer;
	int                         modelelement3s_bufferoffset;
	int                        *modellightmapoffsets;
	int                         modelnumvertices;
	int                         modelnumtriangles;
	const msurface_t           *modelsurfaces;
	                                   
	                                                                       
	                                                                 
	                                                               
	                                                                    
	                                                                
	qboolean                    batchgeneratedvertex;
	qboolean                    batchmultidraw;
	int                         batchmultidrawnumsurfaces;
	const msurface_t          **batchmultidrawsurfacelist;
	int                         batchfirstvertex;
	int                         batchnumvertices;
	int                         batchfirsttriangle;
	int                         batchnumtriangles;
	r_vertexmesh_t             *batchvertexmesh;
	const r_meshbuffer_t       *batchvertexmesh_vertexbuffer;
	int                         batchvertexmesh_bufferoffset;
	float                      *batchvertex3f;
	const r_meshbuffer_t       *batchvertex3f_vertexbuffer;
	int                         batchvertex3f_bufferoffset;
	float                      *batchsvector3f;
	const r_meshbuffer_t       *batchsvector3f_vertexbuffer;
	int                         batchsvector3f_bufferoffset;
	float                      *batchtvector3f;
	const r_meshbuffer_t       *batchtvector3f_vertexbuffer;
	int                         batchtvector3f_bufferoffset;
	float                      *batchnormal3f;
	const r_meshbuffer_t       *batchnormal3f_vertexbuffer;
	int                         batchnormal3f_bufferoffset;
	float                      *batchlightmapcolor4f;
	const r_meshbuffer_t       *batchlightmapcolor4f_vertexbuffer;
	int                         batchlightmapcolor4f_bufferoffset;
	float                      *batchtexcoordtexture2f;
	const r_meshbuffer_t       *batchtexcoordtexture2f_vertexbuffer;
	int                         batchtexcoordtexture2f_bufferoffset;
	float                      *batchtexcoordlightmap2f;
	const r_meshbuffer_t       *batchtexcoordlightmap2f_vertexbuffer;
	int                         batchtexcoordlightmap2f_bufferoffset;
	unsigned char              *batchskeletalindex4ub;
	const r_meshbuffer_t       *batchskeletalindex4ub_vertexbuffer;
	int                         batchskeletalindex4ub_bufferoffset;
	unsigned char              *batchskeletalweight4ub;
	const r_meshbuffer_t       *batchskeletalweight4ub_vertexbuffer;
	int                         batchskeletalweight4ub_bufferoffset;
	int                        *batchelement3i;
	const r_meshbuffer_t       *batchelement3i_indexbuffer;
	int                         batchelement3i_bufferoffset;
	unsigned short             *batchelement3s;
	const r_meshbuffer_t       *batchelement3s_indexbuffer;
	int                         batchelement3s_bufferoffset;
	int                         batchskeletalnumtransforms;
	float                      *batchskeletaltransform3x4;
	const r_meshbuffer_t       *batchskeletaltransform3x4buffer;                  
	int                         batchskeletaltransform3x4offset;
	int                         batchskeletaltransform3x4size;
	                                                          
	float                      *passcolor4f;
	const r_meshbuffer_t       *passcolor4f_vertexbuffer;
	int                         passcolor4f_bufferoffset;

	                                        
	int ent_skinnum;
	int ent_qwskin;
	int ent_flags;
	int ent_alttextures;                                                     
	double shadertime;                                         
	                                                                      
	matrix4x4_t matrix;
	matrix4x4_t inversematrix;
	                                                                  
	float matrixscale;
	float inversematrixscale;
	                                       
	frameblend_t frameblend[MAX_FRAMEBLENDS];
	skeleton_t *skeleton;
	                               
	vec3_t localvieworigin;
	                                    
	float basepolygonfactor;
	float basepolygonoffset;
	                                    
	texture_t *texture;
	rtexture_t *lightmaptexture;
	rtexture_t *deluxemaptexture;
	                                               
	                             
	qboolean uselightmaptexture;
	                                                              
	float fograngerecip;
	float fogmasktabledistmultiplier;
	float fogplane[4];
	float fogheightfade;
	float fogplaneviewdist;

	                    
	                                 
	const rtlight_t *rtlight;

	                                                    
	vec3_t entitylightorigin;
	                                                                         
	                                       
	matrix4x4_t entitytolight;
	                                                                         
	                                                               
	matrix4x4_t entitytoattenuationxyz;
	                                                       
	matrix4x4_t entitytoattenuationz;

	                                       
	float userwavefunc_param[Q3WAVEFUNC_USER_COUNT];

	                                                                     
	                                                                        
	        
	entity_render_t *entity;
}
rsurfacestate_t;

extern rsurfacestate_t rsurface;

void R_HDR_UpdateIrisAdaptation(const vec3_t point);

void RSurf_ActiveModelEntity(const entity_render_t *ent, qboolean wantnormals, qboolean wanttangents, qboolean prepass);
void RSurf_ActiveCustomEntity(const matrix4x4_t *matrix, const matrix4x4_t *inversematrix, int entflags, double shadertime, float r, float g, float b, float a, int numvertices, const float *vertex3f, const float *texcoord2f, const float *normal3f, const float *svector3f, const float *tvector3f, const float *color4f, int numtriangles, const int *element3i, const unsigned short *element3s, qboolean wantnormals, qboolean wanttangents);
void RSurf_SetupDepthAndCulling(void);

void R_Mesh_ResizeArrays(int newvertices);

texture_t *R_GetCurrentTexture(texture_t *t);
void R_DrawWorldSurfaces(qboolean skysurfaces, qboolean writedepth, qboolean depthonly, qboolean debug, qboolean prepass);
void R_DrawModelSurfaces(entity_render_t *ent, qboolean skysurfaces, qboolean writedepth, qboolean depthonly, qboolean debug, qboolean prepass);
void R_AddWaterPlanes(entity_render_t *ent);
void R_DrawCustomSurface(skinframe_t *skinframe, const matrix4x4_t *texmatrix, int materialflags, int firstvertex, int numvertices, int firsttriangle, int numtriangles, qboolean writedepth, qboolean prepass);
void R_DrawCustomSurface_Texture(texture_t *texture, const matrix4x4_t *texmatrix, int materialflags, int firstvertex, int numvertices, int firsttriangle, int numtriangles, qboolean writedepth, qboolean prepass);

#define BATCHNEED_VERTEXMESH_VERTEX      (1<< 1)                                   
#define BATCHNEED_VERTEXMESH_NORMAL      (1<< 2)                                                                                                                   
#define BATCHNEED_VERTEXMESH_VECTOR      (1<< 3)                                                                                                                                                
#define BATCHNEED_VERTEXMESH_VERTEXCOLOR (1<< 4)                                                                                                                                
#define BATCHNEED_VERTEXMESH_TEXCOORD    (1<< 5)                                                                                                                                
#define BATCHNEED_VERTEXMESH_LIGHTMAP    (1<< 6)                                                                                                                                
#define BATCHNEED_VERTEXMESH_SKELETAL    (1<< 7)                                                           
#define BATCHNEED_ARRAY_VERTEX           (1<< 8)                                                       
#define BATCHNEED_ARRAY_NORMAL           (1<< 9)                                                                                                                   
#define BATCHNEED_ARRAY_VECTOR           (1<<10)                                                                                                                                                
#define BATCHNEED_ARRAY_VERTEXCOLOR      (1<<11)                                                                                                                                
#define BATCHNEED_ARRAY_TEXCOORD         (1<<12)                                                                                                                                
#define BATCHNEED_ARRAY_LIGHTMAP         (1<<13)                                                                                                                                
#define BATCHNEED_ARRAY_SKELETAL         (1<<14)                                                           
#define BATCHNEED_NOGAPS                 (1<<15)                                                                     
#define BATCHNEED_ALLOWMULTIDRAW         (1<<16)                        
void RSurf_PrepareVerticesForBatch(int batchneed, int texturenumsurfaces, const msurface_t **texturesurfacelist);
void RSurf_DrawBatch(void);

void R_DecalSystem_SplatEntities(const vec3_t org, const vec3_t normal, float r, float g, float b, float a, float s1, float t1, float s2, float t2, float size);

typedef enum rsurfacepass_e
{
	RSURFPASS_BASE,
	RSURFPASS_BACKGROUND,
	RSURFPASS_RTLIGHT,
	RSURFPASS_DEFERREDGEOMETRY
}
rsurfacepass_t;

void R_SetupShader_Generic(rtexture_t *first, rtexture_t *second, int texturemode, int rgbscale, qboolean usegamma, qboolean notrippy, qboolean suppresstexalpha);
void R_SetupShader_Generic_NoTexture(qboolean usegamma, qboolean notrippy);
void R_SetupShader_DepthOrShadow(qboolean notrippy, qboolean depthrgb, qboolean skeletal);
void R_SetupShader_Surface(const float ambientcolor[3], const float diffusecolor[3], const float specularcolor[3], rsurfacepass_t rsurfacepass, int texturenumsurfaces, const msurface_t **texturesurfacelist, void *waterplane, qboolean notrippy);
void R_SetupShader_DeferredLight(const rtlight_t *rtlight);

typedef struct r_waterstate_waterplane_s
{
	rtexture_t *texture_refraction;                                                       
	rtexture_t *texture_reflection;                                                       
	rtexture_t *texture_camera;                       
	int fbo_refraction;
	int fbo_reflection;
	int fbo_camera;
	mplane_t plane;
	int materialflags;                                                      
	unsigned char pvsbits[(MAX_MAP_LEAFS+7)>>3];                                       
	qboolean pvsvalid;
	int camera_entity;
	vec3_t mins, maxs;
}
r_waterstate_waterplane_t;

typedef struct r_waterstate_s
{
	int waterwidth, waterheight;
	int texturewidth, textureheight;
	int camerawidth, cameraheight;
	rtexture_t *depthtexture;

	int maxwaterplanes;                           
	int numwaterplanes;
	r_waterstate_waterplane_t waterplanes[MAX_WATERPLANES];

	float screenscale[2];
	float screencenter[2];

	qboolean enabled;

	qboolean renderingscene;                                                                                    
	qboolean hideplayer;
}
r_waterstate_t;

typedef struct r_framebufferstate_s
{
	textype_t textype;                                                                  
	int fbo;                                                
	int screentexturewidth, screentextureheight;                         

	rtexture_t *colortexture;                               
	rtexture_t *depthtexture;                               
	rtexture_t *ghosttexture;                                                             
	rtexture_t *bloomtexture[2];                                       
	int bloomfbo[2];                                          
	int bloomindex;                                                 

	int bloomwidth, bloomheight;
	int bloomtexturewidth, bloomtextureheight;

	                                         
	float screentexcoord2f[8];                                              
	float bloomtexcoord2f[8];                                
	float offsettexcoord2f[8];                                               

	r_viewport_t bloomviewport;

	r_waterstate_t water;

	qboolean ghosttexture_valid;                                                     
	qboolean usedepthtextures;                                                                                                
}
r_framebufferstate_t;

extern r_framebufferstate_t r_fb;

extern cvar_t r_viewfbo;

void R_ResetViewRendering2D_Common(int fbo, rtexture_t *depthtexture, rtexture_t *colortexture, float x2, float y2);                                                                          
void R_ResetViewRendering2D(int fbo, rtexture_t *depthtexture, rtexture_t *colortexture);
void R_ResetViewRendering3D(int fbo, rtexture_t *depthtexture, rtexture_t *colortexture);
void R_SetupView(qboolean allowwaterclippingplane, int fbo, rtexture_t *depthtexture, rtexture_t *colortexture);
extern const float r_screenvertex3f[12];
extern cvar_t r_shadows;
extern cvar_t r_shadows_darken;
extern cvar_t r_shadows_drawafterrtlighting;
extern cvar_t r_shadows_castfrombmodels;
extern cvar_t r_shadows_throwdistance;
extern cvar_t r_shadows_throwdirection;
extern cvar_t r_shadows_focus;
extern cvar_t r_shadows_shadowmapscale;
extern cvar_t r_shadows_shadowmapbias;
extern cvar_t r_transparent_alphatocoverage;
extern cvar_t r_transparent_sortsurfacesbynearest;
extern cvar_t r_transparent_useplanardistance;
extern cvar_t r_transparent_sortarraysize;
extern cvar_t r_transparent_sortmindist;
extern cvar_t r_transparent_sortmaxdist;

void R_Model_Sprite_Draw(entity_render_t *ent);

struct prvm_prog_s;
void R_UpdateFog(void);
qboolean CL_VM_UpdateView(double frametime);
void SCR_DrawConsole(void);
void R_Shadow_EditLights_DrawSelectedLightProperties(void);
void R_DecalSystem_Reset(decalsystem_t *decalsystem);
void R_Shadow_UpdateBounceGridTexture(void);
void VM_CL_AddPolygonsToMeshQueue(struct prvm_prog_s *prog);
void R_DrawPortals(void);
void R_BuildLightMap(const entity_render_t *ent, msurface_t *surface);
void R_Water_AddWaterPlane(msurface_t *surface, int entno);
int R_Shadow_GetRTLightInfo(unsigned int lightindex, float *origin, float *radius, float *color);
dp_font_t *FindFont(const char *title, qboolean allocate_new);
void LoadFont(qboolean override, const char *name, dp_font_t *fnt, float scale, float voffset);

void Render_Init(void);

                                  
void R_Textures_Init(void);
void GL_Draw_Init(void);
void GL_Main_Init(void);
void R_Shadow_Init(void);
void R_Sky_Init(void);
void GL_Surf_Init(void);
void R_Particles_Init(void);
void R_Explosion_Init(void);
void gl_backend_init(void);
void Sbar_Init(void);
void R_LightningBeams_Init(void);
void Mod_RenderInit(void);
void Font_Init(void);

qboolean R_CompileShader_CheckStaticParms(void);
void R_GLSL_Restart_f(void);

#endif
