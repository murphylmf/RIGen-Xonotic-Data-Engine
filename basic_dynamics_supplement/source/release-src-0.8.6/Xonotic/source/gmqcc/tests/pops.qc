void main() {
                                                      
    float x = 100;
    float y = 200;
    float z = 300;

                           
    x += 1;
    y += 1;
    z += 1;

    float test_x = (x <=> x + 1);                
    float test_y = (x <=> x);                
    float test_z = (x <=> x - 1);                   

    print(ftos(test_x), "\n");
    print(ftos(test_y), "\n");
    print(ftos(test_z), "\n");
}
