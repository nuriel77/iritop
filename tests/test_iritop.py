from BaseHTTPServer import (BaseHTTPRequestHandler, HTTPServer)
import socket
import threading
import unittest
import argparse
import logging
import json
import sys
from contextlib import (contextmanager, closing)
from cStringIO import StringIO
from os import path
sys.path.append( path.dirname( path.dirname( path.abspath(__file__) ) ) )

import iritop


LOG = logging.getLogger(__name__)


### START TEST CASES ###
class TestArgParser(unittest.TestCase):
 
    def setUp(self):
        self.args = None

    def reset_argv(self):
        sys.argv = [sys.argv[0]]

    def parse_args(self):
        self.args = iritop.parse_args()

    def set_new_args(self, args):
        # Reset args to script name only
        self.reset_argv()

        # Set argument(s)
        for arg in args:
            sys.argv.append(arg)

        # Parse arguments
        self.parse_args()
 
    def test_valid_node_url(self):
        """
        Test valid node URLs
        """
        valid_node_urls = [
            'http://localhost:12345',
            'https://10.30.40.50:12345',
            'http://[::1]:12345',
            'http://[2001:0db8:85a3:0000:0000:8a2e:0370:7334]:33221'
        ]

        for node in valid_node_urls:
            LOG.debug("Testing URL: '%s'" % node)
            self.set_new_args(['--node=' + node])
            self.assertEqual(self.args.node, node)


    def test_invalid_node_url(self):
        """
        Test invalid node URLs
        """
        invalid_node_urls = [
            'httpdwdwdw://localhost:12345',
            'http:/hello.com:1234',
            'https://hello.bla.com:456677',
            'http://14*929=.com'
        ]

        for node in invalid_node_urls:        
            with self.assertRaises(SystemExit):
                LOG.debug("Testing invalid URL: '%s'" % node)
                self.set_new_args(['--node=' + node])

    def test_return_version_string(self):
        """
        Test return Version string and exit
        """
        with captured_output() as (out, err):
            with self.assertRaises(SystemExit):
                self.set_new_args(['--version'])
                output = out.getvalue().strip()
                self.assertEqual(output, 'iritop ' + iritop.__VERSION__)
 
    def test_config_file_not_found(self):
        """
        Test file not found error
        """
        with self.assertRaises(IOError):
            self.set_new_args(['--config=unknown.yml'])


class TestFetchData(unittest.TestCase):

    def setUp(self):
        args = {
            'poll_delay': 1,
            'blink_delay': 0.5,
            'obscure_address': False,
            'test': False,  # Remove?
        }

        """ Get free port and set node address """
        self.free_port = testHTTPServer.find_free_port()
        iritop.NODE = 'http://127.0.0.1:%d' % self.free_port

        """ Test HTTP server instance """
        self.server = testHTTPServer(bind_port=self.free_port, bind_address='127.0.0.1')
        self.start_server()

        """ IRITop instance """
        self.iri_top = iritop.IriTop(Struct(**args))

    def start_server(self):
        self.server_thread = threading.Thread(target=self.server.serve_until_shutdown)
        self.server_thread.daemon = True
        self.server_thread.start()
        LOG.debug("Started test HTTP server at port %d" % self.free_port)

    def test_get_neighbors(self):
       result = iritop.fetch_data({'command': 'getNeighbors'})
       LOG.debug("getNeighbors result: %s" % str(result))

       """ Simply test expect number of keys returned from data """
       self.assertEqual(len(result[0][0].keys()), 8)

    def test_get_node_info(self):
       result = iritop.fetch_data({'command': 'getNodeInfo'})
       LOG.debug("getNodeInfo result: %s" % str(result))

       """ Simply test expect number of keys returned from data """
       self.assertEqual(len(result[0].keys()), 20)

    def test_bad_request(self):
        """ Test bad request """
        with self.assertRaises(Exception):
            result = iritop.fetch_data({'command': 'invalid'})


