                                                          
              

entity self;

                                                         
void		end_sys_globals;
                                                         
             

                                                         
void		end_sys_fields;
                                                         
                

void() m_init;
void(float keynr, float ascii) m_keydown;
void(float width, float height) m_draw;
void(float mode) m_toggle;
void() m_shutdown;
                                                 

                                                         
                
                           
                     

float KEY_UNKNOWN	= 	-1;
float KEY_GAME 		=	0;
float KEY_MENU		=	2;
float KEY_MENU_GRABBED	= 	3;

                           
                 

float FILE_READ = 0;
float FILE_APPEND = 1;
float FILE_WRITE = 2;

                           
                                            

float TRUE 	= 1;
float FALSE = 0;

                           
                    

float true = 1;
float false = 0;

                           
                

float MSG_BROADCAST		= 0;		                    
float MSG_ONE			= 1;		                               
float MSG_ALL			= 2;		                  
float MSG_INIT			= 3;		                           

                             
                         

float MT_MENU = 1;
float MT_CLIENT = 2;

                         
                         

float CS_DEDICATED 		= 0;
float CS_DISCONNECTED 	= 1;
float CS_CONNECTED		= 2;

                           
              

float DRAWFLAG_NORMAL		= 0;
float DRAWFLAG_ADDITIVE 	= 1;
float DRAWFLAG_MODULATE 	= 2;
float DRAWFLAG_2XMODULATE   = 3;

                           
                                                              

entity null_entity;

                           
                  

                
float ERR_CANNOTOPEN			= -1;         
float ERR_NOTENOUGHFILEHANDLES 	= -2;         
float ERR_INVALIDMODE 			= -3;         
float ERR_BADFILENAME 			= -4;         

                    

float ERR_NULLSTRING			= -1;
float ERR_BADDRAWFLAG			= -2;
float ERR_BADSCALE				= -3;
float ERR_BADSIZE				= -3;                        
float ERR_NOTCACHED				= -4;

                    
float SLIST_HOSTCACHEVIEWCOUNT  = 0;
float SLIST_HOSTCACHETOTALCOUNT = 1;
float SLIST_MASTERQUERYCOUNT 	= 2;
float SLIST_MASTERREPLYCOUNT 	= 3;
float SLIST_SERVERQUERYCOUNT 	= 4;
float SLIST_SERVERREPLYCOUNT 	= 5;
float SLIST_SORTFIELD		= 6;
float SLIST_SORTDESCENDING	= 7;
float SLIST_LEGACY_LINE1 	= 1024;
float SLIST_LEGACY_LINE2 	= 1025;
float SLIST_TEST_CONTAINS	= 0;
float SLIST_TEST_NOTCONTAIN	= 1;
float SLIST_TEST_LESSEQUAL	= 2;
float SLIST_TEST_LESS		= 3;
float SLIST_TEST_EQUAL		= 4;
float SLIST_TEST_GREATER	= 5;
float SLIST_TEST_GREATEREQUAL	= 6;
float SLIST_TEST_NOTEQUAL	= 7;
float SLIST_TEST_STARTSWITH	= 8;
float SLIST_TEST_NOTSTARTSWITH	= 9;
float SLIST_MASK_AND = 0;
float SLIST_MASK_OR  = 512;

             
float FONT_DEFAULT     = 0;
float FONT_CONSOLE     = 1;
float FONT_SBAR        = 2;
float FONT_NOTIFY      = 3;
float FONT_CHAT        = 4;
float FONT_CENTERPRINT = 5;
float FONT_INFOBAR     = 6;
float FONT_MENU        = 7;
float FONT_USER        = 8;                                                                                      
float drawfont;

                              
                           
               

                     
                    
                  
  










                                                  
             
                                                  
                                                                      

void 	checkextension(string ext) 	= #1;

             
void 	error(string err,...) 		= #2;
void 	objerror(string err,...) 	= #3;

        

void 	print(string text,...) 		 	 = #4;
void 	bprint(string text,...)			 = #5;
void	sprint(float clientnum, string text,...) = #6;
void 	centerprint(string text,...)		 = #7;

               

