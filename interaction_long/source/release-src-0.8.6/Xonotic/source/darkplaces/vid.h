  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
                             

#ifndef VID_H
#define VID_H

#define ENGINE_ICON ( (gamemode == GAME_NEXUIZ) ? nexuiz_xpm : darkplaces_xpm )

extern int cl_available;

#define MAX_TEXTUREUNITS 16

typedef enum renderpath_e
{
	RENDERPATH_GL11,
	RENDERPATH_GL13,
	RENDERPATH_GL20,
	RENDERPATH_D3D9,
	RENDERPATH_D3D10,
	RENDERPATH_D3D11,
	RENDERPATH_SOFT,
	RENDERPATH_GLES1,
	RENDERPATH_GLES2
}
renderpath_t;

typedef struct viddef_support_s
{
	qboolean gl20shaders;
	qboolean gl20shaders130;                                                 
	int glshaderversion;                                           
	qboolean amd_texture_texture4;
	qboolean arb_depth_texture;
	qboolean arb_draw_buffers;
	qboolean arb_framebuffer_object;
	qboolean arb_multitexture;
	qboolean arb_occlusion_query;
	qboolean arb_query_buffer_object;
	qboolean arb_shadow;
	qboolean arb_texture_compression;
	qboolean arb_texture_cube_map;
	qboolean arb_texture_env_combine;
	qboolean arb_texture_gather;
	qboolean arb_texture_non_power_of_two;
	qboolean arb_vertex_buffer_object;
	qboolean arb_uniform_buffer_object;
	qboolean ati_separate_stencil;
	qboolean ext_blend_minmax;
	qboolean ext_blend_subtract;
	qboolean ext_blend_func_separate;
	qboolean ext_draw_range_elements;
	qboolean ext_framebuffer_object;
	qboolean ext_packed_depth_stencil;
	qboolean ext_stencil_two_side;
	qboolean ext_texture_3d;
	qboolean ext_texture_compression_s3tc;
	qboolean ext_texture_edge_clamp;
	qboolean ext_texture_filter_anisotropic;
	qboolean ext_texture_srgb;
	qboolean arb_texture_float;
	qboolean arb_half_float_pixel;
	qboolean arb_half_float_vertex;
	qboolean arb_multisample;
}
viddef_support_t;

typedef struct viddef_mode_s
{
	int width;
	int height;
	int bitsperpixel;
	qboolean fullscreen;
	float refreshrate;
	qboolean userefreshrate;
	qboolean stereobuffer;
	int samples;
}
viddef_mode_t;

typedef struct viddef_s
{
	                            
	viddef_mode_t mode;
	                                         
	int width;
	int height;
	int bitsperpixel;
	qboolean fullscreen;
	float refreshrate;
	qboolean userefreshrate;
	qboolean stereobuffer;
	int samples;
	qboolean stencil;
	qboolean sRGB2D;                                                                   
	qboolean sRGB3D;                                                                   
	qboolean sRGBcapable2D;                                                           
	qboolean sRGBcapable3D;                                                           

	renderpath_t renderpath;
	qboolean forcevbo;                                               
	qboolean useinterleavedarrays;                                
	qboolean allowalphatocoverage;                                                                                      

	unsigned int texunits;
	unsigned int teximageunits;
	unsigned int texarrayunits;
	unsigned int drawrangeelements_maxvertices;
	unsigned int drawrangeelements_maxindices;

	unsigned int maxtexturesize_2d;
	unsigned int maxtexturesize_3d;
	unsigned int maxtexturesize_cubemap;
	unsigned int max_anisotropy;
	unsigned int maxdrawbuffers;

	viddef_support_t support;

	                                                                    
	                                                                      
	                                                                       
	                       
	unsigned int *softpixels;
	unsigned int *softdepthpixels;

	int forcetextype;                                                                
} viddef_t;

                     
extern viddef_t vid;
extern void (*vid_menudrawfn)(void);
extern void (*vid_menukeyfn)(int key);

#define MAXJOYAXIS 16
                                                                             
#define MAXJOYBUTTON 36
typedef struct vid_joystate_s
{
	float axis[MAXJOYAXIS];            
	unsigned char button[MAXJOYBUTTON];          
	qboolean is360;                                                                          
}
vid_joystate_t;

extern vid_joystate_t vid_joystate;

extern cvar_t joy_index;
extern cvar_t joy_enable;
extern cvar_t joy_detected;
extern cvar_t joy_active;

