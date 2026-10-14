#include "sv_status_effects.qh"

METHOD(StatusEffects, m_active, bool(StatusEffects this, entity actor))
{
	TC(StatusEffects, this);
	if(!actor.statuseffects)
		return false;              
	return (actor.statuseffects.statuseffect_flags[this.m_id] & STATUSEFFECT_FLAG_ACTIVE);
}

METHOD(StatusEffects, m_tick, void(StatusEffects this, entity actor))
{
	StatusEffects data = actor.statuseffects;
	.int flg = statuseffect_flags[this.m_id];
	int oldflag = data.(flg);
	data.(flg) = BITSET(data.(flg), STATUSEFFECT_FLAG_PERSISTENT, this.m_persistent(this, actor));
	if(oldflag != data.(flg))
		StatusEffects_update(actor);

	if(data.(flg) & STATUSEFFECT_FLAG_PERSISTENT)
		return;
	if(time > actor.statuseffects.statuseffect_time[this.m_id])
	{
		this.m_remove(this, actor, STATUSEFFECT_REMOVE_TIMEOUT);
		return;
	}
}

METHOD(StatusEffects, m_apply, void(StatusEffects this, entity actor, float eff_time, float eff_flags))
{
	if(!actor.statuseffects)
		StatusEffects_new(actor);

	eff_flags |= STATUSEFFECT_FLAG_ACTIVE;                                                       
	actor.statuseffects.statuseffect_time[this.m_id] = eff_time;                                                              
	actor.statuseffects.statuseffect_flags[this.m_id] = eff_flags;
	StatusEffects_update(actor);
}

METHOD(StatusEffects, m_remove, void(StatusEffects this, entity actor, int removal_type))
{
	StatusEffects data = actor.statuseffects;
	if(!data)
		return;
	                                                                                                      
	if(removal_type == STATUSEFFECT_REMOVE_NORMAL && !(data.statuseffect_flags[this.m_id] & STATUSEFFECT_FLAG_PERSISTENT) && this.m_active(this, actor))
		sound(actor, CH_TRIGGER, this.m_sound_rm, VOL_BASE, ATTEN_NORM);
	data.statuseffect_time[this.m_id] = 0;
	data.statuseffect_flags[this.m_id] = 0;
	StatusEffects_update(actor);
}

MUTATOR_HOOKFUNCTION(status_effects, SV_StartFrame)
{
	if(game_stopped)
		return;
	                                                                                
	                                                                                                                              
	IL_EACH(g_damagedbycontents, it.damagedbycontents,
	{
		if (it.move_movetype == MOVETYPE_NOCLIP || !it.statuseffects) continue;
		StatusEffects_tick(it);
	});
}

MUTATOR_HOOKFUNCTION(status_effects, PlayerDies)
{
	entity frag_target = M_ARGV(2, entity);

	StatusEffects_removeall(frag_target, STATUSEFFECT_REMOVE_NORMAL);
}

MUTATOR_HOOKFUNCTION(status_effects, ClientDisconnect)
{
	entity player = M_ARGV(0, entity);

	StatusEffects_removeall(player, STATUSEFFECT_REMOVE_NORMAL);                                       
	return true;
}

MUTATOR_HOOKFUNCTION(status_effects, MakePlayerObserver)
{
	entity player = M_ARGV(0, entity);

	                                                                           
	StatusEffects_removeall(player, STATUSEFFECT_REMOVE_NORMAL);                                       
	StatusEffects_clearall(player.statuseffects_store);

	                                    
	if(player.statuseffects && player.statuseffects.owner == player)
		StatusEffects_delete(player);
}

MUTATOR_HOOKFUNCTION(status_effects, reset_map_global)
{
	FOREACH_CLIENT(IS_PLAYER(it) && it.statuseffects,
	{
		StatusEffects_removeall(it, STATUSEFFECT_REMOVE_NORMAL);                                       
		StatusEffects_clearall(it.statuseffects);
		StatusEffects_update(it);
	});
	return false;
}

MUTATOR_HOOKFUNCTION(status_effects, SpectateCopy)
{
	entity spectatee = M_ARGV(0, entity);
	entity client = M_ARGV(1, entity);

	client.statuseffects = spectatee.statuseffects;
}

MUTATOR_HOOKFUNCTION(status_effects, PutClientInServer)
{
	entity player = M_ARGV(0, entity);

	if(player.statuseffects && player.statuseffects.owner == player)
	{
		StatusEffects_clearall(player.statuseffects);
		StatusEffects_update(player);
	}
	else
	{
		StatusEffects_clearall(player.statuseffects_store);
		player.statuseffects = NULL;
	}
}
