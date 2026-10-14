  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
            

#ifndef MATHLIB_H
#define MATHLIB_H

#include "qtypes.h"

#ifndef M_PI
#define M_PI		3.14159265358979323846	                                 
#endif

struct mplane_s;
extern vec3_t vec3_origin;

#define float_nanmask (0x7F800000)
#define double_nanmask (0x7FF8000000000000)
#define FLOAT_IS_NAN(x) (((*(int *)&x)&float_nanmask)==float_nanmask)
#define DOUBLE_IS_NAN(x) (((*(long long *)&x)&double_nanmask)==double_nanmask)

#ifdef VEC_64
#define VEC_IS_NAN(x) DOUBLE_IS_NAN(x)
#else
#define VEC_IS_NAN(x) FLOAT_IS_NAN(x)
#endif

#ifdef PRVM_64
#define PRVM_IS_NAN(x) DOUBLE_IS_NAN(x)
#else
#define PRVM_IS_NAN(x) FLOAT_IS_NAN(x)
#endif

#define bound(min,num,max) ((num) >= (min) ? ((num) < (max) ? (num) : (max)) : (min))

#ifndef min
#define min(A,B) ((A) < (B) ? (A) : (B))
#define max(A,B) ((A) > (B) ? (A) : (B))
#endif

                                                                              
                                         
                                                    
                                                                           
                                                                            
                                                                           
                                                                   
#define lhrandom(MIN,MAX) (((double)(rand() + 0.5) / ((double)RAND_MAX + 1)) * ((MAX)-(MIN)) + (MIN))

#define invpow(base,number) (log(number) / log(base))

                             
                                       
#define log2i(n) ((((n) & 0xAAAAAAAA) != 0 ? 1 : 0) | (((n) & 0xCCCCCCCC) != 0 ? 2 : 0) | (((n) & 0xF0F0F0F0) != 0 ? 4 : 0) | (((n) & 0xFF00FF00) != 0 ? 8 : 0) | (((n) & 0xFFFF0000) != 0 ? 16 : 0))

                                                
#define bit2i(n) log2i((n) << 1)

                                                                      
#define boolxor(a,b) (!(a) != !(b))

                                                                                             
unsigned int CeilPowerOf2(unsigned int value);

#define DEG2RAD(a) ((a) * ((float) M_PI / 180.0f))
#define RAD2DEG(a) ((a) * (180.0f / (float) M_PI))
#define ANGLEMOD(a) ((a) - 360.0 * floor((a) / 360.0))

#define DotProduct2(a,b) ((a)[0]*(b)[0]+(a)[1]*(b)[1])
#define Vector2Clear(a) ((a)[0]=(a)[1]=0)
#define Vector2Compare(a,b) (((a)[0]==(b)[0])&&((a)[1]==(b)[1]))
#define Vector2Copy(a,b) ((b)[0]=(a)[0],(b)[1]=(a)[1])
#define Vector2Negate(a,b) ((b)[0]=-((a)[0]),(b)[1]=-((a)[1]))
#define Vector2Set(a,b,c) ((a)[0]=(b),(a)[1]=(c))
#define Vector2Scale(in, scale, out) ((out)[0] = (in)[0] * (scale),(out)[1] = (in)[1] * (scale))
#define Vector2Normalize2(v,dest) {float ilength = (float) sqrt(DotProduct2((v),(v)));if (ilength) ilength = 1.0f / ilength;dest[0] = (v)[0] * ilength;dest[1] = (v)[1] * ilength;}

