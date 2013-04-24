/*
Copyright (c) 2007 by Grégoire Henry
Copyright (c) 2008, 2009 by Juliusz Chroboczek
Copyright (c) 2010 by Vincent Gross

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
*/
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>
#include <assert.h>

#include <strings.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <ifaddrs.h>
#include <net/if.h>

#include "babeld.h"
#include "neighbour.h"
#include "kernel.h"
#include "util.h"
#include "interface.h"

#include "cyginet.h"

static int get_sdl(struct sockaddr_dl *sdl, char *guidname);

static const unsigned char v4prefix[16] =
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0xFF, 0xFF, 0, 0, 0, 0 };

int export_table = -1, import_table = -1;

int
if_eui64(char *ifname, int ifindex, unsigned char *eui)
{
    struct sockaddr_dl sdl;
    char *tmp = NULL;
    memset(&sdl, 0, sizeof(struct sockaddr_dl));
    if (get_sdl(&sdl, ifname) < 0) {
        return -1;
    }
    tmp = sdl.sdl_data + sdl.sdl_nlen;
    if (sdl.sdl_alen == 8) {
        memcpy(eui, tmp, 8);
        eui[0] ^= 2;
    } else if (sdl.sdl_alen == 6) {
        memcpy(eui,   tmp,   3);
        eui[3] = 0xFF;
        eui[4] = 0xFE;
        memcpy(eui+5, tmp+3, 3);
    } else {
        return -1;
    }
    return 0;
}

/* Fill sdl with the structure corresponding to ifname.
 Warning: make a syscall (and get all interfaces).
 return -1 if an error occurs, 0 otherwise. */
static int
get_sdl(struct sockaddr_dl *sdl, char *ifname)
{
    return cyginet_interface_sdl(sdl, ifname);
}

static int old_forwarding = -1;
static int old_accept_redirects = -1;

static int ifindex_lo = 1;
static int kernel_pipe_handles[2];

/* It enables ip6.forwarding and disable ip6.redirect.
 *
 * Option 1:
 *
 * IPV6CTL_FORWARDING (ip6.forwarding) Boolean: enable/disable
 * forward- ing of IPv6 packets.  Also, identify if the node is
 * acting as a router.  Defaults to off.
 *
 * ==> In the Windows, MSDN says in the registry
 *
 * HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters
 *
 * Value Name: IPEnableRouter
 * Value type: REG_DWORD
 * Value Data: 1
 *
 * A value of 1 enables TCP/IP forwarding for all network
 * connections that are installed and used by this computer.
 *
 * Refer to: http://support.microsoft.com/kb/315236/en-us
 *
 * For ipv6, no global options to enable forwarding, but for each
 * interface respectively.
 *
 * Option 2:
 *
 * ICMPV6CTL_REDIRACCEPT
 *
 * IPV6CTL_SENDREDIRECTS (ip6.redirect) Boolean: enable/disable
 * sending of ICMPv6 redirects in response to unforwardable IPv6
 * packets.  This option is ignored unless the node is routing
 * IPv6 packets, and should normally be enabled on all systems.
 * Defaults to on.
 *
 * ==> MSDN says in the registry
 *
 * HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters
 *
 * EnableICMPRedirect = 0
 *
 * Regarding ipv6, it's in the registry
 *
 * HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters
 *
 * Refer to:
 *     http://technet.microsoft.com/en-us/library/cc766102(v=ws.10).aspx
 *     http://msdn.microsoft.com/en-us/library/aa915651.aspx
 *
 * Notice the msdn page of Windows CE, value is "EnableICMPRedirects",
 * it's plural. But I'd rather use singluar form "EnableICMPRedirect".
 *
 */

int
kernel_setup(int setup)
{
    int flags=0;
    struct interface *ifp;

    if (setup) {

        if (0 != cyginet_startup())
            return -1;

        /* We don't disable ICMPv6 redirect in the Windows */
        /*
        if ((rc = cyginet_set_icmp6_redirect_accept(0)) == -1) {
            fprintf(stderr, "Cannot disable ICMPv6 redirect.\n");
            return -1;
        }

        if (rc) {
            fprintf(stderr,
                    "Disable ICMPv6 redirect successfully. Reboot computer "
                    "to take it effect now.\n\n"
                    );
            return -1;
        }
        */
        FOR_ALL_INTERFACES(ifp) {
            if (cyginet_set_interface_forwards(ifp->name, 1) == -1) {
                fprintf(stderr, "Cannot enable IPv6 forwarding.\n");
                return -1;
            }
        }

        if (pipe(kernel_pipe_handles) == -1)
            return -1;
        if ((flags = fcntl(kernel_pipe_handles[0], F_GETFL, 0)) < 0)
            goto error;
        if (fcntl(kernel_pipe_handles[0], F_SETFL, flags | O_NONBLOCK) == -1)
            goto error;
    }
    else {
        close(kernel_pipe_handles[0]);
        close(kernel_pipe_handles[1]);
        cyginet_cleanup();
    }
    return 1;

 error:
    return -1;
}

