<template>
    <div class="employees-page__documents">
        <section v-if="canViewMedical" class="employees-page__documents-section">
            <div class="employees-page__documents-header">
                <div class="employees-page__documents-heading">
                    <h4 class="employees-page__documents-title">Мед книжки</h4>
                    <p class="employees-page__documents-hint">
                        {{ medicalSummary() }}
                    </p>
                </div>
                <div class="employees-page__documents-header-actions">
                    <template v-if="medicalExpanded && canManageMedical">
                        <Button
                            color="secondary"
                            size="sm"
                            :disabled="savingMedical || !medicalTypeOptions.length"
                            @click="emit('start-create-medical-bulk')"
                        >
                            Добавить все
                        </Button>
                        <Button
                            color="primary"
                            size="sm"
                            :disabled="savingMedical"
                            @click="emit('start-create-medical')"
                        >
                            Добавить запись
                        </Button>
                    </template>
                    <button
                        type="button"
                        class="employees-page__documents-toggle"
                        :aria-expanded="medicalExpanded"
                        @click="medicalExpanded = !medicalExpanded"
                    >
                        <span>{{ medicalExpanded ? 'Свернуть' : 'Развернуть' }}</span>
                        <BaseIcon
                            name="Arrow"
                            :class="[
                                'employees-page__documents-toggle-icon',
                                { 'is-open': medicalExpanded },
                            ]"
                        />
                    </button>
                </div>
            </div>

            <p v-if="medicalExpanded && isLoading" class="employees-page__documents-hint">Загружаем данные…</p>
            <template v-else-if="medicalExpanded">
                <div v-if="isMedicalFormOpen && !medicalForm.id" class="employees-page__documents-form">
                    <div class="employees-page__documents-form-grid">
                        <Select
                            v-if="!isMedicalBulkMode"
                            v-model="medicalForm.medicalCheckTypeId"
                            label="Тип"
                            :options="medicalTypeOptions"
                        />
                        <div v-else class="employees-page__documents-bulk-info">
                            <p class="employees-page__documents-hint">
                                Будут добавлены все типы анализов ({{ medicalTypeOptions.length }}) с указанной датой и комментарием.
                            </p>
                        </div>
                        <DateInput v-model="medicalForm.passedAt" label="Дата прохождения" />
                        <Input v-model="medicalForm.comment" label="Комментарий" />
                    </div>
                    <div class="employees-page__documents-actions">
                        <Button
                            color="primary"
                            size="sm"
                            :loading="savingMedical"
                            :disabled="savingMedical"
                            @click="emit('submit-medical-form')"
                        >
                            {{ isMedicalBulkMode ? 'Добавить все' : medicalForm.id ? 'Сохранить' : 'Добавить' }}
                        </Button>
                        <Button
                            color="ghost"
                            size="sm"
                            :disabled="savingMedical"
                            @click="emit('cancel-medical-form')"
                        >
                            Отмена
                        </Button>
                    </div>
                </div>

                <Table v-if="medicalRecords.length" class="employees-page__documents-table">
                    <thead>
                        <tr>
                            <th>Тип</th>
                            <th>Пройден</th>
                            <th>Следующий</th>
                            <th>Учреждение</th>
                            <th>Вложение</th>
                            <th v-if="canManageMedical" class="employees-page__documents-actions-header">Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="record in medicalRecords" :key="record.id">
                            <td>
                                <template v-if="isMedicalFormOpen && medicalForm.id === record.id">
                                    <Select
                                        v-model="medicalForm.medicalCheckTypeId"
                                        label="Тип"
                                        :options="medicalTypeOptions"
                                    />
                                </template>
                                <template v-else>
                                    {{ record.medical_check_type?.name || '-' }}
                                </template>
                            </td>
                            <td>
                                <template v-if="isMedicalFormOpen && medicalForm.id === record.id">
                                    <DateInput v-model="medicalForm.passedAt" />
                                </template>
                                <template v-else>
                                    {{ formatDate(record.passed_at) }}
                                </template>
                            </td>
                            <td>{{ formatDate(record.next_due_at) }}</td>
                            <td>
                                <span :class="['employees-page__status-pill', statusClass(record.status)]">
                                    {{ statusLabel(record.status) }}
                                </span>
                            </td>
                            <td class="employees-page__documents-comment">
                                <template v-if="isMedicalFormOpen && medicalForm.id === record.id">
                                    <Input v-model="medicalForm.comment" placeholder="Комментарий" />
                                </template>
                                <template v-else>
                                    {{ record.comment || '-' }}
                                </template>
                            </td>
                            <td v-if="canManageMedical" class="employees-page__documents-actions-header">
                                <div
                                    v-if="isMedicalFormOpen && medicalForm.id === record.id"
                                    class="employees-page__documents-inline-actions"
                                >
                                    <Button
                                        color="primary"
                                        size="sm"
                                        :loading="savingMedical"
                                        :disabled="savingMedical"
                                        @click="emit('submit-medical-form')"
                                    >
                                        Сохранить
                                    </Button>
                                    <Button
                                        color="ghost"
                                        size="sm"
                                        :disabled="savingMedical"
                                        @click="emit('cancel-medical-form')"
                                    >
                                        Отмена
                                    </Button>
                                </div>
                                <template v-else>
                                    <Button
                                        color="ghost"
                                        size="sm"
                                        @click="emit('start-edit-medical', record)"
                                    >
                                        Редактировать
                                    </Button>
                                    <button
                                        type="button"
                                        class="employees-page__documents-icon-button"
                                        :disabled="deletingMedicalId === record.id"
                                        title="Удалить"
                                        @click="emit('delete-medical-record', record.id)"
                                    >
                                        <BaseIcon name="Trash" />
                                    </button>
                                </template>
                            </td>
                        </tr>
                    </tbody>
                </Table>
                <p v-else class="employees-page__documents-hint">Записи медкнижек не найдены.</p>
            </template>
        </section>

        <section v-if="showCisDocuments && canViewCis" class="employees-page__documents-section">
            <div class="employees-page__documents-header">
                <div class="employees-page__documents-heading">
                    <h4 class="employees-page__documents-title">Документы СНГ</h4>
                    <p class="employees-page__documents-hint">
                        {{ cisSummary() }}
                    </p>
                </div>
                <div class="employees-page__documents-header-actions">
                    <Button
                        v-if="cisExpanded && canManageCis"
                        color="primary"
                        size="sm"
                        @click="emit('start-create-cis-document')"
                    >
                        Добавить документ
                    </Button>
                    <button
                        type="button"
                        class="employees-page__documents-toggle"
                        :aria-expanded="cisExpanded"
                        @click="cisExpanded = !cisExpanded"
                    >
                        <span>{{ cisExpanded ? 'Свернуть' : 'Развернуть' }}</span>
                        <BaseIcon
                            name="Arrow"
                            :class="[
                                'employees-page__documents-toggle-icon',
                                { 'is-open': cisExpanded },
                            ]"
                        />
                    </button>
                </div>
            </div>

            <p v-if="cisExpanded && isLoading" class="employees-page__documents-hint">Загружаем данные…</p>
            <template v-else-if="cisExpanded">
                <div v-if="isCisFormOpen" class="employees-page__documents-form">
                    <div class="employees-page__documents-form-grid">
                        <Select
                            v-model="cisDocumentForm.cisDocumentTypeId"
                            label="Тип"
                            :options="cisDocumentTypeOptions"
                        />
                        <Input v-model="cisDocumentForm.number" label="Номер" />
                        <DateInput v-model="cisDocumentForm.issuedAt" label="Дата выдачи" />
                        <DateInput v-model="cisDocumentForm.expiresAt" label="Действует до" />
                        <Input v-model="cisDocumentForm.issuer" label="Орган" />
                        <Input v-model="cisDocumentForm.attachmentUrl" label="Ссылка на вложение" />
                        <Input v-model="cisDocumentForm.comment" label="Комментарий" />
                    </div>
                    <div v-if="canManageCis" class="employees-page__documents-upload">
                        <input
                            ref="cisFileInput"
                            type="file"
                            class="employees-page__documents-file-input"
                            accept="image/*,.pdf,.doc,.docx,.png,.jpg,.jpeg,.webp"
                            @change="onCisFileSelected"
                        />
                        <Button
                            color="secondary"
                            size="sm"
                            :loading="uploadingCisAttachment"
                            :disabled="uploadingCisAttachment"
                            @click="triggerCisFileSelect"
                        >
                            Загрузить файл
                        </Button>
                        <p class="employees-page__documents-upload-hint">
                            После загрузки поле ссылки заполнится автоматически.
                        </p>
                    </div>
                    <div class="employees-page__documents-actions">
                        <Button
                            color="primary"
                            size="sm"
                            :loading="savingCis"
                            :disabled="savingCis"
                            @click="emit('submit-cis-document-form')"
                        >
                            {{ cisDocumentForm.id ? 'Сохранить' : 'Добавить' }}
                        </Button>
                        <Button
                            color="ghost"
                            size="sm"
                            :disabled="savingCis"
                            @click="emit('cancel-cis-document-form')"
                        >
                            Отмена
                        </Button>
                    </div>
                </div>

                <Table v-if="cisDocuments.length" class="employees-page__documents-table">
                    <thead>
                        <tr>
                            <th>Тип</th>
                            <th>Номер</th>
                            <th>Выдан</th>
                            <th>Действует до</th>
                            <th>Статус</th>
                            <th>Орган</th>
                            <th>Комментарий</th>
                            <th>Вложение</th>
                            <th v-if="canManageCis" class="employees-page__documents-actions-header">Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="record in cisDocuments" :key="record.id">
                            <td>{{ record.cis_document_type?.name || '—' }}</td>
                            <td>{{ record.number || '—' }}</td>
                            <td>{{ formatDate(record.issued_at) }}</td>
                            <td>{{ formatDate(record.expires_at) }}</td>
                            <td>
                                <span :class="['employees-page__status-pill', statusClass(record.status)]">
                                    {{ statusLabel(record.status) }}
                                </span>
                            </td>
                            <td>{{ record.issuer || '—' }}</td>
                            <td class="employees-page__documents-comment">{{ record.comment || '—' }}</td>
                            <td>
                                <a
                                    v-if="record.attachment_url"
                                    :href="record.attachment_url"
                                    class="employees-page__documents-link"
                                    target="_blank"
                                    rel="noopener"
                                >
                                    Открыть
                                </a>
                                <span v-else>—</span>
                            </td>
                            <td v-if="canManageCis" class="employees-page__documents-actions-header">
                                <button
                                    type="button"
                                    class="employees-page__documents-icon-button"
                                    title="Редактировать"
                                    @click="emit('start-edit-cis-document', record)"
                                >
                                    <BaseIcon name="Edit" />
                                </button>
                                <button
                                    type="button"
                                    class="employees-page__documents-icon-button"
                                    :disabled="deletingCisId === record.id"
                                    title="Удалить"
                                    @click="emit('delete-cis-document', record.id)"
                                >
                                    <BaseIcon name="Trash" />
                                </button>
                            </td>
                        </tr>
                    </tbody>
                </Table>
                <p v-else class="employees-page__documents-hint">Документы СНГ не найдены.</p>
            </template>
        </section>

        <section v-if="showFormalizedDocuments" class="employees-page__documents-section">
            <div class="employees-page__documents-header">
                <div class="employees-page__documents-heading">
                    <h4 class="employees-page__documents-title">Документы оформления</h4>
                    <p class="employees-page__documents-hint">
                        {{ employmentSummary() }}
                    </p>
                </div>
                <div class="employees-page__documents-header-actions">
                    <button
                        type="button"
                        class="employees-page__documents-toggle"
                        :aria-expanded="employmentExpanded"
                        @click="employmentExpanded = !employmentExpanded"
                    >
                        <span>{{ employmentExpanded ? 'Свернуть' : 'Развернуть' }}</span>
                        <BaseIcon
                            name="Arrow"
                            :class="[
                                'employees-page__documents-toggle-icon',
                                { 'is-open': employmentExpanded },
                            ]"
                        />
                    </button>
                </div>
            </div>

            <p v-if="employmentExpanded && isLoading" class="employees-page__documents-hint">Загружаем данные…</p>
            <template v-else-if="employmentExpanded">
                <div v-if="isEmploymentFormOpen" class="employees-page__documents-form">
                    <div class="employees-page__documents-form-grid">
                        <div class="employees-page__documents-bulk-info">
                            <p class="employees-page__documents-hint">
                                {{ employmentDocumentFormLabel }}
                            </p>
                        </div>
                        <DateInput v-model="employmentDocumentForm.issuedAt" label="Дата документа" />
                        <Input v-model="employmentDocumentForm.comment" label="Комментарий" />
                        <Input
                            v-model="employmentDocumentForm.attachmentUrl"
                            label="Ссылка на вложение"
                        />
                    </div>
                    <div v-if="canManageFormalized" class="employees-page__documents-upload">
                        <input
                            ref="employmentFileInput"
                            type="file"
                            class="employees-page__documents-file-input"
                            accept="image/*,.pdf,.doc,.docx,.png,.jpg,.jpeg,.webp"
                            @change="onEmploymentFileSelected"
                        />
                        <Button
                            color="secondary"
                            size="sm"
                            :loading="uploadingEmploymentAttachment"
                            :disabled="uploadingEmploymentAttachment"
                            @click="triggerEmploymentFileSelect"
                        >
                            Загрузить файл
                        </Button>
                        <p class="employees-page__documents-upload-hint">
                            После загрузки поле ссылки заполнится автоматически.
                        </p>
                    </div>
                    <div class="employees-page__documents-actions">
                        <Button
                            color="primary"
                            size="sm"
                            :loading="savingEmployment"
                            :disabled="savingEmployment"
                            @click="emit('submit-employment-document-form')"
                        >
                            {{ employmentDocumentForm.id ? 'Сохранить' : 'Добавить' }}
                        </Button>
                        <Button
                            color="ghost"
                            size="sm"
                            :disabled="savingEmployment"
                            @click="emit('cancel-employment-document-form')"
                        >
                            Отмена
                        </Button>
                    </div>
                </div>

                <Table class="employees-page__documents-table">
                    <thead>
                        <tr>
                            <th>Документ</th>
                            <th>Дата</th>
                            <th>Статус</th>
                            <th>Комментарий</th>
                            <th>Вложение</th>
                            <th v-if="canManageFormalized" class="employees-page__documents-actions-header">Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="record in employmentDocuments" :key="record.id">
                            <td>{{ record.document_name || '—' }}</td>
                            <td>{{ formatDate(record.issued_at) }}</td>
                            <td>
                                <span
                                    :class="[
                                        'employees-page__status-pill',
                                        employmentStatusClass(record),
                                    ]"
                                >
                                    {{ employmentStatusLabel(record) }}
                                </span>
                            </td>
                            <td class="employees-page__documents-comment">{{ record.comment || '—' }}</td>
                            <td>
                                <a
                                    v-if="record.attachment_url"
                                    :href="record.attachment_url"
                                    class="employees-page__documents-link"
                                    target="_blank"
                                    rel="noopener"
                                >
                                    Открыть
                                </a>
                                <span v-else>—</span>
                            </td>
                            <td v-if="canManageFormalized" class="employees-page__documents-actions-header">
                                <template v-if="record.exists">
                                    <button
                                        type="button"
                                        class="employees-page__documents-icon-button"
                                        title="Редактировать"
                                        @click="emit('start-edit-employment-document', record)"
                                    >
                                        <BaseIcon name="Edit" />
                                    </button>
                                    <button
                                        type="button"
                                        class="employees-page__documents-icon-button"
                                        :disabled="deletingEmploymentId === record.id"
                                        title="Удалить"
                                        @click="emit('delete-employment-document', record.id)"
                                    >
                                        <BaseIcon name="Trash" />
                                    </button>
                                </template>
                                <Button
                                    v-else
                                    color="ghost"
                                    size="sm"
                                    @click="emit('start-edit-employment-document', record)"
                                >
                                    Добавить
                                </Button>
                            </td>
                        </tr>
                    </tbody>
                </Table>
            </template>
        </section>
    </div>
