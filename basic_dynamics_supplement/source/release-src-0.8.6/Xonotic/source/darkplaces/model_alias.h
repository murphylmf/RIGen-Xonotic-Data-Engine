  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

#ifndef MODEL_ALIAS_H
#define MODEL_ALIAS_H

  
                                                                              

            

                                                                          
                                                                              
  

#include "modelgen.h"

typedef struct daliashdr_s
{
	int			ident;
	int			version;
	vec3_t		scale;
	vec3_t		scale_origin;
	float		boundingradius;
	vec3_t		eyeposition;
	int			numskins;
	int			skinwidth;
	int			skinheight;
	int			numverts;
	int			numtris;
	int			numframes;
	synctype_t	synctype;
	int			flags;
	float		size;
}
daliashdr_t;

  
                                                                        

                               

                                                                        
  

                                                      
                                      

#define MD2ALIAS_VERSION	8
#define	MD2_SKINNAME	64

typedef struct md2stvert_s
{
	short	s;
	short	t;
} md2stvert_t;

typedef struct md2triangle_s
{
	short	index_xyz[3];
	short	index_st[3];
} md2triangle_t;

typedef struct md2frame_s
{
	float		scale[3];	                              
	float		translate[3];	                
	char		name[16];	                           
} md2frame_t;

                    
                                                                      
                     
                                                                      
                                                
                                                               
                               


typedef struct md2_s
{
	int			ident;
	int			version;

	int			skinwidth;
	int			skinheight;
	int			framesize;		                          

	int			num_skins;
	int			num_xyz;
	int			num_st;			                                 
	int			num_tris;
	int			num_glcmds;		                                   
	int			num_frames;

	int			ofs_skins;		                                     
	int			ofs_st;			                                     
	int			ofs_tris;		                        
	int			ofs_frames;		                         
	int			ofs_glcmds;
	int			ofs_end;		              
} md2_t;

                                                                           
                                                                         
                     
#define MD3VERSION 15
#define MD3NAME 64
#define MD3FRAMENAME 16

                                
                                               
typedef struct md3vertex_s
{
	short origin[3];
	unsigned char pitch;
	unsigned char yaw;
}
md3vertex_t;

                
typedef struct md3frameinfo_s
{
	float mins[3];
	float maxs[3];
	float origin[3];
	float radius;
	char name[MD3FRAMENAME];
}
md3frameinfo_t;

                        
typedef struct md3tag_s
{
	char name[MD3NAME];
	float origin[3];
	float rotationmatrix[9];
}
md3tag_t;

                          
typedef struct md3shader_s
{
	char name[MD3NAME];
	                                                           
	int shadernum;
}
md3shader_t;

                         
  
                                                                           
                     
  
                                                                             
                                    
typedef struct md3mesh_s
{
	char identifier[4];          
	char name[MD3NAME];
	int flags;
	int num_frames;
	int num_shaders;
	int num_vertices;
	int num_triangles;
	int lump_elements;
	int lump_shaders;
	int lump_texcoords;
	int lump_framevertices;
	int lump_end;
}
md3mesh_t;

                                                  
  
                                                                           
                                                            
typedef struct md3modelheader_s
{
	char identifier[4];          
	int version;      
	char name[MD3NAME];
	int flags;
	int num_frames;
	int num_tags;
	int num_meshes;
	int num_skins;
	int lump_frameinfo;
	int lump_tags;
	int lump_meshes;
	int lump_end;
}
md3modelheader_t;

typedef struct aliastag_s
{
	char name[MD3NAME];
	float matrixgl[12];
}
aliastag_t;

typedef struct aliasbone_s
{
	char name[MD3NAME];
	int flags;
	int parent;                    
}
aliasbone_t;

#include "model_zymotic.h"

#include "model_dpmodel.h"

#include "model_psk.h"

#include "model_iqm.h"

                                                
extern float mod_md3_sin[320];

extern cvar_t r_skeletal_debugbone;
extern cvar_t r_skeletal_debugbonecomponent;
extern cvar_t r_skeletal_debugbonevalue;
extern cvar_t r_skeletal_debugtranslatex;
extern cvar_t r_skeletal_debugtranslatey;
extern cvar_t r_skeletal_debugtranslatez;

struct model_s;
struct frameblend_s;

void *Mod_Skeletal_AnimateVertices_AllocBuffers(size_t nbytes);
void Mod_Skeletal_BuildTransforms(const struct model_s * RESTRICT model, const struct frameblend_s * RESTRICT frameblend, const skeleton_t *skeleton, float * RESTRICT bonepose, float * RESTRICT boneposerelative);

#endif

