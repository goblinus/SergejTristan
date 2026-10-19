export const meta = {
  name: 'design-dividend-calendar',
  description: 'Проектирование MVP автообновляемого дивидендного календаря: system-designer ставит задачи дизайнерам, ревьюит и отправляет на доработку (до 3 раундов)',
  phases: [
    { title: 'План', detail: 'system-designer декомпозирует проектирование на задачи' },
    { title: 'Проектирование', detail: 'ui/frontend/backend/system дизайнеры пишут спецификации' },
    { title: 'Ревью', detail: 'system-designer проверяет и согласовывает' },
    { title: 'Доработка', detail: 'дизайнеры устраняют замечания (до 3 раундов)' },
  ],
}

const DATE = (args && args.date) || '2026-10-19'
const MAX_ROUNDS = 3

const PLAN_SCHEMA = {
  type: 'object',
  properties: {
    areas: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          area: { type: 'string', enum: ['system', 'ui', 'frontend', 'backend'] },
          tasks: { type: 'array', items: { type: 'string' } },
        },
        required: ['area', 'tasks'],
      },
    },
  },
  required: ['areas'],
}

const DESIGN_RESULT = {
  type: 'object',
  properties: {
    files: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['files'],
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    approved: { type: 'boolean' },
    issues: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          area: { type: 'string', enum: ['ui', 'frontend', 'backend'] },
          file: { type: 'string' },
          problem: { type: 'string' },
          task: { type: 'string' },
        },
        required: ['area', 'problem', 'task'],
      },
    },
    notes: { type: 'string' },
  },
  required: ['approved', 'issues'],
}

const MODEL_BY_AREA = { system: 'opus', ui: 'sonnet', frontend: 'sonnet', backend: 'sonnet' }

const ROLE_PROMPTS = {
  system: `Ты — системный архитектор проекта («system-designer»). Твоя зона: верхнеуровневая архитектура, ADR в design/system/adr/, ревью и согласование спецификаций дизайнеров областей ui/frontend/backend, разрешение противоречий между ними, постановка задач на доработку. Write/Edit — только внутри design/system/, остальное — только чтение. Production-код не пишешь.`,
  ui: `Ты — UI/UX-дизайнер проекта («ui-designer»). Твоя зона: UX-сценарии, макеты экранов (текстово-структурные описания, wireframe/ASCII при необходимости), UI-kit тёмной Material-темы (цвета, типографика, отступы, базовые элементы), состояния дивидендных событий. Write/Edit — только внутри design/ui/, остальное — только чтение. Production-код не пишешь.`,
  frontend: `Ты — проектировщик фронтенда («frontend-designer»). Стек: JavaScript/TypeScript, Vue.js 3 (Composition API), тёмная Material-тема. Твоя зона: компонентная архитектура, управление состоянием, роутинг, контракты к backend API, требования компонентов из макетов ui-designer (design/ui/). Write/Edit — только внутри design/frontend/, остальное — только чтение. Production-код не пишешь.`,
  backend: `Ты — проектировщик бэкенда («backend-designer»). Стек: Python, SQLAlchemy, Pydantic (uv для зависимостей). Твоя зона: схема БД, API-контракты (REST), архитектура модулей (сборщик данных, парсер/нормализатор, API-сервис, планировщик), требования к интеграциям с источниками сущфактов. Write/Edit — только внутри design/backend/, остальное — только чтение. Production-код не пишешь.`,
}

const CONTEXT = `Проект «Дивидендный календарь» — автообновляемый сервис для непрофессиональных личных инвестиций на российском фондовом рынке (MVP).

Функциональность MVP:
- список тикеров Московской биржи;
- календарь собраний акционеров, на которых решается вопрос о выплате дивидендов;
- хранение дат дивидендной отсечки (дата закрытия реестра) перед собранием акционеров;
- «сторожок»: пользователь выбирает тикеры и отслеживает приближение даты дивидендной отсечки;
- страница пользователя: выбор тикеров для отслеживания.

Состав:
- фронтенд: JavaScript/TypeScript, Vue.js 3 (Composition API), основная тема интерфейса — тёмный Material;
- бэкенд: Python, SQLAlchemy, Pydantic (uv для зависимостей);
- база данных;
- набор инструментов (скрипты) сбора данных из официальных источников (moex.com, disclosure.ru и т.п.), их нормализации и сохранения в БД.`

