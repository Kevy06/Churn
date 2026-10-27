import numpy as np
import pandas as pd
import pytest

import churn as ch


def base_pequena() -> pd.DataFrame:
    return pd.DataFrame({
        "customerID": ["A", "B", "C", "C", "D"],
        "tenure": [0, 10, 24, 24, 5],
        "MonthlyCharges": [50.0, 70.0, 90.0, 90.0, 30.0],
        "TotalCharges": [" ", "700", "2160", "2160", "150"],
        "Contract": ["Month-to-month", "One year", "Two year", "Two year", "Month-to-month"],
        "InternetService": ["DSL", "Fiber optic", "No", "No", "DSL"],
        "PhoneService": ["Yes", "Yes", "No", "No", "Yes"],
        "MultipleLines": ["No", "Yes", "No phone service", "No phone service", "No"],
        "OnlineSecurity": ["No", "Yes", "No internet service", "No internet service", "No"],
        "OnlineBackup": ["No", "No", "No internet service", "No internet service", "Yes"],
        "DeviceProtection": ["No", "No", "No internet service", "No internet service", "No"],
        "TechSupport": ["No", "Yes", "No internet service", "No internet service", "No"],
        "StreamingTV": ["No", "No", "No internet service", "No internet service", "No"],
        "StreamingMovies": ["No", "No", "No internet service", "No internet service", "No"],
        "Churn": ["No", "Yes", "No", "No", "Yes"],
    })


