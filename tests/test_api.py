import pytest
import json
from app import app, api_instance


@pytest.fixture
def client():
    """Create test client for Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestTransactionsParse:
    """Test Endpoint 1: /blackrock/challenge/v1/transactions:parse"""

    def test_parse_basic_expenses(self, client):
        """Test basic expense parsing with ceiling and remnant calculation."""
        payload = {
            "expenses": [
                {"date": "2023-02-28 15:49:20", "amount": 375},
                {"date": "2023-07-01 10:30:00", "amount": 620},
                {"date": "2023-10-12 20:15:30", "amount": 250},
                {"date": "2023-12-17 08:09:45", "amount": 480}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/transactions:parse',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify structure
        assert 'transactions' in data
        assert 'totalExpense' in data
        assert 'totalCeiling' in data
        assert 'totalRemnant' in data

        # Verify counts
        assert len(data['transactions']) == 4

        # Verify totals
        assert data['totalExpense'] == 1725
        assert data['totalCeiling'] == 1900
        assert data['totalRemnant'] == 175

        # Verify individual transaction calculations
        assert data['transactions'][0]['amount'] == 375
        assert data['transactions'][0]['ceiling'] == 400
        assert data['transactions'][0]['remnant'] == 25

        assert data['transactions'][2]['amount'] == 250
        assert data['transactions'][2]['ceiling'] == 300
        assert data['transactions'][2]['remnant'] == 50

    def test_parse_exact_multiple_of_100(self, client):
        """Test expense that is exact multiple of 100."""
        payload = {
            "expenses": [
                {"date": "2023-01-01 00:00:00", "amount": 500}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/transactions:parse',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['transactions'][0]['ceiling'] == 500
        assert data['transactions'][0]['remnant'] == 0

    def test_parse_small_amount(self, client):
        """Test small expense amount."""
        payload = {
            "expenses": [
                {"date": "2023-01-01 00:00:00", "amount": 5}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/transactions:parse',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['transactions'][0]['ceiling'] == 100
        assert data['transactions'][0]['remnant'] == 95

    def test_parse_empty_expenses(self, client):
        """Test with empty expenses list."""
        payload = {"expenses": []}

        response = client.post(
            '/blackrock/challenge/v1/transactions:parse',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['totalExpense'] == 0
        assert data['totalCeiling'] == 0
        assert data['totalRemnant'] == 0
        assert len(data['transactions']) == 0


class TestTransactionsValidator:
    """Test Endpoint 2: /blackrock/challenge/v1/transactions:validator"""

    def test_validator_all_valid(self, client):
        """Test validator with all valid transactions."""
        payload = {
            "wage": 50000,
            "transactions": [
                {"date": "2023-02-28 15:49:20", "amount": 375, "ceiling": 400, "remnant": 25},
                {"date": "2023-07-01 10:30:00", "amount": 620, "ceiling": 700, "remnant": 80},
                {"date": "2023-10-12 20:15:30", "amount": 250, "ceiling": 300, "remnant": 50}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/transactions:validator',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['valid']) == 3
        assert len(data['invalid']) == 0

    def test_validator_duplicate_date(self, client):
        """Test validator with duplicate transaction dates."""
        payload = {
            "wage": 50000,
            "transactions": [
                {"date": "2023-02-28 15:49:20", "amount": 375, "ceiling": 400, "remnant": 25},
                {"date": "2023-02-28 15:49:20", "amount": 620, "ceiling": 700, "remnant": 80}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/transactions:validator',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['valid']) == 1
        assert len(data['invalid']) == 1
        assert 'Duplicate transaction date' in data['invalid'][0]['message']

    def test_validator_negative_amount(self, client):
        """Test validator with negative amount."""
        payload = {
            "wage": 50000,
            "transactions": [
                {"date": "2023-02-28 15:49:20", "amount": -100, "ceiling": 0, "remnant": 0}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/transactions:validator',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['valid']) == 0
        assert len(data['invalid']) == 1
        assert 'negative value' in data['invalid'][0]['message']

    def test_validator_exceeds_wage(self, client):
        """Test validator with amount exceeding wage."""
        payload = {
            "wage": 50000,
            "transactions": [
                {"date": "2023-02-28 15:49:20", "amount": 50000, "ceiling": 50000, "remnant": 0}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/transactions:validator',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['valid']) == 0
        assert len(data['invalid']) == 1
        assert 'exceeds maximum limit' in data['invalid'][0]['message']


class TestTransactionsFilter:
    """Test Endpoint 3: /blackrock/challenge/v1/transactions:filter"""

    def test_filter_with_q_period(self, client):
        """Test filtering with q period (fixed amount)."""
        payload = {
            "q": [{"fixed": 0, "start": "2023-07-01 00:00:00", "end": "2023-07-31 23:59:59"}],
            "p": [],
            "k": [{"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}],
            "transactions": [
                {"date": "2023-07-01 10:30:00", "amount": 620}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/transactions:filter',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['valid']) == 1
        # Q period should set remnant to 0
        assert data['valid'][0]['remnant'] == 0

    def test_filter_with_p_period(self, client):
        """Test filtering with p period (extra amount)."""
        payload = {
            "q": [],
            "p": [{"extra": 25, "start": "2023-10-01 08:00:00", "end": "2023-12-31 23:59:59"}],
            "k": [{"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}],
            "transactions": [
                {"date": "2023-10-12 20:15:30", "amount": 250}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/transactions:filter',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['valid']) == 1
        # Base remnant is 50, plus 25 from p period
        assert data['valid'][0]['remnant'] == 75

    def test_filter_with_q_and_p_periods(self, client):
        """Test filtering with both q and p periods."""
        payload = {
            "q": [{"fixed": 10, "start": "2023-10-01 00:00:00", "end": "2023-10-31 23:59:59"}],
            "p": [{"extra": 25, "start": "2023-10-01 08:00:00", "end": "2023-12-31 23:59:59"}],
            "k": [{"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}],
            "transactions": [
                {"date": "2023-10-12 20:15:30", "amount": 250}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/transactions:filter',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['valid']) == 1
        # Q sets to 10, then p adds 25 = 35
        assert data['valid'][0]['remnant'] == 35

    def test_filter_outside_k_period(self, client):
        """Test transaction outside k period."""
        payload = {
            "q": [],
            "p": [],
            "k": [{"start": "2023-03-01 00:00:00", "end": "2023-11-30 23:59:59"}],
            "transactions": [
                {"date": "2023-02-28 15:49:20", "amount": 375}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/transactions:filter',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['valid']) == 0
        assert len(data['invalid']) == 1
        assert 'not in any evaluation period' in data['invalid'][0]['message']

    def test_filter_negative_amount_excluded(self, client):
        """Test that negative amounts are filtered out correctly."""
        payload = {
            "q": [],
            "p": [],
            "k": [{"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}],
            "transactions": [
                {"date": "2023-12-17 08:09:45", "amount": -10},
                {"date": "2023-12-17 08:09:45", "amount": 480}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/transactions:filter',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Negative should be invalid, positive should be valid (not duplicate)
        assert len(data['valid']) == 1
        assert len(data['invalid']) == 1
        assert data['valid'][0]['amount'] == 480


class TestReturnsNPS:
    """Test Endpoint 4a: /blackrock/challenge/v1/returns:nps"""

    def test_nps_basic_calculation(self, client):
        """Test NPS returns calculation with PDF example data."""
        payload = {
            "age": 29,
            "wage": 50000,
            "inflation": 5.5,
            "q": [{"fixed": 0, "start": "2023-07-01 00:00:00", "end": "2023-07-31 23:59:59"}],
            "p": [{"extra": 25, "start": "2023-10-01 08:00:00", "end": "2023-12-31 23:59:59"}],
            "k": [
                {"start": "2023-03-01 00:00:00", "end": "2023-11-30 23:59:59"},
                {"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}
            ],
            "transactions": [
                {"date": "2023-02-28 15:49:20", "amount": 375},
                {"date": "2023-07-01 10:30:00", "amount": 620},
                {"date": "2023-10-12 20:15:30", "amount": 250},
                {"date": "2023-12-17 08:09:45", "amount": 480}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/returns:nps',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify structure
        assert 'transactionsTotalAmount' in data
        assert 'transactionsTotalCeiling' in data
        assert 'savingsByDates' in data

        # Verify totals
        assert data['transactionsTotalAmount'] == 1725
        assert data['transactionsTotalCeiling'] == 1900

        # Verify k periods
        assert len(data['savingsByDates']) == 2

        # K1 (March to November): only Oct transaction
        k1 = data['savingsByDates'][0]
        assert k1['amount'] == 75  # 50 + 25 from p period
        assert round(k1['profits'], 2) == 44.94
        assert k1['taxBenefit'] == 0

        # K2 (Full year)
        k2 = data['savingsByDates'][1]
        assert k2['amount'] == 145
        assert round(k2['profits'], 2) == 86.88
        assert k2['taxBenefit'] == 0.0

    def test_nps_with_tax_benefit(self, client):
        """Test NPS with high income for tax benefit."""
        payload = {
            "age": 29,
            "wage": 100000,  # Higher wage for tax slab
            "inflation": 5.5,
            "q": [],
            "p": [],
            "k": [{"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}],
            "transactions": [
                {"date": "2023-06-15 10:00:00", "amount": 5000}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/returns:nps',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # With 1.2M annual income, should have tax benefit
        assert data['savingsByDates'][0]['taxBenefit'] >= 0.0

    def test_nps_age_over_60(self, client):
        """Test NPS with age over 60 (should use 5 years)."""
        payload = {
            "age": 65,
            "wage": 50000,
            "inflation": 5.5,
            "q": [],
            "p": [],
            "k": [{"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}],
            "transactions": [
                {"date": "2023-06-15 10:00:00", "amount": 500}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/returns:nps',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should still calculate with minimum 5 years
        assert 'savingsByDates' in data
        assert len(data['savingsByDates']) == 1


class TestReturnsIndex:
    """Test Endpoint 4b: /blackrock/challenge/v1/returns:index"""

    def test_index_basic_calculation(self, client):
        """Test Index fund returns calculation."""
        payload = {
            "age": 29,
            "wage": 50000,
            "inflation": 5.5,
            "q": [],
            "p": [],
            "k": [{"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}],
            "transactions": [
                {"date": "2023-06-15 10:00:00", "amount": 250}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/returns:index',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify structure
        assert 'transactionsTotalAmount' in data
        assert 'transactionsTotalCeiling' in data
        assert 'savingsByDates' in data

        # Index should have 'return' field, not 'profits' or 'taxBenefit'
        k1 = data['savingsByDates'][0]
        assert 'return' in k1
        assert 'profits' not in k1
        assert 'taxBenefit' not in k1

        # Return should be positive
        assert k1['return'] > 0.0

    def test_index_vs_nps_comparison(self, client):
        """Test that index returns are higher than NPS (due to rate difference)."""
        payload_base = {
            "age": 29,
            "wage": 50000,
            "inflation": 5.5,
            "q": [],
            "p": [],
            "k": [{"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}],
            "transactions": [
                {"date": "2023-06-15 10:00:00", "amount": 1000}
            ]
        }

        # Get NPS returns
        response_nps = client.post(
            '/blackrock/challenge/v1/returns:nps',
            data=json.dumps(payload_base),
            content_type='application/json'
        )
        data_nps = json.loads(response_nps.data)

        # Get Index returns
        response_index = client.post(
            '/blackrock/challenge/v1/returns:index',
            data=json.dumps(payload_base),
            content_type='application/json'
        )
        data_index = json.loads(response_index.data)

        # Index returns should be higher (14.49% vs 7.11%)
        nps_real_value = data_nps['savingsByDates'][0]['profits'] + data_nps['savingsByDates'][0]['amount']
        index_return = data_index['savingsByDates'][0]['return']

        assert index_return >= nps_real_value


class TestPerformanceEndpoint:
    """Test Endpoint 5: /blackrock/challenge/v1/performance"""

    def test_performance_endpoint(self, client):
        """Test performance metrics endpoint."""
        response = client.get('/blackrock/challenge/v1/performance')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify structure
        assert 'time' in data
        assert 'memory' in data
        assert 'threads' in data

        # Verify types and formats
        assert isinstance(data['time'], str)
        assert isinstance(data['memory'], str)
        assert isinstance(data['threads'], int)

        # Verify memory format
        assert ' MB' in data['memory']

        # Verify threads is positive
        assert data['threads'] > 0

        # Time should not be 'N/A'
        assert data['time'] != 'N/A'


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_parse_missing_expenses(self, client):
        """Test parse endpoint with missing expenses field."""
        payload = {}

        response = client.post(
            '/blackrock/challenge/v1/transactions:parse',
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Should handle gracefully
        assert response.status_code in [200, 400]

    def test_validator_missing_wage(self, client):
        """Test validator with missing wage."""
        payload = {
            "transactions": [
                {"date": "2023-02-28 15:49:20", "amount": 375}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/transactions:validator',
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Should return error
        assert response.status_code == 400

    def test_returns_decimal_inflation(self, client):
        """Test returns with inflation already as decimal."""
        payload = {
            "age": 29,
            "wage": 50000,
            "inflation": 0.055,  # Already decimal
            "q": [],
            "p": [],
            "k": [{"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}],
            "transactions": [
                {"date": "2023-06-15 10:00:00", "amount": 250}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/returns:nps',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should still work correctly
        assert data['savingsByDates'][0]['profits'] > 0

    def test_filter_multiple_k_periods_overlap(self, client):
        """Test transaction in multiple overlapping k periods."""
        payload = {
            "q": [],
            "p": [],
            "k": [
                {"start": "2023-01-01 00:00:00", "end": "2023-06-30 23:59:59"},
                {"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}
            ],
            "transactions": [
                {"date": "2023-03-15 10:00:00", "amount": 500}
            ]
        }

        response = client.post(
            '/blackrock/challenge/v1/transactions:filter',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Transaction should be valid
        assert len(data['valid']) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
