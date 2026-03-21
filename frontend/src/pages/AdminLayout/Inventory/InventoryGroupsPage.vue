<template>
    <section class="inventory-page__section">
        <div class="inventory-page__section-header">
            <h2>Группы товаров</h2>
            <div class="catalog-tree__header-actions">
                <Button v-if="canCreateNomenclature" color="primary" size="sm" @click="openCreateModal">Создать новую группу</Button>
                <Button color="ghost" size="sm" :loading="loading" @click="loadTree">Обновить</Button>
            </div>
        </div>

        <div v-if="loading" class="inventory-page__loading">Загрузка структуры...</div>
        <div v-else-if="!sortedGroups.length" class="inventory-page__empty">Пока структура не заполнена.</div>

        <div v-else class="catalog-tree">
            <button type="button" class="catalog-tree__root" @click="isTreeExpanded = !isTreeExpanded">
                <span class="catalog-tree__caret">{{ isTreeExpanded ? '⌄' : '›' }}</span>
                <span class="catalog-tree__glyph" />
                <span class="catalog-tree__title">Каталог товаров</span>
            </button>

            <div v-if="isTreeExpanded" class="catalog-tree__list">
                <template v-for="group in sortedGroups" :key="group.id">
                    <div class="catalog-tree__row catalog-tree__row--l1">
                        <button
                            v-if="(categoriesByGroup.get(group.id) || []).length"
                            type="button"
                            class="catalog-tree__caret"
                            @click="toggleGroup(group.id)"
                        >
                            {{ isGroupExpanded(group.id) ? '⌄' : '›' }}
                        </button>
                        <span v-else class="catalog-tree__caret catalog-tree__caret--placeholder" />
                        <span class="catalog-tree__glyph" />
                        <span class="catalog-tree__title">{{ group.name }}</span>
                        <div v-if="canEditNomenclature || canDeleteNomenclature" class="catalog-tree__actions">
                            <button
                                v-if="canEditNomenclature"
                                type="button"
                                class="catalog-tree__icon-btn"
                                title="Изменить"
                                @click="openEditModal('group', group)"
                            >
                                <BaseIcon name="Edit" />
                            </button>
                            <button
                                v-if="canDeleteNomenclature"
                                type="button"
                                class="catalog-tree__icon-btn catalog-tree__icon-btn--danger"
                                title="Удалить"
                                @click="deleteNode('group', group.id)"
                            >
                                <BaseIcon name="Trash" />
                            </button>
                        </div>
                    </div>

                    <template v-if="isGroupExpanded(group.id)">
                        <template v-for="category in categoriesByGroup.get(group.id) || []" :key="category.id">
                            <div class="catalog-tree__row catalog-tree__row--l2">
                                <button
                                    v-if="(typesByCategory.get(category.id) || []).length"
                                    type="button"
                                    class="catalog-tree__caret"
                                    @click="toggleCategory(category.id)"
                                >
                                    {{ isCategoryExpanded(category.id) ? '⌄' : '›' }}
                                </button>
                                <span v-else class="catalog-tree__caret catalog-tree__caret--placeholder" />
                                <span class="catalog-tree__glyph" />
                                <span class="catalog-tree__title">{{ category.name }}</span>
                                <div v-if="canEditNomenclature || canDeleteNomenclature" class="catalog-tree__actions">
                                    <button
                                        v-if="canEditNomenclature"
                                        type="button"
                                        class="catalog-tree__icon-btn"
                                        title="Изменить"
                                        @click="openEditModal('category', category)"
                                    >
                                        <BaseIcon name="Edit" />
                                    </button>
                                    <button
                                        v-if="canDeleteNomenclature"
                                        type="button"
                                        class="catalog-tree__icon-btn catalog-tree__icon-btn--danger"
                                        title="Удалить"
                                        @click="deleteNode('category', category.id)"
                                    >
                                        <BaseIcon name="Trash" />
                                    </button>
                                </div>
                            </div>

                            <template v-if="isCategoryExpanded(category.id)">
                                <template v-for="type in typesByCategory.get(category.id) || []" :key="type.id">
                                    <div class="catalog-tree__row catalog-tree__row--l3">
                                        <span class="catalog-tree__caret catalog-tree__caret--placeholder" />
                                        <span class="catalog-tree__glyph" />
                                        <span class="catalog-tree__title">{{ type.name }}</span>
                                        <div v-if="canEditNomenclature || canDeleteNomenclature" class="catalog-tree__actions">
                                            <button
                                                v-if="canEditNomenclature"
                                                type="button"
                                                class="catalog-tree__icon-btn"
                                                title="Изменить"
                                                @click="openEditModal('type', type)"
                                            >
                                                <BaseIcon name="Edit" />
                                            </button>
                                            <button
                                                v-if="canDeleteNomenclature"
                                                type="button"
                                                class="catalog-tree__icon-btn catalog-tree__icon-btn--danger"
                                                title="Удалить"
                                                @click="deleteNode('type', type.id)"
                                            >
                                                <BaseIcon name="Trash" />
                                            </button>
                                        </div>
                                    </div>
                                </template>
                            </template>
                        </template>
                    </template>
                </template>
            </div>
        </div>

        <Modal v-if="isCreateModalOpen" @close="closeCreateModal">
            <template #header>Создать новую группу</template>
            <template #default>
                <div class="catalog-tree__edit-form catalog-tree__edit-form--create">
                    <Input v-model="createForm.name" label="Название" placeholder="Введите название раздела" />

                    <div ref="createParentRef" class="catalog-picker catalog-picker--modal">
                        <label class="catalog-picker__label">Куда добавить</label>
                        <button
                            type="button"
                            class="catalog-picker__trigger"
                            @click="isCreateParentOpen = !isCreateParentOpen"
                        >
                            <span :class="{ 'is-placeholder': !createForm.parentNode }">{{ createParentLabel }}</span>
                            <span class="catalog-picker__caret">{{ isCreateParentOpen ? '▲' : '▼' }}</span>
                        </button>

                        <div v-if="isCreateParentOpen" class="catalog-picker__menu">
                            <button
                                type="button"
                                class="catalog-picker__item catalog-picker__item--root"
                                :class="{ 'is-selected': createForm.parentNode === 'root' }"
                                @click="selectCreateParent('root')"
                            >
                                ...
                            </button>

                            <template v-for="group in sortedGroups" :key="group.id">
                                <div class="catalog-picker__row catalog-picker__row--l1">
                                    <button
                                        v-if="(categoriesByGroup.get(group.id) || []).length"
                                        type="button"
                                        class="catalog-picker__toggle"
                                        @click="toggleCreateGroup(group.id)"
                                    >
                                        {{ isCreateGroupExpanded(group.id) ? '⌄' : '›' }}
                                    </button>
                                    <span v-else class="catalog-picker__toggle catalog-picker__toggle--placeholder" />
                                    <button
                                        type="button"
                                        class="catalog-picker__item"
                                        :class="{ 'is-selected': createForm.parentNode === `g:${group.id}` }"
                                        @click="selectCreateParent(`g:${group.id}`)"
                                    >
                                        {{ group.name }}
                                    </button>
                                </div>

                                <template v-if="isCreateGroupExpanded(group.id)">
                                    <template v-for="category in categoriesByGroup.get(group.id) || []" :key="category.id">
                                        <div class="catalog-picker__row catalog-picker__row--l2">
                                            <button
                                                v-if="(typesByCategory.get(category.id) || []).length"
                                                type="button"
                                                class="catalog-picker__toggle"
                                                @click="toggleCreateCategory(category.id)"
                                            >
                                                {{ isCreateCategoryExpanded(category.id) ? '⌄' : '›' }}
                                            </button>
                                            <span
                                                v-else
                                                class="catalog-picker__toggle catalog-picker__toggle--placeholder"
                                            />
                                            <button
                                                type="button"
                                                class="catalog-picker__item"
                                                :class="{ 'is-selected': createForm.parentNode === `c:${category.id}` }"
                                                @click="selectCreateParent(`c:${category.id}`)"
                                            >
                                                {{ category.name }}
                                            </button>
                                        </div>

                                        <template v-if="isCreateCategoryExpanded(category.id)">
                                            <div
                                                v-for="type in typesByCategory.get(category.id) || []"
                                                :key="type.id"
                                                class="catalog-picker__row catalog-picker__row--l3"
                                            >
                                                <span class="catalog-picker__toggle catalog-picker__toggle--placeholder" />
                                                <span class="catalog-picker__item catalog-picker__item--static">
                                                    {{ type.name }}
                                                </span>
                                            </div>
                                        </template>
                                    </template>
                                </template>
                            </template>
                        </div>
                    </div>

                    <p class="catalog-tree__create-hint">{{ createParentHint }}</p>
                </div>
            </template>
            <template #footer>
                <Button color="ghost" :disabled="saving" @click="closeCreateModal">Отмена</Button>
                <Button v-if="canCreateNomenclature" color="primary" :loading="saving" @click="handleCreateNode">{{ createSubmitLabel }}</Button>
            </template>
        </Modal>

        <Modal v-if="isEditModalOpen" @close="closeEditModal">
            <template #header>Изменить раздел</template>
            <template #default>
                <div class="catalog-tree__edit-form">
                    <Input v-model="editForm.name" label="Название" placeholder="Введите название" />
                    <Select
                        v-if="editForm.level === 'category'"
                        v-model="editForm.parentGroupId"
                        label="Родитель (1-й этаж)"
                        :options="firstFloorOptions"
                        placeholder="Выберите раздел"
                        searchable
                    />
                    <Select
                        v-if="editForm.level === 'type'"
                        v-model="editForm.parentCategoryId"
                        label="Родитель (2-й этаж)"
                        :options="secondFloorOptions"
                        placeholder="Выберите раздел"
                        searchable
                    />
                </div>
            </template>
            <template #footer>
                <Button color="ghost" :disabled="saving" @click="closeEditModal">Отмена</Button>
                <Button v-if="canEditNomenclature" color="primary" :loading="saving" @click="submitEdit">Сохранить</Button>
            </template>
        </Modal>
    </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useToast } from 'vue-toastification';
