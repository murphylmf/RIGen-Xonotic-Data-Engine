#include "stunned.qh"

#ifdef SVQC
METHOD(Stunned, m_remove, void(StatusEffects this, entity actor, int removal_type))
{
    actor.effects &= ~EF_SHOCK;
    SUPER(Stunned).m_remove(this, actor, removal_type);
}
#if 0
                                                                     
METHOD(Stunned, m_persistent, bool(StatusEffects this, entity actor))
{
    return true;
}
#endif
METHOD(Stunned, m_tick, void(StatusEffects this, entity actor))
{
    if(STAT(FROZEN, actor))
    {
        this.m_remove(this, actor, STATUSEFFECT_REMOVE_NORMAL);
        return;
    }
                               
    actor.effects |= EF_SHOCK;
    SUPER(Stunned).m_tick(this, actor);
}
#endif
