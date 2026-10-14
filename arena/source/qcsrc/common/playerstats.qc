#include "playerstats.qh"

#if defined(CSQC)
#elif defined(MENUQC)
#elif defined(SVQC)
	#include <common/constants.qh>
	#include <common/stats.qh>
	#include <common/util.qh>
	#include <common/weapons/_all.qh>
	#include <server/anticheat.qh>
	#include <server/client.qh>
	#include <server/intermission.qh>
	#include <server/scores.qh>
	#include <server/weapons/accuracy.qh>
	#include <server/world.qh>
#endif


#ifdef GAMEQC
REPLICATE(cvar_cl_allow_uid2name, int, "cl_allow_uid2name");
REPLICATE(cvar_cl_allow_uidranking, bool, "cl_allow_uidranking");
REPLICATE(cvar_cl_allow_uidtracking, int, "cl_allow_uidtracking");
#endif

#ifdef SVQC
REPLICATE_APPLYCHANGE("cl_allow_uidtracking", { PlayerStats_GameReport_AddPlayer(this); });
#endif

#ifdef SVQC
void PlayerStats_Prematch()
{
	        
}

                                                                             
void PlayerStats_GameReport_Reset_All()
{
	strfree(PS_GR_OUT_TL);
	strfree(PS_GR_OUT_PL);
	strfree(PS_GR_OUT_EVL);

	if (PS_GR_OUT_DB >= 0)
	{
		db_close(PS_GR_OUT_DB);
		PlayerStats_GameReport_Init();
	}
	if(PS_GR_OUT_DB < 0)
		return;

	for (int i = 0; i < 16; i++)
		if (teamscorekeepers[i])
			PlayerStats_GameReport_AddTeam(i + 1);
	FOREACH_CLIENT(true, {
		                                                                            
		                                                      
		strfree(it.playerstats_id);
		PlayerStats_GameReport_AddEvent(sprintf("kills-%d", it.playerid));
		PlayerStats_GameReport_AddPlayer(it);
	});
	FOREACH(Scores, true, {
		string label = scores_label(it);
		if (label == "")
			continue;
		PlayerStats_GameReport_AddEvent(strcat(PLAYERSTATS_TOTAL, label));
		PlayerStats_GameReport_AddEvent(strcat(PLAYERSTATS_SCOREBOARD, label));
	});
	for(int i = 0; i < MAX_TEAMSCORE; ++i)
	{
		string label = teamscores_label(i);
		if (label == "")
			continue;
		PlayerStats_GameReport_AddEvent(strcat(PLAYERSTATS_TOTAL, label));
		PlayerStats_GameReport_AddEvent(strcat(PLAYERSTATS_SCOREBOARD, label));
	}
}

void PlayerStats_GameReport_AddPlayer(entity e)
{
	if((PS_GR_OUT_DB < 0) || (e.playerstats_id)) { return; }

	                               
	string s = "";

	if((e.crypto_idfp != "") && (CS_CVAR(e).cvar_cl_allow_uidtracking == 1))
		{ s = e.crypto_idfp; }
	else if(IS_BOT_CLIENT(e))
		{ s = sprintf("bot#%g#%s", skill, e.cleanname); }

	if((s == "") || find(NULL, playerstats_id, s))                                                                
	{
		if(IS_BOT_CLIENT(e))
			{ s = sprintf("bot#%d", e.playerid); }
		else
			{ s = sprintf("player#%d", e.playerid); }
	}

	e.playerstats_id = strzone(s);

	                                     
	string key = sprintf("%s:*", e.playerstats_id);
	string p = db_get(PS_GR_OUT_DB, key);

	if(p == "")
	{
		if(PS_GR_OUT_PL)
		{
			db_put(PS_GR_OUT_DB, key, PS_GR_OUT_PL);
			strunzone(PS_GR_OUT_PL);
		}
		else { db_put(PS_GR_OUT_DB, key, "#"); }
		PS_GR_OUT_PL = strzone(e.playerstats_id);
	}
}

