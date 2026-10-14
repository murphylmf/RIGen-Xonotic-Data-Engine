  
                       

                                        

                                                              
                                                            
                                                               
                                                       

                                                                
                                                               
                                                     

                                                     

                                                                  
                                           

                                
                             
                             
  

#include <limits.h>
#include <fcntl.h>

#ifdef WIN32
# include <direct.h>
# include <io.h>
# include <shlobj.h>
# include <sys/stat.h>
# include <share.h>
#else
# include <pwd.h>
# include <sys/stat.h>
# include <unistd.h>
#endif

#include "quakedef.h"

#if TARGET_OS_IPHONE
                                
# include <SDL.h>
#endif

#include "thread.h"

#include "fs.h"
#include "wad.h"

                                                                      
#ifndef O_BINARY
# define O_BINARY 0
#endif

                                                         
#ifndef O_NONBLOCK
# define O_NONBLOCK 0
#endif

                              
#ifdef WIN32
#undef lseek
# define lseek _lseeki64
#endif

                               
#if _MSC_VER >= 1400
# define read _read
# define write _write
# define close _close
# define unlink _unlink
# define dup _dup
#endif

#if USE_RWOPS
# include <SDL.h>
typedef SDL_RWops *filedesc_t;
# define FILEDESC_INVALID NULL
# define FILEDESC_ISVALID(fd) ((fd) != NULL)
# define FILEDESC_READ(fd,buf,count) ((fs_offset_t)SDL_RWread(fd, buf, 1, count))
# define FILEDESC_WRITE(fd,buf,count) ((fs_offset_t)SDL_RWwrite(fd, buf, 1, count))
# define FILEDESC_CLOSE SDL_RWclose
# define FILEDESC_SEEK SDL_RWseek
static filedesc_t FILEDESC_DUP(const char *filename, filedesc_t fd) {
	filedesc_t new_fd = SDL_RWFromFile(filename, "rb");
	if (SDL_RWseek(new_fd, SDL_RWseek(fd, 0, RW_SEEK_CUR), RW_SEEK_SET) < 0) {
		SDL_RWclose(new_fd);
		return NULL;
	}
	return new_fd;
}
# define unlink(name) Con_DPrintf("Sorry, no unlink support when trying to unlink %s.\n", (name))
#else
typedef int filedesc_t;
# define FILEDESC_INVALID -1
# define FILEDESC_ISVALID(fd) ((fd) != -1)
# define FILEDESC_READ read
# define FILEDESC_WRITE write
# define FILEDESC_CLOSE close
# define FILEDESC_SEEK lseek
static filedesc_t FILEDESC_DUP(const char *filename, filedesc_t fd) {
	return dup(fd);
}
#endif

                        

                                                                              
                                                                    

                                                                           
                                                                
                                                                          
                                                                     
                                                        

                                                                            
                                                                         
                                                                          
                                                                            
                                                                            
                          

  


  
                                                                             

         

                                                                             
  

                                                  
#define ZIP_DATA_HEADER	0x504B0304             
#define ZIP_CDIR_HEADER	0x504B0102             
#define ZIP_END_HEADER	0x504B0506             

                                
#define ZIP_MAX_COMMENTS_SIZE		((unsigned short)0xFFFF)
#define ZIP_END_CDIR_SIZE			22
#define ZIP_CDIR_CHUNK_BASE_SIZE	46
#define ZIP_LOCAL_CHUNK_BASE_SIZE	30

#ifdef LINK_TO_ZLIB
#include <zlib.h>

#define qz_inflate inflate
#define qz_inflateEnd inflateEnd
#define qz_inflateInit2_ inflateInit2_
#define qz_inflateReset inflateReset
#define qz_deflateInit2_ deflateInit2_
#define qz_deflateEnd deflateEnd
#define qz_deflate deflate
#define Z_MEMLEVEL_DEFAULT 8
#else

                               
#define Z_SYNC_FLUSH	2
#define MAX_WBITS		15
#define Z_OK			0
#define Z_STREAM_END	1
#define Z_STREAM_ERROR  (-2)
#define Z_DATA_ERROR    (-3)
#define Z_MEM_ERROR     (-4)
#define Z_BUF_ERROR     (-5)
#define ZLIB_VERSION	"1.2.3"

#define Z_BINARY 0
#define Z_DEFLATED 8
#define Z_MEMLEVEL_DEFAULT 8

#define Z_NULL 0
#define Z_DEFAULT_COMPRESSION (-1)
#define Z_NO_FLUSH 0
#define Z_SYNC_FLUSH 2
#define Z_FULL_FLUSH 3
#define Z_FINISH 4

                                                                   
                                                        
                          


  
                                                                             

     

                                                                             
  

                             
                                                     
                                                  
   
typedef struct
{
	unsigned char			*next_in;	                    
	unsigned int	avail_in;	                                         
	unsigned long	total_in;	                                        

	unsigned char			*next_out;	                                         
	unsigned int	avail_out;	                                     
	unsigned long	total_out;	                                    

	char			*msg;		                                         
	void			*state;		                                

	void			*zalloc;	                                        
	void			*zfree;		                                    
	void			*opaque;	                                                   

	int				data_type;	                                                    
	unsigned long	adler;		                                           
	unsigned long	reserved;	                            
} z_stream;
#endif


                                 
#define QFILE_FLAG_PACKED (1 << 0)
                                                             
#define QFILE_FLAG_DEFLATED (1 << 1)
                                        
#define QFILE_FLAG_DATA (1 << 2)
                                      
#define QFILE_FLAG_REMOVE (1 << 3)

#define FILE_BUFF_SIZE 2048
typedef struct
{
	z_stream	zstream;
	size_t		comp_length;			                                  
	size_t		in_ind, in_len;			                                          
	size_t		in_position;			                                    
	unsigned char		input [FILE_BUFF_SIZE];
} ztoolkit_t;

struct qfile_s
{
	int				flags;
	filedesc_t			handle;					                    
	fs_offset_t		real_length;			                                                             
	fs_offset_t		position;				                                 
	fs_offset_t		offset;					                                                 
	int				ungetc;					                                                                  

	                  
	fs_offset_t		buff_ind, buff_len;		                                    
	unsigned char			buff [FILE_BUFF_SIZE];

	ztoolkit_t*		ztk;	                      

	const unsigned char *data;	                    

	const char *filename;                                                         
};


                                     

                                                                      

typedef struct pk3_endOfCentralDir_s
{
	unsigned int signature;
	unsigned short disknum;
	unsigned short cdir_disknum;	                                                               
	unsigned short localentries;	                                                            
	unsigned short nbentries;		                                                                  
	unsigned int cdir_size;			                                  
	unsigned int cdir_offset;		                                             
	unsigned short comment_size;
	fs_offset_t prepended_garbage;
} pk3_endOfCentralDir_t;


                                     
typedef struct dpackfile_s
{
	char name[56];
	int filepos, filelen;
} dpackfile_t;

typedef struct dpackheader_s
{
	char id[4];
	int dirofs;
	int dirlen;
} dpackheader_t;


                            
     
   
                                                        
#define PACKFILE_FLAG_TRUEOFFS (1 << 0)
                                               
#define PACKFILE_FLAG_DEFLATED (1 << 1)
                           
#define PACKFILE_FLAG_SYMLINK (1 << 2)

typedef struct packfile_s
{
	char name [MAX_QPATH];
	int flags;
	fs_offset_t offset;
	fs_offset_t packsize;	                        
	fs_offset_t realsize;	                                  
} packfile_t;

typedef struct pack_s
{
	char filename [MAX_OSPATH];
	char shortname [MAX_QPATH];
	filedesc_t handle;
	int ignorecase;                       
	int numfiles;
	qboolean vpack;
	packfile_t *files;
} pack_t;
    

                                               
typedef struct searchpath_s
{
	                                           
	char filename[MAX_OSPATH];
	pack_t *pack;
	struct searchpath_s *next;
} searchpath_t;


  
                                                                             

                   

                                                                             
  

void FS_Dir_f(void);
void FS_Ls_f(void);
void FS_Which_f(void);

static searchpath_t *FS_FindFile (const char *name, int* index, qboolean quiet);
static packfile_t* FS_AddFileToPack (const char* name, pack_t* pack,
									fs_offset_t offset, fs_offset_t packsize,
									fs_offset_t realsize, int flags);


  
                                                                             

         

                                                                             
  

mempool_t *fs_mempool;
void *fs_mutex = NULL;

searchpath_t *fs_searchpaths = NULL;
const char *const fs_checkgamedir_missing = "missing";

#define MAX_FILES_IN_PACK	65536

char fs_userdir[MAX_OSPATH];
char fs_gamedir[MAX_OSPATH];
char fs_basedir[MAX_OSPATH];
static pack_t *fs_selfpack = NULL;

                                                               
int fs_numgamedirs = 0;
char fs_gamedirs[MAX_GAMEDIRS][MAX_QPATH];

                                        
gamedir_t *fs_all_gamedirs = NULL;
int fs_all_gamedirs_count = 0;

cvar_t scr_screenshot_name = {CVAR_NORESETTODEFAULTS, "scr_screenshot_name","dp", "prefix name for saved screenshots (changes based on -game commandline, as well as which game mode is running; the date is encoded using strftime escapes)"};
cvar_t fs_empty_files_in_pack_mark_deletions = {0, "fs_empty_files_in_pack_mark_deletions", "0", "if enabled, empty files in a pak/pk3 count as not existing but cancel the search in further packs, effectively allowing patch pak/pk3 files to 'delete' files"};
cvar_t cvar_fs_gamedir = {CVAR_READONLY | CVAR_NORESETTODEFAULTS, "fs_gamedir", "", "the list of currently selected gamedirs (use the 'gamedir' command to change this)"};


  
                                                                             

                                

                                                                             
  

#ifndef LINK_TO_ZLIB
                               
#if defined(WIN32) && defined(ZLIB_USES_WINAPI)
# define ZEXPORT WINAPI
#else
# define ZEXPORT
#endif

static int (ZEXPORT *qz_inflate) (z_stream* strm, int flush);
static int (ZEXPORT *qz_inflateEnd) (z_stream* strm);
static int (ZEXPORT *qz_inflateInit2_) (z_stream* strm, int windowBits, const char *version, int stream_size);
static int (ZEXPORT *qz_inflateReset) (z_stream* strm);
static int (ZEXPORT *qz_deflateInit2_) (z_stream* strm, int level, int method, int windowBits, int memLevel, int strategy, const char *version, int stream_size);
static int (ZEXPORT *qz_deflateEnd) (z_stream* strm);
static int (ZEXPORT *qz_deflate) (z_stream* strm, int flush);
#endif

#define qz_inflateInit2(strm, windowBits) \
        qz_inflateInit2_((strm), (windowBits), ZLIB_VERSION, sizeof(z_stream))
#define qz_deflateInit2(strm, level, method, windowBits, memLevel, strategy) \
        qz_deflateInit2_((strm), (level), (method), (windowBits), (memLevel), (strategy), ZLIB_VERSION, sizeof(z_stream))

#ifndef LINK_TO_ZLIB
                                                                          

static dllfunction_t zlibfuncs[] =
{
	{"inflate",			(void **) &qz_inflate},
	{"inflateEnd",		(void **) &qz_inflateEnd},
	{"inflateInit2_",	(void **) &qz_inflateInit2_},
	{"inflateReset",	(void **) &qz_inflateReset},
	{"deflateInit2_",   (void **) &qz_deflateInit2_},
	{"deflateEnd",      (void **) &qz_deflateEnd},
	{"deflate",         (void **) &qz_deflate},
	{NULL, NULL}
};

                       
static dllhandle_t zlib_dll = NULL;
#endif

#ifdef WIN32
static HRESULT (WINAPI *qSHGetFolderPath) (HWND hwndOwner, int nFolder, HANDLE hToken, DWORD dwFlags, LPTSTR pszPath);
static dllfunction_t shfolderfuncs[] =
{
	{"SHGetFolderPathA", (void **) &qSHGetFolderPath},
	{NULL, NULL}
};
static const char* shfolderdllnames [] =
{
	"shfolder.dll",                               
	NULL
};
static dllhandle_t shfolder_dll = NULL;

const GUID qFOLDERID_SavedGames = {0x4C5C32FF, 0xBB9D, 0x43b0, {0xB5, 0xB4, 0x2D, 0x72, 0xE5, 0x4E, 0xAA, 0xA4}}; 
#define qREFKNOWNFOLDERID const GUID *
#define qKF_FLAG_CREATE 0x8000
#define qKF_FLAG_NO_ALIAS 0x1000
static HRESULT (WINAPI *qSHGetKnownFolderPath) (qREFKNOWNFOLDERID rfid, DWORD dwFlags, HANDLE hToken, PWSTR *ppszPath);
static dllfunction_t shell32funcs[] =
{
	{"SHGetKnownFolderPath", (void **) &qSHGetKnownFolderPath},
	{NULL, NULL}
};
static const char* shell32dllnames [] =
{
	"shell32.dll",                     
	NULL
};
static dllhandle_t shell32_dll = NULL;

