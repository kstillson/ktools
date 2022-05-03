
from dataclasses import dataclass

@dataclass
class WL:
    container_name: str
    user: str
    allow_children: bool
    required: bool
    regex: str
    hit_last: int = 0
    hit_count: int = 0
    hit_count_last_scan: int = 0
    
