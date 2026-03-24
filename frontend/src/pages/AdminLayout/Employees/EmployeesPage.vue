<template>
    <div class="employees-page">
        <div v-if="canViewEmployees" class="employees-page__content">
            <div v-if="!modalOnly" class="employees-page__content-body">
                <header class="employees-page__header">
                <div>
                    <h1 class="employees-page__title">Сотрудники</h1>
                </div>
                <div class="employees-page__header-actions">
                    <div v-if="canDownloadEmployeesList || canBulkPayrollAdjust || canExportTimesheet" class="employees-page__toolbar">
                        <Button
                            v-if="canDownloadEmployeesList"
                            color="secondary"
                            size="sm"
                            :loading="employeesListExporting"
                            :disabled="employeesListExporting"
                            @click="downloadEmployeesList"
                        >
                            Скачать список сотрудников
                        </Button>
                        <Button
                            v-if="canBulkPayrollAdjust"
                            color="secondary"
                            size="sm"
                            @click="openBulkAdjustModal"
                        >
                            Массовое начисление/удержание
                        </Button>
                        <Button v-if="canExportTimesheet" color="secondary" size="sm" @click="openTimesheetExportModal">
                            Табель смен
                        </Button>
                    </div>
                    <Button
                        v-if="canCreateEmployees"
                        color="primary"
                        size="sm"
                        @click="openCreateModal"
                    >
                        Создать сотрудника
                    </Button>
                </div>
            </header>
            <div class="employees-page__filters-panel">
                <button
                    class="employees-page__filters-toggle"
                    type="button"
                    @click="toggleFilters"
                >
                    Фильтры
                    <span :class="['employees-page__filters-icon', { 'is-open': isFiltersOpen }]">▼</span>
                </button>
                <div v-if="isFiltersOpen" class="employees-page__filters-content">
                    <div class="employees-page__filters-controls">
                        <Input
                            :model-value="search"
                            class="employees-page__search"
                            placeholder="Поиск по ФИО, логину или коду"
                            @update:model-value="handleSearchChange"
                        />
                        <div class="employees-page__filters-checkboxes">
                            <Checkbox
                                :model-value="onlyFired"
                                label="Только уволенных"
                                @update:model-value="handleOnlyFiredChange"
                            />
                            <Checkbox
                                :model-value="onlyFormalized"
                                label="Официально оформлен"
                                @update:model-value="handleOnlyFormalizedChange"
                            />
                            <Checkbox
                                :model-value="onlyNotFormalized"
                                label="Не оформлен"
                                @update:model-value="handleOnlyNotFormalizedChange"
                            />
                            <Checkbox
                                :model-value="onlyCis"
                                label="Сотрудник СНГ"
                                @update:model-value="handleOnlyCisChange"
                            />
                            <Checkbox
                                :model-value="onlyNotCis"
                                label="Не СНГ"
                                @update:model-value="handleOnlyNotCisChange"
                            />
                        </div>
                        <Button color="ghost" size="sm" :loading="isLoading" @click="loadEmployees">
                            Найти
                        </Button>
                    </div>
                    <Divider />
                    <div class="employees-page__filters">
                        <div v-if="restaurantOptions.length" class="employees-page__filter-control">
                            <Select
                                v-model="selectedRestaurantFilter"
                                label="Фильтр по ресторанам"
                                :options="restaurantFilterOptions"
                                placeholder="Все рестораны"
                            />
                        </div>
                        <div
                            v-if="positionOptions.length"
                            class="employees-page__filter-control employees-page__filter-control--positions"
                        >
                            <Input
                                v-model="positionFilterQuery"
                                label="Фильтр по должностям"
                                placeholder="Начните вводить"
                            />
                            <div class="employees-page__filter-options employees-page__filter-options--scroll">
                                <Checkbox
                                    v-for="position in filteredPositionOptions"
                                    :key="position.value"
                                    :label="position.label"
                                    :model-value="selectedPositionFilters.includes(position.value)"
                                    @update:model-value="(checked) => togglePositionFilter(position.value, checked)"
                                />
                                <p
                                    v-if="!filteredPositionOptions.length && !positionFilterQuery"
                                    class="employees-page__filter-empty"
                                >
                                    Введите начало должности
                                </p>
                                <p
                                    v-else-if="positionFilterQuery && !filteredPositionOptions.length"
                                    class="employees-page__filter-empty"
                                >
                                    Ничего не найдено
                                </p>
                            </div>
                        </div>
                    </div>
                    <Divider />
                    <div class="employees-page__filters">
                        <div class="employees-page__filter-control employees-page__filter-control--date-range">
                            <p class="employees-page__filter-title">Дата найма</p>
                            <div class="employees-page__filter-range">
                                <div class="employees-page__filter-range-date">
                                    от <DateInput v-model="hireDateFrom" />
                                </div>
                                <div class="employees-page__filter-range-date">
                                    до <DateInput v-model="hireDateTo" />
                                </div>
                            </div>
                        </div>
                        <div class="employees-page__filter-control employees-page__filter-control--date-range">
                            <p class="employees-page__filter-title">Дата увольнения</p>
                            <div class="employees-page__filter-range">
                                <div class="employees-page__filter-range-date">
                                    от <DateInput v-model="fireDateFrom" />
                                </div>
                                <div class="employees-page__filter-range-date">
                                    до <DateInput v-model="fireDateTo" />
                                </div>
                            </div>
                        </div>
                    </div>
                    <Divider />
                    <div class="employees-page__column-selector">
                        <button
                            class="employees-page__column-selector-toggle"
                            type="button"
                            @click="toggleColumnSelector"
                        >
                            Колонки в таблице
                            <span :class="['employees-page__column-selector-icon', { 'is-open': isColumnSelectorOpen }]">▼</span>
                        </button>
                        <div v-if="isColumnSelectorOpen" class="employees-page__column-selector-grid">
                            <Checkbox
                                v-for="column in employeeColumnOptions"
                                :key="column.id"
                                :label="column.label"
                                :model-value="selectedEmployeeColumns.includes(column.id)"
                                @update:model-value="(checked) => handleEmployeeColumnChange(column.id, checked)"
                            />
                        </div>
                    </div>
                </div>
            </div>
            <EmployeesTable
                :employees="sortedEmployees"
                :is-loading="isLoading"
                :format-full-name="formatFullNameShort"
                :format-date="formatDate"
                :format-gender="formatGender"
                :sort-by="sortBy"
                :sort-direction="sortDirection"
                :visible-columns="selectedEmployeeColumns"
                :column-options="employeeColumnOptions"
                @select="openEmployeeModal"
                @update:sort-by="handleSortByChange"
                @update:sort-direction="handleSortDirectionChange"
            />
            </div>

            <EmployeeModal
                v-if="isEmployeeModalOpen"
                :is-open="isEmployeeModalOpen"
                :active-tab="activeModalTab"
                :active-employee="activeEmployee"
                :can-manage-employees="canManageEmployees"
                :can-view-sensitive-staff-fields="canViewSensitiveStaffFields"
                :can-sync-employee-to-iiko="canSyncEmployeeToIiko"
                :card-loading="cardLoading"
                :is-edit-mode="isEditMode"
                :deleting-employee="deletingEmployee"
                :restoring-employee="restoringEmployee"
                :syncing-employee-to-iiko="isIikoSyncActionLoading"
                :employee-card="employeeCard"
                :employee-change-events="employeeChangeEvents"
                :employee-change-events-loading="employeeChangeEventsLoading"
                :employee-change-events-error="employeeChangeEventsError"
                :can-view-employee-changes="canViewEmployeeChanges"
                :can-restore-employees="canRestoreEmployees"
                :format-full-name="formatFullName"
                :format-gender="formatGender"
                :format-amount="formatAmount"
                :format-date="formatDate"
                :format-responsible="formatResponsible"
                :can-manage-user-permissions="canManageUserPermissions"
                :user-permission-catalog="userPermissionCatalogRows"
                :user-permissions="userPermissions"
                :user-assigned-permission-codes="userAssignedPermissionCodes"
                :user-permissions-loading="userPermissionsLoading"
                :user-permission-catalog-loading="userPermissionCatalogLoading"
                :user-permission-pending-map="userPermissionUpdating"
                :photo-url="employeePhotoUrl"
                :uploading-photo="uploadingPhoto"
                :attendance-summary="attendanceSummary"
                :employee-attendances="employeeAttendances"
                :reversed-attendances="reversedAttendances"
                :attendances-loading="attendancesLoading"
                :attendance-date-from="attendanceDateFrom"
                :attendance-date-to="attendanceDateTo"
                :recalculating-night-minutes="recalculatingNightMinutes"
                :employee-trainings="employeeTrainings"
                :trainings-loading="trainingsLoading"
                :training-type-options="trainingTypeOptions"
                :training-types-loading="trainingTypesLoading"
                :creating-training-record="creatingTrainingRecord"
                :editing-training-record="editingTrainingRecord"
                :updating-training-record="updatingTrainingRecord"
                :deleting-training-record-id="deletingTrainingRecordId"
                :training-requirements="trainingRequirementSuggestions"
                :training-requirements-loading="trainingRequirementsLoading"
                :updating-training-requirement-id="updatingTrainingRequirementId"
                :can-view-documents="canViewDocuments"
                :can-view-medical-checks="canViewMedicalChecks"
                :can-view-cis-documents="canViewCisDocuments"
                :medical-check-records="medicalCheckRecords"
                :cis-document-records="cisDocumentRecords"
                :employment-document-records="employmentDocumentRows"
                :medical-check-type-options="medicalCheckTypeOptions"
                :cis-document-type-options="cisDocumentTypeOptions"
                :documents-loading="documentsLoading"
                :can-manage-medical-checks="canManageMedicalChecks"
                :can-manage-cis-documents="canManageCisDocuments"
                :can-manage-documents="canManageDocuments"
                :medical-form="medicalForm"
                :cis-document-form="cisDocumentForm"
                :employment-document-form="employmentDocumentForm"
                :is-medical-bulk-mode="isMedicalBulkMode"
                :is-medical-form-open="isMedicalFormOpen"
                :is-cis-form-open="isCisFormOpen"
                :is-employment-form-open="isEmploymentFormOpen"
                :saving-medical-record="savingMedicalRecord"
                :saving-cis-document="savingCisDocument"
                :saving-employment-document="savingEmploymentDocument"
                :uploading-cis-attachment="uploadingCisAttachment"
                :uploading-employment-attachment="uploadingEmploymentAttachment"
                :deleting-medical-record-id="deletingMedicalRecordId"
                :deleting-cis-document-id="deletingCisDocumentId"
                :deleting-employment-document-id="deletingEmploymentDocumentId"
                :employment-document-form-label="employmentDocumentFormLabel"
                :payroll-adjustment-type-options="payrollAdjustmentTypeOptions"
                :payroll-adjustments="payrollAdjustments"
                :payroll-adjustments-loading="payrollAdjustmentsLoading"
                :editing-payroll-adjustment="editingPayrollAdjustment"
                :updating-payroll-adjustment="updatingPayrollAdjustment"
                :deleting-payroll-adjustment-id="deletingPayrollAdjustmentId"
                :payroll-adjustment-types="payrollAdjustmentTypes"
                :payroll-adjustment-types-loading="payrollAdjustmentTypesLoading"
                :payroll-restaurant-options="payrollRestaurantOptions"
                :responsible-options="responsibleOptions"
                :format-restaurant="formatRestaurant"
                @close="closeEmployeeModal"
                @toggle-edit-mode="toggleEditMode"
                @delete-employee="handleDeleteEmployee"
                @restore-employee="handleRestoreEmployee"
                @sync-employee-to-iiko="handleSyncEmployeeToIiko"
                @load-attendances="loadEmployeeAttendances"
                @recalculate-night-minutes="handleRecalculateNightMinutes"
                @open-attendance="openAttendanceEditModal"
                @create-attendance="openAttendanceCreateModal"
                @open-payroll-adjustment-form="openPayrollAdjustmentForm"
                @start-edit-payroll-adjustment="startEditPayrollAdjustment"
                @cancel-edit-payroll-adjustment="cancelEditPayrollAdjustment"
                @update-payroll-adjustment="handleUpdatePayrollAdjustment"
                @delete-payroll-adjustment="handleDeletePayrollAdjustment"
                @open-training-assignment="openTrainingAssignmentModal"
                @start-edit-training="startEditTrainingRecord"
                @cancel-edit-training="cancelEditTrainingRecord"
                @update-training="handleUpdateTrainingRecord"
                @update-edit-training-field="handleEditTrainingRecordField"
                @delete-training="handleDeleteTrainingRecord"
                @toggle-training-requirement="toggleTrainingRequirement"
                @start-create-medical="startCreateMedicalRecord"
                @start-create-medical-bulk="startCreateMedicalRecordsBulk"
                @start-edit-medical="startEditMedicalRecord"
                @cancel-medical-form="cancelMedicalForm"
                @submit-medical-form="handleSaveMedicalRecord"
                @delete-medical-record="handleDeleteMedicalRecord"
                @start-create-cis-document="startCreateCisDocument"
                @start-edit-cis-document="startEditCisDocument"
                @cancel-cis-document-form="cancelCisDocumentForm"
                @submit-cis-document-form="handleSaveCisDocument"
                @delete-cis-document="handleDeleteCisDocument"
                @upload-cis-attachment="handleUploadCisAttachment"
                @start-edit-employment-document="startEditEmploymentDocument"
                @cancel-employment-document-form="cancelEmploymentDocumentForm"
                @submit-employment-document-form="handleSaveEmploymentDocument"
                @delete-employment-document="handleDeleteEmploymentDocument"
                @upload-employment-attachment="handleUploadEmploymentAttachment"
                @upload-photo="handleUploadEmployeePhoto"
                @toggle-user-permission="handleToggleUserPermission"
                @update:active-tab="handleActiveTabChange"
                @update:attendance-date-from="handleAttendanceDateFromChange"
                @update:attendance-date-to="handleAttendanceDateToChange"
            />

            <EmployeeEditModal
                v-if="isEditMode"
                :is-open="isEditMode"
                :employee-edit-form="employeeEditForm"
                :gender-options="genderOptions"
                :company-options="companyOptions"
                :role-options="roleOptions"
                :position-options="positionOptions"
                :workplace-restaurant-options="workplaceRestaurantOptions"
                :restaurants="restaurants"
                :can-edit-full-access="canEditFullAccess"
                :can-edit-roles="canEditRoles"
                :can-edit-rates="canEditRates"
                :can-edit-iiko-id="canEditIikoId"
                :can-view-sensitive-staff-fields="canViewSensitiveStaffFields"
                :updating-employee="updatingEmployee"
                :edit-context-loading="editContextLoading"
                :format-full-name="formatFullName"
                :employee-card="employeeCard"
                @close="cancelEditMode"
                @update-employee="handleUpdateEmployee"
                @upload-photo="handleUploadEmployeePhoto"
                @toggle-edit-restaurant="toggleEditRestaurant"
            />

            <Modal
                v-if="isDeleteCommentModalOpen"
                class="employees-page__comment-modal"
                @close="closeDeleteCommentModal"
            >
                <template #header>Комментарий к увольнению</template>
                <div class="employees-page__comment-modal-body">
                    <p class="employees-page__comment-modal-hint">
                        Укажите причину увольнения. Запись попадет в журнал изменений.
                    </p>
                    <div class="input">
                        <label class="input-label">Комментарий</label>
                        <textarea
                            v-model="deleteCommentText"
                            class="input-field employees-page__comment-textarea"
                            rows="4"
                            placeholder="Например: уволен по собственному желанию"
                        />
                    </div>
                    <p
                        v-if="deleteFromIikoPending"
                        class="employees-page__comment-modal-hint"
                    >
                        Также будет выполнено увольнение в iiko.
                    </p>
                </div>
                <template #footer>
                    <Button
                        color="ghost"
                        :disabled="deletingEmployee"
                        @click="closeDeleteCommentModal"
                    >
                        Отмена
                    </Button>
                    <Button
                        color="danger"
                        :loading="deletingEmployee"
                        @click="submitDeleteEmployee"
                    >
                        Уволить
                    </Button>
                </template>
            </Modal>

            <Modal
                v-if="isDuplicateInfoModalOpen"
                class="employees-page__duplicate-modal"
                @close="closeDuplicateInfoModal"
            >
                <template #header>Сотрудник уже существует</template>
                <div class="employees-page__duplicate-modal-body">
                    <div class="employees-page__duplicate-photo">
                        <img
                            v-if="duplicateEmployeeInfo?.photo_url"
                            :src="duplicateEmployeeInfo.photo_url"
                            alt="Фото сотрудника"
                        />
                        <div v-else class="employees-page__duplicate-photo-placeholder">
                            {{ duplicateEmployeeInitials }}
                        </div>
                    </div>
                    <div class="employees-page__duplicate-details">
                        <p class="employees-page__duplicate-name">{{ duplicateEmployeeFullName }}</p>
                        <dl class="employees-page__duplicate-list">
                            <div class="employees-page__duplicate-item">
                                <dt>Дата рождения</dt>
                                <dd>{{ formatDate(duplicateEmployeeInfo?.birth_date) }}</dd>
                            </div>
                            <div class="employees-page__duplicate-item">
                                <dt>Место работы</dt>
                                <dd>{{ duplicateEmployeeInfo?.workplace || '—' }}</dd>
                            </div>
                            <div class="employees-page__duplicate-item">
                                <dt>Должность</dt>
                                <dd>{{ duplicateEmployeeInfo?.position || '—' }}</dd>
                            </div>
                            <div class="employees-page__duplicate-item">
                                <dt>Статус</dt>
                                <dd>
                                    {{
                                        duplicateEmployeeInfo?.fired === true
                                            ? 'Уволен'
                                            : duplicateEmployeeInfo?.fired === false
                                            ? 'Работает'
                                            : '—'
                                    }}
                                </dd>
                            </div>
                            <div
                                v-if="duplicateEmployeeInfo?.fired && duplicateEmployeeInfo?.fired_comment"
                                class="employees-page__duplicate-item employees-page__duplicate-item--full"
                            >
                                <dt>Комментарий к увольнению</dt>
                                <dd>{{ duplicateEmployeeInfo.fired_comment }}</dd>
                            </div>
                        </dl>
                    </div>
                </div>
                <template #footer>
                    <Button color="primary" @click="closeDuplicateInfoModal">Понятно</Button>
                </template>
            </Modal>

            <TrainingAssignmentModal
                v-if="isTrainingAssignmentModalOpen"
                :is-open="isTrainingAssignmentModalOpen"
                :training-form="trainingForm"
                :training-type-options="trainingTypeOptions"
                :training-types-loading="trainingTypesLoading"
                :creating-training-record="creatingTrainingRecord"
                @close="closeTrainingAssignmentModal"
                @assign-training="handleCreateTrainingRecord"
            />

            <PayrollAdjustmentModal
                v-if="isPayrollAdjustmentFormVisible"
                :is-open="isPayrollAdjustmentFormVisible"
                :new-payroll-adjustment="newPayrollAdjustment"
                :payroll-adjustment-type-options="payrollAdjustmentTypeOptions"
                :payroll-adjustment-types="payrollAdjustmentTypes"
                :payroll-adjustment-types-loading="payrollAdjustmentTypesLoading"
                :payroll-restaurant-options="payrollRestaurantOptions"
                :creating-payroll-adjustment="creatingPayrollAdjustment"
                :responsible-options="responsibleOptions"
                @close="closePayrollAdjustmentForm"
                @create-payroll-adjustment="handleCreatePayrollAdjustment"
            />

            <Modal
                v-if="isPayrollExportModalOpen"
                class="employees-page__export-modal"
                @close="closePayrollExportModal"
            >
                <template #header>Выгрузка табеля</template>
                <template #default>
                    <form class="employees-page__export-form" @submit.prevent>
                        <DateInput
                            v-model="payrollExportForm.dateFrom"
                            label="Дата с"
                            required
                        />
                        <DateInput
                            v-model="payrollExportForm.dateTo"
                            label="Дата по"
                            required
                        />
                        <Select
                            v-model="payrollExportForm.companyId"
                            label="Компания"
                            :options="companyFilterOptions"
                        />
                        <Select
                            v-model="payrollExportForm.restaurantId"
                            label="Ресторан"
                            :options="restaurantFilterOptions"
                        />
                    <Select
                        v-model="payrollExportForm.userId"
                        label="Сотрудник"
                        :options="employeeFilterOptions"
                    />
                    <Input
                        v-model="payrollExportForm.salaryPercent"
                        label="Процент сотрудников на окладе"
                        type="number"
                        step="1"
                        min="0"
                        max="100"
                        placeholder="100"
                    />
                </form>
                </template>
                <template #footer>
                    <Button color="ghost" :disabled="payrollExporting" @click="closePayrollExportModal">
                        Закрыть
                    </Button>
                    <Button color="primary" :loading="payrollExporting" @click="handleExportPayroll">
                        Скачать
                    </Button>
                </template>
            </Modal>

            <Modal
                v-if="isBulkAdjustModalOpen"
                class="employees-page__export-mass-modal"
                @close="closeBulkAdjustModal"
            >
                <template #header>Массовое начисление/удержание</template>
                <template #default>
                    <form class="employees-page__export-mass-form" @submit.prevent>
                        <div class="employees-page__export-mass-settings employees-page__export-group">
                            <h4 class="employees-page__export-mass-title">Настройки операции</h4>
                            <div class="employees-page__export-mass-form-filter">
                                <Select
                                    v-model="bulkAdjustForm.restaurantId"
                                    label="Ресторан (опционально)"
                                    :options="restaurantFilterOptions"
                                />
                                <DateInput v-model="bulkAdjustForm.date" label="Дата операции" required />
                                <Select
                                    v-model="bulkAdjustForm.adjustmentTypeId"
                                    label="Тип (начисление/удержание)"
                                    :options="payrollAdjustmentTypeOptions"
                                    required
                                />
                                <Input v-model="bulkAdjustForm.comment" label="Комментарий" />
                            </div>
                            <div class="employees-page__bulk-common-amount">
                                <Checkbox v-model="bulkCommonAmountEnabled" label="Единая сумма" />
                                <Input
                                    v-model="bulkCommonAmount"
                                    label="Сумма всем"
                                    type="number"
                                    step="0.01"
                                    placeholder="0"
                                    :disabled="!bulkCommonAmountEnabled"
                                />
                            </div>
                        </div>
                        <div class="employees-page__bulk-toolbar employees-page__export-group">
                            <div class="employees-page__bulk-actions">
                                <Button size="sm" color="ghost" @click="openBulkFillModal">
                                    Заполнить список
                                </Button>
                            </div>
                        </div>
                        <div class="employees-page__bulk-table employees-page__export-group">
                            <table>
                                <thead>
                                    <tr>
                                        <th>
                                            <button class="employees-page__bulk-sort" type="button" @click="toggleBulkSort('name')">
                                                ФИО
                                            </button>
                                        </th>
                                        <th>
                                            <button class="employees-page__bulk-sort" type="button" @click="toggleBulkSort('position')">
                                                Должность
                                            </button>
                                        </th>
                                        <th>
                                            <button class="employees-page__bulk-sort" type="button" @click="toggleBulkSort('staff')">
                                                Табельный
                                            </button>
                                        </th>
                                        <th>
                                            <button class="employees-page__bulk-sort" type="button" @click="toggleBulkSort('subdivision')">
                                                Подразделение
                                            </button>
                                        </th>
                                        <th>
                                            <button class="employees-page__bulk-sort" type="button" @click="toggleBulkSort('amount')">
                                                Сумма
                                            </button>
                                        </th>
                                        <th>Вкл.</th>
                                        <th>Результат</th>
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-if="!bulkAdjustEmployees.length">
                                        <td colspan="8">Нет сотрудников. Заполните список или добавьте из поиска.</td>
                                    </tr>
                                    <tr v-for="row in bulkDisplayedEmployees" :key="row.userId">
                                        <td>{{ row.name }}</td>
                                        <td>{{ row.positionName || '-' }}</td>
                                        <td>{{ row.staffCode || '-' }}</td>
                                        <td>{{ row.subdivisionName || '-' }}</td>
                                        <td>
                                            <Input
                                                v-model="row.amount"
                                                type="number"
                                                step="0.01"
                                                placeholder="0"
                                                :disabled="bulkCommonAmountEnabled"
                                            />
                                        </td>
                                        <td class="employees-page__bulk-check">
                                            <Checkbox v-model="row.enabled" />
                                        </td>
                                        <td class="employees-page__bulk-result-cell">
                                            <span
                                                v-if="row.resultStatus"
                                                class="employees-page__bulk-status"
                                                :class="`is-${row.resultStatus}`"
                                            >
                                                {{ bulkRowStatusLabel(row.resultStatus) }}
                                            </span>
                                            <div v-if="row.resultReason" class="employees-page__bulk-result-reason">
                                                {{ row.resultReason }}
                                            </div>
                                        </td>
                                        <td class="employees-page__bulk-remove">
                                            <button type="button" class="employees-page__icon-button" @click="removeBulkEmployee(row.userId)">
                                                ✕
                                            </button>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                        <div class="employees-page__bulk-search employees-page__export-group">
                            <div class="employees-page__bulk-search-header">
                                <Input
                                    v-model="bulkSearchQuery"
                                    label="Добавить сотрудника из базы (ФИО/табельный)"
                                    placeholder="Начните вводить..."
                                    @update:model-value="handleBulkSearch"
                                />
                                <div class="employees-page__bulk-search-scope">
                                    <span class="employees-page__bulk-search-scope-label">Поиск:</span>
                                    <label class="employees-page__bulk-search-switch">
                                        <input v-model="bulkSearchOnlyFired" type="checkbox">
                                        <span class="employees-page__bulk-search-slider" />
                                    </label>
                                    <span class="employees-page__bulk-search-scope-text">
                                        {{ bulkSearchOnlyFired ? 'уволенные' : 'активные' }}
                                    </span>
                                </div>
                            </div>
                            <p v-if="bulkSearchLoading" class="employees-page__bulk-search-hint">Поиск...</p>
                            <div v-if="bulkSearchResults.length" class="employees-page__bulk-search-results">
                                <button
                                    v-for="item in bulkSearchResults"
                                    :key="resolveEmployeeId(item) || item.staff_code || item.username"
                                    type="button"
                                    class="employees-page__bulk-search-item"
                                    @click="addBulkEmployee(item)"
                                >
                                    {{ formatFullNameShort(item) }}
                                    ({{ item.staff_code || 'без табеля' }})
                                    <span v-if="bulkSearchOnlyFired" class="employees-page__bulk-search-item-meta">уволен</span>
                                </button>
                            </div>
                        </div>
                        <div v-if="bulkAdjustResultSummary" class="employees-page__bulk-result">
                            <p v-if="bulkAdjustResultSummary.created" class="success">
                                Создано: {{ bulkAdjustResultSummary.created }}
                            </p>
                            <p v-if="bulkAdjustResultSummary.skipped">Пропущено: {{ bulkAdjustResultSummary.skipped }}</p>
                            <p v-if="bulkAdjustResultSummary.errors">Ошибки: {{ bulkAdjustResultSummary.errors }}</p>
                        </div>
                        <div v-if="bulkAdjustResult.errors.length || bulkAdjustResult.skipped.length" class="employees-page__bulk-list">
                            <p><strong>Детали:</strong></p>
                            <ul>
                                <li v-for="item in bulkAdjustResult.errors" :key="'err-' + item.staff_code + item.reason">
                                    {{ bulkResultItemLabel(item) }}: {{ item.reason }}
                                </li>
                                <li v-for="item in bulkAdjustResult.skipped" :key="'skip-' + item.staff_code + item.reason">
                                    {{ bulkResultItemLabel(item) }}: {{ item.reason }}
                                </li>
                            </ul>
                        </div>
                    </form>
                </template>
                <template #footer>
                    <Button color="ghost" :disabled="bulkAdjustLoading" @click="closeBulkAdjustModal">
                        Отмена
                    </Button>
                    <Button color="primary" :loading="bulkAdjustLoading" @click="handleBulkAdjust">Применить</Button>
                </template>
            </Modal>

            <Modal
                v-if="isBulkFillModalOpen"
                class="employees-page__export-mass-modal"
                @close="closeBulkFillModal"
            >
                <template #header>Заполнить список</template>
                <template #default>
                    <div class="employees-page__bulk-fill">
                        <Select
                            v-model="bulkFilters.workplaceId"
                            label="Место работы"
                            :options="workplaceFilterOptions"
                        />
                        <div class="employees-page__bulk-filter-panel">
                            <button
                                type="button"
                                class="employees-page__bulk-filter-toggle"
                                @click="toggleBulkSubdivisionPanel"
                            >
                                Подразделения
                                <span class="employees-page__bulk-filter-toggle-meta">
                                    {{ bulkSubdivisionSelectionLabel }}
                                </span>
                            </button>
                            <div v-if="isBulkSubdivisionPanelOpen" class="employees-page__bulk-filter-panel-body">
                                <div class="employees-page__bulk-multiselect">
                                    <div class="employees-page__bulk-options employees-page__bulk-options--scroll">
                                        <Checkbox
                                            :model-value="bulkFilters.subdivisionIds.length === 0"
                                            label="Все"
                                            @update:model-value="(checked) => handleBulkSubdivisionAll(checked)"
                                        />
                                        <Checkbox
                                            v-for="sub in bulkSubdivisionOptions"
                                            :key="sub.value"
                                            :label="sub.label"
                                            :model-value="bulkFilters.subdivisionIds.includes(sub.value)"
                                            @update:model-value="(checked) => toggleBulkSubdivision(sub.value, checked)"
                                        />
                                        <p v-if="!bulkSubdivisionOptions.length" class="employees-page__filter-empty">
                                            Нет доступных подразделений
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="employees-page__bulk-filter-panel">
                            <button
                                type="button"
                                class="employees-page__bulk-filter-toggle"
                                @click="toggleBulkPositionPanel"
                            >
                                Должности
                                <span class="employees-page__bulk-filter-toggle-meta">
                                    {{ bulkPositionSelectionLabel }}
                                </span>
                            </button>
                            <div v-if="isBulkPositionPanelOpen" class="employees-page__bulk-filter-panel-body">
                                <div class="employees-page__bulk-multiselect">
                                    <div class="employees-page__bulk-options employees-page__bulk-options--scroll">
                                        <Checkbox
                                            :model-value="bulkFilters.positionIds.length === 0"
                                            label="Все"
                                            @update:model-value="(checked) => handleBulkPositionAll(checked)"
                                        />
                                        <Checkbox
                                            v-for="pos in bulkPositionOptions"
                                            :key="pos.value"
                                            :label="pos.label"
                                            :model-value="bulkFilters.positionIds.includes(pos.value)"
                                            @update:model-value="(checked) => toggleBulkPosition(pos.value, checked)"
                                        />
                                        <p v-if="!bulkPositionOptions.length" class="employees-page__filter-empty">
                                            Нет доступных должностей
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="employees-page__bulk-checkboxes">
                            <Checkbox v-model="bulkFilters.onlyFormalized" label="Официально оформлен" />
                            <Checkbox v-model="bulkFilters.onlyCis" label="Сотрудник СНГ" />
                        </div>
                    </div>
                </template>
                <template #footer>
                    <Button color="ghost" @click="closeBulkFillModal">Отмена</Button>
                    <Button color="primary" @click="fillBulkEmployeesFromFilters">Заполнить</Button>
                </template>
            </Modal>

            <Modal
                v-if="isTimesheetExportModalOpen"
                class="employees-page__export-modal"
                @close="closeTimesheetExportModal"
            >
                <template #header>Табель смен</template>
                <template #default>
                    <div v-if="timesheetOptionsLoading" class="employees-page__export-loading">Загрузка...</div>
                    <form v-else class="employees-page__export-form" @submit.prevent>
                        <Select
                            v-model="timesheetExportForm.restaurantId"
                            label="Ресторан"
                            :options="timesheetRestaurantOptions"
                            required
                        />
                        <DateInput
                            v-model="timesheetExportForm.dateFrom"
                            label="Дата с"
                            required
                        />
                        <DateInput
                            v-model="timesheetExportForm.dateTo"
                            label="Дата по"
                            required
                        />
                        <div class="employees-page__export-group employees-page__export-group--full">
                            <button
                                type="button"
                                class="employees-page__export-toggle"
                                @click="toggleTimesheetSubdivisionPanel"
                            >
                                <span>Подразделения</span>
                                <span class="employees-page__export-toggle-right">
                                    <span class="employees-page__export-toggle-meta">
                                        {{ timesheetSubdivisionSelectionLabel }}
                                    </span>
                                    <span
                                        :class="[
                                            'employees-page__export-toggle-icon',
                                            { 'is-open': isTimesheetSubdivisionPanelOpen },
                                        ]"
                                    >
                                        ▼
                                    </span>
                                </span>
                            </button>
                            <div v-if="isTimesheetSubdivisionPanelOpen" class="employees-page__export-options">
                                <Checkbox
                                    :model-value="timesheetSubdivisionAll"
                                    label="Все"
                                    @update:model-value="handleTimesheetSubdivisionAll"
                                />
                                <Checkbox
                                    v-for="item in timesheetSubdivisionOptions"
                                    :key="item.id"
                                    :label="item.label"
                                    :model-value="timesheetExportForm.subdivisionIds.includes(item.id)"
                                    @update:model-value="(checked) => toggleTimesheetSubdivision(item.id, checked)"
                                />
                            </div>
                        </div>
                        <div class="employees-page__export-group employees-page__export-group--full">
                            <button
                                type="button"
                                class="employees-page__export-toggle"
                                @click="toggleTimesheetPositionPanel"
                            >
                                <span>Должности</span>
                                <span class="employees-page__export-toggle-right">
                                    <span class="employees-page__export-toggle-meta">
                                        {{ timesheetPositionSelectionLabel }}
                                    </span>
                                    <span
                                        :class="[
                                            'employees-page__export-toggle-icon',
                                            { 'is-open': isTimesheetPositionPanelOpen },
                                        ]"
                                    >
                                        ▼
                                    </span>
                                </span>
                            </button>
                            <div v-if="isTimesheetPositionPanelOpen" class="employees-page__export-options">
                                <Checkbox
                                    :model-value="timesheetPositionAll"
                                    label="Все"
                                    @update:model-value="handleTimesheetPositionAll"
                                />
                                <Checkbox
                                    v-for="item in timesheetPositionOptionsFiltered"
                                    :key="item.id"
                                    :label="item.label"
                                    :model-value="timesheetExportForm.positionIds.includes(item.id)"
                                    @update:model-value="(checked) => toggleTimesheetPosition(item.id, checked)"
                                />
                            </div>
                        </div>
                    </form>
                </template>
                <template #footer>
                    <Button color="ghost" :disabled="timesheetExporting" @click="closeTimesheetExportModal">
                        Отмена
                    </Button>
                    <Button color="primary" :loading="timesheetExporting" @click="handleExportTimesheet">
                        Скачать
                    </Button>
                </template>
            </Modal>

            <AttendanceEditModal
                v-if="isAttendanceEditModalOpen"
                :is-open="isAttendanceEditModalOpen"
                :attendance-form="attendanceForm"
                :editing-attendance="editingAttendance"
                :restaurant-options="attendanceRestaurantOptions"
                :position-options="attendancePositionOptions"
                :is-creating="isCreatingAttendance"
                :updating-attendance="updatingAttendance"
                :deleting-attendance="deletingAttendance"
                :rate-hidden="attendanceRateHidden"
                @close="closeAttendanceEditModal"
                @submit-attendance="handleAttendanceSubmit"
                @delete-attendance="handleAttendanceDelete"
            />

            <EmployeeCreateModal
                v-if="isCreateModalOpen"
                :is-open="isCreateModalOpen"
                :new-employee="newEmployee"
                :gender-options="genderOptions"
                :position-options="positionOptions"
                :workplace-restaurant-options="workplaceRestaurantOptions"
                :restaurants="restaurants"
                :is-creating="isCreating"
                :can-edit-rates="canEditRates"
                :is-super-admin="isSuperAdminRole"
                :can-view-credentials="canViewAuthCredentials"
                :can-sync-to-iiko="canSyncEmployeeToIiko"
                @close="closeCreateModal"
                @create="handleCreateEmployee"
                @toggle-restaurant="toggleRestaurant"
            />

            <Modal
                v-if="isIikoCreateConfirmModalOpen"
                class="employees-page__comment-modal"
                @close="closeIikoCreateConfirmModal"
            >
                <template #header>Подтверждение создания в iiko</template>
                <div class="employees-page__comment-modal-body">
                    <p class="employees-page__comment-modal-hint">
                        Проверьте данные перед отправкой в iiko. При необходимости можно скорректировать поля.
                    </p>
                    <div class="employees-page__iiko-confirm-grid">
                        <Input
                            v-model="iikoCreateConfirmForm.lastName"
                            label="Фамилия в iiko"
                            placeholder="Фамилия"
                        />
                        <Input
                            v-model="iikoCreateConfirmForm.firstName"
                            label="Имя в iiko"
                            placeholder="Имя"
                        />
                        <Input
                            v-model="iikoCreateConfirmForm.staffCode"
                            label="Табельный номер"
                            placeholder="Например, 12345"
                        />
                        <Input
                            v-model="iikoCreateConfirmForm.iikoCode"
                            label="Код iiko"
                            placeholder="Например, 123456"
                        />
                        <Select
                            v-model="iikoCreateConfirmForm.workplaceRestaurantId"
                            label="Место работы"
                            :options="workplaceRestaurantOptions"
                            placeholder="Выберите ресторан"
                        />
                        <Select
                            v-model="iikoCreateConfirmForm.syncRestaurantId"
                            label="Ресторан для синхронизации"
                            :options="workplaceRestaurantOptions"
                            placeholder="Выберите ресторан"
                        />
                    </div>
                </div>
                <template #footer>
                    <Button
                        color="ghost"
                        :disabled="isCreating"
                        @click="closeIikoCreateConfirmModal"
                    >
                        Отмена
                    </Button>
                    <Button
                        color="primary"
                        :loading="isCreating"
                        @click="handleConfirmCreateInIiko"
                    >
                        Подтвердить
                    </Button>
                </template>
            </Modal>

            <Modal
                v-if="isIikoSyncConfirmModalOpen"
                class="employees-page__iiko-sync-modal"
                @close="closeIikoSyncConfirmModal"
            >
                <template #header>
                    {{ iikoSyncModeLabel }}
                </template>
                <div class="employees-page__comment-modal-body">
                    <p class="employees-page__comment-modal-hint">
                        Сверьте локальные данные и данные iiko, затем укажите единый вариант.
                    </p>
                    <div class="employees-page__iiko-preview-controls">
                        <Select
                            v-model="iikoSyncConfirmForm.syncRestaurantId"
                            label="Ресторан для загрузки данных из iiko"
                            :options="workplaceRestaurantOptions"
                            placeholder="Выберите ресторан"
                        />
                        <Button
                            color="secondary"
                            :loading="iikoSyncPreviewLoading"
                            :disabled="syncingEmployeeToIiko"
                            @click="reloadIikoSyncPreview"
                        >
                            Подтянуть данные
                        </Button>
                    </div>

                    <p v-if="iikoSyncPreviewLoading" class="employees-page__comment-modal-hint">
                        Загружаем данные iiko...
                    </p>
                    <p
                        v-if="iikoSyncPreviewError"
                        class="employees-page__comment-modal-hint employees-page__comment-modal-hint--warning"
                    >
                        {{ iikoSyncPreviewError }}
                    </p>
                    <p
                        v-if="iikoSyncLocalSnapshot && !iikoSyncLocalSnapshot?.position_code"
                        class="employees-page__comment-modal-hint employees-page__comment-modal-hint--warning"
                    >
                        У должности сотрудника не заполнен код. Синхронизация в iiko может завершиться ошибкой.
                    </p>

                    <div class="employees-page__iiko-compare-grid">
                        <div class="employees-page__iiko-compare-card">
                            <div class="employees-page__iiko-compare-card-header">
                                <h4>Данные у нас</h4>
                            </div>
                            <dl class="employees-page__iiko-compare-list">
                                <div><dt>Фамилия</dt><dd>{{ displayIikoValue(iikoSyncLocalSnapshot?.last_name) }}</dd></div>
                                <div><dt>Имя</dt><dd>{{ displayIikoValue(iikoSyncLocalSnapshot?.first_name) }}</dd></div>
                                <div><dt>Должность</dt><dd>{{ displayIikoValue(iikoSyncLocalSnapshot?.position_name) }}</dd></div>
                                <div><dt>Код должности</dt><dd>{{ displayIikoValue(iikoSyncLocalSnapshot?.position_code) }}</dd></div>
                                <div><dt>Табельный</dt><dd>{{ displayIikoValue(iikoSyncLocalSnapshot?.staff_code) }}</dd></div>
                                <div><dt>Код iiko</dt><dd>{{ displayIikoValue(iikoSyncLocalSnapshot?.iiko_code) }}</dd></div>
                                <div><dt>ID iiko</dt><dd>{{ displayIikoValue(iikoSyncLocalSnapshot?.iiko_id) }}</dd></div>
                                <div><dt>Ресторан</dt><dd>{{ displayIikoValue(iikoSyncLocalSnapshot?.workplace_restaurant_name) }}</dd></div>
                                <div><dt>Доступы</dt><dd>{{ formatIikoRestaurantList(iikoSyncLocalSnapshot) }}</dd></div>
                                <div><dt>Код подразделения</dt><dd>{{ displayIikoValue(iikoSyncLocalSnapshot?.department_code) }}</dd></div>
                            </dl>
                        </div>

                        <div class="employees-page__iiko-compare-card">
                            <div class="employees-page__iiko-compare-card-header">
                                <h4>Данные в iiko</h4>
                            </div>
                            <dl v-if="iikoSyncRemoteSnapshot" class="employees-page__iiko-compare-list">
                                <div><dt>Фамилия</dt><dd>{{ displayIikoValue(iikoSyncRemoteSnapshot.last_name) }}</dd></div>
                                <div><dt>Имя</dt><dd>{{ displayIikoValue(iikoSyncRemoteSnapshot.first_name) }}</dd></div>
                                <div><dt>Должность</dt><dd>{{ displayIikoValue(iikoSyncRemoteSnapshot.position_name) }}</dd></div>
                                <div><dt>Код должности</dt><dd>{{ displayIikoValue(iikoSyncRemoteSnapshot.position_code) }}</dd></div>
                                <div><dt>Табельный</dt><dd>{{ displayIikoValue(iikoSyncRemoteSnapshot.staff_code) }}</dd></div>
                                <div><dt>Код iiko</dt><dd>{{ displayIikoValue(iikoSyncRemoteSnapshot.iiko_code) }}</dd></div>
                                <div><dt>ID iiko</dt><dd>{{ displayIikoValue(iikoSyncRemoteSnapshot.iiko_id) }}</dd></div>
                                <div><dt>Ресторан</dt><dd>{{ displayIikoValue(iikoSyncRemoteSnapshot.workplace_restaurant_name) }}</dd></div>
                                <div><dt>Доступы</dt><dd>{{ formatIikoRestaurantList(iikoSyncRemoteSnapshot) }}</dd></div>
                                <div><dt>Код подразделения</dt><dd>{{ displayIikoValue(iikoSyncRemoteSnapshot.department_code) }}</dd></div>
                            </dl>
                            <p v-else class="employees-page__comment-modal-hint">
                                Данные сотрудника в iiko не найдены.
                            </p>
                        </div>
                    </div>

                    <div class="employees-page__iiko-update-card">
                        <p class="employees-page__iiko-access-title">Поля для обновления в iiko</p>
                        <div class="employees-page__iiko-update-grid">
                            <div class="employees-page__iiko-update-row">
                                <div class="employees-page__iiko-update-source">
                                    <Select
                                        v-model="iikoSyncFieldSources.lastName"
                                        label="Источник фамилии"
                                        :options="iikoSyncSourceOptions"
                                        :disabled="!iikoSyncFieldEnabled.lastName"
                                    />
                                    <label class="employees-page__iiko-field-toggle">
                                        <input v-model="iikoSyncFieldEnabled.lastName" type="checkbox">
                                        <span class="employees-page__iiko-field-toggle-slider" />
                                        <span class="employees-page__iiko-field-toggle-label">Отправлять в iiko</span>
                                    </label>
                                </div>
                                <Input
                                    v-model="iikoSyncConfirmForm.lastName"
                                    label="Фамилия в iiko"
                                    placeholder="Фамилия"
                                    :disabled="!iikoSyncFieldEnabled.lastName"
                                />
                            </div>
                            <div class="employees-page__iiko-update-row">
                                <div class="employees-page__iiko-update-source">
                                    <Select
                                        v-model="iikoSyncFieldSources.firstName"
                                        label="Источник имени"
                                        :options="iikoSyncSourceOptions"
                                        :disabled="!iikoSyncFieldEnabled.firstName"
                                    />
                                    <label class="employees-page__iiko-field-toggle">
                                        <input v-model="iikoSyncFieldEnabled.firstName" type="checkbox">
                                        <span class="employees-page__iiko-field-toggle-slider" />
                                        <span class="employees-page__iiko-field-toggle-label">Отправлять в iiko</span>
                                    </label>
                                </div>
                                <Input
                                    v-model="iikoSyncConfirmForm.firstName"
                                    label="Имя в iiko"
                                    placeholder="Имя"
                                    :disabled="!iikoSyncFieldEnabled.firstName"
                                />
                            </div>
                            <div class="employees-page__iiko-update-row">
                                <div class="employees-page__iiko-update-source">
                                    <Select
                                        v-model="iikoSyncFieldSources.staffCode"
                                        label="Источник табельного"
                                        :options="iikoSyncSourceOptions"
                                        :disabled="!iikoSyncFieldEnabled.staffCode"
                                    />
                                    <label class="employees-page__iiko-field-toggle">
                                        <input v-model="iikoSyncFieldEnabled.staffCode" type="checkbox">
                                        <span class="employees-page__iiko-field-toggle-slider" />
                                        <span class="employees-page__iiko-field-toggle-label">Отправлять в iiko</span>
                                    </label>
                                </div>
                                <Input
                                    v-model="iikoSyncConfirmForm.staffCode"
                                    label="Табельный номер в iiko"
                                    placeholder="Например, 12345"
                                    :disabled="!iikoSyncFieldEnabled.staffCode"
                                />
                            </div>
                            <div class="employees-page__iiko-update-row">
                                <div class="employees-page__iiko-update-source">
                                    <Select
                                        v-model="iikoSyncFieldSources.iikoCode"
                                        label="Источник кода iiko"
                                        :options="iikoSyncSourceOptions"
                                        :disabled="!iikoSyncFieldEnabled.iikoCode"
                                    />
                                    <label class="employees-page__iiko-field-toggle">
                                        <input v-model="iikoSyncFieldEnabled.iikoCode" type="checkbox">
                                        <span class="employees-page__iiko-field-toggle-slider" />
                                        <span class="employees-page__iiko-field-toggle-label">Отправлять в iiko</span>
                                    </label>
                                </div>
                                <Input
                                    v-model="iikoSyncConfirmForm.iikoCode"
                                    label="Код iiko"
                                    placeholder="Например, 123456"
                                    :disabled="!iikoSyncFieldEnabled.iikoCode"
                                />
                            </div>
                            <div class="employees-page__iiko-update-row">
                                <div class="employees-page__iiko-update-source">
                                    <Select
                                        v-model="iikoSyncFieldSources.workplaceRestaurantId"
                                        label="Источник места работы"
                                        :options="iikoSyncSourceOptions"
                                        :disabled="!iikoSyncFieldEnabled.workplaceRestaurantId"
                                    />
                                    <label class="employees-page__iiko-field-toggle">
                                        <input v-model="iikoSyncFieldEnabled.workplaceRestaurantId" type="checkbox">
                                        <span class="employees-page__iiko-field-toggle-slider" />
                                        <span class="employees-page__iiko-field-toggle-label">Отправлять в iiko</span>
                                    </label>
                                </div>
                                <Select
                                    v-model="iikoSyncConfirmForm.workplaceRestaurantId"
                                    label="Место работы в iiko"
                                    :options="workplaceRestaurantOptions"
                                    placeholder="Выберите ресторан"
                                    :disabled="!iikoSyncFieldEnabled.workplaceRestaurantId"
                                />
                            </div>
                        </div>
                    </div>

                    <div class="employees-page__iiko-access-card">
                        <div class="employees-page__iiko-access-header">
                            <p class="employees-page__iiko-access-title">Доступ в рестораны iiko</p>
                            <label class="employees-page__iiko-field-toggle">
                                <input v-model="iikoSyncFieldEnabled.departmentRestaurantIds" type="checkbox">
                                <span class="employees-page__iiko-field-toggle-slider" />
                                <span class="employees-page__iiko-field-toggle-label">Отправлять в iiko</span>
                            </label>
                        </div>
                        <div
                            class="employees-page__iiko-access-options"
                            :class="{ 'is-disabled': !iikoSyncFieldEnabled.departmentRestaurantIds }"
                        >
                            <Checkbox
                                v-for="option in iikoDepartmentRestaurantOptions"
                                :key="option.value"
                                :label="option.label"
                                :model-value="iikoSyncConfirmForm.departmentRestaurantIds.includes(option.value)"
                                :disabled="!iikoSyncFieldEnabled.departmentRestaurantIds"
                                @update:model-value="(checked) => toggleIikoSyncDepartmentRestaurant(option.value, checked)"
                            />
                            <p v-if="!iikoDepartmentRestaurantOptions.length" class="employees-page__comment-modal-hint">
                                Нет доступных ресторанов для выбора.
                            </p>
                        </div>
                    </div>
                </div>
                <template #footer>
                    <Button
                        color="ghost"
                        :disabled="syncingEmployeeToIiko"
                        @click="closeIikoSyncConfirmModal"
                    >
                        Отмена
                    </Button>
                    <Button
                        color="primary"
                        :loading="syncingEmployeeToIiko"
                        @click="handleConfirmSyncEmployeeToIiko"
                    >
                        Подтвердить
                    </Button>
                </template>
            </Modal>
        </div>
        <div v-else class="employees-page__no-access">
            <h2 class="employees-page__no-access-title">Доступ ограничен</h2>
            <p class="employees-page__no-access-text">
                У вас нет прав для просмотра сотрудников.
            </p>
        </div>
    </div>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'vue-toastification';
