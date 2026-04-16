<script setup>
/**
 * StopProcessConfirmDialog - Confirmation dialog shown when stopping a process
 * that has active crons.
 *
 * Warns the user that active cron jobs will no longer trigger, and asks for
 * explicit confirmation before proceeding. Supports two modes:
 * - 'stop': just stop the process
 * - 'archive': stop the process and archive the session
 */
import { ref } from 'vue'

const emit = defineEmits(['confirm'])

const dialogRef = ref(null)
const mode = ref('stop')       // 'stop' | 'archive'
const cronCount = ref(0)

/**
 * Open the confirmation dialog.
 * @param {Object} options
 * @param {'stop'|'archive'} options.mode - Whether this is a stop-only or stop-and-archive action
 * @param {number} options.cronCount - Number of active crons on the session
 */
function open({ mode: m = 'stop', cronCount: c = 0 } = {}) {
    mode.value = m
    cronCount.value = c
    if (dialogRef.value) {
        dialogRef.value.open = true
    }
}

/**
 * Close the dialog without confirming.
 */
function close() {
    if (dialogRef.value) {
        dialogRef.value.open = false
    }
}

/**
 * User confirmed the action.
 */
function handleConfirm() {
    emit('confirm', { mode: mode.value })
    close()
}

defineExpose({ open, close })
</script>

<template>
    <wa-dialog
        ref="dialogRef"
        label="Active crons will be lost"
        class="stop-confirm-dialog"
    >
        <div class="dialog-content">
            <wa-callout variant="warning" size="small" open>
                <p>
                    This session has
                    <strong>{{ cronCount }} active cron{{ cronCount > 1 ? 's' : '' }}</strong>.
                </p>
                <p>
                    Stopping the process manually will cancel all active crons. They will not be
                    restored automatically when the process restarts.
                </p>
                <p>
                    You can always ask the agent to set them up again later.
                </p>
            </wa-callout>
        </div>

        <div slot="footer" class="dialog-footer">
            <wa-button variant="neutral" appearance="outlined" @click="close">
                Cancel, keep the process
            </wa-button>
            <wa-button variant="danger" appearance="filled" @click="handleConfirm">
                <wa-icon slot="start" name="ban"></wa-icon>
                {{ mode === 'archive' ? 'Stop and archive' : 'Stop the process' }}
            </wa-button>
        </div>
    </wa-dialog>
</template>

<style scoped>
.stop-confirm-dialog {
    --width: min(40rem, calc(100vw - 2rem));
}

.dialog-content {
    display: flex;
    flex-direction: column;
    gap: var(--wa-space-m);
}

.dialog-content p {
    margin: 0;
}

.dialog-content p + p {
    margin-top: var(--wa-space-s);
}

.dialog-footer {
    display: flex;
    flex-wrap: wrap;
    gap: var(--wa-space-s);
    justify-content: flex-end;
}
</style>
