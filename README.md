# NewsWire

A full-stack news aggregation platform built with Django that delivers real-time news through GNews API integration. The application enables users to discover trending stories, search across categories, bookmark articles, and track their activity through a personalized experience.

## Why I Built This

Most news platforms focus only on displaying articles. The goal of NewsWire was to explore how a production-oriented web application handles external API integration, caching, authentication, search tracking, and user-specific content management while maintaining a responsive user experience.

## Key Highlights

* Real-time news retrieval using GNews API
* Category-based news discovery and search
* User authentication and profile management
* Bookmark management with AJAX interactions
* Search history tracking and analytics
* Database-backed caching to reduce redundant API requests
* Responsive dark/light theme support
* Automated unit testing for critical workflows

## Technical Challenges Solved

### Performance Optimization

Implemented a caching layer to reduce unnecessary external API requests and improve response times.

### Data Integrity

Added database constraints and validation mechanisms to prevent duplicate bookmarks and invalid data.

### Security

Used environment-based configuration, URL validation, and Django authentication best practices to protect sensitive information and user workflows.

### Reliability

Created automated tests covering authentication, article management, validation, and access control scenarios.

## Tech Stack

* Python
* Django
* SQLite
* JavaScript
* HTML
* CSS
* GNews API

## Local Setup

```bash
git clone https://github.com/AYUSH2K21/newswire.git
cd newswire

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

python manage.py migrate
python manage.py runserver
```

## Future Improvements

* Password reset workflow
* AI-powered article summarization
* Personalized article recommendations
* Cloud deployment and monitoring

