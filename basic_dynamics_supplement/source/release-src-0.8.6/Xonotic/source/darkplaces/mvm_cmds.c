#include "quakedef.h"

#include "prvm_cmds.h"
#include "clvm_cmds.h"
#include "menu.h"
#include "csprogs.h"

                                                           

                                                                              
       

const char *vm_m_extensions =
"BX_WAL_SUPPORT "
"DP_CINEMATIC_DPV "
"DP_COVERAGE "
"DP_CRYPTO "
"DP_CSQC_BINDMAPS "
"DP_GFX_FONTS "
"DP_GFX_FONTS_FREETYPE "
"DP_UTF8 "
"DP_FONT_VARIABLEWIDTH "
"DP_MENU_EXTRESPONSEPACKET "
"DP_QC_ASINACOSATANATAN2TAN "
"DP_QC_AUTOCVARS "
"DP_QC_CMD "
"DP_QC_CRC16 "
"DP_QC_CVAR_TYPE "
"DP_QC_CVAR_DESCRIPTION "
"DP_QC_DIGEST "
"DP_QC_DIGEST_SHA256 "
"DP_QC_FINDCHAIN_TOFIELD "
"DP_QC_I18N "
"DP_QC_LOG "
"DP_QC_RENDER_SCENE "
"DP_QC_SPRINTF "
"DP_QC_STRFTIME "
"DP_QC_STRINGBUFFERS "
"DP_QC_STRINGBUFFERS_CVARLIST "
"DP_QC_STRINGBUFFERS_EXT_WIP "
"DP_QC_STRINGCOLORFUNCTIONS "
"DP_QC_STRING_CASE_FUNCTIONS "
"DP_QC_STRREPLACE "
"DP_QC_TOKENIZEBYSEPARATOR "
"DP_QC_TOKENIZE_CONSOLE "
"DP_QC_UNLIMITEDTEMPSTRINGS "
"DP_QC_URI_ESCAPE "
"DP_QC_URI_GET "
"DP_QC_URI_POST "
"DP_QC_WHICHPACK "
"FTE_STRINGS "
;

  
         
                   

                            
         
  
static void VM_M_setmousetarget(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_M_setmousetarget);

	switch((int)PRVM_G_FLOAT(OFS_PARM0))
	{
	case 1:
		in_client_mouse = false;
		break;
	case 2:
		in_client_mouse = true;
		break;
	default:
		prog->error_cmd("VM_M_setmousetarget: wrong destination %f !",PRVM_G_FLOAT(OFS_PARM0));
	}
}

  
         
                   

                    
         
  
static void VM_M_getmousetarget(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(0,VM_M_getmousetarget);

	if(in_client_mouse)
		PRVM_G_FLOAT(OFS_RETURN) = 2;
	else
		PRVM_G_FLOAT(OFS_RETURN) = 1;
}



  
         
               

                      
         
  
static void VM_M_setkeydest(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1,VM_M_setkeydest);

	switch((int)PRVM_G_FLOAT(OFS_PARM0))
	{
	case 0:
		           
		key_dest = key_game;
		break;
	case 2:
		           
		key_dest = key_menu;
		break;
	case 3:
		                   
		key_dest = key_menu_grabbed;
		break;
	case 1:
		              
		                         
		         
	default:
		prog->error_cmd("VM_M_setkeydest: wrong destination %f !", PRVM_G_FLOAT(OFS_PARM0));
	}
}

  
         
               

                
         
  
static void VM_M_getkeydest(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(0,VM_M_getkeydest);

	                                                                                  
	switch(key_dest)
	{
	case key_game:
		PRVM_G_FLOAT(OFS_RETURN) = 0;
		break;
	case key_menu:
		PRVM_G_FLOAT(OFS_RETURN) = 2;
		break;
	case key_menu_grabbed:
		PRVM_G_FLOAT(OFS_RETURN) = 3;
		break;
	case key_message:
		                
		                                
		         
	default:
		PRVM_G_FLOAT(OFS_RETURN) = -1;
	}
}


  
         
                  

                                  
         
  
static void VM_M_getresolution(prvm_prog_t *prog)
{
	int nr, fs;
	VM_SAFEPARMCOUNTRANGE(1, 2, VM_getresolution);

	nr = (int)PRVM_G_FLOAT(OFS_PARM0);

	fs = ((prog->argc <= 1) || ((int)PRVM_G_FLOAT(OFS_PARM1)));

	if(nr < -1 || nr >= (fs ? video_resolutions_count : video_resolutions_hardcoded_count))
	{
		PRVM_G_VECTOR(OFS_RETURN)[0] = 0;
		PRVM_G_VECTOR(OFS_RETURN)[1] = 0;
		PRVM_G_VECTOR(OFS_RETURN)[2] = 0;
	}
	else if(nr == -1)
	{
		vid_mode_t *m = VID_GetDesktopMode();
		if (m)
		{
			PRVM_G_VECTOR(OFS_RETURN)[0] = m->width;
			PRVM_G_VECTOR(OFS_RETURN)[1] = m->height;
			PRVM_G_VECTOR(OFS_RETURN)[2] = m->pixelheight_num / (prvm_vec_t) m->pixelheight_denom;
		}
		else
		{
			PRVM_G_VECTOR(OFS_RETURN)[0] = 0;
			PRVM_G_VECTOR(OFS_RETURN)[1] = 0;
			PRVM_G_VECTOR(OFS_RETURN)[2] = 0;
		}
	}
	else
	{
		video_resolution_t *r = &((fs ? video_resolutions : video_resolutions_hardcoded)[nr]);
		PRVM_G_VECTOR(OFS_RETURN)[0] = r->width;
		PRVM_G_VECTOR(OFS_RETURN)[1] = r->height;
		PRVM_G_VECTOR(OFS_RETURN)[2] = r->pixelheight;
	}
}

