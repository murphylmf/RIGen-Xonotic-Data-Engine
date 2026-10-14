
                                                                                                         
                                                                                                       
                                                      

#include <math.h>
#include <string.h>
#include "svbsp.h"
#include "polygon.h"

#define MAX_SVBSP_POLYGONPOINTS 64
#define SVBSP_CLIP_EPSILON (1.0f / 1024.0f)

#define SVBSP_DotProduct(a,b) ((a)[0]*(b)[0]+(a)[1]*(b)[1]+(a)[2]*(b)[2])

typedef struct svbsp_polygon_s
{
	float points[MAX_SVBSP_POLYGONPOINTS][3];
	                                                    
	int facesplitflag;
	int numpoints;
}
svbsp_polygon_t;

static void SVBSP_PlaneFromPoints(float *plane4f, const float *p1, const float *p2, const float *p3)
{
	float ilength;
	                               
	plane4f[0] = (p1[1] - p2[1]) * (p3[2] - p2[2]) - (p1[2] - p2[2]) * (p3[1] - p2[1]);
	plane4f[1] = (p1[2] - p2[2]) * (p3[0] - p2[0]) - (p1[0] - p2[0]) * (p3[2] - p2[2]);
	plane4f[2] = (p1[0] - p2[0]) * (p3[1] - p2[1]) - (p1[1] - p2[1]) * (p3[0] - p2[0]);
	plane4f[3] = SVBSP_DotProduct(plane4f, p1);
	                                                             
	ilength = (float)sqrt(SVBSP_DotProduct(plane4f, plane4f));
	if (ilength)
		ilength = 1.0f / ilength;
	plane4f[0] *= ilength;
	plane4f[1] *= ilength;
	plane4f[2] *= ilength;
	plane4f[3] *= ilength;
}

static void SVBSP_DividePolygon(const svbsp_polygon_t *poly, const float *plane, svbsp_polygon_t *front, svbsp_polygon_t *back, const float *dists, const int *sides)
{
	int i, j, count = poly->numpoints, frontcount = 0, backcount = 0;
	float frac, ifrac, c[3], pdist, ndist;
	const float *nextpoint;
	const float *points = poly->points[0];
	float *outfront = front->points[0];
	float *outback = back->points[0];
	for(i = 0;i < count;i++, points += 3)
	{
		j = i + 1;
		if (j >= count)
			j = 0;
		if (!(sides[i] & 2))
		{
			outfront[frontcount*3+0] = points[0];
			outfront[frontcount*3+1] = points[1];
			outfront[frontcount*3+2] = points[2];
			frontcount++;
		}
		if (!(sides[i] & 1))
		{
			outback[backcount*3+0] = points[0];
			outback[backcount*3+1] = points[1];
			outback[backcount*3+2] = points[2];
			backcount++;
		}
		if ((sides[i] | sides[j]) == 3)
		{
			                                                                     
			if (frontcount + (count - i) > MAX_SVBSP_POLYGONPOINTS - 1)
				continue;
			if (backcount + (count - i) > MAX_SVBSP_POLYGONPOINTS - 1)
				continue;
			nextpoint = poly->points[j];
			pdist = dists[i];
			ndist = dists[j];
			frac = pdist / (pdist - ndist);
			ifrac = 1.0f - frac;
			c[0] = points[0] * ifrac + frac * nextpoint[0];
			c[1] = points[1] * ifrac + frac * nextpoint[1];
			c[2] = points[2] * ifrac + frac * nextpoint[2];
			outfront[frontcount*3+0] = c[0];
			outfront[frontcount*3+1] = c[1];
			outfront[frontcount*3+2] = c[2];
			frontcount++;
			outback[backcount*3+0] = c[0];
			outback[backcount*3+1] = c[1];
			outback[backcount*3+2] = c[2];
			backcount++;
		}
	}
	front->numpoints = frontcount;
	back->numpoints = backcount;
}

