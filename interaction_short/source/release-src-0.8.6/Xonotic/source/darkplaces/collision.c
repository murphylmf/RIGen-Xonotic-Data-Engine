
#include "quakedef.h"
#include "polygon.h"
#include "collision.h"

#define COLLISION_EDGEDIR_DOT_EPSILON (0.999f)
#define COLLISION_EDGECROSS_MINLENGTH2 (1.0f / 4194304.0f)
#define COLLISION_SNAPSCALE (32.0f)
#define COLLISION_SNAP (1.0f / COLLISION_SNAPSCALE)
#define COLLISION_SNAP2 (2.0f / COLLISION_SNAPSCALE)
#define COLLISION_PLANE_DIST_EPSILON (2.0f / COLLISION_SNAPSCALE)

cvar_t collision_impactnudge = {0, "collision_impactnudge", "0.03125", "how much to back off from the impact"};
cvar_t collision_extendmovelength = {0, "collision_extendmovelength", "16", "internal bias on trace length to ensure detection of collisions within the collision_impactnudge distance so that short moves do not degrade across frames (this does not alter the final trace length)"};
cvar_t collision_extendtraceboxlength = {0, "collision_extendtraceboxlength", "1", "internal bias for tracebox() qc builtin to account for collision_impactnudge (this does not alter the final trace length)"};
cvar_t collision_extendtracelinelength = {0, "collision_extendtracelinelength", "1", "internal bias for traceline() qc builtin to account for collision_impactnudge (this does not alter the final trace length)"};
cvar_t collision_debug_tracelineasbox = {0, "collision_debug_tracelineasbox", "0", "workaround for any bugs in Collision_TraceLineBrushFloat by using Collision_TraceBrushBrushFloat"};
cvar_t collision_cache = {0, "collision_cache", "1", "store results of collision traces for next frame to reuse if possible (optimization)"};
                                                                                                                                                                                                                                                     
cvar_t collision_triangle_bevelsides = {0, "collision_triangle_bevelsides", "0", "generate sloped edge planes on triangles - if 0, see axialedgeplanes"};
cvar_t collision_triangle_axialsides = {0, "collision_triangle_axialsides", "1", "generate axially-aligned edge planes on triangles - otherwise use perpendicular edge planes"};
cvar_t collision_bih_fullrecursion = { 0, "collision_bih_fullrecursion", "0", "debugging option to disable the bih recursion optimizations by iterating the entire tree" };

mempool_t *collision_mempool;

void Collision_Init (void)
{
	Cvar_RegisterVariable(&collision_impactnudge);
	Cvar_RegisterVariable(&collision_extendmovelength);
	Cvar_RegisterVariable(&collision_extendtracelinelength);
	Cvar_RegisterVariable(&collision_extendtraceboxlength);
	Cvar_RegisterVariable(&collision_debug_tracelineasbox);
	Cvar_RegisterVariable(&collision_cache);
                                                            
	Cvar_RegisterVariable(&collision_triangle_bevelsides);
	Cvar_RegisterVariable(&collision_triangle_axialsides);
	Cvar_RegisterVariable(&collision_bih_fullrecursion);
	collision_mempool = Mem_AllocPool("collision cache", 0, NULL);
	Collision_Cache_Init(collision_mempool);
}














static void Collision_PrintBrushAsQHull(colbrushf_t *brush, const char *name)
{
	int i;
	Con_Printf("3 %s\n%i\n", name, brush->numpoints);
	for (i = 0;i < brush->numpoints;i++)
		Con_Printf("%f %f %f\n", brush->points[i].v[0], brush->points[i].v[1], brush->points[i].v[2]);
	                   
	Con_Printf("4\n%i\n", brush->numplanes);
	for (i = 0;i < brush->numplanes;i++)
		Con_Printf("%f %f %f %f\n", brush->planes[i].normal[0], brush->planes[i].normal[1], brush->planes[i].normal[2], brush->planes[i].dist);
}

static void Collision_ValidateBrush(colbrushf_t *brush)
{
	int j, k, pointsoffplanes, pointonplanes, pointswithinsufficientplanes, printbrush;
	float d;
	printbrush = false;
	if (!brush->numpoints)
	{
		Con_Print("Collision_ValidateBrush: brush with no points!\n");
		printbrush = true;
	}
#if 0
	                                                         
	if (brush->numplanes == 0 && brush->numpoints != 1)
	{
		Con_Print("Collision_ValidateBrush: brush with no planes and more than one point!\n");
		printbrush = true;
	}
#endif
	if (brush->numplanes)
	{
		pointsoffplanes = 0;
		pointswithinsufficientplanes = 0;
		for (k = 0;k < brush->numplanes;k++)
			if (DotProduct(brush->planes[k].normal, brush->planes[k].normal) < 0.0001f)
				Con_Printf("Collision_ValidateBrush: plane #%i (%f %f %f %f) is degenerate\n", k, brush->planes[k].normal[0], brush->planes[k].normal[1], brush->planes[k].normal[2], brush->planes[k].dist);
		for (j = 0;j < brush->numpoints;j++)
		{
			pointonplanes = 0;
			for (k = 0;k < brush->numplanes;k++)
			{
				d = DotProduct(brush->points[j].v, brush->planes[k].normal) - brush->planes[k].dist;
				if (d > COLLISION_PLANE_DIST_EPSILON)
				{
					Con_Printf("Collision_ValidateBrush: point #%i (%f %f %f) infront of plane #%i (%f %f %f %f)\n", j, brush->points[j].v[0], brush->points[j].v[1], brush->points[j].v[2], k, brush->planes[k].normal[0], brush->planes[k].normal[1], brush->planes[k].normal[2], brush->planes[k].dist);
					printbrush = true;
				}
				if (fabs(d) > COLLISION_PLANE_DIST_EPSILON)
					pointsoffplanes++;
				else
					pointonplanes++;
			}
			if (pointonplanes < 3)
				pointswithinsufficientplanes++;
		}
		if (pointswithinsufficientplanes)
		{
			Con_Print("Collision_ValidateBrush: some points have insufficient planes, every point must be on at least 3 planes to form a corner.\n");
			printbrush = true;
		}
		if (pointsoffplanes == 0)                                
		{
			Con_Print("Collision_ValidateBrush: all points lie on all planes (degenerate, no brush volume!)\n");
			printbrush = true;
		}
	}
	if (printbrush)
		Collision_PrintBrushAsQHull(brush, "unnamed");
}

static float nearestplanedist_float(const float *normal, const colpointf_t *points, int numpoints)
{
	float dist, bestdist;
	if (!numpoints)
		return 0;
	bestdist = DotProduct(points->v, normal);
	points++;
	while(--numpoints)
	{
		dist = DotProduct(points->v, normal);
		bestdist = min(bestdist, dist);
		points++;
	}
	return bestdist;
}

static float furthestplanedist_float(const float *normal, const colpointf_t *points, int numpoints)
{
	float dist, bestdist;
	if (!numpoints)
		return 0;
	bestdist = DotProduct(points->v, normal);
	points++;
	while(--numpoints)
	{
		dist = DotProduct(points->v, normal);
		bestdist = max(bestdist, dist);
		points++;
	}
	return bestdist;
}

static void Collision_CalcEdgeDirsForPolygonBrushFloat(colbrushf_t *brush)
{
	int i, j;
	for (i = 0, j = brush->numpoints - 1;i < brush->numpoints;j = i, i++)
		VectorSubtract(brush->points[i].v, brush->points[j].v, brush->edgedirs[j].v);
}

