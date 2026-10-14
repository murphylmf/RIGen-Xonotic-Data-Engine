                                                       
             
   

#ifndef DP_FREETYPE2_H__
#define DP_FREETYPE2_H__

                        

#include "utf8lib.h"

   
                                                        
  
                                 
                                                   
  
          
                      
                                                        
   

typedef struct ft2_font_map_s ft2_font_map_t;
typedef struct ft2_attachment_s ft2_attachment_t;
#ifdef WIN64
#define ft2_oldstyle_map ((ft2_font_map_t*)-1LL)
#else
#define ft2_oldstyle_map ((ft2_font_map_t*)-1)
#endif

typedef float ft2_kernvec[2];
typedef struct ft2_kerning_s
{
	ft2_kernvec kerning[256][256];                                     
} ft2_kerning_t;

typedef struct ft2_font_s
{
	char            name[64];
	qboolean        has_kerning;
	                                                
	float		currentw;
	float		currenth;
	float           ascend;
	float           descend;
	qboolean        image_font;                                     

	                                                    
	
	const unsigned char  *data;                        
	                           
	void           *face;

	                                                                               
	ft2_font_map_t *font_maps[MAX_FONT_SIZES];
	int             num_sizes;

	              
	size_t            attachmentcount;
	ft2_attachment_t *attachments;

	ft2_settings_t *settings;

	                     
	struct ft2_font_s *next;
} ft2_font_t;

void            Font_CloseLibrary(void);
void            Font_Init(void);
qboolean        Font_OpenLibrary(void);
ft2_font_t*     Font_Alloc(void);
void            Font_UnloadFont(ft2_font_t *font);
                                                                                               
                                                                                   
                                                                                        
int             Font_IndexForSize(ft2_font_t *font, float size, float *outw, float *outh);
ft2_font_map_t *Font_MapForIndex(ft2_font_t *font, int index);
qboolean        Font_LoadFont(const char *name, dp_font_t *dpfnt);
qboolean        Font_GetKerningForSize(ft2_font_t *font, float w, float h, Uchar left, Uchar right, float *outx, float *outy);
qboolean        Font_GetKerningForMap(ft2_font_t *font, int map_index, float w, float h, Uchar left, Uchar right, float *outx, float *outy);
float           Font_VirtualToRealSize(float sz);
float           Font_SnapTo(float val, float snapwidth);
                                                              
ft2_font_map_t *FontMap_FindForChar(ft2_font_map_t *start, Uchar ch);
#endif                    
