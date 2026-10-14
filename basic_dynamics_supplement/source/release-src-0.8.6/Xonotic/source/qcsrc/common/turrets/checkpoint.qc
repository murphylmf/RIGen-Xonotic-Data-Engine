#include "checkpoint.qh"

#ifdef SVQC

                                                           
                           
                                              
                                      
                                
                        
                                                                                           
                                                                                                 
  
void turret_checkpoint_init(entity this)
{
    traceline(this.origin + '0 0 16', this.origin - '0 0 1024', MOVE_WORLDONLY, this);
    setorigin(this, trace_endpos + '0 0 32');

    if(this.target && this.target != "")
    {
        this.enemy = find(NULL, targetname, this.target);
        if(!this.enemy)
            LOG_TRACE("A turret_checkpoint failed to find its target!");
    }
}

spawnfunc(turret_checkpoint)
{
    setorigin(this, this.origin);
    InitializeEntity(this, turret_checkpoint_init, INITPRIO_FINDTARGET);
}

          
spawnfunc(walker_checkpoint)
{
    spawnfunc_turret_checkpoint(this);
}

#endif
