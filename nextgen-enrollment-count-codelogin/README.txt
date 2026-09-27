NEXTGEN ENROLLMENT COUNT — CODE LOGIN EDITION

This is the SAME counting tool as the other editions, but instead of
emailing you a code, it checks a 4-digit code that comes from a separate
small app called "NextGen Login Code" — no internet, no email, no signup,
no setup screen at all.

============================================================
HOW IT WORKS
============================================================
1. Open the separate "NextGen Login Code" app (its own download).
2. It shows a 4-digit code that changes every 60 seconds.
3. Type that code into THIS app's login screen and click
   "Verify & Continue".
4. You're in — use the tool exactly like the other editions: paste your
   document, paste your search words (200+ is fine), click "Count
   Results", then "Download Excel (.xlsx)".
5. Logging in is required again every time you fully close and reopen
   this app (a "Log Out" button in the top-right also does this manually).

Both apps secretly share the same "formula" (built in ahead of time), so
they always agree on the current code without ever needing to connect to
each other, to email, or to the internet.

============================================================
HOW TO RUN THE WINDOWS VERSION
============================================================
1. Copy BOTH "NextGenEnrollmentCount-CodeLogin-win_x64.exe" AND
   "resources.neu" into the SAME folder (they must stay together).
2. Double-click the .exe.
3. Windows may show a "protected your PC" warning — click "More info" then
   "Run anyway".
4. Needs Windows 10/11 with "WebView2" (already built into almost every
   modern Windows PC). If it won't open, search "WebView2 Runtime" and
   install Microsoft's free installer once.
5. No internet connection is needed at any point — login and counting both
   work completely offline.

============================================================
HOW TO INSTALL THE ANDROID VERSION
============================================================
1. Copy "NextGenEnrollmentCount-CodeLogin-1.0.0.apk" onto your Android
   phone.
2. Tap it to install. Android will warn it's from "outside the Play Store"
   — tap "Install anyway".
3. Open "NextGen Enrollment Count (Code Login)" from your home screen.

NOTES
- This is a personal-use login lock, not bank-grade security — anyone who
  has (or can see) the Login Code app's screen can get in. It's meant to
  stop casual/accidental use by someone picking up your device.
- This is a separate, third edition — the Offline Edition and the (email)
  Login Edition both still exist and still work exactly as before. Pick
  whichever fits you best.
- Much smaller download than the email Login Edition (a few MB instead of
  ~70MB) because it uses Windows' own built-in WebView2 instead of bundling
  a full browser.

BUILDING YOUR OWN COPIES (only needed if you change the code)
- Windows/Linux/Mac: run "neu build --release" (needs the free
  @neutralinojs/neu command-line tool). Output appears in the "dist" folder.
- Android: run android/prepare-assets.sh, then from the "android" folder,
  run: gradle assembleDebug