void SVBSP_Init(svbsp_t *b, const float *origin, int maxnodes, svbsp_node_t *nodes)
{
	memset(b, 0, sizeof(*b));
	b->origin[0] = origin[0];
	b->origin[1] = origin[1];
	b->origin[2] = origin[2];
	b->numnodes = 3;
	b->maxnodes = maxnodes;
	b->nodes = nodes;
	b->ranoutofnodes = 0;
	b->stat_occluders_rejected = 0;
	b->stat_occluders_accepted = 0;
	b->stat_occluders_fragments_accepted = 0;
	b->stat_occluders_fragments_rejected = 0;
	b->stat_queries_rejected = 0;
	b->stat_queries_accepted = 0;
	b->stat_queries_fragments_accepted = 0;
	b->stat_queries_fragments_rejected = 0;

	                                                                         
	                                                                    
	                                                         
	  
	                                                                        
	                                                                      
	                                                    

	            
	                                                 
	b->nodes[0].plane[0] = 1;
	b->nodes[0].plane[1] = 0;
	b->nodes[0].plane[2] = 0;
	b->nodes[0].plane[3] = origin[0];
	b->nodes[0].parent = -1;
	b->nodes[0].children[0] = 1;
	b->nodes[0].children[1] = 2;

	               
	                                                          
	b->nodes[1].plane[0] = 0;
	b->nodes[1].plane[1] = 1;
	b->nodes[1].plane[2] = 0;
	b->nodes[1].plane[3] = origin[1];
	b->nodes[1].parent = 0;
	b->nodes[1].children[0] = -1;
	b->nodes[1].children[1] = -1;

	               
	                                                          
	b->nodes[2].plane[0] = 0;
	b->nodes[2].plane[1] = 1;
	b->nodes[2].plane[2] = 0;
	b->nodes[2].plane[3] = origin[1];
	b->nodes[2].parent = 0;
	b->nodes[2].children[0] = -1;
	b->nodes[2].children[1] = -1;
}

static void SVBSP_InsertOccluderPolygonNodes(svbsp_t *b, int *parentnodenumpointer, int parentnodenum, const svbsp_polygon_t *poly, void (*fragmentcallback)(void *fragmentcallback_pointer1, int fragmentcallback_number1, svbsp_t *b, int numpoints, const float *points), void *fragmentcallback_pointer1, int fragmentcallback_number1)
{
	                                                                          
	                                                  
	int i, j, p;
	svbsp_node_t *node;

	                                                       
	if (poly->numpoints < 3)
		return;

	                                                  
	if (b->numnodes + poly->numpoints + 1 >= b->maxnodes)
	{
		b->ranoutofnodes = 1;
		return;
	}

	                                                             

	                       
	                                                                        
	                         
	  
	                                                             
	  
	                                                                         
	                                                                        
	                                                                

	                                                                      
	                                                                   
	            
	for (i = 0, p = poly->numpoints - 1;i < poly->numpoints;p = i, i++)
	{
#if 1
		                                            
		for (j = parentnodenum;j >= 0;j = b->nodes[j].parent)
		{
			float *parentnodeplane = b->nodes[j].plane;
			if (fabs(SVBSP_DotProduct(poly->points[p], parentnodeplane) - parentnodeplane[3]) < SVBSP_CLIP_EPSILON
			 && fabs(SVBSP_DotProduct(poly->points[i], parentnodeplane) - parentnodeplane[3]) < SVBSP_CLIP_EPSILON
			 && fabs(SVBSP_DotProduct(b->origin      , parentnodeplane) - parentnodeplane[3]) < SVBSP_CLIP_EPSILON)
				break;
		}
		if (j >= 0)
			continue;                                        
#endif
#if 0
		                                                                     
		if (poly->splitflags[i])
			continue;
#endif
		                      
		                                                           
		node = b->nodes + b->numnodes++;
		SVBSP_PlaneFromPoints(node->plane, b->origin, poly->points[p], poly->points[i]);
		                                                                      
		             
		                                                             
		  
		                                                                  
		                                         
		                                                                     
		                                                                    
		              
		for (j = 0;j < poly->numpoints;j++)
		{
			float d = SVBSP_DotProduct(poly->points[j], node->plane) - node->plane[3];
			if (d < -SVBSP_CLIP_EPSILON)
				break;
			if (d > SVBSP_CLIP_EPSILON)
			{
				node->plane[0] *= -1;
				node->plane[1] *= -1;
				node->plane[2] *= -1;
				node->plane[3] *= -1;
				break;
			}
		}
		node->parent = parentnodenum;
		node->children[0] = -1;         
		node->children[1] = -1;         
		                                
		*parentnodenumpointer = parentnodenum = (int)(node - b->nodes);
		                                                                   
		parentnodenumpointer = &node->children[1];
	}

#if 1
	                                                   
	if (!poly->facesplitflag)
#endif
	{
		                          
		                                     
		node = b->nodes + b->numnodes++;
		SVBSP_PlaneFromPoints(node->plane, poly->points[0], poly->points[1], poly->points[2]);
		                                                
		                                                                 
		if (SVBSP_DotProduct(b->origin, node->plane) - node->plane[3] < -SVBSP_CLIP_EPSILON)
		{
			node->plane[0] *= -1;
			node->plane[1] *= -1;
			node->plane[2] *= -1;
			node->plane[3] *= -1;
		}
		node->parent = parentnodenum;
		node->children[0] = -1;         
		node->children[1] = -2;          
		                                
		                                                                     
		*parentnodenumpointer = (int)(node - b->nodes);
	}
}

