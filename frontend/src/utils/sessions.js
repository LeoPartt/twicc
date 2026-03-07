// frontend/src/utils/sessions.js

/**
 * Compute the lifecycle cutoff timestamp (in ms) for a session.
 * Tools/agents started before this cutoff cannot be running — the session
 * was restarted or stopped since then.
 * Returns max(last_started_at, last_stopped_at) in ms, or 0 if unavailable.
 *
 * @param {Object} session - Session object with last_started_at / last_stopped_at
 * @returns {number} Cutoff in milliseconds (0 if no cutoff can be determined)
 */
export function getSessionCutoffMs(session) {
    if (!session?.last_started_at) return 0
    const started = new Date(session.last_started_at).getTime()
    const stopped = session.last_stopped_at ? new Date(session.last_stopped_at).getTime() : 0
    return Math.max(started, stopped)
}
