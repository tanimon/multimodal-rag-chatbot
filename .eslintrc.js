/** @type {import('eslint').Linter.Config} */
module.exports = {
  extends: ["@classmethod"],
  parser: "@typescript-eslint/parser",
  parserOptions: {
    project: "./tsconfig.json",
  },
  ignorePatterns: ["**/*.js"],
};
