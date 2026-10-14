  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

#ifndef MODEL_BRUSH_H
#define MODEL_BRUSH_H

  
                                                                              

            

                                                                              
  



  
                           
  
typedef struct mvertex_s
{
	vec3_t position;
}
mvertex_t;

#define SIDE_FRONT 0
#define SIDE_BACK 1
#define SIDE_ON 2


                    
typedef struct mplane_s
{
	union
	{
		struct
		{
			vec3_t normal;
			vec_t dist;
		};
		vec4_t normal_and_dist;
	};
	                                                 
	int type;                          
	int signbits;                          
}
mplane_t;

#define SHADERSTAGE_SKY 0
#define SHADERSTAGE_NORMAL 1
#define SHADERSTAGE_COUNT 2

                          

                                                                                          
#define MATERIALFLAG_MESHCOLLISIONS 0x00000001
                                   
#define MATERIALFLAG_ALPHA 0x00000002
                                      
#define MATERIALFLAG_ADD 0x00000004
                                       
#define MATERIALFLAG_NODEPTHTEST 0x00000008
                                      
#define MATERIALFLAG_WATERALPHA 0x00000010
                        
#define MATERIALFLAG_FULLBRIGHT 0x00000020
                                                 
#define MATERIALFLAG_WALL 0x00000040
                                                               
                         
#define MATERIALFLAG_SKY 0x00000080
                                                      
#define MATERIALFLAG_WATERSCROLL 0x00000100
                            
#define MATERIALFLAG_NODRAW 0x00000200
                                    
#define MATERIALFLAG_LIGHTBOTHSIDES 0x00000400
                                  
#define MATERIALFLAG_ALPHATEST 0x00000800
                                                                             
                                                                            
#define MATERIALFLAG_BLENDED 0x00001000
                                  
#define MATERIALFLAG_CUSTOMBLEND 0x00002000
                                         
#define MATERIALFLAG_NOSHADOW 0x00004000
                                                                                                                              
#define MATERIALFLAG_VERTEXTEXTUREBLEND 0x00008000
                                                                 
#define MATERIALFLAG_NOCULLFACE 0x00010000
                                                                                                                         
#define MATERIALFLAG_SHORTDEPTHRANGE 0x00020000
                                                                                                                     
#define MATERIALFLAG_WATERSHADER 0x00040000
                                                                                            
#define MATERIALFLAG_REFRACTION 0x00080000
                    
#define MATERIALFLAG_REFLECTION 0x00100000
                                                                                                                
#define MATERIALFLAG_MODELLIGHT 0x00200000
                                                               
#define MATERIALFLAG_CUSTOMSURFACE 0x00800000
                                                                                                                  
#define MATERIALFLAG_TRANSDEPTH 0x01000000
                                            
#define MATERIALFLAG_CAMERA 0x02000000
                                                                                               
#define MATERIALFLAG_NORTLIGHT 0x04000000
                  
#define MATERIALFLAG_ALPHAGEN_VERTEX 0x08000000
                                  
#define MATERIALFLAG_OCCLUDE 0x10000000
                                                                      
#define MATERIALFLAGMASK_DEPTHSORTED (MATERIALFLAG_BLENDED | MATERIALFLAG_NODEPTHTEST)
                                                                       
#define MATERIALFLAGMASK_TRANSLUCENT (MATERIALFLAG_WATERALPHA | MATERIALFLAG_SKY | MATERIALFLAG_NODRAW | MATERIALFLAG_ALPHATEST | MATERIALFLAG_BLENDED | MATERIALFLAG_WATERSHADER | MATERIALFLAG_REFRACTION)

typedef struct medge_s
{
	unsigned int v[2];
}
medge_t;

struct entity_render_s;
struct texture_s;
struct msurface_s;

typedef struct mnode_s
{
	                                        
	mplane_t *plane;           
	struct mnode_s *parent;
	struct mportal_s *portals;
	                           
	vec3_t mins;
	vec3_t maxs;
	                                                          
	int combinedsupercontents;

	                           
	struct mnode_s *children[2];

	                 
	unsigned int firstsurface;
	unsigned int numsurfaces;
}
mnode_t;

typedef struct mleaf_s
{
	                                        
	mplane_t *plane;           
	struct mnode_s *parent;
	struct mportal_s *portals;
	                           
	vec3_t mins;
	vec3_t maxs;
	                                                          
	int combinedsupercontents;

	                           
	         
	int clusterindex;                                            
	int areaindex;         
	int containscollisionsurfaces;                                                          
	int numleafsurfaces;
	int *firstleafsurface;
	int numleafbrushes;         
	int *firstleafbrush;         
	unsigned char ambient_sound_level[NUM_AMBIENTS];         
	int contents;                                                                                              
	int portalmarkid;                                                                   
}
mleaf_t;

