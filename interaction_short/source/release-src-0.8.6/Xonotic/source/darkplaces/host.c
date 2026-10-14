  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
                                                              

#include "quakedef.h"

#include <time.h>
#include "libcurl.h"
#ifdef CONFIG_CD
#include "cdaudio.h"
#endif
#include "cl_video.h"
#include "progsvm.h"
#include "csprogs.h"
#include "sv_demo.h"
#include "snd_main.h"
#include "capture_telemetry.h"
#include "thread.h"
#include "utf8lib.h"

  

                                                                          
                   

                                                                        

                                                                               

  

                                
                                                
int host_framecount = 0;
                                       
qboolean host_shuttingdown = false;

                                                                                                           
double realtime;
                                         
double host_dirtytime;

                 
client_t *host_client;

jmp_buf host_abortframe;

                                                                     
cvar_t host_framerate = {0, "host_framerate","0", "locks frame timing to this value in seconds, 0.05 is 20fps for example, note that this can easily run too fast, use cl_maxfps if you want to limit your framerate instead, or sys_ticrate to limit server speed"};
cvar_t cl_maxphysicsframesperserverframe = {0, "cl_maxphysicsframesperserverframe","10", "maximum number of physics frames per server frame"};
                                        
cvar_t host_speeds = {0, "host_speeds","0", "reports how much time is used in server/graphics/sound"};
cvar_t host_maxwait = {0, "host_maxwait","1000", "maximum sleep time requested from the operating system in millisecond. Larger sleeps will be done using multiple host_maxwait length sleeps. Lowering this value will increase CPU load, but may help working around problems with accuracy of sleep times."};
cvar_t cl_minfps = {CVAR_SAVE, "cl_minfps", "40", "minimum fps target - while the rendering performance is below this, it will drift toward lower quality"};
cvar_t cl_minfps_fade = {CVAR_SAVE, "cl_minfps_fade", "1", "how fast the quality adapts to varying framerate"};
cvar_t cl_minfps_qualitymax = {CVAR_SAVE, "cl_minfps_qualitymax", "1", "highest allowed drawdistance multiplier"};
cvar_t cl_minfps_qualitymin = {CVAR_SAVE, "cl_minfps_qualitymin", "0.25", "lowest allowed drawdistance multiplier"};
cvar_t cl_minfps_qualitymultiply = {CVAR_SAVE, "cl_minfps_qualitymultiply", "0.2", "multiplier for quality changes in quality change per second render time (1 assumes linearity of quality and render time)"};
cvar_t cl_minfps_qualityhysteresis = {CVAR_SAVE, "cl_minfps_qualityhysteresis", "0.05", "reduce all quality increments by this to reduce flickering"};
cvar_t cl_minfps_qualitystepmax = {CVAR_SAVE, "cl_minfps_qualitystepmax", "0.1", "maximum quality change in a single frame"};
cvar_t cl_minfps_force = {0, "cl_minfps_force", "0", "also apply quality reductions in timedemo/capturevideo"};
cvar_t cl_maxfps = {CVAR_SAVE, "cl_maxfps", "0", "maximum fps cap, 0 = unlimited, if game is running faster than this it will wait before running another frame (useful to make cpu time available to other programs)"};
cvar_t cl_maxfps_alwayssleep = {0, "cl_maxfps_alwayssleep","1", "gives up some processing time to other applications each frame, value in milliseconds, disabled if cl_maxfps is 0"};
cvar_t cl_maxidlefps = {CVAR_SAVE, "cl_maxidlefps", "20", "maximum fps cap when the game is not the active window (makes cpu time available to other programs"};

cvar_t developer = {CVAR_SAVE, "developer","0", "shows debugging messages and information (recommended for all developers and level designers); the value -1 also suppresses buffering and logging these messages"};
cvar_t developer_extra = {0, "developer_extra", "0", "prints additional debugging messages, often very verbose!"};
cvar_t developer_insane = {0, "developer_insane", "0", "prints huge streams of information about internal workings, entire contents of files being read/written, etc.  Not recommended!"};
cvar_t developer_loadfile = {0, "developer_loadfile","0", "prints name and size of every file loaded via the FS_LoadFile function (which is almost everything)"};
cvar_t developer_loading = {0, "developer_loading","0", "prints information about files as they are loaded or unloaded successfully"};
cvar_t developer_entityparsing = {0, "developer_entityparsing", "0", "prints detailed network entities information each time a packet is received"};

cvar_t timestamps = {CVAR_SAVE, "timestamps", "0", "prints timestamps on console messages"};
cvar_t timeformat = {CVAR_SAVE, "timeformat", "[%Y-%m-%d %H:%M:%S] ", "time format to use on timestamped console messages"};

