import json
from pathlib import Path

with open("dashboard_data.json", "r", encoding="utf-8") as f:
    bundle = json.load(f)

json_str = json.dumps(bundle, ensure_ascii=False)

html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sistema de Monitoramento e Previsão de Churn</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg: #000000;
      --card-bg: rgba(10, 10, 10, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --card-border-hover: rgba(255, 255, 255, 0.18);
      --text-1: #ffffff;
      --text-2: #8e8e93;
      --text-3: #545458;
      --danger: #ff453a;
      --warning: #ffd60a;
      --success: #30d158;
      --accent: #2997ff;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      -webkit-font-smoothing: antialiased;
    }}

    body {{
      background-color: var(--bg);
      color: var(--text-1);
      padding: 28px 36px;
      min-height: 100vh;
    }}

    /* HEADER */
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 28px;
      padding: 18px 24px;
      background: var(--card-bg);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border: 1px solid var(--card-border);
      border-radius: 14px;
    }}

    .header-left h1 {{
      font-size: 1.15rem;
      font-weight: 600;
      letter-spacing: -0.02em;
      color: var(--text-1);
    }}

    .header-left p {{
      font-size: 0.8rem;
      color: var(--text-2);
      margin-top: 3px;
    }}

    .header-right {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}

    .chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      font-size: 0.78rem;
      color: var(--text-2);
    }}

    .chip-dot {{
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--accent);
    }}

    /* KPI METRICS */
    .kpis {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}

    .kpi {{
      background: var(--card-bg);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 20px;
      transition: border-color 0.2s ease;
    }}

    .kpi:hover {{
      border-color: var(--card-border-hover);
    }}

    .kpi-label {{
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--text-2);
      letter-spacing: 0.02em;
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    .kpi-val {{
      font-size: 1.85rem;
      font-weight: 700;
      letter-spacing: -0.03em;
      font-family: 'Inter', sans-serif;
      color: var(--text-1);
      margin-bottom: 4px;
    }}

    .kpi-desc {{
      font-size: 0.74rem;
      color: var(--text-3);
    }}

    /* CHARTS */
    .grid-charts {{
      display: grid;
      grid-template-columns: 1.7fr 1.3fr;
      gap: 20px;
      margin-bottom: 24px;
    }}

    @media (max-width: 1024px) {{
      .grid-charts {{ grid-template-columns: 1fr; }}
    }}

    .panel {{
      background: var(--card-bg);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 22px;
    }}

    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
      padding-bottom: 12px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }}

    .panel-title {{
      font-size: 0.95rem;
      font-weight: 600;
      color: var(--text-1);
    }}

    .panel-subtitle {{
      font-size: 0.74rem;
      color: var(--text-2);
      margin-top: 2px;
    }}

    .chart-wrap {{
      position: relative;
      height: 250px;
      width: 100%;
    }}

    /* CONTROLS */
    .filters {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }}

    .input-search {{
      background: rgba(18, 18, 18, 0.8);
      border: 1px solid var(--card-border);
      color: var(--text-1);
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 0.8rem;
      outline: none;
      min-width: 240px;
      transition: border-color 0.2s;
    }}

    .input-search:focus {{
      border-color: var(--accent);
    }}

    .btn-filter {{
      background: rgba(18, 18, 18, 0.8);
      border: 1px solid var(--card-border);
      color: var(--text-2);
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 0.78rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }}

    .btn-filter:hover, .btn-filter.active {{
      background: #1c1c1e;
      border-color: rgba(255, 255, 255, 0.25);
      color: var(--text-1);
    }}

    /* TABLES */
    .table-responsive {{
      overflow-x: auto;
      max-height: 400px;
      border-radius: 10px;
      border: 1px solid rgba(255, 255, 255, 0.05);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
      text-align: left;
    }}

    th {{
      color: var(--text-2);
      font-weight: 500;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 10px 14px;
      background: #080808;
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 5;
    }}

    td {{
      padding: 11px 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      color: var(--text-1);
    }}

    tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    .cell-id {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.8rem;
      color: #d1d1d6;
    }}

    .cell-score {{
      font-family: 'JetBrains Mono', monospace;
      font-weight: 600;
      font-size: 0.82rem;
    }}
    .cell-score.high {{ color: var(--danger); }}
    .cell-score.medium {{ color: var(--warning); }}

    .badge {{
      display: inline-block;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 500;
      letter-spacing: 0.02em;
    }}

    .badge-high {{
      background: rgba(255, 69, 58, 0.12);
      color: var(--danger);
      border: 1px solid rgba(255, 69, 58, 0.25);
    }}

    .badge-medium {{
      background: rgba(255, 214, 10, 0.12);
      color: var(--warning);
      border: 1px solid rgba(255, 214, 10, 0.25);
    }}

    .badge-selected {{
      background: rgba(41, 151, 255, 0.12);
      color: var(--accent);
      border: 1px solid rgba(41, 151, 255, 0.25);
    }}

    .btn-action {{
      background: #1c1c1e;
      color: var(--text-1);
      border: 1px solid var(--card-border);
      padding: 5px 10px;
      border-radius: 6px;
      font-size: 0.72rem;
      font-weight: 500;
      cursor: pointer;
      transition: 0.15s;
    }}

    .btn-action:hover {{
      background: #2c2c2e;
      border-color: rgba(255, 255, 255, 0.25);
    }}

    .footer {{
      margin-top: 32px;
      padding-top: 18px;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      display: flex;
      justify-content: space-between;
      font-size: 0.75rem;
      color: var(--text-3);
    }}
  </style>
