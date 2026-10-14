#ifndef GMQCC_AST_HDR
#define GMQCC_AST_HDR
#include <vector>
#include "ir.h"

typedef uint16_t ast_flag_t;

                                                
                                 
   

struct ast_node;
struct ast_expression;
struct ast_value;
struct ast_function;
struct ast_block;
struct ast_binary;
struct ast_store;
struct ast_binstore;
struct ast_entfield;
struct ast_ifthen;
struct ast_ternary;
struct ast_loop;
struct ast_call;
struct ast_unary;
struct ast_return;
struct ast_member;
struct ast_array_index;
struct ast_breakcont;
struct ast_switch;
struct ast_label;
struct ast_goto;
struct ast_argpipe;
struct ast_state;

enum {
    AST_FLAG_VARIADIC       = 1 << 0,
    AST_FLAG_NORETURN       = 1 << 1,
    AST_FLAG_INLINE         = 1 << 2,
    AST_FLAG_INITIALIZED    = 1 << 3,
    AST_FLAG_DEPRECATED     = 1 << 4,
    AST_FLAG_INCLUDE_DEF    = 1 << 5,
    AST_FLAG_IS_VARARG      = 1 << 6,
    AST_FLAG_ALIAS          = 1 << 7,
    AST_FLAG_ERASEABLE      = 1 << 8,
    AST_FLAG_NOERASE        = 1 << 9,                                                                
    AST_FLAG_ACCUMULATE     = 1 << 10,

                              
                                                     
       
    AST_FLAG_ARRAY_INIT     = 1 << 11,

    AST_FLAG_FINAL_DECL     = 1 << 12,

                               
                                                                            
                                                                         
                                                                      
                                                                              
                                             
       
    AST_FLAG_COVERAGE       = 1 << 13,
    AST_FLAG_BLOCK_COVERAGE = 1 << 14,

      
                                                                             
                               
       
    AST_FLAG_NOREF          = 1 << 15,

    AST_FLAG_LAST,
    AST_FLAG_TYPE_MASK      = (AST_FLAG_VARIADIC | AST_FLAG_NORETURN),
    AST_FLAG_COVERAGE_MASK  = (AST_FLAG_BLOCK_COVERAGE)
};

enum {
    TYPE_ast_node,                
    TYPE_ast_expression,          
    TYPE_ast_value,               
    TYPE_ast_function,            
    TYPE_ast_block,               
    TYPE_ast_binary,              
    TYPE_ast_store,               
    TYPE_ast_binstore,            
    TYPE_ast_entfield,            
    TYPE_ast_ifthen,              
    TYPE_ast_ternary,             
    TYPE_ast_loop,                
    TYPE_ast_call,                
    TYPE_ast_unary,               
    TYPE_ast_return,              
    TYPE_ast_member,              
    TYPE_ast_array_index,         
    TYPE_ast_breakcont,           
    TYPE_ast_switch,              
    TYPE_ast_label,               
    TYPE_ast_goto,                
    TYPE_ast_argpipe,             
    TYPE_ast_state                
};

#define ast_istype(x, t) ( (x)->m_node_type == (TYPE_##t) )

struct ast_node
{
    ast_node() = delete;
    ast_node(lex_ctx_t, int nodetype);
    virtual ~ast_node();

    lex_ctx_t m_context;
                                                                           
    int              m_node_type;
                                                           
                                                           
       
    bool             m_keep_node;
    bool             m_side_effects;

    void propagateSideEffects(const ast_node *other);
};

#define ast_unref(x) do        \
{                              \
    if (! (x)->m_keep_node ) { \
        delete (x);            \
    }                          \
} while(0)

enum class ast_copy_type_t { value };
static const ast_copy_type_t ast_copy_type = ast_copy_type_t::value;

                                                                  
                                                                   
                  
                                                                    
                        
                                                                    
                                                                
                                                                 
                                                                  
   
struct ast_expression : ast_node {
    ast_expression() = delete;
    ast_expression(lex_ctx_t ctx, int nodetype, qc_type vtype);
    ast_expression(lex_ctx_t ctx, int nodetype);
    ~ast_expression();

