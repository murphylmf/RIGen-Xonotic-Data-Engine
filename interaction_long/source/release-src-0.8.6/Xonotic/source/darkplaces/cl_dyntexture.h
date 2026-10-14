                            
#ifndef CL_DYNTEXTURE_H
#define CL_DYNTEXTURE_H

#define CLDYNTEXTUREPREFIX			"_dynamic/"

                                                                                                             

                                                                                                                 
                                                  
rtexture_t * CL_GetDynTexture( const char *name );

                                                                                                             
void CL_LinkDynTexture( const char *name, rtexture_t *texture );

                                        
void CL_UnlinkDynTexture( const char *name );

#endif

