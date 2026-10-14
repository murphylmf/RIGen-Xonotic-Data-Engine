#include "sv_dodging.qh"

                                                                                                                    

#define PHYS_DODGING 						g_dodging
#define PHYS_DODGING_DELAY 					autocvar_sv_dodging_delay
#define PHYS_DODGING_DISTANCE_THRESHOLD 	autocvar_sv_dodging_wall_distance_threshold
#define PHYS_DODGING_FROZEN_DOUBLETAP		autocvar_sv_dodging_frozen_doubletap
#define PHYS_DODGING_HEIGHT_THRESHOLD 		autocvar_sv_dodging_height_threshold
#define PHYS_DODGING_HORIZ_SPEED_MIN		autocvar_sv_dodging_horiz_speed_min
#define PHYS_DODGING_HORIZ_SPEED_MAX		autocvar_sv_dodging_horiz_speed_max
#define PHYS_DODGING_HORIZ_FORCE_SLOWEST	autocvar_sv_dodging_horiz_force_slowest
#define PHYS_DODGING_HORIZ_FORCE_FASTEST	autocvar_sv_dodging_horiz_force_fastest
#define PHYS_DODGING_HORIZ_FORCE_FROZEN 	autocvar_sv_dodging_horiz_force_frozen
#define PHYS_DODGING_RAMP_TIME 				autocvar_sv_dodging_ramp_time
#define PHYS_DODGING_UP_SPEED 				autocvar_sv_dodging_up_speed
#define PHYS_DODGING_WALL 					autocvar_sv_dodging_wall_dodging
#define PHYS_DODGING_AIR 					autocvar_sv_dodging_air_dodging
#define PHYS_DODGING_MAXSPEED 				autocvar_sv_dodging_maxspeed
#define PHYS_DODGING_AIR_MAXSPEED			autocvar_sv_dodging_air_maxspeed
#define PHYS_DODGING_CLIENTSELECT			autocvar_sv_dodging_clientselect

                                                                                           
#if 0
#define PHYS_DODGING 						STAT(DODGING, this)
#define PHYS_DODGING_DELAY 					STAT(DODGING_DELAY, this)
#define PHYS_DODGING_DISTANCE_THRESHOLD 	STAT(DODGING_DISTANCE_THRESHOLD, this)
#define PHYS_DODGING_FROZEN_DOUBLETAP		STAT(DODGING_FROZEN_DOUBLETAP, this)
#define PHYS_DODGING_HEIGHT_THRESHOLD 		STAT(DODGING_HEIGHT_THRESHOLD, this)
#define PHYS_DODGING_HORIZ_SPEED_MIN		STAT(DODGING_HORIZ_SPEED_MIN, this)
#define PHYS_DODGING_HORIZ_SPEED_MAX		STAT(DODGING_HORIZ_SPEED_MAX, this)
#define PHYS_DODGING_HORIZ_FORCE_SLOWEST	STAT(DODGING_HORIZ_FORCE_SLOWEST, this)
#define PHYS_DODGING_HORIZ_FORCE_FASTEST	STAT(DODGING_HORIZ_FORCE_FASTEST, this)
#define PHYS_DODGING_HORIZ_FORCE_FROZEN 	STAT(DODGING_HORIZ_FORCE_FROZEN, this)
#define PHYS_DODGING_RAMP_TIME 				STAT(DODGING_RAMP_TIME, this)
#define PHYS_DODGING_UP_SPEED 				STAT(DODGING_UP_SPEED, this)
#define PHYS_DODGING_WALL 					STAT(DODGING_WALL, this)
#define PHYS_DODGING_AIR 					STAT(DODGING_AIR, this)
#define PHYS_DODGING_MAXSPEED 				STAT(DODGING_MAXSPEED, this)
#define PHYS_DODGING_AIR_MAXSPEED 			STAT(DODGING_AIR_MAXSPEED, this)
#define PHYS_DODGING_CLIENTSELECT 			STAT(DODGING_CLIENTSELECT, this)
#endif

#ifdef CSQC
	bool autocvar_cl_dodging;
	#define PHYS_DODGING_FRAMETIME				(1 / (frametime <= 0 ? 60 : frametime))
	#define PHYS_DODGING_TIMEOUT(s) 			STAT(DODGING_TIMEOUT)
	#define PHYS_DODGING_PRESSED_KEYS(s)		(s).pressedkeys
	#define PHYS_DODGING_ENABLED(s)				autocvar_cl_dodging
#elif defined(SVQC)
	#define PHYS_DODGING_FRAMETIME				sys_frametime
	#define PHYS_DODGING_TIMEOUT(s) 			CS_CVAR(s).cvar_cl_dodging_timeout
	#define PHYS_DODGING_PRESSED_KEYS(s)		CS(s).pressedkeys
	#define PHYS_DODGING_ENABLED(s)				CS_CVAR(s).cvar_cl_dodging
