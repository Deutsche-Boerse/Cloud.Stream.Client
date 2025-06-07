#include "webinterface.h"

#include "config.h"
#include "client.pb.h"
#include "md_energy.pb.h"

#include <nlohmann/json.hpp>
#include <utils/log.h>

#include <exception>
#include <iostream>
#include <string>

using namespace std::literals::string_literals;
using namespace std::literals::chrono_literals;

WebInterface::WebInterface() {
	if (configuration::s_token.empty()) {
		Log::error("Token empty. Please povide an X-API-Key");
	}

	if (!configuration::s_logFileName.empty()) {
		m_outputMessageFile.open(configuration::s_logFileName, std::ios::out | std::ios::binary);
	}
}

WebInterface::~WebInterface() {
}

void WebInterface::run() {
	// Connect to a server with encryption
	const auto url =
	    "wss://" + configuration::s_wsServer + "/stream?format=proto";
	m_ws.setUrl(url);
	ix::WebSocketHttpHeaders headers;
	headers["X-API-Key"] = configuration::s_token;
	m_ws.setExtraHeaders(headers);

	Log::info("Connecting to %s ...", url.c_str());

	// Setup a callback to be fired 
	// when a message or an event (open, close, error) is received
	m_ws.setOnMessageCallback([this](const ix::WebSocketMessagePtr &msg) {
		if (msg->type == ix::WebSocketMessageType::Message) {
			Client::StreamMessage smsg;
			smsg.ParseFromString(msg->str);
			for (auto i = 0; i < smsg.messages_size(); i++)
			{
				Log::info("received message: %s", smsg.messages(i).ShortDebugString().c_str());
			}
			std::chrono::steady_clock::time_point currTime = std::chrono::steady_clock::now();
			int reportTimeDiff = std::chrono::duration_cast<std::chrono::milliseconds>
				(currTime - m_lastReportTime).count();
			if (reportTimeDiff > 1000) {
				Log::info("Message rate: %7zu msg/sec", (m_message_count * 1000) / reportTimeDiff);
				m_lastReportTime = currTime;
				m_message_count = 0;
			}
			++m_message_count;
		} else if (msg->type == ix::WebSocketMessageType::Open) {
			Log::info("Connection established");
			m_lastReportTime = std::chrono::steady_clock::now();
			// Send subscribe message to the server
			m_ws.sendBinary(build_subscribe_message());
			Log::info("Subscription messages sent");
		} else if (msg->type == ix::WebSocketMessageType::Error) {
			// Maybe SSL is not configured properly
			Log::error("Connection error: %s", msg->errorInfo.reason.c_str());
		}
	});

	// Now that our callback is setup, we can start receive messages
	m_ws.run();
}

std::string WebInterface::build_subscribe_message() const {
	auto msg = Client::Request();
	msg.set_event("subscribe");
	msg.set_requestid(m_requestId++);
	auto sub = msg.mutable_subscribe();
	for (const auto &topic : configuration::s_topics) {
		auto s = sub->add_stream();
		s->set_stream(topic);
		if (configuration::s_rec_seq_id != 0)
			s->set_startseq(configuration::s_rec_seq_id);
		if (configuration::s_rec_ts != 0)
			s->set_starttime(configuration::s_rec_seq_id);
	}
	std::string res;
	msg.SerializeToString(&res);
	return res;
}


std::string WebInterface::build_unsubscribe_message() const {
	auto msg = Client::Request();
	msg.set_event("unsubscribe");
	msg.set_requestid(m_requestId++);
	auto unsub = msg.mutable_unsubscribe();
	for (const auto &topic : configuration::s_topics) {
		unsub->add_stream(topic);
	}
	std::string res;
	msg.SerializeToString(&res);
	return res;
}
