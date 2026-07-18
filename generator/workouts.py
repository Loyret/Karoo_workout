from __future__ import annotations

from dataclasses import dataclass, field
from generator.zwo import Workout, WorkoutStep


@dataclass
class WorkoutTemplate:
    id: str
    name: str
    category: str
    difficulty: int  # 1-5
    duration_min: int
    description: str
    explanation: str
    builder: object = field(repr=False)
    tips: list[str] = field(default_factory=list)
    ftp_required: bool = True

    def build(self, ftp: int) -> Workout:
        return self.builder(ftp)


def _build_endurance(ftp: int) -> Workout:
    return Workout(
        name="Выносливость — Длинная поездка",
        description="Классическая тренировка на развитие аэробной базы. "
        "Стабильная работа в Z2 формирует фундамент для всех "
        "последующих улучшений.",
        tags=["endurance", "base"],
        steps=[
            WorkoutStep(
                type="Warmup", duration=600,
                power_low=0.50, power_high=0.60,
                cadence=85,
                text="Разминка: начните мягко, постепенно увеличивайте нагрузку",
            ),
            WorkoutStep(
                type="SteadyState", duration=2400,
                power=0.70, cadence=88,
                text="Основная часть: ровная езда в зоне выносливости",
            ),
            WorkoutStep(
                type="SteadyState", duration=1800,
                power=0.72, cadence=90,
                text="Немного усильте нагрузку, сохраняя комфорт",
            ),
            WorkoutStep(
                type="SteadyState", duration=1200,
                power=0.68, cadence=85,
                text="Снизьте нагрузку, начинайте восстанавливаться",
            ),
            WorkoutStep(
                type="Cooldown", duration=600,
                power_low=0.45, power_high=0.55,
                cadence=75,
                text="Заминка: расслабьтесь, глубоко дышите",
            ),
        ],
    )


def _build_tempo(ftp: int) -> Workout:
    return Workout(
        name="Темповая работа — Холмистая местность",
        description="Чередование темповых отрезков с восстановлением. "
        "Развивает способность держать повышенную мощность продолжительное время.",
        tags=["tempo", "sweetspot"],
        steps=[
            WorkoutStep(
                type="Warmup", duration=600,
                power_low=0.50, power_high=0.65,
                cadence=85,
                text="Разотрите ноги, подготовьтесь к основной части",
            ),
            WorkoutStep(
                type="SteadyState", duration=600,
                power=0.72, cadence=90,
                text="Въезд на холм: поддерживайте стабильный темп",
            ),
            WorkoutStep(
                type="Intervals", repeat=4,
                on_steps=[WorkoutStep(type="SteadyState", duration=180, power=0.88, cadence=92,
                                      text="Подъём: усильте темп, но контролируйте дыхание")],
                off_steps=[WorkoutStep(type="SteadyState", duration=120, power=0.60, cadence=80,
                                       text="Спуск: восстановление, лёгкое кручение")],
            ),
            WorkoutStep(
                type="SteadyState", duration=900,
                power=0.70, cadence=88,
                text="Ровный участок: стабильная работа",
            ),
            WorkoutStep(
                type="Cooldown", duration=600,
                power_low=0.40, power_high=0.50,
                cadence=75,
                text="Заминка: расслабьтесь",
            ),
        ],
    )


def _build_threshold(ftp: int) -> Workout:
    return Workout(
        name="Пороговая — Классическая 2x20",
        description="Два длинных 20-минутных отрезка на FTP. "
        "Это золотой стандарт тренировок для роста пороговой мощности. "
        "Каждый отрезок — это работа на пределе ваших возможностей.",
        tags=["threshold", "ftp"],
        steps=[
            WorkoutStep(
                type="Warmup", duration=900,
                power_low=0.50, power_high=0.75,
                cadence=85,
                text="Разминка: постепенно выходите на рабочий темп. "
                "Последние 2 минуты — лёгкие ускорения по 10 сек.",
            ),
            WorkoutStep(
                type="Intervals", repeat=2,
                on_steps=[WorkoutStep(
                    type="SteadyState", duration=1200,
                    power=0.95, cadence=90,
                    text="Рабочий отрезок: стабильная мощность на FTP. "
                    "Дышите ровно, не давайте пульсу взлететь.",
                )],
                off_steps=[WorkoutStep(
                    type="SteadyState", duration=300,
                    power=0.50, cadence=75,
                    text="Восстановление: лёгкое кручение, глубокое дыхание",
                )],
            ),
            WorkoutStep(
                type="Cooldown", duration=600,
                power_low=0.40, power_high=0.50,
                cadence=70,
                text="Заминка: расслабьтесь, восстановите дыхание",
            ),
        ],
    )