void PlayerStats_GameReport_AddTeam(int t)
{
	if(PS_GR_OUT_DB < 0) { return; }

	string key = sprintf("%d", t);
	string p = db_get(PS_GR_OUT_DB, key);

	if(p == "")
	{
		if(PS_GR_OUT_TL)
		{
			db_put(PS_GR_OUT_DB, key, PS_GR_OUT_TL);
			strunzone(PS_GR_OUT_TL);
		}
		else { db_put(PS_GR_OUT_DB, key, "#"); }
		PS_GR_OUT_TL = strzone(key);
	}
}

void PlayerStats_GameReport_AddEvent(string event_id)
{
	if(PS_GR_OUT_DB < 0) { return; }

	string key = sprintf("*:%s", event_id);
	string p = db_get(PS_GR_OUT_DB, key);

	if(p == "")
	{
		if(PS_GR_OUT_EVL)
		{
			db_put(PS_GR_OUT_DB, key, PS_GR_OUT_EVL);
			strunzone(PS_GR_OUT_EVL);
		}
		else { db_put(PS_GR_OUT_DB, key, "#"); }
		PS_GR_OUT_EVL = strzone(event_id);
	}
}

float PlayerStats_GameReport_Event(string prefix, string event_id, float value)
{
	if((prefix == "") || PS_GR_OUT_DB < 0) { return 0; }

	string key = sprintf("%s:%s", prefix, event_id);
	float val = stof(db_get(PS_GR_OUT_DB, key));
	val += value;
	db_put(PS_GR_OUT_DB, key, ftos(val));
	return val;
}

void PlayerStats_GameReport_Accuracy(entity p)
{
	#define ACCMAC(suffix, field) \
		PlayerStats_GameReport_Event_Player(p, \
			sprintf("acc-%s-%s", it.netname, suffix), CS(p).accuracy.(field[i-1]));
	FOREACH(Weapons, it != WEP_Null, {
		ACCMAC("hit", accuracy_hit)
		ACCMAC("fired", accuracy_fired)
		ACCMAC("cnt-hit", accuracy_cnt_hit)
		ACCMAC("cnt-fired", accuracy_cnt_fired)
		ACCMAC("frags", accuracy_frags)
	});
	#undef ACCMAC
}

void PlayerStats_GameReport_FinalizePlayer(entity p)
{
	if((p.playerstats_id == "") || PS_GR_OUT_DB < 0) { return; }

	                   
	if(p.alivetime)
	{
		PlayerStats_GameReport_Event_Player(p, PLAYERSTATS_ALIVETIME, time - p.alivetime);
		p.alivetime = 0;
	}

	db_put(PS_GR_OUT_DB, sprintf("%s:_playerid", p.playerstats_id), ftos(p.playerid));

	if(CS_CVAR(p).cvar_cl_allow_uid2name == 1 || IS_BOT_CLIENT(p))
		db_put(PS_GR_OUT_DB, sprintf("%s:_netname", p.playerstats_id), playername(p.netname, p.team, false));

	if(teamplay)
		db_put(PS_GR_OUT_DB, sprintf("%s:_team", p.playerstats_id), ftos(p.team));

	if(stof(db_get(PS_GR_OUT_DB, sprintf("%s:%s", p.playerstats_id, PLAYERSTATS_ALIVETIME))) > 0)
		PlayerStats_GameReport_Event_Player(p, PLAYERSTATS_JOINS, 1);

	PlayerStats_GameReport_Accuracy(p);
	anticheat_report_to_playerstats(p);

	if(IS_REAL_CLIENT(p))
	{
		if(CS(p).latency_cnt)
		{
			float latency = max(0, CS(p).latency_sum / CS(p).latency_cnt);
			if(latency)
			{
				                                                                           
				                                                           
				float prev_latency = PlayerStats_GameReport_Event_Player(p, PLAYERSTATS_AVGLATENCY, 0);
				float new_latency = !prev_latency ? latency : (prev_latency + latency) / 2;
				PlayerStats_GameReport_Event_Player(p, PLAYERSTATS_AVGLATENCY, -prev_latency + new_latency);
			}
		}

		db_put(PS_GR_OUT_DB, sprintf("%s:_ranked", p.playerstats_id), ftos(CS_CVAR(p).cvar_cl_allow_uidranking));
	}

	strfree(p.playerstats_id);
}

