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

// Next 16.2.12 pins PostCSS 8.4.31. These build-time advisories have no patched
// compatible Next release yet; remove them as soon as Next updates its dependency.
const allowedAdvisories = new Set([
  "https://github.com/advisories/GHSA-qx2v-qp2m-jg93",
  "https://github.com/advisories/GHSA-6g55-p6wh-862q",
  "https://github.com/advisories/GHSA-r28c-9q8g-f849",
]);

const vulnerabilities = report.vulnerabilities ?? {};

function isAllowed(name, visited = new Set()) {
  if (visited.has(name)) return false;
  const vulnerability = vulnerabilities[name];
  if (!vulnerability?.via?.length) return false;

  const nextVisited = new Set(visited).add(name);
  return vulnerability.via.every((cause) =>
    typeof cause === "string"
      ? isAllowed(cause, nextVisited)
      : allowedAdvisories.has(cause.url),
  );
}

const blocked = Object.keys(vulnerabilities).filter((name) => !isAllowed(name));
if (blocked.length > 0) {
  console.error(`Production dependency audit failed: ${blocked.join(", ")}`);
  console.error(audit.stdout);
  process.exit(1);
}

if (Object.keys(vulnerabilities).length > 0) {
  console.warn(
    "Production audit passed with only the allowlisted Next/PostCSS advisories.",
  );
} else {
  console.log("Production dependency audit passed with no vulnerabilities.");
}
