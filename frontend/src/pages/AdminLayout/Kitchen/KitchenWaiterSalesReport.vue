<template>
    <div class="admin-page kitchen-waiter-sales-page">
        <header class="admin-page__header">
            <div>
                <h1 class="admin-page__title">Продажи официантов</h1>
                <p class="admin-page__subtitle">
                    {{ waiterModeDescription }}
                </p>
            </div>
            <div class="admin-page__header-actions">
                <Button :loading="loadingOptions" :disabled="loadingOptions || !canViewSalesReport" color="secondary" @click="loadOptions">
                    Обновить списки
                </Button>
                <Button :loading="loadingReport" :disabled="loadingReport || !canViewSalesReport" @click="buildReport">
                    Сформировать отчет
                </Button>
            </div>
        </header>

        <section v-if="!canViewSalesReport" class="admin-page__section">
            <div class="admin-page__empty">Недостаточно прав для просмотра отчета по продажам официантов.</div>
        </section>

        <section v-if="canViewSalesReport" class="kitchen-waiter-sales-page__filters-panel">
            <button
                type="button"
                class="kitchen-waiter-sales-page__filters-toggle"
                @click="isFiltersOpen = !isFiltersOpen"
            >
                Фильтры
                <span :class="['kitchen-waiter-sales-page__filters-icon', { 'is-open': isFiltersOpen }]">
                    ▼
                </span>
            </button>

            <div v-if="isFiltersOpen" class="kitchen-waiter-sales-page__filters-content">
                <div class="kitchen-waiter-sales-page__filters-grid">
                    <Select
                        v-model="restaurantId"
                        label="Ресторан"
                        :options="restaurantOptions"
                        placeholder="Все рестораны"
                    />
                    <Select
                        v-model="waiterMode"
                        label="Учет официанта"
                        :options="waiterModeOptions"
                    />
                    <Select
                        v-model="waiterKey"
                        label="Официант"
                        :options="waiterOptions"
                        placeholder="Все официанты"
                        searchable
                        search-placeholder="Начни вводить фамилию"
                    />
                    <Select
                        v-model="hallName"
                        label="Торговый зал"
                        :options="hallOptions"
                        placeholder="Все залы"
                    />
                    <DateInput v-model="fromDate" label="С даты" />
                    <DateInput v-model="toDate" label="По дату" />
                    <Select
                        v-model="deletedMode"
                        label="Удаленные"
                        :options="deletedModeOptions"
                    />
                </div>

                <div class="kitchen-waiter-sales-page__filters-grid kitchen-waiter-sales-page__filters-grid--wide">
                    <div class="kitchen-waiter-sales-page__multi-filter">
                        <p class="kitchen-waiter-sales-page__multi-filter-title">Включить группы</p>
                        <div class="kitchen-waiter-sales-page__multi-filter-input">
                            <Select
                                v-model="filterDraft.includeGroup"
                                :options="groupOptions"
                                placeholder="Выбери группу"
                                searchable
                                search-placeholder="Поиск группы"
                            />
                            <Button color="ghost" @click="addFilterValue('includeGroups', 'includeGroup')">
                                Добавить
                            </Button>
                        </div>
                        <div v-if="selectedFilters.includeGroups.length" class="kitchen-waiter-sales-page__chips">
                            <button
                                v-for="value in selectedFilters.includeGroups"
                                :key="`include-group-${value}`"
                                type="button"
                                class="kitchen-waiter-sales-page__chip"
                                @click="removeFilterValue('includeGroups', value)"
                            >
                                {{ value }} ✕
                            </button>
                        </div>
                    </div>

                    <div class="kitchen-waiter-sales-page__multi-filter">
                        <p class="kitchen-waiter-sales-page__multi-filter-title">Исключить группы</p>
                        <div class="kitchen-waiter-sales-page__multi-filter-input">
                            <Select
                                v-model="filterDraft.excludeGroup"
                                :options="groupOptions"
                                placeholder="Выбери группу"
                                searchable
                                search-placeholder="Поиск группы"
                            />
                            <Button color="ghost" @click="addFilterValue('excludeGroups', 'excludeGroup')">
                                Добавить
                            </Button>
                        </div>
                        <div v-if="selectedFilters.excludeGroups.length" class="kitchen-waiter-sales-page__chips">
                            <button
                                v-for="value in selectedFilters.excludeGroups"
                                :key="`exclude-group-${value}`"
                                type="button"
                                class="kitchen-waiter-sales-page__chip"
                                @click="removeFilterValue('excludeGroups', value)"
                            >
                                {{ value }} ✕
                            </button>
                        </div>
                    </div>

                    <div class="kitchen-waiter-sales-page__multi-filter">
                        <p class="kitchen-waiter-sales-page__multi-filter-title">Включить категории</p>
                        <div class="kitchen-waiter-sales-page__multi-filter-input">
                            <Select
                                v-model="filterDraft.includeCategory"
                                :options="categoryOptions"
                                placeholder="Выбери категорию"
                                searchable
                                search-placeholder="Поиск категории"
                            />
                            <Button color="ghost" @click="addFilterValue('includeCategories', 'includeCategory')">
                                Добавить
                            </Button>
                        </div>
                        <div v-if="selectedFilters.includeCategories.length" class="kitchen-waiter-sales-page__chips">
                            <button
                                v-for="value in selectedFilters.includeCategories"
                                :key="`include-category-${value}`"
                                type="button"
                                class="kitchen-waiter-sales-page__chip"
                                @click="removeFilterValue('includeCategories', value)"
                            >
                                {{ value }} ✕
                            </button>
                        </div>
                    </div>

                    <div class="kitchen-waiter-sales-page__multi-filter">
                        <p class="kitchen-waiter-sales-page__multi-filter-title">Исключить категории</p>
                        <div class="kitchen-waiter-sales-page__multi-filter-input">
                            <Select
                                v-model="filterDraft.excludeCategory"
                                :options="categoryOptions"
                                placeholder="Выбери категорию"
                                searchable
                                search-placeholder="Поиск категории"
                            />
                            <Button color="ghost" @click="addFilterValue('excludeCategories', 'excludeCategory')">
                                Добавить
                            </Button>
                        </div>
                        <div v-if="selectedFilters.excludeCategories.length" class="kitchen-waiter-sales-page__chips">
                            <button
                                v-for="value in selectedFilters.excludeCategories"
                                :key="`exclude-category-${value}`"
                                type="button"
                                class="kitchen-waiter-sales-page__chip"
                                @click="removeFilterValue('excludeCategories', value)"
                            >
                                {{ value }} ✕
                            </button>
                        </div>
                    </div>

                    <div class="kitchen-waiter-sales-page__multi-filter">
                        <p class="kitchen-waiter-sales-page__multi-filter-title">Включить позиции</p>
                        <div class="kitchen-waiter-sales-page__multi-filter-input">
                            <Select
                                v-model="filterDraft.includePosition"
                                :options="positionOptions"
                                placeholder="Выбери позицию"
                                searchable
                                search-placeholder="Поиск позиции"
                            />
                            <Button color="ghost" @click="addFilterValue('includePositions', 'includePosition')">
                                Добавить
                            </Button>
                        </div>
                        <div v-if="selectedFilters.includePositions.length" class="kitchen-waiter-sales-page__chips">
                            <button
                                v-for="value in selectedFilters.includePositions"
                                :key="`include-position-${value}`"
                                type="button"
                                class="kitchen-waiter-sales-page__chip"
                                @click="removeFilterValue('includePositions', value)"
                            >
                                {{ value }} ✕
                            </button>
                        </div>
                    </div>

                    <div class="kitchen-waiter-sales-page__multi-filter">
                        <p class="kitchen-waiter-sales-page__multi-filter-title">Исключить позиции</p>
                        <div class="kitchen-waiter-sales-page__multi-filter-input">
                            <Select
                                v-model="filterDraft.excludePosition"
                                :options="positionOptions"
                                placeholder="Выбери позицию"
                                searchable
                                search-placeholder="Поиск позиции"
                            />
                            <Button color="ghost" @click="addFilterValue('excludePositions', 'excludePosition')">
                                Добавить
                            </Button>
                        </div>
                        <div v-if="selectedFilters.excludePositions.length" class="kitchen-waiter-sales-page__chips">
                            <button
                                v-for="value in selectedFilters.excludePositions"
                                :key="`exclude-position-${value}`"
                                type="button"
                                class="kitchen-waiter-sales-page__chip"
                                @click="removeFilterValue('excludePositions', value)"
                            >
                                {{ value }} ✕
                            </button>
                        </div>
                    </div>

                    <div class="kitchen-waiter-sales-page__multi-filter">
                        <p class="kitchen-waiter-sales-page__multi-filter-title">Типы оплаты (только выбранные)</p>
                        <div class="kitchen-waiter-sales-page__multi-filter-input">
                            <Select
                                v-model="filterDraft.includePaymentType"
                                :options="paymentTypeOptions"
                                placeholder="Выбери тип оплаты"
                                searchable
                                search-placeholder="Поиск типа оплаты"
                            />
                            <Button color="ghost" @click="addFilterValue('includePaymentTypes', 'includePaymentType')">
                                Добавить
                            </Button>
                        </div>
                        <div v-if="selectedFilters.includePaymentTypes.length" class="kitchen-waiter-sales-page__chips">
                            <button
                                v-for="value in selectedFilters.includePaymentTypes"
                                :key="`include-payment-${value}`"
                                type="button"
                                class="kitchen-waiter-sales-page__chip"
                                @click="removeFilterValue('includePaymentTypes', value)"
                            >
                                {{ value }} ✕
                            </button>
                        </div>
                    </div>
                </div>

                <div class="kitchen-waiter-sales-page__filters-footer">
                    <p class="kitchen-waiter-sales-page__hint">
                        В списках: залов {{ optionsSummary.halls }}, групп {{ optionsSummary.groups }}, категорий {{ optionsSummary.categories }},
                        позиций {{ optionsSummary.positions }}, типов оплаты {{ optionsSummary.payment_types }}.
                    </p>
                    <Button color="ghost" @click="resetFilterLists">
                        Сбросить include/exclude
                    </Button>
                </div>
            </div>
        </section>

        <section v-if="canViewSalesReport" class="kitchen-waiter-sales-page__stats">
            <article class="kitchen-waiter-sales-page__stat-card">
                <p class="kitchen-waiter-sales-page__stat-label">Заказов</p>
                <p class="kitchen-waiter-sales-page__stat-value">{{ formatNumber(totals.orders_count) }}</p>
            </article>
            <article class="kitchen-waiter-sales-page__stat-card">
                <p class="kitchen-waiter-sales-page__stat-label">Гостей</p>
                <p class="kitchen-waiter-sales-page__stat-value">{{ formatNumber(totals.guests_count) }}</p>
            </article>
            <article class="kitchen-waiter-sales-page__stat-card">
                <p class="kitchen-waiter-sales-page__stat-label">Позиций</p>
                <p class="kitchen-waiter-sales-page__stat-value">{{ formatNumber(totals.items_count) }}</p>
            </article>
            <article class="kitchen-waiter-sales-page__stat-card">
                <p class="kitchen-waiter-sales-page__stat-label">Количество</p>
                <p class="kitchen-waiter-sales-page__stat-value">{{ formatNumber(totals.qty) }}</p>
            </article>
            <article class="kitchen-waiter-sales-page__stat-card">
                <p class="kitchen-waiter-sales-page__stat-label">Нагрузка кухни (коэф.)</p>
                <p class="kitchen-waiter-sales-page__stat-value">{{ formatNumber(totals.kitchen_load_qty) }}</p>
            </article>
            <article class="kitchen-waiter-sales-page__stat-card">
                <p class="kitchen-waiter-sales-page__stat-label">Нагрузка зала (коэф.)</p>
                <p class="kitchen-waiter-sales-page__stat-value">{{ formatNumber(totals.hall_load_qty) }}</p>
            </article>
            <article v-if="canViewSalesMoney" class="kitchen-waiter-sales-page__stat-card">
                <p class="kitchen-waiter-sales-page__stat-label">Продажи, руб</p>
                <p class="kitchen-waiter-sales-page__stat-value">{{ formatMoney(totals.sum) }}</p>
            </article>
            <article v-if="canViewSalesMoney" class="kitchen-waiter-sales-page__stat-card">
                <p class="kitchen-waiter-sales-page__stat-label">Скидки, руб</p>
                <p class="kitchen-waiter-sales-page__stat-value">{{ formatMoney(totals.discount_sum) }}</p>
            </article>
        </section>

        <section v-if="canViewSalesReport" class="admin-page__section">
            <h3 class="kitchen-waiter-sales-page__section-title">По официантам и ресторанам</h3>
            <Table v-if="sortedReportRows.length" class="kitchen-waiter-sales-page__table">
                <thead>
                    <tr>
                        <th v-for="column in reportColumns" :key="column.key">
                            <button
                                type="button"
                                class="kitchen-waiter-sales-page__sort-button"
                                @click="toggleSort(column.key)"
                            >
                                <span>{{ column.label }}</span>
                                <span class="kitchen-waiter-sales-page__sort-icons">
                                    <span
                                        class="kitchen-waiter-sales-page__sort-icon"
                                        :class="{ 'kitchen-waiter-sales-page__sort-icon--active': isSortedAsc(column.key) }"
                                    >
                                        ▲
                                    </span>
                                    <span
                                        class="kitchen-waiter-sales-page__sort-icon"
                                        :class="{ 'kitchen-waiter-sales-page__sort-icon--active': isSortedDesc(column.key) }"
                                    >
                                        ▼
                                    </span>
                                </span>
                            </button>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="row in sortedReportRows" :key="reportRowKey(row)">
                        <td>{{ row.restaurant_name || `#${row.restaurant_id}` }}</td>
                        <td>
                            <button
                                type="button"
                                class="kitchen-waiter-sales-page__waiter-link"
                                @click="openWaiterDetails(row)"
                            >
                                {{ waiterDisplayLabel(row) }}
                            </button>
                        </td>
                        <td>{{ row.waiter_name_iiko || '-' }}</td>
                        <td class="kitchen-waiter-sales-page__mono">{{ row.waiter_iiko_id || '-' }}</td>
                        <td>{{ formatNumber(row.orders_count) }}</td>
                        <td>{{ formatNumber(row.guests_count) }}</td>
                        <td>{{ formatNumber(row.items_count) }}</td>
                        <td>{{ formatNumber(row.qty) }}</td>
                        <td>{{ formatNumber(row.kitchen_load_qty) }}</td>
                        <td>{{ formatNumber(row.hall_load_qty) }}</td>
                        <td v-if="canViewSalesMoney">{{ formatMoney(row.sum) }}</td>
                        <td v-if="canViewSalesMoney">{{ formatMoney(row.discount_sum) }}</td>
                    </tr>
                </tbody>
            </Table>
            <div v-else-if="loadingReport" class="admin-page__empty">Формируем отчет...</div>
            <div v-else class="admin-page__empty">Нет данных по выбранным фильтрам.</div>
        </section>

        <section v-if="canViewSalesReport" class="admin-page__section">
            <h3 class="kitchen-waiter-sales-page__section-title">Итоги по ресторанам</h3>
            <Table v-if="totalsByRestaurant.length" class="kitchen-waiter-sales-page__table">
                <thead>
                    <tr>
                        <th>Ресторан</th>
                        <th>Заказов</th>
                        <th>Гостей</th>
                        <th>Позиций</th>
                        <th>Количество</th>
                        <th>Кухня (коэф.)</th>
                        <th>Зал (коэф.)</th>
                        <th v-if="canViewSalesMoney">Продажи, руб</th>
                        <th v-if="canViewSalesMoney">Скидки, руб</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="row in totalsByRestaurant" :key="row.restaurant_id">
                        <td>{{ row.restaurant_name || `#${row.restaurant_id}` }}</td>
                        <td>{{ formatNumber(row.orders_count) }}</td>
                        <td>{{ formatNumber(row.guests_count) }}</td>
                        <td>{{ formatNumber(row.items_count) }}</td>
                        <td>{{ formatNumber(row.qty) }}</td>
                        <td>{{ formatNumber(row.kitchen_load_qty) }}</td>
                        <td>{{ formatNumber(row.hall_load_qty) }}</td>
                        <td v-if="canViewSalesMoney">{{ formatMoney(row.sum) }}</td>
                        <td v-if="canViewSalesMoney">{{ formatMoney(row.discount_sum) }}</td>
                    </tr>
                </tbody>
            </Table>
            <div v-else-if="loadingReport" class="admin-page__empty">Загрузка итогов...</div>
            <div v-else class="admin-page__empty">Итоги по ресторанам отсутствуют.</div>
        </section>

        <section v-if="canViewSalesReport" class="admin-page__section">
            <h3 class="kitchen-waiter-sales-page__section-title">Итоги по официантам</h3>
            <Table v-if="totalsByWaiter.length" class="kitchen-waiter-sales-page__table">
                <thead>
                    <tr>
                        <th>Официант</th>
                        <th>iiko ID</th>
                        <th>Заказов</th>
                        <th>Гостей</th>
                        <th>Позиций</th>
                        <th>Количество</th>
                        <th>Кухня (коэф.)</th>
                        <th>Зал (коэф.)</th>
                        <th v-if="canViewSalesMoney">Продажи, руб</th>
                        <th v-if="canViewSalesMoney">Скидки, руб</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="row in totalsByWaiter" :key="waiterTotalKey(row)">
                        <td>{{ waiterDisplayLabel(row) }}</td>
                        <td class="kitchen-waiter-sales-page__mono">{{ row.waiter_iiko_id || '-' }}</td>
                        <td>{{ formatNumber(row.orders_count) }}</td>
                        <td>{{ formatNumber(row.guests_count) }}</td>
                        <td>{{ formatNumber(row.items_count) }}</td>
                        <td>{{ formatNumber(row.qty) }}</td>
                        <td>{{ formatNumber(row.kitchen_load_qty) }}</td>
                        <td>{{ formatNumber(row.hall_load_qty) }}</td>
                        <td v-if="canViewSalesMoney">{{ formatMoney(row.sum) }}</td>
                        <td v-if="canViewSalesMoney">{{ formatMoney(row.discount_sum) }}</td>
                    </tr>
                </tbody>
            </Table>
            <div v-else-if="loadingReport" class="admin-page__empty">Загрузка итогов...</div>
            <div v-else class="admin-page__empty">Итоги по официантам отсутствуют.</div>
        </section>

        <Modal v-if="waiterDetailsRow" @close="closeWaiterDetails">
            <template #header>
                <div class="kitchen-waiter-sales-page__modal-header">
                    <h3 class="kitchen-waiter-sales-page__modal-title">
                        Детализация позиций: {{ waiterDisplayLabel(waiterDetailsMeta || waiterDetailsRow) }}
                    </h3>
                    <p class="kitchen-waiter-sales-page__modal-subtitle">
                        Ресторан:
                        {{
                            waiterDetailsRow.restaurant_name ||
                            (waiterDetailsRow.restaurant_id ? `#${waiterDetailsRow.restaurant_id}` : '-')
                        }}
                        | iiko ID: {{ waiterDetailsMeta?.waiter_iiko_id || waiterDetailsRow.waiter_iiko_id || '-' }}
                        | iiko Code: {{ waiterDetailsMeta?.waiter_iiko_code || waiterDetailsRow.waiter_iiko_code || '-' }}
                    </p>
                </div>
            </template>

            <div class="kitchen-waiter-sales-page__detail-stats">
                <article class="kitchen-waiter-sales-page__detail-stat">
                    <p>Заказов</p>
                    <strong>{{ formatNumber(waiterDetailsTotals.orders_count) }}</strong>
                </article>
                <article class="kitchen-waiter-sales-page__detail-stat">
                    <p>Гостей</p>
                    <strong>{{ formatNumber(waiterDetailsTotals.guests_count) }}</strong>
                </article>
                <article class="kitchen-waiter-sales-page__detail-stat">
                    <p>Позиций</p>
                    <strong>{{ formatNumber(waiterDetailsTotals.items_count) }}</strong>
                </article>
                <article class="kitchen-waiter-sales-page__detail-stat">
                    <p>Количество</p>
                    <strong>{{ formatNumber(waiterDetailsTotals.qty) }}</strong>
                </article>
                <article class="kitchen-waiter-sales-page__detail-stat">
                    <p>Нагрузка кухни (коэф.)</p>
                    <strong>{{ formatNumber(waiterDetailsTotals.kitchen_load_qty) }}</strong>
                </article>
                <article class="kitchen-waiter-sales-page__detail-stat">
                    <p>Нагрузка зала (коэф.)</p>
                    <strong>{{ formatNumber(waiterDetailsTotals.hall_load_qty) }}</strong>
                </article>
                <article v-if="canViewSalesMoney" class="kitchen-waiter-sales-page__detail-stat">
                    <p>Продажи, руб</p>
                    <strong>{{ formatMoney(waiterDetailsTotals.sum) }}</strong>
                </article>
                <article v-if="canViewSalesMoney" class="kitchen-waiter-sales-page__detail-stat">
                    <p>Скидки, руб</p>
                    <strong>{{ formatMoney(waiterDetailsTotals.discount_sum) }}</strong>
                </article>
            </div>

            <div class="kitchen-waiter-sales-page__detail-filters">
                <Select
                    v-model="waiterDetailsCategoryFilter"
                    label="Категория"
                    :options="waiterDetailsCategoryOptions"
                    placeholder="Все категории"
                />
            </div>

            <Table v-if="sortedWaiterDetailsRows.length" class="kitchen-waiter-sales-page__table">
                <thead>
                    <tr>
                        <th v-for="column in waiterDetailsColumns" :key="column.key">
                            <button
                                type="button"
                                class="kitchen-waiter-sales-page__sort-button"
                                @click="toggleWaiterDetailsSort(column.key)"
                            >
                                <span>{{ column.label }}</span>
                                <span class="kitchen-waiter-sales-page__sort-icons">
                                    <span
                                        class="kitchen-waiter-sales-page__sort-icon"
                                        :class="{ 'kitchen-waiter-sales-page__sort-icon--active': isWaiterDetailsSortedAsc(column.key) }"
                                    >
                                        ▲
                                    </span>
                                    <span
                                        class="kitchen-waiter-sales-page__sort-icon"
                                        :class="{ 'kitchen-waiter-sales-page__sort-icon--active': isWaiterDetailsSortedDesc(column.key) }"
                                    >
                                        ▼
                                    </span>
                                </span>
                            </button>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="row in sortedWaiterDetailsRows" :key="waiterDetailRowKey(row)">
                        <td>{{ valueOrDash(row.dish_name) }}</td>
                        <td class="kitchen-waiter-sales-page__mono">{{ valueOrDash(row.dish_code) }}</td>
                        <td>{{ valueOrDash(row.dish_group) }}</td>
                        <td>{{ valueOrDash(row.dish_category) }}</td>
                        <td>{{ valueOrDash(row.dish_measure_unit) }}</td>
                        <td>{{ valueOrDash(row.payment_type) }}</td>
                        <td>{{ formatNumber(row.orders_count) }}</td>
                        <td>{{ formatNumber(row.items_count) }}</td>
                        <td>{{ formatNumber(row.qty) }}</td>
                        <td>{{ formatNumber(row.kitchen_load_qty) }}</td>
                        <td>{{ formatNumber(row.hall_load_qty) }}</td>
                        <td v-if="canViewSalesMoney">{{ formatMoney(row.sum) }}</td>
                        <td v-if="canViewSalesMoney">{{ formatMoney(row.discount_sum) }}</td>
                    </tr>
                </tbody>
            </Table>
            <div v-else-if="waiterDetailsLoading" class="admin-page__empty">Загрузка детализации...</div>
            <div v-else class="admin-page__empty">По выбранному официанту позиции не найдены.</div>

            <template #footer>
                <Button color="ghost" @click="closeWaiterDetails">Закрыть</Button>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import {
    fetchAllEmployees,
    fetchKitchenRestaurants,
    fetchKitchenWaiterSalesOptions,
    fetchKitchenWaiterSalesPositions,
    fetchKitchenWaiterSalesReport,
} from '@/api';
import { useDebounce } from '@/composables/useDebounce';
import { useToast } from 'vue-toastification';
import { useUserStore } from '@/stores/user';
import Button from '@/components/UI-components/Button.vue';
import Table from '@/components/UI-components/Table.vue';
import Select from '@/components/UI-components/Select.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Modal from '@/components/UI-components/Modal.vue';
import { formatNumberValue } from '@/utils/format';

