#include "aim.qh"

#include <common/physics/player.qh>
#include <common/state.qh>
#include <common/stats.qh>
#include <common/weapons/_all.qh>
#include <server/bot/default/bot.qh>
#include <server/bot/default/cvars.qh>
#include <server/mutators/_mod.qh>
#include <server/weapons/weaponsystem.qh>

                                                                       
                                         
                                                                     

float findtrajectorywithleading(vector org, vector m1, vector m2, entity targ, float shotspeed, float shotspeedupward, float maxtime, float shotdelay, entity ignore)
{
	float c, savesolid, shottime;
	vector dir, end, v, o;
	if (shotspeed < 1)
		return false;                                              
	if (targ.solid < SOLID_BBOX)                               
		return false;                      
	if (!tracetossent)
		tracetossent = new(tracetossent);
	tracetossent.owner = ignore;
	setsize(tracetossent, m1, m2);
	savesolid = targ.solid;
	targ.solid = SOLID_NOT;
	o = (targ.absmin + targ.absmax) * 0.5;
	shottime = ((vlen(o - org) / shotspeed) + shotdelay);
	v = targ.velocity * shottime + o;
	tracebox(o, targ.mins, targ.maxs, v, false, targ);
	v = trace_endpos;
	end = v + (targ.mins + targ.maxs) * 0.5;
	if ((vlen(end - org) / shotspeed + 0.2) > maxtime)
	{
		               
		targ.solid = savesolid;
		return false;
	}

	if (!tracetossfaketarget)
		tracetossfaketarget = new(tracetossfaketarget);
	tracetossfaketarget.solid = savesolid;
	set_movetype(tracetossfaketarget, targ.move_movetype);
	_setmodel(tracetossfaketarget, targ.model);                    
	tracetossfaketarget.model = targ.model;
	tracetossfaketarget.modelindex = targ.modelindex;
	setsize(tracetossfaketarget, targ.mins, targ.maxs);
	setorigin(tracetossfaketarget, v);

	c = 0;
	dir = normalize(end - org);
	while (c < 10)             
	{
		setorigin(tracetossent, org);         
		tracetossent.velocity = findtrajectory_velocity = normalize(dir) * shotspeed + shotspeedupward * '0 0 1';
		tracetoss(tracetossent, ignore);                             
		if (trace_ent == tracetossfaketarget)        
		{
			targ.solid = savesolid;

			                    
			tracetossfaketarget.solid = SOLID_NOT;
			set_movetype(tracetossfaketarget, MOVETYPE_NONE);
			tracetossfaketarget.model = "";
			tracetossfaketarget.modelindex = 0;
			                                                  
			setorigin(tracetossfaketarget, v);

			return true;
		}
		dir.z = dir.z + 0.1;                        
		c = c + 1;
	}
	targ.solid = savesolid;

	                    
	tracetossfaketarget.solid = SOLID_NOT;
	set_movetype(tracetossfaketarget, MOVETYPE_NONE);
	tracetossfaketarget.model = "";
	tracetossfaketarget.modelindex = 0;
	                                                  
	setorigin(tracetossfaketarget, v);

	                                           
	findtrajectory_velocity = normalize(end - org) * shotspeed + shotspeedupward * '0 0 1';
	return false;
}

bool bot_shouldattack(entity this, entity targ)
{
	if (targ.team == this.team)
	{
		if (targ == this)
			return false;
		if (teamplay)
		if (targ.team != 0)
			return false;
	}

	if(STAT(FROZEN, targ))
		return false;

	if(teamplay)
	{
		if(targ.team==0)
			return false;
	}
	else if (autocvar_bot_ignore_bots && IS_BOT_CLIENT(targ))
		return false;

	if (!targ.takedamage)
		return false;
	if (IS_DEAD(targ))
		return false;
	if (PHYS_INPUT_BUTTON_CHAT(targ) && !autocvar_bot_typefrag)
		return false;
	if(targ.flags & FL_NOTARGET)
		return false;
	if(targ.alpha <= 0.1 && targ.alpha != 0)
		return false;                       

	if(MUTATOR_CALLHOOK(BotShouldAttack, this, targ))
		return false;

	return true;
}

                                                                                  
void bot_aim_reset(entity this)
{
	this.bot_mouseaim = this.v_angle;
	this.bot_olddesiredang = this.v_angle;
	this.bot_aimdir_executed = true;
	this.bot_badaimtime = 0;
	this.bot_aimthinktime = time;
	this.bot_prevaimtime = time;
	this.bot_1st_order_aimfilter = '0 0 0';
	this.bot_2nd_order_aimfilter = '0 0 0';
	this.bot_3th_order_aimfilter = '0 0 0';
	this.bot_4th_order_aimfilter = '0 0 0';
	this.bot_5th_order_aimfilter = '0 0 0';
	this.bot_firetimer = 0;
}

