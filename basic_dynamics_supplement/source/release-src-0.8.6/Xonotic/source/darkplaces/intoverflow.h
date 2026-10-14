#ifndef INTOVERFLOW_H
#define INTOVERFLOW_H

                                                                                      
         
                                                       
                                                                    
                 
                                                                                        
                                                                                        
                                           

#define INTOVERFLOW_MAX 2147483647

#define INTOVERFLOW_ADD(a,b) (((a) < INTOVERFLOW_MAX && (b) < INTOVERFLOW_MAX && (a) < INTOVERFLOW_MAX - (b)) ? ((a) + (b)) : INTOVERFLOW_MAX)
#define INTOVERFLOW_SUB(a,b) (((a) < INTOVERFLOW_MAX && (b) < INTOVERFLOW_MAX && (b) <= (a))                  ? ((a) - (b)) : INTOVERFLOW_MAX)
#define INTOVERFLOW_MUL(a,b) (((a) < INTOVERFLOW_MAX && (b) < INTOVERFLOW_MAX && (a) < INTOVERFLOW_MAX / (b)) ? ((a) * (b)) : INTOVERFLOW_MAX)
#define INTOVERFLOW_DIV(a,b) (((a) < INTOVERFLOW_MAX && (b) < INTOVERFLOW_MAX && (b) > 0)                     ? ((a) / (b)) : INTOVERFLOW_MAX)

#define INTOVERFLOW_NORMALIZE(a) (((a) < INTOVERFLOW_MAX) ? (a) : (INTOVERFLOW_MAX - 1))

#endif
