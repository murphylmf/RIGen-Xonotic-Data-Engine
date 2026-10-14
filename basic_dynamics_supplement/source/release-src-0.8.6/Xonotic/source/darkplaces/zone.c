  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
           

#include "quakedef.h"
#include "thread.h"

#ifdef WIN32
#include <windows.h>
#include <winbase.h>
#else
#include <unistd.h>
#endif

#ifdef _MSC_VER
#include <vadefs.h>
#else
#include <stdint.h>
#endif
#define MEMHEADER_SENTINEL_FOR_ADDRESS(p) ((sentinel_seed ^ (unsigned int) (uintptr_t) (p)) + sentinel_seed)
unsigned int sentinel_seed;

qboolean mem_bigendian = false;
void *mem_mutex = NULL;

                                                                                              
#ifndef FILE_BACKED_MALLOC
# define FILE_BACKED_MALLOC 0
#endif

                                                                     
#ifndef MEMCLUMPING
# define MEMCLUMPING 0
#endif
#ifndef MEMCLUMPING_FREECLUMPS
# define MEMCLUMPING_FREECLUMPS 0
#endif

#if MEMCLUMPING
                                                 
#define MEMUNIT 128
                                                     
#ifndef MEMWANTCLUMPSIZE
# define MEMWANTCLUMPSIZE (1<<27)
#endif
                                                                  
#define MEMCLUMPSIZE (MEMWANTCLUMPSIZE - MEMWANTCLUMPSIZE/MEMUNIT/32 - 128)
#define MEMBITS (MEMCLUMPSIZE / MEMUNIT)
#define MEMBITINTS (MEMBITS / 32)

typedef struct memclump_s
{
	                        
	unsigned char block[MEMCLUMPSIZE];
	                                     
	unsigned int sentinel1;
	                                                                    
	                            
	unsigned int bits[MEMBITINTS];
	                                     
	unsigned int sentinel2;
	                                         
	size_t blocksinuse;
	                                                                    
	                                                                         
	size_t largestavailable;
	                          
	struct memclump_s *chain;
}
memclump_t;

#if MEMCLUMPING == 2
static memclump_t masterclump;
#endif
static memclump_t *clumpchain = NULL;
#endif


cvar_t developer_memory = {0, "developer_memory", "0", "prints debugging information about memory allocations"};
cvar_t developer_memorydebug = {0, "developer_memorydebug", "0", "enables memory corruption checks (very slow)"};
cvar_t developer_memoryreportlargerthanmb = {0, "developer_memorylargerthanmb", "16", "prints debugging information about memory allocations over this size"};
cvar_t sys_memsize_physical = {CVAR_READONLY, "sys_memsize_physical", "", "physical memory size in MB (or empty if unknown)"};
cvar_t sys_memsize_virtual = {CVAR_READONLY, "sys_memsize_virtual", "", "virtual memory size in MB (or empty if unknown)"};

static mempool_t *poolchain = NULL;

void Mem_PrintStats(void);
void Mem_PrintList(size_t minallocationsize);

#if FILE_BACKED_MALLOC
#include <stdlib.h>
#include <sys/mman.h>
typedef struct mmap_data_s
{
	size_t len;
}
mmap_data_t;
static void *mmap_malloc(size_t size)
{
	char vabuf[MAX_OSPATH + 1];
	char *tmpdir = getenv("TEMP");
	mmap_data_t *data;
	int fd;
	size += sizeof(mmap_data_t);               
	dpsnprintf(vabuf, sizeof(vabuf), "%s/darkplaces.XXXXXX", tmpdir ? tmpdir : "./tmp");
	fd = mkstemp(vabuf);
	if(fd < 0)
		return NULL;
	ftruncate(fd, size);
	data = (unsigned char *) mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_NORESERVE, fd, 0);
	close(fd);
	unlink(vabuf);
	if(!data)
		return NULL;
	data->len = size;
	return (void *) (data + 1);
}
static void mmap_free(void *mem)
{
	mmap_data_t *data;
	if(!mem)
		return;
	data = ((mmap_data_t *) mem) - 1;
	munmap(data, data->len);
}
#define malloc mmap_malloc
#define free mmap_free
#endif

#if MEMCLUMPING != 2
                                                                    
                                             
static void *attempt_malloc(size_t size)
{
	void *base;
	                              
	unsigned int attempts = 500;
	while (attempts--)
	{
		base = (void *)malloc(size);
		if (base)
			return base;
		Sys_Sleep(1000);
	}
	return NULL;
}
#endif

