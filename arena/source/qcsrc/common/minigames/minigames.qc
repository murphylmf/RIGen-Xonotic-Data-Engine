#include "minigames.qh"

REGISTER_NET_LINKED(ENT_CLIENT_MINIGAME)

entity minigame_get_descriptor(string id)
{
	FOREACH(Minigames, it.netname == id, return it);
	return NULL;
}

                                  
int minigame_tile_letter(string id)
{
	return str2chr(substring(id,0,1),0)-'a';
}

                                  
                                                            
                                                             
                                                                              
int minigame_tile_number(string id)
{
	return stof(substring(id,1,-1)) -1 ;
}

                                                      
vector minigame_tile_pos(string id, int rows, int columns)
{
	return vec2((minigame_tile_letter(id) + 0.5) / columns,
		(1 - (minigame_tile_number(id) + 0.5) / rows));
}

                               
string minigame_tile_buildname(int letter, int number)
{
	return strcat(chr2str('a'+letter),ftos(number+1));
}

                                                 
string minigame_relative_tile(string start_id, int dx, int dy, int rows, int columns)
{
	int letter = minigame_tile_letter(start_id);
	int number = minigame_tile_number(start_id);
	letter = (letter+dx) % columns;
	number = (number+dy) % rows;
	if ( letter < 0 )
		letter = columns + letter;
	if ( number < 0 )
		number = rows + number;
	return minigame_tile_buildname(letter, number);
}

                                                                                   
string minigame_tile_name(vector pos, int rows, int columns)
{
	if ( pos_x < 0 || pos_x > 1 || pos_y < 0 || pos_y > 1 )
		return "";           

	int letter = floor(pos_x * columns);
	int number = floor((1-pos_y) * rows);
	return minigame_tile_buildname(letter, number);
}

                                                                                     
int minigame_next_team(int curr_team, int n_teams)
{
	return curr_team % n_teams + 1;
}

                               
int minigame_prev_team(int curr_team, int n_teams)
{
	return curr_team % n_teams - 1;
}

                                     
                                                                         
void minigame_server_sendflags(entity ent, int mgflags)
{
	#ifdef SVQC
		ent.SendFlags |= mgflags;
	#endif
}

                                                                  
                                                                   
entity msle_spawn(entity minigame_session, entity e)
{
	e.owner = minigame_session;
	e.minigame_autoclean = 1;
	#ifdef SVQC
		setcefc(e, minigame_CheckSend);
		Net_LinkEntity(e, false, 0, minigame_SendEntity);
	#endif
	return e;
}

const int msle_base_id = 2;
int msle_id(string class_name)
{
	if ( class_name == "minigame" ) return 1;
	if ( class_name == "minigame_player" ) return 2;
	int i = msle_base_id;
#define MSLE(Name, Fields) i++; if ( class_name == #Name ) return i;
	MINIGAME_SIMPLELINKED_ENTITIES
#undef MSLE
	return 0;
}

string msle_classname(int id)
{
	if ( id == 1 ) return "minigame";
	if ( id == 2 ) return "minigame_player";
	int i = msle_base_id;
#define MSLE(Name, Fields) i++; if ( id == i ) return #Name;
	MINIGAME_SIMPLELINKED_ENTITIES
#undef MSLE
	return "";
}

int minigame_count_players(entity minigame)
{
	int pl_num = 0;
	entity e;
#ifdef SVQC
	for(e = minigame.minigame_players; e; e = e.list_next)
#elif defined(CSQC)
	e = NULL;
	while( (e = findentity(e,owner,minigame)) )
		if ( e.classname == "minigame_player" )
#endif
		pl_num++;
	return pl_num;
}

#ifdef CSQC
#include "cl_minigames.qc"
#endif
#ifdef SVQC
#include "sv_minigames.qc"
#endif