static int SVBSP_AddPolygonNode(svbsp_t *b, int *parentnodenumpointer, int parentnodenum, const svbsp_polygon_t *poly, int insertoccluder, void (*fragmentcallback)(void *fragmentcallback_pointer1, int fragmentcallback_number1, svbsp_t *b, int numpoints, const float *points), void *fragmentcallback_pointer1, int fragmentcallback_number1)
{
	int i;
	int s;
	int facesplitflag = poly->facesplitflag;
	int bothsides;
	float plane[4];
	float d;
	svbsp_polygon_t front;
	svbsp_polygon_t back;
	svbsp_node_t *node;
	int sides[MAX_SVBSP_POLYGONPOINTS];
	float dists[MAX_SVBSP_POLYGONPOINTS];
	if (poly->numpoints < 1)
		return 0;
	                              
	while (*parentnodenumpointer >= 0)
	{
		                
		parentnodenum = *parentnodenumpointer;
		node = b->nodes + parentnodenum;
		plane[0] = node->plane[0];
		plane[1] = node->plane[1];
		plane[2] = node->plane[2];
		plane[3] = node->plane[3];
		                                     
		bothsides = 0;
		for (i = 0;i < poly->numpoints;i++)
		{
			d = SVBSP_DotProduct(poly->points[i], plane) - plane[3];
			s = 0;
			if (d > SVBSP_CLIP_EPSILON)
				s = 1;
			if (d < -SVBSP_CLIP_EPSILON)
				s = 2;
			bothsides |= s;
			dists[i] = d;
			sides[i] = s;
		}
		                                   
		switch(bothsides)
		{
		default:
		case 0:
			                                                 
			                                                                
			                                                               
			          
			                                          
			if (insertoccluder)
				return 1;            
			                                                          
			                                                      
			facesplitflag = 1;
			parentnodenumpointer = &node->children[0];
			continue;
		case 1:
			                                        
			parentnodenumpointer = &node->children[0];
			continue;
		case 2:
			                                        
			parentnodenumpointer = &node->children[1];
			continue;
		case 3:
			                                                       
#if 1
			SVBSP_DividePolygon(poly, plane, &front, &back, dists, sides);
#else
			PolygonF_Divide(poly->numpoints, poly->points[0], plane[0], plane[1], plane[2], plane[3], SVBSP_CLIP_EPSILON, MAX_SVBSP_POLYGONPOINTS, front.points[0], &front.numpoints, MAX_SVBSP_POLYGONPOINTS, back.points[0], &back.numpoints, NULL);
			if (front.numpoints > MAX_SVBSP_POLYGONPOINTS)
				front.numpoints = MAX_SVBSP_POLYGONPOINTS;
			if (back.numpoints > MAX_SVBSP_POLYGONPOINTS)
				back.numpoints = MAX_SVBSP_POLYGONPOINTS;
#endif
			front.facesplitflag = facesplitflag;
			back.facesplitflag = facesplitflag;
			                                                             
			i  = SVBSP_AddPolygonNode(b, &node->children[0], *parentnodenumpointer, &front, insertoccluder, fragmentcallback, fragmentcallback_pointer1, fragmentcallback_number1);
			i |= SVBSP_AddPolygonNode(b, &node->children[1], *parentnodenumpointer, &back , insertoccluder, fragmentcallback, fragmentcallback_pointer1, fragmentcallback_number1);
			return i;
		}
	}
	            
	if (*parentnodenumpointer == -1)
	{
		                                              
		                                                                         
#if 0
		for (i = 0;i < poly->numpoints-2;i++)
		{
			Debug_PolygonBegin(NULL, DRAWFLAG_ADDITIVE);
			Debug_PolygonVertex(poly->points[  0][0], poly->points[  0][1], poly->points[  0][2], 0.0f, 0.0f, 0.25f, 0.0f, 0.0f, 1.0f);
			Debug_PolygonVertex(poly->points[i+1][0], poly->points[i+1][1], poly->points[i+1][2], 0.0f, 0.0f, 0.25f, 0.0f, 0.0f, 1.0f);
			Debug_PolygonVertex(poly->points[i+2][0], poly->points[i+2][1], poly->points[i+2][2], 0.0f, 0.0f, 0.25f, 0.0f, 0.0f, 1.0f);
			Debug_PolygonEnd();
		}
#endif
		if (insertoccluder)
		{
			b->stat_occluders_fragments_accepted++;
			SVBSP_InsertOccluderPolygonNodes(b, parentnodenumpointer, parentnodenum, poly, fragmentcallback, fragmentcallback_pointer1, fragmentcallback_number1);
		}
		else
			b->stat_queries_fragments_accepted++;
		if (fragmentcallback)
			fragmentcallback(fragmentcallback_pointer1, fragmentcallback_number1, b, poly->numpoints, poly->points[0]);
		return 2;
	}
	else
	{
		                                                                    
		if (insertoccluder)
			b->stat_occluders_fragments_rejected++;
		else
			b->stat_queries_fragments_rejected++;
#if 0
		for (i = 0;i < poly->numpoints-2;i++)
		{
			Debug_PolygonBegin(NULL, DRAWFLAG_ADDITIVE);
			Debug_PolygonVertex(poly->points[  0][0], poly->points[  0][1], poly->points[  0][2], 0.0f, 0.0f, 0.0f, 0.0f, 0.25f, 1.0f);
			Debug_PolygonVertex(poly->points[i+1][0], poly->points[i+1][1], poly->points[i+1][2], 0.0f, 0.0f, 0.0f, 0.0f, 0.25f, 1.0f);
			Debug_PolygonVertex(poly->points[i+2][0], poly->points[i+2][1], poly->points[i+2][2], 0.0f, 0.0f, 0.0f, 0.0f, 0.25f, 1.0f);
			Debug_PolygonEnd();
		}
#endif
	}
	return 1;
}

