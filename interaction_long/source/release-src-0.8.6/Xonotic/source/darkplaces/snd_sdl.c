  
                                 

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           
  
#include <math.h>
#include <SDL.h>

#include "quakedef.h"

#include "snd_main.h"


static unsigned int sdlaudiotime = 0;
static int audio_device = 0;


                                                                                                     
static void Buffer_Callback (void *userdata, Uint8 *stream, int len)
{
	unsigned int factor, RequestedFrames, MaxFrames, FrameCount;
	unsigned int StartOffset, EndOffset;

	factor = snd_renderbuffer->format.channels * snd_renderbuffer->format.width;
	if ((unsigned int)len % factor != 0)
		Sys_Error("SDL sound: invalid buffer length passed to Buffer_Callback (%d bytes)\n", len);

	RequestedFrames = (unsigned int)len / factor;

	if (SndSys_LockRenderBuffer())
	{
		if (snd_usethreadedmixing)
		{
			S_MixToBuffer(stream, RequestedFrames);
			if (snd_blocked)
				memset(stream, snd_renderbuffer->format.width == 1 ? 0x80 : 0, len);
			SndSys_UnlockRenderBuffer();
			return;
		}

		                                                                     
		MaxFrames = snd_renderbuffer->endframe - snd_renderbuffer->startframe;
		if (MaxFrames > RequestedFrames)
			FrameCount = RequestedFrames;
		else
			FrameCount = MaxFrames;
		StartOffset = snd_renderbuffer->startframe % snd_renderbuffer->maxframes;
		EndOffset = (snd_renderbuffer->startframe + FrameCount) % snd_renderbuffer->maxframes;
		if (StartOffset > EndOffset)                        
		{
			unsigned int PartialLength1, PartialLength2;

			PartialLength1 = (snd_renderbuffer->maxframes - StartOffset) * factor;
			memcpy(stream, &snd_renderbuffer->ring[StartOffset * factor], PartialLength1);

			PartialLength2 = FrameCount * factor - PartialLength1;
			memcpy(&stream[PartialLength1], &snd_renderbuffer->ring[0], PartialLength2);

			                                                                                         
			                                                                                            
			memset(&stream[PartialLength1 + PartialLength2], snd_renderbuffer->format.width == 1 ? 0x80 : 0, len - (PartialLength1 + PartialLength2));
		}
		else
		{
			memcpy(stream, &snd_renderbuffer->ring[StartOffset * factor], FrameCount * factor);

			                                                                                         
			                                                                                            
			memset(&stream[FrameCount * factor], snd_renderbuffer->format.width == 1 ? 0x80 : 0, len - (FrameCount * factor));
		}

		snd_renderbuffer->startframe += FrameCount;

		if (FrameCount < RequestedFrames && developer_insane.integer && vid_activewindow)
			Con_DPrintf("SDL sound: %u sample frames missing\n", RequestedFrames - FrameCount);

		sdlaudiotime += RequestedFrames;

		SndSys_UnlockRenderBuffer();
	}
}


  
                    
           

                                                                                
                                                                     
                    
  
qboolean SndSys_Init (const snd_format_t* requested, snd_format_t* suggested)
{
	unsigned int buffersize;
	SDL_AudioSpec wantspec;
	SDL_AudioSpec obtainspec;

	snd_threaded = false;

	Con_DPrint ("SndSys_Init: using the SDL module\n");

	                               
	if( SDL_InitSubSystem( SDL_INIT_AUDIO ) ) {
		Con_Print( "Initializing the SDL Audio subsystem failed!\n" );
		return false;
	}

	buffersize = (unsigned int)ceil((double)requested->speed / 25.0);                                

	                               
	wantspec.callback = Buffer_Callback;
	wantspec.userdata = NULL;
	wantspec.freq = requested->speed;
	wantspec.format = ((requested->width == 1) ? AUDIO_U8 : AUDIO_S16SYS);
	wantspec.channels = requested->channels;
	wantspec.samples = CeilPowerOf2(buffersize);                                                

	Con_Printf("Wanted audio Specification:\n"
				"\tChannels  : %i\n"
				"\tFormat    : 0x%X\n"
				"\tFrequency : %i\n"
				"\tSamples   : %i\n",
				wantspec.channels, wantspec.format, wantspec.freq, wantspec.samples);

	if ((audio_device = SDL_OpenAudioDevice(NULL, 0, &wantspec, &obtainspec, 0)) == 0)
	{
		Con_Printf( "Failed to open the audio device! (%s)\n", SDL_GetError() );
		return false;
	}

	Con_Printf("Obtained audio specification:\n"
				"\tChannels  : %i\n"
				"\tFormat    : 0x%X\n"
				"\tFrequency : %i\n"
				"\tSamples   : %i\n",
				obtainspec.channels, obtainspec.format, obtainspec.freq, obtainspec.samples);

	                                        
	if (wantspec.freq != obtainspec.freq ||
		wantspec.format != obtainspec.format ||
		wantspec.channels != obtainspec.channels)
	{
		SDL_CloseAudioDevice(audio_device);

		                                                 
		if (suggested != NULL)
		{
			suggested->speed = obtainspec.freq;
			                                                                                
			suggested->width = ((obtainspec.format == AUDIO_U8) ? 1 : 2);
			suggested->channels = obtainspec.channels;
		}

		return false;
	}

	snd_threaded = true;

	snd_renderbuffer = Snd_CreateRingBuffer(requested, 0, NULL);
	if (snd_channellayout.integer == SND_CHANNELLAYOUT_AUTO)
		Cvar_SetValueQuick (&snd_channellayout, SND_CHANNELLAYOUT_STANDARD);

	sdlaudiotime = 0;
	SDL_PauseAudioDevice(audio_device, 0);

	return true;
}


  
                    
               

                                                                           
                    
  
void SndSys_Shutdown(void)
{
	if (audio_device > 0) {
		SDL_CloseAudioDevice(audio_device);
		audio_device = 0;
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
	                                                           
}


  
                    
                   

                                                                    
                    
  
unsigned int SndSys_GetSoundTime (void)
{
	return sdlaudiotime;
}


  
                    
                       

                                            
                    
  
qboolean SndSys_LockRenderBuffer (void)
{
	SDL_LockAudioDevice(audio_device);
	return true;
}


  
                    
                         

                                                
                    
  
void SndSys_UnlockRenderBuffer (void)
{
	SDL_UnlockAudioDevice(audio_device);
}

  
                    
                    

                                                                  
                    
  
void SndSys_SendKeyEvents(void)
{
	                
}
