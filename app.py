from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import time
import random

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///game.db"
db = SQLAlchemy(app)

# Datenbankmodell für Spieler
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    money = db.Column(db.Float, default=100.0)
    energy = db.Column(db.Float, default=0.0)
    passive_energy = db.Column(db.Float, default=0.5)
    power_rate = db.Column(db.Float, default=1.0)
    upgrade_level = db.Column(db.Integer, default=1)
    module_count = db.Column(db.Integer, default=0)
    xp = db.Column(db.Float, default=0)  # Aktuelle XP
    level = db.Column(db.Integer, default=1)  # Spieler-Level
    xp_needed = db.Column(db.Float, default=10)  # XP für nächstes Level
    hydro_count = db.Column(db.Integer, default=0)
    coal_count = db.Column(db.Integer, default=0)




# Initiale DB-Erstellung
with app.app_context():
    db.create_all()


# Startseite mit Login-Check
# **📌 Login-Seite anzeigen**
@app.route("/")
def login_page():
    return render_template("login.html")



# **📌 Registrierung**
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Benutzername & Passwort erforderlich"}), 400

    if Player.query.filter_by(username=username).first():
        return jsonify({"error": "Benutzername existiert bereits"}), 400

    password_hash = generate_password_hash(password)
    new_player = Player(username=username, password_hash=password_hash)
    db.session.add(new_player)
    db.session.commit()

    return jsonify({"success": True, "message": "Registrierung erfolgreich!"})

# **📌 Login**
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    player = Player.query.filter_by(username=username).first()

    if not player or not check_password_hash(player.password_hash, password):
        return jsonify({"error": "Falscher Benutzername oder Passwort"}), 401

    session["username"] = username
    return jsonify({"success": True, "message": "Login erfolgreich!"})

# **📌 Logout**
@app.route("/logout")
def logout():
    session.pop("username", None)
    return jsonify({"success": True, "message": "Logout erfolgreich!"})

# **📌 Spielseite nach Login**
@app.route("/game")
def game():
    if "username" not in session:
        return redirect("/")  # Falls der Benutzer nicht eingeloggt ist, zurück zum Login
    return render_template("game.html", username=session["username"])



@app.route("/leaderboard")
def leaderboard():
    players = Player.query.order_by(Player.level.desc()).limit(10).all()  # Top 10 Spieler nach Level
    leaderboard_data = [{"username": p.username, "level": p.level} for p in players]

    return jsonify({"success": True, "leaderboard": leaderboard_data})


@app.route("/generate_energy")
def generate_energy():
    if "username" not in session:
        return jsonify({"error": "Nicht eingeloggt"}), 400

    player = Player.query.filter_by(username=session["username"]).first()
    if not player:
        return jsonify({"error": "Spieler nicht gefunden"}), 400

    # Energie erzeugen
    player.energy += player.power_rate

    # XP-Berechnung (geringerer XP-Gewinn pro Level, aber weiterhin ansteigend)
    xp_gain = player.power_rate * (1 + player.level * 0.02)  # Jetzt weniger pro Level
    player.xp += xp_gain

    # Level-Up, falls XP-Leiste voll ist
    leveled_up = False
    while player.xp >= player.xp_needed:
        player.xp -= player.xp_needed  # Rest-XP bleibt erhalten
        player.level += 1

        # XP-Anforderung stärker erhöhen (Level 1-10: *2, danach *2.5)
        if player.level < 10:
            player.xp_needed *= 2.0  # **Jedes Level erfordert jetzt das Doppelte**
        else:
            player.xp_needed *= 2.5  # **Ab Level 10 wird es noch schwerer**

        leveled_up = True

    db.session.commit()

    return jsonify({
        "success": True,
        "energy": player.energy,
        "money": player.money,
        "power_rate": player.power_rate,
        "xp": player.xp,
        "xp_needed": player.xp_needed,
        "level": player.level,
        "leveled_up": leveled_up
    })




@app.route("/sell_energy")
def sell_energy():
    if "username" not in session:
        return jsonify({"error": "Not logged in"})
    
    player = Player.query.filter_by(username=session["username"]).first()
    if not player:
        return jsonify({"error": "Spieler nicht gefunden"}), 400
    
    price_per_kwh = 0.5 + random.uniform(-0.2, 0.2)  # Dynamische Preise
    earnings = player.energy * price_per_kwh
    player.money += earnings
    player.energy = 0
    db.session.commit()
    return jsonify({"money": player.money, "price": price_per_kwh})

@app.route("/upgrade")
def upgrade():
    if "username" not in session:
        return jsonify({"error": "Nicht eingeloggt"}), 400

    player = Player.query.filter_by(username=session["username"]).first()
    if not player:
        return jsonify({"error": "Spieler nicht gefunden"}), 400

    upgrade_cost = round(50.0 * (1.2 ** player.upgrade_level), 2)

    if player.money >= upgrade_cost:
        player.money -= upgrade_cost
        player.power_rate *= 1.5
        player.upgrade_level += 1
        db.session.commit()

        return jsonify({
            "success": True,
            "power_rate": player.power_rate,
            "upgrade_cost": upgrade_cost,  # Korrekte Preisinformation wird gesendet
            "upgrade_level": player.upgrade_level
        })
    else:
        return jsonify({"error": "Nicht genug Geld"}), 400





