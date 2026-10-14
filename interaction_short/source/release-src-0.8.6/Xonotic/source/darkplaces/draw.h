  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

                                                                     
                          

#ifndef DRAW_H
#define DRAW_H

                                      
typedef struct cachepic_s
{
	              
	int width, height;
	                                                                      
	int autoload;
	                               
	int texflags;
	                                     
	int lastusedframe;
	                          
	rtexture_t *tex;
	                        
	struct cachepic_s *chain;
	                                          
	unsigned int flags;
	             
	qboolean hasalpha;
	              
	char name[MAX_QPATH];
	                                     
	qboolean allow_free_tex;
}
cachepic_t;

typedef enum cachepicflags_e
{
	CACHEPICFLAG_NOTPERSISTENT = 1,
	CACHEPICFLAG_QUIET = 2,
	CACHEPICFLAG_NOCOMPRESSION = 4,
	CACHEPICFLAG_NOCLAMP = 8,
	CACHEPICFLAG_NEWPIC = 16,                                                                                                          
	CACHEPICFLAG_MIPMAP = 32,
	CACHEPICFLAG_NEAREST = 64                                             
}
cachepicflags_t;

void Draw_Init (void);
void Draw_Frame (void);
cachepic_t *Draw_CachePic_Flags (const char *path, unsigned int cachepicflags);
cachepic_t *Draw_CachePic (const char *path);                                                             
                                 
cachepic_t *Draw_NewPic(const char *picname, int width, int height, int alpha, unsigned char *pixels);
                                        
void Draw_FreePic(const char *picname);

                    
                          
                            
                         
typedef struct drawqueuemesh_s
{
	rtexture_t *texture;
	int num_triangles;
	int num_vertices;
	int *data_element3i;
	unsigned short *data_element3s;
	float *data_vertex3f;
	float *data_texcoord2f;
	float *data_color4f;
}
drawqueuemesh_t;

enum drawqueue_drawflag_e {
DRAWFLAG_NORMAL,
DRAWFLAG_ADDITIVE,
DRAWFLAG_MODULATE,
DRAWFLAG_2XMODULATE,
DRAWFLAG_SCREEN,
DRAWFLAG_NUMFLAGS,
DRAWFLAG_MASK = 0xFF,                           
DRAWFLAG_MIPMAP = 0x100,                         
DRAWFLAG_NOGAMMA = 0x200                          
};
#define DRAWFLAGS_BLEND 0xFF                                      

typedef struct ft2_settings_s
{
	float scale, voffset;
	                                                  
	int antialias, hinting;
	float outline, blur, shadowx, shadowy, shadowz;
} ft2_settings_t;

#define MAX_FONT_SIZES 16
#define MAX_FONT_FALLBACKS 3
typedef struct dp_font_s
{
	rtexture_t *tex;
	float width_of[256];                                                                                                                                                    
	float maxwidth;                                                        
	char texpath[MAX_QPATH];
	char title[MAX_QPATH];

	int req_face;                                   
	float req_sizes[MAX_FONT_SIZES];                                                                                                                                               
	char fallbacks[MAX_FONT_FALLBACKS][MAX_QPATH];
	int fallback_faces[MAX_FONT_FALLBACKS];
	struct ft2_font_s *ft2;

	ft2_settings_t settings;
}
dp_font_t;

typedef struct dp_fonts_s
{
	dp_font_t *f;
	int maxsize;
}
dp_fonts_t;
extern dp_fonts_t dp_fonts;

