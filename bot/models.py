from dataclasses import dataclass, field


@dataclass
class Listing:
    platform: str
    listing_id: str
    url: str
    title: str = ""
    price: str = ""
    rooms: float | None = None
    size: str = ""
    address: str = ""
    raw: dict = field(default_factory=dict)

    @property
    def key(self) -> tuple[str, str]:
        return (self.platform, self.listing_id)
