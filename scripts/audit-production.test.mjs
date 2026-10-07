import assert from "node:assert/strict";
import childProcess from "node:child_process";
import { syncBuiltinESMExports } from "node:module";
import { test } from "node:test";

const cases = [
  { name: "clean report", status: 0, report: { vulnerabilities: {} }, exit: null },
  {
    name: "vulnerable dependency",
    status: 1,
    report: { vulnerabilities: { next: { via: [] } } },
    exit: 1,
  },
  { name: "registry error report", status: 1, report: { error: { code: "E503" } }, exit: 1 },
  { name: "failed audit command", status: 2, report: {}, exit: 1 },
  { name: "terminated audit command", status: null, report: {}, exit: 1 },
  { name: "invalid audit output", status: 0, stdout: "not JSON", exit: 1 },
];

for (const [index, scenario] of cases.entries()) {
  test(scenario.name, async (context) => {
    context.mock.method(childProcess, "spawnSync", () => ({
      status: scenario.status,
      stdout: scenario.stdout ?? JSON.stringify(scenario.report),
      stderr: "",
    }));
    syncBuiltinESMExports();
    context.mock.method(console, "error", () => {});
    context.mock.method(console, "log", () => {});
    context.mock.method(process, "exit", (code) => {
      throw new Error(`exit:${code}`);
    });
    try {
      const execution = import(`./audit-production.mjs?scenario=${index}`);
      if (scenario.exit === null) {
        await execution;
      } else {
        await assert.rejects(execution, { message: `exit:${scenario.exit}` });
      }
    } finally {
      context.mock.restoreAll();
      syncBuiltinESMExports();
    }
  });
}
