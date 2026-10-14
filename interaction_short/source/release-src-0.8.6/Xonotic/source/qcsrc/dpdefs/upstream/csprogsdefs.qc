  
                                                                              

                                      
                                                  

                                                                              
  

  
                 
  
entity		self;
entity		other;
entity		world;
float		time;
float		frametime;

float 		player_localentnum;	            
float 		player_localnum;	               
float		maxclients;	                                                          

float		clientcommandframe;	                 
float		servercommandframe;	                                   

string		mapname;

  
                                             
  
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

  
                          
  
void()		CSQC_Init;
void()		CSQC_Shutdown;
float(float f, float t, float n)	CSQC_InputEvent;
void(float w, float h)		CSQC_UpdateView;
float(string s)	CSQC_ConsoleCommand;

                                                             
vector		pmove_org;
vector		pmove_vel;
vector		pmove_mins;
vector		pmove_maxs;
                                                                       
float		input_timelength;
vector		input_angles;
vector		input_movevalues;	                      
float		input_buttons;		                                                    

float		movevar_gravity;
float		movevar_stopspeed;
float		movevar_maxspeed;
float		movevar_spectatormaxspeed;	                           
float		movevar_accelerate;
float		movevar_airaccelerate;
float		movevar_wateraccelerate;
float		movevar_friction;
float		movevar_waterfriction;
float		movevar_entgravity;	                                                                         

                                                  
void		end_sys_globals;		                             
                                                  

  
                                                                              

                                   
                                                  

                                                                              
  

  
                                                                      
  
.float		modelindex;		                                        
.vector		absmin, absmax;	                           

.float		entnum;	                                      
.float		drawmask;
.void()		predraw;

.float		movetype;
.float		solid;

.vector		origin;			      
.vector		oldorigin;		      
.vector		velocity;
.vector		angles;
.vector		avelocity;

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

.entity		chain;

.string		netname;

.entity 	enemy;

.float		flags;

.float		colormap;

.entity		owner;		                         

                                                  
void		end_sys_fields;			                             
                                                  

  
                                                                              

                              

                                                                              
  

                                         
float		intermission;                                                                          

vector		view_angles;                        
vector		view_punchangle;               
vector		view_punchvector;               

  
                                                                              

                       

                                                                              
  

const float MASK_ENGINE			= 1;
const float MASK_ENGINEVIEWMODELS	= 2;
const float MASK_NORMAL			= 4;

const float RF_VIEWMODEL	= 1;
const float RF_EXTERNALMODEL	= 2;
const float RF_DEPTHHACK	= 4;
const float RF_ADDITIVE		= 8;
const float RF_USEAXIS		= 16;

const float VF_MIN		= 1;	          
const float VF_MIN_X		= 2;	         
const float VF_MIN_Y		= 3;	         
const float VF_SIZE		= 4;	                          
const float VF_SIZE_Y		= 5;	         
const float VF_SIZE_X		= 6;	         
const float VF_VIEWPORT		= 7;	                  
const float VF_FOV		= 8;	          
const float VF_FOVX		= 9;	         
const float VF_FOVY		= 10;	         
const float VF_ORIGIN		= 11;	          
const float VF_ORIGIN_X		= 12;	         
const float VF_ORIGIN_Y		= 13;	         
const float VF_ORIGIN_Z		= 14;	         
const float VF_ANGLES		= 15;	          
const float VF_ANGLES_X		= 16;	         
const float VF_ANGLES_Y		= 17;	         
const float VF_ANGLES_Z		= 18;	         
const float VF_DRAWWORLD	= 19;	         
const float VF_DRAWENGINESBAR	= 20;	         
const float VF_DRAWCROSSHAIR	= 21;	         

const float VF_CL_VIEWANGLES	= 33;	          
const float VF_CL_VIEWANGLES_X	= 34;	         
const float VF_CL_VIEWANGLES_Y	= 35;	         
const float VF_CL_VIEWANGLES_Z	= 36;	         

const float VF_PERSPECTIVE      = 200;

const float STAT_HEALTH		= 0;
const float STAT_WEAPONMODEL	= 2;
const float STAT_AMMO		= 3;
const float STAT_ARMOR		= 4;
const float STAT_WEAPONFRAME	= 5;
const float STAT_SHELLS		= 6;
const float STAT_NAILS		= 7;
const float STAT_ROCKETS	= 8;
const float STAT_CELLS		= 9;
const float STAT_ACTIVEWEAPON	= 10;
const float STAT_TOTALSECRETS	= 11;
const float STAT_TOTALMONSTERS	= 12;
const float STAT_SECRETS		= 13;
const float STAT_MONSTERS		= 14;
const float STAT_ITEMS		= 15;
const float STAT_VIEWHEIGHT	= 16;

                        
const float CHAN_AUTO			= 0;
const float CHAN_WEAPON			= 1;
const float CHAN_VOICE			= 2;
const float CHAN_ITEM			= 3;
const float CHAN_BODY			= 4;

const float ATTN_NONE			= 0;
const float ATTN_NORM			= 1;
const float ATTN_IDLE			= 2;
const float ATTN_STATIC			= 3;

                      
const float FILE_READ			= 0;
const float FILE_APPEND			= 1;
const float FILE_WRITE			= 2;

                       
const float CONTENT_EMPTY					= -1;
const float CONTENT_SOLID					= -2;
const float CONTENT_WATER					= -3;
const float CONTENT_SLIME					= -4;
const float CONTENT_LAVA					= -5;
const float CONTENT_SKY						= -6;

                        
const float SOLID_NOT						= 0;
const float SOLID_TRIGGER					= 1;
const float SOLID_BBOX						= 2;
const float SOLID_SLIDEBOX					= 3;
const float SOLID_BSP						= 4;
const float SOLID_CORPSE					= 5;

                       
const float MOVE_NORMAL						= 0;
const float MOVE_NOMONSTERS					= 1;
const float MOVE_MISSILE					= 2;

                    
const float true	= 1;
const float false	= 0;
const float TRUE	= 1;
const float FALSE	= 0;

