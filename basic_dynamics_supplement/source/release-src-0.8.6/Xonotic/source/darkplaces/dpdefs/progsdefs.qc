  
                                                                              

                                      
                                                  

                                                                              
  

  
                 
  
entity		self;
entity		other;
entity		world;
float		time;
float		frametime;

float		force_retouch;		                                       
								                                      
								                                        
								                                      
								                                        
								                             
								                                      
								                                     
string		mapname;

float		deathmatch;
float		coop;
float		teamplay;

float		serverflags;		                                          
								                                   

float		total_secrets;
float		total_monsters;

float		found_secrets;		                          
float		killed_monsters;	                            


                                                                        
                
float		parm1, parm2, parm3, parm4, parm5, parm6, parm7, parm8, parm9, parm10, parm11, parm12, parm13, parm14, parm15, parm16;

  
                                             
  
vector		v_forward, v_up, v_right;	                       

                              
float		trace_allsolid;
float		trace_startsolid;
float		trace_fraction;
vector		trace_endpos;
vector		trace_plane_normal;
float		trace_plane_dist;
entity		trace_ent;
float		trace_inopen;
float		trace_inwater;

entity		msg_entity;				                                      

  
                          
  
void() 		main;						                   

void()		StartFrame;

void() 		PlayerPreThink;
void() 		PlayerPostThink;

void()		ClientKill;
void()		ClientConnect;
void() 		PutClientInServer;		                                        
void()		ClientDisconnect;

void()		SetNewParms;			                                         
									                                      
									                         

void()		SetChangeParms;			                                         
									                                  


                                                  
void		end_sys_globals;		                             
                                                  

  
                                                                              

                                   
                                                  

                                                                              
  

  
                                                                      
  
.float		modelindex;		                                        
.vector		absmin, absmax;	                           

.float		ltime;			                        
.float		movetype;
.float		solid;

.vector		origin;			      
.vector		oldorigin;		      
.vector		velocity;
.vector		angles;
.vector		avelocity;

.vector		punchangle;		                                          

.string		classname;		                 
.string		model;
.float		frame;
.float		skin;
.float		effects;

.vector		mins, maxs;		                                          
.vector		size;			              

.void()		touch;
.void()		use;
.void()		think;
.void()		blocked;		                                                   

.float		nextthink;
.entity		groundentity;

        
.float		health;
.float		frags;
.float		weapon;			                                   
.string		weaponmodel;
.float		weaponframe;
.float		currentammo;
.float		ammo_shells, ammo_nails, ammo_rockets, ammo_cells;

.float		items;			            

.float		takedamage;
.entity		chain;
.float		deadflag;

.vector		view_ofs;			                                 


.float		button0;		       
.float		button1;		      
.float		button2;		       

.float		impulse;		                 

.float		fixangle;
.vector		v_angle;		                                     
.float		idealpitch;		                                              


.string		netname;

.entity 	enemy;

.float		flags;

.float		colormap;
.float		team;

.float		max_health;		                                        

.float		teleport_time;	                

.float		armortype;		                                        
.float		armorvalue;

.float		waterlevel;		                                           
.float		watertype;		                   

.float		ideal_yaw;
.float		yaw_speed;

.entity		aiment;

.entity 	goalentity;		                           

.float		spawnflags;

.string		target;
.string		targetname;

                                                                
                                                               
.float		dmg_take;
.float		dmg_save;
.entity		dmg_inflictor;

.entity		owner;		                         
.vector		movedir;	                                                

.string		message;		                   

.float		sounds;		                                           

.string		noise, noise1, noise2, noise3;	                                 

                                                  
void		end_sys_fields;			                             
                                                  

  
                                                                              

                        

                                                                              
  


  
            
  

