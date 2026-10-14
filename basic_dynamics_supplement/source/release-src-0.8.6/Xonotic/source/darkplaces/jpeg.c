  
                                    

                                                              
                                                            
                                                               
                                                       

                                                                
                                                               
                                                     

                                                     

                                                                  
                                           

                                
                             
                             

  


#include "quakedef.h"
#include "image.h"
#include "jpeg.h"
#include "image_png.h"

cvar_t sv_writepicture_quality = {CVAR_SAVE, "sv_writepicture_quality", "10", "WritePicture quality offset (higher means better quality, but slower)"};
cvar_t r_texture_jpeg_fastpicmip = {CVAR_SAVE, "r_texture_jpeg_fastpicmip", "1", "perform gl_picmip during decompression for JPEG files (faster)"};

                                                    
#ifdef WIN32
typedef unsigned char jboolean;
#else
typedef int jboolean;
#endif

#ifdef LINK_TO_LIBJPEG
#include <jpeglib.h>
#define qjpeg_create_compress jpeg_create_compress
#define qjpeg_create_decompress jpeg_create_decompress
#define qjpeg_destroy_compress jpeg_destroy_compress
#define qjpeg_destroy_decompress jpeg_destroy_decompress
#define qjpeg_finish_compress jpeg_finish_compress
#define qjpeg_finish_decompress jpeg_finish_decompress
#define qjpeg_resync_to_restart jpeg_resync_to_restart
#define qjpeg_read_header jpeg_read_header
#define qjpeg_read_scanlines jpeg_read_scanlines
#define qjpeg_set_defaults jpeg_set_defaults
#define qjpeg_set_quality jpeg_set_quality
#define qjpeg_start_compress jpeg_start_compress
#define qjpeg_start_decompress jpeg_start_decompress
#define qjpeg_std_error jpeg_std_error
#define qjpeg_write_scanlines jpeg_write_scanlines
#define qjpeg_simple_progression jpeg_simple_progression
#define jpeg_dll true
#else
  
                                                                 

                                              

                                                                
                                                                

                                                                 
  

typedef void *j_common_ptr;
typedef struct jpeg_compress_struct *j_compress_ptr;
typedef struct jpeg_decompress_struct *j_decompress_ptr;

#define JPEG_LIB_VERSION  62               

typedef enum
{
	JCS_UNKNOWN,
	JCS_GRAYSCALE,
	JCS_RGB,
	JCS_YCbCr,
	JCS_CMYK,
	JCS_YCCK
} J_COLOR_SPACE;
typedef enum {JPEG_DUMMY1} J_DCT_METHOD;
typedef enum {JPEG_DUMMY2} J_DITHER_MODE;
typedef unsigned int JDIMENSION;

#define JPOOL_PERMANENT	0	                                         
#define JPOOL_IMAGE		1	                                         

#define JPEG_EOI	0xD9                    

#define JMSG_STR_PARM_MAX  80

#define DCTSIZE2 64
#define NUM_QUANT_TBLS 4
#define NUM_HUFF_TBLS 4
#define NUM_ARITH_TBLS 16
#define MAX_COMPS_IN_SCAN 4
#define C_MAX_BLOCKS_IN_MCU 10
#define D_MAX_BLOCKS_IN_MCU 10

struct jpeg_memory_mgr
{
  void* (*alloc_small) (j_common_ptr cinfo, int pool_id, size_t sizeofobject);
  void (*_reserve_space_for_alloc_large) (void *dummy, ...);
  void (*_reserve_space_for_alloc_sarray) (void *dummy, ...);
  void (*_reserve_space_for_alloc_barray) (void *dummy, ...);
  void (*_reserve_space_for_request_virt_sarray) (void *dummy, ...);
  void (*_reserve_space_for_request_virt_barray) (void *dummy, ...);
  void (*_reserve_space_for_realize_virt_arrays) (void *dummy, ...);
  void (*_reserve_space_for_access_virt_sarray) (void *dummy, ...);
  void (*_reserve_space_for_access_virt_barray) (void *dummy, ...);
  void (*_reserve_space_for_free_pool) (void *dummy, ...);
  void (*_reserve_space_for_self_destruct) (void *dummy, ...);

  long max_memory_to_use;
  long max_alloc_chunk;
};

struct jpeg_error_mgr
{
	void (*error_exit) (j_common_ptr cinfo);
	void (*emit_message) (j_common_ptr cinfo, int msg_level);
	void (*output_message) (j_common_ptr cinfo);
	void (*format_message) (j_common_ptr cinfo, char * buffer);
	void (*reset_error_mgr) (j_common_ptr cinfo);
	int msg_code;
	union {
		int i[8];
		char s[JMSG_STR_PARM_MAX];
	} msg_parm;
	int trace_level;
	long num_warnings;
	const char * const * jpeg_message_table;
	int last_jpeg_message;
	const char * const * addon_message_table;
	int first_addon_message;
	int last_addon_message;
};

