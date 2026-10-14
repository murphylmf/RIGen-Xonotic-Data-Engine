  
                                         

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

                                       

#ifndef PR_COMP_H
#define PR_COMP_H

typedef unsigned int	func_t;
typedef int	string_t;

typedef enum etype_e {ev_void, ev_string, ev_float, ev_vector, ev_entity, ev_field, ev_function, ev_pointer} etype_t;


#define	OFS_NULL		0
#define	OFS_RETURN		1
#define	OFS_PARM0		4		                                            
#define	OFS_PARM1		7
#define	OFS_PARM2		10
#define	OFS_PARM3		13
#define	OFS_PARM4		16
#define	OFS_PARM5		19
#define	OFS_PARM6		22
#define	OFS_PARM7		25
#define	RESERVED_OFS	28


typedef enum opcode_e
{
	OP_DONE,
	OP_MUL_F,
	OP_MUL_V,
	OP_MUL_FV,
	OP_MUL_VF,
	OP_DIV_F,
	OP_ADD_F,
	OP_ADD_V,
	OP_SUB_F,
	OP_SUB_V,

	OP_EQ_F,
	OP_EQ_V,
	OP_EQ_S,
	OP_EQ_E,
	OP_EQ_FNC,

	OP_NE_F,
	OP_NE_V,
	OP_NE_S,
	OP_NE_E,
	OP_NE_FNC,

	OP_LE,
	OP_GE,
	OP_LT,
	OP_GT,

	OP_LOAD_F,
	OP_LOAD_V,
	OP_LOAD_S,
	OP_LOAD_ENT,
	OP_LOAD_FLD,
	OP_LOAD_FNC,

	OP_ADDRESS,

	OP_STORE_F,
	OP_STORE_V,
	OP_STORE_S,
	OP_STORE_ENT,
	OP_STORE_FLD,
	OP_STORE_FNC,

	OP_STOREP_F,
	OP_STOREP_V,
	OP_STOREP_S,
	OP_STOREP_ENT,
	OP_STOREP_FLD,
	OP_STOREP_FNC,

	OP_RETURN,
	OP_NOT_F,
	OP_NOT_V,
	OP_NOT_S,
	OP_NOT_ENT,
	OP_NOT_FNC,
	OP_IF,
	OP_IFNOT,
	OP_CALL0,
	OP_CALL1,
	OP_CALL2,
	OP_CALL3,
	OP_CALL4,
	OP_CALL5,
	OP_CALL6,
	OP_CALL7,
	OP_CALL8,
	OP_STATE,
	OP_GOTO,
	OP_AND,
	OP_OR,

	OP_BITAND,
	OP_BITOR
}
opcode_t;


typedef struct statement_s
{
	unsigned short	op;
	signed short	a,b,c;
}
dstatement_t;

typedef struct ddef_s
{
	unsigned short	type;		                                
								                                              
	unsigned short	ofs;
	int			s_name;
}
ddef_t;
#define	DEF_SAVEGLOBAL	(1<<15)

#define	MAX_PARMS	8

typedef struct dfunction_s
{
	int		first_statement;	                                
	int		parm_start;
	int		locals;				                               

	int		profile;		          

	int		s_name;
	int		s_file;			                         

	int		numparms;
	unsigned char	parm_size[MAX_PARMS];
}
dfunction_t;

typedef struct mfunction_s
{
	int		first_statement;	                                
	int		parm_start;
	int		locals;				                               

	                                                                                
	double  tprofile;                                       
	double  tbprofile;                                                                                                
	double	profile;		          
	double	builtinsprofile;                                                     
	double	callcount;                                                                   
	double  totaltime;                                                                  
	double	tprofile_total;		                                                                                
	double	profile_total;		          
	double	builtinsprofile_total;                                                     
	int     recursion;

	int		s_name;
	int		s_file;			                         

	int		numparms;
	unsigned char	parm_size[MAX_PARMS];
}
mfunction_t;

typedef struct mstatement_s
{
	opcode_t	op;
	int			operand[3];                                    
	int			jumpabsolute;                                
}
mstatement_t;


#define	PROG_VERSION	6
typedef struct dprograms_s
{
	int		version;
	int		crc;			                       

	int		ofs_statements;
	int		numstatements;	                          

	int		ofs_globaldefs;
	int		numglobaldefs;

	int		ofs_fielddefs;
	int		numfielddefs;

	int		ofs_functions;
	int		numfunctions;	                         

	int		ofs_strings;
	int		numstrings;		                                

	int		ofs_globals;
	int		numglobals;

	int		entityfields;
}
dprograms_t;

#endif

