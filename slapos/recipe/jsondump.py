
from slapos.recipe.librecipe import GenericBaseRecipe

import json
import os

class Recipe(GenericBaseRecipe):

    def install(self):
        parameter_dict = {
            key: value
            for key, value in self.options.items()
            if key not in ['json-output', 'recipe']
        }

        with os.fdopen(os.open(self.options['json-output'], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as fout:
            fout.write(json.dumps(parameter_dict, indent=2, sort_keys=True))

        return [self.options['json-output']]

    update = install