cvar_t sessionid = {CVAR_READONLY, "sessionid", "", "ID of the current session (use the -sessionid parameter to set it); this is always either empty or begins with a dot (.)"};
cvar_t locksession = {0, "locksession", "0", "Lock the session? 0 = no, 1 = yes and abort on failure, 2 = yes and continue on failure"};

  
                
                      

                                                           
                
  
void Host_AbortCurrentFrame(void) DP_FUNC_NORETURN;
void Host_AbortCurrentFrame(void)
{
	                                                      
	Sys_MakeProcessMean();

	longjmp (host_abortframe, 1);
}

  
                
          

                                          
                
  
void Host_Error (const char *error, ...)
{
	static char hosterrorstring1[MAX_INPUTLINE];                 
	static char hosterrorstring2[MAX_INPUTLINE];                 
	static qboolean hosterror = false;
	va_list argptr;

	                                                                  
	                                                   
	Con_Rcon_Redirect_Abort();

	va_start (argptr,error);
	dpvsnprintf (hosterrorstring1,sizeof(hosterrorstring1),error,argptr);
	va_end (argptr);

	Con_Printf("Host_Error: %s\n", hosterrorstring1);

	                                                                    
	                    
	if (host_framecount < 3 || host_shuttingdown)
		Sys_Error ("Host_Error: %s", hosterrorstring1);

	if (hosterror)
		Sys_Error ("Host_Error: recursively entered (original error was: %s    new error is: %s)", hosterrorstring2, hosterrorstring1);
	hosterror = true;

	strlcpy(hosterrorstring2, hosterrorstring1, sizeof(hosterrorstring2));

	CL_Parse_DumpPacket();

	CL_Parse_ErrorCleanUp();

	             

	                                                                                
	PRVM_Crash(SVVM_prog);
	PRVM_Crash(CLVM_prog);
#ifdef CONFIG_MENU
	PRVM_Crash(MVM_prog);
#endif

	cl.csqc_loaded = false;
	Cvar_SetValueQuick(&csqc_progcrc, -1);
	Cvar_SetValueQuick(&csqc_progsize, -1);

	SV_LockThreadMutex();
	Host_ShutdownServer ();
	SV_UnlockThreadMutex();

	if (cls.state == ca_dedicated)
		Sys_Error ("Host_Error: %s",hosterrorstring2);	                         

	CL_Disconnect ();
	cls.demonum = -1;

	hosterror = false;

	Host_AbortCurrentFrame();
}

static void Host_ServerOptions (void)
{
	int i;

	                  
	svs.maxclients = 8;

                                                                                                                                   
                                                                                                                                                                                
	                                                                  
	                                        
	i = COM_CheckParm ("-dedicated");
	if (i || !cl_available)
	{
		cls.state = ca_dedicated;
		                                                   
		if (i && i + 1 < com_argc && atoi (com_argv[i+1]) >= 1)
			svs.maxclients = atoi (com_argv[i+1]);
		if (COM_CheckParm ("-listen"))
			Con_Printf ("Only one of -dedicated or -listen can be specified\n");
		                                                                                                                                               
		Cvar_SetValue("sv_public", 1);
	}
	else if (cl_available)
	{
		                                                                 
		cls.state = ca_disconnected;
		i = COM_CheckParm ("-listen");
		if (i)
		{
			                                   
			if (i + 1 < com_argc && atoi (com_argv[i+1]) >= 1)
				svs.maxclients = atoi (com_argv[i+1]);
		}
		else
		{
			                                                      
			if (gamemode != GAME_GOODVSBAD2 && !IS_NEXUIZ_DERIVED(gamemode) && gamemode != GAME_BATTLEMECH)
				svs.maxclients = 1;
		}
	}

	svs.maxclients = svs.maxclients_next = bound(1, svs.maxclients, MAX_SCOREBOARD);

	svs.clients = (client_t *)Mem_Alloc(sv_mempool, sizeof(client_t) * svs.maxclients);

	if (svs.maxclients > 1 && !deathmatch.integer && !coop.integer)
		Cvar_SetValueQuick(&deathmatch, 1);
}

  
                       
              
                      
  
void Host_SaveConfig_f(void);
void Host_LoadConfig_f(void);
extern cvar_t sv_writepicture_quality;
extern cvar_t r_texture_jpeg_fastpicmip;
static void Host_InitLocal (void)
{
	Cmd_AddCommand("saveconfig", Host_SaveConfig_f, "save settings to config.cfg (or a specified filename) immediately (also automatic when quitting)");
	Cmd_AddCommand("loadconfig", Host_LoadConfig_f, "reset everything and reload configs");

	Cvar_RegisterVariable (&cl_maxphysicsframesperserverframe);
	Cvar_RegisterVariable (&host_framerate);
	Cvar_RegisterVariable (&host_speeds);
	Cvar_RegisterVariable (&host_maxwait);
	Cvar_RegisterVariable (&cl_minfps);
	Cvar_RegisterVariable (&cl_minfps_fade);
	Cvar_RegisterVariable (&cl_minfps_qualitymax);
	Cvar_RegisterVariable (&cl_minfps_qualitymin);
	Cvar_RegisterVariable (&cl_minfps_qualitystepmax);
	Cvar_RegisterVariable (&cl_minfps_qualityhysteresis);
	Cvar_RegisterVariable (&cl_minfps_qualitymultiply);
	Cvar_RegisterVariable (&cl_minfps_force);
	Cvar_RegisterVariable (&cl_maxfps);
	Cvar_RegisterVariable (&cl_maxfps_alwayssleep);
	Cvar_RegisterVariable (&cl_maxidlefps);

	Cvar_RegisterVariable (&developer);
	Cvar_RegisterVariable (&developer_extra);
	Cvar_RegisterVariable (&developer_insane);
	Cvar_RegisterVariable (&developer_loadfile);
	Cvar_RegisterVariable (&developer_loading);
	Cvar_RegisterVariable (&developer_entityparsing);

	Cvar_RegisterVariable (&timestamps);
	Cvar_RegisterVariable (&timeformat);

	Cvar_RegisterVariable (&sv_writepicture_quality);
	Cvar_RegisterVariable (&r_texture_jpeg_fastpicmip);
}


  
               
                 

                                                    
               
  
static void Host_SaveConfig_to(const char *file)
{
	qfile_t *f;

                                                                    
                   
	                                                          
	if (host_framecount >= 3 && cls.state != ca_dedicated && !COM_CheckParm("-benchmark") && !COM_CheckParm("-capturedemo"))
	{
		f = FS_OpenRealFile(file, "wb", false);
		if (!f)
		{
			Con_Printf("Couldn't write %s.\n", file);
			return;
		}

		Key_WriteBindings (f);
		Cvar_WriteVariables (f);

		FS_Close (f);
	}
}
void Host_SaveConfig(void)
{
	Host_SaveConfig_to(CONFIGFILENAME);
}
void Host_SaveConfig_f(void)
{
	const char *file = CONFIGFILENAME;

	if(Cmd_Argc() >= 2) {
		file = Cmd_Argv(1);
		Con_Printf("Saving to %s\n", file);
	}

	Host_SaveConfig_to(file);
}

