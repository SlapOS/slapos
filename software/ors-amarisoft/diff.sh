#!/bin/sh

git diff -C -C x/rrh --	\
	':!config/out'		\
	':!k/'			\
	':!buildout.hash.cfg'	\
	':!test/test.sh'	\
	':!*.json'		\
	':!diff.sh'		\