#if MEMCLUMPING
static memclump_t *Clump_NewClump(void)
{
	memclump_t **clumpchainpointer;
	memclump_t *clump;
#if MEMCLUMPING == 2
	if (clumpchain)
		return NULL;
	clump = &masterclump;
#else
	clump = (memclump_t*)attempt_malloc(sizeof(memclump_t));
	if (!clump)
		return NULL;
#endif

	                   
	if (developer_memorydebug.integer)
		memset(clump, 0xEF, sizeof(*clump));
	clump->sentinel1 = MEMHEADER_SENTINEL_FOR_ADDRESS(&clump->sentinel1);
	memset(clump->bits, 0, sizeof(clump->bits));
	clump->sentinel2 = MEMHEADER_SENTINEL_FOR_ADDRESS(&clump->sentinel2);
	clump->blocksinuse = 0;
	clump->largestavailable = 0;
	clump->chain = NULL;

	                        
	for (clumpchainpointer = &clumpchain;*clumpchainpointer;clumpchainpointer = &(*clumpchainpointer)->chain)
		;
	*clumpchainpointer = clump;

	return clump;
}
#endif

                                                                     
static void *Clump_AllocBlock(size_t size)
{
	unsigned char *base;
#if MEMCLUMPING
	if (size <= MEMCLUMPSIZE)
	{
		int index;
		unsigned int bit;
		unsigned int needbits;
		unsigned int startbit;
		unsigned int endbit;
		unsigned int needints;
		int startindex;
		int endindex;
		unsigned int value;
		unsigned int mask;
		unsigned int *array;
		memclump_t **clumpchainpointer;
		memclump_t *clump;
		needbits = (size + MEMUNIT - 1) / MEMUNIT;
		needints = (needbits+31)>>5;
		for (clumpchainpointer = &clumpchain;;clumpchainpointer = &(*clumpchainpointer)->chain)
		{
			clump = *clumpchainpointer;
			if (!clump)
			{
				clump = Clump_NewClump();
				if (!clump)
					return NULL;
			}
			if (clump->sentinel1 != MEMHEADER_SENTINEL_FOR_ADDRESS(&clump->sentinel1))
				Sys_Error("Clump_AllocBlock: trashed sentinel1\n");
			if (clump->sentinel2 != MEMHEADER_SENTINEL_FOR_ADDRESS(&clump->sentinel2))
				Sys_Error("Clump_AllocBlock: trashed sentinel2\n");
			startbit = 0;
			endbit = startbit + needbits;
			array = clump->bits;
			                                                                    
			if (needbits >= 32)
			{
				                                                    
				                                                           
				endindex = MEMBITINTS;
				startindex = endindex - needints;
				index = endindex;
				while (--index >= startindex)
				{
					if (array[index])
					{
						endindex = index;
						startindex = endindex - needints;
						if (startindex < 0)
							goto nofreeblock;
					}
				}
				startbit = startindex*32;
				goto foundblock;
			}
			else
			{
				                                             
				                                                   
				mask = (1<<needbits)-1;
				endbit = 32-needbits;
				bit = endbit;
				for (index = 0;index < MEMBITINTS;index++)
				{
					value = array[index];
					if (value != 0xFFFFFFFFu)
					{
						                                   
						for (bit = 0;bit < endbit;bit++)
						{
							if (!(value & (mask<<bit)))
							{
								startbit = index*32+bit;
								goto foundblock;
							}
						}
					}
				}
				goto nofreeblock;
			}
foundblock:
			endbit = startbit + needbits;
			                          
			                 
			for (bit = startbit;bit < endbit;bit++)
				if (clump->bits[bit>>5] & (1<<(bit & 31)))
					Sys_Error("Clump_AllocBlock: internal error (%i needbits)\n", needbits);
			for (bit = startbit;bit < endbit;bit++)
				clump->bits[bit>>5] |= (1<<(bit & 31));
			clump->blocksinuse += needbits;
			base = clump->block + startbit * MEMUNIT;
			if (developer_memorydebug.integer)
				memset(base, 0xBF, needbits * MEMUNIT);
			return base;
nofreeblock:
			;
		}
		                
		return NULL;
	}
	                                
#endif
#if MEMCLUMPING == 2
	return NULL;
#else
	base = (unsigned char *)attempt_malloc(size);
	if (base && developer_memorydebug.integer)
		memset(base, 0xAF, size);
	return base;
#endif
}
static void Clump_FreeBlock(void *base, size_t size)
{
#if MEMCLUMPING
	unsigned int needbits;
	unsigned int startbit;
	unsigned int endbit;
	unsigned int bit;
	memclump_t **clumpchainpointer;
	memclump_t *clump;
	unsigned char *start = (unsigned char *)base;
	for (clumpchainpointer = &clumpchain;(clump = *clumpchainpointer);clumpchainpointer = &(*clumpchainpointer)->chain)
	{
		if (start >= clump->block && start < clump->block + MEMCLUMPSIZE)
		{
			if (clump->sentinel1 != MEMHEADER_SENTINEL_FOR_ADDRESS(&clump->sentinel1))
				Sys_Error("Clump_FreeBlock: trashed sentinel1\n");
			if (clump->sentinel2 != MEMHEADER_SENTINEL_FOR_ADDRESS(&clump->sentinel2))
				Sys_Error("Clump_FreeBlock: trashed sentinel2\n");
			if (start + size > clump->block + MEMCLUMPSIZE)
				Sys_Error("Clump_FreeBlock: block overrun\n");
			                                                   
			needbits = (size + MEMUNIT - 1) / MEMUNIT;
			startbit = (start - clump->block) / MEMUNIT;
			endbit = startbit + needbits;
			                                                                                   
			for (bit = startbit;bit < endbit;bit++)
				if ((clump->bits[bit>>5] & (1<<(bit & 31))) == 0)
					Sys_Error("Clump_FreeBlock: double free\n");
			for (bit = startbit;bit < endbit;bit++)
				clump->bits[bit>>5] &= ~(1<<(bit & 31));
			clump->blocksinuse -= needbits;
			memset(base, 0xFF, needbits * MEMUNIT);
			                                               
			if (clump->blocksinuse == 0)
			{
				*clumpchainpointer = clump->chain;
				if (developer_memorydebug.integer)
					memset(clump, 0xFF, sizeof(*clump));
#if MEMCLUMPING != 2
				free(clump);
#endif
			}
			return;
		}
	}
	                                                                           
#endif
#if MEMCLUMPING != 2
	memset(base, 0xFF, size);
	free(base);
#endif
}

