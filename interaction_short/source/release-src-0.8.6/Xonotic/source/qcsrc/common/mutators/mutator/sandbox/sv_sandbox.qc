#include "sv_sandbox.qh"

#include <server/intermission.qh>

string autocvar_g_sandbox;
int autocvar_g_sandbox_info;
bool autocvar_g_sandbox_readonly;
string autocvar_g_sandbox_storage_name;
float autocvar_g_sandbox_storage_autosave;
bool autocvar_g_sandbox_storage_autoload;
float autocvar_g_sandbox_editor_flood;
int autocvar_g_sandbox_editor_maxobjects;
int autocvar_g_sandbox_editor_free;
float autocvar_g_sandbox_editor_distance_spawn;
float autocvar_g_sandbox_editor_distance_edit;
float autocvar_g_sandbox_object_scale_min;
float autocvar_g_sandbox_object_scale_max;
float autocvar_g_sandbox_object_material_velocity_min;
float autocvar_g_sandbox_object_material_velocity_factor;

IntrusiveList g_sandbox_objects;
float autosave_time;
void sandbox_Database_Load();

REGISTER_MUTATOR(sandbox, expr_evaluate(autocvar_g_sandbox))
{
	MUTATOR_ONADD
	{
		g_sandbox_objects = IL_NEW();
		autosave_time = time + autocvar_g_sandbox_storage_autosave;                                     
		if(autocvar_g_sandbox_storage_autoload)
			sandbox_Database_Load();
	}
}

const float MAX_STORAGE_ATTACHMENTS = 16;
float object_count;
.float object_flood;
.entity object_attach;
.string material;

.float touch_timer;
void sandbox_ObjectFunction_Touch(entity this, entity toucher)
{
	                                

	if(!this.material)
		return;
	if(this.touch_timer > time)
		return;                            
	this.touch_timer = time + 0.1;

	                                                              
	float intensity;
	intensity = vlen(this.velocity) + vlen(toucher.velocity);
	if(intensity)                        
		intensity /= 2;                              
	if (!(intensity >= autocvar_g_sandbox_object_material_velocity_min))
		return;                                           
	                                                   
	intensity -= autocvar_g_sandbox_object_material_velocity_min;                                                    
	intensity = bound(0, intensity * autocvar_g_sandbox_object_material_velocity_factor, 1);

	_sound(this, CH_TRIGGER, strcat("object/impact_", this.material, "_", ftos(ceil(random() * 5)) , ".wav"), VOL_BASE * intensity, ATTEN_NORM);
	Send_Effect_(strcat("impact_", this.material), this.origin, '0 0 0', ceil(intensity * 10));                              
}

void sandbox_ObjectFunction_Think(entity this)
{
	                                               
	if(autocvar_g_sandbox_readonly)
		this.grab = 0;               
	else if(autocvar_g_sandbox_editor_free < 2 && this.crypto_idfp)
		this.grab = 1;              
	else
		this.grab = 3;          

	                                                                                                                             
	                                                                                                                  
	                                                                                   

	                          
	FOREACH_CLIENT(IS_PLAYER(it) && IS_REAL_CLIENT(it), {
		if(this.crypto_idfp == it.crypto_idfp)
		{
			this.realowner = it;
			break;
		}
		this.realowner = NULL;
	});

	this.nextthink = time;

	CSQCMODEL_AUTOUPDATE(this);
}

.float old_solid, old_movetype;
entity sandbox_ObjectEdit_Get(entity this, float permissions)
{
	                                                                        
	                                                                                
	                                                        

	crosshair_trace_plusvisibletriggers(this);
	if(vdist(this.origin - trace_ent.origin, >, autocvar_g_sandbox_editor_distance_edit))
		return NULL;                      
	if(trace_ent.classname != "object")
		return NULL;                           
	if(!permissions)
		return trace_ent;                                                        
	if(trace_ent.crypto_idfp == "")
		return trace_ent;                                                                                 
	if (!(trace_ent.realowner != this && autocvar_g_sandbox_editor_free < 2))
		return trace_ent;                                                                                                    
	return NULL;
}

void sandbox_ObjectEdit_Scale(entity e, float f)
{
	e.scale = f;
	if(e.scale)
	{
		e.scale = bound(autocvar_g_sandbox_object_scale_min, e.scale, autocvar_g_sandbox_object_scale_max);
		_setmodel(e, e.model);                                     
		                                                                         
		setsize(e, RoundPerfectVector(e.mins * e.scale), RoundPerfectVector(e.maxs * e.scale));
	}
}

