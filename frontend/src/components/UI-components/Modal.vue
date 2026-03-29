<template>
    <Transition name="modal-fade" appear>
        <div ref="backdropRef" class="modal-backdrop" @click.self="emit('close')">
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
import { onBeforeUnmount, ref } from 'vue';

const props = defineProps({
    disableLeaveAnimation: { type: Boolean, default: false },
});

const emit = defineEmits(['close']);
const backdropRef = ref(null);

const MODAL_LEAVE_DURATION_MS = 300;

onBeforeUnmount(() => {
    if (typeof window === 'undefined') {
        return;
    }

    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
        return;
    }

    const backdropEl = backdropRef.value;
    if (!backdropEl || !document.body) {
        return;
    }

    if (props.disableLeaveAnimation) {
        return;
    }

    const detachedBackdrop = backdropEl.cloneNode(true);
    detachedBackdrop.classList.add('modal-backdrop--detached');
    detachedBackdrop.setAttribute('aria-hidden', 'true');
    document.body.appendChild(detachedBackdrop);

    requestAnimationFrame(() => {
        detachedBackdrop.classList.add('is-leaving');
    });

    window.setTimeout(() => {
        detachedBackdrop.remove();
    }, MODAL_LEAVE_DURATION_MS);
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/components/ui-components/modal.scss' as *;
</style>
