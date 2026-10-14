#include "common.qh"

#include <common/constants.qh>
#include <common/deathtypes/all.qh>
#include <common/items/_mod.qh>
#include <common/net_linked.qh>
#include <common/notifications/all.qh>
#include <common/state.qh>
#include <common/stats.qh>
#include <common/util.qh>
#include <common/weapons/_all.qh>
#include <common/wepent.qh>
#include <server/command/common.qh>
#include <server/damage.qh>
#include <server/hook.qh>
#include <server/items/items.qh>
#include <server/mutators/_mod.qh>
#include <server/weapons/csqcprojectile.qh>

bool W_DualWielding(entity player)
{
	int held_weapons = 0;
	for(int slot = 0; slot < MAX_WEAPONSLOTS; ++slot)
	{
		.entity weaponentity = weaponentities[slot];
		if(player.(weaponentity) && player.(weaponentity).m_switchweapon != WEP_Null)
			++held_weapons;
	}

	return held_weapons > 1;
}

void W_GiveWeapon(entity e, int wep)
{
	if (!wep) return;

	STAT(WEAPONS, e) |= WepSet_FromWeapon(REGISTRY_GET(Weapons, wep));
}

void W_PlayStrengthSound(entity player)
{
	MUTATOR_CALLHOOK(W_PlayStrengthSound, player);
}

float W_CheckProjectileDamage(entity inflictor, entity projowner, int deathtype, float exception)
{
	float is_from_contents = (deathtype == DEATH_SLIME.m_id || deathtype == DEATH_LAVA.m_id);
	float is_from_owner = (inflictor == projowner);
	float is_from_exception = (exception != -1);

	                                                                                                                                                                                                             

	if(autocvar_g_projectiles_damage <= -2)
	{
		return false;                                                                 
	}
	else if(autocvar_g_projectiles_damage == -1)
	{
		if(is_from_exception)
			return (exception);                                                  
		else
			return false;                                         
	}
	else if(autocvar_g_projectiles_damage == 0)
	{
		if(is_from_exception)
			return (exception);                                                  
		else if(!is_from_contents)
			return false;                                              
	}
	else if(autocvar_g_projectiles_damage == 1)
	{
		if(is_from_exception)
			return (exception);                                                  
		else if(!(is_from_contents || is_from_owner))
			return false;                                                              
	}
	else if(autocvar_g_projectiles_damage == 2)                                                 
	{
		if(is_from_exception)
			return (exception);                                                  
	}

	return true;                                                      
}

void W_PrepareExplosionByDamage(entity this, entity attacker, void(entity this) explode)
{
	this.takedamage = DAMAGE_NO;
	this.event_damage = func_null;

	MUTATOR_CALLHOOK(PrepareExplosionByDamage, this, attacker);

	if(IS_CLIENT(attacker) && !autocvar_g_projectiles_keep_owner)
	{
		this.owner = attacker;
		this.realowner = attacker;
	}

	                                            
	                                                          
	this.nextthink = time;
	setthink(this, explode);
}

void adaptor_think2use_hittype_splash(entity this)                                   
{
	if(!(IS_ONGROUND(this)))                                                                                                                                           
		this.projectiledeathtype |= HITTYPE_SPLASH;
	adaptor_think2use(this);
}

bool SUB_NoImpactCheck(entity this, entity toucher)
{
	                                                                 
	                                                                   
	                                                                       
	                                               
	                                                                                                                 
#if 0
	if(trace_dphitcontents == 0)
	{
		LOG_TRACEF("A hit from a projectile happened with no hit contents! DEBUG THIS, this should never happen for projectiles! Projectile will self-destruct. (edict: %i, classname: %s, origin: %v)", this, this.classname, this.origin);
		checkclient(this);                                                                                          
	}
#endif
    if (trace_dphitq3surfaceflags & Q3SURFACEFLAG_NOIMPACT)
        return true;
    if (toucher == NULL && this.size != '0 0 0')
    {
        vector tic;
        tic = this.velocity * sys_frametime;
        tic = tic + normalize(tic) * vlen(this.maxs - this.mins);
        traceline(this.origin - tic, this.origin + tic, MOVE_NORMAL, this);
        if (trace_fraction >= 1)
        {
                                                                                                                  
                                                  
        }
        else if (trace_dphitq3surfaceflags & Q3SURFACEFLAG_NOIMPACT)
        {
            LOG_TRACE("Detected and prevented the sky-grapple bug.");
            return true;
        }
    }

    return false;
}

bool WarpZone_Projectile_Touch_ImpactFilter_Callback(entity this, entity toucher)
{
	              
	if(toucher && toucher == this.owner)
		return true;
	if(SUB_NoImpactCheck(this, toucher))
	{
		if(this.classname == "nade")
			return false;                  
		else if(this.classname == "grapplinghook")
			RemoveHook(this);
		else
			delete(this);
		return true;
	}
	if(trace_ent && trace_ent.solid > SOLID_TRIGGER)
		UpdateCSQCProjectile(this);
	return false;
}
