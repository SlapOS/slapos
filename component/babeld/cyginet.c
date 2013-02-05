/*
 * Some issues:
 *
 * 1. libwinet_dump_ipv6_route_table
 *
 *    Before Windows Vista, we have to use command "netsh" to get ipv6
 *    route table. But the output misses the value of route protocol.
 *
 * 2. libwinet_edit_route_entry
 * 
 *    What should be the value of protocol? MIB_IPPROTO_NETMGMT or
 *    RTPROT_BABEL_LOCAL
 *    
 */

/* The Win32 select only worked on socket handles. The Cygwin
 * implementation allows select to function normally when given
 * different types of file descriptors (sockets, pipes, handles,
 * etc.).
 */
#if !defined(__INSIDE_CYGWIN__)
  #define __INSIDE_CYGWIN__
  #define USE_SYS_TYPES_FD_SET
#endif
#include <sys/select.h>
#include <sys/fcntl.h>

/* Headers in the /usr/include/w32api */
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <iphlpapi.h>
#include <wlanapi.h>

#include <errno.h>
#include <stdio.h>
#include <unistd.h>
#include <wchar.h>

#define INSIDE_CYGINET
#include "cyginet.h"
#undef INSIDE_CYGINET

static HRESULT (WINAPI *ws_guidfromstring)(LPCTSTR psz, LPGUID pguid) = NULL;
static HANDLE event_notify_monitor_thread = WSA_INVALID_EVENT;

static void
plen2mask(int n, struct in_addr *dest)
{
    unsigned char *p;
    int i;

    static const int pl2m[9] = {
        0x00, 0x80, 0xc0, 0xe0, 0xf0, 0xf8, 0xfc, 0xfe, 0xff
    };

    memset(dest, 0, sizeof(struct in_addr));
    p = (u_char *)dest;
    for (i = 0; i < 4; i++, p++, n -= 8) {
        if (n >= 8) {
            *p = 0xff;
            continue;
        }
        *p = pl2m[n];
        break;
    }
    return;
}

static int
mask2len(const unsigned char *p, const int size)
{
    int i = 0, j;

    for(j = 0; j < size; j++, p++) {
        if(*p != 0xff)
            break;
        i += 8;
    }
    if(j < size) {
        switch(*p) {
#define	MASKLEN(m, l)	case m: do { i += l; break; } while (0)
            MASKLEN(0xfe, 7); break;
            MASKLEN(0xfc, 6); break;
            MASKLEN(0xf8, 5); break;
            MASKLEN(0xf0, 4); break;
            MASKLEN(0xe0, 3); break;
            MASKLEN(0xc0, 2); break;
            MASKLEN(0x80, 1); break;
#undef	MASKLEN
        }
    }
    return i;
}

static int
libwinet_get_interface_info(const char *ifname,
                            int family,
                            int ifindex,
                            PLIBWINET_INTERFACE pinfo)
{
  IP_ADAPTER_ADDRESSES *pAdaptAddr = NULL;
  IP_ADAPTER_ADDRESSES *pTmpAdaptAddr = NULL;
  DWORD dwRet = 0;
  DWORD dwSize = 0x10000;
  DWORD dwReturn = 0;

  dwRet = GetAdaptersAddresses(family,
                               GAA_FLAG_SKIP_ANYCAST            \
                               | GAA_FLAG_SKIP_MULTICAST        \
                               | GAA_FLAG_SKIP_DNS_SERVER       \
                               | GAA_FLAG_SKIP_FRIENDLY_NAME,
                               NULL,
                               pAdaptAddr,
                               &dwSize
                               );
  if (ERROR_BUFFER_OVERFLOW == dwRet) {
    FREE(pAdaptAddr);
    if (NULL == (pAdaptAddr = (IP_ADAPTER_ADDRESSES*)MALLOC(dwSize)))
      return -1;
    dwRet = GetAdaptersAddresses(family,
                                 GAA_FLAG_SKIP_ANYCAST            \
                                 | GAA_FLAG_SKIP_MULTICAST        \
                                 | GAA_FLAG_SKIP_DNS_SERVER       \
                                 | GAA_FLAG_SKIP_FRIENDLY_NAME,
                                 NULL,
                                 pAdaptAddr,
                                 &dwSize
                                 );
  }
  if (NO_ERROR == dwRet) {

    pTmpAdaptAddr = pAdaptAddr;

    while (pTmpAdaptAddr) {
      /* For ipv4, two contidions:
         AdapterName equals ifname and IfIndex is nonzero.
         For ipv6, only judge Ipv6IfIndex
         */
      if (family == AF_INET6 ? pTmpAdaptAddr -> Ipv6IfIndex == ifindex  \
          : (pTmpAdaptAddr -> IfIndex != 0)                             \
          && (strcmp(ifname, pTmpAdaptAddr -> AdapterName) == 0)
          ) {
        memset(pinfo, 0, sizeof(pinfo));
        pinfo -> IfType = pTmpAdaptAddr -> IfType;
        pinfo -> Mtu = pTmpAdaptAddr -> Mtu;
        pinfo -> OperStatus = pTmpAdaptAddr -> OperStatus;
        /* Copy first unicast address */
        if (pTmpAdaptAddr -> FirstUnicastAddress)
          memcpy(&(pinfo -> Address),
                 (pTmpAdaptAddr -> FirstUnicastAddress -> Address).lpSockaddr,
                 sizeof(pinfo -> Address)
                 );
        dwReturn = 1;
        break;
      }

      pTmpAdaptAddr = pTmpAdaptAddr->Next;
    }

  }

  FREE(pAdaptAddr);
  return dwReturn;
}

static int
libwinet_run_command(const char *command)
{
  FILE *output;

  output = popen (command, "r");
  if (!output)
    return -1;
  /* Waiting for subprocess exit and return exit code */
  return pclose (output);
}

#if _WIN32_WINNT < _WIN32_WINNT_VISTA

/*
 * Before Windows Vista, use netsh command to get ipv6 route table
 *
 *   C:\> netsh interface ipv6 show routes verbose
 *
 *   It will print the following route entries:
 *
 *       Prefix            : fe80::1/128
 *       Interface 1       : Loopback Pseudo-Interface
 *       Gateway           : fe80::1
 *       Metric            : 4
 *       Publish           : no
 *       Type              : System
 *       Valid Lifetime    : infinite
 *       Preferred Lifetime: infinite
 *       Site Prefix Length: 0
 *
 *       ....
 *
 *   Type System means that routes used for loopback.
 *
 *   Gateway could be an address or interface name.
 *
 */

static int
libwinet_dump_ipv6_route_table(struct kernel_route *routes,
                               int maxroutes)
{
  #define MAX_LINE_SIZE 80
  const char * command = "netsh interface ipv6 show routes verbose";

  FILE *output;
  char buffer[MAX_LINE_SIZE];
  char *s, *p;
  int count = 0;
  int ignored = 0;

  IN6_ADDR *sin6;
  struct kernel_route * proute = routes;

  output = popen (command, "r");
  if (!output)
    return -1;

  /* Ignore the first line */
  fgets(buffer, MAX_LINE_SIZE, output);

  /* Read the output until EOF */
  while (fgets(buffer, MAX_LINE_SIZE, output)) {

    if (('\n' == buffer[0]) || ('\r' == buffer[0]))
      continue;

    if (NULL == (s = strchr(buffer, ':')))
      break;

    *s ++ = 0;                  /* Split the string */
    s ++;                       /* Skip space */

    /* The first field of route entry */
    if (strncmp(buffer, "Prefix", 6) == 0) {
      sin6 = (IN6_ADDR*)&(proute -> prefix);

      if (NULL == (p = strchr(s, '/')))
        break;
      *p ++ = 0;
      /*
       * Maybe it will be "fe80::5efe:10.85.0.127", ignore it
       */
      if (inet_pton(AF_INET6, s, sin6) != 1)
        ignored = 1;
      proute -> plen = strtol(p, NULL, 10);
    }

    else if (strncmp(buffer, "Interface", 9) == 0)
      proute -> ifindex = strtol(buffer + 9, NULL, 10);

    else if (strncmp(buffer, "Gateway", 7) == 0) {
      sin6 = (IN6_ADDR*)&(proute -> gw);
      if (inet_pton(AF_INET6, s, sin6) != 1)
        memset(sin6, 0, sizeof(IN6_ADDR));
    }

    else if (strncmp(buffer, "Metric", 6) == 0)
      proute -> metric = strtol(s, NULL, 10);

    /* Last field of the route entry */
    else if (strncmp(buffer, "Site Prefix Length", 18) == 0) {
      if (ignored)
        ignored = 0;
      else if (!ignored) {
        proute -> proto = MIB_IPPROTO_OTHER; /* ?? */
        count ++;
        proute ++;
        if (count > maxroutes)
          break;
      }
    }

    else {
      /* Immortal: persistent entry */
      /* Age */
      /* ... */
    }
  }

  pclose (output);
  return count;
}

/* Tell the interface is wireless or not. First we list all wireless
 * interfaces in the machine, then search the designated one.
 */