typedef struct mclipnode_s
{
	int			planenum;
	int			children[2];	                                
} mclipnode_t;

typedef struct hull_s
{
	mclipnode_t *clipnodes;
	mplane_t *planes;
	int firstclipnode;
	int lastclipnode;
	vec3_t clip_mins;
	vec3_t clip_maxs;
	vec3_t clip_size;
}
hull_t;

typedef struct mportal_s
{
	struct mportal_s *next;                                
	mleaf_t *here;                              
	mleaf_t *past;                                          
	int numpoints;
	mvertex_t *points;
	vec3_t mins, maxs;           
	mplane_t plane;
}
mportal_t;

typedef struct svbspmesh_s
{
	struct svbspmesh_s *next;
	int numverts, maxverts;
	int numtriangles, maxtriangles;
	float *verts;
	int *elements;
}
svbspmesh_t;

               

#define Q2BSPMAGIC ('I' + 'B' * 256 + 'S' * 65536 + 'P' * 16777216)
#define Q2BSPVERSION	38

                                                                 
                      

                                                                               

#define	Q2LUMP_ENTITIES		0
#define	Q2LUMP_PLANES			1
#define	Q2LUMP_VERTEXES		2
#define	Q2LUMP_VISIBILITY		3
#define	Q2LUMP_NODES			4
#define	Q2LUMP_TEXINFO		5
#define	Q2LUMP_FACES			6
#define	Q2LUMP_LIGHTING		7
#define	Q2LUMP_LEAFS			8
#define	Q2LUMP_LEAFFACES		9
#define	Q2LUMP_LEAFBRUSHES	10
#define	Q2LUMP_EDGES			11
#define	Q2LUMP_SURFEDGES		12
#define	Q2LUMP_MODELS			13
#define	Q2LUMP_BRUSHES		14
#define	Q2LUMP_BRUSHSIDES		15
#define	Q2LUMP_POP			16
#define	Q2LUMP_AREAS			17
#define	Q2LUMP_AREAPORTALS	18
#define	Q2HEADER_LUMPS		19

typedef struct q2dheader_s
{
	int			ident;
	int			version;
	lump_t		lumps[Q2HEADER_LUMPS];
} q2dheader_t;

typedef struct q2dmodel_s
{
	float		mins[3], maxs[3];
	float		origin[3];		                       
	int			headnode;
	int			firstface, numfaces;	                            
										                               
} q2dmodel_t;

                                                  

                                   
                                                     
                                           

                                                   

                                                                  
#define	Q2CONTENTS_SOLID			1		                                   
#define	Q2CONTENTS_WINDOW			2		                              
#define	Q2CONTENTS_AUX			4
#define	Q2CONTENTS_LAVA			8
#define	Q2CONTENTS_SLIME			16
#define	Q2CONTENTS_WATER			32
#define	Q2CONTENTS_MIST			64
#define	Q2LAST_VISIBLE_CONTENTS	64

                                                            

#define	Q2CONTENTS_AREAPORTAL		0x8000

#define	Q2CONTENTS_PLAYERCLIP		0x10000
#define	Q2CONTENTS_MONSTERCLIP	0x20000

                                                                
#define	Q2CONTENTS_CURRENT_0		0x40000
#define	Q2CONTENTS_CURRENT_90		0x80000
#define	Q2CONTENTS_CURRENT_180	0x100000
#define	Q2CONTENTS_CURRENT_270	0x200000
#define	Q2CONTENTS_CURRENT_UP		0x400000
#define	Q2CONTENTS_CURRENT_DOWN	0x800000

#define	Q2CONTENTS_ORIGIN			0x1000000	                                  

#define	Q2CONTENTS_MONSTER		0x2000000	                                           
#define	Q2CONTENTS_DEADMONSTER	0x4000000
#define	Q2CONTENTS_DETAIL			0x8000000	                                      
#define	Q2CONTENTS_TRANSLUCENT	0x10000000	                                    
#define	Q2CONTENTS_LADDER			0x20000000



#define	Q2SURF_LIGHT		0x1		                                     

#define	Q2SURF_SLICK		0x2		                       

#define	Q2SURF_SKY		0x4		                                
#define	Q2SURF_WARP		0x8		                       
#define	Q2SURF_TRANS33	0x10
#define	Q2SURF_TRANS66	0x20
#define	Q2SURF_FLOWING	0x40	                       
#define	Q2SURF_NODRAW		0x80	                                       

#define Q2SURF_HINT		0x100                                 
#define Q2SURF_SKIP		0x200                                                    

