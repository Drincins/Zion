<template>
    <Modal v-if="isOpen" @close="emit('close')">
        <template #header>
            <div class="employees-page__modal-header">
                <section ref="photoCardRef" class="employees-page__photo-card">
                    <div class="employees-page__photo-card-inner">
                        <div class="employees-page__photo-stack">
                            <input
                                v-if="canManageEmployees"
                                ref="fileInput"
                                type="file"
                                accept="image/*"
                                class="employees-page__photo-input"
                                @change="onPhotoSelected"
                            />
                            <div
                                class="employees-page__photo-preview"
                                :class="{
                                    'is-clickable': isPhotoClickable,
                                    'is-disabled': uploadingPhoto,
                                }"
                                :role="isPhotoClickable ? 'button' : null"
                                :tabindex="isPhotoClickable ? 0 : -1"
                                :aria-label="photoActionLabel"
                                :aria-disabled="!isPhotoClickable"
                                @click="handlePhotoClick"
                                @keydown="handlePhotoKeydown"
                            >
                                <img
                                    v-if="photoUrl"
                                    :src="photoUrl"
                                    alt="Фото сотрудника"
                                    @load="handlePhotoLoaded"
                                    @error="resetPhotoCardTheme"
                                />
                                <div v-else class="employees-page__photo-placeholder">
                                    {{ employeeInitials }}
                                </div>
                            </div>
                        </div>
                        <div class="employees-page__modal-heading">
                            <div class="employees-page__modal-title-row">
                                <h3 class="employees-page__modal-title">{{ formatFullName(activeEmployee) }}</h3>
                                <span
                                    v-if="canViewSensitiveStaffFields && statusLabel"
                                    class="employees-page__status-badge"
                                    :class="statusClass"
                                >
                                    {{ statusLabel }}
                                </span>
                            </div>
                            <p v-if="positionSummary" class="employees-page__modal-meta">
                                {{ positionSummary }}
                            </p>
                            <div class="employees-page__fingerprint-badge employees-page__fingerprint-badge--header">
                                <span class="employees-page__fingerprint-dot" :class="{ 'is-on': employeeCard?.has_fingerprint }"></span>
                                <span>{{ employeeCard?.has_fingerprint ? 'Отпечаток сохранен' : 'Отпечаток не задан' }}</span>
                            </div>
                        </div>
                    </div>
                </section>
                <nav
                    ref="modalTabsRef"
                    class="employees-page__modal-tabs"
                    role="tablist"
                >
                    <span
                        class="employees-page__modal-tab-indicator"
                        :style="tabsIndicatorStyle"
                        aria-hidden="true"
                    ></span>
                    <button
                        :ref="setModalTabRef('info')"
                        type="button"
                        :class="[
                            'employees-page__modal-tab',
                            { 'employees-page__modal-tab--active': activeTab === 'info' },
                        ]"
                        :aria-pressed="activeTab === 'info'"
                        @click="emit('update:activeTab', 'info')"
                    >
                        Данные
                    </button>
                    <button
                        :ref="setModalTabRef('shifts')"
                        type="button"
                        :class="[
                            'employees-page__modal-tab',
                            { 'employees-page__modal-tab--active': activeTab === 'shifts' },
                        ]"
                        :aria-pressed="activeTab === 'shifts'"
                        @click="emit('update:activeTab', 'shifts')"
                    >
                        Смены
                    </button>
                    <button
                        v-if="canViewTrainings"
                        :ref="setModalTabRef('trainings')"
                        type="button"
                        :class="[
                            'employees-page__modal-tab',
                            { 'employees-page__modal-tab--active': activeTab === 'trainings' },
                        ]"
                        :aria-pressed="activeTab === 'trainings'"
                        @click="emit('update:activeTab', 'trainings')"
                    >
                        Тренинги
                    </button>
                    <button
                        v-if="canManageUserPermissions"
                        :ref="setModalTabRef('permissions')"
                        type="button"
                        :class="[
                            'employees-page__modal-tab',
                            { 'employees-page__modal-tab--active': activeTab === 'permissions' },
                        ]"
                        :aria-pressed="activeTab === 'permissions'"
                        @click="emit('update:activeTab', 'permissions')"
                    >
                        Права
                    </button>
                    <button
                        :ref="setModalTabRef('finance')"
                        type="button"
                        :class="[
                            'employees-page__modal-tab',
                            { 'employees-page__modal-tab--active': activeTab === 'finance' },
                        ]"
                        :aria-pressed="activeTab === 'finance'"
                        @click="emit('update:activeTab', 'finance')"
                    >
                        Финансы
                    </button>
                    <button
                        v-if="canViewDocuments"
                        :ref="setModalTabRef('documents')"
                        type="button"
                        :class="[
                            'employees-page__modal-tab',
                            { 'employees-page__modal-tab--active': activeTab === 'documents' },
                        ]"
                        :aria-pressed="activeTab === 'documents'"
                        @click="emit('update:activeTab', 'documents')"
                    >
                        Документы
                    </button>

                    <button
                        v-if="canViewEmployeeChanges"
                        :ref="setModalTabRef('changes')"
                        type="button"
                        :class="[
                            'employees-page__modal-tab',
                            { 'employees-page__modal-tab--active': activeTab === 'changes' },
                        ]"
                        :aria-pressed="activeTab === 'changes'"
                        @click="emit('update:activeTab', 'changes')"
                    >Журнал изменений</button>
                </nav>
            </div>
        </template>

        <template #default>
            <EmployeeModalInfoTab
                v-if="activeTab === 'info'"
                :can-manage-employees="canManageEmployees"
                :card-loading="cardLoading"
                :is-edit-mode="isEditMode"
                :can-restore-employees="canRestoreEmployees"
                :restoring-employee="restoringEmployee"
                :deleting-employee="deletingEmployee"
                :employee-card="employeeCard"
                :active-employee="activeEmployee"
                :can-view-sensitive-staff-fields="canViewSensitiveStaffFields"
                :can-sync-employee-to-iiko="canSyncEmployeeToIiko"
                :syncing-employee-to-iiko="syncingEmployeeToIiko"
                :is-time-control-role="isTimeControlRole"
                :format-full-name="formatFullName"
                :format-gender="formatGender"
                :format-amount="formatAmount"
                :format-date="formatDate"
                @toggle-edit-mode="emit('toggle-edit-mode')"
                @restore-employee="emit('restore-employee')"
                @delete-employee="emit('delete-employee')"
                @sync-employee-to-iiko="emit('sync-employee-to-iiko')"
            />
            <EmployeeModalShiftsTab
                v-else-if="activeTab === 'shifts'"
                :attendance-date-from="attendanceDateFrom"
                :attendance-date-to="attendanceDateTo"
                :attendances-loading="attendancesLoading"
                :recalculating-night-minutes="recalculatingNightMinutes"
                :attendance-view-mode="attendanceViewMode"
                :attendance-restaurant-filter-value="attendanceRestaurantFilterValue"
                :attendance-shift-restaurant-options="attendanceShiftRestaurantOptions"
                :effective-attendance-summary="effectiveAttendanceSummary"
                :filtered-attendances="filteredAttendances"
                :rate-hidden="rateHidden"
                :format-date="formatDate"
                :format-attendance-restaurant="formatAttendanceRestaurant"
                :format-duration-minutes="formatDurationMinutes"
                @load-attendances="emit('load-attendances')"
                @update:attendance-date-from="emit('update:attendanceDateFrom', $event)"
                @update:attendance-date-to="emit('update:attendanceDateTo', $event)"
                @create-attendance="emit('create-attendance')"
                @recalculate-night-minutes="emit('recalculate-night-minutes')"
                @update:attendance-view-mode="attendanceViewMode = $event"
                @update:attendance-restaurant-filter-value="attendanceRestaurantFilterValue = $event"
                @open-attendance="emit('open-attendance', $event)"
            />
            <EmployeeModalTrainingsTab
                v-else-if="activeTab === 'trainings' && canViewTrainings"
                :can-manage-trainings="canManageTrainings"
                :creating-training-record="creatingTrainingRecord"
                :training-types-loading="trainingTypesLoading"
                :training-type-options="trainingTypeOptions"
                :trainings-loading="trainingsLoading"
                :employee-trainings="employeeTrainings"
                :editing-training-record="editingTrainingRecord"
                :updating-training-record="updatingTrainingRecord"
                :deleting-training-record-id="deletingTrainingRecordId"
                :format-date="formatDate"
                @open-training-assignment="emit('open-training-assignment')"
                @start-edit-training="emit('start-edit-training', $event)"
                @cancel-edit-training="emit('cancel-edit-training')"
                @update-training="emit('update-training')"
                @update-edit-training-field="emit('update-edit-training-field', $event)"
                @delete-training="emit('delete-training', $event)"
            />
            <div
                v-else-if="activeTab === 'permissions'"
                class="employees-page__modal-section employees-page__permissions-tab"
            >
                <EmployeePermissionsTab
                    :permissions="userPermissionCatalog"
                    :assigned-codes="userAssignedPermissionCodes"
                    :pending-codes="userPermissionPendingMap"
                    :loading="userPermissionsLoading"
                    :catalog-loading="userPermissionCatalogLoading"
                    :can-manage="canManageUserPermissions"
                    @toggle-permission="(payload) => emit('toggle-user-permission', payload)"
                />
            </div>
            <div
                v-else-if="activeTab === 'documents'"
                class="employees-page__modal-section employees-page__documents-tab"
            >
                <EmployeeDocumentsTab
                    :medical-records="medicalCheckRecords"
                    :cis-documents="cisDocumentRecords"
                    :employment-documents="employmentDocumentRecords"
                    :medical-type-options="medicalCheckTypeOptions"
                    :cis-document-type-options="cisDocumentTypeOptions"
                    :is-loading="documentsLoading"
                    :show-cis-documents="showCisDocuments"
                    :show-formalized-documents="showFormalizedDocuments"
                    :format-date="formatDate"
                    :can-view-medical="canViewMedicalChecks"
                    :can-view-cis="canViewCisDocuments"
                    :can-manage-medical="canManageMedicalChecks"
                    :can-manage-cis="canManageCisDocuments"
                    :can-manage-formalized="canManageDocuments"
                    :medical-form="medicalForm"
                    :cis-document-form="cisDocumentForm"
                    :employment-document-form="employmentDocumentForm"
                    :is-medical-bulk-mode="isMedicalBulkMode"
                    :is-medical-form-open="isMedicalFormOpen"
                    :is-cis-form-open="isCisFormOpen"
                    :is-employment-form-open="isEmploymentFormOpen"
                    :saving-medical="savingMedicalRecord"
                    :saving-cis="savingCisDocument"
                    :saving-employment="savingEmploymentDocument"
                    :uploading-cis-attachment="uploadingCisAttachment"
                    :uploading-employment-attachment="uploadingEmploymentAttachment"
                    :deleting-medical-id="deletingMedicalRecordId"
                    :deleting-cis-id="deletingCisDocumentId"
                    :deleting-employment-id="deletingEmploymentDocumentId"
                    :employment-document-form-label="employmentDocumentFormLabel"
                    @start-create-medical="emit('start-create-medical')"
                    @start-create-medical-bulk="emit('start-create-medical-bulk')"
                    @start-edit-medical="(record) => emit('start-edit-medical', record)"
                    @cancel-medical-form="emit('cancel-medical-form')"
                    @submit-medical-form="emit('submit-medical-form')"
                    @delete-medical-record="(id) => emit('delete-medical-record', id)"
                    @start-create-cis-document="emit('start-create-cis-document')"
                    @start-edit-cis-document="(record) => emit('start-edit-cis-document', record)"
                    @cancel-cis-document-form="emit('cancel-cis-document-form')"
                    @submit-cis-document-form="emit('submit-cis-document-form')"
                    @delete-cis-document="(id) => emit('delete-cis-document', id)"
                    @upload-cis-attachment="(file) => emit('upload-cis-attachment', file)"
                    @start-edit-employment-document="(record) => emit('start-edit-employment-document', record)"
                    @cancel-employment-document-form="emit('cancel-employment-document-form')"
                    @submit-employment-document-form="emit('submit-employment-document-form')"
                    @delete-employment-document="(id) => emit('delete-employment-document', id)"
                    @upload-employment-attachment="(file) => emit('upload-employment-attachment', file)"
                />
            </div>
            <EmployeeModalChangesTab
                v-else-if="activeTab === 'changes'"
                :can-view-employee-changes="canViewEmployeeChanges"
                :employee-change-events="employeeChangeEvents"
                :employee-change-events-loading="employeeChangeEventsLoading"
                :employee-change-events-loading-more="employeeChangeEventsLoadingMore"
                :employee-change-events-error="employeeChangeEventsError"
                :employee-change-events-has-more="employeeChangeEventsHasMore"
                :format-change-date="formatChangeDate"
                :format-change-field="formatChangeField"
                :format-change-value="formatChangeValue"
                :format-change-author="formatChangeAuthor"
                :format-change-comment="formatChangeComment"
                @load-more="emit('load-more-employee-change-events')"
            />
            <div v-else class="employees-page__modal-section">
                <EmployeeFinanceTab
                    :payroll-adjustment-type-options="payrollAdjustmentTypeOptions"
                    :payroll-restaurant-options="payrollRestaurantOptions"
                    :payroll-adjustments="payrollAdjustments"
                    :payroll-adjustments-loading="payrollAdjustmentsLoading"
                    :editing-payroll-adjustment="editingPayrollAdjustment"
                    :updating-payroll-adjustment="updatingPayrollAdjustment"
                    :deleting-payroll-adjustment-id="deletingPayrollAdjustmentId"
                    :payroll-adjustment-types="payrollAdjustmentTypes"
                    :payroll-adjustment-types-loading="payrollAdjustmentTypesLoading"
                    :responsible-options="responsibleOptions"
                    :format-date="formatDate"
                    :format-amount="formatAmount"
                    :format-responsible="formatResponsible"
                    :format-restaurant="formatRestaurant"
                    :rate-hidden="rateHidden"
                    :payroll-filter="payrollFilter"
                    @open-payroll-adjustment-form="emit('open-payroll-adjustment-form')"
                    @start-edit-payroll-adjustment="emit('start-edit-payroll-adjustment', $event)"
                    @cancel-edit-payroll-adjustment="emit('cancel-edit-payroll-adjustment')"
                    @update-payroll-adjustment="emit('update-payroll-adjustment')"
                    @delete-payroll-adjustment="emit('delete-payroll-adjustment', $event)"
                    @update:payroll-filter="payrollFilter = $event"
                />
            </div>
        </template>

        <template #footer>
            <Button color="ghost" @click="emit('close')">Закрыть</Button>
        </template>
    </Modal>

    <Modal v-if="isPhotoPreviewOpen" class="employees-page__photo-modal-window" @close="closePhotoPreview">
        <div class="employees-page__photo-modal">
            <img v-if="photoUrl" :src="photoUrl" alt="Фото сотрудника" />
        </div>
    </Modal>