vector	normalize(vector v) 		= #8;
float 	vlen(vector v)			= #9;
float  	vectoyaw(vector v)		= #10;
vector 	vectoangles(vector v)		= #11;

float	random(void)  = #12;

void	cmd(string command, ...) = #13;

            

float 	cvar(string name) 			= #14;
const string str_cvar(string name)		= #71;
void	cvar_set(string name, string value)	= #15;

void	dprint(string text,...) = #16;

                       

string	ftos(float f)  	= #17;
float	fabs(float f)	= #18;
string	vtos(vector v)  = #19;
string	etos(entity e)	= #20;

float	stof(string val,...)  = #21;

entity	spawn(void) 		= #22;
void	remove(entity e) 	= #23;

entity	find(entity start, .string field, string match)  	= #24;
entity	findfloat(entity start, .float field, float match) 	= #25;
entity	findentity(entity start, .entity field, entity match) 	= #25;

entity	findchainstring(.string field, string match) 	= #26;
entity	findchainfloat(.float field, float match) 	= #27;
entity	findchainentity(.entity field, entity match)	= #27;

string	precache_file(string file) 	= #28;
string	precache_sound(string sample) 	= #29;

void	crash(void)	= #72;
void	coredump(void) 	= #30;
void	stackdump(void) = #73;
void	traceon(void) 	= #31;
void	traceoff(void) 	= #32;

void	eprint(entity e)  	= #33;
float	rint(float f) 		= #34;
float	floor(float f)  	= #35;
float	ceil(float f)  		= #36;
entity	nextent(entity e)  	= #37;
float	sin(float f)  		= #38;
float	cos(float f)  		= #39;
float	sqrt(float f)  		= #40;
vector	randomvec(void)  	= #41;

float	registercvar(string name, string value, float flags)  = #42;                        

float	min(float f,...)  = #43;
float	max(float f,...)  = #44;

float	bound(float min,float value, float max)  = #45;
float	pow(float a, float b)  = #46;

void	copyentity(entity src, entity dst)  = #47;

float	fopen(string filename, float mode)  = #48;
void	fclose(float fhandle)  = #49;
string	fgets(float fhandle)  = #50;
void	fputs(float fhandle, string s)  = #51;

float	strlen(string s)  = #52;
string	strcat(string s1,string s2,...)  = #53;
string	substring(string s, float start, float length)  = #54;

vector	stov(string s)  = #55;

string	strzone(string s)  = #56;
void	strunzone(string s) = #57;

float	tokenize(string s)  = #58;
string	argv(float n)  = #59;

float	isserver(void)  = #60;
float	clientcount(void)  = #61;
float	clientstate(void)  = #62;
void	clientcommand(float client, string s)  = #63;
void	changelevel(string map)  = #64;
void	localsound(string sample)  = #65;
vector	getmousepos(void)  	= #66;
float	gettime(void)		= #67;
void 	loadfromdata(string data) = #68;
void	loadfromfile(string file) = #69;

float	mod(float val, float m) = #70;

float	search_begin(string pattern, float caseinsensitive, float quiet) = #74;
void	search_end(float handle) = #75;
float	search_getsize(float handle) = #76;
string	search_getfilename(float handle, float num) = #77;

string	chr(float ascii) = #78;

                                                 
                   
                                                 
void	WriteByte(float data, float dest, float desto)	= #401;
void	WriteChar(float data, float dest, float desto)	= #402;
void	WriteShort(float data, float dest, float desto)	= #403;
void	WriteLong(float data, float dest, float desto)	= #404;
void	WriteAngle(float data, float dest, float desto)	= #405;
void	WriteCoord(float data, float dest, float desto)	= #406;
void	WriteString(string data, float dest, float desto)= #407;
void	WriteEntity(entity data, float dest, float desto) = #408;

                                                  
                
                                                  

float	iscachedpic(string name)	= #451;
string	precache_pic(string name, ...)	= #452;
void	freepic(string name)		= #453;

float	drawcharacter(vector position, float character, vector scale, vector rgb, float alpha, float flag) = #454;