</template>

<script setup>
import { ref, toRefs, watch } from 'vue';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Select from '@/components/UI-components/Select.vue';
import Table from '@/components/UI-components/Table.vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';

const props = defineProps({
    medicalRecords: { type: Array, default: () => [] },
    cisDocuments: { type: Array, default: () => [] },
    employmentDocuments: { type: Array, default: () => [] },
    medicalTypeOptions: { type: Array, default: () => [] },
    cisDocumentTypeOptions: { type: Array, default: () => [] },
    showCisDocuments: { type: Boolean, default: true },
    showFormalizedDocuments: { type: Boolean, default: false },
    isLoading: { type: Boolean, default: false },
    formatDate: { type: Function, required: true },
    canViewMedical: { type: Boolean, default: false },
    canViewCis: { type: Boolean, default: false },
    canManageMedical: { type: Boolean, default: false },
    canManageCis: { type: Boolean, default: false },
    canManageFormalized: { type: Boolean, default: false },
    medicalForm: { type: Object, default: () => ({}) },
    cisDocumentForm: { type: Object, default: () => ({}) },
    employmentDocumentForm: { type: Object, default: () => ({}) },
    isMedicalBulkMode: { type: Boolean, default: false },
    isMedicalFormOpen: { type: Boolean, default: false },
    isCisFormOpen: { type: Boolean, default: false },
    isEmploymentFormOpen: { type: Boolean, default: false },
    savingMedical: { type: Boolean, default: false },
    savingCis: { type: Boolean, default: false },
    savingEmployment: { type: Boolean, default: false },
    uploadingCisAttachment: { type: Boolean, default: false },
    uploadingEmploymentAttachment: { type: Boolean, default: false },
    deletingMedicalId: { type: [Number, String], default: null },
    deletingCisId: { type: [Number, String], default: null },
    deletingEmploymentId: { type: [Number, String], default: null },
    employmentDocumentFormLabel: { type: String, default: '' },
});