static void VM_M_getgamedirinfo(prvm_prog_t *prog)
{
	int nr, item;
	VM_SAFEPARMCOUNT(2, VM_getgamedirinfo);

	nr = (int)PRVM_G_FLOAT(OFS_PARM0);
	item = (int)PRVM_G_FLOAT(OFS_PARM1);

	PRVM_G_INT( OFS_RETURN ) = OFS_NULL;

	if(nr >= 0 && nr < fs_all_gamedirs_count)
	{
		if(item == 0)
			PRVM_G_INT( OFS_RETURN ) = PRVM_SetTempString( prog, fs_all_gamedirs[nr].name );
		else if(item == 1)
			PRVM_G_INT( OFS_RETURN ) = PRVM_SetTempString( prog, fs_all_gamedirs[nr].description );
	}
}

  
         
                      

                                   
         
  
  
      
                      
                         
                  
                  
                  
                  
           
           
  
static void VM_M_getserverliststat(prvm_prog_t *prog)
{
	int type;
	VM_SAFEPARMCOUNT ( 1, VM_M_getserverliststat );

	PRVM_G_FLOAT( OFS_RETURN ) = 0;

	type = (int)PRVM_G_FLOAT( OFS_PARM0 );
	switch(type)
	{
	case 0:
		PRVM_G_FLOAT ( OFS_RETURN ) = serverlist_viewcount;
		return;
	case 1:
		PRVM_G_FLOAT ( OFS_RETURN ) = serverlist_cachecount;
		return;
	case 2:
		PRVM_G_FLOAT ( OFS_RETURN ) = masterquerycount;
		return;
	case 3:
		PRVM_G_FLOAT ( OFS_RETURN ) = masterreplycount;
		return;
	case 4:
		PRVM_G_FLOAT ( OFS_RETURN ) = serverquerycount;
		return;
	case 5:
		PRVM_G_FLOAT ( OFS_RETURN ) = serverreplycount;
		return;
	case 6:
		PRVM_G_FLOAT ( OFS_RETURN ) = serverlist_sortbyfield;
		return;
	case 7:
		PRVM_G_FLOAT ( OFS_RETURN ) = serverlist_sortflags;
		return;
	default:
		VM_Warning(prog, "VM_M_getserverliststat: bad type %i!\n", type );
	}
}

  
                        
                         

                      
                        
  
static void VM_M_resetserverlistmasks(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(0, VM_M_resetserverlistmasks);
	ServerList_ResetMasks();
}


  
                        
                            

                                                                    
          
             
                        
  
static void VM_M_setserverlistmaskstring(prvm_prog_t *prog)
{
	const char *str;
	int masknr;
	serverlist_mask_t *mask;
	int field;

	VM_SAFEPARMCOUNT( 4, VM_M_setserverlistmaskstring );
	str = PRVM_G_STRING( OFS_PARM2 );

	masknr = (int)PRVM_G_FLOAT( OFS_PARM0 );
	if( masknr >= 0 && masknr < SERVERLIST_ANDMASKCOUNT )
		mask = &serverlist_andmasks[masknr];
	else if( masknr >= 512 && masknr - 512 < SERVERLIST_ORMASKCOUNT )
		mask = &serverlist_ormasks[masknr - 512 ];
	else
	{
		VM_Warning(prog, "VM_M_setserverlistmaskstring: invalid mask number %i\n", masknr );
		return;
	}

	field = (int) PRVM_G_FLOAT( OFS_PARM1 );

	switch( field ) {
		case SLIF_CNAME:
			strlcpy( mask->info.cname, str, sizeof(mask->info.cname) );
			break;
		case SLIF_NAME:
			strlcpy( mask->info.name, str, sizeof(mask->info.name)  );
			break;
		case SLIF_QCSTATUS:
			strlcpy( mask->info.qcstatus, str, sizeof(mask->info.qcstatus)  );
			break;
		case SLIF_PLAYERS:
			strlcpy( mask->info.players, str, sizeof(mask->info.players)  );
			break;
		case SLIF_MAP:
			strlcpy( mask->info.map, str, sizeof(mask->info.map)  );
			break;
		case SLIF_MOD:
			strlcpy( mask->info.mod, str, sizeof(mask->info.mod)  );
			break;
		case SLIF_GAME:
			strlcpy( mask->info.game, str, sizeof(mask->info.game)  );
			break;
		default:
			VM_Warning(prog, "VM_M_setserverlistmaskstring: Bad field number %i passed!\n", field );
			return;
	}

	mask->active = true;
	mask->tests[field] = (serverlist_maskop_t)((int)PRVM_G_FLOAT( OFS_PARM3 ));
}

  
                        
                            

                                                                   

          
             
                        
  