void PlayerStats_GameReport(bool finished)
{
	if(PS_GR_OUT_DB < 0) { return; }

	PlayerScore_Sort(score_dummyfield, 0, false, false);
	PlayerScore_Sort(scoreboard_pos, 1, true, true);
	if(teamplay) { PlayerScore_TeamStats(); }

	FOREACH_CLIENT(true, {
		                          
		PlayerStats_GameReport_Event_Player(it, PLAYERSTATS_RANK, it.score_dummyfield);

		                  
		if(it.scoreboard_pos)
		{
			                       
			PlayerStats_GameReport_Event_Player(it, PLAYERSTATS_SCOREBOARD_VALID, 1);

			                          
			PlayerStats_GameReport_Event_Player(it, PLAYERSTATS_SCOREBOARD_POS, it.scoreboard_pos);

			                      
			PlayerScore_PlayerStats(it);

			                                                
			if(finished)
			{
				PlayerStats_GameReport_Event_Player(it, PLAYERSTATS_WINS, it.winning);
				PlayerStats_GameReport_Event_Player(it, PLAYERSTATS_MATCHES, 1);
			}
		}

		                                   
		PlayerStats_GameReport_FinalizePlayer(it);
	});

	if(autocvar_g_playerstats_gamereport_uri != "")
	{
		PlayerStats_GameReport_DelayMapVote = true;
		url_multi_fopen(
			autocvar_g_playerstats_gamereport_uri,
			FILE_APPEND,
			PlayerStats_GameReport_Handler,
			NULL
		);
	}
	else
	{
		PlayerStats_GameReport_DelayMapVote = false;
		db_close(PS_GR_OUT_DB);
		PS_GR_OUT_DB = -1;
	}
}

void PlayerStats_GameReport_Init()                                                                       
{
	serverflags &= ~SERVERFLAG_PLAYERSTATS;
	serverflags &= ~SERVERFLAG_PLAYERSTATS_CUSTOM;

	if(autocvar_g_playerstats_gamereport_uri == "") { return; }

	PS_GR_OUT_DB = db_create();

	if(PS_GR_OUT_DB >= 0)
	{
		PlayerStats_GameReport_DelayMapVote = true;

		serverflags |= SERVERFLAG_PLAYERSTATS;
		if(autocvar_g_playerstats_gamereport_uri != cvar_defstring("g_playerstats_gamereport_uri"))
		{
			serverflags |= SERVERFLAG_PLAYERSTATS_CUSTOM;
		}

		PlayerStats_GameReport_AddEvent(PLAYERSTATS_ALIVETIME);
		PlayerStats_GameReport_AddEvent(PLAYERSTATS_AVGLATENCY);
		PlayerStats_GameReport_AddEvent(PLAYERSTATS_WINS);
		PlayerStats_GameReport_AddEvent(PLAYERSTATS_MATCHES);
		PlayerStats_GameReport_AddEvent(PLAYERSTATS_JOINS);
		PlayerStats_GameReport_AddEvent(PLAYERSTATS_SCOREBOARD_VALID);
		PlayerStats_GameReport_AddEvent(PLAYERSTATS_SCOREBOARD_POS);
		PlayerStats_GameReport_AddEvent(PLAYERSTATS_RANK);

		                 
		FOREACH(Weapons, it != WEP_Null, {
			PlayerStats_GameReport_AddEvent(strcat("acc-", it.netname, "-hit"));
			PlayerStats_GameReport_AddEvent(strcat("acc-", it.netname, "-fired"));
			PlayerStats_GameReport_AddEvent(strcat("acc-", it.netname, "-cnt-hit"));
			PlayerStats_GameReport_AddEvent(strcat("acc-", it.netname, "-cnt-fired"));
			PlayerStats_GameReport_AddEvent(strcat("acc-", it.netname, "-frags"));
		});

		PlayerStats_GameReport_AddEvent(PLAYERSTATS_ACHIEVEMENT_KILL_SPREE_3);
		PlayerStats_GameReport_AddEvent(PLAYERSTATS_ACHIEVEMENT_KILL_SPREE_5);
		PlayerStats_GameReport_AddEvent(PLAYERSTATS_ACHIEVEMENT_KILL_SPREE_10);
		PlayerStats_GameReport_AddEvent(PLAYERSTATS_ACHIEVEMENT_KILL_SPREE_15);
		PlayerStats_GameReport_AddEvent(PLAYERSTATS_ACHIEVEMENT_KILL_SPREE_20);
		PlayerStats_GameReport_AddEvent(PLAYERSTATS_ACHIEVEMENT_KILL_SPREE_25);
		PlayerStats_GameReport_AddEvent(PLAYERSTATS_ACHIEVEMENT_KILL_SPREE_30);
		PlayerStats_GameReport_AddEvent(PLAYERSTATS_ACHIEVEMENT_BOTLIKE);
		PlayerStats_GameReport_AddEvent(PLAYERSTATS_ACHIEVEMENT_FIRSTBLOOD);
		PlayerStats_GameReport_AddEvent(PLAYERSTATS_ACHIEVEMENT_FIRSTVICTIM);

		anticheat_register_to_playerstats();
	}
	else { PlayerStats_GameReport_DelayMapVote = false; }
}

                                                                         
                                                                                  
