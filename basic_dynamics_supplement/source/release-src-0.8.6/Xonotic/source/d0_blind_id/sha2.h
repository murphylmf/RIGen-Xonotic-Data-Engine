  
               
                                                          
   
                                            
                       
  
                                                                     
                                                                     
           
                                                                    
                                                                   
                                                                       
                                                                         
                                                                          
                                                                            
                                                                           
                                                
   
                                                                           
                                                                        
                                                                             
                                                                            
                                                                             
                                                                          
                                                                        
                                                                             
                                                                            
                                                                         
               
  
                                                               
   

#ifndef __SHA2_H__
#define __SHA2_H__

#ifdef __cplusplus
extern "C" {
#endif

#ifdef WIN32
# define SHA2_USE_INTTYPES_H
# define LITTLE_ENDIAN 1234
# define BIG_ENDIAN    4321
# define BYTE_ORDER LITTLE_ENDIAN 
#else
# define SHA2_USE_INTTYPES_H
#endif

  
                                                                     
                                                                   
        
   
#include <sys/types.h>

#ifdef SHA2_USE_INTTYPES_H

#include <inttypes.h>

#endif                          


                                                                        
#define SHA256_BLOCK_LENGTH		64
#define SHA256_DIGEST_LENGTH		32
#define SHA256_DIGEST_STRING_LENGTH	(SHA256_DIGEST_LENGTH * 2 + 1)
#define SHA384_BLOCK_LENGTH		128
#define SHA384_DIGEST_LENGTH		48
#define SHA384_DIGEST_STRING_LENGTH	(SHA384_DIGEST_LENGTH * 2 + 1)
#define SHA512_BLOCK_LENGTH		128
#define SHA512_DIGEST_LENGTH		64
#define SHA512_DIGEST_STRING_LENGTH	(SHA512_DIGEST_LENGTH * 2 + 1)


                                                                        
                                                                       
                                                                    
                   
   
#if 0
typedef unsigned char u_int8_t;		                       
typedef unsigned int u_int32_t;		                       
typedef unsigned long long u_int64_t;	                       
#endif
  
                                                                  
                                                                  
                                                                      
               
  
                          
  
                                                         
  
                                
  
                                         
  
                                 
   
#ifdef SHA2_USE_INTTYPES_H

typedef struct _SHA256_CTX {
	uint32_t	state[8];
	uint64_t	bitcount;
	uint8_t	buffer[SHA256_BLOCK_LENGTH];
} SHA256_CTX;
typedef struct _SHA512_CTX {
	uint64_t	state[8];
	uint64_t	bitcount[2];
	uint8_t	buffer[SHA512_BLOCK_LENGTH];
} SHA512_CTX;

#else                          

typedef struct _SHA256_CTX {
	u_int32_t	state[8];
	u_int64_t	bitcount;
	u_int8_t	buffer[SHA256_BLOCK_LENGTH];
} SHA256_CTX;
typedef struct _SHA512_CTX {
	u_int64_t	state[8];
	u_int64_t	bitcount[2];
	u_int8_t	buffer[SHA512_BLOCK_LENGTH];
} SHA512_CTX;

#endif                          

typedef SHA512_CTX SHA384_CTX;


                                                                        
#ifndef NOPROTO
#ifdef SHA2_USE_INTTYPES_H

void SHA256_Init(SHA256_CTX *);
void SHA256_Update(SHA256_CTX*, const uint8_t*, size_t);
void SHA256_Final(uint8_t[SHA256_DIGEST_LENGTH], SHA256_CTX*);
char* SHA256_End(SHA256_CTX*, char[SHA256_DIGEST_STRING_LENGTH]);
char* SHA256_Data(const uint8_t*, size_t, char[SHA256_DIGEST_STRING_LENGTH]);

void SHA384_Init(SHA384_CTX*);
void SHA384_Update(SHA384_CTX*, const uint8_t*, size_t);
void SHA384_Final(uint8_t[SHA384_DIGEST_LENGTH], SHA384_CTX*);
char* SHA384_End(SHA384_CTX*, char[SHA384_DIGEST_STRING_LENGTH]);
char* SHA384_Data(const uint8_t*, size_t, char[SHA384_DIGEST_STRING_LENGTH]);

void SHA512_Init(SHA512_CTX*);
void SHA512_Update(SHA512_CTX*, const uint8_t*, size_t);
void SHA512_Final(uint8_t[SHA512_DIGEST_LENGTH], SHA512_CTX*);
char* SHA512_End(SHA512_CTX*, char[SHA512_DIGEST_STRING_LENGTH]);
char* SHA512_Data(const uint8_t*, size_t, char[SHA512_DIGEST_STRING_LENGTH]);

#else                          

void SHA256_Init(SHA256_CTX *);
void SHA256_Update(SHA256_CTX*, const u_int8_t*, size_t);
void SHA256_Final(u_int8_t[SHA256_DIGEST_LENGTH], SHA256_CTX*);
char* SHA256_End(SHA256_CTX*, char[SHA256_DIGEST_STRING_LENGTH]);
char* SHA256_Data(const u_int8_t*, size_t, char[SHA256_DIGEST_STRING_LENGTH]);

void SHA384_Init(SHA384_CTX*);
void SHA384_Update(SHA384_CTX*, const u_int8_t*, size_t);
void SHA384_Final(u_int8_t[SHA384_DIGEST_LENGTH], SHA384_CTX*);
char* SHA384_End(SHA384_CTX*, char[SHA384_DIGEST_STRING_LENGTH]);
char* SHA384_Data(const u_int8_t*, size_t, char[SHA384_DIGEST_STRING_LENGTH]);

void SHA512_Init(SHA512_CTX*);
void SHA512_Update(SHA512_CTX*, const u_int8_t*, size_t);
void SHA512_Final(u_int8_t[SHA512_DIGEST_LENGTH], SHA512_CTX*);
char* SHA512_End(SHA512_CTX*, char[SHA512_DIGEST_STRING_LENGTH]);
char* SHA512_Data(const u_int8_t*, size_t, char[SHA512_DIGEST_STRING_LENGTH]);

void sha256(unsigned char *out, const unsigned char *in, int n);

#endif                          

#else              

void SHA256_Init();
void SHA256_Update();
void SHA256_Final();
char* SHA256_End();
char* SHA256_Data();

void SHA384_Init();
void SHA384_Update();
void SHA384_Final();
char* SHA384_End();
char* SHA384_Data();

void SHA512_Init();
void SHA512_Update();
void SHA512_Final();
char* SHA512_End();
char* SHA512_Data();

void sha256();

#endif              

#ifdef	__cplusplus
}
#endif                  

#endif                 

