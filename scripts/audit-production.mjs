import { spawnSync } from "node:child_process";

const windows = process.platform === "win32";
const audit = spawnSync(
  windows ? (process.env.ComSpec ?? "cmd.exe") : "npm",
  windows
    ? ["/d", "/s", "/c", "npm audit --omit=dev --json"]
    : ["audit", "--omit=dev", "--json"],
  {
    encoding: "utf8",
  },
);

if (audit.error) {
  console.error(`Unable to run npm audit: ${audit.error.message}`);
  process.exit(1);
}

let report;
try {
  report = JSON.parse(audit.stdout);
} catch {
  console.error(audit.stderr || audit.stdout || "npm audit returned invalid JSON");
  process.exit(1);
}

if (report.error || audit.status === null || audit.status > 1) {
  console.error("Unable to complete npm production audit.");
  console.error(audit.stderr || audit.stdout);
  process.exit(1);
}

const blocked = Object.keys(report.vulnerabilities ?? {});
if (blocked.length > 0) {
  console.error(`Production dependency audit failed: ${blocked.join(", ")}`);
  console.error(audit.stdout);
  process.exit(1);
}

console.log("Production dependency audit passed with no vulnerabilities.");
