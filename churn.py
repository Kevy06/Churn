from __future__ import annotations

import argparse
import json
import logging
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import cross_val_predict, train_test_split, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("churn")

URL_IBM = (
    "https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/"
    "master/data/Telco-Customer-Churn.csv"
)
CAMINHO_PADRAO = "data/Telco-Customer-Churn.csv"
SEMENTE = 42

COLUNA_ID = "customerID"
COLUNA_ALVO = "Churn"

SERVICOS_YES_NO = [
    "PhoneService", "MultipleLines", "OnlineSecurity", "OnlineBackup",
    "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies",
]


def baixar_base(destino: str = CAMINHO_PADRAO, url: str = URL_IBM) -> Path:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    log.info("Baixando base de %s", url)
    urllib.request.urlretrieve(url, destino)
    log.info("Base salva em %s (acesso em %s)", destino, date.today().isoformat())
    return destino


def carregar_dados(caminho: str = CAMINHO_PADRAO, baixar_se_ausente: bool = True) -> pd.DataFrame:
    caminho = Path(caminho)
    if not caminho.exists():
        if not baixar_se_ausente:
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
        baixar_base(str(caminho))
    df = pd.read_csv(caminho)
    log.info("Base lida: %d linhas x %d colunas", *df.shape)
    return df


def inspecionar_dados(df: pd.DataFrame) -> dict:
    em_branco = {
        c: int(df[c].astype(str).str.strip().eq("").sum())
        for c in df.select_dtypes(exclude="number").columns
    }
    return {
        "linhas": int(df.shape[0]),
        "colunas": int(df.shape[1]),
        "tipos": {c: str(t) for c, t in df.dtypes.items()},
        "nulos": {c: int(n) for c, n in df.isna().sum().items() if n > 0},
        "textos_em_branco": {c: n for c, n in em_branco.items() if n > 0},
        "customerID_duplicados": int(df[COLUNA_ID].duplicated().sum()) if COLUNA_ID in df else None,
    }


