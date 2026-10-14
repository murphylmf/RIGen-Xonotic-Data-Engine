  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

#ifndef SND_MAIN_H
#define SND_MAIN_H

#include "sound.h"


typedef struct snd_format_s
{
	unsigned int	speed;
	unsigned short	width;
	unsigned short	channels;
} snd_format_t;

typedef struct snd_buffer_s
{
	snd_format_t		format;
	unsigned int		nbframes;	                                 
	unsigned int		maxframes;	                                           
	unsigned char		samples[4];	                 
} snd_buffer_t;

typedef struct snd_ringbuffer_s
{
	snd_format_t		format;
	unsigned char*		ring;
	unsigned int		maxframes;	                                           
	unsigned int		startframe;	                                         
									                                                  
	unsigned int		endframe;	                                                      
									                                                                  
} snd_ringbuffer_t;

              
#define SFXFLAG_NONE			0
#define SFXFLAG_FILEMISSING		(1 << 0)                                                 
#define SFXFLAG_LEVELSOUND		(1 << 1)                                                                        
#define SFXFLAG_STREAMED		(1 << 2)                                                     
#define SFXFLAG_MENUSOUND		(1 << 3)                                                           

typedef struct snd_fetcher_s snd_fetcher_t;
struct sfx_s
{
	char				name[MAX_QPATH];
	sfx_t				*next;
	size_t				memsize;		                                                       

	snd_format_t		format;			                                                                             
	unsigned int		flags;			                       
	unsigned int		loopstart;		                                                      
	unsigned int		total_length;	                   
	const snd_fetcher_t	*fetcher;
	void				*fetcher_data;	                                                

	float				volume_mult;                                            
	float				volume_peak;                                                                              
};

                                      
#define SND_LISTENERS 8

typedef struct channel_s
{
	                             
	sfx_t			*sfx;			                                     
	float			basevolume;		                    
	unsigned int	flags;			                           
	int				entnum;			                                                                                             
	int				entchannel;		                                 
	vec3_t			origin;			                         
	vec_t			distfade;		                                          
	void			*fetcher_data;	                                                   
	int				prologic_invert;                                                                 
	float			basespeed;		                                               

	                                                                                                                                         
	                                                     
	float			mixspeed;
	                                                                                         
	float			volume[SND_LISTENERS];

	                        
	                                                                    
	double			position;
} channel_t;

                           
                                                                                                      
typedef void (*snd_fetcher_getsamplesfloat_t) (channel_t *ch, sfx_t *sfx, int firstsampleframe, int numsampleframes, float *outsamplesfloat);
typedef void (*snd_fetcher_stopchannel_t) (channel_t *ch);
typedef void (*snd_fetcher_freesfx_t) (sfx_t *sfx);
struct snd_fetcher_s
{
	snd_fetcher_getsamplesfloat_t		getsamplesfloat;
	snd_fetcher_stopchannel_t		stopchannel;
	snd_fetcher_freesfx_t		freesfx;
};

extern unsigned int total_channels;
extern channel_t channels[MAX_CHANNELS];

extern snd_ringbuffer_t *snd_renderbuffer;
extern qboolean snd_threaded;                                                                                                    
extern qboolean snd_usethreadedmixing;                                                                                                                                                                                    

extern cvar_t _snd_mixahead;
extern cvar_t snd_swapstereo;
extern cvar_t snd_streaming;
extern cvar_t snd_streaming_length;

#define SND_CHANNELLAYOUT_AUTO		0
#define SND_CHANNELLAYOUT_STANDARD	1
#define SND_CHANNELLAYOUT_ALSA		2
extern cvar_t snd_channellayout;

extern int snd_blocked;		                                                                  

extern mempool_t *snd_mempool;

                                                                                          
                                                                         
                                                  
extern qboolean simsound;


#define STREAM_BUFFERSIZE 16384                   


                                                                       
                                             
                                                                       

void S_MixToBuffer(void *stream, unsigned int frames);

qboolean S_LoadSound (sfx_t *sfx, qboolean complain);

snd_buffer_t *Snd_CreateSndBuffer (const unsigned char *samples, unsigned int sampleframes, const snd_format_t* in_format, unsigned int sb_speed);
qboolean Snd_AppendToSndBuffer (snd_buffer_t* sb, const unsigned char *samples, unsigned int sampleframes, const snd_format_t* format);

                                                                                                
                                                           
snd_ringbuffer_t *Snd_CreateRingBuffer (const snd_format_t* format, unsigned int sampleframes, void* buffer);


                                                                       
                                           
                                                                       

                                                                                   
                                                                        
qboolean SndSys_Init (const snd_format_t* requested, snd_format_t* suggested);

                                                                              
void SndSys_Shutdown (void);

                                                              
void SndSys_Submit (void);

                                                                       
unsigned int SndSys_GetSoundTime (void);

                                               
qboolean SndSys_LockRenderBuffer (void);

                                                   
void SndSys_UnlockRenderBuffer (void);

                                                     
void SndSys_SendKeyEvents(void);

                                                        
typedef struct portable_samplepair_s
{
	float sample[SND_LISTENERS];
} portable_sampleframe_t;

typedef struct listener_s
{
	int channel_unswapped;                   
	float yawangle;
	float dotscale;
	float dotbias;
	float ambientvolume;
}
listener_t;
typedef struct speakerlayout_s
{
	const char *name;
	unsigned int channels;
	listener_t listeners[SND_LISTENERS];
}
speakerlayout_t;

#endif
