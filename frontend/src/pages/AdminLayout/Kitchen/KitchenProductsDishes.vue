<template>
    <div class="admin-page kitchen-products-page">
        <header class="admin-page__header">
            <div>
                <h1 class="admin-page__title">Товары и блюда</h1>
                <p class="admin-page__subtitle">Откройте любую позицию, чтобы посмотреть техкарту и сырые данные iiko.</p>
            </div>
            <div class="admin-page__header-actions">
                <Button color="secondary" :loading="loading" :disabled="loading" @click="loadProducts">
                    Обновить список
                </Button>
                <Button
                    v-if="canSyncNomenclature"
                    :loading="syncingNetwork"
                    :disabled="syncingNetwork"
                    @click="syncProductsNetwork"
                >
                    {{ syncingNetwork ? 'Синхронизация...' : 'Обновить номенклатуру' }}
                </Button>
            </div>
        </header>

        <section class="kitchen-products-page__filters">
            <Input v-model="searchText" label="Поиск" placeholder="Название, ID, код..." />
            <Select v-model="selectedType" label="Тип номенклатуры" :options="typeOptionsWithAll" placeholder="Все" />
            <Select
                v-model="selectedParentGroup"
                label="Родительская группа"
                :options="parentGroupOptionsWithAll"
                placeholder="Все"
            />
        </section>

        <p v-if="networkSyncSummary" class="kitchen-products-page__summary">{{ networkSyncSummary }}</p>
        <p v-if="!loading" class="kitchen-products-page__summary">Найдено: {{ hierarchyProducts.length }}</p>

        <section class="kitchen-products-page__tree-card">
            <div class="kitchen-products-page__tree-actions">
                <Button color="ghost" @click="collapseAllBranches">Свернуть все</Button>
                <Button color="ghost" @click="expandAllBranches">Развернуть все</Button>
            </div>

            <div v-if="loading" class="admin-page__empty">Загрузка номенклатуры...</div>

            <div v-else-if="hierarchyProducts.length" class="kitchen-products-page__tree">
                <div
                    v-for="(entry, index) in hierarchyProducts"
                    :key="entry.nodeId || entry.row?.id || `row-${index}`"
                    class="kitchen-products-page__tree-entry"
                >
                    <div
                        :class="[
                            'kitchen-products-page__line',
                            { 'kitchen-products-page__line--expandable': entry.hasChildren },
                        ]"
                        :style="getTreeIndentStyle(entry.level)"
                    >
                        <button
                            v-if="entry.hasChildren"
                            type="button"
                            class="kitchen-products-page__tree-toggle"
                            :aria-label="entry.isCollapsed ? 'Развернуть группу' : 'Свернуть группу'"
                            @click.stop="toggleBranch(entry.nodeId)"
                        >
                            {{ entry.isCollapsed ? '▸' : '▾' }}
                        </button>
                        <span v-else class="kitchen-products-page__tree-marker kitchen-products-page__tree-marker--leaf">•</span>

                        <div
                            v-if="entry.nodeKind === 'product'"
                            :class="[
                                'kitchen-products-page__line-main',
                                { 'kitchen-products-page__line-main--expandable': entry.hasChildren },
                            ]"
                            role="button"
                            tabindex="0"
                            @click="handleEntryMainClick(entry)"
                            @keydown.enter.prevent="handleEntryMainClick(entry)"
                            @keydown.space.prevent="handleEntryMainClick(entry)"
                        >
                            <div class="kitchen-products-page__line-content">
                                <span class="kitchen-products-page__row-title">{{ valueOrDash(entry.row.name) }}</span>
                                <div class="kitchen-products-page__line-tags">
                                    <span class="kitchen-products-page__line-tag">
                                        {{ valueOrDash(resolveDisplayProductType(entry.row)) }}
                                    </span>
                                    <span class="kitchen-products-page__line-tag">
                                        {{ valueOrDash(formatCategoryNodeLabel(resolveCategoryKey(entry.row))) }}
                                    </span>
                                    <span class="kitchen-products-page__line-tag">
                                        Ед.: {{ valueOrDash(resolveDisplayMainUnit(entry.row)) }}
                                    </span>
                                    <span class="kitchen-products-page__line-tag kitchen-products-page__line-tag--accent">
                                        Нагрузка кухни: ×{{ formatCoefficientTag(entry.row.portion_coef_kitchen) }}
                                    </span>
                                    <span class="kitchen-products-page__line-tag kitchen-products-page__line-tag--accent">
                                        Нагрузка зала: ×{{ formatCoefficientTag(entry.row.portion_coef_hall) }}
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div
                            v-else
                            :class="[
                                'kitchen-products-page__line-main',
                                'kitchen-products-page__line-main--static',
                                { 'kitchen-products-page__line-main--expandable': entry.hasChildren },
                            ]"
                            :role="entry.hasChildren ? 'button' : undefined"
                            :tabindex="entry.hasChildren ? 0 : -1"
                            @click="handleEntryMainClick(entry)"
                            @keydown.enter.prevent="handleEntryMainClick(entry)"
                            @keydown.space.prevent="handleEntryMainClick(entry)"
                        >
                            <div class="kitchen-products-page__line-content">
                                <span class="kitchen-products-page__row-title">{{ entry.label }}</span>
                                <div class="kitchen-products-page__line-tags">
                                    <span class="kitchen-products-page__line-tag">
                                        Позиций: {{ formatNumber(entry.itemsCount) }}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div class="kitchen-products-page__line-actions">
                            <Button
                                v-if="entry.nodeKind === 'product'"
                                color="ghost"
                                class="kitchen-products-page__folder-action"
                                @click.stop="openProductCard(entry.row)"
                            >
                                Карточка
                            </Button>
                            <Button
                                v-if="entry.hasChildren && canEditCatalog"
                                color="ghost"
                                class="kitchen-products-page__folder-action"
                                @click.stop="openFolderCoefficients(entry)"
                            >
                                Коэф. папки
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            <div v-else class="admin-page__empty">Номенклатура не найдена по выбранным фильтрам.</div>
        </section>

        <Modal v-if="selectedProduct" class="kitchen-products-page__modal" @close="closeProductCard">
            <template #header>
                <div class="kitchen-products-page__modal-header">
                    <h3 class="kitchen-products-page__modal-title">{{ selectedProduct.name || 'Карточка номенклатуры' }}</h3>
                    <p class="kitchen-products-page__modal-subtitle">
                        {{ valueOrDash(resolveDisplayProductType(selectedProduct)) }}
                        •
                        {{ valueOrDash(resolveDisplayCategory(selectedProduct.product_category)) }}
                        • Ед.: {{ valueOrDash(resolveDisplayMainUnit(selectedProduct)) }}
                    </p>
                    <p class="kitchen-products-page__modal-subtitle kitchen-products-page__modal-subtitle--muted">
                        ID iiko: {{ selectedProduct.id }} | Код: {{ valueOrDash(selectedProduct.code) }}
                    </p>
                </div>
            </template>

            <div class="kitchen-products-page__tabs">
                <button
                    type="button"
                    :class="['kitchen-products-page__tab', { 'is-active': activeCardTab === 'info' }]"
                    @click="activeCardTab = 'info'"
                >
                    Информация
                </button>
                <button
                    type="button"
                    :class="['kitchen-products-page__tab', { 'is-active': activeCardTab === 'tech' }]"
                    @click="activeCardTab = 'tech'"
                >
                    Техкарта
                </button>
            </div>

            <div v-if="activeCardTab === 'info'" class="kitchen-products-page__tab-panel">
                <div class="kitchen-products-page__info-layout">
                    <section class="kitchen-products-page__info-card">
                        <h4 class="kitchen-products-page__info-card-title">Основные параметры</h4>
                        <div class="kitchen-products-page__details-grid">
                            <div
                                v-for="item in productMainDetails"
                                :key="item.label"
                                class="kitchen-products-page__detail-row"
                            >
                                <span>{{ item.label }}</span>
                                <strong>{{ item.value }}</strong>
                            </div>
                        </div>
                    </section>

                    <section class="kitchen-products-page__info-card kitchen-products-page__info-card--accent">
                        <h4 class="kitchen-products-page__info-card-title">Нагрузка блюда</h4>

                        <div class="kitchen-products-page__load-list">
                            <div class="kitchen-products-page__load-row">
                                <span class="kitchen-products-page__load-label">ПК Производства</span>
                                <div class="kitchen-products-page__load-controls">
                                    <template v-if="activeLoadEditor === 'kitchen' && canEditCatalog">
                                        <input
                                            v-model="modalDraft.portion_coef_kitchen"
                                            class="kitchen-products-page__load-input"
                                            type="number"
                                            step="0.0001"
                                            placeholder="1.0"
                                            :disabled="modalSaving"
                                            @keydown.enter.prevent="saveLoadCoefficient('kitchen')"
                                            @keydown.esc.prevent="cancelLoadEdit"
                                        />
                                        <Button
                                            size="sm"
                                            :disabled="modalSaving"
                                            :loading="modalSaving"
                                            @click="saveLoadCoefficient('kitchen')"
                                        >
                                            OK
                                        </Button>
                                        <Button size="sm" color="ghost" :disabled="modalSaving" @click="cancelLoadEdit">
                                            Отмена
                                        </Button>
                                    </template>
                                    <template v-else>
                                        <strong class="kitchen-products-page__load-value">
                                            {{ formatCoefficientShort(selectedProduct?.portion_coef_kitchen) }}
                                        </strong>
                                        <button
                                            v-if="canEditCatalog"
                                            type="button"
                                            class="kitchen-products-page__edit-icon-btn"
                                            :disabled="modalSaving"
                                            aria-label="Редактировать ПК Производства"
                                            @click="startLoadEdit('kitchen')"
                                        >
                                            <BaseIcon name="Edit" class="kitchen-products-page__edit-icon" />
                                        </button>
                                    </template>
                                </div>
                            </div>

                            <div class="kitchen-products-page__load-row">
                                <span class="kitchen-products-page__load-label">ПК Продажи</span>
                                <div class="kitchen-products-page__load-controls">
                                    <template v-if="activeLoadEditor === 'hall' && canEditCatalog">
                                        <input
                                            v-model="modalDraft.portion_coef_hall"
                                            class="kitchen-products-page__load-input"
                                            type="number"
                                            step="0.0001"
                                            placeholder="1.0"
                                            :disabled="modalSaving"
                                            @keydown.enter.prevent="saveLoadCoefficient('hall')"
                                            @keydown.esc.prevent="cancelLoadEdit"
                                        />
                                        <Button
                                            size="sm"
                                            :disabled="modalSaving"
                                            :loading="modalSaving"
                                            @click="saveLoadCoefficient('hall')"
                                        >
                                            OK
                                        </Button>
                                        <Button size="sm" color="ghost" :disabled="modalSaving" @click="cancelLoadEdit">
                                            Отмена
                                        </Button>
                                    </template>
                                    <template v-else>
                                        <strong class="kitchen-products-page__load-value">
                                            {{ formatCoefficientShort(selectedProduct?.portion_coef_hall) }}
                                        </strong>
                                        <button
                                            v-if="canEditCatalog"
                                            type="button"
                                            class="kitchen-products-page__edit-icon-btn"
                                            :disabled="modalSaving"
                                            aria-label="Редактировать ПК Продажи"
                                            @click="startLoadEdit('hall')"
                                        >
                                            <BaseIcon name="Edit" class="kitchen-products-page__edit-icon" />
                                        </button>
                                    </template>
                                </div>
                            </div>
                        </div>

                        <p class="kitchen-products-page__hint">
                            Значение 1.0 — базовая нагрузка. Выше 1.0 увеличивает вклад блюда в показатель нагрузки.
                        </p>
                    </section>
                </div>
            </div>

            <div v-else class="kitchen-products-page__tab-panel">
                <div class="kitchen-products-page__tech-card">
                    <h4>Техкарта</h4>
                    <Table v-if="techCardItems.length">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Наименование</th>
                                <th>Кол-во</th>
                                <th>Ед.</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="item in techCardItems" :key="item.key">
                                <td>{{ item.index }}</td>
                                <td>{{ item.name }}</td>
                                <td>{{ item.amount }}</td>
                                <td>{{ item.unit }}</td>
                            </tr>
                        </tbody>
                    </Table>
                    <div v-else class="admin-page__empty">Техкарта не найдена или не содержит строк.</div>
                </div>

                <div v-if="hasServiceData" class="kitchen-products-page__raw">
                    <button type="button" class="kitchen-products-page__service-toggle" @click="showServiceData = !showServiceData">
                        {{ showServiceData ? 'Скрыть служебные данные' : 'Показать служебные данные' }}
                    </button>

                    <div v-if="showServiceData" class="kitchen-products-page__service-block">
                        <details v-if="hasData(selectedProduct.raw_payload)">
                            <summary>raw_payload</summary>
                            <pre class="kitchen-products-page__pre">{{ toPrettyJson(selectedProduct.raw_payload) }}</pre>
                        </details>
                        <details v-if="hasData(selectedProduct.raw_v2_payload)">
                            <summary>raw_v2_payload</summary>
                            <pre class="kitchen-products-page__pre">{{ toPrettyJson(selectedProduct.raw_v2_payload) }}</pre>
                        </details>
                        <details v-if="hasData(selectedProduct.tech_card_payload)">
                            <summary>tech_card_payload</summary>
                            <pre class="kitchen-products-page__pre">{{ toPrettyJson(selectedProduct.tech_card_payload) }}</pre>
                        </details>
                        <details v-if="hasData(selectedProduct.raw_xml)">
                            <summary>raw_xml</summary>
                            <pre class="kitchen-products-page__pre">{{ selectedProduct.raw_xml }}</pre>
                        </details>
                    </div>
                </div>
            </div>

            <template #footer>
                <Button color="ghost" :disabled="modalSaving" @click="closeProductCard">Закрыть</Button>
            </template>
        </Modal>

        <Modal v-if="folderCoefficientsTarget" @close="closeFolderCoefficients">
            <template #header>
                Коэффициенты для папки: {{ folderCoefficientsTarget.label || '-' }}
            </template>

            <div class="kitchen-products-page__folder-form">
                <p class="kitchen-products-page__hint">
                    Будет применено к позициям в ветке: {{ folderBranchSize }}.
                </p>
                <Input
                    v-model="folderCoefficientsDraft.portion_coef_kitchen"
                    label="Коэффициент нагрузки кухни"
                    type="number"
                    step="0.0001"
                    placeholder="Не задано"
                />
                <Input
                    v-model="folderCoefficientsDraft.portion_coef_hall"
                    label="Коэффициент нагрузки зала"
                    type="number"
                    step="0.0001"
                    placeholder="Не задано"
                />
            </div>

            <template #footer>
                <Button color="ghost" :disabled="folderCoefficientsSaving" @click="closeFolderCoefficients">Отмена</Button>
                <Button :loading="folderCoefficientsSaving" :disabled="folderCoefficientsSaving" @click="saveFolderCoefficients">
                    Применить к папке
                </Button>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import {
    fetchKitchenProductRows,
    patchKitchenProductRowSettings,
    syncKitchenProductsNetwork,
} from '@/api';
import { useToast } from 'vue-toastification';
import { useUserStore } from '@/stores/user';
import Button from '@/components/UI-components/Button.vue';
import Table from '@/components/UI-components/Table.vue';
import Select from '@/components/UI-components/Select.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Input from '@/components/UI-components/Input.vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';

