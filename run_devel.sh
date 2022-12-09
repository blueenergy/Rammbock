#!/bin/bash
base=`dirname $0`
export PATH=$PATH:/usr/local/bin
robot -L DEBUG --pythonpath "$base/src/" "$@"
