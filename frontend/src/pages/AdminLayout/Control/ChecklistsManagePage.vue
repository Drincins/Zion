<template>
    <div class="control-checklists-manage">
        <header class="control-checklists-manage__header">
            <div>
                <p class="control-checklists-manage__eyebrow">Контроль · Чек-листы</p>
                <h1 class="control-checklists-manage__title">
                    {{ checklist?.name || 'Чек-лист' }}
                </h1>
            </div>
            <div class="control-checklists-manage__header-actions">
                <Button color="ghost" size="sm" @click="goBack">Назад</Button>
                <Button color="ghost" size="sm" :loading="loading" @click="loadChecklist">
                    Обновить
                </Button>
            </div>
        </header>

        <section class="control-checklists-manage__panel">
            <div class="control-checklists-manage__panel-header">
                <div>
                    <h2 class="control-checklists-manage__panel-title">Разделы и вопросы</h2>
                    <p class="control-checklists-manage__panel-subtitle">
                        Соберите чек-лист из разделов и вопросов.
                    </p>
                </div>
                <div class="control-checklists-manage__panel-actions">
                    <Button color="primary" size="sm" @click="openSectionModal">
                        Создать раздел
                    </Button>
                </div>
            </div>

            <div v-if="loading" class="control-checklists-manage__loading">Загрузка...</div>
            <div v-else>
                <div v-if="sections.length" class="control-checklists-manage__sections">
                    <div
                        v-for="(section, sectionIndex) in sections"
                        :key="section.id"
                        class="control-checklists-manage__section-card"
                        :class="{ 'is-highlighted': highlightedSectionId === section.id }"
                        draggable="true"
                        @dragstart="onSectionDragStart(sectionIndex)"
                        @dragover.prevent
                        @drop="onSectionDrop(sectionIndex)"
                    >
                        <div class="control-checklists-manage__section-header">
                            <div class="control-checklists-manage__section-title">
                                <span class="control-checklists-manage__section-index">
                                    Раздел {{ sectionIndex + 1 }}
                                </span>
                                <div class="control-checklists-manage__section-name">
                                    <h3>{{ section.title }}</h3>
                                    <button
                                        type="button"
                                        class="control-checklists-manage__icon-button"
                                        title="Редактировать раздел"
                                        aria-label="Редактировать раздел"
                                        @click.stop="startEditSection(section)"
                                    >
                                        <BaseIcon name="Settings" />
                                    </button>
                                </div>
                            </div>
                            <div class="control-checklists-manage__section-actions">
                                <span class="control-checklists-manage__drag-handle" title="Переместить раздел">
                                    ⇅
                                </span>
                                <button
                                    type="button"
                                    class="control-checklists-manage__icon-button"
                                    title="Удалить раздел"
                                    aria-label="Удалить раздел"
                                    :disabled="saving"
                                    @click.stop="handleDeleteSection(section.id)"
                                >
                                    <BaseIcon name="Trash" />
                                </button>
                            </div>
                        </div>

                        <div class="control-checklists-manage__questions">
                            <div
                                v-for="(question, questionIndex) in questionsBySection(section.id)"
                                :key="question.id"
                                class="control-checklists-manage__question"
                                :class="{
                                    'is-active': activeQuestionId === question.id,
                                    'is-highlighted': highlightedQuestionId === question.id,
                                }"
                                draggable="true"
                                @click="setActiveQuestion(question)"
                                @dragstart="onQuestionDragStart(section.id, questionIndex)"
                                @dragover.prevent
                                @drop="onQuestionDrop(section.id, questionIndex)"
                            >
                                <span class="control-checklists-manage__question-drag" title="Переместить вопрос">
                                    ☰
                                </span>
                                <div class="control-checklists-manage__question-title">
                                    {{ questionIndex + 1 }}. {{ question.text }}
                                </div>
                                <div
                                    v-if="activeQuestionId === question.id"
                                    class="control-checklists-manage__question-body"
                                    @click.stop
                                >
                                    <Input v-model="questionEditForm.text" label="Текст вопроса" />
                                    <Select
                                        v-model="questionEditForm.type"
                                        label="Тип"
                                        :options="questionTypeOptions"
                                    />
                                    <Input
                                        v-if="checklist?.is_scored"
                                        v-model="questionEditForm.weight"
                                        label="Ценность вопроса"
                                        type="number"
                                    />
                                    <div class="control-checklists-manage__question-flags">
                                        <Checkbox v-model="questionEditForm.required" label="Обязательный" />
                                        <Checkbox v-model="questionEditForm.requirePhoto" label="Фото" />
                                        <Checkbox v-model="questionEditForm.requireComment" label="Комментарий" />
                                    </div>
                                    <div class="control-checklists-manage__question-actions">
                                        <Button
                                            color="primary"
                                            size="sm"
                                            :loading="saving"
                                            @click="handleUpdateQuestion(section.id, question.id)"
                                        >
                                            Сохранить
                                        </Button>
                                        <button
                                            type="button"
                                            class="control-checklists-manage__icon-button"
                                            title="Удалить вопрос"
                                            aria-label="Удалить вопрос"
                                            :disabled="saving"
                                            @click="handleDeleteQuestion(question.id)"
                                        >
                                            <BaseIcon name="Trash" />
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <div class="control-checklists-manage__new-question">
                                <Button
                                    color="ghost"
                                    size="sm"
                                    @click="openNewQuestion(section.id)"
                                >
                                    Новый вопрос
                                </Button>
                            </div>

                            <div
                                v-if="newQuestionSectionId === section.id"
                                class="control-checklists-manage__question-editor"
                            >
                                <Input v-model="newQuestionForm.text" label="Текст вопроса" />
                                <Select
                                    v-model="newQuestionForm.type"
                                    label="Тип"
                                    :options="questionTypeOptions"
                                />
                                <Input
                                    v-if="checklist?.is_scored"
                                    v-model="newQuestionForm.weight"
                                    label="Ценность вопроса"
                                    type="number"
                                />
                                <div class="control-checklists-manage__question-flags">
                                    <Checkbox v-model="newQuestionForm.required" label="Обязательный" />
                                    <Checkbox v-model="newQuestionForm.requirePhoto" label="Фото" />
                                    <Checkbox v-model="newQuestionForm.requireComment" label="Комментарий" />
                                </div>
                                <div class="control-checklists-manage__question-actions">
                                    <Button
                                        color="primary"
                                        size="sm"
                                        :loading="saving"
                                        @click="handleCreateQuestion(section.id)"
                                    >
                                        Сохранить
                                    </Button>
                                    <Button color="ghost" size="sm" @click="cancelNewQuestion">Отмена</Button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <p v-else class="control-checklists-manage__empty">Разделов пока нет.</p>

                <div class="control-checklists-manage__footer">
                    <Button color="ghost" size="sm" @click="openSectionModal">Новый раздел</Button>
                    <Button
                        color="primary"
                        size="sm"
                        class="control-checklists-manage__save"
                        :loading="saving"
                        @click="handleSaveChecklist"
                    >
                        Сохранить чек-лист
                    </Button>
                </div>
            </div>
        </section>

        <Modal v-if="isSectionModalOpen" class="control-checklists-manage__modal" @close="closeSectionModal">
            <template #header>
                {{ sectionForm.id ? 'Редактирование раздела' : 'Новый раздел' }}
            </template>
            <template #default>
                <form class="control-checklists-manage__modal-form" @submit.prevent="handleSubmitSection">
                    <Input v-model="sectionForm.title" label="Название раздела" />
                </form>
            </template>
            <template #footer>
                <Button type="button" color="ghost" size="sm" :disabled="saving" @click="closeSectionModal">
                    Отмена
                </Button>
                <Button type="button" color="primary" size="sm" :loading="saving" @click="handleSubmitSection">
                    Сохранить
                </Button>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'vue-toastification';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Select from '@/components/UI-components/Select.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import Modal from '@/components/UI-components/Modal.vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import {
    createChecklistQuestion,
    createChecklistSection,
    deleteChecklistQuestion,
    deleteChecklistSection,
    fetchChecklist,
    updateChecklistQuestion,
    updateChecklistSection,
} from '@/api';

