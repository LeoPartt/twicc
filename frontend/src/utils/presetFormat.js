import {
    CLAUDE_IN_CHROME_LABELS,
    CONTEXT_MAX_LABELS,
    EFFORT_LABELS,
    PERMISSION_MODE_LABELS,
    THINKING_LABELS,
    getModelLabel,
} from '../constants'

/**
 * Returns a single-line summary of the fields a preset forces, joined by " · ",
 * or "all default" when nothing is forced.
 */
export function formatPresetSummary(preset) {
    const parts = []
    if (preset.model !== null && preset.model !== undefined) {
        parts.push(`model: ${getModelLabel(preset.model)}`)
    }
    if (preset.context_max !== null && preset.context_max !== undefined) {
        parts.push(`context: ${CONTEXT_MAX_LABELS[preset.context_max] ?? preset.context_max}`)
    }
    if (preset.effort !== null && preset.effort !== undefined) {
        parts.push(`effort: ${EFFORT_LABELS[preset.effort] ?? preset.effort}`)
    }
    if (preset.thinking !== null && preset.thinking !== undefined) {
        parts.push(`thinking: ${THINKING_LABELS[String(preset.thinking)] ?? preset.thinking}`)
    }
    if (preset.permission_mode !== null && preset.permission_mode !== undefined) {
        parts.push(`permission: ${PERMISSION_MODE_LABELS[preset.permission_mode] ?? preset.permission_mode}`)
    }
    if (preset.claude_in_chrome !== null && preset.claude_in_chrome !== undefined) {
        parts.push(`chrome: ${CLAUDE_IN_CHROME_LABELS[String(preset.claude_in_chrome)] ?? preset.claude_in_chrome}`)
    }
    return parts.length === 0 ? 'all default' : parts.join(' · ')
}
