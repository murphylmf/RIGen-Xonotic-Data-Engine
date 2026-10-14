  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

#ifndef COMMON_H
#define COMMON_H


                                                            
#ifdef WIN32
# define strcasecmp _stricmp
# define strncasecmp _strnicmp
#endif

                                     
#if defined(__APPLE__) && defined(__MACH__)
# define MACOSX
#endif

#ifdef SUNOS
#include <sys/file.h>		                       
#endif

                                                                              

typedef struct sizebuf_s
{
	qboolean	allowoverflow;	                             
	qboolean	overflowed;		                                          
	unsigned char		*data;
	int			maxsize;
	int			cursize;
	int			readcount;
	qboolean	badread;		                                           
} sizebuf_t;

void SZ_Clear (sizebuf_t *buf);
unsigned char *SZ_GetSpace (sizebuf_t *buf, int length);
void SZ_Write (sizebuf_t *buf, const unsigned char *data, int length);
void SZ_HexDumpToConsole(const sizebuf_t *buf);

void Com_HexDumpToConsole(const unsigned char *data, int size);

unsigned short CRC_Block(const unsigned char *data, size_t size);
unsigned short CRC_Block_CaseInsensitive(const unsigned char *data, size_t size);                                                                

unsigned char COM_BlockSequenceCRCByteQW(unsigned char *base, int length, int sequence);

                                       
unsigned Com_BlockChecksum (void *buffer, int length);
void Com_BlockFullChecksum (void *buffer, int len, unsigned char *outbuf);

void COM_Init_Commands(void);


                                                                              
                           
                                                                              

                                                                

                               
     
   

                                                                            
#define BigShort(l) BuffBigShort((unsigned char *)&(l))
#define LittleShort(l) BuffLittleShort((unsigned char *)&(l))
#define BigLong(l) BuffBigLong((unsigned char *)&(l))
#define LittleLong(l) BuffLittleLong((unsigned char *)&(l))
#define BigFloat(l) BuffBigFloat((unsigned char *)&(l))
#define LittleFloat(l) BuffLittleFloat((unsigned char *)&(l))

                                                              
float BuffBigFloat (const unsigned char *buffer);

                                                            
int BuffBigLong (const unsigned char *buffer);

                                                              
short BuffBigShort (const unsigned char *buffer);

                                                                 
float BuffLittleFloat (const unsigned char *buffer);

                                                               
int BuffLittleLong (const unsigned char *buffer);

                                                                 
short BuffLittleShort (const unsigned char *buffer);

                                                        
void StoreBigLong (unsigned char *buffer, unsigned int i);

                                                        
void StoreBigShort (unsigned char *buffer, unsigned short i);

                                                           
void StoreLittleLong (unsigned char *buffer, unsigned int i);

                                                           
void StoreLittleShort (unsigned char *buffer, unsigned short i);
    

                                                                              

                                                                             
                                                                    
typedef enum protocolversion_e
{
	PROTOCOL_UNKNOWN,
	PROTOCOL_DARKPLACES7,                                                                                  
	PROTOCOL_DARKPLACES6,                     
	PROTOCOL_DARKPLACES5,                                                                                                                                                         
	PROTOCOL_DARKPLACES4,                     
	PROTOCOL_DARKPLACES3,                                                                                                                                                                                            
	PROTOCOL_DARKPLACES2,                     
	PROTOCOL_DARKPLACES1,                                                                                                                          
	PROTOCOL_QUAKEDP,                                                                                                                                       
	PROTOCOL_NEHAHRAMOVIE,                                                                                                                                                                                                                                                                                                                                                 
	PROTOCOL_QUAKE,                                                  
	PROTOCOL_QUAKEWORLD,                         
	PROTOCOL_NEHAHRABJP,                                               
	PROTOCOL_NEHAHRABJP2,                                                  
	PROTOCOL_NEHAHRABJP3                                               
}
protocolversion_t;

                               
                                                    
     
   

void MSG_InitReadBuffer (sizebuf_t *buf, unsigned char *data, int size);
void MSG_WriteChar (sizebuf_t *sb, int c);
void MSG_WriteByte (sizebuf_t *sb, int c);
void MSG_WriteShort (sizebuf_t *sb, int c);
void MSG_WriteLong (sizebuf_t *sb, int c);
void MSG_WriteFloat (sizebuf_t *sb, vec_t f);
void MSG_WriteString (sizebuf_t *sb, const char *s);
void MSG_WriteUnterminatedString (sizebuf_t *sb, const char *s);
void MSG_WriteAngle8i (sizebuf_t *sb, vec_t f);
void MSG_WriteAngle16i (sizebuf_t *sb, vec_t f);
void MSG_WriteAngle32f (sizebuf_t *sb, vec_t f);
void MSG_WriteCoord13i (sizebuf_t *sb, vec_t f);
void MSG_WriteCoord16i (sizebuf_t *sb, vec_t f);
void MSG_WriteCoord32f (sizebuf_t *sb, vec_t f);
void MSG_WriteCoord (sizebuf_t *sb, vec_t f, protocolversion_t protocol);
void MSG_WriteVector (sizebuf_t *sb, const vec3_t v, protocolversion_t protocol);
void MSG_WriteAngle (sizebuf_t *sb, vec_t f, protocolversion_t protocol);

