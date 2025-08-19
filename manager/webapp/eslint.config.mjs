import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
baseDirectory: __dirname,
});

// First include the base configs
const eslintConfig = [
...compat.extends("next/core-web-vitals", "next/typescript"),

// Add custom rules for handling unused imports and variables
{
rules: {
// Turn off the default no-unused-vars rule
"@typescript-eslint/no-unused-vars": "off",

// Configure unused-imports plugin rules
"unused-imports/no-unused-imports": "error",
"unused-imports/no-unused-vars": [
"warn",
{
"vars": "all",
"varsIgnorePattern": "^_",
"args": "after-used",
"argsIgnorePattern": "^_"
}
]
},
// Include the unused-imports plugin
plugins: ["unused-imports"]
}
];

export default eslintConfig;
