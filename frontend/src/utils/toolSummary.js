/**
 * Pure utilities for tool input summarization.
 *
 * Used by:
 *   - ToolUseContent.vue           — per-tool card (rich rendering)
 *   - WorkingAssistantMessage.vue  — "Claude is …" status line (inline rendering)
 *
 * Keep this file free of Vue/store imports so HMR cycles don't form
 * (see CLAUDE.md "Avoiding Circular Imports").
 */

import { getIconUrl, getFileIconId } from './fileIcons'
import { getTodoDescription, isValidTodos } from './todoList'

const FILE_PATH_TOOLS = new Set(['Edit', 'Write', 'Read'])
const AGENT_TOOL_NAMES = new Set(['Task', 'Agent'])

const TASK_SUBAGENT_LABELS = {
    explore: 'exploring',
    plan: 'planning',
    bash: 'bashing',
}

/**
 * Make `path` relative to `baseDir` if it lives under it; otherwise return it unchanged.
 */
export function formatRelativePath(path, baseDir) {
    if (!path) return path
    if (baseDir && path.startsWith(baseDir + '/')) {
        return path.slice(baseDir.length + 1)
    }
    return path
}

function capitalize(str) {
    return str.replace(/-/g, ' ').replace(/^\w/, c => c.toUpperCase())
}

/**
 * Display name override for a tool (Task subagent_type, Skill name).
 * Returns { name, namespace } or null if the regular tool name should be shown.
 */
export function getDisplayName(name, input) {
    if (AGENT_TOOL_NAMES.has(name)) {
        const sat = input?.subagent_type
        if (!sat || sat === 'general-purpose') return null
        const colonIdx = sat.indexOf(':')
        if (colonIdx >= 0) {
            return {
                name: capitalize(sat.slice(colonIdx + 1)),
                namespace: capitalize(sat.slice(0, colonIdx)),
            }
        }
        return { name: capitalize(sat), namespace: null }
    }
    if (name === 'Skill' && input?.skill) {
        const skill = input.skill
        const colonIdx = skill.indexOf(':')
        if (colonIdx >= 0) {
            return {
                name: capitalize(skill.slice(colonIdx + 1)),
                namespace: capitalize(skill.slice(0, colonIdx)),
            }
        }
        return { name: capitalize(skill), namespace: null }
    }
    return null
}

/**
 * Convert a tool name + input to a gerund form.
 *
 *   Task / Agent      → subagent_type-derived label ("exploring", "planning",
 *                       "bashing", "agenting")
 *   mcp__server__tool → "mcping (server)"
 *   generic           → lower-case, strip trailing vowels, append "ing"
 */
export function getVerb(name, input) {
    if (!name) return null
    if (AGENT_TOOL_NAMES.has(name)) {
        const subtype = input?.subagent_type?.toLowerCase()
        if (subtype && TASK_SUBAGENT_LABELS[subtype]) {
            return TASK_SUBAGENT_LABELS[subtype]
        }
        return 'agenting'
    }
    if (name.startsWith('mcp__')) {
        const parts = name.split('__')
        const server = parts[1] || 'mcp'
        return `mcping (${server})`
    }
    const lower = name.toLowerCase()
    return lower.replace(/[aeiou]+$/, '') + 'ing'
}

function fileIconFor(filePath) {
    if (!filePath) return null
    const filename = filePath.split('/').pop() || filePath
    const iconId = getFileIconId(filename)
    return iconId !== 'default-file' ? getIconUrl(iconId) : null
}

function buildGrepInline(pattern, fileType, path) {
    const parts = []
    if (pattern) parts.push(pattern)
    if (fileType) parts.push(`in ${fileType} files`)
    if (path) parts.push(`in ${path}`)
    return parts.length ? parts.join(' ') : null
}

function emptyRich(kind = null, overrides = {}) {
    return {
        kind,
        description: null,
        fileIconSrc: null,
        skill: null,
        grep: null,
        globPattern: null,
        webFetchUrl: null,
        webSearchQuery: null,
        toolSearchQuery: null,
        todoDescription: null,
        ...overrides,
    }
}

/**
 * Compute structured + inline summary for a tool_use input.
 *
 * @param {string} name         Tool name (e.g. "Read", "mcp__foo__bar").
 * @param {object} input        Tool input dict (already filtered server-side for some tools).
 * @param {string|null} baseDir Session base dir (git_directory || cwd) for relative paths.
 * @returns {object}            See module docblock for shape.
 */
export function computeToolSummary(name, input, baseDir) {
    const safeInput = input || {}
    const displayName = getDisplayName(name, safeInput)

    // File-path tools ───────────────────────────────────────────────
    if (FILE_PATH_TOOLS.has(name) && safeInput.file_path) {
        const description = formatRelativePath(safeInput.file_path, baseDir)
        return {
            displayName,
            inline: description,
            rich: emptyRich('description', {
                description,
                fileIconSrc: fileIconFor(safeInput.file_path),
            }),
        }
    }

    // Skill ────────────────────────────────────────────────────────
    if (name === 'Skill' && displayName) {
        return {
            displayName,
            inline: displayName.name,
            rich: emptyRich('skill', { skill: displayName }),
        }
    }

    // Grep ─────────────────────────────────────────────────────────
    if (name === 'Grep') {
        const pattern = safeInput.pattern || null
        const fileType = safeInput.type || safeInput.glob || null
        const rawPath = safeInput.path || null
        if (pattern || fileType || rawPath) {
            const path = rawPath ? formatRelativePath(rawPath, baseDir) : null
            const pathIconSrc = rawPath ? fileIconFor(rawPath) : null
            return {
                displayName,
                inline: buildGrepInline(pattern, fileType, path),
                rich: emptyRich('grep', {
                    grep: { pattern, fileType, path, pathIconSrc },
                }),
            }
        }
    }

    // Glob ─────────────────────────────────────────────────────────
    if (name === 'Glob' && safeInput.pattern) {
        return {
            displayName,
            inline: safeInput.pattern,
            rich: emptyRich('glob', { globPattern: safeInput.pattern }),
        }
    }

    // WebFetch ─────────────────────────────────────────────────────
    if (name === 'WebFetch' && safeInput.url) {
        return {
            displayName,
            inline: safeInput.url,
            rich: emptyRich('webFetch', { webFetchUrl: safeInput.url }),
        }
    }

    // WebSearch ────────────────────────────────────────────────────
    if (name === 'WebSearch' && safeInput.query) {
        return {
            displayName,
            inline: safeInput.query,
            rich: emptyRich('webSearch', { webSearchQuery: safeInput.query }),
        }
    }

    // ToolSearch ───────────────────────────────────────────────────
    if (name === 'ToolSearch' && safeInput.query) {
        return {
            displayName,
            inline: safeInput.query,
            rich: emptyRich('toolSearch', { toolSearchQuery: safeInput.query }),
        }
    }

    // TodoWrite ────────────────────────────────────────────────────
    if (name === 'TodoWrite' && isValidTodos(safeInput.todos)) {
        return {
            displayName,
            inline: null,
            rich: emptyRich('todo', {
                todoDescription: getTodoDescription(safeInput.todos),
            }),
        }
    }

    // Generic / fallback (Task with no displayName, Bash, MCP, …) ─
    const description = safeInput.description || null
    return {
        displayName,
        inline: description,
        rich: emptyRich(description ? 'description' : null, { description }),
    }
}
