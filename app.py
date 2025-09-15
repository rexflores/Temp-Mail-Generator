from flask import Flask, render_template, request, jsonify
from mailtm import Email
import random
import string
import bleach
import base64
import datetime
import mimetypes
import re
from urllib.parse import urlparse

app = Flask(__name__)
email_client = Email()  # Initialize the Email object
current_email = None  # Store the current email address
received_emails = []  # Store received emails with enhanced data structure
folders = {
    'inbox': [],
    'sent': [],
    'drafts': [],
    'trash': []
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current application status"""
    return jsonify({
        "current_email": current_email,
        "domain": email_client.domain if email_client else None,
        "total_emails": len(received_emails),
        "folders": {folder: len(emails) for folder, emails in folders.items()}
    })

@app.route('/get_domain', methods=['GET'])
def get_domain():
    try:
        domain = email_client.domain
        return jsonify({"domain": domain, "success": True})
    except Exception as e:
        return jsonify({"error": f"Failed to fetch domain: {str(e)}", "success": False}), 500

@app.route('/register_email', methods=['POST'])
def register_email():
    global current_email
    try:
        data = request.get_json()
        email_prefix = data.get("email_prefix", "").strip()

        if not email_prefix:
            return jsonify({"error": "Email prefix is required.", "success": False}), 400

        # Generate a random suffix to ensure uniqueness
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
        # Combine prefix with a random suffix
        email_client.register(email_prefix + random_suffix)
        current_email = email_client.address
        
        # Clear previous emails when new email is registered
        received_emails.clear()
        for folder in folders.values():
            folder.clear()
            
        return jsonify({
            "email": current_email, 
            "success": True,
            "message": f"Email {current_email} successfully registered"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to register email: {str(e)}", "success": False}), 500

@app.route('/copy_email', methods=['POST'])
def copy_email():
    if current_email:
        return jsonify({
            "message": "Email copied to clipboard!", 
            "email": current_email,
            "success": True
        })
    return jsonify({"error": "No email to copy!", "success": False}), 400

def sanitize_html_content(html_content):
    """Sanitize HTML content while preserving essential styling"""
    try:
        import bleach
        from bleach.css_sanitizer import CSSSanitizer
        
        # Create CSS sanitizer for safe style attributes
        css_sanitizer = CSSSanitizer(allowed_css_properties=[
            'color', 'background-color', 'font-size', 'font-weight', 'font-style',
            'text-align', 'text-decoration', 'margin', 'padding', 'border',
            'width', 'height', 'display', 'float', 'clear'
        ])
        
        allowed_tags = [
            'p', 'br', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'strong', 'b', 'em', 'i', 'u', 'strike', 'sub', 'sup',
            'ul', 'ol', 'li', 'a', 'img', 'table', 'thead', 'tbody', 'tr', 'td', 'th',
            'blockquote', 'pre', 'code', 'hr'
        ]
        
        allowed_attributes = {
            '*': ['style', 'class'],
            'a': ['href', 'title', 'target'],
            'img': ['src', 'alt', 'width', 'height', 'style'],
            'table': ['border', 'cellpadding', 'cellspacing', 'width'],
            'td': ['colspan', 'rowspan', 'width', 'height'],
            'th': ['colspan', 'rowspan', 'width', 'height']
        }
        
        return bleach.clean(
            html_content, 
            tags=allowed_tags, 
            attributes=allowed_attributes,
            css_sanitizer=css_sanitizer
        )
    except Exception as e:
        # Fallback: Basic HTML sanitization without bleach
        print(f"Warning: bleach sanitization failed: {e}")
        return basic_html_sanitize(html_content)

def basic_html_sanitize(html_content):
    """Basic HTML sanitization fallback"""
    import re
    
    # Remove script tags and their content
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove style tags and their content (but keep inline styles for now)
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove dangerous attributes
    dangerous_attrs = ['onclick', 'onload', 'onerror', 'onmouseover', 'onmouseout', 'onfocus', 'onblur']
    for attr in dangerous_attrs:
        html_content = re.sub(f'{attr}\\s*=\\s*["\'][^"\']*["\']', '', html_content, flags=re.IGNORECASE)
    
    # Remove javascript: links
    html_content = re.sub(r'href\\s*=\\s*["\']javascript:[^"\']*["\']', 'href="#"', html_content, flags=re.IGNORECASE)
    
    return html_content

def convert_urls_to_links(text):
    """Convert URLs in plain text to clickable HTML links"""
    if not text:
        return text
    
    import html
    
    # Escape HTML entities first to prevent injection
    text = html.escape(text)
    
    # Handle URLs in brackets like [https://example.com] FIRST
    def replace_bracket_url(match):
        url = html.unescape(match.group(1))
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            display_text = parsed.netloc
        except:
            display_text = url[:30] + "..." if len(url) > 30 else url
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer" style="color: var(--primary-color); text-decoration: none; font-weight: 500;">[{display_text}]</a>'
    
    # Pattern for bracketed URLs - do this BEFORE processing bracket emails
    text = re.sub(r'\[(https?://[^\]]+)\]', replace_bracket_url, text)
    
    # Handle ONLY remaining email addresses in brackets [email@domain.com] that weren't URLs
    def replace_bracket_email(match):
        email = match.group(1)
        return f'<a href="mailto:{email}" style="color: var(--primary-color); text-decoration: none; font-weight: 500;">[{email}]</a>'
    
    # This will only match emails in brackets that haven't been converted to links already
    text = re.sub(r'\[([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\]', replace_bracket_email, text)
    
    # Handle standalone email addresses (not in brackets, not already part of links)
    def replace_email(match):
        email = match.group(1)
        return f'<a href="mailto:{email}" style="color: var(--primary-color); text-decoration: none; font-weight: 500;">{email}</a>'
    
    # This pattern avoids matching emails that are already part of href attributes
    text = re.sub(r'(?<!href=&quot;mailto:)(?<!&gt;)\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b(?!&quot;&gt;)(?!&lt;/a&gt;)', replace_email, text)
    
    # Convert line breaks to <br> tags
    text = text.replace('\n', '<br>')
    
    # Add styling wrapper with better formatting
    text = f'''
    <div style="
        line-height: 1.8; 
        font-family: inherit; 
        padding: 16px; 
        background: var(--sidebar-bg); 
        border-radius: 8px; 
        border-left: 3px solid var(--primary-color);
        white-space: pre-wrap;
        color: var(--text-primary);
    ">
        {text}
    </div>
    '''
    
    return text

def extract_attachments(message):
    """Extract and process email attachments"""
    attachments = []
    if 'attachments' in message:
        for attachment in message['attachments']:
            attachment_info = {
                'filename': attachment.get('filename', 'Unknown'),
                'content_type': attachment.get('contentType', 'application/octet-stream'),
                'size': attachment.get('size', 0),
                'content': attachment.get('content', ''),
                'is_inline': attachment.get('disposition', '').lower() == 'inline'
            }
            
            # Determine if attachment can be previewed
            content_type = attachment_info['content_type'].lower()
            attachment_info['can_preview'] = content_type.startswith(('image/', 'text/', 'application/pdf'))
            
            attachments.append(attachment_info)
    
    return attachments

def process_email_content(message):
    """Process and enhance email content"""
    try:
        email_data = {
            'id': message.get('id', str(random.randint(1000, 9999))),
            'subject': message.get('subject', 'No Subject'),
            'from': message.get('from', {}).get('address', 'Unknown Sender'),
            'from_name': message.get('from', {}).get('name', ''),
            'to': message.get('to', []),
            'date': message.get('date', datetime.datetime.now().isoformat()),
            'timestamp': datetime.datetime.now().timestamp(),
            'is_read': False,
            'is_starred': False,
            'folder': 'inbox',
            'labels': [],
            'attachments': extract_attachments(message)
        }
        
        # Process email content with error handling
        try:
            html_content = message.get('html', '')
            text_content = message.get('text', '')
            
            # Check if we have HTML content or if text content looks like HTML
            has_html = bool(html_content and html_content.strip())
            text_looks_like_html = bool(text_content and ('<' in text_content and '>' in text_content))
            
            if has_html:
                email_data['html_content'] = sanitize_html_content(html_content)
                email_data['content_type'] = 'html'
                # Create preview text from HTML
                preview_text = re.sub('<[^<]+?>', '', html_content)
                email_data['preview_text'] = preview_text[:150] + '...' if len(preview_text) > 150 else preview_text
            elif text_looks_like_html:
                # Text content appears to be HTML, treat it as such
                email_data['html_content'] = sanitize_html_content(text_content)
                email_data['content_type'] = 'html'
                preview_text = re.sub('<[^<]+?>', '', text_content)
                email_data['preview_text'] = preview_text[:150] + '...' if len(preview_text) > 150 else preview_text
            else:
                # Process as plain text but convert URLs to clickable links
                processed_text = convert_urls_to_links(text_content) if text_content else 'No content'
                email_data['text_content'] = processed_text
                email_data['content_type'] = 'text'
                email_data['preview_text'] = text_content[:150] + '...' if len(text_content) > 150 else text_content
                
        except Exception as content_error:
            print(f"Error processing email content: {content_error}")
            # Fallback to text content
            fallback_content = message.get('text', message.get('html', 'No content available'))
            email_data['text_content'] = convert_urls_to_links(fallback_content)
            email_data['content_type'] = 'text'
            email_data['preview_text'] = fallback_content[:150] + '...' if len(fallback_content) > 150 else fallback_content
        
        return email_data
    except Exception as e:
        print(f"Error processing email: {e}")
        # Return minimal email data structure
        return {
            'id': str(random.randint(1000, 9999)),
            'subject': 'Error Processing Email',
            'from': 'system@error',
            'from_name': 'System',
            'to': [],
            'date': datetime.datetime.now().isoformat(),
            'timestamp': datetime.datetime.now().timestamp(),
            'is_read': False,
            'is_starred': False,
            'folder': 'inbox',
            'labels': [],
            'attachments': [],
            'text_content': f'Error processing email: {str(e)}',
            'content_type': 'text',
            'preview_text': 'Error processing email content'
        }

@app.route('/start_listening', methods=['POST'])
def start_listening():
    try:
        def listener(message):
            try:
                print(f"Raw message received: {message}")
                print(f"Message keys: {message.keys() if isinstance(message, dict) else 'Not a dict'}")
                if isinstance(message, dict):
                    print(f"HTML content present: {'html' in message}")
                    print(f"Text content present: {'text' in message}")
                    if 'html' in message:
                        print(f"HTML length: {len(message['html']) if message['html'] else 0}")
                    if 'text' in message:
                        print(f"Text length: {len(message['text']) if message['text'] else 0}")
                        print(f"Text preview: {message['text'][:200] if message['text'] else 'None'}...")
                
                email_data = process_email_content(message)
                received_emails.append(email_data)
                folders['inbox'].append(email_data['id'])
                print(f"New email processed: {email_data['subject']} (Content type: {email_data['content_type']})")
            except Exception as e:
                print(f"Error in listener: {e}")
                import traceback
                traceback.print_exc()
                # Continue listening even if one email fails to process

        email_client.start(listener, interval=1)
        return jsonify({
            "message": "Started listening for new emails",
            "success": True,
            "email": current_email
        })
    except Exception as e:
        return jsonify({"error": f"Failed to start listening: {str(e)}", "success": False}), 500

@app.route('/api/emails', methods=['GET'])
def get_emails():
    """Get emails with optional filtering and pagination"""
    folder = request.args.get('folder', 'inbox')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    
    # Filter emails by folder
    if folder == 'all':
        filtered_emails = received_emails
    else:
        email_ids = folders.get(folder, [])
        filtered_emails = [email for email in received_emails if email['id'] in email_ids]
    
    # Sort by timestamp (newest first)
    filtered_emails.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Pagination
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_emails = filtered_emails[start_idx:end_idx]
    
    return jsonify({
        "emails": paginated_emails,
        "total": len(filtered_emails),
        "page": page,
        "per_page": per_page,
        "has_more": end_idx < len(filtered_emails),
        "success": True
    })

@app.route('/api/emails/<email_id>', methods=['GET'])
def get_email_detail(email_id):
    """Get detailed view of a specific email"""
    email = next((e for e in received_emails if e['id'] == email_id), None)
    if not email:
        return jsonify({"error": "Email not found", "success": False}), 404
    
    # Mark as read
    email['is_read'] = True
    
    return jsonify({
        "email": email,
        "success": True
    })

@app.route('/api/emails/<email_id>/action', methods=['POST'])
def email_action(email_id):
    """Perform actions on emails (mark read/unread, star, delete, move)"""
    data = request.get_json()
    action = data.get('action')
    
    email = next((e for e in received_emails if e['id'] == email_id), None)
    if not email:
        return jsonify({"error": "Email not found", "success": False}), 404
    
    if action == 'mark_read':
        email['is_read'] = True
    elif action == 'mark_unread':
        email['is_read'] = False
    elif action == 'star':
        email['is_starred'] = True
    elif action == 'unstar':
        email['is_starred'] = False
    elif action == 'delete':
        # Move to trash
        for folder_name, email_list in folders.items():
            if email_id in email_list:
                email_list.remove(email_id)
        folders['trash'].append(email_id)
        email['folder'] = 'trash'
    elif action == 'move':
        target_folder = data.get('target_folder', 'inbox')
        # Remove from current folder
        for folder_name, email_list in folders.items():
            if email_id in email_list:
                email_list.remove(email_id)
        # Add to target folder
        folders[target_folder].append(email_id)
        email['folder'] = target_folder
    
    return jsonify({
        "success": True,
        "message": f"Action '{action}' completed successfully"
    })

@app.route('/api/test_email_processing', methods=['POST'])
def test_email_processing():
    """Test endpoint to debug email processing"""
    try:
        data = request.get_json()
        test_message = data.get('message', {})
        
        # Process the test message
        processed_email = process_email_content(test_message)
        
        return jsonify({
            "success": True,
            "original_message": test_message,
            "processed_email": processed_email
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/get_emails', methods=['GET'])
def get_emails_legacy():
    """Legacy endpoint for backward compatibility"""
    if not received_emails:
        return jsonify([])
    
    # Return simplified format for legacy compatibility
    legacy_format = []
    for email in received_emails:
        legacy_email = {
            "subject": email['subject'],
            "content": email.get('html_content', email.get('text_content', 'No content'))
        }
        legacy_format.append(legacy_email)
    
    return jsonify(legacy_format)

if __name__ == '__main__':
    app.run(debug=True)
