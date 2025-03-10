import requests
import pandas as pd
from duckduckgo_search import DDGS
import time
import notion_client
from tqdm import tqdm
import ollama
import PyPDF2
from dotenv import load_dotenv
import os


# ---------------------------
# 1. Récupération des entreprises via l'API
# ---------------------------
def fetch_company_names(naf, department, pages=10):
    data = []
    for page in range(1, pages):
        url = (
            f"https://recherche-entreprises.api.gouv.fr/search?"
            f"departement={department}&activite_principale={naf}"
            f"&page={page}&per_page=25&categorie_entreprise=PME"
        )
        response = requests.get(url)
        response_data = response.json()
        for company in response_data.get("results", []):
            nom = company.get("nom_complet", "")
            code = company.get("matching_etablissements", [{}])[0].get(
                "code_postal", ""
            )
            nature = company.get("nature_juridique", "")
            siren = company.get("siren", "")
            if int(nature) != 1000:
                try:
                    dirigeant = (
                        company["dirigeants"][0]["nom"]
                        + " "
                        + company["dirigeants"][0]["prenoms"]
                    )
                    data.append([nom, siren, code, dirigeant, naf])
                except Exception as e:
                    # En cas d'erreur lors de la récupération du dirigeant, on ignore l'entreprise
                    pass
    df = pd.DataFrame(
        data, columns=["Entreprise", "Siren", "Code Postal", "Dirigeant", "NAF"]
    )
    return df


def delete_double(df):
    return df.drop_duplicates()


# ---------------------------
# 2. Enrichissement des données via DuckDuckGo
# ---------------------------
def add_linkedin(df):
    linkedin_urls = []
    total = len(df)
    ddgs = DDGS()  # Instanciation unique de DDGS pour toutes les requêtes

    for index, row in df.iterrows():
        query = f"{row['Entreprise']} {row['Dirigeant']} linkedin"
        linkedin_url = ""
        try:
            results = ddgs.text(keywords=query, max_results=1)
            if results:
                for result in results:
                    url = result.get("href", "")
                    if "linkedin.com" in url:
                        linkedin_url = url
                        break
        except Exception as e:
            print(
                f"[{index+1}/{total}] Erreur pour la requête '{query}': {e}. Attente de 60 secondes..."
            )
            time.sleep(60)
            try:
                results = ddgs.text(keywords=query, max_results=1)
                if results:
                    for result in results:
                        url = result.get("href", "")
                        if "linkedin.com" in url:
                            linkedin_url = url
                            break
            except Exception as e:
                print(
                    f"[{index+1}/{total}] Nouvelle erreur pour la requête '{query}': {e}. Passage à la suivante."
                )
        linkedin_urls.append(linkedin_url)
        print(f"[{index+1}/{total}] Traité : {row['Entreprise']} - {row['Dirigeant']}")

    print(f"Nombre d’URLs Linkedin trouvées : {len(linkedin_urls)}")
    df["Linkedin"] = linkedin_urls
    return df


def add_company_description(df):
    descriptions = []
    total = len(df)
    ddgs = DDGS()  # Instanciation unique pour toutes les requêtes

    for index, row in df.iterrows():
        query = f"{row['Entreprise']} description"
        description_text = ""
        try:
            results = ddgs.text(keywords=query, max_results=1, region="fr-FR")
            if results:
                description_text = results[0].get("body", "")
        except Exception as e:
            print(
                f"[{index+1}/{total}] Erreur pour la requête '{query}': {e}. Attente de 60 secondes..."
            )
            time.sleep(60)
            try:
                results = ddgs.text(keywords=query, max_results=1)
                if results:
                    description_text = results[0].get("body", "")
            except Exception as e:
                print(
                    f"[{index+1}/{total}] Nouvelle erreur pour la requête '{query}': {e}. Passage à la suivante."
                )
        descriptions.append(description_text)
        print(f"[{index+1}/{total}] Description traitée pour : {row['Entreprise']}")

    df["Description"] = descriptions
    return df


