import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime

from pdf_ops.tools import (
    merge_pdfs, split_pdf, compress_pdf,
    protect_pdf, unlock_pdf, rotate_pdf, watermark_pdf,
    sign_pdf_with_image, extract_text, pdf_to_docx,
    pdf_to_images, images_to_pdf, office_to_pdf, 
    extract_images, pdf_to_excel, pdf_to_html, pdf_ocr,
    reorder_pages,UPLOADS, OUTPUTS
)
import threading, time, zipfile
from uuid import uuid4


progress = {}  # track progress per task
ALLOWED_PDF = {"pdf"}
ALLOWED_IMAGES = {"png", "jpg", "jpeg"}
ALLOWED_OFFICE = {"doc", "docx", "xls", "xlsx", "ppt", "pptx"}

app = Flask(__name__)
app.secret_key = "supersecretkey"
os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(OUTPUTS, exist_ok=True)

# --- Async task registry ---
TASKS = {}  # task_id -> dict(status, progress, output, error)
# progress: 0..100, or -1 for error
# status: 'running' | 'done' | 'error'

def is_ajax(req):
    return req.headers.get("X-Requested-With") == "XMLHttpRequest"

def _heartbeat(task_id, stop_event):
    """Increment progress gently up to 95% while the job is running."""
    while not stop_event.is_set():
        t = TASKS.get(task_id)
        if not t: break
        cur = t.get("progress", 0)
        if t.get("status") == "running" and cur < 95:
            TASKS[task_id]["progress"] = min(95, cur + 2)  # smooth climb
        time.sleep(0.25)

def _package_if_list(task_id, out):
    """If tool returns multiple files (list), zip them and return the zip path."""
    if isinstance(out, (list, tuple)):
        zip_path = os.path.join(OUTPUTS, f"{task_id}.zip")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fp in out:
                # ensure the file is in OUTPUTS or accessible
                arcname = os.path.basename(fp)
                zf.write(fp, arcname)
        return zip_path
    return out

def run_async(task_id, func, *args, **kwargs):
    """Run a tool function in the background; update TASKS[task_id]."""
    stop_event = threading.Event()
    TASKS[task_id] = {"status": "running", "progress": 0, "output": None, "error": None}

    def worker():
        hb = threading.Thread(target=_heartbeat, args=(task_id, stop_event), daemon=True)
        hb.start()
        try:
            result = func(*args, **kwargs)  # your existing tool function (blocking)
            result = _package_if_list(task_id, result)
            TASKS[task_id]["output"] = os.path.basename(result) if result else None
            TASKS[task_id]["progress"] = 100
            TASKS[task_id]["status"] = "done"
        except Exception as e:
            TASKS[task_id]["status"] = "error"
            TASKS[task_id]["progress"] = -1
            TASKS[task_id]["error"] = str(e)
        finally:
            stop_event.set()

    threading.Thread(target=worker, daemon=True).start()

@app.route("/progress/<task_id>")
def task_progress(task_id):
    t = TASKS.get(task_id, {"status": "unknown", "progress": 0})
    resp = {"status": t.get("status"), "progress": t.get("progress", 0)}
    if t.get("status") == "done" and t.get("output"):
        resp["download_url"] = url_for("download", filename=t["output"])
    if t.get("status") == "error":
        resp["error"] = t.get("error")
    return jsonify(resp)

def allowed(filename, exts):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in exts

@app.route("/")
def home():
    return render_template("index.html")

# -------- Generic download --------
@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(OUTPUTS, filename, as_attachment=True)

# -------- Merge --------
# -------- Merge --------
@app.route("/merge", methods=["GET", "POST"])
def merge():
    if request.method == "POST":
        files = request.files.getlist("files")
        paths = []
        for f in files:
            if f and allowed(f.filename, ALLOWED_PDF):
                p = os.path.join(UPLOADS, secure_filename(f.filename))
                f.save(p); paths.append(p)
        if not paths:
            flash("Please upload at least one PDF.")
            return redirect(request.url)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, merge_pdfs, paths)  # list is passed as single arg
            return jsonify({"task_id": task_id})
        else:
            out = merge_pdfs(paths)
            return render_template("result_single.html", file=os.path.basename(out))

    return render_template("tool_upload.html", title="Merge PDF", multiple=True, accept=".pdf")

