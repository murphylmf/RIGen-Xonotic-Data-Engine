#include "sv_new_toys.qh"

#include "../random_items/sv_random_items.qh"
#include <server/weapons/spawning.qh>

  

                                                                                       
                         
             

                                                                      
                                                                                       



                       
                        

                                                                            
                    

       

 
                           
                  
 
                                                                          

 
                           
                         
 
                                                                                           

 
                           
                   
 
                           

                                           

                                                                                      
                                                                             
                                                                                  

                                                             

                                                                               
                            

                                                                             
                       

                                                   
                                      
                 
               
                                                                       

                                                                     
                       

                                                                  
                   

                                                                              
                                      

  

                             

bool nt_IsNewToy(int w);

REGISTER_MUTATOR(nt, expr_evaluate(cvar_string("g_new_toys")) && !MUTATOR_IS_ENABLED(mutator_instagib) && !MUTATOR_IS_ENABLED(ok))
{
	MUTATOR_ONADD
	{
		if(time > 1)                        
			error("This cannot be added at runtime\n");

		                                                
		FOREACH(Weapons, it != WEP_Null, {
			if(nt_IsNewToy(it.m_id))
				it.spawnflags &= ~WEP_FLAG_MUTATORBLOCKED;
		});
	}

	MUTATOR_ONROLLBACK_OR_REMOVE
	{
		FOREACH(Weapons, it != WEP_Null, {
			if(nt_IsNewToy(it.m_id))
				it.spawnflags |= WEP_FLAG_MUTATORBLOCKED;
		});
	}

	MUTATOR_ONREMOVE
	{
		LOG_INFO("This cannot be removed at runtime");
		return -1;
	}

	return 0;
}

.string new_toys;

float autocvar_g_new_toys_autoreplace;
bool autocvar_g_new_toys_use_pickupsound = false;
const float NT_AUTOREPLACE_NEVER = 0;
const float NT_AUTOREPLACE_ALWAYS = 1;
const float NT_AUTOREPLACE_RANDOM = 2;

bool nt_IsNewToy(int w)
{
	switch(w)
	{
		case WEP_SEEKER.m_id:
		case WEP_MINE_LAYER.m_id:
		case WEP_HLAC.m_id:
		case WEP_RIFLE.m_id:
		case WEP_SHOCKWAVE.m_id:
			return true;
		default:
			return false;
	}
}

string nt_GetFullReplacement(string w)
{
	switch(w)
	{
		case "hagar": return "seeker";
		case "devastator": return "minelayer";
		case "machinegun": return "hlac";
		case "vortex": return "rifle";
		                                     
		default: return string_null;
	}
}

string nt_GetReplacement(string w, float m)
{
	if(m == NT_AUTOREPLACE_NEVER)
		return w;
	string s = nt_GetFullReplacement(w);
	if (!s)
		return w;
	if(m == NT_AUTOREPLACE_RANDOM)
		s = strcat(w, " ", s);
	return s;
}

MUTATOR_HOOKFUNCTION(nt, SetStartItems)
{
	                                 
	                                                            
	                  

	float j, n;

	WepSet newdefault;
	WepSet warmup_newdefault;

	newdefault = '0 0 0';
	warmup_newdefault = '0 0 0';

	WepSet seti = '0 0 0';

	FOREACH(Weapons, it != WEP_Null, {
		seti = it.m_wepset;
		n = tokenize_console(nt_GetReplacement(it.netname, autocvar_g_new_toys_autoreplace));

		for(j = 0; j < n; ++j)
			FOREACH(Weapons, it != WEP_Null, {
				if(it.netname == argv(j))
				{
					WepSet setk = it.m_wepset;
					if(start_weapons & seti) newdefault |= setk;
					if(warmup_start_weapons & seti) warmup_newdefault |= setk;
				}
			});
	});

	newdefault &= start_weapons_defaultmask;
	start_weapons &= ~start_weapons_defaultmask;
	start_weapons |= newdefault;

	warmup_newdefault &= warmup_start_weapons_defaultmask;
	warmup_start_weapons &= ~warmup_start_weapons_defaultmask;
	warmup_start_weapons |= warmup_newdefault;
}

MUTATOR_HOOKFUNCTION(nt, SetWeaponreplace)
{
	if (MUTATOR_IS_ENABLED(random_items))
	{
		                                                        
		return;
	}
	entity wep = M_ARGV(0, entity);
	entity wepinfo = M_ARGV(1, entity);
	string ret_string = M_ARGV(2, string);

	                           
	if(wep.new_toys)
	{
		                           
		ret_string = wep.new_toys;
	}
	else
	{
		                    
		ret_string = nt_GetReplacement(wepinfo.netname, autocvar_g_new_toys_autoreplace);
	}

	                              
	ret_string = W_Apply_Weaponreplace(ret_string);

	M_ARGV(2, string) = ret_string;
}

MUTATOR_HOOKFUNCTION(nt, FilterItem)
{
	entity item = M_ARGV(0, entity);

	if(nt_IsNewToy(item.weapon) && autocvar_g_new_toys_use_pickupsound) {
		item.item_pickupsound = string_null;
		item.item_pickupsound_ent = SND_WEAPONPICKUP_NEW_TOYS;
	}
}
