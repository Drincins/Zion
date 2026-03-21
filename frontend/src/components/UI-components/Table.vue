<template>
    <table class="table">
        <slot />
    </table>
</template>

<script setup>
// Этот компонент просто обертывает собственный элемент таблицы общим стилем.
</script>

<style lang="scss">
@use '@/assets/styles/components/ui-components/table.scss' as *;
</style>
