# BlackRock Retirement Savings Challenge - Solution

## 🎯 Overview
Production-grade REST API for automated retirement savings through expense-based micro-investments. This solution implements all required endpoints with comprehensive validation, temporal constraint processing, and investment return calculations.

## 🚀 Features
- **Transaction parsing** with automatic ceiling/remnant calculation
- **Transaction validation** with duplicate detection and constraint checking
- **Temporal constraint filtering** (q, p, k periods) with complex rule application
- **NPS returns calculation** with compound interest and tax benefit calculations
- **Index Fund returns calculation** with inflation adjustment
- **Performance monitoring** endpoint for system metrics

## 🛠️ Technology Stack
- **Language**: Python 3.11
- **Framework**: Flask 3.0
- **Containerization**: Docker & Docker Compose
- **OS**: Alpine Linux (minimal footprint, security-focused)

## 📋 Prerequisites
- Docker installed on your system
- Docker Compose (optional, recommended)
- Port 5477 available

## 🔧 Quick Start

### Option 1: Using Docker Compose (Recommended)
```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Option 2: Using Docker directly
```bash
# Build the image
docker build -t blk-hacking-ind-aditya-raj .

# Run the container
docker run -d -p 5477:5477 blk-hacking-ind-aditya-raj

# View logs
docker logs <container-id>

