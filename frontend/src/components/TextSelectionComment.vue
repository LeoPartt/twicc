<script setup>
// TextSelectionComment.vue — Ephemeral floating widget for commenting on selected
// text in the session view. Shows a small button on text selection; clicking it
// expands a panel with a textarea + "Add to message" action. Nothing is persisted
// to IndexedDB — the user must send the message right away.

import { ref, inject, nextTick, computed, onMounted, onBeforeUnmount } from 'vue'
import { formatComment } from '../stores/codeComments'

const props = defineProps({
    /** The text the user selected in the session view. */
    selectedText: { type: String, required: true },
    /** Viewport-relative position: { top, left } — bottom-center of the selection. */
    position: { type: Object, required: true },
})

const emit = defineEmits(['close'])

const insertTextAtCursor = inject('insertTextAtCursor', null)

const expanded = ref(false)
const commentText = ref('')
const textareaRef = ref(null)
const rootRef = ref(null)

// Pixel offsets applied after measuring the expanded panel to keep it within the viewport.
const positionAdjust = ref({ dx: 0, dy: 0 })

const rootStyle = computed(() => {
    const base = { top: props.position.top + 'px', left: props.position.left + 'px' }
    if (expanded.value) {
        // Override the CSS transform with clamped offsets
        const { dx, dy } = positionAdjust.value
        base.transform = `translate(calc(-50% + ${dx}px), calc(4px + ${dy}px))`
    }
    return base
})

const canAdd = computed(() => !!commentText.value.trim() && !!insertTextAtCursor)

/**
 * After the panel renders, measure its bounding rect and nudge it so it stays
 * fully visible inside the viewport (with an 8 px margin on every side).
 */
function clampToViewport() {
    const el = rootRef.value
    if (!el) return

    const rect = el.getBoundingClientRect()
    const margin = 8
    const vw = window.innerWidth
    const vh = window.innerHeight

    let dx = 0
    let dy = 0

    // Horizontal
    if (rect.left < margin) dx = margin - rect.left
    else if (rect.right > vw - margin) dx = (vw - margin) - rect.right

    // Vertical
    if (rect.bottom > vh - margin) dy = (vh - margin) - rect.bottom
    if (rect.top + dy < margin) dy = margin - rect.top

    if (dx || dy) positionAdjust.value = { dx, dy }
}

function expand() {
    positionAdjust.value = { dx: 0, dy: 0 }
    expanded.value = true
    nextTick(() => {
        clampToViewport()
        textareaRef.value?.focus()
    })
}

function close() {
    emit('close')
}

function addToMessage() {
    if (!canAdd.value) return

    const formatted = formatComment(
        { lineText: props.selectedText, content: commentText.value },
        { isSelectedText: true },
    )
    insertTextAtCursor(formatted + '\n')
    close()
}

function handleKeydown(e) {
    if (e.key === 'Escape') {
        e.stopPropagation()
        close()
    }
}

// Close on any mousedown outside the widget
function handleDocumentMousedown(e) {
    if (rootRef.value?.contains(e.target)) return
    close()
}

onMounted(() => {
    document.addEventListener('mousedown', handleDocumentMousedown, true)
})

onBeforeUnmount(() => {
    document.removeEventListener('mousedown', handleDocumentMousedown, true)
})

defineExpose({ isExpanded: expanded })
</script>

<template>
    <div
        ref="rootRef"
        class="text-selection-comment"
        :class="{ expanded }"
        :style="rootStyle"
    >
        <!-- Collapsed: just the comment button -->
        <wa-button
            v-if="!expanded"
            class="tsc-trigger"
            variant="brand"
            appearance="filled-outlined"
            size="small"
            @mousedown.prevent
            @click.stop="expand"
        >
            <wa-icon name="comment" variant="regular"></wa-icon>
        </wa-button>

        <!-- Expanded: comment panel -->
        <div v-else class="tsc-panel" @keydown="handleKeydown">
            <!-- Selected text preview -->
            <div class="tsc-quote">{{ selectedText }}</div>

            <wa-textarea
                ref="textareaRef"
                :value="commentText"
                @input="commentText = $event.target.value"
                placeholder="Add a comment..."
                size="small"
                rows="3"
            ></wa-textarea>

            <div class="tsc-help">
                This comment is not saved — click "Add to message" once you're done writing.
            </div>

            <div class="tsc-actions">
                <wa-button size="small" variant="neutral" appearance="outlined" @click="close">
                    Cancel
                </wa-button>
                <wa-button
                    size="small"
                    variant="brand"
                    appearance="outlined"
                    :disabled="!canAdd"
                    @click="addToMessage"
                >
                    Add to message
                </wa-button>
            </div>
        </div>
    </div>
</template>

<style scoped>
.text-selection-comment {
    position: fixed;
    z-index: 10000;
    /* Anchor: bottom-center of the selection.
       Both button and panel appear below the selection. */
    transform: translate(-50%, 4px);
}

/* ── Panel ───────────────────────────────────────────────────────── */

.tsc-panel {
    width: 20rem;
    max-width: calc(100vw - 2rem);
    padding: var(--wa-space-s);
    background: var(--wa-color-surface-default);
    border: 1px solid var(--wa-color-surface-border);
    border-radius: var(--wa-border-radius-m);
    box-shadow: var(--wa-shadow-l);
    display: flex;
    flex-direction: column;
    gap: var(--wa-space-s);
}

/* ── Selected text quote ─────────────────────────────────────────── */

.tsc-quote {
    max-height: 4.8em; /* ~3 lines */
    padding: var(--wa-space-xs) var(--wa-space-xs);
    border-left: 3px solid var(--wa-color-brand);
    border-radius: var(--wa-border-radius-s);
    background: var(--wa-color-surface-lowered);
    font-size: var(--wa-font-size-s);
    line-height: 1.4;
    color: var(--wa-color-text-quiet);
    overflow: scroll;
    white-space: pre-wrap;
    word-break: break-word;
}

/* ── Help text ───────────────────────────────────────────────────── */

.tsc-help {
    font-size: var(--wa-font-size-xs);
    line-height: 1.3;
}

/* ── Actions ─────────────────────────────────────────────────────── */

.tsc-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: var(--wa-space-s);
    margin-top: var(--wa-space-xs);
}
</style>
