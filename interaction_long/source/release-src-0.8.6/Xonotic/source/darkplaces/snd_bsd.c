  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
#include "quakedef.h"

#include <sys/param.h>
#include <sys/audioio.h>
#ifndef SUNOS
#	include <sys/endian.h>
#endif
#include <sys/ioctl.h>

#include <fcntl.h>
#ifndef SUNOS
#	include <paths.h>
#endif
#include <unistd.h>

#include "snd_main.h"


static int audio_fd = -1;


  
                    
           

                                                                                
                                                                     
                    
  
qboolean SndSys_Init (const snd_format_t* requested, snd_format_t* suggested)
{
	unsigned int i;
	const char *snddev;
	audio_info_t info;

	                        
#ifdef _PATH_SOUND
	snddev = _PATH_SOUND;
#elif defined(SUNOS)
	snddev = "/dev/audio";
#else
	snddev = "/dev/sound";
#endif
	audio_fd = open (snddev, O_WRONLY | O_NDELAY | O_NONBLOCK);
	if (audio_fd < 0)
	{
		Con_Printf("Can't open the sound device (%s)\n", snddev);
		return false;
	}

	AUDIO_INITINFO (&info);
#ifdef AUMODE_PLAY	                   
	info.mode = AUMODE_PLAY;
#endif
	info.play.sample_rate = requested->speed;
	info.play.channels = requested->channels;
	info.play.precision = requested->width * 8;
	if (requested->width == 1)
#ifdef SUNOS
		info.play.encoding = AUDIO_ENCODING_LINEAR8;
#else
		info.play.encoding = AUDIO_ENCODING_ULINEAR;
#endif
	else
#ifdef SUNOS
		info.play.encoding = AUDIO_ENCODING_LINEAR;
#else
	if (mem_bigendian)
		info.play.encoding = AUDIO_ENCODING_SLINEAR_BE;
	else
		info.play.encoding = AUDIO_ENCODING_SLINEAR_LE;
#endif

	if (ioctl (audio_fd, AUDIO_SETINFO, &info) != 0)
	{
		Con_Printf("Can't set up the sound device (%s)\n", snddev);
		return false;
	}

	                                                
	                                                            

	snd_renderbuffer = Snd_CreateRingBuffer(requested, 0, NULL);
	return true;
}


  
                    
               

                                                                           
                    
  
void SndSys_Shutdown (void)
{
	if (audio_fd >= 0)
	{
		close(audio_fd);
		audio_fd = -1;
	}

	if (snd_renderbuffer != NULL)
	{
		Mem_Free(snd_renderbuffer->ring);
		Mem_Free(snd_renderbuffer);
		snd_renderbuffer = NULL;
	}
}


  
                    
             

                                                           
                    
  
void SndSys_Submit (void)
{
	unsigned int startoffset, factor, limit, nbframes;
	int written;

	if (audio_fd < 0 ||
		snd_renderbuffer->startframe == snd_renderbuffer->endframe)
		return;

	startoffset = snd_renderbuffer->startframe % snd_renderbuffer->maxframes;
	factor = snd_renderbuffer->format.width * snd_renderbuffer->format.channels;
	limit = snd_renderbuffer->maxframes - startoffset;
	nbframes = snd_renderbuffer->endframe - snd_renderbuffer->startframe;
	if (nbframes > limit)
	{
		written = write (audio_fd, &snd_renderbuffer->ring[startoffset * factor], limit * factor);
		if (written < 0)
		{
			Con_Printf("SndSys_Submit: audio write returned %d!\n", written);
			return;
		}

		if (written % factor != 0)
			Sys_Error("SndSys_Submit: nb of bytes written (%d) isn't aligned to a frame sample!\n", written);

		snd_renderbuffer->startframe += written / factor;

		if ((unsigned int)written < limit * factor)
		{
			Con_Printf("SndSys_Submit: audio can't keep up! (%u < %u)\n", written, limit * factor);
			return;
		}

		nbframes -= limit;
		startoffset = 0;
	}

	written = write (audio_fd, &snd_renderbuffer->ring[startoffset * factor], nbframes * factor);
	if (written < 0)
	{
		Con_Printf("SndSys_Submit: audio write returned %d!\n", written);
		return;
	}
	snd_renderbuffer->startframe += written / factor;
}


  
                    
                   

                                                                    
                    
  
unsigned int SndSys_GetSoundTime (void)
{
	audio_info_t info;

	if (ioctl (audio_fd, AUDIO_GETINFO, &info) < 0)
	{
		Con_Print("Error: can't get audio info\n");
		SndSys_Shutdown ();
		return 0;
	}

	return info.play.samples;
}


  
                    
                       

                                            
                    
  
qboolean SndSys_LockRenderBuffer (void)
{
	                
	return true;
}


  
                    
                         

                                                
                    
  
void SndSys_UnlockRenderBuffer (void)
{
	                
}

  
                    
                    

                                                                  
                    
  
void SndSys_SendKeyEvents(void)
{
	                
}
