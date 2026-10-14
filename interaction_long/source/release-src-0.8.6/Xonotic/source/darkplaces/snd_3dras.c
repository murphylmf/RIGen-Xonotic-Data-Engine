      

#include "quakedef.h"
#include "snd_3dras_typedefs.h"
#include "snd_3dras.h"

cvar_t bgmvolume = {CVAR_SAVE, "bgmvolume", "1", "volume of background music (such as CD music or replacement files such as sound/cdtracks/track002.ogg)"};
cvar_t mastervolume = {CVAR_SAVE, "mastervolume", "1", "master volume"};
cvar_t volume = {CVAR_SAVE, "volume", "0.7", "volume of sound effects"};
cvar_t snd_staticvolume = {CVAR_SAVE, "snd_staticvolume", "1", "volume of ambient sound effects (such as swampy sounds at the start of e1m2)"};
cvar_t snd_initialized = { CVAR_READONLY, "snd_initialized", "0", "indicates the sound subsystem is active"};
cvar_t snd_mutewhenidle = {CVAR_SAVE, "snd_mutewhenidle", "1", "whether to disable sound output when game window is inactive"};
static cvar_t snd_precache = {0, "snd_precache", "1", "loads sounds before they are used"};

static dllhandle_t   ras_dll = NULL;
                                                                                                                                    
int ras_version;

static mempool_t *snd_mempool;
static sfx_t sfx_list ={                                                                                                             
	NULL,       
	"",                    
	NULL,            
	0,           
	0           
	                    
	                      
};
static unsigned int channel_id_count=0;
static channel_t channel_list={
	NULL,       
	NULL,             
	0,         
	0,             
	0     
};
static entnum_t  entnum_list={
	NULL,         
	0,              
	{0.0,0.0,0.0},          
	NULL,                                                                                        
};

int   updatecount=0;
int   soundblocked=0;
int   openframe;
void* soundworld;
void* listener;
float listener_location   [3];

                                 
                                     
                                                    
                                                     
                                        
static float DP_Ras_UnitSize=(float)2/1000/1000;       
static float DP_Ras_VolumeScale=0.075;
                                        
                                                       
static float DP_QU_Ras_Scale=19050;
static void* (*ras_delete                     )(void*);
static int   (*ras_getversion                 )();
static void* (*ras_soundworld_new             )(SampleRate, WaveLength);
static void  (*ras_soundworld_destroy         )(void*);
static void  (*ras_soundworld_endframe        )(void*);
static int   (*ras_soundworld_beginframe      )(void*);
static void  (*ras_soundworld_setmainlistener )(void*,void*);
static void  (*ras_soundworld_setscale        )(void*,const Scale);
static void* (*ras_fileinputwhole_new         )(unsigned char*, Index);
static void* (*ras_audiodecoderwav_new        )(void*, int);
static void* (*ras_audiodecoderogg_new        )(void*);
static void* (*ras_sounddataoneshot_new       )(void*,WaveLength,Amount);
static void* (*ras_sounddataloop_new          )(void*,WaveLength,Amount);
static void* (*ras_listener_new               )(void*,Location*,Scalar*);
static void* (*ras_listener_setlocation       )(void*,Location*);
static void* (*ras_listener_setrotation       )(void*,Scalar  *,Scalar*,Scalar*);
static void* (*ras_soundsource_new            )(void*,SoundVolume,Location*);
static int   (*ras_soundsource_ended          )(void*);
static void  (*ras_soundsource_setlocation    )(void*,Location*);
static void* (*ras_soundevent_new             )(void*,void*,void*,SoundPower,Ratio);
static void  (*ras_soundevent_setsoundpower   )(void*,SoundPower);
static int   (*ras_soundevent_ended           )(void*);
static int   (*ras_setcoordinatesystem        )(Location*,Location*,Location*);
static int   (*ras_testrotation               )(Scalar  *,Scalar  *,Scalar  *);

                                                               

