
import json
import os

class Recipe(object):
    def __init__(self, buildout, name, options):
        parameter_dict = {
            key: value
            for key, value in options.items()
            if key not in ['json-output', 'recipe']
        }

        with os.fdopen(os.open(options['json-output'], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as fout:
            fout.write(json.dumps(parameter_dict, indent=2, sort_keys=True))
            fout.close()

    def install(self):
        return []