static int
libwinet_is_wireless_interface(const char *ifname)
{
  GUID ifguid;

  HANDLE hClient = NULL;
  DWORD dwMaxClient = 1;
  /* 1 Client version for Windows XP with SP3 and Wireless LAN API for
     Windows XP with SP2. */
  /* 2 Client version for Windows Vista and Windows Server 2008 */
  DWORD dwCurVersion = 1;
  DWORD dwResult = 0;
  int iRet = 0;
  int i;

  if (NULL == ws_guidfromstring) {
    HMODULE lib;
    if ((lib = LoadLibraryW(L"shell32.dll"))) {
      ws_guidfromstring = (HRESULT (WINAPI *)(LPCTSTR, LPGUID))
        GetProcAddress(lib, (LPCSTR)703); /* GUIDFromStringA */
      FreeLibrary(lib);
    }
  }
  if (NULL == ws_guidfromstring)
    return -1;

  if (!(*ws_guidfromstring)(ifname, &ifguid))
    return -1;

  /* variables used for WlanEnumInterfaces  */
  PWLAN_INTERFACE_INFO_LIST pIfList = NULL;
  PWLAN_INTERFACE_INFO pIfInfo = NULL;

  dwResult = WlanOpenHandle(dwMaxClient, NULL, &dwCurVersion, &hClient);
  if (dwResult != ERROR_SUCCESS)
    return -1;

  dwResult = WlanEnumInterfaces(hClient, NULL, &pIfList);
  if (dwResult != ERROR_SUCCESS)
    return -1;

  for (i = 0; i < (int) pIfList->dwNumberOfItems; i++) {
    pIfInfo = (WLAN_INTERFACE_INFO *) &pIfList->InterfaceInfo[i];
    if (0 == memcmp(&pIfInfo->InterfaceGuid, &ifguid, sizeof(GUID))) {
      iRet = 1;
      break;
    }
  }

  if (pIfList != NULL) {
    WlanFreeMemory(pIfList);
    pIfList = NULL;
  }

  return iRet;
}

#endif  /* _WIN32_WINNT < _WIN32_WINNT_VISTA */

static DWORD WINAPI
libwinet_monitor_route_thread_proc(LPVOID lpParam)
{
  #define EVENT_COUNT 4
  DWORD dwBytesReturned = 0;
  DWORD dwReturn = 0;

  SOCKET s[2] = {INVALID_SOCKET, INVALID_SOCKET};
  WSAOVERLAPPED hOverLappeds[EVENT_COUNT];
  WSAEVENT hEvents[EVENT_COUNT + 1];
  SOCKADDR_IN6 IPv6Addr = {
      AF_INET6,
      0,
      0,
      {{IN6ADDR_ANY_INIT}}
  };
  SOCKADDR_IN IPv4Addr = {
    AF_INET,
    0,
    {{{INADDR_ANY}}},
    {0}
  };

  int mypipe = (int)lpParam;
  BOOL bResult = TRUE;
  int i;

  memset(hOverLappeds, 0, sizeof(WSAOVERLAPPED) * EVENT_COUNT);
  memset(hEvents, 0, sizeof(WSAEVENT) * EVENT_COUNT);

  hEvents[EVENT_COUNT] = event_notify_monitor_thread;

  if (bResult) {
    s[0] = socket(AF_INET, SOCK_DGRAM, 0);
    s[1] = socket(AF_INET6, SOCK_DGRAM, 0);

    if ((INVALID_SOCKET == s[0]) || (INVALID_SOCKET == s[1])) {
      SOCKETERR("socket");
      bResult = FALSE;
    }
  }

  if (bResult)
    for (i = 0; i < EVENT_COUNT; i++)
      if (WSA_INVALID_EVENT == (hEvents[i] = WSACreateEvent())) {
        SOCKETERR("WSACreateEvent");
        bResult = FALSE;
        break;
      }

  /* DestAddrs[0].sa_family = AF_INET; */
  /* ((SOCKADDR_IN*)&DestAddrs[0])->sin_addr.S_un.S_addr =
     htonl(INADDR_ANY); */
  /* DestAddrs[1].sa_family = AF_INET6; */
  /* ((SOCKADDR_IN6*)&DestAddrs[1])->sin6_addr = IN6ADDR_ANY_INIT; */

  /* Waiting for route and interface changed */
  DWORD dwWaitResult;
  while (bResult) {

    memset(hOverLappeds, 0, sizeof(WSAOVERLAPPED) * EVENT_COUNT);
    for (i = 0; i < EVENT_COUNT; i++) 
      hOverLappeds[i].hEvent = hEvents[i];
    for (i = 0; i < 2; i++) {

      if (bResult) {
        if (SOCKET_ERROR == WSAIoctl(s[i],
                                     SIO_ROUTING_INTERFACE_CHANGE,
                                     i ? (LPVOID)&IPv6Addr:(LPVOID)&IPv4Addr,
                                     i ? sizeof(SOCKADDR_IN6):sizeof(SOCKADDR_IN),
                                     NULL,
                                     0,
                                     &dwBytesReturned,
                                     &hOverLappeds[i * 2],
                                     NULL
                                     )) {
          if (WSA_IO_PENDING != WSAGetLastError()) {
            SOCKETERR("WSAIoctl");
            bResult = FALSE;
          }
        }
      }

      if (bResult) {
        if (SOCKET_ERROR == WSAIoctl(s[i],
                                     SIO_ADDRESS_LIST_CHANGE,
                                     NULL,
                                     0,
                                     NULL,
                                     0,
                                     &dwBytesReturned,
                                     &hOverLappeds[i * 2 + 1],
                                     NULL
                                     )) {
          if (WSA_IO_PENDING != WSAGetLastError()) {
            SOCKETERR("WSAIoctl");
            bResult = FALSE;
          }
        }
      }
    }
    if (bResult) {
      dwWaitResult = WSAWaitForMultipleEvents(EVENT_COUNT + 1,
                                              hEvents,
                                              FALSE,
                                              WSA_INFINITE,
                                              FALSE
                                              );
      switch (dwWaitResult) {
      case WSA_WAIT_TIMEOUT:
        break;
      case WSA_WAIT_EVENT_0:
        WSAResetEvent(hEvents[0]);
        if (write(mypipe, &"0", 1) == -1)
          bResult = FALSE;
        break;
      case WSA_WAIT_EVENT_0 + 1:
        WSAResetEvent(hEvents[1]);
        if (write(mypipe, &"1", 1) == -1)
          bResult = FALSE;
        break;
      case WSA_WAIT_EVENT_0 + 2:
        WSAResetEvent(hEvents[2]);
        if (write(mypipe, &"2", 1) == -1)
          bResult = FALSE;
        break;
      case WSA_WAIT_EVENT_0 + 3:
        WSAResetEvent(hEvents[3]);
        if (write(mypipe, &"3", 1) == -1)
          bResult = FALSE;
        break;
      case WSA_WAIT_EVENT_0 + 4:
        WSAResetEvent(hEvents[4]);
        bResult = FALSE;
        break;
      case WSA_WAIT_IO_COMPLETION:
        break;
      default:
        SOCKETERR("WSAWaitForMultipleEvents");
        bResult = FALSE;
      }    
    }
  }
  for (i = 0; i < EVENT_COUNT; i ++)
    CLOSESOCKEVENT(hEvents[i]);
  CLOSESOCKET(s[0]);
  CLOSESOCKET(s[1]);

  return dwReturn;
}

int cyginet_start_monitor_route_changes(int mypipe)
{
  if (WSA_INVALID_EVENT == event_notify_monitor_thread)
    event_notify_monitor_thread = WSACreateEvent();
  if (WSA_INVALID_EVENT == event_notify_monitor_thread)
    return -1;

  HANDLE hthread;
  hthread = CreateThread(NULL,              // default security
                         0,                 // stack size
                         libwinet_monitor_route_thread_proc,
                         (LPVOID)mypipe,
                         0,                 // startup flags
                         NULL
                         );
  if (hthread == NULL) {
    CLOSESOCKEVENT(event_notify_monitor_thread);
    event_notify_monitor_thread = WSA_INVALID_EVENT;
    return -1;
  }
  return 0;
}

int cyginet_stop_monitor_route_changes()
{
  int rc = 0;

  /* Notify thread to quit */
  WSASetEvent(event_notify_monitor_thread);
  CLOSESOCKEVENT(event_notify_monitor_thread);
  event_notify_monitor_thread = WSA_INVALID_EVENT;

  return rc;
}

/*
 * There are 3 ways to change a route:
 *
 * Before Windows Vista
 *
 * 1. IPv4 route: CreateIpForwardEntry
 *                DeleteIpForwardEntry
 *                SetIpForwardEntry
 *
 * 2. IPv6 route: command "netsh"
 *
 *    C:/> netsh interface ipv6 add route
 *                   prefix=<IPv6 address>/<integer>
 *                   interface=]<string>
 *                   nexthop=<IPv6 address>
 *                   metric=<integer>
 *
 *    Example:
 *
 *      add route prefix=3ffe::/16 interface=1 nexthop=fe80::1
 *
 * In Windows Vista and later
 *
 * 3. API: CreateIpForwardEntry2
 *         DeleteIpForwardEntry2
 *         SetIpForwardEntry2
 *
 */