import {
    INVENTORY_NOMENCLATURE_CREATE_PERMISSIONS,
    INVENTORY_NOMENCLATURE_DELETE_PERMISSIONS,
    INVENTORY_NOMENCLATURE_EDIT_PERMISSIONS,
} from '@/accessPolicy';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';
import { useUserStore } from '@/stores/user';
import {
    createInventoryCategory,
    createInventoryGroup,
    createInventoryType,
    deleteInventoryCategory,
    deleteInventoryGroup,
    deleteInventoryType,
    fetchInventoryCategories,
    fetchInventoryGroups,
    fetchInventoryTypes,
    updateInventoryCategory,
    updateInventoryGroup,
    updateInventoryType,
} from '@/api';

const toast = useToast();
const userStore = useUserStore();

const groups = ref([]);
const categories = ref([]);
const types = ref([]);
const loading = ref(false);
const saving = ref(false);

const isTreeExpanded = ref(false);
const expandedGroupIds = ref(new Set());
const expandedCategoryIds = ref(new Set());

const isCreateModalOpen = ref(false);
const isCreateParentOpen = ref(false);
const createParentRef = ref(null);
const createExpandedGroupIds = ref(new Set());
const createExpandedCategoryIds = ref(new Set());

const createForm = reactive({
    name: '',
    parentNode: 'root',
});

