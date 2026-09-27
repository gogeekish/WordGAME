#!/bin/bash
set -e
cd "$(dirname "$0")"
cp ../index.html app/src/main/assets/index.html
mkdir -p app/src/main/assets/vendor
cp ../vendor/totp-shared.js app/src/main/assets/vendor/totp-shared.js
echo "Assets copied."
