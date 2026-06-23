// https://docs.expo.dev/guides/using-eslint/
const expoConfig = require("eslint-config-expo/flat");
const { defineConfig } = require("eslint/config");

module.exports = defineConfig([
  expoConfig,
  {
    ignores: ["dist/*", ".expo/*", "node_modules/*"],
  },
  {
    files: ["**/*.test.{ts,tsx}", "**/__tests__/**"],
    languageOptions: { globals: { describe: true, it: true, expect: true, jest: true } },
  },
]);