</template>

<script setup>
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref, toRefs, watch } from 'vue';
import Button from '@/components/UI-components/Button.vue';
import Modal from '@/components/UI-components/Modal.vue';
import EmployeeModalInfoTab from './EmployeeModalInfoTab.vue';
import EmployeeModalShiftsTab from './EmployeeModalShiftsTab.vue';
import { formatChangeField, formatChangeValue } from '@/utils/changeEvents';
import { normalizeMojibakeText } from '@/utils/textEncoding';

const EmployeeModalChangesTab = defineAsyncComponent(() => import('./EmployeeModalChangesTab.vue'));
const EmployeeModalTrainingsTab = defineAsyncComponent(() => import('./EmployeeModalTrainingsTab.vue'));
const EmployeeDocumentsTab = defineAsyncComponent(() => import('./EmployeeDocumentsTab.vue'));
const EmployeeFinanceTab = defineAsyncComponent(() => import('./EmployeeFinanceTab.vue'));
const EmployeePermissionsTab = defineAsyncComponent(() => import('./EmployeePermissionsTab.vue'));

const props = defineProps({
    isOpen: { type: Boolean, default: false },
    activeEmployee: { type: Object, default: null },
    activeTab: { type: String, default: 'info' },
    canManageEmployees: { type: Boolean, default: false },
    cardLoading: { type: Boolean, default: false },
    isEditMode: { type: Boolean, default: false },
    deletingEmployee: { type: Boolean, default: false },
    employeeCard: { type: Object, default: null },
    formatFullName: { type: Function, required: true },
    formatGender: { type: Function, required: true },
    formatAmount: { type: Function, required: true },
    formatDate: { type: Function, required: true },
    formatResponsible: { type: Function, required: true },
    formatRestaurant: { type: Function, required: true },
    canManageUserPermissions: { type: Boolean, default: false },
    attendanceSummary: { type: Object, default: null },
    employeeAttendances: { type: Object, required: true },
    reversedAttendances: { type: Array, default: () => [] },
    attendancesLoading: { type: Boolean, default: false },
    attendanceDateFrom: { type: String, default: '' },
    attendanceDateTo: { type: String, default: '' },
    recalculatingNightMinutes: { type: Boolean, default: false },
    canViewTrainings: { type: Boolean, default: false },
    canManageTrainings: { type: Boolean, default: false },
    employeeTrainings: { type: Array, default: () => [] },
    trainingsLoading: { type: Boolean, default: false },
    trainingTypeOptions: { type: Array, default: () => [] },
    trainingTypesLoading: { type: Boolean, default: false },
    creatingTrainingRecord: { type: Boolean, default: false },
    editingTrainingRecord: { type: Object, default: () => ({}) },
    updatingTrainingRecord: { type: Boolean, default: false },
    deletingTrainingRecordId: { type: [Number, String], default: null },
    canViewDocuments: { type: Boolean, default: false },
    canViewMedicalChecks: { type: Boolean, default: false },
    canViewCisDocuments: { type: Boolean, default: false },
    medicalCheckRecords: { type: Array, default: () => [] },
    cisDocumentRecords: { type: Array, default: () => [] },
    employmentDocumentRecords: { type: Array, default: () => [] },
    medicalCheckTypeOptions: { type: Array, default: () => [] },
    cisDocumentTypeOptions: { type: Array, default: () => [] },
    documentsLoading: { type: Boolean, default: false },
    canManageMedicalChecks: { type: Boolean, default: false },
    canManageCisDocuments: { type: Boolean, default: false },
    canManageDocuments: { type: Boolean, default: false },
    medicalForm: { type: Object, default: () => ({}) },
    cisDocumentForm: { type: Object, default: () => ({}) },
    employmentDocumentForm: { type: Object, default: () => ({}) },
    isMedicalBulkMode: { type: Boolean, default: false },
    isMedicalFormOpen: { type: Boolean, default: false },
    isCisFormOpen: { type: Boolean, default: false },
    isEmploymentFormOpen: { type: Boolean, default: false },
    savingMedicalRecord: { type: Boolean, default: false },
    savingCisDocument: { type: Boolean, default: false },
    savingEmploymentDocument: { type: Boolean, default: false },
    uploadingCisAttachment: { type: Boolean, default: false },
    uploadingEmploymentAttachment: { type: Boolean, default: false },
    deletingMedicalRecordId: { type: [Number, String], default: null },
    deletingCisDocumentId: { type: [Number, String], default: null },
    deletingEmploymentDocumentId: { type: [Number, String], default: null },
    employmentDocumentFormLabel: { type: String, default: '' },
    userPermissionCatalog: { type: Array, default: () => [] },
    userAssignedPermissionCodes: { type: Array, default: () => [] },
    userPermissions: { type: Array, default: () => [] },
    userPermissionsLoading: { type: Boolean, default: false },
    userPermissionCatalogLoading: { type: Boolean, default: false },
    userPermissionPendingMap: { type: Object, default: () => ({}) },
    payrollAdjustmentTypeOptions: { type: Array, default: () => [] },
    payrollRestaurantOptions: { type: Array, default: () => [] },
    payrollAdjustments: { type: Array, default: () => [] },
    payrollAdjustmentsLoading: { type: Boolean, default: false },
    editingPayrollAdjustment: { type: Object, default: () => ({}) },
    updatingPayrollAdjustment: { type: Boolean, default: false },
    deletingPayrollAdjustmentId: { type: [Number, String], default: null },
    payrollAdjustmentTypes: { type: Array, default: () => [] },
    payrollAdjustmentTypesLoading: { type: Boolean, default: false },
    responsibleOptions: { type: Array, default: () => [] },
    photoUrl: { type: String, default: '' },
    uploadingPhoto: { type: Boolean, default: false },
    deleteFromIiko: { type: Boolean, default: false },
    canViewSensitiveStaffFields: { type: Boolean, default: false },
    canSyncEmployeeToIiko: { type: Boolean, default: false },
    syncingEmployeeToIiko: { type: Boolean, default: false },
    employeeChangeEvents: { type: Array, default: () => [] },
    employeeChangeEventsLoading: { type: Boolean, default: false },
    employeeChangeEventsLoadingMore: { type: Boolean, default: false },
    employeeChangeEventsError: { type: String, default: '' },
    employeeChangeEventsHasMore: { type: Boolean, default: false },
    canViewEmployeeChanges: { type: Boolean, default: false },
    canRestoreEmployees: { type: Boolean, default: false },
    restoringEmployee: { type: Boolean, default: false },
});

