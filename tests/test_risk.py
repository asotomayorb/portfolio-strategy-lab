import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
import numpy as np
import pandas as pd
from risk import erc_weights

def test_erc_sums_to_one_and_is_positive():
    rng = np.random.default_rng(7)
    x = pd.DataFrame(rng.normal(size=(200,3)), columns=list("ABC"))
    w = erc_weights(x)
    assert abs(w.sum() - 1) < 1e-8
    assert (w > 0).all()