const PAGE_LIMIT = 1000;

const TABLE_COLUMNS = [
    { key: 'name', label: 'Название', type: 'text' },
    { key: 'product_type', label: 'Тип номенклатуры', type: 'text' },
    { key: 'parent_group', label: 'Родительская группа', type: 'text' },
    { key: 'main_unit', label: 'Ед. изм.', type: 'text' },
    { key: 'portion_coef_kitchen', label: 'Порц. коэф. кухни', type: 'number' },
    { key: 'portion_coef_hall', label: 'Порц. коэф. зала', type: 'number' },
];

const PRODUCT_TYPE_LABELS = {
    GOODS: 'Товар',
    DISH: 'Блюдо',
    PREPARED: 'Заготовка',
    SERVICE: 'Услуга',
    MODIFIER: 'Модификатор',
    OUTER: 'Сторонний товар',
    RATE: 'Тариф',
};

const TREE_INDENT_PX = 18;
const TYPE_FALLBACK_KEY = 'UNDEFINED';
const CATEGORY_FALLBACK_KEY = '__NO_CATEGORY__';
const CATEGORY_FALLBACK_LABEL = 'Без категории';
const UNGROUPED_FOLDER_LABEL = 'Неопределено';
const TYPE_NODE_PREFIX = '__node_type__';
const CATEGORY_NODE_PREFIX = '__node_category__';
const UNGROUPED_NODE_PREFIX = '__node_ungrouped__';
const EXTERNAL_PARENT_NODE_PREFIX = '__node_external_parent__';

