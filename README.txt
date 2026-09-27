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
Each of the 2 players has 5 sections.
Every section has:
- Document / Word / Content
- Mark / Score
- Question

EVERY ITEM HAS ITS OWN SHOW/HIDE BUTTON.
Only items marked Show appear on the public screen.

The server keeps the game state in RAM while it is running. No internet is required.
