// Monorepo Metro config. Required for SDK < 56 (54 here): without it, Metro/EAS anchors to the
// pnpm workspace root — whose package.json has no `main` — and falls back to expo/AppEntry.js,
// which resolves `../../App` at the repo root and fails the cloud bundle. Anchoring projectRoot to
// this app (so `main: index.ts` is honored) and pointing Metro at both node_modules trees fixes it.
// https://docs.expo.dev/guides/monorepos/
const { getDefaultConfig } = require("expo/metro-config");
const path = require("path");

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, "../..");

const config = getDefaultConfig(projectRoot);
config.watchFolders = [workspaceRoot];
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, "node_modules"),
  path.resolve(workspaceRoot, "node_modules"),
];

module.exports = config;