const TECH_CARD_AMOUNT_KEYS = [
    'bruttoAmount',
    'amountGross',
    'netAmount',
    'amountNet',
    'amountIn',
    'amountOut',
    'amountMiddle',
    'amountIn1',
    'amountIn2',
    'amountIn3',
    'amountOut1',
    'amountOut2',
    'amountOut3',
    'weight',
    'amount',
    'quantity',
    'qty',
    'count',
];

const userStore = useUserStore();
const toast = useToast();

const products = ref([]);
const loading = ref(false);
const syncingNetwork = ref(false);
const networkSyncSummary = ref('');
const selectedProductId = ref('');
const modalSaving = ref(false);
const showServiceData = ref(false);
const activeCardTab = ref('info');
const activeLoadEditor = ref('');

const searchText = ref('');
const selectedType = ref('');
const selectedParentGroup = ref('');
const collapsedBranchIds = ref(new Set());

const sortBy = ref('name');
const sortDirection = ref('asc');

const modalDraft = reactive({
    portion_coef_kitchen: '',
    portion_coef_hall: '',
});
const folderCoefficientsTarget = ref(null);
const folderCoefficientsSaving = ref(false);
const folderCoefficientsDraft = reactive({
    portion_coef_kitchen: '',
    portion_coef_hall: '',
});

const canSyncNomenclature = computed(() => userStore.hasPermission('iiko.catalog.sync'));
const canEditCatalog = computed(() =>
    userStore.hasAnyPermission('sales.dishes.manage', 'iiko.manage'),
);

const selectedProduct = computed(() => products.value.find((item) => item.id === selectedProductId.value) || null);
const folderBranchSize = computed(() => {
    const targetId = normalizeSelectValue(folderCoefficientsTarget.value?.nodeId);
    if (!targetId) {
        return 0;
    }
    return collectBranchRows(targetId).length;
});
const hasServiceData = computed(() => {
    const row = selectedProduct.value;
    if (!row) {
        return false;
    }
    return (
        hasData(row.raw_payload) ||
        hasData(row.raw_v2_payload) ||
        hasData(row.tech_card_payload) ||
        hasData(row.raw_xml)
    );
});

const productMainDetails = computed(() => {
    const row = selectedProduct.value;
    if (!row) {
        return [];
    }
    return [
        { label: 'Название', value: valueOrDash(row.name) },
        { label: 'Удалена', value: resolveDeletedLabel(row) },
        { label: 'Тип номенклатуры', value: valueOrDash(resolveDisplayProductType(row)) },
        { label: 'Родительская группа', value: valueOrDash(resolveDisplayParentGroup(row)) },
        { label: 'Категория', value: valueOrDash(resolveDisplayCategory(row.product_category)) },
        { label: 'Ед. изм.', value: valueOrDash(resolveDisplayMainUnit(row)) },
    ];
});

const typeOptions = computed(() => {
    const codes = new Set();
    for (const row of products.value) {
        const code = resolveProductTypeCode(row);
        if (code) {
            codes.add(code);
        }
    }
    return Array.from(codes)
        .sort((a, b) => a.localeCompare(b, 'ru', { sensitivity: 'base' }))
        .map((code) => ({ value: code, label: formatProductTypeLabel(code) }));
});
const productNameById = computed(() => {
    const map = new Map();
    for (const row of products.value) {
        if (!row?.id) {
            continue;
        }
        map.set(String(row.id), String(row.name || ''));
    }
    return map;
});
const categoryLabelByKey = computed(() => buildCategoryLabelMap(products.value));

const rowsForParentGroupOptions = computed(() =>
    products.value.filter((row) => !selectedType.value || resolveProductTypeCode(row) === selectedType.value),
);
const parentGroupOptions = computed(() => buildParentGroupOptions(rowsForParentGroupOptions.value));

const typeOptionsWithAll = computed(() => [{ value: '', label: 'Все' }, ...typeOptions.value]);
const parentGroupOptionsWithAll = computed(() => [{ value: '', label: 'Все' }, ...parentGroupOptions.value]);
const allFolderIds = computed(() => collectFolderIds(products.value));

const filteredProducts = computed(() => {
    const query = String(searchText.value || '').trim().toLowerCase();
    return products.value.filter((product) => {
        const displayType = resolveDisplayProductType(product);
        const displayParentGroup = resolveDisplayParentGroup(product);
        const displayMainUnit = resolveDisplayMainUnit(product);
        const typeCode = resolveProductTypeCode(product);
        const parentGroupId = normalizeSelectValue(product?.parent_id);

        if (selectedType.value && typeCode !== selectedType.value) {
            return false;
        }
        if (selectedParentGroup.value && parentGroupId !== selectedParentGroup.value) {
            return false;
        }
        if (!query) {
            return true;
        }
        const fields = [
            product.id,
            product.name,
            product.num,
            product.code,
            displayType,
            displayParentGroup,
            displayMainUnit,
            product.portion_coef_kitchen,
            product.portion_coef_hall,
        ];
        return fields.some((value) => String(value || '').toLowerCase().includes(query));
    });
});

const hierarchyProducts = computed(() => buildHierarchyRows(filteredProducts.value));

const techCardItems = computed(() => extractTechCardItems(selectedProduct.value?.tech_card_payload));

onMounted(async () => {
    await loadProducts();
});

watch(
    parentGroupOptions,
    (options) => {
        if (!selectedParentGroup.value) {
            return;
        }
        const isSelectedAvailable = options.some((option) => option.value === selectedParentGroup.value);
        if (!isSelectedAvailable) {
            selectedParentGroup.value = '';
        }
    },
    { immediate: true },
);

function buildOptions(rows, resolver) {
    const set = new Set();
    for (const row of rows) {
        const value = typeof resolver === 'function' ? resolver(row) : row?.[resolver];
        const normalized = normalizeSelectValue(value);
        if (normalized) {
            set.add(normalized);
        }
    }
    return Array.from(set)
        .sort((a, b) => a.localeCompare(b, 'ru', { sensitivity: 'base' }))
        .map((value) => ({ value, label: value }));
}

