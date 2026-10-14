entity self;
.float f;
..float fp;
...float fpp;

void try(entity e, ...float pp) {
    print("and: ", ftos( e.(e.(e.pp)) ), "\n");
}

typedef float Float;

void try2(entity e, ...Float pp) {
    print("and: ", ftos( e.(e.(e.pp)) ), "\n");
}

                                                 

void main() {
    self = spawn();
    self.f = 123;
    self.fp = f;
    self.fpp = fp;
    print(ftos(  self.(self.fp)  ), "\n");
    print(ftos(  self.(self.(self.fpp))  ), "\n");
    try(self, fpp);
    try2(self, fpp);
}
