import pytest

import falcon
import falcon.testing as testing

from _util import create_app  # NOQA


@pytest.fixture
def client(asgi):
    app = create_app(asgi)

    resource = RedirectingResource()
    app.add_route('/', resource)

    return testing.TestClient(app)


@pytest.fixture
def client_exercising_headers(asgi):
    app = create_app(asgi)

    resource = RedirectingResourceWithHeaders()
    app.add_route('/', resource)

    return testing.TestClient(app)


class RedirectingResource:
    # NOTE(kgriffs): You wouldn't necessarily use these types of
    # http methods with these types of redirects; this is only
    # done to simplify testing.

    @staticmethod
    def on_get(req, resp):
        raise falcon.HTTPMovedPermanently('/moved/perm')

    @staticmethod
    def on_post(req, resp):
        raise falcon.HTTPFound('/found')

    @staticmethod
    def on_put(req, resp):
        raise falcon.HTTPSeeOther('/see/other')

    @staticmethod
    def on_delete(req, resp):
        raise falcon.HTTPTemporaryRedirect('/tmp/redirect')

    @staticmethod
    def on_head(req, resp):
        raise falcon.HTTPPermanentRedirect('/perm/redirect')


class RedirectingResourceWithHeaders:
    # NOTE(kgriffs): You wouldn't necessarily use these types of
    # http methods with these types of redirects; this is only
    # done to simplify testing.

    @staticmethod
    def on_get(req, resp):
        raise falcon.HTTPMovedPermanently('/moved/perm', headers={'foo': 'bar'})

    @staticmethod
    def on_post(req, resp):
        raise falcon.HTTPFound('/found', headers={'foo': 'bar'})

    @staticmethod
    def on_put(req, resp):
        raise falcon.HTTPSeeOther('/see/other', headers={'foo': 'bar'})

    @staticmethod
    def on_delete(req, resp):
        raise falcon.HTTPTemporaryRedirect('/tmp/redirect', headers={'foo': 'bar'})

    @staticmethod
    def on_head(req, resp):
        raise falcon.HTTPPermanentRedirect('/perm/redirect', headers={'foo': 'bar'})


class TestRedirects:
    @pytest.mark.parametrize('method,expected_status,expected_location', [
        ('GET', falcon.HTTP_301, '/moved/perm'),
        ('POST', falcon.HTTP_302, '/found'),
        ('PUT', falcon.HTTP_303, '/see/other'),
        ('DELETE', falcon.HTTP_307, '/tmp/redirect'),
        ('HEAD', falcon.HTTP_308, '/perm/redirect'),
    ])
    def test_redirect(self, client, method, expected_status, expected_location):
        result = client.simulate_request(path='/', method=method)

        assert not result.content
        assert result.status == expected_status
        assert result.headers['location'] == expected_location

    @pytest.mark.parametrize('method,expected_status,expected_location', [
        ('GET', falcon.HTTP_301, '/moved/perm'),
        ('POST', falcon.HTTP_302, '/found'),
        ('PUT', falcon.HTTP_303, '/see/other'),
        ('DELETE', falcon.HTTP_307, '/tmp/redirect'),
        ('HEAD', falcon.HTTP_308, '/perm/redirect'),
    ])
    def test_redirect_with_headers(self, client_exercising_headers, method,
                                   expected_status, expected_location):
        result = client_exercising_headers.simulate_request(path='/', method=method)

        assert not result.content
        assert result.status == expected_status
        assert result.headers['location'] == expected_location
        assert result.headers['foo'] == 'bar'