function buildParentGroupOptions(rows) {
    const map = new Map();
    for (const row of rows) {
        const parentId = normalizeSelectValue(row?.parent_id);
        const parentLabel = normalizeSelectValue(resolveDisplayParentGroup(row));
        if (!parentId || !parentLabel) {
            continue;
        }
        if (!map.has(parentId)) {
            map.set(parentId, parentLabel);
        }
    }
    return Array.from(map.entries())
        .sort((a, b) => a[1].localeCompare(b[1], 'ru', { sensitivity: 'base' }))
        .map(([value, label]) => ({ value, label }));
}

function normalizeSelectValue(value) {
    if (value === null || value === undefined) {
        return '';
    }
    return String(value).trim();
}

function formatProductTypeLabel(code) {
    const normalizedCode = normalizeSelectValue(code).toUpperCase();
    if (!normalizedCode) {
        return '';
    }
    const text = PRODUCT_TYPE_LABELS[normalizedCode];
    return text || normalizedCode;
}

function resolveProductTypeCode(product) {
    return normalizeSelectValue(product?.product_type).toUpperCase();
}

function resolveProductTypeKey(product) {
    const typeCode = resolveProductTypeCode(product);
    return typeCode || TYPE_FALLBACK_KEY;
}

function resolveCategoryKey(product) {
    const category = normalizeSelectValue(product?.product_category || product?.iiko_product_category);
    return category || CATEGORY_FALLBACK_KEY;
}

function formatTypeNodeLabel(typeKey) {
    if (!typeKey || typeKey === TYPE_FALLBACK_KEY) {
        return 'Неопределенный тип';
    }
    return formatProductTypeLabel(typeKey);
}

function formatCategoryNodeLabel(categoryKey) {
    if (!categoryKey || categoryKey === CATEGORY_FALLBACK_KEY) {
        return CATEGORY_FALLBACK_LABEL;
    }
    const mapped = normalizeSelectValue(categoryLabelByKey.value.get(categoryKey));
    if (mapped) {
        return mapped;
    }
    if (isLikelyUuid(categoryKey)) {
        return 'Категория (без названия)';
    }
    return categoryKey;
}

function getTypeNodeId(typeKey) {
    return `${TYPE_NODE_PREFIX}${typeKey || TYPE_FALLBACK_KEY}`;
}

function getTypeCategoryPairKey(typeKey, categoryKey) {
    return `${typeKey || TYPE_FALLBACK_KEY}::${categoryKey || CATEGORY_FALLBACK_KEY}`;
}

function parseTypeCategoryPairKey(pairKey) {
    const normalized = normalizeSelectValue(pairKey);
    const separatorIndex = normalized.indexOf('::');
    if (separatorIndex === -1) {
        return {
            typeKey: normalized || TYPE_FALLBACK_KEY,
            categoryKey: CATEGORY_FALLBACK_KEY,
        };
    }
    return {
        typeKey: normalized.slice(0, separatorIndex) || TYPE_FALLBACK_KEY,
        categoryKey: normalized.slice(separatorIndex + 2) || CATEGORY_FALLBACK_KEY,
    };
}

function getCategoryNodeId(typeKey, categoryKey) {
    return `${CATEGORY_NODE_PREFIX}${getTypeCategoryPairKey(typeKey, categoryKey)}`;
}

function getUngroupedNodeId(typeKey, categoryKey) {
    return `${UNGROUPED_NODE_PREFIX}${getTypeCategoryPairKey(typeKey, categoryKey)}`;
}

function getExternalParentNodeId(typeKey, categoryKey, parentId) {
    const parentKey = normalizeSelectValue(parentId) || '__NO_PARENT__';
    return `${EXTERNAL_PARENT_NODE_PREFIX}${getTypeCategoryPairKey(typeKey, categoryKey)}@@${parentKey}`;
}

function parseExternalParentNodeId(nodeId) {
    const normalized = normalizeSelectValue(nodeId);
    if (!normalized.startsWith(EXTERNAL_PARENT_NODE_PREFIX)) {
        return null;
    }
    const raw = normalized.slice(EXTERNAL_PARENT_NODE_PREFIX.length);
    const separatorIndex = raw.lastIndexOf('@@');
    if (separatorIndex === -1) {
        return null;
    }
    const pairKey = normalizeSelectValue(raw.slice(0, separatorIndex));
    const parentId = normalizeSelectValue(raw.slice(separatorIndex + 2));
    if (!pairKey || !parentId) {
        return null;
    }
    return { pairKey, parentId };
}

function getTypeKeyFromNodeId(nodeId) {
    const normalized = normalizeSelectValue(nodeId);
    if (!normalized) {
        return '';
    }
    if (normalized.startsWith(TYPE_NODE_PREFIX)) {
        return normalized.slice(TYPE_NODE_PREFIX.length) || TYPE_FALLBACK_KEY;
    }
    if (normalized.startsWith(CATEGORY_NODE_PREFIX)) {
        return parseTypeCategoryPairKey(normalized.slice(CATEGORY_NODE_PREFIX.length)).typeKey;
    }
    if (normalized.startsWith(UNGROUPED_NODE_PREFIX)) {
        return parseTypeCategoryPairKey(normalized.slice(UNGROUPED_NODE_PREFIX.length)).typeKey;
    }
    if (normalized.startsWith(EXTERNAL_PARENT_NODE_PREFIX)) {
        const parsed = parseExternalParentNodeId(normalized);
        return parsed ? parseTypeCategoryPairKey(parsed.pairKey).typeKey : '';
    }
    return '';
}

function getPairKeyFromNodeId(nodeId) {
    const normalized = normalizeSelectValue(nodeId);
    if (normalized.startsWith(CATEGORY_NODE_PREFIX)) {
        return normalized.slice(CATEGORY_NODE_PREFIX.length);
    }
    if (normalized.startsWith(UNGROUPED_NODE_PREFIX)) {
        return normalized.slice(UNGROUPED_NODE_PREFIX.length);
    }
    if (normalized.startsWith(EXTERNAL_PARENT_NODE_PREFIX)) {
        const parsed = parseExternalParentNodeId(normalized);
        return parsed?.pairKey || '';
    }
    return '';
}

function resolveDisplayProductType(product) {
    return formatProductTypeLabel(resolveProductTypeCode(product));
}

function resolveDisplayParentGroup(product) {
    const parentId = normalizeSelectValue(product?.parent_id);
    if (!parentId) {
        return '';
    }
    const parentName = normalizeSelectValue(productNameById.value.get(parentId));
    return parentName || parentId;
}

function resolveDisplayMainUnit(product) {
    const directText = normalizeSelectValue(
        product?.main_unit_name ||
            product?.unit_name ||
            product?.raw_v2_payload?.mainUnitName ||
            product?.raw_v2_payload?.mainUnit?.name ||
            product?.raw_payload?.v2_product?.mainUnitName ||
            product?.raw_payload?.v2_product?.mainUnit?.name,
    );
    if (directText && !isLikelyUuid(directText)) {
        return directText;
    }

    const containerName = extractContainerName(product?.containers)
        || extractContainerName(product?.raw_v2_payload?.containers)
        || extractContainerName(product?.raw_payload?.v2_product?.containers);
    if (containerName && !isLikelyUuid(containerName)) {
        return containerName;
    }

    const fallbackMainUnit = normalizeSelectValue(product?.main_unit);
    if (!fallbackMainUnit || isLikelyUuid(fallbackMainUnit)) {
        return '';
    }
    return fallbackMainUnit;
}

function resolveDisplayCategory(value) {
    const normalized = normalizeSelectValue(value);
    if (!normalized) {
        return '';
    }
    const mapped = normalizeSelectValue(categoryLabelByKey.value.get(normalized));
    if (mapped) {
        return mapped;
    }
    if (isLikelyUuid(normalized)) {
        return 'Категория (без названия)';
    }
    return normalized;
}