static HRESULT (WINAPI *qCoInitializeEx)(LPVOID pvReserved, DWORD dwCoInit);
static void (WINAPI *qCoUninitialize)(void);
static void (WINAPI *qCoTaskMemFree)(LPVOID pv);
static dllfunction_t ole32funcs[] =
{
	{"CoInitializeEx", (void **) &qCoInitializeEx},
	{"CoUninitialize", (void **) &qCoUninitialize},
	{"CoTaskMemFree", (void **) &qCoTaskMemFree},
	{NULL, NULL}
};
static const char* ole32dllnames [] =
{
	"ole32.dll",                   
	NULL
};
static dllhandle_t ole32_dll = NULL;
#endif

  
                    
                

                   
                    
  
static void PK3_CloseLibrary (void)
{
#ifndef LINK_TO_ZLIB
	Sys_UnloadLibrary (&zlib_dll);
#endif
}


  
                    
               

                        
                    
  
static qboolean PK3_OpenLibrary (void)
{
#ifdef LINK_TO_ZLIB
	return true;
#else
	const char* dllnames [] =
	{
#if defined(WIN32)
# ifdef ZLIB_USES_WINAPI
		"zlibwapi.dll",
		"zlib.dll",
# else
		"zlib1.dll",
# endif
#elif defined(MACOSX)
		"libz.dylib",
#else
		"libz.so.1",
		"libz.so",
#endif
		NULL
	};

	                  
	if (zlib_dll)
		return true;

	               
	return Sys_LoadLibrary (dllnames, &zlib_dll, zlibfuncs);
#endif
}

  
                    
          

                        
                    
  
qboolean FS_HasZlib(void)
{
#ifdef LINK_TO_ZLIB
	return true;
#else
	PK3_OpenLibrary();              
	return (zlib_dll != 0);
#endif
}

  
                    
                      

                                                           
                    
  
static qboolean PK3_GetEndOfCentralDir (const char *packfile, filedesc_t packhandle, pk3_endOfCentralDir_t *eocd)
{
	fs_offset_t filesize, maxsize;
	unsigned char *buffer, *ptr;
	int ind;

	                       
	filesize = FILEDESC_SEEK (packhandle, 0, SEEK_END);
	if (filesize < ZIP_END_CDIR_SIZE)
		return false;

	                                     
	if (filesize < ZIP_MAX_COMMENTS_SIZE + ZIP_END_CDIR_SIZE)
		maxsize = filesize;
	else
		maxsize = ZIP_MAX_COMMENTS_SIZE + ZIP_END_CDIR_SIZE;
	buffer = (unsigned char *)Mem_Alloc (tempmempool, maxsize);
	FILEDESC_SEEK (packhandle, filesize - maxsize, SEEK_SET);
	if (FILEDESC_READ (packhandle, buffer, maxsize) != (fs_offset_t) maxsize)
	{
		Mem_Free (buffer);
		return false;
	}

	                                                                       
	maxsize -= ZIP_END_CDIR_SIZE;
	ptr = &buffer[maxsize];
	ind = 0;
	while (BuffBigLong (ptr) != ZIP_END_HEADER)
	{
		if (ind == maxsize)
		{
			Mem_Free (buffer);
			return false;
		}

		ind++;
		ptr--;
	}

	memcpy (eocd, ptr, ZIP_END_CDIR_SIZE);
	eocd->signature = LittleLong (eocd->signature);
	eocd->disknum = LittleShort (eocd->disknum);
	eocd->cdir_disknum = LittleShort (eocd->cdir_disknum);
	eocd->localentries = LittleShort (eocd->localentries);
	eocd->nbentries = LittleShort (eocd->nbentries);
	eocd->cdir_size = LittleLong (eocd->cdir_size);
	eocd->cdir_offset = LittleLong (eocd->cdir_offset);
	eocd->comment_size = LittleShort (eocd->comment_size);
	eocd->prepended_garbage = filesize - (ind + ZIP_END_CDIR_SIZE) - eocd->cdir_offset - eocd->cdir_size;                                
	eocd->cdir_offset += eocd->prepended_garbage;

	Mem_Free (buffer);

	if (
			eocd->cdir_size > filesize ||
			eocd->cdir_offset >= filesize ||
			eocd->cdir_offset + eocd->cdir_size > filesize
	   )
	{
		                                       
		return false;
	}

	return true;
}


  
                    
                 

                                     
                    
  
static int PK3_BuildFileList (pack_t *pack, const pk3_endOfCentralDir_t *eocd)
{
	unsigned char *central_dir, *ptr;
	unsigned int ind;
	fs_offset_t remaining;

	                                       
	central_dir = (unsigned char *)Mem_Alloc (tempmempool, eocd->cdir_size);
	if (FILEDESC_SEEK (pack->handle, eocd->cdir_offset, SEEK_SET) == -1)
	{
		Mem_Free (central_dir);
		return -1;
	}
	if(FILEDESC_READ (pack->handle, central_dir, eocd->cdir_size) != (fs_offset_t) eocd->cdir_size)
	{
		Mem_Free (central_dir);
		return -1;
	}

	                               
	                                                                            
	                                                                                    
	remaining = eocd->cdir_size;
	pack->numfiles = 0;
	ptr = central_dir;
	for (ind = 0; ind < eocd->nbentries; ind++)
	{
		fs_offset_t namesize, count;

		                              
		if (remaining < ZIP_CDIR_CHUNK_BASE_SIZE)
		{
			Mem_Free (central_dir);
			return -1;
		}
		remaining -= ZIP_CDIR_CHUNK_BASE_SIZE;

		               
		if (BuffBigLong (ptr) != ZIP_CDIR_HEADER)
		{
			Mem_Free (central_dir);
			return -1;
		}

		namesize = (unsigned short)BuffLittleShort (&ptr[28]);	                  

		                                                
		                                        
		                                                                                                        
		  
		                                                                      
		                                                                     
		               
		  
		                                                                 
		  
		                                       
		                                                                     
		if ((ptr[8] & 0x21) == 0 && (ptr[38] & 0x18) == 0)
		{
			                                   
			if (remaining < namesize || namesize >= (int)sizeof (*pack->files))
			{
				Mem_Free (central_dir);
				return -1;
			}

			                                                                                      
			if (ptr[ZIP_CDIR_CHUNK_BASE_SIZE + namesize - 1] != '/')
			{
				char filename [sizeof (pack->files[0].name)];
				fs_offset_t offset, packsize, realsize;
				int flags;

				                                           
				namesize = min(namesize, (int)sizeof (filename) - 1);
				memcpy (filename, &ptr[ZIP_CDIR_CHUNK_BASE_SIZE], namesize);
				filename[namesize] = '\0';

				if (BuffLittleShort (&ptr[10]))
					flags = PACKFILE_FLAG_DEFLATED;
				else
					flags = 0;
				offset = (unsigned int)(BuffLittleLong (&ptr[42]) + eocd->prepended_garbage);
				packsize = (unsigned int)BuffLittleLong (&ptr[20]);
				realsize = (unsigned int)BuffLittleLong (&ptr[24]);

				switch(ptr[5])                       
				{
					case 3:         
					case 2:        
					case 16:         
						if((BuffLittleShort(&ptr[40]) & 0120000) == 0120000)
							                                                                 
							flags |= PACKFILE_FLAG_SYMLINK;
						break;
				}

				FS_AddFileToPack (filename, pack, offset, packsize, realsize, flags);
			}
		}

		                                                
		                                  
		                                    
		count = namesize + (unsigned short)BuffLittleShort (&ptr[30]) + (unsigned short)BuffLittleShort (&ptr[32]);
		ptr += ZIP_CDIR_CHUNK_BASE_SIZE + count;
		remaining -= count;
	}

	                                                    
	if (central_dir != NULL)
		Mem_Free (central_dir);
	return pack->numfiles;
}


  
                    
              

                                                 
                    
  
static pack_t *FS_LoadPackPK3FromFD (const char *packfile, filedesc_t packhandle, qboolean silent)
{
	pk3_endOfCentralDir_t eocd;
	pack_t *pack;
	int real_nb_files;

	if (! PK3_GetEndOfCentralDir (packfile, packhandle, &eocd))
	{
		if(!silent)
			Con_Printf ("%s is not a PK3 file\n", packfile);
		FILEDESC_CLOSE(packhandle);
		return NULL;
	}

	                                            
	if (eocd.disknum != 0 || eocd.cdir_disknum != 0)
	{
		Con_Printf ("%s is a multi-volume ZIP archive\n", packfile);
		FILEDESC_CLOSE(packhandle);
		return NULL;
	}

	                                                                         
	                                                      
#if MAX_FILES_IN_PACK < 65535
	if (eocd.nbentries > MAX_FILES_IN_PACK)
	{
		Con_Printf ("%s contains too many files (%hu)\n", packfile, eocd.nbentries);
		FILEDESC_CLOSE(packhandle);
		return NULL;
	}
#endif

	                                       
	pack = (pack_t *)Mem_Alloc(fs_mempool, sizeof (pack_t));
	pack->ignorecase = true;                    
	strlcpy (pack->filename, packfile, sizeof (pack->filename));
	pack->handle = packhandle;
	pack->numfiles = eocd.nbentries;
	pack->files = (packfile_t *)Mem_Alloc(fs_mempool, eocd.nbentries * sizeof(packfile_t));

	real_nb_files = PK3_BuildFileList (pack, &eocd);
	if (real_nb_files < 0)
	{
		Con_Printf ("%s is not a valid PK3 file\n", packfile);
		FILEDESC_CLOSE(pack->handle);
		Mem_Free(pack);
		return NULL;
	}

	Con_DPrintf("Added packfile %s (%i files)\n", packfile, real_nb_files);
	return pack;
}

static filedesc_t FS_SysOpenFiledesc(const char *filepath, const char *mode, qboolean nonblocking);
static pack_t *FS_LoadPackPK3 (const char *packfile)
{
	filedesc_t packhandle;
	packhandle = FS_SysOpenFiledesc (packfile, "rb", false);
	if (!FILEDESC_ISVALID(packhandle))
		return NULL;
	return FS_LoadPackPK3FromFD(packfile, packhandle, false);
}


  
                    
                     

                                       
                    
  
static qboolean PK3_GetTrueFileOffset (packfile_t *pfile, pack_t *pack)
{
	unsigned char buffer [ZIP_LOCAL_CHUNK_BASE_SIZE];
	fs_offset_t count;

	                 
	if (pfile->flags & PACKFILE_FLAG_TRUEOFFS)
		return true;

	                                  
	if (FILEDESC_SEEK (pack->handle, pfile->offset, SEEK_SET) == -1)
	{
		Con_Printf ("Can't seek in package %s\n", pack->filename);
		return false;
	}
	count = FILEDESC_READ (pack->handle, buffer, ZIP_LOCAL_CHUNK_BASE_SIZE);
	if (count != ZIP_LOCAL_CHUNK_BASE_SIZE || BuffBigLong (buffer) != ZIP_DATA_HEADER)
	{
		Con_Printf ("Can't retrieve file %s in package %s\n", pfile->name, pack->filename);
		return false;
	}

	                            
	pfile->offset += BuffLittleShort (&buffer[26]) + BuffLittleShort (&buffer[28]) + ZIP_LOCAL_CHUNK_BASE_SIZE;

	pfile->flags |= PACKFILE_FLAG_TRUEOFFS;
	return true;
}


  
                                                                             

                       

                                                                             
  


  
                    
                

                                                        
                    
  
static packfile_t* FS_AddFileToPack (const char* name, pack_t* pack,
									 fs_offset_t offset, fs_offset_t packsize,
									 fs_offset_t realsize, int flags)
{
	int (*strcmp_funct) (const char* str1, const char* str2);
	int left, right, middle;
	packfile_t *pfile;

	strcmp_funct = pack->ignorecase ? strcasecmp : strcmp;

	                                                                 
	left = 0;
	right = pack->numfiles - 1;
	while (left <= right)
	{
		int diff;

		middle = (left + right) / 2;
		diff = strcmp_funct (pack->files[middle].name, name);

		                                          
		if (!diff)
			Con_Printf ("Package %s contains the file %s several times\n", pack->filename, name);

		                               
		if (diff > 0)
			right = middle - 1;
		else
			left = middle + 1;
	}

	                                                                            
	pfile = &pack->files[left];
	memmove (pfile + 1, pfile, (pack->numfiles - left) * sizeof (*pfile));
	pack->numfiles++;

	strlcpy (pfile->name, name, sizeof (pfile->name));
	pfile->offset = offset;
	pfile->packsize = packsize;
	pfile->realsize = realsize;
	pfile->flags = flags;

	return pfile;
}


static void FS_mkdir (const char *path)
{
	if(COM_CheckParm("-readonly"))
		return;

#if WIN32
	if (_mkdir (path) == -1)
#else
	if (mkdir (path, 0777) == -1)
#endif
	{
		                                                               
		                                                            
		                                                              
		                                     
	}
}


  
            
             

                              
            
  
void FS_CreatePath (char *path)
{
	char *ofs, save;

	for (ofs = path+1 ; *ofs ; ofs++)
	{
		if (*ofs == '/' || *ofs == '\\')
		{
			                       
			save = *ofs;
			*ofs = 0;
			FS_mkdir (path);
			*ofs = save;
		}
	}
}


  
            
         

            
  
