  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
  
                                                       
  

                                                            
                                                            
                                                            
                                                            
                                                            

#ifndef MODELGEN_H
#define MODELGEN_H

#define ALIAS_VERSION	6

#define ALIAS_ONSEAM				0x0020

typedef enum aliasframetype_e { ALIAS_SINGLE=0, ALIAS_GROUP } aliasframetype_t;

typedef enum aliasskintype_e { ALIAS_SKIN_SINGLE=0, ALIAS_SKIN_GROUP } aliasskintype_t;

typedef struct mdl_s
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
mdl_t;

                        

typedef struct stvert_s
{
	int		onseam;
	int		s;
	int		t;
}
stvert_t;

typedef struct dtriangle_s
{
	int					facesfront;
	int					vertindex[3];
}
dtriangle_t;

#define DT_FACES_FRONT				0x0010

                                                                       
                 

typedef struct trivertx_s
{
	unsigned char	v[3];
	unsigned char	lightnormalindex;
}
trivertx_t;

typedef struct daliasframe_s
{
	trivertx_t	bboxmin;	                         
	trivertx_t	bboxmax;	                         
	char		name[16];	                           
}
daliasframe_t;

typedef struct daliasgroup_s
{
	int			numframes;
	trivertx_t	bboxmin;	                         
	trivertx_t	bboxmax;	                         
}
daliasgroup_t;

typedef struct daliasskingroup_s
{
	int			numskins;
}
daliasskingroup_t;

typedef struct daliasinterval_s
{
	float	interval;
}
daliasinterval_t;

typedef struct daliasskininterval_s
{
	float	interval;
}
daliasskininterval_t;

typedef struct daliasframetype_s
{
	aliasframetype_t	type;
}
daliasframetype_t;

typedef struct daliasskintype_s
{
	aliasskintype_t	type;
}
daliasskintype_t;

#endif

