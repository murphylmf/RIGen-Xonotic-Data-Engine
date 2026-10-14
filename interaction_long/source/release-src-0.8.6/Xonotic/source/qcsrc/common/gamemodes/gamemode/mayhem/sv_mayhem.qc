#include "sv_mayhem.qh"
#include <common/scores.qh>

                                                                   
#include "common/gamemodes/gamemode/tmayhem/sv_tmayhem.qh"

float autocvar_g_mayhem_point_limit;
float autocvar_g_mayhem_point_leadlimit;

bool autocvar_g_mayhem_regenerate;
bool autocvar_g_mayhem_rot;
string autocvar_g_mayhem_weaponarena;
bool autocvar_g_mayhem_powerups;
bool autocvar_g_mayhem_selfdamage;
float autocvar_g_mayhem_scoring_upscaler;
float autocvar_g_mayhem_scoring_damage_weight;
float autocvar_g_mayhem_scoring_kill_weight;
bool autocvar_g_mayhem_scoring_disable_selfdamage2score;
bool autocvar_g_mayhem_pickup_items;
bool autocvar_g_mayhem_pickup_items_remove_weapons_and_ammo;
bool autocvar_g_mayhem_unlimited_ammo;

float autocvar_g_mayhem_start_health = 200;
float autocvar_g_mayhem_start_armor = 200;
float autocvar_g_mayhem_start_ammo_shells = 60;
float autocvar_g_mayhem_start_ammo_nails = 320;
float autocvar_g_mayhem_start_ammo_rockets = 160;
float autocvar_g_mayhem_start_ammo_cells = 180;
float autocvar_g_mayhem_start_ammo_plasma = 180;
float autocvar_g_mayhem_start_ammo_fuel = 0;

.float total_damage_dealt;

  
                 
                                    
 
        
 
  

void mayhem_Initialize()
{
	GameRules_limit_score(autocvar_g_mayhem_point_limit);
	GameRules_limit_lead(autocvar_g_mayhem_point_leadlimit);

	                 
	                                                                
}

  
                                                        
 
                                                                                      
                                                                                  
                                                                   
                                                                                     
                                                                
              
 
  

MUTATOR_HOOKFUNCTION(mayhem, SetStartItems)
{
	start_items       &= ~(IT_UNLIMITED_AMMO | IT_UNLIMITED_SUPERWEAPONS);
	if (!cvar("g_use_ammunition") || autocvar_g_mayhem_unlimited_ammo)
		start_items |= IT_UNLIMITED_AMMO;

	start_health       = warmup_start_health       = autocvar_g_mayhem_start_health;
	start_armorvalue   = warmup_start_armorvalue   = autocvar_g_mayhem_start_armor;
	start_ammo_shells  = warmup_start_ammo_shells  = autocvar_g_mayhem_start_ammo_shells;
	start_ammo_nails   = warmup_start_ammo_nails   = autocvar_g_mayhem_start_ammo_nails;
	start_ammo_rockets = warmup_start_ammo_rockets = autocvar_g_mayhem_start_ammo_rockets;
	start_ammo_cells   = warmup_start_ammo_cells   = autocvar_g_mayhem_start_ammo_cells;
	start_ammo_plasma  = warmup_start_ammo_plasma  = autocvar_g_mayhem_start_ammo_plasma;
	start_ammo_fuel    = warmup_start_ammo_fuel    = autocvar_g_mayhem_start_ammo_fuel;
}

MUTATOR_HOOKFUNCTION(mayhem, PlayerRegen)
{
	if(!autocvar_g_mayhem_regenerate)
		M_ARGV(2, float) = 0;
	if(!autocvar_g_mayhem_rot)
		M_ARGV(3, float) = 0;
	return (!autocvar_g_mayhem_regenerate && !autocvar_g_mayhem_rot);
}

MUTATOR_HOOKFUNCTION(mayhem, ForbidThrowCurrentWeapon)
{
	return true;
}

MUTATOR_HOOKFUNCTION(mayhem, SetWeaponArena)
{
	if (M_ARGV(0, string) == "0" || M_ARGV(0, string) == "")
		M_ARGV(0, string) = autocvar_g_mayhem_weaponarena;
}

MUTATOR_HOOKFUNCTION(mayhem, FilterItem)
{
	entity item = M_ARGV(0, entity);

	                                                                                                                  
	if (autocvar_g_powerups == 1 || (autocvar_g_powerups == -1 && autocvar_g_mayhem_powerups == 1)){
		if (item.itemdef.instanceOfPowerup){
			return false;
		}
	}
	                                                               
	if (autocvar_g_powerups == 0 || autocvar_g_mayhem_powerups == 0){
		if (item.itemdef.instanceOfPowerup){
			return true;
		}
	}
	                                                    
	if (autocvar_g_pickup_items == 0){
		return true;
	}
	                                                                                        
	if ((autocvar_g_mayhem_pickup_items == 1 && autocvar_g_mayhem_pickup_items_remove_weapons_and_ammo == 1) && autocvar_g_pickup_items <= 0){
		if (item.itemdef.instanceOfAmmo || item.itemdef.instanceOfWeaponPickup){
			return true;
		}
	}
	                                                                                 
	if (autocvar_g_pickup_items == -1 && autocvar_g_mayhem_pickup_items == 0){
		return true;
	}
	return false;
}

