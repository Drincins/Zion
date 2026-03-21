<template>
    <div class="employees-page__documents">
        <section class="employees-page__documents-section">
            <div class="employees-page__documents-header">
                <h4 class="employees-page__documents-title">Мед книжки</h4>
                <div
                    v-if="canManageMedical"
                    class="employees-page__documents-header-actions"
                >
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
                </div>
            </div>

            <p v-if="isLoading" class="employees-page__documents-hint">Загружаем данные…</p>
            <template v-else>
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

        <section v-if="showCisDocuments" class="employees-page__documents-section">
            <div class="employees-page__documents-header">
                <h4 class="employees-page__documents-title">Документы СНГ</h4>
                <Button
                    v-if="canManageCis"
                    color="primary"
                    size="sm"
                    @click="emit('start-create-cis-document')"
                >
                    Добавить документ
                </Button>
            </div>

            <p v-if="isLoading" class="employees-page__documents-hint">Загружаем данные…</p>
            <template v-else>
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
    </div>
</template>

<script setup>
import { ref, toRefs } from 'vue';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Select from '@/components/UI-components/Select.vue';
import Table from '@/components/UI-components/Table.vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';

const props = defineProps({
    medicalRecords: { type: Array, default: () => [] },
    cisDocuments: { type: Array, default: () => [] },
    medicalTypeOptions: { type: Array, default: () => [] },
    cisDocumentTypeOptions: { type: Array, default: () => [] },
    showCisDocuments: { type: Boolean, default: true },
    isLoading: { type: Boolean, default: false },
    formatDate: { type: Function, required: true },
    canManageMedical: { type: Boolean, default: false },
    canManageCis: { type: Boolean, default: false },
    medicalForm: { type: Object, default: () => ({}) },
    cisDocumentForm: { type: Object, default: () => ({}) },
    isMedicalBulkMode: { type: Boolean, default: false },
    isMedicalFormOpen: { type: Boolean, default: false },
    isCisFormOpen: { type: Boolean, default: false },
    savingMedical: { type: Boolean, default: false },
    savingCis: { type: Boolean, default: false },
    uploadingCisAttachment: { type: Boolean, default: false },
    deletingMedicalId: { type: [Number, String], default: null },
    deletingCisId: { type: [Number, String], default: null },
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
]);

const {
    medicalRecords,
    cisDocuments,
    medicalTypeOptions,
    cisDocumentTypeOptions,
    showCisDocuments,
    isLoading,
    formatDate,
    canManageMedical,
    canManageCis,
    medicalForm,
    cisDocumentForm,
    isMedicalBulkMode,
    isMedicalFormOpen,
    isCisFormOpen,
    savingMedical,
    savingCis,
    uploadingCisAttachment,
    deletingMedicalId,
    deletingCisId,
} = toRefs(props);

const cisFileInput = ref(null);


function triggerCisFileSelect() {
    cisFileInput.value?.click();
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
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/employees-documents-tab' as *;
</style>
