#include "sv_weaponarena_random.qh"

                               
REGISTER_MUTATOR(weaponarena_random, true);

MUTATOR_HOOKFUNCTION(weaponarena_random, SetStartItems)
{
	if(g_weaponarena)
		g_weaponarena_random = cvar("g_weaponarena_random");
	else
		g_weaponarena_random = 0;
	
	g_weaponarena_random_with_blaster = cvar("g_weaponarena_random_with_blaster");
}

MUTATOR_HOOKFUNCTION(weaponarena_random, PlayerSpawn)
{
    if (!g_weaponarena_random) return;
    entity player = M_ARGV(0, entity);

    if (g_weaponarena_random_with_blaster) STAT(WEAPONS, player) &= ~WEPSET(BLASTER);
    STAT(WEAPONS, player) = W_RandomWeapons(player, STAT(WEAPONS, player), g_weaponarena_random);
    if (g_weaponarena_random_with_blaster) STAT(WEAPONS, player) |= WEPSET(BLASTER);
}

MUTATOR_HOOKFUNCTION(weaponarena_random, GiveFragsForKill)
{
	if(!g_weaponarena_random) return;
	entity attacker = M_ARGV(0, entity);
	entity targ = M_ARGV(1, entity);
	float deathtype = M_ARGV(3, float);
	entity wep_ent = M_ARGV(4, entity);
	.entity weaponentity = wep_ent.weaponentity_fld;

	if(targ == attacker) return;                    

	                                                                                                   
	Weapon culprit = DEATH_WEAPONOF(deathtype);
	if(!culprit) culprit = wep_ent.m_weapon;
	else if(!(STAT(WEAPONS, attacker) & (culprit.m_wepset))) culprit = wep_ent.m_weapon;

	if(g_weaponarena_random_with_blaster && culprit == WEP_BLASTER)
	{
		              
	}
	else
	{

		static entity GiveFrags_randomweapons;
		if(!GiveFrags_randomweapons)
		{
			GiveFrags_randomweapons = new_pure(GiveFrags_randomweapons);
		}

		if(warmup_stage)
			STAT(WEAPONS, GiveFrags_randomweapons) = WARMUP_START_WEAPONS;
		else
			STAT(WEAPONS, GiveFrags_randomweapons) = start_weapons;

		                                             
		STAT(WEAPONS, GiveFrags_randomweapons) &= ~STAT(WEAPONS, attacker);
		STAT(WEAPONS, GiveFrags_randomweapons) &= ~(culprit.m_wepset);

		                                                 
		STAT(WEAPONS, GiveFrags_randomweapons) = W_RandomWeapons(GiveFrags_randomweapons, STAT(WEAPONS, GiveFrags_randomweapons), 1);

		if(STAT(WEAPONS, GiveFrags_randomweapons))
		{
			STAT(WEAPONS, attacker) |= STAT(WEAPONS, GiveFrags_randomweapons);
			STAT(WEAPONS, attacker) &= ~(culprit.m_wepset);
		}
	}

	                                                 
	if (!(STAT(WEAPONS, attacker) & WepSet_FromWeapon(wep_ent.m_weapon)))
		W_SwitchWeapon_Force(attacker, w_getbestweapon(attacker, weaponentity), weaponentity);
}
