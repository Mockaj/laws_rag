import os
import requests

# Define the Qdrant node
QDRANT_NODE = "http://localhost:6333"  # Replace with your actual node URL if different

# Define the snapshot path
snapshot_path = "/Users/mockaj/Downloads/backup/qdrant/snapshot.snapshot"
snapshot_name = os.path.basename(snapshot_path)
new_collection_name = "legal_paragraphs_update"

# Step 1: Upload the snapshot to the node
with open(snapshot_path, "rb") as snapshot_file:
    upload_response = requests.post(
        f"{QDRANT_NODE}/collections/test_collection_import/snapshots/upload?priority=snapshot",
        files={"snapshot": (snapshot_name, snapshot_file)},
    )
    if upload_response.status_code == 200:
        print(f"Successfully uploaded snapshot to {QDRANT_NODE}")
    else:
        print(f"Failed to upload snapshot to {QDRANT_NODE}: {upload_response.text}")
        exit()

# Step 2: Create the new collection
create_collection_response = requests.put(
    f"{QDRANT_NODE}/collections/{new_collection_name}",
    json={
        "vectors": {
            "size": 1024,  # Replace with the actual vector size for your data
            "distance": "Cosine"  # or "Euclidean", "Dot"
        }
    }
)
if create_collection_response.status_code == 200:
    print(f"Successfully created collection {new_collection_name} on {QDRANT_NODE}")
else:
    print(f"Failed to create collection on {QDRANT_NODE}: {create_collection_response.text}")
    exit()

# Step 3: Restore the collection from the snapshot
restore_response = requests.post(
    f"{QDRANT_NODE}/collections/{new_collection_name}/snapshots/restore",
    json={
        "location": snapshot_name,
        "priority": "snapshot"
    }
)
if restore_response.status_code == 200:
    print(f"Successfully restored collection {new_collection_name} from snapshot")
else:
    print(f"Failed to restore collection from snapshot: {restore_response.text}")