MUTATOR_HOOKFUNCTION(mayhem, Damage_Calculate)
{
	entity frag_attacker = M_ARGV(1, entity);
	entity frag_target = M_ARGV(2, entity);
	float frag_deathtype = M_ARGV(3, float);
	float frag_damage = M_ARGV(4, float);

	if (IS_PLAYER(frag_target))                                                                           
	if (!IS_DEAD(frag_target))                                                                                
	if ((autocvar_g_mayhem_selfdamage == 0 && frag_target == frag_attacker) || frag_deathtype == DEATH_FALL.m_id)
		frag_damage = 0;

	M_ARGV(4, float) = frag_damage;
}

void MayhemCalculatePlayerScore(entity scorer)
{
	int scoringmethod = 1;
	float upscaler;                                   
	float frag_weight;                                         
	float damage_weight;                                                                 

	                                                      
	                                                                       
	                                                                                                   

	bool disable_selfdamage2score;

	if (teamplay) {
		                         
		upscaler = autocvar_g_tmayhem_scoring_upscaler;
		frag_weight = autocvar_g_tmayhem_scoring_kill_weight;
		damage_weight = autocvar_g_tmayhem_scoring_damage_weight;
		disable_selfdamage2score = autocvar_g_tmayhem_scoring_disable_selfdamage2score;
	} else {
		                        
		upscaler = autocvar_g_mayhem_scoring_upscaler;
		frag_weight = autocvar_g_mayhem_scoring_kill_weight;
		damage_weight = autocvar_g_mayhem_scoring_damage_weight;
		disable_selfdamage2score = autocvar_g_mayhem_scoring_disable_selfdamage2score;
	}

	                                                              

	if (frag_weight && damage_weight)                                                     
		scoringmethod = 1;
	else if (frag_weight)                           
		scoringmethod = 2;
	else if (damage_weight)                             
		scoringmethod = 3;
	else
		return;                                                  

	switch (scoringmethod)
	{
		default:
		case 1:
		{
			                                                                                                                              

			                                                                                                                                                    
			float suicide_weight = 1 + (disable_selfdamage2score / frag_weight);

			                                                                                                         
			                                              
			float playerdamagescore = ((scorer.total_damage_dealt / (start_health + start_armorvalue)) * 100) * upscaler * damage_weight;
			                                                                                                                                                

			                                           
			float roundedplayerdamagescore = rint(playerdamagescore * 10) / 10;

			                  
			float killcount = PlayerScore_Get(scorer, SP_KILLS) - PlayerScore_Get(scorer, SP_TEAMKILLS) - (PlayerScore_Get(scorer, SP_SUICIDES) * suicide_weight);

			                                         
			float playerkillscore = (killcount * 100) * upscaler * frag_weight;
			                                                                                        

			float playerscore = roundedplayerdamagescore + playerkillscore;

			                                                                                                         
			float scoretoadd = playerscore - (PlayerScore_Get(scorer, SP_SCORE) * 100);
			                                                                                                                         

			                                                               
			GameRules_scoring_add_team(scorer, SCORE, floor(scoretoadd / 100));
			                                                                                                           

			#if 0
				                 
				if(!IS_BOT_CLIENT(scorer)){
					print(sprintf("%f", scorer.total_damage_dealt),         " scorer.total_damage_dealt \n");
					print(sprintf("%f", scorer.hitsound_damage_dealt),      " scorer.hitsound_damage_dealt \n");
					print(sprintf("%f", playerdamagescore/100),             " playerdamagescore \n");
					print(sprintf("%f", roundedplayerdamagescore/100),      " rounded playerdamagescore \n");
					print(sprintf("%f", playerkillscore/100),               " playerkillscore \n");
					print(sprintf("%f", PlayerScore_Get(scorer, SP_KILLS)), " PlayerScore_Get(scorer, SP_KILLS) \n");
					print(sprintf("%f", playerscore/100),                   " playerscore \n");
					print(sprintf("%f", scoretoadd/100),                    " scoretoadd \n");
					print(sprintf("%f", PlayerScore_Get(scorer, SP_SCORE)), " PlayerScore_Get(scorer, SP_SCORE) \n \n");
				}
			#endif
			return;
		}

		case 2:
		{
			                                                                                                             
			float playerkillscore = PlayerScore_Get(scorer, SP_KILLS) - PlayerScore_Get(scorer, SP_TEAMKILLS) - PlayerScore_Get(scorer, SP_SUICIDES);
			float upscaledplayerscore = playerkillscore * upscaler;
			float scoretoadd = upscaledplayerscore - PlayerScore_Get(scorer, SP_SCORE);
			GameRules_scoring_add_team(scorer, SCORE, floor(scoretoadd));

			#if 0
				                 
				if(!IS_BOT_CLIENT(scorer)){
					print(sprintf("%f", playerkillscore),                   " playerkillscore \n");
					print(sprintf("%f", PlayerScore_Get(scorer, SP_KILLS)), " PlayerScore_Get(scorer, SP_KILLS) \n");
					print(sprintf("%f", upscaledplayerscore),               " upscaled playerscore \n");
					print(sprintf("%f", scoretoadd),                        " scoretoadd \n");
					print(sprintf("%f", PlayerScore_Get(scorer, SP_SCORE)), " PlayerScore_Get(scorer, SP_SCORE) \n \n");
				}
			#endif
			return;
		}

		case 3:
		{
			                                                                                                             
			float playerdamagescore = ((scorer.total_damage_dealt / (start_health + start_armorvalue)) * 100);
			float roundedplayerdamagescore = rint(playerdamagescore * 10) / 10;
			float upscaledplayerscore = roundedplayerdamagescore * upscaler;
			float scoretoadd = upscaledplayerscore - (PlayerScore_Get(scorer, SP_SCORE) * 100);
			GameRules_scoring_add_team(scorer, SCORE, floor(scoretoadd / 100));

			#if 0
				                 
				if(!IS_BOT_CLIENT(scorer)){
					print(sprintf("%f", scorer.total_damage_dealt),         " scorer.total_damage_dealt \n");
					print(sprintf("%f", playerdamagescore),                 " playerdamagescore \n");
					print(sprintf("%f", roundedplayerdamagescore),          " rounded playerdamagescore \n");
					print(sprintf("%f", upscaledplayerscore),               " upscaled playerscore \n");
					print(sprintf("%f", scoretoadd),                        " scoretoadd \n");
					print(sprintf("%f", PlayerScore_Get(scorer, SP_SCORE)), " PlayerScore_Get(scorer, SP_SCORE) \n \n");
				}
			#endif
			return;
		}
	}
}

