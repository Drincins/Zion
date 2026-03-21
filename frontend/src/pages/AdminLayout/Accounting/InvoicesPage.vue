<template>
    <div class="invoices-page">
        <header class="invoices-page__header">
            <div>
                <h2 class="invoices-page__title">Счета</h2>
                <p class="invoices-page__subtitle">Отправка на оплату, статусы и документы</p>
            </div>
        </header>

        <section class="invoices-page__filters-panel-button">
            <Button v-if="canCreate" color="primary" size="sm" @click="openCreateModal">Отправить в оплату</Button>
        </section>

        <section class="invoices-page__filters-panel">
            <button class="invoices-page__filters-toggle" type="button" @click="isFiltersOpen = !isFiltersOpen">
                Фильтры
                <span :class="['invoices-page__filters-icon', { 'is-open': isFiltersOpen }]">▼</span>
            </button>
            <div v-if="isFiltersOpen" class="invoices-page__filters-card">
                <div class="invoices-page__status-tabs">
                    <button
                        v-for="tab in statusTabs"
                        :key="tab.value"
                        type="button"
                        :class="['invoices-page__status-tab', { active: filters.status === tab.value }]"
                        @click="setStatus(tab.value)"
                    >
                        {{ tab.label }}
                    </button>
                </div>
                <div class="invoices-page__filters-grid">
                    <Input v-model="filters.search" label="Поиск по контрагенту/назначению" placeholder="Поиск..." />
                    <Select
                        v-model="filters.fromRestaurantId"
                        label="С какого ресторана"
                        :options="restaurantOptions"
                        placeholder="Все"
                    />
                    <Select
                        v-model="filters.forRestaurantId"
                        label="За какой ресторан платим"
                        :options="restaurantOptionsAll"
                        placeholder="Все"
                    />
                    <div class="invoices-page__filter-inline">
                        <span class="invoices-page__filter-date">
                            от <DateInput v-model="filters.dateFrom" />
                        </span>
                        <span class="invoices-page__filter-date">
                            до <DateInput v-model="filters.dateTo" />
                        </span>
                        <Checkbox
                            :model-value="filters.includeInExpenses"
                            label="Можно учесть в расходах"
                            @update:model-value="(v) => (filters.includeInExpenses = v)"
                        />
                    </div>
                    <div class="invoices-page__button">
                        <Button color="ghost" size="sm" :loading="loading" @click="loadInvoices">Обновить</Button>
                    </div>
                </div>
            </div>
        </section>

        <section class="invoices-page__card">
            <div class="invoices-page__card-header">
                <h3 class="invoices-page__card-title">Список счетов</h3>
                <div class="invoices-page__card-actions">
                    <Button color="ghost" size="sm" :loading="loading" @click="loadInvoices">Обновить</Button>
                </div>
            </div>
            <div v-if="loading" class="invoices-page__hint">Загрузка...</div>
            <div v-else>
                <div v-if="invoices.length" class="invoices-page__table-scroll">
                    <Table class="invoices-page__table">
                    <thead>
                        <tr>
                            <th>Дата заявки</th>
                            <th>Дата счета</th>
                            <th>Кто отправляет</th>
                            <th>С ресторана</th>
                            <th>За ресторан</th>
                            <th>Сумма</th>
                            <th>Кому</th>
                            <th>Назначение</th>
                            <th>Статус</th>
                            <th>ЭДО</th>
                            <th>Расходы</th>
                            <th>Файлы</th>
                            <th class="invoices-page__actions-column">Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr
                            v-for="invoice in invoices"
                            :key="invoice.id"
                            class="invoices-page__row"
                            @click="openEditModal(invoice)"
                        >
                            <td>{{ formatDate(invoice.sent_at) }}</td>
                            <td>{{ formatDate(invoice.invoice_date) }}</td>
                            <td>{{ formatUser(invoice.created_by_user_id) }}</td>
                            <td>{{ formatRestaurant(invoice.from_restaurant_id) }}</td>
                            <td>{{ formatRestaurant(invoice.for_restaurant_id) }}</td>
                            <td>{{ formatAmount(invoice.amount) }}</td>
                            <td>{{ invoice.payee }}</td>
                            <td>{{ invoice.purpose }}</td>
                            <td>{{ invoice.status || '-' }}</td>
                            <td>{{ invoice.closing_received_edo ? 'Да' : 'Нет' }}</td>
                            <td>
                                <div @click.stop>
                                <Checkbox
                                    :model-value="Boolean(invoice.include_in_expenses)"
                                    :disabled="!canEdit"
                                    @update:model-value="(v) => toggleInclude(invoice, v)"
                                />
                                </div>
                            </td>
                            <td class="invoices-page__files">
                                <a
                                    v-if="invoice.invoice_file_url"
                                    :href="invoice.invoice_file_url"
                                    @click.stop.prevent="openFilePreview(invoice.invoice_file_url, 'Счет')"
                                >
                                    Счет
                                </a>
                                <a
                                    v-if="invoice.payment_order_file_url"
                                    :href="invoice.payment_order_file_url"
                                    @click.stop.prevent="openFilePreview(invoice.payment_order_file_url, 'Платежное поручение')"
                                >
                                    П/п
                                </a>
                                <template v-if="invoice.closing_documents?.length">
                                    <a
                                        v-for="doc in invoice.closing_documents"
                                        :key="doc.id"
                                        :href="doc.file_url"
                                        @click.stop.prevent="openFilePreview(doc.file_url, `Закрывающий документ ${doc.id}`)"
                                    >
                                        Закр. {{ doc.id }}
                                    </a>
                                </template>
                            </td>
                            <td class="invoices-page__actions-column">
                                <div class="invoices-page__actions">
                                    <Button
                                        v-if="canEdit"
                                        color="ghost"
                                        size="sm"
                                        @click.stop="openEditModal(invoice)"
                                    >
                                        Ред.
                                    </Button>
                                    <Button
                                        v-if="canStatus"
                                        color="ghost"
                                        size="sm"
                                        @click.stop="openStatusModal(invoice)"
                                    >
                                        Статус
                                    </Button>
                                    <Button color="ghost" size="sm" @click.stop="openHistoryModal(invoice)">
                                        История
                                    </Button>
                                    <button
                                        v-if="canDelete"
                                        class="invoices-page__icon-button"
                                        type="button"
                                        :disabled="loading"
                                        title="Удалить"
                                        @click.stop="handleDelete(invoice)"
                                    >
                                        <BaseIcon name="Trash" />
                                    </button>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                    </Table>
                </div>
                <p v-else class="invoices-page__hint">Счета еще не созданы.</p>
            </div>
        </section>

        <!-- Модалка просмотра файлов -->
        <Modal v-if="isFileModalOpen" @close="closeFilePreview">
            <template #header>
                <div class="invoices-page__modal-header">
                    <span>{{ filePreviewTitle || 'Файл' }}</span>
                    <button
                        class="invoices-page__modal-close"
                        type="button"
                        aria-label="Закрыть"
                        @click="closeFilePreview"
                    >
                        ×
                    </button>
                </div>
            </template>
            <div class="invoices-page__file-preview">
                <img
                    v-if="filePreviewKind === 'image'"
                    :src="filePreviewUrl"
                    :alt="filePreviewTitle || 'Файл'"
                />
                <iframe
                    v-else-if="filePreviewKind === 'pdf'"
                    :src="filePreviewUrl"
                    title="Просмотр файла"
                ></iframe>
                <div v-else class="invoices-page__file-preview-fallback">
                    <p class="invoices-page__hint">Предпросмотр недоступен.</p>
                    <a :href="filePreviewUrl" target="_blank" rel="noopener">Открыть файл</a>
                </div>
            </div>
        </Modal>

        <!-- Модалка создания / редактирования счета -->
        <Modal v-if="isInvoiceModalOpen" @close="closeInvoiceModal">
            <template #header>
                {{ isEditMode ? 'Редактирование счета' : 'Отправить в оплату' }}
            </template>
            <div class="invoices-page__form">
                <Select
                    v-model="invoiceForm.fromRestaurantId"
                    :class="invoiceValidation.fromRestaurant"
                    label="С какого ресторана"
                    :options="availableRestaurantOptions"
                    placeholder="Выберите ресторан"
                    required
                />
                <Select
                    v-model="invoiceForm.forRestaurantId"
                    :class="invoiceValidation.forRestaurant"
                    label="За какой ресторан платим"
                    :options="restaurantOptionsAll"
                    placeholder="Выберите ресторан"
                    required
                />
                <Input
                    v-model="invoiceForm.amount"
                    :class="invoiceValidation.amount"
                    label="Сумма"
                    type="number"
                    step="0.01"
                    required
                />
                <Input v-model="invoiceForm.payee" :class="invoiceValidation.payee" label="Кому платим" required />
                <Input v-model="invoiceForm.purpose" :class="invoiceValidation.purpose" label="Назначение" required />
                <DateInput v-model="invoiceForm.invoiceDate" label="Дата счета" />
                <DateInput v-model="invoiceForm.sentAt" label="Дата отправки" />
                <Input v-model="invoiceForm.comment" label="Комментарий" />
                <Checkbox v-model="invoiceForm.includeInExpenses" label="Можно учесть в расходах" />
                <div :class="['invoices-page__file-field', invoiceValidation.invoiceFile]">
                    <span class="invoices-page__card-title">Счет (обязательно)</span>
                    <label class="invoices-page__upload-label">
                        <input type="file" accept=".pdf,.jpg,.png,.jpeg" @change="onInvoiceFileChange" />
                        <span>Загрузить файл</span>
                    </label>
                    <p class="invoices-page__hint">{{ invoiceForm.invoiceFileName || 'Файл не выбран' }}</p>
                </div>
                <div v-if="isEditMode" class="invoices-page__file-field">
                    <span class="invoices-page__card-title">Платежное поручение</span>
                    <label class="invoices-page__upload-label">
                        <input type="file" accept=".pdf,.jpg,.png,.jpeg" @change="onPaymentOrderChange" />
                        <span>Загрузить / заменить</span>
                    </label>
                    <p class="invoices-page__hint">
                        <a v-if="invoiceForm.paymentOrderUrl" :href="invoiceForm.paymentOrderUrl" target="_blank" rel="noopener">Открыть текущее</a>
                        <span v-else>Файл не загружен</span>
                    </p>
                </div>
                <div v-if="isEditMode" class="invoices-page__file-field">
                    <span class="invoices-page__card-title">Закрывающие документы</span>
                    <label class="invoices-page__upload-label">
                        <input type="file" multiple accept=".pdf,.jpg,.png,.jpeg" @change="onClosingDocChange" />
                        <span>Добавить документы</span>
                    </label>
                    <Checkbox
                        v-model="invoiceForm.closingReceivedEdo"
                        label="Документы получены в ЭДО"
                        @update:model-value="handleToggleEdo"
                    />
                    <div class="invoices-page__links">
                        <template v-if="invoiceForm.closingDocuments?.length">
                            <a
                                v-for="doc in invoiceForm.closingDocuments"
                                :key="doc.id || doc.file_key"
                                :href="doc.file_url"
                                target="_blank"
                                rel="noopener"
                            >
                                Документ {{ doc.id || doc.file_key }}
                            </a>
                        </template>
                        <p v-else class="invoices-page__hint">Пока нет загруженных документов</p>
                    </div>
                </div>
            </div>
            <template #footer>
                <div class="invoices-page__actions">
                    <Button color="ghost" size="sm" :disabled="saving" @click="closeInvoiceModal">Отмена</Button>
                    <Button color="primary" size="sm" :loading="saving" @click="handleSubmitInvoice">
                        {{ isEditMode ? 'Сохранить' : 'Создать' }}
                    </Button>
                </div>
            </template>
        </Modal>

        <!-- Модалка истории изменений -->
        <Modal v-if="isHistoryModalOpen" @close="closeHistoryModal">
            <template #header>История изменений</template>
            <div class="invoices-page__history">
                <div class="invoices-page__history-block">
                    <h4 class="invoices-page__history-title">История изменений</h4>
                    <div v-if="changesLoading" class="invoices-page__hint">Загрузка...</div>
                    <div v-else-if="changes.length" class="invoices-page__history-table-scroll">
                        <Table class="invoices-page__history-table">
                            <thead>
                                <tr>
                                    <th>Поле</th>
                                    <th>Было</th>
                                    <th>Стало</th>
                                    <th>Когда</th>
                                    <th>Кто</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="change in changes" :key="change.id">
                                    <td>{{ change.field }}</td>
                                    <td>{{ change.old_value || '-' }}</td>
                                    <td>{{ change.new_value || '-' }}</td>
                                    <td>{{ formatDateTime(change.changed_at) }}</td>
                                    <td>{{ formatUser(change.changed_by_user_id) }}</td>
                                </tr>
                            </tbody>
                        </Table>
                    </div>
                    <p v-else class="invoices-page__hint">История изменений пустая.</p>
                </div>
                <div class="invoices-page__history-block">
                    <h4 class="invoices-page__history-title">Журнал действий</h4>
                    <div v-if="eventsLoading" class="invoices-page__hint">Загрузка...</div>
                    <Table v-else-if="events.length">
                        <thead>
                            <tr>
                                <th>Событие</th>
                                <th>Комментарий</th>
                                <th>Когда</th>
                                <th>Кто</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="event in events" :key="event.id">
                                <td>{{ event.event_type }}</td>
                                <td>{{ event.message || '-' }}</td>
                                <td>{{ formatDateTime(event.created_at) }}</td>
                                <td>{{ formatUser(event.actor_user_id) }}</td>
                            </tr>
                        </tbody>
                    </Table>
                    <p v-else class="invoices-page__hint">Журнал пуст.</p>
                </div>
            </div>
        </Modal>

        <!-- Модалка смены статуса -->
        <Modal v-if="isStatusModalOpen" @close="closeStatusModal">
            <template #header>Смена статуса</template>
            <div class="invoices-page__form">
                <Select
                    v-model="statusForm.status"
                    label="Статус"
                    :options="statusOptions"
                    placeholder="Выберите статус"
                />
            </div>
            <template #footer>
                <div class="invoices-page__actions">
                    <Button color="ghost" size="sm" :disabled="saving" @click="closeStatusModal">Отмена</Button>
                    <Button color="primary" size="sm" :loading="saving" @click="handleStatusUpdate">Обновить</Button>
                </div>
            </template>
        </Modal>

    </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';
