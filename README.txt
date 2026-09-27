WORD ARENA TV — OFFLINE LAN EDITION

FILES
- server.js
- admin.html
- public.html
- package.json

SETUP
1. Install Node.js on the computer that will run the game.
2. Extract this folder.
3. Open Command Prompt/Terminal in this folder.
4. Run: npm install
5. Run: npm start
6. On the computer, open: http://localhost:3000/admin.html
7. On the projector/TV computer, open: http://localhost:3000/public.html
8. For an admin phone on the same Wi-Fi/LAN, use the computer's LAN IP:
   http://COMPUTER-IP:3000/admin.html

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
