all: 

PY_DIR      := python
PY_SRC_DIR  := src
PY_SRCS     := $(addprefix $(PY_DIR)/$(PY_SRC_DIR)/,   \
	client/client.py					\
	client/argparser.py                 \
	client/jwt_token.py)

PY_OUT_DIR  := build/python
PYTHON_REQ  := $(PY_DIR)/requirements.txt


$(PY_OUT_DIR) :
	mkdir -p $(PY_OUT_DIR)

mdstream-client-python: $(PROTO_OBJ_PY) $(PY_SRCS) $(PY_OUT_DIR)
	@cp $(PROTO_OBJ_PY) $(PY_OUT_DIR)
	@cp $(PY_SRCS) $(PY_OUT_DIR)

HELP_MSG += \tmdstream-client-python   Generate python sources from proto files\n