const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('nextgenAPI', {
  sendOtpEmail: (args) => ipcRenderer.invoke('send-otp-email', args),
  readActivation: () => ipcRenderer.invoke('read-activation'),
  writeActivation: (data) => ipcRenderer.invoke('write-activation', data)
});