const emit = defineEmits([
    'close',
    'update:activeTab',
    'toggle-edit-mode',
    'delete-employee',
    'restore-employee',
    'load-attendances',
    'create-attendance',
    'update:attendanceDateFrom',
    'update:attendanceDateTo',
    'recalculate-night-minutes',
    'open-attendance',
    'open-payroll-adjustment-form',
    'start-edit-payroll-adjustment',
    'cancel-edit-payroll-adjustment',
    'update-payroll-adjustment',
    'delete-payroll-adjustment',
    'open-training-assignment',
    'start-edit-training',
    'cancel-edit-training',
    'update-training',
    'update-edit-training-field',
    'delete-training',
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
    'upload-photo',
    'toggle-user-permission',
    'update:delete-from-iiko',
    'sync-employee-to-iiko',
    'load-more-employee-change-events',
]);

const {
    isOpen,
    activeEmployee,
    activeTab,
    canManageEmployees,
    cardLoading,
    isEditMode,
    deletingEmployee,
    employeeCard,
    formatFullName,
    formatGender,
    formatAmount,
    formatDate,
    formatResponsible,
    formatRestaurant,
    canManageUserPermissions,
    attendanceSummary,
    employeeAttendances,
    reversedAttendances,
    attendancesLoading,
    attendanceDateFrom,
    attendanceDateTo,
    recalculatingNightMinutes,
    canViewTrainings,
    canManageTrainings,
    employeeTrainings,
    trainingsLoading,
    trainingTypeOptions,
    trainingTypesLoading,
    creatingTrainingRecord,
    editingTrainingRecord,
    updatingTrainingRecord,
    deletingTrainingRecordId,
    canViewDocuments,
    canViewMedicalChecks,
    canViewCisDocuments,
    medicalCheckRecords,
    cisDocumentRecords,
    employmentDocumentRecords,
    medicalCheckTypeOptions,
    cisDocumentTypeOptions,
    documentsLoading,
    canManageMedicalChecks,
    canManageCisDocuments,
    canManageDocuments,
    medicalForm,
    cisDocumentForm,
    employmentDocumentForm,
    isMedicalBulkMode,
    isMedicalFormOpen,
    isCisFormOpen,
    isEmploymentFormOpen,
    savingMedicalRecord,
    savingCisDocument,
    savingEmploymentDocument,
    uploadingCisAttachment,
    uploadingEmploymentAttachment,
    deletingMedicalRecordId,
    deletingCisDocumentId,
    deletingEmploymentDocumentId,
    employmentDocumentFormLabel,
    payrollAdjustmentTypeOptions,
    payrollRestaurantOptions,
    payrollAdjustmentTypes,
    payrollAdjustmentTypesLoading,
    payrollAdjustments,
    payrollAdjustmentsLoading,
    editingPayrollAdjustment,
    updatingPayrollAdjustment,
    deletingPayrollAdjustmentId,
    responsibleOptions,
    photoUrl,
    uploadingPhoto,
    userPermissionCatalog,
    userAssignedPermissionCodes,
    userPermissionsLoading,
    userPermissionCatalogLoading,
    userPermissionPendingMap,
    canViewSensitiveStaffFields,
    canSyncEmployeeToIiko,
    syncingEmployeeToIiko,
    employeeChangeEvents,
    employeeChangeEventsLoading,
    employeeChangeEventsLoadingMore,
    employeeChangeEventsError,
    employeeChangeEventsHasMore,
    canViewEmployeeChanges,
    canRestoreEmployees,
    restoringEmployee,
} = toRefs(props);

