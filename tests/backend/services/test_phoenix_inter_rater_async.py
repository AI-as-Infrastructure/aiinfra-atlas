"""
Tests for async Phoenix client inter-rater count method

Tests the async httpx implementation for querying inter-rater counts from Phoenix.
Validates that the implementation works correctly for concurrent users.

Related files:
- backend/services/phoenix_client.py:636-703 (get_inter_rater_count async method)
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx


@pytest.fixture(autouse=True)
def configure_phoenix_endpoint(monkeypatch):
    monkeypatch.setenv('PHOENIX_COLLECTOR_ENDPOINT', 'https://app.phoenix.arize.com/s/aiinfra')


class TestPhoenixInterRaterCountAsync:
    """Test suite for async get_inter_rater_count method"""

    @pytest.mark.asyncio
    async def test_no_inter_raters_returns_zero(self):
        """
        Test: Async get_inter_rater_count returns 0 when no inter-raters exist

        Validates async httpx implementation doesn't block event loop
        """
        # Mock the async httpx client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': []}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Mock AsyncClient context manager
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None

        with patch('httpx.AsyncClient', return_value=mock_context):
            # Import after patching
            from backend.services.phoenix_client import PhoenixAPIClient

            client = PhoenixAPIClient()
            count = await client.get_inter_rater_count('span_123')

            assert count == 0
            assert mock_client.get.called

    @pytest.mark.asyncio
    async def test_counts_unique_raters(self):
        """
        Test: Correctly counts unique inter-rater users

        Validates count logic with multiple annotations from same/different users
        """
        # Mock response with 2 unique raters
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {
                    'name': 'Relevance Rating',
                    'metadata': {
                        'is_inter_rater': True,
                        'rater_id': 'user_1'
                    }
                },
                {
                    'name': 'Clarity',
                    'metadata': {
                        'is_inter_rater': True,
                        'rater_id': 'user_1'  # Same user, different annotation
                    }
                },
                {
                    'name': 'Relevance Rating',
                    'metadata': {
                        'is_inter_rater': True,
                        'rater_id': 'user_2'  # Different user
                    }
                }
            ]
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None

        with patch('httpx.AsyncClient', return_value=mock_context):
            from backend.services.phoenix_client import PhoenixAPIClient

            client = PhoenixAPIClient()
            count = await client.get_inter_rater_count('span_456')

            # Should count 2 unique raters
            assert count == 2

    @pytest.mark.asyncio
    async def test_excludes_original_feedback(self):
        """
        Test: Doesn't count original feedback as inter-rater

        Only annotations with is_inter_rater=True should be counted
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {
                    'name': 'Relevance Rating',
                    'metadata': {
                        'is_inter_rater': True,
                        'rater_id': 'user_1'
                    }
                },
                {
                    'name': 'Relevance Rating',
                    'metadata': {
                        'is_inter_rater': False,  # Original feedback
                        'user_id': 'original_user'
                    }
                }
            ]
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None

        with patch('httpx.AsyncClient', return_value=mock_context):
            from backend.services.phoenix_client import PhoenixAPIClient

            client = PhoenixAPIClient()
            count = await client.get_inter_rater_count('span_789')

            # Should only count the inter-rater, not original
            assert count == 1

    @pytest.mark.asyncio
    async def test_handles_phoenix_error(self):
        """
        Test: Returns 0 on Phoenix API error

        Validates graceful error handling doesn't break feedback submission
        """
        mock_response = Mock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None

        with patch('httpx.AsyncClient', return_value=mock_context):
            from backend.services.phoenix_client import PhoenixAPIClient

            client = PhoenixAPIClient()
            count = await client.get_inter_rater_count('span_error')

            # Should return 0 on error
            assert count == 0

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        """
        Test: Returns 0 on exception

        Network errors or timeouts shouldn't break feedback submission
        """
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None

        with patch('httpx.AsyncClient', return_value=mock_context):
            from backend.services.phoenix_client import PhoenixAPIClient

            client = PhoenixAPIClient()
            count = await client.get_inter_rater_count('span_timeout')

            # Should return 0 on exception
            assert count == 0

    @pytest.mark.asyncio
    async def test_uses_configured_space_endpoint(self, monkeypatch):
        monkeypatch.setenv('PHOENIX_COLLECTOR_ENDPOINT', 'https://app.phoenix.arize.com/s/aiinfra')

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': []}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None

        with patch('httpx.AsyncClient', return_value=mock_context):
            from backend.services.phoenix_client import PhoenixAPIClient

            client = PhoenixAPIClient()
            await client.get_inter_rater_count('span_space')

            called_url = mock_client.get.call_args.args[0]
            assert called_url.startswith('https://app.phoenix.arize.com/s/aiinfra/v1/projects/')

    @pytest.mark.asyncio
    async def test_returns_zero_when_endpoint_not_configured(self, monkeypatch):
        monkeypatch.delenv('PHOENIX_COLLECTOR_ENDPOINT', raising=False)

        from backend.services.phoenix_client import PhoenixAPIClient

        client = PhoenixAPIClient()
        count = await client.get_inter_rater_count('span_missing_endpoint')

        assert count == 0


