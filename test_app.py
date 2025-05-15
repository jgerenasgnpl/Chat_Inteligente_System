from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/api/v1/chat/test")
def test_chat():
    return {"message": "Test desde ruta directa"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)