const REPORT_COLUMNS = [
    { key: 'restaurant_name', label: 'Ресторан', type: 'text' },
    { key: 'waiter_name', label: 'Официант (наш)', type: 'text' },
    { key: 'waiter_name_iiko', label: 'Официант iiko', type: 'text' },
    { key: 'waiter_iiko_id', label: 'iiko ID', type: 'text' },
    { key: 'orders_count', label: 'Заказов', type: 'number' },
    { key: 'guests_count', label: 'Гостей', type: 'number' },
    { key: 'items_count', label: 'Позиций', type: 'number' },
    { key: 'qty', label: 'Кол-во', type: 'number' },
    { key: 'kitchen_load_qty', label: 'Кухня (коэф.)', type: 'number' },
    { key: 'hall_load_qty', label: 'Зал (коэф.)', type: 'number' },
    { key: 'sum', label: 'Продажи, руб', type: 'number' },
    { key: 'discount_sum', label: 'Скидки, руб', type: 'number' },
];

const WAITER_DETAILS_COLUMNS = [
    { key: 'dish_name', label: 'Позиция', type: 'text' },
    { key: 'dish_code', label: 'Код блюда', type: 'text' },
    { key: 'dish_group', label: 'Группа', type: 'text' },
    { key: 'dish_category', label: 'Категория', type: 'text' },
    { key: 'dish_measure_unit', label: 'Ед.', type: 'text' },
    { key: 'payment_type', label: 'Тип оплаты', type: 'text' },
    { key: 'orders_count', label: 'Заказов', type: 'number' },
    { key: 'items_count', label: 'Строк', type: 'number' },
    { key: 'qty', label: 'Кол-во', type: 'number' },
    { key: 'kitchen_load_qty', label: 'Кухня (коэф.)', type: 'number' },
    { key: 'hall_load_qty', label: 'Зал (коэф.)', type: 'number' },
    { key: 'sum', label: 'Сумма', type: 'number' },
    { key: 'discount_sum', label: 'Скидка', type: 'number' },
];