#define MAX_FONTS         16                      
#define FONTS_EXPAND       8                                  
#define FONT_DEFAULT     (&dp_fonts.f[0])                         
#define FONT_CONSOLE     (&dp_fonts.f[1])                                      
#define FONT_SBAR        (&dp_fonts.f[2])                       
#define FONT_NOTIFY      (&dp_fonts.f[3])        
#define FONT_CHAT        (&dp_fonts.f[4])        
#define FONT_CENTERPRINT (&dp_fonts.f[5])        
#define FONT_INFOBAR     (&dp_fonts.f[6])        
#define FONT_MENU        (&dp_fonts.f[7])                         
#define FONT_USER(i)     (&dp_fonts.f[8+i])                     
#define MAX_USERFONTS    (dp_fonts.maxsize - 8)

                                      
#define STRING_COLOR_TAG			'^'
#define STRING_COLOR_DEFAULT		7
#define STRING_COLOR_DEFAULT_STR	"^7"
#define STRING_COLOR_RGB_TAG_CHAR	'x'
#define STRING_COLOR_RGB_TAG		"^x"

                                                                                                                                         

                                                       
void DrawQ_Pic(float x, float y, cachepic_t *pic, float width, float height, float red, float green, float blue, float alpha, int flags);
                       
void DrawQ_RotPic(float x, float y, cachepic_t *pic, float width, float height, float org_x, float org_y, float angle, float red, float green, float blue, float alpha, int flags);
                                                                           
void DrawQ_Fill(float x, float y, float width, float height, float red, float green, float blue, float alpha, int flags);
                      
                                   
                                       
                                                                                                                                                                         
                                                 
                                                                                                                                                                                                                 
extern float DrawQ_Color[4];
float DrawQ_String(float x, float y, const char *text, size_t maxlen, float scalex, float scaley, float basered, float basegreen, float baseblue, float basealpha, int flags, int *outcolor, qboolean ignorecolorcodes, const dp_font_t *fnt);
float DrawQ_String_Scale(float x, float y, const char *text, size_t maxlen, float sizex, float sizey, float scalex, float scaley, float basered, float basegreen, float baseblue, float basealpha, int flags, int *outcolor, qboolean ignorecolorcodes, const dp_font_t *fnt);
float DrawQ_TextWidth(const char *text, size_t maxlen, float w, float h, qboolean ignorecolorcodes, const dp_font_t *fnt);
float DrawQ_TextWidth_UntilWidth(const char *text, size_t *maxlen, float w, float h, qboolean ignorecolorcodes, const dp_font_t *fnt, float maxWidth);
float DrawQ_TextWidth_UntilWidth_TrackColors(const char *text, size_t *maxlen, float w, float h, int *outcolor, qboolean ignorecolorcodes, const dp_font_t *fnt, float maxwidth);
float DrawQ_TextWidth_UntilWidth_TrackColors_Scale(const char *text, size_t *maxlen, float w, float h, float sw, float sh, int *outcolor, qboolean ignorecolorcodes, const dp_font_t *fnt, float maxwidth);
                                                                                         
void DrawQ_SuperPic(float x, float y, cachepic_t *pic, float width, float height, float s1, float t1, float r1, float g1, float b1, float a1, float s2, float t2, float r2, float g2, float b2, float a2, float s3, float t3, float r3, float g3, float b3, float a3, float s4, float t4, float r4, float g4, float b4, float a4, int flags);
                       
void DrawQ_Mesh(drawqueuemesh_t *mesh, int flags, qboolean hasalpha);
                        
void DrawQ_SetClipArea(float x, float y, float width, float height);
                          
void DrawQ_ResetClipArea(void);
              
void DrawQ_Line(float width, float x1, float y1, float x2, float y2, float r, float g, float b, float alpha, int flags);
                                                                  
void DrawQ_Lines(float width, int numlines, int flags, qboolean hasalpha);
                   
void DrawQ_LineLoop(drawqueuemesh_t *mesh, int flags);
                              
void DrawQ_Finish(void);
void DrawQ_ProcessDrawFlag(int flags, qboolean alpha);                                      
void DrawQ_RecalcView(void);                                                         

rtexture_t *Draw_GetPicTexture(cachepic_t *pic);

extern rtexturepool_t *drawtexturepool;                 

#endif