string PlayerStats_GetGametype()
{
	if(IS_GAMETYPE(DEATHMATCH) && autocvar_g_maxplayers == 2)
	{
		                                     
		int plcount = 0;
		FOREACH_CLIENT(IS_PLAYER(it), ++plcount);
		if(plcount <= 2)
			return "duel";
	}
	return GetGametype();
}

void PlayerStats_GameReport_Handler(entity fh, entity pass, float status)
{
	string t, tn;
	string p, pn;
	string e, en;
	string nn, tt;
	string s;

	switch(status)
	{
		                                         
		                                         
		                                         
		                  
                                                                             
                                               
                                         
                 
                                                    
                
                                            
                                
                                       
                                     
                             
                                                        
                                                                                                                        
                                                                                                                             
                    
                                         
               
                                         
                                                                     
                         
                                                  
                                                                          
                                                                    
                                                                               
                                                                                             
                                                                                
                                                                  
                                                                                                            
                                                                                                         
                                                                
                                    
                                                   
                                                                                             
                                                                      
                                                            
                                                                  
     
		case URL_READY_CANWRITE:
		{
			url_fputs(fh, "V 9\n");
			#ifdef WATERMARK
			url_fputs(fh, sprintf("R %s\n", WATERMARK));
			#endif
			url_fputs(fh, sprintf("G %s\n", PlayerStats_GetGametype()));
			url_fputs(fh, sprintf("O %s\n", modname));
			url_fputs(fh, sprintf("M %s\n", GetMapname()));
			url_fputs(fh, sprintf("I %s\n", matchid));
			url_fputs(fh, sprintf("S %s\n", cvar_string("hostname")));
			url_fputs(fh, sprintf("C %d\n", cvar_purechanges_count));
			url_fputs(fh, sprintf("U %d\n", cvar("port")));
			url_fputs(fh, sprintf("D %f\n", max(0, time - game_starttime)));
			url_fputs(fh, sprintf("L %s\n", autocvar_g_playerstats_gamereport_ladder));

			        
			if(teamplay)
			{
				for(t = PS_GR_OUT_TL; (tn = db_get(PS_GR_OUT_DB, sprintf("%d", stof(t)))) != ""; t = tn)
				{
					                     
					url_fputs(fh, sprintf("Q team#%s\n", t));

					                                                                                                                             
					for(e = PS_GR_OUT_EVL; (en = db_get(PS_GR_OUT_DB, sprintf("*:%s", e))) != ""; e = en)
					{
						float v = stof(db_get(PS_GR_OUT_DB, sprintf("team#%d:%s", stof(t), e)));
						if(v != 0) { url_fputs(fh, sprintf("e %s %g\n", e, v)); }
					}
				}
			}

			          
			for(p = PS_GR_OUT_PL; (pn = db_get(PS_GR_OUT_DB, sprintf("%s:*", p))) != ""; p = pn)
			{
				                       
				url_fputs(fh, sprintf("P %s\n", p));

				                                                 
				nn = db_get(PS_GR_OUT_DB, sprintf("%s:_playerid", p));
				if(nn != "") { url_fputs(fh, sprintf("i %s\n", nn)); }

				              
				nn = db_get(PS_GR_OUT_DB, sprintf("%s:_netname", p));
				if(nn != "") { url_fputs(fh, sprintf("n %s\n", nn)); }

				                             
				if(teamplay)
				{
					tt = db_get(PS_GR_OUT_DB, sprintf("%s:_team", p));
					url_fputs(fh, sprintf("t %s\n", tt));
				}

				                      
				nn = db_get(PS_GR_OUT_DB, sprintf("%s:_ranked", p));
				if(nn != "") { url_fputs(fh, sprintf("r %s\n", nn)); }

				                       
				for(e = PS_GR_OUT_EVL; (en = db_get(PS_GR_OUT_DB, sprintf("*:%s", e))) != ""; e = en)
				{
					float v = stof(db_get(PS_GR_OUT_DB, sprintf("%s:%s", p, e)));
					if(v != 0) { url_fputs(fh, sprintf("e %s %g\n", e, v)); }
				}
			}
			url_fputs(fh, "\n");
			url_fclose(fh);
			break;
		}

		                                         
		                                         
		                                         
		                  
          
     
		case URL_READY_CANREAD:
		{
			                                                                   
			                           
			LOG_DEBUG("Got response from player stats server:");
			while((s = url_fgets(fh))) { LOG_DEBUG("  ", s); }
			LOG_DEBUG("End of response.");
			url_fclose(fh);
			break;
		}

		case URL_READY_CLOSED:
		{
			                          
			LOG_DEBUG("Player stats written");
			PlayerStats_GameReport_DelayMapVote = false;
			if(PS_GR_OUT_DB >= 0)
			{
				db_close(PS_GR_OUT_DB);
				PS_GR_OUT_DB = -1;
			}
			break;
		}

		case URL_READY_ERROR:
		default:
		{
			LOG_INFO("Player stats writing failed: ", ftos(status));
			PlayerStats_GameReport_DelayMapVote = false;
			if(PS_GR_OUT_DB >= 0)
			{
				db_close(PS_GR_OUT_DB);
				PS_GR_OUT_DB = -1;
			}
			break;
		}
	}
}

