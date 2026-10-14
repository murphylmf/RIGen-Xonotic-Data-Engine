#include "lightningarc.qh"

REGISTER_NET_TEMP(TE_CSQC_ARC)

#if defined(SVQC)

	void te_csqc_lightningarc(vector from, vector to)
	{
		WriteHeader(MSG_BROADCAST, TE_CSQC_ARC);

		WriteVector(MSG_BROADCAST, from);
		WriteVector(MSG_BROADCAST, to);
	}

#elif defined(CSQC)

  
                 
               
                
                   
                    

             
 
                                                                                                                                               
                                                                                                                                                     

 
                                                        
 
             
                
                     
                   
                 
                  
                         
                           
                    

                                                                                       
 
  

	void cl_effects_lightningarc(vector from, vector to, float seglength, float drifts, float drifte,
	float branchfactor, float branchfactor_add)
	{
		float length = vlen(from - to);
		if (length < 1) return;

		                                                                             
		                                                                               
		int steps = min(16, floor(length / seglength));
		if (steps < 1)
		{
			te_lightning1(NULL, from, to);
			return;
		}

		float steplength = length / steps;
		vector direction  = normalize(to - from);
		vector pos_l = from;
		if (length > seglength)
		{
			for (int i = 1; i < steps; i += 1)
			{
				float drift = drifts * (1 - (i / steps)) + drifte * (i / steps);
				vector dirnew = normalize(direction * (1 - drift) + randomvec() * drift);
				vector pos = pos_l +  dirnew * steplength;
				te_lightning1(NULL, pos_l, pos);
				                                                                                                
				                              
				                                                                                                                                                    

				pos_l = pos;
			}
			te_lightning1(NULL, pos_l, to);
		}
		else
		{
			te_lightning1(NULL, from, to);
		}
	}

	NET_HANDLE(TE_CSQC_ARC, bool isNew)
	{
		vector from = ReadVector();
		vector to = ReadVector();
		return = true;

		if (autocvar_cl_effects_lightningarc_simple)
		{
			te_lightning1(NULL, from, to);
		}
		else
		{
			float seglength        = autocvar_cl_effects_lightningarc_segmentlength;
			float drifts           = autocvar_cl_effects_lightningarc_drift_start;
			float drifte           = autocvar_cl_effects_lightningarc_drift_end;
			float branchfactor     = autocvar_cl_effects_lightningarc_branchfactor_start;
			float branchfactor_add = autocvar_cl_effects_lightningarc_branchfactor_add;

			cl_effects_lightningarc(from, to, seglength, drifts, drifte, branchfactor, branchfactor_add);
		}
	}

#endif
