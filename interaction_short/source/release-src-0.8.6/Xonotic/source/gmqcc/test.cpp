#include <vector>

#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#include <sys/types.h>
#include <sys/wait.h>
#include <sys/stat.h>

#include <dirent.h>
#include <unistd.h>

#include "gmqcc.h"

static const char *task_bins[] = {
    "./gmqcc",
    "./qcvm"
};

struct popen_t {
    FILE *handles[3];
    int pipes[3];
    int stderr_fd;
    int stdout_fd;
    int pid;
};

static FILE **task_popen(const char *command, const char *mode) {
    int     inhandle  [2];
    int     outhandle [2];
    int     errhandle [2];
    int     trypipe;

    popen_t *data = (popen_t*)mem_a(sizeof(popen_t));

    char *line = (char*)command;
    std::vector<char *> argv;
    {

        while (*line != '\0') {
            while (*line == ' ' || *line == '\t' || *line == '\n')
                *line++ = '\0';
            argv.push_back(line);
            while (*line != '\0' && *line != ' ' &&
                   *line != '\t' && *line != '\n') line++;
        }
        argv.push_back((char *)0);
    }

    if ((trypipe = pipe(inhandle))  < 0) goto task_popen_error_0;
    if ((trypipe = pipe(outhandle)) < 0) goto task_popen_error_1;
    if ((trypipe = pipe(errhandle)) < 0) goto task_popen_error_2;

    if ((data->pid = fork()) > 0) {
                    
        close(inhandle [0]);
        close(outhandle [1]);
        close(errhandle [1]);
        data->pipes[0] = inhandle [1];
        data->pipes[1] = outhandle[0];
        data->pipes[2] = errhandle[0];
        data->handles[0] = fdopen(inhandle [1], "w");
        data->handles[1] = fdopen(outhandle[0], mode);
        data->handles[2] = fdopen(errhandle[0], mode);
        return data->handles;
    } else if (data->pid == 0) {
                   
        close(inhandle [1]);
        close(outhandle[0]);
        close(errhandle[0]);

                                                            
        dup2(inhandle [0], 0);
        dup2(outhandle[1], 1);
        dup2(errhandle[1], 2);

        execvp(argv[0], &argv[0]);
        exit(95);
    } else {
                         
        goto task_popen_error_3;
    }

task_popen_error_3: close(errhandle[0]), close(errhandle[1]);
task_popen_error_2: close(outhandle[0]), close(outhandle[1]);
task_popen_error_1: close(inhandle [0]), close(inhandle [1]);
task_popen_error_0:

    return nullptr;
}

static int task_pclose(FILE **handles) {
    popen_t *data   = (popen_t*)handles;
    int      status = 0;

    close(data->pipes[0]);             
    close(data->pipes[1]);             
    close(data->pipes[2]);             

    if (data->pid != waitpid(data->pid, &status, 0)) {
      abort();
    }
    if (!WIFEXITED(status))
      return -1;
    if (WIFSIGNALED(status))
      con_out("got signaled!\n");

    mem_d(data);

    return status ? 1 : 0;
}

#define TASK_COMPILE    0
#define TASK_EXECUTE    1
  
                        
                                                                         
                                                                        
                                                                           
                                                                          
                                                                       
                           
  
                                                                     
                         
  
                                                                         
                                                                         
                                                                            
              
  
                                                     
  
          
                                                                       
                                               
  
          
                                                                       
                             
                        
                                                         
                        
                                                               
                     
                                                               
                                                                
  
                                                            
  
          
                                                                      
                                                       
  
                                                                        
                                                 
  
          
                                                                        
                                                                       
                                            
  
          
                                                                         
                                                                        
                                                                              
                                                           
  
          
                                                                             
                                              
  
  
          
                                                                           
                                       
  
                                                                          
                                           
  
                                                                           
                                      
  
                                                                       
                                                                             
                                             
   
struct task_template_t {
    char *description;
    char *compileflags;
    char *executeflags;
    char *proceduretype;
    char *sourcefile;
    char *tempfilename;
    std::vector<char *> comparematch;
    char *rulesfile;
    char *testflags;
};

  
                                                                        
                                                     
   
