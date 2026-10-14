#ifndef GMQCC_PARSER_HDR
#define GMQCC_PARSER_HDR
#include "gmqcc.h"
#include "lexer.h"
#include "ast.h"

#include "intrin.h"
#include "fold.h"

struct parser_t;

#define parser_ctx(p) ((p)->lex->tok.ctx)

struct parser_t {
    parser_t();
    ~parser_t();

    void remove_ast();

    lex_file *lex;
    int tok;

    bool ast_cleaned;

    std::vector<ast_expression *> globals;
    std::vector<ast_expression *> fields;
    std::vector<ast_function *> functions;
    size_t translated;

                                                                     
    std::vector<ast_value *> accessors;

    ast_value *nil;
    ast_value *reserved_version;

    size_t crc_globals;
    size_t crc_fields;

    ast_function *function;
    ht aliases;

                                             
                                              
       
    std::vector<ast_label*> labels;
    std::vector<ast_goto*> gotos;
    std::vector<const char *> breaks;
    std::vector<const char *> continues;

                                             
    std::vector<ht> variables;
    ht htfields;
    ht htglobals;
    std::vector<ht> typedefs;

                                                        
    std::vector<ast_expression*> _locals;
    std::vector<size_t> _blocklocals;
    std::vector<std::unique_ptr<ast_value>> _typedefs;
    std::vector<size_t> _blocktypedefs;
    std::vector<lex_ctx_t> _block_ctx;

                                        
    const oper_info *assign_op;

                      
    ast_value *const_vec[3];

                      
    bool noref;

                               
    size_t max_param_count;

    fold m_fold;
    intrin m_intrin;
};


              
char           *parser_strdup     (const char *str);
ast_expression *parser_find_global(parser_t *parser, const char *name);

#endif
