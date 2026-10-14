
  
                                                                              
                                                                           

                                                                           
                                                                       
                                                                            
                                                                           

                                                                         
                       
     
                         
                       
                                    
                                                           
                                         
                                                                                                             
                                  
                                                                                                                                                                             

                           
                       
 
       
          
       
                      
            
          
 
                                                             
 
              
                                   
                                                                                                                        
          
 
  

#include "quakedef.h"
#include "mathlib.h"

#include <math.h>
#include "curves.h"

                                                                                               
                                                                                                             
                                                     
                                                                                                                                                            
int Q3PatchDimForTess(int size, int tess)
{
	if (tess > 0)
		return (size - 1) * tess + 1;
	else if (tess == 0)
		return (size - 1) / 2 + 1;
	else
		return 0;                                     
}

         
                                                                                      
                                                                                                        
void Q3PatchTesselateFloat(int numcomponents, int outputstride, float *outputvertices, int patchwidth, int patchheight, int inputstride, float *patchvertices, int tesselationwidth, int tesselationheight)
{
	int k, l, x, y, component, outputwidth = Q3PatchDimForTess(patchwidth, tesselationwidth);
	float px, py, *v, a, b, c, *cp[3][3], temp[3][64];
	int xmax = max(1, 2*tesselationwidth);
	int ymax = max(1, 2*tesselationheight);
	
	                                                                          
	                                                                       
	                        
	for (k = 0;k < patchheight-1;k += 2)
	{
		for (l = 0;l < patchwidth-1;l += 2)
		{
			                                                         
			for (y = 0;y < 3;y++)
				for (x = 0;x < 3;x++)
					cp[y][x] = (float *)((unsigned char *)patchvertices + ((k+y)*patchwidth+(l+x)) * inputstride);
			                  
			for (y = 0;y <= ymax;y++)
			{
				                                                            
				                                             
				py = (float)y / (float)ymax;
				                                            
				a = ((1.0f - py) * (1.0f - py));
				b = ((1.0f - py) * (2.0f * py));
				c = ((       py) * (       py));
				for (component = 0;component < numcomponents;component++)
				{
					temp[0][component] = cp[0][0][component] * a + cp[1][0][component] * b + cp[2][0][component] * c;
					temp[1][component] = cp[0][1][component] * a + cp[1][1][component] * b + cp[2][1][component] * c;
					temp[2][component] = cp[0][2][component] * a + cp[1][2][component] * b + cp[2][2][component] * c;
				}
				                                                            
				v = (float *)((unsigned char *)outputvertices + ((k * ymax / 2 + y) * outputwidth + l * xmax / 2) * outputstride);
				                                
				for (x = 0;x <= xmax;x++)
				{
					                                                  
					px = (float)x / (float)xmax;
					                                            
					                           
					a = ((1.0f - px) * (1.0f - px));
					b = ((1.0f - px) * (2.0f * px));
					c = ((       px) * (       px));
					for (component = 0;component < numcomponents;component++)
						v[component] = temp[0][component] * a + temp[1][component] * b + temp[2][component] * c;
					                                                   
					                                                      
					                                                  
					v = (float *)((unsigned char *)v + outputstride);
				}
			}
		}
	}
#if 0
	                                              
	printf("vertices[%i][%i] =\n{\n", (patchheight-1)*tesselationheight+1, (patchwidth-1)*tesselationwidth+1);
	for (y = 0;y < (patchheight-1)*tesselationheight+1;y++)
	{
		for (x = 0;x < (patchwidth-1)*tesselationwidth+1;x++)
		{
			printf("(");
			for (component = 0;component < numcomponents;component++)
				printf("%f ", outputvertices[(y*((patchwidth-1)*tesselationwidth+1)+x)*numcomponents+component]);
			printf(") ");
		}
		printf("\n");
	}
	printf("}\n");
#endif
}

static int Q3PatchTesselation(float largestsquared3xcurvearea, float tolerance)
{
	float f;
	                                                                                                                   
	f = pow(largestsquared3xcurvearea / 64.0f, 0.25f) / tolerance;
	                                   
	if(f < 0.0001)                        
		return 0;
	else if(f < 2)
		return 1;
	else
		return (int) floor(log(f) / log(2.0f)) + 1;
		                            
		                                                   
		                                               
		                   
		                   
		                   
}

