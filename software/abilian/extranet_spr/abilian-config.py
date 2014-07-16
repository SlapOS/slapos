#!/usr/bin/env python


def load_config():
    import json
    import os

    # python scripts

    for filepath in os.environ.get('ABILIAN_CONFIG_EXTRA_PYTHON', '').split(':'):
        execfile(filepath)

    # json parameters

    for filepath in os.environ.get('ABILIAN_CONFIG_EXTRA_JSON', '').split(':'):
        with open(filepath) as fin:
            for key, value in json.load(fin).items():
                globals()[key] = value

    # convert unicode->str if required

    for key, value in globals().items():
        if key in ['SECRET_KEY']:
            globals()[key] = str(value)

    # interpolate password and host provided by separate files

    try:
        globals()['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI % {
                'password': SQLALCHEMY_DATABASE_PASSWORD,
                'ipv4': POSTGRES_IPV4
                }
    except NameError:
        raise NameError("The configuration is not complete yet")


load_config()
del load_config

