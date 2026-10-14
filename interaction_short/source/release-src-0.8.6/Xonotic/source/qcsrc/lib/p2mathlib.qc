  
                                     

                                                              
                                                            
                                                               
                                                       

                                                                
                                                               
                                                     

                                                     

                                                                  
                                                            
                                                                            
  

ERASEABLE
vector vec_bias(vector v, float f)
{
	vector c;
	c.x = v.x + f;
	c.y = v.y + f;
	c.z = v.z + f;
	return c;
}
ERASEABLE
vector vec_to_min(vector a, vector b)
{
	vector c;
	c.x = min(a.x, b.x);
	c.y = min(a.y, b.y);
	c.z = min(a.z, b.z);
	return c;
}

ERASEABLE
vector vec_to_max(vector a, vector b)
{
	vector c;
	c.x = max(a.x, b.x);
	c.y = max(a.y, b.y);
	c.z = max(a.z, b.z);
	return c;
}

                                                                                                                                    
ERASEABLE
vector vec_bounds_in(vector point, vector a, vector b)
{
	vector d = vec_to_min(a, b);
	vector e = vec_to_max(a, b);

	vector c = vec_to_min(vec_to_max(point, d), e);

	return c;
}

ERASEABLE
vector vec_bounds_out(vector point, vector a, vector b)
{
	vector d = vec_to_max(a, b);
	vector e = vec_to_min(a, b);

	vector c = vec_to_min(vec_to_max(point, d), e);

	return c;
}

ERASEABLE
float angle_snap_f(float f, float increment)
{
	for (int j = 0; j <= 360; )
	{
		if (f <= j - increment) return j - increment;
		j = j + increment;
	}

	return 0;
}

ERASEABLE
vector angle_snap_vec(vector v, float increment)
{
	vector c;
	c.x = angle_snap_f(v.x, increment);
	c.y = angle_snap_f(v.y, increment);
	c.z = angle_snap_f(v.z, increment);
	return c;
}

ERASEABLE
vector aim_vec(vector org, vector targ)
{
	vector v;
	                                               
	v.x = targ.x - org.x;
	v.y = targ.y - org.y;
	v.z = org.z - targ.z;
	                        
	return vectoangles(normalize(v));
}