function buildCategoryLabelMap(rows) {
    const rowsById = new Map();
    const labelsByKey = new Map();
    const labelVotesByKey = new Map();

    for (const row of rows) {
        const rowId = normalizeSelectValue(row?.id);
        if (rowId) {
            rowsById.set(rowId, row);
        }
    }

    for (const row of rows) {
        const key = resolveCategoryKey(row);
        if (!key || key === CATEGORY_FALLBACK_KEY) {
            continue;
        }

        if (!isLikelyUuid(key)) {
            labelsByKey.set(key, key);
            continue;
        }

        const candidate = resolveCategoryLabelCandidate(row, rowsById);
        if (!candidate) {
            continue;
        }

        if (!labelVotesByKey.has(key)) {
            labelVotesByKey.set(key, new Map());
        }
        const counter = labelVotesByKey.get(key);
        counter.set(candidate, (counter.get(candidate) || 0) + 1);
    }

    for (const [key, counter] of labelVotesByKey.entries()) {
        let winner = '';
        let winnerCount = -1;
        for (const [label, count] of counter.entries()) {
            if (count > winnerCount || (count === winnerCount && label.localeCompare(winner, 'ru', { sensitivity: 'base' }) < 0)) {
                winner = label;
                winnerCount = count;
            }
        }
        if (winner) {
            labelsByKey.set(key, winner);
        }
    }

    for (const row of rows) {
        const key = resolveCategoryKey(row);
        if (!key || key === CATEGORY_FALLBACK_KEY || labelsByKey.has(key)) {
            continue;
        }
        if (isLikelyUuid(key)) {
            labelsByKey.set(key, 'Категория (без названия)');
        } else {
            labelsByKey.set(key, key);
        }
    }

    return labelsByKey;
}

function resolveCategoryLabelCandidate(row, rowsById) {
    const direct = normalizeCategoryLabelCandidate(
        row?.raw_v2_payload?.categoryName,
        row?.raw_v2_payload?.category?.name,
        row?.raw_payload?.v2_product?.categoryName,
        row?.raw_payload?.v2_product?.category?.name,
        row?.raw_payload?.categoryName,
        row?.raw_payload?.category?.name,
    );
    if (direct) {
        return direct;
    }

    const parentChainLabel = normalizeCategoryLabelCandidate(resolveTopParentName(row, rowsById));
    if (parentChainLabel) {
        return parentChainLabel;
    }

    return '';
}

function normalizeCategoryLabelCandidate(...values) {
    for (const value of values) {
        const text = normalizeSelectValue(value);
        if (!text || text === CATEGORY_FALLBACK_KEY || isLikelyUuid(text)) {
            continue;
        }
        return text;
    }
    return '';
}

function resolveTopParentName(row, rowsById) {
    const visited = new Set();
    let current = row;
    let topParentName = '';

    for (let depth = 0; depth < 24; depth += 1) {
        const parentId = normalizeSelectValue(current?.parent_id);
        if (!parentId || visited.has(parentId)) {
            break;
        }
        visited.add(parentId);
        const parent = rowsById.get(parentId);
        if (!parent) {
            break;
        }
        const parentName = normalizeSelectValue(parent?.name);
        if (parentName && !isLikelyUuid(parentName)) {
            topParentName = parentName;
        }
        current = parent;
    }

    return topParentName;
}

function extractContainerName(containers) {
    if (!Array.isArray(containers)) {
        return '';
    }
    for (const row of containers) {
        const name = normalizeSelectValue(row?.name || row?.unitName || row?.fullName);
        if (name) {
            return name;
        }
    }
    return '';
}

function isLikelyUuid(value) {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(value || ''));
}

function shortUuid(value) {
    const normalized = normalizeSelectValue(value);
    return normalized ? normalized.slice(0, 8) : '';
}

function formatCoefficient(value) {
    if (value === null || value === undefined || value === '') {
        return '-';
    }
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
        return '-';
    }
    return parsed.toFixed(4).replace(/\.?0+$/, '');
}

function formatCoefficientTag(value) {
    const normalized = formatCoefficient(value);
    return normalized === '-' ? '1.0' : normalized;
}

function formatCoefficientShort(value) {
    const normalized = formatCoefficient(value);
    return normalized === '-' ? '1.0' : normalized;
}

function normalizeCoefficientValue(value) {
    const parsed = toPayloadNumber(value);
    if (parsed === null) {
        return 1;
    }
    return Number(parsed.toFixed(6));
}

function formatNumber(value) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
        return '0';
    }
    return parsed.toLocaleString('ru-RU');
}

function formatTechCardAmount(value) {
    if (value === null || value === undefined || value === '') {
        return '-';
    }
    const normalized = String(value).trim().replace(',', '.');
    if (!normalized) {
        return '-';
    }
    const parsed = Number(normalized);
    if (!Number.isFinite(parsed)) {
        return String(value);
    }
    return parsed.toLocaleString('ru-RU', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 6,
    });
}

function valueOrDash(value) {
    if (value === null || value === undefined || value === '') {
        return '-';
    }
    return String(value);
}
function toPrettyJson(value) {
    if (!value) {
        return '-';
    }
    try {
        return JSON.stringify(value, null, 2);
    } catch {
        return String(value);
    }
}

function getSortValue(row, key, type) {
    let value;
    if (key === 'product_type') {
        value = resolveDisplayProductType(row);
    } else if (key === 'parent_group') {
        value = resolveDisplayParentGroup(row);
    } else if (key === 'main_unit') {
        value = resolveDisplayMainUnit(row);
    } else {
        value = row?.[key];
    }
    if (value === null || value === undefined || value === '') {
        return null;
    }
    if (type === 'number') {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : null;
    }
    return String(value).trim();
}

function collectFolderIds(rows) {
    const model = buildHierarchyModel(rows);
    const folderIds = new Set();
    for (const [typeKey, typeRows] of model.rowsByType.entries()) {
        if (!typeRows.length) {
            continue;
        }
        folderIds.add(getTypeNodeId(typeKey));
        const categories = model.categoriesByType.get(typeKey) || new Map();
        for (const [categoryKey, categoryRows] of categories.entries()) {
            if (!categoryRows.length) {
                continue;
            }
            folderIds.add(getCategoryNodeId(typeKey, categoryKey));
            const pairKey = getTypeCategoryPairKey(typeKey, categoryKey);
            const ungroupedRows = model.ungroupedByPairKey.get(pairKey) || [];
            if (ungroupedRows.length) {
                folderIds.add(getUngroupedNodeId(typeKey, categoryKey));
            }
            const externalParents = model.externalParentsByPairKey.get(pairKey) || new Map();
            for (const parentId of externalParents.keys()) {
                folderIds.add(getExternalParentNodeId(typeKey, categoryKey, parentId));
            }
        }
    }
    for (const [parentId, children] of model.childrenByParent.entries()) {
        if (children.length) {
            folderIds.add(parentId);
        }
    }
    return Array.from(folderIds);
}

function collectBranchRows(rootId) {
    const nodeId = normalizeSelectValue(rootId);
    if (!nodeId) {
        return [];
    }
    const model = buildHierarchyModel(products.value);

    if (nodeId.startsWith(TYPE_NODE_PREFIX)) {
        const typeKey = getTypeKeyFromNodeId(nodeId) || TYPE_FALLBACK_KEY;
        return [...(model.rowsByType.get(typeKey) || [])];
    }
    if (nodeId.startsWith(CATEGORY_NODE_PREFIX)) {
        const pairKey = getPairKeyFromNodeId(nodeId);
        return [...(model.rowsByPairKey.get(pairKey) || [])];
    }
    if (nodeId.startsWith(UNGROUPED_NODE_PREFIX)) {
        const pairKey = getPairKeyFromNodeId(nodeId);
        return [...(model.ungroupedByPairKey.get(pairKey) || [])];
    }
    if (nodeId.startsWith(EXTERNAL_PARENT_NODE_PREFIX)) {
        const parsed = parseExternalParentNodeId(nodeId);
        if (!parsed) {
            return [];
        }
        const parentMap = model.externalParentsByPairKey.get(parsed.pairKey) || new Map();
        const group = parentMap.get(parsed.parentId);
        return collectRowsWithDescendants(model, group?.rows || []);
    }

    return collectRowsWithDescendants(model, [nodeId]);
}

