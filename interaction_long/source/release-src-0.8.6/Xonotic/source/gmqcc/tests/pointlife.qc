var float foo = 0;

void funcall() {}
void bar(string str) {}

void main(string str) {
    string pl;

    if (foo)
        return;                                           
                                                              
    pl = "Got overwritten!\n";                 

    print(str);

    pl = "Kill the lifrange here";                 
    funcall();                                              
    bar(pl);                           
}
