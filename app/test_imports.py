#!/usr/bin/env python3
"""
Script de test pour vérifier que toutes les importations fonctionnent correctement
"""

def test_imports():
    """Teste toutes les importations critiques"""
    try:
        print("Test d'importation des modules...")
        
        # Test NumPy
        import numpy as np
        print("✓ NumPy importé avec succès")
        print(f"  Version NumPy: {np.__version__}")
        
        # Test OpenCV
        import cv2
        print("✓ OpenCV importé avec succès")
        print(f"  Version OpenCV: {cv2.__version__}")
        
        # Test Pillow (PIL)
        from PIL import Image
        print("✓ Pillow (PIL) importé avec succès")
        print(f"  Version Pillow: {Image.__version__}")
        
        # Appliquer le patch face_recognition_models avant l'importation
        import face_recognition_patch
        print("✓ Patch face_recognition_models appliqué")
        
        # Test face_recognition
        import face_recognition
        print("✓ face_recognition importé avec succès")
        
        # Test FastAPI
        from fastapi import FastAPI
        print("✓ FastAPI importé avec succès")
        
        # Test SQLAlchemy
        from sqlalchemy import create_engine
        print("✓ SQLAlchemy importé avec succès")
        
        # Test des modules locaux
        from database import get_db
        print("✓ Module database importé avec succès")
        
        from models import User, Photo, FaceMatch
        print("✓ Module models importé avec succès")
        
        from face_recognizer import FaceRecognizer
        print("✓ Module face_recognizer importé avec succès")
        
        print("\n🎉 Toutes les importations fonctionnent correctement!")
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'importation: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

if __name__ == "__main__":
    test_imports() 