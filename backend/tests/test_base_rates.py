"""
Fase 3 (T1): tasas base del crecimiento de las ventas (config/base_rates.toml), extraídas del Exhibit 3 de Mauboussin y
Callahan, "The Impact of Intangibles on Base Rates" (Morgan Stanley, 2021). Comprobaciones de integridad de la
extracción: la usa el DCF inverso (T3).
"""
import pytest

from settings import cfg

BINS = ("0-1", "1-5", "5-10", "10-25", "25-50", "50-100", "100+")
INDUSTRIES = ("Healthcare", "Technology", "Consumer", "Manufacturing", "Other", "All")


def test_every_bin_and_industry_has_four_horizons():
    T = cfg("base_rates.table")
    assert set(T) == {"todas", *BINS}
    for b in T:
        assert set(T[b]) == set(INDUSTRIES), b
        for ind, row in T[b].items():
            for k in ("median", "mean", "std", "count"):
                assert len(row[k]) == len(cfg("base_rates.horizons_years")), (b, ind, k)


@pytest.mark.parametrize("ind", INDUSTRIES)
def test_size_bins_add_up_to_the_full_universe(ind):
    """El recuento de observaciones de los siete tramos suma el del universo completo (la tabla se extrajo entera)."""
    T = cfg("base_rates.table")
    total = [sum(T[b][ind]["count"][h] for b in BINS) for h in range(4)]
    assert total == list(T["todas"][ind]["count"])


def test_industry_counts_add_up_to_all():
    T = cfg("base_rates.table")
    for b in ("todas", *BINS):
        parts = [sum(T[b][i]["count"][h] for i in INDUSTRIES if i != "All") for h in range(4)]
        assert parts == list(T[b]["All"]["count"]), b


def test_values_quoted_in_the_text_of_the_paper():
    """p. 4: mediana del CAGR a 5 años: Healthcare 10.4%, Technology 7.9%, Consumer 6.0%, Manufacturing 5.0%, todas 6.5%."""
    T = cfg("base_rates.table")["todas"]
    assert [T[i]["median"][2] for i in ("Healthcare", "Technology", "Consumer", "Manufacturing", "All")] == \
        [0.104, 0.079, 0.06, 0.05, 0.065]


def test_bins_lower_bounds_are_increasing():
    b = cfg("base_rates.bins")
    assert [b[k] for k in BINS] == sorted(b[k] for k in BINS)