const float EXTRA_LOW = -99999999;
const float EXTRA_HIGH = 99999999;

const vector VEC_1	= '1 1 1';
const vector VEC_0	= '0 0 0';
const vector VEC_M1	= '-1 -1 -1';

const float M_PI = 3.14159265358979323846;

vector	VEC_HULL_MIN = '-16 -16 -24';
vector	VEC_HULL_MAX = '16 16 32';

                                   
const float TE_SPIKE						= 0;
const float TE_SUPERSPIKE					= 1;
const float TE_GUNSHOT						= 2;
const float TE_EXPLOSION					= 3;
const float TE_TAREXPLOSION					= 4;
const float TE_LIGHTNING1					= 5;
const float TE_LIGHTNING2					= 6;
const float TE_WIZSPIKE						= 7;
const float TE_KNIGHTSPIKE					= 8;
const float TE_LIGHTNING3					= 9;
const float TE_LAVASPLASH					= 10;
const float TE_TELEPORT						= 11;
const float TE_EXPLOSION2					= 12;
	                       
	const float TE_EXPLOSIONRGB					= 53;
	const float TE_GUNSHOTQUAD					= 57;
	const float TE_EXPLOSIONQUAD 				= 70;
	const float TE_SPIKEQUAD					= 58;
	const float TE_SUPERSPIKEQUAD				= 59;

                            
const float PFLAGS_NOSHADOW					= 1;
const float PFLAGS_CORONA					= 2;
const float PFLAGS_FULLDYNAMIC				= 128;

const float EF_ADDITIVE		= 32;
const float EF_BLUE		= 64;
const float EF_FLAME		= 1024;
const float EF_FULLBRIGHT	= 512;
const float EF_NODEPTHTEST	= 8192;
const float EF_NODRAW		= 16;
const float EF_NOSHADOW		= 4096;
const float EF_RED		= 128;
const float EF_STARDUST		= 2048;
const float EF_SELECTABLE 	= 16384;

const float PFL_ONGROUND	= 1;
const float PFL_CROUCH		= 2;
const float PFL_DEAD		= 4;
const float PFL_GIBBED		= 8;

             
const float DRAWFLAG_NORMAL = 0;
const float DRAWFLAG_ADDITIVE = 1;
const float DRAWFLAG_MODULATE = 2;
const float DRAWFLAG_2XMODULATE = 3;
const float DRAWFLAG_SCREEN = 4;
const float DRAWFLAG_MIPMAP = 0x100;                           

  
                                                                              

                      
                                            

                                                                              
  

void(vector ang) makevectors = #1;
void(entity e, vector o) setorigin = #2;
void(entity e, string m) setmodel = #3;
void(entity e, vector min, vector max) setsize = #4;

void() break_to_debugger = #6;
float() random = #7;
void(entity e, float chan, string samp, float volume, float atten, ...) sound = #8;
vector(vector v) normalize = #9;
void(string e) error = #10;
void(string e) objerror = #11;
float(vector v) vlen = #12;
float(vector v) vectoyaw = #13;
entity() spawn = #14;
void(entity e) remove = #15;
float(vector v1, vector v2, float tryents, entity ignoreentity) traceline = #16;

entity(entity start, .string fld, string match) find = #18;
void(string s) precache_sound = #19;
void(string s) precache_model = #20;

entity(vector org, float rad) findradius = #22;

void(string s, ...) dprint = #25;
string(float f) ftos = #26;
string(vector v) vtos = #27;
void() coredump = #28;
void() traceon = #29;
void() traceoff = #30;
void(entity e) eprint = #31;
                    
float(float yaw, float dist, float settrace) walkmove = #32;

float() droptofloor = #34;
void(float style, string value) lightstyle = #35;
float(float v) rint = #36;
float(float v) floor = #37;
float(float v) ceil = #38;

float(entity e) checkbottom = #40;
float(vector v) pointcontents = #41;

float(float f) fabs = #43;

float(string s) cvar = #45;
void(string s, ...) localcmd = #46;
entity(entity e) nextent = #47;
void(vector o, vector d, float color, float count) particle = #48;
void() ChangeYaw = #49;

vector(vector v) vectoangles = #51;
vector(vector v, vector w) vectoangles2 = #51;

float(float f) sin = #60;
float(float f) cos = #61;
float(float f) sqrt = #62;
void(entity ent) changepitch = #63;
void(entity e, entity ignore) tracetoss = #64;
string(entity ent) etos = #65;

string(string s) precache_file = #68;
void(entity e) makestatic = #69;

void(string var, string val) cvar_set = #72;

void(vector pos, string samp, float vol, float atten) ambientsound = #74;
string(string s) precache_model2 = #75;
string(string s) precache_sound2 = #76;
string(string s) precache_file2 = #77;

float(string s) stof = #81;


void(vector v1, vector min, vector max, vector v2, float nomonsters, entity forent) tracebox = #90;
vector() randomvec = #91;
vector(vector org) getlight = #92;
vector(vector org, float lpflags) getlight2 = #92;
vector getlight_dir;
vector getlight_ambient;
vector getlight_diffuse;
const float LP_LIGHTMAP	= 1;
const float LP_RTWORLD = 2;
const float LP_DYNLIGHT = 4;
const float LP_COMPLETE = 7;

