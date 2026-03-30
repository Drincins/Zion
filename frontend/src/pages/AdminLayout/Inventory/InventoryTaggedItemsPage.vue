<template>
    <section class="inventory-tagged">
        <header class="inventory-tagged__header">
            <div>
                <h2 class="inventory-tagged__title">Склад · Товары по тегам</h2>
                <p class="inventory-tagged__subtitle">
                    Фильтр по объектам и тегам стоимости.
                </p>
            </div>
            <Button color="ghost" size="sm" :loading="loadingItems" @click="loadItemsByFilters">Обновить</Button>
        </header>

        <section class="inventory-tagged__filters">
            <div ref="departmentSelectRef" class="inventory-tagged__department-select">
                <label class="inventory-tagged__label">Объекты</label>
                <button
                    type="button"
                    class="inventory-tagged__trigger"
                    @click="isDepartmentsOpen = !isDepartmentsOpen"
                >
                    <span :class="{ 'is-placeholder': !selectedDepartmentLabels.length }">{{ departmentsLabel }}</span>
                    <span class="inventory-tagged__caret">{{ isDepartmentsOpen ? '▲' : '▼' }}</span>
                </button>
                <div v-if="isDepartmentsOpen" class="inventory-tagged__menu">
                    <Input
                        v-model="departmentSearch"
                        label=""
                        placeholder="Поиск подразделения"
                        class="inventory-tagged__search"
                    />
                    <div class="inventory-tagged__options">
                        <label
                            v-for="option in filteredDepartmentOptions"
                            :key="option.id"
                            class="inventory-tagged__option"
                        >
                            <input
                                type="checkbox"
                                :checked="selectedDepartmentIds.includes(option.id)"
                                @change="toggleDepartment(option)"
                            />
                            <span>{{ option.label }}</span>
                        </label>
                        <p v-if="!filteredDepartmentOptions.length" class="inventory-tagged__empty-menu">Ничего не найдено</p>
                    </div>
                </div>
            </div>

            <div ref="tagFilterRef" class="inventory-tagged__tag-select">
                <label class="inventory-tagged__label">Теги</label>
                <button
                    type="button"
                    class="inventory-tagged__trigger"
                    @click="isTagsOpen = !isTagsOpen"
                >
                    <span>{{ tagFilterLabel }}</span>
                    <span class="inventory-tagged__caret">{{ isTagsOpen ? '▲' : '▼' }}</span>
                </button>
                <div v-if="isTagsOpen" class="inventory-tagged__menu">
                    <button type="button" class="inventory-tagged__clear" @click="clearTags">Все теги</button>
                    <label
                        v-for="tag in tagOptions"
                        :key="tag.value"
                        class="inventory-tagged__option"
                    >
                        <input
                            type="checkbox"
                            :checked="selectedTagIds.includes(tag.value)"
                            @change="toggleTag(tag.value)"
                        />
                        <span>{{ tag.label }}</span>
                    </label>
                </div>
            </div>

            <div class="inventory-page__form-actions">
                <Button color="primary" size="sm" :loading="loadingItems" @click="loadItemsByFilters">Показать</Button>
                <Button color="ghost" size="sm" :disabled="loadingItems" @click="resetFilters">Сбросить</Button>
            </div>
        </section>

        <section class="inventory-tagged__content">
            <div v-if="!hasLoadedByFilters" class="inventory-page__empty">
                Выберите объекты и нажмите «Показать».
            </div>
            <div v-else-if="loadingItems" class="inventory-page__loading">Загрузка...</div>
            <div v-else-if="tagGroups.length" class="inventory-tagged__groups">
                <article
                    v-for="tagGroup in tagGroups"
                    :key="tagGroup.id"
                    class="inventory-tagged__group"
                >
                    <header class="inventory-tagged__group-header">
                        <h3>{{ tagGroup.label }}</h3>
                        <span>
                            {{ tagGroup.totalQuantity }} шт. · {{ formatMoney(tagGroup.totalCost) }}
                        </span>
                    </header>

                    <div v-if="!tagGroup.objects.length" class="inventory-tagged__group-empty">
                        По выбранным фильтрам данных нет.
                    </div>

                    <div
                        v-for="objectNode in tagGroup.objects"
                        :key="`${tagGroup.id}:${objectNode.key}`"
                        class="inventory-tagged__object"
                    >
                        <div class="inventory-tagged__object-title">{{ objectNode.name }}</div>
                        <button
                            v-for="entry in objectNode.items"
                            :key="entry.key"
                            type="button"
                            class="inventory-tagged__item"
                            @click="openDetail(entry)"
                        >
                            <div class="inventory-tagged__item-main">
                                <span class="inventory-tagged__item-name">{{ entry.item.name }}</span>
                                <span class="inventory-tagged__item-meta">
                                    {{ entry.item.code || `ITEM-${entry.item.id}` }} · {{ entry.catalogPath }}
                                </span>
                            </div>
                            <span class="inventory-tagged__item-values">
                                {{ entry.quantity }} шт. · {{ formatMoney(entry.unitCost) }} · {{ formatMoney(entry.totalCost) }}
                            </span>
                        </button>
                    </div>
                </article>
            </div>
            <div v-else class="inventory-page__empty">Ничего не найдено.</div>
        </section>

        <Modal v-if="detailEntry" @close="detailEntry = null">
            <template #header>Карточка товара</template>
            <template #default>
                <div class="inventory-tagged__detail">
                    <h3>{{ detailEntry.item.name }}</h3>
                    <p>{{ detailEntry.item.note || 'Описание не заполнено' }}</p>
                    <div class="inventory-tagged__detail-grid">
                        <div>
                            <span>Тег</span>
                            <strong>{{ detailEntry.tagLabel }}</strong>
                        </div>
                        <div>
                            <span>Объект</span>
                            <strong>{{ detailEntry.locationName }}</strong>
                        </div>
                        <div>
                            <span>Количество</span>
                            <strong>{{ detailEntry.quantity }} шт.</strong>
                        </div>
                        <div>
                            <span>Цена единицы</span>
                            <strong>{{ formatMoney(detailEntry.unitCost) }}</strong>
                        </div>
                        <div>
                            <span>Сумма</span>
                            <strong>{{ formatMoney(detailEntry.totalCost) }}</strong>
                        </div>
                        <div>
                            <span>Раздел каталога</span>
                            <strong>{{ detailEntry.catalogPath }}</strong>
                        </div>
                    </div>
                </div>
            </template>
        </Modal>
    </section>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import { useInventoryTaggedItemsPage } from '@/pages/AdminLayout/Inventory/composables/useInventoryTaggedItemsPage';

const {
    loadingItems,
    hasLoadedByFilters,
    isDepartmentsOpen,
    isTagsOpen,
    departmentSearch,
    selectedDepartmentIds,
    selectedTagIds,
    departmentSelectRef,
    tagFilterRef,
    detailEntry,
    tagOptions,
    filteredDepartmentOptions,
    selectedDepartmentLabels,
    departmentsLabel,
    tagFilterLabel,
    tagGroups,
    formatMoney,
    toggleDepartment,
    toggleTag,
    clearTags,
    loadItemsByFilters,
    resetFilters,
    openDetail,
} = useInventoryTaggedItemsPage();

</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-tagged-items' as *;
</style>
