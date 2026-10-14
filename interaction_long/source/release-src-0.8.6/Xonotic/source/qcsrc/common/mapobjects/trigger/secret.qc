#include "secret.qh"
#if defined(CSQC)
#elif defined(MENUQC)
#elif defined(SVQC)
    #include <common/util.qh>
    #include <common/weapons/_all.qh>
    #include <common/stats.qh>
#endif

#ifdef SVQC

   
                                     
   
void trigger_secret_touch(entity this, entity toucher)
{
	                                 
	if (!IS_PLAYER(toucher))
		return;

	EXACTTRIGGER_TOUCH(this, toucher);

	                               
	secrets_found += 1;

	                                              
	SUB_UseTargets(this, toucher, toucher);

	                                                                    
	                                                       
	settouch(this, func_null);
}

#if 0
void trigger_secret_reset(entity this)
{
	secrets_found = 0;
	settouch(this, trigger_secret_touch);
}
#endif

                                    
                                                                       
                                                                                                                    
                      
                                                                                                    
                                                             
                                                                
                                                                                                                 
                                                                   
                       
                                                                                              
                                                                                      
  
spawnfunc(trigger_secret)
{
	                                              

	                       
	secrets_total += 1;

	                      
	if (!this.message || this.message == "")
		this.message = "You found a secret!";

	                    
	if ((!this.noise || this.noise == "") && !this.sounds)
		this.sounds = 1;                   

	switch(this.sounds)
	{
		case 1: this.noise = "misc/secret.wav"; break;
		case 2: this.noise = strzone(SND(TALK)); break;
		case 3: this.noise = "misc/trigger1.wav"; break;
	}

	if(this.noise && this.noise != "")
		precache_sound(this.noise);

	                             
	this.delay = 0;

	EXACTTRIGGER_INIT;

	settouch(this, trigger_secret_touch);
                                                                                        
#if 0
	this.reset = trigger_secret_reset;
#endif
}
#endif
