#!/usr/bin/env python3
"""
Script de test pour vérifier que toutes les importations fonctionnent correctement
"""

def test_imports():
    """Teste toutes les importations critiques"""
    try:
        import os
        provider = os.environ.get("FACE_RECOGNIZER_PROVIDER", "local").strip().lower()
        print("Test d'importation des modules...")
        print(f"  Provider reconnaissance: {provider or 'local'}")
        
        # Test NumPy
        import numpy as np
        print("[OK] NumPy importe avec succes")
        print(f"  Version NumPy: {np.__version__}")
        
        # Test OpenCV
        import cv2
        print("[OK] OpenCV importe avec succes")
        print(f"  Version OpenCV: {cv2.__version__}")
        
        # Test Pillow (PIL)
        from PIL import Image
        print("[OK] Pillow (PIL) importe avec succes")
        print(f"  Version Pillow: {Image.__version__}")
        
        if provider in {"aws", "azure"}:
            print("[OK] face_recognition local ignore (provider distant configure)")
        else:
            # Appliquer le patch face_recognition_models avant l'importation
            import face_recognition_patch
            print("[OK] Patch face_recognition_models applique")

            # Test face_recognition
            import face_recognition
            print("[OK] face_recognition importe avec succes")
        
        # Test FastAPI
        from fastapi import FastAPI
        print("[OK] FastAPI importe avec succes")
        
        # Test SQLAlchemy
        from sqlalchemy import create_engine
        print("[OK] SQLAlchemy importe avec succes")
        
        # Test des modules locaux
        from database import get_db
        print("[OK] Module database importe avec succes")
        
        from models import User, Photo, FaceMatch
        print("[OK] Module models importe avec succes")
        
        if provider in {"aws", "azure"}:
            from recognizer_factory import get_face_recognizer
            print("[OK] Module recognizer_factory importe avec succes")
        else:
            from face_recognizer import FaceRecognizer
            print("[OK] Module face_recognizer importe avec succes")
        
        print("\n[OK] Toutes les importations fonctionnent correctement!")
        return True
        
    except ImportError as e:
        print(f"[ERROR] Erreur d'importation: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Erreur inattendue: {e}")
        return False

if __name__ == "__main__":
    import sys
    sys.exit(0 if test_imports() else 1)