# Stop the container
docker stop <container-id>
```

### Option 3: Running locally (for development)
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

## 📡 API Endpoints

### 1. Transaction Parser
**POST** `/blackrock/challenge/v1/transactions:parse`

Parse expenses and calculate ceiling/remnant values.

**Request:**
```json
{
  "expenses": [
    {"date": "2023-10-12 20:15:00", "amount": 250},
    {"date": "2023-02-28 15:49:00", "amount": 375},
    {"date": "2023-07-01 21:59:00", "amount": 620},
    {"date": "2023-12-17 08:09:45", "amount": 480}
  ]
}
```

**Response:**
```json
{
    "totalCeiling": 1900,
    "totalExpense": 1725,
    "totalRemnants": 175,
    "transactions": [
        {
            "amount": 250,
            "ceiling": 300,
            "date": "2023-10-12 20:15:00",
            "remnants": 50
        },
        {
            "amount": 375,
            "ceiling": 400,
            "date": "2023-02-28 15:49:00",
            "remnants": 25
        },
        {
            "amount": 620,
            "ceiling": 700,
            "date": "2023-07-01 21:59:00",
            "remnants": 80
        },
        {
            "amount": 480,
            "ceiling": 500,
            "date": "2023-12-17 08:09:45",
            "remnants": 20
        }
    ]
}
```

### 2. Transaction Validator
**POST** `/blackrock/challenge/v1/transactions:validator`

Validate transactions against wage constraints and business rules.

**Request:**
```json
{
  "wage": 50000,
  "transactions": [
      {"date": "2023-01-15 10:30:00", "amount": 2000000, "ceiling": 300, "remnant": 50},
      {"date": "2023-03-20 14:45:00", "amount": 3500, "ceiling": 400, "remnant": 70},
      {"date": "2023-06-10 09:15:00", "amount": 1500, "ceiling": 200, "remnant": 30},
      {"date": "2023-07-10 09:15:00", "amount": -250, "ceiling": 200, "remnant": 50}
  ]
}
```

**Response:**
```json
{
    "invalid": [
        {
            "amount": 2000000,
            "ceiling": 300,
            "date": "2023-01-15 10:30:00",
            "message": "Amount exceeds maximum limit",
            "remnant": 50
        },
        {
            "amount": -250,
            "ceiling": 200,
            "date": "2023-07-10 09:15:00",
            "message": "Invalid amount: negative value",
            "remnant": 50
        }
    ],
    "valid": [
        {
            "amount": 3500,
            "ceiling": 400,
            "date": "2023-03-20 14:45:00",
            "remnant": 70
        },
        {
            "amount": 1500,
            "ceiling": 200,
            "date": "2023-06-10 09:15:00",
            "remnant": 30
        }
    ]
}
```

### 3. Transaction Filter
**POST** `/blackrock/challenge/v1/transactions:filter`

Apply q, p, k period rules to transactions.

**Request:**
```json
{
    "q": [{"fixed": 0, "start": "2023-07-01 00:00:00", "end": "2023-07-31 23:59:59"}],
    "p": [{"extra": 30, "start": "2023-10-01 08:00:00", "end": "2023-12-31 23:59:59"}],
    "k": [
        {"start": "2023-03-01 00:00:00", "end": "2023-11-30 23:59:59"},
        {"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}
    ],
    "wage":50000,
    "transactions": [
        {"date": "2023-02-28 15:49:20", "amount": 375},
        {"date": "2023-07-15 10:30:00", "amount": 620},
        {"date": "2023-10-12 20:15:30", "amount": 250},
        {"date": "2023-10-12 20:15:30", "amount": 250},
        {"date": "2023-12-17 08:09:45", "amount": -480}
    ]
}
```

**Response:**
```json
{
    "invalid": [
        {
            "amount": 250,
            "date": "2023-10-12 20:15:30",
            "message": "Duplicate transaction"
        },
        {
            "amount": -480,
            "date": "2023-12-17 08:09:45",
            "message": "Invalid amount: negative value"
        }
    ],
    "valid": [
        {
            "amount": 375,
            "ceiling": 400,
            "date": "2023-02-28 15:49:20",
            "inKPeriod": true,
            "remnants": 25
        },
        {
            "amount": 620,
            "ceiling": 700,
            "date": "2023-07-15 10:30:00",
            "inKPeriod": true,
            "remnants": 0
        },
        {
            "amount": 250,
            "ceiling": 300,
            "date": "2023-10-12 20:15:30",
            "inKPeriod": true,
            "remnants": 80
        }
    ]
}
```

### 4. NPS Returns
**POST** `/blackrock/challenge/v1/returns:nps`

Calculate NPS investment returns with tax benefits.

**Request:**
```json
{
    "age": 29,
    "inflation": 5.5,
    "q": [{"fixed": 0, "start": "2023-07-01 00:00:00", "end": "2023-07-31 23:59:59"}],
    "p": [{"extra": 25, "start": "2023-10-01 08:00:00", "end": "2023-12-31 23:59:59"}],
    "k": [
        {"start": "2023-03-01 00:00:00", "end": "2023-11-30 23:59:59"},
        {"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}
    ],
    "wage":50000,
    "transactions": [
        {"date": "2023-02-28 15:49:20", "amount": 375},
        {"date": "2023-07-01 10:30:00", "amount": 620},
        {"date": "2023-10-12 20:15:30", "amount": 250},
        {"date": "2023-12-17 08:09:45", "amount": -10},
        {"date": "2023-12-17 08:09:45", "amount": 480}
    ]
}
```

**Response:**
```json
{
    "savingsByDates": [
        {
            "amount": 75,
            "end": "2023-11-30 23:59:59",
            "profits": 44.94,
            "start": "2023-03-01 00:00:00",
            "taxBenefit": 0
        },
        {
            "amount": 145,
            "end": "2023-12-31 23:59:59",
            "profits": 86.88,
            "start": "2023-01-01 00:00:00",
            "taxBenefit": 0
        }
    ],
    "transactionsTotalAmount": 1725,
    "transactionsTotalCeiling": 1900
}
```

### 5. Index Fund Returns
**POST** `/blackrock/challenge/v1/returns:index`

Calculate Index Fund investment returns.

**Response:**
```json
{
    "savingsByDates": [
        {
            "end": "2023-11-30 23:59:59",
            "return": 946.3,
            "start": "2023-03-01 00:00:00"
        },
        {
            "end": "2023-12-31 23:59:59",
            "return": 1829.51,
            "start": "2023-01-01 00:00:00"
        }
    ],
    "transactionsTotalAmount": 1725,
    "transactionsTotalCeiling": 1900
}
```

### 6. Performance Metrics
**GET** `/blackrock/challenge/v1/performance`

Get system performance metrics.

**Response:**
```json
{
    "memory": "37.29 MB",
    "threads": 2,
    "time": "0.00 ms"
}
```

## 🧪 Testing

The solution includes comprehensive integration tests.

```bash
# Make sure the server is running first
docker-compose up -d

# Run the tests
python tests/test_api.py
```

Expected output:
```
test_api.py::TestTransactionsParse::test_parse_basic_expenses PASSED     [  4%]
test_api.py::TestTransactionsParse::test_parse_exact_multiple_of_100 PASSED [  8%]
test_api.py::TestTransactionsParse::test_parse_small_amount PASSED       [ 13%]
test_api.py::TestTransactionsParse::test_parse_empty_expenses PASSED     [ 17%]
test_api.py::TestTransactionsValidator::test_validator_all_valid PASSED  [ 21%]
test_api.py::TestTransactionsValidator::test_validator_duplicate_date PASSED [ 26%]
test_api.py::TestTransactionsValidator::test_validator_negative_amount PASSED [ 30%]
test_api.py::TestTransactionsValidator::test_validator_exceeds_wage PASSED [ 34%]
test_api.py::TestTransactionsFilter::test_filter_with_q_period PASSED    [ 39%]
test_api.py::TestTransactionsFilter::test_filter_with_p_period PASSED    [ 43%]
test_api.py::TestTransactionsFilter::test_filter_with_q_and_p_periods PASSED [ 47%]
test_api.py::TestTransactionsFilter::test_filter_outside_k_period PASSED [ 52%]
test_api.py::TestTransactionsFilter::test_filter_negative_amount_excluded PASSED [ 56%]
test_api.py::TestReturnsNPS::test_nps_basic_calculation PASSED           [ 60%]
test_api.py::TestReturnsNPS::test_nps_with_tax_benefit PASSED            [ 65%]
test_api.py::TestReturnsNPS::test_nps_age_over_60 PASSED                 [ 69%]
test_api.py::TestReturnsIndex::test_index_basic_calculation PASSED       [ 73%]
test_api.py::TestReturnsIndex::test_index_vs_nps_comparison PASSED       [ 78%]
test_api.py::TestPerformanceEndpoint::test_performance_endpoint PASSED   [ 82%]
test_api.py::TestEdgeCases::test_parse_missing_expenses PASSED           [ 86%]
test_api.py::TestEdgeCases::test_validator_missing_wage PASSED           [ 91%]
test_api.py::TestEdgeCases::test_returns_decimal_inflation PASSED        [ 95%]
test_api.py::TestEdgeCases::test_filter_multiple_k_periods_overlap PASSED [100%]

============================= 23 passed in 0.25s ==============================
```

## 🧮 Algorithm Details

### Processing Order
The system follows a strict processing sequence:

1. **Calculate ceiling and remnant**: Round up to next multiple of 100
2. **Apply q period rules**: Override remnant with fixed amount (if applicable)
3. **Apply p period rules**: Add extra amounts to remnant (cumulative)
4. **Group by k periods**: Aggregate remnant for investment calculation
5. **Calculate returns**: Apply compound interest and inflation adjustment

### Period Rules

**q Periods (Fixed Amount Override)**
- When a transaction falls within a q period, replace remnant with fixed amount
- If multiple q periods match, use the one with the latest start date
- If start dates are equal, use the first in the list

**p Periods (Extra Amount Addition)**
- When a transaction falls within a p period, add extra amount to remnant
- If multiple p periods match, add ALL extra amounts together
- p periods are additive to q periods (both can apply)

**k Periods (Evaluation Grouping)**
- Each k period independently sums remnants from matching transactions
- Transactions can belong to multiple k periods
- Date ranges are inclusive (start and end dates included)

### Investment Calculations

**NPS (National Pension Scheme)**
- Interest rate: 7.11% compounded annually
- Max deduction: ₹2,00,000 or 10% of annual income (whichever is lower)
- Tax benefit calculated based on simplified tax slabs
- Returns adjusted for inflation

**Index Fund (NIFTY 50)**
- Interest rate: 14.49% compounded annually
- No investment limits or restrictions
- No tax benefits
- Returns adjusted for inflation

**Formulas:**
- Compound Interest: `A = P × (1 + r)^t`
- Inflation Adjustment: `A_real = A_future / (1 + inflation)^t`
- Years to retirement: `max(60 - age, 5)`

## 🏗️ Architecture Decisions

### Why Alpine Linux?
- **Size**: ~5MB base image vs ~100MB+ for standard distributions
- **Security**: Minimal attack surface with fewer packages
- **Performance**: Lightweight and fast for containerized microservices
- **Maintenance**: Active community with regular security updates

### Design Patterns
- **Single Responsibility Principle**: Each endpoint handles one specific operation
- **Immutability**: Original transaction data preserved through copies
- **Error Handling**: Comprehensive exception handling with meaningful messages
- **RESTful API**: Standard HTTP methods and status codes

### Performance Considerations
- **Time Complexity**: O(n×q) for q-period matching, O(n×p) for p-periods, O(n×k) for k-periods
- **Space Complexity**: O(n) for transaction storage
- **Optimizations**: 
  - Sorting for q-period conflict resolution
  - Early termination on validation failures
  - Efficient datetime parsing

## 📂 Project Structure
```
retirement_savings_solution/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── Dockerfile         # Container configuration
├── compose.yaml       # Docker Compose setup
├── tests/
│   └── test_api.py    # Integration tests
└── README.md          # This file
```

## 🔒 Security Considerations
- Input validation on all endpoints
- Error messages don't expose internal details
- Alpine Linux for reduced attack surface
- No hardcoded credentials or secrets

## 🚀 Future Enhancements
- Database integration for persistent storage
- Redis caching for frequently accessed calculations
- Authentication & authorization (JWT)
- Rate limiting for API protection
- Batch processing for large datasets
- WebSocket support for real-time updates
- Monitoring and logging with ELK stack
- Kubernetes deployment manifests

## 📝 Example Usage

### Using curl
```bash
# Parse transactions
curl -X POST http://localhost:5477/blackrock/challenge/v1/transactions:parse \\
  -H "Content-Type: application/json" \\
  -d '{"expenses": [{"date": "2023-10-12 20:15:00", "amount": 250}]}'

# Get performance metrics
curl http://localhost:5477/blackrock/challenge/v1/performance
```

### Using Python requests
```python
import requests

url = "http://localhost:5477/blackrock/challenge/v1/transactions:parse"
data = {
    "expenses": [
        {"date": "2023-10-12 20:15:00", "amount": 250}
    ]
}

response = requests.post(url, json=data)
print(response.json())
```

## 🐛 Troubleshooting

**Port already in use:**
```bash
# Check what's using port 5477
lsof -i :5477

# Change port in compose.yaml if needed
ports:
  - "5478:5477"  # Use 5478 on host
```

**Container won't start:**
```bash
# Check logs
docker-compose logs

# Rebuild without cache
docker-compose build --no-cache
docker-compose up -d
```

**Tests failing:**
```bash
# Ensure server is running
curl http://localhost:5477/blackrock/challenge/v1/performance

# Check if port is accessible
telnet localhost 5477
```

## 👤 Author
Aditya Raj - Backend Engineer specializing in financial systems
