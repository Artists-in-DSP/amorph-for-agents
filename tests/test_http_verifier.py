#!/usr/bin/env python3

import functools
import http.server
import threading
import unittest

from scripts.verify_http_endpoint import DEFAULT_RELEASE, ROOT, verify


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class HttpVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(
            QuietHandler,
            directory=str(ROOT / "public-context"),
        )
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_public_tree_passes_anonymous_http_contract(self):
        result = verify(self.base_url, DEFAULT_RELEASE, ("AmorphContextTest/1.0",))
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(6, len(result["receipts"]))
        self.assertEqual(404, result["missing_path_status"])


if __name__ == "__main__":
    unittest.main()
