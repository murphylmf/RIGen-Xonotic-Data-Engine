#include "urllib.qh"

        
.float url_fh;
const float URL_FH_CURL = -1;
const float URL_FH_STDOUT = -2;

       
.string url_url;
.string url_content_type;
.string url_verb;
.float url_wbuf;
.float url_wbufpos;
.float url_rbuf;
.float url_rbufpos;
.float url_id;
.url_ready_func url_ready;
.entity url_ready_pass;

                    
.int url_attempt;
.int url_mode;

entity url_fromid[NUM_URL_ID];
int autocvar__urllib_nextslot;

ERASEABLE
float url_URI_Get_Callback(int id, float status, string data)
{
	if (id < MIN_URL_ID) return 0;
	id -= MIN_URL_ID;
	if (id >= NUM_URL_ID) return 0;
	entity e;
	e = url_fromid[id];
	if (!e) return 0;
	if (e.url_rbuf >= 0 || e.url_wbuf >= 0)
	{
		LOG_INFOF("WARNING: handle %d (%s) has already received data?!?", id + NUM_URL_ID, e.url_url);
		return 0;
	}

	                                                                
	url_fromid[id] = NULL;

	                                                    
	if (e.url_rbuf != -1 || e.url_wbuf != -1 || e.url_fh != URL_FH_CURL) error("url_URI_Get_Callback: not a request waiting for data");

	if (status == 0)
	{
		               
		float n, i;
		n = tokenizebyseparator(data, "\n");
		e.url_rbuf = buf_create();
		if (e.url_rbuf < 0)
		{
			LOG_INFO("url_URI_Get_Callback: out of memory in buf_create");
			e.url_ready(e, e.url_ready_pass, URL_READY_ERROR);
			strfree(e.url_url);
			delete(e);
			return 1;
		}
		e.url_rbufpos = 0;
		if (e.url_rbuf < 0)
		{
			LOG_INFO("url_URI_Get_Callback: out of memory in buf_create");
			e.url_ready(e, e.url_ready_pass, URL_READY_ERROR);
			strfree(e.url_url);
			delete(e);
			return 1;
		}
		for (i = 0; i < n; ++i)
			bufstr_set(e.url_rbuf, i, argv(i));
		e.url_ready(e, e.url_ready_pass, URL_READY_CANREAD);
		return 1;
	}
	else
	{
		           
		e.url_ready(e, e.url_ready_pass, -fabs(status));
		strfree(e.url_url);
		delete(e);
		return 1;
	}
}