int
kernel_setup_socket(int setup)
{
    /* We use a pipe to notify route changed */
    if(setup) {
        if(kernel_socket < 0) {
            kernel_socket = kernel_pipe_handles[0];
            if (-1 ==
                cyginet_start_monitor_route_changes(kernel_pipe_handles[1])) {
                perror("start_monitor_route_changes");
                kernel_socket = -1;
                return -1;
            }
        }
    } else {
        cyginet_stop_monitor_route_changes();
        kernel_socket = -1;
    }
    return 1;
}

int
kernel_setup_interface(int setup, const char *ifname, int ifindex)
{
    return 1;
}

int
kernel_interface_operational(const char *ifname, int ifindex)
{
    int rc;
    int flags = link_detect ? (IFF_UP | IFF_RUNNING) : IFF_UP;

    rc = cyginet_interface_operational(ifname, ifindex);
    if (rc < 0)
        return -1;
    return ((rc & flags) == flags);
}

int
kernel_interface_ipv4(const char *ifname, int ifindex, unsigned char *addr_r)
{
    return cyginet_interface_ipv4(ifname, ifindex, addr_r);
}

int
kernel_interface_mtu(const char *ifname, int ifindex)
{
    return cyginet_interface_mtu(ifname, ifindex);
}

int
kernel_interface_wireless(const char *ifname, int ifindex)
{
    return cyginet_interface_wireless(ifname, ifindex);
}

int
kernel_interface_channel(const char *ifname, int ifindex)
{
    errno = ENOSYS;
    return -1;
}

static void
clear_kernel_socket_event()
{
    int ch;
    while (read(kernel_pipe_handles[0], &ch, 1) > 0);
}

/*
 * RTF_REJECT
 *
 *   Instead of forwarding a packet like a normal route, routes with
 *   RTF_REJECT cause packets to be dropped and unreachable messages
 *   to be sent to the packet originators. This flag is only valid on
 *   routes pointing at the loopback interface.
 *
 * RTF_BLACKHOLE
 *
 *   Like the RTF_REJECT flag, routes with RTF_BLACKHOLE cause packets
 *   to be dropped, but unreachable messages are not sent. This flag
 *   is only valid on routes pointing at the loopback interface.
 *
 * Nullrouting on Windows
 *
 *   Windows XP/Vista/7 does not support reject or blackhole arguments
 *   via route, thus an unused IP address (e.g. 192.168.0.205) must be
 *   used as the target gateway.
 *
 * RTF_GATEWAY: destination is a gateway
 *
 * RTF_HOST: host entry (net otherwise)
 *
 *   It means all the netmask bits are 1.
 *
 * RTF_CLONING: generate new routes on use
 *
 *   Not implemented in the Windows.
 *
 */
