"""
Entity Upload Controller — Flask blueprint for Excel-driven entity import.

Routes:
    GET  /entity-upload                         — upload form page
    GET  /entity-upload/template/<entity_type>  — download Excel template
    POST /entity-upload                         — process uploaded file, return JSON
"""

import logging
import os
import tempfile

from flask import Blueprint, jsonify, render_template, request, send_file

from src.application.services.data.entities.entity_upload_service import (
    ENTITY_SCHEMAS,
    generate_template,
    process_upload,
)
from src.application.services.data_service.data_service import DataService

entity_upload_bp = Blueprint("entity_upload", __name__)
logger = logging.getLogger(__name__)


@entity_upload_bp.route("/entity-upload", methods=["GET"])
def entity_upload_page():
    """Render the entity upload form."""
    entity_types = sorted(ENTITY_SCHEMAS.keys())
    return render_template("entity_upload.html", entity_types=entity_types)


@entity_upload_bp.route("/entity-upload/template/<entity_type>", methods=["GET"])
def download_template(entity_type: str):
    """
    Generate and stream an Excel template for the given entity type.
    Returns the file as an attachment download.
    """
    try:
        buf = generate_template(entity_type)
        return send_file(
            buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"{entity_type}_template.xlsx",
        )
    except ValueError as exc:
        logger.warning("Template request for unknown entity type %r: %s", entity_type, exc)
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Error generating template for %r", entity_type)
        return jsonify({"success": False, "error": str(exc)}), 500


@entity_upload_bp.route("/entity-upload", methods=["POST"])
def process_entity_upload():
    """
    Accept a multipart POST with:
        entity_type (form field) — entity type name
        file        (file field) — .xlsx file to import

    Returns JSON: {'success': bool, 'processed': int, 'errors': [...]}
    """
    entity_type = request.form.get("entity_type", "").strip()
    if not entity_type:
        return jsonify({"success": False, "error": "'entity_type' form field is required"}), 400

    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file field in request"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400

    # Save uploaded file to a temp path so DataService.load_from_excel can read it
    tmp_path = None
    try:
        suffix = os.path.splitext(file.filename or ".xlsx")[1] or ".xlsx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file.save(tmp)
            tmp_path = tmp.name

        data_service = DataService()
        df = data_service.load_from_excel(tmp_path, sheet_name="Data")
        if df is None or df.empty:
            return jsonify({"success": False, "error": "Sheet 'Data' is empty or could not be parsed"}), 400
    except Exception as exc:
        logger.warning("Failed to parse uploaded file: %s", exc)
        return jsonify({"success": False, "error": f"Could not parse Excel file: {exc}"}), 400
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    try:
        data_service = DataService()
        result = process_upload(entity_type, df, data_service.database_service.session)
        result["success"] = True
        logger.info(
            "Entity upload — type=%r processed=%d errors=%d",
            entity_type,
            result.get("processed", 0),
            len(result.get("errors", [])),
        )
        return jsonify(result)
    except Exception as exc:
        logger.exception("Error processing upload for entity type %r", entity_type)
        return jsonify({"success": False, "error": str(exc)}), 500