ERASEABLE
void url_single_fopen(string url, int mode, url_ready_func rdy, entity pass)
{
	entity e;
	int i;
	if (strstrofs(url, "://", 0) >= 0)
	{
		switch (mode)
		{
			case FILE_WRITE:
			case FILE_APPEND:
				                                                    
				                                                    

				                                             
				e = new_pure(url_single_fopen_file);
				e.url_url = strzone(url);
				e.url_content_type = "text/plain";
				e.url_verb = "";
				e.url_fh = URL_FH_CURL;
				e.url_wbuf = buf_create();
				if (e.url_wbuf < 0)
				{
					LOG_INFO("url_single_fopen: out of memory in buf_create");
					rdy(e, pass, URL_READY_ERROR);
					strfree(e.url_url);
					delete(e);
					return;
				}
				e.url_wbufpos = 0;
				e.url_rbuf = -1;
				e.url_ready = rdy;
				e.url_ready_pass = pass;
				rdy(e, pass, URL_READY_CANWRITE);
				break;

			case FILE_READ:
				                 

				                            
				for (i = autocvar__urllib_nextslot; i < NUM_URL_ID; ++i)
					if (url_fromid[i] == NULL) break;
				if (i >= NUM_URL_ID)
				{
					for (i = 0; i < autocvar__urllib_nextslot; ++i)
						if (url_fromid[i] == NULL) break;
					if (i >= autocvar__urllib_nextslot)
					{
						LOG_INFO("url_single_fopen: too many concurrent requests");
						rdy(NULL, pass, URL_READY_ERROR);
						return;
					}
				}

				               
				if (!crypto_uri_postbuf(url, i + MIN_URL_ID, string_null, string_null, -1, 0))
				{
					LOG_INFO("url_single_fopen: failure in crypto_uri_postbuf");
					rdy(NULL, pass, URL_READY_ERROR);
					return;
				}

				                                            
				                                       
				                                 
				e = new_pure(url_single_fopen_file);
				e.url_url = strzone(url);
				e.url_fh = URL_FH_CURL;
				e.url_rbuf = -1;
				e.url_wbuf = -1;
				e.url_ready = rdy;
				e.url_ready_pass = pass;
				e.url_id = i;
				url_fromid[i] = e;

				                                                                 
				cvar_set("_urllib_nextslot", ftos((i + 1) % NUM_URL_ID));
				break;
		}
	}
	else if (url == "-")
	{
		switch (mode)
		{
			case FILE_WRITE:
			case FILE_APPEND:
				e = new_pure(url_single_fopen_stdout);
				e.url_fh = URL_FH_STDOUT;
				e.url_ready = rdy;
				e.url_ready_pass = pass;
				rdy(e, pass, URL_READY_CANWRITE);
				break;
			case FILE_READ:
				LOG_INFO("url_single_fopen: cannot open '-' for reading");
				rdy(NULL, pass, URL_READY_ERROR);
				break;
		}
	}
	else
	{
		float fh;
		fh = fopen(url, mode);
		if (fh < 0)
		{
			rdy(NULL, pass, URL_READY_ERROR);
			return;
		}
		else
		{
			e = new_pure(url_single_fopen_file);
			e.url_fh = fh;
			e.url_ready = rdy;
			e.url_ready_pass = pass;
			if (mode == FILE_READ) rdy(e, pass, URL_READY_CANREAD);
			else rdy(e, pass, URL_READY_CANWRITE);
		}
	}
}

               
ERASEABLE
void url_fclose(entity e)
{
	int i;

	if (e.url_fh == URL_FH_CURL)
	{
		if (e.url_rbuf == -1 || e.url_wbuf != -1)                                  
			if (e.url_rbuf != -1 || e.url_wbuf == -1)                         
				error("url_fclose: not closable in current state");

		                  
		if (e.url_wbuf >= 0)
		{
			                                                   

			                            
			for (i = autocvar__urllib_nextslot; i < NUM_URL_ID; ++i)
				if (url_fromid[i] == NULL) break;
			if (i >= NUM_URL_ID)
			{
				for (i = 0; i < autocvar__urllib_nextslot; ++i)
					if (url_fromid[i] == NULL) break;
				if (i >= autocvar__urllib_nextslot)
				{
					LOG_INFO("url_fclose: too many concurrent requests");
					e.url_ready(e, e.url_ready_pass, URL_READY_ERROR);
					buf_del(e.url_wbuf);
					strfree(e.url_url);
					delete(e);
					return;
				}
			}

			                
			if (!crypto_uri_postbuf(e.url_url, i + MIN_URL_ID, e.url_content_type, e.url_verb, e.url_wbuf, 0))
			{
				LOG_INFO("url_fclose: failure in crypto_uri_postbuf");
				e.url_ready(e, e.url_ready_pass, URL_READY_ERROR);
				buf_del(e.url_wbuf);
				strfree(e.url_url);
				delete(e);
				return;
			}

			                                                   
			                                                     
			                    
			buf_del(e.url_wbuf);
			e.url_wbuf = -1;
			e.url_id = i;
			url_fromid[i] = e;

			                                                                 
			cvar_set("_urllib_nextslot", ftos((i + 1) % NUM_URL_ID));
		}
		else
		{
			                                    
			e.url_ready(e, e.url_ready_pass, URL_READY_CLOSED);
			buf_del(e.url_rbuf);
			strfree(e.url_url);
			delete(e);
		}
	}
	else if (e.url_fh == URL_FH_STDOUT)
	{
		e.url_ready(e, e.url_ready_pass, URL_READY_CLOSED);                                      
		delete(e);
	}
	else
	{
		       
		fclose(e.url_fh);
		e.url_ready(e, e.url_ready_pass, URL_READY_CLOSED);                                      
		delete(e);
	}
}

                            
ERASEABLE
string url_fgets(entity e)
{
	if (e.url_fh == URL_FH_CURL)
	{
		if (e.url_rbuf == -1) error("url_fgets: not readable in current state");
		       
		string s;
		s = bufstr_get(e.url_rbuf, e.url_rbufpos);
		e.url_rbufpos += 1;
		return s;
	}
	else if (e.url_fh == URL_FH_STDOUT)
	{
		         
		return string_null;
	}
	else
	{
		       
		return fgets(e.url_fh);
	}
}

                               
ERASEABLE
void url_fputs(entity e, string s)
{
	if (e.url_fh == URL_FH_CURL)
	{
		if (e.url_wbuf == -1) error("url_fputs: not writable in current state");
		       
		bufstr_set(e.url_wbuf, e.url_wbufpos, s);
		e.url_wbufpos += 1;
	}
	else if (e.url_fh == URL_FH_STDOUT)
	{
		         
		print(s);
	}
	else
	{
		       
		fputs(e.url_fh, s);
	}
}

                                                              
ERASEABLE
void url_multi_ready(entity fh, entity me, float status)
{
	float n;
	if (status == URL_READY_ERROR || status < 0)
	{
		if (status == -422)                         
		{
			LOG_INFO("uri_multi_ready: got HTTP error 422, data is in unusable format - not continuing");
			me.url_ready(fh, me.url_ready_pass, status);
			strfree(me.url_url);
			delete(me);
			return;
		}
		me.url_attempt += 1;
		n = tokenize_console(me.url_url);
		if (n <= me.url_attempt)
		{
			me.url_ready(fh, me.url_ready_pass, status);
			strfree(me.url_url);
			delete(me);
			return;
		}
		url_single_fopen(argv(me.url_attempt), me.url_mode, url_multi_ready, me);
		return;
	}
	me.url_ready(fh, me.url_ready_pass, status);
}

ERASEABLE
void url_multi_fopen(string url, int mode, url_ready_func rdy, entity pass)
{
	float n;
	n = tokenize_console(url);
	if (n <= 0)
	{
		LOG_INFO("url_multi_fopen: need at least one URL");
		rdy(NULL, pass, URL_READY_ERROR);
		return;
	}

	entity me = new_pure(url_multi);
	me.url_url = strzone(url);
	me.url_attempt = 0;
	me.url_mode = mode;
	me.url_ready = rdy;
	me.url_ready_pass = pass;
	url_single_fopen(argv(0), mode, url_multi_ready, me);
}