@app.route("/buy_module")
def buy_module():
    if "username" not in session:
        return jsonify({"error": "Nicht eingeloggt"}), 400

    player = Player.query.filter_by(username=session["username"]).first()
    if not player:
        return jsonify({"error": "Spieler nicht gefunden"}), 400

    module_cost = round(100.0 * (1.3 ** player.module_count), 2)

    if player.money >= module_cost:
        player.money -= module_cost
        player.passive_energy += 1.0  # ✅ PV-Modul gibt 1 kWh/s passive Energie
        player.module_count += 1
        db.session.commit()

        return jsonify({
            "success": True,
            "passive_energy": player.passive_energy,
            "module_cost": round(100.0 * (1.3 ** player.module_count), 2),
            "module_count": player.module_count
        })
    else:
        return jsonify({"error": "Nicht genug Geld"}), 400




@app.route("/get_stats")
def get_stats():
    if "username" not in session:
        return jsonify({"error": "Nicht eingeloggt"}), 400

    player = Player.query.filter_by(username=session["username"]).first()
    if not player:
        return jsonify({"error": "Spieler nicht gefunden"}), 400

    # Berechnung der Kosten für Upgrades und Kraftwerke
    upgrade_cost = round(50.0 * (1.2 ** player.upgrade_level), 2)
    module_cost = round(100.0 * (1.3 ** player.module_count), 2)
    hydro_cost = round(500.0 * (1.5 ** player.hydro_count), 2)
    coal_cost = round(1500.0 * (1.7 ** player.coal_count), 2)

    return jsonify({
        "success": True,
        "money": player.money,
        "energy": player.energy,
        "passive_energy": player.passive_energy,
        "power_rate": player.power_rate,
        "level": player.level,
        "xp": player.xp,
        "xp_needed": player.xp_needed,
        "upgrade_cost": upgrade_cost,
        "module_cost": module_cost,
        "hydro_cost": hydro_cost,
        "coal_cost": coal_cost,
        "upgrade_level": player.upgrade_level,
        "module_count": player.module_count,
        "hydro_count": player.hydro_count,
        "coal_count": player.coal_count
    })





@app.route("/buy_hydro")
def buy_hydro():
    if "username" not in session:
        return jsonify({"error": "Nicht eingeloggt"}), 400

    player = Player.query.filter_by(username=session["username"]).first()
    if not player:
        return jsonify({"error": "Spieler nicht gefunden"}), 400

    hydro_cost = round(500.0 * (1.5 ** player.hydro_count), 2)  # **Höhere Preissteigerung**

    if player.money >= hydro_cost:
        player.money -= hydro_cost
        player.passive_energy += 2.0  # **Wasserkraftwerk gibt mehr passive Energie**
        player.hydro_count += 1
        db.session.commit()

        return jsonify({
            "success": True,
            "passive_energy": player.passive_energy,
            "hydro_cost": round(500.0 * (1.5 ** player.hydro_count), 2),
            "hydro_count": player.hydro_count
        })
    else:
        return jsonify({"error": "Nicht genug Geld"}), 400


@app.route("/buy_coal")
def buy_coal():
    if "username" not in session:
        return jsonify({"error": "Nicht eingeloggt"}), 400

    player = Player.query.filter_by(username=session["username"]).first()
    if not player:
        return jsonify({"error": "Spieler nicht gefunden"}), 400

    coal_cost = round(1500.0 * (1.7 ** player.coal_count), 2)  # **Noch teurer als Wasserkraft!**

    if player.money >= coal_cost:
        player.money -= coal_cost
        player.passive_energy += 5.0  # **Kohlekraftwerk gibt viel mehr passive Energie**
        player.coal_count += 1
        db.session.commit()

        return jsonify({
            "success": True,
            "passive_energy": player.passive_energy,
            "coal_cost": round(1500.0 * (1.7 ** player.coal_count), 2),
            "coal_count": player.coal_count
        })
    else:
        return jsonify({"error": "Nicht genug Geld"}), 400


@app.route("/add_passive_energy")
def add_passive_energy():
    if "username" not in session:
        return jsonify({"error": "Nicht eingeloggt"}), 400

    player = Player.query.filter_by(username=session["username"]).first()
    if not player:
        return jsonify({"error": "Spieler nicht gefunden"}), 400


    # Passive Energie hinzufügen
    player.energy += player.passive_energy

    # XP-Berechnung (ähnlich wie bei aktivem Klick)
    xp_gain = player.passive_energy * (1 + player.level * 0.02)  # XP aus passiver Energie
    player.xp += xp_gain

    # Level-Up, falls XP-Leiste voll ist
    leveled_up = False
    while player.xp >= player.xp_needed:
        player.xp -= player.xp_needed  # Rest-XP bleibt erhalten
        player.level += 1

        # XP-Anforderungen steigen exponentiell
        if player.level < 10:
            player.xp_needed *= 2.0
        else:
            player.xp_needed *= 2.5

        leveled_up = True

    db.session.commit()

    return jsonify({
        "success": True,
        "energy": player.energy,
        "xp": player.xp,
        "xp_needed": player.xp_needed,
        "level": player.level,
        "passive_energy": player.passive_energy,
        "leveled_up": leveled_up
    })





if __name__ == "__main__":
    app.run(debug=True)