float	FALSE					= 0;
float 	TRUE					= 1;

              
float	FL_FLY					= 1;
float	FL_SWIM					= 2;
float	FL_CLIENT				= 8;	                            
float	FL_INWATER				= 16;	                                 
float	FL_MONSTER				= 32;
float	FL_GODMODE				= 64;	               
float	FL_NOTARGET				= 128;	               
float	FL_ITEM					= 256;	                                                                
float	FL_ONGROUND				= 512;	                        
float	FL_PARTIALGROUND		= 1024;	                            
float	FL_WATERJUMP			= 2048;	                              
float	FL_JUMPRELEASED			= 4096;	                      

                        
float	MOVETYPE_NONE			= 0;	              
                                 
                                
float	MOVETYPE_WALK			= 3;	               
float	MOVETYPE_STEP			= 4;	                                      
float	MOVETYPE_FLY			= 5;
float	MOVETYPE_TOSS			= 6;	          
float	MOVETYPE_PUSH			= 7;	                                   
float	MOVETYPE_NOCLIP			= 8;
float	MOVETYPE_FLYMISSILE		= 9;	                                       
float	MOVETYPE_BOUNCE			= 10;
float	MOVETYPE_BOUNCEMISSILE	= 11;	                         

                     
float	SOLID_NOT				= 0;	                                    
float	SOLID_TRIGGER			= 1;	                                  
float	SOLID_BBOX				= 2;	                       
float	SOLID_SLIDEBOX			= 3;	                                     
float	SOLID_BSP				= 4;	                                 

               
float	RANGE_MELEE				= 0;
float	RANGE_NEAR				= 1;
float	RANGE_MID				= 2;
float	RANGE_FAR				= 3;

                  

float	DEAD_NO					= 0;
float	DEAD_DYING				= 1;
float	DEAD_DEAD				= 2;
float	DEAD_RESPAWNABLE		= 3;
float	DEAD_RESPAWNING			= 4;                                            

                    

float	DAMAGE_NO				= 0;
float	DAMAGE_YES				= 1;
float	DAMAGE_AIM				= 2;

        
float	IT_AXE					= 4096;
float	IT_SHOTGUN				= 1;
float	IT_SUPER_SHOTGUN		= 2;
float	IT_NAILGUN				= 4;
float	IT_SUPER_NAILGUN		= 8;
float	IT_GRENADE_LAUNCHER		= 16;
float	IT_ROCKET_LAUNCHER		= 32;
float	IT_LIGHTNING			= 64;
float	IT_EXTRA_WEAPON			= 128;

float	IT_SHELLS				= 256;
float	IT_NAILS				= 512;
float	IT_ROCKETS				= 1024;
float	IT_CELLS				= 2048;

float	IT_ARMOR1				= 8192;
float	IT_ARMOR2				= 16384;
float	IT_ARMOR3				= 32768;
float	IT_SUPERHEALTH			= 65536;

float	IT_KEY1					= 131072;
float	IT_KEY2					= 262144;

float	IT_INVISIBILITY			= 524288;
float	IT_INVULNERABILITY		= 1048576;
float	IT_SUIT					= 2097152;
float	IT_QUAD					= 4194304;

                       

float	CONTENT_EMPTY			= -1;
float	CONTENT_SOLID			= -2;
float	CONTENT_WATER			= -3;
float	CONTENT_SLIME			= -4;
float	CONTENT_LAVA			= -5;
float	CONTENT_SKY				= -6;

float	STATE_TOP		= 0;
float	STATE_BOTTOM	= 1;
float	STATE_UP		= 2;
float	STATE_DOWN		= 3;

vector	VEC_ORIGIN = '0 0 0';
vector	VEC_HULL_MIN = '-16 -16 -24';
vector	VEC_HULL_MAX = '16 16 32';

vector	VEC_HULL2_MIN = '-32 -32 -24';
vector	VEC_HULL2_MAX = '32 32 64';

                 
float	SVC_TEMPENTITY		= 23;
float	SVC_KILLEDMONSTER	= 27;
float	SVC_FOUNDSECRET		= 28;
float	SVC_INTERMISSION	= 30;
float	SVC_FINALE			= 31;
float	SVC_CDTRACK			= 32;
float	SVC_SELLSCREEN		= 33;


float	TE_SPIKE		= 0;
float	TE_SUPERSPIKE	= 1;
float	TE_GUNSHOT		= 2;
float	TE_EXPLOSION	= 3;
float	TE_TAREXPLOSION	= 4;
float	TE_LIGHTNING1	= 5;
float	TE_LIGHTNING2	= 6;
float	TE_WIZSPIKE		= 7;
float	TE_KNIGHTSPIKE	= 8;
float	TE_LIGHTNING3	= 9;
float	TE_LAVASPLASH	= 10;
float	TE_TELEPORT		= 11;

                 
                                      
                                                                        
float	CHAN_AUTO		= 0;
float	CHAN_WEAPON		= 1;
float	CHAN_VOICE		= 2;
float	CHAN_ITEM		= 3;
float	CHAN_BODY		= 4;

