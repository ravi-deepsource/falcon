import pytest

import falcon
from falcon import ASGI_SUPPORTED, constants, testing

from _util import create_app, disable_asgi_non_coroutine_wrapping  # NOQA


def capture_error(req, resp, ex, params):
    resp.status = falcon.HTTP_723
    resp.body = 'error: %s' % str(ex)


async def capture_error_async(*args):
    capture_error(*args)


def handle_error_first(req, resp, ex, params):
    resp.status = falcon.HTTP_200
    resp.body = 'first error handler'


class CustomBaseException(Exception):
    pass


class CustomException(CustomBaseException):

    @staticmethod
    def handle(req, resp, ex, params):
        raise falcon.HTTPError(
            falcon.HTTP_792,
            title='Internet crashed!',
            description='Catastrophic weather event',
            href='http://example.com/api/inconvenient-truth',
            href_text='Drill, baby drill!')


class ErroredClassResource:

    @staticmethod
    def on_get(req, resp):
        raise Exception('Plain Exception')

    @staticmethod
    def on_head(req, resp):
        raise CustomBaseException('CustomBaseException')

    @staticmethod
    def on_delete(req, resp):
        raise CustomException('CustomException')


@pytest.fixture
def client(asgi):
    app = create_app(asgi)
    app.add_route('/', ErroredClassResource())
    return testing.TestClient(app)


class TestErrorHandler:

    @staticmethod
    def test_caught_error(client):
        client.app.add_error_handler(Exception, capture_error)

        result = client.simulate_get()
        assert result.text == 'error: Plain Exception'

        result = client.simulate_head()
        assert result.status_code == 723
        assert not result.content

    @pytest.mark.parametrize('get_headers, resp_content_type, resp_start', [
        (None, constants.MEDIA_JSON, '{"'),
        ({'accept': constants.MEDIA_JSON}, constants.MEDIA_JSON, '{"'),
        ({'accept': constants.MEDIA_XML}, constants.MEDIA_XML, '<?xml'),
    ])
    def test_uncaught_python_error(self, client,
                                   get_headers, resp_content_type, resp_start):
        result = client.simulate_get(headers=get_headers)
        assert result.status_code == 500
        assert result.headers['content-type'] == resp_content_type
        assert result.text.startswith(resp_start)

    @staticmethod
    def test_caught_error_async(asgi):
        if not asgi:
            pytest.skip('Test only applies to ASGI')

        if not ASGI_SUPPORTED:
            pytest.skip('ASGI requires Python 3.6+')

        import falcon.asgi
        app = falcon.asgi.App()
        app.add_route('/', ErroredClassResource())
        app.add_error_handler(Exception, capture_error_async)

        client = testing.TestClient(app)

        result = client.simulate_get()
        assert result.text == 'error: Plain Exception'

        result = client.simulate_head()
        assert result.status_code == 723
        assert not result.content

    @staticmethod
    def test_uncaught_error(client):
        client.app._error_handlers.clear()
        client.app.add_error_handler(CustomException, capture_error)
        with pytest.raises(Exception):
            client.simulate_get()

    @staticmethod
    def test_uncaught_error_else(client):
        client.app._error_handlers.clear()
        with pytest.raises(Exception):
            client.simulate_get()

    @staticmethod
    def test_converted_error(client):
        client.app.add_error_handler(CustomException)

        result = client.simulate_delete()
        assert result.status_code == 792
        assert result.json['title'] == 'Internet crashed!'

    @staticmethod
    def test_handle_not_defined(client):
        with pytest.raises(AttributeError):
            client.app.add_error_handler(CustomBaseException)

    @staticmethod
    def test_subclass_error(client):
        client.app.add_error_handler(CustomBaseException, capture_error)

        result = client.simulate_delete()
        assert result.status_code == 723
        assert result.text == 'error: CustomException'

    @staticmethod
    def test_error_precedence_duplicate(client):
        client.app.add_error_handler(Exception, capture_error)
        client.app.add_error_handler(Exception, handle_error_first)

        result = client.simulate_get()
        assert result.text == 'first error handler'

    @staticmethod
    def test_error_precedence_subclass(client):
        client.app.add_error_handler(Exception, capture_error)
        client.app.add_error_handler(CustomException, handle_error_first)

        result = client.simulate_delete()
        assert result.status_code == 200
        assert result.text == 'first error handler'

        result = client.simulate_get()
        assert result.status_code == 723
        assert result.text == 'error: Plain Exception'

    @staticmethod
    def test_error_precedence_subclass_order_indifference(client):
        client.app.add_error_handler(CustomException, handle_error_first)
        client.app.add_error_handler(Exception, capture_error)

        result = client.simulate_delete()
        assert result.status_code == 200
        assert result.text == 'first error handler'

    @pytest.mark.parametrize('exceptions', [
        (Exception, CustomException),
        [Exception, CustomException],
    ])
    def test_handler_multiple_exception_iterable(self, client, exceptions):
        client.app.add_error_handler(exceptions, capture_error)

        result = client.simulate_get()
        assert result.status_code == 723

        result = client.simulate_delete()
        assert result.status_code == 723

    @staticmethod
    def test_handler_single_exception_iterable(client):
        def exception_list_generator():
            yield CustomException

        client.app.add_error_handler(exception_list_generator(), capture_error)

        result = client.simulate_delete()
        assert result.status_code == 723

    @pytest.mark.parametrize('exceptions', [
        NotImplemented,
        'Hello, world!',
        frozenset([ZeroDivisionError, int, NotImplementedError]),
        [float, float],
    ])
    def test_invalid_add_exception_handler_input(self, client, exceptions):
        with pytest.raises(TypeError):
            client.app.add_error_handler(exceptions, capture_error)

    @staticmethod
    def test_handler_signature_shim():
        def check_args(ex, req, resp):
            assert isinstance(ex, BaseException)
            assert isinstance(req, falcon.Request)
            assert isinstance(resp, falcon.Response)

        def legacy_handler1(ex, req, resp, params):
            check_args(ex, req, resp)

        def legacy_handler2(error_obj, request, response, params):
            check_args(error_obj, request, response)

        def legacy_handler3(err, rq, rs, prms):
            check_args(err, rq, rs)

        app = create_app(asgi=False)
        app.add_route('/', ErroredClassResource())
        client = testing.TestClient(app)

        client.app.add_error_handler(Exception, legacy_handler1)
        client.app.add_error_handler(CustomBaseException, legacy_handler2)
        client.app.add_error_handler(CustomException, legacy_handler3)

        client.simulate_delete()
        client.simulate_get()
        client.simulate_head()

    @staticmethod
    def test_handler_must_be_coroutine_for_asgi():
        async def legacy_handler(err, rq, rs, prms):
            pass

        app = create_app(True)

        with disable_asgi_non_coroutine_wrapping():
            with pytest.raises(ValueError):
                app.add_error_handler(Exception, capture_error)

    @staticmethod
    def test_catch_http_no_route_error(asgi):
        class Resource:
            @staticmethod
            def on_get(req, resp):
                raise falcon.HTTPNotFound()

        def capture_error(req, resp, ex, params):
            resp.set_header('X-name', ex.__class__.__name__)
            raise ex

        app = create_app(asgi)
        app.add_route('/', Resource())
        app.add_error_handler(falcon.HTTPError, capture_error)

        client = testing.TestClient(app)

        result = client.simulate_get('/')
        assert result.status_code == 404
        assert result.headers['X-name'] == 'HTTPNotFound'

        result = client.simulate_get('/404')
        assert result.status_code == 404
        assert result.headers['X-name'] == 'HTTPRouteNotFound'


