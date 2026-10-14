  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

#include "quakedef.h"

#include "cl_collision.h"
#include "image.h"
#include "r_shadow.h"

                            
particletype_t particletype[pt_total] =
{
	{PBLEND_INVALID, PARTICLE_INVALID, false},                                
	{PBLEND_ALPHA, PARTICLE_BILLBOARD, false},                 
	{PBLEND_ADD, PARTICLE_BILLBOARD, false},            
	{PBLEND_ADD, PARTICLE_SPARK, false},           
	{PBLEND_ADD, PARTICLE_HBEAM, false},          
	{PBLEND_ADD, PARTICLE_SPARK, false},          
	{PBLEND_ADD, PARTICLE_ORIENTED_DOUBLESIDED, false},               
	{PBLEND_ADD, PARTICLE_BILLBOARD, false},          
	{PBLEND_ADD, PARTICLE_BILLBOARD, false},            
	{PBLEND_INVMOD, PARTICLE_BILLBOARD, false},           
	{PBLEND_ADD, PARTICLE_BILLBOARD, false},           
	{PBLEND_INVMOD, PARTICLE_ORIENTED_DOUBLESIDED, false},           
	{PBLEND_ALPHA, PARTICLE_BILLBOARD, false},                    
};

#define PARTICLEEFFECT_UNDERWATER 1
#define PARTICLEEFFECT_NOTUNDERWATER 2
#define PARTICLEEFFECT_DEFINED 2147483648U

typedef struct particleeffectinfo_s
{
	int effectnameindex;                                
	                        
	int flags;
	                                                                          
	                                                                        
	double particleaccumulator;
	                                                                          
	                                                               
	                                             
	float countabsolute;
	                                                                       
	                                                                     
	                                                                   
	float countmultiplier;
	                                                                         
	                                                                         
	float trailspacing;
	                                                               
	ptype_t particletype;
	                                           
	pblend_t blendmode;
	                                                                  
	porientation_t orientation;
	                                                                       
	                                 
	unsigned int color[2];
	                                                                         
	                                                                         
	                
	                                                                       
	int tex[2];
	                                                                                   
	float size[3];
	                                                                       
	float alpha[3];
	                                                                                  
	float time[2];
	                                                                     
	float gravity;
	                                                          
	                                                
	float bounce;
	                                     
	                                       
	float airfriction;
	                                                           
	                                       
	float liquidfriction;
	                                                                       
	                                                               
	                         
	float stretchfactor;
	                                            
	float originoffset[3];
	float relativeoriginoffset[3];
	float velocityoffset[3];
	float relativevelocityoffset[3];
	float originjitter[3];
	float velocityjitter[3];
	float velocitymultiplier;
	                                    
	float lightradiusstart;
	float lightradiusfade;
	float lighttime;
	float lightcolor[3];
	qboolean lightshadow;
	int lightcubemapnum;
	float lightcorona[2];
	unsigned int staincolor[2];                                                                                                                 
	int staintex[2];
	float stainalpha[2];
	float stainsize[2];
	                   
	float rotate[4];                                                  
}
particleeffectinfo_t;

char particleeffectname[MAX_PARTICLEEFFECTNAME][64];

int numparticleeffectinfo;
particleeffectinfo_t particleeffectinfo[MAX_PARTICLEEFFECTINFO];

static int particlepalette[256];
  
                                                                                
                                                                                 
                                                                                  
                                                                                  
                                                                                  
                                                                                  
                                                                                  
                                                                                  
                                                                                  
                                                                                  
                                                                                  
                                                                                  
                                                                                   
                                                                                    
                                                                                    
                                                                                    
                                                                                    
                                                                                    
                                                                                    
                                                                                    
                                                                                    
                                                                                    
                                                                                    
                                                                                    
                                                                                    
                                                                                    
                                                                                    
                                                                                    
                                                                                    
                                                                                    
                                                                                    
                                                                                    
  

int		ramp1[8] = {0x6f, 0x6d, 0x6b, 0x69, 0x67, 0x65, 0x63, 0x61};
int		ramp2[8] = {0x6f, 0x6e, 0x6d, 0x6c, 0x6b, 0x6a, 0x68, 0x66};
int		ramp3[8] = {0x6d, 0x6b, 6, 5, 4, 3};

                                                                                                                  

                                                              
typedef struct particletexture_s
{
	rtexture_t *texture;
	float s1, t1, s2, t2;
}
particletexture_t;

static rtexturepool_t *particletexturepool;
static rtexture_t *particlefonttexture;
static particletexture_t particletexture[MAX_PARTICLETEXTURES];
skinframe_t *decalskinframe;

                                   
static const int tex_smoke[8] = {0, 1, 2, 3, 4, 5, 6, 7};
static const int tex_bulletdecal[8] = {8, 9, 10, 11, 12, 13, 14, 15};
static const int tex_blooddecal[8] = {16, 17, 18, 19, 20, 21, 22, 23};
static const int tex_bloodparticle[8] = {24, 25, 26, 27, 28, 29, 30, 31};
static const int tex_rainsplash = 32;
static const int tex_particle = 63;
static const int tex_bubble = 62;
static const int tex_raindrop = 61;
static const int tex_beam = 60;

particleeffectinfo_t baselineparticleeffectinfo =
{
	0,                                                       
	                        
	0,             
	                                                                          
	                                                                        
	0.0,                              
	                                                                          
	                                                               
	                                             
	0.0f,                       
	                                                                       
	                                                                     
	                                                                   
	0.0f,                         
	                                                                         
	                                                                         
	0.0f,                      
	                                                               
	pt_alphastatic,                        
	                                           
	PBLEND_ALPHA,                      
	                                                                  
	PARTICLE_BILLBOARD,                              
	                                                                       
	                                 
	{0xFFFFFF, 0xFFFFFF},                         
	                                                                         
	                                                                         
	                
	                                                                       
	{63, 63                   },              
	                                                                                   
	{1, 1, 0.0f},                 
	                                                                       
	{0.0f, 256.0f, 256.0f},                  
	                                                                                  
	{16777216.0f, 16777216.0f},                 
	                                                                     
	0.0f,                 
	                                                          
	                                                
	0.0f,                
	                                     
	                                       
	0.0f,                     
	                                                           
	                                       
	0.0f,                        
	                                                                       
	                                                               
	                         
	1.0f,                       
	                                            
	{0.0f, 0.0f, 0.0f},                         
	{0.0f, 0.0f, 0.0f},                                 
	{0.0f, 0.0f, 0.0f},                           
	{0.0f, 0.0f, 0.0f},                                   
	{0.0f, 0.0f, 0.0f},                         
	{0.0f, 0.0f, 0.0f},                           
	0.0f,                            
	                                    
	0.0f,                          
	0.0f,                         
	16777216.0f,                   
	{1.0f, 1.0f, 1.0f},                       
	true,                        
	0,                       
	{1.0f, 0.25f},                        
	{(unsigned int)-1, (unsigned int)-1},                                                                                                                                               
	{-1, -1},                   
	{1.0f, 1.0f},                       
	{2.0f, 2.0f},                      
	                   
	{0.0f, 360.0f, 0.0f, 0.0f},                                                                     
};

cvar_t cl_particles = {CVAR_SAVE, "cl_particles", "1", "enables particle effects"};
cvar_t cl_particles_quality = {CVAR_SAVE, "cl_particles_quality", "1", "multiplies number of particles"};
cvar_t cl_particles_alpha = {CVAR_SAVE, "cl_particles_alpha", "1", "multiplies opacity of particles"};
cvar_t cl_particles_size = {CVAR_SAVE, "cl_particles_size", "1", "multiplies particle size"};
cvar_t cl_particles_quake = {CVAR_SAVE, "cl_particles_quake", "0", "makes particle effects look mostly like the ones in Quake"};
cvar_t cl_particles_blood = {CVAR_SAVE, "cl_particles_blood", "1", "enables blood effects"};
cvar_t cl_particles_blood_alpha = {CVAR_SAVE, "cl_particles_blood_alpha", "1", "opacity of blood, does not affect decals"};
cvar_t cl_particles_blood_decal_alpha = {CVAR_SAVE, "cl_particles_blood_decal_alpha", "1", "opacity of blood decal"};
cvar_t cl_particles_blood_decal_scalemin = {CVAR_SAVE, "cl_particles_blood_decal_scalemin", "1.5", "minimal random scale of decal"};
cvar_t cl_particles_blood_decal_scalemax = {CVAR_SAVE, "cl_particles_blood_decal_scalemax", "2", "maximal random scale of decal"};
cvar_t cl_particles_blood_bloodhack = {CVAR_SAVE, "cl_particles_blood_bloodhack", "1", "make certain quake particle() calls create blood effects instead"};
cvar_t cl_particles_bulletimpacts = {CVAR_SAVE, "cl_particles_bulletimpacts", "1", "enables bulletimpact effects"};
cvar_t cl_particles_explosions_sparks = {CVAR_SAVE, "cl_particles_explosions_sparks", "1", "enables sparks from explosions"};
cvar_t cl_particles_explosions_shell = {CVAR_SAVE, "cl_particles_explosions_shell", "0", "enables polygonal shell from explosions"};
cvar_t cl_particles_rain = {CVAR_SAVE, "cl_particles_rain", "1", "enables rain effects"};
cvar_t cl_particles_snow = {CVAR_SAVE, "cl_particles_snow", "1", "enables snow effects"};
cvar_t cl_particles_smoke = {CVAR_SAVE, "cl_particles_smoke", "1", "enables smoke (used by multiple effects)"};
cvar_t cl_particles_smoke_alpha = {CVAR_SAVE, "cl_particles_smoke_alpha", "0.5", "smoke brightness"};
cvar_t cl_particles_smoke_alphafade = {CVAR_SAVE, "cl_particles_smoke_alphafade", "0.55", "brightness fade per second"};
cvar_t cl_particles_sparks = {CVAR_SAVE, "cl_particles_sparks", "1", "enables sparks (used by multiple effects)"};
cvar_t cl_particles_bubbles = {CVAR_SAVE, "cl_particles_bubbles", "1", "enables bubbles (used by multiple effects)"};
cvar_t cl_particles_visculling = {CVAR_SAVE, "cl_particles_visculling", "0", "perform a costly check if each particle is visible before drawing"};
cvar_t cl_particles_collisions = {CVAR_SAVE, "cl_particles_collisions", "1", "allow costly collision detection on particles (sparks that bounce, particles not going through walls, blood hitting surfaces, etc)"};
cvar_t cl_particles_forcetraileffects = {0, "cl_particles_forcetraileffects", "0", "force trails to be displayed even if a non-trail draw primitive was used (debug/compat feature)"};
cvar_t cl_decals = {CVAR_SAVE, "cl_decals", "1", "enables decals (bullet holes, blood, etc)"};
cvar_t cl_decals_visculling = {CVAR_SAVE, "cl_decals_visculling", "1", "perform a very cheap check if each decal is visible before drawing"};
cvar_t cl_decals_time = {CVAR_SAVE, "cl_decals_time", "20", "how long before decals start to fade away"};
cvar_t cl_decals_fadetime = {CVAR_SAVE, "cl_decals_fadetime", "1", "how long decals take to fade away"};
cvar_t cl_decals_newsystem = {CVAR_SAVE, "cl_decals_newsystem", "1", "enables new advanced decal system"};
cvar_t cl_decals_newsystem_intensitymultiplier = {CVAR_SAVE, "cl_decals_newsystem_intensitymultiplier", "2", "boosts intensity of decals (because the distance fade can make them hard to see otherwise)"};
cvar_t cl_decals_newsystem_immediatebloodstain = {CVAR_SAVE, "cl_decals_newsystem_immediatebloodstain", "2", "0: no on-spawn blood stains; 1: on-spawn blood stains for pt_blood; 2: always use on-spawn blood stains"};
cvar_t cl_decals_newsystem_bloodsmears = {CVAR_SAVE, "cl_decals_newsystem_bloodsmears", "1", "enable use of particle velocity as decal projection direction rather than surface normal"};
cvar_t cl_decals_models = {CVAR_SAVE, "cl_decals_models", "0", "enables decals on animated models (if newsystem is also 1)"};
cvar_t cl_decals_bias = {CVAR_SAVE, "cl_decals_bias", "0.125", "distance to bias decals from surface to prevent depth fighting"};
cvar_t cl_decals_max = {CVAR_SAVE, "cl_decals_max", "4096", "maximum number of decals allowed to exist in the world at once"};


static void CL_Particles_ParseEffectInfo(const char *textstart, const char *textend, const char *filename)
{
	int arrayindex;
	int argc;
	int i;
	int linenumber;
	particleeffectinfo_t *info = NULL;
	const char *text = textstart;
	char argv[16][1024];
	for (linenumber = 1;;linenumber++)
	{
		argc = 0;
		for (arrayindex = 0;arrayindex < 16;arrayindex++)
			argv[arrayindex][0] = 0;
		for (;;)
		{
			if (!COM_ParseToken_Simple(&text, true, false, true))
				return;
			if (!strcmp(com_token, "\n"))
				break;
			if (argc < 16)
			{
				strlcpy(argv[argc], com_token, sizeof(argv[argc]));
				argc++;
			}
		}
		if (argc < 1)
			continue;
#define checkparms(n) if (argc != (n)) {Con_Printf("%s:%i: error while parsing: %s given %i parameters, should be %i parameters\n", filename, linenumber, argv[0], argc, (n));break;}
#define readints(array, n) checkparms(n+1);for (arrayindex = 0;arrayindex < argc - 1;arrayindex++) array[arrayindex] = strtol(argv[1+arrayindex], NULL, 0)
#define readfloats(array, n) checkparms(n+1);for (arrayindex = 0;arrayindex < argc - 1;arrayindex++) array[arrayindex] = atof(argv[1+arrayindex])
#define readint(var) checkparms(2);var = strtol(argv[1], NULL, 0)
#define readfloat(var) checkparms(2);var = atof(argv[1])
#define readbool(var) checkparms(2);var = strtol(argv[1], NULL, 0) != 0
		if (!strcmp(argv[0], "effect"))
		{
			int effectnameindex;
			checkparms(2);
			if (numparticleeffectinfo >= MAX_PARTICLEEFFECTINFO)
			{
				Con_Printf("%s:%i: too many effects!\n", filename, linenumber);
				break;
			}
			for (effectnameindex = 1;effectnameindex < MAX_PARTICLEEFFECTNAME;effectnameindex++)
			{
				if (particleeffectname[effectnameindex][0])
				{
					if (!strcmp(particleeffectname[effectnameindex], argv[1]))
						break;
				}
				else
				{
					strlcpy(particleeffectname[effectnameindex], argv[1], sizeof(particleeffectname[effectnameindex]));
					break;
				}
			}
			                                
			if (effectnameindex == MAX_PARTICLEEFFECTNAME)
			{
				Con_Printf("%s:%i: too many effects!\n", filename, linenumber);
				break;
			}
			for(i = 0; i < numparticleeffectinfo; ++i)
			{
				info = particleeffectinfo + i;
				if(!(info->flags & PARTICLEEFFECT_DEFINED))
					if(info->effectnameindex == effectnameindex)
						break;
			}
			if(i < numparticleeffectinfo)
				continue;
			info = particleeffectinfo + numparticleeffectinfo++;
			                                                            
			*info = baselineparticleeffectinfo;
			info->effectnameindex = effectnameindex;
			continue;
		}
		else if (info == NULL)
		{
			Con_Printf("%s:%i: command %s encountered before effect\n", filename, linenumber, argv[0]);
			break;
		}

		info->flags |= PARTICLEEFFECT_DEFINED;
		if (!strcmp(argv[0], "countabsolute")) {readfloat(info->countabsolute);}
		else if (!strcmp(argv[0], "count")) {readfloat(info->countmultiplier);}
		else if (!strcmp(argv[0], "type"))
		{
			checkparms(2);
			if (!strcmp(argv[1], "alphastatic")) info->particletype = pt_alphastatic;
			else if (!strcmp(argv[1], "static")) info->particletype = pt_static;
			else if (!strcmp(argv[1], "spark")) info->particletype = pt_spark;
			else if (!strcmp(argv[1], "beam")) info->particletype = pt_beam;
			else if (!strcmp(argv[1], "rain")) info->particletype = pt_rain;
			else if (!strcmp(argv[1], "raindecal")) info->particletype = pt_raindecal;
			else if (!strcmp(argv[1], "snow")) info->particletype = pt_snow;
			else if (!strcmp(argv[1], "bubble")) info->particletype = pt_bubble;
			else if (!strcmp(argv[1], "blood")) {info->particletype = pt_blood;info->gravity = 1;}
			else if (!strcmp(argv[1], "smoke")) info->particletype = pt_smoke;
			else if (!strcmp(argv[1], "decal")) info->particletype = pt_decal;
			else if (!strcmp(argv[1], "entityparticle")) info->particletype = pt_entityparticle;
			else Con_Printf("%s:%i: unrecognized particle type %s\n", filename, linenumber, argv[1]);
			info->blendmode = particletype[info->particletype].blendmode;
			info->orientation = particletype[info->particletype].orientation;
		}
		else if (!strcmp(argv[0], "blend"))
		{
			checkparms(2);
			if (!strcmp(argv[1], "alpha")) info->blendmode = PBLEND_ALPHA;
			else if (!strcmp(argv[1], "add")) info->blendmode = PBLEND_ADD;
			else if (!strcmp(argv[1], "invmod")) info->blendmode = PBLEND_INVMOD;
			else Con_Printf("%s:%i: unrecognized blendmode %s\n", filename, linenumber, argv[1]);
		}
		else if (!strcmp(argv[0], "orientation"))
		{
			checkparms(2);
			if (!strcmp(argv[1], "billboard")) info->orientation = PARTICLE_BILLBOARD;
			else if (!strcmp(argv[1], "spark")) info->orientation = PARTICLE_SPARK;
			else if (!strcmp(argv[1], "oriented")) info->orientation = PARTICLE_ORIENTED_DOUBLESIDED;
			else if (!strcmp(argv[1], "beam")) info->orientation = PARTICLE_HBEAM;
			else Con_Printf("%s:%i: unrecognized orientation %s\n", filename, linenumber, argv[1]);
		}
		else if (!strcmp(argv[0], "color")) {readints(info->color, 2);}
		else if (!strcmp(argv[0], "tex")) {readints(info->tex, 2);}
		else if (!strcmp(argv[0], "size")) {readfloats(info->size, 2);}
		else if (!strcmp(argv[0], "sizeincrease")) {readfloat(info->size[2]);}
		else if (!strcmp(argv[0], "alpha")) {readfloats(info->alpha, 3);}
		else if (!strcmp(argv[0], "time")) {readfloats(info->time, 2);}
		else if (!strcmp(argv[0], "gravity")) {readfloat(info->gravity);}
		else if (!strcmp(argv[0], "bounce")) {readfloat(info->bounce);}
		else if (!strcmp(argv[0], "airfriction")) {readfloat(info->airfriction);}
		else if (!strcmp(argv[0], "liquidfriction")) {readfloat(info->liquidfriction);}
		else if (!strcmp(argv[0], "originoffset")) {readfloats(info->originoffset, 3);}
		else if (!strcmp(argv[0], "relativeoriginoffset")) {readfloats(info->relativeoriginoffset, 3);}
		else if (!strcmp(argv[0], "velocityoffset")) {readfloats(info->velocityoffset, 3);}
		else if (!strcmp(argv[0], "relativevelocityoffset")) {readfloats(info->relativevelocityoffset, 3);}
		else if (!strcmp(argv[0], "originjitter")) {readfloats(info->originjitter, 3);}
		else if (!strcmp(argv[0], "velocityjitter")) {readfloats(info->velocityjitter, 3);}
		else if (!strcmp(argv[0], "velocitymultiplier")) {readfloat(info->velocitymultiplier);}
		else if (!strcmp(argv[0], "lightradius")) {readfloat(info->lightradiusstart);}
		else if (!strcmp(argv[0], "lightradiusfade")) {readfloat(info->lightradiusfade);}
		else if (!strcmp(argv[0], "lighttime")) {readfloat(info->lighttime);}
		else if (!strcmp(argv[0], "lightcolor")) {readfloats(info->lightcolor, 3);}
		else if (!strcmp(argv[0], "lightshadow")) {readbool(info->lightshadow);}
		else if (!strcmp(argv[0], "lightcubemapnum")) {readint(info->lightcubemapnum);}
		else if (!strcmp(argv[0], "lightcorona")) {readints(info->lightcorona, 2);}
		else if (!strcmp(argv[0], "underwater")) {checkparms(1);info->flags |= PARTICLEEFFECT_UNDERWATER;}
		else if (!strcmp(argv[0], "notunderwater")) {checkparms(1);info->flags |= PARTICLEEFFECT_NOTUNDERWATER;}
		else if (!strcmp(argv[0], "trailspacing")) {readfloat(info->trailspacing);if (info->trailspacing > 0) info->countmultiplier = 1.0f / info->trailspacing;}
		else if (!strcmp(argv[0], "stretchfactor")) {readfloat(info->stretchfactor);}
		else if (!strcmp(argv[0], "staincolor")) {readints(info->staincolor, 2);}
		else if (!strcmp(argv[0], "stainalpha")) {readfloats(info->stainalpha, 2);}
		else if (!strcmp(argv[0], "stainsize")) {readfloats(info->stainsize, 2);}
		else if (!strcmp(argv[0], "staintex")) {readints(info->staintex, 2);}
		else if (!strcmp(argv[0], "stainless")) {info->staintex[0] = -2; info->staincolor[0] = (unsigned int)-1; info->staincolor[1] = (unsigned int)-1; info->stainalpha[0] = 1; info->stainalpha[1] = 1; info->stainsize[0] = 2; info->stainsize[1] = 2; }
		else if (!strcmp(argv[0], "rotate")) {readfloats(info->rotate, 4);}
		else
			Con_Printf("%s:%i: skipping unknown command %s\n", filename, linenumber, argv[0]);
#undef checkparms
#undef readints
#undef readfloats
#undef readint
#undef readfloat
	}
}