void *_Mem_Alloc(mempool_t *pool, void *olddata, size_t size, size_t alignment, const char *filename, int fileline)
{
	unsigned int sentinel1;
	unsigned int sentinel2;
	size_t realsize;
	size_t sharedsize;
	size_t remainsize;
	memheader_t *mem;
	memheader_t *oldmem;
	unsigned char *base;

	if (size <= 0)
	{
		if (olddata)
			_Mem_Free(olddata, filename, fileline);
		return NULL;
	}
	if (pool == NULL)
	{
		if(olddata)
			pool = ((memheader_t *)((unsigned char *) olddata - sizeof(memheader_t)))->pool;
		else
			Sys_Error("Mem_Alloc: pool == NULL (alloc at %s:%i)", filename, fileline);
	}
	if (mem_mutex)
		Thread_LockMutex(mem_mutex);
	if (developer_memory.integer || size >= developer_memoryreportlargerthanmb.value * 1048576)
		Con_DPrintf("Mem_Alloc: pool %s, file %s:%i, size %f bytes (%f MB)\n", pool->name, filename, fileline, (double)size, (double)size / 1048576.0f);
	                                                             
	                                                 
	pool->totalsize += size;
	realsize = alignment + sizeof(memheader_t) + size + sizeof(sentinel2);
	pool->realsize += realsize;
	base = (unsigned char *)Clump_AllocBlock(realsize);
	if (base == NULL)
	{
		Mem_PrintList(0);
		Mem_PrintStats();
		Mem_PrintList(1<<30);
		Mem_PrintStats();
		Sys_Error("Mem_Alloc: out of memory (alloc of size %f (%.3fMB) at %s:%i)", (double)realsize, (double)realsize / (1 << 20), filename, fileline);
	}
	                                                                                      
	mem = (memheader_t*)((((size_t)base + sizeof(memheader_t) + (alignment-1)) & ~(alignment-1)) - sizeof(memheader_t));
	mem->baseaddress = (void*)base;
	mem->filename = filename;
	mem->fileline = fileline;
	mem->size = size;
	mem->pool = pool;

	                                                                                  
	sentinel1 = MEMHEADER_SENTINEL_FOR_ADDRESS(&mem->sentinel);
	sentinel2 = MEMHEADER_SENTINEL_FOR_ADDRESS((unsigned char *) mem + sizeof(memheader_t) + mem->size);
	mem->sentinel = sentinel1;
	memcpy((unsigned char *) mem + sizeof(memheader_t) + mem->size, &sentinel2, sizeof(sentinel2));

	                         
	mem->next = pool->chain;
	mem->prev = NULL;
	pool->chain = mem;
	if (mem->next)
		mem->next->prev = mem;

	if (mem_mutex)
		Thread_UnlockMutex(mem_mutex);

	                                                                         
	sharedsize = 0;
	remainsize = size;
	if (olddata)
	{
		oldmem = (memheader_t*)olddata - 1;
		sharedsize = min(oldmem->size, size);
		memcpy((void *)((unsigned char *) mem + sizeof(memheader_t)), olddata, sharedsize);
		remainsize -= sharedsize;
		_Mem_Free(olddata, filename, fileline);
	}
	memset((void *)((unsigned char *) mem + sizeof(memheader_t) + sharedsize), 0, remainsize);
	return (void *)((unsigned char *) mem + sizeof(memheader_t));
}

                                           
static void _Mem_FreeBlock(memheader_t *mem, const char *filename, int fileline)
{
	mempool_t *pool;
	size_t size;
	size_t realsize;
	unsigned int sentinel1;
	unsigned int sentinel2;

	                                                                              
	sentinel1 = MEMHEADER_SENTINEL_FOR_ADDRESS(&mem->sentinel);
	sentinel2 = MEMHEADER_SENTINEL_FOR_ADDRESS((unsigned char *) mem + sizeof(memheader_t) + mem->size);
	if (mem->sentinel != sentinel1)
		Sys_Error("Mem_Free: trashed head sentinel (alloc at %s:%i, free at %s:%i)", mem->filename, mem->fileline, filename, fileline);
	if (memcmp((unsigned char *) mem + sizeof(memheader_t) + mem->size, &sentinel2, sizeof(sentinel2)))
		Sys_Error("Mem_Free: trashed tail sentinel (alloc at %s:%i, free at %s:%i)", mem->filename, mem->fileline, filename, fileline);

	pool = mem->pool;
	if (developer_memory.integer)
		Con_DPrintf("Mem_Free: pool %s, alloc %s:%i, free %s:%i, size %i bytes\n", pool->name, mem->filename, mem->fileline, filename, fileline, (int)(mem->size));
	                                           
	if ((mem->prev ? mem->prev->next != mem : pool->chain != mem) || (mem->next && mem->next->prev != mem))
		Sys_Error("Mem_Free: not allocated or double freed (free at %s:%i)", filename, fileline);
	if (mem_mutex)
		Thread_LockMutex(mem_mutex);
	if (mem->prev)
		mem->prev->next = mem->next;
	else
		pool->chain = mem->next;
	if (mem->next)
		mem->next->prev = mem->prev;
	                                                      
	size = mem->size;
	realsize = sizeof(memheader_t) + size + sizeof(sentinel2);
	pool->totalsize -= size;
	pool->realsize -= realsize;
	Clump_FreeBlock(mem->baseaddress, realsize);
	if (mem_mutex)
		Thread_UnlockMutex(mem_mutex);
}

