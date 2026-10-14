  
                                           

                                                              
                                                            
                                                               
                                                       

                                                                
                                                               
                                                     

                                                     

                                                                  
                                           

                                
                             
                             

  

#ifndef PNG_H
#define PNG_H

qboolean PNG_OpenLibrary (void);
void PNG_CloseLibrary (void);
unsigned char* PNG_LoadImage_BGRA (const unsigned char *f, int filesize, int *miplevel);
qboolean PNG_SaveImage_preflipped (const char *filename, int width, int height, qboolean has_alpha, unsigned char *data);

#endif

