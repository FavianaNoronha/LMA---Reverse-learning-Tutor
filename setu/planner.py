"""Turn choice v0: about 1 turn in 5 is a no-error turn, drawn only from rules the classmate
has been taught (it cannot use a rule correctly before that)."""
import random
from .state import RajuState


def choose_turn(raju: RajuState, rng: random.Random, p_no_error: float = 0.2) -> tuple[str, str] | None:
    taught = [r for r, s in raju.rules.items() if s == "taught"]
    plantable = raju.eligible_to_plant()
    if taught and (not plantable or rng.random() < p_no_error):
        return "no_error", rng.choice(taught)
    if plantable:
        return "planted", rng.choice(plantable)
    return None