void bot_aimdir(entity this, vector v, float maxfiredeviation)
{
	float dist, delta_t, blend;
	vector desiredang, diffang;

	this.bot_aimdir_executed = true;

	                                                             
	                                  
	this.v_angle_y = this.v_angle.y - floor(this.v_angle.y / 360) * 360;
	this.v_angle_z = 0;

	                                                              
	if (this.bot_prevaimtime == time)
		return;

	                                                                             
	if (SUPERBOT)
	{
		this.v_angle = vectoangles(normalize(v));

		this.v_angle.x *= -1;

		makevectors(this.v_angle);
		shotorg = this.origin + this.view_ofs;
		shotdir = v_forward;

		                                 
		this.bot_firetimer = time + 0.001;
		return;
	}

	                                                        
	if(!v) return;

	float skill_save = skill;
	                                                          
	if (!this.enemy)
		skill = max(4, skill);

	                                   
	                          
	                   
	                                                                                          
	if (time >= this.bot_badaimtime)
	{
		this.bot_badaimtime = max(this.bot_badaimtime + 0.2 + 0.3 * random(), time);
		int f = bound(0, 1 - 0.1 * (skill + this.bot_offsetskill), 1);
		this.bot_badaimoffset = randomvec() * f * autocvar_bot_ai_aimskill_offset;
		this.bot_badaimoffset.x *= 0.7;                           
	}
	float enemy_factor = ((this.enemy) ? 5 : 2);
	                                                                                                                  
	desiredang = vectoangles(v) + this.bot_badaimoffset * enemy_factor;
	                                        
	if (desiredang.x >= 180)
		desiredang.x = desiredang.x - 360;
	desiredang.x = bound(-90, 0 - desiredang.x, 90);
	desiredang.z = this.v_angle.z;
	                                  

	                        
	                             
	   
	                     
	                                                                        
	   

	                        
	diffang = (desiredang - this.bot_olddesiredang);
	                
	diffang.y = diffang.y - floor(diffang.y / 360) * 360;
	if (diffang.y >= 180)
		diffang.y = diffang.y - 360;
	this.bot_olddesiredang = desiredang;
	                                  

	delta_t = time-this.bot_prevaimtime;
	this.bot_prevaimtime = time;
	                                                              
	this.bot_1st_order_aimfilter= this.bot_1st_order_aimfilter
		+ (diffang * (1 / delta_t)    - this.bot_1st_order_aimfilter) * bound(0, autocvar_bot_ai_aimskill_order_filter_1st,1);
	this.bot_2nd_order_aimfilter= this.bot_2nd_order_aimfilter
		+ (this.bot_1st_order_aimfilter - this.bot_2nd_order_aimfilter) * bound(0, autocvar_bot_ai_aimskill_order_filter_2nd,1);
	this.bot_3th_order_aimfilter= this.bot_3th_order_aimfilter
		+ (this.bot_2nd_order_aimfilter - this.bot_3th_order_aimfilter) * bound(0, autocvar_bot_ai_aimskill_order_filter_3th,1);
	this.bot_4th_order_aimfilter= this.bot_4th_order_aimfilter
		+ (this.bot_3th_order_aimfilter - this.bot_4th_order_aimfilter) * bound(0, autocvar_bot_ai_aimskill_order_filter_4th,1);
	this.bot_5th_order_aimfilter= this.bot_5th_order_aimfilter
		+ (this.bot_4th_order_aimfilter - this.bot_5th_order_aimfilter) * bound(0, autocvar_bot_ai_aimskill_order_filter_5th,1);

	                                                                                                                   
	blend = bound(0,skill+this.bot_aimskill,10)*0.1;
	desiredang = desiredang + blend *
	(
		  this.bot_1st_order_aimfilter * autocvar_bot_ai_aimskill_order_mix_1st
		+ this.bot_2nd_order_aimfilter * autocvar_bot_ai_aimskill_order_mix_2nd
		+ this.bot_3th_order_aimfilter * autocvar_bot_ai_aimskill_order_mix_3th
		+ this.bot_4th_order_aimfilter * autocvar_bot_ai_aimskill_order_mix_4th
		+ this.bot_5th_order_aimfilter * autocvar_bot_ai_aimskill_order_mix_5th
	);
	desiredang.x = bound(-90, desiredang.x, 90);

	                        
	diffang = desiredang - this.bot_mouseaim;
	                
	diffang.y = diffang.y - floor(diffang.y / 360) * 360;
	if (diffang.y >= 180)
		diffang.y = diffang.y - 360;
	                                  

	if (time >= this.bot_aimthinktime)
	{
		this.bot_aimthinktime = max(this.bot_aimthinktime + 0.5 - 0.05*(skill+this.bot_thinkskill), time);
		this.bot_mouseaim = this.bot_mouseaim + diffang * (1-random()*0.1*bound(1,10-(skill+this.bot_thinkskill),10));
	}

	                                                                                         

	diffang = this.bot_mouseaim - desiredang;
	                
	diffang.y = diffang.y - floor(diffang.y / 360) * 360;
	if (diffang.y >= 180)
		diffang.y = diffang.y - 360;
	desiredang = desiredang + diffang * bound(0,autocvar_bot_ai_aimskill_think,1);

	                        
	diffang = desiredang - this.v_angle;
	                
	diffang.y = diffang.y - floor(diffang.y / 360) * 360;
	if (diffang.y >= 180)
		diffang.y = diffang.y - 360;
	                                  

	                  
	dist = vlen(diffang);
	                                                                               

	       
	float r, fixedrate, blendrate;
	fixedrate = autocvar_bot_ai_aimskill_fixedrate / bound(1,dist,1000);
	blendrate = autocvar_bot_ai_aimskill_blendrate;
	r = max(fixedrate, blendrate);
	                                                                                                                             
	r = bound(delta_t, r * delta_t * (2 + ((skill + this.bot_mouseskill) ** 3) * 0.005 - random()), 1);
	this.v_angle += diffang * (r + (1 - r) * bound(0, 1 - autocvar_bot_ai_aimskill_mouse, 1));
	this.v_angle_z = 0;
	this.v_angle_y = this.v_angle.y - floor(this.v_angle.y / 360) * 360;
	                                       

	skill = skill_save;

	if (maxfiredeviation <= 0)
		return;

	if (!autocvar_bot_ai_aimskill_firetolerance)
	{
		this.bot_firetimer = time + 0.2;
		return;
	}

	makevectors(this.v_angle);
	shotorg = this.origin + this.view_ofs;
	shotdir = v_forward;

	                                   
	                                                                
	                                                                                     
	                                                                                     
	vector deviation = vectoangles(v) - vectoangles(shotdir);
	while (deviation.x < -180) deviation.x += 360; while (deviation.x > 180) deviation.x -= 360;
	while (deviation.y < -180) deviation.y += 360; while (deviation.y > 180) deviation.y -= 360;
	if (fabs(deviation.x) < maxfiredeviation && fabs(deviation.y) < maxfiredeviation)
	{
		traceline(shotorg, shotorg + shotdir * 1000, false, NULL);
		if (vdist(trace_endpos - shotorg, <, 500 + 500 * bound(0, skill + this.bot_aggresskill, 10))
			|| random() * random() > bound(0, (skill + this.bot_aggresskill) * 0.05, 1))
		{
			this.bot_firetimer = time + bound(0.1, 0.5 - (skill + this.bot_aggresskill) * 0.05, 0.5);
		}
	}
}

