/**
 * Lightweight "mailbox" for passing a search query from the global SearchOverlay
 * to the in-session SessionSearchBar when navigating to a specific session.
 *
 * The SearchOverlay sets the pending search before router.push(); the target
 * SessionItemsList watches the ref and consumes it once the session is active.
 *
 * A simple reactive ref avoids timing issues (the target component may not be
 * mounted yet when the navigation starts) and URL pollution (no query params).
 */

import { ref } from 'vue'

/**
 * Pending in-session search request.
 * @type {import('vue').Ref<{ sessionId: string, query: string } | null>}
 */
export const pendingSessionSearch = ref(null)
