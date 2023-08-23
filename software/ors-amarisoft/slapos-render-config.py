import json

config = "enb"
json_params_empty = """{
    "rf_mode": 'fdd',
    "slap_configuration": {
    },
    "directory": {
    },
    "slapparameter_dict": {
    }
}"""


# 2 cells sharing SDR-based RU consisting of 2 SDR boards (4tx + 4rx ports max)
# RU definition is embedded into cell for simplicity of management
RU1 = {
    'ru_type':      'sdr',
    'ru_link_type': 'sdr',
    'sdr_dev_list': [3, 4],
    'n_antenna_dl': 4,
    'n_antenna_ul': 2,
}

CELL1_a = {
    'cell_type':    'lte',
    'rf_mode':      'tdd',
    'bandwidth':    '5 MHz',
    'dl_earfcn':    38050,      # 2600 MHz
    'pci':          1,
    'cell_id':      "0x01",
    'ru':           RU1,        # RU definition embedded into CELL
}

CELL1_b = {
    'cell_type':    'lte',
    'rf_mode':      'tdd',
    'bandwidth':    '5 MHz',
    'dl_earfcn':    38100,      # 2605 MHz
    'pci':          2,
    'cell_id':      "0x02",
    'ru':           {           # CELL1_b shares RU with CELL1_a referring to it via cell
        'ru_type':      'ruincell_ref',
        'ruincell_ref': 'CELL1_a'
    }
}

# another cell that uses CPRI-based Lopcomm RU
# here we instantiate RU separately since embedding RU into a cell is covered by CELL1_a above
RU2 = {
    'ru_type':      'lopcomm',
    'ru_link_type': 'cpri',
    'mac_addr':     'XXX',
    'cpri_link':    {
        'sdr_dev':  2,
        'sfp_port': 0,
        'mult':     8,
        'mapping':  'bf1',
        'rx_delay': 10,
        'tx_delay': 11,
        'tx_dbm':   50
    }
    'n_antenna_dl': 2,
    'n_antenna_ul': 1,
}

CELL2_1 = {
    'cell_type':    'lte',
    'rf_mode':      'fdd',
    'bandwidth':    '5 MHz',
    'dl_earfcn':    XXX,      # XXX MHz
    'pci':          21,
    'cell_id':      "0x21",
    'ru':           {           # CELL1_b shares RU with CELL1_a referring to it via cell
        'ru_type':      'ruincell_ref',
        'ruincell_ref': 'CELL1_a'
    }
}


# XXX CELL3 TDD LTE
# XXX CELL3 FDD NR
# XXX RU_ref

jCELL1 = json.dumps(CELL1)
jCELL2 = json.dumps(CELL2)
jRU2   = json.dumps(RU2)
json_params = """{
    "earfcn": 126357,
    "tx_gain": 50,
    "rx_gain": 50,
    "sib23_file": "sib",
    "rf_mode": "fdd",
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
        "slave_instance_list": [
            {
                "slave_title":          "Cell 1",
                "slave_reference":      "_CELL1",
                "slap_software_type":   "enb",
                "_": %(jCELL1)s
            },
            {
                "slave_title":          "Cell 2",
                "slave_reference":      "_CELL2",
                "slap_software_type":   "enb",
                "_": %(jCELL2)s
            },
            {
                "slave_title":          "Radio Unit 2",
                "slave_reference":      "_ru2",
                "slap_software_type":   "enb",
                "_": %(jRU2)s
            },
        ],
    }
}""" % globals()
import os
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
        args = None, name, options
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
        #print(self.context)
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
ctx = json.loads(json_params)
ctx.update({'json_module': json})
r._init("recipe", {
  'extensions': 'jinja2.ext.do',
  'url': 'config/{}.jinja2.cfg'.format(config),
  'output': 'config/{}.cfg'.format(config),
  'context': ctx,
  'import-list': 'rawfile lte.jinja2 config/lte.jinja2',
  })
with open('config/{}.cfg'.format(config), 'w+') as f:
  f.write(r._render().decode())
