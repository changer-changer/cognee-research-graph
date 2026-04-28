"""Test M1.2 with minimal text to verify cognify pipeline works."""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asyncio
sys.path.insert(0, '/home/cuizhixing/cognee-env/lib/python3.10/site-packages')

import cognee

async def test_minimal_cognify():
    """Test that cognify works on a tiny text file."""
    dataset = "test_minimal_001"
    text_path = "/tmp/test_minimal.txt"
    with open(text_path, "w") as f:
        f.write("This is a test paper about machine learning.\n")
        f.write("It discusses neural networks and deep learning.\n")

    print("Adding data...")
    await cognee.add(text_path, dataset_name=dataset)
    print("Cognifying...")
    await cognee.cognify(datasets=[dataset])
    print("Searching...")
    from cognee.api.v1.search import SearchType, search
    results = await search(query_type=SearchType.CHUNKS, query_text="machine learning")
    print(f"Search results: {len(results)} chunks found")
    for r in results[:3]:
        print(f"  - {str(r)[:100]}")

    # Cleanup
    await cognee.prune.prune_data()
    print("Cleanup done.")
    return len(results) > 0

if __name__ == "__main__":
    ok = asyncio.run(test_minimal_cognify())
    print(f"\nMinimal cognify test: {'PASS' if ok else 'FAIL'}")
