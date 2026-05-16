# Civil Complaint Resolver

An AI-powered civil complaint resolution system that automatically analyzes, categorizes, and routes civil complaints to appropriate authorities. Supports both image-based and text-based complaints with intelligent duplicate detection and comprehensive analytics.

## Features

- **Multi-modal Input**: Accept complaints via images, URLs, or text descriptions
- **AI-Powered Analysis**: Uses advanced language models to categorize complaints by type, severity, and authority
- **Intelligent Routing**: Automatically routes complaints to the appropriate government authority (MoRTH, Municipal Corporation, BESCOM, etc.)
- **Duplicate Detection**: Perceptual hashing prevents duplicate complaint submissions
- **Vector Database**: Chroma-based vector storage for efficient complaint search and retrieval
- **Web Interface**: Modern Flask-based web application with tabbed input interface
- **CLI Interface**: Command-line interface with multiline input support
- **Analytics Dashboard**: Comprehensive analytics showing complaint trends and authority breakdowns
- **RESTful API**: Programmatic access for integration with other systems

## Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **RAM**: Minimum 4GB (8GB recommended for better performance)
- **Storage**: 2GB free space for models and vector database

### Required Software
- **Git**: For version control
- **Ollama**: For running local AI models (optional, fallback available)
- **Web Browser**: Chrome, Firefox, Safari, or Edge

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/PrathimaSingh/civil-complaint-resolver.git
cd civil-complaint-resolver
```

### 2. Set Up Python Environment

#### Option A: Using venv (Recommended)
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

#### Option B: Using conda
```bash
# Create conda environment
conda create -n civil-complaints python=3.11
conda activate civil-complaints
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

If `requirements.txt` doesn't exist, install these core packages:
```bash
pip install flask langchain langchain-chroma langchain-ollama pillow imagehash requests werkzeug
```

### 4. Set Up Ollama (Optional but Recommended)
Ollama provides local AI models for better performance and privacy.

#### Install Ollama
- **Windows**: Download from https://ollama.ai/download/windows
- **macOS**: `brew install ollama`
- **Linux**: Follow instructions at https://ollama.ai/download/linux

#### Pull Required Models
```bash
# Pull the text embedding model
ollama pull nomic-embed-text

# Pull vision-capable model (for image analysis)
ollama pull llava:7b  # or another vision model
```

## Configuration

### Environment Variables (Optional)
Create a `.env` file in the project root:

```env
# Flask configuration
FLASK_ENV=development
FLASK_DEBUG=True

# Ollama configuration (optional)
OLLAMA_BASE_URL=http://localhost:11434

# Vector database configuration
CHROMA_DB_DIR=./chroma_complaints_db
COLLECTION_NAME=civil_complaints
```

## Running the Application

### Method 1: Web Interface (Recommended)

#### Start the Flask Web Server
```bash
python UI_App.py
```
```
flask --app src/civic_redressal/main.py run

OR

$env:PYTHONPATH = "src"
flask --app civic_redressal.main run
```

#### Access the Application
Open your browser and go to: http://localhost:5000

#### Using the Web Interface
1. **Upload Complaint**: Choose between File Upload, URL Input, or Text Input tabs
2. **File Upload**: Select image files from your computer
3. **URL Input**: Paste image URLs from the web
4. **Text Input**: Describe the complaint in text form
5. **Submit**: Click submit to process the complaint
6. **View Analytics**: Visit http://localhost:5000/analytics for dashboard

### Method 2: Command Line Interface

#### Start the CLI Application
```bash
python civil_complaint_resolver.py
```
```
$env:PYTHONPATH = "src"
python -c "import civic_redressal; print('ok')"
python -m civic_redressal.cli
```

#### CLI Commands
```
Available Commands:
  new <image_path>           -- Process new complaint from image
  text <title>|<description> -- Process new complaint from text
  close <ID> <resolved_path> -- Close a complaint
  analytics                  -- Show analytics
  list                       -- List all complaints
  exit                       -- Quit
```

#### CLI Examples
```bash
# Process image complaint
new path/to/complaint_image.jpg

# Process text complaint
text "Potholes on Main Street causing traffic issues"

# Close a complaint with resolved image
close COMP12345 path/to/resolved_image.jpg

# View analytics
analytics
```

### Method 3: Direct Python Execution

#### Process a Single Complaint
```python
from civil_complaint_resolver import process_new_complaint

# Process image complaint
process_new_complaint("path/to/image.jpg")

# Process text complaint
process_new_complaint("", "Complaint title", "Complaint description")
```

## Project Structure

```
civil-complaint-resolver/
├── civil_complaint_resolver.py    # Core processing engine
├── UI_App.py                      # Flask web application
├── complaint_vector_db.py         # Vector database operations
├── complaints_db.json             # Complaint metadata storage
├── templates/                     # HTML templates
│   ├── index.html                # Main upload interface
│   ├── analytics.html            # Analytics dashboard
│   ├── upload_incoming.html      # Incoming complaint form
│   └── upload_resolved.html      # Resolved complaint form
├── incoming_complaints/          # Uploaded complaint images
├── resolved_complaints/          # Resolved complaint images
├── sent_messages/                 # Communication logs
├── chroma_complaints_db/         # Vector database storage
├── .gitignore                    # Git ignore rules
└── README.md                     # This file
```

## API Usage

### RESTful Endpoints

#### Submit New Complaint
```bash
POST /upload_incoming
Content-Type: multipart/form-data

# Form data:
- file: Image file (optional)
- url: Image URL (optional)
- text: Text description (optional)
- title: Complaint title (optional)
```

#### Get Analytics
```bash
GET /analytics
```

#### Close Complaint
```bash
POST /upload_resolved
Content-Type: multipart/form-data

# Form data:
- complaint_id: ID of complaint to close
- file: Resolved image file
```

## Troubleshooting

### Common Issues

#### 1. Ollama Model Not Found
**Error**: `Model 'nomic-embed-text' not found`
**Solution**:
```bash
ollama pull nomic-embed-text
```

#### 2. Port Already in Use
**Error**: `[Errno 48] Address already in use`
**Solution**: Kill the process using port 5000 or change the port:
```bash
# Find process using port 5000
netstat -tulpn | grep :5000

# Kill the process (replace PID)
kill -9 <PID>
```

#### 3. Vector DB Error
**Error**: `Vector DB Error: Image not found`
**Solution**: This occurs with text-only complaints. The system handles this automatically - ensure you're using the latest version.

#### 4. Import Errors
**Error**: `ModuleNotFoundError`
**Solution**: Install missing dependencies:
```bash
pip install -r requirements.txt
```

#### 5. Permission Errors
**Error**: `Permission denied`
**Solution**: Ensure proper permissions on the project directory and virtual environment.

### Performance Tips

1. **Use Ollama**: Local models provide better performance and privacy
2. **Pre-download Models**: Pull models before running the application
3. **Use SSD Storage**: Vector database performs better on SSDs
4. **Monitor RAM Usage**: Close other applications if experiencing slowdowns

## Development

### Running Tests
```bash
# Run basic functionality tests
python -c "from civil_complaint_resolver import process_new_complaint; print('Import successful')"
```

### Code Style
This project follows PEP 8 Python coding standards. Use tools like `black` and `flake8` for code formatting and linting.

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section above
- Review the code comments for implementation details

## Acknowledgments

- Built with LangChain and LangGraph for AI workflow orchestration
- Uses Chroma for vector database functionality
- Ollama for local AI model hosting
- Flask for web framework
- PIL/Pillow for image processing
