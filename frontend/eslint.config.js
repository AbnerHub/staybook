import js from "@eslint/js";
import globals from "globals";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";

// Configuración plana de ESLint (flat config) para el frontend React + Vite.
// Incluye reglas recomendadas de JS, React (con JSX runtime) y React Hooks.
export default [
  { ignores: ["dist", "coverage", "node_modules"] },
  js.configs.recommended,
  {
    files: ["**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: { ...globals.browser, ...globals.es2021 },
      parserOptions: {
        ecmaFeatures: { jsx: true },
        sourceType: "module",
      },
    },
    settings: {
      react: { version: "detect" },
    },
    plugins: {
      react,
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...react.configs.flat.recommended.rules,
      ...react.configs.flat["jsx-runtime"].rules,
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
      // El proyecto no usa PropTypes (documentado en el design); se desactiva.
      "react/prop-types": "off",
    },
  },
  {
    files: ["**/*.{test,spec}.{js,jsx}", "src/test/**"],
    languageOptions: {
      globals: { ...globals.node, ...globals.vitest },
    },
  },
];
