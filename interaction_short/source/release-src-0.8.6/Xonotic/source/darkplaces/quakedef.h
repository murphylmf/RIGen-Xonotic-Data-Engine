  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
                                          

#ifndef QUAKEDEF_H
#define QUAKEDEF_H

#ifdef __APPLE__
# include <TargetConditionals.h>
#endif

#if defined(__GNUC__) && (__GNUC__ > 2)
#define DP_FUNC_PRINTF(n) __attribute__ ((format (printf, n, n+1)))
#define DP_FUNC_PURE      __attribute__ ((pure))
#define DP_FUNC_NORETURN  __attribute__ ((noreturn))
#else
#define DP_FUNC_PRINTF(n)
#define DP_FUNC_PURE
#define DP_FUNC_NORETURN
#endif

#include <sys/types.h>
#include <ctype.h>
#include <math.h>
#include <string.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
#include <setjmp.h>

#include "qtypes.h"

extern const char *buildstring;
extern char engineversion[128];

#define GAMENAME "id1"

#define MAX_NUM_ARGVS	50

#ifdef DP_SMALLMEMORY
#define	MAX_INPUTLINE			1024
#define	CON_TEXTSIZE			16384
#define	CON_MAXLINES			256
#define	HIST_TEXTSIZE			2048
#define	HIST_MAXLINES			16
#define	MAX_ALIAS_NAME			32
#define	CMDBUFSIZE				131072
#define	MAX_ARGS				80

#define	NET_MAXMESSAGE			65536
#define	MAX_PACKETFRAGMENT		1024
#define	MAX_EDICTS				4096
#define	MAX_MODELS				1024
#define	MAX_SOUNDS				1024
#define	MAX_LIGHTSTYLES			64
#define	MAX_STYLESTRING			16
#define	MAX_SCOREBOARD			32
#define	MAX_SCOREBOARDNAME		128
#define	MAX_USERINFO_STRING		196
#define	MAX_SERVERINFO_STRING	512
#define	MAX_LOCALINFO_STRING	1                                   
#define	CL_MAX_USERCMDS			32
#define	CVAR_HASHSIZE			1024
#define	M_MAX_EDICTS			4096
#define	MAX_DEMOS				8
#define	MAX_DEMONAME			16
#define	MAX_SAVEGAMES			12
#define	SAVEGAME_COMMENT_LENGTH	39
#define	MAX_CLIENTNETWORKEYES	2
#define	MAX_LEVELNETWORKEYES	0                     
#define	MAX_OCCLUSION_QUERIES	256

#define CRYPTO_HOSTKEY_HASHSIZE 256
#define MAX_NETWM_ICON 1026             

#define	MAX_WATERPLANES			2
#define	MAX_CUBEMAPS			1024
#define	MAX_EXPLOSIONS			8
#define	MAX_DLIGHTS				16
#define	MAX_CACHED_PICS			1024                                            
#define	CACHEPICHASHSIZE		256
#define	MAX_PARTICLEEFFECTNAME	256
#define	MAX_PARTICLEEFFECTINFO	1024
#define	MAX_PARTICLETEXTURES	256
#define	MAXCLVIDEOS				1
#define	MAX_DYNAMIC_TEXTURE_COUNT	2
#define	MAX_MAP_LEAFS			8192

#define	MAXTRACKS				256
#define	MAX_DYNAMIC_CHANNELS	64
#define	MAX_CHANNELS			260
#define	MODLIST_TOTALSIZE		32
#define	MAX_FAVORITESERVERS		32
#define	MAX_DECALSYSTEM_QUEUE	64
#define	PAINTBUFFER_SIZE		512
#define	MAX_BINDMAPS			8
#define	MAX_PARTICLES_INITIAL	8192
#define	MAX_PARTICLES			8192
#define	MAX_DECALS_INITIAL		1024
#define	MAX_DECALS				1024
#define	MAX_ENITIES_INITIAL		256
#define	MAX_STATICENTITIES		256
#define	MAX_EFFECTS				16
#define	MAX_BEAMS				16
#define	MAX_TEMPENTITIES		256
#define SERVERLIST_TOTALSIZE		1024
#define SERVERLIST_ANDMASKCOUNT		5
#define SERVERLIST_ORMASKCOUNT		5
#else
#define	MAX_INPUTLINE			16384                                                                                                   
#define	CON_TEXTSIZE			1048576                                                 
#define	CON_MAXLINES			16384                                            
#define	HIST_TEXTSIZE			262144                                                      
#define	HIST_MAXLINES			4096                                                 
#define	MAX_ALIAS_NAME			32
#define	CMDBUFSIZE				655360                                                                                
#define	MAX_ARGS				80                                                                

