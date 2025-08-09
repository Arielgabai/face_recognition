import os


def get_face_recognizer():
    """Retourne une instance du recognizer selon la variable d'env FACE_RECOGNIZER_PROVIDER."""
    provider = os.environ.get("FACE_RECOGNIZER_PROVIDER", "local").strip().lower()
    if provider == "azure":
        from azure_face_recognizer import AzureFaceRecognizer
        return AzureFaceRecognizer()
    else:
        # Défaut: implémentation locale gratuite
        from face_recognizer import FaceRecognizer
        return FaceRecognizer()


