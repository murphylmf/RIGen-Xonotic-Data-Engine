#include "gibs.qh"

REGISTER_NET_TEMP(net_gibsplash)

#ifdef SVQC

.int state;

bool Violence_GibSplash_SendEntity(entity this, entity to, int sf)
{
	int channel = MSG_ONE;
	msg_entity = to;
	WriteHeader(channel, net_gibsplash);
	WriteByte(channel, this.state);                 
	WriteByte(channel, bound(1, this.cnt * 16, 255));                             
	WriteShort(channel, floor(this.origin.x / 4));                                                            
	WriteShort(channel, floor(this.origin.y / 4));                                                            
	WriteShort(channel, floor(this.origin.z / 4));                                                            
	WriteShort(channel, this.oldorigin.x);                                
	return true;
}

void Violence_GibSplash_At(vector org, vector dir, float type, float amount, entity gibowner, entity attacker)
{
	if(g_cts)                  
		return;

	entity e = new_pure(gibsplash);
	e.cnt = amount;
	e.state = type;                               
	if(!sound_allowed(MSG_BROADCAST, gibowner) || !sound_allowed(MSG_BROADCAST, attacker))
		e.state |= 0x40;                 
	e.state |= 8 * gibowner.species;                                 

	                                                                    
	                                                     
	if(gibowner.classname == "body")
		e.team = etof(gibowner.enemy);
	else
		e.team = etof(gibowner);

	                                 
	                    
	e.origin = org;
	e.velocity = dir;

	e.oldorigin_x = compressShortVector(e.velocity);

	FOREACH_CLIENT(IS_REAL_CLIENT(it), Violence_GibSplash_SendEntity(e, it, 0));
	delete(e);
}

void Violence_GibSplash(entity source, float type, float amount, entity attacker)
{
	Violence_GibSplash_At(source.origin + source.view_ofs, source.velocity, type, amount, source, attacker);
}
#endif

#ifdef CSQC

.vector colormod;
.bool silent;

#include "rubble.qh"
#include <common/physics/movetypes/movetypes.qh>

.float scale;
.float alpha;
.float cnt;
.float gravity;

void Gib_Delete(entity this)
{
	delete(this);
}

string species_prefix(int specnum);

void Gib_setmodel(entity gib, string mdlname, int specnum)
{
	switch(specnum)
	{
		case SPECIES_ROBOT_RUSTY:
		case SPECIES_ROBOT_SHINY:
		case SPECIES_ROBOT_SOLID:
			if(specnum != SPECIES_ROBOT_SOLID || mdlname == "models/gibs/chunk.mdl")
			{
				if(mdlname == "models/gibs/bloodyskull.md3")
					setmodel(gib, MDL_GIB_ROBO);
				else
					setmodel(gib, MDL_GIB_ROBO_RANDOM());
				if(specnum == SPECIES_ROBOT_SHINY)
				{
					gib.skin = 1;
					gib.colormod = '2 2 2';
				}
				gib.scale = 1;
				break;
			}
		default:
			_setmodel(gib, mdlname);
			gib.skin = specnum;
			break;
	}
}

void new_te_bloodshower (int ef, vector org, float explosionspeed, int howmany)
{
	float i, pmod;
	pmod = autocvar_cl_particles_quality;
	for (i = 0; i < 50 * pmod; ++i)
		__pointparticles(ef, org, randomvec() * explosionspeed, howmany / 50);
}

void SUB_RemoveOnNoImpact(entity this, entity toucher)
{
	if(trace_dphitq3surfaceflags & Q3SURFACEFLAG_NOIMPACT)
		Gib_Delete(this);
}

void Gib_Touch(entity this, entity toucher)
{
	                                                   

	if(trace_dphitq3surfaceflags & Q3SURFACEFLAG_NOIMPACT)
	{
		Gib_Delete(this);
		return;
	}

	if(!this.silent)
		sound(this, CH_PAIN, SND_GIB_SPLAT_RANDOM(), VOL_BASE, ATTEN_NORM);
	__pointparticles(_particleeffectnum(strcat(species_prefix(this.cnt), "blood")), this.origin + '0 0 1', '0 0 30', 10);

	Gib_Delete(this);
}

