import notion_client
import pandas as pd
from tqdm import tqdm
import time
import numpy as np

def add_row_to_notion(client, database_id, row):
    if row['NAF'] == "62.01A":
        domaine = "conseil en systèmes et logiciels informatiques"
    else:
        domaine = "Programmation informatique"
    
    properties = {
        "Entreprise": {"title": [{"text": {"content": row['Entreprise']}}]},
        "Siren": {"rich_text": [{"text": {"content": str(row['Siren'])}}]},
        "Code Postal": {"rich_text": [{"text": {"content": str(row['Code Postal'])}}]},
        "Dirigeant": {"rich_text": [{"text": {"content": row['Dirigeant']}}]},
        "Domaine": {"select": {"name": domaine}},
        "Linkedin": {"url": row['Linkedin'] if pd.notna(row['Linkedin']) else None},
        "Description": {"rich_text": [{"text": {"content": row['Description'] if pd.notna(row['Description']) else ""}}]},
    }
    client.pages.create(parent={"database_id": database_id}, properties=properties)

if __name__ == '__main__':
    print("Uploading data to Notion...")
    token = "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"
    database_id = "19e7dec278ad80619fa7eb921956e625"
    client = notion_client.Client(auth=token)
    df = pd.read_csv("companies.csv").replace({np.nan: None})

    for index, row in tqdm(df.iterrows(), total=len(df), desc="Uploading to Notion"):
        if row.isnull().any():
            print(f"Row {index} contains NaN values: {row}")
        try:
            add_row_to_notion(client, database_id, row)
        except notion_client.errors.APIResponseError as e:
            if e.status == 502:
                print("Rate limit exceeded. Waiting for 60 seconds...")
                time.sleep(60)
                add_row_to_notion(client, database_id, row)
            else:
                raise e
    print("Data uploaded to Notion.")