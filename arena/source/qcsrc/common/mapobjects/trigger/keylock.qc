#include "keylock.qh"
   
                        
   
void trigger_keylock_trigger(entity this, entity actor, string s)
{
	for(entity t = NULL; (t = find(t, targetname, s)); )
		if(t.use)
			t.use(t, actor, this);
}

   
                                      
   
void trigger_keylock_kill(string s)
{
	entity t;
	for(t = NULL; (t = find(t, targetname, s)); )
		delete(t);
}

void trigger_keylock_touch(entity this, entity toucher)
{
	bool key_used = false;
	bool started_delay = false;

	                                   
	if(!IS_PLAYER(toucher))
		return;

	                   
	if(this.itemkeys)
	{
#ifdef SVQC
		entity store = PS(toucher);
#elif defined(CSQC)
		entity store = toucher;
#endif
		key_used = item_keys_usekey(this, store);
	}

	if(this.itemkeys)
	{
#ifdef SVQC
		                                      
		if(key_used)
		{
			                                                             
			play2(toucher, this.noise1);
			Send_Notification(NOTIF_ONE, toucher, MSG_CENTER, CENTER_DOOR_LOCKED_ALSONEED, item_keys_keylist(this.itemkeys));
			toucher.key_door_messagetime = time + 2;
		}
		else if(toucher.key_door_messagetime <= time)
		{
			                     
			play2(toucher, this.noise2);
			Send_Notification(NOTIF_ONE, toucher, MSG_CENTER, CENTER_DOOR_LOCKED_NEED, item_keys_keylist(this.itemkeys));
			toucher.key_door_messagetime = time + 2;
		}
#endif

		                  
		if(this.delay <= time || started_delay == true)
		if(this.target2)
		{
			trigger_keylock_trigger(this, toucher, this.target2);
			started_delay = true;
			this.delay = time + this.wait;
		}
	}
	else
	{
#ifdef SVQC
		                       
		play2(toucher, this.noise);
		centerprint(toucher, this.message);
#endif

		if(this.target)
			trigger_keylock_trigger(this, toucher, this.target);

		if(this.killtarget)
			trigger_keylock_kill(this.killtarget);

		delete(this);
	}

}

REGISTER_NET_LINKED(ENT_CLIENT_KEYLOCK)

#ifdef SVQC
bool trigger_keylock_send(entity this, entity to, int sf)
{
	WriteHeader(MSG_ENTITY, ENT_CLIENT_KEYLOCK);

	WriteInt24_t(MSG_ENTITY, this.itemkeys);
	WriteByte(MSG_ENTITY, this.height);

	trigger_common_write(this, true);

	return true;
}

void trigger_keylock_link(entity this)
{
	                                
	                                                       
}

                                     
                                             
                                                                              
                      
                                                                     
                                                                                                      
                                                                                                                             
                                                                                                          
                                                                                             
                                                                                                         
                                                                                                                     
                                                                  
                                                                                                              
                                                                    
                                                                                                           
                        
                                                                                                       
                                                                                                    
  
spawnfunc(trigger_keylock)
{
	if(!this.itemkeys) { delete(this); return; }

	                       
	if(this.message == "")
		this.message = "Unlocked!";

	                           
	if(this.noise == "")
	{
		if(this.sounds == 1)
			this.noise = "misc/secret.wav";
		else if(this.sounds == 2)
			this.noise = strzone(SND(TALK));
		else                          
			this.noise = "misc/trigger1.wav";
	}

	                            
	if(this.noise1 == "")
		this.noise1 = "misc/decreasevalue.wav";

	                   
	if(this.noise2 == "")
		this.noise2 = SND(TALK);

	                                                 
	if(!this.wait) { this.wait = 5; }

	                  
	precache_sound(this.noise);
	precache_sound(this.noise1);
	precache_sound(this.noise2);

	EXACTTRIGGER_INIT;

	settouch(this, trigger_keylock_touch);

	trigger_keylock_link(this);
}
#elif defined(CSQC)
NET_HANDLE(ENT_CLIENT_KEYLOCK, bool isnew)
{
	this.itemkeys = ReadInt24_t();
	this.height = ReadByte();

	trigger_common_read(this, true);

	return = true;

	this.entremove = trigger_remove_generic;
}
#endif