const FILTER_LIST_KEYS = [
    'includeGroups',
    'excludeGroups',
    'includeCategories',
    'excludeCategories',
    'includePositions',
    'excludePositions',
    'includePaymentTypes',
];
const DELETED_MODE_OPTIONS = [
    { value: 'without_deleted', label: 'Без удаленных' },
    { value: 'all', label: 'Все' },
    { value: 'only_deleted', label: 'Только удаленные' },
];
const WAITER_MODE_OPTIONS = [
    { value: 'order_close', label: 'По закрытию заказа' },
    { value: 'item_punch', label: 'По пробитию позиции' },
];

const userStore = useUserStore();
const toast = useToast();
const canViewSalesReport = computed(() =>
    userStore.hasAnyPermission(
        'sales.report.view_qty',
        'sales.report.view_money',
        'iiko.view',
        'iiko.manage',
    ),
);
const canViewSalesMoney = computed(() =>
    userStore.hasAnyPermission('sales.report.view_money', 'iiko.view', 'iiko.manage'),
);
const defaultSortMetricKey = computed(() => (canViewSalesMoney.value ? 'sum' : 'qty'));

const loadingOptions = ref(false);
const loadingReport = ref(false);
const isFiltersOpen = ref(true);
let optionsLoadAbortController = null;
let reportLoadAbortController = null;
let waiterDetailsAbortController = null;
let optionsLoadRequestSeq = 0;
let reportLoadRequestSeq = 0;
let waiterDetailsRequestSeq = 0;