static bool task_template_generate(task_template_t *tmpl, char tag, const char *file, size_t line, char *value, size_t *pad) {
    size_t desclen = 0;
    size_t filelen = 0;
    char **destval = nullptr;

    if (!tmpl)
        return false;

    switch(tag) {
        case 'D': destval = &tmpl->description;    break;
        case 'T': destval = &tmpl->proceduretype;  break;
        case 'C': destval = &tmpl->compileflags;   break;
        case 'E': destval = &tmpl->executeflags;   break;
        case 'I': destval = &tmpl->sourcefile;     break;
        case 'F': destval = &tmpl->testflags;      break;
        default:
            con_printmsg(LVL_ERROR, __FILE__, __LINE__, 0, "internal error",
                "invalid tag `%c:` during code generation\n",
                tag
            );
            return false;
    }

      
                                                          
                      
       
    if (*destval) {
        con_printmsg(LVL_ERROR, file, line, 0,                            "compile error",
            "tag `%c:` already assigned value: %s\n",
            tag, *destval
        );
        return false;
    }

      
                                                                         
                         
       
    if (value && *value && (*value == ' ' || *value == '\t'))
        value++;
    else if (!value)
        exit(EXIT_FAILURE);

      
                                                                          
                                                  
       
    if (strchr(value, '\n'))
        *strrchr(value, '\n')='\0';

      
                                                                        
                                                               
       
    *destval = util_strdup(value);


    if (*destval == tmpl->description) {
          
                                                               
                                      
           
        if ((desclen = strlen(tmpl->description)) > pad[0])
            pad[0] = desclen;
    }

    if ((filelen = strlen(file)) > pad[2])
        pad[2] = filelen;

    return true;
}

static bool task_template_parse(const char *file, task_template_t *tmpl, FILE *fp, size_t *pad) {
    char  *data = nullptr;
    char  *back = nullptr;
    size_t size = 0;
    size_t line = 1;

    if (!tmpl)
        return false;

                          
    while (util_getline(&back, &size, fp) != EOF) {
                             
        data = back;
        if (*data && (*data == ' ' || *data == '\t'))
            data++;

        switch (*data) {
              
                                                                    
                                             
               
            case '/':
                if (data[1] != '/') {
                    con_printmsg(LVL_ERROR, file, line, 0,                            "tmpl parse error",
                        "invalid character `/`, perhaps you meant `//` ?");

                    mem_d(back);
                    return false;
                }
            case '#':
                break;

              
                                                                            
                                                                       
                                         
               
            case '\r':
            case '\n':
                break;


              
                                                                          
                     
               
            case 'D':
            case 'T':
            case 'C':
            case 'E':
            case 'I':
            case 'F':
                if (data[1] != ':') {
                    con_printmsg(LVL_ERROR, file, line, 0,                            "tmpl parse error",
                        "expected `:` after `%c`",
                        *data
                    );
                    goto failure;
                }
                if (!task_template_generate(tmpl, *data, file, line, &data[3], pad)) {
                    con_printmsg(LVL_ERROR, file, line, 0,                            "tmpl compile error",
                        "failed to generate for given task\n"
                    );
                    goto failure;
                }
                break;

              
                                                                         
                                       
               
            case 'M':
            {
                char *value = &data[3];
                if (data[1] != ':') {
                    con_printmsg(LVL_ERROR, file, line, 0,                            "tmpl parse error",
                        "expected `:` after `%c`",
                        *data
                    );
                    goto failure;
                }

                  
                                                                                      
                                                              
                   
                if (strrchr(value, '\n'))
                    *strrchr(value, '\n')='\0';
                else                                                  
                    exit(EXIT_FAILURE);

                tmpl->comparematch.push_back(util_strdup(value));

                break;
            }

            default:
                con_printmsg(LVL_ERROR, file, line, 0,                            "tmpl parse error",
                    "invalid tag `%c`", *data
                );
                goto failure;
                                   
        }

                                           
        line++;
        mem_d(back);
        back = nullptr;
    }
    if (back)
        mem_d(back);
    return true;

failure:
    mem_d (back);
    return false;
}

  
                                                                   
                     
   
