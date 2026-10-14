
#ifndef R_TEXTURES_H
#define R_TEXTURES_H

              
#define TEXF_ALPHA 0x00000001
            
#define TEXF_MIPMAP 0x00000002
                                             
#define TEXF_RGBMULTIPLYBYALPHA 0x00000004
                                                                       
#define TEXF_CLAMP 0x00000020
                                                                                          
#define TEXF_FORCENEAREST 0x00000040
                                                                                                                   
#define TEXF_FORCELINEAR 0x00000080
                                                                         
#define TEXF_PICMIP 0x00000100
                                                     
#define TEXF_COMPRESS 0x00000200
                                                                                                                                           
#define TEXF_PERSISTENT 0x00000400
                                                            
#define TEXF_COMPARE 0x00000800
                                                               
#define TEXF_LOWPRECISION 0x00001000
                                                                                                                                                            
#define TEXF_ALLOWUPDATES 0x00002000
                                                                                                                                    
#define TEXF_ISWORLD 0x00004000
                                                                                                                                        
#define TEXF_ISSPRITE 0x00008000
                                                                   
#define TEXF_RENDERTARGET 0x0010000
                                         
#define TEXF_IMPORTANTBITS (TEXF_ALPHA | TEXF_MIPMAP | TEXF_RGBMULTIPLYBYALPHA | TEXF_CLAMP | TEXF_FORCENEAREST | TEXF_FORCELINEAR | TEXF_PICMIP | TEXF_COMPRESS | TEXF_COMPARE | TEXF_LOWPRECISION | TEXF_RENDERTARGET)
                                                    
#define TEXF_FORCE_RELOAD 0x80000000

typedef enum textype_e
{
	                
	TEXTYPE_PALETTE,
	             
	TEXTYPE_RGBA,
	                                                                       
	TEXTYPE_BGRA,
	                                       
	TEXTYPE_ALPHA,
	                                                      
	TEXTYPE_DXT1,
	                                                                      
	TEXTYPE_DXT1A,
	                                                                      
	TEXTYPE_DXT3,
	                                                                      
	TEXTYPE_DXT5,

	                                    
	TEXTYPE_ETC1,

	                                   
	TEXTYPE_SRGB_PALETTE,
	                                
	TEXTYPE_SRGB_RGBA,
	                                                                                          
	TEXTYPE_SRGB_BGRA,
	                                                                         
	TEXTYPE_SRGB_DXT1,
	                                                                                         
	TEXTYPE_SRGB_DXT1A,
	                                                                                         
	TEXTYPE_SRGB_DXT3,
	                                                                                         
	TEXTYPE_SRGB_DXT5,

	                                                                      
	TEXTYPE_COLORBUFFER,
	                                                              
	TEXTYPE_COLORBUFFER16F,
	                                                         
	TEXTYPE_COLORBUFFER32F,
	                                    
	TEXTYPE_DEPTHBUFFER16,
	                                    
	TEXTYPE_DEPTHBUFFER24,
	                                                                             
	TEXTYPE_DEPTHBUFFER24STENCIL8,
	                                                                                   
	TEXTYPE_SHADOWMAP16_COMP,
	                                                                              
	TEXTYPE_SHADOWMAP16_RAW,
	                                                                                   
	TEXTYPE_SHADOWMAP24_COMP,
	                                                                              
	TEXTYPE_SHADOWMAP24_RAW,
}
textype_t;

  
            
                  
                      
                 
                 
      
      
  

                                                                 
typedef struct rtexture_s
{
	                                                               
	int texnum;                          
	int renderbuffernum;                               
	qboolean dirty;                                                    
	qboolean glisdepthstencil;                                                                       
	int gltexturetypeenum;                          
	                              
	void *d3dtexture;
	void *d3dsurface;
#ifdef SUPPORTD3D
	qboolean d3disrendertargetsurface;
	qboolean d3disdepthstencilsurface;
	int d3dformat;
	int d3dusage;
	int d3dpool;
	int d3daddressu;
	int d3daddressv;
	int d3daddressw;
	int d3dmagfilter;
	int d3dminfilter;
	int d3dmipfilter;
	int d3dmaxmiplevelfilter;
	int d3dmipmaplodbias;
	int d3dmaxmiplevel;
#endif
}
rtexture_t;

                                                          
typedef struct rtexturepool_s
{
	int useless;
}
rtexturepool_t;

