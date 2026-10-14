#include "movelib.qh"

#ifdef SVQC
.vector moveto;

   
                 
                                                            
   
vector movelib_dragvec(entity this, float drag, float exp_)
{
    float lspeed,ldrag;

    lspeed = vlen(this.velocity);
    ldrag = lspeed * drag;
    ldrag = ldrag * (drag * exp_);
    ldrag = 1 - (ldrag / lspeed);

    return this.velocity * ldrag;
}

   
                 
                                                         
   
float movelib_dragflt(float fspeed,float drag,float exp_)
{
    float ldrag;

    ldrag = fspeed * drag;
    ldrag = ldrag * ldrag * exp_;
    ldrag = 1 - (ldrag / fspeed);

    return ldrag;
}

   
                                              
                                                                             
                                                                                 
   
vector movelib_inertmove_byspeed(entity this, vector vel_new, float vel_max,float newmin,float oldmax)
{
    float influense;

    influense = vlen(this.velocity) * (1 / vel_max);

    influense = bound(newmin,influense,oldmax);

    return (vel_new * (1 - influense)) + (this.velocity * influense);
}

vector movelib_inertmove(entity this, vector new_vel,float new_bias)
{
    return new_vel * new_bias + this.velocity * (1-new_bias);
}

void movelib_move(entity this, vector force,float max_velocity,float drag,float theMass,float breakforce)
{
    float deltatime;
    float acceleration;
    float mspeed;
    vector breakvec;

    deltatime = time - this.movelib_lastupdate;
    if (deltatime > 0.15) deltatime = 0;
    this.movelib_lastupdate = time;
    if (!deltatime) return;

    mspeed = vlen(this.velocity);

    if (theMass)
        acceleration = vlen(force) / theMass;
    else
        acceleration = vlen(force);

    if (IS_ONGROUND(this))
    {
        if (breakforce)
        {
            breakvec = (normalize(this.velocity) * (breakforce / theMass) * deltatime);
            this.velocity = this.velocity - breakvec;
        }

        this.velocity = this.velocity + force * (acceleration * deltatime);
    }

    if (drag)
        this.velocity = movelib_dragvec(this, drag, 1);

    if (this.waterlevel > 1)
    {
        this.velocity = this.velocity + force * (acceleration * deltatime);
        this.velocity = this.velocity + '0 0 0.05' * autocvar_sv_gravity * deltatime;
    }
    else
        this.velocity = this.velocity + '0 0 -1' * autocvar_sv_gravity * deltatime;

    mspeed = vlen(this.velocity);

    if (max_velocity)
        if (mspeed > max_velocity)
            this.velocity = normalize(this.velocity) * (mspeed - 50);                 
}

  
            
                     
                       
                    
                      
                
                        

                                     
 
                                                       

                                
                              

                                   
 

                                                        
 
                        
                    
                        

                    
                   
                    
               

                          
               
                          
                                       
                                            

                                                                     
                                              
                                                        
                             

                           
     
                                        
                                                
     
        
                             
                                             
            
                                          

                              
                                                                      
                                                      
                          

 
  

void movelib_brake_simple(entity this, float force)
{
    float mspeed;
    vector mdir;
    float vz;

    mspeed = max(0,vlen(this.velocity) - force);
    mdir   = normalize(this.velocity);
    vz = this.velocity.z;
    this.velocity = mdir * mspeed;
    this.velocity_z = vz;
}

   
                                                
                                                                                          
   
#endif

void movelib_groundalign4point(entity this, float spring_length, float spring_up, float blendrate, float _max)
{
    vector a, b, c, d, e, r, push_angle, ahead, side;

    push_angle.y = 0;
    r = (this.absmax + this.absmin) * 0.5 + (v_up * spring_up);
    e = v_up * spring_length;

                                       
    ahead = v_forward * (this.maxs.x * 0.8);
    side  = v_right   * (this.maxs.y * 0.8);

    a = r + ahead + side;
    b = r + ahead - side;
    c = r - ahead + side;
    d = r - ahead - side;

    traceline(a, a - e,MOVE_NORMAL,this);
    a.z =  (1 - trace_fraction);
    r = trace_endpos;

    traceline(b, b - e,MOVE_NORMAL,this);
    b.z =  (1 - trace_fraction);
    r += trace_endpos;

    traceline(c, c - e,MOVE_NORMAL,this);
    c.z =  (1 - trace_fraction);
    r += trace_endpos;

    traceline(d, d - e,MOVE_NORMAL,this);
    d.z =  (1 - trace_fraction);
    r += trace_endpos;

    a.x = r.z;
    r = this.origin;
    r.z = r.z;

    push_angle.x = (a.z - c.z) * _max;
    push_angle.x += (b.z - d.z) * _max;

    push_angle.z = (b.z - a.z) * _max;
    push_angle.z += (d.z - c.z) * _max;

                                           
                                           

    this.angles_x = ((1-blendrate) *  this.angles.x)  + (push_angle.x * blendrate);
    this.angles_z = ((1-blendrate) *  this.angles.z)  + (push_angle.z * blendrate);

                      
    setorigin(this, r);
}