import {
    createAccountingInvoice,
    deleteAccountingInvoice,
    fetchAccountingInvoiceChanges,
    fetchAccountingInvoiceEvents,
    fetchAccountingInvoices,
    fetchEmployees,
    fetchRestaurants,
    updateAccountingInvoice,
    updateAccountingInvoiceStatus,
    uploadAccountingClosingDocument,
    uploadAccountingInvoiceFile,
    uploadAccountingPaymentOrder,
    analyzeAccountingInvoiceLLM,
} from '@/api';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Select from '@/components/UI-components/Select.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import Table from '@/components/UI-components/Table.vue';
import Modal from '@/components/UI-components/Modal.vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import { useUserStore } from '@/stores/user';
import { formatDateTimeValue, formatDateValue, formatNumberValue } from '@/utils/format';
import { useDebounce } from '@/composables/useDebounce';

const toast = useToast();
const userStore = useUserStore();

const STATUS_TABS = [
    { label: 'Все', value: '' },
    { label: 'Отправлен в бухгалтерию', value: 'Отправлен в бухгалтерию' },
    { label: 'Отправлен в оплату', value: 'Отправлен в оплату' },
    { label: 'Оплачен', value: 'Оплачен' },
    { label: 'Требуются закрывающие документы', value: 'Требуются закрывающие документы' },
    { label: 'Счет закрыт', value: 'Счет закрыт' },
];

