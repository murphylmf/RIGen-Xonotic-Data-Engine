  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
                                                                          
                           

#include "quakedef.h"

cvar_t bgmvolume = {CVAR_SAVE, "bgmvolume", "1", "volume of background music (such as CD music or replacement files such as sound/cdtracks/track002.ogg)"};
cvar_t mastervolume = {CVAR_SAVE, "mastervolume", "1", "master volume"};
cvar_t volume = {CVAR_SAVE, "volume", "0.7", "volume of sound effects"};
cvar_t snd_staticvolume = {CVAR_SAVE, "snd_staticvolume", "1", "volume of ambient sound effects (such as swampy sounds at the start of e1m2)"};
cvar_t snd_initialized = { CVAR_READONLY, "snd_initialized", "0", "indicates the sound subsystem is active"};
cvar_t snd_mutewhenidle = {CVAR_SAVE, "snd_mutewhenidle", "1", "whether to disable sound output when game window is inactive"};

void S_Init (void)
{
	Cvar_RegisterVariable(&bgmvolume);
	Cvar_RegisterVariable(&mastervolume);
	Cvar_RegisterVariable(&volume);
	Cvar_RegisterVariable(&snd_staticvolume);
	Cvar_RegisterVariable(&snd_initialized);
	Cvar_RegisterVariable(&snd_mutewhenidle);
}

void S_Terminate (void)
{
}

void S_Startup (void)
{
}

void S_Shutdown (void)
{
}

void S_ClearUsed (void)
{
}

void S_PurgeUnused (void)
{
}


void S_StaticSound (sfx_t *sfx, vec3_t origin, float fvol, float attenuation)
{
}

int S_StartSound (int entnum, int entchannel, sfx_t *sfx, vec3_t origin, float fvol, float attenuation)
{
	return -1;
}

int S_StartSound_StartPosition_Flags (int entnum, int entchannel, sfx_t *sfx, vec3_t origin, float fvol, float attenuation, float startposition, int flags, float fspeed)
{
	return -1;
}

void S_StopChannel (unsigned int channel_ind, qboolean lockmutex, qboolean freesfx)
{
}

qboolean S_SetChannelFlag (unsigned int ch_ind, unsigned int flag, qboolean value)
{
	return false;
}

void S_StopSound (int entnum, int entchannel)
{
}

void S_PauseGameSounds (qboolean toggle)
{
}

void S_SetChannelVolume (unsigned int ch_ind, float fvol)
{
}

sfx_t *S_PrecacheSound (const char *sample, qboolean complain, qboolean levelsound)
{
	return NULL;
}

float S_SoundLength(const char *name)
{
	return -1;
}

qboolean S_IsSoundPrecached (const sfx_t *sfx)
{
	return false;
}

void S_UnloadAllSounds_f (void)
{
}

sfx_t *S_FindName (const char *name)
{
	return NULL;
}

void S_Update(const matrix4x4_t *matrix)
{
}

void S_StopAllSounds (void)
{
}

void S_ExtraUpdate (void)
{
}

qboolean S_LocalSound (const char *s)
{
	return false;
}

void S_BlockSound (void)
{
}

void S_UnblockSound (void)
{
}

int S_GetSoundRate(void)
{
	return 0;
}

int S_GetSoundChannels(void)
{
	return 0;
}

float S_GetChannelPosition (unsigned int ch_ind)
{
	return -1;
}

float S_GetEntChannelPosition(int entnum, int entchannel)
{
	return -1;
}

void SndSys_SendKeyEvents(void)
{
}
