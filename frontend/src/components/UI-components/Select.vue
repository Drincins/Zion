<template>
    <div ref="root" class="input input-select">
        <label v-if="label" class="input-label" :for="triggerId">
            {{ label }}
        </label>
        <button
            :id="triggerId"
            type="button"
            v-bind="attrs"
            class="input-field input-field--select"
            :aria-expanded="isOpen.toString()"
            aria-haspopup="listbox"
            :aria-controls="listId"
            @click="toggle"
            @keydown="onTriggerKeydown"
        >
            <span :class="['input-select__value', { 'is-placeholder': !selectedOption }]">
                {{ selectedLabel }}
            </span>
            <span :class="['input-select__icon', { 'is-open': isOpen }]">▾</span>
        </button>
        <Teleport to="body">
            <Transition name="input-select">
                <ul
                    v-if="isOpen"
                    :id="listId"
                    ref="list"
                    class="input-select__list"
                    role="listbox"
                    :aria-labelledby="triggerId"
                    :style="listStyle"
                >
                    <li
                        v-if="searchable"
                        class="input-select__search"
                        role="presentation"
                    >
                        <input
                            :id="searchId"
                            ref="searchInput"
                            v-model="searchValue"
                            :name="searchName"
                            type="text"
                            class="input-select__search-input"
                            :placeholder="searchPlaceholder"
                            :aria-label="searchAriaLabel"
                            @keydown.stop
                        >
                    </li>
                    <li
                        v-for="option in visibleOptions"
                        :key="option.value"
                        :class="[
                            'input-select__option',
                            option.className,
                            {
                                'is-selected': isSelected(option.value),
                                'input-select__option--warning': option.warning,
                            },
                        ]"
                        role="option"
                        :aria-selected="isSelected(option.value)"
                        @click="selectOption(option.value)"
                    >
                        {{ option.label ?? option.value }}
                    </li>
                </ul>
            </Transition>
        </Teleport>
    </div>
</template>

<script setup>
import { computed, nextTick, ref, useAttrs, watch } from 'vue';
import { useFloatingPanel } from '@/composables/useFloatingPanel';

defineOptions({ inheritAttrs: false });

const { modelValue, label, id, options, placeholder, searchable, searchPlaceholder } = defineProps({
    modelValue: { type: [String, Number], default: null },
    label: { type: String, default: '' },
    id: { type: String, default: '' },
    options: { type: Array, required: true },
    placeholder: { type: String, default: '— Выберите —' },
    searchable: { type: Boolean, default: false },
    searchPlaceholder: { type: String, default: 'Поиск' },
});

const emit = defineEmits(['update:modelValue', 'search']);
const attrs = useAttrs();
const root = ref(null);
const list = ref(null);
const searchInput = ref(null);
const isOpen = ref(false);
const searchValue = ref('');

const triggerUid = `select-trigger-${Math.random().toString(36).slice(2, 9)}`;
const triggerId = computed(() => {
    if (id && String(id).trim() !== '') {
        return String(id);
    }
    return triggerUid;
});
const listUid = `select-listbox-${Math.random().toString(36).slice(2, 9)}`;
const listId = computed(() => {
    const currentId = triggerId.value;
    if (currentId) {
        return `${currentId}-listbox`;
    }
    return listUid;
});
const searchId = computed(() => `${listId.value}-search`);
const searchName = computed(() => searchId.value);
const searchAriaLabel = computed(() => {
    if (label && String(label).trim() !== '') {
        return `${label}: search`;
    }
    return 'Search';
});

const selectedOption = computed(() =>
    options.find((option) => String(option.value) === String(modelValue)),
);

const selectedLabel = computed(() => selectedOption.value?.label ?? placeholder);

const visibleOptions = computed(() => {
    if (!searchable) {
        return options;
    }
    const query = searchValue.value.trim().toLowerCase();
    if (!query) {
        return options;
    }
    return options.filter((option) => {
        const labelValue = option?.label ?? option?.value ?? '';
        return String(labelValue).toLowerCase().includes(query);
    });
});

function isSelected(value) {
    return String(value) === String(modelValue);
}

function toggle() {
    if (attrs.disabled !== undefined && attrs.disabled !== false) {
        return;
    }
    isOpen.value = !isOpen.value;
}

function close() {
    isOpen.value = false;
}

const { floatingStyle: listStyle, updateFloatingPosition } = useFloatingPanel({
    rootRef: root,
    panelRef: list,
    isOpen,
    triggerSelector: '.input-field--select',
    onRequestClose: close,
    computeStyle: ({ rect, panelElement, viewportHeight }) => {
        const maxHeight = 240;
        const listHeight = panelElement ? panelElement.scrollHeight : maxHeight;
        const spaceBelow = viewportHeight - rect.bottom - 6;
        const spaceAbove = rect.top - 6;
        const showAbove = spaceBelow < Math.min(maxHeight, listHeight) && spaceAbove > spaceBelow;
        const available = showAbove ? spaceAbove : spaceBelow;
        const safeAvailable = Math.max(0, available);
        const height = safeAvailable < 120 ? safeAvailable : Math.min(maxHeight, safeAvailable);
        const top = showAbove ? rect.top - height - 6 : rect.bottom + 6;

        return {
            top: `${Math.max(6, top)}px`,
            left: `${Math.max(6, rect.left)}px`,
            width: `${Math.max(140, rect.width)}px`,
            '--select-max-height': `${height}px`
        };
    }
});

function selectOption(value) {
    emit('update:modelValue', value === 'null' ? null : value);
    if (searchable) {
        searchValue.value = '';
    }
    close();
}

function onTriggerKeydown(event) {
    if (event.key === 'Escape') {
        close();
        return;
    }
    if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        if (!isOpen.value) {
            isOpen.value = true;
        }
    }
}

watch(isOpen, async (value) => {
    if (value) {
        await nextTick();
        if (searchable && searchInput.value) {
            searchInput.value.focus();
        }
    } else {
        if (searchable) {
            searchValue.value = '';
        }
    }
});

watch(searchValue, (value) => {
    if (!searchable) return;
    emit('search', value);
    nextTick(() => {
        updateFloatingPosition();
    });
});
</script>

<style lang="scss">
@use '@/assets/styles/components/ui-components/input.scss' as *;
</style>
