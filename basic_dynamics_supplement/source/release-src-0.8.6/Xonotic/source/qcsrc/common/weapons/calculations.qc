#include "calculations.qh"

                                
                               
                                

float explosion_calcpush_getmultiplier(vector explosion_v, vector target_v)
{
	float a;
	a  = explosion_v * (explosion_v - target_v);

	if(a <= 0)
		                                            
		return 0;

	a /= (explosion_v * explosion_v);
		                                                          

	return a;
}

#if 0
vector explosion_calcpush(vector explosion_v, float explosion_m, vector target_v, float target_m, float elasticity)
{
	                             
	                                                             
	                                                                          
	                                                                                      
	                                                                     
	                                                                 
	                                                                                                  

	                                                         
	return explosion_v * explosion_calcpush_getmultiplier(explosion_v, target_v) * (
		(1 + elasticity) * (
			explosion_m
		) / (
			target_m + explosion_m
		)
	);                                              
}
#endif

                                                                                                    
vector damage_explosion_calcpush(vector explosion_f, vector target_v, float speedfactor)
{
	                                                                      
	if(speedfactor < 1)
		return explosion_f;

#if 0
	float m;
	                 
	                                             
	m = 1 / ((1 + 0) * speedfactor - 1);
	vector v;
	v = explosion_calcpush(explosion_f * speedfactor, m, target_v, 1, 0);
	                             
	      
	LOG_INFOF("MASS: %f\nv: %v -> %v\nENERGY BEFORE == %f + %f = %f\nENERGY AFTER >= %f",
		m,
		target_v, target_v + v,
		target_v * target_v, m * explosion_f * speedfactor * explosion_f * speedfactor, target_v * target_v + m * explosion_f * speedfactor * explosion_f * speedfactor,
		(target_v + v) * (target_v + v));
	return v;
#endif
	return explosion_f * explosion_calcpush_getmultiplier(explosion_f * speedfactor, target_v);
}


                            
                           
                            

vector cliptoplane(vector v, vector p)
{
	return v - (v * p) * p;
}

vector solve_cubic_pq(float p, float q)
{
	float D, u, v, a;
	D = q*q/4.0 + p*p*p/27.0;
	if(D < 0)
	{
		                
		a = 1.0/3.0 * acos(-q/2.0 * sqrt(-27.0/(p*p*p)));
		u = sqrt(-4.0/3.0 * p);
		                     
		         
		                 
		                 
		return u * vec3(
			cos(a + 2.0/3.0*M_PI),
			cos(a + 4.0/3.0*M_PI),
			cos(a)
		);
	}
	else if(D == 0)
	{
		         
		if(p == 0)
			return '0 0 0';
		u = 3*q/p;
		v = -u/2;
		return (u >= v) ? vec3(v, v, u) : vec3(u, v, v);
	}
	else
	{
		          
		                             
		                             
		a = cbrt(-q/2.0 + sqrt(D)) + cbrt(-q/2.0 - sqrt(D));
		return vec3(a, a, a);
	}
}
vector solve_cubic_abcd(float a, float b, float c, float d)
{
	                
	                   
	float p, q;
	vector v;
	p = (9*a*c - 3*b*b);
	q = (27*a*a*d - 9*a*b*c + 2*b*b*b);
	v = solve_cubic_pq(p, q);
	v = (v -  b * '1 1 1') * (1.0 / (3.0 * a));
	if(a < 0)
		v += '1 0 -1' * (v.z - v.x);             
	return v;
}

vector findperpendicular(vector v)
{
	return normalize(cliptoplane(vec3(v.z, -v.x, v.y), v));
}

#ifdef SVQC
	int W_GunAlign(entity this, int preferred_align)
	{
		if(this.m_gunalign)
			return this.m_gunalign;                        

		entity own = this.owner;

		if(preferred_align < 1 || preferred_align > 4)
			preferred_align = 3;           

		for(int j = 4; j > 1; --j)                                 
		{
			int taken = 0;
			for(int slot = 0; slot < MAX_WEAPONSLOTS; ++slot)
			{
				.entity weaponentity = weaponentities[slot];
				if(own.(weaponentity).m_gunalign == j)                                                      
					taken |= BIT(j);
				if(own.(weaponentity).m_gunalign == preferred_align)
					taken |= BIT(preferred_align);
			}

			if(!(taken & BIT(preferred_align)))
				return preferred_align;                          
			if(!(taken & BIT(j)))
				return j;                                      
		}

		return preferred_align;                    
	}
