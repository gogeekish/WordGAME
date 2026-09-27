NEXTGEN ENROLLMENT COUNT — LOGIN EDITION (direct email, no EmailJS)

Same counting tool as the other editions, but with a login screen that
emails YOU a 6-digit code directly — no EmailJS, no third-party account,
no signup anywhere else. You only ever sign in ONCE, ever (see below).

============================================================
HOW IT WORKS
============================================================
1. First time you open the app, it asks for your Gmail address and a free
   "App Password" (see steps below — NOT your normal Gmail password).
2. It immediately emails you a 6-digit code using that same Gmail account.
3. Type the code in — you're now permanently signed in. The app remembers
   this by itself; it will never ask you to sign in again on this
   installation, even after closing and reopening it.
4. If you ever copy the whole app folder (the .exe + resources.neu + the
   small file next to them that remembers you're signed in) to a different
   computer, that copy is ALSO already signed in — because the "you're
   signed in" marker travels with the files, not with the computer.
5. At the very top of the login/setup screen there is always a second
   option: "Have a code from the NextGen Login Code app? Click here" — if
   you'd rather not deal with email at all, open the separate offline
   "NextGen Login Code" app instead, type its 4-digit code in there, and
   you're in just the same, no email required.

============================================================
STEP 1 — GET A GMAIL "APP PASSWORD" (one time, ~2 minutes)
============================================================
1. Go to myaccount.google.com/security
2. Turn on "2-Step Verification" if it isn't already on.
3. Go to myaccount.google.com/apppasswords
4. Type any name (e.g. "NextGen App") and click Create.
5. Google shows you a 16-letter code — that's what you type into the app's
   Setup screen (NOT your real Gmail password — this app never sees or
   needs that).

============================================================
HOW TO RUN THE WINDOWS VERSION
============================================================
1. Copy BOTH "NextGenEnrollmentCount-Login-win_x64.exe" AND
   "resources.neu" into the SAME folder (they must stay together).
2. Double-click the .exe.
3. Windows may show a "protected your PC" warning — click "More info" then
   "Run anyway".
4. Needs Windows 10/11 with "WebView2" (already built into almost every
   modern Windows PC). If it won't open, search "WebView2 Runtime" and
   install Microsoft's free installer once.
5. The app sends the email itself using Windows' own built-in PowerShell —
   nothing extra to install.

============================================================
HOW TO INSTALL THE ANDROID VERSION
============================================================
1. Copy "NextGenEnrollmentCount-Login-1.0.0.apk" onto your Android phone.
2. Tap it to install. Android will warn it's from "outside the Play Store"
   — tap "Install anyway".
3. Open "NextGen Enrollment Count" from your home screen and follow the
   same Setup steps.

============================================================
IMPORTANT SECURITY NOTE
============================================================
Your Gmail address and App Password are saved in a small file next to the
app (Windows) or inside the app's private storage (Android) so it can keep
sending codes without asking again. This is a personal-use safeguard, not
bank-grade security — anyone who can open that file, or your email inbox,
could get in. Keep the app's folder private, the same way you'd protect any
file with a password saved in it. If you ever want to remove the saved
login, click "Reset Login Setup" inside the app.

NOTES
- This is a separate, third way to log in — the plain Offline Edition and
  the offline "Code Login Edition" (with its separate Login Code app) both
  still exist and still work exactly as before. Pick whichever fits you.
- This Windows build is small (a few MB) because it uses Windows' own
  built-in WebView2 instead of bundling a whole browser.

BUILDING YOUR OWN COPIES (only needed if you change the code)
- Windows/Linux/Mac: run "neu build --release" (needs the free
  @neutralinojs/neu command-line tool). Output appears in the "dist" folder.
- Android: run android/prepare-assets.sh, then from the "android" folder,
  run: gradle assembleDebug