const isEditModalOpen = ref(false);
const editForm = reactive({
    id: null,
    level: '',
    name: '',
    parentGroupId: '',
    parentCategoryId: '',
});

const sortedGroups = computed(() =>
    [...groups.value].sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' })),
);
const sortedCategories = computed(() =>
    [...categories.value].sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' })),
);
const sortedTypes = computed(() =>
    [...types.value].sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' })),
);

const groupMap = computed(() => {
    const map = new Map();
    groups.value.forEach((group) => map.set(group.id, group));
    return map;
});

const categoryMap = computed(() => {
    const map = new Map();
    categories.value.forEach((category) => map.set(category.id, category));
    return map;
});

const firstFloorOptions = computed(() =>
    sortedGroups.value.map((group) => ({ value: String(group.id), label: group.name })),
);

const secondFloorOptions = computed(() =>
    sortedCategories.value.map((category) => {
        const groupName = groupMap.value.get(category.group_id)?.name || `ID ${category.group_id}`;
        return { value: String(category.id), label: `${groupName} > ${category.name}` };
    }),
);

const categoriesByGroup = computed(() => {
    const map = new Map();
    for (const category of sortedCategories.value) {
        const bucket = map.get(category.group_id) || [];
        bucket.push(category);
        map.set(category.group_id, bucket);
    }
    return map;
});

const typesByCategory = computed(() => {
    const map = new Map();
    for (const type of sortedTypes.value) {
        const bucket = map.get(type.category_id) || [];
        bucket.push(type);
        map.set(type.category_id, bucket);
    }
    return map;
});

const hasCatalogNodes = computed(
    () => groups.value.length > 0 || categories.value.length > 0 || types.value.length > 0,
);