#define	NET_MAXMESSAGE			65536                                                                                 
#define	MAX_PACKETFRAGMENT		1024                                   
#define	MAX_EDICTS				32768                                                                        
#define	MAX_MODELS				8192                                                                              
#define	MAX_SOUNDS				4096                                         
#define	MAX_LIGHTSTYLES			256                                                                          
#define	MAX_STYLESTRING			64                                                   
#define	MAX_SCOREBOARD			255                                                                
#define	MAX_SCOREBOARDNAME		128                                       
#define	MAX_USERINFO_STRING		1280                                                                          
#define	MAX_SERVERINFO_STRING	1280                                                                                 
#define	MAX_LOCALINFO_STRING	32768                                                                                         
#define	CL_MAX_USERCMDS			128                                                    
#define	CVAR_HASHSIZE			65536                                                               
#define	M_MAX_EDICTS			32768                            
#define	MAX_DEMOS				8                                         
#define	MAX_DEMONAME			16                                            
#define	MAX_SAVEGAMES			12                                           
#define	SAVEGAME_COMMENT_LENGTH	39                                            
#define	MAX_CLIENTNETWORKEYES	16                                                                                                                        
#define	MAX_LEVELNETWORKEYES	512                                                                                                                        
#define	MAX_OCCLUSION_QUERIES	4096                                                                                

#define CRYPTO_HOSTKEY_HASHSIZE 8192                                                              
#define MAX_NETWM_ICON 352822                                                                       

#define	MAX_WATERPLANES			16                                                                                  
#define	MAX_CUBEMAPS			1024                                                             
#define	MAX_EXPLOSIONS			64                                                                                 
#define	MAX_DLIGHTS				256                                                                         
#define	MAX_CACHED_PICS			1024                                          
#define	CACHEPICHASHSIZE		256                                                                 
#define	MAX_PARTICLEEFFECTNAME	4096                                                                                
#define	MAX_PARTICLEEFFECTINFO	8192                                                                                               
#define	MAX_PARTICLETEXTURES	256                                                                     
#define	MAXCLVIDEOS				65                                                                                                         
#define	MAX_DYNAMIC_TEXTURE_COUNT	64                                                                       
#define	MAX_MAP_LEAFS			65536                                                          

#define	MAXTRACKS				256                        
                                     
                                                                                 
                                                                        
#define	MAX_DYNAMIC_CHANNELS	512
#define	MAX_CHANNELS			(8192 + 4)
#define	MODLIST_TOTALSIZE		256
#define	MAX_FAVORITESERVERS		256
#define	MAX_DECALSYSTEM_QUEUE	1024
#define	PAINTBUFFER_SIZE		2048
#define	MAX_BINDMAPS			8
#define	MAX_PARTICLES_INITIAL	8192                                         
#define	MAX_PARTICLES			1048576                                      
#define	MAX_DECALS_INITIAL		8192                                      
#define	MAX_DECALS				1048576                                   
#define	MAX_ENITIES_INITIAL		256                                 
#define	MAX_STATICENTITIES		1024                                         
#define	MAX_EFFECTS				256                                 
#define	MAX_BEAMS				256                               
#define	MAX_TEMPENTITIES		4096                                                                                                                             
#define SERVERLIST_TOTALSIZE		2048                                    
#define SERVERLIST_ANDMASKCOUNT		16                                       
#define SERVERLIST_ORMASKCOUNT		16                                      
#endif


#define CMD_TOKENIZELENGTH (MAX_INPUTLINE + MAX_ARGS)                                                                  


#define	MAX_QPATH		128			                                        
#ifdef PATH_MAX
#define	MAX_OSPATH		PATH_MAX
#elif MAX_PATH
#define	MAX_OSPATH		MAX_PATH
#else
#define	MAX_OSPATH		1024		                                        
#endif

#define	ON_EPSILON		0.1			                                

#define	NET_MINRATE		1000                                          

  
                                                              
  
#define	MAX_CL_STATS		256
#define	STAT_HEALTH			0
                        