static void task_template_nullify(task_template_t *tmpl) {
    if (!tmpl)
        return;

    tmpl->description = nullptr;
    tmpl->proceduretype = nullptr;
    tmpl->compileflags = nullptr;
    tmpl->executeflags = nullptr;
    tmpl->sourcefile = nullptr;
    tmpl->tempfilename = nullptr;
    tmpl->rulesfile = nullptr;
    tmpl->testflags = nullptr;
}

static task_template_t *task_template_compile(const char *file, const char *dir, size_t *pad) {
                                 
    char             fullfile[4096];
    size_t           filepadd = 0;
    FILE       *tempfile = nullptr;
    task_template_t *tmpl     = nullptr;

    util_snprintf(fullfile, sizeof(fullfile), "%s/%s", dir, file);

    tempfile = fopen(fullfile, "r");
    tmpl = (task_template_t*)mem_a(sizeof(task_template_t));
    new (tmpl) task_template_t();
    task_template_nullify(tmpl);

      
                                                        
                                                 
       
    if ((filepadd = strlen(fullfile)) > pad[1])
        pad[1] = filepadd;

    tmpl->rulesfile = util_strdup(fullfile);

      
                                                                       
                  
       
    if (!tempfile) {
        con_err("template file: %s does not exist or invalid permissions\n",
            file
        );
        goto failure;
    }

    if (!task_template_parse(file, tmpl, tempfile, pad)) {
        con_err("template parse error: error during parsing\n");
        goto failure;
    }

      
                                                                
         
         
         
         
       
    if (!tmpl->description) {
        con_err("template compile error: %s missing `D:` tag\n", file);
        goto failure;
    }
    if (!tmpl->proceduretype) {
        con_err("template compile error: %s missing `T:` tag\n", file);
        goto failure;
    }
    if (!tmpl->compileflags) {
        con_err("template compile error: %s missing `C:` tag\n", file);
        goto failure;
    }
    if (!tmpl->sourcefile) {
        con_err("template compile error: %s missing `I:` tag\n", file);
        goto failure;
    }

      
                                                                
                                           
       
    if (!strcmp(tmpl->proceduretype, "-compile")) {
        if (tmpl->executeflags)
            con_err("template compile warning: %s erroneous tag `E:` when only compiling\n", file);
        if (tmpl->comparematch.size())
            con_err("template compile warning: %s erroneous tag `M:` when only compiling\n", file);
        goto success;
    } else if (!strcmp(tmpl->proceduretype, "-execute")) {
        if (!tmpl->executeflags) {
                                  
            tmpl->executeflags = util_strdup("$null");
        }
        if (tmpl->comparematch.empty()) {
            con_err("template compile error: %s missing `M:` tag (use `$null` for exclude)\n", file);
            goto failure;
        }
    } else if (!strcmp(tmpl->proceduretype, "-fail")) {
        if (tmpl->executeflags)
            con_err("template compile warning: %s erroneous tag `E:` when only failing\n", file);
        if (tmpl->comparematch.size())
            con_err("template compile warning: %s erroneous tag `M:` when only failing\n", file);
    } else if (!strcmp(tmpl->proceduretype, "-diagnostic")) {
        if (tmpl->executeflags)
            con_err("template compile warning: %s erroneous tag `E:` when only diagnostic\n", file);
        if (tmpl->comparematch.empty()) {
            con_err("template compile error: %s missing `M:` tag (use `$null` for exclude)\n", file);
            goto failure;
        }
    } else if (!strcmp(tmpl->proceduretype, "-pp")) {
        if (tmpl->executeflags)
            con_err("template compile warning: %s erroneous tag `E:` when only preprocessing\n", file);
        if (tmpl->comparematch.empty()) {
            con_err("template compile error: %s missing `M:` tag (use `$null` for exclude)\n", file);
            goto failure;
        }
    } else {
        con_err("template compile error: %s invalid procedure type: %s\n", file, tmpl->proceduretype);
        goto failure;
    }

success:
    fclose(tempfile);
    return tmpl;

failure:
      
                                                                         
                                                             
       
    if (tempfile)
        fclose(tempfile);
    mem_d(tmpl);

    return nullptr;
}

