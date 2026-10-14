  
                                                                           
                                                                     
   

#include "quakedef.h"
#include <errno.h>
#include "capture_telemetry.h"

#define CAPTURE_MAX_ACTIONS 1024
#define CAPTURE_MAX_PENDING_SOUNDS 128
#define CAPTURE_TICKRATE 64.0

typedef struct capture_action_s
{
	int tick;
	float forwardmove;
	float sidemove;
	float yaw_delta;
	float pitch_delta;
	int jump;
	int primary;
	int secondary;
	int weapon_impulse;
	int reload;
}
capture_action_t;

typedef struct capture_pending_sound_s
{
	qboolean active;
	unsigned int event_id;
	int entnum;
	int entchannel;
	double server_time;
	long long server_tick;
	long long scheduled_cursor;
	vec3_t source_origin;
	vec3_t listener_origin;
	char sample_name[MAX_QPATH];
}
capture_pending_sound_t;

cvar_t capture_enable = {0, "capture_enable", "0", "enable deterministic capture instrumentation"};
cvar_t capture_mode = {0, "capture_mode", "0", "0 schedules live usercmds, 1 renders and logs output"};
cvar_t capture_action_file = {0, "capture_action_file", "", "absolute CSV action schedule path"};
cvar_t capture_log_dir = {0, "capture_log_dir", "", "absolute existing output directory"};
cvar_t capture_initial_yaw = {0, "capture_initial_yaw", "0", "deterministic scheduler yaw at episode reset"};
cvar_t capture_initial_pitch = {0, "capture_initial_pitch", "0", "deterministic scheduler pitch at episode reset"};
cvar_t capture_expected_frames = {0, "capture_expected_frames", "320", "stop output after exactly this many frames"};
cvar_t capture_quit_on_end = {0, "capture_quit_on_end", "0", "quit shortly after reaching the exact frame target"};
cvar_t capture_demo_fixedstep = {0, "capture_demo_fixedstep", "0", "reset offline demo presentation to the previous authoritative snapshot"};
cvar_t capture_demo_episode_slowmo = {0, "capture_demo_episode_slowmo", "0", "atomically switch demo playback to this slowmo at episode reset; zero leaves slowmo unchanged"};
cvar_t capture_demo_episode_seed = {0, "capture_demo_episode_seed", "0", "atomically reseed render-only randomness at episode reset"};

extern cvar_t cl_capturevideo;

static capture_action_t capture_actions[CAPTURE_MAX_ACTIONS];
static int capture_num_actions;
static int capture_action_index;
static qboolean capture_action_active;
static qboolean capture_action_prepared;
static float capture_yaw;
static float capture_pitch;
static char capture_episode_id[128];

static FILE *capture_actions_file;
static FILE *capture_frames_file;
static FILE *capture_audio_file;
static int capture_output_frame;
static qboolean capture_output_active;
static qboolean capture_demo_fixedstep_armed;
static long long capture_audio_cursor;
static unsigned int capture_next_sound_id;
static capture_pending_sound_t capture_pending_sounds[CAPTURE_MAX_PENDING_SOUNDS];

static void Capture_CloseFile(FILE **file)
{
	if (*file)
	{
		fflush(*file);
		fclose(*file);
		*file = NULL;
	}
}

static void Capture_CloseLogs(void)
{
	Capture_CloseFile(&capture_actions_file);
	Capture_CloseFile(&capture_frames_file);
	Capture_CloseFile(&capture_audio_file);
}

static qboolean Capture_Path(char *path, size_t path_size, const char *leaf)
{
	if (!capture_log_dir.string[0])
	{
		Con_Print("capture: capture_log_dir is empty\n");
		return false;
	}
	dpsnprintf(path, path_size, "%s/%s", capture_log_dir.string, leaf);
	return true;
}

static FILE *Capture_OpenCSV(const char *leaf, const char *header)
{
	char path[MAX_OSPATH];
	FILE *file;

	if (!Capture_Path(path, sizeof(path), leaf))
		return NULL;
	file = fopen(path, "wb");
	if (!file)
	{
		Con_Printf("capture: failed to open %s: %s\n", path, strerror(errno));
		return NULL;
	}
	fputs(header, file);
	fflush(file);
	return file;
}

