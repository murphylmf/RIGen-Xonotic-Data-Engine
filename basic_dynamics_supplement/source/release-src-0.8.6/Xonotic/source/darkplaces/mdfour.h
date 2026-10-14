  
         

                                                                    
         

                                        

                                                              
                                                            
                                                               
                                                       

                                                                
                                                               
                                                     

                                                     

                                                                  
                                           

                                
                             
                             
  

#ifndef _MDFOUR_H
#define _MDFOUR_H

#ifndef int32
#define int32 int
#endif

#if SIZEOF_INT > 4
#define LARGE_INT32
#endif

#ifndef uint32
#define uint32 unsigned int32
#endif

struct mdfour {
	uint32 A, B, C, D;
	uint32 totalN;
};

void mdfour_begin(struct mdfour *md);                
void mdfour_update(struct mdfour *md, const unsigned char *in, int n);                 
void mdfour_result(struct mdfour *md, unsigned char *out);                 
void mdfour(unsigned char *out, const unsigned char *in, int n);

#endif	            

