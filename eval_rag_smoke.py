import os
import sys
import json
import httpx

def score_grounding(response: dict, candidate_ids: set) -> bool:
    """Evaluate if the response is grounded in the candidate set.

    Lab grounding methodology (subset of Integration):
      1. len(citations) >= 1
      2. every cited chunk_id is present in candidate_ids

    Decline-exclusion is an Integration-tier concern; at the Lab tier,
    a decline on seeded fixtures is itself a defect.
    """
    citations = response.get("citations", [])
    if len(citations) < 1:
        return False
        
    for citation in citations:
        if citation.get("chunk_id") not in candidate_ids:
            return False
            
    return True

def evaluate_question(question: dict, api_url: str = None) -> bool:
    """POST a single question to the live stack and score its grounding behavior."""
    if api_url is None:
        api_url = os.environ.get("API_URL", "http://localhost:8000")

    payload = {
        "question": question["question"],
        "k": question.get("k", 4)
    }
    
    try:
        response = httpx.post(f"{api_url}/rag/answer", json=payload, timeout=60.0)
        if response.status_code != 200:
            return False
            
        res_body = response.json()
        candidate_ids = {chunk["chunk_id"] for chunk in res_body.get("retrieved", [])}
        
        return score_grounding(res_body, candidate_ids)
    except Exception:
        return False

def main() -> int:
    """Load the smoke-test questions, evaluate each against the API, and exit."""
    api_url = os.environ.get("API_URL", "http://localhost:8000")
    
    fixture_path = os.path.join(os.path.dirname(__file__), "data", "rag_smoke.json")
    if not os.path.exists(fixture_path):
        print(f"Error: Fixture file not found at {fixture_path}")
        return 1
        
    with open(fixture_path, "r") as fh:
        questions = json.load(fh)
        
    all_passed = True
    for q in questions:
        passed = evaluate_question(q, api_url)
        status_str = "PASS" if passed else "FAIL"
        print(f"{status_str}: {q['question']}")
        if not passed:
            all_passed = False
            
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())