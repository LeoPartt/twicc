<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useDataStore } from '../stores/data'
import { useSettingsStore } from '../stores/settings'
import { formatDate } from '../utils/date'
import { SESSION_TIME_FORMAT } from '../constants'
import { buildProjectTree } from '../utils/projectTree'
import ProjectEditDialog from './ProjectEditDialog.vue'
import ProjectBadge from './ProjectBadge.vue'
import ProjectProcessIndicator from './ProjectProcessIndicator.vue'
import ProjectTreeNode from './ProjectTreeNode.vue'
import ActivitySparkline from './ActivitySparkline.vue'
import CostDisplay from './CostDisplay.vue'
import AppTooltip from './AppTooltip.vue'

const store = useDataStore()
const settingsStore = useSettingsStore()

// Costs setting
const showCosts = computed(() => settingsStore.areCostsShown)

// Show archived projects setting
const showArchivedProjects = computed(() => settingsStore.isShowArchivedProjects)

// Session time format setting
const sessionTimeFormat = computed(() => settingsStore.getSessionTimeFormat)
const useRelativeTime = computed(() =>
    sessionTimeFormat.value === SESSION_TIME_FORMAT.RELATIVE_SHORT ||
    sessionTimeFormat.value === SESSION_TIME_FORMAT.RELATIVE_NARROW
)
const relativeTimeFormat = computed(() =>
    sessionTimeFormat.value === SESSION_TIME_FORMAT.RELATIVE_SHORT ? 'short' : 'narrow'
)

/**
 * Convert Unix timestamp (seconds) to Date object for wa-relative-time.
 * @param {number} timestamp - Unix timestamp in seconds
 * @returns {Date}
 */
function timestampToDate(timestamp) {
    return new Date(timestamp * 1000)
}

// Named projects (have a user-assigned name), sorted by mtime desc (from store)
const namedProjects = computed(() =>
    store.getProjects.filter(p => p.name !== null && (showArchivedProjects.value || !p.archived))
)

// Unnamed projects organized as a directory tree
const treeRoots = computed(() => {
    const unnamed = store.getProjects.filter(p => p.name === null && (showArchivedProjects.value || !p.archived))
    return buildProjectTree(unnamed)
})

const emit = defineEmits(['select'])

// Ref for the show-archived switch (Web Components need manual .checked sync)
const showArchivedSwitch = ref(null)

// Sync switch checked state with store value
watch(showArchivedProjects, () => {
    nextTick(() => {
        if (showArchivedSwitch.value && showArchivedSwitch.value.checked !== showArchivedProjects.value) {
            showArchivedSwitch.value.checked = showArchivedProjects.value
        }
    })
}, { immediate: true })

// Ref for the edit dialog component
const editDialogRef = ref(null)
// Currently selected project for editing
const editingProject = ref(null)

function handleSelect(project) {
    emit('select', project)
}

function handleMenuSelect(event, project) {
    const item = event.detail?.item
    if (!item) return
    if (item.value === 'edit') {
        editingProject.value = project
        editDialogRef.value?.open()
    } else if (item.value === 'archive') {
        store.setProjectArchived(project.id, true)
    } else if (item.value === 'unarchive') {
        store.setProjectArchived(project.id, false)
    }
}

function handleTreeMenuSelect(event, project) {
    // Same logic but event comes from tree node, no stopPropagation needed
    handleMenuSelect(event, project)
}

function handleToggleShowArchived(event) {
    settingsStore.setShowArchivedProjects(event.target.checked)
}
</script>

