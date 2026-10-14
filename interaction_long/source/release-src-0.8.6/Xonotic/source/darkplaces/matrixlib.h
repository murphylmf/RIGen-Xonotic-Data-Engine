
#ifndef MATRIXLIB_H
#define MATRIXLIB_H

#ifndef M_PI
#define M_PI		3.14159265358979323846	                                 
#endif

                                     

typedef struct matrix4x4_s
{
	vec_t m[4][4];
}
matrix4x4_t;

extern const matrix4x4_t identitymatrix;

                                          

                   
void Matrix4x4_Copy (matrix4x4_t *out, const matrix4x4_t *in);
                                                
void Matrix4x4_CopyRotateOnly (matrix4x4_t *out, const matrix4x4_t *in);
                                                 
void Matrix4x4_CopyTranslateOnly (matrix4x4_t *out, const matrix4x4_t *in);
                                                                   
                                                                
void Matrix4x4_Concat (matrix4x4_t *out, const matrix4x4_t *in1, const matrix4x4_t *in2);
                                           
                                 
void Matrix4x4_Transpose (matrix4x4_t *out, const matrix4x4_t *in1);
                                                                 
                                                                              
                        
                                                                              
                                 
int Matrix4x4_Invert_Full (matrix4x4_t *out, const matrix4x4_t *in1);
                                                                 
                                                               
void Matrix4x4_Invert_Simple (matrix4x4_t *out, const matrix4x4_t *in1);
                                                                          
                                                                             
                                                                            
void Matrix4x4_Interpolate (matrix4x4_t *out, matrix4x4_t *in1, matrix4x4_t *in2, double frac);
                                                              
void Matrix4x4_Clear (matrix4x4_t *out);
                                                                            
                                                                              
                                                                       
                                 
void Matrix4x4_Accumulate (matrix4x4_t *out, matrix4x4_t *in, double weight);
                                                                             
                                                                     
void Matrix4x4_Normalize (matrix4x4_t *out, matrix4x4_t *in1);
                                                                   
                        
void Matrix4x4_Normalize3 (matrix4x4_t *out, matrix4x4_t *in1);
                                                                              
                                                     
void Matrix4x4_Reflect (matrix4x4_t *out, double normalx, double normaly, double normalz, double dist, double axisscale);

                             
                                
void Matrix4x4_CreateIdentity (matrix4x4_t *out);
                             
                  
void Matrix4x4_CreateTranslate (matrix4x4_t *out, double x, double y, double z);
                          
                    
void Matrix4x4_CreateRotate (matrix4x4_t *out, double angle, double x, double y, double z);
                           
                                 
                                                                   
void Matrix4x4_CreateScale (matrix4x4_t *out, double x);
                             
                                                               
                                                   
                                                                   
void Matrix4x4_CreateScale3 (matrix4x4_t *out, double x, double y, double z);
                                      
void Matrix4x4_CreateFromQuakeEntity(matrix4x4_t *out, double x, double y, double z, double pitch, double yaw, double roll, double scale);
                                                          
void Matrix4x4_QuakeToDuke3D(const matrix4x4_t *in, matrix4x4_t *out, double maxShearAngle);

                                                                                            
void Matrix4x4_ToVectors(const matrix4x4_t *in, vec_t vx[3], vec_t vy[3], vec_t vz[3], vec_t t[3]);
                                                                                   
void Matrix4x4_FromVectors(matrix4x4_t *out, const vec_t vx[3], const vec_t vy[3], const vec_t vz[3], const vec_t t[3]);

                                                                       
void Matrix4x4_ToArrayDoubleGL(const matrix4x4_t *in, double out[16]);
                                                                        
void Matrix4x4_FromArrayDoubleGL(matrix4x4_t *out, const double in[16]);
                                                                         
void Matrix4x4_ToArrayDoubleD3D(const matrix4x4_t *in, double out[16]);
                                                                          
void Matrix4x4_FromArrayDoubleD3D(matrix4x4_t *out, const double in[16]);

                                                                      
void Matrix4x4_ToArrayFloatGL(const matrix4x4_t *in, float out[16]);
                                                                       
void Matrix4x4_FromArrayFloatGL(matrix4x4_t *out, const float in[16]);
                                                                        
void Matrix4x4_ToArrayFloatD3D(const matrix4x4_t *in, float out[16]);
                                                                         
void Matrix4x4_FromArrayFloatD3D(matrix4x4_t *out, const float in[16]);

                                                                      
void Matrix4x4_ToArray12FloatGL(const matrix4x4_t *in, float out[12]);
                                                                       
void Matrix4x4_FromArray12FloatGL(matrix4x4_t *out, const float in[12]);
                                                                        
void Matrix4x4_ToArray12FloatD3D(const matrix4x4_t *in, float out[12]);
                                                                         
void Matrix4x4_FromArray12FloatD3D(matrix4x4_t *out, const float in[12]);

                                                                                                          
void Matrix4x4_FromOriginQuat(matrix4x4_t *m, double ox, double oy, double oz, double x, double y, double z, double w);
                                                                                  
void Matrix4x4_ToOrigin3Quat4Float(const matrix4x4_t *m, float *origin, float *quat);
                                                                                                                                
void Matrix4x4_FromDoom3Joint(matrix4x4_t *m, double ox, double oy, double oz, double x, double y, double z);

                                                                                                          
void Matrix4x4_FromBonePose7s(matrix4x4_t *m, float originscale, const short *pose7s);
                                                                
void Matrix4x4_ToBonePose7s(const matrix4x4_t *m, float origininvscale, short *pose7s);

                                                                                         
void Matrix4x4_Blend (matrix4x4_t *out, const matrix4x4_t *in1, const matrix4x4_t *in2, double blend);

                                             
void Matrix4x4_Transform (const matrix4x4_t *in, const vec_t v[3], vec_t out[3]);
                                             
                                                                          
                                                           
void Matrix4x4_Transform4 (const matrix4x4_t *in, const vec_t v[4], vec_t out[4]);
                                                                            
                                                                             
               
                                                                                           
                                                                      
void Matrix4x4_Transform3x3 (const matrix4x4_t *in, const vec_t v[3], vec_t out[3]);
                                                                                                  
void Matrix4x4_TransformPositivePlane (const matrix4x4_t *in, vec_t x, vec_t y, vec_t z, vec_t d, vec_t *o);
                                                                                         
void Matrix4x4_TransformStandardPlane (const matrix4x4_t *in, vec_t x, vec_t y, vec_t z, vec_t d, vec_t *o);

                        
                                                
void Matrix4x4_ConcatTranslate (matrix4x4_t *out, double x, double y, double z);
                                             
void Matrix4x4_ConcatRotate (matrix4x4_t *out, double angle, double x, double y, double z);
                                            
void Matrix4x4_ConcatScale (matrix4x4_t *out, double x);
                                             
void Matrix4x4_ConcatScale3 (matrix4x4_t *out, double x, double y, double z);

                                                 
void Matrix4x4_OriginFromMatrix (const matrix4x4_t *in, vec_t *out);
                                                                       
double Matrix4x4_ScaleFromMatrix (const matrix4x4_t *in);

                                               
void Matrix4x4_SetOrigin (matrix4x4_t *out, double x, double y, double z);
                                                                  
void Matrix4x4_AdjustOrigin (matrix4x4_t *out, double x, double y, double z);
                                                                             
void Matrix4x4_Scale (matrix4x4_t *out, double rotatescale, double originscale);
                                                                               
void Matrix4x4_Abs (matrix4x4_t *out);

#endif