static void Capture_FlushPendingSounds(void)
{
	int i;

	if (!capture_audio_file)
		return;
	for (i = 0; i < CAPTURE_MAX_PENDING_SOUNDS; ++i)
	{
		capture_pending_sound_t *pending = &capture_pending_sounds[i];
		if (!pending->active)
			continue;
		fprintf(capture_audio_file,
			"%u,%.9f,%lld,%d,%d,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%lld,-1,\"%s\"\n",
			pending->event_id, pending->server_time, pending->server_tick,
			pending->entnum, pending->entchannel,
			pending->source_origin[0], pending->source_origin[1], pending->source_origin[2],
			pending->listener_origin[0], pending->listener_origin[1], pending->listener_origin[2],
			pending->scheduled_cursor, pending->sample_name);
		pending->active = false;
	}
	fflush(capture_audio_file);
}

static int Capture_LoadActions(void)
{
	FILE *file;
	char line[1024];

	capture_num_actions = 0;
	if (!capture_action_file.string[0])
	{
		Con_Print("capture: capture_action_file is empty\n");
		return 0;
	}
	file = fopen(capture_action_file.string, "rb");
	if (!file)
	{
		Con_Printf("capture: failed to open action schedule %s: %s\n",
			capture_action_file.string, strerror(errno));
		return 0;
	}
	while (fgets(line, sizeof(line), file))
	{
		capture_action_t action;
		int parsed;

		if (line[0] == '#' || !strncmp(line, "tick,", 5))
			continue;
		parsed = sscanf(line, "%d,%f,%f,%f,%f,%d,%d,%d,%d,%d",
			&action.tick, &action.forwardmove, &action.sidemove,
			&action.yaw_delta, &action.pitch_delta, &action.jump,
			&action.primary, &action.secondary, &action.weapon_impulse,
			&action.reload);
		if (parsed != 10)
		{
			Con_Printf("capture: invalid action row: %s", line);
			fclose(file);
			capture_num_actions = 0;
			return 0;
		}
		if (capture_num_actions >= CAPTURE_MAX_ACTIONS)
		{
			Con_Printf("capture: action schedule exceeds %d rows\n", CAPTURE_MAX_ACTIONS);
			fclose(file);
			capture_num_actions = 0;
			return 0;
		}
		capture_actions[capture_num_actions++] = action;
	}
	fclose(file);
	Con_Printf("capture: loaded %d actions from %s\n",
		capture_num_actions, capture_action_file.string);
	return capture_num_actions;
}

