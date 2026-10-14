
#ifndef IMAGE_H
#define IMAGE_H

extern int image_width, image_height;


                                                                            
                                                                              
                                                                        
                                                                        
void Image_CopyMux(unsigned char *outpixels, const unsigned char *inpixels, int inputwidth, int inputheight, qboolean inputflipx, qboolean inputflipy, qboolean inputflipdiagonal, int numoutputcomponents, int numinputcomponents, int *outputinputcomponentindices);

                                                                    
void Image_GammaRemapRGB(const unsigned char *in, unsigned char *out, int pixels, const unsigned char *gammar, const unsigned char *gammag, const unsigned char *gammab);

                                                                  
void Image_Copy8bitBGRA(const unsigned char *in, unsigned char *out, int pixels, const unsigned int *pal);

void Image_StripImageExtension (const char *in, char *out, size_t size_out);

                                                                
unsigned char *LoadTGA_BGRA (const unsigned char *f, int filesize, int *miplevel);

                                 
unsigned char *loadimagepixelsbgra (const char *filename, qboolean complain, qboolean allowFixtrans, qboolean convertsRGB, int *miplevel);

                                                                              
qboolean LoadPCX_QWSkin(const unsigned char *f, int filesize, unsigned char *pixels, int outwidth, int outheight);

                                                                    
qboolean LoadPCX_PaletteOnly(const unsigned char *f, int filesize, unsigned char *palette768b);

                                          
qboolean LoadWAL_GetMetadata(const unsigned char *f, int filesize, int *retwidth, int *retheight, int *retflags, int *retvalue, int *retcontents, char *retanimname32c);

                                
rtexture_t *loadtextureimage (rtexturepool_t *pool, const char *filename, qboolean complain, int flags, qboolean allowFixtrans, qboolean sRGB);

                                             
qboolean Image_WriteTGABGR_preflipped (const char *filename, int width, int height, const unsigned char *data);

                                      
qboolean Image_WriteTGABGRA (const char *filename, int width, int height, const unsigned char *data);

                                                    
void Image_Resample32(const void *indata, int inwidth, int inheight, int indepth, void *outdata, int outwidth, int outheight, int outdepth, int quality);

                                                                    
void Image_MipReduce32(const unsigned char *in, unsigned char *out, int *width, int *height, int *depth, int destwidth, int destheight, int destdepth);

void Image_HeightmapToNormalmap_BGRA(const unsigned char *inpixels, unsigned char *outpixels, int width, int height, int clamp, float bumpscale);

                                                                                     
void Image_FixTransparentPixels_f(void);
extern cvar_t r_fixtrans_auto;

#define Image_LinearFloatFromsRGBFloat(c) (((c) <= 0.04045f) ? (c) * (1.0f / 12.92f) : (float)pow(((c) + 0.055f)*(1.0f/1.055f), 2.4f))
#define Image_sRGBFloatFromLinearFloat(c) (((c) < 0.0031308f) ? (c) * 12.92f : 1.055f * (float)pow((c), 1.0f/2.4f) - 0.055f)
#define Image_LinearFloatFromsRGB(c) Image_LinearFloatFromsRGBFloat((c) * (1.0f / 255.0f))
#define Image_sRGBFloatFromLinear(c) Image_sRGBFloatFromLinearFloat((c) * (1.0f / 255.0f))
#define Image_sRGBFloatFromLinear_Lightmap(c) Image_sRGBFloatFromLinearFloat((c) * (2.0f / 255.0f)) * 0.5f

void Image_MakeLinearColorsFromsRGB(unsigned char *pout, const unsigned char *pin, int numpixels);
void Image_MakesRGBColorsFromLinear_Lightmap(unsigned char *pout, const unsigned char *pin, int numpixels);

#endif

