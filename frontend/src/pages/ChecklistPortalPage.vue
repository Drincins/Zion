<template>
    <div class="checklist-portal" :class="{ 'is-fill': step === 'fill' }">
        <header class="checklist-portal__header">
            <div>
                <div class="checklist-portal__title">Чек-листы</div>
                <div class="checklist-portal__subtitle">Быстрое прохождение для сотрудников</div>
            </div>
        </header>

        <main class="checklist-portal__content" @click="closeUserMenu">
            <section v-if="step === 'login'" class="checklist-portal__card">
                <h2>Вход</h2>
                <p v-if="authStage === 'staff'" class="checklist-portal__muted">
                    Введите табельный номер.
                </p>
                <p v-else class="checklist-portal__muted">
                    Для этого сотрудника нужна дополнительная авторизация.
                </p>
                <div class="checklist-portal__form">
                    <template v-if="authStage === 'staff'">
                        <label class="checklist-portal__label">Табельный номер</label>
                        <input
                            v-model="loginForm.staffCode"
                            class="checklist-portal__input"
                            type="text"
                            inputmode="numeric"
                            placeholder="Например: 12345"
                        />
                    </template>
                    <template v-else>
                        <label class="checklist-portal__label">Логин</label>
                        <input
                            v-model="loginForm.username"
                            class="checklist-portal__input"
                            type="text"
                            autocomplete="username"
                            placeholder="Введите логин"
                        />
                        <label class="checklist-portal__label">Пароль</label>
                        <input
                            v-model="loginForm.password"
                            class="checklist-portal__input"
                            type="password"
                            autocomplete="current-password"
                            placeholder="Введите пароль"
                        />
                    </template>
                    <div v-if="loginError" class="checklist-portal__error">{{ loginError }}</div>
                    <div class="checklist-portal__actions">
                        <button
                            v-if="authStage === 'credentials'"
                            type="button"
                            class="checklist-portal__button-outline"
                            :disabled="authLoading"
                            @click="backToStaffStep"
                        >
                            Назад
                        </button>
                        <button
                            type="button"
                            class="checklist-portal__button"
                            :disabled="authLoading"
                            @click="authStage === 'staff' ? handleStaffCodeLogin() : handleCredentialsLogin()"
                        >
                            {{ authLoading ? 'Входим...' : 'Войти' }}
                        </button>
                    </div>
                </div>
            </section>

            <section v-else-if="step === 'list'" class="checklist-portal__card">
                <div class="checklist-portal__section-header">
                    <h2>Доступные чек-листы</h2>
                    <div class="checklist-portal__user-menu">
                        <button
                            type="button"
                            class="checklist-portal__user-button"
                            @click.stop="toggleUserMenu"
                        >
                            {{ portalUser?.name || 'Сотрудник' }}
                        </button>
                        <button
                            v-if="userMenuOpen"
                            type="button"
                            class="checklist-portal__user-exit"
                            @click.stop="handleLogout"
                        >
                            Выйти
                        </button>
                    </div>
                </div>
                <div v-if="listLoading" class="checklist-portal__muted">Загрузка...</div>
                <div v-else-if="!checklists.length" class="checklist-portal__muted">
                    Нет доступных чек-листов.
                </div>
                <div v-else class="checklist-portal__list">
                    <button
                        v-for="item in checklists"
                        :key="item.id"
                        type="button"
                        class="checklist-portal__list-item"
                        @click="selectChecklist(item)"
                    >
                        <div class="checklist-portal__list-title">{{ item.name }}</div>
                        <div v-if="item.description" class="checklist-portal__list-desc">
                            {{ item.description }}
                        </div>
                        <div class="checklist-portal__list-meta">
                            <span v-if="item.is_scored">Оценочный</span>
                            <span v-else>Неоцениваемый</span>
                            <span v-if="item.has_control_objects">Выбор ресторана</span>
                        </div>
                    </button>
                </div>
            </section>

            <section v-else-if="step === 'fill'" class="checklist-portal__card">
                <div class="checklist-portal__section-header">
                    <div>
                        <h2>{{ checklistDetail?.name }}</h2>
                        <div v-if="selectedDepartment" class="checklist-portal__muted">
                            Ресторан: {{ selectedDepartment }}
                        </div>
                    </div>
                    <button type="button" class="checklist-portal__link" @click="resetToList">Назад</button>
                </div>
                <div v-if="submitError" class="checklist-portal__error">{{ submitError }}</div>
                <div class="checklist-portal__questions">
                    <template v-if="displayMode === 'step'">
                        <div class="checklist-portal__progress">
                            <span>Вопрос {{ currentQuestionIndex + 1 }} из {{ orderedQuestions.length }}</span>
                            <div class="checklist-portal__progress-bar">
                                <span :style="{ width: `${progressPercent}%` }"></span>
                            </div>
                        </div>
                        <div v-if="currentQuestion" class="checklist-portal__question">
                            <div class="checklist-portal__question-title">
                                {{ currentQuestion.text }}
                                <span
                                    v-if="hasRequirementMarker(currentQuestion)"
                                    class="checklist-portal__required"
                                >
                                    *
                                </span>
                                <span
                                    v-if="requirementLabel(currentQuestion)"
                                    class="checklist-portal__required-note"
                                >
                                    {{ requirementLabel(currentQuestion) }}
                                </span>
                            </div>
                            <QuestionBlock
                                :question="currentQuestion"
                                :answer="answerFor(currentQuestion.id)"
                                :show-errors="showErrors"
                                :error-text="fieldError(currentQuestion.id)"
                                :photo-loading="photoLoadingId === currentQuestion.id"
                                @set-answer="setAnswer"
                                @set-comment="setComment"
                                @skip="skipQuestion"
                                @toggle-comment="toggleComment"
                                @toggle-photo="triggerPhotoInput"
                                @photo-change="handlePhotoChange"
                            />
                        </div>
                        <div class="checklist-portal__step-actions">
                            <button
                                type="button"
                                class="checklist-portal__button-outline"
                                :disabled="currentQuestionIndex === 0"
                                @click="currentQuestionIndex--"
                            >
                                Назад
                            </button>
                            <button
                                type="button"
                                class="checklist-portal__button"
                                @click="goNextQuestion"
                            >
                                {{ currentQuestionIndex + 1 >= orderedQuestions.length ? 'К отправке' : 'Дальше' }}
                            </button>
                        </div>
                    </template>
                    <template v-else>
                        <div v-if="displayMode === 'sections'" class="checklist-portal__section">
                            <div class="checklist-portal__section-header-block">
                                <div class="checklist-portal__section-meta">
                                    Раздел {{ sectionPosition }} из {{ sectionTotal }}
                                </div>
                                <div class="checklist-portal__section-heading">
                                    {{ currentSection?.title || 'Раздел' }}
                                </div>
                            </div>
                            <div class="checklist-portal__section-nav">
                                <button
                                    type="button"
                                    class="checklist-portal__nav-button"
                                    :disabled="sectionIndex === 0"
                                    @click="prevSection"
                                >
                                    ←
                                </button>
                                <button
                                    type="button"
                                    class="checklist-portal__nav-button"
                                    :disabled="sectionIndex >= sectionsOrdered.length - 1"
                                    @click="nextSection"
                                >
                                    →
                                </button>
                            </div>
                            <div
                                v-for="question in currentSection?.questions || []"
                                :key="question.id"
                                class="checklist-portal__question"
                            >
                                <div class="checklist-portal__question-title">
                                    {{ question.text }}
                                    <span v-if="hasRequirementMarker(question)" class="checklist-portal__required">
                                        *
                                    </span>
                                    <span v-if="requirementLabel(question)" class="checklist-portal__required-note">
                                        {{ requirementLabel(question) }}
                                    </span>
                                </div>
                                <QuestionBlock
                                    :question="question"
                                    :answer="answerFor(question.id)"
                                    :show-errors="showErrors"
                                    :error-text="fieldError(question.id)"
                                    :photo-loading="photoLoadingId === question.id"
                                    @set-answer="setAnswer"
                                    @set-comment="setComment"
                                    @skip="skipQuestion"
                                    @toggle-comment="toggleComment"
                                    @toggle-photo="triggerPhotoInput"
                                    @photo-change="handlePhotoChange"
                                />
                            </div>
                        </div>
                        <div
                            v-for="section in sectionsOrdered"
                            v-else
                            :key="section.key"
                            class="checklist-portal__section"
                        >
                            <div v-if="section.title" class="checklist-portal__section-title">
                                {{ section.title }}
                            </div>
                            <div
                                v-for="question in section.questions"
                                :key="question.id"
                                class="checklist-portal__question"
                            >
                                <div class="checklist-portal__question-title">
                                    {{ question.text }}
                                    <span v-if="hasRequirementMarker(question)" class="checklist-portal__required">
                                        *
                                    </span>
                                    <span v-if="requirementLabel(question)" class="checklist-portal__required-note">
                                        {{ requirementLabel(question) }}
                                    </span>
                                </div>
                                <QuestionBlock
                                    :question="question"
                                    :answer="answerFor(question.id)"
                                    :show-errors="showErrors"
                                    :error-text="fieldError(question.id)"
                                    :photo-loading="photoLoadingId === question.id"
                                    @set-answer="setAnswer"
                                    @set-comment="setComment"
                                    @skip="skipQuestion"
                                    @toggle-comment="toggleComment"
                                    @toggle-photo="triggerPhotoInput"
                                    @photo-change="handlePhotoChange"
                                />
                            </div>
                        </div>
                    </template>
                </div>

                <button
                    v-if="displayMode === 'sections'"
                    type="button"
                    class="checklist-portal__button"
                    :disabled="isLastSection ? submitLoading : false"
                    @click="handleSectionsAction"
                >
                    {{
                        isLastSection
                            ? (submitLoading ? 'Отправляем...' : 'Отправить')
                            : 'Следующий раздел'
                    }}
                </button>
                <button
                    v-else
                    type="button"
                    class="checklist-portal__button"
                    :disabled="submitLoading"
                    @click="submitChecklist"
                >
                    {{ submitLoading ? 'Отправляем...' : 'Отправить' }}
                </button>
            </section>

            <section v-else-if="step === 'success'" class="checklist-portal__card">
                <h2>Готово!</h2>
                <div v-if="summaryLoading" class="checklist-portal__muted">Загружаем итог...</div>
                <div v-else class="checklist-portal__summary">
                    <div class="checklist-portal__summary-title">
                        Чек-лист «{{ attemptSummary?.checklist_name || checklistDetail?.name }}» успешно заполнен
                    </div>
                    <div class="checklist-portal__summary-score">
                        <template v-if="attemptSummary?.is_scored">
                            Оценка: {{ attemptSummary?.total_score ?? 0 }} из {{ attemptSummary?.total_max ?? 0 }}
                            <span v-if="attemptSummary?.percent">({{ attemptSummary.percent }}%)</span>
                        </template>
                        <template v-else>
                            Чек-лист неоцениваемый
                        </template>
                    </div>
                    <div class="checklist-portal__summary-grid">
                        <div>Сотрудник</div>
                        <div>{{ attemptSummary?.user_name || portalUser?.name }}</div>
                        <div>Ресторан</div>
                        <div>{{ attemptSummary?.department || selectedDepartment || '—' }}</div>
                        <div>Начало</div>
                        <div>{{ attemptSummary?.started_at || '—' }}</div>
                        <div>Окончание</div>
                        <div>{{ attemptSummary?.submitted_at || '—' }}</div>
                    </div>
                </div>
                <div class="checklist-portal__success-actions">
                    <button type="button" class="checklist-portal__button-outline" @click="downloadReport('pdf')">
                        PDF-отчет
                    </button>
                    <button type="button" class="checklist-portal__button-outline" @click="downloadReport('xlsx')">
                        Excel-отчет
                    </button>
                </div>
                <div class="checklist-portal__success-footer">
                    <button type="button" class="checklist-portal__button-outline" @click="resetToList">
                        На главную
                    </button>
                    <button type="button" class="checklist-portal__button" @click="resetToList">
                        Новый чек-лист
                    </button>
                </div>
            </section>
        </main>

        <div v-if="runModalOpen" class="checklist-portal__modal-overlay">
            <div class="checklist-portal__modal">
                <div class="checklist-portal__modal-header">
                    <div>
                        <div class="checklist-portal__modal-title">
                            {{ selectedChecklist?.name || 'Чек-лист' }}
                        </div>
                        <div v-if="selectedDepartment" class="checklist-portal__muted">
                            Ресторан: {{ selectedDepartment }}
                        </div>
                    </div>
                    <button
                        type="button"
                        class="checklist-portal__icon-button checklist-portal__modal-close"
                        @click="closeRunModal"
                    >
                        ✕
                    </button>
                </div>

                <div class="checklist-portal__modal-body">
                    <p class="checklist-portal__muted">
                        Выберите ресторан прохождения и формат заполнения.
                    </p>
                    <div class="checklist-portal__setup-block">
                        <div class="checklist-portal__section-title">Ресторан прохождения</div>
                        <select
                            v-if="controlObjects.length"
                            v-model="selectedDepartment"
                            class="checklist-portal__input"
                        >
                            <option value="">Выберите ресторан</option>
                            <option v-for="item in controlObjects" :key="item" :value="item">
                                {{ item }}
                            </option>
                        </select>
                        <div v-else class="checklist-portal__muted">
                            Нет доступных ресторанов. Будет использован ваш основной ресторан.
                        </div>
                        <div v-if="objectError" class="checklist-portal__error">{{ objectError }}</div>
                    </div>
                    <div class="checklist-portal__setup-block">
                        <div class="checklist-portal__section-title">Как пройти чек-лист</div>
                        <div class="checklist-portal__mode-grid">
                            <button
                                type="button"
                                :class="[
                                    'checklist-portal__mode-card',
                                    displayMode === 'step' && 'is-active',
                                ]"
                                @click="setDisplayMode('step')"
                            >
                                <div class="checklist-portal__mode-title">По порядку</div>
                                <div class="checklist-portal__muted">Вопрос за вопросом</div>
                            </button>
                            <button
                                type="button"
                                :class="[
                                    'checklist-portal__mode-card',
                                    displayMode === 'sections' && 'is-active',
                                ]"
                                @click="setDisplayMode('sections')"
                            >
                                <div class="checklist-portal__mode-title">По разделам</div>
                                <div class="checklist-portal__muted">С группировкой</div>
                            </button>
                            <button
                                type="button"
                                :class="[
                                    'checklist-portal__mode-card',
                                    displayMode === 'all' && 'is-active',
                                ]"
                                @click="setDisplayMode('all')"
                            >
                                <div class="checklist-portal__mode-title">Целиком</div>
                                <div class="checklist-portal__muted">Весь список</div>
                            </button>
                        </div>
                    </div>
                    <button
                        type="button"
                        class="checklist-portal__button"
                        @click="handleStartChecklist"
                    >
                        Начать чек-лист
                    </button>
                    <div v-if="draftPromptVisible" class="checklist-portal__draft-prompt">
                        <div class="checklist-portal__draft-title">Есть незавершенный чек-лист</div>
                        <div class="checklist-portal__muted">
                            Продолжить или начать заново?
                        </div>
                        <div class="checklist-portal__draft-actions">
                            <button type="button" class="checklist-portal__button" @click="resumeDraft">
                                Продолжить
                            </button>
                            <button
                                type="button"
                                class="checklist-portal__button-outline"
                                @click="startFresh"
                            >
                                Начать заново
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import {
    clearChecklistPortalToken,
    deleteChecklistPortalDraft,
    exportChecklistPortalAttempt,
    fetchChecklistPortalAttempt,
    fetchChecklistPortalChecklist,
    fetchChecklistPortalChecklists,
    fetchChecklistPortalControlObjects,
    fetchChecklistPortalDraft,
    fetchChecklistPortalMe,
    finishChecklistPortalLogin,
    setChecklistPortalToken,
    startChecklistPortalLogin,
    submitChecklistPortalAttempt,
    uploadChecklistPortalPhoto,
    upsertChecklistPortalDraft,
} from '@/api';
import QuestionBlock from '@/components/checklists/ChecklistPortalQuestionBlock.vue';

