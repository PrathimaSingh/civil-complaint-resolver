# flask_App.py - Flask Web Dashboard with Beautiful Analytics
from flask import Flask, render_template, request, redirect, url_for, flash
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename

# Import your main resolver functions
from civil_complaint_resolver import process_new_complaint, close_complaint, tracker_node

app = Flask(__name__)
app.secret_key = "civil_complaint_secret_key_2026"

# Folders
UPLOAD_FOLDER_INCOMING = "./incoming_complaints"
UPLOAD_FOLDER_RESOLVED = "./resolved_complaints"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

os.makedirs(UPLOAD_FOLDER_INCOMING, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_RESOLVED, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ====================== ROUTES ======================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload/incoming', methods=['GET', 'POST'])
def upload_incoming():
    if request.method == 'POST':
        # Check if this is a text-based complaint
        complaint_title = request.form.get('complaint_title', '').strip()
        complaint_description = request.form.get('complaint_description', '').strip()
        image_url = request.form.get('image_url', '').strip()

        has_text = complaint_title or complaint_description
        has_file = 'file' in request.files and request.files['file'].filename
        has_url = image_url

        if not (has_file or has_url or has_text):
            flash('Please provide either an image file, image URL, or complaint text', 'error')
            return redirect(request.url)

        # Handle file upload
        filepath = ""
        if has_file:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name, ext = os.path.splitext(filename)
                new_filename = f"{name}_{timestamp}{ext}"

                filepath = os.path.join(UPLOAD_FOLDER_INCOMING, new_filename)
                file.save(filepath)
                flash(f'Image uploaded: {new_filename}', 'success')
            else:
                flash('Invalid file type', 'error')
                return redirect(request.url)
        elif has_url:
            # Use URL as filepath
            filepath = image_url
            flash(f'Using image URL: {image_url}', 'success')
        else:
            # Text-only complaint, use empty string for image_path
            filepath = ""

        try:
            process_new_complaint(filepath, complaint_title, complaint_description)
            flash('Complaint processed successfully!', 'success')
        except Exception as e:
            flash(f'Processing failed: {str(e)}', 'error')

        return redirect(url_for('upload_incoming'))

    return render_template('upload_incoming.html')

@app.route('/upload/resolved', methods=['GET', 'POST'])
def upload_resolved():
    if request.method == 'POST':
        complaint_id = request.form.get('complaint_id', '').strip()
        if not complaint_id:
            flash('Complaint ID is required', 'error')
            return redirect(request.url)

        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"resolved_{complaint_id}_{timestamp}{os.path.splitext(filename)[1]}"
            
            filepath = os.path.join(UPLOAD_FOLDER_RESOLVED, new_filename)
            file.save(filepath)

            flash(f'Resolved image uploaded: {new_filename}', 'success')

            try:
                close_complaint(complaint_id, filepath)
                flash(f'Complaint {complaint_id} closed successfully!', 'success')
            except Exception as e:
                flash(f'Image uploaded but closing failed: {str(e)}', 'warning')

            return redirect(url_for('upload_resolved'))

    return render_template('upload_resolved.html')

@app.route('/analytics')
def analytics():
    try:
        # Call tracker_node to get fresh analytics
        result = tracker_node({"image_path": ""})
        analytics_data = result.get("analytics", {})

        # Safety: Convert defaultdict to normal dict if needed
        if isinstance(analytics_data.get("by_complaint_type"), dict):
            analytics_data["by_complaint_type"] = dict(analytics_data["by_complaint_type"])
        if isinstance(analytics_data.get("by_category"), dict):
            analytics_data["by_category"] = dict(analytics_data["by_category"])
        if isinstance(analytics_data.get("by_authority"), dict):
            analytics_data["by_authority"] = dict(analytics_data["by_authority"])

        return render_template('analytics.html', 
                             analytics=analytics_data,
                             now=datetime.now().strftime("%d %b %Y, %H:%M"))

    except Exception as e:
        print(f"Analytics Error: {e}")   # For debugging
        flash(f'Error generating analytics: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    print("🚀 Civil Complaint Resolver Web Dashboard Started")
    print("Open browser → http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)