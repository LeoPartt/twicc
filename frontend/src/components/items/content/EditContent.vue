<script setup>
import { computed } from 'vue'
import { structuredPatch } from 'diff'
import MarkdownContent from '../../MarkdownContent.vue'

const props = defineProps({
    input: {
        type: Object,
        required: true
    }
})

/**
 * Generate a unified diff between old_string and new_string, split into separate blocks per hunk.
 * When there are multiple hunks, each gets a prelude showing per-hunk +added/-removed stats.
 */
const diffHunks = computed(() => {
    const oldStr = props.input.old_string ?? ''
    const newStr = props.input.new_string ?? ''
    const result = structuredPatch('', '', oldStr, newStr, '', '', { context: 3 })
    return result.hunks.map(hunk => {
        const lines = []
        for (const line of hunk.lines) {
            // Skip "No newline at end of file" markers
            if (line.startsWith('\\')) continue
            lines.push(line)
        }
        let added = 0
        let removed = 0
        for (const line of lines) {
            if (line.startsWith('+')) added++
            else if (line.startsWith('-')) removed++
        }
        return {
            added,
            removed,
            source: '```diff\n' + lines.join('\n') + '\n```'
        }
    })
})

const multipleHunks = computed(() => diffHunks.value.length > 1)

const isReplaceAll = computed(() => !!props.input.replace_all)
</script>

<template>
    <div class="edit-content">
        <div v-if="isReplaceAll" class="edit-replace-all">Replace all occurrences</div>
        <div v-for="(hunk, index) in diffHunks" :key="index" class="edit-hunk">
            <div v-if="multipleHunks" class="edit-hunk-prelude">
                <span class="diff-added">+{{ hunk.added }}</span>
                <span class="diff-removed">-{{ hunk.removed }}</span>
            </div>
            <MarkdownContent :source="hunk.source" />
        </div>
    </div>
</template>

<style scoped>
.edit-content {
    padding: var(--wa-space-xs) 0;
}

.edit-replace-all {
    font-size: var(--wa-font-size-s);
    color: var(--wa-color-text-quiet);
    font-style: italic;
    margin-bottom: var(--wa-space-xs);
}

.edit-hunk + .edit-hunk {
    margin-top: var(--wa-space-xs);
}

.edit-hunk-prelude {
    display: flex;
    gap: var(--wa-space-xs);
    font-size: var(--wa-font-size-xs);
    font-family: var(--wa-font-family-mono);
    font-weight: bold;
    padding: var(--wa-space-3xs) 0;

    .diff-added {
        color: var(--wa-color-success-50);
    }
    .diff-removed {
        color: var(--wa-color-danger-50);
    }
}

/* Hide the "DIFF" language label — always diff here, no need to show it */
.edit-content :deep(.markdown-body) {
    max-height: 20.25rem;
    overflow: auto;
}

/* Hide the "DIFF" language label — always diff here, no need to show it */
.edit-content :deep(pre.shiki[data-language="diff"]) {
    padding-top: 16px;
}
.edit-content :deep(pre.shiki[data-language="diff"]::before) {
    display: none;
}
</style>
