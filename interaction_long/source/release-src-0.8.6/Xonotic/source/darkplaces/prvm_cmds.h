
#ifndef PRVM_CMDS_H
#define PRVM_CMDS_H

     
                                                    
                                                      
                                                                                            
                    


  
                                                                            
                
                 

                        
                    
                      
                     
                     
                                     
                          
                        
                  
                      
                          
              
             
                     
                          
                     
                  
                 
                   
                   
                       
              
                  
                                                      

                                                         
                                                            

                                             

                                                 
                                                   

                            
                                     
            
           
            
                  
                 
                  
                 
                      
                
                
                 
                  
                                                           
                                       
                                       
                                              
                           
                                    
                                        
                       
                           
                                
                      
                                        
                                                     
                     
                        
                     
                        
                    
                
                   
                   
                                                             
                         
                           
                    
               
                           
                           
                                          
                             
                                 
                        
         
             

                                                                      
                             
                                  
                                                  

                       

                    
                      

                                     
                          
                             
                               
                                                       
                                                       
                                      

                                                         
                                                

                                       

                              
                               

                                                
                                                
                                                 
                                                
                                                 
                                                 
                                                   
                                                   

                                                                    
                                                   

                             
                               
                   
                                                                                                        
                                                                                                 
                                                                                               
                                                  
                                                                                            
                                                                                                                              
                                                                                 
                                                              
                     
                               

                                        
                           
                                          
                               
                             

                                       
                                 
                                              
                                                                      
                                                     

                                                                              
              
               

                        
                  
                              
                      

                                        
                                        
                                      
                                  
                                   
                                         
                                   
                                                   

                                

                        
                                                            
                                                                     
                    
                                                  
                     
                                                  
                                          
                                    
  

#include "quakedef.h"
#include "progdefs.h"
#include "progsvm.h"
#include "clprogdefs.h"
#include "mprogdefs.h"

#include "cl_video.h"

                                                                              
                     

#ifndef VM_NOPARMCHECK
#define VM_SAFEPARMCOUNTRANGE(p1,p2,f)	if(prog->argc < p1 || prog->argc > p2) prog->error_cmd(#f " wrong parameter count %i (" #p1 " to " #p2 " expected ) !", prog->argc)
#define VM_SAFEPARMCOUNT(p,f)	if(prog->argc != p) prog->error_cmd(#f " wrong parameter count %i (" #p " expected ) !", prog->argc)
#else
#define VM_SAFEPARMCOUNTRANGE(p1,p2,f)
#define VM_SAFEPARMCOUNT(p,f)
#endif

#define	VM_RETURN_EDICT(e)		(prog->globals.ip[OFS_RETURN] = PRVM_EDICT_TO_PROG(e))