void _Mem_Free(void *data, const char *filename, int fileline)
{
	if (data == NULL)
	{
		Con_DPrintf("Mem_Free: data == NULL (called at %s:%i)\n", filename, fileline);
		return;
	}

	if (developer_memorydebug.integer)
	{
		                                                
		if (!Mem_IsAllocated(NULL, data))
			Sys_Error("Mem_Free: data is not allocated (called at %s:%i)", filename, fileline);
	}

	_Mem_FreeBlock((memheader_t *)((unsigned char *) data - sizeof(memheader_t)), filename, fileline);
}

mempool_t *_Mem_AllocPool(const char *name, int flags, mempool_t *parent, const char *filename, int fileline)
{
	mempool_t *pool;
	if (developer_memorydebug.integer)
		_Mem_CheckSentinelsGlobal(filename, fileline);
	pool = (mempool_t *)Clump_AllocBlock(sizeof(mempool_t));
	if (pool == NULL)
	{
		Mem_PrintList(0);
		Mem_PrintStats();
		Mem_PrintList(1<<30);
		Mem_PrintStats();
		Sys_Error("Mem_AllocPool: out of memory (allocpool at %s:%i)", filename, fileline);
	}
	memset(pool, 0, sizeof(mempool_t));
	pool->sentinel1 = MEMHEADER_SENTINEL_FOR_ADDRESS(&pool->sentinel1);
	pool->sentinel2 = MEMHEADER_SENTINEL_FOR_ADDRESS(&pool->sentinel2);
	pool->filename = filename;
	pool->fileline = fileline;
	pool->flags = flags;
	pool->chain = NULL;
	pool->totalsize = 0;
	pool->realsize = sizeof(mempool_t);
	strlcpy (pool->name, name, sizeof (pool->name));
	pool->parent = parent;
	pool->next = poolchain;
	poolchain = pool;
	return pool;
}