static void VM_M_setserverlistmasknumber(prvm_prog_t *prog)
{
	int number;
	serverlist_mask_t *mask;
	int	masknr;
	int field;
	VM_SAFEPARMCOUNT( 4, VM_M_setserverlistmasknumber );

	masknr = (int)PRVM_G_FLOAT( OFS_PARM0 );
	if( masknr >= 0 && masknr < SERVERLIST_ANDMASKCOUNT )
		mask = &serverlist_andmasks[masknr];
	else if( masknr >= 512 && masknr - 512 < SERVERLIST_ORMASKCOUNT )
		mask = &serverlist_ormasks[masknr - 512 ];
	else
	{
		VM_Warning(prog, "VM_M_setserverlistmasknumber: invalid mask number %i\n", masknr );
		return;
	}

	number = (int)PRVM_G_FLOAT( OFS_PARM2 );
	field = (int) PRVM_G_FLOAT( OFS_PARM1 );

	switch( field ) {
		case SLIF_MAXPLAYERS:
			mask->info.maxplayers = number;
			break;
		case SLIF_NUMPLAYERS:
			mask->info.numplayers = number;
			break;
		case SLIF_NUMBOTS:
			mask->info.numbots = number;
			break;
		case SLIF_NUMHUMANS:
			mask->info.numhumans = number;
			break;
		case SLIF_PING:
			mask->info.ping = number;
			break;
		case SLIF_PROTOCOL:
			mask->info.protocol = number;
			break;
		case SLIF_FREESLOTS:
			mask->info.freeslots = number;
			break;
		case SLIF_CATEGORY:
			mask->info.category = number;
			break;
		case SLIF_ISFAVORITE:
			mask->info.isfavorite = number != 0;
			break;
		default:
			VM_Warning(prog, "VM_M_setserverlistmasknumber: Bad field number %i passed!\n", field );
			return;
	}

	mask->active = true;
	mask->tests[field] = (serverlist_maskop_t)((int)PRVM_G_FLOAT( OFS_PARM3 ));
}


  
                        
                     

                
                        
  
static void VM_M_resortserverlist(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(0, VM_M_resortserverlist);
	ServerList_RebuildViewList();
}

  
         
                        

                                                     
         
  
static void VM_M_getserverliststring(prvm_prog_t *prog)
{
	const serverlist_entry_t *cache;
	int hostnr;

	VM_SAFEPARMCOUNT(2, VM_M_getserverliststring);

	PRVM_G_INT(OFS_RETURN) = OFS_NULL;

	hostnr = (int)PRVM_G_FLOAT(OFS_PARM1);

	if(hostnr == -1 && serverlist_callbackentry)
	{
		cache = serverlist_callbackentry;
	}
	else
	{
		if(hostnr < 0 || hostnr >= serverlist_viewcount)
		{
			Con_Print("VM_M_getserverliststring: bad hostnr passed!\n");
			return;
		}
		cache = ServerList_GetViewEntry(hostnr);
	}
	switch( (int) PRVM_G_FLOAT(OFS_PARM0) ) {
		case SLIF_CNAME:
			PRVM_G_INT( OFS_RETURN ) = PRVM_SetTempString( prog, cache->info.cname );
			break;
		case SLIF_NAME:
			PRVM_G_INT( OFS_RETURN ) = PRVM_SetTempString( prog, cache->info.name );
			break;
		case SLIF_QCSTATUS:
			PRVM_G_INT (OFS_RETURN ) = PRVM_SetTempString( prog, cache->info.qcstatus );
			break;
		case SLIF_PLAYERS:
			PRVM_G_INT (OFS_RETURN ) = PRVM_SetTempString( prog, cache->info.players );
			break;
		case SLIF_GAME:
			PRVM_G_INT( OFS_RETURN ) = PRVM_SetTempString( prog, cache->info.game );
			break;
		case SLIF_MOD:
			PRVM_G_INT( OFS_RETURN ) = PRVM_SetTempString( prog, cache->info.mod );
			break;
		case SLIF_MAP:
			PRVM_G_INT( OFS_RETURN ) = PRVM_SetTempString( prog, cache->info.map );
			break;
		                         
		case 1024:
			PRVM_G_INT( OFS_RETURN ) = PRVM_SetTempString( prog, cache->line1 );
			break;
		case 1025:
			PRVM_G_INT( OFS_RETURN ) = PRVM_SetTempString( prog, cache->line2 );
			break;
		default:
			Con_Print("VM_M_getserverliststring: bad field number passed!\n");
	}
}

  
         
                        

                                                    
         
  
static void VM_M_getserverlistnumber(prvm_prog_t *prog)
{
	const serverlist_entry_t *cache;
	int hostnr;

	VM_SAFEPARMCOUNT(2, VM_M_getserverliststring);

	PRVM_G_INT(OFS_RETURN) = OFS_NULL;

	hostnr = (int)PRVM_G_FLOAT(OFS_PARM1);

	if(hostnr == -1 && serverlist_callbackentry)
	{
		cache = serverlist_callbackentry;
	}
	else
	{
		if(hostnr < 0 || hostnr >= serverlist_viewcount)
		{
			Con_Print("VM_M_getserverliststring: bad hostnr passed!\n");
			return;
		}
		cache = ServerList_GetViewEntry(hostnr);
	}
	switch( (int) PRVM_G_FLOAT(OFS_PARM0) ) {
		case SLIF_MAXPLAYERS:
			PRVM_G_FLOAT( OFS_RETURN ) = cache->info.maxplayers;
			break;
		case SLIF_NUMPLAYERS:
			PRVM_G_FLOAT( OFS_RETURN ) = cache->info.numplayers;
			break;
		case SLIF_NUMBOTS:
			PRVM_G_FLOAT( OFS_RETURN ) = cache->info.numbots;
			break;
		case SLIF_NUMHUMANS:
			PRVM_G_FLOAT( OFS_RETURN ) = cache->info.numhumans;
			break;
		case SLIF_FREESLOTS:
			PRVM_G_FLOAT( OFS_RETURN ) = cache->info.freeslots;
			break;
		case SLIF_PING:
			PRVM_G_FLOAT( OFS_RETURN ) = cache->info.ping;
			break;
		case SLIF_PROTOCOL:
			PRVM_G_FLOAT( OFS_RETURN ) = cache->info.protocol;
			break;
		case SLIF_CATEGORY:
			PRVM_G_FLOAT( OFS_RETURN ) = cache->info.category;
			break;
		case SLIF_ISFAVORITE:
			PRVM_G_FLOAT( OFS_RETURN ) = cache->info.isfavorite;
			break;
		default:
			Con_Print("VM_M_getserverlistnumber: bad field number passed!\n");
	}
}

  
                        
                      

                                           
                        
  
static void VM_M_setserverlistsort(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT( 2, VM_M_setserverlistsort );

	serverlist_sortbyfield = (serverlist_infofield_t)((int)PRVM_G_FLOAT( OFS_PARM0 ));
	serverlist_sortflags = (int) PRVM_G_FLOAT( OFS_PARM1 );
}

  
                        
                      

                   
                        
  
static void VM_M_refreshserverlist(prvm_prog_t *prog)
{
	qboolean do_reset = false;
	VM_SAFEPARMCOUNTRANGE( 0, 1, VM_M_refreshserverlist );
	if (prog->argc >= 1 && PRVM_G_FLOAT(OFS_PARM0))
		do_reset = true;
	ServerList_QueryList(do_reset, true, false, false);
}

  
                        
                             

                                          
                        
  
static void VM_M_getserverlistindexforkey(prvm_prog_t *prog)
{
	const char *key;
	VM_SAFEPARMCOUNT( 1, VM_M_getserverlistindexforkey );

	key = PRVM_G_STRING( OFS_PARM0 );
	VM_CheckEmptyString( prog, key );

	if( !strcmp( key, "cname" ) )
		PRVM_G_FLOAT( OFS_RETURN ) = SLIF_CNAME;
	else if( !strcmp( key, "ping" ) )
		PRVM_G_FLOAT( OFS_RETURN ) = SLIF_PING;
	else if( !strcmp( key, "game" ) )
		PRVM_G_FLOAT( OFS_RETURN ) = SLIF_GAME;
	else if( !strcmp( key, "mod" ) )
		PRVM_G_FLOAT( OFS_RETURN ) = SLIF_MOD;
	else if( !strcmp( key, "map" ) )
		PRVM_G_FLOAT( OFS_RETURN ) = SLIF_MAP;
	else if( !strcmp( key, "name" ) )
		PRVM_G_FLOAT( OFS_RETURN ) = SLIF_NAME;
	else if( !strcmp( key, "qcstatus" ) )
		PRVM_G_FLOAT( OFS_RETURN ) = SLIF_QCSTATUS;
	else if( !strcmp( key, "players" ) )
		PRVM_G_FLOAT( OFS_RETURN ) = SLIF_PLAYERS;
	else if( !strcmp( key, "maxplayers" ) )
		PRVM_G_FLOAT( OFS_RETURN ) = SLIF_MAXPLAYERS;
	else if( !strcmp( key, "numplayers" ) )
		PRVM_G_FLOAT( OFS_RETURN ) = SLIF_NUMPLAYERS;
	else if( !strcmp( key, "numbots" ) )
		PRVM_G_FLOAT( OFS_RETURN ) = SLIF_NUMBOTS;
	else if( !strcmp( key, "numhumans" ) )
		PRVM_G_FLOAT( OFS_RETURN ) = SLIF_NUMHUMANS;
	else if( !strcmp( key, "freeslots" ) )
		PRVM_G_FLOAT( OFS_RETURN ) = SLIF_FREESLOTS;
	else if( !strcmp( key, "protocol" ) )
		PRVM_G_FLOAT( OFS_RETURN ) = SLIF_PROTOCOL;
	else if( !strcmp( key, "category" ) )
		PRVM_G_FLOAT( OFS_RETURN ) = SLIF_CATEGORY;
	else if( !strcmp( key, "isfavorite" ) )
		PRVM_G_FLOAT( OFS_RETURN ) = SLIF_ISFAVORITE;
	else
		PRVM_G_FLOAT( OFS_RETURN ) = -1;
}

  
                        
                           

                                  
                        
  
static void VM_M_addwantedserverlistkey(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT( 1, VM_M_addwantedserverlistkey );
}

  
                                                                               
               

                             
                     

                                    

                                                                               
  