static int
libwinet_edit_route_entry(const struct sockaddr *dest,
                          unsigned short plen,
                          const struct sockaddr *gate,
                          int ifindex,
                          unsigned int metric,
                          int cmdflag)
{

#if _WIN32_WINNT < _WIN32_WINNT_VISTA

  /* Add ipv6 route before Windows Vista */
  if(dest->sa_family == AF_INET6) {
    const int MAX_BUFFER_SIZE = 1024;
    const char * cmdformat = "netsh interface ipv6 %s route "
                             "prefix=%s/%d interface=%d "
                             "nexthop=%s %s%d";
    char cmdbuf[MAX_BUFFER_SIZE];
    char sdest[INET6_ADDRSTRLEN];
    char sgate[INET6_ADDRSTRLEN];

    if (NULL == inet_ntop(AF_INET6,
                          (const void*)(&(((SOCKADDR_IN6*)dest)->sin6_addr)),
                          sdest,
                          INET6_ADDRSTRLEN
                          ))
      return -1;
    if (NULL == inet_ntop(AF_INET6,
                          (const void*)(&(((SOCKADDR_IN6*)gate)->sin6_addr)),
                          sgate,
                          INET6_ADDRSTRLEN
                          ))
      return -1;

    if (snprintf(cmdbuf,
                 MAX_BUFFER_SIZE,
                 cmdformat,
                 cmdflag == RTM_ADD ? "add" :
                 cmdflag == RTM_DELETE ? "delete" : "set",
                 sdest,
                 plen,
                 ifindex,
                 sgate,
                 cmdflag == RTM_DELETE ? "#" : "metric=",
                 metric
                 ) >= MAX_BUFFER_SIZE)
      return -1;

    if (libwinet_run_command(cmdbuf) != 0)
      return -1;

  }

  /* Add ipv4 route before Windows Vista */
  else if (1) {

    MIB_IPFORWARDROW Row;
    unsigned long Res;
    memset(&Row, 0, sizeof(MIB_IPFORWARDROW));

    Row.dwForwardDest = (((SOCKADDR_IN*)dest) -> sin_addr).S_un.S_addr;
    Row.dwForwardPolicy = 0;
    Row.dwForwardNextHop = (((SOCKADDR_IN*)gate) -> sin_addr).S_un.S_addr;
    Row.dwForwardIfIndex = ifindex;
    /*
     * MIB_IPROUTE_TYPE_DIRECT <==> dwForwardNextHop == dwForwardDest
     * MIB_IPROUTE_TYPE_LOCAL  <==> dwForwardNextHop == Ip of the interface
     * MIB_IPROUTE_TYPE_INDIRECT all the others
     */
    Row.dwForwardType = Row.dwForwardNextHop == Row.dwForwardDest ? \
      MIB_IPROUTE_TYPE_DIRECT : MIB_IPROUTE_TYPE_INDIRECT;
    Row.dwForwardProto = MIB_IPPROTO_NETMGMT;
    Row.dwForwardAge = 0;
    Row.dwForwardNextHopAS = 0;
    Row.dwForwardMetric1 = metric;
    Row.dwForwardMetric2 = -1;
    Row.dwForwardMetric3 = -1;
    Row.dwForwardMetric4 = -1;
    Row.dwForwardMetric5 = -1;
    switch(cmdflag) {
    case RTM_ADD:
      Res = CreateIpForwardEntry(&Row);
      break;
    case RTM_DELETE:
      Res = DeleteIpForwardEntry(&Row);
      break;
    case RTM_CHANGE:
      Res = SetIpForwardEntry(&Row);
      break;
    default:
      Res = -1;
      break;
    }
    if (Res != NO_ERROR)
      return -1;
  }

  /* Use route command */
  else {
    /* route ADD dest MASK mask gate METRIC n IF index */
    /* route CHANGE dest MASK mask gate METRIC n IF index */
    /* route DELETE dest MASK mask gate METRIC n IF index */
    const int MAX_BUFFER_SIZE = 1024;
    char cmdbuf[MAX_BUFFER_SIZE];
    char sdest[INET_ADDRSTRLEN];
    char sgate[INET_ADDRSTRLEN];
    char smask[INET_ADDRSTRLEN];
    
    struct in_addr mask;
    plen2mask(plen, &mask);

    if (NULL == inet_ntop(AF_INET,
                          (const void*)(&(((SOCKADDR_IN*)dest)->sin_addr)),
                          sdest,
                          INET_ADDRSTRLEN
                          ))
      return -1;
    if (NULL == inet_ntop(AF_INET,
                          (const void*)(&(((SOCKADDR_IN*)gate)->sin_addr)),
                          sgate,
                          INET_ADDRSTRLEN
                          ))
      return -1;
    if (NULL == inet_ntop(AF_INET,
                          (const void*)(&mask),
                          smask,
                          INET_ADDRSTRLEN
                          ))
      return -1;

    if (snprintf(cmdbuf,
                 MAX_BUFFER_SIZE,
                 "route %s %s MASK %s %s METRIC %d IF %d",
                 cmdflag == RTM_ADD ? "add" :
                 cmdflag == RTM_DELETE ? "delete" : "change",
                 sdest,
                 smask,
                 sgate,
                 metric,
                 ifindex
                 ) >= MAX_BUFFER_SIZE)
      return -1;

    if (libwinet_run_command(cmdbuf) != 0)
      return -1;
  }

#else
  /* Add route entry after Windows Vista */
    MIB_IPFORWARDROW2 Row2;
    unsigned long Res;

    memset(&Row2, 0, sizeof(MIB_IPFORWARDROW2));

    Row2.InterfaceLuid = NULL;
    Row2.InterfaceIndex = ifindex;
    Row2.DestinationPrefix.PrefixLength = plen;
    memcpy(&Row2.DestinationPrefix.Prefix, dest, sizeof(SOCKADDR_INET));
    memcpy(&Row2.NextHop, gate, sizeof(SOCKADDR_INET)) ;
    Row2.SitePrefixLength = 255; /* INVALID */
    Row2.ValidLifetime = WSA_INFINITE;;
    Row2.PreferredLifetime = WSA_INFINITE;
    Row2.Metric = metric;
    Row2.Protocol = MIB_IPPROTO_NETMGMT;
    Row2.Loopback = gate->sa_family == AF_INET6 ?
      IN6_IS_ADDR_LOOPBACK(&(((SOCKADDR_IN6*)gate)->sin6_addr)) :
      IN_LOOPBACK(ntohl(((SOCKADDR_IN*)gate)->sin_addr.S_un.S_addr));
    Row2.AutoconfigureAddress = FALSE;
    Row2.Publish = FALSE;
    Row2.Immortal = 0;
    Row2.Age = 0;
    Row2.Origin = 0;            /* NlroManual */

    switch(cmdflag) {
    case 0:
      Res = CreateIpForwardEntry2(&Row);
      break;
    case 1:
      Res = SetIpForwardEntry2(&Row);
      break;
    case 2:
      Res = DeleteIpForwardEntry2(&Row);
      break;
    }

    if (Res != NO_ERROR)
      return -1;
  }

#endif  /*  _WIN32_WINNT < _WIN32_WINNT_VISTA */

  return 1;
}

static int
libwinet_set_registry_key(char *key, char * name, int value, int defvalue)
{
  HKEY hKey;
  unsigned long type;
  unsigned long size;
  unsigned long old;

  if (RegOpenKeyEx(HKEY_LOCAL_MACHINE, key, 0, KEY_READ | KEY_WRITE, &hKey) !=
      ERROR_SUCCESS)
    return -1;

  size = sizeof(old);

  if (RegQueryValueEx(hKey, name, NULL, &type, (unsigned char *)&old, &size) !=
      ERROR_SUCCESS || type != REG_DWORD)
    old = defvalue;

  if (RegSetValueEx(hKey,
                    name,
                    0,
                    REG_DWORD,
                    (unsigned char *)&value,
                    sizeof(value)
                    )) {
    RegCloseKey(hKey);
    return -1;
  }

  RegCloseKey(hKey);
  return old;
}

static int
libwinet_get_loopback_index(int family)
{
  IP_ADAPTER_ADDRESSES *pAdaptAddr = NULL;
  IP_ADAPTER_ADDRESSES *pTmpAdaptAddr = NULL;
  DWORD dwRet = 0;
  DWORD dwSize = 0x10000;
  DWORD dwReturn = 0;

  dwRet = GetAdaptersAddresses(family,
                               GAA_FLAG_SKIP_ANYCAST            \
                               | GAA_FLAG_SKIP_MULTICAST        \
                               | GAA_FLAG_SKIP_DNS_SERVER       \
                               | GAA_FLAG_SKIP_FRIENDLY_NAME,
                               NULL,
                               pAdaptAddr,
                               &dwSize
                               );
  if (ERROR_BUFFER_OVERFLOW == dwRet) {
    FREE(pAdaptAddr);
    if (NULL == (pAdaptAddr = (IP_ADAPTER_ADDRESSES*)MALLOC(dwSize)))
      return 0;
    dwRet = GetAdaptersAddresses(family,
                                 GAA_FLAG_SKIP_ANYCAST            \
                                 | GAA_FLAG_SKIP_MULTICAST        \
                                 | GAA_FLAG_SKIP_DNS_SERVER       \
                                 | GAA_FLAG_SKIP_FRIENDLY_NAME,
                                 NULL,
                                 pAdaptAddr,
                                 &dwSize
                                 );
  }
  if (NO_ERROR == dwRet) {

    pTmpAdaptAddr = pAdaptAddr;

    while (pTmpAdaptAddr) {

      if (IF_TYPE_SOFTWARE_LOOPBACK == pTmpAdaptAddr -> IfType) {
        dwReturn = family == AF_INET ?
                   pTmpAdaptAddr -> IfIndex :
                   pTmpAdaptAddr -> Ipv6IfIndex;
        break;
      }

      pTmpAdaptAddr = pTmpAdaptAddr->Next;
    }
  }

  FREE(pAdaptAddr);
  return dwReturn;
}

int
cyginet_set_ipv6_forwards(int value)
{
  char * key = "SYSTEM\\CurrentControlSet\\Services\\Tcpip6\\Parameters";

  return libwinet_set_registry_key(key,
                                   "IPEnableRouter",
                                   value,
                                   0
                                   );
}

int
cyginet_set_icmp6_redirect_accept(int value)
{
  char * key = "SYSTEM\\CurrentControlSet\\Services\\Tcpip6\\Parameters";

  return libwinet_set_registry_key(key,
                                   "EnableICMPRedirect",
                                   value,
                                   1
                                   );
}

/* 
 * On Windows Vista and later, wireless network cards are reported as
 * IF_TYPE_IEEE80211 by the GetAdaptersAddresses function.
 *
 * On earlier versions of Windows, wireless network cards are reported
 * as IF_TYPE_ETHERNET_CSMACD. On Windows XP with SP3 and on Windows
 * XP with SP2 x86 with the Wireless LAN API for Windows XP with SP2
 * installed, the WlanEnumInterfaces function can be used to enumerate
 * wireless interfaces on the local computer.
 */
