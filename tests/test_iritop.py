# flake8: noqa

import socket
import threading
import unittest
import logging
import random
import time
import json
import sys
from os import (path, environ)
from functools import wraps
from blessed import Terminal
from contextlib import (contextmanager, closing)


try:
    from BaseHTTPServer import (BaseHTTPRequestHandler, HTTPServer)
except ImportError:
    from http.server import (BaseHTTPRequestHandler, HTTPServer)  # python 3

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO  # python 3


sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import iritop # noqa

LOG = logging.getLogger(__name__)


# START TEST CASES


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
            LOG.info("Testing URL: '%s'" % node)
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
                LOG.info("Testing invalid URL: '%s'" % node)
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

    def test_password_and_username(self):
        """
        Test username set but not password and vice-versa
        """
        with self.assertRaises(SystemExit):
            LOG.info("Testing only username passed")
            self.set_new_args(['--username=nobody'])

        with self.assertRaises(SystemExit):
            LOG.info("Testing only password passed")
            self.set_new_args(['--password=secret'])

    def test_valid_sort(self):
        sortorderlist = ["", " "+u"\u25BC", " "+u"\u25B2"]
        sort_tests = [
            {'arg': 1, 'col': "", 'order': sortorderlist[1]},
            {'arg': 3, 'col': "", 'order': sortorderlist[1]},
            {'arg': -2, 'col': "", 'order': sortorderlist[2]},
            {'arg': -4, 'col': "", 'order': sortorderlist[2]},
            {'arg': 100, 'col': "", 'order': sortorderlist[1]},
            {'arg': -100, 'col': "", 'order': sortorderlist[1]},
        ]

        for st in sort_tests:
            LOG.info("Testing Sort on column: '%s'" % st['arg'])
            self.set_new_args(['--sort=%s' % st['arg']])
            it = iritop.IriTop(self.args)
            idx = abs(int(st['arg']))-1
            try:
                st['col'] = it.txkeys[idx]['sortcolumn']
            except IndexError:
                st['col'] = it.txkeys[0]['sortcolumn']
            LOG.info("Sort column: %s (%s)" % (it.sortcolumn, "reverse" if
                                                it.sortorder ==
                                                sortorderlist[1]
                                                else "forward"))
            self.assertEqual(it.sortcolumn, st['col'])


class TestFetchData(unittest.TestCase):

    # Note that setUp runs on each test method
    # Could opt for a way to bring up the server
    # for the entire duration of the class test
    def setUp(self):
        args = {
            'poll_delay': 1,
            'blink_delay': 0.5,
            'obscure_address': False,
            'test': False,  # Remove?
            'password': 'secret',
            'username': 'nobody',
            'sort': 3,
            'show_domains': False
        }

        """ Get free port and set node address """
        self.free_port = testHTTPServer.find_free_port()
        iritop.NODE = 'http://127.0.0.1:%d' % self.free_port

        """ Test HTTP server instance """
        self.server = testHTTPServer(bind_port=self.free_port,
                                     bind_address='127.0.0.1')
        self.start_server()

        LOG.debug("Wait for HTTP server")
        while True:
            if is_open('127.0.0.1', self.free_port) is True:
                break
            time.sleep(0.2)

        """ IRITop instance """
        self.iri_top = iritop.IriTop(Struct(**args))

    def start_server(self):
        self.server_thread = threading.Thread(
            target=self.server.serve_until_shutdown)
        self.server_thread.daemon = True
        self.server_thread.start()
        LOG.info("Started test HTTP server at port %d" % self.free_port)

    def test_get_neighbors(self):
        result = iritop.fetch_data({'command': 'getNeighbors'})
        LOG.debug("getNeighbors result: %s" % str(result))

        """ Simply test neighbors key exists in result """
        self.assertIn('neighbors', result[0])

    def test_get_node_info(self):
        result = iritop.fetch_data({'command': 'getNodeInfo'})
        LOG.debug("getNodeInfo result: %s" % str(result))

        """ Simply test appName key exists in result """
        self.assertIn('appName', result[0])

    def test_bad_request(self):
        """ Test bad request """
        with self.assertRaises(Exception):
            result = iritop.fetch_data({'command': 'invalid'})
            result = result

    def test_run_for_a_while(self):
        iritop.MAX_CYCLES = 10

        """ Return None = exited without errors """
        self.assertEqual(self.iri_top.run(FakeSCR), None)


