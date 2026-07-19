# Chroma + FastAPI

* Start building with Chroma in your FastAPI project

## Install dependencies:

```Bash
uv pip install chromadb python-dotenv
```

---

## Store your Chroma Cloud credentials

* Create a .env file if you don‘t have one, and add these environment variables to it. For example:
CHROMA_API_KEY=YOUR_API_KEY
CHROMA_TENANT=YOUR_TENANT_ID
CHROMA_DATABASE=YOUR_DATABASE_NAME

---

## Initialize your Chroma client and collection

* **In `chroma_connection.py`, define `get_chroma_client` and `get_chroma_collection` to plug into FastAPI‘s `Depends` system:**

```Python
import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from fastapi import Depends
from dotenv import load_dotenv
import os

load_dotenv()

_client: ClientAPI | None = None
_collection: Collection | None = None

def get_chroma_client() -> ClientAPI:
	global _client
	if _client is None:
		_client = chromadb.CloudClient(
            api_key=os.getenv("CHROMA_API_KEY"),
            tenant=os.getenv("CHROMA_TENANT"),
            database=os.getenv("CHROMA_DATABASE")
        )
	return _client

def get_chroma_collection(client: ClientAPI = Depends(get_chroma_client)) -> Collection:
	global _collection
	if _collection is None:
		_collection = client.get_or_create_collection(
		    name="my_collection",
		)
	return _collection
```

* **Now, you can access your chroma collection using `fastapi.Depends`:**
```
...
from fastapi import Depends
from chroma_connection import get_chroma_collection
...
@app.post("/api_route/")
async def use_chroma(collection=Depends(get_chroma_collection)):
...
```
---

### Example: batch upload documents

* In order to test the connection to Chroma, here’s an example where we create an API endpoint `/api/documents` for uploading documents in batches.
* In your app entry point (ex `main.py`), add a route to your FastAPI app:

```Python
from fastapi import FastAPI, HTTPException, Depends
from chroma_connection import get_chroma_collection
from pydantic import BaseModel
from typing import Optional

class RequestBody(BaseModel):
    ids: list[str]
    documents: list[str]
    metadatas: list[dict]

app = FastAPI(title="ChromaDB FastAPI Integration")

@app.post("/api/documents/")
async def add_documents(request: RequestBody, col=Depends(get_chroma_collection)):
    try:
        col.add(
            ids=request.ids,
            documents=request.documents,
            metadatas=request.metadatas
        )
        return {"message": "Documents added successfully", "ids": request.ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Test your API

Run your app.

```Bun
bun run dev
```

If you run your app, you can now add documents to your Chroma collection using your new endpoint! You may need to modify this command if your app is running on a different port.
```
curl -X POST "http://localhost:8000/api/documents/" \
     -H "Content-Type: application/json" \
     -d '{
       "ids": ["1", "2"],
       "documents": ["Hello Chroma from FastAPI!", "Second doc with different metadata"],
       "metadatas": [{ "category": "technology" }, { "category": "example" }]
     }'
```