const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const path = require("path");

const app = express();
const server = http.createServer(app);
const io = new Server(server);

const PORT = process.env.PORT || 3000;

app.use(express.static(__dirname));

const QUESTIONS_PER_PLAYER = 5;
const ANSWERS_PER_QUESTION = 5;

function makeAnswer() {
  return { text: "", mark: "", showAnswer: false, showMark: false };
}
function makeQuestion() {
  return {
    question: "",
    showQuestion: false,
    answers: Array.from({ length: ANSWERS_PER_QUESTION }, makeAnswer)
  };
}
function makePlayer(name) {
  return {
    name,
    questions: Array.from({ length: QUESTIONS_PER_PLAYER }, makeQuestion),
    bonus: 0,
    total: 0
  };
}

let state = {
  title: "WORD ARENA TV",
  subtitle: "OFFLINE WORD GAME",
  mode: "team", // "team" = each player has their own 5 questions, "shared" = one shared board of 5 questions
  timer: { running: false, remaining: 30, lastStarted: null },
  gameOver: false,
  winner: "",
  image: { data: "", name: "" },
  players: [makePlayer("PLAYER 1"), makePlayer("PLAYER 2")],
  shared: { questions: Array.from({ length: QUESTIONS_PER_PLAYER }, makeQuestion) }
};

function toNumber(v) {
  const n = Number(String(v).replace(/,/g, ""));
  return Number.isFinite(n) ? n : 0;
}

function normalize() {
  state.players.forEach(p => {
    let earned = 0;
    p.questions.forEach(q => {
      q.answers.forEach(a => {
        if (a.showMark) earned += toNumber(a.mark);
      });
    });
    p.total = earned + toNumber(p.bonus);
  });
}

function publicState() {
  normalize();
  const copy = JSON.parse(JSON.stringify(state));
  if (copy.timer.running && copy.timer.lastStarted) {
    const elapsed = Math.floor((Date.now() - copy.timer.lastStarted) / 1000);
    copy.timer.remaining = Math.max(0, copy.timer.remaining - elapsed);
    if (copy.timer.remaining === 0) copy.timer.running = false;
  }
  copy.timer.lastStarted = null;
  return copy;
}

io.on("connection", socket => {
  socket.emit("state", publicState());

  socket.on("updateState", incoming => {
    if (!incoming || typeof incoming !== "object") return;
    state = {
      ...state,
      ...incoming,
      timer: { ...state.timer, ...(incoming.timer || {}) },
      image: { ...state.image, ...(incoming.image || {}) },
      players: incoming.players || state.players,
      shared: incoming.shared || state.shared
    };
    normalize();
    io.emit("state", publicState());
  });

  socket.on("timerStart", () => {
    if (!state.timer.running) {
      state.timer.running = true;
      state.timer.lastStarted = Date.now();
      io.emit("state", publicState());
    }
  });

  socket.on("timerPause", () => {
    if (state.timer.running && state.timer.lastStarted) {
      const elapsed = Math.floor((Date.now() - state.timer.lastStarted) / 1000);
      state.timer.remaining = Math.max(0, state.timer.remaining - elapsed);
    }
    state.timer.running = false;
    state.timer.lastStarted = null;
    io.emit("state", publicState());
  });

  socket.on("timerReset", seconds => {
    state.timer = { running:false, remaining:Number(seconds)||30, lastStarted:null };
    io.emit("state", publicState());
  });

  socket.on("timerAdd", seconds => {
    let remaining = state.timer.remaining;
    if (state.timer.running && state.timer.lastStarted) {
      remaining = Math.max(0, remaining - Math.floor((Date.now()-state.timer.lastStarted)/1000));
    }
    state.timer.remaining = remaining + (Number(seconds)||0);
    state.timer.lastStarted = state.timer.running ? Date.now() : null;
    io.emit("state", publicState());
  });
});

setInterval(() => {
  if (state.timer.running && state.timer.lastStarted) {
    const elapsed = Math.floor((Date.now()-state.timer.lastStarted)/1000);
    if (state.timer.remaining - elapsed <= 0) {
      state.timer.remaining = 0;
      state.timer.running = false;
      state.timer.lastStarted = null;
    }
    io.emit("state", publicState());
  }
}, 500);

server.listen(PORT, "0.0.0.0", () => {
  console.log(`WORD ARENA TV running on http://localhost:${PORT}`);
  console.log(`For phones on the same Wi-Fi/LAN use the computer's IP address, e.g. http://192.168.1.10:${PORT}`);
});