colbrushf_t *Collision_NewBrushFromPlanes(mempool_t *mempool, int numoriginalplanes, const colplanef_t *originalplanes, int supercontents, int q3surfaceflags, const texture_t *texture, int hasaabbplanes)
{
	                                                         
	int j, k, w, xyzflags;
	int numpointsbuf = 0, maxpointsbuf = 256, numedgedirsbuf = 0, maxedgedirsbuf = 256, numplanesbuf = 0, maxplanesbuf = 256, numelementsbuf = 0, maxelementsbuf = 256;
	int isaabb = true;
	double maxdist;
	colbrushf_t *brush;
	colpointf_t pointsbuf[256];
	colpointf_t edgedirsbuf[256];
	colplanef_t planesbuf[256];
	int elementsbuf[1024];
	int polypointbuf[256];
	int pmaxpoints = 64;
	int pnumpoints;
	double p[2][3*64];
#if 0
	                                                                    
	memset(pointsbuf, 0, sizeof(pointsbuf));
	memset(edgedirsbuf, 0, sizeof(edgedirsbuf));
	memset(planesbuf, 0, sizeof(planesbuf));
	memset(elementsbuf, 0, sizeof(elementsbuf));
	memset(polypointbuf, 0, sizeof(polypointbuf));
	memset(p, 0, sizeof(p));
#endif

	                                                        
	if (numoriginalplanes >= maxplanesbuf)
	{
		Con_DPrint("Collision_NewBrushFromPlanes: failed to build collision brush: too many planes for buffer\n");
		return NULL;
	}

	                                                                             
	maxdist = 0;
	for (j = 0;j < numoriginalplanes;j++)
		maxdist = max(maxdist, fabs(originalplanes[j].dist));
	                                                                                                          
	maxdist = floor(maxdist * (4.0 / 1024.0) + 2) * 1024.0;
	                                                                         
	                                                                        
	                                                     
	for (j = 0;j < numoriginalplanes;j++)
	{
		int n;
		                    
		VectorCopy(originalplanes[j].normal, planesbuf[numplanesbuf].normal);
		planesbuf[numplanesbuf].dist = originalplanes[j].dist;
		planesbuf[numplanesbuf].q3surfaceflags = originalplanes[j].q3surfaceflags;
		planesbuf[numplanesbuf].texture = originalplanes[j].texture;
		numplanesbuf++;

		                                        
		w = 0;
		PolygonD_QuadForPlane(p[w], originalplanes[j].normal[0], originalplanes[j].normal[1], originalplanes[j].normal[2], originalplanes[j].dist, maxdist);
		pnumpoints = 4;
		                              
		for (k = 0;k < numoriginalplanes && pnumpoints >= 3 && pnumpoints <= pmaxpoints;k++)
		{
			                              
			                                                                     
			if (k != j)
			{
				                                                           
				                    
				PolygonD_Divide(pnumpoints, p[w], -originalplanes[k].normal[0], -originalplanes[k].normal[1], -originalplanes[k].normal[2], -originalplanes[k].dist, COLLISION_PLANE_DIST_EPSILON, pmaxpoints, p[!w], &pnumpoints, 0, NULL, NULL, NULL);
				w = !w;
			}
		}

		                              
		if (pnumpoints < 3)
		{
			                                                                                                                                                                                                                    
			continue;
		}

		for (k = 0;k < pnumpoints;k++)
		{
			int l, m;
			m = 0;
			for (l = 0;l < numoriginalplanes;l++)
				if (fabs(DotProduct(&p[w][k*3], originalplanes[l].normal) - originalplanes[l].dist) < COLLISION_PLANE_DIST_EPSILON)
					m++;
			if (m < 3)
				break;
		}
		if (k < pnumpoints)
		{
			Con_DPrintf("Collision_NewBrushFromPlanes: warning: polygon point does not lie on at least 3 planes\n");
			              
		}

		                                                          
		if (pnumpoints > pmaxpoints)
		{
			Con_DPrint("Collision_NewBrushFromPlanes: failed to build collision brush: too many points for buffer\n");
			return NULL;
		}

		                                                           
		if (numelementsbuf + (pnumpoints - 2) * 3 > maxelementsbuf)
		{
			Con_DPrint("Collision_NewBrushFromPlanes: failed to build collision brush: too many triangle elements for buffer\n");
			return NULL;
		}

		                                         
		for (k = 0;k < pnumpoints;k++)
		{
			int m;
			float v[3];
			                                                
			VectorCopy(&p[w][k*3], v);

			                                                             
			for (m = 0;m < numpointsbuf;m++)
				if (VectorDistance2(v, pointsbuf[m].v) < COLLISION_SNAP2)
					break;

			                                      
			if (m == numpointsbuf)
			{
				                                                 
				if (numpointsbuf >= maxpointsbuf)
				{
					Con_DPrint("Collision_NewBrushFromPlanes: failed to build collision brush: too many points for buffer\n");
					return NULL;
				}
				                  
				VectorCopy(&p[w][k*3], pointsbuf[numpointsbuf].v);
				numpointsbuf++;
			}

			                                
			polypointbuf[k] = m;
		}

		                                    
		                                              
		for (k = 0;k < pnumpoints - 2;k++)
		{
			elementsbuf[numelementsbuf++] = polypointbuf[0];
			elementsbuf[numelementsbuf++] = polypointbuf[k + 1];
			elementsbuf[numelementsbuf++] = polypointbuf[k + 2];
		}

		                                           
		for (k = 0, n = pnumpoints-1;k < pnumpoints;n = k, k++)
		{
			int m;
			float dir[3];
			                                                
			VectorSubtract(&p[w][k*3], &p[w][n*3], dir);
			VectorNormalize(dir);

			                                                               
			for (m = 0;m < numedgedirsbuf;m++)
				if (DotProduct(dir, edgedirsbuf[m].v) >= COLLISION_EDGEDIR_DOT_EPSILON)
					break;
			                        
			if (m < numedgedirsbuf)
				continue;

			                                 
			VectorNegate(dir, dir);
			                                                               
			for (m = 0;m < numedgedirsbuf;m++)
				if (DotProduct(dir, edgedirsbuf[m].v) >= COLLISION_EDGEDIR_DOT_EPSILON)
					break;
			                                      
			if (m == numedgedirsbuf)
			{
				                                                 
				if (numedgedirsbuf >= maxedgedirsbuf)
				{
					Con_DPrint("Collision_NewBrushFromPlanes: failed to build collision brush: too many edgedirs for buffer\n");
					return NULL;
				}
				                  
				VectorCopy(dir, edgedirsbuf[numedgedirsbuf].v);
				numedgedirsbuf++;
			}
		}

		                                                                  
		if (isaabb && (originalplanes[j].normal[0] == 0) + (originalplanes[j].normal[1] == 0) + (originalplanes[j].normal[2] == 0) < 2)
			isaabb = false;
	}

	                                                  
	if (numplanesbuf < 4)
	{
		Con_DPrintf("Collision_NewBrushFromPlanes: failed to build collision brush: %i triangles, %i planes (input was %i planes), %i vertices\n", numelementsbuf / 3, numplanesbuf, numoriginalplanes, numpointsbuf);
		return NULL;
	}

	                                                                                                          
	if (numelementsbuf < 12 || numpointsbuf < 4)
		Con_DPrintf("Collision_NewBrushFromPlanes: unable to rebuild triangles/points for collision brush: %i triangles, %i planes (input was %i planes), %i vertices\n", numelementsbuf / 3, numplanesbuf, numoriginalplanes, numpointsbuf);

	                           
	for (j = 0;j < numplanesbuf;j++)
	{
		float d = furthestplanedist_float(planesbuf[j].normal, pointsbuf, numpointsbuf);
		if (fabs(planesbuf[j].dist - d) > COLLISION_PLANE_DIST_EPSILON)
			Con_DPrintf("plane %f %f %f %f mismatches dist %f\n", planesbuf[j].normal[0], planesbuf[j].normal[1], planesbuf[j].normal[2], planesbuf[j].dist, d);
	}

	                                    
	brush = (colbrushf_t *)Mem_Alloc(mempool, sizeof(colbrushf_t) + sizeof(colpointf_t) * numpointsbuf + sizeof(colpointf_t) * numedgedirsbuf + sizeof(colplanef_t) * numplanesbuf + sizeof(int) * numelementsbuf);
	brush->isaabb = isaabb;
	brush->hasaabbplanes = hasaabbplanes;
	brush->supercontents = supercontents;
	brush->numplanes = numplanesbuf;
	brush->numedgedirs = numedgedirsbuf;
	brush->numpoints = numpointsbuf;
	brush->numtriangles = numelementsbuf / 3;
	brush->planes = (colplanef_t *)(brush + 1);
	brush->points = (colpointf_t *)(brush->planes + brush->numplanes);
	brush->edgedirs = (colpointf_t *)(brush->points + brush->numpoints);
	brush->elements = (int *)(brush->points + brush->numpoints);
	brush->q3surfaceflags = q3surfaceflags;
	brush->texture = texture;
	for (j = 0;j < brush->numpoints;j++)
	{
		brush->points[j].v[0] = pointsbuf[j].v[0];
		brush->points[j].v[1] = pointsbuf[j].v[1];
		brush->points[j].v[2] = pointsbuf[j].v[2];
	}
	for (j = 0;j < brush->numedgedirs;j++)
	{
		brush->edgedirs[j].v[0] = edgedirsbuf[j].v[0];
		brush->edgedirs[j].v[1] = edgedirsbuf[j].v[1];
		brush->edgedirs[j].v[2] = edgedirsbuf[j].v[2];
	}
	for (j = 0;j < brush->numplanes;j++)
	{
		brush->planes[j].normal[0] = planesbuf[j].normal[0];
		brush->planes[j].normal[1] = planesbuf[j].normal[1];
		brush->planes[j].normal[2] = planesbuf[j].normal[2];
		brush->planes[j].dist = planesbuf[j].dist;
		brush->planes[j].q3surfaceflags = planesbuf[j].q3surfaceflags;
		brush->planes[j].texture = planesbuf[j].texture;
	}
	for (j = 0;j < brush->numtriangles * 3;j++)
		brush->elements[j] = elementsbuf[j];

	xyzflags = 0;
	VectorClear(brush->mins);
	VectorClear(brush->maxs);
	for (j = 0;j < min(6, numoriginalplanes);j++)
	{
		     if (originalplanes[j].normal[0] ==  1) {xyzflags |=  1;brush->maxs[0] =  originalplanes[j].dist;}
		else if (originalplanes[j].normal[0] == -1) {xyzflags |=  2;brush->mins[0] = -originalplanes[j].dist;}
		else if (originalplanes[j].normal[1] ==  1) {xyzflags |=  4;brush->maxs[1] =  originalplanes[j].dist;}
		else if (originalplanes[j].normal[1] == -1) {xyzflags |=  8;brush->mins[1] = -originalplanes[j].dist;}
		else if (originalplanes[j].normal[2] ==  1) {xyzflags |= 16;brush->maxs[2] =  originalplanes[j].dist;}
		else if (originalplanes[j].normal[2] == -1) {xyzflags |= 32;brush->mins[2] = -originalplanes[j].dist;}
	}
	                                                                                                                         
	                                                                                                                                                                                     
	if (xyzflags != 63)
	{
		VectorCopy(brush->points[0].v, brush->mins);
		VectorCopy(brush->points[0].v, brush->maxs);
		for (j = 1;j < brush->numpoints;j++)
		{
			brush->mins[0] = min(brush->mins[0], brush->points[j].v[0]);
			brush->mins[1] = min(brush->mins[1], brush->points[j].v[1]);
			brush->mins[2] = min(brush->mins[2], brush->points[j].v[2]);
			brush->maxs[0] = max(brush->maxs[0], brush->points[j].v[0]);
			brush->maxs[1] = max(brush->maxs[1], brush->points[j].v[1]);
			brush->maxs[2] = max(brush->maxs[2], brush->points[j].v[2]);
		}
	}
	brush->mins[0] -= 1;
	brush->mins[1] -= 1;
	brush->mins[2] -= 1;
	brush->maxs[0] += 1;
	brush->maxs[1] += 1;
	brush->maxs[2] += 1;
	Collision_ValidateBrush(brush);
	return brush;
}



