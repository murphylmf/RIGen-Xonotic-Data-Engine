  
                                         
                              

                                                             
                                                           
                                                              
                                                      

                                                               
                                                              
                                                    

                                                    

                                                                 
                                                           
                                                                           

  

#ifndef NET_H
#define NET_H

#include "lhnet.h"

#define NET_HEADERSIZE		(2 * sizeof(unsigned int))

                  
#define NETFLAG_LENGTH_MASK 0x0000ffff
#define NETFLAG_DATA        0x00010000
#define NETFLAG_ACK         0x00020000
#define NETFLAG_NAK         0x00040000
#define NETFLAG_EOM         0x00080000
#define NETFLAG_UNRELIABLE  0x00100000
#define NETFLAG_CRYPTO0     0x10000000
#define NETFLAG_CRYPTO1     0x20000000
#define NETFLAG_CRYPTO2     0x40000000
#define NETFLAG_CTL         0x80000000


#define NET_PROTOCOL_VERSION	3
#define NET_EXTRESPONSE_MAX 16

                                                       
                            
                                                                           
                                                       
   
   
                       
                                                                             
                                                              
   
                 
                                
                                                   
   
                     
                                
                                                   
   
                     
                       
   
                   
                
   
              
                    
                   
   
   
   
                
              
   
                
                  
   
                     
                          
                     
                      
                         
                     
                                               
   
                     
                       
                
                
               
                      
                   
   
                   
                
                 
   
              
                 
            
         
                                                                      
                                                                          
                                                                        
                                                                          
                                                                       
                                                                       
                                                                       
                                                     

#define CCREQ_CONNECT		0x01
#define CCREQ_SERVER_INFO	0x02
#define CCREQ_PLAYER_INFO	0x03
#define CCREQ_RULE_INFO		0x04
#define CCREQ_RCON		0x05                                    

#define CCREP_ACCEPT		0x81
#define CCREP_REJECT		0x82
#define CCREP_SERVER_INFO	0x83
#define CCREP_PLAYER_INFO	0x84
#define CCREP_RULE_INFO		0x85
#define CCREP_RCON		0x86                                    

typedef struct netgraphitem_s
{
	double time;
	int reliablebytes;
	int unreliablebytes;
	int ackbytes;
	double cleartime;
}
netgraphitem_t;

typedef struct netconn_s
{
	struct netconn_s *next;

	lhnetsocket_t *mysocket;
	lhnetaddress_t peeraddress;

	                                                   

	                                          
	double connecttime;
	double timeout;
	double lastMessageTime;
	double lastSendTime;

	                                                               
	                                                                          
	                                                        
	      
	sizebuf_t message;
	unsigned char messagedata[NET_MAXMESSAGE];
	      

	                                              
	                            
	int sendMessageLength;
	unsigned char sendMessage[NET_MAXMESSAGE];

	                                                     
	                                    
	int receiveMessageLength;
	unsigned char receiveMessage[NET_MAXMESSAGE];

	                                    
	unsigned int outgoing_unreliable_sequence;

	struct netconn_nq_s
	{
		unsigned int ackSequence;
		unsigned int sendSequence;

		unsigned int receiveSequence;
		unsigned int unreliableReceiveSequence;
	}
	nq;
	struct netconn_qw_s
	{
		              
		qboolean	fatal_error;

		float		last_received;		               

	                                                           
	                                                                  
		float		frame_latency;		                  
		float		frame_rate;

		int			drop_count;			                                        
		int			good_count;			                       

		int			qport;

	                       
		unsigned int		incoming_sequence;
		unsigned int		incoming_acknowledged;
		qboolean		incoming_reliable_acknowledged;	               

		qboolean		incoming_reliable_sequence;		                                 

		qboolean		reliable_sequence;			               
		unsigned int		last_reliable_sequence;		                                 
	}
	qw;

	                      
	double		cleartime;			                                          
	double		incoming_cleartime;		                                                                               

	                                                                      
	                               
#define NETGRAPH_PACKETS 256
#define NETGRAPH_NOPACKET 0
#define NETGRAPH_LOSTPACKET -1
#define NETGRAPH_CHOKEDPACKET -2
	int incoming_packetcounter;
	netgraphitem_t incoming_netgraph[NETGRAPH_PACKETS];
	int outgoing_packetcounter;
	netgraphitem_t outgoing_netgraph[NETGRAPH_PACKETS];

	char address[128];
	crypto_t crypto;

	                     
	int packetsSent;
	int packetsReSent;
	int packetsReceived;
	int receivedDuplicateCount;
	int droppedDatagrams;
	int unreliableMessagesSent;
	int unreliableMessagesReceived;
	int reliableMessagesSent;
	int reliableMessagesReceived;
} netconn_t;

