#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

function readPackageVersion() {
  try {
    const packageJson = JSON.parse(
      fs.readFileSync(path.join(__dirname, "..", "package.json"), "utf8"),
    );
    return packageJson.version || "0.0.0-dev";
  } catch {
    return "0.0.0-dev";
  }
}

const VERSION = readPackageVersion();
const REPOSITORY_URL = "https://github.com/JrJuni/recruit-ai-mcp";

function mcpbFilename() {
  return `recruit-ai-mcp-${VERSION}.mcpb`;
}

function mcpbDownloadUrl() {
  return `${REPOSITORY_URL}/raw/main/mcpb/${mcpbFilename()}`;
}

function usage() {
  return [
    "recruit-ai-mcp bootstrapper",
    "",
    "Usage:",
    "  recruit-ai-mcp setup [--dry-run] [--json] [--lightweight]",
    "                           [--source pypi|testpypi] [--wheel-url URL]",
    "                           [--python PATH]",
    "  recruit-ai-mcp doctor [--json] [--live]",
    "  recruit-ai-mcp smoke [--profile-only]",
    "  recruit-ai-mcp mcp",
    "  recruit-ai-mcp mcp-config [--json] [--server-name NAME]",
    "  recruit-ai-mcp mcpb [--json]",
    "  recruit-ai-mcp where [--json]",
    "  recruit-ai-mcp --help",
    "",
    "setup creates ~/.recruit-ai/runtime/venv and installs the Python package.",
    "Set RECRUIT_AI_PYTHON to an existing Python interpreter to override the managed runtime.",
    "The old deal-intel-mcp command and DEAL_INTEL_* env vars remain compatibility aliases.",
  ].join("\n");
}

function homeDir() {
  return process.env.RECRUIT_AI_HOME || process.env.DEAL_INTEL_HOME || os.homedir();
}

function paths() {
  const home = homeDir();
  const recruitAiRoot = path.join(home, ".recruit-ai");
  const runtimeRoot = process.env.RECRUIT_AI_RUNTIME_DIR
    || process.env.DEAL_INTEL_RUNTIME_DIR
    || path.join(recruitAiRoot, "runtime");
  const mcpbDir = path.join(runtimeRoot, "mcpb");
  const managedPython = process.platform === "win32"
    ? path.join(runtimeRoot, "venv", "Scripts", "python.exe")
    : path.join(runtimeRoot, "venv", "bin", "python");
  const effectivePython = process.env.RECRUIT_AI_PYTHON
    || process.env.DEAL_INTEL_PYTHON
    || managedPython;
  return {
    home,
    config_path: process.env.RECRUIT_AI_CONFIG_PATH
      || process.env.DEAL_INTEL_CONFIG_PATH
      || path.join(recruitAiRoot, "config.yaml"),
    runtime_root: runtimeRoot,
    mcpb_dir: mcpbDir,
    mcpb_path: path.join(mcpbDir, mcpbFilename()),
    install_state_path: path.join(runtimeRoot, "install-state.json"),
    managed_python_path: managedPython,
    effective_python_path: effectivePython,
    smoke_output_dir: process.env.RECRUIT_AI_SMOKE_DIR
      || process.env.DEAL_INTEL_SMOKE_DIR
      || path.join(recruitAiRoot, "smoke"),
    reports_output_dir: process.env.RECRUIT_AI_REPORTS_DIR
      || process.env.DEAL_INTEL_REPORTS_DIR
      || path.join(recruitAiRoot, "reports"),
    product_context_sources: process.env.RECRUIT_AI_PRODUCT_CONTEXT_SOURCE_DIRS
      || process.env.DEAL_INTEL_PRODUCT_CONTEXT_SOURCE_DIRS
      || path.join(recruitAiRoot, "product-context", "sources"),
    product_context_cache: process.env.RECRUIT_AI_PRODUCT_CONTEXT_CACHE_DIR
      || process.env.DEAL_INTEL_PRODUCT_CONTEXT_CACHE_DIR
      || path.join(recruitAiRoot, "product-context", "cache"),
  };
}

function bundledMcpbPath() {
  if (process.env.RECRUIT_AI_BUNDLED_MCPB_PATH) {
    return process.env.RECRUIT_AI_BUNDLED_MCPB_PATH;
  }
  if (process.env.DEAL_INTEL_BUNDLED_MCPB_PATH) {
    return process.env.DEAL_INTEL_BUNDLED_MCPB_PATH;
  }
  return path.join(__dirname, "..", "mcpb", mcpbFilename());
}

function mcpbState() {
  const p = paths();
  const bundledPath = bundledMcpbPath();
  return {
    filename: mcpbFilename(),
    bundled_path: bundledPath,
    bundled_exists: fs.existsSync(bundledPath),
    local_path: p.mcpb_path,
    local_exists: fs.existsSync(p.mcpb_path),
    fallback_download_url: mcpbDownloadUrl(),
  };
}

