
#ifndef MODEL_PSK_H
#define MODEL_PSK_H

typedef struct pskchunk_s
{
	                              
	        
	                                            
	                                        
	                                        
	                                        
	                                        
	                                             
	                                                
	        
	                                            
	                                              
	                                             
	                                            
	char id[20];
	                          
	                      
	int version;
	int recordsize;
	int numrecords;
}
pskchunk_t;

typedef struct pskpnts_s
{
	float origin[3];
}
pskpnts_t;

typedef struct pskvtxw_s
{
	unsigned short pntsindex;                             
	unsigned char unknown1[2];                       
	float texcoord[2];
	unsigned char mattindex;                             
	unsigned char unknown2;             
	unsigned char unknown3[2];                       
}
pskvtxw_t;

typedef struct pskface_s
{
	unsigned short vtxwindex[3];            
	unsigned char mattindex;                             
	unsigned char unknown;                       
	unsigned int group;                                                     
}
pskface_t;

typedef struct pskmatt_s
{
	char name[64];
	int unknown[6];                        
}
pskmatt_t;

typedef struct pskpose_s
{
	float quat[4];
	float origin[3];
	float unknown;                                          
	float size[3];
}
pskpose_t;

typedef struct pskboneinfo_s
{
	char name[64];
	int unknown1;
	int numchildren;
	int parent;                          
	pskpose_t basepose;
}
pskboneinfo_t;

typedef struct pskrawweights_s
{
	float weight;
	int pntsindex;
	int boneindex;
}
pskrawweights_t;

typedef struct pskaniminfo_s
{
	char name[64];
	char group[64];
	int numbones;
	int unknown1;
	int unknown2;
	int unknown3;
	float unknown4;
	float playtime;                     
	float fps;                     
	int unknown5;
	int firstframe;
	int numframes;
	                                                       
}
pskaniminfo_t;

typedef struct pskanimkeys_s
{
	float origin[3];
	float quat[4];
	float frametime;
}
pskanimkeys_t;

#endif