void Collision_CalcPlanesForTriangleBrushFloat(colbrushf_t *brush)
{
	float edge0[3], edge1[3], edge2[3];
	colpointf_t *p;

	TriangleNormal(brush->points[0].v, brush->points[1].v, brush->points[2].v, brush->planes[0].normal);
	if (DotProduct(brush->planes[0].normal, brush->planes[0].normal) < 0.0001f)
	{
		                                                                                        
		                                                         
		brush->numplanes = 0;
		return;
	}

	                                                      
	brush->numplanes = 5;
	brush->numedgedirs = 3;
	VectorNormalize(brush->planes[0].normal);
	brush->planes[0].dist = DotProduct(brush->points->v, brush->planes[0].normal);
	VectorNegate(brush->planes[0].normal, brush->planes[1].normal);
	brush->planes[1].dist = -brush->planes[0].dist;
	                                        
	VectorSubtract(brush->points[2].v, brush->points[0].v, edge0);
	VectorSubtract(brush->points[0].v, brush->points[1].v, edge1);
	VectorSubtract(brush->points[1].v, brush->points[2].v, edge2);
	VectorCopy(edge0, brush->edgedirs[0].v);
	VectorCopy(edge1, brush->edgedirs[1].v);
	VectorCopy(edge2, brush->edgedirs[2].v);
	                                                      
	if (collision_triangle_bevelsides.integer)
	{
		                                                                                                                                            
		CrossProduct(edge0, brush->planes->normal, brush->planes[2].normal);
		CrossProduct(edge1, brush->planes->normal, brush->planes[3].normal);
		CrossProduct(edge2, brush->planes->normal, brush->planes[4].normal);
		VectorNormalize(brush->planes[2].normal);
		VectorNormalize(brush->planes[3].normal);
		VectorNormalize(brush->planes[4].normal);
		VectorAdd(brush->planes[2].normal, brush->planes[0].normal, brush->planes[2].normal);
		VectorAdd(brush->planes[3].normal, brush->planes[0].normal, brush->planes[3].normal);
		VectorAdd(brush->planes[4].normal, brush->planes[0].normal, brush->planes[4].normal);
		VectorNormalize(brush->planes[2].normal);
		VectorNormalize(brush->planes[3].normal);
		VectorNormalize(brush->planes[4].normal);
	}
	else if (collision_triangle_axialsides.integer)
	{
		float projectionnormal[3], projectionedge0[3], projectionedge1[3], projectionedge2[3];
		int i, best;
		float dist, bestdist;
		bestdist = fabs(brush->planes[0].normal[0]);
		best = 0;
		for (i = 1;i < 3;i++)
		{
			dist = fabs(brush->planes[0].normal[i]);
			if (bestdist < dist)
			{
				bestdist = dist;
				best = i;
			}
		}
		VectorClear(projectionnormal);
		if (brush->planes[0].normal[best] < 0)
			projectionnormal[best] = -1;
		else
			projectionnormal[best] = 1;
		VectorCopy(edge0, projectionedge0);
		VectorCopy(edge1, projectionedge1);
		VectorCopy(edge2, projectionedge2);
		projectionedge0[best] = 0;
		projectionedge1[best] = 0;
		projectionedge2[best] = 0;
		CrossProduct(projectionedge0, projectionnormal, brush->planes[2].normal);
		CrossProduct(projectionedge1, projectionnormal, brush->planes[3].normal);
		CrossProduct(projectionedge2, projectionnormal, brush->planes[4].normal);
		VectorNormalize(brush->planes[2].normal);
		VectorNormalize(brush->planes[3].normal);
		VectorNormalize(brush->planes[4].normal);
	}
	else
	{
		CrossProduct(edge0, brush->planes->normal, brush->planes[2].normal);
		CrossProduct(edge1, brush->planes->normal, brush->planes[3].normal);
		CrossProduct(edge2, brush->planes->normal, brush->planes[4].normal);
		VectorNormalize(brush->planes[2].normal);
		VectorNormalize(brush->planes[3].normal);
		VectorNormalize(brush->planes[4].normal);
	}
	brush->planes[2].dist = DotProduct(brush->points[2].v, brush->planes[2].normal);
	brush->planes[3].dist = DotProduct(brush->points[0].v, brush->planes[3].normal);
	brush->planes[4].dist = DotProduct(brush->points[1].v, brush->planes[4].normal);

	if (developer_extra.integer)
	{
		int i;
		                                          
		Collision_ValidateBrush(brush);
		for (i = 0;i < brush->numplanes;i++)
		{
			int j;
			for (j = 0, p = brush->points;j < brush->numpoints;j++, p++)
				if (DotProduct(p->v, brush->planes[i].normal) > brush->planes[i].dist + COLLISION_PLANE_DIST_EPSILON)
					Con_DPrintf("Error in brush plane generation, plane %i\n", i);
		}
	}
}

                                                                            
void Collision_TraceBrushBrushFloat(trace_t *trace, const colbrushf_t *trace_start, const colbrushf_t *trace_end, const colbrushf_t *other_start, const colbrushf_t *other_end)
{
	int nplane, nplane2, nedge1, nedge2, hitq3surfaceflags = 0;
	int tracenumedgedirs = trace_start->numedgedirs;
	                                                  
	int tracenumpoints = trace_start->numpoints;
	int othernumpoints = other_start->numpoints;
	int numplanes1 = other_start->numplanes;
	int numplanes2 = numplanes1 + trace_start->numplanes;
	int numplanes3 = numplanes2 + trace_start->numedgedirs * other_start->numedgedirs * 2;
	vec_t enterfrac = -1, leavefrac = 1, startdist, enddist, ie, f, imove, enterfrac2 = -1;
	vec4_t startplane;
	vec4_t endplane;
	vec4_t newimpactplane;
	const texture_t *hittexture = NULL;
	vec_t startdepth = 1;
	vec3_t startdepthnormal;
	const texture_t *starttexture = NULL;

	VectorClear(startdepthnormal);
	Vector4Clear(newimpactplane);

	                                                                                                                             
	if (trace_start->isaabb && other_start->hasaabbplanes)
		numplanes3 = numplanes2 = numplanes1;

	                           
	                                                                        
	                                   
	  
	                 
	                                                                        
	                                                 
	  
	                                                                       
	                             
	for (nplane = 0;nplane < numplanes3;nplane++)
	{
		if (nplane < numplanes1)
		{
			nplane2 = nplane;
			VectorCopy(other_start->planes[nplane2].normal, startplane);
			VectorCopy(other_end->planes[nplane2].normal, endplane);
		}
		else if (nplane < numplanes2)
		{
			nplane2 = nplane - numplanes1;
			VectorCopy(trace_start->planes[nplane2].normal, startplane);
			VectorCopy(trace_end->planes[nplane2].normal, endplane);
		}
		else
		{
			                                                 
			nplane2 = nplane - numplanes2;
			nedge1 = nplane2 >> 1;
			nedge2 = nedge1 / tracenumedgedirs;
			nedge1 -= nedge2 * tracenumedgedirs;
			if (nplane2 & 1)
			{
				CrossProduct(trace_start->edgedirs[nedge1].v, other_start->edgedirs[nedge2].v, startplane);
				CrossProduct(trace_end->edgedirs[nedge1].v, other_end->edgedirs[nedge2].v, endplane);
			}
			else
			{
				CrossProduct(other_start->edgedirs[nedge2].v, trace_start->edgedirs[nedge1].v, startplane);
				CrossProduct(other_end->edgedirs[nedge2].v, trace_end->edgedirs[nedge1].v, endplane);
			}
			if (VectorLength2(startplane) < COLLISION_EDGECROSS_MINLENGTH2 || VectorLength2(endplane) < COLLISION_EDGECROSS_MINLENGTH2)
				continue;                            
			VectorNormalize(startplane);
			VectorNormalize(endplane);
		}
		startplane[3] = furthestplanedist_float(startplane, other_start->points, othernumpoints);
		endplane[3] = furthestplanedist_float(endplane, other_end->points, othernumpoints);
		startdist = nearestplanedist_float(startplane, trace_start->points, tracenumpoints) - startplane[3];
		enddist = nearestplanedist_float(endplane, trace_end->points, tracenumpoints) - endplane[3];
		                                                                                                                                                                                            

		                                                                
		if (startdist <= 0.0f && nplane < numplanes1 && (startdepth < startdist || startdepth == 1))
		{
			startdepth = startdist;
			VectorCopy(startplane, startdepthnormal);
			starttexture = other_start->planes[nplane2].texture;
		}

		if (startdist > enddist)
		{
			                    
			if (enddist > 0.0f)
				return;
			if (startdist >= 0)
			{
				        
				imove = 1 / (startdist - enddist);
				f = startdist * imove;
				                                                     
				if (enterfrac < f)
				{
					                               
					enterfrac = f;
					                                                         
					if (enterfrac > leavefrac)
						return;
					                                                        
					                                         
					enterfrac2 = (startdist - collision_impactnudge.value) * imove;
					                                                          
					                                                    
					            
					if (enterfrac2 >= trace->fraction)
						return;
					ie = 1.0f - enterfrac;
					newimpactplane[0] = startplane[0] * ie + endplane[0] * enterfrac;
					newimpactplane[1] = startplane[1] * ie + endplane[1] * enterfrac;
					newimpactplane[2] = startplane[2] * ie + endplane[2] * enterfrac;
					newimpactplane[3] = startplane[3] * ie + endplane[3] * enterfrac;
					if (nplane < numplanes1)
					{
						                           
						nplane2 = nplane;
						hitq3surfaceflags = other_start->planes[nplane2].q3surfaceflags;
						hittexture = other_start->planes[nplane2].texture;
					}
					else if (nplane < numplanes2)
					{
						                           
						nplane2 = nplane - numplanes1;
						hitq3surfaceflags = trace_start->planes[nplane2].q3surfaceflags;
						hittexture = trace_start->planes[nplane2].texture;
					}
					else
					{
						hitq3surfaceflags = other_start->q3surfaceflags;
						hittexture = other_start->texture;
					}
				}
			}
		}
		else
		{
			                      
			if (startdist >= 0)
				return;
			if (enddist > 0)
			{
				        
				f = startdist / (startdist - enddist);
				                                                     
				if (leavefrac > f)
				{
					                               
					leavefrac = f;
					                                                         
					if (enterfrac > leavefrac)
						return;
				}
			}
		}
	}

	                                                                        
	                                          

	                                                    
	if (enterfrac > -1)
	{
		                                                                     
		                                   
		if ((trace->hitsupercontentsmask & other_start->supercontents) && !(trace->skipsupercontentsmask & other_start->supercontents) && !(trace->skipmaterialflagsmask & (hittexture ? hittexture->currentmaterialflags : 0)))
		{
			trace->hitsupercontents = other_start->supercontents;
			trace->hitq3surfaceflags = hitq3surfaceflags;
			trace->hittexture = hittexture;
			trace->fraction = bound(0, enterfrac2, 1);
			VectorCopy(newimpactplane, trace->plane.normal);
			trace->plane.dist = newimpactplane[3];
		}
	}
	else
	{
		                                                
		trace->startsupercontents |= other_start->supercontents;
		if ((trace->hitsupercontentsmask & other_start->supercontents) && !(trace->skipsupercontentsmask & other_start->supercontents) && !(trace->skipmaterialflagsmask & (starttexture ? starttexture->currentmaterialflags : 0)))
		{
			trace->startsolid = true;
			if (leavefrac < 1)
				trace->allsolid = true;
			VectorCopy(newimpactplane, trace->plane.normal);
			trace->plane.dist = newimpactplane[3];
			if (trace->startdepth > startdepth)
			{
				trace->startdepth = startdepth;
				VectorCopy(startdepthnormal, trace->startdepthnormal);
				trace->starttexture = starttexture;
			}
		}
	}
}

                                                                            
void Collision_TraceLineBrushFloat(trace_t *trace, const vec3_t linestart, const vec3_t lineend, const colbrushf_t *other_start, const colbrushf_t *other_end)
{
	int nplane, hitq3surfaceflags = 0;
	int numplanes = other_start->numplanes;
	vec_t enterfrac = -1, leavefrac = 1, startdist, enddist, ie, f, imove, enterfrac2 = -1;
	vec4_t startplane;
	vec4_t endplane;
	vec4_t newimpactplane;
	const texture_t *hittexture = NULL;
	vec_t startdepth = 1;
	vec3_t startdepthnormal;
	const texture_t *starttexture = NULL;

	if (collision_debug_tracelineasbox.integer)
	{
		colboxbrushf_t thisbrush_start, thisbrush_end;
		Collision_BrushForBox(&thisbrush_start, linestart, linestart, 0, 0, NULL);
		Collision_BrushForBox(&thisbrush_end, lineend, lineend, 0, 0, NULL);
		Collision_TraceBrushBrushFloat(trace, &thisbrush_start.brush, &thisbrush_end.brush, other_start, other_end);
		return;
	}

	VectorClear(startdepthnormal);
	Vector4Clear(newimpactplane);

	                           
	                                                                        
	                                   
	  
	                 
	                                                                        
	                                                 
	  
	                                                                       
	                             
	for (nplane = 0;nplane < numplanes;nplane++)
	{
		VectorCopy(other_start->planes[nplane].normal, startplane);
		startplane[3] = other_start->planes[nplane].dist;
		VectorCopy(other_end->planes[nplane].normal, endplane);
		endplane[3] = other_end->planes[nplane].dist;
		startdist = DotProduct(linestart, startplane) - startplane[3];
		enddist = DotProduct(lineend, endplane) - endplane[3];
		                                                                                                                                                                                            

		                                                                
		if (startdist <= 0.0f && (startdepth < startdist || startdepth == 1))
		{
			startdepth = startdist;
			VectorCopy(startplane, startdepthnormal);
			starttexture = other_start->planes[nplane].texture;
		}

		if (startdist > enddist)
		{
			                    
			if (enddist > 0.0f)
				return;
			if (startdist > 0)
			{
				        
				imove = 1 / (startdist - enddist);
				f = startdist * imove;
				                                                     
				if (enterfrac < f)
				{
					                               
					enterfrac = f;
					                                                         
					if (enterfrac > leavefrac)
						return;
					                                                        
					                                         
					enterfrac2 = (startdist - collision_impactnudge.value) * imove;
					                                                          
					                                                    
					            
					if (enterfrac2 >= trace->fraction)
						return;
					ie = 1.0f - enterfrac;
					newimpactplane[0] = startplane[0] * ie + endplane[0] * enterfrac;
					newimpactplane[1] = startplane[1] * ie + endplane[1] * enterfrac;
					newimpactplane[2] = startplane[2] * ie + endplane[2] * enterfrac;
					newimpactplane[3] = startplane[3] * ie + endplane[3] * enterfrac;
					hitq3surfaceflags = other_start->planes[nplane].q3surfaceflags;
					hittexture = other_start->planes[nplane].texture;
				}
			}
		}
		else
		{
			                      
			if (startdist > 0)
				return;
			if (enddist > 0)
			{
				        
				f = startdist / (startdist - enddist);
				                                                     
				if (leavefrac > f)
				{
					                               
					leavefrac = f;
					                                                         
					if (enterfrac > leavefrac)
						return;
				}
			}
		}
	}

	                                                                        
	                                          

	                                                    
	if (enterfrac > -1)
	{
		                                                                     
		                                   
		if ((trace->hitsupercontentsmask & other_start->supercontents) && !(trace->skipsupercontentsmask & other_start->supercontents) && !(trace->skipmaterialflagsmask & (hittexture ? hittexture->currentmaterialflags : 0)))
		{
			trace->hitsupercontents = other_start->supercontents;
			trace->hitq3surfaceflags = hitq3surfaceflags;
			trace->hittexture = hittexture;
			trace->fraction = bound(0, enterfrac2, 1);
			VectorCopy(newimpactplane, trace->plane.normal);
			trace->plane.dist = newimpactplane[3];
		}
	}
	else
	{
		                                                
		trace->startsupercontents |= other_start->supercontents;
		if ((trace->hitsupercontentsmask & other_start->supercontents) && !(trace->skipsupercontentsmask & other_start->supercontents) && !(trace->skipmaterialflagsmask & (starttexture ? starttexture->currentmaterialflags : 0)))
		{
			trace->startsolid = true;
			if (leavefrac < 1)
				trace->allsolid = true;
			VectorCopy(newimpactplane, trace->plane.normal);
			trace->plane.dist = newimpactplane[3];
			if (trace->startdepth > startdepth)
			{
				trace->startdepth = startdepth;
				VectorCopy(startdepthnormal, trace->startdepthnormal);
				trace->starttexture = starttexture;
			}
		}
	}
}