void _Mem_FreePool(mempool_t **poolpointer, const char *filename, int fileline)
{
	mempool_t *pool = *poolpointer;
	mempool_t **chainaddress, *iter, *temp;

	if (developer_memorydebug.integer)
		_Mem_CheckSentinelsGlobal(filename, fileline);
	if (pool)
	{
		                         
		for (chainaddress = &poolchain;*chainaddress && *chainaddress != pool;chainaddress = &((*chainaddress)->next));
		if (*chainaddress != pool)
			Sys_Error("Mem_FreePool: pool already free (freepool at %s:%i)", filename, fileline);
		if (pool->sentinel1 != MEMHEADER_SENTINEL_FOR_ADDRESS(&pool->sentinel1))
			Sys_Error("Mem_FreePool: trashed pool sentinel 1 (allocpool at %s:%i, freepool at %s:%i)", pool->filename, pool->fileline, filename, fileline);
		if (pool->sentinel2 != MEMHEADER_SENTINEL_FOR_ADDRESS(&pool->sentinel2))
			Sys_Error("Mem_FreePool: trashed pool sentinel 2 (allocpool at %s:%i, freepool at %s:%i)", pool->filename, pool->fileline, filename, fileline);
		*chainaddress = pool->next;

		                                
		while (pool->chain)
			_Mem_FreeBlock(pool->chain, filename, fileline);

		                        
		for(iter = poolchain; iter; iter = temp) {
			temp = iter->next;
			if(iter->parent == pool)
				_Mem_FreePool(&temp, filename, fileline);
		}

		                       
		Clump_FreeBlock(pool, sizeof(*pool));

		*poolpointer = NULL;
	}
}

void _Mem_EmptyPool(mempool_t *pool, const char *filename, int fileline)
{
	mempool_t *chainaddress;

	if (developer_memorydebug.integer)
	{
		                                                
		                                         
		for (chainaddress = poolchain;chainaddress;chainaddress = chainaddress->next)
			if (chainaddress == pool)
				break;
		if (!chainaddress)
			Sys_Error("Mem_EmptyPool: pool is already free (emptypool at %s:%i)", filename, fileline);
	}
	if (pool == NULL)
		Sys_Error("Mem_EmptyPool: pool == NULL (emptypool at %s:%i)", filename, fileline);
	if (pool->sentinel1 != MEMHEADER_SENTINEL_FOR_ADDRESS(&pool->sentinel1))
		Sys_Error("Mem_EmptyPool: trashed pool sentinel 1 (allocpool at %s:%i, emptypool at %s:%i)", pool->filename, pool->fileline, filename, fileline);
	if (pool->sentinel2 != MEMHEADER_SENTINEL_FOR_ADDRESS(&pool->sentinel2))
		Sys_Error("Mem_EmptyPool: trashed pool sentinel 2 (allocpool at %s:%i, emptypool at %s:%i)", pool->filename, pool->fileline, filename, fileline);

	                                
	while (pool->chain)
		_Mem_FreeBlock(pool->chain, filename, fileline);

	                         
	for(chainaddress = poolchain; chainaddress; chainaddress = chainaddress->next)
		if(chainaddress->parent == pool)
			_Mem_EmptyPool(chainaddress, filename, fileline);

}

void _Mem_CheckSentinels(void *data, const char *filename, int fileline)
{
	memheader_t *mem;
	unsigned int sentinel1;
	unsigned int sentinel2;

	if (data == NULL)
		Sys_Error("Mem_CheckSentinels: data == NULL (sentinel check at %s:%i)", filename, fileline);

	mem = (memheader_t *)((unsigned char *) data - sizeof(memheader_t));
	sentinel1 = MEMHEADER_SENTINEL_FOR_ADDRESS(&mem->sentinel);
	sentinel2 = MEMHEADER_SENTINEL_FOR_ADDRESS((unsigned char *) mem + sizeof(memheader_t) + mem->size);
	if (mem->sentinel != sentinel1)
		Sys_Error("Mem_Free: trashed head sentinel (alloc at %s:%i, sentinel check at %s:%i)", mem->filename, mem->fileline, filename, fileline);
	if (memcmp((unsigned char *) mem + sizeof(memheader_t) + mem->size, &sentinel2, sizeof(sentinel2)))
		Sys_Error("Mem_Free: trashed tail sentinel (alloc at %s:%i, sentinel check at %s:%i)", mem->filename, mem->fileline, filename, fileline);
}

