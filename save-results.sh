#!/bin/bash

. local.config

if [ -z "$NAME" ] || [ -z "$USER" ] || [ -z "$RESULTS_DIR" ] || \
	[ -z "$XFSTESTS_DIR" ]
then
	echo "You must populate local.config, check README for required vars"
	exit 1
fi

_date=$(date +"%m-%d-%Y-%H:%M:%S")
_xfstests=${XFSTESTS_DIR}/results
_dir="${RESULTS_DIR}/results/${USER}/${NAME}/${_date}"

# Copy the bulk results
mkdir -p ${_dir}

# We can have 3-6 lines for the last thing, but we always start with Ran, so
# just strip that part downwards for our current check.log
tac ${_xfstests}/check.log | sed -e '/^Ran/q' | tac > ${_dir}/check.log
cp ${_xfstests}/check.time ${_dir}

# Pull all the .dmesg and .bad files
for i in $(find /xfstests-dev/results/ \( -name "*.dmesg" -o -name "*.bad" \))
do
	_path=${i#$_xfstests/}
	_dirname=$(dirname ${_path})
	mkdir -p ${_dir}/${_dirname}
	cp $i ${_dir}/${_dirname}
done
