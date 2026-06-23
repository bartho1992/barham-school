
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'school.db')

print("=" * 80)
print("                      UTILISATEURS EXISTANTS")
print("=" * 80)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, ecole_id FROM user")
    users = cursor.fetchall()
    
    if not users:
        print("\n❌ Aucun utilisateur trouvé !")
    else:
        print(f"\n✅ {len(users)} utilisateur(s) trouvé(s) :\n")
        for u in users:
            print(f"  ID: {u[0]}")
            print(f"  Nom d'utilisateur: {u[1]}")
            print(f"  Rôle: {u[2]}")
            print(f"  École ID: {u[3] or '-'}\n")
            print("-" * 80)
    
    conn.close()
    
    print("\n✅ Terminé !")
    
except Exception as e:
    print(f"\n❌ Erreur: {e}")

input("\nAppuyez sur Entrée pour fermer...")