static void Capture_EpisodeReset_f(void)
{
	if (!capture_enable.integer)
		return;
	strlcpy(capture_episode_id,
		Cmd_Argc() >= 2 ? Cmd_Argv(1) : "unnamed",
		sizeof(capture_episode_id));
	capture_action_index = 0;
	capture_action_prepared = false;
	capture_output_frame = 0;
	capture_audio_cursor = 0;
	capture_next_sound_id = 1;
	memset(capture_pending_sounds, 0, sizeof(capture_pending_sounds));
	if (capture_mode.integer == 0 && !cls.demoplayback)
	{
		capture_action_active = Capture_LoadActions() > 0;
		capture_yaw = capture_initial_yaw.value;
		capture_pitch = bound(-89.0f, capture_initial_pitch.value, 89.0f);
		cl.viewangles[YAW] = capture_yaw;
		cl.viewangles[PITCH] = capture_pitch;
		cl.viewangles[ROLL] = 0;
		Capture_CloseFile(&capture_actions_file);
		capture_actions_file = Capture_OpenCSV("actions_engine.csv",
			"episode_id,action_index,action_tick,cmd_sequence,cmd_time,"
			"desired_forward,desired_strafe,desired_yaw_delta,desired_pitch_delta,"
			"desired_jump,desired_primary,desired_secondary,desired_weapon_impulse,"
			"desired_reload,sent_forward,sent_strafe,sent_pitch,sent_yaw,"
			"sent_buttons,sent_impulse,jump_edge,primary_edge,secondary_edge,reload_edge\n");
	}
	capture_demo_fixedstep_armed = false;
	if (capture_mode.integer == 1 && cls.demoplayback
		&& capture_demo_fixedstep.integer)
	{
		  
                                                                       
                                                                         
                                                                      
                                                                      
                                                        
     
		cls.timedemo = false;
		if (capture_demo_episode_slowmo.value > 0)
			Cvar_SetValue("slowmo", capture_demo_episode_slowmo.value);
		  
                                                                        
                                                                         
                                                                        
                                                                       
                                                                         
     
		srand((unsigned int)capture_demo_episode_seed.integer);
		cl.time = cl.mtime[1];
		cl.oldtime = cl.time;
		Con_Printf("capture: preroll end id=%s mode=timedemo slowmo=%.12g seed=%d\n",
			capture_episode_id, Cvar_VariableValue("slowmo"),
			capture_demo_episode_seed.integer);
	}
	Con_Printf("capture: episode reset id=%s mode=%d demo=%d demo_fixedstep=%d\n",
		capture_episode_id, capture_mode.integer, cls.demoplayback,
		capture_demo_fixedstep.integer != 0);
}

static void Capture_OutputBegin_f(void)
{
	if (!capture_enable.integer || capture_mode.integer != 1)
		return;
	capture_demo_fixedstep_armed = cls.demoplayback
		&& capture_demo_fixedstep.integer;
	if (capture_demo_fixedstep_armed)
	{
		  
                                                                      
                                                                    
                                                                        
     
		cl.time = cl.mtime[1];
		cl.oldtime = cl.time;
	}
	Capture_CloseFile(&capture_frames_file);
	Capture_CloseFile(&capture_audio_file);
	capture_frames_file = Capture_OpenCSV("frames_engine.csv",
		"episode_id,frame_index,pts_seconds,expected_audio_cursor,mixer_audio_cursor_at_frame,"
		"client_time,server_time_current,server_time_previous,server_tick,interpolation,"
		"camera_x,camera_y,camera_z,forward_x,forward_y,forward_z,"
		"left_x,left_y,left_z,up_x,up_y,up_z,frustum_x,frustum_y,nearclip,farclip,"
		"m00,m01,m02,m03,m10,m11,m12,m13,m20,m21,m22,m23,m30,m31,m32,m33\n");
	capture_audio_file = Capture_OpenCSV("audio_events_engine.csv",
		"event_id,server_time,server_tick,source_entity,source_channel,"
		"source_x,source_y,source_z,listener_x,listener_y,listener_z,"
		"mixer_sample_cursor,waveform_onset_cursor,sample_name\n");
	capture_output_frame = 0;
	capture_audio_cursor = 0;
	capture_next_sound_id = 1;
	memset(capture_pending_sounds, 0, sizeof(capture_pending_sounds));
	capture_output_active = true;
	Cvar_Set("cl_capturevideo", "1");
	Con_Printf("capture: output begin id=%s expected_frames=%d\n",
		capture_episode_id, capture_expected_frames.integer);
	Con_Printf("capture: output timing id=%s slowmo=%.12g\n",
		capture_episode_id, Cvar_VariableValue("slowmo"));
	Con_Printf(
		"capture: hud policy cl_damagetext=%.0f crosshair_hitindication=%.0f "
		"hud_healtharmor=%.0f hud_ammo=%.0f cl_hidewaypoints=%.0f "
		"hud_modicons=%.0f\n",
		Cvar_VariableValue("cl_damagetext"),
		Cvar_VariableValue("crosshair_hitindication"),
		Cvar_VariableValue("hud_panel_healtharmor"),
		Cvar_VariableValue("hud_panel_ammo"),
		Cvar_VariableValue("cl_hidewaypoints"),
		Cvar_VariableValue("hud_panel_modicons"));
}

