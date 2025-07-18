<template>
	<button
		:type="type"
		class="button"
		:disabled="disabled"
	>
		<slot />
	</button>
</template>

<script setup>
defineProps({
	type: {
		type: String,
		default: 'button',
	},
	disabled: {
		type: Boolean,
		default: false,
	},
})
</script>

<style lang="scss">
@use '@/assets/styles/components/ui-components/button.scss' as *;
</style>