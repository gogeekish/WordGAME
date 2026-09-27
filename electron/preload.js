const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  isElectron: true,
  sendToProjector: () => ipcRenderer.invoke("projector:send"),
  showWindowed: () => ipcRenderer.invoke("projector:windowed"),
  showGameScreen: () => ipcRenderer.invoke("projector:show"),
  listDisplays: () => ipcRenderer.invoke("projector:list")
});