static dllfunction_t ras_funcs[] =
{
	{"Delete"                                      ,(void**) &ras_delete                     },
	{"SetCoordinateSystem"                         ,(void**) &ras_setcoordinatesystem        },
	{"TestRotation"                                ,(void**) &ras_testrotation               },
	{"GetVersion"                                  ,(void**) &ras_getversion                 },
	{"SoundWorld_New"                              ,(void**) &ras_soundworld_new             },
	{"SoundWorld_Destroy"                          ,(void**) &ras_soundworld_destroy         },
	{"SoundWorld_EndFrame"                         ,(void**) &ras_soundworld_endframe        },
	{"SoundWorld_BeginFrame"                       ,(void**) &ras_soundworld_beginframe      },
	{"FileInputWhile_New"                          ,(void**) &ras_fileinputwhole_new         },
	{"AudioDecoderFileWav_New"                     ,(void**) &ras_audiodecoderwav_new        },
	{"AudioDecoderFileOgg_New"                     ,(void**) &ras_audiodecoderogg_new        },
	{"SoundDataAudioDecoderOneShot_New"            ,(void**) &ras_sounddataoneshot_new       },
	                                                                                             
	{"SoundWorld_SetMainListener"                  ,(void**) &ras_soundworld_setmainlistener },
	{"SoundWorld_SetScale"                         ,(void**) &ras_soundworld_setscale        },
	{"ListenerPlayer_New"                          ,(void**) &ras_listener_new               },
	{"ListenerPlayer_SetLocation"                  ,(void**) &ras_listener_setlocation       },
	{"ListenerPlayer_SetRotation_InVectors"        ,(void**) &ras_listener_setrotation       },
	{"SoundSource_Ended"                           ,(void**) &ras_soundsource_ended          },
	{"SoundSourcePoint_New"                        ,(void**) &ras_soundsource_new            },
	{"SoundSourcePoint_SetLocation"                ,(void**) &ras_soundsource_setlocation    },
	{"SoundEvent_New"                              ,(void**) &ras_soundevent_new             },
	{"SoundEvent_Ended"                            ,(void**) &ras_soundevent_ended           },
	{"SoundEvent_SetSoundPower"                    ,(void**) &ras_soundevent_setsoundpower   },
	{ NULL                                         , NULL                                      }
};
static const char* ras_dllname [] =
{
#if defined(WIN32)
		"3dras32.dll",
#elif defined(MACOSX)
		"3dras.dylib",
#else
		"3dras.so",
#endif
		NULL
};

                                   
void entnum_new(entnum_t** prev, entnum_t** new){                                                                  
	(*new)=Mem_Alloc(snd_mempool,sizeof(entnum_t));
	if(&new){
		(*new)->next=entnum_list.next;
		entnum_list.next=(*new);
		(*prev)=&entnum_list;
	}else{
		Con_Printf("Could not allocate memory for a new entnum_t");
	}
}
void entnum_begin(entnum_t** prev, entnum_t** now){                                                           
	(*prev)=&entnum_list;
	(*now )=entnum_list.next;
}
void entnum_next(entnum_t** prev, entnum_t** now){                           
	(*prev)=(*now);
	(*now )=(*now)->next;
}
void entnum_delete_and_next(entnum_t** prev, entnum_t** now){                                                   
	entnum_t* next;
	next=(*now)->next;
	if((*now)->rasptr) ras_delete((*now)->rasptr);
	Mem_Free(*now);
	(*now)=next;
	(*prev)->next=(*now);
}
                                          

                                    
void channel_new(channel_t** prev, channel_t** new){                                                                  
	(*new)=Mem_Alloc(snd_mempool,sizeof(channel_t));
	if(&new){
		(*new)->next=channel_list.next;
		channel_list.next=(*new);
		(*prev)=&channel_list;
	}else{
		Con_Printf("Could not allocate memory for a new channel_t");
	}
}
void channel_begin(channel_t** prev, channel_t** now){                                                           
	(*prev)=&channel_list;
	(*now )=channel_list.next;
}
void channel_next(channel_t** prev, channel_t** now){                           
	(*prev)=(*now );
	(*now )=(*now)->next;
}
void channel_delete_and_next(channel_t** prev, channel_t** now){                                                   
	channel_t* next;
	next=(*now)->next;
	if((*now)->rasptr) ras_delete((*now)->rasptr);
	Mem_Free(*now);
	(*now)=next;
	(*prev)->next=(*now);
}
                                           

                                
void sfx_new(sfx_t** prev, sfx_t** new){                                                                  
	(*new)=Mem_Alloc(snd_mempool,sizeof(sfx_t));
	if(&new){
		(*new)->next=sfx_list.next;
		sfx_list.next=(*new);
		(*prev)=&sfx_list;
	}else{
		Con_Printf("Could not allocate memory for a new sfx_t");
	}
}
void sfx_begin(sfx_t** prev, sfx_t** now){                                                           
	(*prev)=&sfx_list;
	(*now )=sfx_list.next;
}
void sfx_next(sfx_t** prev, sfx_t** now){                           
	(*prev)=(*now );
	(*now )=(*now)->next;
}
void sfx_delete_and_next(sfx_t** prev, sfx_t** now){                                                   
	sfx_t* next;
	next=(*now)->next;
	if((*now)->rasptr) ras_delete((*now)->rasptr);
	Mem_Free(*now);
	(*now)=next;
	(*prev)->next=(*now);
}
                                       