const showCisDocuments = computed(() => {
    const cardFlag = employeeCard.value?.is_cis_employee;
    if (cardFlag !== undefined && cardFlag !== null) {
        return Boolean(cardFlag);
    }
    const activeFlag = activeEmployee.value?.is_cis_employee;
    return Boolean(activeFlag);
});

const showFormalizedDocuments = computed(() => {
    const cardFlag = employeeCard.value?.is_formalized;
    if (cardFlag !== undefined && cardFlag !== null) {
        return Boolean(cardFlag);
    }
    const activeFlag =
        activeEmployee.value?.is_formalized ??
        activeEmployee.value?.isFormalized ??
        activeEmployee.value?.formalized;
    return Boolean(activeFlag);
});

const fileInput = ref(null);
const photoCardRef = ref(null);
const isPhotoPreviewOpen = ref(false);
const modalTabsRef = ref(null);
const modalTabRefs = ref({});
const tabIndicatorState = ref({
    x: 0,
    y: 0,
    width: 0,
    height: 0,
    visible: false,
});
let tabsResizeObserver = null;

const tabsIndicatorStyle = computed(() => ({
    '--tab-indicator-x': `${tabIndicatorState.value.x}px`,
    '--tab-indicator-y': `${tabIndicatorState.value.y}px`,
    '--tab-indicator-width': `${tabIndicatorState.value.width}px`,
    '--tab-indicator-height': `${tabIndicatorState.value.height}px`,
    opacity: tabIndicatorState.value.visible ? '1' : '0',
}));
const payrollFilter = ref('all');
const attendanceViewMode = ref('all');
const attendanceRestaurantFilterValue = ref('all');