#endif

REPLICATE(cvar_cl_dodging_timeout, float, "cl_dodging_timeout");
REPLICATE(cvar_cl_dodging, bool, "cl_dodging");

#ifdef SVQC

bool autocvar_sv_dodging_sound;

#include <common/animdecide.qh>
#include <common/physics/player.qh>

REGISTER_MUTATOR(dodging, cvar("g_dodging"))
{
	                               
	MUTATOR_ONADD
	{
		g_dodging = cvar("g_dodging");
	}

	                                
	MUTATOR_ONROLLBACK_OR_REMOVE
	{
		g_dodging = 0;
	}

	return false;
}

#elif defined(CSQC)
REGISTER_MUTATOR(dodging, true);
#endif

                                                                                               
.float dodging_action;

                                              
.float dodging_single_action;

                                                                         
.float last_FORWARD_KEY_time;
.float last_BACKWARD_KEY_time;
.float last_LEFT_KEY_time;
.float last_RIGHT_KEY_time;

                                                                                
.vector dodging_direction;

                                                                                             
                                                             
.float last_dodging_time;

                                                        
.float dodging_force_total;
                                    
.float dodging_force_remaining;

#ifdef CSQC
.int pressedkeys;
#endif

#define X(dir) \
	tracebox(this.origin, this.mins, this.maxs, this.origin + threshold * dir, true, this); \
	if (trace_fraction < 1 && !(trace_dphitq3surfaceflags & Q3SURFACEFLAG_SKY)) \
		return true;

                                                
bool is_close_to_wall(entity this, float threshold, vector forward, vector right)
{
	X(right);
	X(-right);
	X(forward);
	X(-forward);

	return false;
}

bool is_close_to_ground(entity this, float threshold, vector up)
{
	if (IS_ONGROUND(this)) return true;
	X(-up);                                                                                    

	return false;
}

#undef X

float determine_force(entity player) {
	if (PHYS_FROZEN(player)) return PHYS_DODGING_HORIZ_FORCE_FROZEN;

	float horiz_vel = vlen(vec2(player.velocity));
	return map_bound_ranges(horiz_vel,
	                        PHYS_DODGING_HORIZ_SPEED_MIN, PHYS_DODGING_HORIZ_SPEED_MAX,
	                        PHYS_DODGING_HORIZ_FORCE_SLOWEST, PHYS_DODGING_HORIZ_FORCE_FASTEST);
}