const restaurants = ref([]);
const waiters = ref([]);
const employeeDirectory = ref([]);
const optionsPayload = ref({
    halls: [],
    groups: [],
    categories: [],
    positions: [],
    payment_types: [],
});

const selectedFilters = reactive({
    includeGroups: [],
    excludeGroups: [],
    includeCategories: [],
    excludeCategories: [],
    includePositions: [],
    excludePositions: [],
    includePaymentTypes: [],
});

const filterDraft = reactive({
    includeGroup: '',
    excludeGroup: '',
    includeCategory: '',
    excludeCategory: '',
    includePosition: '',
    excludePosition: '',
    includePaymentType: '',
});

const restaurantId = ref('');
const waiterMode = ref('order_close');
const waiterKey = ref('');
const hallName = ref('');
const fromDate = ref(defaultMonthStart());
const toDate = ref(defaultToday());
const deletedMode = ref('without_deleted');

const reportRows = ref([]);
const totalsByRestaurant = ref([]);
const totalsByWaiter = ref([]);
const totals = ref({
    orders_count: 0,
    guests_count: 0,
    items_count: 0,
    qty: 0,
    kitchen_load_qty: 0,
    hall_load_qty: 0,
    sum: 0,
    discount_sum: 0,
});
const waiterDetailsRow = ref(null);
const waiterDetailsMeta = ref(null);
const waiterDetailsRows = ref([]);
const waiterDetailsLoading = ref(false);
const waiterDetailsTotals = ref({
    orders_count: 0,
    guests_count: 0,
    items_count: 0,
    qty: 0,
    kitchen_load_qty: 0,
    hall_load_qty: 0,
    sum: 0,
    discount_sum: 0,
});
const waiterDetailsSortBy = ref(defaultSortMetricKey.value);
const waiterDetailsSortDirection = ref('desc');
const waiterDetailsCategoryFilter = ref('');

