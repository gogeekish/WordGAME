WORD ARENA TV — OFFLINE LAN EDITION

FILES
- server.js
- admin.html
- public.html
- package.json
- electron/main.js, electron/preload.js  (desktop app / .exe wrapper)
- android/  (Android phone app project / .apk wrapper)

============================================================
OPTION A — EASIEST: DOUBLE-CLICK THE .EXE (Windows, one PC + projector)
============================================================
1. Copy "Word Arena TV 1.0.0.exe" onto the Windows PC that will run the game.
2. Plug in the projector/TV with an HDMI (or similar) cable.
3. Press the Windows key + P and choose "Extend" (this tells Windows to treat
   the projector as a second screen instead of mirroring your laptop).
4. Double-click "Word Arena TV 1.0.0.exe". Two windows open automatically:
   - The ADMIN window (the control remote) stays on your laptop screen.
   - The GAME SCREEN window is sent to the projector and made full-screen
     automatically, if a second screen was already detected.
5. If the game screen doesn't appear on the projector (for example, you
   plugged the projector in AFTER opening the app), go to the "Second
   Screen / Projector" panel on the Admin window and click
   "Detect Displays Again", then "Move Game Screen to Projector (Fullscreen)".
6. Play the game from the Admin window, same as described below.
7. Because this .exe still runs the same offline server, you can ALSO open
   http://COMPUTER-IP:3000/admin.html from a phone on the same Wi-Fi, exactly
   like Option B below, at the same time.

============================================================
OPTION B — RUN FROM SOURCE (Windows/Mac/Linux, or LAN-only setup)
============================================================
1. Install Node.js on the computer that will run the game.
2. Extract this folder.
3. Open Command Prompt/Terminal in this folder.
4. Run: npm install
5. Run: npm start
6. On the computer, open: http://localhost:3000/admin.html
7. On the projector/TV computer, open: http://localhost:3000/public.html
8. For an admin phone on the same Wi-Fi/LAN, use the computer's LAN IP:
   http://COMPUTER-IP:3000/admin.html

============================================================
BUILDING YOUR OWN .EXE (only needed if you change the code)
============================================================
1. npm install
2. npm run dist
3. The finished file appears in the "dist" folder as
   "Word Arena TV 1.0.0.exe" — that one file is all you need to copy
   around and share; nobody else needs to install Node.js to run it.

PASTE ALL QUESTIONS AT ONCE
Instead of typing into every box by hand, you can paste a whole batch of
questions into the "Paste All Questions, Answers & Scores" box on the admin
page and click Import. Start each question with its number (1-5), then list
its 5 answers with their points anywhere after that — spacing doesn't
matter. Example:

  1  Name something people do immediately after waking up. | Check phone 35
  Brush teeth 25
  Pray 20   Take a bath 12   Eat 8

  2  Name something people take to school.
  School bag 40   Books 25   lunch 15   Water bottle 12   Pen 8

Pick which board it goes into (Team 1, Team 2, or Shared Board) before you
click Import. This only fills in the boxes — nothing appears on the public
screen until you press that item's own Show button, exactly like typing it
in by hand. Always glance over the filled-in boxes afterward in case a word
or number landed in the wrong spot.

GAME STRUCTURE
There are THREE board modes, switchable any time from Game Settings:

- TEAM MODE (default): 2 players, each with their own 5 questions.
- SHARED MODE: 1 shared board of 5 questions both players compete on.
- MULTIPLAYER: a simple 4-player scoreboard, with no questions at all —
  see below.

Each Team Mode / Shared Mode question has:
- 1 Question box
- 5 Answer boxes, each with its own Mark (points) box

EVERY QUESTION AND EVERY ANSWER/MARK HAS ITS OWN SHOW/HIDE BUTTON.
Only items marked Show appear on the public screen. Showing/hiding is purely
visual — it does NOT change anyone's score by itself.

SCORING — THREE SEPARATE GAMES
Team Mode, the Shared Board, and Multiplayer are treated as three completely
separate games with their own scores; switching between them never mixes or
resets any of them. In Team Mode and the Shared Board, every answer has a
"+ [Player Name]" button for each player next to it — click one to award
that answer's points to whoever actually got it right (this also lets a
player "steal" a point from a question that isn't their own, if you want
that). You can also correct a score by hand any time using the "Correct to"
box in the Scoreboard panel.

MULTIPLAYER MODE — 4 players, hidden until shown, quick-add scoring
Multiplayer is a separate tab with its own 4 players (its own names, not
shared with Team Mode's 2 players) and no questions/answers at all — just a
scoreboard. A brand new player never appears on the projector screen at all
until you click "Show Player" for them, so you can run a 1, 2, 3, or 4-player
game just by showing however many you're using. Above each player's card
there are 3 quick-add buttons (they start as +10, +5, +1) — click one to
instantly add that many points, no typing needed. Change what the 3 numbers
are any time: type new numbers into the boxes above the buttons and click
Save — every player's buttons relabel to match immediately. A manual
"Correct to" box is there too, for any other number, and you can rename
each player right on their card.

============================================================
ANDROID PHONE APP (prepare questions on your phone, even offline)
============================================================
"dist/WordArenaTV.apk" is a small phone app version of the Admin screen.
Unlike opening admin.html in your phone's browser, this app lets you type
in ALL your questions, answers and scores before you even connect to the
game's WiFi — nothing is lost, it's saved right there on your phone.

HOW TO INSTALL IT ON YOUR PHONE
1. Copy WordArenaTV.apk onto your Android phone (send it to yourself, or
   download it from wherever you got this project).
2. Tap the file to install it. Android will warn you it's from "outside
   the Play Store" — this is expected for an app made just for you; tap
   "Install anyway" / "Install without scanning" if asked.
3. Open the "Word Arena TV" app from your home screen.

HOW TO USE IT
1. Type in your questions, answers and scores any time — before or after
   connecting to WiFi. Nothing is shown on the projector from the phone
   app; it just saves your work on the phone until you connect.
2. When you get to the venue, connect your phone to the SAME WiFi as the
   computer running the game.
3. Tap "Find Game Computer" — the app searches the WiFi automatically.
4. Once it says "Found the game computer...", tap "Connect & Sync".
   Everything you typed gets sent to the computer immediately, AND the
   phone STAYS connected from then on — it becomes a full live remote
   control. Every button (Show/Hide, Timer, scores, mode switch) now acts
   on the live game instantly, exactly like using the Admin screen on the
   computer itself.
5. The "Connection Info" box shows the exact address to type into the
   projector's browser.
6. If the phone loses WiFi mid-show, it automatically reconnects once
   back in range; tap "Connect & Sync" again if it doesn't pick back up.

Auto-search works by the phone shouting "is anyone there?" on the WiFi and
the game computer answering back — this needs both devices on the same
WiFi network, with the router not blocking that kind of local traffic
(most home/venue WiFi is fine; some very locked-down office WiFi may block
it — if "Find Game Computer" keeps failing, try a personal hotspot instead).

BUILDING YOUR OWN .APK (only needed if you change the code)
1. Install a Java JDK and the Android command-line tools/SDK.
2. Run ./android/prepare-assets.sh (copies admin.html into the app, with
   the offline flag switched on) whenever you change admin.html.
3. From the "android" folder, run: gradle assembleDebug
4. The finished file appears at
   android/app/build/outputs/apk/debug/app-debug.apk

The server keeps the game state in RAM while it is running. No internet is required.
