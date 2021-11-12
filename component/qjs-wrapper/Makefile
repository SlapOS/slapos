CPPFLAGS=-g -Wall -Wno-array-bounds -Wno-format-truncation -std=c99 -Iinclude -O2 -fPIC
LDFLAGS+= -g
LIBS=-lstdc++ -lmavsdk -lmavsdk_action -lmavsdk_mavlink_passthrough -lmavsdk_telemetry -lopen62541

LIB_NAME := libqjswrapper.so

SRCS := mavsdk_wrapper.cpp pubsub_publish.c qjs_wrapper.c
OBJS := mavsdk_wrapper.o pubsub_publish.o qjs_wrapper.o

all: $(LIB_NAME)

%.o: 

$(LIB_NAME): $(OBJS)
	$(CC) $(LDFLAGS) -shared -o $@ $^ $(LIBS)

install: all
	mkdir -p "$(DESTDIR)$(prefix)/lib"
	install -m644 $(LIB_NAME) "$(DESTDIR)$(prefix)/lib"

clean:
	$(RM) -f $(OBJS)