void sandbox_ObjectAttach_Remove(entity e);
void sandbox_ObjectAttach_Set(entity e, entity parent, string s)
{
	                                   

	                                                        
	sandbox_ObjectAttach_Remove(e);

	e.old_solid = e.solid;                    
	e.old_movetype = e.move_movetype;                   
	set_movetype(e, MOVETYPE_FOLLOW);
	e.solid = SOLID_NOT;
	e.takedamage = DAMAGE_NO;

	setattachment(e, parent, s);
	e.owner = parent;
}

void sandbox_ObjectAttach_Remove(entity e)
{
	                                    

	IL_EACH(g_sandbox_objects, it.owner == e,
	{
		vector org = gettaginfo(it, 0);
		setattachment(it, NULL, "");
		it.owner = NULL;

		                                                                             
		setorigin(it, org);
		it.angles = e.angles;                                                

		it.solid = it.old_solid;                              
		set_movetype(it, it.old_movetype);                             
		it.takedamage = DAMAGE_AIM;
	});
}

entity sandbox_ObjectSpawn(entity this, float database)
{
	                                             

	entity e = new(object);
	IL_PUSH(g_sandbox_objects, e);
	e.takedamage = DAMAGE_AIM;
	e.damageforcescale = 1;
	e.solid = SOLID_BBOX;                                                         
	set_movetype(e, MOVETYPE_TOSS);
	e.frame = 0;
	e.skin = 0;
	e.material = string_null;
	settouch(e, sandbox_ObjectFunction_Touch);
	setthink(e, sandbox_ObjectFunction_Think);
	e.nextthink = time;
	                                                                                             

	if(!database)
	{
		                                        
		                                                                                                           
		if(this.crypto_idfp != "")
			e.crypto_idfp = strzone(this.crypto_idfp);
		else
			print_to(this, "^1SANDBOX - WARNING: ^7You spawned an object, but lack a player UID. ^1Your objects are not secured and can be edited by any player!");

		                                
		e.netname = strzone(this.netname);                     
		e.message = strzone(strftime(true, "%d-%m-%Y %H:%M:%S"));                 
		e.message2 = strzone(strftime(true, "%d-%m-%Y %H:%M:%S"));                     

		                                                                   
		makevectors(this.v_angle);
		WarpZone_TraceLine(this.origin + this.view_ofs, this.origin + this.view_ofs + v_forward * autocvar_g_sandbox_editor_distance_spawn, MOVE_NORMAL, this);
		setorigin(e, trace_endpos);
		e.angles_y = this.v_angle.y;
	}

	CSQCMODEL_AUTOINIT(e);

	object_count += 1;
	return e;
}

void sandbox_ObjectRemove(entity e)
{
	sandbox_ObjectAttach_Remove(e);                        

	                                                                                     
	FOREACH_CLIENT(IS_PLAYER(it) && IS_REAL_CLIENT(it) && it.object_attach == e, { it.object_attach = NULL; });

	strfree(e.material);
	strfree(e.crypto_idfp);
	strfree(e.netname);
	strfree(e.message);
	strfree(e.message2);
	delete(e);
	e = NULL;

	object_count -= 1;
}

string port_string[MAX_STORAGE_ATTACHMENTS];                                                    

