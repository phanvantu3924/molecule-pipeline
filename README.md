# Molecule Discovery Pipeline

AI-driven molecule generation and screening pipeline.

## Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
python main.py
```

Server runs at: http://localhost:8000  
API docs: http://localhost:8000/docs

## Usage

### Create a run
```bash
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{
    "seed_smiles": ["CC(=O)Oc1ccccc1C(=O)O"],
    "rounds": 3,
    "candidates_per_round": 30,
    "top_k": 10
  }'
```

### Check status
```bash
curl http://localhost:8000/runs/{run_id}
```

### Get results
```bash
curl http://localhost:8000/runs/{run_id}/results
```

## Features

✅ **3 Agents**: Planner (implicit), Generator, Ranker  
✅ **RDKit**: Molecular property calculation  
✅ **Screening**: Lipinski-like rules  
✅ **Scoring**: QED - 0.1 × violations  
✅ **Async**: Non-blocking execution  
✅ **Multi-round**: Iterative improvement  

## Architecture
```
User → FastAPI → Pipeline → [Generation → Screening → Ranking] × Rounds → Results
                                  ↓
                               RDKit (MW, LogP, HBD, HBA, TPSA, RotB, QED)
                                  ↓
                               SQLite
```

## Endpoints

- `POST /runs` - Create new run
- `GET /runs/{id}` - Get status
- `GET /runs/{id}/results` - Get top molecules
- `GET /runs/{id}/trace` - Get execution trace
- `GET /health` - Health check

## Example Seeds
```python
"CC(=O)Oc1ccccc1C(=O)O"           # Aspirin
"CN1C=NC2=C1C(=O)N(C(=O)N2C)C"    # Caffeine
```

## Tech Stack

- FastAPI (API framework)
- RDKit (chemistry)
- SQLite (database)
- Pydantic (validation)

## Implementation Details

**Generation**: Rule-based mutations (swap halogens, add/remove methyl)  
**Screening**: Configurable Lipinski filters with max violations  
**Scoring**: `Score = QED - (0.1 × violations)`  
**Multi-round**: Top molecules become seeds for next round  

## Time: ~2 days

Built as take-home assignment for Backend Engineer position.
```

---

## 📄 FILE 4: requirements.txt
```
fastapi==0.109.0
uvicorn==0.27.0
pydantic==2.5.3
rdkit==2023.9.4