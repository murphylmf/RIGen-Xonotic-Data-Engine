
#ifndef DPVSIMPLEDECODE_H
#define DPVSIMPLEDECODE_H

#include "cl_video.h"

#define DPVSIMPLEDECODEERROR_NONE 0
#define DPVSIMPLEDECODEERROR_EOF 1
#define DPVSIMPLEDECODEERROR_READERROR 2
#define DPVSIMPLEDECODEERROR_SOUNDBUFFERTOOSMALL 3
#define DPVSIMPLEDECODEERROR_INVALIDRMASK 4
#define DPVSIMPLEDECODEERROR_INVALIDGMASK 5
#define DPVSIMPLEDECODEERROR_INVALIDBMASK 6
#define DPVSIMPLEDECODEERROR_COLORMASKSOVERLAP 7
#define DPVSIMPLEDECODEERROR_COLORMASKSEXCEEDBPP 8
#define DPVSIMPLEDECODEERROR_UNSUPPORTEDBPP 9

                              

                 
void *dpvsimpledecode_open(clvideo_t *video, char *filename, const char **errorstring);

                  
void dpvsimpledecode_close(void *stream);

                        

                                                                        
                                
                                                                             
                
int dpvsimpledecode_error(void *stream, const char **errorstring);

                                      
unsigned int dpvsimpledecode_getwidth(void *stream);

                                       
unsigned int dpvsimpledecode_getheight(void *stream);

                                      
double dpvsimpledecode_getframerate(void *stream);

                                     
double dpvsimpledecode_getaspectratio(void *stream);

                                                      
int dpvsimpledecode_video(void *stream, void *imagedata, unsigned int Rmask, unsigned int Gmask, unsigned int Bmask, unsigned int bytesperpixel, int imagebytesperrow);

#endif