static void Capture_OutputEnd_f(void)
{
	if (!capture_enable.integer)
		return;
	capture_action_active = false;
	if (capture_mode.integer == 0)
	{
		  
                                                                      
                                                                      
                                                                       
                                                                      
                                                                       
     
		Capture_CloseFile(&capture_actions_file);
	}
	if (capture_mode.integer == 1)
	{
		capture_demo_fixedstep_armed = false;
		Cvar_Set("cl_capturevideo", "0");
		capture_output_active = false;
		Capture_FlushPendingSounds();
		Capture_CloseFile(&capture_frames_file);
		Capture_CloseFile(&capture_audio_file);
	}
	Con_Printf("capture: output end id=%s frames=%d audio_cursor=%lld\n",
		capture_episode_id, capture_output_frame, capture_audio_cursor);
	if (capture_quit_on_end.integer)
	{
		if (capture_mode.integer == 0 && cls.demorecording)
			Cbuf_AddText("stop\n");
		Cbuf_AddText("defer 0.2 quit\n");
	}
}

void Capture_Init(void)
{
	Cvar_RegisterVariable(&capture_enable);
	Cvar_RegisterVariable(&capture_mode);
	Cvar_RegisterVariable(&capture_action_file);
	Cvar_RegisterVariable(&capture_log_dir);
	Cvar_RegisterVariable(&capture_initial_yaw);
	Cvar_RegisterVariable(&capture_initial_pitch);
	Cvar_RegisterVariable(&capture_expected_frames);
	Cvar_RegisterVariable(&capture_quit_on_end);
	Cvar_RegisterVariable(&capture_demo_fixedstep);
	Cvar_RegisterVariable(&capture_demo_episode_slowmo);
	Cvar_RegisterVariable(&capture_demo_episode_seed);
	Cmd_AddCommand("capture_episode_reset", Capture_EpisodeReset_f,
		"reset deterministic capture state for an episode");
	Cmd_AddCommand("capture_output_begin", Capture_OutputBegin_f,
		"begin frame-exact offline video and telemetry output");
	Cmd_AddCommand("capture_output_end", Capture_OutputEnd_f,
		"end deterministic capture output");
}

void Capture_Shutdown(void)
{
	Capture_FlushPendingSounds();
	Capture_CloseLogs();
	capture_action_active = false;
	capture_output_active = false;
	capture_demo_fixedstep_armed = false;
}

void Capture_DemoFixedStepPresentation(void)
{
	double presentation_frametime;

	  
                                                                        
                                                                        
                                                                           
                                                                          
                                                                          
                                        
    
	if (!capture_demo_fixedstep_armed || !capture_enable.integer
		|| capture_mode.integer != 1 || !cls.demoplayback
		|| !capture_demo_fixedstep.integer)
		return;
	cl.time = cl.mtime[1];
	  
                                                                           
                                                                         
                                                               
    
	presentation_frametime = 0.0;
#ifdef CONFIG_VIDEO_CAPTURE
	if (cls.capturevideo.active && cls.capturevideo.framerate > 0.0)
		presentation_frametime = 1.0 / cls.capturevideo.framerate;
#endif
	cl.oldtime = cl.time - bound(0.0, presentation_frametime, 0.1);
}

void Capture_ApplyUsercmd(usercmd_t *cmd)
{
	capture_action_t *action;

	if (!capture_enable.integer || capture_mode.integer != 0 ||
		cls.demoplayback || !capture_action_active)
		return;
	if (capture_action_index >= capture_num_actions)
	{
		cmd->forwardmove = 0;
		cmd->sidemove = 0;
		cmd->buttons = 0;
		cmd->impulse = 0;
		return;
	}
	action = &capture_actions[capture_action_index];
	if (!capture_action_prepared)
	{
		capture_yaw += action->yaw_delta;
		capture_pitch = bound(-89.0f, capture_pitch + action->pitch_delta, 89.0f);
		capture_action_prepared = true;
	}
	cmd->forwardmove = action->forwardmove;
	cmd->sidemove = action->sidemove;
	cmd->upmove = 0;
	cmd->viewangles[PITCH] = capture_pitch;
	cmd->viewangles[YAW] = capture_yaw;
	cmd->viewangles[ROLL] = 0;
	cl.viewangles[PITCH] = capture_pitch;
	cl.viewangles[YAW] = capture_yaw;
	cl.viewangles[ROLL] = 0;
	cmd->buttons = (action->primary ? 1 : 0)
		| (action->jump ? 2 : 0)
		| (action->secondary ? 4 : 0);
	cmd->impulse = action->reload ? 20 : action->weapon_impulse;
}

