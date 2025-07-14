<template>
	<div>
		<div class="theme-toggle-wrapper">
			<ThemeToggle />
		</div>
		<router-view />
	</div>
</template>

<script setup>
import ThemeToggle from '@/components/ThemeToggle.vue'
</script>

<style lang="scss">
.theme-toggle-wrapper {
	position: absolute;
	top: 20px;
	right: 20px;
}
</style>