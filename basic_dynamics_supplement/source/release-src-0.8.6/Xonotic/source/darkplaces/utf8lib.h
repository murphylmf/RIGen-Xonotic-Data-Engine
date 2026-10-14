  
                                         
   
#ifndef UTF8LIB_H__
#define UTF8LIB_H__

#include "qtypes.h"

                            
                             
                                                                                        
#ifdef _MSC_VER
typedef __int32 U_int32;
#else
#include <stdint.h>
#include <sys/types.h>
typedef int32_t U_int32;
#endif

                          
typedef U_int32 Uchar;

                                                                             
              
                                                                              
                                                                
                                                                                         
                                                                                         
extern cvar_t    utf8_enable;
void   u8_Init(void);

size_t u8_strlen(const char*);
size_t u8_strnlen(const char*, size_t);
int    u8_byteofs(const char*, size_t, size_t*);
int    u8_charidx(const char*, size_t, size_t*);
size_t u8_bytelen(const char*, size_t);
size_t u8_prevbyte(const char*, size_t);
Uchar  u8_getchar_utf8_enabled(const char*, const char**);
Uchar  u8_getnchar_utf8_enabled(const char*, const char**, size_t);
int    u8_fromchar(Uchar, char*, size_t);
size_t u8_mbstowcs(Uchar *, const char *, size_t);
size_t u8_wcstombs(char*, const Uchar*, size_t);
size_t u8_COM_StringLengthNoColors(const char *s, size_t size_s, qboolean *valid);

                                                 
char  *u8_encodech(Uchar ch, size_t*, char*buf16);

size_t u8_strpad(char *out, size_t outsize, const char *in, qboolean leftalign, size_t minwidth, size_t maxwidth);
size_t u8_strpad_colorcodes(char *out, size_t outsize, const char *in, qboolean leftalign, size_t minwidth, size_t maxwidth);

                                                                              
                                                                                            
        
   
extern Uchar u8_quake2utf8map[256];
                                                                                 
#define u8_getchar(c,e) (utf8_enable.integer ? u8_getchar_utf8_enabled(c,e) : (u8_quake2utf8map[(unsigned char)(*(e) = (c) + 1)[-1]]))
#define u8_getchar_noendptr(c) (utf8_enable.integer ? u8_getchar_utf8_enabled(c,NULL) : (u8_quake2utf8map[(unsigned char)*(c)]))
#define u8_getchar_check(c,e) ((e) ? u8_getchar((c),(e)) : u8_getchar_noendptr((c)))
#define u8_getnchar(c,e,n) (utf8_enable.integer ? u8_getnchar_utf8_enabled(c,e,n) : ((n) <= 0 ? ((*(e) = c), 0) : (u8_quake2utf8map[(unsigned char)(*(e) = (c) + 1)[-1]])))
#define u8_getnchar_noendptr(c,n) (utf8_enable.integer ? u8_getnchar_utf8_enabled(c,NULL,n) : ((n) <= 0 ? 0  : (u8_quake2utf8map[(unsigned char)*(c)])))
#define u8_getnchar_check(c,e,n) ((e) ? u8_getchar((c),(e),(n)) : u8_getchar_noendptr((c),(n)))

Uchar u8_toupper(Uchar ch);
Uchar u8_tolower(Uchar ch);

#endif               