const emit = defineEmits([
    'start-create-medical',
    'start-create-medical-bulk',
    'start-edit-medical',
    'cancel-medical-form',
    'submit-medical-form',
    'delete-medical-record',
    'start-create-cis-document',
    'start-edit-cis-document',
    'cancel-cis-document-form',
    'submit-cis-document-form',
    'delete-cis-document',
    'upload-cis-attachment',
    'start-edit-employment-document',
    'cancel-employment-document-form',
    'submit-employment-document-form',
    'delete-employment-document',
    'upload-employment-attachment',
]);

const {
    medicalRecords,
    cisDocuments,
    employmentDocuments,
    medicalTypeOptions,
    cisDocumentTypeOptions,
    showCisDocuments,
    showFormalizedDocuments,
    isLoading,
    formatDate,
    canViewMedical,
    canViewCis,
    canManageMedical,
    canManageCis,
    canManageFormalized,
    medicalForm,
    cisDocumentForm,
    employmentDocumentForm,
    isMedicalBulkMode,
    isMedicalFormOpen,
    isCisFormOpen,
    isEmploymentFormOpen,
    savingMedical,
    savingCis,
    savingEmployment,
    uploadingCisAttachment,
    uploadingEmploymentAttachment,
    deletingMedicalId,
    deletingCisId,
    deletingEmploymentId,
    employmentDocumentFormLabel,
} = toRefs(props);