float VID_JoyState_GetAxis(const vid_joystate_t *joystate, int axis, float sensitivity, float deadzone);
void VID_ApplyJoyState(vid_joystate_t *joystate);
void VID_BuildJoyState(vid_joystate_t *joystate);
void VID_Shared_BuildJoyState_Begin(vid_joystate_t *joystate);
void VID_Shared_BuildJoyState_Finish(vid_joystate_t *joystate);
int VID_Shared_SetJoystick(int index);
qboolean VID_JoyBlockEmulatedKeys(int keycode);
void VID_EnableJoystick(qboolean enable);

extern qboolean vid_hidden;
extern qboolean vid_activewindow;
extern qboolean vid_supportrefreshrate;

extern cvar_t vid_soft;
extern cvar_t vid_soft_threads;
extern cvar_t vid_soft_interlace;

extern cvar_t vid_fullscreen;
extern cvar_t vid_width;
extern cvar_t vid_height;
extern cvar_t vid_bitsperpixel;
extern cvar_t vid_samples;
extern cvar_t vid_refreshrate;
extern cvar_t vid_userefreshrate;
extern cvar_t vid_touchscreen_density;
extern cvar_t vid_touchscreen_xdpi;
extern cvar_t vid_touchscreen_ydpi;
extern cvar_t vid_vsync;
extern cvar_t vid_mouse;
extern cvar_t vid_grabkeyboard;
extern cvar_t vid_touchscreen;
extern cvar_t vid_touchscreen_showkeyboard;
extern cvar_t vid_touchscreen_supportshowkeyboard;
extern cvar_t vid_stick_mouse;
extern cvar_t vid_resizable;
extern cvar_t vid_desktopfullscreen;
extern cvar_t vid_minwidth;
extern cvar_t vid_minheight;
extern cvar_t vid_sRGB;
extern cvar_t vid_sRGB_fallback;

extern cvar_t gl_finish;

extern cvar_t v_gamma;
extern cvar_t v_contrast;
extern cvar_t v_brightness;
extern cvar_t v_color_enable;
extern cvar_t v_color_black_r;
extern cvar_t v_color_black_g;
extern cvar_t v_color_black_b;
extern cvar_t v_color_grey_r;
extern cvar_t v_color_grey_g;
extern cvar_t v_color_grey_b;
extern cvar_t v_color_white_r;
extern cvar_t v_color_white_g;
extern cvar_t v_color_white_b;

                         
extern const char *gl_vendor;
                                            
extern const char *gl_renderer;
                                                                 
extern const char *gl_version;
                                   
extern const char *gl_extensions;
                   
extern const char *gl_platform;
                                                                            
                       
extern const char *gl_platformextensions;
                                                                 
extern char gl_driver[256];

void *GL_GetProcAddress(const char *name);
qboolean GL_CheckExtension(const char *minglver_or_ext, const dllfunction_t *funcs, const char *disableparm, int silent);

void VID_Shared_Init(void);

void GL_Init (void);

void VID_ClearExtensions(void);
void VID_CheckExtensions(void);

void VID_Init (void);
                    

void VID_Shutdown (void);
                     

int VID_SetMode (int modenum);
                                                                            
                                           

qboolean VID_InitMode(viddef_mode_t *mode);
                                                                     


                                                                                    
                                       
void VID_UpdateGamma(void);

qboolean VID_HasScreenKeyboardSupport(void);
void VID_ShowKeyboard(qboolean show);
qboolean VID_ShowingKeyboard(void);

void VID_SetMouse (qboolean fullscreengrab, qboolean relative, qboolean hidecursor);
void VID_Finish (void);

void VID_Restart_f(void);

void VID_Start(void);
void VID_Stop(void);

extern unsigned int vid_gammatables_serial;                                                                                                                                                                                                        
extern qboolean vid_gammatables_trivial;                                                                                                                                       
void VID_BuildGammaTables(unsigned short *ramps, int rampsize);                                                                          
void VID_ApplyGammaToColor(const float *rgb, float *out);                                                         

typedef struct
{
	int width, height, bpp, refreshrate;
	int pixelheight_num, pixelheight_denom;
}
vid_mode_t;
vid_mode_t *VID_GetDesktopMode(void);
size_t VID_ListModes(vid_mode_t *modes, size_t maxcount);
size_t VID_SortModes(vid_mode_t *modes, size_t count, qboolean usebpp, qboolean userefreshrate, qboolean useaspect);
void VID_Soft_SharedSetup(void);

#endif