struct jpeg_source_mgr
{
	const unsigned char *next_input_byte;
	size_t bytes_in_buffer;

	void (*init_source) (j_decompress_ptr cinfo);
	jboolean (*fill_input_buffer) (j_decompress_ptr cinfo);
	void (*skip_input_data) (j_decompress_ptr cinfo, long num_bytes);
	jboolean (*resync_to_restart) (j_decompress_ptr cinfo, int desired);
	void (*term_source) (j_decompress_ptr cinfo);
};

typedef struct {
                                                    
                                                                  
                                                             
  int component_id;                                                         
  int component_index;                                                      
  int h_samp_factor;                                                   
  int v_samp_factor;                                                 
  int quant_tbl_no;                                                     
                                            
                                                                  
                                                             
                                                                 
  int dc_tbl_no;                                                      
  int ac_tbl_no;                                                      
  
                                                                      
  
                                                                              
                                    
                                                                         
                                                                        
     
  JDIMENSION width_in_blocks;
  JDIMENSION height_in_blocks;
                                                                     
                                                                         
                                                                    
                                                                       
                                                    
     
  int DCT_scaled_size;
                                                                           
                                                                              
                                                    
                                                                               
                                                                              
     
  JDIMENSION downsampled_width;                               
  JDIMENSION downsampled_height;                               
                                                                          
                                                                       
                                                             
     
  jboolean component_needed;                                                  

                                                                          
                                                                 
  int MCU_width;                                                            
  int MCU_height;                                                         
  int MCU_blocks;                                           
  int MCU_sample_width;                                                              
  int last_col_width;                                                         
  int last_row_height;                                                      

                                                                    
                                                                
                                                         
     
  void *quant_table;

                                                                
  void * dct_table;
} jpeg_component_info;

struct jpeg_decompress_struct
{
	struct jpeg_error_mgr *err;		       
	struct jpeg_memory_mgr *mem;	       

	void *progress;
	void *client_data;
	jboolean is_decompressor;
	int global_state;

	struct jpeg_source_mgr *src;	       
	JDIMENSION image_width;			       
	JDIMENSION image_height;		       

	int num_components;
	J_COLOR_SPACE jpeg_color_space;
	J_COLOR_SPACE out_color_space;
	unsigned int scale_num, scale_denom;
	double output_gamma;
	jboolean buffered_image;
	jboolean raw_data_out;
	J_DCT_METHOD dct_method;
	jboolean do_fancy_upsampling;
	jboolean do_block_smoothing;
	jboolean quantize_colors;
	J_DITHER_MODE dither_mode;
	jboolean two_pass_quantize;
	int desired_number_of_colors;
	jboolean enable_1pass_quant;
	jboolean enable_external_quant;
	jboolean enable_2pass_quant;
	JDIMENSION output_width;

	JDIMENSION output_height;	       

	int out_color_components;

	int output_components;		       

	int rec_outbuf_height;
	int actual_number_of_colors;
	void *colormap;

	JDIMENSION output_scanline;	       

	int input_scan_number;
	JDIMENSION input_iMCU_row;
	int output_scan_number;
	JDIMENSION output_iMCU_row;
	int (*coef_bits)[DCTSIZE2];
	void *quant_tbl_ptrs[NUM_QUANT_TBLS];
	void *dc_huff_tbl_ptrs[NUM_HUFF_TBLS];
	void *ac_huff_tbl_ptrs[NUM_HUFF_TBLS];
	int data_precision;
	jpeg_component_info *comp_info;
	jboolean progressive_mode;
	jboolean arith_code;
	unsigned char arith_dc_L[NUM_ARITH_TBLS];
	unsigned char arith_dc_U[NUM_ARITH_TBLS];
	unsigned char arith_ac_K[NUM_ARITH_TBLS];
	unsigned int restart_interval;
	jboolean saw_JFIF_marker;
	unsigned char JFIF_major_version;
	unsigned char JFIF_minor_version;
	unsigned char density_unit;
	unsigned short X_density;
	unsigned short Y_density;
	jboolean saw_Adobe_marker;
	unsigned char Adobe_transform;
	jboolean CCIR601_sampling;
	void *marker_list;
	int max_h_samp_factor;
	int max_v_samp_factor;
	int min_DCT_scaled_size;
	JDIMENSION total_iMCU_rows;
	void *sample_range_limit;
	int comps_in_scan;
	jpeg_component_info *cur_comp_info[MAX_COMPS_IN_SCAN];
	JDIMENSION MCUs_per_row;
	JDIMENSION MCU_rows_in_scan;
	int blocks_in_MCU;
	int MCU_membership[D_MAX_BLOCKS_IN_MCU];
	int Ss, Se, Ah, Al;
	int unread_marker;
	void *master;
	void *main;
	void *coef;
	void *post;
	void *inputctl;
	void *marker;
	void *entropy;
	void *idct;
	void *upsample;
	void *cconvert;
	void *cquantize;
};


