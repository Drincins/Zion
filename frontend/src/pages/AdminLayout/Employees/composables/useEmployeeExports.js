import { ref } from 'vue';
import { useToast } from 'vue-toastification';
import { exportEmployeesListXlsx } from '@/api';
import { extractApiErrorMessage } from '@/utils/apiErrors';
import { downloadBlobFile } from '@/utils/downloadBlobFile';

export function useEmployeeExports({
    canDownloadEmployeesList,
    getSortedEmployees,
    resolveEmployeesForExport,
    employeeColumnOptions,
    selectedEmployeeColumns,
}) {
    const toast = useToast();

    const employeesListExporting = ref(false);

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

        const resolvedList = typeof resolveEmployeesForExport === 'function'
            ? await resolveEmployeesForExport()
            : getSortedEmployees?.();
        const list = Array.isArray(resolvedList) ? resolvedList : [];
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

    return {
        employeesListExporting,
        downloadEmployeesList,
    };
}