int cyginet_interface_wireless(const char *ifname, int ifindex)
{
  LIBWINET_INTERFACE winf;

  if (1 == libwinet_get_interface_info(ifname, AF_INET6, ifindex, &winf)) {

    if (IF_TYPE_IEEE80211 == winf.IfType)
      return 1;

#if _WIN32_WINNT < _WIN32_WINNT_VISTA
    if (IF_TYPE_ETHERNET_CSMACD == winf.IfType) {
      return libwinet_is_wireless_interface(ifname);
    }
#endif

    return 0;
  }
  return -1;
}

int
cyginet_interface_mtu(const char *ifname, int ifindex)
{
  LIBWINET_INTERFACE winf;

  if (1 == libwinet_get_interface_info(ifname, AF_INET6, ifindex, &winf))
    return winf.Mtu;

  return -1;
}

int
cyginet_interface_operational(const char *ifname, int ifindex)
{
  LIBWINET_INTERFACE winf;

  if (1 == libwinet_get_interface_info(ifname, AF_INET6, ifindex, &winf))
    return winf.OperStatus;

  return -1;
}

int
cyginet_interface_ipv4(const char *ifname,
                       int ifindex,
                       unsigned char *addr_r)
{
  LIBWINET_INTERFACE winf;

  if (1 == libwinet_get_interface_info(ifname, AF_INET, ifindex, &winf)) {

    memcpy(addr_r, &((struct sockaddr_in*)&winf.Address)->sin_addr, 4);
    return 1;
  }
  return -1;
}

int
cyginet_interface_sdl(struct sockaddr_dl *sdl, char *ifname)
{
  IP_ADAPTER_ADDRESSES *pAdaptAddr = NULL;
  IP_ADAPTER_ADDRESSES *pTmpAdaptAddr = NULL;
  DWORD dwRet = 0;
  DWORD dwSize = 0x10000;
  DWORD dwReturn = -1;
  DWORD dwFamily = AF_UNSPEC;
  size_t size;

  int ifindex;

  if (0 == (ifindex = if_nametoindex(ifname)))
    return -1;

  dwRet = GetAdaptersAddresses(dwFamily,
                               GAA_FLAG_SKIP_ANYCAST            \
                               | GAA_FLAG_SKIP_MULTICAST        \
                               | GAA_FLAG_SKIP_DNS_SERVER       \
                               | GAA_FLAG_SKIP_FRIENDLY_NAME,
                               NULL,
                               pAdaptAddr,
                               &dwSize
                               );
  if (ERROR_BUFFER_OVERFLOW == dwRet) {
    FREE(pAdaptAddr);
    if (NULL == (pAdaptAddr = (IP_ADAPTER_ADDRESSES*)MALLOC(dwSize)))
      return -1;
    dwRet = GetAdaptersAddresses(dwFamily,
                                 GAA_FLAG_SKIP_ANYCAST            \
                                 | GAA_FLAG_SKIP_MULTICAST        \
                                 | GAA_FLAG_SKIP_DNS_SERVER       \
                                 | GAA_FLAG_SKIP_FRIENDLY_NAME,
                                 NULL,
                                 pAdaptAddr,
                                 &dwSize
                                 );
  }
  if (NO_ERROR == dwRet) {

    pTmpAdaptAddr = pAdaptAddr;

    while (pTmpAdaptAddr) {

      if (pTmpAdaptAddr -> Ipv6IfIndex == ifindex) {
        size = strlen(ifname);
        sdl -> sdl_family = 0;
        sdl -> sdl_index = pTmpAdaptAddr -> Ipv6IfIndex;
        sdl -> sdl_type = pTmpAdaptAddr -> IfType;
        sdl -> sdl_nlen = size;
        sdl -> sdl_alen = pTmpAdaptAddr -> PhysicalAddressLength;
        sdl -> sdl_slen = 0;
        memcpy(sdl -> sdl_data, ifname, size);
        memcpy(sdl -> sdl_data + size,
               pTmpAdaptAddr -> PhysicalAddress,
               pTmpAdaptAddr -> PhysicalAddressLength
               );
        sdl -> sdl_len = ((void*)(sdl->sdl_data) - (void*)sdl) + size   \
          + pTmpAdaptAddr -> PhysicalAddressLength;
        dwReturn = 0;
        break;
      }

      pTmpAdaptAddr = pTmpAdaptAddr->Next;
    }

  }

  FREE(pAdaptAddr);
  return dwReturn;
}

int
cyginet_loopback_index(int family)
{
  return libwinet_get_loopback_index(family);
}

static PMIB_IPFORWARDTABLE
libwinet_get_ipforward_table(int forder)
{
  DWORD dwSize = 0;
  PMIB_IPFORWARDTABLE pIpForwardTable;
  pIpForwardTable = (PMIB_IPFORWARDTABLE)MALLOC(sizeof(MIB_IPFORWARDTABLE));
  if (NULL == pIpForwardTable)
    return NULL;

  if (ERROR_INSUFFICIENT_BUFFER == GetIpForwardTable(pIpForwardTable,
                                                     &dwSize,
                                                     forder
                                                     )) {
    FREE(pIpForwardTable);
    pIpForwardTable = (PMIB_IPFORWARDTABLE) MALLOC(dwSize);
    if (pIpForwardTable == NULL)
      return NULL;
  }
  if (NO_ERROR == GetIpForwardTable(pIpForwardTable,
                                    &dwSize,
                                    forder))
    return pIpForwardTable;
  return NULL;  
}

/*
 * There are 3 ways to dump route table in the Windows:
 *
 * Before Windows Vista
 *
 * 1. IPv4 route: GetIpForwardTable
 *
 * 2. IPv6 route: command "netsh"
 *
 *    C:/> netsh interface ipv6 show route verbose
 *
 * In Windows Vista and later
 *
 * 3. API: GetIpForwardTable2
 *
 */
int
cyginet_dump_route_table(struct kernel_route *routes, int maxroutes)
{
  
  ULONG NumEntries = -1;
  struct kernel_route *proute;
  int i;

#if _WIN32_WINNT < _WIN32_WINNT_VISTA

  /* First dump ipv6 route */
  NumEntries = libwinet_dump_ipv6_route_table(routes, maxroutes);

  if (NumEntries < 0)
    return -1;

  /* Then ipv4 route table */
  SOCKADDR_IN * paddr;
  PMIB_IPFORWARDTABLE pIpForwardTable;
  PMIB_IPFORWARDROW pRow;
  if (NULL == (pIpForwardTable = libwinet_get_ipforward_table(0)))
    return -1;
  
  {
    proute = routes + NumEntries;
    NumEntries += pIpForwardTable->dwNumEntries;
    if (NumEntries > maxroutes) {
      FREE(pIpForwardTable);
      return -1;
    }
    pRow = pIpForwardTable->table;    
    for (i = 0;
         i < (int) pIpForwardTable->dwNumEntries;
         i++, proute ++, pRow ++) {

      /* libwinet_map_ifindex_to_ipv6ifindex */
      proute -> ifindex = pRow -> dwForwardIfIndex;
      proute -> metric = pRow -> dwForwardMetric1;
      proute -> proto = pRow -> dwForwardProto;
      proute -> plen = mask2len((unsigned char*)&(pRow -> dwForwardMask), 4);

      /* Note that the IPv4 addresses returned in GetIpForwardTable
       * entries are in network byte order
       */
      paddr = (SOCKADDR_IN*)proute -> prefix;
      paddr -> sin_family = AF_INET;
      (paddr -> sin_addr).S_un.S_addr = pRow -> dwForwardDest;

      paddr = (SOCKADDR_IN*)proute -> gw;
      paddr -> sin_family = AF_INET;
      (paddr -> sin_addr).S_un.S_addr = pRow -> dwForwardNextHop;
    }
    FREE(pIpForwardTable);
  }

#else
  PMIB_IPFORWARD_TABLE2 pIpForwardTable2;
  PMIB_IPFORWARD_ROW2 pRow2;

  /* From Windows Vista later, use GetIpForwardTable2 instead */
  if (NO_ERROR == GetIpForwardTable2(family,
                                     pIpForwardTable2
                                     0)) {

    if (pIpForwardTable2 -> NumEntries < maxroutes) {

      proute = routes + NumEntries;
      NumEntries = pIpForwardTable2->dwNumEntries;
      pRow2 = pIpForwardTable2 -> Table;

      for (i = 0; i < NumEntries; i++, proute ++, pRow2 ++) {
        proute -> ifindex = pRow2 -> InterfaceIndex;
        proute -> metric = pRow2 -> Metric;
        proute -> proto = pRow2 -> Protocol;
        proute -> plen = (pRow2 -> DestinationPrefix).PrefixLength;
        memcpy(proute -> prefix,
               (pRow2 -> DestinationPrefix).DestinationPrefix,
               sizeof(SOCKADDR_INET)
               );
        memcpy(proute -> gw,
               pRow2 -> NextHop,
               sizeof(SOCKADDR_INET)
               );
      }

    }
    FreeMibTable(pIpForwardTable2);
  }
#endif

  return NumEntries;
}

int
cyginet_add_route_entry(const struct sockaddr *dest,
                        unsigned short plen,
                        const struct sockaddr *gate,
                        int ifindex,
                        unsigned int metric)
{
  return libwinet_edit_route_entry(dest, plen, gate, ifindex, metric, 1);
}

int
cyginet_delete_route_entry(const struct sockaddr *dest,
                           unsigned short plen,
                           const struct sockaddr *gate,
                           int ifindex,
                           unsigned int metric)
{
  return libwinet_edit_route_entry(dest, plen, gate, ifindex, metric, 2);
}