struct jpeg_compress_struct
{
	struct jpeg_error_mgr *err;
	struct jpeg_memory_mgr *mem;
	void *progress;
	void *client_data;
	jboolean is_decompressor;
	int global_state;

	void *dest;
	JDIMENSION image_width;
	JDIMENSION image_height;
	int input_components;
	J_COLOR_SPACE in_color_space;
	double input_gamma;
	int data_precision;

	int num_components;
	J_COLOR_SPACE jpeg_color_space;
	jpeg_component_info *comp_info;
	void *quant_tbl_ptrs[NUM_QUANT_TBLS];
	void *dc_huff_tbl_ptrs[NUM_HUFF_TBLS];
	void *ac_huff_tbl_ptrs[NUM_HUFF_TBLS];
	unsigned char arith_dc_L[NUM_ARITH_TBLS];
	unsigned char arith_dc_U[NUM_ARITH_TBLS];
	unsigned char arith_ac_K[NUM_ARITH_TBLS];

	int num_scans;
	const void *scan_info;
	jboolean raw_data_in;
	jboolean arith_code;
	jboolean optimize_coding;
	jboolean CCIR601_sampling;
	int smoothing_factor;
	J_DCT_METHOD dct_method;

	unsigned int restart_interval;
	int restart_in_rows;

	jboolean write_JFIF_header;
	unsigned char JFIF_major_version;
	unsigned char JFIF_minor_version;
	unsigned char density_unit;
	unsigned short X_density;
	unsigned short Y_density;
	jboolean write_Adobe_marker;
	JDIMENSION next_scanline;

	jboolean progressive_mode;
	int max_h_samp_factor;
	int max_v_samp_factor;
	JDIMENSION total_iMCU_rows;
	int comps_in_scan;
	jpeg_component_info *cur_comp_info[MAX_COMPS_IN_SCAN];
	JDIMENSION MCUs_per_row;
	JDIMENSION MCU_rows_in_scan;
	int blocks_in_MCU;
	int MCU_membership[C_MAX_BLOCKS_IN_MCU];
	int Ss, Se, Ah, Al;

	void *master;
	void *main;
	void *prep;
	void *coef;
	void *marker;
	void *cconvert;
	void *downsample;
	void *fdct;
	void *entropy;
	void *script_space;
	int script_space_size;
};

struct jpeg_destination_mgr
{
	unsigned char* next_output_byte;
	size_t free_in_buffer;

	void (*init_destination) (j_compress_ptr cinfo);
	jboolean (*empty_output_buffer) (j_compress_ptr cinfo);
	void (*term_destination) (j_compress_ptr cinfo);
};


  
                                                                 

                        

                                                                 
  

                                  
#define qjpeg_create_compress(cinfo) \
	qjpeg_CreateCompress((cinfo), JPEG_LIB_VERSION, (size_t) sizeof(struct jpeg_compress_struct))
#define qjpeg_create_decompress(cinfo) \
	qjpeg_CreateDecompress((cinfo), JPEG_LIB_VERSION, (size_t) sizeof(struct jpeg_decompress_struct))

static void (*qjpeg_CreateCompress) (j_compress_ptr cinfo, int version, size_t structsize);
static void (*qjpeg_CreateDecompress) (j_decompress_ptr cinfo, int version, size_t structsize);
static void (*qjpeg_destroy_compress) (j_compress_ptr cinfo);
static void (*qjpeg_destroy_decompress) (j_decompress_ptr cinfo);
static void (*qjpeg_finish_compress) (j_compress_ptr cinfo);
static jboolean (*qjpeg_finish_decompress) (j_decompress_ptr cinfo);
static jboolean (*qjpeg_resync_to_restart) (j_decompress_ptr cinfo, int desired);
static int (*qjpeg_read_header) (j_decompress_ptr cinfo, jboolean require_image);
static JDIMENSION (*qjpeg_read_scanlines) (j_decompress_ptr cinfo, unsigned char** scanlines, JDIMENSION max_lines);
static void (*qjpeg_set_defaults) (j_compress_ptr cinfo);
static void (*qjpeg_set_quality) (j_compress_ptr cinfo, int quality, jboolean force_baseline);
static jboolean (*qjpeg_start_compress) (j_compress_ptr cinfo, jboolean write_all_tables);
static jboolean (*qjpeg_start_decompress) (j_decompress_ptr cinfo);
static struct jpeg_error_mgr* (*qjpeg_std_error) (struct jpeg_error_mgr *err);
static JDIMENSION (*qjpeg_write_scanlines) (j_compress_ptr cinfo, unsigned char** scanlines, JDIMENSION num_lines);
static void (*qjpeg_simple_progression) (j_compress_ptr cinfo);