float(string name, string value) registercvar = #93;
float( float a, ... ) min = #94;
float( float b, ... ) max = #95;
float(float minimum, float val, float maximum) bound = #96;
float(float f, float f) pow = #97;
entity(entity start, .float fld, float match) findfloat = #98;
entity(entity start, .entity fld, entity match) findentity = #98;
float(string s) checkextension = #99;
                                      

float(string filename, float mode) fopen = #110;
void(float fhandle) fclose = #111;
string(float fhandle) fgets = #112;
void(float fhandle, string s) fputs = #113;
float(string s) strlen = #114;
string(...) strcat = #115;
string(string s, float start, float length) substring = #116;
vector(string) stov = #117;
string(string s) strzone = #118;
void(string s) strunzone = #119;
void(string s, float chan, float vol) localsound = #177;

                        

float(float number, float quantity) bitshift = #218;

                                                                   
float(string str, string sub, float startpos) strstrofs = #221;
float(string str, float ofs) str2chr = #222;
string(float c, ...) chr2str = #223;
string(float ccase, float calpha, float cnum, string s, ...) strconv = #224;
string(float chars, string s, ...) strpad = #225;
string(string info, string key, string value, ...) infoadd = #226;
string(string info, string key) infoget = #227;
float(string s1, string s2) strcmp = #228;
float(string s1, string s2, float len) strncmp = #228;
float(string s1, string s2) strcasecmp = #229;
float(string s1, string s2, float len) strncasecmp = #230;

                       
void() clearscene = #300;
void(float mask) addentities = #301;
void(entity ent) addentity = #302;
float(float property, ...) setproperty = #303;
float(float property) getproperty = #309;
vector(float property) getpropertyvec = #309;
void() renderscene = #304;
void(vector org, float radius, vector lightcolours) adddynamiclight = #305;
void(vector org, float radius, vector lightcolours, float style, string cubemapname, float pflags) adddynamiclight2 = #305;
                                                                                        
void(string texturename, float flag, ...) R_BeginPolygon = #306;
void(vector org, vector texcoords, vector rgb, float alpha) R_PolygonVertex = #307;
void() R_EndPolygon = #308;
vector (vector v) cs_unproject = #310;
vector (vector v) cs_project = #311;

void(float width, vector pos1, vector pos2, vector rgb, float alpha, float flag) drawline = #315;
float(string name) iscachedpic = #316;
string(string name, ...) precache_pic = #317;
string(string name) precache_cubemap = #317;
vector(string picname) draw_getimagesize = #318;
void(string name) freepic = #319;
float(vector position, float character, vector scale, vector rgb, float alpha, float flag) drawcharacter = #320;
float(vector position, string text, vector scale, vector rgb, float alpha, float flag) drawstring = #321;
float(vector position, string pic, vector size, vector rgb, float alpha, float flag) drawpic = #322;
float(vector position, vector size, vector rgb, float alpha, float flag) drawfill = #323;
void(float x, float y, float width, float height) drawsetcliparea = #324;
void(void) drawresetcliparea = #325;
float(vector position, string text, vector scale, float alpha, float flag) drawcolorcodedstring = #326;
vector(vector position, string text, vector scale, vector rgb, float alpha, float flag) drawcolorcodedstring2 = #326;

float(float stnum) getstatf = #330;
float(float stnum, ...) getstati = #331;                                           
string(float firststnum) getstats = #332;
void(entity e, float mdlindex) setmodelindex = #333;
string(float mdlindex) modelnameforindex = #334;
float(string effectname) particleeffectnum = #335;
void(entity ent, float effectnum, vector start, vector end) trailparticles = #336;
                                                                                         
void(float effectnum, vector origin , vector dir, float count) pointparticles = #337;
void(string s, ...) centerprint = #338;
void(string s, ...) print = #339;
string(float keynum) keynumtostring = #340;
float(string keyname) stringtokeynum = #341;
string(float keynum) getkeybind = #342;
void(float usecursor) setcursormode = #343;
vector() getmousepos = #344;
float(float framenum) getinputstate = #345;
void(float sens) setsensitivityscale = #346;
void(...) runstandardplayerphysics = #347;                                         
string(float playernum, string keyname) getplayerkeyvalue = #348;
float() isdemo = #349;
float() isserver = #350;
void(vector origin, vector forward, vector right, vector up) SetListener = #351;
void(string cmdname) registercommand = #352;
float(entity ent) wasfreed = #353;
string(string key) serverkey = #354;

                                                      
float() ReadByte = #360;
float() ReadChar = #361;
float() ReadShort = #362;
float() ReadLong = #363;
float() ReadCoord = #364;
float() ReadAngle = #365;
string() ReadString = #366;
float() ReadFloat = #367;

                              
void(entity from, entity to) copyentity = #400;

