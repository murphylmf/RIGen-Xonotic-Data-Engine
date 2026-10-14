  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
  
                                                        
  

                                                             
                                                             
                                                             
                                                             
                                                             

#ifndef SPRITEGEN_H
#define SPRITEGEN_H

                                                         
                                                    
                                         
  
                                  
                                     
                                                            
                                            
                    
                                 
                                            
                    
              
                                                         

#define SPRITE_VERSION		1
#define SPRITEHL_VERSION	2
#define SPRITE32_VERSION	32

#define SPRITE2_VERSION		2

typedef struct dsprite_s
{
	int			ident;
	int			version;
	int			type;
	float		boundingradius;
	int			width;
	int			height;
	int			numframes;
	float		beamlength;
	synctype_t	synctype;
} dsprite_t;

typedef struct dspritehl_s
{
	int			ident;
	int			version;
	int			type;
	int			rendermode;
	float		boundingradius;
	int			width;
	int			height;
	int			numframes;
	float		beamlength;
	synctype_t	synctype;
} dspritehl_t;

typedef struct dsprite2frame_s
{
	int		width, height;
	int		origin_x, origin_y;		                                
	char	name[64];				                   
} dsprite2frame_t;

typedef struct dsprite2_s
{
	int				ident;
	int				version;
	int				numframes;
	dsprite2frame_t	frames[1];		                 
} dsprite2_t;

#define SPR_VP_PARALLEL_UPRIGHT		0
#define SPR_FACING_UPRIGHT			1
#define SPR_VP_PARALLEL				2
#define SPR_ORIENTED				3
#define SPR_VP_PARALLEL_ORIENTED	4
#define SPR_LABEL               	5
#define SPR_LABEL_SCALE         	6
#define SPR_OVERHEAD				7

#define SPRHL_OPAQUE	0
#define SPRHL_ADDITIVE	1
#define SPRHL_INDEXALPHA	2
#define SPRHL_ALPHATEST	3

typedef struct dspriteframe_s {
	int			origin[2];
	int			width;
	int			height;
} dspriteframe_t;

typedef struct dspritegroup_s {
	int			numframes;
} dspritegroup_t;

typedef struct dspriteinterval_s {
	float	interval;
} dspriteinterval_t;

typedef enum spriteframetype_e { SPR_SINGLE=0, SPR_GROUP } spriteframetype_t;

typedef struct dspriteframetype_s {
	spriteframetype_t	type;
} dspriteframetype_t;

#endif

