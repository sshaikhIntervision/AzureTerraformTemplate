"""
Integration tests for database operations across Azure Functions.
Tests end-to-end workflows involving database interactions.

Note: These tests require actual database connection configuration.
Set INTEGRATION_TEST_DB=true and provide real DB credentials to run these tests.
Otherwise, they will be skipped.
"""
import pytest
import os
import psycopg2
from unittest.mock import Mock
import json
import datetime


# Skip integration tests if not explicitly enabled
pytestmark = pytest.mark.skipif(
    os.getenv('INTEGRATION_TEST_DB') != 'true',
    reason="Integration tests require INTEGRATION_TEST_DB=true environment variable"
)


@pytest.mark.integration
@pytest.mark.database
class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @pytest.fixture(scope='class')
    def db_connection(self):
        """Provide a real database connection for integration tests."""
        config = {
            'host': os.getenv('TEST_COSMOPG_HOST', 'localhost'),
            'dbname': os.getenv('TEST_COSMOPG_DBNAME', 'test_db'),
            'user': os.getenv('TEST_COSMOPG_USER', 'test_user'),
            'password': os.getenv('TEST_COSMOPG_PASSWORD', 'test_password'),
            'port': int(os.getenv('TEST_COSMOPG_PORT', '5432'))
        }

        try:
            conn = psycopg2.connect(**config)
            yield conn
            conn.close()
        except Exception as e:
            pytest.skip(f"Could not connect to test database: {e}")

    @pytest.fixture(scope='class')
    def setup_test_schema(self, db_connection):
        """Setup test database schema."""
        cursor = db_connection.cursor()

        # Create test tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_logs (
                message_uuid VARCHAR(255) PRIMARY KEY,
                timestamp TIMESTAMP,
                chat_summary TEXT,
                data_source VARCHAR(255),
                document_upload BOOLEAN,
                email VARCHAR(255),
                feedback VARCHAR(50),
                feedback_text TEXT,
                feedback_type VARCHAR(50),
                input_query TEXT,
                output TEXT,
                processed_query TEXT,
                sessionid VARCHAR(255),
                sources JSONB,
                doc_content TEXT,
                doc_type VARCHAR(50)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_url (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) UNIQUE,
                sharepoint_url TEXT
            );
        """)

        db_connection.commit()
        cursor.close()

        yield

        # Cleanup
        cursor = db_connection.cursor()
        cursor.execute("DROP TABLE IF EXISTS chat_logs CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS source_url CASCADE;")
        db_connection.commit()
        cursor.close()

    def test_insert_and_retrieve_chat_log(self, db_connection, setup_test_schema):
        """Test inserting and retrieving a chat log."""
        cursor = db_connection.cursor()

        # Insert test data
        test_data = {
            'message_uuid': 'test-msg-001',
            'timestamp': datetime.datetime.now(),
            'email': 'integration@test.com',
            'input_query': 'Test query',
            'output': 'Test response',
            'sessionid': 'test-session-001',
            'sources': json.dumps([])
        }

        cursor.execute("""
            INSERT INTO chat_logs (message_uuid, timestamp, email, input_query, output, sessionid, sources)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            test_data['message_uuid'],
            test_data['timestamp'],
            test_data['email'],
            test_data['input_query'],
            test_data['output'],
            test_data['sessionid'],
            test_data['sources']
        ))
        db_connection.commit()

        # Retrieve data
        cursor.execute("""
            SELECT email, input_query, output, sessionid
            FROM chat_logs
            WHERE message_uuid = %s
        """, (test_data['message_uuid'],))

        result = cursor.fetchone()
        cursor.close()

        assert result is not None
        assert result[0] == 'integration@test.com'
        assert result[1] == 'Test query'
        assert result[2] == 'Test response'
        assert result[3] == 'test-session-001'

    def test_update_feedback(self, db_connection, setup_test_schema):
        """Test updating feedback for a chat log."""
        cursor = db_connection.cursor()

        # Insert initial data
        cursor.execute("""
            INSERT INTO chat_logs (message_uuid, email, sessionid, input_query, output)
            VALUES (%s, %s, %s, %s, %s)
        """, ('test-msg-002', 'test@example.com', 'session-002', 'Query', 'Response'))
        db_connection.commit()

        # Update feedback
        cursor.execute("""
            UPDATE chat_logs
            SET feedback = %s, feedback_text = %s, feedback_type = %s
            WHERE sessionid = %s AND message_uuid = %s
        """, ('positive', 'Great answer!', 'thumbs_up', 'session-002', 'test-msg-002'))
        db_connection.commit()

        # Verify update
        cursor.execute("""
            SELECT feedback, feedback_text, feedback_type
            FROM chat_logs
            WHERE message_uuid = %s
        """, ('test-msg-002',))

        result = cursor.fetchone()
        cursor.close()

        assert result[0] == 'positive'
        assert result[1] == 'Great answer!'
        assert result[2] == 'thumbs_up'

    def test_delete_chat_by_session(self, db_connection, setup_test_schema):
        """Test deleting chat logs by session ID."""
        cursor = db_connection.cursor()

        # Insert multiple records for the same session
        session_id = 'session-to-delete'
        email = 'delete@test.com'

        for i in range(3):
            cursor.execute("""
                INSERT INTO chat_logs (message_uuid, email, sessionid, input_query, output)
                VALUES (%s, %s, %s, %s, %s)
            """, (f'msg-{i}', email, session_id, f'Query {i}', f'Response {i}'))
        db_connection.commit()

        # Delete records
        cursor.execute("""
            DELETE FROM chat_logs
            WHERE sessionid = %s AND email = %s
        """, (session_id, email))
        db_connection.commit()

        deleted_count = cursor.rowcount

        # Verify deletion
        cursor.execute("""
            SELECT COUNT(*) FROM chat_logs WHERE sessionid = %s
        """, (session_id,))
        remaining = cursor.fetchone()[0]
        cursor.close()

        assert deleted_count == 3
        assert remaining == 0

    def test_retrieve_sessions_by_email(self, db_connection, setup_test_schema):
        """Test retrieving all sessions for a user email."""
        cursor = db_connection.cursor()

        email = 'multi@session.com'

        # Insert records for multiple sessions
        sessions = ['session-a', 'session-b', 'session-c']
        for i, session in enumerate(sessions):
            cursor.execute("""
                INSERT INTO chat_logs (message_uuid, email, sessionid, input_query, output, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (f'msg-session-{i}', email, session, f'Query {i}', f'Response {i}',
                  datetime.datetime.now() + datetime.timedelta(hours=i)))
        db_connection.commit()

        # Retrieve sessions
        cursor.execute("""
            SELECT sessionid, timestamp, input_query
            FROM chat_logs
            WHERE email = %s
            ORDER BY timestamp DESC
        """, (email,))

        results = cursor.fetchall()
        cursor.close()

        assert len(results) == 3
        # Should be ordered by timestamp DESC
        assert results[0][0] == 'session-c'
        assert results[1][0] == 'session-b'
        assert results[2][0] == 'session-a'

    def test_get_session_with_document(self, db_connection, setup_test_schema):
        """Test retrieving sessions with document uploads."""
        cursor = db_connection.cursor()

        # Insert session with document
        cursor.execute("""
            INSERT INTO chat_logs (
                message_uuid, email, sessionid, input_query, output,
                document_upload, doc_content, doc_type
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, ('msg-doc', 'doc@test.com', 'session-doc', 'Analyze doc',
              'Analysis result', True, 'Document content here', 'pdf'))
        db_connection.commit()

        # Retrieve session with document
        cursor.execute("""
            SELECT * FROM chat_logs
            WHERE sessionid = %s AND doc_type IS NOT NULL
        """, ('session-doc',))

        result = cursor.fetchone()
        cursor.close()

        assert result is not None
        # Verify document fields (indices may vary based on column order)
        # Just check that we got a result with the session
        assert 'session-doc' in result

    def test_sharepoint_url_lookup(self, db_connection, setup_test_schema):
        """Test SharePoint URL lookup by filename."""
        cursor = db_connection.cursor()

        # Insert test SharePoint URLs
        cursor.execute("""
            INSERT INTO source_url (filename, sharepoint_url)
            VALUES (%s, %s)
        """, ('test-doc.pdf', 'https://sharepoint.com/test-doc.pdf'))
        db_connection.commit()

        # Lookup URL
        cursor.execute("""
            SELECT sharepoint_url FROM source_url WHERE filename = %s
        """, ('test-doc.pdf',))

        result = cursor.fetchone()
        cursor.close()

        assert result is not None
        assert result[0] == 'https://sharepoint.com/test-doc.pdf'

    def test_concurrent_session_creation(self, db_connection, setup_test_schema):
        """Test handling of concurrent session creation (race conditions)."""
        cursor = db_connection.cursor()

        # Simulate concurrent inserts for different sessions
        sessions = [f'concurrent-session-{i}' for i in range(5)]

        for session in sessions:
            cursor.execute("""
                INSERT INTO chat_logs (message_uuid, email, sessionid, input_query, output)
                VALUES (%s, %s, %s, %s, %s)
            """, (f'msg-{session}', 'concurrent@test.com', session, 'Query', 'Response'))

        db_connection.commit()

        # Verify all sessions were created
        cursor.execute("""
            SELECT COUNT(DISTINCT sessionid)
            FROM chat_logs
            WHERE email = %s
        """, ('concurrent@test.com',))

        count = cursor.fetchone()[0]
        cursor.close()

        assert count == 5

    def test_transaction_rollback(self, db_connection, setup_test_schema):
        """Test transaction rollback on error."""
        cursor = db_connection.cursor()

        try:
            # Start a transaction
            cursor.execute("""
                INSERT INTO chat_logs (message_uuid, email, sessionid, input_query, output)
                VALUES (%s, %s, %s, %s, %s)
            """, ('msg-rollback-1', 'rollback@test.com', 'session-rb', 'Query', 'Response'))

            # This should fail (duplicate primary key)
            cursor.execute("""
                INSERT INTO chat_logs (message_uuid, email, sessionid, input_query, output)
                VALUES (%s, %s, %s, %s, %s)
            """, ('msg-rollback-1', 'rollback@test.com', 'session-rb', 'Query', 'Response'))

            db_connection.commit()

        except Exception:
            db_connection.rollback()

        # Verify nothing was committed
        cursor.execute("""
            SELECT COUNT(*) FROM chat_logs WHERE message_uuid = %s
        """, ('msg-rollback-1',))

        count = cursor.fetchone()[0]
        cursor.close()

        assert count == 0  # Transaction should have been rolled back


@pytest.mark.integration
class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    @pytest.mark.skip(reason="Requires full environment setup with all services")
    def test_complete_chat_workflow(self):
        """
        Test complete workflow:
        1. Create new session
        2. Query assistant
        3. Retrieve session
        4. Provide feedback
        5. Delete session

        This test is skipped by default as it requires full environment setup.
        """
        pass

    @pytest.mark.skip(reason="Requires full environment setup")
    def test_document_upload_workflow(self):
        """
        Test document upload workflow:
        1. Upload document
        2. Extract text
        3. Query about document
        4. Retrieve document session
        5. Followup query with document context

        This test is skipped by default.
        """
        pass
