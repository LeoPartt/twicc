<script setup>
defineProps({
    customTitle: {
        type: String,
        required: true
    }
})
</script>

<template>
    <wa-details class="item-details custom-title no-details" icon-placement="start">
        <span slot="summary" class="items-details-summary">
            <strong class="items-details-summary-name">Session title changed</strong>
            <span class="items-details-summary-separator"> — </span>
            <span class="items-details-summary-description">{{ customTitle }}</span>
        </span>
    </wa-details>
</template>