qboolean Collision_PointInsideBrushFloat(const vec3_t point, const colbrushf_t *brush)
{
	int nplane;
	const colplanef_t *plane;

	if (!BoxesOverlap(point, point, brush->mins, brush->maxs))
		return false;
	for (nplane = 0, plane = brush->planes;nplane < brush->numplanes;nplane++, plane++)
		if (DotProduct(plane->normal, point) > plane->dist)
			return false;
	return true;
}

void Collision_TracePointBrushFloat(trace_t *trace, const vec3_t linestart, const colbrushf_t *other_start)
{
	int nplane;
	int numplanes = other_start->numplanes;
	vec_t startdist;
	vec4_t startplane;
	vec4_t newimpactplane;
	vec_t startdepth = 1;
	vec3_t startdepthnormal;
	const texture_t *starttexture = NULL;

	VectorClear(startdepthnormal);
	Vector4Clear(newimpactplane);

	                           
	                                                                        
	                                   
	  
	                 
	                                                                        
	                                                 
	  
	                                                                       
	                             
	for (nplane = 0; nplane < numplanes; nplane++)
	{
		VectorCopy(other_start->planes[nplane].normal, startplane);
		startplane[3] = other_start->planes[nplane].dist;
		startdist = DotProduct(linestart, startplane) - startplane[3];

		if (startdist > 0)
			return;

		                                                                
		if (startdepth < startdist || startdepth == 1)
		{
			startdepth = startdist;
			VectorCopy(startplane, startdepthnormal);
			starttexture = other_start->planes[nplane].texture;
		}
	}

	                                                                        
	                                          

	                                                
	trace->startsupercontents |= other_start->supercontents;
	if ((trace->hitsupercontentsmask & other_start->supercontents) && !(trace->skipsupercontentsmask & other_start->supercontents) && !(trace->skipmaterialflagsmask & (starttexture ? starttexture->currentmaterialflags : 0)))
	{
		trace->startsolid = true;
		trace->allsolid = true;
		VectorCopy(newimpactplane, trace->plane.normal);
		trace->plane.dist = newimpactplane[3];
		if (trace->startdepth > startdepth)
		{
			trace->startdepth = startdepth;
			VectorCopy(startdepthnormal, trace->startdepthnormal);
			trace->starttexture = starttexture;
		}
	}
}

static void Collision_SnapCopyPoints(int numpoints, const colpointf_t *in, colpointf_t *out, float fractionprecision, float invfractionprecision)
{
	int i;
	for (i = 0;i < numpoints;i++)
	{
		out[i].v[0] = floor(in[i].v[0] * fractionprecision + 0.5f) * invfractionprecision;
		out[i].v[1] = floor(in[i].v[1] * fractionprecision + 0.5f) * invfractionprecision;
		out[i].v[2] = floor(in[i].v[2] * fractionprecision + 0.5f) * invfractionprecision;
	}
}

void Collision_TraceBrushTriangleMeshFloat(trace_t *trace, const colbrushf_t *thisbrush_start, const colbrushf_t *thisbrush_end, int numtriangles, const int *element3i, const float *vertex3f, int stride, float *bbox6f, int supercontents, int q3surfaceflags, const texture_t *texture, const vec3_t segmentmins, const vec3_t segmentmaxs)
{
	int i;
	colpointf_t points[3];
	colpointf_t edgedirs[3];
	colplanef_t planes[5];
	colbrushf_t brush;
	memset(&brush, 0, sizeof(brush));
	brush.isaabb = false;
	brush.hasaabbplanes = false;
	brush.numpoints = 3;
	brush.numedgedirs = 3;
	brush.numplanes = 5;
	brush.points = points;
	brush.edgedirs = edgedirs;
	brush.planes = planes;
	brush.supercontents = supercontents;
	brush.q3surfaceflags = q3surfaceflags;
	brush.texture = texture;
	for (i = 0;i < brush.numplanes;i++)
	{
		brush.planes[i].q3surfaceflags = q3surfaceflags;
		brush.planes[i].texture = texture;
	}
	if(stride > 0)
	{
		int k, cnt, tri;
		cnt = (numtriangles + stride - 1) / stride;
		for(i = 0; i < cnt; ++i)
		{
			if(BoxesOverlap(bbox6f + i * 6, bbox6f + i * 6 + 3, segmentmins, segmentmaxs))
			{
				for(k = 0; k < stride; ++k)
				{
					tri = i * stride + k;
					if(tri >= numtriangles)
						break;
					VectorCopy(vertex3f + element3i[tri * 3 + 0] * 3, points[0].v);
					VectorCopy(vertex3f + element3i[tri * 3 + 1] * 3, points[1].v);
					VectorCopy(vertex3f + element3i[tri * 3 + 2] * 3, points[2].v);
					Collision_SnapCopyPoints(brush.numpoints, points, points, COLLISION_SNAPSCALE, COLLISION_SNAP);
					Collision_CalcEdgeDirsForPolygonBrushFloat(&brush);
					Collision_CalcPlanesForTriangleBrushFloat(&brush);
					                                               
					Collision_TraceBrushBrushFloat(trace, thisbrush_start, thisbrush_end, &brush, &brush);
				}
			}
		}
	}
	else if(stride == 0)
	{
		for (i = 0;i < numtriangles;i++, element3i += 3)
		{
			if (TriangleBBoxOverlapsBox(vertex3f + element3i[0]*3, vertex3f + element3i[1]*3, vertex3f + element3i[2]*3, segmentmins, segmentmaxs))
			{
				VectorCopy(vertex3f + element3i[0] * 3, points[0].v);
				VectorCopy(vertex3f + element3i[1] * 3, points[1].v);
				VectorCopy(vertex3f + element3i[2] * 3, points[2].v);
				Collision_SnapCopyPoints(brush.numpoints, points, points, COLLISION_SNAPSCALE, COLLISION_SNAP);
				Collision_CalcEdgeDirsForPolygonBrushFloat(&brush);
				Collision_CalcPlanesForTriangleBrushFloat(&brush);
				                                               
				Collision_TraceBrushBrushFloat(trace, thisbrush_start, thisbrush_end, &brush, &brush);
			}
		}
	}
	else
	{
		for (i = 0;i < numtriangles;i++, element3i += 3)
		{
			VectorCopy(vertex3f + element3i[0] * 3, points[0].v);
			VectorCopy(vertex3f + element3i[1] * 3, points[1].v);
			VectorCopy(vertex3f + element3i[2] * 3, points[2].v);
			Collision_SnapCopyPoints(brush.numpoints, points, points, COLLISION_SNAPSCALE, COLLISION_SNAP);
			Collision_CalcEdgeDirsForPolygonBrushFloat(&brush);
			Collision_CalcPlanesForTriangleBrushFloat(&brush);
			                                               
			Collision_TraceBrushBrushFloat(trace, thisbrush_start, thisbrush_end, &brush, &brush);
		}
	}
}