float	ATTN_NONE		= 0;
float	ATTN_NORM		= 1;
float	ATTN_IDLE		= 2;
float	ATTN_STATIC		= 3;

               

float	UPDATE_GENERAL	= 0;
float	UPDATE_STATIC	= 1;
float	UPDATE_BINARY	= 2;
float	UPDATE_TEMP		= 3;

                 

float	EF_BRIGHTFIELD	= 1;
float	EF_MUZZLEFLASH 	= 2;
float	EF_BRIGHTLIGHT 	= 4;
float	EF_DIMLIGHT 	= 8;


           
float	MSG_BROADCAST	= 0;		                    
float	MSG_ONE			= 1;		                               
float	MSG_ALL			= 2;		                  
float	MSG_INIT		= 3;		                           

                                                                             

  
                    
  

void(vector ang)	makevectors		= #1;		                              
void(entity e, vector o) setorigin	= #2;
void(entity e, string m) setmodel	= #3;		                               
void(entity e, vector min, vector max) setsize = #4;
                 
void() break_to_debugger						= #6;
float() random						= #7;		                
void(entity e, float chan, string samp, float vol, float atten) sound = #8;
vector(vector v) normalize			= #9;
void(string e, ...) error				= #10;
void(string e, ...) objerror				= #11;
float(vector v) vlen				= #12;
float(vector v) vectoyaw			= #13;
entity() spawn						= #14;
void(entity e) remove				= #15;

                       
                     
                                                                
                                                  
                               
void(vector v1, vector v2, float nomonsters, entity forent) traceline = #16;

entity() checkclient				= #17;	                               
entity(entity start, .string fld, string match) find = #18;
string(string s) precache_sound		= #19;
string(string s) precache_model		= #20;
void(entity client, string s, ...)stuffcmd = #21;
entity(vector org, float rad) findradius = #22;
void(string s, ...) bprint				= #23;
void(entity client, string s, ...) sprint = #24;
void(string s, ...) dprint				= #25;
string(float f) ftos				= #26;
string(vector v) vtos				= #27;
void() coredump						= #28;		                    
void() traceon						= #29;		                          
void() traceoff						= #30;
void(entity e) eprint				= #31;		                         
float(float yaw, float dist) walkmove	= #32;	                        
                  
float() droptofloor= #34;	                          
void(float style, string value) lightstyle = #35;
float(float v) rint					= #36;		                       
float(float v) floor				= #37;		                       
float(float v) ceil					= #38;		                        
                  
float(entity e) checkbottom			= #40;		                            
float(vector v) pointcontents		= #41;		                      
                  
float(float f) fabs = #43;
vector(entity e, float speed) aim = #44;		                              
float(string s) cvar = #45;						                    
void(string s, ...) localcmd = #46;					                            
entity(entity e) nextent = #47;					                               
void(vector o, vector d, float color, float count) particle = #48;                          
void() ChangeYaw = #49;						                              
											                    
                  
vector(vector v) vectoangles			= #51;

  
                                   
  
void(float to, float f) WriteByte		= #52;
void(float to, float f) WriteChar		= #53;
void(float to, float f) WriteShort		= #54;
void(float to, float f) WriteLong		= #55;
void(float to, float f) WriteCoord		= #56;
void(float to, float f) WriteAngle		= #57;
void(float to, string s, ...) WriteString	= #58;
void(float to, entity s) WriteEntity	= #59;

  
                                      
  

                                   
                                   
                                    
                                   
                                    
                                    
                                     
                                     

void(float step) movetogoal				= #67;

string(string s) precache_file		= #68;	                             
void(entity e) makestatic		= #69;
void(string s) changelevel = #70;

                 

void(string var, string val) cvar_set = #72;	                  

void(entity client, string s, ...) centerprint = #73;	                        

void(vector pos, string samp, float vol, float atten) ambientsound = #74;

string(string s) precache_model2	= #75;		                          
string(string s) precache_sound2	= #76;		                          
string(string s) precache_file2		= #77;		                          

void(entity e) setspawnparms		= #78;		                      
												                        
												                   

                                                                              
