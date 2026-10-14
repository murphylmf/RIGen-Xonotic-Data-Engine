  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
                                  

#ifndef SYS_H
#define SYS_H

extern cvar_t sys_usenoclockbutbenchmark;

  
                 
  

                 
#ifdef WIN32
# include <windows.h>
typedef HMODULE dllhandle_t;

                  
#else
  typedef void* dllhandle_t;
#endif

typedef struct dllfunction_s
{
	const char *name;
	void **funcvariable;
}
dllfunction_t;

                     
                                                                                          
                
              
   
qboolean Sys_LoadLibrary (const char** dllnames, dllhandle_t* handle, const dllfunction_t *fcts);
void Sys_UnloadLibrary (dllhandle_t* handle);
void* Sys_GetProcAddress (dllhandle_t handle, const char* name);

                             
void Sys_InitConsole (void);
                                                                         
void Sys_Init_Commands (void);


                              
char *Sys_TimeString(const char *timeformat);

  
                                                                                                    
  

                                                  
void Sys_Error (const char *error, ...) DP_FUNC_PRINTF(1) DP_FUNC_NORETURN;

                                                        
void Sys_PrintToTerminal(const char *text);
void Sys_PrintfToTerminal(const char *fmt, ...);

                                                                                    
void Sys_Shutdown (void);
void Sys_Quit (int returnvalue);

                                                                       
                                                                            
                                                                             
                                                                            
   
#ifdef __cplusplus
extern "C"
#endif
void Sys_AllowProfiling (qboolean enable);

typedef struct sys_cleantime_s
{
	double dirtytime;                                          
	double cleantime;                                                      
}
sys_cleantime_t;

double Sys_DirtyTime(void);

void Sys_ProvideSelfFD (void);

char *Sys_ConsoleInput (void);

                                                                                  
void Sys_Sleep(int microseconds);

                                                               
void Sys_SendKeyEvents (void);

char *Sys_GetClipboardData (void);

extern qboolean sys_supportsdlgetticks;
unsigned int Sys_SDL_GetTicks (void);                                
void Sys_SDL_Delay (unsigned int milliseconds);                             

                                                        
void Sys_InitProcessNice (void);
void Sys_MakeProcessNice (void);
void Sys_MakeProcessMean (void);

#endif