const statusTabs = STATUS_TABS;
const statusOptions = STATUS_TABS.filter((item) => item.value).map((item) => ({ value: item.value, label: item.label }));

const invoices = ref([]);
const total = ref(0);
const loading = ref(false);
const isFiltersOpen = ref(false);
let invoicesLoadAbortController = null;
let invoicesLoadRequestSeq = 0;

const restaurants = ref([]);
const staff = ref([]);
const restaurantOptions = computed(() =>
    (restaurants.value || []).map((r) => ({ value: String(r.id), label: r.name || `Ресторан #${r.id}` })),
);
const restaurantOptionsAll = computed(() => [{ value: '', label: 'Все рестораны' }, ...restaurantOptions.value]);
const availableRestaurantOptions = computed(() => {
    const ids = new Set((userStore.restaurantIds || []).map((id) => String(id)));
    if (!ids.size) {
        return restaurantOptions.value;
    }
    return restaurantOptions.value.filter((opt) => ids.has(opt.value));
});

const filters = reactive({
    status: '',
    search: '',
    fromRestaurantId: '',
    forRestaurantId: '',
    dateFrom: '',
    dateTo: '',
    includeInExpenses: false,
});
const debouncedLoadInvoices = useDebounce(() => {
    loadInvoices();
}, 400);

