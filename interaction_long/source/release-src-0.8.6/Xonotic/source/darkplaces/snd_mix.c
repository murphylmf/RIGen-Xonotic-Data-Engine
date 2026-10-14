  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

#include "quakedef.h"
#include "snd_main.h"

extern cvar_t snd_softclip;

static portable_sampleframe_t paintbuffer[PAINTBUFFER_SIZE];
static portable_sampleframe_t paintbuffer_unswapped[PAINTBUFFER_SIZE];

extern speakerlayout_t snd_speakerlayout;                              

#ifdef CONFIG_VIDEO_CAPTURE
static void S_CaptureAVISound(const portable_sampleframe_t *paintbuffer, size_t length)
{
	size_t i;
	unsigned int j;

	if (!cls.capturevideo.active)
		return;

	                                                                   
	for(j = 0; j < snd_speakerlayout.channels; ++j)
	{
		unsigned int j0 = snd_speakerlayout.listeners[j].channel_unswapped;
		for(i = 0; i < length; ++i)
			paintbuffer_unswapped[i].sample[j0] = paintbuffer[i].sample[j];
	}

	SCR_CaptureVideo_SoundFrame(paintbuffer_unswapped, length);
}
#endif

extern cvar_t snd_softclip;

static void S_SoftClipPaintBuffer(portable_sampleframe_t *painted_ptr, int nbframes, int width, int nchannels)
{
	int i;

	if((snd_softclip.integer == 1 && width <= 2) || snd_softclip.integer > 1)
	{
		portable_sampleframe_t *p = painted_ptr;

#if 0
                                                            
                          
#define SOFTCLIP(x) (x) = sin(bound(-M_PI/2, (x), M_PI/2)) * 0.25
#endif

		                                                           
		static float maxvol = 0;
		maxvol = max(1.0f, maxvol * (1.0f - nbframes / (0.4f * snd_renderbuffer->format.speed)));
#define SOFTCLIP(x) if(fabs(x)>maxvol) maxvol=fabs(x); (x) /= maxvol;

		if (nchannels == 8)                 
		{
			for (i = 0;i < nbframes;i++, p++)
			{
				SOFTCLIP(p->sample[0]);
				SOFTCLIP(p->sample[1]);
				SOFTCLIP(p->sample[2]);
				SOFTCLIP(p->sample[3]);
				SOFTCLIP(p->sample[4]);
				SOFTCLIP(p->sample[5]);
				SOFTCLIP(p->sample[6]);
				SOFTCLIP(p->sample[7]);
			}
		}
		else if (nchannels == 6)                 
		{
			for (i = 0; i < nbframes; i++, p++)
			{
				SOFTCLIP(p->sample[0]);
				SOFTCLIP(p->sample[1]);
				SOFTCLIP(p->sample[2]);
				SOFTCLIP(p->sample[3]);
				SOFTCLIP(p->sample[4]);
				SOFTCLIP(p->sample[5]);
			}
		}
		else if (nchannels == 4)                 
		{
			for (i = 0; i < nbframes; i++, p++)
			{
				SOFTCLIP(p->sample[0]);
				SOFTCLIP(p->sample[1]);
				SOFTCLIP(p->sample[2]);
				SOFTCLIP(p->sample[3]);
			}
		}
		else if (nchannels == 2)               
		{
			for (i = 0; i < nbframes; i++, p++)
			{
				SOFTCLIP(p->sample[0]);
				SOFTCLIP(p->sample[1]);
			}
		}
		else if (nchannels == 1)             
		{
			for (i = 0; i < nbframes; i++, p++)
			{
				SOFTCLIP(p->sample[0]);
			}
		}
#undef SOFTCLIP
	}
}

