#!/bin/bash

. environment.sh

DIR=var/gutenberg/raw-data

mkdir -p $DIR
wget -P $DIR -c http://www.gutenberg.org/cache/epub/103/pg103.txt
wget -P $DIR -c http://www.gutenberg.org/cache/epub/18857/pg18857.txt
wget -P $DIR -c http://www.gutenberg.org/cache/epub/2488/pg2488.txt
wget -P $DIR -c http://www.gutenberg.org/cache/epub/164/pg164.txt
wget -P $DIR -c http://www.gutenberg.org/cache/epub/1268/pg1268.txt
wget -P $DIR -c http://www.gutenberg.org/cache/epub/800/pg800.txt
wget -P $DIR -c http://www.gutenberg.org/cache/epub/4791/pg4791.txt
wget -P $DIR -c http://www.gutenberg.org/cache/epub/3526/pg3526.txt
wget -P $DIR -c http://www.gutenberg.org/cache/epub/2083/pg2083.txt

