#include "config.h"

#include <utils/container.h>
#include <utils/get_password.h>
#include <utils/log.h>

#include <getopt.h>
#include <iostream>

static inline int parse_size_t(const char *s, size_t *var);
static inline int parse_int(const char *s, int *var);

namespace {
// parameters
enum cfg_params {
	CFG_LOGIN_SERVER,
	CFG_WEBSOCKET_SERVER,
	CFG_USERNAME,
	CFG_PASSWORD,
	CFG_TOKEN,
	CFG_SUBJECT,
	CFG_LOG_FILE,
	CFG_RECOVER_BY_SEQ_ID,
	CFG_RECOVER_BY_TIMESTAMP,
	CFG_HELP
};

static struct option options[] = {
	{ "login-server",          required_argument, 0, CFG_LOGIN_SERVER           },
	{ "websocket-server",      required_argument, 0, CFG_WEBSOCKET_SERVER       },
	{ "username",              required_argument, 0, CFG_USERNAME               },
	{ "password",              required_argument, 0, CFG_PASSWORD               },
	{ "token",                 required_argument, 0, CFG_TOKEN                  },
	{ "subject",               required_argument, 0, CFG_SUBJECT                },
	{ "log-file",              required_argument, 0, CFG_LOG_FILE               },
	{ "recover-by-seq-id",     required_argument, 0, CFG_RECOVER_BY_SEQ_ID      },
	{ "recover-by-timestamp",  required_argument, 0, CFG_RECOVER_BY_TIMESTAMP   },
	{ "help",                  no_argument,       0, CFG_HELP                   }
};

inline void usage(char *proc) {
	fprintf(
	    stdout,
	    "Usage:\n %s\n"
	    " where:\n"
	    "  [--login-server          <loginserver>]    # (optional) defaults to value of wsserver\n"
	    "  [--websocket-server      <wsserver>]       # (required) defaults to \"\"\n"
	    "  [--username              <username>]       # (optional) defaults to \"\"\n"
	    "  [--password              <password>]       # (optional) defaults to \"\"\n"
	    "  [--token                 <token>]          # (optional) WS Auth token, defaults to \"\"\n"
	    "  [--subject               <subject>]        # (required once) subjects to request.  Can occur \n"
	    "                                             #            multiple times\n"
	    "  [--log-file              <filepath>]       # (optional) Write messages to specified file.\n"
	    "                                             #            or stdout if no file is given\n"
	    "  [--recover-by-seq-id     <sequenceID>]     # (optional) recover messages starting from ID\n"
	    "  [--recover-by-timestamp  <timestamp>]      # (optional) recover messages starting from timestamp\n"
	    "  [--help]                                   # (optional) this message\n",
	    proc);
}
} // namespace

int config_parse(struct configuration *c, int argc, char *argv[]) {
    int done = 0;
    int ret = 0;
	opterr = 0;

	while ((ret = getopt_long(argc, argv, "", options, NULL)) != -1) {
		switch (ret) {
		case CFG_LOGIN_SERVER:
			configuration::s_loginServer = optarg;
			break;
        case CFG_WEBSOCKET_SERVER:
			configuration::s_wsServer = optarg;
			break;
		case CFG_USERNAME:
			configuration::s_username = optarg;
			break;
		case CFG_PASSWORD:
			configuration::s_password = optarg;
			break;
		case CFG_TOKEN:
			configuration::s_token = optarg;
			break;
		case CFG_LOG_FILE:
			configuration::s_logFileName = optarg;
			break;
		case CFG_RECOVER_BY_SEQ_ID:
			if (parse_size_t(optarg, &configuration::s_rec_seq_id) != 0) {
				Log::error("Failed to parse recover sequence id.");
				return -1;
			}
			break;
		case CFG_RECOVER_BY_TIMESTAMP:
			if (parse_size_t(optarg, &configuration::s_rec_ts) != 0) {
				Log::error("Failed to parse recover timestamp.");
			}
			break;
		case CFG_SUBJECT:
			configuration::s_topics.push_back(optarg);
			break;
		case CFG_HELP:
			usage(argv[0]);
			return 0;

		case '?':
			Log::error("Option '%c' not defined\n", optopt);
            usage(argv[0]);
			return -1;
			break;
		default:
			Log::error("Option no recognized!'\n", optopt);
			abort();
		}
	}
	// Verify that all required options are set
	if (configuration::s_wsServer.empty()) {
		Log::error("Websocket server not set.  Stop!");
		return -1;
	} else {
		Log::info("Websocket server: wss://%s:%i/stream", configuration::s_wsServer.c_str(), configuration::s_wsPort);
	}

	if (configuration::s_loginServer.empty()) {
		Log::info("Login Server empty.  Using Websocket server address.");
		configuration::s_loginServer = configuration::s_wsServer;
	} else {
		Log::info("Login server: https://%s/login", configuration::s_loginServer.c_str());
	}

	if (configuration::s_topics.empty()) {
		Log::error("No topic selected.  Stop!");
		return -1;
	} else {
		Log::info("Selected subjects: %s", Container::print_container(configuration::s_topics).c_str());
	}

	if (configuration::s_token.empty()) {
		if (configuration::s_username.empty()) {
			Log::info("Username not set.  Please enter username:");
			std::cin >> configuration::s_username;
		}
		Log::info("Username: %s", configuration::s_username.c_str());
		if (configuration::s_password.empty()) {
			Log::info("Password not set.  Please enter password:");
			get_password(configuration::s_password);
		}
	}


	if (configuration::s_rec_seq_id != 0) {
		Log::info("Recovering data from sequence ID %zu", configuration::s_rec_seq_id);
	}

	if (configuration::s_rec_ts != 0) {
		Log::info("Recovering data from timestamp %zu", configuration::s_rec_ts);
	}
    return 0;
}

static inline int parse_size_t(const char *s, size_t *pi)
{
  char *end;
  *pi = strtoul(s, &end, 10);
  if (!*s || *end)
    return -1;
  return 0;
}

static inline int parse_int(const char *s, int *pi)
{
  char *end;
  *pi = strtoul(s, &end, 10);
  if (!*s || *end)
    return -1;
  return 0;
}