export function useMultiSelect() {
    function toggleMultiValue(list = [], value, checked) {
        if (!Array.isArray(list)) {
            return;
        }
        const idx = list.indexOf(value);
        if (checked) {
            if (idx === -1) {
                list.push(value);
            }
            return;
        }
        if (idx >= 0) {
            list.splice(idx, 1);
        }
    }

    function countSelectedValues(selectedValues = [], allowedValues = []) {
        if (!Array.isArray(selectedValues) || !Array.isArray(allowedValues)) {
            return 0;
        }
        if (!allowedValues.length || !selectedValues.length) {
            return 0;
        }
        const allowedSet = new Set(allowedValues);
        return selectedValues.filter((value) => allowedSet.has(value)).length;
    }

    function keepAllowedValues(selectedValues = [], allowedValues = []) {
        if (!Array.isArray(selectedValues) || !Array.isArray(allowedValues)) {
            return [];
        }
        const allowedSet = new Set(allowedValues);
        return selectedValues.filter((value) => allowedSet.has(value));
    }

    function buildSelectionLabel({
        totalCount = 0,
        selectedCount = 0,
        noneLabel = 'Нет данных',
        allLabel = 'Все',
        emptyLabel = 'Не выбрано',
        selectedPrefix = 'Выбрано',
        emptyMeansAll = false,
        fullMeansAll = false,
    } = {}) {
        if (!totalCount) {
            return noneLabel;
        }
        if (emptyMeansAll && selectedCount === 0) {
            return allLabel;
        }
        if (fullMeansAll && selectedCount === totalCount) {
            return allLabel;
        }
        if (selectedCount === 0) {
            return emptyLabel;
        }
        return `${selectedPrefix}: ${selectedCount}`;
    }

    return {
        toggleMultiValue,
        countSelectedValues,
        keepAllowedValues,
        buildSelectionLabel,
    };
}
