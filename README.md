# Sentiment Analysis — Deploy & Monitoring

Sistema completo per il deploy e monitoraggio di un modello di **Sentiment Analysis** per recensioni e-commerce.

## Stack tecnologico

| Componente | Tecnologia |
|---|---|
| API REST | FastAPI + Uvicorn |
| Modello ML | scikit-learn (pickle) |
| Containerization | Docker + Docker Compose |
| CI/CD | Jenkins |
| Metriche | Prometheus |
| Dashboard | Grafana |

---

## Struttura del progetto

```
sentiment-analysis-project/
├── app/
│   ├── main.py            # FastAPI application
│   ├── requirements.txt   # Python dependencies
│   └── Dockerfile         # Container image
├── tests/
│   └── test_api.py        # Unit + integration tests
├── jenkins/
│   └── Jenkinsfile        # CI/CD pipeline
├── prometheus/
│   └── prometheus.yml     # Scrape configuration
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/   # Prometheus datasource
│   │   └── dashboards/    # Dashboard loader
│   └── dashboards/
│       └── sentiment-dashboard.json
├── docker-compose.yml
└── README.md
```

---

## Avvio rapido (Docker Compose)

### Pre-requisiti
- [Docker Desktop per Windows](https://www.docker.com/products/docker-desktop/) ≥ 4.x
- Docker Compose v2 (incluso in Docker Desktop)

### 1. Clona il repository
```bash
git clone https://github.com/<tuo-username>/sentiment-analysis-project.git
cd sentiment-analysis-project
```

### 2. Avvia l'intero stack
```bash
docker-compose up --build -d
```

Il primo avvio scarica automaticamente il modello dal repository Profession-AI.

### 3. Verifica i servizi

| Servizio | URL |
|---|---|
| API REST | http://localhost:8000 |
| Docs API (Swagger) | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

Credenziali Grafana → `admin` / `admin123`

---

## API Endpoints

### `POST /predict`
Analizza il sentimento di una recensione.

**Request:**
```json
{
  "review": "This product is amazing! I love it."
}
```

**Response:**
```json
{
  "sentiment": "positive",
  "confidence": 0.95
}
```

**cURL esempio:**
```bash
curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d "{\"review\": \"Great product, highly recommended!\"}"
```

### `GET /metrics`
Espone le metriche in formato Prometheus.

```bash
curl http://localhost:8000/metrics
```

### `GET /health`
Health check del servizio.

---

## Esecuzione dei test

### In locale (Windows)
```bash
cd sentiment-analysis-project
pip install -r app\requirements.txt
python -m pytest tests\ -v
```

### Con Docker
```bash
docker run --rm -v "%cd%":/app -w /app python:3.11-slim ^
    sh -c "pip install -q -r app/requirements.txt && pytest tests/ -v"
```

---

## CI/CD con Jenkins

### Setup Jenkins (Windows)

1. **Installa Jenkins** da https://www.jenkins.io/download/
2. **Plugin richiesti** (Manage Jenkins → Plugins):
   - Pipeline
   - Git
   - Docker Pipeline
   - JUnit

3. **Crea una nuova Pipeline:**
   - New Item → Pipeline
   - Definition: "Pipeline script from SCM"
   - SCM: Git → inserisci URL repository
   - Script Path: `jenkins/Jenkinsfile`

4. **Configura le credenziali Docker** (solo se usi un registry):
   - Manage Jenkins → Credentials → System → Global
   - Kind: Username with password
   - ID: `docker-registry-credentials`

### Flusso della pipeline

```
Checkout → Install Deps → Tests → Build Image → Push → Deploy → Smoke Test
```

- La pipeline si attiva ad ogni **commit su qualsiasi branch**
- Il **push al registry** avviene solo sui branch `main`/`master`
- In caso di errore, la pipeline si interrompe e notifica (configurare email in Jenkinsfile)

---

## Monitoraggio

### Metriche raccolte

| Metrica | Tipo | Descrizione |
|---|---|---|
| `sentiment_requests_total` | Counter | Totale richieste per status |
| `sentiment_request_latency_seconds` | Histogram | Latenza delle richieste |
| `sentiment_prediction_errors_total` | Counter | Errori di predizione |
| `sentiment_cpu_usage_percent` | Gauge | CPU del processo |
| `sentiment_memory_usage_bytes` | Gauge | RAM del processo |

### Dashboard Grafana

La dashboard viene caricata automaticamente al primo avvio e include:
- **Stat panels**: totale richieste, successi, errori, CPU
- **Time series**: request rate, latenza P50/P95/P99, memoria, CPU nel tempo

---

## Sviluppo locale (senza Docker)

```bash
# Installa dipendenze
pip install -r app\requirements.txt

# Avvia l'API
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## Troubleshooting

| Problema | Soluzione |
|---|---|
| Il modello non si scarica | Verifica la connessione internet; il download avviene al primo avvio |
| Porta 8000 occupata | Modifica il port mapping in `docker-compose.yml` |
| Grafana non carica la dashboard | Attendi 30s poi ricarica; controlla i log con `docker-compose logs grafana` |
| Jenkins non trova Docker | Aggiungi il path di Docker alle variabili d'ambiente di sistema |