#define DotProduct4(a,b) ((a)[0]*(b)[0]+(a)[1]*(b)[1]+(a)[2]*(b)[2]+(a)[3]*(b)[3])
#define Vector4Clear(a) ((a)[0]=(a)[1]=(a)[2]=(a)[3]=0)
#define Vector4Compare(a,b) (((a)[0]==(b)[0])&&((a)[1]==(b)[1])&&((a)[2]==(b)[2])&&((a)[3]==(b)[3]))
#define Vector4Copy(a,b) ((b)[0]=(a)[0],(b)[1]=(a)[1],(b)[2]=(a)[2],(b)[3]=(a)[3])
#define Vector4Negate(a,b) ((b)[0]=-((a)[0]),(b)[1]=-((a)[1]),(b)[2]=-((a)[2]),(b)[3]=-((a)[3]))
#define Vector4Set(a,b,c,d,e) ((a)[0]=(b),(a)[1]=(c),(a)[2]=(d),(a)[3]=(e))
#define Vector4Normalize2(v,dest) {float ilength = (float) sqrt(DotProduct4((v),(v)));if (ilength) ilength = 1.0f / ilength;dest[0] = (v)[0] * ilength;dest[1] = (v)[1] * ilength;dest[2] = (v)[2] * ilength;dest[3] = (v)[3] * ilength;}
#define Vector4Subtract(a,b,c) ((c)[0]=(a)[0]-(b)[0],(c)[1]=(a)[1]-(b)[1],(c)[2]=(a)[2]-(b)[2],(c)[3]=(a)[3]-(b)[3])
#define Vector4Add(a,b,c) ((c)[0]=(a)[0]+(b)[0],(c)[1]=(a)[1]+(b)[1],(c)[2]=(a)[2]+(b)[2],(c)[3]=(a)[3]+(b)[3])
#define Vector4Scale(in, scale, out) ((out)[0] = (in)[0] * (scale),(out)[1] = (in)[1] * (scale),(out)[2] = (in)[2] * (scale),(out)[3] = (in)[3] * (scale))
#define Vector4Multiply(a,b,c) ((c)[0]=(a)[0]*(b)[0],(c)[1]=(a)[1]*(b)[1],(c)[2]=(a)[2]*(b)[2],(c)[3]=(a)[3]*(b)[3])
#define Vector4MA(a, scale, b, c) ((c)[0] = (a)[0] + (scale) * (b)[0],(c)[1] = (a)[1] + (scale) * (b)[1],(c)[2] = (a)[2] + (scale) * (b)[2],(c)[3] = (a)[3] + (scale) * (b)[3])
#define Vector4Lerp(v1,lerp,v2,c) ((c)[0] = (v1)[0] + (lerp) * ((v2)[0] - (v1)[0]), (c)[1] = (v1)[1] + (lerp) * ((v2)[1] - (v1)[1]), (c)[2] = (v1)[2] + (lerp) * ((v2)[2] - (v1)[2]), (c)[3] = (v1)[3] + (lerp) * ((v2)[3] - (v1)[3]))