function mcpbHandoff() {
  const state = mcpbState();
  return {
    ...state,
    install_summary: "Install the local MCPB file in Claude Desktop Extensions.",
    claude_steps: [
      "Run `recruit-ai-mcp setup` first if local_exists is false.",
      "Open Claude Desktop -> Settings -> Extensions.",
      "Install the local MCPB file shown in local_path.",
      "Paste mcpb_python_interpreter_path into the Python interpreter path field.",
      "Choose storage backend: mongo for real data, local_sample for a quick trial.",
      "Restart Claude Desktop and ask: Run config_doctor.",
      "If config_doctor is OK, create the first client, position, and candidate, then run a recruiting recommendation or metrics tool.",
    ],
  };
}

function copyBundledMcpbToRuntime() {
  const before = mcpbState();
  if (!before.bundled_exists) {
    return {
      ok: false,
      error: "bundled_mcpb_missing",
      message: "The npm package is missing the bundled MCPB file.",
      mcpb: before,
      next_action:
        "Reinstall recruit-ai-mcp from npm, or download the matching MCPB artifact from the GitHub repository.",
    };
  }
  try {
    ensureDir(path.dirname(before.local_path));
    fs.copyFileSync(before.bundled_path, before.local_path);
    return {
      ok: true,
      mcpb: mcpbState(),
    };
  } catch (error) {
    return {
      ok: false,
      error: "mcpb_copy_failed",
      message: `Could not copy the bundled MCPB file: ${error.message}`,
      mcpb: before,
      next_action: "Check write permissions for the Recruit AI runtime directory.",
    };
  }
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
  if (process.env.RECRUIT_AI_BOOTSTRAP_PYTHON) {
    return process.env.RECRUIT_AI_BOOTSTRAP_PYTHON;
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
  const basePackage = `recruit-ai-mcp==${VERSION}`;
  const packageName = hasFlag(args, "--lightweight")
    ? basePackage
    : `recruit-ai-mcp[embedding]==${VERSION}`;
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
      message: "Recruit AI Python runtime was not found.",
      python_path: p.effective_python_path,
      next_action: "Run `recruit-ai-mcp setup`, or set RECRUIT_AI_PYTHON.",
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
    mcpb: mcpbHandoff(),
  };
  if (hasFlag(args, "--json")) {
    printJson(payload);
    return 0;
  }
  process.stdout.write("Recruit AI runtime paths\n");
  for (const [key, value] of Object.entries(payload.paths)) {
    process.stdout.write(`- ${key}: ${value}\n`);
  }
  return 0;
}

function mcpHandoffPayload(args) {
  const p = paths();
  const serverName = optionValue(args, "--server-name") || "recruit-ai-mcp";
  const config = {
    mcpServers: {
      [serverName]: {
        command: p.effective_python_path,
        args: ["-m", "deal_intel.mcp_server"],
        env: {
          PYTHONUTF8: "1",
          PYTHONIOENCODING: "utf-8",
        },
      },
    },
  };
  return {
    ok: true,
    bootstrapper_version: VERSION,
    server_name: serverName,
    mcpb: mcpbHandoff(),
    mcpb_python_interpreter_path: p.effective_python_path,
    managed_python_path: p.managed_python_path,
    config_path: p.config_path,
    claude_desktop_config_snippet: config,
    notes: [
      "The npm setup command installs the Python runtime and places a local MCPB file for Claude Desktop.",
      "For MCPB, paste mcpb_python_interpreter_path into the Python interpreter path field.",
      "For manual Claude Desktop setup, merge claude_desktop_config_snippet into claude_desktop_config.json.",
      "Secrets are not included; keep MongoDB/API keys in MCPB sensitive fields, .env, or shell environment.",
    ],
  };
}

function cmdMcpConfig(args) {
  const payload = mcpHandoffPayload(args);
  if (hasFlag(args, "--json")) {
    printJson(payload);
    return 0;
  }
  process.stdout.write("Recruit AI MCP handoff\n");
  process.stdout.write(`Local MCPB file:\n${payload.mcpb.local_path}\n`);
  process.stdout.write(`Local MCPB exists: ${payload.mcpb.local_exists}\n`);
  process.stdout.write(`Bundled MCPB exists: ${payload.mcpb.bundled_exists}\n`);
  process.stdout.write(`Fallback download URL:\n${payload.mcpb.fallback_download_url}\n\n`);
  process.stdout.write(`MCPB Python interpreter path:\n${payload.mcpb_python_interpreter_path}\n\n`);
  process.stdout.write("Claude Desktop MCPB install steps:\n");
  for (const [index, step] of payload.mcpb.claude_steps.entries()) {
    process.stdout.write(`${index + 1}. ${step}\n`);
  }
  process.stdout.write("\n");
  process.stdout.write("Claude Desktop config snippet:\n");
  process.stdout.write(`${JSON.stringify(payload.claude_desktop_config_snippet, null, 2)}\n\n`);
  for (const note of payload.notes) {
    process.stdout.write(`- ${note}\n`);
  }
  return 0;
}

