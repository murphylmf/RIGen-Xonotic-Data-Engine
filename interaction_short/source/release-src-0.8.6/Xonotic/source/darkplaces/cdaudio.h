  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

typedef struct cl_cdstate_s
{
	qboolean Valid;
	qboolean Playing;
	qboolean PlayLooping;
	unsigned char PlayTrack;
}
cl_cdstate_t;

                         

extern qboolean cdValid;
extern qboolean cdPlaying;
extern qboolean cdPlayLooping;
extern unsigned char cdPlayTrack;

extern cvar_t cdaudioinitialized;

int CDAudio_Init(void);
void CDAudio_Open(void);
void CDAudio_Close(void);
void CDAudio_Play(int track, qboolean looping);
void CDAudio_Play_byName (const char *trackname, qboolean looping, qboolean tryreal, float startposition);
void CDAudio_Stop(void);
void CDAudio_Pause(void);
void CDAudio_Resume(void);
int CDAudio_Startup(void);
void CDAudio_Shutdown(void);
void CDAudio_Update(void);
float CDAudio_GetPosition(void);
void CDAudio_StartPlaylist(qboolean resume);

                                               
void CDAudio_SysEject (void);
void CDAudio_SysCloseDoor (void);
int CDAudio_SysGetAudioDiskInfo (void);
float CDAudio_SysGetVolume (void);
void CDAudio_SysSetVolume (float volume);
int CDAudio_SysPlay (int track);
int CDAudio_SysStop (void);
int CDAudio_SysPause (void);
int CDAudio_SysResume (void);
int CDAudio_SysUpdate (void);
void CDAudio_SysInit (void);
int CDAudio_SysStartup (void);
void CDAudio_SysShutdown (void);
