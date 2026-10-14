  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

#ifndef ZONE_H
#define ZONE_H

extern qboolean mem_bigendian;

                                         
#define MEMPARANOIA 0

#define POOLNAMESIZE 128
                                                      
#define POOLFLAG_TEMP 1

typedef struct memheader_s
{
	                                                                                                  
	void *baseaddress;
	                                                          
	struct memheader_s *next;
	struct memheader_s *prev;
	                                 
	struct mempool_s *pool;
	                                                                       
	size_t size;
	                                                
	const char *filename;
	int fileline;
	                                                             
	unsigned int sentinel;
	                                                                                    
}
memheader_t;

typedef struct mempool_s
{
	                                    
	unsigned int sentinel1;
	                                         
	struct memheader_s *chain;
	             
	int flags;
	                                                          
	size_t totalsize;
	                                                            
	size_t realsize;
	                                                                                                              
	size_t lastchecksize;
	                                  
	struct mempool_s *next;
	                                               
	struct mempool_s *parent;
	                                                    
	const char *filename;
	int fileline;
	                   
	char name[POOLNAMESIZE];
	                                    
	unsigned int sentinel2;
}
mempool_t;

#define Mem_Alloc(pool,size) _Mem_Alloc(pool, NULL, size, 16, __FILE__, __LINE__)
#define Mem_Memalign(pool,alignment,size) _Mem_Alloc(pool, NULL, size, alignment, __FILE__, __LINE__)
#define Mem_Realloc(pool,data,size) _Mem_Alloc(pool, data, size, 16, __FILE__, __LINE__)
#define Mem_Free(mem) _Mem_Free(mem, __FILE__, __LINE__)
#define Mem_CheckSentinels(data) _Mem_CheckSentinels(data, __FILE__, __LINE__)
#define Mem_CheckSentinelsGlobal() _Mem_CheckSentinelsGlobal(__FILE__, __LINE__)
#define Mem_AllocPool(name, flags, parent) _Mem_AllocPool(name, flags, parent, __FILE__, __LINE__)
#define Mem_FreePool(pool) _Mem_FreePool(pool, __FILE__, __LINE__)
#define Mem_EmptyPool(pool) _Mem_EmptyPool(pool, __FILE__, __LINE__)

void *_Mem_Alloc(mempool_t *pool, void *data, size_t size, size_t alignment, const char *filename, int fileline);
void _Mem_Free(void *data, const char *filename, int fileline);
mempool_t *_Mem_AllocPool(const char *name, int flags, mempool_t *parent, const char *filename, int fileline);
void _Mem_FreePool(mempool_t **pool, const char *filename, int fileline);
void _Mem_EmptyPool(mempool_t *pool, const char *filename, int fileline);
void _Mem_CheckSentinels(void *data, const char *filename, int fileline);
void _Mem_CheckSentinelsGlobal(const char *filename, int fileline);
                                                             
qboolean Mem_IsAllocated(mempool_t *pool, void *data);

char* Mem_strdup (mempool_t *pool, const char* s);

typedef struct memexpandablearray_array_s
{
	unsigned char *data;
	unsigned char *allocflags;
	size_t numflaggedrecords;
}
memexpandablearray_array_t;

typedef struct memexpandablearray_s
{
	mempool_t *mempool;
	size_t recordsize;
	size_t numrecordsperarray;
	size_t numarrays;
	size_t maxarrays;
	memexpandablearray_array_t *arrays;
}
memexpandablearray_t;

void Mem_ExpandableArray_NewArray(memexpandablearray_t *l, mempool_t *mempool, size_t recordsize, int numrecordsperarray);
void Mem_ExpandableArray_FreeArray(memexpandablearray_t *l);
void *Mem_ExpandableArray_AllocRecord(memexpandablearray_t *l);
void Mem_ExpandableArray_FreeRecord(memexpandablearray_t *l, void *record);
size_t Mem_ExpandableArray_IndexRange(const memexpandablearray_t *l) DP_FUNC_PURE;
void *Mem_ExpandableArray_RecordAtIndex(const memexpandablearray_t *l, size_t index) DP_FUNC_PURE;

                                 
extern mempool_t *tempmempool;

void Memory_Init (void);
void Memory_Shutdown (void);
void Memory_Init_Commands (void);

extern mempool_t *zonemempool;
#define Z_Malloc(size) Mem_Alloc(zonemempool,size)
#define Z_Free(data) Mem_Free(data)

extern struct cvar_s developer_memory;
extern struct cvar_s developer_memorydebug;
extern struct cvar_s developer_memoryreportlargerthanmb;

#endif

