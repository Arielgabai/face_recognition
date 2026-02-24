"""Tests unitaires pour la logique de validation selfie.

Lance avec : python test_selfie_validation.py
"""
import sys
import os


# ── Copie locale des helpers (sans charger FastAPI) ───────────────────────────

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


def _selfie_merge_faces(face_locations,
                        iou_duplicate: float = 0.45,
                        min_area_ratio: float = 0.30):
    """NMS leger : supprime doublons Haar et petits faux positifs.

    Compare chaque candidat a TOUS les rects deja gardes (pas seulement le principal).
    """
    if not face_locations:
        return []
    areas = [(f, max(0, f[1] - f[3]) * max(0, f[2] - f[0])) for f in face_locations]
    areas.sort(key=lambda x: -x[1])
    main_face, main_area = areas[0]
    if len(areas) == 1:
        return [main_face]
    kept = [main_face]
    for face, area in areas[1:]:
        if area < min_area_ratio * main_area:
            continue  # petit faux positif
        if any(_selfie_iou(face, k) > iou_duplicate for k in kept):
            continue  # doublon d'un rect deja garde
        kept.append(face)
    return kept


def _count_real_faces(nms_kept,
                      sec_area_ratio: float = 0.35,
                      sec_max_iou: float = 0.20):
    """Apres NMS, compte les faces vraiment distinctes (logique de validation)."""
    if not nms_kept:
        return 0
    main = nms_kept[0]
    main_area = max(0, main[1] - main[3]) * max(0, main[2] - main[0])
    real = [main]
    for face in nms_kept[1:]:
        fa = max(0, face[1] - face[3]) * max(0, face[2] - face[0])
        if fa >= sec_area_ratio * main_area and _selfie_iou(face, main) < sec_max_iou:
            real.append(face)
    return len(real)


# ── Helpers d'assertion ───────────────────────────────────────────────────────

def rect(x, y, w, h):
    """Convertit (x,y,w,h) en (top, right, bottom, left) comme Haar."""
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
    assert_near("IoU partial overlap", _selfie_iou(a, b), 1/3, tol=0.01)


# ── Tests NMS merge ───────────────────────────────────────────────────────────

def test_merge_single():
    result = _selfie_merge_faces([rect(100, 100, 150, 150)])
    assert_equal("single face: keep 1", len(result), 1)

def test_merge_duplicate_high_iou():
    """2 rectangles quasi identiques (meme visage) => garder 1 (iou_duplicate=0.45)."""
    main = rect(100, 100, 150, 150)
    dup  = rect(105, 102, 148, 148)
    result = _selfie_merge_faces([main, dup])
    assert_equal("duplicate high-IoU: keep 1", len(result), 1)

def test_merge_small_false_positive():
    """Petit rectangle (<30% aire principale) => ignore."""
    main  = rect(100, 100, 150, 150)
    small = rect(300, 300, 30, 30)
    result = _selfie_merge_faces([main, small])
    assert_equal("small false positive: keep 1", len(result), 1)

def test_merge_two_real_faces():
    """2 visages de taille comparable, pas d'overlap => garder 2."""
    face1 = rect(50,  100, 120, 120)
    face2 = rect(350, 100, 115, 115)
    result = _selfie_merge_faces([face1, face2])
    assert_equal("2 real faces: keep 2", len(result), 2)

def test_merge_three_rects_one_face():
    """3 rectangles Haar autour du meme visage => garder 1."""
    main = rect(100, 100, 150, 150)
    d1   = rect(102, 101, 149, 149)
    d2   = rect(98,   99, 152, 152)
    result = _selfie_merge_faces([main, d1, d2])
    assert_equal("3 Haar rects 1 face: keep 1", len(result), 1)

def test_merge_main_plus_tiny_eye():
    """Visage + tiny faux-positif (oeil) => keep 1."""
    main = rect(100, 100, 200, 200)
    eye  = rect(160, 135, 30, 25)
    result = _selfie_merge_faces([main, eye])
    assert_equal("face + tiny eye: keep 1", len(result), 1)

