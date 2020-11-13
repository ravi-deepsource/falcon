import re

import pytest

import falcon
import falcon.testing as testing

from _util import create_app  # NOQA


class Proxy:
    @staticmethod
    def forward(req):
        return falcon.HTTP_503


class Sink:
    def __init__(self):
        self._proxy = Proxy()

    def __call__(self, req, resp, **kwargs):
        resp.status = self._proxy.forward(req)
        self.kwargs = kwargs


class SinkAsync(Sink):
    async def __call__(self, req, resp, **kwargs):
        super().__call__(req, resp, **kwargs)


class BookCollection(testing.SimpleTestResource):
    pass


@pytest.fixture
def resource():
    return BookCollection()


@pytest.fixture
def sink(asgi):
    return SinkAsync() if asgi else Sink()


@pytest.fixture
def client(asgi):
    app = create_app(asgi)
    return testing.TestClient(app)


class TestDefaultRouting:

    @staticmethod
    def test_single_default_pattern(client, sink, resource):
        client.app.add_sink(sink)

        response = client.simulate_request(path='/')
        assert response.status == falcon.HTTP_503

    @staticmethod
    def test_single_simple_pattern(client, sink, resource):
        client.app.add_sink(sink, r'/foo')

        response = client.simulate_request(path='/foo/bar')
        assert response.status == falcon.HTTP_503

    @staticmethod
    def test_single_compiled_pattern(client, sink, resource):
        client.app.add_sink(sink, re.compile(r'/foo'))

        response = client.simulate_request(path='/foo/bar')
        assert response.status == falcon.HTTP_503

        response = client.simulate_request(path='/auth')
        assert response.status == falcon.HTTP_404

    @staticmethod
    def test_named_groups(client, sink, resource):
        client.app.add_sink(sink, r'/user/(?P<id>\d+)')

        response = client.simulate_request(path='/user/309')
        assert response.status == falcon.HTTP_503
        assert sink.kwargs['id'] == '309'

        response = client.simulate_request(path='/user/sally')
        assert response.status == falcon.HTTP_404

    @staticmethod
    def test_multiple_patterns(asgi, client, sink, resource):
        if asgi:
            async def sink_too(req, resp):
                resp.status = falcon.HTTP_781
        else:
            def sink_too(req, resp):
                resp.status = falcon.HTTP_781

        client.app.add_sink(sink, r'/foo')
        client.app.add_sink(sink_too, r'/foo')  # Last duplicate wins

        client.app.add_sink(sink, r'/katza')

        response = client.simulate_request(path='/foo/bar')
        assert response.status == falcon.HTTP_781

        response = client.simulate_request(path='/katza')
        assert response.status == falcon.HTTP_503

    @staticmethod
    def test_with_route(client, sink, resource):
        client.app.add_route('/books', resource)
        client.app.add_sink(sink, '/proxy')

        response = client.simulate_request(path='/proxy/books')
        assert not resource.called
        assert response.status == falcon.HTTP_503

        response = client.simulate_request(path='/books')
        assert resource.called
        assert response.status == falcon.HTTP_200

    @staticmethod
    def test_route_precedence(client, sink, resource):
        # NOTE(kgriffs): In case of collision, the route takes precedence.
        client.app.add_route('/books', resource)
        client.app.add_sink(sink, '/books')

        response = client.simulate_request(path='/books')
        assert resource.called
        assert response.status == falcon.HTTP_200

    @staticmethod
    def test_route_precedence_with_id(client, sink, resource):
        # NOTE(kgriffs): In case of collision, the route takes precedence.
        client.app.add_route('/books/{id}', resource)
        client.app.add_sink(sink, '/books')

        response = client.simulate_request(path='/books')
        assert not resource.called
        assert response.status == falcon.HTTP_503

    @staticmethod
    def test_route_precedence_with_both_id(client, sink, resource):
        # NOTE(kgriffs): In case of collision, the route takes precedence.
        client.app.add_route('/books/{id}', resource)
        client.app.add_sink(sink, r'/books/\d+')

        response = client.simulate_request(path='/books/123')
        assert resource.called
        assert response.status == falcon.HTTP_200
