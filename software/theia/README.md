# Theia software release

Theia is a cloud (and desktop) IDE https://www.theia-ide.org

This version comes pre-configured with a few plugins, but does not come with python plugin, to let
you choose between theia and vscode one.

## Installing vscode extensions

To install vscode's python plugin ( https://code.visualstudio.com/docs/languages/python ):

<key>F1</key> `Deploy plugin by id` and enter `vscode:extension/ms-python.python` and wait for a while.
Check theia's log files in case of issues.

see https://github.com/theia-ide/theia/wiki/Testing-VS-Code-extensions for more details.

## jedi

[jedi](https://github.com/davidhalter/jedi) which is used by both thiea and vscode python plugins has
some support for `zc.buildout`. It looks up for a `buildout.cfg` file and if found will load all scripts
from the bin directory from this buildout to add eggs to sys.path. In webrunner we have almost 100 scripts
in bin directory, with maybe 30 eggs in each scripts, so this makes jedi so slow it's unusable. Also, if
an error occurs parsing these scripts, jedi won't be usable. This issue is tracked in
https://github.com/davidhalter/jedi/issues/1325

A simple workaround is to create and empty `buildout.cfg` file at the root of project folder.