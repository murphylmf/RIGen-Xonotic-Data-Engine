  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  
         

  

                                                                                                                                                      
          

                                                                          
                                                                               
                           

                                         
                                                

                                                                                                                                                                                                                                                      
                                        


                                               
                        

                                                                        
                                       

                                                             
                                          
                            
                             

                                                       
                                      
                                          
                                                                        
                               
  

#ifndef CVAR_H
#define CVAR_H

             

#define CVAR_SAVE 1
#define CVAR_NOTIFY 2
#define CVAR_READONLY 4
#define CVAR_SERVERINFO 8
#define CVAR_USERINFO 16
                                                                                                             
#define CVAR_PRIVATE 32
                                                                                                                                                                                                                                             
#define CVAR_NQUSERINFOHACK 64
                                      
#define CVAR_NORESETTODEFAULTS 128
                                                                                                                                                  
#define CVAR_MAXFLAGSVAL 255
                         
#define CVAR_DEFAULTSET (1<<30)
#define CVAR_ALLOCATED (1<<31)

  
                                   
                            
                              
                             
                           
                             
                             

                              
                           
                        
                        
                          
                         

                          

                           
 
           
                  
 
             

                         
 
          
                                     
                
                                          
 
           
  

typedef struct cvar_s
{
	int flags;

	const char *name;

	const char *string;
	const char *description;
	int integer;
	float value;
	float vector[3];

	const char *defstring;

	                                             
	qboolean initstate;                                  
	int initflags;
	const char *initstring;
	const char *initdescription;
	int initinteger;
	float initvalue;
	float initvector[3];
	const char *initdefstring;

	int globaldefindex[3];
	int globaldefindex_stringno[3];

	                      
	struct cvar_s *next;
	struct cvar_s *nextonhashchain;
} cvar_t;

  
                                                                                                        
                                                                                              
                                                                                  
                                                                                
                                                 
                                                                                      
  

                                                                          
                         
void Cvar_RegisterVariable (cvar_t *variable);

                                                          
void Cvar_Set (const char *var_name, const char *value);

                                                
void Cvar_SetValue (const char *var_name, float value);

void Cvar_SetQuick (cvar_t *var, const char *value);
void Cvar_SetValueQuick (cvar_t *var, float value);

float Cvar_VariableValueOr (const char *var_name, float def);
                             

float Cvar_VariableValue (const char *var_name);
                                          

const char *Cvar_VariableStringOr (const char *var_name, const char *def);
                             

const char *Cvar_VariableString (const char *var_name);
                                         

const char *Cvar_VariableDefString (const char *var_name);
                                         

const char *Cvar_VariableDescription (const char *var_name);
                                         

const char *Cvar_CompleteVariable (const char *partial);
                                                                        
                               

void Cvar_CompleteCvarPrint (const char *partial);

qboolean Cvar_Command (void);
                                                                     
                                                                      
                                 

void Cvar_SaveInitState(void);
void Cvar_RestoreInitState(void);

void Cvar_UnlockDefaults (void);
void Cvar_LockDefaults_f (void);
void Cvar_ResetToDefaults_All_f (void);
void Cvar_ResetToDefaults_NoSaveOnly_f (void);
void Cvar_ResetToDefaults_SaveOnly_f (void);

void Cvar_WriteVariables (qfile_t *f);
                                                                 
                                     

cvar_t *Cvar_FindVar (const char *var_name);
cvar_t *Cvar_FindVarAfter (const char *prev_var_name, int neededflags);

int Cvar_CompleteCountPossible (const char *partial);
const char **Cvar_CompleteBuildList (const char *partial);
                                                             
                                  
                    

                                                                        
                                                              
                                                  
                                                                     
void Cvar_List_f (void);

void Cvar_Set_f (void);
void Cvar_SetA_f (void);
void Cvar_Del_f (void);
                                                      
                                                  

                                                     
                                                  
cvar_t *Cvar_Get (const char *name, const char *value, int flags, const char *newdescription);

extern const char *cvar_dummy_description;                           
extern cvar_t *cvar_vars;                          

void Cvar_UpdateAllAutoCvars(void);                                                                                  

#ifdef FILLALLCVARSWITHRUBBISH
void Cvar_FillAll_f();
#endif                              

#endif

