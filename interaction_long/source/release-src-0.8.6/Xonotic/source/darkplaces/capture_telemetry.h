#ifndef CAPTURE_TELEMETRY_H
#define CAPTURE_TELEMETRY_H

#include "snd_main.h"

void Capture_Init(void);
void Capture_Shutdown(void);
void Capture_ApplyUsercmd(usercmd_t *cmd);
void Capture_UsercmdSent(const usercmd_t *cmd);
qboolean Capture_DemoFixedStepReadReady(double client_time,
	double snapshot_time);
void Capture_DemoFixedStepPresentation(void);
void Capture_VideoFrame(void);
void Capture_AudioSamples(const portable_sampleframe_t *paintbuffer, size_t length);
void Capture_SoundStart(int entnum, int entchannel, const char *sample_name,
	const vec3_t source_origin);

#endif
