<script setup>
// ProjectDetailPanel.vue - Detail panel shown when no session is selected.
// Delegates header display to ProjectDetailHeader, then shows tabbed content.

import { ref, computed, onActivated, onDeactivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ALL_PROJECTS_ID, useDataStore } from '../stores/data'
import { useWorkspacesStore } from '../stores/workspaces'
import { isWorkspaceProjectId, extractWorkspaceId } from '../utils/workspaceIds'
import ProjectDetailHeader from './ProjectDetailHeader.vue'
import ContributionGraphs from './ContributionGraphs.vue'
import TerminalPanel from './TerminalPanel.vue'

const props = defineProps({
    /** Project ID or ALL_PROJECTS_ID for aggregate view */
    projectId: {
        type: String,
        required: true,
    },
    /** Whether this panel is currently visible (not hidden behind a session view) */
    active: {
        type: Boolean,
        default: true,
    },
})

const dataStore = useDataStore()
const workspacesStore = useWorkspacesStore()

// KeepAlive lifecycle — track whether this instance is active (not cached)
const isKeptAlive = ref(true)
onActivated(() => { isKeptAlive.value = true })
onDeactivated(() => { isKeptAlive.value = false })

// Effective active state: visible AND not deactivated by KeepAlive
const isActive = computed(() => props.active && isKeptAlive.value)

// Workspace project IDs (needed for ContributionGraphs)
const isWorkspaceMode = computed(() => isWorkspaceProjectId(props.projectId))
const workspaceId = computed(() => isWorkspaceMode.value ? extractWorkspaceId(props.projectId) : null)
const workspaceProjectIds = computed(() =>
    workspaceId.value ? workspacesStore.getVisibleProjectIds(workspaceId.value) : null
)

const terminalContextKey = computed(() => {
    if (props.projectId === ALL_PROJECTS_ID) {
        return 'global'
    }
    if (isWorkspaceProjectId(props.projectId)) {
        return `w:${extractWorkspaceId(props.projectId)}`
    }
    return `p:${props.projectId}`
})

// For project terminals, pass the real project ID (not workspace/all-projects pseudo-IDs)
const terminalProjectId = computed(() => {
    if (props.projectId === ALL_PROJECTS_ID || isWorkspaceProjectId(props.projectId)) {
        return null
    }
    return props.projectId
})

// For workspace terminals, compute the lowest common ancestor of all project directories
const terminalCwd = computed(() => {
    if (!isWorkspaceMode.value || !workspaceProjectIds.value) return null
    const dirs = workspaceProjectIds.value
        .map(pid => dataStore.getProject(pid))
        .map(p => p?.directory)
        .filter(Boolean)
    if (dirs.length === 0) return null
    if (dirs.length === 1) return dirs[0]
    // Find the longest common path prefix
    const parts = dirs.map(d => d.split('/'))
    const common = []
    for (let i = 0; i < parts[0].length; i++) {
        const segment = parts[0][i]
        if (parts.every(p => p[i] === segment)) {
            common.push(segment)
        } else {
            break
        }
    }
    return common.length > 1 ? common.join('/') : '/'
})

// Tab management — derived from route (like SessionView)
const route = useRoute()
const router = useRouter()
const headerRef = ref(null)

const TABS = [
    { id: 'stats', label: 'Stats', icon: 'chart-simple' },
    { id: 'terminal', label: 'Terminal', icon: 'terminal' },
]

// Active tab derived from the route name
const isAllProjectsMode = computed(() => route.name?.startsWith('projects-'))
const activeTab = computed(() => {
    const name = route.name
    if (name === 'project-terminal' || name === 'projects-terminal') return 'terminal'
    return 'stats'
})

const activeTabLabel = computed(() => {
    const tab = TABS.find(t => t.id === activeTab.value)
    return tab?.label ?? null
})