# -------- Split --------
@app.route("/split", methods=["GET", "POST"])
def split():
    if request.method == "POST":
        f = request.files.get("file")
        if not f or not allowed(f.filename, ALLOWED_PDF):
            flash("Please upload a PDF."); return redirect(request.url)
        p = os.path.join(UPLOADS, secure_filename(f.filename)); f.save(p)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, split_pdf, p)  # returns list -> zipped for AJAX
            return jsonify({"task_id": task_id})
        else:
            outs = split_pdf(p)
            return render_template("result_links.html", files=[os.path.basename(x) for x in outs], title="Split Result")

    return render_template("tool_upload.html", title="Split PDF", accept=".pdf")

# -------- Compress --------
@app.route("/compress", methods=["GET", "POST"])
def compress():
    if request.method == "POST":
        f = request.files.get("file")
        quality = request.form.get("quality", "screen")
        if not f or not allowed(f.filename, ALLOWED_PDF):
            flash("Please upload a PDF."); return redirect(request.url)
        p = os.path.join(UPLOADS, secure_filename(f.filename)); f.save(p)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, compress_pdf, p, quality=quality)
            return jsonify({"task_id": task_id})
        else:
            out = compress_pdf(p, quality=quality)
            return render_template("result_single.html", file=os.path.basename(out))

    return render_template("tool_upload.html", title="Compress PDF", accept=".pdf", extra_controls="""
    <label class='lbl'>Quality</label>
    <select name="quality" class="input">
      <option value="screen">Small (screen)</option>
      <option value="ebook">eBook</option>
      <option value="printer">Printer</option>
      <option value="prepress">Prepress</option>
    </select>
    """)

# -------- PDF to Word --------
@app.route("/pdf-to-word", methods=["GET", "POST"])
def pdf_to_word():
    if request.method == "POST":
        f = request.files.get("file")
        if not f or not allowed(f.filename, ALLOWED_PDF):
            flash("Please upload a PDF."); return redirect(request.url)
        p = os.path.join(UPLOADS, secure_filename(f.filename)); f.save(p)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, pdf_to_docx, p)
            return jsonify({"task_id": task_id})
        else:
            out = pdf_to_docx(p)
            return render_template("result_single.html", file=os.path.basename(out))

    return render_template("tool_upload.html", title="PDF to Word", accept=".pdf")

# -------- PDF to Images --------
@app.route("/pdf-to-images", methods=["GET", "POST"])
def pdf_to_images_route():
    if request.method == "POST":
        f = request.files.get("file")
        fmt = request.form.get("fmt", "png")
        if not f or not allowed(f.filename, ALLOWED_PDF):
            flash("Please upload a PDF."); return redirect(request.url)
        p = os.path.join(UPLOADS, secure_filename(f.filename)); f.save(p)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, pdf_to_images, p, fmt=fmt)  # list -> zipped
            return jsonify({"task_id": task_id})
        else:
            outs = pdf_to_images(p, fmt=fmt)
            return render_template("result_links.html", files=[os.path.basename(x) for x in outs], title="PDF to Images")

    return render_template("tool_upload.html", title="PDF to Images", accept=".pdf", extra_controls="""
    <label class='lbl'>Format</label>
    <select name="fmt" class="input">
      <option value="png">PNG</option>
      <option value="jpg">JPG</option>
    </select>
    """)

# -------- Images to PDF --------
@app.route("/images-to-pdf", methods=["GET", "POST"])
def images_to_pdf_route():
    if request.method == "POST":
        files = request.files.getlist("files")
        paths = []
        for f in files:
            if f and allowed(f.filename, ALLOWED_IMAGES):
                p = os.path.join(UPLOADS, secure_filename(f.filename)); f.save(p); paths.append(p)
        if not paths:
            flash("Upload JPG/PNG images."); return redirect(request.url)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, images_to_pdf, paths)
            return jsonify({"task_id": task_id})
        else:
            out = images_to_pdf(paths)
            return render_template("result_single.html", file=os.path.basename(out))

    return render_template("tool_upload.html", title="Images to PDF", multiple=True, accept=".png,.jpg,.jpeg")

