import pytest

import falcon.testing as testing


class TestSlots:

    @staticmethod
    def test_slots_request(asgi):
        req = testing.create_asgi_req() if asgi else testing.create_req()

        try:
            req.doesnt = 'exist'
        except AttributeError:
            pytest.fail('Unable to add additional variables dynamically')

    @staticmethod
    def test_slots_response(asgi):
        if asgi:
            import falcon.asgi
            resp = falcon.asgi.Response()
        else:
            import falcon
            resp = falcon.Response()

        try:
            resp.doesnt = 'exist'
        except AttributeError:
            pytest.fail('Unable to add additional variables dynamically')