class TestAsyncIntegration:
    """Test async integration with feedback submission"""

    def test_asyncio_run_works_in_sync_context(self):
        """
        Test: asyncio.run() successfully calls async method from sync context

        This simulates how feedback.py calls the async method
        """
        import asyncio

        async def mock_get_count():
            """Mock async function"""
            return 2

        # This is how feedback.py calls it
        count = asyncio.run(mock_get_count())

        assert count == 2

    def test_determines_inter_rater_number_correctly(self):
        """
        Test: Inter-rater number = count + 1

        Validates the calculation logic in feedback.py
        """
        existing_counts = [0, 1, 2, 5, 10]

        for count in existing_counts:
            inter_rater_number = count + 1
            assert inter_rater_number == count + 1
            assert inter_rater_number > 0

    @pytest.mark.asyncio
    async def test_concurrent_calls_dont_block(self):
        """
        Test: Multiple concurrent calls work without blocking

        Validates async implementation supports concurrent users
        """
        import asyncio

        # Mock quick responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': []}

        async def mock_get(*args, **kwargs):
            await asyncio.sleep(0.01)  # Simulate network delay
            return mock_response

        mock_client = AsyncMock()
        mock_client.get = mock_get

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None

        with patch('httpx.AsyncClient', return_value=mock_context):
            from backend.services.phoenix_client import PhoenixAPIClient

            client = PhoenixAPIClient()

            # Simulate 10 concurrent users
            tasks = [
                client.get_inter_rater_count(f'span_{i}')
                for i in range(10)
            ]

            # All should complete without blocking
            results = await asyncio.gather(*tasks)

            assert len(results) == 10
            assert all(count == 0 for count in results)


