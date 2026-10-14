  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

#ifndef MENU_H
#define MENU_H

enum m_state_e {
	m_none,
	m_main,
	m_demo,
	m_singleplayer,
	m_transfusion_episode,
	m_transfusion_skill,
	m_load,
	m_save,
	m_multiplayer,
	m_setup,
	m_options,
	m_video,
	m_keys,
	m_help,
	m_credits,
	m_quit,
	m_lanconfig,
	m_gameoptions,
	m_slist,
	m_options_effects,
	m_options_graphics,
	m_options_colorcontrol,
	m_reset,
	m_modlist
};

extern enum m_state_e m_state;
extern char m_return_reason[128];
void M_Update_Return_Reason(const char *s);

  
                   
  
                   
                          
                   
                             

  
                 
  
                    
                           
                    
                              
                          

  
              
  

void MR_Init_Commands (void);
void MR_Init (void);
void MR_Restart (void);
extern void (*MR_KeyEvent) (int key, int ascii, qboolean downevent);
extern void (*MR_Draw) (void);
extern void (*MR_ToggleMenu) (int mode);
extern void (*MR_Shutdown) (void);
extern void (*MR_NewMap) (void);
extern int (*MR_GetServerListEntryCategory) (const serverlist_entry_t *entry);

typedef struct video_resolution_s
{
	const char *type;
	int width, height;
	int conwidth, conheight;
	double pixelheight;                  
}
video_resolution_t;
extern video_resolution_t *video_resolutions;
extern int video_resolutions_count;
extern video_resolution_t video_resolutions_hardcoded[];
extern int video_resolutions_hardcoded_count;
#endif

