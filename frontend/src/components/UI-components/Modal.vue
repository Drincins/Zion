<template>
    <Transition name="modal-fade" appear>
        <div class="modal-backdrop" @click.self="emit('close')">
            <div class="modal-window">
                <header class="modal-header">
                    <slot name="header" />
                </header>
                <section class="modal-body">
                    <slot />
                </section>
                <footer class="modal-footer">
                    <slot name="footer" />
                </footer>
            </div>
        </div>
    </Transition>
</template>

<script setup>
const emit = defineEmits(['close']);
</script>

<style scoped lang="scss">
@use '@/assets/styles/components/ui-components/modal.scss' as *;
</style>