typedef void (*updatecallback_t)(rtexture_t *rt, void *data);

                                                         
rtexturepool_t *R_AllocTexturePool(void);
                                                               
void R_FreeTexturePool(rtexturepool_t **rtexturepool);

                                                                                                                                          
extern cvar_t gl_texturecompression;
extern cvar_t gl_texturecompression_color;
extern cvar_t gl_texturecompression_normal;
extern cvar_t gl_texturecompression_gloss;
extern cvar_t gl_texturecompression_glow;
extern cvar_t gl_texturecompression_2d;
extern cvar_t gl_texturecompression_q3bsplightmaps;
extern cvar_t gl_texturecompression_q3bspdeluxemaps;
extern cvar_t gl_texturecompression_sky;
extern cvar_t gl_texturecompression_lightcubemaps;
extern cvar_t gl_texturecompression_reflectmask;
extern cvar_t r_texture_dds_load;
extern cvar_t r_texture_dds_save;

                                                              
                                               
                                                            
rtexture_t *R_LoadTexture2D(rtexturepool_t *rtexturepool, const char *identifier, int width, int height, const unsigned char *data, textype_t textype, int flags, int miplevel, const unsigned int *palette);
rtexture_t *R_LoadTexture3D(rtexturepool_t *rtexturepool, const char *identifier, int width, int height, int depth, const unsigned char *data, textype_t textype, int flags, int miplevel, const unsigned int *palette);
rtexture_t *R_LoadTextureCubeMap(rtexturepool_t *rtexturepool, const char *identifier, int width, const unsigned char *data, textype_t textype, int flags, int miplevel, const unsigned int *palette);
rtexture_t *R_LoadTextureShadowMap2D(rtexturepool_t *rtexturepool, const char *identifier, int width, int height, textype_t textype, qboolean filter);
rtexture_t *R_LoadTextureRenderBuffer(rtexturepool_t *rtexturepool, const char *identifier, int width, int height, textype_t textype);
rtexture_t *R_LoadTextureDDSFile(rtexturepool_t *rtexturepool, const char *filename, qboolean srgb, int flags, qboolean *hasalphaflag, float *avgcolor, int miplevel, qboolean optionaltexture);

                                
int R_SaveTextureDDSFile(rtexture_t *rt, const char *filename, qboolean skipuncompressed, qboolean hasalpha);

                 
void R_FreeTexture(rtexture_t *rt);

                                                                            
                                                                        
                                                                          
void R_UpdateTexture(rtexture_t *rt, const unsigned char *data, int x, int y, int z, int width, int height, int depth);

                                                                            
                                                   
#define R_GetTexture(rt) ((rt) ? ((rt)->dirty ? R_RealGetTexture(rt) : (rt)->texnum) : r_texture_white->texnum)
int R_RealGetTexture (rtexture_t *rt);

                                                                  
int R_TextureWidth(rtexture_t *rt);

                                                                   
int R_TextureHeight(rtexture_t *rt);

                                                                  
int R_TextureFlags(rtexture_t *rt);

                                                       
                           
void R_PurgeTexture(rtexture_t *prt);

                                                                                   
void R_Textures_Frame(void);

                                                       
void R_MarkDirtyTexture(rtexture_t *rt);
void R_MakeTextureDynamic(rtexture_t *rt, updatecallback_t updatecallback, void *data);

                               
void R_ClearTexture (rtexture_t *rt);

                                                         
int R_PicmipForFlags(int flags);

void R_TextureStats_Print(qboolean printeach, qboolean printpool, qboolean printtotal);

#endif

