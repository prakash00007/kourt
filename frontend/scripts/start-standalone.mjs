import { cpSync, existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const standaloneRoot = path.join(projectRoot, ".next", "standalone");
const standaloneNextRoot = path.join(standaloneRoot, ".next");

function ensureDir(dirPath) {
  mkdirSync(dirPath, { recursive: true });
}

function copyIfPresent(sourcePath, targetPath) {
  if (!existsSync(sourcePath)) {
    return;
  }

  ensureDir(path.dirname(targetPath));
  cpSync(sourcePath, targetPath, { recursive: true, force: true });
}

copyIfPresent(path.join(projectRoot, ".next", "static"), path.join(standaloneNextRoot, "static"));
copyIfPresent(path.join(projectRoot, "public"), path.join(standaloneRoot, "public"));

await import(path.join(standaloneRoot, "server.js"));
