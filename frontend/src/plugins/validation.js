import { configure, defineRule } from 'vee-validate';
import {
    email,
    integer,
    max,
    max_value,
    min,
    min_value,
    numeric,
    required,
} from '@vee-validate/rules';

const validationRules = {
    required,
    email,
    min,
    max,
    numeric,
    integer,
    min_value,
    max_value,
};

const validationMessages = {
    required: 'Это поле обязательно для заполнения.',
    email: 'Введите корректный адрес электронной почты.',
    min: 'Значение слишком короткое.',
    max: 'Значение слишком длинное.',
    numeric: 'Допустимы только цифры.',
    integer: 'Допустимы только целые числа.',
    min_value: 'Значение меньше допустимого минимума.',
    max_value: 'Значение превышает допустимый максимум.',
};

export function setupValidation() {
    Object.entries(validationRules).forEach(([ruleName, ruleFn]) => {
        defineRule(ruleName, ruleFn);
    });

    configure({
        validateOnBlur: true,
        validateOnChange: true,
        validateOnInput: false,
        validateOnModelUpdate: true,
        generateMessage: (context) =>
            validationMessages[context.rule?.name] ||
            `Поле "${context.field || 'поле'}" заполнено некорректно.`,
    });
}
