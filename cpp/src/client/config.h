#pragma once

#include <chrono>
#include <sstream>
#include <string>
#include <vector>

struct configuration {
	// Connection
	inline static std::string s_loginServer = "";
	inline static std::string s_wsServer    = "";
	inline static int         s_wsPort      = 443;

	// Authentication
	inline static std::string s_username = "";
	inline static std::string s_password = "";
	inline static std::string s_token    = "";

	// Data
	inline static std::vector<std::string> s_topics      = {};
	inline static bool                     s_logBinary   = false;
	inline static std::string              s_logFileName = "";
	inline static size_t                   s_rec_seq_id  = 0;
	inline static size_t                   s_rec_ts      = 0;

	inline friend std::ostream &operator<<(std::ostream &ss, const configuration &) {
		// clang-format off
		ss << R"({"ws_address":")" << s_wsServer << ':' << s_wsPort
		   << R"(", login_address":")" << s_loginServer
		   << R"(", "Username": ")" << s_username
		   << R"(", "Token/Password": "surpressed)"
		   << R"(", "topics": [)";
		for (const auto &topic : s_topics) {
			ss << '"' << topic << '"';
			if (topic != s_topics.back())   ss << ", ";
			else                            ss << "] ";
		}
		ss << R"(", "logBinary": ")" << std::boolalpha << s_logBinary
		   << R"(", "LogFile": ")" << (s_logFileName.empty() ? "stdout" : s_logFileName)
		   << R"("})";
		// clang-format on
		return ss;
	}
};

int config_parse(struct configuration *c, int argc, char *argv[]);