function cmdMcpb(args) {
  const mcpb = mcpbHandoff();
  const payload = {
    ok: mcpb.bundled_exists || mcpb.local_exists,
    bootstrapper_version: VERSION,
    mcpb,
    mcpb_python_interpreter_path: paths().effective_python_path,
  };
  if (!payload.ok) {
    payload.error = "bundled_mcpb_missing";
    payload.message = "The npm package is missing the bundled MCPB file.";
    payload.next_action =
      "Reinstall recruit-ai-mcp from npm, or download the matching MCPB artifact from the GitHub repository.";
  }
  if (hasFlag(args, "--json")) {
    printJson(payload);
    return payload.ok ? 0 : 1;
  }
  if (!payload.ok) {
    process.stderr.write(`${payload.message}\n${payload.next_action}\n`);
    return 1;
  }
  process.stdout.write("Recruit AI MCPB install handoff\n");
  process.stdout.write(`Local MCPB file:\n${payload.mcpb.local_path}\n`);
  process.stdout.write(`Local MCPB exists: ${payload.mcpb.local_exists}\n`);
  process.stdout.write(`Bundled MCPB exists: ${payload.mcpb.bundled_exists}\n`);
  process.stdout.write(`Fallback download URL:\n${payload.mcpb.fallback_download_url}\n\n`);
  process.stdout.write(`Python interpreter path for the MCPB form:\n${payload.mcpb_python_interpreter_path}\n\n`);
  process.stdout.write("Next steps:\n");
  for (const [index, step] of payload.mcpb.claude_steps.entries()) {
    process.stdout.write(`${index + 1}. ${step}\n`);
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
    mcpb: mcpbHandoff(),
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
      copy_mcpb: {
        from: bundledMcpbPath(),
        to: p.mcpb_path,
      },
      post_install_check: {
        command: p.managed_python_path,
        args: ["-m", "deal_intel.cli", "smoke-profile", "--profile", "sample"],
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

  const copyResult = copyBundledMcpbToRuntime();
  steps.push({
    step: "copy_mcpb",
    status: copyResult.ok ? 0 : 1,
    error: copyResult.ok ? null : copyResult.error,
    from: copyResult.mcpb?.bundled_path || bundledMcpbPath(),
    to: copyResult.mcpb?.local_path || p.mcpb_path,
  });
  payload.mcpb = mcpbHandoff();
  if (!copyResult.ok) {
    payload.ok = false;
    payload.status = "failed";
    payload.error = copyResult.error;
    payload.message = copyResult.message;
    payload.next_action = copyResult.next_action;
    payload.steps = steps;
    if (json) {
      printJson(payload);
    } else {
      process.stderr.write(`${payload.message}\n${payload.next_action}\n`);
    }
    return 1;
  }

  const checkResult = spawnSync(p.managed_python_path, [
    "-m",
    "deal_intel.cli",
    "smoke-profile",
    "--profile",
    "sample",
  ], {
    stdio: "inherit",
    env: baseEnv(),
  });
  steps.push({
    step: "post_install_check",
    status: checkResult.status,
    error: checkResult.error?.message || null,
  });
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
    mcpb_path: payload.mcpb.local_path,
    last_post_install_check_status: checkResult.status === 0 ? "pass" : "fail",
  };
  writeInstallState(state);
  payload.ok = checkResult.status === 0;
  payload.status = payload.ok ? "installed" : "installed_with_post_install_check_failure";
  payload.steps = steps;
  payload.install_state_path = p.install_state_path;
  payload.mcpb = mcpbHandoff();
  payload.next_action = payload.ok
    ? "Install the local MCPB file in Claude Desktop, paste the Python path, run config_doctor, then add your first recruiting records."
    : "Inspect the post-install smoke output, then rerun `recruit-ai-mcp smoke --profile-only`.";
  if (json) {
    printJson(payload);
  } else {
    process.stdout.write(`Installed Recruit AI MCP ${VERSION}\n\n`);
    process.stdout.write(`Installed runtime:\n${p.runtime_root}\n\n`);
    process.stdout.write(`Python interpreter path for Claude MCPB:\n${p.managed_python_path}\n\n`);
    process.stdout.write(`MCPB file to install in Claude Desktop:\n${payload.mcpb.local_path}\n\n`);
    process.stdout.write("Next steps:\n");
    for (const [index, step] of payload.mcpb.claude_steps.entries()) {
      process.stdout.write(`${index + 1}. ${step}\n`);
    }
    process.stdout.write(`\nInstall state:\n${p.install_state_path}\n\n`);
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
  if (command === "mcp-config") {
    return cmdMcpConfig(args);
  }
  if (command === "mcpb") {
    return cmdMcpb(args);
  }
  process.stderr.write(`Unknown command: ${command}\n\n${usage()}\n`);
  return 2;
}

if (require.main === module) {
  process.exitCode = main(process.argv.slice(2));
}

module.exports = {
  main,
};
