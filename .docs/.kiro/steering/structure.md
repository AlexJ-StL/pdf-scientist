# Project Structure

## Root Directory Layout
```
├── process_pdf.py          # Main PDF processing script
├── requirements.txt        # Python dependencies
├── .env                   # Environment variables (API keys, DB config)
├── .gitignore            # Git ignore rules
├── styles.css            # CSS styling (likely for future UI)
├── .docs/                # Documentation and planning files
├── .venv/                # Python virtual environment
└── .mypy_cache/          # MyPy type checking cache
```

## Key Files
- **process_pdf.py**: Core application logic for PDF processing, text extraction, chunking, embedding generation, and MongoDB storage
- **requirements.txt**: All Python package dependencies
- **.env**: Contains sensitive configuration (API keys, database URIs)
- **processing_log.csv**: Generated log file tracking PDF processing events

## Documentation Structure
The `.docs/` folder contains:
- Project planning documents
- Architecture specifications
- Database connection examples for multiple languages
- Implementation roadmaps

## Development Conventions
- Use environment variables for all sensitive configuration
- Log processing events to CSV for tracking
- Follow the chunking strategy: 500 characters with 100 character overlap
- Store embeddings directly in MongoDB documents
- Use descriptive filenames for processed PDFs
- Close database connections after operations

## Ignored Files
- `.aider*` files (AI coding assistant artifacts)
- `.docs*` files (documentation working files)
- Standard Python cache and environment files