const route = useRoute();
const router = useRouter();
const toast = useToast();

const loading = ref(false);
const saving = ref(false);
const checklist = ref(null);
const sections = ref([]);
const questions = ref([]);
const draggedSectionIndex = ref(null);
const draggedQuestion = reactive({
    sectionId: null,
    index: null,
});
const highlightedSectionId = ref(null);
const highlightedQuestionId = ref(null);
const activeQuestionSnapshot = ref(null);

const isSectionModalOpen = ref(false);
const sectionForm = reactive({
    id: null,
    title: '',
});

const newQuestionSectionId = ref(null);
const activeQuestionId = ref(null);
const newQuestionForm = reactive({
    text: '',
    type: 'yesno',
    weight: '',
    required: true,
    requirePhoto: false,
    requireComment: false,
});

const questionEditForm = reactive({
    text: '',
    type: 'yesno',
    weight: '',
    required: true,
    requirePhoto: false,
    requireComment: false,
});

const questionTypeOptions = [
    { value: 'yesno', label: 'Да/Нет' },
    { value: 'scale', label: 'Шкала' },
    { value: 'short_text', label: 'Короткий текст' },
    { value: 'long_text', label: 'Длинный текст' },
];

const checklistId = computed(() => Number(route.params.id));

function resolveQuestionWeight(value) {
    if (!checklist.value?.is_scored) {
        return null;
    }
    return value === '' ? null : Number(value);
}

