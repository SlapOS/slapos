CPPFLAGS=-g -Wall -Wno-array-bounds -Wno-format-truncation -std=c99 -O2 -fPIC
LDFLAGS+= -g
LIBS=-lstdc++ -lmavsdk -lmavsdk_action -lmavsdk_mavlink_passthrough -lmavsdk_telemetry -lopen62541

LIB_NAME := libqjswrapper.so

WRAPPER_HEADERS := $(wildcard include/*.h)

SRCS := mavsdk_wrapper.cpp qjs_wrapper.c
OBJS := mavsdk_wrapper.o qjs_wrapper.o

all: $(LIB_NAME)

%.o: $(WRAPPER_HEADERS)

$(LIB_NAME): $(OBJS)
	$(CC) $(LDFLAGS) -shared -o $@ $^ $(LIBS)

install: all
	mkdir -p "$(DESTDIR)$(prefix)/lib"
	install -m644 $(LIB_NAME) "$(DESTDIR)$(prefix)/lib"

clean:
	$(RM) -f $(OBJS)