import {
    fetchEmployeeCard,
    fetchEmployeeChangeEvents,
    fetchEmployeeDetail,
    fetchEmployeeIikoSyncPreview,
    fetchEmployees,
    fetchEmployeesBootstrap,
    fetchAccessPositions,
    uploadEmployeePhoto,
    updateStaffEmployee,
    deleteStaffEmployee,
    restoreStaffEmployee,
    fetchCompanies,
    fetchRoles,
    fetchRestaurants,
    fetchUser,
    createUser,
    updateUser,
} from '@/api';
import { useDebounce } from '@/composables/useDebounce';
import { useUserStore } from '@/stores/user';
import { useEmployeeAccess } from './composables/useEmployeeAccess';
import { useEmployeeListState } from './composables/useEmployeeListState';
import { useEmployeeTableFilters } from './composables/useEmployeeTableFilters';
import { useEmployeeAttendances } from './composables/useEmployeeAttendances';
import { useEmployeeBulkAdjust } from './composables/useEmployeeBulkAdjust';
import { useEmployeeDocuments } from './composables/useEmployeeDocuments';
import { useEmployeeExports } from './composables/useEmployeeExports';
import { useEmployeePayrollAdjustments } from './composables/useEmployeePayrollAdjustments';
import { useEmployeePermissions } from './composables/useEmployeePermissions';
import { useEmployeeTimesheetExport } from './composables/useEmployeeTimesheetExport';
import { useEmployeeTrainings } from './composables/useEmployeeTrainings';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import Divider from '@/components/UI-components/Divider.vue';
import AttendanceEditModal from './components/AttendanceEditModal.vue';
import EmployeeCreateModal from './components/EmployeeCreateModal.vue';
import EmployeeEditModal from './components/EmployeeEditModal.vue';
import EmployeeModal from './components/EmployeeModal.vue';
import EmployeesTable from './components/EmployeesTable.vue';
import PayrollAdjustmentModal from './components/PayrollAdjustmentModal.vue';
import TrainingAssignmentModal from './components/TrainingAssignmentModal.vue';
import { getEmployeeColumns } from './employeeColumns';
import { formatDateInputValue, formatDateValue, formatNumberValue, parseDate } from '@/utils/format';
import { formatPhoneForInput, normalizePhoneForApi, sanitizePhoneInput } from '@/utils/phone';