int
cyginet_update_route_entry(const struct sockaddr *dest,
                           unsigned short plen,
                           const struct sockaddr *gate,
                           int ifindex,
                           unsigned int metric)
{
  return libwinet_edit_route_entry(dest, plen, gate, ifindex, metric, 3);
}

/*
 * This function is used to read route socket to get changes of route
 * table, and return a struct rt_msghdr in the buffer. However I can't
 * find windows API to implement it.
 */
int
cyginet_read_route_socket(void *buffer, size_t size)
{
  /* TODO */
  return 0;
}

int cyginet_startup()
{
  WORD wVersionRequested;
  WSADATA wsaData;

  /* Use the MAKEWORD(lowbyte, highbyte) macro declared in Windef.h */
  wVersionRequested = MAKEWORD(2, 2);
  return WSAStartup(wVersionRequested, &wsaData);
}

void cyginet_cleanup()
{
  WSACleanup();
}

/* The following functions are reserved. */
#if 0

static int
convert_ipv6_route_table2()
{
  const MAX_LINE_SIZE = 80;
  const char * command = "netsh interface ipv6 show route verbose";
  /* One example entry of netsh output
     Prefix            : fe80::1/128
     Interface 1       : Loopback Pseudo-Interface
     Gateway           : fe80::1
     Metric            : 4
     Publish           : no
     Type              : System
     Valid Lifetime    : infinite
     Preferred Lifetime: infinite
     Site Prefix Length: 0
  */

  FILE *output;
  char buffer[MAX_LINE_SIZE];
  int index = -1;
  size_t size;
  char *s, *p;
  int ifindex;
  MIB_IPFORWARD_ROW2 iprow;
  MIB_IPFORWARD_ROW2 *piprow = &iprow;

  output = popen (command, "r");
  if (!output)
    return -1;

  /* Ignore the first line */
  fgets(buffer, MAX_LINE_SIZE, output);

  memset(piprow, 0, sizeof(MIB_IPFORWARD_ROW2));
  piprow -> Protocol = MIB_IPPROTO_OTHER;

  /* Read the output until EOF */
  while (fgets(buffer, MAX_LINE_SIZE, output)) {

    if (('\n' == buffer[0]) || ('\r' == buffer[0]))
      continue;

    if (NULL == (s = strchr(buffer, ':')))
      break;

    *s ++ = 0;
    s ++;

    if (strncmp(buffer, "Prefix", 6) == 0) {

      index ++;

      if (NULL == (p = strchr(s, '/')))
        break;
      *p ++ = 0;

      if (WSAStringToAddress(s,
                             AF_INET6,
                             NULL,
                             (LPSOCKADDR)(&(piprow -> DestinationPrefix.Prefix)),
                             &size
                             ) == SOCKET_ERROR)
        break;

      piprow -> DestinationPrefix.PrefixLength = strtol(p, NULL, 10);
    }

    else if (strncmp(buffer, "Interface", 9) == 0) {
      ifindex = strtol(buffer + 9, NULL, 10);
      piprow -> InterfaceIndex = ifindex;
    }

    else if (strncmp(buffer, "Gateway", 7) == 0) {
      /* NextHop */
      /* Loopback: A value that specifies if the route is a loopback
         route (the gateway is on the local host). */
    }

    else if (strncmp(buffer, "Metric", 6) == 0)
      piprow -> Metric = strtol(s, NULL, 10);

    else if (strncmp(buffer, "Publish", 7) == 0)
      piprow -> Publish = (strncmp("yes", s, 3) == 0);

    else if (strncmp(buffer, "Type", 4) == 0) {

      if (strncmp("Manual", s, 6) == 0) {
        piprow -> Origin = NlroManual;
      }
      else if (strncmp("System", s, 6) == 0) {
        piprow -> Origin = NlroDHCP;
      }
      else if (strncmp("Autoconf", s, 8) == 0) {
        piprow -> Origin = Nlro6to4;
        piprow -> AutoconfigureAddress = 1;
      }
    }

    else if (strncmp(buffer, "Valid Lifetime", 14) == 0)
      piprow -> ValidLifetime = convert_time_from_string_to_ulong(s);

    else if (strncmp(buffer, "Preferred Lifetime", 18) == 0)
      piprow -> PreferredLifetime = convert_time_from_string_to_ulong(s);

    else if (strncmp(buffer, "Site Prefix Length", 18) == 0)
      piprow -> SitePrefixLength = (UCHAR)strtol(s, NULL, 10);

    else {
      /* Immortal: persistent entry */
      /* Age */
      break;
    }
  }

  /* Return the exit code of command */
  return pclose (output);
}

/*
 * Output format: struct rt_msghdr
 *
 *     rtm_msglen
 *
 *     rtm_type    =  RTM_GET
 *
 *     rtm_index   =  IfIndex for Ipv4
 *                    Ipv6IfIndex for Ipv6
 *
 *     rtm_flags   =  RTF_HOST:     All netmask bits are 1.
 *                    RTF_GATEWAY:  Destination is a gateway.
 *
 *     rtm_addrs   =  RTA_DST RTA_GATEWAY RTA_NETMASK
 *     rtm_errno      Set when failed.
 *
 * RTF_HOST:  Set when all netmask bits are 1
 *
 * RTF_GATEWAY: Set when gateway is not local address.
 *              dwForwardNextHop is not
 *
 */
static int
convert_ipv6_route_table_to_rtm(struct rt_msghdr *rtm,
                                int maxroutes)
{
  const MAX_LINE_SIZE = 80;
  const char * command = "netsh interface ipv6 show route verbose";
  /* One example entry of netsh output
     Prefix            : fe80::1/128
     Interface 1       : Loopback Pseudo-Interface
     Gateway           : fe80::1
     Metric            : 4
     Publish           : no
     Type              : System
     Valid Lifetime    : infinite
     Preferred Lifetime: infinite
     Site Prefix Length: 0
  */

  FILE *output;
  char buffer[MAX_LINE_SIZE];
  int index = -1;
  size_t size;
  char *s, *p;
  int ifindex;
  int start = 0;

  SOCKADDR *sa;
  int msg_len = sizeof(struct rt_msghdr) + 3 * sizeof(SOCKADDR);

  output = popen (command, "r");
  if (!output)
    return -1;

  /* Ignore the first line */
  fgets(buffer, MAX_LINE_SIZE, output);

  /* Read the output until EOF */
  while (fgets(buffer, MAX_LINE_SIZE, output)) {

    if (('\n' == buffer[0]) || ('\r' == buffer[0]))
      continue;

    if (NULL == (s = strchr(buffer, ':')))
      break;

    *s ++ = 0;
    s ++;

    if (strncmp(buffer, "Prefix", 6) == 0) {
      rtm -> rtm_msglen = msg_len;
      rtm -> rtm_version = RTM_VERSION;
      rtm -> rtm_type = RTM_GET;
      rtm -> rtm_addrs = RTA_DST | RTA_GATEWAY | RTA_NETMASK;
      sa = (SOCKADDR*)(rtm + 1);

      if (NULL == (p = strchr(s, '/')))
        break;
      *p ++ = 0;

      if (WSAStringToAddress(s,
                             AF_INET6,
                             NULL,
                             sa,
                             &size
                             ) == SOCKET_ERROR)
        break;
      // PrefixLength = strtol(p, NULL, 10);
      sa ++;
    }

    else if (strncmp(buffer, "Interface", 9) == 0)
      rtm -> rtm_index = strtol(buffer + 9, NULL, 10);

    else if (strncmp(buffer, "Gateway", 7) == 0) {
      /* NextHop */
      /* Loopback: A value that specifies if the route is a loopback
         route (the gateway is on the local host). */
      if (WSAStringToAddress(s,
                             AF_INET6,
                             NULL,
                             sa,
                             &size
                             ) == SOCKET_ERROR)
        break;
      sa ++;
      /* Netmask */
    }

    else if (strncmp(buffer, "Site Prefix Length", 18) == 0) {
      rtm = (struct rt_msghdr*)((void*)rtm + msg_len);
      start ++;
      if (start > maxroutes)
        break;
    }

    else {
      /* Immortal: persistent entry */
      /* Age */
    }
  }

  pclose (output);
  return start;
}

static int
libwinet_map_ifindex_to_ipv6ifindex(int ifindex)
{
  IP_ADAPTER_ADDRESSES *pAdaptAddr = NULL;
  IP_ADAPTER_ADDRESSES *pTmpAdaptAddr = NULL;
  DWORD dwRet = 0;
  DWORD dwSize = 0x10000;
  DWORD dwReturn = 0;
  DWORD Family = AF_UNSPEC;

  dwRet = GetAdaptersAddresses(Family,
                               GAA_FLAG_SKIP_ANYCAST            \
                               | GAA_FLAG_SKIP_MULTICAST        \
                               | GAA_FLAG_SKIP_DNS_SERVER       \
                               | GAA_FLAG_SKIP_FRIENDLY_NAME,
                               NULL,
                               pAdaptAddr,
                               &dwSize
                               );
  if (ERROR_BUFFER_OVERFLOW == dwRet) {
    FREE(pAdaptAddr);
    if (NULL == (pAdaptAddr = (IP_ADAPTER_ADDRESSES*)MALLOC(dwSize)))
      return 0;
    dwRet = GetAdaptersAddresses(Family,
                                 GAA_FLAG_SKIP_ANYCAST            \
                                 | GAA_FLAG_SKIP_MULTICAST        \
                                 | GAA_FLAG_SKIP_DNS_SERVER       \
                                 | GAA_FLAG_SKIP_FRIENDLY_NAME,
                                 NULL,
                                 pAdaptAddr,
                                 &dwSize
                                 );
  }
  if (NO_ERROR == dwRet) {

    pTmpAdaptAddr = pAdaptAddr;

    while (pTmpAdaptAddr) {
      if (pTmpAdaptAddr -> IfIndex == ifindex) {
        dwReturn = pTmpAdaptAddr -> Ipv6IfIndex;
        break;
      }

      pTmpAdaptAddr = pTmpAdaptAddr->Next;
    }
  }

  FREE(pAdaptAddr);
  return dwReturn;
}

