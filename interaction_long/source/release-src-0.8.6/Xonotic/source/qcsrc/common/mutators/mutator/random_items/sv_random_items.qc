#include "sv_random_items.qh"

         
                                                                                
                   
                                              

                                                                               

                                                                               

                

                                         
                                              

                        

                                                        
                                                 

                                                                        
                                                          

       

float autocvar_g_random_loot_min;                                   
float autocvar_g_random_loot_max;                                   
float autocvar_g_random_loot_time;                                        
float autocvar_g_random_loot_spread;                                 

                         

                                                     
                                                

                                                                     
                                                         

                                                                          
              
bool random_items_is_spawning = false;

                                                                               

                                                                         
                                                                  
                                         
string RandomItems_GetRandomItemClassNameWithProperty(string prefix,
	.bool item_property);

                                                                               

string RandomItems_GetRandomItemClassName(string prefix)
{
	if (MUTATOR_CALLHOOK(RandomItems_GetRandomItemClassName, prefix))
	{
		return M_ARGV(1, string);
	}
	return RandomItems_GetRandomVanillaItemClassName(prefix,
		RANDOM_ITEM_TYPE_ALL);
}

string RandomItems_GetRandomVanillaItemClassName(string prefix, int types)
{
	if (types == 0)
	{
		return "";
	}
	while (types != 0)
	{
		string cvar_name;
		RandomSelection_Init();
		if (types & RANDOM_ITEM_TYPE_HEALTH)
		{
			cvar_name = sprintf("g_%s_health_probability", prefix);
			if (!(cvar_type(cvar_name) & CVAR_TYPEFLAG_EXISTS))
			{
				LOG_WARNF("Random items: cvar %s doesn't exist.", cvar_name);
			}
			else
			{
				RandomSelection_AddFloat(RANDOM_ITEM_TYPE_HEALTH,
					cvar(cvar_name), 1);
			}
		}
		if (types & RANDOM_ITEM_TYPE_ARMOR)
		{
			cvar_name = sprintf("g_%s_armor_probability", prefix);
			if (!(cvar_type(cvar_name) & CVAR_TYPEFLAG_EXISTS))
			{
				LOG_WARNF("Random items: cvar %s doesn't exist.", cvar_name);
			}
			else
			{
				RandomSelection_AddFloat(RANDOM_ITEM_TYPE_ARMOR,
					cvar(cvar_name), 1);
			}
		}
		if (types & RANDOM_ITEM_TYPE_RESOURCE)
		{
			cvar_name = sprintf("g_%s_resource_probability", prefix);
			if (!(cvar_type(cvar_name) & CVAR_TYPEFLAG_EXISTS))
			{
				LOG_WARNF("Random items: cvar %s doesn't exist.", cvar_name);
			}
			else
			{
				RandomSelection_AddFloat(RANDOM_ITEM_TYPE_RESOURCE,
					cvar(cvar_name), 1);
			}
		}
		if (types & RANDOM_ITEM_TYPE_WEAPON)
		{
			cvar_name = sprintf("g_%s_weapon_probability", prefix);
			if (!(cvar_type(cvar_name) & CVAR_TYPEFLAG_EXISTS))
			{
				LOG_WARNF("Random items: cvar %s doesn't exist.", cvar_name);
			}
			else
			{
				RandomSelection_AddFloat(RANDOM_ITEM_TYPE_WEAPON, cvar(cvar_name), 1);
			}
		}
		if (types & RANDOM_ITEM_TYPE_POWERUP)
		{
			cvar_name = sprintf("g_%s_powerup_probability", prefix);
			if (!(cvar_type(cvar_name) & CVAR_TYPEFLAG_EXISTS))
			{
				LOG_WARNF("Random items: cvar %s doesn't exist.", cvar_name);
			}
			else
			{
				RandomSelection_AddFloat(RANDOM_ITEM_TYPE_POWERUP, cvar(cvar_name), 1);
			}
		}
		int item_type = RandomSelection_chosen_float;
		string class_name = "";
		switch (item_type)
		{
			case RANDOM_ITEM_TYPE_HEALTH:
			{
				class_name = RandomItems_GetRandomItemClassNameWithProperty(
					prefix, instanceOfHealth);
				break;
			}
			case RANDOM_ITEM_TYPE_ARMOR:
			{
				class_name = RandomItems_GetRandomItemClassNameWithProperty(
					prefix, instanceOfArmor);
				break;
			}
			case RANDOM_ITEM_TYPE_RESOURCE:
			{
				class_name = RandomItems_GetRandomItemClassNameWithProperty(
					prefix, instanceOfAmmo);
				break;
			}
			case RANDOM_ITEM_TYPE_WEAPON:
			{
				RandomSelection_Init();
				FOREACH(Weapons, it != WEP_Null &&
					!(it.spawnflags & WEP_FLAG_MUTATORBLOCKED),
				{
					cvar_name = sprintf("g_%s_%s_probability", prefix,
						it.m_canonical_spawnfunc);
					if (!(cvar_type(cvar_name) & CVAR_TYPEFLAG_EXISTS))
					{
						LOG_WARNF("Random items: cvar %s doesn't exist.",
							cvar_name);
						continue;
					}
					RandomSelection_AddString(it.m_canonical_spawnfunc,
						cvar(cvar_name), 1);
				});
				class_name = RandomSelection_chosen_string;
				break;
			}
			case RANDOM_ITEM_TYPE_POWERUP:
			{
				class_name = RandomItems_GetRandomItemClassNameWithProperty(
					prefix, instanceOfPowerup);
				break;
			}
		}
		if (class_name != "")
		{
			return class_name;
		}
		types &= ~item_type;
	}
	return "";
}

                                                                               

                                                                 
                                    
                                                          
string RandomItems_GetItemReplacementClassNames(entity item)
{
	string cvar_name = sprintf("g_random_items_replace_%s", item.classname);
	if (!(cvar_type(cvar_name) & CVAR_TYPEFLAG_EXISTS))
	{
		LOG_WARNF("Random items: cvar %s doesn't exist.", cvar_name);
		return "";
	}
	return cvar_string(cvar_name);
}

