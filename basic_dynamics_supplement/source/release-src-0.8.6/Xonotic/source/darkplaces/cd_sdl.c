  
                                                              
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

#include "quakedef.h"
#include "cdaudio.h"

#if SDL_MAJOR_VERSION == 1 && SDL_MINOR_VERSION == 2
                       

#include <SDL.h>
#include <time.h>

                                                         

                                                                           
static void CDAudio_SDL_CDDrive_f( void );

                                           
static SDL_CD *cd;

static int ValidateDrive( void )
{
	if( cd && SDL_CDStatus( cd ) > 0 )
		return cdValid = true;

	return cdValid = false;
}

void CDAudio_SysEject (void)
{
	SDL_CDEject( cd );
}


void CDAudio_SysCloseDoor (void)
{
	                 
}

int CDAudio_SysGetAudioDiskInfo (void)
{
	if( ValidateDrive() )                                                        
		return cd->numtracks;
	return -1;
}

float CDAudio_SysGetVolume (void)
{
	return -1.0f;
}

void CDAudio_SysSetVolume (float volume)
{
	                 
}

int CDAudio_SysPlay (int track)
{
	return SDL_CDPlayTracks(cd, track-1, 0, 1, 0);
}

int CDAudio_SysStop (void)
{
	return SDL_CDStop( cd );
}

int CDAudio_SysPause (void)
{
	return SDL_CDPause( cd );
}

int CDAudio_SysResume (void)
{
	return SDL_CDResume( cd );
}

int CDAudio_SysUpdate (void)
{
	static time_t lastchk = 0;

	if (cdPlaying && lastchk < time(NULL))
	{
		lastchk = time(NULL) + 2;                           
		if( !cd || cd->status <= 0 ) {
			cdValid = false;
			return -1;
		}
		if (SDL_CDStatus( cd ) == CD_STOPPED)
		{
			if( cdPlayLooping )
				CDAudio_SysPlay( cdPlayTrack );
			else
				cdPlaying = false;
		}
	}
	return 0;
}

void CDAudio_SysInit (void)
{
	if( SDL_InitSubSystem( SDL_INIT_CDROM ) == -1 )
		Con_Print( "Failed to init the CDROM SDL subsystem!\n" );

	Cmd_AddCommand( "cddrive", CDAudio_SDL_CDDrive_f, "select an SDL-detected CD drive by number" );
}

static int IsAudioCD( void )
{
	int i;
	for( i = 0 ; i < cd->numtracks ; i++ )
		if( cd->track[ i ].type == SDL_AUDIO_TRACK )
			return true;
	return false;
}

int CDAudio_SysStartup (void)
{
	int i;
	int numdrives;

	numdrives = SDL_CDNumDrives();
	if( numdrives == -1 )                                               
		return -1;

	Con_Printf( "Found %i cdrom drives.\n", numdrives );

	for( i = 0 ; i < numdrives ; i++, cd = NULL ) {
		cd = SDL_CDOpen( i );
		if( !cd ) {
			Con_Printf( "CD drive %i is invalid.\n", i );
			continue;
		}

		if( CD_INDRIVE( SDL_CDStatus( cd ) ) )
			if( IsAudioCD() )
				break;
			else
				Con_Printf( "The CD in drive %i is not an audio cd.\n", i );
		else
			Con_Printf( "No CD in drive %i.\n", i );

		SDL_CDClose( cd );
	}

	if( i == numdrives && !cd )
		return -1;

	return 0;
}

void CDAudio_SysShutdown (void)
{
	if( cd )
		SDL_CDClose( cd );
}

void CDAudio_SDL_CDDrive_f( void )
{
	int i;
	int numdrives = SDL_CDNumDrives();

	if( Cmd_Argc() != 2 ) {
		Con_Print( "cddrive <drivenr>\n" );
		return;
	}

	i = atoi( Cmd_Argv( 1 ) );
	if( i >= numdrives ) {
		Con_Printf("Only %i drives!\n", numdrives );
		return;
	}

	if( cd )
		SDL_CDClose( cd );

	cd = SDL_CDOpen( i );
	if( !cd ) {
		Con_Printf( "Couldn't open drive %i.\n", i );
		return;
	}

	if( !CD_INDRIVE( SDL_CDStatus( cd ) ) )
		Con_Printf( "No cd in drive %i.\n", i );
	else if( !IsAudioCD() )
		Con_Printf( "The CD in drive %i is not an audio CD.\n", i );

	ValidateDrive();
}





#else
                                 

void CDAudio_SysEject (void)
{
}


void CDAudio_SysCloseDoor (void)
{
}


int CDAudio_SysGetAudioDiskInfo (void)
{
	return -1;
}


float CDAudio_SysGetVolume (void)
{
	return -1.0f;
}


void CDAudio_SysSetVolume (float fvolume)
{
}


int CDAudio_SysPlay (int track)
{
	return -1;
}


int CDAudio_SysStop (void)
{
	return -1;
}


int CDAudio_SysPause (void)
{
	return -1;
}

int CDAudio_SysResume (void)
{
	return -1;
}

int CDAudio_SysUpdate (void)
{
	return -1;
}


void CDAudio_SysInit (void)
{
}

int CDAudio_SysStartup (void)
{
	return -1;
}

void CDAudio_SysShutdown (void)
{
}
#endif