static dllfunction_t jpegfuncs[] =
{
	{"jpeg_CreateCompress",		(void **) &qjpeg_CreateCompress},
	{"jpeg_CreateDecompress",	(void **) &qjpeg_CreateDecompress},
	{"jpeg_destroy_compress",	(void **) &qjpeg_destroy_compress},
	{"jpeg_destroy_decompress",	(void **) &qjpeg_destroy_decompress},
	{"jpeg_finish_compress",	(void **) &qjpeg_finish_compress},
	{"jpeg_finish_decompress",	(void **) &qjpeg_finish_decompress},
	{"jpeg_resync_to_restart",	(void **) &qjpeg_resync_to_restart},
	{"jpeg_read_header",		(void **) &qjpeg_read_header},
	{"jpeg_read_scanlines",		(void **) &qjpeg_read_scanlines},
	{"jpeg_set_defaults",		(void **) &qjpeg_set_defaults},
	{"jpeg_set_quality",		(void **) &qjpeg_set_quality},
	{"jpeg_start_compress",		(void **) &qjpeg_start_compress},
	{"jpeg_start_decompress",	(void **) &qjpeg_start_decompress},
	{"jpeg_std_error",			(void **) &qjpeg_std_error},
	{"jpeg_write_scanlines",	(void **) &qjpeg_write_scanlines},
	{"jpeg_simple_progression",	(void **) &qjpeg_simple_progression},
	{NULL, NULL}
};

                      
dllhandle_t jpeg_dll = NULL;
qboolean jpeg_tried_loading = 0;
#endif

static unsigned char jpeg_eoi_marker [2] = {0xFF, JPEG_EOI};
static jmp_buf error_in_jpeg;
static qboolean jpeg_toolarge;

                                              
typedef struct
{
	struct jpeg_destination_mgr pub;

	qfile_t* outfile;
	unsigned char* buffer;
	size_t bufsize;                           
} my_destination_mgr;
typedef my_destination_mgr* my_dest_ptr;


  
                                                                 

                   

                                                                 
  

  
                    
                

                        
                    
  
qboolean JPEG_OpenLibrary (void)
{
#ifdef LINK_TO_LIBJPEG
	return true;
#else
	const char* dllnames [] =
	{
#if defined(WIN32)
		"libjpeg.dll",
#elif defined(MACOSX)
		"libjpeg.62.dylib",
#else
		"libjpeg.so.62",
		"libjpeg.so",
#endif
		NULL
	};

	                  
	if (jpeg_dll)
		return true;

	if (jpeg_tried_loading)                 
		return false;

	jpeg_tried_loading = true;

#ifdef __ANDROID__
	                                                       
	Con_Printf("Not opening libjpeg.so dynamically on Android - use LINK_TO_LIBJPEG instead if it is needed.\n");
	return false;
#endif

	               
	return Sys_LoadLibrary (dllnames, &jpeg_dll, jpegfuncs);
#endif
}


  
                    
                 

                   
                    
  
void JPEG_CloseLibrary (void)
{
#ifndef LINK_TO_LIBJPEG
	Sys_UnloadLibrary (&jpeg_dll);
	jpeg_tried_loading = false;               
#endif
}


  
                                                                 

                   

                                                                 
  

static void JPEG_Noop (j_decompress_ptr cinfo) {}

static jboolean JPEG_FillInputBuffer (j_decompress_ptr cinfo)
{
                               
    cinfo->src->next_input_byte = jpeg_eoi_marker;
    cinfo->src->bytes_in_buffer = 2;

	return TRUE;
}

static void JPEG_SkipInputData (j_decompress_ptr cinfo, long num_bytes)
{
    if (cinfo->src->bytes_in_buffer <= (unsigned long)num_bytes)
	{
		cinfo->src->bytes_in_buffer = 0;
		return;
	}

    cinfo->src->next_input_byte += num_bytes;
    cinfo->src->bytes_in_buffer -= num_bytes;
}