void Collision_TraceLineTriangleMeshFloat(trace_t *trace, const vec3_t linestart, const vec3_t lineend, int numtriangles, const int *element3i, const float *vertex3f, int stride, float *bbox6f, int supercontents, int q3surfaceflags, const texture_t *texture, const vec3_t segmentmins, const vec3_t segmentmaxs)
{
	int i;
	                        
	if(stride > 0)
	{
		int k, cnt, tri;
		cnt = (numtriangles + stride - 1) / stride;
		for(i = 0; i < cnt; ++i)
		{
			if(BoxesOverlap(bbox6f + i * 6, bbox6f + i * 6 + 3, segmentmins, segmentmaxs))
			{
				for(k = 0; k < stride; ++k)
				{
					tri = i * stride + k;
					if(tri >= numtriangles)
						break;
					Collision_TraceLineTriangleFloat(trace, linestart, lineend, vertex3f + element3i[tri * 3 + 0] * 3, vertex3f + element3i[tri * 3 + 1] * 3, vertex3f + element3i[tri * 3 + 2] * 3, supercontents, q3surfaceflags, texture);
				}
			}
		}
	}
	else
	{
		for (i = 0;i < numtriangles;i++, element3i += 3)
			Collision_TraceLineTriangleFloat(trace, linestart, lineend, vertex3f + element3i[0] * 3, vertex3f + element3i[1] * 3, vertex3f + element3i[2] * 3, supercontents, q3surfaceflags, texture);
	}
}

void Collision_TraceBrushTriangleFloat(trace_t *trace, const colbrushf_t *thisbrush_start, const colbrushf_t *thisbrush_end, const float *v0, const float *v1, const float *v2, int supercontents, int q3surfaceflags, const texture_t *texture)
{
	int i;
	colpointf_t points[3];
	colpointf_t edgedirs[3];
	colplanef_t planes[5];
	colbrushf_t brush;
	memset(&brush, 0, sizeof(brush));
	brush.isaabb = false;
	brush.hasaabbplanes = false;
	brush.numpoints = 3;
	brush.numedgedirs = 3;
	brush.numplanes = 5;
	brush.points = points;
	brush.edgedirs = edgedirs;
	brush.planes = planes;
	brush.supercontents = supercontents;
	brush.q3surfaceflags = q3surfaceflags;
	brush.texture = texture;
	for (i = 0;i < brush.numplanes;i++)
	{
		brush.planes[i].q3surfaceflags = q3surfaceflags;
		brush.planes[i].texture = texture;
	}
	VectorCopy(v0, points[0].v);
	VectorCopy(v1, points[1].v);
	VectorCopy(v2, points[2].v);
	Collision_SnapCopyPoints(brush.numpoints, points, points, COLLISION_SNAPSCALE, COLLISION_SNAP);
	Collision_CalcEdgeDirsForPolygonBrushFloat(&brush);
	Collision_CalcPlanesForTriangleBrushFloat(&brush);
	                                               
	Collision_TraceBrushBrushFloat(trace, thisbrush_start, thisbrush_end, &brush, &brush);
}

void Collision_BrushForBox(colboxbrushf_t *boxbrush, const vec3_t mins, const vec3_t maxs, int supercontents, int q3surfaceflags, const texture_t *texture)
{
	int i;
	memset(boxbrush, 0, sizeof(*boxbrush));
	boxbrush->brush.isaabb = true;
	boxbrush->brush.hasaabbplanes = true;
	boxbrush->brush.points = boxbrush->points;
	boxbrush->brush.edgedirs = boxbrush->edgedirs;
	boxbrush->brush.planes = boxbrush->planes;
	boxbrush->brush.supercontents = supercontents;
	boxbrush->brush.q3surfaceflags = q3surfaceflags;
	boxbrush->brush.texture = texture;
	if (VectorCompare(mins, maxs))
	{
		              
		boxbrush->brush.numpoints = 1;
		boxbrush->brush.numedgedirs = 0;
		boxbrush->brush.numplanes = 0;
		VectorCopy(mins, boxbrush->brush.points[0].v);
	}
	else
	{
		boxbrush->brush.numpoints = 8;
		boxbrush->brush.numedgedirs = 3;
		boxbrush->brush.numplanes = 6;
		                              
		                                                                     
		                              
		VectorSet(boxbrush->brush.points[0].v, mins[0], mins[1], mins[2]);
		VectorSet(boxbrush->brush.points[1].v, maxs[0], mins[1], mins[2]);
		VectorSet(boxbrush->brush.points[2].v, mins[0], maxs[1], mins[2]);
		VectorSet(boxbrush->brush.points[3].v, maxs[0], maxs[1], mins[2]);
		VectorSet(boxbrush->brush.points[4].v, mins[0], mins[1], maxs[2]);
		VectorSet(boxbrush->brush.points[5].v, maxs[0], mins[1], maxs[2]);
		VectorSet(boxbrush->brush.points[6].v, mins[0], maxs[1], maxs[2]);
		VectorSet(boxbrush->brush.points[7].v, maxs[0], maxs[1], maxs[2]);
		VectorSet(boxbrush->brush.edgedirs[0].v, 1, 0, 0);
		VectorSet(boxbrush->brush.edgedirs[1].v, 0, 1, 0);
		VectorSet(boxbrush->brush.edgedirs[2].v, 0, 0, 1);
		VectorSet(boxbrush->brush.planes[0].normal, -1,  0,  0);boxbrush->brush.planes[0].dist = -mins[0];
		VectorSet(boxbrush->brush.planes[1].normal,  1,  0,  0);boxbrush->brush.planes[1].dist =  maxs[0];
		VectorSet(boxbrush->brush.planes[2].normal,  0, -1,  0);boxbrush->brush.planes[2].dist = -mins[1];
		VectorSet(boxbrush->brush.planes[3].normal,  0,  1,  0);boxbrush->brush.planes[3].dist =  maxs[1];
		VectorSet(boxbrush->brush.planes[4].normal,  0,  0, -1);boxbrush->brush.planes[4].dist = -mins[2];
		VectorSet(boxbrush->brush.planes[5].normal,  0,  0,  1);boxbrush->brush.planes[5].dist =  maxs[2];
		for (i = 0;i < 6;i++)
		{
			boxbrush->brush.planes[i].q3surfaceflags = q3surfaceflags;
			boxbrush->brush.planes[i].texture = texture;
		}
	}
	boxbrush->brush.supercontents = supercontents;
	boxbrush->brush.q3surfaceflags = q3surfaceflags;
	boxbrush->brush.texture = texture;
	VectorSet(boxbrush->brush.mins, mins[0] - 1, mins[1] - 1, mins[2] - 1);
	VectorSet(boxbrush->brush.maxs, maxs[0] + 1, maxs[1] + 1, maxs[2] + 1);
	                                            
}

                                                                                  
                                                                                                                                                                                                                                                                                   

                                          
                                                                             
                                                                             
                                                                        
float Collision_ClipTrace_Line_Sphere(double *linestart, double *lineend, double *sphereorigin, double sphereradius, double *impactpoint, double *impactnormal)
{
	double dir[3], scale, v[3], deviationdist2, impactdist, linelength;
	                                                                        
	               
	VectorCopy(lineend, impactpoint);
	VectorClear(impactnormal);
	                           
	VectorSubtract(lineend, linestart, dir);
	                      
	linelength = VectorLength(dir);
	if (linelength)
	{
		scale = 1.0 / linelength;
		VectorScale(dir, scale, dir);
	}
	                                                                      
	                                                                    
	impactdist = DotProduct(sphereorigin, dir) - DotProduct(linestart, dir);
	                                                             
	                                                                        
	                                                                      
	VectorMA(linestart, impactdist, dir, v);
	VectorSubtract(v, sphereorigin, v);
	deviationdist2 = sphereradius * sphereradius - VectorLength2(v);
	                                                                      
	if (deviationdist2 < 0)
		return 1;                          
	                                                 
	impactdist -= sqrt(deviationdist2);
	if (impactdist >= linelength)
		return 1;                           
	if (impactdist < 0)
		return 1;                                             
	                            
	VectorMA(linestart, impactdist, dir, impactpoint);
	                                                             
	VectorSubtract(impactpoint, sphereorigin, impactnormal);
	                         
	VectorNormalize(impactnormal);
	                                       
	return impactdist / linelength;
}