const isInvoiceModalOpen = ref(false);
const isEditMode = ref(false);
const isHistoryModalOpen = ref(false);
const saving = ref(false);
const ocrLoading = ref(false);
const paymentUploading = ref(false);
const closingUploading = ref(false);
const isValidationActive = ref(false);

const invoiceForm = reactive({
    id: null,
    fromRestaurantId: '',
    forRestaurantId: '',
    amount: '',
    payee: '',
    purpose: '',
    invoiceDate: '',
    sentAt: new Date().toISOString().slice(0, 10),
    comment: '',
    includeInExpenses: false,
    closingReceivedEdo: false,
    invoiceFile: null,
    invoiceFileName: '',
    paymentOrderUrl: '',
    closingDocuments: [],
});

const invoiceValidation = computed(() => {
    if (!isValidationActive.value) {
        return {
            fromRestaurant: '',
            forRestaurant: '',
            amount: '',
            payee: '',
            purpose: '',
            invoiceFile: '',
        };
    }

    const amountValue = invoiceForm.amount;
    const amountValid = Boolean(amountValue) && !Number.isNaN(Number(amountValue));
    const payeeValid = Boolean(invoiceForm.payee && invoiceForm.payee.trim());
    const purposeValid = Boolean(invoiceForm.purpose && invoiceForm.purpose.trim());
    const fileRequired = !isEditMode.value;
    const fileValid = !fileRequired || Boolean(invoiceForm.invoiceFile);

    return {
        fromRestaurant: invoiceForm.fromRestaurantId ? '' : 'is-invalid',
        forRestaurant: invoiceForm.forRestaurantId ? '' : 'is-invalid',
        amount: amountValid ? '' : 'is-invalid',
        payee: payeeValid ? '' : 'is-invalid',
        purpose: purposeValid ? '' : 'is-invalid',
        invoiceFile: fileRequired ? (fileValid ? '' : 'is-invalid') : '',
    };
});