const portalTokenKey = 'checklist_portal_token';

const step = ref('login');
const runModalOpen = ref(false);
const draftInfo = ref(null);
const draftPromptVisible = ref(false);
const portalUser = ref(null);
const checklists = ref([]);
const selectedChecklist = ref(null);
const checklistDetail = ref(null);
const controlObjects = ref([]);
const selectedDepartment = ref('');
const displayMode = ref('sections');
const currentQuestionIndex = ref(0);

const loginForm = reactive({
    staffCode: '',
    username: '',
    password: '',
});
const authStage = ref('staff');
const userMenuOpen = ref(false);
const loginError = ref('');
const authLoading = ref(false);

const listLoading = ref(false);
const submitLoading = ref(false);
const submitError = ref('');
const attemptId = ref(null);
const attemptSummary = ref(null);
const summaryLoading = ref(false);
const objectError = ref('');
const photoLoadingId = ref(null);
const showErrors = ref(false);

const answers = reactive({});
let draftSaveTimer = null;

function clearAnswers() {
    Object.keys(answers).forEach((key) => delete answers[key]);
}

const orderedQuestions = computed(() => {
    if (!checklistDetail.value?.questions) {
        return [];
    }
    return [...checklistDetail.value.questions].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
});

const currentQuestion = computed(() => orderedQuestions.value[currentQuestionIndex.value] || null);