function collectRowsWithDescendants(model, roots) {
    const result = [];
    const queue = Array.isArray(roots) ? [...roots] : [roots];
    const visited = new Set();
    while (queue.length) {
        const next = queue.shift();
        const currentId = normalizeSelectValue(next?.id || next);
        if (!currentId || visited.has(currentId)) {
            continue;
        }
        visited.add(currentId);
        const row = model.rowsById.get(currentId);
        if (row) {
            result.push(row);
        }
        const children = model.childrenByParent.get(currentId) || [];
        for (const child of children) {
            const childId = normalizeSelectValue(child?.id || child);
            if (childId && !visited.has(childId)) {
                queue.push(childId);
            }
        }
    }
    return result;
}

function buildHierarchyModel(rows) {
    const rowsById = new Map();
    const rowsByType = new Map();
    const categoriesByType = new Map();
    const rowsByPairKey = new Map();
    const externalParentsByPairKey = new Map();

    for (const row of rows) {
        const rowId = normalizeSelectValue(row?.id);
        if (rowId) {
            rowsById.set(rowId, row);
        }

        const typeKey = resolveProductTypeKey(row);
        const categoryKey = resolveCategoryKey(row);
        const pairKey = getTypeCategoryPairKey(typeKey, categoryKey);

        if (!rowsByType.has(typeKey)) {
            rowsByType.set(typeKey, []);
        }
        rowsByType.get(typeKey).push(row);

        if (!categoriesByType.has(typeKey)) {
            categoriesByType.set(typeKey, new Map());
        }
        if (!categoriesByType.get(typeKey).has(categoryKey)) {
            categoriesByType.get(typeKey).set(categoryKey, []);
        }
        categoriesByType.get(typeKey).get(categoryKey).push(row);

        if (!rowsByPairKey.has(pairKey)) {
            rowsByPairKey.set(pairKey, []);
        }
        rowsByPairKey.get(pairKey).push(row);
    }

    const hasValidParentInRows = (row) => {
        const rowId = normalizeSelectValue(row?.id);
        const parentId = normalizeSelectValue(row?.parent_id);
        if (!rowId || !parentId || rowId === parentId) {
            return false;
        }
        const parentRow = rowsById.get(parentId);
        if (!parentRow) {
            return false;
        }
        return (
            resolveProductTypeKey(parentRow) === resolveProductTypeKey(row)
            && resolveCategoryKey(parentRow) === resolveCategoryKey(row)
        );
    };

    const childrenByParent = new Map();
    for (const row of rows) {
        if (!hasValidParentInRows(row)) {
            continue;
        }
        const parentId = normalizeSelectValue(row?.parent_id);
        if (!childrenByParent.has(parentId)) {
            childrenByParent.set(parentId, []);
        }
        childrenByParent.get(parentId).push(row);
    }

    const rootFoldersByPairKey = new Map();
    const ungroupedByPairKey = new Map();

    for (const [pairKey, pairRows] of rowsByPairKey.entries()) {
        const rootCandidates = pairRows.filter((row) => !hasValidParentInRows(row));
        const rootFolders = [];
        const ungroupedRows = [];
        const externalParents = new Map();

        for (const row of rootCandidates) {
            const rowId = normalizeSelectValue(row?.id);
            const hasChildren = Boolean(rowId && (childrenByParent.get(rowId) || []).length);
            const parentId = normalizeSelectValue(row?.parent_id);
            const externalParent = parentId ? rowsById.get(parentId) : null;

            if (externalParent) {
                const externalParentId = normalizeSelectValue(externalParent?.id) || parentId;
                const externalParentLabel =
                    normalizeSelectValue(externalParent?.name)
                    || resolveDisplayParentGroup(row)
                    || `Папка #${shortUuid(externalParentId)}`;
                if (!externalParents.has(externalParentId)) {
                    externalParents.set(externalParentId, {
                        id: externalParentId,
                        label: externalParentLabel,
                        rows: [],
                    });
                }
                externalParents.get(externalParentId).rows.push(row);
                continue;
            }
            if (hasChildren) {
                rootFolders.push(row);
            } else {
                ungroupedRows.push(row);
            }
        }

        if (!rootFolders.length && !ungroupedRows.length && !externalParents.size && pairRows.length) {
            ungroupedRows.push(...pairRows);
        }

        externalParentsByPairKey.set(pairKey, externalParents);
        rootFoldersByPairKey.set(pairKey, rootFolders);
        ungroupedByPairKey.set(pairKey, ungroupedRows);
    }

    return {
        rowsById,
        rowsByType,
        categoriesByType,
        rowsByPairKey,
        childrenByParent,
        externalParentsByPairKey,
        rootFoldersByPairKey,
        ungroupedByPairKey,
    };
}

function sortRowsForHierarchy(rows) {
    const list = [...rows];
    const column = TABLE_COLUMNS.find((item) => item.key === sortBy.value);
    const direction = sortDirection.value === 'desc' ? -1 : 1;
    return list.sort((a, b) => {
        const aValue = getSortValue(a, sortBy.value, column?.type);
        const bValue = getSortValue(b, sortBy.value, column?.type);
        return compareSortValues(aValue, bValue, column?.type) * direction;
    });
}