function attendanceRestaurantKey(attendance) {
    const rawId = attendance?.restaurant_id;
    if (rawId === null || rawId === undefined || rawId === '') {
        return 'none';
    }
    const parsed = Number(rawId);
    if (Number.isFinite(parsed)) {
        return `id:${parsed}`;
    }
    return `id:${String(rawId)}`;
}

const attendanceShiftRestaurantOptions = computed(() => {
    const items = Array.isArray(employeeAttendances.value?.items) ? employeeAttendances.value.items : [];
    const byKey = new Map();

    for (const attendance of items) {
        const key = attendanceRestaurantKey(attendance);
        if (byKey.has(key)) {
            continue;
        }
        if (key === 'none') {
            byKey.set(key, {
                value: key,
                label: 'Без ресторана',
                sortKey: 'яяяяяяяя',
            });
            continue;
        }
        const parsedId = Number(attendance?.restaurant_id);
        const label = attendance?.restaurant_name
            ? normalizeMojibakeText(attendance.restaurant_name)
            : Number.isFinite(parsedId)
            ? `ID ${parsedId}`
            : '—';
        byKey.set(key, {
            value: key,
            label,
            sortKey: label.toLocaleLowerCase('ru-RU'),
        });
    }

    const dynamic = Array.from(byKey.values())
        .sort((a, b) => a.sortKey.localeCompare(b.sortKey, 'ru-RU'))
        .map(({ value, label }) => ({ value, label }));

    return [
        { value: 'all', label: 'Все рестораны' },
        ...dynamic,
    ];
});