const renderSections = computed(() => {
    const sections = (checklistDetail.value?.sections || []).slice().sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
    const map = new Map();
    sections.forEach((section) => {
        map.set(section.id, { key: section.id, title: section.name, questions: [] });
    });
    const unsectioned = [];
    orderedQuestions.value.forEach((q) => {
        if (q.section_id && map.has(q.section_id)) {
            map.get(q.section_id).questions.push(q);
        } else {
            unsectioned.push(q);
        }
    });
    const result = Array.from(map.values()).filter((entry) => entry.questions.length);
    if (unsectioned.length) {
        result.push({ key: 'none', title: displayMode.value === 'sections' ? 'Без раздела' : null, questions: unsectioned });
    }
    if (displayMode.value === 'all') {
        return [{ key: 'all', title: null, questions: orderedQuestions.value }];
    }
    return result;
});

const sectionsOrdered = computed(() => renderSections.value);
const sectionIndex = ref(0);
const currentSection = computed(() => sectionsOrdered.value[sectionIndex.value] || null);
const sectionPosition = computed(() => sectionIndex.value + 1);
const sectionTotal = computed(() => sectionsOrdered.value.length);
const isLastSection = computed(() => sectionIndex.value >= sectionsOrdered.value.length - 1);
const progressPercent = computed(() => {
    if (!orderedQuestions.value.length) return 0;
    return Math.round(((currentQuestionIndex.value + 1) / orderedQuestions.value.length) * 100);
});

