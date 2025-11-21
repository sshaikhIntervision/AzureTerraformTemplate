"""
Unit tests for FeedbackHandler Azure Function.
Tests feedback update functionality with database mocking.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the function path to sys.path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                '../../azure-deployment/functions/FeedbackHandler'))


@pytest.mark.unit
@pytest.mark.database
class TestFeedbackHandler:
    """Test suite for FeedbackHandler function."""

    @pytest.fixture
    def mock_request_full_feedback(self):
        """Mock HTTP request with complete feedback data."""
        mock_req = Mock()
        mock_req.get_json.return_value = {
            'sessionid': 'session-123',
            'message_uuid': 'msg-456',
            'feedback': 'positive',
            'feedback_text': 'Very helpful response!',
            'feedback_type': 'thumbs_up'
        }
        return mock_req

    @pytest.fixture
    def mock_request_minimal_feedback(self):
        """Mock HTTP request with minimal feedback data."""
        mock_req = Mock()
        mock_req.get_json.return_value = {
            'sessionid': 'session-123',
            'message_uuid': 'msg-456',
            'feedback': 'positive'
        }
        return mock_req

    @pytest.fixture
    def mock_request_invalid_json(self):
        """Mock HTTP request with invalid JSON."""
        mock_req = Mock()
        mock_req.get_json.side_effect = ValueError("Invalid JSON")
        return mock_req

    @pytest.fixture
    def mock_request_missing_required(self):
        """Mock HTTP request missing required fields."""
        mock_req = Mock()
        mock_req.get_json.return_value = {
            'sessionid': 'session-123'
            # Missing message_uuid and feedback
        }
        return mock_req

    @patch('FeedbackHandler.psycopg2.connect')
    def test_successful_feedback_update_full_data(self, mock_connect, mock_request_full_feedback):
        """Test successful feedback update with all optional fields."""
        # Setup mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Import and test the function
        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_request_full_feedback)

        # Assertions
        assert response.status_code == 200
        assert "updated successfully" in response.get_body().decode()
        assert "session-123" in response.get_body().decode()
        assert "msg-456" in response.get_body().decode()

        # Verify database operations
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

        # Verify SQL query structure
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "UPDATE chat_logs SET feedback = %s" in query
        assert "feedback_text = %s" in query
        assert "feedback_type = %s" in query
        assert "WHERE sessionid = %s AND message_uuid = %s" in query
        assert params == ('positive', 'Very helpful response!', 'thumbs_up', 'session-123', 'msg-456')

    @patch('FeedbackHandler.psycopg2.connect')
    def test_successful_feedback_update_minimal_data(self, mock_connect, mock_request_minimal_feedback):
        """Test feedback update with only required fields."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_request_minimal_feedback)

        assert response.status_code == 200

        # Verify SQL query only includes feedback field
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "UPDATE chat_logs SET feedback = %s" in query
        assert "feedback_text" not in query
        assert "feedback_type" not in query
        assert params == ('positive', 'session-123', 'msg-456')

    def test_invalid_json_request(self, mock_request_invalid_json):
        """Test handling of invalid JSON in request."""
        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_request_invalid_json)

        assert response.status_code == 400
        assert "Invalid JSON format" in response.get_body().decode()

    def test_missing_required_fields(self, mock_request_missing_required):
        """Test handling of missing required fields."""
        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_request_missing_required)

        assert response.status_code == 400
        assert "Please provide sessionid, message_uuid, and feedback" in response.get_body().decode()

    @patch('FeedbackHandler.psycopg2.connect')
    def test_missing_sessionid(self, mock_connect):
        """Test handling of missing sessionid."""
        mock_req = Mock()
        mock_req.get_json.return_value = {
            'message_uuid': 'msg-456',
            'feedback': 'positive'
        }

        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_req)

        assert response.status_code == 400

    @patch('FeedbackHandler.psycopg2.connect')
    def test_missing_message_uuid(self, mock_connect):
        """Test handling of missing message_uuid."""
        mock_req = Mock()
        mock_req.get_json.return_value = {
            'sessionid': 'session-123',
            'feedback': 'positive'
        }

        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_req)

        assert response.status_code == 400

    @patch('FeedbackHandler.psycopg2.connect')
    def test_missing_feedback(self, mock_connect):
        """Test handling of missing feedback."""
        mock_req = Mock()
        mock_req.get_json.return_value = {
            'sessionid': 'session-123',
            'message_uuid': 'msg-456'
        }

        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_req)

        assert response.status_code == 400

    @patch('FeedbackHandler.psycopg2.connect')
    def test_database_connection_error(self, mock_connect, mock_request_full_feedback):
        """Test handling of database connection errors."""
        mock_connect.side_effect = Exception("Database connection failed")

        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_request_full_feedback)

        assert response.status_code == 500
        assert "Failed to update feedback" in response.get_body().decode()

    @patch('FeedbackHandler.psycopg2.connect')
    def test_database_update_error(self, mock_connect, mock_request_full_feedback):
        """Test handling of database update errors."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Update failed")

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_request_full_feedback)

        assert response.status_code == 500

    @patch('FeedbackHandler.psycopg2.connect')
    def test_commit_error(self, mock_connect, mock_request_full_feedback):
        """Test handling of database commit errors."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.commit.side_effect = Exception("Commit failed")

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_request_full_feedback)

        assert response.status_code == 500

    @patch('FeedbackHandler.psycopg2.connect')
    def test_feedback_with_only_text(self, mock_connect):
        """Test feedback update with feedback_text but no feedback_type."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_req = Mock()
        mock_req.get_json.return_value = {
            'sessionid': 'session-123',
            'message_uuid': 'msg-456',
            'feedback': 'positive',
            'feedback_text': 'Great answer!'
        }

        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_req)

        assert response.status_code == 200

        # Verify query includes feedback_text but not feedback_type
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]

        assert "feedback_text = %s" in query
        assert "feedback_type" not in query

    @patch('FeedbackHandler.psycopg2.connect')
    def test_feedback_with_only_type(self, mock_connect):
        """Test feedback update with feedback_type but no feedback_text."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_req = Mock()
        mock_req.get_json.return_value = {
            'sessionid': 'session-123',
            'message_uuid': 'msg-456',
            'feedback': 'negative',
            'feedback_type': 'thumbs_down'
        }

        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_req)

        assert response.status_code == 200

        # Verify query includes feedback_type but not feedback_text
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]

        assert "feedback_type = %s" in query
        assert "feedback_text" not in query

    @patch('FeedbackHandler.psycopg2.connect')
    def test_sql_injection_prevention(self, mock_connect):
        """Test that SQL injection is prevented through parameterized queries."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Request with potential SQL injection
        mock_req = Mock()
        mock_req.get_json.return_value = {
            'sessionid': "session-123'; DROP TABLE chat_logs; --",
            'message_uuid': 'msg-456',
            'feedback': 'positive'
        }

        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_req)

        # Should succeed with parameterized query
        assert response.status_code == 200

        # Verify parameterized query was used
        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]

        assert params[1] == "session-123'; DROP TABLE chat_logs; --"

    @patch('FeedbackHandler.psycopg2.connect')
    def test_special_characters_in_feedback(self, mock_connect):
        """Test feedback with special characters."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_req = Mock()
        mock_req.get_json.return_value = {
            'sessionid': 'session-123',
            'message_uuid': 'msg-456',
            'feedback': 'positive',
            'feedback_text': "Great! It's working perfectly 👍 <script>alert('test')</script>"
        }

        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_req)

        assert response.status_code == 200

    @patch('FeedbackHandler.psycopg2.connect')
    def test_empty_feedback_text(self, mock_connect):
        """Test feedback with empty feedback_text."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_req = Mock()
        mock_req.get_json.return_value = {
            'sessionid': 'session-123',
            'message_uuid': 'msg-456',
            'feedback': 'positive',
            'feedback_text': ''
        }

        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_req)

        assert response.status_code == 200

    @patch('FeedbackHandler.psycopg2.connect')
    def test_negative_feedback(self, mock_connect):
        """Test negative feedback submission."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_req = Mock()
        mock_req.get_json.return_value = {
            'sessionid': 'session-123',
            'message_uuid': 'msg-456',
            'feedback': 'negative',
            'feedback_text': 'Not accurate',
            'feedback_type': 'thumbs_down'
        }

        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_req)

        assert response.status_code == 200

        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]
        assert params[0] == 'negative'

    @patch('FeedbackHandler.get_db_connection')
    def test_get_db_connection_error_handling(self, mock_get_connection):
        """Test error handling in get_db_connection function."""
        mock_get_connection.side_effect = Exception("Connection timeout")

        from FeedbackHandler import FeedbackHandler

        mock_req = Mock()
        mock_req.get_json.return_value = {
            'sessionid': 'session-123',
            'message_uuid': 'msg-456',
            'feedback': 'positive'
        }

        response = FeedbackHandler(mock_req)

        assert response.status_code == 500

    @patch('FeedbackHandler.update_feedback')
    def test_update_feedback_returns_false(self, mock_update_feedback):
        """Test when update_feedback function returns False."""
        mock_update_feedback.return_value = False

        from FeedbackHandler import FeedbackHandler

        mock_req = Mock()
        mock_req.get_json.return_value = {
            'sessionid': 'session-123',
            'message_uuid': 'msg-456',
            'feedback': 'positive'
        }

        response = FeedbackHandler(mock_req)

        assert response.status_code == 500
        assert "Failed to update feedback" in response.get_body().decode()

    @patch('FeedbackHandler.psycopg2.connect')
    def test_long_feedback_text(self, mock_connect):
        """Test feedback with very long feedback_text."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        long_text = "This is a very detailed feedback. " * 100  # ~3500 characters

        mock_req = Mock()
        mock_req.get_json.return_value = {
            'sessionid': 'session-123',
            'message_uuid': 'msg-456',
            'feedback': 'positive',
            'feedback_text': long_text
        }

        from FeedbackHandler import FeedbackHandler

        response = FeedbackHandler(mock_req)

        assert response.status_code == 200