void MSG_BeginReading (sizebuf_t *sb);
int MSG_ReadLittleShort (sizebuf_t *sb);
int MSG_ReadBigShort (sizebuf_t *sb);
int MSG_ReadLittleLong (sizebuf_t *sb);
int MSG_ReadBigLong (sizebuf_t *sb);
float MSG_ReadLittleFloat (sizebuf_t *sb);
float MSG_ReadBigFloat (sizebuf_t *sb);
char *MSG_ReadString (sizebuf_t *sb, char *string, size_t maxstring);
int MSG_ReadBytes (sizebuf_t *sb, int numbytes, unsigned char *out);

#define MSG_ReadChar(sb) ((sb)->readcount >= (sb)->cursize ? ((sb)->badread = true, -1) : (signed char)(sb)->data[(sb)->readcount++])
#define MSG_ReadByte(sb) ((sb)->readcount >= (sb)->cursize ? ((sb)->badread = true, -1) : (unsigned char)(sb)->data[(sb)->readcount++])
#define MSG_ReadShort MSG_ReadLittleShort
#define MSG_ReadLong MSG_ReadLittleLong
#define MSG_ReadFloat MSG_ReadLittleFloat

float MSG_ReadAngle8i (sizebuf_t *sb);
float MSG_ReadAngle16i (sizebuf_t *sb);
float MSG_ReadAngle32f (sizebuf_t *sb);
float MSG_ReadCoord13i (sizebuf_t *sb);
float MSG_ReadCoord16i (sizebuf_t *sb);
float MSG_ReadCoord32f (sizebuf_t *sb);
float MSG_ReadCoord (sizebuf_t *sb, protocolversion_t protocol);
void MSG_ReadVector (sizebuf_t *sb, vec3_t v, protocolversion_t protocol);
float MSG_ReadAngle (sizebuf_t *sb, protocolversion_t protocol);
    
                                                                              

typedef float (*COM_WordWidthFunc_t) (void *passthrough, const char *w, size_t *length, float maxWidth);                                                                                                                                    
typedef int (*COM_LineProcessorFunc) (void *passthrough, const char *line, size_t length, float width, qboolean isContination);
int COM_Wordwrap(const char *string, size_t length, float continuationSize, float maxWidth, COM_WordWidthFunc_t wordWidth, void *passthroughCW, COM_LineProcessorFunc processLine, void *passthroughPL);

extern char com_token[MAX_INPUTLINE];

int COM_ParseToken_Simple(const char **datapointer, qboolean returnnewline, qboolean parsebackslash, qboolean parsecomments);
int COM_ParseToken_QuakeC(const char **datapointer, qboolean returnnewline);
int COM_ParseToken_VM_Tokenize(const char **datapointer, qboolean returnnewline);
int COM_ParseToken_Console(const char **datapointer);

extern int com_argc;
extern const char **com_argv;
extern int com_selffd;

int COM_CheckParm (const char *parm);
void COM_Init (void);
void COM_Shutdown (void);
void COM_InitGameType (void);

char *va(char *buf, size_t buflen, const char *format, ...) DP_FUNC_PRINTF(3);
                                                                                                             


                                                                             
#ifdef snprintf
# undef snprintf
#endif
#define snprintf DO_NOT_USE_SNPRINTF__USE_DPSNPRINTF
#ifdef vsnprintf
# undef vsnprintf
#endif
#define vsnprintf DO_NOT_USE_VSNPRINTF__USE_DPVSNPRINTF

                             
                                                                    
                                                                            
                                   
extern int dpsnprintf (char *buffer, size_t buffersize, const char *format, ...) DP_FUNC_PRINTF(3);
extern int dpvsnprintf (char *buffer, size_t buffersize, const char *format, va_list args);

                                                                                                           
                                                                
#undef strcat
#define strcat DO_NOT_USE_STRCAT__USE_STRLCAT_OR_MEMCPY
#undef strncat
#define strncat DO_NOT_USE_STRNCAT__USE_STRLCAT_OR_MEMCPY
#undef strcpy
#define strcpy DO_NOT_USE_STRCPY__USE_STRLCPY_OR_MEMCPY
#undef strncpy
#define strncpy DO_NOT_USE_STRNCPY__USE_STRLCPY_OR_MEMCPY
                
                                                    


                                                                              

extern	struct cvar_s	registered;
extern	struct cvar_s	cmdline;

