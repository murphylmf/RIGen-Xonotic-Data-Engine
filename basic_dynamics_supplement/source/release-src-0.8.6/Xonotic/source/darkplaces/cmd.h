  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

                                                

                                                                             

  

                                                                               
                                                                            
                                                                          

                                                                

                                                                         

  

#ifndef CMD_H
#define CMD_H

extern void *cmd_text_mutex;
#define Cbuf_LockThreadMutex() (void)(cmd_text_mutex ? Thread_LockMutex(cmd_text_mutex) : 0)
#define Cbuf_UnlockThreadMutex() (void)(cmd_text_mutex ? Thread_UnlockMutex(cmd_text_mutex) : 0)

                                                             
void Cbuf_Init (void);

void Cmd_Init_Commands (void);

void Cbuf_Shutdown (void);

                                                                  
                                                      
   
void Cbuf_AddText (const char *text);

                                                                         
                                                                           
            
   
void Cbuf_InsertText (const char *text);

                                                                        
                                                                   
                                                                 
                                               
   
void Cbuf_Execute (void);
                                                                            
void Cbuf_Frame (void);

                                                                             

  

                                                                        
                                                                     

                                                                          
                                                                         
               

  

typedef void (*xcommand_t) (void);

typedef enum
{
	src_client,		                                                     
					                                                 
	src_command		                            
} cmd_source_t;

extern cmd_source_t cmd_source;

void Cmd_Init (void);
void Cmd_Shutdown (void);

                                                                                     
void Cmd_SaveInitState (void);
                                                                                   
void Cmd_RestoreInitState (void);

void Cmd_AddCommand_WithClientCommand (const char *cmd_name, xcommand_t consolefunction, xcommand_t clientfunction, const char *description);
void Cmd_AddCommand (const char *cmd_name, xcommand_t function, const char *description);
                                                                
                                                    
                                                                       

                                                                  
qboolean Cmd_Exists (const char *cmd_name);

                                                                             
                                
const char *Cmd_CompleteCommand (const char *partial);

int Cmd_CompleteAliasCountPossible (const char *partial);

const char **Cmd_CompleteAliasBuildList (const char *partial);

int Cmd_CompleteCountPossible (const char *partial);

const char **Cmd_CompleteBuildList (const char *partial);

void Cmd_CompleteCommandPrint (const char *partial);

const char *Cmd_CompleteAlias (const char *partial);

void Cmd_CompleteAliasPrint (const char *partial);

                                                       

                                                 

int Cmd_Argc (void);
const char *Cmd_Argv (int arg);
const char *Cmd_Args (void);
                                                                      
                                                                 
                                                       

                                                                     
                                                         
int Cmd_CheckParm (const char *parm);

                                       
                                                                      
                                        

                                                                        
                                                                         
void Cmd_ExecuteString (const char *text, cmd_source_t src, qboolean lockmutex);

                                                             
                                                                       
void Cmd_ForwardStringToServer (const char *s);

                                                                           
                                                                          
                                                                             
void Cmd_ForwardToServer (void);

                                                                              
                                           
void Cmd_Print(const char *text);

                                                                       
                                                                           
                                                                          
                                                                              
                                                                       
                                       
qboolean Cmd_QuoteString(char *out, size_t outlen, const char *in, const char *quoteset, qboolean putquotes);

void Cmd_ClearCsqcFuncs (void);

#endif

