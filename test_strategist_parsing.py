
import json
import logging

# Mock logger
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("Test")

# Mock response content
mock_llm_response_content = """
```json
[
  {
    "drug": "Metformin",
    "target_disease": "Leukemia",
    "shared_pathways": ["AMPK signaling", "mTOR inhibition"],
    "mechanism_of_action": "Activates AMPK...",
    "confidence_score": 90,
    "reasoning_trace": "Trace 1"
  },
  {
    "drug": "Atorvastatin",
    "target_disease": "Leukemia",
    "shared_pathways": ["Cholesterol biosynthesis", "Apoptosis"],
    "mechanism_of_action": "Inhibits HMG-CoA reductase...",
    "confidence_score": 85,
    "reasoning_trace": "Trace 2"
  }
]
```
"""

def test_parsing():
    content = mock_llm_response_content.strip()
    
    # Strip markdown code blocks if present
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    
    try:
        result = json.loads(content.strip())
        
        # Validate result is a list
        if isinstance(result, dict):
            result = [result]
            
        print(f"SUCCESS: Parsed {len(result)} items.")
        for item in result:
            print(f"- Found drug: {item.get('drug')}")
            
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_parsing()