static void JPEG_MemSrc (j_decompress_ptr cinfo, const unsigned char *buffer, size_t filesize)
{
	cinfo->src = (struct jpeg_source_mgr *)cinfo->mem->alloc_small ((j_common_ptr) cinfo, JPOOL_PERMANENT, sizeof (struct jpeg_source_mgr));

	cinfo->src->next_input_byte = buffer;
	cinfo->src->bytes_in_buffer = filesize;

	cinfo->src->init_source = JPEG_Noop;
	cinfo->src->fill_input_buffer = JPEG_FillInputBuffer;
	cinfo->src->skip_input_data = JPEG_SkipInputData;
	cinfo->src->resync_to_restart = qjpeg_resync_to_restart;                          
	cinfo->src->term_source = JPEG_Noop;
}

static void JPEG_ErrorExit (j_common_ptr cinfo)
{
	((struct jpeg_decompress_struct*)cinfo)->err->output_message (cinfo);
	longjmp(error_in_jpeg, 1);
}


  
                    
              

                                    
                    
  
unsigned char* JPEG_LoadImage_BGRA (const unsigned char *f, int filesize, int *miplevel)
{
	struct jpeg_decompress_struct cinfo;
	struct jpeg_error_mgr jerr;
	unsigned char *image_buffer = NULL, *scanline = NULL;
	unsigned int line;
	int submip = 0;

	                    
	if (!jpeg_dll)
		return NULL;

	if(miplevel && r_texture_jpeg_fastpicmip.integer)
		submip = bound(0, *miplevel, 3);

	cinfo.err = qjpeg_std_error (&jerr);
	qjpeg_create_decompress (&cinfo);
	if(setjmp(error_in_jpeg))
		goto error_caught;
	cinfo.err = qjpeg_std_error (&jerr);
	cinfo.err->error_exit = JPEG_ErrorExit;
	JPEG_MemSrc (&cinfo, f, filesize);
	qjpeg_read_header (&cinfo, TRUE);
	cinfo.scale_num = 1;
	cinfo.scale_denom = (1 << submip);
	qjpeg_start_decompress (&cinfo);

	image_width = cinfo.output_width;
	image_height = cinfo.output_height;

	if (image_width > 32768 || image_height > 32768 || image_width <= 0 || image_height <= 0)
	{
		Con_Printf("JPEG_LoadImage: invalid image size %ix%i\n", image_width, image_height);
		return NULL;
	}

	image_buffer = (unsigned char *)Mem_Alloc(tempmempool, image_width * image_height * 4);
	scanline = (unsigned char *)Mem_Alloc(tempmempool, image_width * cinfo.output_components);
	if (!image_buffer || !scanline)
	{
		if (image_buffer)
			Mem_Free (image_buffer);
		if (scanline)
			Mem_Free (scanline);

		Con_Printf("JPEG_LoadImage: not enough memory for %i by %i image\n", image_width, image_height);
		qjpeg_finish_decompress (&cinfo);
		qjpeg_destroy_decompress (&cinfo);
		return NULL;
	}

	                                     
	line = 0;
	while (cinfo.output_scanline < cinfo.output_height)
	{
		unsigned char *buffer_ptr;
		int ind;

		qjpeg_read_scanlines (&cinfo, &scanline, 1);

		                            
		switch (cinfo.output_components)
		{
			             
			case 3:
				buffer_ptr = &image_buffer[image_width * line * 4];
				for (ind = 0; ind < image_width * 3; ind += 3, buffer_ptr += 4)
				{
					buffer_ptr[2] = scanline[ind];
					buffer_ptr[1] = scanline[ind + 1];
					buffer_ptr[0] = scanline[ind + 2];
					buffer_ptr[3] = 255;
				}
				break;

			                                                 
			case 1:
			default:
				buffer_ptr = &image_buffer[image_width * line * 4];
				for (ind = 0; ind < image_width; ind++, buffer_ptr += 4)
				{
					buffer_ptr[0] = scanline[ind];
					buffer_ptr[1] = scanline[ind];
					buffer_ptr[2] = scanline[ind];
					buffer_ptr[3] = 255;
				}
		}

		line++;
	}
	Mem_Free (scanline); scanline = NULL;

	qjpeg_finish_decompress (&cinfo);
	qjpeg_destroy_decompress (&cinfo);

	if(miplevel)
		*miplevel -= submip;

	return image_buffer;

error_caught:
	if(scanline)
		Mem_Free (scanline);
	if(image_buffer)
		Mem_Free (image_buffer);
	qjpeg_destroy_decompress (&cinfo);
	return NULL;
}


  
                                                                 

                  

                                                                 
  

