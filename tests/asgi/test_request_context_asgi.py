import pytest

from falcon.asgi import Request
import falcon.testing as testing


class TestRequestContext:

    @staticmethod
    def test_default_request_context():
        req = testing.create_asgi_req()

        req.context.hello = 'World'
        assert req.context.hello == 'World'
        assert req.context['hello'] == 'World'

        req.context['note'] = 'Default Request.context_type used to be dict.'
        assert 'note' in req.context
        assert hasattr(req.context, 'note')
        assert req.context.get('note') == req.context['note']

    @staticmethod
    def test_custom_request_context():

        # Define a Request-alike with a custom context type
        class MyCustomContextType():
            pass

        class MyCustomRequest(Request):
            context_type = MyCustomContextType

        req = testing.create_asgi_req(req_type=MyCustomRequest)
        assert isinstance(req.context, MyCustomContextType)

    @staticmethod
    def test_custom_request_context_failure():

        # Define a Request-alike with a non-callable custom context type
        class MyCustomRequest(Request):
            context_type = False

        with pytest.raises(TypeError):
            testing.create_asgi_req(req_type=MyCustomRequest)

    @staticmethod
    def test_custom_request_context_request_access():

        def create_context(req):
            return {'uri': req.uri}

        # Define a Request-alike with a custom context type
        class MyCustomRequest(Request):
            context_type = create_context

        req = testing.create_asgi_req(req_type=MyCustomRequest)
        assert isinstance(req.context, dict)
        assert req.context['uri'] == req.uri
