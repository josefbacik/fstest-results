#!/bin/bash

. local.config

if [ -z "$NAME" ] || [ -z "$USER" ] || [ -z "$RESULTS_DIR" ] || \
	[ -z "$XFSTESTS_DIR" ]
then
	echo "You must populate local.config, check README for required vars"
	exit 1
fi

copy_dir() {
	_dir=$1
	_config=$(basename ${_dir})
	_date=$(date +"%m-%d-%Y-%H:%M:%S")
	_target="${RESULTS_DIR}/results/${USER}/${NAME}/${_config}/${_date}"

	mkdir -p ${_target}

	# We can have 3-6 lines for the last thing, but we always start with
	# Ran, so just strip that part downwards for our current check.log
	tac ${_dir}/check.log | sed -e '/^Ran/q' | tac > ${_target}/check.log
	cp ${_dir}/check.time ${_target}

	for i in $(find ${_dir} \( -name "*.dmesg" -o -name "*.bad" \))
	do
		_path=${i#$_dir/}
		_dirname=$(dirname ${_path})
		_filename=$(basename $i)
		_filename=$(echo "${_filename}.html")
		mkdir -p ${_target}/${_dirname}
		cat header > ${_target}/${_dirname}/${_filename}
		cat $i >> ${_target}/${_dirname}/${_filename}
		cat footer >> ${_target}/${_dirname}/${_filename}
	done
}

for i in $(find ${XFSTESTS_DIR}/results -name check.log)
do
	[ "$(dirname ${i})" == "${XFSTESTS_DIR}/results" ] && continue
	copy_dir "$(dirname ${i})"
done
