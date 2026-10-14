#ifndef CRYPTO_H
#define CRYPTO_H

extern cvar_t crypto_developer;
extern cvar_t crypto_aeslevel;
#define ENCRYPTION_REQUIRED (crypto_aeslevel.integer >= 3)

extern int crypto_keyfp_recommended_length;                                         

#define CRYPTO_HEADERSIZE 31
                                          
                                                                

#include "lhnet.h"

#define FP64_SIZE 44
#define DHKEY_SIZE 16

typedef struct
{
	unsigned char dhkey[DHKEY_SIZE];                                  
	char client_idfp[FP64_SIZE+1];
	char client_keyfp[FP64_SIZE+1];
	qboolean client_issigned;
	char server_idfp[FP64_SIZE+1];
	char server_keyfp[FP64_SIZE+1];
	qboolean server_issigned;
	qboolean authenticated;
	qboolean use_aes;
	void *data;
}
crypto_t;

void Crypto_Init(void);
void Crypto_Init_Commands(void);
void Crypto_LoadKeys(void);                                                                    
void Crypto_Shutdown(void);
qboolean Crypto_Available(void);
void sha256(unsigned char *out, const unsigned char *in, int n);                                            
const void *Crypto_EncryptPacket(crypto_t *crypto, const void *data_src, size_t len_src, void *data_dst, size_t *len_dst, size_t len);
const void *Crypto_DecryptPacket(crypto_t *crypto, const void *data_src, size_t len_src, void *data_dst, size_t *len_dst, size_t len);
#define CRYPTO_NOMATCH 0                                                 
#define CRYPTO_MATCH 1                                               
#define CRYPTO_DISCARD 2                              
#define CRYPTO_REPLACE 3                                             
int Crypto_ClientParsePacket(const char *data_in, size_t len_in, char *data_out, size_t *len_out, lhnetaddress_t *peeraddress);
int Crypto_ServerParsePacket(const char *data_in, size_t len_in, char *data_out, size_t *len_out, lhnetaddress_t *peeraddress);

                                                                

qboolean Crypto_ServerAppendToChallenge(const char *data_in, size_t len_in, char *data_out, size_t *len_out, size_t maxlen);
crypto_t *Crypto_ServerGetInstance(lhnetaddress_t *peeraddress);
qboolean Crypto_FinishInstance(crypto_t *out, crypto_t *in);                                                                                      
const char *Crypto_GetInfoResponseDataString(void);

                                                                                                                                           
                       
qboolean Crypto_RetrieveHostKey(lhnetaddress_t *peeraddress, int *keyid, char *keyfp, size_t keyfplen, char *idfp, size_t idfplen, int *aeslevel, qboolean *issigned);
int Crypto_RetrieveLocalKey(int keyid, char *keyfp, size_t keyfplen, char *idfp, size_t idfplen, qboolean *issigned);                                                                   

size_t Crypto_SignData(const void *data, size_t datasize, int keyid, void *signed_data, size_t signed_size);
size_t Crypto_SignDataDetached(const void *data, size_t datasize, int keyid, void *signed_data, size_t signed_size);

                    
                
                                                                
                                                                          
                                                                
                                                                                    
            
                                                                
                                                                                                                                                                                 
  
                   
                                                                                      
                                                                
                                                                                                                            
                                                                                                            
                                                                                         
                                                                                  
                                                                                                                     
                                                                                                            
                                                               
                                                                
                                                                                                                        
                                                                                              
                                                            
                                     
                                                                                                       
  
                                    
                                                                                  
                                                           
                                                                                           
                                                                
                                                                                                                            
                                                                                                            
                                                                                                                         
                                                                                                                
  
                                
                                                                                  
                                                           
                                                                
                                                                                                                         
                                                                                               
  
                   
                                                              
                                                                
                                                                                                                      
                                                                                               
                                                                                                       
                                                                                                                                  
  
                                                                     
  
                   
                                                                                              
  
                                                                
                                                                                                                                                                  
  
                                    

            
            
                                                                                 
                                                    
                   
                   
                              
            
                                                                                                             
                   
                                                                     
                                                                                                                     
                
                                                                                                           
                                                                            
                                                                             
                                                                                                                                                        


                     
                    
                        
                                                                              
                                                                               
                                                                           
                                                                               
                                                                            
                                                                          
                                                                      
                                                                             
                                                                            
                                                               
                                                                              

#endif