#define	STAT_WEAPON			2
#define	STAT_AMMO			3
#define	STAT_ARMOR			4
#define	STAT_WEAPONFRAME	5
#define	STAT_SHELLS			6
#define	STAT_NAILS			7
#define	STAT_ROCKETS		8
#define	STAT_CELLS			9
#define	STAT_ACTIVEWEAPON	10
#define	STAT_TOTALSECRETS	11
#define	STAT_TOTALMONSTERS	12
#define	STAT_SECRETS		13		                                             
#define	STAT_MONSTERS		14		                                
#define STAT_ITEMS			15             
#define STAT_VIEWHEIGHT		16             
                                 
                                 
#define STAT_VIEWZOOM		21        
#define STAT_MOVEVARS_AIRACCEL_QW_STRETCHFACTOR 220        
#define STAT_MOVEVARS_AIRCONTROL_PENALTY					221        
#define STAT_MOVEVARS_AIRSPEEDLIMIT_NONQW 222        
#define STAT_MOVEVARS_AIRSTRAFEACCEL_QW 223        
#define STAT_MOVEVARS_AIRCONTROL_POWER					224        
#define STAT_MOVEFLAGS                              225        
#define STAT_MOVEVARS_WARSOWBUNNY_AIRFORWARDACCEL	226        
#define STAT_MOVEVARS_WARSOWBUNNY_ACCEL				227        
#define STAT_MOVEVARS_WARSOWBUNNY_TOPSPEED			228        
#define STAT_MOVEVARS_WARSOWBUNNY_TURNACCEL			229        
#define STAT_MOVEVARS_WARSOWBUNNY_BACKTOSIDERATIO	230        
#define STAT_MOVEVARS_AIRSTOPACCELERATE				231        
#define STAT_MOVEVARS_AIRSTRAFEACCELERATE			232        
#define STAT_MOVEVARS_MAXAIRSTRAFESPEED				233        
#define STAT_MOVEVARS_AIRCONTROL					234        
#define STAT_FRAGLIMIT								235        
#define STAT_TIMELIMIT								236        
#define STAT_MOVEVARS_WALLFRICTION					237        
#define STAT_MOVEVARS_FRICTION						238        
#define STAT_MOVEVARS_WATERFRICTION					239        
#define STAT_MOVEVARS_TICRATE						240        
#define STAT_MOVEVARS_TIMESCALE						241        
#define STAT_MOVEVARS_GRAVITY						242        
#define STAT_MOVEVARS_STOPSPEED						243        
#define STAT_MOVEVARS_MAXSPEED						244        
#define STAT_MOVEVARS_SPECTATORMAXSPEED				245        
#define STAT_MOVEVARS_ACCELERATE					246        
#define STAT_MOVEVARS_AIRACCELERATE					247        
#define STAT_MOVEVARS_WATERACCELERATE				248        
#define STAT_MOVEVARS_ENTGRAVITY					249        
#define STAT_MOVEVARS_JUMPVELOCITY					250        
#define STAT_MOVEVARS_EDGEFRICTION					251        
#define STAT_MOVEVARS_MAXAIRSPEED					252        
#define STAT_MOVEVARS_STEPHEIGHT					253        
#define STAT_MOVEVARS_AIRACCEL_QW					254        
#define STAT_MOVEVARS_AIRACCEL_SIDEWAYS_FRICTION	255        

                   
#define MOVEFLAG_VALID 0x80000000
#define MOVEFLAG_Q2AIRACCELERATE 0x00000001
#define MOVEFLAG_NOGRAVITYONGROUND 0x00000002
#define MOVEFLAG_GRAVITYUNAFFECTEDBYTICRATE 0x00000004

                

#define	IT_SHOTGUN				1
#define	IT_SUPER_SHOTGUN		2
#define	IT_NAILGUN				4
#define	IT_SUPER_NAILGUN		8
#define	IT_GRENADE_LAUNCHER		16
#define	IT_ROCKET_LAUNCHER		32
#define	IT_LIGHTNING			64
#define IT_SUPER_LIGHTNING      128
#define IT_SHELLS               256
#define IT_NAILS                512
#define IT_ROCKETS              1024
#define IT_CELLS                2048
#define IT_AXE                  4096
#define IT_ARMOR1               8192
#define IT_ARMOR2               16384
#define IT_ARMOR3               32768
#define IT_SUPERHEALTH          65536
#define IT_KEY1                 131072
#define IT_KEY2                 262144
#define	IT_INVISIBILITY			524288
#define	IT_INVULNERABILITY		1048576
#define	IT_SUIT					2097152
#define	IT_QUAD					4194304
#define IT_SIGIL1               (1<<28)
#define IT_SIGIL2               (1<<29)
#define IT_SIGIL3               (1<<30)
#define IT_SIGIL4               (1<<31)

                                             
                                      

