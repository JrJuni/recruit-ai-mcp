#!/usr/bin/env node
"use strict";

const { main } = require("./deal-intel-mcp.js");

process.exitCode = main(process.argv.slice(2));
