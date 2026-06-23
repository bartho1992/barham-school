
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'school.db')

print("Vérification des clés en base de données...\n")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, cle, ecole_nom, active FROM licence ORDER BY created_at DESC")
    rows = cursor.fetchall()
    
    if not rows:
        print("❌ Aucune clé trouvée !")
    else:
        print(f"✅ {len(rows)} clé(s) trouvée(s) :\n")
        for r in rows:
            status = "ACTIVE" if r[3] else "INACTIVE"
            print(f"  🔑 {r[1]}")
            print(f"     École: {r[2] or '-'}")
            print(f"     Statut: {status}\n")
    
    conn.close()
except Exception as e:
    print(f"❌ Erreur: {e}")
