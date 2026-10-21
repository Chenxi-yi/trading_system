import json
import ssl
import unittest
from urllib.error import HTTPError, URLError
from miniquant.data.public_failures import failure_record


class PublicFailureTests(unittest.TestCase):
    def test_access_block_and_no_sensitive_message(self):
        for code in (403,451):
            record=failure_record(HTTPError('https://secret.test?key=secret',code,'secret',{'secret':'secret'},None))
            self.assertEqual(record['http_status'],code)
            self.assertTrue(record['access_block'])
            self.assertNotIn('secret',json.dumps(record))

    def test_temporary_http_error_is_distinct_from_block(self):
        record=failure_record(HTTPError('https://test',502,'secret',{},None))
        self.assertFalse(record['access_block'])
        self.assertEqual(record['http_status'],502)

    def test_tls_type_and_errno_only(self):
        record=failure_record(URLError(ssl.SSLEOFError(8,'secret')))
        self.assertEqual(record['reason_type'],'SSLEOFError')
        self.assertEqual(record['reason_errno'],8)
        self.assertNotIn('secret',json.dumps(record))

    def test_string_reason_is_not_saved(self):
        self.assertEqual(failure_record(URLError('secret')),dict(error_type='URLError',reason_type='str'))