# -------- Office to PDF (Word/Excel/PowerPoint) --------
@app.route("/office-to-pdf", methods=["GET", "POST"])
def office_to_pdf_route():
    if request.method == "POST":
        f = request.files.get("file")
        if not f or not allowed(f.filename, ALLOWED_OFFICE):
            flash("Upload DOCX/XLSX/PPTX."); return redirect(request.url)
        p = os.path.join(UPLOADS, secure_filename(f.filename)); f.save(p)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, office_to_pdf, p)
            return jsonify({"task_id": task_id})
        else:
            try:
                out = office_to_pdf(p)
                return render_template("result_single.html", file=os.path.basename(out))
            except Exception as e:
                flash(str(e)); return redirect(request.url)

    return render_template("tool_upload.html", title="Office to PDF", accept=".doc,.docx,.xls,.xlsx,.ppt,.pptx")

# -------- Watermark --------
@app.route("/watermark", methods=["GET", "POST"])
def watermark():
    if request.method == "POST":
        pdf = request.files.get("file")
        wm = request.files.get("watermark")
        if not pdf or not allowed(pdf.filename, ALLOWED_PDF):
            flash("Upload a PDF."); return redirect(request.url)
        if not wm or not allowed(wm.filename, ALLOWED_PDF):
            flash("Upload a watermark PDF (single page)."); return redirect(request.url)
        p1 = os.path.join(UPLOADS, secure_filename(pdf.filename)); pdf.save(p1)
        p2 = os.path.join(UPLOADS, secure_filename(wm.filename)); wm.save(p2)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, watermark_pdf, p1, p2)
            return jsonify({"task_id": task_id})
        else:
            out = watermark_pdf(p1, p2)
            return render_template("result_single.html", file=os.path.basename(out))

    return render_template("tool_upload.html", title="Watermark PDF", accept=".pdf", extra_controls="""
    <label class="lbl upload-label">Watermark PDF</label>

    <div class="file-upload-container">
    <input type="file" name="watermark" id="watermarkInput" accept=".pdf" hidden required>

    <!-- Cyberpunk Choose File Button -->
    <label for="watermarkInput" class="cyberpunk-btn" data-text="Choose File">
        <span class="btn-text">Choose File</span>
    </label>

    <!-- Selected Filename (Centered Below Button) -->
    <span id="watermark-file-name" class="file-name">No file selected</span>
    </div>

    <script>
    document.getElementById('watermarkInput').addEventListener('change', function() {
    const fileName = this.files.length > 0 ? this.files[0].name : 'No file selected';
    document.getElementById('watermark-file-name').textContent = fileName;
    });
    </script>
    """)

# -------- Rotate --------
@app.route("/rotate", methods=["GET", "POST"])
def rotate():
    if request.method == "POST":
        f = request.files.get("file")
        angle = int(request.form.get("angle", "90"))
        if not f or not allowed(f.filename, ALLOWED_PDF):
            flash("Upload a PDF."); return redirect(request.url)
        p = os.path.join(UPLOADS, secure_filename(f.filename)); f.save(p)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, rotate_pdf, p, angle=angle)
            return jsonify({"task_id": task_id})
        else:
            out = rotate_pdf(p, angle=angle)
            return render_template("result_single.html", file=os.path.basename(out))

    return render_template("tool_upload.html", title="Rotate PDF", accept=".pdf", extra_controls="""
    <label class='lbl'>Angle</label>
    <select name="angle" class="input">
      <option value="90">90°</option>
      <option value="180">180°</option>
      <option value="270">270°</option>
    </select>
    """)