static void task_template_destroy(task_template_t *tmpl) {
    if (!tmpl)
        return;

    if (tmpl->description)    mem_d(tmpl->description);
    if (tmpl->proceduretype)  mem_d(tmpl->proceduretype);
    if (tmpl->compileflags)   mem_d(tmpl->compileflags);
    if (tmpl->executeflags)   mem_d(tmpl->executeflags);
    if (tmpl->sourcefile)     mem_d(tmpl->sourcefile);
    if (tmpl->rulesfile)      mem_d(tmpl->rulesfile);
    if (tmpl->testflags)      mem_d(tmpl->testflags);


    for (auto &it : tmpl->comparematch)
        mem_d(it);

      
                                                                     
                                                  
       
    mem_d(tmpl->tempfilename);
    mem_d(tmpl);
}

  
                                                                         
                                                                          
   
struct task_t {
    task_template_t *tmpl;
    FILE **runhandles;
    FILE *stderrlog;
    FILE *stdoutlog;
    char *stdoutlogfile;
    char *stderrlogfile;
    bool compiled;
};

static std::vector<task_t> task_tasks;

  
                                                             
                                        
   
static bool task_propagate(const char *curdir, size_t *pad, const char *defs) {
    bool  success = true;
    DIR *dir;
    struct dirent *files;
    struct stat directory;
    char buffer[4096];
    size_t found = 0;
    std::vector<char *> directories;
    char *claim = util_strdup(curdir);

    directories.push_back(claim);
    dir = opendir(claim);

      
                                                                         
                      
       
    while ((files = readdir(dir))) {
        util_asprintf(&claim, "%s/%s", curdir, files->d_name);
        if (stat(claim, &directory) == -1) {
            closedir(dir);
            mem_d(claim);
            return false;
        }

        if (S_ISDIR(directory.st_mode) && files->d_name[0] != '.') {
            directories.push_back(claim);
        } else {
            mem_d(claim);
            claim = nullptr;
        }
    }
    closedir(dir);

      
                                                                  
                                                                   
                            
       
    for (auto &it : directories) {
        dir = opendir(it);
        while ((files = readdir(dir))) {
            util_snprintf(buffer, sizeof(buffer), "%s/%s", it, files->d_name);
            if (stat(buffer, &directory) == -1) {
                con_err("internal error: stat failed, aborting\n");
                abort();
            }

            if (S_ISDIR(directory.st_mode))
                continue;

              
                                                                         
                                                            
               
            if (strcmp(files->d_name + strlen(files->d_name) - 5, ".tmpl") == 0) {
                task_template_t *tmpl = task_template_compile(files->d_name, it, pad);
                char             buf[4096];                                
                const char      *qcflags = nullptr;
                task_t           task;

                memset(&task, 0, sizeof(task));

                found ++;
                if (!tmpl) {
                    con_err("error compiling task template: %s\n", files->d_name);
                    success = false;
                    continue;
                }
                  
                                                                        
                                                            
                   
                tmpl->tempfilename = nullptr;
                util_asprintf(&tmpl->tempfilename, "%s/TMPDAT.%s.dat", it, files->d_name);

                  
                                                                     
                                                                         
                                                                           
                   
                qcflags = getenv("QCFLAGS");

                  
                                                                            
                                                                         
                                                  
                   
                if (strcmp(tmpl->proceduretype, "-pp")) {
                    if (qcflags) {
                        if (tmpl->testflags && !strcmp(tmpl->testflags, "-no-defs")) {
                            util_snprintf(buf, sizeof(buf), "%s %s/%s %s %s -o %s",
                                task_bins[TASK_COMPILE],
                                it,
                                tmpl->sourcefile,
                                qcflags,
                                tmpl->compileflags,
                                tmpl->tempfilename
                            );
                        } else {
                            util_snprintf(buf, sizeof(buf), "%s %s/%s %s/%s %s %s -o %s",
                                task_bins[TASK_COMPILE],
                                curdir,
                                defs,
                                it,
                                tmpl->sourcefile,
                                qcflags,
                                tmpl->compileflags,
                                tmpl->tempfilename
                            );
                        }
                    } else {
                        if (tmpl->testflags && !strcmp(tmpl->testflags, "-no-defs")) {
                            util_snprintf(buf, sizeof(buf), "%s %s/%s %s -o %s",
                                task_bins[TASK_COMPILE],
                                it,
                                tmpl->sourcefile,
                                tmpl->compileflags,
                                tmpl->tempfilename
                            );
                        } else {
                            util_snprintf(buf, sizeof(buf), "%s %s/%s %s/%s %s -o %s",
                                task_bins[TASK_COMPILE],
                                curdir,
                                defs,
                                it,
                                tmpl->sourcefile,
                                tmpl->compileflags,
                                tmpl->tempfilename
                            );
                        }
                    }
                } else {
                                                                                        
                    if (tmpl->testflags && !strcmp(tmpl->testflags, "-no-defs")) {
                        util_snprintf(buf, sizeof(buf), "%s -E %s/%s %s -o %s",
                            task_bins[TASK_COMPILE],
                            it,
                            tmpl->sourcefile,
                            tmpl->compileflags,
                            tmpl->tempfilename
                        );
                    } else {
                        util_snprintf(buf, sizeof(buf), "%s -E %s/%s %s/%s %s -o %s",
                            task_bins[TASK_COMPILE],
                            curdir,
                            defs,
                            it,
                            tmpl->sourcefile,
                            tmpl->compileflags,
                            tmpl->tempfilename
                        );
                    }
                }

                  
                                                                              
                                                                   
                   
                task.tmpl = tmpl;
                if (!(task.runhandles = task_popen(buf, "r"))) {
                    con_err("error opening pipe to process for test: %s\n", tmpl->description);
                    success = false;
                    continue;
                }

                  
                                                                             
                              
                   
                util_snprintf(buf, sizeof(buf), "%s.stdout", tmpl->tempfilename);
                task.stdoutlogfile = util_strdup(buf);
                if (!(task.stdoutlog = fopen(buf, "w"))) {
                    con_err("error opening %s for stdout\n", buf);
                    continue;
                }

                util_snprintf(buf, sizeof(buf), "%s.stderr", tmpl->tempfilename);
                task.stderrlogfile = util_strdup(buf);
                if (!(task.stderrlog = fopen(buf, "w"))) {
                    con_err("error opening %s for stderr\n", buf);
                    continue;
                }
                task_tasks.push_back(task);
            }
        }
        closedir(dir);
        mem_d(it);                          
    }
    return success;
}

  
                                                                    
                                                        
   