static void FS_Path_f (void)
{
	searchpath_t *s;

	Con_Print("Current search path:\n");
	for (s=fs_searchpaths ; s ; s=s->next)
	{
		if (s->pack)
		{
			if(s->pack->vpack)
				Con_Printf("%sdir (virtual pack)\n", s->pack->filename);
			else
				Con_Printf("%s (%i files)\n", s->pack->filename, s->pack->numfiles);
		}
		else
			Con_Printf("%s\n", s->filename);
	}
}


  
                 
              
                 
  
                                                                 
                                                                   
                                                   
   
static pack_t *FS_LoadPackPAK (const char *packfile)
{
	dpackheader_t header;
	int i, numpackfiles;
	filedesc_t packhandle;
	pack_t *pack;
	dpackfile_t *info;

	packhandle = FS_SysOpenFiledesc(packfile, "rb", false);
	if (!FILEDESC_ISVALID(packhandle))
		return NULL;
	if(FILEDESC_READ (packhandle, (void *)&header, sizeof(header)) != sizeof(header))
	{
		Con_Printf ("%s is not a packfile\n", packfile);
		FILEDESC_CLOSE(packhandle);
		return NULL;
	}
	if (memcmp(header.id, "PACK", 4))
	{
		Con_Printf ("%s is not a packfile\n", packfile);
		FILEDESC_CLOSE(packhandle);
		return NULL;
	}
	header.dirofs = LittleLong (header.dirofs);
	header.dirlen = LittleLong (header.dirlen);

	if (header.dirlen % sizeof(dpackfile_t))
	{
		Con_Printf ("%s has an invalid directory size\n", packfile);
		FILEDESC_CLOSE(packhandle);
		return NULL;
	}

	numpackfiles = header.dirlen / sizeof(dpackfile_t);

	if (numpackfiles < 0 || numpackfiles > MAX_FILES_IN_PACK)
	{
		Con_Printf ("%s has %i files\n", packfile, numpackfiles);
		FILEDESC_CLOSE(packhandle);
		return NULL;
	}

	info = (dpackfile_t *)Mem_Alloc(tempmempool, sizeof(*info) * numpackfiles);
	FILEDESC_SEEK (packhandle, header.dirofs, SEEK_SET);
	if(header.dirlen != FILEDESC_READ (packhandle, (void *)info, header.dirlen))
	{
		Con_Printf("%s is an incomplete PAK, not loading\n", packfile);
		Mem_Free(info);
		FILEDESC_CLOSE(packhandle);
		return NULL;
	}

	pack = (pack_t *)Mem_Alloc(fs_mempool, sizeof (pack_t));
	pack->ignorecase = true;                                                        
	strlcpy (pack->filename, packfile, sizeof (pack->filename));
	pack->handle = packhandle;
	pack->numfiles = 0;
	pack->files = (packfile_t *)Mem_Alloc(fs_mempool, numpackfiles * sizeof(packfile_t));

	                      
	for (i = 0;i < numpackfiles;i++)
	{
		fs_offset_t offset = (unsigned int)LittleLong (info[i].filepos);
		fs_offset_t size = (unsigned int)LittleLong (info[i].filelen);

		                                                           
		info[i].name[sizeof(info[i].name) - 1] = 0;

		FS_AddFileToPack (info[i].name, pack, offset, size, size, PACKFILE_FLAG_TRUEOFFS);
	}

	Mem_Free(info);

	Con_DPrintf("Added packfile %s (%i files)\n", packfile, numpackfiles);
	return pack;
}

  
                    
                  

                                                       
                    
  
static pack_t *FS_LoadPackVirtual (const char *dirname)
{
	pack_t *pack;
	pack = (pack_t *)Mem_Alloc(fs_mempool, sizeof (pack_t));
	pack->vpack = true;
	pack->ignorecase = false;
	strlcpy (pack->filename, dirname, sizeof(pack->filename));
	pack->handle = FILEDESC_INVALID;
	pack->numfiles = -1;
	pack->files = NULL;
	Con_DPrintf("Added packfile %s (virtual pack)\n", dirname);
	return pack;
}

  
                
                   
                
  
                                           
                                                       
  
                                                         
                                             
  
                                                                                
                     
  
   
static qboolean FS_AddPack_Fullpath(const char *pakfile, const char *shortname, qboolean *already_loaded, qboolean keep_plain_dirs)
{
	searchpath_t *search;
	pack_t *pak = NULL;
	const char *ext = FS_FileExtension(pakfile);
	size_t l;

	for(search = fs_searchpaths; search; search = search->next)
	{
		if(search->pack && !strcasecmp(search->pack->filename, pakfile))
		{
			if(already_loaded)
				*already_loaded = true;
			return true;                  
		}
	}

	if(already_loaded)
		*already_loaded = false;

	if(!strcasecmp(ext, "pk3dir"))
		pak = FS_LoadPackVirtual (pakfile);
	else if(!strcasecmp(ext, "pak"))
		pak = FS_LoadPackPAK (pakfile);
	else if(!strcasecmp(ext, "pk3"))
		pak = FS_LoadPackPK3 (pakfile);
	else if(!strcasecmp(ext, "obb"))                         
		pak = FS_LoadPackPK3 (pakfile);
	else
		Con_Printf("\"%s\" does not have a pack extension\n", pakfile);

	if(pak)
	{
		strlcpy(pak->shortname, shortname, sizeof(pak->shortname));

		                                                                   
		if(keep_plain_dirs)
		{
			                                                       
			searchpath_t *insertion_point = 0;
			if(fs_searchpaths && !fs_searchpaths->pack)
			{
				insertion_point = fs_searchpaths;
				for(;;)
				{
					if(!insertion_point->next)
						break;
					if(insertion_point->next->pack)
						break;
					insertion_point = insertion_point->next;
				}
			}
			                                                                 
			                                                                  
			                                                   
			if(!insertion_point)
			{
				search = (searchpath_t *)Mem_Alloc(fs_mempool, sizeof(searchpath_t));
				search->next = fs_searchpaths;
				fs_searchpaths = search;
			}
			else
			                                                              
			{
				search = (searchpath_t *)Mem_Alloc(fs_mempool, sizeof(searchpath_t));
				search->next = insertion_point->next;
				insertion_point->next = search;
			}
		}
		else
		{
			search = (searchpath_t *)Mem_Alloc(fs_mempool, sizeof(searchpath_t));
			search->next = fs_searchpaths;
			fs_searchpaths = search;
		}
		search->pack = pak;
		if(pak->vpack)
		{
			dpsnprintf(search->filename, sizeof(search->filename), "%s/", pakfile);
			                                                                           
			                                                   
			l = strlen(pak->shortname);
			if(l >= 7)
				if(!strcasecmp(pak->shortname + l - 7, ".pk3dir"))
					pak->shortname[l - 3] = 0;
			l = strlen(pak->filename);
			if(l >= 7)
				if(!strcasecmp(pak->filename + l - 7, ".pk3dir"))
					pak->filename[l - 3] = 0;
		}
		return true;
	}
	else
	{
		Con_Printf("unable to load pak \"%s\"\n", pakfile);
		return false;
	}
}


  
                
          
                
  
                                                                                
                                                       
  
                                                         
                                             
  
                                                                                
                     
   
qboolean FS_AddPack(const char *pakfile, qboolean *already_loaded, qboolean keep_plain_dirs)
{
	char fullpath[MAX_OSPATH];
	int index;
	searchpath_t *search;

	if(already_loaded)
		*already_loaded = false;

	                             
	search = FS_FindFile(pakfile, &index, true);
	if(!search || search->pack)
	{
		Con_Printf("could not find pak \"%s\"\n", pakfile);
		return false;
	}

	dpsnprintf(fullpath, sizeof(fullpath), "%s%s", search->filename, pakfile);

	return FS_AddPack_Fullpath(fullpath, pakfile, already_loaded, keep_plain_dirs);
}


  
                
                   

                                                            
                                         
                
  
static void FS_AddGameDirectory (const char *dir)
{
	int i;
	stringlist_t list;
	searchpath_t *search;

	strlcpy (fs_gamedir, dir, sizeof (fs_gamedir));

	stringlistinit(&list);
	listdirectory(&list, "", dir);
	stringlistsort(&list, false);

	                                       
	for (i = 0;i < list.numstrings;i++)
	{
		if (!strcasecmp(FS_FileExtension(list.strings[i]), "pak"))
		{
			FS_AddPack_Fullpath(list.strings[i], list.strings[i] + strlen(dir), NULL, false);
		}
	}

	                                       
	for (i = 0;i < list.numstrings;i++)
	{
		if (!strcasecmp(FS_FileExtension(list.strings[i]), "pk3") || !strcasecmp(FS_FileExtension(list.strings[i]), "obb") || !strcasecmp(FS_FileExtension(list.strings[i]), "pk3dir"))
		{
			FS_AddPack_Fullpath(list.strings[i], list.strings[i] + strlen(dir), NULL, false);
		}
	}

	stringlistfreecontents(&list);

	                                       
	                                                       
	search = (searchpath_t *)Mem_Alloc(fs_mempool, sizeof(searchpath_t));
	strlcpy (search->filename, dir, sizeof (search->filename));
	search->next = fs_searchpaths;
	fs_searchpaths = search;
}


  
                
                   
                
  
static void FS_AddGameHierarchy (const char *dir)
{
	char vabuf[1024];
	                                
	FS_AddGameDirectory (va(vabuf, sizeof(vabuf), "%s%s/", fs_basedir, dir));

	if (*fs_userdir)
		FS_AddGameDirectory(va(vabuf, sizeof(vabuf), "%s%s/", fs_userdir, dir));
}


  
            
                
            
  
const char *FS_FileExtension (const char *in)
{
	const char *separator, *backslash, *colon, *dot;

	separator = strrchr(in, '/');
	backslash = strrchr(in, '\\');
	if (!separator || separator < backslash)
		separator = backslash;
	colon = strrchr(in, ':');
	if (!separator || separator < colon)
		separator = colon;

	dot = strrchr(in, '.');
	if (dot == NULL || (separator && (dot < separator)))
		return "";

	return dot + 1;
}


  
            
                  
            
  
const char *FS_FileWithoutPath (const char *in)
{
	const char *separator, *backslash, *colon;

	separator = strrchr(in, '/');
	backslash = strrchr(in, '\\');
	if (!separator || separator < backslash)
		separator = backslash;
	colon = strrchr(in, ':');
	if (!separator || separator < colon)
		separator = colon;
	return separator ? separator + 1 : in;
}


  
                
                  
                
  
static void FS_ClearSearchPath (void)
{
	                                                                   
	                                                                         
	                                        
	while (fs_searchpaths)
	{
		searchpath_t *search = fs_searchpaths;
		fs_searchpaths = search->next;
		if (search->pack && search->pack != fs_selfpack)
		{
			if(!search->pack->vpack)
			{
				                 
				FILEDESC_CLOSE(search->pack->handle);
				                                     
				if (search->pack->files)
					Mem_Free(search->pack->files);
			}
			Mem_Free(search->pack);
		}
		Mem_Free(search);
	}
}

static void FS_AddSelfPack(void)
{
	if(fs_selfpack)
	{
		searchpath_t *search;
		search = (searchpath_t *)Mem_Alloc(fs_mempool, sizeof(searchpath_t));
		search->next = fs_searchpaths;
		search->pack = fs_selfpack;
		fs_searchpaths = search;
	}
}


  
                
         
                
  
void FS_Rescan (void)
{
	int i;
	qboolean fs_modified = false;
	qboolean reset = false;
	char gamedirbuf[MAX_INPUTLINE];
	char vabuf[1024];

	if (fs_searchpaths)
		reset = true;
	FS_ClearSearchPath();

	                                                             
	if (reset)
		COM_ChangeGameTypeForGameDirs();

	                              
	                               
	FS_AddGameHierarchy (gamedirname1);
	                                                
	if (gamedirname2 && gamedirname2[0])
		strlcpy(com_modname, gamedirname2, sizeof(com_modname));
	else
		strlcpy(com_modname, gamedirname1, sizeof(com_modname));

	                                     
	                                                                           
	if (gamedirname2 && gamedirname2[0])
	{
		fs_modified = true;
		FS_AddGameHierarchy (gamedirname2);
	}

	                  
	                                           
	                                                     
	                                                
	*gamedirbuf = 0;
	for (i = 0;i < fs_numgamedirs;i++)
	{
		fs_modified = true;
		FS_AddGameHierarchy (fs_gamedirs[i]);
		                                            
		strlcpy (com_modname, fs_gamedirs[i], sizeof (com_modname));
		if(i)
			strlcat(gamedirbuf, va(vabuf, sizeof(vabuf), " %s", fs_gamedirs[i]), sizeof(gamedirbuf));
		else
			strlcpy(gamedirbuf, fs_gamedirs[i], sizeof(gamedirbuf));
	}
	Cvar_SetQuick(&cvar_fs_gamedir, gamedirbuf);                                      

	                                          
	FS_AddSelfPack();

	                                                                
	                           
	if (strcmp(com_modname, gamedirname1))
		Cvar_SetQuick (&scr_screenshot_name, com_modname);
	else
		Cvar_SetQuick (&scr_screenshot_name, gamescreenshotname);
	
	if((i = COM_CheckParm("-modname")) && i < com_argc - 1)
		strlcpy(com_modname, com_argv[i+1], sizeof(com_modname));

	                                                                      
	if (COM_CheckParm ("-condebug") != 0)
		unlink (va(vabuf, sizeof(vabuf), "%s/qconsole.log", fs_gamedir));

	                                                                      
	if (FS_FileExists("gfx/pop.lmp"))
		Cvar_Set ("registered", "1");
	switch(gamemode)
	{
	case GAME_NORMAL:
	case GAME_HIPNOTIC:
	case GAME_ROGUE:
		if (!registered.integer)
		{
			if (fs_modified)
				Con_Print("Playing shareware version, with modification.\nwarning: most mods require full quake data.\n");
			else
				Con_Print("Playing shareware version.\n");
		}
		else
			Con_Print("Playing registered version.\n");
		break;
	case GAME_STEELSTORM:
		if (registered.integer)
			Con_Print("Playing registered version.\n");
		else
			Con_Print("Playing shareware version.\n");
		break;
	default:
		break;
	}

	                                                                  
	W_UnloadAll();
}