const PERMISSION_CODE_GROUP_FALLBACKS = [
    { pattern: /^system(\.|$)/, label: 'Система' },
    { pattern: /^staff(_|\.|$)/, label: 'Сотрудники' },
    { pattern: /^(roles|positions|users|companies|restaurants)(\.|$)/, label: 'Администрирование' },
    { pattern: /^(employees_card|staff_employees)(\.|$)/, label: 'Сотрудники' },
    { pattern: /^checklists(\.|$)/, label: 'Сотрудники' },
    { pattern: /^inventory(\.|$)/, label: 'Склад' },
    { pattern: /^payroll(\.|$)/, label: 'Зарплата' },
    { pattern: /^kpi(\.|$)/, label: 'KPI' },
    { pattern: /^training(\.|$)/, label: 'Обучение' },
    { pattern: /^iiko(\.|$)/, label: 'Продажи' },
    { pattern: /^sales(\.|$)/, label: 'Продажи' },
    { pattern: /^sections(\.|$)/, label: 'Доступ к разделам' },
    { pattern: /^(medical_checks|cis_documents)(\.|$)/, label: 'Кадры' },
    { pattern: /^access_control(\.|$)/, label: 'Доступ' },
    { pattern: /^kitchen(\.|$)/, label: 'Кухня' },
    { pattern: /^(time|timesheet)(_|\.|$)/, label: 'Табель смен' },
];

const props = defineProps({
    modalOnly: {
        type: Boolean,
        default: false,
    },
});


const userStore = useUserStore();
const router = useRouter();
const route = useRoute();

const modalOnly = computed(() => props.modalOnly);

const {
    isSuperAdminRole,
    canViewSensitiveStaffFields,
    canEditIikoId,
    canViewAuthCredentials,
    canViewEmployees,
    canManageEmployees,
    canEditRoles,
    canEditRates,
    canCreateEmployees,
    canSyncEmployeeToIiko,
    canEditFullAccess,
    canManageUserPermissions,
    canLoadRoles,
    canLoadRestaurants,
    canLoadCompanies,
    canLoadPositions,
    canBulkPayrollAdjust,
    canExportTimesheet,
    canDownloadEmployeesList,
    canViewDocuments,
    canViewMedicalChecks,
    canViewCisDocuments,
    canManageMedicalChecks,
    canManageCisDocuments,
    canManageDocuments,
    canViewEmployeeChanges,
    canRestoreEmployees
} = useEmployeeAccess(userStore);

const toast = useToast();

const {
    employeeColumnOptions,
    selectedEmployeeColumns,
    search,
    onlyFired,
    onlyFormalized,
    onlyNotFormalized,
    onlyCis,
    onlyNotCis,
    sortBy,
    sortDirection,
    isFiltersOpen,
    isColumnSelectorOpen,
    handleSearchChange,
    handleOnlyFiredChange,
    handleOnlyFormalizedChange,
    handleOnlyNotFormalizedChange,
    handleOnlyCisChange,
    handleOnlyNotCisChange,
    handleSortByChange,
    handleSortDirectionChange,
    handleEmployeeColumnChange,
    toggleFilters,
    toggleColumnSelector
} = useEmployeeListState({
    canViewSensitiveStaffFields,
    getEmployeeColumns,
    onMinColumnsError: () => {
        toast.error('Не удалось выполнить операцию');
    }
});

const employees = ref([]);
const isLoading = ref(false);
let employeesLoadCounter = 0;
let employeesLoadPromise = null;
let employeesLoadKey = '';
let employeesLoadAbortController = null;
const EMPLOYEES_BOOTSTRAP_DEDUP_MS = 5000;
let employeesLastBootstrapKey = '';
let employeesLastBootstrapAt = 0;
const EMPLOYEE_TAB_AUTOLOAD_DEDUP_MS = 1500;
const employeeTabAutoLoadInflight = new Map();
const employeeTabAutoLoadRecent = new Map();

const isEmployeeModalOpen = ref(false);
const isOpeningFromRoute = ref(false);
const activeEmployee = ref(null);
const employeeCard = ref(null);
const cardLoading = ref(false);
const uploadingPhoto = ref(false);
const activeModalTab = ref('info');
const employeeChangeEvents = ref([]);
const employeeChangeEventsLoading = ref(false);
const employeeChangeEventsError = ref('');
const CARD_CHANGE_FIELDS = new Set([
    'rate',
    'individual_rate',
    'position_rate',
    'position',
    'position_id',
    'role',
    'role_id',
    'company',
    'company_id',
    'workplace_restaurant',
    'workplace_restaurant_id',
    'workplace_id',
    'restaurants',
    'has_full_restaurant_access',
    'permissions',
    'staff_code',
    'username',
    'phone',
    'phone_number',
    'email',
    'first_name',
    'last_name',
    'middle_name',
    'hire_date',
    'fire_date',
    'fired',
    'birth_date',
    'gender',
    'iiko_id',
    'iiko_code',
    'employee_row_id',
    'has_fingerprint',
    'is_formalized',
    'confidential_data_consent',
    'is_cis_employee',
    'photo_key',
    'restaurant_subdivision_id',
    'restaurant_subdivision_name',
]);
const restoringEmployee = ref(false);
const syncingEmployeeToIiko = ref(false);
const preparingIikoSyncPreview = ref(false);
const isDeleteCommentModalOpen = ref(false);
const deleteCommentText = ref('');
const deleteFromIikoPending = ref(false);
const isDuplicateInfoModalOpen = ref(false);
const duplicateEmployeeInfo = ref(null);
const isIikoSyncActionLoading = computed(
    () => syncingEmployeeToIiko.value || preparingIikoSyncPreview.value,
);

const employeePhotoUrl = computed(() => employeeCard.value?.photo_url || '');

const handleActiveTabChange = (tab) => {
    if (tab === 'permissions' && !canManageUserPermissions.value) {
        return;
    }
    activeModalTab.value = tab;
};
const {
    employeeAttendances,
    reversedAttendances,
    attendanceSummary,
    attendanceRateHidden,
    attendancesLoading,
    attendanceDateFrom,
    attendanceDateTo,
    recalculatingNightMinutes,
    isAttendanceEditModalOpen,
    isCreatingAttendance,
    editingAttendance,
    updatingAttendance,
    deletingAttendance,
    attendanceForm,
    handleAttendanceDateFromChange,
    handleAttendanceDateToChange,
    loadEmployeeAttendances,
    openAttendanceEditModal,
    openAttendanceCreateModal,
    closeAttendanceEditModal,
    handleAttendanceSubmit,
    handleAttendanceDelete,
    handleRecalculateNightMinutes,
    resetEmployeeAttendancesState,
} = useEmployeeAttendances({
    activeEmployee,
    employeeCard,
    formatMinutesTotal,
    toMinutesValue,
});

const {
    medicalCheckRecords,
    cisDocumentRecords,
    medicalCheckTypes,
    cisDocumentTypes,
    medicalCheckTypesLoading,
    cisDocumentTypesLoading,
    documentsLoading,
    medicalForm,
    cisDocumentForm,
    employmentDocumentForm,
    isMedicalFormOpen,
    isMedicalBulkMode,
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
    medicalCheckTypeOptions,
    cisDocumentTypeOptions,
    employmentDocumentRows,
    employmentDocumentFormLabel,
    startCreateMedicalRecord,
    startCreateMedicalRecordsBulk,
    startCreateCisDocument,
    startEditMedicalRecord,
    startEditCisDocument,
    startEditEmploymentDocument,
    cancelMedicalForm,
    cancelCisDocumentForm,
    cancelEmploymentDocumentForm,
    loadMedicalCheckTypes,
    loadCisDocumentTypes,
    refreshEmployeeDocuments,
    handleSaveMedicalRecord,
    handleDeleteMedicalRecord,
    handleSaveCisDocument,
    handleDeleteCisDocument,
    handleSaveEmploymentDocument,
    handleDeleteEmploymentDocument,
    handleUploadEmploymentAttachment,
    handleUploadCisAttachment,
    syncEmployeeDocumentsFromCard,
    resetEmployeeDocumentsState,
} = useEmployeeDocuments({
    activeEmployee,
    canViewDocuments,
    canViewMedicalChecks,
    canViewCisDocuments,
});
const {
    userPermissionCatalog,
    userPermissionCatalogLoading,
    userPermissions,
    userPermissionsLoading,
    userPermissionUpdating,
    userAssignedPermissionCodes,
    loadUserPermissionCatalog,
    loadUserPermissions,
    handleToggleUserPermission,
    resetUserPermissionState,
} = useEmployeePermissions({
    activeEmployee,
    canManageUserPermissions,
});
const {
    employeeTrainings,
    trainingsLoading,
    trainingEventTypes,
    trainingTypesLoading,
    trainingForm,
    creatingTrainingRecord,
    isTrainingAssignmentModalOpen,
    editingTrainingRecord,
    updatingTrainingRecord,
    deletingTrainingRecordId,
    trainingRequirementSuggestions,
    trainingRequirementsLoading,
    updatingTrainingRequirementId,
    trainingTypeOptions,
    loadTrainingEventTypes,
    loadEmployeeTrainings,
    loadTrainingRequirements,
    toggleTrainingRequirement,
    openTrainingAssignmentModal,
    closeTrainingAssignmentModal,
    handleCreateTrainingRecord,
    startEditTrainingRecord,
    cancelEditTrainingRecord,
    handleUpdateTrainingRecord,
    handleDeleteTrainingRecord,
    resetEmployeeTrainingsState,
} = useEmployeeTrainings({
    activeEmployee,
    employeeCard,
    formatDateInput,
});