typedef enum userdirmode_e
{
	USERDIRMODE_NOHOME,                
	USERDIRMODE_HOME,                                        
	USERDIRMODE_MYGAMES,                                                           
	USERDIRMODE_SAVEDGAMES,                                                                                               
	USERDIRMODE_COUNT
}
userdirmode_t;

typedef enum gamemode_e
{
	GAME_NORMAL,
	GAME_HIPNOTIC,
	GAME_ROGUE,
	GAME_QUOTH,
	GAME_NEHAHRA,
	GAME_NEXUIZ,
	GAME_XONOTIC,
	GAME_TRANSFUSION,
	GAME_GOODVSBAD2,
	GAME_TEU,
	GAME_BATTLEMECH,
	GAME_ZYMOTIC,
	GAME_SETHERAL,
	GAME_TENEBRAE,                        
	GAME_NEOTERIC,
	GAME_OPENQUARTZ,                  
	GAME_PRYDON,
	GAME_DELUXEQUAKE,
	GAME_THEHUNTED,
	GAME_DEFEATINDETAIL2,
	GAME_DARSANA,
	GAME_CONTAGIONTHEORY,
	GAME_EDU2P,
	GAME_PROPHECY,
	GAME_BLOODOMNICIDE,
	GAME_STEELSTORM,                     
	GAME_STEELSTORM2,                     
	GAME_SSAMMO,                     
	GAME_STEELSTORMREVENANTS,                                
	GAME_TOMESOFMEPHISTOPHELES,                     
	GAME_STRAPBOMB,                              
	GAME_MOONHELM,
	GAME_VORETOURNAMENT,
	GAME_COUNT
}
gamemode_t;

                                                                            
#define IS_NEXUIZ_DERIVED(g) ((g) == GAME_NEXUIZ || (g) == GAME_XONOTIC || (g) == GAME_VORETOURNAMENT)
                      
#define IS_OLDNEXUIZ_DERIVED(g) ((g) == GAME_NEXUIZ || (g) == GAME_VORETOURNAMENT)

extern gamemode_t gamemode;
extern const char *gamename;
extern const char *gamenetworkfiltername;
extern const char *gamedirname1;
extern const char *gamedirname2;
extern const char *gamescreenshotname;
extern const char *gameuserdirname;
extern char com_modname[MAX_OSPATH];

void COM_ChangeGameTypeForGameDirs(void);

void COM_ToLowerString (const char *in, char *out, size_t size_out);
void COM_ToUpperString (const char *in, char *out, size_t size_out);
int COM_StringBeginsWith(const char *s, const char *match);

int COM_ReadAndTokenizeLine(const char **text, char **argv, int maxargc, char *tokenbuf, int tokenbufsize, const char *commentprefix);

size_t COM_StringLengthNoColors(const char *s, size_t size_s, qboolean *valid);
qboolean COM_StringDecolorize(const char *in, size_t size_in, char *out, size_t size_out, qboolean escape_carets);
void COM_ToLowerString (const char *in, char *out, size_t size_out);
void COM_ToUpperString (const char *in, char *out, size_t size_out);

typedef struct stringlist_s
{
	                                                                         
	int maxstrings;
	int numstrings;
	char **strings;
} stringlist_t;

int matchpattern(const char *in, const char *pattern, int caseinsensitive);
int matchpattern_with_separator(const char *in, const char *pattern, int caseinsensitive, const char *separators, qboolean wildcard_least_one);
void stringlistinit(stringlist_t *list);
void stringlistfreecontents(stringlist_t *list);
void stringlistappend(stringlist_t *list, const char *text);
void stringlistsort(stringlist_t *list, qboolean uniq);
void listdirectory(stringlist_t *list, const char *basepath, const char *path);

char *InfoString_GetValue(const char *buffer, const char *key, char *value, size_t valuelength);
void InfoString_SetValue(char *buffer, size_t bufferlength, const char *key, const char *value);
void InfoString_Print(char *buffer);

                                    
                                     
#if defined(__OpenBSD__) || defined(__NetBSD__) || defined(__FreeBSD__) || defined(MACOSX)
# define HAVE_STRLCAT 1
# define HAVE_STRLCPY 1
#endif

#ifndef HAVE_STRLCAT
   
                                                                    
                                                               
                                                                      
                                                       
                                         
   
size_t strlcat(char *dst, const char *src, size_t siz);
#endif                         

#ifndef HAVE_STRLCPY
   
                                                                
                                                            
                                                              
   
size_t strlcpy(char *dst, const char *src, size_t siz);

#endif                         

void FindFraction(double val, int *num, int *denom, int denomMax);

                                                   
char **XPM_DecodeString(const char *in);

size_t base64_encode(unsigned char *buf, size_t buflen, size_t outbuflen);

#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))

#endif

