enum
{
	CURLCBSTATUS_OK = 0,
	CURLCBSTATUS_FAILED = -1,                                                     
	CURLCBSTATUS_ABORTED = -2,                            
	CURLCBSTATUS_SERVERERROR = -3,                                                 
	CURLCBSTATUS_UNKNOWN = -4                       
};
typedef void (*curl_callback_t) (int status, size_t length_received, unsigned char *buffer, void *cbdata);
                                                                                

void Curl_Run(void);
qboolean Curl_Running(void);
qboolean Curl_Begin_ToFile(const char *URL, double maxspeed, const char *name, int loadtype, qboolean forthismap);

qboolean Curl_Begin_ToMemory(const char *URL, double maxspeed, unsigned char *buf, size_t bufsize, curl_callback_t callback, void *cbdata);
qboolean Curl_Begin_ToMemory_POST(const char *URL, const char *extraheaders, double maxspeed, const char *post_content_type, const unsigned char *postbuf, size_t postbufsize, unsigned char *buf, size_t bufsize, curl_callback_t callback, void *cbdata);
void Curl_Cancel_ToMemory(curl_callback_t callback, void* cbdata);

void Curl_Init(void);
void Curl_Init_Commands(void);
void Curl_Shutdown(void);
void Curl_CancelAll(void);
void Curl_Clear_forthismap(void);
qboolean Curl_Have_forthismap(void);
void Curl_Register_predownload(void);

void Curl_ClearRequirements(void);
void Curl_RequireFile(const char *filename);
void Curl_SendRequirements(void);

typedef struct Curl_downloadinfo_s
{
	char filename[MAX_QPATH];
	double progress;
	double speed;
	qboolean queued;
}
Curl_downloadinfo_t;
Curl_downloadinfo_t *Curl_GetDownloadInfo(int *nDownloads, const char **additional_info, char *addinfo, size_t addinfolength);
	                                    
	                                  
	                                                                    
	                                                                         
	                 
