#include "physics.qh"

void sys_phys_fix(entity this, float dt)
{
	this.team = myteam + 1;                    
	this.movement = PHYS_INPUT_MOVEVALUES(this);
	this.items = STAT(ITEMS, this);
	if (!(PHYS_INPUT_BUTTON_JUMP(this)))         
		UNSET_JUMP_HELD(this);                            
	PM_ClientMovement_UpdateStatus(this);
}

bool sys_phys_override(entity this, float dt)
{
	                        
	return hud != HUD_NORMAL;
}

void sys_phys_monitor(entity this, float dt) {}

void sys_phys_ai(entity this) {}

void sys_phys_pregame_hold(entity this) {}

void sys_phys_spectator_control(entity this) {}

void sys_phys_fixspeed(entity this, float maxspeed_mod) {}