function answerFor(questionId) {
    if (!answers[questionId]) {
        answers[questionId] = {
            response_value: '',
            comment: '',
            photo_path: '',
            photo_url: '',
            skipped: false,
            showComment: false,
        };
    }
    return answers[questionId];
}

function toggleComment(questionId) {
    const answer = answerFor(questionId);
    answer.showComment = !answer.showComment;
}

function skipQuestion(questionId) {
    const answer = answerFor(questionId);
    answer.skipped = !answer.skipped;
    if (answer.skipped) {
        answer.response_value = '';
    }
}

function setDisplayMode(mode) {
    displayMode.value = mode;
}

function goNextQuestion() {
    if (currentQuestionIndex.value < orderedQuestions.value.length - 1) {
        currentQuestionIndex.value += 1;
        return;
    }
    submitChecklist();
}

function triggerPhotoInput(questionId) {
    const input = document.getElementById(`portal-photo-${questionId}`);
    if (input) {
        input.click();
    }
}

function setAnswer(questionId, value) {
    answerFor(questionId).response_value = value;
}

function setComment(questionId, value) {
    answerFor(questionId).comment = value;
}

function fieldError(questionId) {
    const question = orderedQuestions.value.find((q) => q.id === questionId);
    if (!question) return '';
    const answer = answerFor(questionId);
    if (answer.skipped) {
        return '';
    }
    if (question.required && !answer.response_value) {
        return 'Ответ обязателен.';
    }
    if (question.require_comment && !answer.comment) {
        return 'Нужен комментарий.';
    }
    if (question.require_photo && !answer.photo_path) {
        return 'Нужно фото.';
    }
    return '';
}

