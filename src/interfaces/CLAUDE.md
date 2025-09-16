# Interfaces Layer - CLAUDE.md

## 🎯 Purpose
The interfaces layer serves as the **presentation layer** in our Domain-Driven Design (DDD) architecture. It handles all external communications and user interactions without containing business logic.

## 📂 Directory Structure
```
src/interfaces/
└── flask/                      👈 Flask-based web interface
    ├── flask.py               👈 Main Flask app factory
    ├── web/                   👈 HTML views + controllers  
    │   ├── controllers/       👈 Request handlers for web UI
    │   ├── templates/         👈 Jinja2 HTML templates
    │   └── static/           👈 CSS, JS, images
    └── api/                   👈 REST/JSON API
        ├── controllers/       👈 API endpoint handlers
        └── routes/           👈 Route registration
```

## 🏗️ Architecture Principles

### 1. **Interface Adapters Pattern**
- Interfaces layer acts as adapter between external world and application services
- No business logic - only request/response handling and data formatting
- Clean separation between web UI and REST API

### 2. **Dependency Direction**
```
Interfaces → Application Services → Domain
```
- Interfaces depend on application services, never the reverse
- Domain layer has no knowledge of Flask or web frameworks

### 3. **Single Responsibility**
- **Web Controllers**: Handle HTTP requests, render templates
- **API Controllers**: Handle REST endpoints, return JSON
- **Templates**: Present data, no business logic
- **Static Assets**: UI resources (CSS, JS, images)

## 🎨 Web Interface Features

### Current Implementation
- **Legacy Home Page** (`/`): Simple interface with direct links
- **Comprehensive Dashboard** (`/dashboard`): Modern 7-view trading hub
- **Performance Visualization**: 4-panel charts with real-time data
- **Interactive Controls**: Algorithm configuration with sliders and dropdowns

### Design Principles  
- **Bootstrap 5.1.3**: Responsive, mobile-first design
- **Progressive Enhancement**: Core functionality works without JavaScript
- **Accessibility**: Semantic HTML, proper ARIA labels
- **Performance**: Lazy loading, client-side caching

## 🔌 API Interface Features

### RESTful Design
- **Resource-based URLs**: `/api/entities/company_shares`
- **HTTP Verbs**: GET for retrieval, POST for actions
- **JSON Responses**: Consistent format with success/error handling
- **Status Codes**: Proper HTTP status codes (200, 404, 500)

### Available Endpoints
```
GET  /api/entities/company_shares          # All company data
GET  /api/entities/company_shares/{id}     # Specific company  
GET  /api/entities/summary                 # Database summary
POST /api/test_managers/backtest           # Execute backtest
POST /api/test_managers/live_trading       # Execute live trading
```

## 🔄 Data Flow Patterns

### Web Request Flow
```
HTTP Request → Web Controller → Application Service → Domain Logic → Infrastructure → Database
                     ↓
               Jinja2 Template ← Presentation Data ← Domain Entities ← Repository ← ORM Models
                     ↓
               HTML Response
```

### API Request Flow  
```
HTTP Request → API Controller → Application Service → Domain Logic → Infrastructure → Database
                     ↓
              JSON Response ← Serialized Data ← Domain Entities ← Repository ← ORM Models
```

## 🛠️ Development Guidelines

### Adding New Web Routes
1. Add route method to `dashboard_controller.py`
2. Create corresponding Jinja2 template in `templates/`
3. Add navigation links and form handling
4. Test with various screen sizes

### Adding New API Endpoints
1. Add endpoint method to appropriate controller (e.g., `backtest_controller.py`)
2. Register route in `routes/routes.py`  
3. Implement proper error handling and JSON serialization
4. Document endpoint behavior and expected responses

### Template Development
- Use Bootstrap classes for responsive design
- Include CSRF protection for forms
- Implement proper error message display (Flash messages)
- Add loading states for long-running operations

### Static Asset Management
- Place CSS files in `web/static/css/`
- Use CDN for external libraries (Bootstrap, Font Awesome)
- Optimize images and minimize JavaScript
- Implement caching headers for production

## 🚀 Performance Considerations

### Frontend Optimization
- **Lazy Loading**: Dashboard sections load on demand
- **Client Caching**: Configuration saved in localStorage  
- **Minimal JavaScript**: Core functionality works server-side
- **Compressed Assets**: Minimize CSS/JS in production

### Backend Optimization
- **Database Connection Pooling**: Reuse connections efficiently
- **Query Optimization**: Use repository pattern appropriately
- **Response Caching**: Cache frequently accessed data
- **Async Operations**: Long-running tasks handled properly

## 🔐 Security Best Practices

### Input Validation
- Validate all form inputs and API parameters
- Sanitize user-provided data
- Use proper SQL parameterization (via ORM)
- Implement CSRF protection for forms

### Error Handling
- Never expose internal system details in error messages
- Log detailed errors server-side
- Return user-friendly error messages
- Use proper HTTP status codes

### Authentication & Authorization
- Future: Implement user sessions and role-based access
- API key authentication for programmatic access
- Rate limiting for API endpoints
- Secure cookie handling

## 🧪 Testing Strategy

### Unit Tests
- Test controller methods with mocked dependencies
- Verify template rendering with sample data
- Test API endpoint response formats
- Validate error handling scenarios

### Integration Tests  
- Full request/response cycle testing
- Database integration testing
- Template rendering with real data
- API endpoint testing with various inputs

### UI Testing
- Cross-browser compatibility testing
- Mobile responsiveness testing  
- Accessibility testing (WCAG compliance)
- Performance testing (load times, memory usage)

## 📊 Monitoring & Analytics

### Application Metrics
- Response times for web pages and API endpoints
- Error rates and exception tracking
- User interaction patterns
- Database query performance

### User Experience Metrics
- Page load times
- Form submission success rates
- Dashboard usage patterns
- Mobile vs desktop usage

## 🔮 Future Enhancements

### Planned Features
- [ ] **Real-time Data**: WebSocket integration for live updates
- [ ] **User Management**: Authentication, authorization, user profiles
- [ ] **Advanced Charting**: TradingView integration
- [ ] **Export Features**: PDF reports, CSV downloads, Excel exports
- [ ] **Mobile App**: React Native or Flutter companion app

### Technical Improvements
- [ ] **Microservice Architecture**: Split into smaller services
- [ ] **GraphQL API**: More flexible data querying
- [ ] **Caching Layer**: Redis for improved performance  
- [ ] **CDN Integration**: Global content delivery
- [ ] **Progressive Web App**: Offline functionality

## 📚 Related Documentation
- See `flask/CLAUDE.md` for detailed Flask implementation notes
- See `../application/CLAUDE.md` for application service integration
- See `../domain/CLAUDE.md` for business logic separation
- See `../infrastructure/CLAUDE.md` for data persistence patterns