#define	MSG_BROADCAST	0		                    
#define	MSG_ONE			1		                               
#define	MSG_ALL			2		                  
#define	MSG_INIT		3		                           

static sizebuf_t *VM_M_WriteDest (prvm_prog_t *prog)
{
	int		dest;
	int		destclient;

	if(!sv.active)
		prog->error_cmd("VM_M_WriteDest: game is not server (%s)", prog->name);

	dest = (int)PRVM_G_FLOAT(OFS_PARM1);
	switch (dest)
	{
	case MSG_BROADCAST:
		return &sv.datagram;

	case MSG_ONE:
		destclient = (int) PRVM_G_FLOAT(OFS_PARM2);
		if (destclient < 0 || destclient >= svs.maxclients || !svs.clients[destclient].active || !svs.clients[destclient].netconnection)
			prog->error_cmd("VM_clientcommand: %s: invalid client !", prog->name);

		return &svs.clients[destclient].netconnection->message;

	case MSG_ALL:
		return &sv.reliable_datagram;

	case MSG_INIT:
		return &sv.signon;

	default:
		prog->error_cmd("WriteDest: bad destination");
		break;
	}

	return NULL;
}

static void VM_M_WriteByte (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_M_WriteByte);
	MSG_WriteByte (VM_M_WriteDest(prog), (int)PRVM_G_FLOAT(OFS_PARM0));
}