# ---------------------------
# 3. Interaction avec Notion
# ---------------------------
def get_existing_companies(client, database_id):
    """
    Récupère l'ensemble des noms d'entreprises déjà présentes dans la base Notion.
    """
    existing_companies = set()
    has_more = True
    next_cursor = None
    while has_more:
        query_params = {}
        if next_cursor:
            query_params["start_cursor"] = next_cursor
        response = client.databases.query(database_id=database_id, **query_params)
        results = response.get("results", [])
        for page in results:
            entreprise_prop = page["properties"].get("Entreprise", {})
            if entreprise_prop.get("title") and entreprise_prop["title"]:
                company_name = entreprise_prop["title"][0].get("plain_text", "")
                if company_name:
                    existing_companies.add(company_name)
        has_more = response.get("has_more", False)
        next_cursor = response.get("next_cursor", None)
    return existing_companies


def generate_lm_for_company(row, cv_content, lm_exemple_content):
    """
    Génère une lettre de motivation spécifique à une entreprise en utilisant l'API d'Ollama.
    """
    # Déterminer le domaine en fonction du code NAF
    if row["NAF"] == "62.01Z":
        domaine = "conseil en systèmes et logiciels informatiques"
    else:
        domaine = "Programmation informatique"

    prompt = f"""
Tu es un assistant expert en rédaction de lettres de motivation. Ta mission consiste à fournir le texte d’une lettre de motivation claire, convaincante et adaptée aux informations suivantes :

- Domaine d’activité : {domaine}
- Entreprise : {row["Entreprise"]} (Code postal : {row["Code Postal"]})
- Description du poste : {row["Description"]}
- Contenu de mon CV :
{cv_content}
- Exemple de lettre de motivation :
{lm_exemple_content}

Rédige la meilleure lettre de motivation possible en fonction de ces éléments, en veillant à souligner clairement les expériences et compétences pertinentes, et à expliquer pourquoi je suis le candidat idéal pour ce poste.

**Consignes importantes** :
1. Ne génère **que le corps** du texte de la lettre de motivation (pas de formule de politesse de début ou de fin, pas de mention de ton rôle ou de la tâche que tu accomplis).
2. Ne fournis **aucun élément supplémentaire** : pas de titre, pas d’explication de ta démarche, pas de salutation, pas de signature, ni aucune autre information hors du corps du texte.
3. Respecte le style, le registre et la langue française.
4. Le texte doit être composé **d’au moins trois paragraphes** distincts.

Commence directement par le premier paragraphe du corps du texte et termine à la fin du dernier paragraphe de la lettre de motivation.
    """
    response = ollama.chat(
        model="llama3.2",
        messages=[{"role": "user", "content": prompt}],
        stream=False,
    )
    lm_content = response["message"]["content"]
    return lm_content


def add_row_to_notion(client, database_id, row, lm_content):
    if row["NAF"] == "62.01Z":
        domaine = "conseil en systèmes et logiciels informatiques"
    else:
        domaine = "Programmation informatique"

    properties = {
        "Entreprise": {"title": [{"text": {"content": row["Entreprise"]}}]},
        "Siren": {"rich_text": [{"text": {"content": str(row["Siren"])}}]},
        "Code Postal": {"rich_text": [{"text": {"content": str(row["Code Postal"])}}]},
        "Dirigeant": {"rich_text": [{"text": {"content": row["Dirigeant"]}}]},
        "Domaine": {"select": {"name": domaine}},
        "Linkedin": {
            "url": (
                row["Linkedin"]
                if pd.notna(row["Linkedin"]) and row["Linkedin"] != ""
                else None
            )
        },
        "Description": {
            "rich_text": [
                {
                    "text": {
                        "content": (
                            row["Description"] if pd.notna(row["Description"]) else ""
                        )
                    }
                }
            ]
        },
    }
    # Création de la page dans Notion
    response = client.pages.create(
        parent={"database_id": database_id}, properties=properties
    )
    page_id = response["id"]

    # Préparation du contenu à ajouter, avec un en-tête
    header = "Lettre de motivation :\n"
    full_text = header + lm_content

    # Fonction pour découper le texte en morceaux de 2000 caractères maximum
    def split_text(text, chunk_size=2000):
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    chunks = split_text(full_text)

    # Création d'une liste de blocs pour chaque morceau
    blocks = []
    for chunk in chunks:
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}]
                },
            }
        )

    # Ajout des blocs à la page Notion
    client.blocks.children.append(
        block_id=page_id,
        children=blocks,
    )