function hasRequirementMarker(question) {
    return Boolean(question?.require_comment || question?.require_photo);
}

function requirementLabel(question) {
    const labels = [];
    if (question?.require_comment) {
        labels.push('комментарий обязателен');
    }
    if (question?.require_photo) {
        labels.push('фото обязательно');
    }
    return labels.join(', ');
}

function setAuthToken(token) {
    setChecklistPortalToken(token);
    localStorage.setItem(portalTokenKey, token);
}

function clearAuth() {
    portalUser.value = null;
    localStorage.removeItem(portalTokenKey);
    clearChecklistPortalToken();
    if (draftSaveTimer) {
        clearTimeout(draftSaveTimer);
        draftSaveTimer = null;
    }
    closeRunModal();
    userMenuOpen.value = false;
    authStage.value = 'staff';
    loginForm.password = '';
    step.value = 'login';
}

async function finalizePortalLogin(data) {
    setAuthToken(data.access_token);
    portalUser.value = data.user;
    await loadChecklists();
    step.value = 'list';
}

async function handleStaffCodeLogin() {
    loginError.value = '';
    authLoading.value = true;
    try {
        const data = await startChecklistPortalLogin(loginForm.staffCode);
        if (data.requires_credentials) {
            authStage.value = 'credentials';
            loginForm.username = data.username_hint || '';
            loginForm.password = '';
            return;
        }
        await finalizePortalLogin(data);
    } catch (error) {
        loginError.value = error?.response?.data?.detail || 'Не удалось войти';
    } finally {
        authLoading.value = false;
    }
}

