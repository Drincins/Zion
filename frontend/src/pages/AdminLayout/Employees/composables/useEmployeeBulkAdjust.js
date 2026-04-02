import { computed, reactive, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';
import { createPayrollAdjustmentsBulk, fetchAllEmployees, fetchEmployees } from '@/api';
import { useDebounce } from '@/composables/useDebounce';
import { useMultiSelect } from '@/composables/useMultiSelect';

export function useEmployeeBulkAdjust({
    restaurantOptions,
    timesheetOptions,
    formatDateInput,
    resolveEmployeeId,
    formatFullNameShort,
    employeeMatchesWorkplace,
    loadPayrollAdjustmentTypes,
    loadTimesheetOptions,
}) {
    const toast = useToast();
    const { toggleMultiValue } = useMultiSelect();

    const isBulkAdjustModalOpen = ref(false);
    const bulkAdjustLoading = ref(false);
    const bulkAdjustForm = reactive({
        restaurantId: '',
        date: '',
        adjustmentTypeId: '',
        comment: '',
    });
    const bulkCommonAmountEnabled = ref(false);
    const bulkCommonAmount = ref('');
    const bulkAdjustResult = reactive({
        createdCount: 0,
        skipped: [],
        errors: [],
    });
    const bulkAdjustEmployees = ref([]);
    const bulkSearchQuery = ref('');
    const bulkSearchResults = ref([]);
    const bulkSearchLoading = ref(false);
    const bulkSearchOnlyFired = ref(false);
    const bulkKnownRestaurantEmployees = ref([]);
    const bulkFilters = reactive({
        workplaceId: '',
        positionIds: [],
        subdivisionIds: [],
        onlyFormalized: false,
        onlyCis: false,
    });
    const isBulkPositionPanelOpen = ref(false);
    const isBulkSubdivisionPanelOpen = ref(false);
    const bulkSortBy = ref('name');
    const bulkSortDir = ref('asc');
    const isBulkFillModalOpen = ref(false);

    const bulkAdjustResultSummary = computed(() => {
        if (!bulkAdjustResult) return null;
        return {
            created: bulkAdjustResult.createdCount || 0,
            skipped: bulkAdjustResult.skipped?.length || 0,
            errors: bulkAdjustResult.errors?.length || 0,
        };
    });

    const bulkPositionSelectionLabel = computed(() => {
        const count = bulkFilters.positionIds.length;
        if (!count) return 'все';
        return `выбрано: ${count}`;
    });

    const bulkSubdivisionSelectionLabel = computed(() => {
        const count = bulkFilters.subdivisionIds.length;
        if (!count) return 'все';
        return `выбрано: ${count}`;
    });

    const bulkPositionOptions = computed(() => {
        const map = new Map();
        const selectedSubIds = new Set(bulkFilters.subdivisionIds || []);
        const filterBySubdivision = selectedSubIds.size > 0;

        const consider = (subId) => {
            if (!filterBySubdivision) return true;
            return subId && selectedSubIds.has(String(subId));
        };

        const addOption = (id, name, subId) => {
            if (!id || !name) return;
            if (!consider(subId)) return;
            map.set(String(id), name);
        };

        for (const employee of bulkKnownRestaurantEmployees.value.concat(bulkAdjustEmployees.value)) {
            const id = employee.positionId ?? employee.position_id ?? null;
            const name = employee.positionName ?? employee.position_name ?? employee.position ?? '';
            const subId =
                employee.subdivisionId ??
                employee.restaurant_subdivision_id ??
                employee.position?.restaurant_subdivision_id ??
                employee.subdivisionId ??
                null;
            addOption(id, name, subId);
        }

        if (map.size === 0 && Array.isArray(timesheetOptions.value?.positions)) {
            for (const position of timesheetOptions.value.positions) {
                if (position?.id) {
                    const label = position.name || `ID ${position.id}`;
                    addOption(position.id, label, position.restaurant_subdivision_id || null);
                }
            }
        }

        return Array.from(map.entries()).map(([value, label]) => ({ value, label }));
    });

    const bulkSubdivisionOptions = computed(() => {
        const map = new Map();
        for (const employee of bulkKnownRestaurantEmployees.value.concat(bulkAdjustEmployees.value)) {
            const id = employee.subdivisionId ?? employee.restaurant_subdivision_id ?? null;
            const name =
                employee.subdivisionName ??
                employee.restaurant_subdivision_name ??
                ((id ? `Подразделение ${id}` : '') || '');
            if (id && name) {
                map.set(String(id), name);
            }
        }

        if (map.size === 0 && Array.isArray(timesheetOptions.value?.subdivisions)) {
            for (const subdivision of timesheetOptions.value.subdivisions) {
                if (subdivision?.id) {
                    const label = subdivision.name || `Подразделение ${subdivision.id}`;
                    map.set(String(subdivision.id), label);
                }
            }
        }

        return Array.from(map.entries()).map(([value, label]) => ({ value, label }));
    });

    const workplaceFilterOptions = computed(() => {
        return [
            { value: '', label: 'Все' },
            ...restaurantOptions.value.map((item) => ({
                value: String(item.value),
                label: item.label,
            })),
        ];
    });

    const bulkDisplayedEmployees = computed(() => {
        const list = [...bulkAdjustEmployees.value];
        const dir = bulkSortDir.value === 'desc' ? -1 : 1;

        return list.sort((a, b) => {
            let aVal = '';
            let bVal = '';

            if (bulkSortBy.value === 'staff') {
                aVal = a.staffCode || '';
                bVal = b.staffCode || '';
            } else if (bulkSortBy.value === 'position') {
                aVal = a.positionName || '';
                bVal = b.positionName || '';
            } else if (bulkSortBy.value === 'subdivision') {
                aVal = a.subdivisionName || '';
                bVal = b.subdivisionName || '';
            } else if (bulkSortBy.value === 'amount') {
                const aNum = Number(a.amount);
                const bNum = Number(b.amount);
                return (aNum - bNum) * dir;
            } else {
                aVal = a.name || '';
                bVal = b.name || '';
            }

            return aVal.localeCompare(bVal, 'ru', { sensitivity: 'base', numeric: true }) * dir;
        });
    });

    const bulkStaffCodeToName = computed(() => {
        const map = new Map();
        for (const row of bulkAdjustEmployees.value) {
            const staffCode = (row?.staffCode || '').trim();
            if (!staffCode) {
                continue;
            }
            if (row?.name) {
                map.set(staffCode, row.name);
            }
        }
        return map;
    });

    function bulkResultItemLabel(item) {
        const directName = String(item?.full_name || '').trim();
        const staffCode = (item?.staff_code || '').trim();
        if (directName && staffCode) {
            return `${directName} (${staffCode})`;
        }
        if (directName) {
            return directName;
        }
        if (!staffCode) {
            return '—';
        }
        const name = bulkStaffCodeToName.value.get(staffCode);
        return name ? `${name} (${staffCode})` : staffCode;
    }

    function bulkRowStatusLabel(status) {
        if (status === 'created') return 'Создано';
        if (status === 'skipped') return 'Пропущено';
        if (status === 'error') return 'Ошибка';
        if (status === 'pending') return 'Отправка';
        return status || '';
    }

    function resetBulkAdjustForm() {
        bulkAdjustForm.restaurantId = '';
        const today = new Date();
        bulkAdjustForm.date = formatDateInput(today);
        bulkAdjustForm.adjustmentTypeId = '';
        bulkAdjustForm.comment = '';
        bulkCommonAmountEnabled.value = false;
        bulkCommonAmount.value = '';
        bulkAdjustResult.createdCount = 0;
        bulkAdjustResult.skipped = [];
        bulkAdjustResult.errors = [];
        bulkAdjustEmployees.value = [];
        bulkSearchResults.value = [];
        bulkSearchQuery.value = '';
        bulkSearchOnlyFired.value = false;
        bulkKnownRestaurantEmployees.value = [];
        bulkFilters.workplaceId = '';
        bulkFilters.positionIds = [];
        bulkFilters.subdivisionIds = [];
        bulkFilters.onlyFormalized = false;
        bulkFilters.onlyCis = false;
        bulkSortBy.value = 'name';
        bulkSortDir.value = 'asc';
        isBulkFillModalOpen.value = false;
    }

    function openBulkAdjustModal() {
        resetBulkAdjustForm();
        if (typeof loadPayrollAdjustmentTypes === 'function') {
            loadPayrollAdjustmentTypes();
        }
        if (typeof loadTimesheetOptions === 'function') {
            loadTimesheetOptions();
        }
        isBulkAdjustModalOpen.value = true;
    }

    function closeBulkAdjustModal() {
        isBulkAdjustModalOpen.value = false;
        bulkAdjustLoading.value = false;
    }

    function openBulkFillModal() {
        isBulkFillModalOpen.value = true;
    }

    function closeBulkFillModal() {
        isBulkFillModalOpen.value = false;
    }

    watch(
        () => bulkCommonAmountEnabled.value,
        (enabled) => {
            if (!enabled) {
                return;
            }
            for (const row of bulkAdjustEmployees.value) {
                row.amount = bulkCommonAmount.value;
            }
        }
    );

    watch(
        () => bulkCommonAmount.value,
        (value) => {
            if (!bulkCommonAmountEnabled.value) {
                return;
            }
            for (const row of bulkAdjustEmployees.value) {
                row.amount = value;
            }
        }
    );

    function mapEmployeeToBulkRow(user, options = {}) {
        const userId = resolveEmployeeId(user);
        return {
            userId,
            staffCode: user.staff_code || user.staffCode || '',
            name: formatFullNameShort(user),
            amount: bulkCommonAmountEnabled.value ? bulkCommonAmount.value : '',
            enabled: true,
            resultStatus: null,
            resultReason: '',
            positionId: user.position_id ?? user.positionId ?? null,
            positionName: user.position_name ?? user.position?.name ?? user.positionName ?? null,
            subdivisionId:
                user.restaurant_subdivision_id ??
                user.position?.restaurant_subdivision_id ??
                user.subdivisionId ??
                null,
            subdivisionName:
                user.restaurant_subdivision_name ??
                user.position?.restaurant_subdivision?.name ??
                user.subdivisionName ??
                null,
            formalized: Boolean(user.is_formalized ?? user.formalized),
            cis: Boolean(user.is_cis_employee ?? user.cis),
            workplaceId:
                user.workplace_restaurant_id ??
                user.workplaceId ??
                user.workplace_restaurant?.id ??
                null,
            forceVisible: Boolean(options.forceVisible),
        };
    }

    function addBulkEmployee(user) {
        const userId = resolveEmployeeId(user);
        if (!user || !userId) return;
        const exists = bulkAdjustEmployees.value.some((row) => row.userId === userId);
        if (exists) return;
        bulkAdjustEmployees.value.push(mapEmployeeToBulkRow(user, { forceVisible: true }));
    }

    function removeBulkEmployee(userId) {
        bulkAdjustEmployees.value = bulkAdjustEmployees.value.filter((row) => row.userId !== userId);
    }

    function fillBulkEmployeesFromFilters() {
        const workplaceId = bulkFilters.workplaceId;
        const rid = Number(workplaceId);
        const hasWorkplace = Number.isFinite(rid);

        const posSet = new Set((bulkFilters.positionIds || []).map((id) => String(id)));
        const subSet = new Set((bulkFilters.subdivisionIds || []).map((id) => String(id)));

        const matchesFilters = (row) => {
            if (hasWorkplace && !employeeMatchesWorkplace(row, rid)) {
                return false;
            }
            if (bulkFilters.onlyFormalized && !(row.is_formalized ?? row.formalized)) {
                return false;
            }
            if (bulkFilters.onlyCis && !(row.is_cis_employee ?? row.cis)) {
                return false;
            }
            const posId = row.position_id ?? row.positionId ?? null;
            if (posSet.size && !posSet.has(String(posId || ''))) {
                return false;
            }
            const subId =
                row.restaurant_subdivision_id ??
                row.position?.restaurant_subdivision_id ??
                row.subdivisionId ??
                null;
            if (subSet.size && !subSet.has(String(subId || ''))) {
                return false;
            }
            return true;
        };

        const applyList = (list) => {
            const matched = (list || []).filter((employee) => matchesFilters(employee));
            bulkKnownRestaurantEmployees.value = matched;
            bulkAdjustEmployees.value = matched.map((employee) => mapEmployeeToBulkRow(employee));
            closeBulkFillModal();
        };

        bulkSearchLoading.value = true;
        fetchAllEmployees({ include_fired: true })
            .then((data) => {
                const list = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];
                applyList(list);
            })
            .catch((error) => {
                console.error(error);
                toast.error('Не удалось загрузить сотрудников');
            })
            .finally(() => {
                bulkSearchLoading.value = false;
            });
    }

    const debouncedBulkSearch = useDebounce(async (query) => {
        if (!query || query.trim().length < 2) {
            bulkSearchResults.value = [];
            return;
        }
        bulkSearchLoading.value = true;
        try {
            const params = { q: query.trim(), limit: 50 };
            if (bulkSearchOnlyFired.value) {
                params.include_fired = true;
                params.only_fired = true;
            }
            const data = await fetchEmployees(params);
            const list = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];
            bulkSearchResults.value = list;
        } catch (error) {
            console.error(error);
            bulkSearchResults.value = [];
        } finally {
            bulkSearchLoading.value = false;
        }
    }, 400);

    function handleBulkSearch(value) {
        bulkSearchQuery.value = value;
        debouncedBulkSearch(value);
    }

    watch(
        () => bulkSearchOnlyFired.value,
        () => {
            bulkSearchResults.value = [];
            if (bulkSearchQuery.value && bulkSearchQuery.value.trim().length >= 2) {
                debouncedBulkSearch(bulkSearchQuery.value);
            }
        }
    );

    function handleBulkPositionAll(checked) {
        if (checked) {
            bulkFilters.positionIds = [];
        }
    }

    function toggleBulkPosition(value, checked) {
        const normalized = String(value);
        toggleMultiValue(bulkFilters.positionIds, normalized, checked);
    }

    function handleBulkSubdivisionAll(checked) {
        if (checked) {
            bulkFilters.subdivisionIds = [];
        }
    }

    function toggleBulkSubdivision(value, checked) {
        const normalized = String(value);
        toggleMultiValue(bulkFilters.subdivisionIds, normalized, checked);
    }

    function toggleBulkSort(key) {
        if (bulkSortBy.value === key) {
            bulkSortDir.value = bulkSortDir.value === 'asc' ? 'desc' : 'asc';
        } else {
            bulkSortBy.value = key;
            bulkSortDir.value = 'asc';
        }
    }

    function toggleBulkPositionPanel() {
        isBulkPositionPanelOpen.value = !isBulkPositionPanelOpen.value;
    }

    function toggleBulkSubdivisionPanel() {
        isBulkSubdivisionPanelOpen.value = !isBulkSubdivisionPanelOpen.value;
    }

    async function handleBulkAdjust() {
        if (!bulkAdjustForm.date || !bulkAdjustForm.adjustmentTypeId) {
            toast.error('Заполните все обязательные поля');
            return;
        }

        for (const row of bulkAdjustEmployees.value) {
            row.resultStatus = null;
            row.resultReason = '';
        }

        const formRestaurantId = Number(bulkAdjustForm.restaurantId);
        const hasFormRestaurant = Number.isFinite(formRestaurantId);

        let commonAmountValue = null;
        if (bulkCommonAmountEnabled.value) {
            const parsed = Number.parseFloat(String(bulkCommonAmount.value).replace(',', '.'));
            if (!Number.isFinite(parsed)) {
                toast.error('Укажите корректную сумму для всех');
                return;
            }
            commonAmountValue = parsed;
        }

        bulkAdjustResult.createdCount = 0;
        bulkAdjustResult.skipped = [];
        bulkAdjustResult.errors = [];

        const localErrors = [];
        const rowsByRestaurant = new Map();
        const pendingStaffCodes = new Set();

        for (const row of bulkDisplayedEmployees.value) {
            if (!row.enabled) continue;
            const staffCode = (row.staffCode || '').trim();
            if (!staffCode) {
                localErrors.push({
                    staff_code: '',
                    full_name: row.name || '',
                    reason: `${row.name || 'Сотрудник'}: нет табельного кода`,
                });
                row.resultStatus = 'error';
                row.resultReason = 'Нет табельного кода';
                continue;
            }

            const amountSource = bulkCommonAmountEnabled.value ? commonAmountValue : row.amount;
            const amountNum = Number.parseFloat(String(amountSource).replace(',', '.'));
            if (!Number.isFinite(amountNum)) {
                localErrors.push({ staff_code: staffCode, full_name: row.name || '', reason: 'Некорректная сумма' });
                row.resultStatus = 'error';
                row.resultReason = 'Некорректная сумма';
                continue;
            }

            const rowRestaurantId = Number(row.workplaceId);
            const targetRestaurantId = hasFormRestaurant ? formRestaurantId : rowRestaurantId;
            if (!Number.isFinite(targetRestaurantId)) {
                localErrors.push({ staff_code: staffCode, full_name: row.name || '', reason: 'Не указан ресторан' });
                row.resultStatus = 'error';
                row.resultReason = 'Не указан ресторан';
                continue;
            }

            if (!rowsByRestaurant.has(targetRestaurantId)) {
                rowsByRestaurant.set(targetRestaurantId, []);
            }
            rowsByRestaurant.get(targetRestaurantId).push({ staff_code: staffCode, amount: amountNum });
            pendingStaffCodes.add(staffCode);
            row.resultStatus = 'pending';
        }

        if (!rowsByRestaurant.size) {
            bulkAdjustResult.errors = localErrors;
            toast.error('Нет строк для отправки: заполните суммы и отметьте сотрудников');
            return;
        }

        const rowByStaffCode = new Map();
        for (const row of bulkAdjustEmployees.value) {
            const staffCode = (row?.staffCode || '').trim();
            if (staffCode) {
                rowByStaffCode.set(staffCode, row);
            }
        }

        bulkAdjustLoading.value = true;
        try {
            let createdTotal = 0;
            const allSkipped = [];
            const allErrors = [...localErrors];

            for (const [restaurantId, rows] of rowsByRestaurant.entries()) {
                const payload = {
                    restaurant_id: Number(restaurantId),
                    period_from: bulkAdjustForm.date,
                    period_to: bulkAdjustForm.date,
                    date: bulkAdjustForm.date,
                    adjustment_type_id: Number(bulkAdjustForm.adjustmentTypeId),
                    comment: bulkAdjustForm.comment || null,
                    rows,
                    dry_run: false,
                };
                try {
                    const result = await createPayrollAdjustmentsBulk(payload);
                    createdTotal += result?.created_count || 0;
                    if (Array.isArray(result?.skipped)) {
                        allSkipped.push(...result.skipped);
                    }
                    if (Array.isArray(result?.errors)) {
                        allErrors.push(...result.errors);
                    }
                } catch (error) {
                    const detail = error?.response?.data;
                    const message =
                        detail?.detail ||
                        detail?.message ||
                        (typeof detail === 'string' ? detail : null) ||
                        error?.message ||
                        'Не удалось выполнить операцию';
                    for (const row of rows) {
                        const staffCode = String(row?.staff_code || '').trim();
                        const sourceRow = rowByStaffCode.get?.(staffCode);
                        allErrors.push({
                            staff_code: staffCode,
                            full_name: sourceRow?.name || '',
                            reason: message,
                        });
                    }
                }
            }

            bulkAdjustResult.createdCount = createdTotal;
            bulkAdjustResult.skipped = allSkipped;
            bulkAdjustResult.errors = allErrors;

            const skippedCodes = new Set();
            const errorCodes = new Set();
            for (const item of allSkipped) {
                const staffCode = (item?.staff_code || '').trim();
                if (!staffCode) continue;
                skippedCodes.add(staffCode);
                const row = rowByStaffCode.get(staffCode);
                if (row) {
                    row.resultStatus = 'skipped';
                    row.resultReason = item.reason || 'Пропущено';
                }
            }
            for (const item of allErrors) {
                const staffCode = (item?.staff_code || '').trim();
                if (!staffCode) continue;
                errorCodes.add(staffCode);
                const row = rowByStaffCode.get(staffCode);
                if (row) {
                    row.resultStatus = 'error';
                    row.resultReason = item.reason || 'Ошибка';
                }
            }

            for (const staffCode of pendingStaffCodes) {
                if (skippedCodes.has(staffCode) || errorCodes.has(staffCode)) {
                    continue;
                }
                const row = rowByStaffCode.get(staffCode);
                if (row) {
                    row.resultStatus = 'created';
                    row.resultReason = '';
                }
            }

            toast.success(`Создано записей: ${bulkAdjustResult.createdCount}`);
        } catch (error) {
            const detail = error?.response?.data;
            const message =
                detail?.detail ||
                detail?.message ||
                (typeof detail === 'string' ? detail : null) ||
                error?.message ||
                'Не удалось выполнить операцию';
            toast.error(message);
        } finally {
            bulkAdjustLoading.value = false;
        }
    }

    return {
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
    };
}
