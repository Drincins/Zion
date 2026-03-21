<template>
    <div class="admin-page kitchen-payment-methods-page">
        <header class="admin-page__header">
            <div>
                <h1 class="admin-page__title">Методы оплаты iiko</h1>
                <p class="admin-page__subtitle">
                    Справочник методов оплаты и их интерпретация для аналитики выручки.
                </p>
            </div>
            <div class="admin-page__header-actions">
                <Button :loading="loading" :disabled="loading" @click="loadPaymentMethods">
                    Обновить
                </Button>
            </div>
        </header>

        <section class="kitchen-payment-methods-page__filters">
            <Input v-model="search" placeholder="Поиск по названию или GUID" />
            <Select
                v-model="selectedCategory"
                label="Тип интерпретации"
                :options="categoryFilterOptions"
                placeholder="Все типы"
            />
            <Select
                v-model="selectedStatus"
                label="Статус"
                :options="statusOptions"
                placeholder="Все"
            />
        </section>

        <section class="admin-page__section">
            <Table v-if="filteredMethods.length">
                <thead>
                    <tr>
                        <th>Название</th>
                        <th>GUID</th>
                        <th>Тип интерпретации</th>
                        <th>Активен</th>
                        <th>Комментарий</th>
                        <th class="admin-page__actions">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="row in filteredMethods" :key="row.guid">
                        <td>{{ row.name || '-' }}</td>
                        <td class="kitchen-payment-methods-page__mono">{{ row.guid }}</td>
                        <td>
                            <Select
                                v-model="drafts[row.guid].category"
                                :disabled="!canManage"
                                :options="categoryEditOptions"
                                placeholder="Не задано"
                            />
                        </td>
                        <td class="kitchen-payment-methods-page__status">
                            <Checkbox
                                v-model="drafts[row.guid].is_active"
                                :disabled="!canManage"
                                label=""
                            />
                        </td>
                        <td>
                            <Input
                                v-model="drafts[row.guid].comment"
                                :readonly="!canManage"
                                placeholder="Например: не денежный расчет"
                            />
                        </td>
                        <td class="admin-page__actions">
                            <Button
                                color="secondary"
                                size="sm"
                                :disabled="!canManage || savingGuid === row.guid"
                                :loading="savingGuid === row.guid"
                                @click="saveMethod(row)"
                            >
                                Сохранить
                            </Button>
                        </td>
                    </tr>
                </tbody>
            </Table>

            <div v-else-if="loading" class="admin-page__empty">
                Загрузка методов оплаты...
            </div>
            <div v-else class="admin-page__empty">
                Методы оплаты не найдены.
            </div>
        </section>
    </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue';
import { fetchKitchenPaymentMethods, patchKitchenPaymentMethod } from '@/api';
import { useToast } from 'vue-toastification';
import { useUserStore } from '@/stores/user';
import Input from '@/components/UI-components/Input.vue';
import Button from '@/components/UI-components/Button.vue';
import Table from '@/components/UI-components/Table.vue';
import Select from '@/components/UI-components/Select.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';

const CATEGORY_OPTIONS = [
    { value: 'real_money', label: 'Реальные деньги' },
    { value: 'non_money', label: 'Не деньги' },
    { value: 'staff', label: 'Персонал' },
    { value: 'certificate', label: 'Сертификат' },
    { value: 'bonus', label: 'Бонусы' },
    { value: 'other', label: 'Другое' },
];

const EMPTY_CATEGORY = '__empty__';

const userStore = useUserStore();
const toast = useToast();

const methods = ref([]);
const loading = ref(false);
const savingGuid = ref('');

const search = ref('');
const selectedCategory = ref('');
const selectedStatus = ref('all');

const drafts = reactive({});

const canManage = computed(() => userStore.hasAnyPermission('iiko.manage'));

const categoryFilterOptions = computed(() => [
    { value: '', label: 'Все типы' },
    ...CATEGORY_OPTIONS,
    { value: EMPTY_CATEGORY, label: 'Не задано' },
]);

const categoryEditOptions = computed(() => [
    { value: EMPTY_CATEGORY, label: 'Не задано' },
    ...CATEGORY_OPTIONS,
]);

const statusOptions = [
    { value: 'all', label: 'Все' },
    { value: 'active', label: 'Активные' },
    { value: 'inactive', label: 'Неактивные' },
];

const filteredMethods = computed(() => {
    const query = search.value.trim().toLowerCase();
    return methods.value.filter((row) => {
        if (query) {
            const haystack = `${row.name || ''} ${row.guid || ''}`.toLowerCase();
            if (!haystack.includes(query)) {
                return false;
            }
        }

        if (selectedCategory.value) {
            if (selectedCategory.value === EMPTY_CATEGORY) {
                if (row.category) {
                    return false;
                }
            } else if ((row.category || '') !== selectedCategory.value) {
                return false;
            }
        }

        if (selectedStatus.value === 'active' && !row.is_active) {
            return false;
        }
        if (selectedStatus.value === 'inactive' && row.is_active) {
            return false;
        }

        return true;
    });
});

function ensureDraft(guid) {
    if (!drafts[guid]) {
        drafts[guid] = {
            category: EMPTY_CATEGORY,
            comment: '',
            is_active: true,
        };
    }
}

function syncDrafts(rows) {
    const activeGuids = new Set(rows.map((row) => row.guid));
    for (const key of Object.keys(drafts)) {
        if (!activeGuids.has(key)) {
            delete drafts[key];
        }
    }
    for (const row of rows) {
        ensureDraft(row.guid);
        drafts[row.guid].category = row.category || EMPTY_CATEGORY;
        drafts[row.guid].comment = row.comment || '';
        drafts[row.guid].is_active = Boolean(row.is_active);
    }
}

async function loadPaymentMethods() {
    loading.value = true;
    try {
        const data = await fetchKitchenPaymentMethods({ include_inactive: true });
        methods.value = Array.isArray(data) ? data : [];
        syncDrafts(methods.value);
    } catch (error) {
        toast.error(`Ошибка загрузки методов оплаты: ${error.response?.data?.detail || error.message}`);
    } finally {
        loading.value = false;
    }
}

async function saveMethod(method) {
    if (!canManage.value || !method?.guid) {
        return;
    }
    ensureDraft(method.guid);
    savingGuid.value = method.guid;

    try {
        const draft = drafts[method.guid];
        const updated = await patchKitchenPaymentMethod(method.guid, {
            category: draft.category === EMPTY_CATEGORY ? null : draft.category,
            comment: draft.comment || null,
            is_active: Boolean(draft.is_active),
        });
        methods.value = methods.value.map((row) =>
            row.guid === method.guid ? { ...row, ...updated } : row,
        );
        syncDrafts(methods.value);
        toast.success('Метод оплаты сохранен');
    } catch (error) {
        toast.error(`Ошибка сохранения: ${error.response?.data?.detail || error.message}`);
    } finally {
        savingGuid.value = '';
    }
}

loadPaymentMethods();
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kitchen-payment-methods' as *;
</style>
