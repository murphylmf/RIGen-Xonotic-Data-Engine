  
                                          

                                                              
                                                            
                                                               
                                                       

                                                                
                                                               
                                                     

                                                     

                                                                  
                                           

                                
                             
                             

  


#include "quakedef.h"
#include "snd_main.h"
#include "snd_wav.h"


typedef struct wavinfo_s
{
	int		rate;
	int		width;
	int		channels;
	int		loopstart;
	int		samples;
	int		dataofs;		                                               
} wavinfo_t;


static unsigned char *data_p;
static unsigned char *iff_end;
static unsigned char *last_chunk;
static unsigned char *iff_data;
static int iff_chunk_len;


static short GetLittleShort(void)
{
	short val;

	val = BuffLittleShort (data_p);
	data_p += 2;

	return val;
}

static int GetLittleLong(void)
{
	int val = 0;

	val = BuffLittleLong (data_p);
	data_p += 4;

	return val;
}

static void FindNextChunk(const char *name)
{
	while (1)
	{
		data_p=last_chunk;

		if (data_p >= iff_end)
		{	                        
			data_p = NULL;
			return;
		}

		data_p += 4;
		iff_chunk_len = GetLittleLong();
		if (iff_chunk_len < 0)
		{
			data_p = NULL;
			return;
		}
		if (data_p + iff_chunk_len > iff_end)
		{
			                   
			data_p = NULL;
			return;
		}
		data_p -= 8;
		last_chunk = data_p + 8 + ( (iff_chunk_len + 1) & ~1 );
		if (!strncmp((const char *)data_p, name, 4))
			return;
	}
}

static void FindChunk(const char *name)
{
	last_chunk = iff_data;
	FindNextChunk (name);
}


  
                            
 
             

            
                 
   
  
                          
              
                                  
                                                                        
                                     
                            
 
  


  
            
          
            
  
static wavinfo_t GetWavinfo (char *name, unsigned char *wav, int wavlength)
{
	wavinfo_t info;
	int i;
	int format;
	int samples;

	memset (&info, 0, sizeof(info));

	if (!wav)
		return info;

	iff_data = wav;
	iff_end = wav + wavlength;

	                    
	FindChunk("RIFF");
	if (!(data_p && !strncmp((const char *)data_p+8, "WAVE", 4)))
	{
		Con_Print("Missing RIFF/WAVE chunks\n");
		return info;
	}

	                   
	iff_data = data_p + 12;
	                

	FindChunk("fmt ");
	if (!data_p)
	{
		Con_Print("Missing fmt chunk\n");
		return info;
	}
	data_p += 8;
	format = GetLittleShort();
	if (format != 1)
	{
		Con_Print("Microsoft PCM format only\n");
		return info;
	}

	info.channels = GetLittleShort();
	info.rate = GetLittleLong();
	data_p += 4+2;
	info.width = GetLittleShort() / 8;

	                
	FindChunk("cue ");
	if (data_p)
	{
		data_p += 32;
		info.loopstart = GetLittleLong();

		                                                                  
		FindNextChunk ("LIST");
		if (data_p)
		{
			if (!strncmp ((const char *)data_p + 28, "mark", 4))
			{	                                                            
				data_p += 24;
				i = GetLittleLong ();	                  
				info.samples = info.loopstart + i;
			}
		}
	}
	else
		info.loopstart = -1;

	                  
	FindChunk("data");
	if (!data_p)
	{
		Con_Print("Missing data chunk\n");
		return info;
	}

	data_p += 4;
	samples = GetLittleLong () / info.width / info.channels;

	if (info.samples)
	{
		if (samples < info.samples)
		{
			Con_Printf ("Sound %s has a bad loop length\n", name);
			info.samples = samples;
		}
	}
	else
		info.samples = samples;

	info.dataofs = data_p - wav;

	return info;
}


  
                    
                   
                    
  
static void WAV_GetSamplesFloat(channel_t *ch, sfx_t *sfx, int firstsampleframe, int numsampleframes, float *outsamplesfloat)
{
	int i, len = numsampleframes * sfx->format.channels;
	if (sfx->format.width == 2)
	{
		const short *bufs = (const short *)sfx->fetcher_data + firstsampleframe * sfx->format.channels;
		for (i = 0;i < len;i++)
			outsamplesfloat[i] = bufs[i] * (1.0f / 32768.0f);
	}
	else
	{
		const signed char *bufb = (const signed char *)sfx->fetcher_data + firstsampleframe * sfx->format.channels;
		for (i = 0;i < len;i++)
			outsamplesfloat[i] = bufb[i] * (1.0f / 128.0f);
	}
}

  
                    
           
                    
  
static void WAV_FreeSfx(sfx_t *sfx)
{
	                             
	Mem_Free(sfx->fetcher_data);
}

const snd_fetcher_t wav_fetcher = { WAV_GetSamplesFloat, NULL, WAV_FreeSfx };


  
              
             
              
  
qboolean S_LoadWavFile (const char *filename, sfx_t *sfx)
{
	fs_offset_t filesize;
	unsigned char *data;
	wavinfo_t info;
	int i, len;
	const unsigned char *inb;
	unsigned char *outb;

	                  
	if (sfx->fetcher != NULL)
		return true;

	                
	data = FS_LoadFile(filename, snd_mempool, false, &filesize);
	if (!data)
		return false;

	                                              
	if (memcmp (data, "RIFF", 4) || memcmp (data + 8, "WAVE", 4))
	{
		Mem_Free(data);
		return false;
	}

	if (developer_loading.integer >= 2)
		Con_Printf ("Loading WAV file \"%s\"\n", filename);

	info = GetWavinfo (sfx->name, data, (int)filesize);
	if (info.channels < 1 || info.channels > 2)                                                   
	{
		Con_Printf("%s has an unsupported number of channels (%i)\n",sfx->name, info.channels);
		Mem_Free(data);
		return false;
	}
	                         
	                                                     

	sfx->format.speed = info.rate;
	sfx->format.width = info.width;
	sfx->format.channels = info.channels;
	sfx->fetcher = &wav_fetcher;
	sfx->fetcher_data = Mem_Alloc(snd_mempool, info.samples * sfx->format.width * sfx->format.channels);
	sfx->total_length = info.samples;
	sfx->memsize += filesize;
	len = info.samples * sfx->format.channels * sfx->format.width;
	inb = data + info.dataofs;
	outb = (unsigned char *)sfx->fetcher_data;
	if (info.width == 2)
	{
		if (mem_bigendian)
		{
			                                                                           
			for (i = 0;i < len;i += 2)
			{
				outb[i] = inb[i+1];
				outb[i+1] = inb[i];
			}
		}
		else
		{
			                               
			memcpy(outb, inb, len);
		}
	}
	else
	{
		                                                                      
		for (i = 0;i < len;i++)
			outb[i] = inb[i] - 0x80;
	}

	if (info.loopstart < 0)
		sfx->loopstart = sfx->total_length;
	else
		sfx->loopstart = info.loopstart;
	sfx->loopstart = min(sfx->loopstart, sfx->total_length);
	sfx->flags &= ~SFXFLAG_STREAMED;

	return true;
}