#define JPEG_OUTPUT_BUF_SIZE 4096
static void JPEG_InitDestination (j_compress_ptr cinfo)
{
	my_dest_ptr dest = (my_dest_ptr)cinfo->dest;
	dest->buffer = (unsigned char*)cinfo->mem->alloc_small ((j_common_ptr) cinfo, JPOOL_IMAGE, JPEG_OUTPUT_BUF_SIZE * sizeof(unsigned char));
	dest->pub.next_output_byte = dest->buffer;
	dest->pub.free_in_buffer = JPEG_OUTPUT_BUF_SIZE;
}

static jboolean JPEG_EmptyOutputBuffer (j_compress_ptr cinfo)
{
	my_dest_ptr dest = (my_dest_ptr)cinfo->dest;

	if (FS_Write (dest->outfile, dest->buffer, JPEG_OUTPUT_BUF_SIZE) != (size_t) JPEG_OUTPUT_BUF_SIZE)
		longjmp(error_in_jpeg, 1);

	dest->pub.next_output_byte = dest->buffer;
	dest->pub.free_in_buffer = JPEG_OUTPUT_BUF_SIZE;
	return true;
}

static void JPEG_TermDestination (j_compress_ptr cinfo)
{
	my_dest_ptr dest = (my_dest_ptr)cinfo->dest;
	size_t datacount = JPEG_OUTPUT_BUF_SIZE - dest->pub.free_in_buffer;

	                                         
	if (datacount > 0)
		if (FS_Write (dest->outfile, dest->buffer, datacount) != (fs_offset_t)datacount)
			longjmp(error_in_jpeg, 1);
}

static void JPEG_FileDest (j_compress_ptr cinfo, qfile_t* outfile)
{
	my_dest_ptr dest;

	                                   
	if (cinfo->dest == NULL)
		cinfo->dest = (struct jpeg_destination_mgr *)(*cinfo->mem->alloc_small) ((j_common_ptr) cinfo, JPOOL_PERMANENT, sizeof(my_destination_mgr));

	dest = (my_dest_ptr)cinfo->dest;
	dest->pub.init_destination = JPEG_InitDestination;
	dest->pub.empty_output_buffer = JPEG_EmptyOutputBuffer;
	dest->pub.term_destination = JPEG_TermDestination;
	dest->outfile = outfile;
}

static void JPEG_Mem_InitDestination (j_compress_ptr cinfo)
{
	my_dest_ptr dest = (my_dest_ptr)cinfo->dest;
	dest->pub.next_output_byte = dest->buffer;
	dest->pub.free_in_buffer = dest->bufsize;
}

static jboolean JPEG_Mem_EmptyOutputBuffer (j_compress_ptr cinfo)
{
	my_dest_ptr dest = (my_dest_ptr)cinfo->dest;
	jpeg_toolarge = true;
	dest->pub.next_output_byte = dest->buffer;
	dest->pub.free_in_buffer = dest->bufsize;
	return true;
}

static void JPEG_Mem_TermDestination (j_compress_ptr cinfo)
{
	my_dest_ptr dest = (my_dest_ptr)cinfo->dest;
	dest->bufsize = dest->pub.next_output_byte - dest->buffer;
}
static void JPEG_MemDest (j_compress_ptr cinfo, void* buf, size_t bufsize)
{
	my_dest_ptr dest;

	                                   
	if (cinfo->dest == NULL)
		cinfo->dest = (struct jpeg_destination_mgr *)(*cinfo->mem->alloc_small) ((j_common_ptr) cinfo, JPOOL_PERMANENT, sizeof(my_destination_mgr));

	dest = (my_dest_ptr)cinfo->dest;
	dest->pub.init_destination = JPEG_Mem_InitDestination;
	dest->pub.empty_output_buffer = JPEG_Mem_EmptyOutputBuffer;
	dest->pub.term_destination = JPEG_Mem_TermDestination;
	dest->outfile = NULL;

	dest->buffer = (unsigned char *) buf;
	dest->bufsize = bufsize;
}


  
                    
                         

                                      
                    
  
qboolean JPEG_SaveImage_preflipped (const char *filename, int width, int height, unsigned char *data)
{
	struct jpeg_compress_struct cinfo;
	struct jpeg_error_mgr jerr;
	unsigned char *scanline;
	unsigned int offset, linesize;
	qfile_t* file;

	                    
	if (!jpeg_dll)
	{
		Con_Print("You need the libjpeg library to save JPEG images\n");
		return false;
	}

	                
	file = FS_OpenRealFile(filename, "wb", true);
	if (!file)
		return false;

	if(setjmp(error_in_jpeg))
		goto error_caught;
	cinfo.err = qjpeg_std_error (&jerr);
	cinfo.err->error_exit = JPEG_ErrorExit;

	qjpeg_create_compress (&cinfo);
	JPEG_FileDest (&cinfo, file);

	                                     
	cinfo.image_width = width;
	cinfo.image_height = height;
	cinfo.in_color_space = JCS_RGB;
	cinfo.input_components = 3;
	qjpeg_set_defaults (&cinfo);
	qjpeg_set_quality (&cinfo, (int)(scr_screenshot_jpeg_quality.value * 100), TRUE);
	qjpeg_simple_progression (&cinfo);

	                                                  
	cinfo.optimize_coding = 1;
	cinfo.comp_info[0].h_samp_factor = 1;
	cinfo.comp_info[0].v_samp_factor = 1;
	cinfo.comp_info[1].h_samp_factor = 1;
	cinfo.comp_info[1].v_samp_factor = 1;
	cinfo.comp_info[2].h_samp_factor = 1;
	cinfo.comp_info[2].v_samp_factor = 1;

	qjpeg_start_compress (&cinfo, true);

	                         
	linesize = cinfo.image_width * 3;
	offset = linesize * (cinfo.image_height - 1);
	while (cinfo.next_scanline < cinfo.image_height)
	{
		scanline = &data[offset - cinfo.next_scanline * linesize];

		qjpeg_write_scanlines (&cinfo, &scanline, 1);
	}

	qjpeg_finish_compress (&cinfo);
	qjpeg_destroy_compress (&cinfo);

	FS_Close (file);
	return true;

error_caught:
	qjpeg_destroy_compress (&cinfo);
	FS_Close (file);
	return false;
}