static void VM_M_WriteChar (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_M_WriteChar);
	MSG_WriteChar (VM_M_WriteDest(prog), (int)PRVM_G_FLOAT(OFS_PARM0));
}

static void VM_M_WriteShort (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_M_WriteShort);
	MSG_WriteShort (VM_M_WriteDest(prog), (int)PRVM_G_FLOAT(OFS_PARM0));
}

static void VM_M_WriteLong (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_M_WriteLong);
	MSG_WriteLong (VM_M_WriteDest(prog), (int)PRVM_G_FLOAT(OFS_PARM0));
}

static void VM_M_WriteAngle (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_M_WriteAngle);
	MSG_WriteAngle (VM_M_WriteDest(prog), PRVM_G_FLOAT(OFS_PARM0), sv.protocol);
}

static void VM_M_WriteCoord (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_M_WriteCoord);
	MSG_WriteCoord (VM_M_WriteDest(prog), PRVM_G_FLOAT(OFS_PARM0), sv.protocol);
}

static void VM_M_WriteString (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_M_WriteString);
	MSG_WriteString (VM_M_WriteDest(prog), PRVM_G_STRING(OFS_PARM0));
}

static void VM_M_WriteEntity (prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(1, VM_M_WriteEntity);
	MSG_WriteShort (VM_M_WriteDest(prog), PRVM_G_EDICTNUM(OFS_PARM0));
}

  
                 
               

                                      

                                  
                 
  
static void VM_M_copyentity (prvm_prog_t *prog)
{
	prvm_edict_t *in, *out;
	VM_SAFEPARMCOUNT(2,VM_M_copyentity);
	in = PRVM_G_EDICT(OFS_PARM0);
	out = PRVM_G_EDICT(OFS_PARM1);
	memcpy(out->fields.fp, in->fields.fp, prog->entityfields * sizeof(prvm_vec_t));
}

                                     
static void VM_M_getmousepos(prvm_prog_t *prog)
{
	VM_SAFEPARMCOUNT(0,VM_M_getmousepos);

	if (key_consoleactive || (key_dest != key_menu && key_dest != key_menu_grabbed))
		VectorSet(PRVM_G_VECTOR(OFS_RETURN), 0, 0, 0);
	else if (in_client_mouse)
		VectorSet(PRVM_G_VECTOR(OFS_RETURN), in_windowmouse_x * vid_conwidth.integer / vid.width, in_windowmouse_y * vid_conheight.integer / vid.height, 0);
	else
		VectorSet(PRVM_G_VECTOR(OFS_RETURN), in_mouse_x * vid_conwidth.integer / vid.width, in_mouse_y * vid_conheight.integer / vid.height, 0);
}