int
kernel_route(int operation, const unsigned char *dest, unsigned short plen,
             const unsigned char *gate, int ifindex, unsigned int metric,
             const unsigned char *newgate, int newifindex,
             unsigned int newmetric)
{
    char local6[1][1][16] = {{IN6ADDR_ANY_INIT}};
    char local4[1][1][16] =
        {{{ 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x7f, 0x00, 0x00, 0x01 }}};
    int rc, ipv4;
    int route_ifindex;
    int prefix_len;
    struct sockaddr_storage destination = {0};
    struct sockaddr_storage gateway = {0};

    /* Check that the protocol family is consistent. */
    if(plen >= 96 && v4mapped(dest)) {
        if(!v4mapped(gate)) {
            errno = EINVAL;
            return -1;
        }
        ipv4 = 1;
    } else {
        if(v4mapped(gate)) {
            errno = EINVAL;
            return -1;
        }
        ipv4 = 0;
    }
    
    if(operation == ROUTE_MODIFY && newmetric == metric &&
       memcmp(newgate, gate, 16) == 0 && newifindex == ifindex)
      return 0;

    if(operation == ROUTE_MODIFY) {
        if((metric == KERNEL_INFINITY) ||
           (newmetric == KERNEL_INFINITY) ||
           (ipv4 && plen == 128 && memcmp(dest, newgate, 16) == 0)) {
            kernel_route(ROUTE_FLUSH, dest, plen,
                         gate, ifindex, metric,
                         NULL, 0, 0);
            return kernel_route(ROUTE_ADD, dest, plen,
                                newgate, newifindex, newmetric,
                                NULL, 0, 0);
        } else {
            metric = newmetric;
            gate = newgate;
            ifindex = newifindex;
        }
    }

    kdebugf("kernel_route: %s %s/%d metric %d dev %d nexthop %s\n",
            operation == ROUTE_ADD ? "add" :
            operation == ROUTE_FLUSH ? "flush" : "change",
            format_address(dest), plen, metric, ifindex,
            format_address(gate));

    if(kernel_socket < 0) kernel_setup_socket(1);

    route_ifindex = ifindex;
    prefix_len = ipv4 ? plen - 96 : plen;

    if(0 && metric == KERNEL_INFINITY) {
        /* It means this route has property: RTF_BLACKHOLE */
        if(ifindex_lo < 0) {
            ifindex_lo = cyginet_loopback_index(AF_UNSPEC);
            if(ifindex_lo <= 0)
                return -1;
        }
        route_ifindex = ifindex_lo;
    }

#define PUSHADDR(dst, src)                                              \
    do { struct sockaddr_in *sin = (struct sockaddr_in*)&(dst);          \
        sin->sin_family = AF_INET;                                      \
        memcpy(&sin->sin_addr, (src) + 12, 4);                          \
    } while (0)

#define PUSHADDR6(dst, src)                                             \
    do { struct sockaddr_in6 *sin6 = (struct sockaddr_in6*)&(dst);       \
        sin6->sin6_family = AF_INET6;                                   \
        memcpy(&sin6->sin6_addr, (src), 16);                            \
    } while (0)

    if(ipv4) {
        PUSHADDR(destination, dest);
        if (0 && metric == KERNEL_INFINITY) {
            /* blackhole route, now it doesn't work */
            kdebugf("Error: ipv4 blackhole route doesn't work.\n");
            return -1;
            assert (operation != ROUTE_MODIFY);
            PUSHADDR(gateway, **local4);
        }
        else if(plen == 128 && memcmp(dest+12, gate+12, 4) == 0) {
            assert (operation != ROUTE_MODIFY);
            PUSHADDR(gateway, gate); /* MIB_IPROUTE_TYPE_DIRECT */
        }
        else
            PUSHADDR(gateway, gate); /* MIB_IPROUTE_TYPE_INDIRECT */

    } else {
        PUSHADDR6(destination, dest);
        if (0 && metric == KERNEL_INFINITY)
            PUSHADDR6(gateway, **local6);
        else
            PUSHADDR6(gateway, gate);
    }
#undef PUSHADDR
#undef PUSHADDR6
    /* what if route_ifindex == 0 */
    switch(operation) {
    case ROUTE_FLUSH:
        rc = cyginet_delete_route_entry((struct sockaddr*)&destination,
                                        prefix_len,
                                        (struct sockaddr*)&gateway,
                                        route_ifindex,
                                        metric
                                        );
        break;
    case ROUTE_ADD:
        rc = cyginet_add_route_entry((struct sockaddr*)&destination,
                                     prefix_len,
                                     (struct sockaddr*)&gateway,
                                     route_ifindex,
                                     metric
                                     );
        break;
    case ROUTE_MODIFY:
        rc = cyginet_update_route_entry((struct sockaddr*)&destination,
                                        prefix_len,
                                        (struct sockaddr*)&gateway,
                                        route_ifindex,
                                        metric
                                        );
        break;
    default:
        return -1;
    };

    /* Monitor thread will write data to kernel pipe when any change
       in the route table is happened. Here it's babeld itself to
       change the route table, so kernel pipe need to be clean. */
    clear_kernel_socket_event();
    return rc;
}