def test_merge_four_rects_two_real():
    """4 rectangles: 2 groupes de 2 doublons => NMS doit garder 2 (un par groupe)."""
    # groupe A autour de (100,100)
    a1 = rect(100, 100, 150, 150)
    a2 = rect(103, 102, 148, 148)
    # groupe B loin, taille similaire
    b1 = rect(400, 100, 145, 145)
    b2 = rect(402, 101, 143, 143)
    result = _selfie_merge_faces([a1, a2, b1, b2])
    assert_equal("4 rects 2 groups: NMS keep 2", len(result), 2)

def test_merge_iou_custom_threshold():
    """Verifie que le seuil iou_duplicate est bien respecte.

    IoU(a, b) ~ 0.33.
    - iou_duplicate=0.10 : 0.33 > 0.10 => b est un doublon => keep 1
    - iou_duplicate=0.45 : 0.33 < 0.45 => b est distinct  => keep 2
    - iou_duplicate=0.20 : 0.33 > 0.20 => b est un doublon => keep 1
    """
    a = rect(0, 0, 100, 100)
    b = rect(50, 0, 100, 100)   # IoU ~0.33
    result_strict = _selfie_merge_faces([a, b], iou_duplicate=0.10)
    assert_equal("iou=0.10, overlap~0.33: doublon => keep 1", len(result_strict), 1)
    result_medium = _selfie_merge_faces([a, b], iou_duplicate=0.20)
    assert_equal("iou=0.20, overlap~0.33: doublon => keep 1", len(result_medium), 1)
    result_lax = _selfie_merge_faces([a, b], iou_duplicate=0.45)
    assert_equal("iou=0.45, overlap~0.33: distinct => keep 2", len(result_lax), 2)


# ── Tests count_real_faces ────────────────────────────────────────────────────

def test_real_faces_one():
    """Un seul visage => 1 face reelle."""
    nms = [rect(100, 100, 150, 150)]
    assert_equal("real_faces single: 1", _count_real_faces(nms), 1)

def test_real_faces_two_distinct():
    """2 visages distincts taille comparable, faible iou => 2 faces reelles."""
    f1 = rect(50,  100, 130, 130)
    f2 = rect(400, 100, 120, 120)
    nms = [f1, f2]
    assert_equal("real_faces 2 distinct: 2", _count_real_faces(nms), 2)

def test_real_faces_second_too_small():
    """2e face trop petite par rapport a la 1ere (<35%) => pas une face reelle."""
    big   = rect(50, 100, 150, 150)
    small = rect(350, 100, 60, 60)   # 3600 vs 22500 => 16%
    nms = [big, small]
    assert_equal("real_faces 2nd too small: 1", _count_real_faces(nms), 1)

def test_real_faces_second_high_iou():
    """2e face grande mais fort overlap => doublon, pas une face reelle distincte."""
    f1 = rect(100, 100, 150, 150)
    f2 = rect(103, 102, 148, 148)
    nms = [f1, f2]
    assert_equal("real_faces high iou: 1", _count_real_faces(nms), 1)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Tests IoU ===")
    test_iou_identical()
    test_iou_no_overlap()
    test_iou_partial()

    print("\n=== Tests NMS merge ===")
    test_merge_single()
    test_merge_duplicate_high_iou()
    test_merge_small_false_positive()
    test_merge_two_real_faces()
    test_merge_three_rects_one_face()
    test_merge_main_plus_tiny_eye()
    test_merge_four_rects_two_real()
    test_merge_iou_custom_threshold()

    print("\n=== Tests count_real_faces ===")
    test_real_faces_one()
    test_real_faces_two_distinct()
    test_real_faces_second_too_small()
    test_real_faces_second_high_iou()

    print("\n[ALL PASS] Tous les tests passent.")