entity(.string fld, string match) findchain = #402;
entity(.float fld, float match) findchainfloat = #403;
void(vector org, string modelname, float startframe, float endframe, float framerate) effect = #404;
void(vector org, vector velocity, float howmany) te_blood = #405;
void(vector mincorner, vector maxcorner, float explosionspeed, float howmany) te_bloodshower = #406;
void(vector org, vector color) te_explosionrgb = #407;
void(vector mincorner, vector maxcorner, vector vel, float howmany, float color, float gravityflag, float randomveljitter) te_particlecube = #408;
void(vector mincorner, vector maxcorner, vector vel, float howmany, float color) te_particlerain = #409;
void(vector mincorner, vector maxcorner, vector vel, float howmany, float color) te_particlesnow = #410;
void(vector org, vector vel, float howmany) te_spark = #411;
void(vector org) te_gunshotquad = #412;
void(vector org) te_spikequad = #413;
void(vector org) te_superspikequad = #414;
void(vector org) te_explosionquad = #415;
void(vector org) te_smallflash = #416;
void(vector org, float radius, float lifetime, vector color) te_customflash = #417;
void(vector org) te_gunshot = #418;
void(vector org) te_spike = #419;
void(vector org) te_superspike = #420;
void(vector org) te_explosion = #421;
void(vector org) te_tarexplosion = #422;
void(vector org) te_wizspike = #423;
void(vector org) te_knightspike = #424;
void(vector org) te_lavasplash = #425;
void(vector org) te_teleport = #426;
void(vector org, float colorstart, float colorlength) te_explosion2 = #427;
void(entity own, vector start, vector end) te_lightning1 = #428;
void(entity own, vector start, vector end) te_lightning2 = #429;
void(entity own, vector start, vector end) te_lightning3 = #430;
void(entity own, vector start, vector end) te_beam = #431;
void(vector dir) vectorvectors = #432;
void(vector org) te_plasmaburn = #433;
float(entity e, float s) getsurfacenumpoints = #434;
vector(entity e, float s, float n) getsurfacepoint = #435;
vector(entity e, float s) getsurfacenormal = #436;
string(entity e, float s) getsurfacetexture = #437;
float(entity e, vector p) getsurfacenearpoint = #438;
vector(entity e, float s, vector p) getsurfaceclippedpoint = #439;

float(string s) tokenize = #441;
string(float n) argv = #442;
void(entity e, entity tagentity, string tagname) setattachment = #443;
float(string pattern, float caseinsensitive, float quiet) search_begin = #444;
void(float handle) search_end = #445;
float(float handle) search_getsize = #446;
string(float handle, float num) search_getfilename = #447;
string(string s) cvar_string = #448;
entity(entity start, .float fld, float match) findflags = #449;
entity(.float fld, float match) findchainflags = #450;
float(entity ent, string tagname) gettagindex = #451;
vector(entity ent, float tagindex) gettaginfo = #452;

void(vector org, vector vel, float howmany) te_flamejet = #457;

entity(float num) entitybyindex = #459;
float() buf_create = #460;
void(float bufhandle) buf_del = #461;
float(float bufhandle) buf_getsize = #462;
void(float bufhandle_from, float bufhandle_to) buf_copy = #463;
void(float bufhandle, float sortpower, float backward) buf_sort = #464;
string(float bufhandle, string glue) buf_implode = #465;
string(float bufhandle, float string_index) bufstr_get = #466;
void(float bufhandle, float string_index, string str) bufstr_set = #467;
float(float bufhandle, string str, float order) bufstr_add = #468;
void(float bufhandle, float string_index) bufstr_free = #469;

float(float s) asin = #471;
float(float c) acos = #472;
float(float t) atan = #473;
float(float c, float s) atan2 = #474;
float(float a) tan = #475;
float(string s) strippedstringlen = #476;
float(string s) strlennocol = #476;                                                                                              
string(string s) decolorizedstring = #477;
string(string s) strdecolorize = #477;                                                                                              
string(float uselocaltime, string format, ...) strftime = #478;
string(string s) strtolower = #480;
string(string s) strtoupper = #481;
string(string s) cvar_defstring = #482;
void(vector origin, string sample, float volume, float attenuation) pointsound = #483;
string(string search, string replace, string subject) strreplace = #484;
string(string search, string replace, string subject) strireplace = #485;
vector(entity e, float s, float n, float a) getsurfacepointattribute = #486;
#ifdef SUPPORT_GECKO
float gecko_create( string name ) = #487;
void gecko_destroy( string name ) = #488;
void gecko_navigate( string name, string URI ) = #489;
float gecko_keyevent( string name, float key, float eventtype ) = #490;
void gecko_mousemove( string name, float x, float y ) = #491;
void gecko_resize( string name, float w, float h ) = #492;
vector gecko_get_texture_extent( string name ) = #493;
#else

#endif

  
                                                                              

                        

                                                                              
  

                        
               
                                    
                        
                          
float PT_ALPHASTATIC = 1;
float PT_STATIC = 2;
float PT_SPARK = 3;
float PT_BEAM = 4;
float PT_RAIN = 5;
float PT_RAINDECAL = 6;
float PT_SNOW = 7;
float PT_BUBBLE = 8;
float PT_BLOOD = 9;
float PT_SMOKE = 10;
float PT_DECAL = 11;
float PT_ENTITYPARTICLE = 12;
                       
float PBLEND_ALPHA = 0;
float PBLEND_ADD = 1;
float PBLEND_INVMOD = 2;
                        
float PARTICLE_BILLBOARD = 0;
float PARTICLE_SPARK = 1;
float PARTICLE_ORIENTED_DOUBLESIDED = 2;
float PARTICLE_BEAM = 3;
                      
float particle_type;              
float particle_blendmode;                         
float particle_orientation;                           
vector particle_color1;
vector particle_color2;
float particle_tex;                                   
float particle_size;
float particle_sizeincrease;
float particle_alpha;
float particle_alphafade;
float particle_time;
float particle_gravity;
float particle_bounce;
float particle_airfriction;
float particle_liquidfriction;
float particle_originjitter;
float particle_velocityjitter;
float particle_qualityreduction;                                                   
float particle_stretch;
vector particle_staincolor1;
vector particle_staincolor2;
float particle_staintex;
float particle_stainalpha;
float particle_stainsize;
float particle_delayspawn;
float particle_delaycollision;
float particle_angle;
float particle_spin;
                       
