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
    total_energy_generated = db.Column(db.Float, default=0)
    prestige_level = db.Column(db.Integer, default=0)  # **NEU**
    prestige_points = db.Column(db.Integer, default=0)
    energy_boost_level = db.Column(db.Integer, default=0)
    xp_boost_level = db.Column(db.Integer, default=0)




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


@app.route("/prestige")
def prestige():
    if "username" not in session:
        return jsonify({"error": "Nicht eingeloggt"}), 400

    player = Player.query.filter_by(username=session["username"]).first()
    if not player:
        return jsonify({"error": "Spieler nicht gefunden"}), 400

    if player.total_energy_generated < 100000:
        return jsonify({"error": "Nicht genug erzeugte Energie für Prestige"}), 400

    # Prestige-Punkte berechnen
    prestige_points = int((player.total_energy_generated / 100000) ** 0.5)

    # **Prestige-Level erhöhen & Punkte speichern**
    player.prestige_level += 1
    player.prestige_points += prestige_points

    # **Spielerwerte zurücksetzen**
    player.money = 100.0
    player.energy = 0.0
    player.power_rate = 1.0
    player.upgrade_level = 1
    player.xp = 0
    player.level = 1
    player.xp_needed = 10
    player.total_energy_generated = 0

    db.session.commit()

    return jsonify({"success": True, "prestige_level": player.prestige_level, "prestige_points": player.prestige_points})




@app.route("/leaderboard")
def leaderboard():
    players = Player.query.order_by(Player.prestige_level.desc()).limit(10).all()  # Top 10 Spieler nach Prestige-Level
    leaderboard_data = [{"username": p.username, "prestige_level": p.prestige_level} for p in players]

    return jsonify({"success": True, "leaderboard": leaderboard_data})



@app.route("/generate_energy")
def generate_energy():
    if "username" not in session:
        return jsonify({"error": "Nicht eingeloggt"}), 400

    player = Player.query.filter_by(username=session["username"]).first()
    if not player:
        return jsonify({"error": "Spieler nicht gefunden"}), 400

    # Energieproduktion korrekt speichern
    energy_gain = player.power_rate
    player.energy += energy_gain
    player.total_energy_generated += energy_gain  # **Fix: Gesamtenergie erhöhen**

    # XP Berechnung mit exponentiellem Wachstum
    xp_gain = player.power_rate * (1.05 ** player.level)
    player.xp += xp_gain

    # Level-Up Logik
    leveled_up = False
    while player.xp >= player.xp_needed:
        player.xp -= player.xp_needed
        player.level += 1
        player.xp_needed *= 1.5  # XP-Anforderung steigt um 50%
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
        "total_energy_generated": player.total_energy_generated,  # **Debug: Anzeigen**
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

    upgrade_cost = round(50.0 * (1.15 ** player.upgrade_level), 2)

    if player.money >= upgrade_cost:
        player.money -= upgrade_cost
        player.power_rate *= 1.1  # Ertragsmultiplikator
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


@app.route("/buy_upgrade")
def buy_upgrade():
    if "username" not in session:
        return jsonify({"error": "Nicht eingeloggt"}), 400

    player = Player.query.filter_by(username=session["username"]).first()
    if not player:
        return jsonify({"error": "Spieler nicht gefunden"}), 400

    upgrade_type = request.args.get("type")
    
    # Upgrade-Level abrufen
    upgrade_levels = {
        "energy_boost": player.energy_boost_level,
        "xp_boost": player.xp_boost_level
    }

    # Skalierung der Kosten
    base_cost = 5
    cost = int(base_cost * (1.3 ** upgrade_levels[upgrade_type]))

    if player.prestige_points < cost:
        return jsonify({"error": "Nicht genug Prestige-Punkte"}), 400

    # Prestige-Punkte abziehen & Level speichern
    player.prestige_points -= cost
    if upgrade_type == "energy_boost":
        player.energy_boost_level += 1
        player.power_rate *= 1.1  # +10% Energie
    elif upgrade_type == "xp_boost":
        player.xp_boost_level += 1
        player.xp_needed *= 0.9  # -10% XP Kosten pro Level

    db.session.commit()

    return jsonify({
        "success": True,
        "new_level": upgrade_levels[upgrade_type] + 1,
        "new_cost": int(base_cost * (1.3 ** (upgrade_levels[upgrade_type] + 1))),
        "prestige_points": player.prestige_points
    })




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

    # Falls Prestige-Werte nicht existieren, setze sie auf 0
    prestige_level = getattr(player, "prestige_level", 0)
    prestige_points = getattr(player, "prestige_points", 0)

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
        "coal_count": player.coal_count,
        "total_energy_generated": player.total_energy_generated,
        "prestige_points": player.prestige_points,
        "prestige_level": player.prestige_level,
        "energy_boost_level": player.energy_boost_level,
        "xp_boost_level": player.xp_boost_level
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
