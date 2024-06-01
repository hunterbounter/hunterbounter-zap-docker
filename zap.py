# zap.py
import requests
import psycopg2
from fastapi import HTTPException
import logging

ZAP_BASE_URL = 'http://localhost:8080'
ZAP_API_KEY = 'your_api_key'
DB_HOST = 'localhost'
DB_NAME = 'zap_results'
DB_USER = 'zap_user'
DB_PASS = 'your_password'

logging.basicConfig(level=logging.INFO)


def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    return conn


def is_zap_online():
    try:
        response = requests.get(f'{ZAP_BASE_URL}/JSON/core/view/version/', params={'apikey': ZAP_API_KEY})
        if response.status_code == 200:
            logging.info("ZAP is online. Version: %s", response.json().get('version'))
            return {"success": True, "version": response.json().get('version')}
        else:
            logging.warning("Received unexpected status code from ZAP: %s", response.status_code)
            return {"success": False, "message": "Received unexpected status code"}
    except requests.RequestException as e:
        logging.error("Failed to connect to ZAP: %s", str(e))
        return {"success": False, "message": str(e)}


def create_context(context_name: str):
    try:
        context_response = requests.get(f'{ZAP_BASE_URL}/JSON/context/action/newContext/',
                                        params={'contextName': context_name, 'apikey': ZAP_API_KEY})
        return {"success": True, "message": f"Context '{context_name}' successfully created"}
    except:
        return {"success": False, "message": "Failed to create context"}


def add_site(site):
    target_url = site.url
    context_name = site.context

    create_context(context_name)

    access_response = requests.get(f'{ZAP_BASE_URL}/JSON/core/action/accessUrl/',
                                   params={'url': target_url, 'apikey': ZAP_API_KEY})
    if access_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to access URL in ZAP")

    include_response = requests.get(f'{ZAP_BASE_URL}/JSON/context/action/includeInContext/',
                                    params={'contextName': context_name, 'regex': f'{target_url}.*',
                                            'apikey': ZAP_API_KEY})
    if include_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to include URL in context")

    return {"success": True, "message": "Site successfully added to ZAP and included in context"}


def start_scan(site):
    target_url = site.url
    try:
        scan_response = requests.get(f'{ZAP_BASE_URL}/JSON/ascan/action/scan/',
                                     params={'url': target_url, 'apikey': ZAP_API_KEY})
        scan_response.raise_for_status()
    except:
        add_site_response = add_site(site)
        if add_site_response.get('success'):
            # URL successfully added, retry scan
            start_scan_response = start_scan(site)
            if start_scan_response.get('success'):
                return {"success": True, "message": "Scan successfully started"}

        else:
            return {"success": False, "message": "Failed to add site to ZAP"}
    return {"success": True, "message": "Scan successfully started"}


def scan_status(scan_id: str):
    status_response = requests.get(f'{ZAP_BASE_URL}/JSON/ascan/view/status/',
                                   params={'scanId': scan_id, 'apikey': ZAP_API_KEY})
    if status_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to retrieve scan status")

    return status_response.json()


def get_scan_results(url: str):
    results_response = requests.get(f'{ZAP_BASE_URL}/JSON/alert/view/alerts/',
                                    params={'baseurl': url, 'apikey': ZAP_API_KEY})
    if results_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to retrieve scan results")

    # alerts = results_response.json().get('alerts', [])
    return results_response.json()


def get_all_scan_results():
    try:
        results_response = requests.get(f'{ZAP_BASE_URL}/JSON/alert/view/alerts/', params={'apikey': ZAP_API_KEY})
        if results_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to retrieve scan results")
        return results_response.json().get('alerts', [])
    except requests.RequestException as e:
        logging.error("Failed to retrieve scan results from ZAP: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve scan results")


def scan_results(url: str):
    results_response = requests.get(f'{ZAP_BASE_URL}/JSON/alert/view/alerts/',
                                    params={'baseurl': url, 'apikey': ZAP_API_KEY})
    if results_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to retrieve scan results")

    alerts = results_response.json().get('alerts', [])
    conn = get_db_connection()
    cur = conn.cursor()

    for alert in alerts:
        cur.execute("""
            INSERT INTO scan_results (alert_id, url, risk, description, solution, other_info, reference, cwe_id, wasc_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            alert.get('id'),
            alert.get('url'),
            alert.get('risk'),
            alert.get('description'),
            alert.get('solution'),
            alert.get('otherInfo'),
            alert.get('reference'),
            alert.get('cweid'),
            alert.get('wascid')
        ))

    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Scan results saved to database"}


def get_contexts():
    contexts_response = requests.get(f'{ZAP_BASE_URL}/JSON/context/view/contexts/', params={'apikey': ZAP_API_KEY})
    if contexts_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to retrieve contexts")

    return contexts_response.json()


def delete_context(context_name: str):
    delete_response = requests.get(f'{ZAP_BASE_URL}/JSON/context/action/removeContext/',
                                   params={'contextName': context_name, 'apikey': ZAP_API_KEY})
    if delete_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to delete context")

    return {"message": f"Context '{context_name}' successfully deleted"}


def db_results():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM scan_results")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    results = []
    for row in rows:
        result = {
            "id": row[0],
            "alert_id": row[1],
            "url": row[2],
            "risk": row[3],
            "description": row[4],
            "solution": row[5],
            "other_info": row[6],
            "reference": row[7],
            "cwe_id": row[8],
            "wasc_id": row[9]
        }
        results.append(result)

    return results


def delete_db_results():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM scan_results")
    conn.commit()
    cur.close()
    conn.close()

    return {"message": "All scan results deleted from database"}


def active_scans_count():
    try:
        active_scans_response = requests.get(f'{ZAP_BASE_URL}/JSON/ascan/view/scans/', params={'apikey': ZAP_API_KEY})
    except:
        return {"success": False, "message": "Failed to retrieve active scans"}

    if active_scans_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to retrieve active scans")

    scans = active_scans_response.json().get('scans', [])
    active_scans = [scan for scan in scans if scan.get('progress') != '100']
    total_active_scans = len(active_scans)

    return {"success": True, "message": total_active_scans, "data": active_scans}
