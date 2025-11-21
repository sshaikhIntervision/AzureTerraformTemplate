"""
Unit tests for ChatAssistantHandler Azure Function.
Tests Azure OpenAI integration and query handling.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the function path to sys.path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                '../../azure-deployment/functions/ChatAssistantHandler'))


@pytest.mark.unit
@pytest.mark.api
class TestChatAssistantHandler:
    """Test suite for ChatAssistantHandler function."""

    @pytest.fixture
    def mock_request_with_query_param(self):
        """Mock HTTP request with query in URL params."""
        mock_req = Mock()
        mock_req.params.get.return_value = 'What is Azure?'
        return mock_req

    @pytest.fixture
    def mock_request_with_body(self):
        """Mock HTTP request with query in body."""
        mock_req = Mock()
        mock_req.params.get.return_value = None
        mock_req.get_json.return_value = {'query': 'What is construction safety?'}
        return mock_req

    @pytest.fixture
    def mock_request_no_query(self):
        """Mock HTTP request with no query."""
        mock_req = Mock()
        mock_req.params.get.return_value = None
        mock_req.get_json.return_value = {}
        return mock_req

    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI API response."""
        return {
            "id": "msg-12345",
            "choices": [
                {
                    "message": {
                        "content": "Azure is Microsoft's cloud computing platform.",
                        "context": {
                            "citations": [
                                {
                                    "content": "Azure provides cloud services...",
                                    "title": "azure-intro.pdf",
                                    "url": "https://example.com/azure-intro.pdf"
                                },
                                {
                                    "content": "Cloud computing basics...",
                                    "title": "cloud-guide.pdf",
                                    "url": "https://example.com/cloud-guide.pdf"
                                }
                            ]
                        }
                    }
                }
            ]
        }

    @pytest.fixture
    def mock_openai_response_no_citations(self):
        """Mock OpenAI response with no citations."""
        return {
            "id": "msg-12345",
            "choices": [
                {
                    "message": {
                        "content": "I don't have information about that.",
                        "context": {
                            "citations": []
                        }
                    }
                }
            ]
        }

    @patch('ChatAssistantHandler.query_construction_bot')
    def test_successful_query_from_params(self, mock_query_bot, mock_request_with_query_param, mock_openai_response):
        """Test successful query processing from URL parameters."""
        mock_query_bot.return_value = json.dumps(mock_openai_response)

        from ChatAssistantHandler import ChatAssistant

        response = ChatAssistant(mock_request_with_query_param)

        assert response.status_code == 200
        assert response.mimetype == "application/json"

        response_data = json.loads(response.get_body())
        assert 'message_uuid' in response_data
        assert response_data['message_uuid'] == 'msg-12345'
        assert 'content' in response_data
        assert 'sources' in response_data
        assert len(response_data['sources']) == 2

        # Verify query_bot was called with correct query
        mock_query_bot.assert_called_once_with('What is Azure?')

    @patch('ChatAssistantHandler.query_construction_bot')
    def test_successful_query_from_body(self, mock_query_bot, mock_request_with_body, mock_openai_response):
        """Test successful query processing from request body."""
        mock_query_bot.return_value = json.dumps(mock_openai_response)

        from ChatAssistantHandler import ChatAssistant

        response = ChatAssistant(mock_request_with_body)

        assert response.status_code == 200
        response_data = json.loads(response.get_body())
        assert response_data['content'] == "Azure is Microsoft's cloud computing platform."

        mock_query_bot.assert_called_once_with('What is construction safety?')

    @patch('ChatAssistantHandler.query_construction_bot')
    def test_response_with_no_citations(self, mock_query_bot, mock_request_with_query_param, mock_openai_response_no_citations):
        """Test response when no citations are found."""
        mock_query_bot.return_value = json.dumps(mock_openai_response_no_citations)

        from ChatAssistantHandler import ChatAssistant

        response = ChatAssistant(mock_request_with_query_param)

        assert response.status_code == 200
        response_data = json.loads(response.get_body())
        assert response_data['sources'] == []
        assert response_data['content'] == "I don't have information about that."

    @patch('ChatAssistantHandler.query_construction_bot')
    def test_citations_formatting(self, mock_query_bot, mock_request_with_query_param, mock_openai_response):
        """Test that citations are properly formatted in response."""
        mock_query_bot.return_value = json.dumps(mock_openai_response)

        from ChatAssistantHandler import ChatAssistant

        response = ChatAssistant(mock_request_with_query_param)

        response_data = json.loads(response.get_body())
        sources = response_data['sources']

        assert sources[0]['title'] == 'azure-intro.pdf'
        assert sources[0]['url'] == 'https://example.com/azure-intro.pdf'
        assert 'content' in sources[0]

        assert sources[1]['title'] == 'cloud-guide.pdf'
        assert sources[1]['url'] == 'https://example.com/cloud-guide.pdf'

    @patch('ChatAssistantHandler.query_construction_bot')
    def test_openai_api_error(self, mock_query_bot, mock_request_with_query_param):
        """Test handling of OpenAI API errors."""
        mock_query_bot.side_effect = Exception("OpenAI API error")

        from ChatAssistantHandler import ChatAssistant

        with pytest.raises(Exception):
            ChatAssistant(mock_request_with_query_param)

    @patch('ChatAssistantHandler.query_construction_bot')
    def test_invalid_json_response(self, mock_query_bot, mock_request_with_query_param):
        """Test handling of invalid JSON from query_construction_bot."""
        mock_query_bot.return_value = "Invalid JSON{{"

        from ChatAssistantHandler import ChatAssistant

        with pytest.raises(json.JSONDecodeError):
            ChatAssistant(mock_request_with_query_param)

    def test_no_query_provided_with_invalid_json_body(self):
        """Test handling when no query is provided and body has invalid JSON."""
        mock_req = Mock()
        mock_req.params.get.return_value = None
        mock_req.get_json.side_effect = ValueError("Invalid JSON")

        from ChatAssistantHandler import ChatAssistant

        # Should handle ValueError and continue (query remains None)
        # This will likely cause issues downstream but tests error handling
        with pytest.raises(Exception):  # Will fail when trying to process None query
            ChatAssistant(mock_req)

    @patch('ChatAssistantHandler.query_construction_bot')
    def test_long_query(self, mock_query_bot, mock_openai_response):
        """Test handling of very long queries."""
        long_query = "What is construction safety? " * 100  # Very long query

        mock_req = Mock()
        mock_req.params.get.return_value = None
        mock_req.get_json.return_value = {'query': long_query}

        mock_query_bot.return_value = json.dumps(mock_openai_response)

        from ChatAssistantHandler import ChatAssistant

        response = ChatAssistant(mock_req)

        assert response.status_code == 200
        mock_query_bot.assert_called_once_with(long_query)

    @patch('ChatAssistantHandler.query_construction_bot')
    def test_special_characters_in_query(self, mock_query_bot, mock_openai_response):
        """Test handling of special characters in query."""
        special_query = "What is <script>alert('test')</script> & safety?"

        mock_req = Mock()
        mock_req.params.get.return_value = special_query

        mock_query_bot.return_value = json.dumps(mock_openai_response)

        from ChatAssistantHandler import ChatAssistant

        response = ChatAssistant(mock_req)

        assert response.status_code == 200
        mock_query_bot.assert_called_once_with(special_query)

    @patch('ChatAssistantHandler.query_construction_bot')
    def test_unicode_in_query(self, mock_query_bot, mock_openai_response):
        """Test handling of unicode characters in query."""
        unicode_query = "你好 مرحبا Hello 🎉"

        mock_req = Mock()
        mock_req.params.get.return_value = unicode_query

        mock_query_bot.return_value = json.dumps(mock_openai_response)

        from ChatAssistantHandler import ChatAssistant

        response = ChatAssistant(mock_req)

        assert response.status_code == 200


