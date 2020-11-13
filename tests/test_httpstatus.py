# -*- coding: utf-8

import http

import pytest

import falcon
from falcon.http_status import HTTPStatus
import falcon.testing as testing

from _util import create_app  # NOQA


@pytest.fixture(params=[True, False])
def client(request):
    app = create_app(asgi=request.param)
    app.add_route('/status', TestStatusResource())
    return testing.TestClient(app)


@pytest.fixture(params=[True, False])
def hook_test_client(request):
    app = create_app(asgi=request.param)
    app.add_route('/status', TestHookResource())
    return testing.TestClient(app)


def before_hook(req, resp, resource, params):
    raise HTTPStatus(falcon.HTTP_200,
                     headers={'X-Failed': 'False'},
                     body='Pass')


def after_hook(req, resp, resource):
    resp.status = falcon.HTTP_200
    resp.set_header('X-Failed', 'False')
    resp.body = 'Pass'


def noop_after_hook(req, resp, resource):
    pass


class TestStatusResource:

    @falcon.before(before_hook)
    @staticmethod
    def on_get(req, resp):
        resp.status = falcon.HTTP_500
        resp.set_header('X-Failed', 'True')
        resp.body = 'Fail'

    @staticmethod
    def on_post(req, resp):
        resp.status = falcon.HTTP_500
        resp.set_header('X-Failed', 'True')
        resp.body = 'Fail'

        raise HTTPStatus(falcon.HTTP_200,
                         headers={'X-Failed': 'False'},
                         body='Pass')

    @falcon.after(after_hook)
    @staticmethod
    def on_put(req, resp):
        # NOTE(kgriffs): Test that passing a unicode status string
        # works just fine.
        resp.status = '500 Internal Server Error'
        resp.set_header('X-Failed', 'True')
        resp.body = 'Fail'

    @staticmethod
    def on_patch(req, resp):
        raise HTTPStatus(falcon.HTTP_200, body=None)

    @falcon.after(noop_after_hook)
    @staticmethod
    def on_delete(req, resp):
        raise HTTPStatus(falcon.HTTP_200,
                         headers={'X-Failed': 'False'},
                         body='Pass')


class TestHookResource:

    @staticmethod
    def on_get(req, resp):
        resp.status = falcon.HTTP_500
        resp.set_header('X-Failed', 'True')
        resp.body = 'Fail'

    @staticmethod
    def on_patch(req, resp):
        raise HTTPStatus(falcon.HTTP_200,
                         body=None)

    @staticmethod
    def on_delete(req, resp):
        raise HTTPStatus(falcon.HTTP_200,
                         headers={'X-Failed': 'False'},
                         body='Pass')


class TestHTTPStatus:
    @staticmethod
    def test_raise_status_in_before_hook(client):
        """ Make sure we get the 200 raised by before hook """
        response = client.simulate_request(path='/status', method='GET')
        assert response.status == falcon.HTTP_200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    @staticmethod
    def test_raise_status_in_responder(client):
        """ Make sure we get the 200 raised by responder """
        response = client.simulate_request(path='/status', method='POST')
        assert response.status == falcon.HTTP_200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    @staticmethod
    def test_raise_status_runs_after_hooks(client):
        """ Make sure after hooks still run """
        response = client.simulate_request(path='/status', method='PUT')
        assert response.status == falcon.HTTP_200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    @staticmethod
    def test_raise_status_survives_after_hooks(client):
        """ Make sure after hook doesn't overwrite our status """
        response = client.simulate_request(path='/status', method='DELETE')
        assert response.status == falcon.HTTP_200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    @staticmethod
    def test_raise_status_empty_body(client):
        """ Make sure passing None to body results in empty body """
        response = client.simulate_request(path='/status', method='PATCH')
        assert response.text == ''


