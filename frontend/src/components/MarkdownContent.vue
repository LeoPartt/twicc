<script setup>
import { ref, inject, watch, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { renderMarkdown } from '../utils/markdown.js'
import { vHighlight } from '../directives/vHighlight.js'
import { toast } from '../composables/useToast'
// Uses the combined version that includes both light and dark
// Then override with our theme file that uses [data-color-scheme] without media queries
import 'github-markdown-css/github-markdown.css'
import '../styles/github-markdown-themes.css'

const props = defineProps({
    source: {
        type: String,
        required: true
    },
    showToolbar: {
        type: Boolean,
        default: true
    }
})

const emit = defineEmits(['rendered'])

const router = useRouter()

// Search highlight terms injected from SessionItemsList (empty when no search active)
const highlightTerms = inject('searchHighlightTerms', ref([]))

const renderedHtml = ref('')
const container = ref(null)
const rendering = ref(true)

// Lazy-loaded mermaid instance (dynamic import to avoid ~500KB in main bundle)
let mermaidModule = null
let mermaidInitialized = false

async function getMermaid() {
    if (!mermaidModule) {
        mermaidModule = (await import('mermaid')).default
    }
    if (!mermaidInitialized) {
        mermaidInitialized = true
        mermaidModule.initialize({
            startOnLoad: false,
            theme: 'default',
            securityLevel: 'loose',
        })
    }
    return mermaidModule
}

// Render mermaid diagrams found in the parsed HTML
async function renderMermaidDiagrams() {
    if (!container.value) return

    const mermaidBlocks = container.value.querySelectorAll('code.language-mermaid')
    if (mermaidBlocks.length === 0) return

    const mermaid = await getMermaid()

    for (const block of mermaidBlocks) {
        const pre = block.closest('pre')
        if (!pre) continue

        const source = block.textContent
        const id = `mermaid-${Math.random().toString(36).slice(2, 11)}`

        try {
            const { svg } = await mermaid.render(id, source)
            const wrapper = document.createElement('div')
            wrapper.className = 'mermaid-diagram'
            wrapper.innerHTML = svg
            pre.replaceWith(wrapper)
        } catch {
            // If mermaid fails, leave the code block as-is (it will show as plain code)
            pre.classList.add('mermaid-error')
        }
    }
}

// Add data-language attribute to code blocks for the language label
function addLanguageLabels() {
    if (!container.value) return

    for (const pre of container.value.querySelectorAll('pre.shiki')) {
        const code = pre.querySelector('code[class*="language-"]')
        if (!code) continue
        const lang = code.className.match(/language-(\S+)/)?.[1]
        if (lang) pre.dataset.language = lang
    }
}

async function render() {
    rendering.value = true
    try {
        renderedHtml.value = await renderMarkdown(props.source)
        await nextTick()
        addLanguageLabels()
        await renderMermaidDiagrams()
    } finally {
        rendering.value = false
        emit('rendered')
    }
}

watch(() => props.source, render)
onMounted(render)

const showRaw = ref(false)

function toggleRaw() {
    showRaw.value = !showRaw.value
}

function copySource() {
    navigator.clipboard.writeText(props.source)
    toast.success('Markdown copied to clipboard', { duration: 2000 })
}

// Intercept clicks on relative links inside rendered markdown to use Vue Router
// navigation instead of full page reloads (SPA-friendly).
function handleLinkClick(event) {
    // Walk up from the click target to find an <a> element (if any)
    const anchor = event.target.closest('a')
    if (!anchor) return

    // Skip absolute links (they already have target="_blank")
    if (anchor.getAttribute('target') === '_blank') return

    const href = anchor.getAttribute('href')
    if (!href) return

    // Skip non-http(s) protocols (mailto:, tel:, etc.)
    if (/^[a-z][a-z0-9+.-]*:/i.test(href) && !/^https?:/i.test(href)) return

    // Let the browser handle modifier clicks (open in new tab)
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return

    event.preventDefault()
    router.push(href)
}
</script>

<template>
    <div class="markdown-content-wrapper">
        <div v-if="showToolbar" class="markdown-toolbar">
            <wa-button-group orientation="vertical" label="Markdown tools">
                <wa-button
                    size="small"
                    :variant="showRaw ? 'neutral' : 'brand'"
                    appearance="filled"
                    :title="showRaw ? 'Show rendered markdown' : 'Show raw markdown'"
                    @click="toggleRaw"
                >
                    <wa-icon :name="showRaw ? 'code' : 'eye'"></wa-icon>
                </wa-button>
                <wa-button
                    size="small"
                    variant="neutral"
                    appearance="filled"
                    title="Copy raw markdown"
                    @click="copySource"
                >
                    <wa-icon name="copy"></wa-icon>
                </wa-button>
            </wa-button-group>
        </div>
        <pre v-if="showRaw" class="markdown-raw">{{ source }}</pre>
        <div
            v-show="!showRaw"
            ref="container"
            class="markdown-body"
            v-html="renderedHtml"
            v-highlight="highlightTerms"
            @click="handleLinkClick"
        ></div>
    </div>
</template>

<style>
/* -------------------------------------------------------------------
   Styles NOT covered by github-markdown-css:
   Shiki syntax highlighting extras + Mermaid diagrams.
   Dark mode handled via class data-color-scheme="dark" on <html> (set by main.js).
   NOT scoped — must penetrate v-html content.
   ------------------------------------------------------------------- */
.markdown-content-wrapper {
    position: relative;
}

.markdown-body {
    background: transparent;
    /* Override github-markdown-css fixed 16px to inherit from :root */
    font-size: 1rem;
}

/* -- Floating toolbar (raw toggle + copy) ---------------------------- */
.markdown-toolbar {
    position: absolute;
    top: 0;
    right: 0;
    padding: 0;
    background: transparent;
    border: none;
    opacity: 0;
    transform: scale(0.8);
    transform-origin: top right;
    transition: opacity 0.15s ease;
    z-index: 2;
}
.markdown-content-wrapper:hover .markdown-toolbar {
    opacity: 0.3;
}
.markdown-toolbar:hover {
    opacity: 1 !important;
}
@media (pointer:coarse) {
    .markdown-content-wrapper:focus {
        opacity: 1 !important;
    }
}
.markdown-toolbar wa-button wa-icon {
    width: .6rem;
}

.markdown-raw {
    margin: 0;
    padding: 0;
    background: transparent;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: var(--wa-font-family-body);
    font-size: 1rem;
    color: var(--wa-color-text-normal);
}

/* -- Shiki-generated code blocks ------------------------------------- */
.markdown-body pre {
    padding: 16px;
    border-radius: 6px;
    overflow-x: auto;
    margin-top: 1em;
}
.markdown-body .highlight pre, .markdown-body pre, .markdown-body code, .markdown-body tt {
    font-size: inherit !important;
}
.markdown-body pre.shiki[data-language]:not([data-language="text"]) {
    padding-top: 36px;
    position: relative;
}
.markdown-body pre.shiki[data-language]:not([data-language="text"])::before {
    content: attr(data-language);
    position: absolute;
    top: 8px;
    left: 16px;
    font-size: var(--wa-font-size-s);
    color: #656d76;
    text-transform: uppercase;
    font-family: var(--wa-font-sans);
}

/* -- Mermaid diagrams ------------------------------------------------ */
.markdown-body .mermaid-diagram {
    margin: 16px 0;
    text-align: center;
    overflow-x: auto;
}
.markdown-body .mermaid-diagram svg {
    max-width: 100%;
    height: auto;
}
.markdown-body pre.mermaid-error {
    border-left: 3px solid #d29922;
}

/* Dark tweak to handle dark mode https://shiki.style/guide/dual-themes */
.shiki, .shiki span {
    --shiki-bg-color: var(--wa-color-surface-default);
    background-color: var(--shiki-bg-color) !important;
}
html.wa-dark .shiki,
html.wa-dark .shiki span {
  color: var(--shiki-dark) !important;
  /* Optional, if you also want font styles */
  font-style: var(--shiki-dark-font-style) !important;
  font-weight: var(--shiki-dark-font-weight) !important;
  text-decoration: var(--shiki-dark-text-decoration) !important;
}

/* -- Search highlight marks (injected by v-highlight directive) ---------- */
mark.search-highlight {
    background-color: oklch(0.85 0.15 90);  /* Warm yellow */
    color: oklch(0.25 0 0);                 /* Dark text for contrast */
    border-radius: 2px;
    padding: 0 1px;
}
html.wa-dark mark.search-highlight {
    background-color: oklch(0.65 0.15 90);  /* Dimmer yellow for dark mode */
    color: oklch(0.95 0 0);                 /* Light text for contrast */
}

</style>
