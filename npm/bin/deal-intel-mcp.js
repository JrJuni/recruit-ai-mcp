#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const VERSION = "0.0.0-dev";

function usage() {
  return [
    "deal-intel-mcp bootstrapper skeleton",
    "",
    "Usage:",
    "  deal-intel-mcp setup [--dry-run]",
    "  deal-intel-mcp doctor [--json] [--live]",
    "  deal-intel-mcp smoke [--profile-only]",
    "  deal-intel-mcp mcp",
    "  deal-intel-mcp where [--json]",
    "  deal-intel-mcp --help",
    "",
    "This Node wrapper installs nothing yet. D3.3 will add runtime installation.",
    "Set DEAL_INTEL_PYTHON to an existing Python interpreter for local testing.",
  ].join("\n");
}

function homeDir() {
  return process.env.DEAL_INTEL_HOME || os.homedir();
}

function paths() {
  const home = homeDir();
  const dealIntelRoot = path.join(home, ".deal-intel");
  const runtimeRoot = process.env.DEAL_INTEL_RUNTIME_DIR || path.join(dealIntelRoot, "runtime");
  const managedPython = process.platform === "win32"
    ? path.join(runtimeRoot, "venv", "Scripts", "python.exe")
    : path.join(runtimeRoot, "venv", "bin", "python");
  const effectivePython = process.env.DEAL_INTEL_PYTHON || managedPython;
  return {
    home,
    config_path: process.env.DEAL_INTEL_CONFIG_PATH || path.join(dealIntelRoot, "config.yaml"),
    runtime_root: runtimeRoot,
    install_state_path: path.join(runtimeRoot, "install-state.json"),
    managed_python_path: managedPython,
    effective_python_path: effectivePython,
    smoke_output_dir: process.env.DEAL_INTEL_SMOKE_DIR || path.join(dealIntelRoot, "smoke"),
    reports_output_dir: process.env.DEAL_INTEL_REPORTS_DIR || path.join(dealIntelRoot, "reports"),
    product_context_sources: process.env.DEAL_INTEL_PRODUCT_CONTEXT_SOURCE_DIRS
      || path.join(dealIntelRoot, "product-context", "sources"),
    product_context_cache: process.env.DEAL_INTEL_PRODUCT_CONTEXT_CACHE_DIR
      || path.join(dealIntelRoot, "product-context", "cache"),
  };
}

function printJson(payload) {
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
}

function hasFlag(args, flag) {
  return args.includes(flag);
}

function commandExists(commandPath) {
  if (!commandPath) {
    return false;
  }
  if (commandPath.includes(path.sep) || commandPath.includes("/") || commandPath.includes("\\")) {
    return fs.existsSync(commandPath);
  }
  const probe = spawnSync(commandPath, ["--version"], { encoding: "utf8" });
  return !probe.error;
}

function baseEnv() {
  return {
    ...process.env,
    PYTHONUTF8: process.env.PYTHONUTF8 || "1",
    PYTHONIOENCODING: process.env.PYTHONIOENCODING || "utf-8",
  };
}

function runPython(args, options = {}) {
  const p = paths();
  if (!commandExists(p.effective_python_path)) {
    const payload = {
      ok: false,
      error: "runtime_python_missing",
      message: "Deal Intelligence Python runtime was not found.",
      python_path: p.effective_python_path,
      next_action: "Run `deal-intel-mcp setup` after D3.3 lands, or set DEAL_INTEL_PYTHON.",
    };
    if (options.json) {
      printJson(payload);
    } else {
      process.stderr.write(`${payload.message}\n`);
      process.stderr.write(`Python path: ${payload.python_path}\n`);
      process.stderr.write(`${payload.next_action}\n`);
    }
    return 1;
  }
  const result = spawnSync(p.effective_python_path, args, {
    stdio: "inherit",
    env: baseEnv(),
  });
  if (result.error) {
    process.stderr.write(`Failed to run Python command: ${result.error.message}\n`);
    return 1;
  }
  return result.status === null ? 1 : result.status;
}

function cmdWhere(args) {
  const payload = {
    ok: true,
    bootstrapper_version: VERSION,
    paths: paths(),
  };
  if (hasFlag(args, "--json")) {
    printJson(payload);
    return 0;
  }
  process.stdout.write("Deal Intelligence runtime paths\n");
  for (const [key, value] of Object.entries(payload.paths)) {
    process.stdout.write(`- ${key}: ${value}\n`);
  }
  return 0;
}

function cmdSetup(args) {
  const payload = {
    ok: false,
    status: "not_implemented",
    bootstrapper_version: VERSION,
    message: "Runtime installation is planned for D3.3. This D3.2 command skeleton does not install packages yet.",
    planned_runtime_root: paths().runtime_root,
    dry_run: hasFlag(args, "--dry-run"),
    next_action: "For now, install the Python package manually and set DEAL_INTEL_PYTHON for wrapper testing.",
  };
  if (hasFlag(args, "--json")) {
    printJson(payload);
  } else {
    process.stdout.write(`${payload.message}\n`);
    process.stdout.write(`Planned runtime root: ${payload.planned_runtime_root}\n`);
    process.stdout.write(`${payload.next_action}\n`);
  }
  return 2;
}

function cmdDoctor(args) {
  const cliArgs = ["-m", "deal_intel.cli", "config", "doctor"];
  if (!hasFlag(args, "--live")) {
    cliArgs.push("--offline");
  }
  if (hasFlag(args, "--json")) {
    cliArgs.push("--json");
  }
  return runPython(cliArgs, { json: hasFlag(args, "--json") });
}

function cmdSmoke(args) {
  const p = paths();
  fs.mkdirSync(p.smoke_output_dir, { recursive: true });
  const profileStatus = runPython([
    "-m", "deal_intel.cli",
    "smoke-profile",
    "--profile", "sample",
  ]);
  if (profileStatus !== 0 || hasFlag(args, "--profile-only")) {
    return profileStatus;
  }
  return runPython([
    "-m", "deal_intel.cli",
    "smoke-natural-questions",
    "--as-of", "2026-06-10",
    "--output-dir", p.smoke_output_dir,
  ]);
}

function cmdMcp(args) {
  if (args.length > 0) {
    process.stderr.write(`Unexpected mcp arguments: ${args.join(" ")}\n`);
    return 2;
  }
  return runPython(["-m", "deal_intel.mcp_server"]);
}

function main(argv) {
  const [command, ...args] = argv;
  if (!command || command === "--help" || command === "-h" || command === "help") {
    process.stdout.write(`${usage()}\n`);
    return 0;
  }
  if (command === "--version" || command === "-v" || command === "version") {
    process.stdout.write(`${VERSION}\n`);
    return 0;
  }
  if (command === "where") {
    return cmdWhere(args);
  }
  if (command === "setup") {
    return cmdSetup(args);
  }
  if (command === "doctor") {
    return cmdDoctor(args);
  }
  if (command === "smoke") {
    return cmdSmoke(args);
  }
  if (command === "mcp") {
    return cmdMcp(args);
  }
  process.stderr.write(`Unknown command: ${command}\n\n${usage()}\n`);
  return 2;
}

process.exitCode = main(process.argv.slice(2));
