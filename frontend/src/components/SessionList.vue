<script setup>
/**
 * SessionList - Virtual-scrolled list of sessions for a project.
 *
 * Handles list-level concerns: virtual scrolling, pagination (load more),
 * search filtering, keyboard navigation. Each session item is rendered
 * by SessionListItem, which owns its own store lookups (computed).
 */
import { ref, computed, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useDataStore, ALL_PROJECTS_ID, sessionSortComparator } from '../stores/data'
import { useWorkspacesStore } from '../stores/workspaces'
import { isWorkspaceProjectId, extractWorkspaceId } from '../utils/workspaceIds'
import VirtualScroller from './VirtualScroller.vue'
import SessionListItem from './SessionListItem.vue'

const props = defineProps({
    projectId: {
        type: String,
        required: true
    },
    sessionId: {
        type: String,
        default: null
    },
    showProjectName: {
        type: Boolean,
        default: false
    },
    searchQuery: {
        type: String,
        default: ''
    },
    showArchived: {
        type: Boolean,
        default: false
    },
    showArchivedProjects: {
        type: Boolean,
        default: true
    },
    compactView: {
        type: Boolean,
        default: false
    },
    // When true, sessions with a running Claude SDK process or unread content
    // are always surfaced in the sidebar — even when they belong to a project
    // outside the current filter/workspace.
    showActiveAcrossFilters: {
        type: Boolean,
        default: false
    }
})

const store = useDataStore()
const route = useRoute()

// Natural scope project IDs for the current sidebar filter, passed down so
// SessionListItem can flag any session whose project falls outside it as
// cross-filter (and show its project badge accordingly). null = all-projects
// mode (no scope restriction).
const scopeProjectIds = computed(() => {
    if (isWorkspaceProjectId(props.projectId)) {
        const wsId = extractWorkspaceId(props.projectId)
        const wsStore = useWorkspacesStore()
        return wsStore.getVisibleProjectIds(wsId)
    }
    if (props.projectId === ALL_PROJECTS_ID) return null
    return [props.projectId]
})

// The currently "active" workspace for cross-filter `workspace`-mode pins. Set
// when the sidebar is on a workspace view (projectId `workspace:X`) OR when a
// single-project view preserves the workspace via the `?workspace=X` query.
const activeWorkspaceId = computed(() => {
    if (isWorkspaceProjectId(props.projectId)) {
        return extractWorkspaceId(props.projectId)
    }
    return route.query.workspace || null
})

/**
 * Apply the "hide archived sessions / archived projects" filter, with the
 * usual exception: the currently selected session is never hidden (so a
 * deep-linked archived session stays visible even when the toggles are off).
 */
function applyArchivedFilters(list) {
    const archivedProjectIds = props.showArchivedProjects
        ? null
        : new Set(store.getProjects.filter(p => p.archived).map(p => p.id))
    return list.filter(s =>
        (props.showArchived || !s.archived || s.id === props.sessionId) &&
        (!archivedProjectIds || !archivedProjectIds.has(s.project_id) || s.id === props.sessionId)
    )
}

// Sessions naturally in scope for the current sidebar filter (workspace, all
// projects or single project). Already sorted by `sessionSortComparator` via
// the store getters.
const naturalSessions = computed(() => {
    if (isWorkspaceProjectId(props.projectId)) {
        const wsId = extractWorkspaceId(props.projectId)
        const wsStore = useWorkspacesStore()
        const visibleIds = new Set(wsStore.getVisibleProjectIds(wsId))
        return applyArchivedFilters(store.getAllSessions.filter(s => visibleIds.has(s.project_id)))
    }
    if (props.projectId === ALL_PROJECTS_ID) {
        return applyArchivedFilters(store.getAllSessions)
    }
    return applyArchivedFilters(store.getProjectSessions(props.projectId))
})

/**
 * Pinned sessions that do NOT naturally belong to the current sidebar filter
 * but should still appear thanks to their pin mode:
 *   - `all`       → always visible, regardless of filter
 *   - `workspace` → visible when an active workspace contains their project
 *   - `project`   → never cross-filter (only shown in its own project scope)
 *
 * Sorted by the standard comparator, which reduces to process-first → mtime
 * inside this group since every member is pinned.
 */
