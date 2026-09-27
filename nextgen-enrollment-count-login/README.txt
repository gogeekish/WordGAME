NEXTGEN ENROLLMENT COUNT — LOGIN EDITION

This is the SAME counting tool as the Offline Edition, but it makes you type
in a 6-digit code (emailed to you) before you can use it.

============================================================
WHY IT WORKS THIS WAY (please read this first)
============================================================
This app has no big company server running behind it — it lives entirely on
your computer or phone. To email you a code safely, WITHOUT ever storing your
email password inside the app, it uses a free helper service called
"EmailJS". EmailJS sends the email for you; the app never sees or stores your
real email password anywhere.

============================================================
STEP 1 — CREATE YOUR FREE EMAILJS ACCOUNT (one-time, about 5 minutes)
============================================================
1. Go to https://www.emailjs.com and click "Sign Up" (free plan is enough —
   200 emails/month).
2. After signing up, click "Add New Service" (left menu: "Email Services").
   Choose "Gmail" (or whichever email you use) and follow the on-screen
   steps to connect it — it will ask you to log in to that email account
   and click "Allow". You never type a password into EmailJS itself; Google
   handles that part directly.
3. Once connected, you'll see a "Service ID" like "service_ab12cd3" —
   write that down.
4. Click "Email Templates" (left menu) → "Create New Template".
   - Give it any name, e.g. "OTP Login".
   - In the template's "Content" box, make sure it includes this exact
     text somewhere: {{otp_code}}
     For example: "Your NextGen Enrollment Count login code is: {{otp_code}}"
   - In the "To Email" field (top of the template editor), type: {{to_email}}
   - Click "Save". You'll see a "Template ID" like "template_xy98zz1" —
     write that down.
5. Click your account name (top right) → "General" → find your
   "Public Key" (looks like a random string of letters/numbers) —
   write that down too.

You now have 3 things: a Service ID, a Template ID, and a Public Key.

============================================================
STEP 2 — RUN THE APP AND ENTER YOUR CODES
============================================================
1. Open the app (the .exe on Windows, or the app icon on your phone).
2. The very first screen is "One-Time Setup". Paste in:
   - Service ID
   - Template ID
   - Public Key
   - Your email address (this is where every login code will be sent —
     it will always go here, no matter what)
3. Click "Save Setup". You won't see this screen again unless you click
   "Change Setup" on the login screen later.

============================================================
STEP 3 — LOGGING IN, EVERY TIME YOU OPEN THE APP
============================================================
1. Click "Send Code to My Email".
2. Check your email (the one from Step 2) for a 6-digit code. It may take
   a minute; check spam/junk folders too the first time.
3. Type the 6-digit code into the box and click "Verify & Continue".
4. You're in! Use the counting tool exactly like the Offline Edition:
   paste your document, paste your search words (200 or more is fine),
   click "Count Results", then "Download Excel (.xlsx)".
5. Each code only works for 10 minutes. If it expires, just click
   "Send Code to My Email" again for a new one.
6. Logging in is required again every time you fully close and reopen the
   app (a "Log Out" button in the top-right also does this manually).

============================================================
HOW TO RUN THE .EXE (Windows)
============================================================
1. Copy "NextGen Enrollment Count (Login Edition) 1.0.0.exe" onto your
   Windows computer.
2. Double-click it. Windows may show a "protected your PC" warning because
   the app isn't signed by a paid certificate — click "More info" then
   "Run anyway".
3. You do need an internet connection for the login step (to send/receive
   the code) — but the actual counting and Excel export work exactly the
   same as the Offline Edition once you're logged in.

============================================================
HOW TO INSTALL THE ANDROID APP
============================================================
1. Copy "NextGenEnrollmentCount-Login-1.0.0.apk" onto your Android phone.
2. Tap the file to install it. Android will warn it's from "outside the
   Play Store" — tap "Install anyway".
3. Open "NextGen Enrollment Count (Login)" from your home screen and follow
   Steps 2 and 3 above.

NOTES
- This is a personal-use login lock, not bank-grade security — anyone who
  can open your email can get in, which is normally just you. It's meant to
  stop casual/accidental use by someone else picking up your device.
- This app is completely separate from Word Arena TV and from the Offline
  Edition of NextGen Enrollment Count — none of them affect each other.

BUILDING YOUR OWN COPIES (only needed if you change the code)
- Windows: npm install, then npm run dist (finished file in "dist" folder)
- Android: run android/prepare-assets.sh, then from the "android" folder,
  run: gradle assembleDebug (finished file at
  android/app/build/outputs/apk/debug/app-debug.apk)