float	drawstring(vector position, string text, vector scale, vector rgb, float alpha, float flag) = #455;

float	drawcolorcodedstring(vector position, string text, vector scale, float alpha, float flag) = #467;

vector	drawcolorcodedstring2(vector position, string text, vector scale, vector rgb, float alpha, float flag) = #467;
 
float	drawpic(vector position, string pic, vector size, vector rgb, float alpha, float flag) = #456;

float	drawfill(vector position, vector size, vector rgb, float alpha, float flag) = #457;

void	drawsetcliparea(float x, float y, float width, float height) = #458;

void	drawresetcliparea(void) = #459;

vector  drawgetimagesize(string pic) = #460;

                                                
                 
                                                

void	setkeydest(float dest) 	= #601;
float	getkeydest(void)	= #602;

void	setmousetarget(float trg) = #603;
float	getmousetarget(void)	  = #604;

float	isfunction(string function_name) = #607;
void	callfunction(...) = #605;
void	writetofile(float fhandle, entity ent) = #606;
vector	getresolution(float number) = #608;
string	keynumtostring(float keynum) = #609;

float	gethostcachevalue(float type) = #611;
string	gethostcachestring(float type, float hostnr) = #612;

                  
                        
                                      
                      
string(float key, float bindmap) getkeybind_bindmap = #342;
float(float key, string bind, float bindmap) setkeybind_bindmap = #630;
vector(void) getbindmaps = #631;
float(vector bm) setbindmaps = #632;
string(string command, float bindmap) findkeysforcommand = #610;
float(string key) stringtokeynum = #341;
                                                                                             
                                                                        
           

           
                 
                                      
                             
string(string serveraddress) crypto_getkeyfp = #633;                                                                                  
string(string serveraddress) crypto_getidfp = #634;                                                                             
float(string serveraddress) crypto_getidstatus = #643;                                                                                       
string(string serveraddress) crypto_getencryptlevel = #635;                                                                                                                                                                
string(float i) crypto_getmykeyfp = #636;                                                                                                                                
string(float i) crypto_getmyidfp = #637;                                                                                                                            
float CRYPTO_IDSTATUS_OUTOFRANGE = -1;
float CRYPTO_IDSTATUS_EMPTY = 0;
float CRYPTO_IDSTATUS_UNSIGNED = 1;
float CRYPTO_IDSTATUS_SIGNED = 2;
float(float i) crypto_getmyidstatus = #641;                                                                                                               
float(string url, float id, string content_type, string delim, float buf, float keyid) crypto_uri_postbuf = #513;
              
                                                        

                  
                      
                                           
                       
float GECKO_BUTTON_DOWN         = 0;
float GECKO_BUTTON_UP           = 1;
                                                            
float GECKO_BUTTON_PRESS        = 2;
                                       
float GECKO_BUTTON_DOUBLECLICK  = 3;
                      
float gecko_create( string name ) = #487;
void gecko_destroy( string name ) = #488;
void gecko_navigate( string name, string URI ) = #489;
float gecko_keyevent( string name, float key, float eventtype ) = #490;
void gecko_mousemove( string name, float x, float y ) = #491;
void gecko_resize( string name, float w, float h ) = #492;
vector gecko_get_texture_extent( string name ) = #493;
                              
                                                
              
                                                                                               

             
            
                                    
              
                                       
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

                       
                 
                                      
                       
float PRECACHE_PIC_FROMWAD = 1;                                         
float PRECACHE_PIC_NOTPERSISTENT = 2;                                           
float PRECACHE_PIC_MIPMAP = 8;                                                                        
                                                                                

             
            
                                 
                                                                                                                                              
                                                                               
float(float caseinsensitive, string s, ...) crc16 = #494;

                 
float(string name) cvar_type = #495;
float CVAR_TYPEFLAG_EXISTS = 1;
float CVAR_TYPEFLAG_SAVED = 2;
float CVAR_TYPEFLAG_PRIVATE = 4;
float CVAR_TYPEFLAG_ENGINE = 8;
float CVAR_TYPEFLAG_HASDESCRIPTION = 16;
float CVAR_TYPEFLAG_READONLY = 32;

                     
          
                                      
                                                                                                                    