string RandomItems_GetRandomItemClassNameWithProperty(string prefix,
	.bool item_property)
{
	RandomSelection_Init();
	FOREACH(Items, it.item_property && (it.spawnflags & ITEM_FLAG_NORMAL) &&
		Item_IsDefinitionAllowed(it),
	{
		string cvar_name = sprintf("g_%s_%s_probability", prefix,
			it.m_canonical_spawnfunc);
		if (!(cvar_type(cvar_name) & CVAR_TYPEFLAG_EXISTS))
		{
			LOG_WARNF("Random items: cvar %s doesn't exist.", cvar_name);
			continue;
		}
		RandomSelection_AddString(it.m_canonical_spawnfunc, cvar(cvar_name), 1);
	});
	return RandomSelection_chosen_string;
}

                               
                                    
                                                    
entity RandomItems_ReplaceMapItem(entity item)
{
	                                                       
	string new_classnames = RandomItems_GetItemReplacementClassNames(item);
	if (new_classnames == "")
	{
		return NULL;
	}
	string new_classname;
	if (new_classnames == "random")
	{
		new_classname = RandomItems_GetRandomItemClassName("random_items");
		if (new_classname == "")
		{
			return NULL;
		}
	}
	else
	{
		int num_new_classnames = tokenize_console(new_classnames);
		if (num_new_classnames == 1)
		{
			new_classname = new_classnames;
		}
		else
		{
			int classname_index = floor(random() * num_new_classnames);
			new_classname = argv(classname_index);
		}
	}
	                                                           
	if (new_classname == item.classname)
	{
		return NULL;
	}
	random_items_is_spawning = true;
	entity new_item;
	if (!MUTATOR_IS_ENABLED(ok))
	{
		                                            
		new_item = Item_Create(strzone(new_classname), item.origin,
			Item_ShouldKeepPosition(item));
		random_items_is_spawning = false;
		if (new_item == NULL)
		{
			return NULL;
		}
	}
	else
	{
		new_item = spawn();
		Item_CopyFields(item, new_item);
		new_item.classname = strzone(new_classname);
		new_item.ok_item = true;
		Item_Initialize(new_item, new_classname);
		random_items_is_spawning = false;
		if (wasfreed(new_item))
		{
			return NULL;
		}
	}
	if (item.team)
	{
		new_item.team = item.team;
	}
	return new_item;
}

                                     
                                             
                      
void RandomItems_SpawnLootItem(vector position)
{
	string class_name = RandomItems_GetRandomItemClassName("random_loot");
	if (class_name == "")
	{
		return;
	}
	vector spread = '0 0 0';
	spread.z = autocvar_g_random_loot_spread / 2;
	spread += randomvec() * autocvar_g_random_loot_spread;
	random_items_is_spawning = true;
	if (!MUTATOR_IS_ENABLED(ok))
	{
		Item_CreateLoot(class_name, position, spread,
			autocvar_g_random_loot_time);
	}
	else
	{
		entity item = spawn();
		item.ok_item = true;
		item.classname = class_name;
		Item_InitializeLoot(item, class_name, position, spread,
			autocvar_g_random_loot_time);
	}
	random_items_is_spawning = false;
}

                                                                              

MUTATOR_HOOKFUNCTION(random_items, BuildMutatorsString)
{
	M_ARGV(0, string) = strcat(M_ARGV(0, string), ":random_items");
}

MUTATOR_HOOKFUNCTION(random_items, BuildMutatorsPrettyString)
{
	M_ARGV(0, string) = strcat(M_ARGV(0, string), ", Random items");
}

                                                              
MUTATOR_HOOKFUNCTION(random_items, FilterItem, CBC_ORDER_LAST)
{
	                               
	if (!autocvar_g_random_items)
	{
		return false;
	}
	if (random_items_is_spawning == true)
	{
		return false;
	}
	entity item = M_ARGV(0, entity);
	if (Item_IsLoot(item))
	{
		return false;
	}
	if (RandomItems_ReplaceMapItem(item) == NULL)
	{
		return false;
	}
	return true;
}

                                                                    
MUTATOR_HOOKFUNCTION(random_items, ItemTouched, CBC_ORDER_LAST)
{
	                                
	if (!autocvar_g_random_items)
	{
		return;
	}
	entity item = M_ARGV(0, entity);
	if (Item_IsLoot(item))
	{
		return;
	}
	entity new_item = RandomItems_ReplaceMapItem(item);
	if (new_item == NULL)
	{
		return;
	}
	Item_ScheduleRespawn(new_item);
	delete(item);
}

                                                     
MUTATOR_HOOKFUNCTION(random_items, PlayerDies)
{
	                               
	if (!autocvar_g_random_loot)
	{
		return;
	}
	entity victim = M_ARGV(2, entity);
	vector loot_position = victim.origin + '0 0 32';
	int num_loot_items = floor(autocvar_g_random_loot_min + random() *
		autocvar_g_random_loot_max);
	for (int item_index = 0; item_index < num_loot_items; ++item_index)
	{
		RandomItems_SpawnLootItem(loot_position);
	}
}