    ast_expression(ast_copy_type_t, const ast_expression&);
    ast_expression(ast_copy_type_t, lex_ctx_t ctx, const ast_expression&);
    ast_expression(ast_copy_type_t, int nodetype, const ast_expression&);
    ast_expression(ast_copy_type_t, int nodetype, lex_ctx_t ctx, const ast_expression&);

    static ast_expression *shallowType(lex_ctx_t ctx, qc_type vtype);

    bool compareType(const ast_expression &other) const;
    void adoptType(const ast_expression &other);

    qc_type                 m_vtype = TYPE_VOID;
    ast_expression         *m_next = nullptr;
                                   
    size_t                  m_count = 0;
    std::vector<std::unique_ptr<ast_value>> m_type_params;

    ast_flag_t              m_flags = 0;
                                                             
                              
       
    ast_expression         *m_varparam = nullptr;
                                                             
                                                              
                                                         
                                                              
       
    ir_value               *m_outl = nullptr;
    ir_value               *m_outr = nullptr;

    virtual bool codegen(ast_function *current, bool lvalue, ir_value **out);
};

        
  
                                                      
                                                            
                     
                                                                  
   
union basic_value_t {
    qcfloat_t     vfloat;
    int           vint;
    vec3_t        vvec;
    const char   *vstring;
    int           ventity;
    ast_function *vfunc;
    ast_value    *vfield;
};

struct ast_value : ast_expression
{
    ast_value() = delete;
    ast_value(lex_ctx_t ctx, const std::string &name, qc_type qctype);
    ~ast_value();

    ast_value(ast_copy_type_t, const ast_expression&, const std::string&);
    ast_value(ast_copy_type_t, const ast_value&);
    ast_value(ast_copy_type_t, const ast_value&, const std::string&);

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    void addParam(ast_value*);

    bool generateGlobal(ir_builder*, bool isfield);
    bool generateLocal(ir_function*, bool param);
    bool generateAccessors(ir_builder*);

    std::string m_name;
    std::string m_desc;

    const char *m_argcounter = nullptr;

    int m_cvq = CV_NONE;                              
    bool m_isfield = false;                            
    bool m_isimm = false;                                     
    bool m_hasvalue = false;
    bool m_inexact = false;                                            
    basic_value_t m_constval;
                                                
                                            
                    
       
    std::vector<basic_value_t> m_initlist;

    ir_value *m_ir_v = nullptr;
    std::vector<ir_value*> m_ir_values;
    size_t m_ir_value_count = 0;

                                                  
    ast_value *m_setter = nullptr;
    ast_value *m_getter = nullptr;

    bool m_intrinsic = false;                                        

private:
    bool generateGlobalFunction(ir_builder*);
    bool generateGlobalField(ir_builder*);
    ir_value *prepareGlobalArray(ir_builder*);
    bool setGlobalArray();
    bool checkArray(const ast_value &array) const;
};

void ast_type_to_string(const ast_expression *e, char *buf, size_t bufsize);

enum ast_binary_ref {
    AST_REF_NONE  = 0,
    AST_REF_LEFT  = 1 << 1,
    AST_REF_RIGHT = 1 << 2,
    AST_REF_ALL   = (AST_REF_LEFT | AST_REF_RIGHT)
};


         
  
                                       
   
struct ast_binary : ast_expression
{
    ast_binary() = delete;
    ast_binary(lex_ctx_t ctx, int op, ast_expression *l, ast_expression *r);
    ~ast_binary();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    int m_op;
    ast_expression *m_left;
    ast_expression *m_right;
    ast_binary_ref m_refs;
    bool m_right_first;
};

           
  
                                                                               
                                                             
   
struct ast_binstore : ast_expression
{
    ast_binstore() = delete;
    ast_binstore(lex_ctx_t ctx, int storeop, int mathop, ast_expression *l, ast_expression *r);
    ~ast_binstore();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    int m_opstore;
    int m_opbin;
    ast_expression *m_dest;
    ast_expression *m_source;
                                                                                  
    bool m_keep_dest;
};

        
  
                                     
   
struct ast_unary : ast_expression
{
    ast_unary() = delete;
    ~ast_unary();

    static ast_unary* make(lex_ctx_t ctx, int op, ast_expression *expr);

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    int m_op;
    ast_expression *m_operand;

private:
    ast_unary(lex_ctx_t ctx, int op, ast_expression *expr);
};

         
  
                                                                          
                                              
                                        
   
