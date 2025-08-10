from pathlib import Path
from .minimum_wage import __load_minimum_wage__

__all__ = ('minimum_wage')

DATA_DIR = Path(__file__).parent

minimum_wage = __load_minimum_wage__()


