import { defineConfig } from 'vitepress'

export default defineConfig({
    title: 'Zero Ichi',
    description: 'A powerful WhatsApp bot built with Python + Neonize — packed with AI, media downloader, group management, and a web dashboard.',
    base: '/',
    appearance: 'dark',
    lastUpdated: true,

    head: [
        ['link', { rel: 'icon', href: '/logo.png' }],
        ['link', { rel: 'preconnect', href: 'https://fonts.googleapis.com' }],
        ['link', { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' }],
        ['link', { href: 'https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,400;0,500;0,700;1,400&display=swap', rel: 'stylesheet' }],
        ['meta', { name: 'theme-color', content: '#201d1d' }],
        ['meta', { property: 'og:type', content: 'website' }],
        ['meta', { property: 'og:title', content: 'Zero Ichi — WhatsApp Bot' }],
        ['meta', { property: 'og:description', content: 'A powerful WhatsApp bot built with Python + Neonize — packed with AI, media downloader, group management, and a web dashboard.' }],
        ['meta', { property: 'og:image', content: '/logo.png' }],
        ['meta', { name: 'twitter:card', content: 'summary' }],
        ['meta', { name: 'twitter:title', content: 'Zero Ichi — WhatsApp Bot' }],
        ['meta', { name: 'twitter:description', content: 'A powerful WhatsApp bot built with Python + Neonize — packed with AI, media downloader, group management, and a web dashboard.' }],
    ],

    markdown: {
        theme: {
            light: 'github-dark',
            dark: 'github-dark',
        },
    },

    themeConfig: {
        logo: '/logo.png',
        siteTitle: 'Zero Ichi',

        outline: {
            level: [2, 3],
            label: 'On this page',
        },

        nav: [
            { text: 'Guide', link: '/getting-started/installation' },
            { text: 'Commands', link: '/commands/general' },
            {
                text: 'Features',
                items: [
                    { text: 'Agentic AI', link: '/features/ai' },
                    { text: 'Internationalization', link: '/features/i18n' },
                    { text: 'Web Dashboard', link: '/features/dashboard' },
                    { text: 'Webhooks', link: '/features/webhooks' },
                    { text: 'Anti-Spam', link: '/features/anti-spam' },
                ],
            },
            {
                text: 'Development',
                items: [
                    { text: 'Contributing', link: '/development/contributing' },
                    { text: 'Architecture', link: '/development/architecture' },
                    { text: 'Custom Commands', link: '/development/custom-commands' },
                ],
            },
        ],

        sidebar: [
            {
                text: 'Guide',
                items: [
                    { text: 'Installation', link: '/getting-started/installation' },
                    { text: 'Configuration', link: '/getting-started/configuration' },
                    { text: 'First Run', link: '/getting-started/first-run' },
                ],
            },
            {
                text: 'Commands',
                collapsed: false,
                items: [
                    { text: 'General', link: '/commands/general' },
                    { text: 'Admin', link: '/commands/admin' },
                    { text: 'Group', link: '/commands/group' },
                    { text: 'Downloader', link: '/commands/downloader' },
                    { text: 'Content', link: '/commands/content' },
                    { text: 'Fun', link: '/commands/fun' },
                    { text: 'Utility', link: '/commands/utility' },
                    { text: 'Moderation', link: '/commands/moderation' },
                    { text: 'Owner', link: '/commands/owner' },
                ],
            },
            {
                text: 'Features',
                collapsed: false,
                items: [
                    { text: 'Agentic AI', link: '/features/ai' },
                    { text: 'Internationalization', link: '/features/i18n' },
                    { text: 'Web Dashboard', link: '/features/dashboard' },
                    { text: 'Webhooks', link: '/features/webhooks' },
                    { text: 'Anti-Spam', link: '/features/anti-spam' },
                ],
            },
            {
                text: 'Development',
                collapsed: true,
                items: [
                    { text: 'Contributing', link: '/development/contributing' },
                    { text: 'Architecture', link: '/development/architecture' },
                    { text: 'Custom Commands', link: '/development/custom-commands' },
                ],
            },
        ],

        socialLinks: [
            { icon: 'github', link: 'https://github.com/MhankBarBar/zero-ichi' },
        ],

        search: {
            provider: 'local',
        },

        footer: {
            message: 'Built with ❤️',
            copyright: '© 2026 MhankBarBar',
        },

        editLink: {
            pattern: 'https://github.com/MhankBarBar/zero-ichi/edit/master/docs/:path',
            text: 'Edit this page on GitHub',
        },

        lastUpdated: {
            text: 'Last updated',
        },
    },
})
