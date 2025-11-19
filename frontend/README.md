# AutoTest-RL Frontend Dashboard

Beautiful, interactive Python-based frontend for the AutoTest-RL API Testing System.

## Features

- 🏠 **Dashboard**: System overview, metrics, and quick actions
- 📄 **Documents**: Upload and manage API documentation
- 🧪 **Tests**: Execute tests and view real-time results
- 🧠 **Intelligence**: AI insights, patterns, and recommendations
- 📊 **Analytics**: Performance metrics, coverage, and trends

## Technology Stack

- **Streamlit**: Python web framework for data apps
- **Plotly**: Interactive visualizations
- **Pandas**: Data manipulation and analysis
- **Requests**: API communication

## Quick Start

### Run with Docker (Recommended)

```bash
# From project root
docker-compose up -d frontend

# Access at http://localhost:8501
```

### Run Locally

```bash
cd frontend

# Install dependencies
pip install -r requirements.txt

# Set API URL
export API_BASE_URL="http://localhost:8000"

# Run app
streamlit run app.py
```

## Configuration

Edit `.streamlit/secrets.toml` to configure the API base URL:

```toml
API_BASE_URL = "http://localhost:8000"
```

## Pages

### 🏠 Dashboard
- System health status
- Key metrics (documents, tests, success rate)
- Testing activity charts
- Recent test sessions
- Quick actions

### 📄 Documents
- Upload PDF/JSON API documentation
- View all uploaded documents
- Document details and statistics
- Quick test execution from document

### 🧪 Tests
- Configure and run test sessions
- Real-time test progress monitoring
- Detailed test results viewer
- Test history

### 🧠 Intelligence
- AI intelligence summary
- Learned patterns viewer
- Generated insights
- Endpoint recommendations
- API structure analysis

### 📊 Analytics
- Performance metrics and baselines
- Test coverage analysis
- Result heatmaps
- Trend analysis

## Development

### Project Structure

```
frontend/
├── app.py                  # Main application
├── pages/
│   ├── documents.py        # Document management
│   ├── tests.py            # Test execution
│   ├── intelligence.py     # AI insights
│   └── analytics.py        # Analytics
├── .streamlit/
│   ├── config.toml         # Streamlit config
│   └── secrets.toml        # API configuration
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
└── README.md               # This file
```

### Adding New Features

1. Create new page in `pages/` directory
2. Import in `app.py`
3. Add navigation option in sidebar
4. Connect to API endpoints

## Customization

### Theme

Edit `.streamlit/config.toml` to customize colors:

```toml
[theme]
primaryColor = "#667eea"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
```

### API Integration

All API calls go through `requests` library. Update `API_BASE_URL` to point to your API instance.

## Troubleshooting

### Cannot Connect to API

1. Verify API is running: `curl http://localhost:8000/health`
2. Check API_BASE_URL in secrets.toml
3. Ensure network connectivity between containers

### Port Already in Use

Change port in config.toml:
```toml
[server]
port = 8502
```

Then update docker-compose.yml accordingly.

### Slow Loading

- Increase timeout in API requests
- Enable caching for frequently accessed data
- Use pagination for large datasets

## License

MIT License - See parent project LICENSE