void PlayerStats_PlayerBasic(entity joiningplayer, float newrequest)
{
	GameRules_scoring_add(joiningplayer, ELO, -1);
	                                                                                       
	if(autocvar_g_playerstats_playerbasic_uri != "")
	{
		string uri = autocvar_g_playerstats_playerbasic_uri;
		if (joiningplayer.crypto_idfp == "") {
			GameRules_scoring_add(joiningplayer, ELO, -1);
		} else {
			                                                  
			if(PS_B_IN_DB < 0)
				PS_B_IN_DB = db_create();

			                              
			uri = strcat(uri, "/player/", uri_escape(uri_escape(uri_escape(joiningplayer.crypto_idfp))), "/elo.txt");
			LOG_DEBUG("Retrieving playerstats from URL: ", uri);
			url_single_fopen(
				uri,
				FILE_APPEND,
				PlayerStats_PlayerBasic_Handler,
				joiningplayer
			);

			                                                                                                    
			if(newrequest)
			{
				                                                                                   
				joiningplayer.playerstats_basicstatus = PS_B_STATUS_WAITING;
			}
			else
			{
				                                                                             
				joiningplayer.playerstats_basicstatus = PS_B_STATUS_UPDATING;
			}
		}
	}
	else
	{
		                                                               
		GameRules_scoring_add(joiningplayer, ELO, -1);
		if(PS_B_IN_DB >= 0)
		{
			db_close(PS_B_IN_DB);
			PS_B_IN_DB = -1;

			FOREACH_CLIENT(IS_REAL_CLIENT(it), it.playerstats_basicstatus = PS_B_STATUS_IDLE);
		}
	}
}

