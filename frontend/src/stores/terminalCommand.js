/**
 * Pending-command queue for terminal contexts.
 *
 * Lets any component request "open a terminal in the <contextKey> view and
 * run this command". The matching ``TerminalPanel`` instance watches its
 * own ``contextKey`` slot and consumes the command when it's ready.
 *
 * Currently used by the "Launch in terminal" button on the Claude CLI
 * "not authenticated" toast and sidebar callout.
 */
import { defineStore } from 'pinia'

export const useTerminalCommandStore = defineStore('terminalCommand', {
    state: () => ({
        /**
         * contextKey (e.g. ``'global'``) -> ``{ snippet: string, appendEnter: bool }``
         * Absent key means no pending command for that context.
         */
        pending: {},
    }),
    actions: {
        /**
         * Queue a command for the given terminal context. The next
         * matching ``TerminalPanel`` to observe this entry will pick it up
         * and execute it (opening a new terminal tab, or reusing the
         * default ``Main`` tab if it has never been started).
         */
        request(contextKey, snippet, { appendEnter = true } = {}) {
            this.pending = { ...this.pending, [contextKey]: { snippet, appendEnter } }
        },
        /**
         * Atomically read and clear the pending command for a context.
         * Returns the entry, or ``null`` if nothing was queued.
         */
        take(contextKey) {
            const entry = this.pending[contextKey]
            if (!entry) return null
            const next = { ...this.pending }
            delete next[contextKey]
            this.pending = next
            return entry
        },
    },
})
