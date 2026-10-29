import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
export default defineConfig({plugins:[react()],base:'./',test:{environment:'node',include:['tests/**/*.test.ts']},server:{host:'127.0.0.1',port:5191,strictPort:true}});
