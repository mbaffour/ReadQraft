#!/usr/bin/env node
import { copyFileSync, existsSync, mkdirSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const rootDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const toolsDir = join(rootDir, ".tools");
const binDir = join(toolsDir, "bin");
const envDir = join(toolsDir, "readqraft-bio");
const cacheDir = join(toolsDir, "cache");
const micromambaName = process.platform === "win32" ? "micromamba.exe" : "micromamba";
const micromambaPath = join(binDir, micromambaName);

function platformId() {
  const arch = process.arch;
  if (process.platform === "darwin" && arch === "arm64") return "osx-arm64";
  if (process.platform === "darwin" && arch === "x64") return "osx-64";
  if (process.platform === "win32" && arch === "x64") return "win-64";
  if (process.platform === "linux" && arch === "x64") return "linux-64";
  if (process.platform === "linux" && arch === "arm64") return "linux-aarch64";
  throw new Error(`Unsupported platform for bundled tool install: ${process.platform}/${arch}`);
}

function run(command, args, options = {}) {
  console.log(`$ ${command} ${args.join(" ")}`);
  execFileSync(command, args, { stdio: "inherit", ...options });
}

function commandOutput(command, args, options = {}) {
  return execFileSync(command, args, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], ...options }).trim();
}

async function download(url, destination) {
  console.log(`Downloading ${url}`);
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Download failed ${response.status}: ${url}`);
  const bytes = Buffer.from(await response.arrayBuffer());
  writeFileSync(destination, bytes);
}

function walk(dir) {
  const items = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    items.push(full);
    if (statSync(full).isDirectory()) items.push(...walk(full));
  }
  return items;
}

async function ensureMicromamba() {
  mkdirSync(binDir, { recursive: true });
  mkdirSync(cacheDir, { recursive: true });
  if (existsSync(micromambaPath)) return;

  const platform = platformId();
  const archive = join(cacheDir, `micromamba-${platform}.tar.bz2`);
  const extractDir = join(cacheDir, `micromamba-${platform}`);
  rmSync(extractDir, { recursive: true, force: true });
  mkdirSync(extractDir, { recursive: true });

  await download(`https://micro.mamba.pm/api/micromamba/${platform}/latest`, archive);
  run("tar", ["-xjf", archive, "-C", extractDir]);

  const candidates = walk(extractDir).filter((p) => basename(p).toLowerCase() === micromambaName.toLowerCase());
  if (!candidates.length) throw new Error(`Could not find ${micromambaName} in downloaded archive.`);
  copyFileSync(candidates[0], micromambaPath);
  if (process.platform !== "win32") run("chmod", ["755", micromambaPath]);
}

function toolEnv() {
  const pathParts =
    process.platform === "win32"
      ? [join(envDir, "Library", "bin"), join(envDir, "Scripts"), envDir, process.env.PATH || ""]
      : [join(envDir, "bin"), process.env.PATH || ""];
  const javaHome = process.platform === "win32" ? join(envDir, "Library") : join(envDir, "lib", "jvm");
  return {
    ...process.env,
    PATH: pathParts.join(process.platform === "win32" ? ";" : ":"),
    JAVA_HOME: existsSync(javaHome) ? javaHome : process.env.JAVA_HOME || "",
    READQRAFT_TOOL_ENV: envDir
  };
}

function verifyTool(command, args) {
  const env = toolEnv();
  try {
    const output = commandOutput(command, args, { env, shell: process.platform === "win32" });
    console.log(`${command}: ${output.split(/\r?\n/)[0]}`);
    return output;
  } catch (error) {
    throw new Error(`Installed tool verification failed for ${command}. ${error.message}`);
  }
}

function verifyPythonModule(moduleName, args) {
  const output = commandOutput("python", ["-m", moduleName, ...args], { env: toolEnv(), shell: process.platform === "win32" });
  console.log(`${moduleName}: ${output.split(/\r?\n/)[0]}`);
  return output;
}

async function main() {
  const platform = platformId();
  const windows = platform === "win-64";
  const condaPackages = windows ? ["python=3.13", "pip", "fastqc", "multiqc"] : ["fastqc", "fastp", "cutadapt", "multiqc"];
  console.log(`Installing ReadQraft tools for ${platform}`);
  await ensureMicromamba();

  run(micromambaPath, ["create", "-y", "-p", envDir, "-c", "conda-forge", "-c", "bioconda", ...condaPackages], {
    env: { ...process.env, MAMBA_ROOT_PREFIX: join(toolsDir, "micromamba-root") }
  });
  if (windows) {
    run("python", ["-m", "pip", "install", "cutadapt"], {
      env: toolEnv(),
      shell: true
    });
  }

  const versions = {
    fastqc: verifyTool("fastqc", ["--version"]),
    trimmer: windows ? verifyPythonModule("cutadapt", ["--version"]) : verifyTool("fastp", ["--version"]),
    cutadapt: verifyPythonModule("cutadapt", ["--version"]),
    multiqc: verifyPythonModule("multiqc", ["--version"])
  };
  writeFileSync(
    join(toolsDir, "tools-manifest.json"),
    JSON.stringify({ platform, envDir, condaPackages, windowsPipPackages: windows ? ["cutadapt"] : [], versions, createdAt: new Date().toISOString() }, null, 2)
  );
  console.log(`\nReadQraft tools are ready in ${envDir}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
