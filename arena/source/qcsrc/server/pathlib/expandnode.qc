#include "expandnode.qh"

#include <server/pathlib/pathlib.qh>
#include <server/pathlib/utility.qh>

  
                       
                      
                     

                                                                      
 
             

                               

                                               
                                               

              
                               

           
                               

            
                               

           
                               

                    
                                   

                   
                                   

                 
                                   

                
                                   

                           
     
                                  
                                                                                  
                           

     

                       
                                     
              
                        
                
                              
     
                       
                                                         
               
         
                                     
                         
         
            
                     

             
                              
         
                                
                               
                                               
                  
         

                                                    
                 
                                         
           
           
     

                                                              

                              
     
                                                                               
     

                            
 
  

float pathlib_expandnode_star(entity node, vector start, vector goal)
{
    vector point;

    vector where = node.origin;

    vector f = PLIB_FORWARD * pathlib_gridsize;
    vector r = PLIB_RIGHT   * pathlib_gridsize;

    if (node.pathlib_node_edgeflags == pathlib_node_edgeflag_unknown)
        node.pathlib_node_edgeflags = tile_check_plus2(node, node.origin);

    if(node.pathlib_node_edgeflags == pathlib_node_edgeflag_none)
    {
        LOG_TRACE("Node at ", vtos(node.origin), " not expanable");
        return pathlib_open_cnt;
    }

              
    if (node.pathlib_node_edgeflags & pathlib_node_edgeflag_forward)
    {
        point = where + f;
        pathlib_makenode(node, start, point, goal, pathlib_movecost);
    }

           
    if (node.pathlib_node_edgeflags & pathlib_node_edgeflag_back)
    {
        point = where - f;
        pathlib_makenode(node, start, point, goal, pathlib_movecost);
    }

            
        if (node.pathlib_node_edgeflags & pathlib_node_edgeflag_right)
    {
        point = where + r;
        pathlib_makenode(node, start, point, goal, pathlib_movecost);
    }

           
    if (node.pathlib_node_edgeflags & pathlib_node_edgeflag_left)
    {
        point = where - r;
        pathlib_makenode(node, start, point, goal, pathlib_movecost);

    }

                    
    if (node.pathlib_node_edgeflags & pathlib_node_edgeflag_forwardright)
    {
        point = where + f + r;
        pathlib_makenode(node, start, point, goal, pathlib_movecost_diag);
    }

                   
    if (node.pathlib_node_edgeflags & pathlib_node_edgeflag_forwardleft)
    {
        point = where + f - r;
        pathlib_makenode(node, start, point, goal, pathlib_movecost_diag);

    }

                 
    if (node.pathlib_node_edgeflags & pathlib_node_edgeflag_backright)
    {
        point = where - f + r;
        pathlib_makenode(node, start, point, goal, pathlib_movecost_diag);
    }

                
    if (node.pathlib_node_edgeflags & pathlib_node_edgeflag_backleft)
    {
        point = where - f - r;
        pathlib_makenode(node, start, point, goal, pathlib_movecost_diag);
    }

    return pathlib_open_cnt;
}

  
                                                                        
 
                 

                               

                                               
                                               

              
                      
                                                                 

           
                      
                                                                 

            
                      
                                                                 

           
                      
                                                                 

                                              
                                              

                    
                          
                                                                 

                   
                          
                                                                 

                 
                          
                                                                 

                
                          
                                                                 

                            
 
  

float pathlib_expandnode_box(entity node, vector start, vector goal)
{
    vector v;

    for(v.z = node.origin.z - pathlib_gridsize; v.z <= node.origin.z + pathlib_gridsize; v.z += pathlib_gridsize)
    for(v.y = node.origin.y - pathlib_gridsize; v.y <= node.origin.y + pathlib_gridsize; v.y += pathlib_gridsize)
    for(v.x = node.origin.x - pathlib_gridsize; v.x <= node.origin.x + pathlib_gridsize; v.x += pathlib_gridsize)
    {
                                   
            pathlib_makenode(node,start,v,goal,pathlib_movecost);
    }

    return pathlib_open_cnt;
}