extern netconn_t *netconn_list;
extern mempool_t *netconn_mempool;

extern cvar_t hostname;
extern cvar_t developer_networking;

#ifdef CONFIG_MENU
#define SERVERLIST_VIEWLISTSIZE		SERVERLIST_TOTALSIZE

typedef enum serverlist_maskop_e
{
	                                           
	                                                                                             
	SLMO_CONTAINS,
	SLMO_NOTCONTAIN,

	SLMO_LESSEQUAL,
	SLMO_LESS,
	SLMO_EQUAL,
	SLMO_GREATER,
	SLMO_GREATEREQUAL,
	SLMO_NOTEQUAL,
	SLMO_STARTSWITH,
	SLMO_NOTSTARTSWITH
} serverlist_maskop_t;

                                                             
typedef struct serverlist_info_s
{
	                          
	char cname[128];
	                                 
	int ping;
	                    
	char game[32];
	                   
	char mod[32];
	                   
	char map[32];
	                       
	char name[128];
	                                  
	char qcstatus[128];
	                                                    
	char players[2800];
	                     
	int maxplayers;
	                                                          
	int numplayers;
	                                                       
	int numbots;
	                                                           
	int numhumans;
	                        
	int freeslots;
	                    
	int protocol;
	                     
	                                                                
	                          
	int gameversion;

	                      
	int category;
	                        
	qboolean isfavorite;
} serverlist_info_t;

typedef enum
{
	SLIF_CNAME,
	SLIF_PING,
	SLIF_GAME,
	SLIF_MOD,
	SLIF_MAP,
	SLIF_NAME,
	SLIF_MAXPLAYERS,
	SLIF_NUMPLAYERS,
	SLIF_PROTOCOL,
	SLIF_NUMBOTS,
	SLIF_NUMHUMANS,
	SLIF_FREESLOTS,
	SLIF_QCSTATUS,
	SLIF_PLAYERS,
	SLIF_CATEGORY,
	SLIF_ISFAVORITE,
	SLIF_COUNT
} serverlist_infofield_t;

typedef enum
{
	SLSF_DESCENDING = 1,
	SLSF_FAVORITES = 2,
	SLSF_CATEGORIES = 4
} serverlist_sortflags_t;

typedef enum
{
	SQS_NONE = 0,
	SQS_QUERYING,
	SQS_QUERIED,
	SQS_TIMEDOUT,
	SQS_REFRESHING
} serverlist_query_state;

typedef struct serverlist_entry_s
{
	                                                                               
	serverlist_query_state query;
	                                                                                     
	unsigned querycounter;
	                                               
	double querytime;
	                                                                                            
	int protocol;

	serverlist_info_t info;

	               
	char line1[128];
	char line2[128];
} serverlist_entry_t;

typedef struct serverlist_mask_s
{
	qboolean			active;
	serverlist_maskop_t  tests[SLIF_COUNT];
	serverlist_info_t info;
} serverlist_mask_t;

#define ServerList_GetCacheEntry(x) (&serverlist_cache[(x)])
#define ServerList_GetViewEntry(x) (ServerList_GetCacheEntry(serverlist_viewlist[(x)]))

extern serverlist_mask_t serverlist_andmasks[SERVERLIST_ANDMASKCOUNT];
extern serverlist_mask_t serverlist_ormasks[SERVERLIST_ORMASKCOUNT];

extern serverlist_infofield_t serverlist_sortbyfield;
extern int serverlist_sortflags;                                          

