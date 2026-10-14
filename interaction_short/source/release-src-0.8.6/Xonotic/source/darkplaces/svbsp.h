
                                                                                                         
                                                                                                       

#ifndef SVBSP_H
#define SVBSP_H

typedef struct svbsp_node_s
{
	         
	                                                               
	                                              
	                                                                          
	                                                            
	int parent, children[2], padding;
	                           
	float plane[4];
}
svbsp_node_t;

typedef struct svbsp_s
{
	                             
	float origin[3];
	                                       
	int numnodes;
	                             
	int maxnodes;
	                              
	svbsp_node_t *nodes;
	                                                                       
	int ranoutofnodes;
	                  
	                                                             
	                                                                       
	                                      
	int stat_occluders_rejected;
	int stat_occluders_accepted;
	int stat_occluders_fragments_rejected;
	int stat_occluders_fragments_accepted;
	int stat_queries_rejected;
	int stat_queries_accepted;
	int stat_queries_fragments_rejected;
	int stat_queries_fragments_accepted;
}
svbsp_t;

                                                                     
  
                                                                            
                                                                             
                                          
  
                                                                   
                                             
void SVBSP_Init(svbsp_t *b, const float *origin, int maxnodes, svbsp_node_t *nodes);

                                                                             
                                                     
  
                                                                         
                                               
                                                
                                                                   
  
                                                                 
  
                                                                         
                      
                                                                              
  
                                                       
int SVBSP_AddPolygon(svbsp_t *b, int numpoints, const float *points, int insertoccluder, void (*fragmentcallback)(void *fragmentcallback_pointer1, int fragmentcallback_number1, svbsp_t *b, int numpoints, const float *points), void *fragmentcallback_pointer1, int fragmentcallback_number1);

#endif