const crossFilterPinnedSessions = computed(() => {
    const naturalIds = new Set(naturalSessions.value.map(s => s.id))
    const wsId = activeWorkspaceId.value
    const wsStore = useWorkspacesStore()
    const activeWs = wsId ? wsStore.getWorkspaceById(wsId) : null

    const matches = Object.values(store.sessions).filter(s => {
        if (!s.pinned) return false
        if (s.parent_session_id) return false
        if (naturalIds.has(s.id)) return false
        if (s.pinned === 'all') return true
        if (s.pinned === 'workspace' && activeWs) {
            return activeWs.projectIds.includes(s.project_id)
        }
        return false
    })

    return applyArchivedFilters(matches).sort(sessionSortComparator(store.processStates))
})

/**
 * Sessions that have a running Claude SDK process or unread content but fall
 * outside the current sidebar filter (and are not cross-filter pinned already).
 * Gated by the `showActiveAcrossFilters` prop — when the setting is off, this
 * block is empty and the UI keeps its previous shape.
 *
 * "Unread" mirrors the DB-side check: `last_new_content_at` is set and is more
 * recent than `last_viewed_at` (or the session has never been viewed). We do
 * NOT apply the "only in user_turn" refinement used by `SessionListItem`'s
 * unread *indicator* — a session mid-assistant-turn still deserves to stay
 * surfaced. Drafts are excluded (they have no server-side activity).
 */
const crossFilterActiveSessions = computed(() => {
    if (!props.showActiveAcrossFilters) return []
    const naturalIds = new Set(naturalSessions.value.map(s => s.id))
    const pinnedIds = new Set(crossFilterPinnedSessions.value.map(s => s.id))
    const processStates = store.processStates

    const matches = Object.values(store.sessions).filter(s => {
        if (s.parent_session_id) return false
        if (s.draft) return false
        if (naturalIds.has(s.id)) return false
        if (pinnedIds.has(s.id)) return false
        const ps = processStates[s.id]
        const hasProcess = ps != null
        const isUnread = !!s.last_new_content_at
            && (!s.last_viewed_at || s.last_new_content_at > s.last_viewed_at)
        return hasProcess || isUnread
    })

    return applyArchivedFilters(matches).sort(sessionSortComparator(processStates))
})

/**
 * Id of the selected session when it belongs to none of the upstream blocks —
 * i.e. a deep link to a session that nothing would otherwise bring on screen.
 * Prepended at the very top of the list with a divider below it.
 */
const extraSessionId = computed(() => {
    if (!props.sessionId) return null
    if (naturalSessions.value.some(s => s.id === props.sessionId)) return null
    if (crossFilterPinnedSessions.value.some(s => s.id === props.sessionId)) return null
    if (crossFilterActiveSessions.value.some(s => s.id === props.sessionId)) return null
    const s = store.sessions[props.sessionId]
    if (!s || s.parent_session_id) return null
    return s.id
})

/**
 * Ids of the last item of each top block that should be followed by a divider.
 * A divider is only rendered when the block it terminates has a non-empty
 * block somewhere below it — so the bottom-most non-empty block never gets
 * a trailing divider.
 */
const dividerAfterIds = computed(() => {
    const pinned = crossFilterPinnedSessions.value
    const active = crossFilterActiveSessions.value
    const natural = naturalSessions.value
    const hasExtra = !!extraSessionId.value
    const hasPinned = pinned.length > 0
    const hasActive = active.length > 0
    const hasNatural = natural.length > 0

    const ids = new Set()
    if (hasExtra && (hasPinned || hasActive || hasNatural)) {
        ids.add(extraSessionId.value)
    }
    if (hasPinned && (hasActive || hasNatural)) {
        ids.add(pinned[pinned.length - 1].id)
    }
    if (hasActive && hasNatural) {
        ids.add(active[active.length - 1].id)
    }
    return ids
})

