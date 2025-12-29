"""
Molecule Discovery Pipeline - Simple Version
All-in-one implementation for take-home assignment
"""

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import uuid
import random
from rdkit import Chem
from rdkit.Chem import Descriptors, QED
import sqlite3
import json

# ============= FastAPI App =============
app = FastAPI(title="Molecule Pipeline")

# ============= Database Setup =============
def init_db():
    conn = sqlite3.connect('molecules.db')
    c = conn.cursor()
    
    # Runs table
    c.execute('''CREATE TABLE IF NOT EXISTS runs
                 (id TEXT PRIMARY KEY, 
                  config TEXT,
                  status TEXT,
                  created_at TEXT,
                  results TEXT)''')
    
    # Molecules table
    c.execute('''CREATE TABLE IF NOT EXISTS molecules
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  run_id TEXT,
                  smiles TEXT,
                  round_num INTEGER,
                  mw REAL, logp REAL, hbd INTEGER, hba INTEGER,
                  tpsa REAL, rotb INTEGER, qed REAL,
                  violations INTEGER, score REAL, rank INTEGER)''')
    
    conn.commit()
    conn.close()

init_db()

# ============= Pydantic Models =============
class RunConfig(BaseModel):
    seed_smiles: List[str]
    rounds: int = 3
    candidates_per_round: int = 30
    top_k: int = 10
    max_mw: float = 500
    max_logp: float = 5
    max_hbd: int = 5
    max_hba: int = 10
    max_tpsa: float = 140
    max_violations: int = 1

class RunResponse(BaseModel):
    id: str
    status: str
    created_at: str

# ============= Chemistry Functions =============
def validate_smiles(smiles: str) -> bool:
    """Check if SMILES is valid"""
    try:
        mol = Chem.MolFromSmiles(smiles)
        return mol is not None
    except:
        return False

def calculate_properties(smiles: str) -> Optional[Dict]:
    """Calculate molecular properties using RDKit"""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return None
        
        return {
            'mw': Descriptors.MolWt(mol),
            'logp': Descriptors.MolLogP(mol),
            'hbd': Descriptors.NumHDonors(mol),
            'hba': Descriptors.NumHAcceptors(mol),
            'tpsa': Descriptors.TPSA(mol),
            'rotb': Descriptors.NumRotatableBonds(mol),
            'qed': QED.qed(mol)
        }
    except:
        return None

# ============= Generation Functions =============
def mutate_smiles(smiles: str) -> str:
    """Simple mutation strategies"""
    mutations = [
        lambda s: s.replace('F', 'Cl'),
        lambda s: s.replace('Cl', 'F'),
        lambda s: s.replace('Br', 'I'),
        lambda s: s + 'C' if len(s) < 100 else s,
        lambda s: s[:-1] if len(s) > 10 else s,
    ]
    
    mut = random.choice(mutations)
    new_smiles = mut(smiles)
    
    # Validate
    if validate_smiles(new_smiles):
        return new_smiles
    return smiles

def generate_candidates(seeds: List[str], count: int, existing: set) -> List[str]:
    """Generate new molecule candidates"""
    candidates = []
    attempts = 0
    max_attempts = count * 5
    
    while len(candidates) < count and attempts < max_attempts:
        attempts += 1
        seed = random.choice(seeds)
        new_smiles = mutate_smiles(seed)
        
        if new_smiles not in existing and new_smiles not in candidates:
            candidates.append(new_smiles)
            existing.add(new_smiles)
    
    return candidates

# ============= Screening Functions =============
def screen_molecule(props: Dict, config: RunConfig) -> tuple:
    """Apply Lipinski-like filters"""
    violations = 0
    
    if props['mw'] > config.max_mw:
        violations += 1
    if props['logp'] > config.max_logp:
        violations += 1
    if props['hbd'] > config.max_hbd:
        violations += 1
    if props['hba'] > config.max_hba:
        violations += 1
    if props['tpsa'] > config.max_tpsa:
        violations += 1
    
    # Calculate score
    score = props['qed'] - (0.1 * violations)
    passed = violations <= config.max_violations
    
    return violations, score, passed

