#include "announcer.qh"

#include <client/draw.qh>
#include <client/hud/panel/centerprint.qh>
#include <client/hud/panel/scoreboard.qh>
#include <client/mutators/_mod.qh>
#include <common/notifications/all.qh>
#include <common/stats.qh>
#include <common/mapinfo.qh>
#include <common/ent_cs.qh>

bool announcer_1min;
bool announcer_5min;
string AnnouncerOption()
{
	string ret = autocvar_cl_announcer;
	MUTATOR_CALLHOOK(AnnouncerOption, ret);
	ret = M_ARGV(0, string);
	return ret;
}

entity announcer_countdown;

   
                                                                       
   
string prev_pl1_name;
string prev_pl2_name;
void Announcer_Duel()
{
	Scoreboard_UpdatePlayerTeams();

	entity pl1 = players.sort_next;
	entity pl2 = pl1.sort_next;
	string pl1_name = (pl1 && pl1.team != NUM_SPECTATOR ? entcs_GetName(pl1.sv_entnum) : "???");
	string pl2_name = (pl2 && pl2.team != NUM_SPECTATOR ? entcs_GetName(pl2.sv_entnum) : "???");

	if(pl1_name == prev_pl1_name && pl2_name == prev_pl2_name)
		return;                                      

	strcpy(prev_pl1_name, pl1_name);
	strcpy(prev_pl2_name, pl2_name);

	                                      
	centerprint_SetDuelTitle(pl1_name, pl2_name);
}

void Announcer_ClearTitle()
{
	strfree(prev_pl1_name);
	strfree(prev_pl2_name);
	centerprint_ClearTitle();
}

bool prev_inround;
float prev_starttime;
float prev_roundstarttime;
void Announcer_Countdown(entity this)
{
	float starttime = STAT(GAMESTARTTIME);
	float roundstarttime = STAT(ROUNDSTARTTIME);
	if(roundstarttime == -1)
	{
		Local_Notification(MSG_CENTER, CENTER_COUNTDOWN_ROUNDSTOP);
		delete(this);
		announcer_countdown = NULL;
		Announcer_ClearTitle();
		return;
	}

	bool inround = (roundstarttime && time >= starttime);
	float countdown = (inround ? roundstarttime - time : starttime - time);
	float countdown_rounded = floor(0.5 + countdown);

	if (starttime != prev_starttime || roundstarttime != prev_roundstarttime || prev_inround != inround)
		this.skin = 0;                                 

	if(countdown <= 0)                                            
	{
		Local_Notification(MSG_CENTER, CENTER_COUNTDOWN_BEGIN);
		Local_Notification(MSG_MULTI, COUNTDOWN_BEGIN);
		delete(this);
		announcer_countdown = NULL;
		Announcer_ClearTitle();
		return;
	}
	else                            
	{
		if(inround)
		{
			if(!prev_inround) Announcer_ClearTitle();                                            
			if (!this.skin)             
				Local_Notification(MSG_CENTER, CENTER_COUNTDOWN_ROUNDSTART, STAT(ROUNDS_PLAYED) + 1, countdown_rounded);
			Notification annce_num = Announcer_PickNumber(CNT_ROUNDSTART, countdown_rounded);
			if(annce_num != NULL)
				Local_Notification(MSG_ANNCE, annce_num);
			this.nextthink = (roundstarttime - (countdown - 1));
		}
		else
		{
			if (!this.skin)             
				Local_Notification(MSG_CENTER, CENTER_COUNTDOWN_GAMESTART, countdown_rounded);
			Notification annce_num = Announcer_PickNumber(CNT_GAMESTART, countdown_rounded);
			if(!roundstarttime && annce_num != NULL)                                                  
				Local_Notification(MSG_ANNCE, annce_num);
			this.nextthink = (starttime - (countdown - 1));
		}
		                                                                                          
		                                                                                                        
		                                                                                        
		this.skin = 1;                  
	}

	prev_inround = inround;
	prev_starttime = starttime;
	prev_roundstarttime = roundstarttime;
}

   
                                                                                  
  
                                                                                  
                                                                                          
                                      
   
float previous_game_starttime;
void Announcer_Gamestart()
{
	float startTime = STAT(GAMESTARTTIME);
	float roundstarttime = STAT(ROUNDSTARTTIME);
	if(time > startTime && roundstarttime > startTime)
		startTime = roundstarttime;
	if(intermission || warmup_stage)
	{
		if(announcer_countdown)
		{
			Announcer_ClearTitle();
			centerprint_Kill(ORDINAL(CPID_ROUND));
			delete(announcer_countdown);
			announcer_countdown = NULL;
		}
		return;
	}

	if(announcer_countdown && gametype.m_1v1)
		Announcer_Duel();

	if(previous_game_starttime != startTime)
	{
		if(time < startTime)
		{
			if (!announcer_countdown)
			{
				announcer_countdown = new_pure(announcer_countdown);
				setthink(announcer_countdown, Announcer_Countdown);
			}

			if(!warmup_stage && time < STAT(GAMESTARTTIME))
			{
				if (gametype.m_1v1)
					Announcer_Duel();
				else
					centerprint_SetTitle(strcat("^BG", MapInfo_Type_ToText(gametype)));                           

				if(time + 5.0 < startTime)                                                                                       
					Local_Notification(MSG_ANNCE, ANNCE_PREPARE);
			}

			announcer_countdown.nextthink = startTime - floor(startTime - time + 0.5);                                     
		}
	}

	previous_game_starttime = startTime;
}

#define ANNOUNCER_CHECKMINUTE(minute) MACRO_BEGIN \
	if(announcer_##minute##min) { \
		if(timeleft > minute * 60) \
			announcer_##minute##min = false; \
	} else { \
		if(timeleft < minute * 60 && timeleft > minute * 60 - 1) { \
			announcer_##minute##min = true; \
			Local_Notification(MSG_ANNCE, ANNCE_REMAINING_MIN_##minute); \
		} \
	} \
MACRO_END

void Announcer_Time()
{
	static bool warmup_stage_prev;

	if(intermission)
		return;

	if (warmup_stage != warmup_stage_prev)
	{
		announcer_5min = announcer_1min = false;
		warmup_stage_prev = warmup_stage;
		return;
	}

	float starttime = STAT(GAMESTARTTIME);
	if(time < starttime)
	{
		announcer_5min = announcer_1min = false;
		return;
	}

	float timeleft;
	if(warmup_stage)
	{
		float warmup_timelimit = STAT(WARMUP_TIMELIMIT);
		if(warmup_timelimit > 0)
			timeleft = max(0, warmup_timelimit + starttime - time);
		else
			timeleft = 0;
	}
	else
		timeleft = max(0, STAT(TIMELIMIT) * 60 + starttime - time);

	if(autocvar_cl_announcer_maptime >= 2)
		ANNOUNCER_CHECKMINUTE(5);

	if((autocvar_cl_announcer_maptime == 1) || (autocvar_cl_announcer_maptime == 3))
		ANNOUNCER_CHECKMINUTE(1);
}

void Announcer()
{
	                                                         
	if(!gametype)
		return;
	Announcer_Gamestart();
	Announcer_Time();
}
