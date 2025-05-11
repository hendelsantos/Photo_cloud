import hashlib
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import os, shutil, json
from uuid import uuid4
from collections import defaultdict
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_ROOT = "static/uploads"
os.makedirs(UPLOAD_ROOT, exist_ok=True)
os.makedirs("comments", exist_ok=True)

users_file = "users.json"

def is_logged_in(request: Request):
    return "username" in request.session

def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if os.path.exists(users_file):
        with open(users_file, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(users_file, "w") as f:
        json.dump(users, f)

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    search = request.query_params.get("search")
    date = request.query_params.get("date")
    albums = defaultdict(list)
    for album in os.listdir(UPLOAD_ROOT):
        album_path = os.path.join(UPLOAD_ROOT, album)
        if os.path.isdir(album_path):
            for file in os.listdir(album_path):
                if search and search.lower() not in file.lower():
                    continue
                if date:
                    ts = os.path.getmtime(os.path.join(album_path, file))
                    from datetime import datetime
                    f_date = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                    if f_date != date:
                        continue
                if not file.endswith(".meta"):
                    meta_file = os.path.join(album_path, file + ".meta")
                    visibility = "public"
                    if os.path.exists(meta_file):
                        with open(meta_file) as m:
                            visibility = m.read().strip()
                    if visibility == "public" or request.session.get("username"):
                        albums[album].append(file)
    return templates.TemplateResponse("index.html", {"request": request, "albums": albums, "user": request.session.get("username")})

@app.get("/home", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "msg": ""})

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    users = load_users()
    if username in users and users[username] == hash_password(password):
        request.session["username"] = username
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "msg": "Credenciais inválidas"})

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "msg": ""})

@app.post("/register")
def register(request: Request, username: str = Form(...), password: str = Form(...)):
    users = load_users()
    if username in users:
        return templates.TemplateResponse("register.html", {"request": request, "msg": "Usuário já existe"})
    users[username] = hash_password(password)
    save_users(users)
    request.session["username"] = username
    return RedirectResponse("/", status_code=302)

@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload")
async def upload_file(request: Request, album: str = Form(...), visibility: str = Form(...), files: list[UploadFile] = File(...)):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    username = request.session.get("username")
    album_dir = os.path.join(UPLOAD_ROOT, album)
    os.makedirs(album_dir, exist_ok=True)
    for file in files:
        filename = f"{uuid4()}_{username}_{file.filename}"
        file_path = os.path.join(album_dir, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        with open(file_path + ".meta", "w") as meta:
            meta.write(visibility)
    return RedirectResponse("/", status_code=303)

@app.get("/perfil", response_class=HTMLResponse)
def perfil(request: Request):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    user_albums = []
    album_counts = {}
    for album in os.listdir(UPLOAD_ROOT):
        album_path = os.path.join(UPLOAD_ROOT, album)
        if os.path.isdir(album_path):
            count = len([f for f in os.listdir(album_path) if not f.endswith(".meta")])
            user_albums.append(album)
            album_counts[album] = count
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": username,
        "user_albums": user_albums,
        "album_counts": album_counts
    })

@app.get("/download/{album}", response_class=FileResponse)
def download_album(album: str, request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    album_path = os.path.join(UPLOAD_ROOT, album)
    if not os.path.isdir(album_path):
        return RedirectResponse("/", status_code=302)
    zip_filename = f"{album}.zip"
    zip_path = os.path.join("static", zip_filename)
    shutil.make_archive(os.path.splitext(zip_path)[0], 'zip', album_path)
    return FileResponse(zip_path, media_type='application/zip', filename=zip_filename)

class Comment(BaseModel):
    name: str
    message: str

@app.get("/photo/{album}/{filename}", response_class=HTMLResponse)
def view_photo(album: str, filename: str, request: Request):
    comment_file = os.path.join("comments", f"{album}_{filename}.json")
    comments = []
    if os.path.exists(comment_file):
        with open(comment_file, "r") as f:
            comments = json.load(f)
    return templates.TemplateResponse("photo.html", {
        "request": request,
        "album": album,
        "filename": filename,
        "comments": comments,
        "user": request.session.get("username")
    })

@app.post("/comment/{album}/{filename}")
def add_comment(album: str, filename: str, request: Request, message: str = Form(...)):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    comment_file = os.path.join("comments", f"{album}_{filename}.json")
    comments = []
    if os.path.exists(comment_file):
        with open(comment_file, "r") as f:
            comments = json.load(f)
    comments.append({"name": username, "message": message})
    with open(comment_file, "w") as f:
        json.dump(comments, f)
    return RedirectResponse(f"/photo/{album}/{filename}", status_code=303)

@app.get("/delete/{album}/{filename}")
def delete_photo(album: str, filename: str, request: Request):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    meta_path = os.path.join(UPLOAD_ROOT, album, filename + ".meta")
    if os.path.exists(meta_path):
        with open(meta_path, "r") as meta:
            visibility = meta.read().strip()
        if username != "admin" and username not in filename:
            return RedirectResponse("/", status_code=302)
    photo_path = os.path.join(UPLOAD_ROOT, album, filename)
    comment_path = os.path.join("comments", f"{album}_{filename}.json")
    if os.path.exists(photo_path): os.remove(photo_path)
    if os.path.exists(meta_path): os.remove(meta_path)
    if os.path.exists(comment_path): os.remove(comment_path)
    return RedirectResponse("/", status_code=302)