void channel_new_smart(channel_t** prev, channel_t** now){
	channel_new(prev,now);
	++channel_id_count;
	(*now)->id=channel_id_count;
}
void Free_Unlocked_Sfx(void){
	sfx_t *prev, *now;
	sfx_begin(&prev,&now);
	while(now){
		if(
			!(now->flags & SFXFLAG_SERVERSOUND) &&
			now->locks<=0
		){
			sfx_delete_and_next(&prev,&now);
		}else{
			sfx_next(&prev,&now);
		}
	}
}
void DP_To_Ras_Location(const float in[3],Location out[3]){
	out[0]=(Location)(in[0]*DP_QU_Ras_Scale );
	out[1]=(Location)(in[1]*DP_QU_Ras_Scale );
	out[2]=(Location)(in[2]*DP_QU_Ras_Scale );
}
void S_Restart_f(void){
	S_Shutdown();
	S_Startup();
}
static void S_Play_Common (float fvol, float attenuation){
	int i;
	char name [MAX_QPATH];
	sfx_t *sfx;
	if(ras_version>0 && ras_dll){
		#ifdef RAS_PRINT
			Con_Printf("Called S_Play_Common\n");
			Con_Printf("Does this need to be location in depend channel ?\n");
		#endif

		i = 1;
		while (i < Cmd_Argc ())
		{
			                                                                   
			strlcpy (name, Cmd_Argv (i), sizeof (name));
			if (!strrchr (name, '.'))
				strlcat (name, ".wav", sizeof (name));
			i++;

			                                                     
			if (fvol == -1.0f)
			{
				fvol = atof (Cmd_Argv (i));
				i++;
			}

			sfx = S_PrecacheSound (name, true, true);
			if (sfx)
				S_StartSound (-1, 0, sfx, listener_location, fvol, attenuation);
		}
	}
}
static void S_Play_f(void){
	S_Play_Common (1.0f, 1.0f);
}
static void S_Play2_f(void){
	S_Play_Common (1.0f, 0.0f);
}
static void S_PlayVol_f(void){
	S_Play_Common (-1.0f, 0.0f);
}
static void S_SoundList_f(void){
	channel_t *prev_c, *now_c;
	    sfx_t *prev_s, *now_s;
	 entnum_t *prev_e, *now_e;
	 int count_c,count_s,count_e;
	
	if(ras_version>0 && ras_dll){

		Con_Printf("Sfx (SoundDatas) :\n"
				 "------------------\n"
				 "Locks\tflags\tpointer\tName\n");
		count_s=0;
		sfx_begin(&prev_s,&now_s);
		while(now_s){
			++count_s;
			Con_Printf("%i\t%i\t%i\t%s\n",
				now_s->locks, now_s->flags, now_s->rasptr!=NULL, now_s->name
			);
			sfx_next(&prev_s,&now_s);
		}

		Con_Printf("Entnum (SoundSources) :\n"
				 "-----------------------\n"
				 "Ent\tpointer\n");
		count_e=0;
		entnum_begin(&prev_e,&now_e);
		while(now_e){
			++count_e;
			Con_Printf("%i\t%i\n",
				now_e->entnum, now_e->rasptr!=NULL
			);
			entnum_next(&prev_e,&now_e);
		}

		Con_Printf("Channels (SoundEvents) :\n"
				 "------------------------\n"
				 "Ent\tChannel\tID\tpointer\n");
		count_c=0;
		channel_begin(&prev_c,&now_c);
		while(now_c){
			++count_c;
			Con_Printf("%i\t%i\t%i\t%i\n",
				now_c->entnum, now_c->entchannel, now_c->id, now_c->rasptr!=NULL
			);
			channel_next(&prev_c,&now_c);
		}

		Con_Printf(
			"Count:\n"
			"------\n"
			"Channels: %i\n"
			"Sfx's:    %i\n"
			"Entities: %i\n",
			count_c,count_s,count_e
		);
	}
}
void Free_All_sfx(){
	sfx_t *prev, *now;
	sfx_begin(&prev,&now);
	while(now) sfx_delete_and_next(&prev,&now);
}
void Free_All_channel(){
	channel_t *prev, *now;
	channel_begin(&prev,&now);
	while(now) channel_delete_and_next(&prev,&now);
}
void Free_All_entnum(){
	entnum_t *prev, *now;
	entnum_begin(&prev,&now);
	while(now) entnum_delete_and_next(&prev,&now);
}
void S_Init (void){
	Location up[3],right[3],front[3];
	ras_version=0;
	snd_mempool = Mem_AllocPool("sound", 0, NULL);
	if(ras_dll) Con_Printf( "3D RAS already loaded ... (this indicates a bug)\n");
	if (Sys_LoadLibrary (ras_dllname, &ras_dll, ras_funcs))
	{
		Con_Printf ("Loading 3D RAS succeeded\n");
		Con_Printf ("Checking the lib version\n");
		ras_version=ras_getversion();
		if (ras_version>0){
			
			Con_Printf ("Version %i found\n",ras_version);
			Cvar_RegisterVariable(&volume);
			Cvar_RegisterVariable(&bgmvolume);
			Cvar_RegisterVariable(&mastervolume);
			Cvar_RegisterVariable(&snd_staticvolume);
			Cvar_RegisterVariable(&snd_precache);

			Cmd_AddCommand("play", S_Play_f, "play a sound at your current location (not heard by anyone else)");
			Cmd_AddCommand("snd_play", S_Play_f, "play a sound at your current location (not heard by anyone else)");
			Cmd_AddCommand("play2", S_Play2_f, "play a sound globally throughout the level (not heard by anyone else)");
			Cmd_AddCommand("snd_play2", S_Play2_f, "play a sound globally throughout the level (not heard by anyone else)");
			Cmd_AddCommand("playvol", S_PlayVol_f, "play a sound at the specified volume level at your current location (not heard by anyone else)");
			Cmd_AddCommand("snd_playvol", S_PlayVol_f, "play a sound at the specified volume level at your current location (not heard by anyone else)");
			Cmd_AddCommand("stopsound", S_StopAllSounds, "silence");
			Cmd_AddCommand("soundlist", S_SoundList_f, "list loaded sounds");
			Cmd_AddCommand("snd_stopsound", S_StopAllSounds, "silence");
			Cmd_AddCommand("snd_soundlist", S_SoundList_f, "list loaded sounds");
			Cmd_AddCommand("snd_restart", S_Restart_f, "restart sound system");
			Cmd_AddCommand("snd_shutdown", S_Shutdown, "shutdown the sound system keeping the dll loaded");
			Cmd_AddCommand("snd_startup", S_Startup, "start the sound system");
			Cmd_AddCommand("snd_unloadallsounds", S_UnloadAllSounds_f, "unload all sound files");

			                                                                      
			   up[0]= 0 ,   up[1]= 0 ,    up[2]=1;
			right[0]= 0 ,right[1]=-1 , right[2]=0;
			front[0]= 1 ,front[1]= 0 , front[2]=0;
			if(ras_setcoordinatesystem(right,up,front)==0){
				Con_Printf("Failed to set the Coordinate System\n");
				ras_version=0;
			}
		}else{
			Con_Printf ("Failed to get the lib version\n");
			Sys_UnloadLibrary (&ras_dll);
			ras_dll=0;
		}
	}else{
		ras_dll=0;
		Con_Printf ("Loading 3D RAS failed\n");
		Sys_UnloadLibrary (&ras_dll);
	}
}
void S_Terminate (void){
	if(ras_dll){
		S_Shutdown();
		Free_All_sfx();                                            
		Sys_UnloadLibrary(&ras_dll);
		ras_dll=0;
		ras_version=0;
	}
}