function buildQuestionPayload(form, sectionId, { order } = {}) {
    const payload = {
        text: form.text.trim(),
        type: form.type,
        section_id: sectionId,
        weight: resolveQuestionWeight(form.weight),
        required: form.required,
        require_photo: form.requirePhoto,
        require_comment: form.requireComment,
    };
    if (order !== undefined) {
        payload.order = order;
    }
    return payload;
}

function resetNewQuestionForm() {
    newQuestionForm.text = '';
    newQuestionForm.type = 'yesno';
    newQuestionForm.weight = '';
    newQuestionForm.required = true;
    newQuestionForm.requirePhoto = false;
    newQuestionForm.requireComment = false;
}

function questionsBySection(sectionId) {
    return questions.value
        .filter((item) => item.section_id === sectionId)
        .sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
}

function sortedSections() {
    sections.value = [...sections.value].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
}

function sortedQuestions() {
    questions.value = [...questions.value].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
}

function highlightSection(id) {
    highlightedSectionId.value = id;
    setTimeout(() => {
        if (highlightedSectionId.value === id) {
            highlightedSectionId.value = null;
        }
    }, 1000);
}

function highlightQuestion(id) {
    highlightedQuestionId.value = id;
    setTimeout(() => {
        if (highlightedQuestionId.value === id) {
            highlightedQuestionId.value = null;
        }
    }, 1000);
}

async function loadChecklist() {
    if (!checklistId.value) {
        return;
    }
    loading.value = true;
    try {
        const data = await fetchChecklist(checklistId.value);
        checklist.value = data || null;
        sections.value = Array.isArray(data?.sections) ? data.sections : [];
        questions.value = Array.isArray(data?.questions) ? data.questions : [];
        sortedSections();
        sortedQuestions();
    } catch (error) {
        console.error(error);
        toast.error('Не удалось загрузить чек-лист.');
    } finally {
        loading.value = false;
    }
}

function goBack() {
    router.push({ name: 'control-checklists' });
}

function openSectionModal() {
    sectionForm.id = null;
    sectionForm.title = '';
    isSectionModalOpen.value = true;
}

function closeSectionModal() {
    isSectionModalOpen.value = false;
}

function startEditSection(section) {
    sectionForm.id = section.id;
    sectionForm.title = section.title;
    isSectionModalOpen.value = true;
}

async function handleSubmitSection() {
    if (!sectionForm.title.trim()) {
        toast.error('Введите название раздела.');
        return;
    }
    saving.value = true;
    try {
        const payload = {
            title: sectionForm.title.trim(),
        };
        if (sectionForm.id) {
            await updateChecklistSection(checklistId.value, sectionForm.id, payload);
            toast.success('Раздел обновлен.');
        } else {
            const maxOrder = sections.value.length
                ? Math.max(...sections.value.map((item) => item.order ?? 0))
                : 0;
            await createChecklistSection(checklistId.value, { ...payload, order: maxOrder + 1 });
            toast.success('Раздел создан.');
        }
        closeSectionModal();
        await loadChecklist();
    } catch (error) {
        console.error(error);
        toast.error('Не удалось сохранить раздел.');
    } finally {
        saving.value = false;
    }
}

async function handleDeleteSection(sectionId) {
    if (!confirm('Удалить раздел?')) {
        return;
    }
    saving.value = true;
    try {
        await deleteChecklistSection(checklistId.value, sectionId);
        toast.success('Раздел удален.');
        await loadChecklist();
    } catch (error) {
        console.error(error);
        toast.error('Не удалось удалить раздел.');
    } finally {
        saving.value = false;
    }
}

function openNewQuestion(sectionId) {
    newQuestionSectionId.value = sectionId;
    resetNewQuestionForm();
}

function cancelNewQuestion() {
    newQuestionSectionId.value = null;
}

function setActiveQuestion(question) {
    if (activeQuestionId.value === question.id) {
        if (!isQuestionDirty()) {
            collapseQuestion();
        }
        return;
    }
    activeQuestionId.value = question.id;
    questionEditForm.text = question.text || '';
    questionEditForm.type = question.type || 'yesno';
    questionEditForm.weight = question.weight ?? '';
    questionEditForm.required = Boolean(question.required);
    questionEditForm.requirePhoto = Boolean(question.require_photo);
    questionEditForm.requireComment = Boolean(question.require_comment);
    activeQuestionSnapshot.value = {
        text: questionEditForm.text,
        type: questionEditForm.type,
        weight: questionEditForm.weight ?? '',
        required: questionEditForm.required,
        requirePhoto: questionEditForm.requirePhoto,
        requireComment: questionEditForm.requireComment,
    };
}

function collapseQuestion() {
    activeQuestionId.value = null;
    activeQuestionSnapshot.value = null;
}

