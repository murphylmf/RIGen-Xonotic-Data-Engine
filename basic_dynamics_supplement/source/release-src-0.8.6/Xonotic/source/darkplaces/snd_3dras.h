     

#ifndef SND_3DRAS_H
#define SND_3DRAS_H

#include "sound.h"

#define DEFAULT_SOUND_PACKET_VOLUME 255
#define DEFAULT_SOUND_PACKET_ATTENUATION 1.0

#define CHANNELFLAG_NONE		0
#define CHANNELFLAG_FORCELOOP	(1 << 0)                                                 
#define CHANNELFLAG_LOCALSOUND	(1 << 1)                                                  
#define CHANNELFLAG_PAUSED		(1 << 2)
#define CHANNELFLAG_FULLVOLUME	(1 << 3)                                        

#define SFXFLAG_NONE		0
                                                                                       
#define SFXFLAG_SERVERSOUND	(1 << 1)                                               
                                                                                         
#define SFXFLAG_PERMANENTLOCK	(1 << 3)                                                    

typedef struct channel_s{
	struct channel_s* next;
	void* rasptr;                                                                                      
	int   entnum;                                       
	int   entchannel;
	unsigned int   id;
} channel_t;

typedef struct entnum_s{
	struct entnum_s *next;
	int       entnum;
	vec3_t    lastloc;                                                                                                                   
	void     *rasptr;                                                                                       
} entnum_t;

struct sfx_s{
	struct sfx_s *next;
	char  name[MAX_QPATH];
	void* rasptr;                                                   
	
	int locks;
	unsigned int flags;       	                       
	                                                                                   
	                                                
};

#endif
