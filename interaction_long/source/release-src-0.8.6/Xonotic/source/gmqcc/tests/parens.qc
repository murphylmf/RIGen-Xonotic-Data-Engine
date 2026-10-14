float arr[2];

string gets() { return "S\n"; }
void main(float x) {
    string s;

    s = gets();                           
    print(s);                            
    print("A ", "B\n");                   
    print("A ", "B ", "C\n");                
    print(gets());                                    
    print(gets(), "next\n");                              
    print("-> ", gets());                             
    print(ftos(x), "\n");                             
    print(x ? "xA\n" : "xB\n");                              
    print(!x ? "xA\n" : "xB\n");                              
                  
    arr[0] = 10;
    arr[1] = 11;
                                  
    arr[x ? 0 : 1] += 100;
    print(ftos(arr[0]), "\n");
    print(ftos(arr[1]), "\n");
    print(ftos(arr[x ? 0 : 1]), "\n");
    print(ftos(arr[!x ? 0 : 1]), "\n");

                                 
    float i, j;
    for (i = 0, j = 0; i < x; ++i)
        print("-");
    print("\n");

                          
    if (x ? 1 : 0)
        print("OK\n");
    if (x ? 0 : 1)
        print("NO\n");

                               
    print(("Is this wrong ", "now?\n"));
}
