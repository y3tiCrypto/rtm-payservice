from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    # RPC
    rpc_host: str = "127.0.0.1"
    rpc_port: int = 8766
    rpc_user: str
    rpc_password: str

    # Database (MySQL)
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "raptoreumpay"

    # ZeroMQ (ZMQ) Blockchain Integration
    zmq_enabled: bool = False
    zmq_host: str = "127.0.0.1"
    zmq_port: int = 28332

    # App
    secret_key: str
    base_url: str = "http://localhost:8000"

    # Admin (very basic for MVP)
    admin_username: str = "admin"
    admin_password: str = "change_me"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()