static void Host_AddConfigText(void)
{
	                                                                   
	                                                               
	if (gamemode == GAME_NEHAHRA)
		Cbuf_InsertText("alias startmap_sp \"map nehstart\"\nalias startmap_dm \"map nehstart\"\nexec " STARTCONFIGFILENAME "\n");
	else if (gamemode == GAME_TRANSFUSION)
		Cbuf_InsertText("alias startmap_sp \"map e1m1\"\n""alias startmap_dm \"map bb1\"\nexec " STARTCONFIGFILENAME "\n");
	else if (gamemode == GAME_TEU)
		Cbuf_InsertText("alias startmap_sp \"map start\"\nalias startmap_dm \"map start\"\nexec teu.rc\n");
	else
		Cbuf_InsertText("alias startmap_sp \"map start\"\nalias startmap_dm \"map start\"\nexec " STARTCONFIGFILENAME "\n");
}

  
               
                 

                                                                  
               
  
void Host_LoadConfig_f(void)
{
	                                                       
	Cmd_RestoreInitState();
#ifdef CONFIG_MENU
	                                                             
	Cbuf_InsertText("\nmenu_restart\n");
#endif
	                                                                     
	Host_AddConfigText();
}

  
                 
              

                                 
                                     
                 
  
void SV_ClientPrint(const char *msg)
{
	if (host_client->netconnection)
	{
		MSG_WriteByte(&host_client->netconnection->message, svc_print);
		MSG_WriteString(&host_client->netconnection->message, msg);
	}
}

  
                 
               

                                 
                                     
                 
  
void SV_ClientPrintf(const char *fmt, ...)
{
	va_list argptr;
	char msg[MAX_INPUTLINE];

	va_start(argptr,fmt);
	dpvsnprintf(msg,sizeof(msg),fmt,argptr);
	va_end(argptr);

	SV_ClientPrint(msg);
}

  
                 
                 

                                
                 
  
void SV_BroadcastPrint(const char *msg)
{
	int i;
	client_t *client;

	for (i = 0, client = svs.clients;i < svs.maxclients;i++, client++)
	{
		if (client->active && client->netconnection)
		{
			MSG_WriteByte(&client->netconnection->message, svc_print);
			MSG_WriteString(&client->netconnection->message, msg);
		}
	}

	if (sv_echobprint.integer && cls.state == ca_dedicated)
		Con_Print(msg);
}

  
                 
                  

                                
                 
  
void SV_BroadcastPrintf(const char *fmt, ...)
{
	va_list argptr;
	char msg[MAX_INPUTLINE];

	va_start(argptr,fmt);
	dpvsnprintf(msg,sizeof(msg),fmt,argptr);
	va_end(argptr);

	SV_BroadcastPrint(msg);
}

  
                 
                   

                                           
                 
  
void Host_ClientCommands(const char *fmt, ...)
{
	va_list argptr;
	char string[MAX_INPUTLINE];

	if (!host_client->netconnection)
		return;

	va_start(argptr,fmt);
	dpvsnprintf(string, sizeof(string), fmt, argptr);
	va_end(argptr);

	MSG_WriteByte(&host_client->netconnection->message, svc_stufftext);
	MSG_WriteString(&host_client->netconnection->message, string);
}

  
                     
             

                                                             
                                               
                     
  
