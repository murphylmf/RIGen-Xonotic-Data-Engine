#include "items.qh"

#include <client/main.qh>
#include <common/items/_mod.qh>
#include <common/physics/movetypes/movetypes.qh>
#include <common/weapons/_all.qh>
#include <lib/csqcmodel/cl_model.qh>
#include <lib/csqcmodel/common.qh>
#include <lib/warpzone/common.qh>

.vector item_glowmod;
.int item_simple;
.float alpha;
.bool pushable;
.float anim_start_time;                                            
.vector angles_held;                                           
.float wait, delay, pointtime;                               

HashMap ENT_CLIENT_ITEM_simple;
STATIC_INIT(ENT_CLIENT_ITEM_simple)
{
	HM_NEW(ENT_CLIENT_ITEM_simple);
}
SHUTDOWN(ENT_CLIENT_ITEM_simple)
{
	HM_DELETE(ENT_CLIENT_ITEM_simple);
}

void ItemSetModel(entity this, bool wantsimple)
{
	if(wantsimple)
	{
		string _fn2 = substring(this.mdl, 0 , strlen(this.mdl) -4);
		#define extensions(x) \
		x(iqm) \
		x(dpm) \
		x(md3) \
		x(mdl) \
		    
		#define tryext(ext) { \
			string s = strcat(_fn2, autocvar_cl_simpleitems_postfix, "." #ext); \
			string cached = HM_gets(ENT_CLIENT_ITEM_simple, s); \
			if (cached == "") { \
				HM_sets(ENT_CLIENT_ITEM_simple, s, cached = fexists(s) ? "1" : "0"); \
			} \
			if (cached != "0") { \
				this.model = s; \
				this.item_simple = 1; \
				break; \
			} \
		}
		do {
			extensions(tryext);
			this.model = this.mdl;                         
			this.item_simple = -1;                           
			LOG_TRACEF("Simple item requested for %s but no model exists for it", this.mdl);
		} while (0);
		#undef tryext
		#undef extensions
	}
	else
	{
		this.model = this.mdl;
		this.item_simple = 0;
	}

	                                                                                     
	if(this.model == "")
		LOG_WARNF("this.model is unset for item %s", this.classname);
	precache_model(this.model);
	_setmodel(this, this.model);
	setsize(this, '-16 -16 0', '16 16 48');
	                                                                           
}

void ItemDraw(entity this)
{
	bool wantsimple = autocvar_cl_simple_items && this.ItemStatus & ITS_ALLOWSI;
	if(wantsimple != this.item_simple && this.item_simple != -1)
		ItemSetModel(this, wantsimple);

	                                                                                                             
	bool animate = autocvar_cl_items_animate & 1 && this.item_simple <= 0 && (this.ItemStatus & ITS_ANIMATE1 || this.ItemStatus & ITS_ANIMATE2);

	                                              
	if(!animate)
	{
		this.avelocity_y = 0;
		this.angles = this.angles_held;                                   
	}
	else if(!this.avelocity_y)                                                               
	{
		if(this.ItemStatus & ITS_ANIMATE1)
			this.avelocity_y = 180;
		else if(this.ItemStatus & ITS_ANIMATE2)
			this.avelocity_y = -90;
	}

	                                                  
	float bobheight = 0;                                               
	if(this.move_movetype && (!IS_ONGROUND(this) || this.velocity != '0 0 0'))
	{
		                                                                                                      
		                                                                                                             
		if(animate)
			bobheight = this.origin_z - this.oldorigin_z;
		Movetype_Physics_NoMatchTicrate(this, frametime, true);
		this.oldorigin = this.origin;                                        
		if(animate)
		{
			if(bobheight)
			{
				this.anim_start_time += frametime;                                
				this.oldorigin_z -= bobheight;                                                          
			}
			else
			{
				this.anim_start_time = time;                                       
				if(this.ItemStatus & ITS_ANIMATE1)
					bobheight = 10;                            
				else if(this.ItemStatus & ITS_ANIMATE2)
					bobheight = 8;                            
			}
		}
	}
	else if(animate)
	{
		this.angles += this.avelocity * frametime;                                             

		if(this.ItemStatus & ITS_ANIMATE1)
			bobheight = 10 + 8 * sin((time - this.anim_start_time) * 2);
		else if(this.ItemStatus & ITS_ANIMATE2)
			bobheight = 8 + 4 * sin((time - this.anim_start_time) * 3);
	}

	                       
	if (bobheight != this.origin_z - this.oldorigin_z)
	{
		this.origin_z = this.oldorigin_z + bobheight;
		this.mins_z = 0 - bobheight;                                           
		this.maxs_z = 48 - bobheight;
		                                                                           
	}

	                              
	this.alpha = 1;
	this.drawmask = 0;
	if(this.fade_end && !warpzone_warpzones_exist)
	{
		vector org = getpropertyvec(VF_ORIGIN);
		if(vdist(org - this.origin, >, this.fade_end))
			this.alpha = 0;                           
		else if(autocvar_cl_items_fadedist > 0)
		{
			this.fade_start = max(500, this.fade_end - autocvar_cl_items_fadedist);
			if(vdist(org - this.origin, >, this.fade_start))
				this.alpha = bound(0, (this.fade_end - vlen(org - this.origin - 0.5 * (this.mins + this.maxs))) / (this.fade_end - this.fade_start), 1);
		}
	}

	if(!this.alpha)
		return;

	                                                     
	if(this.ItemStatus & ITS_AVAILABLE)
	{
		if(hud)                                                
		{
			this.alpha *= autocvar_cl_items_vehicle_alpha;
			this.colormod = this.glowmod = autocvar_cl_items_vehicle_color;
		}
		else if(this.ItemStatus & ITS_STAYWEP)
		{
			this.alpha *= autocvar_cl_weapon_stay_alpha;
			this.colormod = this.glowmod = autocvar_cl_weapon_stay_color;
		}
		else
		{
			this.colormod = '1 1 1';
			this.glowmod = this.item_glowmod;
		}
	}
	else
	{
		this.alpha *= autocvar_cl_ghost_items;
		this.colormod = this.glowmod = autocvar_cl_ghost_items_color;
	}

	if(!this.alpha)
		return;

	                            
	if(this.ItemStatus & ITS_EXPIRING)
	{
		if(!this.wait)                                                          
		{
			this.wait = time + IT_DESPAWNFX_TIME;                        
			this.delay = 0.25;
		}

		if(autocvar_cl_items_animate & 2)
			this.alpha *= (this.wait - time) / IT_DESPAWNFX_TIME;

		if(autocvar_cl_items_animate & 4 && time >= this.pointtime)
		{
			pointparticles(EFFECT_ITEM_DESPAWN, this.origin + '0 0 16', '0 0 0', 1);
			if (this.delay > 0.0625)
				this.delay *= 0.5;
			this.pointtime = time + this.delay;
		}
	}

	this.drawmask = this.alpha <= 0 ? 0 : MASK_NORMAL;
}