static void VM_M_crypto_getkeyfp(prvm_prog_t *prog)
{
	lhnetaddress_t addr;
	const char *s;
	char keyfp[FP64_SIZE + 1];

	VM_SAFEPARMCOUNT(1,VM_M_crypto_getkeyfp);

	s = PRVM_G_STRING( OFS_PARM0 );
	VM_CheckEmptyString( prog, s );

	if(LHNETADDRESS_FromString(&addr, s, 26000) && Crypto_RetrieveHostKey(&addr, NULL, keyfp, sizeof(keyfp), NULL, 0, NULL, NULL))
		PRVM_G_INT( OFS_RETURN ) = PRVM_SetTempString( prog, keyfp );
	else
		PRVM_G_INT( OFS_RETURN ) = OFS_NULL;
}
static void VM_M_crypto_getidfp(prvm_prog_t *prog)
{
	lhnetaddress_t addr;
	const char *s;
	char idfp[FP64_SIZE + 1];

	VM_SAFEPARMCOUNT(1,VM_M_crypto_getidfp);

	s = PRVM_G_STRING( OFS_PARM0 );
	VM_CheckEmptyString( prog, s );

	if(LHNETADDRESS_FromString(&addr, s, 26000) && Crypto_RetrieveHostKey(&addr, NULL, NULL, 0, idfp, sizeof(idfp), NULL, NULL))
		PRVM_G_INT( OFS_RETURN ) = PRVM_SetTempString( prog, idfp );
	else
		PRVM_G_INT( OFS_RETURN ) = OFS_NULL;
}
static void VM_M_crypto_getidstatus(prvm_prog_t *prog)
{
	lhnetaddress_t addr;
	const char *s;
	qboolean issigned;

	VM_SAFEPARMCOUNT(1,VM_M_crypto_getidstatus);

	s = PRVM_G_STRING( OFS_PARM0 );
	VM_CheckEmptyString( prog, s );

	if(LHNETADDRESS_FromString(&addr, s, 26000) && Crypto_RetrieveHostKey(&addr, NULL, NULL, 0, NULL, 0, NULL, &issigned))
		PRVM_G_FLOAT( OFS_RETURN ) = issigned ? 2 : 1;
	else
		PRVM_G_FLOAT( OFS_RETURN ) = 0;
}
static void VM_M_crypto_getencryptlevel(prvm_prog_t *prog)
{
	lhnetaddress_t addr;
	const char *s;
	int aeslevel;
	char vabuf[1024];

	VM_SAFEPARMCOUNT(1,VM_M_crypto_getencryptlevel);

	s = PRVM_G_STRING( OFS_PARM0 );
	VM_CheckEmptyString( prog, s );

	if(LHNETADDRESS_FromString(&addr, s, 26000) && Crypto_RetrieveHostKey(&addr, NULL, NULL, 0, NULL, 0, &aeslevel, NULL))
		PRVM_G_INT( OFS_RETURN ) = PRVM_SetTempString(prog, aeslevel ? va(vabuf, sizeof(vabuf), "%d AES128", aeslevel) : "0");
	else
		PRVM_G_INT( OFS_RETURN ) = OFS_NULL;
}
static void VM_M_crypto_getmykeyfp(prvm_prog_t *prog)
{
	int i;
	char keyfp[FP64_SIZE + 1];

	VM_SAFEPARMCOUNT(1,VM_M_crypto_getmykey);

	i = PRVM_G_FLOAT( OFS_PARM0 );
	switch(Crypto_RetrieveLocalKey(i, keyfp, sizeof(keyfp), NULL, 0, NULL))
	{
		case -1:
			PRVM_G_INT( OFS_RETURN ) = PRVM_SetTempString(prog, "");
			break;
		case 0:
			PRVM_G_INT( OFS_RETURN ) = OFS_NULL;
			break;
		default:
		case 1:
			PRVM_G_INT( OFS_RETURN ) = PRVM_SetTempString(prog, keyfp);
			break;
	}
}
static void VM_M_crypto_getmyidfp(prvm_prog_t *prog)
{
	int i;
	char idfp[FP64_SIZE + 1];

	VM_SAFEPARMCOUNT(1,VM_M_crypto_getmykey);

	i = PRVM_G_FLOAT( OFS_PARM0 );
	switch(Crypto_RetrieveLocalKey(i, NULL, 0, idfp, sizeof(idfp), NULL))
	{
		case -1:
			PRVM_G_INT( OFS_RETURN ) = PRVM_SetTempString(prog, "");
			break;
		case 0:
			PRVM_G_INT( OFS_RETURN ) = OFS_NULL;
			break;
		default:
		case 1:
			PRVM_G_INT( OFS_RETURN ) = PRVM_SetTempString(prog, idfp);
			break;
	}
}
static void VM_M_crypto_getmyidstatus(prvm_prog_t *prog)
{
	int i;
	qboolean issigned;

	VM_SAFEPARMCOUNT(1,VM_M_crypto_getmykey);

	i = PRVM_G_FLOAT( OFS_PARM0 );
	switch(Crypto_RetrieveLocalKey(i, NULL, 0, NULL, 0, &issigned))
	{
		case -1:
			PRVM_G_FLOAT( OFS_RETURN ) = 0;                    
			break;
		case 0:
			PRVM_G_FLOAT( OFS_RETURN ) = -1;                
			break;
		default:
		case 1:
			PRVM_G_FLOAT( OFS_RETURN ) = issigned ? 2 : 1;
			break;
	}
}

