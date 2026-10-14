
#ifdef WIN32
#include <windows.h>
#else
#include <dirent.h>
#endif

#include "quakedef.h"

                                                                                                                            

int matchpattern(const char *in, const char *pattern, int caseinsensitive)
{
	return matchpattern_with_separator(in, pattern, caseinsensitive, "/\\:", false);
}

                                                             
                                                              
int matchpattern_with_separator(const char *in, const char *pattern, int caseinsensitive, const char *separators, qboolean wildcard_least_one)
{
	int c1, c2;
	while (*pattern)
	{
		switch (*pattern)
		{
		case 0:
			return 1;                  
		case '?':                              
			if (*in == 0 || strchr(separators, *in))
				return 0;            
			in++;
			pattern++;
			break;
		case '*':                                         
			if(wildcard_least_one)
			{
				if (*in == 0 || strchr(separators, *in))
					return 0;            
				in++;
			}
			pattern++;
			while (*in)
			{
				if (strchr(separators, *in))
					break;
				                                        
				if (matchpattern_with_separator(in, pattern, caseinsensitive, separators, wildcard_least_one))
					return 1;
				                               
				in++;
			}
			break;
		default:
			if (*in != *pattern)
			{
				if (!caseinsensitive)
					return 0;            
				c1 = *in;
				if (c1 >= 'A' && c1 <= 'Z')
					c1 += 'a' - 'A';
				c2 = *pattern;
				if (c2 >= 'A' && c2 <= 'Z')
					c2 += 'a' - 'A';
				if (c1 != c2)
					return 0;            
			}
			in++;
			pattern++;
			break;
		}
	}
	if (*in)
		return 0;                                               
	return 1;           
}

                          
void stringlistinit(stringlist_t *list)
{
	memset(list, 0, sizeof(*list));
}

void stringlistfreecontents(stringlist_t *list)
{
	int i;
	for (i = 0;i < list->numstrings;i++)
	{
		if (list->strings[i])
			Z_Free(list->strings[i]);
		list->strings[i] = NULL;
	}
	list->numstrings = 0;
	list->maxstrings = 0;
	if (list->strings)
		Z_Free(list->strings);
	list->strings = NULL;
}

void stringlistappend(stringlist_t *list, const char *text)
{
	size_t textlen;
	char **oldstrings;

	if (list->numstrings >= list->maxstrings)
	{
		oldstrings = list->strings;
		list->maxstrings += 4096;
		list->strings = (char **) Z_Malloc(list->maxstrings * sizeof(*list->strings));
		if (list->numstrings)
			memcpy(list->strings, oldstrings, list->numstrings * sizeof(*list->strings));
		if (oldstrings)
			Z_Free(oldstrings);
	}
	textlen = strlen(text) + 1;
	list->strings[list->numstrings] = (char *) Z_Malloc(textlen);
	memcpy(list->strings[list->numstrings], text, textlen);
	list->numstrings++;
}

static int stringlistsort_cmp(const void *a, const void *b)
{
	return strcasecmp(*(const char **)a, *(const char **)b);
}

void stringlistsort(stringlist_t *list, qboolean uniq)
{
	int i, j;
	if(list->numstrings < 1)
		return;
	qsort(&list->strings[0], list->numstrings, sizeof(list->strings[0]), stringlistsort_cmp);
	if(uniq)
	{
		                      
		                           
		for (i = 1, j = 0; i < list->numstrings; ++i)
		{
			char *save;
			if(!strcasecmp(list->strings[i], list->strings[j]))
				continue;
			++j;
			save = list->strings[j];
			list->strings[j] = list->strings[i];
			list->strings[i] = save;
		}
		for(i = j+1; i < list->numstrings; ++i)
		{
			if (list->strings[i])
				Z_Free(list->strings[i]);
		}
		list->numstrings = j+1;
	}
}

                                 
static void adddirentry(stringlist_t *list, const char *path, const char *name)
{
	if (strcmp(name, ".") && strcmp(name, ".."))
	{
		char temp[MAX_OSPATH];
		dpsnprintf( temp, sizeof( temp ), "%s%s", path, name );
		stringlistappend(list, temp);
	}
}
#ifdef WIN32
void listdirectory(stringlist_t *list, const char *basepath, const char *path)
{
	char pattern[4096];
	WIN32_FIND_DATA n_file;
	HANDLE hFile;
	strlcpy (pattern, basepath, sizeof(pattern));
	strlcat (pattern, path, sizeof (pattern));
	strlcat (pattern, "*", sizeof (pattern));
	                                       
	hFile = FindFirstFile(pattern, &n_file);
	if(hFile == INVALID_HANDLE_VALUE)
		return;
	do {
		adddirentry(list, path, n_file.cFileName);
	} while (FindNextFile(hFile, &n_file) != 0);
	FindClose(hFile);
}
#else
void listdirectory(stringlist_t *list, const char *basepath, const char *path)
{
	char fullpath[MAX_OSPATH];
	DIR *dir;
	struct dirent *ent;
	dpsnprintf(fullpath, sizeof(fullpath), "%s%s", basepath, path);
#ifdef __ANDROID__
	                                                                       
	                                                              
	if (basepath[0] != '/')
	{
		char listpath[MAX_OSPATH];
		qfile_t *listfile;
		dpsnprintf(listpath, sizeof(listpath), "%sls.txt", fullpath);
		char *buf = (char *) FS_SysLoadFile(listpath, tempmempool, true, NULL);
		if (!buf)
			return;
		char *p = buf;
		for (;;)
		{
			char *q = strchr(p, '\n');
			if (q == NULL)
				break;
			*q = 0;
			adddirentry(list, path, p);
			p = q + 1;
		}
		Mem_Free(buf);
		return;
	}
#endif
	dir = opendir(fullpath);
	if (!dir)
		return;

	while ((ent = readdir(dir)))
		adddirentry(list, path, ent->d_name);
	closedir(dir);
}
#endif

