.PHONY: all help

CPP_DIR      ?= cpp
CPP_DIALECT  ?= c++17
CPP_FLAGS    := 
CPP          := g++
CPPFLAGS     :=                          \
	-O3 -g                               \
	-I/include/                          \
	-I/usr/include/                      \
	-I$(CPP_DIR)/src/                    \
	-I$(PROTO_CPP_OUT)/                  \
	-I$(JWT_LIB)                         \
	-Wall -Wextra -Wpedantic -Werror     \
	-std=$(CPP_DIALECT) -D_MULTITHREADED \
	-I$(PROTO_DIR)/$(PROTO_SRC_DIR) 

LDFLAGS      :=                          \
	-I$(PROTO_CPP_OUT)/


CPP_SRCS     :=                          \
	main.cpp                             \
	config.cpp                           \
	webinterface.cpp

CPP_LIBS     :=                          \
	-lixwebsocket                        \
	-pthread                             \
	-lssl                                \
	-lcrypto                             \
	-lz                                  \
	-lprotobuf

CPP_SRC_DIR   := src/client
CPP_OUT_DIR   := build/cpp
CPP_OBJ_FILES := $(addprefix $(CPP_OUT_DIR)/, $(patsubst %.cpp, %.o, $(CPP_SRCS)))
MDSTREAM      := ${CPP_OUT_DIR}/mdstream-client-cpp

HELP_MSG    += \tmdstream-client-cpp      Compile\
	sources and link the object files to mdstream-client program\n

# compile and link files regarding main market data stream client program
mdstream-client-cpp: $(MDSTREAM)

$(MDSTREAM): $(CPP_OBJ_FILES)
	$(CPP) $(CPPFLAGS) $(CPP_OBJ_FILES) $(PROTO_OBJ_CPP) $(LDFLAGS) -o $@ $(CPP_LIBS)

$(CPP_OUT_DIR)/%.o: $(CPP_DIR)/$(CPP_SRC_DIR)/%.cpp $(PROTO_CPP)
	mkdir -p $(CPP_OUT_DIR)
	$(CPP) $(CPPFLAGS) -c $< -o $@ $(CPP_LIBS)