void Gib_Draw(entity this)
{
	vector oldorg;
	oldorg = this.origin;

	Movetype_Physics_MatchTicrate(this, autocvar_cl_gibs_ticrate, autocvar_cl_gibs_sloppy);
	if(wasfreed(this))
		return;

	if(gettouch(this) == Gib_Touch)                                            
		                                                                     
		__trailparticles(this, _particleeffectnum(strcat(species_prefix(this.cnt), EFFECT_TR_SLIGHTBLOOD.eent_eff_name)), oldorg, this.origin);
	else
		__trailparticles(this, _particleeffectnum(strcat(species_prefix(this.cnt), EFFECT_TR_BLOOD.eent_eff_name)), oldorg, this.origin);

	this.renderflags = 0;

	                                           
	                                                                 
	this.nextthink -= frametime * (1 / bound(0.01, view_quality, 1.00) - 1);

	this.alpha = bound(0, this.nextthink - time, 1);

	if(this.alpha < ALPHA_MIN_VISIBLE)
	{
		this.drawmask = 0;
		Gib_Delete(this);
	}
}

void TossGib (string mdlname, vector safeorg, vector org, vector vconst, vector vrand, int specnum, bool destroyontouch, bool issilent)
{
	entity gib;

	                                               
	gib = ListNewChildRubble(CasingsNGibs, new(gib));
	set_movetype(gib, MOVETYPE_BOUNCE);
	gib.gravity = 1;
	gib.solid = SOLID_CORPSE;
	gib.cnt = specnum;
	gib.silent = issilent;
	gib.colormap = 4;       
	gib.colormap |= BIT(10);                      
	Gib_setmodel(gib, mdlname, specnum);

	setsize (gib, '-8 -8 -8', '8 8 8');

	gib.draw = Gib_Draw;
	IL_PUSH(g_drawables, gib);
	if(destroyontouch)
		settouch(gib, Gib_Touch);
	else
		settouch(gib, SUB_RemoveOnNoImpact);

	                                             
	if(org != safeorg)
	{
		tracebox(safeorg, gib.mins, gib.maxs, org, MOVE_NOMONSTERS, gib);
		org = trace_endpos;
	}

	setorigin(gib, org);
	gib.velocity = vconst * autocvar_cl_gibs_velocity_scale + vrand * autocvar_cl_gibs_velocity_random + '0 0 1' * autocvar_cl_gibs_velocity_up;
	gib.avelocity = prandomvec() * vlen(gib.velocity) * autocvar_cl_gibs_avelocity_scale;
	gib.move_time = time;
	gib.damageforcescale = autocvar_cl_gibs_damageforcescale;

	gib.nextthink = time + autocvar_cl_gibs_lifetime * (1 + prandom() * 0.15);
	gib.drawmask = MASK_NORMAL;

	LimitedChildrenRubble(CasingsNGibs, "gib", autocvar_cl_gibs_maxcount, Gib_Delete, NULL);
}