int CL_ParticleEffectIndexForName(const char *name)
{
	int i;
	for (i = 1;i < MAX_PARTICLEEFFECTNAME && particleeffectname[i][0];i++)
		if (!strcmp(particleeffectname[i], name))
			return i;
	return 0;
}

const char *CL_ParticleEffectNameForIndex(int i)
{
	if (i < 1 || i >= MAX_PARTICLEEFFECTNAME)
		return NULL;
	return particleeffectname[i];
}

                                           
static const char *standardeffectnames[EFFECT_TOTAL] =
{
	"",
	"TE_GUNSHOT",
	"TE_GUNSHOTQUAD",
	"TE_SPIKE",
	"TE_SPIKEQUAD",
	"TE_SUPERSPIKE",
	"TE_SUPERSPIKEQUAD",
	"TE_WIZSPIKE",
	"TE_KNIGHTSPIKE",
	"TE_EXPLOSION",
	"TE_EXPLOSIONQUAD",
	"TE_TAREXPLOSION",
	"TE_TELEPORT",
	"TE_LAVASPLASH",
	"TE_SMALLFLASH",
	"TE_FLAMEJET",
	"EF_FLAME",
	"TE_BLOOD",
	"TE_SPARK",
	"TE_PLASMABURN",
	"TE_TEI_G3",
	"TE_TEI_SMOKE",
	"TE_TEI_BIGEXPLOSION",
	"TE_TEI_PLASMAHIT",
	"EF_STARDUST",
	"TR_ROCKET",
	"TR_GRENADE",
	"TR_BLOOD",
	"TR_WIZSPIKE",
	"TR_SLIGHTBLOOD",
	"TR_KNIGHTSPIKE",
	"TR_VORESPIKE",
	"TR_NEHAHRASMOKE",
	"TR_NEXUIZPLASMA",
	"TR_GLOWTRAIL",
	"SVC_PARTICLE"
};

static void CL_Particles_LoadEffectInfo(const char *customfile)
{
	int i;
	int filepass;
	unsigned char *filedata;
	fs_offset_t filesize;
	char filename[MAX_QPATH];
	numparticleeffectinfo = 0;
	memset(particleeffectinfo, 0, sizeof(particleeffectinfo));
	memset(particleeffectname, 0, sizeof(particleeffectname));
	for (i = 0;i < EFFECT_TOTAL;i++)
		strlcpy(particleeffectname[i], standardeffectnames[i], sizeof(particleeffectname[i]));
	for (filepass = 0;;filepass++)
	{
		if (filepass == 0)
		{
			if (customfile)
				strlcpy(filename, customfile, sizeof(filename));
			else
				strlcpy(filename, "effectinfo.txt", sizeof(filename));
		}
		else if (filepass == 1)
		{
			if (!cl.worldbasename[0] || customfile)
				continue;
			dpsnprintf(filename, sizeof(filename), "%s_effectinfo.txt", cl.worldnamenoextension);
		}
		else
			break;
		filedata = FS_LoadFile(filename, tempmempool, true, &filesize);
		if (!filedata)
			continue;
		CL_Particles_ParseEffectInfo((const char *)filedata, (const char *)filedata + filesize, filename);
		Mem_Free(filedata);
	}
}

static void CL_Particles_LoadEffectInfo_f(void)
{
	CL_Particles_LoadEffectInfo(Cmd_Argc() > 1 ? Cmd_Argv(1) : NULL);
}

  
               
                
               
  
void CL_ReadPointFile_f (void);
void CL_Particles_Init (void)
{
	Cmd_AddCommand ("pointfile", CL_ReadPointFile_f, "display point file produced by qbsp when a leak was detected in the map (a line leading through the leak hole, to an entity inside the level)");
	Cmd_AddCommand ("cl_particles_reloadeffects", CL_Particles_LoadEffectInfo_f, "reloads effectinfo.txt and maps/levelname_effectinfo.txt (where levelname is the current map) if parameter is given, loads from custom file (no levelname_effectinfo are loaded in this case)");

	Cvar_RegisterVariable (&cl_particles);
	Cvar_RegisterVariable (&cl_particles_quality);
	Cvar_RegisterVariable (&cl_particles_alpha);
	Cvar_RegisterVariable (&cl_particles_size);
	Cvar_RegisterVariable (&cl_particles_quake);
	Cvar_RegisterVariable (&cl_particles_blood);
	Cvar_RegisterVariable (&cl_particles_blood_alpha);
	Cvar_RegisterVariable (&cl_particles_blood_decal_alpha);
	Cvar_RegisterVariable (&cl_particles_blood_decal_scalemin);
	Cvar_RegisterVariable (&cl_particles_blood_decal_scalemax);
	Cvar_RegisterVariable (&cl_particles_blood_bloodhack);
	Cvar_RegisterVariable (&cl_particles_explosions_sparks);
	Cvar_RegisterVariable (&cl_particles_explosions_shell);
	Cvar_RegisterVariable (&cl_particles_bulletimpacts);
	Cvar_RegisterVariable (&cl_particles_rain);
	Cvar_RegisterVariable (&cl_particles_snow);
	Cvar_RegisterVariable (&cl_particles_smoke);
	Cvar_RegisterVariable (&cl_particles_smoke_alpha);
	Cvar_RegisterVariable (&cl_particles_smoke_alphafade);
	Cvar_RegisterVariable (&cl_particles_sparks);
	Cvar_RegisterVariable (&cl_particles_bubbles);
	Cvar_RegisterVariable (&cl_particles_visculling);
	Cvar_RegisterVariable (&cl_particles_collisions);
	Cvar_RegisterVariable (&cl_particles_forcetraileffects);
	Cvar_RegisterVariable (&cl_decals);
	Cvar_RegisterVariable (&cl_decals_visculling);
	Cvar_RegisterVariable (&cl_decals_time);
	Cvar_RegisterVariable (&cl_decals_fadetime);
	Cvar_RegisterVariable (&cl_decals_newsystem);
	Cvar_RegisterVariable (&cl_decals_newsystem_intensitymultiplier);
	Cvar_RegisterVariable (&cl_decals_newsystem_immediatebloodstain);
	Cvar_RegisterVariable (&cl_decals_newsystem_bloodsmears);
	Cvar_RegisterVariable (&cl_decals_models);
	Cvar_RegisterVariable (&cl_decals_bias);
	Cvar_RegisterVariable (&cl_decals_max);
}

void CL_Particles_Shutdown (void)
{
}

void CL_SpawnDecalParticleForSurface(int hitent, const vec3_t org, const vec3_t normal, int color1, int color2, int texnum, float size, float alpha);
void CL_SpawnDecalParticleForPoint(const vec3_t org, float maxdist, float size, float alpha, int texnum, int color1, int color2);

                             
                                                                                                       
                                                                                                        
                                                                            
                                                                                
                                                               
                                                                                                                  
                                                                                             
                                                               
                                                                                                                                                               
                                         
                                              
                                                                                                      
                                        
                                            
                                                                                                                                    
                                                                                                
                                                       
                                                    
                                                                         
                                                                         
particle_t *CL_NewParticle(const vec3_t sortorigin, unsigned short ptypeindex, int pcolor1, int pcolor2, int ptex, float psize, float psizeincrease, float palpha, float palphafade, float pgravity, float pbounce, float px, float py, float pz, float pvx, float pvy, float pvz, float pairfriction, float pliquidfriction, float originjitter, float velocityjitter, qboolean pqualityreduction, float lifetime, float stretch, pblend_t blendmode, porientation_t orientation, int staincolor1, int staincolor2, int staintex, float stainalpha, float stainsize, float angle, float spin, float tint[4])
{
	int l1, l2, r, g, b;
	particle_t *part;
	vec3_t v;
	if (!cl_particles.integer)
		return NULL;
	for (;cl.free_particle < cl.max_particles && cl.particles[cl.free_particle].typeindex;cl.free_particle++);
	if (cl.free_particle >= cl.max_particles)
		return NULL;
	if (!lifetime)
		lifetime = palpha / min(1, palphafade);
	part = &cl.particles[cl.free_particle++];
	if (cl.num_particles < cl.free_particle)
		cl.num_particles = cl.free_particle;
	memset(part, 0, sizeof(*part));
	VectorCopy(sortorigin, part->sortorigin);
	part->typeindex = ptypeindex;
	part->blendmode = blendmode;
	if(orientation == PARTICLE_HBEAM || orientation == PARTICLE_VBEAM)
	{
		particletexture_t *tex = &particletexture[ptex];
		if(tex->t1 == 0 && tex->t2 == 1)                           
			part->orientation = PARTICLE_VBEAM;
		else
			part->orientation = PARTICLE_HBEAM;
	}
	else
		part->orientation = orientation;
	l2 = (int)lhrandom(0.5, 256.5);
	l1 = 256 - l2;
	part->color[0] = ((((pcolor1 >> 16) & 0xFF) * l1 + ((pcolor2 >> 16) & 0xFF) * l2) >> 8) & 0xFF;
	part->color[1] = ((((pcolor1 >>  8) & 0xFF) * l1 + ((pcolor2 >>  8) & 0xFF) * l2) >> 8) & 0xFF;
	part->color[2] = ((((pcolor1 >>  0) & 0xFF) * l1 + ((pcolor2 >>  0) & 0xFF) * l2) >> 8) & 0xFF;
	if (vid.sRGB3D)
	{
		part->color[0] = (unsigned char)floor(Image_LinearFloatFromsRGB(part->color[0]) * 255.0f + 0.5f);
		part->color[1] = (unsigned char)floor(Image_LinearFloatFromsRGB(part->color[1]) * 255.0f + 0.5f);
		part->color[2] = (unsigned char)floor(Image_LinearFloatFromsRGB(part->color[2]) * 255.0f + 0.5f);
	}
	part->alpha = palpha;
	part->alphafade = palphafade;
	part->staintexnum = staintex;
	if(staincolor1 >= 0 && staincolor2 >= 0)
	{
		l2 = (int)lhrandom(0.5, 256.5);
		l1 = 256 - l2;
		if(blendmode == PBLEND_INVMOD)
		{
			r = ((((staincolor1 >> 16) & 0xFF) * l1 + ((staincolor2 >> 16) & 0xFF) * l2) * (255 - part->color[0])) / 0x8000;                                             
			g = ((((staincolor1 >>  8) & 0xFF) * l1 + ((staincolor2 >>  8) & 0xFF) * l2) * (255 - part->color[1])) / 0x8000;
			b = ((((staincolor1 >>  0) & 0xFF) * l1 + ((staincolor2 >>  0) & 0xFF) * l2) * (255 - part->color[2])) / 0x8000;
		}
		else
		{
			r = ((((staincolor1 >> 16) & 0xFF) * l1 + ((staincolor2 >> 16) & 0xFF) * l2) * part->color[0]) / 0x8000;                                             
			g = ((((staincolor1 >>  8) & 0xFF) * l1 + ((staincolor2 >>  8) & 0xFF) * l2) * part->color[1]) / 0x8000;
			b = ((((staincolor1 >>  0) & 0xFF) * l1 + ((staincolor2 >>  0) & 0xFF) * l2) * part->color[2]) / 0x8000;
		}
		if(r > 0xFF) r = 0xFF;
		if(g > 0xFF) g = 0xFF;
		if(b > 0xFF) b = 0xFF;
	}
	else
	{
		r = part->color[0];                                              
		g = part->color[1];
		b = part->color[2];
	}
	part->staincolor[0] = r;
	part->staincolor[1] = g;
	part->staincolor[2] = b;
	part->stainalpha = palpha * stainalpha;
	part->stainsize = psize * stainsize;
	if(tint)
	{
		if(blendmode != PBLEND_INVMOD)                               
		{
			part->color[0] *= tint[0];
			part->color[1] *= tint[1];
			part->color[2] *= tint[2];
		}
		part->alpha *= tint[3];
		part->alphafade *= tint[3];
		part->stainalpha *= tint[3];
	}
	part->texnum = ptex;
	part->size = psize;
	part->sizeincrease = psizeincrease;
	part->gravity = pgravity;
	part->bounce = pbounce;
	part->stretch = stretch;
	VectorRandom(v);
	part->org[0] = px + originjitter * v[0];
	part->org[1] = py + originjitter * v[1];
	part->org[2] = pz + originjitter * v[2];
	part->vel[0] = pvx + velocityjitter * v[0];
	part->vel[1] = pvy + velocityjitter * v[1];
	part->vel[2] = pvz + velocityjitter * v[2];
	part->time2 = 0;
	part->airfriction = pairfriction;
	part->liquidfriction = pliquidfriction;
	part->die = cl.time + lifetime;
	part->delayedspawn = cl.time;
                               
	part->qualityreduction = pqualityreduction;
	part->angle = angle;
	part->spin = spin;
	                                                                                                                                   
	if (part->typeindex == pt_rain)
	{
		int i;
		particle_t *part2;
		vec3_t endvec;
		trace_t trace;
		                                                                        
		part->typeindex = pt_spark;
		part->bounce = 0;
		VectorMA(part->org, lifetime, part->vel, endvec);
		trace = CL_TraceLine(part->org, endvec, MOVE_NOMONSTERS, NULL, SUPERCONTENTS_SOLID | SUPERCONTENTS_LIQUIDSMASK, 0, 0, collision_extendmovelength.value, true, false, NULL, false, false);
		part->die = cl.time + lifetime * trace.fraction;
		part2 = CL_NewParticle(endvec, pt_raindecal, pcolor1, pcolor2, tex_rainsplash, part->size, part->size * 20, part->alpha, part->alpha / 0.4, 0, 0, trace.endpos[0] + trace.plane.normal[0], trace.endpos[1] + trace.plane.normal[1], trace.endpos[2] + trace.plane.normal[2], trace.plane.normal[0], trace.plane.normal[1], trace.plane.normal[2], 0, 0, 0, 0, pqualityreduction, 0, 1, PBLEND_ADD, PARTICLE_ORIENTED_DOUBLESIDED, -1, -1, -1, 1, 1, 0, 0, NULL);
		if (part2)
		{
			part2->delayedspawn = part->die;
			part2->die += part->die - cl.time;
			for (i = rand() & 7;i < 10;i++)
			{
				part2 = CL_NewParticle(endvec, pt_spark, pcolor1, pcolor2, tex_particle, 0.25f, 0, part->alpha * 2, part->alpha * 4, 1, 0, trace.endpos[0] + trace.plane.normal[0], trace.endpos[1] + trace.plane.normal[1], trace.endpos[2] + trace.plane.normal[2], trace.plane.normal[0] * 16, trace.plane.normal[1] * 16, trace.plane.normal[2] * 16 + cl.movevars_gravity * 0.04, 0, 0, 0, 32, pqualityreduction, 0, 1, PBLEND_ADD, PARTICLE_SPARK, -1, -1, -1, 1, 1, 0, 0, NULL);
				if (part2)
				{
					part2->delayedspawn = part->die;
					part2->die += part->die - cl.time;
				}
			}
		}
	}
#if 0
	else if (part->bounce != 0 && part->gravity == 0 && part->typeindex != pt_snow)
	{
		float lifetime = part->alpha / (part->alphafade ? part->alphafade : 1);
		vec3_t endvec;
		trace_t trace;
		VectorMA(part->org, lifetime, part->vel, endvec);
		trace = CL_TraceLine(part->org, endvec, MOVE_NOMONSTERS, NULL, SUPERCONTENTS_SOLID | SUPERCONTENTS_BODY, true, false, NULL, false);
		part->delayedcollisions = cl.time + lifetime * trace.fraction - 0.1;
	}
#endif

	return part;
}

static void CL_ImmediateBloodStain(particle_t *part)
{
	vec3_t v;
	int staintex;

	                                                                                                      
	if (part->staintexnum >= 0 && cl_decals_newsystem.integer && cl_decals.integer)
	{
		VectorCopy(part->vel, v);
		VectorNormalize(v);
		staintex = part->staintexnum;
		R_DecalSystem_SplatEntities(part->org, v, 1-part->staincolor[0]*(1.0f/255.0f), 1-part->staincolor[1]*(1.0f/255.0f), 1-part->staincolor[2]*(1.0f/255.0f), part->stainalpha*(1.0f/255.0f), particletexture[staintex].s1, particletexture[staintex].t1, particletexture[staintex].s2, particletexture[staintex].t2, part->stainsize);
	}

	                                                                                                      
	if (part->typeindex == pt_blood && cl_decals_newsystem.integer && cl_decals.integer)
	{
		VectorCopy(part->vel, v);
		VectorNormalize(v);
		staintex = tex_blooddecal[rand()&7];
		R_DecalSystem_SplatEntities(part->org, v, part->color[0]*(1.0f/255.0f), part->color[1]*(1.0f/255.0f), part->color[2]*(1.0f/255.0f), part->alpha*(1.0f/255.0f), particletexture[staintex].s1, particletexture[staintex].t1, particletexture[staintex].s2, particletexture[staintex].t2, part->size * 2);
	}
}