def base_sintetica(n=400, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    tenure = rng.integers(0, 72, n)
    contrato = rng.choice(["Month-to-month", "One year", "Two year"], n, p=[0.55, 0.25, 0.20])
    mensal = rng.uniform(20, 110, n).round(2)
    risco = 0.6 * (contrato == "Month-to-month") + 0.4 * (tenure < 12)
    churn = np.where(rng.random(n) < 0.1 + 0.5 * risco, "Yes", "No")
    sim_nao = lambda: rng.choice(["Yes", "No"], n)
    return pd.DataFrame({
        "customerID": [f"C{i}" for i in range(n)], "tenure": tenure, "MonthlyCharges": mensal,
        "TotalCharges": (tenure * mensal).astype(str), "Contract": contrato,
        "InternetService": rng.choice(["DSL", "Fiber optic", "No"], n),
        "PhoneService": sim_nao(), "MultipleLines": sim_nao(), "OnlineSecurity": sim_nao(),
        "OnlineBackup": sim_nao(), "DeviceProtection": sim_nao(), "TechSupport": sim_nao(),
        "StreamingTV": sim_nao(), "StreamingMovies": sim_nao(), "Churn": churn,
    })


def test_inspecionar_detecta_branco_e_duplicado():
    d = ch.inspecionar_dados(base_pequena())
    assert d["textos_em_branco"]["TotalCharges"] == 1
    assert d["customerID_duplicados"] == 1


def test_limpeza_totalcharges_duplicados_e_bruto_intacto():
    bruto = base_pequena()
    limpo, rel = ch.limpar_dados(bruto)
    assert len(limpo) == 4
    assert rel["duplicados_removidos"] == 1
    assert limpo["TotalCharges"].dtype.kind == "f"
    assert limpo.loc[limpo.customerID == "A", "TotalCharges"].iloc[0] == 0.0
    assert bruto["TotalCharges"].iloc[0] == " "


def test_limpeza_mantem_semantica_das_categorias():
    limpo, _ = ch.limpar_dados(base_pequena())
    assert "No internet service" in set(limpo["OnlineSecurity"])


def test_limpeza_remove_churn_invalido():
    df = base_pequena()
    df.loc[1, "Churn"] = None
    limpo, rel = ch.limpar_dados(df)
    assert rel["churn_invalido_removidos"] == 1


def test_outliers_so_reporta():
    df = pd.DataFrame({"tenure": [1, 2, 3, 4, 500], "MonthlyCharges": [1.0] * 5, "TotalCharges": [1.0] * 5})
    rel = ch.detectar_outliers(df)
    assert rel["tenure"]["qtd"] == 1 and len(df) == 5


def test_taxa_churn_e_categoria():
    limpo, _ = ch.limpar_dados(base_pequena())
    assert ch.taxa_churn_geral(limpo) == pytest.approx(50.0)
    tab = ch.churn_por_categoria(limpo, "Contract")
    mensal = tab.loc[tab.Contract == "Month-to-month", "taxa_churn_pct"].iloc[0]
    assert mensal == 50.0


def test_churn_por_periodo_mes_semestre_ano():
    df = pd.DataFrame({
        "data": ["2024-01-10", "2024-02-11", "2024-08-01", "2025-03-05"],
        "Churn": ["Yes", "No", "Yes", "No"],
    })
    m = ch.taxa_churn_por_periodo(df, "data", "M")
    s = ch.taxa_churn_por_periodo(df, "data", "S").set_index("periodo")
    a = ch.taxa_churn_por_periodo(df, "data", "A").set_index("periodo")
    assert len(m) == 4
    assert s.loc["2024-S1", "taxa_churn_pct"] == 50.0
    assert s.loc["2024-S2", "taxa_churn_pct"] == 100.0
    assert a.loc["2024", "clientes"] == 3
    with pytest.raises(ValueError):
        ch.taxa_churn_por_periodo(df, "data", "X")


def test_estimar_data_adesao():
    df = pd.DataFrame({"tenure": [0, 1, 13]})
    d = ch.estimar_data_adesao(df, "2026-06-30")
    assert list(d.dt.strftime("%Y-%m")) == ["2026-06", "2026-05", "2025-05"]


def test_features_derivadas():
    limpo, _ = ch.limpar_dados(base_pequena())
    f = ch.criar_features(limpo, limite_recente=6).set_index("customerID")
    assert np.isnan(f.loc["A", "gasto_medio_observado"])
    assert f.loc["B", "gasto_medio_observado"] == pytest.approx(70.0)
    assert f.loc["B", "qtd_servicos_ativos"] == 5
    assert f.loc["C", "qtd_servicos_ativos"] == 0
    assert f.loc["A", "contrato_mensal"] == 1 and f.loc["B", "contrato_mensal"] == 0
    assert f.loc["D", "cliente_recente"] == 1 and f.loc["C", "cliente_recente"] == 0


def test_limite_recente_vem_dos_dados():
    df = base_sintetica()
    limite = ch.sugerir_limite_cliente_recente(df)
    assert 0 <= limite <= 72


def test_preparacao_remove_id_e_alvo_binario():
    f = ch.criar_features(ch.limpar_dados(base_sintetica())[0])
    X, y = ch.preparar_xy(f)
    assert "customerID" not in X.columns and "Churn" not in X.columns
    assert set(y.unique()) <= {0, 1}


def test_split_estratificado_e_reprodutivel():
    f = ch.criar_features(ch.limpar_dados(base_sintetica())[0])
    X, y = ch.preparar_xy(f)
    _, _, y_tr, y_te = ch.dividir_treino_teste(X, y)
    assert abs(y_tr.mean() - y_te.mean()) < 0.02
    _, _, y_tr2, _ = ch.dividir_treino_teste(X, y)
    assert list(y_tr.index) == list(y_tr2.index)


def test_treino_avaliacao_e_score():
    f = ch.criar_features(ch.limpar_dados(base_sintetica())[0])
    X, y = ch.preparar_xy(f)
    modelos, tab = ch.treinar_e_avaliar(*ch.dividir_treino_teste(X, y)[:2], *ch.dividir_treino_teste(X, y)[2:])
    assert set(tab["modelo"]) == {"Regressao Logistica", "Arvore de Decisao", "Random Forest"}
    assert (tab["roc_auc"] > 0.6).all()
    score = ch.gerar_score_risco(f)
    assert score["prob_churn"].between(0, 1).all() and len(score) == len(f)


def test_pipeline_completo(tmp_path):
    csv = tmp_path / "base.csv"
    base_sintetica(300).to_csv(csv, index=False)
    out = tmp_path / "res"
    r = ch.executar_pipeline(str(csv), str(out), data_referencia="2026-06-30", gerar_graficos=False)
    for arq in ["dados_limpos.csv", "dados_com_features.csv", "metricas_modelos.csv",
                "score_risco_clientes.csv", "churn_mensal.csv", "churn_semestral.csv",
                "churn_anual.csv", "relatorio.json"]:
        assert (out / arq).exists(), arq
    assert 0 < r["taxa_churn_geral_pct"] < 100