const sortBy = ref(defaultSortMetricKey.value);
const sortDirection = ref('desc');

const reportColumns = computed(() =>
    canViewSalesMoney.value
        ? REPORT_COLUMNS
        : REPORT_COLUMNS.filter((column) => column.key !== 'sum' && column.key !== 'discount_sum'),
);
const waiterDetailsColumns = computed(() =>
    canViewSalesMoney.value
        ? WAITER_DETAILS_COLUMNS
        : WAITER_DETAILS_COLUMNS.filter((column) => column.key !== 'sum' && column.key !== 'discount_sum'),
);

const restaurantOptions = computed(() => [
    { value: '', label: 'Все рестораны' },
    ...(restaurants.value || []).map((item) => ({ value: String(item.id), label: item.name })),
]);
const employeeDirectoryMap = computed(() =>
    new Map(
        (employeeDirectory.value || [])
            .map((employee) => [Number(employee?.id), employee])
            .filter(([id]) => Number.isFinite(id) && id > 0),
    ),
);

const waiterOptions = computed(() => [
    { value: '', label: 'Все официанты' },
    ...(waiters.value || [])
        .filter((row) => row?.user_id !== null || row?.iiko_id || row?.iiko_code)
        .map((row) => ({
            value: waiterOptionValue(row),
            label: waiterDisplayLabel(row),
        })),
]);
const deletedModeOptions = computed(() => DELETED_MODE_OPTIONS);
const waiterModeOptions = computed(() => WAITER_MODE_OPTIONS);
const waiterModeDescription = computed(() =>
    waiterMode.value === 'item_punch'
        ? 'Отчет по пробитию позиций (Dish/Item waiter) с фильтрами по группам, категориям и позициям.'
        : 'Отчет по закрытым заказам (Order waiter) с фильтрами по группам, категориям и позициям.',
);

const groupOptions = computed(() => mapToSelectOptions(optionsPayload.value?.groups));
const categoryOptions = computed(() => mapToSelectOptions(optionsPayload.value?.categories));
const positionOptions = computed(() => mapToSelectOptions(optionsPayload.value?.positions));
const paymentTypeOptions = computed(() => mapToSelectOptions(optionsPayload.value?.payment_types));
const hallOptions = computed(() => [
    { value: '', label: 'Все залы' },
    ...mapToSelectOptions(optionsPayload.value?.halls),
]);

const optionsSummary = computed(() => ({
    halls: (optionsPayload.value?.halls || []).length,
    groups: (optionsPayload.value?.groups || []).length,
    categories: (optionsPayload.value?.categories || []).length,
    positions: (optionsPayload.value?.positions || []).length,
    payment_types: (optionsPayload.value?.payment_types || []).length,
}));

const waiterDetailsCategoryOptions = computed(() => {
    const categories = Array.from(
        new Set(
            (waiterDetailsRows.value || [])
                .map((row) => String(row?.dish_category || '').trim())
                .filter(Boolean),
        ),
    ).sort((a, b) => a.localeCompare(b, 'ru', { sensitivity: 'base' }));
    return [{ value: '', label: 'Все категории' }, ...categories.map((value) => ({ value, label: value }))];
});

const sortedReportRows = computed(() => {
    const column = reportColumns.value.find((item) => item.key === sortBy.value);
    const direction = sortDirection.value === 'desc' ? -1 : 1;
    return [...reportRows.value].sort((a, b) => {
        const aValue = getSortValue(a, sortBy.value, column?.type);
        const bValue = getSortValue(b, sortBy.value, column?.type);
        return compareSortValues(aValue, bValue, column?.type) * direction;
    });
});

const filteredWaiterDetailsRows = computed(() => {
    const category = String(waiterDetailsCategoryFilter.value || '').trim();
    if (!category) {
        return waiterDetailsRows.value;
    }
    return waiterDetailsRows.value.filter((row) => String(row?.dish_category || '').trim() === category);
});

