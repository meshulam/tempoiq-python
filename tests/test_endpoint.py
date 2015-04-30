import unittest
from monkey import monkeypatch_requests
from tempoiq import endpoint as p
from tempoiq import __version__


class TestEndpoint(unittest.TestCase):
    def setUp(self):
        self.end = p.HTTPEndpoint('www.nothing.com', 'foo', 'bar')
        monkeypatch_requests(self.end)

    def test_make_url_args_list(self):
        params = {'foo': [1, 'foo']}
        ret = p.make_url_args(params)
        self.assertEquals(ret, 'foo=1&foo=foo')

    def test_make_url_args_tuple(self):
        params = {'foo': (1, 'foo')}
        ret = p.make_url_args(params)
        self.assertEquals(ret, 'foo=1&foo=foo')

    def test_make_url_args_dict(self):
        params = {'foo': {'bar': 'baz',
                          'abc': 'def'}}
        ret = p.make_url_args(params)
        pass1 = 'foo%5Bbar%5D=baz' in ret
        pass2 = 'foo%5Babc%5D=def' in ret
        self.assertTrue(pass1)
        self.assertTrue(pass2)

    def test_make_url_args_bool_true(self):
        params = {'foo': True}
        ret = p.make_url_args(params)
        self.assertEquals(ret, 'foo=true')

    def test_make_url_args_bool_false(self):
        params = {'foo': False}
        ret = p.make_url_args(params)
        self.assertEquals(ret, 'foo=false')

    def test_make_url_args_bool_none(self):
        params = {'foo': None}
        ret = p.make_url_args(params)
        self.assertEquals(ret, '')

    def test_make_url_args_bool_bare_value_str(self):
        params = {'foo': 'bar'}
        ret = p.make_url_args(params)
        self.assertEquals(ret, 'foo=bar')

    def test_make_url_args_bool_bare_value_non_str(self):
        params = {'foo': 2.0}
        ret = p.make_url_args(params)
        self.assertEquals(ret, 'foo=2.0')

    def test_endpoint_constructor(self):
        self.assertEquals(self.end.base_url, 'https://www.nothing.com/v2/')
        self.assertEquals(self.end.headers['User-Agent'],
                          'tempoiq-python/%s' % __version__)
        self.assertEquals(self.end.headers['Accept-Encoding'], 'gzip')
        self.assertTrue(hasattr(self.end, 'auth'))

    def test_endpoint_constructor_with_schema(self):
        self.end = p.HTTPEndpoint('http://www.nothing.com', 'foo', 'bar')
        self.assertEquals(self.end.base_url, 'http://www.nothing.com/v2/')
        self.assertEquals(self.end.headers['User-Agent'],
                          'tempoiq-python/%s' % __version__)
        self.assertEquals(self.end.headers['Accept-Encoding'], 'gzip')
        self.assertTrue(hasattr(self.end, 'auth'))

    def test_make_url_with_port(self):
        ret = p.construct_url('www.example.com', False, 8080)
        self.assertEquals(ret, 'http://www.example.com:8080')

    def test_make_url_with_trailing_slash(self):
        ret = p.construct_url('http://www.example.com/', True, None)
        self.assertEquals(ret, 'http://www.example.com')

    def test_make_url_with_trailing_slash_and_port(self):
        ret = p.construct_url('example.com/', True, 8080)
        self.assertEquals(ret, 'https://example.com:8080')

    def test_endpoint_post(self):
        url = 'series/'
        body = 'foobar'
        self.end.pool.post.return_value = True
        self.end.post(url, body)
        self.end.pool.post.assert_called_once_with(
            'https://www.nothing.com/v2/series/',
            data=body,
            headers=self.end.headers,
            auth=self.end.auth)

    def test_endpoint_get(self):
        url = 'series/'
        self.end.pool.get.return_value = True
        self.end.get(url)
        self.end.pool.get.assert_called_once_with(
            'https://www.nothing.com/v2/series/',
            data='',
            headers=self.end.headers,
            auth=self.end.auth)

    def test_endpoint_put(self):
        url = 'series/'
        body = 'foobar'
        self.end.pool.put.return_value = True
        self.end.put(url, body)
        self.end.pool.put.assert_called_once_with(
            'https://www.nothing.com/v2/series/',
            data=body,
            headers=self.end.headers,
            auth=self.end.auth)

    def test_endpoint_delete(self):
        url = 'series/'
        self.end.pool.delete.return_value = True
        self.end.delete(url)
        self.end.pool.delete.assert_called_once_with(
            'https://www.nothing.com/v2/series/',
            data='',
            headers=self.end.headers,
            auth=self.end.auth)

    def test_endpoint_merges_headers(self):
        url = 'series/'
        new_headers = {'foo': 'bar'}
        self.end.pool.get.return_value = True
        self.end.get(url, headers=new_headers)
        merged = p.merge_headers(self.end.headers, new_headers)
        self.end.pool.get.assert_called_once_with(
            'https://www.nothing.com/v2/series/',
            data='',
            headers=merged,
            auth=self.end.auth)
