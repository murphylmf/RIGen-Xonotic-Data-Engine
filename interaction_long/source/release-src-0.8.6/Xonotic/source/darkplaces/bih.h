
                                                                                                        

                                                                                                               

#ifndef BIH_H
#define BIH_H

#define BIH_MAXUNORDEREDCHILDREN 8

typedef enum biherror_e
{
	BIHERROR_OK,                      
	BIHERROR_OUT_OF_NODES                                                                                               
}
biherror_t;

typedef enum bih_nodetype_e
{
	BIH_SPLITX = 0,
	BIH_SPLITY = 1,
	BIH_SPLITZ = 2,
	BIH_UNORDERED = 3,
}
bih_nodetype_t;

typedef enum bih_leaftype_e
{
	BIH_BRUSH = 4,
	BIH_COLLISIONTRIANGLE = 5,
	BIH_RENDERTRIANGLE = 6
}
bih_leaftype_t;

typedef struct bih_node_s
{
	bih_nodetype_t type;                                   
	                                                                                                                                                                                                
	                                                                  
	float mins[3];
	float maxs[3];
	                                                        
	int front;
	int back;
	                       
	float frontmin;               
	float backmax;               
	                                                                               
	int children[BIH_MAXUNORDEREDCHILDREN];
}
bih_node_t;

typedef struct bih_leaf_s
{
	bih_leaftype_t type;                                  
	float mins[3];
	float maxs[3];
	                                                                   
	int textureindex;
	int surfaceindex;
	int itemindex;                           
}
bih_leaf_t;

typedef struct bih_s
{
	                   
	                                                           
	int numleafs;
	bih_leaf_t *leafs;
	                                     
	int numnodes;
	bih_node_t *nodes;
	int rootnode;                                   
	                                 
	float mins[3];
	float maxs[3];

	                                     
	int maxnodes;
	int error;                                                                                
	int *leafsort;
	int *leafsortscratch;
}
bih_t;

int BIH_Build(bih_t *bih, int numleafs, bih_leaf_t *leafs, int maxnodes, bih_node_t *nodes, int *temp_leafsort, int *temp_leafsortscratch);

int BIH_GetTriangleListForBox(const bih_t *bih, int maxtriangles, int *trianglelist_idx, int *trianglelist_surf, const float *mins, const float *maxs);

#endif