# ---------------------------
# 4. Script principal
# ---------------------------
if __name__ == "__main__":
    print("Start")

    # Lecture du contenu du CV à partir du fichier PDF (unique pour toutes les lettres)
    cv_path = "CV_MEHDI.pdf"
    with open(cv_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        cv_content = ""
        for page in reader.pages:
            cv_content += page.extract_text()

    # Lecture du contenu de l'exemple de lettre de motivation à partir du fichier PDF
    lm_exemple_path = "LM.pdf"
    with open(lm_exemple_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        lm_exemple_content = ""
        for page in reader.pages:
            lm_exemple_content += page.extract_text()

    # Charger le fichier de configuration
    load_dotenv("config.env")
    # Paramètres Notion

    # Récupérer le token et le database_id depuis config.env
    token = os.getenv("TOKEN")
    database_id = os.getenv("DATABASE_ID")
    notion_client_instance = notion_client.Client(auth=token)

    # Récupérer les entreprises déjà présentes dans Notion (filtrage par Siren)
    print("Récupération des entreprises existantes dans Notion...")
    existing_companies = get_existing_companies(notion_client_instance, database_id)
    print(f"Nombre d'entreprises existantes dans Notion : {len(existing_companies)}")

    # Paramètres de recherche (exemple)
    naf1 = "62.02A"
    naf2 = "62.01Z"
    department = "83"

    print("Récupération des entreprises pour NAF1:", naf1)
    df_naf1 = fetch_company_names(naf1, department)
    print("Récupération des entreprises pour NAF2:", naf2)
    df_naf2 = fetch_company_names(naf2, department)

    print("Suppression des doublons...")
    df_companies = pd.concat([df_naf1, df_naf2])
    df_companies = delete_double(df_companies)
    print("Nombre total d'entreprises récupérées :", len(df_companies))

    # Filtrer les entreprises déjà présentes dans Notion via le Siren
    df_companies = df_companies[~df_companies["Siren"].isin(existing_companies)]
    print("Nombre d'entreprises à traiter (nouvelles) :", len(df_companies))

    # Si des entreprises sont à traiter, on enrichit les données avec DuckDuckGo
    if len(df_companies) > 0:
        print("Ajout des URLs Linkedin...")
        df_companies = add_linkedin(df_companies)
        print("Ajout des descriptions des entreprises...")
        df_companies = add_company_description(df_companies)
    else:
        print("Aucune nouvelle entreprise à enrichir.")

    # Pour chaque entreprise, générer une lettre de motivation spécifique et la charger dans Notion
    if len(df_companies) > 0:
        print("Chargement des données dans Notion...")
        for index, row in tqdm(
            df_companies.iterrows(), total=len(df_companies), desc="Uploading to Notion"
        ):
            if row.isnull().any():
                print(f"Row {index} contient des valeurs NaN: {row}")
            try:
                # Génération de la lettre de motivation pour l'entreprise courante
                lm_content = generate_lm_for_company(
                    row, cv_content, lm_exemple_content
                )
                add_row_to_notion(notion_client_instance, database_id, row, lm_content)
            except notion_client.errors.APIResponseError as e:
                if e.status == 502:
                    print("Limite de débit atteinte. Attente de 60 secondes...")
                    time.sleep(60)
                    lm_content = generate_lm_for_company(
                        row, cv_content, lm_exemple_content
                    )
                    add_row_to_notion(
                        notion_client_instance, database_id, row, lm_content
                    )
                else:
                    raise e
        print("Données chargées dans Notion.")
    else:
        print("Aucune nouvelle entreprise à charger dans Notion.")

    print("End")
