  
             
                                                
   
                                    
                       
  
                                                                     
                                                                     
           
                                                                    
                                                                   
                                                                       
                                                                         
                                                                          
                                                                            
                                                                           
                                                
   
                                                                           
                                                                        
                                                                             
                                                                            
                                                                             
                                                                          
                                                                        
                                                                             
                                                                            
                                                                         
               
  
                     
                                                  
   

#ifndef __D0_H__
#define __D0_H__

#include <unistd.h>          

#define D0_EXPORT __attribute__((__visibility__("default")))
#define D0_USED __attribute__((used))
#define D0_WARN_UNUSED_RESULT __attribute__((warn_unused_result))
#define D0_BOOL int

typedef void *(d0_malloc_t)(size_t len);
typedef void (d0_free_t)(void *p);
typedef void *(d0_createmutex_t)(void);
typedef void (d0_destroymutex_t)(void *);
typedef int (d0_lockmutex_t)(void *);                   
typedef int (d0_unlockmutex_t)(void *);                   

extern d0_malloc_t *d0_malloc;
extern d0_free_t *d0_free;
extern d0_createmutex_t *d0_createmutex;
extern d0_destroymutex_t *d0_destroymutex;
extern d0_lockmutex_t *d0_lockmutex;
extern d0_unlockmutex_t *d0_unlockmutex;

void d0_setmallocfuncs(d0_malloc_t *m, d0_free_t *f);
void d0_setmutexfuncs(d0_createmutex_t *c, d0_destroymutex_t *d, d0_lockmutex_t *l, d0_unlockmutex_t *u);
void d0_initfuncs(void);                                                                  

extern const char *d0_bsd_license_notice;

#endif
