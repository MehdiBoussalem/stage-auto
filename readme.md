# Projet d'Intégration et Génération de Lettres de Motivation pour Entreprises

Ce projet est une solution automatisée qui récupère des données d'entreprises à partir de l'API publique du gouvernement, enrichit ces données via des recherches sur DuckDuckGo, génère une lettre de motivation personnalisée pour chaque entreprise en utilisant l'API d'Ollama, et ajoute le tout dans une base Notion.

## Fonctionnalités

- **Récupération des entreprises** :  
  Utilisation de l'API [recherche-entreprises.api.gouv.fr](https://entreprises.data.gouv.fr/) pour extraire les informations de PME basées sur le code NAF et le département.

- **Enrichissement des données** :  
  Recherche des URL LinkedIn et des descriptions d'entreprise grâce à DuckDuckGo afin d'enrichir les informations récupérées.

- **Génération de lettres de motivation personnalisées** :  
  Pour chaque entreprise, le script génère une lettre de motivation en s'appuyant sur un CV et un exemple de lettre (fichiers PDF). L'API d'Ollama est utilisée pour créer une lettre adaptée aux spécificités de chaque entreprise.

- **Intégration dans Notion** :  
  Les informations et la lettre de motivation générée sont automatiquement ajoutées dans une base Notion. Le contenu de la lettre est découpé en blocs de texte pour respecter les contraintes de l'API Notion.

- **Configuration via fichier d'environnement** :  
  Le token d'authentification Notion et l'ID de la base de données sont chargés depuis un fichier `config.env`.

## Prérequis

- **Python 3.x**
- Modules Python requis :
  - `requests`
  - `pandas`
  - `duckduckgo_search`
  - `notion_client`
  - `tqdm`
  - `ollama`
  - `PyPDF2`
  - `python-dotenv`

Vous pouvez installer toutes les dépendances avec :

```bash
pip install -r requirements.txt
```

## Configuration

Créez un fichier `config.env` dans le même répertoire que votre script avec le contenu suivant :

```
TOKEN=ntn_XXXXXXXXXXXXXXX
DATABASE_ID=YYYYYYYYYYYYYYYYYYYYYYYYYYYY
```

Remplacez les valeurs par vos identifiants Notion.

## Utilisation

1. **Préparez vos fichiers PDF** :  
   - Un fichier PDF contenant votre CV (par exemple `CV_MEHDI.pdf`).
   - Un fichier PDF avec un exemple de lettre de motivation (`LM.pdf`).

2. **Exécutez le script** :

   ```bash
   python main.py
   ```

   Le script réalise les actions suivantes :
   - Récupération des entreprises selon les codes NAF et département définis.
   - Enrichissement des données via DuckDuckGo.
   - Pour chaque entreprise non présente dans la base Notion (filtrage par Siren), génération d'une lettre de motivation personnalisée et création d'une page dans Notion avec un bloc de texte contenant la lettre.

## Organisation du Code

- **fetch_company_names** : Récupère les informations d'entreprises via l'API.
- **add_linkedin** et **add_company_description** : Enrichissent les données des entreprises avec DuckDuckGo.
- **generate_lm_for_company** : Génère la lettre de motivation personnalisée pour chaque entreprise en appelant l'API d'Ollama.
- **add_row_to_notion** : Crée une nouvelle page dans Notion pour l'entreprise et y ajoute un bloc de texte contenant la lettre.
- **Configuration** : Les variables sensibles (TOKEN et DATABASE_ID) sont récupérées depuis le fichier `config.env`.

## Remarques

- **API Notion** : Assurez-vous que votre token Notion dispose des autorisations nécessaires et que votre base de données est bien configurée pour recevoir les pages.
- **Limites de l'API** : Le script gère les cas de dépassement de quota (limite de débit) en effectuant des pauses.
- **Ollama API** : La génération de la lettre de motivation est effectuée via l'API d'Ollama (modèle "llama3.2"). Assurez-vous que cette API est accessible et configurée correctement.

## Auteurs

Mehdi Boussalem et Cherif Miloua