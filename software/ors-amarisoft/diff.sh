#!/bin/sh

git diff -C -C $@ --	\
	':!config/out'		\
	':!k/'			\
	':!buildout.hash.cfg'	\
	':!test/test.sh'	\
	':!*.json'		\
	':!*.json.jinja2'	\
	':!diff.sh'		\

