<template>
    <div class="inventory-settings">
        <InventoryTechnicalTabs />

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
    </div>
</template>

<script setup>
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import InventoryTechnicalTabs from '@/pages/AdminLayout/Inventory/components/InventoryTechnicalTabs.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';
import { useInventoryGroupsPage } from '@/pages/AdminLayout/Inventory/composables/useInventoryGroupsPage';

const {
    sortedGroups,
    categoriesByGroup,
    typesByCategory,
    firstFloorOptions,
    secondFloorOptions,
    loading,
    saving,
    isTreeExpanded,
    isCreateModalOpen,
    isCreateParentOpen,
    createParentRef,
    createForm,
    isEditModalOpen,
    editForm,
    createParentLabel,
    createParentHint,
    createSubmitLabel,
    canCreateNomenclature,
    canEditNomenclature,
    canDeleteNomenclature,
    isGroupExpanded,
    isCategoryExpanded,
    toggleGroup,
    toggleCategory,
    isCreateGroupExpanded,
    isCreateCategoryExpanded,
    toggleCreateGroup,
    toggleCreateCategory,
    openCreateModal,
    closeCreateModal,
    selectCreateParent,
    loadTree,
    handleCreateNode,
    openEditModal,
    closeEditModal,
    submitEdit,
    deleteNode,
} = useInventoryGroupsPage();
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-groups' as *;
</style>
