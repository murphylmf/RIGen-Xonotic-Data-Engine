  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
                                                          

#ifndef INPUT_H
#define INPUT_H

extern cvar_t in_pitch_min;
extern cvar_t in_pitch_max;

extern qboolean in_client_mouse;
extern float in_windowmouse_x, in_windowmouse_y;
extern float in_mouse_x, in_mouse_y;

                                                                     

void IN_Move (void);
                                                          

#define IN_BESTWEAPON_MAX 32
typedef struct
{
	char name[32];
	int impulse;
	int activeweaponcode;
	int weaponbit;
	int ammostat;
	int ammomin;
	                                                                                  
}
in_bestweapon_info_t;
extern in_bestweapon_info_t in_bestweapon_info[IN_BESTWEAPON_MAX];
void IN_BestWeapon_ResetData(void);                                                             

#endif

