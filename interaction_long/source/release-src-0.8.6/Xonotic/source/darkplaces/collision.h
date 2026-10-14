
#ifndef COLLISION_H
#define COLLISION_H

typedef union plane_s
{
	struct
	{
		vec3_t	normal;
		vec_t	dist;
	};
	vec4_t normal_and_dist;
}
plane_t;

struct texture_s;
typedef struct trace_s
{
	                                                                    
	int allsolid;
	                                                                     
	int startsolid;
	                                                                                
	int worldstartsolid;
	                                                                                                                                                                                                              
	int bmodelstartsolid;
	                                                    
	                              
	int inopen;
	                                                               
	                              
	int inwater;
	                                                                 
	                                                                  
	                               
	double fraction;
	                                                                     
	double endpos[3];
	                                                                    
	plane_t plane;
	                           
	                                                
	void *ent;
	                                                                   
	                                          
	int hitsupercontentsmask;
	                                                                                                                                                                            
	int skipsupercontentsmask;
	                                                                                                     
	int skipmaterialflagsmask;
	                                            
	int startsupercontents;
	                                            
	int hitsupercontents;
	                                              
	int hitq3surfaceflags;
	                                      
	const struct texture_s *hittexture;
	                                                    
	                                                     
	int startfound;
	                                                                     
	                                                            
	double startdepth;
	double startdepthnormal[3];
	const struct texture_s *starttexture;
}
trace_t;

void Collision_Init(void);
void Collision_ClipTrace_Box(trace_t *trace, const vec3_t cmins, const vec3_t cmaxs, const vec3_t start, const vec3_t mins, const vec3_t maxs, const vec3_t end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask, int boxsupercontents, int boxq3surfaceflags, const texture_t *boxtexture);
void Collision_ClipTrace_Point(trace_t *trace, const vec3_t cmins, const vec3_t cmaxs, const vec3_t start, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask, int boxsupercontents, int boxq3surfaceflags, const texture_t *boxtexture);

void Collision_Cache_Reset(qboolean resetlimits);
void Collision_Cache_Init(mempool_t *mempool);
void Collision_Cache_NewFrame(void);

typedef struct colpointf_s
{
	vec3_t v;
}
colpointf_t;

typedef struct colplanef_s
{
	const struct texture_s *texture;
	int q3surfaceflags;
	union
	{
		struct
		{
			vec3_t normal;
			vec_t dist;
		};
		vec4_t normal_and_dist;
	};
}
colplanef_t;

typedef struct colbrushf_s
{
	              
	vec3_t mins;
	vec3_t maxs;
	                                                                        
	int markframe;
	                                  
	int supercontents;
	                                              
	int numplanes;
	colplanef_t *planes;
	                                          
	int numedgedirs;
	colpointf_t *edgedirs;
	                                 
	int numpoints;
	colpointf_t *points;
	                                                                 
	int numtriangles;
	int *elements;
	                                                  
	const struct texture_s *texture;
	int q3surfaceflags;
	                                        
	int isaabb;                                         
	int hasaabbplanes;                                                             
}
colbrushf_t;

typedef struct colboxbrushf_s
{
	colpointf_t points[8];
	colpointf_t edgedirs[6];
	colplanef_t planes[6];
	colbrushf_t brush;
}
colboxbrushf_t;

void Collision_CalcPlanesForTriangleBrushFloat(colbrushf_t *brush);
colbrushf_t *Collision_NewBrushFromPlanes(mempool_t *mempool, int numoriginalplanes, const colplanef_t *originalplanes, int supercontents, int q3surfaceflags, const texture_t *texture, int hasaabbplanes);
void Collision_TraceBrushBrushFloat(trace_t *trace, const colbrushf_t *thisbrush_start, const colbrushf_t *thisbrush_end, const colbrushf_t *thatbrush_start, const colbrushf_t *thatbrush_end);
void Collision_TraceBrushTriangleMeshFloat(trace_t *trace, const colbrushf_t *thisbrush_start, const colbrushf_t *thisbrush_end, int numtriangles, const int *element3i, const float *vertex3f, int stride, float *bbox6f, int supercontents, int q3surfaceflags, const texture_t *texture, const vec3_t segmentmins, const vec3_t segmentmaxs);
void Collision_TraceLineBrushFloat(trace_t *trace, const vec3_t linestart, const vec3_t lineend, const colbrushf_t *thatbrush_start, const colbrushf_t *thatbrush_end);
void Collision_TraceLineTriangleMeshFloat(trace_t *trace, const vec3_t linestart, const vec3_t lineend, int numtriangles, const int *element3i, const float *vertex3f, int stride, float *bbox6f, int supercontents, int q3surfaceflags, const texture_t *texture, const vec3_t segmentmins, const vec3_t segmentmaxs);
void Collision_TracePointBrushFloat(trace_t *trace, const vec3_t point, const colbrushf_t *thatbrush);
qboolean Collision_PointInsideBrushFloat(const vec3_t point, const colbrushf_t *brush);

