const js = require('@eslint/js');
const vue = require('eslint-plugin-vue');
const eslintConfigPrettier = require('eslint-config-prettier');
const globals = require('globals');
const unusedImports = require('eslint-plugin-unused-imports');

module.exports = [
    { ignores: ['dist/**', 'node_modules/**'] },

    js.configs.recommended,
    ...vue.configs['flat/recommended'],

    {
        files: ['src/**/*.{js,vue}'],
        languageOptions: {
            ecmaVersion: 'latest',
            sourceType: 'module',
            globals: {
                ...globals.browser,
                defineProps: 'readonly',
                defineEmits: 'readonly',
                defineExpose: 'readonly',
                withDefaults: 'readonly',
            },
        },
        plugins: { vue, 'unused-imports': unusedImports },
        rules: {
            'unused-imports/no-unused-imports': 'error',
            'unused-imports/no-unused-vars': [
                'warn',
                { args: 'after-used', argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
            ],
            'no-undef': 'error',
            'no-debugger': 'error',
            'no-console': ['warn', { allow: ['error', 'warn'] }],
            eqeqeq: ['error', 'always'],
            quotes: ['error', 'single'],
            semi: ['error', 'always'],
            'comma-dangle': ['error', 'never'],
            'object-curly-spacing': ['error', 'always'],
            indent: ['error', 4],
            'vue/html-indent': ['error', 4],
            'vue/max-attributes-per-line': ['error', { singleline: 3 }],
            'vue/no-mutating-props': 'error',
            'vue/multi-word-component-names': 'off',
        },
    },
    {
        files: ['src/**/*.vue'],
        languageOptions: {
            parser: require('vue-eslint-parser'),
            parserOptions: { parser: require('espree') },
        },
    },
    {
        files: ['public/sw.js'],
        languageOptions: {
            ecmaVersion: 'latest',
            sourceType: 'script',
            globals: {
                ...(globals.serviceworker || {}),
                ...(globals.worker || {}),
            },
        },
        rules: { 'no-undef': 'off' },
    },
    {
        files: ['eslint.config.cjs', 'vite.config.*', '*.config.*', 'scripts/**/*.{js,cjs,mjs}'],
        languageOptions: {
            ecmaVersion: 'latest',
            sourceType: 'module',
            globals: { ...globals.node },
        },
        rules: { 'no-undef': 'off' },
    },
    eslintConfigPrettier,
];