float(float max_themes) initparticlespawner = #522;                                                                                                               
void() resetparticle = #523;                                        
void(float theme) particletheme = #524;                                       
float() particlethemesave = #525;                                                              
void(float theme) particlethemeupdate = #525;                                                              
void(float theme) particlethemefree = #526;                           
float(vector org, vector vel) spawnparticle = #527;                                         
float(vector org, vector vel, float theme) quickparticle = #527;                                                                          
float(vector org, vector vel, float delay, float collisiondelay) delayedparticle = #528;
float(vector org, vector vel, float delay, float collisiondelay, float theme) quickdelayedparticle = #528;
                                                                                  
                                                                                  
                                                                                                   
         
                                                         
                                                            
                                                       
                                                                                                               
                                  
                                                                                                                          
void() printparticle =
{
	                                                                                  
	print("PARTICLE:\n");
	print(strcat("  type: ", ftos(particle_type), "\n"));
	print(strcat("  blendmode: ", ftos(particle_blendmode), "\n"));
	print(strcat("  orientation: ", ftos(particle_orientation), "\n"));
	print(strcat("  color1: ", vtos(particle_color1), "\n"));
	print(strcat("  color2: ", vtos(particle_color2), "\n"));
	print(strcat("  tex: ", ftos(particle_tex), "\n"));
	print(strcat("  size: ", ftos(particle_size), "\n"));
	print(strcat("  sizeincrease: ", ftos(particle_sizeincrease), "\n"));
	print(strcat("  alpha: ", ftos(particle_alpha), "\n"));
	print(strcat("  alphafade: ", ftos(particle_alphafade), "\n"));
	print(strcat("  time: ", ftos(particle_time), "\n"));
	print(strcat("  gravity: ", ftos(particle_gravity), "\n"));
	print(strcat("  bounce: ", ftos(particle_bounce), "\n"));
	print(strcat("  airfriction: ", ftos(particle_airfriction), "\n"));
	print(strcat("  liquidfriction: ", ftos(particle_liquidfriction), "\n"));
	print(strcat("  originjitter: ", ftos(particle_originjitter), "\n"));
	print(strcat("  velocityjitter: ", ftos(particle_velocityjitter), "\n"));
	print(strcat("  qualityreduction: ", ftos(particle_qualityreduction), "\n"));
	print(strcat("  stretch: ", ftos(particle_stretch), "\n"));
	print(strcat("  staincolor1: ", vtos(particle_staincolor1), "\n"));
	print(strcat("  staincolor2: ", vtos(particle_staincolor2), "\n"));
	print(strcat("  staintex: ", ftos(particle_staintex), "\n"));
	print(strcat("  stainalpha: ", ftos(particle_stainalpha), "\n"));
	print(strcat("  stainsize: ", ftos(particle_stainsize), "\n"));
	print(strcat("  delayspawn: ", ftos(particle_delayspawn), "\n"));
	print(strcat("  delaycollision: ", ftos(particle_delaycollision), "\n"));
	print(strcat("  angle: ", ftos(particle_angle), "\n"));
	print(strcat("  spin: ", ftos(particle_spin), "\n"));
}

                                          
               
                                    
float RF_USETRANSPARENTOFFSET = 64;                                         
                     
float transparent_offset;                                        
                                                                                                                                                                                                            
                                                                                                     
                                            

                            
               
                                    
const float RF_WORLDOBJECT = 128;
                                                                                                                         
                                                                                 

                           
               
                                    
const float RF_MODELLIGHT = 4096;
.vector modellight_ambient;
.vector modellight_diffuse;
.vector modellight_dir;
                                                                             

                   
               
                                    
                       
void(float ispaused) setpause = #531;
                                                                                                           
                                                                                          

                            
               
                                    
                        
                        
float E_ACTIVE 	    = 0;             
float E_ORIGIN      = 1;          
float E_FORWARD     = 2;          
float E_RIGHT       = 3;          
float E_UP          = 4;          
float E_SCALE       = 5;         
float E_ORIGINANDVECTORS = 6;                                                     
float E_ALPHA       = 7;         
float E_COLORMOD    = 8;          
float E_PANTSCOLOR  = 9;          
float E_SHIRTCOLOR  = 10;          
float E_SKIN        = 11;         
float E_MINS        = 12;          
float E_MAXS        = 13;          
float E_ABSMIN      = 14;          
float E_ABSMAX      = 15;          
float E_LIGHT       = 16;                       
                       
float(float entitynum, float fldnum) getentity = #504;
vector(float entitynum, float fldnum) getentityvec = #504;
                                                                                                         
                                                                                                                 
                                                                                                                            
                                                                                                                                

              
                         
                                   
                   
                                              
                                                                            
                                                              
                                              
                                                            
                                     
                                                                  
                                                             
                                                          
                   
                       
float drawfont;                                                          
float FONT_DEFAULT = 0;                
float FONT_CONSOLE = 1;                                                    
float FONT_SBAR = 2;                                                  
float FONT_NOTIFY = 3;                                       
float FONT_CHAT = 4;                
float FONT_CENTERPRINT = 5;                
float FONT_INFOBAR = 6;                
float FONT_MENU = 7;                                       
float FONT_USER0 = 8;                                   
float FONT_USER1 = 9;                                   
float FONT_USER2 = 10;                                  
float FONT_USER3 = 11;                                  
float FONT_USER4 = 12;                                  
float FONT_USER5 = 13;                                  
float FONT_USER6 = 14;                                  
float FONT_USER7 = 15;                                       
                      
float findfont(string s) = #356;                                               
float loadfont(string fontname, string fontmaps, string sizes, float slot, float fix_scale, float fix_voffset) = #357;
                                                                                       
                                                            
                                                                 
                                                                                   
                                                                                             
                                                               
                                                                                    
                                                                                      
                                                                                          
float stringwidth(string text, float allowColorCodes, vector size) = #327;                                                       
float stringwidth_menu(string text, float allowColorCodes, vector size) = #468;                                          
                                                                       
          
                               
                        
                        

                       
                         
                                   
                   
                                                                                                                    
                                                          
                                                                                                                                
                                                              
                                                        
                                                                                                  
                                                                                                  
                                                                                                 
                                                         
                                                                         
                                                     

                  
                        
                                      
                      
