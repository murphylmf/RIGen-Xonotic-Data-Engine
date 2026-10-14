
#ifndef MODEL_ZYMOTIC_H
#define MODEL_ZYMOTIC_H

typedef struct zymlump_s
{
	int start;
	int length;
} zymlump_t;

typedef struct zymtype1header_s
{
	char id[12];                                             
	int type;                                                               
	int filesize;                             
	float mins[3], maxs[3], radius;                     
	int numverts;
	int numtris;
	int numshaders;
	int numbones;                                                           
	int numscenes;                                 

                       
	                                        
	zymlump_t lump_scenes;                                                                                                   
	zymlump_t lump_poses;                                                        
	zymlump_t lump_bones;                             
	zymlump_t lump_vertbonecounts;                                                                                                                           
	zymlump_t lump_verts;                                                       
	zymlump_t lump_texcoords;                                    
	zymlump_t lump_render;                                                                                                                                                                                          
	zymlump_t lump_shaders;                                                                  
	zymlump_t lump_trizone;                                                     
}
zymtype1header_t;

#define ZYMBONEFLAG_SHARED 1

typedef struct zymbone_s
{
	char name[32];
	int flags;
	int parent;                      
}
zymbone_t;

                                                                               
#define ZYMSCENEFLAG_NOLOOP 1

typedef struct zymscene_s
{
	char name[32];
	float mins[3], maxs[3], radius;                
	float framerate;                                                                   
	int flags;
	int start, length;                  
}
zymscene_t;

typedef struct zymvertex_s
{
	int bonenum;
	float origin[3];
}
zymvertex_t;

#endif

