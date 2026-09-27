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
4. If you ever copy the whole app folder (the .exe + the small file next to
   it that remembers you're signed in) to a different computer, that copy
   is ALSO already signed in — because the "you're signed in" marker
   travels with the files, not with the computer.
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
1. Copy "NextGen Enrollment Count (Login Edition) 1.0.1.exe" anywhere on
   your Windows computer — it's one single file, nothing else needed.
2. Double-click it. Windows may show a "protected your PC" warning because
   the app isn't signed by a paid certificate — click "More info" then
   "Run anyway".
3. Once you complete Setup, the app quietly creates a small file called
   "nextgen-login-store.json" in the SAME folder as the .exe — that's the
   file that remembers you're signed in. Leave it there; if you copy the
   app elsewhere, copy that file along with it.

============================================================
HOW TO INSTALL THE ANDROID VERSION
============================================================
1. Copy "NextGenEnrollmentCount-Login-1.0.1.apk" onto your Android phone.
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
- This is a normal single-file Electron .exe (same style as the Offline
  Edition), so there's no second file to keep track of.

VERSION HISTORY
- 1.0.1 — fixed a bug where the app forgot you were signed in every time
  it was closed and reopened (it was checking the wrong folder for the
  saved sign-in file). Also flipped the results table: search words down
  the first column, months across the top.
- 1.0.0 — first release (EmailJS-based, later replaced with direct email
  sending). Superseded by 1.0.1; kept in this project's git history, not
  in the "dist" folder, since it had the sign-in bug above.
From here on, each new build of this app keeps its version number (like
"1.0.1", "1.0.2"...) and old builds stay in "dist" alongside new ones,
the same way Word Arena TV's versions do.

BUILDING YOUR OWN COPIES (only needed if you change the code)
- Windows: npm install, then npm run dist (finished file in "dist" folder)
- Android: run android/prepare-assets.sh, then from the "android" folder,
  run: gradle assembleDebug
