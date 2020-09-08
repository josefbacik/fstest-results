#!/bin/bash

. local.config

python generate.py
cp style.css $RESULTS_DIR
