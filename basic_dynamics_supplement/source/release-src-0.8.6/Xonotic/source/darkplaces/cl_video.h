
#ifndef CL_VIDEO_H
#define CL_VIDEO_H

#include "cl_dyntexture.h"

                                                                         
#define CLVIDEOPREFIX	CLDYNTEXTUREPREFIX "video/"
#define CLTHRESHOLD		2.0

#define MENUOWNER		1

typedef enum clvideostate_e
{
	CLVIDEO_UNUSED,
	CLVIDEO_PLAY,
	CLVIDEO_LOOP,
	CLVIDEO_PAUSE,
	CLVIDEO_FIRSTFRAME,
	CLVIDEO_RESETONWAKEUP,
	CLVIDEO_STATECOUNT
} clvideostate_t;

#define CLVIDEO_MAX_SUBTITLES 512

extern cvar_t cl_video_subtitles;
extern cvar_t cl_video_subtitles_lines;
extern cvar_t cl_video_subtitles_textsize;
extern cvar_t cl_video_scale;
extern cvar_t cl_video_scale_vpos;
extern cvar_t cl_video_stipple;
extern cvar_t cl_video_brightness;
extern cvar_t cl_video_keepaspectratio;

typedef struct clvideo_s
{
	int		ownertag;
	clvideostate_t state;

	                
	void	*stream;

	double	starttime;
	int		framenum;
	double	framerate;

	void	*imagedata;

	cachepic_t cpif;

	                          
	int		subtitles;
	char	*subtitle_text[CLVIDEO_MAX_SUBTITLES];
	float	subtitle_start[CLVIDEO_MAX_SUBTITLES];
	float	subtitle_end[CLVIDEO_MAX_SUBTITLES];

	                                                    
	void (*close) (void *stream);
	unsigned int (*getwidth) (void *stream);
	unsigned int (*getheight) (void *stream);
	double (*getframerate) (void *stream);
	double (*getaspectratio) (void *stream);
	int (*decodeframe) (void *stream, void *imagedata, unsigned int Rmask, unsigned int Gmask, unsigned int Bmask, unsigned int bytesperpixel, int imagebytesperrow);

	                                                                                                   
	                                                                         
    double  lasttime;
	                                                                    
	qboolean suspended;

	char	filename[MAX_QPATH];
} clvideo_t;

clvideo_t*	CL_OpenVideo( const char *filename, const char *name, int owner, const char *subtitlesfile );
clvideo_t*	CL_GetVideoByName( const char *name );
void		CL_SetVideoState( clvideo_t *video, clvideostate_t state );
void		CL_RestartVideo( clvideo_t *video );

void		CL_CloseVideo( clvideo_t * video );
void		CL_PurgeOwner( int owner );

void		CL_Video_Frame( void );                     
void		CL_Video_Init( void );
void		CL_Video_Shutdown( void );

                
extern int cl_videoplaying;

void CL_DrawVideo( void );
void CL_VideoStart( char *filename, const char *subtitlesfile );
void CL_VideoStop( void );

                                          
                                                                                                                                                        
void CL_Video_KeyEvent( int key, int ascii, qboolean down );

#endif
