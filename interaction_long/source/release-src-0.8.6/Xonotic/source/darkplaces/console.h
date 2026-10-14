  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

#ifndef CONSOLE_H
#define CONSOLE_H

  
          
  
extern int con_totallines;
extern int con_backscroll;
extern qboolean con_initialized;

void Con_Rcon_Redirect_Init(lhnetsocket_t *sock, lhnetaddress_t *dest, qboolean proquakeprotocol);
void Con_Rcon_Redirect_End(void);
void Con_Rcon_Redirect_Abort(void);

                                                       
void Con_CheckResize (void);
void Con_Init (void);
void Con_Init_Commands (void);
void Con_Shutdown (void);
void Con_DrawConsole (int lines);

                                     
void Con_MaskPrint(int mask, const char *msg);

                                    
void Con_MaskPrintf(int mask, const char *fmt, ...) DP_FUNC_PRINTF(2);

                                                                  
void Con_Print(const char *txt);

                                              
void Con_Printf(const char *fmt, ...) DP_FUNC_PRINTF(1);

                                                                  
void Con_DPrint(const char *msg);

                                                                  
void Con_DPrintf(const char *fmt, ...) DP_FUNC_PRINTF(1);
void Con_Clear_f (void);
void Con_DrawNotify (void);

                           
void Con_ClearNotify (void);
void Con_ToggleConsole_f (void);

int Nicks_CompleteChatLine(char *buffer, size_t size, unsigned int pos);

qboolean GetMapList (const char *s, char *completedname, int completednamebufferlength);

                                                                   
                                               
                                                            
                                         
void Con_CompleteCommandLine(void);

                                                          
                                       
void Con_DisplayList(const char **list);


             
     
   
void Log_Init (void);
void Log_Close (void);
void Log_Start (void);
void Log_DestBuffer_Flush (void);                                                                            

void Log_Printf(const char *logfilename, const char *fmt, ...) DP_FUNC_PRINTF(2);
    

                                                       
                                                       
#define CON_MASK_HIDENOTIFY 128
#define CON_MASK_CHAT 1
#define CON_MASK_INPUT 2
#define CON_MASK_DEVELOPER 4
#define CON_MASK_PRINT 8

typedef struct con_lineinfo_s
{
	char *start;
	size_t len;
	int mask;

	                          
	double addtime;
	int height;                                                        
}
con_lineinfo_t;

typedef struct conbuffer_s
{
	qboolean active;
	int textsize;
	char *text;
	int maxlines;
	con_lineinfo_t *lines;
	int lines_first;
	int lines_count;                   
}
conbuffer_t;

#define CONBUFFER_LINES(buf, i) (buf)->lines[((buf)->lines_first + (i)) % (buf)->maxlines]
#define CONBUFFER_LINES_COUNT(buf) ((buf)->lines_count)
#define CONBUFFER_LINES_LAST(buf) CONBUFFER_LINES(buf, CONBUFFER_LINES_COUNT(buf) - 1)

void ConBuffer_Init(conbuffer_t *buf, int textsize, int maxlines, mempool_t *mempool);
void ConBuffer_Clear (conbuffer_t *buf);
void ConBuffer_Shutdown(conbuffer_t *buf);

                                                    
                                                        
                  
   
void ConBuffer_FixTimes(conbuffer_t *buf);

                                                    
void ConBuffer_DeleteLine(conbuffer_t *buf);

                                                   
void ConBuffer_DeleteLastLine(conbuffer_t *buf);

                                                        
void ConBuffer_AddLine(conbuffer_t *buf, const char *line, int len, int mask);
int ConBuffer_FindPrevLine(conbuffer_t *buf, int mask_must, int mask_mustnot, int start);
int ConBuffer_FindNextLine(conbuffer_t *buf, int mask_must, int mask_mustnot, int start);
const char *ConBuffer_GetLine(conbuffer_t *buf, int i);

#endif