static ULONG
convert_time_from_string_to_ulong(const char * stime)
{
  char *s;
  long k;
  long result;
  if (strncmp(stime, "infinite", 8) == 0)
    return WSA_INFINITE;

  result = 0;
  s = (char*)stime;
  do {
    k = strtol(s, &s, 10);
    if (*s == 's') {
      result += k;
      s = NULL;
    }
    else if (*s == 'm') {
      result += 60 * k;
      s ++;
    }
    else if (*s == 'h') {
      result += 3600 * k;
      s ++;
    }
    else if (*s == 'd') {
      result += 3600 * 24 * k;
      s ++;
    }
    else s = NULL;
  } while (s);

  return result;
}

/*
 * It's another way to tell wireless netcard, query device status by
 * DeviceIoControl.
 *
 */
#if !defined OID_802_11_CONFIGURATION
#define OID_802_11_CONFIGURATION 0x0d010211
#endif

#if !defined IOCTL_NDIS_QUERY_GLOBAL_STATS
#define IOCTL_NDIS_QUERY_GLOBAL_STATS 0x00170002
#endif

static int
libwinet_is_wireless_device(const wchar_t *pszwAdapterName)
{
  const int MAX_DEV_NAME_LEN = 45;
  const int MAX_OUT_BUF_SIZE = 100;
  wchar_t DevName[MAX_DEV_NAME_LEN];
  HANDLE DevHand;
  unsigned int ErrNo;
  unsigned int Oid;
  unsigned char OutBuff[MAX_OUT_BUF_SIZE];
  unsigned long OutBytes;

  if (swprintf(DevName,
               MAX_DEV_NAME_LEN,
               L"\\\\.\\%ls",
               pszwAdapterName
               ) >= MAX_DEV_NAME_LEN)
    return -1;

  DevHand = CreateFileW(DevName,
                        GENERIC_READ,
                        FILE_SHARE_READ | FILE_SHARE_WRITE,
                        NULL,
                        OPEN_EXISTING,
                        FILE_ATTRIBUTE_NORMAL,
                        NULL
                        );

  if (DevHand == INVALID_HANDLE_VALUE) {
    ErrNo = GetLastError();
    return -1;
  }

  Oid = OID_802_11_CONFIGURATION;

  if (!DeviceIoControl(DevHand,
                       IOCTL_NDIS_QUERY_GLOBAL_STATS,
                       &Oid,
                       sizeof(Oid),
                       OutBuff,
                       sizeof(OutBuff),
                       &OutBytes,
                       NULL
                       )) {

    ErrNo = GetLastError();
    CloseHandle(DevHand);

    /* OID not supported. Device probably not wireless. */
    if ((ErrNo == ERROR_GEN_FAILURE)
        || (ErrNo == ERROR_INVALID_PARAMETER)
        || ErrNo == ERROR_NOT_SUPPORTED) {
      return 0;
    }

    /* DeviceIoControl() Error */
    return -1;
  }

  CloseHandle(DevHand);
  return 1;
}

static int
libwinet_ipv6_interfaces_forwards(int forward)
{
  const int MAX_BUFFER_SIZE = 80;
  char cmdbuf[MAX_BUFFER_SIZE];
  int result;
  
  struct if_nameindex * p;
  struct if_nameindex * ptr;
  if (NULL == (ptr = (struct if_nameindex *)if_nameindex()))
    return -1;

  p = ptr;
  while (p -> if_index) {
    if (snprintf(cmdbuf,
                 MAX_BUFFER_SIZE,
                 "ipv6 ifc %d %cforward",
                 p -> if_index,
                 forward ? ' ' : '-'
                 ) >= MAX_BUFFER_SIZE)
      break;
    if (libwinet_run_command(cmdbuf) != 0)
      break;
    p ++;
  }
  result = ! (p -> if_index);
  if_freenameindex(ptr);
  return result;
}

BOOL RouteLookup(SOCKADDR   *destAddr,
                 int         destLen,
                 SOCKADDR   *localAddr,
                 int         localLen)
{
  DWORD       dwBytes = 0;
  BOOL        bRet = TRUE;
  CHAR        szAddr[MAX_PATH] = {0};
  SOCKET      s = INVALID_SOCKET;


  if (INVALID_SOCKET == (s = socket(destAddr->sa_family,SOCK_DGRAM,0)))
    {
      SOCKETERR("socket");
      return FALSE;
    }

  if (SOCKET_ERROR == WSAIoctl(s,
                               SIO_ROUTING_INTERFACE_QUERY,
                               destAddr,
                               destLen,
                               localAddr,
                               localLen,
                               &dwBytes,
                               NULL,
                               NULL
                               ))
    {
      SOCKETERR("WSAIoctl");
      bRet = FALSE;
    }

  if (bRet)
    {
      dwBytes = sizeof(szAddr);

      ZeroMemory(szAddr,dwBytes);

      WSAAddressToStringA(destAddr,
                          (DWORD)destLen,
                          NULL,
                          szAddr,
                          &dwBytes
                          );

      dwBytes = sizeof(szAddr);

      ZeroMemory(szAddr,dwBytes);

      WSAAddressToStringA(localAddr,
                          (DWORD)localLen,
                          NULL,
                          szAddr,
                          &dwBytes
                          );
    }

  CLOSESOCKET(s);

  return bRet;
}

DWORD GetInterfaceIndexForAddress(SOCKADDR *pAddr)
{
  IP_ADAPTER_UNICAST_ADDRESS *pTmpUniAddr = NULL;
  IP_ADAPTER_ADDRESSES *pAdaptAddr = NULL;
  IP_ADAPTER_ADDRESSES *pTmpAdaptAddr = NULL;
  BOOL bFound = FALSE;
  DWORD dwRet = 0;
  DWORD dwReturn = (DWORD) SOCKET_ERROR;
  DWORD dwSize = 0x10000;
  DWORD Family = AF_UNSPEC;

  switch (pAddr->sa_family) {
  case AF_INET:
    Family = AF_INET;
    break;
  case AF_INET6:
    Family = AF_INET6;
    break;
  default:
    WSASetLastError(WSAEAFNOSUPPORT);
    break;
  }
  if (NULL == (pAdaptAddr = (IP_ADAPTER_ADDRESSES*)MALLOC(dwSize)))
    return -1;

  dwRet = GetAdaptersAddresses(Family,
                               GAA_FLAG_SKIP_ANYCAST \
                               | GAA_FLAG_SKIP_MULTICAST \
                               |GAA_FLAG_SKIP_DNS_SERVER,
                               NULL,
                               pAdaptAddr,
                               &dwSize
                               );
  if (ERROR_BUFFER_OVERFLOW == dwRet) {
    FREE(pAdaptAddr);
    if (NULL == (pAdaptAddr = (IP_ADAPTER_ADDRESSES*)MALLOC(dwSize)))
      return -1;
    dwRet = GetAdaptersAddresses(Family,
                                 GAA_FLAG_SKIP_ANYCAST \
                                 | GAA_FLAG_SKIP_MULTICAST \
                                 |GAA_FLAG_SKIP_DNS_SERVER,
                                 NULL,
                                 pAdaptAddr,
                                 &dwSize
                                 );
  }
  if (NO_ERROR == dwRet) {

    pTmpAdaptAddr = pAdaptAddr;

    while (pTmpAdaptAddr) {

      //look at each IP_ADAPTER_UNICAST_ADDRESS node
      pTmpUniAddr = pTmpAdaptAddr->FirstUnicastAddress;

      while (pTmpUniAddr) {

        if (AF_INET == pTmpUniAddr->Address.lpSockaddr->sa_family) {

          /* IN4_ADDR_EQUAL */
          if (memcmp(&((SOCKADDR_IN*)pAddr)->sin_addr,
                     &((SOCKADDR_IN*)pTmpUniAddr->Address.lpSockaddr)->sin_addr,
                     sizeof(SOCKADDR_IN)
                     ) == 0)
            {
              dwReturn = pTmpAdaptAddr->IfIndex;
              bFound = TRUE;

              break;
            }

        }
        else {
          /* IN6_ADDR_EQUAL */
          if (memcmp(&((SOCKADDR_IN6*)pAddr)->sin6_addr,
                     &((SOCKADDR_IN6*)pTmpUniAddr->Address.lpSockaddr)->sin6_addr,
                     sizeof(SOCKADDR_IN6)
                     ) == 0)
            {
              dwReturn = pTmpAdaptAddr->Ipv6IfIndex;
              bFound = TRUE;

              break;
            }
        }

        pTmpUniAddr = pTmpUniAddr->Next;

      }

      if (bFound)
        break;

      pTmpAdaptAddr = pTmpAdaptAddr->Next;

    }

  }

  FREE(pAdaptAddr);
  return dwReturn;
}

