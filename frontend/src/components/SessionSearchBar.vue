<script setup>
import { ref, watch, nextTick } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { apiFetch } from '../utils/api'

const props = defineProps({
    sessionId: {
        type: String,
        required: true
    },
})

const emit = defineEmits(['close'])

const inputRef = ref(null)
const query = ref('')
const isLoading = ref(false)
const matchCount = ref(null)  // null = no search yet, 0+ = result count
const error = ref(null)

/**
 * Perform the search API call.
 * Calls the same /api/search/ endpoint with session_id filter.
 * The backend auto-excludes title documents when session_id is provided.
 */
async function performSearch() {
    const q = query.value.trim()
    if (q.length < 2) {
        matchCount.value = null
        error.value = null
        return
    }

    isLoading.value = true
    error.value = null

    try {
        const params = new URLSearchParams({
            q,
            session_id: props.sessionId,
            include_archived: 'true',
            limit: '1',  // Only 1 session group (we're filtering by session_id)
        })

        const response = await apiFetch(`/api/search/?${params}`)

        if (!response.ok) {
            if (response.status === 503) {
                error.value = 'Search index not available'
            } else {
                error.value = 'Search failed'
            }
            matchCount.value = null
            return
        }

        const data = await response.json()

        // Count distinct line_nums across all matches
        if (data.results && data.results.length > 0) {
            const matches = data.results[0].matches || []
            const uniqueLineNums = new Set(matches.map(m => m.line_num))
            matchCount.value = uniqueLineNums.size
        } else {
            matchCount.value = 0
        }
    } catch (err) {
        error.value = 'Search failed'
        matchCount.value = null
    } finally {
        isLoading.value = false
    }
}

const debouncedSearch = useDebounceFn(performSearch, 300)

// Watch query changes to trigger debounced search
watch(query, () => {
    debouncedSearch()
})

/**
 * Focus the search input.
 * Called when the search bar becomes visible.
 */
function focusInput() {
    nextTick(() => {
        const input = inputRef.value?.shadowRoot?.querySelector('input')
            ?? inputRef.value?.querySelector?.('input')
            ?? inputRef.value
        input?.focus()
    })
}

/**
 * Handle keyboard events on the search input.
 */
function handleKeydown(e) {
    if (e.key === 'Escape') {
        e.preventDefault()
        e.stopPropagation()
        emit('close')
    }
    // Enter / Shift+Enter for next/previous (future functionality)
}

/**
 * Open the search bar and focus input.
 */
function open() {
    focusInput()
}

/**
 * Reset search state.
 */
function reset() {
    query.value = ''
    matchCount.value = null
    error.value = null
}

defineExpose({ open, reset })
</script>

<template>
    <div class="session-search-bar">
        <wa-input
            ref="inputRef"
            :value="query"
            @input="query = $event.target.value"
            @keydown="handleKeydown"
            placeholder="Find in session..."
            size="small"
            class="search-input"
            clearable
        >
            <wa-icon slot="start" name="magnifying-glass"></wa-icon>
        </wa-input>
        <wa-badge
            :variant="matchCount === 0 ? 'danger' : 'neutral'"
            :class="{ 'badge-placeholder': matchCount === null }"
        >
            {{ matchCount ?? 0 }}
        </wa-badge>
        <button
            class="nav-button"
            disabled
            title="Previous match"
            aria-label="Previous match"
        >
            <wa-icon name="chevron-up"></wa-icon>
        </button>
        <button
            class="nav-button"
            disabled
            title="Next match"
            aria-label="Next match"
        >
            <wa-icon name="chevron-down"></wa-icon>
        </button>
        <button
            class="nav-button close-button"
            title="Close (Escape)"
            aria-label="Close search"
            @click="emit('close')"
        >
            <wa-icon name="x"></wa-icon>
        </button>
    </div>
</template>

<style scoped>
.session-search-bar {
    display: flex;
    align-items: center;
    gap: var(--wa-space-m);
    padding: var(--wa-space-s);
    background: var(--wa-color-surface-default);
    border: 4px solid var(--wa-color-surface-border);
    border-top: 0;
    border-radius: 0 0 var(--wa-border-radius-l) var(--wa-border-radius-l);
    flex-shrink: 0;
    position: absolute;
    z-index: 1;
    left: 50%;
    translate: -50% 0;
}

.search-input {
    flex: 1;
    min-width: 0;
    max-width: 300px;
}

.search-spinner {
    font-size: var(--wa-font-size-m);
    flex-shrink: 0;
}

.badge-placeholder {
    visibility: hidden;
}

.nav-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border: none;
    border-radius: var(--wa-border-radius-m);
    background: transparent;
    box-shadow: none;
    color: var(--wa-color-text-muted);
    cursor: pointer;
    flex-shrink: 0;
    padding: 0;
}

.nav-button:hover:not(:disabled) {
    background: var(--wa-color-surface-raised);
    color: var(--wa-color-text);
}

.nav-button:disabled {
    opacity: 0.2;
    cursor: default;
}

.close-button:hover:not(:disabled) {
    color: var(--wa-color-text);
}


@container session-items-list (width <= 30rem) {
    .session-search-bar {
        width: 95%;
        gap: var(--wa-space-s);
        padding: var(--wa-space-xs);
    }
}


</style>