struct ast_return : ast_expression
{
    ast_return() = delete;
    ast_return(lex_ctx_t ctx, ast_expression *expr);
    ~ast_return();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    ast_expression *m_operand;
};

               
  
                         
                                                            
                                                    
               
                                                        
                       
                                                               
             
                                                               
                                                           
   
struct ast_entfield : ast_expression
{
    ast_entfield() = delete;
    ast_entfield(lex_ctx_t ctx, ast_expression *entity, ast_expression *field);
    ast_entfield(lex_ctx_t ctx, ast_expression *entity, ast_expression *field, const ast_expression *outtype);
    ~ast_entfield();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

                                                        
    ast_expression *m_entity;
                                                                     
    ast_expression *m_field;
};

                 
  
                                                        
                                         
   
struct ast_member : ast_expression
{
    static ast_member *make(lex_ctx_t ctx, ast_expression *owner, unsigned int field, const std::string &name);
    ~ast_member();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    ast_expression *m_owner;
    unsigned int m_field;
    std::string m_name;
    bool m_rvalue;

private:
    ast_member() = delete;
    ast_member(lex_ctx_t ctx, ast_expression *owner, unsigned int field, const std::string &name);
};

                      
  
                                                 
                                                                 
                                                                         
                
                                                                          
                                                                          
                                           
   
struct ast_array_index : ast_expression
{
    static ast_array_index* make(lex_ctx_t ctx, ast_expression *array, ast_expression *index);
    ~ast_array_index();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    ast_expression *m_array;
    ast_expression *m_index;
private:
    ast_array_index() = delete;
    ast_array_index(lex_ctx_t ctx, ast_expression *array, ast_expression *index);
};

                    
  
                                                  
   
struct ast_argpipe : ast_expression
{
    ast_argpipe() = delete;
    ast_argpipe(lex_ctx_t ctx, ast_expression *index);

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    ~ast_argpipe();
    ast_expression *m_index;
};

        
  
                                       
                                     
   
struct ast_store : ast_expression
{
    ast_store() = delete;
    ast_store(lex_ctx_t ctx, int op, ast_expression *d, ast_expression *s);
    ~ast_store();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    int m_op;
    ast_expression *m_dest;
    ast_expression *m_source;
};

     
  
                                                                          
                                                                          
  
                                                                   
  
                                                                       
                                                                      
         
   
struct ast_ifthen : ast_expression
{
    ast_ifthen() = delete;
    ast_ifthen(lex_ctx_t ctx, ast_expression *cond, ast_expression *ontrue, ast_expression *onfalse);
    ~ast_ifthen();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    ast_expression *m_cond;
                                                                     
    ast_expression *m_on_true;
    ast_expression *m_on_false;
};

                         
  
                                                                 
                                                           
                                                                
              
  
                                                               
                                                  
  
                                                            
                                                                  
   
struct ast_ternary : ast_expression
{
    ast_ternary() = delete;
    ast_ternary(lex_ctx_t ctx, ast_expression *cond, ast_expression *ontrue, ast_expression *onfalse);
    ~ast_ternary();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    ast_expression *m_cond;
                                                                     
    ast_expression *m_on_true;
    ast_expression *m_on_false;
};

                      
  
                                       
                                     
                                
                                 
                                    
                                                       
                                                         
                            

      
                        
 
           

                                             
                         
              

          
 
   
struct ast_loop : ast_expression
{
    ast_loop() = delete;
    ast_loop(lex_ctx_t ctx,
             ast_expression *initexpr,
             ast_expression *precond, bool pre_not,
             ast_expression *postcond, bool post_not,
             ast_expression *increment,
             ast_expression *body);
    ~ast_loop();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    ast_expression *m_initexpr;
    ast_expression *m_precond;
    ast_expression *m_postcond;
    ast_expression *m_increment;
    ast_expression *m_body;
                                                                       
                                       
                                                                         
                                                                           
            
       
    bool m_pre_not;
    bool m_post_not;
};

                 
   
struct ast_breakcont : ast_expression
{
    ast_breakcont() = delete;
    ast_breakcont(lex_ctx_t ctx, bool iscont, unsigned int levels);
    ~ast_breakcont();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;