async function handleCredentialsLogin() {
    loginError.value = '';
    authLoading.value = true;
    try {
        const data = await finishChecklistPortalLogin({
            staff_code: loginForm.staffCode,
            username: loginForm.username,
            password: loginForm.password,
        });
        await finalizePortalLogin(data);
    } catch (error) {
        loginError.value = error?.response?.data?.detail || 'Не удалось войти';
    } finally {
        authLoading.value = false;
    }
}

function backToStaffStep() {
    authStage.value = 'staff';
    loginForm.username = '';
    loginForm.password = '';
    loginError.value = '';
}

async function loadChecklists() {
    listLoading.value = true;
    try {
        const data = await fetchChecklistPortalChecklists();
        checklists.value = Array.isArray(data) ? data : [];
    } catch {
        checklists.value = [];
    } finally {
        listLoading.value = false;
    }
}

async function selectChecklist(item) {
    selectedChecklist.value = item;
    submitError.value = '';
    showErrors.value = false;
    clearAnswers();
    try {
        const detailData = await fetchChecklistPortalChecklist(item.id);
        checklistDetail.value = detailData;
        const objectsData = await fetchChecklistPortalControlObjects(item.id);
        controlObjects.value = Array.isArray(objectsData) ? objectsData : [];
        selectedDepartment.value = controlObjects.value.length === 1
            ? controlObjects.value[0]
            : controlObjects.value.length
                ? ''
                : (portalUser.value?.default_department || '');
        displayMode.value = 'sections';
        currentQuestionIndex.value = 0;
        sectionIndex.value = 0;
        draftPromptVisible.value = false;
        runModalOpen.value = true;
        await loadDraft();
    } catch {
        submitError.value = 'Не удалось загрузить чек-лист.';
    }
}