static void S_ConvertPaintBuffer(portable_sampleframe_t *painted_ptr, void *rb_ptr, int nbframes, int width, int nchannels)
{
	int i, val;

	                                           
	                                       
	if (width == 2)          
	{
		short *snd_out = (short*)rb_ptr;
		if (nchannels == 8)                 
		{
			for (i = 0;i < nbframes;i++, painted_ptr++)
			{
				val = (int)(painted_ptr->sample[0] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
				val = (int)(painted_ptr->sample[1] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
				val = (int)(painted_ptr->sample[2] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
				val = (int)(painted_ptr->sample[3] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
				val = (int)(painted_ptr->sample[4] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
				val = (int)(painted_ptr->sample[5] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
				val = (int)(painted_ptr->sample[6] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
				val = (int)(painted_ptr->sample[7] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
			}
		}
		else if (nchannels == 6)                 
		{
			for (i = 0; i < nbframes; i++, painted_ptr++)
			{
				val = (int)(painted_ptr->sample[0] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
				val = (int)(painted_ptr->sample[1] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
				val = (int)(painted_ptr->sample[2] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
				val = (int)(painted_ptr->sample[3] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
				val = (int)(painted_ptr->sample[4] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
				val = (int)(painted_ptr->sample[5] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
			}
		}
		else if (nchannels == 4)                 
		{
			for (i = 0; i < nbframes; i++, painted_ptr++)
			{
				val = (int)(painted_ptr->sample[0] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
				val = (int)(painted_ptr->sample[1] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
				val = (int)(painted_ptr->sample[2] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
				val = (int)(painted_ptr->sample[3] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
			}
		}
		else if (nchannels == 2)               
		{
			for (i = 0; i < nbframes; i++, painted_ptr++)
			{
				val = (int)(painted_ptr->sample[0] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
				val = (int)(painted_ptr->sample[1] * 32768.0f);*snd_out++ = bound(-32768, val, 32767);
			}
		}
		else if (nchannels == 1)             
		{
			for (i = 0; i < nbframes; i++, painted_ptr++)
			{
				val = (int)((painted_ptr->sample[0] + painted_ptr->sample[1]) * 16384.0f);*snd_out++ = bound(-32768, val, 32767);
			}
		}

		                                  
		if (cls.timedemo)
			memset(rb_ptr, 0, nbframes * nchannels * width);
	}
	else         
	{
		unsigned char *snd_out = (unsigned char*)rb_ptr;
		if (nchannels == 8)                 
		{
			for (i = 0; i < nbframes; i++, painted_ptr++)
			{
				val = (int)(painted_ptr->sample[0] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
				val = (int)(painted_ptr->sample[1] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
				val = (int)(painted_ptr->sample[2] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
				val = (int)(painted_ptr->sample[3] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
				val = (int)(painted_ptr->sample[4] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
				val = (int)(painted_ptr->sample[5] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
				val = (int)(painted_ptr->sample[6] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
				val = (int)(painted_ptr->sample[7] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
			}
		}
		else if (nchannels == 6)                 
		{
			for (i = 0; i < nbframes; i++, painted_ptr++)
			{
				val = (int)(painted_ptr->sample[0] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
				val = (int)(painted_ptr->sample[1] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
				val = (int)(painted_ptr->sample[2] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
				val = (int)(painted_ptr->sample[3] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
				val = (int)(painted_ptr->sample[4] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
				val = (int)(painted_ptr->sample[5] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
			}
		}
		else if (nchannels == 4)                 
		{
			for (i = 0; i < nbframes; i++, painted_ptr++)
			{
				val = (int)(painted_ptr->sample[0] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
				val = (int)(painted_ptr->sample[1] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
				val = (int)(painted_ptr->sample[2] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
				val = (int)(painted_ptr->sample[3] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
			}
		}
		else if (nchannels == 2)               
		{
			for (i = 0; i < nbframes; i++, painted_ptr++)
			{
				val = (int)(painted_ptr->sample[0] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
				val = (int)(painted_ptr->sample[1] * 128.0f) + 128; *snd_out++ = bound(0, val, 255);
			}
		}
		else if (nchannels == 1)             
		{
			for (i = 0;i < nbframes;i++, painted_ptr++)
			{
				val = (int)((painted_ptr->sample[0] + painted_ptr->sample[1]) * 64.0f) + 128; *snd_out++ = bound(0, val, 255);
			}
		}

		                                  
		if (cls.timedemo)
			memset(rb_ptr, 128, nbframes * nchannels);
	}
}


  
                                                                               

              

                                                                               
  

void S_MixToBuffer(void *stream, unsigned int bufferframes)
{
	int channelindex;
	channel_t *ch;
	int totalmixframes;
	unsigned char *outbytes = (unsigned char *) stream;
	sfx_t *sfx;
	portable_sampleframe_t *paint;
	int wantframes;
	int i;
	int count;
	int fetched;
	int fetch;
	int istartframe;
	int iendframe;
	int ilengthframes;
	int totallength;
	int loopstart;
	int indexfrac;
	int indexfracstep;
#define S_FETCHBUFFERSIZE 4096
	float fetchsampleframes[S_FETCHBUFFERSIZE*2];
	const float *fetchsampleframe;
	float vol[SND_LISTENERS];
	float lerp[2];
	float sample[3];
	double posd;
	double speedd;
	float maxvol;
	qboolean looping;
	qboolean silent;

	                                                           
	while (bufferframes)
	{
		                                        
		totalmixframes = min(bufferframes, PAINTBUFFER_SIZE);

		                         
		memset(paintbuffer, 0, totalmixframes * sizeof(paintbuffer[0]));

		                         
		                                                                    
		ch = channels;                                                                                                 
		for (channelindex = 0;channelindex < (int)total_channels;channelindex++, ch++)
		{
			sfx = ch->sfx;
			if (sfx == NULL)
				continue;
			if (!S_LoadSound (sfx, true))
				continue;
			if (ch->flags & CHANNELFLAG_PAUSED)
				continue;
			if (!sfx->total_length)
				continue;

			                                                                         
			                                                                       
			                                                           
			posd = ch->position;
			speedd = ch->mixspeed * sfx->format.speed / snd_renderbuffer->format.speed;
			for (i = 0;i < SND_LISTENERS;i++)
				vol[i] = ch->volume[i];

			                                                                                                                                   
			maxvol = 0;
			for (i = 0;i < SND_LISTENERS;i++)
				if(vol[i] > maxvol)
					maxvol = vol[i];
			switch(snd_renderbuffer->format.width)
			{
				case 1:        
					silent = maxvol < (1.0f / (256.0f));
					                               
					break;
				case 2:         
					silent = maxvol < (1.0f / (65536.0f));
					                               
					break;
				default:                  
					silent = maxvol < 1.0e-13f;
					                                       
					                                  
					                    
					                                 
					                                  
					                                   
					                              
					break;
			}

			                                                            
			if (ch->prologic_invert == -1)
				vol[1] *= -1.0f;

			                                         
			totallength = sfx->total_length;
			loopstart = (int)sfx->loopstart < totallength ? (int)sfx->loopstart : ((ch->flags & CHANNELFLAG_FORCELOOP) ? 0 : totallength);
			looping = loopstart < totallength;

			                                                    
			paint = paintbuffer;
			istartframe = 0;
			for (wantframes = totalmixframes;wantframes > 0;posd += count * speedd, wantframes -= count)
			{
				                                   
				if (posd < 0)
				{
					                                                          
					count = (int)floor(-posd / speedd) + 1;
					count = bound(1, count, wantframes);
					                                           
					continue;
				}

				                                                      
				count = wantframes;
				for (;;)
				{
					istartframe = (int)floor(posd);
					iendframe = (int)floor(posd + (count-1) * speedd);
					ilengthframes = count > 1 ? (iendframe - istartframe + 2) : 2;
					if (ilengthframes <= S_FETCHBUFFERSIZE)
						break;
					                                    
					count -= count >> 2;
				}

				                                     
				                                                              
				                                                   
				if (!silent)
					memset(fetchsampleframes, 0, ilengthframes*sfx->format.channels*sizeof(fetchsampleframes[0]));

				                                  
				fetched = 0;
				for (;;)
				{
					fetch = min(ilengthframes - fetched, totallength - istartframe);
					if (fetch > 0)
					{
						if (!silent)
							sfx->fetcher->getsamplesfloat(ch, sfx, istartframe, fetch, fetchsampleframes + fetched*sfx->format.channels);
						istartframe += fetch;
						fetched += fetch;
					}
					if (istartframe == totallength && looping && fetched < ilengthframes)
					{
						                           
						posd += loopstart - totallength;
						istartframe = loopstart;
					}
					else
					{
						break;
					}
				}

				                                                                                                                       
				fetchsampleframe = fetchsampleframes;
				indexfrac = (int)floor((posd - floor(posd)) * 65536.0);
				indexfracstep = (int)floor(speedd * 65536.0);
				if (!silent)
				{
					if (sfx->format.channels == 2)
					{
						                  
#if SND_LISTENERS != 8
#error the following code only supports up to 8 channels, update it
#endif
						if (snd_speakerlayout.channels > 2)
						{
							                  
							for (i = 0;i < count;i++, paint++)
							{
								lerp[1] = indexfrac * (1.0f / 65536.0f);
								lerp[0] = 1.0f - lerp[1];
								sample[0] = fetchsampleframe[0] * lerp[0] + fetchsampleframe[2] * lerp[1];
								sample[1] = fetchsampleframe[1] * lerp[0] + fetchsampleframe[3] * lerp[1];
								sample[2] = (sample[0] + sample[1]) * 0.5f;
								paint->sample[0] += sample[0] * vol[0];
								paint->sample[1] += sample[1] * vol[1];
								paint->sample[2] += sample[0] * vol[2];
								paint->sample[3] += sample[1] * vol[3];
								paint->sample[4] += sample[2] * vol[4];
								paint->sample[5] += sample[2] * vol[5];
								paint->sample[6] += sample[0] * vol[6];
								paint->sample[7] += sample[1] * vol[7];
								indexfrac += indexfracstep;
								fetchsampleframe += 2 * (indexfrac >> 16);
								indexfrac &= 0xFFFF;
							}
						}
						else
						{
							                
							for (i = 0;i < count;i++, paint++)
							{
								lerp[1] = indexfrac * (1.0f / 65536.0f);
								lerp[0] = 1.0f - lerp[1];
								sample[0] = fetchsampleframe[0] * lerp[0] + fetchsampleframe[2] * lerp[1];
								sample[1] = fetchsampleframe[1] * lerp[0] + fetchsampleframe[3] * lerp[1];
								paint->sample[0] += sample[0] * vol[0];
								paint->sample[1] += sample[1] * vol[1];
								indexfrac += indexfracstep;
								fetchsampleframe += 2 * (indexfrac >> 16);
								indexfrac &= 0xFFFF;
							}
						}
					}
					else if (sfx->format.channels == 1)
					{
						                       
#if SND_LISTENERS != 8
#error the following code only supports up to 8 channels, update it
#endif
						if (snd_speakerlayout.channels > 2)
						{
							                  
							for (i = 0;i < count;i++, paint++)
							{
								lerp[1] = indexfrac * (1.0f / 65536.0f);
								lerp[0] = 1.0f - lerp[1];
								sample[0] = fetchsampleframe[0] * lerp[0] + fetchsampleframe[1] * lerp[1];
								paint->sample[0] += sample[0] * vol[0];
								paint->sample[1] += sample[0] * vol[1];
								paint->sample[2] += sample[0] * vol[2];
								paint->sample[3] += sample[0] * vol[3];
								paint->sample[4] += sample[0] * vol[4];
								paint->sample[5] += sample[0] * vol[5];
								paint->sample[6] += sample[0] * vol[6];
								paint->sample[7] += sample[0] * vol[7];
								indexfrac += indexfracstep;
								fetchsampleframe += (indexfrac >> 16);
								indexfrac &= 0xFFFF;
							}
						}
						else
						{
							                
							for (i = 0;i < count;i++, paint++)
							{
								lerp[1] = indexfrac * (1.0f / 65536.0f);
								lerp[0] = 1.0f - lerp[1];
								sample[0] = fetchsampleframe[0] * lerp[0] + fetchsampleframe[1] * lerp[1];
								paint->sample[0] += sample[0] * vol[0];
								paint->sample[1] += sample[0] * vol[1];
								indexfrac += indexfracstep;
								fetchsampleframe += (indexfrac >> 16);
								indexfrac &= 0xFFFF;
							}
						}
					}
				}
			}
			ch->position = posd;
			if (!looping && istartframe == totallength)
				S_StopChannel(ch - channels, false, false);
		}

		S_SoftClipPaintBuffer(paintbuffer, totalmixframes, snd_renderbuffer->format.width, snd_renderbuffer->format.channels);

#ifdef CONFIG_VIDEO_CAPTURE
		if (!snd_usethreadedmixing)
			S_CaptureAVISound(paintbuffer, totalmixframes);
#endif

		S_ConvertPaintBuffer(paintbuffer, outbytes, totalmixframes, snd_renderbuffer->format.width, snd_renderbuffer->format.channels);

		                             
		outbytes += totalmixframes * snd_renderbuffer->format.width * snd_renderbuffer->format.channels;
		bufferframes -= totalmixframes;
	}
}
