import globals from "globals";

export default [
  {
    files: ["web/static/js/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: {
        ...globals.browser,
        ...globals.amd,
        ...globals.commonjs,
        lucide: "readonly",
      },
    },
    rules: {
      "no-unused-vars": ["warn", { "argsIgnorePattern": "^_", "caughtErrorsIgnorePattern": "^_" }],
      "no-console": "off",
      "no-undef": "error",
      "semi": ["error", "always"],
    },
  },
];