const cisFileInput = ref(null);
const employmentFileInput = ref(null);
const medicalExpanded = ref(false);
const cisExpanded = ref(false);
const employmentExpanded = ref(false);


function triggerCisFileSelect() {
    cisFileInput.value?.click();
}

function triggerEmploymentFileSelect() {
    employmentFileInput.value?.click();
}


function onCisFileSelected(event) {
    const [file] = event?.target?.files || [];
    if (file) {
        emit('upload-cis-attachment', file);
    }
    if (event?.target) {
        event.target.value = '';
    }
}

function onEmploymentFileSelected(event) {
    const [file] = event?.target?.files || [];
    if (file) {
        emit('upload-employment-attachment', file);
    }
    if (event?.target) {
        event.target.value = '';
    }
}

watch(
    () => isMedicalFormOpen.value,
    (value) => {
        if (value) {
            medicalExpanded.value = true;
        }
    },
    { immediate: true },
);

watch(
    () => isCisFormOpen.value,
    (value) => {
        if (value) {
            cisExpanded.value = true;
        }
    },
    { immediate: true },
);

watch(
    () => isEmploymentFormOpen.value,
    (value) => {
        if (value) {
            employmentExpanded.value = true;
        }
    },
    { immediate: true },
);

const statusLabels = {
    ok: 'В порядке',
    expiring: 'Скоро истекает',
    expired: 'Просрочено',
    unknown: 'Неизвестно',
};

