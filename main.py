from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, create_tables
from models import Photo, TotalPhotos
from uuid import uuid4
from datetime import datetime, timedelta
import shutil, os

# Criação das tabelas
create_tables()

app = FastAPI()

app.mount("/static", StaticFiles(directory="statics"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "statics/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def delete_old_photos():
    session = SessionLocal()
    limite = datetime.utcnow() - timedelta(hours=24)
    expiradas = session.query(Photo).filter(Photo.upload_time < limite).all()
    for foto in expiradas:
        try:
            os.remove(os.path.join(UPLOAD_DIR, foto.filename))
        except:
            pass
        session.delete(foto)
    session.commit()
    session.close()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    delete_old_photos()
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload")
async def upload_photos(request: Request, album: str = Form(...), user_name: str = Form(...), files: list[UploadFile] = Form(...)):
    session: Session = SessionLocal()
    saved_photos = []

    for file in files:
        filename = f"{uuid4()}_{file.filename}"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        photo = Photo(filename=filename, album=album, user_name=user_name)
        session.add(photo)
        saved_photos.append(photo)

    total = session.query(TotalPhotos).first()
    if not total:
        total = TotalPhotos(count=len(saved_photos))
        session.add(total)
    else:
        total.count += len(saved_photos)

    session.commit()
    session.close()

    return RedirectResponse("/galeria", status_code=302)

@app.get("/upload", response_class=HTMLResponse)
def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.get("/galeria", response_class=HTMLResponse)
def galeria(request: Request):
    session = SessionLocal()
    fotos = session.query(Photo).order_by(Photo.upload_time.desc()).all()
    total = session.query(TotalPhotos).first()
    count = total.count if total else 0
    session.close()
    return templates.TemplateResponse("galeria.html", {
        "request": request,
        "photos": fotos,
        "total_count": count
    })

@app.post("/delete/{photo_id}")
def delete_photo(photo_id: int):
    session = SessionLocal()
    photo = session.query(Photo).filter(Photo.id == photo_id).first()
    if photo:
        try:
            os.remove(os.path.join(UPLOAD_DIR, photo.filename))
        except:
            pass
        session.delete(photo)
        session.commit()
    session.close()
    return RedirectResponse("/galeria", status_code=303)

@app.get("/download/{filename}")
def download_photo(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    return FileResponse(path=file_path, filename=filename, media_type='application/octet-stream')
