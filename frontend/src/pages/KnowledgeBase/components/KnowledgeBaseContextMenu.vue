<template>
    <Teleport to="body">
        <Transition name="kb-menu">
            <div
                v-if="visible"
                ref="menuRef"
                class="kb-context-menu"
                :style="{ left: `${menuPosition.left}px`, top: `${menuPosition.top}px` }"
            >
                <button
                    v-for="item in items"
                    :key="item.key"
                    type="button"
                    class="kb-context-menu__item"
                    :class="{ 'is-danger': item.danger }"
                    :disabled="item.disabled"
                    @click="handleSelect(item)"
                >
                    {{ item.label }}
                </button>
            </div>
        </Transition>
    </Teleport>
</template>

<script setup>
import { nextTick, reactive, ref, watch } from 'vue';
import { useClickOutside } from '@/composables/useClickOutside';

const props = defineProps({
    visible: {
        type: Boolean,
        default: false,
    },
    x: {
        type: Number,
        default: 0,
    },
    y: {
        type: Number,
        default: 0,
    },
    items: {
        type: Array,
        default: () => [],
    },
});

const emit = defineEmits(['select', 'close']);
const menuRef = ref(null);
const menuPosition = reactive({
    left: 8,
    top: 8,
});

watch(
    () => [props.visible, props.x, props.y, props.items?.length],
    async () => {
        if (!props.visible) {
            return;
        }
        await nextTick();
        updateMenuPosition();
    },
);

function updateMenuPosition() {
    const padding = 8;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const menuRect = menuRef.value?.getBoundingClientRect();
    const menuWidth = menuRect?.width || 220;
    const menuHeight = menuRect?.height || 280;

    const nextLeft = Math.min(
        Math.max(props.x, padding),
        Math.max(padding, viewportWidth - menuWidth - padding),
    );
    const nextTop = Math.min(
        Math.max(props.y, padding),
        Math.max(padding, viewportHeight - menuHeight - padding),
    );

    menuPosition.left = nextLeft;
    menuPosition.top = nextTop;
}

useClickOutside(
    () => [
        {
            element: menuRef,
            when: () => props.visible,
            onOutside: () => emit('close'),
        }
    ],
    { eventName: 'mousedown' },
);

function handleSelect(item) {
    if (!item || item.disabled) {
        return;
    }
    emit('select', item.key);
}
</script>

<style scoped lang="scss">
.kb-context-menu {
    position: fixed;
    min-width: 190px;
    background: color-mix(in srgb, var(--color-surface) 96%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-border) 84%, transparent);
    border-radius: 12px;
    padding: 6px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    z-index: 80;
}

.kb-context-menu__item {
    border: none;
    background: transparent;
    color: var(--color-text);
    border-radius: 8px;
    text-align: left;
    padding: 8px 10px;
    font-size: 13px;
    cursor: pointer;
}

.kb-context-menu__item:hover:not(:disabled) {
    background: color-mix(in srgb, var(--color-primary) 16%, transparent);
}

.kb-context-menu__item:disabled {
    opacity: 0.7;
    cursor: default;
}

.kb-context-menu__item.is-danger {
    color: var(--color-danger);
}

.kb-menu-enter-active,
.kb-menu-leave-active {
    transition: opacity 0.14s ease, transform 0.14s ease;
}

.kb-menu-enter-from,
.kb-menu-leave-to {
    opacity: 0;
    transform: translateY(4px);
}
</style>
