const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const nodemailer = require('nodemailer');

const STORE_FILENAME = 'nextgen-login-store.json';

// Always-reliable location: tied to the Windows user profile, never affected
// by a portable .exe's temporary self-extraction folder changing between runs.
function reliableStorePath() {
  return path.join(app.getPath('userData'), STORE_FILENAME);
}

// Best-effort location: electron-builder sets this to the folder the portable
// .exe itself sits in, so a copy of that folder (exe + this file) carries the
// signed-in state to another computer. Not guaranteed on every setup, so it
// is only ever a secondary source/target, never the only place we check.
function portableStorePath() {
  return process.env.PORTABLE_EXECUTABLE_DIR
    ? path.join(process.env.PORTABLE_EXECUTABLE_DIR, STORE_FILENAME)
    : null;
}

ipcMain.handle('read-activation', async () => {
  const portablePath = portableStorePath();
  if (portablePath) {
    try {
      return JSON.parse(fs.readFileSync(portablePath, 'utf8'));
    } catch (e) { /* fall through to the reliable location */ }
  }
  try {
    return JSON.parse(fs.readFileSync(reliableStorePath(), 'utf8'));
  } catch (e) {
    return null;
  }
});

ipcMain.handle('write-activation', async (event, data) => {
  const json = JSON.stringify(data);
  fs.mkdirSync(path.dirname(reliableStorePath()), { recursive: true });
  fs.writeFileSync(reliableStorePath(), json);
  const portablePath = portableStorePath();
  if (portablePath) {
    try { fs.writeFileSync(portablePath, json); } catch (e) { /* best-effort only */ }
  }
  return true;
});

ipcMain.handle('send-otp-email', async (event, { fromEmail, appPassword, toEmail, subject, body }) => {
  try {
    const transporter = nodemailer.createTransport({
      host: 'smtp.gmail.com',
      port: 587,
      secure: false,
      auth: { user: fromEmail, pass: appPassword }
    });
    await transporter.sendMail({ from: fromEmail, to: toEmail, subject, text: body });
    return { ok: true };
  } catch (e) {
    return { ok: false, error: e.message || String(e) };
  }
});

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 900,
    title: 'NextGen Enrollment Count',
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js')
    }
  });
  win.loadFile(path.join(__dirname, '..', 'index.html'));
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
