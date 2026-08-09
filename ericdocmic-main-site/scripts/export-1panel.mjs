import { createWriteStream, existsSync } from "node:fs"
import { mkdir } from "node:fs/promises"
import { spawnSync } from "node:child_process"
import { fileURLToPath } from "node:url"
import path from "node:path"

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const releaseDir = path.join(root, "release")
await mkdir(releaseDir, { recursive: true })

const timestamp = new Date()
  .toISOString()
  .replace(/[-:]/g, "")
  .replace(/\..+/, "")
  .replace("T", "-")

const archivePath = path.join(releaseDir, `ericdocmic-main-1panel-${timestamp}.tar.gz`)

const tar = spawnSync(
  "tar",
  [
    "--exclude=.DS_Store",
    "--exclude=__MACOSX",
    "--exclude=._*",
    "--exclude=release",
    "-czf",
    archivePath,
    "index.html",
    "404.html",
  ],
  {
    cwd: root,
    env: { ...process.env, COPYFILE_DISABLE: "1" },
    stdio: "inherit",
  },
)

if (tar.status !== 0) {
  process.exit(tar.status ?? 1)
}

const list = spawnSync("tar", ["tf", archivePath], { encoding: "utf8" })
const hasMacMetadata = /(^|\/)(\._|__MACOSX)/m.test(list.stdout)

if (!existsSync(archivePath)) {
  throw new Error("Archive was not created")
}

console.log(`1Panel archive ready: ${archivePath}`)
console.log(`macOS metadata check: ${hasMacMetadata ? 1 : 0}`)

if (hasMacMetadata) {
  process.exit(1)
}
