"""
Unit tests for UpdateChatlogsDB Azure Function.
Tests chat log insertion functionality with database mocking.
"""
import pytest
import json
import datetime
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the function path to sys.path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                '../../azure-deployment/functions/UpdateChatlogsDB'))


@pytest.mark.unit
@pytest.mark.database
class TestUpdateChatlogsDB:
    """Test suite for UpdateChatlogsDB function."""

    @pytest.fixture
    def mock_request_full_data(self):
        """Mock HTTP request with complete chat log data."""
        mock_req = Mock()
        data = {
            'message_uuid': 'msg-123',
            'timestamp': '2025-11-21T10:00:00',
            'chat_summary': 'Discussion about Azure',
            'data_source': 'azure-docs',
            'document_upload': False,
            'email': 'test@example.com',
            'feedback': 'positive',
            'feedback_text': 'Very helpful',
            'feedback_type': 'thumbs_up',
            'input_query': 'What is Azure?',
            'output': 'Azure is a cloud platform',
            'processed_query': 'what is azure',
            'sessionid': 'session-123',
            'sources': ['doc1.pdf', 'doc2.pdf'],
            'doc_content': None,
            'doc_type': None
        }
        mock_req.get_json.return_value = data
        return mock_req

    @pytest.fixture
    def mock_request_minimal_data(self):
        """Mock HTTP request with minimal required data."""
        mock_req = Mock()
        data = {
            'email': 'test@example.com',
            'input_query': 'Hello',
            'output': 'Hi there!'
        }
        mock_req.get_json.return_value = data
        return mock_req

    @pytest.fixture
    def mock_request_invalid_json(self):
        """Mock HTTP request with invalid JSON."""
        mock_req = Mock()
        mock_req.get_json.side_effect = ValueError("Invalid JSON")
        return mock_req

    @patch('UpdateChatlogsDB.psycopg2.connect')
    def test_successful_insertion_full_data(self, mock_connect, mock_request_full_data):
        """Test successful insertion of chat log with all fields."""
        # Setup mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Import and test the function
        from UpdateChatlogsDB import UpdateChatlogsDB

        response = UpdateChatlogsDB(mock_request_full_data)

        # Assertions
        assert response.status_code == 200
        assert "Object stored successfully" in response.get_body().decode()

        # Verify database operations
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

        # Verify correct data was passed to execute
        call_args = mock_cursor.execute.call_args
        data_tuple = call_args[0][1]

        assert data_tuple[0] == 'msg-123'  # message_uuid
        assert data_tuple[5] == 'test@example.com'  # email
        assert data_tuple[9] == 'What is Azure?'  # input_query
        assert data_tuple[10] == 'Azure is a cloud platform'  # output

    @patch('UpdateChatlogsDB.psycopg2.connect')
    def test_successful_insertion_minimal_data(self, mock_connect, mock_request_minimal_data):
        """Test insertion with minimal data, auto-generating UUIDs."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from UpdateChatlogsDB import UpdateChatlogsDB

        response = UpdateChatlogsDB(mock_request_minimal_data)

        assert response.status_code == 200

        # Verify that execute was called (UUIDs should be auto-generated)
        mock_cursor.execute.assert_called_once()

        # Verify data tuple structure
        call_args = mock_cursor.execute.call_args
        data_tuple = call_args[0][1]

        # Should have 16 fields
        assert len(data_tuple) == 16
        # Email should be present
        assert data_tuple[5] == 'test@example.com'

    def test_invalid_json_request(self, mock_request_invalid_json):
        """Test handling of invalid JSON in request."""
        from UpdateChatlogsDB import UpdateChatlogsDB

        response = UpdateChatlogsDB(mock_request_invalid_json)

        assert response.status_code == 400
        assert "Invalid JSON format" in response.get_body().decode()

    @patch('UpdateChatlogsDB.psycopg2.connect')
    def test_database_connection_error(self, mock_connect, mock_request_full_data):
        """Test handling of database connection errors."""
        mock_connect.side_effect = Exception("Database connection failed")

        from UpdateChatlogsDB import UpdateChatlogsDB

        response = UpdateChatlogsDB(mock_request_full_data)

        assert response.status_code == 500
        assert "error occurred" in response.get_body().decode()

    @patch('UpdateChatlogsDB.psycopg2.connect')
    def test_database_insertion_error(self, mock_connect, mock_request_full_data):
        """Test handling of database insertion errors."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Insertion failed")

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from UpdateChatlogsDB import UpdateChatlogsDB

        response = UpdateChatlogsDB(mock_request_full_data)

        assert response.status_code == 500

    @patch('UpdateChatlogsDB.psycopg2.connect')
    def test_sources_json_serialization(self, mock_connect):
        """Test that sources array is properly JSON serialized."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_req = Mock()
        mock_req.get_json.return_value = {
            'email': 'test@example.com',
            'sources': ['doc1.pdf', 'doc2.pdf', 'doc3.pdf']
        }

        from UpdateChatlogsDB import UpdateChatlogsDB

        response = UpdateChatlogsDB(mock_req)

        assert response.status_code == 200

        # Verify sources was JSON serialized
        call_args = mock_cursor.execute.call_args
        data_tuple = call_args[0][1]
        sources_json = data_tuple[13]  # sources field

        assert isinstance(sources_json, str)
        assert 'doc1.pdf' in sources_json
        assert 'doc2.pdf' in sources_json

    @patch('UpdateChatlogsDB.psycopg2.connect')
    @patch('UpdateChatlogsDB.uuid.uuid4')
    def test_auto_generated_uuids(self, mock_uuid, mock_connect):
        """Test that UUIDs are auto-generated when not provided."""
        mock_uuid.return_value = 'auto-generated-uuid'

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_req = Mock()
        mock_req.get_json.return_value = {
            'email': 'test@example.com',
            'input_query': 'Test query'
        }

        from UpdateChatlogsDB import UpdateChatlogsDB

        response = UpdateChatlogsDB(mock_req)

        assert response.status_code == 200

    @patch('UpdateChatlogsDB.psycopg2.connect')
    @patch('UpdateChatlogsDB.datetime')
    def test_auto_generated_timestamp(self, mock_datetime, mock_connect):
        """Test that timestamp is auto-generated when not provided."""
        mock_now = datetime.datetime(2025, 11, 21, 12, 0, 0)
        mock_datetime.datetime.now.return_value = mock_now

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_req = Mock()
        mock_req.get_json.return_value = {
            'email': 'test@example.com'
        }

        from UpdateChatlogsDB import UpdateChatlogsDB

        response = UpdateChatlogsDB(mock_req)

        assert response.status_code == 200

    @patch('UpdateChatlogsDB.psycopg2.connect')
    def test_commit_error(self, mock_connect, mock_request_full_data):
        """Test handling of database commit errors."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.commit.side_effect = Exception("Commit failed")

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from UpdateChatlogsDB import UpdateChatlogsDB

        response = UpdateChatlogsDB(mock_request_full_data)

        assert response.status_code == 500

    @patch('UpdateChatlogsDB.psycopg2.connect')
    def test_special_characters_in_data(self, mock_connect):
        """Test insertion with special characters in text fields."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_req = Mock()
        mock_req.get_json.return_value = {
            'email': 'test@example.com',
            'input_query': "What's the difference between Azure & AWS?",
            'output': 'Azure is Microsoft\'s cloud platform, while AWS is Amazon\'s.',
            'feedback_text': 'Great explanation! 👍'
        }

        from UpdateChatlogsDB import UpdateChatlogsDB

        response = UpdateChatlogsDB(mock_req)

        assert response.status_code == 200

    @patch('UpdateChatlogsDB.psycopg2.connect')
    def test_null_optional_fields(self, mock_connect):
        """Test insertion with None values for optional fields."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_req = Mock()
        mock_req.get_json.return_value = {
            'email': 'test@example.com',
            'input_query': 'Test',
            'feedback': None,
            'feedback_text': None,
            'doc_content': None
        }

        from UpdateChatlogsDB import UpdateChatlogsDB

        response = UpdateChatlogsDB(mock_req)

        assert response.status_code == 200

    @patch('UpdateChatlogsDB.psycopg2.connect')
    def test_large_text_fields(self, mock_connect):
        """Test insertion with large text content."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_req = Mock()
        large_text = "A" * 10000  # 10KB of text
        mock_req.get_json.return_value = {
            'email': 'test@example.com',
            'input_query': large_text,
            'output': large_text,
            'doc_content': large_text
        }

        from UpdateChatlogsDB import UpdateChatlogsDB

        response = UpdateChatlogsDB(mock_req)

        assert response.status_code == 200

    @patch('UpdateChatlogsDB.get_db_connection')
    def test_get_db_connection_error_handling(self, mock_get_connection):
        """Test error handling in get_db_connection function."""
        mock_get_connection.side_effect = Exception("Connection timeout")

        from UpdateChatlogsDB import UpdateChatlogsDB

        mock_req = Mock()
        mock_req.get_json.return_value = {'email': 'test@example.com'}

        response = UpdateChatlogsDB(mock_req)

        assert response.status_code == 500

    @patch('UpdateChatlogsDB.psycopg2.connect')
    def test_document_upload_scenario(self, mock_connect):
        """Test insertion with document upload data."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_req = Mock()
        mock_req.get_json.return_value = {
            'email': 'test@example.com',
            'document_upload': True,
            'doc_content': 'This is the extracted document content',
            'doc_type': 'pdf',
            'input_query': 'Analyze this document'
        }

        from UpdateChatlogsDB import UpdateChatlogsDB

        response = UpdateChatlogsDB(mock_req)

        assert response.status_code == 200

        # Verify document fields were stored
        call_args = mock_cursor.execute.call_args
        data_tuple = call_args[0][1]
        assert data_tuple[14] == 'This is the extracted document content'  # doc_content
        assert data_tuple[15] == 'pdf'  # doc_type