vector bot_shotlead(vector targorigin, vector targvelocity, float shotspeed, float shotdelay)
{
	                                                                                                            
	return targorigin + targvelocity * (shotdelay + vlen(targorigin - shotorg) / shotspeed);
}

bool bot_aim(entity this, .entity weaponentity, float shotspeed, float shotspeedupward, float maxshottime, bool applygravity, bool shot_accurate)
{
	float hf, distanceratio;
	vector v;
	hf = this.dphitcontentsmask;
	this.dphitcontentsmask = DPCONTENTS_SOLID | DPCONTENTS_BODY | DPCONTENTS_CORPSE;

	float speed_factor = W_WeaponSpeedFactor(this);
	shotspeed *= speed_factor;
	shotspeedupward *= speed_factor;
	if (!shotspeed)
	{
		LOG_TRACE("bot_aim: WARNING: weapon ", this.(weaponentity).m_weapon.m_name, " shotspeed is zero!");
		shotspeed = 1000000;
	}
	if (!maxshottime)
	{
		LOG_TRACE("bot_aim: WARNING: weapon ", this.(weaponentity).m_weapon.m_name, " maxshottime is zero!");
		maxshottime = 1;
	}
	makevectors(this.v_angle);
	shotorg = this.origin + this.view_ofs;
	shotdir = v_forward;
	vector enemy_org = (this.enemy.absmin + this.enemy.absmax) * 0.5;
	v = bot_shotlead(enemy_org, this.enemy.velocity, shotspeed, this.bot_aimlatency);

	                                                                                      
	                                                                                       
	                                                         
	                                                         
	float dist = max(10, vlen(v - shotorg));
	float maxfiredeviation = 1000 / (dist - 9) - 0.35;

	float f = (shot_accurate) ? 1 : 1.6;
	f += bound(0, (10 - (skill + this.bot_aimskill)) * 0.3, 3);
	maxfiredeviation = min(90, maxfiredeviation * f);

	if (applygravity && this.enemy)
	{
		if (!findtrajectorywithleading(shotorg, '0 0 0', '0 0 0', this.enemy, shotspeed, shotspeedupward, maxshottime, 0, this))
		{
			this.dphitcontentsmask = hf;
			return false;
		}

		bot_aimdir(this, findtrajectory_velocity - shotspeedupward * '0 0 1', maxfiredeviation);
	}
	else
	{
		bot_aimdir(this, v - shotorg, maxfiredeviation);
		                                                                                                                                                                                                                                                                                                                                     
		                                                             
		                           
		                         
		                                         
		                
		traceline(shotorg, enemy_org, false, this);
		if (trace_fraction < 1)
		if (trace_ent != this.enemy)
		if (!bot_shouldattack(this, trace_ent))
		{
			this.dphitcontentsmask = hf;
			return false;
		}
	}

	if (time > this.bot_firetimer)
	{
		this.dphitcontentsmask = hf;
		return false;
	}

	                                  
	                
	this.dphitcontentsmask = hf;
	return true;
}