#define NEX_IT_UZI              1
#define NEX_IT_SHOTGUN          2
#define NEX_IT_GRENADE_LAUNCHER 4
#define NEX_IT_ELECTRO          8
#define NEX_IT_CRYLINK          16
#define NEX_IT_NEX              32
#define NEX_IT_HAGAR            64
#define NEX_IT_ROCKET_LAUNCHER  128
#define NEX_IT_SHELLS           256
#define NEX_IT_BULLETS          512
#define NEX_IT_ROCKETS          1024
#define NEX_IT_CELLS            2048
#define NEX_IT_LASER            4094
#define NEX_IT_STRENGTH         8192
#define NEX_IT_INVINCIBLE       16384
#define NEX_IT_SPEED            32768
#define NEX_IT_SLOWMO           65536

                                             
                                 

#define RIT_SHELLS              128
#define RIT_NAILS               256
#define RIT_ROCKETS             512
#define RIT_CELLS               1024
#define RIT_AXE                 2048
#define RIT_LAVA_NAILGUN        4096
#define RIT_LAVA_SUPER_NAILGUN  8192
#define RIT_MULTI_GRENADE       16384
#define RIT_MULTI_ROCKET        32768
#define RIT_PLASMA_GUN          65536
#define RIT_ARMOR1              8388608
#define RIT_ARMOR2              16777216
#define RIT_ARMOR3              33554432
#define RIT_LAVA_NAILS          67108864
#define RIT_PLASMA_AMMO         134217728
#define RIT_MULTI_ROCKETS       268435456
#define RIT_SHIELD              536870912
#define RIT_ANTIGRAV            1073741824
#define RIT_SUPERHEALTH         2147483648

                                     
                                             
                        
#define HIT_PROXIMITY_GUN_BIT 16
#define HIT_MJOLNIR_BIT       7
#define HIT_LASER_CANNON_BIT  23
#define HIT_PROXIMITY_GUN   (1<<HIT_PROXIMITY_GUN_BIT)
#define HIT_MJOLNIR         (1<<HIT_MJOLNIR_BIT)
#define HIT_LASER_CANNON    (1<<HIT_LASER_CANNON_BIT)
#define HIT_WETSUIT         (1<<(23+2))
#define HIT_EMPATHY_SHIELDS (1<<(23+3))

                                             

#include "zone.h"
#include "fs.h"
#include "common.h"
#include "cvar.h"
#include "bspfile.h"
#include "sys.h"
#include "vid.h"
#include "mathlib.h"

#include "r_textures.h"

#include "crypto.h"
#include "draw.h"
#include "screen.h"
#include "netconn.h"
#include "protocol.h"
#include "cmd.h"
#include "sbar.h"
#include "sound.h"
#include "model_shared.h"
#include "world.h"
#include "client.h"
#include "render.h"
#include "progs.h"
#include "progsvm.h"
#include "server.h"

#include "input.h"
#include "keys.h"
#include "console.h"
#ifdef CONFIG_MENU
#include "menu.h"
#endif
#include "csprogs.h"

extern qboolean noclip_anglehack;

extern cvar_t developer;
extern cvar_t developer_extra;
extern cvar_t developer_insane;
extern cvar_t developer_loadfile;
extern cvar_t developer_loading;

extern cvar_t sessionid;

#define STARTCONFIGFILENAME "quake.rc"
#define CONFIGFILENAME "config.cfg"

                                           
                                                               
                                                                   
                                                            
   
#if defined(__ANDROID__)                                                    
# define DP_OS_NAME		"Android"
# define DP_OS_STR		"android"
# define USE_GLES2		1
# define USE_RWOPS		1
# define LINK_TO_ZLIB	1
# define LINK_TO_LIBVORBIS 1
# define DP_MOBILETOUCH	1
# define DP_FREETYPE_STATIC 1
#elif TARGET_OS_IPHONE                                                     
# define DP_OS_NAME		"iPhoneOS"
# define DP_OS_STR		"iphoneos"
# define USE_GLES2		1
# define LINK_TO_ZLIB	1
# define LINK_TO_LIBVORBIS 1
# define DP_MOBILETOUCH	1
# define DP_FREETYPE_STATIC 1
#elif defined(__linux__)
# define DP_OS_NAME		"Linux"
# define DP_OS_STR		"linux"
#elif defined(_WIN64)
# define DP_OS_NAME		"Windows64"
# define DP_OS_STR		"win64"
#elif defined(WIN32)
# define DP_OS_NAME		"Windows"
# define DP_OS_STR		"win32"
#elif defined(__FreeBSD__)
# define DP_OS_NAME		"FreeBSD"
# define DP_OS_STR		"freebsd"
#elif defined(__NetBSD__)
# define DP_OS_NAME		"NetBSD"
# define DP_OS_STR		"netbsd"
#elif defined(__OpenBSD__)
# define DP_OS_NAME		"OpenBSD"
# define DP_OS_STR		"openbsd"
#elif defined(MACOSX)
# define DP_OS_NAME		"Mac OS X"
# define DP_OS_STR		"osx"
#elif defined(__MORPHOS__)
# define DP_OS_NAME		"MorphOS"
# define DP_OS_STR		"morphos"
#else
# define DP_OS_NAME		"Unknown"
# define DP_OS_STR		"unknown"
#endif

