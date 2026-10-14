#include "sv_dynamic_handicap.qh"
         
                                                                           
            
                   
                                              

                                                                               

int autocvar_g_dynamic_handicap;                                         
                                                                           
                                                   
float autocvar_g_dynamic_handicap_scale;
                                                                                
                                                                          
                               
float autocvar_g_dynamic_handicap_exponent;
float autocvar_g_dynamic_handicap_min;                                        
float autocvar_g_dynamic_handicap_max;                                        

                                                                               

                                            
                                       
                          
float DynamicHandicap_ClampHandicap(float handicap);

                                                                               

                                               
                      
void DynamicHandicap_UpdateHandicap()
{
	float total_score = 0;
	float totalplayers = 0;
	FOREACH_CLIENT(IS_PLAYER(it),
	{
		total_score += PlayerScore_Get(it, SP_SCORE);
		++totalplayers;
	});
	float mean_score = total_score / totalplayers;
	FOREACH_CLIENT(true,
	{
		float score = PlayerScore_Get(it, SP_SCORE);
		float handicap = fabs((score - mean_score) *
			autocvar_g_dynamic_handicap_scale);
		handicap = handicap ** autocvar_g_dynamic_handicap_exponent;
		if (score < mean_score)
		{
			handicap = -handicap;
		}
		if (handicap >= 0)
		{
			handicap += 1;
		}
		else
		{
			handicap = 1 / (fabs(handicap) + 1);
		}
		handicap = DynamicHandicap_ClampHandicap(handicap);
		Handicap_SetForcedHandicap(it, handicap);
	});
}

float DynamicHandicap_ClampHandicap(float handicap)
{
	if ((autocvar_g_dynamic_handicap_min >= 0) && (handicap <
		autocvar_g_dynamic_handicap_min))
	{
		handicap = autocvar_g_dynamic_handicap_min;
	}
	if ((autocvar_g_dynamic_handicap_max > 0) && (handicap >
		autocvar_g_dynamic_handicap_max))
	{
		handicap = autocvar_g_dynamic_handicap_max;
	}
	return handicap;
}

                                                                              

REGISTER_MUTATOR(dynamic_handicap, autocvar_g_dynamic_handicap);

MUTATOR_HOOKFUNCTION(dynamic_handicap, BuildMutatorsString)
{
	M_ARGV(0, string) = strcat(M_ARGV(0, string), ":handicap");
}

MUTATOR_HOOKFUNCTION(dynamic_handicap, BuildMutatorsPrettyString)
{
	M_ARGV(0, string) = strcat(M_ARGV(0, string), ", Dynamic handicap");
}

MUTATOR_HOOKFUNCTION(dynamic_handicap, ClientDisconnect)
{
	DynamicHandicap_UpdateHandicap();
}

MUTATOR_HOOKFUNCTION(dynamic_handicap, PutClientInServer)
{
	DynamicHandicap_UpdateHandicap();
}

MUTATOR_HOOKFUNCTION(dynamic_handicap, MakePlayerObserver)
{
	DynamicHandicap_UpdateHandicap();
}

MUTATOR_HOOKFUNCTION(dynamic_handicap, AddedPlayerScore)
{
	if (M_ARGV(0, entity) != SP_SCORE)
	{
		return;
	}
	DynamicHandicap_UpdateHandicap();
}
