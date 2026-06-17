#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const VERSION = "0.0.0-dev";

function usage() {
  return [
    "deal-intel-mcp bootstrapper",
    "",
    "Usage:",
    "  deal-intel-mcp setup [--dry-run] [--json] [--lightweight]",
    "                           [--source pypi|testpypi] [--wheel-url URL]",
    "                           [--python PATH]",
    "  deal-intel-mcp doctor [--json] [--live]",
    "  deal-intel-mcp smoke [--profile-only]",
    "  deal-intel-mcp mcp",
    "  deal-intel-mcp where [--json]",
    "  deal-intel-mcp --help",
    "",
    "setup creates ~/.deal-intel/runtime/venv and installs the Python package.",
    "Set DEAL_INTEL_PYTHON to an existing Python interpreter to override the managed runtime.",
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

function optionValue(args, flag) {
  const index = args.indexOf(flag);
  if (index === -1) {
    return null;
  }
  return args[index + 1] || null;
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

function runCapture(command, args) {
  const result = spawnSync(command, args, {
    encoding: "utf8",
    env: baseEnv(),
  });
  return {
    ok: !result.error && result.status === 0,
    status: result.status,
    error: result.error ? result.error.message : null,
    stdout: result.stdout || "",
    stderr: result.stderr || "",
  };
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function baseEnv() {
  return {
    ...process.env,
    PYTHONUTF8: process.env.PYTHONUTF8 || "1",
    PYTHONIOENCODING: process.env.PYTHONIOENCODING || "utf-8",
  };
}

function detectedPython(args) {
  const explicit = optionValue(args, "--python");
  if (explicit) {
    return explicit;
  }
  if (process.env.DEAL_INTEL_BOOTSTRAP_PYTHON) {
    return process.env.DEAL_INTEL_BOOTSTRAP_PYTHON;
  }
  if (process.env.PYTHON) {
    return process.env.PYTHON;
  }
  const candidates = process.platform === "win32"
    ? ["py", "python", "python3"]
    : ["python3", "python"];
  for (const candidate of candidates) {
    if (commandExists(candidate)) {
      return candidate;
    }
  }
  return null;
}

function pythonVersion(pythonPath) {
  if (!pythonPath) {
    return { ok: false, error: "python_missing" };
  }
  const args = pythonPath === "py"
    ? ["-3.11", "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"]
    : ["-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"];
  const result = runCapture(pythonPath, args);
  if (!result.ok) {
    return { ok: false, error: result.error || result.stderr.trim() || "python_version_failed" };
  }
  const version = result.stdout.trim();
  const [major, minor] = version.split(".").map((part) => Number.parseInt(part, 10));
  return {
    ok: Number.isInteger(major) && Number.isInteger(minor) && (major > 3 || (major === 3 && minor >= 11)),
    version,
    error: major > 3 || (major === 3 && minor >= 11) ? null : "python_too_old",
  };
}

function venvCreateCommand(pythonPath, venvPath) {
  if (pythonPath === "py") {
    return { command: "py", args: ["-3.11", "-m", "venv", venvPath] };
  }
  return { command: pythonPath, args: ["-m", "venv", venvPath] };
}

function installSpec(args) {
  const wheelUrl = optionValue(args, "--wheel-url");
  if (wheelUrl) {
    return {
      source: "wheel_url",
      spec: wheelUrl,
      index_url_args: [],
      extras: [],
    };
  }
  const source = optionValue(args, "--source") || "pypi";
  if (!["pypi", "testpypi"].includes(source)) {
    return { error: `source must be pypi or testpypi, got: ${source}` };
  }
  const packageName = hasFlag(args, "--lightweight")
    ? "deal-intel-mcp"
    : "deal-intel-mcp[embedding]";
  const indexUrlArgs = source === "testpypi"
    ? ["--index-url", "https://test.pypi.org/simple/", "--extra-index-url", "https://pypi.org/simple/"]
    : [];
  return {
    source,
    spec: packageName,
    index_url_args: indexUrlArgs,
    extras: hasFlag(args, "--lightweight") ? [] : ["embedding"],
  };
}

function writeInstallState(payload) {
  const p = paths();
  ensureDir(p.runtime_root);
  fs.writeFileSync(p.install_state_path, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function runPython(args, options = {}) {
  const p = paths();
  if (!commandExists(p.effective_python_path)) {
    const payload = {
      ok: false,
      error: "runtime_python_missing",
      message: "Deal Intelligence Python runtime was not found.",
      python_path: p.effective_python_path,
      next_action: "Run `deal-intel-mcp setup`, or set DEAL_INTEL_PYTHON.",
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
  const p = paths();
  const dryRun = hasFlag(args, "--dry-run");
  const json = hasFlag(args, "--json");
  const detected = detectedPython(args);
  const version = pythonVersion(detected);
  const spec = installSpec(args);
  if (spec.error) {
    const payload = {
      ok: false,
      error: "invalid_setup_option",
      message: spec.error,
    };
    if (json) {
      printJson(payload);
    } else {
      process.stderr.write(`${payload.message}\n`);
    }
    return 2;
  }
  const venvPath = path.join(p.runtime_root, "venv");
  const venvCommand = detected ? venvCreateCommand(detected, venvPath) : null;
  const payload = {
    ok: dryRun,
    status: dryRun ? "planned" : "pending",
    bootstrapper_version: VERSION,
    dry_run: dryRun,
    runtime_root: p.runtime_root,
    venv_path: venvPath,
    managed_python_path: p.managed_python_path,
    detected_python: detected,
    detected_python_version: version.version || null,
    install_source: spec.source,
    install_spec: spec.spec,
    extras: spec.extras,
    commands: {
      create_venv: venvCommand,
      upgrade_pip: {
        command: p.managed_python_path,
        args: ["-m", "pip", "install", "--upgrade", "pip"],
      },
      install_package: {
        command: p.managed_python_path,
        args: ["-m", "pip", "install", ...spec.index_url_args, spec.spec],
      },
      doctor: {
        command: p.managed_python_path,
        args: ["-m", "deal_intel.cli", "config", "doctor", "--offline"],
      },
    },
  };
  if (!detected || !version.ok) {
    payload.ok = false;
    payload.status = "failed";
    payload.error = version.error || "python_missing";
    payload.message = detected
      ? `Python 3.11+ is required; detected ${version.version || "unknown"}.`
      : "Python 3.11+ was not found.";
    payload.next_action = "Install Python 3.11+ or pass --python PATH.";
    if (json) {
      printJson(payload);
    } else {
      process.stderr.write(`${payload.message}\n${payload.next_action}\n`);
    }
    return 1;
  }
  if (dryRun) {
    payload.next_action = "Run without --dry-run to create the runtime venv and install the package.";
    if (json) {
      printJson(payload);
    } else {
      process.stdout.write("Setup plan only; no files changed.\n");
      process.stdout.write(`Runtime root: ${payload.runtime_root}\n`);
      process.stdout.write(`Python: ${payload.detected_python} (${payload.detected_python_version})\n`);
      process.stdout.write(`Install: ${payload.install_spec}\n`);
      process.stdout.write(`${payload.next_action}\n`);
    }
    return 0;
  }

  ensureDir(p.runtime_root);
  const steps = [];
  const createResult = spawnSync(venvCommand.command, venvCommand.args, {
    stdio: "inherit",
    env: baseEnv(),
  });
  steps.push({ step: "create_venv", status: createResult.status, error: createResult.error?.message || null });
  if (createResult.error || createResult.status !== 0) {
    payload.ok = false;
    payload.status = "failed";
    payload.error = "venv_creation_failed";
    payload.steps = steps;
    if (json) {
      printJson(payload);
    }
    return 1;
  }

  const upgradeResult = spawnSync(p.managed_python_path, ["-m", "pip", "install", "--upgrade", "pip"], {
    stdio: "inherit",
    env: baseEnv(),
  });
  steps.push({ step: "upgrade_pip", status: upgradeResult.status, error: upgradeResult.error?.message || null });
  if (upgradeResult.error || upgradeResult.status !== 0) {
    payload.ok = false;
    payload.status = "failed";
    payload.error = "pip_upgrade_failed";
    payload.steps = steps;
    if (json) {
      printJson(payload);
    }
    return 1;
  }

  const installArgs = ["-m", "pip", "install", ...spec.index_url_args, spec.spec];
  const installResult = spawnSync(p.managed_python_path, installArgs, {
    stdio: "inherit",
    env: baseEnv(),
  });
  steps.push({ step: "install_package", status: installResult.status, error: installResult.error?.message || null });
  if (installResult.error || installResult.status !== 0) {
    payload.ok = false;
    payload.status = "failed";
    payload.error = "package_install_failed";
    payload.steps = steps;
    if (json) {
      printJson(payload);
    }
    return 1;
  }

  const doctorResult = spawnSync(p.managed_python_path, ["-m", "deal_intel.cli", "config", "doctor", "--offline"], {
    stdio: "inherit",
    env: baseEnv(),
  });
  steps.push({ step: "doctor", status: doctorResult.status, error: doctorResult.error?.message || null });
  const state = {
    schema_version: 1,
    installed_at: new Date().toISOString(),
    bootstrapper_version: VERSION,
    python_path: p.managed_python_path,
    python_version: version.version,
    package_source: spec.source,
    package_version: null,
    package_spec: spec.spec,
    extras: spec.extras,
    last_doctor_status: doctorResult.status === 0 ? "pass" : "fail",
  };
  writeInstallState(state);
  payload.ok = doctorResult.status === 0;
  payload.status = payload.ok ? "installed" : "installed_with_doctor_failure";
  payload.steps = steps;
  payload.install_state_path = p.install_state_path;
  payload.next_action = payload.ok ? "Run `deal-intel-mcp smoke` or configure MCPB with the managed Python path." : "Inspect doctor output, then rerun `deal-intel-mcp doctor`.";
  if (json) {
    printJson(payload);
  } else {
    process.stdout.write(`Runtime Python: ${p.managed_python_path}\n`);
    process.stdout.write(`Install state: ${p.install_state_path}\n`);
    process.stdout.write(`${payload.next_action}\n`);
  }
  return payload.ok ? 0 : 1;
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
