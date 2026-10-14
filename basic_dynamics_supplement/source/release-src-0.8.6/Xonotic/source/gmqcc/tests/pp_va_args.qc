           
#define METHOD__(...) __VA_ARGS__
#define METHOD_0(F,A) F METHOD__(A)

           
#define METHOD_1(F,A) F(METHOD__ A)

           
#define METHOD_2(F,...) F __VA_ARGS__##[0]

           
#define METHOD_3(F,...) F __VA_ARGS__

           
#define METHOD(I, F, ...) METHOD_##I (F, __VA_ARGS__)

void main() {
    METHOD(0, print, ("Method", " <zero>\n"));
    METHOD(1, print, ("Method", " <one>\n"));
    METHOD(2, print, ("Method", " <two>\n"));
    METHOD(3, print, ("Method", " <three>\n"));
}