async function loadDraft() {
    draftInfo.value = null;
    if (!selectedChecklist.value) {
        return;
    }
    try {
        const data = await fetchChecklistPortalDraft(selectedChecklist.value.id);
        draftInfo.value = data;
    } catch (error) {
        if (error?.response?.status !== 404) {
            submitError.value = 'Не удалось загрузить черновик.';
        }
    }
}

function applyDraft(draft) {
    if (!draft) return;
    clearAnswers();
    (draft.answers || []).forEach((item) => {
        answers[item.question_id] = {
            response_value: item.response_value || '',
            comment: item.comment || '',
            photo_path: item.photo_path || '',
            photo_url: item.photo_url || '',
            skipped: false,
            showComment: Boolean(item.comment),
        };
    });
    if (draft.department) {
        selectedDepartment.value = draft.department;
    }
}

async function handleStartChecklist() {
    objectError.value = '';
    submitError.value = '';
    if (controlObjects.value.length && !selectedDepartment.value) {
        objectError.value = 'Выберите ресторан.';
        return;
    }
    if (draftInfo.value) {
        draftPromptVisible.value = true;
        return;
    }
    await beginChecklist(false);
}

async function resumeDraft() {
    if (!draftInfo.value) {
        return;
    }
    draftPromptVisible.value = false;
    applyDraft(draftInfo.value);
    await beginChecklist(true);
}

async function startFresh() {
    draftPromptVisible.value = false;
    await deleteDraft();
    await beginChecklist(false);
}

async function beginChecklist(useDraft) {
    if (!useDraft) {
        clearAnswers();
    }
    currentQuestionIndex.value = 0;
    sectionIndex.value = 0;
    showErrors.value = false;
    step.value = 'fill';
    runModalOpen.value = false;
    await saveDraft(true);
}

async function deleteDraft() {
    if (!selectedChecklist.value) return;
    try {
        await deleteChecklistPortalDraft(selectedChecklist.value.id);
    } catch {
        // ignore
    }
    draftInfo.value = null;
}

async function saveDraft(force = false) {
    if (!selectedChecklist.value || step.value !== 'fill') {
        return;
    }
    const payloadAnswers = orderedQuestions.value.map((q) => {
        const answer = answerFor(q.id);
        return {
            question_id: q.id,
            response_value: answer.response_value || null,
            comment: answer.comment || null,
            photo_path: answer.photo_path || null,
        };
    });
    const hasAny = payloadAnswers.some(
        (item) => item.response_value || item.comment || item.photo_path,
    );
    if (!hasAny && !force) {
        return;
    }
    try {
        const data = await upsertChecklistPortalDraft(selectedChecklist.value.id, {
            department: selectedDepartment.value || null,
            answers: payloadAnswers,
        });
        draftInfo.value = data;
    } catch {
        // ignore draft save errors
    }
}

function scheduleDraftSave() {
    if (step.value !== 'fill') {
        return;
    }
    if (draftSaveTimer) {
        clearTimeout(draftSaveTimer);
    }
    draftSaveTimer = setTimeout(() => {
        draftSaveTimer = null;
        saveDraft(false);
    }, 700);
}

function closeRunModal() {
    runModalOpen.value = false;
    draftPromptVisible.value = false;
    resetRunState();
}