#if MEMCLUMPING
static void _Mem_CheckClumpSentinels(memclump_t *clump, const char *filename, int fileline)
{
	                                
	if (clump->sentinel1 != MEMHEADER_SENTINEL_FOR_ADDRESS(&clump->sentinel1))
		Sys_Error("Mem_CheckClumpSentinels: trashed sentinel 1 (sentinel check at %s:%i)", filename, fileline);
	if (clump->sentinel2 != MEMHEADER_SENTINEL_FOR_ADDRESS(&clump->sentinel2))
		Sys_Error("Mem_CheckClumpSentinels: trashed sentinel 2 (sentinel check at %s:%i)", filename, fileline);
}
#endif

void _Mem_CheckSentinelsGlobal(const char *filename, int fileline)
{
	memheader_t *mem;
#if MEMCLUMPING
	memclump_t *clump;
#endif
	mempool_t *pool;
	for (pool = poolchain;pool;pool = pool->next)
	{
		if (pool->sentinel1 != MEMHEADER_SENTINEL_FOR_ADDRESS(&pool->sentinel1))
			Sys_Error("Mem_CheckSentinelsGlobal: trashed pool sentinel 1 (allocpool at %s:%i, sentinel check at %s:%i)", pool->filename, pool->fileline, filename, fileline);
		if (pool->sentinel2 != MEMHEADER_SENTINEL_FOR_ADDRESS(&pool->sentinel2))
			Sys_Error("Mem_CheckSentinelsGlobal: trashed pool sentinel 2 (allocpool at %s:%i, sentinel check at %s:%i)", pool->filename, pool->fileline, filename, fileline);
	}
	for (pool = poolchain;pool;pool = pool->next)
		for (mem = pool->chain;mem;mem = mem->next)
			_Mem_CheckSentinels((void *)((unsigned char *) mem + sizeof(memheader_t)), filename, fileline);
#if MEMCLUMPING
	for (pool = poolchain;pool;pool = pool->next)
		for (clump = clumpchain;clump;clump = clump->chain)
			_Mem_CheckClumpSentinels(clump, filename, fileline);
#endif
}

qboolean Mem_IsAllocated(mempool_t *pool, void *data)
{
	memheader_t *header;
	memheader_t *target;

	if (pool)
	{
		                       
		target = (memheader_t *)((unsigned char *) data - sizeof(memheader_t));
		for( header = pool->chain ; header ; header = header->next )
			if( header == target )
				return true;
	}
	else
	{
		                   
		for (pool = poolchain;pool;pool = pool->next)
			if (Mem_IsAllocated(pool, data))
				return true;
	}
	return false;
}

void Mem_ExpandableArray_NewArray(memexpandablearray_t *l, mempool_t *mempool, size_t recordsize, int numrecordsperarray)
{
	memset(l, 0, sizeof(*l));
	l->mempool = mempool;
	l->recordsize = recordsize;
	l->numrecordsperarray = numrecordsperarray;
}

void Mem_ExpandableArray_FreeArray(memexpandablearray_t *l)
{
	size_t i;
	if (l->maxarrays)
	{
		for (i = 0;i != l->numarrays;i++)
			Mem_Free(l->arrays[i].data);
		Mem_Free(l->arrays);
	}
	memset(l, 0, sizeof(*l));
}

