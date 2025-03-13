import functools

import sentry_sdk
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.csrf import CookieCSRFStoragePolicy
from pyramid.path import DottedNameResolver
from pyramid.session import SignedCookieSessionFactory
from sentry_sdk.integrations.pyramid import PyramidIntegration
from tet.config import create_configurator
from tet.util.path import caller_package

__version__ = "0.1.6"


FEATURES_SETTINGS = {
    "auth": [
        "tetkit.authentication_callback",
    ],
    "db": [
        "tetkit.db_models_path",
    ],
    "cookies": [
        "cookies.name",
        "cookies.auth_secret",
        "cookies.secret",
    ],
    "jwt": [
        "jwt.secret",
    ],
}


def application(factory_function=None, features=[]):
    package = caller_package()

    tet_features = [
        "services",
        "i18n",
        "renderers.json",
    ]

    if "tonnikala" in features:
        tet_features += [
            "renderers.tonnikala",
            "renderers.tonnikala.i18n",
            "security.csrf",
        ]

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*a, **kw):
            if len(a) > 1:
                raise ValueError(
                    "application_factory wrapped function "
                    "called with more than 1 positional argument"
                )

            global_config = a[0] if a else None
            settings = kw
            config = create_configurator(
                global_config=global_config,
                settings=settings,
                included_features=tet_features,
                excluded_features=[],
                package=package,
                # **extra_parameters
            )

            _setup_tetkit(config, features)

            returned = func(config)
            if isinstance(returned, Configurator):
                config = returned

            return config.make_wsgi_app()

        return wrapper

    if factory_function is not None:
        return decorator(factory_function)
    else:
        return decorator


def _setup_tetkit(config, features=[]):
    settings = config.get_settings()
    _validate_features(features, settings)
    resolver = DottedNameResolver()

    if settings.get("sentry.dsn"):
        sentry_sdk.init(
            dsn=settings["sentry.dsn"],
            integrations=[PyramidIntegration()],
            environment=settings["sentry.environment"],
        )

    if "db" in features:
        config.include("tetkit.db")

    if "auth" in features:
        config.set_authorization_policy(ACLAuthorizationPolicy())
        config.set_root_factory(settings["tetkit.root_factory"])

        authn_callback = resolver.resolve(settings["tetkit.authentication_callback"])

    if "cookies" in features:
        config.set_authentication_policy(
            AuthTktAuthenticationPolicy(
                secret=settings["cookies.auth_secret"],
                cookie_name=settings["cookies.name"],
                callback=authn_callback,
                reissue_time=24 * 60 * 60 / 10,  # 24/10 hours
                timeout=24 * 60 * 60,  # 24 hours
            )
        )
        config.set_session_factory(
            SignedCookieSessionFactory(
                secret=settings["cookies.secret"],
            )
        )
        config.set_csrf_storage_policy(CookieCSRFStoragePolicy())

    if "jwt" in features:
        config.include("pyramid_jwt")
        config.set_jwt_authentication_policy(
            settings["jwt.secret"],
            auth_type="Bearer",
            callback=authn_callback,
            # expiration=60 * 60 * 24,  # 1 day
        )

    if "cors" in features:
        config.include("tetkit.security.cors")
        config.add_cors_preflight_handler()


def _validate_features(features: list, settings: dict) -> None:
    if "auth" in features and "cookies" not in features and "jwt" not in features:
        raise Exception(
            "Need to have at least cookies or jwt feature when there is auth"
        )

    for feature in features:
        for s in FEATURES_SETTINGS.get(feature, []):
            if not settings.get(s):
                raise Exception(f"Missing setting {s}")