const isStatusModalOpen = ref(false);
const statusForm = reactive({
    id: null,
    status: '',
});

const changes = ref([]);
const events = ref([]);
const changesLoading = ref(false);
const eventsLoading = ref(false);

const isFileModalOpen = ref(false);
const filePreviewUrl = ref('');
const filePreviewTitle = ref('');
const filePreviewKind = ref('file');

const canCreate = computed(() => userStore.hasPermission('accounting.invoices.create'));
const canEdit = computed(() => userStore.hasPermission('accounting.invoices.edit'));
const canStatus = computed(() => userStore.hasPermission('accounting.invoices.status'));
const canDelete = computed(() => userStore.hasPermission('accounting.invoices.delete'));
const currentUserName = computed(() => userStore.fullName || userStore.login || 'Текущий пользователь');
const staffMap = computed(() => {
    const map = new Map();
    for (const user of staff.value) {
        if (!user?.id) continue;
        map.set(user.id, formatUserLabel(user));
    }
    return map;
});

function setStatus(value) {
    filters.status = value;
    loadInvoices();
}

function formatDate(value) {
    return formatDateValue(value, {
        emptyValue: '—',
        invalidValue: '—',
        locale: 'ru-RU',
    });
}

function formatDateTime(value) {
    return formatDateTimeValue(value, {
        emptyValue: '—',
        invalidValue: '—',
        locale: 'ru-RU',
    });
}

