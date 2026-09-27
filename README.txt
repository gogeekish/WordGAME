WORD ARENA TV — OFFLINE LAN EDITION

FILES
- server.js
- admin.html
- public.html
- package.json
- electron/main.js, electron/preload.js  (desktop app / .exe wrapper)

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

GAME STRUCTURE
There are two board modes, switchable any time from Game Settings on the admin page:

- TEAM MODE (default): each of the 2 players has their own 5 questions.
- SHARED MODE: one shared board of 5 questions that both teams compete on;
  the host awards each answer's points to whichever team guesses it, using
  the "+ [Player Name]" button next to that answer.

Each question has:
- 1 Question box
- 5 Answer boxes, each with its own Mark (points) box

EVERY QUESTION AND EVERY ANSWER/MARK HAS ITS OWN SHOW/HIDE BUTTON.
Only items marked Show appear on the public screen. A team's Total Score
only counts marks that have been revealed (shown), plus any bonus points.
Switching between Team Mode and Shared Mode never resets scores that were
already earned.

VOICE CONTROL (admin page, host computer, Chrome browser only)
Click "Start Listening" on the Voice Control panel, then say things like:
- "team 1" / "team 2" / "shared board" — choose which board to control
- "question 1" through "question 5" — jump to that question
- "next question" / "previous question"
- "show question" / "hide question"
- "show answer 1" through "show answer 5" (and "hide answer #")
- "show mark 1" through "show mark 5" (also accepts "score") (and "hide mark #")
- "show all" / "hide all" — reveal or hide everything in the current question
- "start timer" / "pause timer" / "reset timer"
Voice control needs a real microphone and only works reliably on the
computer actually running Chrome locally (http://localhost:3000/admin.html).
Browsers block microphone access on a plain http://COMPUTER-IP address for
security reasons, so voice control won't work from a phone over Wi-Fi unless
you set up HTTPS separately.

The server keeps the game state in RAM while it is running. No internet is required.
