<template>
    <div class="inventory-operations">
        <header class="inventory-operations__header">
            <div class="inventory-operations__header-main">
                <h1 class="inventory-operations__title">Движение товаров</h1>
                <p class="inventory-operations__subtitle">
                    Создавайте приход, перемещения и списания через учетную запись операции.
                </p>
            </div>

            <div class="inventory-operations__header-actions">
                <router-link :to="{ name: 'inventory-journal' }" class="inventory-operations__journal-link">
                    Журнал операций
                </router-link>
                <Button color="secondary" size="sm" :loading="loadingLookups || loadingOperations" @click="loadAllData">
                    Обновить
                </Button>
                <Button
                    v-if="canCreateMovement"
                    color="primary"
                    size="sm"
                    class="inventory-operations__add-button"
                    @click="openCreateModal"
                >
                    <BaseIcon name="Plus" class="inventory-operations__add-icon" />
                    <span>Добавить</span>
                </Button>
            </div>
        </header>

        <section class="inventory-operations__filters-panel">
            <button class="inventory-operations__filters-toggle" type="button" @click="toggleFilters">
                Фильтры
                <span :class="['inventory-operations__filters-icon', { 'is-open': isFiltersOpen }]">▼</span>
            </button>

            <div v-if="isFiltersOpen" class="inventory-operations__filters-content">
                <div class="inventory-operations__filters-controls">
                    <Input
                        v-model="tableSearchQuery"
                        class="inventory-operations__search"
                        placeholder="Поиск по товару, основанию или сотруднику"
                    />
                    <div class="inventory-operations__filter-types">
                        <button
                            v-for="option in operationTableFilterOptions"
                            :key="option.value"
                            type="button"
                            :class="[
                                'inventory-operations__filter-type-btn',
                                { 'is-active': tableTypeFilter === option.value }
                            ]"
                            @click="tableTypeFilter = option.value"
                        >
                            {{ option.label }}
                        </button>
                    </div>
                </div>

                <div class="inventory-operations__filters-meta">
                    <p class="inventory-operations__filters-summary">
                        Показано: <strong>{{ filteredOperations.length }}</strong> из {{ operations.length }}
                    </p>
                    <Button
                        v-if="tableSearchQuery || tableTypeFilter !== 'all'"
                        color="ghost"
                        size="sm"
                        @click="resetTableFilters"
                    >
                        Сбросить
                    </Button>
                </div>
            </div>
        </section>

        <section class="inventory-operations__table-card">
            <div class="inventory-operations__table-head">
                <h2 class="inventory-operations__table-title">Созданные операции</h2>
                <p class="inventory-operations__table-subtitle">
                    Записей: <strong>{{ filteredOperations.length }}</strong>
                </p>
            </div>

            <div v-if="loadingOperations" class="inventory-page__loading">Загрузка операций...</div>

            <div v-else-if="filteredOperations.length" class="inventory-operations__table-wrap">
                <Table>
                    <thead>
                        <tr>
                            <th>Дата (МСК)</th>
                            <th>Тип операции</th>
                            <th>Товар</th>
                            <th>Откуда</th>
                            <th>Куда</th>
                            <th>Кол-во</th>
                            <th>Основание</th>
                            <th>Кто создал</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="event in filteredOperations" :key="event.id">
                            <td>{{ formatDateTime(event.created_at) }}</td>
                            <td>
                                <span class="inventory-operations__badge" :class="actionClass(event.action_type)">
                                    {{ event.action_label }}
                                </span>
                            </td>
                            <td>
                                <div class="inventory-operations__item">
                                    <strong>{{ event.item_name || '—' }}</strong>
                                    <span>{{ event.item_code || '—' }}</span>
                                </div>
                            </td>
                            <td>{{ formatFrom(event) }}</td>
                            <td>{{ formatTo(event) }}</td>
                            <td>{{ formatQuantity(event) }}</td>
                            <td>{{ formatReason(event) }}</td>
                            <td>{{ event.actor_name || 'Система' }}</td>
                        </tr>
                    </tbody>
                </Table>
            </div>

            <p v-else class="inventory-page__empty">
                {{ operations.length ? 'По выбранным фильтрам операций не найдено.' : 'Операций пока нет.' }}
            </p>
        </section>

        <Modal v-if="isCreateModalOpen" @close="closeCreateModal">
            <template #header>
                <div class="inventory-operations__modal-header">
                    <h3 class="inventory-operations__modal-title">Новая операция</h3>
                    <p class="inventory-operations__modal-subtitle">
                        Запись фиксирует: что, сколько и откуда куда перемещается.
                    </p>
                </div>
            </template>

            <template #default>
                <div class="inventory-operations__modal-body">
                    <div class="inventory-operations__type-row">
                        <label class="inventory-operations__label">Тип операции</label>
                        <div class="inventory-operations__type-list">
                            <button
                                v-for="option in operationTypeOptions"
                                :key="option.value"
                                type="button"
                                :class="[
                                    'inventory-operations__type-btn',
                                    { 'is-active': operationType === option.value }
                                ]"
                                @click="operationType = option.value"
                            >
                                {{ option.label }}
                            </button>
                        </div>
                    </div>

                    <div class="inventory-operations__form-grid">
                        <Select
                            v-model="form.itemId"
                            label="Что перемещаем"
                            :options="itemOptions"
                            placeholder="Выберите товар"
                            searchable
                        />

                        <Input
                            v-model="form.quantity"
                            label="Сколько"
                            type="number"
                            min="1"
                            step="1"
                            placeholder="Например, 5"
                        />

                        <Select
                            v-if="isIncomeOperation"
                            v-model="form.toLocationId"
                            label="Куда зачислить"
                            :options="locationOptions"
                            placeholder="Выберите объект"
                            searchable
                        />

                        <Input
                            v-if="isIncomeOperation"
                            v-model="form.unitCost"
                            label="Цена за единицу (опционально)"
                            type="number"
                            min="0"
                            step="0.01"
                            placeholder="По умолчанию из карточки"
                        />

                        <Select
                            v-if="isTransferOperation || isWriteoffOperation"
                            v-model="form.fromLocationId"
                            label="Откуда"
                            :options="locationOptions"
                            placeholder="Выберите источник"
                            searchable
                        />

                        <Select
                            v-if="isTransferOperation"
                            v-model="form.toLocationId"
                            label="Куда"
                            :options="targetLocationOptions"
                            placeholder="Выберите получателя"
                            searchable
                        />

                        <Input
                            v-model="form.reason"
                            label="Почему / основание"
                            placeholder="Например: поставка, инвентаризация, внутренний перевод"
                        />
                    </div>

                    <p v-if="isTransferOperation || isWriteoffOperation" class="inventory-operations__stock-hint">
                        Доступно в источнике: <strong>{{ sourceLocationQuantity }}</strong> шт.
                    </p>
                    <p
                        v-else-if="isIncomeOperation && selectedToLocation && selectedItem"
                        class="inventory-operations__stock-hint"
                    >
                        Текущий остаток в точке зачисления: <strong>{{ targetLocationQuantity }}</strong> шт.
                    </p>

                    <section class="inventory-operations__record-card">
                        <h4 class="inventory-operations__record-title">Запись операции</h4>
                        <dl class="inventory-operations__record-grid">
                            <dt>Что</dt>
                            <dd>{{ draftRecord.what }}</dd>
                            <dt>Сколько</dt>
                            <dd>{{ draftRecord.quantity }}</dd>
                            <dt>Откуда</dt>
                            <dd>{{ draftRecord.from }}</dd>
                            <dt>Куда</dt>
                            <dd>{{ draftRecord.to }}</dd>
                            <dt>Как</dt>
                            <dd>{{ draftRecord.method }}</dd>
                            <dt>Почему</dt>
                            <dd>{{ draftRecord.reason }}</dd>
                        </dl>
                    </section>
                </div>
            </template>

            <template #footer>
                <div class="inventory-operations__modal-actions">
                    <Button color="ghost" size="sm" :disabled="submitting" @click="closeCreateModal">Отмена</Button>
                    <Button v-if="canCreateMovement" color="primary" size="sm" :loading="submitting" @click="submitOperation">
                        Сохранить операцию
                    </Button>
                </div>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';
import Table from '@/components/UI-components/Table.vue';
import { useInventoryOperationsPage } from './composables/useInventoryOperationsPage';

const {
    operationType,
    operationTypeOptions,
    operationTableFilterOptions,
    loadingLookups,
    loadingOperations,
    submitting,
    isCreateModalOpen,
    isFiltersOpen,
    tableSearchQuery,
    tableTypeFilter,
    form,
    isIncomeOperation,
    isTransferOperation,
    isWriteoffOperation,
    itemOptions,
    selectedItem,
    locationOptions,
    targetLocationOptions,
    selectedToLocation,
    canCreateMovement,
    sourceLocationQuantity,
    targetLocationQuantity,
    filteredOperations,
    draftRecord,
    toggleFilters,
    resetTableFilters,
    openCreateModal,
    closeCreateModal,
    actionClass,
    formatDateTime,
    formatFrom,
    formatTo,
    formatQuantity,
    formatReason,
    loadOperations,
    loadAllData,
    submitOperation,
} = useInventoryOperationsPage();
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-operations' as *;
</style>