static void FS_Rescan_f(void)
{
	FS_Rescan();
}

  
                
                 
                
  
extern qboolean vid_opened;
qboolean FS_ChangeGameDirs(int numgamedirs, char gamedirs[][MAX_QPATH], qboolean complain, qboolean failmissing)
{
	int i;
	const char *p;

	if (fs_numgamedirs == numgamedirs)
	{
		for (i = 0;i < numgamedirs;i++)
			if (strcasecmp(fs_gamedirs[i], gamedirs[i]))
				break;
		if (i == numgamedirs)
			return true;                                                  
	}

	if (numgamedirs > MAX_GAMEDIRS)
	{
		if (complain)
			Con_Printf("That is too many gamedirs (%i > %i)\n", numgamedirs, MAX_GAMEDIRS);
		return false;                     
	}

	for (i = 0;i < numgamedirs;i++)
	{
		                                
		p = FS_CheckGameDir(gamedirs[i]);
		if(!p)
		{
			if (complain)
				Con_Printf("Nasty gamedir name rejected: %s\n", gamedirs[i]);
			return false;                  
		}
		if(p == fs_checkgamedir_missing && failmissing)
		{
			if (complain)
				Con_Printf("Gamedir missing: %s%s/\n", fs_basedir, gamedirs[i]);
			return false;                    
		}
	}

	Host_SaveConfig();

	fs_numgamedirs = numgamedirs;
	for (i = 0;i < fs_numgamedirs;i++)
		strlcpy(fs_gamedirs[i], gamedirs[i], sizeof(fs_gamedirs[i]));

	                                                 
	FS_Rescan();

	if (cls.demoplayback)
	{
		CL_Disconnect_f();
		cls.demonum = 0;
	}

	                                                                          
	S_UnloadAllSounds_f();

	                                                                                     
	VID_Stop();
	vid_opened = false;

	                                                           
	Cbuf_InsertText("\nloadconfig\nvid_restart\n\n");

	return true;
}

  
                
            
                
  
static void FS_GameDir_f (void)
{
	int i;
	int numgamedirs;
	char gamedirs[MAX_GAMEDIRS][MAX_QPATH];

	if (Cmd_Argc() < 2)
	{
		Con_Printf("gamedirs active:");
		for (i = 0;i < fs_numgamedirs;i++)
			Con_Printf(" %s", fs_gamedirs[i]);
		Con_Printf("\n");
		return;
	}

	numgamedirs = Cmd_Argc() - 1;
	if (numgamedirs > MAX_GAMEDIRS)
	{
		Con_Printf("Too many gamedirs (%i > %i)\n", numgamedirs, MAX_GAMEDIRS);
		return;
	}

	for (i = 0;i < numgamedirs;i++)
		strlcpy(gamedirs[i], Cmd_Argv(i+1), sizeof(gamedirs[i]));

	if ((cls.state == ca_connected && !cls.demoplayback) || sv.active)
	{
		                                                                      
		Con_Printf("Can not change gamedir while client is connected or server is running!\n");
		return;
	}

	                                       
	CL_Disconnect();

	FS_ChangeGameDirs(numgamedirs, gamedirs, true, true);
}

static const char *FS_SysCheckGameDir(const char *gamedir, char *buf, size_t buflength)
{
	qboolean success;
	qfile_t *f;
	stringlist_t list;
	fs_offset_t n;
	char vabuf[1024];

	stringlistinit(&list);
	listdirectory(&list, gamedir, "");
	success = list.numstrings > 0;
	stringlistfreecontents(&list);

	if(success)
	{
		f = FS_SysOpen(va(vabuf, sizeof(vabuf), "%smodinfo.txt", gamedir), "r", false);
		if(f)
		{
			n = FS_Read (f, buf, buflength - 1);
			if(n >= 0)
				buf[n] = 0;
			else
				*buf = 0;
			FS_Close(f);
		}
		else
			*buf = 0;
		return buf;
	}

	return NULL;
}

  
                
               
                
  
const char *FS_CheckGameDir(const char *gamedir)
{
	const char *ret;
	static char buf[8192];
	char vabuf[1024];

	if (FS_CheckNastyPath(gamedir, true))
		return NULL;

	ret = FS_SysCheckGameDir(va(vabuf, sizeof(vabuf), "%s%s/", fs_userdir, gamedir), buf, sizeof(buf));
	if(ret)
	{
		if(!*ret)
		{
			                               
			ret = FS_SysCheckGameDir(va(vabuf, sizeof(vabuf), "%s%s/", fs_basedir, gamedir), buf, sizeof(buf));
			if(ret)
				return ret;
			return "";
		}
		return ret;
	}

	ret = FS_SysCheckGameDir(va(vabuf, sizeof(vabuf), "%s%s/", fs_basedir, gamedir), buf, sizeof(buf));
	if(ret)
		return ret;
	
	return fs_checkgamedir_missing;
}

static void FS_ListGameDirs(void)
{
	stringlist_t list, list2;
	int i;
	const char *info;
	char vabuf[1024];

	fs_all_gamedirs_count = 0;
	if(fs_all_gamedirs)
		Mem_Free(fs_all_gamedirs);

	stringlistinit(&list);
	listdirectory(&list, va(vabuf, sizeof(vabuf), "%s/", fs_basedir), "");
	listdirectory(&list, va(vabuf, sizeof(vabuf), "%s/", fs_userdir), "");
	stringlistsort(&list, false);

	stringlistinit(&list2);
	for(i = 0; i < list.numstrings; ++i)
	{
		if(i)
			if(!strcmp(list.strings[i-1], list.strings[i]))
				continue;
		info = FS_CheckGameDir(list.strings[i]);
		if(!info)
			continue;
		if(info == fs_checkgamedir_missing)
			continue;
		if(!*info)
			continue;
		stringlistappend(&list2, list.strings[i]); 
	}
	stringlistfreecontents(&list);

	fs_all_gamedirs = (gamedir_t *)Mem_Alloc(fs_mempool, list2.numstrings * sizeof(*fs_all_gamedirs));
	for(i = 0; i < list2.numstrings; ++i)
	{
		info = FS_CheckGameDir(list2.strings[i]);
		                                                                 
		if(!info)
			continue;
		if(info == fs_checkgamedir_missing)
			continue;
		if(!*info)
			continue;
		strlcpy(fs_all_gamedirs[fs_all_gamedirs_count].name, list2.strings[i], sizeof(fs_all_gamedirs[fs_all_gamedirs_count].name));
		strlcpy(fs_all_gamedirs[fs_all_gamedirs_count].description, info, sizeof(fs_all_gamedirs[fs_all_gamedirs_count].description));
		++fs_all_gamedirs_count;
	}
}

  
            
                                   
                   
      
  

static void COM_InsertFlags(const char *buf) {
	const char *p;
	char *q;
	const char **new_argv;
	int i = 0;
	int args_left = 256;
	new_argv = (const char **)Mem_Alloc(fs_mempool, sizeof(*com_argv) * (com_argc + args_left + 2));
	if(com_argc == 0)
		new_argv[0] = "dummy";                         
	else
		new_argv[0] = com_argv[0];
	++i;
	p = buf;
	while(COM_ParseToken_Console(&p))
	{
		size_t sz = strlen(com_token) + 1;                 
		if(i > args_left)
			break;
		q = (char *)Mem_Alloc(fs_mempool, sz);
		strlcpy(q, com_token, sz);
		new_argv[i] = q;
		++i;
	}
	                           
	if (com_argc >= 1)
	{
		memcpy((char *)(&new_argv[i]), &com_argv[1], sizeof(*com_argv) * (com_argc - 1));
		i += com_argc - 1;
	}
	                                         
	new_argv[i] = NULL;
	com_argv = new_argv;
	com_argc = i;
}

  
                
                
                
  
void FS_Init_SelfPack (void)
{
	PK3_OpenLibrary ();
	fs_mempool = Mem_AllocPool("file management", 0, NULL);

	                                   
	if (!COM_CheckParm("-noopt"))
	{
		char *buf = (char *) FS_SysLoadFile("darkplaces.opt", tempmempool, true, NULL);
		if(buf)
			COM_InsertFlags(buf);
		Mem_Free(buf);
	}

#ifndef USE_RWOPS
	                        
	if (!COM_CheckParm("-noselfpack"))
	{
		if (com_selffd >= 0)
		{
			fs_selfpack = FS_LoadPackPK3FromFD(com_argv[0], com_selffd, true);
			if(fs_selfpack)
			{
				FS_AddSelfPack();
				if (!COM_CheckParm("-noopt"))
				{
					char *buf = (char *) FS_LoadFile("darkplaces.opt", tempmempool, true, NULL);
					if(buf)
						COM_InsertFlags(buf);
					Mem_Free(buf);
				}
			}
		}
	}
#endif
}

static int FS_ChooseUserDir(userdirmode_t userdirmode, char *userdir, size_t userdirsize)
{
#if defined(__IPHONEOS__)
	if (userdirmode == USERDIRMODE_HOME)
	{
		                                                                                                         
		                                                                      
		strlcpy(userdir, "../Documents/", MAX_OSPATH);
		return 1;
	}
	return -1;

#elif defined(WIN32)
	char *homedir;
#if _MSC_VER >= 1400
	size_t homedirlen;
#endif
	TCHAR mydocsdir[MAX_PATH + 1];
	wchar_t *savedgamesdirw;
	char savedgamesdir[MAX_OSPATH];
	int fd;
	char vabuf[1024];

	userdir[0] = 0;
	switch(userdirmode)
	{
	default:
		return -1;
	case USERDIRMODE_NOHOME:
		strlcpy(userdir, fs_basedir, userdirsize);
		break;
	case USERDIRMODE_MYGAMES:
		if (!shfolder_dll)
			Sys_LoadLibrary(shfolderdllnames, &shfolder_dll, shfolderfuncs);
		mydocsdir[0] = 0;
		if (qSHGetFolderPath && qSHGetFolderPath(NULL, CSIDL_PERSONAL, NULL, 0, mydocsdir) == S_OK)
		{
			dpsnprintf(userdir, userdirsize, "%s/My Games/%s/", mydocsdir, gameuserdirname);
			break;
		}
#if _MSC_VER >= 1400
		_dupenv_s(&homedir, &homedirlen, "USERPROFILE");
		if(homedir)
		{
			dpsnprintf(userdir, userdirsize, "%s/.%s/", homedir, gameuserdirname);
			free(homedir);
			break;
		}
#else
		homedir = getenv("USERPROFILE");
		if(homedir)
		{
			dpsnprintf(userdir, userdirsize, "%s/.%s/", homedir, gameuserdirname);
			break;
		}
#endif
		return -1;
	case USERDIRMODE_SAVEDGAMES:
		if (!shell32_dll)
			Sys_LoadLibrary(shell32dllnames, &shell32_dll, shell32funcs);
		if (!ole32_dll)
			Sys_LoadLibrary(ole32dllnames, &ole32_dll, ole32funcs);
		if (qSHGetKnownFolderPath && qCoInitializeEx && qCoTaskMemFree && qCoUninitialize)
		{
			savedgamesdir[0] = 0;
			qCoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
  
                  
                                                                                                                   
     
                                                                                                                    
      
  
			if (qSHGetKnownFolderPath(&qFOLDERID_SavedGames, qKF_FLAG_CREATE | qKF_FLAG_NO_ALIAS, NULL, &savedgamesdirw) == S_OK)
			{
				memset(savedgamesdir, 0, sizeof(savedgamesdir));
#if _MSC_VER >= 1400
				wcstombs_s(NULL, savedgamesdir, sizeof(savedgamesdir), savedgamesdirw, sizeof(savedgamesdir)-1);
#else
				wcstombs(savedgamesdir, savedgamesdirw, sizeof(savedgamesdir)-1);
#endif
				qCoTaskMemFree(savedgamesdirw);
			}
			qCoUninitialize();
			if (savedgamesdir[0])
			{
				dpsnprintf(userdir, userdirsize, "%s/%s/", savedgamesdir, gameuserdirname);
				break;
			}
		}
		return -1;
	}
#else
	int fd;
	char *homedir;
	char vabuf[1024];
	userdir[0] = 0;
	switch(userdirmode)
	{
	default:
		return -1;
	case USERDIRMODE_NOHOME:
		strlcpy(userdir, fs_basedir, userdirsize);
		break;
	case USERDIRMODE_HOME:
		homedir = getenv("HOME");
		if(homedir)
		{
			dpsnprintf(userdir, userdirsize, "%s/.%s/", homedir, gameuserdirname);
			break;
		}
		return -1;
	case USERDIRMODE_SAVEDGAMES:
		homedir = getenv("HOME");
		if(homedir)
		{
#ifdef MACOSX
			dpsnprintf(userdir, userdirsize, "%s/Library/Application Support/%s/", homedir, gameuserdirname);
#else
			                                              
			                                     
			                                        
			                                   
			                                                             
			                                          
			                                          
			                                   
			return -1;
#endif
			break;
		}
		return -1;
	}
#endif


#if !defined(__IPHONEOS__)

#ifdef WIN32
	                         
	if (userdirmode == USERDIRMODE_NOHOME && strcmp(gamedirname1, "id1"))
		return 0;                                                                                                                                                                                         
#endif

	                                                             
#ifdef WIN32
	                                                               
	fd = FS_SysOpenFiledesc(va(vabuf, sizeof(vabuf), "%s%s/config.cfg", userdir, gamedirname1), "a", false);
	if(fd >= 0)
		FILEDESC_CLOSE(fd);
#else
	                                                              
	if(access(va(vabuf, sizeof(vabuf), "%s%s/", userdir, gamedirname1), W_OK | X_OK) >= 0)
		fd = 1;
	else
		fd = -1;
#endif
	if(fd >= 0)
	{
		return 1;                                                 
	}
	else
	{
		if (userdirmode == USERDIRMODE_NOHOME)
			return -1;                                                    
		else
			return 0;                                                                    
	}
#endif
}

  
                
       
                
  
void FS_Init (void)
{
	const char *p;
	int i;

	*fs_basedir = 0;
	*fs_userdir = 0;
	*fs_gamedir = 0;

	                  
	                                                                
                                                                                                                                                                              
	i = COM_CheckParm ("-basedir");
	if (i && i < com_argc-1)
	{
		strlcpy (fs_basedir, com_argv[i+1], sizeof (fs_basedir));
		i = (int)strlen (fs_basedir);
		if (i > 0 && (fs_basedir[i-1] == '\\' || fs_basedir[i-1] == '/'))
			fs_basedir[i-1] = 0;
	}
	else
	{
                                                                         
#ifdef DP_FS_BASEDIR
		strlcpy(fs_basedir, DP_FS_BASEDIR, sizeof(fs_basedir));
#elif defined(__ANDROID__)
		dpsnprintf(fs_basedir, sizeof(fs_basedir), "/sdcard/%s/", gameuserdirname);
#elif defined(MACOSX)
		                                                                                                  
		if (strstr(com_argv[0], ".app/"))
		{
			char *split;
			strlcpy(fs_basedir, com_argv[0], sizeof(fs_basedir));
			split = strstr(fs_basedir, ".app/");
			if (split)
			{
				struct stat statresult;
				char vabuf[1024];
				                                   
				split[5] = 0;
				                                     
				if (stat(va(vabuf, sizeof(vabuf), "%s/Contents/Resources/%s", fs_basedir, gamedirname1), &statresult) == 0)
				{
					                                         
					strlcat(fs_basedir, "Contents/Resources/", sizeof(fs_basedir));
				}
				else
				{
					                                                     
					                                             
					while (split > fs_basedir && *split != '/')
						split--;
					*split = 0;
				}
			}
		}
#endif
	}

	                                                                                  
	memset(fs_basedir + sizeof(fs_basedir) - 2, 0, 2);
	                                                                 
	if (fs_basedir[0] && fs_basedir[strlen(fs_basedir) - 1] != '/' && fs_basedir[strlen(fs_basedir) - 1] != '\\')
		strlcat(fs_basedir, "/", sizeof(fs_basedir));

	                                  
	if((i = COM_CheckParm("-userdir")) && i < com_argc - 1)
		dpsnprintf(fs_userdir, sizeof(fs_userdir), "%s/", com_argv[i+1]);
	else if (COM_CheckParm("-nohome"))
		*fs_userdir = 0;                                               
	else
	{
#ifdef DP_FS_USERDIR
		strlcpy(fs_userdir, DP_FS_USERDIR, sizeof(fs_userdir));
#else
		int dirmode;
		int highestuserdirmode = USERDIRMODE_COUNT - 1;
		int preferreduserdirmode = USERDIRMODE_COUNT - 1;
		int userdirstatus[USERDIRMODE_COUNT];
# ifdef WIN32
		                         
		if (!strcmp(gamedirname1, "id1"))
			preferreduserdirmode = USERDIRMODE_NOHOME;
# endif
		                                                  
		if (COM_CheckParm("-home")) preferreduserdirmode = USERDIRMODE_HOME;
		if (COM_CheckParm("-mygames")) preferreduserdirmode = USERDIRMODE_MYGAMES;
		if (COM_CheckParm("-savedgames")) preferreduserdirmode = USERDIRMODE_SAVEDGAMES;
		                                             
		for (dirmode = 0;dirmode < USERDIRMODE_COUNT;dirmode++)
		{
			userdirstatus[dirmode] = FS_ChooseUserDir((userdirmode_t)dirmode, fs_userdir, sizeof(fs_userdir));
			if (userdirstatus[dirmode] == 1)
				Con_DPrintf("userdir %i = %s (writable)\n", dirmode, fs_userdir);
			else if (userdirstatus[dirmode] == 0)
				Con_DPrintf("userdir %i = %s (not writable or does not exist)\n", dirmode, fs_userdir);
			else
				Con_DPrintf("userdir %i (not applicable)\n", dirmode);
		}
		                                                                  
		                                       
		if (preferreduserdirmode == 0 && userdirstatus[0] < 1)
			preferreduserdirmode = highestuserdirmode;
		                                                                     
		for (dirmode = USERDIRMODE_COUNT - 1;dirmode > 0;dirmode--)
			if (userdirstatus[dirmode] == 1)
				break;
		                                                  
		if (dirmode == 0 && preferreduserdirmode > 0)
			for (dirmode = preferreduserdirmode;dirmode > 0;dirmode--)
				if (userdirstatus[dirmode] >= 0)
					break;
		                                
		FS_ChooseUserDir((userdirmode_t)dirmode, fs_userdir, sizeof(fs_userdir));
		Con_DPrintf("userdir %i is the winner\n", dirmode);
#endif
	}

	                                                                 
	if (!strcmp(fs_basedir, fs_userdir))
		fs_userdir[0] = 0;

	FS_ListGameDirs();

	p = FS_CheckGameDir(gamedirname1);
	if(!p || p == fs_checkgamedir_missing)
		Con_Printf("WARNING: base gamedir %s%s/ not found!\n", fs_basedir, gamedirname1);

	if(gamedirname2)
	{
		p = FS_CheckGameDir(gamedirname2);
		if(!p || p == fs_checkgamedir_missing)
			Con_Printf("WARNING: base gamedir %s%s/ not found!\n", fs_basedir, gamedirname2);
	}

	                  
	                                           
	                                                     
	for (i = 1;i < com_argc && fs_numgamedirs < MAX_GAMEDIRS;i++)
	{
		if (!com_argv[i])
			continue;
		if (!strcmp (com_argv[i], "-game") && i < com_argc-1)
		{
			i++;
			p = FS_CheckGameDir(com_argv[i]);
			if(!p)
				Sys_Error("Nasty -game name rejected: %s", com_argv[i]);
			if(p == fs_checkgamedir_missing)
				Con_Printf("WARNING: -game %s%s/ not found!\n", fs_basedir, com_argv[i]);
			                                                 
			strlcpy (fs_gamedirs[fs_numgamedirs], com_argv[i], sizeof(fs_gamedirs[fs_numgamedirs]));
			fs_numgamedirs++;
		}
	}

	                          
	FS_Rescan();

	if (Thread_HasThreads())
		fs_mutex = Thread_CreateMutex();
}