void SV_DropClient(qboolean crash)
{
	prvm_prog_t *prog = SVVM_prog;
	int i;
	Con_Printf("Client \"%s\" dropped\n", host_client->name);

	SV_StopDemoRecording(host_client);

	                                                                   
	host_client->edict = PRVM_EDICT_NUM(host_client - svs.clients + 1);

	if (host_client->netconnection)
	{
		                             
		if (!crash)
		{
			                                                                     
			unsigned char bufdata[8];
			sizebuf_t buf;
			memset(&buf, 0, sizeof(buf));
			buf.data = bufdata;
			buf.maxsize = sizeof(bufdata);
			MSG_WriteByte(&buf, svc_disconnect);
			NetConn_SendUnreliableMessage(host_client->netconnection, &buf, sv.protocol, 10000, 0, false);
			NetConn_SendUnreliableMessage(host_client->netconnection, &buf, sv.protocol, 10000, 0, false);
			NetConn_SendUnreliableMessage(host_client->netconnection, &buf, sv.protocol, 10000, 0, false);
		}
	}

	                                    
	                                                               
	                                                       
	if (host_client->clientconnectcalled && sv.active && host_client->edict)
	{
		                                               
		                                                             
		int saveSelf = PRVM_serverglobaledict(self);
		host_client->clientconnectcalled = false;
		PRVM_serverglobalfloat(time) = sv.time;
		PRVM_serverglobaledict(self) = PRVM_EDICT_TO_PROG(host_client->edict);
		prog->ExecuteProgram(prog, PRVM_serverfunction(ClientDisconnect), "QC function ClientDisconnect is missing");
		PRVM_serverglobaledict(self) = saveSelf;
	}

	if (host_client->netconnection)
	{
		                           
		NetConn_Close(host_client->netconnection);
		host_client->netconnection = NULL;
	}

	                                    
	if (host_client->download_file)
	{
		Con_DPrintf("Download of %s aborted when %s dropped\n", host_client->download_name, host_client->name);
		FS_Close(host_client->download_file);
		host_client->download_file = NULL;
		host_client->download_name[0] = 0;
		host_client->download_expectedposition = 0;
		host_client->download_started = false;
	}

	                                        
	host_client->name[0] = 0;
	host_client->colors = 0;
	host_client->frags = 0;
	                                   
	                                                                     
	i = host_client - svs.clients;
	MSG_WriteByte (&sv.reliable_datagram, svc_updatename);
	MSG_WriteByte (&sv.reliable_datagram, i);
	MSG_WriteString (&sv.reliable_datagram, host_client->name);
	MSG_WriteByte (&sv.reliable_datagram, svc_updatecolors);
	MSG_WriteByte (&sv.reliable_datagram, i);
	MSG_WriteByte (&sv.reliable_datagram, host_client->colors);
	MSG_WriteByte (&sv.reliable_datagram, svc_updatefrags);
	MSG_WriteByte (&sv.reliable_datagram, i);
	MSG_WriteShort (&sv.reliable_datagram, host_client->frags);

	                      
	if (host_client->entitydatabase)
		EntityFrame_FreeDatabase(host_client->entitydatabase);
	if (host_client->entitydatabase4)
		EntityFrame4_FreeDatabase(host_client->entitydatabase4);
	if (host_client->entitydatabase5)
		EntityFrame5_FreeDatabase(host_client->entitydatabase5);

	if (sv.active)
	{
		                                                                                        
		PRVM_ED_ClearEdict(prog, host_client->edict);
	}

	                                                      
	memset(host_client, 0, sizeof(*host_client));

	                                                                   
	                                                           
	NetConn_Heartbeat(1);

	if (sv.loadgame)
	{
		for (i = 0;i < svs.maxclients;i++)
			if (svs.clients[i].active && !svs.clients[i].spawned)
				break;
		if (i == svs.maxclients)
		{
			Con_Printf("Loaded game, everyone rejoined - unpausing\n");
			sv.paused = sv.loadgame = false;                                         
		}
	}
}

  
                  
                   

                                                          
                  
  
void Host_ShutdownServer(void)
{
	prvm_prog_t *prog = SVVM_prog;
	int i;

	Con_DPrintf("Host_ShutdownServer\n");

	if (!sv.active)
		return;

	NetConn_Heartbeat(2);
	NetConn_Heartbeat(2);

                                                     
	World_End(&sv.world);
	if(prog->loaded)
	{
		if(PRVM_serverfunction(SV_Shutdown))
		{
			func_t s = PRVM_serverfunction(SV_Shutdown);
			PRVM_serverglobalfloat(time) = sv.time;
			PRVM_serverfunction(SV_Shutdown) = 0;                                        
			prog->ExecuteProgram(prog, s,"SV_Shutdown() required");
		}
	}
	for (i = 0, host_client = svs.clients;i < svs.maxclients;i++, host_client++)
		if (host_client->active)
			SV_DropClient(false);                   

	NetConn_CloseServerPorts();

	sv.active = false;
  
                   
  
	memset(&sv, 0, sizeof(sv));
	memset(svs.clients, 0, svs.maxclients*sizeof(client_t));

	cl.islocalgame = false;
}


                                                                              

  
                   
                       

                                                         
                   
  
static void Host_GetConsoleCommands (void)
{
	char *cmd;

	while (1)
	{
		cmd = Sys_ConsoleInput ();
		if (!cmd)
			break;
		Cbuf_AddText (cmd);
	}
}

  
                  
               

                                             
                  
  
const char *Host_TimingReport(char *buf, size_t buflen)
{
	return va(buf, buflen, "%.1f%% CPU, %.2f%% lost, offset avg %.1fms, max %.1fms, sdev %.1fms", svs.perf_cpuload * 100, svs.perf_lost * 100, svs.perf_offset_avg * 1000, svs.perf_offset_max * 1000, svs.perf_offset_sdev * 1000);
}

  
                  
          

                       
                  
  
static void Host_Init(void);
void Host_Main(void)
{
	double time1 = 0;
	double time2 = 0;
	double time3 = 0;
	double cl_timer = 0, sv_timer = 0;
	double clframetime, deltacleantime, olddirtytime, dirtytime;
	double wait;
	int pass1, pass2, pass3, i;
	char vabuf[1024];
	qboolean playing;

	Host_Init();

	realtime = 0;
	host_dirtytime = Sys_DirtyTime();
	for (;;)
	{
		if (setjmp(host_abortframe))
		{
			SCR_ClearLoadingScreen(false);
			continue;			                                                     
		}

		olddirtytime = host_dirtytime;
		dirtytime = Sys_DirtyTime();
		deltacleantime = dirtytime - olddirtytime;
		if (deltacleantime < 0)
		{
			                           
			if (deltacleantime < -0.01)
				Con_Printf("Host_Mingled: time stepped backwards (went from %f to %f, difference %f)\n", olddirtytime, dirtytime, deltacleantime);
			deltacleantime = 0;
		}
		else if (deltacleantime >= 1800)
		{
			Con_Printf("Host_Mingled: time stepped forward (went from %f to %f, difference %f)\n", olddirtytime, dirtytime, deltacleantime);
			deltacleantime = 0;
		}
		realtime += deltacleantime;
		host_dirtytime = dirtytime;

		cl_timer += deltacleantime;
		sv_timer += deltacleantime;

		if (!svs.threaded)
		{
			svs.perf_acc_realtime += deltacleantime;

			                                    
			playing = false;
			for (i = 0, host_client = svs.clients;i < svs.maxclients;i++, host_client++)
				if(host_client->begun)
					if(host_client->netconnection)
						playing = true;
			if(sv.time < 10)
			{
				                                                            
				                       
				svs.perf_acc_realtime = svs.perf_acc_sleeptime = svs.perf_acc_lost = svs.perf_acc_offset = svs.perf_acc_offset_squared = svs.perf_acc_offset_max = svs.perf_acc_offset_samples = 0;
			}
			else if(svs.perf_acc_realtime > 5)
			{
				svs.perf_cpuload = 1 - svs.perf_acc_sleeptime / svs.perf_acc_realtime;
				svs.perf_lost = svs.perf_acc_lost / svs.perf_acc_realtime;
				if(svs.perf_acc_offset_samples > 0)
				{
					svs.perf_offset_max = svs.perf_acc_offset_max;
					svs.perf_offset_avg = svs.perf_acc_offset / svs.perf_acc_offset_samples;
					svs.perf_offset_sdev = sqrt(svs.perf_acc_offset_squared / svs.perf_acc_offset_samples - svs.perf_offset_avg * svs.perf_offset_avg);
				}
				if(svs.perf_lost > 0 && developer_extra.integer)
					if(playing)                                      
						Con_DPrintf("Server can't keep up: %s\n", Host_TimingReport(vabuf, sizeof(vabuf)));
				svs.perf_acc_realtime = svs.perf_acc_sleeptime = svs.perf_acc_lost = svs.perf_acc_offset = svs.perf_acc_offset_squared = svs.perf_acc_offset_max = svs.perf_acc_offset_samples = 0;
			}
		}

		if (slowmo.value < 0.00001 && slowmo.value != 0)
			Cvar_SetValue("slowmo", 0);
		if (host_framerate.value < 0.00001 && host_framerate.value != 0)
			Cvar_SetValue("host_framerate", 0);

		                                                                          
		if(!*sv_random_seed.string && !cls.demoplayback)
			rand();

		                     
		Key_EventQueue_Unblock();
		SndSys_SendKeyEvents();
		Sys_SendKeyEvents();

		NetConn_UpdateSockets();

		Log_DestBuffer_Flush();

		                                                                    
		                                                          
		if (sv.active && !svs.threaded)
			NetConn_ServerFrame();

		Curl_Run();

		                                       
		Host_GetConsoleCommands();

		                                                                             
		                                                                                                        
		                                             
		if (sv.active ? sv_timer > 0 : cl_timer > 0)
		{
			                           
                                
			CL_VM_PreventInformationLeaks();
			Cbuf_Frame();
                             
		}

		                                                                          

		                                                                
		if (cls.state == ca_dedicated)
			wait = sv_timer * -1000000.0;
		else if (!sv.active || svs.threaded)
			wait = cl_timer * -1000000.0;
		else
			wait = max(cl_timer, sv_timer) * -1000000.0;

		if (!cls.timedemo && !SCR_CaptureVideo_OfflineDemoAccelerating() && wait >= 1)
		{
			double time0, delta;

			if(host_maxwait.value <= 0)
				wait = min(wait, 1000000.0);
			else
				wait = min(wait, host_maxwait.value * 1000.0);
			if(wait < 1)
				wait = 1;                          

			time0 = Sys_DirtyTime();
			if (sv_checkforpacketsduringsleep.integer && !sys_usenoclockbutbenchmark.integer && !svs.threaded) {
				NetConn_SleepMicroseconds((int)wait);
				if (cls.state != ca_dedicated)
					NetConn_ClientFrame();                                             
				                                                         
			}
			else
				Sys_Sleep((int)wait);
			delta = Sys_DirtyTime() - time0;
			if (delta < 0 || delta >= 1800) delta = 0;
			if (!svs.threaded)
				svs.perf_acc_sleeptime += delta;
                           
			continue;
		}

		                                                       
		if (cl_timer > 0.1)
			cl_timer = 0.1;
		if (sv_timer > 0.1)
		{
			if (!svs.threaded)
				svs.perf_acc_lost += (sv_timer - 0.1);
			sv_timer = 0.1;
		}

		R_TimeReport("---");

	                     
	  
	                    
	  
	                     

		                                                       
		if (sv.active && sv_timer > 0 && !svs.threaded)
		{
			                                                                     
			                                                                         
			                                                                          
			                                              
			int framecount, framelimit = 1;
			double advancetime, aborttime = 0;
			float offset;
			prvm_prog_t *prog = SVVM_prog;

			                      
			                                                                                 

			                                                                 
			if (sys_ticrate.value <= 0)
				advancetime = sv_timer;
			else if (cl.islocalgame && !sv_fixedframeratesingleplayer.integer)
			{
				                                                                                    
				advancetime = bound(0.01, cl_timer, 0.1);
			}
			else
			{
				advancetime = sys_ticrate.value;
				                                                                 
				framelimit = cl_maxphysicsframesperserverframe.integer;
				aborttime = Sys_DirtyTime() + 0.1;
			}
			if(slowmo.value > 0 && slowmo.value < 1)
				advancetime = min(advancetime, 0.1 / slowmo.value);
			else
				advancetime = min(advancetime, 0.1);

			if(advancetime > 0)
			{
				offset = Sys_DirtyTime() - dirtytime;if (offset < 0 || offset >= 1800) offset = 0;
				offset += sv_timer;
				++svs.perf_acc_offset_samples;
				svs.perf_acc_offset += offset;
				svs.perf_acc_offset_squared += offset * offset;
				if(svs.perf_acc_offset_max < offset)
					svs.perf_acc_offset_max = offset;
			}

			                                  
			                                                                    
			sv.frametime = advancetime * slowmo.value;
			if (host_framerate.value)
				sv.frametime = host_framerate.value;
			if (sv.paused || (cl.islocalgame && (key_dest != key_game || key_consoleactive || cl.csqc_paused)))
				sv.frametime = 0;

			for (framecount = 0;framecount < framelimit && sv_timer > 0;framecount++)
			{
				sv_timer -= advancetime;

				                                             
				if (sv.frametime)
					SV_Physics();

				                                                            
				if (framelimit > 1 && Sys_DirtyTime() >= aborttime)
					break;
			}
			R_TimeReport("serverphysics");

			                                   
			SV_SendClientMessages();

			if (sv.paused == 1 && realtime > sv.pausedstart && sv.pausedstart > 0) {
				prog->globals.fp[OFS_PARM0] = realtime - sv.pausedstart;
				PRVM_serverglobalfloat(time) = sv.time;
				prog->ExecuteProgram(prog, PRVM_serverfunction(SV_PausedTic), "QC function SV_PausedTic is missing");
			}

			                                                                 
			NetConn_Heartbeat(0);
			R_TimeReport("servernetwork");
		}
		else if (!svs.threaded)
		{
			                                         
			R_TimeReport("serverphysics");
			R_TimeReport("servernetwork");
		}

	                     
	  
	                    
	  
	                     

		if (cls.state != ca_dedicated && (cl_timer > 0 || cls.timedemo || SCR_CaptureVideo_OfflineDemoAccelerating() || ((vid_activewindow ? cl_maxfps : cl_maxidlefps).value < 1)))
		{
			R_TimeReport("---");
			Collision_Cache_NewFrame();
			R_TimeReport("photoncache");
			                             
			if (cls.capturevideo.active)
			{
				     
				if (cls.capturevideo.realtime)
					clframetime = cl.realframetime = max(cl_timer, 1.0 / cls.capturevideo.framerate);
				else
				{
					clframetime = 1.0 / cls.capturevideo.framerate;
					cl.realframetime = max(cl_timer, clframetime);
				}
			}
			else if (vid_activewindow && cl_maxfps.value >= 1 && !cls.timedemo)
			{
				clframetime = cl.realframetime = max(cl_timer, 1.0 / cl_maxfps.value);
				                                                               
				wait = bound(0, cl_maxfps_alwayssleep.value * 1000, 100000);
				if (wait > 0)
					Sys_Sleep((int)wait);
			}
			else if (!vid_activewindow && cl_maxidlefps.value >= 1 && !cls.timedemo)
				clframetime = cl.realframetime = max(cl_timer, 1.0 / cl_maxidlefps.value);
			else
				clframetime = cl.realframetime = cl_timer;

			                       
			clframetime *= cl.movevars_timescale;
			                                               
			if (cls.demoplayback)
			{
				clframetime *= slowmo.value;
				                                                        
				if (cls.demopaused)
					clframetime = 0;
			}
			else
			{
				                                    
				if (host_framerate.value)
					clframetime = host_framerate.value;

				if (cl.paused || (cl.islocalgame && (key_dest != key_game || key_consoleactive || cl.csqc_paused)))
					clframetime = 0;
			}

			if (cls.timedemo)
				clframetime = cl.realframetime = cl_timer;

			                                             
			cl_timer -= cl.realframetime;
			                                                                     
			                                                                       
			                                                                   
			if (SCR_CaptureVideo_OfflineDemoAccelerating())
				cl_timer = 0;

			cl.oldtime = cl.time;
			cl.time += clframetime;

			               
			if (host_speeds.integer)
				time1 = Sys_DirtyTime();
			R_TimeReport("pre-input");

			                         
			CL_Input();

			R_TimeReport("input");

			                        
			NetConn_ClientFrame();

			                                         
			CL_ReadDemoMessage();
			Capture_DemoFixedStepPresentation();
			R_TimeReport("clientnetwork");

			                                                        
			CL_SendMove();
			R_TimeReport("sendmove");

			                                                                 
			CL_UpdateWorld();
			R_TimeReport("lerpworld");

			CL_Video_Frame();

			R_TimeReport("client");

			CL_UpdateScreen();
			CL_MeshEntities_Reset();
			R_TimeReport("render");

			if (host_speeds.integer)
				time2 = Sys_DirtyTime();

			               
			if(cl.csqc_usecsqclistener)
			{
				S_Update(&cl.csqc_listenermatrix);
				cl.csqc_usecsqclistener = false;
			}
			else
				S_Update(&r_refdef.view.matrix);

#ifdef CONFIG_CD
			CDAudio_Update();
			R_TimeReport("audio");
#endif

			                                 
			in_mouse_x = in_mouse_y = 0;

			if (host_speeds.integer)
			{
				pass1 = (int)((time1 - time3)*1000000);
				time3 = Sys_DirtyTime();
				pass2 = (int)((time2 - time1)*1000000);
				pass3 = (int)((time3 - time2)*1000000);
				Con_Printf("%6ius total %6ius server %6ius gfx %6ius snd\n",
							pass1+pass2+pass3, pass1, pass2, pass3);
			}
		}

#if MEMPARANOIA
		Mem_CheckSentinelsGlobal();
#else
		if (developer_memorydebug.integer)
			Mem_CheckSentinelsGlobal();
#endif

		                                                                    
		if (cl_timer >= 0)
			cl_timer = 0;
		if (sv_timer >= 0)
		{
			if (!svs.threaded)
				svs.perf_acc_lost += sv_timer;
			sv_timer = 0;
		}

		host_framecount++;
	}
}

                                                                              

