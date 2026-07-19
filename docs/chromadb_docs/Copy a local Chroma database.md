# Copy a local Chroma database

* Upload your existing data to Chroma Cloud using the Chroma CLI

* **Step 1:** Install the CLI
```Python
pip install chroma
```
```Mac + Unix
curl -sSL https://raw.githubusercontent.com/chroma-core/chroma/main/rust/cli/install/install.sh | bash
```
```Windows
iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/chroma-core/chroma/main/rust/cli/install/install.ps1'))

* **Step 2:** Copy local database to Chroma Cloud
chroma login
chroma copy --all --from-local --to-cloud --db epa_methods