  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                      

                                                    

                                                                 
                                                           
                                                                           

  
            

#ifndef CONPROC_H
#define CONPROC_H

#define CCOM_WRITE_TEXT		0x2
                

#define CCOM_GET_TEXT		0x3
                      
                    

#define CCOM_GET_SCR_LINES	0x4
            

#define CCOM_SET_SCR_LINES	0x5
                           

void InitConProc (HANDLE hFile, HANDLE heventParent, HANDLE heventChild);
void DeinitConProc (void);

#endif

