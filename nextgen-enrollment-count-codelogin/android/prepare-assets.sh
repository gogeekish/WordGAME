#!/bin/bash
set -e
cd "$(dirname "$0")"
cp ../index.html app/src/main/assets/index.html
mkdir -p app/src/main/assets/vendor
cp ../vendor/totp-shared.js app/src/main/assets/vendor/totp-shared.js
cp ../vendor/xlsx.full.min.js app/src/main/assets/vendor/xlsx.full.min.js
cp ../vendor/date-parser.js app/src/main/assets/vendor/date-parser.js
echo "Assets copied."