void FS_Init_Commands(void)
{
	Cvar_RegisterVariable (&scr_screenshot_name);
	Cvar_RegisterVariable (&fs_empty_files_in_pack_mark_deletions);
	Cvar_RegisterVariable (&cvar_fs_gamedir);

	Cmd_AddCommand ("gamedir", FS_GameDir_f, "changes active gamedir list (can take multiple arguments), not including base directory (example usage: gamedir ctf)");
	Cmd_AddCommand ("fs_rescan", FS_Rescan_f, "rescans filesystem for new pack archives and any other changes");
	Cmd_AddCommand ("path", FS_Path_f, "print searchpath (game directories and archives)");
	Cmd_AddCommand ("dir", FS_Dir_f, "list files in searchpath matching an * filename pattern, one per line");
	Cmd_AddCommand ("ls", FS_Ls_f, "list files in searchpath matching an * filename pattern, multiple per line");
	Cmd_AddCommand ("which", FS_Which_f, "accepts a file name as argument and reports where the file is taken from");
}

  
                
           
                
  
void FS_Shutdown (void)
{
	                                
	                                                                          
	                     
	FS_ClearSearchPath();
	Mem_FreePool (&fs_mempool);
	PK3_CloseLibrary ();

#ifdef WIN32
	Sys_UnloadLibrary (&shfolder_dll);
	Sys_UnloadLibrary (&shell32_dll);
	Sys_UnloadLibrary (&ole32_dll);
#endif

	if (fs_mutex)
		Thread_DestroyMutex(fs_mutex);
}

static filedesc_t FS_SysOpenFiledesc(const char *filepath, const char *mode, qboolean nonblocking)
{
	filedesc_t handle = FILEDESC_INVALID;
	int mod, opt;
	unsigned int ind;
	qboolean dolock = false;

	                        
	switch (mode[0])
	{
		case 'r':
			mod = O_RDONLY;
			opt = 0;
			break;
		case 'w':
			mod = O_WRONLY;
			opt = O_CREAT | O_TRUNC;
			break;
		case 'a':
			mod = O_WRONLY;
			opt = O_CREAT | O_APPEND;
			break;
		default:
			Con_Printf ("FS_SysOpen(%s, %s): invalid mode\n", filepath, mode);
			return FILEDESC_INVALID;
	}
	for (ind = 1; mode[ind] != '\0'; ind++)
	{
		switch (mode[ind])
		{
			case '+':
				mod = O_RDWR;
				break;
			case 'b':
				opt |= O_BINARY;
				break;
			case 'l':
				dolock = true;
				break;
			default:
				Con_Printf ("FS_SysOpen(%s, %s): unknown character in mode (%c)\n",
							filepath, mode, mode[ind]);
		}
	}

	if (nonblocking)
		opt |= O_NONBLOCK;

	if(COM_CheckParm("-readonly") && mod != O_RDONLY)
		return FILEDESC_INVALID;

#if USE_RWOPS
	if (dolock)
		return FILEDESC_INVALID;
	handle = SDL_RWFromFile(filepath, mode);
#else
# ifdef WIN32
#  if _MSC_VER >= 1400
	_sopen_s(&handle, filepath, mod | opt, (dolock ? ((mod == O_RDONLY) ? _SH_DENYRD : _SH_DENYRW) : _SH_DENYNO), _S_IREAD | _S_IWRITE);
#  else
	handle = _sopen (filepath, mod | opt, (dolock ? ((mod == O_RDONLY) ? _SH_DENYRD : _SH_DENYRW) : _SH_DENYNO), _S_IREAD | _S_IWRITE);
#  endif
# else
	handle = open (filepath, mod | opt, 0666);
	if(handle >= 0 && dolock)
	{
		struct flock l;
		l.l_type = ((mod == O_RDONLY) ? F_RDLCK : F_WRLCK);
		l.l_whence = SEEK_SET;
		l.l_start = 0;
		l.l_len = 0;
		if(fcntl(handle, F_SETLK, &l) == -1)
		{
			FILEDESC_CLOSE(handle);
			handle = -1;
		}
	}
# endif
#endif

	return handle;
}

int FS_SysOpenFD(const char *filepath, const char *mode, qboolean nonblocking)
{
#ifdef USE_RWOPS
	return -1;
#else
	return FS_SysOpenFiledesc(filepath, mode, nonblocking);
#endif
}

  
                    
          

                                                                                        
                    
  
qfile_t* FS_SysOpen (const char* filepath, const char* mode, qboolean nonblocking)
{
	qfile_t* file;

	file = (qfile_t *)Mem_Alloc (fs_mempool, sizeof (*file));
	file->ungetc = EOF;
	file->handle = FS_SysOpenFiledesc(filepath, mode, nonblocking);
	if (!FILEDESC_ISVALID(file->handle))
	{
		Mem_Free (file);
		return NULL;
	}

	file->filename = Mem_strdup(fs_mempool, filepath);

	file->real_length = FILEDESC_SEEK (file->handle, 0, SEEK_END);

	                                                                   
	if (mode[0] == 'a')
		file->position = file->real_length;
	else
		FILEDESC_SEEK (file->handle, 0, SEEK_SET);

	return file;
}


  
           
                 

                                                    
           
  
static qfile_t *FS_OpenPackedFile (pack_t* pack, int pack_ind)
{
	packfile_t *pfile;
	filedesc_t dup_handle;
	qfile_t* file;

	pfile = &pack->files[pack_ind];

	                                               
	if (! (pfile->flags & PACKFILE_FLAG_TRUEOFFS))
		if (!PK3_GetTrueFileOffset (pfile, pack))
			return NULL;

#ifndef LINK_TO_ZLIB
	                                    
	if (!zlib_dll && (pfile->flags & PACKFILE_FLAG_DEFLATED))
	{
		Con_Printf("WARNING: can't open the compressed file %s\n"
					"You need the Zlib DLL to use compressed files\n",
					pfile->name);
		return NULL;
	}
#endif

	                                                                                 
	                                                                       
	if (FILEDESC_SEEK (pack->handle, pfile->offset, SEEK_SET) == -1)
	{
		Con_Printf ("FS_OpenPackedFile: can't lseek to %s in %s (offset: %08x%08x)\n",
					pfile->name, pack->filename, (unsigned int)(pfile->offset >> 32), (unsigned int)(pfile->offset));
		return NULL;
	}

	dup_handle = FILEDESC_DUP (pack->filename, pack->handle);
	if (!FILEDESC_ISVALID(dup_handle))
	{
		Con_Printf ("FS_OpenPackedFile: can't dup package's handle (pack: %s)\n", pack->filename);
		return NULL;
	}

	file = (qfile_t *)Mem_Alloc (fs_mempool, sizeof (*file));
	memset (file, 0, sizeof (*file));
	file->handle = dup_handle;
	file->flags = QFILE_FLAG_PACKED;
	file->real_length = pfile->realsize;
	file->offset = pfile->offset;
	file->position = 0;
	file->ungetc = EOF;

	if (pfile->flags & PACKFILE_FLAG_DEFLATED)
	{
		ztoolkit_t *ztk;

		file->flags |= QFILE_FLAG_DEFLATED;

		                              
		ztk = (ztoolkit_t *)Mem_Alloc (fs_mempool, sizeof (*ztk));

		ztk->comp_length = pfile->packsize;

		                         
		ztk->zstream.next_in = ztk->input;
		ztk->zstream.avail_in = 0;

		                         
    
                                                                   
                                                                    
                                                                       
                         
                                                                       
                                                  
     
		if (qz_inflateInit2 (&ztk->zstream, -MAX_WBITS) != Z_OK)
		{
			Con_Printf ("FS_OpenPackedFile: inflate init error (file: %s)\n", pfile->name);
			FILEDESC_CLOSE(dup_handle);
			Mem_Free(file);
			return NULL;
		}

		ztk->zstream.next_out = file->buff;
		ztk->zstream.avail_out = sizeof (file->buff);

		file->ztk = ztk;
	}

	return file;
}

  
                    
                 

                                                                       
                                      
                                                                             
                                                     
                    
  
