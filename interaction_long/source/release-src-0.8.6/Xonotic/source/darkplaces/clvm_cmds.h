#ifndef __CLVM_CMDS_H__
#define __CLVM_CMDS_H__

                                                                            
                                                              

void VM_CL_setmodel (void);
void VM_CL_precache_model (void);
void VM_CL_setorigin (void);

void VM_CL_R_AddDynamicLight (void);
void VM_CL_R_ClearScene (void);
void VM_CL_R_AddEntities (void);
void VM_CL_R_AddEntity (void);
void VM_CL_R_SetView (void);
void VM_CL_R_RenderScene (void);
void VM_CL_R_LoadWorldModel (void);

void VM_CL_R_PolygonBegin (void);
void VM_CL_R_PolygonVertex (void);
void VM_CL_R_PolygonEnd (void);

void VM_CL_setattachment(void);
void VM_CL_gettagindex(void);
void VM_CL_gettaginfo(void);

#endif                      
