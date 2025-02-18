
import requests
import pandas as pd

def fetch_company_names(naf, department, pages=10):
    liste_nom = []
    for page in range(1,pages):
        url = f"https://recherche-entreprises.api.gouv.fr/search?departement={department}&activite_principale={naf}&page={page}&per_page=25&categorie_entreprise=PME"
        response = requests.get(url)
        data = response.json()
        for company in data['results']:
            nom = company['nom_complet']
            code = company['matching_etablissements'][0]['code_postal']
            nature = company['nature_juridique']
            if int(nature) != 1000:
                try :
                    dirigent = company['dirigeants'][0]['nom'] + ' ' + company['dirigeants'][0]['prenoms']                    
                    liste_nom.append(f"{nom} - {code} - {dirigent}  - {nature}")
                except:
                    pass
                
            
    return liste_nom

def delete_double(liste):
    return list(set(liste))



if __name__ == '__main__':
    
    print('Start')
    # Example usage
    naf1 = "62.02A"
    naf2 = "62.01Z"
    department = "83"
    print('getting company names for NAF1:', naf1)
    company_names_naf1 = fetch_company_names(naf1, department)
    print('getting company names for NAF2:', naf2)
    company_names_naf2 = fetch_company_names(naf2, department)
    print('deleting double names')
    company_names = delete_double(company_names_naf1 + company_names_naf2)
    print('list of company names:')
    for nom in company_names:
        print(nom)
    print('Number of companies:', len(company_names))
    print('saving to companies.csv')
    company_details = [nom.split(' - ') for nom in company_names]
    df = pd.DataFrame(company_details, columns=['Entreprise', 'Code Postal', 'Dirigeant', 'Nature Juridique'])
    df.to_csv('companies.csv', index=False)
    print('End')