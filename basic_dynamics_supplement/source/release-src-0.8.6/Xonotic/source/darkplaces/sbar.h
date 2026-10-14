  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                      

                                                    

                                                                 
                                                           
                                                                           

  

#ifndef SBAR_H
#define SBAR_H

#define	SBAR_HEIGHT		24

extern	int			sb_lines;			                       
extern	cvar_t		sbar_alpha_bg;
extern	cvar_t		sbar_alpha_fg;

void Sbar_Init (void);

                                
void Sbar_Draw (void);

int Sbar_GetSortedPlayerIndex (int index);
void Sbar_SortFrags (void);

#endif