string sandbox_ObjectPort_Save(entity e, bool database)
{
	                                                      
	int o = 0;

	                                                               
	IL_EACH(g_sandbox_objects, it == e || it.owner == e, LAMBDA(
		                                                                                     
		int slot, physics, solidity;
		if(it == e)                                           
		{
			slot = 0;
			solidity = it.solid;                                                    
			physics = it.move_movetype;                                                  
		}
		else if(it.owner == e)                                    
		{
			o += 1;                         
			slot = o;
			solidity = it.old_solid;                                                      
			physics = it.old_movetype;                                                     
			gettaginfo(it.owner, it.tag_index);                                                                         
		}
		else
			continue;

		                                                                  
		if(slot)
		{
			                                           
			if(gettaginfo_name)
				port_string[slot] = strcat(port_string[slot], "\"", gettaginfo_name, "\" ");
			else
				port_string[slot] = strcat(port_string[slot], "\"\" ");        
		}
		else
		{
			                                            
			if(database)
			{
				port_string[slot] = strcat(port_string[slot], sprintf("\"%.9v\"", it.origin), " ");
				port_string[slot] = strcat(port_string[slot], sprintf("\"%.9v\"", it.angles), " ");
			}
		}
		                                    
		port_string[slot] = strcat(port_string[slot], "\"", it.model, "\" ");
		port_string[slot] = strcat(port_string[slot], ftos(it.skin), " ");
		port_string[slot] = strcat(port_string[slot], ftos(it.alpha), " ");
		port_string[slot] = strcat(port_string[slot], sprintf("\"%.9v\"", it.colormod), " ");
		port_string[slot] = strcat(port_string[slot], sprintf("\"%.9v\"", it.glowmod), " ");
		port_string[slot] = strcat(port_string[slot], ftos(it.frame), " ");
		port_string[slot] = strcat(port_string[slot], ftos(it.scale), " ");
		port_string[slot] = strcat(port_string[slot], ftos(solidity), " ");
		port_string[slot] = strcat(port_string[slot], ftos(physics), " ");
		port_string[slot] = strcat(port_string[slot], ftos(it.damageforcescale), " ");
		if(it.material)
			port_string[slot] = strcat(port_string[slot], "\"", it.material, "\" ");
		else
			port_string[slot] = strcat(port_string[slot], "\"\" ");        
		if(database)
		{
			                                          
			if(it.crypto_idfp)
				port_string[slot] = strcat(port_string[slot], "\"", it.crypto_idfp, "\" ");
			else
				port_string[slot] = strcat(port_string[slot], "\"\" ");        
			port_string[slot] = strcat(port_string[slot], "\"", e.netname, "\" ");
			port_string[slot] = strcat(port_string[slot], "\"", e.message, "\" ");
			port_string[slot] = strcat(port_string[slot], "\"", e.message2, "\" ");
		}
	));

	                                                                               
	string s = "";
	for(int j = 0; j <= MAX_STORAGE_ATTACHMENTS; ++j)
	{
		if(port_string[j])
			s = strcat(s, port_string[j], "; ");
		port_string[j] = string_null;                          
	}

	return s;
}

entity sandbox_ObjectPort_Load(entity this, string s, float database)
{
	                                                           
	int n, i;
	entity e = NULL, parent = NULL;
	string arg = string_null;

	                                         
	n = tokenizebyseparator(s, "; ");
	for(i = 0; i < n; ++i)
		port_string[i] = argv(i);

	                                                       
	for(i = 0; i < n; ++i)
	{
		#define SANDBOX_GETARG arg = argv(++argv_num);
		int argv_num = -1;                                              

		string tagname = string_null;
		tokenize_console(port_string[i]);
		e = sandbox_ObjectSpawn(this, database);

		                                                                  
		if(i)
		{
			                                           
			SANDBOX_GETARG; tagname = (arg != "") ? arg : string_null;
		}
		else
		{
			                                            
			if(database)
			{
				SANDBOX_GETARG; setorigin(e, stov(arg));
				SANDBOX_GETARG; e.angles = stov(arg);
			}
			parent = e;                               
		}
		                                    
		SANDBOX_GETARG; _setmodel(e, arg);
		SANDBOX_GETARG; e.skin = stof(arg);
		SANDBOX_GETARG; e.alpha = stof(arg);
		SANDBOX_GETARG; e.colormod = stov(arg);
		SANDBOX_GETARG; e.glowmod = stov(arg);
		SANDBOX_GETARG; e.frame = stof(arg);
		SANDBOX_GETARG; sandbox_ObjectEdit_Scale(e, stof(arg));
		SANDBOX_GETARG; e.solid = e.old_solid = stof(arg);
		SANDBOX_GETARG; e.old_movetype = stof(arg);
		set_movetype(e, e.old_movetype);
		SANDBOX_GETARG; e.damageforcescale = stof(arg);
		strfree(e.material);
		SANDBOX_GETARG; e.material = (arg != "") ? strzone(arg) : string_null;
		if(database)
		{
			                                          
			strfree(e.crypto_idfp);
			SANDBOX_GETARG; e.crypto_idfp = (arg != "") ? strzone(arg) : string_null;
			SANDBOX_GETARG; strcpy(e.netname, arg);
			SANDBOX_GETARG; strcpy(e.message, arg);
			SANDBOX_GETARG; strcpy(e.message2, arg);
		}

		              
		if(i)
			sandbox_ObjectAttach_Set(e, parent, tagname);
	}

	for(i = 0; i <= MAX_STORAGE_ATTACHMENTS; ++i)
		port_string[i] = string_null;                          

	return e;
}