static void
print_kernel_route(int add, struct kernel_route *route)
{
    char *ifname = NULL;
    char guidname[IFNAMSIZ];
    if(if_indextoname(route->ifindex, guidname))
        ifname = cyginet_ifname(guidname);

    fprintf(stderr,
            "%s kernel route: dest: %s gw: %s metric: %d if: %s(%d) \n",
            add == RTM_ADD ? "Add" :
            add == RTM_DELETE ? "Delete" : "Change",
            format_prefix(route->prefix, route->plen),
            format_address(route->gw),
            route->metric,
            ifname ? ifname : "unk",
            route->ifindex
            );
}

static int
parse_kernel_route(struct cyginet_route *src, struct kernel_route *route)
{
    struct sockaddr *sa;

    if(ifindex_lo < 0) {
        ifindex_lo = cyginet_loopback_index(AF_UNSPEC);
        if(ifindex_lo <= 0)
            return -1;
    }

    memset(route, 0, sizeof(struct kernel_route));
    route -> plen = src -> plen;
    route -> metric = src -> metric;
    route -> proto = src -> proto;
    route -> ifindex = src -> ifindex;

    sa = (struct sockaddr*)&(src -> prefix);
    if(sa->sa_family == AF_INET6) {
        struct sockaddr_in6 *sin6 = (struct sockaddr_in6 *)sa;
        memcpy(route->prefix, &sin6->sin6_addr, 16);
        if(IN6_IS_ADDR_LINKLOCAL(&sin6->sin6_addr)
             || IN6_IS_ADDR_MC_LINKLOCAL(&sin6->sin6_addr))
           return -1;
    } else if(sa->sa_family == AF_INET) {
        struct sockaddr_in *sin = (struct sockaddr_in *)sa;
#if defined(IN_LINKLOCAL)
        if(IN_LINKLOCAL(ntohl(sin->sin_addr.s_addr)))
            return -1;
#endif
        if(IN_MULTICAST(ntohl(sin->sin_addr.s_addr)))
            return -1;
        v4tov6(route->prefix, (unsigned char *)&sin->sin_addr);
    } else {
        return -1;
    }

    /* Gateway */
    sa = (struct sockaddr*)&(src -> gateway);
    if(sa->sa_family == AF_INET6) {
        struct sockaddr_in6 *sin6 = (struct sockaddr_in6 *)sa;
        memcpy(route->gw, &sin6->sin6_addr, 16);
    } else if(sa->sa_family == AF_INET) {
        struct sockaddr_in *sin = (struct sockaddr_in *)sa;
        v4tov6(route->gw, (unsigned char *)&sin->sin_addr);
    }

    if(route->ifindex == ifindex_lo)
        return -1;

    /* Netmask */
    if(v4mapped(route->prefix)) route->plen += 96;

    return 0;
}

int
kernel_routes(struct kernel_route *routes, int maxroutes)
{
    int rc, i;
    int count;

    struct kernel_route * proute = routes;
    struct cyginet_route * ptable;

    rc = cyginet_dump_route_table(NULL, 0);
    if (rc < 0)
        return -1;
    if (rc == 0)
        return 0;

    rc += 10;
    if (NULL == (ptable = calloc(rc, sizeof(struct cyginet_route))))
        return -1;

    rc = cyginet_dump_route_table(ptable, rc);
    if (rc < 0) {
        free(ptable);
        return -1;
    } else if (maxroutes < rc)
        return maxroutes;
    
    for (i = 0, count = 0; i < rc; i++) {

        if (parse_kernel_route(ptable + i, proute) != 0)
            continue;

        if(debug > 2)
            print_kernel_route(RTM_ADD, proute);

        if (maxroutes > rc)
            proute++;
        count ++;
    }

    free(ptable);
    return count;
}

/* Note: ifname returned by getifaddrs maybe includes a suffix number
   in the Cygwin, it looks like:

   {C05BAB6E-B82D-4C4D-AF07-EFF7C45C5DB0}_1
   {C05BAB6E-B82D-4C4D-AF07-EFF7C45C5DB0}_2
   ...

   */
static int
compare_ifname(const char * ifapname, const char * ifname)
{
    assert(ifname);
    char * guidname = cyginet_guidname(ifname);
    if (guidname)
        return strncmp(guidname, ifapname, strlen(guidname));
    return -1;
}

int
cyginet_kernel_addresses(char *ifname, int ifindex, int ll,
                         struct kernel_route *routes, int maxroutes)
{
    int rc, i, n;
    struct cyginet_route *ptable, *p;
    n = maxroutes * 2;

