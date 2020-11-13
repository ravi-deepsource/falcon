import pytest

from falcon import Response

from _util import skipif_asgi_unsupported  # NOQA


@pytest.fixture(params=[True, False])
def resp_type(request):
    if request.param:
        skipif_asgi_unsupported()
        import falcon.asgi
        return falcon.asgi.Response

    return Response


class TestResponseContext:

    @staticmethod
    def test_default_response_context(resp_type):
        resp = resp_type()

        resp.context.hello = 'World!'
        assert resp.context.hello == 'World!'
        assert resp.context['hello'] == 'World!'

        resp.context['note'] = 'Default Response.context_type used to be dict.'
        assert 'note' in resp.context
        assert hasattr(resp.context, 'note')
        assert resp.context.get('note') == resp.context['note']

    @staticmethod
    def test_custom_response_context(resp_type):

        class MyCustomContextType:
            pass

        class MyCustomResponse(resp_type):
            context_type = MyCustomContextType

        resp = MyCustomResponse()
        assert isinstance(resp.context, MyCustomContextType)

    @staticmethod
    def test_custom_response_context_failure(resp_type):

        class MyCustomResponse(resp_type):
            context_type = False

        with pytest.raises(TypeError):
            MyCustomResponse()

    @staticmethod
    def test_custom_response_context_factory(resp_type):

        def create_context(resp):
            return {'resp': resp}

        class MyCustomResponse(resp_type):
            context_type = create_context

        resp = MyCustomResponse()
        assert isinstance(resp.context, dict)
        assert resp.context['resp'] is resp