function formatAmount(value) {
    return formatNumberValue(value, {
        emptyValue: '—',
        invalidValue: '—',
        locale: 'ru-RU',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

function formatUser(userId) {
    if (!userId) return '—';
    if (Number(userId) === Number(userStore.id)) {
        return currentUserName.value;
    }
    return staffMap.value.get(Number(userId)) || `ID ${userId}`;
}

function formatUserLabel(user) {
    if (!user) {
        return '';
    }
    const fullName = [user.last_name, user.first_name].filter(Boolean).join(' ').trim();
    return fullName || user.username || `ID ${user.id}`;
}

function formatRestaurant(restaurantId) {
    const found = restaurantOptions.value.find((r) => Number(r.value) === Number(restaurantId));
    return found?.label || `ID ${restaurantId}`;
}

function getFileKind(url) {
    if (!url) return 'file';
    const cleanUrl = url.split('#')[0].split('?')[0];
    const ext = cleanUrl.slice(cleanUrl.lastIndexOf('.') + 1).toLowerCase();
    if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg'].includes(ext)) {
        return 'image';
    }
    if (ext === 'pdf') {
        return 'pdf';
    }
    return 'file';
}

function openFilePreview(url, title) {
    if (!url) return;
    filePreviewUrl.value = url;
    filePreviewTitle.value = title || 'Файл';
    filePreviewKind.value = getFileKind(url);
    isFileModalOpen.value = true;
}

function closeFilePreview() {
    isFileModalOpen.value = false;
    filePreviewUrl.value = '';
    filePreviewTitle.value = '';
    filePreviewKind.value = 'file';
}

async function loadStaff() {
    try {
        const data = await fetchEmployees({ include_fired: true, limit: 1000 });
        staff.value = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];
    } catch (error) {
        console.error(error);
        staff.value = [];
    }
}

async function loadRestaurants() {
    try {
        const data = await fetchRestaurants();
        restaurants.value = Array.isArray(data) ? data : data?.items || [];
    } catch (error) {
        console.error(error);
    }
}

async function loadInvoices() {
    if (invoicesLoadAbortController) {
        invoicesLoadAbortController.abort();
        invoicesLoadAbortController = null;
    }
    const abortController = new AbortController();
    invoicesLoadAbortController = abortController;
    const requestSeq = ++invoicesLoadRequestSeq;
    loading.value = true;
    try {
        const params = {
            status: filters.status || undefined,
            search: filters.search || undefined,
            from_restaurant_id: filters.fromRestaurantId || undefined,
            for_restaurant_id: filters.forRestaurantId || undefined,
            date_from: filters.dateFrom || undefined,
            date_to: filters.dateTo || undefined,
            include_in_expenses: filters.includeInExpenses || undefined,
            limit: 200,
            offset: 0,
        };
        const data = await fetchAccountingInvoices(params, {
            signal: abortController.signal,
        });
        if (requestSeq !== invoicesLoadRequestSeq) {
            return;
        }
        invoices.value = data?.items || [];
        total.value = data?.total || 0;
    } catch (error) {
        if (error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError') {
            return;
        }
        if (requestSeq !== invoicesLoadRequestSeq) {
            return;
        }
        toast.error(error?.response?.data?.detail || 'Не удалось загрузить счета');
        console.error(error);
    } finally {
        if (requestSeq === invoicesLoadRequestSeq) {
            loading.value = false;
        }
        if (invoicesLoadAbortController === abortController) {
            invoicesLoadAbortController = null;
        }
    }
}

function resetInvoiceForm() {
    invoiceForm.id = null;
    invoiceForm.fromRestaurantId = '';
    invoiceForm.forRestaurantId = '';
    invoiceForm.amount = '';
    invoiceForm.payee = '';
    invoiceForm.purpose = '';
    invoiceForm.invoiceDate = '';
    invoiceForm.sentAt = new Date().toISOString().slice(0, 10);
    invoiceForm.comment = '';
    invoiceForm.includeInExpenses = false;
    invoiceForm.closingReceivedEdo = false;
    invoiceForm.invoiceFile = null;
    invoiceForm.invoiceFileName = '';
    invoiceForm.paymentOrderUrl = '';
    invoiceForm.closingDocuments = [];
}

function openCreateModal() {
    resetInvoiceForm();
    const userRestaurantId = (userStore.restaurantIds || [])[0];
    if (userRestaurantId) {
        invoiceForm.fromRestaurantId = String(userRestaurantId);
    }
    invoiceForm.sentAt = new Date().toISOString().slice(0, 10);
    isValidationActive.value = false;
    isEditMode.value = false;
    isInvoiceModalOpen.value = true;
}

function openEditModal(invoice) {
    resetInvoiceForm();
    invoiceForm.id = invoice.id;
    invoiceForm.fromRestaurantId = invoice.from_restaurant_id ? String(invoice.from_restaurant_id) : '';
    invoiceForm.forRestaurantId = invoice.for_restaurant_id ? String(invoice.for_restaurant_id) : '';
    invoiceForm.amount = invoice.amount ?? '';
    invoiceForm.payee = invoice.payee || '';
    invoiceForm.purpose = invoice.purpose || '';
    invoiceForm.invoiceDate = invoice.invoice_date ? invoice.invoice_date.slice(0, 10) : '';
    invoiceForm.sentAt = invoice.sent_at ? invoice.sent_at.slice(0, 10) : new Date().toISOString().slice(0, 10);
    invoiceForm.comment = invoice.comment || '';
    invoiceForm.includeInExpenses = Boolean(invoice.include_in_expenses);
    invoiceForm.closingReceivedEdo = Boolean(invoice.closing_received_edo);
    invoiceForm.invoiceFileName = invoice.invoice_file_key ? 'Файл загружен' : '';
    invoiceForm.paymentOrderUrl = invoice.payment_order_file_url || '';
    invoiceForm.closingDocuments = invoice.closing_documents || [];
    isValidationActive.value = false;
    isEditMode.value = true;
    isInvoiceModalOpen.value = true;
}

function closeInvoiceModal() {
    isInvoiceModalOpen.value = false;
    isEditMode.value = false;
    isValidationActive.value = false;
    resetInvoiceForm();
}

function openHistoryModal(invoice) {
    if (!invoice?.id) return;
    isHistoryModalOpen.value = true;
    loadInvoiceDetails(invoice.id);
}

function closeHistoryModal() {
    isHistoryModalOpen.value = false;
    changes.value = [];
    events.value = [];
}

function onInvoiceFileChange(event) {
    const file = event?.target?.files?.[0];
    if (file) {
        invoiceForm.invoiceFile = file;
        invoiceForm.invoiceFileName = file.name;
        runOcrPrefill(file);
    }
}

function onPaymentOrderChange(event) {
    const file = event?.target?.files?.[0];
    if (!file || !invoiceForm.id) return;
    paymentUploading.value = true;
    uploadAccountingPaymentOrder(invoiceForm.id, file)
        .then((data) => {
            invoiceForm.paymentOrderUrl = data?.payment_order_file_url || '';
            toast.success('Платежное поручение загружено');
            loadInvoices();
        })
        .catch((error) => {
            toast.error(error?.response?.data?.detail || 'Не удалось загрузить файл');
            console.error(error);
        })
        .finally(() => {
            paymentUploading.value = false;
            if (event?.target) event.target.value = '';
        });
}

function onClosingDocChange(event) {
    const files = event?.target?.files;
    if (!files?.length || !invoiceForm.id) return;
    const uploads = Array.from(files);
    closingUploading.value = true;
    Promise.all(
        uploads.map((file) =>
            uploadAccountingClosingDocument(invoiceForm.id, file).catch((error) => {
                toast.error(error?.response?.data?.detail || 'Не удалось загрузить закрывающий документ');
                console.error(error);
            }),
        ),
    )
        .then(() => {
            toast.success('Закрывающие документы загружены');
            loadInvoices();
            loadInvoiceDetails(invoiceForm.id);
        })
        .finally(() => {
            closingUploading.value = false;
            if (event?.target) event.target.value = '';
        });
}

async function runOcrPrefill(file) {
    if (!file) return;
    ocrLoading.value = true;
    try {
        const data = await analyzeAccountingInvoiceLLM(file);
        if (data?.amount) {
            invoiceForm.amount = String(data.amount);
        }
        if (data?.payee && !invoiceForm.payee) {
            invoiceForm.payee = data.payee;
        }
        if (data?.purpose && !invoiceForm.purpose) {
            invoiceForm.purpose = data.purpose;
        }
        if (data?.invoice_date && !invoiceForm.invoiceDate) {
            invoiceForm.invoiceDate =
                data.invoice_date.length === 10 ? data.invoice_date : data.invoice_date.slice(0, 10);
        }
        if (data?.sent_at && !invoiceForm.sentAt) {
            invoiceForm.sentAt = data.sent_at.length === 10 ? data.sent_at : data.sent_at.slice(0, 10);
        }
        if (data?.text) {
            toast.success('Счет распознан, данные подставлены');
        }
    } catch (error) {
        console.error(error);
        toast.error(error?.response?.data?.detail || 'Не удалось распознать файл');
    } finally {
        ocrLoading.value = false;
    }
}

function validateForm() {
    if (!invoiceForm.fromRestaurantId || !invoiceForm.forRestaurantId) {
        toast.error('Укажите рестораны');
        return false;
    }
    if (!invoiceForm.amount || Number.isNaN(Number(invoiceForm.amount))) {
        toast.error('Введите корректную сумму');
        return false;
    }
    if (!invoiceForm.payee || !invoiceForm.purpose) {
        toast.error('Укажите получателя и назначение');
        return false;
    }
    if (!isEditMode.value && !invoiceForm.invoiceFile) {
        toast.error('Загрузите файл счета');
        return false;
    }
    return true;
}

async function handleSubmitInvoice() {
    if (!isEditMode.value) {
        isValidationActive.value = true;
    }
    if (!validateForm()) {
        return;
    }
    saving.value = true;
    try {
        if (isEditMode.value && invoiceForm.id) {
            const payload = {
                from_restaurant_id: invoiceForm.fromRestaurantId ? Number(invoiceForm.fromRestaurantId) : null,
                for_restaurant_id: invoiceForm.forRestaurantId ? Number(invoiceForm.forRestaurantId) : null,
                amount: invoiceForm.amount ? Number(invoiceForm.amount) : null,
                payee: invoiceForm.payee,
                purpose: invoiceForm.purpose,
                invoice_date: invoiceForm.invoiceDate || null,
                sent_at: invoiceForm.sentAt || null,
                comment: invoiceForm.comment,
                include_in_expenses: invoiceForm.includeInExpenses,
                closing_received_edo: invoiceForm.closingReceivedEdo,
            };
            await updateAccountingInvoice(invoiceForm.id, payload);
            if (invoiceForm.invoiceFile) {
                await uploadAccountingInvoiceFile(invoiceForm.id, invoiceForm.invoiceFile);
            }
            toast.success('Счет обновлен');
        } else {
            const formData = new FormData();
            formData.append('from_restaurant_id', invoiceForm.fromRestaurantId);
            formData.append('for_restaurant_id', invoiceForm.forRestaurantId);
            formData.append('amount', invoiceForm.amount);
            formData.append('payee', invoiceForm.payee);
            formData.append('purpose', invoiceForm.purpose);
            if (invoiceForm.invoiceDate) {
                formData.append('invoice_date', invoiceForm.invoiceDate);
            }
            formData.append('sent_at', invoiceForm.sentAt || new Date().toISOString().slice(0, 10));
            formData.append('comment', invoiceForm.comment || '');
            formData.append('include_in_expenses', invoiceForm.includeInExpenses ? 'true' : 'false');
            formData.append('invoice_file', invoiceForm.invoiceFile);
            await createAccountingInvoice(formData);
            toast.success('Счет создан');
        }
        closeInvoiceModal();
        await loadInvoices();
    } catch (error) {
        toast.error(error?.response?.data?.detail || 'Ошибка сохранения');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

async function handleDelete(invoice) {
    if (!invoice?.id) return;
    if (!window.confirm('Удалить счет?')) return;
    try {
        await deleteAccountingInvoice(invoice.id);
        toast.success('Счет удален');
        await loadInvoices();
    } catch (error) {
        toast.error(error?.response?.data?.detail || 'Не удалось удалить');
        console.error(error);
    }
}

function openStatusModal(invoice) {
    statusForm.id = invoice.id;
    statusForm.status = invoice.status || '';
    isStatusModalOpen.value = true;
}

function closeStatusModal() {
    statusForm.id = null;
    statusForm.status = '';
    isStatusModalOpen.value = false;
}

async function handleStatusUpdate() {
    if (!statusForm.id || !statusForm.status) {
        toast.error('Выберите статус');
        return;
    }
    saving.value = true;
    try {
        await updateAccountingInvoiceStatus(statusForm.id, { status: statusForm.status });
        toast.success('Статус обновлен');
        closeStatusModal();
        await loadInvoices();
    } catch (error) {
        toast.error(error?.response?.data?.detail || 'Не удалось обновить статус');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

async function loadInvoiceDetails(invoiceId) {
    if (!invoiceId) return;
    try {
        changesLoading.value = true;
        eventsLoading.value = true;
        const [changesData, eventsData] = await Promise.all([
            fetchAccountingInvoiceChanges(invoiceId),
            fetchAccountingInvoiceEvents(invoiceId),
        ]);
        changes.value = changesData || [];
        events.value = eventsData || [];
    } catch (error) {
        console.error(error);
    } finally {
        changesLoading.value = false;
        eventsLoading.value = false;
    }
}

async function toggleInclude(invoice, value) {
    if (!canEdit.value) return;
    try {
        await updateAccountingInvoice(invoice.id, { include_in_expenses: value });
        toast.success('Изменено');
        await loadInvoices();
    } catch (error) {
        toast.error(error?.response?.data?.detail || 'Не удалось сохранить');
        console.error(error);
    }
}

async function handleToggleEdo(value) {
    if (!isEditMode.value || !invoiceForm.id) return;
    saving.value = true;
    try {
        await updateAccountingInvoice(invoiceForm.id, { closing_received_edo: value });
        invoiceForm.closingReceivedEdo = value;
        toast.success('Статус ЭДО обновлен');
        await loadInvoices();
        await loadInvoiceDetails(invoiceForm.id);
    } catch (error) {
        toast.error(error?.response?.data?.detail || 'Не удалось обновить ЭДО');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

onMounted(async () => {
    await loadStaff();
    await loadRestaurants();
    await loadInvoices();
});

onBeforeUnmount(() => {
    if (invoicesLoadAbortController) {
        invoicesLoadAbortController.abort();
        invoicesLoadAbortController = null;
    }
});

watch(
    () => filters.search,
    () => {
        debouncedLoadInvoices();
    },
    { flush: 'post' },
);
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/accounting-invoices' as *;
</style>
