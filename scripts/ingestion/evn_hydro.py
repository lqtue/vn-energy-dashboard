import requests
from bs4 import BeautifulSoup
import os
import sys
from datetime import datetime
import json
import csv

# Configuration
URL = "https://hochuathuydien.evn.com.vn/PageHoChuaThuyDienEmbedEVN.aspx"
LATEST_CSV = "data/processed/evn_hydro_latest.csv"
HISTORICAL_CSV = "data/processed/evn_hydro_historical.csv"

def parse_float(val):
    if not val or val.strip() == "-" or val.strip() == "":
        return None
    try:
        return float(val.strip().replace(',', '.'))
    except ValueError:
        return None

def parse_int(val):
    if not val or val.strip() == "-" or val.strip() == "":
        return None
    try:
        return int(val.strip())
    except ValueError:
        return None

def scrape():
    print(f"[{datetime.now()}] Fetching data from {URL}...")
    response = requests.get(URL, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all('table')
    
    results = []
    current_year = datetime.now().year
    
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 11:
                continue
            if cells[0].name == 'th' or cells[0].get('colspan') == '11':
                continue
            
            name_b = cells[0].find('b')
            if name_b:
                reservoir_name = name_b.text.strip()
            else:
                reservoir_name = cells[0].text.strip().split('\n')[0].strip()
            
            if not reservoir_name or "Tên hồ" in reservoir_name:
                continue

            time_str = cells[1].text.strip()
            try:
                full_time_str = f"{time_str} {current_year}"
                obs_time = datetime.strptime(full_time_str, "%d/%m %H:%M %Y").isoformat()
            except ValueError:
                try:
                    obs_time = datetime.strptime(time_str, "%d/%m/%Y %H:%M").isoformat()
                except ValueError:
                    continue
                
            results.append({
                "reservoir_name": reservoir_name,
                "observation_time": obs_time,
                "upstream_level": parse_float(cells[2].text),
                "normal_level": parse_float(cells[3].text),
                "dead_level": parse_float(cells[4].text),
                "inflow": parse_float(cells[5].text),
                "total_discharge": parse_float(cells[6].text),
                "spillway_discharge": parse_float(cells[7].text),
                "powerhouse_discharge": parse_float(cells[8].text),
                "deep_gates": parse_int(cells[9].text),
                "surface_gates": parse_int(cells[10].text)
            })
    return results

def save_to_csv(data):
    if not data: return
    os.makedirs(os.path.dirname(LATEST_CSV), exist_ok=True)
    headers = data[0].keys()
    
    with open(LATEST_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
        
    file_exists = os.path.isfile(HISTORICAL_CSV)
    existing_records = set()
    if file_exists:
        with open(HISTORICAL_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_records.add((row['reservoir_name'], row['observation_time']))

    new_records = [d for d in data if (d['reservoir_name'], d['observation_time']) not in existing_records]
    if new_records:
        with open(HISTORICAL_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            if not file_exists: writer.writeheader()
            writer.writerows(new_records)

def main():
    data = scrape()
    if data: save_to_csv(data)
    print(f"Processed {len(data)} records.")

if __name__ == "__main__":
    main()