VOID PrintAllInterfaces()
{
  IP_ADAPTER_ADDRESSES *pAdaptAddr = NULL;
  IP_ADAPTER_ADDRESSES *pTmpAdaptAddr = NULL;
  DWORD dwRet = 0;
  DWORD dwSize = 0x10000;
  DWORD Family = AF_UNSPEC;

  if (NULL == (pAdaptAddr = (IP_ADAPTER_ADDRESSES*)MALLOC(dwSize))) {
    printf("Memory error.\n");
    return ;
  }
  dwRet = GetAdaptersAddresses(Family,
                               GAA_FLAG_SKIP_ANYCAST \
                               | GAA_FLAG_SKIP_MULTICAST \
                               |GAA_FLAG_SKIP_DNS_SERVER,
                               NULL,
                               pAdaptAddr,
                               &dwSize
                               );
  if (ERROR_BUFFER_OVERFLOW == dwRet) {
    FREE(pAdaptAddr);
    if (NULL == (pAdaptAddr = (IP_ADAPTER_ADDRESSES*)MALLOC(dwSize))) {
      printf("Memory error.\n");
      return ;
    }
    dwRet = GetAdaptersAddresses(Family,
                                 GAA_FLAG_SKIP_ANYCAST \
                                 | GAA_FLAG_SKIP_MULTICAST \
                                 |GAA_FLAG_SKIP_DNS_SERVER,
                                 NULL,
                                 pAdaptAddr,
                                 &dwSize
                                 );
  }
  if (NO_ERROR == dwRet) {

    pTmpAdaptAddr = pAdaptAddr;

    while (pTmpAdaptAddr) {
      printf("If6Index:\t %ld\n", pTmpAdaptAddr -> Ipv6IfIndex);
      printf("If4Index:\t %ld\n", pTmpAdaptAddr -> IfIndex);
      printf("Friendly Name:\t %S\n", pTmpAdaptAddr -> FriendlyName);
      printf("Adapter Name:\t %s\n", pTmpAdaptAddr -> AdapterName);
      printf("IfType:\t %ld\n", pTmpAdaptAddr -> IfType);
      printf("Oper Status:\t %d\n", pTmpAdaptAddr -> OperStatus);
      printf("\n\n");

      pTmpAdaptAddr = pTmpAdaptAddr->Next;
    }
  }

  else
    printf("GetAdaptersAddresses failed.\n");

  FREE(pAdaptAddr);
}

void WaitForNetworkChnages()
{
  WSAQUERYSET querySet = {0};
  querySet.dwSize = sizeof(WSAQUERYSET);
  querySet.dwNameSpace = NS_NLA;

  HANDLE LookupHandle = NULL;
  WSALookupServiceBegin(&querySet, LUP_RETURN_ALL, &LookupHandle);
  DWORD BytesReturned = 0;
  WSANSPIoctl(LookupHandle,
              SIO_NSP_NOTIFY_CHANGE,
              NULL,
              0,
              NULL,
              0,
              &BytesReturned,
              NULL
              );
  WSALookupServiceEnd(LookupHandle);
}

DWORD GetConnectedNetworks()
{
  WSAQUERYSET qsRestrictions;
  DWORD dwControlFlags;
  HANDLE hLookup;
  DWORD dwCount = 0;

  ZeroMemory(&qsRestrictions, sizeof(WSAQUERYSET));
  qsRestrictions.dwSize = sizeof(WSAQUERYSET);
  qsRestrictions.dwNameSpace = NS_ALL;
  dwControlFlags = LUP_RETURN_ALL;

  int result = WSALookupServiceBegin(&qsRestrictions,
    dwControlFlags, &hLookup);

  DWORD dwBufferLength;
  WSAQUERYSET qsResult;
  while (0 == result)
  {
    ZeroMemory(&qsResult, sizeof(WSAQUERYSET));
    result = WSALookupServiceNext(hLookup,
                                  LUP_RETURN_NAME,
                                  &dwBufferLength,
                                  &qsResult
                                  );
    dwCount ++;
  }

  result = WSALookupServiceEnd(hLookup);
  return dwCount;
}

#endif  /* Unused */

/* ------------------------------------------------------------- */
/*                                                               */
/* The following functions are used to test or verify something. */
/*                                                               */
/* ------------------------------------------------------------- */
#ifdef TEST_CYGINET

static int
libwinet_set_forward_entry(char* pszDest,
                           char* pszNetMask,
                           char* pszGateway,
                           DWORD dwIfIndex,
                           DWORD dwMetric)
{
    DWORD dwStatus;

    MIB_IPFORWARDROW routeEntry;            // Ip routing table row entry
    
    memset(&routeEntry, 0, sizeof(MIB_IPFORWARDROW));

    // converting and checking input arguments...
    if (pszDest == NULL || pszNetMask == NULL || pszGateway == NULL)
    {
        printf("IpRoute: Bad Argument\n");
        return -1;
    }

    routeEntry.dwForwardDest = inet_addr(pszDest); // convert dotted ip addr. to ip addr.
    if (routeEntry.dwForwardDest == INADDR_NONE)
    {
        printf("IpRoute: Bad Destination %s\n", pszDest);
        return -1;
    }

    routeEntry.dwForwardMask = inet_addr(pszNetMask);
    if ( (routeEntry.dwForwardMask == INADDR_NONE) && 
         (strcmp("255.255.255.255", pszNetMask) != 0) )
    {
        printf("IpRoute: Bad Mask %s\n", pszNetMask);
        return -1;
    }

    routeEntry.dwForwardNextHop = inet_addr(pszGateway);
    if (routeEntry.dwForwardNextHop == INADDR_NONE)
    {
        printf("IpRoute: Bad Gateway %s\n", pszGateway);
        return -1;
    }

    if ( (routeEntry.dwForwardDest & routeEntry.dwForwardMask) != routeEntry.dwForwardDest)
    {
        printf("IpRoute: Invalid Mask %s\n", pszNetMask);
        return -1;
        
    }

    routeEntry.dwForwardIfIndex = dwIfIndex;
    routeEntry.dwForwardMetric1 = dwMetric;

    // some default values
    routeEntry.dwForwardProto = MIB_IPPROTO_NETMGMT;
    routeEntry.dwForwardMetric2 = (DWORD)-1;
    routeEntry.dwForwardMetric3 = (DWORD)-1;
    routeEntry.dwForwardMetric4 = (DWORD)-1;
    
    dwStatus = SetIpForwardEntry(&routeEntry); 
    if (dwStatus != NO_ERROR)
    {
        printf("IpRoute: couldn't add (%s), dwStatus = %lu.\n",
                    pszDest, dwStatus);
        return -1;
    }
    return 0;
}