#define Q2SURF_ALPHATEST 0x02000000	                                                                                


  
                        
 
                
                                                                 
                                        
                
                          
                                                
            

                          
 
                                         
                                           
                                      
                                                            
                                                        
              

                        
 
                                                      

                 
              

                                          
                 

                              
                             

                               
                               
            

                             
 
                                                    
               
                 

                         
 
                 
                
                
             


                                                              
                                                                 
                         
                    
                    
                       
 
                   
                                              
           

                                                             
                                                             
                                                       
                              
 
                
                
                  

                        
 
                     
                      
            
  


              

#define Q3BSPVERSION	46
#define Q3BSPVERSION_LIVE 47
#define Q3BSPVERSION_IG	48

#define	Q3LUMP_ENTITIES		0                                                 
#define	Q3LUMP_TEXTURES		1                                 
#define	Q3LUMP_PLANES		2                                   
#define	Q3LUMP_NODES		3                                                                   
#define	Q3LUMP_LEAFS		4                                 
#define	Q3LUMP_LEAFFACES	5                                                
#define	Q3LUMP_LEAFBRUSHES	6                                                  
#define	Q3LUMP_MODELS		7                                          
#define	Q3LUMP_BRUSHES		8                                         
#define	Q3LUMP_BRUSHSIDES	9                                 
#define	Q3LUMP_VERTICES		10                                 
#define	Q3LUMP_TRIANGLES	11                                  
#define	Q3LUMP_EFFECTS		12                       
#define	Q3LUMP_FACES		13                            
#define	Q3LUMP_LIGHTMAPS	14                                     
#define	Q3LUMP_LIGHTGRID	15                                                
#define	Q3LUMP_PVS			16                                                                        
#define	Q3HEADER_LUMPS		17
#define	Q3LUMP_ADVERTISEMENTS 17                                                                    
#define	Q3HEADER_LUMPS_LIVE	18
#define	Q3HEADER_LUMPS_MAX	18

typedef struct q3dheader_s
{
	int			ident;
	int			version;
	lump_t		lumps[Q3HEADER_LUMPS_MAX];
} q3dheader_t;

typedef struct q3dtexture_s
{
	char name[Q3PATHLENGTH];
	int surfaceflags;
	int contents;
}
q3dtexture_t;

                                                                              
typedef struct q3dplane_s
{
	float normal[3];
	float dist;
}
q3dplane_t;

typedef struct q3dnode_s
{
	int planeindex;
	int childrenindex[2];
	int mins[3];
	int maxs[3];
}
q3dnode_t;

typedef struct q3dleaf_s
{
	int clusterindex;             
	int areaindex;              
	int mins[3];
	int maxs[3];
	int firstleafface;
	int numleaffaces;
	int firstleafbrush;
	int numleafbrushes;
}
q3dleaf_t;

typedef struct q3dmodel_s
{
	float mins[3];
	float maxs[3];
	int firstface;
	int numfaces;
	int firstbrush;
	int numbrushes;
}
q3dmodel_t;

typedef struct q3dbrush_s
{
	int firstbrushside;
	int numbrushsides;
	int textureindex;
}
q3dbrush_t;

typedef struct q3dbrushside_s
{
	int planeindex;
	int textureindex;
}
q3dbrushside_t;

typedef struct q3dbrushside_ig_s
{
	int planeindex;
	int textureindex;
	int surfaceflags;
}
q3dbrushside_ig_t;

typedef struct q3dvertex_s
{
	float origin3f[3];
	float texcoord2f[2];
	float lightmap2f[2];
	float normal3f[3];
	unsigned char color4ub[4];
}
q3dvertex_t;

typedef struct q3dmeshvertex_s
{
	int offset;                              
}
q3dmeshvertex_t;

typedef struct q3deffect_s
{
	char shadername[Q3PATHLENGTH];
	int brushindex;
	int unknown;                                                                        
}
q3deffect_t;

#define Q3FACETYPE_FLAT 1          
#define Q3FACETYPE_PATCH 2          
#define Q3FACETYPE_MESH 3          
#define Q3FACETYPE_FLARE 4                             

typedef struct q3dface_s
{
	int textureindex;
	int effectindex;              
	int type;              
	int firstvertex;
	int numvertices;
	int firstelement;
	int numelements;
	int lightmapindex;              
	int lightmap_base[2];
	int lightmap_size[2];
	union
	{
		struct
		{
			                        
			int blah[14];
		}
		unknown;
		struct
		{
			                  
			                                                                                     
			float lightmap_origin[3];
			float lightmap_vectors[2][3];
			float normal[3];
			int unused1[2];
		}
		flat;
		struct
		{
			                   
			                                                              
			                                                            
			                                       
			                                                                 
			                                      
			int unused1[3];
			float mins[3];            
			float maxs[3];            
			int unused2[3];
			int patchsize[2];                             
		}
		patch;
		struct
		{
			                  
			                                         
			int unused1[3];
			float mins[3];
			float maxs[3];
			int unused2[5];
		}
		mesh;
		struct
		{
			                   
			                                                          
			                                                                
			                                          
			                                      
			float origin[3];
			int unused1[11];
		}
		flare;
	}
	specific;
}
q3dface_t;

