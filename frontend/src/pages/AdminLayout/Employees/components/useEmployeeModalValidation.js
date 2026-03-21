import { computed, watch } from 'vue';
import { useForm } from 'vee-validate';

function isEqualValue(left, right) {
    if (Number.isNaN(left) && Number.isNaN(right)) {
        return true;
    }
    return left === right;
}

export function useEmployeeModalValidation({ isOpen, sourceModel, validationSchema, onSubmit }) {
    const fieldNames = Object.keys(sourceModel.value || {});

    const getSourceValues = () => {
        const values = {};
        fieldNames.forEach((fieldName) => {
            values[fieldName] = sourceModel.value[fieldName];
        });
        return values;
    };

    const { errors, values, setFieldValue, handleSubmit, resetForm } = useForm({
        validationSchema,
        initialValues: getSourceValues(),
    });

    fieldNames.forEach((fieldName) => {
        watch(
            () => sourceModel.value[fieldName],
            (nextValue) => {
                if (!isEqualValue(values[fieldName], nextValue)) {
                    setFieldValue(fieldName, nextValue, false);
                }
            },
        );

        watch(
            () => values[fieldName],
            (nextValue) => {
                if (!isEqualValue(sourceModel.value[fieldName], nextValue)) {
                    sourceModel.value[fieldName] = nextValue;
                }
            },
        );
    });

    watch(
        () => isOpen.value,
        () => {
            resetForm({
                values: getSourceValues(),
                errors: {},
                touched: {},
            });
        },
        { immediate: true },
    );

    function bindField(fieldName) {
        return computed({
            get: () => values[fieldName],
            set: (nextValue) => {
                setFieldValue(fieldName, nextValue);
            },
        });
    }

    function getFieldError(fieldName) {
        return errors.value[fieldName] || '';
    }

    const handleValidatedSubmit = handleSubmit((formValues) => {
        Object.assign(sourceModel.value, formValues);
        onSubmit(formValues);
    });

    return {
        bindField,
        getFieldError,
        handleValidatedSubmit,
    };
}
