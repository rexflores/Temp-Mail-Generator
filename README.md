# 📧 TempMail - Modern Email Client

A modernized temporary email generator with a Gmail/Outlook-style interface, built using **Mail.tm** service. Features a responsive design, dark mode, HTML email rendering, and real-time email monitoring.

## ✨ Features

### 🎨 Modern UI/UX
- **Gmail/Outlook-style interface** with professional design
- **Responsive layout** that works on all devices
- **Dark/Light theme toggle** with user preference persistence
- **Real-time email updates** with automatic polling
- **Smooth animations** and hover effects throughout

### 📧 Email Management
- **HTML email rendering** with secure sanitization
- **Attachment support** with preview and download
- **Folder organization** (Inbox, Sent, Drafts, Trash)
- **Email actions** (star, mark read/unread, delete)
- **Search functionality** across all emails

### 🔒 Security
- **XSS protection** with HTML sanitization using bleach
- **Safe attachment handling**
- **Secure email content rendering**

### ⚡ Interactive Features
- **Loading states** with skeleton loaders
- **Toast notifications** for user feedback
- **Keyboard shortcuts** (Enter to register email)
- **Mobile-responsive** sidebar navigation

## 🚀 Quick Start

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rexflores/Temp-Mail-Generator.git
   cd Temp-Mail-Generator
   ```

2. **Set up virtual environment (recommended):**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

**Web Interface (Modern UI):**
```bash
python app.py
```
Then open your browser to `http://localhost:5000`

**GUI Interface (Tkinter):**
```bash
cd GUI
python gui_app.py
```

**CLI Interface:**
```bash
cd CLI
python cli_app.py
```

## 📱 How to Use

### 1. Register a Temporary Email
- Enter a custom prefix in the sidebar
- Click the "+" button to register
- Your temporary email will be generated and displayed

### 2. Start Listening for Emails
- Click the "Listen" button to start monitoring
- New emails will appear automatically in real-time
- Email count badges will update in the sidebar

### 3. Read and Manage Emails
- Click on any email in the list to view details
- Use action buttons to reply, forward, delete, or star emails
- Switch between folders using the sidebar navigation

### 4. Customize Your Experience
- Toggle between light and dark themes
- Use the search box to find specific emails
- Refresh manually or let auto-polling handle updates

## 🛠️ Technical Details

### Backend (Flask)
- **Enhanced API endpoints** for modern email client features
- **HTML sanitization** with bleach library for XSS protection
- **Error handling** and robust email processing
- **Folder management** and email organization
- **RESTful API** design for frontend integration

### Frontend
- **Vanilla JavaScript** with modern ES6+ features
- **CSS Custom Properties** for theme management
- **Feather Icons** for consistent iconography
- **DOMPurify** for additional client-side sanitization
- **Responsive CSS Grid/Flexbox** layouts

### Dependencies
- **Flask 2.3.3** - Web framework
- **mailtm 1.1.1** - Mail.tm API client
- **bleach 6.0.0** - HTML sanitization
- **python-dateutil 2.8.2** - Date processing

## 🌐 Deployment

### Vercel Deployment
The project includes `vercel.json` configuration for easy deployment:

```bash
npm install -g vercel
vercel
```

### Local Development
```bash
python app.py
# App runs on http://localhost:5000
```

## 📁 Project Structure

```
Temp-Mail-Generator/
├── app.py                 # Modern Flask application
├── requirements.txt       # Python dependencies
├── vercel.json           # Vercel deployment config
├── test_sanitization.py  # HTML sanitization tests
├── templates/
│   └── index.html        # Modern email client UI
├── GUI/
│   └── gui_app.py        # Tkinter GUI version
└── CLI/
    └── cli_app.py        # Command-line version
```

## 🔧 API Endpoints

- `GET /` - Main email client interface
- `GET /api/status` - Application status
- `POST /register_email` - Register new temporary email
- `POST /start_listening` - Start email monitoring
- `GET /api/emails` - Get emails with pagination/filtering
- `GET /api/emails/<id>` - Get specific email details
- `POST /api/emails/<id>/action` - Perform email actions

## 🐛 Troubleshooting

### Common Issues

**HTML Sanitization Errors:**
- Ensure bleach 6.0.0 is installed: `pip install bleach==6.0.0`
- The app includes fallback sanitization if bleach fails

**Email Not Receiving:**
- Check that you've clicked "Listen" to start monitoring
- Verify your temporary email is valid and active
- Check browser console for any JavaScript errors

**UI Not Loading Properly:**
- Ensure all CDN resources are accessible (DOMPurify, Feather Icons)
- Clear browser cache and reload
- Check browser developer tools for errors

### Development

**Running Tests:**
```bash
python test_sanitization.py
```

**Debug Mode:**
The Flask app runs in debug mode by default during development.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Commit your changes: `git commit -m 'Add feature'`
5. Push to the branch: `git push origin feature-name`
6. Submit a pull request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- **Mail.tm** for providing the temporary email service
- **Feather Icons** for the beautiful icon set
- **DOMPurify** for client-side HTML sanitization
- **Flask** for the excellent web framework

---

**Built with ❤️ for modern email management**