void CL_SpawnDecalParticleForSurface(int hitent, const vec3_t org, const vec3_t normal, int color1, int color2, int texnum, float size, float alpha)
{
	int l1, l2;
	decal_t *decal;
	entity_render_t *ent = &cl.entities[hitent].render;
	unsigned char color[3];
	if (!cl_decals.integer)
		return;
	if (!ent->allowdecals)
		return;

	l2 = (int)lhrandom(0.5, 256.5);
	l1 = 256 - l2;
	color[0] = ((((color1 >> 16) & 0xFF) * l1 + ((color2 >> 16) & 0xFF) * l2) >> 8) & 0xFF;
	color[1] = ((((color1 >>  8) & 0xFF) * l1 + ((color2 >>  8) & 0xFF) * l2) >> 8) & 0xFF;
	color[2] = ((((color1 >>  0) & 0xFF) * l1 + ((color2 >>  0) & 0xFF) * l2) >> 8) & 0xFF;

	if (cl_decals_newsystem.integer)
	{
		if (vid.sRGB3D)
			R_DecalSystem_SplatEntities(org, normal, Image_LinearFloatFromsRGB(color[0]), Image_LinearFloatFromsRGB(color[1]), Image_LinearFloatFromsRGB(color[2]), alpha*(1.0f/255.0f), particletexture[texnum].s1, particletexture[texnum].t1, particletexture[texnum].s2, particletexture[texnum].t2, size);
		else
			R_DecalSystem_SplatEntities(org, normal, color[0]*(1.0f/255.0f), color[1]*(1.0f/255.0f), color[2]*(1.0f/255.0f), alpha*(1.0f/255.0f), particletexture[texnum].s1, particletexture[texnum].t1, particletexture[texnum].s2, particletexture[texnum].t2, size);
		return;
	}

	for (;cl.free_decal < cl.max_decals && cl.decals[cl.free_decal].typeindex;cl.free_decal++);
	if (cl.free_decal >= cl.max_decals)
		return;
	decal = &cl.decals[cl.free_decal++];
	if (cl.num_decals < cl.free_decal)
		cl.num_decals = cl.free_decal;
	memset(decal, 0, sizeof(*decal));
	decal->decalsequence = cl.decalsequence++;
	decal->typeindex = pt_decal;
	decal->texnum = texnum;
	VectorMA(org, cl_decals_bias.value, normal, decal->org);
	VectorCopy(normal, decal->normal);
	decal->size = size;
	decal->alpha = alpha;
	decal->time2 = cl.time;
	decal->color[0] = color[0];
	decal->color[1] = color[1];
	decal->color[2] = color[2];
	if (vid.sRGB3D)
	{
		decal->color[0] = (unsigned char)(Image_LinearFloatFromsRGB(decal->color[0]) * 256.0f);
		decal->color[1] = (unsigned char)(Image_LinearFloatFromsRGB(decal->color[1]) * 256.0f);
		decal->color[2] = (unsigned char)(Image_LinearFloatFromsRGB(decal->color[2]) * 256.0f);
	}
	decal->owner = hitent;
	decal->clusterindex = -1000;                                    
	if (hitent)
	{
		                                                                                                       
		decal->ownermodel = cl.entities[decal->owner].render.model;
		Matrix4x4_Transform(&cl.entities[decal->owner].render.inversematrix, org, decal->relativeorigin);
		Matrix4x4_Transform3x3(&cl.entities[decal->owner].render.inversematrix, normal, decal->relativenormal);
	}
	else
	{
		if(r_refdef.scene.worldmodel && r_refdef.scene.worldmodel->brush.PointInLeaf)
		{
			mleaf_t *leaf = r_refdef.scene.worldmodel->brush.PointInLeaf(r_refdef.scene.worldmodel, decal->org);
			if(leaf)
				decal->clusterindex = leaf->clusterindex;
		}
	}
}

void CL_SpawnDecalParticleForPoint(const vec3_t org, float maxdist, float size, float alpha, int texnum, int color1, int color2)
{
	int i;
	vec_t bestfrac;
	vec3_t bestorg;
	vec3_t bestnormal;
	vec3_t org2;
	int besthitent = 0, hitent;
	trace_t trace;
	bestfrac = 10;
	for (i = 0;i < 32;i++)
	{
		VectorRandom(org2);
		VectorMA(org, maxdist, org2, org2);
		trace = CL_TraceLine(org, org2, MOVE_NOMONSTERS, NULL, SUPERCONTENTS_SOLID | SUPERCONTENTS_SKY, 0, 0, collision_extendmovelength.value, true, false, &hitent, false, true);
		                                                                      
		                            
		if (bestfrac > trace.fraction && !(trace.hitq3surfaceflags & Q3SURFACEFLAG_NOMARKS))
		{
			bestfrac = trace.fraction;
			besthitent = hitent;
			VectorCopy(trace.endpos, bestorg);
			VectorCopy(trace.plane.normal, bestnormal);
		}
	}
	if (bestfrac < 1)
		CL_SpawnDecalParticleForSurface(besthitent, bestorg, bestnormal, color1, color2, texnum, size, alpha);
}

