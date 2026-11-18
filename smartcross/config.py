from dataclasses import asdict, dataclass, replace


def number(value, minimum, maximum):
    if type(value) not in (int, float) or not minimum <= value <= maximum:
        raise ValueError(f"Informe um número entre {minimum} e {maximum}.")
    return float(value)


@dataclass(frozen=True)
class ROI:
    x: float = .18
    y: float = .58
    width: float = .64
    height: float = .32

    def contains(self, box, width, height):
        left, _, right, bottom = box
        x, y = (left + right) / (2 * width), bottom / height
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

    @classmethod
    def parse(cls, data):
        if not isinstance(data, dict) or set(data) != {"x", "y", "width", "height"}:
            raise ValueError("Informe x, y, width e height.")
        roi = cls(number(data["x"], 0, 1), number(data["y"], 0, 1),
                  number(data["width"], .01, 1), number(data["height"], .01, 1))
        if roi.x + roi.width > 1 or roi.y + roi.height > 1:
            raise ValueError("A zona deve ficar inteiramente dentro da imagem.")
        return roi


@dataclass(frozen=True)
class Settings:
    roi: ROI = ROI()
    confidence: float = .45
    confirmation: float = .8
    hold: float = 2.5

    def update(self, fields):
        limits = {"confidence": (.05, .99), "confirmation": (.1, 10), "hold": (0, 30)}
        if not fields or set(fields) - (limits.keys() | {"roi"}):
            raise ValueError("Parâmetros inválidos.")
        changes = {key: ROI.parse(value) if key == "roi" else number(value, *limits[key])
                   for key, value in fields.items()}
        return replace(self, **changes)

    def json(self):
        return asdict(self)
