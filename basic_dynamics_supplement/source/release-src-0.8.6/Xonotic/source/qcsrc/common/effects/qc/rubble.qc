#include "rubble.qh"

#ifdef GAMEQC

void LimitedChildrenRubble(IntrusiveList list, string cname, int limit, void(entity) deleteproc, entity parent){
	                                                      
	                                                         
	while (1)
	{
		                                                        
		                                              
		int c = 0;
		entity oldest = NULL;
		float oldesttime = 0;
		                                         
		IL_EACH(list, it.classname == cname,
		{
			if(!parent || parent == it.owner){
				++c;
				if(!oldest || oldesttime > it.creationtime)
				{
					oldest = it;
					oldesttime = it.creationtime;
				}
			}
		});

		                                                
		if (c <= limit) break;

		                                          
		deleteproc(oldest);
	}
}


                                                                                                                                             
                                                                                               
entity ReplaceOldListedChildRubble(IntrusiveList list, entity child, entity oldChild){
	child.creationtime = oldChild.creationtime;
	IL_REMOVE(list, oldChild);
	IL_PUSH(list, child);
	return child;
}

entity ListNewChildRubble(IntrusiveList list, entity child){
	child.creationtime = time;
	IL_PUSH(list, child);
	return child;
}

#endif