    bool         m_is_continue;
    unsigned int m_levels;
};

                    
  
                                                                       
                                                                            
                                                        
                                                               
                                                                             
                       
                   
   
struct ast_switch_case {
    ast_expression *m_value;                            
    ast_expression *m_code;
};

struct ast_switch : ast_expression
{
    ast_switch() = delete;
    ast_switch(lex_ctx_t ctx, ast_expression *op);
    ~ast_switch();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    ast_expression *m_operand;
    std::vector<ast_switch_case> m_cases;
};


              
  
                                                           
   
struct ast_label : ast_expression
{
    ast_label() = delete;
    ast_label(lex_ctx_t ctx, const std::string &name, bool undefined);
    ~ast_label();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    std::string m_name;
    ir_block *m_irblock;
    std::vector<ast_goto*> m_gotos;

                                           
    bool m_undefined;

private:
    void registerGoto(ast_goto*);
    friend struct ast_goto;
};

             
  
                                                               
   
struct ast_goto : ast_expression
{
    ast_goto() = delete;
    ast_goto(lex_ctx_t ctx, const std::string &name);
    ~ast_goto();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    void setLabel(ast_label*);

    std::string m_name;
    ast_label *m_target;
    ir_block *m_irblock_from;
};

             
  
                                                                     
   
struct ast_state : ast_expression
{
    ast_state() = delete;
    ast_state(lex_ctx_t ctx, ast_expression *frame, ast_expression *think);
    ~ast_state();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    ast_expression *m_framenum;
    ast_expression *m_nextthink;
};

            
  
                                                                           
                                                               
                                                               
                                                                
              
                                                                    
                                                                        
   
struct ast_call : ast_expression
{
    ast_call() = delete;
    static ast_call *make(lex_ctx_t, ast_expression*);
    ~ast_call();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    bool checkTypes(ast_expression *this_func_va_type) const;

    ast_expression *m_func;
    std::vector<ast_expression *> m_params;
    ast_expression *m_va_count;

private:
    ast_call(lex_ctx_t ctx, ast_expression *funcexpr);
    bool checkVararg(ast_expression *va_type, ast_expression *exp_type) const;
};

         
  
   
struct ast_block : ast_expression
{
    ast_block() = delete;
    ast_block(lex_ctx_t ctx);
    ~ast_block();

    bool codegen(ast_function *current, bool lvalue, ir_value **out) override;

    std::vector<ast_value*>      m_locals;
    std::vector<ast_expression*> m_exprs;
    std::vector<ast_expression*> m_collect;

    void setType(const ast_expression &from);
    bool GMQCC_WARN addExpr(ast_expression*);
    void collect(ast_expression*);
};

           
  
                                                   
                                                                     
  
                                                                     
                                                                
                                                                   
                                              
  
                                                          
  
   
struct ast_function : ast_node
{
    ast_function() = delete;
    static ast_function *make(lex_ctx_t ctx, const std::string &name, ast_value *vtype);
    ~ast_function();

    const char* makeLabel(const char *prefix);
    virtual bool generateFunction(ir_builder*);

    ast_value  *m_function_type = nullptr;
    std::string m_name;

    int m_builtin = 0;

                                                                    
    std::vector<std::string> m_static_names;
                                                                  
                                                                 
                                                                 
                                     
    unsigned int m_static_count = 0;

    ir_function *m_ir_func = nullptr;
    ir_block *m_curblock = nullptr;
    std::vector<ir_block*> m_breakblocks;
    std::vector<ir_block*> m_continueblocks;

    size_t m_labelcount = 0;
                                                    
                                                        
                                         
       
    std::vector<std::unique_ptr<ast_block>> m_blocks;
    std::unique_ptr<ast_value> m_varargs;
    std::unique_ptr<ast_value> m_argc;
    ast_value *m_fixedparams = nullptr;                     
    ast_value *m_return_value = nullptr;

private:
    ast_function(lex_ctx_t ctx, const std::string &name, ast_value *vtype);

    char m_labelbuf[64];
};

  
                                                                                     
                                                                                     
                                                                                           
                 
   
typedef int static_assert_is_ast_flag_safe [((AST_FLAG_LAST) <= (ast_flag_t)(-1)) ? 1 : -1];
#endif