MUTATOR_HOOKFUNCTION(mayhem, PlayerDamage_SplitHealthArmor)
{
	if (!autocvar_g_mayhem_scoring_damage_weight) return;

	entity frag_target = M_ARGV(2, entity);

	if (StatusEffects_active(STATUSEFFECT_SpawnShield, frag_target) && autocvar_g_spawnshield_blockdamage >= 1) return;

	entity frag_attacker = M_ARGV(1, entity);
	float frag_deathtype = M_ARGV(6, float);
	float frag_damage = M_ARGV(7, float);
	float damage_take = bound(0, M_ARGV(4, float), GetResource(frag_target, RES_HEALTH));
	float damage_save = bound(0, M_ARGV(5, float), GetResource(frag_target, RES_ARMOR));
	float excess = max(0, frag_damage - damage_take - damage_save);
	float total = frag_damage - excess;

	if (total == 0) return;

	if (StatusEffects_active(STATUSEFFECT_SpawnShield, frag_target) && autocvar_g_spawnshield_blockdamage)
		total *= 1 - autocvar_g_spawnshield_blockdamage;

	entity scorer = NULL;                                                

	if (IS_PLAYER(frag_attacker))
	{
		                    
		if (frag_target != frag_attacker)
			frag_attacker.total_damage_dealt += total;

		                                
		if (frag_target == frag_attacker && !autocvar_g_mayhem_scoring_disable_selfdamage2score)
			frag_attacker.total_damage_dealt -= total;

		scorer = frag_attacker;
	}
	else
	{
		                                                                     
		                                                                 
		                                                                 
		              
		                                                                                                                                     
		                                               
		                                                              
		if (!autocvar_g_mayhem_scoring_disable_selfdamage2score && (
				frag_deathtype == DEATH_KILL.m_id ||
				frag_deathtype == DEATH_DROWN.m_id ||
				frag_deathtype == DEATH_HURTTRIGGER.m_id ||
				frag_deathtype == DEATH_CAMP.m_id ||
				frag_deathtype == DEATH_LAVA.m_id ||
				frag_deathtype == DEATH_SLIME.m_id ||
				frag_deathtype == DEATH_SWAMP.m_id))
			frag_target.total_damage_dealt -= total;

		scorer = frag_target;
	}

	#if 0
		                 
		if(!IS_BOT_CLIENT(scorer)){
			print(sprintf("%f", total), " total dmg from PlayerDamage_SplitHealthArmor \n");
			print(sprintf("%f", scorer.total_damage_dealt), "scorer.total_damage_dealt\n");
		}
	#endif

	MayhemCalculatePlayerScore(scorer);
}

MUTATOR_HOOKFUNCTION(mayhem, GiveFragsForKill, CBC_ORDER_FIRST)
{
	entity frag_attacker = M_ARGV(0, entity);
	M_ARGV(2, float) = 0;                                      

	if (IS_PLAYER(frag_attacker)) MayhemCalculatePlayerScore(frag_attacker);

	return true;
}

MUTATOR_HOOKFUNCTION(mayhem, reset_map_players)
{
	                              
	FOREACH_CLIENT(true, {
		it.total_damage_dealt = 0;
	});
	return false;
}

