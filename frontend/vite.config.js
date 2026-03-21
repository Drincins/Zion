import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';
import fs from 'fs';

const devProxyTarget =
    (process.env.VITE_DEV_PROXY_TARGET && process.env.VITE_DEV_PROXY_TARGET.trim()) ||
    'http://127.0.0.1:8000';
const projectRoot = fs.realpathSync(process.cwd());

export default defineConfig({
    root: projectRoot,
    base: '/',
    plugins: [vue()],
    resolve: {
        alias: {
            '@': path.resolve(projectRoot, './src'),
        },
    },
    server: {
        proxy: {
            '/api': {
                target: devProxyTarget,
                changeOrigin: true,
            },
        },
    },
    css: {
        preprocessorOptions: {
            scss: {
                additionalData: '@use "@/assets/styles/vars.scss" as *;',
            },
        },
    },
});
