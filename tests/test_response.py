import unittest
import json
from tempoiq.response import Response, WriteResponse
from test_protocol_cursor import DummyResponse


class TestResponse(unittest.TestCase):
    def test_response_constructor_success(self):
        resp = DummyResponse()
        r = Response(resp, None)
        self.assertEquals(r.status, 200)
        self.assertEquals(r.reason, 'OK')
        self.assertEquals(r.successful, 0)
        self.assertEquals(r.error, None)

    def test_response_constructor_failure(self):
        resp = DummyResponse()
        resp.status_code = 403
        resp.reason = 'Forbidden'
        resp.text = 'foo'
        r = Response(resp, None)
        self.assertEquals(r.status, 403)
        self.assertEquals(r.reason, 'Forbidden')
        self.assertEquals(r.successful, 1)
        self.assertEquals(r.error, 'foo')

    def test_response_constructor_partial(self):
        resp = DummyResponse()
        resp.status_code = 207
        resp.reason = 'Forbidden'
        resp.text = 'foo'
        r = Response(resp, None)
        self.assertEquals(r.status, 207)
        self.assertEquals(r.reason, 'Forbidden')
        self.assertEquals(r.successful, 2)
        self.assertEquals(r.error, 'foo')

    def test_response_status_code_alias(self):
        resp = DummyResponse()
        resp.status_code = 207
        resp.reason = 'Forbidden'
        resp.text = 'foo'
        r = Response(resp, None)
        self.assertEquals(r.status_code, 207)


class TestWriteResponse(unittest.TestCase):
    def setUp(self):
        self.all_success = json.dumps({
            'key1': {
                'device_state': 'existing',
                'message': None,
                'success': True
            },
            'key2': {
                'device_state': 'created',
                'message': None,
                'success': True
            },
            'key3': {
                'device_state': 'modified',
                'message': None,
                'success': True
            }
        })
        self.partial_success = json.dumps({
            'key1': {
                'device_state': 'existing',
                'message': None,
                'success': True
            },
            'key2': {
                'device_state': 'created',
                'message': 'bad things happened',
                'success': False
            }
        })
        self.all_failures = json.dumps({
            'key1': {
                'device_state': 'existing',
                'message': 'bad things happened',
                'success': False
            },
            'key2': {
                'device_state': 'created',
                'message': 'worse things happened',
                'success': False
            }
        })

    def test_status_success(self):
        dummy = DummyResponse()
        dummy.text = self.all_success
        resp = WriteResponse(dummy, None)
        self.assertEquals(resp.successful, 0)

    def test_status_partial(self):
        dummy = DummyResponse()
        dummy.text = self.partial_success
        resp = WriteResponse(dummy, None)
        self.assertEquals(resp.successful, 2)

    def test_status_failure(self):
        dummy = DummyResponse()
        dummy.text = self.all_failures
        resp = WriteResponse(dummy, None)
        self.assertEquals(resp.successful, 1)

    def test_getting_failures(self):
        dummy = DummyResponse()
        dummy.text = self.partial_success
        resp = WriteResponse(dummy, None)
        failures = [f for f in resp.failures]
        self.assertEquals(failures, [('key2', 'bad things happened')])

    def test_getting_created(self):
        dummy = DummyResponse()
        dummy.text = self.all_success
        resp = WriteResponse(dummy, None)
        results = [r for r in resp.created]
        self.assertEquals(results, ['key2'])

    def test_getting_existing(self):
        dummy = DummyResponse()
        dummy.text = self.all_success
        resp = WriteResponse(dummy, None)
        results = [r for r in resp.existing]
        self.assertEquals(results, ['key1'])

    def test_getting_modified(self):
        dummy = DummyResponse()
        dummy.text = self.all_success
        resp = WriteResponse(dummy, None)
        results = [r for r in resp.modified]
        self.assertEquals(results, ['key3'])
