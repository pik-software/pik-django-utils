from django.http import HttpRequest
from django_restql.mixins import RequestQueryParserMixin
from django_restql.settings import restql_settings


class DefaultRequestQueryParserMixin(RequestQueryParserMixin):
    """ Provides class defined default RestQL query support """

    default_restql_query = None

    @classmethod
    def has_restql_query_param(cls, request):
        return bool(
            hasattr(request, 'parsed_restql_query')
            or bool(cls.default_restql_query)
            or super().has_restql_query_param(request))

    @classmethod
    def get_parsed_restql_query_from_req(cls, request):
        if not request:
            request = HttpRequest()
        got_query = restql_settings.QUERY_PARAM_NAME in request.GET
        if not got_query and cls.default_restql_query:
            request.parsed_restql_query = cls.default_restql_query
        return super().get_parsed_restql_query_from_req(request)