bool PM_dodging_checkpressedkeys(entity this)
{
	bool frozen_dodging = (PHYS_FROZEN(this) && PHYS_DODGING_FROZEN(this));
	bool frozen_no_doubletap = (frozen_dodging && !PHYS_DODGING_FROZEN_DOUBLETAP);

	float tap_direction_x = 0;
	float tap_direction_y = 0;
	bool dodge_detected = false;
	vector mymovement = PHYS_CS(this).movement;

	#define X(COND,BTN,RESULT)																				\
	if (mymovement_##COND) {																				\
		                             																		\
		if(!(PHYS_DODGING_PRESSED_KEYS(this) & KEY_##BTN) || frozen_no_doubletap) {							\
			tap_direction_##RESULT;																			\
			if ((time - this.last_##BTN##_KEY_time) < PHYS_DODGING_TIMEOUT(this) || frozen_no_doubletap) {	\
				dodge_detected = true;																		\
			} else if(PHYS_INPUT_BUTTON_DODGE(this)) {														\
				dodge_detected = true;																		\
			}																								\
			this.last_##BTN##_KEY_time = time;																\
		}																									\
	}
	X(x < 0, BACKWARD,	x--);
	X(x > 0, FORWARD,	x++);
	X(y < 0, LEFT,		y--);
	X(y > 0, RIGHT,		y++);
	#undef X

	if (!dodge_detected) return false;

	                                            
	                                                                               
	                                                                                                             
	                                                                               
	if ((time - this.last_dodging_time) < PHYS_DODGING_DELAY)
		return false;

	vector forward, right, up;
	MAKE_VECTORS(this.angles, forward, right, up);

	bool can_dodge = (is_close_to_ground(this, PHYS_DODGING_HEIGHT_THRESHOLD, up) && (PHYS_DODGING_MAXSPEED == 0 || vdist(this.velocity, <, PHYS_DODGING_MAXSPEED)));
	bool can_wall_dodge = (PHYS_DODGING_WALL && is_close_to_wall(this, PHYS_DODGING_DISTANCE_THRESHOLD, forward, right));
	bool can_air_dodge = (PHYS_DODGING_AIR && (PHYS_DODGING_AIR_MAXSPEED == 0 || vdist(this.velocity, <, PHYS_DODGING_AIR_MAXSPEED)));
	if (!can_dodge && !can_wall_dodge && !can_air_dodge) return false;

	this.last_dodging_time = time;

	this.dodging_action = 1;
	this.dodging_single_action = 1;

	this.dodging_force_total = determine_force(this);
	this.dodging_force_remaining = this.dodging_force_total;

	this.dodging_direction.x = tap_direction_x;
	this.dodging_direction.y = tap_direction_y;

	                                                            
	float length = sqrt(this.dodging_direction.x ** 2 + this.dodging_direction.y ** 2);

	this.dodging_direction.x = this.dodging_direction.x / length;
	this.dodging_direction.y = this.dodging_direction.y / length;

	return true;
}

void PM_dodging(entity this)
{
	                                                                                                      
	if (!this.dodging_action) return;

	                                              
	bool frozen_dodging = (PHYS_FROZEN(this) && PHYS_DODGING_FROZEN(this));
	if (this.waterlevel >= WATERLEVEL_SWIMMING || IS_DEAD(this) || (PHYS_DODGING_CLIENTSELECT && !PHYS_DODGING_ENABLED(this) && !frozen_dodging))
	{
		this.dodging_action = 0;
		this.dodging_direction.x = 0;
		this.dodging_direction.y = 0;
		return;
	}

	vector forward, right, up;
	if(PHYS_DODGING_AIR)
		MAKE_VECTORS(this.v_angle, forward, right, up);
	else
		MAKE_VECTORS(this.angles, forward, right, up);

	                                            
	                                                                               
	                                                                     
	                                                                        
	float common_factor = PHYS_DODGING_FRAMETIME / PHYS_DODGING_RAMP_TIME;
	                                                                                                                  
	                                                                                                      

	float velocity_increase = min(common_factor * this.dodging_force_total, this.dodging_force_remaining);
	this.dodging_force_remaining -= velocity_increase;
	this.velocity += this.dodging_direction.x * velocity_increase * forward
	               + this.dodging_direction.y * velocity_increase * right;

	                                                   
	if (this.dodging_single_action == 1)
	{
		UNSET_ONGROUND(this);

		this.velocity += PHYS_DODGING_UP_SPEED * up;

#ifdef SVQC
		if (autocvar_sv_dodging_sound)
			PlayerSound(this, playersound_jump, CH_PLAYER, VOL_BASE, VOICETYPE_PLAYERSOUND);

		animdecide_setaction(this, ANIMACTION_JUMP, true);
#endif

		this.dodging_single_action = 0;
	}

	if(this.dodging_force_remaining <= 0)
	{
		                                                  
		this.dodging_action = 0;
		this.dodging_direction.x = 0;
		this.dodging_direction.y = 0;
	}
}

#ifdef CSQC
void PM_dodging_GetPressedKeys(entity this)
{
	PM_dodging_checkpressedkeys(this);

	                                                                      
	int keys = this.pressedkeys;
	keys = BITSET(keys, KEY_FORWARD, 	PHYS_CS(this).movement.x > 0);
	keys = BITSET(keys, KEY_BACKWARD, 	PHYS_CS(this).movement.x < 0);
	keys = BITSET(keys, KEY_RIGHT, 		PHYS_CS(this).movement.y > 0);
	keys = BITSET(keys, KEY_LEFT, 		PHYS_CS(this).movement.y < 0);

	keys = BITSET(keys, KEY_JUMP, 		PHYS_INPUT_BUTTON_JUMP(this));
	keys = BITSET(keys, KEY_CROUCH, 	IS_DUCKED(this));                                                                                                 
	keys = BITSET(keys, KEY_ATCK, 		PHYS_INPUT_BUTTON_ATCK(this));
	keys = BITSET(keys, KEY_ATCK2, 		PHYS_INPUT_BUTTON_ATCK2(this));
	this.pressedkeys = keys;
}
#endif

MUTATOR_HOOKFUNCTION(dodging, PlayerPhysics)
{
	entity player = M_ARGV(0, entity);

#ifdef CSQC
	PM_dodging_GetPressedKeys(player);
#endif
	PM_dodging(player);
}

#ifdef SVQC

void dodging_ResetPlayer(entity this)
{
	this.last_dodging_time = 0;

	this.dodging_action = 0;
	this.dodging_single_action = 0;

	this.dodging_force_total = 0;
	this.dodging_force_remaining = 0;

	this.dodging_direction = '0 0 0';
}

MUTATOR_HOOKFUNCTION(dodging, PlayerSpawn)
{
	entity player = M_ARGV(0, entity);
	dodging_ResetPlayer(player);
}

MUTATOR_HOOKFUNCTION(dodging, MakePlayerObserver)
{
	entity player = M_ARGV(0, entity);
	dodging_ResetPlayer(player);
}

MUTATOR_HOOKFUNCTION(dodging, GetPressedKeys)
{
	entity player = M_ARGV(0, entity);

	PM_dodging_checkpressedkeys(player);
}

#endif
