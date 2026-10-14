#include "costs.qh"

float pathlib_g_static(entity parent,vector to, float static_cost)
{
    return parent.pathlib_node_g + static_cost;
}

float pathlib_g_static_water(entity parent,vector to, float static_cost)
{
    if(inwater(to))
        return parent.pathlib_node_g + static_cost * pathlib_movecost_waterfactor;
    else
        return parent.pathlib_node_g + static_cost;
}

float pathlib_g_euclidean(entity parent,vector to, float static_cost)
{
    return parent.pathlib_node_g + vlen(parent.origin - to);
}

float pathlib_g_euclidean_water(entity parent,vector to, float static_cost)
{
    if(inwater(to))
        return parent.pathlib_node_g + vlen(parent.origin - to) * pathlib_movecost_waterfactor;
    else
        return parent.pathlib_node_g + vlen(parent.origin - to);
}


   
                                                                      
                                                                 
   
float pathlib_h_manhattan(vector a, vector b)
{
                                                    

    float h  = fabs(a.x - b.x);
    h += fabs(a.y - b.y);
    h *= pathlib_gridsize;

    return h;
}

   
                                                            
                          
   
float pathlib_h_diagonal(vector a, vector b)
{
                                                      

    float hx = fabs(a.x - b.x);
    float hy = fabs(a.y - b.y);
    float h = pathlib_movecost * max(hx, hy);

    return h;
}

   
                                                             
                                                                  
                         
   
float pathlib_h_euclidean(vector a, vector b)
{
    return vlen(a - b);
}

   
                                                             
                                               
   
float pathlib_h_diagonal2(vector a,vector b)
{
      
                                                         
                                                       
                                                                      
      

    float hx = fabs(a.x - b.x);
    float hy = fabs(a.y - b.y);

    float h_diag = min(hx,hy);
    float h_str = hx + hy;

    float h =  pathlib_movecost_diag * h_diag;
    h += pathlib_movecost * (h_str - 2 * h_diag);

    return h;
}

   
                                                             
                                               
   
float pathlib_h_diagonal2sdp(vector preprev, vector prev, vector point, vector end)
{
                                                           
                                                         
                                                                        

    float hx = fabs(point.x - end.x);
    float hy = fabs(point.y - end.y);
    float hz = fabs(point.z - end.z);

    float h_diag = min3(hx,hy,hz);
    float h_str = hx + hy + hz;

    float h =  pathlib_movecost_diag * h_diag;
    h += pathlib_movecost * (h_str - 2 * h_diag);

    vector d1 = normalize(preprev - point);
    vector d2 = normalize(prev    - point);
    float m = vlen(d1 - d2);

    return h * m;
}


float pathlib_h_diagonal3(vector a, vector b)
{
    float hx = fabs(a.x - b.x);
    float hy = fabs(a.y - b.y);
    float hz = fabs(a.z - b.z);

    float h_diag = min3(hx,hy,hz);
    float h_str = hx + hy + hz;

    float h =  pathlib_movecost_diag * h_diag;
    h += pathlib_movecost * (h_str - 2 * h_diag);

    return h;
}