typedef struct q3dlightmap_s
{
	unsigned char rgb[128*128*3];
}
q3dlightmap_t;

typedef struct q3dlightgrid_s
{
	unsigned char ambientrgb[3];
	unsigned char diffusergb[3];
	unsigned char diffusepitch;
	unsigned char diffuseyaw;
}
q3dlightgrid_t;

typedef struct q3dpvs_s
{
	int numclusters;
	int chainlength;
	                          
	                                                
	                                                                                     
}
q3dpvs_t;

                        
#define Q3SURFACEFLAG_NODAMAGE 1
#define Q3SURFACEFLAG_SLICK 2
#define Q3SURFACEFLAG_SKY 4
#define Q3SURFACEFLAG_LADDER 8                      
#define Q3SURFACEFLAG_NOIMPACT 16
#define Q3SURFACEFLAG_NOMARKS 32
#define Q3SURFACEFLAG_FLESH 64                      
#define Q3SURFACEFLAG_NODRAW 128
#define Q3SURFACEFLAG_HINT 256
#define Q3SURFACEFLAG_SKIP 512                      
#define Q3SURFACEFLAG_NOLIGHTMAP 1024
#define Q3SURFACEFLAG_POINTLIGHT 2048
#define Q3SURFACEFLAG_METALSTEPS 4096
#define Q3SURFACEFLAG_NOSTEPS 8192                      
#define Q3SURFACEFLAG_NONSOLID 16384
#define Q3SURFACEFLAG_LIGHTFILTER 32768
#define Q3SURFACEFLAG_ALPHASHADOW 65536
#define Q3SURFACEFLAG_NODLIGHT 131072
#define Q3SURFACEFLAG_DUST 262144

                            
#define Q3SURFACEPARM_ALPHASHADOW 1
#define Q3SURFACEPARM_AREAPORTAL 2
#define Q3SURFACEPARM_CLUSTERPORTAL 4
#define Q3SURFACEPARM_DETAIL 8
#define Q3SURFACEPARM_DONOTENTER 16
#define Q3SURFACEPARM_FOG 32
#define Q3SURFACEPARM_LAVA 64
#define Q3SURFACEPARM_LIGHTFILTER 128
#define Q3SURFACEPARM_METALSTEPS 256
#define Q3SURFACEPARM_NODAMAGE 512
#define Q3SURFACEPARM_NODLIGHT 1024
#define Q3SURFACEPARM_NODRAW 2048
#define Q3SURFACEPARM_NODROP 4096
#define Q3SURFACEPARM_NOIMPACT 8192
#define Q3SURFACEPARM_NOLIGHTMAP 16384
#define Q3SURFACEPARM_NOMARKS 32768
#define Q3SURFACEPARM_NOMIPMAPS 65536
#define Q3SURFACEPARM_NONSOLID 131072
#define Q3SURFACEPARM_ORIGIN 262144
#define Q3SURFACEPARM_PLAYERCLIP 524288
#define Q3SURFACEPARM_SKY 1048576
#define Q3SURFACEPARM_SLICK 2097152
#define Q3SURFACEPARM_SLIME 4194304
#define Q3SURFACEPARM_STRUCTURAL 8388608
#define Q3SURFACEPARM_TRANS 16777216
#define Q3SURFACEPARM_WATER 33554432
#define Q3SURFACEPARM_POINTLIGHT 67108864
#define Q3SURFACEPARM_HINT 134217728
#define Q3SURFACEPARM_DUST 268435456
#define Q3SURFACEPARM_BOTCLIP 536870912
#define Q3SURFACEPARM_LIGHTGRID 1073741824
#define Q3SURFACEPARM_ANTIPORTAL 2147483648u

typedef struct q3mbrush_s
{
	struct colbrushf_s *colbrushf;
	int numbrushsides;
	struct q3mbrushside_s *firstbrushside;
	struct texture_s *texture;
}
q3mbrush_t;

typedef struct q3mbrushside_s
{
	struct mplane_s *plane;
	struct texture_s *texture;
}
q3mbrushside_t;

                                                                                                                   
#define CHECKPVSBIT(pvs,b) ((b) >= 0 ? (unsigned char) ((pvs)[(b) >> 3] & (1 << ((b) & 7))) : (unsigned char) false)
#define SETPVSBIT(pvs,b) (void) ((b) >= 0 ? (unsigned char) ((pvs)[(b) >> 3] |= (1 << ((b) & 7))) : (unsigned char) false)
#define CLEARPVSBIT(pvs,b) (void) ((b) >= 0 ? (unsigned char) ((pvs)[(b) >> 3] &= ~(1 << ((b) & 7))) : (unsigned char) false)

#endif