int FS_CheckNastyPath (const char *path, qboolean isgamedir)
{
	                                                                                                                                
	if (!path[0])
		return 2;

	                                                              
	                                                                   
	if (strstr(path, "\\"))
		return 1;                

	                                                                   
	                                                                          
	                          
	                                                    
	if (strstr(path, ":"))
		return 1;                                               

	                                
	if (strstr(path, "//"))
		return 1;                                                  

	                                                           
	if (strstr(path, ".."))
		return 2;                                            

	                                                 
	if (path[0] == '/')
		return 2;                                            

	                                                                                                                   
	if (strstr(path, "./"))
		return 2;                                                     

	                                        
	if (isgamedir && path[strlen(path)-1] == '/')
		return 2;

	                                                         
	if (strstr(path, "/."))
		return 2;                                            

	                                                                       
	                                
	return false;
}


  
                    
           

                                                     

                                                        
                                             
                    
  
static searchpath_t *FS_FindFile (const char *name, int* index, qboolean quiet)
{
	searchpath_t *search;
	pack_t *pak;

	                                                 
	for (search = fs_searchpaths;search;search = search->next)
	{
		                             
		if (search->pack && !search->pack->vpack)
		{
			int (*strcmp_funct) (const char* str1, const char* str2);
			int left, right, middle;

			pak = search->pack;
			strcmp_funct = pak->ignorecase ? strcasecmp : strcmp;

			                                    
			left = 0;
			right = pak->numfiles - 1;
			while (left <= right)
			{
				int diff;

				middle = (left + right) / 2;
				diff = strcmp_funct (pak->files[middle].name, name);

				           
				if (!diff)
				{
					if (fs_empty_files_in_pack_mark_deletions.integer && pak->files[middle].realsize == 0)
					{
						                                                                    
						if (!quiet && developer_extra.integer)
							Con_DPrintf("FS_FindFile: %s is marked as deleted\n", name);

						if (index != NULL)
							*index = -1;
						return NULL;
					}

					if (!quiet && developer_extra.integer)
						Con_DPrintf("FS_FindFile: %s in %s\n",
									pak->files[middle].name, pak->filename);

					if (index != NULL)
						*index = middle;
					return search;
				}

				                               
				if (diff > 0)
					right = middle - 1;
				else
					left = middle + 1;
			}
		}
		else
		{
			char netpath[MAX_OSPATH];
			dpsnprintf(netpath, sizeof(netpath), "%s%s", search->filename, name);
			if (FS_SysFileExists (netpath))
			{
				if (!quiet && developer_extra.integer)
					Con_DPrintf("FS_FindFile: %s\n", netpath);

				if (index != NULL)
					*index = -1;
				return search;
			}
		}
	}

	if (!quiet && developer_extra.integer)
		Con_DPrintf("FS_FindFile: can't find %s\n", name);

	if (index != NULL)
		*index = -1;
	return NULL;
}


  
           
               

                                                                 
           
  
static qfile_t *FS_OpenReadFile (const char *filename, qboolean quiet, qboolean nonblocking, int symlinkLevels)
{
	searchpath_t *search;
	int pack_ind;

	search = FS_FindFile (filename, &pack_ind, quiet);

	             
	if (search == NULL)
		return NULL;

	                           
	if (pack_ind < 0)
	{
		                                         
		char path [MAX_OSPATH];
		dpsnprintf (path, sizeof (path), "%s%s", search->filename, filename);
		return FS_SysOpen (path, "rb", nonblocking);
	}

	                                  

	                       
	                                                                        
	                                                  
	if(search->pack->files[pack_ind].flags & PACKFILE_FLAG_SYMLINK)
	{
		if(symlinkLevels <= 0)
		{
			Con_Printf("symlink: %s: too many levels of symbolic links\n", filename);
			return NULL;
		}
		else
		{
			char linkbuf[MAX_QPATH];
			fs_offset_t count;
			qfile_t *linkfile = FS_OpenPackedFile (search->pack, pack_ind);
			const char *mergeslash;
			char *mergestart;

			if(!linkfile)
				return NULL;
			count = FS_Read(linkfile, linkbuf, sizeof(linkbuf) - 1);
			FS_Close(linkfile);
			if(count < 0)
				return NULL;
			linkbuf[count] = 0;
			
			                           
			mergeslash = strrchr(filename, '/');
			mergestart = linkbuf;
			if(!mergeslash)
				mergeslash = filename;
			while(!strncmp(mergestart, "../", 3))
			{
				mergestart += 3;
				while(mergeslash > filename)
				{
					--mergeslash;
					if(*mergeslash == '/')
						break;
				}
			}
			                                                                                                              
			if(mergeslash == filename)
			{
				                                                                            
			}
			else
			{
				                                           
				                                                                                                         
				int spaceNeeded = mergeslash - filename + 1;
				int spaceRemoved = mergestart - linkbuf;
				if(count - spaceRemoved + spaceNeeded >= MAX_QPATH)
				{
					Con_DPrintf("symlink: too long path rejected\n");
					return NULL;
				}
				memmove(linkbuf + spaceNeeded, linkbuf + spaceRemoved, count - spaceRemoved);
				memcpy(linkbuf, filename, spaceNeeded);
				linkbuf[count - spaceRemoved + spaceNeeded] = 0;
				mergestart = linkbuf;
			}
			if (!quiet && developer_loading.integer)
				Con_DPrintf("symlink: %s -> %s\n", filename, mergestart);
			if(FS_CheckNastyPath (mergestart, false))
			{
				Con_DPrintf("symlink: nasty path %s rejected\n", mergestart);
				return NULL;
			}
			return FS_OpenReadFile(mergestart, quiet, nonblocking, symlinkLevels - 1);
		}
	}

	return FS_OpenPackedFile (search->pack, pack_ind);
}


  
                                                                             

                     

                                                                             
  

  
                    
               

                                                            
                                                         
                    
  
qfile_t* FS_OpenRealFile (const char* filepath, const char* mode, qboolean quiet)
{
	char real_path [MAX_OSPATH];

	if (FS_CheckNastyPath(filepath, false))
	{
		Con_Printf("FS_OpenRealFile(\"%s\", \"%s\", %s): nasty filename rejected\n", filepath, mode, quiet ? "true" : "false");
		return NULL;
	}

	dpsnprintf (real_path, sizeof (real_path), "%s/%s", fs_gamedir, filepath);                         

	                                                                    
	                                     
	if (mode[0] == 'w' || mode[0] == 'a' || strchr (mode, '+'))
		FS_CreatePath (real_path);
	return FS_SysOpen (real_path, mode, false);
}


  
                    
                  

                                            
                    
  
qfile_t* FS_OpenVirtualFile (const char* filepath, qboolean quiet)
{
	qfile_t *result = NULL;
	if (FS_CheckNastyPath(filepath, false))
	{
		Con_Printf("FS_OpenVirtualFile(\"%s\", %s): nasty filename rejected\n", filepath, quiet ? "true" : "false");
		return NULL;
	}

	if (fs_mutex) Thread_LockMutex(fs_mutex);
	result = FS_OpenReadFile (filepath, quiet, false, 16);
	if (fs_mutex) Thread_UnlockMutex(fs_mutex);
	return result;
}


  
                    
               

                                            
                    
  
qfile_t* FS_FileFromData (const unsigned char *data, const size_t size, qboolean quiet)
{
	qfile_t* file;
	file = (qfile_t *)Mem_Alloc (fs_mempool, sizeof (*file));
	memset (file, 0, sizeof (*file));
	file->flags = QFILE_FLAG_DATA;
	file->ungetc = EOF;
	file->real_length = size;
	file->data = data;
	return file;
}

  
                    
        

            
                    
  
int FS_Close (qfile_t* file)
{
	if(file->flags & QFILE_FLAG_DATA)
	{
		Mem_Free(file);
		return 0;
	}

	if (FILEDESC_CLOSE (file->handle))
		return EOF;

	if (file->filename)
	{
		if (file->flags & QFILE_FLAG_REMOVE)
		{
			if (remove(file->filename) == -1)
			{
				                                             
				                                              
				                                           
				        
			}
		}

		Mem_Free((void *) file->filename);
	}

	if (file->ztk)
	{
		qz_inflateEnd (&file->ztk->zstream);
		Mem_Free (file->ztk);
	}

	Mem_Free (file);
	return 0;
}

void FS_RemoveOnClose(qfile_t* file)
{
	file->flags |= QFILE_FLAG_REMOVE;
}

  
                    
        

                                  
                    
  
fs_offset_t FS_Write (qfile_t* file, const void* data, size_t datasize)
{
	fs_offset_t written = 0;

	                                                                     
	if (file->buff_ind != file->buff_len)
	{
		if (FILEDESC_SEEK (file->handle, file->buff_ind - file->buff_len, SEEK_CUR) == -1)
		{
			Con_Printf("WARNING: could not seek in %s.\n", file->filename);
		}
	}

	                    
	FS_Purge (file);

	                                           
	                                                                                                                                                                                                                           
	while (written < (fs_offset_t)datasize)
	{
		                                            
		fs_offset_t maxchunk = 1<<30;         
		int chunk = (int)min((fs_offset_t)datasize - written, maxchunk);
		int result = (int)FILEDESC_WRITE (file->handle, (const unsigned char *)data + written, chunk);
		                                                          
		if (result > 0)
			written += result;
		                                                                             
		if (result != chunk)
			break;
	}
	file->position = FILEDESC_SEEK (file->handle, 0, SEEK_CUR);
	if (file->real_length < file->position)
		file->real_length = file->position;

	                                                                    
	return written;
}


  
                    
       

                                         
                    
  
fs_offset_t FS_Read (qfile_t* file, void* buffer, size_t buffersize)
{
	fs_offset_t count, done;

	if (buffersize == 0)
		return 0;

	                                  
	if (file->ungetc != EOF)
	{
		((char*)buffer)[0] = file->ungetc;
		buffersize--;
		file->ungetc = EOF;
		done = 1;
	}
	else
		done = 0;

	if(file->flags & QFILE_FLAG_DATA)
	{
		size_t left = file->real_length - file->position;
		if(buffersize > left)
			buffersize = left;
		memcpy(buffer, file->data + file->position, buffersize);
		file->position += buffersize;
		return buffersize;
	}

	                                                     
	if (file->buff_ind < file->buff_len)
	{
		count = file->buff_len - file->buff_ind;
		count = ((fs_offset_t)buffersize > count) ? count : (fs_offset_t)buffersize;
		done += count;
		memcpy (buffer, &file->buff[file->buff_ind], count);
		file->buff_ind += count;

		buffersize -= count;
		if (buffersize == 0)
			return done;
	}

	                                                       

	                               
	if (! (file->flags & QFILE_FLAG_DEFLATED))
	{
		fs_offset_t nb;

		                                                          
		count = file->real_length - file->position;

		                                                                   
		if (buffersize > sizeof (file->buff) / 2)
		{
			if (count > (fs_offset_t)buffersize)
				count = (fs_offset_t)buffersize;
			if (FILEDESC_SEEK (file->handle, file->offset + file->position, SEEK_SET) == -1)
			{
				                                             
				                                              
				                                           
			}
			nb = FILEDESC_READ (file->handle, &((unsigned char*)buffer)[done], count);
			if (nb > 0)
			{
				done += nb;
				file->position += nb;

				                    
				FS_Purge (file);
			}
		}
		else
		{
			if (count > (fs_offset_t)sizeof (file->buff))
				count = (fs_offset_t)sizeof (file->buff);
			if (FILEDESC_SEEK (file->handle, file->offset + file->position, SEEK_SET) == -1)
			{
				                                             
				                                              
				                                           
			}
			nb = FILEDESC_READ (file->handle, file->buff, count);
			if (nb > 0)
			{
				file->buff_len = nb;
				file->position += nb;

				                                                          
				count = (fs_offset_t)buffersize > file->buff_len ? file->buff_len : (fs_offset_t)buffersize;
				memcpy (&((unsigned char*)buffer)[done], file->buff, count);
				file->buff_ind = count;
				done += count;
			}
		}

		return done;
	}

	                                                      
	                                                                   
	while (buffersize > 0)
	{
		ztoolkit_t *ztk = file->ztk;
		int error;

		                                                       

		                                                 
		if (ztk->in_ind == ztk->in_len)
		{
			                                   
			if (file->position == file->real_length)
				return done;

			count = (fs_offset_t)(ztk->comp_length - ztk->in_position);
			if (count > (fs_offset_t)sizeof (ztk->input))
				count = (fs_offset_t)sizeof (ztk->input);
			FILEDESC_SEEK (file->handle, file->offset + (fs_offset_t)ztk->in_position, SEEK_SET);
			if (FILEDESC_READ (file->handle, ztk->input, count) != count)
			{
				Con_Printf ("FS_Read: unexpected end of file\n");
				break;
			}

			ztk->in_ind = 0;
			ztk->in_len = count;
			ztk->in_position += count;
		}

		ztk->zstream.next_in = &ztk->input[ztk->in_ind];
		ztk->zstream.avail_in = (unsigned int)(ztk->in_len - ztk->in_ind);

		                                                                               
		                                                                       

		                                   
		if (buffersize < sizeof (file->buff) / 2)
		{
			ztk->zstream.next_out = file->buff;
			ztk->zstream.avail_out = sizeof (file->buff);
			error = qz_inflate (&ztk->zstream, Z_SYNC_FLUSH);
			if (error != Z_OK && error != Z_STREAM_END)
			{
				Con_Printf ("FS_Read: Can't inflate file\n");
				break;
			}
			ztk->in_ind = ztk->in_len - ztk->zstream.avail_in;

			file->buff_len = (fs_offset_t)sizeof (file->buff) - ztk->zstream.avail_out;
			file->position += file->buff_len;

			                                                          
			count = (fs_offset_t)buffersize > file->buff_len ? file->buff_len : (fs_offset_t)buffersize;
			memcpy (&((unsigned char*)buffer)[done], file->buff, count);
			file->buff_ind = count;
		}

		                                        
		else
		{
			ztk->zstream.next_out = &((unsigned char*)buffer)[done];
			ztk->zstream.avail_out = (unsigned int)buffersize;
			error = qz_inflate (&ztk->zstream, Z_SYNC_FLUSH);
			if (error != Z_OK && error != Z_STREAM_END)
			{
				Con_Printf ("FS_Read: Can't inflate file\n");
				break;
			}
			ztk->in_ind = ztk->in_len - ztk->zstream.avail_in;

			                                
			count = (fs_offset_t)(buffersize - ztk->zstream.avail_out);
			file->position += count;

			                    
			FS_Purge (file);
		}

		done += count;
		buffersize -= count;
	}

	return done;
}


  
                    
        

                          
                    
  
int FS_Print (qfile_t* file, const char *msg)
{
	return (int)FS_Write (file, msg, strlen (msg));
}

  
                    
         

                          
                    
  
int FS_Printf(qfile_t* file, const char* format, ...)
{
	int result;
	va_list args;

	va_start (args, format);
	result = FS_VPrintf (file, format, args);
	va_end (args);

	return result;
}


  
                    
          

                          
                    
  
int FS_VPrintf (qfile_t* file, const char* format, va_list ap)
{
	int len;
	fs_offset_t buff_size = MAX_INPUTLINE;
	char *tempbuff;

	for (;;)
	{
		tempbuff = (char *)Mem_Alloc (tempmempool, buff_size);
		len = dpvsnprintf (tempbuff, buff_size, format, ap);
		if (len >= 0 && len < buff_size)
			break;
		Mem_Free (tempbuff);
		buff_size *= 2;
	}

	len = FILEDESC_WRITE (file->handle, tempbuff, len);
	Mem_Free (tempbuff);

	return len;
}


  
                    
       

                                
                    
  
int FS_Getc (qfile_t* file)
{
	unsigned char c;

	if (FS_Read (file, &c, 1) != 1)
		return EOF;

	return c;
}


  
                    
         

                                                                        
                    
  
int FS_UnGetc (qfile_t* file, unsigned char c)
{
	                                                    
	if (file->ungetc != EOF)
		return EOF;

	file->ungetc = c;
	return c;
}


  
                    
       

                                 
                    
  
int FS_Seek (qfile_t* file, fs_offset_t offset, int whence)
{
	ztoolkit_t *ztk;
	unsigned char* buffer;
	fs_offset_t buffersize;

	                          
	switch (whence)
	{
		case SEEK_CUR:
			offset += file->position - file->buff_len + file->buff_ind;
			break;

		case SEEK_SET:
			break;

		case SEEK_END:
			offset += file->real_length;
			break;

		default:
			return -1;
	}
	if (offset < 0 || offset > file->real_length)
		return -1;

	if(file->flags & QFILE_FLAG_DATA)
	{
		file->position = offset;
		return 0;
	}

	                                                                         
	if (file->position - file->buff_len <= offset && offset <= file->position)
	{
		file->buff_ind = offset + file->buff_len - file->position;
		return 0;
	}

	                    
	FS_Purge (file);

	                                                   
	if (! (file->flags & QFILE_FLAG_DEFLATED))
	{
		if (FILEDESC_SEEK (file->handle, file->offset + offset, SEEK_SET) == -1)
			return -1;
		file->position = offset;
		return 0;
	}

	                                                                 
	                                            
	ztk = file->ztk;

	                                                                           
	if (offset <= file->position)
	{
		ztk->in_ind = 0;
		ztk->in_len = 0;
		ztk->in_position = 0;
		file->position = 0;
		if (FILEDESC_SEEK (file->handle, file->offset, SEEK_SET) == -1)
			Con_Printf("IMPOSSIBLE: couldn't seek in already opened pk3 file.\n");

		                        
		ztk->zstream.next_in = ztk->input;
		ztk->zstream.avail_in = 0;
		qz_inflateReset (&ztk->zstream);
	}

	                                                           
	buffersize = 2 * sizeof (file->buff);
	buffer = (unsigned char *)Mem_Alloc (tempmempool, buffersize);

	                                                    
	while (offset > (file->position - file->buff_len + file->buff_ind))
	{
		fs_offset_t diff = offset - (file->position - file->buff_len + file->buff_ind);
		fs_offset_t count, len;

		count = (diff > buffersize) ? buffersize : diff;
		len = FS_Read (file, buffer, count);
		if (len != count)
		{
			Mem_Free (buffer);
			return -1;
		}
	}

	Mem_Free (buffer);
	return 0;
}


  
                    
       

                                   
                    
  
fs_offset_t FS_Tell (qfile_t* file)
{
	return file->position - file->buff_len + file->buff_ind;
}


  
                    
           

                             
                    
  
fs_offset_t FS_FileSize (qfile_t* file)
{
	return file->real_length;
}


  
                    
        

                                        
                    
  
void FS_Purge (qfile_t* file)
{
	file->buff_len = 0;
	file->buff_ind = 0;
	file->ungetc = EOF;
}


  
            
                    

                                              
                        
            
  
