<template>
    <section class="inventory-page__section inventory-movements">
        <header class="inventory-movements__header">
            <div class="inventory-movements__header-main">
                <h1 class="inventory-movements__title">Журнал операций</h1>
                <p class="inventory-movements__subtitle">
                    История операций по складу с фильтрами по товарам, объектам, типам действий и сотрудникам.
                </p>
            </div>
            <div class="inventory-movements__header-actions">
                <router-link :to="{ name: 'inventory-balance' }" class="inventory-movements__back-link">
                    Назад
                </router-link>
                <Button color="ghost" size="sm" :loading="loading" @click="loadMovements">Обновить</Button>
            </div>
        </header>

        <section class="inventory-movements__filters-panel">
            <button class="inventory-movements__filters-toggle" type="button" @click="isFiltersOpen = !isFiltersOpen">
                Фильтры
                <span :class="['inventory-movements__filters-icon', { 'is-open': isFiltersOpen }]">▼</span>
            </button>

            <form v-if="isFiltersOpen" class="inventory-movements__filters" @submit.prevent="loadMovements">
                <DateInput v-model="dateFrom" label="С даты" />
                <DateInput v-model="dateTo" label="По дату" />
                <Input
                    v-model="searchQuery"
                    label="Поиск"
                    placeholder="Код или название товара"
                />

            <div :ref="(el) => setFilterRef('catalog', el)" class="movements-multiselect">
                <label class="movements-multiselect__label">Товары и категории</label>
                <button type="button" class="movements-multiselect__trigger" @click="toggleDropdown('catalog')">
                    <span>{{ catalogFilterLabel }}</span>
                    <span>{{ dropdownState.catalog ? '▲' : '▼' }}</span>
                </button>
                <div v-if="dropdownState.catalog" class="movements-multiselect__menu">
                    <button type="button" class="movements-multiselect__clear" @click="clearSelection('catalog')">
                        Все товары и категории
                    </button>
                    <template v-for="group in groupedCatalogOptions" :key="`g:${group.id}`">
                        <div class="movements-catalog__row movements-catalog__row--group">
                            <button
                                v-if="group.categories.length"
                                type="button"
                                class="movements-catalog__toggle"
                                @click="toggleCatalogGroup(group.id)"
                            >
                                {{ isCatalogGroupExpanded(group.id) ? '⌄' : '›' }}
                            </button>
                            <span v-else class="movements-catalog__toggle movements-catalog__toggle--placeholder" />
                            <label class="movements-multiselect__option">
                                <input
                                    type="checkbox"
                                    :checked="selectedFilters.catalog.includes(`g:${group.id}`)"
                                    @change="toggleSelection('catalog', `g:${group.id}`)"
                                />
                                <span>{{ group.name }}</span>
                            </label>
                        </div>
                        <template v-if="isCatalogGroupExpanded(group.id)">
                            <template v-for="category in group.categories" :key="`c:${category.id}`">
                                <div class="movements-catalog__row movements-catalog__row--category">
                                    <button
                                        v-if="category.items.length"
                                        type="button"
                                        class="movements-catalog__toggle"
                                        @click="toggleCatalogCategory(category.id)"
                                    >
                                        {{ isCatalogCategoryExpanded(category.id) ? '⌄' : '›' }}
                                    </button>
                                    <span v-else class="movements-catalog__toggle movements-catalog__toggle--placeholder" />
                                    <label class="movements-multiselect__option">
                                        <input
                                            type="checkbox"
                                            :checked="selectedFilters.catalog.includes(`c:${category.id}`)"
                                            @change="toggleSelection('catalog', `c:${category.id}`)"
                                        />
                                        <span>{{ category.name }}</span>
                                    </label>
                                </div>
                                <template v-if="isCatalogCategoryExpanded(category.id)">
                                    <div
                                        v-for="item in category.items"
                                        :key="`i:${item.id}`"
                                        class="movements-catalog__row movements-catalog__row--item"
                                    >
                                        <span class="movements-catalog__toggle movements-catalog__toggle--placeholder" />
                                        <label class="movements-multiselect__option">
                                            <input
                                                type="checkbox"
                                                :checked="selectedFilters.catalog.includes(`i:${item.id}`)"
                                                @change="toggleSelection('catalog', `i:${item.id}`)"
                                            />
                                            <span>{{ item.code || `ITEM-${item.id}` }} · {{ item.name }}</span>
                                        </label>
                                    </div>
                                </template>
                            </template>
                        </template>
                    </template>
                </div>
            </div>

            <div :ref="(el) => setFilterRef('objects', el)" class="movements-multiselect">
                <label class="movements-multiselect__label">Объекты</label>
                <button type="button" class="movements-multiselect__trigger" @click="toggleDropdown('objects')">
                    <span>{{ objectFilterLabel }}</span>
                    <span>{{ dropdownState.objects ? '▲' : '▼' }}</span>
                </button>
                <div v-if="dropdownState.objects" class="movements-multiselect__menu">
                    <button type="button" class="movements-multiselect__clear" @click="clearSelection('objects')">
                        Все объекты
                    </button>
                    <label
                        v-for="option in objectOptions"
                        :key="option.value"
                        class="movements-multiselect__option"
                    >
                        <input
                            type="checkbox"
                            :checked="selectedFilters.objects.includes(option.value)"
                            @change="toggleSelection('objects', option.value)"
                        />
                        <span>{{ option.label }}</span>
                    </label>
                </div>
            </div>

            <div :ref="(el) => setFilterRef('actions', el)" class="movements-multiselect">
                <label class="movements-multiselect__label">Типы действий</label>
                <button type="button" class="movements-multiselect__trigger" @click="toggleDropdown('actions')">
                    <span>{{ actionFilterLabel }}</span>
                    <span>{{ dropdownState.actions ? '▲' : '▼' }}</span>
                </button>
                <div v-if="dropdownState.actions" class="movements-multiselect__menu">
                    <button type="button" class="movements-multiselect__clear" @click="clearSelection('actions')">
                        Все действия
                    </button>
                    <label
                        v-for="option in actionOptions"
                        :key="option.value"
                        class="movements-multiselect__option"
                    >
                        <input
                            type="checkbox"
                            :checked="selectedFilters.actions.includes(option.value)"
                            @change="toggleSelection('actions', option.value)"
                        />
                        <span>{{ option.label }}</span>
                    </label>
                </div>
            </div>

            <div :ref="(el) => setFilterRef('actors', el)" class="movements-multiselect">
                <label class="movements-multiselect__label">Сотрудники</label>
                <button type="button" class="movements-multiselect__trigger" @click="toggleDropdown('actors')">
                    <span>{{ actorFilterLabel }}</span>
                    <span>{{ dropdownState.actors ? '▲' : '▼' }}</span>
                </button>
                <div v-if="dropdownState.actors" class="movements-multiselect__menu">
                    <button type="button" class="movements-multiselect__clear" @click="clearSelection('actors')">
                        Все сотрудники
                    </button>
                    <label
                        v-for="option in actorOptions"
                        :key="option.value"
                        class="movements-multiselect__option"
                    >
                        <input
                            type="checkbox"
                            :checked="selectedFilters.actors.includes(option.value)"
                            @change="toggleSelection('actors', option.value)"
                        />
                        <span>{{ option.label }}</span>
                    </label>
                </div>
            </div>

                <div class="inventory-page__form-actions">
                    <Button type="submit" color="primary" size="sm" :loading="loading">Показать</Button>
                    <Button type="button" color="ghost" size="sm" :disabled="loading" @click="resetFilters">Сбросить</Button>
                </div>
            </form>
        </section>

        <p class="inventory-movements__summary">
            Записей: <strong>{{ movements.length }}</strong>
        </p>

        <div v-if="loading" class="inventory-page__loading">Загрузка движений...</div>
        <div v-else class="inventory-movements__table-area">
            <Table v-if="movements.length">
                <thead>
                    <tr>
                        <th>Дата (МСК)</th>
                        <th>Действие</th>
                        <th>Товар</th>
                        <th>Объект</th>
                        <th>Кол-во</th>
                        <th>Кто сделал</th>
                        <th>Детали</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="event in movements" :key="event.id">
                        <td>{{ formatDateTime(event.created_at) }}</td>
                        <td>
                            <span class="inventory-movements__action" :class="actionClass(event.action_type)">
                                {{ event.action_label }}
                            </span>
                        </td>
                        <td>
                            <div class="inventory-movements__item">
                                <strong>{{ event.item_name || '—' }}</strong>
                                <span>{{ event.item_code || '—' }}</span>
                            </div>
                        </td>
                        <td>{{ formatObject(event) }}</td>
                        <td>{{ formatQuantity(event) }}</td>
                        <td>{{ event.actor_name || 'Система' }}</td>
                        <td>{{ formatDetails(event) }}</td>
                    </tr>
                </tbody>
            </Table>
            <p v-else class="inventory-page__empty">Движения не найдены.</p>
        </div>
    </section>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Table from '@/components/UI-components/Table.vue';
import { useInventoryRecordsPage } from './composables/useInventoryRecordsPage';

const {
    loading,
    movements,
    isFiltersOpen,
    dateFrom,
    dateTo,
    searchQuery,
    selectedFilters,
    dropdownState,
    groupedCatalogOptions,
    objectOptions,
    actionOptions,
    actorOptions,
    catalogFilterLabel,
    objectFilterLabel,
    actionFilterLabel,
    actorFilterLabel,
    setFilterRef,
    toggleDropdown,
    toggleSelection,
    clearSelection,
    isCatalogGroupExpanded,
    isCatalogCategoryExpanded,
    toggleCatalogGroup,
    toggleCatalogCategory,
    actionClass,
    formatDateTime,
    formatObject,
    formatQuantity,
    formatDetails,
    loadMovements,
    resetFilters,
} = useInventoryRecordsPage();
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-records' as *;
</style>