def _build_vo2max(ftp: int) -> Workout:
    return Workout(
        name="VO2max — Интервалы 5x3",
        description="Пять 3-минутных интервалов на 115-120% FTP. "
        "Максимально нагружают аэробную систему, развивают "
        "максимальное потребление кислорода.",
        tags=["vo2max", "intervals"],
        steps=[
            WorkoutStep(
                type="Warmup", duration=900,
                power_low=0.50, power_high=0.80,
                cadence=85,
                text="Разминка: 3 ускорения по 30 секунд в конце",
            ),
            WorkoutStep(
                type="Intervals", repeat=5,
                on_steps=[WorkoutStep(
                    type="SteadyState", duration=180,
                    power=1.18, cadence=95,
                    text="Максимум! Держите мощность, не спадайте!",
                )],
                off_steps=[WorkoutStep(
                    type="SteadyState", duration=180,
                    power=0.45, cadence=70,
                    text="Восстановление: глубокое дыхание, лёгкое кручение",
                )],
            ),
            WorkoutStep(
                type="Cooldown", duration=600,
                power_low=0.40, power_high=0.50,
                cadence=70,
                text="Заминка: медленно снижайте нагрузку",
            ),
        ],
    )


def _build_sweet_spot(ftp: int) -> Workout:
    return Workout(
        name="Sweet Spot — Идеальный баланс",
        description="Работа на 88-93% FTP — 'сладкая зона'. "
        "Максимальная отдача при минимальных затратах на восстановление. "
        "Идеально для занятого графика.",
        tags=["sweetspot", "efficiency"],
        steps=[
            WorkoutStep(
                type="Warmup", duration=600,
                power_low=0.50, power_high=0.70,
                cadence=85,
                text="Разминка: подготовьтесь к длинным отрезкам",
            ),
            WorkoutStep(
                type="Intervals", repeat=3,
                on_steps=[WorkoutStep(
                    type="SteadyState", duration=600,
                    power=0.90, cadence=90,
                    text="Sweet Spot:comfortably hard. Вы должны чувствовать "
                    "лёгкий дискомфорт, но контролировать дыхание.",
                )],
                off_steps=[WorkoutStep(
                    type="SteadyState", duration=180,
                    power=0.55, cadence=75,
                    text="Восстановление: расслабьтесь",
                )],
            ),
            WorkoutStep(
                type="SteadyState", duration=600,
                power=0.70, cadence=88,
                text="Дожимаем: ровная работа до конца",
            ),
            WorkoutStep(
                type="Cooldown", duration=600,
                power_low=0.40, power_high=0.50,
                cadence=70,
                text="Заминка",
            ),
        ],
    )


def _build_hiit(ftp: int) -> Workout:
    return Workout(
        name="HIIT — Взрывные спринты",
        description="Чередование максимальных 15-секундных спринтов "
        "с активным восстановлением. Развивает максимальную мощность "
        "и нейромышечную связь.",
        tags=["hiit", "sprints", "power"],
        steps=[
            WorkoutStep(
                type="Warmup", duration=900,
                power_low=0.50, power_high=0.85,
                cadence=85,
                text="Разминка: 4 нарастания по 15 сек до высокой мощности",
            ),
            WorkoutStep(
                type="Intervals", repeat=8,
                on_steps=[WorkoutStep(
                    type="SteadyState", duration=15,
                    power=1.60, cadence=110,
                    text="СПРИНТ! Максимум! Взрывная мощность!",
                )],
                off_steps=[WorkoutStep(
                    type="SteadyState", duration=75,
                    power=0.40, cadence=65,
                    text="Восстановление: полный отдых",
                )],
            ),
            WorkoutStep(
                type="Cooldown", duration=600,
                power_low=0.40, power_high=0.50,
                cadence=70,
                text="Заминка: не останавливайтесь резко",
            ),
        ],
    )


def _build_active_recovery(ftp: int) -> Workout:
    return Workout(
        name="Активное восстановление",
        description="Лёгкая поездка для ускорения восстановления. "
        "Низкая мощность стимулирует кровоток без создания "
        "дополнительного стресса.",
        tags=["recovery", "easy"],
        steps=[
            WorkoutStep(
                type="Warmup", duration=300,
                power_low=0.30, power_high=0.45,
                cadence=80,
                text="Начните очень легко",
            ),
            WorkoutStep(
                type="SteadyState", duration=2700,
                power=0.45, cadence=80,
                text="Лёгкая езда: наслаждайтесь процессом. "
                "Если устаёте — снизьте мощность.",
            ),
            WorkoutStep(
                type="Cooldown", duration=300,
                power_low=0.30, power_high=0.40,
                cadence=70,
                text="Завершите поездку",
            ),
        ],
    )


