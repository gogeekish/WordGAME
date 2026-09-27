const { app, BrowserWindow, screen, ipcMain, Menu } = require("electron");
const path = require("path");

const PORT = process.env.PORT || 3000;
const BASE_URL = `http://localhost:${PORT}`;

let adminWin = null;
let publicWin = null;

// Prevent two copies of the app running at once (they would fight over the same port).
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (adminWin) {
      if (adminWin.isMinimized()) adminWin.restore();
      adminWin.focus();
    }
  });
}

function startEmbeddedServer() {
  // Loads and starts the same Express + Socket.io server used for LAN play.
  // Requiring it here starts it listening on PORT inside this app's process.
  require(path.join(__dirname, "..", "server.js"));
}

function getPrimaryAndSecondary() {
  const displays = screen.getAllDisplays();
  const primary = screen.getPrimaryDisplay();
  const secondary = displays.find(d => d.id !== primary.id) || null;
  return { displays, primary, secondary };
}

function placePublicWindow(fullscreenOnSecondary) {
  if (!publicWin || publicWin.isDestroyed()) return;
  const { primary, secondary } = getPrimaryAndSecondary();
  if (secondary && fullscreenOnSecondary) {
    publicWin.setFullScreen(false);
    publicWin.setBounds(secondary.bounds);
    publicWin.setFullScreen(true);
    publicWin.show();
  } else {
    publicWin.setFullScreen(false);
    const w = 1000, h = 600;
    publicWin.setBounds({
      x: primary.bounds.x + Math.round((primary.bounds.width - w) / 2),
      y: primary.bounds.y + Math.round((primary.bounds.height - h) / 2),
      width: w,
      height: h
    });
    publicWin.show();
  }
}

function createWindows() {
  adminWin = new BrowserWindow({
    width: 1300,
    height: 900,
    title: "WORD ARENA TV — Admin",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  adminWin.setMenuBarVisibility(false);
  adminWin.loadURL(`${BASE_URL}/admin.html`);

  publicWin = new BrowserWindow({
    width: 1000,
    height: 600,
    title: "WORD ARENA TV — Game Screen",
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  publicWin.setMenuBarVisibility(false);
  publicWin.loadURL(`${BASE_URL}/public.html`);
  publicWin.once("ready-to-show", () => {
    // Auto-place on launch: fullscreen on the projector if one is already
    // connected and Windows is set to "Extend these displays"; otherwise
    // show a normal window on the main screen so it can be dragged over later.
    placePublicWindow(true);
  });

  // If a projector/second monitor gets plugged in after launch, move the
  // game screen over to it automatically.
  screen.on("display-added", () => placePublicWindow(true));

  adminWin.on("closed", () => {
    adminWin = null;
    if (publicWin && !publicWin.isDestroyed()) publicWin.close();
  });
  publicWin.on("closed", () => { publicWin = null; });
}

ipcMain.handle("projector:send", () => {
  placePublicWindow(true);
  return true;
});
ipcMain.handle("projector:windowed", () => {
  placePublicWindow(false);
  return true;
});
ipcMain.handle("projector:show", () => {
  if (publicWin && !publicWin.isDestroyed()) {
    publicWin.show();
    publicWin.focus();
  }
  return true;
});
ipcMain.handle("projector:list", () => {
  const { displays, primary } = getPrimaryAndSecondary();
  return displays.map(d => ({
    id: d.id,
    bounds: d.bounds,
    isPrimary: d.id === primary.id
  }));
});

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  startEmbeddedServer();
  createWindows();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindows();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
