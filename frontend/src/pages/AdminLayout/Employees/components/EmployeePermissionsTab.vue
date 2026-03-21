<template>
    <div class="employees-page__permissions">
        <div class="employees-page__permissions-toolbar">
            <Input
                v-model="searchQuery"
                label="Поиск по правам"
                placeholder="Введите код или название"
            />
            <Select
                v-model="groupFilter"
                label="Группа"
                :options="groupOptions"
            />
        </div>
        <div v-if="catalogLoading || loading" class="employees-page__permissions-state">
            Загружаем права...
        </div>
        <div v-else-if="!permissions.length" class="employees-page__permissions-state">
            Нет доступных прав. Проверьте настройки каталога.
        </div>
        <div v-else>
            <div v-if="!filteredPermissions.length" class="employees-page__permissions-state">
                По фильтрам ничего не найдено.
            </div>
            <div v-else class="employees-page__permissions-table-wrapper">
                <Table class="employees-page__permissions-table">
                    <thead>
                        <tr>
                            <th>Право</th>
                            <th>Группа</th>
                            <th>Описание</th>
                            <th class="employees-page__permissions-actions-header">Доступ</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="permission in filteredPermissions" :key="permission.code">
                            <td>
                                <div class="employees-page__permission-name">
                                    <span class="employees-page__permission-label">
                                        {{ permission.label || permission.code }}
                                    </span>
                                </div>
                            </td>
                            <td>{{ permission.group || '—' }}</td>
                            <td class="employees-page__permission-description">
                                {{ permission.description || '—' }}
                            </td>
                            <td class="employees-page__permissions-actions">
                                <Checkbox
                                    :model-value="assignedSet.has(permission.code)"
                                    :disabled="!canManage || pendingMap[permission.code] || loading || catalogLoading"
                                    @update:model-value="(checked) => handleToggle(permission.code, checked)"
                                />
                            </td>
                        </tr>
                    </tbody>
                </Table>
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed, ref, toRefs } from 'vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import Input from '@/components/UI-components/Input.vue';
import Select from '@/components/UI-components/Select.vue';
import Table from '@/components/UI-components/Table.vue';

const props = defineProps({
    permissions: { type: Array, default: () => [] },
    assignedCodes: { type: Array, default: () => [] },
    pendingCodes: { type: Object, default: () => ({}) },
    loading: { type: Boolean, default: false },
    catalogLoading: { type: Boolean, default: false },
    canManage: { type: Boolean, default: false },
});

const emit = defineEmits(['toggle-permission']);

const { permissions, assignedCodes, pendingCodes, loading, catalogLoading, canManage } =
    toRefs(props);

const searchQuery = ref('');
const groupFilter = ref('');

const assignedSet = computed(() => {
    const set = new Set();
    for (const code of assignedCodes.value || []) {
        if (typeof code === 'string' && code.trim()) {
            set.add(code.trim());
        }
    }
    return set;
});

const pendingMap = computed(() => pendingCodes.value || {});

const groupOptions = computed(() => {
    const groups = new Set();
    for (const permission of permissions.value || []) {
        if (permission?.group) {
            groups.add(permission.group);
        }
    }
    const list = Array.from(groups).sort((a, b) => a.localeCompare(b, 'ru', { sensitivity: 'base' }));
    return [
        { value: '', label: 'Все группы' },
        ...list.map((group) => ({ value: group, label: group })),
    ];
});

const filteredPermissions = computed(() => {
    const query = searchQuery.value.trim().toLowerCase();
    const group = groupFilter.value.trim().toLowerCase();
    return (permissions.value || []).filter((permission) => {
        const matchesGroup = group
            ? (permission.group || '').toLowerCase() === group
            : true;
        if (!matchesGroup) {
            return false;
        }
        if (!query) {
            return true;
        }
        const haystack = `${permission.label} ${permission.code} ${permission.description || ''}`.toLowerCase();
        return haystack.includes(query);
    });
});

function handleToggle(code, checked) {
    emit('toggle-permission', { code, checked });
}
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/employees-permissions-tab' as *;
</style>