#if SERVERLIST_TOTALSIZE > 65536
#error too many servers, change type of index array
#endif
extern int serverlist_viewcount;
extern unsigned short serverlist_viewlist[SERVERLIST_VIEWLISTSIZE];

extern int serverlist_cachecount;
extern serverlist_entry_t *serverlist_cache;
extern const serverlist_entry_t *serverlist_callbackentry;

extern qboolean serverlist_consoleoutput;

void ServerList_GetPlayerStatistics(int *numplayerspointer, int *maxplayerspointer);
#endif

                                                                              
  
                           
  
                                                                              

extern char cl_net_extresponse[NET_EXTRESPONSE_MAX][1400];
extern int cl_net_extresponse_count;
extern int cl_net_extresponse_last;

extern char sv_net_extresponse[NET_EXTRESPONSE_MAX][1400];
extern int sv_net_extresponse_count;
extern int sv_net_extresponse_last;

#ifdef CONFIG_MENU
extern double masterquerytime;
extern int masterquerycount;
extern int masterreplycount;
extern int serverquerycount;
extern int serverreplycount;
#endif

extern sizebuf_t cl_message;
extern sizebuf_t sv_message;
extern char cl_readstring[MAX_INPUTLINE];
extern char sv_readstring[MAX_INPUTLINE];

extern cvar_t sv_public;

extern cvar_t cl_netlocalping;

extern cvar_t cl_netport;
extern cvar_t sv_netport;
extern cvar_t net_address;
extern cvar_t net_address_ipv6;
extern cvar_t net_usesizelimit;
extern cvar_t net_burstreserve;

qboolean NetConn_CanSend(netconn_t *conn);
int NetConn_SendUnreliableMessage(netconn_t *conn, sizebuf_t *data, protocolversion_t protocol, int rate, int burstsize, qboolean quakesignon_suppressreliables);
qboolean NetConn_HaveClientPorts(void);
qboolean NetConn_HaveServerPorts(void);
void NetConn_CloseClientPorts(void);
void NetConn_OpenClientPorts(void);
void NetConn_CloseServerPorts(void);
void NetConn_OpenServerPorts(int opennetports);
void NetConn_UpdateSockets(void);
lhnetsocket_t *NetConn_ChooseClientSocketForAddress(lhnetaddress_t *address);
lhnetsocket_t *NetConn_ChooseServerSocketForAddress(lhnetaddress_t *address);
void NetConn_Init(void);
void NetConn_Shutdown(void);
netconn_t *NetConn_Open(lhnetsocket_t *mysocket, lhnetaddress_t *peeraddress);
void NetConn_Close(netconn_t *conn);
void NetConn_Listen(qboolean state);
int NetConn_Read(lhnetsocket_t *mysocket, void *data, int maxlength, lhnetaddress_t *peeraddress);
int NetConn_Write(lhnetsocket_t *mysocket, const void *data, int length, const lhnetaddress_t *peeraddress);
int NetConn_WriteString(lhnetsocket_t *mysocket, const char *string, const lhnetaddress_t *peeraddress);
int NetConn_IsLocalGame(void);
void NetConn_ClientFrame(void);
void NetConn_ServerFrame(void);
void NetConn_SleepMicroseconds(int microseconds);
void NetConn_Heartbeat(int priority);
void Net_Stats_f(void);

#ifdef CONFIG_MENU
void NetConn_QueryMasters(qboolean querydp, qboolean queryqw);
void NetConn_QueryQueueFrame(void);
void Net_Slist_f(void);
void Net_SlistQW_f(void);
void Net_Refresh_f(void);

                                 
                                                                                          
void ServerList_RebuildViewList(void);
void ServerList_ResetMasks(void);
void ServerList_QueryList(qboolean resetcache, qboolean querydp, qboolean queryqw, qboolean consoleoutput);

                                               
void NetConn_UpdateFavorites(void);
#endif

#define MAX_CHALLENGES 128
typedef struct challenge_s
{
	lhnetaddress_t address;
	double time;
	char string[12];
}
challenge_t;

extern challenge_t challenges[MAX_CHALLENGES];

#endif

