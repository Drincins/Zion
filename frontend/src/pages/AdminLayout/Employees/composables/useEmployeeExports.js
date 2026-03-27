import { reactive, ref } from 'vue';
import { useToast } from 'vue-toastification';
import { exportEmployeesListXlsx, exportPayrollRegister } from '@/api';
import { extractApiErrorMessage } from '@/utils/apiErrors';
import { downloadBlobFile } from '@/utils/downloadBlobFile';

export function useEmployeeExports({
    canExportPayroll,
    canDownloadEmployeesList,
    getSortedEmployees,
    employeeColumnOptions,
    selectedEmployeeColumns,
}) {
    const toast = useToast();

    const isPayrollExportModalOpen = ref(false);
    const payrollExporting = ref(false);
    const employeesListExporting = ref(false);

    const payrollExportForm = reactive({
        dateFrom: '',
        dateTo: '',
        companyId: '',
        restaurantId: '',
        userId: '',
        salaryPercent: '100',
    });

    function openPayrollExportModal() {
        if (!canExportPayroll?.value) {
            return;
        }
        isPayrollExportModalOpen.value = true;
    }

    function closePayrollExportModal() {
        isPayrollExportModalOpen.value = false;
        payrollExporting.value = false;
    }

    function getEmployeesExportColumns() {
        const allColumns = employeeColumnOptions.value || [];
        const visible =
            Array.isArray(selectedEmployeeColumns.value) && selectedEmployeeColumns.value.length
                ? selectedEmployeeColumns.value
                : allColumns.map((column) => column.id);
        const visibleSet = new Set(visible);
        return allColumns.filter((column) => visibleSet.has(column.id));
    }

    async function downloadEmployeesList() {
        if (!canDownloadEmployeesList.value) {
            return;
        }

        const list = Array.isArray(getSortedEmployees?.()) ? getSortedEmployees() : [];
        if (!list.length) {
            toast.error('Нет сотрудников для выгрузки');
            return;
        }

        const columns = getEmployeesExportColumns();
        const columnIds = columns.map((column) => column.id).filter(Boolean);
        const userIds = list
            .map((employee) => Number(employee?.id))
            .filter((id) => Number.isFinite(id));

        if (!userIds.length) {
            toast.error('Нет сотрудников для выгрузки');
            return;
        }

        employeesListExporting.value = true;
        try {
            const blob = await exportEmployeesListXlsx({
                user_ids: userIds,
                column_ids: columnIds,
            });
            const today = new Date();
            const dateLabel = [
                today.getFullYear(),
                String(today.getMonth() + 1).padStart(2, '0'),
                String(today.getDate()).padStart(2, '0'),
            ].join('-');
            downloadBlobFile(blob, `employees_${dateLabel}.xlsx`);
            toast.success('Выгрузка сформирована');
        } catch (error) {
            toast.error(extractApiErrorMessage(error, 'Не удалось выполнить операцию'));
            console.error(error);
        } finally {
            employeesListExporting.value = false;
        }
    }

    async function handleExportPayroll() {
        if (!canExportPayroll?.value) {
            return;
        }
        if (!payrollExportForm.dateFrom || !payrollExportForm.dateTo) {
            toast.error('Укажите период для выгрузки');
            return;
        }

        if (payrollExportForm.dateFrom > payrollExportForm.dateTo) {
            toast.error('Дата "с" должна быть меньше или равна дате "по"');
            return;
        }

        const params = {
            date_from: payrollExportForm.dateFrom,
            date_to: payrollExportForm.dateTo,
        };

        if (payrollExportForm.companyId) {
            const parsed = Number(payrollExportForm.companyId);
            if (!Number.isFinite(parsed)) {
                toast.error('Некорректная компания');
                return;
            }
            params.company_id = parsed;
        }

        if (payrollExportForm.restaurantId) {
            const parsed = Number(payrollExportForm.restaurantId);
            if (!Number.isFinite(parsed)) {
                toast.error('Некорректный ресторан');
                return;
            }
            params.restaurant_id = parsed;
        }

        if (payrollExportForm.userId) {
            const parsed = Number(payrollExportForm.userId);
            if (!Number.isFinite(parsed)) {
                toast.error('Некорректный сотрудник');
                return;
            }
            params.user_ids = [parsed];
        }

        if (payrollExportForm.salaryPercent !== '' && payrollExportForm.salaryPercent !== null) {
            const parsed = Number(payrollExportForm.salaryPercent);
            if (!Number.isFinite(parsed) || parsed < 0 || parsed > 100) {
                toast.error('Процент оклада должен быть от 0 до 100');
                return;
            }
            params.salary_percent = parsed;
        }

        payrollExporting.value = true;
        try {
            const blob = await exportPayrollRegister(params);
            const rangeLabel =
                payrollExportForm.dateFrom === payrollExportForm.dateTo
                    ? payrollExportForm.dateFrom
                    : `${payrollExportForm.dateFrom}_${payrollExportForm.dateTo}`;
            downloadBlobFile(blob, `payroll_${rangeLabel}.xlsx`);
            toast.success('Выгрузка сформирована');
            closePayrollExportModal();
        } catch (error) {
            toast.error(extractApiErrorMessage(error, 'Не удалось выполнить операцию'));
            console.error(error);
        } finally {
            payrollExporting.value = false;
        }
    }

    return {
        isPayrollExportModalOpen,
        payrollExporting,
        employeesListExporting,
        payrollExportForm,
        openPayrollExportModal,
        closePayrollExportModal,
        downloadEmployeesList,
        handleExportPayroll,
    };
}
