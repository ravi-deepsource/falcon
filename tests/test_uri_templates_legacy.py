import pytest

import falcon
from falcon import routing


class TestUriTemplates:

    @pytest.mark.parametrize('value', (42, falcon.App))
    @staticmethod
    def test_string_type_required(value):
        with pytest.raises(TypeError):
            routing.compile_uri_template(value)

    @pytest.mark.parametrize('value', ('this', 'this/that'))
    @staticmethod
    def test_template_must_start_with_slash(value):
        with pytest.raises(ValueError):
            routing.compile_uri_template(value)

    @pytest.mark.parametrize('value', ('//', 'a//', '//b', 'a//b', 'a/b//', 'a/b//c'))
    @staticmethod
    def test_template_may_not_contain_double_slash(value):
        with pytest.raises(ValueError):
            routing.compile_uri_template(value)

    @staticmethod
    def test_root():
        fields, pattern = routing.compile_uri_template('/')
        assert not fields
        assert not pattern.match('/x')

        result = pattern.match('/')
        assert result
        assert not result.groupdict()

    @pytest.mark.parametrize('path', ('/hello', '/hello/world', '/hi/there/how/are/you'))
    @staticmethod
    def test_no_fields(path):
        fields, pattern = routing.compile_uri_template(path)
        assert not fields
        assert not pattern.match(path[:-1])

        result = pattern.match(path)
        assert result
        assert not result.groupdict()

    @staticmethod
    def test_one_field():
        fields, pattern = routing.compile_uri_template('/{name}')
        assert fields == {'name'}

        result = pattern.match('/Kelsier')
        assert result
        assert result.groupdict() == {'name': 'Kelsier'}

        fields, pattern = routing.compile_uri_template('/character/{name}')
        assert fields == {'name'}

        result = pattern.match('/character/Kelsier')
        assert result
        assert result.groupdict() == {'name': 'Kelsier'}

        fields, pattern = routing.compile_uri_template('/character/{name}/profile')
        assert fields == {'name'}

        assert not pattern.match('/character')
        assert not pattern.match('/character/Kelsier')
        assert not pattern.match('/character/Kelsier/')

        result = pattern.match('/character/Kelsier/profile')
        assert result
        assert result.groupdict() == {'name': 'Kelsier'}

    @staticmethod
    def test_one_field_with_digits():
        fields, pattern = routing.compile_uri_template('/{name123}')
        assert fields == {'name123'}

        result = pattern.match('/Kelsier')
        assert result
        assert result.groupdict() == {'name123': 'Kelsier'}

    @staticmethod
    def test_one_field_with_prefixed_digits():
        fields, pattern = routing.compile_uri_template('/{37signals}')
        assert fields == set()

        result = pattern.match('/s2n')
        assert not result

    @pytest.mark.parametrize('postfix', ('', '/'))
    @staticmethod
    def test_two_fields(postfix):
        path = '/book/{book_id}/characters/{n4m3}' + postfix
        fields, pattern = routing.compile_uri_template(path)
        assert fields == {'n4m3', 'book_id'}

        result = pattern.match('/book/0765350386/characters/Vin')
        assert result
        assert result.groupdict() == {'n4m3': 'Vin', 'book_id': '0765350386'}

    @staticmethod
    def test_three_fields():
        fields, pattern = routing.compile_uri_template('/{a}/{b}/x/{c}')
        assert fields == set('abc')

        result = pattern.match('/one/2/x/3')
        assert result
        assert result.groupdict() == {'a': 'one', 'b': '2', 'c': '3'}

    @staticmethod
    def test_malformed_field():
        fields, pattern = routing.compile_uri_template('/{a}/{1b}/x/{c}')
        assert fields == set('ac')

        result = pattern.match('/one/{1b}/x/3')
        assert result
        assert result.groupdict() == {'a': 'one', 'c': '3'}
