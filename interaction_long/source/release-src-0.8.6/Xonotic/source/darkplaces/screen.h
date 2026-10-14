  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
           

#ifndef SCREEN_H
#define SCREEN_H

void CL_Screen_Init (void);
void CL_UpdateScreen (void);
void SCR_CenterPrint(const char *str);

void SCR_BeginLoadingPlaque (qboolean startup);

                                                       
void SCR_UpdateLoadingScreen(qboolean clear, qboolean startup);
void SCR_UpdateLoadingScreenIfShown(void);

                                       
void SCR_PushLoadingScreen (qboolean redraw, const char *msg, float len_in_parent);
void SCR_PopLoadingScreen (qboolean redraw);
void SCR_ClearLoadingScreen (qboolean redraw);

extern float scr_con_current;                                       

extern int sb_lines;

extern cvar_t scr_viewsize;
extern cvar_t scr_fov;
extern cvar_t showfps;
extern cvar_t showtime;
extern cvar_t showdate;

extern cvar_t crosshair;
extern cvar_t crosshair_size;

extern cvar_t scr_conalpha;
extern cvar_t scr_conalphafactor;
extern cvar_t scr_conalpha2factor;
extern cvar_t scr_conalpha3factor;
extern cvar_t scr_conscroll_x;
extern cvar_t scr_conscroll_y;
extern cvar_t scr_conscroll2_x;
extern cvar_t scr_conscroll2_y;
extern cvar_t scr_conscroll3_x;
extern cvar_t scr_conscroll3_y;
extern cvar_t scr_conbrightness;
extern cvar_t r_letterbox;

extern cvar_t scr_refresh;
extern cvar_t scr_stipple;

extern cvar_t r_stereo_separation;
extern cvar_t r_stereo_angle;
qboolean R_Stereo_Active(void);
extern int r_stereo_side;

typedef struct scr_touchscreenarea_s
{
	const char *pic;
	const char *text;
	float rect[4];
	float textheight;
	float active;
	float activealpha;
	float inactivealpha;
}
scr_touchscreenarea_t;

                                    
extern int scr_numtouchscreenareas;
extern scr_touchscreenarea_t scr_touchscreenareas[128];

#endif

