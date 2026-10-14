  
                       

                                        

                                                              
                                                            
                                                               
                                                       

                                                                
                                                               
                                                     

                                                     

                                                                  
                                           

                                
                             
                             
  

#ifndef FS_H
#define FS_H


                         

typedef struct qfile_s qfile_t;

#ifdef WIN32
                                    
typedef __int64 fs_offset_t;                                                                              
#else
typedef long long fs_offset_t;
#endif



                             

extern char fs_gamedir [MAX_OSPATH];
extern char fs_basedir [MAX_OSPATH];
extern char fs_userdir [MAX_OSPATH];

                                                               
#define MAX_GAMEDIRS 16
extern int fs_numgamedirs;
extern char fs_gamedirs[MAX_GAMEDIRS][MAX_QPATH];


                                  

                                                                                       
                                                                                              

qboolean FS_AddPack(const char *pakfile, qboolean *already_loaded, qboolean keep_plain_dirs);                                                      
const char *FS_WhichPack(const char *filename);
void FS_CreatePath (char *path);
int FS_SysOpenFD(const char *filepath, const char *mode, qboolean nonblocking);                      
qfile_t* FS_SysOpen (const char* filepath, const char* mode, qboolean nonblocking);                      
qfile_t* FS_OpenRealFile (const char* filepath, const char* mode, qboolean quiet);
qfile_t* FS_OpenVirtualFile (const char* filepath, qboolean quiet);
qfile_t* FS_FileFromData (const unsigned char *data, const size_t size, qboolean quiet);
int FS_Close (qfile_t* file);
void FS_RemoveOnClose(qfile_t* file);
fs_offset_t FS_Write (qfile_t* file, const void* data, size_t datasize);
fs_offset_t FS_Read (qfile_t* file, void* buffer, size_t buffersize);
int FS_Print(qfile_t* file, const char *msg);
int FS_Printf(qfile_t* file, const char* format, ...) DP_FUNC_PRINTF(2);
int FS_VPrintf(qfile_t* file, const char* format, va_list ap);
int FS_Getc (qfile_t* file);
int FS_UnGetc (qfile_t* file, unsigned char c);
int FS_Seek (qfile_t* file, fs_offset_t offset, int whence);
fs_offset_t FS_Tell (qfile_t* file);
fs_offset_t FS_FileSize (qfile_t* file);
void FS_Purge (qfile_t* file);
const char *FS_FileWithoutPath (const char *in);
const char *FS_FileExtension (const char *in);
int FS_CheckNastyPath (const char *path, qboolean isgamedir);

extern const char *const fs_checkgamedir_missing;               
const char *FS_CheckGameDir(const char *gamedir);                                                                             

typedef struct
{
	char name[MAX_OSPATH];
	char description[8192];
}
gamedir_t;
extern gamedir_t *fs_all_gamedirs;                                       
extern int fs_all_gamedirs_count;

qboolean FS_ChangeGameDirs(int numgamedirs, char gamedirs[][MAX_QPATH], qboolean complain, qboolean failmissing);
qboolean FS_IsRegisteredQuakePack(const char *name);
int FS_CRCFile(const char *filename, size_t *filesizepointer);
void FS_Rescan(void);

typedef struct fssearch_s
{
	int numfilenames;
	char **filenames;
	                     
	char *filenamesbuffer;
}
fssearch_t;

fssearch_t *FS_Search(const char *pattern, int caseinsensitive, int quiet);
void FS_FreeSearch(fssearch_t *search);

unsigned char *FS_LoadFile (const char *path, mempool_t *pool, qboolean quiet, fs_offset_t *filesizepointer);
unsigned char *FS_SysLoadFile (const char *path, mempool_t *pool, qboolean quiet, fs_offset_t *filesizepointer);
qboolean FS_WriteFileInBlocks (const char *filename, const void *const *data, const fs_offset_t *len, size_t count);
qboolean FS_WriteFile (const char *filename, const void *data, fs_offset_t len);


                                   

void FS_StripExtension (const char *in, char *out, size_t size_out);
void FS_DefaultExtension (char *path, const char *extension, size_t size_path);

#define FS_FILETYPE_NONE 0
#define FS_FILETYPE_FILE 1
#define FS_FILETYPE_DIRECTORY 2
int FS_FileType (const char *filename);		                                 
int FS_SysFileType (const char *filename);		                                          

qboolean FS_FileExists (const char *filename);		                                 
qboolean FS_SysFileExists (const char *filename);	                                          

unsigned char *FS_Deflate(const unsigned char *data, size_t size, size_t *deflated_size, int level, mempool_t *mempool);
unsigned char *FS_Inflate(const unsigned char *data, size_t size, size_t *inflated_size, mempool_t *mempool);

qboolean FS_HasZlib(void);

void FS_Init_SelfPack(void);
void FS_Init(void);
void FS_Shutdown(void);
void FS_Init_Commands(void);

#endif
