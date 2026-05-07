const { app, BrowserWindow, dialog } = require("electron");
const { execFileSync, spawn } = require("child_process");
const fs = require("fs");
const net = require("net");
const path = require("path");

let backendProcess = null;

function findFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      server.close(() => resolve(address.port));
    });
    server.on("error", reject);
  });
}

function backendExecutable() {
  const resourceBackend = path.join(process.resourcesPath || "", "backend");
  const exe = process.platform === "win32" ? "readqraft-backend.exe" : "readqraft-backend";
  const candidate = path.join(resourceBackend, exe);
  return fs.existsSync(candidate) ? candidate : null;
}

function toolEnvironment() {
  const packagedArchive = path.join(process.resourcesPath || "", "tools", "readqraft-bio.tar.gz");
  const extracted = path.join(app.getPath("userData"), "tools", "readqraft-bio");
  const development = path.resolve(__dirname, "../../.tools/readqraft-bio");
  if (fs.existsSync(extracted)) return extracted;
  if (fs.existsSync(packagedArchive)) {
    const extractRoot = path.join(app.getPath("userData"), "tools");
    fs.mkdirSync(extractRoot, { recursive: true });
    execFileSync("tar", ["-xzf", packagedArchive, "-C", extractRoot], { stdio: "ignore" });
    return extracted;
  }
  if (fs.existsSync(development)) return development;
  return null;
}

function startBackend(port) {
  const toolEnv = process.env.READQRAFT_TOOL_ENV || toolEnvironment();
  const env = {
    ...process.env,
    READQRAFT_PORT: String(port),
    READQRAFT_ALLOW_MOCK_TOOLS: process.env.READQRAFT_ALLOW_MOCK_TOOLS || (toolEnv ? "0" : "1")
  };
  if (toolEnv) {
    env.READQRAFT_TOOL_ENV = toolEnv;
  }
  const executable = backendExecutable();
  if (executable) {
    backendProcess = spawn(executable, ["--host", "127.0.0.1", "--port", String(port)], { env, stdio: "pipe" });
  } else {
    const backendDir = path.resolve(__dirname, "../../backend");
    backendProcess = spawn(process.env.PYTHON || "python3", ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(port)], {
      cwd: backendDir,
      env,
      stdio: "pipe"
    });
  }
  backendProcess.on("exit", (code) => {
    if (code !== 0 && !app.isQuitting) {
      console.error(`ReadQraft backend exited with code ${code}`);
    }
  });
}

async function waitForBackend(port) {
  const url = `http://127.0.0.1:${port}/api/health`;
  for (let attempt = 0; attempt < 80; attempt += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // wait and retry
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("Backend did not become ready.");
}

async function createWindow() {
  const port = await findFreePort();
  startBackend(port);
  try {
    await waitForBackend(port);
  } catch (error) {
    dialog.showErrorBox("ReadQraft backend did not start", `${error.message}\n\nOpen docs/troubleshooting.md for setup help.`);
  }

  const win = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 980,
    minHeight: 700,
    title: "ReadQraft",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      additionalArguments: [`--readqraft-api=http://127.0.0.1:${port}`]
    }
  });

  if (process.argv.includes("--dev")) {
    await win.loadURL(process.env.READQRAFT_FRONTEND_URL || "http://127.0.0.1:5173");
  } else {
    await win.loadFile(path.join(process.resourcesPath, "frontend", "index.html"));
  }
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  app.isQuitting = true;
  if (backendProcess) backendProcess.kill();
});
