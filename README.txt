Steward Googlefed
=================
This is a Steward extension for using Google Federated Auth for a web
interface. This extension only supplies the auth, not the rest of the web
interface.

Setup
=====
To use ``steward_googlefed``, just add it to your includes either programmatically::

    config.include('steward_googlefed')

or in the config.ini file::

    pyramid.includes = steward_googlefed

Configuration
=============

Library Settings
----------------
``steward_googlefed`` depends on ``pyramid_beaker`` for session data. See their
docs for more information, but a sample configuration using cookie sessions is
below::

    session.type = cookie
    session.encrypt_key = <key>
    session.validate_key = <key>

``steward_googlefed`` depends on ``velruse`` for logging in with Google. The
only setting that is required is the realm, which is the url that the user will
be coming from when doing the OpenID auth with Google. For example::

    velruse.google.realm = https://myapp.com

Internal Settings
-----------------

* **googlefed.domain** - The domain that is given access to Steward. The auth will ensure that the Google-verified email fits the format <username>@<domain>
* **googlefed.all_admin** - If true, add everyone that logs in via Google to the 'admin' group. Useful for debugging.

Authorization in Steward works by using the standard Pyramid user + group +
permission model. Steward requires you to set up a list of users and what
groups they are a part of. Since the username you set up for Steward may not
match the username you have as your Google email, ``steward_googlefed``
allows you to provide a userid map that converts the Google email addresses to
a different username. The userid map can be inside the config file, or
specified as an external yaml or json file::

    googlefed.user_map = <file>.yaml

The file must end with '.yaml' or '.json'. If no value is provided, the user
map will be generated from the config file. To convert 'steven@highlig.ht' into
the user 'stevearc', add the setting::
    
    googlefed.user.steven = stevearc

You may add as many 'googlefed.user' settings as you wish. If the email
username is not found in the user map, it is left unconverted.

.. note::
    Your Steward web interface should define a route with the name 'root'. If
    it does not, steward_googlefed will just use '/' instead of doing url
    lookup when redirecting users on login/logout.
