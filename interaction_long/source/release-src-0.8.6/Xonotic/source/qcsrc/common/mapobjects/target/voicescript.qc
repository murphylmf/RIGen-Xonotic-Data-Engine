#include "voicescript.qh"
#ifdef SVQC
.entity voicescript;                         
.float voicescript_index;                                                         
.float voicescript_nextthink;                           
.float voicescript_voiceend;                             

void target_voicescript_clear(entity pl)
{
	pl.voicescript = NULL;
}

void target_voicescript_use(entity this, entity actor, entity trigger)
{
	if(actor.voicescript != this)
	{
		actor.voicescript = this;
		actor.voicescript_index = 0;
		actor.voicescript_nextthink = time + this.delay;
	}
}

void target_voicescript_next(entity pl)
{
	entity vs;
	float i, n, dt;

	vs = pl.voicescript;
	if(!vs)
		return;
	if(vs.message == "")
		return;
	if (!IS_PLAYER(pl))
		return;
	if(game_stopped)
		return;

	if(time >= pl.voicescript_voiceend)
	{
		if(time >= pl.voicescript_nextthink)
		{
			                        
			n = tokenize_console(vs.message);

			if(pl.voicescript_index < vs.cnt)
				i = pl.voicescript_index * 2;
			else if(n > vs.cnt * 2)
				i = ((pl.voicescript_index - vs.cnt) % ((n - vs.cnt * 2 - 1) / 2)) * 2 + vs.cnt * 2 + 1;
			else
				i = -1;

			if(i >= 0)
			{
				play2(pl, strcat(vs.netname, "/", argv(i), ".wav"));
				dt = stof(argv(i + 1));
				if(dt >= 0)
				{
					pl.voicescript_voiceend = time + dt;
					pl.voicescript_nextthink = pl.voicescript_voiceend + vs.wait * (0.5 + random());
				}
				else
				{
					pl.voicescript_voiceend = time - dt;
					pl.voicescript_nextthink = pl.voicescript_voiceend;
				}

				pl.voicescript_index += 1;
			}
			else
			{
				pl.voicescript = NULL;                    
			}
		}
	}
}

spawnfunc(target_voicescript)
{
	                                        
	                                                                                      
	                                                                                 
	                                                                           
	                                    
	                                      
	                                                

	float i, n;
	this.use = target_voicescript_use;

	n = tokenize_console(this.message);
	this.cnt = n / 2;
	for(i = 0; i+1 < n; i += 2)
	{
		if(argv(i) == "*")
		{
			this.cnt = i / 2;
			++i;
		}
		precache_sound(strcat(this.netname, "/", argv(i), ".wav"));
	}
}
#endif
