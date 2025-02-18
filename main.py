import requests
import pandas as pd
from duckduckgo_search import DDGS
import time


def fetch_company_names(naf, department, pages=10):
    data = []
    for page in range(1, pages):
        url = f"https://recherche-entreprises.api.gouv.fr/search?departement={department}&activite_principale={naf}&page={page}&per_page=25&categorie_entreprise=PME"
        response = requests.get(url)
        response_data = response.json()
        for company in response_data['results']:
            nom = company['nom_complet']
            code = company['matching_etablissements'][0]['code_postal']
            nature = company['nature_juridique']
            siren = company['siren']
            if int(nature) != 1000:
                try:
                    dirigent = company['dirigeants'][0]['nom'] + ' ' + company['dirigeants'][0]['prenoms']
                    data.append([nom,siren ,code, dirigent,naf])
                except:
                    pass
    df = pd.DataFrame(data, columns=['Entreprise','Siren' ,'Code Postal', 'Dirigeant', 'NAF'])
    return df

def delete_double(df):
    return df.drop_duplicates()

def add_linkedin(df):
    linkedin_urls = []
    total = len(df)
    
    # Instanciation d'une seule session DDGS pour toutes les requêtes
    ddgs = DDGS()
    
    for index, row in df.iterrows():
        query = f"{row['Entreprise']} {row['Dirigeant']} linkedin"
        linkedin_url = ""
        
        try:
            results = ddgs.text(keywords=query, max_results=1)
            if results:
                for result in results:
                    url = result.get('href', '')
                    if 'linkedin.com' in url:
                        linkedin_url = url
                        break
        except Exception as e:
            print(f"[{index+1}/{total}] Erreur pour la requête '{query}': {e}. Attente de 60 secondes...")
            time.sleep(60)
            # Nouvelle tentative après la pause
            try:
                results = ddgs.text(keywords=query, max_results=1)
                if results:
                    for result in results:
                        url = result.get('href', '')
                        if 'linkedin.com' in url:
                            linkedin_url = url
                            break
            except Exception as e:
                print(f"[{index+1}/{total}] Nouvelle erreur pour la requête '{query}': {e}. Passage à la suivante.")
        
        linkedin_urls.append(linkedin_url)
        print(f"[{index+1}/{total}] Traité : {row['Entreprise']} - {row['Dirigeant']}")
    
    #ddgs.shutdown()  # Fermer proprement la session DDGS si nécessaire
    print(f'Linkedin urls found: {len(linkedin_urls)}')
    df['Linkedin'] = linkedin_urls
    return df
def add_company_description(df):
    descriptions = []
    total = len(df)
    # Création d'une seule instance DDGS pour toutes les requêtes
    ddgs = DDGS()

    for index, row in df.iterrows():
        query = f"{row['Entreprise']} description"
        description_text = ""
        try:
            results = ddgs.text(keywords=query, max_results=1, region='fr-FR')
            if results:
                # Récupérer le champ 'body' qui contient souvent le résumé ou la description
                description_text = results[0].get('body', '')
        except Exception as e:
            print(f"[{index+1}/{total}] Erreur pour la requête '{query}': {e}. Attente de 60 secondes...")
            time.sleep(60)
            try:
                results = ddgs.text(keywords=query, max_results=1)
                if results:
                    description_text = results[0].get('body', '')
            except Exception as e:
                print(f"[{index+1}/{total}] Nouvelle erreur pour la requête '{query}': {e}. Passage à la suivante.")
        
        descriptions.append(description_text)
        print(f"[{index+1}/{total}] Description traitée pour : {row['Entreprise']}")

    df['Description'] = descriptions
    return df
if __name__ == '__main__':
    print('Start')
    # Example usage
    naf1 = "62.02A"
    naf2 = "62.01Z"
    department = "83"
    print('getting company names for NAF1:', naf1)
    df_naf1 = fetch_company_names(naf1, department)
    print('getting company names for NAF2:', naf2)
    df_naf2 = fetch_company_names(naf2, department)
    print('deleting double names')
    df_companies = pd.concat([df_naf1, df_naf2])
    df_companies = delete_double(df_companies)
    print('Number of companies:', len(df_companies))
    print('adding linkedin urls')
    df_companies = add_linkedin(df_companies)
    print('adding company descriptions')
    df_companies = add_company_description(df_companies)
    print('saving to companies.csv')
    df_companies.to_csv('companies.csv', index=False)
    print('End')