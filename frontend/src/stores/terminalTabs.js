import { defineStore } from 'pinia'

export const useTerminalTabsStore = defineStore('terminalTabs', {
    state: () => ({
        // contextKey → sorted array of terminal indices from backend
        indices: {},
        // contextKey → { terminalIndex: label } — labels from tmux user options
        labels: {},
    }),
    actions: {
        setIndices(contextKey, terminalIndices) {
            this.indices[contextKey] = [...terminalIndices].sort((a, b) => a - b)
        },
        addIndex(contextKey, index) {
            if (!this.indices[contextKey]) {
                this.indices[contextKey] = [index]
                return
            }
            if (!this.indices[contextKey].includes(index)) {
                this.indices[contextKey] = [...this.indices[contextKey], index].sort((a, b) => a - b)
            }
        },
        removeIndex(contextKey, index) {
            if (this.indices[contextKey]) {
                this.indices[contextKey] = this.indices[contextKey].filter(i => i !== index)
            }
            if (this.labels[contextKey]) {
                delete this.labels[contextKey][index]
            }
        },
        setLabels(contextKey, labelsMap) {
            this.labels[contextKey] = {}
            for (const [index, label] of Object.entries(labelsMap)) {
                if (label) {
                    this.labels[contextKey][Number(index)] = label
                }
            }
        },
        setLabel(contextKey, index, label) {
            if (!this.labels[contextKey]) {
                this.labels[contextKey] = {}
            }
            if (label) {
                this.labels[contextKey][index] = label
            } else {
                delete this.labels[contextKey][index]
            }
        },
        getLabel(contextKey, index) {
            return this.labels[contextKey]?.[index] || ''
        },
    },
})