// Flat list consumed by the virtual scroller:
//   [extra?, ...crossFilterPinned, ...crossFilterActive, ...natural]
// Dividers live in the template, keyed off `dividerAfterIds`.
const allSessions = computed(() => {
    const result = []
    if (extraSessionId.value) {
        const extra = store.sessions[extraSessionId.value]
        if (extra) result.push(extra)
    }
    result.push(...crossFilterPinnedSessions.value)
    result.push(...crossFilterActiveSessions.value)
    result.push(...naturalSessions.value)
    return result
})

/**
 * Check if a query matches a text using subsequence matching.
 * All characters from query must appear in text, in order, but not necessarily consecutive.
 * Case-insensitive.
 *
 * Examples:
 *   matchSubsequence("vs", "virtual scroller") -> true (v...irtual s...croller)
 *   matchSubsequence("vscr", "virtual scroller") -> true (v...irtual scr...oller)
 *   matchSubsequence("xyz", "virtual scroller") -> false
 *
 * @param {string} query - The search query
 * @param {string} text - The text to search in
 * @returns {boolean} True if query is a subsequence of text
 */
function matchSubsequence(query, text) {
    const lowerQuery = query.toLowerCase()
    const lowerText = text.toLowerCase()

    let queryIndex = 0
    for (let i = 0; i < lowerText.length && queryIndex < lowerQuery.length; i++) {
        if (lowerText[i] === lowerQuery[queryIndex]) {
            queryIndex++
        }
    }
    return queryIndex === lowerQuery.length
}

// Filtered sessions based on search query (subsequence matching on title)
const sessions = computed(() => {
    const query = props.searchQuery.trim()
    if (!query) return allSessions.value

    return allSessions.value.filter(session => {
        const displayName = (session.draft && !session.title)
            ? 'New session'
            : (session.title || session.id)
        return matchSubsequence(query, displayName)
    })
})

// Pagination state
const hasMore = computed(() => store.hasMoreSessions(props.projectId))
const isLoading = computed(() => store.areSessionsLoading(props.projectId))

// Local error state for "load more" failures (not initial load)
const loadMoreError = ref(false)

// Virtual scroller configuration
// Session items have relatively uniform height (~80-100px normal, ~35-40px compact)
const minSessionHeight = computed(() => props.compactView ? 35 : 70)
const SCROLLER_BUFFER = 300

// Reference to the VirtualScroller component
const scrollerRef = ref(null)

// Keyboard navigation: highlighted item index (-1 = none)
const highlightedIndex = ref(-1)

// Number of items to jump for PageUp/PageDown
const PAGE_SIZE = 10

// Load more sessions when approaching the end of the list
async function loadMore() {
    if (isLoading.value || !hasMore.value || loadMoreError.value) return

    try {
        loadMoreError.value = false
        await store.loadSessions(props.projectId)
    } catch {
        // Only show error if we already have some sessions (not initial load)
        if (sessions.value.length > 0) {
            loadMoreError.value = true
        }
    }
}

// Retry after error
async function handleRetry() {
    loadMoreError.value = false
    await loadMore()
}

/**
 * Handle virtual scroller update event.
 * Triggers loading more sessions when user scrolls near the end.
 */
function onScrollerUpdate({ visibleEndIndex }) {
    // Load more when within 10 items of the end
    if (hasMore.value && !isLoading.value && sessions.value.length - visibleEndIndex < 10) {
        loadMore()
    }
}

// Reset scroll to top and highlight when project changes
watch(() => props.projectId, () => {
    loadMoreError.value = false
    highlightedIndex.value = -1
    if (scrollerRef.value) {
        scrollerRef.value.scrollToTop()
    }
})

// Reset highlight when search query changes
watch(() => props.searchQuery, () => {
    highlightedIndex.value = -1
})

// Reset highlight when selected session changes.
watch(() => props.sessionId, (newSessionId) => {
    highlightedIndex.value = -1
})