const statusClasses = {
    ok: 'employees-page__status-pill--success',
    expiring: 'employees-page__status-pill--warning',
    expired: 'employees-page__status-pill--danger',
    unknown: 'employees-page__status-pill--muted',
};

function normalizeStatus(value) {
    if (!value || typeof value !== 'string') {
        return 'unknown';
    }
    const normalized = value.trim().toLowerCase();
    return normalized && normalized in statusLabels ? normalized : 'unknown';
}

function statusLabel(status) {
    return statusLabels[normalizeStatus(status)];
}

function statusClass(status) {
    return statusClasses[normalizeStatus(status)];
}

function employmentStatusLabel(record) {
    if (!record?.exists) {
        return 'Не добавлен';
    }
    return record?.attachment_url ? 'Загружен' : 'Без файла';
}

function employmentStatusClass(record) {
    if (!record?.exists) {
        return 'employees-page__status-pill--muted';
    }
    return record?.attachment_url
        ? 'employees-page__status-pill--success'
        : 'employees-page__status-pill--warning';
}

function medicalSummary() {
    const count = medicalRecords.value.length;
    if (!count) {
        return 'Записей пока нет.';
    }
    return `Всего записей: ${count}.`;
}

function cisSummary() {
    const count = cisDocuments.value.length;
    if (!count) {
        return 'Документы не добавлены.';
    }
    return `Добавлено документов: ${count}.`;
}

function employmentSummary() {
    const filledCount = employmentDocuments.value.filter((record) => record.exists).length;
    return `Заполнено ${filledCount} из ${employmentDocuments.value.length} обязательных документов.`;
}
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/employees-documents-tab' as *;
</style>