class FakeSCR:
    @staticmethod
    def clear():
        pass


# END TEST CASES


def is_open(ip, port):
    # TODO: See how to supress warning
    # 'ResourceWarning: unclosed <socket.socket...'
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, int(port)))
        s.shutdown(2)
        return True
    except Exception:
        return False


""" Check authentication wrapper """
def check_auth(func):
    @wraps(func)
    def wrapped(inst, *args, **kw):

        # nobody:secret base64 encoded
        if (inst.headers.get('Authorization') ==
                'Basic bm9ib2R5OnNlY3JldA=='):

            """ Allow if Authorization successful """
            LOG.debug("Client authenticated: %s" %
                      inst.client_address[0])

            return func(inst, *args, **kw)

        else:
            """ Deny on wrong user:password """
            return inst.refuse(address=inst.client_address[0],
                               reason='Failed authentication',
                               code=403)
    return wrapped


""" Random Data Generators """
def counted(f):
    def wrapped(*args, **kwargs):
        wrapped.calls += 1
        return f(*args, **kwargs)
    wrapped.calls = 1
    return wrapped


def increment(f):
    def wrapped(*args, **kwargs):
        args[0]._increment_data()
        return f(*args, **kwargs)
    return wrapped


class Neighbor:

    protocol = ('udp', 'tcp')

    def __init__(self, count):
        self.neighbor_data = {
            "address": "someneighbor%d:%d" % (count, random.randint(21600, 25600)),
            "domain": "testing.iota%d.io" % (count),
            "connected": True,
            "connectionType": self.protocol[random.randint(0, 1)],
            "numberOfAllTransactions": random.randint(100000, 200000),
            "numberOfInvalidTransactions": random.randint(0, 3),
            "numberOfNewTransactions": random.randint(10, 20000),
            "numberOfRandomTransactionRequests": random.randint(100, 20000),
            "numberOfSentTransactions": random.randint(100000, 200000),
            "numberOfStaleTransactions": random.randint(100, 2000)
        }

    def _increment_data(self):
        self.neighbor_data = {
            "address": self.neighbor_data['address'],
            "domain": self.neighbor_data['domain'],
            "connectionType": self.neighbor_data['connectionType'],
            "numberOfAllTransactions": random.randint(
                self.neighbor_data['numberOfAllTransactions'] + 10,
                self.neighbor_data['numberOfAllTransactions'] + 200
            ),
            "numberOfInvalidTransactions": random.randint(
                self.neighbor_data['numberOfInvalidTransactions'] + 0,
                self.neighbor_data['numberOfInvalidTransactions'] + 1
            ),
            "numberOfNewTransactions": random.randint(
                self.neighbor_data['numberOfNewTransactions'] + 10,
                self.neighbor_data['numberOfNewTransactions'] + 200
            ),
            "numberOfRandomTransactionRequests": random.randint(
                self.neighbor_data['numberOfRandomTransactionRequests'] + 1,
                self.neighbor_data['numberOfRandomTransactionRequests'] + 4
            ),
            "numberOfSentTransactions": random.randint(
                self.neighbor_data['numberOfSentTransactions'] + 10,
                self.neighbor_data['numberOfSentTransactions'] + 500
            ),
            "numberOfStaleTransactions": random.randint(
                self.neighbor_data['numberOfStaleTransactions'] + 0,
                self.neighbor_data['numberOfStaleTransactions'] + 2
            )
        }

    @increment
    def get_data(self):
        return self.neighbor_data

    def __str__(self):
        return str(self.neighbor_data)


class RandomNeighborDataGenerator():

    def __init__(self):
        # Generate a random number of initial neighbors
        self.neighbors = [Neighbor(n) for n in range(1, random.randint(2, 6))]

    def rand_neighbors_count(self):
        # Randominze increase or decrease of neighbors
        if random.randint(0, 1) == 0 and len(self.neighbors) >= 2:
            del self.neighbors[ random.randint(0, len(self.neighbors)-1) ]
        else:
            self.neighbors.append(Neighbor(len(self.neighbors) + 1))

    @counted
    def get_data(self):
        return [n.get_data() for n in self.neighbors]

    def get_neighbors_count(self):
        return len(self.neighbors)


