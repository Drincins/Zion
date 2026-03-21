<template>
    <div class="checklist-portal__question-control">
        <div v-if="isYesNo" class="checklist-portal__yesno">
            <button
                type="button"
                :class="['checklist-portal__chip', 'is-yes', answer.response_value === 'Да' && 'is-active']"
                @click="setAnswer('Да')"
            >
                Да
            </button>
            <button
                type="button"
                :class="['checklist-portal__chip', 'is-no', answer.response_value === 'Нет' && 'is-active']"
                @click="setAnswer('Нет')"
            >
                Нет
            </button>
            <button
                v-if="!question.required"
                type="button"
                :class="['checklist-portal__chip', 'is-skip', answer.skipped && 'is-active']"
                @click="toggleSkip"
            >
                Пропустить
            </button>
        </div>

        <div v-else-if="isScale" class="checklist-portal__scale">
            <div class="checklist-portal__scale-label">Оценка (1-{{ scaleMax }})</div>
            <div class="checklist-portal__scale-grid">
                <button
                    v-for="num in scaleMax"
                    :key="num"
                    type="button"
                    :class="[
                        'checklist-portal__chip',
                        String(num) === answer.response_value && 'is-active',
                    ]"
                    @click="setAnswer(String(num))"
                >
                    {{ num }}
                </button>
                <button
                    v-if="!question.required"
                    type="button"
                    :class="['checklist-portal__chip', 'is-skip', answer.skipped && 'is-active']"
                    @click="toggleSkip"
                >
                    Пропустить
                </button>
            </div>
        </div>

        <div v-else>
            <input
                v-if="isShortText"
                :value="responseValue"
                class="checklist-portal__input"
                type="text"
                placeholder="Введите ответ"
                @input="onResponseInput"
            />
            <textarea
                v-else
                :value="responseValue"
                class="checklist-portal__textarea"
                rows="3"
                placeholder="Введите ответ"
                @input="onResponseInput"
            ></textarea>
            <button
                v-if="!question.required"
                type="button"
                :class="['checklist-portal__chip', 'is-skip', answer.skipped && 'is-active']"
                @click="toggleSkip"
            >
                Пропустить
            </button>
        </div>
    </div>

    <div class="checklist-portal__question-actions">
        <button type="button" class="checklist-portal__icon-button" @click="toggleComment">
            <span class="checklist-portal__icon">💬</span>
            <span v-if="answer.comment" class="checklist-portal__icon-check">✓</span>
        </button>
        <button type="button" class="checklist-portal__icon-button" @click="togglePhoto">
            <span class="checklist-portal__icon">📷</span>
            <span v-if="answer.photo_path" class="checklist-portal__icon-check">✓</span>
        </button>
    </div>

    <div v-if="answer.showComment" class="checklist-portal__question-extra">
        <label class="checklist-portal__label">
            Комментарий
            <span v-if="question.require_comment" class="checklist-portal__required">*</span>
        </label>
        <textarea
            :value="commentValue"
            class="checklist-portal__textarea"
            rows="2"
            placeholder="Комментарий"
            @input="onCommentInput"
        ></textarea>
    </div>

    <div class="checklist-portal__question-extra">
        <input
            :id="'portal-photo-' + question.id"
            class="checklist-portal__input"
            type="file"
            accept="image/*"
            style="display: none"
            @change="onPhotoChange"
        />
        <div v-if="photoLoading" class="checklist-portal__muted">Загрузка фото...</div>
        <div v-else-if="answer.photo_url" class="checklist-portal__photo">
            <img :src="answer.photo_url" alt="Фото" />
        </div>
    </div>

    <div v-if="showErrors && errorText" class="checklist-portal__error">
        {{ errorText }}
    </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
    question: { type: Object, required: true },
    answer: { type: Object, required: true },
    showErrors: { type: Boolean, default: false },
    errorText: { type: String, default: '' },
    photoLoading: { type: Boolean, default: false },
});

const emit = defineEmits([
    'set-answer',
    'set-comment',
    'skip',
    'toggle-comment',
    'toggle-photo',
    'photo-change',
]);

const isYesNo = computed(() =>
    ['yesno', 'boolean', 'bool', 'yn'].includes((props.question.type || '').toLowerCase()),
);
const isScale = computed(() => ['scale', 'rating'].includes((props.question.type || '').toLowerCase()));
const isShortText = computed(() =>
    ['short_text', 'short', 'text'].includes((props.question.type || '').toLowerCase()),
);

const scaleMax = computed(() => {
    const meta = props.question.meta || {};
    const candidates = [meta.scale_max, meta.max, meta.max_value];
    let max = candidates.find((val) => typeof val === 'number' || typeof val === 'string');
    if (!max && typeof meta.range === 'string') {
        const parts = meta.range.split('-').map((item) => Number(item.trim()));
        if (parts.length === 2 && !Number.isNaN(parts[1])) {
            max = parts[1];
        }
    }
    const parsed = Number(max);
    return Number.isFinite(parsed) && parsed > 0 ? Math.min(parsed, 10) : 5;
});

const responseValue = computed(() => props.answer?.response_value || '');
const commentValue = computed(() => props.answer?.comment || '');

function setAnswer(value) {
    emit('set-answer', props.question.id, value);
}

function onResponseInput(event) {
    setAnswer(event?.target?.value ?? '');
}

function onCommentInput(event) {
    emit('set-comment', props.question.id, event?.target?.value ?? '');
}

function toggleSkip() {
    emit('skip', props.question.id);
}

function toggleComment() {
    emit('toggle-comment', props.question.id);
}

function togglePhoto() {
    emit('toggle-photo', props.question.id);
}

function onPhotoChange(event) {
    emit('photo-change', props.question.id, event);
}
</script>