#if defined(__GNUC__)
# if defined(__i386__)
#  define DP_ARCH_STR		"686"
#  define SSE_POSSIBLE
#  ifdef __SSE__
#   define SSE_PRESENT
#  endif
#  ifdef __SSE2__
#   define SSE2_PRESENT
#  endif
# elif defined(__x86_64__)
#  define DP_ARCH_STR		"x86_64"
#  define SSE_PRESENT
#  define SSE2_PRESENT
# elif defined(__powerpc__)
#  define DP_ARCH_STR		"ppc"
# endif
#elif defined(_WIN64)
# define DP_ARCH_STR		"x86_64"
# define SSE_PRESENT
# define SSE2_PRESENT
#elif defined(WIN32)
# define DP_ARCH_STR		"x86"
# define SSE_POSSIBLE
#endif

#ifdef SSE_PRESENT
# define SSE_POSSIBLE
#endif

#ifdef NO_SSE
# undef SSE_PRESENT
# undef SSE_POSSIBLE
# undef SSE2_PRESENT
#endif

#ifdef SSE_POSSIBLE
                                                     
qboolean Sys_HaveSSE(void);
qboolean Sys_HaveSSE2(void);
#else
#define Sys_HaveSSE() false
#define Sys_HaveSSE2() false
#endif

#include "glquake.h"

#include "palette.h"

                                        
extern int host_framecount;
                                                                        
extern double realtime;
                                                            
extern double host_dirtytime;

void Host_InitCommands(void);
void Host_Main(void);
void Host_Shutdown(void);
void Host_StartVideo(void);
void Host_Error(const char *error, ...) DP_FUNC_PRINTF(1) DP_FUNC_NORETURN;
void Host_Quit_f(void);
void Host_ClientCommands(const char *fmt, ...) DP_FUNC_PRINTF(1);
void Host_ShutdownServer(void);
void Host_Reconnect_f(void);
void Host_NoOperation_f(void);
void Host_LockSession(void);
void Host_UnlockSession(void);

void Host_AbortCurrentFrame(void);

                                                                                                                                                  
extern int current_skill;

  
        
  
extern cvar_t chase_active;
extern cvar_t cl_viewmodel_scale;

void Chase_Init (void);
void Chase_Reset (void);
void Chase_Update (void);

void fractalnoise(unsigned char *noise, int size, int startgrid);
void fractalnoisequick(unsigned char *noise, int size, int startgrid);
float noise4f(float x, float y, float z, float w);

void Sys_Shared_Init(void);

                                                                        
                                                                              
                           
#define DEMOMSG_CLIENT_TO_SERVER 0x80000000

                                                   
                                                                      
#define ISWHITESPACE(ch) (!(ch) || (ch) == ' ' || (ch) == '\t' || (ch) == '\r' || (ch) == '\n')

                                                                
#define ISWHITESPACEORCONTROL(ch) ((signed char) (ch) <= (signed char) ' ')


#ifdef PRVM_64
#define FLOAT_IS_TRUE_FOR_INT(x) ((x) & 0x7FFFFFFFFFFFFFFF)                                                                  
#define FLOAT_LOSSLESS_FORMAT "%.17g"
#define VECTOR_LOSSLESS_FORMAT "%.17g %.17g %.17g"
#else
#define FLOAT_IS_TRUE_FOR_INT(x) ((x) & 0x7FFFFFFF)                                                         
#define FLOAT_LOSSLESS_FORMAT "%.9g"
#define VECTOR_LOSSLESS_FORMAT "%.9g %.9g %.9g"
#endif

                               
                                                                                           
#ifdef WIN32
#define INT_LOSSLESS_FORMAT_SIZE "I64"
#define INT_LOSSLESS_FORMAT_CONVERT_S(x) ((__int64)(x))
#define INT_LOSSLESS_FORMAT_CONVERT_U(x) ((unsigned __int64)(x))
#else
#define INT_LOSSLESS_FORMAT_SIZE "j"
#define INT_LOSSLESS_FORMAT_CONVERT_S(x) ((intmax_t)(x))
#define INT_LOSSLESS_FORMAT_CONVERT_U(x) ((uintmax_t)(x))
#endif

#endif