def limpar_dados(df_bruto: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rel: dict = {"linhas_inicio": int(len(df_bruto))}
    df = df_bruto.copy()

    for col in df.select_dtypes(exclude="number").columns:
        df[col] = df[col].astype("string").str.strip().replace("", pd.NA).astype(object)
    df = df.where(df.notna(), np.nan)

    if "TotalCharges" in df.columns:
        df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
        vazios = df["TotalCharges"].isna()
        rel["totalcharges_vazios"] = int(vazios.sum())
        if "tenure" in df.columns:
            tenure_zero = vazios & (pd.to_numeric(df["tenure"], errors="coerce") == 0)
            df.loc[tenure_zero, "TotalCharges"] = 0.0
            rel["totalcharges_zerados_tenure0"] = int(tenure_zero.sum())
            inconsistentes = df["TotalCharges"].isna()
            rel["totalcharges_removidos_inconsistentes"] = int(inconsistentes.sum())
            df = df.loc[~inconsistentes]

    if COLUNA_ID in df.columns:
        dup = df[COLUNA_ID].duplicated(keep="first")
        rel["duplicados_removidos"] = int(dup.sum())
        df = df.loc[~dup]

    if COLUNA_ALVO in df.columns:
        df[COLUNA_ALVO] = df[COLUNA_ALVO].astype("string").str.strip().str.capitalize()
        invalido = ~df[COLUNA_ALVO].isin(["Yes", "No"])
        rel["churn_invalido_removidos"] = int(invalido.sum())
        df = df.loc[~invalido]
        df[COLUNA_ALVO] = df[COLUNA_ALVO].astype(object)

    for col in ("tenure", "MonthlyCharges"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    rel["linhas_fim"] = int(len(df))
    rel["outliers_iqr"] = detectar_outliers(df)
    df = df.reset_index(drop=True)
    log.info("Limpeza: %d -> %d linhas", rel["linhas_inicio"], rel["linhas_fim"])
    return df, rel


def detectar_outliers(df: pd.DataFrame, colunas=("tenure", "MonthlyCharges", "TotalCharges")) -> dict:
    saida = {}
    for col in colunas:
        if col not in df.columns:
            continue
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        mask = (df[col] < q1 - 1.5 * iqr) | (df[col] > q3 + 1.5 * iqr)
        saida[col] = {"qtd": int(mask.sum()), "min": float(df[col].min()), "max": float(df[col].max())}
    return saida


def _alvo_binario(df: pd.DataFrame) -> pd.Series:
    return (df[COLUNA_ALVO] == "Yes").astype(int)


def taxa_churn_geral(df: pd.DataFrame) -> float:
    return float(_alvo_binario(df).mean() * 100)


def churn_por_categoria(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    tmp = df.assign(_y=_alvo_binario(df))
    tab = tmp.groupby(coluna, dropna=False)["_y"].agg(clientes="count", churn="sum")
    tab["taxa_churn_pct"] = (tab["churn"] / tab["clientes"] * 100).round(2)
    return tab.reset_index().sort_values("taxa_churn_pct", ascending=False)


def _churn_por_faixa(df: pd.DataFrame, faixas: pd.Series, nome: str) -> pd.DataFrame:
    tmp = pd.DataFrame({nome: faixas, "_y": _alvo_binario(df)})
    tab = tmp.groupby(nome, observed=True)["_y"].agg(clientes="count", churn="sum")
    tab["taxa_churn_pct"] = (tab["churn"] / tab["clientes"] * 100).round(2)
    tab = tab.reset_index()
    tab[nome] = tab[nome].astype(str)
    return tab


def churn_por_faixa_tenure(df: pd.DataFrame, limites=(0, 6, 12, 24, 48, 72)) -> pd.DataFrame:
    faixas = pd.cut(df["tenure"], bins=list(limites), include_lowest=True)
    return _churn_por_faixa(df, faixas, "faixa_tenure")


def churn_por_faixa_cobranca(df: pd.DataFrame, n_faixas: int = 4) -> pd.DataFrame:
    faixas = pd.qcut(df["MonthlyCharges"], q=n_faixas, duplicates="drop")
    return _churn_por_faixa(df, faixas, "faixa_mensalidade")


def estimar_data_adesao(df: pd.DataFrame, data_referencia: str | date) -> pd.Series:
    ref = pd.Timestamp(data_referencia)
    total = ref.year * 12 + (ref.month - 1) - df["tenure"].astype(int)
    return pd.to_datetime(
        {"year": total // 12, "month": total % 12 + 1, "day": 1}
    )


def taxa_churn_por_periodo(df: pd.DataFrame, coluna_data: str, granularidade: str = "M") -> pd.DataFrame:
    g = granularidade.upper()
    if g not in {"M", "S", "A"}:
        raise ValueError("granularidade deve ser 'M' (mês), 'S' (semestre) ou 'A' (ano)")
    datas = pd.to_datetime(df[coluna_data], errors="coerce")
    if g == "M":
        periodo = datas.dt.strftime("%Y-%m")
    elif g == "S":
        periodo = datas.dt.year.astype("Int64").astype(str) + "-S" + ((datas.dt.month - 1) // 6 + 1).astype("Int64").astype(str)
    else:
        periodo = datas.dt.year.astype("Int64").astype(str)
    tmp = pd.DataFrame({"periodo": periodo, "_y": _alvo_binario(df)}).dropna(subset=["periodo"])
    tmp = tmp[~tmp["periodo"].str.contains("NA|<NA>", regex=True)]
    tab = tmp.groupby("periodo")["_y"].agg(clientes="count", churn="sum")
    tab["taxa_churn_pct"] = (tab["churn"] / tab["clientes"] * 100).round(2)
    return tab.reset_index().sort_values("periodo")


def sugerir_limite_cliente_recente(df: pd.DataFrame) -> int:
    arvore = DecisionTreeClassifier(max_depth=1, random_state=SEMENTE)
    arvore.fit(df[["tenure"]], _alvo_binario(df))
    return int(np.floor(arvore.tree_.threshold[0]))


def criar_features(df: pd.DataFrame, limite_recente: int | None = None) -> pd.DataFrame:
    out = df.copy()

    tenure_pos = out["tenure"] > 0
    out["gasto_medio_observado"] = np.where(tenure_pos, out["TotalCharges"] / out["tenure"].where(tenure_pos), np.nan)

    ativos = pd.Series(0, index=out.index)
    for col in SERVICOS_YES_NO:
        if col in out.columns:
            ativos += (out[col] == "Yes").astype(int)
    if "InternetService" in out.columns:
        ativos += out["InternetService"].isin(["DSL", "Fiber optic"]).astype(int)
    out["qtd_servicos_ativos"] = ativos

    out["contrato_mensal"] = (out["Contract"] == "Month-to-month").astype(int)

    if limite_recente is None:
        limite_recente = sugerir_limite_cliente_recente(out)
    out["cliente_recente"] = (out["tenure"] <= limite_recente).astype(int)
    out.attrs["limite_cliente_recente"] = int(limite_recente)
    return out


def preparar_xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    y = _alvo_binario(df)
    X = df.drop(columns=[c for c in (COLUNA_ID, COLUNA_ALVO) if c in df.columns])
    return X, y


def dividir_treino_teste(X: pd.DataFrame, y: pd.Series, tamanho_teste: float = 0.2):
    return train_test_split(X, y, test_size=tamanho_teste, stratify=y, random_state=SEMENTE)


def montar_preprocessador(X: pd.DataFrame) -> ColumnTransformer:
    num = X.select_dtypes(include="number").columns.tolist()
    cat = [c for c in X.columns if c not in num]
    return ColumnTransformer(
        [
            ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("esc", StandardScaler())]), num),
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
        ]
    )


def criar_modelos(X: pd.DataFrame) -> dict[str, Pipeline]:
    return {
        "Regressao Logistica": Pipeline([
            ("pre", montar_preprocessador(X)),
            ("modelo", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEMENTE)),
        ]),
        "Arvore de Decisao": Pipeline([
            ("pre", montar_preprocessador(X)),
            ("modelo", DecisionTreeClassifier(max_depth=5, min_samples_leaf=20,
                                              class_weight="balanced", random_state=SEMENTE)),
        ]),
        "Random Forest": Pipeline([
            ("pre", montar_preprocessador(X)),
            ("modelo", RandomForestClassifier(n_estimators=300, min_samples_leaf=5,
                                              class_weight="balanced", n_jobs=-1, random_state=SEMENTE)),
        ]),
    }


def avaliar_modelo(modelo: Pipeline, X_teste: pd.DataFrame, y_teste: pd.Series) -> dict:
    prob = modelo.predict_proba(X_teste)[:, 1]
    pred = (prob >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_teste, pred).ravel()
    return {
        "acuracia": round(accuracy_score(y_teste, pred), 4),
        "precisao": round(precision_score(y_teste, pred, zero_division=0), 4),
        "recall": round(recall_score(y_teste, pred), 4),
        "f1": round(f1_score(y_teste, pred), 4),
        "roc_auc": round(roc_auc_score(y_teste, prob), 4),
        "vp": int(tp), "fp": int(fp), "fn": int(fn), "vn": int(tn),
    }


def treinar_e_avaliar(X_treino, X_teste, y_treino, y_teste) -> tuple[dict, pd.DataFrame]:
    treinados, linhas = {}, []
    for nome, pipe in criar_modelos(X_treino).items():
        log.info("Treinando: %s", nome)
        pipe.fit(X_treino, y_treino)
        treinados[nome] = pipe
        linhas.append({"modelo": nome, **avaliar_modelo(pipe, X_teste, y_teste)})
    tabela = pd.DataFrame(linhas).sort_values("roc_auc", ascending=False).reset_index(drop=True)
    return treinados, tabela


def importancia_variaveis(modelo: Pipeline, top: int = 15) -> pd.DataFrame:
    nomes = modelo.named_steps["pre"].get_feature_names_out()
    est = modelo.named_steps["modelo"]
    if hasattr(est, "feature_importances_"):
        valores = est.feature_importances_
    else:
        valores = np.abs(est.coef_[0])
    return (pd.DataFrame({"variavel": nomes, "importancia": valores})
            .sort_values("importancia", ascending=False).head(top).reset_index(drop=True))


def gerar_score_risco(df_features: pd.DataFrame, nome_modelo: str = "Random Forest") -> pd.DataFrame:
    X, y = preparar_xy(df_features)
    modelo = criar_modelos(X)[nome_modelo]
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEMENTE)
    prob = cross_val_predict(modelo, X, y, cv=cv, method="predict_proba")[:, 1]
    saida = pd.DataFrame({
        COLUNA_ID: df_features[COLUNA_ID].values,
        "prob_churn": prob.round(4),
        "faixa_risco": pd.cut(prob, bins=[-0.01, 0.33, 0.66, 1.0], labels=["Baixo", "Medio", "Alto"]),
        "churn_real": y.values,
    })
    return saida.sort_values("prob_churn", ascending=False).reset_index(drop=True)


