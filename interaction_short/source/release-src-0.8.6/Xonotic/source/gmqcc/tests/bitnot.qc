void main() {
    float a; a = 1;
    float b; b = 1;
    float c; c = 1;
    float d; d = 1;
    vector e; e = '1 1 1';
    vector f; f = '1 1 1';

#ifdef __STD_FTEQCC__
    a &~= 1;     
#else
    a &= ~1;     
#endif
#ifdef __STD_GMQCC__
    b &= ~1;     
    c &= ~d;     
#else
    b &~= 1;     
    c &~= 1;     
#endif
#ifdef __STD_FTEQCC__
    f &~= e;           
#else
    f &= ~e;           
#endif
#ifdef __STD_GMQCC__
    e &= ~e;           
#else
    e &~= e;           
#endif

    print("a: ", ftos(a), "\nb: ",
                 ftos(b), "\nc: ",
                 ftos(c), "\n");
    print("e: ", vtos(e), "\n");
    print("f: ", vtos(f), "\n");
}