void S_Startup (void){
	Location loc[3]={0, 0, 0};
	Scalar   rot[4]={1.0, 0, 0, 0};
	if(ras_version>0 && ras_dll){
		channel_id_count=1;
		soundworld= ras_soundworld_new(48000,0.1);
		if(soundworld==0){
			Con_Printf("Failed to start a SoundWorld\n");
		}else{
			Con_Printf("Succeeded in starting a new SoundWorld\n");
			listener=ras_listener_new(soundworld,loc,rot);
			ras_soundworld_setmainlistener(soundworld,listener);
			openframe = ras_soundworld_beginframe(soundworld);
			ras_soundworld_setscale(soundworld,DP_Ras_UnitSize);
		}
	}
}
void S_Shutdown (void){
	if(ras_version>0 && ras_dll && soundworld){
		if(openframe) ras_soundworld_endframe(soundworld);
		
		                                                                          
		                                                                                             
		Free_All_channel();
		Free_All_entnum();
		
		ras_soundworld_destroy(soundworld);
		soundworld=ras_delete(soundworld);
		if(soundworld){
			Con_Printf("Failed to stop the SoundWorld\n");
		}else{
			Con_Printf("Succeeded in stopping the SoundWorld\n");
		}
	}
}
void S_UnloadAllSounds_f(void){
	if(ras_version>0 && ras_dll){
		Free_All_sfx();
	}
}