<template>
    <div class="project-list">
        <wa-switch
            ref="showArchivedSwitch"
            size="small"
            class="show-archived-toggle"
            @change="handleToggleShowArchived"
        >
            Show archived projects
        </wa-switch>

        <!-- Section 1: Named projects (flat, by mtime) -->
        <template v-if="namedProjects.length">
            <div class="section-header">Named projects</div>
            <wa-card
                v-for="project in namedProjects"
                :key="project.id"
                class="project-card"
                appearance="outlined"
                @click="handleSelect(project)"
            >
                <div class="project-info">
                    <div class="project-title-row">
                        <ProjectBadge :project-id="project.id" class="project-title" />
                        <ProjectProcessIndicator :project-id="project.id" size="small" />
                        <wa-tag v-if="project.archived" variant="neutral" size="small">Archived</wa-tag>
                    </div>
                    <div class="project-menu" @click.stop>
                        <wa-dropdown
                            placement="bottom-end"
                            @wa-select="(e) => handleMenuSelect(e, project)"
                        >
                            <wa-button
                                :id="`project-menu-trigger-${project.id}`"
                                slot="trigger"
                                variant="neutral"
                                appearance="plain"
                                size="small"
                            >
                                <wa-icon name="ellipsis" label="Project menu"></wa-icon>
                            </wa-button>
                            <wa-dropdown-item value="edit">
                                <wa-icon slot="icon" name="pencil"></wa-icon>
                                Edit
                            </wa-dropdown-item>
                            <wa-dropdown-item v-if="!project.archived" value="archive">
                                <wa-icon slot="icon" name="box-archive"></wa-icon>
                                Archive
                            </wa-dropdown-item>
                            <wa-dropdown-item v-if="project.archived" value="unarchive">
                                <wa-icon slot="icon" name="box-open"></wa-icon>
                                Unarchive
                            </wa-dropdown-item>
                        </wa-dropdown>
                        <AppTooltip :for="`project-menu-trigger-${project.id}`">Project actions</AppTooltip>
                    </div>
                    <div v-if="project.directory" class="project-directory">{{ project.directory }}</div>
                    <div class="project-meta-wrapper">
                        <div class="project-meta">
                            <span :id="`sessions-count-${project.id}`" class="sessions-count">
                                <wa-icon auto-width name="folder-open" variant="regular"></wa-icon>
                                <span>{{ project.sessions_count }} session{{ project.sessions_count !== 1 ? 's' : '' }}</span>
                            </span>
                            <AppTooltip :for="`sessions-count-${project.id}`">Number of sessions</AppTooltip>
                            <template v-if="showCosts">
                                <CostDisplay :id="`project-cost-${project.id}`" :cost="project.total_cost" class="project-cost" />
                                <AppTooltip :for="`project-cost-${project.id}`">Total project cost</AppTooltip>
                            </template>
                            <span :id="`project-mtime-${project.id}`" class="project-mtime">
                                <wa-icon auto-width name="clock" variant="regular"></wa-icon>
                                <wa-relative-time v-if="useRelativeTime" :date.prop="timestampToDate(project.mtime)" :format="relativeTimeFormat" numeric="always" sync></wa-relative-time>
                                <span v-else>{{ formatDate(project.mtime) }}</span>
                            </span>
                            <AppTooltip :for="`project-mtime-${project.id}`">{{ useRelativeTime ? `Last activity: ${formatDate(project.mtime)}` : 'Last activity' }}</AppTooltip>
                        </div>
                        <div :id="`project-sparkline-${project.id}`" class="project-graph">
                            <ActivitySparkline :id-suffix="project.id" :data="store.weeklyActivity[project.id] || []" />
                        </div>
                        <AppTooltip :for="`project-sparkline-${project.id}`">Project activity (message turns per week)</AppTooltip>
                    </div>
                </div>
            </wa-card>
        </template>

        <!-- Section 2: Unnamed projects (tree) -->
        <template v-if="treeRoots.length">
            <div v-if="namedProjects.length" class="section-header">Other projects</div>
            <ProjectTreeNode
                v-for="root in treeRoots"
                :key="root.project ? root.project.id : root.segment"
                :node="root"
                @select="handleSelect"
                @menu-select="handleTreeMenuSelect"
            />
        </template>

        <div v-if="namedProjects.length === 0 && treeRoots.length === 0" class="empty-state">
            No projects found
        </div>
    </div>

    <ProjectEditDialog ref="editDialogRef" :project="editingProject" />
</template>

<style scoped>
.project-list {
    display: flex;
    flex-direction: column;
    gap: var(--wa-space-m);
}

.project-card {
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    &::part(body) {
        position: relative;
    }
}

.project-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--wa-shadow-m);
}

.project-info {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: var(--wa-space-xs);
}

.project-title-row {
    display: flex;
    align-items: center;
    gap: var(--wa-space-xl);
}

.project-title {
    font-weight: 600;
    font-size: var(--wa-font-size-m);
    min-width: 0;
}

.project-menu {
    position: absolute;
    top: 0;
    right: 0;
}

.show-archived-toggle {
    align-self: flex-end;
    font-size: var(--wa-font-size-s);
}

.project-directory {
    font-size: var(--wa-font-size-s);
    color: var(--wa-color-text-quiet);
    word-break: break-all;
}

.project-meta-wrapper {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.project-meta {
    display: flex;
    justify-content: start;
    gap: var(--wa-space-m);
    font-size: var(--wa-font-size-s);
    color: var(--wa-color-text-quiet);

    & > span {
        display: flex;
        align-items: center;
        gap: var(--wa-space-xs);
    }

}

.section-header {
    font-size: var(--wa-font-size-s);
    font-weight: 600;
    color: var(--wa-color-text-quiet);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: var(--wa-space-xs) 0;
}

.empty-state {
    text-align: center;
    padding: var(--wa-space-xl);
    color: var(--wa-color-text-quiet);
    font-size: var(--wa-font-size-l);
}
</style>