// Scroll to the selected session after DOM update.
// Uses flush:'post' because the VirtualScroller has :key="projectId" — when both
// projectId and sessionId change simultaneously (e.g., navigating from search results),
// the scroller is destroyed and recreated. A pre-flush watcher would scroll the OLD
// scroller. flush:'post' ensures the new scroller is mounted and has run its
// onMounted/syncScrollPosition before we attempt to scroll.
// Uses immediate:true because navigating from single-project (/project/X) to all-projects
// (/projects/X/session/Y) remounts the entire component tree (different route branches).
// Without immediate, the watcher wouldn't fire for the initial sessionId value on mount.
watch(() => props.sessionId, (newSessionId) => {
    if (newSessionId) {
        scrollToSession(newSessionId)
    }
}, { flush: 'post', immediate: true })

/**
 * Scroll the session list to make a session visible.
 * Retries a few times because the VirtualScroller may be recreated (via :key)
 * when projectId changes simultaneously with sessionId, and the new scroller
 * needs time to mount and measure items.
 */
function scrollToSession(targetSessionId, attempt = 0) {
    const MAX_ATTEMPTS = 5
    const RETRY_DELAY = 50

    if (!sessions.value.some(s => s.id === targetSessionId)) {
        // Session not in list yet (data loading). Retry a few times.
        if (attempt < MAX_ATTEMPTS) {
            setTimeout(() => scrollToSession(targetSessionId, attempt + 1), RETRY_DELAY)
        }
        return
    }

    if (!scrollerRef.value) {
        // Scroller not mounted yet (recreated via :key). Retry.
        if (attempt < MAX_ATTEMPTS) {
            setTimeout(() => scrollToSession(targetSessionId, attempt + 1), RETRY_DELAY)
        }
        return
    }

    // Use the VirtualScroller's scrollToKey which has a robust "jump, settle, correct"
    // loop: it scrolls to the item, waits for ResizeObserver height measurements to
    // stabilize, then verifies visibility and re-scrolls if needed. This handles all
    // timing issues when the scroller was just recreated (via :key on projectId change).
    scrollerRef.value.scrollToKey(targetSessionId, { align: 'center' })
}

const emit = defineEmits(['select', 'drop-data', 'focus-search'])

function handleSelect(session) {
    emit('select', session)
}

function handleDropData(data) {
    emit('drop-data', data)
}

/**
 * Get the starting index for keyboard navigation.
 * If a session is highlighted, use that. Otherwise, use the selected session's index.
 * Returns -1 if neither is available.
 */
function getNavigationStartIndex() {
    if (highlightedIndex.value >= 0) {
        return highlightedIndex.value
    }
    // No highlight - try to start from selected session
    if (props.sessionId) {
        const selectedIndex = sessions.value.findIndex(s => s.id === props.sessionId)
        if (selectedIndex >= 0) {
            return selectedIndex
        }
    }
    return -1
}

/**
 * Handle keyboard navigation from the search input or the list itself.
 * Navigates through sessions with arrow keys and selects with Enter.
 *
 * @param {KeyboardEvent} event - The keyboard event
 * @param {Object} [options] - Navigation options
 * @param {boolean} [options.fromSearch=false] - True when called from the search input.
 *   When true, navigation ignores the selected session and always starts from scratch
 *   (e.g., ArrowDown goes to the first item, not relative to the active session).
 * @returns {boolean} True if the event was handled (should preventDefault)
 */
