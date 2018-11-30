#!/usr/bin/env bash
set -e

while [ -n "$1" ]; do
  param="$1"
  value="$2"
  case $param in
    --sdc-home)
        SDC_HOME="$value"
        shift
        ;;
    *)
    break
  esac
  shift
done

SDC_HOME=${SDC_HOME:-$(mktemp -d)}

export SDC_HOME

GPG_HOME="$SDC_HOME/gpg"
mkdir -p "$GPG_HOME"
chmod 0700 "$SDC_HOME" "$GPG_HOME"

echo "Running app with home directory: $SDC_HOME"
echo ""

gpg --homedir "$GPG_HOME" --allow-secret-key-import --import tests/files/securedrop.gpg.asc

# create the database for local testing
./createdb.py "$SDC_HOME"

exec python -m securedrop_client --sdc-home "$SDC_HOME" --no-proxy $@
