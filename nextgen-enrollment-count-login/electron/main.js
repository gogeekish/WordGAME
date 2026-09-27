const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const nodemailer = require('nodemailer');

function storeDir() {
  return process.env.PORTABLE_EXECUTABLE_DIR || path.dirname(app.getPath('exe'));
}

function storeFilePath() {
  return path.join(storeDir(), 'nextgen-login-store.json');
}

ipcMain.handle('read-activation', async () => {
  try {
    const txt = fs.readFileSync(storeFilePath(), 'utf8');
    return JSON.parse(txt);
  } catch (e) {
    return null;
  }
});

ipcMain.handle('write-activation', async (event, data) => {
  fs.writeFileSync(storeFilePath(), JSON.stringify(data));
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