function handleKeyNavigation(event, { fromSearch = false } = {}) {
    const count = sessions.value.length
    if (count === 0) return false

    const key = event.key
    // When coming from the search input with no highlight, always start from
    // scratch (-1) so that ArrowDown goes to the first item, not relative to
    // the currently selected session.
    const startIndex = (fromSearch && highlightedIndex.value < 0) ? -1 : getNavigationStartIndex()
    let newIndex = highlightedIndex.value

    switch (key) {
        case 'ArrowDown':
            // Move down from current position, or start at first item
            newIndex = startIndex < 0 ? 0 : Math.min(startIndex + 1, count - 1)
            break

        case 'ArrowUp':
            // If already at the first item, move focus back to the search input
            if (startIndex === 0) {
                highlightedIndex.value = -1
                emit('focus-search')
                return true
            }
            // Move up from current position, or start at last item
            newIndex = startIndex < 0 ? count - 1 : Math.max(startIndex - 1, 0)
            break

        case 'Home':
            newIndex = 0
            break

        case 'End':
            newIndex = count - 1
            break

        case 'PageDown':
            newIndex = startIndex < 0 ? PAGE_SIZE - 1 : Math.min(startIndex + PAGE_SIZE, count - 1)
            break

        case 'PageUp':
            // If already at the first item, move focus back to the search input
            if (startIndex === 0) {
                highlightedIndex.value = -1
                emit('focus-search')
                return true
            }
            newIndex = startIndex < 0 ? 0 : Math.max(startIndex - PAGE_SIZE, 0)
            break

        case 'Enter':
            // Select the highlighted session
            if (highlightedIndex.value >= 0 && highlightedIndex.value < count) {
                handleSelect(sessions.value[highlightedIndex.value])
                return true
            }
            return false

        case 'Escape':
            // Clear highlight if any, otherwise let parent handle it (e.g., clear search)
            if (highlightedIndex.value >= 0) {
                highlightedIndex.value = -1
                return true
            }
            return false

        default:
            return false
    }

    // Update highlight and scroll to it
    if (newIndex !== highlightedIndex.value) {
        highlightedIndex.value = newIndex
        if (scrollerRef.value) {
            // For Home/End, use the scroller's native methods which work better
            // For other navigation, scroll to make the item visible
            if (key === 'Home') {
                scrollerRef.value.scrollToTop()
            } else if (key === 'End') {
                // scrollToBottom() uses estimated heights for unmeasured items,
                // which may not scroll far enough. After the initial scroll,
                // wait for items to be rendered AND measured by ResizeObserver.
                // ResizeObserver is async and not tied to Vue's nextTick, so we use
                // a small timeout to allow measurements to complete.
                scrollerRef.value.scrollToBottom()
                setTimeout(() => {
                    scrollerRef.value?.scrollToIndex(newIndex, { align: 'end' })
                }, 50)
            } else if (key === 'PageDown' || key === 'PageUp') {
                // Page navigation may jump to unmeasured items, use delayed correction
                scrollToIndexIfNeeded(newIndex, { delayedCorrection: true })
            } else {
                // For arrow keys, items are usually already measured (adjacent to visible)
                scrollToIndexIfNeeded(newIndex)
            }

            // Ensure focus stays on the list after scroll (items may be re-rendered)
            // Use nextTick to wait for Vue to update the DOM
            nextTick(() => {
                scrollerRef.value?.$el?.focus()
            })
        }
    }
    return true
}

/**
 * Scroll to an index only if it's not already fully visible in the viewport.
 * Uses align 'start' or 'end' depending on scroll direction.
 *
 * @param {number} index - The item index to scroll to
 * @param {Object} [options] - Options
 * @param {boolean} [options.delayedCorrection=false] - If true, re-scroll after a delay
 *        to account for items that weren't measured yet (heights were estimated)
 */
function scrollToIndexIfNeeded(index, { delayedCorrection = false } = {}) {
    if (!scrollerRef.value) return

    // Get the actual visible range from the scroller (based on measured heights)
    // visibleEnd is exclusive and may include a partially visible item at the bottom
    const { start: visibleStart, end: visibleEnd } = scrollerRef.value.getVisibleRange()

    let scrolled = false
    let align = null

    if (index < visibleStart) {
        // Item is above the viewport
        align = 'start'
        scrollerRef.value.scrollToIndex(index, { align })
        scrolled = true
    } else if (index >= visibleEnd) {
        // Item is below the viewport
        align = 'end'
        scrollerRef.value.scrollToIndex(index, { align })
        scrolled = true
    }

    // If we scrolled and correction is requested, re-scroll after items are measured
    // This handles the case where we scroll to unmeasured items with estimated heights
    if (scrolled && delayedCorrection && align) {
        setTimeout(() => {
            scrollerRef.value?.scrollToIndex(index, { align })
        }, 50)
    }
}

/**
 * Handle keydown events directly on the session list container.
 * This allows keyboard navigation when focus is in the list (not just the search input).
 *
 * @param {KeyboardEvent} event
 */
