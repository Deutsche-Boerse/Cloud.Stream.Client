# Cloud Stream Client
Cloud Stream Client is designed to showcase of connectivity between
client application through WebSocket communication with Cloud Stream.
The project utilizes Protocol Buffers (protobuf) as a 
language-neutral data serialization mechanism to efficiently exchange 
messages between the client and the cloud stream service. 

This README provides a brief overview of the project structure, dependencies,
and instructions on how to build and run the client program.

## Table of Contents
* [Python client](#python-client)
* [Docker based](#docker-based)
  * [Dependencies](#dependencies)
  * [Project Structure](#project-structure)
  * [Build Instructions](#build-instructions)
  * [Running the Client](#running-the-client)
  * [List of Parameters](#list-of-parameters)

## Python client
A Python client can be run with minimum effort. It is the same as the one used in Docker 

First we need to make sure python3 is available.

```myuser:~/Cloud.Stream.Client$ $ python3 --version```

Second we need to install the modules required

```myuser:~/Cloud.Stream.Client$ pip3 install --user -r python/requirements.txt```

Export your api-key generated in the GUI as API_KEY environment variable

Clone the repo and go to the root folder of the repo to run the command to start the python client and subscribe to your desired subject.
For example:

```myuser:~/Cloud.Stream.Client$ python3 python/src/client/client.py --websocket-server md.deutsche-boerse.com --subject md-tradegate --token $API_KEY --msgFormat json```

The messages are logged by default into streamclient.log
The message format is proto by default, the above example uses json but proto is recommended.
The https_proxy variable must be exported if you run this from behind a proxy.

Generally, feel free to modify the client.py before you run or other purposes
```
myuser:~/Cloud.Stream.Client$ head -2 streamclient.log
{'subs': 'md-tradegate', 'messages': [{'@type': 'type.googleapis.com/Client.Response', 'requestId': '123456789', 'subscription': {'statusCode': 200}}]},
{'subs': 'md-tradegate', 'seq': '356857164', 'messages': [{'@type': 'type.googleapis.com/dbag.cef.MarketData', 'Seq': {'ApplID': 2150, 'ApplSeqNum': '7255305109391986657'}, 'Instrmt': {'MktID': 'XGAT', 'Sym': 'LU1291109616', 'SecTyp': 'FUN'}, 'Dat': {'Bid': {'Px': {'m': '133401', 'e': -4}, 'Sz': {'m': '2000'}, 'MDQteTyp': {'Value': 'TRADEABLE'}, 'Typ': {}}, 'Offer': {'Px': {'m': '133519', 'e': -4}, 'Sz': {'m': '2000'}, 'MDQteTyp': {'Value': 'TRADEABLE'}, 'Typ': {'Value': 'OFFER'}}, 'Status': {'Value': 'ACTIVE'}, 'TrdgStat': {'Value': 'CONTINUOUS'}, 'Tm': '1689257358134000000'}}]}
```


## Docker based
One can docker in case you're restricted on the machine you're running the client.

### Dependencies
The project includes a Dockerfile containing all necessary dependencies.
To build the image simply run `make build-image`, which will genearte an 
image with all required dependecies. Alternatively, if you prefer building 
from source code, the following dependencies are required. 
* `mdstream-client-cpp`:
    - C++ compiler with C++17 support (e.g., GCC, Clang)
    - Protobuf 3.21 or later
    - IXWebSocket 11.4 or later
    - [nlohmann/json](https://github.com/nlohmann/json)

* `mdstream-client-python`:
    - Python 3.6 or later
    - [websockets](https://github.com/aaugustin/websockets)
    - [pyjwt](https://github.com/jpadilla/pyjwt)
    - [pprint](https://docs.python.org/3/library/pprint.html)
    - [protobuf](https://pypi.org/project/protobuf/)
    - [requests](https://github.com/psf/requests)
    - [urllib](https://docs.python.org/3/library/urllib.html)

### Project Structure
The project is organized as follows.
```
Cloud.Stream.Client
├── Makefile
├── README.md
├── build-image
├── proto
|   ├── README.md
|   ├── rules.mk
|   └── src
|       ├── client.proto
|       ├── md_cef.proto
|       ├── md_crypto.proto
|       └── md_energy.proto
├── cpp
|   ├── README.md
|   ├── rules.mk
|   └── src
|       ├── client
|       |   └── ...
|       └── utils
|           └── ...
└── python
    ├── README.md
    ├── requirements.txt
    ├── rules.mk
    └── src
        ├── client
        |   └── ...
        └── interpreter
            └── ...
```

* `cpp/`: Contains the C++ client code.
* `python/`: Contains the Python Client and requirements.
* `proto/`: Contains the Protocol Buffer definition files (.proto) for message serialization
* `.devcontainer/`: Contains Dockerfile for building an image with all dependencies.
* `Makefile`: A Makefile containinng build targets and commands.

### Build Instructions
1. Clone the repository:
```bash
git clone https://github.com/deutsche-boerse/Cloud.Stream.Client.git
cd Cloud.Stream.Client
```

2. Build the Docker image. (optional)
```bash
make build-image
make run-container
```

#### mdstream-client-cpp
3. Generate C++ files and headers from protobuf files.
```bash
make proto-cpp
```

4. Compile and link the C++ client.
```bash
make mdstream-client-cpp
```

#### mdstream-client-python
3. Generate Python sources from protobuf files
```bash
make proto-python
```

4. Generate Python sources for the client.
```bash
make mdstream-client-python
```


### Running the Client
Here's an example how to run `mdstream-client-cpp`
```
./build/cpp/mdstream-client-cpp --websocket-server [CLOUD_STREAM_SERVER]  \
    --subject [STREAM] --username [USER] --password [PASSOWRD] 
```

Here's an example how to run `mdstream-client-python`
```
python3 ./build/python/client.py --websocket-server [CLOUD_STREAM_SERVER] \   
    --subject [STREAM] --token [API_KEY]
```

### List of Parameters
| Parameter                | type          | Description                                            |
| ------------------------ | ------------- | ------------------------------------------------------ |
| `--login-server`         | String (URL)  | login server URL to get jwt authentication key         |
| `--websocket-server`     | String (URL)  | WebSocket address of Cloud Stream interface            |
| `--token`                | String        | Authentication token                                   |
| `--subject`              | String        | Requested subjects. Multiple subjects can be selected. |
| `--log-file`             | String (Path) | Write messages to specified file or stdout if no file is given |
| `--recover-by-seq-id`    | Integer       | Recover message starting from ID                       |
| `--recover-by-timestamp` | Integer       | Recover message from timestamp in nanosecond           |
| `--msgFormat`            | String        | proto or json as message format delivered to client    |