void *Mem_ExpandableArray_AllocRecord(memexpandablearray_t *l)
{
	size_t i, j;
	for (i = 0;;i++)
	{
		if (i == l->numarrays)
		{
			if (l->numarrays == l->maxarrays)
			{
				memexpandablearray_array_t *oldarrays = l->arrays;
				l->maxarrays = max(l->maxarrays * 2, 128);
				l->arrays = (memexpandablearray_array_t*) Mem_Alloc(l->mempool, l->maxarrays * sizeof(*l->arrays));
				if (oldarrays)
				{
					memcpy(l->arrays, oldarrays, l->numarrays * sizeof(*l->arrays));
					Mem_Free(oldarrays);
				}
			}
			l->arrays[i].numflaggedrecords = 0;
			l->arrays[i].data = (unsigned char *) Mem_Alloc(l->mempool, (l->recordsize + 1) * l->numrecordsperarray);
			l->arrays[i].allocflags = l->arrays[i].data + l->recordsize * l->numrecordsperarray;
			l->numarrays++;
		}
		if (l->arrays[i].numflaggedrecords < l->numrecordsperarray)
		{
			for (j = 0;j < l->numrecordsperarray;j++)
			{
				if (!l->arrays[i].allocflags[j])
				{
					l->arrays[i].allocflags[j] = true;
					l->arrays[i].numflaggedrecords++;
					memset(l->arrays[i].data + l->recordsize * j, 0, l->recordsize);
					return (void *)(l->arrays[i].data + l->recordsize * j);
				}
			}
		}
	}
}

                                                                              
                    
                                                                              
                       
                                                                              
                                                                              
                                                                              
            
   
void Mem_ExpandableArray_FreeRecord(memexpandablearray_t *l, void *record)          
{
	size_t i, j;
	unsigned char *p = (unsigned char *)record;
	for (i = 0;i != l->numarrays;i++)
	{
		if (p >= l->arrays[i].data && p < (l->arrays[i].data + l->recordsize * l->numrecordsperarray))
		{
			j = (p - l->arrays[i].data) / l->recordsize;
			if (p != l->arrays[i].data + j * l->recordsize)
				Sys_Error("Mem_ExpandableArray_FreeRecord: no such record %p\n", p);
			if (!l->arrays[i].allocflags[j])
				Sys_Error("Mem_ExpandableArray_FreeRecord: record %p is already free!\n", p);
			l->arrays[i].allocflags[j] = false;
			l->arrays[i].numflaggedrecords--;
			return;
		}
	}
}

size_t Mem_ExpandableArray_IndexRange(const memexpandablearray_t *l)
{
	size_t i, j, k, end = 0;
	for (i = 0;i < l->numarrays;i++)
	{
		for (j = 0, k = 0;k < l->arrays[i].numflaggedrecords;j++)
		{
			if (l->arrays[i].allocflags[j])
			{
				end = l->numrecordsperarray * i + j + 1;
				k++;
			}
		}
	}
	return end;
}

void *Mem_ExpandableArray_RecordAtIndex(const memexpandablearray_t *l, size_t index)
{
	size_t i, j;
	i = index / l->numrecordsperarray;
	j = index % l->numrecordsperarray;
	if (i >= l->numarrays || !l->arrays[i].allocflags[j])
		return NULL;
	return (void *)(l->arrays[i].data + j * l->recordsize);
}


                                                                            
                                                                           
                    
mempool_t *tempmempool;
                
mempool_t *zonemempool;

void Mem_PrintStats(void)
{
	size_t count = 0, size = 0, realsize = 0;
	mempool_t *pool;
	memheader_t *mem;
	Mem_CheckSentinelsGlobal();
	for (pool = poolchain;pool;pool = pool->next)
	{
		count++;
		size += pool->totalsize;
		realsize += pool->realsize;
	}
	Con_Printf("%lu memory pools, totalling %lu bytes (%.3fMB)\n", (unsigned long)count, (unsigned long)size, size / 1048576.0);
	Con_Printf("total allocated size: %lu bytes (%.3fMB)\n", (unsigned long)realsize, realsize / 1048576.0);
	for (pool = poolchain;pool;pool = pool->next)
	{
		if ((pool->flags & POOLFLAG_TEMP) && pool->chain)
		{
			Con_Printf("Memory pool %p has sprung a leak totalling %lu bytes (%.3fMB)!  Listing contents...\n", (void *)pool, (unsigned long)pool->totalsize, pool->totalsize / 1048576.0);
			for (mem = pool->chain;mem;mem = mem->next)
				Con_Printf("%10lu bytes allocated at %s:%i\n", (unsigned long)mem->size, mem->filename, mem->fileline);
		}
	}
}

void Mem_PrintList(size_t minallocationsize)
{
	mempool_t *pool;
	memheader_t *mem;
	Mem_CheckSentinelsGlobal();
	Con_Print("memory pool list:\n"
	           "size    name\n");
	for (pool = poolchain;pool;pool = pool->next)
	{
		Con_Printf("%10luk (%10luk actual) %s (%+li byte change) %s\n", (unsigned long) ((pool->totalsize + 1023) / 1024), (unsigned long)((pool->realsize + 1023) / 1024), pool->name, (long)(pool->totalsize - pool->lastchecksize), (pool->flags & POOLFLAG_TEMP) ? "TEMP" : "");
		pool->lastchecksize = pool->totalsize;
		for (mem = pool->chain;mem;mem = mem->next)
			if (mem->size >= minallocationsize)
				Con_Printf("%10lu bytes allocated at %s:%i\n", (unsigned long)mem->size, mem->filename, mem->fileline);
	}
}