NET_HANDLE(net_gibsplash, bool isNew)
{
	Net_Accept(net_gibsplash);

	string gentle_prefix = "morphed_";

	int type = ReadByte();                
	int amount = ReadByte() / 16.0;                  
	vector org;
	org.x = ReadShort() * 4 + 2;
	org.y = ReadShort() * 4 + 2;
	org.z = ReadShort() * 4 + 2;
	vector vel = decompressShortVector(ReadShort());

	return = true;

	float cl_gentle_gibs = autocvar_cl_gentle_gibs;
	if(cl_gentle_gibs || autocvar_cl_gentle)
		type |= 0x80;                  

	if(type & 0x80)
	{
		if(cl_gentle_gibs == 2)
			gentle_prefix = "";
		else if(cl_gentle_gibs == 3)
			gentle_prefix = "happy_";
	}
	else if(autocvar_cl_particlegibs)
	{
		type |= 0x80;
		gentle_prefix = "particlegibs_";
	}

	if (!(cl_gentle_gibs || autocvar_cl_gentle))
		amount *= 1 - autocvar_cl_nogibs;

	if(autocvar_ekg)
		amount *= 5;

	if(amount <= 0 || !isNew)
		return;

	setorigin(this, org);                  

	int specnum = (type & 0x78) / 8;                                                                  
	bool issilent = (type & 0x40);
	type = type & 0x87;                                                                    
	string specstr = species_prefix(specnum);

	switch(type)
	{
		case 0x01:
			if(!issilent)
				sound (this, CH_PAIN, SND_GIB, VOL_BASE, ATTEN_NORM);

			if(prandom() < amount)
				TossGib ("models/gibs/eye.md3", org, org, vel, prandomvec() * 150, specnum, 0, issilent);
			new_te_bloodshower(_particleeffectnum(strcat(specstr, "bloodshower")), org, 1200, amount);
			if(prandom() < amount)
				TossGib ("models/gibs/bloodyskull.md3", org, org + 16 * prandomvec(), vel, prandomvec() * 100, specnum, 0, issilent);

			for(int c = 0; c < amount; ++c)
			{
				int randomvalue = amount - c;

				if(prandom() < randomvalue)
					TossGib ("models/gibs/arm.md3", org, org + 16 * prandomvec() + '0 0 8', vel, prandomvec() * (prandom() * 120 + 90), specnum,0, issilent);
				if(prandom() < randomvalue)
					TossGib ("models/gibs/arm.md3", org, org + 16 * prandomvec() + '0 0 8', vel, prandomvec() * (prandom() * 120 + 90), specnum,0, issilent);
				if(prandom() < randomvalue)
					TossGib ("models/gibs/chest.md3", org, org + 16 * prandomvec(), vel, prandomvec() * (prandom() * 120 + 80), specnum,0, issilent);
				if(prandom() < randomvalue)
					TossGib ("models/gibs/smallchest.md3", org, org + 16 * prandomvec(), vel, prandomvec() * (prandom() * 120 + 80), specnum,0, issilent);
				if(prandom() < randomvalue)
					TossGib ("models/gibs/leg1.md3", org, org + 16 * prandomvec() + '0 0 -5', vel, prandomvec() * (prandom() * 120 + 85), specnum,0, issilent);
				if(prandom() < randomvalue)
					TossGib ("models/gibs/leg2.md3", org, org + 16 * prandomvec() + '0 0 -5', vel, prandomvec() * (prandom() * 120 + 85), specnum,0, issilent);

				                        
				if(prandom() < randomvalue)
					TossGib ("models/gibs/chunk.mdl", org, org + 16 * prandomvec(), vel, prandomvec() * 450, specnum,1, issilent);
				if(prandom() < randomvalue)
					TossGib ("models/gibs/chunk.mdl", org, org + 16 * prandomvec(), vel, prandomvec() * 450, specnum,1, issilent);
				if(prandom() < randomvalue)
					TossGib ("models/gibs/chunk.mdl", org, org + 16 * prandomvec(), vel, prandomvec() * 450, specnum,1, issilent);
				if(prandom() < randomvalue)
					TossGib ("models/gibs/chunk.mdl", org, org + 16 * prandomvec(), vel, prandomvec() * 450, specnum,1, issilent);
			}
			break;
		case 0x02:
			__pointparticles(_particleeffectnum(strcat(specstr, "blood")), org, vel, amount * 16);
			break;
		case 0x03:
			if(prandom() < amount)
				TossGib ("models/gibs/chunk.mdl", org, org, vel, prandomvec() * (prandom() * 30 + 20), specnum, 1, issilent);                                            
			break;
		case 0x81:
			__pointparticles(_particleeffectnum(strcat(gentle_prefix, "damage_dissolve")), org, vel, amount);
			break;
		case 0x82:
			__pointparticles(_particleeffectnum(strcat(gentle_prefix, "damage_hit")), org, vel, amount * 16);
			break;
		case 0x83:
			                                
			break;
	}
	delete(this);
}
#endif