float() buf_create = #440;
void(float bufhandle) buf_del = #441;
float(float bufhandle) buf_getsize = #442;
void(float bufhandle_from, float bufhandle_to) buf_copy = #443;
void(float bufhandle, float sortpower, float backward) buf_sort = #444;
string(float bufhandle, string glue) buf_implode = #445;
string(float bufhandle, float string_index) bufstr_get = #446;
void(float bufhandle, float string_index, string str) bufstr_set = #447;
float(float bufhandle, string str, float order) bufstr_add = #448;
void(float bufhandle, float string_index) bufstr_free = #449;
void(float bufhandle, string pattern, string antipattern) buf_cvarlist = #517;

                             
             
                                              
                      
string(string s) strtolower = #480;                                                       
string(string s) strtoupper = #481;                                                       
              
                                                          

                        
                 
                                      
                      
string(string name) cvar_description = #518;
              
                                   

              
                       
                                      
                      
string(string digest, string data, ...) digest_hex = #639;
              
                                          
                                                      
                                            
                                                               
                                                                      

                  
            
                                 
                             
string(string in) uri_escape = #510;
string(string in) uri_unescape = #511;

               
                 
                                      
                                      
                                                                        
                                              
                                                              
                                                               
                  
                                   
                     
                                                     
                                                                        
float(string url, float id) uri_get = #513;
                
                 
                                      
                                                             
                                                                                           
                                                                            
float(string url, float id, string content_type, string data) uri_post = #513;
float(string url, float id, string content_type, string delim, float buf) uri_postbuf = #513;

                  
               
                                    
                      
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
              
                                                                                                                                                      
                                                                                                              
                                                                                                                   
                                                                                        
                                                                                                                                                   
                                                                                                                                                                               
                                                                                           

             
                 
                                      
                       
void coverage() = #642;                                                                                                                  

                                   
string(string, float) netaddress_resolve = #625;
string(string search, string replace, string subject) strreplace = #484;
string(float uselocaltime, string format, ...) strftime = #478;
float(string s) tokenize_console = #514;
float(float i) argv_start_index = #515;
float(float i) argv_end_index = #516;
string(float, float) getgamedirinfo = #626;
#define GETGAMEDIRINFO_NAME 0
#define GETGAMEDIRINFO_DESCRIPTION 1
float log(float f) = #532;
string(string format, ...) sprintf = #627;
string(string s) strdecolorize = #477;
entity	findflags(entity start, .float field, float match) = #87;
entity	findchainflags(.float field, float match) = #88;
float(string s, string separator1, ...) tokenizebyseparator = #479;
float 	etof(entity ent) = #79;
entity 	ftoe(float num)	 = #80;
float   validstring(string str) = #81;
float 	altstr_count(string str) = #82;
string  altstr_prepare(string str) = #83;
string  altstr_get(string str, float num) = #84;
string  altstr_set(string str, float num, string set) = #85;
string 	altstr_ins(string str, float num, string set) = #86;
float	isdemo() = #349;
float	drawsubpic(vector position, vector size, string pic, vector srcPosition, vector srcSize, vector rgb, float alpha, float flag) = #469;
                                                                                     
void 	parseentitydata(entity ent, string data) = #613;
void 	resethostcachemasks(void) = #615;
void 	sethostcachemaskstring(float mask, float fld, string str, float op) = #616;
void	sethostcachemasknumber(float mask, float fld, float num, float op) = #617;
void 	resorthostcache(void) = #618;
float SLSF_DESCENDING = 1;
float SLSF_FAVORITES = 2;
float SLSF_CATEGORIES = 4;
void	sethostcachesort(float fld, float slsf) = #619;
void	refreshhostcache(...) = #620;                                           
float	gethostcachenumber(float fld, float hostnr) = #621;
float	gethostcacheindexforkey(string key) = #622;
void	addwantedhostcachekey(string key) = #623;
string	getextresponse(void) = #624;
const string cvar_string(string name) = #71;
const string cvar_defstring(string name) = #89;
float	stringwidth(string text, float handleColors, vector size) = #468;