### END TEST CASES """

""" Handler for HTTP Server requests """
class HTTPHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        """ Simple POST router """
        if self.path == '/':
            content_len = int(self.headers.get('content-length'))
            post_body = self.rfile.read(content_len)
            data = json.loads(post_body.decode('ascii'))
            self._process_data(data)
        else:
            self.do_response(code=404)

    def _process_data(self, data):
        LOG.debug("Server got data: '%s'" % data)
        if 'command' not in data:
            self.do_response(response={"error": "missing command"}, code=400)

        if data['command'] == 'getNeighbors':
            code = 200
            response = [{
                "address": "vmi11111.testserver.net:14600",
                "connectionType": "udp",
                "numberOfAllTransactions": 123280,
                "numberOfInvalidTransactions": 0,
                "numberOfNewTransactions": 22093,
                "numberOfRandomTransactionRequests": 1097,
                "numberOfSentTransactions": 110276,
                "numberOfStaleTransactions": 3413
            },
            {
                "address": "node03.testserver.nl:15700",
                "connectionType": "tcp",
                "numberOfAllTransactions": 122298,
                "numberOfInvalidTransactions": 0,
                "numberOfNewTransactions": 17055,
                "numberOfRandomTransactionRequests": 1095,
                "numberOfSentTransactions": 109190,
                "numberOfStaleTransactions": 3798
            }]
        elif data['command'] == 'getNodeInfo':
            code = 200
            response = {
                "appName": "IRI",
                "appVersion": "1.5.6-RELEASE",
                "coordinatorAddress": "KPWCHICGJZXKE9GSUDXZYUAPLHAKAHYHDXNPHENTERYMMBQOPSQIDENXKLKCEYCPVTZQLEEJVYJZV9BWU",
                "duration": 0,
                "features": [
                    "snapshotPruning",
                    "dnsRefresher",
                    "zeroMessageQueue",
                    "tipSolidification"
                ],
                "jreAvailableProcessors": 4,
                "jreFreeMemory": 585111872,
                "jreMaxMemory": 3221225472,
                "jreTotalMemory": 2013265920,
                "jreVersion": "1.8.0_191",
                "latestMilestone": "WWUOHJKZHJRDTIYSGYRIEUFCOJIJYGZJNPMRVNPOWQPOJAOGORXYRTWTPDXKLUJQ99YVUPKGZJXO99999",
                "latestMilestoneIndex": 968273,
                "latestSolidSubtangleMilestone": "KRNMNTGO9RWUJRQQKFTXVVX9KLAHQQSJGCJYTNIPUSGODMMOUWZLNAEUJE9APAGSMUDAGQPJVNHV99999",
                "latestSolidSubtangleMilestoneIndex": 968272,
                "milestoneStartIndex": 933210,
                "neighbors": 8,
                "packetsQueueSize": 0,
                "time": 1547589763171,
                "tips": 3601,
                "transactionsToRequest": 51
            }
        else:
            response = {"error": "invalid command"}
            code = 400

        self.do_response(code=code, response=response)
        
    def do_response(self, response=None, code=200):
        self._set_headers(code)
        self.wfile.write(json.dumps(response).encode())

    def _set_headers(self, code):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()


""" HTTP test server """
class testHTTPServer():

    def __init__(self, bind_address, bind_port):
        self.server_address = (bind_address, bind_port)

    def serve_until_shutdown(self):
        self.httpd = HTTPServer(self.server_address, HTTPHandler)
        while True:
            self.httpd.handle_request()

    @staticmethod
    def find_free_port():
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('', 0))
            return s.getsockname()[1]


@contextmanager
def captured_output():
    """ Capture output context mgr """
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class Struct:
    """ Transform dict to namspace """
    def __init__(self, **entries):
        self.__dict__.update(entries)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, format='[%(levelname)s] %(message)s')
    logging.getLogger(__name__).setLevel(logging.DEBUG)
    unittest.main()