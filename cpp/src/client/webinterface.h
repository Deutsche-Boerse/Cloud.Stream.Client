#pragma once

#include "config.h"
#include <ixwebsocket/IXWebSocket.h>

#include <fstream>

class WebInterface
{
public:
	WebInterface();
	~WebInterface();

	/** Start client process */
	void run();

protected:
	/** Obtain token using username and password from config */
	void get_token() const;
	std::string build_subscribe_message() const;

	std::string build_unsubscribe_message() const;


	mutable int m_requestId = 1;

	unsigned long long int m_message_count = 0;

private:
	ix::WebSocket m_ws;
	std::fstream m_outputMessageFile;
	std::chrono::steady_clock::time_point m_lastReportTime;
};