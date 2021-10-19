CXXFLAGS = -O2
LIBS = -lpthread ../lib/libmavsdk_wrapper.a
CXXFILES = connect.cpp
PROG = connect

$(PROG):
	$(CXX) $(CXXFILES) $(LIBS) $(CXXFLAGS) -o $(PROG)

clean:
	$(RM) -f $(PROG) *.o