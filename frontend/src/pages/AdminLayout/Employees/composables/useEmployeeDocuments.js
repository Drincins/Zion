import { computed, reactive, ref } from 'vue';
import { useToast } from 'vue-toastification';
import {
    createCisDocumentRecord,
    createMedicalCheckRecord,
    deleteCisDocumentRecord,
    deleteMedicalCheckRecord,
    fetchCisDocumentTypes,
    fetchEmployeeCard,
    fetchMedicalCheckTypes,
    updateCisDocumentRecord,
    updateMedicalCheckRecord,
    uploadCisDocumentAttachment,
} from '@/api';

export function useEmployeeDocuments({
    activeEmployee,
    employeeCard,
    canViewDocuments,
}) {
    const toast = useToast();

    const medicalCheckRecords = ref([]);
    const cisDocumentRecords = ref([]);
    const medicalCheckTypes = ref([]);
    const cisDocumentTypes = ref([]);
    const medicalCheckTypesLoading = ref(false);
    const cisDocumentTypesLoading = ref(false);
    const documentsLoading = ref(false);
    const medicalForm = reactive({
        id: null,
        medicalCheckTypeId: null,
        passedAt: '',
        comment: '',
    });
    const cisDocumentForm = reactive({
        id: null,
        cisDocumentTypeId: null,
        number: '',
        issuedAt: '',
        expiresAt: '',
        issuer: '',
        attachmentUrl: '',
        comment: '',
    });
    const isMedicalFormOpen = ref(false);
    const isMedicalBulkMode = ref(false);
    const isCisFormOpen = ref(false);
    const savingMedicalRecord = ref(false);
    const savingCisDocument = ref(false);
    const uploadingCisAttachment = ref(false);
    const deletingMedicalRecordId = ref(null);
    const deletingCisDocumentId = ref(null);

    const medicalCheckTypeOptions = computed(() =>
        medicalCheckTypes.value
            .map((type) => ({ value: String(type.id), label: type.name }))
            .sort((a, b) => a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' })),
    );

    const cisDocumentTypeOptions = computed(() =>
        cisDocumentTypes.value
            .map((type) => ({ value: String(type.id), label: type.name }))
            .sort((a, b) => a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' })),
    );

    function resetMedicalForm() {
        medicalForm.id = null;
        medicalForm.medicalCheckTypeId = null;
        medicalForm.passedAt = '';
        medicalForm.comment = '';
    }

    function resetCisDocumentForm() {
        cisDocumentForm.id = null;
        cisDocumentForm.cisDocumentTypeId = null;
        cisDocumentForm.number = '';
        cisDocumentForm.issuedAt = '';
        cisDocumentForm.expiresAt = '';
        cisDocumentForm.issuer = '';
        cisDocumentForm.attachmentUrl = '';
        cisDocumentForm.comment = '';
    }

    function startCreateMedicalRecord() {
        isMedicalBulkMode.value = false;
        resetMedicalForm();
        isMedicalFormOpen.value = true;
    }

    function startCreateMedicalRecordsBulk() {
        resetMedicalForm();
        isMedicalBulkMode.value = true;
        isMedicalFormOpen.value = true;
    }

    function startCreateCisDocument() {
        resetCisDocumentForm();
        isCisFormOpen.value = true;
    }

    function startEditMedicalRecord(record) {
        if (!record) return;
        isMedicalBulkMode.value = false;
        isMedicalFormOpen.value = true;
        medicalForm.id = record.id ?? null;
        medicalForm.medicalCheckTypeId = record.medical_check_type?.id
            ? String(record.medical_check_type.id)
            : null;
        medicalForm.passedAt = record.passed_at || '';
        medicalForm.comment = record.comment || '';
    }

    function startEditCisDocument(record) {
        if (!record) return;
        isCisFormOpen.value = true;
        cisDocumentForm.id = record.id ?? null;
        cisDocumentForm.cisDocumentTypeId = record.cis_document_type?.id
            ? String(record.cis_document_type.id)
            : null;
        cisDocumentForm.number = record.number || '';
        cisDocumentForm.issuedAt = record.issued_at || '';
        cisDocumentForm.expiresAt = record.expires_at || '';
        cisDocumentForm.issuer = record.issuer || '';
        cisDocumentForm.attachmentUrl = record.attachment_url || '';
        cisDocumentForm.comment = record.comment || '';
    }

    function cancelMedicalForm() {
        isMedicalFormOpen.value = false;
        savingMedicalRecord.value = false;
        isMedicalBulkMode.value = false;
        resetMedicalForm();
    }

    function cancelCisDocumentForm() {
        isCisFormOpen.value = false;
        savingCisDocument.value = false;
        resetCisDocumentForm();
    }

    function normalizeOptional(value) {
        if (value === null || value === undefined) {
            return null;
        }
        if (typeof value === 'string') {
            const trimmed = value.trim();
            return trimmed || null;
        }
        return value;
    }

    async function loadMedicalCheckTypes() {
        if (!canViewDocuments.value || medicalCheckTypesLoading.value) {
            return;
        }
        medicalCheckTypesLoading.value = true;
        try {
            const data = await fetchMedicalCheckTypes();
            if (Array.isArray(data?.items)) {
                medicalCheckTypes.value = data.items;
            } else if (Array.isArray(data)) {
                medicalCheckTypes.value = data;
            } else {
                medicalCheckTypes.value = [];
            }
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            medicalCheckTypesLoading.value = false;
        }
    }

    async function loadCisDocumentTypes() {
        if (!canViewDocuments.value || cisDocumentTypesLoading.value) {
            return;
        }
        cisDocumentTypesLoading.value = true;
        try {
            const data = await fetchCisDocumentTypes();
            if (Array.isArray(data?.items)) {
                cisDocumentTypes.value = data.items;
            } else if (Array.isArray(data)) {
                cisDocumentTypes.value = data;
            } else {
                cisDocumentTypes.value = [];
            }
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            cisDocumentTypesLoading.value = false;
        }
    }

    function syncEmployeeDocumentsFromCard(data) {
        medicalCheckRecords.value = Array.isArray(data?.medical_checks)
            ? data.medical_checks
            : [];
        cisDocumentRecords.value = Array.isArray(data?.cis_documents)
            ? data.cis_documents
            : [];
    }

    async function refreshEmployeeDocuments() {
        if (!activeEmployee.value || !canViewDocuments.value) {
            return;
        }
        documentsLoading.value = true;
        try {
            const data = await fetchEmployeeCard(activeEmployee.value.id);
            employeeCard.value = data;
            syncEmployeeDocumentsFromCard(data);

            if (medicalForm.id && !medicalCheckRecords.value.some((item) => item.id === medicalForm.id)) {
                cancelMedicalForm();
            }
            if (cisDocumentForm.id && !cisDocumentRecords.value.some((item) => item.id === cisDocumentForm.id)) {
                cancelCisDocumentForm();
            }
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            documentsLoading.value = false;
        }
    }

    async function handleSaveMedicalRecord() {
        if (!activeEmployee.value) {
            toast.error('Не выбран сотрудник');
            return;
        }

        if (isMedicalBulkMode.value) {
            await handleSaveAllMedicalRecords();
            return;
        }

        if (!medicalForm.medicalCheckTypeId) {
            toast.error('Выберите тип анализа');
            return;
        }
        if (!medicalForm.passedAt) {
            toast.error('Укажите дату прохождения');
            return;
        }

        savingMedicalRecord.value = true;
        try {
            const payload = {
                medical_check_type_id: Number(medicalForm.medicalCheckTypeId),
                passed_at: medicalForm.passedAt,
                comment: normalizeOptional(medicalForm.comment),
            };

            if (medicalForm.id) {
                await updateMedicalCheckRecord(medicalForm.id, payload);
                toast.success('Запись медкнижки обновлена');
            } else {
                await createMedicalCheckRecord({ user_id: activeEmployee.value.id, ...payload });
                toast.success('Запись медкнижки добавлена');
            }
            await refreshEmployeeDocuments();
            cancelMedicalForm();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            savingMedicalRecord.value = false;
        }
    }

    async function handleSaveAllMedicalRecords() {
        if (!medicalForm.passedAt) {
            toast.error('Укажите дату прохождения');
            return;
        }
        const allTypes = (medicalCheckTypes.value || []).filter((type) => type && type.id);
        if (!allTypes.length) {
            toast.error('Нет доступных типов анализов');
            return;
        }
        const existingKeys = new Set(
            medicalCheckRecords.value.map(
                (record) => `${record.medical_check_type?.id || ''}:${record.passed_at || ''}`,
            ),
        );
        const targets = allTypes.filter(
            (type) => !existingKeys.has(`${type.id}:${medicalForm.passedAt}`),
        );
        if (!targets.length) {
            toast.error('Все типы уже добавлены на выбранную дату');
            return;
        }

        savingMedicalRecord.value = true;
        try {
            const failed = [];
            for (const type of targets) {
                try {
                    await createMedicalCheckRecord({
                        user_id: activeEmployee.value.id,
                        medical_check_type_id: Number(type.id),
                        passed_at: medicalForm.passedAt,
                        comment: normalizeOptional(medicalForm.comment),
                    });
                } catch (error) {
                    failed.push(type.name || `Тип #${type.id}`);
                    console.error(error);
                }
            }
            await refreshEmployeeDocuments();
            cancelMedicalForm();
            const successCount = targets.length - failed.length;
            if (successCount > 0) {
                const suffix = targets.length > 1 ? ` (${successCount} из ${targets.length})` : '';
                toast.success(`Записи медкнижек добавлены${suffix}`);
            }
            if (failed.length) {
                toast.error(`Не удалось добавить: ${failed.join(', ')}`);
            }
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            savingMedicalRecord.value = false;
        }
    }

    async function handleSaveCisDocument() {
        if (!activeEmployee.value) {
            toast.error('Не удалось выполнить операцию');
            return;
        }
        if (!cisDocumentForm.cisDocumentTypeId) {
            toast.error('Не удалось выполнить операцию');
            return;
        }
        if (!cisDocumentForm.issuedAt) {
            toast.error('Не удалось выполнить операцию');
            return;
        }

        savingCisDocument.value = true;
        try {
            const payload = {
                cis_document_type_id: Number(cisDocumentForm.cisDocumentTypeId),
                number: normalizeOptional(cisDocumentForm.number),
                issued_at: cisDocumentForm.issuedAt,
                expires_at: cisDocumentForm.expiresAt || null,
                issuer: normalizeOptional(cisDocumentForm.issuer),
                comment: normalizeOptional(cisDocumentForm.comment),
                attachment_url: normalizeOptional(cisDocumentForm.attachmentUrl),
            };

            if (cisDocumentForm.id) {
                await updateCisDocumentRecord(cisDocumentForm.id, payload);
                toast.success('Документ обновлен');
            } else {
                await createCisDocumentRecord({ user_id: activeEmployee.value.id, ...payload });
                toast.success('Документ добавлен');
            }
            await refreshEmployeeDocuments();
            cancelCisDocumentForm();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            savingCisDocument.value = false;
        }
    }

    async function handleDeleteMedicalRecord(recordId) {
        if (!recordId) {
            return;
        }
        deletingMedicalRecordId.value = recordId;
        try {
            await deleteMedicalCheckRecord(recordId);
            toast.success('Запись удалена');
            if (medicalForm.id === recordId) {
                cancelMedicalForm();
            }
            await refreshEmployeeDocuments();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            deletingMedicalRecordId.value = null;
        }
    }

    async function handleDeleteCisDocument(recordId) {
        if (!recordId) {
            return;
        }
        deletingCisDocumentId.value = recordId;
        try {
            await deleteCisDocumentRecord(recordId);
            toast.success('Запись удалена');
            if (cisDocumentForm.id === recordId) {
                cancelCisDocumentForm();
            }
            await refreshEmployeeDocuments();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            deletingCisDocumentId.value = null;
        }
    }

    async function handleUploadCisAttachment(file) {
        if (!activeEmployee.value || !file) {
            return;
        }
        uploadingCisAttachment.value = true;
        try {
            const response = await uploadCisDocumentAttachment(activeEmployee.value.id, file);
            cisDocumentForm.attachmentUrl = response?.attachment_key || response?.attachment_url || '';
            toast.success('Файл загружен');
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось загрузить файл');
            console.error(error);
        } finally {
            uploadingCisAttachment.value = false;
        }
    }

    function resetEmployeeDocumentsState() {
        medicalCheckRecords.value = [];
        cisDocumentRecords.value = [];
        medicalCheckTypes.value = [];
        cisDocumentTypes.value = [];
        documentsLoading.value = false;
        medicalCheckTypesLoading.value = false;
        cisDocumentTypesLoading.value = false;
        cancelMedicalForm();
        cancelCisDocumentForm();
    }

    return {
        medicalCheckRecords,
        cisDocumentRecords,
        medicalCheckTypes,
        cisDocumentTypes,
        medicalCheckTypesLoading,
        cisDocumentTypesLoading,
        documentsLoading,
        medicalForm,
        cisDocumentForm,
        isMedicalFormOpen,
        isMedicalBulkMode,
        isCisFormOpen,
        savingMedicalRecord,
        savingCisDocument,
        uploadingCisAttachment,
        deletingMedicalRecordId,
        deletingCisDocumentId,
        medicalCheckTypeOptions,
        cisDocumentTypeOptions,
        startCreateMedicalRecord,
        startCreateMedicalRecordsBulk,
        startCreateCisDocument,
        startEditMedicalRecord,
        startEditCisDocument,
        cancelMedicalForm,
        cancelCisDocumentForm,
        loadMedicalCheckTypes,
        loadCisDocumentTypes,
        refreshEmployeeDocuments,
        handleSaveMedicalRecord,
        handleDeleteMedicalRecord,
        handleSaveCisDocument,
        handleDeleteCisDocument,
        handleUploadCisAttachment,
        syncEmployeeDocumentsFromCard,
        resetEmployeeDocumentsState,
    };
}

