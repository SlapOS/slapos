OBJDIR=.obj

CFLAGS=-g -Wall -MMD -MF $(OBJDIR)/$(@F).d
CFLAGS+= -Wno-array-bounds -Wno-format-truncation
CFLAGS+= -O2

LDFLAGS+= -g
LIBS=-lopen62541

LIB_NAME := libopen62541qjs.so

all: $(OBJDIR) $(LIB_NAME)

$(OBJDIR):
	mkdir -p $(OBJDIR)

$(OBJDIR)/%.pic.o: %.c | $(OBJDIR)
	$(CC) $(CFLAGS) -fPIC -c -o $@ $<

$(LIB_NAME): $(OBJDIR)/publisher.pic.o
	$(CC) $(LDFLAGS) -shared -o $@ $^ $(LIBS)

install: all
	mkdir -p "$(DESTDIR)$(prefix)/lib"
	install -m644 $(LIB_NAME) "$(DESTDIR)$(prefix)/lib"

clean:
	rm -rf $(OBJDIR)/