static void task_precleanup(const char *curdir) {
    DIR     *dir;
    struct dirent  *files;
    char          buffer[4096];

    dir = opendir(curdir);

    while ((files = readdir(dir))) {
        if (strstr(files->d_name, "TMP")     ||
            strstr(files->d_name, ".stdout") ||
            strstr(files->d_name, ".stderr") ||
            strstr(files->d_name, ".dat"))
        {
            util_snprintf(buffer, sizeof(buffer), "%s/%s", curdir, files->d_name);
            if (remove(buffer))
                con_err("error removing temporary file: %s\n", buffer);
        }
    }

    closedir(dir);
}

static void task_destroy(void) {
      
                                                                     
                                                                     
                       
       
    for (auto &it : task_tasks) {
          
                                                                          
                                                        
           
        if (it.stdoutlog) fclose(it.stdoutlog);
        if (it.stderrlog) fclose(it.stderrlog);

          
                                                                            
                                                                           
                                                                          
           
        if (it.compiled || !strcmp(it.tmpl->proceduretype, "-fail")) {
            if (remove(it.stdoutlogfile))
                con_err("error removing stdout log file: %s\n", it.stdoutlogfile);
            if (remove(it.stderrlogfile))
                con_err("error removing stderr log file: %s\n", it.stderrlogfile);

            (void)!remove(it.tmpl->tempfilename);
        }

                                                 
        mem_d(it.stdoutlogfile);
        mem_d(it.stderrlogfile);

        task_template_destroy(it.tmpl);
    }
}

  
                                                                  
                                                                    
                                                                   
                           
   