#define VectorNegate(a,b) ((b)[0]=-((a)[0]),(b)[1]=-((a)[1]),(b)[2]=-((a)[2]))
#define VectorSet(a,b,c,d) ((a)[0]=(b),(a)[1]=(c),(a)[2]=(d))
#define VectorClear(a) ((a)[0]=(a)[1]=(a)[2]=0)
#define DotProduct(a,b) ((a)[0]*(b)[0]+(a)[1]*(b)[1]+(a)[2]*(b)[2])
#define VectorSubtract(a,b,c) ((c)[0]=(a)[0]-(b)[0],(c)[1]=(a)[1]-(b)[1],(c)[2]=(a)[2]-(b)[2])
#define VectorAdd(a,b,c) ((c)[0]=(a)[0]+(b)[0],(c)[1]=(a)[1]+(b)[1],(c)[2]=(a)[2]+(b)[2])
#define VectorCopy(a,b) ((b)[0]=(a)[0],(b)[1]=(a)[1],(b)[2]=(a)[2])
#define VectorMultiply(a,b,c) ((c)[0]=(a)[0]*(b)[0],(c)[1]=(a)[1]*(b)[1],(c)[2]=(a)[2]*(b)[2])
#define CrossProduct(a,b,c) ((c)[0]=(a)[1]*(b)[2]-(a)[2]*(b)[1],(c)[1]=(a)[2]*(b)[0]-(a)[0]*(b)[2],(c)[2]=(a)[0]*(b)[1]-(a)[1]*(b)[0])
#define VectorNormalize(v) {float ilength = (float) sqrt(DotProduct((v),(v)));if (ilength) ilength = 1.0f / ilength;(v)[0] *= ilength;(v)[1] *= ilength;(v)[2] *= ilength;}
#define VectorNormalize2(v,dest) {float ilength = (float) sqrt(DotProduct((v),(v)));if (ilength) ilength = 1.0f / ilength;dest[0] = (v)[0] * ilength;dest[1] = (v)[1] * ilength;dest[2] = (v)[2] * ilength;}
#define VectorNormalizeDouble(v) {double ilength = sqrt(DotProduct((v),(v)));if (ilength) ilength = 1.0 / ilength;(v)[0] *= ilength;(v)[1] *= ilength;(v)[2] *= ilength;}
#define VectorDistance2(a, b) (((a)[0] - (b)[0]) * ((a)[0] - (b)[0]) + ((a)[1] - (b)[1]) * ((a)[1] - (b)[1]) + ((a)[2] - (b)[2]) * ((a)[2] - (b)[2]))
#define VectorDistance(a, b) (sqrt(VectorDistance2(a,b)))
#define VectorLength(a) (sqrt((double)DotProduct(a, a)))
#define VectorLength2(a) (DotProduct(a, a))
#define VectorScale(in, scale, out) ((out)[0] = (in)[0] * (scale),(out)[1] = (in)[1] * (scale),(out)[2] = (in)[2] * (scale))
#define VectorScaleCast(in, scale, outtype, out) ((out)[0] = (outtype) ((in)[0] * (scale)),(out)[1] = (outtype) ((in)[1] * (scale)),(out)[2] = (outtype) ((in)[2] * (scale)))
#define VectorCompare(a,b) (((a)[0]==(b)[0])&&((a)[1]==(b)[1])&&((a)[2]==(b)[2]))
#define VectorMA(a, scale, b, c) ((c)[0] = (a)[0] + (scale) * (b)[0],(c)[1] = (a)[1] + (scale) * (b)[1],(c)[2] = (a)[2] + (scale) * (b)[2])
#define VectorM(scale1, b1, c) ((c)[0] = (scale1) * (b1)[0],(c)[1] = (scale1) * (b1)[1],(c)[2] = (scale1) * (b1)[2])
#define VectorMAM(scale1, b1, scale2, b2, c) ((c)[0] = (scale1) * (b1)[0] + (scale2) * (b2)[0],(c)[1] = (scale1) * (b1)[1] + (scale2) * (b2)[1],(c)[2] = (scale1) * (b1)[2] + (scale2) * (b2)[2])
#define VectorMAMAM(scale1, b1, scale2, b2, scale3, b3, c) ((c)[0] = (scale1) * (b1)[0] + (scale2) * (b2)[0] + (scale3) * (b3)[0],(c)[1] = (scale1) * (b1)[1] + (scale2) * (b2)[1] + (scale3) * (b3)[1],(c)[2] = (scale1) * (b1)[2] + (scale2) * (b2)[2] + (scale3) * (b3)[2])
#define VectorMAMAMAM(scale1, b1, scale2, b2, scale3, b3, scale4, b4, c) ((c)[0] = (scale1) * (b1)[0] + (scale2) * (b2)[0] + (scale3) * (b3)[0] + (scale4) * (b4)[0],(c)[1] = (scale1) * (b1)[1] + (scale2) * (b2)[1] + (scale3) * (b3)[1] + (scale4) * (b4)[1],(c)[2] = (scale1) * (b1)[2] + (scale2) * (b2)[2] + (scale3) * (b3)[2] + (scale4) * (b4)[2])
#define VectorRandom(v) do{(v)[0] = lhrandom(-1, 1);(v)[1] = lhrandom(-1, 1);(v)[2] = lhrandom(-1, 1);}while(DotProduct(v, v) > 1)
#define VectorLerp(v1,lerp,v2,c) ((c)[0] = (v1)[0] + (lerp) * ((v2)[0] - (v1)[0]), (c)[1] = (v1)[1] + (lerp) * ((v2)[1] - (v1)[1]), (c)[2] = (v1)[2] + (lerp) * ((v2)[2] - (v1)[2]))
#define VectorReflect(a,r,b,c) do{double d;d = DotProduct((a), (b)) * -(1.0 + (r));VectorMA((a), (d), (b), (c));}while(0)
#define BoxesOverlap(a,b,c,d) ((a)[0] <= (d)[0] && (b)[0] >= (c)[0] && (a)[1] <= (d)[1] && (b)[1] >= (c)[1] && (a)[2] <= (d)[2] && (b)[2] >= (c)[2])
#define BoxInsideBox(a,b,c,d) ((a)[0] >= (c)[0] && (b)[0] <= (d)[0] && (a)[1] >= (c)[1] && (b)[1] <= (d)[1] && (a)[2] >= (c)[2] && (b)[2] <= (d)[2])
#define TriangleBBoxOverlapsBox(a,b,c,d,e) (min((a)[0], min((b)[0], (c)[0])) < (e)[0] && max((a)[0], max((b)[0], (c)[0])) > (d)[0] && min((a)[1], min((b)[1], (c)[1])) < (e)[1] && max((a)[1], max((b)[1], (c)[1])) > (d)[1] && min((a)[2], min((b)[2], (c)[2])) < (e)[2] && max((a)[2], max((b)[2], (c)[2])) > (d)[2])

