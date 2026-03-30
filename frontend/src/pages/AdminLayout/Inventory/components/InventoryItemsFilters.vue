<template>
    <section class="inventory-items__filters">
        <div :ref="departmentSelectRef" class="inventory-items__department-select">
            <label class="inventory-items__label">Подразделения</label>
            <button
                type="button"
                class="inventory-items__department-trigger"
                @click="$emit('update:isDepartmentsOpen', !isDepartmentsOpen)"
            >
                <span :class="{ 'is-placeholder': !selectedDepartmentLabels.length }">{{ departmentsLabel }}</span>
                <span class="inventory-items__caret">{{ isDepartmentsOpen ? '▲' : '▼' }}</span>
            </button>
            <div v-if="isDepartmentsOpen" class="inventory-items__department-menu">
                <Input
                    v-model="departmentSearchModel"
                    label=""
                    placeholder="Поиск подразделения"
                    class="inventory-items__department-search"
                />
                <div class="inventory-items__department-list">
                    <label
                        v-for="option in filteredDepartmentOptions"
                        :key="option.id"
                        class="inventory-items__department-option"
                    >
                        <input
                            type="checkbox"
                            :checked="selectedDepartmentIds.includes(option.id)"
                            @change="toggleDepartment(option)"
                        />
                        <span>{{ option.label }}</span>
                    </label>
                    <p v-if="!filteredDepartmentOptions.length" class="inventory-items__department-empty">Ничего не найдено</p>
                </div>
            </div>
        </div>

        <div :ref="catalogFilterRef" class="catalog-picker">
            <label class="inventory-items__label">Раздел каталога</label>
            <button
                type="button"
                class="catalog-picker__trigger"
                @click="$emit('update:isCatalogFilterOpen', !isCatalogFilterOpen)"
            >
                <span :class="{ 'is-placeholder': !selectedCatalogNodeIds.length }">{{ catalogFilterLabel }}</span>
                <span class="inventory-items__caret">{{ isCatalogFilterOpen ? '▲' : '▼' }}</span>
            </button>
            <div v-if="isCatalogFilterOpen" class="catalog-picker__menu">
                <label class="catalog-picker__item catalog-picker__item--root catalog-picker__item--check">
                    <input
                        type="checkbox"
                        :checked="!selectedCatalogNodeIds.length"
                        @change="clearFilterCatalogNodes"
                    />
                    <span>Все разделы</span>
                </label>
                <template v-for="group in sortedGroups" :key="group.id">
                    <div class="catalog-picker__row catalog-picker__row--l1">
                        <button
                            v-if="(categoriesByGroup.get(group.id) || []).length"
                            type="button"
                            class="catalog-picker__toggle"
                            @click="toggleFilterGroup(group.id)"
                        >
                            {{ isFilterGroupExpanded(group.id) ? '⌄' : '›' }}
                        </button>
                        <span v-else class="catalog-picker__toggle catalog-picker__toggle--placeholder" />
                        <label class="catalog-picker__item catalog-picker__item--check" :class="{ 'is-selected': isCatalogNodeSelected(`g:${group.id}`) }">
                            <input
                                type="checkbox"
                                :checked="isCatalogNodeSelected(`g:${group.id}`)"
                                @change="toggleFilterCatalogNode(`g:${group.id}`)"
                            />
                            <span>{{ group.name }}</span>
                        </label>
                    </div>

                    <template v-if="isFilterGroupExpanded(group.id)">
                        <template v-for="category in categoriesByGroup.get(group.id) || []" :key="category.id">
                            <div class="catalog-picker__row catalog-picker__row--l2">
                                <button
                                    v-if="(typesByCategory.get(category.id) || []).length"
                                    type="button"
                                    class="catalog-picker__toggle"
                                    @click="toggleFilterCategory(category.id)"
                                >
                                    {{ isFilterCategoryExpanded(category.id) ? '⌄' : '›' }}
                                </button>
                                <span v-else class="catalog-picker__toggle catalog-picker__toggle--placeholder" />
                                <label class="catalog-picker__item catalog-picker__item--check" :class="{ 'is-selected': isCatalogNodeSelected(`c:${category.id}`) }">
                                    <input
                                        type="checkbox"
                                        :checked="isCatalogNodeSelected(`c:${category.id}`)"
                                        @change="toggleFilterCatalogNode(`c:${category.id}`)"
                                    />
                                    <span>{{ category.name }}</span>
                                </label>
                            </div>

                            <template v-if="isFilterCategoryExpanded(category.id)">
                                <div
                                    v-for="type in typesByCategory.get(category.id) || []"
                                    :key="type.id"
                                    class="catalog-picker__row catalog-picker__row--l3"
                                >
                                    <span class="catalog-picker__toggle catalog-picker__toggle--placeholder" />
                                    <label class="catalog-picker__item catalog-picker__item--check" :class="{ 'is-selected': isCatalogNodeSelected(`t:${type.id}`) }">
                                        <input
                                            type="checkbox"
                                            :checked="isCatalogNodeSelected(`t:${type.id}`)"
                                            @change="toggleFilterCatalogNode(`t:${type.id}`)"
                                        />
                                        <span>{{ type.name }}</span>
                                    </label>
                                </div>
                            </template>
                        </template>
                    </template>
                </template>
            </div>
        </div>

        <div class="inventory-page__form-actions">
            <Button color="primary" size="sm" :loading="loadingItems" @click="loadItemsByFilters">Показать</Button>
            <Button color="ghost" size="sm" :disabled="loadingItems" @click="resetFilters">Сбросить</Button>
        </div>
    </section>
</template>

<script setup>
import { computed } from 'vue';

import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';

const props = defineProps({
    catalogFilterLabel: { type: String, required: true },
    catalogFilterRef: { type: Object, required: true },
    categoriesByGroup: { type: Object, required: true },
    clearFilterCatalogNodes: { type: Function, required: true },
    departmentSearch: { type: String, required: true },
    departmentSelectRef: { type: Object, required: true },
    departmentsLabel: { type: String, required: true },
    filteredDepartmentOptions: { type: Array, required: true },
    isCatalogFilterOpen: { type: Boolean, required: true },
    isCatalogNodeSelected: { type: Function, required: true },
    isDepartmentsOpen: { type: Boolean, required: true },
    isFilterCategoryExpanded: { type: Function, required: true },
    isFilterGroupExpanded: { type: Function, required: true },
    loadItemsByFilters: { type: Function, required: true },
    loadingItems: { type: Boolean, required: true },
    resetFilters: { type: Function, required: true },
    selectedCatalogNodeIds: { type: Array, required: true },
    selectedDepartmentIds: { type: Array, required: true },
    selectedDepartmentLabels: { type: Array, required: true },
    sortedGroups: { type: Array, required: true },
    toggleDepartment: { type: Function, required: true },
    toggleFilterCatalogNode: { type: Function, required: true },
    toggleFilterCategory: { type: Function, required: true },
    toggleFilterGroup: { type: Function, required: true },
    typesByCategory: { type: Object, required: true },
});

const emit = defineEmits(['update:departmentSearch', 'update:isCatalogFilterOpen', 'update:isDepartmentsOpen']);

const departmentSearchModel = computed({
    get: () => props.departmentSearch,
    set: (value) => emit('update:departmentSearch', value),
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-items' as *;
</style>
