"""Tests unitaires pour la logique de validation selfie.

Lance avec : python test_selfie_validation.py
"""
import sys
import os

# Importer directement les helpers sans charger toute l'app
def _selfie_iou(a, b) -> float:
    ay1, ax2, ay2, ax1 = a
    by1, bx2, by2, bx1 = b
    ix1 = max(ax1, bx1); iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2); iy2 = min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0

def _selfie_merge_faces(face_locations):
    if not face_locations:
        return []
    areas = [(f, max(0, f[1] - f[3]) * max(0, f[2] - f[0])) for f in face_locations]
    areas.sort(key=lambda x: -x[1])
    main_face, main_area = areas[0]
    if len(areas) == 1:
        return [main_face]
    kept = [main_face]
    for face, area in areas[1:]:
        if area < 0.30 * main_area:
            continue  # petit faux positif
        if _selfie_iou(face, main_face) > 0.30:
            continue  # doublon même visage
        kept.append(face)
    return kept


# ── Helpers ──────────────────────────────────────────────────────────────────

def rect(x, y, w, h):
    """Convertit (x,y,w,h) → (top, right, bottom, left) comme Haar."""
    return (y, x + w, y + h, x)

def assert_equal(label, got, expected):
    ok = got == expected
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}: got={got!r} expected={expected!r}")
    if not ok:
        sys.exit(1)

def assert_near(label, got, expected, tol=0.01):
    ok = abs(got - expected) <= tol
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}: got={got:.4f} expected~{expected:.4f} tol={tol}")
    if not ok:
        sys.exit(1)


# ── Tests IoU ─────────────────────────────────────────────────────────────────

def test_iou_identical():
    f = rect(100, 100, 200, 200)
    assert_near("IoU identical faces", _selfie_iou(f, f), 1.0)

def test_iou_no_overlap():
    a = rect(0, 0, 100, 100)
    b = rect(200, 200, 100, 100)
    assert_near("IoU no overlap", _selfie_iou(a, b), 0.0)

def test_iou_partial():
    a = rect(0, 0, 100, 100)
    b = rect(50, 0, 100, 100)
    # overlap = 50*100=5000, union = 10000+10000-5000=15000 → 1/3
    assert_near("IoU partial overlap", _selfie_iou(a, b), 1/3, tol=0.01)


# ── Tests merge ───────────────────────────────────────────────────────────────

def test_merge_single():
    faces = [rect(100, 100, 150, 150)]
    result = _selfie_merge_faces(faces)
    assert_equal("merge single face: keep 1", len(result), 1)

def test_merge_duplicate_same_face():
    """Haar renvoie 2 rectangles quasi identiques pour 1 seul visage: doit garder 1."""
    main = rect(100, 100, 150, 150)
    dup  = rect(105, 102, 148, 148)
    result = _selfie_merge_faces([main, dup])
    assert_equal("merge duplicate Haar rects: keep 1", len(result), 1)

def test_merge_small_false_positive():
    """Petit rectangle (<30% de la face principale): doit etre ignore."""
    main  = rect(100, 100, 150, 150)
    small = rect(300, 300, 30, 30)
    result = _selfie_merge_faces([main, small])
    assert_equal("merge small false positive: keep 1", len(result), 1)

def test_merge_two_real_faces():
    """2 personnes visibles: 2 faces significatives doivent rester."""
    face1 = rect(50,  100, 120, 120)
    face2 = rect(350, 100, 115, 115)
    result = _selfie_merge_faces([face1, face2])
    assert_equal("merge 2 real faces: keep 2", len(result), 2)

def test_merge_three_haar_rects_one_face():
    """Haar donne 3 rectangles autour du meme visage: doit garder 1."""
    main = rect(100, 100, 150, 150)
    d1   = rect(102, 101, 149, 149)
    d2   = rect(98,  99,  152, 152)
    result = _selfie_merge_faces([main, d1, d2])
    assert_equal("merge 3 Haar rects for 1 face: keep 1", len(result), 1)

def test_merge_main_plus_tiny_eye():
    """Visage + tiny faux-positif: garder uniquement le visage."""
    main = rect(100, 100, 200, 200)
    eye  = rect(160, 135, 30, 25)
    result = _selfie_merge_faces([main, eye])
    assert_equal("merge face + tiny faux-positif: keep 1", len(result), 1)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Tests IoU ===")
    test_iou_identical()
    test_iou_no_overlap()
    test_iou_partial()

    print("\n=== Tests merge_faces ===")
    test_merge_single()
    test_merge_duplicate_same_face()
    test_merge_small_false_positive()
    test_merge_two_real_faces()
    test_merge_three_haar_rects_one_face()
    test_merge_main_plus_tiny_eye()

    print("\n[ALL PASS] Tous les tests passent.")
