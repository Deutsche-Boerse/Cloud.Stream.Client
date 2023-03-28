#pragma once

#include <string.h>
#include <stdarg.h>
#include <chrono>

namespace Log {
	inline void timeToBuffer(char *buffer, size_t len) {
		time_t currTime = time(NULL);
		struct tm * p = localtime(&currTime);
		strftime(buffer, len, "%d-%b-%Y %H:%M:%S ", p);
	}
	
	inline void info(const char *format, ...) {
		va_list args;
		char buffer[1000];
		va_start(args, format);
		timeToBuffer(buffer, sizeof(buffer));
		fprintf(stdout, "%s : ", buffer);
		vfprintf(stdout, format, args);
		fprintf(stdout, "\n");
		va_end(args);
	}

	inline void error(const char *format, ...) {
		va_list args;
		char buffer[1000];
		va_start(args, format);
		timeToBuffer(buffer, sizeof(buffer));
		fprintf(stderr, "%s : ", buffer);
		vfprintf(stderr, format, args);
		fprintf(stderr, "\n");
		va_end(args);
	}
}