static bool task_trymatch(task_t &task, std::vector<char *> &line) {
    bool success = true;
    bool process = true;
    int retval = EXIT_SUCCESS;
    FILE *execute;
    char buffer[4096];
    task_template_t *tmpl = task.tmpl;

    memset(buffer,0,sizeof(buffer));

    if (!strcmp(tmpl->proceduretype, "-execute")) {
          
                                                              
                              
           
        if (!strcmp(tmpl->executeflags, "$null")) {
            util_snprintf(buffer,  sizeof(buffer), "%s %s",
                task_bins[TASK_EXECUTE],
                tmpl->tempfilename
            );
        } else {
            util_snprintf(buffer,  sizeof(buffer), "%s %s %s",
                task_bins[TASK_EXECUTE],
                tmpl->executeflags,
                tmpl->tempfilename
            );
        }

        execute = popen(buffer, "r");
        if (!execute)
            return false;
    } else if (!strcmp(tmpl->proceduretype, "-pp")) {
          
                                                               
                                                           
           
        if (!(execute = fopen(tmpl->tempfilename, "r")))
            return false;
        process = false;
    } else {
          
                                                                  
                                                                     
                            
           
        if (!(execute = fopen(task.stderrlogfile, "r")))
            return false;
        process = false;
    }

      
                                                                        
                              
       
    {
        char  *data    = nullptr;
        size_t size    = 0;
        size_t compare = 0;

        while (util_getline(&data, &size, execute) != EOF) {
            if (!strcmp(data, "No main function found\n")) {
                con_err("test failure: `%s` (No main function found) [%s]\n",
                    tmpl->description,
                    tmpl->rulesfile
                );
                if (!process)
                    fclose(execute);
                else
                    pclose((FILE*)execute);
                return false;
            }

              
                                                                     
                                                    
               
            if  (strrchr(data, '\n'))
                *strrchr(data, '\n') = '\0';

              
                                                                    
                                                       
               
            if(!strcmp(tmpl->proceduretype, "-diagnostic")) {
                if (strstr(data, "there have been errors, bailing out"))
                    continue;                
                if (strstr(data, ": error: ")) {
                    char *claim = util_strdup(data + (strstr(data, ": error: ") - data) + 9);
                    mem_d(data);
                    data = claim;
                }
            }

              
                                                                                      
                                                                                   
                                                                                          
               
            if (!strcmp(tmpl->proceduretype, "-pp") && !*data)
                continue;

            if (tmpl->comparematch.size() > compare) {
                if (strcmp(data, tmpl->comparematch[compare++])) {
                    success = false;
                }
            } else {
                success = false;
            }

            line.push_back(data);

                       
            data = nullptr;
            size = 0;
        }

        if (compare != tmpl->comparematch.size())
            success = false;

        mem_d(data);
        data = nullptr;
    }

    if (process)
        retval = pclose((FILE*)execute);
    else
        fclose(execute);

    return success && retval == EXIT_SUCCESS;
}

static const char *task_type(task_template_t *tmpl) {
    if (!strcmp(tmpl->proceduretype, "-pp"))
        return "type: preprocessor";
    if (!strcmp(tmpl->proceduretype, "-execute"))
        return "type: execution";
    if (!strcmp(tmpl->proceduretype, "-compile"))
        return "type: compile";
    if (!strcmp(tmpl->proceduretype, "-diagnostic"))
        return "type: diagnostic";
    return "type: fail";
}

  
                                                                  
                                                                      
                                                                    
                                     
   