class TestHTTPStatusWithMiddleware:

    def test_raise_status_in_process_request(self, hook_test_client):
        """ Make sure we can raise status from middleware process request """
        client = hook_test_client

        class TestMiddleware:
            @staticmethod
            def process_request(req, resp):
                raise HTTPStatus(falcon.HTTP_200,
                                 headers={'X-Failed': 'False'},
                                 body='Pass')

            # NOTE(kgriffs): Test the side-by-side support for dual WSGI and
            #   ASGI compatibility.
            async def process_request_async(self, req, resp):
                self.process_request(req, resp)

        client.app.add_middleware(TestMiddleware())

        response = client.simulate_request(path='/status', method='GET')
        assert response.status == falcon.HTTP_200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    def test_raise_status_in_process_resource(self, hook_test_client):
        """ Make sure we can raise status from middleware process resource """
        client = hook_test_client

        class TestMiddleware:
            @staticmethod
            def process_resource(req, resp, resource, params):
                raise HTTPStatus(falcon.HTTP_200,
                                 headers={'X-Failed': 'False'},
                                 body='Pass')

            async def process_resource_async(self, *args):
                self.process_resource(*args)

        # NOTE(kgriffs): Pass a list to test that add_middleware can handle it
        client.app.add_middleware([TestMiddleware()])

        response = client.simulate_request(path='/status', method='GET')
        assert response.status == falcon.HTTP_200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    def test_raise_status_runs_process_response(self, hook_test_client):
        """ Make sure process_response still runs """
        client = hook_test_client

        class TestMiddleware:
            @staticmethod
            def process_response(req, resp, resource, req_succeeded):
                resp.status = falcon.HTTP_200
                resp.set_header('X-Failed', 'False')
                resp.body = 'Pass'

            async def process_response_async(self, *args):
                self.process_response(*args)

        # NOTE(kgriffs): Pass a generic iterable to test that add_middleware
        #   can handle it.
        client.app.add_middleware(iter([TestMiddleware()]))

        response = client.simulate_request(path='/status', method='GET')
        assert response.status == falcon.HTTP_200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'


class NoBodyResource:
    @staticmethod
    def on_get(req, res):
        res.data = b'foo'
        raise HTTPStatus(falcon.HTTP_745)

    @staticmethod
    def on_post(req, res):
        res.media = {'a': 1}
        raise HTTPStatus(falcon.HTTP_725)

    @staticmethod
    def on_put(req, res):
        res.body = 'foo'
        raise HTTPStatus(falcon.HTTP_719)


@pytest.fixture()
def body_client(asgi):
    app = create_app(asgi=asgi)
    app.add_route('/status', NoBodyResource())
    return testing.TestClient(app)


class TestNoBodyWithStatus:
    @staticmethod
    def test_data_is_set(body_client):
        res = body_client.simulate_get('/status')
        assert res.status == falcon.HTTP_745
        assert res.content == b''

    @staticmethod
    def test_media_is_set(body_client):
        res = body_client.simulate_post('/status')
        assert res.status == falcon.HTTP_725
        assert res.content == b''

    @staticmethod
    def test_body_is_set(body_client):
        res = body_client.simulate_put('/status')
        assert res.status == falcon.HTTP_719
        assert res.content == b''


@pytest.fixture()
def custom_status_client(asgi):
    def client(status):
        class Resource:
            @staticmethod
            def on_get(req, resp):
                resp.content_type = falcon.MEDIA_TEXT
                resp.data = b'Hello, World!'
                resp.status = status

        app = create_app(asgi=asgi)
        app.add_route('/status', Resource())
        return testing.TestClient(app)

    return client


@pytest.mark.parametrize('status,expected_code', [
    (http.HTTPStatus(200), 200),
    (http.HTTPStatus(202), 202),
    (http.HTTPStatus(403), 403),
    (http.HTTPStatus(500), 500),
    (http.HTTPStatus.OK, 200),
    (http.HTTPStatus.USE_PROXY, 305),
    (http.HTTPStatus.NOT_FOUND, 404),
    (http.HTTPStatus.NOT_IMPLEMENTED, 501),
    (200, 200),
    (307, 307),
    (500, 500),
    (702, 702),
    (b'200 OK', 200),
    (b'702 Emacs', 702),
])
def test_non_string_status(custom_status_client, status, expected_code):
    client = custom_status_client(status)
    resp = client.simulate_get('/status')
    assert resp.text == 'Hello, World!'
    assert resp.status_code == expected_code
