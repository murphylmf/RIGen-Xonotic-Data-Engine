#include "gmqcc.h"

  
                                                     
                                                
  
                                                                      
                             
  
                      
                               
                               
                               
  
                                                                    
                               
  
                                                      
                        
                                                                 
  
                                                                
                                               
  
                                                                
             
  
                                                                    
                                                                 
                                 
  
                                                              
                                                               
                                                              
                                                             
  
                                                                  
                                                                        
                         
  
                         
                                                   
   
static const uint32_t utf8_tab[] = {
    0xC0000002, 0xC0000003, 0xC0000004, 0xC0000005, 0xC0000006,
    0xC0000007, 0xC0000008, 0xC0000009, 0xC000000A, 0xC000000B,
    0xC000000C, 0xC000000D, 0xC000000E, 0xC000000F, 0xC0000010,
    0xC0000011, 0xC0000012, 0xC0000013, 0xC0000014, 0xC0000015,
    0xC0000016, 0xC0000017, 0xC0000018, 0xC0000019, 0xC000001A,
    0xC000001B, 0xC000001C, 0xC000001D, 0xC000001E, 0xC000001F,
    0xB3000000, 0xC3000001, 0xC3000002, 0xC3000003, 0xC3000004,
    0xC3000005, 0xC3000006, 0xC3000007, 0xC3000008, 0xC3000009,
    0xC300000A, 0xC300000B, 0xC300000C, 0xD300000D, 0xC300000E,
    0xC300000F, 0xBB0C0000, 0xC30C0001, 0xC30C0002, 0xC30C0003,
    0xD30C0004
};

int utf8_from(char *s, utf8ch_t ch) {
    if (!s)
        return 0;

    if ((unsigned)ch < 0x80) {
        *s = ch;
        return 1;
    } else if ((unsigned)ch < 0x800) {
        *s++ = 0xC0 | (ch >> 6);
        *s   = 0x80 | (ch & 0x3F);
        return 2;
    } else if ((unsigned)ch < 0xD800 || (unsigned)ch - 0xE000 < 0x2000) {
        *s++ = 0xE0 | (ch >> 12);
        *s++ = 0x80 | ((ch >> 6) & 0x3F);
        *s   = 0x80 | (ch & 0x3F);
        return 3;
    } else if ((unsigned)ch - 0x10000 < 0x100000) {
        *s++ = 0xF0 | (ch >> 18);
        *s++ = 0x80 | ((ch >> 12) & 0x3F);
        *s++ = 0x80 | ((ch >> 6) & 0x3F);
        *s   = 0x80 | (ch & 0x3F);
        return 4;
    }
    return 0;
}

int utf8_to(utf8ch_t *i, const unsigned char *s, size_t n) {
    unsigned c,j;

    if (!s || !n)
        return 0;

                                                   
    if (!i)
        i = (utf8ch_t*)(void*)&i;

    if (*s < 0x80)
        return !!(*i = *s);
    if (*s-0xC2U > 0x32)
        return 0;

    c = utf8_tab[*s++-0xC2U];

      
                                        
      
                                                                   
                                                                  
                                           
       
    if (n < 4 && ((c<<(6*n-6)) & (1U << 31)))
        return 0;

      
                                                                          
                                                          
       
    if ((((*s>>3)-0x10)|((*s>>3)+((int32_t)c>>26))) & ~7)
        return 0;

    for (j=2; j<3; j++) {
        if (!((c = c<<6 | (*s++-0x80))&(1U<<31))) {
            *i = c;
            return j;
        }
        if (*s-0x80U >= 0x40)
            return 0;
    }

    *i = c<<6 | (*s++-0x80);
    return 4;
}