#define VM_STRINGTEMP_LENGTH MAX_INPUTLINE

            
void PR_Cmd_Init(void);

                    
void VM_CheckEmptyString (prvm_prog_t *prog, const char *s);
void VM_VarString(prvm_prog_t *prog, int first, char *out, int outlength);
prvm_stringbuffer_t *BufStr_FindCreateReplace (prvm_prog_t *prog, int bufindex, int flags, const char *format);
void BufStr_Set(prvm_prog_t *prog, prvm_stringbuffer_t *stringbuffer, int strindex, const char *str);
void BufStr_Del(prvm_prog_t *prog, prvm_stringbuffer_t *stringbuffer);
void BufStr_Flush(prvm_prog_t *prog);

           
void VM_checkextension (prvm_prog_t *prog);
void VM_error (prvm_prog_t *prog);
void VM_objerror (prvm_prog_t *prog);
void VM_print (prvm_prog_t *prog);
void VM_bprint (prvm_prog_t *prog);
void VM_sprint (prvm_prog_t *prog);
void VM_centerprint (prvm_prog_t *prog);
void VM_normalize (prvm_prog_t *prog);
void VM_vlen (prvm_prog_t *prog);
void VM_vectoyaw (prvm_prog_t *prog);
void VM_vectoangles (prvm_prog_t *prog);
void VM_random (prvm_prog_t *prog);
void VM_localsound(prvm_prog_t *prog);
void VM_break (prvm_prog_t *prog);
void VM_localcmd (prvm_prog_t *prog);
void VM_cvar (prvm_prog_t *prog);
void VM_cvar_string(prvm_prog_t *prog);
void VM_cvar_type (prvm_prog_t *prog);
void VM_cvar_defstring (prvm_prog_t *prog);
void VM_cvar_set (prvm_prog_t *prog);
void VM_dprint (prvm_prog_t *prog);
void VM_ftos (prvm_prog_t *prog);
void VM_fabs (prvm_prog_t *prog);
void VM_vtos (prvm_prog_t *prog);
void VM_etos (prvm_prog_t *prog);
void VM_stof(prvm_prog_t *prog);
void VM_itof(prvm_prog_t *prog);
void VM_ftoe(prvm_prog_t *prog);
void VM_strftime(prvm_prog_t *prog);
void VM_spawn (prvm_prog_t *prog);
void VM_remove (prvm_prog_t *prog);
void VM_find (prvm_prog_t *prog);
void VM_findfloat (prvm_prog_t *prog);
void VM_findchain (prvm_prog_t *prog);
void VM_findchainfloat (prvm_prog_t *prog);
void VM_findflags (prvm_prog_t *prog);
void VM_findchainflags (prvm_prog_t *prog);
void VM_precache_file (prvm_prog_t *prog);
void VM_precache_sound (prvm_prog_t *prog);
void VM_coredump (prvm_prog_t *prog);

void VM_stackdump (prvm_prog_t *prog);
void VM_crash(prvm_prog_t *prog);             
void VM_traceon (prvm_prog_t *prog);
void VM_traceoff (prvm_prog_t *prog);
void VM_eprint (prvm_prog_t *prog);
void VM_rint (prvm_prog_t *prog);
void VM_floor (prvm_prog_t *prog);
void VM_ceil (prvm_prog_t *prog);
void VM_nextent (prvm_prog_t *prog);

void VM_changelevel (prvm_prog_t *prog);
void VM_sin (prvm_prog_t *prog);
void VM_cos (prvm_prog_t *prog);
void VM_sqrt (prvm_prog_t *prog);
void VM_randomvec (prvm_prog_t *prog);
void VM_registercvar (prvm_prog_t *prog);
void VM_min (prvm_prog_t *prog);
void VM_max (prvm_prog_t *prog);
void VM_bound (prvm_prog_t *prog);
void VM_pow (prvm_prog_t *prog);
void VM_log (prvm_prog_t *prog);
void VM_asin (prvm_prog_t *prog);
void VM_acos (prvm_prog_t *prog);
void VM_atan (prvm_prog_t *prog);
void VM_atan2 (prvm_prog_t *prog);
void VM_tan (prvm_prog_t *prog);

void VM_Files_Init(prvm_prog_t *prog);
void VM_Files_CloseAll(prvm_prog_t *prog);

void VM_fopen(prvm_prog_t *prog);
void VM_fclose(prvm_prog_t *prog);
void VM_fgets(prvm_prog_t *prog);
void VM_fputs(prvm_prog_t *prog);
void VM_writetofile(prvm_prog_t *prog);                     

void VM_strlen(prvm_prog_t *prog);
void VM_strcat(prvm_prog_t *prog);
void VM_substring(prvm_prog_t *prog);
void VM_stov(prvm_prog_t *prog);
void VM_strzone(prvm_prog_t *prog);
void VM_strunzone(prvm_prog_t *prog);

                             
void VM_numentityfields(prvm_prog_t *prog);
void VM_entityfieldname(prvm_prog_t *prog);
void VM_entityfieldtype(prvm_prog_t *prog);
void VM_getentityfieldstring(prvm_prog_t *prog);
void VM_putentityfieldstring(prvm_prog_t *prog);

                                                   
void VM_strlennocol(prvm_prog_t *prog);
                             
