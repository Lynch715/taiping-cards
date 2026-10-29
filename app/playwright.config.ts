import { defineConfig } from '@playwright/test';
export default defineConfig({testDir:'tests/e2e',timeout:180000,use:{baseURL:'http://127.0.0.1:5191',viewport:{width:390,height:844},trace:'retain-on-failure'},webServer:{command:'npm run dev',url:'http://127.0.0.1:5191',reuseExistingServer:true}});