def _grafico_churn_barras(tabela: pd.DataFrame, coluna: str, titulo: str, caminho: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(tabela[coluna].astype(str), tabela["taxa_churn_pct"], color="#c0392b")
    ax.set_title(titulo)
    ax.set_ylabel("Taxa de churn (%)")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(caminho, dpi=130)
    plt.close(fig)


def _grafico_roc(modelos: dict, X_teste, y_teste, caminho: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 5))
    for nome, pipe in modelos.items():
        fpr, tpr, _ = roc_curve(y_teste, pipe.predict_proba(X_teste)[:, 1])
        ax.plot(fpr, tpr, label=nome)
    ax.plot([0, 1], [0, 1], "--", color="gray")
    ax.set_xlabel("Falsos positivos")
    ax.set_ylabel("Verdadeiros positivos")
    ax.set_title("Curva ROC - comparação de modelos")
    ax.legend()
    fig.tight_layout()
    fig.savefig(caminho, dpi=130)
    plt.close(fig)


def executar_pipeline(
    caminho_csv: str = CAMINHO_PADRAO,
    pasta_saida: str = "resultados",
    coluna_data: str | None = None,
    data_referencia: str | None = None,
    gerar_graficos: bool = True,
) -> dict:
    saida = Path(pasta_saida)
    saida.mkdir(parents=True, exist_ok=True)

    bruto = carregar_dados(caminho_csv)
    diagnostico = inspecionar_dados(bruto)
    limpo, rel_limpeza = limpar_dados(bruto)
    limpo.to_csv(saida / "dados_limpos.csv", index=False)

    eda = {
        nome: churn_por_categoria(limpo, col)
        for nome, col in (("contrato", "Contract"), ("internet", "InternetService"), ("pagamento", "PaymentMethod"))
        if col in limpo.columns
    }
    eda["faixa_tenure"] = churn_por_faixa_tenure(limpo)
    eda["faixa_mensalidade"] = churn_por_faixa_cobranca(limpo)
    for nome, tab in eda.items():
        tab.to_csv(saida / f"churn_por_{nome}.csv", index=False)

    if coluna_data and coluna_data in limpo.columns:
        base_tempo, col_tempo, origem = limpo, coluna_data, "coluna de data real"
    else:
        ref = data_referencia or date.today().isoformat()
        base_tempo = limpo.assign(data_adesao_estimada=estimar_data_adesao(limpo, ref))
        col_tempo, origem = "data_adesao_estimada", f"adesão ESTIMADA (ref. {ref} - tenure)"
    periodos = {}
    for sigla, nome in (("M", "mensal"), ("S", "semestral"), ("A", "anual")):
        periodos[nome] = taxa_churn_por_periodo(base_tempo, col_tempo, sigla)
        periodos[nome].to_csv(saida / f"churn_{nome}.csv", index=False)

    limite = sugerir_limite_cliente_recente(limpo)
    com_features = criar_features(limpo, limite_recente=limite)
    com_features.to_csv(saida / "dados_com_features.csv", index=False)

    X, y = preparar_xy(com_features)
    X_tr, X_te, y_tr, y_te = dividir_treino_teste(X, y)
    modelos, metricas = treinar_e_avaliar(X_tr, X_te, y_tr, y_te)
    metricas.to_csv(saida / "metricas_modelos.csv", index=False)
    melhor = metricas.loc[0, "modelo"]
    importancias = importancia_variaveis(modelos["Random Forest"])
    importancias.to_csv(saida / "importancia_variaveis_rf.csv", index=False)
    score = gerar_score_risco(com_features, nome_modelo="Random Forest")
    score.to_csv(saida / "score_risco_clientes.csv", index=False)

    if gerar_graficos:
        _grafico_churn_barras(eda["contrato"], "Contract", "Churn por tipo de contrato", saida / "grafico_contrato.png")
        _grafico_churn_barras(eda["faixa_tenure"], "faixa_tenure", "Churn por faixa de tenure", saida / "grafico_tenure.png")
        _grafico_roc(modelos, X_te, y_te, saida / "grafico_roc.png")

    resumo = {
        "diagnostico_inicial": diagnostico,
        "limpeza": rel_limpeza,
        "taxa_churn_geral_pct": round(taxa_churn_geral(limpo), 2),
        "limite_cliente_recente_meses": limite,
        "origem_dos_periodos": origem,
        "melhor_modelo_por_auc": melhor,
        "metricas": metricas.to_dict(orient="records"),
        "clientes_risco_alto": int((score["faixa_risco"] == "Alto").sum()),
    }
    with open(saida / "relatorio.json", "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2, default=str)
    _imprimir_resumo(resumo, eda, periodos, metricas, importancias)
    log.info("Arquivos gravados em: %s", saida.resolve())
    return resumo


def _imprimir_resumo(resumo, eda, periodos, metricas, importancias) -> None:
    linha = "=" * 70
    print(f"\n{linha}\nRELATÓRIO DE CHURN\n{linha}")
    print(f"Taxa de churn geral: {resumo['taxa_churn_geral_pct']}%")
    print(f"Limpeza: {resumo['limpeza']['linhas_inicio']} -> {resumo['limpeza']['linhas_fim']} linhas")
    print(f"Limite de 'cliente recente' (via EDA): tenure <= {resumo['limite_cliente_recente_meses']} meses")
    print("\nChurn por contrato:\n", eda["contrato"].to_string(index=False))
    print("\nChurn por faixa de tenure:\n", eda["faixa_tenure"].to_string(index=False))
    print(f"\nChurn anual ({resumo['origem_dos_periodos']}):\n", periodos["anual"].to_string(index=False))
    print("\nComparação de modelos (teste):\n", metricas[["modelo", "acuracia", "precisao", "recall", "f1", "roc_auc"]].to_string(index=False))
    print("\nTop variáveis (Random Forest):\n", importancias.head(8).to_string(index=False))
    print(f"\nClientes em risco ALTO: {resumo['clientes_risco_alto']}\n{linha}\n")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Pipeline de previsão de churn (Telco).")
    p.add_argument("--csv", default=CAMINHO_PADRAO, help="caminho do CSV (baixa da IBM se não existir)")
    p.add_argument("--saida", default="resultados", help="pasta de saída")
    p.add_argument("--coluna-data", default=None, help="coluna com data real (para churn por mês/semestre/ano)")
    p.add_argument("--data-referencia", default=None, help="AAAA-MM-DD usada para estimar a adesão (padrão: hoje)")
    p.add_argument("--sem-graficos", action="store_true", help="não gera PNGs")
    a = p.parse_args(argv)
    executar_pipeline(a.csv, a.saida, a.coluna_data, a.data_referencia, not a.sem_graficos)


if __name__ == "__main__":
    main()