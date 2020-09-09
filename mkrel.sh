#!/usr/bin/bash -e
# Make new release
VER=$1

echo $VER > VERSION
git add VERSION
git tag "v$VER" -m "v$VER"