static size_t JPEG_try_SaveImage_to_Buffer (struct jpeg_compress_struct *cinfo, char *jpegbuf, size_t jpegsize, int quality, int width, int height, unsigned char *data)
{
	unsigned char *scanline;
	unsigned int linesize;

	jpeg_toolarge = false;
	JPEG_MemDest (cinfo, jpegbuf, jpegsize);

	                                     
	cinfo->image_width = width;
	cinfo->image_height = height;
	cinfo->in_color_space = JCS_RGB;
	cinfo->input_components = 3;
	qjpeg_set_defaults (cinfo);
	qjpeg_set_quality (cinfo, quality, FALSE);

	cinfo->comp_info[0].h_samp_factor = 2;
	cinfo->comp_info[0].v_samp_factor = 2;
	cinfo->comp_info[1].h_samp_factor = 1;
	cinfo->comp_info[1].v_samp_factor = 1;
	cinfo->comp_info[2].h_samp_factor = 1;
	cinfo->comp_info[2].v_samp_factor = 1;
	cinfo->optimize_coding = 1;

	qjpeg_start_compress (cinfo, true);

	                         
	linesize = width * 3;
	while (cinfo->next_scanline < cinfo->image_height)
	{
		scanline = &data[cinfo->next_scanline * linesize];

		qjpeg_write_scanlines (cinfo, &scanline, 1);
	}

	qjpeg_finish_compress (cinfo);

	if(jpeg_toolarge)
		return 0;

	return ((my_dest_ptr) cinfo->dest)->bufsize;
}

size_t JPEG_SaveImage_to_Buffer (char *jpegbuf, size_t jpegsize, int width, int height, unsigned char *data)
{
	struct jpeg_compress_struct cinfo;
	struct jpeg_error_mgr jerr;

	int quality;
	int quality_guess;
	size_t result;

	                    
	if (!jpeg_dll)
	{
		Con_Print("You need the libjpeg library to save JPEG images\n");
		return false;
	}

	if(setjmp(error_in_jpeg))
		goto error_caught;
	cinfo.err = qjpeg_std_error (&jerr);
	cinfo.err->error_exit = JPEG_ErrorExit;

	qjpeg_create_compress (&cinfo);

#if 0
	                                
	{
		char buf[1048576];
		unsigned char *img;
		int i;

		img = Mem_Alloc(tempmempool, width * height * 3);
		for(i = 0; i < width * height * 3; ++i)
			img[i] = rand() & 0xFF;

		for(i = 0; i <= 100; ++i)
		{
			Con_Printf("! %d %d %d %d\n", width, height, i, (int) JPEG_try_SaveImage_to_Buffer(&cinfo, buf, sizeof(buf), i, width, height, img));
		}

		Mem_Free(img);
	}
#endif

	                                                                                           
	quality_guess   = (int)((256 * jpegsize - 81920) / (width*height) - 8);                                        

	quality_guess = bound(0, quality_guess, 100);
	quality = bound(0, quality_guess + sv_writepicture_quality.integer, 100);                                       

	while(!(result = JPEG_try_SaveImage_to_Buffer(&cinfo, jpegbuf, jpegsize, quality, width, height, data)))
	{
		--quality;
		if(quality < 0)
		{
			Con_Printf("couldn't write image at all, probably too big\n");
			return 0;
		}
	}
	qjpeg_destroy_compress (&cinfo);
	Con_DPrintf("JPEG_SaveImage_to_Buffer: guessed quality/size %d/%d, actually got %d/%d\n", quality_guess, (int)jpegsize, quality, (int)result);

	return result;

error_caught:
	qjpeg_destroy_compress (&cinfo);
	return 0;
}

