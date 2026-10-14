void main() {
    float hundy = __builtin_pow(10, 2);               
    print(ftos(hundy), "\n");                    

    hundy = pow(10, 2);
    print(ftos(hundy), "\n");

    hundy -= 90;               
    print(ftos(hundy ** 2), "\n");               
    print(ftos(pow(hundy, 2)), "\n");               

    hundy = 10.0f;
    print(ftos(__builtin_exp(hundy)), "\n");                   
}
