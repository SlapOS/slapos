config = "gnb"
json_params_empty = """{
    "rf_mode": 'fdd',
    "slap_configuration": {
    },
    "directory": {
    },
    "slapparameter_dict": {
    }
}"""
json_params = """{
    "rf_mode": "tdd",
    "trx": "sdr",
    "bbu": "ors",
    "ru": "ors",
    "one_watt": "True",
    "earfcn": 646666,
    "nr_arfcn": 646666,
    "nr_band": 43,
    "tx_gain": 62,
    "rx_gain": 43,
    "sib23_file": "sib",
    "slap_configuration": {
        "tap-name": "slaptap9",
        "configuration.default_lte_bandwidth": "10 MHz",
        "configuration.default_lte_imsi": "001010123456789",
        "configuration.default_lte_k": "00112233445566778899aabbccddeeff",
        "configuration.default_lte_inactivity_timer": 10000,
        "configuration.default_nr_bandwidth": 40,
        "configuration.default_nr_imsi": "001010123456789",
        "configuration.default_nr_k": "00112233445566778899aabbccddeeff",
        "configuration.default_nr_ssb_pos_bitmap": "10000000",
        "configuration.default_n_antenna_dl": 2,
        "configuration.default_n_antenna_ul": 2,
        "configuration.default_nr_inactivity_timer": 10000
    },
    "directory": {
        "log": "log",
        "etc": "etc",
        "var": "var"
    },
    "slapparameter_dict": {
        "tdd_ul_dl_config": "5ms 8UL 1DL 2/10 (maximum uplink)"
    }
}"""
import os
import json
from jinja2 import Environment, StrictUndefined, \
    BaseLoader, TemplateNotFound, PrefixLoader
import six

DEFAULT_CONTEXT = {x.__name__: x for x in (
    abs, all, any, bin, bool, bytes, callable, chr, complex, dict, divmod,
    enumerate, filter, float, format, frozenset, hex, int,
    isinstance, iter, len, list, map, max, min, next, oct, ord, pow,
    range, repr, reversed, round, set, six, sorted, str, sum, tuple, zip)}

if six.PY2:
    import itertools
    DEFAULT_CONTEXT.update(
        filter=itertools.ifilter,
        map=itertools.imap,
        range=xrange,
        zip=itertools.izip,
    )

def _assert(x, *args):
    if x:
        return ""
    raise AssertionError(*args)
DEFAULT_CONTEXT['assert'] = _assert

DUMPS_KEY = 'dumps'
DEFAULT_IMPORT_DELIMITER = '/'

def getKey(expression, buildout, _, options):
    section, entry = expression.split(':')
    if section:
        return buildout[section][entry]
    else:
        return options[entry]

def getJsonKey(expression, buildout, _, __):
    return json.loads(getKey(expression, buildout, _, __))

EXPRESSION_HANDLER = {
    'raw': (lambda expression, _, __, ___: expression),
    'key': getKey,
    'json': (lambda expression, _, __, ___: json.loads(expression)),
    'jsonkey': getJsonKey,
    'import': (lambda expression, _, __, ___:
        __import__(expression, fromlist=['*'], level=0)),
    'section': (lambda expression, buildout, _, __: dict(
        buildout[expression])),
}

class RelaxedPrefixLoader(PrefixLoader):
    """
    Same as PrefixLoader, but accepts imports lacking separator.
    """
    def get_loader(self, template):
        if self.delimiter not in template:
            template += self.delimiter
        return super(RelaxedPrefixLoader, self).get_loader(template)

class RecipeBaseLoader(BaseLoader):
    """
    Base class for import classes altering import path.
    """
    def __init__(self, path, delimiter, encoding):
        self.base = os.path.normpath(path)
        self.delimiter = delimiter
        self.encoding = encoding

    def get_source(self, environment, template):
        path = self._getPath(template)
        # Code adapted from jinja2's doc on BaseLoader.
        if path is None or not os.path.exists(path):
            raise TemplateNotFound(template)
        mtime = os.path.getmtime(path)
        with open(path, 'rb') as f:
            source = f.read().decode(self.encoding)
        return source, path, lambda: mtime == os.path.getmtime(path)

    def _getPath(self, template):
        raise NotImplementedError

class FileLoader(RecipeBaseLoader):
    """
    Single-path loader.
    """
    def _getPath(self, template):
        if template:
            return None
        return self.base

class FolderLoader(RecipeBaseLoader):
    """
    Multi-path loader (to allow importing a folder's content).
    """
    def _getPath(self, template):
        path = os.path.normpath(os.path.join(
            self.base,
            *template.split(self.delimiter)
        ))
        if path.startswith(self.base):
            return path
        return None

LOADER_TYPE_DICT = {
    'rawfile': (FileLoader, EXPRESSION_HANDLER['raw']),
    'file': (FileLoader, getKey),
    'rawfolder': (FolderLoader, EXPRESSION_HANDLER['raw']),
    'folder': (FolderLoader, getKey),
}

compiled_source_cache = {}
class Recipe():

    def _init(self, name, options):
        self.once = options.get('once')
        self.encoding = options.get('encoding', 'utf-8')
        self._update = True
        import_delimiter = options.get('import-delimiter',
            DEFAULT_IMPORT_DELIMITER)
        import_dict = {}
        for line in options.get('import-list', '').splitlines(False):
            if not line:
                continue
            expression_type, alias, expression = line.split(None, 2)
            if alias in import_dict:
                raise ValueError('Duplicate import-list entry %r' % alias)
            loader_type, expression_handler = LOADER_TYPE_DICT[
                expression_type]
            import_dict[alias] = loader_type(
                expression_handler(expression, *args),
                import_delimiter, self.encoding,
            )
        if import_dict:
            loader = RelaxedPrefixLoader(import_dict,
                delimiter=import_delimiter)
        else:
            loader = None
        self.template = options['url']
        extension_list = [x for x in (y.strip()
            for y in options.get('extensions', '').split()) if x]
        self.context = options['context']
        self.context.update(DEFAULT_CONTEXT.copy())
        self.env = Environment(
            extensions=extension_list,
            undefined=StrictUndefined,
            loader=loader)

    def _render(self):
        env = self.env
        template = self.template
        with open(template, 'rb') as f:
          source = f.read().decode(self.encoding)
        compiled_source_cache[template] = compiled_source = \
            env.compile(source, filename=template)

        template_object = env.template_class.from_code(env,
            compiled_source,
            env.make_globals(None), None)
        print(self.context)
        return template_object.render(**self.context).encode(self.encoding)

    def install(self):
        once = self.once
        if once and os.path.exists(once):
            return
        installed = super(Recipe, self).install()
        if once:
            open(once, 'ab').close()
            return
        return installed

    def update(self):
        if self._update:
            self.install()
        else:
            super(Recipe, self).update()

r = Recipe()
r._init("recipe", {
  'extensions': 'jinja2.ext.do',
  'url': 'config/{}.jinja2.cfg'.format(config),
  'output': 'config/{}.cfg'.format(config),
  'context': json.loads(json_params),
  })
with open('config/{}.cfg'.format(config), 'w+') as f:
  f.write(r._render().decode())