void Collision_BrushForBox(colboxbrushf_t *boxbrush, const vec3_t mins, const vec3_t maxs, int supercontents, int q3surfaceflags, const texture_t *texture);

void Collision_BoundingBoxOfBrushTraceSegment(const colbrushf_t *start, const colbrushf_t *end, vec3_t mins, vec3_t maxs, float startfrac, float endfrac);

float Collision_ClipTrace_Line_Sphere(double *linestart, double *lineend, double *sphereorigin, double sphereradius, double *impactpoint, double *impactnormal);
void Collision_TraceLineTriangleFloat(trace_t *trace, const vec3_t linestart, const vec3_t lineend, const float *point0, const float *point1, const float *point2, int supercontents, int q3surfaceflags, const texture_t *texture);
void Collision_TraceBrushTriangleFloat(trace_t *trace, const colbrushf_t *thisbrush_start, const colbrushf_t *thisbrush_end, const float *v0, const float *v1, const float *v2, int supercontents, int q3surfaceflags, const texture_t *texture);

                                            
                             
  
                                                                               
  
                                                                            
                                              
  
                                                                          
                                                                  
  
                                             
struct frameblend_s;
struct skeleton_s;
void Collision_ClipToGenericEntity(trace_t *trace, dp_model_t *model, const struct frameblend_s *frameblend, const struct skeleton_s *skeleton, const vec3_t bodymins, const vec3_t bodymaxs, int bodysupercontents, matrix4x4_t *matrix, matrix4x4_t *inversematrix, const vec3_t start, const vec3_t mins, const vec3_t maxs, const vec3_t end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask, float extend);
void Collision_ClipLineToGenericEntity(trace_t *trace, dp_model_t *model, const struct frameblend_s *frameblend, const struct skeleton_s *skeleton, const vec3_t bodymins, const vec3_t bodymaxs, int bodysupercontents, matrix4x4_t *matrix, matrix4x4_t *inversematrix, const vec3_t start, const vec3_t end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask, float extend, qboolean hitsurfaces);
void Collision_ClipPointToGenericEntity(trace_t *trace, dp_model_t *model, const struct frameblend_s *frameblend, const struct skeleton_s *skeleton, const vec3_t bodymins, const vec3_t bodymaxs, int bodysupercontents, matrix4x4_t *matrix, matrix4x4_t *inversematrix, const vec3_t start, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask);
                                                                           
void Collision_ClipToWorld(trace_t *trace, dp_model_t *model, const vec3_t start, const vec3_t mins, const vec3_t maxs, const vec3_t end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask, float extend);
void Collision_ClipLineToWorld(trace_t *trace, dp_model_t *model, const vec3_t start, const vec3_t end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask, float extend, qboolean hitsurfaces);
void Collision_ClipPointToWorld(trace_t *trace, dp_model_t *model, const vec3_t start, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask);
                                                       
void Collision_Cache_ClipLineToGenericEntitySurfaces(trace_t *trace, dp_model_t *model, matrix4x4_t *matrix, matrix4x4_t *inversematrix, const vec3_t start, const vec3_t end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask);
void Collision_Cache_ClipLineToWorldSurfaces(trace_t *trace, dp_model_t *model, const vec3_t start, const vec3_t end, int hitsupercontentsmask, int skipsupercontentsmask, int skipmaterialflagsmask);
                                 
                                                       
                                                                              
void Collision_CombineTraces(trace_t *cliptrace, const trace_t *trace, void *touch, qboolean isbmodel);

                                            
            
              
                                                     
                              
                                                         
#define COLLISIONPARANOID 0

extern cvar_t collision_impactnudge;
extern cvar_t collision_extendtracelinelength;
extern cvar_t collision_extendtraceboxlength;
extern cvar_t collision_extendmovelength;
extern cvar_t collision_bih_fullrecursion;

#endif
