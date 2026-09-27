#!/bin/sh
# Regenerates android/app/src/main/assets/admin.html from the root admin.html.
# Run this again any time the root admin.html changes, before building the app.
set -e
cd "$(dirname "$0")"
SRC="../admin.html"
DEST="app/src/main/assets/admin.html"

{
  echo '<script>window.ANDROID_OFFLINE_MODE=true;</script>'
  sed 's#/socket.io/socket.io.js#socket.io.js#' "$SRC"
} > "$DEST"

echo "Wrote $DEST"