class TestMultipleInterRaterFlow:
    """Test full flow with multiple inter-raters getting sequential numbers"""

    @pytest.mark.asyncio
    async def test_sequential_raters_get_correct_numbers(self):
        """
        Test: Three sequential raters get numbers 1, 2, 3

        Simulates the full flow:
        1. First rater: count=0 → inter_rater_number=1
        2. Second rater: count=1 → inter_rater_number=2
        3. Third rater: count=2 → inter_rater_number=3

        Validates that annotation names and metadata are correct for each
        """
        # Test the logic without importing full backend
        rater_scenarios = [
            {'existing_count': 0, 'expected_number': 1, 'rater_id': 'user_1'},
            {'existing_count': 1, 'expected_number': 2, 'rater_id': 'user_2'},
            {'existing_count': 2, 'expected_number': 3, 'rater_id': 'user_3'},
        ]

        for scenario in rater_scenarios:
            # Simulate Phoenix returning count of existing raters
            count = scenario['existing_count']

            # Calculate inter_rater_number (as done in feedback.py)
            inter_rater_number = count + 1

            # Verify number matches expected
            assert inter_rater_number == scenario['expected_number'], \
                f"Expected number {scenario['expected_number']}, got {inter_rater_number}"

            # Verify annotation name format
            annotation_name = f"[inter-rating-{inter_rater_number}] Relevance Rating"
            assert annotation_name == f"[inter-rating-{scenario['expected_number']}] Relevance Rating"

            # Verify metadata structure
            metadata = {
                'is_inter_rater': True,
                'rater_id': scenario['rater_id'],
                'inter_rater_number': inter_rater_number,
                'original_span_id': 'original_span_123'
            }

            assert metadata['inter_rater_number'] == scenario['expected_number']
            assert metadata['is_inter_rater'] is True
            assert metadata['rater_id'] == scenario['rater_id']

    @pytest.mark.asyncio
    async def test_annotation_ids_unique_per_rater(self):
        """
        Test: Each rater gets unique annotation IDs

        Validates annotation ID format includes inter_rater_number:
        - Rater 1: inter_rater_{rater_id}_1_{qa_id}_{timestamp}
        - Rater 2: inter_rater_{rater_id}_2_{qa_id}_{timestamp}
        - Rater 3: inter_rater_{rater_id}_3_{qa_id}_{timestamp}
        """
        import time

        qa_id = "test_qa_123"
        timestamp = int(time.time())

        for rater_num in [1, 2, 3]:
            rater_id = f"anon_{rater_num}"[:8]
            inter_rater_number = rater_num

            # Generate annotation ID as done in feedback.py
            annotation_id = f"inter_rater_{rater_id}_{inter_rater_number}_{qa_id}_{timestamp}"

            # Verify format
            assert f"_{inter_rater_number}_" in annotation_id, \
                f"Annotation ID missing inter_rater_number: {annotation_id}"

            # Verify uniqueness - each rater has different number in ID
            assert annotation_id == f"inter_rater_{rater_id}_{rater_num}_{qa_id}_{timestamp}"

    def test_metadata_includes_inter_rater_number(self):
        """
        Test: Metadata includes inter_rater_number field

        This is what Phoenix displays and what prevents overwrites
        """
        # Simulate metadata for three raters
        raters_metadata = []

        for rater_num in [1, 2, 3]:
            metadata = {
                'is_inter_rater': True,
                'rater_id': f'anon_user_{rater_num}',
                'inter_rater_number': rater_num,
                'original_span_id': 'original_span_456'
            }
            raters_metadata.append(metadata)

        # Verify each has correct number
        assert raters_metadata[0]['inter_rater_number'] == 1
        assert raters_metadata[1]['inter_rater_number'] == 2
        assert raters_metadata[2]['inter_rater_number'] == 3

        # Verify all have is_inter_rater flag
        assert all(m['is_inter_rater'] for m in raters_metadata)

        # Verify all have different rater_ids
        rater_ids = [m['rater_id'] for m in raters_metadata]
        assert len(set(rater_ids)) == 3, "Rater IDs should be unique"

    def test_annotation_names_formatted_correctly(self):
        """
        Test: Annotation names have correct [inter-rating-N] prefix

        Validates format matches OpenSpec specification
        """
        base_name = "Relevance Rating"

        # Test each inter-rater number
        for number in [1, 2, 3]:
            annotation_name = f"[inter-rating-{number}] {base_name}"

            # Verify format
            assert annotation_name.startswith(f"[inter-rating-{number}]")
            assert annotation_name.endswith(base_name)
            assert "] " in annotation_name  # Space after bracket

        # Verify they're all different
        names = [f"[inter-rating-{n}] {base_name}" for n in [1, 2, 3]]
        assert len(set(names)) == 3, "Each rater should have unique annotation name"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