    while (1) {
        if (NULL == (ptable = calloc(n, sizeof(struct cyginet_route))))
            return -1;

        rc = cyginet_getifaddresses(ifname, ptable, n);
        if(rc < 0)
            return -1;
            
        if (rc < n)
            break;

        free(ptable);
        n += n;
    }
        
    i = 0;
    p = ptable; p --;
    while (p ++, n --) {
        struct sockaddr *s = (struct sockaddr*)&(p -> prefix);
        if (s -> sa_family == AF_INET6) {
            struct sockaddr_in6 *sin6 = (struct sockaddr_in6*)&(p->prefix);
            if(!!ll != !!IN6_IS_ADDR_LINKLOCAL(&sin6->sin6_addr))
                continue;
            memcpy(routes[i].prefix, &sin6->sin6_addr, 16);
            routes[i].plen = 128;
            routes[i].metric = 0;
            routes[i].ifindex = ifindex;
            routes[i].proto = RTPROT_BABEL_LOCAL;
            memset(routes[i].gw, 0, 16);
            i++;
        } else if (s -> sa_family == AF_INET) {
            struct sockaddr_in *sin = (struct sockaddr_in*)&(p->prefix);
            if(ll)
                continue;
#if defined(IN_LINKLOCAL)
            if(IN_LINKLOCAL(htonl(sin->sin_addr.s_addr)))
                continue;
#endif
            memcpy(routes[i].prefix, v4prefix, 12);
            memcpy(routes[i].prefix + 12, &sin->sin_addr, 4);
            routes[i].plen = 128;
            routes[i].metric = 0;
            routes[i].ifindex = ifindex;
            routes[i].proto = RTPROT_BABEL_LOCAL;
            memset(routes[i].gw, 0, 16);
            i++;
        }
    }
    free(ptable);
    return i;
}

int
kernel_addresses(char *ifname, int ifindex, int ll,
                 struct kernel_route *routes, int maxroutes)
{
    struct ifaddrs *ifa, *ifap;
    int rc, i;
    rc = getifaddrs(&ifa);
    if(rc < 0)
        return -1;

    ifap = ifa;
    i = 0;
    while(ifap && i < maxroutes) {
        if((ifname != NULL && compare_ifname(ifap->ifa_name, ifname) != 0))
            goto next;
        if(ifap->ifa_addr->sa_family == AF_INET6) {
            struct sockaddr_in6 *sin6 = (struct sockaddr_in6*)ifap->ifa_addr;
            if(!!ll != !!IN6_IS_ADDR_LINKLOCAL(&sin6->sin6_addr))
                goto next;
            memcpy(routes[i].prefix, &sin6->sin6_addr, 16);
            routes[i].plen = 128;
            routes[i].metric = 0;
            routes[i].ifindex = ifindex;
            routes[i].proto = RTPROT_BABEL_LOCAL;
            memset(routes[i].gw, 0, 16);
            i++;
        } else if(ifap->ifa_addr->sa_family == AF_INET) {
            struct sockaddr_in *sin = (struct sockaddr_in*)ifap->ifa_addr;
            if(ll)
                goto next;
#if defined(IN_LINKLOCAL)
            if(IN_LINKLOCAL(htonl(sin->sin_addr.s_addr)))
                goto next;
#endif
            memcpy(routes[i].prefix, v4prefix, 12);
            memcpy(routes[i].prefix + 12, &sin->sin_addr, 4);
            routes[i].plen = 128;
            routes[i].metric = 0;
            routes[i].ifindex = ifindex;
            routes[i].proto = RTPROT_BABEL_LOCAL;
            memset(routes[i].gw, 0, 16);
            i++;
        }
 next:
        ifap = ifap->ifa_next;
    }

    freeifaddrs(ifa);
    return i;
}

int
kernel_callback(int (*fn)(int, void*), void *closure)
{
    if (kernel_socket < 0) kernel_setup_socket(1);

    /* In the Windows, we can't get the exact changed route, but the
       route table is really changed. */
    kdebugf("Kernel table changed.\n");
    cyginet_refresh_interface_table();
    clear_kernel_socket_event();

    return fn(~0, closure);
}

/* Local Variables:      */
/* c-basic-offset: 4     */
/* indent-tabs-mode: nil */
/* End:                  */
