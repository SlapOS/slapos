CPPFLAGS=-g -Wall -Wno-array-bounds -Wno-format-truncation -O2 -fPIC
LDFLAGS+= -g
LIBS=-lstdc++ -lmavsdk -lmavsdk_action -lmavsdk_mavlink_passthrough -lmavsdk_telemetry

LIB_NAME := libmavsdkqjs.so

MAVSDK_WRAPPER_HEADERS := $(wildcard include/*.h)

SRCS := mavsdk_wrapper.cpp mavsdk_qjs_wrapper.c
OBJS := mavsdk_wrapper.o mavsdk_qjs_wrapper.o

all: $(LIB_NAME)

%.o: $(MAVSDK_WRAPPER_HEADERS)

$(LIB_NAME): $(OBJS)
	$(CC) $(LDFLAGS) -shared -o $@ $^ $(LIBS)

install: all
	mkdir -p "$(DESTDIR)$(prefix)/lib"
	install -m644 $(LIB_NAME) "$(DESTDIR)$(prefix)/lib"

clean:
	$(RM) -f $(OBJS)