#define TriangleNormal(a,b,c,n) ( \
	(n)[0] = ((a)[1] - (b)[1]) * ((c)[2] - (b)[2]) - ((a)[2] - (b)[2]) * ((c)[1] - (b)[1]), \
	(n)[1] = ((a)[2] - (b)[2]) * ((c)[0] - (b)[0]) - ((a)[0] - (b)[0]) * ((c)[2] - (b)[2]), \
	(n)[2] = ((a)[0] - (b)[0]) * ((c)[1] - (b)[1]) - ((a)[1] - (b)[1]) * ((c)[0] - (b)[0]) \
	)

                                
                                                                             
                                                                      
                                                                        
                                                                            
                                                                       
                                                                         
                                                                            
                                        
                                     
   
#define PointInfrontOfTriangle(p,a,b,c) \
( ((p)[0] - (a)[0]) * (((a)[1] - (b)[1]) * ((c)[2] - (b)[2]) - ((a)[2] - (b)[2]) * ((c)[1] - (b)[1])) \
+ ((p)[1] - (a)[1]) * (((a)[2] - (b)[2]) * ((c)[0] - (b)[0]) - ((a)[0] - (b)[0]) * ((c)[2] - (b)[2])) \
+ ((p)[2] - (a)[2]) * (((a)[0] - (b)[0]) * ((c)[1] - (b)[1]) - ((a)[1] - (b)[1]) * ((c)[0] - (b)[0])) > 0)

#if 0
                                                      
int PointInfrontOfTriangle(const float *p, const float *a, const float *b, const float *c)
{
	float dir0[3], dir1[3], normal[3];

	                                                     
	VectorSubtract(a, b, dir0);
	VectorSubtract(c, b, dir1);

	                                                                    
	                                                                    
	                    
	CrossProduct(dir0, dir1, normal);

	                                                                     
	                                                                 
	                                                 
	return DotProduct(p, normal) > DotProduct(a, normal);
}
#endif

#define lhcheeserand(seed) ((seed) = ((seed) * 987211u) ^ ((seed) >> 13u) ^ 914867)
#define lhcheeserandom(seed,MIN,MAX) ((double)(lhcheeserand(seed) + 0.5) / ((double)4096.0*1024.0*1024.0) * ((MAX)-(MIN)) + (MIN))
#define VectorCheeseRandom(seed,v) do{(v)[0] = lhcheeserandom(seed,-1, 1);(v)[1] = lhcheeserandom(seed,-1, 1);(v)[2] = lhcheeserandom(seed,-1, 1);}while(DotProduct(v, v) > 1)
#define VectorLehmerRandom(seed,v) do{(v)[0] = Math_crandomf(seed);(v)[1] = Math_crandomf(seed);(v)[2] = Math_crandomf(seed);}while(DotProduct(v, v) > 1)

  
                                                                         
                                          
                                                                                               
                                                                                         

                               
                                                                                       
                                       
                                                                          
                                                                     
                            
  
            
  
                                      
                                      
                                      
                     
  
     
  
                                     
                             
                           
                           
                           
                          
  
 
                                                                     
                                                             
                      
                                                                                
                                                                                                                  
                                                                                                             
                                                                                           
                                                             
                                                                                                                    
                                                             
                                                                                                                                             
                                                                                                                                                                  
                                                                                                                                                     
  

#define VectorCopy4(a,b) {(b)[0]=(a)[0];(b)[1]=(a)[1];(b)[2]=(a)[2];(b)[3]=(a)[3];}