void sandbox_Database_Save()
{
	                                         
	string file_name;
	float file_get;

	file_name = strcat("sandbox/storage_", autocvar_g_sandbox_storage_name, "_", GetMapname(), ".txt");
	file_get = fopen(file_name, FILE_WRITE);
	fputs(file_get, strcat("// sandbox storage \"", autocvar_g_sandbox_storage_name, "\" for map \"", GetMapname(), "\" last updated ", strftime(true, "%d-%m-%Y %H:%M:%S")));
	fputs(file_get, strcat(" containing ", ftos(object_count), " objects\n"));

	IL_EACH(g_sandbox_objects, !it.owner,                                                               
	{
		                                                             
		fputs(file_get, strcat(sandbox_ObjectPort_Save(it, true), "\n"));
	});
	fclose(file_get);
}

void sandbox_Database_Load()
{
	                                           
	string file_read, file_name;
	float file_get, i;

	file_name = strcat("sandbox/storage_", autocvar_g_sandbox_storage_name, "_", GetMapname(), ".txt");
	file_get = fopen(file_name, FILE_READ);
	if(file_get < 0)
	{
		if(autocvar_g_sandbox_info > 0)
			LOG_INFO("^3SANDBOX - SERVER: ^7could not find storage file ^3", file_name, "^7, no objects were loaded");
	}
	else
	{
		for (;;)
		{
			file_read = fgets(file_get);
			if(file_read == "")
				break;
			if(substring(file_read, 0, 2) == "//")
				continue;
			if(substring(file_read, 0, 1) == "#")
				continue;

			entity e;
			e = sandbox_ObjectPort_Load(NULL, file_read, true);

			if(e.material)
			{
				                                                                                       
				for (i = 1; i <= 5; i++)                     
					precache_sound(strcat("object/impact_", e.material, "_", ftos(i), ".wav"));
			}
		}
		if(autocvar_g_sandbox_info > 0)
			LOG_INFO("^3SANDBOX - SERVER: ^7successfully loaded storage file ^3", file_name);
	}
	fclose(file_get);
}

