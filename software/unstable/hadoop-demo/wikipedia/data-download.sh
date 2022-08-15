#!/bin/bash

. environment.sh

DIR=var/wikipedia/raw-data

mkdir -p $DIR

# http://dumps.wikimedia.org/enwiki/20140203/

# All pages, current versions only.

wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current1.xml-p000000010p000010000.bz2
wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current2.xml-p000010001p000025000.bz2
wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current3.xml-p000025001p000055000.bz2
wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current4.xml-p000055002p000104998.bz2
wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current5.xml-p000105001p000184999.bz2
wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current6.xml-p000185003p000305000.bz2
wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current7.xml-p000305002p000464997.bz2
wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current8.xml-p000465001p000665000.bz2
wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current9.xml-p000665001p000925000.bz2

# don't download the full dataset

# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current10.xml-p000925001p001325000.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current11.xml-p001325001p001825000.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current12.xml-p001825001p002425000.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current13.xml-p002425001p003124998.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current14.xml-p003125001p003924999.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current15.xml-p003925001p004825000.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current16.xml-p004825002p006025000.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current17.xml-p006025001p007524997.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current18.xml-p007525002p009225000.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current19.xml-p009225001p011125000.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current20.xml-p011125001p013324998.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current21.xml-p013325001p015725000.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current22.xml-p015725003p018225000.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current23.xml-p018225001p020925000.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current24.xml-p020925002p023725000.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current25.xml-p023725001p026624999.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current26.xml-p026625002p029625000.bz2
# wget -P $DIR -c http://dumps.wikimedia.org/enwiki/20140203/enwiki-20140203-pages-meta-current27.xml-p029625001p041836446.bz2