static unsigned char *FS_LoadAndCloseQFile (qfile_t *file, const char *path, mempool_t *pool, qboolean quiet, fs_offset_t *filesizepointer)
{
	unsigned char *buf = NULL;
	fs_offset_t filesize = 0;

	if (file)
	{
		filesize = file->real_length;
		if(filesize < 0)
		{
			Con_Printf("FS_LoadFile(\"%s\", pool, %s, filesizepointer): trying to open a non-regular file\n", path, quiet ? "true" : "false");
			FS_Close(file);
			return NULL;
		}

		buf = (unsigned char *)Mem_Alloc (pool, filesize + 1);
		buf[filesize] = '\0';
		FS_Read (file, buf, filesize);
		FS_Close (file);
		if (developer_loadfile.integer)
			Con_Printf("loaded file \"%s\" (%u bytes)\n", path, (unsigned int)filesize);
	}

	if (filesizepointer)
		*filesizepointer = filesize;
	return buf;
}


  
            
           

                                             
                        
            
  
unsigned char *FS_LoadFile (const char *path, mempool_t *pool, qboolean quiet, fs_offset_t *filesizepointer)
{
	qfile_t *file = FS_OpenVirtualFile(path, quiet);
	return FS_LoadAndCloseQFile(file, path, pool, quiet, filesizepointer);
}


  
            
              

                      
                        
            
  
unsigned char *FS_SysLoadFile (const char *path, mempool_t *pool, qboolean quiet, fs_offset_t *filesizepointer)
{
	qfile_t *file = FS_SysOpen(path, "rb", false);
	return FS_LoadAndCloseQFile(file, path, pool, quiet, filesizepointer);
}


  
            
            

                                                           
            
  
qboolean FS_WriteFileInBlocks (const char *filename, const void *const *data, const fs_offset_t *len, size_t count)
{
	qfile_t *file;
	size_t i;
	fs_offset_t lentotal;

	file = FS_OpenRealFile(filename, "wb", false);
	if (!file)
	{
		Con_Printf("FS_WriteFile: failed on %s\n", filename);
		return false;
	}

	lentotal = 0;
	for(i = 0; i < count; ++i)
		lentotal += len[i];
	Con_DPrintf("FS_WriteFile: %s (%u bytes)\n", filename, (unsigned int)lentotal);
	for(i = 0; i < count; ++i)
		FS_Write (file, data[i], len[i]);
	FS_Close (file);
	return true;
}

qboolean FS_WriteFile (const char *filename, const void *data, fs_offset_t len)
{
	return FS_WriteFileInBlocks(filename, &data, &len, 1);
}


  
                                                                             

                       

                                                                             
  

  
            
                 
            
  
void FS_StripExtension (const char *in, char *out, size_t size_out)
{
	char *last = NULL;
	char currentchar;

	if (size_out == 0)
		return;

	while ((currentchar = *in) && size_out > 1)
	{
		if (currentchar == '.')
			last = out;
		else if (currentchar == '/' || currentchar == '\\' || currentchar == ':')
			last = NULL;
		*out++ = currentchar;
		in++;
		size_out--;
	}
	if (last)
		*last = 0;
	else
		*out = 0;
}


  
                  
                   
                  
  
void FS_DefaultExtension (char *path, const char *extension, size_t size_path)
{
	const char *src;

	                                                
	                                   
	src = path + strlen(path);

	while (*src != '/' && src != path)
	{
		if (*src == '.')
			return;                                       
		src--;
	}

	strlcat (path, extension, size_path);
}


  
                  
           

                                                     
                  
  
int FS_FileType (const char *filename)
{
	searchpath_t *search;
	char fullpath[MAX_OSPATH];

	search = FS_FindFile (filename, NULL, true);
	if(!search)
		return FS_FILETYPE_NONE;

	if(search->pack && !search->pack->vpack)
		return FS_FILETYPE_FILE;                                                         

	dpsnprintf(fullpath, sizeof(fullpath), "%s%s", search->filename, filename);
	return FS_SysFileType(fullpath);
}


  
                  
             

                                                     
                  
  
qboolean FS_FileExists (const char *filename)
{
	return (FS_FindFile (filename, NULL, true) != NULL);
}


  
                  
                

                                      
                  
  
int FS_SysFileType (const char *path)
{
#if WIN32
                                                 
# ifndef INVALID_FILE_ATTRIBUTES
#  define INVALID_FILE_ATTRIBUTES ((DWORD)-1)
# endif

	DWORD result = GetFileAttributes(path);

	if(result == INVALID_FILE_ATTRIBUTES)
		return FS_FILETYPE_NONE;

	if(result & FILE_ATTRIBUTE_DIRECTORY)
		return FS_FILETYPE_DIRECTORY;

	return FS_FILETYPE_FILE;
#else
	struct stat buf;

	if (stat (path,&buf) == -1)
		return FS_FILETYPE_NONE;

#ifndef S_ISDIR
#define S_ISDIR(a) (((a) & S_IFMT) == S_IFDIR)
#endif
	if(S_ISDIR(buf.st_mode))
		return FS_FILETYPE_DIRECTORY;

	return FS_FILETYPE_FILE;
#endif
}

qboolean FS_SysFileExists (const char *path)
{
	return FS_SysFileType (path) != FS_FILETYPE_NONE;
}

  
           
         

                                                                            
           
  
fssearch_t *FS_Search(const char *pattern, int caseinsensitive, int quiet)
{
	fssearch_t *search;
	searchpath_t *searchpath;
	pack_t *pak;
	int i, basepathlength, numfiles, numchars, resultlistindex, dirlistindex;
	stringlist_t resultlist;
	stringlist_t dirlist;
	const char *slash, *backslash, *colon, *separator;
	char *basepath;

	for (i = 0;pattern[i] == '.' || pattern[i] == ':' || pattern[i] == '/' || pattern[i] == '\\';i++)
		;

	if (i > 0)
	{
		Con_Printf("Don't use punctuation at the beginning of a search pattern!\n");
		return NULL;
	}

	stringlistinit(&resultlist);
	stringlistinit(&dirlist);
	search = NULL;
	slash = strrchr(pattern, '/');
	backslash = strrchr(pattern, '\\');
	colon = strrchr(pattern, ':');
	separator = max(slash, backslash);
	separator = max(separator, colon);
	basepathlength = separator ? (separator + 1 - pattern) : 0;
	basepath = (char *)Mem_Alloc (tempmempool, basepathlength + 1);
	if (basepathlength)
		memcpy(basepath, pattern, basepathlength);
	basepath[basepathlength] = 0;

	                                                 
	for (searchpath = fs_searchpaths;searchpath;searchpath = searchpath->next)
	{
		                             
		if (searchpath->pack && !searchpath->pack->vpack)
		{
			                                         
			pak = searchpath->pack;
			for (i = 0;i < pak->numfiles;i++)
			{
				char temp[MAX_OSPATH];
				strlcpy(temp, pak->files[i].name, sizeof(temp));
				while (temp[0])
				{
					if (matchpattern(temp, (char *)pattern, true))
					{
						for (resultlistindex = 0;resultlistindex < resultlist.numstrings;resultlistindex++)
							if (!strcmp(resultlist.strings[resultlistindex], temp))
								break;
						if (resultlistindex == resultlist.numstrings)
						{
							stringlistappend(&resultlist, temp);
							if (!quiet && developer_loading.integer)
								Con_Printf("SearchPackFile: %s : %s\n", pak->filename, temp);
						}
					}
					                                                   
					                                                                          
					slash = strrchr(temp, '/');
					backslash = strrchr(temp, '\\');
					colon = strrchr(temp, ':');
					separator = temp;
					if (separator < slash)
						separator = slash;
					if (separator < backslash)
						separator = backslash;
					if (separator < colon)
						separator = colon;
					*((char *)separator) = 0;
				}
			}
		}
		else
		{
			stringlist_t matchedSet, foundSet;
			const char *start = pattern;

			stringlistinit(&matchedSet);
			stringlistinit(&foundSet);
			                               
			stringlistappend(&matchedSet, "");
			                                 
			while (*start)
			{
				const char *asterisk, *wildcard, *nextseparator, *prevseparator;
				char subpath[MAX_OSPATH];
				char subpattern[MAX_OSPATH];

				                         
				wildcard = strchr(start, '?');
				asterisk = strchr(start, '*');
				if (asterisk && (!wildcard || asterisk < wildcard))
				{
					wildcard = asterisk;
				}

				if (wildcard)
				{
					nextseparator = strchr( wildcard, '/' );
				}
				else
				{
					nextseparator = NULL;
				}

				if( !nextseparator ) {
					nextseparator = start + strlen( start );
				}

				                                                                                                                                      
				                                          
				strlcpy(subpattern, pattern, min(sizeof(subpattern), (size_t) (nextseparator - pattern + 1)));
				                                        
				prevseparator = strrchr( subpattern, '/' );
				if (!prevseparator)
					prevseparator = subpattern;
				else
					prevseparator++;
				                                                                                     
				                                                                                 
				strlcpy(subpath, start, min(sizeof(subpath), (size_t) ((prevseparator - subpattern) - (start - pattern) + 1)));

				                                                                                   
				for( dirlistindex = 0 ; dirlistindex < matchedSet.numstrings ; dirlistindex++ ) {
					char temp[MAX_OSPATH];
					strlcpy( temp, matchedSet.strings[ dirlistindex ], sizeof(temp) );
					strlcat( temp, subpath, sizeof(temp) );
					listdirectory( &foundSet, searchpath->filename, temp );
				}
				if( dirlistindex == 0 ) {
					break;
				}
				                               
				stringlistfreecontents( &matchedSet );
				                            
				for( dirlistindex = 0 ; dirlistindex < foundSet.numstrings ; dirlistindex++ ) {
					const char *direntry = foundSet.strings[ dirlistindex ];
					if (matchpattern(direntry, subpattern, true)) {
						stringlistappend( &matchedSet, direntry );
					}
				}
				stringlistfreecontents( &foundSet );

				start = nextseparator;
			}

			for (dirlistindex = 0;dirlistindex < matchedSet.numstrings;dirlistindex++)
			{
				const char *matchtemp = matchedSet.strings[dirlistindex];
				if (matchpattern(matchtemp, (char *)pattern, true))
				{
					for (resultlistindex = 0;resultlistindex < resultlist.numstrings;resultlistindex++)
						if (!strcmp(resultlist.strings[resultlistindex], matchtemp))
							break;
					if (resultlistindex == resultlist.numstrings)
					{
						stringlistappend(&resultlist, matchtemp);
						if (!quiet && developer_loading.integer)
							Con_Printf("SearchDirFile: %s\n", matchtemp);
					}
				}
			}
			stringlistfreecontents( &matchedSet );
		}
	}

	if (resultlist.numstrings)
	{
		stringlistsort(&resultlist, true);
		numfiles = resultlist.numstrings;
		numchars = 0;
		for (resultlistindex = 0;resultlistindex < resultlist.numstrings;resultlistindex++)
			numchars += (int)strlen(resultlist.strings[resultlistindex]) + 1;
		search = (fssearch_t *)Z_Malloc(sizeof(fssearch_t) + numchars + numfiles * sizeof(char *));
		search->filenames = (char **)((char *)search + sizeof(fssearch_t));
		search->filenamesbuffer = (char *)((char *)search + sizeof(fssearch_t) + numfiles * sizeof(char *));
		search->numfilenames = (int)numfiles;
		numfiles = 0;
		numchars = 0;
		for (resultlistindex = 0;resultlistindex < resultlist.numstrings;resultlistindex++)
		{
			size_t textlen;
			search->filenames[numfiles] = search->filenamesbuffer + numchars;
			textlen = strlen(resultlist.strings[resultlistindex]) + 1;
			memcpy(search->filenames[numfiles], resultlist.strings[resultlistindex], textlen);
			numfiles++;
			numchars += (int)textlen;
		}
	}
	stringlistfreecontents(&resultlist);

	Mem_Free(basepath);
	return search;
}

