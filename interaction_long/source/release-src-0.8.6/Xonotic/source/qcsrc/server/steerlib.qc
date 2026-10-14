#include "steerlib.qh"

#include <server/pathlib/utility.qh>

   
                                
   
#define steerlib_pull(ent,point) normalize(point - (ent).origin)
                                                 
 
                                          
   

   
                             
   
#define steerlib_push(ent,point) normalize((ent).origin - point)
  
                                               
 
                                          
 
  
   
                                                                 
   
vector steerlib_arrive(entity this, vector point, float maximal_distance)
{
    float distance = bound(0.001, vlen(this.origin - point), maximal_distance);
    vector direction = normalize(point - this.origin);
    return  direction * (distance / maximal_distance);
}

   
                                                             
   
vector steerlib_attract(entity this, vector point, float maximal_distance)
{
    float distance = bound(0.001, vlen(this.origin - point), maximal_distance);
    vector direction = normalize(point - this.origin);

    return  direction * (1 - (distance / maximal_distance));
}

vector steerlib_attract2(entity this, vector point, float min_influense, float max_distance, float max_influense)
{
    float distance = bound(0.00001, vlen(this.origin - point), max_distance);
    vector direction = normalize(point - this.origin);

    float influense = 1 - (distance / max_distance);
    influense = min_influense + (influense * (max_influense - min_influense));

    return direction * influense;
}

  
                                                                                                                     
 
                     
                             
                            
                             

                 
                                             

                                                      

                                                      
                                                 

                                                                                    
                             

                                                                                       

             
                       
                          
                        
                            

                                                                                       
 
  
   
                           
   
vector steerlib_repel(entity this, vector point, float maximal_distance)
{
    float distance = bound(0.001, vlen(this.origin - point), maximal_distance);
    vector direction = normalize(this.origin - point);

    return  direction * (1 - (distance / maximal_distance));
}

   
                                                 
   
vector steerlib_standoff(entity this, vector point, float ideal_distance)
{
    vector direction;
    float distance = vlen(this.origin - point);

    if(distance < ideal_distance)
    {
        direction = normalize(this.origin - point);
        return direction * (distance / ideal_distance);
    }

    direction = normalize(point - this.origin);
    return direction * (ideal_distance / distance);

}

   
                                            

          
                                                       

                                                                                                    
                                           
   
vector steerlib_wander(entity this, float range, float threshold, vector oldpoint)
{
    vector wander_point = v_forward - oldpoint;

    if (vdist(wander_point, >, threshold))
        return oldpoint;

    range = bound(0, range, 1);

    wander_point = this.origin + v_forward * 128;
    wander_point = wander_point + randomvec() * (range * 128) - randomvec() * (range * 128);

    return normalize(wander_point - this.origin);
}

   
                                         
   
vector steerlib_dodge(entity this, vector point, vector dodge_dir, float min_distance)
{
    float distance = max(vlen(this.origin - point), min_distance);
    if (min_distance < distance)
        return '0 0 0';

    return dodge_dir * (min_distance / distance);
}

   
                         
                                                                                   
   
.float flock_id;
vector steerlib_flock(entity this, float _radius, float standoff, float separation_force, float flock_force)
{
    vector push = '0 0 0', pull = '0 0 0';
    int ccount = 0;

    entity flock_member = findradius(this.origin, _radius);
    while(flock_member)
    {
        if(flock_member != this)
        if(flock_member.flock_id == this.flock_id)
        {
            ++ccount;
            push = push + (steerlib_repel(this, flock_member.origin,standoff) * separation_force);
            pull = pull + (steerlib_arrive(this, flock_member.origin + flock_member.velocity, _radius) * flock_force);
        }
        flock_member = flock_member.chain;
    }
    return push + (pull* (1 / ccount));
}

   
                         
                                                                                   
                                        
   
vector steerlib_flock2d(entity this, float _radius, float standoff, float separation_force, float flock_force)
{
    vector push = '0 0 0', pull = '0 0 0';
    int ccount = 0;

    entity flock_member = findradius(this.origin,_radius);
    while(flock_member)
    {
        if(flock_member != this)
        if(flock_member.flock_id == this.flock_id)
        {
            ++ccount;
            push = push + (steerlib_repel(this, flock_member.origin, standoff) * separation_force);
            pull = pull + (steerlib_arrive(this, flock_member.origin + flock_member.velocity, _radius) * flock_force);
        }
        flock_member = flock_member.chain;
    }

    push.z = 0;
    pull.z = 0;

    return push + (pull * (1 / ccount));
}

   
                                                                       
                                                               

                                                               
   
