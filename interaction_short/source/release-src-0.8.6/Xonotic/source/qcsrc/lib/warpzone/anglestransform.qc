#include "anglestransform.qh"

                    
                                                    
vector AnglesTransform_Apply(vector transform, vector v)
{
	vector forward, right, up;
	FIXED_MAKE_VECTORS(transform, forward, right, up);
	return forward * v.x + right * (-v.y) + up * v.z;
}

vector AnglesTransform_Multiply(vector t1, vector t2)
{
	vector forward, right, up;
	FIXED_MAKE_VECTORS(t2, forward, right, up);
	forward = AnglesTransform_Apply(t1, forward);
	up = AnglesTransform_Apply(t1, up);
	return fixedvectoangles2(forward, up);
}

vector AnglesTransform_Invert(vector transform)
{
	vector i_forward, i_up;
	vector forward, right, up;
	FIXED_MAKE_VECTORS(transform, forward, right, up);
	                                                                                        
	                                         
	                                                                     
	                                  
	i_forward.x = forward.x;
	i_forward.y = -right.x;
	i_forward.z = up.x;
	i_up.x = forward.z;
	i_up.y = -right.z;
	i_up.z = up.z;
	return fixedvectoangles2(i_forward, i_up);
}

vector AnglesTransform_TurnDirectionFR(vector transform)
{
	                               
	                                        
	                              
	                                                     
	transform.x = -transform.x;
	transform.y = 180 + transform.y;
	transform.z = -transform.z;
	               
	               
	               
	return transform;
}

vector AnglesTransform_TurnDirectionFU(vector transform)
{
	                               
	                                        
	                              
	                                                     
	transform.x = -transform.x;
	transform.y = 180 + transform.y;
	transform.z = 180 - transform.z;
	return transform;
}

vector AnglesTransform_RightDivide(vector to_transform, vector from_transform)
{
	return AnglesTransform_Multiply(to_transform, AnglesTransform_Invert(from_transform));
}

vector AnglesTransform_LeftDivide(vector from_transform, vector to_transform)
{
	return AnglesTransform_Multiply(AnglesTransform_Invert(from_transform), to_transform);
}

vector AnglesTransform_Normalize(vector t, float minimize_roll)
{
	float need_flip;
	                                            
	t.x = t.x - 360 * rint(t.x / 360);
	t.y = t.y - 360 * rint(t.y / 360);
	t.z = t.z - 360 * rint(t.z / 360);
	if(minimize_roll)
		need_flip = (t.z > 90 || t.z <= -90);
	else
		need_flip = (t.x > 90 || t.x < -90);                                                                              
	if(need_flip)
	{
		if(t.x >= 0) t.x = 180 - t.x; else t.x = -180 - t.x;
		if(t.y > 0) t.y -= 180; else t.y += 180;
		if(t.z > 0) t.z -= 180; else t.z += 180;
	}
	return t;
}

vector AnglesTransform_CancelRoll(vector t)
{
	const float epsilon = 30;
	float f;

	               
	                                    
	                                                            
	                                                       

	                             

	f = fabs(t.x - (-90)) / epsilon;
	if(f < 1)
	{
		            
		t.y += t.z;
		t.z = 0;
	}
	else
	{
		f = fabs(t.x - 90) / epsilon;
		if(f < 1)
		{
			           
			t.y -= t.z;
			t.z = 0;
		}
	}
	return t;
}

#if POSITIVE_PITCH_IS_DOWN
vector AnglesTransform_ApplyToAngles(vector transform, vector v)
{
	v.x = -v.x;
	v = AnglesTransform_Multiply(transform, v);
	v.x = -v.x;
	return v;
}
vector AnglesTransform_ApplyToVAngles(vector transform, vector v)
{
	v = AnglesTransform_Multiply(transform, v);
	return v;
}
vector AnglesTransform_FromAngles(vector v)
{
	v.x = -v.x;
	return v;
}
vector AnglesTransform_ToAngles(vector v)
{
	v.x = -v.x;
	return v;
}
vector AnglesTransform_FromVAngles(vector v)
{
	return v;
}
vector AnglesTransform_ToVAngles(vector v)
{
	return v;
}
#else
vector AnglesTransform_ApplyToAngles(vector transform, vector v)
{
	v = AnglesTransform_Multiply(transform, v);
	return v;
}
vector AnglesTransform_ApplyToVAngles(vector transform, vector v)
{
	v.x = -v.x;
	v = AnglesTransform_Multiply(transform, v);
	v.x = -v.x;
	return v;
}
vector AnglesTransform_FromAngles(vector v)
{
	return v;
}
vector AnglesTransform_ToAngles(vector v)
{
	return v;
}
vector AnglesTransform_FromVAngles(vector v)
{
	v.x = -v.x;
	return v;
}
vector AnglesTransform_ToVAngles(vector v)
{
	v.x = -v.x;
	return v;
}
#endif

vector AnglesTransform_Multiply_GetPostShift(vector t0, vector st0, vector t1, vector st1)
{
	                         
	                              
	                                 
	return st0 + AnglesTransform_Apply(t0, st1);
}
vector AnglesTransform_PrePostShift_GetPostShift(vector sf, vector t, vector st)
{
	return st - AnglesTransform_Apply(t, sf);
}
