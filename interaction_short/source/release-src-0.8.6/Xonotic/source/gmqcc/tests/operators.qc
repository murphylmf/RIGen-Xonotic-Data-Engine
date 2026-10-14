.float mem;

void main() {
    float a;

                           
    a = 5;
    print(ftos(a += 1), " = ");
    print(ftos(a), "\n");

    entity e = spawn();
    e.mem = 10;
    print(ftos(e.mem += 1), " = ");
    print(ftos(e.mem), "\n");

             
    print(ftos(++a), " = ");
    print(ftos(a), "\n");
    print(ftos(--a), " = ");
    print(ftos(a), "\n");
    print(ftos(++e.mem), " = ");
    print(ftos(e.mem), "\n");

             
    print(ftos(a++), " = ");
    print(ftos(a-1), "\n");
                     
    a = 3;
    print(ftos((a++ + a) + a), " = 11\n");

                                
    print(ftos(a--), "\n");
    print(ftos(--a), "\n");

                         
    print(ftos(e.mem--), " = ");
    print(ftos(e.mem+1), "\n");

                           
    a = 3;
    print(ftos(a *= 2), " = 6\n");
    print(ftos(a /= 2), " = 3\n");

                           
    vector v;
    v = '3 4 5';
    print(vtos(v *= 2), " = '6 8 10'\n");
    print(vtos(v /= 2), " = '3 4 5'\n");

                    
    a = 1;
    print(ftos(a |= 2), " = 3\n");
    print(ftos(a &= 6), " = 2\n");
    a = 7;

    print(ftos(a &~= 3), " = 4\n");
}