vector steerlib_swarm(entity this, float _radius, float standoff, float separation_force, float swarm_force)
{
    vector force = '0 0 0', center = '0 0 0';
    int ccount = 0;

    entity swarm_member = findradius(this.origin,_radius);
    while(swarm_member)
    {
        if(swarm_member.flock_id == this.flock_id)
        {
            ++ccount;
            center = center + swarm_member.origin;
            force = force + (steerlib_repel(this, swarm_member.origin,standoff) * separation_force);
        }
        swarm_member = swarm_member.chain;
    }

    center = center * (1 / ccount);
    force = force + (steerlib_arrive(this, center,_radius) * swarm_force);

    return force;
}

   
                                                 
                                                                                                     
                                                                                                    
   
vector steerlib_traceavoid(entity this, float pitch, float length)
{
    vector v_left = v_right * -1;
    vector v_down = v_up * -1;

    vector vup_left = (v_forward + (v_left * pitch + v_up * pitch)) * length;
    traceline(this.origin, this.origin +  vup_left, MOVE_NOMONSTERS, this);
    float fup_left = trace_fraction;

                                                    

    vector vup_right = (v_forward + (v_right * pitch + v_up * pitch)) * length;
    traceline(this.origin, this.origin + vup_right, MOVE_NOMONSTERS, this);
    float fup_right = trace_fraction;

                                                    

    vector vdown_left = (v_forward + (v_left * pitch + v_down * pitch)) * length;
    traceline(this.origin, this.origin + vdown_left, MOVE_NOMONSTERS, this);
    float fdown_left = trace_fraction;

                                                    

    vector vdown_right = (v_forward + (v_right * pitch + v_down * pitch)) * length;
    traceline(this.origin, this.origin + vdown_right, MOVE_NOMONSTERS, this);
    float fdown_right = trace_fraction;

                                                    
    vector upwish    = v_up    * (fup_left   + fup_right);
    vector downwish  = v_down  * (fdown_left + fdown_right);
    vector leftwish  = v_left  * (fup_left   + fdown_left);
    vector rightwish = v_right * (fup_right  + fdown_right);

    return (upwish + leftwish + downwish + rightwish) * 0.25;

}

   
                                                 
                                                                                                  
                                                                                                    
   
vector steerlib_traceavoid_flat(entity this, float pitch, float length, vector vofs)
{
    vector v_left = v_right * -1;

    vector vt_front = v_forward * length;
    traceline(this.origin + vofs, this.origin + vofs + vt_front,MOVE_NOMONSTERS,this);
    float f_front = trace_fraction;

    vector vt_left = (v_forward + (v_left * pitch)) * length;
    traceline(this.origin + vofs, this.origin + vofs + vt_left,MOVE_NOMONSTERS,this);
    float f_left = trace_fraction;

                                                    

    vector vt_right = (v_forward + (v_right * pitch)) * length;
    traceline(this.origin + vofs, this.origin + vofs + vt_right ,MOVE_NOMONSTERS,this);
    float f_right = trace_fraction;

                                                    

    vector leftwish  = v_left    * f_left;
    vector rightwish = v_right   * f_right;
    vector frontwish = v_forward * f_front;

    return normalize(leftwish + rightwish + frontwish);
}

                          
float beamsweep(entity this, vector from, vector dir, float length, float step, float step_up, float step_down)
{
    vector u = '0 0 1' * step_up;
    vector d = '0 0 1' * step_down;

    traceline(from + u, from - d,MOVE_NORMAL,this);
    if(trace_fraction == 1.0)
        return 0;

    if(!location_isok(trace_endpos, false, false))
        return 0;

    vector a = trace_endpos;
    for(int i = 0; i < length; i += step)
    {

        vector b = a + dir * step;
        tracebox(a + u,'-4 -4 -4','4 4 4', b + u,MOVE_NORMAL,this);
        if(trace_fraction != 1.0)
            return i / length;

        traceline(b + u, b - d,MOVE_NORMAL,this);
        if(trace_fraction == 1.0)
            return i / length;

        if(!location_isok(trace_endpos, false, false))
            return i / length;
#ifdef BEAMSTEER_VISUAL
        te_lightning1(NULL,a+u,b+u);
        te_lightning1(NULL,b+u,b-d);
#endif
        a = trace_endpos;
    }

    return 1;
}

vector steerlib_beamsteer(entity this, vector dir, float length, float step, float step_up, float step_down)
{
    dir.z *= 0.15;
    vector vr = vectoangles(dir);
                 

    tracebox(this.origin + '0 0 1' * step_up, this.mins, this.maxs, ('0 0 1' * step_up) + this.origin +  (dir * length), MOVE_NOMONSTERS, this);
    if(trace_fraction == 1.0)
    {
                                                                       
        return dir;
    }

    makevectors(vr);
    float bm_forward = beamsweep(this, this.origin, v_forward, length, step, step_up, step_down);

    vr = normalize(v_forward + v_right * 0.125);
    vector vl = normalize(v_forward - v_right * 0.125);

    float bm_right = beamsweep(this, this.origin, vr, length, step, step_up, step_down);
    float bm_left  = beamsweep(this, this.origin, vl, length, step, step_up, step_down);

    float p = bm_left + bm_right;
    if(p == 2)
    {
                                                                                          
                                                                                                   

        return v_forward;
    }

    p = 2 - p;

    vr = normalize(v_forward + v_right * p);
    vl = normalize(v_forward - v_right * p);
    bm_right = beamsweep(this, this.origin, vr, length, step, step_up, step_down);
    bm_left  = beamsweep(this, this.origin, vl, length, step, step_up, step_down);


    if(bm_left + bm_right < 0.15)
    {
        vr = normalize((v_forward*-1) + v_right * 0.90);
        vl = normalize((v_forward*-1) - v_right * 0.90);

        bm_right = beamsweep(this, this.origin, vr, length, step, step_up, step_down);
        bm_left  = beamsweep(this, this.origin, vl, length, step, step_up, step_down);
    }

                                                                                      
                                                                                               

    bm_forward *= bm_forward;
    bm_right   *= bm_right;
    bm_left    *= bm_left;

    vr = vr * bm_right;
    vl = vl * bm_left;

    return normalize(vr + vl);
}
