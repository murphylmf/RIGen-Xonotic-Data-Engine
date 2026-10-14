#include "tracing.qh"

#include <common/constants.qh>
#include <common/deathtypes/all.qh>
#include <common/effects/all.qh>
#include <common/net_linked.qh>
#include <common/state.qh>
#include <common/util.qh>
#include <common/weapons/_all.qh>
#include <common/wepent.qh>
#include <lib/warpzone/common.qh>
#include <server/antilag.qh>
#include <server/damage.qh>
#include <server/main.qh>
#include <server/mutators/_mod.qh>
#include <server/weapons/accuracy.qh>
#include <server/weapons/common.qh>
#include <server/weapons/hitplot.qh>
#include <server/weapons/weaponsystem.qh>

                                                                             
                                                                      
                                                
void W_SetupShot_Dir_ProjectileSize_Range(entity ent, .entity weaponentity, vector s_forward, vector mi, vector ma, float antilag, float recoil, Sound snd, float chan, float maxdamage, float range, int deathtype)
{
	TC(Sound, snd);
	float nudge = 1;                                                                                                                                        
	float oldsolid = ent.dphitcontentsmask;
	Weapon wep = DEATH_WEAPONOF(deathtype);
	if(!IS_CLIENT(ent))
		antilag = false;                               
	if (IS_PLAYER(ent) && (wep.spawnflags & WEP_FLAG_PENETRATEWALLS))
	{
		                                                                                                                  
		                                                                                                                    
		                                                                                                                 
		                                                                            
		                                                                       
		                                                                                            
		                                                                               
		ent.dphitcontentsmask = DPCONTENTS_BODY | DPCONTENTS_CORPSE;
	}
	else
		ent.dphitcontentsmask = DPCONTENTS_SOLID | DPCONTENTS_BODY | DPCONTENTS_CORPSE;
	if(antilag)
		WarpZone_traceline_antilag(NULL, ent.origin + ent.view_ofs, ent.origin + ent.view_ofs + s_forward * range, MOVE_NORMAL, ent, ANTILAG_LATENCY(ent));
		                                                                     
	else
		WarpZone_TraceLine(ent.origin + ent.view_ofs, ent.origin + ent.view_ofs + s_forward * range, MOVE_NOMONSTERS, ent);
	ent.dphitcontentsmask = DPCONTENTS_SOLID | DPCONTENTS_BODY | DPCONTENTS_CORPSE;

	vector forward, right, up;
	forward = v_forward;
	right = v_right;
	up = v_up;
	w_shotend = WarpZone_UnTransformOrigin(WarpZone_trace_transform, trace_endpos);                    
	v_forward = forward;
	v_right = right;
	v_up = up;

	                                            
	if(vdist(w_shotend - (ent.origin + ent.view_ofs), <, autocvar_g_trueaim_minrange))
		w_shotend = ent.origin + ent.view_ofs + s_forward * autocvar_g_trueaim_minrange;

	                   
	if (IS_PLAYER(ent) && accuracy_canbegooddamage(ent))
		accuracy_add(ent, wep, maxdamage, 0);

	if(IS_PLAYER(ent))
		W_HitPlotAnalysis(ent, wep, forward, right, up);

	vector md = ent.(weaponentity).movedir;
	vector vecs = ((md.x > 0) ? md : '0 0 0');

	vector dv = right * -vecs.y + up * vecs.z;
	w_shotorg = ent.origin + ent.view_ofs;
	if(antilag)
	{
		if(CS(ent).antilag_debug)
			tracebox_antilag(ent, w_shotorg, mi, ma, w_shotorg + dv, MOVE_NORMAL, ent, CS(ent).antilag_debug);
		else
			tracebox_antilag(ent, w_shotorg, mi, ma, w_shotorg + dv, MOVE_NORMAL, ent, ANTILAG_LATENCY(ent));
	}
	else
		tracebox(w_shotorg, mi, ma, w_shotorg + dv, MOVE_NORMAL, ent);
	w_shotorg = trace_endpos;

	                                                                
	if(antilag)
	{
		if(CS(ent).antilag_debug)
			tracebox_antilag(ent, w_shotorg, mi, ma, w_shotorg + forward * (vecs.x + nudge), MOVE_NORMAL, ent, CS(ent).antilag_debug);
		else
			tracebox_antilag(ent, w_shotorg, mi, ma, w_shotorg + forward * (vecs.x + nudge), MOVE_NORMAL, ent, ANTILAG_LATENCY(ent));
	}
	else
		tracebox(w_shotorg, mi, ma, w_shotorg + forward * (vecs.x + nudge), MOVE_NORMAL, ent);
	w_shotorg = trace_endpos - forward * nudge;
	                                                
	if(W_DualWielding(ent))
		w_shotdir = s_forward;
	else
		w_shotdir = normalize(w_shotend - w_shotorg);

	                             
	                             
	                             

	if (antilag)
	if (!CS_CVAR(ent).cvar_cl_noantilag)
	{
		if (autocvar_g_antilag == 1)                                             
		{
			traceline(w_shotorg, w_shotorg + w_shotdir * range, MOVE_NORMAL, ent);
			if (!trace_ent.takedamage)
			{
				traceline_antilag_force (ent, w_shotorg, w_shotorg + w_shotdir * range, MOVE_NORMAL, ent, ANTILAG_LATENCY(ent));
				if (trace_ent.takedamage && IS_PLAYER(trace_ent))
				{
					entity e;
					e = trace_ent;
					traceline(w_shotorg, e.origin, MOVE_NORMAL, ent);
					if(trace_ent == e)
						w_shotdir = normalize(trace_ent.origin - w_shotorg);
				}
			}
		}
		else if(autocvar_g_antilag == 3)                       
		{
			                                   
			if (CS(ent).cursor_trace_ent)                                                
			if (CS(ent).cursor_trace_ent != ent)                             
			if (CS(ent).cursor_trace_ent.takedamage)                                    
			if (IS_PLAYER(CS(ent).cursor_trace_ent))                         
			{
				                                                  
				                                                                  
				traceline(w_shotorg, w_shotorg + w_shotdir * range, MOVE_NORMAL, ent);
				if (!trace_ent.takedamage)
				{
					                                            
					traceline(w_shotorg, CS(ent).cursor_trace_ent.origin, MOVE_NORMAL, ent);
					if (trace_ent == CS(ent).cursor_trace_ent)
						w_shotdir = normalize(CS(ent).cursor_trace_ent.origin - w_shotorg);
					else
						LOG_INFO("antilag fail");
				}
			}
		}
	}

	ent.dphitcontentsmask = oldsolid;                                                 

	if (!autocvar_g_norecoil)
		ent.punchangle_x = recoil * -1;

	if (snd != SND_Null) {
		sound(ent, chan, snd, (W_DualWielding(ent) ? VOL_BASE * 0.7 : VOL_BASE), ATTN_NORM);
		W_PlayStrengthSound(ent);
	}

	                                               
	w_shotend = w_shotend + normalize(w_shotend - w_shotorg) * nudge;
	                                                                                                            
	                                                                                                            
	                                                                                                            
}