SHUTDOWN(PlayerStats_PlayerBasic_Shutdown)
{
	if(PS_B_IN_DB >= 0)
	{
		db_close(PS_B_IN_DB);
		PS_B_IN_DB = -1;
	}

	if(PS_GR_OUT_DB >= 0)
	{
		db_close(PS_GR_OUT_DB);
		PS_GR_OUT_DB = -1;
	}
}

void PlayerStats_PlayerBasic_CheckUpdate(entity joiningplayer)
{
	                                                                     

	LOG_DEBUGF("PlayerStats_PlayerBasic_CheckUpdate('%s'): %f",
		joiningplayer.netname,
		time
	);

	                                                                                
	                                                                                                            
	                                                               
	if(!joiningplayer.playerstats_basicstatus)
	{
		PlayerStats_PlayerBasic(
			joiningplayer,
			(joiningplayer.playerstats_basicstatus == PS_B_STATUS_RECEIVED)
		);
	}
}

void PlayerStats_PlayerBasic_Handler(entity fh, entity p, float status)
{
	switch(status)
	{
		case URL_READY_CANWRITE:
		{
			LOG_DEBUG("-- Sending data to player stats server");
			                         
                   
                                               
         
                                                                                    
                                                                                  
                                                                     
                                                                                                                    
     url_fputs(fh, "\n");
			url_fclose(fh);
			return;
		}

		case URL_READY_CANREAD:
		{
			bool handled = false;
			string gt = string_null;
			for (string s = ""; (s = url_fgets(fh)); ) {
				int n = tokenizebyseparator(s, " ");                   
				if (n == 1) continue;
				string key = "", value = "", data = "";
				if (n == 2) {
                    key = argv(0);
                    data = argv(1);
				} else if (n >= 3) {
                    key = argv(0);
                    value = argv(1);
                    data = argv(2);
				}
                switch (key) {
                    case "V":
                                                                   
                        break;
                    case "R":
                                                                   
                        break;
                    case "T":
                                                                
                        break;
                    case "S":
                                                                    
                        break;
                    case "P":
                                                                   
                        break;
                    case "n":
                                                                      
                        break;
                    case "i":
                                                                    
                                                     
                        break;
                    case "G":
                        gt = data;
                        break;
                    case "e":
                                               
                                                 
                        if (gt == PlayerStats_GetGametype()) {
                            handled = true;
                            float e = stof(data);
                            GameRules_scoring_add(p, ELO, +1 + e);
                        }
                        if (gt == "") {
                                                                  
                        } else {
                                                                                        
                        }
                        break;
                }
			}
			url_fclose(fh);
			if (handled) return;
			break;
		}
		case URL_READY_CLOSED:
		{
			                          
			LOG_INFO("Player stats synchronized with server");
			return;
		}

		case URL_READY_ERROR:
		default:
		{
			LOG_INFO("Receiving player stats failed: ", ftos(status));
			break;
		}
	}
	GameRules_scoring_add(p, ELO, -1);
}
#endif        

#ifdef MENUQC


#if 0                                 
	string e = "", en = "";
	float i = 0;
	for(e = PS_D_IN_EVL; (en = db_get(PS_D_IN_DB, e)) != ""; e = en)
	{
		LOG_INFOF("%d:%s:%s", i, e, db_get(PS_D_IN_DB, sprintf("#%s", e)));
		++i;
	}
#endif