function isQuestionDirty() {
    if (!activeQuestionSnapshot.value) {
        return false;
    }
    return (
        activeQuestionSnapshot.value.text !== questionEditForm.text ||
        activeQuestionSnapshot.value.type !== questionEditForm.type ||
        String(activeQuestionSnapshot.value.weight ?? '') !== String(questionEditForm.weight ?? '') ||
        activeQuestionSnapshot.value.required !== questionEditForm.required ||
        activeQuestionSnapshot.value.requirePhoto !== questionEditForm.requirePhoto ||
        activeQuestionSnapshot.value.requireComment !== questionEditForm.requireComment
    );
}

async function handleCreateQuestion(sectionId) {
    if (!newQuestionForm.text.trim()) {
        toast.error('Введите текст вопроса.');
        return;
    }
    saving.value = true;
    try {
        const payload = buildQuestionPayload(newQuestionForm, sectionId, {
            order: questionsBySection(sectionId).length + 1,
        });
        await createChecklistQuestion(checklistId.value, payload);
        toast.success('Вопрос добавлен.');
        newQuestionSectionId.value = null;
        await loadChecklist();
    } catch (error) {
        console.error(error);
        toast.error('Не удалось сохранить вопрос.');
    } finally {
        saving.value = false;
    }
}

async function handleUpdateQuestion(sectionId, questionId) {
    if (!questionEditForm.text.trim()) {
        toast.error('Введите текст вопроса.');
        return;
    }
    saving.value = true;
    try {
        const payload = buildQuestionPayload(questionEditForm, sectionId);
        await updateChecklistQuestion(checklistId.value, questionId, payload);
        toast.success('Вопрос обновлен.');
        await loadChecklist();
    } catch (error) {
        console.error(error);
        toast.error('Не удалось сохранить вопрос.');
    } finally {
        saving.value = false;
    }
}

async function handleDeleteQuestion(questionId) {
    if (!confirm('Удалить вопрос?')) {
        return;
    }
    saving.value = true;
    try {
        await deleteChecklistQuestion(checklistId.value, questionId);
        toast.success('Вопрос удален.');
        await loadChecklist();
        if (activeQuestionId.value === questionId) {
            activeQuestionId.value = null;
        }
    } catch (error) {
        console.error(error);
        toast.error('Не удалось удалить вопрос.');
    } finally {
        saving.value = false;
    }
}

async function handleSaveChecklist() {
    await loadChecklist();
    toast.success('Чек-лист сохранён.');
}

function onSectionDragStart(index) {
    draggedSectionIndex.value = index;
}

async function onSectionDrop(targetIndex) {
    if (draggedSectionIndex.value === null || draggedSectionIndex.value === targetIndex) {
        draggedSectionIndex.value = null;
        return;
    }
    const reordered = [...sections.value];
    const [moved] = reordered.splice(draggedSectionIndex.value, 1);
    reordered.splice(targetIndex, 0, moved);
    sections.value = reordered;
    draggedSectionIndex.value = null;

    saving.value = true;
    try {
        await Promise.all(
            sections.value.map((section, index) =>
                updateChecklistSection(checklistId.value, section.id, { order: index + 1 }),
            ),
        );
        highlightSection(moved.id);
        await loadChecklist();
    } catch (error) {
        console.error(error);
        toast.error('Не удалось переместить раздел.');
    } finally {
        saving.value = false;
    }
}

function onQuestionDragStart(sectionId, index) {
    draggedQuestion.sectionId = sectionId;
    draggedQuestion.index = index;
}

async function onQuestionDrop(sectionId, targetIndex) {
    if (draggedQuestion.sectionId === null || draggedQuestion.index === null) {
        return;
    }
    if (draggedQuestion.sectionId !== sectionId || draggedQuestion.index === targetIndex) {
        draggedQuestion.sectionId = null;
        draggedQuestion.index = null;
        return;
    }
    const list = questionsBySection(sectionId);
    const [moved] = list.splice(draggedQuestion.index, 1);
    list.splice(targetIndex, 0, moved);
    const other = questions.value.filter((item) => item.section_id !== sectionId);
    questions.value = [...other, ...list];
    draggedQuestion.sectionId = null;
    draggedQuestion.index = null;

    saving.value = true;
    try {
        await Promise.all(
            list.map((question, index) =>
                updateChecklistQuestion(checklistId.value, question.id, { order: index + 1 }),
            ),
        );
        highlightQuestion(moved.id);
        await loadChecklist();
    } catch (error) {
        console.error(error);
        toast.error('Не удалось переместить вопрос.');
    } finally {
        saving.value = false;
    }
}

watch(
    () => checklistId.value,
    async () => {
        await loadChecklist();
    },
    { immediate: true },
);
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/control-checklists-manage' as *;
</style>