vector W_CalculateProjectileVelocity(entity actor, vector pvelocity, vector mvelocity, float forceAbsolute)
{
	vector mdirection;
	float mspeed;
	vector outvelocity;

	mvelocity = mvelocity * W_WeaponSpeedFactor(actor);

	mdirection = normalize(mvelocity);
	mspeed = vlen(mvelocity);

	outvelocity = get_shotvelocity(pvelocity, mdirection, mspeed, (forceAbsolute ? 0 : autocvar_g_projectiles_newton_style), autocvar_g_projectiles_newton_style_2_minfactor, autocvar_g_projectiles_newton_style_2_maxfactor);

	return outvelocity;
}

void W_SetupProjVelocity_Explicit(entity proj, vector dir, vector upDir, float pSpeed, float pUpSpeed, float pZSpeed, float spread, float forceAbsolute)
{
	if(proj.owner == NULL)
		error("Unowned missile");

	dir = dir + upDir * (pUpSpeed / pSpeed);
	dir.z += pZSpeed / pSpeed;
	pSpeed *= vlen(dir);
	dir = normalize(dir);

	#if 0
	if(autocvar_g_projectiles_spread_style != mspercallsstyle)
	{
		mspercallsum = mspercallcount = 0;
		mspercallsstyle = autocvar_g_projectiles_spread_style;
	}
	mspercallsum -= gettime(GETTIME_HIRES);
	#endif

	dir = W_CalculateSpread(dir, spread, autocvar_g_weaponspreadfactor, autocvar_g_projectiles_spread_style);

	#if 0
	mspercallsum += gettime(GETTIME_HIRES);
	mspercallcount += 1;
	LOG_INFO("avg: ", ftos(mspercallcount / mspercallsum), " per sec");
	#endif

	proj.velocity = W_CalculateProjectileVelocity(proj.owner, proj.owner.velocity, pSpeed * dir, forceAbsolute);
}


                       
                      
                       