function switchToTab(tabId) {
    if (tabId === activeTab.value) return
    if (tabId === 'terminal') {
        router.push({
            name: isAllProjectsMode.value ? 'projects-terminal' : 'project-terminal',
            params: isAllProjectsMode.value ? {} : { projectId: props.projectId },
            query: route.query,
        })
    } else {
        // Stats = default route (no suffix)
        router.push({
            name: isAllProjectsMode.value ? 'projects-all' : 'project',
            params: isAllProjectsMode.value ? {} : { projectId: props.projectId },
            query: route.query,
        })
    }
}

function switchToTabAndCollapse(tabId) {
    switchToTab(tabId)
    if (headerRef.value?.isCompactExpanded) {
        headerRef.value.isCompactExpanded = false
    }
}

function onTabShow(event) {
    const panel = event.detail?.name
    // Only handle events from our own tabs (not from nested tab-groups like TerminalPanel's)
    if (panel && TABS.some(t => t.id === panel)) switchToTab(panel)
}
</script>

<template>
    <div class="project-detail-panel">
        <ProjectDetailHeader ref="headerRef" :project-id="projectId" :active-tab-label="activeTabLabel">
            <template #compact-extra>
                <div class="compact-tab-nav">
                    <wa-button
                        v-for="tab in TABS"
                        :key="tab.id"
                        size="small"
                        :variant="activeTab === tab.id ? 'brand' : 'neutral'"
                        :appearance="activeTab === tab.id ? 'outlined' : 'plain'"
                        @click="switchToTabAndCollapse(tab.id)"
                    >
                        <wa-icon :name="tab.icon" slot="prefix"></wa-icon>
                        {{ tab.label }}
                    </wa-button>
                </div>
            </template>
        </ProjectDetailHeader>

        <wa-divider></wa-divider>

        <wa-tab-group
            :active="activeTab"
            class="detail-tabs"
            @wa-tab-show="onTabShow"
        >
            <wa-tab v-for="tab in TABS" :key="tab.id" slot="nav" :panel="tab.id">
                <wa-button
                    :appearance="activeTab === tab.id ? 'outlined' : 'plain'"
                    :variant="activeTab === tab.id ? 'brand' : 'neutral'"
                    size="small"
                >
                    {{ tab.label }}
                </wa-button>
            </wa-tab>

            <wa-tab-panel name="stats">
                <ContributionGraphs :project-id="projectId" :project-ids="workspaceProjectIds" />
            </wa-tab-panel>

            <wa-tab-panel name="terminal">
                <TerminalPanel
                    :context-key="terminalContextKey"
                    :project-id="terminalProjectId"
                    :cwd="terminalCwd"
                    :active="isActive && activeTab === 'terminal'"
                />
            </wa-tab-panel>
        </wa-tab-group>
    </div>
</template>

<style scoped>
.project-detail-panel {
    container: project-detail / inline-size;
    display: flex;
    flex-direction: column;
    height: 100%;
    padding-top: var(--wa-space-s);
    width: 100%;
    overflow: hidden;
}

wa-divider {
    --spacing: 0;
    --width: 4px;
}

.detail-tabs {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    --indicator-color: transparent;
    --track-width: 4px;
}

.detail-tabs::part(base) {
    height: 100%;
    overflow: hidden;
}

.detail-tabs::part(body) {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.detail-tabs :deep(wa-tab-panel::part(base)) {
    padding: 0;
}

wa-tab::part(base) {
    padding: var(--wa-space-xs);
}

.detail-tabs :deep(wa-tab-panel[active]) {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
}

.detail-tabs :deep(wa-tab-panel[active])::part(base) {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
}

/* Compact tab nav: hidden by default, shown in compact overlay */
.compact-tab-nav {
    display: none;
}

@media (max-height: 900px) {
    .project-detail-panel {
        padding-top: 0;
    }

    /* Hide the divider and normal tab-group nav */
    wa-divider {
        display: none;
    }

    .detail-tabs::part(nav) {
        display: none;
    }

    /* Show the compact tab nav inside the header overlay */
    .compact-tab-nav {
        display: flex;
        align-items: center;
        gap: var(--wa-space-xs);
        padding-inline: var(--wa-space-xs);
        padding-bottom: var(--wa-space-xs);
    }
}
</style>