static void MemList_f(void)
{
	switch(Cmd_Argc())
	{
	case 1:
		Mem_PrintList(1<<30);
		Mem_PrintStats();
		break;
	case 2:
		Mem_PrintList(atoi(Cmd_Argv(1)) * 1024);
		Mem_PrintStats();
		break;
	default:
		Con_Print("MemList_f: unrecognized options\nusage: memlist [all]\n");
		break;
	}
}

static void MemStats_f(void)
{
	Mem_CheckSentinelsGlobal();
	R_TextureStats_Print(false, false, true);
	GL_Mesh_ListVBOs(false);
	Mem_PrintStats();
}


char* Mem_strdup (mempool_t *pool, const char* s)
{
	char* p;
	size_t sz;
	if (s == NULL)
		return NULL;
	sz = strlen (s) + 1;
	p = (char*)Mem_Alloc (pool, sz);
	strlcpy (p, s, sz);
	return p;
}

  
                        
           
                        
  
void Memory_Init (void)
{
	static union {unsigned short s;unsigned char b[2];} u;
	u.s = 0x100;
	mem_bigendian = u.b[0] != 0;

	sentinel_seed = rand();
	poolchain = NULL;
	tempmempool = Mem_AllocPool("Temporary Memory", POOLFLAG_TEMP, NULL);
	zonemempool = Mem_AllocPool("Zone", 0, NULL);

	if (Thread_HasThreads())
		mem_mutex = Thread_CreateMutex();
}

void Memory_Shutdown (void)
{
                               
                               

	if (mem_mutex)
		Thread_DestroyMutex(mem_mutex);
	mem_mutex = NULL;
}

void Memory_Init_Commands (void)
{
	Cmd_AddCommand ("memstats", MemStats_f, "prints memory system statistics");
	Cmd_AddCommand ("memlist", MemList_f, "prints memory pool information (or if used as memlist 5 lists individual allocations of 5K or larger, 0 lists all allocations)");
	Cvar_RegisterVariable (&developer_memory);
	Cvar_RegisterVariable (&developer_memorydebug);
	Cvar_RegisterVariable (&developer_memoryreportlargerthanmb);
	Cvar_RegisterVariable (&sys_memsize_physical);
	Cvar_RegisterVariable (&sys_memsize_virtual);

#if defined(WIN32)
#ifdef _WIN64
	{
		MEMORYSTATUSEX status;
		              
		Cvar_SetValueQuick(&sys_memsize_virtual, 8388608);
		               
		status.dwLength = sizeof(status);
		if(GlobalMemoryStatusEx(&status))
		{
			Cvar_SetValueQuick(&sys_memsize_physical, status.ullTotalPhys / 1048576.0);
			Cvar_SetValueQuick(&sys_memsize_virtual, min(sys_memsize_virtual.value, status.ullTotalVirtual / 1048576.0));
		}
	}
#else
	{
		MEMORYSTATUS status;
		              
		Cvar_SetValueQuick(&sys_memsize_virtual, 2048);
		               
		status.dwLength = sizeof(status);
		GlobalMemoryStatus(&status);
		Cvar_SetValueQuick(&sys_memsize_physical, status.dwTotalPhys / 1048576.0);
		Cvar_SetValueQuick(&sys_memsize_virtual, min(sys_memsize_virtual.value, status.dwTotalVirtual / 1048576.0));
	}
#endif
#else
	{
		              
		Cvar_SetValueQuick(&sys_memsize_virtual, (sizeof(void*) == 4) ? 2048 : 268435456);
		               
		{
			                                        
			FILE *f = fopen("/proc/meminfo", "r");
			if(f)
			{
				static char buf[1024];
				while(fgets(buf, sizeof(buf), f))
				{
					const char *p = buf;
					if(!COM_ParseToken_Console(&p))
						continue;
					if(!strcmp(com_token, "MemTotal:"))
					{
						if(!COM_ParseToken_Console(&p))
							continue;
						Cvar_SetValueQuick(&sys_memsize_physical, atof(com_token) / 1024.0);
					}
					if(!strcmp(com_token, "SwapTotal:"))
					{
						if(!COM_ParseToken_Console(&p))
							continue;
						Cvar_SetValueQuick(&sys_memsize_virtual, min(sys_memsize_virtual.value , atof(com_token) / 1024.0 + sys_memsize_physical.value));
					}
				}
				fclose(f);
			}
		}
	}
#endif
}