MUTATOR_HOOKFUNCTION(sandbox, SV_ParseClientCommand)
{
	if(MUTATOR_RETURNVALUE)                                
		return;

	entity player = M_ARGV(0, entity);
	string cmd_name = M_ARGV(1, string);
	int cmd_argc = M_ARGV(2, int);

	if(cmd_name == "g_sandbox")
	{
		if(autocvar_g_sandbox_readonly)
		{
			print_to(player, "^2SANDBOX - INFO: ^7Sandbox mode is active, but in read-only mode. Sandbox commands cannot be used");
			return true;
		}
		if(cmd_argc < 2)
		{
			print_to(player, "^2SANDBOX - INFO: ^7Sandbox mode is active. For usage information, type 'sandbox help'");
			return true;
		}

		switch(argv(1))
		{
			entity e;
			int j;
			string s;

			                                                  
			case "help":
				print_to(player, "You can use the following sandbox commands:");
				print_to(player, "^7\"^2object_spawn ^3models/foo/bar.md3^7\" spawns a new object in front of the player, and gives it the specified model");
				print_to(player, "^7\"^2object_remove^7\" removes the object the player is looking at. Players can only remove their own objects");
				print_to(player, "^7\"^2object_duplicate ^3value^7\" duplicates the object, if the player has copying rights over the original");
				print_to(player, "^3copy value ^7- copies the properties of the object to the specified client cvar");
				print_to(player, "^3paste value ^7- spawns an object with the given properties. Properties or cvars must be specified as follows; eg1: \"0 1 2 ...\", eg2: \"$cl_cvar\"");
				print_to(player, "^7\"^2object_attach ^3property value^7\" attaches one object to another. Players can only attach their own objects");
				print_to(player, "^3get ^7- selects the object you are facing as the object to be attached");
				print_to(player, "^3set value ^7- attaches the previously selected object to the object you are facing, on the specified bone");
				print_to(player, "^3remove ^7- detaches all objects from the object you are facing");
				print_to(player, "^7\"^2object_edit ^3property value^7\" edits the given property of the object. Players can only edit their own objects");
				print_to(player, "^3skin value ^7- changes the skin of the object");
				print_to(player, "^3alpha value ^7- sets object transparency");
				print_to(player, "^3colormod \"value_x value_y value_z\" ^7- main object color");
				print_to(player, "^3glowmod \"value_x value_y value_z\" ^7- glow object color");
				print_to(player, "^3frame value ^7- object animation frame, for self-animated models");
				print_to(player, "^3scale value ^7- changes object scale. 0.5 is half size and 2 is double size");
				print_to(player, "^3solidity value ^7- object collisions, 0 = non-solid, 1 = solid");
				print_to(player, "^3physics value ^7- object physics, 0 = static, 1 = movable, 2 = physical");
				print_to(player, "^3force value ^7- amount of force applied to objects that are shot");
				print_to(player, "^3material value ^7- sets the material of the object. Default materials are: metal, stone, wood, flesh");
				print_to(player, "^7\"^2object_claim^7\" sets the player as the owner of the object, if they have the right to edit it");
				print_to(player, "^7\"^2object_info ^3value^7\" shows public information about the object");
				print_to(player, "^3object ^7- prints general information about the object, such as owner and creation / editing date");
				print_to(player, "^3mesh ^7- prints information about the object's mesh, including skeletal bones");
				print_to(player, "^3attachments ^7- prints information about the object's attachments");
				print_to(player, "^7The ^1drag object ^7key can be used to grab and carry objects. Players can only grab their own objects");
				return true;

			                                                           
			case "object_spawn":
				if(time < player.object_flood)
				{
					print_to(player, strcat("^1SANDBOX - WARNING: ^7Flood protection active. Please wait ^3", ftos(player.object_flood - time), " ^7seconds beofore spawning another object"));
					return true;
				}
				player.object_flood = time + autocvar_g_sandbox_editor_flood;
				if(object_count >= autocvar_g_sandbox_editor_maxobjects)
				{
					print_to(player, strcat("^1SANDBOX - WARNING: ^7Cannot spawn any more objects. Up to ^3", ftos(autocvar_g_sandbox_editor_maxobjects), " ^7objects may exist at a time"));
					return true;
				}
				if(cmd_argc < 3)
				{
					print_to(player, "^1SANDBOX - WARNING: ^7Attempted to spawn an object without specifying a model. Please specify the path to your model file after the 'object_spawn' command");
					return true;
				}
				if (!(fexists(argv(2))))
				{
					print_to(player, "^1SANDBOX - WARNING: ^7Attempted to spawn an object with a non-existent model. Make sure the path to your model file is correct");
					return true;
				}

				e = sandbox_ObjectSpawn(player, false);
				_setmodel(e, argv(2));

				if(autocvar_g_sandbox_info > 0)
					LOG_INFO("^3SANDBOX - SERVER: ^7", player.netname, " spawned an object at origin ^3", vtos(e.origin));
				return true;

			                                                            
			case "object_remove":
				e = sandbox_ObjectEdit_Get(player, true);
				if(e != NULL)
				{
					if(autocvar_g_sandbox_info > 0)
						LOG_INFO("^3SANDBOX - SERVER: ^7", player.netname, " removed an object at origin ^3", vtos(e.origin));
					sandbox_ObjectRemove(e);
					return true;
				}

				print_to(player, "^1SANDBOX - WARNING: ^7Object could not be removed. Make sure you are facing an object that you have edit rights over");
				return true;

			                                                               
			case "object_duplicate":
				switch(argv(2))
				{
					case "copy":
						                                                                              
						e = sandbox_ObjectEdit_Get(player, autocvar_g_sandbox_editor_free);                                      
						if(e != NULL)
						{
							s = sandbox_ObjectPort_Save(e, false);
							s = strreplace("\"", "\\\"", s);
							stuffcmd(player, strcat("set ", argv(3), " \"", s, "\""));

							print_to(player, "^2SANDBOX - INFO: ^7Object copied to clipboard");
							return true;
						}
						print_to(player, "^1SANDBOX - WARNING: ^7Object could not be copied. Make sure you are facing an object that you have copy rights over");
						return true;

					case "paste":
						                                                                          
						if(time < player.object_flood)
						{
							print_to(player, strcat("^1SANDBOX - WARNING: ^7Flood protection active. Please wait ^3", ftos(player.object_flood - time), " ^7seconds beofore spawning another object"));
							return true;
						}
						player.object_flood = time + autocvar_g_sandbox_editor_flood;
						if(argv(3) == "")                          
						{
							print_to(player, "^1SANDBOX - WARNING: ^7No object in clipboard. You must copy an object before you can paste it");
							return true;
						}
						if(object_count >= autocvar_g_sandbox_editor_maxobjects)
						{
							print_to(player, strcat("^1SANDBOX - WARNING: ^7Cannot spawn any more objects. Up to ^3", ftos(autocvar_g_sandbox_editor_maxobjects), " ^7objects may exist at a time"));
							return true;
						}
						e = sandbox_ObjectPort_Load(player, argv(3), false);

						print_to(player, "^2SANDBOX - INFO: ^7Object pasted successfully");
						if(autocvar_g_sandbox_info > 0)
							LOG_INFO("^3SANDBOX - SERVER: ^7", player.netname, " pasted an object at origin ^3", vtos(e.origin));
						return true;
				}
				return true;

			                                                            
			case "object_attach":
				switch(argv(2))
				{
					case "get":
						                                                 
						e = sandbox_ObjectEdit_Get(player, true);
						if(e != NULL)
						{
							player.object_attach = e;
							print_to(player, "^2SANDBOX - INFO: ^7Object selected for attachment");
							return true;
						}
						print_to(player, "^1SANDBOX - WARNING: ^7Object could not be selected for attachment. Make sure you are facing an object that you have edit rights over");
						return true;
					case "set":
						if(player.object_attach == NULL)
						{
							print_to(player, "^1SANDBOX - WARNING: ^7No object selected for attachment. Please select an object to be attached first.");
							return true;
						}

						                                               
						e = sandbox_ObjectEdit_Get(player, true);
						if(e != NULL)
						{
							sandbox_ObjectAttach_Set(player.object_attach, e, argv(3));
							player.object_attach = NULL;                                                                   
							print_to(player, "^2SANDBOX - INFO: ^7Object attached successfully");
							if(autocvar_g_sandbox_info > 1)
								LOG_INFO("^3SANDBOX - SERVER: ^7", player.netname, " attached objects at origin ^3", vtos(e.origin));
							return true;
						}
						print_to(player, "^1SANDBOX - WARNING: ^7Object could not be attached to the parent. Make sure you are facing an object that you have edit rights over");
						return true;
					case "remove":
						                               
						e = sandbox_ObjectEdit_Get(player, true);
						if(e != NULL)
						{
							sandbox_ObjectAttach_Remove(e);
							print_to(player, "^2SANDBOX - INFO: ^7Child objects detached successfully");
							if(autocvar_g_sandbox_info > 1)
								LOG_INFO("^3SANDBOX - SERVER: ^7", player.netname, " detached objects at origin ^3", vtos(e.origin));
							return true;
						}
						print_to(player, "^1SANDBOX - WARNING: ^7Child objects could not be detached. Make sure you are facing an object that you have edit rights over");
						return true;
				}
				return true;

			                                                          
			case "object_edit":
				if(argv(2) == "")
				{
					print_to(player, "^1SANDBOX - WARNING: ^7Too few parameters. You must specify a property to edit");
					return true;
				}

				e = sandbox_ObjectEdit_Get(player, true);
				if(e != NULL)
				{
					switch(argv(2))
					{
						case "skin":
							e.skin = stof(argv(3));
							break;
						case "alpha":
							e.alpha = stof(argv(3));
							break;
						case "color_main":
							e.colormod = stov(argv(3));
							break;
						case "color_glow":
							e.glowmod = stov(argv(3));
							break;
						case "frame":
							e.frame = stof(argv(3));
							break;
						case "scale":
							sandbox_ObjectEdit_Scale(e, stof(argv(3)));
							break;
						case "solidity":
							switch(argv(3))
							{
								case "0":             
									e.solid = SOLID_TRIGGER;
									break;
								case "1":         
									e.solid = SOLID_BBOX;
									break;
								default:
									break;
							}
						case "physics":
							switch(argv(3))
							{
								case "0":          
									set_movetype(e, MOVETYPE_NONE);
									break;
								case "1":           
									set_movetype(e, MOVETYPE_TOSS);
									break;
								case "2":            
									set_movetype(e, MOVETYPE_PHYSICS);
									break;
								default:
									break;
							}
							break;
						case "force":
							e.damageforcescale = stof(argv(3));
							break;
						case "material":
							strfree(e.material);
							if(argv(3))
							{
								for (j = 1; j <= 5; j++)                                        
									precache_sound(strcat("object/impact_", argv(3), "_", ftos(j), ".wav"));
								e.material = strzone(argv(3));
							}
							else
								e.material = string_null;               
							break;
						default:
							print_to(player, "^1SANDBOX - WARNING: ^7Invalid object property. For usage information, type 'sandbox help'");
							return true;
					}

					                           
					strcpy(e.message2, strftime(true, "%d-%m-%Y %H:%M:%S"));

					if(autocvar_g_sandbox_info > 1)
						LOG_INFO("^3SANDBOX - SERVER: ^7", player.netname, " edited property ^3", argv(2), " ^7of an object at origin ^3", vtos(e.origin));
					return true;
				}

				print_to(player, "^1SANDBOX - WARNING: ^7Object could not be edited. Make sure you are facing an object that you have edit rights over");
				return true;

			                                                           
			case "object_claim":
				                                                                                               
				if(player.crypto_idfp == "")
				{
					print_to(player, "^1SANDBOX - WARNING: ^7You do not have a player UID, and cannot claim objects");
					return true;
				}
				e = sandbox_ObjectEdit_Get(player, true);
				if(e != NULL)
				{
					                          
					                                                                                  
					                                                                                     
					if(e.netname != player.netname)
					{
						strcpy(e.netname, player.netname);
						print_to(player, "^2SANDBOX - INFO: ^7Object owner name updated");
					}

					if(e.crypto_idfp == player.crypto_idfp)
					{
						print_to(player, "^2SANDBOX - INFO: ^7Object is already yours, nothing to claim");
						return true;
					}

					strcpy(e.crypto_idfp, player.crypto_idfp);

					print_to(player, "^2SANDBOX - INFO: ^7Object claimed successfully");
				}
				print_to(player, "^1SANDBOX - WARNING: ^7Object could not be claimed. Make sure you are facing an object that you have edit rights over");
				return true;

			                                                          
			case "object_info":
				                                                           
				e = sandbox_ObjectEdit_Get(player, false);
				if(e != NULL)
				{
					switch(argv(2))
					{
						case "object":
							print_to(player, strcat("^2SANDBOX - INFO: ^7Object is owned by \"^7", e.netname, "^7\", created \"^3", e.message, "^7\", last edited \"^3", e.message2, "^7\""));
							return true;
						case "mesh":
							s = "";
							FOR_EACH_TAG(e)
								s = strcat(s, "^7\"^5", gettaginfo_name, "^7\", ");
							print_to(player, strcat("^2SANDBOX - INFO: ^7Object mesh is \"^3", e.model, "^7\" at animation frame ^3", ftos(e.frame), " ^7containing the following tags: ", s));
							return true;
						case "attachments":
							                                                               
							s = "";
							j = 0;
							IL_EACH(g_sandbox_objects, it.owner == e,
							{
								++j;                
								gettaginfo(e, it.tag_index);
								s = strcat(s, "^1attachment ", ftos(j), "^7 has mesh \"^3", it.model, "^7\" at animation frame ^3", ftos(it.frame));
								s = strcat(s, "^7 and is attached to bone \"^5", gettaginfo_name, "^7\", ");
							});
							if(j)                               
								print_to(player, strcat("^2SANDBOX - INFO: ^7Object contains the following ^1", ftos(j), "^7 attachment(s): ", s));
							else
								print_to(player, "^2SANDBOX - INFO: ^7Object contains no attachments");
							return true;
					}
				}
				print_to(player, "^1SANDBOX - WARNING: ^7No information could be found. Make sure you are facing an object");
				return true;

			                                                     
			default:
				print_to(player, "Invalid command. For usage information, type 'sandbox help'");
				return true;
		}
	}
}

MUTATOR_HOOKFUNCTION(sandbox, SV_StartFrame)
{
	if(!autocvar_g_sandbox_storage_autosave)
		return;
	if(time < autosave_time)
		return;
	autosave_time = time + autocvar_g_sandbox_storage_autosave;

	sandbox_Database_Save();

	return true;
}
