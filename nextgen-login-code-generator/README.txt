NEXTGEN LOGIN CODE — OFFLINE CODE GENERATOR

WHAT THIS APP IS
This is a small separate app whose only job is to show a rotating 4-digit
code — like a bank token or an authenticator app. It's the "key" for the
CODE LOGIN EDITION of NextGen Enrollment Count.

IT NEEDS NO INTERNET, NO EMAIL, AND NO ACCOUNT
Unlike the earlier Login Edition (which emailed you a code), this one works
completely offline. Both this app and the main app secretly agree on a
"formula" ahead of time (baked in when I built them), so they can each work
out the same code on their own, at the same moment, without ever talking to
each other or to the internet.

HOW TO USE IT
1. Open this app (on your phone, or on the same or a different computer —
   your choice).
2. It shows a big 4-digit code with a small countdown ring around it.
3. Type that code into the NextGen Enrollment Count (Code Login) app's
   login screen within about a minute or so (the code refreshes every
   60 seconds, but the app also accepts the PREVIOUS code for a little
   extra breathing room).
4. If the code stops working, just look at this app again — it will have
   moved to a new one.

HOW TO RUN THE WINDOWS VERSION
1. Copy BOTH "NextGenLoginCode-win_x64.exe" AND "resources.neu" into the
   SAME folder on your Windows computer (they must stay together — the exe
   reads the app's content from resources.neu sitting right next to it).
2. Double-click the .exe.
3. Windows may show a "protected your PC" warning — click "More info" then
   "Run anyway".
4. This version needs Windows 10 or 11 with "WebView2" installed — nearly
   every modern Windows PC already has this built in (it comes with
   Windows Update / Microsoft Edge). If the app doesn't open at all, search
   "WebView2 Runtime" and install Microsoft's free installer once.

HOW TO INSTALL THE ANDROID VERSION
1. Copy "NextGenLoginCode-1.0.0.apk" onto your Android phone.
2. Tap it to install. Android will warn it's from "outside the Play Store"
   — tap "Install anyway".
3. Open "NextGen Login Code" from your home screen.

WHY IS THE WINDOWS FILE SO MUCH SMALLER THAN BEFORE?
The earlier .exe files (Word Arena TV, NextGen Enrollment Count) used a
tool called Electron, which packs an entire mini web browser inside the
app — that's why they were ~70MB. This app instead uses the web browser
already built into Windows (WebView2), so the app itself only needs to be
a few megabytes.

BUILDING YOUR OWN COPIES (only needed if you change the code)
- Windows/Linux/Mac: run "neu build --release" (needs the free
  @neutralinojs/neu command-line tool). Output appears in the "dist" folder.
- Android: run android/prepare-assets.sh, then from the "android" folder,
  run: gradle assembleDebug