#else
	int W_GunAlign(entity this, int preferred_align)
	{
		return this.m_gunalign > 0 ? this.m_gunalign : preferred_align;
	}
#endif

#if 0
int W_GetGunAlignment(entity player)
{
	int gunalign = STAT(GUNALIGN, player);
	if(gunalign < 1 || gunalign > 4)
		gunalign = 3;                 
	--gunalign;

	return gunalign;
}
#endif

vector W_CalculateSpread(vector forward, float spread, float spreadfactor, float spreadstyle)
{
	float sigma;
	vector v1 = '0 0 0', v2;
	float dx, dy, r;
	spread *= spreadfactor;                                 
	if(spread <= 0)
		return forward;

	switch(spreadstyle)
	{
		case 0:
		{
			                                             
			                                
			                                
			return forward + randomvec() * spread;
		}
		case 1:
		{
			                        
			return normalize(forward + cliptoplane(randomvec() * spread, forward));
		}
		case 2:
		{
			                                                                    
			sigma = spread * 0.89442719099991587855;                         
			v1 = findperpendicular(forward);
			v2 = cross(forward, v1);
			                              
			dx = random() * 2 * M_PI;
			dy = sin(dx);
			dx = cos(dx);
			                              
			r = random();
			r = sqrt(r);
			return normalize(forward + (v1 * dx + v2 * dy) * r * sigma);
		}
		case 3:            
		{
			sigma = spread * 0.44721359549996;                         
			                                                                                
			v1 = forward;
			v1_x += gsl_ran_gaussian(sigma);
			v1_y += gsl_ran_gaussian(sigma);
			v1_z += gsl_ran_gaussian(sigma);
			return v1;
		}
		case 4:            
		{
			sigma = spread * 0.44721359549996;                         
			                                                                                
			v1_x = gsl_ran_gaussian(sigma);
			v1_y = gsl_ran_gaussian(sigma);
			v1_z = gsl_ran_gaussian(sigma);
			return normalize(forward + cliptoplane(v1, forward));
		}
		case 5:       
		{
			sigma = spread * 1.154700538379252;                         
			v1 = findperpendicular(forward);
			v2 = cross(forward, v1);
			                              
			dx = random() * 2 * M_PI;
			dy = sin(dx);
			dx = cos(dx);
			                              
			r = random();
			r = solve_cubic_abcd(-2, 3, 0, -r) * '0 1 0';
			return normalize(forward + (v1 * dx + v2 * dy) * r * sigma);
		}
		case 6:         
		{
			sigma = spread * 1.095445115010332;                         
			v1 = findperpendicular(forward);
			v2 = cross(forward, v1);
			                              
			dx = random() * 2 * M_PI;
			dy = sin(dx);
			dx = cos(dx);
			                              
			r = random();
			r = sqrt(1 - r);
			r = sqrt(1 - r);
			return normalize(forward + (v1 * dx + v2 * dy) * r * sigma);
		}
		case 7:               
		{
			sigma = spread * 1.224744871391589;                         
			v1 = findperpendicular(forward);
			v2 = cross(forward, v1);
			                              
			dx = random() * 2 * M_PI;
			dy = sin(dx);
			dx = cos(dx);
			                              
			r = random();
			r = 1 - sqrt(r);
			r = 1 - sqrt(r);
			return normalize(forward + (v1 * dx + v2 * dy) * r * sigma);
		}
		default:
			error("g_projectiles_spread_style must be 0 (sphere), 1 (flattened sphere), 2 (circle), 3 (gauss 3D), 4 (gauss plane), 5 (linear falloff), 6 (quadratic falloff), 7 (stronger falloff)!");
	}

	return '0 0 0';
	  
                                    
                            
          
          
                          
                                         
                                                
                              
                                                       
                                
    
}