function buildHierarchyRows(rows) {
    const model = buildHierarchyModel(rows);
    const result = [];
    const visited = new Set();

    const addProductBranch = (row, level) => {
        const rowId = normalizeSelectValue(row?.id);
        if (!rowId || visited.has(rowId)) {
            return;
        }
        visited.add(rowId);

        const children = sortRowsForHierarchy(model.childrenByParent.get(rowId) || []);
        const isCollapsed = collapsedBranchIds.value.has(rowId);
        result.push({
            nodeId: rowId,
            nodeKind: 'product',
            label: normalizeSelectValue(row?.name),
            row,
            level,
            hasChildren: children.length > 0,
            isCollapsed,
            itemsCount: 1,
        });

        if (isCollapsed) {
            return;
        }
        for (const child of children) {
            addProductBranch(child, level + 1);
        }
    };

    const typeKeys = Array.from(model.rowsByType.keys()).sort((a, b) =>
        formatTypeNodeLabel(a).localeCompare(formatTypeNodeLabel(b), 'ru', { sensitivity: 'base' }),
    );

    for (const typeKey of typeKeys) {
        const typeRows = model.rowsByType.get(typeKey) || [];
        const categoryMap = model.categoriesByType.get(typeKey) || new Map();
        const categoryKeys = Array.from(categoryMap.keys()).sort((a, b) =>
            formatCategoryNodeLabel(a).localeCompare(formatCategoryNodeLabel(b), 'ru', { sensitivity: 'base' }),
        );
        const typeNodeId = getTypeNodeId(typeKey);
        const typeCollapsed = collapsedBranchIds.value.has(typeNodeId);

        result.push({
            nodeId: typeNodeId,
            nodeKind: 'type',
            label: formatTypeNodeLabel(typeKey),
            row: null,
            level: 0,
            hasChildren: categoryKeys.length > 0,
            isCollapsed: typeCollapsed,
            itemsCount: typeRows.length,
        });

        if (typeCollapsed) {
            continue;
        }

        for (const categoryKey of categoryKeys) {
            const pairKey = getTypeCategoryPairKey(typeKey, categoryKey);
            const categoryRows = categoryMap.get(categoryKey) || [];
            const categoryNodeId = getCategoryNodeId(typeKey, categoryKey);
            const categoryCollapsed = collapsedBranchIds.value.has(categoryNodeId);
            const rootFolders = sortRowsForHierarchy(model.rootFoldersByPairKey.get(pairKey) || []);
            const externalParents = Array.from((model.externalParentsByPairKey.get(pairKey) || new Map()).values())
                .map((group) => ({
                    ...group,
                    rows: sortRowsForHierarchy(group.rows || []),
                }))
                .sort((a, b) => (a.label || '').localeCompare(b.label || '', 'ru', { sensitivity: 'base' }));
            const ungroupedRows = sortRowsForHierarchy(model.ungroupedByPairKey.get(pairKey) || []);
            const categoryChildrenCount = rootFolders.length + externalParents.length + (ungroupedRows.length ? 1 : 0);

            result.push({
                nodeId: categoryNodeId,
                nodeKind: 'category',
                label: formatCategoryNodeLabel(categoryKey),
                row: null,
                level: 1,
                hasChildren: categoryChildrenCount > 0,
                isCollapsed: categoryCollapsed,
                itemsCount: categoryRows.length,
            });

            if (categoryCollapsed) {
                continue;
            }

            for (const rootFolder of rootFolders) {
                addProductBranch(rootFolder, 2);
            }

            for (const externalParent of externalParents) {
                const externalNodeId = getExternalParentNodeId(typeKey, categoryKey, externalParent.id);
                const externalCollapsed = collapsedBranchIds.value.has(externalNodeId);
                result.push({
                    nodeId: externalNodeId,
                    nodeKind: 'group',
                    label: externalParent.label || `Папка #${shortUuid(externalParent.id)}`,
                    row: null,
                    level: 2,
                    hasChildren: externalParent.rows.length > 0,
                    isCollapsed: externalCollapsed,
                    itemsCount: externalParent.rows.length,
                });

                if (!externalCollapsed) {
                    for (const row of externalParent.rows) {
                        addProductBranch(row, 3);
                    }
                }
            }

            if (ungroupedRows.length) {
                const ungroupedNodeId = getUngroupedNodeId(typeKey, categoryKey);
                const ungroupedCollapsed = collapsedBranchIds.value.has(ungroupedNodeId);
                result.push({
                    nodeId: ungroupedNodeId,
                    nodeKind: 'group',
                    label: UNGROUPED_FOLDER_LABEL,
                    row: null,
                    level: 2,
                    hasChildren: true,
                    isCollapsed: ungroupedCollapsed,
                    itemsCount: ungroupedRows.length,
                });

                if (!ungroupedCollapsed) {
                    for (const ungroupedRow of ungroupedRows) {
                        addProductBranch(ungroupedRow, 3);
                    }
                }
            }
        }
    }

    return result;
}

function getTreeIndentStyle(level) {
    const normalizedLevel = Number.isFinite(Number(level)) ? Number(level) : 0;
    const safeLevel = Math.min(Math.max(normalizedLevel, 0), 12);
    return { paddingLeft: `${safeLevel * TREE_INDENT_PX}px` };
}

function toggleBranch(nodeIdRaw) {
    const nodeId = normalizeSelectValue(nodeIdRaw?.nodeId || nodeIdRaw?.id || nodeIdRaw);
    if (!nodeId) {
        return;
    }
    const next = new Set(collapsedBranchIds.value);
    if (next.has(nodeId)) {
        next.delete(nodeId);
    } else {
        next.add(nodeId);
    }
    collapsedBranchIds.value = next;
}

function collapseAllBranches() {
    collapsedBranchIds.value = new Set(allFolderIds.value);
}

function expandAllBranches() {
    collapsedBranchIds.value = new Set();
}

function compareSortValues(aValue, bValue, type) {
    const aEmpty = aValue === null;
    const bEmpty = bValue === null;
    if (aEmpty && bEmpty) return 0;
    if (aEmpty) return 1;
    if (bEmpty) return -1;
    if (type === 'number') return Number(aValue) - Number(bValue);
    return String(aValue).localeCompare(String(bValue), 'ru', { sensitivity: 'base' });
}

function applyProductToDraft(product) {
    modalDraft.portion_coef_kitchen =
        product?.portion_coef_kitchen === null || product?.portion_coef_kitchen === undefined
            ? ''
            : String(product.portion_coef_kitchen);
    modalDraft.portion_coef_hall =
        product?.portion_coef_hall === null || product?.portion_coef_hall === undefined
            ? ''
            : String(product.portion_coef_hall);
}

function resolveLoadDraftByField(field) {
    if (field === 'kitchen') {
        return modalDraft.portion_coef_kitchen;
    }
    if (field === 'hall') {
        return modalDraft.portion_coef_hall;
    }
    return '';
}

function resolveLoadValueByField(product, field) {
    if (field === 'kitchen') {
        return product?.portion_coef_kitchen;
    }
    if (field === 'hall') {
        return product?.portion_coef_hall;
    }
    return null;
}

function resolveLoadPayloadByField(field) {
    if (field === 'kitchen') {
        return { portion_coef_kitchen: toPayloadNumber(modalDraft.portion_coef_kitchen) };
    }
    if (field === 'hall') {
        return { portion_coef_hall: toPayloadNumber(modalDraft.portion_coef_hall) };
    }
    return null;
}

function startLoadEdit(field) {
    if (!canEditCatalog.value || modalSaving.value) {
        return;
    }
    if (field !== 'kitchen' && field !== 'hall') {
        return;
    }
    const product = selectedProduct.value;
    if (product) {
        applyProductToDraft(product);
    }
    activeLoadEditor.value = field;
}

function cancelLoadEdit() {
    const product = selectedProduct.value;
    if (product) {
        applyProductToDraft(product);
    }
    activeLoadEditor.value = '';
}

async function saveLoadCoefficient(field) {
    if (!canEditCatalog.value || modalSaving.value) {
        return;
    }
    if (field !== 'kitchen' && field !== 'hall') {
        return;
    }
    const product = selectedProduct.value;
    if (!product?.id) {
        return;
    }

    const nextValue = normalizeCoefficientValue(resolveLoadDraftByField(field));
    const currentValue = normalizeCoefficientValue(resolveLoadValueByField(product, field));
    if (nextValue === currentValue) {
        activeLoadEditor.value = '';
        return;
    }

    const payload = resolveLoadPayloadByField(field);
    if (!payload) {
        return;
    }

    modalSaving.value = true;
    try {
        const updated = await patchKitchenProductRowSettings(product.id, payload);
        products.value = products.value.map((row) => (row.id === product.id ? { ...row, ...updated } : row));
        applyProductToDraft({ ...product, ...updated });
        activeLoadEditor.value = '';
        toast.success('Коэффициент сохранен');
    } catch (error) {
        toast.error(`Ошибка сохранения карточки: ${error.response?.data?.detail || error.message}`);
    } finally {
        modalSaving.value = false;
    }
}

function handleEntryMainClick(entry) {
    if (!entry) {
        return;
    }
    if (entry.nodeKind === 'product') {
        if (entry.hasChildren) {
            toggleBranch(entry.nodeId);
            return;
        }
        openProductCard(entry.row);
        return;
    }
    if (entry.hasChildren) {
        toggleBranch(entry.nodeId);
    }
}

function openProductCard(product) {
    if (!product?.id) {
        return;
    }
    selectedProductId.value = product.id;
    activeCardTab.value = 'info';
    activeLoadEditor.value = '';
    showServiceData.value = false;
    applyProductToDraft(product);
}

function closeProductCard() {
    selectedProductId.value = '';
    activeCardTab.value = 'info';
    activeLoadEditor.value = '';
    modalSaving.value = false;
    showServiceData.value = false;
}

