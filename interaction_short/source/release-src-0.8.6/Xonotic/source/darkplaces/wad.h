  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
        

#ifndef WAD_H
#define WAD_H

                 
          
                 

#define	CMP_NONE		0
#define	CMP_LZSS		1

#define	TYP_NONE		0
#define	TYP_LABEL		1

#define	TYP_LUMPY		64				                           
#define	TYP_PALETTE		64
#define	TYP_QTEX		65
#define	TYP_QPIC		66
#define	TYP_SOUND		67
#define	TYP_MIPTEX		68

typedef struct qpic_s
{
	int			width, height;
	unsigned char		data[4];			                 
} qpic_t;



typedef struct wadinfo_s
{
	char		identification[4];		                         
	int			numlumps;
	int			infotableofs;
} wadinfo_t;

typedef struct lumpinfo_s
{
	int			filepos;
	int			disksize;
	int			size;					               
	char		type;
	char		compression;
	char		pad1, pad2;
	char		name[16];				                          
} lumpinfo_t;

void W_UnloadAll(void);
unsigned char *W_GetLumpName(const char *name);

                        
void W_LoadTextureWadFile(char *filename, int complain);
unsigned char *W_GetTextureBGRA(char *name);                                                                                                  
unsigned char *W_ConvertWAD3TextureBGRA(sizebuf_t *sb);                                                                                                  

#endif

