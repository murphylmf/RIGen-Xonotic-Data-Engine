#ifndef FT2_PRIVATE_H__
#define FT2_PRIVATE_H__

                                                       
                                                
#define FONT_CHARS_PER_LINE 16
#define FONT_CHAR_LINES 16
#define FONT_CHARS_PER_MAP (FONT_CHARS_PER_LINE * FONT_CHAR_LINES)

typedef struct glyph_slot_s
{
	qboolean image;
	                                              
	                                                                           
	float txmin;                               
	float txmax;
	float tymin;
	float tymax;
	float vxmin;
	float vxmax;
	float vymin;
	float vymax;
	float advance_x;
	float advance_y;
} glyph_slot_t;

struct ft2_font_map_s
{
	Uchar                  start;
	struct ft2_font_map_s *next;
	float                  size;
	                                            
	                                                                              
	float                  intSize;
	int                    glyphSize;

	cachepic_t            *pic;
	qboolean               static_tex;
	glyph_slot_t           glyphs[FONT_CHARS_PER_MAP];

	                                                                
	                                                                   
	ft2_kerning_t          kerning;
	                                                                
	double                 sfx, sfy;

	                                                               
	float           width_of[256];
};

struct ft2_attachment_s
{
	const unsigned char *data;
	fs_offset_t    size;
};

                                                                                      
qboolean Font_LoadMapForIndex(ft2_font_t *font, int map_index, Uchar _ch, ft2_font_map_t **outmap);

void font_start(void);
void font_shutdown(void);
void font_newmap(void);

#endif                   
