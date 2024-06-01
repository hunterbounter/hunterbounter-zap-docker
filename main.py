import json
import sys
import threading
import time
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from telemetry import get_server_stats, send_telemetry, send_scan_telemetry
from zap import (
    create_context, add_site, start_scan, scan_status, scan_results,
    get_contexts, delete_context, db_results, delete_db_results, active_scans_count, is_zap_online, get_scan_results,
    get_all_scan_results
)

app = FastAPI()


class Site(BaseModel):
    url: str
    context: Optional[str] = "Default Context"


@app.post("/create_context")
async def create_context_endpoint(context_name: str):
    return create_context(context_name)


@app.post("/add_site")
async def add_site_endpoint(site: Site):
    return add_site(site)


@app.post("/start_scan")
async def start_scan_endpoint(site: Site):
    return start_scan(site)


@app.get("/scan_status")
async def scan_status_endpoint(scan_id: str):
    return scan_status(scan_id)


@app.get("/scan_results_db")
async def scan_results_db_endpoint(url: str):
    return scan_results(url)


@app.get("/scan_results")
async def scan_results_endpoint(url: str):
    return get_scan_results(url)


@app.get("/scan_results_all")
async def scan_results_endpoint():
    return get_all_scan_results()


@app.get("/contexts")
async def get_contexts_endpoint():
    return get_contexts()


@app.delete("/delete_context")
async def delete_context_endpoint(context_name: str):
    return delete_context(context_name)


@app.get("/db_results")
async def db_results_endpoint():
    return db_results()


@app.delete("/db_results")
async def delete_db_results_endpoint():
    return delete_db_results()


@app.get("/active_scans_count")
async def active_scans_count_endpoint():
    return active_scans_count()


def telemetry_thread():
    while True:
        # check is macos
        if sys.platform == 'darwin':
            return
        server_stats = get_server_stats()
        json_stats = json.dumps(server_stats, indent=4)
        send_telemetry(json_stats)
        time.sleep(10)  # 30 Sec interval


def send_scan_results():
    while True:
        zap_is_online = is_zap_online()
        logging.info(zap_is_online)
        if zap_is_online['success']:
            send_scan_telemetry()
        time.sleep(5)  # 15 Sec interval


def zap_status():
    while True:
        context_response = is_zap_online()
        json_response = json.dumps(context_response, indent=4)
        print("Context Response: ", json_response)

        time.sleep(5)  # 30 Sec interval


if __name__ == "__main__":
    threading.Thread(target=telemetry_thread, daemon=True).start()
    threading.Thread(target=send_scan_results, daemon=True).start()
    threading.Thread(target=zap_status, daemon=True).start()

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5002)
