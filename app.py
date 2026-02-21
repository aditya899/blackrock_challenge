from flask import Flask, request, jsonify
from datetime import datetime
from typing import List, Dict, Optional
import math
import psutil
import threading
import os
import time

app = Flask(__name__)


class RetirementSavingsAPI:
    def __init__(self):
        self.NPS_RATE = 0.0711
        self.INDEX_RATE = 0.1449
        self.NPS_MAX_DEDUCTION = 200000
        self.NPS_MAX_PERCENTAGE = 0.10

    @staticmethod
    def calculate_ceiling_and_remnant(amount: float) -> tuple:
        """Calculate ceiling (next multiple of 100) and remnants."""
        ceiling = math.ceil(amount / 100) * 100
        remnant = ceiling - amount
        return ceiling, remnant

    @staticmethod
    def parse_datetime(date_str: str) -> datetime:
        """Parse datetime string."""
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

    @staticmethod
    def calculate_tax(income: float) -> float:
        """Calculate tax based on simplified slabs."""
        if income <= 700000:
            return 0
        elif income <= 1000000:
            return (income - 700000) * 0.10
        elif income <= 1200000:
            return 30000 + (income - 1000000) * 0.15
        elif income <= 1500000:
            return 30000 + 30000 + (income - 1200000) * 0.20
        else:
            return 30000 + 30000 + 60000 + (income - 1500000) * 0.30

    def transactions_parse(self, expenses: List[Dict]) -> Dict:
        """Endpoint 1: Transaction Builder"""
        transactions = []
        total_expense = 0
        total_ceiling = 0
        total_remnant = 0

        for expense in expenses:
            amount = expense['amount']
            ceiling, remnant = self.calculate_ceiling_and_remnant(amount)

            transaction = {
                'date': expense['date'],
                'amount': amount,
                'ceiling': ceiling,
                'remnant': remnant
            }
            transactions.append(transaction)

            total_expense += amount
            total_ceiling += ceiling
            total_remnant += remnant

        return {
            'transactions': transactions,
            'totalExpense': total_expense,
            'totalCeiling': total_ceiling,
            'totalRemnant': total_remnant
        }

    @staticmethod
    def transactions_validator(wage: float, transactions: List[Dict]) -> Dict:
        """Endpoint 2: Transaction Validator"""
        valid = []
        invalid = []
        seen_dates = {}

        for trans in transactions:
            date_str = trans['date']

            # Check for duplicates
            if date_str in seen_dates:
                invalid_trans = trans.copy()
                invalid_trans['message'] = 'Duplicate transaction date'
                invalid.append(invalid_trans)
                continue

            seen_dates[date_str] = True

            # Validate amount
            if trans['amount'] < 0:
                invalid_trans = trans.copy()
                invalid_trans['message'] = 'Invalid amount: negative value'
                invalid.append(invalid_trans)
                continue

            if trans['amount'] >= 500000:
                invalid_trans = trans.copy()
                invalid_trans['message'] = 'Amount exceeds maximum limit'
                invalid.append(invalid_trans)
                continue

            valid.append(trans)

        return {
            'valid': valid,
            'invalid': invalid
        }

    def apply_q_periods(self, transaction_date: datetime, q_periods: List[Dict]) -> Optional[float]:
        """Apply q period rules - return fixed amount if applicable."""
        matching_q = []

        for q in q_periods:
            start = self.parse_datetime(q['start'])
            end = self.parse_datetime(q['end'])

            if start <= transaction_date <= end:
                matching_q.append((start, q))

        if not matching_q:
            return None

        # Use the one that starts latest (closest to transaction date)
        matching_q.sort(key=lambda x: x[0], reverse=True)
        return matching_q[0][1]['fixed']

    def apply_p_periods(self, transaction_date: datetime, p_periods: List[Dict]) -> float:
        """Apply p period rules - return total extra amount."""
        extra_total = 0

        for p in p_periods:
            start = self.parse_datetime(p['start'])
            end = self.parse_datetime(p['end'])

            if start <= transaction_date <= end:
                extra_total += p['extra']

        return extra_total

    def is_in_any_k_period(self, transaction_date: datetime, k_periods: List[Dict]) -> bool:
        """Check if transaction falls within at least one k period."""
        if not k_periods:
            return True

        for k in k_periods:
            start = self.parse_datetime(k['start'])
            end = self.parse_datetime(k['end'])
            if start <= transaction_date <= end:
                return True
        return False

    def transactions_filter(self, q: List[Dict], p: List[Dict], k: List[Dict], transactions: List[Dict]) -> Dict:
        """
        Endpoint 3: Temporal Constraints Validator

        This endpoint should:
        1. Calculate ceiling and remnants if not present
        2. Validate transactions (duplicates, negative amounts)
        3. Filter by k periods
        4. Apply q and p rules
        """
        valid = []
        invalid = []
        seen_dates = {}

        for trans in transactions:
            try:
                # Step 1: Calculate ceiling and remnants if not present
                if 'ceiling' not in trans or 'remnant' not in trans:
                    amount = trans['amount']
                    ceiling, remnant = self.calculate_ceiling_and_remnant(amount)
                    trans_copy = trans.copy()
                    trans_copy['ceiling'] = ceiling
                    trans_copy['remnant'] = remnant
                else:
                    trans_copy = trans.copy()

                date_str = trans['date']

                # Step 2: Validate amount
                if trans['amount'] < 0:
                    invalid_trans = {
                        'date': trans['date'],
                        'amount': trans['amount'],
                        'message': 'Invalid amount: negative value'
                    }
                    invalid.append(invalid_trans)
                    continue

                if trans['amount'] >= 500000:
                    invalid_trans = {
                        'date': trans['date'],
                        'amount': trans['amount'],
                        'message': 'Amount exceeds maximum limit'
                    }
                    invalid.append(invalid_trans)
                    continue

                # Step 3: Check for duplicates
                if date_str in seen_dates:
                    invalid_trans = {
                        'date': trans['date'],
                        'amount': trans['amount'],
                        'message': 'Duplicate transaction'
                    }
                    invalid.append(invalid_trans)
                    continue

                seen_dates[date_str] = True

                # Step 4: Validate against k periods
                trans_date = self.parse_datetime(trans['date'])
                in_k_period = self.is_in_any_k_period(trans_date, k)

                if not in_k_period:
                    invalid_trans = {
                        'date': trans['date'],
                        'amount': trans['amount'],
                        'message': 'Transaction date not in any evaluation period'
                    }
                    invalid.append(invalid_trans)
                    continue

                # Step 5: Apply q periods (fixed amount override)
                fixed_amount = self.apply_q_periods(trans_date, q)
                if fixed_amount is not None:
                    trans_copy['remnant'] = fixed_amount

                # Step 6: Apply p periods (extra amount addition)
                extra_amount = self.apply_p_periods(trans_date, p)
                trans_copy['remnant'] += extra_amount

                # Add inKPeriod flag
                trans_copy['inKPeriod'] = True

                valid.append(trans_copy)

            except Exception as e:
                invalid_trans = {
                    'date': trans.get('date', 'unknown'),
                    'amount': trans.get('amount', 0),
                    'message': f'Invalid transaction: {str(e)}'
                }
                invalid.append(invalid_trans)

        return {
            'valid': valid,
            'invalid': invalid
        }

    def calculate_returns(self, age: int, wage: float, inflation: float, q: List[Dict],
                          p: List[Dict], k: List[Dict], transactions: List[Dict],
                          investment_type: str) -> Dict:
        """Endpoints 4: Returns Calculation (NPS or Index)"""
        if inflation > 1:
            inflation = inflation / 100
        # Apply q and p period filters
        filtered_result = self.transactions_filter(q, p, k, transactions)
        valid_transactions = filtered_result['valid']

        total_amount = sum(t['amount'] for t in valid_transactions)
        total_ceiling = sum(t['ceiling'] for t in valid_transactions)

        years_to_retirement = max(60 - age, 5)
        annual_income = wage * 12

        savings_by_dates = []

        # Process each k period
        for k_period in k:
            k_start = self.parse_datetime(k_period['start'])
            k_end = self.parse_datetime(k_period['end'])

            period_remnant = 0

            # Sum remnants for transactions in this k period
            for trans in valid_transactions:
                trans_date = self.parse_datetime(trans['date'])
                if k_start <= trans_date <= k_end:
                    period_remnant += trans['remnant']

            if investment_type == 'nps':
                # NPS calculation with tax benefits
                invested = min(period_remnant, self.NPS_MAX_PERCENTAGE * annual_income, self.NPS_MAX_DEDUCTION)

                # Compound interest
                future_value = invested * ((1 + self.NPS_RATE) ** years_to_retirement)
                # Inflation adjustment
                real_value = future_value / ((1 + inflation) ** years_to_retirement)
                profits = real_value - invested

                # Tax benefit calculation
                nps_deduction = min(invested, self.NPS_MAX_PERCENTAGE * annual_income, self.NPS_MAX_DEDUCTION)
                tax_benefit = self.calculate_tax(annual_income) - self.calculate_tax(annual_income - nps_deduction)

                savings_by_dates.append({
                    'start': k_period['start'],
                    'end': k_period['end'],
                    'amount': round(period_remnant, 2),
                    'profits': round(profits, 2),
                    'taxBenefit': round(tax_benefit, 2)
                })
            else:
                # Index Fund calculation
                future_value = period_remnant * ((1 + self.INDEX_RATE) ** years_to_retirement)
                real_value = future_value / ((1 + inflation) ** years_to_retirement)

                savings_by_dates.append({
                    'start': k_period['start'],
                    'end': k_period['end'],
                    'return': round(real_value, 2)
                })

        return {
            'transactionsTotalAmount': round(total_amount, 2),
            'transactionsTotalCeiling': round(total_ceiling, 2),
            'savingsByDates': savings_by_dates
        }