watch(
    attendanceShiftRestaurantOptions,
    (options) => {
        const hasCurrent = (options || []).some((option) => option.value === attendanceRestaurantFilterValue.value);
        if (!hasCurrent) {
            attendanceRestaurantFilterValue.value = 'all';
        }
    },
    { immediate: true },
);

watch(isOpen, (opened) => {
    if (!opened) {
        attendanceViewMode.value = 'all';
        attendanceRestaurantFilterValue.value = 'all';
    }
});

const filteredAttendances = computed(() => {
    const items = Array.isArray(reversedAttendances.value) ? reversedAttendances.value : [];
    if (attendanceViewMode.value !== 'by_restaurant') {
        return items;
    }
    if (attendanceRestaurantFilterValue.value === 'all') {
        return items;
    }
    return items.filter((attendance) => attendanceRestaurantKey(attendance) === attendanceRestaurantFilterValue.value);
});

const filteredAttendanceSummary = computed(() => {
    const items = filteredAttendances.value;
    if (!items.length) {
        return null;
    }
    let totalMinutes = 0;
    let nightMinutes = 0;
    for (const attendance of items) {
        const totalValue = Number(attendance?.duration_minutes);
        const nightValue = Number(attendance?.night_minutes);
        if (Number.isFinite(totalValue)) {
            totalMinutes += totalValue;
        }
        if (Number.isFinite(nightValue)) {
            nightMinutes += nightValue;
        }
    }
    return {
        shiftCount: items.length,
        totalDuration: formatDurationMinutes(totalMinutes),
        nightDuration: formatDurationMinutes(nightMinutes),
    };
});

