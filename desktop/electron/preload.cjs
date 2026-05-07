const { contextBridge } = require("electron");

const apiArg = process.argv.find((arg) => arg.startsWith("--readqraft-api="));
const apiBase = apiArg ? apiArg.split("=")[1] : "http://127.0.0.1:8765";

contextBridge.exposeInMainWorld("readqraft", {
  apiBase
});
