.PHONY: all clean

# protobuf variables 
PROTO_DIR     := proto
PROTOC        := protoc
PROTO_FILES   ?= client.proto md_cef.proto md_crypto.proto md_energy.proto
PROTO_SRC_DIR := src
PROTO_CPP_OUT := build/proto/cpp
PROTO_PY_OUT  := build/proto/python
PROTO_OUT     := $(PROTO_CPP_OUT) $(PROTO_PY_OUT)

PROTO_CPP     := $(PROTO_CPP_OUT)/proto
PROTO_PY      := $(PROTO_PY_OUT)/proto

# compile variables and flags 
CPP_DIALECT   ?= c++17
CPP			  := g++
CPPFLAGS	  :=              \
	-I./$(PROTO_CPP_OUT)      \
	-std=$(CPP_DIALECT)

# input protobuf headers and sources
PROTO_SRC     := $(addprefix $(PROTO_SRC)/, $(PROTO_FILES))
PROTO_OBJ_CPP := $(addprefix $(PROTO_CPP_OUT)/, $(patsubst %.proto, %.o, $(PROTO_FILES)))
PROTO_OBJ_PY  := $(addprefix $(PROTO_PY_OUT)/, $(patsubst %.proto, %_pb2.py, $(PROTO_FILES)))


all: proto-cpp proto-python

proto-cpp: $(PROTO_CPP)

$(PROTO_CPP):  $(PROTO_OBJ_CPP)
	@touch $@

# cpp output generation
$(PROTO_CPP_OUT)/%.pb.cc: $(PROTO_DIR)/$(PROTO_SRC_DIR)/%.proto | $(PROTO_CPP_OUT)
	$(PROTOC) --cpp_out=$(PROTO_CPP_OUT) -I$(PROTO_DIR)/$(PROTO_SRC_DIR) $<

$(PROTO_CPP_OUT)/%.o: $(PROTO_CPP_OUT)/%.pb.cc
	$(CPP) $(CPPFLAGS) -c $< -o $@

$(PROTO_CPP_OUT):
	mkdir -p $(PROTO_CPP_OUT)

# python output generation
proto-python: $(PROTO_PY)

$(PROTO_PY):  $(PROTO_OBJ_PY)
	@touch $@


$(PROTO_PY_OUT)/%_pb2.py: $(PROTO_DIR)/$(PROTO_SRC_DIR)/%.proto | $(PROTO_PY_OUT)
	$(PROTOC) --python_out=$(PROTO_PY_OUT) -I$(PROTO_DIR)/$(PROTO_SRC_DIR) $<

$(PROTO_PY_OUT):
	mkdir -p $(PROTO_PY_OUT)


HELP_MSG    += \tproto-cpp                Generate\
	C++ object files, and headers from protobuf files in $(PROTO_DIR)/$(PROTO_SRC_DIR)\n
HELP_MSG    += \tproto-python             Generate\
	python sources from protobuf files in $(PROTO_DIR)/$(PROTO_SRC_DIR).\n