void Capture_UsercmdSent(const usercmd_t *cmd)
{
	capture_action_t *action;
	capture_action_t *previous;
	int jump_edge;
	int primary_edge;
	int secondary_edge;
	int reload_edge;

	if (!capture_enable.integer || capture_mode.integer != 0 ||
		cls.demoplayback || !capture_action_active ||
		capture_action_index >= capture_num_actions)
		return;
	action = &capture_actions[capture_action_index];
	previous = capture_action_index ? &capture_actions[capture_action_index - 1] : NULL;
	jump_edge = action->jump - (previous ? previous->jump : 0);
	primary_edge = action->primary - (previous ? previous->primary : 0);
	secondary_edge = action->secondary - (previous ? previous->secondary : 0);
	reload_edge = action->reload - (previous ? previous->reload : 0);
	if (capture_actions_file)
	{
		fprintf(capture_actions_file,
			"\"%s\",%d,%d,%u,%.9f,%.6f,%.6f,%.6f,%.6f,"
			"%d,%d,%d,%d,%d,%.6f,%.6f,%.6f,%.6f,%d,%d,%d,%d,%d,%d\n",
			capture_episode_id, capture_action_index, action->tick,
			cmd->sequence, cmd->time, action->forwardmove, action->sidemove,
			action->yaw_delta, action->pitch_delta, action->jump,
			action->primary, action->secondary, action->weapon_impulse,
			action->reload, cmd->forwardmove, cmd->sidemove,
			cmd->viewangles[PITCH], cmd->viewangles[YAW], cmd->buttons,
			cmd->impulse, jump_edge, primary_edge, secondary_edge, reload_edge);
		fflush(capture_actions_file);
	}
	++capture_action_index;
	capture_action_prepared = false;
}

void Capture_VideoFrame(void)
{
	double matrix[16];
	double interpolation;
	long long server_tick;
	int i;

	if (!capture_enable.integer || capture_mode.integer != 1 ||
		!capture_output_active || !capture_frames_file)
		return;
	if (cl.mtime[0] > cl.mtime[1])
		interpolation = bound(0.0,
			(cl.time - cl.mtime[1]) / (cl.mtime[0] - cl.mtime[1]), 1.0);
	else
		interpolation = 1.0;
	server_tick = (long long)floor(cl.mtime[0] * CAPTURE_TICKRATE + 0.5);
	Matrix4x4_ToArrayDoubleGL(&r_refdef.view.matrix, matrix);
	fprintf(capture_frames_file,
		"\"%s\",%d,%.9f,%lld,%lld,%.9f,%.9f,%.9f,%lld,%.9f,"
		"%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,"
		"%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f",
		capture_episode_id, capture_output_frame, capture_output_frame / 64.0,
		(long long)capture_output_frame * 750, capture_audio_cursor,
		cl.time, cl.mtime[0], cl.mtime[1],
		server_tick, interpolation,
		r_refdef.view.origin[0], r_refdef.view.origin[1], r_refdef.view.origin[2],
		r_refdef.view.forward[0], r_refdef.view.forward[1], r_refdef.view.forward[2],
		r_refdef.view.left[0], r_refdef.view.left[1], r_refdef.view.left[2],
		r_refdef.view.up[0], r_refdef.view.up[1], r_refdef.view.up[2],
		r_refdef.view.frustum_x, r_refdef.view.frustum_y,
		r_refdef.nearclip, r_refdef.farclip);
	for (i = 0; i < 16; ++i)
		fprintf(capture_frames_file, ",%.12g", matrix[i]);
	fputc('\n', capture_frames_file);
	fflush(capture_frames_file);
	++capture_output_frame;
	if (capture_expected_frames.integer > 0 &&
		capture_output_frame >= capture_expected_frames.integer)
	{
		  
                                                                       
                                                                      
                                                                
     
		capture_demo_fixedstep_armed = false;
		Cvar_Set("cl_capturevideo", "0");
		capture_output_active = false;
		Capture_FlushPendingSounds();
		Capture_CloseFile(&capture_frames_file);
		Capture_CloseFile(&capture_audio_file);
		Con_Printf("capture: exact frame target reached id=%s frames=%d audio_cursor=%lld\n",
			capture_episode_id, capture_output_frame, capture_audio_cursor);
		if (capture_quit_on_end.integer)
			Cbuf_AddText("defer 0.2 quit\n");
	}
}

