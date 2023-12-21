import logging

class UserLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user if request.user.is_authenticated else 'Anonymous'
        logging_context = {'user': user}
        logger = logging.getLogger(__name__)
        logger = logging.LoggerAdapter(logger, logging_context)

        response = self.get_response(request)
        return response