qboolean vid_opened = false;
void Host_StartVideo(void)
{
	if (!vid_opened && cls.state != ca_dedicated)
	{
		vid_opened = true;
		                                                                                                                                                           
		NetConn_UpdateSockets();
		VID_Start();
#ifdef CONFIG_CD
		CDAudio_Startup();
#endif
	}
}

char engineversion[128];

qboolean sys_nostdout = false;

extern qboolean host_stuffcmdsrun;

static qfile_t *locksession_fh = NULL;
static qboolean locksession_run = false;
static void Host_InitSession(void)
{
	int i;
	Cvar_RegisterVariable(&sessionid);
	Cvar_RegisterVariable(&locksession);

	                                              
	if ((i = COM_CheckParm("-sessionid")) && (i + 1 < com_argc))
	{
		char vabuf[1024];
		if(com_argv[i+1][0] == '.')
			Cvar_SetQuick(&sessionid, com_argv[i+1]);
		else
			Cvar_SetQuick(&sessionid, va(vabuf, sizeof(vabuf), ".%s", com_argv[i+1]));
	}
}
void Host_LockSession(void)
{
	if(locksession_run)
		return;
	locksession_run = true;
	if(locksession.integer != 0 && !COM_CheckParm("-readonly"))
	{
		char vabuf[1024];
		char *p = va(vabuf, sizeof(vabuf), "%slock%s", *fs_userdir ? fs_userdir : fs_basedir, sessionid.string);
		FS_CreatePath(p);
		locksession_fh = FS_SysOpen(p, "wl", false);
		                                                                                                   
		if(!locksession_fh)
		{
			if(locksession.integer == 2)
			{
				Con_Printf("WARNING: session lock %s could not be acquired. Please run with -sessionid and an unique session name. Continuing anyway.\n", p);
			}
			else
			{
				Sys_Error("session lock %s could not be acquired. Please run with -sessionid and an unique session name.\n", p);
			}
		}
	}
}
void Host_UnlockSession(void)
{
	if(!locksession_run)
		return;
	locksession_run = false;

	if(locksession_fh)
	{
		FS_Close(locksession_fh);
		                                                           
		                                                        
		                                   
		locksession_fh = NULL;
	}
}

  
                    
         
                    
  
static void Host_Init (void)
{
	int i;
	const char* os;
	char vabuf[1024];

	if (COM_CheckParm("-profilegameonly"))
		Sys_AllowProfiling(false);

	                                                                          
	if (COM_CheckParm("-benchmark"))
		srand(0);                                              
	else
		srand((unsigned int)time(NULL));

	                                              
	                                            
	                                    
                                                                                                             
	if (COM_CheckParm("-developer"))
	{
		developer.value = developer.integer = 1;
		developer.string = "1";
	}

	if (COM_CheckParm("-developer2") || COM_CheckParm("-developer3"))
	{
		developer.value = developer.integer = 1;
		developer.string = "1";
		developer_extra.value = developer_extra.integer = 1;
		developer_extra.string = "1";
		developer_insane.value = developer_insane.integer = 1;
		developer_insane.string = "1";
		developer_memory.value = developer_memory.integer = 1;
		developer_memory.string = "1";
		developer_memorydebug.value = developer_memorydebug.integer = 1;
		developer_memorydebug.string = "1";
	}

	if (COM_CheckParm("-developer3"))
	{
		gl_paranoid.integer = 1;gl_paranoid.string = "1";
		gl_printcheckerror.integer = 1;gl_printcheckerror.string = "1";
	}

                                                                                                        
	if (COM_CheckParm("-nostdout"))
		sys_nostdout = 1;

	                     
	Memory_Init();

	                                                                  
	Cmd_Init();

	                                             
	Memory_Init_Commands();

	                                                        
	Con_Init();

	                                                                 
	u8_Init();
	Curl_Init_Commands();
	Cmd_Init_Commands();
	Sys_Init_Commands();
	COM_Init_Commands();
	FS_Init_Commands();

	                                                     
	Sys_InitConsole();

	                                                                                                
	FS_Init_SelfPack();

	                                                              
	COM_InitGameType();

	                                                           
	os = DP_OS_NAME;
	dpsnprintf (engineversion, sizeof (engineversion), "%s %s %s", gamename, os, buildstring);
	Con_Printf("%s\n", engineversion);

	                                
	Sys_InitProcessNice();

	                     
	Mathlib_Init();

	                                                                                       
	FS_Init();

	                                         
	Host_InitSession();

	                        
	Crypto_Init();
	Crypto_Init_Commands();

	NetConn_Init();
	Curl_Init();
	            
	                
	PRVM_Init();
	Mod_Init();
	World_Init();
	SV_Init();
	V_Init();                                                                 
	Host_InitCommands();
	Host_InitLocal();
	Host_ServerOptions();

	Thread_Init();

	if (cls.state == ca_dedicated)
		Cmd_AddCommand ("disconnect", CL_Disconnect_f, "disconnect from server (or disconnect all clients if running a server)");
	else
	{
		Con_DPrintf("Initializing client\n");

		R_Modules_Init();
		Palette_Init();
#ifdef CONFIG_MENU
		MR_Init_Commands();
#endif
		VID_Shared_Init();
		VID_Init();
		Render_Init();
		S_Init();
#ifdef CONFIG_CD
		CDAudio_Init();
#endif
		Key_Init();
		CL_Init();
	}

	                                                                                                    
	                                                        
	Cmd_SaveInitState();

	                                                                                 
	                                                                                

	                                       
	if (setjmp(host_abortframe)) {
		return;
	}

	Host_AddConfigText();
	Cbuf_Execute();

	                                                                          
	if (!host_stuffcmdsrun)
	{
		Cbuf_AddText("exec default.cfg\nexec " CONFIGFILENAME "\nexec autoexec.cfg\nstuffcmds\n");
		Cbuf_Execute();
	}

	                                                                          
	SCR_BeginLoadingPlaque(true);

#ifdef CONFIG_MENU
	if (cls.state != ca_dedicated)
	{
		MR_Init();
	}
#endif

	                                   
                                                                                                                                                                            
	i = COM_CheckParm("-benchmark");
	if (i && i + 1 < com_argc)
	if (!sv.active && !cls.demoplayback && !cls.connect_trying)
	{
		Cbuf_AddText(va(vabuf, sizeof(vabuf), "timedemo %s\n", com_argv[i + 1]));
		Cbuf_Execute();
	}

	                              
                                                                        
	i = COM_CheckParm("-demo");
	if (i && i + 1 < com_argc)
	if (!sv.active && !cls.demoplayback && !cls.connect_trying)
	{
		Cbuf_AddText(va(vabuf, sizeof(vabuf), "playdemo %s\n", com_argv[i + 1]));
		Cbuf_Execute();
	}

                                                                                   
	i = COM_CheckParm("-capturedemo");
	if (i && i + 1 < com_argc)
	if (!sv.active && !cls.demoplayback && !cls.connect_trying)
	{
		Cbuf_AddText(va(vabuf, sizeof(vabuf), "playdemo %s\ncl_capturevideo 1\n", com_argv[i + 1]));
		Cbuf_Execute();
	}

	if (cls.state == ca_dedicated || COM_CheckParm("-listen"))
	if (!sv.active && !cls.demoplayback && !cls.connect_trying)
	{
		Cbuf_AddText("startmap_dm\n");
		Cbuf_Execute();
	}

	if (!sv.active && !cls.demoplayback && !cls.connect_trying)
	{
#ifdef CONFIG_MENU
		Cbuf_AddText("togglemenu 1\n");
#endif
		Cbuf_Execute();
	}

	Con_DPrint("========Initialized=========\n");

	                    

	if (cls.state != ca_dedicated)
		SV_StartThread();
}


  
               
             

                                                                          
                                                                  
               
  
