
#include "quakedef.h"
#include "image.h"

cvar_t r_lightningbeam_thickness = {CVAR_SAVE, "r_lightningbeam_thickness", "8", "thickness of the lightning beam effect"};
cvar_t r_lightningbeam_scroll = {CVAR_SAVE, "r_lightningbeam_scroll", "5", "speed of texture scrolling on the lightning beam effect"};
cvar_t r_lightningbeam_repeatdistance = {CVAR_SAVE, "r_lightningbeam_repeatdistance", "128", "how far to stretch the texture along the lightning beam effect"};
cvar_t r_lightningbeam_color_red = {CVAR_SAVE, "r_lightningbeam_color_red", "1", "color of the lightning beam effect"};
cvar_t r_lightningbeam_color_green = {CVAR_SAVE, "r_lightningbeam_color_green", "1", "color of the lightning beam effect"};
cvar_t r_lightningbeam_color_blue = {CVAR_SAVE, "r_lightningbeam_color_blue", "1", "color of the lightning beam effect"};
cvar_t r_lightningbeam_qmbtexture = {CVAR_SAVE, "r_lightningbeam_qmbtexture", "0", "load the qmb textures/particles/lightning.pcx texture instead of generating one, can look better"};

static texture_t cl_beams_externaltexture;
static texture_t cl_beams_builtintexture;

static void r_lightningbeams_start(void)
{
	memset(&cl_beams_externaltexture, 0, sizeof(cl_beams_externaltexture));
	memset(&cl_beams_builtintexture, 0, sizeof(cl_beams_builtintexture));
}

static void CL_Beams_SetupExternalTexture(void)
{
	if (Mod_LoadTextureFromQ3Shader(&cl_beams_externaltexture, "textures/particles/lightning", false, false, TEXF_ALPHA | TEXF_FORCELINEAR))
		cl_beams_externaltexture.basematerialflags = cl_beams_externaltexture.currentmaterialflags = MATERIALFLAG_WALL | MATERIALFLAG_ADD | MATERIALFLAG_BLENDED | MATERIALFLAG_NOCULLFACE;
	else
		Cvar_SetValueQuick(&r_lightningbeam_qmbtexture, false);
}

static void CL_Beams_SetupBuiltinTexture(void)
{
	                                                        
	int texwidth = 128;
	int texheight = 64;
	float r, g, b, intensity, thickness = texheight * 0.25f, border = thickness + 2.0f, ithickness = 1.0f / thickness, center, n;
	int x, y;
	unsigned char *data;
	skinframe_t *skinframe;
	float centersamples[17][2];

	                                                   
	for (x = 0; x < 16; x++)
	{
		centersamples[x][0] = lhrandom(border, texheight - border);
		centersamples[x][1] = lhrandom(0.2f, 1.00f);
	}
	centersamples[16][0] = centersamples[0][0];
	centersamples[16][1] = centersamples[0][1];

	data = (unsigned char *)Mem_Alloc(tempmempool, texwidth * texheight * 4);

	                                                          
	for (x = 0; x < texwidth; x++)
	{
		r = x * 16.0f / texwidth;
		y = (int)r;
		g = r - y;
		center = centersamples[y][0] * (1.0f - g) + centersamples[y+1][0] * g;
		n = centersamples[y][1] * (1.0f - g) + centersamples[y + 1][1] * g;
		for (y = 0; y < texheight; y++)
		{
			intensity = 1.0f - fabs((y - center) * ithickness);
			if (intensity > 0)
			{
				intensity = pow(intensity * n, 2);
				r = intensity * 1.000f * 255.0f;
				g = intensity * 2.000f * 255.0f;
				b = intensity * 4.000f * 255.0f;
				data[(y * texwidth + x) * 4 + 2] = (unsigned char)(bound(0, r, 255));
				data[(y * texwidth + x) * 4 + 1] = (unsigned char)(bound(0, g, 255));
				data[(y * texwidth + x) * 4 + 0] = (unsigned char)(bound(0, b, 255));
			}
			else
				intensity = 0.0f;
			data[(y * texwidth + x) * 4 + 3] = (unsigned char)255;
		}
	}

	skinframe = R_SkinFrame_LoadInternalBGRA("lightningbeam", TEXF_FORCELINEAR, data, texwidth, texheight, false);
	Mod_LoadCustomMaterial(&cl_beams_builtintexture, "cl_beams_builtintexture", 0, MATERIALFLAG_WALL | MATERIALFLAG_ADD | MATERIALFLAG_BLENDED | MATERIALFLAG_NOCULLFACE, skinframe);
	Mem_Free(data);
}

static void r_lightningbeams_shutdown(void)
{
	memset(&cl_beams_externaltexture, 0, sizeof(cl_beams_externaltexture));
	memset(&cl_beams_builtintexture, 0, sizeof(cl_beams_builtintexture));
}

static void r_lightningbeams_newmap(void)
{
	if (cl_beams_externaltexture.currentskinframe)
		R_SkinFrame_MarkUsed(cl_beams_externaltexture.currentskinframe);
	if (cl_beams_builtintexture.currentskinframe)
		R_SkinFrame_MarkUsed(cl_beams_builtintexture.currentskinframe);
}

