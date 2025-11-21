"""
Unit tests for ReadUploadDoc Azure Function.
Tests file processing functionality for PDF, DOCX, and TXT files.
"""
import pytest
import json
import base64
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys
import os

# Add the function path to sys.path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                '../../azure-deployment/functions/ReadUploadDoc'))


@pytest.mark.unit
@pytest.mark.fileprocessing
class TestReadUploadDoc:
    """Test suite for ReadUploadDoc function."""

    @pytest.fixture
    def sample_txt_content(self):
        """Sample text file content."""
        return "This is a test text file.\nIt has multiple lines.\nFor testing purposes."

    @pytest.fixture
    def sample_pdf_content(self):
        """Sample PDF content (minimal valid PDF)."""
        pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer<</Size 5/Root 1 0 R>>
startxref
306
%%EOF"""
        return pdf_content

    @pytest.fixture
    def mock_request_txt(self, sample_txt_content):
        """Mock HTTP request for TXT file."""
        mock_req = Mock()
        encoded_content = base64.b64encode(sample_txt_content.encode()).decode()
        mock_req.get_json.return_value = {
            'file_content': encoded_content,
            'file_type': 'txt'
        }
        return mock_req

    @pytest.fixture
    def mock_request_pdf(self, sample_pdf_content):
        """Mock HTTP request for PDF file."""
        mock_req = Mock()
        encoded_content = base64.b64encode(sample_pdf_content).decode()
        mock_req.get_json.return_value = {
            'file_content': encoded_content,
            'file_type': 'pdf'
        }
        return mock_req

    @pytest.fixture
    def mock_request_docx(self):
        """Mock HTTP request for DOCX file."""
        mock_req = Mock()
        # Create a minimal DOCX-like base64 content
        mock_req.get_json.return_value = {
            'file_content': 'UEsDBBQABgAIAAAAIQA=',  # Minimal ZIP header
            'file_type': 'docx'
        }
        return mock_req

    @pytest.fixture
    def mock_request_invalid_type(self):
        """Mock HTTP request with unsupported file type."""
        mock_req = Mock()
        mock_req.get_json.return_value = {
            'file_content': 'dGVzdCBjb250ZW50',
            'file_type': 'exe'
        }
        return mock_req

    @pytest.fixture
    def mock_request_missing_content(self):
        """Mock HTTP request missing file_content."""
        mock_req = Mock()
        mock_req.get_json.return_value = {
            'file_type': 'txt'
        }
        return mock_req

    @pytest.fixture
    def mock_request_missing_type(self):
        """Mock HTTP request missing file_type."""
        mock_req = Mock()
        mock_req.get_json.return_value = {
            'file_content': 'dGVzdCBjb250ZW50'
        }
        return mock_req

    @patch('ReadUploadDoc.read_txt')
    @patch('ReadUploadDoc.os.remove')
    def test_successful_txt_extraction(self, mock_remove, mock_read_txt, mock_request_txt, sample_txt_content):
        """Test successful extraction of text from TXT file."""
        mock_read_txt.return_value = sample_txt_content

        from ReadUploadDoc import ReadUploadDoc

        response = ReadUploadDoc(mock_request_txt)

        assert response.status_code == 200
        response_data = json.loads(response.get_body())
        assert "Extracted Text" in response_data
        assert response_data["Extracted Text"] == sample_txt_content

        # Verify temp file was cleaned up
        mock_remove.assert_called_once()

    @patch('ReadUploadDoc.read_pdf')
    @patch('ReadUploadDoc.os.remove')
    def test_successful_pdf_extraction(self, mock_remove, mock_read_pdf, mock_request_pdf):
        """Test successful extraction of text from PDF file."""
        expected_text = "Sample PDF content"
        mock_read_pdf.return_value = expected_text

        from ReadUploadDoc import ReadUploadDoc

        response = ReadUploadDoc(mock_request_pdf)

        assert response.status_code == 200
        response_data = json.loads(response.get_body())
        assert response_data["Extracted Text"] == expected_text

        mock_remove.assert_called_once()

    @patch('ReadUploadDoc.read_docx')
    @patch('ReadUploadDoc.os.remove')
    def test_successful_docx_extraction(self, mock_remove, mock_read_docx, mock_request_docx):
        """Test successful extraction of text from DOCX file."""
        expected_text = "Sample DOCX content"
        mock_read_docx.return_value = expected_text

        from ReadUploadDoc import ReadUploadDoc

        response = ReadUploadDoc(mock_request_docx)

        assert response.status_code == 200
        response_data = json.loads(response.get_body())
        assert response_data["Extracted Text"] == expected_text

        mock_remove.assert_called_once()

    @patch('ReadUploadDoc.os.remove')
    def test_unsupported_file_type(self, mock_remove, mock_request_invalid_type):
        """Test handling of unsupported file type."""
        from ReadUploadDoc import ReadUploadDoc

        response = ReadUploadDoc(mock_request_invalid_type)

        assert response.status_code == 400
        assert "Unsupported file type" in response.get_body().decode()

        # Temp file should still be cleaned up
        mock_remove.assert_called_once()

    def test_missing_file_content(self, mock_request_missing_content):
        """Test handling of missing file_content."""
        from ReadUploadDoc import ReadUploadDoc

        response = ReadUploadDoc(mock_request_missing_content)

        assert response.status_code == 400
        assert "Invalid input" in response.get_body().decode()

    def test_missing_file_type(self, mock_request_missing_type):
        """Test handling of missing file_type."""
        from ReadUploadDoc import ReadUploadDoc

        response = ReadUploadDoc(mock_request_missing_type)

        assert response.status_code == 400
        assert "Invalid input" in response.get_body().decode()

    def test_invalid_base64_encoding(self):
        """Test handling of invalid base64 encoding."""
        mock_req = Mock()
        mock_req.get_json.return_value = {
            'file_content': 'invalid!@#$%base64',
            'file_type': 'txt'
        }

        from ReadUploadDoc import ReadUploadDoc

        response = ReadUploadDoc(mock_req)

        assert response.status_code == 500
        assert "error occurred" in response.get_body().decode()

    @patch('ReadUploadDoc.read_txt')
    @patch('ReadUploadDoc.os.remove')
    def test_file_reading_error(self, mock_remove, mock_read_txt, mock_request_txt):
        """Test handling of file reading errors."""
        mock_read_txt.side_effect = Exception("File read error")

        from ReadUploadDoc import ReadUploadDoc

        response = ReadUploadDoc(mock_request_txt)

        assert response.status_code == 500
        assert "error occurred" in response.get_body().decode()

    @patch('ReadUploadDoc.os.remove')
    def test_temp_file_cleanup_on_error(self, mock_remove):
        """Test that temp file is cleaned up even on error."""
        mock_req = Mock()
        mock_req.get_json.return_value = {
            'file_content': 'dGVzdA==',
            'file_type': 'unsupported'
        }

        from ReadUploadDoc import ReadUploadDoc

        response = ReadUploadDoc(mock_req)

        assert response.status_code == 400
        mock_remove.assert_called_once()

    def test_case_insensitive_file_type(self):
        """Test that file type is handled case-insensitively."""
        mock_req = Mock()
        content = base64.b64encode(b"test content").decode()

        # Test uppercase
        mock_req.get_json.return_value = {
            'file_content': content,
            'file_type': 'TXT'
        }

        from ReadUploadDoc import ReadUploadDoc

        with patch('ReadUploadDoc.read_txt', return_value="test"):
            with patch('ReadUploadDoc.os.remove'):
                response = ReadUploadDoc(mock_req)
                assert response.status_code == 200

    @patch('ReadUploadDoc.read_txt')
    @patch('ReadUploadDoc.os.remove')
    def test_empty_txt_file(self, mock_remove, mock_read_txt):
        """Test extraction from empty TXT file."""
        mock_read_txt.return_value = ""

        mock_req = Mock()
        content = base64.b64encode(b"").decode()
        mock_req.get_json.return_value = {
            'file_content': content,
            'file_type': 'txt'
        }

        from ReadUploadDoc import ReadUploadDoc

        response = ReadUploadDoc(mock_req)

        assert response.status_code == 200
        response_data = json.loads(response.get_body())
        assert response_data["Extracted Text"] == ""

    @patch('ReadUploadDoc.read_txt')
    @patch('ReadUploadDoc.os.remove')
    def test_large_txt_file(self, mock_remove, mock_read_txt):
        """Test extraction from large TXT file."""
        large_content = "A" * 1000000  # 1MB of text
        mock_read_txt.return_value = large_content

        mock_req = Mock()
        content = base64.b64encode(large_content.encode()).decode()
        mock_req.get_json.return_value = {
            'file_content': content,
            'file_type': 'txt'
        }

        from ReadUploadDoc import ReadUploadDoc

        response = ReadUploadDoc(mock_req)

        assert response.status_code == 200

    @patch('ReadUploadDoc.read_txt')
    @patch('ReadUploadDoc.os.remove')
    def test_special_characters_in_txt(self, mock_remove, mock_read_txt):
        """Test extraction from TXT file with special characters."""
        special_content = "Hello! @#$%^&*() 你好 مرحبا 🎉"
        mock_read_txt.return_value = special_content

        mock_req = Mock()
        content = base64.b64encode(special_content.encode()).decode()
        mock_req.get_json.return_value = {
            'file_content': content,
            'file_type': 'txt'
        }

        from ReadUploadDoc import ReadUploadDoc

        response = ReadUploadDoc(mock_req)

        assert response.status_code == 200

    @patch('ReadUploadDoc.PdfReader')
    @patch('ReadUploadDoc.os.remove')
    def test_corrupted_pdf_file(self, mock_remove, mock_pdf_reader):
        """Test handling of corrupted PDF file."""
        mock_pdf_reader.side_effect = Exception("PDF parsing error")

        mock_req = Mock()
        content = base64.b64encode(b"corrupted pdf content").decode()
        mock_req.get_json.return_value = {
            'file_content': content,
            'file_type': 'pdf'
        }

        from ReadUploadDoc import ReadUploadDoc

        response = ReadUploadDoc(mock_req)

        assert response.status_code == 500

    @patch('ReadUploadDoc.Document')
    @patch('ReadUploadDoc.os.remove')
    def test_corrupted_docx_file(self, mock_remove, mock_document):
        """Test handling of corrupted DOCX file."""
        mock_document.side_effect = Exception("DOCX parsing error")

        mock_req = Mock()
        content = base64.b64encode(b"corrupted docx content").decode()
        mock_req.get_json.return_value = {
            'file_content': content,
            'file_type': 'docx'
        }

        from ReadUploadDoc import ReadUploadDoc

        response = ReadUploadDoc(mock_req)

        assert response.status_code == 500

    def test_invalid_json_request(self):
        """Test handling of invalid JSON request."""
        mock_req = Mock()
        mock_req.get_json.side_effect = ValueError("Invalid JSON")

        from ReadUploadDoc import ReadUploadDoc

        response = ReadUploadDoc(mock_req)

        assert response.status_code == 500


@pytest.mark.unit
class TestReadUploadDocHelperFunctions:
    """Test helper functions for file reading."""

    def test_read_txt_function(self, sample_txt_file):
        """Test read_txt helper function."""
        from ReadUploadDoc import read_txt

        content = read_txt(sample_txt_file)

        assert "This is a test text file" in content
        assert "multiple lines" in content

    def test_read_txt_nonexistent_file(self):
        """Test read_txt with nonexistent file."""
        from ReadUploadDoc import read_txt

        with pytest.raises(FileNotFoundError):
            read_txt("/nonexistent/file.txt")

    def test_read_docx_function(self, sample_docx_file):
        """Test read_docx helper function."""
        from ReadUploadDoc import read_docx

        content = read_docx(sample_docx_file)

        assert "Hello from DOCX" in content

    def test_read_pdf_function(self, sample_pdf_file):
        """Test read_pdf helper function."""
        from ReadUploadDoc import read_pdf

        content = read_pdf(sample_pdf_file)

        # PDF extraction may vary, just check it doesn't error
        assert isinstance(content, str)

    def test_read_pdf_nonexistent_file(self):
        """Test read_pdf with nonexistent file."""
        from ReadUploadDoc import read_pdf

        with pytest.raises(Exception):
            read_pdf("/nonexistent/file.pdf")

    @patch('builtins.open', side_effect=IOError("Permission denied"))
    def test_read_txt_permission_error(self, mock_file):
        """Test read_txt with permission error."""
        from ReadUploadDoc import read_txt

        with pytest.raises(IOError):
            read_txt("/restricted/file.txt")

    def test_read_docx_with_multiple_paragraphs(self, tmp_path):
        """Test read_docx with multiple paragraphs."""
        # This test requires the actual docx library, which should parse correctly
        docx_path = tmp_path / "multi_para.docx"

        # Create a minimal DOCX with multiple paragraphs
        import zipfile
        from io import BytesIO

        docx_zip = BytesIO()
        with zipfile.ZipFile(docx_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')
            zipf.writestr('_rels/.rels', '''<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')
            zipf.writestr('word/document.xml', '''<?xml version="1.0"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:r><w:t>First paragraph</w:t></w:r></w:p>
<w:p><w:r><w:t>Second paragraph</w:t></w:r></w:p>
<w:p><w:r><w:t>Third paragraph</w:t></w:r></w:p>
</w:body>
</w:document>''')

        docx_path.write_bytes(docx_zip.getvalue())

        from ReadUploadDoc import read_docx

        content = read_docx(str(docx_path))

        assert "First paragraph" in content
        assert "Second paragraph" in content
        assert "Third paragraph" in content
        assert content.count('\n') >= 2  # At least 2 newlines for 3 paragraphs
