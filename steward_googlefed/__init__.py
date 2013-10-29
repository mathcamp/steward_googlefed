""" Steward extension for using Google federated auth for webpages """
import logging
from pyramid.security import (Everyone, Authenticated, forget, Allow,
                              NO_PERMISSION_REQUIRED, ALL_PERMISSIONS)
import velruse
from pyramid_beaker import session_factory_from_settings
from pyramid.httpexceptions import HTTPFound, HTTPForbidden
from pyramid.view import view_config
from pyramid.settings import asbool

LOG = logging.getLogger(__name__)

def _get_app_root(request):
    """ Get the root url of the app """
    try:
        return request.route_url('root')
    except KeyError:
        LOG.warn("Steward has no 'root' route_name. Using '/' instead")
        return '/'

class GoogleAuthPolicy(object):
    """ Simple auth policy using google's openid """
    def __init__(self, userid_map):
        self.userid_map = userid_map

    def authenticated_userid(self, request):
        """ Return the authenticated userid or ``None`` if no
        authenticated userid can be found. This method of the policy
        should ensure that a record exists in whatever persistent store is
        used related to the user (the user should not have been deleted);
        if a record associated with the current id does not exist in a
        persistent store, it should return ``None``."""
        username = request.session.get('username')
        return self.userid_map.get(username, username)

    def unauthenticated_userid(self, request):
        """ Return the *unauthenticated* userid.  This method performs the
        same duty as ``authenticated_userid`` but is permitted to return the
        userid based only on data present in the request; it needn't (and
        shouldn't) check any persistent store to ensure that the user record
        related to the request userid exists."""
        username = request.session.get('username')
        return self.userid_map.get(username, username)

    def effective_principals(self, request):
        """ Return a sequence representing the effective principals
        including the userid and any groups belonged to by the current
        user, including 'system' groups such as
        ``pyramid.security.Everyone`` and
        ``pyramid.security.Authenticated``. """
        perms = [Everyone]
        username = request.session.get('username')
        if username:
            userid = self.unauthenticated_userid(request)
            perms.append(Authenticated)
            perms.append(userid)
            settings = request.registry.settings
            if asbool(settings.get('googlefed.all_admin')):
                perms.append('admin')
            else:
                return request.registry.auth_db.groups(userid, request)
        return perms

    def remember(self, request, principal, **kw):
        """ Return a set of headers suitable for 'remembering' the
        principal named ``principal`` when set in a response.  An
        individual authentication policy and its consumers can decide
        on the composition and meaning of **kw. """
        return []

    def forget(self, request):
        """ Return a set of headers suitable for 'forgetting' the
        current user on subsequent requests. """
        return []

@view_config(route_name='login', permission=NO_PERMISSION_REQUIRED)
@view_config(context=HTTPForbidden, permission=NO_PERMISSION_REQUIRED)
def do_login(request):
    """ Store the redirect in the session and log in with google """
    login_url = request.route_url('login')
    if request.url != login_url:
        request.session['next'] = request.url
    elif 'next' in request.GET:
        request.session['next'] = request.GET['next']
    else:
        request.session['next'] = _get_app_root(request)
    return HTTPFound(location=velruse.login_url(request, 'google'))

@view_config(route_name='logout')
def do_logout(request):
    """ Log the user out """
    request.session.delete()
    raise HTTPFound(location=_get_app_root(request), headers=forget(request))

@view_config(context='velruse.AuthenticationComplete')
def on_login(request):
    """ Called when a user successfully logs in """
    context = request.context
    email_addr = context.profile['verifiedEmail']
    email, domain = email_addr.split('@')
    my_domain = request.registry.settings.get('googlefed.domain')
    if domain == my_domain:
        request.session['username'] = email
    else:
        LOG.warning("Email '%s' does not match '%s'!", email_addr, my_domain)

    next_url = request.session.pop('next', _get_app_root(request))
    raise HTTPFound(location=next_url)

@view_config(context='velruse.AuthenticationDenied')
def on_login_denied(request):
    """ Called when the login is denied """
    raise HTTPFound(location=_get_app_root(request))

def includeme(config):
    """ Configure the app """
    settings = config.get_settings()

    velruse.AuthenticationComplete.__acl__ = \
            velruse.AuthenticationDenied.__acl__ = [
        (Allow, Everyone, ALL_PERMISSIONS),
    ]

    map_source = settings.get('googlefed.user_map')
    if map_source is None:
        prefix = 'googlefed.user.'
        userid_map = {}
        for key, val in settings.iteritems():
            if key.startswith(prefix):
                userid_map[key[len(prefix):]] = val
    elif map_source.endswith('.yaml'):
        import yaml
        with open(map_source, 'r') as infile:
            userid_map = yaml.load(infile)
    elif map_source.endswith('.json'):
        import json
        with open(map_source, 'r') as infile:
            userid_map = json.load(infile)
    else:
        raise ValueError("Unrecognized user_map format '%s'" % map_source)

    config.add_authentication_policy(GoogleAuthPolicy(userid_map))
    config.set_session_factory(session_factory_from_settings(settings))

    config.include('velruse.providers.google_hybrid')
    config.add_google_hybrid_login(attrs=['email'],
                                   realm=settings['velruse.google.realm'])

    config.scan()
