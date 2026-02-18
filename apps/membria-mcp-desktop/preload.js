import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("membria", {
  startTerminal: (payload) => ipcRenderer.invoke("terminal:start", payload),
  sendInput: (payload) => ipcRenderer.send("terminal:input", payload),
  onData: (handler) => ipcRenderer.on("terminal:data", (_evt, data) => handler(data)),
  onExit: (handler) => ipcRenderer.on("terminal:exit", (_evt, data) => handler(data)),
});