class NoBodyResource:
    @staticmethod
    def on_get(req, res):
        res.data = b'foo'
        raise falcon.HTTPError(falcon.HTTP_IM_A_TEAPOT)

    @staticmethod
    def on_post(req, res):
        res.media = {'a': 1}
        raise falcon.HTTPError(falcon.HTTP_740)

    @staticmethod
    def on_put(req, res):
        res.body = 'foo'
        raise falcon.HTTPError(falcon.HTTP_701)


class TestNoBodyWithStatus:
    @pytest.fixture()
    @staticmethod
    def body_client(asgi):
        app = create_app(asgi=asgi)
        app.add_route('/error', NoBodyResource())

        def no_reps(req, resp, exception):
            pass

        app.set_error_serializer(no_reps)
        return testing.TestClient(app)

    @staticmethod
    def test_data_is_set(body_client):
        res = body_client.simulate_get('/error')
        assert res.status == falcon.HTTP_IM_A_TEAPOT
        assert res.content == b''

    @staticmethod
    def test_media_is_set(body_client):
        res = body_client.simulate_post('/error')
        assert res.status == falcon.HTTP_740
        assert res.content == b''

    @staticmethod
    def test_body_is_set(body_client):
        res = body_client.simulate_put('/error')
        assert res.status == falcon.HTTP_701
        assert res.content == b''


class CustomErrorResource:
    @staticmethod
    def on_get(req, res):
        res.data = b'foo'
        raise ZeroDivisionError()

    @staticmethod
    def on_post(req, res):
        res.media = {'a': 1}
        raise ZeroDivisionError()

    @staticmethod
    def on_put(req, res):
        res.body = 'foo'
        raise ZeroDivisionError()


class TestCustomError:
    @pytest.fixture()
    @staticmethod
    def body_client(asgi):
        app = create_app(asgi=asgi)
        app.add_route('/error', CustomErrorResource())

        if asgi:
            async def handle_zero_division(req, resp, ex, params):
                assert await resp.render_body() is None
                resp.status = falcon.HTTP_719
        else:
            def handle_zero_division(req, resp, ex, params):
                assert resp.render_body() is None
                resp.status = falcon.HTTP_719

        app.add_error_handler(ZeroDivisionError, handle_zero_division)
        return testing.TestClient(app)

    @staticmethod
    def test_data_is_set(body_client):
        res = body_client.simulate_get('/error')
        assert res.status == falcon.HTTP_719
        assert res.content == b''

    @staticmethod
    def test_media_is_set(body_client):
        res = body_client.simulate_post('/error')
        assert res.status == falcon.HTTP_719
        assert res.content == b''

    @staticmethod
    def test_body_is_set(body_client):
        res = body_client.simulate_put('/error')
        assert res.status == falcon.HTTP_719
        assert res.content == b''
