#!/bin/bash
set -e
cd "$(dirname "$0")"
cp ../index.html app/src/main/assets/index.html
mkdir -p app/src/main/assets/vendor
cp ../vendor/xlsx.full.min.js app/src/main/assets/vendor/xlsx.full.min.js
echo "Assets copied."
