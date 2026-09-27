import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "coverage", "node_modules"] },
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: { ...globals.browser, ...globals.node },
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    plugins: { "react-hooks": reactHooks, "react-refresh": reactRefresh },
    rules: {
      ...reactHooks.configs["recommended-latest"].rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true, allowExportNames: ["createQueryClient", "useSession", "HOME_BY_ROLE"] },
      ],
      "@typescript-eslint/consistent-type-imports": ["error", { fixStyle: "inline-type-imports" }],
      "@typescript-eslint/no-unnecessary-condition": "off",
      // react-hook-form: onSubmit={handleSubmit(...)} devuelve una promesa por diseño.
      "@typescript-eslint/no-misused-promises": ["error", { checksVoidReturn: { attributes: false } }],
      "@typescript-eslint/require-await": "off",
      "@typescript-eslint/restrict-template-expressions": ["error", { allowNumber: true }],
    },
  },
  {
    files: ["src/test/**", "**/*.test.{ts,tsx}"],
    rules: { "react-refresh/only-export-components": "off" },
  },
  {
    files: ["eslint.config.js", "vite.config.ts"],
    ...tseslint.configs.disableTypeChecked,
  },
);