static float Squared3xCurveArea(const float *a, const float *control, const float *b, int components)
{
#if 0
	                                                  

	float deviation;
	float quartercurvearea = 0;
	int c;
	for (c = 0;c < components;c++)
	{
		deviation = control[c] * 0.5f - a[c] * 0.25f - b[c] * 0.25f;
		quartercurvearea += deviation*deviation;
	}

	                                                                                    
	return quartercurvearea * quartercurvearea * 64.0;

#else
	                                                                                  
	                                                                          
	                                             
	  
	                                                                        
	                                      
	                                                                      
	                                                                    
	                                                                        
	                          
	  
	                                               
	                
	  
	                                                                      
	                                                      
	  
	                                                                          
	                                                                                  
	                                                                                 
	                                                
	  
	        
	  
	                                                                       
	                                  
	  
	                                                       
	  
	                          
	  
	                    
	  
	                  
	  
	                 
	   
	                                    
	int c;
	float aa = 0, bb = 0, ab = 0;
	for (c = 0;c < components;c++)
	{
		float xa = a[c] - control[c];
		float xb = b[c] - control[c];
		aa += xa * xa;
		ab += xa * xb;
		bb += xb * xb;
	}
	                                    
	                                          
	                                       
	return aa * bb - ab * ab;
#endif
}

                                                                                   
int Q3PatchTesselationOnX(int patchwidth, int patchheight, int components, const float *in, float tolerance)
{
	int x, y;
	const float *patch;
	float squared3xcurvearea, largestsquared3xcurvearea;
	largestsquared3xcurvearea = 0;
	for (y = 0;y < patchheight;y++)
	{
		for (x = 0;x < patchwidth-1;x += 2)
		{
			patch = in + ((y * patchwidth) + x) * components;
			squared3xcurvearea = Squared3xCurveArea(&patch[0], &patch[components], &patch[2*components], components);
			if (largestsquared3xcurvearea < squared3xcurvearea)
				largestsquared3xcurvearea = squared3xcurvearea;
		}
	}
	return Q3PatchTesselation(largestsquared3xcurvearea, tolerance);
}

                                                                                   
int Q3PatchTesselationOnY(int patchwidth, int patchheight, int components, const float *in, float tolerance)
{
	int x, y;
	const float *patch;
	float squared3xcurvearea, largestsquared3xcurvearea;
	largestsquared3xcurvearea = 0;
	for (y = 0;y < patchheight-1;y += 2)
	{
		for (x = 0;x < patchwidth;x++)
		{
			patch = in + ((y * patchwidth) + x) * components;
			squared3xcurvearea = Squared3xCurveArea(&patch[0], &patch[patchwidth*components], &patch[2*patchwidth*components], components);
			if (largestsquared3xcurvearea < squared3xcurvearea)
				largestsquared3xcurvearea = squared3xcurvearea;
		}
	}
	return Q3PatchTesselation(largestsquared3xcurvearea, tolerance);
}

                                                                      
static int FindEqualOddVertexInArray(int numcomponents, float *vertex, float *vertices, int width, int height)
{
	int x, y, j;
	for (y=0; y<height; y+=2)
	{
		for (x=0; x<width; x+=2)
		{
			qboolean found = true;
			for (j=0; j<numcomponents; j++)
				if (fabs(*(vertex+j) - *(vertices+j)) > 0.05)
				                                                               
				                                                              
				         
				{
					found = false;
					break;
				}
			if(found)
				return y*width+x;
			vertices += numcomponents*2;
		}
		vertices += numcomponents*(width-1);
	}
	return -1;
}

#define SIDE_INVALID -1
#define SIDE_X 0
#define SIDE_Y 1