void Capture_AudioSamples(const portable_sampleframe_t *paintbuffer, size_t length)
{
	int pending_index;
	long long base_cursor;

	if (!capture_enable.integer || capture_mode.integer != 1 ||
		!capture_audio_file)
		return;
	base_cursor = capture_audio_cursor;
	for (pending_index = 0; pending_index < CAPTURE_MAX_PENDING_SOUNDS; ++pending_index)
	{
		capture_pending_sound_t *pending = &capture_pending_sounds[pending_index];
		size_t start;
		size_t i;
		long long onset = -1;

		if (!pending->active)
			continue;
		if (pending->scheduled_cursor >= base_cursor + (long long)length)
			continue;
		start = pending->scheduled_cursor > base_cursor
			? (size_t)(pending->scheduled_cursor - base_cursor) : 0;
		for (i = start; i < length; ++i)
		{
			if (fabs(paintbuffer[i].sample[0]) > 0.00001f ||
				fabs(paintbuffer[i].sample[1]) > 0.00001f)
			{
				onset = base_cursor + (long long)i;
				break;
			}
		}
		if (onset < 0 && base_cursor + (long long)length
			< pending->scheduled_cursor + 4800)
			continue;
		fprintf(capture_audio_file,
			"%u,%.9f,%lld,%d,%d,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%lld,%lld,\"%s\"\n",
			pending->event_id, pending->server_time, pending->server_tick,
			pending->entnum, pending->entchannel,
			pending->source_origin[0], pending->source_origin[1], pending->source_origin[2],
			pending->listener_origin[0], pending->listener_origin[1], pending->listener_origin[2],
			pending->scheduled_cursor, onset, pending->sample_name);
		pending->active = false;
	}
	capture_audio_cursor += (long long)length;
	fflush(capture_audio_file);
}

void Capture_SoundStart(int entnum, int entchannel, const char *sample_name,
	const vec3_t source_origin)
{
	int i;
	capture_pending_sound_t *pending = NULL;

	if (!capture_enable.integer || capture_mode.integer != 1 ||
		!capture_output_active || !capture_audio_file)
		return;
	for (i = 0; i < CAPTURE_MAX_PENDING_SOUNDS; ++i)
	{
		if (!capture_pending_sounds[i].active)
		{
			pending = &capture_pending_sounds[i];
			break;
		}
	}
	if (!pending)
	{
		Con_Print("capture: pending sound event buffer exhausted\n");
		return;
	}
	memset(pending, 0, sizeof(*pending));
	pending->active = true;
	pending->event_id = capture_next_sound_id++;
	pending->entnum = entnum;
	pending->entchannel = entchannel;
	pending->server_time = cl.mtime[0];
	pending->server_tick = (long long)floor(cl.mtime[0] * CAPTURE_TICKRATE + 0.5);
	pending->scheduled_cursor = capture_audio_cursor;
	VectorCopy(source_origin, pending->source_origin);
	VectorCopy(r_refdef.view.origin, pending->listener_origin);
	strlcpy(pending->sample_name, sample_name, sizeof(pending->sample_name));
}