vec_t Length (vec3_t v);

                         
float VectorNormalizeLength (vec3_t v);

                         
float VectorNormalizeLength2 (vec3_t v, vec3_t dest);

#define NUMVERTEXNORMALS	162
extern float m_bytenormals[NUMVERTEXNORMALS][3];

unsigned char NormalToByte(const vec3_t n);
void ByteToNormal(unsigned char num, vec3_t n);

void R_ConcatRotations (const float in1[3*3], const float in2[3*3], float out[3*3]);
void R_ConcatTransforms (const float in1[3*4], const float in2[3*4], float out[3*4]);

void AngleVectors (const vec3_t angles, vec3_t forward, vec3_t right, vec3_t up);
                                                    
void AngleVectorsFLU (const vec3_t angles, vec3_t forward, vec3_t left, vec3_t up);
                                                      
void AngleVectorsDuke3DFLU (const vec3_t angles, vec3_t forward, vec3_t left, vec3_t up, double maxShearAngle);
                                     
void AngleMatrix (const vec3_t angles, const vec3_t translate, vec_t matrix[][4]);
                                                                           
void AnglesFromVectors (vec3_t angles, const vec3_t forward, const vec3_t up, qboolean flippitch);

                                                                                        
void VectorVectors(const vec3_t forward, vec3_t right, vec3_t up);
void VectorVectorsDouble(const double *forward, double *right, double *up);

void PlaneClassify(struct mplane_s *p);
int BoxOnPlaneSide(const vec3_t emins, const vec3_t emaxs, const struct mplane_s *p);
int BoxOnPlaneSide_Separate(const vec3_t emins, const vec3_t emaxs, const vec3_t normal, const vec_t dist);
void BoxPlaneCorners(const vec3_t emins, const vec3_t emaxs, const struct mplane_s *p, vec3_t outnear, vec3_t outfar);
void BoxPlaneCorners_Separate(const vec3_t emins, const vec3_t emaxs, const vec3_t normal, vec3_t outnear, vec3_t outfar);
void BoxPlaneCornerDistances(const vec3_t emins, const vec3_t emaxs, const struct mplane_s *p, vec_t *outnear, vec_t *outfar);
void BoxPlaneCornerDistances_Separate(const vec3_t emins, const vec3_t emaxs, const vec3_t normal, vec_t *outnear, vec_t *outfar);

#define PlaneDist(point,plane)  ((plane)->type < 3 ? (point)[(plane)->type] : DotProduct((point), (plane)->normal))
#define PlaneDiff(point,plane) (((plane)->type < 3 ? (point)[(plane)->type] : DotProduct((point), (plane)->normal)) - (plane)->dist)

                                      
typedef struct tinyplane_s
{
	float normal[3], dist;
}
tinyplane_t;

typedef struct tinydoubleplane_s
{
	double normal[3], dist;
}
tinydoubleplane_t;

void RotatePointAroundVector(vec3_t dst, const vec3_t dir, const vec3_t point, float degrees);

float RadiusFromBounds (const vec3_t mins, const vec3_t maxs);
float RadiusFromBoundsAndOrigin (const vec3_t mins, const vec3_t maxs, const vec3_t origin);

struct matrix4x4_s;
                                 
void Matrix4x4_Print(const struct matrix4x4_s *in);
int Math_atov(const char *s, prvm_vec3_t out);

void BoxFromPoints(vec3_t mins, vec3_t maxs, int numpoints, vec_t *point3f);

int LoopingFrameNumberFromDouble(double t, int loopframes);

                                                                            
                                                          
typedef struct randomseed_s
{
	unsigned int s[4];
}
randomseed_t;

void Math_RandomSeed_Reset(randomseed_t *r);
void Math_RandomSeed_FromInts(randomseed_t *r, unsigned int s0, unsigned int s1, unsigned int s2, unsigned int s3);
unsigned long long Math_rand64(randomseed_t *r);
float Math_randomf(randomseed_t *r);
float Math_crandomf(randomseed_t *r);
float Math_randomrangef(randomseed_t *r, float minf, float maxf);
int Math_randomrangei(randomseed_t *r, int mini, int maxi);

void Mathlib_Init(void);

#endif

