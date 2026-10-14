  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

#ifndef SOUND_H
#define SOUND_H

#include "matrixlib.h"


                                                                       
            
                                                                       

#define DEFAULT_SOUND_PACKET_VOLUME 255
#define DEFAULT_SOUND_PACKET_ATTENUATION 1.0

                
                                                                               
#define CHANNELFLAG_NONE	0
#define CHANNELFLAG_RELIABLE	(1 << 0)                                                  
#define CHANNELFLAG_FORCELOOP	(1 << 1)                                                 
#define CHANNELFLAG_LOCALSOUND	(1 << 2)                                                  
#define CHANNELFLAG_PAUSED	(1 << 3)                
#define CHANNELFLAG_FULLVOLUME	(1 << 4)                                        

                                                                       
                      
                                                                       

typedef struct sfx_s sfx_t;

extern cvar_t mastervolume;
extern cvar_t bgmvolume;
extern cvar_t volume;
extern cvar_t snd_initialized;
extern cvar_t snd_staticvolume;
extern cvar_t snd_mutewhenidle;


                                                                       
            
                                                                       

void S_Init (void);
void S_Terminate (void);

void S_Startup (void);
void S_Shutdown (void);
void S_UnloadAllSounds_f (void);

void S_Update(const matrix4x4_t *listenermatrix);
void S_ExtraUpdate (void);

sfx_t *S_PrecacheSound (const char *sample, qboolean complain, qboolean levelsound);
float S_SoundLength(const char *name);
void S_ClearUsed (void);
void S_PurgeUnused (void);
qboolean S_IsSoundPrecached (const sfx_t *sfx);
sfx_t *S_FindName(const char *name);

                                              
#define CHAN_MIN_AUTO       -128
#define CHAN_MAX_AUTO          0
#define CHAN_MIN_SINGLE        1
#define CHAN_MAX_SINGLE      127
#define IS_CHAN_AUTO(n)        ((n) >= CHAN_MIN_AUTO && (n) <= CHAN_MAX_AUTO)
#define IS_CHAN_SINGLE(n)      ((n) >= CHAN_MIN_SINGLE && (n) <= CHAN_MAX_SINGLE)
#define IS_CHAN(n)             (IS_CHAN_AUTO(n) || IS_CHAN_SINGLE(n))

                                    
#define CHAN_ENGINE2NET(c)     (c)
#define CHAN_NET2ENGINE(c)     (c)

                                                                                                   
                                          
#define CHAN_USER2ENGINE(c)    (c)
#define CHAN_ENGINE2USER(c)    (c)
#define CHAN_ENGINE2CVAR(c)    (abs(c))

                                                                     
int S_StartSound (int entnum, int entchannel, sfx_t *sfx, vec3_t origin, float fvol, float attenuation);
int S_StartSound_StartPosition_Flags (int entnum, int entchannel, sfx_t *sfx, vec3_t origin, float fvol, float attenuation, float startposition, int flags, float fspeed);
qboolean S_LocalSound (const char *s);

void S_StaticSound (sfx_t *sfx, vec3_t origin, float fvol, float attenuation);
void S_StopSound (int entnum, int entchannel);
void S_StopAllSounds (void);
void S_PauseGameSounds (qboolean toggle);

void S_StopChannel (unsigned int channel_ind, qboolean lockmutex, qboolean freesfx);
qboolean S_SetChannelFlag (unsigned int ch_ind, unsigned int flag, qboolean value);
void S_SetChannelVolume (unsigned int ch_ind, float fvol);
void S_SetChannelSpeed (unsigned int ch_ind, float fspeed);
float S_GetChannelPosition (unsigned int ch_ind);
float S_GetEntChannelPosition(int entnum, int entchannel);

void S_BlockSound (void);
void S_UnblockSound (void);

int S_GetSoundRate (void);
int S_GetSoundChannels (void);

#endif
