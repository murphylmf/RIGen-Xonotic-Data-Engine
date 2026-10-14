#include "quake.qh"

#include <common/stats.qh>
#include <common/weapons/_all.qh>
#include <common/weapons/_all.qh>

                        
                                                                             
                        
                                    
                                         
  

SPAWNFUNC_WEAPON(weapon_supernailgun, WEP_HAGAR)
SPAWNFUNC_WEAPON(weapon_supershotgun, WEP_MACHINEGUN)

SPAWNFUNC_ITEM(item_spikes, ITEM_Bullets)
SPAWNFUNC_ITEM(item_armor2, ITEM_ArmorMega)
SPAWNFUNC_ITEM(item_armorInv, ITEM_ArmorMega)                                         
SPAWNFUNC_ITEM_COND(item_health, (this.spawnflags & 2), ITEM_HealthMega, ITEM_HealthMedium)
