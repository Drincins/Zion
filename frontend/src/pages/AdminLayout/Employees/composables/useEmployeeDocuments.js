import { computed, reactive, ref } from 'vue';
import { useToast } from 'vue-toastification';
import {
    createEmploymentDocumentRecord,
    createCisDocumentRecord,
    createMedicalCheckRecord,
    deleteEmploymentDocumentRecord,
    deleteCisDocumentRecord,
    deleteMedicalCheckRecord,
    fetchCisDocumentRecords,
    fetchCisDocumentTypes,
    fetchEmploymentDocumentRecords,
    fetchMedicalCheckRecords,
    fetchMedicalCheckTypes,
    updateEmploymentDocumentRecord,
    updateCisDocumentRecord,
    updateMedicalCheckRecord,
    uploadEmploymentDocumentAttachment,
    uploadCisDocumentAttachment,
} from '@/api';

const EMPLOYMENT_DOCUMENT_OPTIONS = [
    { value: 'employment_order', label: 'Приказ о приеме на работу' },
    { value: 'employment_contract', label: 'Договор' },
];

export function useEmployeeDocuments({
    activeEmployee,
    canViewDocuments,
    canViewMedicalChecks,
    canViewCisDocuments,
}) {
    const toast = useToast();

    const medicalCheckRecords = ref([]);
    const cisDocumentRecords = ref([]);
    const employmentDocumentRecords = ref([]);
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
    const employmentDocumentForm = reactive({
        id: null,
        documentKind: null,
        issuedAt: '',
        attachmentUrl: '',
        comment: '',
    });
    const isMedicalFormOpen = ref(false);
    const isMedicalBulkMode = ref(false);
    const isCisFormOpen = ref(false);
    const isEmploymentFormOpen = ref(false);
    const savingMedicalRecord = ref(false);
    const savingCisDocument = ref(false);
    const savingEmploymentDocument = ref(false);
    const uploadingCisAttachment = ref(false);
    const uploadingEmploymentAttachment = ref(false);
    const deletingMedicalRecordId = ref(null);
    const deletingCisDocumentId = ref(null);
    const deletingEmploymentDocumentId = ref(null);

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

    const employmentDocumentRows = computed(() =>
        EMPLOYMENT_DOCUMENT_OPTIONS.map((item) => {
            const existing = employmentDocumentRecords.value.find(
                (record) => record.document_kind === item.value,
            );
            if (existing) {
                return {
                    ...existing,
                    document_name: existing.document_name || item.label,
                    exists: true,
                };
            }
            return {
                id: `placeholder-${item.value}`,
                document_kind: item.value,
                document_name: item.label,
                issued_at: '',
                comment: '',
                attachment_url: '',
                exists: false,
            };
        }),
    );

    const employmentDocumentFormLabel = computed(() => {
        const option = EMPLOYMENT_DOCUMENT_OPTIONS.find(
            (item) => item.value === employmentDocumentForm.documentKind,
        );
        return option?.label || 'Документ оформления';
    });

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

    function resetEmploymentDocumentForm() {
        employmentDocumentForm.id = null;
        employmentDocumentForm.documentKind = null;
        employmentDocumentForm.issuedAt = '';
        employmentDocumentForm.attachmentUrl = '';
        employmentDocumentForm.comment = '';
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

    function startEditEmploymentDocument(record) {
        if (!record?.document_kind) {
            return;
        }
        isEmploymentFormOpen.value = true;
        employmentDocumentForm.id = record.exists ? record.id ?? null : null;
        employmentDocumentForm.documentKind = record.document_kind;
        employmentDocumentForm.issuedAt = record.issued_at || '';
        employmentDocumentForm.attachmentUrl = record.attachment_url || '';
        employmentDocumentForm.comment = record.comment || '';
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

    function cancelEmploymentDocumentForm() {
        isEmploymentFormOpen.value = false;
        savingEmploymentDocument.value = false;
        resetEmploymentDocumentForm();
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
        if (!canViewMedicalChecks.value || medicalCheckTypesLoading.value) {
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
        if (!canViewCisDocuments.value || cisDocumentTypesLoading.value) {
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
            medicalCheckRecords.value = [];
            cisDocumentRecords.value = [];
            employmentDocumentRecords.value = [];
            return;
        }
        documentsLoading.value = true;
        try {
            const [medicalData, cisData, employmentData] = await Promise.all([
                canViewMedicalChecks.value
                    ? fetchMedicalCheckRecords({ user_id: activeEmployee.value.id })
                    : Promise.resolve({ items: [] }),
                canViewCisDocuments.value
                    ? fetchCisDocumentRecords({ user_id: activeEmployee.value.id })
                    : Promise.resolve({ items: [] }),
                fetchEmploymentDocumentRecords({ user_id: activeEmployee.value.id }),
            ]);

            medicalCheckRecords.value = Array.isArray(medicalData?.items)
                ? medicalData.items
                : [];
            cisDocumentRecords.value = Array.isArray(cisData?.items)
                ? cisData.items
                : [];
            employmentDocumentRecords.value = Array.isArray(employmentData?.items)
                ? employmentData.items
                : [];

            if (medicalForm.id && !medicalCheckRecords.value.some((item) => item.id === medicalForm.id)) {
                cancelMedicalForm();
            }
            if (cisDocumentForm.id && !cisDocumentRecords.value.some((item) => item.id === cisDocumentForm.id)) {
                cancelCisDocumentForm();
            }
            if (
                employmentDocumentForm.id &&
                !employmentDocumentRecords.value.some((item) => item.id === employmentDocumentForm.id)
            ) {
                cancelEmploymentDocumentForm();
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

    async function handleSaveEmploymentDocument() {
        if (!activeEmployee.value) {
            toast.error('Не выбран сотрудник');
            return;
        }
        if (!employmentDocumentForm.documentKind) {
            toast.error('Не выбран документ');
            return;
        }

        savingEmploymentDocument.value = true;
        try {
            const payload = {
                document_kind: employmentDocumentForm.documentKind,
                issued_at: employmentDocumentForm.issuedAt || null,
                comment: normalizeOptional(employmentDocumentForm.comment),
                attachment_url: normalizeOptional(employmentDocumentForm.attachmentUrl),
            };

            if (employmentDocumentForm.id) {
                await updateEmploymentDocumentRecord(employmentDocumentForm.id, payload);
                toast.success('Документ оформления обновлен');
            } else {
                await createEmploymentDocumentRecord({
                    user_id: activeEmployee.value.id,
                    ...payload,
                });
                toast.success('Документ оформления добавлен');
            }

            await refreshEmployeeDocuments();
            cancelEmploymentDocumentForm();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            savingEmploymentDocument.value = false;
        }
    }

    async function handleDeleteEmploymentDocument(recordId) {
        if (!recordId) {
            return;
        }
        deletingEmploymentDocumentId.value = recordId;
        try {
            await deleteEmploymentDocumentRecord(recordId);
            toast.success('Документ удален');
            if (employmentDocumentForm.id === recordId) {
                cancelEmploymentDocumentForm();
            }
            await refreshEmployeeDocuments();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            deletingEmploymentDocumentId.value = null;
        }
    }

    async function handleUploadEmploymentAttachment(file) {
        if (!activeEmployee.value || !file) {
            return;
        }
        uploadingEmploymentAttachment.value = true;
        try {
            const response = await uploadEmploymentDocumentAttachment(activeEmployee.value.id, file);
            employmentDocumentForm.attachmentUrl = response?.attachment_key || response?.attachment_url || '';
            toast.success('Файл загружен');
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось загрузить файл');
            console.error(error);
        } finally {
            uploadingEmploymentAttachment.value = false;
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
        employmentDocumentRecords.value = [];
        medicalCheckTypes.value = [];
        cisDocumentTypes.value = [];
        documentsLoading.value = false;
        medicalCheckTypesLoading.value = false;
        cisDocumentTypesLoading.value = false;
        cancelMedicalForm();
        cancelCisDocumentForm();
        cancelEmploymentDocumentForm();
    }

    return {
        medicalCheckRecords,
        cisDocumentRecords,
        employmentDocumentRecords,
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
    };
}
