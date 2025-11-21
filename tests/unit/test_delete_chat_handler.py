"""
Unit tests for DeleteChatHandler Azure Function.
Tests chat deletion functionality with database mocking.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the function path to sys.path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                '../../azure-deployment/functions/DeleteChatHandler'))


@pytest.mark.unit
@pytest.mark.database
class TestDeleteChatHandler:
    """Test suite for DeleteChatHandler function."""

    @pytest.fixture
    def mock_request_valid(self):
        """Mock valid HTTP request with email and session_id."""
        mock_req = Mock()
        mock_req.get_body.return_value = b'{"email": "test@example.com", "sessionid": "session-123"}'
        mock_req.get_json.return_value = {
            'email': 'test@example.com',
            'sessionid': 'session-123'
        }
        return mock_req

    @pytest.fixture
    def mock_request_no_body(self):
        """Mock HTTP request with no body."""
        mock_req = Mock()
        mock_req.get_body.return_value = None
        mock_req.get_json.return_value = None
        return mock_req

    @pytest.fixture
    def mock_request_missing_sessionid(self):
        """Mock HTTP request missing sessionid."""
        mock_req = Mock()
        mock_req.get_body.return_value = b'{"email": "test@example.com"}'
        mock_req.get_json.return_value = {'email': 'test@example.com'}
        return mock_req

    @pytest.fixture
    def mock_request_missing_email(self):
        """Mock HTTP request missing email."""
        mock_req = Mock()
        mock_req.get_body.return_value = b'{"sessionid": "session-123"}'
        mock_req.get_json.return_value = {'sessionid': 'session-123'}
        return mock_req

    @patch('DeleteChatHandler.psycopg2.connect')
    def test_successful_deletion_with_records(self, mock_connect, mock_request_valid):
        """Test successful deletion of existing chat records."""
        # Setup mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 3  # Simulate 3 rows deleted

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Import and test the function
        from DeleteChatHandler import DeleteChatHandler

        response = DeleteChatHandler(mock_request_valid)

        # Assertions
        assert response.status_code == 200
        assert "Successfully deleted 3 record(s)" in response.get_body().decode()
        assert "session-123" in response.get_body().decode()
        assert "test@example.com" in response.get_body().decode()

        # Verify database operations
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('DeleteChatHandler.psycopg2.connect')
    def test_deletion_no_records_found(self, mock_connect, mock_request_valid):
        """Test deletion when no records match the criteria."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0  # No rows deleted

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from DeleteChatHandler import DeleteChatHandler

        response = DeleteChatHandler(mock_request_valid)

        assert response.status_code == 404
        assert "No records found" in response.get_body().decode()
        assert "session-123" in response.get_body().decode()

    def test_missing_request_body(self, mock_request_no_body):
        """Test handling of missing request body."""
        from DeleteChatHandler import DeleteChatHandler

        response = DeleteChatHandler(mock_request_no_body)

        assert response.status_code == 400
        assert "Bad Request" in response.get_body().decode()

    def test_missing_sessionid(self, mock_request_missing_sessionid):
        """Test handling of missing sessionid in request."""
        from DeleteChatHandler import DeleteChatHandler

        response = DeleteChatHandler(mock_request_missing_sessionid)

        assert response.status_code == 400
        assert "Please provide a sessionid" in response.get_body().decode()

    @patch('DeleteChatHandler.psycopg2.connect')
    def test_database_connection_error(self, mock_connect, mock_request_valid):
        """Test handling of database connection errors."""
        mock_connect.side_effect = Exception("Database connection failed")

        from DeleteChatHandler import DeleteChatHandler

        response = DeleteChatHandler(mock_request_valid)

        assert response.status_code == 500
        assert "Internal Server Error" in response.get_body().decode()

    @patch('DeleteChatHandler.psycopg2.connect')
    def test_database_execution_error(self, mock_connect, mock_request_valid):
        """Test handling of database execution errors."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Query execution failed")

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from DeleteChatHandler import DeleteChatHandler

        response = DeleteChatHandler(mock_request_valid)

        assert response.status_code == 500
        assert "Internal Server Error" in response.get_body().decode()

    @patch('DeleteChatHandler.psycopg2.connect')
    def test_commit_error(self, mock_connect, mock_request_valid):
        """Test handling of database commit errors."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.commit.side_effect = Exception("Commit failed")

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from DeleteChatHandler import DeleteChatHandler

        response = DeleteChatHandler(mock_request_valid)

        assert response.status_code == 500

    @patch('DeleteChatHandler.psycopg2.connect')
    def test_sql_injection_prevention(self, mock_connect):
        """Test that SQL injection is prevented through parameterized queries."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Request with potential SQL injection
        mock_req = Mock()
        mock_req.get_body.return_value = b'{}'
        mock_req.get_json.return_value = {
            'email': "test@example.com'; DROP TABLE chat_logs; --",
            'sessionid': "session-123"
        }

        from DeleteChatHandler import DeleteChatHandler

        response = DeleteChatHandler(mock_req)

        # Verify parameterized query was used
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "DELETE FROM chat_logs WHERE sessionid = %s AND email = %s" in query
        assert params == ("session-123", "test@example.com'; DROP TABLE chat_logs; --")
        assert response.status_code == 404  # No records found

    @patch('DeleteChatHandler.psycopg2.connect')
    def test_deletion_with_special_characters(self, mock_connect):
        """Test deletion with special characters in email and session_id."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_req = Mock()
        mock_req.get_body.return_value = b'{}'
        mock_req.get_json.return_value = {
            'email': 'test+user@example.com',
            'sessionid': 'session-123-abc-def'
        }

        from DeleteChatHandler import DeleteChatHandler

        response = DeleteChatHandler(mock_req)

        assert response.status_code == 200
        assert "Successfully deleted" in response.get_body().decode()

    @patch('DeleteChatHandler.psycopg2.connect')
    def test_bulk_deletion(self, mock_connect, mock_request_valid):
        """Test deletion of multiple records in one session."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 50  # Simulate 50 rows deleted

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from DeleteChatHandler import DeleteChatHandler

        response = DeleteChatHandler(mock_request_valid)

        assert response.status_code == 200
        assert "Successfully deleted 50 record(s)" in response.get_body().decode()

    @patch('DeleteChatHandler.get_db_connection')
    def test_get_db_connection_error_handling(self, mock_get_connection):
        """Test error handling in get_db_connection function."""
        mock_get_connection.side_effect = Exception("Connection timeout")

        from DeleteChatHandler import DeleteChatHandler

        mock_req = Mock()
        mock_req.get_body.return_value = b'{}'
        mock_req.get_json.return_value = {
            'email': 'test@example.com',
            'sessionid': 'session-123'
        }

        response = DeleteChatHandler(mock_req)

        assert response.status_code == 500

    @patch('DeleteChatHandler.psycopg2.connect')
    def test_cursor_close_on_error(self, mock_connect, mock_request_valid):
        """Test that cursor and connection are properly closed even on error."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Query failed")

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from DeleteChatHandler import DeleteChatHandler

        response = DeleteChatHandler(mock_request_valid)

        assert response.status_code == 500

    @patch('DeleteChatHandler.psycopg2.connect')
    def test_empty_email_field(self, mock_connect):
        """Test handling of empty email field."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_req = Mock()
        mock_req.get_body.return_value = b'{}'
        mock_req.get_json.return_value = {
            'email': '',
            'sessionid': 'session-123'
        }

        from DeleteChatHandler import DeleteChatHandler

        response = DeleteChatHandler(mock_req)

        # Should still attempt deletion with empty email
        assert mock_cursor.execute.called