void S_Update(const matrix4x4_t *listener_matrix){
	float forward   [3];
	float left      [3];
	float up        [3];
	float float3    [3];
	Location location3 [3];
	entnum_t  *prev_e, *now_e;
	channel_t *prev_c, *now_c;
	if(ras_version>0 && ras_dll && soundworld){
		Matrix4x4_ToVectors(listener_matrix,forward,left,up,listener_location);                               
		if(openframe){
			VectorNegate(left,left);
			DP_To_Ras_Location(listener_location,location3);
			ras_listener_setlocation(listener,location3);
			ras_listener_setrotation(listener,left,up,forward);
			  
              
                                                            
                                     
                                     
                                    
     
                                     
              
                                                            
                                     
                                     
                                    
     
     
			if(updatecount>100){
				updatecount=0;
				#ifdef RAS_PRINT
				Con_Printf("S_Update: Add a callback to SCR_CaptureVideo_SoundFrame.\n");
				Con_Printf("S_Update: Add Slomo.\n");
				Con_Printf("S_Update: Add BlockedSoundCheck.\n");
				Con_Printf("S_Update: Add Slomo(as a cvar) and pauze.\n");
				#endif
			}else{
				++updatecount;
			}
			                                                                     
			                                          
			if(cl.entities){                             
				                                                            
				entnum_begin(&prev_e,&now_e);
				while(now_e){
					if(!now_e->rasptr){
						Con_Printf("S_Update: Found an entnum_t without a valid RAS-ptr... This indicates a bug.\n");
						entnum_delete_and_next(&prev_e,&now_e);
					}else{                                     
						if(now_e->entnum!=-1){                                                    
							if(ras_soundsource_ended(now_e->rasptr)){
									VectorCopy(cl.entities[now_e->entnum].state_current.origin,float3);
									VectorCopy(now_e->lastloc,float3);
									DP_To_Ras_Location(float3,location3);
									ras_soundsource_setlocation(now_e->rasptr,location3);
									entnum_next(&prev_e,&now_e);
							}else{
								entnum_delete_and_next(&prev_e,&now_e);
							}
						}else{
							if(ras_soundsource_ended(now_e->rasptr)){
								entnum_delete_and_next(&prev_e,&now_e);
							}else{
								entnum_next(&prev_e,&now_e);
							}
						}
					}
				}
			}else{
				Free_All_entnum();
			}
			channel_begin(&prev_c,&now_c);
			while(now_c){
				if(!now_c->rasptr){
					Con_Printf("S_Update: Found an channel_t without a valid RAS-ptr... This indicates a bug.\n");
					channel_delete_and_next(&prev_c,&now_c);
				}else{                                                
					if(ras_soundevent_ended(now_c->rasptr)){
						channel_delete_and_next(&prev_c,&now_c);
					}else{
						channel_next(&prev_c,&now_c);
					}
				}
			}
			ras_soundworld_endframe  (soundworld);
		}
		openframe =ras_soundworld_beginframe(soundworld);
	}
}
void S_ExtraUpdate (void){
	                                               
	                               
	   
}
sfx_t* S_FindName (const char *name){
	sfx_t *prev,*now;
	if(ras_version>0 && ras_dll){
		#ifdef RAS_PRINT
		Con_Printf("Called S_FindName %s\n",name);
		#endif

		if (strlen (name) >= sizeof (now->name))
		{
			Con_Printf ("S_FindName: sound name too long (%s)\n", name);
			return NULL;
		}
		
		sfx_begin(&prev,&now);
		               
		while (now){
			if(strcmp (now->name, name)==0) return now;
			sfx_next(&prev,&now);
		}
		
		                          
		                                    
		sfx_new(&prev,&now);
		now->locks=0;
		now->flags=0;
		now->rasptr=0;
		                    
		                      
		strlcpy (now->name, name, sizeof (now->name));
		return now;
	}
	return NULL;
}
int S_LoadSound(sfx_t *sfx, int complain){
	                                                                     
	fs_offset_t filesize;
	char namebuffer[MAX_QPATH +16  ];
	char filename  [MAX_QPATH +16+4];
	char fileext   [4];
	size_t len;
	unsigned char *data=NULL;
	void* file_ptr=NULL;
	void* decoder_ptr=NULL;
	if(ras_version>0 && ras_dll){

		fileext[3]=0;             
		                        
		if (sfx->rasptr) return true;

		                                                                             
		if (!data && strncasecmp(sfx->name, "sound/", 6))
		{
			len = dpsnprintf (namebuffer, sizeof(namebuffer), "sound/%s", sfx->name);
			if (len < 0){                 
				Con_DPrintf("S_LoadSound: name \"%s\" is too long\n", sfx->name);
				return false;
			}
			if(!data){
				data = FS_LoadFile(namebuffer, snd_mempool, false, &filesize);
				if(data) memcpy(fileext,namebuffer+len-3,3);                     
			}
			if(!data){                                      
				memcpy(filename,namebuffer,len);
				memcpy(filename+len-4,".wav",5);
				data = FS_LoadFile(filename, snd_mempool, false, &filesize);
				if(data) memcpy(fileext,"wav",3);
			}
			if(!data){                                      
				memcpy(filename,namebuffer,len);
				memcpy(filename+len-4,".ogg",5);
				data = FS_LoadFile(filename, snd_mempool, false, &filesize);
				if(data) memcpy(fileext,"ogg",3);
			}
		}
		if(!data){
			                                                              
			len = dpsnprintf (namebuffer, sizeof(namebuffer), "%s", sfx->name);
			if (len < 0){                 
				Con_DPrintf("S_LoadSound: name \"%s\" is too long\n", sfx->name);
				return false;
			}
			if(!data){
				data = FS_LoadFile(namebuffer, snd_mempool, false, &filesize);
				if(data) memcpy(fileext,namebuffer+len-3,3);                          
			}
			if(!data){                        
				memcpy(filename,namebuffer,len);
				memcpy(filename+len-4,".wav",5);
				data = FS_LoadFile(filename, snd_mempool, false, &filesize);
				if(data) memcpy(fileext,"wav",3);
			}
			if(!data){                        
				memcpy(filename,namebuffer,len);
				memcpy(filename+len-4,".ogg",5);
				data = FS_LoadFile(filename, snd_mempool, false, &filesize);
				if(data) memcpy(fileext,"ogg",3);
			}
		}
		if (!data){
			if(complain) Con_Printf("Failed attempt load file '%s'\n",namebuffer);
		}else{                                     
			file_ptr=ras_fileinputwhole_new(data,filesize);
			                                        
			                                  
			FS_Close(data);

			if(!file_ptr){
				Con_Printf("Failed to upload file to audio lib\n");
			}else{
				if(0==strncasecmp(fileext,"wav",3)){
					decoder_ptr=ras_audiodecoderwav_new(file_ptr,true);                                                    
				}
				if(0==strncasecmp(fileext,"ogg",3)){
					decoder_ptr=ras_audiodecoderogg_new(file_ptr);
				}
				if(!decoder_ptr){
					Con_Printf("File succeeded to load, but no decoder available for '%s'\n",fileext);
				}else{
					#ifdef RAS_PRINT
					Con_Printf("ToDo: Add a cvar to configure the cache size and number of cache blocks.\n");
					Con_Printf("ToDo: Add support for looping sounds.\n");
					#endif
					sfx->rasptr=ras_sounddataoneshot_new(decoder_ptr,0.05,8);
				}
				file_ptr=ras_delete(file_ptr);
			}
			return !(sfx->rasptr);
		}
		return false;
	}
	return false;
}
sfx_t *S_PrecacheSound (const char *name, qboolean complain, qboolean serversound){
	sfx_t *sfx;
	if(ras_version>0 && ras_dll){
		#ifdef RAS_PRINT
		Con_Printf("Called S_PrecacheSound %s, %i, %i\n",name,complain,serversound);
		#endif
		if (name == NULL || name[0] == 0)
			return NULL;
		sfx = S_FindName (name);
		if (sfx == NULL) return NULL;
		if (lock) ++(sfx->locks);
		if (snd_precache.integer) S_LoadSound(sfx, complain);
		return sfx;
	}
	return NULL;
}
void S_ClearUsed (void){
	sfx_t *prev_s, *now_s;
	unsigned int i;

	if(ras_version>0 && ras_dll){
		Con_Printf("Called S_ClearUsed\n");
		for(i=0;i<numsounds;++i){
			Con_Printf("Loading :'%s'\n",serversound[i]);
			                          

			Con_Printf("ToDo: Load abmient sounds (Need geometry).\n");

			                                      
			sfx_begin(&prev_s,&now_s);
			while(now_s){
				if (now_s->flags & SFXFLAG_SERVERSOUND) now_s->flags &= ~SFXFLAG_SERVERSOUND;
				sfx_next(&prev_s,&now_s);
			}
		}
	}
}
void S_PurgeUnused(void){
	Free_Unlocked_Sfx();
}
qboolean S_IsSoundPrecached (const sfx_t *sfx){
	if(ras_version>0 && ras_dll){
		return !sfx->rasptr;
	}
	return 0;
}

