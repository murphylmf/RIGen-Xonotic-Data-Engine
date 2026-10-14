  
                                    

                                                              
                                                            
                                                               
                                                       

                                                                
                                                               
                                                     

                                                     

                                                                  
                                           

                                
                             
                             

  

#ifndef JPEG_H
#define JPEG_H


qboolean JPEG_OpenLibrary (void);
void JPEG_CloseLibrary (void);
unsigned char* JPEG_LoadImage_BGRA (const unsigned char *f, int filesize, int *miplevel);
qboolean JPEG_SaveImage_preflipped (const char *filename, int width, int height, unsigned char *data);

                                                    
   
size_t JPEG_SaveImage_to_Buffer (char *jpegbuf, size_t jpegsize, int width, int height, unsigned char *data);
qboolean Image_Compress(const char *imagename, size_t maxsize, void **buf, size_t *size);


#endif
