from fastapi import FastAPI

app = FastAPI(
    title="GovTech Transparência API",
    description="API gamificada de auditoria política",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": "Bem-vindo à API GovTech Transparência!"}