void PlayerStats_PlayerDetail_AddItem(string event, string data)
{
	if(PS_D_IN_DB < 0) { return; }

	                                                               
	string marker = sprintf("%s", event);
	if(db_get(PS_D_IN_DB, marker) == "")
	{
		if(PS_D_IN_EVL)
		{
			db_put(PS_D_IN_DB, marker, PS_D_IN_EVL);
			strunzone(PS_D_IN_EVL);
		}
		else { db_put(PS_D_IN_DB, marker, "#"); }
		PS_D_IN_EVL = strzone(marker);
	}

	                                  
	db_put(PS_D_IN_DB, sprintf("#%s", event), data);
	LOG_DEBUG("Added item ", sprintf("#%s", event), "=", data, " to PS_D_IN_DB");
}

void PlayerStats_PlayerDetail()
{
	                                     
	if((autocvar_g_playerstats_playerdetail_uri != "") && (crypto_getmyidstatus(0) > 0))
	{
		                                                  
		if(PS_D_IN_DB < 0)
			PS_D_IN_DB = db_create();

		                                                                 
		LOG_DEBUG("Retrieving playerstats from URL: ", autocvar_g_playerstats_playerdetail_uri);
		url_single_fopen(
			autocvar_g_playerstats_playerdetail_uri,
			FILE_APPEND,
			PlayerStats_PlayerDetail_Handler,
			NULL
		);

		PlayerStats_PlayerDetail_Status = PS_D_STATUS_WAITING;
	}
	else
	{
		                                                               
		if(PS_D_IN_DB >= 0)
		{
			db_close(PS_D_IN_DB);
			PS_D_IN_DB = -1;
		}

		PlayerStats_PlayerDetail_Status = PS_D_STATUS_IDLE;
	}
}

void PlayerStats_PlayerDetail_CheckUpdate()
{
	                                                                      
	float gamecount = cvar("cl_matchcount");

	#if 0
	LOG_INFOF("PlayerStats_PlayerDetail_CheckUpdate(): %f >= %f, %d > %d",
		time,
		PS_D_NEXTUPDATETIME,
		PS_D_LASTGAMECOUNT,
		gamecount
	);
	#endif

	if(
		(time >= PS_D_NEXTUPDATETIME)
		||
		(gamecount > PS_D_LASTGAMECOUNT)
	)
	{
		PlayerStats_PlayerDetail();
		PS_D_NEXTUPDATETIME = (time + autocvar_g_playerstats_playerdetail_autoupdatetime);
		PS_D_LASTGAMECOUNT = gamecount;
	}
}

