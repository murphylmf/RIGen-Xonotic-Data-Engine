  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           
  

#include "quakedef.h"

#include <signal.h>

int cl_available = false;

qboolean vid_supportrefreshrate = false;

void VID_Shutdown(void)
{
}

static void signal_handler(int sig)
{
	Con_Printf("Received signal %d, exiting...\n", sig);
	Sys_Quit(1);
}

static void InitSig(void)
{
#ifndef WIN32
	signal(SIGHUP, signal_handler);
	signal(SIGINT, signal_handler);
	signal(SIGQUIT, signal_handler);
	signal(SIGILL, signal_handler);
	signal(SIGTRAP, signal_handler);
	signal(SIGIOT, signal_handler);
	signal(SIGBUS, signal_handler);
	signal(SIGFPE, signal_handler);
	signal(SIGSEGV, signal_handler);
	signal(SIGTERM, signal_handler);
#endif
}

void VID_SetMouse (qboolean fullscreengrab, qboolean relative, qboolean hidecursor)
{
}

void VID_Finish (void)
{
}

void VID_Init(void)
{
	InitSig();                     
}

qboolean VID_InitMode(viddef_mode_t *mode)
{
	return false;
}

void *GL_GetProcAddress(const char *name)
{
	return NULL;
}

void Sys_SendKeyEvents(void)
{
}

void VID_BuildJoyState(vid_joystate_t *joystate)
{
}

void IN_Move(void)
{
}

vid_mode_t *VID_GetDesktopMode(void)
{
	return NULL;
}

size_t VID_ListModes(vid_mode_t *modes, size_t maxcount)
{
	return 0;
}
