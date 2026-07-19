# Configure Chroma SDK

* This database connection string connects you to Chroma Cloud.
* Chroma Cloud has the exact same API as Local Chroma - so there is no code migration necessary. Just update your client to one of the options below

* **In the below examples the following credentials were used as if they were in the workspace `.env` file:**
CHROMA_HOST=api.trychroma.com
CHROMADB_API_KEY=[see $PATH]
CHROMADB_TENANT_ID=[see $PATH]
CHROMA_DATABASE=epa_methods

---

## Install and Code for Python, Rust, and TypeScript:

1) **Python**
```Bash
uv pip install chromadb
```
```Python
import chromadb

client = chromadb.CloudClient(
  api_key='CHROMADB_API_KEY',
  tenant='CHROMADB_TENANT_ID',
  database='epa_methods'
)
```

2) **Rust**
```Bash
cargo add chroma
```
```Rust
use chroma::{ChromaHttpClient, ChromaHttpClientOptions};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
let client = ChromaHttpClient::new(ChromaHttpClientOptions::chroma_cloud("CHROMADB_API_KEY", "epa_methods")?);
  let collections = client.list_collections(100, None).await?;
  println!("{:#?}", collections);
  Ok(())
}
```

3) **TypeScript**
```Bash
npm install chromadb @chroma-core/default-embed
```
```TypeScript
import { CloudClient } from "chromadb";

const client = new CloudClient({
  apiKey: 'CHROMADB_API_KEY',
  tenant: 'CHROMADB_TENANT_ID',
  database: 'epa_methods'
});
```