const sortedWaiterDetailsRows = computed(() => {
    const column = waiterDetailsColumns.value.find((item) => item.key === waiterDetailsSortBy.value);
    const direction = waiterDetailsSortDirection.value === 'desc' ? -1 : 1;
    return [...filteredWaiterDetailsRows.value].sort((a, b) => {
        const aValue = getSortValue(a, waiterDetailsSortBy.value, column?.type);
        const bValue = getSortValue(b, waiterDetailsSortBy.value, column?.type);
        return compareSortValues(aValue, bValue, column?.type) * direction;
    });
});

function isRequestCanceled(error) {
    return (
        error?.code === 'ERR_CANCELED' ||
        error?.name === 'CanceledError' ||
        error?.message === 'canceled' ||
        error?.message === 'Request canceled'
    );
}

const debouncedLoadOptions = useDebounce(() => {
    void loadOptions();
}, 180);

watch(restaurantId, () => {
    debouncedLoadOptions();
});

watch(waiterMode, () => {
    waiterKey.value = '';
    if (waiterDetailsRow.value) {
        closeWaiterDetails();
    }
    debouncedLoadOptions();
});

watch(canViewSalesMoney, (allowed) => {
    if (allowed) {
        return;
    }
    if (sortBy.value === 'sum' || sortBy.value === 'discount_sum') {
        sortBy.value = 'qty';
        sortDirection.value = 'desc';
    }
    if (waiterDetailsSortBy.value === 'sum' || waiterDetailsSortBy.value === 'discount_sum') {
        waiterDetailsSortBy.value = 'qty';
        waiterDetailsSortDirection.value = 'desc';
    }
});

function defaultToday() {
    return new Date().toISOString().slice(0, 10);
}

function defaultMonthStart() {
    const dt = new Date();
    dt.setDate(1);
    return dt.toISOString().slice(0, 10);
}

function reportRowKey(row) {
    return `${row.restaurant_id || 'none'}:${row.waiter_user_id || 'none'}:${row.waiter_iiko_id || 'none'}:${row.waiter_iiko_code || 'none'}`;
}

function waiterTotalKey(row) {
    return `${row.waiter_user_id || 'none'}:${row.waiter_iiko_id || 'none'}:${row.waiter_iiko_code || 'none'}`;
}

function waiterDetailRowKey(row) {
    return `${row.restaurant_id || 'none'}:${row.dish_code || 'none'}:${row.payment_type || 'none'}:${row.dish_name || 'none'}`;
}

function valueOrDash(value) {
    if (value === null || value === undefined || value === '') {
        return '-';
    }
    return String(value);
}

function formatEmployeeName(employee) {
    const parts = [employee?.last_name, employee?.first_name, employee?.middle_name]
        .map((part) => (part || '').trim())
        .filter(Boolean);
    if (parts.length) {
        return parts.join(' ');
    }
    return String(employee?.username || employee?.staff_code || employee?.id || '').trim();
}

function waiterDisplayLabel(row) {
    const directName = String(
        row?.waiter_name ??
        row?.name ??
        row?.user_name ??
        '',
    ).trim();
    if (directName) {
        return directName;
    }
    const employee = employeeDirectoryMap.value.get(Number(row?.waiter_user_id ?? row?.user_id));
    if (employee) {
        return formatEmployeeName(employee);
    }
    if (row?.waiter_iiko_code || row?.iiko_code) {
        return String(row.waiter_iiko_code || row.iiko_code);
    }
    if (row?.waiter_iiko_id || row?.iiko_id) {
        return String(row.waiter_iiko_id || row.iiko_id);
    }
    if (row?.waiter_user_id || row?.user_id) {
        return `#${row.waiter_user_id ?? row.user_id}`;
    }
    return '-';
}

function waiterOptionValue(row) {
    if (row?.user_id !== null && row?.user_id !== undefined) {
        return `user:${row.user_id}`;
    }
    if (row?.iiko_id) {
        return `iiko:${row.iiko_id}`;
    }
    if (row?.iiko_code) {
        return `code:${row.iiko_code}`;
    }
    return '';
}

function mapToSelectOptions(values) {
    return (values || []).map((value) => ({
        value,
        label: value,
    }));
}

function normalizeValue(value) {
    return String(value || '').trim().toLowerCase();
}

function addFilterValue(listKey, draftKey) {
    const value = String(filterDraft[draftKey] || '').trim();
    if (!value) {
        return;
    }
    const list = selectedFilters[listKey];
    if (!Array.isArray(list)) {
        return;
    }
    const newKey = normalizeValue(value);
    if (!list.some((item) => normalizeValue(item) === newKey)) {
        selectedFilters[listKey] = [...list, value];
    }
    filterDraft[draftKey] = '';
}

function removeFilterValue(listKey, value) {
    const list = selectedFilters[listKey];
    if (!Array.isArray(list)) {
        return;
    }
    selectedFilters[listKey] = list.filter((item) => item !== value);
}

function keepOnlyExistingValues(values, dictionaryValues) {
    const dictionarySet = new Set((dictionaryValues || []).map((item) => normalizeValue(item)));
    return (values || []).filter((value) => dictionarySet.has(normalizeValue(value)));
}

function syncSelectedFiltersWithOptions() {
    selectedFilters.includeGroups = keepOnlyExistingValues(
        selectedFilters.includeGroups,
        optionsPayload.value?.groups,
    );
    selectedFilters.excludeGroups = keepOnlyExistingValues(
        selectedFilters.excludeGroups,
        optionsPayload.value?.groups,
    );
    selectedFilters.includeCategories = keepOnlyExistingValues(
        selectedFilters.includeCategories,
        optionsPayload.value?.categories,
    );
    selectedFilters.excludeCategories = keepOnlyExistingValues(
        selectedFilters.excludeCategories,
        optionsPayload.value?.categories,
    );
    selectedFilters.includePositions = keepOnlyExistingValues(
        selectedFilters.includePositions,
        optionsPayload.value?.positions,
    );
    selectedFilters.excludePositions = keepOnlyExistingValues(
        selectedFilters.excludePositions,
        optionsPayload.value?.positions,
    );
    selectedFilters.includePaymentTypes = keepOnlyExistingValues(
        selectedFilters.includePaymentTypes,
        optionsPayload.value?.payment_types,
    );
}

function resetFilterLists() {
    for (const key of FILTER_LIST_KEYS) {
        selectedFilters[key] = [];
    }
    filterDraft.includeGroup = '';
    filterDraft.excludeGroup = '';
    filterDraft.includeCategory = '';
    filterDraft.excludeCategory = '';
    filterDraft.includePosition = '';
    filterDraft.excludePosition = '';
    filterDraft.includePaymentType = '';
}