# -------- Protect / Unlock --------
@app.route("/protect", methods=["GET", "POST"])
def protect():
    if request.method == "POST":
        f = request.files.get("file")
        pwd = request.form.get("password", "")
        if not f or not allowed(f.filename, ALLOWED_PDF):
            flash("Upload a PDF."); return redirect(request.url)
        if not pwd:
            flash("Enter a password."); return redirect(request.url)
        p = os.path.join(UPLOADS, secure_filename(f.filename)); f.save(p)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, protect_pdf, p, pwd)
            return jsonify({"task_id": task_id})
        else:
            out = protect_pdf(p, pwd)
            return render_template("result_single.html", file=os.path.basename(out))

    return render_template("tool_upload.html", title="Protect PDF", accept=".pdf", extra_controls="""
    <label class='lbl'>Password</label>
    <input type="password" name="password" required class="input">
    """)

@app.route("/unlock", methods=["GET", "POST"])
def unlock():
    if request.method == "POST":
        f = request.files.get("file")
        pwd = request.form.get("password", "")
        if not f or not allowed(f.filename, ALLOWED_PDF):
            flash("Upload a PDF."); return redirect(request.url)
        p = os.path.join(UPLOADS, secure_filename(f.filename)); f.save(p)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, unlock_pdf, p, pwd)
            return jsonify({"task_id": task_id})
        else:
            try:
                out = unlock_pdf(p, pwd)
                return render_template("result_single.html", file=os.path.basename(out))
            except Exception as e:
                flash(str(e)); return redirect(request.url)

    return render_template("tool_upload.html", title="Unlock PDF", accept=".pdf", extra_controls="""
    <label class='lbl'>Password</label>
    <input type="password" name="password" required class="input">
    """)


# -------- Extract Text --------
@app.route("/extract-text", methods=["GET", "POST"])
def extract_text_route():
    if request.method == "POST":
        f = request.files.get("file")
        if not f or not allowed(f.filename, ALLOWED_PDF):
            flash("Upload a PDF."); return redirect(request.url)
        p = os.path.join(UPLOADS, secure_filename(f.filename)); f.save(p)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, extract_text, p)
            return jsonify({"task_id": task_id})
        else:
            out = extract_text(p)
            return render_template("result_single.html", file=os.path.basename(out))

    return render_template("tool_upload.html", title="Extract Text", accept=".pdf")

# -------- Sign (image) --------
@app.route("/sign", methods=["GET", "POST"])
def sign():
    if request.method == "POST":
        pdf = request.files.get("file")
        img = request.files.get("image")
        scale = float(request.form.get("scale", "0.25"))
        if not pdf or not allowed(pdf.filename, ALLOWED_PDF):
            flash("Upload a PDF."); return redirect(request.url)
        if not img or not allowed(img.filename, ALLOWED_IMAGES):
            flash("Upload a PNG/JPG signature image."); return redirect(request.url)
        p1 = os.path.join(UPLOADS, secure_filename(pdf.filename)); pdf.save(p1)
        p2 = os.path.join(UPLOADS, secure_filename(img.filename)); img.save(p2)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, sign_pdf_with_image, p1, p2, scale=scale)
            return jsonify({"task_id": task_id})
        else:
            out = sign_pdf_with_image(p1, p2, scale=scale)
            return render_template("result_single.html", file=os.path.basename(out))

    return render_template("tool_upload.html", title="Sign PDF", accept=".pdf", extra_controls="""
    <label class="lbl upload-label">Signature image (PNG/JPG)</label>

    <div class="file-upload-container">
        <input type="file" name="image" id="signatureInput" accept=".png,.jpg,.jpeg" hidden required>
        
        <!-- Cyberpunk Choose File Button -->
        <label for="signatureInput" class="cyberpunk-btn" data-text="Choose Image">
        <span class="btn-text">Choose Image</span>
        </label>

        <!-- Selected Filename (Centered Below Button) -->
        <span id="signature-file-name" class="file-name">No file selected</span>
    </div>

    <label class="lbl upload-label">Size (page width fraction)</label>
    <input type="number" name="scale" min="0.1" max="0.5" step="0.05" value="0.25" class="input">
    """)

