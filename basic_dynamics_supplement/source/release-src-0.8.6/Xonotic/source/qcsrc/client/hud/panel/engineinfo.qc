#include "engineinfo.qh"

#include <client/draw.qh>

                    

void HUD_EngineInfo_Export(int fh)
{
	                                                                             
}

float prevfps;
float prevfps_time;
int framecounter;

float frametimeavg;
float frametimeavg1;               
float frametimeavg2;                
float autocvar_hud_panel_engineinfo_framecounter_exponentialmovingaverage;
float autocvar_hud_panel_engineinfo_framecounter_exponentialmovingaverage_new_weight;
float autocvar_hud_panel_engineinfo_framecounter_exponentialmovingaverage_instantupdate_change_threshold;
void HUD_EngineInfo()
{
	if(!autocvar__hud_configure)
	{
		if(!autocvar_hud_panel_engineinfo) return;
	}

	HUD_Panel_LoadCvars();
	vector pos, mySize;
	pos = panel_pos;
	mySize = panel_size;

	if (autocvar_hud_panel_engineinfo_dynamichud)
		HUD_Scale_Enable();
	else
		HUD_Scale_Disable();
	HUD_Panel_DrawBg();
	if(panel_bg_padding)
	{
		pos += '1 1 0' * panel_bg_padding;
		mySize -= '2 2 0' * panel_bg_padding;
	}

	float currentTime = gettime(GETTIME_FRAMESTART);
	if(autocvar_hud_panel_engineinfo_framecounter_exponentialmovingaverage)
	{
		float currentframetime = currentTime - prevfps_time;
		frametimeavg = (frametimeavg + frametimeavg1 + frametimeavg2 + currentframetime)/4;                                                                                       
		frametimeavg2 = frametimeavg1;
		frametimeavg1 = frametimeavg;

		float weight;
		weight = autocvar_hud_panel_engineinfo_framecounter_exponentialmovingaverage_new_weight;
		if(currentframetime > 0.0001)                                                                                                                                                                     
		{
			if(fabs(prevfps - (1/frametimeavg)) > prevfps * autocvar_hud_panel_engineinfo_framecounter_exponentialmovingaverage_instantupdate_change_threshold)                                                                                                                  
				prevfps = (1/currentframetime);
			prevfps = (1 - weight) * prevfps + weight * (1/frametimeavg);                                                                                                    
		}
		prevfps_time = currentTime;
	}
	else
	{
		framecounter += 1;
		if(currentTime - prevfps_time > autocvar_hud_panel_engineinfo_framecounter_time)
		{
			prevfps = framecounter/(currentTime - prevfps_time);
			framecounter = 0;
			prevfps_time = currentTime;
		}
	}

	vector color = HUD_Get_Num_Color(prevfps, 100, true);
	drawstring_aspect(pos, sprintf(_("FPS: %.*f"), autocvar_hud_panel_engineinfo_framecounter_decimals, prevfps), mySize, color, panel_fg_alpha, DRAWFLAG_NORMAL);
}
