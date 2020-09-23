#!/bin/bash

_fail() {
	echo $1
	exit 1
}

# cd into our base directory, we can be run from anywhere
cd $(dirname $0)
DIR=$(pwd)

. local.config

cd $XFSTESTS_DIR
./check -g auto
cd $DIR
./save-results.sh || _fail "Couldn't save results"

cd $RESULTS_DIR
git add . || _fail "Couldn't add files"
git commit -m "xfstests results" || _fail "Couldn't commit"
git pull --rebase || _fail "Couldn't rebase"
git push origin master || _fail "Couldn't push"