const COMMON_RULES = `Общие требования к документам:
- формат markdown, схемы — PlantUML (отдельные файлы .puml рядом с .md);
- сохранять в design/<твоя область>/, именование: ${DATE}_название-документа_<область>.md;
- владелец утвердил этот workflow — подтверждение на запись файлов в твоей области уже получено, повторно не запрашивай;
- проектируется MVP — избегай избыточной функциональности, выходящей за описанный объём;
- задач на разработку нет: только проектная документация.`

// --- План ---
phase('План')
const plan = await agent(
  `${ROLE_PROMPTS.system}\n\n${CONTEXT}\n\n` +
  `Составь план проектирования MVP. Для каждой области (system — твои собственные документы архитектуры и ADR, ui, frontend, backend) сформулируй список конкретных задач: какие документы должны быть подготовлены, какие вопросы каждый документ закрывает. ` +
  `Учитывай будущую стыковку: модель данных (тикеры, собрания, даты отсечки, «сторожки»), API-контракты бэкенда и фронтенда, UX-сценарии страницы пользователя и календаря, стилистика тёмной Material-темы, формат скриптов сбора данных.\n\n${COMMON_RULES}`,
  { model: MODEL_BY_AREA.system, schema: PLAN_SCHEMA, label: 'план проектирования' }
)
if (!plan) throw new Error('system-designer не вернул план')
log(`План готов: ${plan.areas.map(a => `${a.area} (${a.tasks.length} задач)`).join(', ')}`)

// --- Проектирование ---
phase('Проектирование')
const drafts = await parallel(plan.areas.map(a => () =>
  agent(
    `${ROLE_PROMPTS[a.area]}\n\n${CONTEXT}\n\n` +
    `Твои задачи от system-designer:\n${a.tasks.map((t, i) => `${i + 1}. ${t}`).join('\n')}\n\n` +
    `Выполни все задачи: подготовь документы проектирования для области «${a.area}». Верни список созданных файлов.\n\n${COMMON_RULES}`,
    { model: MODEL_BY_AREA[a.area], schema: DESIGN_RESULT, phase: 'Проектирование', label: `проектирование: ${a.area}` }
  )
))
const allFiles = drafts.filter(Boolean).flatMap(d => d.files)
log(`Подготовлено документов: ${allFiles.length}`)

// --- Ревью и доработки ---
let unresolved = []
let roundsUsed = 0
for (let round = 1; round <= MAX_ROUNDS; round++) {
  roundsUsed = round
  const review = await agent(
    `${ROLE_PROMPTS.system}\n\n${CONTEXT}\n\n` +
    `Проведи ревью всех спецификаций в design/ (раунд ${round} из ${MAX_ROUNDS}). Проверь: соответствие объёму MVP, консистентность модели данных (тикеры, собрания, отсечки, «сторожки»), API-контрактов и UX-сценариев между областями ui, frontend и backend, полноту покрытия функциональности. ` +
    `Результат ревью зафиксируй файлом в design/system/. Если всё согласовано — approved=true. Иначе верни список замечаний: область, файл, проблема, задача на доработку для ответственного дизайнера.\n\n${COMMON_RULES}`,
    { model: MODEL_BY_AREA.system, schema: REVIEW_SCHEMA, phase: 'Ревью', label: `ревью, раунд ${round}` }
  )
  if (!review || review.approved || review.issues.length === 0) {
    unresolved = []
    log(`Ревью раунда ${round}: согласовано`)
    break
  }
  log(`Ревью раунда ${round}: ${review.issues.length} замечаний`)
  if (round === MAX_ROUNDS) { unresolved = review.issues; break }

  const byArea = {}
  for (const issue of review.issues) {
    (byArea[issue.area] = byArea[issue.area] || []).push(issue)
  }
  await parallel(Object.entries(byArea).map(([area, issues]) => () =>
    agent(
      `${ROLE_PROMPTS[area]}\n\n${CONTEXT}\n\n` +
      `Замечания system-designer по твоей области (раунд ${round}):\n` +
      issues.map((is, i) => `${i + 1}. [${is.file || 'общее'}] ${is.problem}\n   Задача: ${is.task}`).join('\n') +
      `\n\nДоработай свои документы в design/${area}/ по каждому замечанию. Верни список изменённых файлов.\n\n${COMMON_RULES}`,
      { model: MODEL_BY_AREA[area], schema: DESIGN_RESULT, phase: 'Доработка', label: `доработка: ${area}, раунд ${round}` }
    )
  ))
}

return {
  plan: plan.areas,
  files: allFiles,
  roundsUsed,
  unresolved,
}