const effectiveAttendanceSummary = computed(() => {
    if (attendanceViewMode.value === 'all') {
        return attendanceSummary.value || filteredAttendanceSummary.value;
    }
    return filteredAttendanceSummary.value;
});

const canTriggerPhotoSelect = computed(() =>
    canManageEmployees.value && !uploadingPhoto.value,
);
const canOpenPhotoPreview = computed(() => Boolean(photoUrl.value));
const isPhotoClickable = computed(() =>
    !uploadingPhoto.value && (canOpenPhotoPreview.value || canTriggerPhotoSelect.value),
);

function setModalTabRef(tabKey) {
    return (element) => {
        if (element) {
            modalTabRefs.value[tabKey] = element;
            return;
        }
        delete modalTabRefs.value[tabKey];
    };
}

function updateTabIndicator() {
    const tabsRoot = modalTabsRef.value;
    const activeTabButton = modalTabRefs.value[activeTab.value];
    if (!tabsRoot || !activeTabButton) {
        tabIndicatorState.value.visible = false;
        return;
    }

    let x = 0;
    let y = 0;
    let node = activeTabButton;

    while (node && node !== tabsRoot) {
        x += node.offsetLeft || 0;
        y += node.offsetTop || 0;
        node = node.offsetParent;
    }

    if (node !== tabsRoot) {
        const tabsRect = tabsRoot.getBoundingClientRect();
        const tabRect = activeTabButton.getBoundingClientRect();
        x = tabRect.left - tabsRect.left;
        y = tabRect.top - tabsRect.top;
    }

    tabIndicatorState.value = {
        x,
        y,
        width: activeTabButton.offsetWidth || 0,
        height: activeTabButton.offsetHeight || 0,
        visible: true,
    };
}

function scheduleTabIndicatorUpdate() {
    nextTick(() => {
        updateTabIndicator();
    });
}

const photoActionLabel = computed(() => {
    if (photoUrl.value) {
        return 'Открыть фото сотрудника';
    }
    if (canManageEmployees.value) {
        return 'Добавить фото сотрудника';
    }
    return 'Фото сотрудника';
});

function triggerFileSelect() {
    fileInput.value?.click();
}

function resetPhotoCardTheme() {
    const node = photoCardRef.value;
    if (!node) {
        return;
    }
    node.style.removeProperty('--photo-card-top');
    node.style.removeProperty('--photo-card-bottom');
}

function handlePhotoLoaded() {
    const node = photoCardRef.value;
    if (!node) {
        return;
    }
    try {
        node.style.setProperty('--photo-card-top', 'var(--color-surface)');
        node.style.setProperty('--photo-card-bottom', 'var(--color-surface-200)');
    } catch {
        resetPhotoCardTheme();
    }
}

function handlePhotoClick() {
    if (!isPhotoClickable.value) {
        return;
    }
    if (canOpenPhotoPreview.value) {
        isPhotoPreviewOpen.value = true;
        return;
    }
    if (!canTriggerPhotoSelect.value) {
        return;
    }
    triggerFileSelect();
}

function handlePhotoKeydown(event) {
    if (!isPhotoClickable.value) {
        return;
    }
    const key = event?.key;
    if (key !== 'Enter' && key !== ' ' && key !== 'Spacebar' && key !== 'Space') {
        return;
    }
    if (canOpenPhotoPreview.value) {
        event.preventDefault();
        isPhotoPreviewOpen.value = true;
        return;
    }
    if (!canTriggerPhotoSelect.value) {
        return;
    }
    event.preventDefault();
    triggerFileSelect();
}

function closePhotoPreview() {
    isPhotoPreviewOpen.value = false;
}

function onPhotoSelected(event) {
    const [file] = event?.target?.files || [];
    if (file) {
        emit('upload-photo', file);
    }
    if (event?.target) {
        event.target.value = '';
    }
}

watch(
    [
        activeTab,
        isOpen,
        canManageUserPermissions,
        canViewDocuments,
        canViewEmployeeChanges,
    ],
    () => {
        scheduleTabIndicatorUpdate();
    },
);

watch(
    () => isOpen.value,
    (open) => {
        if (!open) {
            isPhotoPreviewOpen.value = false;
        }
    },
);

watch(
    () => photoUrl.value,
    (value) => {
        if (!value) {
            isPhotoPreviewOpen.value = false;
        }
    },
);