string(float key, float bindmap) getkeybind_bindmap = #342;
float(float key, string bind, float bindmap) setkeybind_bindmap = #630;
vector(void) getbindmaps = #631;
float(vector bm) setbindmaps = #632;
string(string command, float bindmap) findkeysforcommand = #610;
                                                                
                                                                   
                                                                        
           

           
                 
                                      
                             
float(string url, float id, string content_type, string delim, float buf, float keyid) crypto_uri_postbuf = #513;
              
                                                        

                  
                 
                                      
                       
const float VF_MAINVIEW         = 400;
                                                                             
                                                                              
                                                                       
                                                    
                                                                            

                        
                 
                                      
                       
const float VF_MINFPS_QUALITY   = 401;
                                                                             
                                     

                           
                           
                 
                                      
                      
void(entity e, float refdefflags) V_CalcRefdef = #640;
                       
float PMF_DUCKED = 4;
float PMF_ONGROUND = 8;
float REFDEFFLAG_TELEPORTED = 1;
float REFDEFFLAG_JUMPING = 2;
float REFDEFFLAG_DEAD = 4;
float REFDEFFLAG_INTERMISSION = 8;
                                                             
                                                                        
                                                     
                                                            
                                                                               
                                                                               
                                                                                 
                                                                                      
                                    

                    
float	drawsubpic(vector position, vector size, string pic, vector srcPosition, vector srcSize, vector rgb, float alpha, float flag) = #328;
vector	drawgetimagesize(string pic) = #318;
#define SPA_POSITION 0
#define SPA_S_AXIS 1
#define SPA_T_AXIS 2
#define SPA_R_AXIS 3
#define SPA_TEXCOORDS0 4
#define SPA_LIGHTMAP0_TEXCOORDS 5
#define SPA_LIGHTMAP_COLOR 6
                                                             
                                                                  
                                                           
                                                            
                                                              
                                                                          
                                                                               
float(entity e, float s) getsurfacenumtriangles = #628;
vector(entity e, float s, float n) getsurfacetriangle = #629;

                            
            
                                      
                       
float DEG2RAD = 0.0174532925199432957692369076848861271344287188854172545609719144;
float RAD2DEG = 57.2957795130823208767981548141051703324054724665643215491602438612;
float PI      = 3.1415926535897932384626433832795028841971693993751058209749445923;
                      
                       
                                                                                                                             
                                                                                                                   
                                                                                                                             
                                                                                                                                                                                                                            
                                                                                                                                                                     
  
              
                                                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                  

               
                 
                                      
                      
string(string format, ...) sprintf = #627;
              
                     
                  
     
                                                                                          
                
                                                                                                      
                                                                                                 
                                                                                                                  
                
                                                                                                                             
                                                                                                                             
                                                                                                                                         
                                                                                                                                   
                      
                                                                                                                           
                                                                               
                                                                               
                                                                               
                                     

               
             
                                             
                       
float GETTIME_FRAMESTART = 0;                          
float GETTIME_REALTIME = 1;                                     
float GETTIME_HIRES = 2;                                                                                        
float GETTIME_UPTIME = 3;                                  
                      
float(float tmr) gettime = #519;
              
                         

                       
                 
                                      
                       
float GETTIME_CDTRACK = 4;
              
                                                                          
                                                                                 

                           
                                   
                                      
                      
float(string s, string separator1, ...) tokenizebyseparator = #479;
              
                                                                                           
                                                    
                                               
                                                                                                                                               

                        
                 
                                      
                      
float(string s) tokenize_console = #514;
float(float i) argv_start_index = #515;
float(float i) argv_end_index = #516;
              
                                                                   
                                                                                                                    
                                                                                                                                                                

                    
                    
                 
                                      
                      
void(entity e, float chan, string samp, float vol, float atten, float speed, float flags) sound7 = #8;
float SOUNDFLAG_RELIABLE = 1;
              
                                     
                        
                                                                                
                                                                         
                                                                        
                                                                               
                                                              
                                                                            
                                                                         
                                                          
                                                                      
                                                                               
                                                                              
                                                                             
                               
                                                                               
                                       
                                                                               
                                                                               
                                    

                       
                 
                                      
                       
float PRECACHE_PIC_FROMWAD = 1;                                         
float PRECACHE_PIC_NOTPERSISTENT = 2;                                           
float PRECACHE_PIC_MIPMAP = 8;                                                                        
                                                                                

                                
                 
                                      
                       
float MOVE_WORLDONLY = 3;
              
                                                                                                                                                            

                     
              
                                   
                       
float(entity e, float channel) getsoundtime = #533;                                                                                      
float(string sample) soundlength = #534;                                                                                                                   
                                                                                                                                                       
                                                                                                                                 
                                                                                                                     
                  
                             
                                              
                              
               

                     
              
                                   
                                                        
float(entity num) num_for_edict = #512;

                                      
                 
                                      
          
.float dphitcontentsmask;                                                                                                                                                                                                                                                                                                                                                               
float trace_dpstartcontents;                                                
float trace_dphitcontents;                                                                                                                   
float trace_dphitq3surfaceflags;                                            
string trace_dphittexturename;                                    
            