# ============= Pipeline Function =============
def run_pipeline(run_id: str, config: RunConfig):
    """Main pipeline execution"""
    conn = sqlite3.connect('molecules.db')
    c = conn.cursor()
    
    try:
        # Update status
        c.execute("UPDATE runs SET status=? WHERE id=?", ("running", run_id))
        conn.commit()
        
        all_smiles = set(config.seed_smiles)
        seeds = config.seed_smiles.copy()
        
        # Run multiple rounds
        for round_num in range(1, config.rounds + 1):
            print(f"Round {round_num}/{config.rounds}")
            
            # Generate candidates
            candidates = generate_candidates(seeds, config.candidates_per_round, all_smiles)
            
            # Process each candidate
            round_molecules = []
            for smiles in candidates:
                props = calculate_properties(smiles)
                if not props:
                    continue
                
                violations, score, passed = screen_molecule(props, config)
                
                if passed:
                    round_molecules.append({
                        'smiles': smiles,
                        'score': score,
                        **props,
                        'violations': violations
                    })
                
                # Save to database
                c.execute("""INSERT INTO molecules 
                           (run_id, smiles, round_num, mw, logp, hbd, hba, tpsa, rotb, qed, violations, score)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                         (run_id, smiles, round_num, props['mw'], props['logp'], 
                          props['hbd'], props['hba'], props['tpsa'], props['rotb'], 
                          props['qed'], violations, score if passed else None))
            
            conn.commit()
            
            # Use top molecules as seeds for next round
            if round_molecules:
                round_molecules.sort(key=lambda x: x['score'], reverse=True)
                seeds = [m['smiles'] for m in round_molecules[:5]]
        
        # Rank top molecules
        c.execute("""SELECT * FROM molecules 
                    WHERE run_id=? AND score IS NOT NULL 
                    ORDER BY score DESC LIMIT ?""", 
                 (run_id, config.top_k))
        
        top_mols = c.fetchall()
        
        # Update ranks
        for rank, mol in enumerate(top_mols, 1):
            c.execute("UPDATE molecules SET rank=? WHERE id=?", (rank, mol[0]))
        
        # Save results summary
        results = {
            'top_k': config.top_k,
            'completed_rounds': config.rounds,
            'total_molecules': len(all_smiles)
        }
        
        c.execute("UPDATE runs SET status=?, results=? WHERE id=?", 
                 ("completed", json.dumps(results), run_id))
        conn.commit()
        
        print(f"✅ Run {run_id[:8]} completed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        c.execute("UPDATE runs SET status=? WHERE id=?", ("failed", run_id))
        conn.commit()
    
    finally:
        conn.close()

# ============= API Endpoints =============

@app.get("/")
def root():
    return {"message": "Molecule Discovery Pipeline", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/runs", response_model=RunResponse)
def create_run(config: RunConfig, background_tasks: BackgroundTasks):
    """Create and start a new run"""
    run_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    
    # Save to database
    conn = sqlite3.connect('molecules.db')
    c = conn.cursor()
    c.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?)",
             (run_id, json.dumps(config.dict()), "queued", created_at, None))
    conn.commit()
    conn.close()
    
    # Start pipeline in background
    background_tasks.add_task(run_pipeline, run_id, config)
    
    return RunResponse(id=run_id, status="queued", created_at=created_at)

@app.get("/runs/{run_id}")
def get_run_status(run_id: str):
    """Get run status"""
    conn = sqlite3.connect('molecules.db')
    c = conn.cursor()
    c.execute("SELECT * FROM runs WHERE id=?", (run_id,))
    run = c.fetchone()
    conn.close()
    
    if not run:
        return {"error": "Run not found"}
    
    return {
        "id": run[0],
        "status": run[2],
        "created_at": run[3],
        "results": json.loads(run[4]) if run[4] else None
    }

@app.get("/runs/{run_id}/results")
def get_results(run_id: str):
    """Get top ranked molecules"""
    conn = sqlite3.connect('molecules.db')
    c = conn.cursor()
    
    # Get run info
    c.execute("SELECT status FROM runs WHERE id=?", (run_id,))
    run = c.fetchone()
    if not run:
        return {"error": "Run not found"}
    
    # Get top molecules
    c.execute("""SELECT smiles, mw, logp, hbd, hba, tpsa, rotb, qed, violations, score, rank
                FROM molecules WHERE run_id=? AND rank IS NOT NULL 
                ORDER BY rank""", (run_id,))
    
    molecules = []
    for row in c.fetchall():
        molecules.append({
            "smiles": row[0],
            "mw": row[1],
            "logp": row[2],
            "hbd": row[3],
            "hba": row[4],
            "tpsa": row[5],
            "rotb": row[6],
            "qed": row[7],
            "violations": row[8],
            "score": row[9],
            "rank": row[10]
        })
    
    conn.close()
    
    return {
        "run_id": run_id,
        "status": run[0],
        "top_molecules": molecules
    }

@app.get("/runs/{run_id}/trace")
def get_trace(run_id: str):
    """Get execution trace (simplified)"""
    conn = sqlite3.connect('molecules.db')
    c = conn.cursor()
    
    # Get molecules grouped by round
    c.execute("""SELECT round_num, COUNT(*), 
                SUM(CASE WHEN score IS NOT NULL THEN 1 ELSE 0 END)
                FROM molecules WHERE run_id=? 
                GROUP BY round_num ORDER BY round_num""", (run_id,))
    
    trace = []
    for row in c.fetchall():
        trace.append({
            "round": row[0],
            "generated": row[1],
            "passed_screening": row[2]
        })
    
    conn.close()
    
    return {"run_id": run_id, "trace": trace}

# ============= Run Server =============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)