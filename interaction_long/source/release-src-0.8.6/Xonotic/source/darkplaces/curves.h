
#ifndef CURVES_H
#define CURVES_H

#define PATCH_LODS_NUM 2
#define PATCH_LOD_COLLISION 0
#define PATCH_LOD_VISUAL 1

typedef struct patchinfo_s
{
	int xsize, ysize;
	struct {
		int xtess, ytess;
	} lods[PATCH_LODS_NUM];
} patchinfo_t;

                                                                                               
                                                                                                         
                                                     
int Q3PatchDimForTess(int size, int tess);

         
                                                                                      
                                                                                                        
void Q3PatchTesselateFloat(int numcomponents, int outputstride, float *outputvertices, int patchwidth, int patchheight, int inputstride, float *patchvertices, int tesselationwidth, int tesselationheight);
                                                                                   
int Q3PatchTesselationOnX(int patchwidth, int patchheight, int components, const float *in, float tolerance);
                                                                                   
int Q3PatchTesselationOnY(int patchwidth, int patchheight, int components, const float *in, float tolerance);
                                             
                                               
                                                                    
                                                      
void Q3PatchTriangleElements(int *elements, int width, int height, int firstvertex);

int Q3PatchAdjustTesselation(int numcomponents, patchinfo_t *patch1, float *patchvertices1, patchinfo_t *patch2, float *patchvertices2);

#endif

