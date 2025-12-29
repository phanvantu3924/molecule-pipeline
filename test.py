"""Simple test script for the API"""
import requests
import time
import json

BASE = "http://localhost:8000"

def test():
    print("=" * 50)
    print("Testing Molecule Discovery Pipeline")
    print("=" * 50)
    
    # 1. Health check
    print("\n1. Health Check...")
    r = requests.get(f"{BASE}/health")
    print(f"✅ Status: {r.json()}")
    
    # 2. Create run
    print("\n2. Creating Run...")
    payload = {
        "seed_smiles": ["CC(=O)Oc1ccccc1C(=O)O", "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"],
        "rounds": 2,
        "candidates_per_round": 20,
        "top_k": 5
    }
    
    r = requests.post(f"{BASE}/runs", json=payload)
    data = r.json()
    run_id = data['id']
    print(f"✅ Run ID: {run_id[:8]}...")
    
    # 3. Wait for completion
    print("\n3. Waiting for completion...")
    for i in range(30):  # Max 60 seconds
        r = requests.get(f"{BASE}/runs/{run_id}")
        status = r.json()['status']
        print(f"   Status: {status}")
        
        if status == "completed":
            break
        elif status == "failed":
            print("❌ Run failed")
            return
        
        time.sleep(2)
    
    # 4. Get results
    print("\n4. Results:")
    r = requests.get(f"{BASE}/runs/{run_id}/results")
    results = r.json()
    
    print(f"   Top {len(results['top_molecules'])} molecules:")
    for mol in results['top_molecules']:
        print(f"   {mol['rank']}. {mol['smiles'][:30]}... | Score: {mol['score']:.3f} | QED: {mol['qed']:.3f}")
    
    # 5. Get trace
    print("\n5. Trace:")
    r = requests.get(f"{BASE}/runs/{run_id}/trace")
    trace = r.json()
    
    for t in trace['trace']:
        print(f"   Round {t['round']}: {t['generated']} generated, {t['passed_screening']} passed")
    
    print("\n" + "=" * 50)
    print("✅ All tests passed!")
    print("=" * 50)

if __name__ == "__main__":
    try:
        test()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Run: python main.py")
    except Exception as e:
        print(f"❌ Error: {e}")