function handleEditTrainingRecordField(payload) {
    const field = payload?.field;
    if (!field || !Object.prototype.hasOwnProperty.call(editingTrainingRecord, field)) {
        return;
    }
    editingTrainingRecord[field] = payload.value;
}

const userPermissionCatalogRows = computed(() =>
    userPermissionCatalog.value.map((permission) => ({
        code: permission?.code || '',
        label: permission?.display_name || permission?.name || permission?.code || '',
        description: permission?.description?.trim() || '',
        group: resolvePermissionGroup(permission),
    })),
);

const companies = ref([]);
const positions = ref([]);
const positionsLoadedFromAccess = ref(false);
const restaurants = ref([]);
const roles = ref([]);
const referencesLoadedFromBootstrap = ref(false);
let isEmployeesBootstrapAvailable = true;

const companyOptions = computed(() =>
    companies.value
        .map((company) => ({ value: String(company.id), label: company.name }))
        .sort((a, b) => a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' })),
);
const companyFilterOptions = computed(() => [
    { value: '', label: 'Все компании' },
    ...companyOptions.value,
]);

const restaurantOptions = computed(() =>
    restaurants.value
        .map((restaurant) => ({ value: String(restaurant.id), label: restaurant.name }))
        .sort((a, b) => a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' })),
);

const workplaceRestaurantOptions = computed(() => [
    { value: '', label: 'Не выбрано' },
    ...restaurantOptions.value,
]);
const restaurantFilterOptions = computed(() => [
    { value: '', label: 'Все рестораны' },
    ...restaurantOptions.value,
]);

const positionOptions = computed(() =>
    positions.value
        .map((position) => ({ value: String(position.id), label: position.name }))
        .sort((a, b) => a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' })),
);

const attendanceRestaurantOptions = computed(() => [
    { value: '', label: 'Не выбран' },
    ...restaurantOptions.value,
]);

const attendancePositionOptions = computed(() => [
    { value: '', label: 'Не выбрана' },
    ...positionOptions.value,
]);

function resolvePermissionGroup(permission) {
    const explicit = extractExplicitPermissionZone(permission);
    if (explicit) {
        return explicit;
    }
    return inferPermissionGroupFromCode(permission);
}

function extractExplicitPermissionZone(permission) {
    const candidates = [
        permission?.responsibility_zone,
        permission?.responsibilityZone,
    ];
    for (const candidate of candidates) {
        if (typeof candidate === 'string') {
            const trimmed = candidate.trim();
            if (trimmed) {
                return trimmed;
            }
        }
    }
    return '';
}

function inferPermissionGroupFromCode(permission) {
    const rawCode =
        typeof permission?.code === 'string'
            ? permission.code
            : typeof permission?.api_router === 'string'
            ? permission.api_router
            : '';
    const normalized = rawCode.trim().toLowerCase();
    if (!normalized) {
        return '';
    }
    for (const fallback of PERMISSION_CODE_GROUP_FALLBACKS) {
        if (fallback.pattern.test(normalized)) {
            return fallback.label;
        }
    }
    const prefix = normalized.split(/[._]/)[0]?.replace(/_/g, ' ').trim();
    if (!prefix) {
        return '';
    }
    return prefix.replace(/\b\w/g, (char) => char.toUpperCase());
}

const {
    selectedRestaurantFilter,
    selectedPositionFilters,
    hireDateFrom,
    hireDateTo,
    fireDateFrom,
    fireDateTo,
    positionFilterQuery,
    includeFired,
    filteredPositionOptions,
    defaultRestaurantFilter,
    togglePositionFilter
} = useEmployeeTableFilters({
    onlyFired,
    positionOptions,
    restaurantOptions,
    userStore
});


const isEditMode = ref(false);
const editContextLoading = ref(false);
const updatingEmployee = ref(false);
const deletingEmployee = ref(false);

const employeeEditForm = reactive({
    username: '',
    firstName: '',
    middleName: '',
    lastName: '',
    gender: null,
    staffCode: '',
    iikoCode: '',
    iikoId: '',
    phoneNumber: '',
    phoneInput: '',
    email: '',
    isCisEmployee: false,
    isFormalized: false,
    confidentialDataConsent: false,
    roleId: null,
    companyId: null,
    positionId: null,
    workplaceRestaurantId: '',
    restaurantIds: [],
    hasFullRestaurantAccess: false,
    hasGlobalAccess: false,
    rateHidden: false,
    rate: '',
    individualRate: '',
    useIndividualRate: false,
    hireDate: '',
    fireDate: '',
    birthDate: '',
    password: '',
    photoKey: '',
});

const suppressEmployeeRateAutofill = ref(false);
const suppressEmployeeEditWorkplaceSync = ref(false);
const employeeEditInitialFullAccess = ref(false);
const employeeEditInitialUsername = ref('');
const employeeEditInitialRestaurantIds = ref([]);
const employeeEditRestaurantsTouched = ref(false);

const payrollRestaurantOptions = computed(() => {
    if (Array.isArray(restaurants.value) && restaurants.value.length) {
        return restaurants.value.map((r) => ({
            value: String(r.id),
            label: r.name || `ID ${r.id}`,
        }));
    }

    if (Array.isArray(userStore.restaurantIds) && userStore.restaurantIds.length) {
        return userStore.restaurantIds
            .map((id) => Number(id))
            .filter((id) => Number.isFinite(id))
            .map((id) => ({
                value: String(id),
                label: `ID ${id}`,
            }));
    }

    const restaurantsFromEmployee = Array.isArray(activeEmployee.value?.restaurants)
        ? activeEmployee.value.restaurants
        : [];
    if (restaurantsFromEmployee.length) {
        return restaurantsFromEmployee
            .filter((r) => r?.id)
            .map((r) => ({
                value: String(r.id),
                label: r.name || `ID ${r.id}`,
            }));
    }

    const ids = Array.isArray(activeEmployee.value?.restaurant_ids)
        ? activeEmployee.value.restaurant_ids
        : [];
    return ids
        .map((id) => Number(id))
        .filter((id) => Number.isFinite(id))
        .map((id) => ({
            value: String(id),
            label: `ID ${id}`,
        }));
});

const responsibleOptions = computed(() => {
    const options = new Map();
    for (const employee of employees.value) {
        if (employee?.id) {
            options.set(employee.id, {
                value: String(employee.id),
                label: formatFullName(employee),
            });
        }
    }
    if (userStore.id && !options.has(userStore.id)) {
        options.set(userStore.id, {
            value: String(userStore.id),
            label: userStore.fullName || userStore.login || `ID ${userStore.id}`,
        });
    }
    return Array.from(options.values());
});
const employeeFilterOptions = computed(() => [
    { value: '', label: 'Все сотрудники' },
    ...responsibleOptions.value,
]);

const {
    payrollAdjustmentTypes,
    payrollAdjustmentTypesLoading,
    payrollAdjustments,
    payrollAdjustmentsLoading,
    isPayrollAdjustmentFormVisible,
    creatingPayrollAdjustment,
    editingPayrollAdjustment,
    updatingPayrollAdjustment,
    deletingPayrollAdjustmentId,
    newPayrollAdjustment,
    payrollAdjustmentTypeOptions,
    loadPayrollAdjustmentTypes,
    loadEmployeePayrollAdjustments,
    openPayrollAdjustmentForm,
    closePayrollAdjustmentForm,
    startEditPayrollAdjustment,
    cancelEditPayrollAdjustment,
    handleUpdatePayrollAdjustment,
    handleDeletePayrollAdjustment,
    handleCreatePayrollAdjustment,
    resetEmployeePayrollState,
} = useEmployeePayrollAdjustments({
    activeEmployee,
    userStore,
    formatDateInput,
    payrollRestaurantOptions,
});
const {
    isTimesheetExportModalOpen,
    timesheetExporting,
    timesheetOptionsLoading,
    timesheetOptions,
    isTimesheetSubdivisionPanelOpen,
    isTimesheetPositionPanelOpen,
    timesheetExportForm,
    timesheetRestaurantOptions,
    timesheetSubdivisionOptions,
    timesheetPositionOptionsFiltered,
    timesheetSubdivisionAll,
    timesheetPositionAll,
    timesheetSubdivisionSelectionLabel,
    timesheetPositionSelectionLabel,
    loadTimesheetOptions,
    openTimesheetExportModal,
    closeTimesheetExportModal,
    toggleTimesheetSubdivisionPanel,
    toggleTimesheetPositionPanel,
    handleTimesheetSubdivisionAll,
    toggleTimesheetSubdivision,
    handleTimesheetPositionAll,
    toggleTimesheetPosition,
    handleExportTimesheet,
} = useEmployeeTimesheetExport({
    formatDateInput,
});

const {
    isBulkAdjustModalOpen,
    bulkAdjustLoading,
    bulkAdjustForm,
    bulkCommonAmountEnabled,
    bulkCommonAmount,
    bulkAdjustResult,
    bulkAdjustEmployees,
    bulkSearchQuery,
    bulkSearchResults,
    bulkSearchLoading,
    bulkSearchOnlyFired,
    bulkFilters,
    isBulkPositionPanelOpen,
    isBulkSubdivisionPanelOpen,
    isBulkFillModalOpen,
    bulkAdjustResultSummary,
    bulkPositionSelectionLabel,
    bulkSubdivisionSelectionLabel,
    bulkPositionOptions,
    bulkSubdivisionOptions,
    workplaceFilterOptions,
    bulkDisplayedEmployees,
    bulkResultItemLabel,
    bulkRowStatusLabel,
    openBulkAdjustModal,
    closeBulkAdjustModal,
    openBulkFillModal,
    closeBulkFillModal,
    addBulkEmployee,
    removeBulkEmployee,
    fillBulkEmployeesFromFilters,
    handleBulkSearch,
    handleBulkPositionAll,
    toggleBulkPosition,
    handleBulkSubdivisionAll,
    toggleBulkSubdivision,
    toggleBulkSort,
    toggleBulkPositionPanel,
    toggleBulkSubdivisionPanel,
    handleBulkAdjust,
} = useEmployeeBulkAdjust({
    employees,
    restaurantOptions,
    timesheetOptions,
    formatDateInput,
    resolveEmployeeId,
    formatFullNameShort,
    employeeMatchesWorkplace,
    loadPayrollAdjustmentTypes,
    loadTimesheetOptions,
});


const isCreateModalOpen = ref(false);
const isCreating = ref(false);
const isIikoCreateConfirmModalOpen = ref(false);
const isIikoSyncConfirmModalOpen = ref(false);

const newEmployee = reactive({
    username: '',
    password: '',
    firstName: '',
    middleName: '',
    lastName: '',
    gender: null,
    iikoCode: '',
    staffCode: '',
    phoneNumber: '',
    phoneInput: '',
    email: '',
    isCisEmployee: false,
    isFormalized: false,
    confidentialDataConsent: false,
    roleId: null,
    companyId: null,
    positionId: null,
    workplaceRestaurantId: '',
    rate: '',
    individualRate: '',
    useIndividualRate: false,
    hireDate: '',
    fireDate: '',
    birthDate: '',
    photoKey: '',
    restaurantIds: [],
    hasFullRestaurantAccess: false,
    addToIiko: false,
    iikoSyncRestaurantId: '',
    createInAdmin: false,
});

const iikoCreateConfirmForm = reactive({
    firstName: '',
    lastName: '',
    staffCode: '',
    iikoCode: '',
    workplaceRestaurantId: '',
    syncRestaurantId: '',
});

const iikoSyncConfirmForm = reactive({
    firstName: '',
    lastName: '',
    staffCode: '',
    iikoCode: '',
    workplaceRestaurantId: '',
    syncRestaurantId: '',
    departmentRestaurantIds: [],
});
const iikoSyncSourceOptions = [
    { value: 'local', label: 'Наши данные' },
    { value: 'iiko', label: 'Данные iiko' },
    { value: 'manual', label: 'Ввести вручную' },
];
const iikoSyncFieldSources = reactive({
    firstName: 'local',
    lastName: 'local',
    staffCode: 'local',
    iikoCode: 'local',
    workplaceRestaurantId: 'local',
});
const iikoSyncFieldEnabled = reactive({
    firstName: true,
    lastName: true,
    staffCode: true,
    iikoCode: true,
    workplaceRestaurantId: true,
    departmentRestaurantIds: true,
});
const iikoSyncLocalSnapshot = ref(null);
const iikoSyncRemoteSnapshot = ref(null);
const iikoSyncPreviewLoading = ref(false);
const iikoSyncPreviewError = ref('');
const iikoSyncModeLabel = computed(() => {
    const hasIikoId = Boolean(activeEmployee.value?.iiko_id || employeeCard.value?.iiko_id);
    return hasIikoId ? 'Подтверждение обновления в iiko' : 'Подтверждение создания в iiko';
});
const iikoDepartmentRestaurantOptions = computed(() => {
    const options = new Map();
    for (const restaurant of restaurants.value || []) {
        if (!restaurant?.id) {
            continue;
        }
        options.set(Number(restaurant.id), restaurant.name || `Ресторан #${restaurant.id}`);
    }
    for (const snapshot of [iikoSyncLocalSnapshot.value, iikoSyncRemoteSnapshot.value]) {
        if (!snapshot) {
            continue;
        }
        const ids = Array.isArray(snapshot.restaurant_ids) ? snapshot.restaurant_ids : [];
        const names = Array.isArray(snapshot.restaurant_names) ? snapshot.restaurant_names : [];
        ids.forEach((id, index) => {
            const parsed = Number(id);
            if (!Number.isFinite(parsed) || options.has(parsed)) {
                return;
            }
            options.set(parsed, names[index] || `Ресторан #${parsed}`);
        });
    }
    return Array.from(options.entries())
        .map(([value, label]) => ({ value, label }))
        .sort((a, b) => a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' }));
});

const roleOptions = computed(() =>
    roles.value
        .map((role) => ({ value: String(role.id), label: role.name }))
        .sort((a, b) => a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' })),
);
const genderOptions = [
    { value: 'male', label: 'Мужской' },
    { value: 'female', label: 'Женский' },
];

function derivePositionsFromEmployees(items = []) {
    const positionMap = new Map();
    for (const item of items) {
        if (item?.position_id && item?.position_name) {
            positionMap.set(item.position_id, {
                id: item.position_id,
                name: item.position_name,
                rate: item?.position_rate ?? null,
            });
        }
    }
    positions.value = Array.from(positionMap.values());
}

function findPositionById(positionId) {
    if (positionId === null || positionId === undefined || positionId === '') {
        return null;
    }
    const parsed = Number(positionId);
    if (!Number.isFinite(parsed)) {
        return null;
    }
    return positions.value.find((position) => position.id === parsed) ?? null;
}

function syncNewEmployeeRateWithPosition() {
    if (newEmployee.useIndividualRate) {
        return;
    }
    if (!newEmployee.positionId) {
        newEmployee.rate = '';
        return;
    }
    const position = findPositionById(newEmployee.positionId);
    if (!position || position.rate === null || position.rate === undefined) {
        newEmployee.rate = '';
        return;
    }
    newEmployee.rate = String(position.rate);
}

function syncEmployeeEditRateWithPosition() {
    if (suppressEmployeeRateAutofill.value) {
        return;
    }
    if (employeeEditForm.rateHidden) {
        return;
    }
    if (employeeEditForm.useIndividualRate) {
        return;
    }
    if (!employeeEditForm.positionId) {
        employeeEditForm.rate = '';
        return;
    }
    const position = findPositionById(employeeEditForm.positionId);
    if (!position || position.rate === null || position.rate === undefined) {
        employeeEditForm.rate = '';
        return;
    }
    employeeEditForm.rate = String(position.rate);
}

function applyBootstrapReferences(references) {
    const data = references && typeof references === 'object' ? references : {};

    if (canLoadRestaurants.value && Array.isArray(data.restaurants)) {
        restaurants.value = data.restaurants;
    }
    if (canLoadCompanies.value && Array.isArray(data.companies)) {
        companies.value = data.companies;
    }
    if (canLoadRoles.value && Array.isArray(data.roles)) {
        roles.value = data.roles;
    }
    if (canLoadPositions.value && Array.isArray(data.positions)) {
        positions.value = data.positions;
        positionsLoadedFromAccess.value = true;
    }
    referencesLoadedFromBootstrap.value = true;
}

async function loadEmployees(options = {}) {
    const includeReferences = Boolean(options?.includeReferences);
    if (!canViewEmployees.value) {
        if (employeesLoadAbortController) {
            employeesLoadAbortController.abort();
            employeesLoadAbortController = null;
        }
        employees.value = [];
        employeesLastBootstrapKey = '';
        employeesLastBootstrapAt = 0;
        return;
    }
    const hasRestaurantFilter =
        selectedRestaurantFilter.value !== null &&
        selectedRestaurantFilter.value !== undefined &&
        String(selectedRestaurantFilter.value).trim() !== '';
    const restaurantIdRaw = hasRestaurantFilter ? Number(selectedRestaurantFilter.value) : NaN;
    const restaurantId = Number.isFinite(restaurantIdRaw) && restaurantIdRaw > 0 ? restaurantIdRaw : null;
    const params = {
        q: search.value || undefined,
        include_fired: includeFired.value || undefined,
        restaurant_id: restaurantId ?? undefined,
        hire_date_from: hireDateFrom.value || undefined,
        hire_date_to: hireDateTo.value || undefined,
        fire_date_from: fireDateFrom.value || undefined,
        fire_date_to: fireDateTo.value || undefined,
        limit: 1000,
    };
    const canUseBootstrap = Boolean(includeReferences && isEmployeesBootstrapAvailable);
    const requestKey = JSON.stringify({
        includeReferences: canUseBootstrap,
        ...params,
    });
    if (
        canUseBootstrap &&
        employeesLastBootstrapKey === requestKey &&
        Date.now() - employeesLastBootstrapAt < EMPLOYEES_BOOTSTRAP_DEDUP_MS
    ) {
        return;
    }
    if (employeesLoadPromise && employeesLoadKey === requestKey) {
        return await employeesLoadPromise;
    }

    if (employeesLoadAbortController) {
        employeesLoadAbortController.abort();
        employeesLoadAbortController = null;
    }
    const abortController = new AbortController();
    employeesLoadAbortController = abortController;
    const requestId = ++employeesLoadCounter;
    isLoading.value = true;
    const currentPromise = (async () => {
        try {
            if (canUseBootstrap) {
                try {
                    const data = await fetchEmployeesBootstrap(params, {
                        signal: abortController.signal,
                    });
                    if (requestId !== employeesLoadCounter) return;
                    const items = Array.isArray(data?.items) ? data.items : [];
                    employees.value = items;
                    applyBootstrapReferences(data?.references);
                    if (!positionsLoadedFromAccess.value) {
                        derivePositionsFromEmployees(items);
                    }
                    employeesLastBootstrapKey = requestKey;
                    employeesLastBootstrapAt = Date.now();
                    return;
                } catch (error) {
                    if (error?.response?.status === 404) {
                        isEmployeesBootstrapAvailable = false;
                    } else {
                        throw error;
                    }
                }
            }

            const { items } = await fetchEmployees(params, {
                signal: abortController.signal,
            });
            if (requestId !== employeesLoadCounter) return;
            employees.value = items;

            if (!positionsLoadedFromAccess.value) {
                derivePositionsFromEmployees(items);
            }
        } catch (error) {
            if (error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError') {
                return;
            }
            if (requestId !== employeesLoadCounter) return;
            const detail = error?.response?.data?.detail;
            if (error?.response?.status === 403) {
                employees.value = [];
                positions.value = [];
                positionsLoadedFromAccess.value = false;
            } else {
                toast.error(detail || 'Не удалось выполнить операцию');
                console.error(error);
            }
        } finally {
            if (requestId === employeesLoadCounter) {
                isLoading.value = false;
            }
            if (employeesLoadAbortController === abortController) {
                employeesLoadAbortController = null;
            }
        }
    })();

    employeesLoadPromise = currentPromise;
    employeesLoadKey = requestKey;
    try {
        await currentPromise;
    } finally {
        if (employeesLoadPromise === currentPromise) {
            employeesLoadPromise = null;
            employeesLoadKey = '';
        }
    }
}

function formatFullName(employee) {
    if (!employee) return '—';
    const lastName = employee.last_name ?? employee.lastName;
    const firstName = employee.first_name ?? employee.firstName;
    const middleName = employee.middle_name ?? employee.middleName;
    const parts = [lastName, firstName, middleName].filter(Boolean);
    return parts.length ? parts.join(' ') : employee.username;
}

function formatFullNameShort(employee) {
    if (!employee) return '-';
    const lastName = employee.last_name ?? employee.lastName;
    const firstName = employee.first_name ?? employee.firstName;
    const parts = [lastName, firstName].filter(Boolean);
    if (parts.length) {
        return parts.join(' ');
    }
    return formatFullName(employee);
}

function getDuplicateEmployeeInfo(detail) {
    if (!detail || typeof detail !== 'object' || detail.code !== 'employee_duplicate') {
        return null;
    }
    const info = detail.employee && typeof detail.employee === 'object' ? detail.employee : {};
    const canOpenCard =
        detail.can_open_card ?? detail.can_open ?? detail.can_view_card ?? detail.can_view ?? null;
    const fullName = [info.last_name, info.first_name, info.middle_name].filter(Boolean).join(' ');
    const parts = [];
    if (fullName) {
        parts.push(`ФИО: ${fullName}`);
    }
    if (info.birth_date) {
        parts.push(`Дата рождения: ${formatDate(info.birth_date)}`);
    }
    if (info.hire_date) {
        parts.push(`Прием: ${formatDate(info.hire_date)}`);
    }
    if (info.fire_date) {
        parts.push(`Увольнение: ${formatDate(info.fire_date)}`);
    }
    if (info.position) {
        parts.push(`Должность: ${info.position}`);
    }
    if (info.workplace) {
        parts.push(`Место работы: ${info.workplace}`);
    }
    const baseMessage = 'Сотрудник с такими ФИО и датой рождения уже существует.';
    const message = parts.length ? `${baseMessage} ${parts.join(', ')}` : baseMessage;
    const rawId = info.id ?? info.user_id ?? detail.employee_id ?? detail.user_id;
    const id = Number(rawId);
    return {
        message,
        employee: info,
        id: Number.isFinite(id) ? id : null,
        canOpenCard: canOpenCard === null ? null : Boolean(canOpenCard),
    };
}

async function handleDuplicateEmployeeError(detail, options = {}) {
    const duplicate = getDuplicateEmployeeInfo(detail);
    if (!duplicate) {
        return false;
    }
    toast.error(duplicate.message);
    if ((duplicate.canOpenCard ?? true) && duplicate.id && canViewEmployees.value) {
        if (options.closeCreate) {
            closeCreateModal();
        }
        await openEmployeeModal({ ...duplicate.employee, id: duplicate.id });
    } else {
        if (options.closeCreate) {
            closeCreateModal();
        }
        openDuplicateInfoModal(duplicate.employee);
    }
    return true;
}

const duplicateEmployeeFullName = computed(() => {
    const info = duplicateEmployeeInfo.value;
    if (!info) {
        return '—';
    }
    const parts = [info.last_name, info.first_name, info.middle_name].filter(Boolean);
    return parts.length ? parts.join(' ') : '—';
});

const duplicateEmployeeInitials = computed(() => {
    const info = duplicateEmployeeInfo.value;
    if (!info) {
        return '';
    }
    const last = info.last_name?.trim()?.[0] || '';
    const first = info.first_name?.trim()?.[0] || '';
    const middle = info.middle_name?.trim()?.[0] || '';
    const initials = `${last}${first}${middle}`.trim();
    return initials || '—';
});

function employeeMatchesWorkplace(employee, workplaceId) {
    if (!workplaceId) return false;
    const target = Number(workplaceId);
    if (!Number.isFinite(target)) return false;
    const source =
        employee?.workplace_restaurant_id ??
        employee?.workplaceId ??
        employee?.workplace_restaurant?.id ??
        null;
    const normalized = Number(source);
    return Number.isFinite(normalized) && normalized === target;
}

function normalizeEmailForApi(value) {
    const raw = (value ?? '').toString().trim();
    if (!raw) {
        return { email: null, error: null };
    }

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(raw)) {
        return { email: null, error: 'Введите корректный email адрес.' };
    }

    return { email: raw, error: null };
}

function applyPhoneInput(target, value) {
    const sanitized = sanitizePhoneInput(value);
    target.phoneNumber = sanitized;
    target.phoneInput = formatPhoneForInput(sanitized);
}

const collator = new Intl.Collator('ru', { numeric: true, sensitivity: 'base' });

const sortedEmployees = computed(() => {
    const baseList = filterEmployeesByRestaurant(employees.value, selectedRestaurantFilter.value);
    const filteredList = filterEmployeesByPositions(baseList, selectedPositionFilters.value);
    const hireFilteredList = filterEmployeesByDateRange(
        filteredList,
        'hire_date',
        hireDateFrom.value,
        hireDateTo.value,
    );
    const fireFilteredList = filterEmployeesByDateRange(
        hireFilteredList,
        'fire_date',
        fireDateFrom.value,
        fireDateTo.value,
    );
    const flaggedList = filterEmployeesByFlags(fireFilteredList);
    const list = Array.isArray(flaggedList) ? [...flaggedList] : [];
    if (!list.length || !sortBy.value) {
        return list;
    }

    const direction = sortDirection.value === 'desc' ? -1 : 1;

    return list.sort((a, b) => {
        const aValue = getSortValue(a, sortBy.value);
        const bValue = getSortValue(b, sortBy.value);

        const aEmpty = aValue === null || aValue === undefined || aValue === '';
        const bEmpty = bValue === null || bValue === undefined || bValue === '';

        if (aEmpty && bEmpty) return 0;
        if (aEmpty) return direction;
        if (bEmpty) return -direction;

        const aNumber = typeof aValue === 'number' ? aValue : Number(aValue);
        const bNumber = typeof bValue === 'number' ? bValue : Number(bValue);

        if (Number.isFinite(aNumber) && Number.isFinite(bNumber)) {
            return (aNumber - bNumber) * direction;
        }

        return collator.compare(String(aValue), String(bValue)) * direction;
    });
});

const {
    isPayrollExportModalOpen,
    payrollExporting,
    employeesListExporting,
    payrollExportForm,
    closePayrollExportModal,
    downloadEmployeesList,
    handleExportPayroll,
} = useEmployeeExports({
    canDownloadEmployeesList,
    getSortedEmployees: () => sortedEmployees.value,
    employeeColumnOptions,
    selectedEmployeeColumns,
});

function getSortValue(employee, field) {
    switch (field) {
        case 'staff_code':
            return employee?.staff_code ?? '';
        case 'full_name':
            return formatFullName(employee);
        case 'username':
            return employee?.username ?? '';
        case 'role_name':
            return employee?.role_name ?? '';
        case 'position_name':
            return employee?.position_name ?? '';
        case 'hire_date':
        case 'fire_date':
        case 'birth_date':
            return employee?.[field] ? parseDateValue(employee[field])?.getTime() ?? null : null;
        case 'restaurants':
            return getEmployeeRestaurantsList(employee);
        case 'status':
            return employee?.fired ? 1 : 0;
        default:
            return employee?.[field] ?? '';
    }
}

function parseDateValue(value) {
    return parseDate(value);
}

function formatDateInput(value) {
    return formatDateInputValue(value, { emptyValue: '' });
}

function formatDate(value) {
    return formatDateValue(value, {
        emptyValue: '—',
        invalidValue: '—',
    });
}

function formatGender(value) {
    if (value === 'male') return 'Мужской';
    if (value === 'female') return 'Женский';
    return '—';
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

function formatResponsible(responsibleId, responsibleName) {
    if (!responsibleId) {
        return responsibleName || '-';
    }
    if (responsibleName) {
        return responsibleName;
    }
    if (activeEmployee.value?.id === responsibleId) {
        return formatFullName(activeEmployee.value);
    }
    const inList = employees.value.find((employee) => employee.id === responsibleId);
    if (inList) {
        return formatFullName(inList);
    }
    if (employeeCard.value?.id === responsibleId) {
        return formatFullName(employeeCard.value);
    }
    return `ID ${responsibleId}`;
}

function formatRestaurant(restaurantId) {
    if (restaurantId === null || restaurantId === undefined || restaurantId === '') {
        return '—';
    }
    const idNum = Number(restaurantId);
    const fromActive = activeEmployee.value?.restaurants?.find((r) => r?.id === idNum);
    if (fromActive) {
        return fromActive.name || `ID ${idNum}`;
    }
    const fromList = restaurants.value?.find((r) => r?.id === idNum);
    if (fromList) {
        return fromList.name || `ID ${idNum}`;
    }
    return `ID ${idNum}`;
}

function toMinutesValue(value) {
    if (value === null || value === undefined || value === '') {
        return 0;
    }
    const numberValue = Number(value);
    return Number.isFinite(numberValue) ? numberValue : 0;
}

function formatMinutesTotal(totalMinutes) {
    if (!totalMinutes) {
        return '0 ч 0 мин';
    }
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    const parts = [];
    if (hours) {
        parts.push(`${hours} ч`);
    }
    parts.push(`${minutes} мин`);
    return parts.join(' ');
}

function resolveEmployeeId(employee) {
    const id = Number(employee?.id ?? employee?.user_id);
    return Number.isFinite(id) ? id : null;
}

function resolveEmployeeIdFromQuery(value) {
    const rawValue = Array.isArray(value) ? value[0] : value;
    const id = Number(rawValue);
    return Number.isFinite(id) ? id : null;
}

async function openEmployeeFromQuery() {
    if (!canViewEmployees.value) {
        return;
    }
    const employeeId = resolveEmployeeIdFromQuery(route.query.employeeId);
    if (!employeeId) {
        if (modalOnly.value && isEmployeeModalOpen.value && !isOpeningFromRoute.value) {
            closeEmployeeModal();
        }
        return;
    }
    if (isEmployeeModalOpen.value && Number(activeEmployee.value?.id) === employeeId) {
        return;
    }
    if (isOpeningFromRoute.value) {
        return;
    }

    isOpeningFromRoute.value = true;
    try {
        let employee =
            employees.value.find((item) => resolveEmployeeId(item) === employeeId) || null;
        if (!employee) {
            const detail = await fetchEmployeeDetail(employeeId);
            employee = detail?.user ?? detail;
        }
        if (!employee) {
            return;
        }
        await openEmployeeModal(employee);
    } catch (error) {
        console.error(error);
        toast.error(error?.response?.data?.detail || 'Не удалось открыть карточку сотрудника');
    } finally {
        isOpeningFromRoute.value = false;
    }
}

async function openEmployeeModal(employee) {
    if (!canViewEmployees.value) {
        return;
    }
    const employeeId = resolveEmployeeId(employee);
    if (!employeeId) {
        toast.error('Не удалось открыть карточку сотрудника');
        return;
    }
    closeAttendanceEditModal();
    cancelEditMode();
    activeEmployee.value = { ...(employee || {}), id: employeeId };
    isEmployeeModalOpen.value = true;
    activeModalTab.value = 'info';
    await loadEmployeeCard(employeeId);
}

async function loadEmployeeCard(userId) {
    cardLoading.value = true;
    try {
        employeeCard.value = await fetchEmployeeCard(userId ?? activeEmployee.value?.id);
        syncEmployeeDocumentsFromCard(employeeCard.value);
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось выполнить операцию');
        console.error(error);
    } finally {
        cardLoading.value = false;
    }
}

async function loadEmployeeChangeEvents() {
    if (!activeEmployee.value || !canViewEmployeeChanges.value) {
        employeeChangeEvents.value = [];
        employeeChangeEventsError.value = '';
        return;
    }
    employeeChangeEventsLoading.value = true;
    employeeChangeEventsError.value = '';
    try {
        const data = await fetchEmployeeChangeEvents({
            user_id: activeEmployee.value.id,
            limit: 200,
        });
        const items = Array.isArray(data?.items) ? data.items : [];
        employeeChangeEvents.value = items.filter((item) => CARD_CHANGE_FIELDS.has(item.field));
    } catch (error) {
        console.error(error);
        employeeChangeEventsError.value =
            error?.response?.data?.detail || 'Не удалось загрузить историю';
        employeeChangeEvents.value = [];
    } finally {
        employeeChangeEventsLoading.value = false;
    }
}

function resolveActiveEmployeeTabKey() {
    const employeeId = Number(activeEmployee.value?.id);
    if (!Number.isFinite(employeeId) || employeeId <= 0) {
        return '';
    }
    const positionIdRaw = Number(activeEmployee.value?.position_id);
    const positionId = Number.isFinite(positionIdRaw) && positionIdRaw > 0 ? positionIdRaw : 'none';
    return `${employeeId}:${positionId}`;
}

async function runEmployeeTabAutoLoad(tab, key, loader) {
    if (!key) {
        return;
    }

    const now = Date.now();
    const recent = employeeTabAutoLoadRecent.get(tab);
    if (recent && recent.key === key && now - recent.at < EMPLOYEE_TAB_AUTOLOAD_DEDUP_MS) {
        return;
    }

    const inflightKey = `${tab}:${key}`;
    if (employeeTabAutoLoadInflight.has(inflightKey)) {
        await employeeTabAutoLoadInflight.get(inflightKey);
        return;
    }

    const promise = (async () => {
        await loader();
        employeeTabAutoLoadRecent.set(tab, { key, at: Date.now() });
    })().finally(() => {
        employeeTabAutoLoadInflight.delete(inflightKey);
    });

    employeeTabAutoLoadInflight.set(inflightKey, promise);
    await promise;
}

async function autoLoadShiftTab() {
    const baseKey = resolveActiveEmployeeTabKey();
    if (!baseKey) {
        return;
    }
    const key = `${baseKey}:${attendanceDateFrom.value || ''}:${attendanceDateTo.value || ''}`;
    await runEmployeeTabAutoLoad('shifts', key, async () => {
        await loadEmployeeAttendances();
    });
}

async function autoLoadTrainingTab() {
    const key = resolveActiveEmployeeTabKey();
    if (!key) {
        return;
    }
    await runEmployeeTabAutoLoad('trainings', key, async () => {
        if (!trainingEventTypes.value.length && !trainingTypesLoading.value) {
            await loadTrainingEventTypes();
        }
        await loadEmployeeTrainings();
        await loadTrainingRequirements();
    });
}

async function autoLoadPermissionTab() {
    if (!canManageUserPermissions.value) {
        return;
    }
    const key = resolveActiveEmployeeTabKey();
    if (!key) {
        return;
    }
    await runEmployeeTabAutoLoad('permissions', key, async () => {
        await loadUserPermissionCatalog();
        await loadUserPermissions();
    });
}

async function autoLoadDocumentsTab() {
    if (!canViewDocuments.value) {
        return;
    }
    const key = resolveActiveEmployeeTabKey();
    if (!key) {
        return;
    }
    await runEmployeeTabAutoLoad('documents', key, async () => {
        if (canManageDocuments.value) {
            if (!medicalCheckTypes.value.length && !medicalCheckTypesLoading.value) {
                await loadMedicalCheckTypes();
            }
            if (!cisDocumentTypes.value.length && !cisDocumentTypesLoading.value) {
                await loadCisDocumentTypes();
            }
        }
        await refreshEmployeeDocuments();
    });
}

async function autoLoadFinanceTab() {
    const key = resolveActiveEmployeeTabKey();
    if (!key) {
        return;
    }
    await runEmployeeTabAutoLoad('finance', key, async () => {
        if (!payrollAdjustmentTypes.value.length && !payrollAdjustmentTypesLoading.value) {
            await loadPayrollAdjustmentTypes();
        }
        await loadEmployeePayrollAdjustments();
    });
}

async function autoLoadChangesTab() {
    if (!canViewEmployeeChanges.value) {
        return;
    }
    const key = resolveActiveEmployeeTabKey();
    if (!key) {
        return;
    }
    await runEmployeeTabAutoLoad('changes', key, async () => {
        await loadEmployeeChangeEvents();
    });
}

async function handleUploadEmployeePhoto(file) {
    if (!activeEmployee.value || !file) {
        return;
    }
    uploadingPhoto.value = true;
    try {
        const response = await uploadEmployeePhoto(activeEmployee.value.id, file);
        employeeCard.value = {
            ...(employeeCard.value || {}),
            photo_key: response?.photo_key || null,
            photo_url: response?.photo_url || null,
        };
        toast.success('Фото обновлено');
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось выполнить операцию');
        console.error(error);
    } finally {
        uploadingPhoto.value = false;
    }
}

function populateEmployeeEditForm(card, userData) {
    suppressEmployeeRateAutofill.value = true;
    suppressEmployeeEditWorkplaceSync.value = true;
    employeeEditForm.username = userData?.username ?? '';
    employeeEditForm.firstName = card?.first_name ?? '';
    employeeEditForm.middleName = card?.middle_name ?? '';
    employeeEditForm.lastName = card?.last_name ?? '';
    employeeEditForm.gender = card?.gender ?? null;
    employeeEditForm.staffCode = card?.staff_code ?? '';
    employeeEditForm.email = card?.email ?? userData?.email ?? '';
    employeeEditForm.iikoCode = card?.iiko_code ?? '';
    employeeEditForm.iikoId = card?.iiko_id ?? activeEmployee.value?.iiko_id ?? '';
    employeeEditForm.isCisEmployee = getEmployeeCisValue(card, userData);
    employeeEditForm.confidentialDataConsent = Boolean(card?.confidential_data_consent);
    employeeEditForm.roleId = card?.role_id ? String(card.role_id) : null;
    employeeEditForm.companyId = card?.company_id ? String(card.company_id) : null;
    employeeEditForm.positionId = card?.position_id ? String(card.position_id) : null;
    employeeEditForm.workplaceRestaurantId = card?.workplace_restaurant_id
        ? String(card.workplace_restaurant_id)
        : '';
    employeeEditForm.rateHidden = Boolean(card?.rate_hidden);
    if (employeeEditForm.rateHidden) {
        employeeEditForm.rate = '';
        employeeEditForm.individualRate = '';
        employeeEditForm.useIndividualRate = false;
    } else {
        employeeEditForm.rate = card?.rate !== null && card?.rate !== undefined ? String(card.rate) : '';
        employeeEditForm.individualRate =
            card?.individual_rate !== null && card?.individual_rate !== undefined ? String(card.individual_rate) : '';
        employeeEditForm.useIndividualRate = Boolean(
            card?.individual_rate !== null && card?.individual_rate !== undefined,
        );
    }
    employeeEditForm.hireDate = card?.hire_date ?? '';
    employeeEditForm.fireDate = card?.fire_date ?? '';
    employeeEditForm.birthDate = card?.birth_date ?? '';
    applyPhoneInput(employeeEditForm, card?.phone_number ?? '');
    employeeEditForm.isFormalized = getEmployeeFormalizedValue(card, userData);
    employeeEditForm.photoKey = card?.photo_key ?? '';
    employeeEditForm.password = '';

    const restaurantsFromUser = Array.isArray(userData?.restaurants)
        ? userData.restaurants.map((r) => r.id)
        : Array.isArray(userData?.restaurant_ids)
            ? userData.restaurant_ids
            : [];
    employeeEditForm.restaurantIds = restaurantsFromUser;
    employeeEditInitialRestaurantIds.value = [...restaurantsFromUser];
    employeeEditRestaurantsTouched.value = false;
    const hasFullAccessFlag = Boolean(userData?.has_full_restaurant_access);
    const hasGlobalAccess = Boolean(userData?.has_global_access);
    employeeEditForm.hasGlobalAccess = hasGlobalAccess;
    employeeEditForm.hasFullRestaurantAccess = hasFullAccessFlag;
    employeeEditInitialFullAccess.value = hasFullAccessFlag;
    employeeEditInitialUsername.value = employeeEditForm.username;

    if (!employeeEditForm.middleName && userData?.middle_name) {
        employeeEditForm.middleName = userData.middle_name;
    }
    if (!employeeEditForm.confidentialDataConsent && userData?.confidential_data_consent) {
        employeeEditForm.confidentialDataConsent = Boolean(userData.confidential_data_consent);
    }

    if (!employeeEditForm.roleId && userData?.role?.id) {
        employeeEditForm.roleId = String(userData.role.id);
    }
    if (!employeeEditForm.companyId && userData?.company?.id) {
        employeeEditForm.companyId = String(userData.company.id);
    }
    if (!employeeEditForm.positionId && userData?.position?.id) {
        employeeEditForm.positionId = String(userData.position.id);
    }
    if (!employeeEditForm.useIndividualRate && userData?.individual_rate !== null && userData?.individual_rate !== undefined) {
        employeeEditForm.individualRate = String(userData.individual_rate);
        employeeEditForm.useIndividualRate = true;
    }
    if (!employeeEditForm.workplaceRestaurantId && userData?.workplace_restaurant_id) {
        employeeEditForm.workplaceRestaurantId = String(userData.workplace_restaurant_id);
    }
    if (userData?.position?.id && !positions.value.some((pos) => pos.id === userData.position.id)) {
        positions.value = [
            ...positions.value,
            { id: userData.position.id, name: userData.position.name || `ID ${userData.position.id}` },
        ];
    }
    nextTick(() => {
        suppressEmployeeRateAutofill.value = false;
        suppressEmployeeEditWorkplaceSync.value = false;
    });
}

async function enterEditMode() {
    if (!activeEmployee.value || !canManageEmployees.value) {
        return;
    }
    try {
        editContextLoading.value = true;
        isEditMode.value = true;
        const userData = await fetchUser(activeEmployee.value.id);
        populateEmployeeEditForm(employeeCard.value, userData);
    } catch (error) {
        const detail = error?.response?.data?.detail;
        isEditMode.value = false;
        toast.error(detail || 'Не удалось выполнить операцию');
        console.error(error);
    } finally {
        editContextLoading.value = false;
    }
}

function cancelEditMode() {
    isEditMode.value = false;
    editContextLoading.value = false;
    employeeEditForm.password = '';
}

async function toggleEditMode() {
    if (isEditMode.value) {
        cancelEditMode();
        return;
    }
    await enterEditMode();
}


function filterEmployeesByRestaurant(list, filterValue) {
    if (!filterValue) {
        return list || [];
    }
    const parsedId = Number(filterValue);
    if (!Number.isFinite(parsedId)) {
        return list || [];
    }
    return (list || []).filter((employee) => employeeMatchesWorkplace(employee, parsedId));
}

function filterEmployeesByPositions(list, selectedIds) {
    if (!Array.isArray(selectedIds) || selectedIds.length === 0) {
        return list || [];
    }
    const allowed = new Set(
        selectedIds
            .map((id) => Number(id))
            .filter((id) => Number.isFinite(id)),
    );
    if (!allowed.size) {
        return list || [];
    }
    return (list || []).filter((employee) => {
        const positionId = Number(employee?.position_id);
        return Number.isFinite(positionId) && allowed.has(positionId);
    });
}

function parseDateFilterValue(value) {
    if (!value) {
        return null;
    }
    const time = Date.parse(value);
    return Number.isFinite(time) ? time : null;
}

function filterEmployeesByDateRange(list, field, fromValue, toValue) {
    const fromTime = parseDateFilterValue(fromValue);
    const toTime = parseDateFilterValue(toValue);
    if (fromTime === null && toTime === null) {
        return list || [];
    }
    return (list || []).filter((employee) => {
        const time = parseDateFilterValue(employee?.[field]);
        if (time === null) {
            return false;
        }
        if (fromTime !== null && time < fromTime) {
            return false;
        }
        if (toTime !== null && time > toTime) {
            return false;
        }
        return true;
    });
}

function getEmployeeFlagValue(sources, keys) {
    for (const source of sources) {
        if (!source) {
            continue;
        }
        for (const key of keys) {
            if (source?.[key] !== undefined && source?.[key] !== null) {
                return Boolean(source[key]);
            }
        }
    }
    return false;
}

function getEmployeeFiredValue(...sources) {
    return getEmployeeFlagValue(sources, ['fired', 'is_fired', 'isFired']);
}

function getEmployeeFormalizedValue(...sources) {
    return getEmployeeFlagValue(sources, ['is_formalized', 'isFormalized', 'formalized']);
}

function getEmployeeCisValue(...sources) {
    return getEmployeeFlagValue(sources, ['is_cis_employee', 'isCisEmployee', 'cis']);
}

function isEmployeeFired(employee) {
    return getEmployeeFiredValue(employee);
}

function isEmployeeFormalized(employee) {
    return getEmployeeFormalizedValue(employee);
}

function isEmployeeCis(employee) {
    return getEmployeeCisValue(employee);
}

function filterEmployeesByFlags(list) {
    const wantsFormalized = onlyFormalized.value;
    const wantsNotFormalized = onlyNotFormalized.value;
    const formalizedFilterActive = wantsFormalized || wantsNotFormalized;
    const hasContradiction = wantsFormalized && wantsNotFormalized;
    const wantsCis = onlyCis.value;
    const wantsNotCis = onlyNotCis.value;
    const cisFilterActive = wantsCis || wantsNotCis;
    const cisContradiction = wantsCis && wantsNotCis;

    if (!onlyFired.value && !formalizedFilterActive && !cisFilterActive) {
        return list || [];
    }
    return (list || []).filter((employee) => {
        if (onlyFired.value && !isEmployeeFired(employee)) {
            return false;
        }
        if (!hasContradiction) {
            if (wantsFormalized && !isEmployeeFormalized(employee)) {
                return false;
            }
            if (wantsNotFormalized && isEmployeeFormalized(employee)) {
                return false;
            }
        }
        if (!cisContradiction) {
            if (wantsCis && !isEmployeeCis(employee)) {
                return false;
            }
            if (wantsNotCis && isEmployeeCis(employee)) {
                return false;
            }
        }
        return true;
    });
}

function getEmployeeRestaurantsList(employee) {
    if (!employee) {
        return '';
    }
    if (Array.isArray(employee.restaurants) && employee.restaurants.length) {
        const names = employee.restaurants
            .map((restaurant) => {
                if (restaurant?.name) {
                    return restaurant.name;
                }
                if (restaurant?.id !== undefined && restaurant?.id !== null) {
                    return `ID ${restaurant.id}`;
                }
                return '';
            })
            .filter(Boolean);
        if (names.length) {
            return names.join(', ');
        }
    }
    if (Array.isArray(employee.restaurant_ids) && employee.restaurant_ids.length) {
        return employee.restaurant_ids
            .filter((value) => value !== null && value !== undefined && value !== '')
            .join(', ');
    }
    return '';
}

function closeEmployeeModal() {
    isEmployeeModalOpen.value = false;
    activeEmployee.value = null;
    employeeCard.value = null;
    uploadingPhoto.value = false;
    syncingEmployeeToIiko.value = false;
    preparingIikoSyncPreview.value = false;
    isIikoSyncConfirmModalOpen.value = false;
    resetIikoSyncPreviewState();
    resetIikoSyncConfirmForm();
    isDeleteCommentModalOpen.value = false;
    deleteCommentText.value = '';
    deleteFromIikoPending.value = false;
    resetEmployeeAttendancesState();
    employeeChangeEvents.value = [];
    employeeChangeEventsError.value = '';
    employeeChangeEventsLoading.value = false;
    resetEmployeeTrainingsState();
    resetUserPermissionState();
    resetEmployeePayrollState();
    resetEmployeeDocumentsState();
    cancelEditMode();

    if (route.query.employeeId) {
        const nextQuery = { ...route.query };
        delete nextQuery.employeeId;
        router.replace({ query: nextQuery });
    }
}

function openCreateModal() {
    if (!canCreateEmployees.value) {
        toast.error('Не удалось выполнить операцию');
        return;
    }
    isCreateModalOpen.value = true;
}

function closeCreateModal() {
    isCreateModalOpen.value = false;
    isIikoCreateConfirmModalOpen.value = false;
    resetCreateForm();
}

function resetIikoCreateConfirmForm() {
    iikoCreateConfirmForm.firstName = '';
    iikoCreateConfirmForm.lastName = '';
    iikoCreateConfirmForm.staffCode = '';
    iikoCreateConfirmForm.iikoCode = '';
    iikoCreateConfirmForm.workplaceRestaurantId = '';
    iikoCreateConfirmForm.syncRestaurantId = '';
}

function syncIikoCreateConfirmFormFromNewEmployee() {
    iikoCreateConfirmForm.firstName = newEmployee.firstName || '';
    iikoCreateConfirmForm.lastName = newEmployee.lastName || '';
    iikoCreateConfirmForm.staffCode = newEmployee.staffCode || '';
    iikoCreateConfirmForm.iikoCode = newEmployee.iikoCode || '';
    iikoCreateConfirmForm.workplaceRestaurantId = newEmployee.workplaceRestaurantId || '';
    iikoCreateConfirmForm.syncRestaurantId = newEmployee.iikoSyncRestaurantId || newEmployee.workplaceRestaurantId || '';
}

function applyIikoCreateConfirmFormToCreateForm() {
    newEmployee.firstName = (iikoCreateConfirmForm.firstName || '').trim();
    newEmployee.lastName = (iikoCreateConfirmForm.lastName || '').trim();
    newEmployee.staffCode = (iikoCreateConfirmForm.staffCode || '').trim();
    newEmployee.iikoCode = (iikoCreateConfirmForm.iikoCode || '').trim();
    newEmployee.workplaceRestaurantId = iikoCreateConfirmForm.workplaceRestaurantId || '';
    newEmployee.iikoSyncRestaurantId = iikoCreateConfirmForm.syncRestaurantId || '';
}

function closeIikoCreateConfirmModal() {
    if (isCreating.value) {
        return;
    }
    isIikoCreateConfirmModalOpen.value = false;
    resetIikoCreateConfirmForm();
}

async function handleConfirmCreateInIiko() {
    applyIikoCreateConfirmFormToCreateForm();
    isIikoCreateConfirmModalOpen.value = false;
    await handleCreateEmployee({ skipIikoConfirm: true });
}

function displayIikoValue(value) {
    if (value === null || value === undefined || value === '') {
        return '—';
    }
    return String(value);
}

function formatIikoRestaurantList(snapshot) {
    if (!snapshot || typeof snapshot !== 'object') {
        return '—';
    }
    const names = Array.isArray(snapshot.restaurant_names)
        ? snapshot.restaurant_names.filter((name) => typeof name === 'string' && name.trim())
        : [];
    if (names.length) {
        return names.join(', ');
    }
    const ids = Array.isArray(snapshot.restaurant_ids)
        ? snapshot.restaurant_ids
            .map((id) => Number(id))
            .filter((id) => Number.isFinite(id) && id > 0)
        : [];
    if (ids.length) {
        return ids.map((id) => formatRestaurant(id) || `Ресторан #${id}`).join(', ');
    }
    return '—';
}

function resetIikoSyncConfirmForm() {
    iikoSyncConfirmForm.firstName = '';
    iikoSyncConfirmForm.lastName = '';
    iikoSyncConfirmForm.staffCode = '';
    iikoSyncConfirmForm.iikoCode = '';
    iikoSyncConfirmForm.workplaceRestaurantId = '';
    iikoSyncConfirmForm.syncRestaurantId = '';
    iikoSyncConfirmForm.departmentRestaurantIds = [];
}

function resetIikoSyncFieldSources() {
    iikoSyncFieldSources.firstName = 'local';
    iikoSyncFieldSources.lastName = 'local';
    iikoSyncFieldSources.staffCode = 'local';
    iikoSyncFieldSources.iikoCode = 'local';
    iikoSyncFieldSources.workplaceRestaurantId = 'local';
}

function resetIikoSyncFieldEnabled() {
    iikoSyncFieldEnabled.firstName = true;
    iikoSyncFieldEnabled.lastName = true;
    iikoSyncFieldEnabled.staffCode = true;
    iikoSyncFieldEnabled.iikoCode = true;
    iikoSyncFieldEnabled.workplaceRestaurantId = true;
    iikoSyncFieldEnabled.departmentRestaurantIds = true;
}

function resetIikoSyncPreviewState() {
    iikoSyncLocalSnapshot.value = null;
    iikoSyncRemoteSnapshot.value = null;
    iikoSyncPreviewLoading.value = false;
    iikoSyncPreviewError.value = '';
}

function getIikoSyncPreviewRestaurantId() {
    const raw = iikoSyncConfirmForm.syncRestaurantId;
    const parsed = Number(raw);
    if (!Number.isFinite(parsed) || parsed <= 0) {
        return null;
    }
    return parsed;
}

function applyIikoSyncValuesToForm(snapshot) {
    if (!snapshot || typeof snapshot !== 'object') {
        return;
    }
    iikoSyncConfirmForm.firstName = (snapshot.first_name || '').trim();
    iikoSyncConfirmForm.lastName = (snapshot.last_name || '').trim();
    iikoSyncConfirmForm.staffCode = (snapshot.staff_code || '').trim();
    iikoSyncConfirmForm.iikoCode = (snapshot.iiko_code || '').trim();
    const workplaceRestaurantId = snapshot.workplace_restaurant_id
        ? String(snapshot.workplace_restaurant_id)
        : '';
    iikoSyncConfirmForm.workplaceRestaurantId = workplaceRestaurantId;
    iikoSyncConfirmForm.syncRestaurantId = workplaceRestaurantId;

    const snapshotRestaurantIds = Array.isArray(snapshot.restaurant_ids)
        ? snapshot.restaurant_ids
        : [];
    const normalizedIds = [];
    const seenIds = new Set();
    for (const rawId of snapshotRestaurantIds) {
        const parsed = Number(rawId);
        if (!Number.isFinite(parsed) || parsed <= 0 || seenIds.has(parsed)) {
            continue;
        }
        seenIds.add(parsed);
        normalizedIds.push(parsed);
    }
    if (!normalizedIds.length && workplaceRestaurantId) {
        const parsedWorkplaceId = Number(workplaceRestaurantId);
        if (Number.isFinite(parsedWorkplaceId) && parsedWorkplaceId > 0) {
            normalizedIds.push(parsedWorkplaceId);
        }
    }
    iikoSyncConfirmForm.departmentRestaurantIds = normalizedIds;
    if (!iikoSyncConfirmForm.syncRestaurantId && normalizedIds.length) {
        iikoSyncConfirmForm.syncRestaurantId = String(normalizedIds[0]);
    }
}

function applyIikoSyncValuesFromLocal() {
    applyIikoSyncValuesToForm(iikoSyncLocalSnapshot.value);
}

function getIikoSyncSnapshotBySource(source) {
    if (source === 'iiko') {
        return iikoSyncRemoteSnapshot.value;
    }
    return iikoSyncLocalSnapshot.value;
}

function applyIikoSyncFieldSource(fieldKey) {
    const source = iikoSyncFieldSources[fieldKey];
    if (source === 'manual') {
        return;
    }
    const snapshot = getIikoSyncSnapshotBySource(source);
    if (fieldKey === 'firstName') {
        iikoSyncConfirmForm.firstName = (snapshot?.first_name || '').trim();
        return;
    }
    if (fieldKey === 'lastName') {
        iikoSyncConfirmForm.lastName = (snapshot?.last_name || '').trim();
        return;
    }
    if (fieldKey === 'staffCode') {
        iikoSyncConfirmForm.staffCode = (snapshot?.staff_code || '').trim();
        return;
    }
    if (fieldKey === 'iikoCode') {
        iikoSyncConfirmForm.iikoCode = (snapshot?.iiko_code || '').trim();
        return;
    }
    if (fieldKey === 'workplaceRestaurantId') {
        const rawWorkplaceRestaurantId = snapshot?.workplace_restaurant_id;
        iikoSyncConfirmForm.workplaceRestaurantId = rawWorkplaceRestaurantId
            ? String(rawWorkplaceRestaurantId)
            : '';
    }
}

function applyIikoSyncFieldSourcesToForm() {
    applyIikoSyncFieldSource('firstName');
    applyIikoSyncFieldSource('lastName');
    applyIikoSyncFieldSource('staffCode');
    applyIikoSyncFieldSource('iikoCode');
    applyIikoSyncFieldSource('workplaceRestaurantId');
    if (!iikoSyncConfirmForm.syncRestaurantId && iikoSyncConfirmForm.workplaceRestaurantId) {
        iikoSyncConfirmForm.syncRestaurantId = iikoSyncConfirmForm.workplaceRestaurantId;
    }
}

function toggleIikoSyncDepartmentRestaurant(restaurantId, checked) {
    const parsedId = Number(restaurantId);
    if (!Number.isFinite(parsedId) || parsedId <= 0) {
        return;
    }
    if (checked) {
        if (!iikoSyncConfirmForm.departmentRestaurantIds.includes(parsedId)) {
            iikoSyncConfirmForm.departmentRestaurantIds = [
                ...iikoSyncConfirmForm.departmentRestaurantIds,
                parsedId,
            ];
        }
        return;
    }
    iikoSyncConfirmForm.departmentRestaurantIds = iikoSyncConfirmForm.departmentRestaurantIds.filter(
        (item) => Number(item) !== parsedId,
    );
}

function closeIikoSyncConfirmModal() {
    if (syncingEmployeeToIiko.value) {
        return;
    }
    isIikoSyncConfirmModalOpen.value = false;
    resetIikoSyncPreviewState();
    resetIikoSyncConfirmForm();
    resetIikoSyncFieldSources();
    resetIikoSyncFieldEnabled();
}

async function loadIikoSyncPreview(options = {}) {
    const { applyLocalSnapshotToForm = false } = options;
    if (!activeEmployee.value) {
        return;
    }

    preparingIikoSyncPreview.value = true;
    iikoSyncPreviewLoading.value = true;
    iikoSyncPreviewError.value = '';
    iikoSyncRemoteSnapshot.value = null;
    try {
        const syncRestaurantId = getIikoSyncPreviewRestaurantId();
        const preview = await fetchEmployeeIikoSyncPreview(activeEmployee.value.id, {
            sync_restaurant_id: syncRestaurantId || undefined,
        });
        if (preview?.local) {
            iikoSyncLocalSnapshot.value = preview.local;
            if (applyLocalSnapshotToForm) {
                applyIikoSyncValuesFromLocal();
            }
        }
        iikoSyncRemoteSnapshot.value = preview?.iiko || null;
        iikoSyncPreviewError.value = preview?.iiko_error || '';
        applyIikoSyncFieldSourcesToForm();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        iikoSyncPreviewError.value =
            typeof detail === 'string' && detail.trim()
                ? detail
                : 'Не удалось загрузить данные сотрудника из iiko';
    } finally {
        iikoSyncPreviewLoading.value = false;
        preparingIikoSyncPreview.value = false;
    }
}

async function reloadIikoSyncPreview() {
    await loadIikoSyncPreview({ applyLocalSnapshotToForm: false });
}

async function openIikoSyncConfirmModal() {
    if (!activeEmployee.value || !canSyncEmployeeToIiko.value) {
        return;
    }

    resetIikoSyncPreviewState();
    resetIikoSyncConfirmForm();
    resetIikoSyncFieldSources();
    resetIikoSyncFieldEnabled();
    isIikoSyncConfirmModalOpen.value = true;

    const fallbackRestaurantIds = [];
    const seenFallbackRestaurantIds = new Set();
    const activeRestaurantIds = Array.isArray(activeEmployee.value?.restaurant_ids)
        ? activeEmployee.value.restaurant_ids
        : [];
    for (const rawId of activeRestaurantIds) {
        const parsed = Number(rawId);
        if (!Number.isFinite(parsed) || parsed <= 0 || seenFallbackRestaurantIds.has(parsed)) {
            continue;
        }
        seenFallbackRestaurantIds.add(parsed);
        fallbackRestaurantIds.push(parsed);
    }
    const fallbackWorkplaceRestaurantId =
        employeeCard.value?.workplace_restaurant_id || activeEmployee.value?.workplace_restaurant_id || null;
    if (fallbackWorkplaceRestaurantId) {
        const parsedWorkplaceId = Number(fallbackWorkplaceRestaurantId);
        if (Number.isFinite(parsedWorkplaceId) && parsedWorkplaceId > 0 && !seenFallbackRestaurantIds.has(parsedWorkplaceId)) {
            seenFallbackRestaurantIds.add(parsedWorkplaceId);
            fallbackRestaurantIds.push(parsedWorkplaceId);
        }
    }

    const localSnapshotFallback = {
        first_name: employeeCard.value?.first_name || activeEmployee.value?.first_name || '',
        last_name: employeeCard.value?.last_name || activeEmployee.value?.last_name || '',
        position_name: employeeCard.value?.position_name || activeEmployee.value?.position_name || '',
        position_code: employeeCard.value?.position_code || activeEmployee.value?.position_code || '',
        staff_code: employeeCard.value?.staff_code || activeEmployee.value?.staff_code || '',
        iiko_code: employeeCard.value?.iiko_code || activeEmployee.value?.iiko_code || '',
        iiko_id: employeeCard.value?.iiko_id || activeEmployee.value?.iiko_id || '',
        workplace_restaurant_id: fallbackWorkplaceRestaurantId,
        workplace_restaurant_name: formatRestaurant(
            fallbackWorkplaceRestaurantId,
        ),
        department_code: '',
        restaurant_ids: fallbackRestaurantIds,
        restaurant_names: fallbackRestaurantIds.map((id) => formatRestaurant(id) || `Ресторан #${id}`),
        department_codes: [],
    };
    iikoSyncLocalSnapshot.value = localSnapshotFallback;
    applyIikoSyncValuesFromLocal();

    await loadIikoSyncPreview({ applyLocalSnapshotToForm: true });
}

async function handleConfirmSyncEmployeeToIiko() {
    if (!activeEmployee.value || !canSyncEmployeeToIiko.value) {
        return;
    }

    const syncRestaurantRaw =
        iikoSyncConfirmForm.syncRestaurantId ||
        iikoSyncConfirmForm.workplaceRestaurantId ||
        iikoSyncLocalSnapshot.value?.workplace_restaurant_id ||
        employeeCard.value?.workplace_restaurant_id ||
        activeEmployee.value?.workplace_restaurant_id;
    const syncRestaurantId = Number(syncRestaurantRaw);
    if (!Number.isFinite(syncRestaurantId) || syncRestaurantId <= 0) {
        toast.error('Выберите ресторан для синхронизации с iiko.');
        return;
    }

    const payload = {
        add_to_iiko: true,
        iiko_sync_restaurant_id: syncRestaurantId,
    };
    let hasEnabledField = false;

    if (iikoSyncFieldEnabled.firstName) {
        const firstName = (iikoSyncConfirmForm.firstName || '').trim();
        if (!firstName) {
            toast.error('Укажите имя для отправки в iiko или отключите это поле.');
            return;
        }
        payload.first_name = firstName;
        hasEnabledField = true;
    }

    if (iikoSyncFieldEnabled.lastName) {
        const lastName = (iikoSyncConfirmForm.lastName || '').trim();
        if (!lastName) {
            toast.error('Укажите фамилию для отправки в iiko или отключите это поле.');
            return;
        }
        payload.last_name = lastName;
        hasEnabledField = true;
    }

    if (iikoSyncFieldEnabled.staffCode) {
        payload.staff_code = (iikoSyncConfirmForm.staffCode || '').trim() || null;
        hasEnabledField = true;
    }

    if (iikoSyncFieldEnabled.iikoCode) {
        payload.iiko_code = (iikoSyncConfirmForm.iikoCode || '').trim() || null;
        hasEnabledField = true;
    }

    if (iikoSyncFieldEnabled.workplaceRestaurantId) {
        const workplaceRaw = iikoSyncConfirmForm.workplaceRestaurantId;
        if (!workplaceRaw) {
            toast.error('Укажите место работы для отправки в iiko или отключите это поле.');
            return;
        }
        const workplaceRestaurantId = Number(workplaceRaw);
        if (!Number.isFinite(workplaceRestaurantId) || workplaceRestaurantId <= 0) {
            toast.error('Выберите корректное место работы.');
            return;
        }
        payload.workplace_restaurant_id = workplaceRestaurantId;
        hasEnabledField = true;
    }

    if (iikoSyncFieldEnabled.departmentRestaurantIds) {
        const departmentRestaurantIds = [];
        const seenDepartmentRestaurantIds = new Set();
        for (const rawId of iikoSyncConfirmForm.departmentRestaurantIds || []) {
            const parsed = Number(rawId);
            if (!Number.isFinite(parsed) || parsed <= 0 || seenDepartmentRestaurantIds.has(parsed)) {
                continue;
            }
            seenDepartmentRestaurantIds.add(parsed);
            departmentRestaurantIds.push(parsed);
        }
        if (!departmentRestaurantIds.length) {
            toast.error('Выберите хотя бы один ресторан для доступа в iiko или отключите это поле.');
            return;
        }
        payload.iiko_department_restaurant_ids = departmentRestaurantIds;
        hasEnabledField = true;
    }

    if (!hasEnabledField) {
        toast.error('Выберите хотя бы одно поле для отправки в iiko.');
        return;
    }

    syncingEmployeeToIiko.value = true;
    try {
        const updatedCard = await updateStaffEmployee(activeEmployee.value.id, payload);
        if (updatedCard) {
            employeeCard.value = updatedCard;
        }
        closeIikoSyncConfirmModal();
        if (updatedCard?.iiko_sync_error) {
            toast.warning(updatedCard.iiko_sync_error);
        } else {
            toast.success('Сотрудник синхронизирован с iiko');
        }
        if (canViewEmployees.value) {
            await loadEmployees();
            const refreshed = employees.value.find((employee) => employee.id === activeEmployee.value.id);
            if (refreshed) {
                activeEmployee.value = refreshed;
            }
        }
    } catch (error) {
        const detail = error?.response?.data?.detail;
        const detailText = typeof detail === 'string' ? detail : '';
        toast.error(detailText || 'Не удалось синхронизировать сотрудника с iiko');
        console.error(error);
    } finally {
        syncingEmployeeToIiko.value = false;
    }
}

function resetCreateForm() {
    newEmployee.username = '';
    newEmployee.password = '';
    newEmployee.firstName = '';
    newEmployee.middleName = '';
    newEmployee.lastName = '';
    newEmployee.gender = null;
    newEmployee.iikoCode = '';
    newEmployee.staffCode = '';
    applyPhoneInput(newEmployee, '');
    newEmployee.email = '';
    newEmployee.isCisEmployee = false;
    newEmployee.confidentialDataConsent = false;
    newEmployee.roleId = null;
    newEmployee.companyId = null;
    newEmployee.positionId = null;
    newEmployee.workplaceRestaurantId = '';
    newEmployee.rate = '';
    newEmployee.individualRate = '';
    newEmployee.useIndividualRate = false;
    newEmployee.hireDate = '';
    newEmployee.fireDate = '';
    newEmployee.birthDate = '';
    newEmployee.photoKey = '';
    newEmployee.isFormalized = false;
    newEmployee.restaurantIds = [];
    newEmployee.hasFullRestaurantAccess = false;
    newEmployee.addToIiko = false;
    newEmployee.iikoSyncRestaurantId = '';
    newEmployee.createInAdmin = false;
    resetIikoCreateConfirmForm();
}

function toggleRestaurant(id, checked) {
    if (newEmployee.hasFullRestaurantAccess) {
        return;
    }
    if (checked) {
        if (!newEmployee.restaurantIds.includes(id)) {
            newEmployee.restaurantIds.push(id);
        }
    } else {
        const index = newEmployee.restaurantIds.indexOf(id);
        if (index !== -1) {
            newEmployee.restaurantIds.splice(index, 1);
        }
    }
}

function toggleEditRestaurant(id, checked) {
    if (employeeEditForm.hasGlobalAccess) {
        return;
    }
    if (employeeEditForm.hasFullRestaurantAccess) {
        // Convert "all restaurants" access into an explicit list so it can be edited.
        employeeEditForm.hasFullRestaurantAccess = false;
        employeeEditForm.restaurantIds = Array.isArray(restaurants.value)
            ? restaurants.value
                  .map((item) => item?.id)
                  .filter((rid) => Number.isFinite(rid))
            : [];
    }
    if (checked) {
        if (!employeeEditForm.restaurantIds.includes(id)) {
            employeeEditForm.restaurantIds.push(id);
        }
    } else {
        const index = employeeEditForm.restaurantIds.indexOf(id);
        if (index !== -1) {
            employeeEditForm.restaurantIds.splice(index, 1);
        }
    }
    employeeEditRestaurantsTouched.value = true;
}

async function loadRoles() {
    if (!canLoadRoles.value) {
        roles.value = [];
        return;
    }
    try {
        const data = await fetchRoles();
        roles.value = Array.isArray(data) ? data : [];
    } catch (error) {
        const detail = error?.response?.data?.detail;
        if (error?.response?.status === 403) {
            roles.value = [];
        } else {
        toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        }
    }
}

async function loadRestaurants() {
    if (!canLoadRestaurants.value) {
        restaurants.value = [];
        return;
    }
    try {
        const data = await fetchRestaurants();
        restaurants.value = Array.isArray(data) ? data : [];
    } catch (error) {
        const detail = error?.response?.data?.detail;
        if (error?.response?.status === 403) {
            restaurants.value = [];
        } else {
        toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        }
    }
}

async function loadCompanies() {
    if (!canLoadCompanies.value) {
        companies.value = [];
        return;
    }
    try {
        const data = await fetchCompanies();
        companies.value = Array.isArray(data) ? data : [];
    } catch (error) {
        const detail = error?.response?.data?.detail;
        if (error?.response?.status === 403) {
            companies.value = [];
        } else {
        toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        }
    }
}

async function loadPositions() {
    if (!canLoadPositions.value) {
        positionsLoadedFromAccess.value = false;
        if (employees.value.length) {
            derivePositionsFromEmployees(employees.value);
        } else {
            positions.value = [];
        }
        return;
    }
    try {
        const data = await fetchAccessPositions();
        positions.value = Array.isArray(data) ? data : [];
        positionsLoadedFromAccess.value = true;
    } catch (error) {
        const detail = error?.response?.data?.detail;
        if (error?.response?.status === 403) {
            positionsLoadedFromAccess.value = false;
            derivePositionsFromEmployees(employees.value);
        } else {
        toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        }
    }
}

let employeeReferenceDataPromise = null;

async function ensureEmployeeReferenceData() {
    if (employeeReferenceDataPromise) {
        return await employeeReferenceDataPromise;
    }

    employeeReferenceDataPromise = (async () => {
        const tasks = [];
        if (canLoadRestaurants.value && !restaurants.value.length) {
            tasks.push(loadRestaurants());
        }
        if (canLoadCompanies.value && !companies.value.length) {
            tasks.push(loadCompanies());
        }
        if (canLoadRoles.value && !roles.value.length) {
            tasks.push(loadRoles());
        }
        if (canLoadPositions.value && !positionsLoadedFromAccess.value) {
            tasks.push(loadPositions());
        }
        if (!tasks.length) {
            return;
        }
        const results = await Promise.allSettled(tasks);
        for (const result of results) {
            if (result.status === 'rejected') {
                console.error(result.reason);
            }
        }
    })();

    try {
        return await employeeReferenceDataPromise;
    } finally {
        employeeReferenceDataPromise = null;
    }
}

async function handleUpdateEmployee() {
    if (!activeEmployee.value || !canManageEmployees.value) {
        return;
    }

    const wantsFullAccess = employeeEditForm.hasFullRestaurantAccess;
    const username = employeeEditForm.username?.trim() || null;
    const { email, error: emailError } = normalizeEmailForApi(employeeEditForm.email);
    if (emailError) {
        toast.error(emailError);
        return;
    }
    if (
        wantsFullAccess !== employeeEditInitialFullAccess.value &&
        !canEditFullAccess.value
    ) {
        toast.error('Не удалось выполнить операцию');
        return;
    }

    const roleId = canEditRoles.value
        ? employeeEditForm.roleId !== null && employeeEditForm.roleId !== undefined
            ? Number(employeeEditForm.roleId)
            : 0
        : null;
    const companyId =
        employeeEditForm.companyId !== null &&
        employeeEditForm.companyId !== undefined &&
        employeeEditForm.companyId !== ''
            ? Number(employeeEditForm.companyId)
            : null;
    const positionId =
        employeeEditForm.positionId !== null && employeeEditForm.positionId !== undefined
            ? Number(employeeEditForm.positionId)
            : 0;
    const workplaceRestaurantId =
        employeeEditForm.workplaceRestaurantId !== null &&
        employeeEditForm.workplaceRestaurantId !== undefined &&
        employeeEditForm.workplaceRestaurantId !== ''
            ? Number(employeeEditForm.workplaceRestaurantId)
            : 0;

    if (employeeEditForm.workplaceRestaurantId && !Number.isFinite(workplaceRestaurantId)) {
        toast.error('Не удалось выполнить операцию');
        return;
    }

    const restaurantIdsRaw = employeeEditForm.restaurantIds.map((id) => Number(id));
    if (restaurantIdsRaw.some((id) => !Number.isFinite(id))) {
        toast.error('Некорректные рестораны');
        return;
    }
    const restaurantIds = Array.from(new Set(restaurantIdsRaw));

    let rate = null;
    let individualRate = null;
    if (canEditRates.value && !employeeEditForm.rateHidden) {
        if (employeeEditForm.useIndividualRate) {
            const rawRate = employeeEditForm.individualRate;
            if (rawRate === "" || rawRate === null || rawRate === undefined) {
                rate = 0;
                individualRate = 0;
            } else {
                const parsed = Number.parseFloat(String(rawRate).replace(",", "."));
                if (!Number.isFinite(parsed)) {
                    toast.error('Не удалось выполнить операцию');
                    return;
                }
                rate = parsed;
                individualRate = parsed;
            }
        } else if (employeeEditForm.rate !== "" && employeeEditForm.rate !== null) {
            const parsed = Number.parseFloat(String(employeeEditForm.rate).replace(",", "."));
            if (!Number.isFinite(parsed)) {
                toast.error('Не удалось выполнить операцию');
                return;
            }
            rate = parsed;
        }
    }
    const { phone: normalizedPhone, error: phoneError } = normalizePhoneForApi(
        employeeEditForm.phoneNumber,
    );
    if (phoneError) {
        toast.error('Не удалось выполнить операцию');
        return;
    }

    updatingEmployee.value = true;
    try {
        const payload = {
            first_name: employeeEditForm.firstName || null,
            middle_name: employeeEditForm.middleName || null,
            last_name: employeeEditForm.lastName || null,
            gender: employeeEditForm.gender || null,
            staff_code: employeeEditForm.staffCode || null,
            iiko_code: employeeEditForm.iikoCode || null,
            ...(canEditIikoId.value
                ? { iiko_id: employeeEditForm.iikoId || null }
                : {}),
            is_cis_employee: Boolean(employeeEditForm.isCisEmployee),
            is_formalized: Boolean(employeeEditForm.isFormalized),
            confidential_data_consent: Boolean(employeeEditForm.confidentialDataConsent),
            phone_number: normalizedPhone,
            email,
            role_id: canEditRoles.value ? roleId : undefined,
            company_id: companyId ?? undefined,
            position_id: positionId,
            workplace_restaurant_id: workplaceRestaurantId,
            restaurant_ids: restaurantIds,
            ...(employeeEditForm.rateHidden || !canEditRates.value
                ? {}
                : {
                      rate: rate,
                      individual_rate: employeeEditForm.useIndividualRate ? individualRate : null,
                  }),
            hire_date: employeeEditForm.hireDate || null,
            ...(employeeCard.value?.fired ? { fire_date: employeeEditForm.fireDate || null } : {}),
            birth_date: employeeEditForm.birthDate || null,
            photo_key: employeeEditForm.photoKey || null,
        };

        if (!canViewSensitiveStaffFields.value) {
            delete payload.iiko_code;
            delete payload.confidential_data_consent;
            delete payload.role_id;
        }
        if (!canEditIikoId.value) {
            delete payload.iiko_id;
        }

        if (employeeEditForm.password) {
            payload.password = employeeEditForm.password;
        }
        if (rate === null) {
            delete payload.rate;
        }
        const hadRestaurants =
            Array.isArray(employeeEditInitialRestaurantIds.value) &&
            (employeeEditInitialRestaurantIds.value.length > 0 || employeeEditInitialFullAccess.value);
        if (!payload.restaurant_ids || payload.restaurant_ids.length === 0) {
            if (employeeEditRestaurantsTouched.value && hadRestaurants) {
                payload.restaurant_ids = [];
                payload.clear_restaurants = true;
            } else {
                delete payload.restaurant_ids;
            }
        }
        if (!payload.photo_key) {
            payload.photo_key = null;
        }
        if (!payload.staff_code) {
            payload.staff_code = null;
        }
        if (!payload.iiko_code) {
            payload.iiko_code = null;
        }
        if (canEditIikoId.value && !payload.iiko_id) {
            payload.iiko_id = null;
        }
        if (!payload.gender) {
            payload.gender = null;
        }
        if (!payload.hire_date) {
            payload.hire_date = null;
        }
        if (!payload.birth_date) {
            payload.birth_date = null;
        }

        const updatedCard = await updateStaffEmployee(activeEmployee.value.id, payload);
        employeeCard.value = updatedCard;

        const shouldUpdateFullAccess =
            canEditFullAccess.value &&
            wantsFullAccess !== employeeEditInitialFullAccess.value;
            const shouldUpdateUsername = username !== (employeeEditInitialUsername.value?.trim() || null);

        if (shouldUpdateFullAccess || shouldUpdateUsername) {
            try {
                await updateUser(activeEmployee.value.id, {
                    ...(shouldUpdateFullAccess
                        ? { has_full_restaurant_access: wantsFullAccess }
                        : {}),
                    ...(shouldUpdateUsername ? { username } : {}),
                });
                employeeEditInitialFullAccess.value = wantsFullAccess;
                employeeEditInitialUsername.value = username ?? '';
            } catch (error) {
                const detail = error?.response?.data?.detail;
                toast.error(detail || 'Не удалось выполнить операцию');
                console.error(error);
                await loadEmployeeCard(activeEmployee.value.id);
                return;
            }
        }

        toast.success('Данные сотрудника обновлены');
        cancelEditMode();
        if (canViewEmployees.value) {
            await loadEmployees();
            const refreshed = employees.value.find((employee) => employee.id === updatedCard.id);
            if (refreshed) {
                activeEmployee.value = refreshed;
            }
        }
        if (canViewEmployeeChanges.value) {
            await loadEmployeeChangeEvents();
        }
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось выполнить операцию');
        console.error(error);
    } finally {
        updatingEmployee.value = false;
    }
}

async function handleDeleteEmployee() {
    if (!activeEmployee.value || !canManageEmployees.value) {
        return;
    }
    let deleteFromIiko = false;
    if (activeEmployee.value?.iiko_id) {
        deleteFromIiko = window.confirm('Удалить сотрудника также в iiko?');
    }
    deleteFromIikoPending.value = deleteFromIiko;
    deleteCommentText.value = '';
    isDeleteCommentModalOpen.value = true;
}

function closeDeleteCommentModal() {
    if (deletingEmployee.value) {
        return;
    }
    isDeleteCommentModalOpen.value = false;
    deleteCommentText.value = '';
    deleteFromIikoPending.value = false;
}

function openDuplicateInfoModal(info) {
    duplicateEmployeeInfo.value = info || null;
    isDuplicateInfoModalOpen.value = true;
}

function closeDuplicateInfoModal() {
    isDuplicateInfoModalOpen.value = false;
    duplicateEmployeeInfo.value = null;
}

async function submitDeleteEmployee() {
    if (!activeEmployee.value || !canManageEmployees.value) {
        return;
    }
    const comment = deleteCommentText.value.trim();
    if (!comment) {
        toast.error('Комментарий обязателен');
        return;
    }
    deletingEmployee.value = true;
    try {
        await deleteStaffEmployee(activeEmployee.value.id, deleteFromIikoPending.value, comment);
        toast.success('Сотрудник удалён');
        closeDeleteCommentModal();
        closeEmployeeModal();
        await loadEmployees();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось удалить сотрудника');
        console.error(error);
    } finally {
        deletingEmployee.value = false;
    }
}

async function handleRestoreEmployee() {
    if (!activeEmployee.value || !canRestoreEmployees.value) {
        return;
    }
    restoringEmployee.value = true;
    try {
        const updatedCard = await restoreStaffEmployee(activeEmployee.value.id);
        if (updatedCard) {
            employeeCard.value = updatedCard;
        }
        toast.success('Сотрудник восстановлен');
        if (canViewEmployees.value) {
            await loadEmployees();
            const refreshed = employees.value.find((employee) => employee.id === activeEmployee.value.id);
            if (refreshed) {
                activeEmployee.value = refreshed;
            }
        }
        if (canViewEmployeeChanges.value) {
            await loadEmployeeChangeEvents();
        }
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось восстановить сотрудника');
        console.error(error);
    } finally {
        restoringEmployee.value = false;
    }
}

async function handleSyncEmployeeToIiko() {
    if (!activeEmployee.value || !canSyncEmployeeToIiko.value) {
        return;
    }
    await openIikoSyncConfirmModal();
}

async function handleCreateEmployee(options = {}) {
    const skipIikoConfirm = Boolean(options?.skipIikoConfirm);
    if (!canCreateEmployees.value) {
        toast.error('Не удалось выполнить операцию');
        return;
    }

    if (newEmployee.addToIiko && !canSyncEmployeeToIiko.value) {
        toast.error('Недостаточно прав для синхронизации сотрудника с iiko');
        return;
    }

    if (newEmployee.hasFullRestaurantAccess && !canEditFullAccess.value) {
        toast.error('Не удалось выполнить операцию');
        return;
    }

    const firstName = (newEmployee.firstName || '').trim();
    const lastName = (newEmployee.lastName || '').trim();
    const birthDate = newEmployee.birthDate;
    if (!lastName || !firstName || !birthDate) {
        toast.error('Заполните фамилию, имя и дату рождения.');
        return;
    }

    const roleId = canEditRoles.value
        ? newEmployee.roleId !== null && newEmployee.roleId !== undefined && newEmployee.roleId !== ''
            ? Number(newEmployee.roleId)
            : null
        : null;
    if (canEditRoles.value && newEmployee.roleId && !Number.isFinite(roleId)) {
        toast.error('Не удалось выполнить операцию');
        return;
    }

    const companyId =
        newEmployee.companyId !== null && newEmployee.companyId !== undefined && newEmployee.companyId !== ''
            ? Number(newEmployee.companyId)
            : null;
    if (newEmployee.companyId && !Number.isFinite(companyId)) {
        toast.error('Не удалось выполнить операцию');
        return;
    }

    const positionId =
        newEmployee.positionId !== null && newEmployee.positionId !== undefined && newEmployee.positionId !== ''
            ? Number(newEmployee.positionId)
            : null;
    if (newEmployee.positionId && !Number.isFinite(positionId)) {
        toast.error('Не удалось выполнить операцию');
        return;
    }

    if (
        newEmployee.workplaceRestaurantId === null
        || newEmployee.workplaceRestaurantId === undefined
        || newEmployee.workplaceRestaurantId === ''
    ) {
        toast.error('Укажите место работы.');
        return;
    }
    const workplaceRestaurantId = Number(newEmployee.workplaceRestaurantId);
    if (!Number.isFinite(workplaceRestaurantId)) {
        toast.error('Выберите корректное место работы.');
        return;
    }

    let restaurantIds = [];
    if (!newEmployee.hasFullRestaurantAccess) {
        const restaurantIdsRaw = newEmployee.restaurantIds.map((id) => Number(id));
        const hasInvalidRestaurants = restaurantIdsRaw.some((id) => !Number.isFinite(id));
        if (hasInvalidRestaurants) {
            toast.error('Не удалось выполнить операцию');
            return;
        }
        restaurantIds = Array.from(new Set(restaurantIdsRaw));
    }
    let iikoSyncRestaurantId = null;
    let iikoDepartmentRestaurantIds = [];
    if (newEmployee.addToIiko) {
        const rawSyncRestaurantId = newEmployee.iikoSyncRestaurantId || newEmployee.workplaceRestaurantId;
        const parsedSyncRestaurantId = Number(rawSyncRestaurantId);
        if (!Number.isFinite(parsedSyncRestaurantId) || parsedSyncRestaurantId <= 0) {
            toast.error('Выберите ресторан для синхронизации с iiko.');
            return;
        }
        iikoSyncRestaurantId = parsedSyncRestaurantId;

        const sourceIds = newEmployee.hasFullRestaurantAccess
            ? (restaurants.value || []).map((restaurant) => Number(restaurant?.id))
            : restaurantIds.slice();
        sourceIds.push(workplaceRestaurantId);
        const seenIikoDepartmentIds = new Set();
        for (const rawId of sourceIds) {
            const parsed = Number(rawId);
            if (!Number.isFinite(parsed) || parsed <= 0 || seenIikoDepartmentIds.has(parsed)) {
                continue;
            }
            seenIikoDepartmentIds.add(parsed);
            iikoDepartmentRestaurantIds.push(parsed);
        }
        if (!iikoDepartmentRestaurantIds.length) {
            toast.error('Выберите хотя бы один ресторан для доступа в iiko.');
            return;
        }
    }

    let rate = null;
    let individualRate = null;
    if (canEditRates.value) {
        if (newEmployee.useIndividualRate) {
            const rawRate = newEmployee.individualRate;
            if (rawRate === "" || rawRate === null || rawRate === undefined) {
                rate = 0;
                individualRate = 0;
            } else {
                const parsedRate = Number.parseFloat(String(rawRate).replace(",", "."));
                if (!Number.isFinite(parsedRate)) {
                    toast.error('Не удалось выполнить операцию');
                    return;
                }
                rate = parsedRate;
                individualRate = parsedRate;
            }
        } else if (newEmployee.rate !== "" && newEmployee.rate !== null) {
            const parsedRate = Number.parseFloat(String(newEmployee.rate).replace(",", "."));
            if (!Number.isFinite(parsedRate)) {
                toast.error('Не удалось выполнить операцию');
                return;
            }
            rate = parsedRate;
        }
    }
    const { phone: normalizedPhone, error: phoneError } = normalizePhoneForApi(
        newEmployee.phoneNumber,
    );
    if (phoneError) {
        toast.error(phoneError);
        return;
    }
    const username = newEmployee.username?.trim() || null;
    const password = newEmployee.password?.trim() || null;
    const { email, error: emailError } = normalizeEmailForApi(newEmployee.email);
    if (emailError) {
        toast.error(emailError);
        return;
    }
    if (newEmployee.addToIiko && !skipIikoConfirm) {
        syncIikoCreateConfirmFormFromNewEmployee();
        isIikoCreateConfirmModalOpen.value = true;
        return;
    }

    isCreating.value = true;
    try {
        const payload = {
            username,
            password,
            first_name: firstName,
            middle_name: newEmployee.middleName || null,
            last_name: lastName,
            birth_date: birthDate,
            gender: newEmployee.gender || null,
            iiko_code: newEmployee.iikoCode || null,
            staff_code: newEmployee.staffCode?.trim() || null,
            phone_number: normalizedPhone,
            email,
            hire_date: newEmployee.hireDate || undefined,
            fire_date: newEmployee.fireDate || undefined,
            photo_key: newEmployee.photoKey?.trim() || undefined,
            role_id: canEditRoles.value ? roleId ?? undefined : undefined,
            company_id: companyId ?? undefined,
            position_id: positionId ?? undefined,
            workplace_restaurant_id: workplaceRestaurantId ?? undefined,
            restaurant_ids: restaurantIds,
            has_full_restaurant_access: Boolean(newEmployee.hasFullRestaurantAccess),
            is_cis_employee: Boolean(newEmployee.isCisEmployee),
            is_formalized: Boolean(newEmployee.isFormalized),
            confidential_data_consent: Boolean(newEmployee.confidentialDataConsent),
            add_to_iiko: Boolean(newEmployee.addToIiko),
            iiko_sync_restaurant_id: iikoSyncRestaurantId ?? undefined,
            iiko_department_restaurant_ids: iikoDepartmentRestaurantIds,
        };
        if (canEditRates.value && rate !== null) {
            payload.rate = rate;
        }
        if (canEditRates.value && individualRate !== null) {
            payload.individual_rate = individualRate;
        }
        if (!canViewSensitiveStaffFields.value) {
            delete payload.iiko_code;
            delete payload.role_id;
            delete payload.confidential_data_consent;
        }
        const createdUser = await createUser(payload);

        toast.success('Сотрудник создан');
        if (createdUser?.iiko_sync_error) {
            toast.warning(createdUser.iiko_sync_error);
        }
        closeCreateModal();
        await loadEmployees();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        if (await handleDuplicateEmployeeError(detail, { closeCreate: true })) {
            return;
        }
        const detailText = typeof detail === 'string' ? detail : '';
        toast.error(detailText || 'Не удалось выполнить операцию');
        console.error(error);
    } finally {
        isCreating.value = false;
    }
}

watch(
    () => newEmployee.workplaceRestaurantId,
    (value, oldValue) => {
        if (newEmployee.hasFullRestaurantAccess) {
            return;
        }

        const previousWorkplaceId = Number(oldValue);
        if (Number.isFinite(previousWorkplaceId)) {
            newEmployee.restaurantIds = newEmployee.restaurantIds.filter(
                (id) => Number(id) !== previousWorkplaceId,
            );
            if (Number(newEmployee.iikoSyncRestaurantId) === previousWorkplaceId) {
                newEmployee.iikoSyncRestaurantId = '';
            }
        }

        if (!value) {
            return;
        }

        const parsed = Number(value);
        if (!Number.isFinite(parsed)) {
            return;
        }
        if (!newEmployee.restaurantIds.some((id) => Number(id) === parsed)) {
            newEmployee.restaurantIds.push(parsed);
        }
        if (!newEmployee.iikoSyncRestaurantId) {
            newEmployee.iikoSyncRestaurantId = String(parsed);
        }
    },
);

watch(
    () => employeeEditForm.workplaceRestaurantId,
    (value, oldValue) => {
        if (suppressEmployeeEditWorkplaceSync.value) {
            return;
        }

        if (!employeeEditForm.hasGlobalAccess && !employeeEditForm.hasFullRestaurantAccess) {
            const previousWorkplaceId =
                oldValue !== null && oldValue !== undefined && oldValue !== ''
                    ? Number(oldValue)
                    : Number.NaN;
            if (Number.isFinite(previousWorkplaceId)) {
                employeeEditForm.restaurantIds = employeeEditForm.restaurantIds.filter(
                    (id) => Number(id) !== previousWorkplaceId,
                );
                employeeEditRestaurantsTouched.value = true;
            }
        }

        if (!value) {
            return;
        }

        const parsed = Number(value);
        if (!Number.isFinite(parsed)) {
            return;
        }

        if (!employeeEditForm.hasGlobalAccess && !employeeEditForm.hasFullRestaurantAccess) {
            if (!employeeEditForm.restaurantIds.some((id) => Number(id) === parsed)) {
                employeeEditForm.restaurantIds.push(parsed);
                employeeEditRestaurantsTouched.value = true;
            }
        }

        const restaurant = restaurants.value.find((item) => item?.id === parsed);
        const companyId = restaurant?.company_id;
        if (Number.isFinite(companyId)) {
            employeeEditForm.companyId = String(companyId);
        }
    },
    { flush: 'sync' },
);

watch(
    () => newEmployee.positionId,
    () => {
        syncNewEmployeeRateWithPosition();
    },
);

watch(
    () => employeeEditForm.positionId,
    () => {
        syncEmployeeEditRateWithPosition();
    },
);

watch(
    () => newEmployee.phoneInput,
    (value) => {
        const sanitized = sanitizePhoneInput(value);
        if (newEmployee.phoneNumber !== sanitized) {
            newEmployee.phoneNumber = sanitized;
        }
        const formatted = formatPhoneForInput(sanitized);
        if (formatted !== value) {
            newEmployee.phoneInput = formatted;
        }
    },
    { flush: 'sync' },
);

watch(
    () => employeeEditForm.phoneInput,
    (value) => {
        const sanitized = sanitizePhoneInput(value);
        if (employeeEditForm.phoneNumber !== sanitized) {
            employeeEditForm.phoneNumber = sanitized;
        }
        const formatted = formatPhoneForInput(sanitized);
        if (formatted !== value) {
            employeeEditForm.phoneInput = formatted;
        }
    },
    { flush: 'sync' },
);

watch(
    () => newEmployee.useIndividualRate,
    (useIndividualRate) => {
        if (useIndividualRate) {
            if (!newEmployee.individualRate && newEmployee.rate) {
                newEmployee.individualRate = newEmployee.rate;
            }
        } else {
            newEmployee.individualRate = '';
            syncNewEmployeeRateWithPosition();
        }
    },
);

watch(
    () => employeeEditForm.useIndividualRate,
    (useIndividualRate) => {
        if (useIndividualRate) {
            if (!employeeEditForm.individualRate && employeeEditForm.rate) {
                employeeEditForm.individualRate = employeeEditForm.rate;
            }
        } else {
            employeeEditForm.individualRate = '';
            syncEmployeeEditRateWithPosition();
        }
    },
);

watch(
    () => newEmployee.hasFullRestaurantAccess,
    (fullAccess) => {
        if (fullAccess) {
            const restaurantIds = Array.isArray(restaurants.value)
                ? restaurants.value.map((restaurant) => restaurant.id)
                : [];
            newEmployee.restaurantIds = restaurantIds;
        } else {
            newEmployee.restaurantIds = [];
        }
    },
);

watch(
    () => newEmployee.createInAdmin,
    (enabled) => {
        if (!enabled) {
            newEmployee.username = '';
            newEmployee.password = '';
        }
    },
);

watch(
    () => [
        iikoSyncFieldSources.firstName,
        iikoSyncFieldSources.lastName,
        iikoSyncFieldSources.staffCode,
        iikoSyncFieldSources.iikoCode,
        iikoSyncFieldSources.workplaceRestaurantId,
    ],
    () => {
        applyIikoSyncFieldSourcesToForm();
    },
);

watch(
    () => iikoSyncConfirmForm.syncRestaurantId,
    (value) => {
        const parsed = Number(value);
        if (!Number.isFinite(parsed) || parsed <= 0) {
            return;
        }
        if (iikoSyncConfirmForm.departmentRestaurantIds.includes(parsed)) {
            return;
        }
        iikoSyncConfirmForm.departmentRestaurantIds = [
            ...iikoSyncConfirmForm.departmentRestaurantIds,
            parsed,
        ];
    },
);

watch(
    () => canSyncEmployeeToIiko.value,
    (allowed) => {
        if (allowed) {
            return;
        }
        newEmployee.addToIiko = false;
        if (isIikoCreateConfirmModalOpen.value) {
            closeIikoCreateConfirmModal();
        }
        if (isIikoSyncConfirmModalOpen.value) {
            closeIikoSyncConfirmModal();
        }
    },
    { immediate: true },
);

watch(
    () => employeeEditForm.hasFullRestaurantAccess,
    (fullAccess) => {
        if (fullAccess) {
            const restaurantIds = Array.isArray(restaurants.value)
                ? restaurants.value.map((restaurant) => restaurant.id)
                : [];
            employeeEditForm.restaurantIds = restaurantIds;
        } else {
            employeeEditForm.restaurantIds = [];
        }
    },
);



watch(
    defaultRestaurantFilter,
    (value) => {
        if (!selectedRestaurantFilter.value && value) {
            selectedRestaurantFilter.value = value;
        }
    },
    { immediate: true },
);

watch(restaurants, (list) => {
    const restaurantIds = Array.isArray(list)
        ? list.map((restaurant) => restaurant.id)
        : [];
    if (newEmployee.hasFullRestaurantAccess) {
        newEmployee.restaurantIds = restaurantIds;
    }
    if (employeeEditForm.hasFullRestaurantAccess) {
        employeeEditForm.restaurantIds = restaurantIds;
    }
    if (selectedRestaurantFilter.value) {
        const exists = restaurantIds.some((id) => String(id) === selectedRestaurantFilter.value);
        if (!exists) {
            selectedRestaurantFilter.value = '';
        }
    }
    if (!selectedRestaurantFilter.value && defaultRestaurantFilter.value) {
        selectedRestaurantFilter.value = defaultRestaurantFilter.value;
    }
});

watch(positionOptions, (options) => {
    if (!selectedPositionFilters.value.length) {
        return;
    }
    const allowed = new Set(options.map((option) => String(option.value)));
    selectedPositionFilters.value = selectedPositionFilters.value.filter((id) =>
        allowed.has(String(id)),
    );
});

watch(
    () => activeEmployee.value?.id,
    async (id) => {
        resetEmployeeAttendancesState();
        resetEmployeeTrainingsState();
        if (!id) {
            resetUserPermissionState();
            employeeChangeEvents.value = [];
            employeeChangeEventsError.value = '';
            return;
        }
        resetUserPermissionState();
        if (activeModalTab.value === 'trainings') {
            await autoLoadTrainingTab();
        }
        if (activeModalTab.value === 'permissions' && canManageUserPermissions.value) {
            await autoLoadPermissionTab();
        }
    },
);

watch(
    () => canViewEmployees.value,
    async (allowed) => {
        if (allowed) {
            await loadEmployees({ includeReferences: true });
            if (!referencesLoadedFromBootstrap.value) {
                void ensureEmployeeReferenceData();
            }
            if (modalOnly.value || route.query.employeeId) {
                await openEmployeeFromQuery();
            }
        } else {
            employees.value = [];
            positions.value = [];
            positionsLoadedFromAccess.value = false;
            referencesLoadedFromBootstrap.value = false;
            closeEmployeeModal();
            closeCreateModal();
            closeAttendanceEditModal();
        }
    },
    { immediate: true },
);

watch(
    () => route.query.employeeId,
    () => {
        if (modalOnly.value || route.query.employeeId) {
            openEmployeeFromQuery();
        }
    },
    { immediate: true },
);

watch(
    () => canManageUserPermissions.value,
    async (allowed) => {
        if (!allowed && activeModalTab.value === 'permissions') {
            activeModalTab.value = 'info';
        }
        if (allowed && activeModalTab.value === 'permissions' && activeEmployee.value) {
            await autoLoadPermissionTab();
        }
        if (!allowed) {
            resetUserPermissionState();
        }
    },
    { immediate: true },
);

watch(
    () => canViewEmployeeChanges.value,
    async (allowed) => {
        if (allowed && activeEmployee.value && activeModalTab.value === 'changes') {
            await autoLoadChangesTab();
        }
        if (!allowed) {
            employeeChangeEvents.value = [];
            employeeChangeEventsError.value = '';
        }
    },
    { immediate: true },
);

const debouncedLoadEmployees = useDebounce(loadEmployees, 400);
const debouncedFilterLoadEmployees = useDebounce(() => loadEmployees(), 120);

watch(includeFired, () => {
    if (canViewEmployees.value) {
        debouncedFilterLoadEmployees();
    }
});

watch(selectedRestaurantFilter, () => {
    if (canViewEmployees.value) {
        debouncedFilterLoadEmployees();
    }
});

watch(
    search,
    () => {
        if (!canViewEmployees.value) {
            return;
        }
        debouncedLoadEmployees();
    },
    { flush: 'post' },
);

watch(
    () => activeModalTab.value,
    async (tab) => {
        if (tab !== 'info' && isEditMode.value) {
            cancelEditMode();
        }
        if (tab !== 'trainings') {
            closeTrainingAssignmentModal();
        }
        if (tab === 'shifts' && activeEmployee.value) {
            await autoLoadShiftTab();
        }
        if (tab === 'trainings' && activeEmployee.value) {
            await autoLoadTrainingTab();
        }
        if (tab === 'permissions' && activeEmployee.value && canManageUserPermissions.value) {
            await autoLoadPermissionTab();
        }
        if (tab === 'documents' && activeEmployee.value && canViewDocuments.value) {
            await autoLoadDocumentsTab();
        }
        if (tab === 'finance' && activeEmployee.value) {
            await autoLoadFinanceTab();
        }
        if (tab === 'changes' && activeEmployee.value && canViewEmployeeChanges.value) {
            await autoLoadChangesTab();
        }
    },
);

onBeforeUnmount(() => {
    if (employeesLoadAbortController) {
        employeesLoadAbortController.abort();
        employeesLoadAbortController = null;
    }
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/employees-page' as *;
</style>