void Collision_TraceLineTriangleFloat(trace_t *trace, const vec3_t linestart, const vec3_t lineend, const float *point0, const float *point1, const float *point2, int supercontents, int q3surfaceflags, const texture_t *texture)
{
	float d1, d2, d, f, f2, impact[3], edgenormal[3], faceplanenormal[3], faceplanedist, faceplanenormallength2, edge01[3], edge21[3], edge02[3];

	                          
	                                          
	                                            
	                                                                 
	                                      
	                                      
	                                       
	                                                               

	                                                               
	                                                                
	                                                                       
	                                                               

	                                                                                
	         
	VectorSubtract(point0, point1, edge01);
	VectorSubtract(point2, point1, edge21);
	CrossProduct(edge01, edge21, faceplanenormal);
	                                                                                        
	        
	faceplanenormallength2 = DotProduct(faceplanenormal, faceplanenormal);
	if (faceplanenormallength2 < 0.0001f)
		return;
	                         
	        
	faceplanedist = DotProduct(point0, faceplanenormal);

	                                                           
	                                                                        

	                               
	        
	d1 = DotProduct(faceplanenormal, linestart);
	if (d1 <= faceplanedist)
		return;

	                             
	        
	d2 = DotProduct(faceplanenormal, lineend);
	                                              
	if (d2 >= faceplanedist)
		return;

	                                                
	                                                                         

	                                                  
	                                                                
	        
	d = 1.0f / (d1 - d2);
	                                                                   
	                                                                       
	                                   
	                                                 
	        
	f = (d1 - faceplanedist) * d;
	f2  = f - collision_impactnudge.value * d;
	                                                             
	        
	if (f2 >= trace->fraction)
		return;
	                                                                       
	        
	impact[0] = linestart[0] + f * (lineend[0] - linestart[0]);
	impact[1] = linestart[1] + f * (lineend[1] - linestart[1]);
	impact[2] = linestart[2] + f * (lineend[2] - linestart[2]);

	                                                                     
	                                                                          
	                                                                           
	                                                                           

	                                                       
	                                                                      

	         
	CrossProduct(edge01, faceplanenormal, edgenormal);
	if (DotProduct(impact, edgenormal) > DotProduct(point1, edgenormal))
		return;

	         
	CrossProduct(faceplanenormal, edge21, edgenormal);
	if (DotProduct(impact, edgenormal) > DotProduct(point2, edgenormal))
		return;

	         
	VectorSubtract(point0, point2, edge02);
	CrossProduct(faceplanenormal, edge02, edgenormal);
	if (DotProduct(impact, edgenormal) > DotProduct(point0, edgenormal))
		return;

	               

	                                                             
	if (!(supercontents & trace->hitsupercontentsmask) || (supercontents & trace->skipsupercontentsmask) || (texture->currentmaterialflags & trace->skipmaterialflagsmask))
		return;

	                               
	trace->fraction = f2;

	                                                                 
	                                                                      
	d = 1.0 / sqrt(faceplanenormallength2);
	VectorScale(faceplanenormal, d, trace->plane.normal);
	trace->plane.dist = faceplanedist * d;

	trace->hitsupercontents = supercontents;
	trace->hitq3surfaceflags = q3surfaceflags;
	trace->hittexture = texture;
}

void Collision_BoundingBoxOfBrushTraceSegment(const colbrushf_t *start, const colbrushf_t *end, vec3_t mins, vec3_t maxs, float startfrac, float endfrac)
{
	int i;
	colpointf_t *ps, *pe;
	float tempstart[3], tempend[3];
	VectorLerp(start->points[0].v, startfrac, end->points[0].v, mins);
	VectorCopy(mins, maxs);
	for (i = 0, ps = start->points, pe = end->points;i < start->numpoints;i++, ps++, pe++)
	{
		VectorLerp(ps->v, startfrac, pe->v, tempstart);
		VectorLerp(ps->v, endfrac, pe->v, tempend);
		mins[0] = min(mins[0], min(tempstart[0], tempend[0]));
		mins[1] = min(mins[1], min(tempstart[1], tempend[1]));
		mins[2] = min(mins[2], min(tempstart[2], tempend[2]));
		maxs[0] = min(maxs[0], min(tempstart[0], tempend[0]));
		maxs[1] = min(maxs[1], min(tempstart[1], tempend[1]));
		maxs[2] = min(maxs[2], min(tempstart[2], tempend[2]));
	}
	mins[0] -= 1;
	mins[1] -= 1;
	mins[2] -= 1;
	maxs[0] += 1;
	maxs[1] += 1;
	maxs[2] += 1;
}

                                             

static void Collision_TranslateBrush(const vec3_t shift, colbrushf_t *brush)
{
	int i;
	                                
	for(i = 0; i < brush->numplanes; ++i)
	{
		brush->planes[i].dist += DotProduct(shift, brush->planes[i].normal);
	}
	for(i = 0; i < brush->numpoints; ++i)
	{
		VectorAdd(brush->points[i].v, shift, brush->points[i].v);
	}
	VectorAdd(brush->mins, shift, brush->mins);
	VectorAdd(brush->maxs, shift, brush->maxs);
}

static void Collision_TransformBrush(const matrix4x4_t *matrix, colbrushf_t *brush)
{
	int i;
	vec3_t v;
	                                             
	brush->isaabb = false;
	brush->hasaabbplanes = false;
	                                
	for(i = 0; i < brush->numplanes; ++i)
	{
		Matrix4x4_TransformPositivePlane(matrix, brush->planes[i].normal[0], brush->planes[i].normal[1], brush->planes[i].normal[2], brush->planes[i].dist, brush->planes[i].normal_and_dist);
	}
	for(i = 0; i < brush->numedgedirs; ++i)
	{
		Matrix4x4_Transform(matrix, brush->edgedirs[i].v, v);
		VectorCopy(v, brush->edgedirs[i].v);
	}
	for(i = 0; i < brush->numpoints; ++i)
	{
		Matrix4x4_Transform(matrix, brush->points[i].v, v);
		VectorCopy(v, brush->points[i].v);
	}
	VectorCopy(brush->points[0].v, brush->mins);
	VectorCopy(brush->points[0].v, brush->maxs);
	for(i = 1; i < brush->numpoints; ++i)
	{
		if(brush->points[i].v[0] < brush->mins[0]) brush->mins[0] = brush->points[i].v[0];
		if(brush->points[i].v[1] < brush->mins[1]) brush->mins[1] = brush->points[i].v[1];
		if(brush->points[i].v[2] < brush->mins[2]) brush->mins[2] = brush->points[i].v[2];
		if(brush->points[i].v[0] > brush->maxs[0]) brush->maxs[0] = brush->points[i].v[0];
		if(brush->points[i].v[1] > brush->maxs[1]) brush->maxs[1] = brush->points[i].v[1];
		if(brush->points[i].v[2] > brush->maxs[2]) brush->maxs[2] = brush->points[i].v[2];
	}
}

typedef struct collision_cachedtrace_parameters_s
{
	dp_model_t *model;
	vec3_t end;
	vec3_t start;
	int hitsupercontentsmask;
	int skipsupercontentsmask;
	int skipmaterialflagsmask;
	matrix4x4_t matrix;
}
collision_cachedtrace_parameters_t;

typedef struct collision_cachedtrace_s
{
	qboolean valid;
	collision_cachedtrace_parameters_t p;
	trace_t result;
}
collision_cachedtrace_t;

static mempool_t *collision_cachedtrace_mempool;
static collision_cachedtrace_t *collision_cachedtrace_array;
static int collision_cachedtrace_firstfree;
static int collision_cachedtrace_lastused;
static int collision_cachedtrace_max;
static unsigned char collision_cachedtrace_sequence;
static int collision_cachedtrace_hashsize;
static int *collision_cachedtrace_hash;
static unsigned int *collision_cachedtrace_arrayfullhashindex;
static unsigned int *collision_cachedtrace_arrayhashindex;
static unsigned int *collision_cachedtrace_arraynext;
static unsigned char *collision_cachedtrace_arrayused;
static qboolean collision_cachedtrace_rebuildhash;

void Collision_Cache_Reset(qboolean resetlimits)
{
	if (collision_cachedtrace_hash)
		Mem_Free(collision_cachedtrace_hash);
	if (collision_cachedtrace_array)
		Mem_Free(collision_cachedtrace_array);
	if (collision_cachedtrace_arrayfullhashindex)
		Mem_Free(collision_cachedtrace_arrayfullhashindex);
	if (collision_cachedtrace_arrayhashindex)
		Mem_Free(collision_cachedtrace_arrayhashindex);
	if (collision_cachedtrace_arraynext)
		Mem_Free(collision_cachedtrace_arraynext);
	if (collision_cachedtrace_arrayused)
		Mem_Free(collision_cachedtrace_arrayused);
	if (resetlimits || !collision_cachedtrace_max)
		collision_cachedtrace_max = collision_cache.integer ? 128 : 1;
	collision_cachedtrace_firstfree = 1;
	collision_cachedtrace_lastused = 0;
	collision_cachedtrace_hashsize = collision_cachedtrace_max;
	collision_cachedtrace_array = (collision_cachedtrace_t *)Mem_Alloc(collision_cachedtrace_mempool, collision_cachedtrace_max * sizeof(collision_cachedtrace_t));
	collision_cachedtrace_hash = (int *)Mem_Alloc(collision_cachedtrace_mempool, collision_cachedtrace_hashsize * sizeof(int));
	collision_cachedtrace_arrayfullhashindex = (unsigned int *)Mem_Alloc(collision_cachedtrace_mempool, collision_cachedtrace_max * sizeof(unsigned int));
	collision_cachedtrace_arrayhashindex = (unsigned int *)Mem_Alloc(collision_cachedtrace_mempool, collision_cachedtrace_max * sizeof(unsigned int));
	collision_cachedtrace_arraynext = (unsigned int *)Mem_Alloc(collision_cachedtrace_mempool, collision_cachedtrace_max * sizeof(unsigned int));
	collision_cachedtrace_arrayused = (unsigned char *)Mem_Alloc(collision_cachedtrace_mempool, collision_cachedtrace_max * sizeof(unsigned char));
	collision_cachedtrace_sequence = 1;
	collision_cachedtrace_rebuildhash = false;
}

void Collision_Cache_Init(mempool_t *mempool)
{
	collision_cachedtrace_mempool = mempool;
	Collision_Cache_Reset(true);
}

static void Collision_Cache_RebuildHash(void)
{
	int index;
	int range = collision_cachedtrace_lastused + 1;
	unsigned char sequence = collision_cachedtrace_sequence;
	int firstfree = collision_cachedtrace_max;
	int lastused = 0;
	int *hash = collision_cachedtrace_hash;
	unsigned int hashindex;
	unsigned int *arrayhashindex = collision_cachedtrace_arrayhashindex;
	unsigned int *arraynext = collision_cachedtrace_arraynext;
	collision_cachedtrace_rebuildhash = false;
	memset(collision_cachedtrace_hash, 0, collision_cachedtrace_hashsize * sizeof(int));
	for (index = 1;index < range;index++)
	{
		if (collision_cachedtrace_arrayused[index] == sequence)
		{
			hashindex = arrayhashindex[index];
			arraynext[index] = hash[hashindex];
			hash[hashindex] = index;
			lastused = index;
		}
		else
		{
			if (firstfree > index)
				firstfree = index;
			collision_cachedtrace_arrayused[index] = 0;
		}
	}
	collision_cachedtrace_firstfree = firstfree;
	collision_cachedtrace_lastused = lastused;
}

