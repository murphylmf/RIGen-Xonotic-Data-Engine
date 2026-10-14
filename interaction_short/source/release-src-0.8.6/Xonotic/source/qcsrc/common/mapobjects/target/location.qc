#include "location.qh"
#ifdef SVQC
void target_push_init(entity this);

spawnfunc(target_location)
{
                               
                                                                    

    target_push_init(this);

    IL_PUSH(g_locations, this);
}

spawnfunc(info_location)
{
    this.message = this.netname;
    spawnfunc_target_location(this);
}
#endif
