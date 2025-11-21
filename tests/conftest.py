"""
Pytest configuration and shared fixtures for Azure Functions tests.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import json
import os
from typing import Dict, Any


@pytest.fixture
def mock_azure_function_request():
    """Mock Azure Functions HttpRequest object."""
    mock_req = Mock()
    mock_req.method = "POST"
    mock_req.url = "http://localhost:7071/api/function"
    mock_req.headers = {"Content-Type": "application/json"}

    def get_json():
        return {"test": "data"}

    mock_req.get_json = get_json
    mock_req.get_body = lambda: b'{"test": "data"}'
    mock_req.params = {}

    return mock_req


@pytest.fixture
def mock_database_connection():
    """Mock PostgreSQL database connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Setup cursor mock
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchone.return_value = None
    mock_cursor.execute.return_value = None
    mock_cursor.description = []

    # Setup connection mock
    mock_conn.cursor.return_value.__enter__ = lambda self: mock_cursor
    mock_conn.cursor.return_value.__exit__ = lambda self, *args: None
    mock_conn.commit.return_value = None
    mock_conn.close.return_value = None

    return mock_conn, mock_cursor


@pytest.fixture
def mock_psycopg2_connect(mock_database_connection):
    """Mock psycopg2.connect function."""
    mock_conn, mock_cursor = mock_database_connection

    with patch('psycopg2.connect', return_value=mock_conn) as mock_connect:
        yield mock_connect, mock_conn, mock_cursor


@pytest.fixture
def mock_environment_variables():
    """Mock environment variables for Azure Functions."""
    env_vars = {
        'POSTGRES_HOST': 'test-db.postgres.database.azure.com',
        'POSTGRES_DB': 'test_db',
        'POSTGRES_USER': 'test_user',
        'POSTGRES_PASSWORD': 'test_password',
        'AZURE_SEARCH_ENDPOINT': 'https://test-search.search.windows.net',
        'AZURE_SEARCH_KEY': 'test-search-key',
        'AZURE_OPENAI_ENDPOINT': 'https://test-openai.openai.azure.com',
        'AZURE_OPENAI_KEY': 'test-openai-key',
        'AZURE_OPENAI_DEPLOYMENT': 'gpt-4'
    }

    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def sample_chat_session():
    """Sample chat session data."""
    return {
        'session_id': 'test-session-123',
        'user_email': 'test@example.com',
        'timestamp': '2025-11-21T10:00:00',
        'query': 'What is Azure?',
        'response': 'Azure is Microsoft cloud computing platform.',
        'sources': ['doc1.pdf', 'doc2.pdf']
    }


@pytest.fixture
def sample_feedback():
    """Sample feedback data."""
    return {
        'session_id': 'test-session-123',
        'user_email': 'test@example.com',
        'feedback': 'positive',
        'rating': 5,
        'comment': 'Very helpful response!'
    }


@pytest.fixture
def sample_pdf_file(tmp_path):
    """Create a sample PDF file for testing."""
    pdf_path = tmp_path / "test.pdf"
    # Create a minimal valid PDF
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
409
%%EOF"""
    pdf_path.write_bytes(pdf_content)
    return str(pdf_path)


@pytest.fixture
def sample_docx_file(tmp_path):
    """Create a sample DOCX file for testing."""
    docx_path = tmp_path / "test.docx"
    # Create a minimal DOCX (ZIP archive)
    import zipfile
    from io import BytesIO

    # Create minimal DOCX structure
    docx_zip = BytesIO()
    with zipfile.ZipFile(docx_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add [Content_Types].xml
        zipf.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')

        # Add _rels/.rels
        zipf.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')

        # Add word/document.xml with sample text
        zipf.writestr('word/document.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:r><w:t>Hello from DOCX</w:t></w:r></w:p>
</w:body>
</w:document>''')

    docx_path.write_bytes(docx_zip.getvalue())
    return str(docx_path)


@pytest.fixture
def sample_txt_file(tmp_path):
    """Create a sample TXT file for testing."""
    txt_path = tmp_path / "test.txt"
    txt_path.write_text("This is a test text file.\nIt has multiple lines.\nFor testing purposes.")
    return str(txt_path)


@pytest.fixture
def mock_azure_search_client():
    """Mock Azure Search Client."""
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.get_answers.return_value = []
    mock_result.__iter__ = lambda self: iter([
        {
            'content': 'Sample search result',
            'metadata_storage_name': 'doc1.pdf',
            '@search.score': 0.95
        }
    ])
    mock_client.search.return_value = mock_result
    return mock_client


@pytest.fixture
def mock_openai_client():
    """Mock Azure OpenAI Client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(content='This is a test AI response.')
        )
    ]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_http_response():
    """Mock HTTP response from function to function calls."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({'status': 'success', 'data': []})
    mock_response.json.return_value = {'status': 'success', 'data': []}
    return mock_response