static int GetSide(int p1, int p2, int width, int height, int *pointdist)
{
	int x1 = p1 % width, y1 = p1 / width;
	int x2 = p2 % width, y2 = p2 / width;
	if (p1 < 0 || p2 < 0)
		return SIDE_INVALID;
	if (x1 == x2)
	{
		if (y1 != y2)
		{
			*pointdist = abs(y2 - y1);
			return SIDE_Y;
		}
		else
			return SIDE_INVALID;
	}
	else if (y1 == y2)
	{
		*pointdist = abs(x2 - x1);
		return SIDE_X;
	}
	else
		return SIDE_INVALID;
}

                                                                                                 
                                                              
int Q3PatchAdjustTesselation(int numcomponents, patchinfo_t *patch1, float *patchvertices1, patchinfo_t *patch2, float *patchvertices2)
{
	                             
	                                         
	                                                      
	                                        

	struct {int id1,id2;} commonverts[8];
	int i, j, k, side1, side2, *tess1, *tess2;
	int dist1 = 0, dist2 = 0;
	qboolean modified = false;

	                                                         
	commonverts[0].id1 = 0;
	commonverts[1].id1 = patch1->xsize-1;
	commonverts[2].id1 = patch1->xsize*(patch1->ysize-1);
	commonverts[3].id1 = patch1->xsize*patch1->ysize-1;
	for (i=0;i<4;++i)
		commonverts[i].id2 = FindEqualOddVertexInArray(numcomponents, patchvertices1+numcomponents*commonverts[i].id1, patchvertices2, patch2->xsize, patch2->ysize);

	                              
	commonverts[4].id2 = 0;
	commonverts[5].id2 = patch2->xsize-1;
	commonverts[6].id2 = patch2->xsize*(patch2->ysize-1);
	commonverts[7].id2 = patch2->xsize*patch2->ysize-1;
	for (i=4;i<8;++i)
		commonverts[i].id1 = FindEqualOddVertexInArray(numcomponents, patchvertices2+numcomponents*commonverts[i].id2, patchvertices1, patch1->xsize, patch1->ysize);

	for (i=0;i<8;++i)
		for (j=i+1;j<8;++j)
		{
			side1 = GetSide(commonverts[i].id1,commonverts[j].id1,patch1->xsize,patch1->ysize,&dist1);
			side2 = GetSide(commonverts[i].id2,commonverts[j].id2,patch2->xsize,patch2->ysize,&dist2);

			if (side1 == SIDE_INVALID || side2 == SIDE_INVALID)
				continue;

			if(dist1 != dist2)
			{
				                                               
				continue;
			}

			                         
			for (k=0;k<PATCH_LODS_NUM;++k)
			{
				tess1 = side1 == SIDE_X ? &patch1->lods[k].xtess : &patch1->lods[k].ytess;
				tess2 = side2 == SIDE_X ? &patch2->lods[k].xtess : &patch2->lods[k].ytess;
				if (*tess1 != *tess2)
				{
					if (*tess1 < *tess2)
						*tess1 = *tess2;
					else
						*tess2 = *tess1;
					modified = true;
				}
			}
		}

	return modified;
}

#undef SIDE_INVALID 
#undef SIDE_X
#undef SIDE_Y

                                             
                                               
                                                                    
                                                     
void Q3PatchTriangleElements(int *elements, int width, int height, int firstvertex)
{
	int x, y, row0, row1;
	for (y = 0;y < height - 1;y++)
	{
		if(y % 2)
		{
			                                                                           
			row0 = firstvertex + (y + 0) * width + width - 2;
			row1 = firstvertex + (y + 1) * width + width - 2;
			for (x = 0;x < width - 1;x++)
			{
				*elements++ = row1;
				*elements++ = row1 + 1;
				*elements++ = row0 + 1;
				*elements++ = row0;
				*elements++ = row1;
				*elements++ = row0 + 1;
				row0--;
				row1--;
			}
		}
		else
		{
			row0 = firstvertex + (y + 0) * width;
			row1 = firstvertex + (y + 1) * width;
			for (x = 0;x < width - 1;x++)
			{
				*elements++ = row0;
				*elements++ = row1;
				*elements++ = row0 + 1;
				*elements++ = row1;
				*elements++ = row1 + 1;
				*elements++ = row0 + 1;
				row0++;
				row1++;
			}
		}
	}
}

