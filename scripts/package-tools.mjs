#!/usr/bin/env node
import { existsSync, mkdirSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const rootDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const toolsDir = join(rootDir, ".tools");
const envDir = join(toolsDir, "readqraft-bio");
const archive = join(toolsDir, "readqraft-bio.tar.gz");

if (!existsSync(envDir)) {
  throw new Error(`Tool environment not found: ${envDir}. Run npm run tools:install first.`);
}

mkdirSync(toolsDir, { recursive: true });
rmSync(archive, { force: true });
console.log(`Creating tool bundle archive: ${archive}`);
execFileSync("tar", ["-czf", archive, "-C", toolsDir, "readqraft-bio"], { stdio: "inherit" });
console.log("Tool bundle archive ready.");
