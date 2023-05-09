from fastapi import FastAPI
from fastapi.responses import FileResponse
import streamlit

app = FastAPI()

@app.get("/")
async def get_root():
    return {"Hello": "World"}

@app.get("/test")
async def get_success():
    return FileResponse("alphaPage.html")

@app.get ("/javascriptTest")
async def get_javaScript():
    return ("Success :)")