watch(
    () => modalTabsRef.value,
    (node, prevNode) => {
        if (tabsResizeObserver && prevNode) {
            tabsResizeObserver.unobserve(prevNode);
        }
        if (tabsResizeObserver && node) {
            tabsResizeObserver.observe(node);
        }
        scheduleTabIndicatorUpdate();
    },
);

onMounted(() => {
    if (typeof ResizeObserver !== 'undefined') {
        tabsResizeObserver = new ResizeObserver(() => {
            updateTabIndicator();
        });
        if (modalTabsRef.value) {
            tabsResizeObserver.observe(modalTabsRef.value);
        }
    }
    window.addEventListener('resize', scheduleTabIndicatorUpdate);
    scheduleTabIndicatorUpdate();
});

onBeforeUnmount(() => {
    if (tabsResizeObserver) {
        tabsResizeObserver.disconnect();
        tabsResizeObserver = null;
    }
    window.removeEventListener('resize', scheduleTabIndicatorUpdate);
});

watch(
    () => photoUrl.value,
    (value) => {
        if (!value) {
            resetPhotoCardTheme();
        }
    },
);

const statusLabel = computed(() => {
    if (!canViewSensitiveStaffFields.value) {
        return '';
    }
    const fired = employeeCard.value?.fired ?? activeEmployee.value?.fired;
    if (fired === undefined || fired === null) {
        return '';
    }
    return fired ? 'Уволен' : 'Активен';
});

const statusClass = computed(() => {
    if (!statusLabel.value) {
        return '';
    }
    return employeeCard.value?.fired ?? activeEmployee.value?.fired
        ? 'employees-page__status-badge--fired'
        : 'employees-page__status-badge--active';
});

const rateHidden = computed(() => {
    const cardHidden = employeeCard.value?.rate_hidden;
    if (cardHidden !== undefined && cardHidden !== null) {
        return Boolean(cardHidden);
    }
    return Boolean(activeEmployee.value?.rate_hidden);
});

const isTimeControlRole = computed(() => {
    const roleId = employeeCard.value?.role_id ?? activeEmployee.value?.role_id;
    const roleIdNumber = Number(roleId);
    if (Number.isFinite(roleIdNumber) && roleIdNumber === 10) {
        return true;
    }
    const roleName = employeeCard.value?.role_name ?? activeEmployee.value?.role_name ?? '';
    if (!roleName) {
        return false;
    }
    const normalized = roleName.toString().trim().toLowerCase().replace(/[\s_-]+/g, '');
    return normalized === 'таймконтроль' || normalized === 'timecontrol';
});

const positionSummary = computed(() => {
    const position = employeeCard.value?.position_name || activeEmployee.value?.position_name;

    return [position].filter(Boolean).join('');
});

const employeeInitials = computed(() => {
    const info = employeeCard.value || activeEmployee.value;
    if (!info) {
        return '—';
    }
    const last = info.last_name ?? info.lastName ?? '';
    const first = info.first_name ?? info.firstName ?? '';
    let initials = `${String(last).trim().charAt(0)}${String(first).trim().charAt(0)}`.trim();
    if (!initials) {
        const fullName = formatFullName.value ? formatFullName.value(info) : '';
        const parts = String(fullName || '')
            .trim()
            .split(/\s+/)
            .filter(Boolean);
        if (parts.length) {
            initials = `${parts[0].charAt(0)}${parts[1]?.charAt(0) || ''}`.trim();
        }
    }
    return initials ? initials.toUpperCase() : '—';
});

const sourceLabels = {
    system: 'Система',
    manual: 'Вручную',
    import: 'Импорт',
    sync: 'Синхронизация',
    api: 'API',
};

const normalizeText = normalizeMojibakeText;

function formatChangeAuthor(event) {
    if (event?.changed_by_name) {
        return normalizeText(event.changed_by_name);
    }
    if (event?.changed_by_id) {
        return `ID ${event.changed_by_id}`;
    }
    if (event?.source) {
        const mapped = sourceLabels[event.source] || event.source;
        return normalizeText(mapped);
    }
    return '-';
}

function formatChangeComment(value) {
    if (!value) {
        return '-';
    }
    return normalizeText(String(value));
}

function formatChangeDate(value) {
    if (!value) {
        return '-';
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return String(value);
    }
    return parsed.toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function formatAttendanceRestaurant(attendance) {
    if (!attendance) {
        return '-';
    }
    if (attendance.restaurant_name) {
        return normalizeText(attendance.restaurant_name);
    }
    if (attendance.restaurant_id) {
        return `ID ${attendance.restaurant_id}`;
    }
    return '—';
}

function formatDurationMinutes(value) {
    if (value === null || value === undefined || value === '') {
        return '—';
    }
    const minutes = Number(value);
    if (!Number.isFinite(minutes)) {
        return '—';
    }
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours && mins) {
        return `${hours} ч ${mins} мин`;
    }
    if (hours) {
        return `${hours} ч`;
    }
    return `${mins} мин`;
}

</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/employees-modal' as *;
</style>