</head>
<body>

  <!-- HEADER -->
  <header class="header">
    <div class="header-left">
      <h1>Monitoramento de Retenção e Risco de Evasão</h1>
      <p>Análise Preditiva e Apoio à Tomada de Decisão &bull; Setor de Telecomunicações</p>
    </div>
    <div class="header-right">
      <div class="chip">
        <span class="chip-dot"></span>
        <span>Base Ativa: 7.043 Registros</span>
      </div>
      <div class="chip">
        <span>Modelo: Regressão Logística (Recall 78,34%)</span>
      </div>
    </div>
  </header>

  <!-- KPI CARDS -->
  <section class="kpis">
    <div class="kpi">
      <div class="kpi-label">Receita Mensal em Risco</div>
      <div class="kpi-val" id="kpi-receita">R$ 0</div>
      <div class="kpi-desc">Faturamento de clientes com probabilidade &ge; 70%</div>
    </div>

    <div class="kpi">
      <div class="kpi-label">Clientes em Alto Risco</div>
      <div class="kpi-val" id="kpi-alto">0</div>
      <div class="kpi-desc">Público prioritário para ações de retenção</div>
    </div>

    <div class="kpi">
      <div class="kpi-label">Médio Risco (40% a 69%)</div>
      <div class="kpi-val" id="kpi-medio">0</div>
      <div class="kpi-desc">Acompanhamento preventivo de relacionamento</div>
    </div>

    <div class="kpi">
      <div class="kpi-label">Baixo Risco (&lt; 40%)</div>
      <div class="kpi-val" id="kpi-baixo">0</div>
      <div class="kpi-desc">Clientes estáveis no ciclo de cobrança</div>
    </div>

    <div class="kpi">
      <div class="kpi-label">Taxa Geral de Evasão</div>
      <div class="kpi-val" id="kpi-taxa">0%</div>
      <div class="kpi-desc">Percentual histórico consolidado</div>
    </div>
  </section>

  <!-- CHARTS -->
  <section class="grid-charts">
    <div class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">Taxa de Churn por Modelo de Contrato</div>
          <div class="panel-subtitle">Percentual de cancelamento em relação à modalidade de adesão</div>
        </div>
      </div>
      <div class="chart-wrap">
        <canvas id="chartContrato"></canvas>
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">Distribuição da Base por Faixa de Risco</div>
          <div class="panel-subtitle">Classificação calculada pelo algoritmo preditivo</div>
        </div>
      </div>
      <div class="chart-wrap">
        <canvas id="chartDistribuicao"></canvas>
      </div>
    </div>
  </section>

  <!-- CRITICAL CLIENTS TABLE -->
  <section class="panel" style="margin-bottom: 24px;">
    <div class="panel-header">
      <div>
        <div class="panel-title">Clientes Críticos para Intervenção</div>
        <div class="panel-subtitle">Ordenados por probabilidade decrescente de cancelamento</div>
      </div>
    </div>

    <div class="filters">
      <input type="text" id="search" class="input-search" placeholder="Filtrar por ID do cliente..." oninput="filtrarTabela()">
      <button class="btn-filter active" id="btn-todos" onclick="setFiltro('Todos', this)">Todos</button>
      <button class="btn-filter" id="btn-fibra" onclick="setFiltro('Fiber optic', this)">Fibra Óptica</button>
      <button class="btn-filter" id="btn-mensal" onclick="setFiltro('Month-to-month', this)">Contrato Mensal</button>
    </div>

    <div class="table-responsive">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Probabilidade</th>
            <th>Classificação</th>
            <th>Vínculo (Tenure)</th>
            <th>Contrato</th>
            <th>Internet</th>
            <th>Mensalidade</th>
            <th>Suporte</th>
            <th>Ação</th>
          </tr>
        </thead>
        <tbody id="tabela-corpo"></tbody>
      </table>
    </div>
  </section>

  <!-- BENCHMARK TABLE -->
  <section class="panel">
    <div class="panel-header">
      <div>
        <div class="panel-title">Avaliação Comparativa de Algoritmos</div>
        <div class="panel-subtitle">Resultados obtidos via validação cruzada estratificada em 5 folds</div>
      </div>
    </div>

    <div class="table-responsive">
      <table>
        <thead>
          <tr>
            <th>Algoritmo</th>
            <th>Acurácia</th>
            <th>Precisão</th>
            <th>Recall</th>
            <th>F1-Score</th>
            <th>AUC-ROC</th>
            <th>Critério de Seleção</th>
          </tr>
        </thead>
        <tbody id="tabela-modelos"></tbody>
      </table>
    </div>
  </section>

  <!-- FOOTER -->
  <footer class="footer">
    <div>UNEX &bull; Mineração de Dados (SIS920) &bull; Projeto Semestral</div>
    <div>Equipe: Kevilyn Cruz, Ian Silva, Igor Veloso, Cauã Meira, Felipe Santos</div>
  </footer>

  <script>
    const DADOS = {json_str};

    document.getElementById('kpi-receita').innerText = 'R$ ' + DADOS.kpis.receita_em_risco_mensal.toLocaleString('pt-BR', {{minimumFractionDigits: 2}});
    document.getElementById('kpi-alto').innerText = DADOS.kpis.clientes_alto_risco.toLocaleString('pt-BR');
    document.getElementById('kpi-medio').innerText = DADOS.kpis.clientes_medio_risco.toLocaleString('pt-BR');
    document.getElementById('kpi-baixo').innerText = DADOS.kpis.clientes_baixo_risco.toLocaleString('pt-BR');
    document.getElementById('kpi-taxa').innerText = DADOS.kpis.taxa_churn_geral + '%';

    // Gráfico Contrato
    new Chart(document.getElementById('chartContrato'), {{
      type: 'bar',
      data: {{
        labels: DADOS.contrato.map(c => c.Contract),
        datasets: [{{
          data: DADOS.contrato.map(c => c.taxa_churn_pct),
          backgroundColor: ['#ff453a', '#ffd60a', '#30d158'],
          borderRadius: 6
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            backgroundColor: '#1c1c1e',
            titleColor: '#fff',
            bodyColor: '#8e8e93',
            borderColor: 'rgba(255,255,255,0.1)',
            borderWidth: 1,
            padding: 8
          }}
        }},
        scales: {{
          y: {{
            beginAtZero: true,
            grid: {{ color: 'rgba(255, 255, 255, 0.05)' }},
            ticks: {{ color: '#8e8e93', font: {{ family: 'Inter', size: 11 }} }}
          }},
          x: {{
            grid: {{ display: false }},
            ticks: {{ color: '#d1d1d6', font: {{ family: 'Inter', size: 12, weight: 500 }} }}
          }}
        }}
      }}
    }});

    // Gráfico Distribuição
    new Chart(document.getElementById('chartDistribuicao'), {{
      type: 'doughnut',
      data: {{
        labels: ['Alto Risco (≥ 70%)', 'Médio Risco (40-69%)', 'Baixo Risco (< 40%)'],
        datasets: [{{
          data: [DADOS.kpis.clientes_alto_risco, DADOS.kpis.clientes_medio_risco, DADOS.kpis.clientes_baixo_risco],
          backgroundColor: ['#ff453a', '#ffd60a', '#30d158'],
          borderWidth: 0
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {{
          legend: {{
            position: 'bottom',
            labels: {{
              color: '#8e8e93',
              font: {{ family: 'Inter', size: 11 }},
              padding: 12,
              usePointStyle: true,
              pointStyle: 'circle'
            }}
          }},
          tooltip: {{
            backgroundColor: '#1c1c1e',
            titleColor: '#fff',
            bodyColor: '#8e8e93',
            borderColor: 'rgba(255,255,255,0.1)',
            borderWidth: 1,
            padding: 8
          }}
        }}
      }}
    }});

    // Tabela Modelos
    const tbodyMod = document.getElementById('tabela-modelos');
    tbodyMod.innerHTML = DADOS.metricas_modelos.map(m => {{
      const isWinner = m.modelo === 'Regressao Logistica';
      return `
        <tr style="${{isWinner ? 'background: rgba(41, 151, 255, 0.06);' : ''}}">
          <td>
            <span style="font-weight: 500;">${{m.modelo}}</span>
            ${{isWinner ? '<span class="badge badge-selected" style="margin-left: 8px;">Adotado</span>' : ''}}
          </td>
          <td>${{(m.acuracia * 100).toFixed(2)}}%</td>
          <td>${{(m.precisao * 100).toFixed(2)}}%</td>
          <td style="color: ${{isWinner ? '#2997ff' : 'inherit'}}; font-weight: 600;">${{(m.recall * 100).toFixed(2)}}%</td>
          <td>${{(m.f1 * 100).toFixed(2)}}%</td>
          <td>${{(m.roc_auc * 100).toFixed(2)}}%</td>
          <td style="color: var(--text-2);">${{isWinner ? 'Maior Recall na Detecção de Churn (78,34%)' : 'Alta Precisão Operacional (55,67%)'}}</td>
        </tr>
      `;
    }}).join('');

    // Tabela Clientes
    let filtroAtual = 'Todos';

    function renderTabela(lista) {{
      const tbody = document.getElementById('tabela-corpo');
      tbody.innerHTML = lista.map(c => `
        <tr>
          <td class="cell-id">${{c.customerID}}</td>
          <td class="cell-score ${{c.faixa_risco === 'Alto' ? 'high' : 'medium'}}">${{(c.prob_churn * 100).toFixed(1)}}%</td>
          <td>
            <span class="badge ${{c.faixa_risco === 'Alto' ? 'badge-high' : 'badge-medium'}}">
              ${{c.faixa_risco}}
            </span>
          </td>
          <td>${{c.tenure}} ${{c.tenure === 1 ? 'mês' : 'meses'}}</td>
          <td>${{c.Contract}}</td>
          <td>${{c.InternetService}}</td>
          <td style="font-weight: 500;">R$ ${{c.MonthlyCharges.toFixed(2)}}</td>
          <td style="color: var(--text-2);">${{c.TechSupport}}</td>
          <td>
            <button class="btn-action" onclick="alert('Ação registrada para o cliente ${{c.customerID}}.\\n\\nDirecionamento: Contato preventivo para proposta de retenção e estabilidade contratual.')">
              Iniciar Retenção
            </button>
          </td>
        </tr>
      `).join('');
    }}

    function filtrarTabela() {{
      const busca = document.getElementById('search').value.toLowerCase();
      let filtrados = DADOS.top_clientes;

      if (filtroAtual === 'Fiber optic') {{
        filtrados = filtrados.filter(c => c.InternetService === 'Fiber optic');
      }} else if (filtroAtual === 'Month-to-month') {{
        filtrados = filtrados.filter(c => c.Contract === 'Month-to-month');
      }}

      if (busca) {{
        filtrados = filtrados.filter(c => c.customerID.toLowerCase().includes(busca));
      }}

      renderTabela(filtrados);
    }}

    function setFiltro(tipo, btn) {{
      filtroAtual = tipo;
      document.querySelectorAll('.btn-filter').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      filtrarTabela();
    }}

    renderTabela(DADOS.top_clientes);
  </script>
</body>
</html>
"""

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("dashboard.html atualizado: Total Black #000000, sóbrio e corporativo!")