bool Headshot(entity targ, entity ent, vector start, vector end)
{
	if(!IS_PLAYER(targ) || IS_DEAD(targ) || STAT(FROZEN, targ) || !targ.takedamage)
		return false;
	vector org = targ.origin;                                                                                                                      
	vector headmins = org + '0.6 0 0' * targ.mins_x + '0 0.6 0' * targ.mins_y + '0 0 1' * (1.3 * targ.view_ofs_z - 0.3 * targ.maxs_z);
	vector headmaxs = org + '0.6 0 0' * targ.maxs_x + '0 0.6 0' * targ.maxs_y + '0 0 1' * targ.maxs_z;

	return trace_hits_box(start, end, headmins, headmaxs);
}

void FireRailgunBullet (entity this, .entity weaponentity, vector start, vector end, float bdamage, bool headshot_notify, float bforce, float mindist, float maxdist, float halflifedist, float forcehalflifedist, int deathtype)
{
	vector dir = normalize(end - start);
	vector force = dir * bforce;

	                                                                       
	end = end + dir;

	float totaldmg = 0;
	bool headshot = false;                                                        

	                                                                       
	                                                                          
	                                                                
	entity o = this;
	while (1)
	{
		if(CS(this).antilag_debug)
			WarpZone_traceline_antilag (this, start, end, false, o, CS(this).antilag_debug);
		else
			WarpZone_traceline_antilag (this, start, end, false, o, ANTILAG_LATENCY(this));
		if(o && WarpZone_trace_firstzone)
		{
			o = NULL;
			continue;
		}

		if(trace_ent.solid == SOLID_BSP || trace_ent.solid == SOLID_SLIDEBOX)
			Damage_DamageInfo(trace_endpos, bdamage, 0, 0, force, deathtype, trace_ent.species, this);

		                                             
		if (trace_ent == NULL || trace_fraction == 1)
			break;

		if(headshot_notify && !headshot && Headshot(trace_ent, this, start, end))
			headshot = true;

		                                                       
		IL_PUSH(g_railgunhit, trace_ent);
		trace_ent.railgunhit = true;
		trace_ent.railgunhitloc = end;
		trace_ent.railgunhitsolidbackup = trace_ent.solid;
		trace_ent.railgundistance = vlen(WarpZone_UnTransformOrigin(WarpZone_trace_transform, trace_endpos) - start);
		trace_ent.railgunforce = WarpZone_TransformVelocity(WarpZone_trace_transform, force);

		                         
		if (trace_ent.solid == SOLID_BSP)
			break;

		                            
		trace_ent.solid = SOLID_NOT;
	}

	vector endpoint = trace_endpos;
	entity endent = trace_ent;
	float endq3surfaceflags = trace_dphitq3surfaceflags;

	                                                                      
	IL_EACH(g_railgunhit, it.railgunhit,
	{
		it.solid = it.railgunhitsolidbackup;
	});

	                                                             
	float length = vlen(endpoint - start);
	entity pseudoprojectile = NULL;
	FOREACH_CLIENT(IS_REAL_CLIENT(it) && it != this, {
		                                  
		if (IS_SPEC(it) && it.enemy == this) continue;

		                            
		vector beampos = start + dir * bound(0, (it.origin - start) * dir, length);

		if(!pseudoprojectile)
			pseudoprojectile = new(pseudoprojectile);                                                           

		msg_entity = it;
		                                                                                                             
		soundtoat(MSG_ONE, pseudoprojectile, beampos, CH_SHOTS, SND(NEXWHOOSH_RANDOM()), VOL_BASEVOICE, ATTEN_IDLE, 0);
	});
	if(pseudoprojectile)
		delete(pseudoprojectile);

	                                                      
	IL_EACH(g_railgunhit, it.railgunhit,
	{
		                                         

		float foff = ExponentialFalloff(mindist, maxdist, halflifedist, it.railgundistance);
		float ffs = ExponentialFalloff(mindist, maxdist, forcehalflifedist, it.railgundistance);

		if(accuracy_isgooddamage(this, it))
			totaldmg += bdamage * foff;

		                   
		if (it.takedamage)
			Damage(it, this, this, bdamage * foff, deathtype, weaponentity, it.railgunhitloc, it.railgunforce * ffs);

		it.railgunhitloc = '0 0 0';
		it.railgunhitsolidbackup = SOLID_NOT;
		it.railgunhit = false;
		it.railgundistance = 0;
	});

	IL_CLEAR(g_railgunhit);

	if(headshot)
		Send_Notification(NOTIF_ONE, this, MSG_ANNCE, ANNCE_HEADSHOT);

	                                             
	if(this.(weaponentity))
		accuracy_add(this, this.(weaponentity).m_weapon, 0, min(bdamage, totaldmg));

	trace_endpos = endpoint;
	trace_ent = endent;
	trace_dphitq3surfaceflags = endq3surfaceflags;
}

