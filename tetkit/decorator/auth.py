import functools

from pyramid.httpexceptions import HTTPFound


def login_required(view):
    @functools.wraps(view)
    def wrapped(context, request):
        if not request.user:
            return HTTPFound(request.route_url('login'))
        return view(context, request)

    return wrapped
