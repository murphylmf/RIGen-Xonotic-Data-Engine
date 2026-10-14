const string a = "hello world";      
float b[] = { 1, 2, 3 };            
float c[5] = { 5, 4, 3, 2, 1 };     
const float d[] = { 1 };            

void main() {
    print(ftos(_length a), "\n");      
    print(ftos(_length b), "\n");     
    print(ftos(_length c), "\n");     
    print(ftos(_length d), "\n");     

    static float al = _length(a);
    static float bl = _length(b);
    static float cl = _length(c);
    static float dl = _length(d);

    print(ftos(al), "\n");      
    print(ftos(bl), "\n");     
    print(ftos(cl), "\n");     
    print(ftos(dl), "\n");     

    print(ftos(_length "hello world"), "\n");      
}