void fireBullet_trace_callback(vector start, vector hit, vector end)
{
	if(vdist(hit - start, >, 16))
		trailparticles(NULL, fireBullet_trace_callback_eff, start, hit);
	WarpZone_trace_forent = NULL;
	fireBullet_last_hit = NULL;
}

void fireBullet_antilag(entity this, .entity weaponentity, vector start, vector dir, float spread, float max_solid_penetration, float damage, float headshot_multiplier, float force, float dtype, entity tracer_effect, bool do_antilag)
{
	dir = normalize(dir + randomvec() * spread);
	vector end = start + dir * max_shot_distance;

	fireBullet_last_hit = NULL;
	fireBullet_trace_callback_eff = tracer_effect;

	float solid_penetration_fraction = 1;
	float damage_fraction = 1;
	float total_damage = 0;

	float lag = ((do_antilag) ? antilag_getlag(this) : 0);
	if(lag)
		antilag_takeback_all(this, lag);

	                                                           
	int oldsolid = this.dphitcontentsmask;
	if(this)
		this.dphitcontentsmask = DPCONTENTS_SOLID | DPCONTENTS_BODY | DPCONTENTS_CORPSE;

	WarpZone_trace_forent = this;

	bool headshot = false;                                                        
	for (;;)
	{
		WarpZone_TraceBox_ThroughZone(start, '0 0 0', '0 0 0', end, false, WarpZone_trace_forent, NULL, fireBullet_trace_callback);
		dir = WarpZone_TransformVelocity(WarpZone_trace_transform, dir);
		end = WarpZone_TransformOrigin(WarpZone_trace_transform, end);
		start = trace_endpos;
		entity hit = trace_ent;

		                                                                
		if (trace_fraction == 1.0)
			break;

		                          
		if (trace_dphitq3surfaceflags & Q3SURFACEFLAG_SKY)
			break;

		                                                       
		                                                         
			        

		                                 
		  
		                           
		  
		                                                                     
		                                              
		  
		                                                                       
		  
		                    
		                               
		                                                                           
		bool is_weapclip = false;
		if(trace_dphitq3surfaceflags & Q3SURFACEFLAG_NODRAW)
		if (!(trace_dphitq3surfaceflags & Q3SURFACEFLAG_NONSOLID))
		if (!(trace_dphitcontents & DPCONTENTS_OPAQUE))
			is_weapclip = true;

		if(!hit || hit.solid == SOLID_BSP || hit.solid == SOLID_SLIDEBOX)
			Damage_DamageInfo(start, damage * damage_fraction, 0, 0, max(1, force) * dir * damage_fraction, dtype, hit.species, this);

		if (hit && hit != WarpZone_trace_forent && hit != fireBullet_last_hit)                                                                                                             
		{
			fireBullet_last_hit = hit;
			yoda = 0;
			MUTATOR_CALLHOOK(FireBullet_Hit, this, hit, start, end, damage, this.(weaponentity));
			damage = M_ARGV(4, float);
			if(headshot_multiplier && Headshot(hit, this, start, end))
			{
				damage *= headshot_multiplier;
				headshot = true;
			}
			bool gooddamage = accuracy_isgooddamage(this, hit);
			Damage(hit, this, this, damage * damage_fraction, dtype, weaponentity, start, force * dir * damage_fraction);
			                                       
			if(gooddamage)
			{
				                     
				float added_damage = min(damage - total_damage, damage * damage_fraction);
				total_damage += damage * damage_fraction;
				accuracy_add(this, this.(weaponentity).m_weapon, 0, added_damage);
			}
		}

		if (is_weapclip && !autocvar_g_ballistics_penetrate_clips)
			break;

		                    
		                               
		if(start.x > world.maxs.x || start.y > world.maxs.y || start.z > world.maxs.z || start.x < world.mins.x || start.y < world.mins.y || start.z < world.mins.z)
			break;

		float maxdist;
		entity hitstore = IS_PLAYER(hit) ? PS(hit) : hit;
		if(max_solid_penetration < 0)
			break;
		else if(hitstore.ballistics_density < -1)
			break;                                  
		else if(hitstore.ballistics_density < 0)
			maxdist = vlen(hit.maxs - hit.mins) + 1;                                
		else if(hitstore.ballistics_density == 0)
			maxdist = max_solid_penetration * solid_penetration_fraction;
		else
			maxdist = max_solid_penetration * solid_penetration_fraction / hitstore.ballistics_density;

		if(maxdist <= autocvar_g_ballistics_mindistance)
			break;

		                                                                                 
		                                             
		traceline_inverted (start, start + dir * maxdist, MOVE_NORMAL, WarpZone_trace_forent, true, hit);
		if(trace_fraction == 1)                                
			break;

		float dist_taken = max(autocvar_g_ballistics_mindistance, vlen(trace_endpos - start));
		float fraction_used_of_what_is_left = dist_taken / maxdist;
		solid_penetration_fraction -= solid_penetration_fraction * fraction_used_of_what_is_left;
		solid_penetration_fraction = max(solid_penetration_fraction, 0);
		damage_fraction = pow(solid_penetration_fraction, autocvar_g_ballistics_solidpenetration_exponent);

		                                                                     
		if (hit && (hit.solid != SOLID_BSP))
			if(vdist(trace_endpos - start, >, 4))
				trailparticles(this, fireBullet_trace_callback_eff, start, trace_endpos);

		start = trace_endpos;

		if(hit.solid == SOLID_BSP)
			Damage_DamageInfo(start, 0, 0, 0, max(1, force) * normalize(dir) * -damage_fraction, dtype, 0, this);
	}

	if(headshot)
		Send_Notification(NOTIF_ONE, this, MSG_ANNCE, ANNCE_HEADSHOT);

	if(lag)
		antilag_restore_all(this);

	                             
	if(this)
		this.dphitcontentsmask = oldsolid;
}