function openFolderCoefficients(entry) {
    const nodeId = normalizeSelectValue(entry?.nodeId || entry?.row?.id || entry?.id);
    if (!nodeId) {
        return;
    }
    folderCoefficientsTarget.value = {
        nodeId,
        label: normalizeSelectValue(entry?.label || entry?.row?.name) || nodeId,
    };
    folderCoefficientsDraft.portion_coef_kitchen =
        entry?.row?.portion_coef_kitchen === null || entry?.row?.portion_coef_kitchen === undefined
            ? ''
            : String(entry.row.portion_coef_kitchen);
    folderCoefficientsDraft.portion_coef_hall =
        entry?.row?.portion_coef_hall === null || entry?.row?.portion_coef_hall === undefined
            ? ''
            : String(entry.row.portion_coef_hall);
}

function closeFolderCoefficients() {
    folderCoefficientsTarget.value = null;
    folderCoefficientsSaving.value = false;
    folderCoefficientsDraft.portion_coef_kitchen = '';
    folderCoefficientsDraft.portion_coef_hall = '';
}

async function saveFolderCoefficients() {
    if (!canEditCatalog.value) {
        return;
    }
    const rootId = normalizeSelectValue(folderCoefficientsTarget.value?.nodeId);
    if (!rootId) {
        return;
    }
    const payload = {
        portion_coef_kitchen: toPayloadNumber(folderCoefficientsDraft.portion_coef_kitchen),
        portion_coef_hall: toPayloadNumber(folderCoefficientsDraft.portion_coef_hall),
    };
    const branchRows = collectBranchRows(rootId);
    if (!branchRows.length) {
        toast.error('В выбранной папке нет позиций для обновления');
        return;
    }

    folderCoefficientsSaving.value = true;
    let updated = 0;
    let failed = 0;
    try {
        const branchRowIds = branchRows
            .map((row) => normalizeSelectValue(row?.id))
            .filter(Boolean);

        for (let index = 0; index < branchRowIds.length; index += 8) {
            const chunkIds = branchRowIds.slice(index, index + 8);
            const chunkResults = await Promise.allSettled(
                chunkIds.map(async (rowId) => ({
                    rowId,
                    nextRow: await patchKitchenProductRowSettings(rowId, payload),
                })),
            );

            for (const result of chunkResults) {
                if (result.status === 'fulfilled') {
                    const { rowId, nextRow } = result.value;
                    products.value = products.value.map((item) => (item.id === rowId ? { ...item, ...nextRow } : item));
                    updated += 1;
                } else {
                    failed += 1;
                }
            }
        }

        if (failed) {
            toast.warning(`Обновлено: ${updated}, с ошибкой: ${failed}`);
        } else {
            toast.success(`Коэффициенты применены к ${updated} позициям`);
        }
        closeFolderCoefficients();
    } catch (error) {
        toast.error(`Ошибка применения коэффициентов: ${error.response?.data?.detail || error.message}`);
    } finally {
        folderCoefficientsSaving.value = false;
    }
}

async function loadProducts() {
    loading.value = true;
    try {
        const allRows = [];
        let offset = 0;
        while (true) {
            const chunk = (await fetchKitchenProductRows({ limit: PAGE_LIMIT, offset })) || [];
            allRows.push(...chunk);
            if (chunk.length < PAGE_LIMIT) {
                break;
            }
            offset += PAGE_LIMIT;
        }
        products.value = allRows;
        collapseAllBranches();
    } catch (error) {
        toast.error(`Ошибка загрузки номенклатуры: ${error.response?.data?.detail || error.message}`);
    } finally {
        loading.value = false;
    }
}

async function syncProductsNetwork() {
    syncingNetwork.value = true;
    networkSyncSummary.value = '';
    try {
        const data = await syncKitchenProductsNetwork({
            include_deleted: false,
            revision_from: -1,
        });
        const totals = data?.totals || {};
        networkSyncSummary.value =
            `Номенклатура обновлена: restaurants=${totals.restaurants || 0}, ` +
            `upserted=${totals.upserted || 0}, v2=${totals.v2_products || 0}, ` +
            `tech_cards=${totals.tech_cards || 0}, errors=${totals.errors || 0}`;
        toast.success('Обновление номенклатуры завершено');
        await loadProducts();
    } catch (error) {
        toast.error(`Ошибка обновления номенклатуры: ${error.response?.data?.detail || error.message}`);
    } finally {
        syncingNetwork.value = false;
    }
}

function toPayloadNumber(value) {
    if (value === null || value === undefined || value === '') {
        return null;
    }
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
}
function extractTechCardItems(payload) {
    if (!payload || typeof payload !== 'object') {
        return [];
    }
    const rows = [];
    collectTechCardRows(payload, rows, 0);
    const result = [];
    for (const row of rows) {
        const productId = extractField(row, ['productId', 'ingredientProductId', 'ingredientId', 'nomenclatureId', 'id']);
        const name =
            extractField(row, ['productName', 'ingredientName', 'name', 'nomenclatureName']) ||
            row?.product?.name ||
            row?.ingredient?.name ||
            (productId ? productNameById.value.get(String(productId)) : null);
        const amount = extractField(row, TECH_CARD_AMOUNT_KEYS);
        const unit = extractField(row, ['unitName', 'unit', 'measureUnit']) || row?.product?.mainUnit;
        result.push({
            key: `${String(productId || 'row')}-${result.length}`,
            index: result.length + 1,
            name: valueOrDash(name),
            amount: formatTechCardAmount(amount),
            unit: valueOrDash(unit),
        });
    }
    return result;
}

function collectTechCardRows(node, rows, depth) {
    if (depth > 8 || node === null || node === undefined) {
        return;
    }
    if (Array.isArray(node)) {
        for (const item of node) {
            collectTechCardRows(item, rows, depth + 1);
        }
        return;
    }
    if (typeof node !== 'object') {
        return;
    }
    if (isTechCardRow(node)) {
        rows.push(node);
    }
    for (const value of Object.values(node)) {
        collectTechCardRows(value, rows, depth + 1);
    }
}

function isTechCardRow(node) {
    const hasAmount = extractField(node, TECH_CARD_AMOUNT_KEYS) !== null;
    const hasProduct = extractField(node, ['productId', 'ingredientProductId', 'ingredientId', 'nomenclatureId']) !== null;
    return hasAmount && hasProduct;
}

function extractField(node, keys) {
    if (!node || typeof node !== 'object') {
        return null;
    }
    for (const key of keys) {
        const value = node[key];
        if (value !== null && value !== undefined && value !== '') {
            return value;
        }
    }
    return null;
}

function resolveDeletedLabel(row) {
    if (!row || typeof row !== 'object') {
        return '-';
    }
    const candidates = [
        row.deleted,
        row.is_deleted,
        row.isDeleted,
        row?.raw_v2_payload?.deleted,
        row?.raw_v2_payload?.isDeleted,
        row?.raw_v2_payload?.is_deleted,
        row?.raw_payload?.deleted,
        row?.raw_payload?.isDeleted,
        row?.raw_payload?.is_deleted,
        row?.raw_payload?.v2_product?.deleted,
        row?.raw_payload?.v2_product?.isDeleted,
    ];
    for (const value of candidates) {
        if (value === null || value === undefined || value === '') {
            continue;
        }
        if (typeof value === 'boolean') {
            return value ? 'Да' : 'Нет';
        }
        const normalized = String(value).trim().toUpperCase();
        if (!normalized) {
            continue;
        }
        if (['TRUE', 'YES', '1', 'DELETED'].includes(normalized)) {
            return 'Да';
        }
        if (['FALSE', 'NO', '0', 'NOT_DELETED'].includes(normalized)) {
            return 'Нет';
        }
        return String(value);
    }
    return '-';
}

function hasData(value) {
    if (value === null || value === undefined) {
        return false;
    }
    if (typeof value === 'string') {
        return value.trim() !== '';
    }
    if (Array.isArray(value)) {
        return value.length > 0;
    }
    if (typeof value === 'object') {
        return Object.keys(value).length > 0;
    }
    return true;
}
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kitchen-products-dishes' as *;
</style>