#include <math.h>
static size_t task_schedualize(size_t *pad) {
    char space[2][64];
    bool execute = false;
    char *data = nullptr;
    std::vector<char *> match;
    size_t size = 0;
    size_t i = 0;
    size_t failed = 0;
    int status = 0;

    util_snprintf(space[0], sizeof(space[0]), "%d", (int)task_tasks.size());

    for (auto &it : task_tasks) {
        i++;
        memset(space[1], 0, sizeof(space[1]));
        util_snprintf(space[1], sizeof(space[1]), "%d", (int)(i));

        con_out("test #%u %*s", i, strlen(space[0]) - strlen(space[1]), "");
                                
                                                                                                           
                                      
                             

          
                                                                    
                    
           

                                                                                      
        execute = !! (!strcmp(it.tmpl->proceduretype, "-execute")) ||
                     (!strcmp(it.tmpl->proceduretype, "-pp"))      ||
                     (!strcmp(it.tmpl->proceduretype, "-diagnostic"));

          
                                                                          
                              
           
        it.compiled = true;

          
                                                                          
                                          
           
        while (util_getline(&data, &size, it.runhandles[1]) != EOF) {
            fputs(data, it.stdoutlog);

            if (strstr(data, "failed to open file")) {
                it.compiled = false;
                execute                = false;
            }
        }
        while (util_getline(&data, &size, it.runhandles[2]) != EOF) {
              
                                                                       
                               
              
                                                                      
                                                                       
                                               
               
            if (strstr(data, "error") && strcmp(it.tmpl->proceduretype, "-diagnostic")) {
                execute                = false;
                it.compiled = false;
            }

            fputs(data, it.stderrlog);
            fflush(it.stderrlog);                          
        }

        if (!it.compiled && strcmp(it.tmpl->proceduretype, "-fail")) {
            con_out("failure:   `%s` %*s %*s\n",
                it.tmpl->description,
                (pad[0] + pad[1] - strlen(it.tmpl->description)) + (strlen(it.tmpl->rulesfile) - pad[1]),
                it.tmpl->rulesfile,
                (pad[1] + pad[2] - strlen(it.tmpl->rulesfile)) + (strlen("(failed to compile)") - pad[2]),
                "(failed to compile)"
            );
            failed++;
            continue;
        }

        status = task_pclose(it.runhandles);
        if (status != 0 && status != 1) {
            con_out("compiler failure (returned: %i):   `%s` %*s\n",
                status,
                it.tmpl->description,
                (pad[0] + pad[1] - strlen(it.tmpl->description)) + (strlen(it.tmpl->rulesfile) - pad[1]),
                it.tmpl->rulesfile
            );
            failed++;
            continue;
        }
        if ((!strcmp(it.tmpl->proceduretype, "-fail") && status == EXIT_SUCCESS)
        ||  ( strcmp(it.tmpl->proceduretype, "-fail") && status == EXIT_FAILURE)) {
            con_out("failure:   `%s` %*s %*s\n",
                it.tmpl->description,
                (pad[0] + pad[1] - strlen(it.tmpl->description)) + (strlen(it.tmpl->rulesfile) - pad[1]),
                it.tmpl->rulesfile,
                (pad[1] + pad[2] - strlen(it.tmpl->rulesfile)) + (strlen("(compiler didn't return exit success)") - pad[2]),
                "(compiler didn't return exit success)"
            );
            failed++;
            continue;
        }

        if (!execute) {
            con_out("succeeded: `%s` %*s %*s\n",
                it.tmpl->description,
                (pad[0] + pad[1] - strlen(it.tmpl->description)) + (strlen(it.tmpl->rulesfile) - pad[1]),
                it.tmpl->rulesfile,
                (pad[1] + pad[2] - strlen(it.tmpl->rulesfile)) + (strlen(task_type(it.tmpl)) - pad[2]),
                task_type(it.tmpl)

            );
            continue;
        }

          
                                                                       
                                                                      
                       
           
        if (!task_trymatch(it, match)) {
            size_t d = 0;

            con_out("failure:   `%s` %*s %*s\n",
                it.tmpl->description,
                (pad[0] + pad[1] - strlen(it.tmpl->description)) + (strlen(it.tmpl->rulesfile) - pad[1]),
                it.tmpl->rulesfile,
                (pad[1] + pad[2] - strlen(it.tmpl->rulesfile)) + (strlen(
                    (strcmp(it.tmpl->proceduretype, "-pp"))
                        ? "(invalid results from execution)"
                        : (strcmp(it.tmpl->proceduretype, "-diagnostic"))
                            ? "(invalid results from preprocessing)"
                            : "(invalid results from compiler diagnsotics)"
                ) - pad[2]),
                (strcmp(it.tmpl->proceduretype, "-pp"))
                    ? "(invalid results from execution)"
                    : (strcmp(it.tmpl->proceduretype, "-diagnostic"))
                            ? "(invalid results from preprocessing)"
                            : "(invalid results from compiler diagnsotics)"
            );

              
                                                                           
                                                                             
                                                         
               
            con_out("    Expected From %u Matches: (got %u Matches)\n",
                it.tmpl->comparematch.size(),
                match.size()
            );
            for (; d < it.tmpl->comparematch.size(); d++) {
                char *select = it.tmpl->comparematch[d];
                size_t length = 60 - strlen(select);
                con_out("        Expected: \"%s\"", select);
                while (length --)
                    con_out(" ");
                con_out("| Got: \"%s\"\n", (d >= match.size()) ? "<<nothing else to compare>>" : match[d]);
            }

              
                                                                                
                                                                                  
                         
               
            if (match.size() > it.tmpl->comparematch.size()) {
                for (d = 0; d < match.size() - it.tmpl->comparematch.size(); d++) {
                    con_out("        Expected: Nothing                                                       | Got: \"%s\"\n",
                        match[d + it.tmpl->comparematch.size()]
                    );
                }
            }

            for (auto &it : match)
                mem_d(it);
            match.clear();
            failed++;
            continue;
        }

        for (auto &it : match)
            mem_d(it);
        match.clear();

        con_out("succeeded: `%s` %*s %*s\n",
            it.tmpl->description,
            (pad[0] + pad[1] - strlen(it.tmpl->description)) + (strlen(it.tmpl->rulesfile) - pad[1]),
            it.tmpl->rulesfile,
            (pad[1] + pad[2] - strlen(it.tmpl->rulesfile)) + (strlen(task_type(it.tmpl))- pad[2]),
            task_type(it.tmpl)

        );
    }
    mem_d(data);
    return failed;
}

  
                                                                     
                                                                     
                                                                       
                                                                   
                                                                    
                                                                     
                     
  
                                                                     
         
  
                                                
   