const createParentLabel = computed(() => {
    if (!hasCatalogNodes.value) {
        return 'База пуста — будет создана новая группа';
    }
    const parsed = parseCreateParentNode(createForm.parentNode);
    if (!parsed || parsed.level === 'root') {
        return '... (новая группа)';
    }
    if (parsed.level === 'g') {
        const group = groupMap.value.get(parsed.id);
        return group ? `${group.name} (новая категория)` : '... (новая группа)';
    }
    if (parsed.level === 'c') {
        const category = categoryMap.value.get(parsed.id);
        if (!category) {
            return '... (новая группа)';
        }
        const groupName = groupMap.value.get(category.group_id)?.name || `ID ${category.group_id}`;
        return `${groupName} > ${category.name} (новый вид)`;
    }
    return '... (новая группа)';
});

const createParentHint = computed(() => {
    if (!hasCatalogNodes.value) {
        return 'Структура пуста. Первый раздел будет создан на уровне группы.';
    }
    const parsed = parseCreateParentNode(createForm.parentNode);
    if (!parsed || parsed.level === 'root') {
        return 'Будет создана новая группа (1-й этаж).';
    }
    if (parsed.level === 'g') {
        return 'Будет создана новая категория внутри выбранной группы.';
    }
    return 'Будет создан новый вид внутри выбранной категории.';
});

const createSubmitLabel = computed(() => {
    if (!hasCatalogNodes.value) {
        return 'Создать группу';
    }
    const parsed = parseCreateParentNode(createForm.parentNode);
    if (!parsed || parsed.level === 'root') {
        return 'Создать группу';
    }
    if (parsed.level === 'g') {
        return 'Создать категорию';
    }
    return 'Создать вид';
});
const canCreateNomenclature = computed(() => userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_CREATE_PERMISSIONS));
const canEditNomenclature = computed(() => userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_EDIT_PERMISSIONS));
const canDeleteNomenclature = computed(() => userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_DELETE_PERMISSIONS));

function parseCreateParentNode(value) {
    if (!value || value === 'root') {
        return { level: 'root' };
    }
    const [level, idRaw] = String(value).split(':');
    if (!['g', 'c'].includes(level)) {
        return null;
    }
    const id = Number(idRaw);
    if (!Number.isFinite(id)) {
        return null;
    }
    return { level, id };
}

function isGroupExpanded(groupId) {
    return expandedGroupIds.value.has(groupId);
}

function isCategoryExpanded(categoryId) {
    return expandedCategoryIds.value.has(categoryId);
}

function toggleGroup(groupId) {
    const next = new Set(expandedGroupIds.value);
    if (next.has(groupId)) {
        next.delete(groupId);
    } else {
        next.add(groupId);
    }
    expandedGroupIds.value = next;
}

function toggleCategory(categoryId) {
    const next = new Set(expandedCategoryIds.value);
    if (next.has(categoryId)) {
        next.delete(categoryId);
    } else {
        next.add(categoryId);
    }
    expandedCategoryIds.value = next;
}

function resetCreateForm() {
    createForm.name = '';
    createForm.parentNode = 'root';
}

function seedCreateTreeExpansion() {
    createExpandedGroupIds.value = new Set(sortedGroups.value.map((group) => group.id));
    createExpandedCategoryIds.value = new Set();
}

function isCreateGroupExpanded(groupId) {
    return createExpandedGroupIds.value.has(groupId);
}

function isCreateCategoryExpanded(categoryId) {
    return createExpandedCategoryIds.value.has(categoryId);
}

function toggleCreateGroup(groupId) {
    const next = new Set(createExpandedGroupIds.value);
    if (next.has(groupId)) {
        next.delete(groupId);
    } else {
        next.add(groupId);
    }
    createExpandedGroupIds.value = next;
}

function toggleCreateCategory(categoryId) {
    const next = new Set(createExpandedCategoryIds.value);
    if (next.has(categoryId)) {
        next.delete(categoryId);
    } else {
        next.add(categoryId);
    }
    createExpandedCategoryIds.value = next;
}

function openCreateModal() {
    if (!canCreateNomenclature.value) {
        toast.error('Недостаточно прав для создания номенклатуры');
        return;
    }
    resetCreateForm();
    seedCreateTreeExpansion();
    isCreateParentOpen.value = false;
    isCreateModalOpen.value = true;
}

function closeCreateModal() {
    isCreateModalOpen.value = false;
    isCreateParentOpen.value = false;
    resetCreateForm();
}

function selectCreateParent(value) {
    createForm.parentNode = value;
    isCreateParentOpen.value = false;
}

function resetEditForm() {
    editForm.id = null;
    editForm.level = '';
    editForm.name = '';
    editForm.parentGroupId = '';
    editForm.parentCategoryId = '';
}