void VM_strdecolorize(prvm_prog_t *prog);
                                                 
void VM_strtolower(prvm_prog_t *prog);
void VM_strtoupper(prvm_prog_t *prog);

void VM_clcommand (prvm_prog_t *prog);

void VM_tokenize (prvm_prog_t *prog);
void VM_tokenizebyseparator (prvm_prog_t *prog);
void VM_argv (prvm_prog_t *prog);

void VM_isserver(prvm_prog_t *prog);
void VM_clientcount(prvm_prog_t *prog);
void VM_clientstate(prvm_prog_t *prog);
                                                            
void VM_getostype(prvm_prog_t *prog);
void VM_getmousepos(prvm_prog_t *prog);
void VM_gettime(prvm_prog_t *prog);
void VM_getsoundtime(prvm_prog_t *prog);
void VM_soundlength(prvm_prog_t *prog);
void VM_loadfromdata(prvm_prog_t *prog);
void VM_parseentitydata(prvm_prog_t *prog);
void VM_loadfromfile(prvm_prog_t *prog);
void VM_modulo(prvm_prog_t *prog);

void VM_search_begin(prvm_prog_t *prog);
void VM_search_end(prvm_prog_t *prog);
void VM_search_getsize(prvm_prog_t *prog);
void VM_search_getfilename(prvm_prog_t *prog);
void VM_chr(prvm_prog_t *prog);
void VM_iscachedpic(prvm_prog_t *prog);
void VM_precache_pic(prvm_prog_t *prog);
void VM_freepic(prvm_prog_t *prog);
void VM_drawcharacter(prvm_prog_t *prog);
void VM_drawstring(prvm_prog_t *prog);
void VM_drawcolorcodedstring(prvm_prog_t *prog);
void VM_stringwidth(prvm_prog_t *prog);
void VM_drawpic(prvm_prog_t *prog);
void VM_drawrotpic(prvm_prog_t *prog);
void VM_drawsubpic(prvm_prog_t *prog);
void VM_drawfill(prvm_prog_t *prog);
void VM_drawsetcliparea(prvm_prog_t *prog);
void VM_drawresetcliparea(prvm_prog_t *prog);
void VM_getimagesize(prvm_prog_t *prog);

void VM_findfont(prvm_prog_t *prog);
void VM_loadfont(prvm_prog_t *prog);

void VM_makevectors (prvm_prog_t *prog);
void VM_vectorvectors (prvm_prog_t *prog);

void VM_keynumtostring (prvm_prog_t *prog);
void VM_getkeybind (prvm_prog_t *prog);
void VM_findkeysforcommand (prvm_prog_t *prog);
void VM_stringtokeynum (prvm_prog_t *prog);
void VM_setkeybind (prvm_prog_t *prog);
void VM_getbindmaps (prvm_prog_t *prog);
void VM_setbindmaps (prvm_prog_t *prog);

void VM_cin_open(prvm_prog_t *prog);
void VM_cin_close(prvm_prog_t *prog);
void VM_cin_setstate(prvm_prog_t *prog);
void VM_cin_getstate(prvm_prog_t *prog);
void VM_cin_restart(prvm_prog_t *prog);

void VM_gecko_create(prvm_prog_t *prog);
void VM_gecko_destroy(prvm_prog_t *prog);
void VM_gecko_navigate(prvm_prog_t *prog);
void VM_gecko_keyevent(prvm_prog_t *prog);
void VM_gecko_movemouse(prvm_prog_t *prog);
void VM_gecko_resize(prvm_prog_t *prog);
void VM_gecko_get_texture_extent(prvm_prog_t *prog);

void VM_drawline (prvm_prog_t *prog);

void VM_bitshift (prvm_prog_t *prog);

void VM_altstr_count(prvm_prog_t *prog);
void VM_altstr_prepare(prvm_prog_t *prog);
void VM_altstr_get(prvm_prog_t *prog);
void VM_altstr_set(prvm_prog_t *prog);
void VM_altstr_ins(prvm_prog_t *prog);

