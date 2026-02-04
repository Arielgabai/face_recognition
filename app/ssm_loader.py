"""
Chargeur de configuration depuis AWS SSM Parameter Store.

Ce module doit être importé et exécuté AVANT toute initialisation de:
- la base de données (database.py)
- les settings Pydantic (settings.py)
- les clients AWS (S3, SQS, Rekognition)
- le worker photo (photo_worker_sqs.py)

Les paramètres SSM sont chargés et injectés dans os.environ pour être
ensuite lus par les autres modules de configuration.

Usage dans main.py:
    # TOUT EN HAUT, après face_recognition_patch
    from ssm_loader import load_ssm_parameters
    load_ssm_parameters()
    
    # Ensuite seulement les autres imports
    from database import ...
    from settings import ...

Variables d'environnement requises:
    APP_CONFIG_PREFIX: Préfixe SSM (ex: /findme/prod)
    AWS_REGION: Région AWS (défaut: eu-west-1)

Structure SSM attendue:
    /findme/prod/DATABASE_URL -> postgresql://...
    /findme/prod/PHOTO_BUCKET_NAME -> my-bucket
    /findme/prod/PHOTO_SQS_QUEUE_URL -> https://sqs...
    etc.
"""

import os

# Flag pour garantir l'idempotence
_ssm_loaded = False


def load_ssm_parameters() -> bool:
    """
    Charge les paramètres depuis AWS SSM Parameter Store et les injecte dans os.environ.
    
    Cette fonction:
    - Lit APP_CONFIG_PREFIX et AWS_REGION depuis os.environ
    - Appelle SSM get_parameters_by_path avec le préfixe
    - Extrait le nom du paramètre (sans le préfixe) et la valeur
    - Injecte dans os.environ (ex: PHOTO_BUCKET_NAME=my-bucket)
    - Ne s'exécute qu'une seule fois (idempotent)
    - Ne plante pas si SSM est vide ou partiellement configuré
    
    Returns:
        bool: True si les paramètres ont été chargés, False sinon
    
    Sécurité:
        - Les valeurs des paramètres ne sont PAS loggées (secrets potentiels)
        - Seuls les noms de paramètres sont affichés dans les logs
    """
    global _ssm_loaded
    
    # Idempotence: ne s'exécute qu'une fois
    if _ssm_loaded:
        print("[SSM] Paramètres déjà chargés, skip")
        return True
    
    # Lire le préfixe de configuration
    prefix = os.environ.get("APP_CONFIG_PREFIX", "").strip()
    
    if not prefix:
        print("[SSM] APP_CONFIG_PREFIX non défini, chargement SSM désactivé")
        print("[SSM] Les paramètres seront lus depuis les variables d'environnement standard")
        _ssm_loaded = True
        return False
    
    # Normaliser le préfixe (sans slash final)
    prefix = prefix.rstrip("/")
    
    # Région AWS
    region = os.environ.get("AWS_REGION", "eu-west-1")
    
    print(f"[SSM] Chargement des paramètres depuis {prefix} (région: {region})")
    
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        
        ssm = boto3.client("ssm", region_name=region)
        
        # Utiliser un paginator pour gérer un grand nombre de paramètres
        paginator = ssm.get_paginator("get_parameters_by_path")
        
        loaded_count = 0
        loaded_params = []
        
        for page in paginator.paginate(
            Path=prefix,
            Recursive=True,
            WithDecryption=True,  # Déchiffrer les SecureString
        ):
            for param in page.get("Parameters", []):
                name = param["Name"]
                value = param["Value"]
                
                # Extraire le nom du paramètre sans le préfixe
                # Ex: /findme/prod/PHOTO_BUCKET_NAME -> PHOTO_BUCKET_NAME
                if name.startswith(prefix + "/"):
                    key = name[len(prefix) + 1:]
                else:
                    key = name.split("/")[-1]
                
                # Gérer les paramètres imbriqués (ex: /findme/prod/db/host -> DB_HOST)
                # On remplace les / par _ et on met en majuscules
                key = key.replace("/", "_").upper()
                
                # Injecter dans os.environ
                os.environ[key] = value
                loaded_params.append(key)
                loaded_count += 1
        
        if loaded_count > 0:
            print(f"[SSM] {loaded_count} paramètre(s) chargé(s):")
            for param_name in sorted(loaded_params):
                # Ne pas logger la valeur (potentiellement sensible)
                print(f"[SSM]   - {param_name}")
        else:
            print(f"[SSM] Aucun paramètre trouvé sous {prefix}")
            print("[SSM] Vérifiez que les paramètres existent dans SSM Parameter Store")
        
        _ssm_loaded = True
        return loaded_count > 0
        
    except NoCredentialsError:
        print("[SSM] ⚠️  Aucune credential AWS trouvée")
        print("[SSM] Assurez-vous que l'instance a un rôle IAM avec les permissions ssm:GetParametersByPath")
        _ssm_loaded = True
        return False
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        print(f"[SSM] ⚠️  Erreur AWS SSM ({error_code}): {error_msg}")
        
        if error_code == "AccessDeniedException":
            print("[SSM] Vérifiez les permissions IAM: ssm:GetParametersByPath, ssm:GetParameter")
        
        _ssm_loaded = True
        return False
        
    except ImportError:
        print("[SSM] ⚠️  boto3 non installé, chargement SSM impossible")
        _ssm_loaded = True
        return False
        
    except Exception as e:
        print(f"[SSM] ⚠️  Erreur inattendue: {type(e).__name__}: {e}")
        _ssm_loaded = True
        return False


def is_ssm_loaded() -> bool:
    """Retourne True si les paramètres SSM ont déjà été chargés."""
    return _ssm_loaded


def get_ssm_status() -> dict:
    """
    Retourne le statut du chargement SSM (utile pour le monitoring).
    
    Returns:
        dict: {
            "loaded": bool,
            "prefix": str ou None,
            "region": str
        }
    """
    return {
        "loaded": _ssm_loaded,
        "prefix": os.environ.get("APP_CONFIG_PREFIX"),
        "region": os.environ.get("AWS_REGION", "eu-west-1"),
    }
