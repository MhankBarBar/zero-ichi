import { defineConfig } from 'vitepress'

export default defineConfig({
    title: 'Zero Ichi',
    description: 'Documentation for the Zero Ichi WhatsApp Bot',
    base: '/',

    head: [
        ['link', { rel: 'icon', href: '/logo.png' }],
    ],

    themeConfig: {
        logo: '/logo.png',

        nav: [
            { text: 'Guide', link: '/getting-started/installation' },
            { text: 'Commands', link: '/commands/general' },
            { text: 'Features', link: '/features/ai' },
            {
                text: 'Development',
                items: [
                    { text: 'Architecture', link: '/development/architecture' },
                    { text: 'Custom Commands', link: '/development/custom-commands' },
                ],
            },
        ],

        sidebar: {
            '/getting-started/': [
                {
                    text: 'Getting Started',
                    items: [
                        { text: 'Installation', link: '/getting-started/installation' },
                        { text: 'Configuration', link: '/getting-started/configuration' },
                        { text: 'First Run', link: '/getting-started/first-run' },
                    ],
                },
            ],
            '/commands/': [
                {
                    text: 'Commands',
                    items: [
                        { text: 'General', link: '/commands/general' },
                        { text: 'Admin', link: '/commands/admin' },
                        { text: 'Group', link: '/commands/group' },
                        { text: 'Content', link: '/commands/content' },
                        { text: 'Moderation', link: '/commands/moderation' },
                        { text: 'Fun', link: '/commands/fun' },
                        { text: 'Utility', link: '/commands/utility' },
                        { text: 'Owner', link: '/commands/owner' },
                    ],
                },
            ],
            '/features/': [
                {
                    text: 'Features',
                    items: [
                        { text: 'Agentic AI', link: '/features/ai' },
                        { text: 'Internationalization', link: '/features/i18n' },
                        { text: 'Web Dashboard', link: '/features/dashboard' },
                    ],
                },
            ],
            '/development/': [
                {
                    text: 'Development',
                    items: [
                        { text: 'Architecture', link: '/development/architecture' },
                        { text: 'Custom Commands', link: '/development/custom-commands' },
                    ],
                },
            ],
        },

        socialLinks: [
            { icon: 'github', link: 'https://github.com/MhankBarBar/zero-ichi' },
        ],

        search: {
            provider: 'local',
        },

        footer: {
            message: 'Built with 💖',
            copyright: '© 2025 MhankBarBar',
        },

        editLink: {
            pattern: 'https://github.com/MhankBarBar/zero-ichi/edit/master/docs/:path',
            text: 'Edit this page on GitHub',
        },
    },
})
