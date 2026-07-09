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

# Stateless Helper: Get Mail.tm client from Authorization header or token query arg
def get_client_from_request():
    token = request.headers.get('Authorization')
    if token and token.startswith('Bearer '):
        token = token.split(' ')[1]
        
    if not token:
        token = request.args.get('token')
    
    if not token:
        return None
        
    client = Email()
    client.token = token
    client.session.headers.update({'Authorization': f'Bearer {token}'})
    return client

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current application status (stateless)"""
    client = get_client_from_request()
    if not client:
        return jsonify({"error": "Unauthorized", "success": False}), 401
    
    try:
        me = client.session.get('https://api.mail.tm/me').json()
        domain = me.get('address', '').split('@')[-1] if '@' in me.get('address', '') else ''
        return jsonify({
            "current_email": me.get('address'),
            "domain": domain,
            "success": True
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get status: {str(e)}", "success": False}), 500

@app.route('/get_domains', methods=['GET'])
def get_domains():
    try:
        temp_client = Email()
        url = "https://api.mail.tm/domains"
        response = temp_client.session.get(url)
        response.raise_for_status()
        data = response.json()
        domains = [d['domain'] for d in data.get('hydra:member', []) if d.get('isActive')]
        return jsonify({"domains": domains, "success": True})
    except Exception as e:
        return jsonify({"error": f"Failed to fetch domains: {str(e)}", "success": False}), 500

@app.route('/register_email', methods=['POST'])
def register_email():
    try:
        data = request.get_json()
        email_prefix = data.get("email_prefix", "").strip()
        domain = data.get("domain", "").strip()

        if not email_prefix:
            return jsonify({"error": "Email prefix is required.", "success": False}), 400

        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
        username = email_prefix + random_suffix
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        
        temp_client = Email()
        temp_client.register(username=username, password=password, domain=domain if domain else None)
        address = temp_client.address
            
        return jsonify({
            "email": address,
            "password": password,
            "token": temp_client.token,
            "success": True,
            "message": f"Email {address} successfully registered"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to register email: {str(e)}", "success": False}), 500

@app.route('/login_email', methods=['POST'])
def login_email():
    try:
        data = request.get_json()
        address = data.get("email", "").strip()
        password = data.get("password", "").strip()

        if not address or not password:
            return jsonify({"error": "Email and password are required.", "success": False}), 400

        temp_client = Email()
        temp_client.address = address
        temp_client.get_token(password)

        return jsonify({
            "email": address,
            "password": password,
            "token": temp_client.token,
            "success": True,
            "message": f"Successfully logged into {address}"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to login: {str(e)}", "success": False}), 500

@app.route('/copy_email', methods=['POST'])
def copy_email():
    inbox_id = request.headers.get('X-Inbox-Id')
    if inbox_id:
        return jsonify({
            "message": "Email copied to clipboard!", 
            "email": inbox_id,
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
            protocols=['http', 'https', 'mailto', 'data', 'cid'],
            css_sanitizer=css_sanitizer,
            strip=True
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
                'id': attachment.get('id', ''),
                'filename': attachment.get('filename', 'Unknown'),
                'content_type': attachment.get('contentType', 'application/octet-stream'),
                'size': attachment.get('size', 0),
                'content': attachment.get('content', ''),
                'downloadUrl': attachment.get('downloadUrl', ''),
                'is_inline': attachment.get('disposition', '').lower() == 'inline',
                'content_id': attachment.get('contentId', '').strip('<>') if attachment.get('contentId') else None
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
            if isinstance(html_content, list):
                html_content = '\n'.join(html_content)
                
            text_content = message.get('text', '')
            if isinstance(text_content, list):
                text_content = '\n'.join(text_content)
            
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

@app.route('/api/emails', methods=['GET'])
def get_emails():
    """Get emails list from mail.tm (stateless)"""
    client = get_client_from_request()
    if not client:
        return jsonify({"error": "Unauthorized", "success": False}), 401
        
    page = int(request.args.get('page', 1))
    
    try:
        resp = client.session.get('https://api.mail.tm/messages', params={'page': page})
        if resp.status_code != 200:
            return jsonify({"error": "Failed to fetch messages", "success": False}), resp.status_code
            
        data = resp.json()
        messages = data.get('hydra:member', [])
        total = data.get('hydra:totalItems', len(messages))
        
        mapped_emails = []
        for m in messages:
            mapped_emails.append({
                'id': m['id'],
                'subject': m.get('subject', 'No Subject'),
                'from_name': m.get('from', {}).get('name', ''),
                'from': m.get('from', {}).get('address', ''),
                'to': [t.get('address', '') for t in m.get('to', [])],
                'date': m.get('createdAt', ''),
                'timestamp': datetime.datetime.fromisoformat(m.get('createdAt', '').replace('Z', '+00:00')).timestamp() if m.get('createdAt') else 0,
                'is_read': m.get('seen', False),
                'preview_text': m.get('intro', ''),
                'has_attachments': m.get('hasAttachments', False),
                'folder': 'inbox'
            })
            
        return jsonify({
            "emails": mapped_emails,
            "total": total,
            "page": page,
            "has_more": "hydra:view" in data and "hydra:next" in data["hydra:view"],
            "success": True
        })
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/api/emails/<email_id>', methods=['GET'])
def get_email_detail(email_id):
    """Fetch full email on demand and sanitize"""
    client = get_client_from_request()
    if not client:
        return jsonify({"error": "Unauthorized", "success": False}), 401
        
    try:
        resp = client.session.get(f'https://api.mail.tm/messages/{email_id}')
        if resp.status_code != 200:
            return jsonify({"error": "Email not found", "success": False}), resp.status_code
            
        full_msg = resp.json()
        email_data = process_email_content(full_msg)
        
        # Mark as read
        client.session.patch(f'https://api.mail.tm/messages/{email_id}', json={'seen': True})
        email_data['is_read'] = True
        
        return jsonify({
            "email": email_data,
            "success": True
        })
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/api/emails/<email_id>/action', methods=['POST'])
def email_action(email_id):
    """Perform actions on emails directly on mail.tm"""
    client = get_client_from_request()
    if not client:
        return jsonify({"error": "Unauthorized", "success": False}), 401
        
    data = request.get_json()
    action = data.get('action')
    
    try:
        if action == 'delete':
            response = client.session.delete(f"https://api.mail.tm/messages/{email_id}")
            response.raise_for_status()
            return jsonify({"success": True, "message": "Email permanently deleted"})
        elif action == 'mark_read':
            client.session.patch(f"https://api.mail.tm/messages/{email_id}", json={'seen': True})
            return jsonify({"success": True})
        elif action == 'mark_unread':
            client.session.patch(f"https://api.mail.tm/messages/{email_id}", json={'seen': False})
            return jsonify({"success": True})
        else:
            return jsonify({"success": True, "message": f"Action '{action}' simulated (not supported by API)"})
    except Exception as e:
        return jsonify({"error": f"Failed to perform action: {str(e)}", "success": False}), 500

@app.route('/api/emails/<email_id>/attachments/<attachment_id>', methods=['GET'])
def download_attachment(email_id, attachment_id):
    client = get_client_from_request()
    if not client:
        return jsonify({"error": "Unauthorized", "success": False}), 401
    
    try:
        msg_resp = client.session.get(f"https://api.mail.tm/messages/{email_id}")
        if msg_resp.status_code != 200:
            return jsonify({"error": "Email not found", "success": False}), 404
            
        full_msg = msg_resp.json()
        attachment = next((a for a in full_msg.get('attachments', []) if a['id'] == attachment_id), None)
        
        if not attachment:
            return jsonify({"error": "Attachment not found", "success": False}), 404
            
        download_url = attachment.get('downloadUrl')
        url = f"https://api.mail.tm{download_url}"
        
        response = client.session.get(url)
        response.raise_for_status()
        
        from flask import Response
        return Response(
            response.content,
            mimetype=attachment.get('contentType', 'application/octet-stream'),
            headers={
                "Content-Disposition": f'attachment; filename="{attachment.get("name", "download")}"'
            }
        )
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

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
    """Legacy endpoint for backward compatibility (stateless)"""
    client = get_client_from_request()
    if not client:
        return jsonify([])
    try:
        resp = client.session.get('https://api.mail.tm/messages', params={'page': 1})
        if resp.status_code != 200:
            return jsonify([])
        return jsonify([{ "subject": m.get('subject', ''), "content": m.get('intro', '') } for m in resp.json().get('hydra:member', [])])
    except:
        return jsonify([])

if __name__ == '__main__':
    app.run(debug=True)