class RandomAPIDataGenerator():

    def __init__(self, neighbors_count):
        self.get_neighbors_count = neighbors_count
        self.api_data = {
            "appName": "IRI",
            "appVersion": "1.5.6-RELEASE",
            "coordinatorAddress": "KPWCHICGJZXKE9GSUDXZYUAPLHAKAHYHDXNP" +
                                  "HENTERYMMBQOPSQIDENXKLKCEYCPVTZQLEEJ" +
                                  "VYJZV9BWU",
            "duration": 0,
            "features": [
                "snapshotPruning",
                "dnsRefresher",
                "zeroMessageQueue",
                "tipSolidification"
            ],
            "jreAvailableProcessors": 4,
            "jreFreeMemory": random.randint(400000000, 600000000),
            "jreMaxMemory": 3221225472,
            "jreTotalMemory": random.randint(2000000000, 2500000000),
            "jreVersion": "1.8.0_201",
            "latestMilestone": "WWUOHJKZHJRDTIYSGYRIEUFCOJIJYGZJNPMRVNP" +
                               "OWQPOJAOGORXYRTWTPDXKLUJQ99YVUPKGZJXO" +
                               "99999",
            "latestMilestoneIndex": 933210,
            "latestSolidSubtangleMilestone": "KRNMNTGO9RWUJRQQKFTXVVX9K" +
                                             "LAHQQSJGCJYTNIPUSGODMMOUW" +
                                             "ZLNAEUJE9APAGSMUDAGQPJVNH" +
                                             "V99999",
            "latestSolidSubtangleMilestoneIndex": 933210,
            "milestoneStartIndex": 933210,
            "neighbors": self.get_neighbors_count(),
            "packetsQueueSize": 0,
            "time": int(round(time.time() * 1000)),
            "tips": random.randint(1000, 5000),
            "transactionsToRequest": random.randint(0, 100)
        }

    def _increment_data(self):
        self.api_data['jreFreeMemory'] = random.randint(400000000, 600000000)
        self.api_data['jreTotalMemory'] = random.randint(2000000000, 2500000000)
        self.api_data['latestMilestoneIndex'] += 1
        self.api_data['latestSolidSubtangleMilestoneIndex'] += 1
        self.api_data['neighbors'] = self.get_neighbors_count()
        self.api_data['time'] = int(round(time.time() * 1000))
        self.api_data['tips'] = random.randint(1000, 5000)
        self.api_data['transactionsToRequest'] = random.randint(0, 100)

    @increment
    def get_data(self):
        return self.api_data


""" Handler for HTTP Server requests """
class HTTPHandler(BaseHTTPRequestHandler):

    neighbor_data = RandomNeighborDataGenerator()
    api_data = RandomAPIDataGenerator(
            neighbor_data.get_neighbors_count)

    def refuse(self, address=None, reason=None, code=401):
        LOG.warning("HTTP: Client refused with '%s': %s" %
                    (reason, address))
        response = {}
        if address is not None:
            response['unauthorized'] = address

        if reason is not None:
            response['reason'] = reason

        self.do_response(response=response, code=401)

    @check_auth
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
        code = 200

        LOG.debug("Server got data: '%s'" % data)
        if 'command' not in data:
            self.do_response(response={"error": "missing command"}, code=400)

        # Optionally increment data values here to
        # help mimic real API port query over time
        if data['command'] == 'getNeighbors':
            if self.neighbor_data.get_data.calls % 5 == 0:
                LOG.debug("Increase or decrease neighbor count")
                self.neighbor_data.rand_neighbors_count()
            response = {"duration": 0,
                        "neighbors": self.neighbor_data.get_data()}
        elif data['command'] == 'getNodeInfo':
            response = self.api_data.get_data()
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

    def log_message(self, format, *args):
        return


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
    logging.basicConfig(stream=sys.stderr,
                        format='[%(levelname)s] %(message)s')
    logging.getLogger(__name__).setLevel(logging.INFO)
    unittest.main()
