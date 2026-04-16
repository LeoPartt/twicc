// frontend/src/utils/theme.js
// Theme management utilities - extracted to avoid circular imports with main.js

const DEFAULT_WA_THEME = 'default'
const DEFAULT_WA_BRAND = 'cyan'

const THEME_TO_PALETTE = { awesome: 'bright', default: 'default', shoelace: 'shoelace' }

const storedSettings = (() => {
    try {
        const raw = localStorage.getItem('twicc-settings')
        return raw ? JSON.parse(raw) : {}
    } catch { return {} }
})()

let currentColorScheme = storedSettings.colorScheme || storedSettings.themeMode || 'system'  // `themeMode` is legacy key
let currentWaTheme = storedSettings.waTheme || DEFAULT_WA_THEME
let currentWaBrand = storedSettings.waBrand || DEFAULT_WA_BRAND

function applyColorScheme() {
    let isDark
    if (currentColorScheme === 'system') {
        isDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    } else {
        isDark = currentColorScheme === 'dark'
    }
    document.documentElement.classList.toggle('wa-dark', isDark)
    document.documentElement.dataset.colorScheme = isDark ? 'dark' : 'light'
}

const WA_THEME_CLASSES = ['wa-theme-awesome', 'wa-theme-default', 'wa-theme-shoelace']
const WA_PALETTE_CLASSES = ['wa-palette-bright', 'wa-palette-default', 'wa-palette-shoelace']
const WA_BRAND_CLASSES = ['wa-brand-blue', 'wa-brand-red', 'wa-brand-orange', 'wa-brand-yellow', 'wa-brand-green', 'wa-brand-cyan', 'wa-brand-indigo', 'wa-brand-purple', 'wa-brand-pink', 'wa-brand-gray']

function applyWaClasses() {
    const palette = THEME_TO_PALETTE[currentWaTheme] || 'default'
    const el = document.documentElement
    el.classList.remove(...WA_THEME_CLASSES, ...WA_PALETTE_CLASSES, ...WA_BRAND_CLASSES)
    el.classList.add(
        `wa-theme-${currentWaTheme}`,
        `wa-palette-${palette}`,
        `wa-brand-${currentWaBrand}`,
    )
    document.documentElement.dataset.theme = currentWaTheme
}

export function setColorScheme(mode) {
    currentColorScheme = mode
    applyColorScheme()
}

export function setWaTheme(theme) {
    currentWaTheme = theme
    applyWaClasses()
}

export function setWaBrand(brand) {
    currentWaBrand = brand
    applyWaClasses()
}

/**
 * Initialize theme on app startup.
 * Apply initial color scheme and WA classes, listen for system preference changes.
 */
export function initTheme() {
    applyColorScheme()
    applyWaClasses()
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyColorScheme)
}
