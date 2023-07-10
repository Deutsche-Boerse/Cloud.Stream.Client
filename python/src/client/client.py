#!/usr/bin/env python3

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


# Configure logging format
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)

# Global variable: number of messages storing the previous value
n_messages = 0
n_messages_prev = 0

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
                if args.timestampmsg:
                    flog.write((time.time_ns()).to_bytes(8, byteorder="big", signed=False))
            flog.write(message.data)
        else:
            logging.info("got 0 bytes message")


async def msgStat():
    """
    Print messages-per-second every second
    """
    global n_messages, n_messages_prev, shutdownNow
    # first sleep to second mark (try to be as close as possible to .000 milisecond)
    t1 = datetime.datetime.now()
    tms = (1000000 - t1.microsecond) / 1000
    logging.info("t1:{}, tms:{}".format(t1, int(tms)))
    # millisecond sleep to hit "second mark .000"
    await asyncio.sleep(tms / 1000)
    logging.info("t:{}".format(datetime.datetime.now()))
    while not shutdownNow:
        logging.info("{} msgs/s".format(n_messages - n_messages_prev))
        n_messages_prev = n_messages
        # sleep to hit "second mark .000"
        t1 = datetime.datetime.now()
        tms = (1000000 - t1.microsecond) / 1000
        await asyncio.sleep(tms / 1000)
    logging.info("msgStat finished")


async def on_message_to_queue(message, qq):
    """
    Receiving a websocket message message and put it to queue.
    """
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


#testsList = [(1,'{"event":"subscribe", "requestId":123456789, "subscribe":{"stream":[{"stream": "md-tradegate"}]}}'),(10,'stop')]
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
    global mainTask, shutdownNow
    asyncio.current_task().set_name("start")
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(connect=10)
    ) as session:
        async with session.ws_connect(
            timeout=aiohttp.ClientTimeout(connect=10),
            url=ws_url,
            headers=url_header,
            ssl=True,
            proxy='http://proxy.shrd.dbgcloud.io:3128',
            heartbeat=30,
            params={"format": args.msgFormat},
        ) as ws:
            logging.info(
                "successful connected {} to {}!".format(
                    ws.get_extra_info("sockname"), ws.get_extra_info("peername")
                )
            )
            mainTask = asyncio.create_task(doTasks(ws, qq))
            await mainTask
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
    args.msgFormat = "proto"
    logging.info(
        "server:{} username:{} password:xXxXxX format:{}".format(
            server, username, args.msgFormat
        )
    )
    # If no token is provided: Collect from username and password and persist it
    if not args.token:
        data = {
            "username": username,
            "password": password,
        }
        data = json.dumps(data).encode()

        logging.info(
            "Authenticate using username and password at server {}".format(server)
        )
        req = requests.post(
            "https://" + server + "/login",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        if req.status_code >= 400:
            invalid_request_reason = req.text
            loggin.info(f"failed because: {invalid_request_reason}")
        args.token = req.json()["AccessToken"]

        # Cleanup sensitive data
        del data
        del req

    # Validate that we can extract header information from JWT-Token
    #headers = verifyToken(args.token)
    #logging.info("Successfully extracted headers from JWT Token: {}".format(headers))

    url_header = {"Authorization": "Bearer " + args.token}
    ws_url = "wss://" + server + "/stream?format=" + args.msgFormat
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
