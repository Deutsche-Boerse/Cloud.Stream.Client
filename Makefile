-include Makefile.local

all: mdstream-client-cpp mdstream-client-python

include .devcontainer/rules.mk

dir := proto
include $(dir)/rules.mk

dir := cpp
include $(dir)/rules.mk

dir := python
include $(dir)/rules.mk

help:
	@printf "Usage: make [target]\n"
	@printf "\n"
	@printf "Available targets:\n"
	@printf "\n"
	@printf "\thelp                     Show this help message\n";
	@printf "$(HELP_MSG)"
	@printf "\n";

clean:
	$(RM) -rf build