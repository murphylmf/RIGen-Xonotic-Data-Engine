#ifndef CSPROGS_H
#define CSPROGS_H

                                         
#define CL_MAX_EDICTS MAX_EDICTS

#define ENTMASK_ENGINE				1
#define ENTMASK_ENGINEVIEWMODELS	2
#define ENTMASK_NORMAL				4

#define VF_MIN			1	          
#define VF_MIN_X		2	         
#define VF_MIN_Y		3	         
#define VF_SIZE			4	                          
#define VF_SIZE_X		5	         
#define VF_SIZE_Y		6	         
#define VF_VIEWPORT		7	                  
#define VF_FOV			8	          
#define VF_FOVX			9	         
#define VF_FOVY			10	         
#define VF_ORIGIN		11	          
#define VF_ORIGIN_X		12	         
#define VF_ORIGIN_Y		13	         
#define VF_ORIGIN_Z		14	         
#define VF_ANGLES		15	          
#define VF_ANGLES_X		16	         
#define VF_ANGLES_Y		17	         
#define VF_ANGLES_Z		18	         

#define VF_DRAWWORLD		19	                                        
#define VF_DRAWENGINESBAR	20	         
#define VF_DRAWCROSSHAIR	21	         

#define VF_CL_VIEWANGLES	33	                                     
#define VF_CL_VIEWANGLES_X	34	         
#define VF_CL_VIEWANGLES_Y	35	         
#define VF_CL_VIEWANGLES_Z	36	         

                          
#define VF_PERSPECTIVE		200          

                                                                                              
#define VF_CLEARSCREEN		201          

                                                                                               
#define VF_FOG_DENSITY		202          
#define VF_FOG_COLOR		203           
#define VF_FOG_COLOR_R		204          
#define VF_FOG_COLOR_G		205          
#define VF_FOG_COLOR_B		206          
#define VF_FOG_ALPHA		207          
#define VF_FOG_START		208          
#define VF_FOG_END   		209          
#define VF_FOG_HEIGHT		210          
#define VF_FOG_FADEDEPTH	211          

                       
#define VF_MAINVIEW		400          
#define VF_MINFPS_QUALITY	401          

#define RF_VIEWMODEL		1	                                                                                                
#define RF_EXTERNALMODEL	2	                                                                                                                             
#define RF_DEPTHHACK		4	                                                                                                                                                                             
#define RF_ADDITIVE			8	                                                                           
#define RF_USEAXIS			16	                                                                                                                                                         
								                                                                                              
                            
#define RF_USETRANSPARENTOFFSET 64                                                                                                                                                              
#define RF_WORLDOBJECT          128                                                         
#define RF_MODELLIGHT           4096                        
#define RF_DYNAMICMODELLIGHT    8192                                

#define RF_FULLBRIGHT			256
#define RF_NOSHADOW				512

extern cvar_t csqc_progname;	                                                                     
extern cvar_t csqc_progcrc;
extern cvar_t csqc_progsize;

void CL_VM_PreventInformationLeaks(void);

qboolean MakeDownloadPacket(const char *filename, unsigned char *data, size_t len, int crc, int cnt, sizebuf_t *buf, int protocol);

qboolean CL_VM_GetEntitySoundOrigin(int entnum, vec3_t out);

qboolean CL_VM_TransformView(int entnum, matrix4x4_t *viewmatrix, mplane_t *clipplane, vec3_t visorigin);

void CL_VM_Init(void);
void CL_VM_ShutDown(void);
void CL_VM_UpdateIntermissionState(int intermission);
void CL_VM_UpdateShowingScoresState(int showingscores);
qboolean CL_VM_InputEvent(int eventtype, float x, float y);
qboolean CL_VM_ConsoleCommand(const char *cmd);
void CL_VM_UpdateDmgGlobals(int dmg_take, int dmg_save, vec3_t dmg_origin);
void CL_VM_UpdateIntermissionState(int intermission);
qboolean CL_VM_Event_Sound(int sound_num, float volume, int channel, float attenuation, int ent, vec3_t pos, int flags, float speed);
qboolean CL_VM_Parse_TempEntity(void);
void CL_VM_Parse_StuffCmd(const char *msg);
void CL_VM_Parse_CenterPrint(const char *msg);
int CL_GetPitchSign(prvm_prog_t *prog, prvm_edict_t *ent);
int CL_GetTagMatrix(prvm_prog_t *prog, matrix4x4_t *out, prvm_edict_t *ent, int tagindex, prvm_vec_t *shadingorigin);
void CL_GetEntityMatrix(prvm_prog_t *prog, prvm_edict_t *ent, matrix4x4_t *out, qboolean viewmatrix);
                                                                 
void VM_Polygons_Reset(prvm_prog_t *prog);
void QW_CL_StartUpload(unsigned char *data, int size);

void CSQC_UpdateNetworkTimes(double newtime, double oldtime);
void CSQC_AddPrintText(const char *msg);
void CSQC_ReadEntities(void);
void CSQC_RelinkAllEntities(int drawmask);
void CSQC_RelinkCSQCEntities(void);
void CSQC_Predraw(prvm_edict_t *ed);
void CSQC_Think(prvm_edict_t *ed);
qboolean CSQC_AddRenderEdict(prvm_edict_t *ed, int edictnum);           
void CSQC_R_RecalcView(void);

dp_model_t *CL_GetModelByIndex(int modelindex);

int CL_VM_GetViewEntity(void);

#endif