# -------- Extract Images --------
@app.route("/extract-images", methods=["GET", "POST"])
def extract_images_route():
    if request.method == "POST":
        f = request.files.get("file")
        if not f or not allowed(f.filename, ALLOWED_PDF):
            flash("Upload a PDF."); return redirect(request.url)
        p = os.path.join(UPLOADS, secure_filename(f.filename))
        f.save(p)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, extract_images, p)  # returns list -> zipped
            return jsonify({"task_id": task_id})
        else:
            outs = extract_images(p)
            return render_template("result_links.html",
                                   files=[os.path.basename(x) for x in outs],
                                   title="Extracted Images")

    return render_template("tool_upload.html", title="Extract Images", accept=".pdf")


# -------- PDF to Excel --------
@app.route("/pdf-to-excel", methods=["GET", "POST"])
def pdf_to_excel_route():
    if request.method == "POST":
        f = request.files.get("file")
        if not f or not allowed(f.filename, ALLOWED_PDF):
            flash("Upload a PDF."); return redirect(request.url)
        p = os.path.join(UPLOADS, secure_filename(f.filename))
        f.save(p)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, pdf_to_excel, p)
            return jsonify({"task_id": task_id})
        else:
            out = pdf_to_excel(p)
            return render_template("result_single.html", file=os.path.basename(out))

    return render_template("tool_upload.html", title="PDF to Excel", accept=".pdf")


# -------- PDF to HTML --------
@app.route("/pdf-to-html", methods=["GET", "POST"])
def pdf_to_html_route():
    if request.method == "POST":
        f = request.files.get("file")
        if not f or not allowed(f.filename, ALLOWED_PDF):
            flash("Upload a PDF."); return redirect(request.url)
        p = os.path.join(UPLOADS, secure_filename(f.filename))
        f.save(p)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, pdf_to_html, p)
            return jsonify({"task_id": task_id})
        else:
            out = pdf_to_html(p)
            return render_template("result_single.html", file=os.path.basename(out))

    return render_template("tool_upload.html", title="PDF to HTML", accept=".pdf")


# -------- OCR PDF --------
@app.route("/pdf-ocr", methods=["GET", "POST"])
def pdf_ocr_route():
    if request.method == "POST":
        f = request.files.get("file")
        lang = request.form.get("lang", "eng")
        if not f or not allowed(f.filename, ALLOWED_PDF):
            flash("Upload a scanned PDF."); return redirect(request.url)
        p = os.path.join(UPLOADS, secure_filename(f.filename))
        f.save(p)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, pdf_ocr, p, lang=lang)
            return jsonify({"task_id": task_id})
        else:
            out = pdf_ocr(p, lang=lang)
            return render_template("result_single.html", file=os.path.basename(out))

    return render_template("tool_upload.html", title="OCR PDF", accept=".pdf", extra_controls="""
    <label class='lbl'>Language</label>
    <input type="text" name="lang" value="eng" class="input" placeholder="eng, deu, fra, ...">
    """)


# -------- Reorder Pages --------
@app.route("/reorder-pages", methods=["GET", "POST"])
def reorder_pages_route():
    if request.method == "POST":
        f = request.files.get("file")
        new_order = request.form.get("order", "")
        if not f or not allowed(f.filename, ALLOWED_PDF):
            flash("Upload a PDF."); return redirect(request.url)
        if not new_order:
            flash("Enter new page order (e.g., 2,1,3)").strip()
            return redirect(request.url)

        p = os.path.join(UPLOADS, secure_filename(f.filename))
        f.save(p)
        try:
            order_list = [int(x.strip()) for x in new_order.split(",") if x.strip().isdigit()]
        except:
            flash("Invalid order format."); return redirect(request.url)

        if is_ajax(request):
            task_id = uuid4().hex
            run_async(task_id, reorder_pages, p, order_list)
            return jsonify({"task_id": task_id})
        else:
            out = reorder_pages(p, order_list)
            return render_template("result_single.html", file=os.path.basename(out))

    return render_template("tool_upload.html", title="Reorder Pages", accept=".pdf", extra_controls="""
    <label class='lbl'>New Order (comma separated, e.g. 2,1,3)</label>
    <input type="text" name="order" required class="input">
    """)


@app.context_processor
def inject_year():
    # This makes {{ current_year }} available in all templates
    return {'current_year': datetime.now().year}

if __name__ == "__main__":
    app.run(debug=True)