static void CL_Sparks(const vec3_t originmins, const vec3_t originmaxs, const vec3_t velocitymins, const vec3_t velocitymaxs, float sparkcount);
static void CL_Smoke(const vec3_t originmins, const vec3_t originmaxs, const vec3_t velocitymins, const vec3_t velocitymaxs, float smokecount);
static void CL_NewParticlesFromEffectinfo(int effectnameindex, float pcount, const vec3_t originmins, const vec3_t originmaxs, const vec3_t velocitymins, const vec3_t velocitymaxs, entity_t *ent, int palettecolor, qboolean spawndlight, qboolean spawnparticles, float tintmins[4], float tintmaxs[4], float fade, qboolean wanttrail);
static void CL_ParticleEffect_Fallback(int effectnameindex, float count, const vec3_t originmins, const vec3_t originmaxs, const vec3_t velocitymins, const vec3_t velocitymaxs, entity_t *ent, int palettecolor, qboolean spawndlight, qboolean spawnparticles, qboolean wanttrail)
{
	vec3_t center;
	matrix4x4_t lightmatrix;
	particle_t *part;

	VectorLerp(originmins, 0.5, originmaxs, center);
	Matrix4x4_CreateTranslate(&lightmatrix, center[0], center[1], center[2]);
	if (effectnameindex == EFFECT_SVC_PARTICLE)
	{
		if (cl_particles.integer)
		{
			                                                                                                                     
			if (count == 1024)
				CL_NewParticlesFromEffectinfo(EFFECT_TE_EXPLOSION, 1, originmins, originmaxs, velocitymins, velocitymaxs, NULL, 0, spawndlight, spawnparticles, NULL, NULL, 1, wanttrail);
			else if (cl_particles_blood_bloodhack.integer && !cl_particles_quake.integer && (palettecolor == 73 || palettecolor == 225))
				CL_NewParticlesFromEffectinfo(EFFECT_TE_BLOOD, count / 2.0f, originmins, originmaxs, velocitymins, velocitymaxs, NULL, 0, spawndlight, spawnparticles, NULL, NULL, 1, wanttrail);
			else
			{
				count *= cl_particles_quality.value;
				for (;count > 0;count--)
				{
					int k = particlepalette[(palettecolor & ~7) + (rand()&7)];
					CL_NewParticle(center, pt_alphastatic, k, k, tex_particle, 1.5, 0, 255, 0, 0.05, 0, lhrandom(originmins[0], originmaxs[0]), lhrandom(originmins[1], originmaxs[1]), lhrandom(originmins[2], originmaxs[2]), lhrandom(velocitymins[0], velocitymaxs[0]), lhrandom(velocitymins[1], velocitymaxs[1]), lhrandom(velocitymins[2], velocitymaxs[2]), 0, 0, 8, 0, true, lhrandom(0.1, 0.5), 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
				}
			}
		}
	}
	else if (effectnameindex == EFFECT_TE_WIZSPIKE)
		CL_NewParticlesFromEffectinfo(EFFECT_SVC_PARTICLE, 30*count, originmins, originmaxs, velocitymins, velocitymaxs, NULL, 20, spawndlight, spawnparticles, NULL, NULL, 1, wanttrail);
	else if (effectnameindex == EFFECT_TE_KNIGHTSPIKE)
		CL_NewParticlesFromEffectinfo(EFFECT_SVC_PARTICLE, 20*count, originmins, originmaxs, velocitymins, velocitymaxs, NULL, 226, spawndlight, spawnparticles, NULL, NULL, 1, wanttrail);
	else if (effectnameindex == EFFECT_TE_SPIKE)
	{
		if (cl_particles_bulletimpacts.integer)
		{
			if (cl_particles_quake.integer)
			{
				if (cl_particles_smoke.integer)
					CL_NewParticlesFromEffectinfo(EFFECT_SVC_PARTICLE, 10*count, originmins, originmaxs, velocitymins, velocitymaxs, NULL, 0, spawndlight, spawnparticles, NULL, NULL, 1, wanttrail);
			}
			else
			{
				CL_Smoke(originmins, originmaxs, velocitymins, velocitymaxs, 4*count);
				CL_Sparks(originmins, originmaxs, velocitymins, velocitymaxs, 15*count);
				CL_NewParticle(center, pt_static, 0x808080,0x808080, tex_particle, 3, 0, 256, 512, 0, 0, lhrandom(originmins[0], originmaxs[0]), lhrandom(originmins[1], originmaxs[1]), lhrandom(originmins[2], originmaxs[2]), 0, 0, 0, 0, 0, 0, 0, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
			}
		}
		              
		R_Stain(center, 16, 40, 40, 40, 64, 88, 88, 88, 64);
		CL_SpawnDecalParticleForPoint(center, 6, 3, 255, tex_bulletdecal[rand()&7], 0xFFFFFF, 0xFFFFFF);
	}
	else if (effectnameindex == EFFECT_TE_SPIKEQUAD)
	{
		if (cl_particles_bulletimpacts.integer)
		{
			if (cl_particles_quake.integer)
			{
				if (cl_particles_smoke.integer)
					CL_NewParticlesFromEffectinfo(EFFECT_SVC_PARTICLE, 10*count, originmins, originmaxs, velocitymins, velocitymaxs, NULL, 0, spawndlight, spawnparticles, NULL, NULL, 1, wanttrail);
			}
			else
			{
				CL_Smoke(originmins, originmaxs, velocitymins, velocitymaxs, 4*count);
				CL_Sparks(originmins, originmaxs, velocitymins, velocitymaxs, 15*count);
				CL_NewParticle(center, pt_static, 0x808080,0x808080, tex_particle, 3, 0, 256, 512, 0, 0, lhrandom(originmins[0], originmaxs[0]), lhrandom(originmins[1], originmaxs[1]), lhrandom(originmins[2], originmaxs[2]), 0, 0, 0, 0, 0, 0, 0, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
			}
		}
		              
		R_Stain(center, 16, 40, 40, 40, 64, 88, 88, 88, 64);
		CL_SpawnDecalParticleForPoint(center, 6, 3, 255, tex_bulletdecal[rand()&7], 0xFFFFFF, 0xFFFFFF);
		CL_AllocLightFlash(NULL, &lightmatrix, 100, 0.15f, 0.15f, 1.5f, 500, 0.2, 0, -1, true, 1, 0.25, 1, 0, 0, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
	}
	else if (effectnameindex == EFFECT_TE_SUPERSPIKE)
	{
		if (cl_particles_bulletimpacts.integer)
		{
			if (cl_particles_quake.integer)
			{
				if (cl_particles_smoke.integer)
					CL_NewParticlesFromEffectinfo(EFFECT_SVC_PARTICLE, 20*count, originmins, originmaxs, velocitymins, velocitymaxs, NULL, 0, spawndlight, spawnparticles, NULL, NULL, 1, wanttrail);
			}
			else
			{
				CL_Smoke(originmins, originmaxs, velocitymins, velocitymaxs, 8*count);
				CL_Sparks(originmins, originmaxs, velocitymins, velocitymaxs, 30*count);
				CL_NewParticle(center, pt_static, 0x808080,0x808080, tex_particle, 3, 0, 256, 512, 0, 0, lhrandom(originmins[0], originmaxs[0]), lhrandom(originmins[1], originmaxs[1]), lhrandom(originmins[2], originmaxs[2]), 0, 0, 0, 0, 0, 0, 0, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
			}
		}
		              
		R_Stain(center, 16, 40, 40, 40, 64, 88, 88, 88, 64);
		CL_SpawnDecalParticleForPoint(center, 6, 3, 255, tex_bulletdecal[rand()&7], 0xFFFFFF, 0xFFFFFF);
	}
	else if (effectnameindex == EFFECT_TE_SUPERSPIKEQUAD)
	{
		if (cl_particles_bulletimpacts.integer)
		{
			if (cl_particles_quake.integer)
			{
				if (cl_particles_smoke.integer)
					CL_NewParticlesFromEffectinfo(EFFECT_SVC_PARTICLE, 20*count, originmins, originmaxs, velocitymins, velocitymaxs, NULL, 0, spawndlight, spawnparticles, NULL, NULL, 1, wanttrail);
			}
			else
			{
				CL_Smoke(originmins, originmaxs, velocitymins, velocitymaxs, 8*count);
				CL_Sparks(originmins, originmaxs, velocitymins, velocitymaxs, 30*count);
				CL_NewParticle(center, pt_static, 0x808080,0x808080, tex_particle, 3, 0, 256, 512, 0, 0, lhrandom(originmins[0], originmaxs[0]), lhrandom(originmins[1], originmaxs[1]), lhrandom(originmins[2], originmaxs[2]), 0, 0, 0, 0, 0, 0, 0, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
			}
		}
		              
		R_Stain(center, 16, 40, 40, 40, 64, 88, 88, 88, 64);
		CL_SpawnDecalParticleForPoint(center, 6, 3, 255, tex_bulletdecal[rand()&7], 0xFFFFFF, 0xFFFFFF);
		CL_AllocLightFlash(NULL, &lightmatrix, 100, 0.15f, 0.15f, 1.5f, 500, 0.2, 0, -1, true, 1, 0.25, 1, 0, 0, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
	}
	else if (effectnameindex == EFFECT_TE_BLOOD)
	{
		if (!cl_particles_blood.integer)
			return;
		if (cl_particles_quake.integer)
			CL_NewParticlesFromEffectinfo(EFFECT_SVC_PARTICLE, 2*count, originmins, originmaxs, velocitymins, velocitymaxs, NULL, 73, spawndlight, spawnparticles, NULL, NULL, 1, wanttrail);
		else
		{
			static double bloodaccumulator = 0;
			qboolean immediatebloodstain = (cl_decals_newsystem_immediatebloodstain.integer >= 1);
			                                                                                                                                                                                                                                                                                                   
			bloodaccumulator += count * 0.333 * cl_particles_quality.value;
			for (;bloodaccumulator > 0;bloodaccumulator--)
			{
				part = CL_NewParticle(center, pt_blood, 0xFFFFFF, 0xFFFFFF, tex_bloodparticle[rand()&7], 8, 0, cl_particles_blood_alpha.value * 768, cl_particles_blood_alpha.value * 384, 1, -1, lhrandom(originmins[0], originmaxs[0]), lhrandom(originmins[1], originmaxs[1]), lhrandom(originmins[2], originmaxs[2]), lhrandom(velocitymins[0], velocitymaxs[0]), lhrandom(velocitymins[1], velocitymaxs[1]), lhrandom(velocitymins[2], velocitymaxs[2]), 1, 4, 0, 64, true, 0, 1, PBLEND_INVMOD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
				if (immediatebloodstain && part)
				{
					immediatebloodstain = false;
					CL_ImmediateBloodStain(part);
				}
			}
		}
	}
	else if (effectnameindex == EFFECT_TE_SPARK)
		CL_Sparks(originmins, originmaxs, velocitymins, velocitymaxs, count);
	else if (effectnameindex == EFFECT_TE_PLASMABURN)
	{
		                     
		R_Stain(center, 40, 40, 40, 40, 64, 88, 88, 88, 64);
		CL_SpawnDecalParticleForPoint(center, 6, 6, 255, tex_bulletdecal[rand()&7], 0xFFFFFF, 0xFFFFFF);
		CL_AllocLightFlash(NULL, &lightmatrix, 200, 1, 1, 1, 1000, 0.2, 0, -1, true, 1, 0.25, 1, 0, 0, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
	}
	else if (effectnameindex == EFFECT_TE_GUNSHOT)
	{
		if (cl_particles_bulletimpacts.integer)
		{
			if (cl_particles_quake.integer)
				CL_NewParticlesFromEffectinfo(EFFECT_SVC_PARTICLE, 20*count, originmins, originmaxs, velocitymins, velocitymaxs, NULL, 0, spawndlight, spawnparticles, NULL, NULL, 1, wanttrail);
			else
			{
				CL_Smoke(originmins, originmaxs, velocitymins, velocitymaxs, 4*count);
				CL_Sparks(originmins, originmaxs, velocitymins, velocitymaxs, 20*count);
				CL_NewParticle(center, pt_static, 0x808080,0x808080, tex_particle, 3, 0, 256, 512, 0, 0, lhrandom(originmins[0], originmaxs[0]), lhrandom(originmins[1], originmaxs[1]), lhrandom(originmins[2], originmaxs[2]), 0, 0, 0, 0, 0, 0, 0, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
			}
		}
		              
		R_Stain(center, 16, 40, 40, 40, 64, 88, 88, 88, 64);
		CL_SpawnDecalParticleForPoint(center, 6, 3, 255, tex_bulletdecal[rand()&7], 0xFFFFFF, 0xFFFFFF);
	}
	else if (effectnameindex == EFFECT_TE_GUNSHOTQUAD)
	{
		if (cl_particles_bulletimpacts.integer)
		{
			if (cl_particles_quake.integer)
				CL_NewParticlesFromEffectinfo(EFFECT_SVC_PARTICLE, 20*count, originmins, originmaxs, velocitymins, velocitymaxs, NULL, 0, spawndlight, spawnparticles, NULL, NULL, 1, wanttrail);
			else
			{
				CL_Smoke(originmins, originmaxs, velocitymins, velocitymaxs, 4*count);
				CL_Sparks(originmins, originmaxs, velocitymins, velocitymaxs, 20*count);
				CL_NewParticle(center, pt_static, 0x808080,0x808080, tex_particle, 3, 0, 256, 512, 0, 0, lhrandom(originmins[0], originmaxs[0]), lhrandom(originmins[1], originmaxs[1]), lhrandom(originmins[2], originmaxs[2]), 0, 0, 0, 0, 0, 0, 0, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
			}
		}
		              
		R_Stain(center, 16, 40, 40, 40, 64, 88, 88, 88, 64);
		CL_SpawnDecalParticleForPoint(center, 6, 3, 255, tex_bulletdecal[rand()&7], 0xFFFFFF, 0xFFFFFF);
		CL_AllocLightFlash(NULL, &lightmatrix, 100, 0.15f, 0.15f, 1.5f, 500, 0.2, 0, -1, true, 1, 0.25, 1, 0, 0, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
	}
	else if (effectnameindex == EFFECT_TE_EXPLOSION)
	{
		CL_ParticleExplosion(center);
		CL_AllocLightFlash(NULL, &lightmatrix, 350, 4.0f, 2.0f, 0.50f, 700, 0.5, 0, -1, true, 1, 0.25, 0.25, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
	}
	else if (effectnameindex == EFFECT_TE_EXPLOSIONQUAD)
	{
		CL_ParticleExplosion(center);
		CL_AllocLightFlash(NULL, &lightmatrix, 350, 2.5f, 2.0f, 4.0f, 700, 0.5, 0, -1, true, 1, 0.25, 0.25, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
	}
	else if (effectnameindex == EFFECT_TE_TAREXPLOSION)
	{
		if (cl_particles_quake.integer)
		{
			int i;
			for (i = 0;i < 1024 * cl_particles_quality.value;i++)
			{
				if (i & 1)
					CL_NewParticle(center, pt_alphastatic, particlepalette[66], particlepalette[71], tex_particle, 1.5f, 0, 255, 0, 0, 0, center[0], center[1], center[2], 0, 0, 0, -4, -4, 16, 256, true, (rand() & 1) ? 1.4 : 1.0, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
				else
					CL_NewParticle(center, pt_alphastatic, particlepalette[150], particlepalette[155], tex_particle, 1.5f, 0, 255, 0, 0, 0, center[0], center[1], center[2], 0, 0, lhrandom(-256, 256), 0, 0, 16, 0, true, (rand() & 1) ? 1.4 : 1.0, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
			}
		}
		else
			CL_ParticleExplosion(center);
		CL_AllocLightFlash(NULL, &lightmatrix, 600, 1.6f, 0.8f, 2.0f, 1200, 0.5, 0, -1, true, 1, 0.25, 0.25, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
	}
	else if (effectnameindex == EFFECT_TE_SMALLFLASH)
		CL_AllocLightFlash(NULL, &lightmatrix, 200, 2, 2, 2, 1000, 0.2, 0, -1, true, 1, 0.25, 0.25, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
	else if (effectnameindex == EFFECT_TE_FLAMEJET)
	{
		count *= cl_particles_quality.value;
		while (count-- > 0)
			CL_NewParticle(center, pt_smoke, 0x6f0f00, 0xe3974f, tex_particle, 4, 0, lhrandom(64, 128), 384, -1, 1.1, lhrandom(originmins[0], originmaxs[0]), lhrandom(originmins[1], originmaxs[1]), lhrandom(originmins[2], originmaxs[2]), lhrandom(velocitymins[0], velocitymaxs[0]), lhrandom(velocitymins[1], velocitymaxs[1]), lhrandom(velocitymins[2], velocitymaxs[2]), 1, 4, 0, 128, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
	}
	else if (effectnameindex == EFFECT_TE_LAVASPLASH)
	{
		float i, j, inc, vel;
		vec3_t dir, org;

		inc = 8 / cl_particles_quality.value;
		for (i = -128;i < 128;i += inc)
		{
			for (j = -128;j < 128;j += inc)
			{
				dir[0] = j + lhrandom(0, inc);
				dir[1] = i + lhrandom(0, inc);
				dir[2] = 256;
				org[0] = center[0] + dir[0];
				org[1] = center[1] + dir[1];
				org[2] = center[2] + lhrandom(0, 64);
				vel = lhrandom(50, 120) / VectorLength(dir);                       
				CL_NewParticle(center, pt_alphastatic, particlepalette[224], particlepalette[231], tex_particle, 1.5f, 0, 255, 0, 0.05, 0, org[0], org[1], org[2], dir[0] * vel, dir[1] * vel, dir[2] * vel, 0, 0, 0, 0, true, lhrandom(2, 2.62), 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
			}
		}
	}
	else if (effectnameindex == EFFECT_TE_TELEPORT)
	{
		float i, j, k, inc, vel;
		vec3_t dir;

		if (cl_particles_quake.integer)
			inc = 4 / cl_particles_quality.value;
		else
			inc = 8 / cl_particles_quality.value;
		for (i = -16;i < 16;i += inc)
		{
			for (j = -16;j < 16;j += inc)
			{
				for (k = -24;k < 32;k += inc)
				{
					VectorSet(dir, i*8, j*8, k*8);
					VectorNormalize(dir);
					vel = lhrandom(50, 113);
					if (cl_particles_quake.integer)
						CL_NewParticle(center, pt_alphastatic, particlepalette[7], particlepalette[14], tex_particle, 1.5f, 0, 255, 0, 0, 0, center[0] + i + lhrandom(0, inc), center[1] + j + lhrandom(0, inc), center[2] + k + lhrandom(0, inc), dir[0] * vel, dir[1] * vel, dir[2] * vel, 0, 0, 0, 0, true, lhrandom(0.2, 0.34), 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					else
						CL_NewParticle(center, pt_alphastatic, particlepalette[7], particlepalette[14], tex_particle, 1.5f, 0, inc * lhrandom(37, 63), inc * 187, 0, 0, center[0] + i + lhrandom(0, inc), center[1] + j + lhrandom(0, inc), center[2] + k + lhrandom(0, inc), dir[0] * vel, dir[1] * vel, dir[2] * vel, 0, 0, 0, 0, true, 0, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
				}
			}
		}
		if (!cl_particles_quake.integer)
			CL_NewParticle(center, pt_static, 0xffffff, 0xffffff, tex_particle, 30, 0, 256, 512, 0, 0, center[0], center[1], center[2], 0, 0, 0, 0, 0, 0, 0, false, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
		CL_AllocLightFlash(NULL, &lightmatrix, 200, 2.0f, 2.0f, 2.0f, 400, 99.0f, 0, -1, true, 1, 0.25, 1, 0, 0, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
	}
	else if (effectnameindex == EFFECT_TE_TEI_G3)
		CL_NewParticle(center, pt_beam, 0xFFFFFF, 0xFFFFFF, tex_beam, 8, 0, 256, 256, 0, 0, originmins[0], originmins[1], originmins[2], originmaxs[0], originmaxs[1], originmaxs[2], 0, 0, 0, 0, false, 0, 1, PBLEND_ADD, PARTICLE_HBEAM, -1, -1, -1, 1, 1, 0, 0, NULL);
	else if (effectnameindex == EFFECT_TE_TEI_SMOKE)
	{
		if (cl_particles_smoke.integer)
		{
			count *= 0.25f * cl_particles_quality.value;
			while (count-- > 0)
				CL_NewParticle(center, pt_smoke, 0x202020, 0x404040, tex_smoke[rand()&7], 5, 0, 255, 512, 0, 0, lhrandom(originmins[0], originmaxs[0]), lhrandom(originmins[1], originmaxs[1]), lhrandom(originmins[2], originmaxs[2]), lhrandom(velocitymins[0], velocitymaxs[0]), lhrandom(velocitymins[1], velocitymaxs[1]), lhrandom(velocitymins[2], velocitymaxs[2]), 0, 0, 1.5f, 6.0f, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
		}
	}
	else if (effectnameindex == EFFECT_TE_TEI_BIGEXPLOSION)
	{
		CL_ParticleExplosion(center);
		CL_AllocLightFlash(NULL, &lightmatrix, 500, 2.5f, 2.0f, 1.0f, 500, 9999, 0, -1, true, 1, 0.25, 0.5, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
	}
	else if (effectnameindex == EFFECT_TE_TEI_PLASMAHIT)
	{
		float f;
		R_Stain(center, 40, 40, 40, 40, 64, 88, 88, 88, 64);
		CL_SpawnDecalParticleForPoint(center, 6, 8, 255, tex_bulletdecal[rand()&7], 0xFFFFFF, 0xFFFFFF);
		if (cl_particles_smoke.integer)
			for (f = 0;f < count;f += 4.0f / cl_particles_quality.value)
				CL_NewParticle(center, pt_smoke, 0x202020, 0x404040, tex_smoke[rand()&7], 5, 0, 255, 512, 0, 0, lhrandom(originmins[0], originmaxs[0]), lhrandom(originmins[1], originmaxs[1]), lhrandom(originmins[2], originmaxs[2]), lhrandom(velocitymins[0], velocitymaxs[0]), lhrandom(velocitymins[1], velocitymaxs[1]), lhrandom(velocitymins[2], velocitymaxs[2]), 0, 0, 20, 155, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
		if (cl_particles_sparks.integer)
			for (f = 0;f < count;f += 1.0f / cl_particles_quality.value)
				CL_NewParticle(center, pt_spark, 0x2030FF, 0x80C0FF, tex_particle, 2.0f, 0, lhrandom(64, 255), 512, 0, 0, lhrandom(originmins[0], originmaxs[0]), lhrandom(originmins[1], originmaxs[1]), lhrandom(originmins[2], originmaxs[2]), lhrandom(velocitymins[0], velocitymaxs[0]), lhrandom(velocitymins[1], velocitymaxs[1]), lhrandom(velocitymins[2], velocitymaxs[2]), 0, 0, 0, 465, true, 0, 1, PBLEND_ADD, PARTICLE_SPARK, -1, -1, -1, 1, 1, 0, 0, NULL);
		CL_AllocLightFlash(NULL, &lightmatrix, 500, 0.6f, 1.2f, 2.0f, 2000, 9999, 0, -1, true, 1, 0.25, 0.25, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
	}
	else if (effectnameindex == EFFECT_EF_FLAME)
	{
		if (!spawnparticles)
			count = 0;
		count *= 300 * cl_particles_quality.value;
		while (count-- > 0)
			CL_NewParticle(center, pt_smoke, 0x6f0f00, 0xe3974f, tex_particle, 4, 0, lhrandom(64, 128), 384, -1, 0, lhrandom(originmins[0], originmaxs[0]), lhrandom(originmins[1], originmaxs[1]), lhrandom(originmins[2], originmaxs[2]), lhrandom(velocitymins[0], velocitymaxs[0]), lhrandom(velocitymins[1], velocitymaxs[1]), lhrandom(velocitymins[2], velocitymaxs[2]), 1, 4, 16, 128, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
		CL_AllocLightFlash(NULL, &lightmatrix, 200, 2.0f, 1.5f, 0.5f, 0, 0, 0, -1, true, 1, 0.25, 0.25, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
	}
	else if (effectnameindex == EFFECT_EF_STARDUST)
	{
		if (!spawnparticles)
			count = 0;
		count *= 200 * cl_particles_quality.value;
		while (count-- > 0)
			CL_NewParticle(center, pt_static, 0x903010, 0xFFD030, tex_particle, 4, 0, lhrandom(64, 128), 128, 1, 0, lhrandom(originmins[0], originmaxs[0]), lhrandom(originmins[1], originmaxs[1]), lhrandom(originmins[2], originmaxs[2]), lhrandom(velocitymins[0], velocitymaxs[0]), lhrandom(velocitymins[1], velocitymaxs[1]), lhrandom(velocitymins[2], velocitymaxs[2]), 0.2, 0.8, 16, 128, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
		CL_AllocLightFlash(NULL, &lightmatrix, 200, 1.0f, 0.7f, 0.3f, 0, 0, 0, -1, true, 1, 0.25, 0.25, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
	}
	else if (!strncmp(particleeffectname[effectnameindex], "TR_", 3))
	{
		vec3_t dir, pos;
		float len, dec, qd;
		int smoke, blood, bubbles, r, color, spawnedcount;

		if (spawndlight && r_refdef.scene.numlights < MAX_DLIGHTS)
		{
			vec4_t light;
			Vector4Set(light, 0, 0, 0, 0);

			if (effectnameindex == EFFECT_TR_ROCKET)
				Vector4Set(light, 3.0f, 1.5f, 0.5f, 200);
			else if (effectnameindex == EFFECT_TR_VORESPIKE)
			{
				if (gamemode == GAME_PRYDON && !cl_particles_quake.integer)
					Vector4Set(light, 0.3f, 0.6f, 1.2f, 100);
				else
					Vector4Set(light, 1.2f, 0.5f, 1.0f, 200);
			}
			else if (effectnameindex == EFFECT_TR_NEXUIZPLASMA)
				Vector4Set(light, 0.75f, 1.5f, 3.0f, 200);

			if (light[3])
			{
				matrix4x4_t traillightmatrix;
				Matrix4x4_CreateFromQuakeEntity(&traillightmatrix, originmaxs[0], originmaxs[1], originmaxs[2], 0, 0, 0, light[3]);
				R_RTLight_Update(&r_refdef.scene.templights[r_refdef.scene.numlights], false, &traillightmatrix, light, -1, NULL, true, 1, 0.25, 0, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
				r_refdef.scene.lights[r_refdef.scene.numlights] = &r_refdef.scene.templights[r_refdef.scene.numlights];r_refdef.scene.numlights++;
			}
		}

		if (!spawnparticles)
			return;

		if (originmaxs[0] == originmins[0] && originmaxs[1] == originmins[1] && originmaxs[2] == originmins[2])
			return;

		VectorSubtract(originmaxs, originmins, dir);
		len = VectorNormalizeLength(dir);

		if (ent)
		{
			dec = -ent->persistent.trail_time;
			ent->persistent.trail_time += len;
			if (ent->persistent.trail_time < 0.01f)
				return;

			                                 
			ent->persistent.trail_time = 0.0f;
		}
		else
			dec = 0;

		                                                           
		VectorMA(originmins, dec, dir, pos);
		len -= dec;

		smoke = cl_particles.integer && cl_particles_smoke.integer;
		blood = cl_particles.integer && cl_particles_blood.integer;
		bubbles = cl_particles.integer && cl_particles_bubbles.integer && !cl_particles_quake.integer && (CL_PointSuperContents(pos) & (SUPERCONTENTS_WATER | SUPERCONTENTS_SLIME));
		qd = 1.0f / cl_particles_quality.value;
		spawnedcount = 0;

		while (len >= 0 && ++spawnedcount <= 16384)
		{
			dec = 3;
			if (blood)
			{
				if (effectnameindex == EFFECT_TR_BLOOD)
				{
					if (cl_particles_quake.integer)
					{
						color = particlepalette[67 + (rand()&3)];
						CL_NewParticle(center, pt_alphastatic, color, color, tex_particle, 1.5f, 0, 255, 0, 0.05, 0, pos[0], pos[1], pos[2], 0, 0, 0, 0, 0, 3, 0, true, 2, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					}
					else
					{
						dec = 16;
						CL_NewParticle(center, pt_blood, 0xFFFFFF, 0xFFFFFF, tex_bloodparticle[rand()&7], 8, 0, qd * cl_particles_blood_alpha.value * 768.0f, qd * cl_particles_blood_alpha.value * 384.0f, 1, -1, pos[0], pos[1], pos[2], lhrandom(velocitymins[0], velocitymaxs[0]), lhrandom(velocitymins[1], velocitymaxs[1]), lhrandom(velocitymins[2], velocitymaxs[2]), 1, 4, 0, 64, true, 0, 1, PBLEND_INVMOD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					}
				}
				else if (effectnameindex == EFFECT_TR_SLIGHTBLOOD)
				{
					if (cl_particles_quake.integer)
					{
						dec = 6;
						color = particlepalette[67 + (rand()&3)];
						CL_NewParticle(center, pt_alphastatic, color, color, tex_particle, 1.5f, 0, 255, 0, 0.05, 0, pos[0], pos[1], pos[2], 0, 0, 0, 0, 0, 3, 0, true, 2, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					}
					else
					{
						dec = 32;
						CL_NewParticle(center, pt_blood, 0xFFFFFF, 0xFFFFFF, tex_bloodparticle[rand()&7], 8, 0, qd * cl_particles_blood_alpha.value * 768.0f, qd * cl_particles_blood_alpha.value * 384.0f, 1, -1, pos[0], pos[1], pos[2], lhrandom(velocitymins[0], velocitymaxs[0]), lhrandom(velocitymins[1], velocitymaxs[1]), lhrandom(velocitymins[2], velocitymaxs[2]), 1, 4, 0, 64, true, 0, 1, PBLEND_INVMOD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					}
				}
			}
			if (smoke)
			{
				if (effectnameindex == EFFECT_TR_ROCKET)
				{
					if (cl_particles_quake.integer)
					{
						r = rand()&3;
						color = particlepalette[ramp3[r]];
						CL_NewParticle(center, pt_alphastatic, color, color, tex_particle, 1.5f, 0, 255, 0, -0.05, 0, pos[0], pos[1], pos[2], 0, 0, 0, 0, 0, 3, 0, true, 0.1372549*(6-r), 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					}
					else
					{
						CL_NewParticle(center, pt_smoke, 0x303030, 0x606060, tex_smoke[rand()&7], 3, 0, cl_particles_smoke_alpha.value*62, cl_particles_smoke_alphafade.value*62, 0, 0, pos[0], pos[1], pos[2], 0, 0, 0, 0, 0, 0, 0, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
						CL_NewParticle(center, pt_static, 0x801010, 0xFFA020, tex_smoke[rand()&7], 3, 0, cl_particles_smoke_alpha.value*288, cl_particles_smoke_alphafade.value*1400, 0, 0, pos[0], pos[1], pos[2], 0, 0, 0, 0, 0, 0, 20, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					}
				}
				else if (effectnameindex == EFFECT_TR_GRENADE)
				{
					if (cl_particles_quake.integer)
					{
						r = 2 + (rand()%5);
						color = particlepalette[ramp3[r]];
						CL_NewParticle(center, pt_alphastatic, color, color, tex_particle, 1.5f, 0, 255, 0, -0.05, 0, pos[0], pos[1], pos[2], 0, 0, 0, 0, 0, 3, 0, true, 0.1372549*(6-r), 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					}
					else
					{
						CL_NewParticle(center, pt_smoke, 0x303030, 0x606060, tex_smoke[rand()&7], 3, 0, cl_particles_smoke_alpha.value*50, cl_particles_smoke_alphafade.value*75, 0, 0, pos[0], pos[1], pos[2], 0, 0, 0, 0, 0, 0, 0, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					}
				}
				else if (effectnameindex == EFFECT_TR_WIZSPIKE)
				{
					if (cl_particles_quake.integer)
					{
						dec = 6;
						color = particlepalette[52 + (rand()&7)];
						CL_NewParticle(center, pt_alphastatic, color, color, tex_particle, 1.5f, 0, 255, 0, 0, 0, pos[0], pos[1], pos[2], 30*dir[1], 30*-dir[0], 0, 0, 0, 0, 0, true, 0.5, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
						CL_NewParticle(center, pt_alphastatic, color, color, tex_particle, 1.5f, 0, 255, 0, 0, 0, pos[0], pos[1], pos[2], 30*-dir[1], 30*dir[0], 0, 0, 0, 0, 0, true, 0.5, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					}
					else if (gamemode == GAME_GOODVSBAD2)
					{
						dec = 6;
						CL_NewParticle(center, pt_static, 0x00002E, 0x000030, tex_particle, 6, 0, 128, 384, 0, 0, pos[0], pos[1], pos[2], 0, 0, 0, 0, 0, 0, 0, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					}
					else
					{
						color = particlepalette[20 + (rand()&7)];
						CL_NewParticle(center, pt_static, color, color, tex_particle, 2, 0, 64, 192, 0, 0, pos[0], pos[1], pos[2], 0, 0, 0, 0, 0, 0, 0, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					}
				}
				else if (effectnameindex == EFFECT_TR_KNIGHTSPIKE)
				{
					if (cl_particles_quake.integer)
					{
						dec = 6;
						color = particlepalette[230 + (rand()&7)];
						CL_NewParticle(center, pt_alphastatic, color, color, tex_particle, 1.5f, 0, 255, 0, 0, 0, pos[0], pos[1], pos[2], 30*dir[1], 30*-dir[0], 0, 0, 0, 0, 0, true, 0.5, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
						CL_NewParticle(center, pt_alphastatic, color, color, tex_particle, 1.5f, 0, 255, 0, 0, 0, pos[0], pos[1], pos[2], 30*-dir[1], 30*dir[0], 0, 0, 0, 0, 0, true, 0.5, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					}
					else
					{
						color = particlepalette[226 + (rand()&7)];
						CL_NewParticle(center, pt_static, color, color, tex_particle, 2, 0, 64, 192, 0, 0, pos[0], pos[1], pos[2], 0, 0, 0, 0, 0, 0, 0, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					}
				}
				else if (effectnameindex == EFFECT_TR_VORESPIKE)
				{
					if (cl_particles_quake.integer)
					{
						color = particlepalette[152 + (rand()&3)];
						CL_NewParticle(center, pt_alphastatic, color, color, tex_particle, 1.5f, 0, 255, 0, 0, 0, pos[0], pos[1], pos[2], 0, 0, 0, 0, 0, 8, 0, true, 0.3, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					}
					else if (gamemode == GAME_GOODVSBAD2)
					{
						dec = 6;
						CL_NewParticle(center, pt_alphastatic, particlepalette[0 + (rand()&255)], particlepalette[0 + (rand()&255)], tex_particle, 6, 0, 255, 384, 0, 0, pos[0], pos[1], pos[2], 0, 0, 0, 0, 0, 0, 0, true, 0, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					}
					else if (gamemode == GAME_PRYDON)
					{
						dec = 6;
						CL_NewParticle(center, pt_static, 0x103040, 0x204050, tex_particle, 6, 0, 64, 192, 0, 0, pos[0], pos[1], pos[2], 0, 0, 0, 0, 0, 0, 0, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
					}
					else
						CL_NewParticle(center, pt_static, 0x502030, 0x502030, tex_particle, 3, 0, 64, 192, 0, 0, pos[0], pos[1], pos[2], 0, 0, 0, 0, 0, 0, 0, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
				}
				else if (effectnameindex == EFFECT_TR_NEHAHRASMOKE)
				{
					dec = 7;
					CL_NewParticle(center, pt_alphastatic, 0x303030, 0x606060, tex_smoke[rand()&7], 7, 0, 64, 320, 0, 0, pos[0], pos[1], pos[2], 0, 0, lhrandom(4, 12), 0, 0, 0, 4, false, 0, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
				}
				else if (effectnameindex == EFFECT_TR_NEXUIZPLASMA)
				{
					dec = 4;
					CL_NewParticle(center, pt_static, 0x283880, 0x283880, tex_particle, 4, 0, 255, 1024, 0, 0, pos[0], pos[1], pos[2], 0, 0, 0, 0, 0, 0, 16, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
				}
				else if (effectnameindex == EFFECT_TR_GLOWTRAIL)
					CL_NewParticle(center, pt_alphastatic, particlepalette[palettecolor], particlepalette[palettecolor], tex_particle, 5, 0, 128, 320, 0, 0, pos[0], pos[1], pos[2], 0, 0, 0, 0, 0, 0, 0, true, 0, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
			}
			if (bubbles)
			{
				if (effectnameindex == EFFECT_TR_ROCKET)
					CL_NewParticle(center, pt_bubble, 0x404040, 0x808080, tex_bubble, 2, 0, lhrandom(128, 512), 512, -0.25, 1.5, pos[0], pos[1], pos[2], 0, 0, 0, 0.0625, 0.25, 0, 16, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
				else if (effectnameindex == EFFECT_TR_GRENADE)
					CL_NewParticle(center, pt_bubble, 0x404040, 0x808080, tex_bubble, 2, 0, lhrandom(128, 512), 512, -0.25, 1.5, pos[0], pos[1], pos[2], 0, 0, 0, 0.0625, 0.25, 0, 16, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
			}
			                                    
			dec *= qd;
			len -= dec;
			VectorMA (pos, dec, dir, pos);
		}
		if (ent)
			ent->persistent.trail_time = len;
	}
	else
		Con_DPrintf("CL_ParticleEffect_Fallback: no fallback found for effect %s\n", particleeffectname[effectnameindex]);
}

                                                                   
                        
static void CL_NewParticlesFromEffectinfo(int effectnameindex, float pcount, const vec3_t originmins, const vec3_t originmaxs, const vec3_t velocitymins, const vec3_t velocitymaxs, entity_t *ent, int palettecolor, qboolean spawndlight, qboolean spawnparticles, float tintmins[4], float tintmaxs[4], float fade, qboolean wanttrail)
{
	qboolean found = false;
	char vabuf[1024];
	if (effectnameindex < 1 || effectnameindex >= MAX_PARTICLEEFFECTNAME || !particleeffectname[effectnameindex][0])
	{
		Con_DPrintf("Unknown effect number %i received from server\n", effectnameindex);
		return;                  
	}
	if (!cl_particles_quake.integer && particleeffectinfo[0].effectnameindex)
	{
		int effectinfoindex;
		int supercontents;
		int tex, staintex;
		particleeffectinfo_t *info;
		vec3_t center;
		vec3_t traildir;
		vec3_t trailpos;
		vec3_t rvec;
		vec3_t angles;
		vec3_t velocity;
		vec3_t forward;
		vec3_t right;
		vec3_t up;
		vec_t traillen;
		vec_t trailstep;
		qboolean underwater;
		qboolean immediatebloodstain;
		particle_t *part;
		float avgtint[4], tint[4], tintlerp;
		                                                                                                                                    
		VectorLerp(originmins, 0.5, originmaxs, center);
		supercontents = CL_PointSuperContents(center);
		underwater = (supercontents & (SUPERCONTENTS_WATER | SUPERCONTENTS_SLIME)) != 0;
		VectorSubtract(originmaxs, originmins, traildir);
		traillen = VectorLength(traildir);
		VectorNormalize(traildir);
		if(tintmins)
		{
			Vector4Lerp(tintmins, 0.5, tintmaxs, avgtint);
		}
		else
		{
			Vector4Set(avgtint, 1, 1, 1, 1);
		}
		for (effectinfoindex = 0, info = particleeffectinfo;effectinfoindex < MAX_PARTICLEEFFECTINFO && info->effectnameindex;effectinfoindex++, info++)
		{
			if ((info->effectnameindex == effectnameindex) && (info->flags & PARTICLEEFFECT_DEFINED))
			{
				qboolean definedastrail = info->trailspacing > 0;

				qboolean drawastrail = wanttrail;
				if (cl_particles_forcetraileffects.integer)
					drawastrail = drawastrail || definedastrail;

				found = true;
				if ((info->flags & PARTICLEEFFECT_UNDERWATER) && !underwater)
					continue;
				if ((info->flags & PARTICLEEFFECT_NOTUNDERWATER) && underwater)
					continue;

				                              
				if (info->lightradiusstart > 0 && spawndlight)
				{
					matrix4x4_t tempmatrix;
					if (drawastrail)
						Matrix4x4_CreateTranslate(&tempmatrix, originmaxs[0], originmaxs[1], originmaxs[2]);
					else
						Matrix4x4_CreateTranslate(&tempmatrix, center[0], center[1], center[2]);
					if (info->lighttime > 0 && info->lightradiusfade > 0)
					{
						                               
						                            
						CL_AllocLightFlash(NULL, &tempmatrix, info->lightradiusstart, info->lightcolor[0]*avgtint[0]*avgtint[3], info->lightcolor[1]*avgtint[1]*avgtint[3], info->lightcolor[2]*avgtint[2]*avgtint[3], info->lightradiusfade, info->lighttime, info->lightcubemapnum, -1, info->lightshadow, info->lightcorona[0], info->lightcorona[1], 0, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
					}
					else if (r_refdef.scene.numlights < MAX_DLIGHTS)
					{
						                 
						                                 
						Matrix4x4_Scale(&tempmatrix, info->lightradiusstart, 1);
						rvec[0] = info->lightcolor[0]*avgtint[0]*avgtint[3];
						rvec[1] = info->lightcolor[1]*avgtint[1]*avgtint[3];
						rvec[2] = info->lightcolor[2]*avgtint[2]*avgtint[3];
						R_RTLight_Update(&r_refdef.scene.templights[r_refdef.scene.numlights], false, &tempmatrix, rvec, -1, info->lightcubemapnum > 0 ? va(vabuf, sizeof(vabuf), "cubemaps/%i", info->lightcubemapnum) : NULL, info->lightshadow, info->lightcorona[0], info->lightcorona[1], 0, 1, 1, LIGHTFLAG_NORMALMODE | LIGHTFLAG_REALTIMEMODE);
						r_refdef.scene.lights[r_refdef.scene.numlights] = &r_refdef.scene.templights[r_refdef.scene.numlights];r_refdef.scene.numlights++;
					}
				}

				if (!spawnparticles)
					continue;

				                  
				tex = info->tex[0];
				if (info->tex[1] > info->tex[0])
				{
					tex = (int)lhrandom(info->tex[0], info->tex[1]);
					tex = min(tex, info->tex[1] - 1);
				}
				if(info->staintex[0] < 0)
					staintex = info->staintex[0];
				else
				{
					staintex = (int)lhrandom(info->staintex[0], info->staintex[1]);
					staintex = min(staintex, info->staintex[1] - 1);
				}
				if (info->particletype == pt_decal)
				{
					VectorMAM(0.5f, velocitymins, 0.5f, velocitymaxs, velocity);
					AnglesFromVectors(angles, velocity, NULL, false);
					AngleVectors(angles, forward, right, up);
					VectorMAMAMAM(1.0f, center, info->relativeoriginoffset[0], forward, info->relativeoriginoffset[1], right, info->relativeoriginoffset[2], up, trailpos);

					CL_SpawnDecalParticleForPoint(trailpos, info->originjitter[0], lhrandom(info->size[0], info->size[1]), lhrandom(info->alpha[0], info->alpha[1])*avgtint[3], tex, info->color[0], info->color[1]);
				}
				else if (info->orientation == PARTICLE_HBEAM)
				{
					if (!drawastrail)
						continue;

					AnglesFromVectors(angles, traildir, NULL, false);
					AngleVectors(angles, forward, right, up);
					VectorMAMAM(info->relativeoriginoffset[0], forward, info->relativeoriginoffset[1], right, info->relativeoriginoffset[2], up, trailpos);

					CL_NewParticle(center, info->particletype, info->color[0], info->color[1], tex, lhrandom(info->size[0], info->size[1]), info->size[2], lhrandom(info->alpha[0], info->alpha[1]), info->alpha[2], 0, 0, originmins[0] + trailpos[0], originmins[1] + trailpos[1], originmins[2] + trailpos[2], originmaxs[0], originmaxs[1], originmaxs[2], 0, 0, 0, 0, false, lhrandom(info->time[0], info->time[1]), info->stretchfactor, info->blendmode, info->orientation, info->staincolor[0], info->staincolor[1], staintex, lhrandom(info->stainalpha[0], info->stainalpha[1]), lhrandom(info->stainsize[0], info->stainsize[1]), 0, 0, tintmins ? avgtint : NULL);
				}
				else
				{
					float cnt;
					if (!cl_particles.integer)
						continue;
					switch (info->particletype)
					{
					case pt_smoke: if (!cl_particles_smoke.integer) continue;break;
					case pt_spark: if (!cl_particles_sparks.integer) continue;break;
					case pt_bubble: if (!cl_particles_bubbles.integer) continue;break;
					case pt_blood: if (!cl_particles_blood.integer) continue;break;
					case pt_rain: if (!cl_particles_rain.integer) continue;break;
					case pt_snow: if (!cl_particles_snow.integer) continue;break;
					default: break;
					}

					cnt = info->countabsolute;
					cnt += (pcount * info->countmultiplier) * cl_particles_quality.value;
					                                     
					                                   
					                                      
					                                  
					if (drawastrail && definedastrail)
						cnt += (traillen / info->trailspacing) * cl_particles_quality.value;
					cnt *= fade;
					if (cnt == 0)
						continue;                    
					info->particleaccumulator += cnt;

					if (drawastrail || definedastrail)
						immediatebloodstain = false;
					else
						immediatebloodstain =
							((cl_decals_newsystem_immediatebloodstain.integer >= 1) && (info->particletype == pt_blood))
							||
							((cl_decals_newsystem_immediatebloodstain.integer >= 2) && staintex);

					if (drawastrail)
					{
						VectorCopy(originmins, trailpos);
						trailstep = traillen / cnt;
					}
					else
					{
						VectorCopy(center, trailpos);
						trailstep = 0;
					}

					if (trailstep == 0)
					{
						VectorMAM(0.5f, velocitymins, 0.5f, velocitymaxs, velocity);
						AnglesFromVectors(angles, velocity, NULL, false);
					}
					else
						AnglesFromVectors(angles, traildir, NULL, false);

					AngleVectors(angles, forward, right, up);
					VectorMAMAMAM(1.0f, trailpos, info->relativeoriginoffset[0], forward, info->relativeoriginoffset[1], right, info->relativeoriginoffset[2], up, trailpos);
					VectorMAMAM(info->relativevelocityoffset[0], forward, info->relativevelocityoffset[1], right, info->relativevelocityoffset[2], up, velocity);
					info->particleaccumulator = bound(0, info->particleaccumulator, 16384);
					for (;info->particleaccumulator >= 1;info->particleaccumulator--)
					{
						if (info->tex[1] > info->tex[0])
						{
							tex = (int)lhrandom(info->tex[0], info->tex[1]);
							tex = min(tex, info->tex[1] - 1);
						}
						if (!(drawastrail || definedastrail))
						{
							trailpos[0] = lhrandom(originmins[0], originmaxs[0]);
							trailpos[1] = lhrandom(originmins[1], originmaxs[1]);
							trailpos[2] = lhrandom(originmins[2], originmaxs[2]);
						}
						if(tintmins)
						{
							tintlerp = lhrandom(0, 1);
							Vector4Lerp(tintmins, tintlerp, tintmaxs, tint);
						}
						VectorRandom(rvec);
						part = CL_NewParticle(center, info->particletype, info->color[0], info->color[1], tex, lhrandom(info->size[0], info->size[1]), info->size[2], lhrandom(info->alpha[0], info->alpha[1]), info->alpha[2], info->gravity, info->bounce, trailpos[0] + info->originoffset[0] + info->originjitter[0] * rvec[0], trailpos[1] + info->originoffset[1] + info->originjitter[1] * rvec[1], trailpos[2] + info->originoffset[2] + info->originjitter[2] * rvec[2], lhrandom(velocitymins[0], velocitymaxs[0]) * info->velocitymultiplier + info->velocityoffset[0] + info->velocityjitter[0] * rvec[0] + velocity[0], lhrandom(velocitymins[1], velocitymaxs[1]) * info->velocitymultiplier + info->velocityoffset[1] + info->velocityjitter[1] * rvec[1] + velocity[1], lhrandom(velocitymins[2], velocitymaxs[2]) * info->velocitymultiplier + info->velocityoffset[2] + info->velocityjitter[2] * rvec[2] + velocity[2], info->airfriction, info->liquidfriction, 0, 0, info->countabsolute <= 0, lhrandom(info->time[0], info->time[1]), info->stretchfactor, info->blendmode, info->orientation, info->staincolor[0], info->staincolor[1], staintex, lhrandom(info->stainalpha[0], info->stainalpha[1]), lhrandom(info->stainsize[0], info->stainsize[1]), lhrandom(info->rotate[0], info->rotate[1]), lhrandom(info->rotate[2], info->rotate[3]), tintmins ? tint : NULL);
						if (immediatebloodstain && part)
						{
							immediatebloodstain = false;
							CL_ImmediateBloodStain(part);
						}
						if (trailstep)
							VectorMA(trailpos, trailstep, traildir, trailpos);
					}
				}
			}
		}
	}
	if (!found)
		CL_ParticleEffect_Fallback(effectnameindex, pcount, originmins, originmaxs, velocitymins, velocitymaxs, ent, palettecolor, spawndlight, spawnparticles, wanttrail);
}

void CL_ParticleTrail(int effectnameindex, float pcount, const vec3_t originmins, const vec3_t originmaxs, const vec3_t velocitymins, const vec3_t velocitymaxs, entity_t *ent, int palettecolor, qboolean spawndlight, qboolean spawnparticles, float tintmins[4], float tintmaxs[4], float fade)
{
	CL_NewParticlesFromEffectinfo(effectnameindex, pcount, originmins, originmaxs, velocitymins, velocitymaxs, ent, palettecolor, spawndlight, spawnparticles, tintmins, tintmaxs, fade, true);
}

void CL_ParticleBox(int effectnameindex, float pcount, const vec3_t originmins, const vec3_t originmaxs, const vec3_t velocitymins, const vec3_t velocitymaxs, entity_t *ent, int palettecolor, qboolean spawndlight, qboolean spawnparticles, float tintmins[4], float tintmaxs[4], float fade)
{
	CL_NewParticlesFromEffectinfo(effectnameindex, pcount, originmins, originmaxs, velocitymins, velocitymaxs, ent, palettecolor, spawndlight, spawnparticles, tintmins, tintmaxs, fade, false);
}

                                  
void CL_ParticleEffect(int effectnameindex, float pcount, const vec3_t originmins, const vec3_t originmaxs, const vec3_t velocitymins, const vec3_t velocitymaxs, entity_t *ent, int palettecolor)
{
	CL_ParticleBox(effectnameindex, pcount, originmins, originmaxs, velocitymins, velocitymaxs, ent, palettecolor, true, true, NULL, NULL, 1);
}

  
               
                  
               
  
void CL_EntityParticles (const entity_t *ent)
{
	int i, j;
	vec_t pitch, yaw, dist = 64, beamlength = 16;
	vec3_t org, v;
	static vec3_t avelocities[NUMVERTEXNORMALS];
	if (!cl_particles.integer) return;
	if (cl.time <= cl.oldtime) return;                                                 

	Matrix4x4_OriginFromMatrix(&ent->render.matrix, org);

	if (!avelocities[0][0])
		for (i = 0;i < NUMVERTEXNORMALS;i++)
			for (j = 0;j < 3;j++)
				avelocities[i][j] = lhrandom(0, 2.55);

	for (i = 0;i < NUMVERTEXNORMALS;i++)
	{
		yaw = cl.time * avelocities[i][0];
		pitch = cl.time * avelocities[i][1];
		v[0] = org[0] + m_bytenormals[i][0] * dist + (cos(pitch)*cos(yaw)) * beamlength;
		v[1] = org[1] + m_bytenormals[i][1] * dist + (cos(pitch)*sin(yaw)) * beamlength;
		v[2] = org[2] + m_bytenormals[i][2] * dist + (-sin(pitch)) * beamlength;
		CL_NewParticle(org, pt_entityparticle, particlepalette[0x6f], particlepalette[0x6f], tex_particle, 1, 0, 255, 0, 0, 0, v[0], v[1], v[2], 0, 0, 0, 0, 0, 0, 0, true, 0, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
	}
}


void CL_ReadPointFile_f (void)
{
	double org[3], leakorg[3];
	vec3_t vecorg;
	int r, c, s;
	char *pointfile = NULL, *pointfilepos, *t, tchar;
	char name[MAX_QPATH];

	if (!cl.worldmodel)
		return;

	dpsnprintf(name, sizeof(name), "%s.pts", cl.worldnamenoextension);
	pointfile = (char *)FS_LoadFile(name, tempmempool, true, NULL);
	if (!pointfile)
	{
		Con_Printf("Could not open %s\n", name);
		return;
	}

	Con_Printf("Reading %s...\n", name);
	VectorClear(leakorg);
	c = 0;
	s = 0;
	pointfilepos = pointfile;
	while (*pointfilepos)
	{
		while (*pointfilepos == '\n' || *pointfilepos == '\r')
			pointfilepos++;
		if (!*pointfilepos)
			break;
		t = pointfilepos;
		while (*t && *t != '\n' && *t != '\r')
			t++;
		tchar = *t;
		*t = 0;
#if _MSC_VER >= 1400
#define sscanf sscanf_s
#endif
		r = sscanf (pointfilepos,"%lf %lf %lf", &org[0], &org[1], &org[2]);
		VectorCopy(org, vecorg);
		*t = tchar;
		pointfilepos = t;
		if (r != 3)
			break;
		if (c == 0)
			VectorCopy(org, leakorg);
		c++;

		if (cl.num_particles < cl.max_particles - 3)
		{
			s++;
			CL_NewParticle(vecorg, pt_alphastatic, particlepalette[(-c)&15], particlepalette[(-c)&15], tex_particle, 2, 0, 255, 0, 0, 0, org[0], org[1], org[2], 0, 0, 0, 0, 0, 0, 0, true, 1<<30, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
		}
	}
	Mem_Free(pointfile);
	VectorCopy(leakorg, vecorg);
	Con_Printf("%i points read (%i particles spawned)\nLeak at %f %f %f\n", c, s, leakorg[0], leakorg[1], leakorg[2]);

	if (c == 0)
	{
		return;
	}

	CL_NewParticle(vecorg, pt_beam, 0xFF0000, 0xFF0000, tex_beam, 64, 0, 255, 0, 0, 0, org[0] - 4096, org[1], org[2], org[0] + 4096, org[1], org[2], 0, 0, 0, 0, false, 1<<30, 1, PBLEND_ADD, PARTICLE_HBEAM, -1, -1, -1, 1, 1, 0, 0, NULL);
	CL_NewParticle(vecorg, pt_beam, 0x00FF00, 0x00FF00, tex_beam, 64, 0, 255, 0, 0, 0, org[0], org[1] - 4096, org[2], org[0], org[1] + 4096, org[2], 0, 0, 0, 0, false, 1<<30, 1, PBLEND_ADD, PARTICLE_HBEAM, -1, -1, -1, 1, 1, 0, 0, NULL);
	CL_NewParticle(vecorg, pt_beam, 0x0000FF, 0x0000FF, tex_beam, 64, 0, 255, 0, 0, 0, org[0], org[1], org[2] - 4096, org[0], org[1], org[2] + 4096, 0, 0, 0, 0, false, 1<<30, 1, PBLEND_ADD, PARTICLE_HBEAM, -1, -1, -1, 1, 1, 0, 0, NULL);
}

  
               
                      

                                         
               
  
void CL_ParseParticleEffect (void)
{
	vec3_t org, dir;
	int i, count, msgcount, color;

	MSG_ReadVector(&cl_message, org, cls.protocol);
	for (i=0 ; i<3 ; i++)
		dir[i] = MSG_ReadChar(&cl_message) * (1.0 / 16.0);
	msgcount = MSG_ReadByte(&cl_message);
	color = MSG_ReadByte(&cl_message);

	if (msgcount == 255)
		count = 1024;
	else
		count = msgcount;

	CL_ParticleEffect(EFFECT_SVC_PARTICLE, count, org, org, dir, dir, NULL, color);
}

  
               
                    

               
  
void CL_ParticleExplosion (const vec3_t org)
{
	int i;
	trace_t trace;
	           
	            
	R_Stain(org, 96, 40, 40, 40, 64, 88, 88, 88, 64);
	CL_SpawnDecalParticleForPoint(org, 40, 48, 255, tex_bulletdecal[rand()&7], 0xFFFFFF, 0xFFFFFF);

	if (cl_particles_quake.integer)
	{
		for (i = 0;i < 1024;i++)
		{
			int r, color;
			r = rand()&3;
			if (i & 1)
			{
				color = particlepalette[ramp1[r]];
				CL_NewParticle(org, pt_alphastatic, color, color, tex_particle, 1.5f, 0, 255, 0, 0, 0, org[0], org[1], org[2], 0, 0, 0, -4, -4, 16, 256, true, 0.1006 * (8 - r), 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
			}
			else
			{
				color = particlepalette[ramp2[r]];
				CL_NewParticle(org, pt_alphastatic, color, color, tex_particle, 1.5f, 0, 255, 0, 0, 0, org[0], org[1], org[2], 0, 0, 0, 1, 1, 16, 256, true, 0.0669 * (8 - r), 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
			}
		}
	}
	else
	{
		i = CL_PointSuperContents(org);
		if (i & (SUPERCONTENTS_SLIME | SUPERCONTENTS_WATER))
		{
			if (cl_particles.integer && cl_particles_bubbles.integer)
				for (i = 0;i < 128 * cl_particles_quality.value;i++)
					CL_NewParticle(org, pt_bubble, 0x404040, 0x808080, tex_bubble, 2, 0, lhrandom(128, 255), 128, -0.125, 1.5, org[0], org[1], org[2], 0, 0, 0, 0.0625, 0.25, 16, 96, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
		}
		else
		{
			if (cl_particles.integer && cl_particles_sparks.integer && cl_particles_explosions_sparks.integer)
			{
				for (i = 0;i < 512 * cl_particles_quality.value;i++)
				{
					int k = 0;
					vec3_t v, v2;
					do
					{
						VectorRandom(v2);
						VectorMA(org, 128, v2, v);
						trace = CL_TraceLine(org, v, MOVE_NOMONSTERS, NULL, SUPERCONTENTS_SOLID, 0, 0, collision_extendmovelength.value, true, false, NULL, false, false);
					}
					while (k < 16 && trace.fraction < 0.1f);
					VectorSubtract(trace.endpos, org, v2);
					VectorScale(v2, 2.0f, v2);
					CL_NewParticle(org, pt_spark, 0x903010, 0xFFD030, tex_particle, 1.0f, 0, lhrandom(0, 255), 512, 0, 0, org[0], org[1], org[2], v2[0], v2[1], v2[2], 0, 0, 0, 0, true, 0, 1, PBLEND_ADD, PARTICLE_SPARK, -1, -1, -1, 1, 1, 0, 0, NULL);
				}
			}
		}
	}

	if (cl_particles_explosions_shell.integer)
		R_NewExplosion(org);
}

  
               
                     

               
  
void CL_ParticleExplosion2 (const vec3_t org, int colorStart, int colorLength)
{
	int i, k;
	if (!cl_particles.integer) return;

	for (i = 0;i < 512 * cl_particles_quality.value;i++)
	{
		k = particlepalette[colorStart + (i % colorLength)];
		if (cl_particles_quake.integer)
			CL_NewParticle(org, pt_alphastatic, k, k, tex_particle, 1, 0, 255, 0, 0, 0, org[0], org[1], org[2], 0, 0, 0, -4, -4, 16, 256, true, 0.3, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
		else
			CL_NewParticle(org, pt_alphastatic, k, k, tex_particle, lhrandom(0.5, 1.5), 0, 255, 512, 0, 0, org[0], org[1], org[2], 0, 0, 0, lhrandom(1.5, 3), lhrandom(1.5, 3), 8, 192, true, 0, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
	}
}

static void CL_Sparks(const vec3_t originmins, const vec3_t originmaxs, const vec3_t velocitymins, const vec3_t velocitymaxs, float sparkcount)
{
	vec3_t center;
	VectorMAM(0.5f, originmins, 0.5f, originmaxs, center);
	if (cl_particles_sparks.integer)
	{
		sparkcount *= cl_particles_quality.value;
		while(sparkcount-- > 0)
			CL_NewParticle(center, pt_spark, particlepalette[0x68], particlepalette[0x6f], tex_particle, 0.5f, 0, lhrandom(64, 255), 512, 1, 0, lhrandom(originmins[0], originmaxs[0]), lhrandom(originmins[1], originmaxs[1]), lhrandom(originmins[2], originmaxs[2]), lhrandom(velocitymins[0], velocitymaxs[0]), lhrandom(velocitymins[1], velocitymaxs[1]), lhrandom(velocitymins[2], velocitymaxs[2]) + cl.movevars_gravity * 0.1f, 0, 0, 0, 64, true, 0, 1, PBLEND_ADD, PARTICLE_SPARK, -1, -1, -1, 1, 1, 0, 0, NULL);
	}
}

static void CL_Smoke(const vec3_t originmins, const vec3_t originmaxs, const vec3_t velocitymins, const vec3_t velocitymaxs, float smokecount)
{
	vec3_t center;
	VectorMAM(0.5f, originmins, 0.5f, originmaxs, center);
	if (cl_particles_smoke.integer)
	{
		smokecount *= cl_particles_quality.value;
		while(smokecount-- > 0)
			CL_NewParticle(center, pt_smoke, 0x101010, 0x101010, tex_smoke[rand()&7], 2, 2, 255, 256, 0, 0, lhrandom(originmins[0], originmaxs[0]), lhrandom(originmins[1], originmaxs[1]), lhrandom(originmins[2], originmaxs[2]), lhrandom(velocitymins[0], velocitymaxs[0]), lhrandom(velocitymins[1], velocitymaxs[1]), lhrandom(velocitymins[2], velocitymaxs[2]), 0, 0, 0, smokecount > 0 ? 16 : 0, true, 0, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
	}
}

void CL_ParticleCube (const vec3_t mins, const vec3_t maxs, const vec3_t dir, int count, int colorbase, vec_t gravity, vec_t randomvel)
{
	vec3_t center;
	int k;
	if (!cl_particles.integer) return;
	VectorMAM(0.5f, mins, 0.5f, maxs, center);

	count = (int)(count * cl_particles_quality.value);
	while (count--)
	{
		k = particlepalette[colorbase + (rand()&3)];
		CL_NewParticle(center, pt_alphastatic, k, k, tex_particle, 2, 0, 255, 128, gravity, 0, lhrandom(mins[0], maxs[0]), lhrandom(mins[1], maxs[1]), lhrandom(mins[2], maxs[2]), dir[0], dir[1], dir[2], 0, 0, 0, randomvel, true, 0, 1, PBLEND_ALPHA, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
	}
}

void CL_ParticleRain (const vec3_t mins, const vec3_t maxs, const vec3_t dir, int count, int colorbase, int type)
{
	int k;
	float minz, maxz, lifetime = 30;
	vec3_t org;
	if (!cl_particles.integer) return;
	if (dir[2] < 0)           
	{
		minz = maxs[2] + dir[2] * 0.1;
		maxz = maxs[2];
		if (cl.worldmodel)
			lifetime = (maxz - cl.worldmodel->normalmins[2]) / max(1, -dir[2]);
	}
	else            
	{
		minz = mins[2];
		maxz = maxs[2] + dir[2] * 0.1;
		if (cl.worldmodel)
			lifetime = (cl.worldmodel->normalmaxs[2] - minz) / max(1, dir[2]);
	}

	count = (int)(count * cl_particles_quality.value);

	switch(type)
	{
	case 0:
		if (!cl_particles_rain.integer) break;
		count *= 4;                                           

		while(count--)
		{
			k = particlepalette[colorbase + (rand()&3)];
			VectorSet(org, lhrandom(mins[0], maxs[0]), lhrandom(mins[1], maxs[1]), lhrandom(minz, maxz));
			if (gamemode == GAME_GOODVSBAD2)
				CL_NewParticle(org, pt_rain, k, k, tex_particle, 20, 0, lhrandom(32, 64), 0, 0, -1, org[0], org[1], org[2], dir[0], dir[1], dir[2], 0, 0, 0, 0, true, lifetime, 1, PBLEND_ADD, PARTICLE_SPARK, -1, -1, -1, 1, 1, 0, 0, NULL);
			else
				CL_NewParticle(org, pt_rain, k, k, tex_particle, 0.5, 0, lhrandom(32, 64), 0, 0, -1, org[0], org[1], org[2], dir[0], dir[1], dir[2], 0, 0, 0, 0, true, lifetime, 1, PBLEND_ADD, PARTICLE_SPARK, -1, -1, -1, 1, 1, 0, 0, NULL);
		}
		break;
	case 1:
		if (!cl_particles_snow.integer) break;
		while(count--)
		{
			k = particlepalette[colorbase + (rand()&3)];
			VectorSet(org, lhrandom(mins[0], maxs[0]), lhrandom(mins[1], maxs[1]), lhrandom(minz, maxz));
			if (gamemode == GAME_GOODVSBAD2)
				CL_NewParticle(org, pt_snow, k, k, tex_particle, 20, 0, lhrandom(64, 128), 0, 0, -1, org[0], org[1], org[2], dir[0], dir[1], dir[2], 0, 0, 0, 0, true, lifetime, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
			else
				CL_NewParticle(org, pt_snow, k, k, tex_particle, 1, 0, lhrandom(64, 128), 0, 0, -1, org[0], org[1], org[2], dir[0], dir[1], dir[2], 0, 0, 0, 0, true, lifetime, 1, PBLEND_ADD, PARTICLE_BILLBOARD, -1, -1, -1, 1, 1, 0, 0, NULL);
		}
		break;
	default:
		Con_Printf ("CL_ParticleRain: unknown type %i (0 = rain, 1 = snow)\n", type);
	}
}

cvar_t r_drawparticles = {0, "r_drawparticles", "1", "enables drawing of particles"};
static cvar_t r_drawparticles_drawdistance = {CVAR_SAVE, "r_drawparticles_drawdistance", "2000", "particles further than drawdistance*size will not be drawn"};
static cvar_t r_drawparticles_nearclip_min = {CVAR_SAVE, "r_drawparticles_nearclip_min", "4", "particles closer than drawnearclip_min will not be drawn"};
static cvar_t r_drawparticles_nearclip_max = {CVAR_SAVE, "r_drawparticles_nearclip_max", "4", "particles closer than drawnearclip_min will be faded"};
cvar_t r_drawdecals = {0, "r_drawdecals", "1", "enables drawing of decals"};
static cvar_t r_drawdecals_drawdistance = {CVAR_SAVE, "r_drawdecals_drawdistance", "500", "decals further than drawdistance*size will not be drawn"};

#define PARTICLETEXTURESIZE 64
#define PARTICLEFONTSIZE (PARTICLETEXTURESIZE*8)

static unsigned char shadebubble(float dx, float dy, vec3_t light)
{
	float dz, f, dot;
	vec3_t normal;
	dz = 1 - (dx*dx+dy*dy);
	if (dz > 0)                          
	{
		f = 0;
		            
		normal[0] = dx;normal[1] = dy;normal[2] = dz;
		VectorNormalize(normal);
		dot = DotProduct(normal, light);
		if (dot > 0.5)                       
			f += ((dot *  2) - 1);
		else if (dot < -0.5)                       
			f += ((dot * -2) - 1);
		             
		normal[0] = dx;normal[1] = dy;normal[2] = -dz;
		VectorNormalize(normal);
		dot = DotProduct(normal, light);
		if (dot > 0.5)                       
			f += ((dot *  2) - 1);
		else if (dot < -0.5)                       
			f += ((dot * -2) - 1);
		f *= 128;
		f += 16;                                                     
		f = bound(0, f, 255);
		return (unsigned char) f;
	}
	else
		return 0;
}

int particlefontwidth, particlefontheight, particlefontcellwidth, particlefontcellheight, particlefontrows, particlefontcols;
static void CL_Particle_PixelCoordsForTexnum(int texnum, int *basex, int *basey, int *width, int *height)
{
	*basex = (texnum % particlefontcols) * particlefontcellwidth;
	*basey = ((texnum / particlefontcols) % particlefontrows) * particlefontcellheight;
	*width = particlefontcellwidth;
	*height = particlefontcellheight;
}

static void setuptex(int texnum, unsigned char *data, unsigned char *particletexturedata)
{
	int basex, basey, w, h, y;
	CL_Particle_PixelCoordsForTexnum(texnum, &basex, &basey, &w, &h);
	if(w != PARTICLETEXTURESIZE || h != PARTICLETEXTURESIZE)
		Sys_Error("invalid particle texture size for autogenerating");
	for (y = 0;y < PARTICLETEXTURESIZE;y++)
		memcpy(particletexturedata + ((basey + y) * PARTICLEFONTSIZE + basex) * 4, data + y * PARTICLETEXTURESIZE * 4, PARTICLETEXTURESIZE * 4);
}

static void particletextureblotch(unsigned char *data, float radius, float red, float green, float blue, float alpha)
{
	int x, y;
	float cx, cy, dx, dy, f, iradius;
	unsigned char *d;
	cx = (lhrandom(radius + 1, PARTICLETEXTURESIZE - 2 - radius) + lhrandom(radius + 1, PARTICLETEXTURESIZE - 2 - radius)) * 0.5f;
	cy = (lhrandom(radius + 1, PARTICLETEXTURESIZE - 2 - radius) + lhrandom(radius + 1, PARTICLETEXTURESIZE - 2 - radius)) * 0.5f;
	iradius = 1.0f / radius;
	alpha *= (1.0f / 255.0f);
	for (y = 0;y < PARTICLETEXTURESIZE;y++)
	{
		for (x = 0;x < PARTICLETEXTURESIZE;x++)
		{
			dx = (x - cx);
			dy = (y - cy);
			f = (1.0f - sqrt(dx * dx + dy * dy) * iradius) * alpha;
			if (f > 0)
			{
				if (f > 1)
					f = 1;
				d = data + (y * PARTICLETEXTURESIZE + x) * 4;
				d[0] += (int)(f * (blue  - d[0]));
				d[1] += (int)(f * (green - d[1]));
				d[2] += (int)(f * (red   - d[2]));
			}
		}
	}
}

#if 0
static void particletextureclamp(unsigned char *data, int minr, int ming, int minb, int maxr, int maxg, int maxb)
{
	int i;
	for (i = 0;i < PARTICLETEXTURESIZE*PARTICLETEXTURESIZE;i++, data += 4)
	{
		data[0] = bound(minb, data[0], maxb);
		data[1] = bound(ming, data[1], maxg);
		data[2] = bound(minr, data[2], maxr);
	}
}
#endif

static void particletextureinvert(unsigned char *data)
{
	int i;
	for (i = 0;i < PARTICLETEXTURESIZE*PARTICLETEXTURESIZE;i++, data += 4)
	{
		data[0] = 255 - data[0];
		data[1] = 255 - data[1];
		data[2] = 255 - data[2];
	}
}

                                                                                              
static void R_InitBloodTextures (unsigned char *particletexturedata)
{
	int i, j, k, m;
	size_t datasize = PARTICLETEXTURESIZE*PARTICLETEXTURESIZE*4;
	unsigned char *data = (unsigned char *)Mem_Alloc(tempmempool, datasize);

	                  
	for (i = 0;i < 8;i++)
	{
		memset(data, 255, datasize);
		for (k = 0;k < 24;k++)
			particletextureblotch(data, PARTICLETEXTURESIZE/16, 96, 0, 0, 160);
		                                                        
		particletextureinvert(data);
		setuptex(tex_bloodparticle[i], data, particletexturedata);
	}

	               
	for (i = 0;i < 8;i++)
	{
		memset(data, 255, datasize);
		m = 8;
		for (j = 1;j < 10;j++)
			for (k = min(j, m - 1);k < m;k++)
				particletextureblotch(data, (float)j*PARTICLETEXTURESIZE/64.0f, 96, 0, 0, 320 - j * 8);
		                                                        
		particletextureinvert(data);
		setuptex(tex_blooddecal[i], data, particletexturedata);
	}

	Mem_Free(data);
}

                                                                             
                          

static void R_InitParticleTexture (void)
{
	int x, y, d, i, k, m;
	int basex, basey, w, h;
	float dx, dy, f, s1, t1, s2, t2;
	vec3_t light;
	char *buf;
	fs_offset_t filesize;
	char texturename[MAX_QPATH];
	skinframe_t *sf;

	                                                                     
	                                                                      
	                                                                      
	                                                                    
	                                                                         
	                                                                      
	                                                                        
	                                                             

#ifndef DUMPPARTICLEFONT
	decalskinframe = R_SkinFrame_LoadExternal("particles/particlefont.tga", TEXF_ALPHA | TEXF_FORCELINEAR | TEXF_RGBMULTIPLYBYALPHA, false);
	if (decalskinframe)
	{
		particlefonttexture = decalskinframe->base;
		                                     
		particlefontwidth = image_width;
		particlefontheight = image_height;
		particlefontcellwidth = image_width / 8;
		particlefontcellheight = image_height / 8;
		particlefontcols = 8;
		particlefontrows = 8;
	}
	else
#endif
	{
		unsigned char *particletexturedata = (unsigned char *)Mem_Alloc(tempmempool, PARTICLEFONTSIZE*PARTICLEFONTSIZE*4);
		size_t datasize = PARTICLETEXTURESIZE*PARTICLETEXTURESIZE*4;
		unsigned char *data = (unsigned char *)Mem_Alloc(tempmempool, datasize);
		unsigned char *noise1 = (unsigned char *)Mem_Alloc(tempmempool, PARTICLETEXTURESIZE*2*PARTICLETEXTURESIZE*2);
		unsigned char *noise2 = (unsigned char *)Mem_Alloc(tempmempool, PARTICLETEXTURESIZE*2*PARTICLETEXTURESIZE*2);

		particlefontwidth = particlefontheight = PARTICLEFONTSIZE;
		particlefontcellwidth = particlefontcellheight = PARTICLETEXTURESIZE;
		particlefontcols = 8;
		particlefontrows = 8;

		memset(particletexturedata, 255, PARTICLEFONTSIZE*PARTICLEFONTSIZE*4);

		        
		for (i = 0;i < 8;i++)
		{
			memset(data, 255, datasize);
			do
			{
				fractalnoise(noise1, PARTICLETEXTURESIZE*2, PARTICLETEXTURESIZE/8);
				fractalnoise(noise2, PARTICLETEXTURESIZE*2, PARTICLETEXTURESIZE/4);
				m = 0;
				for (y = 0;y < PARTICLETEXTURESIZE;y++)
				{
					dy = (y - 0.5f*PARTICLETEXTURESIZE) / (PARTICLETEXTURESIZE*0.5f-1);
					for (x = 0;x < PARTICLETEXTURESIZE;x++)
					{
						dx = (x - 0.5f*PARTICLETEXTURESIZE) / (PARTICLETEXTURESIZE*0.5f-1);
						d = (noise2[y*PARTICLETEXTURESIZE*2+x] - 128) * 3 + 192;
						if (d > 0)
							d = (int)(d * (1-(dx*dx+dy*dy)));
						d = (d * noise1[y*PARTICLETEXTURESIZE*2+x]) >> 7;
						d = bound(0, d, 255);
						data[(y*PARTICLETEXTURESIZE+x)*4+3] = (unsigned char) d;
						if (m < d)
							m = d;
					}
				}
			}
			while (m < 224);
			setuptex(tex_smoke[i], data, particletexturedata);
		}

		              
		memset(data, 255, datasize);
		for (y = 0;y < PARTICLETEXTURESIZE;y++)
		{
			dy = (y - 0.5f*PARTICLETEXTURESIZE) / (PARTICLETEXTURESIZE*0.5f-1);
			for (x = 0;x < PARTICLETEXTURESIZE;x++)
			{
				dx = (x - 0.5f*PARTICLETEXTURESIZE) / (PARTICLETEXTURESIZE*0.5f-1);
				f = 255.0f * (1.0 - 4.0f * fabs(10.0f - sqrt(dx*dx+dy*dy)));
				data[(y*PARTICLETEXTURESIZE+x)*4+3] = (int) (bound(0.0f, f, 255.0f));
			}
		}
		setuptex(tex_rainsplash, data, particletexturedata);

		                  
		memset(data, 255, datasize);
		for (y = 0;y < PARTICLETEXTURESIZE;y++)
		{
			dy = (y - 0.5f*PARTICLETEXTURESIZE) / (PARTICLETEXTURESIZE*0.5f-1);
			for (x = 0;x < PARTICLETEXTURESIZE;x++)
			{
				dx = (x - 0.5f*PARTICLETEXTURESIZE) / (PARTICLETEXTURESIZE*0.5f-1);
				d = (int)(256 * (1 - (dx*dx+dy*dy)));
				d = bound(0, d, 255);
				data[(y*PARTICLETEXTURESIZE+x)*4+3] = (unsigned char) d;
			}
		}
		setuptex(tex_particle, data, particletexturedata);

		       
		memset(data, 255, datasize);
		light[0] = 1;light[1] = 1;light[2] = 1;
		VectorNormalize(light);
		for (y = 0;y < PARTICLETEXTURESIZE;y++)
		{
			dy = (y - 0.5f*PARTICLETEXTURESIZE) / (PARTICLETEXTURESIZE*0.5f-1);
			                                                                     
			                                           
			if (dy > 0.5f)
				dy = (dy - 0.5f) * 2.0f;
			else
				dy = (dy - 0.5f) / 1.5f;
			for (x = 0;x < PARTICLETEXTURESIZE;x++)
			{
				dx = (x - 0.5f*PARTICLETEXTURESIZE) / (PARTICLETEXTURESIZE*0.5f-1);
				                              
				dx *= 2.0f;
				data[(y*PARTICLETEXTURESIZE+x)*4+3] = shadebubble(dx, dy, light);
			}
		}
		setuptex(tex_raindrop, data, particletexturedata);

		         
		memset(data, 255, datasize);
		light[0] = 1;light[1] = 1;light[2] = 1;
		VectorNormalize(light);
		for (y = 0;y < PARTICLETEXTURESIZE;y++)
		{
			dy = (y - 0.5f*PARTICLETEXTURESIZE) / (PARTICLETEXTURESIZE*0.5f-1);
			for (x = 0;x < PARTICLETEXTURESIZE;x++)
			{
				dx = (x - 0.5f*PARTICLETEXTURESIZE) / (PARTICLETEXTURESIZE*0.5f-1);
				data[(y*PARTICLETEXTURESIZE+x)*4+3] = shadebubble(dx, dy, light);
			}
		}
		setuptex(tex_bubble, data, particletexturedata);

		                                   
		R_InitBloodTextures (particletexturedata);

		                
		for (i = 0;i < 8;i++)
		{
			memset(data, 255, datasize);
			for (k = 0;k < 12;k++)
				particletextureblotch(data, PARTICLETEXTURESIZE/16, 0, 0, 0, 128);
			for (k = 0;k < 3;k++)
				particletextureblotch(data, PARTICLETEXTURESIZE/2, 0, 0, 0, 160);
			                                                        
			particletextureinvert(data);
			setuptex(tex_bulletdecal[i], data, particletexturedata);
		}

#ifdef DUMPPARTICLEFONT
		Image_WriteTGABGRA ("particles/particlefont.tga", PARTICLEFONTSIZE, PARTICLEFONTSIZE, particletexturedata);
#endif

		decalskinframe = R_SkinFrame_LoadInternalBGRA("particlefont", TEXF_ALPHA | TEXF_FORCELINEAR | TEXF_RGBMULTIPLYBYALPHA, particletexturedata, PARTICLEFONTSIZE, PARTICLEFONTSIZE, false);
		particlefonttexture = decalskinframe->base;

		Mem_Free(particletexturedata);
		Mem_Free(data);
		Mem_Free(noise1);
		Mem_Free(noise2);
	}
	for (i = 0;i < MAX_PARTICLETEXTURES;i++)
	{
		CL_Particle_PixelCoordsForTexnum(i, &basex, &basey, &w, &h);
		particletexture[i].texture = particlefonttexture;
		particletexture[i].s1 = (basex + 1) / (float)particlefontwidth;
		particletexture[i].t1 = (basey + 1) / (float)particlefontheight;
		particletexture[i].s2 = (basex + w - 1) / (float)particlefontwidth;
		particletexture[i].t2 = (basey + h - 1) / (float)particlefontheight;
	}

#ifndef DUMPPARTICLEFONT
	particletexture[tex_beam].texture = loadtextureimage(particletexturepool, "particles/nexbeam.tga", false, TEXF_ALPHA | TEXF_FORCELINEAR | TEXF_RGBMULTIPLYBYALPHA, true, vid.sRGB3D);
	if (!particletexture[tex_beam].texture)
#endif
	{
		unsigned char noise3[64][64], data2[64][16][4];
		          
		fractalnoise(&noise3[0][0], 64, 4);
		m = 0;
		for (y = 0;y < 64;y++)
		{
			dy = (y - 0.5f*64) / (64*0.5f-1);
			for (x = 0;x < 16;x++)
			{
				dx = (x - 0.5f*16) / (16*0.5f-2);
				d = (int)((1 - sqrt(fabs(dx))) * noise3[y][x]);
				data2[y][x][0] = data2[y][x][1] = data2[y][x][2] = (unsigned char) bound(0, d, 255);
				data2[y][x][3] = 255;
			}
		}

#ifdef DUMPPARTICLEFONT
		Image_WriteTGABGRA ("particles/nexbeam.tga", 64, 64, &data2[0][0][0]);
#endif
		particletexture[tex_beam].texture = R_LoadTexture2D(particletexturepool, "nexbeam", 16, 64, &data2[0][0][0], TEXTYPE_BGRA, TEXF_ALPHA | TEXF_FORCELINEAR | TEXF_RGBMULTIPLYBYALPHA, -1, NULL);
	}
	particletexture[tex_beam].s1 = 0;
	particletexture[tex_beam].t1 = 0;
	particletexture[tex_beam].s2 = 1;
	particletexture[tex_beam].t2 = 1;

	                                             
	buf = (char *) FS_LoadFile("particles/particlefont.txt", tempmempool, false, &filesize);
	if(buf)
	{
		const char *bufptr;
		bufptr = buf;
		for(;;)
		{
			if(!COM_ParseToken_Simple(&bufptr, true, false, true))
				break;
			if(!strcmp(com_token, "\n"))
				continue;              
			i = atoi(com_token);

			texturename[0] = 0;
			s1 = 0;
			t1 = 0;
			s2 = 1;
			t2 = 1;

			if (COM_ParseToken_Simple(&bufptr, true, false, true) && strcmp(com_token, "\n"))
			{
				strlcpy(texturename, com_token, sizeof(texturename));
				s1 = atof(com_token);
				if (COM_ParseToken_Simple(&bufptr, true, false, true) && strcmp(com_token, "\n"))
				{
					texturename[0] = 0;
					t1 = atof(com_token);
					if (COM_ParseToken_Simple(&bufptr, true, false, true) && strcmp(com_token, "\n"))
					{
						s2 = atof(com_token);
						if (COM_ParseToken_Simple(&bufptr, true, false, true) && strcmp(com_token, "\n"))
						{
							t2 = atof(com_token);
							strlcpy(texturename, "particles/particlefont.tga", sizeof(texturename));
							if (COM_ParseToken_Simple(&bufptr, true, false, true) && strcmp(com_token, "\n"))
								strlcpy(texturename, com_token, sizeof(texturename));
						}
					}
				}
				else
					s1 = 0;
			}
			if (!texturename[0])
			{
				Con_Printf("particles/particlefont.txt: syntax should be texnum x1 y1 x2 y2 texturename or texnum x1 y1 x2 y2 or texnum texturename\n");
				continue;
			}
			if (i < 0 || i >= MAX_PARTICLETEXTURES)
			{
				Con_Printf("particles/particlefont.txt: texnum %i outside valid range (0 to %i)\n", i, MAX_PARTICLETEXTURES);
				continue;
			}
			sf = R_SkinFrame_LoadExternal(texturename, TEXF_ALPHA | TEXF_FORCELINEAR | TEXF_RGBMULTIPLYBYALPHA, true);                                               
			if(!sf)
			{
				                                              
				continue;
			}
			particletexture[i].texture = sf->base;
			particletexture[i].s1 = s1;
			particletexture[i].t1 = t1;
			particletexture[i].s2 = s2;
			particletexture[i].t2 = t2;
		}
		Mem_Free(buf);
	}
}

static void r_part_start(void)
{
	int i;
	                                                             
	for (i = 0;i < 256;i++)
		particlepalette[i] = palette_rgb[i][0] * 65536 + palette_rgb[i][1] * 256 + palette_rgb[i][2];
	particletexturepool = R_AllocTexturePool();
	R_InitParticleTexture ();
	CL_Particles_LoadEffectInfo(NULL);
}

static void r_part_shutdown(void)
{
	R_FreeTexturePool(&particletexturepool);
}

static void r_part_newmap(void)
{
	if (decalskinframe)
		R_SkinFrame_MarkUsed(decalskinframe);
	CL_Particles_LoadEffectInfo(NULL);
}

unsigned short particle_elements[MESHQUEUE_TRANSPARENT_BATCHSIZE*6];
float particle_vertex3f[MESHQUEUE_TRANSPARENT_BATCHSIZE*12], particle_texcoord2f[MESHQUEUE_TRANSPARENT_BATCHSIZE*8], particle_color4f[MESHQUEUE_TRANSPARENT_BATCHSIZE*16];

void R_Particles_Init (void)
{
	int i;
	for (i = 0;i < MESHQUEUE_TRANSPARENT_BATCHSIZE;i++)
	{
		particle_elements[i*6+0] = i*4+0;
		particle_elements[i*6+1] = i*4+1;
		particle_elements[i*6+2] = i*4+2;
		particle_elements[i*6+3] = i*4+0;
		particle_elements[i*6+4] = i*4+2;
		particle_elements[i*6+5] = i*4+3;
	}

	Cvar_RegisterVariable(&r_drawparticles);
	Cvar_RegisterVariable(&r_drawparticles_drawdistance);
	Cvar_RegisterVariable(&r_drawparticles_nearclip_min);
	Cvar_RegisterVariable(&r_drawparticles_nearclip_max);
	Cvar_RegisterVariable(&r_drawdecals);
	Cvar_RegisterVariable(&r_drawdecals_drawdistance);
	R_RegisterModule("R_Particles", r_part_start, r_part_shutdown, r_part_newmap, NULL, NULL);
}

static void R_DrawDecal_TransparentCallback(const entity_render_t *ent, const rtlight_t *rtlight, int numsurfaces, int *surfacelist)
{
	int surfacelistindex;
	const decal_t *d;
	float *v3f, *t2f, *c4f;
	particletexture_t *tex;
	vec_t right[3], up[3], size, ca;
	float alphascale = (1.0f / 65536.0f) * cl_particles_alpha.value;

	RSurf_ActiveModelEntity(r_refdef.scene.worldentity, false, false, false);

	r_refdef.stats[r_stat_drawndecals] += numsurfaces;
                              
	GL_DepthMask(false);
	GL_DepthRange(0, 1);
	GL_PolygonOffset(0, 0);
	GL_DepthTest(true);
	GL_CullFace(GL_NONE);

	                                    
	for (surfacelistindex = 0;surfacelistindex < numsurfaces;surfacelistindex++)
	{
		d = cl.decals + surfacelist[surfacelistindex];

		                  
		c4f = particle_color4f + 16*surfacelistindex;
		ca = d->alpha * alphascale;
		                                             
		if (ca > 1.0f / 256.0f)
			ca = 1.0f / 256.0f;	
		if (r_refdef.fogenabled)
			ca *= RSurf_FogVertex(d->org);
		Vector4Set(c4f, d->color[0] * ca, d->color[1] * ca, d->color[2] * ca, 1);
		Vector4Copy(c4f, c4f + 4);
		Vector4Copy(c4f, c4f + 8);
		Vector4Copy(c4f, c4f + 12);

		                             
		size = d->size * cl_particles_size.value;
		VectorVectors(d->normal, right, up);
		VectorScale(right, size, right);
		VectorScale(up, size, up);
		v3f = particle_vertex3f + 12*surfacelistindex;
		v3f[ 0] = d->org[0] - right[0] - up[0];
		v3f[ 1] = d->org[1] - right[1] - up[1];
		v3f[ 2] = d->org[2] - right[2] - up[2];
		v3f[ 3] = d->org[0] - right[0] + up[0];
		v3f[ 4] = d->org[1] - right[1] + up[1];
		v3f[ 5] = d->org[2] - right[2] + up[2];
		v3f[ 6] = d->org[0] + right[0] + up[0];
		v3f[ 7] = d->org[1] + right[1] + up[1];
		v3f[ 8] = d->org[2] + right[2] + up[2];
		v3f[ 9] = d->org[0] + right[0] - up[0];
		v3f[10] = d->org[1] + right[1] - up[1];
		v3f[11] = d->org[2] + right[2] - up[2];

		                      
		tex = &particletexture[d->texnum];
		t2f = particle_texcoord2f + 8*surfacelistindex;
		t2f[0] = tex->s1;t2f[1] = tex->t2;
		t2f[2] = tex->s1;t2f[3] = tex->t1;
		t2f[4] = tex->s2;t2f[5] = tex->t1;
		t2f[6] = tex->s2;t2f[7] = tex->t2;
	}

	                                    
	                                                         
	GL_BlendFunc(GL_ZERO, GL_ONE_MINUS_SRC_COLOR);
	R_SetupShader_Generic(particletexture[63].texture, NULL, GL_MODULATE, 1, false, false, true);
	R_Mesh_PrepareVertices_Generic_Arrays(numsurfaces * 4, particle_vertex3f, particle_color4f, particle_texcoord2f);
	R_Mesh_Draw(0, numsurfaces * 4, 0, numsurfaces * 2, NULL, NULL, 0, particle_elements, NULL, 0);
}

void R_DrawDecals (void)
{
	int i;
	int drawdecals = r_drawdecals.integer;
	decal_t *decal;
	float frametime;
	float decalfade;
	float drawdist2;
	unsigned int killsequence = cl.decalsequence - bound(0, (unsigned int) cl_decals_max.integer, cl.decalsequence);

	frametime = bound(0, cl.time - cl.decals_updatetime, 1);
	cl.decals_updatetime = bound(cl.time - 1, cl.decals_updatetime + frametime, cl.time + 1);

	                                  
	if (!cl.num_decals)
		return;

	decalfade = frametime * 256 / cl_decals_fadetime.value;
	drawdist2 = r_drawdecals_drawdistance.value * r_refdef.view.quality;
	drawdist2 = drawdist2*drawdist2;

	for (i = 0, decal = cl.decals;i < cl.num_decals;i++, decal++)
	{
		if (!decal->typeindex)
			continue;

		if (killsequence > decal->decalsequence)
			goto killdecal;

		if (cl.time > decal->time2 + cl_decals_time.value)
		{
			decal->alpha -= decalfade;
			if (decal->alpha <= 0)
				goto killdecal;
		}

		if (decal->owner)
		{
			if (cl.entities[decal->owner].render.model == decal->ownermodel)
			{
				Matrix4x4_Transform(&cl.entities[decal->owner].render.matrix, decal->relativeorigin, decal->org);
				Matrix4x4_Transform3x3(&cl.entities[decal->owner].render.matrix, decal->relativenormal, decal->normal);
			}
			else
				goto killdecal;
		}

		if(cl_decals_visculling.integer && decal->clusterindex > -1000 && !CHECKPVSBIT(r_refdef.viewcache.world_pvsbits, decal->clusterindex))
			continue;

		if (!drawdecals)
			continue;

		if (DotProduct(r_refdef.view.origin, decal->normal) > DotProduct(decal->org, decal->normal) && VectorDistance2(decal->org, r_refdef.view.origin) < drawdist2 * (decal->size * decal->size))
			R_MeshQueue_AddTransparent(TRANSPARENTSORT_DISTANCE, decal->org, R_DrawDecal_TransparentCallback, NULL, i, NULL);
		continue;
killdecal:
		decal->typeindex = 0;
		if (cl.free_decal > i)
			cl.free_decal = i;
	}

	                                   
	while (cl.num_decals > 0 && cl.decals[cl.num_decals - 1].typeindex == 0)
		cl.num_decals--;

	if (cl.num_decals == cl.max_decals && cl.max_decals < MAX_DECALS)
	{
		decal_t *olddecals = cl.decals;
		cl.max_decals = min(cl.max_decals * 2, MAX_DECALS);
		cl.decals = (decal_t *) Mem_Alloc(cls.levelmempool, cl.max_decals * sizeof(decal_t));
		memcpy(cl.decals, olddecals, cl.num_decals * sizeof(decal_t));
		Mem_Free(olddecals);
	}

	r_refdef.stats[r_stat_totaldecals] = cl.num_decals;
}

static void R_DrawParticle_TransparentCallback(const entity_render_t *ent, const rtlight_t *rtlight, int numsurfaces, int *surfacelist)
{
	vec3_t vecorg, vecvel, baseright, baseup;
	int surfacelistindex;
	int batchstart, batchcount;
	const particle_t *p;
	pblend_t blendmode;
	rtexture_t *texture;
	float *v3f, *t2f, *c4f;
	particletexture_t *tex;
	float up2[3], v[3], right[3], up[3], fog, ifog, size, len, lenfactor, alpha;
                                                  
	float palpha, spintime, spinrad, spincos, spinsin, spinm1, spinm2, spinm3, spinm4;
	vec4_t colormultiplier;
	float minparticledist_start, minparticledist_end;
	qboolean dofade;

	RSurf_ActiveModelEntity(r_refdef.scene.worldentity, false, false, false);

	Vector4Set(colormultiplier, r_refdef.view.colorscale * (1.0 / 256.0f), r_refdef.view.colorscale * (1.0 / 256.0f), r_refdef.view.colorscale * (1.0 / 256.0f), cl_particles_alpha.value * (1.0 / 256.0f));

	r_refdef.stats[r_stat_particles] += numsurfaces;
                              
	GL_DepthMask(false);
	GL_DepthRange(0, 1);
	GL_PolygonOffset(0, 0);
	GL_DepthTest(true);
	GL_CullFace(GL_NONE);

	spintime = r_refdef.scene.time;

	minparticledist_start = DotProduct(r_refdef.view.origin, r_refdef.view.forward) + r_drawparticles_nearclip_min.value;
	minparticledist_end = DotProduct(r_refdef.view.origin, r_refdef.view.forward) + r_drawparticles_nearclip_max.value;
	dofade = (minparticledist_start < minparticledist_end);

	                                          
	for (surfacelistindex = 0, v3f = particle_vertex3f, t2f = particle_texcoord2f, c4f = particle_color4f;surfacelistindex < numsurfaces;surfacelistindex++, v3f += 3*4, t2f += 2*4, c4f += 4*4)
	{
		p = cl.particles + surfacelist[surfacelistindex];

		blendmode = (pblend_t)p->blendmode;
		palpha = p->alpha;
		if(dofade && p->orientation != PARTICLE_VBEAM && p->orientation != PARTICLE_HBEAM)
			palpha *= min(1, (DotProduct(p->org, r_refdef.view.forward)  - minparticledist_start) / (minparticledist_end - minparticledist_start));
		alpha = palpha * colormultiplier[3];
		                                             
		if (alpha > 1.0f)
			alpha = 1.0f;

		switch (blendmode)
		{
		case PBLEND_INVALID:
		case PBLEND_INVMOD:
			                                                                   
			if (r_refdef.fogenabled)
				alpha *= RSurf_FogVertex(p->org);
			                                                                                                             
			alpha *= 1.0f / 256.0f;
			c4f[0] = p->color[0] * alpha;
			c4f[1] = p->color[1] * alpha;
			c4f[2] = p->color[2] * alpha;
			c4f[3] = 0;
			break;
		case PBLEND_ADD:
			                                                                   
			if (r_refdef.fogenabled)
				alpha *= RSurf_FogVertex(p->org);
			                                                                                                             
			c4f[0] = p->color[0] * colormultiplier[0] * alpha;
			c4f[1] = p->color[1] * colormultiplier[1] * alpha;
			c4f[2] = p->color[2] * colormultiplier[2] * alpha;
			c4f[3] = 0;
			break;
		case PBLEND_ALPHA:
			c4f[0] = p->color[0] * colormultiplier[0];
			c4f[1] = p->color[1] * colormultiplier[1];
			c4f[2] = p->color[2] * colormultiplier[2];
			c4f[3] = alpha;
			                               
			if (particletype[p->typeindex].lighting)
			{
				float a[3], c[3], dir[3];
				vecorg[0] = p->org[0];
				vecorg[1] = p->org[1];
				vecorg[2] = p->org[2];
				R_CompleteLightPoint(a, c, dir, vecorg, LP_LIGHTMAP | LP_RTWORLD | LP_DYNLIGHT, r_refdef.scene.lightmapintensity, r_refdef.scene.ambientintensity);
				c4f[0] = p->color[0] * colormultiplier[0] * (a[0] + 0.25f * c[0]);
				c4f[1] = p->color[1] * colormultiplier[1] * (a[1] + 0.25f * c[1]);
				c4f[2] = p->color[2] * colormultiplier[2] * (a[2] + 0.25f * c[2]);
			}
			                       
			if (r_refdef.fogenabled)
			{
				fog = RSurf_FogVertex(p->org);
				ifog = 1 - fog;
				c4f[0] = c4f[0] * fog + r_refdef.fogcolor[0] * ifog;
				c4f[1] = c4f[1] * fog + r_refdef.fogcolor[1] * ifog;
				c4f[2] = c4f[2] * fog + r_refdef.fogcolor[2] * ifog;
			}
			                                                                                        
			VectorScale(c4f, alpha, c4f);
			break;
		}
		                                               
		Vector4Copy(c4f, c4f + 4);
		Vector4Copy(c4f, c4f + 8);
		Vector4Copy(c4f, c4f + 12);

		size = p->size * cl_particles_size.value;
		tex = &particletexture[p->texnum];
		switch(p->orientation)
		{
                          
		case PARTICLE_BILLBOARD:
			if (p->angle + p->spin)
			{
				spinrad = (p->angle + p->spin * (spintime - p->delayedspawn)) * (float)(M_PI / 180.0f);
				spinsin = sin(spinrad) * size;
				spincos = cos(spinrad) * size;
				spinm1 = -p->stretch * spincos;
				spinm2 = -spinsin;
				spinm3 = spinsin;
				spinm4 = -p->stretch * spincos;
				VectorMAM(spinm1, r_refdef.view.left, spinm2, r_refdef.view.up, right);
				VectorMAM(spinm3, r_refdef.view.left, spinm4, r_refdef.view.up, up);
			}
			else
			{
				VectorScale(r_refdef.view.left, -size * p->stretch, right);
				VectorScale(r_refdef.view.up, size, up);
			}

			v3f[ 0] = p->org[0] - right[0] - up[0];
			v3f[ 1] = p->org[1] - right[1] - up[1];
			v3f[ 2] = p->org[2] - right[2] - up[2];
			v3f[ 3] = p->org[0] - right[0] + up[0];
			v3f[ 4] = p->org[1] - right[1] + up[1];
			v3f[ 5] = p->org[2] - right[2] + up[2];
			v3f[ 6] = p->org[0] + right[0] + up[0];
			v3f[ 7] = p->org[1] + right[1] + up[1];
			v3f[ 8] = p->org[2] + right[2] + up[2];
			v3f[ 9] = p->org[0] + right[0] - up[0];
			v3f[10] = p->org[1] + right[1] - up[1];
			v3f[11] = p->org[2] + right[2] - up[2];
			t2f[0] = tex->s1;t2f[1] = tex->t2;
			t2f[2] = tex->s1;t2f[3] = tex->t1;
			t2f[4] = tex->s2;t2f[5] = tex->t1;
			t2f[6] = tex->s2;t2f[7] = tex->t2;
			break;
		case PARTICLE_ORIENTED_DOUBLESIDED:
			vecvel[0] = p->vel[0];
			vecvel[1] = p->vel[1];
			vecvel[2] = p->vel[2];
			VectorVectors(vecvel, baseright, baseup);
			if (p->angle + p->spin)
			{
				spinrad = (p->angle + p->spin * (spintime - p->delayedspawn)) * (float)(M_PI / 180.0f);
				spinsin = sin(spinrad) * size;
				spincos = cos(spinrad) * size;
				spinm1 = p->stretch * spincos;
				spinm2 = -spinsin;
				spinm3 = spinsin;
				spinm4 = p->stretch * spincos;
				VectorMAM(spinm1, baseright, spinm2, baseup, right);
				VectorMAM(spinm3, baseright, spinm4, baseup, up);
			}
			else
			{
				VectorScale(baseright, size * p->stretch, right);
				VectorScale(baseup, size, up);
			}
			v3f[ 0] = p->org[0] - right[0] - up[0];
			v3f[ 1] = p->org[1] - right[1] - up[1];
			v3f[ 2] = p->org[2] - right[2] - up[2];
			v3f[ 3] = p->org[0] - right[0] + up[0];
			v3f[ 4] = p->org[1] - right[1] + up[1];
			v3f[ 5] = p->org[2] - right[2] + up[2];
			v3f[ 6] = p->org[0] + right[0] + up[0];
			v3f[ 7] = p->org[1] + right[1] + up[1];
			v3f[ 8] = p->org[2] + right[2] + up[2];
			v3f[ 9] = p->org[0] + right[0] - up[0];
			v3f[10] = p->org[1] + right[1] - up[1];
			v3f[11] = p->org[2] + right[2] - up[2];
			t2f[0] = tex->s1;t2f[1] = tex->t2;
			t2f[2] = tex->s1;t2f[3] = tex->t1;
			t2f[4] = tex->s2;t2f[5] = tex->t1;
			t2f[6] = tex->s2;t2f[7] = tex->t2;
			break;
		case PARTICLE_SPARK:
			len = VectorLength(p->vel);
			VectorNormalize2(p->vel, up);
			lenfactor = p->stretch * 0.04 * len;
			if(lenfactor < size * 0.5)
				lenfactor = size * 0.5;
			VectorMA(p->org, -lenfactor, up, v);
			VectorMA(p->org,  lenfactor, up, up2);
			R_CalcBeam_Vertex3f(v3f, v, up2, size);
			t2f[0] = tex->s1;t2f[1] = tex->t2;
			t2f[2] = tex->s1;t2f[3] = tex->t1;
			t2f[4] = tex->s2;t2f[5] = tex->t1;
			t2f[6] = tex->s2;t2f[7] = tex->t2;
			break;
		case PARTICLE_VBEAM:
			R_CalcBeam_Vertex3f(v3f, p->org, p->vel, size);
			VectorSubtract(p->vel, p->org, up);
			VectorNormalize(up);
			v[0] = DotProduct(p->org, up) * (1.0f / 64.0f) * p->stretch;
			v[1] = DotProduct(p->vel, up) * (1.0f / 64.0f) * p->stretch;
			t2f[0] = tex->s2;t2f[1] = v[0];
			t2f[2] = tex->s1;t2f[3] = v[0];
			t2f[4] = tex->s1;t2f[5] = v[1];
			t2f[6] = tex->s2;t2f[7] = v[1];
			break;
		case PARTICLE_HBEAM:
			R_CalcBeam_Vertex3f(v3f, p->org, p->vel, size);
			VectorSubtract(p->vel, p->org, up);
			VectorNormalize(up);
			v[0] = DotProduct(p->org, up) * (1.0f / 64.0f) * p->stretch;
			v[1] = DotProduct(p->vel, up) * (1.0f / 64.0f) * p->stretch;
			t2f[0] = v[0];t2f[1] = tex->t1;
			t2f[2] = v[0];t2f[3] = tex->t2;
			t2f[4] = v[1];t2f[5] = tex->t2;
			t2f[6] = v[1];t2f[7] = tex->t1;
			break;
		}
	}

	                                                                 
	blendmode = PBLEND_INVALID;
	texture = NULL;
	batchstart = 0;
	batchcount = 0;
	R_Mesh_PrepareVertices_Generic_Arrays(numsurfaces * 4, particle_vertex3f, particle_color4f, particle_texcoord2f);
	for (surfacelistindex = 0;surfacelistindex < numsurfaces;)
	{
		p = cl.particles + surfacelist[surfacelistindex];

		if (texture != particletexture[p->texnum].texture)
		{
			texture = particletexture[p->texnum].texture;
			R_SetupShader_Generic(texture, NULL, GL_MODULATE, 1, false, false, false);
		}

		if (p->blendmode == PBLEND_INVMOD)
		{
			                                       
			GL_BlendFunc(GL_ZERO, GL_ONE_MINUS_SRC_COLOR);
			                                             
			batchstart = surfacelistindex++;
			for (;surfacelistindex < numsurfaces;surfacelistindex++)
			{
				p = cl.particles + surfacelist[surfacelistindex];
				if (p->blendmode != PBLEND_INVMOD || texture != particletexture[p->texnum].texture)
					break;
			}
		}
		else
		{
			                                        
			                                                                  
			GL_BlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
			                                             
			batchstart = surfacelistindex++;
			for (;surfacelistindex < numsurfaces;surfacelistindex++)
			{
				p = cl.particles + surfacelist[surfacelistindex];
				if (p->blendmode == PBLEND_INVMOD || texture != particletexture[p->texnum].texture)
					break;
			}
		}

		batchcount = surfacelistindex - batchstart;
		R_Mesh_Draw(batchstart * 4, batchcount * 4, batchstart * 2, batchcount * 2, NULL, NULL, 0, particle_elements, NULL, 0);
	}
}

void R_DrawParticles (void)
{
	int i, a;
	int drawparticles = r_drawparticles.integer;
	float minparticledist_start;
	particle_t *p;
	float gravity, frametime, f, dist, oldorg[3], decaldir[3];
	float drawdist2;
	int hitent;
	trace_t trace;
	qboolean update;

	frametime = bound(0, cl.time - cl.particles_updatetime, 1);
	cl.particles_updatetime = bound(cl.time - 1, cl.particles_updatetime + frametime, cl.time + 1);

	                                  
	if (!cl.num_particles)
		return;

	minparticledist_start = DotProduct(r_refdef.view.origin, r_refdef.view.forward) + r_drawparticles_nearclip_min.value;
	gravity = frametime * cl.movevars_gravity;
	update = frametime > 0;
	drawdist2 = r_drawparticles_drawdistance.value * r_refdef.view.quality;
	drawdist2 = drawdist2*drawdist2;

	for (i = 0, p = cl.particles;i < cl.num_particles;i++, p++)
	{
		if (!p->typeindex)
		{
			if (cl.free_particle > i)
				cl.free_particle = i;
			continue;
		}

		if (update)
		{
			if (p->delayedspawn > cl.time)
				continue;

			p->size += p->sizeincrease * frametime;
			p->alpha -= p->alphafade * frametime;

			if (p->alpha <= 0 || p->die <= cl.time)
				goto killparticle;

			if (p->orientation != PARTICLE_VBEAM && p->orientation != PARTICLE_HBEAM && frametime > 0)
			{
				if (p->liquidfriction && cl_particles_collisions.integer && (CL_PointSuperContents(p->org) & SUPERCONTENTS_LIQUIDSMASK))
				{
					if (p->typeindex == pt_blood)
						p->size += frametime * 8;
					else
						p->vel[2] -= p->gravity * gravity;
					f = 1.0f - min(p->liquidfriction * frametime, 1);
					VectorScale(p->vel, f, p->vel);
				}
				else
				{
					p->vel[2] -= p->gravity * gravity;
					if (p->airfriction)
					{
						f = 1.0f - min(p->airfriction * frametime, 1);
						VectorScale(p->vel, f, p->vel);
					}
				}

				VectorCopy(p->org, oldorg);
				VectorMA(p->org, frametime, p->vel, p->org);
                                                       
				if (p->bounce && cl_particles_collisions.integer && VectorLength(p->vel))
				{
					trace = CL_TraceLine(oldorg, p->org, MOVE_NORMAL, NULL, SUPERCONTENTS_SOLID | ((p->typeindex == pt_rain || p->typeindex == pt_snow) ? SUPERCONTENTS_LIQUIDSMASK : 0), 0, 0, collision_extendmovelength.value, true, false, &hitent, false, false);
					                                                                   
					                                                    
					                           
					if (trace.hitq3surfaceflags & Q3SURFACEFLAG_NOIMPACT || ((trace.startsupercontents | trace.hitsupercontents) & SUPERCONTENTS_NODROP) || (trace.startsupercontents & SUPERCONTENTS_SOLID))
						goto killparticle;
					VectorCopy(trace.endpos, p->org);
					                                      
					if (trace.fraction < 1)
					{
						VectorCopy(trace.endpos, p->org);

						if (p->staintexnum >= 0)
						{
							                          
							if (!(trace.hitq3surfaceflags & Q3SURFACEFLAG_NOMARKS))
							{
								R_Stain(p->org, 16,
									p->staincolor[0], p->staincolor[1], p->staincolor[2], (int)(p->stainalpha * p->stainsize * (1.0f / 160.0f)),
									p->staincolor[0], p->staincolor[1], p->staincolor[2], (int)(p->stainalpha * p->stainsize * (1.0f / 160.0f)));
								if (cl_decals.integer)
								{
									                                     
									a = 0xFFFFFF ^ (p->staincolor[0]*65536+p->staincolor[1]*256+p->staincolor[2]);
									if (cl_decals_newsystem_bloodsmears.integer)
									{
										VectorCopy(p->vel, decaldir);
										VectorNormalize(decaldir);
									}
									else
										VectorCopy(trace.plane.normal, decaldir);
									CL_SpawnDecalParticleForSurface(hitent, p->org, decaldir, a, a, p->staintexnum, p->stainsize, p->stainalpha);                                               
								}
							}
						}

						if (p->typeindex == pt_blood)
						{
							                          
							if (trace.hitq3surfaceflags & Q3SURFACEFLAG_NOMARKS)
								goto killparticle;
							if(p->staintexnum == -1)                                        
							{
								R_Stain(p->org, 16, 64, 16, 16, (int)(p->alpha * p->size * (1.0f / 80.0f)), 64, 32, 32, (int)(p->alpha * p->size * (1.0f / 80.0f)));
								if (cl_decals.integer)
								{
									                                     
									if (cl_decals_newsystem_bloodsmears.integer)
									{
										VectorCopy(p->vel, decaldir);
										VectorNormalize(decaldir);
									}
									else
										VectorCopy(trace.plane.normal, decaldir);
									CL_SpawnDecalParticleForSurface(hitent, p->org, decaldir, p->color[0] * 65536 + p->color[1] * 256 + p->color[2], p->color[0] * 65536 + p->color[1] * 256 + p->color[2], tex_blooddecal[rand()&7], p->size * lhrandom(cl_particles_blood_decal_scalemin.value, cl_particles_blood_decal_scalemax.value), cl_particles_blood_decal_alpha.value * 768);
								}
							}
							goto killparticle;
						}
						else if (p->bounce < 0)
						{
							                                   
							goto killparticle;
						}
						else
						{
							                                   
							dist = DotProduct(p->vel, trace.plane.normal) * -p->bounce;
							VectorMA(p->vel, dist, trace.plane.normal, p->vel);
						}
					}
				}

				if (VectorLength2(p->vel) < 0.03)
				{
					if(p->orientation == PARTICLE_SPARK)                                                                          
						goto killparticle;
					VectorClear(p->vel);
				}
			}

			if (p->typeindex != pt_static)
			{
				switch (p->typeindex)
				{
				case pt_entityparticle:
					                                                        
					if (p->time2)
						goto killparticle;
					else
						p->time2 = 1;
					break;
				case pt_blood:
					a = CL_PointSuperContents(p->org);
					if (a & (SUPERCONTENTS_SOLID | SUPERCONTENTS_LAVA | SUPERCONTENTS_NODROP))
						goto killparticle;
					break;
				case pt_bubble:
					a = CL_PointSuperContents(p->org);
					if (!(a & (SUPERCONTENTS_WATER | SUPERCONTENTS_SLIME)))
						goto killparticle;
					break;
				case pt_rain:
					a = CL_PointSuperContents(p->org);
					if (a & (SUPERCONTENTS_SOLID | SUPERCONTENTS_LIQUIDSMASK))
						goto killparticle;
					break;
				case pt_snow:
					if (cl.time > p->time2)
					{
						               
						p->time2 = cl.time + (rand() & 3) * 0.1;
						p->vel[0] = p->vel[0] * 0.9f + lhrandom(-32, 32);
						p->vel[1] = p->vel[0] * 0.9f + lhrandom(-32, 32);
					}
					a = CL_PointSuperContents(p->org);
					if (a & (SUPERCONTENTS_SOLID | SUPERCONTENTS_LIQUIDSMASK))
						goto killparticle;
					break;
				default:
					break;
				}
			}
		}
		else if (p->delayedspawn > cl.time)
			continue;
		if (!drawparticles)
			continue;
		                                                                    
		                                                        
		                                                               
		switch(p->typeindex)
		{
		case pt_beam:
			                        
			R_MeshQueue_AddTransparent(TRANSPARENTSORT_DISTANCE, p->sortorigin, R_DrawParticle_TransparentCallback, NULL, i, NULL);
			break;
		default:
			if(cl_particles_visculling.integer)
				if (!r_refdef.viewcache.world_novis)
					if(r_refdef.scene.worldmodel && r_refdef.scene.worldmodel->brush.PointInLeaf)
					{
						mleaf_t *leaf = r_refdef.scene.worldmodel->brush.PointInLeaf(r_refdef.scene.worldmodel, p->org);
						if(leaf)
							if(!CHECKPVSBIT(r_refdef.viewcache.world_pvsbits, leaf->clusterindex))
								continue;
					}
			                                                                                   
			if (DotProduct(p->org, r_refdef.view.forward) >= minparticledist_start && VectorDistance2(p->org, r_refdef.view.origin) < drawdist2 * (p->size * p->size))
				R_MeshQueue_AddTransparent(TRANSPARENTSORT_DISTANCE, p->sortorigin, R_DrawParticle_TransparentCallback, NULL, i, NULL);
			break;
		}

		continue;
killparticle:
		p->typeindex = 0;
		if (cl.free_particle > i)
			cl.free_particle = i;
	}

	                                      
	while (cl.num_particles > 0 && cl.particles[cl.num_particles - 1].typeindex == 0)
		cl.num_particles--;

	if (cl.num_particles == cl.max_particles && cl.max_particles < MAX_PARTICLES)
	{
		particle_t *oldparticles = cl.particles;
		cl.max_particles = min(cl.max_particles * 2, MAX_PARTICLES);
		cl.particles = (particle_t *) Mem_Alloc(cls.levelmempool, cl.max_particles * sizeof(particle_t));
		memcpy(cl.particles, oldparticles, cl.num_particles * sizeof(particle_t));
		Mem_Free(oldparticles);
	}
}