typedef struct CompressedImageCacheItem
{
	char imagename[MAX_QPATH];
	size_t maxsize;
	void *compressed;
	size_t compressed_size;
	struct CompressedImageCacheItem *next;
}
CompressedImageCacheItem;
#define COMPRESSEDIMAGECACHE_SIZE 4096
static CompressedImageCacheItem *CompressedImageCache[COMPRESSEDIMAGECACHE_SIZE];

static void CompressedImageCache_Add(const char *imagename, size_t maxsize, void *compressed, size_t compressed_size)
{
	char vabuf[1024];
	const char *hashkey = va(vabuf, sizeof(vabuf), "%s:%d", imagename, (int) maxsize);
	int hashindex = CRC_Block((unsigned char *) hashkey, strlen(hashkey)) % COMPRESSEDIMAGECACHE_SIZE;
	CompressedImageCacheItem *i;

	if(strlen(imagename) >= MAX_QPATH)
		return;                  
	
	i = (CompressedImageCacheItem*) Z_Malloc(sizeof(CompressedImageCacheItem));
	strlcpy(i->imagename, imagename, sizeof(i->imagename));
	i->maxsize = maxsize;
	i->compressed = compressed;
	i->compressed_size = compressed_size;
	i->next = CompressedImageCache[hashindex];
	CompressedImageCache[hashindex] = i;
}

static CompressedImageCacheItem *CompressedImageCache_Find(const char *imagename, size_t maxsize)
{
	char vabuf[1024];
	const char *hashkey = va(vabuf, sizeof(vabuf), "%s:%d", imagename, (int) maxsize);
	int hashindex = CRC_Block((unsigned char *) hashkey, strlen(hashkey)) % COMPRESSEDIMAGECACHE_SIZE;
	CompressedImageCacheItem *i = CompressedImageCache[hashindex];

	while(i)
	{
		if(i->maxsize == maxsize)
			if(!strcmp(i->imagename, imagename))
				return i;
		i = i->next;
	}
	return NULL;
}

qboolean Image_Compress(const char *imagename, size_t maxsize, void **buf, size_t *size)
{
	unsigned char *imagedata, *newimagedata;
	int maxPixelCount;
	int components[3] = {2, 1, 0};
	CompressedImageCacheItem *i;

	JPEG_OpenLibrary ();                                                                 
	PNG_OpenLibrary ();               

	                    
	if (!jpeg_dll)
	{
		Con_Print("You need the libjpeg library to save JPEG images\n");
		return false;
	}

	i = CompressedImageCache_Find(imagename, maxsize);
	if(i)
	{
		*size = i->compressed_size;
		*buf = i->compressed;
	}

	                 
	imagedata = loadimagepixelsbgra(imagename, true, false, false, NULL);
	if(!imagedata)
		return false;

	                                                         
	if(maxsize <= 768)
		maxPixelCount = 32 * 32;
	else if(maxsize <= 1024)
		maxPixelCount = 64 * 64;
	else if(maxsize <= 4096)
		maxPixelCount = 128 * 128;
	else
		maxPixelCount = 256 * 256;

	while(image_width * image_height > maxPixelCount)
	{
		int one = 1;
		Image_MipReduce32(imagedata, imagedata, &image_width, &image_height, &one, image_width/2, image_height/2, 1);
	}

	newimagedata = (unsigned char *) Mem_Alloc(tempmempool, image_width * image_height * 3);

	                                     
	Image_CopyMux(newimagedata, imagedata, image_width, image_height, false, false, false, 3, 4, components);
	Mem_Free(imagedata);

	                             
	*buf = Z_Malloc(maxsize);
	*size = JPEG_SaveImage_to_Buffer((char *) *buf, maxsize, image_width, image_height, newimagedata);
	Mem_Free(newimagedata);

	if(!*size)
	{
		Z_Free(*buf);
		*buf = NULL;
		Con_Printf("could not compress image %s to %d bytes\n", imagename, (int)maxsize);
		                
		                       
	}

	                        
	CompressedImageCache_Add(imagename, maxsize, *buf, *size);
	return (*buf != NULL);
}
