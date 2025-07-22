#!/usr/bin/env python3
import sys
sys.path.append(r'proto/src')

# Global imports
import datetime
from google.protobuf import json_format
import json
import logging
import os
import requests
import aiohttp
import asyncio
from multiprocessing import Process, Queue
import time

# Local imports: Protobuf
import client_pb2

# Local imports: Modules
from argparser import argParser
from jwt_token import verifyToken

global net_orig_bytes_total
class CompressionMonitoringConnector(aiohttp.TCPConnector):
    """
    Custom TCP connector that monitors raw network bytes to track compression effectiveness
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_bytes_received = 0
        self.total_bytes_sent = 0
        self.total_payload_bytes = 0
        self.connection_count = 0
    
    async def _create_connection(self, req, traces, timeout):
        """Override connection creation to add monitoring hooks"""
        conn = await super()._create_connection(req, traces, timeout)
        self.connection_count += 1
        
        # Get the transport and protocol from the connection
        transport = conn.transport
        protocol = transport.get_protocol() if hasattr(transport, 'get_protocol') else conn
        
        # Store original write method for outgoing data
        original_write = transport.write
        
        def monitored_write(data):
            """Monitor outgoing raw bytes"""
            self.total_bytes_sent += len(data)
            return original_write(data)
        
        transport.write = monitored_write
        
        # For incoming data, we need to hook at the protocol level
        # Look for data_received method on the protocol
        if hasattr(protocol, 'data_received'):
            original_data_received = protocol.data_received
            
            def monitored_data_received(data):
                """Monitor incoming raw bytes and parse multiple WebSocket frames"""
                self.total_bytes_received += len(data)
                
                # Parse potentially multiple WebSocket frames in the data
                offset = 0
                frames_parsed = 0
                total_payload_in_packet = 0
                compression_active = False
                
                while offset < len(data):
                    remaining = len(data) - offset
                    
                    # Need at least 2 bytes for basic frame header
                    if remaining < 2:
                        break
                    
                    # Parse frame header
                    first_byte = data[offset]
                    second_byte = data[offset + 1]
                    
                    fin = bool(first_byte & 0x80)
                    rsv1 = bool(first_byte & 0x40)  # Compression extension bit
                    opcode = first_byte & 0x0F
                    
                    masked = bool(second_byte & 0x80)
                    payload_len = second_byte & 0x7F
                    
                    header_size = 2
                    
                    # Handle extended payload length
                    if payload_len == 126:
                        if remaining < 4:
                            break
                        payload_len = int.from_bytes(data[offset + 2:offset + 4], 'big')
                        header_size = 4
                    elif payload_len == 127:
                        if remaining < 10:
                            break
                        payload_len = int.from_bytes(data[offset + 2:offset + 10], 'big')
                        header_size = 10
                    
                    # Add mask key size if present
                    if masked:
                        header_size += 4
                    
                    # Check if we have the complete frame
                    total_frame_size = header_size + payload_len
                    if offset + total_frame_size > len(data):
                        break
                    
                    # Successfully parsed a complete frame
                    frames_parsed += 1
                    total_payload_in_packet += payload_len
                    
                    # Track if any frame has compression active
                    if rsv1:
                        compression_active = True
                    
                    # Move to next frame
                    offset += total_frame_size
                
                if frames_parsed > 0:
                    self.total_payload_bytes += total_payload_in_packet
                    # Only log compression status changes or periodically
                    if compression_active and not hasattr(self, '_compression_logged'):
                        logging.info(f"WebSocket compression detected (RSV1=True)")
                        self._compression_logged = True
                
                return original_data_received(data)
            
            protocol.data_received = monitored_data_received
        
        # Alternative: try to hook the response handler's data_received
        elif hasattr(conn, '_protocol') and hasattr(conn._protocol, 'data_received'):
            original_data_received = conn._protocol.data_received
            
            def monitored_data_received(data):
                """Monitor incoming raw bytes via _protocol"""
                self.total_bytes_received += len(data)
                logging.info(f"Network RX (_protocol): {len(data)} bytes (total: {self.total_bytes_received})")
                return original_data_received(data)
            
            conn._protocol.data_received = monitored_data_received
        else:
            logging.warning("Could not find data_received method to hook into")
        
        return conn
    
    def get_compression_stats(self):
        """Return network-level statistics including payload-only data"""
        return {
            'total_bytes_received': self.total_bytes_received,
            'total_payload_bytes': self.total_payload_bytes,
            'total_bytes_sent': self.total_bytes_sent,
            'connections': self.connection_count
        }


# Configure logging format
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)

# Global variable: number of messages storing the previous value
n_messages = 0
n_messages_prev = 0

# Global variable: compression tracking
total_uncompressed_bytes = 0

# Global variable: monitoring connector
monitoring_connector = None

# Flag triggering end of execution
shutdownNow = False


# Forward declaration: args will be a dict
args: dict


def queuereader_proc(queue):
    """
    Collect messages passed via the queue into a file 
    """
    now = datetime.datetime.utcnow()
    filename_d = args.log_file
    # Debug: Log messages
    fLogMsg = None
    if filename_d:
        wf="w"
        if "proto" == args.msgFormat:
            wf = "wb"
        fLogMsg = open(filename_d, wf)
        logging.info("will dump messages to file:{}".format(filename_d))
    msg = "start"
    while msg != "stop":
        msg = queue.get()
        if msg == "stop":
            logging.info("queuereader_proc got stop")
        else:
            log_message(msg, fLogMsg)
    if fLogMsg:
        fLogMsg.close()


async def killRemainingTimedTasks():
    """
    Stop event processing to prepare program exit
    """
    for task in asyncio.all_tasks():
        if task.get_name() in ("start", "doTasks"):
            logging.info("skip cancelling {}".format(task.get_name()))
            continue
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logging.info("{} is cancelled now".format(task.get_name()))
    logging.info("killRemainingTimedTasks done")


mainTask = None


async def sendBytesAfterTimeout(message, to, ws, qq):
    """
    Send messages received from ws (websocket) to the queue (qq) processor.
    The "stop" message will signal that the sending must finish
    """
    logging.info(
        "{} sleeping {}s before sending message:{}".format(
            asyncio.current_task().get_name(), to, message
        )
    )
    await asyncio.sleep(to)
    global shutdownNow, mainTask
    if "stop" == message:
        logging.info("will stop now")
        qq.put(message)
        shutdownNow = True
        logging.info("stop signals were sent")
        await ws.close()
        logging.info("ws.close() done")
        return
    try:
        if "proto" == args.msgFormat:
            logging.info("trying to parse:{}".format(message))
            protomsg = json_format.Parse(message, client_pb2.Request())
            testcmd = protomsg.SerializeToString()
            await ws.send_bytes(testcmd)
            logging.info(
                "message:{} was sent (as .proto format, {} bytes)".format(
                    message, len(testcmd)
                )
            )
        else:
            await ws.send_str(message)
            logging.info("message:{} was send".format(message))
    except:
        logging.critical("cannot parse command:{}".format(message), exc_info=True)


def log_message(message, flog):
    """
    Log data of received message. Format is length(4 bytes) + message
    """
    if args.msgFormat == "json":
        msg_json = json.loads(message.data)
        if args.log_messages:
            flog.write("{},\n".format(msg_json))
    else:
        msg_proto = client_pb2.StreamMessage()
        l = len(message.data)
        if l > 0:
            if args.msgFormat == "proto":
                flog.write((l).to_bytes(4, byteorder="big", signed=False))
            flog.write(message.data)
        else:
            logging.info("got 0 bytes message")


async def msgStat():
    """
    Print messages-per-second and compression statistics every second
    """
    global n_messages, n_messages_prev, shutdownNow, total_uncompressed_bytes, monitoring_connector
    
    # Tracking previous values for calculating rates
    total_uncompressed_prev = 0
    total_network_prev = 0
    total_payload_prev = 0
    
    # first sleep to second mark (try to be as close as possible to .000 milisecond)
    t1 = datetime.datetime.now()
    tms = (1000000 - t1.microsecond) / 1000
    logging.info("t1:{}, tms:{}".format(t1, int(tms)))
    # millisecond sleep to hit "second mark .000"
    await asyncio.sleep(tms / 1000)
    logging.info("t:{}".format(datetime.datetime.now()))
    
    while not shutdownNow:
        # Get current network statistics
        stats = monitoring_connector.get_compression_stats() if 'monitoring_connector' in globals() else {
            'total_bytes_received': 0, 'total_payload_bytes': 0, 'total_bytes_sent': 0
        }
        
        # Calculate rates since last report
        msgs_rate = n_messages - n_messages_prev
        uncompressed_rate = total_uncompressed_bytes - total_uncompressed_prev
        network_rate = stats['total_bytes_received'] - total_network_prev
        payload_rate = stats['total_payload_bytes'] - total_payload_prev
        
        # Calculate compression ratios
        if args.compressionLevel == 0:
            # When compression is disabled, payload should equal uncompressed data
            payload_ratio = 1.0
            compression_savings = 0.0
        else:
            payload_ratio = payload_rate / uncompressed_rate if uncompressed_rate > 0 else 0
            compression_savings = (1 - payload_ratio) * 100 if payload_ratio > 0 else 0
        
        # Log comprehensive statistics
        compression_status = "DISABLED" if args.compressionLevel == 0 else "ENABLED"
        logging.info(
            f"Rate: {msgs_rate:4} msgs/s | "
            f"Uncompressed: {uncompressed_rate:6} B/s | "
            f"Payload: {payload_rate:6} B/s | "
            f"Network: {network_rate:6} B/s | "
            f"Compression: {compression_status} | "
            f"Savings: {compression_savings:5.1f}% | "
            f"Ratio: {payload_ratio:.3f}"
        )
        
        # Update previous values
        n_messages_prev = n_messages
        total_uncompressed_prev = total_uncompressed_bytes
        total_network_prev = stats['total_bytes_received']
        total_payload_prev = stats['total_payload_bytes']
        
        # sleep to hit "second mark .000"
        t1 = datetime.datetime.now()
        tms = (1000000 - t1.microsecond) / 1000
        await asyncio.sleep(tms / 1000)
    
    logging.info("msgStat finished")


async def on_message_to_queue(message, qq):
    """
    Receiving a websocket message and put it to queue, also tracking uncompressed message size.
    """
    global total_uncompressed_bytes
    
    # Track uncompressed message size
    if hasattr(message, 'data') and message.data:
        uncompressed_size = len(message.data)
        total_uncompressed_bytes += uncompressed_size
    
    qq.put(message)
    global n_messages
    if n_messages % args.log_every_n_messages == 0:
        if args.msgFormat == "json":
            logging.info("{:4} messages received.".format(n_messages))
        elif args.msgFormat == "proto":
            logging.info("{:4} messages received.".format(n_messages))
    n_messages += 1


async def processWs(ws, qq):
    """
    Receive messages and queue them up for further processing
    """
    global shutdownNow
    async for m in ws:
        if ("proto" == args.msgFormat and m.type == aiohttp.WSMsgType.BINARY) or (
            "json" == args.msgFormat and m.type == aiohttp.WSMsgType.TEXT
        ):
            await on_message_to_queue(m, qq)
        if m.type == aiohttp.WSMsgType.CLOSE:
            logging.info("websocket close received:{}".format(m.data))
            shutdownNow = True
            return
        if m.type == aiohttp.WSMsgType.PING:
            logging.info("websocket PING")
        if m.type == aiohttp.WSMsgType.PONG:
            logging.info("websocket PONG")


reader_p = None


def makeQueueProc(qq):
    """
    Create a separate process (as daemon) for queue processing
    We can receive from websocket as fast as possible by disconnecting
    """
    global reader_p
    reader_p = Process(target=queuereader_proc, args=((qq),))
    reader_p.daemon = True
    reader_p.start()  # Launch reader_p() as another proc


async def handleWs(ws, qq):
    global shutdownNow
    try:
        while not ws.closed and not shutdownNow:
            await processWs(ws, qq)
    except Exception as e:
        logging.info("handleWs exception", e)
    if ws.closed:
        logging.info("handleWs ws.closed")
        qq.put("stop")
        shutdownNow = True

    await killRemainingTimedTasks()
    logging.info("handleWs finished")


#testsList = [(1,'{"event":"subscribe", "requestId":123456789, "subscribe":{"stream":[{"stream": "md-tradegate"}]}}'),(30,"stop")]
testsList = []

async def doTasks(ws, qq):
    """
    Create the task list. Websocket, message statistics and timed test commands run all in the same thread
    """
    asyncio.current_task().set_name("doTasks")
    tasklist = [handleWs(ws, qq), msgStat()]
    [tasklist.append(sendBytesAfterTimeout(m, t, ws, qq)) for t, m in testsList]
    try:
        results = await asyncio.gather(*tasklist, return_exceptions=True)
    except asyncio.CancelledError:
        logging.info("gather was cancelled so we'll exit")
        return
    logging.info("doTasks done with results:{}".format(results))


async def start(qq):
    """
    Create the websocket connection and start the tasks
    """
    https_proxy = os.environ.get('https_proxy')
    global mainTask, shutdownNow, monitoring_connector
    asyncio.current_task().set_name("start")
    
    # Create custom connector for monitoring network-level bytes
    monitoring_connector = CompressionMonitoringConnector()
    
    async with aiohttp.ClientSession(
        connector=monitoring_connector,
        timeout=aiohttp.ClientTimeout(connect=10)
    ) as session:
        async with session.ws_connect(
            timeout=aiohttp.ClientTimeout(connect=10),
            url=ws_url,
            headers=url_header,
            ssl=True,
            proxy=https_proxy,
            heartbeat=30,
            params={"format": args.msgFormat, "compressionLevel":args.compressionLevel,},
            compress=None if args.compressionLevel == 0 else int(args.compressionLevel),  # Disable compression if level 0
        ) as ws:
            logging.info(
                "successful connected {} to {}!".format(
                    ws.get_extra_info("sockname"), ws.get_extra_info("peername")
                )
            )
            
            # Check if compression was negotiated
            compression_status = "DISABLED" if args.compressionLevel == 0 else f"LEVEL {args.compressionLevel}"
            logging.info(f"WebSocket client compression: {compression_status}")
            logging.info(f"Server compressionLevel parameter: {args.compressionLevel}")
            logging.info(f"Message format: {args.msgFormat}")
            
            # Check WebSocket response headers for compression negotiation
            if hasattr(ws, '_response'):
                response_headers = dict(ws._response.headers)
                compression_headers = {k: v for k, v in response_headers.items() 
                                     if 'compress' in k.lower() or 'deflate' in k.lower() or 'extension' in k.lower()}
                logging.info(f"WebSocket response headers (compression related): {compression_headers}")
            
            if args.compressionLevel == 0:
                logging.info("Compression DISABLED - RSV1 should be False in all frames")
            else:
                logging.info("Compression ENABLED - watch for RSV1=True in compressed frames")
            mainTask = asyncio.create_task(doTasks(ws, qq))
            await mainTask
            
            # Log final compression statistics
            stats = monitoring_connector.get_compression_stats()
            payload_compression_ratio = stats['total_payload_bytes'] / total_uncompressed_bytes if total_uncompressed_bytes > 0 else 0
            full_compression_ratio = stats['total_bytes_received'] / total_uncompressed_bytes if total_uncompressed_bytes > 0 else 0
            
            logging.info(f"Final compression stats:")
            logging.info(f"  Network payload bytes (compressed): {stats['total_payload_bytes']}")
            logging.info(f"  Total network bytes (with headers): {stats['total_bytes_received']}")
            logging.info(f"  Message bytes processed (uncompressed): {total_uncompressed_bytes}")
            logging.info(f"  Payload compression ratio: {payload_compression_ratio:.3f}")
            logging.info(f"  Full frame compression ratio: {full_compression_ratio:.3f}")
            logging.info(f"  Payload space saved: {((1 - payload_compression_ratio) * 100):.1f}%")
    logging.info("start is DONE")


if __name__ == "__main__":
    """
    Main function is entry point of the python script
    Get a token from /login and then load the tests from the testfile
    It creates a queue for communication between the main process (asyncio loop) and a separate file writer process
    """
    # Parse command line arguments
    parser = argParser()
    args = parser.get_args()

    # Set variables
    server = args.websocket_server
    username = args.username
    password = args.password
    subject = args.subject
    startSeq = args.recover_by_seq_id
    startTime = args.recover_by_timestamp
    recover = f', "startSeq":{startSeq}' if startSeq is not None else f', "startTime":{startTime}' if startTime is not None else ""
    if args.testfile != "":
        logging.info("processing testfile:{}".format(args.testfile))
        with open(args.testfile, "r") as testfile:
            for line in testfile:
                if line.startswith("!"):
                    continue
                if len(line) > 0:
                    cmd = line.strip().split("#")
                    if len(cmd) != 2:
                        logging.warning(
                            "line format not recognized. Should be: timeoffset#command"
                        )
                    else:
                        testsList.append((float(cmd[0]), cmd[1]))
    else:
        if subject != "":
            cmd = '{"event":"subscribe", "requestId":123456789, "subscribe":{"stream":['
            sep = ""
            for s in subject:        
                cmd = f'{cmd}{sep}{{"stream": "{s}"{recover}}}'
                sep=", "
            cmd = f"{cmd}]}}}}"
            testsList.append((0,cmd))
    logging.info(
        "server:{} username:{} password:xXxXxX format:{} subject:{}".format(
            server, username, args.msgFormat, subject
        )
    )

    # Validate that we can extract header information from JWT-Token
    #headers = verifyToken(args.token)
    #logging.info("Successfully extracted headers from JWT Token: {}".format(headers))

    url_header = [("X-API-Key", args.token)]
    ws_url = "wss://" + server + "/stream"
    qq = Queue()
    makeQueueProc(qq)
    asyncio.run(start(qq))
    if reader_p.is_alive():
        qq.close()
        qq.join_thread()
        reader_p.join()
        logging.info("reader_p done")
    else:
        logging.info("reader_p not alive")