void ItemRemove(entity this)
{
	if(this.alpha)
	if(!this.wait || time < this.wait - ticrate)                                                
		pointparticles(EFFECT_ITEM_PICKUP, (this.absmin + this.absmax) * 0.5, '0 0 0', 1);
	strfree(this.mdl);
}

NET_HANDLE(ENT_CLIENT_ITEM, bool isnew)
{
	int sf = ReadByte();

	if(sf & ISF_LOCATION)
	{
		float bobheight = this.origin_z - this.oldorigin_z;
		this.origin = this.oldorigin = ReadVector();
		this.origin_z += bobheight;                                                                          
		setorigin(this, this.origin);        
	}

	if(sf & ISF_ANGLES)
	{
		this.angles = this.angles_held = ReadAngleVector();
	}

	                                                                           
                  
  
                                         
  
   

	if(sf & ISF_STATUS)                                                                       
	{
		int prevItemStatus = this.ItemStatus;
		this.ItemStatus = ReadByte();

		if(this.ItemStatus & ITS_ALLOWFB)
			this.effects |= EF_FULLBRIGHT;
		else
			this.effects &= ~EF_FULLBRIGHT;

		if(this.ItemStatus & ITS_AVAILABLE)
		{
			if(this.solid != SOLID_TRIGGER)
			{
				this.solid = SOLID_TRIGGER;
				setorigin(this, this.origin);                            
			}

			if(this.ItemStatus & ITS_GLOW)
				this.effects |= (EF_ADDITIVE | EF_FULLBRIGHT);
			if(!(prevItemStatus & ITS_AVAILABLE) && this.alpha && !isnew)
				pointparticles(EFFECT_ITEM_RESPAWN, (this.absmin + this.absmax) * 0.5, '0 0 0', 1);
		}
		else
		{
			if(this.solid != SOLID_NOT)
			{
				this.solid = SOLID_NOT;
				setorigin(this, this.origin);                                              
			}

			if(this.ItemStatus & ITS_GLOW)
				this.effects &= ~(EF_ADDITIVE | EF_FULLBRIGHT);
			if(prevItemStatus & ITS_AVAILABLE && this.alpha)
				pointparticles(EFFECT_ITEM_PICKUP, (this.absmin + this.absmax) * 0.5, '0 0 0', 1);
		}
	}

	if(sf & ISF_MODEL)
	{
		if(isnew)
		{
			IL_PUSH(g_drawables, this);
			this.draw = ItemDraw;
			this.flags |= FL_ITEM;
		}

		this.fade_end = ReadShort();

		strcpy(this.mdl, ReadString());
		this.item_simple = -2;

		this.skin = ReadByte();
	}

	if(sf & ISF_COLORMAP)
	{
		this.colormap = ReadShort();
		this.item_glowmod_x = ReadByte() / 255.0;
		this.item_glowmod_y = ReadByte() / 255.0;
		this.item_glowmod_z = ReadByte() / 255.0;
	}

	if(sf & ISF_DROP)
	{
		this.gravity = 1;
		this.pushable = true;
		set_movetype(this, MOVETYPE_TOSS);
		this.velocity = ReadVector();
	}
	else if (this.gravity)                                                      
	{
		                                                                                    
		this.gravity = 0;                              
		this.pushable = false;                  
		set_movetype(this, MOVETYPE_NONE);                   
		this.velocity = '0 0 0';                   
		SET_ONGROUND(this);                  
	}

	this.entremove = ItemRemove;

	return true;
}