void VM_buf_create(prvm_prog_t *prog);
void VM_buf_del (prvm_prog_t *prog);
void VM_buf_getsize (prvm_prog_t *prog);
void VM_buf_copy (prvm_prog_t *prog);
void VM_buf_sort (prvm_prog_t *prog);
void VM_buf_implode (prvm_prog_t *prog);
void VM_bufstr_get (prvm_prog_t *prog);
void VM_bufstr_set (prvm_prog_t *prog);
void VM_bufstr_add (prvm_prog_t *prog);
void VM_bufstr_free (prvm_prog_t *prog);

void VM_buf_loadfile(prvm_prog_t *prog);
void VM_buf_writefile(prvm_prog_t *prog);
void VM_bufstr_find(prvm_prog_t *prog);
void VM_matchpattern(prvm_prog_t *prog);

void VM_changeyaw (prvm_prog_t *prog);
void VM_changepitch (prvm_prog_t *prog);

void VM_uncolorstring (prvm_prog_t *prog);

void VM_strstrofs (prvm_prog_t *prog);
void VM_str2chr (prvm_prog_t *prog);
void VM_chr2str (prvm_prog_t *prog);
void VM_strconv (prvm_prog_t *prog);
void VM_strpad (prvm_prog_t *prog);
void VM_infoadd (prvm_prog_t *prog);
void VM_infoget (prvm_prog_t *prog);
void VM_strncmp (prvm_prog_t *prog);
void VM_strncmp (prvm_prog_t *prog);
void VM_strncasecmp (prvm_prog_t *prog);
void VM_registercvar (prvm_prog_t *prog);
void VM_wasfreed (prvm_prog_t *prog);

void VM_strreplace (prvm_prog_t *prog);
void VM_strireplace (prvm_prog_t *prog);

void VM_crc16(prvm_prog_t *prog);
void VM_digest_hex(prvm_prog_t *prog);

void VM_SetTraceGlobals(prvm_prog_t *prog, const trace_t *trace);
void VM_ClearTraceGlobals(prvm_prog_t *prog);

void VM_uri_escape (prvm_prog_t *prog);
void VM_uri_unescape (prvm_prog_t *prog);
void VM_whichpack (prvm_prog_t *prog);

void VM_etof (prvm_prog_t *prog);
void VM_uri_get (prvm_prog_t *prog);
void VM_netaddress_resolve (prvm_prog_t *prog);

void VM_tokenize_console (prvm_prog_t *prog);
void VM_argv_start_index (prvm_prog_t *prog);
void VM_argv_end_index (prvm_prog_t *prog);

void VM_buf_cvarlist(prvm_prog_t *prog);
void VM_cvar_description(prvm_prog_t *prog);

void VM_CL_getextresponse (prvm_prog_t *prog);
void VM_SV_getextresponse (prvm_prog_t *prog);

                                                 
void VM_CL_isdemo (prvm_prog_t *prog);
void VM_CL_videoplaying (prvm_prog_t *prog);

void VM_isfunction(prvm_prog_t *prog);
void VM_callfunction(prvm_prog_t *prog);

void VM_sprintf(prvm_prog_t *prog);

void VM_getsurfacenumpoints(prvm_prog_t *prog);
void VM_getsurfacepoint(prvm_prog_t *prog);
void VM_getsurfacepointattribute(prvm_prog_t *prog);
void VM_getsurfacenormal(prvm_prog_t *prog);
void VM_getsurfacetexture(prvm_prog_t *prog);
void VM_getsurfacenearpoint(prvm_prog_t *prog);
void VM_getsurfaceclippedpoint(prvm_prog_t *prog);
void VM_getsurfacenumtriangles(prvm_prog_t *prog);
void VM_getsurfacetriangle(prvm_prog_t *prog);

                   
void VM_physics_enable(prvm_prog_t *prog);
void VM_physics_addforce(prvm_prog_t *prog);
void VM_physics_addtorque(prvm_prog_t *prog);

void VM_coverage(prvm_prog_t *prog);

#endif
