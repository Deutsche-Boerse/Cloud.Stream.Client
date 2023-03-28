#include "config.h"
#include "webinterface.h"

struct configuration config;

int main(int argc, char **argv) {
	// Read commandline
	if (config_parse(&config, argc, argv)) {
		return -1;
	}

	WebInterface interface;
	interface.run();

	return 0;
}