# Initialize API instance
api_instance = RetirementSavingsAPI()


@app.route('/blackrock/challenge/v1/transactions:parse', methods=['POST'])
def parse_transactions():
    """Parse expenses into transactions with ceiling and remnants."""
    try:
        data = request.get_json()
        expenses = data.get('expenses', [])
        result = api_instance.transactions_parse(expenses)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/blackrock/challenge/v1/transactions:validator', methods=['POST'])
def validate_transactions():
    """Validate transactions against constraints."""
    try:
        data = request.get_json()
        wage = data.get('wage')
        transactions = data.get('transactions', [])
        result = api_instance.transactions_validator(wage, transactions)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/blackrock/challenge/v1/transactions:filter', methods=['POST'])
def filter_transactions():
    """Apply temporal constraints (q, p, k periods)."""
    try:
        data = request.get_json()
        q = data.get('q', [])
        p = data.get('p', [])
        k = data.get('k', [])
        transactions = data.get('transactions', [])
        result = api_instance.transactions_filter(q, p, k, transactions)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/blackrock/challenge/v1/returns:nps', methods=['POST'])
def calculate_nps_returns():
    """Calculate NPS investment returns with tax benefits."""
    try:
        data = request.get_json()
        age = data.get('age')
        wage = data.get('wage')
        inflation = data.get('inflation')
        q = data.get('q', [])
        p = data.get('p', [])
        k = data.get('k', [])
        transactions = data.get('transactions', [])

        result = api_instance.calculate_returns(age, wage, inflation, q, p, k, transactions, 'nps')
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/blackrock/challenge/v1/returns:index', methods=['POST'])
def calculate_index_returns():
    """Calculate Index Fund investment returns."""
    try:
        data = request.get_json()
        age = data.get('age')
        wage = data.get('wage')
        inflation = data.get('inflation')
        q = data.get('q', [])
        p = data.get('p', [])
        k = data.get('k', [])
        transactions = data.get('transactions', [])

        result = api_instance.calculate_returns(age, wage, inflation, q, p, k, transactions, 'index')
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/blackrock/challenge/v1/performance', methods=['GET'])
def get_performance():
    try:
        # Track request start time
        start_time = time.time()

        # Get system metrics
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        thread_count = threading.active_count()

        # Calculate elapsed time in milliseconds
        elapsed_time = (time.time() - start_time) * 1000  # Convert to ms

        # FORMAT OPTIONS:

        # Option A: Milliseconds (e.g., "2.45")
        time_str = f"{elapsed_time:.2f}"

        # Option B: HH:mm:ss.SSS format
        hours = int(elapsed_time // 3600000)
        minutes = int((elapsed_time % 3600000) // 60000)
        seconds = int((elapsed_time % 60000) // 1000)
        milliseconds = int(elapsed_time % 1000)
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

        # Option C: Simple milliseconds with unit
        time_str = f"{elapsed_time:.2f} ms"

        return jsonify({
            'time': time_str,
            'memory': f"{memory_mb:.2f} MB",
            'threads': thread_count
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5477, debug=False)