static void
runTestCases()
{
  printf("\n\nTest getifaddrs works in the Cygwin:\n\n");
  {
    struct ifaddrs * piftable, *pif;
    getifaddrs(&piftable);
    for (pif = piftable; pif != NULL; pif = pif -> ifa_next)
      printf("Iterface name is %s\n", pif -> ifa_name);
    freeifaddrs(piftable);
  }

  printf("\n\nTest if_indexname works in the Cygwin:\n\n");
  {
    struct if_nameindex * ptr = (struct if_nameindex *)if_nameindex();
    if (ptr) {
      struct if_nameindex * p = ptr;
      while (p -> if_index) {
        printf("%d\t\t%s\n", p -> if_index, p -> if_name);
        p ++;
      }
      if_freenameindex(ptr);
    }
  }

  printf("\n\nTest if_indextoname works in the Cygwin:\n\n");
  {
    CHAR ifname[256];
    if (if_indextoname(1, ifname))
      printf("Interface Index 1: %s\n", ifname);
    else
      printf("if_indextoname failed\n");
  }

#if _WIN32_WINNT < _WIN32_WINNT_VISTA

  printf("\n\nTest libwinet_dump_ipv6_route_table:\n\n");
  {
    struct kernel_route routes[100];
    memset(routes, 0, sizeof(struct kernel_route) * 100);
    int n = libwinet_dump_ipv6_route_table(routes, 100);
    printf("Get route numbers: %d\n", n);
  }

  printf("\n\nTest libwinet_run_command:\n\n");
  {
    printf("ls command return %d\n", libwinet_run_command("ls"));
  }

  printf("\n\nTest libwinet_is_wireless_interface:\n\n");
  {
    struct if_nameindex * ptr = (struct if_nameindex *)if_nameindex();
    if (ptr) {
      struct if_nameindex * p = ptr;
      while (p -> if_index) {
        printf("%s is wireless netcard: %d\n",
               p -> if_name,
               libwinet_is_wireless_interface(p -> if_name)
               );
        p ++;
      }
      if_freenameindex(ptr);
    }
  }

#endif  /* _WIN32_WINNT < _WIN32_WINNT_VISTA */

  printf("\n\nTest libwinet_get_loopback_index:\n\n");
  {
    printf("Ipv4 loopback ifindex is %d\n",
           libwinet_get_loopback_index(AF_INET)
           );
    printf("Ipv6 loopback ifindex is %d\n",
           libwinet_get_loopback_index(AF_INET6)
           );
  }

  printf("\n\nTest cyginet_set_ipv6_forwards:\n\n");
  {
    printf("cyginet_set_ipv6_forwards(1) return %d\n",
           cyginet_set_ipv6_forwards(1)
           );
    printf("cyginet_set_ipv6_forwards(0) return %d\n",
           cyginet_set_ipv6_forwards(0)
           );
  }

  printf("\n\nTest cyginet_set_icmp6_redirect_accept:\n\n");
  {
    printf("cyginet_set_icmp6_redirect_accept(0) return %d\n",
           cyginet_set_icmp6_redirect_accept(0)
           );
    printf("cyginet_set_icmp6_redirect_accept(1) return %d\n",
           cyginet_set_icmp6_redirect_accept(1)
           );
  }

  printf("\n\nTest cyginet_interface_wireless:\n\n");
  {
    struct if_nameindex * ptr = (struct if_nameindex *)if_nameindex();
    if (ptr) {
      struct if_nameindex * p = ptr;
      int n;
      while (p -> if_index) {
        n = cyginet_interface_wireless(p -> if_name, p -> if_index);
        printf("%s is wireless netcard: %d\n", p -> if_name, n);
        p ++;
      }
      if_freenameindex(ptr);
    }
  }

  printf("\n\nTest cyginet_interface_mtu:\n\n");
  {
    struct if_nameindex * ptr = (struct if_nameindex *)if_nameindex();
    if (ptr) {
      struct if_nameindex * p = ptr;
      int n;
      while (p -> if_index) {
        n = cyginet_interface_mtu(p -> if_name, p -> if_index);
        printf("mtu of %s is : %d\n", p -> if_name, n);
        p ++;
      }
      if_freenameindex(ptr);
    }
  }

  printf("\n\nTest cyginet_interface_operational:\n\n");
  {
    struct if_nameindex * ptr = (struct if_nameindex *)if_nameindex();
    if (ptr) {
      struct if_nameindex * p = ptr;
      int n;
      while (p -> if_index) {
        n = cyginet_interface_operational(p -> if_name, p -> if_index);
        printf("%s is up: %d\n", p -> if_name, n);
        p ++;
      }
      if_freenameindex(ptr);
    }
  }

  printf("\n\nTest cyginet_interface_ipv4:\n\n");
  {
    struct sockaddr_in sa;
    struct if_nameindex * ptr = (struct if_nameindex *)if_nameindex();
    if (ptr) {
      struct if_nameindex * p = ptr;
      int n;
      while (p -> if_index) {
        memset(&sa, 0, sizeof(sa));
        n = cyginet_interface_ipv4(p -> if_name,
                                   p -> if_index,
                                   (unsigned char*)&sa
                                   );
        printf("get ipv4 from %s: %d\n", p -> if_name, n);
        p ++;
      }
      if_freenameindex(ptr);
    }
  }

  printf("\n\nTest cyginet_interface_sdl:\n\n");
  {
    struct sockaddr_dl sdl;
    struct if_nameindex * ptr = (struct if_nameindex *)if_nameindex();
    if (ptr) {
      struct if_nameindex * p = ptr;
      int n;
      while (p -> if_index) {
        memset(&sdl, 0, sizeof(struct sockaddr_dl));
        n = cyginet_interface_sdl(&sdl, p -> if_name);
        printf("get sdl from %s: %d\n", p -> if_name, n);
        if (0 == n) {
          printf("sdl_len is %d\n", sdl.sdl_len);
          printf("sdl_nlen is %d\n", sdl.sdl_nlen);
          printf("sdl_alen is %d\n", sdl.sdl_alen);
        }
        p ++;
      }
      if_freenameindex(ptr);
    }
  }

  printf("\n\nTest libwinet_monitor_route_thread_proc:\n\n");
  do {
    int mypipes[2];
    int n;
    char *cmd1 = "netsh interface ipv6 add route 3ffe::/16 1 fe80::1";
    char *cmd2 = "netsh interface ipv6 delete route 3ffe::/16 1 fe80::1";
    // char *cmd3 = "netsh interface ipv6 update route 3ffe::/16 1 fe80::1";
    if (-1 == pipe(mypipes))
      break;
    n = cyginet_start_monitor_route_changes(mypipes[1]);
    if (n == 0) {
      char ch = ' ';
      printf("Run command: %s\n", cmd1);      
      libwinet_run_command(cmd1);
      Sleep(100);
      if (read(mypipes[0], &ch, 1) == 1)
        printf("Event number is %c\n", ch);

      printf("Run command: %s\n", cmd2);      
      libwinet_run_command(cmd2);
      Sleep(100);
      if (read(mypipes[0], &ch, 1) == 1)
        printf("Event number is %c\n", ch);
      
      cyginet_stop_monitor_route_changes();
    }
    close(mypipes[0]);
    close(mypipes[1]);
  } while(0);

  printf("\n\nTest select and pipe with \n");
  printf("\tcyginet_start_monitor_route_changes\n");
  printf("\tcyginet_stop_monitor_route_changes\n\n");
  do {
    break;                      /* We don't run it beacuse it need
                                   manual intervention. */
    int mypipes[2];
    int n;
    fd_set readfds;
    char buf[16];
    if (-1 == pipe(mypipes))
      break;
    if (fcntl(mypipes[0], F_SETFL, O_NONBLOCK) < 0)
      printf("Error set NONBLOCK\n");
    FD_ZERO(&readfds);
    n = cyginet_start_monitor_route_changes(mypipes[1]);
    if (n == 0) {
      FD_SET(mypipes[0], &readfds);
      printf("Please disable/enable your netcard or plug/unplug "
             "netting wire so as to change route table.\n");
      fflush(NULL);
      printf("select return: %d\n",
             select(FD_SETSIZE, &readfds, NULL, NULL, NULL)
             );
      memset(buf, 0, 16);
      printf("read pipe, return %d\n",
             read(mypipes[0], buf, 16));
      printf("Event number is %s\n",buf);             
      cyginet_stop_monitor_route_changes();
    }
    close(mypipes[0]);
    close(mypipes[1]);
  } while(0);

  printf("\n\nTest cyginet_dump_route_table:\n\n");
  do {
    #define MAX_ROUTES 120
    struct kernel_route routes[MAX_ROUTES];
    memset(routes, 0, sizeof(struct kernel_route) * MAX_ROUTES);
    int n = cyginet_dump_route_table(routes, MAX_ROUTES);
    printf("Get route numbers: %d\n", n);
  } while (0);

  printf("\n\nTest libwinet_edit_route_entry:\n\n");
  do {
    SOCKADDR *dest; 
    SOCKADDR *gate;
    SOCKADDR_IN dest4 = { AF_INET, 0, {{{ INADDR_ANY }}}, {0} };
    SOCKADDR_IN gate4 = { AF_INET, 0, {{{ INADDR_ANY }}}, {0} };
    SOCKADDR_IN6 dest6 = {
      AF_INET6,
      0,
      0,
      {{IN6ADDR_ANY_INIT}}
    };
    SOCKADDR_IN6 gate6 = {
      AF_INET6,
      0,
      0,
      {{IN6ADDR_ANY_INIT}}
    };
    int prefix;
    unsigned int metric;
    int ifindex;
    int n;
    printf("libwinet_set_forward_entry return %d\n",
           libwinet_set_forward_entry("192.168.128.250",
                                      "255.255.255.255",
                                      "192.168.128.200",
                                      2,
                                      20
                                      )
           );
    if (inet_pton(AF_INET, "192.168.128.119", &dest4.sin_addr) != 1)
      break;
    if (inet_pton(AF_INET, "192.168.128.200", &gate4.sin_addr) != 1)
      break;
    ifindex = 2;
    metric = 3;
    prefix = 32;
    
    dest = (SOCKADDR*)&dest4;
    gate = (SOCKADDR*)&gate4;
    n = libwinet_edit_route_entry(dest,
                                  prefix,
                                  gate,
                                  ifindex,
                                  metric,
                                  RTM_ADD
                                  );
    printf("Add Ipv4 route return %d\n", n);
    n = libwinet_edit_route_entry(dest,
                                  prefix,
                                  gate,
                                  ifindex,
                                  metric,
                                  RTM_CHANGE
                                  );
    printf("Change Ipv4 route return %d\n", n);
    metric = 15;
    n = libwinet_edit_route_entry(dest,
                                  prefix,
                                  gate,
                                  ifindex,
                                  metric,
                                  RTM_DELETE
                                  );
    printf("Delete Ipv4 route return %d\n", n);

    if (inet_pton(AF_INET6, "3ffe::", &dest6.sin6_addr) != 1)
      break;
    if (inet_pton(AF_INET6, "fe80::1", &gate6.sin6_addr) != 1)
      break;
    prefix = 112;
    metric = 1200;
    ifindex = 1;
    dest = (SOCKADDR*)&dest6;
    gate = (SOCKADDR*)&gate6;
    n = libwinet_edit_route_entry(dest,
                                  prefix,
                                  gate,
                                  ifindex,
                                  metric,
                                  RTM_ADD
                                  );
    printf("Add Ipv6 route return %d\n", n);
    metric = 1100;
    n = libwinet_edit_route_entry(dest,
                                  prefix,
                                  gate,
                                  ifindex,
                                  metric,
                                  RTM_CHANGE
                                  );
    printf("Change Ipv6 route return %d\n", n);
    n = libwinet_edit_route_entry(dest,
                                  prefix,
                                  gate,
                                  ifindex,
                                  metric,
                                  RTM_DELETE
                                  );
    printf("Delete Ipv6 route return %d\n", n);

  } while(0);
}

int main(int argc, char* argv[])
{
  WORD wVersionRequested;
  WSADATA wsaData;
  int err;

  /* Use the MAKEWORD(lowbyte, highbyte) macro declared in Windef.h */
  wVersionRequested = MAKEWORD(2, 2);

  err = WSAStartup(wVersionRequested, &wsaData);
  if (err != 0) {
    /* Tell the user that we could not find a usable */
    /* Winsock DLL.                                  */
    printf("WSAStartup failed with error: %d\n", err);
    return 1;
  }

  /* Confirm that the WinSock DLL supports 2.2.*/
  /* Note that if the DLL supports versions greater    */
  /* than 2.2 in addition to 2.2, it will still return */
  /* 2.2 in wVersion since that is the version we      */
  /* requested.                                        */

  if (LOBYTE(wsaData.wVersion) != 2 || HIBYTE(wsaData.wVersion) != 2) {
    /* Tell the user that we could not find a usable */
    /* WinSock DLL.                                  */
    printf("Could not find a usable version of Winsock.dll\n");
    WSACleanup();
    return 1;
  }
  else
    printf("The Winsock 2.2 dll was found okay\n");

  runTestCases();

  WSACleanup();
  return 0;
}

#endif  /* TEST_CYGINET */

