#ifndef CAPTURE_TELEMETRY_H
#define CAPTURE_TELEMETRY_H

#include "snd_main.h"

void Capture_Init(void);
void Capture_Shutdown(void);
void Capture_ApplyUsercmd(usercmd_t *cmd);
void Capture_UsercmdSent(const usercmd_t *cmd);
void Capture_DemoControlMessageParsed(const char *text);
qboolean Capture_DemoConsumeControlMessageBoundary(void);
void Capture_DemoNetworkTimeAdvanced(void);
void Capture_DemoNetworkStepReadBegin(void);
qboolean Capture_DemoConsumeNetworkTimeBoundary(void);
qboolean Capture_DemoConsumeOutputPrime(void);
double Capture_DemoFixedFrameTime(void);
void Capture_VideoFrame(void);
void Capture_AudioSamples(const portable_sampleframe_t *paintbuffer, size_t length);
void Capture_SoundStart(int entnum, int entchannel, const char *sample_name,
	const vec3_t source_origin);

#endif
