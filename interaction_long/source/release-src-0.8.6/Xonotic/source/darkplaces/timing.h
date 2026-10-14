  
                                                  

                                

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

#ifndef __TIMING_H__
#define __TIMING_H__

#if defined(DO_TIMING)

#define TIMING_BEGIN	double _timing_end_, _timing_start_ = Sys_DirtyTime();
#define TIMING_END_STR(S)		\
  _timing_end_ = Sys_DirtyTime();	\
  Con_Printf ("%s: %.3g s\n", S, _timing_end_ - _timing_start_);
#define TIMING_END	TIMING_END_STR(__FUNCTION__)

#define TIMING_INTERMEDIATE(S)						\
  {									\
    double currentTime = Sys_DirtyTime();				\
    Con_Printf ("%s: %.3g s\n", S, currentTime - _timing_start_);	\
  }
  
#define TIMING_TIMESTATEMENT(Stmt)	\
  {					\
    TIMING_BEGIN			\
    Stmt;				\
    TIMING_END_STR(#Stmt);		\
  }

#else

#define TIMING_BEGIN
#define TIMING_END_STR(S)
#define TIMING_END
#define TIMING_INTERMEDIATE(S)
#define TIMING_TIMESTATEMENT(Stmt)	Stmt

#endif

#endif                

