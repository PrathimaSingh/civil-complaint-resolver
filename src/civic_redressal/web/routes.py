# src/my_project/web/routes.py
import os
from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename
from datetime import datetime

from civic_redressal.services.complaint_service import (
    close_complaint,
    ingest_complaints_from_csv,
    predict_complaints,
    predict_rag_complaints,
    process_new_complaint,
    process_new_complaint_rag,
)
from civic_redressal.agents.analytics.agent import run_analytics_agent

# Folders
UPLOAD_FOLDER_RESOLVED = "./resolved_complaints"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

os.makedirs(UPLOAD_FOLDER_RESOLVED, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

web_bp = Blueprint("web", __name__)

@web_bp.get("/")
def home():
    return render_template("index.html")

@web_bp.route('/upload/incoming', methods=['GET', 'POST'])
def upload_incoming():
    if request.method == 'POST':
        # Check if this is a text-based complaint
        title = request.form.get('complaint_title', '').strip()
        description = request.form.get('complaint_description', '').strip()
        image_url = request.form.get('image_url', '').strip()

        has_text = title or description
        has_file = 'file' in request.files and request.files['file'].filename
        has_url = image_url

        if not (has_file or has_url or has_text):
            flash('Please provide either an image file, image URL, or complaint text', 'error')
            return redirect(request.url)

        # Handle file upload
        filepath = ""
        if has_file:
            file = request.files['file']
            if file and allowed_file(file.filename or ""):
                filename = secure_filename(file.filename or "")
                filepath = filename
                flash(f'Image uploaded: {filename}', 'success')
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
            process_new_complaint(filepath, title, description)
            flash('Complaint processed successfully!', 'success')
        except Exception as e:
            flash(f'Processing failed: {str(e)}', 'error')

        return redirect(url_for('web.upload_incoming'))

    return render_template('upload_incoming.html')

@web_bp.route('/upload/resolved', methods=['GET', 'POST'])
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

        if file and allowed_file(file.filename or ""):
            filename = secure_filename(file.filename or "")
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

            return redirect(url_for('web.upload_resolved'))

    return render_template('upload_resolved.html')

@web_bp.get('/ingest')
def ingest_page():
    return render_template('ingest.html')


@web_bp.route('/ingest', methods=['POST'])
def run_ingest():
    csv_path = request.form.get('csv_path', '').strip()
    title_column = request.form.get('title_column', 'title').strip() or 'title'
    description_column = request.form.get('description_column', 'description').strip() or 'description'
    image_column = request.form.get('image_column', 'image_path').strip() or 'image_path'
    category_column = request.form.get('category_column', 'category').strip() or 'category'
    sub_category_column = request.form.get('sub_category_column', 'sub_category').strip() or 'sub_category'
    civic_agency_column = request.form.get('civic_agency_column', 'civic_agency').strip() or 'civic_agency'

    if not csv_path:
        flash('CSV file path is required.', 'error')
        return redirect(url_for('web.ingest_page'))

    try:
        ingest_complaints_from_csv(
            csv_path,
            title_column,
            description_column,
            image_column,
            category_column,
            sub_category_column,
            civic_agency_column,
        )
        flash('Ingestion started successfully.', 'success')
    except Exception as e:
        flash(f'Ingestion failed: {str(e)}', 'error')

    return redirect(url_for('web.ingest_page'))


@web_bp.get('/rag')
def rag_page():
    return render_template('rag.html')


@web_bp.route('/rag', methods=['POST'])
def run_rag():
    rag_input = request.form.get('rag_input', '').strip()
    if not rag_input:
        flash('Please provide a title and description.', 'error')
        return redirect(url_for('web.rag_page'))

    parts = rag_input.split('|', 2)
    if len(parts) < 2:
        flash('Expected format: <title>|<description>', 'error')
        return redirect(url_for('web.rag_page'))

    title = parts[0].strip()
    description = parts[1].strip()

    try:
        process_new_complaint_rag(title, description)
        flash('RAG complaint processing started.', 'success')
    except Exception as e:
        flash(f'RAG processing failed: {str(e)}', 'error')

    return redirect(url_for('web.rag_page'))


@web_bp.get('/ragimg')
def ragimg_page():
    return render_template('ragimg.html')


@web_bp.route('/ragimg', methods=['POST'])
def run_ragimg():
    rag_input = request.form.get('rag_input', '').strip()
    if not rag_input:
        flash('Please provide an image path, title, and description.', 'error')
        return redirect(url_for('web.ragimg_page'))

    parts = rag_input.split('|', 2)
    if len(parts) < 3:
        flash('Expected format: <image_path>|<title>|<description>', 'error')
        return redirect(url_for('web.ragimg_page'))

    image_path = parts[0].strip()
    title = parts[1].strip()
    description = parts[2].strip()

    try:
        process_new_complaint_rag(title, description, image_path)
        flash('RAG image complaint processing started.', 'success')
    except Exception as e:
        flash(f'RAG image processing failed: {str(e)}', 'error')

    return redirect(url_for('web.ragimg_page'))


@web_bp.get('/predict')
def predict_page():
    return render_template('predict.html')


@web_bp.route('/predict', methods=['POST'])
def run_prediction():
    test_file_path = request.form.get('test_file_path', '').strip()
    validation_file_path = request.form.get('validation_file_path', '').strip()
    mode = request.form.get('mode', 'predict').strip()

    if not test_file_path or not validation_file_path:
        flash('Both test and validation CSV file paths are required.', 'error')
        return redirect(url_for('web.predict_page'))

    try:
        if mode == 'predict_rag':
            predict_rag_complaints(test_file_path, validation_file_path)
        else:
            predict_complaints(test_file_path, validation_file_path)
        flash(f'Prediction started for {mode}.', 'success')
    except Exception as e:
        flash(f'Prediction failed: {str(e)}', 'error')

    return redirect(url_for('web.predict_page'))


@web_bp.get('/analytics')
def analytics():
    try:
        # Call run_analytics_agent to get fresh analytics
        result = run_analytics_agent({"image_path": ""})
        analytics_data = result.get("analytics", {})

        # Safety: Convert defaultdict to normal dict if needed
        if isinstance(analytics_data.get("by_complaint_type"), dict):
            analytics_data["by_complaint_type"] = dict(analytics_data["by_complaint_type"])
        if isinstance(analytics_data.get("by_complaint_subtype"), dict):
            analytics_data["by_complaint_subtype"] = dict(analytics_data["by_complaint_subtype"])
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