void S_KillChannel (channel_t *now){                        
	if(now->rasptr){
		ras_soundevent_setsoundpower(now->rasptr,0);
		ras_delete(now->rasptr);
		now->rasptr=0;
	}else{
		Con_Printf("S_KillChannel: Warning pointer was 0 ... this indicates a bug.\n");
	}
}

int S_StartSound_OnEnt (int entnum, int entchannel, sfx_t *sfx, float fvol, float attenuation){
	 entnum_t *prev_e, *now_e;
	channel_t *prev_c, *now_c;
	Location tmp_location[3];

	                          
	if(!cl.entities){
		Con_Printf("S_StartSound_OnEnt: no entity list exists\n");
		return -1;
	}

	                             
	entnum_begin(&prev_e,&now_e);
	while(now_e){
		if(now_e->entnum==entnum) break;
		entnum_next(&prev_e,&now_e);
	}
	                                       
	if(!now_e){
		entnum_new(&prev_e,&now_e);
		if(!now_e){
			Con_Printf("S_StartSound_OnEnt: could not make new entnum_t\n");
			return -1;
		}
		VectorCopy(cl.entities[entnum].state_current.origin, now_e->lastloc);
		DP_To_Ras_Location(now_e->lastloc,tmp_location);
		now_e->rasptr=ras_soundsource_new(soundworld,1.0,tmp_location);
		if(!now_e->rasptr){
			Con_Printf("S_StartSound_OnEnt: could not create a new sound source\n");
			return -1;
		}
	}

	                                   
	channel_begin(&prev_c,&now_c);
	while(now_c){
		if(
			now_c->entnum==entnum &&
			now_c->entchannel==entchannel
		) break;
		channel_next(&prev_c,&now_c);
	}
	
	if(now_c){                                  
		S_KillChannel(now_c);
	}else{                                                            
		channel_new_smart(&prev_c,&now_c);
		if(!now_c){
			Con_Printf("S_StartSound_OnEnt: could not make new channel_t\n");
			channel_delete_and_next(&prev_c,&now_c);
			return -1;
		}
		now_c->entnum    =entnum;
		now_c->entchannel=entchannel;
	}

	                                                               
	now_c->rasptr=ras_soundevent_new(
		soundworld,now_e->rasptr,sfx->rasptr,fvol*DP_Ras_VolumeScale,1.0
	);
	if(!now_c->rasptr){                                                 
		channel_delete_and_next(&prev_c,&now_c);
		Con_Printf("S_StartSound_OnEnt: could not make a new soundevent.\n");
		return -1;
	}
	return now_c->id;
}
int S_StartSound_OnLocation (sfx_t *sfx, vec3_t origin, float fvol, float attenuation){
	 entnum_t *prev_e, *now_e;
	channel_t *prev_c, *now_c;
	Location tmp_location[3];
	DP_To_Ras_Location(origin,tmp_location);
	
	 entnum_new      (&prev_e,&now_e);
	VectorCopy(now_e->lastloc,origin);
	now_e->entnum=-1;
	now_e->rasptr=ras_soundsource_new(soundworld,1.0,tmp_location);
	if(!now_e->rasptr){
		Con_Printf("S_StartSound_OnLocation: Could not make a new soundsource.\n");
		entnum_delete_and_next(&prev_e,&now_e);
		return -1;
	}
	channel_new_smart(&prev_c,&now_c);
	now_c->entnum=-1;
	now_c->entchannel=-1;
	now_c->rasptr =ras_soundevent_new(soundworld,now_e->rasptr,sfx->rasptr,fvol*DP_Ras_VolumeScale,1.0);
	if(!now_c->rasptr){
		 entnum_delete_and_next(&prev_e,&now_e);
		channel_delete_and_next(&prev_c,&now_c);
		Con_Printf("S_StartSound_OnLocation: Could not make a new soundevent.\n");
		return -1;
	}
	return now_c->id;
}


                                               
                                               
                                                                                  
                                                             
                                                                                                     
                                                         
                                                                                                   
                                                 
                                                                
                                                                                  
                                                                             
                                                                     