void fireBullet(entity this, .entity weaponentity, vector start, vector dir, float spread, float max_solid_penetration, float damage, float headshot_multiplier, float force, float dtype, entity tracer_effect)
{
	fireBullet_antilag(this, weaponentity, start, dir, spread, max_solid_penetration, damage, headshot_multiplier, force, dtype, tracer_effect, true);
}

void crosshair_trace(entity pl)
{
	traceline_antilag(pl, CS(pl).cursor_trace_start, CS(pl).cursor_trace_start + normalize(CS(pl).cursor_trace_endpos - CS(pl).cursor_trace_start) * max_shot_distance, MOVE_NORMAL, pl, ANTILAG_LATENCY(pl));
}

void crosshair_trace_plusvisibletriggers(entity pl)
{
	crosshair_trace_plusvisibletriggers__is_wz(pl, false);
}

void WarpZone_crosshair_trace_plusvisibletriggers(entity pl)
{
	crosshair_trace_plusvisibletriggers__is_wz(pl, true);
}

void crosshair_trace_plusvisibletriggers__is_wz(entity pl, bool is_wz)
{
	FOREACH_ENTITY_FLOAT(solid, SOLID_TRIGGER,
	{
		if(it.model != "")
		{
			it.solid = SOLID_BSP;
			IL_PUSH(g_ctrace_changed, it);
		}
	});

	if (is_wz)
		WarpZone_crosshair_trace(pl);
	else
		crosshair_trace(pl);

	IL_EACH(g_ctrace_changed, true, { it.solid = SOLID_TRIGGER; });

	IL_CLEAR(g_ctrace_changed);
}

void WarpZone_crosshair_trace(entity pl)
{
	WarpZone_traceline_antilag(pl, CS(pl).cursor_trace_start, CS(pl).cursor_trace_start + normalize(CS(pl).cursor_trace_endpos - CS(pl).cursor_trace_start) * max_shot_distance, MOVE_NORMAL, pl, ANTILAG_LATENCY(pl));
}
