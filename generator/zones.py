from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Zone:
    name: str
    short: str
    power_low: float  # % of FTP
    power_high: float
    description: str
    purpose: str
    color: str

    def power_range(self, ftp: int) -> tuple[int, int]:
        return (int(ftp * self.power_low), int(ftp * self.power_high))

    def midpoint_watts(self, ftp: int) -> int:
        return int(ftp * (self.power_low + self.power_high) / 2)


class TrainingZones:
    ZONES = [
        Zone(
            name="Восстановление",
            short="Z1",
            power_low=0.00,
            power_high=0.55,
            description="Очень лёгкая нагрузка, восстановление между интервалами",
            purpose="Восстановление, разминка, заминка",
            color="#3b82f6",
        ),
        Zone(
            name="Выносливость",
            short="Z2",
            power_low=0.56,
            power_high=0.75,
            description="Комфортный темп, можно разговаривать",
            purpose="Базовая выносливость, длинные поездки, аэробная база",
            color="#22c55e",
        ),
        Zone(
            name="Темповая",
            short="Z3",
            power_low=0.76,
            power_high=0.90,
            description="Умеренно тяжело, разговоры затруднены",
            purpose="Темповая работа, гонки на средней дистанции",
            color="#eab308",
        ),
        Zone(
            name="Пороговая",
            short="Z4",
            power_low=0.91,
            power_high=1.05,
            description="Тяжело, можно сказать только несколько слов",
            purpose="Рост FTP, гонки, подъёмы",
            color="#f97316",
        ),
        Zone(
            name="Максимальная",
            short="Z5",
            power_low=1.06,
            power_high=1.20,
            description="Очень тяжело, одиночные слова",
            purpose="VO2max, максимальная аэробная мощность",
            color="#ef4444",
        ),
        Zone(
            name="Анаэробная",
            short="Z6",
            power_low=1.21,
            power_high=1.50,
            description="Максимальные усилия до 2 минут",
            purpose="Анаэробная выносливость, спринты",
            color="#dc2626",
        ),
        Zone(
            name="Нейромышечная",
            short="Z7",
            power_low=1.51,
            power_high=2.50,
            description="Максимальная мощность, спринты до 15 секунд",
            purpose="Максимальная мощность, нейромышечная адаптация",
            color="#991b1b",
        ),
    ]

    @classmethod
    def get_zone_for_power(cls, power_pct: float) -> Zone | None:
        for zone in reversed(cls.ZONES):
            if power_pct >= zone.power_low:
                return zone
        return cls.ZONES[0]

    @classmethod
    def get_zone_color(cls, power_pct: float) -> str:
        zone = cls.get_zone_for_power(power_pct)
        return zone.color if zone else "#3b82f6"