int S_StartSound (int entnum, int entchannel, sfx_t *sfx, vec3_t origin, float fvol, float attenuation){
	sfx_t *prev_s,*now_s;
	int sfx_ok;
	if(ras_version>0 && ras_dll && soundworld){
		#ifdef RAS_PRINT
		Con_Printf("Called S_StartSound %i, %i, %f, %f\n",entnum,entchannel,fvol,attenuation);
		#endif
		if(sfx==NULL){                                                          
			#ifdef RAS_PRINT
			Con_Printf("S_StartSound: forgot to mention a sfx!\n");
			#endif
			return -1;
		}

		sfx_ok=0;
		sfx_begin(&prev_s,&now_s);
		while(now_s){
			if(now_s==sfx){
				sfx_ok=1;
				break;
			}
			sfx_next(&prev_s,&now_s);
		}
		if(!sfx_ok){
			Con_Printf("S_StartSound: passed illegal sfx_t!\n");
			return -1;
		}
		if (!S_LoadSound(sfx,true)) return -1;


		if(entnum!=-1){                                 
			return S_StartSound_OnEnt(entnum,entchannel,sfx,fvol,attenuation);
		}else{
			return S_StartSound_OnLocation(      sfx,origin,fvol,attenuation);
		}
	}
	Con_Printf("S_StartSound: engine not stated\n");
	return -1;
}
qboolean S_LocalSound (const char *s){
	sfx_t	*sfx;
	int		ch_ind;
	if(ras_version>0 && ras_dll){
		#ifdef RAS_PRINT
		Con_Printf("Called S_LocalSound %s\n",s);
		#endif

		sfx = S_PrecacheSound (s, true, true);
		if (!sfx)
		{
			Con_Printf("S_LocalSound: can't precache %s\n", s);
			return false;
		}

		                                 
		sfx->flags |= SFXFLAG_PERMANENTLOCK;
		#ifdef RAS_PRINT
		Con_Printf("S_LocalSound: this is still a small hack\n");
		#endif
		ch_ind = S_StartSound (cl.viewentity, 0, sfx, listener_location, 1, 0);
		if (ch_ind < 0)
			return false;

		                                                   
		return true;
	}
	return 0;
}
void S_StaticSound (sfx_t *sfx, vec3_t origin, float fvol, float attenuation){
	                                    
	if(ras_version>0 && ras_dll){
		#ifdef RAS_PRINT
		Con_Printf("Called S_StaticSound\n");
		Con_Printf("Waiting on Qantourisc to add Static sounds in his lib.\n");
		#endif
		                                                                      
	}
}
void S_StopSound (int entnum, int entchannel){
	channel_t *prev, *now;
	if(ras_version>0 && ras_dll){
		                                                              
		channel_begin(&prev,&now);
		while(now){
			if(now->entnum==entnum && now->entchannel==entchannel) break;
			channel_next(&prev,&now);
		}
		if(now){                                   
			S_KillChannel(now);
			channel_delete_and_next(&prev,&now);
		}else{
			Con_Printf("S_StopSound: Could not find the requested entnum-entchannel sound\n");
		}
	}
}
void S_StopAllSounds (void){
	channel_t *prev, *now;
	if(ras_version>0 && ras_dll){
		                                         
		channel_begin(&prev,&now);
		while(now){
			S_KillChannel(now);
			channel_next(&prev,&now);
		}
	}
}
void S_PauseGameSounds (qboolean toggle){
	if(ras_version>0 && ras_dll){
		Con_Printf("Called S_PauseGameSounds %i\n",toggle);
		                                  
	}
}
void S_StopChannel (unsigned int channel_ind){
	channel_t *prev,*now;
	if(ras_version>0 && ras_dll){
		channel_begin(&prev,&now);
		while(now){
			if(now->id==channel_ind){
				S_KillChannel(now);
				channel_delete_and_next(&prev,&now);
			}else{
				channel_next(&prev,&now);
			}
		}
	}
}
qboolean S_SetChannelFlag (unsigned int ch_ind, unsigned int flag, qboolean value){
	if(ras_version>0 && ras_dll){
		Con_Printf("Called S_SetChannelFlag %u, %u, %i\n",ch_ind, flag, value);
	}
	return 0;
}
void S_SetChannelVolume (unsigned int ch_ind, float fvol){
	channel_t *prev,*now;
	if(ras_version>0 && ras_dll){
		Con_Printf("Called S_SetChannelVolume %u, %f\n",ch_ind, fvol);
		channel_begin(&prev,&now);
		while(now){
			if(now->id==ch_ind){
				if(now->rasptr){
					ras_soundevent_setsoundpower(now->rasptr,fvol*DP_Ras_VolumeScale);
				}else{
					Con_Printf("S_StopChannel: Warning pointer was 0 ... this indicates a bug.\n");
				}
			}
			channel_next(&prev,&now);
		}
	}
}

float S_GetChannelPosition (unsigned int ch_ind)
{
	                    
	return -1;
}

void S_BlockSound (void){
	soundblocked++;
}
void S_UnblockSound (void){
	soundblocked--;
	if(soundblocked<0){
		Con_Printf("S_UnblockSound: Requested more S_UnblockSound then S_BlockSound.\n");
	}
}

int S_GetSoundRate (void){
	Con_Printf("Inside 3DRAS, the soundrate of the end-user is NONE of the dev's concern.\n");
	Con_Printf("So let's assume 44100.\n");
	return 44100;
}

int S_GetSoundChannels (void){
	Con_Printf("Inside 3DRAS, the soundrate of the end-user is NONE of the dev's concern.\n");
	Con_Printf("So let's assume 2.\n");
	return 2;
}

  
                    
                    

                                                                  
                    
  
void SndSys_SendKeyEvents(void)
{
	                
}
