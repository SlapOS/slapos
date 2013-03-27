PREFIX = /usr/local

CDEBUGFLAGS = -Os -g -Wall

DEFINES = $(PLATFORM_DEFINES)

CFLAGS = $(CDEBUGFLAGS) $(DEFINES) $(EXTRA_DEFINES)

LDLIBS = -lrt

SRCS = babeld.c net.c kernel.c util.c interface.c source.c neighbour.c \
       route.c xroute.c message.c resend.c configuration.c local.c

OBJS = babeld.o net.o kernel.o util.o interface.o source.o neighbour.o \
       route.o xroute.o message.o resend.o configuration.o local.o

KERNEL_SOUCES = kernel_netlink.c kernel_socket.c

ifneq "$(WINVER)" ""

SRCS += cyginet.c
OBJS += cyginet.o
LDLIBS +=  -liphlpapi -lws2_32 -lwlanapi -lole32 -lsetupapi
KERNEL_SOUCES += kernel_cygwin.c

ifeq "$(WINVER)" "XP"
CFLAGS += -D_WIN32_WINNT=0x0503
endif

ifeq "$(WINVER)" "VISTA"
CLFAGS += -D_WIN32_WINNT=0x0600
endif

endif

babeld: $(OBJS)
	$(CC) $(CFLAGS) $(LDFLAGS) -o babeld $(OBJS) $(LDLIBS)

.SUFFIXES: .man .html

.man.html:
	rman -f html $< | \
	sed -e "s|<a href='babeld.8'|<a href=\"babeld.html\"|" \
            -e "s|<a href='\\(ahcp[-a-z]*\\).8'|<a href=\"../ahcp/\1.html\"|" \
	    -e "s|<a href='[^']*8'>\\(.*(8)\\)</a>|\1|" \
	> $@

babeld.html: babeld.man

.PHONY: all install install.minimal uninstall clean

all: babeld babeld.man

install.minimal: babeld
	-rm -f $(TARGET)$(PREFIX)/bin/babeld
	mkdir -p $(TARGET)$(PREFIX)/bin
	cp -f babeld $(TARGET)$(PREFIX)/bin

install: install.minimal all
	mkdir -p $(TARGET)$(PREFIX)/man/man8
	cp -f babeld.man $(TARGET)$(PREFIX)/man/man8/babeld.8

uninstall:
	-rm -f $(TARGET)$(PREFIX)/bin/babeld
	-rm -f $(TARGET)$(PREFIX)/man/man8/babeld.8

clean:
	-rm -f babeld babeld.html *.o *~ core TAGS gmon.out

kernel.o: $(KERNEL_SOURCES)

# Usage: ./testc.exe
# Verify most of the functions in the cyginet.c
testc.exe: cyginet.c
	$(CC) $(CFLAGS) $(LDFLAGS) -DTEST_CYGINET -o $@ $< $(LDLIBS)