function handleListKeydown(event) {
    // Only handle navigation keys
    const navigationKeys = ['ArrowDown', 'ArrowUp', 'Home', 'End', 'PageUp', 'PageDown', 'Enter', 'Escape']
    if (!navigationKeys.includes(event.key)) return

    const handled = handleKeyNavigation(event)
    if (handled) {
        event.preventDefault()
    }
}

// Expose methods for parent component access via ref
defineExpose({
    handleKeyNavigation,
})
</script>

<template>
    <div class="session-list-container" :class="{ 'session-list-container--compact': compactView }">
        <!-- Empty state: no sessions at all -->
        <div v-if="allSessions.length === 0 && !isLoading" class="empty-state">
            No sessions
        </div>

        <!-- Empty state: no matching sessions (search returned nothing) -->
        <div v-else-if="sessions.length === 0 && !isLoading" class="empty-state">
            No matching sessions
        </div>

        <!-- Session list with virtual scroller -->
        <VirtualScroller
            v-else
            ref="scrollerRef"
            :key="projectId"
            :items="sessions"
            :item-key="session => session.id"
            :min-item-height="minSessionHeight"
            :buffer="SCROLLER_BUFFER"
            :unload-buffer="SCROLLER_BUFFER * 1.5"
            class="session-list"
            tabindex="0"
            @update="onScrollerUpdate"
            @keydown="handleListKeydown"
        >
            <template #default="{ item: session, index }">
                <SessionListItem
                    :session="session"
                    :active="session.id === sessionId"
                    :highlighted="index === highlightedIndex"
                    :compact-view="compactView"
                    :show-project-name="showProjectName"
                    :scope-project-ids="scopeProjectIds"
                    @select="handleSelect"
                    @drop-data="handleDropData"
                />
                <wa-divider
                    v-if="dividerAfterIds.has(session.id)"
                    class="session-list-group-divider"
                ></wa-divider>
            </template>
        </VirtualScroller>

        <!-- Error state for load more (shown after the scroller) -->
        <div v-if="loadMoreError" class="load-more-error">
            <wa-callout variant="danger">
                <span>Failed to load more sessions</span>
                <wa-button
                    slot="footer"
                    variant="danger"
                    appearance="outlined"
                    size="small"
                    :loading="isLoading"
                    @click="handleRetry"
                >
                    <wa-icon name="arrow-rotate-right" slot="start"></wa-icon>
                    Retry
                </wa-button>
            </wa-callout>
        </div>

        <!-- Loading indicator (shown at bottom when loading more) -->
        <div v-if="isLoading && sessions.length > 0" class="load-more-indicator">
            <wa-spinner></wa-spinner>
        </div>

    </div>
</template>

<style scoped>
.session-list-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    overflow: hidden;
    container-type: inline-size;
    container-name: session-list;
}

.session-list {
    flex: 1;
    min-height: 0;
    padding-block: var(--wa-space-2xs);
}

/* Remove default focus outline on the list - we show highlight on items instead */
.session-list:focus {
    outline: none;
}

/* Gap between items (non-compact mode only).
   Targets the child component's root element via Vue's scoped CSS inheritance. */
.session-list-container:not(.session-list-container--compact) :deep(.session-item-wrapper) {
    margin-block: var(--wa-space-3xs);
}

/* Divider rendered below the "extra" selected session at the very top of the
   list, and below the cross-filter pinned block (pinned sessions not
   naturally in scope) when either is present. */
.session-list-group-divider {
    --width: var(--divider-size);
    --spacing: var(--wa-space-2xs);
}

.load-more-indicator {
    display: flex;
    justify-content: center;
    padding: var(--wa-space-s);
    flex-shrink: 0;
}

.load-more-error {
    padding: var(--wa-space-s);
    flex-shrink: 0;
}

.load-more-error wa-callout {
    --wa-callout-padding: var(--wa-space-s);
}

.load-more-error wa-callout span {
    font-size: var(--wa-font-size-s);
}

.empty-state {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: var(--wa-space-l);
    color: var(--wa-color-text-quiet);
    font-size: var(--wa-font-size-l);
}
</style>