void Host_Shutdown(void)
{
	static qboolean isdown = false;

	if (isdown)
	{
		Con_Print("recursive shutdown\n");
		return;
	}
	if (setjmp(host_abortframe))
	{
		Con_Print("aborted the quitting frame?!?\n");
		return;
	}
	isdown = true;

	                               
	S_StopAllSounds();

	                        
	if (svs.threaded)
		SV_StopThread();

	                                          
	CL_Disconnect();

	                                   
	SV_LockThreadMutex();
	Host_ShutdownServer ();
	SV_UnlockThreadMutex();

#ifdef CONFIG_MENU
	                
	if(MR_Shutdown)
		MR_Shutdown();
#endif

	                   
	                                  

	CL_Video_Shutdown();

	Host_SaveConfig();

#ifdef CONFIG_CD
	CDAudio_Shutdown ();
#endif
	S_Terminate ();
	Curl_Shutdown ();
	NetConn_Shutdown ();
	                 

	if (cls.state != ca_dedicated)
	{
		R_Modules_Shutdown();
		VID_Shutdown();
	}

	SV_StopThread();
	Thread_Shutdown();
	Cmd_Shutdown();
	Key_Shutdown();
	CL_Shutdown();
	Sys_Shutdown();
	Log_Close();
	Crypto_Shutdown();

	Host_UnlockSession();

	S_Shutdown();
	Con_Shutdown();
	Memory_Shutdown();
}
