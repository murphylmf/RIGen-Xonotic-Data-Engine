#include "teleport.qh"
REGISTER_NET_LINKED(ENT_CLIENT_TRIGGER_TELEPORT)

#ifdef SVQC
void trigger_teleport_use(entity this, entity actor, entity trigger)
{
	if(teamplay)
		this.team = actor.team;
#ifdef SVQC
	this.SendFlags |= SF_TRIGGER_UPDATE;
#endif
}
#endif

bool Teleport_Active(entity this, entity player)
{
	if (this.active != ACTIVE_ACTIVE)
		return false;

#ifdef SVQC
	if (!player.teleportable)
		return false;

	if(player.vehicle)
	if(!player.vehicle.teleportable)
		return false;

	if(IS_TURRET(player))
		return false;
#elif defined(CSQC)
	if(!IS_PLAYER(player))
		return false;
#endif

	if(IS_DEAD(player))
		return false;

	if(this.team)
		if(((this.spawnflags & INVERT_TEAMS) == 0) == (DIFF_TEAM(this, player)))
			return false;

	                                                                                                                
	if(this.classname == "trigger_teleport" && this.spawnflags & TELEPORT_OBSERVERS_ONLY)
		return false;

	return true;
}

void Teleport_Touch(entity this, entity toucher)
{
	entity player = toucher;

	if(!Teleport_Active(this, player))
		return;

	EXACTTRIGGER_TOUCH(this, player);

#ifdef SVQC
	if(IS_PLAYER(player))
		RemoveGrapplingHooks(player);
#endif

	entity e;
	e = Simple_TeleportPlayer(this, player);

#ifdef SVQC
	string s = this.target; this.target = string_null;
	SUB_UseTargets(this, player, player);                                                     
	if (!this.target) this.target = s;

	SUB_UseTargets(e, player, player);
#endif
}

#ifdef SVQC
void target_teleport_use(entity this, entity actor, entity trigger)
{
	entity player = actor;

	if(!Teleport_Active(this, player))
		return;

	if(IS_PLAYER(player))
		RemoveGrapplingHooks(player);

	entity e = Simple_TeleportPlayer(this, player);

	string s = this.target; this.target = string_null;
	SUB_UseTargets(this, player, player);                                                     
	if (!this.target)
	{
		this.target = s;
	}

	if(e != this)                                                              
		SUB_UseTargets(e, player, player);
}
#endif

#ifdef SVQC
float trigger_teleport_send(entity this, entity to, float sf)
{
	WriteHeader(MSG_ENTITY, ENT_CLIENT_TRIGGER_TELEPORT);

	WriteByte(MSG_ENTITY, this.team);
	WriteInt24_t(MSG_ENTITY, this.spawnflags);
	WriteByte(MSG_ENTITY, this.active);
	WriteCoord(MSG_ENTITY, this.speed);

	trigger_common_write(this, true);

	return true;
}

void trigger_teleport_link(entity this)
{
	                                            
}

spawnfunc(trigger_teleport)
{
	this.angles = '0 0 0';

	this.active = ACTIVE_ACTIVE;
	EXACTTRIGGER_INIT;
	this.use = trigger_teleport_use;

	if(this.noise != "")
		FOREACH_WORD(this.noise, true, precache_sound(it));

	                                                               
	InitializeEntity(this, teleport_findtarget, INITPRIO_FINDTARGET);

	if (!this.target || this.target == "")
	{
		objerror (this, "Teleporter with no target");
		return;
	}

	IL_PUSH(g_teleporters, this);
}

void target_teleporter_checktarget(entity this)
{
	                                                 
	                                                                                

	if(!this.target || this.target == "")
	{
		                                       
		                                                                             
		bool is_teleporter_target = false;
		                                                                                                             
		FOREACH_ENTITY_STRING(target, this.targetname,
		{
			if(it.classname == "trigger_teleport" || it.classname == "target_teleporter")
			{
				is_teleporter_target = true;
				break;                                                        
			}
		});

		if(is_teleporter_target)
		{
			                                                                            
			spawnfunc_info_teleport_destination(this);
			return;
		}

		                                                                          
		this.enemy = this;
		this.mangle = this.angles;
		this.angles = '0 0 0';
	}

	                                                                                       

	this.active = ACTIVE_ACTIVE;
	this.use = target_teleport_use;

	if(this.noise && this.noise != "")
		FOREACH_WORD(this.noise, true, precache_sound(it));

	if(this.target && this.target != "")                                                                                                          
		teleport_findtarget(this);
}

spawnfunc(target_teleporter)
{
	InitializeEntity(this, target_teleporter_checktarget, INITPRIO_FINDTARGET);
}
#elif defined(CSQC)
NET_HANDLE(ENT_CLIENT_TRIGGER_TELEPORT, bool isnew)
{
	this.classname = "trigger_teleport";
	if(isnew)
		IL_PUSH(g_teleporters, this);
	int mytm = ReadByte();
	if(mytm)
	{
		this.team = mytm - 1;
	}
	this.spawnflags = ReadInt24_t();
	this.active = ReadByte();
	this.speed = ReadCoord();

	trigger_common_read(this, true);

	this.entremove = trigger_remove_generic;
	this.solid = SOLID_TRIGGER;
	                                     
	this.move_time = time;
	defer(this, 0.25, teleport_findtarget);

	return true;
}

#endif
