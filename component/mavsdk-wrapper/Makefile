MAVSDK_WRAPPER_HEADERS := $(wildcard include/*.h)
LIB_LIST := $(wildcard $(MAVSDK_LIB)/*.a)
LIB_NAME ?= libmavsdk_wrapper.a

SRCS := $(wildcard *.cpp)
OBJS := $(SRCS:%.cpp=%.o)

all: $(LIB_NAME)

$(LIB_NAME): $(OBJS)
	$(foreach lib,$(LIB_LIST),$(AR) x $(lib);)
	$(AR) qc $@ *.o
	rm *.o

%.o: $(MAVSDK_WRAPPER_HEADERS)

install: all
	mkdir -p "$(DESTDIR)$(prefix)/lib"
	install -m644 $(LIB_NAME) "$(DESTDIR)$(prefix)/lib"
	mkdir -p "$(DESTDIR)$(prefix)/include"
	cp -r $(MAVSDK_INC)/* "$(DESTDIR)$(prefix)/include"

.PHONY: clean
clean:
	rm -f $(LIB_NAME)