int SVBSP_AddPolygon(svbsp_t *b, int numpoints, const float *points, int insertoccluder, void (*fragmentcallback)(void *fragmentcallback_pointer1, int fragmentcallback_number1, svbsp_t *b, int numpoints, const float *points), void *fragmentcallback_pointer1, int fragmentcallback_number1)
{
	int i;
	int nodenum;
	svbsp_polygon_t poly;
	                                       
	                                                       
	if (numpoints < 1)
		return 0;
	                                                     
	if (numpoints > MAX_SVBSP_POLYGONPOINTS)
		return 0;
	poly.numpoints = numpoints;
	for (i = 0;i < numpoints;i++)
	{
		poly.points[i][0] = points[i*3+0];
		poly.points[i][1] = points[i*3+1];
		poly.points[i][2] = points[i*3+2];
		                                                                                                                        
		poly.facesplitflag = 0;                                                                           
	}
#if 0
                     
	for (i = 0;i < poly.numpoints-2;i++)
	{
		Debug_PolygonBegin(NULL, DRAWFLAG_ADDITIVE);
		Debug_PolygonVertex(poly.points[  0][0], poly.points[  0][1], poly.points[  0][2], 0.0f, 0.0f, 0.0f, 0.25f, 0.0f, 1.0f);
		Debug_PolygonVertex(poly.points[i+1][0], poly.points[i+1][1], poly.points[i+1][2], 0.0f, 0.0f, 0.0f, 0.25f, 0.0f, 1.0f);
		Debug_PolygonVertex(poly.points[i+2][0], poly.points[i+2][1], poly.points[i+2][2], 0.0f, 0.0f, 0.0f, 0.25f, 0.0f, 1.0f);
		Debug_PolygonEnd();
	}
#endif
	nodenum = 0;
	i = SVBSP_AddPolygonNode(b, &nodenum, -1, &poly, insertoccluder, fragmentcallback, fragmentcallback_pointer1, fragmentcallback_number1);
	if (insertoccluder)
	{
		if (i & 2)
			b->stat_occluders_accepted++;
		else
			b->stat_occluders_rejected++;
	}
	else
	{
		if (i & 2)
			b->stat_queries_accepted++;
		else
			b->stat_queries_rejected++;
	}
	return i;
}