prvm_builtin_t vm_m_builtins[] = {
NULL,									                                    
VM_checkextension,				       
VM_error,							       
VM_objerror,						       
VM_print,							       
VM_bprint,							       
VM_sprint,							       
VM_centerprint,					       
VM_normalize,						       
VM_vlen,								       
VM_vectoyaw,						       
VM_vectoangles,					       
VM_random,							       
VM_localcmd,						       
VM_cvar,								       
VM_cvar_set,						       
VM_dprint,							       
VM_ftos,								       
VM_fabs,								       
VM_vtos,								       
VM_etos,								       
VM_stof,								       
VM_spawn,							       
VM_remove,							       
VM_find,								       
VM_findfloat,						       
VM_findchain,						       
VM_findchainfloat,				       
VM_precache_file,					       
VM_precache_sound,				       
VM_coredump,						       
VM_traceon,							       
VM_traceoff,						       
VM_eprint,							       
VM_rint,								       
VM_floor,							       
VM_ceil,								       
VM_nextent,							       
VM_sin,								       
VM_cos,								       
VM_sqrt,								       
VM_randomvec,						       
VM_registercvar,					       
VM_min,								       
VM_max,								       
VM_bound,							       
VM_pow,								       
VM_M_copyentity,					       
VM_fopen,							       
VM_fclose,							       
VM_fgets,							       
VM_fputs,							       
VM_strlen,							       
VM_strcat,							       
VM_substring,						       
VM_stov,								       
VM_strzone,							       
VM_strunzone,						       
VM_tokenize,						       
VM_argv,								       
VM_isserver,						       
VM_clientcount,					       
VM_clientstate,					       
VM_clcommand,						       
VM_changelevel,					       
VM_localsound,						       
VM_M_getmousepos,					       
VM_gettime,							       
VM_loadfromdata,					       
VM_loadfromfile,					       
VM_modulo,							       
VM_cvar_string,					       
VM_crash,							       
VM_stackdump,						       
VM_search_begin,					       
VM_search_end,						       
VM_search_getsize,				       
VM_search_getfilename,			       
VM_chr,								       
VM_itof,								       
VM_ftoe,								       
VM_itof,								                
VM_altstr_count,					       
VM_altstr_prepare,				       
VM_altstr_get,						       
VM_altstr_set,						       
VM_altstr_ins,						       
VM_findflags,						       
VM_findchainflags,				       
VM_cvar_defstring,				       
                                                                                                              
#if 0
VM_CL_setmodel,					                                                
VM_CL_precache_model,			                                            
VM_CL_setorigin,				                                                 
#else
NULL,
NULL,
NULL,
#endif
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
VM_strstrofs,						                                                                               
VM_str2chr,						                                                          
VM_chr2str,						                                                  
VM_strconv,						                                                                                          
VM_strpad,						                                                               
VM_infoadd,						                                                                                
VM_infoget,						                                                             
VM_strncmp,							                                                                    
VM_strncasecmp,					                                                            
VM_strncasecmp,					                                                                        
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
                                                                                                              
#if 0
                       
VM_CL_R_ClearScene,				                                              
VM_CL_R_AddEntities,			                                                         
VM_CL_R_AddEntity,				                                                       
VM_CL_R_SetView,				                                                                   
VM_CL_R_RenderScene,			                                               
VM_CL_R_AddDynamicLight,		                                                                                                
VM_CL_R_PolygonBegin,			                                                                                                           
VM_CL_R_PolygonVertex,			                                                                                                        
VM_CL_R_PolygonEnd,				                           
NULL                          ,				                                               
                                                                                                                                    
VM_CL_setattachment,				                                                                                                                    
VM_CL_gettagindex,				                                                                                             
VM_CL_gettaginfo,					                                                                                             
#else
                       
NULL,		
NULL,		
NULL,		
NULL,		
NULL,		
NULL,		
NULL,		
NULL,	
NULL,	
NULL,
NULL,	
NULL,	
NULL,	
#endif
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
VM_keynumtostring,				                                           
VM_stringtokeynum,				                                        
VM_getkeybind,							                                                                   
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
VM_CL_isdemo,							       
NULL,									       
NULL,									       
NULL,									       
VM_wasfreed,							                                  
NULL,									       
VM_CL_videoplaying,						       
VM_findfont,							                                                      
VM_loadfont,							                                                                                                 
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
VM_M_WriteByte,					       
VM_M_WriteChar,					       
VM_M_WriteShort,					       
VM_M_WriteLong,					       
VM_M_WriteAngle,					       
VM_M_WriteCoord,					       
VM_M_WriteString,					       
VM_M_WriteEntity,					       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
VM_buf_create,					                                                
VM_buf_del,						                                                           
VM_buf_getsize,					                                                                
VM_buf_copy,					                                                                                     
VM_buf_sort,					                                                                                             
VM_buf_implode,					                                                                              
VM_bufstr_get,					                                                                                    
VM_bufstr_set,					                                                                                              
VM_bufstr_add,					                                                                                        
VM_bufstr_free,					                                                                                   
NULL,									       
VM_iscachedpic,					                         
VM_precache_pic,					       
VM_freepic,							       
VM_drawcharacter,					       
VM_drawstring,						       
VM_drawpic,							       
VM_drawfill,						       
VM_drawsetcliparea,				       
VM_drawresetcliparea,			       
VM_getimagesize,					       
VM_cin_open,						       
VM_cin_close,						       
VM_cin_setstate,					       
VM_cin_getstate,					       
VM_cin_restart, 					       
VM_drawline,						       
VM_drawcolorcodedstring,		       
VM_stringwidth,					       
VM_drawsubpic,						       
VM_drawrotpic,						       
VM_asin,								                                                           
VM_acos,								                                                           
VM_atan,								                                                           
VM_atan2,							                                                                     
VM_tan,								                                                          
VM_strlennocol,					                                                                                                       
VM_strdecolorize,					                                                                                  
VM_strftime,						                                                                       
VM_tokenizebyseparator,			                                                                       
VM_strtolower,						                                                                           
VM_strtoupper,						                                                                           
NULL,									       
NULL,									       
VM_strreplace,						                                                                                           
VM_strireplace,					                                                                                            
NULL,									       
VM_gecko_create,					                                         
VM_gecko_destroy,					                                         
VM_gecko_navigate,				                                                      
VM_gecko_keyevent,				                                                                       
VM_gecko_movemouse,				                                                             
VM_gecko_resize,					                                                          
VM_gecko_get_texture_extent,	                                                      
VM_crc16,						                                                                              
VM_cvar_type,					                                                              
VM_numentityfields,				                                                          
VM_entityfieldname,				                                                                         
VM_entityfieldtype,				                                                                        
VM_getentityfieldstring,		                                                                                          
VM_putentityfieldstring,		                                                                                                   
NULL,									       
NULL,									       
VM_whichpack,					                                        
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
VM_uri_escape,					                                            
VM_uri_unescape,				                                              
VM_etof,					                                                                    
VM_uri_get,						                                                                                                                                              
VM_tokenize_console,					                                                                           
VM_argv_start_index,					                                                                          
VM_argv_end_index,						                                                                        
VM_buf_cvarlist,						                                                                                                             
VM_cvar_description,					                                                                            
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
VM_log,									       
VM_getsoundtime,						                                                                                 
VM_soundlength,							                                                                      
VM_buf_loadfile,                                                                                                                  
VM_buf_writefile,                                                                                                                                                     
VM_bufstr_find,                                                                                                                                                
VM_matchpattern,                                                                                                                           
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
NULL,									       
VM_M_setkeydest,					                                   
VM_M_getkeydest,					                              
VM_M_setmousetarget,				                                      
VM_M_getmousetarget,				                                  
VM_callfunction,				                              
VM_writetofile,					                                                   
VM_isfunction,					                                              
VM_M_getresolution,				                                                                 
VM_keynumtostring,				                                           
VM_findkeysforcommand,		                                                                  
VM_M_getserverliststat,			                                           
VM_M_getserverliststring,		                                                           
VM_parseentitydata,				                                                     
VM_stringtokeynum,				                                        
VM_M_resetserverlistmasks,		                                      
VM_M_setserverlistmaskstring,	                                                                                
VM_M_setserverlistmasknumber,	                                                                               
VM_M_resortserverlist,			                                  
VM_M_setserverlistsort,			                                                          
VM_M_refreshserverlist,			                                   
VM_M_getserverlistnumber,		                                                         
VM_M_getserverlistindexforkey,                                                 
VM_M_addwantedserverlistkey,	                                              
VM_CL_getextresponse,			                                   
VM_netaddress_resolve,                                                          
VM_M_getgamedirinfo,                                                              
VM_sprintf,                                                               
NULL,        
NULL,        
VM_setkeybind,						                                                                 
VM_getbindmaps,						                               
VM_setbindmaps,						                                   
VM_M_crypto_getkeyfp,					                                           
VM_M_crypto_getidfp,					                                          
VM_M_crypto_getencryptlevel,				                                                  
VM_M_crypto_getmykeyfp,					                                            
VM_M_crypto_getmyidfp,					                                           
NULL,							       
VM_digest_hex,						       
NULL,							       
VM_M_crypto_getmyidstatus,				                                           
VM_coverage,						       
VM_M_crypto_getidstatus,				                                             
NULL
};

const int vm_m_numbuiltins = sizeof(vm_m_builtins) / sizeof(prvm_builtin_t);

void MVM_init_cmd(prvm_prog_t *prog)
{
	r_refdef_scene_t *scene;

	VM_Cmd_Init(prog);
	VM_Polygons_Reset(prog);

	scene = R_GetScenePointer( RST_MENU );

	memset (scene, 0, sizeof (*scene));

	scene->maxtempentities = 128;
	scene->tempentities = (entity_render_t*) Mem_Alloc(prog->progs_mempool, sizeof(entity_render_t) * scene->maxtempentities);

	scene->maxentities = MAX_EDICTS + 256 + 512;
	scene->entities = (entity_render_t **)Mem_Alloc(prog->progs_mempool, sizeof(entity_render_t *) * scene->maxentities);

	                               
	scene->ambientintensity = 32.0f;
}

void MVM_reset_cmd(prvm_prog_t *prog)
{
	                                                                                         

	                
	VM_Cmd_Reset(prog);
	VM_Polygons_Reset(prog);
}