@pytest.mark.unit
class TestQueryConstructionBot:
    """Test query_construction_bot function."""

    @patch('ChatAssistantHandler.AzureOpenAI')
    def test_query_construction_bot_success(self, mock_azure_openai):
        """Test successful query to OpenAI."""
        # Mock the client and completion
        mock_client = MagicMock()
        mock_completion = MagicMock()

        # Mock the model_dump_json method
        mock_response_json = json.dumps({
            "id": "msg-123",
            "choices": [{
                "message": {
                    "content": "Test response",
                    "context": {"citations": []}
                }
            }]
        })
        mock_completion.model_dump_json.return_value = mock_response_json

        mock_client.chat.completions.create.return_value = mock_completion
        mock_azure_openai.return_value = mock_client

        from ChatAssistantHandler import query_construction_bot

        result = query_construction_bot("What is Azure?")

        assert isinstance(result, str)
        response_data = json.loads(result)
        assert 'id' in response_data
        assert 'choices' in response_data

        # Verify AzureOpenAI client was called correctly
        mock_azure_openai.assert_called_once()
        mock_client.chat.completions.create.assert_called_once()

    @patch('ChatAssistantHandler.AzureOpenAI')
    def test_query_construction_bot_with_data_sources(self, mock_azure_openai):
        """Test that Azure Search data sources are properly configured."""
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.model_dump_json.return_value = '{"id": "test"}'

        mock_client.chat.completions.create.return_value = mock_completion
        mock_azure_openai.return_value = mock_client

        from ChatAssistantHandler import query_construction_bot

        with patch.dict(os.environ, {
            'AZURE_SEARCH_ENDPOINT': 'https://test-search.search.windows.net',
            'AZURE_SEARCH_INDEX': 'test-index',
            'AZURE_SEARCH_API_KEY': 'test-key',
            'AZURE_OPENAI_ENDPOINT': 'https://test-openai.openai.azure.com',
            'AZURE_OPENAI_API_KEY': 'test-openai-key',
            'DEPLOYMENT': 'gpt-4',
            'OPENAI_API_VERSION': '2024-02-15-preview'
        }):
            query_construction_bot("Test query")

        # Verify extra_body with data_sources was passed
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert 'extra_body' in call_kwargs
        assert 'data_sources' in call_kwargs['extra_body']
        assert call_kwargs['extra_body']['data_sources'][0]['type'] == 'azure_search'

    @patch('ChatAssistantHandler.AzureOpenAI')
    def test_query_construction_bot_system_prompt(self, mock_azure_openai):
        """Test that system prompt is included in messages."""
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.model_dump_json.return_value = '{"id": "test"}'

        mock_client.chat.completions.create.return_value = mock_completion
        mock_azure_openai.return_value = mock_client

        from ChatAssistantHandler import query_construction_bot

        query_construction_bot("Test query")

        # Verify messages structure
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs['messages']

        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert 'construction' in messages[0]['content'].lower()
        assert messages[1]['role'] == 'user'
        assert messages[1]['content'] == 'Test query'

    @patch('ChatAssistantHandler.AzureOpenAI')
    def test_query_construction_bot_api_error(self, mock_azure_openai):
        """Test handling of OpenAI API errors."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        mock_azure_openai.return_value = mock_client

        from ChatAssistantHandler import query_construction_bot

        with pytest.raises(Exception):
            query_construction_bot("Test query")

    @patch('ChatAssistantHandler.AzureOpenAI')
    def test_query_construction_bot_authentication(self, mock_azure_openai):
        """Test that API authentication is properly configured."""
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.model_dump_json.return_value = '{"id": "test"}'

        mock_client.chat.completions.create.return_value = mock_completion
        mock_azure_openai.return_value = mock_client

        from ChatAssistantHandler import query_construction_bot

        with patch.dict(os.environ, {
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com',
            'AZURE_OPENAI_API_KEY': 'test-key-12345',
            'OPENAI_API_VERSION': '2024-02-15-preview',
            'DEPLOYMENT': 'gpt-4'
        }):
            query_construction_bot("Test")

        # Verify client was initialized with correct credentials
        call_args = mock_azure_openai.call_args[1]
        assert call_args['azure_endpoint'] == 'https://test.openai.azure.com'
        assert call_args['api_key'] == 'test-key-12345'
        assert call_args['api_version'] == '2024-02-15-preview'

    @patch('ChatAssistantHandler.AzureOpenAI')
    def test_query_construction_bot_empty_query(self, mock_azure_openai):
        """Test handling of empty query."""
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.model_dump_json.return_value = '{"id": "test"}'

        mock_client.chat.completions.create.return_value = mock_completion
        mock_azure_openai.return_value = mock_client

        from ChatAssistantHandler import query_construction_bot

        result = query_construction_bot("")

        # Should still process empty query
        assert isinstance(result, str)

    @patch('ChatAssistantHandler.AzureOpenAI')
    def test_query_construction_bot_model_deployment(self, mock_azure_openai):
        """Test that correct model deployment is used."""
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.model_dump_json.return_value = '{"id": "test"}'

        mock_client.chat.completions.create.return_value = mock_completion
        mock_azure_openai.return_value = mock_client

        from ChatAssistantHandler import query_construction_bot

        with patch.dict(os.environ, {'DEPLOYMENT': 'gpt-4-turbo'}):
            query_construction_bot("Test")

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs['model'] == 'gpt-4-turbo'
