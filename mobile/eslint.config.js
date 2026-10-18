const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');

module.exports = defineConfig([
  expoConfig,
  { ignores: ['dist/**', 'dist-*/**', 'web/dist/**', 'test-results/**', 'playwright-report/**'] },
]);
