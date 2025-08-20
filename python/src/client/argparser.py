import argparse
import sys


class argParser:
    """
    Parser class that parses parameters from commandline
    """

    def __init__(self, argv=sys.argv[1:]):
        """
        commandline input
        """
        self.parser = argparse.ArgumentParser(
            description="Subscribe to the Cloud Stream from Deutsche Boerse"
        )
        # Connection parameters: Server and topics
        self.parser.add_argument("--login-server")
        self.parser.add_argument("--websocket-server")

        # Authentication
        self.parser.add_argument("--username")
        self.parser.add_argument("--password")
        self.parser.add_argument("--token")

        # Token
        self.parser.add_argument(
            "--subject", nargs="+", required=True, help="<Required> Set topics"
        )

        # Output
        self.parser.add_argument("-n", "--log_every_n_messages", default=100000, type=int)
        self.parser.add_argument("--log-file", default="streamclient.log")
        self.parser.add_argument("--timestampmsg", action="store_true")
        self.parser.add_argument(
            "--no-log_messages", dest="log_messages", action="store_false"
        )
        self.parser.add_argument(
            "--no-timestamps", dest="timestampmsg", action="store_false"
        )

        self.parser.add_argument("--recover-by-seq-id")
        self.parser.add_argument("--recover-by-timestamp")

        self.parser.add_argument("--msgFormat", default="proto")
        self.parser.add_argument("--testfile", default="")
        self.parser.add_argument("--compressionLevel", default=0, type=int)

        self.args = self.parser.parse_args()

    def get_args(self):
        """
        Return parsed arguments
        """
        return self.args