static GMQCC_WARN bool test_perform(const char *curdir, const char *defs) {
    size_t             failed       = false;
    static const char *default_defs = "defs.qh";

    size_t pad[] = {
                                                                                          
                    0,                                 0,                        0
    };

      
                                                                     
                                                    
       
    if (!defs) {
        defs = default_defs;
    }


    task_precleanup(curdir);
    if (!task_propagate(curdir, pad, defs)) {
        con_err("error: failed to propagate tasks\n");
        task_destroy();
        return false;
    }
      
                                                                         
                                                                        
                                                                         
                                                                            
              
       
    failed = task_schedualize(pad);
    if (failed)
        con_out("%u out of %u tests failed\n", failed, task_tasks.size());
    task_destroy();

    return (failed) ? false : true;
}

  
                                                                  
                                                                   
                                            
   
static bool parsecmd(const char *optname, int *argc_, char ***argv_, char **out, int ds, bool split) {
    int  argc   = *argc_;
    char **argv = *argv_;

    size_t len = strlen(optname);

    if (strncmp(argv[0]+ds, optname, len))
        return false;

                                                             
    if (argv[0][ds+len] == '=') {
        *out = argv[0]+ds+len+1;
        return true;
    }

    if (!split || argc < ds)                                                                  
        return false;

                           
    *out = argv[1];
    --*argc_;
    ++*argv_;
    return true;
}

int main(int argc, char **argv) {
    bool succeed  = false;
    char *defs = nullptr;

    con_init();

      
                                                                        
                                      
       
    while (argc > 1) {
        ++argv;
        --argc;

        if (argv[0][0] == '-') {
            if (parsecmd("defs", &argc, &argv, &defs, 1, false))
                continue;

            if (!strcmp(argv[0]+1, "debug")) {
                OPTS_OPTION_BOOL(OPTION_DEBUG) = true;
                continue;
            }
            if (!strcmp(argv[0]+1, "nocolor")) {
                con_color(0);
                continue;
            }

            con_err("invalid argument %s\n", argv[0]+1);
            return -1;
        }
    }
    succeed = test_perform("tests", defs);

    return (succeed) ? EXIT_SUCCESS : EXIT_FAILURE;
}
