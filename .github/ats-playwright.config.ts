import { defineConfig } from '@playwright/test';

import baseConfig from './playwright.config';

export default defineConfig({
    ...baseConfig,
    use: {
        ...baseConfig.use,
        trace: 'retain-on-failure',
        screenshot: 'only-on-failure',
        video: 'retain-on-failure',
    },
});