void Collision_Cache_NewFrame(void)
{
	if (collision_cache.integer)
	{
		if (collision_cachedtrace_max < 128)
			Collision_Cache_Reset(true);
	}
	else
	{
		if (collision_cachedtrace_max > 1)
			Collision_Cache_Reset(true);
	}
	                                                                    
	if (collision_cachedtrace_sequence == 255)
	{
		Collision_Cache_RebuildHash();
		collision_cachedtrace_sequence = 1;
	}
	else
	{
		collision_cachedtrace_rebuildhash = true;
		collision_cachedtrace_sequence++;
	}
}

static unsigned int Collision_Cache_HashIndexForArray(unsigned int *array, unsigned int size)
{
	unsigned int i;
	unsigned int hashindex = 0;
	                                                           
	for (i = 0;i < size;i++)
		hashindex += array[i] * (1 + i);
	return hashindex;
}

static collision_cachedtrace_t *Collision_Cache_Lookup(dp_model_t *model, const matrix4x4_t *matrix, const matrix4x4_t *inversematrix, const vec3_t start, const vec3_t end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask)
{
	int hashindex = 0;
	unsigned int fullhashindex;
	int index = 0;
	int range;
	unsigned char sequence = collision_cachedtrace_sequence;
	int *hash = collision_cachedtrace_hash;
	unsigned int *arrayfullhashindex = collision_cachedtrace_arrayfullhashindex;
	unsigned int *arraynext = collision_cachedtrace_arraynext;
	collision_cachedtrace_t *cached = collision_cachedtrace_array + index;
	collision_cachedtrace_parameters_t params;
	                                           
	if (!collision_cache.integer)
		r_refdef.stats[r_stat_photoncache_traced]++;
	else
	{
		                      
		memset(&params, 0, sizeof(params));
		params.model = model;
		VectorCopy(start, params.start);
		VectorCopy(end,   params.end);
		params.hitsupercontentsmask = hitsupercontentsmask;
		params.skipsupercontentsmask = skipsupercontentsmask;
		params.skipmaterialflagsmask = skipmaterialflagsmask;
		params.matrix = *matrix;
		fullhashindex = Collision_Cache_HashIndexForArray((unsigned int *)&params, sizeof(params) / sizeof(unsigned int));
		hashindex = (int)(fullhashindex % (unsigned int)collision_cachedtrace_hashsize);
		for (index = hash[hashindex];index;index = arraynext[index])
		{
			if (arrayfullhashindex[index] != fullhashindex)
				continue;
			cached = collision_cachedtrace_array + index;
			                                                  
			if (cached->p.model != params.model
			 || cached->p.end[0] != params.end[0]
			 || cached->p.end[1] != params.end[1]
			 || cached->p.end[2] != params.end[2]
			 || cached->p.start[0] != params.start[0]
			 || cached->p.start[1] != params.start[1]
			 || cached->p.start[2] != params.start[2]
			 || cached->p.hitsupercontentsmask != params.hitsupercontentsmask
			 || cached->p.skipsupercontentsmask != params.skipsupercontentsmask
			 || cached->p.skipmaterialflagsmask != params.skipmaterialflagsmask
			 || cached->p.matrix.m[0][0] != params.matrix.m[0][0]
			 || cached->p.matrix.m[0][1] != params.matrix.m[0][1]
			 || cached->p.matrix.m[0][2] != params.matrix.m[0][2]
			 || cached->p.matrix.m[0][3] != params.matrix.m[0][3]
			 || cached->p.matrix.m[1][0] != params.matrix.m[1][0]
			 || cached->p.matrix.m[1][1] != params.matrix.m[1][1]
			 || cached->p.matrix.m[1][2] != params.matrix.m[1][2]
			 || cached->p.matrix.m[1][3] != params.matrix.m[1][3]
			 || cached->p.matrix.m[2][0] != params.matrix.m[2][0]
			 || cached->p.matrix.m[2][1] != params.matrix.m[2][1]
			 || cached->p.matrix.m[2][2] != params.matrix.m[2][2]
			 || cached->p.matrix.m[2][3] != params.matrix.m[2][3]
			 || cached->p.matrix.m[3][0] != params.matrix.m[3][0]
			 || cached->p.matrix.m[3][1] != params.matrix.m[3][1]
			 || cached->p.matrix.m[3][2] != params.matrix.m[3][2]
			 || cached->p.matrix.m[3][3] != params.matrix.m[3][3]
			)
				continue;
			                                      
			r_refdef.stats[r_stat_photoncache_cached]++;
			cached->valid = true;
			collision_cachedtrace_arrayused[index] = collision_cachedtrace_sequence;
			return cached;
		}
		r_refdef.stats[r_stat_photoncache_traced]++;
		                             
		for (index = collision_cachedtrace_firstfree, range = collision_cachedtrace_max;index < range;index++)
			if (collision_cachedtrace_arrayused[index] == 0)
				break;
		if (index == range)
		{
			                                              
			for (index = 1, range = collision_cachedtrace_max;index < range;index++)
				if (collision_cachedtrace_arrayused[index] != sequence)
					break;
			if (index < range)
			{
				                                      
				Collision_Cache_RebuildHash();
			}
			else
			{
				                            
				collision_cachedtrace_max *= 2;
				Collision_Cache_Reset(false);
				index = 1;
			}
		}
		                                                
		collision_cachedtrace_firstfree = index + 1;
		if (collision_cachedtrace_lastused < index)
			collision_cachedtrace_lastused = index;
		cached = collision_cachedtrace_array + index;
		collision_cachedtrace_arraynext[index] = collision_cachedtrace_hash[hashindex];
		collision_cachedtrace_hash[hashindex] = index;
		collision_cachedtrace_arrayhashindex[index] = hashindex;
		cached->valid = false;
		cached->p = params;
		collision_cachedtrace_arrayfullhashindex[index] = fullhashindex;
		collision_cachedtrace_arrayused[index] = collision_cachedtrace_sequence;
	}
	return cached;
}

void Collision_Cache_ClipLineToGenericEntitySurfaces(trace_t *trace, dp_model_t *model, matrix4x4_t *matrix, matrix4x4_t *inversematrix, const vec3_t start, const vec3_t end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask)
{
	collision_cachedtrace_t *cached = Collision_Cache_Lookup(model, matrix, inversematrix, start, end, hitsupercontentsmask, skipsupercontentsmask, skipmaterialflagsmask);
	if (cached->valid)
	{
		*trace = cached->result;
		return;
	}

	Collision_ClipLineToGenericEntity(trace, model, NULL, NULL, vec3_origin, vec3_origin, 0, matrix, inversematrix, start, end, hitsupercontentsmask, skipsupercontentsmask, skipmaterialflagsmask, collision_extendmovelength.value, true);

	cached->result = *trace;
}

void Collision_Cache_ClipLineToWorldSurfaces(trace_t *trace, dp_model_t *model, const vec3_t start, const vec3_t end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask)
{
	collision_cachedtrace_t *cached = Collision_Cache_Lookup(model, &identitymatrix, &identitymatrix, start, end, hitsupercontentsmask, skipsupercontentsmask, skipmaterialflagsmask);
	if (cached->valid)
	{
		*trace = cached->result;
		return;
	}

	Collision_ClipLineToWorld(trace, model, start, end, hitsupercontentsmask, skipsupercontentsmask, skipmaterialflagsmask, collision_extendmovelength.value, true);

	cached->result = *trace;
}

typedef struct extendtraceinfo_s
{
	trace_t *trace;
	float realstart[3];
	float realend[3];
	float realdelta[3];
	float extendstart[3];
	float extendend[3];
	float extenddelta[3];
	float reallength;
	float extendlength;
	float scaletoextend;
	float extend;
}
extendtraceinfo_t;

static void Collision_ClipExtendPrepare(extendtraceinfo_t *extendtraceinfo, trace_t *trace, const vec3_t tstart, const vec3_t tend, float textend)
{
	memset(trace, 0, sizeof(*trace));
	trace->fraction = 1;

	extendtraceinfo->trace = trace;
	VectorCopy(tstart, extendtraceinfo->realstart);
	VectorCopy(tend, extendtraceinfo->realend);
	VectorSubtract(extendtraceinfo->realend, extendtraceinfo->realstart, extendtraceinfo->realdelta);
	VectorCopy(extendtraceinfo->realstart, extendtraceinfo->extendstart);
	VectorCopy(extendtraceinfo->realend, extendtraceinfo->extendend);
	VectorCopy(extendtraceinfo->realdelta, extendtraceinfo->extenddelta);
	extendtraceinfo->reallength = VectorLength(extendtraceinfo->realdelta);
	extendtraceinfo->extendlength = extendtraceinfo->reallength;
	extendtraceinfo->scaletoextend = 1.0f;
	extendtraceinfo->extend = textend;

	                                                          
	if (extendtraceinfo->reallength && extendtraceinfo->extend)
	{
		extendtraceinfo->extendlength = extendtraceinfo->reallength + extendtraceinfo->extend;
		extendtraceinfo->scaletoextend = extendtraceinfo->extendlength / extendtraceinfo->reallength;
		VectorMA(extendtraceinfo->realstart, extendtraceinfo->scaletoextend, extendtraceinfo->realdelta, extendtraceinfo->extendend);
		VectorSubtract(extendtraceinfo->extendend, extendtraceinfo->extendstart, extendtraceinfo->extenddelta);
	}
}

static void Collision_ClipExtendFinish(extendtraceinfo_t *extendtraceinfo)
{
	trace_t *trace = extendtraceinfo->trace;

	if (trace->fraction != 1.0f)
	{
		                                 
		trace->fraction *= extendtraceinfo->scaletoextend;

		                                                                                                                                                                    
		if (trace->fraction > 1.0f)
		{
			                                                                                                                
 			trace->ent = NULL;
			trace->hitq3surfaceflags = 0;
			trace->hitsupercontents = 0;
			trace->hittexture = NULL;
			VectorClear(trace->plane.normal);
			trace->plane.dist = 0.0f;
		}
	}

	               
	trace->fraction = bound(0, trace->fraction, 1);

	                             
	VectorMA(extendtraceinfo->realstart, trace->fraction, extendtraceinfo->realdelta, trace->endpos);
}

