# Technology Stack

## Core Technologies
- **Language**: Python 3.12
- **Database**: MongoDB Atlas (cloud-hosted)
- **Vector Embeddings**: OpenAI Embeddings API
- **Environment Management**: python-dotenv for configuration

## Key Libraries
- **PyPDF2**: PDF text extraction
- **langchain**: Text processing, embeddings, and vector operations
- **tiktoken**: Token counting for OpenAI models
- **pymongo**: MongoDB database operations
- **pandas**: Data processing and logging
- **python-dotenv**: Environment variable management

## Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables in .env file
OPENAI_API_KEY=your_openai_api_key
MONGODB_URI=your_mongodb_connection_string
```

## Database Configuration
- Database: `epa_methods`
- Collection: `documents`
- Document structure includes: filename, chunk_index, text, embedding

## Common Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run the PDF processor (modify the example usage in process_pdf.py)
python process_pdf.py
```

## API Keys Required
- OpenAI API key for embeddings
- MongoDB Atlas connection string
- Additional API keys available: Gemini, Anthropic, Groq, Samba