void PlayerStats_PlayerDetail_Handler(entity fh, entity unused, float status)
{
	switch(status)
	{
		case URL_READY_CANWRITE:
		{
			LOG_DEBUG("PlayerStats_PlayerDetail_Handler(): Sending data to player stats server...");
			url_fputs(fh, "V 1\n");
			#ifdef WATERMARK
			url_fputs(fh, sprintf("R %s\n", WATERMARK));
			#endif
			url_fputs(fh, sprintf("l %s\n", cvar_string("_menu_prvm_language")));            
			                                                                          
			url_fputs(fh, sprintf("n %s\n", cvar_string("_cl_name")));        
			url_fputs(fh, sprintf("m %s %s\n", cvar_string("_cl_playermodel"), cvar_string("_cl_playerskin")));              
			url_fputs(fh, "\n");
			url_fclose(fh);
			break;
		}

		case URL_READY_CANREAD:
		{
			                                                                                        
			string input = "";
			string gametype = "overall";
			while((input = url_fgets(fh)))
			{
				float count = tokenizebyseparator(input, " ");
				string key = "", event = "", data = "";

				if(argv(0) == "#") { continue; }

				if(count == 2)
				{
					key = argv(0);
					data = substring(input, argv_start_index(1), strlen(input) - argv_start_index(1));
				}
				else if(count >= 3)
				{
					key = argv(0);
					event = argv(1);
					data = substring(input, argv_start_index(2), strlen(input) - argv_start_index(2));
				}
				else { continue; }

				switch(key)
				{
					               
					case "V": PlayerStats_PlayerDetail_AddItem("version", data); break;
					case "R": PlayerStats_PlayerDetail_AddItem("release", data); break;
					case "T": PlayerStats_PlayerDetail_AddItem("time", data); break;

					              
					case "S": PlayerStats_PlayerDetail_AddItem("statsurl", data); break;
					case "P": PlayerStats_PlayerDetail_AddItem("hashkey", data); break;
					case "n": PlayerStats_PlayerDetail_AddItem("playernick", data); break;
					case "i": PlayerStats_PlayerDetail_AddItem("playerid", data); break;

					                   
					case "G": gametype = data; break;
					case "e":
					{
						if(event != "" && data != "")
						{
							PlayerStats_PlayerDetail_AddItem(
								sprintf(
									"%s/%s",
									gametype,
									event
								),
								data
							);
						}
						break;
					}

					default:
					{
						LOG_INFOF(
							"PlayerStats_PlayerDetail_Handler(): ERROR: "
							"Key went unhandled? Is our version outdated?\n"
							"PlayerStats_PlayerDetail_Handler(): "
							"Key '%s', Event '%s', Data '%s'",
							key,
							event,
							data
						);
						break;
					}
				}

				#if 0
				LOG_INFOF(
					"PlayerStats_PlayerDetail_Handler(): "
					"Key '%s', Event '%s', Data '%s'",
					key,
					event,
					data
				);
				#endif
			}
			                                                                  
			url_fclose(fh);
			PlayerStats_PlayerDetail_Status = PS_D_STATUS_RECEIVED;
			statslist.getStats(statslist);
			break;
		}

		case URL_READY_CLOSED:
		{
			                          
			LOG_INFO("PlayerStats_PlayerDetail_Handler(): Player stats synchronized with server.");
			break;
		}

		case URL_READY_ERROR:
		default:
		{
			LOG_INFO("PlayerStats_PlayerDetail_Handler(): Receiving player stats failed: ", ftos(status));
			PlayerStats_PlayerDetail_Status = PS_D_STATUS_ERROR;
			if(PS_D_IN_DB >= 0)
			{
				db_close(PS_D_IN_DB);
				PS_D_IN_DB = -1;
			}
			break;
		}
	}
}
#endif

  
                                   
 
                      
         

            
                                                                  

          
                                
            
  
                     
   
                                               
                              
   
      
                                   
                                              
                                                                             
  
 

                                                             
 
                      
         

            
                                

          
                                
            
  
                            
   
                                                      
                                     
   
      
                                   
                                            
  

                                              
                                 
                                                                       
 

                                                   
 
                      
            

            
                                               
                                   
 

                                              
 
                           
                       
                                              
 

                                                        
 
         
          

                                

               
  
                                        
                                                                          
                          
                
                                               
      
             
                                                                                                         
                                                                                                       
                                                                                          
                                                                                                                                         
      
                       
                  
                              
                                       
                                                        
                                 
                             
    
                         

                                           

                                                        
               
                                                 
                    
     
                   
                    
     
                    
     
                                                      
                                                        
                                                       
     

                   
              

                   
              
                        
                                             
                        
                                             
                        
                                          
                        
                                              
                        
                                             
                        
                                                
                        
                                              
                        
                     
                                       
     
                        
                                         
         
                                                                     
     
        
              
    
                                  
                  
         
                        
                             
                                                    
         
                       
          
                                                                
         
  
 

                      
 
                             
 

           
                               
 
                                                                                      

                      
         

                   
                                        
                                     
  
                                                        
                                                        
                                                        
  
 
      

             
                         
 
                                                                            

                      
         

                   
                                                 
                                             
  
                                                                   
                                                
                                                        
                                                             
  
 
      

           
                                                                          
                         
 
                                                                          

                      
         

                   
                                                 
                                             
  
                                                                 
                                                        
                                                        
  
 

      
  
