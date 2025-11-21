"""
Unit tests for ChatTransactionHandler Azure Function.
Tests orchestration of chat queries, document uploads, and API calls.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the function path to sys.path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                '../../azure-deployment/functions/ChatTransactionHandler'))


@pytest.mark.unit
@pytest.mark.api
class TestChatTransactionHandler:
    """Test suite for ChatTransactionHandler function."""

    @pytest.fixture
    def mock_request_new_chat(self):
        """Mock HTTP request for new chat session."""
        mock_req = Mock()
        mock_req.get_body.return_value = b'{}'
        mock_req.get_json.return_value = {
            'email': 'test@example.com',
            'query': 'What is Azure?',
            'sessionid': None,
            'document_uploaded': False
        }
        return mock_req

    @pytest.fixture
    def mock_request_followup_chat(self):
        """Mock HTTP request for followup chat."""
        mock_req = Mock()
        mock_req.get_body.return_value = b'{}'
        mock_req.get_json.return_value = {
            'email': 'test@example.com',
            'query': 'Tell me more',
            'sessionid': 'session-123',
            'document_uploaded': False
        }
        return mock_req

    @pytest.fixture
    def mock_request_with_document(self):
        """Mock HTTP request with document upload."""
        mock_req = Mock()
        mock_req.get_body.return_value = b'{}'
        mock_req.get_json.return_value = {
            'email': 'test@example.com',
            'query': 'Analyze this document',
            'sessionid': None,
            'document_uploaded': True,
            'file_content': 'base64encodedcontent',
            'file_type': 'pdf'
        }
        return mock_req

    @pytest.fixture
    def mock_request_no_body(self):
        """Mock HTTP request with no body."""
        mock_req = Mock()
        mock_req.get_body.return_value = None
        return mock_req

    @pytest.fixture
    def mock_assistant_response(self):
        """Mock response from ChatAssistantHandler."""
        return {
            'message_uuid': 'msg-123',
            'content': 'Azure is Microsoft cloud platform [doc1] and [doc2].',
            'sources': [
                {'title': 'azure-intro.pdf'},
                {'title': 'cloud-guide.pdf'}
            ]
        }

    @pytest.fixture
    def mock_followup_data(self):
        """Mock response from Chat_Retrieve_function."""
        return {
            'body': [
                {'Input_query': 'Hello', 'output': 'Hi there!'},
                {'Input_query': 'What is cloud?', 'output': 'Cloud is...'},
                {'Input_query': 'Tell me more', 'output': 'More details...'}
            ]
        }

    @patch('ChatTransactionHandler.requests.post')
    def test_successful_new_chat(self, mock_post, mock_request_new_chat, mock_assistant_response):
        """Test successful handling of new chat session."""
        # Mock requests.post calls
        mock_responses = []

        # Assistant response
        assistant_mock = Mock()
        assistant_mock.json.return_value = mock_assistant_response
        mock_responses.append(assistant_mock)

        # UpdateChatlogsDB response
        db_mock = Mock()
        db_mock.status_code = 200
        mock_responses.append(db_mock)

        mock_post.side_effect = mock_responses

        from ChatTransactionHandler import ChatTransactionHandler

        with patch('ChatTransactionHandler.update_dict_with_sharepoint_url', return_value=[]):
            with patch('ChatTransactionHandler.replace_references_with_links', return_value='Processed text'):
                response = ChatTransactionHandler(mock_request_new_chat)

        assert response.status_code == 200
        response_data = json.loads(response.get_body())

        assert 'message_uuid' in response_data
        assert 'sessionid' in response_data
        assert response_data['email'] == 'test@example.com'
        assert response_data['input_query'] == 'What is Azure?'

        # Verify assistant was called
        assert mock_post.call_count == 2  # Assistant + UpdateDB

    @patch('ChatTransactionHandler.requests.post')
    def test_followup_chat_with_history(self, mock_post, mock_request_followup_chat,
                                       mock_assistant_response, mock_followup_data):
        """Test followup chat with history retrieval."""
        mock_responses = []

        # Chat retrieve response
        retrieve_mock = Mock()
        retrieve_mock.json.return_value = mock_followup_data
        mock_responses.append(retrieve_mock)

        # Assistant response
        assistant_mock = Mock()
        assistant_mock.json.return_value = mock_assistant_response
        mock_responses.append(assistant_mock)

        # UpdateChatlogsDB response
        db_mock = Mock()
        db_mock.status_code = 200
        mock_responses.append(db_mock)

        mock_post.side_effect = mock_responses

        from ChatTransactionHandler import ChatTransactionHandler

        with patch('ChatTransactionHandler.update_dict_with_sharepoint_url', return_value=[]):
            with patch('ChatTransactionHandler.replace_references_with_links', return_value='Processed text'):
                response = ChatTransactionHandler(mock_request_followup_chat)

        assert response.status_code == 200
        response_data = json.loads(response.get_body())
        assert response_data['sessionid'] == 'session-123'

        # Verify all services were called
        assert mock_post.call_count == 3  # Retrieve + Assistant + UpdateDB

    @patch('ChatTransactionHandler.requests.post')
    def test_chat_with_document_upload(self, mock_post, mock_request_with_document, mock_assistant_response):
        """Test chat with document upload."""
        mock_responses = []

        # ReadUploadDoc response
        doc_mock = Mock()
        doc_mock.json.return_value = {'Extracted Text': 'This is extracted document content'}
        mock_responses.append(doc_mock)

        # Assistant response
        assistant_mock = Mock()
        assistant_response = mock_assistant_response.copy()
        assistant_response['sources'] = []  # Documents have no sources
        assistant_mock.json.return_value = assistant_response
        mock_responses.append(assistant_mock)

        # UpdateChatlogsDB response
        db_mock = Mock()
        db_mock.status_code = 200
        mock_responses.append(db_mock)

        mock_post.side_effect = mock_responses

        from ChatTransactionHandler import ChatTransactionHandler

        response = ChatTransactionHandler(mock_request_with_document)

        assert response.status_code == 200
        response_data = json.loads(response.get_body())
        assert response_data['document_upload'] == True
        assert response_data['sources'] == []

    def test_missing_request_body(self, mock_request_no_body):
        """Test handling of missing request body."""
        from ChatTransactionHandler import ChatTransactionHandler

        response = ChatTransactionHandler(mock_request_no_body)

        assert response.status_code == 400
        assert "Bad Request" in response.get_body().decode()

    @patch('ChatTransactionHandler.requests.post')
    def test_assistant_api_error(self, mock_post, mock_request_new_chat):
        """Test handling of assistant API errors."""
        mock_post.side_effect = Exception("Assistant API error")

        from ChatTransactionHandler import ChatTransactionHandler

        response = ChatTransactionHandler(mock_request_new_chat)

        assert response.status_code == 500
        assert "error" in response.get_body().decode().lower()

    @patch('ChatTransactionHandler.requests.post')
    def test_no_information_found_response(self, mock_post, mock_request_new_chat):
        """Test handling when no information is found."""
        # Mock assistant response with no info message
        assistant_mock = Mock()
        assistant_mock.json.return_value = {
            'message_uuid': 'msg-123',
            'content': 'The requested information is not available in the retrieved data. Please try another query or topic.',
            'sources': []
        }

        db_mock = Mock()
        db_mock.status_code = 200

        mock_post.side_effect = [assistant_mock, db_mock]

        from ChatTransactionHandler import ChatTransactionHandler

        response = ChatTransactionHandler(mock_request_new_chat)

        assert response.status_code == 200
        response_data = json.loads(response.get_body())

        # Verify friendly message is returned
        assert "wasn't able to find" in response_data['output'] or "rephrase" in response_data['output']

    @patch('ChatTransactionHandler.requests.post')
    def test_followup_retrieval_error_fallback(self, mock_post, mock_request_followup_chat, mock_assistant_response):
        """Test fallback when followup retrieval fails."""
        mock_responses = []

        # Chat retrieve fails
        retrieve_mock = Mock()
        retrieve_mock.json.side_effect = Exception("Retrieve error")
        mock_responses.append(retrieve_mock)

        # But assistant still works
        assistant_mock = Mock()
        assistant_mock.json.return_value = mock_assistant_response
        mock_responses.append(assistant_mock)

        # UpdateChatlogsDB
        db_mock = Mock()
        db_mock.status_code = 200
        mock_responses.append(db_mock)

        mock_post.side_effect = mock_responses

        from ChatTransactionHandler import ChatTransactionHandler

        with patch('ChatTransactionHandler.update_dict_with_sharepoint_url', return_value=[]):
            with patch('ChatTransactionHandler.replace_references_with_links', return_value='text'):
                response = ChatTransactionHandler(mock_request_followup_chat)

        # Should generate new session_id and continue
        assert response.status_code == 200


@pytest.mark.unit
class TestChatTransactionHelperFunctions:
    """Test helper functions in ChatTransactionHandler."""

    def test_add_followup_queries(self):
        """Test add_followup_queries function."""
        from ChatTransactionHandler import add_followup_queries

        followup_data = {
            'body': [
                {'Input_query': 'Query 1', 'output': 'Output 1'},
                {'Input_query': 'Query 2', 'output': 'Output 2'},
                {'Input_query': 'Query 3', 'output': 'Output 3'}
            ]
        }

        result = add_followup_queries(followup_data, 'New query', prev_chat_count=2)

        assert 'Query 2' in result
        assert 'Query 3' in result
        assert 'Output 2' in result
        assert 'Output 3' in result
        assert 'New query' in result
        assert 'History chat' in result

    def test_add_followup_queries_empty_data(self):
        """Test add_followup_queries with empty data."""
        from ChatTransactionHandler import add_followup_queries

        followup_data = {'body': []}

        result = add_followup_queries(followup_data, 'New query', prev_chat_count=2)

        # Should handle gracefully
        assert result is None or 'New query' in str(result)

    @patch('ChatTransactionHandler.requests.post')
    def test_add_doc_content(self, mock_post):
        """Test add_doc_content function."""
        from ChatTransactionHandler import add_doc_content

        # Mock ReadUploadDoc response
        doc_mock = Mock()
        doc_mock.json.return_value = {'Extracted Text': 'Document content here'}
        mock_post.return_value = doc_mock

        result = add_doc_content('base64content', 'pdf', 'Analyze this')

        assert 'Document content here' in result
        assert 'Analyze this' in result
        assert 'Document text:' in result

    @patch('ChatTransactionHandler.psycopg2.connect')
    def test_fetch_sharepoint_url_from_postgresql(self, mock_connect):
        """Test fetch_sharepoint_url_from_postgresql function."""
        from ChatTransactionHandler import fetch_sharepoint_url_from_postgresql

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('https://sharepoint.com/doc.pdf',)

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = fetch_sharepoint_url_from_postgresql('test-doc.pdf')

        assert result == 'https://sharepoint.com/doc.pdf'
        mock_cursor.execute.assert_called_once()

    @patch('ChatTransactionHandler.psycopg2.connect')
    def test_fetch_sharepoint_url_not_found(self, mock_connect):
        """Test fetch_sharepoint_url when URL not found."""
        from ChatTransactionHandler import fetch_sharepoint_url_from_postgresql

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = fetch_sharepoint_url_from_postgresql('nonexistent.pdf')

        assert result is None

    @patch('ChatTransactionHandler.fetch_sharepoint_url_from_postgresql')
    def test_update_dict_with_sharepoint_url(self, mock_fetch):
        """Test update_dict_with_sharepoint_url function."""
        from ChatTransactionHandler import update_dict_with_sharepoint_url

        mock_fetch.side_effect = lambda title: f'https://sharepoint.com/{title}'

        data = [
            {'title': 'doc1.pdf'},
            {'title': 'doc2.pdf'}
        ]

        result = update_dict_with_sharepoint_url(data)

        assert result[0]['url'] == 'https://sharepoint.com/doc1.pdf'
        assert result[1]['url'] == 'https://sharepoint.com/doc2.pdf'
        assert 'title' in result[0]  # Title is kept

    def test_replace_references_with_links(self):
        """Test replace_references_with_links function."""
        from ChatTransactionHandler import replace_references_with_links

        text = "Azure is great [doc1] and also [doc2] has info."
        sources = [
            {'url': 'https://example.com/doc1.pdf'},
            {'url': 'https://example.com/doc2.pdf'}
        ]

        result = replace_references_with_links(text, sources)

        assert '[Source](https://example.com/doc1.pdf)' in result
        assert '[Source](https://example.com/doc2.pdf)' in result
        assert '[doc1]' not in result
        assert '[doc2]' not in result

    def test_replace_references_with_links_no_url(self):
        """Test replace_references_with_links when source has no URL."""
        from ChatTransactionHandler import replace_references_with_links

        text = "Info here [doc1] and [doc2]."
        sources = [
            {'url': 'https://example.com/doc1.pdf'}
            # doc2 missing
        ]

        result = replace_references_with_links(text, sources)

        assert '[Source](https://example.com/doc1.pdf)' in result
        # [doc2] should be removed (empty string replacement)
        assert '[doc2]' not in result

    def test_replace_references_multiple_occurrences(self):
        """Test replace_references_with_links with multiple occurrences."""
        from ChatTransactionHandler import replace_references_with_links

        text = "First [doc1], then [doc1] again, and [doc2]."
        sources = [
            {'url': 'https://example.com/doc1.pdf'},
            {'url': 'https://example.com/doc2.pdf'}
        ]

        result = replace_references_with_links(text, sources)

        # Both [doc1] occurrences should be replaced
        assert result.count('[Source](https://example.com/doc1.pdf)') == 2
        assert result.count('[Source](https://example.com/doc2.pdf)') == 1

    @patch('ChatTransactionHandler.psycopg2.connect')
    def test_get_value_by_session_id(self, mock_connect):
        """Test get_value_by_session_id function."""
        from ChatTransactionHandler import get_value_by_session_id

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('uuid', 'timestamp', 'summary', None, True, 'test@example.com',
             None, None, None, 'query', 'output', 'processed', 'session-123',
             '[]', 'file_content', 'pdf')
        ]

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = get_value_by_session_id('session-123')

        assert len(result) == 1
        assert result[0][14] == 'file_content'
        assert result[0][15] == 'pdf'

    @patch('ChatTransactionHandler.psycopg2.connect')
    def test_get_value_by_session_id_not_found(self, mock_connect):
        """Test get_value_by_session_id when session not found."""
        from ChatTransactionHandler import get_value_by_session_id

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = get_value_by_session_id('nonexistent-session')

        assert result == []

    @patch('ChatTransactionHandler.get_value_by_session_id')
    @patch('ChatTransactionHandler.add_doc_content')
    def test_add_doc_content_followup(self, mock_add_doc, mock_get_value):
        """Test add_doc_content_followup function."""
        from ChatTransactionHandler import add_doc_content_followup

        # Mock session data
        mock_get_value.return_value = [
            (None, None, None, None, None, None, None, None, None, None,
             None, None, None, None, 'base64content', 'pdf')
        ]

        mock_add_doc.return_value = 'Processed query with doc'

        result = add_doc_content_followup('session-123', 'Follow up query')

        assert result == 'Processed query with doc'
        mock_add_doc.assert_called_once_with('base64content', 'pdf', 'Follow up query')

    @patch('ChatTransactionHandler.psycopg2.connect')
    def test_get_db_connection_success(self, mock_connect):
        """Test get_db_connection successful connection."""
        from ChatTransactionHandler import get_db_connection

        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        result = get_db_connection()

        assert result == mock_conn

    @patch('ChatTransactionHandler.psycopg2.connect')
    def test_get_db_connection_error(self, mock_connect):
        """Test get_db_connection error handling."""
        from ChatTransactionHandler import get_db_connection

        mock_connect.side_effect = Exception("Connection failed")

        with pytest.raises(Exception):
            get_db_connection()