function ensureValidDates() {
    if (!fromDate.value || !toDate.value) {
        toast.error('Укажи период отчета');
        return false;
    }
    if (fromDate.value > toDate.value) {
        toast.error('Дата "С" не может быть позже даты "По"');
        return false;
    }
    return true;
}

function formatNumber(value) {
    const parsed = Number(value);
    return formatNumberValue(parsed, {
        emptyValue: '0',
        invalidValue: '0',
        locale: 'ru-RU',
        minimumFractionDigits: Number.isInteger(parsed) ? 0 : 2,
        maximumFractionDigits: 2,
    });
}

function formatMoney(value) {
    return formatNumberValue(value, {
        emptyValue: '0,00',
        invalidValue: '0,00',
        locale: 'ru-RU',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

function isSortedAsc(columnKey) {
    return sortBy.value === columnKey && sortDirection.value === 'asc';
}

function isSortedDesc(columnKey) {
    return sortBy.value === columnKey && sortDirection.value === 'desc';
}

function toggleSort(columnKey) {
    if (sortBy.value === columnKey) {
        sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
        return;
    }
    sortBy.value = columnKey;
    sortDirection.value = 'asc';
}

function isWaiterDetailsSortedAsc(columnKey) {
    return waiterDetailsSortBy.value === columnKey && waiterDetailsSortDirection.value === 'asc';
}

function isWaiterDetailsSortedDesc(columnKey) {
    return waiterDetailsSortBy.value === columnKey && waiterDetailsSortDirection.value === 'desc';
}

function toggleWaiterDetailsSort(columnKey) {
    if (waiterDetailsSortBy.value === columnKey) {
        waiterDetailsSortDirection.value = waiterDetailsSortDirection.value === 'asc' ? 'desc' : 'asc';
        return;
    }
    waiterDetailsSortBy.value = columnKey;
    waiterDetailsSortDirection.value = 'asc';
}

function getSortValue(row, key, type) {
    const value = row?.[key];
    if (value === null || value === undefined || value === '') {
        return null;
    }
    if (type === 'number') {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : null;
    }
    return String(value).trim();
}

function compareSortValues(aValue, bValue, type) {
    const aEmpty = aValue === null;
    const bEmpty = bValue === null;
    if (aEmpty && bEmpty) {
        return 0;
    }
    if (aEmpty) {
        return 1;
    }
    if (bEmpty) {
        return -1;
    }
    if (type === 'number') {
        return Number(aValue) - Number(bValue);
    }
    return String(aValue).localeCompare(String(bValue), 'ru', { sensitivity: 'base' });
}

function buildBaseParams() {
    const params = new URLSearchParams();
    params.append('from_date', fromDate.value);
    params.append('to_date', toDate.value);
    params.append('deleted_mode', deletedMode.value);
    params.append('waiter_mode', waiterMode.value);
    if (restaurantId.value) {
        params.append('restaurant_id', restaurantId.value);
    }
    return params;
}

function appendListParam(params, key, values) {
    for (const value of values || []) {
        params.append(key, value);
    }
}

function appendCommonFilters(params) {
    if (hallName.value) {
        params.append('include_halls', hallName.value);
    }
    appendListParam(params, 'include_groups', selectedFilters.includeGroups);
    appendListParam(params, 'exclude_groups', selectedFilters.excludeGroups);
    appendListParam(params, 'include_categories', selectedFilters.includeCategories);
    appendListParam(params, 'exclude_categories', selectedFilters.excludeCategories);
    appendListParam(params, 'include_positions', selectedFilters.includePositions);
    appendListParam(params, 'exclude_positions', selectedFilters.excludePositions);
    appendListParam(params, 'include_payment_types', selectedFilters.includePaymentTypes);
}

function waiterParamsFromKey(params) {
    const value = String(waiterKey.value || '').trim();
    if (!value) {
        return;
    }
    if (value.startsWith('user:')) {
        const parsed = Number(value.slice(5));
        if (Number.isFinite(parsed)) {
            params.append('waiter_user_id', String(parsed));
        }
        return;
    }
    if (value.startsWith('iiko:')) {
        const iikoId = value.slice(5).trim();
        if (iikoId) {
            params.append('waiter_iiko_id', iikoId);
        }
        return;
    }
    if (value.startsWith('code:')) {
        const iikoCode = value.slice(5).trim();
        if (iikoCode) {
            params.append('waiter_iiko_code', iikoCode);
        }
    }
}

async function loadRestaurants() {
    const data = await fetchKitchenRestaurants();
    restaurants.value = Array.isArray(data) ? data : [];
}

async function loadEmployeeDirectory() {
    try {
        const data = await fetchAllEmployees({ include_fired: true, limit: 250 });
        employeeDirectory.value = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];
    } catch (error) {
        console.warn('Не удалось загрузить справочник сотрудников для отчета официантов', error);
    }
}

async function loadOptions() {
    if (!canViewSalesReport.value) {
        return;
    }
    if (!ensureValidDates()) {
        return;
    }
    if (optionsLoadAbortController) {
        optionsLoadAbortController.abort();
        optionsLoadAbortController = null;
    }
    const abortController = new AbortController();
    optionsLoadAbortController = abortController;
    const requestSeq = ++optionsLoadRequestSeq;
    loadingOptions.value = true;
    try {
        const payload = (await fetchKitchenWaiterSalesOptions(buildBaseParams(), {
            signal: abortController.signal,
        })) || {};
        if (requestSeq !== optionsLoadRequestSeq || abortController.signal.aborted) {
            return;
        }
        waiters.value = Array.isArray(payload.waiters) ? payload.waiters : [];
        optionsPayload.value = {
            halls: Array.isArray(payload.halls) ? payload.halls : [],
            groups: Array.isArray(payload.groups) ? payload.groups : [],
            categories: Array.isArray(payload.categories) ? payload.categories : [],
            positions: Array.isArray(payload.positions) ? payload.positions : [],
            payment_types: Array.isArray(payload.payment_types) ? payload.payment_types : [],
        };

        if (
            waiterKey.value &&
            !waiterOptions.value.some((option) => option.value === waiterKey.value)
        ) {
            waiterKey.value = '';
        }
        if (
            hallName.value &&
            !hallOptions.value.some((option) => option.value === hallName.value)
        ) {
            hallName.value = '';
        }

        syncSelectedFiltersWithOptions();
    } catch (error) {
        if (isRequestCanceled(error) || requestSeq !== optionsLoadRequestSeq) {
            return;
        }
        toast.error(`Ошибка загрузки опций фильтров: ${error.response?.data?.detail || error.message}`);
    } finally {
        if (requestSeq === optionsLoadRequestSeq) {
            loadingOptions.value = false;
        }
        if (optionsLoadAbortController === abortController) {
            optionsLoadAbortController = null;
        }
    }
}

async function buildReport() {
    if (!canViewSalesReport.value) {
        toast.error('Недостаточно прав для построения отчета');
        return;
    }
    if (!ensureValidDates()) {
        return;
    }

    if (reportLoadAbortController) {
        reportLoadAbortController.abort();
        reportLoadAbortController = null;
    }
    const abortController = new AbortController();
    reportLoadAbortController = abortController;
    const requestSeq = ++reportLoadRequestSeq;
    loadingReport.value = true;
    try {
        const params = buildBaseParams();
        waiterParamsFromKey(params);
        appendCommonFilters(params);

        const payload = (await fetchKitchenWaiterSalesReport(params, {
            signal: abortController.signal,
        })) || {};
        if (requestSeq !== reportLoadRequestSeq || abortController.signal.aborted) {
            return;
        }
        reportRows.value = Array.isArray(payload.items) ? payload.items : [];
        totalsByRestaurant.value = Array.isArray(payload.totals_by_restaurant) ? payload.totals_by_restaurant : [];
        totalsByWaiter.value = Array.isArray(payload.totals_by_waiter) ? payload.totals_by_waiter : [];
        totals.value = {
            orders_count: Number(payload.totals?.orders_count || 0),
            guests_count: Number(payload.totals?.guests_count || 0),
            items_count: Number(payload.totals?.items_count || 0),
            qty: Number(payload.totals?.qty || 0),
            kitchen_load_qty: Number(payload.totals?.kitchen_load_qty || 0),
            hall_load_qty: Number(payload.totals?.hall_load_qty || 0),
            sum: Number(payload.totals?.sum || 0),
            discount_sum: Number(payload.totals?.discount_sum || 0),
        };

        if (waiterDetailsRow.value) {
            closeWaiterDetails();
        }
    } catch (error) {
        if (isRequestCanceled(error) || requestSeq !== reportLoadRequestSeq) {
            return;
        }
        toast.error(`Ошибка построения отчета: ${error.response?.data?.detail || error.message}`);
    } finally {
        if (requestSeq === reportLoadRequestSeq) {
            loadingReport.value = false;
        }
        if (reportLoadAbortController === abortController) {
            reportLoadAbortController = null;
        }
    }
}

function resetWaiterDetailsTotals() {
    waiterDetailsTotals.value = {
        orders_count: 0,
        guests_count: 0,
        items_count: 0,
        qty: 0,
        kitchen_load_qty: 0,
        hall_load_qty: 0,
        sum: 0,
        discount_sum: 0,
    };
}

function closeWaiterDetails() {
    if (waiterDetailsAbortController) {
        waiterDetailsAbortController.abort();
        waiterDetailsAbortController = null;
    }
    waiterDetailsRow.value = null;
    waiterDetailsMeta.value = null;
    waiterDetailsRows.value = [];
    waiterDetailsLoading.value = false;
    waiterDetailsCategoryFilter.value = '';
    waiterDetailsSortBy.value = defaultSortMetricKey.value;
    waiterDetailsSortDirection.value = 'desc';
    resetWaiterDetailsTotals();
}

async function openWaiterDetails(row) {
    if (!row) {
        return;
    }
    waiterDetailsRow.value = row;
    waiterDetailsMeta.value = null;
    waiterDetailsRows.value = [];
    waiterDetailsCategoryFilter.value = '';
    waiterDetailsSortBy.value = defaultSortMetricKey.value;
    waiterDetailsSortDirection.value = 'desc';
    resetWaiterDetailsTotals();
    if (waiterDetailsAbortController) {
        waiterDetailsAbortController.abort();
        waiterDetailsAbortController = null;
    }
    const abortController = new AbortController();
    waiterDetailsAbortController = abortController;
    const requestSeq = ++waiterDetailsRequestSeq;
    waiterDetailsLoading.value = true;

    try {
        const params = buildBaseParams();
        if (row.restaurant_id !== null && row.restaurant_id !== undefined) {
            params.set('restaurant_id', String(row.restaurant_id));
        }

        if (row.waiter_user_id !== null && row.waiter_user_id !== undefined) {
            params.append('waiter_user_id', String(row.waiter_user_id));
        } else if (row.waiter_iiko_id) {
            params.append('waiter_iiko_id', String(row.waiter_iiko_id));
        } else if (row.waiter_iiko_code) {
            params.append('waiter_iiko_code', String(row.waiter_iiko_code));
        } else {
            throw new Error('У официанта нет идентификатора для детализации');
        }

        appendCommonFilters(params);

        const payload = (await fetchKitchenWaiterSalesPositions(params, {
            signal: abortController.signal,
        })) || {};
        if (requestSeq !== waiterDetailsRequestSeq || abortController.signal.aborted) {
            return;
        }
        waiterDetailsMeta.value = payload.waiter || null;
        waiterDetailsRows.value = Array.isArray(payload.items) ? payload.items : [];
        waiterDetailsTotals.value = {
            orders_count: Number(payload.totals?.orders_count || 0),
            guests_count: Number(payload.totals?.guests_count || 0),
            items_count: Number(payload.totals?.items_count || 0),
            qty: Number(payload.totals?.qty || 0),
            kitchen_load_qty: Number(payload.totals?.kitchen_load_qty || 0),
            hall_load_qty: Number(payload.totals?.hall_load_qty || 0),
            sum: Number(payload.totals?.sum || 0),
            discount_sum: Number(payload.totals?.discount_sum || 0),
        };
    } catch (error) {
        if (isRequestCanceled(error) || requestSeq !== waiterDetailsRequestSeq) {
            return;
        }
        toast.error(`Ошибка загрузки детализации официанта: ${error.response?.data?.detail || error.message}`);
        closeWaiterDetails();
    } finally {
        if (requestSeq === waiterDetailsRequestSeq) {
            waiterDetailsLoading.value = false;
        }
        if (waiterDetailsAbortController === abortController) {
            waiterDetailsAbortController = null;
        }
    }
}

onMounted(async () => {
    if (!canViewSalesReport.value) {
        return;
    }
    try {
        await Promise.all([loadRestaurants(), loadEmployeeDirectory()]);
        await loadOptions();
        await buildReport();
    } catch (error) {
        if (isRequestCanceled(error)) {
            return;
        }
        toast.error(`Ошибка инициализации отчета: ${error.response?.data?.detail || error.message}`);
    }
});
onBeforeUnmount(() => {
    debouncedLoadOptions.cancel?.();
    if (optionsLoadAbortController) {
        optionsLoadAbortController.abort();
        optionsLoadAbortController = null;
    }
    if (reportLoadAbortController) {
        reportLoadAbortController.abort();
        reportLoadAbortController = null;
    }
    if (waiterDetailsAbortController) {
        waiterDetailsAbortController.abort();
        waiterDetailsAbortController = null;
    }
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kitchen-waiter-sales-report' as *;
</style>