float DPCONTENTS_SOLID = 1;                                    
float DPCONTENTS_WATER = 2;
float DPCONTENTS_SLIME = 4;
float DPCONTENTS_LAVA = 8;
float DPCONTENTS_SKY = 16;
float DPCONTENTS_BODY = 32;                                    
float DPCONTENTS_CORPSE = 64;                             
float DPCONTENTS_NODROP = 128;                                            
float DPCONTENTS_PLAYERCLIP = 256;                          
float DPCONTENTS_MONSTERCLIP = 512;                           
float DPCONTENTS_DONOTENTER = 1024;                 
float DPCONTENTS_LIQUIDSMASK = 14;                        
float DPCONTENTS_BOTCLIP = 2048;                 
float DPCONTENTS_OPAQUE = 4096;                                                                               
float Q3SURFACEFLAG_NODAMAGE = 1;
float Q3SURFACEFLAG_SLICK = 2;                        
float Q3SURFACEFLAG_SKY = 4;                                                   
float Q3SURFACEFLAG_LADDER = 8;                     
float Q3SURFACEFLAG_NOIMPACT = 16;                                                                       
float Q3SURFACEFLAG_NOMARKS = 32;                                                                           
float Q3SURFACEFLAG_FLESH = 64;                                                            
float Q3SURFACEFLAG_NODRAW = 128;                                       
                                                                        
                                                                        
                                                                               
                                                                               
float Q3SURFACEFLAG_METALSTEPS = 4096;                                                         
float Q3SURFACEFLAG_NOSTEPS = 8192;                                                           
float Q3SURFACEFLAG_NONSOLID = 16384;                                       
                                                                                 
                                                                                 
                                                                               
                                                                                             
              
                                                                        
                                                                             
                                                                      
                                                                              
                                                                           
                                                                           
                                                                              

                 
                 
                                      
                      
float(string name) cvar_type = #495;
float CVAR_TYPEFLAG_EXISTS = 1;
float CVAR_TYPEFLAG_SAVED = 2;
float CVAR_TYPEFLAG_PRIVATE = 4;
float CVAR_TYPEFLAG_ENGINE = 8;
float CVAR_TYPEFLAG_HASDESCRIPTION = 16;
float CVAR_TYPEFLAG_READONLY = 32;

             
                 
                                      
                                                                                                                                              
                                                                               
float(float caseinsensitive, string s, ...) crc16 = #494;

                 
                 
                                      
                      
string(string filename) whichpack = #503;
              
                                                                                        
                                 
                                        

                  
                 
                                      
                             
string(string in) uri_escape = #510;
string(string in) uri_unescape = #511;

              
                       
                                      
                      
string(string digest, string data, ...) digest_hex = #639;
              
                                          
                                                      
                                            
                                                               
                                                                      

                     
                       
                                      
              
                                         

           
                                      
                      
float log(float f) = #532;
              
           

                          
                        
                                      
                      
                                                         
                                                 
float(float modlindex) skel_create = #263;                                                                                                                                                                                                                                                                                                                                      
float(float skel, entity ent, float modlindex, float retainfrac, float firstbone, float lastbone) skel_build = #264;                                                                                                                                                                                                                                                                                                                                                                                              
float(float skel) skel_get_numbones = #265;                                                                                      
string(float skel, float bonenum) skel_get_bonename = #266;                                                                                                              
float(float skel, float bonenum) skel_get_boneparent = #267;                                                                                                                                                                 
float(float skel, string tagname) skel_find_bone = #268;                                                                                                                                                        
vector(float skel, float bonenum) skel_get_bonerel = #269;                                                                                                                                   
vector(float skel, float bonenum) skel_get_boneabs = #270;                                                                                                                      
void(float skel, float bonenum, vector org) skel_set_bone = #271;                                                                                                                                  
void(float skel, float bonenum, vector org) skel_mul_bone = #272;                                                                                                                                                          
void(float skel, float startbone, float endbone, vector org) skel_mul_bones = #273;                                                                                                                                                                
void(float skeldst, float skelsrc, float startbone, float endbone) skel_copybones = #274;                                                                                                                          
void(float skel) skel_delete = #275;                                                                                                                                          
float(float modlindex, string framename) frameforname = #276;                                                                                    
float(float modlindex, float framenum) frameduration = #277;                                                                                                                                                                                   
         
.float skeletonindex;                                                          
.float frame;                                                                                  
.float frame2;                                                        
.float frame3;                                                        
.float frame4;                                                          
.float lerpfrac;                                
.float lerpfrac3;                                
.float lerpfrac4;                                
.float frame1time;                                      
.float frame2time;                                      
.float frame3time;                                      
.float frame4time;                                      
              
                                                                              
  
                                                                                      
  
        
                                                                                                                       
                                                                                                                                                                      
                                                                                                                                                        
                                                                                                                                                                                   
  
                   
                                       
                                                                                  
                                                                                                                    
                                                                            
  
  
  
                         
  
                                                                         
                                                                           
                                                                     
                                                                         
float(float skel, float bonenum, string g1, string g2, string g3, string g4, string g5, string g6) example_skel_findbonegroup =
{
	local string bonename;
	while (bonenum >= 0)
	{
		bonename = skel_get_bonename(skel, bonenum);
		if (bonename == g1) return 1;
		if (bonename == g2) return 2;
		if (bonename == g3) return 3;
		if (bonename == g4) return 4;
		if (bonename == g5) return 5;
		if (bonename == g6) return 6;
		bonenum = skel_get_boneparent(skel, bonenum);
	}
	return 0;
};
                                                                 
void() example_skel_player_setup =
{
	self.skeletonindex = skel_create(self.modelindex);
};
                                                
                                                                     
void(float animmodelindex, float framegroup, float framegroupstarttime) example_skel_player_update_begin =
{
	                                    
	self.frame = framegroup;
	self.frame2 = 0;
	self.frame3 = 0;
	self.frame4 = 0;
	self.frame1time = framegroupstarttime;
	self.frame2time = 0;
	self.frame3time = 0;
	self.frame4time = 0;
	self.lerpfrac = 0;
	self.lerpfrac3 = 0;
	self.lerpfrac4 = 0;
	skel_build(self.skeletonindex, self, animmodelindex, 0, 0, 100000);
};
                                                                          
