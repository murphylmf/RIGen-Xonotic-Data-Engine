  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  


#define MAX_MAP_HULLS 16                                                 

                                                                               


#define BSPVERSION	29

typedef struct lump_s
{
	int		fileofs, filelen;
} lump_t;

#define	LUMP_ENTITIES	0
#define	LUMP_PLANES		1
#define	LUMP_TEXTURES	2
#define	LUMP_VERTEXES	3
#define	LUMP_VISIBILITY	4
#define	LUMP_NODES		5
#define	LUMP_TEXINFO	6
#define	LUMP_FACES		7
#define	LUMP_LIGHTING	8
#define	LUMP_CLIPNODES	9
#define	LUMP_LEAFS		10
#define	LUMP_MARKSURFACES 11
#define	LUMP_EDGES		12
#define	LUMP_SURFEDGES	13
#define	LUMP_MODELS		14
#define	HEADER_LUMPS	15

typedef struct hullinfo_s
{
	int			filehulls;
	float		hullsizes[MAX_MAP_HULLS][2][3];
} hullinfo_t;

typedef struct mmodel_s
{
	float		mins[3], maxs[3];
	float		origin[3];
	int			headnode[MAX_MAP_HULLS];
	int			visleafs;		                                 
	int			firstface, numfaces;
} mmodel_t;

  
                                                                                                                                                                            
                       
 
                         
                  
                               
                                                   
                           
           

                        
 
               
                             
            

                            
 
                 
                                  
                
  

#define	MIPLEVELS	4
  
                       
 
                
                        
                                                      
           


                        
 
                
            
  


                       
#define	PLANE_X			0
#define	PLANE_Y			1
#define	PLANE_Z			2

                                                  
#define	PLANE_ANYX		3
#define	PLANE_ANYY		4
#define	PLANE_ANYZ		5

  
                       
 
                 
            
                                                                   
           
  


                             
#define CONTENTS_EMPTY			-1
#define CONTENTS_SOLID			-2
#define CONTENTS_WATER			-3
#define CONTENTS_SLIME			-4
#define CONTENTS_LAVA				-5
#define CONTENTS_SKY				-6
                                               
#define CONTENTS_ORIGIN			-7                       
#define CONTENTS_CLIP				-8                             
#define CONTENTS_CURRENT_0		-9
#define CONTENTS_CURRENT_90		-10
#define CONTENTS_CURRENT_180		-11
#define CONTENTS_CURRENT_270		-12
#define CONTENTS_CURRENT_UP		-13
#define CONTENTS_CURRENT_DOWN		-14

                           
#define CONTENTSQ2_SOLID			0x00000001                                    
#define CONTENTSQ2_WINDOW			0x00000002                               
#define CONTENTSQ2_AUX				0x00000004
#define CONTENTSQ2_LAVA				0x00000008
#define CONTENTSQ2_SLIME			0x00000010
#define CONTENTSQ2_WATER			0x00000020
#define CONTENTSQ2_MIST				0x00000040
#define CONTENTSQ2_AREAPORTAL		0x00008000
#define CONTENTSQ2_PLAYERCLIP		0x00010000
#define CONTENTSQ2_MONSTERCLIP		0x00020000
#define CONTENTSQ2_CURRENT_0		0x00040000
#define CONTENTSQ2_CURRENT_90		0x00080000
#define CONTENTSQ2_CURRENT_180		0x00100000
#define CONTENTSQ2_CURRENT_270		0x00200000
#define CONTENTSQ2_CURRENT_UP		0x00400000
#define CONTENTSQ2_CURRENT_DOWN		0x00800000
#define CONTENTSQ2_ORIGIN			0x01000000                                   
#define CONTENTSQ2_MONSTER			0x02000000                                            
#define CONTENTSQ2_DEADMONSTER		0x04000000
#define CONTENTSQ2_DETAIL			0x08000000                                       
#define CONTENTSQ2_TRANSLUCENT		0x10000000                                     
#define CONTENTSQ2_LADDER			0x20000000

                           
#define CONTENTSQ3_SOLID			0x00000001                                  
#define CONTENTSQ3_LAVA				0x00000008        
#define CONTENTSQ3_SLIME			0x00000010         
#define CONTENTSQ3_WATER			0x00000020         
#define CONTENTSQ3_FOG				0x00000040           
#define CONTENTSQ3_AREAPORTAL		0x00008000                                
#define CONTENTSQ3_PLAYERCLIP		0x00010000                 
#define CONTENTSQ3_MONSTERCLIP		0x00020000                  
#define CONTENTSQ3_TELEPORTER		0x00040000                      
#define CONTENTSQ3_JUMPPAD			0x00080000                      
#define CONTENTSQ3_CLUSTERPORTAL	0x00100000                      
#define CONTENTSQ3_DONOTENTER		0x00200000                      
#define CONTENTSQ3_BOTCLIP			0x00400000                      
#define CONTENTSQ3_ORIGIN			0x01000000                                                                                 
#define CONTENTSQ3_BODY				0x02000000                                                      
#define CONTENTSQ3_CORPSE			0x04000000                                                    
#define CONTENTSQ3_DETAIL			0x08000000                                                        
#define CONTENTSQ3_STRUCTURAL		0x10000000                                   
#define CONTENTSQ3_TRANSLUCENT		0x20000000                                                 
#define CONTENTSQ3_TRIGGER			0x40000000                            
#define CONTENTSQ3_NODROP			0x80000000                                          

#define SUPERCONTENTS_SOLID			0x00000001
#define SUPERCONTENTS_WATER			0x00000002
#define SUPERCONTENTS_SLIME			0x00000004
#define SUPERCONTENTS_LAVA			0x00000008
#define SUPERCONTENTS_SKY			0x00000010
#define SUPERCONTENTS_BODY			0x00000020
#define SUPERCONTENTS_CORPSE		0x00000040
#define SUPERCONTENTS_NODROP		0x00000080
#define SUPERCONTENTS_PLAYERCLIP	0x00000100
#define SUPERCONTENTS_MONSTERCLIP	0x00000200
#define SUPERCONTENTS_DONOTENTER	0x00000400
#define SUPERCONTENTS_BOTCLIP		0x00000800
#define SUPERCONTENTS_OPAQUE		0x00001000
                                       
         
                
                
             
                   
                                                                                                              
                                                                                                              
                                                                                                                 
#define SUPERCONTENTS_LIQUIDSMASK	(SUPERCONTENTS_LAVA | SUPERCONTENTS_SLIME | SUPERCONTENTS_WATER)
#define SUPERCONTENTS_VISBLOCKERMASK	SUPERCONTENTS_OPAQUE

  
                                            
                                           
                                           
                                            
                                            
                                             
                                           
                                           
                                      
                                              
                                        
                                           
                                           
                                         
                                        
                                         
                                            
                                           
                                           
                                            
                                         
                                        
  

  
                      
 
                
                                                                  
                                       
                
                          
                                                
          

                          
 
                
                                                     
              


                        
 
                                         
              
             
            
  
#define	TEX_SPECIAL		1		                                               

                                                                          
                                             
  
                      
 
                                        
          
  

#define	MAXLIGHTMAPS	4
  
                      
 
                                                                  
                         
             

                                                 
                 
                

                
                                     
                                                          
          
  



#define	AMBIENT_WATER	0
#define	AMBIENT_SKY		1
#define	AMBIENT_SLIME	2
#define	AMBIENT_LAVA	3

#define	NUM_AMBIENTS			4		                           

                                                                      
                                       
  
                      
 
                
                                            

                                         
                

                                  
                                 

                                            
          
  