@dataclass
class WorkoutTemplates:
    templates: list[WorkoutTemplate] = field(default_factory=lambda: [
        WorkoutTemplate(
            id="endurance",
            name="Выносливость",
            category="Базовая",
            difficulty=2,
            duration_min=75,
            description="Классическая тренировка на развитие аэробной базы",
            explanation=(
                "Тренировка в зоне выносливости (Z2) — фундамент "
                "всей велосипедной подготовки. Развивает капилляризацию "
                "мышц, увеличивает количество митохондрий и улучшает "
                "способность организма использовать жир как источник энергии. "
                "Это самая важная тренировка для начинающих и "
                "опытных гонщиков одинаково."
            ),
            tips=[
                "Пульс должен оставаться в комфортном диапазоне",
                "Вы должны свободно разговаривать во время поездки",
                "Если не можете — снизьте мощность",
                "Идеально для длинных выходных поездок",
            ],
            builder=_build_endurance,
        ),
        WorkoutTemplate(
            id="tempo",
            name="Темповая работа",
            category="Базовая",
            difficulty=3,
            duration_min=60,
            description="Развитие темповой выносливости на холмах",
            explanation=(
                "Темповая зона (Z3) находится между комфортной ездой и "
                "тяжёлой работой. Развивает способность поддерживать "
                "повышенную мощность в течение длительного времени. "
                "Это мостик между базовой подготовкой и "
                "специфическими интервалами."
            ),
            tips=[
                "Не берите слишком высоко — это не гонка",
                "Контролируйте дыхание: вдох на 2-3 педали, выдох на 2-3",
                "Поддерживайте стабильный каденс",
                "Отлично подходит для имитации подъёмов",
            ],
            builder=_build_tempo,
        ),
        WorkoutTemplate(
            id="sweetspot",
            name="Sweet Spot",
            category="Эффективность",
            difficulty=3,
            duration_min=60,
            description="Идеальный баланс нагрузки и восстановления",
            explanation=(
                "Sweet Spot (88-93% FTP) — это 'золотая середина' "
                "тренировок. Вы получаете 90% пользы от пороговых "
                "тренировок, но тратите меньше времени на восстановление. "
                "Идеально для тех, кто тренируется 4-6 раз в неделю."
            ),
            tips=[
                "Должно быть 'комфортно тяжело'",
                "Если можете говоритьполными предложениями — слишком легко",
                "Если задыхаетесь — слишком тяжело",
                "Лучший ROI тренировочных усилий",
            ],
            builder=_build_sweet_spot,
        ),
        WorkoutTemplate(
            id="threshold",
            name="Пороговая 2x20",
            category="Развитие силы",
            difficulty=4,
            duration_min=75,
            description="Классическая пороговая тренировка для роста FTP",
            explanation=(
                "Два 20-минутных отрезка на 95% FTP — это 'золотой "
                "стандарт' тренировок. Работа на пороге лактата стимулирует "
                "рост mitochondria и увеличивает FTP. Это самая "
                "результативная тренировка для увеличения "
                "пороговой мощности."
            ),
            tips=[
                "Сосредоточьтесь на стабильной мощности, не пульсе",
                "Используйте ровную дорогу или тренажёр",
                "Последние 5 минут будут тяжёлыми — это нормально",
                "Не увеличивайте мощность в начале — сэкономьте силы",
            ],
            builder=_build_threshold,
        ),
        WorkoutTemplate(
            id="vo2max",
            name="VO2max 5x3",
            category="Максимальная мощность",
            difficulty=5,
            duration_min=50,
            description="Развитие максимального потребления кислорода",
            explanation=(
                "Интервалы на 115-120% FTP максимально нагружают "
                "аэробную систему. Организм адаптируется, увеличивая "
                "максимальное потребление кислорода (VO2max). Это "
                "определяет ваш потолок мощности."
            ),
            tips=[
                "Каждый интервал — максимальное усилие",
                "Восстановление критически важно — не пропускайте",
                "Если не можете держать мощность на 5 интервале — нормально",
                "Не делайте чаще 1-2 раз в неделю",
            ],
            builder=_build_vo2max,
        ),
        WorkoutTemplate(
            id="hiit",
            name="HIIT Спринты",
            category="Максимальная мощность",
            difficulty=5,
            duration_min=40,
            description="Взрывные спринты для максимальной мощности",
            explanation=(
                "Короткие максимальные спринты развивают "
                "нейромышечную связь, максимальную мощность и "
                "способность к восстановлению. Это 'шорткат' "
                "к увеличению мощности для коротких подъёмов и финишей."
            ),
            tips=[
                "Каждый спринт —настоящим максимум",
                "Встаньте на педали для максимальной мощности",
                "Не жалейте сил на спринт — для этого он и нужен",
                "Идеально на ровной дороге или тренажёре",
            ],
            builder=_build_hiit,
        ),
        WorkoutTemplate(
            id="recovery",
            name="Активное восстановление",
            category="Восстановление",
            difficulty=1,
            duration_min=45,
            description="Лёгкая поездка для ускорения восстановления",
            explanation=(
                "Активное восстановление ускоряет процесс "
                "восстановления за счёт увеличения кровотока в мышцах. "
                "Низкая мощность не создаёт дополнительного стресса, "
                "но помогает вывести продукты распада. "
                "Идеально после тяжёлых тренировок."
            ),
            tips=[
                "Если устаёте — вы перегружены, остановитесь",
                "Можно совместить с прогулкой или поездкой за покупками",
                "Пульс не должен превышать 60% максимального",
                "Главное правило: ' легче — лучше'",
            ],
            builder=_build_active_recovery,
        ),
    ])

    def get_by_id(self, template_id: str) -> WorkoutTemplate | None:
        for t in self.templates:
            if t.id == template_id:
                return t
        return None

    def get_by_category(self, category: str) -> list[WorkoutTemplate]:
        return [t for t in self.templates if t.category == category]

    def get_categories(self) -> list[str]:
        return list({t.category for t in self.templates})