void Collision_ClipToGenericEntity(trace_t *trace, dp_model_t *model, const frameblend_t *frameblend, const skeleton_t *skeleton, const vec3_t bodymins, const vec3_t bodymaxs, int bodysupercontents, matrix4x4_t *matrix, matrix4x4_t *inversematrix, const vec3_t tstart, const vec3_t mins, const vec3_t maxs, const vec3_t tend, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask, float extend)
{
	vec3_t starttransformed, endtransformed;
	extendtraceinfo_t extendtraceinfo;
	Collision_ClipExtendPrepare(&extendtraceinfo, trace, tstart, tend, extend);

	Matrix4x4_Transform(inversematrix, extendtraceinfo.extendstart, starttransformed);
	Matrix4x4_Transform(inversematrix, extendtraceinfo.extendend, endtransformed);
#if COLLISIONPARANOID >= 3
	Con_Printf("trans(%f %f %f -> %f %f %f, %f %f %f -> %f %f %f)", extendtraceinfo.extendstart[0], extendtraceinfo.extendstart[1], extendtraceinfo.extendstart[2], starttransformed[0], starttransformed[1], starttransformed[2], extendtraceinfo.extendend[0], extendtraceinfo.extendend[1], extendtraceinfo.extendend[2], endtransformed[0], endtransformed[1], endtransformed[2]);
#endif

	if (model && model->TraceBox)
	{
		if(model->TraceBrush && (inversematrix->m[0][1] || inversematrix->m[0][2] || inversematrix->m[1][0] || inversematrix->m[1][2] || inversematrix->m[2][0] || inversematrix->m[2][1]))
		{
			                                                                                      
			                                                                
			                                                 
			colboxbrushf_t thisbrush_start, thisbrush_end;
			Collision_BrushForBox(&thisbrush_start, mins, maxs, 0, 0, NULL);
			Collision_BrushForBox(&thisbrush_end, mins, maxs, 0, 0, NULL);
			Collision_TranslateBrush(extendtraceinfo.extendstart, &thisbrush_start.brush);
			Collision_TranslateBrush(extendtraceinfo.extendend, &thisbrush_end.brush);
			Collision_TransformBrush(inversematrix, &thisbrush_start.brush);
			Collision_TransformBrush(inversematrix, &thisbrush_end.brush);
			                                                                     
			                                                                 
			model->TraceBrush(model, frameblend, skeleton, trace, &thisbrush_start.brush, &thisbrush_end.brush, hitsupercontentsmask, skipsupercontentsmask, skipmaterialflagsmask);
		}
		else                                                      
			model->TraceBox(model, frameblend, skeleton, trace, starttransformed, mins, maxs, endtransformed, hitsupercontentsmask, skipsupercontentsmask, skipmaterialflagsmask);
	}
	else                                                                                                                                                                                        
		Collision_ClipTrace_Box(trace, bodymins, bodymaxs, starttransformed, mins, maxs, endtransformed, hitsupercontentsmask, skipsupercontentsmask, skipmaterialflagsmask, bodysupercontents, 0, NULL);

	Collision_ClipExtendFinish(&extendtraceinfo);

	                  
	                                                                    
	Matrix4x4_TransformPositivePlane(matrix, trace->plane.normal[0], trace->plane.normal[1], trace->plane.normal[2], trace->plane.dist, trace->plane.normal_and_dist);
}

void Collision_ClipToWorld(trace_t *trace, dp_model_t *model, const vec3_t tstart, const vec3_t mins, const vec3_t maxs, const vec3_t tend, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask, float extend)
{
	extendtraceinfo_t extendtraceinfo;
	Collision_ClipExtendPrepare(&extendtraceinfo, trace, tstart, tend, extend);
	                                                                         
	if (model && model->TraceBox)
		model->TraceBox(model, NULL, NULL, trace, extendtraceinfo.extendstart, mins, maxs, extendtraceinfo.extendend, hitsupercontentsmask, skipsupercontentsmask, skipmaterialflagsmask);
	Collision_ClipExtendFinish(&extendtraceinfo);
}

void Collision_ClipLineToGenericEntity(trace_t *trace, dp_model_t *model, const frameblend_t *frameblend, const skeleton_t *skeleton, const vec3_t bodymins, const vec3_t bodymaxs, int bodysupercontents, matrix4x4_t *matrix, matrix4x4_t *inversematrix, const vec3_t tstart, const vec3_t tend, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask, float extend, qboolean hitsurfaces)
{
	vec3_t starttransformed, endtransformed;
	extendtraceinfo_t extendtraceinfo;
	Collision_ClipExtendPrepare(&extendtraceinfo, trace, tstart, tend, extend);

	Matrix4x4_Transform(inversematrix, extendtraceinfo.extendstart, starttransformed);
	Matrix4x4_Transform(inversematrix, extendtraceinfo.extendend, endtransformed);
#if COLLISIONPARANOID >= 3
	Con_Printf("trans(%f %f %f -> %f %f %f, %f %f %f -> %f %f %f)", extendtraceinfo.extendstart[0], extendtraceinfo.extendstart[1], extendtraceinfo.extendstart[2], starttransformed[0], starttransformed[1], starttransformed[2], extendtraceinfo.extendend[0], extendtraceinfo.extendend[1], extendtraceinfo.extendend[2], endtransformed[0], endtransformed[1], endtransformed[2]);
#endif

	if (model && model->TraceLineAgainstSurfaces && hitsurfaces)
		model->TraceLineAgainstSurfaces(model, frameblend, skeleton, trace, starttransformed, endtransformed, hitsupercontentsmask, skipsupercontentsmask, skipmaterialflagsmask);
	else if (model && model->TraceLine)
		model->TraceLine(model, frameblend, skeleton, trace, starttransformed, endtransformed, hitsupercontentsmask, skipsupercontentsmask, skipmaterialflagsmask);
	else
		Collision_ClipTrace_Box(trace, bodymins, bodymaxs, starttransformed, vec3_origin, vec3_origin, endtransformed, hitsupercontentsmask, skipsupercontentsmask, skipmaterialflagsmask, bodysupercontents, 0, NULL);

	Collision_ClipExtendFinish(&extendtraceinfo);

	                  
	                                                                    
	Matrix4x4_TransformPositivePlane(matrix, trace->plane.normal[0], trace->plane.normal[1], trace->plane.normal[2], trace->plane.dist, trace->plane.normal_and_dist);
}

void Collision_ClipLineToWorld(trace_t *trace, dp_model_t *model, const vec3_t tstart, const vec3_t tend, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask, float extend, qboolean hitsurfaces)
{
	extendtraceinfo_t extendtraceinfo;
	Collision_ClipExtendPrepare(&extendtraceinfo, trace, tstart, tend, extend);

	if (model && model->TraceLineAgainstSurfaces && hitsurfaces)
		model->TraceLineAgainstSurfaces(model, NULL, NULL, trace, extendtraceinfo.extendstart, extendtraceinfo.extendend, hitsupercontentsmask, skipsupercontentsmask, skipmaterialflagsmask);
	else if (model && model->TraceLine)
		model->TraceLine(model, NULL, NULL, trace, extendtraceinfo.extendstart, extendtraceinfo.extendend, hitsupercontentsmask, skipsupercontentsmask, skipmaterialflagsmask);

	Collision_ClipExtendFinish(&extendtraceinfo);
}

void Collision_ClipPointToGenericEntity(trace_t *trace, dp_model_t *model, const frameblend_t *frameblend, const skeleton_t *skeleton, const vec3_t bodymins, const vec3_t bodymaxs, int bodysupercontents, matrix4x4_t *matrix, matrix4x4_t *inversematrix, const vec3_t start, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask)
{
	float starttransformed[3];
	memset(trace, 0, sizeof(*trace));
	trace->fraction = 1;

	Matrix4x4_Transform(inversematrix, start, starttransformed);
#if COLLISIONPARANOID >= 3
	Con_Printf("trans(%f %f %f -> %f %f %f)", start[0], start[1], start[2], starttransformed[0], starttransformed[1], starttransformed[2]);
#endif

	if (model && model->TracePoint)
		model->TracePoint(model, NULL, NULL, trace, starttransformed, hitsupercontentsmask, skipsupercontentsmask, skipmaterialflagsmask);
	else
		Collision_ClipTrace_Point(trace, bodymins, bodymaxs, starttransformed, hitsupercontentsmask, skipsupercontentsmask, skipmaterialflagsmask, bodysupercontents, 0, NULL);

	VectorCopy(start, trace->endpos);
	                  
	                                                                    
	Matrix4x4_TransformPositivePlane(matrix, trace->plane.normal[0], trace->plane.normal[1], trace->plane.normal[2], trace->plane.dist, trace->plane.normal_and_dist);
}

void Collision_ClipPointToWorld(trace_t *trace, dp_model_t *model, const vec3_t start, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask)
{
	memset(trace, 0, sizeof(*trace));
	trace->fraction = 1;
	if (model && model->TracePoint)
		model->TracePoint(model, NULL, NULL, trace, start, hitsupercontentsmask, skipsupercontentsmask, skipmaterialflagsmask);
	VectorCopy(start, trace->endpos);
}

void Collision_CombineTraces(trace_t *cliptrace, const trace_t *trace, void *touch, qboolean isbmodel)
{
	                                                                            
	if (trace->allsolid)
		cliptrace->allsolid = true;
	if (trace->startsolid)
	{
		if (isbmodel)
			cliptrace->bmodelstartsolid = true;
		cliptrace->startsolid = true;
		if (cliptrace->fraction == 1)
			cliptrace->ent = touch;
		if (cliptrace->startdepth > trace->startdepth)
		{
			cliptrace->startdepth = trace->startdepth;
			VectorCopy(trace->startdepthnormal, cliptrace->startdepthnormal);
		}
	}
	                                                                    
	                                                                
	                                                         
	                    
	                            
	if (trace->inwater)
		cliptrace->inwater = true;
	if ((trace->fraction < cliptrace->fraction) && (VectorLength2(trace->plane.normal) > 0))
	{
		cliptrace->fraction = trace->fraction;
		VectorCopy(trace->endpos, cliptrace->endpos);
		cliptrace->plane = trace->plane;
		cliptrace->ent = touch;
		cliptrace->hitsupercontents = trace->hitsupercontents;
		cliptrace->hitq3surfaceflags = trace->hitq3surfaceflags;
		cliptrace->hittexture = trace->hittexture;
	}
	cliptrace->startsupercontents |= trace->startsupercontents;
}
