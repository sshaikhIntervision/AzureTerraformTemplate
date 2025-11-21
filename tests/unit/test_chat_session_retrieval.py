"""
Unit tests for ChatSessionRetreival Azure Function.
Tests session retrieval functionality with database mocking.
"""
import pytest
import json
import datetime
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the function path to sys.path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                '../../azure-deployment/functions/ChatSessionRetreival'))


@pytest.mark.unit
@pytest.mark.database
class TestChatSessionRetreival:
    """Test suite for ChatSessionRetreival function."""

    @pytest.fixture
    def mock_request_valid(self):
        """Mock valid HTTP request."""
        mock_req = Mock()
        mock_req.get_json.return_value = {'email': 'test@example.com'}
        return mock_req

    @pytest.fixture
    def mock_request_invalid_json(self):
        """Mock HTTP request with invalid JSON."""
        mock_req = Mock()
        mock_req.get_json.side_effect = ValueError("Invalid JSON")
        return mock_req

    @pytest.fixture
    def mock_request_missing_email(self):
        """Mock HTTP request missing email field."""
        mock_req = Mock()
        mock_req.get_json.return_value = {}
        return mock_req

    @patch('ChatSessionRetreival.psycopg2.connect')
    def test_successful_session_retrieval_with_results(self, mock_connect, mock_request_valid):
        """Test successful retrieval of chat sessions."""
        # Setup mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock database results
        mock_rows = [
            ('session-1', datetime.datetime(2025, 11, 21, 10, 0, 0), 'What is Azure?'),
            ('session-2', datetime.datetime(2025, 11, 21, 11, 0, 0), 'How to deploy functions?'),
            ('session-1', datetime.datetime(2025, 11, 21, 9, 0, 0), 'Hello'),  # Older message in session-1
        ]
        mock_cursor.fetchall.return_value = mock_rows

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Import and test the function
        from ChatSessionRetreival import ChatSessionRetreival

        response = ChatSessionRetreival(mock_request_valid)

        # Assertions
        assert response.status_code == 200
        assert response.mimetype == "application/json"

        # Parse response body
        response_data = json.loads(response.get_body())

        # Should have 2 sessions (latest message from each)
        assert len(response_data) == 2

        # Verify sessions are sorted by timestamp (newest first)
        assert response_data[0]['sessionId'] == 'session-2'
        assert response_data[1]['sessionId'] == 'session-1'

        # Verify latest message is picked for session-1
        assert response_data[1]['Input_query'] == 'What is Azure?'

        # Verify database operations
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('ChatSessionRetreival.psycopg2.connect')
    def test_successful_session_retrieval_no_results(self, mock_connect, mock_request_valid):
        """Test retrieval when no chat history exists."""
        # Setup mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from ChatSessionRetreival import ChatSessionRetreival

        response = ChatSessionRetreival(mock_request_valid)

        # Assertions
        assert response.status_code == 200
        assert response.mimetype == "application/json"

        response_data = json.loads(response.get_body())
        assert response_data == []

    def test_invalid_json_request(self, mock_request_invalid_json):
        """Test handling of invalid JSON in request."""
        from ChatSessionRetreival import ChatSessionRetreival

        response = ChatSessionRetreival(mock_request_invalid_json)

        assert response.status_code == 400
        assert "Invalid request body" in response.get_body().decode()

    @patch('ChatSessionRetreival.psycopg2.connect')
    def test_missing_email_field(self, mock_connect, mock_request_missing_email):
        """Test handling of missing email field."""
        from ChatSessionRetreival import ChatSessionRetreival

        with pytest.raises(KeyError):
            ChatSessionRetreival(mock_request_missing_email)

    @patch('ChatSessionRetreival.psycopg2.connect')
    def test_database_connection_error(self, mock_connect, mock_request_valid):
        """Test handling of database connection errors."""
        mock_connect.side_effect = Exception("Database connection failed")

        from ChatSessionRetreival import ChatSessionRetreival

        response = ChatSessionRetreival(mock_request_valid)

        assert response.status_code == 500
        assert "Error fetching data" in response.get_body().decode()

    @patch('ChatSessionRetreival.psycopg2.connect')
    def test_database_query_error(self, mock_connect, mock_request_valid):
        """Test handling of database query errors."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Query execution failed")

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from ChatSessionRetreival import ChatSessionRetreival

        response = ChatSessionRetreival(mock_request_valid)

        assert response.status_code == 500
        assert "Error fetching data" in response.get_body().decode()

    @patch('ChatSessionRetreival.psycopg2.connect')
    def test_timestamp_string_handling(self, mock_connect, mock_request_valid):
        """Test handling of timestamp as string instead of datetime object."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock database results with string timestamps
        mock_rows = [
            ('session-1', '2025-11-21T10:00:00', 'What is Azure?'),
            ('session-2', '2025-11-21T11:00:00', 'How to deploy?'),
        ]
        mock_cursor.fetchall.return_value = mock_rows

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from ChatSessionRetreival import ChatSessionRetreival

        response = ChatSessionRetreival(mock_request_valid)

        assert response.status_code == 200
        response_data = json.loads(response.get_body())
        assert len(response_data) == 2

    @patch('ChatSessionRetreival.psycopg2.connect')
    def test_sql_injection_prevention(self, mock_connect, mock_request_valid):
        """Test that SQL injection is prevented through parameterized queries."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Request with potential SQL injection
        mock_request_valid.get_json.return_value = {
            'email': "test@example.com'; DROP TABLE chat_logs; --"
        }

        from ChatSessionRetreival import ChatSessionRetreival

        response = ChatSessionRetreival(mock_request_valid)

        # Verify parameterized query was used
        call_args = mock_cursor.execute.call_args
        assert call_args[0][1] == ("test@example.com'; DROP TABLE chat_logs; --",)
        assert response.status_code == 200

    @patch('ChatSessionRetreival.psycopg2.connect')
    def test_large_result_set(self, mock_connect, mock_request_valid):
        """Test handling of large result sets."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Generate large number of sessions
        mock_rows = [
            (f'session-{i}', datetime.datetime(2025, 11, 21, i % 24, 0, 0), f'Query {i}')
            for i in range(100)
        ]
        mock_cursor.fetchall.return_value = mock_rows

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from ChatSessionRetreival import ChatSessionRetreival

        response = ChatSessionRetreival(mock_request_valid)

        assert response.status_code == 200
        response_data = json.loads(response.get_body())
        assert len(response_data) == 100

    @patch('ChatSessionRetreival.get_db_connection')
    def test_get_db_connection_error_handling(self, mock_get_connection):
        """Test error handling in get_db_connection function."""
        mock_get_connection.side_effect = Exception("Connection timeout")

        from ChatSessionRetreival import ChatSessionRetreival

        mock_req = Mock()
        mock_req.get_json.return_value = {'email': 'test@example.com'}

        response = ChatSessionRetreival(mock_req)

        assert response.status_code == 500