async function loadTree() {
    loading.value = true;
    try {
        const [groupsData, categoriesData, typesData] = await Promise.all([
            fetchInventoryGroups(),
            fetchInventoryCategories(),
            fetchInventoryTypes(),
        ]);
        groups.value = Array.isArray(groupsData) ? groupsData : [];
        categories.value = Array.isArray(categoriesData) ? categoriesData : [];
        types.value = Array.isArray(typesData) ? typesData : [];
        expandedGroupIds.value = new Set();
        expandedCategoryIds.value = new Set();
    } catch (error) {
        toast.error('Не удалось загрузить структуру товаров');
        console.error(error);
    } finally {
        loading.value = false;
    }
}

async function handleCreateNode() {
    if (!canCreateNomenclature.value) {
        toast.error('Недостаточно прав для создания номенклатуры');
        return;
    }
    const name = createForm.name.trim();
    if (!name) {
        toast.error('Введите название');
        return;
    }

    saving.value = true;
    try {
        if (!hasCatalogNodes.value) {
            await createInventoryGroup({ name });
        } else {
            const parent = parseCreateParentNode(createForm.parentNode);
            if (!parent || parent.level === 'root') {
                await createInventoryGroup({ name });
            } else if (parent.level === 'g') {
                const group = groupMap.value.get(parent.id);
                if (!group) {
                    toast.error('Выберите папку для новой категории');
                    return;
                }
                await createInventoryCategory({ name, group_id: group.id });
            } else {
                const category = categoryMap.value.get(parent.id);
                if (!category) {
                    toast.error('Выберите папку для нового вида');
                    return;
                }
                await createInventoryType({
                    name,
                    group_id: category.group_id,
                    category_id: category.id,
                });
            }
        }
        toast.success('Раздел создан');
        closeCreateModal();
        await loadTree();
    } catch (error) {
        toast.error('Не удалось создать раздел');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

function onDocumentClick(event) {
    if (createParentRef.value && !createParentRef.value.contains(event.target)) {
        isCreateParentOpen.value = false;
    }
}

onMounted(() => {
    document.addEventListener('click', onDocumentClick);
    loadTree();
});

onBeforeUnmount(() => {
    document.removeEventListener('click', onDocumentClick);
});

function openEditModal(level, entity) {
    if (!canEditNomenclature.value) {
        toast.error('Недостаточно прав для редактирования номенклатуры');
        return;
    }
    editForm.id = entity.id;
    editForm.level = level;
    editForm.name = entity.name || '';
    editForm.parentGroupId = level !== 'group' ? String(entity.group_id || '') : '';
    editForm.parentCategoryId = level === 'type' ? String(entity.category_id || '') : '';
    isEditModalOpen.value = true;
}

function closeEditModal() {
    isEditModalOpen.value = false;
    resetEditForm();
}

async function submitEdit() {
    if (!canEditNomenclature.value) {
        toast.error('Недостаточно прав для редактирования номенклатуры');
        return;
    }
    if (!editForm.id) {
        return;
    }
    const name = editForm.name.trim();
    if (!name) {
        toast.error('Введите название');
        return;
    }

    saving.value = true;
    try {
        if (editForm.level === 'group') {
            await updateInventoryGroup(editForm.id, { name });
        } else if (editForm.level === 'category') {
            const groupId = Number(editForm.parentGroupId);
            if (!groupId) {
                toast.error('Выберите родителя 1-го этажа');
                return;
            }
            await updateInventoryCategory(editForm.id, { name, group_id: groupId });
        } else if (editForm.level === 'type') {
            const categoryId = Number(editForm.parentCategoryId);
            const category = categoryMap.value.get(categoryId);
            if (!category) {
                toast.error('Выберите родителя 2-го этажа');
                return;
            }
            await updateInventoryType(editForm.id, {
                name,
                group_id: category.group_id,
                category_id: category.id,
            });
        }
        toast.success('Изменения сохранены');
        closeEditModal();
        await loadTree();
    } catch (error) {
        toast.error('Не удалось сохранить изменения');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

async function deleteNode(level, id) {
    if (!canDeleteNomenclature.value) {
        toast.error('Недостаточно прав для удаления номенклатуры');
        return;
    }
    if (!window.confirm('Удалить раздел?')) {
        return;
    }
    saving.value = true;
    try {
        if (level === 'group') {
            await deleteInventoryGroup(id);
        } else if (level === 'category') {
            await deleteInventoryCategory(id);
        } else {
            await deleteInventoryType(id);
        }
        toast.success('Раздел удален');
        await loadTree();
    } catch (error) {
        toast.error('Не удалось удалить раздел');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-groups' as *;
</style>