void R_LightningBeams_Init(void)
{
	Cvar_RegisterVariable(&r_lightningbeam_thickness);
	Cvar_RegisterVariable(&r_lightningbeam_scroll);
	Cvar_RegisterVariable(&r_lightningbeam_repeatdistance);
	Cvar_RegisterVariable(&r_lightningbeam_color_red);
	Cvar_RegisterVariable(&r_lightningbeam_color_green);
	Cvar_RegisterVariable(&r_lightningbeam_color_blue);
	Cvar_RegisterVariable(&r_lightningbeam_qmbtexture);
	R_RegisterModule("R_LightningBeams", r_lightningbeams_start, r_lightningbeams_shutdown, r_lightningbeams_newmap, NULL, NULL);
}

static void CL_Beam_AddQuad(dp_model_t *mod, msurface_t *surf, const vec3_t start, const vec3_t end, const vec3_t offset, float t1, float t2)
{
	int e0, e1, e2, e3;
	vec3_t n;
	vec3_t dir;
	float c[4];

	Vector4Set(c, r_lightningbeam_color_red.value, r_lightningbeam_color_green.value, r_lightningbeam_color_blue.value, 1.0f);

	VectorSubtract(end, start, dir);
	CrossProduct(dir, offset, n);
	VectorNormalize(n);

	e0 = Mod_Mesh_IndexForVertex(mod, surf, start[0] + offset[0], start[1] + offset[1], start[2] + offset[2], n[0], n[1], n[2], t1, 0, 0, 0, c[0], c[1], c[2], c[3]);
	e1 = Mod_Mesh_IndexForVertex(mod, surf, start[0] - offset[0], start[1] - offset[1], start[2] - offset[2], n[0], n[1], n[2], t1, 1, 0, 0, c[0], c[1], c[2], c[3]);
	e2 = Mod_Mesh_IndexForVertex(mod, surf, end[0] - offset[0], end[1] - offset[1], end[2] - offset[2], n[0], n[1], n[2], t2, 1, 0, 0, c[0], c[1], c[2], c[3]);
	e3 = Mod_Mesh_IndexForVertex(mod, surf, end[0] + offset[0], end[1] + offset[1], end[2] + offset[2], n[0], n[1], n[2], t2, 0, 0, 0, c[0], c[1], c[2], c[3]);
	Mod_Mesh_AddTriangle(mod, surf, e0, e1, e2);
	Mod_Mesh_AddTriangle(mod, surf, e0, e2, e3);
}

void CL_Beam_AddPolygons(const beam_t *b)
{
	vec3_t beamdir, right, up, offset, start, end;
	vec_t beamscroll = r_refdef.scene.time * -r_lightningbeam_scroll.value;
	vec_t beamrepeatscale = 1.0f / r_lightningbeam_repeatdistance.value;
	float length, t1, t2;
	dp_model_t *mod;
	msurface_t *surf;

	if (r_lightningbeam_qmbtexture.integer && cl_beams_externaltexture.currentskinframe == NULL)
		CL_Beams_SetupExternalTexture();
	if (!r_lightningbeam_qmbtexture.integer && cl_beams_builtintexture.currentskinframe == NULL)
		CL_Beams_SetupBuiltinTexture();

	                                                            
	                        
	CL_Beam_CalculatePositions(b, start, end);
	VectorSubtract(end, start, beamdir);
	                                   
	length = sqrt(DotProduct(beamdir, beamdir));
	                                                             
	t1 = 1.0f / length;
	                                        
	VectorScale(beamdir, t1, beamdir);

	                                                                                        
	                                             
	VectorSubtract(r_refdef.view.origin, start, up);
	                                                             
	                                                                   
	t1 = -DotProduct(up, beamdir);
	VectorMA(up, t1, beamdir, up);
	                                                                        
	CrossProduct(beamdir, up, right);
	                                               
	VectorNormalize(right);
	VectorNormalize(up);

	                                                                           
	t1 = beamscroll;
	t1 = t1 - (int)t1;
	t2 = t1 + beamrepeatscale * length;

	                                                
	         
	        
	         
	        
	         
	                                                                       
	                                                             
	                                                                      
	               

	mod = &cl_meshentitymodels[MESH_PARTICLES];
	surf = Mod_Mesh_AddSurface(mod, r_lightningbeam_qmbtexture.integer ? &cl_beams_externaltexture : &cl_beams_builtintexture);
	            
	VectorM(r_lightningbeam_thickness.value, right, offset);
	CL_Beam_AddQuad(mod, surf, start, end, offset, t1, t2);
	            
	VectorMAM(r_lightningbeam_thickness.value * 0.70710681f, right, r_lightningbeam_thickness.value * 0.70710681f, up, offset);
	CL_Beam_AddQuad(mod, surf, start, end, offset, t1 + 0.33f, t2 + 0.33f);
	            
	VectorMAM(r_lightningbeam_thickness.value * 0.70710681f, right, r_lightningbeam_thickness.value * -0.70710681f, up, offset);
	CL_Beam_AddQuad(mod, surf, start, end, offset, t1 + 0.66f, t2 + 0.66f);
}