void FS_FreeSearch(fssearch_t *search)
{
	Z_Free(search);
}

extern int con_linewidth;
static int FS_ListDirectory(const char *pattern, int oneperline)
{
	int numfiles;
	int numcolumns;
	int numlines;
	int columnwidth;
	int linebufpos;
	int i, j, k, l;
	const char *name;
	char linebuf[MAX_INPUTLINE];
	fssearch_t *search;
	search = FS_Search(pattern, true, true);
	if (!search)
		return 0;
	numfiles = search->numfilenames;
	if (!oneperline)
	{
		                                                              
		                                                                   
		                                                                    
		                 
		                         
		columnwidth = 0;
		for (i = 0;i < numfiles;i++)
		{
			l = (int)strlen(search->filenames[i]);
			if (columnwidth < l)
				columnwidth = l;
		}
		                              
		columnwidth++;
		                              
		numcolumns = con_linewidth / columnwidth;
		                                                                
		if (numcolumns >= 2)
		{
			numlines = (numfiles + numcolumns - 1) / numcolumns;
			for (i = 0;i < numlines;i++)
			{
				linebufpos = 0;
				for (k = 0;k < numcolumns;k++)
				{
					l = i * numcolumns + k;
					if (l < numfiles)
					{
						name = search->filenames[l];
						for (j = 0;name[j] && linebufpos + 1 < (int)sizeof(linebuf);j++)
							linebuf[linebufpos++] = name[j];
						                                                  
						if (k + 1 < numcolumns && l + 1 < numfiles)
							for (;j < columnwidth && linebufpos + 1 < (int)sizeof(linebuf);j++)
								linebuf[linebufpos++] = ' ';
					}
				}
				linebuf[linebufpos] = 0;
				Con_Printf("%s\n", linebuf);
			}
		}
		else
			oneperline = true;
	}
	if (oneperline)
		for (i = 0;i < numfiles;i++)
			Con_Printf("%s\n", search->filenames[i]);
	FS_FreeSearch(search);
	return (int)numfiles;
}

static void FS_ListDirectoryCmd (const char* cmdname, int oneperline)
{
	const char *pattern;
	if (Cmd_Argc() >= 3)
	{
		Con_Printf("usage:\n%s [path/pattern]\n", cmdname);
		return;
	}
	if (Cmd_Argc() == 2)
		pattern = Cmd_Argv(1);
	else
		pattern = "*";
	if (!FS_ListDirectory(pattern, oneperline))
		Con_Print("No files found.\n");
}

void FS_Dir_f(void)
{
	FS_ListDirectoryCmd("dir", true);
}

void FS_Ls_f(void)
{
	FS_ListDirectoryCmd("ls", false);
}

void FS_Which_f(void)
{
	const char *filename;
	int index;
	searchpath_t *sp;
	if (Cmd_Argc() != 2)
	{
		Con_Printf("usage:\n%s <file>\n", Cmd_Argv(0));
		return;
	}  
	filename = Cmd_Argv(1);
	sp = FS_FindFile(filename, &index, true);
	if (!sp) {
		Con_Printf("%s isn't anywhere\n", filename);
		return;
	}
	if (sp->pack)
	{
		if(sp->pack->vpack)
			Con_Printf("%s is in virtual package %sdir\n", filename, sp->pack->shortname);
		else
			Con_Printf("%s is in package %s\n", filename, sp->pack->shortname);
	}
	else
		Con_Printf("%s is file %s%s\n", filename, sp->filename, filename);
}


const char *FS_WhichPack(const char *filename)
{
	int index;
	searchpath_t *sp = FS_FindFile(filename, &index, true);
	if(sp && sp->pack)
		return sp->pack->shortname;
	else if(sp)
		return "";
	else
		return 0;
}

  
                    
                        

                                                               

                                                   
                    
  
qboolean FS_IsRegisteredQuakePack(const char *name)
{
	searchpath_t *search;
	pack_t *pak;

	                                                 
	for (search = fs_searchpaths;search;search = search->next)
	{
		if (search->pack && !search->pack->vpack && !strcasecmp(FS_FileWithoutPath(search->filename), name))
			                                                 
		{
			int (*strcmp_funct) (const char* str1, const char* str2);
			int left, right, middle;

			pak = search->pack;
			strcmp_funct = pak->ignorecase ? strcasecmp : strcmp;

			                                    
			left = 0;
			right = pak->numfiles - 1;
			while (left <= right)
			{
				int diff;

				middle = (left + right) / 2;
				diff = strcmp_funct (pak->files[middle].name, "gfx/pop.lmp");

				           
				if (!diff)
					return true;

				                               
				if (diff > 0)
					right = middle - 1;
				else
					left = middle + 1;
			}

			                                                             
			return false;
		}
	}

	return false;
}

int FS_CRCFile(const char *filename, size_t *filesizepointer)
{
	int crc = -1;
	unsigned char *filedata;
	fs_offset_t filesize;
	if (filesizepointer)
		*filesizepointer = 0;
	if (!filename || !*filename)
		return crc;
	filedata = FS_LoadFile(filename, tempmempool, true, &filesize);
	if (filedata)
	{
		if (filesizepointer)
			*filesizepointer = filesize;
		crc = CRC_Block(filedata, filesize);
		Mem_Free(filedata);
	}
	return crc;
}

unsigned char *FS_Deflate(const unsigned char *data, size_t size, size_t *deflated_size, int level, mempool_t *mempool)
{
	z_stream strm;
	unsigned char *out = NULL;
	unsigned char *tmp;

	*deflated_size = 0;
#ifndef LINK_TO_ZLIB
	if(!zlib_dll)
		return NULL;
#endif

	memset(&strm, 0, sizeof(strm));
	strm.zalloc = Z_NULL;
	strm.zfree = Z_NULL;
	strm.opaque = Z_NULL;

	if(level < 0)
		level = Z_DEFAULT_COMPRESSION;

	if(qz_deflateInit2(&strm, level, Z_DEFLATED, -MAX_WBITS, Z_MEMLEVEL_DEFAULT, Z_BINARY) != Z_OK)
	{
		Con_Printf("FS_Deflate: deflate init error!\n");
		return NULL;
	}

	strm.next_in = (unsigned char*)data;
	strm.avail_in = (unsigned int)size;

	tmp = (unsigned char *) Mem_Alloc(tempmempool, size);
	if(!tmp)
	{
		Con_Printf("FS_Deflate: not enough memory in tempmempool!\n");
		qz_deflateEnd(&strm);
		return NULL;
	}

	strm.next_out = tmp;
	strm.avail_out = (unsigned int)size;

	if(qz_deflate(&strm, Z_FINISH) != Z_STREAM_END)
	{
		Con_Printf("FS_Deflate: deflate failed!\n");
		qz_deflateEnd(&strm);
		Mem_Free(tmp);
		return NULL;
	}
	
	if(qz_deflateEnd(&strm) != Z_OK)
	{
		Con_Printf("FS_Deflate: deflateEnd failed\n");
		Mem_Free(tmp);
		return NULL;
	}

	if(strm.total_out >= size)
	{
		Con_Printf("FS_Deflate: deflate is useless on this data!\n");
		Mem_Free(tmp);
		return NULL;
	}

	out = (unsigned char *) Mem_Alloc(mempool, strm.total_out);
	if(!out)
	{
		Con_Printf("FS_Deflate: not enough memory in target mempool!\n");
		Mem_Free(tmp);
		return NULL;
	}

	*deflated_size = (size_t)strm.total_out;

	memcpy(out, tmp, strm.total_out);
	Mem_Free(tmp);
	
	return out;
}

static void AssertBufsize(sizebuf_t *buf, int length)
{
	if(buf->cursize + length > buf->maxsize)
	{
		int oldsize = buf->maxsize;
		unsigned char *olddata;
		olddata = buf->data;
		buf->maxsize += length;
		buf->data = (unsigned char *) Mem_Alloc(tempmempool, buf->maxsize);
		if(olddata)
		{
			memcpy(buf->data, olddata, oldsize);
			Mem_Free(olddata);
		}
	}
}

unsigned char *FS_Inflate(const unsigned char *data, size_t size, size_t *inflated_size, mempool_t *mempool)
{
	int ret;
	z_stream strm;
	unsigned char *out = NULL;
	unsigned char tmp[2048];
	unsigned int have;
	sizebuf_t outbuf;

	*inflated_size = 0;
#ifndef LINK_TO_ZLIB
	if(!zlib_dll)
		return NULL;
#endif

	memset(&outbuf, 0, sizeof(outbuf));
	outbuf.data = (unsigned char *) Mem_Alloc(tempmempool, sizeof(tmp));
	outbuf.maxsize = sizeof(tmp);

	memset(&strm, 0, sizeof(strm));
	strm.zalloc = Z_NULL;
	strm.zfree = Z_NULL;
	strm.opaque = Z_NULL;

	if(qz_inflateInit2(&strm, -MAX_WBITS) != Z_OK)
	{
		Con_Printf("FS_Inflate: inflate init error!\n");
		Mem_Free(outbuf.data);
		return NULL;
	}

	strm.next_in = (unsigned char*)data;
	strm.avail_in = (unsigned int)size;

	do
	{
		strm.next_out = tmp;
		strm.avail_out = sizeof(tmp);
		ret = qz_inflate(&strm, Z_NO_FLUSH);
		                                                          
		                   
		switch(ret)
		{
			case Z_STREAM_END:
			case Z_OK:
				break;
				
			case Z_STREAM_ERROR:
				Con_Print("FS_Inflate: stream error!\n");
				break;
			case Z_DATA_ERROR:
				Con_Print("FS_Inflate: data error!\n");
				break;
			case Z_MEM_ERROR:
				Con_Print("FS_Inflate: mem error!\n");
				break;
			case Z_BUF_ERROR:
				Con_Print("FS_Inflate: buf error!\n");
				break;
			default:
				Con_Print("FS_Inflate: unknown error!\n");
				break;
				
		}
		if(ret != Z_OK && ret != Z_STREAM_END)
		{
			Con_Printf("Error after inflating %u bytes\n", (unsigned)strm.total_in);
			Mem_Free(outbuf.data);
			qz_inflateEnd(&strm);
			return NULL;
		}
		have = sizeof(tmp) - strm.avail_out;
		AssertBufsize(&outbuf, max(have, sizeof(tmp)));
		SZ_Write(&outbuf, tmp, have);
	} while(ret != Z_STREAM_END);

	qz_inflateEnd(&strm);

	out = (unsigned char *) Mem_Alloc(mempool, outbuf.cursize);
	if(!out)
	{
		Con_Printf("FS_Inflate: not enough memory in target mempool!\n");
		Mem_Free(outbuf.data);
		return NULL;
	}

	memcpy(out, outbuf.data, outbuf.cursize);
	Mem_Free(outbuf.data);

	*inflated_size = (size_t)outbuf.cursize;
	
	return out;
}