void(float animmodelindex, float framegroup, float framegroupstarttime, float blendalpha, string groupbonename, string excludegroupname1, string excludegroupname2) example_skel_player_update_applyoverride =
{
	local float bonenum;
	local float numbones;
	self.frame = framegroup;
	self.frame2 = 0;
	self.frame3 = 0;
	self.frame4 = 0;
	self.frame1time = framegroupstarttime;
	self.frame2time = 0;
	self.frame3time = 0;
	self.frame4time = 0;
	self.lerpfrac = 0;
	self.lerpfrac3 = 0;
	self.lerpfrac4 = 0;
	bonenum = 0;
	numbones = skel_get_numbones(self.skeletonindex);
	while (bonenum < numbones)
	{
		if (example_skel_findbonegroup(self.skeletonindex, bonenum, groupbonename, excludegroupname1, excludegroupname2, "", "", "") == 1)
			skel_build(self.skeletonindex, self, animmodelindex, 1 - blendalpha, bonenum, bonenum + 1);
		bonenum = bonenum + 1;
	}
};
                                                                                                          
void(vector eyetarget, string bonename) example_skel_player_update_eyetarget =
{
	local float bonenum;
	local vector ang;
	local vector oldforward, oldright, oldup;
	local vector relforward, relright, relup, relorg;
	local vector boneforward, boneright, boneup, boneorg;
	local vector parentforward, parentright, parentup, parentorg;
	local vector u, v;
	local vector modeleyetarget;
	bonenum = skel_find_bone(self.skeletonindex, bonename) - 1;
	if (bonenum < 0)
		return;
	oldforward = v_forward;
	oldright = v_right;
	oldup = v_up;
	v = eyetarget - self.origin;
	modeleyetarget_x =   v * v_forward;
	modeleyetarget_y = 0-v * v_right;
	modeleyetarget_z =   v * v_up;
	                                                           
	                                   
	relorg = skel_get_bonerel(self.skeletonindex, bonenum);
	relforward = v_forward;
	relright = v_right;
	relup = v_up;
	boneorg = skel_get_boneabs(self.skeletonindex, bonenum);
	boneforward = v_forward;
	boneright = v_right;
	boneup = v_up;
	parentorg = skel_get_boneabs(self.skeletonindex, skel_get_boneparent(self.skeletonindex, bonenum));
	parentforward = v_forward;
	parentright = v_right;
	parentup = v_up;
	                                                
	u = modeleyetarget - boneorg;
	                                                                             
	v_x = u * parentforward;
	v_y = u * parentright;
	v_z = u * parentup;
	ang = vectoangles2(v, relup);
	ang_x = 0 - ang_x;
	makevectors(ang);
	                               
	skel_set_bone(self.skeletonindex, bonenum, relorg);
	                              
	v_forward = oldforward;
	v_right = oldright;
	v_up = oldup;
};
                                          
                                                                          
void() example_skel_player_delete =
{
	skel_delete(self.skeletonindex);
	self.skeletonindex = 0;
};
  
                                               
  

                  
               
                                    
                      
float() numentityfields = #496;
string(float fieldnum) entityfieldname = #497;
float(float fieldnum) entityfieldtype = #498;
string(float fieldnum, entity ent) getentityfieldstring = #499;
float(float fieldnum, entity ent, string s) putentityfieldstring = #500;
            
                             
float FIELD_STRING   = 1;
float FIELD_FLOAT    = 2;
float FIELD_VECTOR   = 3;
float FIELD_ENTITY   = 4;
float FIELD_FUNCTION = 6;
              
                                                                                                                                                      
                                                                                                              
                                                                                                                   
                                                                                        
                                                                                                                                                   
                                                                                                                                                                               
                                                                                           

                    
void(string s) loadfromdata = #529;
void(string s) loadfromfile = #530;
void(string s) callfunction = #605;
void(float fh, entity e) writetofile = #606;
float(string s) isfunction = #607;
void(entity e, string s) parseentitydata = #608;

             
                 
                                      
                       
void coverage() = #642;                                                                                                                  

                          
             
                                  
                      
float(string pattern, float caseinsensitive, float quiet, string packfile) search_packfile_begin = #444;
              
                                                                                                                                                                                                                                                                                                                                                                        
                                                                                                               

                    
const float		STAT_MOVEVARS_TICRATE           = 240;
const float		STAT_MOVEVARS_TIMESCALE         = 241;
const float		STAT_FRAGLIMIT					= 235;
const float		STAT_TIMELIMIT					= 236;
const float     STAT_MOVEVARS_GRAVITY           = 242;
string(void)						ReadPicture = #501;
float PARTICLES_USEALPHA = 1;
float particles_alphamin, particles_alphamax;
float PARTICLES_USECOLOR = 2;
vector particles_colormin, particles_colormax;
float PARTICLES_USEFADE = 4;                                                         
float particles_fade;
float PARTICLES_DRAWASTRAIL = 128;
void(float effectindex, entity own, vector org_from, vector org_to, vector dir_from, vector dir_to, float countmultiplier, float flags) boxparticles = #502;
float trace_networkentity;
const float RF_FULLBRIGHT	= 256;
const float RF_NOSHADOW	= 512;
float RF_DYNAMICMODELLIGHT = 8192;

float gettaginfo_parent;
string gettaginfo_name;
vector gettaginfo_offset;
vector gettaginfo_forward;
vector gettaginfo_right;
vector gettaginfo_up;
float checkpvs(vector viewpos, entity viewee) = #240;
                                                                                              
                                                  
