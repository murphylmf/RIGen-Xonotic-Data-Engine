#include "keys.qh"

#ifdef CSQC
bool item_keys_usekey(entity l, entity p)
{
	int valid = (l.itemkeys & p.itemkeys);                                               
	l.itemkeys &= ~valid;                                           
	return valid != 0;
}
#endif

#ifdef SVQC
  
     
                                                                
                                   
                 
                                                                      
                             
  

bool item_keys_usekey(entity l, entity p)
{
	int valid = l.itemkeys & p.itemkeys;

	if (!valid) {
		                                     
		return false;
	} else if (l.itemkeys == valid) {
		                             
		l.itemkeys = 0;
		return true;
	} else {
		                                          
		l.itemkeys &= ~valid;
		return true;
	}
}

string item_keys_keylist(float keylist) {
	          
	if (!keylist)
		return "";

	          
	if ((keylist & (keylist-1)) == 0)
		return strcat("the ", item_keys_names[lowestbit(keylist)]);

	string n = "";
	int base = 0;
	while (keylist) {
		int l = lowestbit(keylist);
		if (n)
			n = strcat(n, ", the ", item_keys_names[base + l]);
		else
			n = strcat("the ", item_keys_names[base + l]);

		keylist = bitshift(keylist,  -(l + 1));
		base+= l + 1;
	}

	return n;
}


  
                                
        
                                
  

   
                     
   
void item_key_touch(entity this, entity toucher)
{
	if (!IS_PLAYER(toucher))
		return;

	                                    
	if (PS(toucher).itemkeys & this.itemkeys)
		return;

	PS(toucher).itemkeys |= this.itemkeys;
	play2(toucher, this.noise);

	centerprint(toucher, this.message);

	string oldmsg = this.message;
	this.message = "";
	SUB_UseTargets(this, toucher, toucher);                                                          
	this.message = oldmsg;
}

   
                                                    
   
void spawn_item_key(entity this)
{
	precache_model(this.model);

	if (this.spawnflags & 1)            
		this.noalign = 1;

	if (this.noalign)
		set_movetype(this, MOVETYPE_NONE);
	else
		set_movetype(this, MOVETYPE_TOSS);

	precache_sound(this.noise);

	this.mdl = this.model;
	this.effects = EF_LOWPRECISION;
	_setmodel(this, this.model);
	                                           
	setorigin(this, this.origin + '0 0 32');
	setsize(this, '-16 -16 -56', '16 16 0');
	this.modelflags |= MF_ROTATE;
	this.solid = SOLID_TRIGGER;

	if (!this.noalign)
	{
		                                                                 
		setorigin(this, this.origin + '0 0 1');
		                                                                
		droptofloor(this);
	}

	settouch(this, item_key_touch);
}


                                                             
             
                                                         
              
              
              
               
                 
                  
            
                       
                                                                                                                   
                           
                                                 
                   
                                                        
                               
                                     
                                                         
                            
                                                                                 
                        
                                                    

                                              
  
spawnfunc(item_key)
{
	string _netname;
	vector _colormod;

	                                                   
	if (this.itemkeys>0 && (this.itemkeys & (this.itemkeys-1)) != 0) {
		objerror(this, "item_key.itemkeys must contain only 1 bit set specifying the key it represents!");
		delete(this);
		return;
	}

	                                    
	switch(this.itemkeys) {
	case BIT(0):
		_netname = "GOLD key";
		_colormod = '1 .9 0';
		break;

	case BIT(1):
		_netname = "SILVER key";
		_colormod = '.9 .9 .9';
		break;

	case BIT(2):
		_netname = "BRONZE key";
		_colormod = '.6 .25 0';
		break;

	case BIT(3):
		_netname = "RED keycard";
		_colormod = '.9 0 0';
		break;

	case BIT(4):
		_netname = "BLUE keycard";
		_colormod = '0 0 .9';
		break;

	case BIT(5):
		_netname = "GREEN keycard";
		_colormod = '0 .9 0';
		break;

	default:
		_netname = "FLUFFY PINK keycard";
		_colormod = '1 1 1';

		if (this.netname == "") {
			objerror(this, "item_key doesn't have a default name for this key and a custom one was not specified!");
			delete(this);
			return;
		}
		break;

	}

	                     
	string _model = string_null;
	if (this.itemkeys <= ITEM_KEY_BIT(2)) {
		_model = "models/keys/key.md3";
	} else if (this.itemkeys >= ITEM_KEY_BIT(3) && this.itemkeys <= ITEM_KEY_BIT(5)) {
		_model = "models/keys/key.md3";                                         
	} else if (this.model == "") {
		objerror(this, "item_key doesn't have a default model for this key and a custom one was not specified!");
		delete(this);
		return;
	}

	                      
	if (this.netname == "")
		this.netname = _netname;

	                       
	if (!this.colormod)
		this.colormod = _colormod;

	                    
	if (this.model == "")
		this.model = _model;

	                             
	if (this.message == "")
		this.message = strzone(strcat("You've picked up the ", this.netname, "!"));

	if (this.noise == "")
		this.noise = strzone(SND(ITEMPICKUP));

	                          
	item_keys_names[lowestbit(this.itemkeys)] = this.netname;

	                         
	spawn_item_key(this);
}

                                                              
           
                           
                                                 
                                                        
                           
                                                         
                            
                                                                                 
                        
                                                        
  
spawnfunc(item_key1)
{
	this.itemkeys = ITEM_KEY_BIT(1);
	spawnfunc_item_key(this);
}

                                                              
         
                           
                                               
                                                        
                           
                                                         
                            
                                                                                 
                        
                                                        
  
spawnfunc(item_key2)
{
	this.itemkeys = ITEM_KEY_BIT(0);
	spawnfunc_item_key(this);
}

#endif
