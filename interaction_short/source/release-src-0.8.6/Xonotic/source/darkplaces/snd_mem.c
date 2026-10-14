  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  


#include "quakedef.h"

#include "snd_main.h"
#include "snd_ogg.h"
#include "snd_wav.h"


  
                    
                    

                                                                                             
                                                        
                    
  
snd_ringbuffer_t *Snd_CreateRingBuffer (const snd_format_t* format, unsigned int sampleframes, void* buffer)
{
	snd_ringbuffer_t *ringbuffer;

	                                                            
	if (sampleframes == 0 && buffer != NULL)
		return NULL;

	ringbuffer = (snd_ringbuffer_t*)Mem_Alloc(snd_mempool, sizeof (*ringbuffer));
	memset(ringbuffer, 0, sizeof(*ringbuffer));
	memcpy(&ringbuffer->format, format, sizeof(ringbuffer->format));

	                                    
	if (buffer == NULL)
	{
		unsigned int maxframes;
		size_t memsize;

		if (sampleframes == 0)
			maxframes = (format->speed + 1) / 2;                                                                       
		else
			maxframes = sampleframes;

		memsize = maxframes * format->width * format->channels;
		ringbuffer->ring = (unsigned char *) Mem_Alloc(snd_mempool, memsize);
		ringbuffer->maxframes = maxframes;
	}
	else
	{
		ringbuffer->ring = (unsigned char *) buffer;
		ringbuffer->maxframes = sampleframes;
	}

	return ringbuffer;
}


  
                    
                   
                    
  
snd_buffer_t *Snd_CreateSndBuffer (const unsigned char *samples, unsigned int sampleframes, const snd_format_t* in_format, unsigned int sb_speed)
{
	size_t newsampleframes, memsize;
	snd_buffer_t* sb;

	newsampleframes = (size_t) ceil((double)sampleframes * (double)sb_speed / (double)in_format->speed);

	memsize = newsampleframes * in_format->channels * in_format->width;
	memsize += sizeof (*sb) - sizeof (sb->samples);

	sb = (snd_buffer_t*)Mem_Alloc (snd_mempool, memsize);
	sb->format.channels = in_format->channels;
	sb->format.width = in_format->width;
	sb->format.speed = sb_speed;
	sb->maxframes = (unsigned int)newsampleframes;
	sb->nbframes = 0;

	if (!Snd_AppendToSndBuffer (sb, samples, sampleframes, in_format))
	{
		Mem_Free (sb);
		return NULL;
	}

	return sb;
}


  
                    
                     
                    
  
qboolean Snd_AppendToSndBuffer (snd_buffer_t* sb, const unsigned char *samples, unsigned int sampleframes, const snd_format_t* format)
{
	size_t srclength, outcount;
	unsigned char *out_data;

	                                                                      
	                                                              

	                                  
	if (sb->format.channels != format->channels || sb->format.width != format->width)
	{
		Con_Print("AppendToSndBuffer: incompatible sound formats!\n");
		return false;
	}

	outcount = (size_t) ((double)sampleframes * (double)sb->format.speed / (double)format->speed);

	                                   
	if (outcount > sb->maxframes - sb->nbframes)
	{
		Con_Print("AppendToSndBuffer: sound buffer too short!\n");
		return false;
	}

	out_data = &sb->samples[sb->nbframes * sb->format.width * sb->format.channels];
	srclength = sampleframes * format->channels;

	                                 
	if (format->speed == sb->format.speed)
	{
		if (format->width == 1)
		{
			size_t i;

			for (i = 0; i < srclength; i++)
				((signed char*)out_data)[i] = samples[i] - 128;
		}
		else                            
			memcpy (out_data, samples, srclength * format->width);
	}

	                                                                   
	                                                        
	                                                                     
#	define FRACTIONAL_BITS 14
#	define FRACTIONAL_MASK ((1 << FRACTIONAL_BITS) - 1)
#	define INTEGER_BITS (sizeof(samplefrac)*8 - FRACTIONAL_BITS)
	else
	{
		const unsigned int fracstep = (unsigned int)((double)format->speed / sb->format.speed * (1 << FRACTIONAL_BITS));
		size_t remain_in = srclength, total_out = 0;
		unsigned int samplefrac;
		const unsigned char *in_ptr = samples;
		unsigned char *out_ptr = out_data;

		                                                    
		if (format->speed * format->channels > (1 << INTEGER_BITS))
		{
			Con_Printf ("ResampleSfx: sound quality too high for resampling (%uHz, %u channel(s))\n",
					   format->speed, format->channels);
			return 0;
		}

		                                                               
		                                                                     
		                                              
		while (total_out < outcount)
		{
			size_t tmpcount, interpolation_limit, i, j;
			unsigned int srcsample;

			samplefrac = 0;

			                                                      
			if (outcount - total_out > sb->format.speed)
			{
				tmpcount = sb->format.speed;
				interpolation_limit = tmpcount;                                    
			}
			else
			{
				tmpcount = outcount - total_out;
				interpolation_limit = (int)ceil((double)(((remain_in / format->channels) - 1) << FRACTIONAL_BITS) / fracstep);
				if (interpolation_limit > tmpcount)
					interpolation_limit = tmpcount;
			}

			                 
			if (format->width == 2)
			{
				const short* in_ptr_short;

				                    
				for (i = 0; i < interpolation_limit; i++)
				{
					srcsample = (samplefrac >> FRACTIONAL_BITS) * format->channels;
					in_ptr_short = &((const short*)in_ptr)[srcsample];

					for (j = 0; j < format->channels; j++)
					{
						int a, b;

						a = *in_ptr_short;
						b = *(in_ptr_short + format->channels);
						*((short*)out_ptr) = (((b - a) * (samplefrac & FRACTIONAL_MASK)) >> FRACTIONAL_BITS) + a;

						in_ptr_short++;
						out_ptr += sizeof (short);
					}

					samplefrac += fracstep;
				}

				                        
				for (             ; i < tmpcount; i++)
				{
					srcsample = (samplefrac >> FRACTIONAL_BITS) * format->channels;
					in_ptr_short = &((const short*)in_ptr)[srcsample];

					for (j = 0; j < format->channels; j++)
					{
						*((short*)out_ptr) = *in_ptr_short;

						in_ptr_short++;
						out_ptr += sizeof (short);
					}

					samplefrac += fracstep;
				}
			}
			                
			else                            
			{
				const unsigned char* in_ptr_byte;

				                               
				for (i = 0; i < interpolation_limit; i++)
				{
					srcsample = (samplefrac >> FRACTIONAL_BITS) * format->channels;
					in_ptr_byte = &((const unsigned char*)in_ptr)[srcsample];

					for (j = 0; j < format->channels; j++)
					{
						int a, b;

						a = *in_ptr_byte - 128;
						b = *(in_ptr_byte + format->channels) - 128;
						*((signed char*)out_ptr) = (((b - a) * (samplefrac & FRACTIONAL_MASK)) >> FRACTIONAL_BITS) + a;

						in_ptr_byte++;
						out_ptr += sizeof (signed char);
					}

					samplefrac += fracstep;
				}

				                        
				for (             ; i < tmpcount; i++)
				{
					srcsample = (samplefrac >> FRACTIONAL_BITS) * format->channels;
					in_ptr_byte = &((const unsigned char*)in_ptr)[srcsample];

					for (j = 0; j < format->channels; j++)
					{
						*((signed char*)out_ptr) = *in_ptr_byte - 128;

						in_ptr_byte++;
						out_ptr += sizeof (signed char);
					}

					samplefrac += fracstep;
				}
			}

			                                              
			remain_in -= format->speed * format->channels;
			in_ptr += format->speed * format->channels * format->width;
			total_out += tmpcount;
		}
	}

	sb->nbframes += (unsigned int)outcount;
	return true;
}


                                                                               

  
              
           
              
  
qboolean S_LoadSound (sfx_t *sfx, qboolean complain)
{
	char namebuffer[MAX_QPATH + 16];
	size_t len;

	                        
	if (sfx->fetcher != NULL)
		return true;

	                                                             
	                                                          
	if (sfx->flags & SFXFLAG_FILEMISSING)
		return false;

	            
	if (snd_renderbuffer == NULL)
		return false;

	                                                                                            
	sfx->volume_peak = 0.0;

	if (developer_loading.integer)
		Con_Printf("loading sound %s\n", sfx->name);

	SCR_PushLoadingScreen(true, sfx->name, 1);

	                                                                             
	if (strncasecmp(sfx->name, "sound/", 6))
	{
		dpsnprintf (namebuffer, sizeof(namebuffer), "sound/%s", sfx->name);
		len = strlen(namebuffer);
		if (len >= 4 && !strcasecmp (namebuffer + len - 4, ".wav"))
		{
			if (S_LoadWavFile (namebuffer, sfx))
				goto loaded;
			memcpy (namebuffer + len - 3, "ogg", 4);
		}
		if (len >= 4 && !strcasecmp (namebuffer + len - 4, ".ogg"))
		{
			if (OGG_LoadVorbisFile (namebuffer, sfx))
				goto loaded;
		}
	}

	                                                              
	dpsnprintf (namebuffer, sizeof(namebuffer), "%s", sfx->name);
	len = strlen(namebuffer);
	                                               
	                                      
	                                      
	if (len >= 4 && !strcasecmp (namebuffer + len - 4, ".wav"))
	{
		if (S_LoadWavFile (namebuffer, sfx))
			goto loaded;
		memcpy (namebuffer + len - 3, "ogg", 4);
	}
	if (len >= 4 && !strcasecmp (namebuffer + len - 4, ".ogg"))
	{
		if (OGG_LoadVorbisFile (namebuffer, sfx))
			goto loaded;
	}

	                        
	sfx->flags |= SFXFLAG_FILEMISSING;
	if (complain)
		Con_DPrintf("failed to load sound \"%s\"\n", sfx->name);

	SCR_PopLoadingScreen(false);
	return false;

loaded:
	SCR_PopLoadingScreen(false);
	return true;
}