async function downloadReport(format) {
    if (!attemptId.value) {
        return;
    }
    try {
        const response = await exportChecklistPortalAttempt(attemptId.value, format);
        const contentType = response.headers['content-type'] || '';
        const extension = format === 'xlsx' ? 'xlsx' : 'pdf';
        const blob = new Blob([response.data], { type: contentType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `checklist_report_${attemptId.value}.${extension}`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    } catch {
        submitError.value = 'Не удалось скачать отчет.';
    }
}

async function loadAttemptSummary(id) {
    summaryLoading.value = true;
    attemptSummary.value = null;
    try {
        const data = await fetchChecklistPortalAttempt(id);
        attemptSummary.value = data;
    } catch {
        attemptSummary.value = null;
    } finally {
        summaryLoading.value = false;
    }
}

function resetRunState() {
    selectedChecklist.value = null;
    checklistDetail.value = null;
    controlObjects.value = [];
    selectedDepartment.value = '';
    submitError.value = '';
    objectError.value = '';
    showErrors.value = false;
    currentQuestionIndex.value = 0;
    sectionIndex.value = 0;
    draftInfo.value = null;
    draftPromptVisible.value = false;
    attemptId.value = null;
    attemptSummary.value = null;
    summaryLoading.value = false;
}

async function handlePhotoChange(questionId, event) {
    const file = event?.target?.files?.[0];
    if (!file) return;
    photoLoadingId.value = questionId;
    try {
        const formData = new FormData();
        formData.append('file', file);
        const data = await uploadChecklistPortalPhoto(formData);
        const answer = answerFor(questionId);
        answer.photo_path = data.photo_path;
        answer.photo_url = data.url || '';
        scheduleDraftSave();
    } catch {
        submitError.value = 'Не удалось загрузить фото.';
    } finally {
        photoLoadingId.value = null;
    }
}

async function submitChecklist() {
    showErrors.value = true;
    submitError.value = '';
    const requiredSections = new Set();
    const unansweredSections = new Set();
    orderedQuestions.value.forEach((q) => {
        const answer = answerFor(q.id);
        const sectionName = q.section_title || 'Без раздела';
        const errorText = fieldError(q.id);
        if (errorText) {
            requiredSections.add(sectionName);
            return;
        }
        if (!answer.skipped && !answer.response_value) {
            unansweredSections.add(sectionName);
        }
    });
    if (requiredSections.size) {
        submitError.value = `Вы не ответили на обязательные вопросы в разделах: ${[
            ...requiredSections,
        ].join(', ')}`;
        return;
    }
    if (unansweredSections.size) {
        const confirmText = `Вы ответили не на все вопросы в разделах: ${[
            ...unansweredSections,
        ].join(', ')}. Завершить?`;
        if (!window.confirm(confirmText)) {
            return;
        }
    }
    submitLoading.value = true;
    try {
        const data = await submitChecklistPortalAttempt({
            checklist_id: checklistDetail.value.id,
            department: selectedDepartment.value || null,
            answers: orderedQuestions.value.map((q) => {
                const answer = answerFor(q.id);
                return {
                    question_id: q.id,
                    response_value: answer.response_value || null,
                    comment: answer.comment || null,
                    photo_path: answer.photo_path || null,
                };
            }),
        });
        await deleteDraft();
        attemptId.value = data.attempt_id;
        await loadAttemptSummary(data.attempt_id);
        step.value = 'success';
    } catch (error) {
        submitError.value = error?.response?.data?.detail || 'Не удалось отправить чек-лист.';
    } finally {
        submitLoading.value = false;
    }
}

function resetToList() {
    closeRunModal();
    step.value = 'list';
}

function nextSection() {
    if (sectionIndex.value < sectionsOrdered.value.length - 1) {
        sectionIndex.value += 1;
    }
}

function prevSection() {
    if (sectionIndex.value > 0) {
        sectionIndex.value -= 1;
    }
}

function handleSectionsAction() {
    if (isLastSection.value) {
        submitChecklist();
        return;
    }
    nextSection();
}

function handleLogout() {
    userMenuOpen.value = false;
    clearAuth();
}

function toggleUserMenu() {
    userMenuOpen.value = !userMenuOpen.value;
}

function closeUserMenu() {
    userMenuOpen.value = false;
}

watch(
    answers,
    () => {
        scheduleDraftSave();
    },
    { deep: true },
);

watch(selectedDepartment, () => {
    scheduleDraftSave();
});

onMounted(async () => {
    const token = localStorage.getItem(portalTokenKey);
    if (token) {
        setAuthToken(token);
        try {
            const data = await fetchChecklistPortalMe();
            portalUser.value = data;
            await loadChecklists();
            step.value = 'list';
            return;
        } catch {
            clearAuth();
        }
    }
    step.value = 'login';
});

onBeforeUnmount(() => {
    if (draftSaveTimer) {
        clearTimeout(draftSaveTimer);
        draftSaveTimer = null;
    }
});
</script>

<style lang="scss">
@use '@/assets/styles/pages/checklist-portal' as *;
</style>
