
#ifndef MODEL_DPMODEL_H
#define MODEL_DPMODEL_H

  
                                         
                                                                                                                                                                              
                                                                                      
              
                                                              
                                                                                                                                                    
              
                                                                                                                       
                                                                    
                                                                                                                    
                                                                    
           
                                                                                                             
                                                                                                                                                                                                                                                                                                                                                                                                                                                                             
                                                                                                                                                                                                                            
                                     
                                        
                                                                                                                
                          
                                                                                             
                                         
                                                                                                                                                                            
                  
                                            
                                                                     
                                                                                                                                    
                                             
                                                                                                                                                                                          
                                                                                                                          
                        
                                                                                              
  
                             
typedef struct dpmheader_s
{
	char id[16];                                  
	unsigned int type;                                  
	unsigned int filesize;                             
	float mins[3], maxs[3], yawradius, allradius;                     
	                                         
	unsigned int num_bones;
	unsigned int num_meshs;
	unsigned int num_frames;
	unsigned int ofs_bones;                              
	unsigned int ofs_meshs;                              
	unsigned int ofs_frames;                                 
}
dpmheader_t;
                                      
typedef struct dpmmesh_s
{
	                                         
	char shadername[32];                             
	unsigned int num_verts;
	unsigned int num_tris;
	unsigned int ofs_verts;                                                       
	unsigned int ofs_texcoords;                                    
	unsigned int ofs_indices;                                                                                                             
	unsigned int ofs_groupids;                                                                                                             
}
dpmmesh_t;
                                                      
#define DPMBONEFLAG_ATTACHMENT 1
               
typedef struct dpmbone_s
{
	                                                                
	char name[32];
	                     
	signed int parent;
	                     
	unsigned int flags;
}
dpmbone_t;
                                                      
                                                                   
                                                                         
                                                                         
                                                                         
typedef struct dpmbonepose_s
{
	float matrix[3][4];
}
dpmbonepose_t;
                                                       
typedef struct dpmframe_s
{
	                                                                   
	char name[32];
	float mins[3], maxs[3], yawradius, allradius;
	int ofs_bonepositions;                                       
}
dpmframe_t;
                                  
typedef struct dpmbonevert_s
{
	                                                      
	                                                                
	                                         
	float origin[3];                                 
	float influence;                                               
	                                                    
	                                                                
	                                                                 
	float normal[3];                                
	unsigned int bonenum;                      
}
dpmbonevert_t;
                                     
typedef struct dpmvertex_s
{
	unsigned int numbones;
	                                                             
}
dpmvertex_t;

#endif

